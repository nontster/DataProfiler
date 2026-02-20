
import os
import unittest
from unittest.mock import MagicMock, patch
from src.config import Config
from src.core.metrics import TableProfile, ColumnProfile
from src.db.clickhouse import insert_profiles, insert_schema_objects, insert_table_inventory
from src.db.postgres_metrics import insert_profiles_pg, insert_schema_objects_pg, insert_table_inventory_pg

class TestOracleConfig(unittest.TestCase):
    
    def setUp(self):
        self.patcher = patch.dict(os.environ, {
            'ORACLE_HOST': 'oracle-test-host',
            'ORACLE_SERVICE_NAME': 'oracle-test-service',
            'ORACLE_SCHEMA': 'oracle-test-schema'
        })
        self.patcher.start()
        
        # Reload/Update config to pick up env vars
        Config.ORACLE_HOST = 'oracle-test-host'
        Config.ORACLE_SERVICE_NAME = 'oracle-test-service'
        Config.ORACLE_SCHEMA = 'oracle-test-schema'
        
        # Dummy profile data
        self.col_profile = ColumnProfile(
            table_name='test_table',
            column_name='test_col',
            data_type='VARCHAR',
            row_count=100
        )
        self.table_profile = TableProfile(
            table_name='test_table',
            row_count=100,
            column_profiles=[self.col_profile]
        )

    def tearDown(self):
        self.patcher.stop()

    @patch('src.db.clickhouse.get_clickhouse_client')
    def test_clickhouse_insert_profiles_oracle(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        insert_profiles(self.table_profile, database_type='oracle')
        
        # Check that insert was called
        mock_client.insert.assert_called()
        
        # Extract data argument
        call_args = mock_client.insert.call_args
        # signature: client.insert(table, data, column_names=...)
        # data is the second arg
        data = call_args[0][1]
        
        # Verify first row's host/db match Oracle config
        # Row format in insert_profiles:
        # [app, env, host, db_name, schema, ...]
        row = data[0]
        self.assertEqual(row[2], 'oracle-test-host')
        self.assertEqual(row[3], 'oracle-test-service')
        self.assertEqual(row[4], 'oracle-test-schema')

 

    @patch('src.db.postgres_metrics.execute_values')
    @patch('src.db.postgres_metrics.get_postgres_metrics_connection')
    def test_postgres_insert_profiles_oracle_check_values(self, mock_get_conn, mock_execute_values):
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn
        
        insert_profiles_pg(self.table_profile, database_type='oracle')
        
        mock_execute_values.assert_called()
        call_args = mock_execute_values.call_args
        # execute_values(cursor, query, data)
        data = call_args[0][2]
        
        row = data[0]
        # Row format tuple: (app, env, host, db, schema, ...)
        self.assertEqual(row[2], 'oracle-test-host')
        self.assertEqual(row[3], 'oracle-test-service')
        self.assertEqual(row[4], 'oracle-test-schema')

if __name__ == '__main__':
    unittest.main()
