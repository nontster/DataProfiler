"""
DataProfiler - Automated Data Profiling Tool
Uses Soda Core to profile PostgreSQL tables and stores results in ClickHouse.
"""

import os
import sys
import logging
import textwrap
from typing import Optional

import psycopg2
from psycopg2 import OperationalError, ProgrammingError
import clickhouse_connect
from clickhouse_connect.driver.exceptions import ClickHouseError
from jinja2 import Template
from soda.scan import Scan
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# --- Configuration from Environment Variables ---
class Config:
    """Centralized configuration management."""
    
    # PostgreSQL Configuration
    POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
    POSTGRES_PORT = int(os.getenv('POSTGRES_PORT', 5432))
    POSTGRES_DATABASE = os.getenv('POSTGRES_DATABASE', 'postgres')
    POSTGRES_USER = os.getenv('POSTGRES_USER', 'postgres')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', '')
    POSTGRES_SCHEMA = os.getenv('POSTGRES_SCHEMA', 'public')
    
    # ClickHouse Configuration
    CLICKHOUSE_HOST = os.getenv('CLICKHOUSE_HOST', 'localhost')
    CLICKHOUSE_PORT = int(os.getenv('CLICKHOUSE_PORT', 8123))
    CLICKHOUSE_USER = os.getenv('CLICKHOUSE_USER', 'default')
    CLICKHOUSE_PASSWORD = os.getenv('CLICKHOUSE_PASSWORD', '')
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration."""
        required = ['POSTGRES_PASSWORD', 'CLICKHOUSE_PASSWORD']
        missing = [key for key in required if not getattr(cls, key)]
        
        if missing:
            logger.warning(f"Missing recommended config: {', '.join(missing)}")
        
        return True


# --- Database Connections ---
class DatabaseConnectionError(Exception):
    """Custom exception for database connection errors."""
    pass


class TableNotFoundError(Exception):
    """Custom exception when table doesn't exist."""
    pass


def get_postgres_connection():
    """Create and return a PostgreSQL connection with error handling."""
    try:
        conn = psycopg2.connect(
            host=Config.POSTGRES_HOST,
            port=Config.POSTGRES_PORT,
            database=Config.POSTGRES_DATABASE,
            user=Config.POSTGRES_USER,
            password=Config.POSTGRES_PASSWORD,
            connect_timeout=10
        )
        logger.debug("PostgreSQL connection established")
        return conn
    except OperationalError as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        raise DatabaseConnectionError(f"PostgreSQL connection failed: {e}")


def get_clickhouse_client():
    """Create and return a ClickHouse client with error handling."""
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
    """Initialize ClickHouse table for storing profiling results."""
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


# --- Metadata Discovery ---
def table_exists(table_name: str) -> bool:
    """Check if a table exists in the PostgreSQL database."""
    try:
        conn = get_postgres_connection()
        cur = conn.cursor()
        
        query = """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = %s AND table_schema = %s
            )
        """
        cur.execute(query, (table_name, Config.POSTGRES_SCHEMA))
        exists = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        return exists
    except (OperationalError, ProgrammingError) as e:
        logger.error(f"Error checking table existence: {e}")
        return False


def get_table_metadata(table_name: str) -> list[dict]:
    """
    Retrieve column metadata for a given table.
    
    Args:
        table_name: Name of the table to get metadata for
        
    Returns:
        List of dictionaries with 'name' and 'type' keys
        
    Raises:
        TableNotFoundError: If the table doesn't exist
        DatabaseConnectionError: If connection fails
    """
    # Validate table exists first
    if not table_exists(table_name):
        raise TableNotFoundError(f"Table '{table_name}' not found in schema '{Config.POSTGRES_SCHEMA}'")
    
    try:
        conn = get_postgres_connection()
        cur = conn.cursor()
        
        query = """
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = %s AND table_schema = %s
            ORDER BY ordinal_position
        """
        cur.execute(query, (table_name, Config.POSTGRES_SCHEMA))
        columns = cur.fetchall()
        
        cur.close()
        conn.close()
        
        logger.info(f"Found {len(columns)} columns in table '{table_name}'")
        return [{"name": col[0], "type": col[1]} for col in columns]
        
    except (OperationalError, ProgrammingError) as e:
        logger.error(f"Error fetching metadata for '{table_name}': {e}")
        raise DatabaseConnectionError(f"Failed to fetch metadata: {e}")


def is_profile_supported(pg_type: str) -> bool:
    """Check if a PostgreSQL data type is supported for profiling."""
    unsupported = ['timestamp', 'timestamp without time zone', 'date', 'bytea', 'boolean']
    return pg_type not in unsupported


