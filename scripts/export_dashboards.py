
import json
import os
import glob

def add_datasource_variable(dashboard_json, filename):
    """
    Add a datasource template variable to the dashboard.
    Determines the datasource type (query) based on the filename suffix.
    """
    
    # Determine datasource type based on filename suffix
    # Default to prometheus as a placeholder if neither matches, or maybe just 'datasource'
    ds_query = "datasource" 
    if filename.endswith("_ch.json"):
        ds_query = "grafana-clickhouse-datasource"
    elif filename.endswith("_pg.json"):
        ds_query = "postgres"
    
    ds_variable = {
        "current": {
            "selected": False,
            "text": "default",
            "value": "default"
        },
        "hide": 0,
        "includeAll": False,
        "label": "Data Source",
        "multi": False,
        "name": "DS_PROFILER_METRICS",
        "options": [],
        "query": ds_query,
        "refresh": 1,
        "regex": "",
        "skipUrlSync": False,
        "type": "datasource"
    }

    if "templating" not in dashboard_json:
        dashboard_json["templating"] = {"list": []}
    
    if "list" not in dashboard_json["templating"]:
        dashboard_json["templating"]["list"] = []

    # Check if variable already exists
    for var in dashboard_json["templating"]["list"]:
        if var.get("name") == "DS_PROFILER_METRICS":
            # Update the query type if it exists but might be wrong? 
            # Better to just update it.
            var["query"] = ds_query
            return dashboard_json

    # Prepend the datasource variable
    dashboard_json["templating"]["list"].insert(0, ds_variable)
    return dashboard_json


def replace_datasource_recursive(data):
    """
    Recursively replace datasource references with the template variable.
    """
    if isinstance(data, dict):
        new_data = {}
        for k, v in data.items():
            if k == "datasource" and isinstance(v, dict) and "uid" in v and v["uid"] != "-- Grafana --":
                 # Replace the datasource object value
                 new_data[k] = {
                     "type": "datasource",
                     "uid": "${DS_PROFILER_METRICS}"
                 }
            elif k == "datasource" and isinstance(v, str) and v != "-- Grafana --" and "${" not in v:
                 # Legacy string data source handling
                 new_data[k] = "${DS_PROFILER_METRICS}"
            else:
                 new_data[k] = replace_datasource_recursive(v)
        return new_data
    elif isinstance(data, list):
        return [replace_datasource_recursive(i) for i in data]
    else:
        return data


def sanitize_dashboard(dashboard_json, filename):
    """
    Process dashboard JSON to:
    1. Sanitize strings (remove backend suffixes).
    2. Inject dynamic datasource variable with type based on filename.
    3. Update datasource references.
    """
    # Helper for string sanitization
    def clean_strings(data):
        if isinstance(data, dict):
            return {k: clean_strings(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [clean_strings(i) for i in data]
        elif isinstance(data, str):
            sanitized = data.replace(" (PostgreSQL)", "").replace(" (ClickHouse)", "")
            sanitized = sanitized.replace("(PostgreSQL)", "").replace("(ClickHouse)", "")
            return sanitized
        else:
            return data

    # 1. Clean strings first
    cleaned_data = clean_strings(dashboard_json)
    
    # 2. Add datasource variable
    with_var = add_datasource_variable(cleaned_data, filename)
    
    # 3. Replace datasource references
    final_data = replace_datasource_recursive(with_var)
    
    return final_data


def export_dashboards():
    source_dir = os.path.join(os.path.dirname(__file__), "../grafana/dashboards")
    output_dir = os.path.join(os.path.dirname(__file__), "../grafana/dashboards_exported")

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Find all JSON files in the source directory
    dashboard_files = glob.glob(os.path.join(source_dir, "*.json"))

    if not dashboard_files:
        print(f"No dashboard files found in {source_dir}")
        return

    print(f"Found {len(dashboard_files)} dashboards to process...")

    for file_path in dashboard_files:
        filename = os.path.basename(file_path)
        print(f"Processing {filename}...")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                dashboard_data = json.load(f)
            
            # Sanitize the dashboard data
            sanitized_data = sanitize_dashboard(dashboard_data, filename)
            
            output_path = os.path.join(output_dir, filename)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(sanitized_data, f, indent=2, ensure_ascii=False)
                
            print(f"  -> Exported to {output_path}")
            
        except Exception as e:
            print(f"  -> Error processing {filename}: {e}")

    print("\nExport completed.")

if __name__ == "__main__":
    export_dashboards()
