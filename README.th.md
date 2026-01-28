🌐 **Language:** [English](README.md) | **ภาษาไทย**

# DataProfiler

เครื่องมือสำหรับทำ **Data Profiling** อัตโนมัติจาก **PostgreSQL** และ **Microsoft SQL Server** แบบ [dbt-profiler](https://github.com/data-mie/dbt-profiler) style และจัดเก็บผลลัพธ์ลง ClickHouse

![Dashboard Screenshot](docs/images/react_environment_comparison_dashboard.png)

## 🎯 ภาพรวม

DataProfiler ทำหน้าที่:

1. **รองรับหลาย Database**: PostgreSQL, Microsoft SQL Server (Azure SQL Edge), และ **MySQL**
2. **ดึงข้อมูล Schema** อัตโนมัติจาก database ต้นทาง (information_schema)
3. **คำนวณ Metrics** แบบ dbt-profiler style ด้วย SQL queries
4. **จัดเก็บผลลัพธ์** ลง ClickHouse เพื่อการวิเคราะห์และติดตาม
5. **Export ได้หลายรูปแบบ**: Markdown, JSON, CSV, Console Table
6. **Web Dashboard** สำหรับ visualize ข้อมูล (React + TailwindCSS)
7. **วิเคราะห์ความเสี่ยง Auto-Increment Overflow** พร้อมทำนายการเติบโตด้วย Linear Regression

## 📊 ข้อมูลที่ Profile

สำหรับแต่ละ Column ระบบจะเก็บข้อมูลสถิติดังนี้ (dbt-profiler compatible):

| Metric                | คำอธิบาย                                | Condition             |
| --------------------- | --------------------------------------- | --------------------- |
| `column_name`         | ชื่อ column                             | ทุก column            |
| `data_type`           | ประเภทข้อมูล                            | ทุก column            |
| `not_null_proportion` | สัดส่วนค่าที่ไม่เป็น NULL (0.00 - 1.00) | ทุก column            |
| `distinct_proportion` | สัดส่วนค่าที่ไม่ซ้ำกัน (0.00 - 1.00)    | ทุก column            |
| `distinct_count`      | จำนวนค่าที่ไม่ซ้ำกัน                    | ทุก column            |
| `is_unique`           | เป็น unique หรือไม่ (true/false)        | ทุก column            |
| `min` / `max`         | ค่าต่ำสุด / สูงสุด                      | numeric, date, time\* |
| `avg`                 | ค่าเฉลี่ย                               | numeric\*\*           |
| `median`              | ค่ามัธยฐาน                              | numeric\*\*           |
| `std_dev_population`  | Standard deviation (population)         | numeric\*\*           |
| `std_dev_sample`      | Standard deviation (sample)             | numeric\*\*           |
| `profiled_at`         | เวลาที่ทำ profile                       | ทุก column            |

> **\*** `min`/`max` รองรับเฉพาะ: integer, numeric, float, date, timestamp, time  
> **\*\*** `avg`, `median`, `std_dev` รองรับเฉพาะ: integer, numeric, float

## 🔮 การวิเคราะห์ความเสี่ยง Auto-Increment Overflow

DataProfiler มีฟีเจอร์ **วิเคราะห์ความเสี่ยง Auto-Increment Column Overflow** เพื่อทำนายว่า Primary Key จะเต็มเมื่อใด

### ฟีเจอร์

- **ติดตามค่าปัจจุบัน**: ตรวจสอบค่าปัจจุบันของ auto-increment columns
- **คำนวณค่าสูงสุด**: คำนวณค่า max ตาม data type (เช่น INT, BIGINT)
- **เปอร์เซ็นต์การใช้งาน**: คำนวณ capacity ที่ใช้ไปแล้ว
- **ทำนายอัตราการเติบโต**: ใช้ Linear Regression กับข้อมูลย้อนหลังจาก ClickHouse
- **จำนวนวันก่อนเต็ม**: ทำนายว่าอีกกี่วัน column จะถึงค่าสูงสุด
- **สถานะแจ้งเตือน**: CRITICAL (< 30 วัน / > 90%), WARNING (< 90 วัน / > 75%), NORMAL

### Data Types ที่รองรับ

| Data Type   | ค่าสูงสุด                 | ช่วง                                   |
| ----------- | ------------------------- | -------------------------------------- |
| `smallint`  | 32,767                    | -32,768 ถึง 32,767                     |
| `integer`   | 2,147,483,647             | -2.1 พันล้าน ถึง 2.1 พันล้าน           |
| `bigint`    | 9,223,372,036,854,775,807 | -9.2 ควินทิลเลียน ถึง 9.2 ควินทิลเลียน |
| `serial`    | 2,147,483,647             | 1 ถึง 2.1 พันล้าน                      |
| `bigserial` | 9,223,372,036,854,775,807 | 1 ถึง 9.2 ควินทิลเลียน                 |

#### MSSQL Data Types

| Data Type  | ค่าสูงสุด                 | ช่วง                                   |
| ---------- | ------------------------- | -------------------------------------- |
| `tinyint`  | 255                       | 0 ถึง 255                              |
| `smallint` | 32,767                    | -32,768 ถึง 32,767                     |
| `int`      | 2,147,483,647             | -2.1 พันล้าน ถึง 2.1 พันล้าน           |
| `bigint`   | 9,223,372,036,854,775,807 | -9.2 ควินทิลเลียน ถึง 9.2 ควินทิลเลียน |

> **หมายเหตุ**: รองรับทั้ง PostgreSQL SERIAL/BIGSERIAL/IDENTITY columns และ MSSQL IDENTITY columns

## 🏗️ Schema Profiling & Comparison

DataProfiler สามารถทำ Profile ข้อมูล Schema (Columns, Data Types, Indexes, Foreign Keys) และจัดเก็บเพื่อเปรียบเทียบระหว่าง Environment ที่แตกต่างกัน (เช่น UAT เทียบกับ Production)

### ฟีเจอร์

- **Schema Snapshot**: เก็บข้อมูล Metadata ของ Schema อย่างละเอียด
- **Comparison Dashboard**: เปรียบเทียบความแตกต่างผ่าน Grafana Dashboard
- **Multi-Database Support**: รองรับการ Profile Schema จากทั้ง PostgreSQL และ MSSQL
- **Strict Mode**: เปรียบเทียบค่า Default, Nullability และ Index Structure อย่างละเอียด

### ข้อมูลที่เปรียบเทียบ

| หมวดหมู่        | ตรวจสอบ                                            |
| --------------- | -------------------------------------------------- |
| **Columns**     | การมีอยู่, Data Types, Nullability, Default Values |
| **Indexes**     | Primary Keys, Index Membership, ชื่อ Index         |
| **Constraints** | Foreign Keys, Check Constraints                    |

### การใช้งาน

```bash
# PostgreSQL (ค่าเริ่มต้น)
python main.py users --auto-increment

# MSSQL
python main.py users -d mssql --auto-increment

# กำหนดระยะเวลาย้อนหลัง (ค่าเริ่มต้น: 7 วัน)
python main.py users --auto-increment --lookback-days 14

# พร้อมระบุ application และ environment
python main.py users --app order-service --env production --auto-increment
```

### Schema Profiling

```bash
# Profile schema สำหรับ User Service ที่ Production
python main.py users --profile-schema --app user-service --env production

# Profile table เดียวกันที่ UAT
python main.py users --profile-schema --app user-service --env uat

# ดูผลการเปรียบเทียบผ่าน Grafana Dashboard
```

### ตัวอย่าง Output

```
============================================================
AUTO-INCREMENT OVERFLOW RISK ANALYSIS
============================================================

🟢 users.id (integer)
   Current: 1,234,567 / 2,147,483,647
   Usage: 0.057479%
   Days until full: 4,521 days
   Growth rate: ~500 IDs/day
============================================================
```

## 🛠️ Requirements

- Python 3.10+
- PostgreSQL และ/หรือ Microsoft SQL Server (Azure SQL Edge สำหรับ ARM64/M1)
- MySQL (v8.0+)
- ClickHouse
- Dependencies:
  - `psycopg2` - PostgreSQL adapter
  - `pymssql` - MSSQL adapter
  - `clickhouse-connect` - ClickHouse client
  - `mysql-connector-python` - MySQL adapter
  - `soda-core-postgres` - Soda Core for PostgreSQL
  - `soda-core-sqlserver` - Soda Core for SQL Server
  - `jinja2` - Template engine
  - `python-dotenv` - Environment variable management
  - `numpy` - Numerical computing
  - `scipy` - Scientific computing (Linear Regression)

## 📦 Installation

1. Clone repository:

```bash
git clone <repository-url>
cd DataProfiler
```

2. สร้าง Virtual Environment และ Activate:

```bash
# สร้าง venv
python -m venv venv

# Activate (macOS/Linux)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

3. ติดตั้ง Dependencies จาก requirements.txt:

```bash
pip install -r requirements.txt
```

> **หมายเหตุ:** หากต้องการอัปเดต dependencies ให้รัน `pip install -r requirements.txt --upgrade`

## ⚙️ Configuration

### 1. สร้างไฟล์ Environment Variables

คัดลอก `.env.example` เป็น `.env` และแก้ไขค่าตามจริง:

```bash
cp .env.example .env
```

แก้ไขไฟล์ `.env`:

```bash
# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_actual_password
POSTGRES_SCHEMA=public

# MySQL Configuration
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=prod
MYSQL_USER=user
MYSQL_PASSWORD=password123

# ClickHouse Configuration
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=your_actual_password
```

> ⚠️ **สำคัญ:** ไฟล์ `.env` ถูก ignore โดย git อยู่แล้ว ไม่ต้องกังวลเรื่อง commit credentials

### 2. Soda Core Configuration

แก้ไขไฟล์ `configuration.yml` สำหรับ Soda Core:

```yaml
data_source my_postgres:
  type: postgres
  host: ${POSTGRES_HOST}
  port: ${POSTGRES_PORT}
  username: ${POSTGRES_USER}
  password: ${POSTGRES_PASSWORD}
  database: ${POSTGRES_DATABASE}
  schema: ${POSTGRES_SCHEMA}

data_source my_mssql:
  type: sqlserver
  host: ${MSSQL_HOST}
  port: ${MSSQL_PORT}
  username: ${MSSQL_USER}
  password: ${MSSQL_PASSWORD}
  database: ${MSSQL_DATABASE}
  schema: ${MSSQL_SCHEMA}
```

## 🚀 Usage

### Basic Usage

```bash
# Profile 'users' table จาก PostgreSQL (ค่าเริ่มต้น)
python main.py users

# Profile จาก Schema ที่กำหนด (เช่น 'prod' หรือ 'uat')
python main.py users --schema prod

# Profile จาก MSSQL
python main.py users -d mssql

# Profile with Application & Environment context
python main.py users -d mssql --app user-service --env uat --auto-increment --metrics-backend postgresql
python main.py users -d mssql --app user-service --env production --auto-increment --metrics-backend postgresql

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

### Options เพิ่มเติม

```bash
# ไม่เก็บผลลัพธ์ลง Metrics Backend
python main.py users --no-store

# Verbose logging
python main.py users -v

# ดู help
python main.py --help
```

### การเลือกประเภท Database (`-d`, `--database-type`)

เลือก source database ที่ต้องการ profile:

| Option       | รายละเอียด               | Environment Variables ที่ต้องการ                   |
| ------------ | ------------------------ | -------------------------------------------------- |
| `postgresql` | PostgreSQL (ค่าเริ่มต้น) | `POSTGRES_HOST`, `POSTGRES_PORT`, etc.             |
| `mssql`      | Microsoft SQL Server     | `MSSQL_HOST`, `MSSQL_PORT`, `MSSQL_DATABASE`, etc. |
| `mysql`      | MySQL                    | `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DATABASE`, etc. |

```bash
# Profile จาก PostgreSQL (ค่าเริ่มต้น)
python main.py users

# Profile จาก MSSQL
python main.py users -d mssql
python main.py orders --database-type mssql

# MSSQL พร้อมวิเคราะห์ auto-increment
python main.py users -d mssql --auto-increment
```

### การเลือก Metrics Backend (`--metrics-backend`)

เลือกที่เก็บผลลัพธ์การ profiling:

| Option       | รายละเอียด               | Environment Variables ที่ต้องการ          |
| ------------ | ------------------------ | ----------------------------------------- |
| `clickhouse` | ClickHouse (ค่าเริ่มต้น) | `CLICKHOUSE_HOST`, `CLICKHOUSE_PORT`      |
| `postgresql` | PostgreSQL               | `PG_METRICS_*` หรือใช้ค่าจาก `POSTGRES_*` |

```bash
# ใช้ ClickHouse (ค่าเริ่มต้น)
python main.py users

# ใช้ PostgreSQL เป็นที่เก็บ metrics
python main.py users --metrics-backend postgresql

# รวมกัน: Profile จาก MSSQL, เก็บใน PostgreSQL
python main.py orders -d mssql --metrics-backend postgresql
```

### การวิเคราะห์ Auto-Increment

```bash
# รวมการวิเคราะห์ auto-increment overflow
python main.py users --auto-increment
python main.py users -d mssql --auto-increment

# กำหนดระยะเวลาย้อนหลังสำหรับคำนวณ growth rate
python main.py users --auto-increment --lookback-days 14
```

### ตัวอย่างแบบสมบูรณ์: Profile MSSQL พร้อมเก็บใน PostgreSQL

```bash
# กำหนด environment variables
export MSSQL_HOST=sqlserver.local
export MSSQL_PORT=1433
export MSSQL_DATABASE=sales_db
export MSSQL_USER=sa
export MSSQL_PASSWORD='YourStrong@Password123'
export MSSQL_SCHEMA=dbo

export PG_METRICS_HOST=metrics-db.local
export PG_METRICS_PORT=5432
export PG_METRICS_DATABASE=profiler_metrics
export PG_METRICS_USER=metrics_user
export PG_METRICS_PASSWORD='your_password'

# รัน profiler
python main.py orders \
  -d mssql \
  --metrics-backend postgresql \
  --app sales-service \
  --env production \
  --schema prod \
  --auto-increment
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
├── init-scripts/             # Database initialization scripts
│   ├── clickhouse/           # ClickHouse schema & test data
│   ├── mssql/                # MSSQL init & data generation
│   └── postgres/             # PostgreSQL init & data generation
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
│   │   ├── autoincrement_metrics.py  # Auto-increment analysis
│   │   ├── formatters.py  # Output formatters (MD, JSON, CSV)
│   │   ├── metrics.py     # dbt-profiler style metrics
│   │   └── profiler.py    # Legacy Soda Core profiler
│   └── db/                # Database connections
│       ├── __init__.py
│       ├── autoincrement.py  # Auto-increment detector (PostgreSQL & MSSQL)
│       ├── clickhouse.py
│       ├── connection_factory.py  # Multi-database factory
│       ├── mssql.py        # MSSQL client
│       └── postgres.py
├── tests/                 # Unit tests
│   ├── __init__.py
│   ├── test_autoincrement.py
│   ├── test_config.py
│   ├── test_connections.py
│   ├── test_metadata.py
│   └── test_profiler.py
└── venv/                  # Python virtual environment (git ignored)
```

## 🧪 Testing

### Run All Tests

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

## ⏰ Control-M Integration

DataProfiler มี wrapper script สำหรับรันเป็น scheduled job บน **Control-M** หรือ job scheduler อื่นๆ

### ตำแหน่ง Wrapper Script

```
scripts/run_profiler.sh
```

### รองรับ CLI Arguments

Wrapper script รองรับการส่ง CLI arguments ไปยัง Python profiler โดยตรง CLI arguments จะ **override** environment variables

```bash
# ดู help
scripts/run_profiler.sh -h
scripts/run_profiler.sh --help

# Override database type ผ่าน CLI (ไม่สนใจ PROFILER_DB_TYPE env var)
scripts/run_profiler.sh -d mssql
scripts/run_profiler.sh --database-type mssql

# Override metrics backend ผ่าน CLI (ไม่สนใจ METRICS_BACKEND env var)
scripts/run_profiler.sh --metrics-backend postgresql

# ระบุชื่อ table ผ่าน CLI (ไม่สนใจ PROFILER_TABLE env var)
scripts/run_profiler.sh orders

# Override schema (ไม่สนใจ PROFILER_SCHEMA env var)
scripts/run_profiler.sh --schema uat

# รวม CLI arguments หลายตัว
scripts/run_profiler.sh orders -d mssql --metrics-backend postgresql --auto-increment --schema prod

# ไม่เก็บ metrics
scripts/run_profiler.sh --no-store
```

#### ลำดับความสำคัญของ Arguments

CLI arguments มีความสำคัญกว่า environment variables:

| Configuration | ลำดับ   | ตัวอย่าง                       |
| ------------- | ------- | ------------------------------ |
| CLI argument  | 1 (สูง) | `--metrics-backend postgresql` |
| Environment   | 2 (ต่ำ) | `METRICS_BACKEND=clickhouse`   |

ตัวอย่าง: ถ้าตั้ง `METRICS_BACKEND=clickhouse` แต่รัน:

```bash
scripts/run_profiler.sh --metrics-backend postgresql
```

Script จะใช้ **PostgreSQL** ในการเก็บ metrics

### Environment Variables สำหรับ Control-M

กำหนด environment variables เหล่านี้ใน Control-M job definition:

#### Database Connection & Metrics Backend

อ้างอิงส่วน **[Configuration](#%EF%B8%8F-configuration)** สำหรับ environment variables ที่จำเป็น:

- `POSTGRES_*`
- `MSSQL_*`
- `CLICKHOUSE_*`
- `PG_METRICS_*`

#### Profiler Options (ไม่บังคับ)

| Variable                  | ค่าเริ่มต้น  | คำอธิบาย                                          |
| ------------------------- | ------------ | ------------------------------------------------- |
| `PROFILER_TABLE`          | `users`      | ชื่อ table ที่จะ profile                          |
| `PROFILER_SCHEMA`         | (default DB) | ชื่อ Schema (เช่น `public`, `dbo`, `prod`, `uat`) |
| `PROFILER_FORMAT`         | `table`      | Output format: `table`, `markdown`, `json`, `csv` |
| `PROFILER_OUTPUT_FILE`    | -            | File path สำหรับบันทึก output                     |
| `PROFILER_APP`            | `default`    | ชื่อ Application                                  |
| `PROFILER_ENV`            | `production` | ชื่อ Environment                                  |
| `PROFILER_DB_TYPE`        | `postgresql` | Database type: `postgresql`, `mssql`, `mysql`     |
| `METRICS_BACKEND`         | `clickhouse` | Metrics backend: `clickhouse`, `postgresql`       |
| `PROFILER_AUTO_INCREMENT` | `false`      | เปิดใช้การวิเคราะห์ auto-increment                |
| `PROFILER_PROFILE_SCHEMA` | `false`      | เปิดใช้งาน Schema Profiling                       |
| `PROFILER_LOOKBACK_DAYS`  | `7`          | จำนวนวันสำหรับคำนวณ growth rate                   |
| `PROFILER_NO_STORE`       | `false`      | ไม่เก็บ metrics                                   |
| `PROFILER_VERBOSE`        | `false`      | เปิด verbose logging                              |
| `PYTHON_PATH`             | `python3`    | Path ไปยัง Python executable                      |
| `PROFILER_HOME`           | (script dir) | Path ไปยัง DataProfiler installation              |

### Exit Codes

| Code | คำอธิบาย                                                       |
| ---- | -------------------------------------------------------------- |
| `0`  | สำเร็จ                                                         |
| `1`  | ข้อผิดพลาด configuration (ขาด environment variables ที่จำเป็น) |
| `2`  | ข้อผิดพลาดการทำงาน (profiler ล้มเหลว)                          |
| `3`  | ข้อผิดพลาด Python environment                                  |

### ตัวอย่าง Control-M Job

#### ตัวอย่าง 1: PostgreSQL + ClickHouse Metrics

```bash
# Job: DATA_PROFILER_USERS_PROD
# Application: DataOps
# Sub-Application: Profiling

# Environment Variables (set ใน Control-M):
POSTGRES_HOST=db.production.internal
POSTGRES_PORT=5432
POSTGRES_DATABASE=app_db
POSTGRES_USER=profiler_svc
POSTGRES_PASSWORD='your_secure_password'
CLICKHOUSE_HOST=ch.production.internal
CLICKHOUSE_PORT=8123
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD='your_secure_password'
PROFILER_TABLE=users
PROFILER_APP=order-service
PROFILER_ENV=production
PROFILER_AUTO_INCREMENT=true

# Command:
/opt/dataprofiler/scripts/run_profiler.sh
```

> **Local Development**: ใช้ค่า default จาก Docker Compose: `POSTGRES_USER=postgres`, `POSTGRES_PASSWORD=password123`, `CLICKHOUSE_USER=default`, `CLICKHOUSE_PASSWORD=password123`

#### ตัวอย่าง 2: MSSQL + PostgreSQL Metrics

```bash
# Job: DATA_PROFILER_ORDERS_MSSQL
# Application: DataOps
# Sub-Application: Profiling

# Environment Variables (set ใน Control-M):
# Source Database (MSSQL)
MSSQL_HOST=sqlserver.production.internal
MSSQL_PORT=1433
MSSQL_DATABASE=sales_db
MSSQL_USER=profiler_svc
MSSQL_PASSWORD='your_secure_password'
MSSQL_SCHEMA=dbo

# Metrics Storage (PostgreSQL)
METRICS_BACKEND=postgresql
PG_METRICS_HOST=metrics-db.production.internal
PG_METRICS_PORT=5432
PG_METRICS_DATABASE=profiler_metrics
PG_METRICS_USER=metrics_user
PG_METRICS_PASSWORD='your_secure_password'

# Profiler Options
PROFILER_TABLE=orders
PROFILER_DB_TYPE=mssql
PROFILER_APP=sales-service
PROFILER_ENV=production
PROFILER_AUTO_INCREMENT=true
PROFILER_LOOKBACK_DAYS=14

# Command:
/opt/dataprofiler/scripts/run_profiler.sh
```

> **Local Development**: ใช้ค่า default จาก Docker Compose: `MSSQL_USER=sa`, `MSSQL_PASSWORD=YourStrong@Password123`

### Logging

Wrapper script สร้าง log files ใน `$PROFILER_HOME/logs/` ในรูปแบบ:

```
profiler_<CTM_ORDERID>.log
```

Control-M variables `CTM_JOBNAME` และ `CTM_ORDERID` จะถูกใช้อัตโนมัติสำหรับ job identification ใน logs

## 🔄 Workflow

```mermaid
flowchart LR
    A[PostgreSQL] -->|1. Discover Schema| B[DataProfiler]
    B -->|2. Generate SodaCL| C[Soda Core]
    C -->|3. Profile Data| B
    B -->|4. Store Results| D[ClickHouse]
    B -->|5. Auto-Increment Analysis| E[Linear Regression]
    E -->|6. Predict Overflow| D
```

1. **Schema Discovery** - ดึงข้อมูล Column และ Data Type จาก `information_schema`
2. **Template Generation** - สร้าง SodaCL YAML แบบ Dynamic ด้วย Jinja2
3. **Data Profiling** - Soda Core สแกนและเก็บสถิติ
4. **Result Storage** - บันทึกผลลัพธ์ลง ClickHouse table `data_profiles`
5. **Auto-Increment Analysis** - วิเคราะห์ auto-increment columns ด้วย Linear Regression
6. **Overflow Prediction** - ทำนายและบันทึกความเสี่ยงลง `autoincrement_profiles`

## 🐳 Docker Full Stack Environment

โปรเจกต์นี้รองรับการทำงานแบบ Full Stack Containerized สามารถรันระบบทั้งหมด (DBs, Backend, Frontend, Grafana) ได้ด้วยคำสั่งเดียว:

```bash
# Start all services
docker-compose up -d --build
```

### ภาพรวม Services

| Service        | URL / Port            | รายละเอียด                           |
| -------------- | --------------------- | ------------------------------------ |
| **Frontend**   | http://localhost:8080 | Main Data Profiler Dashboard (React) |
| **Grafana**    | http://localhost:3000 | Advanced Visualization (Admin)       |
| **Backend**    | Internal (5001)       | API Service (Flask)                  |
| **ClickHouse** | localhost:8123        | HTTP Interface                       |
| **PostgreSQL** | localhost:5432        | Source Database                      |
| **MSSQL**      | localhost:1433        | Source Database (Azure SQL Edge)     |
| **MySQL**      | localhost:3306        | Source Database                      |

### ข้อมูลการเข้าใช้งาน (Credentials)

- **Grafana**: User: `admin`, Pass: `admin`
- **PostgreSQL**: User: `postgres`, Pass: `password123`
- **MSSQL**: User: `sa`, Pass: `YourStrong@Password123`
- **MySQL**: User: `user`, Pass: `password123`
- **ClickHouse**: User: `default`, Pass: `password123`

### การเริ่มใช้งาน MSSQL (Azure SQL Edge)

MSSQL ใช้ Azure SQL Edge สำหรับ ARM64/M1:

```bash
# Start MSSQL container
docker compose up -d mssql

# รอ ~30 วินาที จากนั้น initialize database
python init-scripts/mssql/init-mssql.py

# ทดสอบ profiler
python main.py users -d mssql --no-store
```

> **หมายเหตุ**: Azure SQL Edge ไม่รัน init scripts อัตโนมัติเหมือน PostgreSQL ต้องใช้ Python script สร้าง database

### ข้อมูลตัวอย่าง & การทดสอบ

Docker จะสร้างข้อมูลตัวอย่าง **100+ records** ใน PostgreSQL ให้อัตโนมัติ (ตาราง `users` และ `products`)

#### สร้างข้อมูลเพิ่มเติม

**สำหรับ PostgreSQL:**

```bash
# เพิ่ม 100 users ใน PostgreSQL
python init-scripts/postgres/generate-postgres-data.py --users 100

# เพิ่ม 50 new products
python init-scripts/postgres/generate-postgres-data.py --products 50 --no-users

# เพิ่มทั้ง users และ products
python init-scripts/postgres/generate-postgres-data.py --users 500 --products 200
```

**สำหรับ MSSQL:**

```bash
# เพิ่ม 100 users ใน MSSQL
python init-scripts/mssql/generate-mssql-data.py --users 100

# เพิ่ม 50 products ใน MSSQL
python init-scripts/mssql/generate-mssql-data.py --products 50 --no-users

# เพิ่มทั้ง users และ products
python init-scripts/mssql/generate-mssql-data.py --users 500 --products 200

# ดูสถิติปัจจุบัน
python init-scripts/mssql/generate-mssql-data.py --stats-only

# สำหรับ MySQL:
# เพิ่ม 100 users ใน MySQL (ระบุ schema: prod, uat, หรือ public)
python init-scripts/mysql/generate-mysql-data.py --schema prod --users 100
```

#### รัน Profiler

```bash
# รัน profiler ภายใน backend container (Production)
docker-compose exec backend python ../main.py users --app order-service --env production --schema prod

# รัน profiler ภายใน backend container (UAT)
docker-compose exec backend python ../main.py users --app order-service --env uat --schema uat

# รันพร้อม auto-increment analysis
docker-compose exec backend python ../main.py users --auto-increment --schema prod
```

### การหยุดการทำงาน

```bash
docker-compose down -v  # หยุดและลบ volumes
```

## 📋 ClickHouse Schema

### ตาราง `data_profiles`

ตารางหลักสำหรับเก็บผลลัพธ์การ profiling:

```sql
CREATE TABLE data_profiles (
    scan_time DateTime DEFAULT now(),
    table_name String,
    column_name String,
    distinct_count Nullable(Int64),
    missing_count Nullable(Int64),
    min Nullable(String),
    max Nullable(String),
    avg Nullable(Float64)
) ENGINE = MergeTree() ORDER BY (scan_time, table_name)
```

### ตาราง `autoincrement_profiles`

ตารางสำหรับเก็บผลการวิเคราะห์ auto-increment overflow:

```sql
CREATE TABLE autoincrement_profiles (
    profiled_at DateTime DEFAULT now(),
    application String,
    environment String,
    table_name String,
    column_name String,
    data_type String,
    current_value Int64,
    max_type_value Int64,
    usage_percentage Float64,
    daily_growth_rate Nullable(Float64),
    days_until_full Nullable(Float64),
    alert_status String
) ENGINE = MergeTree() ORDER BY (profiled_at, table_name, column_name)
```

## 📊 การพัฒนา Dashboard

หากต้องการรัน Dashboard แบบ Manual (ไม่อยู่ใน Docker) เพื่อการพัฒนา:

```bash
# 1. Start Backend API
cd dashboard/backend
python app.py

# 2. Start Frontend
cd dashboard/frontend
npm run dev
# เข้าใช้งานที่ http://localhost:5173
```

### Technology Stack

| Component | Technology         |
| --------- | ------------------ |
| Backend   | Flask + Flask-CORS |
| Frontend  | React + Vite       |
| Styling   | TailwindCSS        |
| Charts    | Recharts           |

### Environment Comparison Dashboard

Dashboard รองรับ **dual-environment comparison** สำหรับเปรียบเทียบ data profiles ระหว่าง environments (เช่น UAT เทียบกับ Production)

![React Environment Comparison Dashboard Screenshot](docs/images/react_environment_comparison_dashboard.png)

#### ฟีเจอร์

- **Dual Environment Selectors**: เลือกสอง environments เพื่อเปรียบเทียบ side-by-side
- **Summary Panel**: แสดง row counts และ profiling timestamps ของทั้งสอง environments
- **Comparison Charts**: กราฟแท่งเปรียบเทียบ Not Null Proportion และ Distinct Proportion
- **Difference Highlighting**: ไฮไลท์ความแตกต่างด้วยสี (เขียว = ดีขึ้น, แดง = แย่ลง)
- **Min/Max Filtering**: แสดง min/max เฉพาะ columns ที่เป็น numeric หรือ date/time
- **Auto-Increment Comparison**: เปรียบเทียบ overflow risk metrics ระหว่าง environments

#### API Endpoints

| Endpoint                                                                   | คำอธิบาย                                          |
| -------------------------------------------------------------------------- | ------------------------------------------------- |
| `GET /api/metadata`                                                        | แสดงรายชื่อ applications และ environments ทั้งหมด |
| `GET /api/profiles/compare/<table>?app=<app>&env1=<env1>&env2=<env2>`      | เปรียบเทียบ profiles ระหว่างสอง environments      |
| `GET /api/autoincrement/compare/<table>?app=<app>&env1=<env1>&env2=<env2>` | เปรียบเทียบ auto-increment metrics                |

### Schema Comparison Dashboard

Dashboard รองรับ **dual-environment schema comparison** สำหรับเปรียบเทียบ table schemas ระหว่าง environments (เช่น UAT เทียบกับ Production)

![React Schema Comparison Dashboard Screenshot](docs/images/react_schema_comparison_dashboard.png)

#### ฟีเจอร์

- **Tab Navigation**: สลับระหว่างมุมมอง Data Profile และ Schema Comparison
- **Summary Cards**: แสดงจำนวน columns ทั้งหมด, ตรงกัน, แตกต่าง, และเฉพาะใน environment
- **Comparison Table**: มุมมอง side-by-side ของ column schemas พร้อม:
  - เปรียบเทียบ Data Type
  - สถานะ Nullable (NULL / NOT NULL)
  - ตัวบ่งชี้ Primary Key (🔑)
  - ตัวบ่งชี้ Index membership (📇)
- **Difference Highlighting**: Status badges แบบสี:
  - ✓ Match (เทา) - Column มีอยู่และตรงกันในทั้งสอง environments
  - ⚠ Modified (เหลือง) - Column มีอยู่แต่มีความแตกต่าง
  - - Added (เขียว) - Column มีเฉพาะใน Environment 2
  - - Removed (แดง) - Column มีเฉพาะใน Environment 1

#### API Endpoints

| Endpoint                                                            | คำอธิบาย                                   |
| ------------------------------------------------------------------- | ------------------------------------------ |
| `GET /api/schema/compare/<table>?app=<app>&env1=<env1>&env2=<env2>` | เปรียบเทียบ schema ระหว่างสอง environments |

#### การใช้งาน

ในการเก็บข้อมูล schema ให้รัน profiler ด้วย `--profile-schema` flag:

```bash
# Profile schema สำหรับ UAT
python main.py users --profile-schema --app user-service --env uat

# Profile schema สำหรับ Production
python main.py users --profile-schema --app user-service --env production
```

## 📈 Grafana Dashboard (ทางเลือกเสริม)

โปรเจกต์นี้มาพร้อมกับ **Grafana** ที่เชื่อมต่อกับ ClickHouse ให้โดยอัตโนมัติ

![Grafana Dashboard](docs/images/grafana_dashboard.png)

### ฟีเจอร์

- **Direct ClickHouse Integration**: เชื่อมต่อโดยตรง ไม่ต้องผ่าน middleware
- **Customizable**: สร้าง Dashboard ที่ซับซ้อนด้วย SQL
- **Alerting**: รองรับระบบแจ้งเตือนของ Grafana
- **User Management**: ระบบจัดการผู้ใช้งาน

### การใช้งาน

Grafana ถูกรวมอยู่ใน `docker-compose.yml` แล้ว:

1. Start services:

   ```bash
   docker-compose up -d
   ```

2. เข้าใช้งาน Grafana:
   - URL: http://localhost:3000
   - User: `admin`
   - Password: `admin`

3. สร้าง Dashboard:
   - DataSource: **ClickHouse** (ถูกตั้งค่าไว้แล้ว)
   - Example Query (Data Profiles):
     ```sql
     SELECT table_name, max(row_count) as rows
     FROM data_profiles
     GROUP BY table_name
     ```
   - Example Query (Auto-Increment Monitoring):
     ```sql
     SELECT
       table_name,
       column_name,
       usage_percentage,
       days_until_full,
       alert_status
     FROM autoincrement_profiles
     ORDER BY profiled_at DESC
     LIMIT 100
     ```

## ⚠️ Limitations

Data Types ที่ไม่รองรับในปัจจุบัน (สำหรับ min/max/avg):

- `timestamp`
- `timestamp without time zone`
- `date`
- `bytea`

## 📝 License

[MIT License](LICENSE)

## 🤝 Contributing

Pull requests ยินดีต้อนรับ! สำหรับการเปลี่ยนแปลงใหญ่ กรุณาเปิด Issue ก่อนเพื่อหารือ
