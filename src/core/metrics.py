"""
Metrics calculation module for dbt-profiler style data profiling.
Calculates comprehensive column statistics using direct SQL queries.
Supports multiple database types (PostgreSQL, MSSQL).
"""

import logging
from typing import Optional, Literal
from dataclasses import dataclass, field
from datetime import datetime

from src.db.connection_factory import get_connection, get_schema, get_quote_char
from src.config import Config

logger = logging.getLogger(__name__)

# Type alias for supported databases
DatabaseType = Literal['postgresql', 'postgres', 'mssql', 'sqlserver', 'mysql']


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


# PostgreSQL numeric types
POSTGRES_NUMERIC_TYPES = [
    'integer', 'bigint', 'smallint', 'int', 'int2', 'int4', 'int8',
    'numeric', 'decimal', 'real', 'double precision', 'float', 'float4', 'float8',
    'money'
]

# MSSQL numeric types
MSSQL_NUMERIC_TYPES = [
    'tinyint', 'smallint', 'int', 'bigint',
    'numeric', 'decimal', 'real', 'float',
    'money', 'smallmoney'
]

# MySQL numeric types
MYSQL_NUMERIC_TYPES = [
    'tinyint', 'smallint', 'mediumint', 'int', 'integer', 'bigint',
    'decimal', 'dec', 'float', 'double', 'double precision', 'real',
    'bit', 'bool', 'boolean' # Treated as numeric (tinyint)
]

# PostgreSQL min/max supported types
POSTGRES_MINMAX_TYPES = POSTGRES_NUMERIC_TYPES + [
    'date', 'timestamp', 'timestamp without time zone', 
    'timestamp with time zone', 'time', 'time without time zone',
    'time with time zone', 'interval'
]

# MSSQL min/max supported types
MSSQL_MINMAX_TYPES = MSSQL_NUMERIC_TYPES + [
    'date', 'datetime', 'datetime2', 'datetimeoffset',
    'time', 'smalldatetime'
]

# MySQL min/max supported types
MYSQL_MINMAX_TYPES = MYSQL_NUMERIC_TYPES + [
    'date', 'datetime', 'timestamp', 'time', 'year'
]


def get_row_count(table_name: str, database_type: DatabaseType = 'postgresql', schema: Optional[str] = None) -> int:
    """Get approximate row count from catalog statistics (O(1), no table scan).
    
    Uses database-specific system catalogs for fast estimation:
      - PostgreSQL: pg_class.reltuples (updated by ANALYZE/autovacuum)
      - MySQL: information_schema.tables.TABLE_ROWS (estimate for InnoDB)
      - MSSQL: sys.dm_db_partition_stats (maintained by engine, accurate)
    
    Falls back to SELECT COUNT(*) if catalog returns 0 (e.g. table never analyzed).
    """
    conn = get_connection(database_type)
    cur = conn.cursor()
    
    target_schema = schema or get_schema(database_type) or ('public' if database_type == 'postgresql' else 'dbo')
    db_type = database_type.lower()
    count = 0
    
    try:
        if db_type in ('postgresql', 'postgres'):
            query = """
                SELECT COALESCE(c.reltuples, 0)::bigint
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relname = %s AND n.nspname = %s
            """
            logger.debug(f"Executing catalog row count query:\n{query}")
            cur.execute(query, (table_name, target_schema))
            result = cur.fetchone()
            count = result[0] if result else 0
        
        elif db_type in ('mysql',):
            query = """
                SELECT COALESCE(TABLE_ROWS, 0)
                FROM information_schema.tables
                WHERE TABLE_NAME = %s AND TABLE_SCHEMA = %s
            """
            logger.debug(f"Executing catalog row count query:\n{query}")
            cur.execute(query, (table_name, target_schema))
            result = cur.fetchone()
            count = result[0] if result else 0
        
        elif db_type in ('mssql', 'sqlserver'):
            query = """
                SELECT COALESCE(SUM(p.rows), 0)
                FROM sys.partitions p
                JOIN sys.tables t ON t.object_id = p.object_id
                JOIN sys.schemas s ON s.schema_id = t.schema_id
                WHERE t.name = %s AND s.name = %s AND p.index_id IN (0, 1)
            """
            logger.debug(f"Executing catalog row count query:\n{query}")
            cur.execute(query, (table_name, target_schema))
            result = cur.fetchone()
            count = result[0] if result else 0
    
    except Exception as e:
        logger.warning(f"Catalog row count query failed for '{target_schema}.{table_name}': {e}")
        count = 0
    
    # Fallback: exact count if catalog returns 0 (e.g. freshly created, never analyzed)
    if count <= 0:
        logger.debug(f"Catalog returned 0 for '{target_schema}.{table_name}', falling back to SELECT COUNT(*)")
        oq, cq = get_quote_char(database_type)
        try:
            query = f'SELECT COUNT(*) FROM {oq}{target_schema}{cq}.{oq}{table_name}{cq}'
            logger.debug(f"Executing fallback count query: {query}")
            cur.execute(query)
            count = cur.fetchone()[0]
        except Exception as e:
            logger.error(f"Fallback COUNT(*) also failed for '{target_schema}.{table_name}': {e}")
            count = 0
    else:
        logger.debug(f"Row count for '{target_schema}.{table_name}' from catalog: {count:,} (approximate)")
    
    cur.close()
    conn.close()
    
    return count


