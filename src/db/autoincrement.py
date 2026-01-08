"""
Auto-increment column detection and monitoring for PostgreSQL.

Provides functions to discover SERIAL/BIGSERIAL/IDENTITY columns
and query their current sequence values for overflow risk assessment.
"""

import logging
from typing import Optional
from abc import ABC, abstractmethod

from src.db.postgres import get_postgres_connection
from src.db.mssql import get_mssql_connection
from src.config import Config
from src.exceptions import DatabaseConnectionError

logger = logging.getLogger(__name__)


# Maximum values for PostgreSQL integer types
POSTGRES_TYPE_MAX_VALUES = {
    'smallint': 32767,
    'integer': 2147483647,
    'bigint': 9223372036854775807,
}

# Maximum values for MSSQL integer types
MSSQL_TYPE_MAX_VALUES = {
    'tinyint': 255,
    'smallint': 32767,
    'int': 2147483647,
    'bigint': 9223372036854775807,
}


class AutoIncrementDetector(ABC):
    """Abstract base class for database-specific auto-increment detection."""
    
    @abstractmethod
    def get_autoincrement_columns(self, table_name: str) -> list[dict]:
        """Get all auto-increment columns for a table."""
        pass
    
    @abstractmethod
    def get_current_value(self, sequence_name: str) -> Optional[int]:
        """Get current value of an auto-increment sequence."""
        pass


class PostgreSQLAutoIncrementDetector(AutoIncrementDetector):
    """PostgreSQL implementation for SERIAL/BIGSERIAL/IDENTITY columns."""
    
    def __init__(self, schema: str = None):
        self.schema = schema or Config.POSTGRES_SCHEMA
    
    def get_autoincrement_columns(self, table_name: str) -> list[dict]:
        """
        Discover all auto-increment columns in a PostgreSQL table.
        
        Finds columns using SERIAL, BIGSERIAL, SMALLSERIAL, or IDENTITY.
        
        Args:
            table_name: Name of the table to inspect
            
        Returns:
            List of dicts with keys:
            - column_name: Name of the column
            - data_type: PostgreSQL data type (smallint, integer, bigint)
            - sequence_name: Full sequence name for querying current value
        """
        try:
            conn = get_postgres_connection()
            cur = conn.cursor()
            
            # Query to find columns with sequences (SERIAL types)
            # Also handles IDENTITY columns in PostgreSQL 10+
            query = """
                SELECT 
                    c.column_name,
                    c.data_type,
                    pg_get_serial_sequence(%s || '.' || %s, c.column_name) as sequence_name
                FROM information_schema.columns c
                WHERE c.table_name = %s 
                    AND c.table_schema = %s
                    AND (
                        c.column_default LIKE 'nextval%%'
                        OR c.is_identity = 'YES'
                    )
                ORDER BY c.ordinal_position
            """
            
            cur.execute(query, (self.schema, table_name, table_name, self.schema))
            rows = cur.fetchall()
            
            result = []
            for row in rows:
                column_name, data_type, sequence_name = row
                if sequence_name:  # Only include if we found a valid sequence
                    result.append({
                        'column_name': column_name,
                        'data_type': data_type.lower(),
                        'sequence_name': sequence_name,
                    })
                    logger.debug(f"Found auto-increment: {column_name} ({data_type}) -> {sequence_name}")
            
            cur.close()
            conn.close()
            
            logger.info(f"Found {len(result)} auto-increment columns in '{table_name}'")
            return result
            
        except Exception as e:
            logger.error(f"Error discovering auto-increment columns: {e}")
            raise DatabaseConnectionError(f"Failed to discover auto-increment columns: {e}")
    
    def get_current_value(self, sequence_name: str) -> Optional[int]:
        """
        Get the current (last used) value of a PostgreSQL sequence.
        
        Args:
            sequence_name: Full sequence name (schema.sequence_name format)
            
        Returns:
            Current sequence value, or None if not yet used
        """
        try:
            conn = get_postgres_connection()
            cur = conn.cursor()
            
            # Query the sequence directly for last_value
            # This works across all PostgreSQL versions
            # Format: SELECT last_value FROM schema.sequence_name
            query = f"SELECT last_value FROM {sequence_name}"
            
            cur.execute(query)
            row = cur.fetchone()
            
            cur.close()
            conn.close()
            
            if row is None:
                logger.warning(f"Sequence not found: {sequence_name}")
                return None
            
            last_value = row[0]
            
            # last_value of 1 could mean either:
            # - Sequence was never used (starts at 1)
            # - Sequence was used once
            # We return the value as-is since we can't distinguish reliably
            return last_value if last_value is not None else 0
            
        except Exception as e:
            logger.error(f"Error getting sequence value for {sequence_name}: {e}")
            return None
    
    def get_all_autoincrement_info(self, table_name: str) -> list[dict]:
        """
        Get complete auto-increment information including current values.
        
        Args:
            table_name: Name of the table to analyze
            
        Returns:
            List of dicts with column info and current/max values
        """
        columns = self.get_autoincrement_columns(table_name)
        
        result = []
        for col in columns:
            current_value = self.get_current_value(col['sequence_name'])
            data_type = col['data_type']
            max_value = POSTGRES_TYPE_MAX_VALUES.get(data_type, POSTGRES_TYPE_MAX_VALUES['bigint'])
            
            if current_value is not None:
                usage_percentage = (current_value / max_value) * 100
                remaining = max_value - current_value
            else:
                usage_percentage = 0.0
                remaining = max_value
                current_value = 0
            
            result.append({
                'table_name': table_name,
                'column_name': col['column_name'],
                'data_type': data_type,
                'sequence_name': col['sequence_name'],
                'current_value': current_value,
                'max_type_value': max_value,
                'usage_percentage': round(usage_percentage, 6),
                'remaining_values': remaining,
            })
        
        return result


