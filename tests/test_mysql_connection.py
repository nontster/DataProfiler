"""
Unit tests for MySQL connection functions.
"""

import unittest
from unittest.mock import patch, MagicMock
import sys

# Mock mysql.connector before importing src.db.mysql to avoid ImportError if driver missing
mock_mysql = MagicMock()
class MockError(Exception): pass
mock_mysql.connector.Error = MockError
sys.modules['mysql'] = mock_mysql
sys.modules['mysql.connector'] = mock_mysql.connector

from src.db.mysql import get_mysql_connection, table_exists, get_table_metadata
from src.exceptions import DatabaseConnectionError, TableNotFoundError
from src.config import Config

class TestMySQLConnection(unittest.TestCase):
    """Test cases for MySQL connection."""

    @patch('src.db.mysql.mysql.connector.connect')
    def test_successful_connection(self, mock_connect):
        """Test successful MySQL connection."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        
        conn = get_mysql_connection()
        
        self.assertEqual(conn, mock_conn)
        mock_connect.assert_called_once()
        # Verify default DB is used
        call_kwargs = mock_connect.call_args[1]
        self.assertEqual(call_kwargs['database'], Config.MYSQL_DATABASE)

    @patch('src.db.mysql.mysql.connector.connect')
    def test_connection_with_custom_db(self, mock_connect):
        """Test connection with custom database."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        
        get_mysql_connection(database="custom_db")
        
        call_kwargs = mock_connect.call_args[1]
        self.assertEqual(call_kwargs['database'], "custom_db")

    @patch('src.db.mysql.mysql.connector.connect')
    def test_connection_failure_raises_exception(self, mock_connect):
        """Test that connection failure raises DatabaseConnectionError."""
        from mysql.connector import Error
        mock_connect.side_effect = Error("Connection refused")
        
        with self.assertRaises(DatabaseConnectionError):
            get_mysql_connection()

    @patch('src.db.mysql.get_mysql_connection')
    def test_table_exists_true(self, mock_get_conn):
        """Test table_exists returns True when table exists."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (1,)  # Count > 0
        mock_get_conn.return_value = mock_conn
        
        exists = table_exists('users', schema='prod')
        
        self.assertTrue(exists)
        mock_cursor.execute.assert_called()
        # Check that schema was used as table_schema
        args = mock_cursor.execute.call_args[0]
        self.assertIn('prod', args[1])

    @patch('src.db.mysql.get_mysql_connection')
    def test_table_exists_false(self, mock_get_conn):
        """Test table_exists returns False when table missing."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (0,)  # Count == 0
        mock_get_conn.return_value = mock_conn
        
        exists = table_exists('missing_table')
        
        self.assertFalse(exists)

    @patch('src.db.mysql.get_mysql_connection')
    @patch('src.db.mysql.table_exists')
    def test_get_table_metadata(self, mock_table_exists, mock_get_conn):
        """Test getting table metadata."""
        mock_table_exists.return_value = True
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        # Mock column return: name, type
        mock_cursor.fetchall.return_value = [
            ('id', 'int'),
            ('username', 'varchar'),
        ]
        mock_get_conn.return_value = mock_conn
        
        columns = get_table_metadata('users', schema='prod')
        
        self.assertEqual(len(columns), 2)
        self.assertEqual(columns[0]['name'], 'id')
        self.assertEqual(columns[1]['type'], 'varchar')

if __name__ == '__main__':
    unittest.main()
