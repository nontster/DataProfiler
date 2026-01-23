#!/usr/bin/env python3
"""
Initialize MSSQL database with test data.
Usage: python init-scripts/mssql/init-mssql.py
"""

import time
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
    
    print("\n📦 Creating schemas...")
    run_sql("""
        IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'prod')
        BEGIN
            EXEC('CREATE SCHEMA prod')
        END
        
        IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'uat')
        BEGIN
            EXEC('CREATE SCHEMA uat')
        END
    """, database='testdb')
    print("   ✅ schemas 'prod' and 'uat' created")
    
    
    print("\n📋 Creating prod.users (Production) table...")
    run_sql("""
        IF NOT EXISTS (SELECT * FROM sys.tables t JOIN sys.schemas s ON t.schema_id = s.schema_id WHERE t.name = 'users' AND s.name = 'prod')
        BEGIN
            CREATE TABLE prod.users (
                id INT IDENTITY(1,1) PRIMARY KEY,
                username NVARCHAR(100) NOT NULL,
                
                -- Prod: NVARCHAR(100)
                email NVARCHAR(100) NOT NULL,
                
                age INT,
                salary DECIMAL(10,2),
                is_active BIT DEFAULT 1,
                created_at DATETIME2 DEFAULT GETDATE()
            );
            
            INSERT INTO prod.users (username, email, age, salary, is_active)
            VALUES 
                ('alice', 'alice@example.com', 28, 75000.00, 1),
                ('bob', 'bob@example.com', 35, 85000.50, 1),
                ('charlie', 'charlie@example.com', 42, 95000.75, 1),
                ('diana', 'diana@example.com', 31, 72000.25, 0),
                ('eve', 'eve@example.com', 29, 68000.00, 1);
            
            -- Create simple index
            CREATE INDEX idx_users_username ON prod.users(username);
            
            -- Create composite index
            CREATE INDEX idx_users_age_salary ON prod.users(age, salary);
            
            -- Create unique index
            CREATE UNIQUE INDEX idx_users_email ON prod.users(email);
        END
    """, database='testdb')
    print("   ✅ prod.users created with 5 records")

    print("\n📋 Creating uat.users (UAT) table...")
    run_sql("""
        IF NOT EXISTS (SELECT * FROM sys.tables t JOIN sys.schemas s ON t.schema_id = s.schema_id WHERE t.name = 'users' AND s.name = 'uat')
        BEGIN
            CREATE TABLE uat.users (
                id INT IDENTITY(1,1) PRIMARY KEY,
                username NVARCHAR(100) NOT NULL,
                
                -- Drift: NVARCHAR(150)
                email NVARCHAR(150) NOT NULL,
                
                -- Drift: NOT NULL
                age INT NOT NULL,
                
                -- Drift: DECIMAL(12,2)
                salary DECIMAL(12,2),
                
                is_active BIT DEFAULT 1,
                created_at DATETIME2 DEFAULT GETDATE(),
                
                -- Drift: Extra column
                middle_name NVARCHAR(50)
            );
            
            -- Insert data (copy from Prod)
            INSERT INTO uat.users (username, email, age, salary, is_active)
            SELECT username, email, age, salary, is_active FROM prod.users;
            
            -- UAT Indexes
            -- Drift: Missing username index
            CREATE INDEX idx_users_age_salary ON uat.users(age, salary);
            CREATE UNIQUE INDEX idx_users_email ON uat.users(email);
        END
    """, database='testdb')
    print("   ✅ uat.users created with 5 records")
    
    print("\n📋 Creating products table (dbo)...")
    run_sql("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'products' AND schema_id = SCHEMA_ID('dbo'))
        BEGIN
            CREATE TABLE dbo.products (
                product_id BIGINT IDENTITY(1,1) PRIMARY KEY,
                name NVARCHAR(200) NOT NULL,
                price DECIMAL(12,2),
                quantity INT,
                category NVARCHAR(100)
            );
            
            INSERT INTO dbo.products (name, price, quantity, category)
            VALUES 
                ('Laptop Pro', 1299.99, 50, 'Electronics'),
                ('Wireless Mouse', 29.99, 200, 'Electronics'),
                ('USB-C Cable', 15.99, 500, 'Accessories');
        END
    """, database='testdb')
    print("   ✅ products created with 3 records")
    
    print("\n" + "=" * 50)
    print("✅ MSSQL initialization completed successfully!")
    print("=" * 50)
    print("\nYou can now run:")
    print("  python main.py users -d mssql --schema prod")
    print("  python main.py users -d mssql --schema uat")
    print("  python main.py products -d mssql --auto-increment")


if __name__ == '__main__':
    main()
