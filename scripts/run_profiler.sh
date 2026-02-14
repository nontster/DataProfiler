#!/bin/bash
#===============================================================================
# Data Profiler Wrapper Script for Control-M
#===============================================================================
# 
# Description:
#   Wrapper script to execute DataProfiler from Control-M scheduling system.
#   All configuration should be passed via environment variables from Control-M.
#
# Required Environment Variables (configure in Control-M):
#   Database Connection:
#     POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DATABASE, POSTGRES_USER, POSTGRES_PASSWORD
#     MSSQL_HOST, MSSQL_PORT, MSSQL_DATABASE, MSSQL_USER, MSSQL_PASSWORD (if using MSSQL)
#     MYSQL_HOST, MYSQL_PORT, MYSQL_DATABASE, MYSQL_USER, MYSQL_PASSWORD (if using MySQL)
#   
#   Metrics Backend (choose one):
#     PG_METRICS_HOST, PG_METRICS_PORT, etc. (primary choice, default)
#     CLICKHOUSE_HOST, CLICKHOUSE_PORT, CLICKHOUSE_USER, CLICKHOUSE_PASSWORD (optional)
#
# Optional Environment Variables:
#   PROFILER_TABLE        - Comma-separated table names (required with --data-profile)
#   PROFILER_FORMAT       - Output format: table|markdown|json|csv (default: table)
#   PROFILER_OUTPUT_FILE  - File path to save output (optional)
#   PROFILER_APP          - Application name (default: default)
#   PROFILER_ENV          - Environment name (default: production)
#   PROFILER_DB_TYPE      - Database type: postgresql|mssql|mysql (default: postgresql)
#   METRICS_BACKEND       - Metrics backend: postgresql|clickhouse (default: postgresql)
#   PROFILER_DATA_PROFILE   - Enable data profiling: true|false (default: false)
#   PROFILER_AUTO_INCREMENT - Enable auto-increment analysis: true|false (default: false)
#   PROFILER_PROFILE_SCHEMA - Enable schema profiling: true|false (default: false)
#   PROFILER_LOOKBACK_DAYS  - Days for growth rate calculation (default: 7)
#   PROFILER_NO_STORE       - Skip storing to metrics backend: true|false (default: false)
#   PROFILER_VERBOSE        - Enable verbose logging: true|false (default: false)
#   PYTHON_PATH             - Path to Python executable (default: python3)
#   PROFILER_HOME           - Path to DataProfiler installation (default: script location)
#
# Exit Codes:
#   0 - Success
#   1 - Configuration error (missing required env vars)
#   2 - Execution error (profiler failed)
#   3 - Python environment error
#
# Usage in Control-M:
#   Set environment variables in the job definition, then execute this script.
#
#===============================================================================

set -o pipefail

# ============================================================================
# Configuration
# ============================================================================

# Determine script and project directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROFILER_HOME="${PROFILER_HOME:-$(dirname "$SCRIPT_DIR")}"

# Python configuration
PYTHON_PATH="${PYTHON_PATH:-python3}"

# Job identification for logging
JOB_NAME="${CTM_JOBNAME:-DataProfiler}"
JOB_ID="${CTM_ORDERID:-$(date +%Y%m%d%H%M%S)}"

# Log file (can be overridden)
LOG_DIR="${PROFILER_HOME}/logs"
LOG_FILE="${LOG_FILE:-${LOG_DIR}/profiler_${JOB_ID}.log}"

# ============================================================================
# Logging Functions
# ============================================================================

log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] [${level}] [${JOB_NAME}:${JOB_ID}] ${message}" | tee -a "${LOG_FILE}"
}

log_info() {
    log "INFO" "$1"
}

log_warn() {
    log "WARN" "$1"
}

log_error() {
    log "ERROR" "$1"
}

log_debug() {
    if [[ "${PROFILER_VERBOSE}" == "true" ]]; then
        log "DEBUG" "$1"
    fi
}

# ============================================================================
# Validation Functions
# ============================================================================

validate_env_var() {
    local var_name="$1"
    local var_value="${!var_name}"
    
    if [[ -z "$var_value" ]]; then
        log_error "Required environment variable '${var_name}' is not set"
        return 1
    fi
    log_debug "Validated: ${var_name}=***"
    return 0
}

