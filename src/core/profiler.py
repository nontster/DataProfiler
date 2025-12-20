"""
Core profiling logic.
"""

import logging
import textwrap
from typing import Optional

from jinja2 import Template
from soda.scan import Scan

from src.config import Config
from src.db.postgres import get_table_metadata
from src.db.clickhouse import init_clickhouse, insert_profiles
from src.exceptions import TableNotFoundError, DatabaseConnectionError

logger = logging.getLogger(__name__)

# Data types not supported for profiling
UNSUPPORTED_TYPES = [
    'timestamp', 
    'timestamp without time zone', 
    'date', 
    'bytea', 
    'boolean'
]


def is_profile_supported(pg_type: str) -> bool:
    """
    Check if a PostgreSQL data type is supported for profiling.
    
    Args:
        pg_type: PostgreSQL data type name
        
    Returns:
        bool: True if type is supported
    """
    return pg_type not in UNSUPPORTED_TYPES


def generate_sodacl_yaml(table_name: str, columns: list[dict]) -> str:
    """
    Generate SodaCL YAML configuration for profiling.
    
    Args:
        table_name: Name of the table to profile
        columns: List of column dictionaries with 'name' key
        
    Returns:
        str: SodaCL YAML content
    """
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
    return template.render(table_name=table_name, columns=columns)


def extract_profiling_results(scan_results: dict) -> list[dict]:
    """
    Extract profiling data from Soda scan results.
    
    Args:
        scan_results: Results from scan.get_scan_results()
        
    Returns:
        List of profile dictionaries
    """
    records = []
    
    if 'profiling' not in scan_results:
        return records
    
    for p in scan_results['profiling']:
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
            records.append(record)
    
    return records


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
        logger.info(f"Skipping {len(skipped_columns)} unsupported columns: "
                   f"{[c['name'] for c in skipped_columns]}")
    
    if not profile_columns:
        logger.warning("No columns available for profiling after filtering")
        return 0
    
    logger.info(f"Profiling {len(profile_columns)} columns: "
               f"{[c['name'] for c in profile_columns]}")
    
    # Step 4: Generate SodaCL configuration
    yaml_content = generate_sodacl_yaml(table_name, profile_columns)
    
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
    
    # Step 6: Extract and store results
    results = scan.get_scan_results()
    records = extract_profiling_results(results)
    
    if records:
        if insert_profiles(records):
            logger.info(f"✅ SUCCESS: Saved {len(records)} column profiles to ClickHouse")
            logger.info(f"   Columns: {[r['column_name'] for r in records]}")
            return len(records)
        else:
            return None
    else:
        logger.warning("No profiling data was collected from the scan")
        return 0
