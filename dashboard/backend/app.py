"""
Flask API backend for Data Profile Dashboard (Multi-Environment).
Serves profiling data from ClickHouse.
"""

import os
import sys
from flask import Flask, jsonify, request
from flask_cors import CORS

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import clickhouse_connect
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))

app = Flask(__name__)
CORS(app)

# ClickHouse configuration
CH_HOST = os.getenv('CLICKHOUSE_HOST', 'localhost')
CH_PORT = int(os.getenv('CLICKHOUSE_PORT', 8123))
CH_USER = os.getenv('CLICKHOUSE_USER', 'default')
CH_PASSWORD = os.getenv('CLICKHOUSE_PASSWORD', '')


def get_client():
    """Get ClickHouse client."""
    return clickhouse_connect.get_client(
        host=CH_HOST,
        port=CH_PORT,
        username=CH_USER,
        password=CH_PASSWORD
    )


@app.route('/api/metadata', methods=['GET'])
def get_metadata():
    """Get distinct applications and environments."""
    client = get_client()
    
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


@app.route('/api/tables', methods=['GET'])
def get_tables():
    """Get list of profiled tables filtered by app and env."""
    application = request.args.get('app')
    environment = request.args.get('env')
    
    # Base query
    query = """
        SELECT 
            table_name,
            max(row_count) as row_count,
            count(DISTINCT column_name) as column_count,
            max(scan_time) as last_profiled
        FROM data_profiles
        WHERE 1=1
    """
    
    # Add filters
    if application:
        query += f" AND application = '{application}'"
    if environment:
        query += f" AND environment = '{environment}'"
        
    query += """
        GROUP BY table_name
        ORDER BY table_name
    """
    
    client = get_client()
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


@app.route('/api/profiles/<table_name>', methods=['GET'])
def get_profiles(table_name):
    """Get latest profile for a specific table."""
    application = request.args.get('app', 'default')
    environment = request.args.get('env', 'development')
    
    client = get_client()
    
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


@app.route('/api/autoincrement/<table_name>', methods=['GET'])
def get_autoincrement(table_name):
    """Get auto-increment overflow risk data for a specific table."""
    application = request.args.get('app', 'default')
    environment = request.args.get('env', 'development')
    
    client = get_client()
    
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


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    print("🚀 Starting Data Profile Dashboard API (Multi-Env)...")
    print(f"   ClickHouse: {CH_HOST}:{CH_PORT}")
    print("   API: http://localhost:5001")
    app.run(host='0.0.0.0', port=5001, debug=True)