validate_database_config() {
    local db_type="${PROFILER_DB_TYPE:-postgresql}"
    local errors=0
    
    log_info "Validating database configuration for type: ${db_type}"
    
    if [[ "$db_type" == "postgresql" ]]; then
        validate_env_var "POSTGRES_HOST" || ((errors++))
        validate_env_var "POSTGRES_PORT" || ((errors++))
        validate_env_var "POSTGRES_DATABASE" || ((errors++))
        validate_env_var "POSTGRES_USER" || ((errors++))
        validate_env_var "POSTGRES_PASSWORD" || ((errors++))
    elif [[ "$db_type" == "mssql" ]]; then
        validate_env_var "MSSQL_HOST" || ((errors++))
        validate_env_var "MSSQL_PORT" || ((errors++))
        validate_env_var "MSSQL_DATABASE" || ((errors++))
        validate_env_var "MSSQL_USER" || ((errors++))
        validate_env_var "MSSQL_PASSWORD" || ((errors++))
    elif [[ "$db_type" == "mysql" ]]; then
        validate_env_var "MYSQL_HOST" || ((errors++))
        validate_env_var "MYSQL_PORT" || ((errors++))
        validate_env_var "MYSQL_DATABASE" || ((errors++))
        validate_env_var "MYSQL_USER" || ((errors++))
        validate_env_var "MYSQL_PASSWORD" || ((errors++))
    else
        log_error "Invalid database type: ${db_type}. Must be 'postgresql', 'mssql', or 'mysql'"
        return 1
    fi
    
    return $errors
}

validate_metrics_config() {
    local backend="${METRICS_BACKEND:-postgresql}"
    local db_type="${PROFILER_DB_TYPE:-postgresql}"
    local errors=0
    
    # Skip validation if not storing metrics
    if [[ "${PROFILER_NO_STORE}" == "true" ]]; then
        log_info "Metrics storage disabled, skipping backend validation"
        return 0
    fi
    
    log_info "Validating metrics backend configuration: ${backend}"
    
    if [[ "$backend" == "clickhouse" ]]; then
        validate_env_var "CLICKHOUSE_HOST" || ((errors++))
        validate_env_var "CLICKHOUSE_PORT" || ((errors++))
    elif [[ "$backend" == "postgresql" ]]; then
        # PostgreSQL metrics can use same credentials as source DB or separate
        if [[ -n "${PG_METRICS_HOST}" ]]; then
            # Use dedicated PG_METRICS_* variables
            validate_env_var "PG_METRICS_HOST" || ((errors++))
            validate_env_var "PG_METRICS_PORT" || ((errors++))
            validate_env_var "PG_METRICS_DATABASE" || ((errors++))
            validate_env_var "PG_METRICS_USER" || ((errors++))
            validate_env_var "PG_METRICS_PASSWORD" || ((errors++))
        elif [[ "$db_type" == "postgresql" ]]; then
            # Fallback to source PostgreSQL connection (only valid when source is PostgreSQL)
            log_info "Using source PostgreSQL connection for metrics storage"
            validate_env_var "POSTGRES_HOST" || ((errors++))
            validate_env_var "POSTGRES_PORT" || ((errors++))
        else
            # Source is MSSQL but PG_METRICS_* not set - error
            log_error "When using MSSQL as source database, you must configure PG_METRICS_* variables for PostgreSQL metrics storage"
            log_error "Required: PG_METRICS_HOST, PG_METRICS_PORT, PG_METRICS_DATABASE, PG_METRICS_USER, PG_METRICS_PASSWORD"
            return 1
        fi
    else
        log_error "Invalid metrics backend: ${backend}. Must be 'clickhouse' or 'postgresql'"
        return 1
    fi
    
    return $errors
}

validate_python_env() {
    log_info "Validating Python environment..."
    
    # Check if Python is available
    if ! command -v "${PYTHON_PATH}" &> /dev/null; then
        log_error "Python not found at: ${PYTHON_PATH}"
        return 1
    fi
    
    local python_version=$("${PYTHON_PATH}" --version 2>&1)
    log_info "Python version: ${python_version}"
    
    # Check if main.py exists
    if [[ ! -f "${PROFILER_HOME}/main.py" ]]; then
        log_error "main.py not found in: ${PROFILER_HOME}"
        return 1
    fi
    
    # Check if virtual environment exists and activate it
    if [[ -d "${PROFILER_HOME}/venv" ]]; then
        log_info "Activating virtual environment..."
        source "${PROFILER_HOME}/venv/bin/activate"
        PYTHON_PATH="python"
    fi
    
    log_info "Python environment validated successfully"
    return 0
}

# ============================================================================
# CLI Argument Parsing (for validation purposes)
# ============================================================================

