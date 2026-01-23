#!/usr/bin/env python3
"""
DataProfiler - Automated Data Profiling Tool

Main entry point for running data profiling from command line.
Supports dbt-profiler style metrics and multiple output formats.
"""

import sys
import argparse
import logging
from typing import Optional

from src.config import Config
from src.db.connection_factory import get_table_metadata, normalize_database_type
from src.db.clickhouse import (
    init_clickhouse, insert_profiles,
    init_autoincrement_table, insert_autoincrement_profiles,
    get_clickhouse_client
)
from src.db.postgres_metrics import (
    init_postgres_metrics, insert_profiles_pg,
    insert_autoincrement_profiles_pg, fetch_historical_data_pg
)
from src.db.autoincrement import get_autoincrement_detector
from src.core.metrics import profile_table
from src.core.formatters import format_profile
from src.core.autoincrement_metrics import profile_table_autoincrement
from src.exceptions import TableNotFoundError, DatabaseConnectionError

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='DataProfiler - dbt-profiler style data profiling tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py users                         # Profile 'users' table from PostgreSQL
  python main.py users -d mssql                # Profile from SQL Server
  python main.py users --format markdown       # Output as Markdown table
  python main.py users --format json           # Output as JSON
  python main.py users --format csv            # Output as CSV
  python main.py users -o users.md             # Save to file
  python main.py users --no-store              # Don't save to ClickHouse
  python main.py users --auto-increment        # Include auto-increment overflow analysis
  python main.py test_users -d mssql --auto-increment  # MSSQL with IDENTITY analysis
        """
    )
    
    parser.add_argument(
        'table',
        nargs='?',
        default='users',
        help='Name of the table to profile (default: users)'
    )
    
    parser.add_argument(
        '-f', '--format',
        choices=['table', 'markdown', 'json', 'csv'],
        default='table',
        help='Output format (default: table)'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        help='Output file path (if not specified, prints to console)'
    )
    
    parser.add_argument(
        '--no-store',
        action='store_true',
        help='Do not store results in ClickHouse'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose/debug logging'
    )
    
    parser.add_argument(
        '--app',
        default='default',
        help='Application name (default: default)'
    )

    parser.add_argument(
        '--env',
        default='development',
        help='Environment name (e.g., uat, production)'
    )

    parser.add_argument(
        '--auto-increment',
        action='store_true',
        help='Include auto-increment column overflow analysis'
    )

    parser.add_argument(
        '--lookback-days',
        type=int,
        default=7,
        help='Days of historical data for growth rate calculation (default: 7)'
    )

    parser.add_argument(
        '-d', '--database-type',
        choices=['postgresql', 'mssql'],
        default='postgresql',
        help='Database type to profile (default: postgresql)'
    )

    parser.add_argument(
        '--metrics-backend',
        choices=['clickhouse', 'postgresql'],
        default=None,
        help='Backend for storing metrics (default: from METRICS_BACKEND env var or clickhouse)'
    )

    return parser.parse_args()


def run_profiler(
    table_name: str,
    output_format: str = 'table',
    output_file: Optional[str] = None,
    store_metrics: bool = True,
    application: str = 'default',
    environment: str = 'development',
    include_auto_increment: bool = False,
    lookback_days: int = 7,
    database_type: str = 'postgresql',
    metrics_backend: Optional[str] = None
) -> Optional[int]:
    """
    Run the data profiler for a specific table.
    
    Args:
        table_name: Name of the table to profile
        output_format: Output format (table, markdown, json, csv)
        output_file: Optional file path to save output
        store_metrics: Whether to store results in metrics backend
        application: Application name
        environment: Environment name
        include_auto_increment: Whether to profile auto-increment columns
        lookback_days: Days of historical data for growth rate calculation
        database_type: Database type (postgresql or mssql)
        metrics_backend: Backend for storing metrics (clickhouse or postgresql)
        
    Returns:
        Number of column profiles generated, or None if failed
    """
    db_type = normalize_database_type(database_type)
    
    # Determine metrics backend
    backend = metrics_backend or Config.METRICS_BACKEND
    logger.info(f"Starting profiler for table: '{table_name}' [{application}/{environment}] (database: {db_type}, metrics: {backend})")
    
    # Step 1: Initialize metrics backend (if storing)
    if store_metrics:
        if backend == 'postgresql':
            if not init_postgres_metrics():
                logger.error("Aborting: PostgreSQL metrics initialization failed")
                return None
        else:
            if not init_clickhouse():
                logger.error("Aborting: ClickHouse initialization failed")
                return None
            if include_auto_increment:
                if not init_autoincrement_table():
                    logger.error("Aborting: Auto-increment table initialization failed")
                    return None
    
    # Step 2: Get table metadata
    try:
        logger.info(f"Discovering schema for '{table_name}'...")
        columns = get_table_metadata(table_name, db_type)
    except TableNotFoundError as e:
        logger.error(f"❌ {e}")
        return None
    except DatabaseConnectionError as e:
        logger.error(f"❌ Database error: {e}")
        return None
    
    if not columns:
        logger.warning(f"No columns found in table '{table_name}'")
        return 0
    
    logger.info(f"Found {len(columns)} columns to profile")
    
    # Step 3: Calculate metrics for all columns
    try:
        table_profile = profile_table(table_name, columns, db_type)
    except Exception as e:
        logger.error(f"❌ Profiling failed: {e}")
        return None
    
    # Step 4: Format and output results
    try:
        formatted_output = format_profile(table_profile, output_format)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(formatted_output)
            logger.info(f"✅ Profile saved to: {output_file}")
        else:
            print(formatted_output)
            
    except Exception as e:
        logger.error(f"❌ Output formatting failed: {e}")
        return None
    
    # Step 5: Store in metrics backend (if enabled)
    if store_metrics:
        if backend == 'postgresql':
            if insert_profiles_pg(table_profile, application=application, environment=environment, database_type=db_type):
                logger.info(f"✅ Results stored in PostgreSQL (data_profiles)")
            else:
                logger.warning("Failed to store results in PostgreSQL")
        else:
            if insert_profiles(table_profile, application=application, environment=environment, database_type=db_type):
                logger.info(f"✅ Results stored in ClickHouse (data_profiles)")
            else:
                logger.warning("Failed to store results in ClickHouse")
    
    return len(table_profile.column_profiles)


def run_autoincrement_profiler(
    table_name: str,
    store_metrics: bool = True,
    application: str = 'default',
    environment: str = 'development',
    lookback_days: int = 7,
    database_type: str = 'postgresql',
    metrics_backend: Optional[str] = None
) -> Optional[int]:
    """
    Run auto-increment overflow analysis for a table.
    
    Args:
        table_name: Name of the table to analyze
        store_metrics: Whether to store results in metrics backend
        application: Application name
        environment: Environment name
        lookback_days: Days of historical data for growth rate
        database_type: Database type (postgresql or mssql)
        metrics_backend: Backend for storing metrics (clickhouse or postgresql)
        
    Returns:
        Number of auto-increment columns profiled, or None if failed
    """
    db_type = normalize_database_type(database_type)
    backend = metrics_backend or Config.METRICS_BACKEND
    logger.info(f"\n🔍 Auto-increment analysis for '{table_name}' (database: {db_type}, metrics: {backend})...")
    
    try:
        # Get detector for the specified database type
        detector = get_autoincrement_detector(db_type)
        
        # Get client for historical data (if storing)
        clickhouse_client = None
        pg_historical_fetcher = None
        if store_metrics:
            if backend == 'clickhouse':
                try:
                    clickhouse_client = get_clickhouse_client()
                except Exception as e:
                    logger.warning(f"Could not connect to ClickHouse for historical data: {e}")
            elif backend == 'postgresql':
                pg_historical_fetcher = fetch_historical_data_pg
        
        # Profile auto-increment columns
        profiles = profile_table_autoincrement(
            table_name=table_name,
            detector=detector,
            clickhouse_client=clickhouse_client,
            pg_historical_fetcher=pg_historical_fetcher,
            application=application,
            environment=environment,
            lookback_days=lookback_days,
        )
        
        if not profiles:
            logger.info("No auto-increment columns found in this table")
            return 0
        
        # Print summary
        print("\n" + "=" * 60)
        print("AUTO-INCREMENT OVERFLOW RISK ANALYSIS")
        print("=" * 60)
        for p in profiles:
            status_icon = "🔴" if p.alert_status == 'CRITICAL' else "🟡" if p.alert_status == 'WARNING' else "🟢"
            days_str = f"{p.days_until_full:.0f} days" if p.days_until_full else "N/A (need more data)"
            print(f"\n{status_icon} {p.table_name}.{p.column_name} ({p.data_type})")
            print(f"   Current: {p.current_value:,} / {p.max_type_value:,}")
            print(f"   Usage: {p.usage_percentage:.6f}%")
            print(f"   Days until full: {days_str}")
            if p.daily_growth_rate:
                print(f"   Growth rate: ~{p.daily_growth_rate:,.0f} IDs/day")
        print("=" * 60 + "\n")
        
        # Store in metrics backend
        if store_metrics and profiles:
            if backend == 'postgresql':
                if insert_autoincrement_profiles_pg(profiles, application, environment, database_type):
                    logger.info("✅ Auto-increment results stored in PostgreSQL")
                else:
                    logger.warning("Failed to store auto-increment results in PostgreSQL")
            else:
                if insert_autoincrement_profiles(profiles, application, environment, database_type):
                    logger.info("✅ Auto-increment results stored in ClickHouse")
                else:
                    logger.warning("Failed to store auto-increment results in ClickHouse")
        
        return len(profiles)
        
    except Exception as e:
        logger.error(f"❌ Auto-increment analysis failed: {e}")
        return None


def main():
    """Main entry point for the DataProfiler."""
    args = parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate configuration
    Config.validate()
    
    # Determine metrics backend
    metrics_backend = args.metrics_backend or Config.METRICS_BACKEND
    
    # Run the profiler
    result = run_profiler(
        table_name=args.table,
        output_format=args.format,
        output_file=args.output,
        store_metrics=not args.no_store,
        application=args.app,
        environment=args.env,
        include_auto_increment=args.auto_increment,
        lookback_days=args.lookback_days,
        database_type=args.database_type,
        metrics_backend=metrics_backend
    )
    
    # Run auto-increment analysis if requested
    if args.auto_increment:
        ai_result = run_autoincrement_profiler(
            table_name=args.table,
            store_metrics=not args.no_store,
            application=args.app,
            environment=args.env,
            lookback_days=args.lookback_days,
            database_type=args.database_type,
            metrics_backend=metrics_backend
        )
        if ai_result is None:
            logger.warning("Auto-increment analysis had issues")
    
    if result is None:
        logger.error("Profiling failed")
        sys.exit(1)
    elif result == 0:
        logger.warning("No profiles were generated")
        sys.exit(0)
    else:
        logger.info(f"Profiling completed: {result} columns profiled")
        sys.exit(0)


if __name__ == "__main__":
    main()
