# DataProfiler - Developer Guide

This document provides technical details for developers working on the DataProfiler codebase.

## 📐 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                          main.py                                │
│         (CLI Parser, Entry Points, Orchestration)               │
└───────────────────────┬─────────────────────────────────────────┘
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
    ┌───────────┐ ┌───────────┐ ┌───────────────┐
    │  Profiler │ │    AI     │ │    Schema     │
    │  (Metrics)│ │(AutoIncr.)│ │  (Compare)    │
    └─────┬─────┘ └─────┬─────┘ └───────┬───────┘
          │             │               │
          └─────────────┴───────────────┘
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
    ┌───────────┐ ┌───────────┐ ┌───────────────┐
    │  Source   │ │  Metrics  │ │   Formatters  │
    │   DBs     │ │  Backend  │ │  (Output)     │
    └───────────┘ └───────────┘ └───────────────┘
```

### Data Flow

1. **Input**: User runs `main.py` with options (`--table` only required for `--data-profile` / `--profile-schema` / `--auto-increment`)
2. **Table Inventory**: Discover all tables in the schema and store in `table_inventory` (always runs)
3. **Data Profiling** (opt-in via `--data-profile`): Fetch column metadata, compute metrics, store and/or output
4. **Auto-Increment** (opt-in via `--auto-increment`, requires `--data-profile`): Analyse overflow risk
5. **Schema Profiling** (opt-in via `--profile-schema`): Store detailed schema metadata

---

## 📁 Project Structure

```
src/
├── config.py               # Environment variable loading
├── exceptions.py           # Custom exception classes
├── core/
│   ├── metrics.py          # dbt-profiler style metrics calculation
│   ├── formatters.py       # Output formatters (Markdown, JSON, CSV)
│   ├── autoincrement_metrics.py  # Growth rate & days-until-full
│   ├── schema_comparator.py      # Schema diff data structures
│   └── profiler.py         # (Legacy) Soda Core wrapper
└── db/
    ├── connection_factory.py # Unified DB connection interface
    ├── postgres.py          # PostgreSQL connector
    ├── mssql.py             # SQL Server connector
    ├── mysql.py             # MySQL connector
    ├── clickhouse.py        # ClickHouse metrics storage
    ├── postgres_metrics.py  # PostgreSQL metrics storage
    ├── autoincrement.py     # Auto-increment detectors
    └── schema_extractor.py  # Schema metadata extractors
```

---

## 🔌 Key Modules

### 1. Connection Factory (`src/db/connection_factory.py`)

Provides unified interface for database operations:

```python
from src.db.connection_factory import get_connection, get_table_metadata

# Get connection by type
conn = get_connection('postgresql')  # or 'mssql', 'mysql'

# Get table metadata
columns = get_table_metadata('users', 'postgresql', schema='public')
# Returns: [{'name': 'id', 'type': 'integer'}, ...]
```

**Key Functions:**
| Function | Purpose |
|----------|---------|
| `get_connection(db_type)` | Get database connection object |
| `get_table_metadata(table, db_type, schema)` | Get column metadata |
| `get_schema(db_type)` | Get configured schema name |
| `get_quote_char(db_type)` | Get SQL identifier quotes (`"`, `[`, `` ` ``) |
| `list_tables(db_type, schema)` | List all table names in a schema (for inventory) |

---

### 2. Metrics Calculation (`src/core/metrics.py`)

Calculates dbt-profiler compatible metrics:

```python
from src.core.metrics import profile_table, ColumnProfile

profile = profile_table(
    table_name='users',
    columns=[{'name': 'id', 'type': 'integer'}, ...],
    database_type='postgresql',
    schema='public'
)
```

**Supported Metrics:**

- `not_null_proportion` - Ratio of non-NULL values
- `distinct_proportion` - Ratio of unique values
- `distinct_count` - Unique value count
- `is_unique` - All values unique?
- `min_value`, `max_value` - For numeric/date types
- `avg`, `median`, `std_dev_*` - For numeric types only

