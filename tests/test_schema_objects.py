"""
Unit tests for schema objects extraction (stored procedures, views, triggers).

Tests cover:
- Data class creation and to_dict()
- PostgreSQL, MSSQL, MySQL extraction methods with mocked cursors
- run_schema_objects_profiler integration
"""

import hashlib
import unittest
from unittest.mock import patch, MagicMock

from src.core.schema_comparator import (
    StoredProcedureSchema,
    ViewSchema,
    TriggerSchema,
)
from src.db.schema_extractor import (
    _md5_hash,
    PostgresSchemaExtractor,
    MSSQLSchemaExtractor,
    MySQLSchemaExtractor,
)


# =============================================================================
# Helper
# =============================================================================

def _expected_md5(text: str) -> str:
    return hashlib.md5(text.encode('utf-8')).hexdigest()


# =============================================================================
# Data Class Tests
# =============================================================================

class TestStoredProcedureSchema(unittest.TestCase):

    def test_to_dict(self):
        sp = StoredProcedureSchema(
            name='get_users',
            schema_name='public',
            language='plpgsql',
            parameter_list='user_id integer',
            return_type='SETOF users',
            definition_hash='abc123',
        )
        d = sp.to_dict()
        self.assertEqual(d['name'], 'get_users')
        self.assertEqual(d['language'], 'plpgsql')
        self.assertEqual(d['definition_hash'], 'abc123')

    def test_defaults(self):
        sp = StoredProcedureSchema(name='fn', schema_name='public')
        self.assertEqual(sp.language, '')
        self.assertEqual(sp.definition_hash, '')


class TestViewSchema(unittest.TestCase):

    def test_to_dict(self):
        v = ViewSchema(
            name='active_users',
            schema_name='public',
            definition_hash='def456',
            is_materialized=True,
            columns='id,name,email',
        )
        d = v.to_dict()
        self.assertEqual(d['name'], 'active_users')
        self.assertTrue(d['is_materialized'])
        self.assertEqual(d['columns'], 'id,name,email')


class TestTriggerSchema(unittest.TestCase):

    def test_to_dict(self):
        t = TriggerSchema(
            name='audit_log_trigger',
            schema_name='public',
            table_name='orders',
            event='INSERT,UPDATE',
            timing='AFTER',
            definition_hash='ghi789',
        )
        d = t.to_dict()
        self.assertEqual(d['table_name'], 'orders')
        self.assertEqual(d['event'], 'INSERT,UPDATE')


# =============================================================================
# _md5_hash Tests
# =============================================================================

class TestMd5Hash(unittest.TestCase):

    def test_empty_string(self):
        self.assertEqual(_md5_hash(''), '')

    def test_normal_string(self):
        self.assertEqual(_md5_hash('hello'), _expected_md5('hello'))


# =============================================================================
# PostgreSQL Extractor Tests
# =============================================================================

class TestPostgresSchemaExtractorObjects(unittest.TestCase):

    def _make_extractor(self, cursor_rows):
        """Create extractor with a mocked connection returning given rows."""
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.return_value = cursor_rows
        conn.cursor.return_value = cursor
        return PostgresSchemaExtractor(conn)

    @patch('src.db.schema_extractor.Config')
    def test_extract_stored_procedures(self, mock_config):
        mock_config.POSTGRES_SCHEMA = 'public'
        rows = [
            ('get_user', 'plpgsql', 'id integer', 'users', 'CREATE FUNCTION get_user()...'),
            ('do_cleanup', 'sql', '', 'void', 'CREATE PROCEDURE do_cleanup()...'),
        ]
        extractor = self._make_extractor(rows)
        
        result = extractor.extract_stored_procedures('public')
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].name, 'get_user')
        self.assertEqual(result[0].language, 'plpgsql')
        self.assertEqual(result[0].return_type, 'users')
        self.assertEqual(result[0].definition_hash, _expected_md5('CREATE FUNCTION get_user()...'))

    @patch('src.db.schema_extractor.Config')
    def test_extract_stored_procedures_empty(self, mock_config):
        mock_config.POSTGRES_SCHEMA = 'public'
        extractor = self._make_extractor([])
        result = extractor.extract_stored_procedures('public')
        self.assertEqual(result, [])

    @patch('src.db.schema_extractor.Config')
    def test_extract_triggers(self, mock_config):
        mock_config.POSTGRES_SCHEMA = 'public'
        rows = [
            ('trg_audit', 'orders', 'INSERT', 'AFTER', 'EXECUTE FUNCTION audit_fn()'),
            ('trg_audit', 'orders', 'UPDATE', 'AFTER', 'EXECUTE FUNCTION audit_fn()'),
        ]
        extractor = self._make_extractor(rows)
        result = extractor.extract_triggers('public')
        
        # Should aggregate events for same trigger
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, 'trg_audit')
        self.assertEqual(result[0].event, 'INSERT,UPDATE')
        self.assertEqual(result[0].timing, 'AFTER')

    @patch('src.db.schema_extractor.Config')
    def test_extract_views(self, mock_config):
        mock_config.POSTGRES_SCHEMA = 'public'
        
        conn = MagicMock()
        
        # The method uses ONE main cursor for both regular and materialized view queries.
        # It creates separate cursors via conn.cursor() for column lookups.
        view_cursor = MagicMock()
        # First fetchall → regular views, second fetchall → materialized views
        view_cursor.fetchall.side_effect = [
            [('active_users', 'SELECT * FROM users WHERE active = true')],  # regular views
            [],  # materialized views (empty)
        ]
        
        # Column cursor for the regular view
        col_cursor = MagicMock()
        col_cursor.fetchall.return_value = [('id',), ('name',), ('email',)]
        
        # cursor() calls: 1st = view_cursor, 2nd = col_cursor
        conn.cursor.side_effect = [view_cursor, col_cursor]
        
        extractor = PostgresSchemaExtractor(conn)
        result = extractor.extract_views('public')
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, 'active_users')
        self.assertFalse(result[0].is_materialized)
        self.assertEqual(result[0].columns, 'id,name,email')


