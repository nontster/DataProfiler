
import sys
import os
import oracledb

# Add project root to path
sys.path.append(os.getcwd())

from src.config import Config

def check_system():
    print(f"Connecting to {Config.ORACLE_HOST}:{Config.ORACLE_PORT}/{Config.ORACLE_SERVICE_NAME} as SYSTEM...")
    try:
        params = oracledb.ConnectParams(
            host=Config.ORACLE_HOST,
            port=Config.ORACLE_PORT,
            service_name=Config.ORACLE_SERVICE_NAME
        )
        conn = oracledb.connect(
            user="SYSTEM",
            password=Config.ORACLE_PASSWORD,
            params=params
        )
        print("SUCCESS: Connected as SYSTEM")
        
        cursor = conn.cursor()
        
        # Check users
        print("Checking users...")
        cursor.execute("SELECT username FROM all_users WHERE username = :1", ('USER',)) # Config.ORACLE_USER default is 'user' -> 'USER' in DB
        row = cursor.fetchone()
        # Check users again (case insensitive search usually finds USER)
        print("Checking users...")
        cursor.execute("SELECT username FROM all_users WHERE username = :1", ('USER',)) 
        row = cursor.fetchone()
        
        # Helper to run ignoring errors
        def run_ignore_error(sql):
            try:
                cursor.execute(sql)
            except Exception as e:
                print(f"Ignored error: {e}")

        if row:
             print(f"User USER exists. Dropping to recreate to be sure of password...")
             run_ignore_error("DROP USER \"user\" CASCADE") # Drop lowercase if exists
             run_ignore_error("DROP USER USER CASCADE")     # Drop uppercase if exists
        
        print("Creating user USER (standard)...")
        try:
            # Create user (standard uppercase by default without quotes)
            cursor.execute("CREATE USER user IDENTIFIED BY \"password123\"")
            # Note: password is case sensitive usually if quoted, or depends on DB version.
            # But let's use quotes for password to be sure.
            # User is usually USER unquoted.
            # Wait, 'user' is a reserved word in some contexts? No.
            # To be safe, let's just use what worked but without quotes for username if possible, 
            # OR just use "USER" explicitly.
            
            # Actually, `CREATE USER USER ...` might fail if USER is reserved.
            # But the env var is `user`. 
            # Let's try `CREATE USER "USER" ...` to be explicit upper case.
        except Exception as e:
            # If failed, maybe it's because of quotes. Try unquoted.
            print(f"Failed to create with quotes, trying without: {e}")
            try:
                cursor.execute("CREATE USER user IDENTIFIED BY \"password123\"")
            except Exception as e2:
                 print(f"Failed unquoted too: {e2}")
                 # Maybe use a different name if 'user' is reserved?
                 # But config uses 'user'.
                 pass

        # Try to ensure we have a valid user
        try:
             # Force creation of "USER" (uppercase)
             run_ignore_error("CREATE USER \"USER\" IDENTIFIED BY \"password123\"")
             run_ignore_error("GRANT CONNECT, RESOURCE TO \"USER\"")
             run_ignore_error("GRANT UNLIMITED TABLESPACE TO \"USER\"")
             print("User 'USER' (uppercase) created/granted.")
        except Exception as e:
             print(f"Error creating USER: {e}")

        cursor.close()
        conn.close()
        return True
    except oracledb.Error as e:
        print(f"FAILED: {e}")
        return False

if __name__ == "__main__":
    if check_system():
        sys.exit(0)
    else:
        sys.exit(1)
