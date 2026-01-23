"""
Microsoft SQL Server database connection and operations.
"""

import logging
from typing import Optional

import pymssql

from src.config import Config
from src.exceptions import DatabaseConnectionError, TableNotFoundError

logger = logging.getLogger(__name__)


def get_mssql_connection():
    """
    Create and return a MSSQL connection with error handling.
    
    Returns:
        pymssql.Connection: Database connection object
        
    Raises:
        DatabaseConnectionError: If connection fails
    """
    try:
        conn = pymssql.connect(
            server=Config.MSSQL_HOST,
            port=Config.MSSQL_PORT,
            database=Config.MSSQL_DATABASE,
            user=Config.MSSQL_USER,
            password=Config.MSSQL_PASSWORD,
            login_timeout=10
        )
        logger.debug("MSSQL connection established")
        return conn
    except pymssql.Error as e:
        logger.error(f"Failed to connect to MSSQL: {e}")
        raise DatabaseConnectionError(f"MSSQL connection failed: {e}")


def table_exists(table_name: str, schema: Optional[str] = None) -> bool:
    """
    Check if a table exists in the MSSQL database.
    
    Args:
        table_name: Name of the table to check
        schema: Optional schema name (defaults to Config.MSSQL_SCHEMA)
        
    Returns:
        bool: True if table exists, False otherwise
    """
    try:
        conn = get_mssql_connection()
        cur = conn.cursor()
        
        target_schema = schema or Config.MSSQL_SCHEMA or 'dbo'
        
        query = """
            SELECT CASE WHEN EXISTS (
                SELECT 1 FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_NAME = %s AND TABLE_SCHEMA = %s
            ) THEN 1 ELSE 0 END
        """
        cur.execute(query, (table_name, target_schema))
        exists = cur.fetchone()[0] == 1
        
        cur.close()
        conn.close()
        
        return exists
    except pymssql.Error as e:
        logger.error(f"Error checking table existence: {e}")
        return False


def get_table_metadata(table_name: str, schema: Optional[str] = None) -> list[dict]:
    """
    Retrieve column metadata for a given table.
    
    Args:
        table_name: Name of the table to get metadata for
        schema: Optional schema name (defaults to Config.MSSQL_SCHEMA)
        
    Returns:
        List of dictionaries with 'name' and 'type' keys
        
    Raises:
        TableNotFoundError: If the table doesn't exist
        DatabaseConnectionError: If connection fails
    """
    # Validate table exists first
    if not table_exists(table_name, schema):
        target_schema = schema or Config.MSSQL_SCHEMA or 'dbo'
        raise TableNotFoundError(
            f"Table '{table_name}' not found in schema '{target_schema}'"
        )
    
    try:
        conn = get_mssql_connection()
        cur = conn.cursor()
        
        target_schema = schema or Config.MSSQL_SCHEMA or 'dbo'
        
        query = """
            SELECT COLUMN_NAME, DATA_TYPE 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = %s AND TABLE_SCHEMA = %s
            ORDER BY ORDINAL_POSITION
        """
        cur.execute(query, (table_name, target_schema))
        columns = cur.fetchall()
        
        cur.close()
        conn.close()
        
        logger.info(f"Found {len(columns)} columns in table '{target_schema}.{table_name}'")
        return [{"name": col[0], "type": col[1]} for col in columns]
        
    except pymssql.Error as e:
        logger.error(f"Error fetching metadata for '{table_name}': {e}")
        raise DatabaseConnectionError(f"Failed to fetch metadata: {e}")
