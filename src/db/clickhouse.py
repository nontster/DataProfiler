"""
ClickHouse database connection and operations.
"""

import logging

import clickhouse_connect
from clickhouse_connect.driver.exceptions import ClickHouseError

from src.config import Config
from src.exceptions import DatabaseConnectionError

logger = logging.getLogger(__name__)


def get_clickhouse_client():
    """
    Create and return a ClickHouse client with error handling.
    
    Returns:
        clickhouse_connect.driver.client.Client: ClickHouse client
        
    Raises:
        DatabaseConnectionError: If connection fails
    """
    try:
        client = clickhouse_connect.get_client(
            host=Config.CLICKHOUSE_HOST,
            port=Config.CLICKHOUSE_PORT,
            username=Config.CLICKHOUSE_USER,
            password=Config.CLICKHOUSE_PASSWORD
        )
        logger.debug("ClickHouse connection established")
        return client
    except ClickHouseError as e:
        logger.error(f"Failed to connect to ClickHouse: {e}")
        raise DatabaseConnectionError(f"ClickHouse connection failed: {e}")


def init_clickhouse() -> bool:
    """
    Initialize ClickHouse table for storing profiling results.
    Supports multi-application and multi-environment profiles.
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    try:
        client = get_clickhouse_client()
        
        # data_profiles table with multi-tenancy support
        client.command("""
            CREATE TABLE IF NOT EXISTS data_profiles (
                -- Metadata
                scan_time DateTime DEFAULT now(),
                
                -- Multi-tenancy columns
                application String DEFAULT 'default',
                environment LowCardinality(String) DEFAULT 'development',
                database_host String DEFAULT '',
                database_name String DEFAULT '',
                schema_name String DEFAULT 'public',
                
                -- Table/Column info
                table_name String,
                column_name String,
                data_type String,
                
                -- Metrics
                row_count Int64,
                not_null_proportion Nullable(Float64),
                distinct_proportion Nullable(Float64),
                distinct_count Nullable(Int64),
                is_unique UInt8,
                min Nullable(String),
                max Nullable(String),
                avg Nullable(Float64),
                median Nullable(Float64),
                std_dev_population Nullable(Float64),
                std_dev_sample Nullable(Float64)
                
            ) ENGINE = MergeTree()
            PARTITION BY toYYYYMM(scan_time)
            ORDER BY (application, environment, table_name, scan_time, column_name)
        """)
        
        logger.info("✅ ClickHouse table 'data_profiles' is ready (multi-env schema)")
        return True
    except (ClickHouseError, DatabaseConnectionError) as e:
        logger.error(f"❌ ClickHouse initialization failed: {e}")
        return False


def insert_profiles(
    table_profile,
    application: str = "default",
    environment: str = "development",
    database_type: str = "postgresql"
) -> bool:
    """
    Insert profiling records into ClickHouse.
    
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
        client = get_clickhouse_client()
        
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
            row = [
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
                1 if col.is_unique else 0,
                col.min_value,
                col.max_value,
                col.avg,
                col.median,
                col.std_dev_population,
                col.std_dev_sample,
            ]
            data.append(row)
        
        client.insert(
            'data_profiles', 
            data, 
            column_names=[
                'application', 'environment', 'database_host', 'database_name', 'schema_name',
                'table_name', 'column_name', 'data_type', 'row_count',
                'not_null_proportion', 'distinct_proportion', 'distinct_count',
                'is_unique', 'min', 'max', 'avg', 'median',
                'std_dev_population', 'std_dev_sample'
            ]
        )
        
        logger.info(f"✅ Inserted {len(data)} profiles [{application}/{environment}]")
        return True
        
    except ClickHouseError as e:
        logger.error(f"❌ Failed to insert data into ClickHouse: {e}")
        return False


