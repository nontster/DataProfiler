"""
ClickHouse database connection and operations.
"""

import logging
from typing import Optional

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
    Initialize ClickHouse tables for storing profiling results.
    Creates both legacy and new v2 tables.
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    try:
        client = get_clickhouse_client()
        
        # Legacy table (for backward compatibility)
        client.command("""
            CREATE TABLE IF NOT EXISTS data_profiles (
                scan_time DateTime DEFAULT now(),
                table_name String,
                column_name String,
                distinct_count Nullable(Int64),
                missing_count Nullable(Int64),
                min Nullable(String),
                max Nullable(String),
                avg Nullable(Float64)
            ) ENGINE = MergeTree() ORDER BY (scan_time, table_name)
        """)
        
        # New v2 table with dbt-profiler style metrics
        client.command("""
            CREATE TABLE IF NOT EXISTS data_profiles_v2 (
                scan_time DateTime DEFAULT now(),
                table_name String,
                column_name String,
                data_type String,
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
            ) ENGINE = MergeTree() ORDER BY (scan_time, table_name, column_name)
        """)
        
        logger.info("✅ ClickHouse tables ready (data_profiles, data_profiles_v2)")
        return True
    except (ClickHouseError, DatabaseConnectionError) as e:
        logger.error(f"❌ ClickHouse initialization failed: {e}")
        return False


def insert_profiles(records: list[dict]) -> bool:
    """
    Insert profiling records into ClickHouse (legacy table).
    
    Args:
        records: List of profile dictionaries
        
    Returns:
        bool: True if insert successful, False otherwise
    """
    if not records:
        logger.warning("No records to insert")
        return False
    
    try:
        client = get_clickhouse_client()
        data = [
            [r['table_name'], r['column_name'], r['distinct_count'], 
             r['missing_count'], r['min'], r['max'], r['avg']] 
            for r in records
        ]
        
        client.insert(
            'data_profiles', 
            data, 
            column_names=['table_name', 'column_name', 'distinct_count', 
                         'missing_count', 'min', 'max', 'avg']
        )
        
        logger.info(f"✅ Inserted {len(records)} records into ClickHouse")
        return True
        
    except ClickHouseError as e:
        logger.error(f"❌ Failed to insert data into ClickHouse: {e}")
        return False


def insert_profiles_v2(table_profile) -> bool:
    """
    Insert profiling records into ClickHouse v2 table (dbt-profiler style).
    
    Args:
        table_profile: TableProfile object with column profiles
        
    Returns:
        bool: True if insert successful, False otherwise
    """
    if not table_profile.column_profiles:
        logger.warning("No column profiles to insert")
        return False
    
    try:
        client = get_clickhouse_client()
        
        data = []
        for col in table_profile.column_profiles:
            row = [
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
            'data_profiles_v2', 
            data, 
            column_names=[
                'table_name', 'column_name', 'data_type', 'row_count',
                'not_null_proportion', 'distinct_proportion', 'distinct_count',
                'is_unique', 'min', 'max', 'avg', 'median',
                'std_dev_population', 'std_dev_sample'
            ]
        )
        
        logger.info(f"✅ Inserted {len(data)} profiles into data_profiles_v2")
        return True
        
    except ClickHouseError as e:
        logger.error(f"❌ Failed to insert data into ClickHouse: {e}")
        return False
