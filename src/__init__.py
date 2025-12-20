"""
DataProfiler - Automated Data Profiling Tool
"""

__version__ = "1.0.0"
__author__ = "DataProfiler Team"

from src.core.profiler import run_profiler
from src.config import Config

__all__ = ["run_profiler", "Config"]
