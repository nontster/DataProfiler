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
from src.db.connection_factory import get_table_metadata, normalize_database_type, list_tables
from src.db.clickhouse import (
    init_clickhouse, insert_profiles,
    init_autoincrement_table, insert_autoincrement_profiles,
    get_clickhouse_client,
    init_table_inventory, insert_table_inventory
)
from src.db.postgres_metrics import (
    init_postgres_metrics, insert_profiles_pg,
    insert_autoincrement_profiles_pg, fetch_historical_data_pg,
    init_table_inventory_pg, insert_table_inventory_pg
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
  # Table inventory only (default — no --table needed)
  python main.py -d mssql --schema prod --app order-svc --env production

  # Data profiling (requires --table + --data-profile)
  python main.py -t users --data-profile
  python main.py -t users,orders --data-profile -d mssql --schema prod
  python main.py -t users --data-profile --format json -o users.json

  # Auto-increment analysis (requires --data-profile)
  python main.py -t users --data-profile --auto-increment

  # Schema profiling (requires --table)
  python main.py -t users --profile-schema

  # Combined
  python main.py -t users --data-profile --profile-schema --auto-increment
        """
    )
    
    parser.add_argument(
        '-t', '--table',
        default=None,
        help='Comma-separated list of table names to profile (e.g., users,orders,products)'
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
        choices=['postgresql', 'mssql', 'mysql'],
        default='postgresql',
        help='Database type to profile (default: postgresql)'
    )

    parser.add_argument(
        '--metrics-backend',
        choices=['clickhouse', 'postgresql'],
        default=None,
        help='Backend for storing metrics (default: from METRICS_BACKEND env var or postgresql)'
    )

    parser.add_argument(
        '--schema',
        default=None,
        help='Database schema (default: public for PG, dbo for MSSQL)'
    )

    # Schema profiling argument
    parser.add_argument(
        '--profile-schema',
        action='store_true',
        help='Profile table schema and store in metrics database (for Grafana comparison)'
    )

    # Data profiling argument
    parser.add_argument(
        '--data-profile',
        action='store_true',
        help='Run data profiling (column-level statistics). Requires --table.'
    )

    return parser.parse_args()


def init_metrics_backend(
    store_metrics: bool,
    metrics_backend: str,
    include_auto_increment: bool = False
) -> bool:
    """
    Initialize metrics backend once before processing tables.
    
    Args:
        store_metrics: Whether to store results in metrics backend
        metrics_backend: Backend type ('clickhouse' or 'postgresql')
        include_auto_increment: Whether auto-increment analysis is enabled
        
    Returns:
        True if initialization successful (or not needed), False otherwise
    """
    if not store_metrics:
        return True
    
    backend = metrics_backend or Config.METRICS_BACKEND
    logger.info(f"Initializing metrics backend: {backend}")
    
    if backend == 'postgresql':
        if not init_postgres_metrics():
            logger.error("PostgreSQL metrics initialization failed")
            return False
        if not init_table_inventory_pg():
            logger.error("Table inventory initialization failed")
            return False
    else:
        if not init_clickhouse():
            logger.error("ClickHouse initialization failed")
            return False
        if include_auto_increment:
            if not init_autoincrement_table():
                logger.error("Auto-increment table initialization failed")
                return False
        if not init_table_inventory():
            logger.error("Table inventory initialization failed")
            return False
    
    logger.info(f"✅ Metrics backend '{backend}' initialized successfully")
    return True


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
    metrics_backend: Optional[str] = None,
    schema: Optional[str] = None
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
        schema: Database schema
        
    Returns:
        Number of column profiles generated, or None if failed
    """
    db_type = normalize_database_type(database_type)
    
    # Determine metrics backend
    backend = metrics_backend or Config.METRICS_BACKEND
    schema_info = f"schema: {schema}" if schema else "default schema"
    logger.info(f"Starting profiler for table: '{table_name}' [{application}/{environment}] (database: {db_type}, {schema_info}, metrics: {backend})")
    
    # Step 2: Get table metadata
    try:
        logger.info(f"Discovering schema for '{table_name}'...")
        # Note: get_table_metadata needs to be updated to accept schema if not already
        columns = get_table_metadata(table_name, db_type, schema=schema)
    except TableNotFoundError as e:
        logger.error(f"❌ {e}")
        return None
    except DatabaseConnectionError as e:
        logger.error(f"❌ Database error: {e}")
        return None
    except TypeError as e:
        # Fallback if get_table_metadata doesn't support schema yet
        if "unexpected keyword argument 'schema'" in str(e):
             logger.warning("get_table_metadata does not support schema arg yet, trying without")
             columns = get_table_metadata(table_name, db_type)
        else:
            raise e
    
    if not columns:
        logger.warning(f"No columns found in table '{table_name}'")
        return 0
    
    logger.info(f"Found {len(columns)} columns to profile")
    
    # Step 3: Calculate metrics for all columns
    try:
        # Note: profile_table might need schema if it queries data directly
        table_profile = profile_table(table_name, columns, db_type, schema=schema)
    except Exception as e:
        logger.error(f"❌ Profiling failed: {e}")
        return None
    
    # Step 4: Format and output results
    try:
        formatted_output = format_profile(table_profile, output_format)
        
        if output_file:
            with open(output_file, 'a', encoding='utf-8') as f:
                f.write(formatted_output)
                f.write('\n')  # Separator between tables
            logger.info(f"✅ Profile appended to: {output_file}")
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
    metrics_backend: Optional[str] = None,
    schema: Optional[str] = None
) -> Optional[int]:
    """
    Run auto-increment overflow analysis for a table.
    """
    db_type = normalize_database_type(database_type)
    backend = metrics_backend or Config.METRICS_BACKEND
    schema_info = f"schema: {schema}" if schema else "default schema"
    logger.info(f"\n🔍 Auto-increment analysis for '{table_name}' (database: {db_type}, {schema_info}, metrics: {backend})...")
    
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
        # Note: profile_table_autoincrement needs schema support
        profiles = profile_table_autoincrement(
            table_name=table_name,
            detector=detector,
            clickhouse_client=clickhouse_client,
            pg_historical_fetcher=pg_historical_fetcher,
            application=application,
            environment=environment,
            lookback_days=lookback_days,
            schema=schema
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


def get_database_connection(database_type: str):
    """
    Get a database connection for the given database type.
    Used for schema profiling with connection reuse.
    
    Args:
        database_type: Database type (postgresql, mssql, mysql)
        
    Returns:
        Database connection object
    """
    if database_type == 'postgresql':
        from src.db.postgres import get_postgres_connection
        return get_postgres_connection()
    elif database_type == 'mysql':
        from src.db.mysql import get_mysql_connection
        return get_mysql_connection()
    else:
        from src.db.mssql import get_mssql_connection
        return get_mssql_connection()


def run_schema_profiler(
    table_name: str,
    application: str = 'default',
    environment: str = 'development',
    database_type: str = 'postgresql',
    metrics_backend: Optional[str] = None,
    schema: Optional[str] = None,
    conn=None
) -> Optional[int]:
    """
    Profile table schema and store in metrics database.
    
    Args:
        table_name: Name of the table to profile
        application: Application name
        environment: Environment name
        database_type: Database type (postgresql, mssql)
        metrics_backend: Backend for storing metrics
        schema: Database schema
        conn: Optional existing database connection (for reuse across tables)
        
    Returns:
        Number of columns profiled, or None on error
    """
    from src.db.schema_extractor import get_schema_extractor
    
    schema_info = f"schema: {schema}" if schema else "default schema"
    logger.info(f"Profiling schema for '{table_name}' [{application}/{environment}] ({schema_info})")
    
    own_connection = conn is None
    try:
        # Get or reuse database connection
        if own_connection:
            conn = get_database_connection(database_type)
        
        # Extract schema
        extractor = get_schema_extractor(database_type, conn)
        # Pass schema explicitly
        table_schema = extractor.extract_table_schema(table_name, schema_name=schema)
        
        # Store in metrics database
        backend = metrics_backend or Config.METRICS_BACKEND
        
        if backend == 'postgresql':
            from src.db.postgres_metrics import (
                init_schema_profiles_pg,
                insert_schema_profiles_pg
            )
            init_schema_profiles_pg()
            insert_schema_profiles_pg(table_schema, application, environment)
        else:
            from src.db.clickhouse import (
                init_schema_profiles_clickhouse,
                insert_schema_profiles
            )
            init_schema_profiles_clickhouse()
            insert_schema_profiles(table_schema, application, environment)
        
        logger.info(f"✅ Schema profile stored: {len(table_schema.columns)} columns")
        return len(table_schema.columns)
        
    except Exception as e:
        logger.error(f"Schema profiling failed: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        # Only close if we created the connection
        if own_connection and conn:
            try:
                conn.close()
            except Exception:
                pass


def run_schema_objects_profiler(
    application: str = 'default',
    environment: str = 'development',
    database_type: str = 'postgresql',
    metrics_backend: Optional[str] = None,
    schema: Optional[str] = None,
    conn=None
) -> Optional[int]:
    """
    Profile schema-level objects (stored procedures, views, triggers)
    and store in metrics database. Called once per schema, not per table.
    
    Args:
        application: Application name
        environment: Environment name
        database_type: Database type (postgresql, mssql, mysql)
        metrics_backend: Backend for storing metrics
        schema: Database schema
        conn: Optional existing database connection
        
    Returns:
        Total number of objects profiled, or None on error
    """
    from src.db.schema_extractor import get_schema_extractor
    
    schema_info = f"schema: {schema}" if schema else "default schema"
    logger.info(f"Profiling schema objects [{application}/{environment}] ({schema_info})")
    
    own_connection = conn is None
    try:
        if own_connection:
            conn = get_database_connection(database_type)
        
        extractor = get_schema_extractor(database_type, conn)
        
        # Extract schema-level objects
        procedures = extractor.extract_stored_procedures(schema_name=schema)
        views = extractor.extract_views(schema_name=schema)
        triggers = extractor.extract_triggers(schema_name=schema)
        
        total = len(procedures) + len(views) + len(triggers)
        logger.info(
            f"Found {total} schema objects: "
            f"{len(procedures)} procedures, {len(views)} views, {len(triggers)} triggers"
        )
        
        if total == 0:
            logger.info("No schema objects found — skipping storage")
            return 0
        
        # Determine connection info for metadata
        db_host = ''
        db_name = ''
        if database_type == 'postgresql':
            db_host = Config.POSTGRES_HOST or ''
            db_name = Config.POSTGRES_DATABASE or ''
        elif database_type == 'mssql':
            db_host = Config.MSSQL_HOST or ''
            db_name = Config.MSSQL_DATABASE or ''
        elif database_type == 'mysql':
            db_host = Config.MYSQL_HOST or ''
            db_name = Config.MYSQL_DATABASE or ''
        
        schema_name = schema or 'public'
        
        # Store in metrics backend
        backend = metrics_backend or Config.METRICS_BACKEND
        
        if backend == 'postgresql':
            from src.db.postgres_metrics import (
                init_schema_objects_pg,
                insert_schema_objects_pg
            )
            init_schema_objects_pg()
            insert_schema_objects_pg(
                procedures, views, triggers,
                database_host=db_host,
                database_name=db_name,
                schema_name=schema_name,
                application=application,
                environment=environment,
            )
        else:
            from src.db.clickhouse import (
                init_schema_objects_clickhouse,
                insert_schema_objects
            )
            init_schema_objects_clickhouse()
            insert_schema_objects(
                procedures, views, triggers,
                database_host=db_host,
                database_name=db_name,
                schema_name=schema_name,
                application=application,
                environment=environment,
            )
        
        logger.info(f"✅ Schema objects profile stored: {total} objects")
        return total
        
    except Exception as e:
        logger.error(f"Schema objects profiling failed: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        if own_connection and conn:
            try:
                conn.close()
            except Exception:
                pass


def main():
    """Main entry point for the DataProfiler."""
    args = parse_args()
    
    # --- Cross-parameter validation ---
    needs_table = args.data_profile or args.profile_schema or args.auto_increment
    
    if needs_table and not args.table:
        print("Error: --table/-t is required when using --data-profile, --profile-schema, or --auto-increment.", file=sys.stderr)
        print("Usage: python main.py --table <table1>[,<table2>,...] --data-profile [options]", file=sys.stderr)
        sys.exit(1)
    
    if args.auto_increment and not args.data_profile:
        print("Error: --auto-increment requires --data-profile.", file=sys.stderr)
        sys.exit(1)
    
    if (args.format != 'table' or args.output) and not args.data_profile:
        logger.warning("--format/--output have no effect without --data-profile")
    
    if args.lookback_days != 7 and not args.auto_increment:
        logger.warning("--lookback-days has no effect without --auto-increment")
    
    # Parse comma-separated table names (may be empty for inventory-only mode)
    table_names = []
    if args.table:
        table_names = [t.strip() for t in args.table.split(',') if t.strip()]
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate configuration
    Config.validate()
    
    # Determine metrics backend
    metrics_backend = args.metrics_backend or Config.METRICS_BACKEND
    
    logger.info(f"Tables to process: {', '.join(table_names)} ({len(table_names)} table(s))")
    
    # Initialize metrics backend once before processing tables
    store_metrics = not args.no_store
    if not init_metrics_backend(store_metrics, metrics_backend, args.auto_increment):
        logger.error("Failed to initialize metrics backend. Aborting.")
        sys.exit(1)
    
    # Clear output file before appending (if specified)
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            pass  # Truncate file
        logger.info(f"Output file initialized: {args.output}")
    
    total_columns = 0
    failed_tables = []
    
    # --- Table Inventory: auto-collect table list ---
    if store_metrics:
        try:
            schema_for_inventory = args.schema
            discovered_tables = list_tables(args.database_type, schema=schema_for_inventory)
            logger.info(f"Discovered {len(discovered_tables)} tables in schema '{schema_for_inventory or 'default'}'")
            
            if metrics_backend == 'postgresql':
                insert_table_inventory_pg(
                    tables=discovered_tables,
                    schema=schema_for_inventory or 'public',
                    application=args.app,
                    environment=args.env,
                    database_type=args.database_type
                )
            else:
                insert_table_inventory(
                    tables=discovered_tables,
                    schema=schema_for_inventory or 'public',
                    application=args.app,
                    environment=args.env,
                    database_type=args.database_type
                )
        except Exception as e:
            logger.warning(f"Table inventory collection failed (non-fatal): {e}")
        
        # --- Schema Objects: auto-collect stored procedures, views, triggers ---
        try:
            obj_result = run_schema_objects_profiler(
                application=args.app,
                environment=args.env,
                database_type=args.database_type,
                metrics_backend=metrics_backend,
                schema=args.schema,
            )
            
            if obj_result is None:
                logger.warning("Schema objects profiling failed (non-fatal)")
            elif obj_result == 0:
                logger.info("No schema objects found in this schema")
            else:
                logger.info(f"Schema objects profiling completed: {obj_result} objects")
        except Exception as e:
            logger.warning(f"Schema objects collection failed (non-fatal): {e}")
    
    # Open shared connection for schema profiling (reuse across tables)
    schema_conn = None
    if args.profile_schema:
        try:
            schema_conn = get_database_connection(args.database_type)
            logger.info(f"Database connection established for schema profiling")
        except Exception as e:
            logger.error(f"Failed to establish database connection for schema profiling: {e}")
            sys.exit(1)
    
    try:
        for table_name in table_names:
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing table: {table_name}")
            logger.info(f"{'='*60}")
            
            # Handle schema profiling mode
            if args.profile_schema:
                result = run_schema_profiler(
                    table_name=table_name,
                    application=args.app,
                    environment=args.env,
                    database_type=args.database_type,
                    metrics_backend=metrics_backend,
                    schema=args.schema,
                    conn=schema_conn
                )
                
                if result is None:
                    logger.error(f"Schema profiling failed for table: {table_name}")
                    failed_tables.append(table_name)
                    continue
                
                logger.info(f"Schema profiling completed for '{table_name}': {result} columns")
        
            # Run data profiling (only if --data-profile flag is set)
            if args.data_profile:
                result = run_profiler(
                    table_name=table_name,
                    output_format=args.format,
                    output_file=args.output,
                    store_metrics=store_metrics,
                    application=args.app,
                    environment=args.env,
                    include_auto_increment=args.auto_increment,
                    lookback_days=args.lookback_days,
                    database_type=args.database_type,
                    metrics_backend=metrics_backend,
                    schema=args.schema
                )
                
                # Run auto-increment analysis if requested
                if args.auto_increment:
                    ai_result = run_autoincrement_profiler(
                        table_name=table_name,
                        store_metrics=store_metrics,
                        application=args.app,
                        environment=args.env,
                        lookback_days=args.lookback_days,
                        database_type=args.database_type,
                        metrics_backend=metrics_backend,
                        schema=args.schema
                    )
                    if ai_result is None:
                        logger.warning(f"Auto-increment analysis had issues for table: {table_name}")
                
                if result is None:
                    logger.error(f"Profiling failed for table: {table_name}")
                    failed_tables.append(table_name)
                elif result == 0:
                    logger.warning(f"No profiles were generated for table: {table_name}")
                else:
                    total_columns += result
                    logger.info(f"Profiling completed for '{table_name}': {result} columns profiled")
    finally:
        # Close shared schema profiling connection
        if schema_conn:
            try:
                schema_conn.close()
                logger.info("Schema profiling connection closed")
            except Exception:
                pass
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info(f"SUMMARY: {len(table_names)} table(s) processed, {total_columns} total columns profiled")
    if failed_tables:
        logger.error(f"Failed tables: {', '.join(failed_tables)}")
    logger.info(f"{'='*60}")
    
    if failed_tables:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
