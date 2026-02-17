#!/usr/bin/env python3
"""
Generate test data in Oracle database.

Usage:
    python init-scripts/oracle/generate-oracle-data.py [--users N] [--products N] [--schema SCHEMA]

Examples:
    python init-scripts/oracle/generate-oracle-data.py              # Add to PROD.users
    python init-scripts/oracle/generate-oracle-data.py --schema UAT # Add to UAT.users
    python init-scripts/oracle/generate-oracle-data.py --users 500  # Add 500 users
"""

import argparse
import random
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    import oracledb
except ImportError:
    print("❌ oracledb not installed. Run: pip install oracledb")
    sys.exit(1)

# Configuration
ORACLE_HOST = os.getenv('ORACLE_HOST', 'localhost')
ORACLE_PORT = int(os.getenv('ORACLE_PORT', 21521))
ORACLE_SERVICE_NAME = os.getenv('ORACLE_SERVICE_NAME', 'XEPDB1')
ORACLE_USER = os.getenv('ORACLE_USER', 'PROD')
ORACLE_PASSWORD = os.getenv('ORACLE_PASSWORD', 'password123')
# Note: In Oracle, User ~= Schema. defaulting schema to User if not provided.

def get_connection():
    """Get Oracle connection."""
    try:
        dsn = f"{ORACLE_HOST}:{ORACLE_PORT}/{ORACLE_SERVICE_NAME}"
        conn = oracledb.connect(
            user=ORACLE_USER,
            password=ORACLE_PASSWORD,
            dsn=dsn
        )
        return conn
    except oracledb.Error as e:
        print(f"❌ Failed to connect to Oracle: {e}")
        print(f"   DSN: {ORACLE_HOST}:{ORACLE_PORT}/{ORACLE_SERVICE_NAME}")
        sys.exit(1)


def get_max_id(conn, table, schema='PROD', id_column='id'):
    """Get the current max ID from a table to generate unique suffixes."""
    cursor = conn.cursor()
    try:
        # NVL equivalent to ISNULL
        cursor.execute(f"SELECT NVL(MAX({id_column}), 0) FROM {schema}.{table}")
        result = cursor.fetchone()
        return result[0] if result else 0
    except oracledb.Error:
        return 0
    finally:
        cursor.close()


def generate_users(conn, count, table_name='users', schema='PROD'):
    """Generate test users."""
    table_name = table_name.upper()
    schema = schema.upper()
    full_table_name = f"{schema}.{table_name}"
    
    print(f"\n👤 Generating {count} users in {full_table_name}...")
    
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute(
        "SELECT COUNT(*) FROM all_tables WHERE owner = :1 AND table_name = :2",
        (schema, table_name)
    )
    if cursor.fetchone()[0] == 0:
        print(f"❌ Table '{full_table_name}' does not exist. Please run init scripts first.")
        return
    
    # Get starting point for unique usernames
    start_id = get_max_id(conn, table_name, schema) + 1
    
    # Generate data
    data = []
    for i in range(count):
        idx = start_id + i
        username = f'newuser_{idx}'
        email = f'newuser{idx}@test.com'
        age = random.randint(18, 78)
        salary = round(random.uniform(30000, 180000), 2)
        is_active = 1 if random.random() > 0.2 else 0
        
        # Oracle INSERT needs tuples or dicts for executemany
        data.append((username, email, age, salary, is_active))
    
    # Insert in batches
    batch_size = 1000
    inserted = 0
    
    sql = f"""
        INSERT INTO {full_table_name} (username, email, age, salary, is_active)
        VALUES (:1, :2, :3, :4, :5)
    """
    
    try:
        for i in range(0, len(data), batch_size):
            batch = data[i:i+batch_size]
            cursor.executemany(sql, batch)
            conn.commit()
            inserted += len(batch)
            print(f"   Inserted {inserted}/{count} users...")
    except oracledb.Error as e:
        print(f"❌ Error inserting users: {e}")
    
    print(f"   ✅ Added {count} new users to {full_table_name} (Suffixes {start_id} to {start_id + count - 1})")
    cursor.close()


