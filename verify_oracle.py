
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from src.db.oracle import get_oracle_connection, table_exists, get_table_metadata, list_tables
from src.db.connection_factory import get_connection, normalize_database_type
from src.db.schema_extractor import OracleSchemaExtractor
from src.core.metrics import calculate_column_metrics, get_row_count
from src.config import Config

class TestOracleSupport(unittest.TestCase):

    @patch('src.db.oracle.oracledb')
    def test_connection(self, mock_oracledb):
        """Test Oracle connection creation."""
        mock_conn = MagicMock()
        mock_oracledb.connect.return_value = mock_conn
        
        conn = get_oracle_connection()
        
        self.assertEqual(conn, mock_conn)
        mock_oracledb.connect.assert_called_once()
    
    @patch('src.db.oracle.get_oracle_connection')
    def test_list_tables(self, mock_get_conn):
        """Test listing tables."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_get_conn.return_value = mock_conn
        
        # Mock result
        mock_cur.fetchall.return_value = [('TABLE1',), ('TABLE2',)]
        
        tables = list_tables()
        
        self.assertEqual(tables, ['TABLE1', 'TABLE2'])
        # Verify query uses all_tables
        self.assertIn('all_tables', mock_cur.execute.call_args[0][0].lower())

    @patch('src.db.connection_factory.get_oracle_connection')
    def test_factory_dispatch(self, mock_get_conn):
        """Test connection factory dispatches to Oracle."""
        get_connection('oracle')
        mock_get_conn.assert_called_once()

    def test_normalize_type(self):
        """Test type normalization."""
        self.assertEqual(normalize_database_type('oracle'), 'oracle')
        self.assertEqual(normalize_database_type('ORACLE'), 'oracle')

    @patch('src.db.schema_extractor.OracleSchemaExtractor._extract_columns')
    @patch('src.db.schema_extractor.OracleSchemaExtractor._extract_primary_key')
    @patch('src.db.schema_extractor.OracleSchemaExtractor._extract_indexes')
    @patch('src.db.schema_extractor.OracleSchemaExtractor._extract_foreign_keys')
    @patch('src.db.schema_extractor.OracleSchemaExtractor._extract_check_constraints')
    def test_schema_extractor(self, mock_check, mock_fk, mock_idx, mock_pk, mock_cols):
        """Test schema extractor structure."""
        mock_conn = MagicMock()
        extractor = OracleSchemaExtractor(mock_conn)
        
        # Setup mocks
        mock_cols.return_value = {}
        mock_pk.return_value = None
        mock_idx.return_value = []
        mock_fk.return_value = []
        mock_check.return_value = []
        
        schema = extractor.extract_table_schema('TEST_TABLE')
        
        self.assertEqual(schema.table_name, 'TEST_TABLE')
        self.assertEqual(schema.database_name, Config.ORACLE_SERVICE_NAME)
        # Verify it called the extraction methods
        mock_cols.assert_called_once()

    @patch('src.core.metrics.get_connection')
    def test_row_count_oracle(self, mock_get_conn):
        """Test row count uses num_rows from all_tables."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_get_conn.return_value = mock_conn
        
        mock_cur.fetchone.return_value = (100,)
        
        count = get_row_count('TEST_TABLE', 'oracle')
        
        self.assertEqual(count, 100)
        # Check query looks for num_rows in all_tables
        query = mock_cur.execute.call_args[0][0].lower()
        self.assertIn('num_rows', query)
        self.assertIn('all_tables', query)

if __name__ == '__main__':
    unittest.main()
