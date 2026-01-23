"""
Flask API backend for Data Profile Dashboard (Multi-Environment).
Serves profiling data from ClickHouse or PostgreSQL based on configuration.
"""

import os
import sys
from flask import Flask, jsonify, request
from flask_cors import CORS

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import clickhouse_connect
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))

app = Flask(__name__)
CORS(app)

# Metrics backend configuration (fixed at launch)
METRICS_BACKEND = os.getenv('METRICS_BACKEND', 'clickhouse')

# ClickHouse configuration
CH_HOST = os.getenv('CLICKHOUSE_HOST', 'localhost')
CH_PORT = int(os.getenv('CLICKHOUSE_PORT', 8123))
CH_USER = os.getenv('CLICKHOUSE_USER', 'default')
CH_PASSWORD = os.getenv('CLICKHOUSE_PASSWORD', '')

# PostgreSQL Metrics configuration
PG_HOST = os.getenv('PG_METRICS_HOST', os.getenv('POSTGRES_HOST', 'localhost'))
PG_PORT = int(os.getenv('PG_METRICS_PORT', os.getenv('POSTGRES_PORT', 5432)))
PG_DATABASE = os.getenv('PG_METRICS_DATABASE', os.getenv('POSTGRES_DATABASE', 'postgres'))
PG_USER = os.getenv('PG_METRICS_USER', os.getenv('POSTGRES_USER', 'postgres'))
PG_PASSWORD = os.getenv('PG_METRICS_PASSWORD', os.getenv('POSTGRES_PASSWORD', ''))


def get_clickhouse_client():
    """Get ClickHouse client."""
    return clickhouse_connect.get_client(
        host=CH_HOST,
        port=CH_PORT,
        username=CH_USER,
        password=CH_PASSWORD
    )


def get_postgres_connection():
    """Get PostgreSQL connection for metrics."""
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DATABASE,
        user=PG_USER,
        password=PG_PASSWORD
    )


# ============================================================================
# API Endpoints
# ============================================================================

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current backend configuration."""
    return jsonify({
        'metrics_backend': METRICS_BACKEND,
        'backend_display_name': 'PostgreSQL' if METRICS_BACKEND == 'postgresql' else 'ClickHouse'
    })


@app.route('/api/metadata', methods=['GET'])
def get_metadata():
    """Get distinct applications and environments."""
    if METRICS_BACKEND == 'postgresql':
        return get_metadata_pg()
    return get_metadata_ch()


def get_metadata_ch():
    """Get metadata from ClickHouse."""
    client = get_clickhouse_client()
    
    query = """
        SELECT DISTINCT application, environment 
        FROM data_profiles
        ORDER BY application, environment
    """
    result = client.query(query)
    
    apps = {}
    for row in result.result_rows:
        app_name = row[0]
        env_name = row[1]
        
        if app_name not in apps:
            apps[app_name] = []
        apps[app_name].append(env_name)
    
    # Format for easy frontend consumption
    metadata = []
    for app_name, envs in apps.items():
        metadata.append({
            'application': app_name,
            'environments': envs
        })
        
    return jsonify(metadata)


def get_metadata_pg():
    """Get metadata from PostgreSQL."""
    conn = get_postgres_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    query = """
        SELECT DISTINCT application, environment 
        FROM data_profiles
        ORDER BY application, environment
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    apps = {}
    for row in rows:
        app_name = row['application']
        env_name = row['environment']
        
        if app_name not in apps:
            apps[app_name] = []
        apps[app_name].append(env_name)
    
    # Format for easy frontend consumption
    metadata = []
    for app_name, envs in apps.items():
        metadata.append({
            'application': app_name,
            'environments': envs
        })
        
    return jsonify(metadata)


@app.route('/api/tables', methods=['GET'])
def get_tables():
    """Get list of profiled tables filtered by app and env."""
    application = request.args.get('app')
    environment = request.args.get('env')
    
    if METRICS_BACKEND == 'postgresql':
        return get_tables_pg(application, environment)
    return get_tables_ch(application, environment)


