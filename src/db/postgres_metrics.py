"""
PostgreSQL metrics storage operations.
Alternative to ClickHouse for storing profiling results.
"""

import logging
from typing import Optional

import psycopg2
from psycopg2.extras import execute_values

from src.config import Config
from src.exceptions import DatabaseConnectionError

logger = logging.getLogger(__name__)


def get_postgres_metrics_connection():
    """
    Create and return a PostgreSQL connection for metrics storage.
    
    Returns:
        psycopg2.connection: PostgreSQL connection
        
    Raises:
        DatabaseConnectionError: If connection fails
    """
    try:
        conn = psycopg2.connect(
            host=Config.PG_METRICS_HOST,
            port=Config.PG_METRICS_PORT,
            dbname=Config.PG_METRICS_DATABASE,
            user=Config.PG_METRICS_USER,
            password=Config.PG_METRICS_PASSWORD
        )
        logger.debug("PostgreSQL metrics connection established")
        return conn
    except psycopg2.Error as e:
        logger.error(f"Failed to connect to PostgreSQL metrics: {e}")
        raise DatabaseConnectionError(f"PostgreSQL metrics connection failed: {e}")


def init_postgres_metrics() -> bool:
    """
    Initialize PostgreSQL tables for storing profiling results.
    Supports multi-application and multi-environment profiles.
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    try:
        conn = get_postgres_metrics_connection()
        cursor = conn.cursor()
        
        # Create data_profiles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_profiles (
                id SERIAL PRIMARY KEY,
                scan_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Multi-tenancy columns
                application VARCHAR(255) DEFAULT 'default',
                environment VARCHAR(50) DEFAULT 'development',
                database_host VARCHAR(255) DEFAULT '',
                database_name VARCHAR(255) DEFAULT '',
                schema_name VARCHAR(100) DEFAULT 'public',
                
                -- Table/Column info
                table_name VARCHAR(255) NOT NULL,
                column_name VARCHAR(255) NOT NULL,
                data_type VARCHAR(100),
                
                -- Metrics
                row_count BIGINT,
                not_null_proportion FLOAT,
                distinct_proportion FLOAT,
                distinct_count BIGINT,
                is_unique BOOLEAN,
                min_value TEXT,
                max_value TEXT,
                avg_value FLOAT,
                median_value FLOAT,
                std_dev_population FLOAT,
                std_dev_sample FLOAT
            )
        """)
        
        # Create indexes for common query patterns
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_data_profiles_app_env 
            ON data_profiles (application, environment)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_data_profiles_table 
            ON data_profiles (table_name, scan_time DESC)
        """)
        
        # Create auto_increment_metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auto_increment_metrics (
                id SERIAL PRIMARY KEY,
                scan_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Multi-tenancy columns
                application VARCHAR(255) DEFAULT 'default',
                environment VARCHAR(50) DEFAULT 'development',
                database_host VARCHAR(255) DEFAULT '',
                database_name VARCHAR(255) DEFAULT '',
                schema_name VARCHAR(100) DEFAULT 'public',
                
                -- Column info
                table_name VARCHAR(255) NOT NULL,
                column_name VARCHAR(255) NOT NULL,
                data_type VARCHAR(100),
                sequence_name VARCHAR(255),
                
                -- Current metrics
                current_value BIGINT,
                max_type_value BIGINT,
                usage_percentage FLOAT,
                remaining_values BIGINT,
                
                -- Growth metrics
                daily_growth_rate FLOAT,
                days_until_full FLOAT,
                
                -- Alert status
                alert_status VARCHAR(20) DEFAULT 'OK'
            )
        """)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_autoincrement_app_env 
            ON auto_increment_metrics (application, environment)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_autoincrement_table 
            ON auto_increment_metrics (table_name, column_name, scan_time DESC)
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info("✅ PostgreSQL metrics tables are ready (data_profiles, auto_increment_metrics)")
        return True
        
    except (psycopg2.Error, DatabaseConnectionError) as e:
        logger.error(f"❌ PostgreSQL metrics initialization failed: {e}")
        return False


