"""
Auto-increment metrics calculation and data structures.

Provides metrics calculation including:
- Usage percentage
- Remaining values
- Growth rate analysis using Linear Regression
- Days until overflow prediction
"""

import logging
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
from scipy import stats

from src.config import Config

logger = logging.getLogger(__name__)


# Alert thresholds
CRITICAL_DAYS = 30
CRITICAL_USAGE_PERCENT = 90.0
WARNING_DAYS = 90
WARNING_USAGE_PERCENT = 75.0

# Default lookback period for growth rate calculation
DEFAULT_LOOKBACK_DAYS = 7


@dataclass
class AutoIncrementProfile:
    """Data class representing auto-increment column metrics."""
    
    # Column identification
    table_name: str
    column_name: str
    data_type: str
    sequence_name: str
    
    # Current state
    current_value: int
    max_type_value: int
    usage_percentage: float
    remaining_values: int
    
    # Growth metrics (calculated from time series)
    daily_growth_rate: Optional[float] = None
    days_until_full: Optional[float] = None
    
    # Alert status
    alert_status: str = 'OK'  # OK, WARNING, CRITICAL
    
    # Metadata
    profiled_at: datetime = field(default_factory=datetime.now)
    
    def calculate_alert_status(self) -> str:
        """Determine alert status based on thresholds."""
        # Check by days until full (if available)
        if self.days_until_full is not None:
            if self.days_until_full < CRITICAL_DAYS:
                return 'CRITICAL'
            elif self.days_until_full < WARNING_DAYS:
                return 'WARNING'
        
        # Check by usage percentage
        if self.usage_percentage >= CRITICAL_USAGE_PERCENT:
            return 'CRITICAL'
        elif self.usage_percentage >= WARNING_USAGE_PERCENT:
            return 'WARNING'
        
        return 'OK'


def calculate_linear_regression_growth_rate(
    timestamps: list[datetime],
    values: list[int]
) -> Optional[float]:
    """
    Calculate daily growth rate using Linear Regression.
    
    Args:
        timestamps: List of datetime objects for each data point
        values: List of sequence values at each timestamp
        
    Returns:
        Daily growth rate (IDs per day), or None if insufficient data
    """
    if len(timestamps) < 2 or len(values) < 2:
        logger.debug("Insufficient data points for linear regression")
        return None
    
    if len(timestamps) != len(values):
        logger.warning("Timestamps and values length mismatch")
        return None
    
    try:
        # Convert timestamps to numeric (days since first timestamp)
        base_time = min(timestamps)
        days = np.array([
            (ts - base_time).total_seconds() / 86400.0  # seconds per day
            for ts in timestamps
        ])
        
        values_array = np.array(values, dtype=np.float64)
        
        # Perform linear regression
        slope, intercept, r_value, p_value, std_err = stats.linregress(days, values_array)
        
        # slope is the daily growth rate
        logger.debug(f"Linear regression: slope={slope:.2f} ids/day, R²={r_value**2:.4f}")
        
        # Return slope only if it's positive (growing)
        if slope > 0:
            return float(slope)
        else:
            logger.debug("Negative or zero slope - sequence values not growing")
            return None
            
    except Exception as e:
        logger.error(f"Error calculating linear regression: {e}")
        return None


def calculate_days_until_full(
    current_value: int,
    max_value: int,
    daily_growth_rate: float
) -> Optional[float]:
    """
    Calculate days until the sequence reaches its maximum value.
    
    Args:
        current_value: Current sequence value
        max_value: Maximum possible value for the data type
        daily_growth_rate: Average daily growth rate
        
    Returns:
        Estimated days until full, or None if cannot be calculated
    """
    if daily_growth_rate is None or daily_growth_rate <= 0:
        return None
    
    remaining = max_value - current_value
    if remaining <= 0:
        return 0.0
    
    days = remaining / daily_growth_rate
    return round(days, 2)