def get_tables_ch(application, environment):
    """Get tables from ClickHouse."""
    query = """
        SELECT 
            table_name,
            max(row_count) as row_count,
            count(DISTINCT column_name) as column_count,
            max(scan_time) as last_profiled
        FROM data_profiles
        WHERE 1=1
    """
    
    if application:
        query += f" AND application = '{application}'"
    if environment:
        query += f" AND environment = '{environment}'"
        
    query += """
        GROUP BY table_name
        ORDER BY table_name
    """
    
    client = get_clickhouse_client()
    result = client.query(query)
    
    tables = []
    for row in result.result_rows:
        tables.append({
            'table_name': row[0],
            'row_count': row[1],
            'column_count': row[2],
            'last_profiled': row[3].isoformat() if row[3] else None
        })
    
    return jsonify(tables)


def get_tables_pg(application, environment):
    """Get tables from PostgreSQL."""
    query = """
        SELECT 
            table_name,
            max(row_count) as row_count,
            count(DISTINCT column_name) as column_count,
            max(scan_time) as last_profiled
        FROM data_profiles
        WHERE 1=1
    """
    
    params = []
    if application:
        query += " AND application = %s"
        params.append(application)
    if environment:
        query += " AND environment = %s"
        params.append(environment)
        
    query += """
        GROUP BY table_name
        ORDER BY table_name
    """
    
    conn = get_postgres_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    tables = []
    for row in rows:
        tables.append({
            'table_name': row['table_name'],
            'row_count': row['row_count'],
            'column_count': row['column_count'],
            'last_profiled': row['last_profiled'].isoformat() if row['last_profiled'] else None
        })
    
    return jsonify(tables)


@app.route('/api/profiles/<table_name>', methods=['GET'])
def get_profiles(table_name):
    """Get latest profile for a specific table."""
    application = request.args.get('app', 'default')
    environment = request.args.get('env', 'development')
    
    client = get_clickhouse_client()
    
    # Get the latest scan_time for this table/app/env
    latest_query = f"""
        SELECT max(scan_time) 
        FROM data_profiles 
        WHERE table_name = '{table_name}' 
          AND application = '{application}'
          AND environment = '{environment}'
    """
    latest_result = client.query(latest_query)
    latest_time = latest_result.result_rows[0][0] if latest_result.result_rows else None
    
    if not latest_time:
        return jsonify({'error': 'Table not found'}), 404
    
    # Get all columns for the latest scan
    query = f"""
        SELECT 
            column_name,
            data_type,
            row_count,
            not_null_proportion,
            distinct_proportion,
            distinct_count,
            is_unique,
            min,
            max,
            avg,
            median,
            std_dev_population,
            std_dev_sample,
            scan_time
        FROM data_profiles
        WHERE table_name = '{table_name}' 
          AND scan_time = '{latest_time}'
          AND application = '{application}'
          AND environment = '{environment}'
        ORDER BY column_name
    """
    
    result = client.query(query)
    
    columns = []
    for row in result.result_rows:
        columns.append({
            'column_name': row[0],
            'data_type': row[1],
            'row_count': row[2],
            'not_null_proportion': row[3],
            'distinct_proportion': row[4],
            'distinct_count': row[5],
            'is_unique': bool(row[6]),
            'min': row[7],
            'max': row[8],
            'avg': row[9],
            'median': row[10],
            'std_dev_population': row[11],
            'std_dev_sample': row[12],
            'scan_time': row[13].isoformat() if row[13] else None
        })
    
    return jsonify({
        'table_name': table_name,
        'application': application,
        'environment': environment,
        'row_count': columns[0]['row_count'] if columns else 0,
        'columns': columns
    })


@app.route('/api/profiles/compare/<table_name>', methods=['GET'])
def compare_profiles(table_name):
    """Compare profiles between two environments."""
    application = request.args.get('app', 'default')
    env1 = request.args.get('env1')
    env2 = request.args.get('env2')
    
    if not env1 or not env2:
        return jsonify({'error': 'Both env1 and env2 are required'}), 400
    
    if METRICS_BACKEND == 'postgresql':
        return compare_profiles_pg(table_name, application, env1, env2)
    return compare_profiles_ch(table_name, application, env1, env2)