def insert_profiles_pg(
    table_profile,
    application: str = "default",
    environment: str = "development",
    database_type: str = "postgresql"
) -> bool:
    """
    Insert profiling records into PostgreSQL.
    
    Args:
        table_profile: TableProfile object with column profiles
        application: Application/service name (e.g., 'order-service')
        environment: Environment name (e.g., 'uat', 'production')
        database_type: Source database type ('postgresql' or 'mssql')
        
    Returns:
        bool: True if insert successful, False otherwise
    """
    if not table_profile.column_profiles:
        logger.warning("No column profiles to insert")
        return False
    
    try:
        conn = get_postgres_metrics_connection()
        cursor = conn.cursor()
        
        # Determine source database info based on database_type
        if database_type == 'mssql':
            source_host = Config.MSSQL_HOST
            source_database = Config.MSSQL_DATABASE
            source_schema = Config.MSSQL_SCHEMA
        else:
            source_host = Config.POSTGRES_HOST
            source_database = Config.POSTGRES_DATABASE
            source_schema = Config.POSTGRES_SCHEMA
        
        data = []
        for col in table_profile.column_profiles:
            row = (
                application,
                environment,
                source_host,
                source_database,
                source_schema,
                col.table_name,
                col.column_name,
                col.data_type,
                col.row_count,
                col.not_null_proportion,
                col.distinct_proportion,
                col.distinct_count,
                col.is_unique,
                col.min_value,
                col.max_value,
                col.avg,
                col.median,
                col.std_dev_population,
                col.std_dev_sample,
            )
            data.append(row)
        
        insert_query = """
            INSERT INTO data_profiles (
                application, environment, database_host, database_name, schema_name,
                table_name, column_name, data_type, row_count,
                not_null_proportion, distinct_proportion, distinct_count,
                is_unique, min_value, max_value, avg_value, median_value,
                std_dev_population, std_dev_sample
            ) VALUES %s
        """
        
        execute_values(cursor, insert_query, data)
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"✅ Inserted {len(data)} profiles to PostgreSQL [{application}/{environment}]")
        return True
        
    except psycopg2.Error as e:
        logger.error(f"❌ Failed to insert data into PostgreSQL: {e}")
        return False


def insert_autoincrement_profiles_pg(
    profiles: list,
    application: str = "default",
    environment: str = "development",
    database_type: str = "postgresql"
) -> bool:
    """
    Insert auto-increment profiling records into PostgreSQL.
    
    Args:
        profiles: List of AutoIncrementProfile objects
        application: Application/service name
        environment: Environment name
        database_type: Source database type ('postgresql' or 'mssql')
        
    Returns:
        bool: True if insert successful, False otherwise
    """
    if not profiles:
        logger.warning("No auto-increment profiles to insert")
        return False
    
    try:
        conn = get_postgres_metrics_connection()
        cursor = conn.cursor()
        
        # Determine source database info based on database_type
        if database_type == 'mssql':
            source_host = Config.MSSQL_HOST
            source_database = Config.MSSQL_DATABASE
            source_schema = Config.MSSQL_SCHEMA
        else:
            source_host = Config.POSTGRES_HOST
            source_database = Config.POSTGRES_DATABASE
            source_schema = Config.POSTGRES_SCHEMA
        
        data = []
        for profile in profiles:
            row = (
                application,
                environment,
                source_host,
                source_database,
                source_schema,
                profile.table_name,
                profile.column_name,
                profile.data_type,
                profile.sequence_name,
                profile.current_value,
                profile.max_type_value,
                profile.usage_percentage,
                profile.remaining_values,
                profile.daily_growth_rate,
                profile.days_until_full,
                profile.alert_status,
            )
            data.append(row)
        
        insert_query = """
            INSERT INTO auto_increment_metrics (
                application, environment, database_host, database_name, schema_name,
                table_name, column_name, data_type, sequence_name,
                current_value, max_type_value, usage_percentage, remaining_values,
                daily_growth_rate, days_until_full, alert_status
            ) VALUES %s
        """
        
        execute_values(cursor, insert_query, data)
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"✅ Inserted {len(data)} auto-increment profiles to PostgreSQL [{application}/{environment}]")
        return True
        
    except psycopg2.Error as e:
        logger.error(f"❌ Failed to insert auto-increment data into PostgreSQL: {e}")
        return False


