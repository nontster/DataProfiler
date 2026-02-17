
import sys
import os
import oracledb

# Add project root to path
sys.path.append(os.getcwd())

from src.config import Config
from src.db.connection_factory import list_tables

def debug_oracle():
    print(f"Config.ORACLE_USER: {Config.ORACLE_USER}")
    print(f"Config.ORACLE_SCHEMA: {Config.ORACLE_SCHEMA}")
    print(f"Config.ORACLE_HOST: {Config.ORACLE_HOST}")
    print(f"Config.ORACLE_PORT: {Config.ORACLE_PORT}")
    print(f"Config.ORACLE_SERVICE_NAME: {Config.ORACLE_SERVICE_NAME}")
    
    
    # print("\nAttempting connection...")
    # try:
    #     conn = get_oracle_connection()
    #     print("Connection SUCCESS")
    #     conn.close()
    # except Exception as e:
    #     print(f"Connection FAILED: {e}")
    #     return

    print("\nListing tables...")
    try:
        tables = list_tables('oracle')
        print(f"Tables found: {tables}")
    except Exception as e:
        print(f"List tables FAILED: {e}")

if __name__ == "__main__":
    debug_oracle()