# =============================================================================
# MSSQL Extractor Tests
# =============================================================================

class TestMSSQLSchemaExtractorObjects(unittest.TestCase):

    def _make_extractor(self, cursor_rows):
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.return_value = cursor_rows
        conn.cursor.return_value = cursor
        return MSSQLSchemaExtractor(conn)

    @patch('src.db.schema_extractor.Config')
    def test_extract_stored_procedures(self, mock_config):
        mock_config.MSSQL_SCHEMA = 'dbo'
        rows = [
            ('sp_get_orders', 'CREATE PROCEDURE sp_get_orders AS BEGIN SELECT * FROM orders END'),
        ]
        extractor = self._make_extractor(rows)
        result = extractor.extract_stored_procedures('dbo')
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, 'sp_get_orders')
        self.assertEqual(result[0].language, 'tsql')

    @patch('src.db.schema_extractor.Config')
    def test_extract_views(self, mock_config):
        mock_config.MSSQL_SCHEMA = 'dbo'
        rows = [
            ('vw_active', 'CREATE VIEW vw_active AS SELECT * FROM users', 'id,name'),
        ]
        extractor = self._make_extractor(rows)
        result = extractor.extract_views('dbo')
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].columns, 'id,name')

    @patch('src.db.schema_extractor.Config')
    def test_extract_triggers(self, mock_config):
        mock_config.MSSQL_SCHEMA = 'dbo'
        rows = [
            ('trg_audit', 'orders', 'INSERT', 'AFTER', 'CREATE TRIGGER trg_audit...'),
        ]
        extractor = self._make_extractor(rows)
        result = extractor.extract_triggers('dbo')
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].table_name, 'orders')
        self.assertEqual(result[0].timing, 'AFTER')


# =============================================================================
# MySQL Extractor Tests
# =============================================================================

class TestMySQLSchemaExtractorObjects(unittest.TestCase):

    def _make_extractor(self, cursor_rows):
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.return_value = cursor_rows
        conn.cursor.return_value = cursor
        extractor = MySQLSchemaExtractor(conn)
        extractor.database = 'testdb'
        return extractor

    @patch('src.db.schema_extractor.Config')
    def test_extract_stored_procedures(self, mock_config):
        rows = [
            ('get_data', 'PROCEDURE', None, 'SQL', 'SELECT * FROM data'),
            ('calc_total', 'FUNCTION', 'DECIMAL(10,2)', 'SQL', 'RETURN 42'),
        ]
        extractor = self._make_extractor(rows)
        result = extractor.extract_stored_procedures('testdb')
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].name, 'get_data')
        self.assertEqual(result[0].return_type, '')  # PROCEDURE has no return
        self.assertEqual(result[1].name, 'calc_total')
        self.assertEqual(result[1].return_type, 'DECIMAL(10,2)')

    @patch('src.db.schema_extractor.Config')
    def test_extract_triggers(self, mock_config):
        rows = [
            ('before_insert_users', 'users', 'INSERT', 'BEFORE', 'SET NEW.created_at = NOW()'),
        ]
        extractor = self._make_extractor(rows)
        result = extractor.extract_triggers('testdb')
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].timing, 'BEFORE')
        self.assertEqual(result[0].event, 'INSERT')


# =============================================================================
# run_schema_objects_profiler Integration Test
# =============================================================================

class TestRunSchemaObjectsProfiler(unittest.TestCase):

    @patch('main.get_database_connection')
    @patch('main.Config')
    def test_runs_extraction_and_stores(self, mock_config, mock_get_conn):
        """Test end-to-end: extract → store in PostgreSQL backend."""
        from main import run_schema_objects_profiler
        
        mock_config.METRICS_BACKEND = 'postgresql'
        mock_config.POSTGRES_HOST = 'localhost'
        mock_config.POSTGRES_DB = 'testdb'
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn
        
        # Mock cursor to return one procedure
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            ('my_proc', 'plpgsql', 'x int', 'void', 'CREATE FUNCTION my_proc()...'),
        ]
        mock_conn.cursor.return_value = cursor
        
        with patch('src.db.postgres_metrics.init_schema_objects_pg', return_value=True), \
             patch('src.db.postgres_metrics.insert_schema_objects_pg', return_value=True) as mock_insert:
            
            result = run_schema_objects_profiler(
                application='test-app',
                environment='dev',
                database_type='postgresql',
                metrics_backend='postgresql',
                schema='public',
            )
        
        # The extractor was called; connection was used
        self.assertIsNotNone(result)


if __name__ == '__main__':
    unittest.main()