def fetch_historical_data_pg(
    application: str,
    environment: str,
    table_name: str,
    column_name: str,
    lookback_days: int = 7
) -> tuple:
    """
    Fetch historical auto-increment values from PostgreSQL.
    
    Args:
        application: Application name filter
        environment: Environment name filter
        table_name: Table name filter
        column_name: Column name filter
        lookback_days: Number of days to look back
        
    Returns:
        Tuple of (timestamps, values) lists
    """
    try:
        conn = get_postgres_metrics_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT scan_time, current_value
            FROM auto_increment_metrics
            WHERE application = %s
                AND environment = %s
                AND table_name = %s
                AND column_name = %s
                AND scan_time >= NOW() - INTERVAL '%s days'
            ORDER BY scan_time ASC
        """
        
        cursor.execute(query, (application, environment, table_name, column_name, lookback_days))
        rows = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        timestamps = [row[0] for row in rows]
        values = [row[1] for row in rows]
        
        logger.debug(f"Fetched {len(timestamps)} historical data points from PostgreSQL for {table_name}.{column_name}")
        return timestamps, values
        
    except psycopg2.Error as e:
        logger.warning(f"Could not fetch historical data from PostgreSQL: {e}")
        return [], []


def get_postgres_metrics_client():
    """
    Get a PostgreSQL metrics connection (alias for get_postgres_metrics_connection).
    This provides a similar interface to get_clickhouse_client().
    
    Returns:
        psycopg2.connection: PostgreSQL connection
    """
    return get_postgres_metrics_connection()




# =============================================================================
# Schema Profiling Functions
# =============================================================================

def init_schema_profiles_pg() -> bool:
    """
    Initialize PostgreSQL table for storing schema profiles.
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    try:
        conn = get_postgres_metrics_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_profiles (
                id SERIAL PRIMARY KEY,
                scan_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Multi-tenancy
                application VARCHAR(255) DEFAULT 'default',
                environment VARCHAR(50) DEFAULT 'development',
                database_host VARCHAR(255) DEFAULT '',
                database_name VARCHAR(255) DEFAULT '',
                schema_name VARCHAR(100) DEFAULT 'public',
                table_name VARCHAR(255) NOT NULL,
                
                -- Column info
                column_name VARCHAR(255) NOT NULL,
                column_position INTEGER,
                data_type VARCHAR(100),
                is_nullable BOOLEAN DEFAULT FALSE,
                column_default TEXT,
                max_length INTEGER,
                numeric_precision INTEGER,
                numeric_scale INTEGER,
                
                -- Constraint info
                is_primary_key BOOLEAN DEFAULT FALSE,
                is_in_index BOOLEAN DEFAULT FALSE,
                index_names TEXT DEFAULT '',
                is_foreign_key BOOLEAN DEFAULT FALSE,
                fk_references VARCHAR(255) DEFAULT ''
            )
        """)
        
        # Create indexes for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_schema_profiles_app_env
            ON schema_profiles (application, environment, table_name)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_schema_profiles_scan
            ON schema_profiles (table_name, scan_time)
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info("✅ PostgreSQL table 'schema_profiles' is ready")
        return True
        
    except psycopg2.Error as e:
        logger.error(f"❌ Schema profiles table initialization failed: {e}")
        return False


def insert_schema_profiles_pg(
    schema,
    application: str = "default",
    environment: str = "development"
) -> bool:
    """
    Insert schema profile into PostgreSQL.
    
    Args:
        schema: TableSchema object
        application: Application/service name
        environment: Environment name
        
    Returns:
        bool: True if insert successful, False otherwise
    """
    try:
        conn = get_postgres_metrics_connection()
        cursor = conn.cursor()
        
        # Build index lookup for each column
        column_indexes = {}
        for idx in schema.indexes:
            for col in idx.columns:
                if col not in column_indexes:
                    column_indexes[col] = []
                column_indexes[col].append(idx.name)
        
        # Build FK lookup
        column_fks = {}
        for fk in schema.foreign_keys:
            for i, col in enumerate(fk.columns):
                ref = f"{fk.referenced_table}({fk.referenced_columns[i]})"
                column_fks[col] = ref
        
        # Insert each column
        for position, (col_name, col) in enumerate(schema.columns.items(), 1):
            is_pk = schema.primary_key and col_name in schema.primary_key
            idx_names = column_indexes.get(col_name, [])
            fk_ref = column_fks.get(col_name, '')
            
            cursor.execute("""
                INSERT INTO schema_profiles (
                    application, environment, database_host, database_name,
                    schema_name, table_name, column_name, column_position,
                    data_type, is_nullable, column_default, max_length,
                    numeric_precision, numeric_scale, is_primary_key,
                    is_in_index, index_names, is_foreign_key, fk_references
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                application,
                environment,
                schema.database_host,
                schema.database_name,
                schema.schema_name,
                schema.table_name,
                col_name,
                position,
                col.data_type,
                col.is_nullable,
                col.default_value,
                col.max_length,
                col.numeric_precision,
                col.numeric_scale,
                is_pk,
                bool(idx_names),
                ','.join(idx_names),
                bool(fk_ref),
                fk_ref,
            ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"✅ Inserted {len(schema.columns)} schema profiles [{application}/{environment}]")
        return True
        
    except psycopg2.Error as e:
        logger.error(f"❌ Failed to insert schema profiles into PostgreSQL: {e}")
        return False


