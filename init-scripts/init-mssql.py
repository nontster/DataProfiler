#!/usr/bin/env python3
"""
Initialize MSSQL database with test data.
Usage: python init-scripts/init-mssql.py
"""

import time
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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


def wait_for_mssql(max_retries=30, delay=2):
    """Wait for MSSQL to be ready."""
    print(f"Waiting for MSSQL at {MSSQL_HOST}:{MSSQL_PORT}...")
    
    for i in range(max_retries):
        try:
            conn = pymssql.connect(
                server=MSSQL_HOST,
                port=MSSQL_PORT,
                user=MSSQL_USER,
                password=MSSQL_PASSWORD,
                database='master',
                login_timeout=5
            )
            conn.close()
            print(f"✅ MSSQL is ready! (attempt {i+1})")
            return True
        except pymssql.Error as e:
            print(f"   Attempt {i+1}/{max_retries}: {e}")
            time.sleep(delay)
    
    print("❌ MSSQL is not ready after maximum retries")
    return False


def run_sql(sql, database='master'):
    """Execute SQL statement."""
    conn = pymssql.connect(
        server=MSSQL_HOST,
        port=MSSQL_PORT,
        user=MSSQL_USER,
        password=MSSQL_PASSWORD,
        database=database,
        autocommit=True
    )
    cursor = conn.cursor()
    cursor.execute(sql)
    conn.close()


def main():
    if not wait_for_mssql():
        sys.exit(1)
    
    print("\n📦 Creating testdb database...")
    run_sql("""
        IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'testdb')
        BEGIN
            CREATE DATABASE testdb;
        END
    """)
    print("   ✅ testdb created")
    
    print("\n📋 Creating test_users table...")
    run_sql("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'test_users')
        BEGIN
            CREATE TABLE dbo.test_users (
                id INT IDENTITY(1,1) PRIMARY KEY,
                username NVARCHAR(100) NOT NULL,
                email NVARCHAR(255) NOT NULL,
                age INT,
                salary DECIMAL(10,2),
                is_active BIT DEFAULT 1,
                created_at DATETIME2 DEFAULT GETDATE()
            );
            
            INSERT INTO dbo.test_users (username, email, age, salary, is_active)
            VALUES 
                ('alice', 'alice@example.com', 28, 75000.00, 1),
                ('bob', 'bob@example.com', 35, 85000.50, 1),
                ('charlie', 'charlie@example.com', 42, 95000.75, 1),
                ('diana', 'diana@example.com', 31, 72000.25, 0),
                ('eve', 'eve@example.com', 29, 68000.00, 1);
        END
    """, database='testdb')
    print("   ✅ test_users created with 5 records")
    
    print("\n📋 Creating test_products table...")
    run_sql("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'test_products')
        BEGIN
            CREATE TABLE dbo.test_products (
                product_id BIGINT IDENTITY(1,1) PRIMARY KEY,
                name NVARCHAR(200) NOT NULL,
                price DECIMAL(12,2),
                quantity INT,
                category NVARCHAR(100)
            );
            
            INSERT INTO dbo.test_products (name, price, quantity, category)
            VALUES 
                ('Laptop Pro', 1299.99, 50, 'Electronics'),
                ('Wireless Mouse', 29.99, 200, 'Electronics'),
                ('USB-C Cable', 15.99, 500, 'Accessories');
        END
    """, database='testdb')
    print("   ✅ test_products created with 3 records")
    
    print("\n" + "=" * 50)
    print("✅ MSSQL initialization completed successfully!")
    print("=" * 50)
    print("\nYou can now run:")
    print("  python main.py test_users -d mssql")
    print("  python main.py test_products -d mssql --auto-increment")


if __name__ == '__main__':
    main()
