"""
Unit tests for metadata discovery functions.
"""

import os
import unittest
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_and_scan import (
    table_exists,
    get_table_metadata,
    is_profile_supported,
    TableNotFoundError,
    DatabaseConnectionError
)


class TestIsProfileSupported(unittest.TestCase):
    """Test cases for is_profile_supported function."""

    def test_integer_is_supported(self):
        """Test that integer type is supported."""
        self.assertTrue(is_profile_supported('integer'))

    def test_varchar_is_supported(self):
        """Test that varchar type is supported."""
        self.assertTrue(is_profile_supported('character varying'))

    def test_numeric_is_supported(self):
        """Test that numeric type is supported."""
        self.assertTrue(is_profile_supported('numeric'))

    def test_text_is_supported(self):
        """Test that text type is supported."""
        self.assertTrue(is_profile_supported('text'))

    def test_timestamp_not_supported(self):
        """Test that timestamp type is not supported."""
        self.assertFalse(is_profile_supported('timestamp'))

    def test_timestamp_without_timezone_not_supported(self):
        """Test that timestamp without time zone is not supported."""
        self.assertFalse(is_profile_supported('timestamp without time zone'))

    def test_date_not_supported(self):
        """Test that date type is not supported."""
        self.assertFalse(is_profile_supported('date'))

    def test_bytea_not_supported(self):
        """Test that bytea type is not supported."""
        self.assertFalse(is_profile_supported('bytea'))

    def test_boolean_not_supported(self):
        """Test that boolean type is not supported."""
        self.assertFalse(is_profile_supported('boolean'))


class TestTableExists(unittest.TestCase):
    """Test cases for table_exists function."""

    @patch('generate_and_scan.get_postgres_connection')
    def test_table_exists_returns_true(self, mock_get_conn):
        """Test that table_exists returns True for existing table."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (True,)
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn
        
        result = table_exists('users')
        
        self.assertTrue(result)
        mock_cursor.execute.assert_called_once()

    @patch('generate_and_scan.get_postgres_connection')
    def test_table_not_exists_returns_false(self, mock_get_conn):
        """Test that table_exists returns False for non-existing table."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (False,)
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn
        
        result = table_exists('nonexistent')
        
        self.assertFalse(result)

    @patch('generate_and_scan.get_postgres_connection')
    def test_connection_error_returns_false(self, mock_get_conn):
        """Test that connection error returns False."""
        from psycopg2 import OperationalError
        mock_get_conn.side_effect = OperationalError("Connection failed")
        
        result = table_exists('users')
        
        self.assertFalse(result)


class TestGetTableMetadata(unittest.TestCase):
    """Test cases for get_table_metadata function."""

    @patch('generate_and_scan.table_exists')
    @patch('generate_and_scan.get_postgres_connection')
    def test_returns_column_metadata(self, mock_get_conn, mock_table_exists):
        """Test that get_table_metadata returns correct column metadata."""
        mock_table_exists.return_value = True
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('id', 'integer'),
            ('name', 'character varying'),
            ('age', 'integer'),
        ]
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn
        
        result = get_table_metadata('users')
        
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], {'name': 'id', 'type': 'integer'})
        self.assertEqual(result[1], {'name': 'name', 'type': 'character varying'})
        self.assertEqual(result[2], {'name': 'age', 'type': 'integer'})

    @patch('generate_and_scan.table_exists')
    def test_table_not_found_raises_exception(self, mock_table_exists):
        """Test that TableNotFoundError is raised for non-existing table."""
        mock_table_exists.return_value = False
        
        with self.assertRaises(TableNotFoundError) as context:
            get_table_metadata('nonexistent')
        
        self.assertIn('nonexistent', str(context.exception))
        self.assertIn('not found', str(context.exception))

    @patch('generate_and_scan.table_exists')
    @patch('generate_and_scan.get_postgres_connection')
    def test_empty_table_returns_empty_list(self, mock_get_conn, mock_table_exists):
        """Test that empty table returns empty list."""
        mock_table_exists.return_value = True
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn
        
        result = get_table_metadata('empty_table')
        
        self.assertEqual(result, [])


if __name__ == '__main__':
    unittest.main()