# Extract CLI arguments that affect validation
parse_cli_args() {
    # Reset variables that CLI args can override
    CLI_METRICS_BACKEND=""
    CLI_DATABASE_TYPE=""
    CLI_NO_STORE="false"
    CLI_TABLE=""
    CLI_APP=""
    CLI_ENV=""
    CLI_SCHEMA=""
    CLI_AUTO_INCREMENT="false"
    CLI_DATA_PROFILE="false"
    CLI_LOOKBACK_DAYS=""
    
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --table|-t)
                CLI_TABLE="$2"
                shift 2
                ;;
            --metrics-backend|-m)
                CLI_METRICS_BACKEND="$2"
                shift 2
                ;;
            --database-type|-d)
                CLI_DATABASE_TYPE="$2"
                shift 2
                ;;
            --app)
                CLI_APP="$2"
                shift 2
                ;;
            --env)
                CLI_ENV="$2"
                shift 2
                ;;
            --schema)
                CLI_SCHEMA="$2"
                shift 2
                ;;
            --auto-increment)
                CLI_AUTO_INCREMENT="true"
                shift
                ;;
            --data-profile)
                CLI_DATA_PROFILE="true"
                shift
                ;;
            --profile-schema)
                CLI_PROFILE_SCHEMA="true"
                shift
                ;;
            --lookback-days)
                CLI_LOOKBACK_DAYS="$2"
                shift 2
                ;;
            --no-store)
                CLI_NO_STORE="true"
                shift
                ;;
            --*|-*)
                # Skip other options with value
                if [[ $# -gt 1 && ! "$2" =~ ^- ]]; then
                    shift 2
                else
                    shift
                fi
                ;;
            *)
                # Unknown positional argument, skip
                shift
                ;;
        esac
    done
    
    # Apply CLI overrides to validation variables
    if [[ -n "$CLI_METRICS_BACKEND" ]]; then
        METRICS_BACKEND="$CLI_METRICS_BACKEND"
    fi
    if [[ -n "$CLI_DATABASE_TYPE" ]]; then
        PROFILER_DB_TYPE="$CLI_DATABASE_TYPE"
    fi
    if [[ "$CLI_NO_STORE" == "true" ]]; then
        PROFILER_NO_STORE="true"
    fi
    if [[ -n "$CLI_TABLE" ]]; then
        PROFILER_TABLE="$CLI_TABLE"
    fi
    if [[ -n "$CLI_APP" ]]; then
        PROFILER_APP="$CLI_APP"
    fi
    if [[ -n "$CLI_ENV" ]]; then
        PROFILER_ENV="$CLI_ENV"
    fi
    if [[ -n "$CLI_SCHEMA" ]]; then
        PROFILER_SCHEMA="$CLI_SCHEMA"
    fi
    if [[ "$CLI_AUTO_INCREMENT" == "true" ]]; then
        PROFILER_AUTO_INCREMENT="true"
    fi
    if [[ "$CLI_DATA_PROFILE" == "true" ]]; then
        PROFILER_DATA_PROFILE="true"
    fi
    if [[ "$CLI_PROFILE_SCHEMA" == "true" ]]; then
        PROFILER_PROFILE_SCHEMA="true"
    fi
    if [[ -n "$CLI_LOOKBACK_DAYS" ]]; then
        PROFILER_LOOKBACK_DAYS="$CLI_LOOKBACK_DAYS"
    fi
}

# ============================================================================
# Main Execution
# ============================================================================

build_command_args() {
    local args=()
    
    # Table name (required named argument)
    if [[ -n "${PROFILER_TABLE}" ]]; then
        args+=("--table" "${PROFILER_TABLE}")
    fi
    
    # Output format
    if [[ -n "${PROFILER_FORMAT}" ]]; then
        args+=("--format" "${PROFILER_FORMAT}")
    fi
    
    # Output file
    if [[ -n "${PROFILER_OUTPUT_FILE}" ]]; then
        args+=("--output" "${PROFILER_OUTPUT_FILE}")
    fi
    
    # Application name
    if [[ -n "${PROFILER_APP}" ]]; then
        args+=("--app" "${PROFILER_APP}")
    fi
    
    # Environment name
    if [[ -n "${PROFILER_ENV}" ]]; then
        args+=("--env" "${PROFILER_ENV}")
    fi
    
    # Database type
    if [[ -n "${PROFILER_DB_TYPE}" ]]; then
        args+=("--database-type" "${PROFILER_DB_TYPE}")
    fi
    
    # Metrics backend
    if [[ -n "${METRICS_BACKEND}" ]]; then
        args+=("--metrics-backend" "${METRICS_BACKEND}")
    fi
    
    # Schema name
    if [[ -n "${PROFILER_SCHEMA}" ]]; then
        args+=("--schema" "${PROFILER_SCHEMA}")
    fi
    
    # Auto-increment analysis
    if [[ "${PROFILER_AUTO_INCREMENT}" == "true" ]]; then
        args+=("--auto-increment")
    fi
    
    # Schema profiling
    if [[ "${PROFILER_PROFILE_SCHEMA}" == "true" ]]; then
        args+=("--profile-schema")
    fi
    
    # Lookback days
    if [[ -n "${PROFILER_LOOKBACK_DAYS}" ]]; then
        args+=("--lookback-days" "${PROFILER_LOOKBACK_DAYS}")
    fi
    
    # No store flag
    if [[ "${PROFILER_NO_STORE}" == "true" ]]; then
        args+=("--no-store")
    fi
    
    # Verbose logging
    if [[ "${PROFILER_VERBOSE}" == "true" ]]; then
        args+=("--verbose")
    fi
    
    # Data profiling
    if [[ "${PROFILER_DATA_PROFILE}" == "true" ]]; then
        args+=("--data-profile")
    fi
    
    echo "${args[@]}"
}

