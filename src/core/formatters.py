"""
Output formatters for data profiles.
Supports Markdown, JSON, CSV, and console table formats.
"""

import json
import csv
import io
from typing import Optional
from datetime import datetime

from src.core.metrics import TableProfile, ColumnProfile


def format_markdown(profile: TableProfile) -> str:
    """
    Format profile as Markdown table (dbt-profiler style).
    
    Args:
        profile: TableProfile to format
        
    Returns:
        Markdown formatted string
    """
    lines = []
    lines.append(f"# Data Profile: {profile.table_name}")
    lines.append("")
    lines.append(f"**Profiled at:** {profile.profiled_at.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Row count:** {profile.row_count:,}")
    lines.append("")
    
    # Table header
    headers = [
        "column_name", "data_type", "not_null_proportion", "distinct_proportion",
        "distinct_count", "is_unique", "min", "max", "avg", "median",
        "std_dev_population", "std_dev_sample"
    ]
    
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    
    # Table rows
    for col in profile.column_profiles:
        row = [
            col.column_name,
            col.data_type,
            f"{col.not_null_proportion:.2f}" if col.not_null_proportion is not None else "",
            f"{col.distinct_proportion:.2f}" if col.distinct_proportion is not None else "",
            str(col.distinct_count) if col.distinct_count is not None else "",
            "1" if col.is_unique else "0",
            str(col.min_value) if col.min_value is not None else "",
            str(col.max_value) if col.max_value is not None else "",
            f"{col.avg:.4f}" if col.avg is not None else "",
            f"{col.median:.4f}" if col.median is not None else "",
            f"{col.std_dev_population:.4f}" if col.std_dev_population is not None else "",
            f"{col.std_dev_sample:.4f}" if col.std_dev_sample is not None else "",
        ]
        lines.append("| " + " | ".join(row) + " |")
    
    return "\n".join(lines)


def format_json(profile: TableProfile, pretty: bool = True) -> str:
    """
    Format profile as JSON.
    
    Args:
        profile: TableProfile to format
        pretty: If True, format with indentation
        
    Returns:
        JSON formatted string
    """
    data = {
        "table_name": profile.table_name,
        "row_count": profile.row_count,
        "profiled_at": profile.profiled_at.isoformat(),
        "columns": []
    }
    
    for col in profile.column_profiles:
        col_data = {
            "column_name": col.column_name,
            "data_type": col.data_type,
            "not_null_proportion": col.not_null_proportion,
            "distinct_proportion": col.distinct_proportion,
            "distinct_count": col.distinct_count,
            "is_unique": col.is_unique,
            "min": col.min_value,
            "max": col.max_value,
            "avg": col.avg,
            "median": col.median,
            "std_dev_population": col.std_dev_population,
            "std_dev_sample": col.std_dev_sample,
        }
        data["columns"].append(col_data)
    
    if pretty:
        return json.dumps(data, indent=2, ensure_ascii=False)
    return json.dumps(data, ensure_ascii=False)


def format_csv(profile: TableProfile) -> str:
    """
    Format profile as CSV.
    
    Args:
        profile: TableProfile to format
        
    Returns:
        CSV formatted string
    """
    output = io.StringIO()
    
    fieldnames = [
        "table_name", "column_name", "data_type", "row_count",
        "not_null_proportion", "distinct_proportion", "distinct_count",
        "is_unique", "min", "max", "avg", "median",
        "std_dev_population", "std_dev_sample", "profiled_at"
    ]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for col in profile.column_profiles:
        row = {
            "table_name": col.table_name,
            "column_name": col.column_name,
            "data_type": col.data_type,
            "row_count": col.row_count,
            "not_null_proportion": col.not_null_proportion,
            "distinct_proportion": col.distinct_proportion,
            "distinct_count": col.distinct_count,
            "is_unique": 1 if col.is_unique else 0,
            "min": col.min_value,
            "max": col.max_value,
            "avg": col.avg,
            "median": col.median,
            "std_dev_population": col.std_dev_population,
            "std_dev_sample": col.std_dev_sample,
            "profiled_at": col.profiled_at.isoformat(),
        }
        writer.writerow(row)
    
    return output.getvalue()


def format_table(profile: TableProfile) -> str:
    """
    Format profile as pretty-printed console table.
    
    Args:
        profile: TableProfile to format
        
    Returns:
        Formatted table string for console output
    """
    lines = []
    lines.append(f"\n{'='*80}")
    lines.append(f"  Data Profile: {profile.table_name}")
    lines.append(f"  Profiled at: {profile.profiled_at.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"  Row count: {profile.row_count:,}")
    lines.append(f"{'='*80}\n")
    
    # Column headers
    header = f"{'Column':<20} {'Type':<15} {'Not Null':<10} {'Distinct':<10} {'Unique':<7} {'Min':<12} {'Max':<12}"
    lines.append(header)
    lines.append("-" * len(header))
    
    for col in profile.column_profiles:
        not_null = f"{col.not_null_proportion:.2f}" if col.not_null_proportion else "N/A"
        distinct = f"{col.distinct_proportion:.2f}" if col.distinct_proportion else "N/A"
        unique = "Yes" if col.is_unique else "No"
        min_val = str(col.min_value)[:10] if col.min_value else "N/A"
        max_val = str(col.max_value)[:10] if col.max_value else "N/A"
        
        row = f"{col.column_name:<20} {col.data_type:<15} {not_null:<10} {distinct:<10} {unique:<7} {min_val:<12} {max_val:<12}"
        lines.append(row)
    
    # Numeric columns detail
    numeric_cols = [c for c in profile.column_profiles if c.avg is not None]
    if numeric_cols:
        lines.append(f"\n{'Numeric Column Statistics':-^80}")
        lines.append(f"{'Column':<20} {'Avg':<15} {'Median':<15} {'Std Dev (Pop)':<15} {'Std Dev (Sam)':<15}")
        lines.append("-" * 80)
        
        for col in numeric_cols:
            avg = f"{col.avg:.4f}" if col.avg else "N/A"
            median = f"{col.median:.4f}" if col.median else "N/A"
            std_pop = f"{col.std_dev_population:.4f}" if col.std_dev_population else "N/A"
            std_sam = f"{col.std_dev_sample:.4f}" if col.std_dev_sample else "N/A"
            
            row = f"{col.column_name:<20} {avg:<15} {median:<15} {std_pop:<15} {std_sam:<15}"
            lines.append(row)
    
    lines.append("")
    return "\n".join(lines)


def format_profile(
    profile: TableProfile,
    format_type: str = "table"
) -> str:
    """
    Format profile using specified format type.
    
    Args:
        profile: TableProfile to format
        format_type: One of 'table', 'markdown', 'json', 'csv'
        
    Returns:
        Formatted string
    """
    formatters = {
        "table": format_table,
        "markdown": format_markdown,
        "json": format_json,
        "csv": format_csv,
    }
    
    formatter = formatters.get(format_type.lower())
    if not formatter:
        raise ValueError(f"Unknown format type: {format_type}. Valid options: {list(formatters.keys())}")
    
    return formatter(profile)
