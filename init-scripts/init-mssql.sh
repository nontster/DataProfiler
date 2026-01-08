#!/bin/bash
# init-mssql.sh - Initialize MSSQL database manually
# Usage: ./init-scripts/init-mssql.sh

set -e

MSSQL_HOST="${MSSQL_HOST:-localhost}"
MSSQL_PORT="${MSSQL_PORT:-1433}"
MSSQL_PASSWORD="${MSSQL_PASSWORD:-YourStrong@Password123}"

echo "Waiting for MSSQL to be ready..."
sleep 10

# Check if sqlcmd is available locally, otherwise use docker exec
if command -v sqlcmd &> /dev/null; then
    SQLCMD="sqlcmd -S ${MSSQL_HOST},${MSSQL_PORT} -U sa -P ${MSSQL_PASSWORD}"
else
    SQLCMD="docker exec -i dataprofiler-mssql /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P ${MSSQL_PASSWORD}"
fi

echo "Creating testdb database..."
$SQLCMD -Q "IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'testdb') CREATE DATABASE testdb;"

echo "Creating test_users table..."
$SQLCMD -d testdb -Q "
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
    
    PRINT 'Created test_users table with 5 sample records';
END
"

echo "Creating test_products table..."
$SQLCMD -d testdb -Q "
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
    
    PRINT 'Created test_products table with 3 sample records';
END
"

echo "✅ MSSQL initialization completed successfully!"
echo ""
echo "You can now run:"
echo "  python main.py test_users -d mssql"