def generate_products(conn, count, schema='PROD'):
    """Generate test products."""
    table = 'PRODUCTS'
    schema = schema.upper()
    print(f"\n📦 Generating {count} products in {schema}.{table}...")
    
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute(
        "SELECT COUNT(*) FROM all_tables WHERE owner = :1 AND table_name = :2",
        (schema, table)
    )
    if cursor.fetchone()[0] == 0:
        print(f"❌ Table '{schema}.{table}' does not exist. Please run init scripts first.")
        return
    
    # Get starting point
    start_id = get_max_id(conn, table, schema, 'id') + 1
    
    categories = ['Electronics', 'Accessories', 'Furniture', 'Appliances', 'Stationery']
    is_uat = (schema == 'UAT')
    
    data = []
    for i in range(count):
        idx = start_id + i
        name = f'Product_{idx}'
        category = random.choice(categories)
        price = round(random.uniform(10, 1000), 2)
        stock_quantity = random.randint(0, 500)
        is_available = 1 if random.random() > 0.15 else 0
        
        if is_uat:
            # UAT has extra columns: sku, discount_percent
            sku = f'{category[:4].upper()}-P{idx:04d}'
            # Random discount or None
            discount = round(random.uniform(0, 20), 2) if random.random() > 0.5 else None
            data.append((name, category, price, stock_quantity, is_available, sku, discount))
        else:
            data.append((name, category, price, stock_quantity, is_available))
    
    # Determine columns for INSERT
    if is_uat:
        sql = f"""
            INSERT INTO {schema}.{table} (name, category, price, stock_quantity, is_available, sku, discount_percent)
            VALUES (:1, :2, :3, :4, :5, :6, :7)
        """
    else:
        sql = f"""
            INSERT INTO {schema}.{table} (name, category, price, stock_quantity, is_available)
            VALUES (:1, :2, :3, :4, :5)
        """
    
    # Insert in batches
    batch_size = 1000
    inserted = 0
    
    try:
        for i in range(0, len(data), batch_size):
            batch = data[i:i+batch_size]
            cursor.executemany(sql, batch)
            conn.commit()
            inserted += len(batch)
            print(f"   Inserted {inserted}/{count} products...")
    except oracledb.Error as e:
        print(f"❌ Error inserting products: {e}")
        
    print(f"   ✅ Added {count} new products (Suffixes {start_id} to {start_id + count - 1})")
    cursor.close()


def show_stats(conn):
    """Show current table statistics."""
    cursor = conn.cursor()
    print("\n📊 Current table statistics:")
    
    targets = [('PROD', 'USERS'), ('UAT', 'USERS'), ('PROD', 'PRODUCTS'), ('UAT', 'PRODUCTS')]
    
    for schema, table in targets:
        try:
            # Check existence first to avoid errors
            cursor.execute(
                "SELECT COUNT(*) FROM all_tables WHERE owner = :1 AND table_name = :2", 
                (schema, table)
            )
            if cursor.fetchone()[0] > 0:
                id_col = 'id'
                cursor.execute(f"SELECT COUNT(*), MAX({id_col}), MIN({id_col}) FROM {schema}.{table}")
                row = cursor.fetchone()
                if row and row[0]:
                    print(f"   {schema}.{table}: {row[0]:,} records (ID range: {row[2]} - {row[1]})")
        except oracledb.Error:
            pass
    
    cursor.close()


def main():
    parser = argparse.ArgumentParser(
        description='Generate test data in Oracle database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python init-scripts/oracle/generate-oracle-data.py --schema PROD         # Add to Prod
  python init-scripts/oracle/generate-oracle-data.py --schema UAT          # Add to UAT
  python init-scripts/oracle/generate-oracle-data.py --users 500 --schema PROD
        """
    )
    parser.add_argument('--users', type=int, default=100, help='Number of users to generate (default: 100)')
    parser.add_argument('--products', type=int, default=50, help='Number of products to generate (default: 50)')
    parser.add_argument('--table', type=str, default='users', help='Target table name (default: users)')
    parser.add_argument('--schema', type=str, default='PROD', help='Target schema (default: PROD)')
    parser.add_argument('--no-users', action='store_true', help='Skip generating users')
    parser.add_argument('--no-products', action='store_true', help='Skip generating products')
    parser.add_argument('--stats-only', action='store_true', help='Only show current statistics')
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("Oracle Test Data Generator")
    print("=" * 50)
    print(f"Host: {ORACLE_HOST}:{ORACLE_PORT}/{ORACLE_SERVICE_NAME}")
    print(f"User: {ORACLE_USER}")
    
    try:
        conn = get_connection()
        print("✅ Connected to Oracle")
        
        if args.stats_only:
            show_stats(conn)
            conn.close()
            return
        
        # Upper case schema for Oracle
        target_schema = args.schema.upper()
        
        if not args.no_users and args.users > 0:
            generate_users(conn, args.users, args.table, target_schema)
        
        if not args.no_products and args.products > 0:
            generate_products(conn, args.products, target_schema)
        
        show_stats(conn)
        conn.close()
        
        print("\n" + "=" * 50)
        print("✅ Data generation completed!")
        print("=" * 50)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