def compare_profiles_ch(table_name, application, env1, env2):
    """Compare profiles using ClickHouse backend."""
    client = get_clickhouse_client()
    
    def get_latest_profile(env):
        """Get the latest profile for an environment."""
        # Get the latest scan_time for this table/app/env
        latest_query = f"""
            SELECT max(scan_time) 
            FROM data_profiles 
            WHERE table_name = '{table_name}' 
              AND application = '{application}'
              AND environment = '{env}'
        """
        latest_result = client.query(latest_query)
        latest_time = latest_result.result_rows[0][0] if latest_result.result_rows else None
        
        if not latest_time:
            return None
        
        query = f"""
            SELECT 
                column_name,
                data_type,
                row_count,
                not_null_proportion,
                distinct_proportion,
                distinct_count,
                is_unique,
                min,
                max,
                avg,
                median,
                std_dev_population,
                std_dev_sample,
                scan_time,
                database_host
            FROM data_profiles
            WHERE table_name = '{table_name}' 
              AND scan_time = '{latest_time}'
              AND application = '{application}'
              AND environment = '{env}'
            ORDER BY column_name
        """
        
        result = client.query(query)
        
        columns = {}
        row_count = 0
        scan_time = None
        database_host = None
        for row in result.result_rows:
            columns[row[0]] = {
                'column_name': row[0],
                'data_type': row[1],
                'row_count': row[2],
                'not_null_proportion': row[3],
                'distinct_proportion': row[4],
                'distinct_count': row[5],
                'is_unique': bool(row[6]),
                'min': row[7],
                'max': row[8],
                'avg': row[9],
                'median': row[10],
                'std_dev_population': row[11],
                'std_dev_sample': row[12],
                'scan_time': row[13].isoformat() if row[13] else None
            }
            row_count = row[2]
            scan_time = row[13].isoformat() if row[13] else None
            database_host = row[14] if len(row) > 14 else None
        
        return {
            'columns': columns,
            'row_count': row_count,
            'scan_time': scan_time,
            'database_host': database_host
        }
    
    profile1 = get_latest_profile(env1)
    profile2 = get_latest_profile(env2)
    
    # Get all unique column names from both profiles
    all_columns = set()
    if profile1:
        all_columns.update(profile1['columns'].keys())
    if profile2:
        all_columns.update(profile2['columns'].keys())
    
    # Build comparison data
    comparison = []
    for col_name in sorted(all_columns):
        col1 = profile1['columns'].get(col_name) if profile1 else None
        col2 = profile2['columns'].get(col_name) if profile2 else None
        
        # Calculate differences
        not_null_diff = None
        distinct_diff = None
        if col1 and col2:
            if col1['not_null_proportion'] is not None and col2['not_null_proportion'] is not None:
                not_null_diff = col2['not_null_proportion'] - col1['not_null_proportion']
            if col1['distinct_proportion'] is not None and col2['distinct_proportion'] is not None:
                distinct_diff = col2['distinct_proportion'] - col1['distinct_proportion']
        
        comparison.append({
            'column_name': col_name,
            'data_type': col1['data_type'] if col1 else (col2['data_type'] if col2 else None),
            'env1': col1,
            'env2': col2,
            'not_null_diff': not_null_diff,
            'distinct_diff': distinct_diff,
            'in_env1': col1 is not None,
            'in_env2': col2 is not None
        })
    
    return jsonify({
        'table_name': table_name,
        'application': application,
        'env1': {
            'name': env1,
            'row_count': profile1['row_count'] if profile1 else None,
            'scan_time': profile1['scan_time'] if profile1 else None,
            'database_host': profile1['database_host'] if profile1 else None,
            'exists': profile1 is not None
        },
        'env2': {
            'name': env2,
            'row_count': profile2['row_count'] if profile2 else None,
            'scan_time': profile2['scan_time'] if profile2 else None,
            'database_host': profile2['database_host'] if profile2 else None,
            'exists': profile2 is not None
        },
        'columns': comparison
    })


