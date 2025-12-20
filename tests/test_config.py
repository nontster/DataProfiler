"""
Unit tests for the Config class.
"""

import os
import unittest
from unittest.mock import patch

from src.config import Config


class TestConfig(unittest.TestCase):
    """Test cases for Config class."""

    def test_default_postgres_host(self):
        """Test default PostgreSQL host value."""
        self.assertIsNotNone(Config.POSTGRES_HOST)

    def test_default_postgres_port(self):
        """Test default PostgreSQL port is integer."""
        self.assertIsInstance(Config.POSTGRES_PORT, int)
        self.assertEqual(Config.POSTGRES_PORT, 5432)

    def test_default_clickhouse_port(self):
        """Test default ClickHouse port is integer."""
        self.assertIsInstance(Config.CLICKHOUSE_PORT, int)
        self.assertEqual(Config.CLICKHOUSE_PORT, 8123)

    def test_validate_returns_true(self):
        """Test that validate always returns True (with warnings for missing)."""
        result = Config.validate()
        self.assertTrue(result)

    def test_get_postgres_config_returns_dict(self):
        """Test that get_postgres_config returns a dictionary."""
        config = Config.get_postgres_config()
        self.assertIsInstance(config, dict)
        self.assertIn('host', config)
        self.assertIn('port', config)
        self.assertIn('database', config)
        self.assertIn('user', config)
        self.assertIn('password', config)

    def test_get_clickhouse_config_returns_dict(self):
        """Test that get_clickhouse_config returns a dictionary."""
        config = Config.get_clickhouse_config()
        self.assertIsInstance(config, dict)
        self.assertIn('host', config)
        self.assertIn('port', config)
        self.assertIn('username', config)
        self.assertIn('password', config)


if __name__ == '__main__':
    unittest.main()
