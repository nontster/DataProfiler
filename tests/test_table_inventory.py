"""
Unit tests for table inventory feature.
Tests list_tables, init_table_inventory, and insert_table_inventory functions.
"""

import unittest
from unittest.mock import patch, MagicMock, call


class TestPostgresListTables(unittest.TestCase):
    """Test list_tables for PostgreSQL."""

    @patch('src.db.postgres.get_postgres_connection')
    def test_list_tables_returns_sorted_list(self, mock_get_conn):
        from src.db.postgres import list_tables
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('products',), ('users',), ('orders',)
        ]
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn
        
        result = list_tables(schema='prod')
        
        self.assertEqual(result, ['products', 'users', 'orders'])
        mock_cursor.execute.assert_called_once()
        # Verify SQL filters BASE TABLE and correct schema
        sql = mock_cursor.execute.call_args[0][0]
        self.assertIn('BASE TABLE', sql)
        mock_conn.close.assert_called_once()

    @patch('src.db.postgres.get_postgres_connection')
    def test_list_tables_with_existing_connection(self, mock_get_conn):
        """Should use provided connection and NOT close it."""
        from src.db.postgres import list_tables
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [('users',)]
        mock_conn.cursor.return_value = mock_cursor
        
        result = list_tables(schema='prod', conn=mock_conn)
        
        self.assertEqual(result, ['users'])
        mock_get_conn.assert_not_called()  # Should NOT create new connection
        mock_conn.close.assert_not_called()  # Should NOT close provided connection

    @patch('src.db.postgres.get_postgres_connection')
    def test_list_tables_empty_schema(self, mock_get_conn):
        from src.db.postgres import list_tables
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn
        
        result = list_tables(schema='empty_schema')
        
        self.assertEqual(result, [])


class TestMSSQLListTables(unittest.TestCase):
    """Test list_tables for MSSQL."""

    @patch('src.db.mssql.get_mssql_connection')
    def test_list_tables_returns_list(self, mock_get_conn):
        from src.db.mssql import list_tables
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('orders',), ('products',), ('users',)
        ]
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn
        
        result = list_tables(schema='dbo')
        
        self.assertEqual(result, ['orders', 'products', 'users'])
        mock_conn.close.assert_called_once()

    @patch('src.db.mssql.get_mssql_connection')
    def test_list_tables_with_existing_connection(self, mock_get_conn):
        from src.db.mssql import list_tables
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [('users',)]
        mock_conn.cursor.return_value = mock_cursor
        
        result = list_tables(schema='prod', conn=mock_conn)
        
        mock_get_conn.assert_not_called()
        mock_conn.close.assert_not_called()


class TestMySQLListTables(unittest.TestCase):
    """Test list_tables for MySQL."""

    @patch('src.db.mysql.get_mysql_connection')
    def test_list_tables_returns_list(self, mock_get_conn):
        from src.db.mysql import list_tables
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('orders',), ('products',), ('users',)
        ]
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn
        
        result = list_tables(schema='mydb')
        
        self.assertEqual(result, ['orders', 'products', 'users'])

    @patch('src.db.mysql.get_mysql_connection')
    def test_list_tables_handles_bytes(self, mock_get_conn):
        """MySQL connector may return bytes instead of strings."""
        from src.db.mysql import list_tables
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            (b'orders',), (b'users',)
        ]
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn
        
        result = list_tables(schema='mydb')
        
        self.assertEqual(result, ['orders', 'users'])
        # Verify they are strings, not bytes
        for name in result:
            self.assertIsInstance(name, str)


