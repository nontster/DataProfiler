#!/usr/bin/env python3
"""
Generate test data in PostgreSQL database.

Usage:
    python init-scripts/postgres/generate-postgres-data.py [--users N] [--products N] [--schema SCHEMA]

Examples:
    python init-scripts/postgres/generate-postgres-data.py              # Add to prod.users
    python init-scripts/postgres/generate-postgres-data.py --schema uat # Add to uat.users
    python init-scripts/postgres/generate-postgres-data.py --users 500  # Add 500 users
"""

import argparse
import random
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    import psycopg2
except ImportError:
    print("❌ psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

# Configuration
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
POSTGRES_PORT = int(os.getenv('POSTGRES_PORT', 5432))
POSTGRES_USER = os.getenv('POSTGRES_USER', 'postgres')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'password123')
POSTGRES_DATABASE = os.getenv('POSTGRES_DATABASE', 'postgres')


def get_connection():
    """Get PostgreSQL connection."""
    try:
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            dbname=POSTGRES_DATABASE
        )
        conn.autocommit = True
        return conn
    except psycopg2.Error as e:
        print(f"❌ Failed to connect to PostgreSQL: {e}")
        print(f"   Host: {POSTGRES_HOST}:{POSTGRES_PORT}")
        print(f"   Database: {POSTGRES_DATABASE}")
        sys.exit(1)


def get_max_id(conn, table, schema='public', id_column='id'):
    """Get the current max ID from a table."""
    with conn.cursor() as cursor:
        try:
            cursor.execute(f"SELECT COALESCE(MAX({id_column}), 0) FROM {schema}.{table}")
            result = cursor.fetchone()
            return result[0] if result else 0
        except psycopg2.Error:
            # Table might not exist
            return 0


def generate_users(conn, count, table_name='users', schema='prod'):
    """Generate test users."""
    full_table_name = f"{schema}.{table_name}"
    print(f"\n👤 Generating {count} users in {full_table_name}...")
    
    with conn.cursor() as cursor:
        # Check if table exists
        cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s AND table_schema = %s)", (table_name, schema))
        if not cursor.fetchone()[0]:
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
            is_active = 'true' if random.random() > 0.2 else 'false'
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


def generate_products(conn, count):
    """Generate test products."""
    # Products are in public schema
    schema = 'public'
    table = 'products'
    print(f"\n📦 Generating {count} products in {schema}.{table}...")
    
    with conn.cursor() as cursor:
        # Check if table exists
        cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s AND table_schema = %s)", (table, schema))
        if not cursor.fetchone()[0]:
            print(f"❌ Table '{table}' does not exist. Please run init scripts first.")
            return

        # Get starting point
        start_id = get_max_id(conn, table, schema, 'id') + 1 
        
        categories = ['Electronics', 'Accessories', 'Clothing', 'Home', 'Sports', 'Books', 'Toys']
        
        # Build batch insert
        values = []
        for i in range(count):
            idx = start_id + i
            name = f'Product_{idx}'
            price = round(random.uniform(10, 1000), 2)
            quantity = random.randint(0, 500)
            category = random.choice(categories)
            is_available = 'true' if quantity > 0 else 'false'
            # Note: columns based on 01-sample-data.sql: name, category, price, stock_quantity, is_available
            values.append(f"('{name}', '{category}', {price}, {quantity}, {is_available})")
        
        # Insert in batches of 1000
        batch_size = 1000
        inserted = 0
        
        for i in range(0, len(values), batch_size):
            batch = values[i:i+batch_size]
            sql = f"""
                INSERT INTO {schema}.{table} (name, category, price, stock_quantity, is_available)
                VALUES {','.join(batch)}
            """
            cursor.execute(sql)
            inserted += len(batch)
            print(f"   Inserted {inserted}/{count} products...")
        
    print(f"   ✅ Added {count} new products (IDs {start_id} to {start_id + count - 1})")


def show_stats(conn):
    """Show current table statistics."""
    with conn.cursor() as cursor:
        print("\n📊 Current table statistics:")
        
        targets = [('prod', 'users'), ('uat', 'users'), ('public', 'products')]
        
        for schema, table in targets:
            try:
                # Basic check if table exists to avoid errors in output
                cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s AND table_schema = %s)", (table, schema))
                if cursor.fetchone()[0]:
                     cursor.execute(f"SELECT COUNT(*), MAX(id), MIN(id) FROM {schema}.{table}")
                     row = cursor.fetchone()
                     if row and row[0]:
                         print(f"   {schema}.{table}: {row[0]:,} records (ID range: {row[2]} - {row[1]})")
                else:
                    pass
            except psycopg2.Error:
                conn.rollback() # Reset transaction state


def main():
    parser = argparse.ArgumentParser(
        description='Generate test data in PostgreSQL database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python init-scripts/postgres/generate-postgres-data.py --schema prod        # Add to Prod
  python init-scripts/postgres/generate-postgres-data.py --schema uat         # Add to UAT
  python init-scripts/postgres/generate-postgres-data.py --users 500 --schema prod
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
    print("PostgreSQL Test Data Generator")
    print("=" * 50)
    print(f"Host: {POSTGRES_HOST}:{POSTGRES_PORT}")
    print(f"Database: {POSTGRES_DATABASE}")
    
    conn = get_connection()
    print("✅ Connected to PostgreSQL")
    
    if args.stats_only:
        show_stats(conn)
        conn.close()
        return
    
    if not args.no_users and args.users > 0:
        generate_users(conn, args.users, args.table, args.schema)
    
    if not args.no_products and args.products > 0:
        generate_products(conn, args.products)
    
    show_stats(conn)
    conn.close()
    
    print("\n" + "=" * 50)
    print("✅ Data generation completed!")
    print("=" * 50)
    print("\nYou can now run profiler:")
    print(f"  python main.py {args.table} --schema {args.schema} --auto-increment")


if __name__ == '__main__':
    main()
