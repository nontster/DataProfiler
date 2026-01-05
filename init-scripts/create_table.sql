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
