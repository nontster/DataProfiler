#!/bin/bash
#===============================================================================
# DataProfiler Deployment Package Creator
#===============================================================================
# Creates a minimal package for deploying DataProfiler to Control-M servers
#
# Usage: ./scripts/create_package.sh [output_dir]
#===============================================================================

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
OUTPUT_DIR="${1:-${PROJECT_ROOT}/dist}"
PACKAGE_NAME="dataprofiler-$(date +%Y%m%d)"

echo "=============================================="
echo "DataProfiler Deployment Package Creator"
echo "=============================================="
echo ""

# Create output directory
mkdir -p "${OUTPUT_DIR}/${PACKAGE_NAME}"
DEST="${OUTPUT_DIR}/${PACKAGE_NAME}"

echo "📦 Creating package: ${PACKAGE_NAME}"
echo "📁 Destination: ${DEST}"
echo ""

# Copy required files
echo "📋 Copying required files..."

# 1. Main entry point
cp "${PROJECT_ROOT}/main.py" "${DEST}/"
echo "   ✓ main.py"

# 2. Source code
cp -r "${PROJECT_ROOT}/src" "${DEST}/"
echo "   ✓ src/"

# 3. Scripts
mkdir -p "${DEST}/scripts"
cp "${PROJECT_ROOT}/scripts/run_profiler.sh" "${DEST}/scripts/"
chmod +x "${DEST}/scripts/run_profiler.sh"
echo "   ✓ scripts/run_profiler.sh"

# 4. Requirements
cp "${PROJECT_ROOT}/requirements.txt" "${DEST}/"
echo "   ✓ requirements.txt"

# 5. Environment template
cp "${PROJECT_ROOT}/.env.example" "${DEST}/"
echo "   ✓ .env.example"

# 6. Create logs directory
mkdir -p "${DEST}/logs"
echo "   ✓ logs/"

# 7. Create installation script
cat > "${DEST}/install.sh" << 'EOF'
#!/bin/bash
#===============================================================================
# DataProfiler Installation Script
#===============================================================================
# Run this script on the Control-M server to set up the environment
#
# Prerequisites:
#   - Python 3.10+
#   - pip
#   - Access to PyPI (or internal mirror)
#===============================================================================

set -e

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=============================================="
echo "DataProfiler Installation"
echo "=============================================="
echo "Install directory: ${INSTALL_DIR}"
echo ""

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: ${PYTHON_VERSION}"

# Create virtual environment
echo ""
echo "📦 Creating virtual environment..."
python3 -m venv "${INSTALL_DIR}/venv"

# Activate and install dependencies
echo "📦 Installing dependencies..."
source "${INSTALL_DIR}/venv/bin/activate"
pip install --upgrade pip
pip install -r "${INSTALL_DIR}/requirements.txt"

echo ""
echo "=============================================="
echo "✅ Installation complete!"
echo "=============================================="
echo ""
echo "Next steps:"
echo "1. Copy .env.example to .env and configure:"
echo "   cp ${INSTALL_DIR}/.env.example ${INSTALL_DIR}/.env"
echo ""
echo "2. Edit .env with your database credentials"
echo ""
echo "3. Test the profiler:"
echo "   ${INSTALL_DIR}/scripts/run_profiler.sh --help"
echo ""
echo "4. Configure Control-M job with environment variables"
echo "   (see README.md for details)"
echo ""
EOF
chmod +x "${DEST}/install.sh"
echo "   ✓ install.sh (installation script)"

# 8. Create a simple README for the package
cat > "${DEST}/DEPLOYMENT.md" << 'EOF'
# DataProfiler Deployment Package

## Quick Start

1. **Extract package** to target server (e.g., `/opt/dataprofiler`)

2. **Run installation script**:
   ```bash
   cd /opt/dataprofiler
   ./install.sh
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

4. **Test**:
   ```bash
   ./scripts/run_profiler.sh --help
   ```

## Control-M Configuration

Set these environment variables in your Control-M job:

### Database Connection (choose one)
```bash
# PostgreSQL
POSTGRES_HOST=your_host
POSTGRES_PORT=5432
POSTGRES_DATABASE=your_db
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password

# OR MSSQL
MSSQL_HOST=your_host
MSSQL_PORT=1433
MSSQL_DATABASE=your_db
MSSQL_USER=your_user
MSSQL_PASSWORD=your_password
```

### Metrics Backend
```bash
# ClickHouse (default)
CLICKHOUSE_HOST=your_host
CLICKHOUSE_PORT=8123
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=your_password

# OR PostgreSQL
METRICS_BACKEND=postgresql
PG_METRICS_HOST=your_host
PG_METRICS_PORT=5432
PG_METRICS_DATABASE=your_db
PG_METRICS_USER=your_user
PG_METRICS_PASSWORD=your_password
```

### Profiler Options
```bash
PROFILER_TABLE=users
PROFILER_DB_TYPE=mssql          # or postgresql
PROFILER_APP=user-service
PROFILER_ENV=production
PROFILER_AUTO_INCREMENT=true
```

### Command
```bash
/opt/dataprofiler/scripts/run_profiler.sh
```

## Exit Codes

| Code | Description |
|------|-------------|
| 0 | Success |
| 1 | Configuration error |
| 2 | Execution error |
| 3 | Python environment error |

## Logs

Logs are written to: `<PROFILER_HOME>/logs/profiler_<JOB_ID>.log`
EOF
echo "   ✓ DEPLOYMENT.md"

# Create tarball
echo ""
echo "📦 Creating tarball..."
cd "${OUTPUT_DIR}"
tar -czvf "${PACKAGE_NAME}.tar.gz" "${PACKAGE_NAME}"
echo ""

# Summary
echo "=============================================="
echo "✅ Package created successfully!"
echo "=============================================="
echo ""
echo "Package location:"
echo "  📁 Directory: ${DEST}"
echo "  📦 Tarball:   ${OUTPUT_DIR}/${PACKAGE_NAME}.tar.gz"
echo ""
echo "Package contents:"
du -sh "${DEST}"/*
echo ""
echo "To deploy:"
echo "  1. Copy ${OUTPUT_DIR}/${PACKAGE_NAME}.tar.gz to target server"
echo "  2. Extract: tar -xzvf ${PACKAGE_NAME}.tar.gz"
echo "  3. Run: cd ${PACKAGE_NAME} && ./install.sh"
echo ""
