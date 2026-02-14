#!/usr/bin/env python3
"""
Generate test data in MSSQL database.

Usage:
    python init-scripts/mssql/generate-mssql-data.py [--users N] [--products N] [--schema SCHEMA]

Examples:
    python init-scripts/mssql/generate-mssql-data.py              # Add to prod.users
    python init-scripts/mssql/generate-mssql-data.py --schema uat # Add to uat.users
    python init-scripts/mssql/generate-mssql-data.py --users 500  # Add 500 users
"""

import argparse
import random
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    import pymssql
except ImportError:
    print("❌ pymssql not installed. Run: pip install pymssql")
    sys.exit(1)

# Configuration
MSSQL_HOST = os.getenv('MSSQL_HOST', 'localhost')
MSSQL_PORT = int(os.getenv('MSSQL_PORT', 1433))
MSSQL_USER = os.getenv('MSSQL_USER', 'sa')
MSSQL_PASSWORD = os.getenv('MSSQL_PASSWORD', 'YourStrong@Password123')
MSSQL_DATABASE = os.getenv('MSSQL_DATABASE', 'testdb')


def get_connection():
    """Get MSSQL connection."""
    try:
        conn = pymssql.connect(
            server=MSSQL_HOST,
            port=MSSQL_PORT,
            user=MSSQL_USER,
            password=MSSQL_PASSWORD,
            database=MSSQL_DATABASE,
            autocommit=True
        )
        return conn
    except pymssql.Error as e:
        print(f"❌ Failed to connect to MSSQL: {e}")
        print(f"   Host: {MSSQL_HOST}:{MSSQL_PORT}")
        print(f"   Database: {MSSQL_DATABASE}")
        sys.exit(1)


def get_max_id(conn, table, schema='dbo', id_column='id'):
    """Get the current max ID from a table."""
    cursor = conn.cursor()
    # Safely query max ID
    cursor.execute(f"SELECT ISNULL(MAX({id_column}), 0) FROM {schema}.{table}")
    result = cursor.fetchone()
    return result[0] if result else 0


def generate_users(conn, count, table_name='users', schema='prod'):
    """Generate test users."""
    full_table_name = f"{schema}.{table_name}"
    print(f"\n👤 Generating {count} users in {full_table_name}...")
    
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute(f"SELECT * FROM sys.tables t JOIN sys.schemas s ON t.schema_id = s.schema_id WHERE t.name = %s AND s.name = %s", (table_name, schema))
    if not cursor.fetchone():
        print(f"❌ Table '{full_table_name}' does not exist. Please run init scripts first.")
        return
    
    # Get starting point
    start_id = get_max_id(conn, table_name, schema) + 1
    
    # Build batch insert
    values = []
    for i in range(count):
        idx = start_id + i
        username = f'newuser_{idx}'
        email = f'newuser{idx}@test.com'
        age = random.randint(18, 78)
        salary = round(random.uniform(30000, 180000), 2)
        is_active = 1 if random.random() > 0.2 else 0
        values.append(f"('{username}', '{email}', {age}, {salary}, {is_active})")
    
    # Insert in batches of 1000
    batch_size = 1000
    inserted = 0
    
    for i in range(0, len(values), batch_size):
        batch = values[i:i+batch_size]
        
        sql = f"""
            INSERT INTO {full_table_name} (username, email, age, salary, is_active)
            VALUES {','.join(batch)}
        """
        cursor.execute(sql)
        inserted += len(batch)
        print(f"   Inserted {inserted}/{count} users...")
    
    print(f"   ✅ Added {count} new users to {full_table_name} (IDs {start_id} to {start_id + count - 1})")


