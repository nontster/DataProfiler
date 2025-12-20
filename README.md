🌐 **Language:** **English** | [ภาษาไทย](README.th.md)

# DataProfiler

Automated **Data Profiling** tool for PostgreSQL with [dbt-profiler](https://github.com/data-mie/dbt-profiler) style metrics, storing results in ClickHouse.

![Dashboard Screenshot](docs/images/dashboard.png)

## 🎯 Overview

DataProfiler provides:

1. **Automatic Schema Discovery** from PostgreSQL (information_schema)
2. **dbt-profiler Style Metrics** calculation via SQL queries
3. **Result Storage** in ClickHouse for analysis and tracking
4. **Multiple Export Formats**: Markdown, JSON, CSV, Console Table
5. **Web Dashboard** for data visualization (React + TailwindCSS)

## 📊 Profiled Metrics

For each column, the system collects the following statistics (dbt-profiler compatible):

| Metric                | Description                                 | Condition             |
| --------------------- | ------------------------------------------- | --------------------- |
| `column_name`         | Column name                                 | All columns           |
| `data_type`           | Data type                                   | All columns           |
| `not_null_proportion` | Proportion of non-NULL values (0.00 - 1.00) | All columns           |
| `distinct_proportion` | Proportion of unique values (0.00 - 1.00)   | All columns           |
| `distinct_count`      | Count of unique values                      | All columns           |
| `is_unique`           | Whether all values are unique (true/false)  | All columns           |
| `min` / `max`         | Minimum / Maximum values                    | numeric, date, time\* |
| `avg`                 | Average value                               | numeric\*\*           |
| `median`              | Median value                                | numeric\*\*           |
| `std_dev_population`  | Population standard deviation               | numeric\*\*           |
| `std_dev_sample`      | Sample standard deviation                   | numeric\*\*           |
| `profiled_at`         | Profile timestamp                           | All columns           |

> **\*** `min`/`max` supported for: integer, numeric, float, date, timestamp, time  
> **\*\*** `avg`, `median`, `std_dev` supported for: integer, numeric, float

## 🛠️ Requirements

- Python 3.10+
- PostgreSQL
- ClickHouse
- Dependencies:
  - `psycopg2` - PostgreSQL adapter
  - `clickhouse-connect` - ClickHouse client
  - `soda-core-postgres` - Soda Core for PostgreSQL
  - `jinja2` - Template engine
  - `python-dotenv` - Environment variable management

## 📦 Installation

1. Clone repository:

```bash
git clone <repository-url>
cd DataProfiler
```

2. Create and activate Virtual Environment:

```bash
# Create venv
python -m venv venv

# Activate (macOS/Linux)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

## ⚙️ Configuration

### 1. Create Environment Variables File

Copy `.env.example` to `.env` and edit values:

```bash
cp .env.example .env
```

Edit `.env` file:

```bash
# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_actual_password
POSTGRES_SCHEMA=public

# ClickHouse Configuration
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=your_actual_password
```

> ⚠️ **Important:** The `.env` file is already git-ignored. No need to worry about committing credentials.

### 2. Soda Core Configuration

Edit `configuration.yml` for Soda Core:

```yaml
data_source my_postgres:
  type: postgres
  host: ${POSTGRES_HOST}
  port: ${POSTGRES_PORT}
  username: ${POSTGRES_USER}
  password: ${POSTGRES_PASSWORD}
  database: ${POSTGRES_DATABASE}
  schema: ${POSTGRES_SCHEMA}
```

## 🚀 Usage

### Basic Usage

```bash
# Profile 'users' table (default app/env)
python main.py users

# Profile with Application & Environment context
python main.py users --app order-service --env uat
python main.py users --app order-service --env production

# Profile a specific table
python main.py products
```

### Output Formats

```bash
# Console table (default)
python main.py users --format table

# Markdown (dbt-profiler style)
python main.py users --format markdown

# JSON
python main.py users --format json

# CSV
python main.py users --format csv
```

### Save to File

```bash
python main.py users --format markdown --output profiles/users.md
python main.py users --format json --output profiles/users.json
python main.py users --format csv --output profiles/users.csv
```

### Additional Options

```bash
# Skip storing to ClickHouse
python main.py users --no-store

# Verbose logging
python main.py users -v

# Show help
python main.py --help
```

## 📁 Project Structure

```
DataProfiler/
├── .env.example           # Environment variables template
├── .env                   # Environment variables (git ignored)
├── .gitignore             # Git ignore rules
├── configuration.yml      # Soda Core data source configuration
├── docker-compose.yml     # Docker test environment
├── main.py                # Main entry point
├── init-scripts/          # PostgreSQL init scripts
│   └── 01-sample-data.sql
├── pytest.ini             # Pytest configuration
├── README.md              # Documentation (English)
├── README.th.md           # Documentation (Thai)
├── requirements.txt       # Python dependencies
├── src/                   # Source code modules
│   ├── __init__.py
│   ├── config.py          # Configuration management
│   ├── exceptions.py      # Custom exceptions
│   ├── core/              # Core profiling logic
│   │   ├── __init__.py
│   │   ├── formatters.py  # Output formatters (MD, JSON, CSV)
│   │   ├── metrics.py     # dbt-profiler style metrics
│   │   └── profiler.py    # Legacy Soda Core profiler
│   └── db/                # Database connections
│       ├── __init__.py
│       ├── clickhouse.py
│       └── postgres.py
├── tests/                 # Unit tests
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_connections.py
│   ├── test_metadata.py
│   └── test_profiler.py
└── venv/                  # Python virtual environment (git ignored)
```

## 🧪 Testing

```bash
# Activate virtual environment
source venv/bin/activate

# Run tests
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=src --cov-report=term-missing
```

## 🐳 Docker Development Environment

For testing, use Docker Compose to set up PostgreSQL and ClickHouse:

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

### Sample Data

Docker automatically creates sample data:

| Table      | Description                                           |
| ---------- | ----------------------------------------------------- |
| `users`    | 10 records - User data (with NULL values for testing) |
| `products` | 8 records - Product data                              |

### Stop Services

```bash
# Stop all services
docker-compose down

# Stop and remove all data
docker-compose down -v
```

## 📊 Dashboard

DataProfiler includes a Web Dashboard for visualizing profile data.

### Features

- **Sidebar Navigation** - Table list with row/column counts
- **Bar Charts** - Not Null Proportion, Distinct Proportion
- **Column Details Table** - All metrics in table format
- **Dark Theme** - Modern UI

### Running the Dashboard

```bash
# 1. Start Backend API (port 5001)
cd dashboard/backend
source ../venv/bin/activate
python app.py

# 2. Start Frontend (port 5173)
cd dashboard/frontend
npm install  # First time only
npm run dev

# 3. Open Browser
open http://localhost:5173
```

### Technology Stack

| Component | Technology         |
| --------- | ------------------ |
| Backend   | Flask + Flask-CORS |
| Frontend  | React + Vite       |
| Styling   | TailwindCSS        |
| Charts    | Recharts           |

## 📈 Grafana Dashboard (Alternative)

This project includes a **Grafana** instance connected to ClickHouse for advanced visualization.

### Features

- **Direct ClickHouse Integration**: No middleware required.
- **Customizable**: Create complex dashboards with SQL queries.
- **Alerting**: Native Grafana alerting support.
- **User Management**: Role-based access control.

### Setup

The Grafana service is included in `docker-compose.yml` and pre-configured with the ClickHouse datasource.

1. Start all services:

   ```bash
   docker-compose up -d
   ```

2. Open Grafana:

   - URL: http://localhost:3000
   - User: `admin`
   - Password: `admin`

3. Create Dashboard:
   - DataSource: **ClickHouse** (pre-configured)
   - Example Query:
     ```sql
     SELECT table_name, max(row_count) as rows
     FROM data_profiles
     WHERE application = 'order-service'
     GROUP BY table_name
     ```

## 📝 License

[MIT License](LICENSE)

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss.
