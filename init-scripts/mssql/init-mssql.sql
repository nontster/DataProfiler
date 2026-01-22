-- MSSQL Initialization Script for DataProfiler Testing
-- This script creates a test database and sample table with IDENTITY column

-- Create test database
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'testdb')
BEGIN
    CREATE DATABASE testdb;
END
GO

USE testdb;
GO

-- Create schema if not exists (dbo is default)
IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'dbo')
BEGIN
    EXEC('CREATE SCHEMA dbo');
END
GO

-- Create users table with IDENTITY column for auto-increment testing
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'users' AND schema_id = SCHEMA_ID('dbo'))
BEGIN
    CREATE TABLE dbo.users (
        id INT IDENTITY(1,1) PRIMARY KEY,
        username NVARCHAR(100) NOT NULL,
        email NVARCHAR(255) NOT NULL,
        age INT,
        salary DECIMAL(10,2),
        is_active BIT DEFAULT 1,
        created_at DATETIME2 DEFAULT GETDATE(),
        updated_at DATETIME2 DEFAULT GETDATE()
    );
    
    -- Insert sample data
    INSERT INTO dbo.users (username, email, age, salary, is_active)
    VALUES 
        ('alice', 'alice@example.com', 28, 75000.00, 1),
        ('bob', 'bob@example.com', 35, 85000.50, 1),
        ('charlie', 'charlie@example.com', 42, 95000.75, 1),
        ('diana', 'diana@example.com', 31, 72000.25, 0),
        ('eve', 'eve@example.com', 29, 68000.00, 1),
        ('frank', 'frank@example.com', 45, 110000.00, 1),
        ('grace', 'grace@example.com', 38, 92000.50, 1),
        ('henry', 'henry@example.com', 27, 65000.00, 0),
        ('iris', 'iris@example.com', 33, 88000.25, 1),
        ('jack', 'jack@example.com', 41, 105000.75, 1);
    
    PRINT 'Created users table with 10 sample records';
END
GO

-- Create products table with BIGINT IDENTITY for overflow testing
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'products' AND schema_id = SCHEMA_ID('dbo'))
BEGIN
    CREATE TABLE dbo.products (
        product_id BIGINT IDENTITY(1,1) PRIMARY KEY,
        name NVARCHAR(200) NOT NULL,
        price DECIMAL(12,2),
        quantity INT,
        category NVARCHAR(100)
    );
    
    -- Insert sample data
    INSERT INTO dbo.products (name, price, quantity, category)
    VALUES 
        ('Laptop Pro', 1299.99, 50, 'Electronics'),
        ('Wireless Mouse', 29.99, 200, 'Electronics'),
        ('USB-C Cable', 15.99, 500, 'Accessories'),
        ('Monitor 27"', 399.99, 30, 'Electronics'),
        ('Keyboard Mechanical', 89.99, 100, 'Electronics');
    
    PRINT 'Created products table with 5 sample records';
END
GO

PRINT 'MSSQL initialization completed successfully';
GO
