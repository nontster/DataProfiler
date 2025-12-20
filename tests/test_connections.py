"""
Unit tests for database connection functions.
"""

import os
import unittest
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_and_scan import (
    get_postgres_connection,
    get_clickhouse_client,
    DatabaseConnectionError
)


class TestPostgresConnection(unittest.TestCase):
    """Test cases for PostgreSQL connection."""

    @patch('generate_and_scan.psycopg2.connect')
    def test_successful_connection(self, mock_connect):
        """Test successful PostgreSQL connection."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        
        conn = get_postgres_connection()
        
        self.assertEqual(conn, mock_conn)
        mock_connect.assert_called_once()

    @patch('generate_and_scan.psycopg2.connect')
    def test_connection_failure_raises_exception(self, mock_connect):
        """Test that connection failure raises DatabaseConnectionError."""
        from psycopg2 import OperationalError
        mock_connect.side_effect = OperationalError("Connection refused")
        
        with self.assertRaises(DatabaseConnectionError) as context:
            get_postgres_connection()
        
        self.assertIn("PostgreSQL connection failed", str(context.exception))

    @patch('generate_and_scan.psycopg2.connect')
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

    @patch('generate_and_scan.clickhouse_connect.get_client')
    def test_successful_connection(self, mock_get_client):
        """Test successful ClickHouse connection."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        client = get_clickhouse_client()
        
        self.assertEqual(client, mock_client)
        mock_get_client.assert_called_once()

    @patch('generate_and_scan.clickhouse_connect.get_client')
    def test_connection_failure_raises_exception(self, mock_get_client):
        """Test that connection failure raises DatabaseConnectionError."""
        from clickhouse_connect.driver.exceptions import ClickHouseError
        mock_get_client.side_effect = ClickHouseError("Connection refused")
        
        with self.assertRaises(DatabaseConnectionError) as context:
            get_clickhouse_client()
        
        self.assertIn("ClickHouse connection failed", str(context.exception))


if __name__ == '__main__':
    unittest.main()