class TestConnectionFactoryListTables(unittest.TestCase):
    """Test list_tables dispatcher in connection_factory."""

    @patch('src.db.connection_factory.pg_list_tables')
    def test_dispatches_to_postgres(self, mock_pg):
        from src.db.connection_factory import list_tables
        
        mock_pg.return_value = ['users', 'orders']
        result = list_tables('postgresql', schema='prod')
        
        mock_pg.assert_called_once_with(schema='prod', conn=None)
        self.assertEqual(result, ['users', 'orders'])

    @patch('src.db.connection_factory.mssql_list_tables')
    def test_dispatches_to_mssql(self, mock_mssql):
        from src.db.connection_factory import list_tables
        
        mock_mssql.return_value = ['users']
        result = list_tables('mssql', schema='dbo')
        
        mock_mssql.assert_called_once_with(schema='dbo', conn=None)

    @patch('src.db.connection_factory.mysql_list_tables')
    def test_dispatches_to_mysql(self, mock_mysql):
        from src.db.connection_factory import list_tables
        
        mock_mysql.return_value = ['users']
        result = list_tables('mysql', schema='mydb')
        
        mock_mysql.assert_called_once_with(schema='mydb', conn=None)

    def test_unsupported_database_raises_error(self):
        from src.db.connection_factory import list_tables
        
        with self.assertRaises(ValueError):
            list_tables('oracle', schema='test')


class TestClickHouseTableInventory(unittest.TestCase):
    """Test ClickHouse table inventory functions."""

    @patch('src.db.clickhouse.get_clickhouse_client')
    def test_init_table_inventory_creates_table(self, mock_get_client):
        from src.db.clickhouse import init_table_inventory
        
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        result = init_table_inventory()
        
        self.assertTrue(result)
        mock_client.command.assert_called_once()
        sql = mock_client.command.call_args[0][0]
        self.assertIn('table_inventory', sql)
        self.assertIn('CREATE TABLE IF NOT EXISTS', sql)

    @patch('src.db.clickhouse.get_clickhouse_client')
    def test_insert_table_inventory(self, mock_get_client):
        from src.db.clickhouse import insert_table_inventory
        
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        tables = ['users', 'orders', 'products']
        result = insert_table_inventory(
            tables=tables,
            schema='prod',
            application='order-service',
            environment='production',
            database_type='postgresql'
        )
        
        self.assertTrue(result)
        mock_client.insert.assert_called_once()
        call_args = mock_client.insert.call_args
        self.assertEqual(call_args[0][0], 'table_inventory')
        data = call_args[0][1]
        self.assertEqual(len(data), 3)

    @patch('src.db.clickhouse.get_clickhouse_client')
    def test_insert_table_inventory_empty_list(self, mock_get_client):
        from src.db.clickhouse import insert_table_inventory
        
        result = insert_table_inventory(tables=[], schema='prod')
        
        self.assertTrue(result)
        mock_get_client.assert_not_called()


class TestPostgresMetricsTableInventory(unittest.TestCase):
    """Test PostgreSQL metrics table inventory functions."""

    @patch('src.db.postgres_metrics.get_postgres_metrics_connection')
    def test_init_table_inventory_pg(self, mock_get_conn):
        from src.db.postgres_metrics import init_table_inventory_pg
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn
        
        result = init_table_inventory_pg()
        
        self.assertTrue(result)
        # Should create table + 2 indexes = 3 execute calls
        self.assertEqual(mock_cursor.execute.call_count, 3)
        create_sql = mock_cursor.execute.call_args_list[0][0][0]
        self.assertIn('table_inventory', create_sql)
        mock_conn.commit.assert_called_once()

    @patch('src.db.postgres_metrics.execute_values')
    @patch('src.db.postgres_metrics.get_postgres_metrics_connection')
    def test_insert_table_inventory_pg(self, mock_get_conn, mock_exec_values):
        from src.db.postgres_metrics import insert_table_inventory_pg
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn
        
        tables = ['users', 'orders']
        result = insert_table_inventory_pg(
            tables=tables,
            schema='prod',
            application='myapp',
            environment='uat',
            database_type='postgresql'
        )
        
        self.assertTrue(result)
        mock_exec_values.assert_called_once()
        mock_conn.commit.assert_called_once()

    @patch('src.db.postgres_metrics.get_postgres_metrics_connection')
    def test_insert_table_inventory_pg_empty_list(self, mock_get_conn):
        from src.db.postgres_metrics import insert_table_inventory_pg
        
        result = insert_table_inventory_pg(tables=[], schema='prod')
        
        self.assertTrue(result)
        mock_get_conn.assert_not_called()


if __name__ == '__main__':
    unittest.main()
