import unittest
from unittest.mock import MagicMock
from src.db.schema_extractor import MySQLSchemaExtractor
from src.core.schema_comparator import ColumnSchema

class TestMySQLSchemaExtractorBytes(unittest.TestCase):
    def test_byte_decoding(self):
        # Mock connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Initialize extractor
        extractor = MySQLSchemaExtractor(mock_conn)

        # 1. Test Column Extraction
        # Mock return values as BYTES
        # col_name, data_type, nullable, default, max_len, precision, scale, col_type
        mock_cursor.fetchall.return_value = [
            (b'id', b'int', b'NO', None, None, None, None, b'int(11)'),
            (b'name', b'varchar', b'YES', b'NULL', 100, None, None, b'varchar(100)'),
        ]
        
        columns = extractor._extract_columns('users', 'prod')
        
        self.assertIsInstance(columns['id'].name, str)
        self.assertEqual(columns['id'].name, 'id')
        self.assertIsInstance(columns['id'].data_type, str)
        self.assertEqual(columns['id'].data_type, 'int(11)')
        
        self.assertIsInstance(columns['name'].name, str)
        self.assertEqual(columns['name'].name, 'name')
        self.assertIsInstance(columns['name'].default_value, str)
        self.assertEqual(columns['name'].default_value, 'NULL')

        # 2. Test Primary Key Extraction
        mock_cursor.fetchall.return_value = [(b'id',)]
        pk = extractor._extract_primary_key('users', 'prod')
        
        self.assertIsInstance(pk[0], str)
        self.assertEqual(pk[0], 'id')

        # 3. Test Index Extraction
        # idx_name, col_name, non_unique, idx_type
        mock_cursor.fetchall.return_value = [
            (b'idx_name', b'name', 1, b'BTREE')
        ]
        indexes = extractor._extract_indexes('users', 'prod')
        
        self.assertIsInstance(indexes[0].name, str)
        self.assertEqual(indexes[0].name, 'idx_name')
        self.assertIsInstance(indexes[0].columns[0], str)
        self.assertEqual(indexes[0].columns[0], 'name')
        self.assertIsInstance(indexes[0].index_type, str)
        self.assertEqual(indexes[0].index_type, 'BTREE')

        # 4. Test Foreign Key Extraction
        # fk_name, col_name, ref_table, ref_col, on_delete, on_update
        mock_cursor.fetchall.return_value = [
            (b'fk_user_role', b'role_id', b'roles', b'id', b'CASCADE', b'RESTRICT')
        ]
        fks = extractor._extract_foreign_keys('users', 'prod')
        
        self.assertIsInstance(fks[0].name, str)
        self.assertEqual(fks[0].name, 'fk_user_role')
        self.assertIsInstance(fks[0].columns[0], str)
        self.assertEqual(fks[0].columns[0], 'role_id')
        self.assertIsInstance(fks[0].referenced_table, str)
        self.assertEqual(fks[0].referenced_table, 'roles')
        self.assertIsInstance(fks[0].referenced_columns[0], str)
        self.assertEqual(fks[0].referenced_columns[0], 'id')
        self.assertIsInstance(fks[0].on_delete, str)
        self.assertEqual(fks[0].on_delete, 'CASCADE')

if __name__ == '__main__':
    unittest.main()