**Database-Specific Notes:**
| Database | Median Support | Notes |
|----------|---------------|-------|
| PostgreSQL | ✅ `PERCENTILE_CONT()` | Full support |
| MSSQL | ✅ `PERCENTILE_CONT() OVER()` | Full support |
| MySQL | ❌ Returns `NULL` | No native function |

---

### 3. Auto-Increment Analysis (`src/db/autoincrement.py`)

Abstract base class with database-specific implementations:

```python
from src.db.autoincrement import get_autoincrement_detector

detector = get_autoincrement_detector('postgresql')
columns = detector.get_autoincrement_columns('users')
# Returns: [{'column_name': 'id', 'data_type': 'integer', 'sequence_name': '...'}]

value = detector.get_current_value(columns[0]['sequence_name'])
```

**Implementations:**
| Class | Database | Detection Method |
|-------|----------|------------------|
| `PostgreSQLAutoIncrementDetector` | PostgreSQL | `pg_get_serial_sequence()`, IDENTITY |
| `MSSQLAutoIncrementDetector` | SQL Server | `sys.identity_columns` |
| `MySQLAutoIncrementDetector` | MySQL | `information_schema.COLUMNS.EXTRA` |

---

### 4. Schema Extraction (`src/db/schema_extractor.py`)

Extracts detailed schema metadata for comparison:

```python
from src.db.schema_extractor import get_schema_extractor

extractor = get_schema_extractor('postgresql', connection)
schema = extractor.extract_table_schema('users', 'public')

# Access metadata
schema.columns    # dict[str, ColumnSchema]
schema.primary_key  # tuple[str, ...]
schema.indexes    # list[IndexSchema]
schema.foreign_keys  # list[ForeignKeySchema]
```

---

### 5. Metrics Storage

Two backend options for storing profiling results:

#### ClickHouse (`src/db/clickhouse.py`)

```python
from src.db.clickhouse import get_clickhouse_client, insert_column_profiles

client = get_clickhouse_client()
insert_column_profiles(client, column_profiles, 'myapp', 'production')
```

#### PostgreSQL (`src/db/postgres_metrics.py`)

```python
from src.db.postgres_metrics import get_pg_metrics_client, insert_column_profiles

client = get_pg_metrics_client()
insert_column_profiles(client, column_profiles, 'myapp', 'production')
```

---

## 🔧 Adding a New Database

### Step 1: Create Connector (`src/db/newdb.py`)

```python
from src.config import Config

def get_newdb_connection():
    """Create connection to NewDB."""
    import newdb_driver
    return newdb_driver.connect(
        host=Config.NEWDB_HOST,
        port=Config.NEWDB_PORT,
        ...
    )

def get_table_metadata(table_name: str, schema: str = None) -> list[dict]:
    """Get column metadata from information_schema."""
    conn = get_newdb_connection()
    # Query information_schema.columns
    # Return [{'name': col_name, 'type': data_type}, ...]
```

### Step 2: Update Connection Factory

Edit `src/db/connection_factory.py`:

```python
from src.db.newdb import get_newdb_connection, get_table_metadata as newdb_metadata

def get_connection(database_type):
    # ...existing code...
    elif db_type in ('newdb',):
        return get_newdb_connection()
```

### Step 3: Add Type Lists in Metrics

Edit `src/core/metrics.py`:

```python
NEWDB_NUMERIC_TYPES = ['int', 'bigint', 'decimal', ...]
NEWDB_MINMAX_TYPES = NEWDB_NUMERIC_TYPES + ['date', 'timestamp', ...]

def is_numeric_type(data_type, database_type):
    # Add newdb case
    elif db_type in ('newdb',):
        numeric_types = NEWDB_NUMERIC_TYPES
```

### Step 4: Add Auto-Increment Detector

