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
    environment: str = "development"
) -> bool:
    """
    Insert profiling records into PostgreSQL.
    
    Args:
        table_profile: TableProfile object with column profiles
        application: Application/service name (e.g., 'order-service')
        environment: Environment name (e.g., 'uat', 'production')
        
    Returns:
        bool: True if insert successful, False otherwise
    """
    if not table_profile.column_profiles:
        logger.warning("No column profiles to insert")
        return False
    
    try:
        conn = get_postgres_metrics_connection()
        cursor = conn.cursor()
        
        data = []
        for col in table_profile.column_profiles:
            row = (
                application,
                environment,
                Config.POSTGRES_HOST,
                Config.POSTGRES_DATABASE,
                Config.POSTGRES_SCHEMA,
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
    environment: str = "development"
) -> bool:
    """
    Insert auto-increment profiling records into PostgreSQL.
    
    Args:
        profiles: List of AutoIncrementProfile objects
        application: Application/service name
        environment: Environment name
        
    Returns:
        bool: True if insert successful, False otherwise
    """
    if not profiles:
        logger.warning("No auto-increment profiles to insert")
        return False
    
    try:
        conn = get_postgres_metrics_connection()
        cursor = conn.cursor()
        
        data = []
        for profile in profiles:
            row = (
                application,
                environment,
                Config.POSTGRES_HOST,
                Config.POSTGRES_DATABASE,
                Config.POSTGRES_SCHEMA,
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
