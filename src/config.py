"""
Centralized configuration management.
Loads configuration from environment variables.
"""

import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


class Config:
    """Centralized configuration management."""
    
    # PostgreSQL Configuration
    POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
    POSTGRES_PORT = int(os.getenv('POSTGRES_PORT', 5432))
    POSTGRES_DATABASE = os.getenv('POSTGRES_DATABASE', 'postgres')
    POSTGRES_USER = os.getenv('POSTGRES_USER', 'postgres')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', '')
    POSTGRES_SCHEMA = os.getenv('POSTGRES_SCHEMA', 'public')
    
    # ClickHouse Configuration
    CLICKHOUSE_HOST = os.getenv('CLICKHOUSE_HOST', 'localhost')
    CLICKHOUSE_PORT = int(os.getenv('CLICKHOUSE_PORT', 8123))
    CLICKHOUSE_USER = os.getenv('CLICKHOUSE_USER', 'default')
    CLICKHOUSE_PASSWORD = os.getenv('CLICKHOUSE_PASSWORD', '')
    
    # MSSQL Configuration
    MSSQL_HOST = os.getenv('MSSQL_HOST', 'localhost')
    MSSQL_PORT = int(os.getenv('MSSQL_PORT', 1433))
    MSSQL_DATABASE = os.getenv('MSSQL_DATABASE', 'master')
    MSSQL_USER = os.getenv('MSSQL_USER', 'sa')
    MSSQL_PASSWORD = os.getenv('MSSQL_PASSWORD', '')
    MSSQL_SCHEMA = os.getenv('MSSQL_SCHEMA', 'dbo')
    
    # Metrics Storage Configuration
    METRICS_BACKEND = os.getenv('METRICS_BACKEND', 'clickhouse')  # 'clickhouse' or 'postgresql'
    
    # PostgreSQL Metrics Configuration (defaults to same as source PostgreSQL)
    PG_METRICS_HOST = os.getenv('PG_METRICS_HOST', os.getenv('POSTGRES_HOST', 'localhost'))
    PG_METRICS_PORT = int(os.getenv('PG_METRICS_PORT', os.getenv('POSTGRES_PORT', 5432)))
    PG_METRICS_DATABASE = os.getenv('PG_METRICS_DATABASE', os.getenv('POSTGRES_DATABASE', 'postgres'))
    PG_METRICS_USER = os.getenv('PG_METRICS_USER', os.getenv('POSTGRES_USER', 'postgres'))
    PG_METRICS_PASSWORD = os.getenv('PG_METRICS_PASSWORD', os.getenv('POSTGRES_PASSWORD', ''))
    
    @classmethod
    def validate(cls) -> bool:
        """
        Validate required configuration.
        
        Returns:
            bool: True if configuration is valid
        """
        required = ['POSTGRES_PASSWORD', 'CLICKHOUSE_PASSWORD']
        missing = [key for key in required if not getattr(cls, key)]
        
        if missing:
            logger.warning(f"Missing recommended config: {', '.join(missing)}")
        
        return True
    
    @classmethod
    def get_postgres_config(cls) -> dict:
        """Get PostgreSQL configuration as dictionary."""
        return {
            'host': cls.POSTGRES_HOST,
            'port': cls.POSTGRES_PORT,
            'database': cls.POSTGRES_DATABASE,
            'user': cls.POSTGRES_USER,
            'password': cls.POSTGRES_PASSWORD,
        }
    
    @classmethod
    def get_clickhouse_config(cls) -> dict:
        """Get ClickHouse configuration as dictionary."""
        return {
            'host': cls.CLICKHOUSE_HOST,
            'port': cls.CLICKHOUSE_PORT,
            'username': cls.CLICKHOUSE_USER,
            'password': cls.CLICKHOUSE_PASSWORD,
        }
    
    @classmethod
    def get_mssql_config(cls) -> dict:
        """Get MSSQL configuration as dictionary."""
        return {
            'server': cls.MSSQL_HOST,
            'port': cls.MSSQL_PORT,
            'database': cls.MSSQL_DATABASE,
            'user': cls.MSSQL_USER,
            'password': cls.MSSQL_PASSWORD,
        }

