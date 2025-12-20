"""
Integration tests for the run_profiler function.
These tests use mocking to avoid needing actual database connections.
"""

import os
import unittest
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_and_scan import (
    run_profiler,
    TableNotFoundError,
    DatabaseConnectionError
)


class TestRunProfiler(unittest.TestCase):
    """Test cases for run_profiler function."""

    @patch('generate_and_scan.get_clickhouse_client')
    @patch('generate_and_scan.get_table_metadata')
    @patch('generate_and_scan.init_clickhouse')
    def test_returns_none_when_clickhouse_init_fails(self, mock_init_ch, mock_get_meta, mock_get_ch):
        """Test that run_profiler returns None when ClickHouse init fails."""
        mock_init_ch.return_value = False
        
        result = run_profiler('users')
        
        self.assertIsNone(result)
        mock_get_meta.assert_not_called()

    @patch('generate_and_scan.get_table_metadata')
    @patch('generate_and_scan.init_clickhouse')
    def test_returns_none_when_table_not_found(self, mock_init_ch, mock_get_meta):
        """Test that run_profiler returns None when table not found."""
        mock_init_ch.return_value = True
        mock_get_meta.side_effect = TableNotFoundError("Table not found")
        
        result = run_profiler('nonexistent')
        
        self.assertIsNone(result)

    @patch('generate_and_scan.get_table_metadata')
    @patch('generate_and_scan.init_clickhouse')
    def test_returns_zero_when_no_columns(self, mock_init_ch, mock_get_meta):
        """Test that run_profiler returns 0 when no columns found."""
        mock_init_ch.return_value = True
        mock_get_meta.return_value = []
        
        result = run_profiler('empty_table')
        
        self.assertEqual(result, 0)

    @patch('generate_and_scan.get_table_metadata')
    @patch('generate_and_scan.init_clickhouse')
    def test_returns_zero_when_all_columns_unsupported(self, mock_init_ch, mock_get_meta):
        """Test that run_profiler returns 0 when all columns are unsupported types."""
        mock_init_ch.return_value = True
        mock_get_meta.return_value = [
            {'name': 'created_at', 'type': 'timestamp'},
            {'name': 'is_active', 'type': 'boolean'},
        ]
        
        result = run_profiler('timestamp_only_table')
        
        self.assertEqual(result, 0)

    @patch('generate_and_scan.Scan')
    @patch('generate_and_scan.get_clickhouse_client')
    @patch('generate_and_scan.get_table_metadata')
    @patch('generate_and_scan.init_clickhouse')
    def test_successful_profiling(self, mock_init_ch, mock_get_meta, mock_get_ch, mock_scan_class):
        """Test successful profiling workflow."""
        mock_init_ch.return_value = True
        mock_get_meta.return_value = [
            {'name': 'id', 'type': 'integer'},
            {'name': 'name', 'type': 'character varying'},
        ]
        
        # Mock the Scan object
        mock_scan = MagicMock()
        mock_scan.get_scan_results.return_value = {
            'profiling': [{
                'table': 'users',
                'columnProfiles': [
                    {
                        'columnName': 'id',
                        'profile': {
                            'distinct': 10,
                            'missing_count': 0,
                            'min': 1,
                            'max': 10,
                            'avg': 5.5
                        }
                    },
                    {
                        'columnName': 'name',
                        'profile': {
                            'distinct': 10,
                            'missing_count': 0,
                            'min': None,
                            'max': None,
                            'avg': None
                        }
                    }
                ]
            }]
        }
        mock_scan_class.return_value = mock_scan
        
        # Mock ClickHouse client
        mock_ch_client = MagicMock()
        mock_get_ch.return_value = mock_ch_client
        
        result = run_profiler('users')
        
        self.assertEqual(result, 2)
        mock_ch_client.insert.assert_called_once()

    @patch('generate_and_scan.Scan')
    @patch('generate_and_scan.get_table_metadata')
    @patch('generate_and_scan.init_clickhouse')
    def test_returns_zero_when_no_profiling_data(self, mock_init_ch, mock_get_meta, mock_scan_class):
        """Test that run_profiler returns 0 when no profiling data collected."""
        mock_init_ch.return_value = True
        mock_get_meta.return_value = [
            {'name': 'id', 'type': 'integer'},
        ]
        
        mock_scan = MagicMock()
        mock_scan.get_scan_results.return_value = {}  # No profiling data
        mock_scan_class.return_value = mock_scan
        
        result = run_profiler('users')
        
        self.assertEqual(result, 0)


if __name__ == '__main__':
    unittest.main()
