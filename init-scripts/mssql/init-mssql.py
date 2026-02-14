#!/usr/bin/env python3
"""
Initialize MSSQL database with test data.
Usage: python init-scripts/mssql/init-mssql.py
"""

import time
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    import pymssql
except ImportError:
    print("❌ pymssql not installed. Run: pip install pymssql")
    sys.exit(1)

# Configuration
MSSQL_HOST = os.getenv('MSSQL_HOST', 'localhost')
MSSQL_PORT = int(os.getenv('MSSQL_PORT', 1433))
MSSQL_USER = os.getenv('MSSQL_USER', 'sa')
MSSQL_PASSWORD = os.getenv('MSSQL_PASSWORD', 'YourStrong@Password123')


def wait_for_mssql(max_retries=30, delay=2):
    """Wait for MSSQL to be ready."""
    print(f"Waiting for MSSQL at {MSSQL_HOST}:{MSSQL_PORT}...")
    
    for i in range(max_retries):
        try:
            conn = pymssql.connect(
                server=MSSQL_HOST,
                port=MSSQL_PORT,
                user=MSSQL_USER,
                password=MSSQL_PASSWORD,
                database='master',
                login_timeout=5
            )
            conn.close()
            print(f"✅ MSSQL is ready! (attempt {i+1})")
            return True
        except pymssql.Error as e:
            print(f"   Attempt {i+1}/{max_retries}: {e}")
            time.sleep(delay)
    
    print("❌ MSSQL is not ready after maximum retries")
    return False


def run_sql(sql, database='master'):
    """Execute SQL statement."""
    conn = pymssql.connect(
        server=MSSQL_HOST,
        port=MSSQL_PORT,
        user=MSSQL_USER,
        password=MSSQL_PASSWORD,
        database=database,
        autocommit=True
    )
    cursor = conn.cursor()
    cursor.execute(sql)
    conn.close()


