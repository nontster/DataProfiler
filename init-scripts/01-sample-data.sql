-- Sample data for testing DataProfiler
-- This script runs automatically when PostgreSQL container starts

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL,
    age INTEGER,
    salary NUMERIC(10, 2),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample data
INSERT INTO users (username, email, age, salary, is_active) VALUES
    ('john_doe', 'john@example.com', 28, 55000.00, true),
    ('jane_smith', 'jane@example.com', 34, 72000.00, true),
    ('bob_wilson', 'bob@example.com', 45, 85000.00, true),
    ('alice_johnson', 'alice@example.com', 29, 62000.00, false),
    ('charlie_brown', 'charlie@example.com', NULL, 48000.00, true),
    ('diana_prince', 'diana@example.com', 31, NULL, true),
    ('edward_stark', 'edward@example.com', 52, 120000.00, true),
    ('fiona_green', 'fiona@example.com', 27, 45000.00, false),
    ('george_lucas', 'george@example.com', 38, 95000.00, true),
    ('hannah_montana', 'hannah@example.com', 23, 38000.00, true);

-- Create products table for additional testing
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    price NUMERIC(10, 2),
    stock_quantity INTEGER,
    is_available BOOLEAN DEFAULT true
);

-- Insert sample products
INSERT INTO products (name, category, price, stock_quantity, is_available) VALUES
    ('Laptop Pro', 'Electronics', 1299.99, 50, true),
    ('Wireless Mouse', 'Electronics', 29.99, 200, true),
    ('Office Chair', 'Furniture', 249.99, 30, true),
    ('Standing Desk', 'Furniture', 599.99, 15, true),
    ('Coffee Maker', 'Appliances', 89.99, NULL, false),
    ('Notebook Set', 'Stationery', 12.99, 500, true),
    ('Monitor 27"', 'Electronics', 349.99, 75, true),
    ('Keyboard RGB', 'Electronics', 79.99, 120, true);

-- Verify data
SELECT 'users' as table_name, COUNT(*) as row_count FROM users
UNION ALL
SELECT 'products' as table_name, COUNT(*) as row_count FROM products;
