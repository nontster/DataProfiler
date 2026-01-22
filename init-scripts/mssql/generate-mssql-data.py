#!/usr/bin/env python3
"""
Generate test data in MSSQL database.

Usage:
    python init-scripts/mssql/generate-mssql-data.py [--users N] [--products N]

Examples:
    python init-scripts/mssql/generate-mssql-data.py              # Add 100 users and 50 products
    python init-scripts/mssql/generate-mssql-data.py --users 500  # Add 500 users only
    python init-scripts/mssql/generate-mssql-data.py --products 200  # Add 200 products only
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


def get_max_id(conn, table, id_column='id'):
    """Get the current max ID from a table."""
    cursor = conn.cursor()
    cursor.execute(f"SELECT ISNULL(MAX({id_column}), 0) FROM {table}")
    result = cursor.fetchone()
    return result[0] if result else 0


def generate_users(conn, count):
    """Generate test users."""
    print(f"\n👤 Generating {count} users in users...")
    
    cursor = conn.cursor()
    
    # Get starting point
    start_id = get_max_id(conn, 'users') + 1
    
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
            INSERT INTO dbo.users (username, email, age, salary, is_active)
            VALUES {','.join(batch)}
        """
        cursor.execute(sql)
        inserted += len(batch)
        print(f"   Inserted {inserted}/{count} users...")
    
    print(f"   ✅ Added {count} new users (IDs {start_id} to {start_id + count - 1})")


def generate_products(conn, count):
    """Generate test products."""
    print(f"\n📦 Generating {count} products in products...")
    
    cursor = conn.cursor()
    
    # Get starting point
    start_id = get_max_id(conn, 'products', 'product_id') + 1
    
    categories = ['Electronics', 'Accessories', 'Clothing', 'Home', 'Sports', 'Books', 'Toys']
    
    # Build batch insert
    values = []
    for i in range(count):
        idx = start_id + i
        name = f'Product_{idx}'
        price = round(random.uniform(10, 1000), 2)
        quantity = random.randint(0, 500)
        category = random.choice(categories)
        values.append(f"(N'{name}', {price}, {quantity}, N'{category}')")
    
    # Insert in batches of 1000
    batch_size = 1000
    inserted = 0
    
    for i in range(0, len(values), batch_size):
        batch = values[i:i+batch_size]
        sql = f"""
            INSERT INTO dbo.products (name, price, quantity, category)
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
    
    # Users
    cursor.execute("SELECT COUNT(*), MAX(id), MIN(id) FROM users")
    row = cursor.fetchone()
    if row and row[0]:
        print(f"   users: {row[0]:,} records (ID range: {row[2]} - {row[1]})")
    
    # Products
    cursor.execute("SELECT COUNT(*), MAX(product_id), MIN(product_id) FROM products")
    row = cursor.fetchone()
    if row and row[0]:
        print(f"   products: {row[0]:,} records (ID range: {row[2]} - {row[1]})")


def main():
    parser = argparse.ArgumentParser(
        description='Generate test data in MSSQL database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python init-scripts/mssql/generate-mssql-data.py              # Add 100 users and 50 products
  python init-scripts/mssql/generate-mssql-data.py --users 500  # Add 500 users only
  python init-scripts/mssql/generate-mssql-data.py --products 200  # Add 200 products only
  python init-scripts/mssql/generate-mssql-data.py --users 1000 --products 500  # Add both
        """
    )
    parser.add_argument('--users', type=int, default=100, help='Number of users to generate (default: 100)')
    parser.add_argument('--products', type=int, default=50, help='Number of products to generate (default: 50)')
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
        generate_users(conn, args.users)
    
    if not args.no_products and args.products > 0:
        generate_products(conn, args.products)
    
    show_stats(conn)
    conn.close()
    
    print("\n" + "=" * 50)
    print("✅ Data generation completed!")
    print("=" * 50)
    print("\nYou can now run profiler to see growth rate:")
    print("  python main.py users -d mssql --auto-increment")


if __name__ == '__main__':
    main()