def compare_profiles_pg(table_name, application, env1, env2):
    """Compare profiles using PostgreSQL backend."""
    conn = get_postgres_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    def get_latest_profile(env):
        """Get the latest profile for an environment."""
        # Get the latest scan_time for this table/app/env
        cursor.execute("""
            SELECT max(scan_time) 
            FROM data_profiles 
            WHERE table_name = %s 
              AND application = %s
              AND environment = %s
        """, (table_name, application, env))
        row = cursor.fetchone()
        latest_time = row['max'] if row else None
        
        if not latest_time:
            return None
        
        # Get all columns for the latest scan
        cursor.execute("""
            SELECT 
                column_name,
                data_type,
                row_count,
                not_null_proportion,
                distinct_proportion,
                distinct_count,
                is_unique,
                min_value,
                max_value,
                avg_value,
                median_value,
                std_dev_population,
                std_dev_sample,
                scan_time,
                database_host
            FROM data_profiles
            WHERE table_name = %s 
              AND scan_time = %s
              AND application = %s
              AND environment = %s
            ORDER BY column_name
        """, (table_name, latest_time, application, env))
        
        rows = cursor.fetchall()
        
        columns = {}
        row_count = 0
        scan_time = None
        database_host = None
        for row in rows:
            columns[row['column_name']] = {
                'column_name': row['column_name'],
                'data_type': row['data_type'],
                'row_count': row['row_count'],
                'not_null_proportion': row['not_null_proportion'],
                'distinct_proportion': row['distinct_proportion'],
                'distinct_count': row['distinct_count'],
                'is_unique': bool(row['is_unique']),
                'min': row['min_value'],
                'max': row['max_value'],
                'avg': row['avg_value'],
                'median': row['median_value'],
                'std_dev_population': row['std_dev_population'],
                'std_dev_sample': row['std_dev_sample'],
                'scan_time': row['scan_time'].isoformat() if row['scan_time'] else None
            }
            row_count = row['row_count']
            scan_time = row['scan_time'].isoformat() if row['scan_time'] else None
            database_host = row['database_host']
        
        return {
            'columns': columns,
            'row_count': row_count,
            'scan_time': scan_time,
            'database_host': database_host
        }
    
    profile1 = get_latest_profile(env1)
    profile2 = get_latest_profile(env2)
    
    cursor.close()
    conn.close()
    
    # Get all unique column names from both profiles
    all_columns = set()
    if profile1:
        all_columns.update(profile1['columns'].keys())
    if profile2:
        all_columns.update(profile2['columns'].keys())
    
    # Build comparison data
    comparison = []
    for col_name in sorted(all_columns):
        col1 = profile1['columns'].get(col_name) if profile1 else None
        col2 = profile2['columns'].get(col_name) if profile2 else None
        
        # Calculate differences
        not_null_diff = None
        distinct_diff = None
        if col1 and col2:
            if col1['not_null_proportion'] is not None and col2['not_null_proportion'] is not None:
                not_null_diff = col2['not_null_proportion'] - col1['not_null_proportion']
            if col1['distinct_proportion'] is not None and col2['distinct_proportion'] is not None:
                distinct_diff = col2['distinct_proportion'] - col1['distinct_proportion']
        
        comparison.append({
            'column_name': col_name,
            'data_type': col1['data_type'] if col1 else (col2['data_type'] if col2 else None),
            'env1': col1,
            'env2': col2,
            'not_null_diff': not_null_diff,
            'distinct_diff': distinct_diff,
            'in_env1': col1 is not None,
            'in_env2': col2 is not None
        })
    
    return jsonify({
        'table_name': table_name,
        'application': application,
        'env1': {
            'name': env1,
            'row_count': profile1['row_count'] if profile1 else None,
            'scan_time': profile1['scan_time'] if profile1 else None,
            'database_host': profile1['database_host'] if profile1 else None,
            'exists': profile1 is not None
        },
        'env2': {
            'name': env2,
            'row_count': profile2['row_count'] if profile2 else None,
            'scan_time': profile2['scan_time'] if profile2 else None,
            'database_host': profile2['database_host'] if profile2 else None,
            'exists': profile2 is not None
        },
        'columns': comparison
    })