def main():
    if not wait_for_mssql():
        sys.exit(1)
    
    print("\n📦 Creating testdb database...")
    run_sql("""
        IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'testdb')
        BEGIN
            CREATE DATABASE testdb;
        END
    """)
    print("   ✅ testdb created")
    
    print("\n📦 Creating schemas...")
    run_sql("""
        IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'prod')
        BEGIN
            EXEC('CREATE SCHEMA prod')
        END
        
        IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'uat')
        BEGIN
            EXEC('CREATE SCHEMA uat')
        END
    """, database='testdb')
    print("   ✅ schemas 'prod' and 'uat' created")
    
    
    # ==========================================
    # 1. Production Environment (Golden Schema)
    # ==========================================
    print("\n📋 Creating prod.users (Production) table...")
    run_sql("""
        IF NOT EXISTS (SELECT * FROM sys.tables t JOIN sys.schemas s ON t.schema_id = s.schema_id WHERE t.name = 'users' AND s.name = 'prod')
        BEGIN
            CREATE TABLE prod.users (
                id INT IDENTITY(1,1) PRIMARY KEY,
                username NVARCHAR(50) NOT NULL,
                email NVARCHAR(100) NOT NULL,
                age INT,
                salary DECIMAL(10,2),
                is_active BIT DEFAULT 1,
                created_at DATETIME2 DEFAULT GETDATE()
            );
            
            -- Production Indexes
            CREATE INDEX idx_users_username ON prod.users(username);
            CREATE INDEX idx_users_age_salary ON prod.users(age, salary);
            CREATE UNIQUE INDEX idx_users_email ON prod.users(email);

            -- Insert sample data (99 records)
             INSERT INTO prod.users (username, email, age, salary, is_active) VALUES
                ('john_doe', 'john@company.com', 35, 75000.00, 1),
                ('jane_smith', 'jane@company.com', 42, 92000.00, 1),
                ('bob_wilson', 'bob@company.com', 51, 105000.00, 1),
                ('alice_johnson', 'alice@company.com', 38, 82000.00, 1),
                ('charlie_brown', 'charlie@company.com', 45, 98000.00, 1),
                ('diana_prince', 'diana@company.com', 39, NULL, 1),
                ('edward_stark', 'edward@company.com', 55, 130000.00, 1),
                ('fiona_green', 'fiona@company.com', 33, 68000.00, 1),
                ('george_lucas', 'george@company.com', 48, 115000.00, 1),
                ('hannah_montana', 'hannah@company.com', 29, 58000.00, 1),
                ('ivan_petrov', 'ivan@company.com', 44, 88000.00, 1),
                ('julia_roberts', 'julia@company.com', 41, 95000.00, 1),
                ('kevin_hart', 'kevin@company.com', 36, 72000.00, 0),
                ('laura_palmer', 'laura@company.com', 32, 64000.00, 1),
                ('mike_tyson', 'mike@company.com', 50, 108000.00, 1),
                ('nancy_drew', 'nancy@company.com', 28, 55000.00, 1),
                ('oscar_wilde', 'oscar@company.com', 46, 99000.00, 0),
                ('paula_abdul', 'paula@company.com', 43, 86000.00, 1),
                ('quentin_beck', 'quentin@company.com', 37, 76000.00, 1),
                ('rachel_green', 'rachel@company.com', 34, 70000.00, 1),
                ('steve_rogers', 'steve@company.com', 40, 91000.00, 1),
                ('tina_turner', 'tina@company.com', 47, 102000.00, 0),
                ('ulrich_stern', 'ulrich@company.com', 39, 79000.00, 1),
                ('victoria_secret', 'victoria@company.com', 36, 74000.00, 1),
                ('walter_white', 'walter@company.com', 52, 125000.00, 1),
                ('xena_warrior', 'xena@company.com', 33, 66000.00, 0),
                ('yuri_gagarin', 'yuri@company.com', 45, 97000.00, 1),
                ('zara_larsson', 'zara@company.com', 27, 52000.00, 1),
                ('adam_levine', 'adam@company.com', 41, 93000.00, 1),
                ('betty_white', 'betty@company.com', 58, 115000.00, 1),
                ('carl_sagan', 'carl@company.com', 49, 106000.00, 0),
                ('debbie_harry', 'debbie@company.com', 38, 82000.00, 1),
                ('elvis_presley', 'elvis@company.com', 44, NULL, 1),
                ('frank_sinatra', 'frank@company.com', 53, 132000.00, 1),
                ('greta_thunberg', 'greta@company.com', 25, 48000.00, 1),
                ('henry_ford', 'henry@company.com', 57, 148000.00, 0),
                ('iris_west', 'iris@company.com', 31, 62000.00, 1),
                ('james_bond', 'james@company.com', 46, 118000.00, 1),
                ('kate_middleton', 'kate@company.com', 40, 95000.00, 1),
                ('leonardo_dicaprio', 'leonardo@company.com', 48, 140000.00, 1),
                ('madonna_ciccone', 'madonna@company.com', 54, 112000.00, 0),
                ('neil_armstrong', 'neil@company.com', NULL, 105000.00, 1),
                ('oprah_winfrey', 'oprah@company.com', 59, 185000.00, 1),
                ('peter_parker', 'peter@company.com', 26, 54000.00, 1),
                ('queen_elizabeth', 'queen@company.com', 65, 210000.00, 1),
                ('robert_downey', 'robert@company.com', 50, 148000.00, 0),
                ('sandra_bullock', 'sandra@company.com', 49, 125000.00, 1),
                ('tom_hanks', 'tom@company.com', 56, 138000.00, 1),
                ('uma_thurman', 'uma@company.com', 45, 102000.00, 1),
                ('vin_diesel', 'vin@company.com', 48, 115000.00, 1),
                ('will_smith', 'will@company.com', 52, 142000.00, 0),
                ('xavier_charles', 'xavier@company.com', 60, 158000.00, 1),
                ('yoko_ono', 'yoko@company.com', 62, 108000.00, 1),
                ('zack_snyder', 'zack@company.com', 47, 118000.00, 1),
                ('amy_adams', 'amy@company.com', 43, 92000.00, 1),
                ('brad_pitt', 'brad@company.com', 54, 155000.00, 0),
                ('cate_blanchett', 'cate@company.com', 46, 138000.00, 1),
                ('denzel_washington', 'denzel@company.com', 59, 172000.00, 1),
                ('emma_watson', 'emma@company.com', 32, 85000.00, 1),
                ('faye_dunaway', 'faye@company.com', 63, 98000.00, 1),
                ('gary_oldman', 'gary@company.com', 56, 128000.00, 0),
                ('helen_mirren', 'helen@company.com', 65, 115000.00, 1),
                ('idris_elba', 'idris@company.com', 49, 122000.00, 1),
                ('jennifer_lawrence', 'jennifer@company.com', 31, 102000.00, 1),
                ('keanu_reeves', 'keanu@company.com', 53, 145000.00, 1),
                ('lupita_nyongo', 'lupita@company.com', 38, 88000.00, 0),
                ('morgan_freeman', 'morgan@company.com', 72, 192000.00, 1),
                ('natalie_portman', 'natalie@company.com', 40, 105000.00, 1),
                ('olivia_colman', 'olivia@company.com', 47, 112000.00, 1),
                ('patrick_stewart', 'patrick@company.com', 68, 148000.00, 1),
                ('ryan_gosling', 'ryan@company.com', 41, 125000.00, 1),
                ('scarlett_johansson', 'scarlett@company.com', 37, 135000.00, 1),
                ('timothee_chalamet', 'timothee@company.com', 27, 72000.00, 1),
                ('viola_davis', 'viola@company.com', 55, 122000.00, 0),
                ('woody_harrelson', 'woody@company.com', 59, 115000.00, 1),
                ('gemma_chan', 'gemma@company.com', 39, 92000.00, 1),
                ('hugh_jackman', 'hugh@company.com', 53, 152000.00, 1),
                ('ian_mckellen', 'ian@company.com', 81, 135000.00, 1),
                ('andrew_garfield', 'andrew@company.com', 38, 98000.00, 0),
                ('benedict_cumberbatch', 'benedict@company.com', 45, 132000.00, 1),
                ('chris_hemsworth', 'chris@company.com', 39, 140000.00, 1),
                ('dakota_johnson', 'dakota@company.com', 33, 78000.00, 1),
                ('elizabeth_olsen', 'elizabeth@company.com', 34, 92000.00, 1),
                ('florence_pugh', 'florence@company.com', 28, 68000.00, 0),
                ('gal_gadot', 'gal@company.com', 37, 125000.00, 1),
                ('hailee_steinfeld', 'hailee@company.com', 26, 62000.00, 1),
                ('jake_gyllenhaal', 'jake@company.com', 42, 118000.00, 1),
                ('kate_winslet', 'kate_w@company.com', 46, 132000.00, 0),
                ('margot_robbie', 'margot@company.com', 33, 115000.00, 1),
                ('nicole_kidman', 'nicole@company.com', 55, 148000.00, 1),
                ('oscar_isaac', 'oscar_i@company.com', 43, 105000.00, 1),
                ('pedro_pascal', 'pedro@company.com', 47, 122000.00, 0),
                ('rami_malek', 'rami@company.com', 41, 102000.00, 1),
                ('saoirse_ronan', 'saoirse@company.com', 29, 82000.00, 1),
                ('tom_holland', 'tom_h@company.com', 27, 78000.00, 1),
                ('dev_patel', 'dev@company.com', 33, 88000.00, 1),
                ('leslie_mann', 'leslie@company.com', 49, 95000.00, 1),
                ('queen_latifah', 'queen_l@company.com', 52, 115000.00, 1),
                ('imelda_staunton', 'imelda@company.com', 64, 98000.00, 1);
        END
    """, database='testdb')
    print("   ✅ prod.users created with 99 records")

    print("\n📋 Creating prod.products table...")
    run_sql("""
        IF NOT EXISTS (SELECT * FROM sys.tables t JOIN sys.schemas s ON t.schema_id = s.schema_id WHERE t.name = 'products' AND s.name = 'prod')
        BEGIN
            CREATE TABLE prod.products (
                id INT IDENTITY(1,1) PRIMARY KEY,
                name NVARCHAR(100) NOT NULL,
                category NVARCHAR(50),
                price DECIMAL(10,2),
                stock_quantity INT,
                is_available BIT DEFAULT 1
            );
            
            -- Production Products Indexes
            CREATE INDEX idx_products_category ON prod.products(category);
            CREATE INDEX idx_products_price ON prod.products(price);
            
            INSERT INTO prod.products (name, category, price, stock_quantity, is_available) VALUES
                ('Laptop Pro 16', 'Electronics', 1499.99, 50, 1),
                ('Laptop Air 13', 'Electronics', 999.99, 75, 1),
                ('Wireless Mouse Pro', 'Electronics', 49.99, 200, 1),
                ('Wireless Mouse Basic', 'Electronics', 19.99, 350, 1),
                ('Office Chair Standard', 'Furniture', 249.99, 30, 1),
                ('Office Chair Executive', 'Furniture', 499.99, 15, 1),
                ('Standing Desk Electric', 'Furniture', 699.99, 20, 1),
                ('Coffee Maker Drip', 'Appliances', 89.99, 60, 1),
                ('Coffee Maker Espresso', 'Appliances', 299.99, 25, 1),
                ('Notebook Set Premium', 'Stationery', 18.99, 500, 1),
                ('Monitor 27" 4K', 'Electronics', 449.99, 45, 1),
                ('Monitor 32" Curved', 'Electronics', 599.99, 30, 1),
                ('Keyboard Mechanical', 'Electronics', 129.99, 120, 1),
                ('Keyboard Wireless', 'Electronics', 59.99, 180, 1),
                ('Desk Lamp LED Pro', 'Furniture', 49.99, 85, 1),
                ('USB Hub 7-Port', 'Electronics', 29.99, 150, 1),
                ('Webcam 4K', 'Electronics', 99.99, 70, 1),
                ('Headphones Wireless ANC', 'Electronics', 249.99, 40, 1),
                ('Headphones Wired Studio', 'Electronics', 149.99, 55, 1),
                ('Monitor Stand Bamboo', 'Furniture', 59.99, 45, 1),
                ('Cable Organizer Set', 'Accessories', 14.99, 300, 1),
                ('Laptop Stand Aluminum', 'Accessories', 44.99, 110, 1),
                ('Power Strip Smart', 'Electronics', 34.99, 200, 1),
                ('Air Purifier HEPA', 'Appliances', 249.99, 25, 1),
                ('Desk Mat XXL', 'Accessories', 34.99, 180, 1),
                ('Gaming Mouse RGB', 'Electronics', 79.99, 95, 1),
                ('Monitor Arm Dual', 'Furniture', 129.99, 35, 1),
                ('Wireless Charger Qi', 'Electronics', 39.99, 175, 1),
                ('Bluetooth Speaker Pro', 'Electronics', 99.99, 65, 1),
                ('Desk Drawer Organizer', 'Furniture', 69.99, 35, 1),
                ('Whiteboard 3x4', 'Stationery', 44.99, 40, 1),
                ('Pen Set Executive', 'Stationery', 29.99, 250, 1),
                ('Sticky Notes Mega Pack', 'Stationery', 12.99, 400, 1),
                ('Paper Shredder Cross-Cut', 'Appliances', 99.99, 20, 1),
                ('Filing Cabinet 3-Drawer', 'Furniture', 189.99, 18, 1),
                ('Bookshelf 5-Tier', 'Furniture', 119.99, 22, 1),
                ('Footrest Ergonomic Pro', 'Furniture', 54.99, 55, 1),
                ('Wrist Rest Gel', 'Accessories', 19.99, 160, 1),
                ('Mousepad XXL', 'Accessories', 16.99, 220, 1),
                ('External SSD 1TB', 'Electronics', 109.99, 70, 1),
                ('External SSD 2TB', 'Electronics', 179.99, 35, 1),
                ('USB Flash Drive 128GB', 'Electronics', 19.99, 350, 1),
                ('Ethernet Cable Cat6 10ft', 'Electronics', 12.99, 280, 1),
                ('HDMI Cable 8K 6ft', 'Electronics', 19.99, 190, 1),
                ('DisplayPort Cable 1.4', 'Electronics', 17.99, 145, 1),
                ('Surge Protector 8-Outlet', 'Electronics', 39.99, 95, 1),
                ('UPS Battery 1500VA', 'Electronics', 199.99, 25, 1),
                ('Router WiFi 6E', 'Electronics', 229.99, 40, 1),
                ('Network Switch 8-Port', 'Electronics', 59.99, 55, 1),
                ('Printer Laser Color', 'Electronics', 399.99, 15, 1),
                ('Scanner Flatbed', 'Electronics', 149.99, 30, 1),
                ('Ink Cartridge Set XL', 'Stationery', 54.99, 120, 1),
                ('Paper A4 Premium 5-Ream', 'Stationery', 34.99, 200, 1),
                ('Stapler Electric', 'Stationery', 29.99, 85, 1),
                ('Paper Clips Jumbo Box', 'Stationery', 5.99, 600, 1),
                ('Folder Set Hanging', 'Stationery', 16.99, 200, 1),
                ('Label Maker Pro', 'Stationery', 49.99, 50, 1),
                ('Calculator Financial', 'Stationery', 34.99, 80, 1),
                ('Planner Weekly', 'Stationery', 24.99, 150, 1),
                ('Envelope Pack Business', 'Stationery', 12.99, 280, 1),
                ('Tape Dispenser Heavy', 'Stationery', 12.99, 195, 1),
                ('Scissors Professional', 'Stationery', 16.99, 160, 1),
                ('Highlighter Set 12-Color', 'Stationery', 11.99, 350, 1),
                ('Marker Whiteboard Set', 'Stationery', 14.99, 275, 1),
                ('Pencil Mechanical Set', 'Stationery', 12.99, 220, 1),
                ('Desk Organizer Bamboo', 'Furniture', 44.99, 90, 1),
                ('Magazine Rack Wall', 'Furniture', 24.99, 110, 1),
                ('Wall Clock Modern', 'Furniture', 39.99, 65, 1),
                ('Trash Can Smart', 'Furniture', 49.99, 50, 1),
                ('Plant Pot Ceramic Set', 'Furniture', 34.99, 85, 1),
                ('Photo Frame Digital', 'Furniture', 59.99, 40, 1),
                ('Cork Board XL', 'Furniture', 34.99, 55, 1),
                ('Coat Rack Standing', 'Furniture', 54.99, 25, 1),
                ('Cushion Lumbar Support', 'Furniture', 44.99, 70, 1),
                ('Rug Anti-Fatigue', 'Furniture', 69.99, 30, 1),
                ('Kettle Smart', 'Appliances', 49.99, 95, 1),
                ('Toaster 4-Slice', 'Appliances', 49.99, 60, 1),
                ('Microwave Inverter', 'Appliances', 149.99, 30, 1),
                ('Mini Fridge 3.5cu', 'Appliances', 189.99, 20, 1),
                ('Blender Pro', 'Appliances', 79.99, 45, 1),
                ('Food Processor 12-Cup', 'Appliances', 129.99, 25, 1),
                ('Hand Mixer 5-Speed', 'Appliances', 34.99, 70, 1),
                ('Rice Cooker Digital', 'Appliances', 59.99, 45, 1),
                ('Slow Cooker 6-Quart', 'Appliances', 69.99, 35, 1),
                ('Pressure Cooker Electric', 'Appliances', 119.99, 25, 1),
                ('Air Fryer XL', 'Appliances', 129.99, 40, 1),
                ('Grill Indoor Electric', 'Appliances', 99.99, 30, 1),
                ('Waffle Maker Belgian', 'Appliances', 44.99, 50, 1),
                ('Juicer Cold Press', 'Appliances', 89.99, 30, 1),
                ('Water Dispenser Hot/Cold', 'Appliances', 159.99, 15, 1),
                ('Ice Maker Countertop', 'Appliances', 179.99, 18, 1),
                ('Fan Tower', 'Appliances', 49.99, 80, 1),
                ('Heater Ceramic', 'Appliances', 59.99, 45, 1),
                ('Humidifier Ultrasonic', 'Appliances', 54.99, 55, 1),
                ('Dehumidifier 30-Pint', 'Appliances', 179.99, 20, 1),
                ('Vacuum Robot', 'Appliances', 299.99, 25, 1),
                ('Steam Iron Professional', 'Appliances', 49.99, 60, 1),
                ('Gaming Chair Racing', 'Furniture', 349.99, 25, 1),
                ('Ergonomic Chair Mesh', 'Furniture', 549.99, 18, 1),
                ('L-Shaped Desk Oak', 'Furniture', 449.99, 12, 1),
                ('Adjustable Desk Bamboo', 'Furniture', 649.99, 20, 1),
                ('Conference Table 8ft', 'Furniture', 899.99, 8, 1),
                ('Webcam Ring Light', 'Electronics', 39.99, 100, 1),
                ('USB-C Dock 12-in-1', 'Electronics', 79.99, 65, 1),
                ('Tablet Stand Adjustable', 'Accessories', 29.99, 130, 1),
                ('Screen Protector Kit', 'Accessories', 14.99, 250, 1),
                ('Cleaning Kit Electronics', 'Accessories', 19.99, 180, 1),
                ('Backpack Laptop 17"', 'Accessories', 59.99, 75, 1),
                ('Sleeve Laptop 15"', 'Accessories', 24.99, 120, 1),
                ('Docking Station USB4', 'Electronics', 199.99, 30, 1),
                ('Smart Plug WiFi 4-Pack', 'Electronics', 29.99, 150, 1);
        END
    """, database='testdb')
    print("   ✅ prod.products created with 111 records")

    # ==========================================
    # 2. UAT Environment (Simulated Drift)
    # ==========================================
    print("\n📋 Creating uat.users (UAT) table...")
    run_sql("""
        IF NOT EXISTS (SELECT * FROM sys.tables t JOIN sys.schemas s ON t.schema_id = s.schema_id WHERE t.name = 'users' AND s.name = 'uat')
        BEGIN
            CREATE TABLE uat.users (
                id INT IDENTITY(1,1) PRIMARY KEY,
                username NVARCHAR(50) NOT NULL,
                
                -- Drift: NVARCHAR(150)
                email NVARCHAR(150),
                
                -- Drift: NOT NULL in UAT (vs nullable via pattern in Prod)
                age INT,
                
                -- Drift: DECIMAL(12,2)
                salary DECIMAL(12,2),
                
                is_active BIT DEFAULT 1,
                created_at DATETIME2 DEFAULT GETDATE(),
                
                -- Drift: Extra column
                middle_name NVARCHAR(50)
            );
            
            -- UAT Indexes
            -- Drift: Missing username index
            CREATE INDEX idx_users_age_salary ON uat.users(age, salary);
            CREATE UNIQUE INDEX idx_users_email ON uat.users(email);

            INSERT INTO uat.users (username, email, age, salary, is_active, middle_name) VALUES
                ('john_doe', 'john@testmail.io', 35, 72000.00, 1, NULL),
                ('jane_smith', 'jane@testmail.io', 42, 89000.00, 1, 'Marie'),
                ('bob_wilson', 'bob@testmail.io', 51, 102000.00, 1, NULL),
                ('alice_johnson', 'alice@testmail.io', 38, 79000.00, 0, 'Grace'),
                ('charlie_brown', 'charlie@testmail.io', NULL, 95000.00, 1, NULL),
                ('diana_prince', 'diana@testmail.io', 39, NULL, 1, 'Athena'),
                ('edward_stark', 'edward@testmail.io', 55, 128000.00, 1, NULL),
                ('fiona_green', 'fiona@testmail.io', 33, 65000.00, 0, NULL),
                ('george_lucas', 'george@testmail.io', 48, 112000.00, 1, 'Walton'),
                ('hannah_montana', 'hannah@testmail.io', 29, 55000.00, 1, NULL),
                ('kevin_hart', 'kevin@testmail.io', 36, 70000.00, 1, 'Darnell'),
                ('laura_palmer', 'laura@testmail.io', 32, 61000.00, 1, NULL),
                ('mike_tyson', 'mike@testmail.io', 50, 105000.00, 1, 'Gerard'),
                ('nancy_drew', 'nancy@testmail.io', 28, 53000.00, 1, NULL),
                ('oscar_wilde', 'oscar@testmail.io', NULL, 96000.00, 0, 'Fingal'),
                ('rachel_green', 'rachel@testmail.io', 34, 68000.00, 1, 'Karen'),
                ('steve_rogers', 'steve@testmail.io', 40, 88000.00, 1, 'Grant'),
                ('tina_turner', 'tina@testmail.io', 47, 99000.00, 0, NULL),
                ('walter_white', 'walter@testmail.io', 52, 122000.00, 1, 'Hartwell'),
                ('yuri_gagarin', 'yuri@testmail.io', 45, 94000.00, 1, NULL),
                ('adam_levine', 'adam@testmail.io', 41, 90000.00, 1, 'Noah'),
                ('betty_white', 'betty@testmail.io', 58, 112000.00, 1, NULL),
                ('carl_sagan', 'carl@testmail.io', NULL, 103000.00, 0, 'Edward'),
                ('frank_sinatra', 'frank@testmail.io', 53, 130000.00, 1, 'Albert'),
                ('greta_thunberg', 'greta@testmail.io', 25, 46000.00, 1, NULL),
                ('henry_ford', 'henry@testmail.io', 57, 145000.00, 1, NULL),
                ('iris_west', 'iris@testmail.io', 31, 60000.00, 1, 'Ann'),
                ('james_bond', 'james@testmail.io', 46, 115000.00, 1, NULL),
                ('kate_middleton', 'kate@testmail.io', 40, 92000.00, 1, NULL),
                ('leonardo_dicaprio', 'leonardo@testmail.io', 48, 138000.00, 1, 'Wilhelm'),
                ('oprah_winfrey', 'oprah@testmail.io', 59, 180000.00, 1, 'Gail'),
                ('peter_parker', 'peter@testmail.io', 26, 52000.00, 1, 'Benjamin'),
                ('tom_hanks', 'tom@testmail.io', 56, 135000.00, 1, 'Jeffrey'),
                ('uma_thurman', 'uma@testmail.io', 45, 100000.00, 1, 'Karuna'),
                ('vin_diesel', 'vin@testmail.io', 48, 112000.00, 1, NULL),
                ('will_smith', 'will@testmail.io', NULL, 140000.00, 0, 'Carroll'),
                ('xavier_charles', 'xavier@testmail.io', 60, 155000.00, 1, NULL),
                ('amy_adams', 'amy@testmail.io', 43, 89000.00, 1, 'Lou'),
                ('brad_pitt', 'brad@testmail.io', 54, 152000.00, 0, 'William'),
                ('cate_blanchett', 'cate@testmail.io', 46, 135000.00, 1, NULL),
                ('emma_watson', 'emma@testmail.io', 32, 82000.00, 1, 'Charlotte'),
                ('gary_oldman', 'gary@testmail.io', 56, 125000.00, 0, 'Leonard'),
                ('helen_mirren', 'helen@testmail.io', 65, 112000.00, 1, NULL),
                ('idris_elba', 'idris@testmail.io', 49, 119000.00, 1, NULL),
                ('jennifer_lawrence', 'jennifer@testmail.io', 31, 99000.00, 1, 'Shrader'),
                ('keanu_reeves', 'keanu@testmail.io', 53, 142000.00, 1, 'Charles'),
                ('morgan_freeman', 'morgan@testmail.io', 72, 188000.00, 1, NULL),
                ('natalie_portman', 'natalie@testmail.io', 40, 102000.00, 1, NULL),
                ('olivia_colman', 'olivia@testmail.io', NULL, 109000.00, 1, 'Sarah'),
                ('patrick_stewart', 'patrick@testmail.io', 68, 145000.00, 1, NULL),
                ('ryan_gosling', 'ryan@testmail.io', 41, 122000.00, 1, 'Thomas'),
                ('scarlett_johansson', 'scarlett@testmail.io', 37, 132000.00, 1, 'Ingrid'),
                ('viola_davis', 'viola@testmail.io', 55, 119000.00, 0, NULL),
                ('gemma_chan', 'gemma@testmail.io', 39, 89000.00, 1, NULL),
                ('hugh_jackman', 'hugh@testmail.io', 53, 149000.00, 1, 'Michael'),
                ('chris_hemsworth', 'chris@testmail.io', 39, 137000.00, 1, NULL),
                ('elizabeth_olsen', 'elizabeth@testmail.io', 34, 89000.00, 1, 'Chase'),
                ('gal_gadot', 'gal@testmail.io', 37, 122000.00, 1, NULL),
                ('margot_robbie', 'margot@testmail.io', 33, 112000.00, 1, 'Elise'),
                ('nicole_kidman', 'nicole@testmail.io', 55, 145000.00, 1, 'Mary'),
                -- UAT-only users
                ('new_hire_01', 'newhire01@testmail.io', 24, 42000.00, 1, NULL),
                ('new_hire_02', 'newhire02@testmail.io', 22, 40000.00, 1, 'James'),
                ('new_hire_03', 'newhire03@testmail.io', 26, 45000.00, 1, NULL),
                ('new_hire_04', 'newhire04@testmail.io', 23, NULL, 1, NULL),
                ('new_hire_05', 'newhire05@testmail.io', NULL, 43000.00, 0, 'Test'),
                ('intern_alpha', 'intern_a@testmail.io', 20, 28000.00, 1, NULL),
                ('intern_beta', 'intern_b@testmail.io', 21, 28000.00, 1, NULL),
                ('contractor_01', 'contract01@testmail.io', 35, NULL, 1, NULL),
                ('contractor_02', 'contract02@testmail.io', 40, NULL, 1, 'External'),
                ('temp_user_01', 'temp01@testmail.io', NULL, 35000.00, 1, NULL),
                ('test_admin', 'admin@testmail.io', 30, 65000.00, 1, 'Admin'),
                ('qa_tester', 'qa@testmail.io', 28, 55000.00, 1, NULL),
                ('dev_tester', 'dev_test@testmail.io', 32, 62000.00, 1, NULL),
                ('staging_user', 'staging@testmail.io', NULL, NULL, 0, 'Staging'),
                ('demo_account', 'demo@testmail.io', 25, 50000.00, 1, NULL),
                ('load_test_01', 'loadtest01@testmail.io', NULL, NULL, 1, NULL),
                ('load_test_02', 'loadtest02@testmail.io', NULL, NULL, 1, NULL),
                ('load_test_03', 'loadtest03@testmail.io', NULL, NULL, 1, 'Perf'),
                ('smoke_test', 'smoke@testmail.io', 30, 55000.00, 1, NULL),
                ('regression_user', 'regression@testmail.io', 28, 52000.00, 1, 'QA');
        END
    """, database='testdb')
    print("   ✅ uat.users created with 80 records")
    
    print("\n📋 Creating uat.products table...")
    run_sql("""
        IF NOT EXISTS (SELECT * FROM sys.tables t JOIN sys.schemas s ON t.schema_id = s.schema_id WHERE t.name = 'products' AND s.name = 'uat')
        BEGIN
            CREATE TABLE uat.products (
                id INT IDENTITY(1,1) PRIMARY KEY,
                name NVARCHAR(100) NOT NULL,
                
                -- Drift: NVARCHAR(80)
                category NVARCHAR(80),
                
                -- Drift: DECIMAL(12,4)
                price DECIMAL(12,4),
                
                stock_quantity INT,
                is_available BIT DEFAULT 1,
                
                -- Drift: Extra columns
                sku NVARCHAR(30),
                discount_percent DECIMAL(5,2)
            );
            
            -- UAT Products Indexes
            -- Drift: Missing price index
            CREATE INDEX idx_products_category ON uat.products(category);
            
            INSERT INTO uat.products (name, category, price, stock_quantity, is_available, sku, discount_percent) VALUES
                ('Laptop Pro 16', 'Electronics', 1399.9900, 30, 1, 'ELEC-LP16-001', 5.00),
                ('Laptop Air 13', 'Electronics', 949.9900, 45, 1, 'ELEC-LA13-002', 8.00),
                ('Wireless Mouse Pro', 'Electronics', 44.9900, 150, 1, 'ELEC-WMP-003', NULL),
                ('Wireless Mouse Basic', 'Electronics', 17.9900, 200, 1, 'ELEC-WMB-004', 10.00),
                ('Office Chair Standard', 'Furniture', 229.9900, 20, 1, 'FURN-OCS-005', NULL),
                ('Office Chair Executive', 'Furniture', 469.9900, 8, 0, 'FURN-OCE-006', 5.00),
                ('Standing Desk Electric', 'Furniture', 649.9900, 12, 1, 'FURN-SDE-007', NULL),
                ('Coffee Maker Drip', 'Appliances', 79.9900, NULL, 0, 'APPL-CMD-008', 15.00),
                ('Coffee Maker Espresso', 'Appliances', 279.9900, 15, 1, 'APPL-CME-009', 10.00),
                ('Notebook Set Premium', 'Stationery', 16.9900, 300, 1, 'STAT-NSP-010', NULL),
                ('Monitor 27" 4K', 'Electronics', 419.9900, 25, 1, 'ELEC-M27-011', 5.00),
                ('Monitor 32" Curved', 'Electronics', 569.9900, 18, 1, 'ELEC-M32-012', NULL),
                ('Keyboard Mechanical', 'Electronics', 119.9900, 80, 1, 'ELEC-KM-013', NULL),
                ('Keyboard Wireless', 'Electronics', 54.9900, 120, 1, 'ELEC-KW-014', 10.00),
                ('Desk Lamp LED Pro', 'Furniture', 44.9900, 50, 1, 'FURN-DLP-015', NULL),
                ('USB Hub 7-Port', 'Electronics', 27.9900, 100, 1, 'ELEC-UH7-016', 5.00),
                ('Webcam 4K', 'Electronics', 89.9900, 40, 0, 'ELEC-WC4-017', 10.00),
                ('Headphones Wireless ANC', 'Electronics', 229.9900, 25, 1, 'ELEC-HWA-018', NULL),
                ('Monitor Stand Bamboo', 'Furniture', 54.9900, 30, 1, 'FURN-MSB-019', NULL),
                ('Cable Organizer Set', 'Accessories', 12.9900, 200, 1, 'ACCS-COS-020', NULL),
                ('Laptop Stand Aluminum', 'Accessories', 39.9900, 75, 1, 'ACCS-LSA-021', 5.00),
                ('Air Purifier HEPA', 'Appliances', 229.9900, 15, 1, 'APPL-APH-022', NULL),
                ('Desk Mat XXL', 'Accessories', 29.9900, 120, 1, 'ACCS-DMX-023', NULL),
                ('Gaming Mouse RGB', 'Electronics', 74.9900, 60, 1, 'ELEC-GMR-024', NULL),
                ('Monitor Arm Dual', 'Furniture', 119.9900, 20, 1, 'FURN-MAD-025', 5.00),
                ('Wireless Charger Qi', 'Electronics', 34.9900, 100, 0, 'ELEC-WCQ-026', 15.00),
                ('Bluetooth Speaker Pro', 'Electronics', 94.9900, 40, 1, 'ELEC-BSP-027', NULL),
                ('Whiteboard 3x4', 'Stationery', 39.9900, 25, 1, 'STAT-WB3-028', NULL),
                ('Pen Set Executive', 'Stationery', 27.9900, 180, 1, 'STAT-PSE-029', NULL),
                ('Paper Shredder Cross-Cut', 'Appliances', 89.9900, 12, 0, 'APPL-PSC-030', 10.00),
                ('Filing Cabinet 3-Drawer', 'Furniture', 179.9900, 10, 1, 'FURN-FC3-031', NULL),
                ('Bookshelf 5-Tier', 'Furniture', 109.9900, 15, 1, 'FURN-BS5-032', NULL),
                ('External SSD 1TB', 'Electronics', 99.9900, 45, 1, 'ELEC-ES1-033', 10.00),
                ('External SSD 2TB', 'Electronics', 169.9900, 20, 1, 'ELEC-ES2-034', NULL),
                ('USB Flash Drive 128GB', 'Electronics', 17.9900, 250, 1, 'ELEC-UFD-035', NULL),
                ('HDMI Cable 8K 6ft', 'Electronics', 17.9900, 130, 1, 'ELEC-HC8-036', NULL),
                ('Surge Protector 8-Outlet', 'Electronics', 37.9900, 60, 1, 'ELEC-SP8-037', 5.00),
                ('UPS Battery 1500VA', 'Electronics', 189.9900, 15, 0, 'ELEC-UPS-038', NULL),
                ('Router WiFi 6E', 'Electronics', 219.9900, 25, 1, 'ELEC-RW6-039', NULL),
                ('Printer Laser Color', 'Electronics', 379.9900, 8, 1, 'ELEC-PLC-040', 5.00),
                ('Scanner Flatbed', 'Electronics', 139.9900, 18, 1, 'ELEC-SF-041', NULL),
                ('Ink Cartridge Set XL', 'Stationery', 49.9900, 80, 0, 'STAT-ICS-042', 10.00),
                ('Paper A4 Premium 5-Ream', 'Stationery', 32.9900, 150, 1, 'STAT-PA4-043', NULL),
                ('Highlighter Set 12-Color', 'Stationery', 10.9900, 250, 1, 'STAT-HS12-044', NULL),
                ('Marker Whiteboard Set', 'Stationery', 13.9900, 200, 1, 'STAT-MWS-045', NULL),
                ('Desk Organizer Bamboo', 'Furniture', 42.9900, 60, 1, 'FURN-DOB-046', NULL),
                ('Wall Clock Modern', 'Furniture', 37.9900, 40, 1, 'FURN-WCM-047', NULL),
                ('Trash Can Smart', 'Furniture', 47.9900, 30, 1, 'FURN-TCS-048', 5.00),
                ('Plant Pot Ceramic Set', 'Furniture', 32.9900, 55, 0, 'FURN-PPC-049', NULL),
                ('Cork Board XL', 'Furniture', 32.9900, 35, 1, 'FURN-CBX-050', NULL),
                ('Kettle Smart', 'Appliances', 46.9900, 60, 1, 'APPL-KS-051', 5.00),
                ('Toaster 4-Slice', 'Appliances', 47.9900, 40, 1, 'APPL-T4S-052', NULL),
                ('Microwave Inverter', 'Appliances', 139.9900, 18, 1, 'APPL-MI-053', NULL),
                ('Mini Fridge 3.5cu', 'Appliances', 179.9900, 12, 0, 'APPL-MF3-054', 5.00),
                ('Blender Pro', 'Appliances', 74.9900, 30, 1, 'APPL-BP-055', NULL),
                ('Rice Cooker Digital', 'Appliances', 54.9900, 30, 1, 'APPL-RCD-056', NULL),
                ('Air Fryer XL', 'Appliances', 119.9900, 25, 1, 'APPL-AFX-057', NULL),
                ('Vacuum Robot', 'Appliances', 279.9900, 15, 1, 'APPL-VR-058', 10.00),
                ('Gaming Chair Racing', 'Furniture', 329.9900, 15, 1, 'FURN-GCR-059', 5.00),
                ('Ergonomic Chair Mesh', 'Furniture', 529.9900, 10, 1, 'FURN-ECM-060', NULL),
                ('L-Shaped Desk Oak', 'Furniture', 429.9900, 8, 0, 'FURN-LSD-061', NULL),
                ('Adjustable Desk Bamboo', 'Furniture', 629.9900, 12, 1, 'FURN-ADB-062', 5.00),
                ('Conference Table 8ft', 'Furniture', 879.9900, 5, 1, 'FURN-CT8-063', NULL),
                ('Webcam Ring Light', 'Electronics', 37.9900, 70, 1, 'ELEC-WRL-064', NULL),
                ('USB-C Dock 12-in-1', 'Electronics', 74.9900, 40, 1, 'ELEC-UCD-065', NULL),
                ('Tablet Stand Adjustable', 'Accessories', 27.9900, 90, 1, 'ACCS-TSA-066', NULL),
                ('Cleaning Kit Electronics', 'Accessories', 17.9900, 130, 1, 'ACCS-CKE-067', NULL),
                ('Backpack Laptop 17"', 'Accessories', 54.9900, 50, 1, 'ACCS-BL17-068', 5.00),
                ('Docking Station USB4', 'Electronics', 189.9900, 18, 1, 'ELEC-DSU-069', NULL),
                ('Smart Plug WiFi 4-Pack', 'Electronics', 27.9900, 100, 1, 'ELEC-SPW-070', NULL),
                ('VR Headset Pro', 'Electronics', 599.9900, 10, 1, 'ELEC-VRP-071', NULL),
                ('AR Glasses Dev Kit', 'Electronics', 899.9900, 5, 0, 'ELEC-ARG-072', 15.00),
                ('Smart Whiteboard 55"', 'Electronics', 2499.9900, 3, 1, 'ELEC-SW55-073', NULL),
                ('Standing Mat Anti-Fatigue', 'Furniture', 79.9900, 40, 1, 'FURN-SMA-074', NULL),
                ('Privacy Screen 27"', 'Accessories', 49.9900, 25, 1, 'ACCS-PS27-075', 5.00),
                ('Noise Machine White', 'Appliances', 39.9900, 35, 1, 'APPL-NMW-076', NULL),
                ('Desk Bike Under', 'Furniture', 199.9900, 8, 1, 'FURN-DBU-077', NULL),
                ('Cable Management Tray', 'Accessories', 24.9900, 60, 1, 'ACCS-CMT-078', NULL),
                ('Monitor Light Bar', 'Electronics', 44.9900, 45, 1, 'ELEC-MLB-079', NULL),
                ('Acoustic Panel Set', 'Furniture', 89.9900, 20, 1, 'FURN-APS-080', 10.00),
                ('Portable Projector Mini', 'Electronics', 349.9900, 12, 1, 'ELEC-PPM-081', NULL),
                ('Wireless Presenter', 'Electronics', 29.9900, 80, 1, 'ELEC-WP-082', NULL),
                ('Fidget Desk Toy Set', 'Accessories', 14.9900, 100, 1, 'ACCS-FDT-083', NULL),
                ('Aroma Diffuser USB', 'Appliances', 24.9900, 50, 1, 'APPL-ADU-084', NULL),
                ('Laptop Cooling Pad', 'Accessories', 34.9900, 55, 1, 'ACCS-LCP-085', 5.00),
                ('Smart Lamp Color', 'Electronics', 59.9900, 30, 1, 'ELEC-SLC-086', NULL),
                ('Document Camera HD', 'Electronics', 149.9900, 15, 0, 'ELEC-DCH-087', 10.00),
                ('Keyboard Wrist Pad', 'Accessories', 19.9900, 90, 1, 'ACCS-KWP-088', NULL),
                ('Webcam Cover Slide', 'Accessories', 4.9900, 500, 1, 'ACCS-WCS-089', NULL),
                ('USB Desk Fan Mini', 'Appliances', 14.9900, 120, 1, 'APPL-UDF-090', NULL);
        END
    """, database='testdb')
    print("   ✅ uat.products created with 90 records")
    
    print("\n" + "=" * 50)
    print("✅ MSSQL initialization completed successfully!")
    print("=" * 50)
    print("\nYou can now run:")
    print("  python main.py --table users -d mssql --schema prod")
    print("  python main.py --table users -d mssql --schema uat")
    print("  python main.py -t users,products -d mssql --auto-increment")


if __name__ == '__main__':
    main()
