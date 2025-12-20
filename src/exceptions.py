"""
Custom exceptions for DataProfiler.
"""


class DataProfilerError(Exception):
    """Base exception for DataProfiler."""
    pass


class DatabaseConnectionError(DataProfilerError):
    """Exception raised when database connection fails."""
    pass


class TableNotFoundError(DataProfilerError):
    """Exception raised when table doesn't exist."""
    pass


class ProfilingError(DataProfilerError):
    """Exception raised when profiling fails."""
    pass
