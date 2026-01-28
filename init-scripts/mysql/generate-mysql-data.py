#!/usr/bin/env python3
"""
Generate test data in MySQL database.

Usage:
    python init-scripts/mysql/generate-mysql-data.py [--users N] [--products N] [--schema SCHEMA]

Examples:
    python init-scripts/mysql/generate-mysql-data.py              # Add to prod.users
    python init-scripts/mysql/generate-mysql-data.py --schema uat # Add to uat.users
    python init-scripts/mysql/generate-mysql-data.py --users 500  # Add 500 users
"""

import argparse
import random
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    import mysql.connector
except ImportError:
    print("❌ mysql-connector-python not installed. Run: pip install mysql-connector-python")
    sys.exit(1)

# Configuration
MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
MYSQL_USER = os.getenv('MYSQL_USER', 'user')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'password123')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'prod')


def get_connection(database=None):
    """Get MySQL connection."""
    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=database or MYSQL_DATABASE,
            autocommit=True
        )
        return conn
    except mysql.connector.Error as e:
        print(f"❌ Failed to connect to MySQL: {e}")
        print(f"   Host: {MYSQL_HOST}:{MYSQL_PORT}")
        sys.exit(1)


def get_max_id(conn, table, schema='prod', id_column='id'):
    """Get the current max ID from a table."""
    with conn.cursor() as cursor:
        try:
            # Note: Using schema argument as database name
            cursor.execute(f"SELECT COALESCE(MAX({id_column}), 0) FROM {schema}.{table}")
            result = cursor.fetchone()
            return result[0] if result else 0
        except mysql.connector.Error:
            # Table might not exist
            return 0


def generate_users(conn, count, table_name='users', schema='prod'):
    """Generate test users."""
    full_table_name = f"{schema}.{table_name}"
    print(f"\n👤 Generating {count} users in {full_table_name}...")
    
    with conn.cursor() as cursor:
        # Check if table exists
        cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = %s AND table_schema = %s", (table_name, schema))
        if cursor.fetchone()[0] == 0:
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


def generate_products(conn, count, table_name='products', schema='prod'):
    """Generate test products."""
    full_table_name = f"{schema}.{table_name}"
    print(f"\n📦 Generating {count} products in {full_table_name}...")
    
    with conn.cursor() as cursor:
        # Check if table exists
        cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = %s AND table_schema = %s", (table_name, schema))
        if cursor.fetchone()[0] == 0:
            print(f"❌ Table '{full_table_name}' does not exist. Please run init scripts first.")
            return

        # Get starting point
        start_id = get_max_id(conn, table_name, schema, 'id') + 1 
        
        categories = ['Electronics', 'Accessories', 'Clothing', 'Home', 'Sports', 'Books', 'Toys']
        
        # Build batch insert
        values = []
        for i in range(count):
            idx = start_id + i
            name = f'Product_{idx}'
            price = round(random.uniform(10, 1000), 2)
            quantity = random.randint(0, 500)
            category = random.choice(categories)
            is_available = 1 if quantity > 0 else 0
            # Note: columns based on 01-sample-data.sql: name, category, price, stock_quantity, is_available
            values.append(f"('{name}', '{category}', {price}, {quantity}, {is_available})")
        
        # Insert in batches of 1000
        batch_size = 1000
        inserted = 0
        
        for i in range(0, len(values), batch_size):
            batch = values[i:i+batch_size]
            sql = f"""
                INSERT INTO {full_table_name} (name, category, price, stock_quantity, is_available)
                VALUES {','.join(batch)}
            """
            cursor.execute(sql)
            inserted += len(batch)
            print(f"   Inserted {inserted}/{count} products...")
        
    print(f"   ✅ Added {count} new products (IDs {start_id} to {start_id + count - 1})")


def show_stats(conn, schema='prod'):
    """Show current table statistics for the target schema."""
    with conn.cursor() as cursor:
        print(f"\n📊 Current table statistics for schema '{schema}':")
        
        targets = [(schema, 'users'), (schema, 'products')]
        
        for tgt_schema, table in targets:
            try:
                # Basic check if table exists to avoid errors in output
                cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = %s AND table_schema = %s", (table, tgt_schema))
                if cursor.fetchone()[0] > 0:
                     cursor.execute(f"SELECT COUNT(*), MAX(id), MIN(id) FROM {tgt_schema}.{table}")
                     row = cursor.fetchone()
                     if row and row[0]:
                         print(f"   {table}: {row[0]:,} records (ID range: {row[2]} - {row[1]})")
                else:
                    print(f"   {table}: Table not found in {tgt_schema}")
            except mysql.connector.Error:
                pass


def main():
    parser = argparse.ArgumentParser(
        description='Generate test data in MySQL database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python init-scripts/mysql/generate-mysql-data.py --schema prod        # Add to Prod
  python init-scripts/mysql/generate-mysql-data.py --schema uat         # Add to UAT
  python init-scripts/mysql/generate-mysql-data.py --users 500 --schema prod
        """
    )
    parser.add_argument('--users', type=int, default=100, help='Number of users to generate (default: 100)')
    parser.add_argument('--products', type=int, default=50, help='Number of products to generate (default: 50)')
    parser.add_argument('--table', type=str, default='users', help='Target table name (default: users)')
    parser.add_argument('--schema', type=str, default=MYSQL_DATABASE, help=f'Target schema/database (default: {MYSQL_DATABASE})')
    parser.add_argument('--no-users', action='store_true', help='Skip generating users')
    parser.add_argument('--no-products', action='store_true', help='Skip generating products')
    parser.add_argument('--stats-only', action='store_true', help='Only show current statistics')
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("MySQL Test Data Generator")
    print("=" * 50)
    print(f"Host: {MYSQL_HOST}:{MYSQL_PORT}")
    
    conn = get_connection()
    print("✅ Connected to MySQL")
    
    if args.stats_only:
        show_stats(conn, args.schema)
        conn.close()
        return
    
    if not args.no_users and args.users > 0:
        generate_users(conn, args.users, args.table, args.schema)
    
    if not args.no_products and args.products > 0:
        generate_products(conn, args.products, table_name='products', schema=args.schema)
    
    show_stats(conn, args.schema)
    conn.close()
    
    print("\n" + "=" * 50)
    print("✅ Data generation completed!")
    print("=" * 50)
    print("\nYou can now run profiler:")
    print(f"  python main.py {args.table} -d mysql --schema {args.schema}")


if __name__ == '__main__':
    main()