@app.route('/api/autoincrement/<table_name>', methods=['GET'])
def get_autoincrement(table_name):
    """Get auto-increment overflow risk data for a specific table."""
    application = request.args.get('app', 'default')
    environment = request.args.get('env', 'development')
    
    if METRICS_BACKEND == 'postgresql':
        return get_autoincrement_pg(table_name, application, environment)
    return get_autoincrement_ch(table_name, application, environment)


def get_autoincrement_ch(table_name, application, environment):
    """Get auto-increment data from ClickHouse."""
    client = get_clickhouse_client()
    
    # Get the latest auto-increment metrics for this table
    query = f"""
        SELECT 
            column_name,
            data_type,
            current_value,
            max_type_value,
            usage_percentage,
            remaining_values,
            days_until_full,
            daily_growth_rate,
            alert_status,
            scan_time
        FROM auto_increment_metrics
        WHERE table_name = '{table_name}'
          AND application = '{application}'
          AND environment = '{environment}'
        ORDER BY scan_time DESC
        LIMIT 1 BY column_name
    """
    
    try:
        result = client.query(query)
        
        columns = []
        for row in result.result_rows:
            columns.append({
                'column_name': row[0],
                'data_type': row[1],
                'current_value': row[2],
                'max_type_value': row[3],
                'usage_percentage': row[4],
                'remaining_values': row[5],
                'days_until_full': row[6],
                'daily_growth_rate': row[7],
                'alert_status': row[8],
                'scan_time': row[9].isoformat() if row[9] else None
            })
        
        return jsonify({
            'table_name': table_name,
            'application': application,
            'environment': environment,
            'columns': columns
        })
    except Exception as e:
        # Table might not have auto-increment columns or no data yet
        return jsonify({
            'table_name': table_name,
            'application': application,
            'environment': environment,
            'columns': []
        })