# --- Main Workflow ---
def run_profiler(table_name: str) -> Optional[int]:
    """
    Run the data profiler for a specific table.
    
    Args:
        table_name: Name of the table to profile
        
    Returns:
        Number of column profiles saved, or None if failed
    """
    logger.info(f"Starting profiler for table: '{table_name}'")
    
    # Step 1: Initialize ClickHouse
    if not init_clickhouse():
        logger.error("Aborting: ClickHouse initialization failed")
        return None
    
    # Step 2: Get table metadata
    try:
        logger.info(f"Discovering schema for '{table_name}'...")
        all_columns = get_table_metadata(table_name)
    except TableNotFoundError as e:
        logger.error(f"❌ {e}")
        return None
    except DatabaseConnectionError as e:
        logger.error(f"❌ Database error: {e}")
        return None
    
    if not all_columns:
        logger.warning(f"No columns found in table '{table_name}'")
        return 0
    
    # Step 3: Filter supported columns
    profile_columns = [c for c in all_columns if is_profile_supported(c['type'])]
    skipped_columns = [c for c in all_columns if not is_profile_supported(c['type'])]
    
    if skipped_columns:
        logger.info(f"Skipping {len(skipped_columns)} unsupported columns: {[c['name'] for c in skipped_columns]}")
    
    if not profile_columns:
        logger.warning("No columns available for profiling after filtering")
        return 0
    
    logger.info(f"Profiling {len(profile_columns)} columns: {[c['name'] for c in profile_columns]}")
    
    # Step 4: Generate SodaCL configuration
    sodacl_template = textwrap.dedent("""
        checks for {{ table_name }}:
          - row_count > 0

        profile columns:
          columns:
            {% for col in columns %}
            - {{ table_name }}.{{ col.name }}
            {% endfor %}
    """)
    
    template = Template(sodacl_template)
    yaml_content = template.render(table_name=table_name, columns=profile_columns)
    
    # Step 5: Run Soda Scan
    logger.info("Running Soda Core scan...")
    try:
        scan = Scan()
        scan.set_data_source_name("my_postgres")
        scan.add_configuration_yaml_file(file_path="configuration.yml")
        scan.add_sodacl_yaml_str(yaml_content)
        scan.execute()
    except Exception as e:
        logger.error(f"❌ Soda scan failed: {e}")
        return None
    
    # Step 6: Extract profiling results
    results = scan.get_scan_results()
    clickhouse_records = []
    
    if 'profiling' in results:
        for p in results['profiling']:
            t_name = p.get('table')
            column_profiles_list = p.get('columnProfiles', [])
            
            for col_item in column_profiles_list:
                col_name = col_item.get('columnName')
                stats = col_item.get('profile', {})
                
                record = {
                    "table_name": t_name,
                    "column_name": col_name,
                    "distinct_count": stats.get('distinct'),
                    "missing_count": stats.get('missing_count'),
                    "min": str(stats.get('min')) if stats.get('min') is not None else None,
                    "max": str(stats.get('max')) if stats.get('max') is not None else None,
                    "avg": stats.get('avg')
                }
                clickhouse_records.append(record)
    
    # Step 7: Store results in ClickHouse
    if clickhouse_records:
        try:
            client = get_clickhouse_client()
            data = [
                [r['table_name'], r['column_name'], r['distinct_count'], 
                 r['missing_count'], r['min'], r['max'], r['avg']] 
                for r in clickhouse_records
            ]
            
            client.insert(
                'data_profiles', 
                data, 
                column_names=['table_name', 'column_name', 'distinct_count', 
                             'missing_count', 'min', 'max', 'avg']
            )
            
            logger.info(f"✅ SUCCESS: Saved {len(clickhouse_records)} column profiles to ClickHouse")
            logger.info(f"   Columns: {[r['column_name'] for r in clickhouse_records]}")
            return len(clickhouse_records)
            
        except (ClickHouseError, DatabaseConnectionError) as e:
            logger.error(f"❌ Failed to insert data into ClickHouse: {e}")
            return None
    else:
        logger.warning("No profiling data was collected from the scan")
        return 0


def main():
    """Main entry point for the DataProfiler."""
    # Validate configuration
    Config.validate()
    
    # Get table name from command line or use default
    if len(sys.argv) > 1:
        target_table = sys.argv[1]
    else:
        target_table = "users"
        logger.info(f"No table specified, using default: '{target_table}'")
    
    # Run the profiler
    result = run_profiler(target_table)
    
    if result is None:
        logger.error("Profiling failed")
        sys.exit(1)
    elif result == 0:
        logger.warning("No profiles were generated")
        sys.exit(0)
    else:
        logger.info(f"Profiling completed successfully: {result} columns profiled")
        sys.exit(0)


if __name__ == "__main__":
    main()