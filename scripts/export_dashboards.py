
import json
import os
import glob

def sanitize_dashboard(dashboard_json):
    """
    Recursively remove '(PostgreSQL)' and '(ClickHouse)' from string values in the JSON.
    """
    if isinstance(dashboard_json, dict):
        return {k: sanitize_dashboard(v) for k, v in dashboard_json.items()}
    elif isinstance(dashboard_json, list):
        return [sanitize_dashboard(i) for i in dashboard_json]
    elif isinstance(dashboard_json, str):
        # Remove target strings
        sanitized = dashboard_json.replace(" (PostgreSQL)", "").replace(" (ClickHouse)", "")
        sanitized = sanitized.replace("(PostgreSQL)", "").replace("(ClickHouse)", "")
        return sanitized
    else:
        return dashboard_json

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
            sanitized_data = sanitize_dashboard(dashboard_data)
            
            # Modify the UID to be generic if needed, or leave as is? 
            # The prompt didn't specify changing UIDs, but it might be good practice if importing to the same Grafana instance.
            # For now, I'll stick to the specific requirement: removing the backend text.

             # Add a tag or modify title to indicate it is an export? 
            # The prompt just said "export dashboard for import".
            
            output_path = os.path.join(output_dir, filename)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(sanitized_data, f, indent=2, ensure_ascii=False)
                
            print(f"  -> Exported to {output_path}")
            
        except Exception as e:
            print(f"  -> Error processing {filename}: {e}")

    print("\nExport completed.")

if __name__ == "__main__":
    export_dashboards()
