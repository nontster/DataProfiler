"""
Oracle database connection and operations.
"""

import logging
from typing import Optional

import oracledb
from src.config import Config
from src.exceptions import DatabaseConnectionError, TableNotFoundError

logger = logging.getLogger(__name__)


def get_oracle_connection():
    """
    Create and return an Oracle connection with error handling.
    
    Returns:
        oracledb.Connection: Database connection object
        
    Raises:
        DatabaseConnectionError: If connection fails
    """
    try:
        # Use thin mode by default (doesn't require Instant Client)
        params = oracledb.ConnectParams(
            host=Config.ORACLE_HOST,
            port=Config.ORACLE_PORT,
            service_name=Config.ORACLE_SERVICE_NAME
        )
        
        conn = oracledb.connect(
            user=Config.ORACLE_USER,
            password=Config.ORACLE_PASSWORD,
            params=params
        )
        logger.debug("Oracle connection established")
        return conn
    except oracledb.Error as e:
        logger.error(f"Failed to connect to Oracle: {e}")
        raise DatabaseConnectionError(f"Oracle connection failed: {e}")


def table_exists(table_name: str, schema: Optional[str] = None) -> bool:
    """
    Check if a table exists in the Oracle database.
    
    Args:
        table_name: Name of the table to check
        schema: Optional schema name (defaults to Config.ORACLE_SCHEMA)
        
    Returns:
        bool: True if table exists, False otherwise
    """
    try:
        conn = get_oracle_connection()
        cur = conn.cursor()
        
        target_schema = (schema or Config.ORACLE_SCHEMA or 'USER').upper()
        target_table = table_name.upper()
        
        query = """
            SELECT COUNT(*) 
            FROM all_tables 
            WHERE table_name = :1 AND owner = :2
        """
        cur.execute(query, (target_table, target_schema))
        count = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        return count > 0
    except oracledb.Error as e:
        logger.error(f"Error checking table existence: {e}")
        return False


def get_table_metadata(table_name: str, schema: Optional[str] = None) -> list[dict]:
    """
    Retrieve column metadata for a given table.
    
    Args:
        table_name: Name of the table to get metadata for
        schema: Optional schema name (defaults to Config.ORACLE_SCHEMA)
        
    Returns:
        List of dictionaries with 'name' and 'type' keys
        
    Raises:
        TableNotFoundError: If the table doesn't exist
        DatabaseConnectionError: If connection fails
    """
    # Validate table exists first
    if not table_exists(table_name, schema):
        target_schema = schema or Config.ORACLE_SCHEMA or 'USER'
        raise TableNotFoundError(
            f"Table '{table_name}' not found in schema '{target_schema}'"
        )
    
    try:
        conn = get_oracle_connection()
        cur = conn.cursor()
        
        target_schema = (schema or Config.ORACLE_SCHEMA or 'USER').upper()
        target_table = table_name.upper()
        
        query = """
            SELECT column_name, data_type, data_length, data_precision, data_scale
            FROM all_tab_columns 
            WHERE table_name = :1 AND owner = :2
            ORDER BY column_id
        """
        cur.execute(query, (target_table, target_schema))
        columns = cur.fetchall()
        
        cur.close()
        conn.close()
        
        logger.info(f"Found {len(columns)} columns in table '{target_schema}.{table_name}'")
        
        # Format types similar to other DBs
        formatted_columns = []
        for col in columns:
            col_name = col[0]
            data_type = col[1].lower()
            
            formatted_columns.append({
                "name": col_name,
                "type": data_type
            })
            
        return formatted_columns
        
    except oracledb.Error as e:
        logger.error(f"Error fetching metadata for '{table_name}': {e}")
        raise DatabaseConnectionError(f"Failed to fetch metadata: {e}")


def list_tables(schema: Optional[str] = None, conn=None) -> list[str]:
    """
    List all tables in an Oracle schema.
    
    Args:
        schema: Schema name (defaults to Config.ORACLE_SCHEMA)
        conn: Optional existing connection
        
    Returns:
        Sorted list of table names
    """
    own_conn = conn is None
    try:
        if own_conn:
            conn = get_oracle_connection()
        cur = conn.cursor()
        
        target_schema = (schema or Config.ORACLE_SCHEMA or 'USER').upper()
        
        query = """
            SELECT table_name 
            FROM all_tables 
            WHERE owner = :1
            ORDER BY table_name
        """
        cur.execute(query, (target_schema,))
        tables = [row[0] for row in cur.fetchall()]
        
        cur.close()
        if own_conn:
            conn.close()
        
        logger.info(f"Found {len(tables)} tables in schema '{target_schema}'")
        return tables
        
    except oracledb.Error as e:
        logger.error(f"Error listing tables: {e}")
        raise DatabaseConnectionError(f"Failed to list tables: {e}")
