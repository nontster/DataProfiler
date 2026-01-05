INSERT INTO auto_increment_metrics (application, environment, database_host, database_name, schema_name, table_name, column_name, data_type, sequence_name, current_value, max_type_value, usage_percentage, remaining_values, daily_growth_rate, days_until_full, alert_status) VALUES
('dataprofiler', 'uat', 'postgres-uat', 'testdb', 'public', 'users', 'id', 'integer', 'users_id_seq', 10000, 2147483647, 0.000465, 2147473647, 500, 4294947, 'OK'),
('dataprofiler', 'uat', 'postgres-uat', 'testdb', 'public', 'orders', 'order_id', 'integer', 'orders_order_id_seq', 50000, 2147483647, 0.002328, 2147433647, 2500, 858973, 'OK'),
('dataprofiler', 'uat', 'postgres-uat', 'testdb', 'public', 'products', 'product_id', 'integer', 'products_product_id_seq', 5000, 2147483647, 0.000233, 2147478647, 100, 21474786, 'OK'),
('dataprofiler', 'production', 'postgres-prod', 'proddb', 'public', 'users', 'id', 'integer', 'users_id_seq', 1500000, 2147483647, 0.069849, 2145983647, 15000, 143065, 'OK'),
('dataprofiler', 'production', 'postgres-prod', 'proddb', 'public', 'orders', 'order_id', 'integer', 'orders_order_id_seq', 8500000, 2147483647, 0.395812, 2138983647, 85000, 25164, 'OK'),
('dataprofiler', 'production', 'postgres-prod', 'proddb', 'public', 'orders', 'order_id', 'bigint', 'orders_order_id_seq', 850000000, 9223372036854775807, 0.00000922, 9223372036003775807, 850000, 10851025925, 'OK'),
('dataprofiler', 'production', 'postgres-prod', 'proddb', 'public', 'products', 'product_id', 'integer', 'products_product_id_seq', 25000, 2147483647, 0.001164, 2147458647, 250, 8589835, 'OK');
