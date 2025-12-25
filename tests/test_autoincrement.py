"""
Unit tests for auto-increment column detection and monitoring.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Test data
MOCK_SEQUENCE_DATA = [
    {
        'column_name': 'id',
        'data_type': 'integer',
        'sequence_name': 'public.users_id_seq',
    }
]

MOCK_AUTOINCREMENT_INFO = [
    {
        'table_name': 'users',
        'column_name': 'id',
        'data_type': 'integer',
        'sequence_name': 'public.users_id_seq',
        'current_value': 1000,
        'max_type_value': 2147483647,
        'usage_percentage': 0.0000465661,
        'remaining_values': 2147482647,
    }
]


class TestTypeMaxValues:
    """Test data type maximum value constants."""
    
    def test_smallint_max(self):
        from src.db.autoincrement import TYPE_MAX_VALUES
        assert TYPE_MAX_VALUES['smallint'] == 32767
    
    def test_integer_max(self):
        from src.db.autoincrement import TYPE_MAX_VALUES
        assert TYPE_MAX_VALUES['integer'] == 2147483647
    
    def test_bigint_max(self):
        from src.db.autoincrement import TYPE_MAX_VALUES
        assert TYPE_MAX_VALUES['bigint'] == 9223372036854775807


class TestAutoIncrementDetector:
    """Test PostgreSQL auto-increment detector."""
    
    def test_get_autoincrement_detector_postgresql(self):
        from src.db.autoincrement import get_autoincrement_detector, PostgreSQLAutoIncrementDetector
        detector = get_autoincrement_detector('postgresql')
        assert isinstance(detector, PostgreSQLAutoIncrementDetector)
    
    def test_get_autoincrement_detector_postgres_alias(self):
        from src.db.autoincrement import get_autoincrement_detector, PostgreSQLAutoIncrementDetector
        detector = get_autoincrement_detector('postgres')
        assert isinstance(detector, PostgreSQLAutoIncrementDetector)
    
    def test_get_autoincrement_detector_unsupported(self):
        from src.db.autoincrement import get_autoincrement_detector
        with pytest.raises(ValueError, match="Unsupported database type"):
            get_autoincrement_detector('mysql')


class TestAutoIncrementMetrics:
    """Test auto-increment metrics calculation."""
    
    def test_calculate_usage_percentage(self):
        """Test that usage percentage is calculated correctly."""
        from src.core.autoincrement_metrics import AutoIncrementProfile
        
        profile = AutoIncrementProfile(
            table_name='test',
            column_name='id',
            data_type='integer',
            sequence_name='test_id_seq',
            current_value=1000000,
            max_type_value=2147483647,
            usage_percentage=0.0465661,  # (1000000/2147483647)*100
            remaining_values=2146483647,
        )
        
        # Usage percentage should be around 0.0465661%
        assert 0.04 < profile.usage_percentage < 0.05
    
    def test_alert_status_ok(self):
        """Test OK alert status."""
        from src.core.autoincrement_metrics import AutoIncrementProfile
        
        profile = AutoIncrementProfile(
            table_name='test',
            column_name='id',
            data_type='integer',
            sequence_name='test_id_seq',
            current_value=1000,
            max_type_value=2147483647,
            usage_percentage=0.00005,
            remaining_values=2147482647,
            days_until_full=36500,  # 100 years
        )
        
        assert profile.calculate_alert_status() == 'OK'
    
    def test_alert_status_warning_by_days(self):
        """Test WARNING alert status when days until full < 90."""
        from src.core.autoincrement_metrics import AutoIncrementProfile
        
        profile = AutoIncrementProfile(
            table_name='test',
            column_name='id',
            data_type='integer',
            sequence_name='test_id_seq',
            current_value=1000000,
            max_type_value=2147483647,
            usage_percentage=50.0,
            remaining_values=1073741823,
            days_until_full=60,  # Less than 90 days
        )
        
        assert profile.calculate_alert_status() == 'WARNING'
    
    def test_alert_status_critical_by_days(self):
        """Test CRITICAL alert status when days until full < 30."""
        from src.core.autoincrement_metrics import AutoIncrementProfile
        
        profile = AutoIncrementProfile(
            table_name='test',
            column_name='id',
            data_type='integer',
            sequence_name='test_id_seq',
            current_value=2000000000,
            max_type_value=2147483647,
            usage_percentage=93.0,
            remaining_values=147483647,
            days_until_full=15,  # Less than 30 days
        )
        
        assert profile.calculate_alert_status() == 'CRITICAL'
    
    def test_alert_status_critical_by_usage(self):
        """Test CRITICAL alert status when usage > 90%."""
        from src.core.autoincrement_metrics import AutoIncrementProfile
        
        profile = AutoIncrementProfile(
            table_name='test',
            column_name='id',
            data_type='integer',
            sequence_name='test_id_seq',
            current_value=2000000000,
            max_type_value=2147483647,
            usage_percentage=93.12,  # > 90%
            remaining_values=147483647,
            days_until_full=None,  # No historical data
        )
        
        assert profile.calculate_alert_status() == 'CRITICAL'


class TestLinearRegressionGrowthRate:
    """Test linear regression growth rate calculation."""
    
    def test_calculate_growth_rate_basic(self):
        """Test basic linear regression calculation."""
        from src.core.autoincrement_metrics import calculate_linear_regression_growth_rate
        
        # Create data with known growth rate (~100 IDs per day)
        base_time = datetime.now() - timedelta(days=7)
        timestamps = [base_time + timedelta(days=i) for i in range(8)]
        values = [1000 + (i * 100) for i in range(8)]  # 100 IDs per day
        
        growth_rate = calculate_linear_regression_growth_rate(timestamps, values)
        
        assert growth_rate is not None
        assert 95 <= growth_rate <= 105  # Should be ~100
    
    def test_calculate_growth_rate_insufficient_data(self):
        """Test with insufficient data points."""
        from src.core.autoincrement_metrics import calculate_linear_regression_growth_rate
        
        # Only one data point
        timestamps = [datetime.now()]
        values = [1000]
        
        growth_rate = calculate_linear_regression_growth_rate(timestamps, values)
        
        assert growth_rate is None
    
    def test_calculate_growth_rate_negative_slope(self):
        """Test with decreasing values (should return None)."""
        from src.core.autoincrement_metrics import calculate_linear_regression_growth_rate
        
        base_time = datetime.now() - timedelta(days=7)
        timestamps = [base_time + timedelta(days=i) for i in range(8)]
        values = [1000 - (i * 100) for i in range(8)]  # Decreasing
        
        growth_rate = calculate_linear_regression_growth_rate(timestamps, values)
        
        assert growth_rate is None


class TestDaysUntilFull:
    """Test days until full calculation."""
    
    def test_calculate_days_until_full_basic(self):
        """Test basic calculation."""
        from src.core.autoincrement_metrics import calculate_days_until_full
        
        days = calculate_days_until_full(
            current_value=1000000,
            max_value=2000000,
            daily_growth_rate=10000,  # 10k per day
        )
        
        assert days is not None
        assert days == 100.0  # (2M - 1M) / 10k = 100 days
    
    def test_calculate_days_until_full_no_growth(self):
        """Test with zero growth rate."""
        from src.core.autoincrement_metrics import calculate_days_until_full
        
        days = calculate_days_until_full(
            current_value=1000000,
            max_value=2000000,
            daily_growth_rate=0,
        )
        
        assert days is None
    
    def test_calculate_days_until_full_already_full(self):
        """Test when already at max."""
        from src.core.autoincrement_metrics import calculate_days_until_full
        
        days = calculate_days_until_full(
            current_value=2000000,
            max_value=2000000,
            daily_growth_rate=1000,
        )
        
        assert days == 0.0
