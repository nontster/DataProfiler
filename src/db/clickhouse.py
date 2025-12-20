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
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    try:
        client = get_clickhouse_client()
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
        logger.info("✅ ClickHouse table 'data_profiles' is ready")
        return True
    except (ClickHouseError, DatabaseConnectionError) as e:
        logger.error(f"❌ ClickHouse initialization failed: {e}")
        return False


def insert_profiles(records: list[dict]) -> bool:
    """
    Insert profiling records into ClickHouse.
    
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