Edit `src/db/autoincrement.py`:

```python
class NewDBAutoIncrementDetector(AutoIncrementDetector):
    def get_autoincrement_columns(self, table_name: str) -> list[dict]:
        # Query for auto-increment columns
        pass

    def get_current_value(self, sequence_name: str) -> Optional[int]:
        # Get current sequence value
        pass

def get_autoincrement_detector(database_type):
    # Add mapping
    'newdb': NewDBAutoIncrementDetector,
```

### Step 5: Add Schema Extractor

Edit `src/db/schema_extractor.py`:

```python
class NewDBSchemaExtractor(SchemaExtractor):
    def extract_table_schema(self, table_name, schema_name=None) -> TableSchema:
        # Implement extraction
        pass

def get_schema_extractor(database_type, connection):
    # Add mapping
    elif database_type == 'newdb':
        return NewDBSchemaExtractor(connection)
```

### Step 6: Update Configuration

Edit `src/config.py`:

```python
class Config:
    NEWDB_HOST = os.getenv('NEWDB_HOST', 'localhost')
    NEWDB_PORT = int(os.getenv('NEWDB_PORT', '1234'))
    # ...
```

---

## ⚠️ Known Limitations

### MySQL

| Feature            | Status   | Notes                                             |
| ------------------ | -------- | ------------------------------------------------- |
| Median calculation | ❌       | MySQL lacks `PERCENTILE_CONT()`                   |
| Byte encoding      | ⚠️ Fixed | `mysql-connector` returns bytes for some metadata |

### MSSQL

| Feature        | Status | Notes                            |
| -------------- | ------ | -------------------------------- |
| Azure SQL Edge | ✅     | Used for ARM64/M1 compatibility  |
| Startup time   | ⚠️     | Requires ~30s warmup before init |

---

## 🧪 Testing

```bash
# Run all tests
PYTHONPATH=. venv/bin/pytest

# Run with coverage
PYTHONPATH=. venv/bin/pytest --cov=src --cov-report=term-missing

# Run specific test file
PYTHONPATH=. venv/bin/pytest tests/test_mysql_connection.py -v
```

### Test Files

| File                                   | Coverage                 |
| -------------------------------------- | ------------------------ |
| `test_config.py`                       | Configuration loading    |
| `test_connections.py`                  | Database connections     |
| `test_autoincrement.py`                | Auto-increment detection |
| `test_mysql_schema_extractor_bytes.py` | MySQL byte decoding      |

---

## 🐳 Docker Development

### Architecture

The Docker Compose setup uses **two separate PostgreSQL instances** to prevent confusion:

| Service            | Port | Database           | Purpose                                                                                   |
| ------------------ | ---- | ------------------ | ----------------------------------------------------------------------------------------- |
| `postgres`         | 5432 | `postgres`         | Sample source database (prod/uat/public schemas)                                          |
| `postgres-metrics` | 5433 | `profiler_metrics` | Metrics storage (data_profiles, auto_increment_metrics, schema_profiles, table_inventory) |

### Commands

```bash
# Start all services
docker-compose up -d --build

# View logs
docker-compose logs -f backend

# Run profiler in container (inventory only)
docker-compose exec backend python ../main.py --app test --env dev

# Run profiler with data profiling
docker-compose exec backend python ../main.py --table users --data-profile --app test --env dev

# Profile multiple tables
docker-compose exec backend python ../main.py -t users,products --data-profile --app test --env dev

# Rebuild single service
docker-compose build backend && docker-compose up -d backend

# Reset all data (removes both DB volumes)
docker-compose down -v
```

---

## 📚 References

- [dbt-profiler](https://github.com/data-mie/dbt-profiler) - Metrics specification
- [Soda Core](https://docs.soda.io/soda-core/overview.html) - Data quality framework
- [mysql-connector-python](https://dev.mysql.com/doc/connector-python/en/) - MySQL driver
