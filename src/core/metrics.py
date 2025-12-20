"""
Metrics calculation module for dbt-profiler style data profiling.
Calculates comprehensive column statistics using direct SQL queries.
"""

import logging
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime

from src.db.postgres import get_postgres_connection
from src.config import Config

logger = logging.getLogger(__name__)


@dataclass
class ColumnProfile:
    """Data class representing a column's profile metrics."""
    table_name: str
    column_name: str
    data_type: str
    row_count: int
    not_null_proportion: Optional[float] = None
    distinct_proportion: Optional[float] = None
    distinct_count: Optional[int] = None
    is_unique: bool = False
    min_value: Optional[str] = None
    max_value: Optional[str] = None
    avg: Optional[float] = None
    median: Optional[float] = None
    std_dev_population: Optional[float] = None
    std_dev_sample: Optional[float] = None
    profiled_at: datetime = field(default_factory=datetime.now)


@dataclass 
class TableProfile:
    """Data class representing a table's complete profile."""
    table_name: str
    row_count: int
    column_profiles: list[ColumnProfile]
    profiled_at: datetime = field(default_factory=datetime.now)


def get_row_count(table_name: str) -> int:
    """Get total row count for a table."""
    conn = get_postgres_connection()
    cur = conn.cursor()
    
    query = f'SELECT COUNT(*) FROM "{Config.POSTGRES_SCHEMA}"."{table_name}"'
    cur.execute(query)
    count = cur.fetchone()[0]
    
    cur.close()
    conn.close()
    
    return count


def is_numeric_type(data_type: str) -> bool:
    """Check if a PostgreSQL data type is numeric."""
    numeric_types = [
        'integer', 'bigint', 'smallint', 'int', 'int2', 'int4', 'int8',
        'numeric', 'decimal', 'real', 'double precision', 'float', 'float4', 'float8',
        'money'
    ]
    return data_type.lower() in numeric_types


def calculate_column_metrics(
    table_name: str,
    column_name: str,
    data_type: str,
    row_count: int
) -> ColumnProfile:
    """
    Calculate comprehensive metrics for a single column.
    
    Args:
        table_name: Name of the table
        column_name: Name of the column
        data_type: PostgreSQL data type
        row_count: Total rows in table
        
    Returns:
        ColumnProfile with all calculated metrics
    """
    conn = get_postgres_connection()
    cur = conn.cursor()
    
    schema = Config.POSTGRES_SCHEMA
    
    # Build the metrics query
    is_numeric = is_numeric_type(data_type)
    
    # Base metrics (all column types)
    base_query = f'''
        SELECT 
            COUNT("{column_name}") as not_null_count,
            COUNT(DISTINCT "{column_name}") as distinct_count
        FROM "{schema}"."{table_name}"
    '''
    
    cur.execute(base_query)
    base_result = cur.fetchone()
    not_null_count = base_result[0]
    distinct_count = base_result[1]
    
    # Calculate proportions
    not_null_proportion = not_null_count / row_count if row_count > 0 else None
    distinct_proportion = distinct_count / row_count if row_count > 0 else None
    is_unique = distinct_count == not_null_count and not_null_count > 0
    
    # Get min/max (works for most types)
    try:
        minmax_query = f'''
            SELECT 
                MIN("{column_name}")::text,
                MAX("{column_name}")::text
            FROM "{schema}"."{table_name}"
        '''
        cur.execute(minmax_query)
        minmax_result = cur.fetchone()
        min_value = minmax_result[0]
        max_value = minmax_result[1]
    except Exception:
        min_value = None
        max_value = None
    
    # Numeric-only metrics
    avg = None
    median = None
    std_dev_population = None
    std_dev_sample = None
    
    if is_numeric:
        try:
            numeric_query = f'''
                SELECT 
                    AVG("{column_name}")::float8,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY "{column_name}")::float8,
                    STDDEV_POP("{column_name}")::float8,
                    STDDEV_SAMP("{column_name}")::float8
                FROM "{schema}"."{table_name}"
            '''
            cur.execute(numeric_query)
            numeric_result = cur.fetchone()
            avg = numeric_result[0]
            median = numeric_result[1]
            std_dev_population = numeric_result[2]
            std_dev_sample = numeric_result[3]
        except Exception as e:
            logger.debug(f"Could not calculate numeric metrics for {column_name}: {e}")
    
    cur.close()
    conn.close()
    
    return ColumnProfile(
        table_name=table_name,
        column_name=column_name,
        data_type=data_type,
        row_count=row_count,
        not_null_proportion=round(not_null_proportion, 4) if not_null_proportion else None,
        distinct_proportion=round(distinct_proportion, 4) if distinct_proportion else None,
        distinct_count=distinct_count,
        is_unique=is_unique,
        min_value=min_value,
        max_value=max_value,
        avg=round(avg, 6) if avg else None,
        median=round(median, 6) if median else None,
        std_dev_population=round(std_dev_population, 6) if std_dev_population else None,
        std_dev_sample=round(std_dev_sample, 6) if std_dev_sample else None,
    )


def profile_table(table_name: str, columns: list[dict]) -> TableProfile:
    """
    Profile all columns in a table.
    
    Args:
        table_name: Name of the table to profile
        columns: List of column dicts with 'name' and 'type' keys
        
    Returns:
        TableProfile with all column profiles
    """
    logger.info(f"Calculating metrics for {len(columns)} columns...")
    
    # Get row count once for the whole table
    row_count = get_row_count(table_name)
    logger.info(f"Table '{table_name}' has {row_count:,} rows")
    
    column_profiles = []
    
    for col in columns:
        col_name = col['name']
        col_type = col['type']
        
        logger.debug(f"Profiling column: {col_name} ({col_type})")
        
        try:
            profile = calculate_column_metrics(
                table_name=table_name,
                column_name=col_name,
                data_type=col_type,
                row_count=row_count
            )
            column_profiles.append(profile)
        except Exception as e:
            logger.warning(f"Failed to profile column '{col_name}': {e}")
    
    return TableProfile(
        table_name=table_name,
        row_count=row_count,
        column_profiles=column_profiles
    )