class MSSQLAutoIncrementDetector(AutoIncrementDetector):
    """SQL Server implementation for IDENTITY columns."""
    
    def __init__(self, schema: str = None):
        self.schema = schema or Config.MSSQL_SCHEMA
    
    def get_autoincrement_columns(self, table_name: str) -> list[dict]:
        """
        Discover all IDENTITY columns in a SQL Server table.
        
        Args:
            table_name: Name of the table to inspect
            
        Returns:
            List of dicts with keys:
            - column_name: Name of the column
            - data_type: SQL Server data type (tinyint, smallint, int, bigint)
            - sequence_name: Full table.column reference for identification
        """
        try:
            conn = get_mssql_connection()
            cur = conn.cursor()
            
            # Query sys.identity_columns to find IDENTITY columns
            query = """
                SELECT 
                    c.name AS column_name,
                    t.name AS data_type,
                    CONCAT(%s, '.', %s, '.', c.name) AS sequence_name
                FROM sys.identity_columns ic
                INNER JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
                INNER JOIN sys.types t ON c.user_type_id = t.user_type_id
                WHERE ic.object_id = OBJECT_ID(CONCAT(%s, '.', %s))
                ORDER BY c.column_id
            """
            
            cur.execute(query, (self.schema, table_name, self.schema, table_name))
            rows = cur.fetchall()
            
            result = []
            for row in rows:
                column_name, data_type, sequence_name = row
                result.append({
                    'column_name': column_name,
                    'data_type': data_type.lower(),
                    'sequence_name': sequence_name,
                })
                logger.debug(f"Found IDENTITY column: {column_name} ({data_type})")
            
            cur.close()
            conn.close()
            
            logger.info(f"Found {len(result)} IDENTITY columns in '{table_name}'")
            return result
            
        except Exception as e:
            logger.error(f"Error discovering IDENTITY columns: {e}")
            raise DatabaseConnectionError(f"Failed to discover IDENTITY columns: {e}")
    
    def get_current_value(self, sequence_name: str) -> Optional[int]:
        """
        Get the current (last used) value of an IDENTITY column.
        
        Args:
            sequence_name: Full reference (schema.table.column format)
            
        Returns:
            Current IDENTITY value, or None if not yet used
        """
        try:
            # Parse sequence_name: schema.table.column
            parts = sequence_name.split('.')
            if len(parts) != 3:
                logger.error(f"Invalid sequence_name format: {sequence_name}")
                return None
            
            schema, table, column = parts
            
            conn = get_mssql_connection()
            cur = conn.cursor()
            
            # Use IDENT_CURRENT to get the last identity value
            query = f"SELECT IDENT_CURRENT('[{schema}].[{table}]')"
            
            cur.execute(query)
            row = cur.fetchone()
            
            cur.close()
            conn.close()
            
            if row is None or row[0] is None:
                logger.warning(f"No IDENTITY value found for: {sequence_name}")
                return None
            
            return int(row[0])
            
        except Exception as e:
            logger.error(f"Error getting IDENTITY value for {sequence_name}: {e}")
            return None
    
    def get_all_autoincrement_info(self, table_name: str) -> list[dict]:
        """
        Get complete IDENTITY column information including current values.
        
        Args:
            table_name: Name of the table to analyze
            
        Returns:
            List of dicts with column info and current/max values
        """
        columns = self.get_autoincrement_columns(table_name)
        
        result = []
        for col in columns:
            current_value = self.get_current_value(col['sequence_name'])
            data_type = col['data_type']
            max_value = MSSQL_TYPE_MAX_VALUES.get(data_type, MSSQL_TYPE_MAX_VALUES['bigint'])
            
            if current_value is not None:
                usage_percentage = (current_value / max_value) * 100
                remaining = max_value - current_value
            else:
                usage_percentage = 0.0
                remaining = max_value
                current_value = 0
            
            result.append({
                'table_name': table_name,
                'column_name': col['column_name'],
                'data_type': data_type,
                'sequence_name': col['sequence_name'],
                'current_value': current_value,
                'max_type_value': max_value,
                'usage_percentage': round(usage_percentage, 6),
                'remaining_values': remaining,
            })
        
        return result


def get_autoincrement_detector(database_type: str = 'postgresql') -> AutoIncrementDetector:
    """
    Factory function to get the appropriate auto-increment detector.
    
    Args:
        database_type: Type of database ('postgresql', 'mysql', 'oracle', 'mssql')
        
    Returns:
        AutoIncrementDetector instance for the specified database
        
    Raises:
        ValueError: If database type is not supported
    """
    detectors = {
        'postgresql': PostgreSQLAutoIncrementDetector,
        'postgres': PostgreSQLAutoIncrementDetector,
        'mssql': MSSQLAutoIncrementDetector,
        'sqlserver': MSSQLAutoIncrementDetector,
    }
    
    detector_class = detectors.get(database_type.lower())
    if detector_class is None:
        supported = ', '.join(detectors.keys())
        raise ValueError(f"Unsupported database type: {database_type}. Supported: {supported}")
    
    return detector_class()