main() {
    # Handle --help / -h before any validation
    for arg in "$@"; do
        if [[ "$arg" == "-h" || "$arg" == "--help" ]]; then
            cd "${PROFILER_HOME}" || exit 1
            # Activate virtual environment if exists
            if [[ -d "${PROFILER_HOME}/venv" ]]; then
                source "${PROFILER_HOME}/venv/bin/activate"
                PYTHON_PATH="python"
            fi
            "${PYTHON_PATH}" main.py --help
            exit 0
        fi
    done
    
    # Create log directory if needed
    mkdir -p "${LOG_DIR}"
    
    log_info "=========================================="
    log_info "DataProfiler Execution Started"
    log_info "=========================================="
    log_info "PROFILER_HOME: ${PROFILER_HOME}"
    log_info "Job Name: ${JOB_NAME}"
    log_info "Job ID: ${JOB_ID}"
    
    # Print Control-M context if available
    if [[ -n "${CTM_JOBNAME}" ]]; then
        log_info "Control-M Job: ${CTM_JOBNAME}"
        log_info "Control-M Order ID: ${CTM_ORDERID:-N/A}"
        log_info "Control-M Run Counter: ${CTM_RUN_COUNTER:-N/A}"
    fi
    
    # Parse CLI arguments to override environment variables for validation
    parse_cli_args "$@"
    
    # Validate table name is provided when needed
    local needs_table="false"
    if [[ "${PROFILER_DATA_PROFILE}" == "true" || "${PROFILER_PROFILE_SCHEMA}" == "true" || "${PROFILER_AUTO_INCREMENT}" == "true" ]]; then
        needs_table="true"
    fi
    
    if [[ "${needs_table}" == "true" && -z "${PROFILER_TABLE}" ]]; then
        log_error "Table name is required when using --data-profile, --profile-schema, or --auto-increment"
        log_error "Set PROFILER_TABLE environment variable or pass --table/-t argument"
        exit 1
    fi
    
    # Validate --auto-increment requires --data-profile
    if [[ "${PROFILER_AUTO_INCREMENT}" == "true" && "${PROFILER_DATA_PROFILE}" != "true" ]]; then
        log_error "--auto-increment requires --data-profile"
        exit 1
    fi
    
    log_info "Effective config - DB Type: ${PROFILER_DB_TYPE:-postgresql}, Metrics Backend: ${METRICS_BACKEND:-postgresql}, Table: ${PROFILER_TABLE:-'(inventory only)'}"
    
    # Step 1: Validate Python environment
    if ! validate_python_env; then
        log_error "Python environment validation failed"
        exit 3
    fi
    
    # Step 2: Validate database configuration
    if ! validate_database_config; then
        log_error "Database configuration validation failed"
        exit 1
    fi
    
    # Step 3: Validate metrics configuration
    if ! validate_metrics_config; then
        log_error "Metrics backend configuration validation failed"
        exit 1
    fi
    
    # Step 4: Build command arguments
    local cmd_args=$(build_command_args)
    log_info "Executing: ${PYTHON_PATH} main.py ${cmd_args}"
    
    # Step 5: Change to project directory and execute
    cd "${PROFILER_HOME}" || {
        log_error "Failed to change directory to ${PROFILER_HOME}"
        exit 2
    }
    
    # Execute the profiler
    local start_time=$(date +%s)
    
    "${PYTHON_PATH}" main.py ${cmd_args} 2>&1 | while IFS= read -r line; do
        echo "[PROFILER] ${line}" | tee -a "${LOG_FILE}"
    done
    
    local exit_code=${PIPESTATUS[0]}
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log_info "=========================================="
    log_info "Execution completed in ${duration} seconds"
    log_info "Exit code: ${exit_code}"
    log_info "=========================================="
    
    if [[ ${exit_code} -ne 0 ]]; then
        log_error "DataProfiler execution failed with exit code: ${exit_code}"
        exit 2
    fi
    
    log_info "DataProfiler execution completed successfully"
    exit 0
}

# Execute main function
main "$@"