def get_autoincrement_pg(table_name, application, environment):
    """Get auto-increment data from PostgreSQL."""
    try:
        conn = get_postgres_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT DISTINCT ON (column_name)
                column_name,
                data_type,
                current_value,
                max_type_value,
                usage_percentage,
                remaining_values,
                days_until_full,
                daily_growth_rate,
                alert_status,
                scan_time
            FROM auto_increment_metrics
            WHERE table_name = %s
              AND application = %s
              AND environment = %s
            ORDER BY column_name, scan_time DESC
        """, (table_name, application, environment))
        
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        columns = []
        for row in rows:
            columns.append({
                'column_name': row['column_name'],
                'data_type': row['data_type'],
                'current_value': row['current_value'],
                'max_type_value': row['max_type_value'],
                'usage_percentage': row['usage_percentage'],
                'remaining_values': row['remaining_values'],
                'days_until_full': row['days_until_full'],
                'daily_growth_rate': row['daily_growth_rate'],
                'alert_status': row['alert_status'],
                'scan_time': row['scan_time'].isoformat() if row['scan_time'] else None
            })
        
        return jsonify({
            'table_name': table_name,
            'application': application,
            'environment': environment,
            'columns': columns
        })
    except Exception as e:
        # Table might not have auto-increment columns or no data yet
        return jsonify({
            'table_name': table_name,
            'application': application,
            'environment': environment,
            'columns': []
        })


@app.route('/api/autoincrement/compare/<table_name>', methods=['GET'])
def compare_autoincrement(table_name):
    """Compare auto-increment overflow risk between two environments."""
    application = request.args.get('app', 'default')
    env1 = request.args.get('env1')
    env2 = request.args.get('env2')
    
    if not env1 or not env2:
        return jsonify({'error': 'Both env1 and env2 are required'}), 400
    
    if METRICS_BACKEND == 'postgresql':
        return compare_autoincrement_pg(table_name, application, env1, env2)
    return compare_autoincrement_ch(table_name, application, env1, env2)


def compare_autoincrement_ch(table_name, application, env1, env2):
    """Compare auto-increment using ClickHouse backend."""
    client = get_clickhouse_client()
    
    def get_autoincrement_data(env):
        query = f"""
            SELECT 
                column_name,
                data_type,
                current_value,
                max_type_value,
                usage_percentage,
                remaining_values,
                days_until_full,
                daily_growth_rate,
                alert_status,
                scan_time
            FROM auto_increment_metrics
            WHERE table_name = '{table_name}'
              AND application = '{application}'
              AND environment = '{env}'
            ORDER BY scan_time DESC
            LIMIT 1 BY column_name
        """
        try:
            result = client.query(query)
            data = {}
            for row in result.result_rows:
                data[row[0]] = {
                    'column_name': row[0],
                    'data_type': row[1],
                    'current_value': row[2],
                    'max_type_value': row[3],
                    'usage_percentage': row[4],
                    'remaining_values': row[5],
                    'days_until_full': row[6],
                    'daily_growth_rate': row[7],
                    'alert_status': row[8],
                    'scan_time': row[9].isoformat() if row[9] else None
                }
            return data
        except Exception:
            return {}
    
    data1 = get_autoincrement_data(env1)
    data2 = get_autoincrement_data(env2)
    
    return build_autoincrement_comparison_response(table_name, application, env1, env2, data1, data2)


def compare_autoincrement_pg(table_name, application, env1, env2):
    """Compare auto-increment using PostgreSQL backend."""
    conn = get_postgres_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    def get_autoincrement_data(env):
        try:
            cursor.execute("""
                SELECT DISTINCT ON (column_name)
                    column_name,
                    data_type,
                    current_value,
                    max_type_value,
                    usage_percentage,
                    remaining_values,
                    days_until_full,
                    daily_growth_rate,
                    alert_status,
                    scan_time
                FROM auto_increment_metrics
                WHERE table_name = %s
                  AND application = %s
                  AND environment = %s
                ORDER BY column_name, scan_time DESC
            """, (table_name, application, env))
            
            rows = cursor.fetchall()
            data = {}
            for row in rows:
                data[row['column_name']] = {
                    'column_name': row['column_name'],
                    'data_type': row['data_type'],
                    'current_value': row['current_value'],
                    'max_type_value': row['max_type_value'],
                    'usage_percentage': row['usage_percentage'],
                    'remaining_values': row['remaining_values'],
                    'days_until_full': row['days_until_full'],
                    'daily_growth_rate': row['daily_growth_rate'],
                    'alert_status': row['alert_status'],
                    'scan_time': row['scan_time'].isoformat() if row['scan_time'] else None
                }
            return data
        except Exception:
            return {}
    
    data1 = get_autoincrement_data(env1)
    data2 = get_autoincrement_data(env2)
    
    cursor.close()
    conn.close()
    
    return build_autoincrement_comparison_response(table_name, application, env1, env2, data1, data2)


def build_autoincrement_comparison_response(table_name, application, env1, env2, data1, data2):
    """Build the auto-increment comparison response."""
    # Merge columns from both environments
    all_columns = set(data1.keys()) | set(data2.keys())
    
    comparison = []
    for col_name in sorted(all_columns):
        col1 = data1.get(col_name)
        col2 = data2.get(col_name)
        
        comparison.append({
            'column_name': col_name,
            'data_type': col1['data_type'] if col1 else (col2['data_type'] if col2 else None),
            'env1': col1,
            'env2': col2,
            'in_env1': col1 is not None,
            'in_env2': col2 is not None
        })
    
    return jsonify({
        'table_name': table_name,
        'application': application,
        'env1': env1,
        'env2': env2,
        'columns': comparison
    })


# =============================================================================
# Schema Comparison Endpoints
# =============================================================================

@app.route('/api/schema/compare/<table_name>', methods=['GET'])
def compare_schema(table_name):
    """Compare schema between two environments."""
    application = request.args.get('app', 'default')
    env1 = request.args.get('env1')
    env2 = request.args.get('env2')
    
    if not env1 or not env2:
        return jsonify({'error': 'Both env1 and env2 are required'}), 400
    
    if METRICS_BACKEND == 'postgresql':
        return compare_schema_pg(table_name, application, env1, env2)
    return compare_schema_ch(table_name, application, env1, env2)


def compare_schema_ch(table_name, application, env1, env2):
    """Compare schema using ClickHouse backend."""
    client = get_clickhouse_client()
    
    def get_latest_schema(env):
        """Get the latest schema for an environment."""
        # Get the latest scan_time for this table/app/env
        latest_query = f"""
            SELECT max(scan_time) 
            FROM schema_profiles 
            WHERE table_name = '{table_name}' 
              AND application = '{application}'
              AND environment = '{env}'
        """
        try:
            latest_result = client.query(latest_query)
            latest_time = latest_result.result_rows[0][0] if latest_result.result_rows else None
        except Exception:
            return None
        
        if not latest_time:
            return None
        
        query = f"""
            SELECT 
                column_name,
                column_position,
                data_type,
                is_nullable,
                column_default,
                max_length,
                numeric_precision,
                numeric_scale,
                is_primary_key,
                is_in_index,
                index_names,
                is_foreign_key,
                fk_references,
                scan_time,
                database_host,
                database_name,
                schema_name
            FROM schema_profiles
            WHERE table_name = '{table_name}' 
              AND scan_time = '{latest_time}'
              AND application = '{application}'
              AND environment = '{env}'
            ORDER BY column_position
        """
        
        result = client.query(query)
        
        columns = {}
        scan_time = None
        database_host = None
        database_name = None
        schema_name = None
        
        for row in result.result_rows:
            columns[row[0]] = {
                'column_name': row[0],
                'column_position': row[1],
                'data_type': row[2],
                'is_nullable': bool(row[3]),
                'column_default': row[4],
                'max_length': row[5],
                'numeric_precision': row[6],
                'numeric_scale': row[7],
                'is_primary_key': bool(row[8]),
                'is_in_index': bool(row[9]),
                'index_names': row[10],
                'is_foreign_key': bool(row[11]),
                'fk_references': row[12]
            }
            scan_time = row[13].isoformat() if row[13] else None
            database_host = row[14] if len(row) > 14 else None
            database_name = row[15] if len(row) > 15 else None
            schema_name = row[16] if len(row) > 16 else None
        
        return {
            'columns': columns,
            'scan_time': scan_time,
            'database_host': database_host,
            'database_name': database_name,
            'schema_name': schema_name
        }
    
    schema1 = get_latest_schema(env1)
    schema2 = get_latest_schema(env2)
    
    return build_schema_comparison_response(table_name, application, env1, env2, schema1, schema2)


def compare_schema_pg(table_name, application, env1, env2):
    """Compare schema using PostgreSQL backend."""
    conn = get_postgres_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    def get_latest_schema(env):
        """Get the latest schema for an environment."""
        # Get the latest scan_time for this table/app/env
        cursor.execute("""
            SELECT max(scan_time) 
            FROM schema_profiles 
            WHERE table_name = %s 
              AND application = %s
              AND environment = %s
        """, (table_name, application, env))
        row = cursor.fetchone()
        latest_time = row['max'] if row else None
        
        if not latest_time:
            return None
        
        cursor.execute("""
            SELECT 
                column_name,
                column_position,
                data_type,
                is_nullable,
                column_default,
                max_length,
                numeric_precision,
                numeric_scale,
                is_primary_key,
                is_in_index,
                index_names,
                is_foreign_key,
                fk_references,
                scan_time,
                database_host,
                database_name,
                schema_name
            FROM schema_profiles
            WHERE table_name = %s 
              AND scan_time = %s
              AND application = %s
              AND environment = %s
            ORDER BY column_position
        """, (table_name, latest_time, application, env))
        
        rows = cursor.fetchall()
        
        columns = {}
        scan_time = None
        database_host = None
        database_name = None
        schema_name = None
        
        for row in rows:
            columns[row['column_name']] = {
                'column_name': row['column_name'],
                'column_position': row['column_position'],
                'data_type': row['data_type'],
                'is_nullable': bool(row['is_nullable']),
                'column_default': row['column_default'],
                'max_length': row['max_length'],
                'numeric_precision': row['numeric_precision'],
                'numeric_scale': row['numeric_scale'],
                'is_primary_key': bool(row['is_primary_key']),
                'is_in_index': bool(row['is_in_index']),
                'index_names': row['index_names'],
                'is_foreign_key': bool(row['is_foreign_key']),
                'fk_references': row['fk_references']
            }
            scan_time = row['scan_time'].isoformat() if row['scan_time'] else None
            database_host = row['database_host']
            database_name = row['database_name']
            schema_name = row['schema_name']
        
        return {
            'columns': columns,
            'scan_time': scan_time,
            'database_host': database_host,
            'database_name': database_name,
            'schema_name': schema_name
        }
    
    schema1 = get_latest_schema(env1)
    schema2 = get_latest_schema(env2)
    
    cursor.close()
    conn.close()
    
    return build_schema_comparison_response(table_name, application, env1, env2, schema1, schema2)


def build_schema_comparison_response(table_name, application, env1, env2, schema1, schema2):
    """Build the schema comparison response."""
    # Get all unique column names from both schemas
    all_columns = set()
    if schema1:
        all_columns.update(schema1['columns'].keys())
    if schema2:
        all_columns.update(schema2['columns'].keys())
    
    # Build comparison data
    comparison = []
    for col_name in sorted(all_columns):
        col1 = schema1['columns'].get(col_name) if schema1 else None
        col2 = schema2['columns'].get(col_name) if schema2 else None
        
        # Detect differences
        differences = []
        if col1 and col2:
            if col1.get('data_type') != col2.get('data_type'):
                differences.append('data_type')
            if col1.get('is_nullable') != col2.get('is_nullable'):
                differences.append('is_nullable')
            if col1.get('column_default') != col2.get('column_default'):
                differences.append('column_default')
            if col1.get('is_primary_key') != col2.get('is_primary_key'):
                differences.append('is_primary_key')
            if col1.get('is_in_index') != col2.get('is_in_index'):
                differences.append('is_in_index')
            if col1.get('is_foreign_key') != col2.get('is_foreign_key'):
                differences.append('is_foreign_key')
        
        comparison.append({
            'column_name': col_name,
            'env1': col1,
            'env2': col2,
            'in_env1': col1 is not None,
            'in_env2': col2 is not None,
            'differences': differences,
            'has_differences': len(differences) > 0 or (col1 is None) != (col2 is None)
        })
    
    # Sort by: columns with differences first, then by column position
    comparison.sort(key=lambda x: (
        not x['has_differences'],
        x['env1']['column_position'] if x['env1'] else (x['env2']['column_position'] if x['env2'] else 999)
    ))
    
    # Summary stats
    total_columns = len(all_columns)
    matching_columns = sum(1 for c in comparison if not c['has_differences'])
    different_columns = sum(1 for c in comparison if c['has_differences'])
    only_in_env1 = sum(1 for c in comparison if c['in_env1'] and not c['in_env2'])
    only_in_env2 = sum(1 for c in comparison if c['in_env2'] and not c['in_env1'])
    
    return jsonify({
        'table_name': table_name,
        'application': application,
        'env1': {
            'name': env1,
            'scan_time': schema1['scan_time'] if schema1 else None,
            'database_host': schema1['database_host'] if schema1 else None,
            'database_name': schema1['database_name'] if schema1 else None,
            'schema_name': schema1['schema_name'] if schema1 else None,
            'column_count': len(schema1['columns']) if schema1 else 0,
            'exists': schema1 is not None
        },
        'env2': {
            'name': env2,
            'scan_time': schema2['scan_time'] if schema2 else None,
            'database_host': schema2['database_host'] if schema2 else None,
            'database_name': schema2['database_name'] if schema2 else None,
            'schema_name': schema2['schema_name'] if schema2 else None,
            'column_count': len(schema2['columns']) if schema2 else 0,
            'exists': schema2 is not None
        },
        'summary': {
            'total_columns': total_columns,
            'matching_columns': matching_columns,
            'different_columns': different_columns,
            'only_in_env1': only_in_env1,
            'only_in_env2': only_in_env2
        },
        'columns': comparison
    })


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    print("🚀 Starting Data Profile Dashboard API (Multi-Env)...")
    print(f"   ClickHouse: {CH_HOST}:{CH_PORT}")
    print("   API: http://localhost:5001")
    app.run(host='0.0.0.0', port=5001, debug=True)
