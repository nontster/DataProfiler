import os
import psycopg2
import clickhouse_connect
from jinja2 import Template
from soda.scan import Scan
from dotenv import load_dotenv
import textwrap
import sys

# Load environment variables from .env file
load_dotenv()

# --- Configuration from Environment Variables ---
POSTGRES_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', 5432)),
    'database': os.getenv('POSTGRES_DATABASE', 'postgres'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', ''),
    'schema': os.getenv('POSTGRES_SCHEMA', 'public'),
}

CLICKHOUSE_CONFIG = {
    'host': os.getenv('CLICKHOUSE_HOST', 'localhost'),
    'port': int(os.getenv('CLICKHOUSE_PORT', 8123)),
    'username': os.getenv('CLICKHOUSE_USER', 'default'),
    'password': os.getenv('CLICKHOUSE_PASSWORD', ''),
}


# --- 1. Setup ClickHouse ---
def get_ch_client():
    return clickhouse_connect.get_client(
        host=CLICKHOUSE_CONFIG['host'],
        port=CLICKHOUSE_CONFIG['port'],
        username=CLICKHOUSE_CONFIG['username'],
        password=CLICKHOUSE_CONFIG['password']
    )


def init_clickhouse():
    try:
        client = get_ch_client()
        client.command("""
            CREATE TABLE IF NOT EXISTS data_profiles (
                scan_time DateTime DEFAULT now(),
                table_name String,
                column_name String,
                distinct_count Nullable(Int64),
                missing_count Nullable(Int64),
                min Nullable(String),
                max Nullable(String),
                avg Nullable(Float64)
            ) ENGINE = MergeTree() ORDER BY (scan_time, table_name)
        """)
        print("✅ ClickHouse Connection & Table Ready")
    except Exception as e:
        print(f"❌ ClickHouse Init Error: {e}")


# --- 2. Metadata Discovery & Filtering ---
def get_table_metadata(table_name):
    conn = psycopg2.connect(
        host=POSTGRES_CONFIG['host'],
        port=POSTGRES_CONFIG['port'],
        database=POSTGRES_CONFIG['database'],
        user=POSTGRES_CONFIG['user'],
        password=POSTGRES_CONFIG['password']
    )
    cur = conn.cursor()
    
    # ใช้ Parameterized Query เพื่อป้องกัน SQL Injection
    query = """
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = %s AND table_schema = %s
    """
    cur.execute(query, (table_name, POSTGRES_CONFIG['schema']))
    columns = cur.fetchall()
    
    cur.close()
    conn.close()
    return [{"name": col[0], "type": col[1]} for col in columns]


def is_profile_supported(pg_type):
    unsupported = ['timestamp', 'timestamp without time zone', 'date', 'bytea']
    return pg_type not in unsupported


# --- 3. Main Workflow ---
def run_poc(table_name):
    init_clickhouse()
    
    print(f"--- Discovering Schema for {table_name} ---")
    all_columns = get_table_metadata(table_name)
    
    profile_columns = [c for c in all_columns if is_profile_supported(c['type'])]
    
    sodacl_template = textwrap.dedent("""
        checks for {{ table_name }}:
          - row_count > 0

        profile columns:
          columns:
            {% for col in columns %}
            - {{ table_name }}.{{ col.name }}
            {% endfor %}
    """)
    
    template = Template(sodacl_template)
    yaml_content = template.render(table_name=table_name, columns=profile_columns)
    
    print("--- Running Soda Scan ---")
    scan = Scan()
    scan.set_data_source_name("my_postgres")
    scan.add_configuration_yaml_file(file_path="configuration.yml")
    scan.add_sodacl_yaml_str(yaml_content)
    
    scan.execute()
    
    # --- Data Extraction (Corrected Logic) ---
    results = scan.get_scan_results()
    clickhouse_records = []
    
    if 'profiling' in results:
        for p in results['profiling']:
            # แก้ไข Key ให้ตรงกับ JSON output
            t_name = p.get('table') 
            
            # แก้ไข: columnProfiles เป็น List ไม่ใช่ Dict
            column_profiles_list = p.get('columnProfiles', [])
            
            for col_item in column_profiles_list:
                col_name = col_item.get('columnName')
                stats = col_item.get('profile', {})
                
                # Map ค่าสถิติ (Mapping ตาม JSON)
                record = {
                    "table_name": t_name,
                    "column_name": col_name,
                    "distinct_count": stats.get('distinct'), # JSON ใช้คำว่า 'distinct'
                    "missing_count": stats.get('missing_count'),
                    "min": str(stats.get('min')) if stats.get('min') is not None else None,
                    "max": str(stats.get('max')) if stats.get('max') is not None else None,
                    "avg": stats.get('avg')
                }
                clickhouse_records.append(record)

    # --- Send to ClickHouse ---
    if clickhouse_records:
        try:
            client = get_ch_client()
            data = [[r['table_name'], r['column_name'], r['distinct_count'], r['missing_count'], r['min'], r['max'], r['avg']] for r in clickhouse_records]
            
            client.insert('data_profiles', data, column_names=['table_name', 'column_name', 'distinct_count', 'missing_count', 'min', 'max', 'avg'])
            print(f"✅ SUCCESS: Saved {len(clickhouse_records)} column profiles to ClickHouse!")
            print(f"   (Columns: {[r['column_name'] for r in clickhouse_records]})")
            
        except Exception as e:
            print(f"❌ Insert Error: {e}")
    else:
        print("❌ No profiling data collected.")
        # ไม่ต้อง Debug JSON แล้วเพราะเรารู้แล้วว่าข้อมูลมาถูกทาง


if __name__ == "__main__":
    # ถ้ามีการใส่ชื่อตารางมาตอนรัน ให้ใช้ชื่อนั้น ถ้าไม่มีให้ใช้ 'users' เป็นค่าเริ่มต้น
    target_table = sys.argv[1] if len(sys.argv) > 1 else "users"
    run_poc(target_table)