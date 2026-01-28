"""
MySQL database connection and operations.
"""

import logging
from typing import Optional

import mysql.connector
from mysql.connector import Error

from src.config import Config
from src.exceptions import DatabaseConnectionError, TableNotFoundError

logger = logging.getLogger(__name__)


def get_mysql_connection(database: Optional[str] = None):
    """
    Create and return a MySQL connection with error handling.
    
    Args:
        database: Optional database name to connect to (overrides config)
    
    Returns:
        mysql.connector.connection: Database connection object
        
    Raises:
        DatabaseConnectionError: If connection fails
    """
    try:
        # Use provided database or fall back to config default
        target_db = database if database else Config.MYSQL_DATABASE
        
        conn = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            port=Config.MYSQL_PORT,
            database=target_db,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            connection_timeout=10
        )
        # Ensure we are actually using the target database if connect didn't select it 
        # (though the arg above should handle it)
        if database and conn.is_connected():
            cursor = conn.cursor()
            cursor.execute(f"USE {database}")
            cursor.close()
            
        logger.debug(f"MySQL connection established (DB: {target_db})")
        return conn
    except Error as e:
        logger.error(f"Failed to connect to MySQL: {e}")
        raise DatabaseConnectionError(f"MySQL connection failed: {e}")


def table_exists(table_name: str, schema: Optional[str] = None) -> bool:
    """
    Check if a table exists in the MySQL database.
    
    Args:
        table_name: Name of the table to check
        schema: Optional schema (database) name (defaults to Config.MYSQL_DATABASE)
        
    Returns:
        bool: True if table exists, False otherwise
    """
    try:
        # For MySQL, schema is synonymous with database
        target_db = schema or Config.MYSQL_DATABASE
        
        # We need to connect to a DB to run queries, use target_db or default
        conn = get_mysql_connection(database=target_db)
        cursor = conn.cursor()
        
        query = """
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_name = %s AND table_schema = %s
        """
        cursor.execute(query, (table_name, target_db))
        count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return count > 0
    except (Error, DatabaseConnectionError) as e:
        logger.error(f"Error checking table existence: {e}")
        return False


def get_table_metadata(table_name: str, schema: Optional[str] = None) -> list[dict]:
    """
    Retrieve column metadata for a given table.
    
    Args:
        table_name: Name of the table to get metadata for
        schema: Optional schema (database) name (defaults to Config.MYSQL_DATABASE)
        
    Returns:
        List of dictionaries with 'name' and 'type' keys
        
    Raises:
        TableNotFoundError: If the table doesn't exist
        DatabaseConnectionError: If connection fails
    """
    target_db = schema or Config.MYSQL_DATABASE
    
    # Validate table exists first
    if not table_exists(table_name, target_db):
        raise TableNotFoundError(
            f"Table '{table_name}' not found in database '{target_db}'"
        )
    
    try:
        conn = get_mysql_connection(database=target_db)
        cursor = conn.cursor()
        
        query = """
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = %s AND table_schema = %s
            ORDER BY ordinal_position
        """
        cursor.execute(query, (table_name, target_db))
        columns = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        logger.info(f"Found {len(columns)} columns in table '{target_db}.{table_name}'")
        
        result = []
        for col in columns:
            col_name = col[0].decode('utf-8') if isinstance(col[0], bytes) else col[0]
            col_type = col[1].decode('utf-8') if isinstance(col[1], bytes) else col[1]
            result.append({"name": col_name, "type": col_type})
            
        return result
        
    except (Error, DatabaseConnectionError) as e:
        logger.error(f"Error fetching metadata for '{table_name}': {e}")
        raise DatabaseConnectionError(f"Failed to fetch metadata: {e}")