def init_autoincrement_table() -> bool:
    """
    Initialize ClickHouse table for auto-increment overflow monitoring.
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    try:
        client = get_clickhouse_client()
        
        client.command("""
            CREATE TABLE IF NOT EXISTS auto_increment_metrics (
                -- Metadata
                scan_time DateTime DEFAULT now(),
                
                -- Multi-tenancy columns
                application String DEFAULT 'default',
                environment LowCardinality(String) DEFAULT 'development',
                database_host String DEFAULT '',
                database_name String DEFAULT '',
                schema_name String DEFAULT 'public',
                
                -- Column info
                table_name String,
                column_name String,
                data_type String,
                sequence_name String,
                
                -- Current metrics
                current_value Int64,
                max_type_value Int64,
                usage_percentage Float64,
                remaining_values Int64,
                
                -- Growth metrics (calculated from time series)
                daily_growth_rate Nullable(Float64),
                days_until_full Nullable(Float64),
                
                -- Alert status
                alert_status LowCardinality(String) DEFAULT 'OK'
                
            ) ENGINE = MergeTree()
            PARTITION BY toYYYYMM(scan_time)
            ORDER BY (application, environment, table_name, column_name, scan_time)
        """)
        
        logger.info("✅ ClickHouse table 'auto_increment_metrics' is ready")
        return True
    except (ClickHouseError, DatabaseConnectionError) as e:
        logger.error(f"❌ Auto-increment table initialization failed: {e}")
        return False


def insert_autoincrement_profiles(
    profiles: list,
    application: str = "default",
    environment: str = "development",
    database_type: str = "postgresql"
) -> bool:
    """
    Insert auto-increment profiling records into ClickHouse.
    
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
        client = get_clickhouse_client()
        
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
            row = [
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
            ]
            data.append(row)
        
        client.insert(
            'auto_increment_metrics',
            data,
            column_names=[
                'application', 'environment', 'database_host', 'database_name', 'schema_name',
                'table_name', 'column_name', 'data_type', 'sequence_name',
                'current_value', 'max_type_value', 'usage_percentage', 'remaining_values',
                'daily_growth_rate', 'days_until_full', 'alert_status'
            ]
        )
        
        logger.info(f"✅ Inserted {len(data)} auto-increment profiles [{application}/{environment}]")
        return True
        
    except ClickHouseError as e:
        logger.error(f"❌ Failed to insert auto-increment data into ClickHouse: {e}")
        return False




# =============================================================================
# Schema Profiling Functions
# =============================================================================

def init_schema_profiles_clickhouse() -> bool:
    """
    Initialize ClickHouse table for storing schema profiles.
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    try:
        client = get_clickhouse_client()
        
        client.command("""
            CREATE TABLE IF NOT EXISTS schema_profiles (
                -- Metadata
                scan_time DateTime DEFAULT now(),
                
                -- Multi-tenancy
                application String DEFAULT 'default',
                environment LowCardinality(String) DEFAULT 'development',
                database_host String DEFAULT '',
                database_name String DEFAULT '',
                schema_name String DEFAULT 'public',
                table_name String,
                
                -- Column info
                column_name String,
                column_position Int32,
                data_type String,
                is_nullable UInt8 DEFAULT 0,
                column_default Nullable(String),
                max_length Nullable(Int32),
                numeric_precision Nullable(Int32),
                numeric_scale Nullable(Int32),
                
                -- Constraint info
                is_primary_key UInt8 DEFAULT 0,
                is_in_index UInt8 DEFAULT 0,
                index_names String DEFAULT '',
                is_foreign_key UInt8 DEFAULT 0,
                fk_references String DEFAULT ''
                
            ) ENGINE = MergeTree()
            PARTITION BY toYYYYMM(scan_time)
            ORDER BY (application, environment, table_name, scan_time, column_name)
        """)
        
        logger.info("✅ ClickHouse table 'schema_profiles' is ready")
        return True
    except (ClickHouseError, DatabaseConnectionError) as e:
        logger.error(f"❌ Schema profiles table initialization failed: {e}")
        return False


def insert_schema_profiles(
    schema,
    application: str = "default",
    environment: str = "development"
) -> bool:
    """
    Insert schema profile into ClickHouse.
    
    Args:
        schema: TableSchema object
        application: Application/service name
        environment: Environment name
        
    Returns:
        bool: True if insert successful, False otherwise
    """
    try:
        client = get_clickhouse_client()
        
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
        
        data = []
        for position, (col_name, col) in enumerate(schema.columns.items(), 1):
            is_pk = schema.primary_key and col_name in schema.primary_key
            idx_names = column_indexes.get(col_name, [])
            fk_ref = column_fks.get(col_name, '')
            
            row = [
                application,
                environment,
                schema.database_host,
                schema.database_name,
                schema.schema_name,
                schema.table_name,
                col_name,
                position,
                col.data_type,
                1 if col.is_nullable else 0,
                col.default_value,
                col.max_length,
                col.numeric_precision,
                col.numeric_scale,
                1 if is_pk else 0,
                1 if idx_names else 0,
                ','.join(idx_names),
                1 if fk_ref else 0,
                fk_ref,
            ]
            data.append(row)
        
        client.insert(
            'schema_profiles',
            data,
            column_names=[
                'application', 'environment', 'database_host', 'database_name',
                'schema_name', 'table_name', 'column_name', 'column_position',
                'data_type', 'is_nullable', 'column_default', 'max_length',
                'numeric_precision', 'numeric_scale', 'is_primary_key',
                'is_in_index', 'index_names', 'is_foreign_key', 'fk_references'
            ]
        )
        
        logger.info(f"✅ Inserted {len(data)} schema profiles [{application}/{environment}]")
        return True
        
    except ClickHouseError as e:
        logger.error(f"❌ Failed to insert schema profiles into ClickHouse: {e}")
        return False
