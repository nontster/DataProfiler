"""
Integration tests for the run_profiler function.
These tests use mocking to avoid needing actual database connections.
"""

import unittest
from unittest.mock import patch, MagicMock

from src.core.profiler import run_profiler, extract_profiling_results, generate_sodacl_yaml
from src.exceptions import TableNotFoundError, DatabaseConnectionError


class TestGenerateSodaclYaml(unittest.TestCase):
    """Test cases for generate_sodacl_yaml function."""

    def test_generates_valid_yaml(self):
        """Test that generate_sodacl_yaml produces valid YAML content."""
        columns = [{'name': 'id', 'type': 'integer'}, {'name': 'name', 'type': 'varchar'}]
        result = generate_sodacl_yaml('users', columns)
        
        self.assertIn('checks for users', result)
        self.assertIn('row_count > 0', result)
        self.assertIn('users.id', result)
        self.assertIn('users.name', result)

    def test_empty_columns_list(self):
        """Test with empty columns list."""
        result = generate_sodacl_yaml('users', [])
        
        self.assertIn('checks for users', result)
        self.assertNotIn('users.', result.split('profile columns')[1] if 'profile columns' in result else '')


class TestExtractProfilingResults(unittest.TestCase):
    """Test cases for extract_profiling_results function."""

    def test_extracts_results_correctly(self):
        """Test that profiling results are extracted correctly."""
        scan_results = {
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
                    }
                ]
            }]
        }
        
        records = extract_profiling_results(scan_results)
        
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['table_name'], 'users')
        self.assertEqual(records[0]['column_name'], 'id')
        self.assertEqual(records[0]['distinct_count'], 10)

    def test_empty_results(self):
        """Test with empty scan results."""
        records = extract_profiling_results({})
        self.assertEqual(records, [])

    def test_no_profiling_key(self):
        """Test with results missing profiling key."""
        records = extract_profiling_results({'other': 'data'})
        self.assertEqual(records, [])


class TestRunProfiler(unittest.TestCase):
    """Test cases for run_profiler function."""

    @patch('src.core.profiler.insert_profiles')
    @patch('src.core.profiler.get_table_metadata')
    @patch('src.core.profiler.init_clickhouse')
    def test_returns_none_when_clickhouse_init_fails(self, mock_init_ch, mock_get_meta, mock_insert):
        """Test that run_profiler returns None when ClickHouse init fails."""
        mock_init_ch.return_value = False
        
        result = run_profiler('users')
        
        self.assertIsNone(result)
        mock_get_meta.assert_not_called()

    @patch('src.core.profiler.get_table_metadata')
    @patch('src.core.profiler.init_clickhouse')
    def test_returns_none_when_table_not_found(self, mock_init_ch, mock_get_meta):
        """Test that run_profiler returns None when table not found."""
        mock_init_ch.return_value = True
        mock_get_meta.side_effect = TableNotFoundError("Table not found")
        
        result = run_profiler('nonexistent')
        
        self.assertIsNone(result)

    @patch('src.core.profiler.get_table_metadata')
    @patch('src.core.profiler.init_clickhouse')
    def test_returns_zero_when_no_columns(self, mock_init_ch, mock_get_meta):
        """Test that run_profiler returns 0 when no columns found."""
        mock_init_ch.return_value = True
        mock_get_meta.return_value = []
        
        result = run_profiler('empty_table')
        
        self.assertEqual(result, 0)

    @patch('src.core.profiler.get_table_metadata')
    @patch('src.core.profiler.init_clickhouse')
    def test_returns_zero_when_all_columns_unsupported(self, mock_init_ch, mock_get_meta):
        """Test that run_profiler returns 0 when all columns are unsupported types."""
        mock_init_ch.return_value = True
        mock_get_meta.return_value = [
            {'name': 'created_at', 'type': 'timestamp'},
            {'name': 'is_active', 'type': 'boolean'},
        ]
        
        result = run_profiler('timestamp_only_table')
        
        self.assertEqual(result, 0)

    @patch('src.core.profiler.Scan')
    @patch('src.core.profiler.insert_profiles')
    @patch('src.core.profiler.get_table_metadata')
    @patch('src.core.profiler.init_clickhouse')
    def test_successful_profiling(self, mock_init_ch, mock_get_meta, mock_insert, mock_scan_class):
        """Test successful profiling workflow."""
        mock_init_ch.return_value = True
        mock_get_meta.return_value = [
            {'name': 'id', 'type': 'integer'},
            {'name': 'name', 'type': 'character varying'},
        ]
        mock_insert.return_value = True
        
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
        
        result = run_profiler('users')
        
        self.assertEqual(result, 2)
        mock_insert.assert_called_once()

    @patch('src.core.profiler.Scan')
    @patch('src.core.profiler.get_table_metadata')
    @patch('src.core.profiler.init_clickhouse')
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
