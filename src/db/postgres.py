"""
PostgreSQL database connection and operations.
"""

import logging
from typing import Optional

import psycopg2
from psycopg2 import OperationalError, ProgrammingError

from src.config import Config
from src.exceptions import DatabaseConnectionError, TableNotFoundError

logger = logging.getLogger(__name__)


def get_postgres_connection():
    """
    Create and return a PostgreSQL connection with error handling.
    
    Returns:
        psycopg2.connection: Database connection object
        
    Raises:
        DatabaseConnectionError: If connection fails
    """
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


def table_exists(table_name: str, schema: Optional[str] = None) -> bool:
    """
    Check if a table exists in the PostgreSQL database.
    
    Args:
        table_name: Name of the table to check
        schema: Optional schema name (defaults to Config.POSTGRES_SCHEMA)
        
    Returns:
        bool: True if table exists, False otherwise
    """
    try:
        conn = get_postgres_connection()
        cur = conn.cursor()
        
        target_schema = schema or Config.POSTGRES_SCHEMA or 'public'
        
        query = """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = %s AND table_schema = %s
            )
        """
        cur.execute(query, (table_name, target_schema))
        exists = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        return exists
    except (OperationalError, ProgrammingError) as e:
        logger.error(f"Error checking table existence: {e}")
        return False


def get_table_metadata(table_name: str, schema: Optional[str] = None) -> list[dict]:
    """
    Retrieve column metadata for a given table.
    
    Args:
        table_name: Name of the table to get metadata for
        schema: Optional schema name (defaults to Config.POSTGRES_SCHEMA)
        
    Returns:
        List of dictionaries with 'name' and 'type' keys
        
    Raises:
        TableNotFoundError: If the table doesn't exist
        DatabaseConnectionError: If connection fails
    """
    # Validate table exists first
    if not table_exists(table_name, schema):
        target_schema = schema or Config.POSTGRES_SCHEMA or 'public'
        raise TableNotFoundError(
            f"Table '{table_name}' not found in schema '{target_schema}'"
        )
    
    try:
        conn = get_postgres_connection()
        cur = conn.cursor()
        
        target_schema = schema or Config.POSTGRES_SCHEMA or 'public'
        
        query = """
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = %s AND table_schema = %s
            ORDER BY ordinal_position
        """
        cur.execute(query, (table_name, target_schema))
        columns = cur.fetchall()
        
        cur.close()
        conn.close()
        
        logger.info(f"Found {len(columns)} columns in table '{target_schema}.{table_name}'")
        return [{"name": col[0], "type": col[1]} for col in columns]
        
    except (OperationalError, ProgrammingError) as e:
        logger.error(f"Error fetching metadata for '{table_name}': {e}")
        raise DatabaseConnectionError(f"Failed to fetch metadata: {e}")
