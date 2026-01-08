"""
Database connection factory for multi-database support.
Provides a unified interface for getting connections to different database types.
"""

import logging
from typing import Literal

from src.db.postgres import get_postgres_connection, get_table_metadata as pg_get_table_metadata
from src.db.mssql import get_mssql_connection, get_table_metadata as mssql_get_table_metadata
from src.config import Config

logger = logging.getLogger(__name__)

# Supported database types
DatabaseType = Literal['postgresql', 'postgres', 'mssql', 'sqlserver']


def get_connection(database_type: DatabaseType):
    """
    Get a database connection for the specified database type.
    
    Args:
        database_type: Type of database ('postgresql', 'mssql', etc.)
        
    Returns:
        Database connection object
        
    Raises:
        ValueError: If database type is not supported
    """
    db_type = database_type.lower()
    
    if db_type in ('postgresql', 'postgres'):
        return get_postgres_connection()
    elif db_type in ('mssql', 'sqlserver'):
        return get_mssql_connection()
    else:
        raise ValueError(f"Unsupported database type: {database_type}")


def get_table_metadata(table_name: str, database_type: DatabaseType) -> list[dict]:
    """
    Get table metadata for the specified database type.
    
    Args:
        table_name: Name of the table
        database_type: Type of database
        
    Returns:
        List of column metadata dictionaries
    """
    db_type = database_type.lower()
    
    if db_type in ('postgresql', 'postgres'):
        return pg_get_table_metadata(table_name)
    elif db_type in ('mssql', 'sqlserver'):
        return mssql_get_table_metadata(table_name)
    else:
        raise ValueError(f"Unsupported database type: {database_type}")


def get_schema(database_type: DatabaseType) -> str:
    """
    Get the configured schema for the specified database type.
    
    Args:
        database_type: Type of database
        
    Returns:
        Schema name
    """
    db_type = database_type.lower()
    
    if db_type in ('postgresql', 'postgres'):
        return Config.POSTGRES_SCHEMA
    elif db_type in ('mssql', 'sqlserver'):
        return Config.MSSQL_SCHEMA
    else:
        raise ValueError(f"Unsupported database type: {database_type}")


def get_quote_char(database_type: DatabaseType) -> tuple[str, str]:
    """
    Get the identifier quote characters for the specified database type.
    
    Args:
        database_type: Type of database
        
    Returns:
        Tuple of (open_quote, close_quote)
    """
    db_type = database_type.lower()
    
    if db_type in ('postgresql', 'postgres'):
        return ('"', '"')
    elif db_type in ('mssql', 'sqlserver'):
        return ('[', ']')
    else:
        raise ValueError(f"Unsupported database type: {database_type}")


def normalize_database_type(database_type: str) -> str:
    """
    Normalize database type string to a standard form.
    
    Args:
        database_type: Input database type string
        
    Returns:
        Normalized database type ('postgresql' or 'mssql')
    """
    db_type = database_type.lower()
    
    if db_type in ('postgresql', 'postgres'):
        return 'postgresql'
    elif db_type in ('mssql', 'sqlserver'):
        return 'mssql'
    else:
        raise ValueError(f"Unsupported database type: {database_type}")