# =============================================================================
# Table Inventory Functions
# =============================================================================

def init_table_inventory_pg() -> bool:
    """
    Initialize PostgreSQL table for storing table inventory snapshots.
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    try:
        conn = get_postgres_metrics_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS table_inventory (
                id SERIAL PRIMARY KEY,
                scan_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Multi-tenancy
                application VARCHAR(255) DEFAULT 'default',
                environment VARCHAR(50) DEFAULT 'development',
                database_host VARCHAR(255) DEFAULT '',
                database_name VARCHAR(255) DEFAULT '',
                schema_name VARCHAR(100) DEFAULT 'public',
                
                -- Table info
                table_name VARCHAR(255) NOT NULL
            )
        """)
        
        # Indexes for Grafana drift queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_table_inventory_app_env
            ON table_inventory (application, environment, schema_name)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_table_inventory_scan
            ON table_inventory (schema_name, scan_time DESC)
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info("✅ PostgreSQL table 'table_inventory' is ready")
        return True
        
    except psycopg2.Error as e:
        logger.error(f"❌ Table inventory initialization failed: {e}")
        return False


def insert_table_inventory_pg(
    tables: list[str],
    schema: str = "public",
    application: str = "default",
    environment: str = "development",
    database_type: str = "postgresql"
) -> bool:
    """
    Insert table inventory snapshot into PostgreSQL.
    
    Args:
        tables: List of table names discovered in the schema
        schema: Schema name
        application: Application/service name
        environment: Environment name
        database_type: Source database type
        
    Returns:
        bool: True if insert successful, False otherwise
    """
    if not tables:
        logger.warning("No tables to insert into inventory")
        return True
    
    try:
        conn = get_postgres_metrics_connection()
        cursor = conn.cursor()
        
        # Determine source database info
        if database_type in ('mssql', 'sqlserver'):
            source_host = Config.MSSQL_HOST
            source_database = Config.MSSQL_DATABASE
        elif database_type in ('mysql',):
            source_host = Config.MYSQL_HOST
            source_database = Config.MYSQL_DATABASE
        else:
            source_host = Config.POSTGRES_HOST
            source_database = Config.POSTGRES_DATABASE
        
        data = []
        for table_name in tables:
            row = (
                application,
                environment,
                source_host,
                source_database,
                schema,
                table_name,
            )
            data.append(row)
        
        insert_query = """
            INSERT INTO table_inventory (
                application, environment, database_host, database_name,
                schema_name, table_name
            ) VALUES %s
        """
        
        execute_values(cursor, insert_query, data)
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"✅ Inserted {len(data)} tables into inventory [{application}/{environment}/{schema}]")
        return True
        
    except psycopg2.Error as e:
        logger.error(f"❌ Failed to insert table inventory into PostgreSQL: {e}")
        return False