def fetch_historical_data(
    clickhouse_client,
    application: str,
    environment: str,
    table_name: str,
    column_name: str,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS
) -> tuple[list[datetime], list[int]]:
    """
    Fetch historical auto-increment values from ClickHouse.
    
    Args:
        clickhouse_client: ClickHouse client connection
        application: Application name filter
        environment: Environment name filter
        table_name: Table name filter
        column_name: Column name filter
        lookback_days: Number of days to look back
        
    Returns:
        Tuple of (timestamps, values) lists
    """
    try:
        query = """
            SELECT scan_time, current_value
            FROM auto_increment_metrics
            WHERE application = {application:String}
                AND environment = {environment:String}
                AND table_name = {table_name:String}
                AND column_name = {column_name:String}
                AND scan_time >= now() - INTERVAL {lookback_days:Int32} DAY
            ORDER BY scan_time ASC
        """
        
        result = clickhouse_client.query(
            query,
            parameters={
                'application': application,
                'environment': environment,
                'table_name': table_name,
                'column_name': column_name,
                'lookback_days': lookback_days,
            }
        )
        
        timestamps = []
        values = []
        
        for row in result.result_rows:
            timestamps.append(row[0])
            values.append(row[1])
        
        logger.debug(f"Fetched {len(timestamps)} historical data points for {table_name}.{column_name}")
        return timestamps, values
        
    except Exception as e:
        logger.warning(f"Could not fetch historical data: {e}")
        return [], []


def calculate_autoincrement_metrics(
    raw_data: dict,
    clickhouse_client=None,
    application: str = 'default',
    environment: str = 'development',
    lookback_days: int = DEFAULT_LOOKBACK_DAYS
) -> AutoIncrementProfile:
    """
    Calculate complete auto-increment metrics including growth rate prediction.
    
    Args:
        raw_data: Dict from autoincrement detector with current values
        clickhouse_client: Optional ClickHouse client for historical data
        application: Application name for querying history
        environment: Environment name for querying history
        lookback_days: Number of days to analyze for growth rate
        
    Returns:
        AutoIncrementProfile with all calculated metrics
    """
    table_name = raw_data['table_name']
    column_name = raw_data['column_name']
    current_value = raw_data['current_value']
    max_type_value = raw_data['max_type_value']
    
    # Calculate growth rate from historical data if ClickHouse client is available
    daily_growth_rate = None
    days_until_full = None
    
    if clickhouse_client is not None:
        timestamps, values = fetch_historical_data(
            clickhouse_client=clickhouse_client,
            application=application,
            environment=environment,
            table_name=table_name,
            column_name=column_name,
            lookback_days=lookback_days,
        )
        
        if timestamps and values:
            # Add current data point for more accurate calculation
            timestamps.append(datetime.now())
            values.append(current_value)
            
            daily_growth_rate = calculate_linear_regression_growth_rate(timestamps, values)
            
            if daily_growth_rate is not None:
                days_until_full = calculate_days_until_full(
                    current_value=current_value,
                    max_value=max_type_value,
                    daily_growth_rate=daily_growth_rate
                )
    
    # Create the profile
    profile = AutoIncrementProfile(
        table_name=table_name,
        column_name=column_name,
        data_type=raw_data['data_type'],
        sequence_name=raw_data['sequence_name'],
        current_value=current_value,
        max_type_value=max_type_value,
        usage_percentage=raw_data['usage_percentage'],
        remaining_values=raw_data['remaining_values'],
        daily_growth_rate=round(daily_growth_rate, 2) if daily_growth_rate else None,
        days_until_full=days_until_full,
    )
    
    # Calculate and set alert status
    profile.alert_status = profile.calculate_alert_status()
    
    return profile


def profile_table_autoincrement(
    table_name: str,
    detector,
    clickhouse_client=None,
    application: str = 'default',
    environment: str = 'development',
    lookback_days: int = DEFAULT_LOOKBACK_DAYS
) -> list[AutoIncrementProfile]:
    """
    Profile all auto-increment columns in a table.
    
    Args:
        table_name: Name of the table to profile
        detector: AutoIncrementDetector instance
        clickhouse_client: Optional ClickHouse client for historical data
        application: Application name
        environment: Environment name
        lookback_days: Days of historical data to analyze
        
    Returns:
        List of AutoIncrementProfile for each auto-increment column
    """
    logger.info(f"Profiling auto-increment columns for table: {table_name}")
    
    # Get raw data from detector
    raw_columns = detector.get_all_autoincrement_info(table_name)
    
    if not raw_columns:
        logger.info(f"No auto-increment columns found in '{table_name}'")
        return []
    
    # Calculate metrics for each column
    profiles = []
    for raw_data in raw_columns:
        profile = calculate_autoincrement_metrics(
            raw_data=raw_data,
            clickhouse_client=clickhouse_client,
            application=application,
            environment=environment,
            lookback_days=lookback_days,
        )
        profiles.append(profile)
        
        logger.info(
            f"  {profile.column_name}: {profile.usage_percentage:.4f}% used, "
            f"status={profile.alert_status}, days_until_full={profile.days_until_full}"
        )
    
    return profiles