def is_numeric_type(data_type: str, database_type: DatabaseType = 'postgresql') -> bool:
    """Check if a data type is numeric for the given database."""
    db_type = database_type.lower()
    
    if db_type in ('postgresql', 'postgres'):
        numeric_types = POSTGRES_NUMERIC_TYPES
    elif db_type in ('mssql', 'sqlserver'):
        numeric_types = MSSQL_NUMERIC_TYPES
    elif db_type in ('mysql',):
        numeric_types = MYSQL_NUMERIC_TYPES
    else:
        numeric_types = POSTGRES_NUMERIC_TYPES
    
    return data_type.lower() in numeric_types


def is_minmax_supported(data_type: str, database_type: DatabaseType = 'postgresql') -> bool:
    """
    Check if MIN/MAX is meaningful for this data type.
    Per dbt-profiler: min/max only for numeric, date, and time columns.
    """
    db_type = database_type.lower()
    
    if db_type in ('postgresql', 'postgres'):
        supported_types = POSTGRES_MINMAX_TYPES
    elif db_type in ('mssql', 'sqlserver'):
        supported_types = MSSQL_MINMAX_TYPES
    elif db_type in ('mysql',):
        supported_types = MYSQL_MINMAX_TYPES
    else:
        supported_types = POSTGRES_MINMAX_TYPES
    
    return data_type.lower() in supported_types


