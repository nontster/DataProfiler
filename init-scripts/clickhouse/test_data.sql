-- Initialize data_profiles table
CREATE TABLE IF NOT EXISTS data_profiles (
    scan_time DateTime DEFAULT now(),
    application String DEFAULT 'default',
    environment LowCardinality(String) DEFAULT 'development',
    database_host String DEFAULT '',
    database_name String DEFAULT '',
    schema_name String DEFAULT 'public',
    table_name String,
    column_name String,
    data_type String,
    row_count Int64,
    not_null_proportion Nullable(Float64),
    distinct_proportion Nullable(Float64),
    distinct_count Nullable(Int64),
    is_unique UInt8,
    min Nullable(String),
    max Nullable(String),
    avg Nullable(Float64),
    median Nullable(Float64),
    std_dev_population Nullable(Float64),
    std_dev_sample Nullable(Float64)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(scan_time)
ORDER BY (application, environment, table_name, scan_time, column_name);

-- Clear existing test data (optional)
-- TRUNCATE TABLE data_profiles;

-- ==========================================================
-- TEST DATA FOR UAT ENVIRONMENT
-- ==========================================================
INSERT INTO data_profiles (
    application, environment, database_host, database_name, schema_name,
    table_name, column_name, data_type, row_count,
    not_null_proportion, distinct_proportion, distinct_count,
    is_unique, min, max, avg, median, std_dev_population, std_dev_sample
) VALUES
-- users table - UAT
('dataprofiler', 'uat', 'postgres-uat', 'testdb', 'public', 'users', 'id', 'integer', 10000, 1.0, 1.0, 10000, 1, '1', '10000', 5000.5, 5000.0, 2886.75, 2886.9),
('dataprofiler', 'uat', 'postgres-uat', 'testdb', 'public', 'users', 'username', 'varchar', 10000, 0.98, 0.95, 9500, 0, 'aardvark', 'zebra', NULL, NULL, NULL, NULL),
('dataprofiler', 'uat', 'postgres-uat', 'testdb', 'public', 'users', 'email', 'varchar', 10000, 0.95, 0.92, 9200, 0, 'a@test.com', 'z@test.com', NULL, NULL, NULL, NULL),
('dataprofiler', 'uat', 'postgres-uat', 'testdb', 'public', 'users', 'age', 'integer', 10000, 0.88, 0.07, 70, 0, '18', '85', 35.5, 34.0, 12.5, 12.6),
('dataprofiler', 'uat', 'postgres-uat', 'testdb', 'public', 'users', 'created_at', 'timestamp', 10000, 1.0, 0.85, 8500, 0, '2024-01-01', '2024-12-31', NULL, NULL, NULL, NULL),
('dataprofiler', 'uat', 'postgres-uat', 'testdb', 'public', 'users', 'status', 'varchar', 10000, 0.92, 0.0003, 3, 0, 'active', 'suspended', NULL, NULL, NULL, NULL),

-- orders table - UAT
('dataprofiler', 'uat', 'postgres-uat', 'testdb', 'public', 'orders', 'order_id', 'integer', 50000, 1.0, 1.0, 50000, 1, '1', '50000', 25000.5, 25000.0, 14433.76, 14433.9),
('dataprofiler', 'uat', 'postgres-uat', 'testdb', 'public', 'orders', 'user_id', 'integer', 50000, 1.0, 0.18, 9000, 0, '1', '10000', 5000.0, 5000.0, 2886.75, 2886.9),
('dataprofiler', 'uat', 'postgres-uat', 'testdb', 'public', 'orders', 'amount', 'decimal', 50000, 0.99, 0.45, 22500, 0, '9.99', '9999.99', 250.75, 150.0, 350.5, 350.6),
('dataprofiler', 'uat', 'postgres-uat', 'testdb', 'public', 'orders', 'status', 'varchar', 50000, 1.0, 0.0001, 5, 0, 'cancelled', 'shipped', NULL, NULL, NULL, NULL),
('dataprofiler', 'uat', 'postgres-uat', 'testdb', 'public', 'orders', 'created_at', 'timestamp', 50000, 1.0, 0.92, 46000, 0, '2024-01-01', '2024-12-31', NULL, NULL, NULL, NULL),

-- products table - UAT
('dataprofiler', 'uat', 'postgres-uat', 'testdb', 'public', 'products', 'product_id', 'integer', 5000, 1.0, 1.0, 5000, 1, '1', '5000', 2500.5, 2500.0, 1443.38, 1443.5),
('dataprofiler', 'uat', 'postgres-uat', 'testdb', 'public', 'products', 'name', 'varchar', 5000, 1.0, 0.98, 4900, 0, 'Apple iPhone', 'Zebra Printer', NULL, NULL, NULL, NULL),
('dataprofiler', 'uat', 'postgres-uat', 'testdb', 'public', 'products', 'price', 'decimal', 5000, 0.95, 0.35, 1750, 0, '0.99', '9999.99', 299.99, 149.99, 450.25, 450.3),
('dataprofiler', 'uat', 'postgres-uat', 'testdb', 'public', 'products', 'category', 'varchar', 5000, 0.92, 0.005, 25, 0, 'Books', 'Toys', NULL, NULL, NULL, NULL),
('dataprofiler', 'uat', 'postgres-uat', 'testdb', 'public', 'products', 'stock', 'integer', 5000, 0.88, 0.08, 400, 0, '0', '9999', 250.0, 100.0, 500.5, 500.6);

-- ==========================================================
-- TEST DATA FOR PRODUCTION ENVIRONMENT
-- (Different values to show comparison differences)
-- ==========================================================
INSERT INTO data_profiles (
    application, environment, database_host, database_name, schema_name,
    table_name, column_name, data_type, row_count,
    not_null_proportion, distinct_proportion, distinct_count,
    is_unique, min, max, avg, median, std_dev_population, std_dev_sample
) VALUES
-- users table - Production (higher row count, better data quality)
('dataprofiler', 'production', 'postgres-prod', 'proddb', 'public', 'users', 'id', 'integer', 1500000, 1.0, 1.0, 1500000, 1, '1', '1500000', 750000.5, 750000.0, 433012.7, 433013.0),
('dataprofiler', 'production', 'postgres-prod', 'proddb', 'public', 'users', 'username', 'varchar', 1500000, 1.0, 0.99, 1485000, 0, 'aardvark1', 'zyzzyva999', NULL, NULL, NULL, NULL),
('dataprofiler', 'production', 'postgres-prod', 'proddb', 'public', 'users', 'email', 'varchar', 1500000, 1.0, 0.995, 1492500, 1, 'a@company.com', 'z@company.com', NULL, NULL, NULL, NULL),
('dataprofiler', 'production', 'postgres-prod', 'proddb', 'public', 'users', 'age', 'integer', 1500000, 0.95, 0.05, 75, 0, '13', '99', 38.2, 36.0, 14.8, 14.9),
('dataprofiler', 'production', 'postgres-prod', 'proddb', 'public', 'users', 'created_at', 'timestamp', 1500000, 1.0, 0.75, 1125000, 0, '2020-01-01', '2024-12-31', NULL, NULL, NULL, NULL),
('dataprofiler', 'production', 'postgres-prod', 'proddb', 'public', 'users', 'status', 'varchar', 1500000, 1.0, 0.0002, 4, 0, 'active', 'verified', NULL, NULL, NULL, NULL),
-- Production has extra column not in UAT
('dataprofiler', 'production', 'postgres-prod', 'proddb', 'public', 'users', 'last_login', 'timestamp', 1500000, 0.85, 0.65, 975000, 0, '2024-01-01', '2024-12-31', NULL, NULL, NULL, NULL),

-- orders table - Production (much higher volume)
('dataprofiler', 'production', 'postgres-prod', 'proddb', 'public', 'orders', 'order_id', 'integer', 8500000, 1.0, 1.0, 8500000, 1, '1', '8500000', 4250000.5, 4250000.0, 2453626.0, 2453627.0),
('dataprofiler', 'production', 'postgres-prod', 'proddb', 'public', 'orders', 'user_id', 'integer', 8500000, 1.0, 0.15, 1275000, 0, '1', '1500000', 750000.0, 750000.0, 433012.7, 433013.0),
('dataprofiler', 'production', 'postgres-prod', 'proddb', 'public', 'orders', 'amount', 'decimal', 8500000, 1.0, 0.55, 4675000, 0, '0.01', '99999.99', 350.25, 175.0, 580.75, 580.8),
('dataprofiler', 'production', 'postgres-prod', 'proddb', 'public', 'orders', 'status', 'varchar', 8500000, 1.0, 0.00006, 6, 0, 'cancelled', 'refunded', NULL, NULL, NULL, NULL),
('dataprofiler', 'production', 'postgres-prod', 'proddb', 'public', 'orders', 'created_at', 'timestamp', 8500000, 1.0, 0.88, 7480000, 0, '2020-01-01', '2024-12-31', NULL, NULL, NULL, NULL),
-- Production has extra columns
('dataprofiler', 'production', 'postgres-prod', 'proddb', 'public', 'orders', 'shipping_address', 'text', 8500000, 0.92, 0.45, 3825000, 0, '1 Main St', '99999 Zebra Lane', NULL, NULL, NULL, NULL),
('dataprofiler', 'production', 'postgres-prod', 'proddb', 'public', 'orders', 'discount_code', 'varchar', 8500000, 0.35, 0.001, 8500, 0, 'DEAL10', 'XMAS50', NULL, NULL, NULL, NULL),

-- products table - Production
('dataprofiler', 'production', 'postgres-prod', 'proddb', 'public', 'products', 'product_id', 'integer', 25000, 1.0, 1.0, 25000, 1, '1', '25000', 12500.5, 12500.0, 7216.88, 7217.0),
('dataprofiler', 'production', 'postgres-prod', 'proddb', 'public', 'products', 'name', 'varchar', 25000, 1.0, 0.995, 24875, 0, 'ACME Widget', 'Zephyr Drone', NULL, NULL, NULL, NULL),
('dataprofiler', 'production', 'postgres-prod', 'proddb', 'public', 'products', 'price', 'decimal', 25000, 1.0, 0.42, 10500, 0, '0.01', '49999.99', 499.99, 199.99, 850.75, 850.8),
('dataprofiler', 'production', 'postgres-prod', 'proddb', 'public', 'products', 'category', 'varchar', 25000, 1.0, 0.003, 75, 0, 'Accessories', 'Wearables', NULL, NULL, NULL, NULL),
('dataprofiler', 'production', 'postgres-prod', 'proddb', 'public', 'products', 'stock', 'integer', 25000, 0.98, 0.12, 3000, 0, '0', '50000', 500.0, 200.0, 1200.5, 1200.6),
-- Production has extra columns
('dataprofiler', 'production', 'postgres-prod', 'proddb', 'public', 'products', 'rating', 'decimal', 25000, 0.88, 0.01, 50, 0, '1.0', '5.0', 4.2, 4.3, 0.75, 0.76),
('dataprofiler', 'production', 'postgres-prod', 'proddb', 'public', 'products', 'review_count', 'integer', 25000, 0.75, 0.15, 3750, 0, '0', '15000', 150.0, 50.0, 450.25, 450.3);