def generate_products(conn, count, schema='prod'):
    """Generate test products."""
    table = 'products'
    print(f"\n📦 Generating {count} products in {schema}.{table}...")
    
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute(f"SELECT * FROM sys.tables t JOIN sys.schemas s ON t.schema_id = s.schema_id WHERE t.name = %s AND s.name = %s", (table, schema))
    if not cursor.fetchone():
        print(f"❌ Table '{schema}.{table}' does not exist. Please run init scripts first.")
        return
    
    # Get starting point
    start_id = get_max_id(conn, table, schema, 'id') + 1
    
    categories = ['Electronics', 'Accessories', 'Furniture', 'Appliances', 'Stationery']
    is_uat = (schema == 'uat')
    
    # Build batch insert
    values = []
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
            discount = f'{round(random.uniform(0, 20), 2)}' if random.random() > 0.5 else 'NULL'
            values.append(f"(N'{name}', N'{category}', {price}, {stock_quantity}, {is_available}, N'{sku}', {discount})")
        else:
            values.append(f"(N'{name}', N'{category}', {price}, {stock_quantity}, {is_available})")
    
    # Determine columns for INSERT
    if is_uat:
        columns = 'name, category, price, stock_quantity, is_available, sku, discount_percent'
    else:
        columns = 'name, category, price, stock_quantity, is_available'
    
    # Insert in batches of 1000
    batch_size = 1000
    inserted = 0
    
    for i in range(0, len(values), batch_size):
        batch = values[i:i+batch_size]
        sql = f"""
            INSERT INTO {schema}.{table} ({columns})
            VALUES {','.join(batch)}
        """
        cursor.execute(sql)
        inserted += len(batch)
        print(f"   Inserted {inserted}/{count} products...")
    
    print(f"   ✅ Added {count} new products (IDs {start_id} to {start_id + count - 1})")


def show_stats(conn):
    """Show current table statistics."""
    cursor = conn.cursor()
    print("\n📊 Current table statistics:")
    
    targets = [('prod', 'users'), ('uat', 'users'), ('prod', 'products'), ('uat', 'products')]
    
    for schema, table in targets:
        # Check if table exists
        cursor.execute(f"SELECT * FROM sys.tables t JOIN sys.schemas s ON t.schema_id = s.schema_id WHERE t.name = %s AND s.name = %s", (table, schema))
        if cursor.fetchone():
            id_col = 'id'
            try:
                cursor.execute(f"SELECT COUNT(*), MAX({id_col}), MIN({id_col}) FROM {schema}.{table}")
                row = cursor.fetchone()
                if row and row[0]:
                    print(f"   {schema}.{table}: {row[0]:,} records (ID range: {row[2]} - {row[1]})")
            except:
                pass


def main():
    parser = argparse.ArgumentParser(
        description='Generate test data in MSSQL database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python init-scripts/mssql/generate-mssql-data.py --schema prod         # Add to Prod
  python init-scripts/mssql/generate-mssql-data.py --schema uat          # Add to UAT
  python init-scripts/mssql/generate-mssql-data.py --users 500 --schema prod
        """
    )
    parser.add_argument('--users', type=int, default=100, help='Number of users to generate (default: 100)')
    parser.add_argument('--products', type=int, default=50, help='Number of products to generate (default: 50)')
    parser.add_argument('--table', type=str, default='users', help='Target table name (default: users)')
    parser.add_argument('--schema', type=str, default='prod', help='Target schema (default: prod)')
    parser.add_argument('--no-users', action='store_true', help='Skip generating users')
    parser.add_argument('--no-products', action='store_true', help='Skip generating products')
    parser.add_argument('--stats-only', action='store_true', help='Only show current statistics')
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("MSSQL Test Data Generator")
    print("=" * 50)
    print(f"Host: {MSSQL_HOST}:{MSSQL_PORT}")
    print(f"Database: {MSSQL_DATABASE}")
    
    conn = get_connection()
    print("✅ Connected to MSSQL")
    
    if args.stats_only:
        show_stats(conn)
        conn.close()
        return
    
    if not args.no_users and args.users > 0:
        generate_users(conn, args.users, args.table, args.schema)
    
    if not args.no_products and args.products > 0:
        generate_products(conn, args.products, args.schema)
    
    show_stats(conn)
    conn.close()
    
    print("\n" + "=" * 50)
    print("✅ Data generation completed!")
    print("=" * 50)
    print("\nYou can now run profiler:")
    print(f"  python main.py {args.table} -d mssql --schema {args.schema} --auto-increment")


if __name__ == '__main__':
    main()