def calculate_column_metrics(
    table_name: str,
    column_name: str,
    data_type: str,
    row_count: int,
    database_type: DatabaseType = 'postgresql',
    schema: Optional[str] = None
) -> ColumnProfile:
    """
    Calculate comprehensive metrics for a single column.
    
    Args:
        table_name: Name of the table
        column_name: Name of the column
        data_type: Database data type
        row_count: Total rows in table
        database_type: Type of database (postgresql or mssql)
        schema: Database schema
        
    Returns:
        ColumnProfile with all calculated metrics
    """
    conn = get_connection(database_type)
    cur = conn.cursor()
    
    target_schema = schema or get_schema(database_type) or ('public' if database_type == 'postgresql' else 'dbo')
    oq, cq = get_quote_char(database_type)
    db_type = database_type.lower()
    
    # Build the metrics query
    is_numeric = is_numeric_type(data_type, database_type)
    supports_minmax = is_minmax_supported(data_type, database_type)
    
    # Base metrics (all column types)
    base_query = f'''
        SELECT 
            COUNT({oq}{column_name}{cq}) as not_null_count,
            COUNT(DISTINCT {oq}{column_name}{cq}) as distinct_count
        FROM {oq}{target_schema}{cq}.{oq}{table_name}{cq}
    '''
    
    logger.debug(f"Executing base metrics query for {column_name}:\n{base_query}")
    cur.execute(base_query)
    base_result = cur.fetchone()
    not_null_count = base_result[0]
    distinct_count = base_result[1]
    
    # Calculate proportions
    not_null_proportion = not_null_count / row_count if row_count > 0 else None
    distinct_proportion = distinct_count / row_count if row_count > 0 else None
    is_unique = distinct_count == not_null_count and not_null_count > 0
    
    # Get min/max (only for numeric, date, and time types per dbt-profiler)
    min_value = None
    max_value = None
    
    if supports_minmax:
        try:
            if db_type in ('postgresql', 'postgres'):
                minmax_query = f'''
                    SELECT 
                        MIN({oq}{column_name}{cq})::text,
                        MAX({oq}{column_name}{cq})::text
                    FROM {oq}{target_schema}{cq}.{oq}{table_name}{cq}
                '''
            elif db_type in ('mysql',):
                minmax_query = f'''
                    SELECT 
                        CAST(MIN({oq}{column_name}{cq}) AS CHAR),
                        CAST(MAX({oq}{column_name}{cq}) AS CHAR)
                    FROM {oq}{target_schema}{cq}.{oq}{table_name}{cq}
                '''
            else:  # MSSQL
                minmax_query = f'''
                    SELECT 
                        CAST(MIN({oq}{column_name}{cq}) AS NVARCHAR(MAX)),
                        CAST(MAX({oq}{column_name}{cq}) AS NVARCHAR(MAX))
                    FROM {oq}{target_schema}{cq}.{oq}{table_name}{cq}
                '''
            logger.debug(f"Executing min/max query for {column_name}:\n{minmax_query}")
            cur.execute(minmax_query)
            minmax_result = cur.fetchone()
            min_value = minmax_result[0]
            max_value = minmax_result[1]
        except Exception:
            min_value = None
            max_value = None
            
        # Fix for MySQL connector returning bytes for text columns
        if isinstance(min_value, bytes):
            min_value = min_value.decode('utf-8', errors='replace')
        if isinstance(max_value, bytes):
            max_value = max_value.decode('utf-8', errors='replace')

    
    # Numeric-only metrics
    avg = None
    median = None
    std_dev_population = None
    std_dev_sample = None
    
    if is_numeric:
        try:
            if db_type in ('postgresql', 'postgres'):
                numeric_query = f'''
                    SELECT 
                        AVG({oq}{column_name}{cq})::float8,
                        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY {oq}{column_name}{cq})::float8,
                        STDDEV_POP({oq}{column_name}{cq})::float8,
                        STDDEV_SAMP({oq}{column_name}{cq})::float8
                    FROM {oq}{target_schema}{cq}.{oq}{table_name}{cq}
                '''
            elif db_type in ('mysql',):
                # MySQL doesn't fully support PERCENTILE_CONT/MEDIAN cleanly in one line
                numeric_query = f'''
                    SELECT 
                        AVG({oq}{column_name}{cq}),
                        NULL, -- Median not supported
                        STDDEV_POP({oq}{column_name}{cq}),
                        STDDEV_SAMP({oq}{column_name}{cq})
                    FROM {oq}{target_schema}{cq}.{oq}{table_name}{cq}
                '''
            else:  # MSSQL - use PERCENTILE_CONT with OVER clause
                numeric_query = f'''
                    SELECT 
                        AVG(CAST({oq}{column_name}{cq} AS FLOAT)),
                        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY {oq}{column_name}{cq}) OVER (),
                        STDEVP({oq}{column_name}{cq}),
                        STDEV({oq}{column_name}{cq})
                    FROM {oq}{target_schema}{cq}.{oq}{table_name}{cq}
                '''
            logger.debug(f"Executing numeric metrics query for {column_name}:\n{numeric_query}")
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


def profile_table(
    table_name: str, 
    columns: list[dict],
    database_type: DatabaseType = 'postgresql',
    schema: Optional[str] = None
) -> TableProfile:
    """
    Profile all columns in a table.
    
    Args:
        table_name: Name of the table to profile
        columns: List of column dicts with 'name' and 'type' keys
        database_type: Type of database (postgresql or mssql)
        schema: Database schema
        
    Returns:
        TableProfile with all column profiles
    """
    logger.info(f"Calculating metrics for {len(columns)} columns...")
    
    # Get row count once for the whole table
    row_count = get_row_count(table_name, database_type, schema=schema)
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
                row_count=row_count,
                database_type=database_type,
                schema=schema
            )
            column_profiles.append(profile)
        except Exception as e:
            logger.warning(f"Failed to profile column '{col_name}': {e}")
    
    return TableProfile(
        table_name=table_name,
        row_count=row_count,
        column_profiles=column_profiles
    )
