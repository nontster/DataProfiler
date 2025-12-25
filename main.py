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
from src.db.postgres import get_table_metadata
from src.db.clickhouse import (
    init_clickhouse, insert_profiles,
    init_autoincrement_table, insert_autoincrement_profiles,
    get_clickhouse_client
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
  python main.py users                      # Profile 'users' table, console output
  python main.py users --format markdown    # Output as Markdown table
  python main.py users --format json        # Output as JSON
  python main.py users --format csv         # Output as CSV
  python main.py users -o users.md          # Save to file
  python main.py users --no-store           # Don't save to ClickHouse
  python main.py users --auto-increment     # Include auto-increment overflow analysis
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

    return parser.parse_args()


def run_profiler(
    table_name: str,
    output_format: str = 'table',
    output_file: Optional[str] = None,
    store_to_clickhouse: bool = True,
    application: str = 'default',
    environment: str = 'development',
    include_auto_increment: bool = False,
    lookback_days: int = 7
) -> Optional[int]:
    """
    Run the data profiler for a specific table.
    
    Args:
        table_name: Name of the table to profile
        output_format: Output format (table, markdown, json, csv)
        output_file: Optional file path to save output
        store_to_clickhouse: Whether to store results in ClickHouse
        application: Application name
        environment: Environment name
        include_auto_increment: Whether to profile auto-increment columns
        lookback_days: Days of historical data for growth rate calculation
        
    Returns:
        Number of column profiles generated, or None if failed
    """
    logger.info(f"Starting profiler for table: '{table_name}' [{application}/{environment}]")
    
    # Step 1: Initialize ClickHouse (if storing)
    if store_to_clickhouse:
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
        columns = get_table_metadata(table_name)
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
        table_profile = profile_table(table_name, columns)
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
    
    # Step 5: Store in ClickHouse (if enabled)
    if store_to_clickhouse:
        if insert_profiles(table_profile, application=application, environment=environment):
            logger.info(f"✅ Results stored in ClickHouse (data_profiles)")
        else:
            logger.warning("Failed to store results in ClickHouse")
    
    return len(table_profile.column_profiles)


def run_autoincrement_profiler(
    table_name: str,
    store_to_clickhouse: bool = True,
    application: str = 'default',
    environment: str = 'development',
    lookback_days: int = 7
) -> Optional[int]:
    """
    Run auto-increment overflow analysis for a table.
    
    Args:
        table_name: Name of the table to analyze
        store_to_clickhouse: Whether to store results in ClickHouse
        application: Application name
        environment: Environment name
        lookback_days: Days of historical data for growth rate
        
    Returns:
        Number of auto-increment columns profiled, or None if failed
    """
    logger.info(f"\n🔍 Auto-increment analysis for '{table_name}'...")
    
    try:
        # Get detector for PostgreSQL
        detector = get_autoincrement_detector('postgresql')
        
        # Get ClickHouse client for historical data (if storing)
        clickhouse_client = None
        if store_to_clickhouse:
            try:
                clickhouse_client = get_clickhouse_client()
            except Exception as e:
                logger.warning(f"Could not connect to ClickHouse for historical data: {e}")
        
        # Profile auto-increment columns
        profiles = profile_table_autoincrement(
            table_name=table_name,
            detector=detector,
            clickhouse_client=clickhouse_client,
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
        
        # Store in ClickHouse
        if store_to_clickhouse and profiles:
            if insert_autoincrement_profiles(profiles, application, environment):
                logger.info("✅ Auto-increment results stored in ClickHouse")
            else:
                logger.warning("Failed to store auto-increment results")
        
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
    
    # Run the profiler
    result = run_profiler(
        table_name=args.table,
        output_format=args.format,
        output_file=args.output,
        store_to_clickhouse=not args.no_store,
        application=args.app,
        environment=args.env,
        include_auto_increment=args.auto_increment,
        lookback_days=args.lookback_days
    )
    
    # Run auto-increment analysis if requested
    if args.auto_increment:
        ai_result = run_autoincrement_profiler(
            table_name=args.table,
            store_to_clickhouse=not args.no_store,
            application=args.app,
            environment=args.env,
            lookback_days=args.lookback_days
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
