"""
Auto-increment column detection and monitoring for PostgreSQL.

Provides functions to discover SERIAL/BIGSERIAL/IDENTITY columns
and query their current sequence values for overflow risk assessment.
"""

import logging
from typing import Optional
from abc import ABC, abstractmethod

from src.db.postgres import get_postgres_connection
from src.config import Config
from src.exceptions import DatabaseConnectionError

logger = logging.getLogger(__name__)


# Maximum values for PostgreSQL integer types
TYPE_MAX_VALUES = {
    'smallint': 32767,
    'integer': 2147483647,
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
            max_value = TYPE_MAX_VALUES.get(data_type, TYPE_MAX_VALUES['bigint'])
            
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
        # Future implementations:
        # 'mysql': MySQLAutoIncrementDetector,
        # 'oracle': OracleAutoIncrementDetector,
        # 'mssql': MSSQLAutoIncrementDetector,
    }
    
    detector_class = detectors.get(database_type.lower())
    if detector_class is None:
        supported = ', '.join(detectors.keys())
        raise ValueError(f"Unsupported database type: {database_type}. Supported: {supported}")
    
    return detector_class()
