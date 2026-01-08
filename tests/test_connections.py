"""
Unit tests for database connection functions.
"""

import unittest
from unittest.mock import patch, MagicMock

from src.db.postgres import get_postgres_connection
from src.db.clickhouse import get_clickhouse_client
from src.exceptions import DatabaseConnectionError


class TestPostgresConnection(unittest.TestCase):
    """Test cases for PostgreSQL connection."""

    @patch('src.db.postgres.psycopg2.connect')
    def test_successful_connection(self, mock_connect):
        """Test successful PostgreSQL connection."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        
        conn = get_postgres_connection()
        
        self.assertEqual(conn, mock_conn)
        mock_connect.assert_called_once()

    @patch('src.db.postgres.psycopg2.connect')
    def test_connection_failure_raises_exception(self, mock_connect):
        """Test that connection failure raises DatabaseConnectionError."""
        from psycopg2 import OperationalError
        mock_connect.side_effect = OperationalError("Connection refused")
        
        with self.assertRaises(DatabaseConnectionError) as context:
            get_postgres_connection()
        
        self.assertIn("PostgreSQL connection failed", str(context.exception))

    @patch('src.db.postgres.psycopg2.connect')
    def test_connection_uses_config_values(self, mock_connect):
        """Test that connection uses Config values."""
        mock_connect.return_value = MagicMock()
        
        get_postgres_connection()
        
        call_kwargs = mock_connect.call_args[1]
        self.assertIn('host', call_kwargs)
        self.assertIn('port', call_kwargs)
        self.assertIn('database', call_kwargs)
        self.assertIn('user', call_kwargs)
        self.assertIn('password', call_kwargs)
        self.assertIn('connect_timeout', call_kwargs)


class TestClickHouseConnection(unittest.TestCase):
    """Test cases for ClickHouse connection."""

    @patch('src.db.clickhouse.clickhouse_connect.get_client')
    def test_successful_connection(self, mock_get_client):
        """Test successful ClickHouse connection."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        client = get_clickhouse_client()
        
        self.assertEqual(client, mock_client)
        mock_get_client.assert_called_once()

    @patch('src.db.clickhouse.clickhouse_connect.get_client')
    def test_connection_failure_raises_exception(self, mock_get_client):
        """Test that connection failure raises DatabaseConnectionError."""
        from clickhouse_connect.driver.exceptions import ClickHouseError
        mock_get_client.side_effect = ClickHouseError("Connection refused")
        
        with self.assertRaises(DatabaseConnectionError) as context:
            get_clickhouse_client()
        
        self.assertIn("ClickHouse connection failed", str(context.exception))


class TestMSSQLConnection(unittest.TestCase):
    """Test cases for MSSQL connection."""

    @patch('src.db.mssql.pymssql.connect')
    def test_successful_connection(self, mock_connect):
        """Test successful MSSQL connection."""
        from src.db.mssql import get_mssql_connection
        
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        
        conn = get_mssql_connection()
        
        self.assertEqual(conn, mock_conn)
        mock_connect.assert_called_once()

    @patch('src.db.mssql.pymssql.connect')
    def test_connection_failure_raises_exception(self, mock_connect):
        """Test that connection failure raises DatabaseConnectionError."""
        from src.db.mssql import get_mssql_connection
        import pymssql
        
        mock_connect.side_effect = pymssql.Error("Connection refused")
        
        with self.assertRaises(DatabaseConnectionError) as context:
            get_mssql_connection()
        
        self.assertIn("MSSQL connection failed", str(context.exception))

    @patch('src.db.mssql.pymssql.connect')
    def test_connection_uses_config_values(self, mock_connect):
        """Test that connection uses Config values."""
        from src.db.mssql import get_mssql_connection
        
        mock_connect.return_value = MagicMock()
        
        get_mssql_connection()
        
        call_kwargs = mock_connect.call_args[1]
        self.assertIn('server', call_kwargs)
        self.assertIn('port', call_kwargs)
        self.assertIn('database', call_kwargs)
        self.assertIn('user', call_kwargs)
        self.assertIn('password', call_kwargs)


if __name__ == '__main__':
    unittest.main()
