#!/usr/bin/env python3
"""
DataProfiler - Automated Data Profiling Tool

Main entry point for running data profiling from command line.
"""

import sys
import logging

from src.config import Config
from src.core.profiler import run_profiler

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for the DataProfiler."""
    # Validate configuration
    Config.validate()
    
    # Get table name from command line or use default
    if len(sys.argv) > 1:
        target_table = sys.argv[1]
    else:
        target_table = "users"
        logger.info(f"No table specified, using default: '{target_table}'")
    
    # Run the profiler
    result = run_profiler(target_table)
    
    if result is None:
        logger.error("Profiling failed")
        sys.exit(1)
    elif result == 0:
        logger.warning("No profiles were generated")
        sys.exit(0)
    else:
        logger.info(f"Profiling completed successfully: {result} columns profiled")
        sys.exit(0)


if __name__ == "__main__":
    main()
