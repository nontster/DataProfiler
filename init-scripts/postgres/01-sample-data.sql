-- Sample data for testing DataProfiler
-- This script runs automatically when PostgreSQL container starts

-- Create schemas
CREATE SCHEMA IF NOT EXISTS prod;
CREATE SCHEMA IF NOT EXISTS uat;

-- ==========================================
-- 1. Production Environment (Golden Schema)
-- ==========================================
CREATE TABLE IF NOT EXISTS prod.users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL,
    age INTEGER,
    salary NUMERIC(10, 2),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Production Indexes
CREATE INDEX IF NOT EXISTS idx_users_username ON prod.users(username);
CREATE INDEX IF NOT EXISTS idx_users_age_salary ON prod.users(age, salary);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON prod.users(email);


-- ==========================================
-- 2. UAT Environment (Simulated Drift)
-- ==========================================
CREATE TABLE IF NOT EXISTS uat.users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    
    -- Drift: different length
    email VARCHAR(150),
    
    -- Drift: NOT NULL in UAT (vs nullable in Prod)
    age INTEGER,
    
    -- Drift: different precision
    salary NUMERIC(12, 2),
    
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Drift: Extra column in UAT
    middle_name VARCHAR(50)
);

-- UAT Indexes 
-- Drift: Missing index on username
CREATE INDEX IF NOT EXISTS idx_users_age_salary ON uat.users(age, salary);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON uat.users(email);


-- Insert sample data into PROD
INSERT INTO prod.users (username, email, age, salary, is_active) VALUES
    ('john_doe', 'john@example.com', 28, 55000.00, true),
    ('jane_smith', 'jane@example.com', 34, 72000.00, true),
    ('bob_wilson', 'bob@example.com', 45, 85000.00, true),
    ('alice_johnson', 'alice@example.com', 29, 62000.00, false),
    ('charlie_brown', 'charlie@example.com', NULL, 48000.00, true),
    ('diana_prince', 'diana@example.com', 31, NULL, true),
    ('edward_stark', 'edward@example.com', 52, 120000.00, true),
    ('fiona_green', 'fiona@example.com', 27, 45000.00, false),
    ('george_lucas', 'george@example.com', 38, 95000.00, true),
    ('hannah_montana', 'hannah@example.com', 23, 38000.00, true),
    ('ivan_petrov', 'ivan@example.com', 41, 78000.00, true),
    ('julia_roberts', 'julia@example.com', 36, 88000.00, true),
    ('kevin_hart', 'kevin@example.com', 33, 67000.00, false),
    ('laura_palmer', 'laura@example.com', 29, 54000.00, true),
    ('mike_tyson', 'mike@example.com', 48, 92000.00, true),
    ('nancy_drew', 'nancy@example.com', 26, 43000.00, true),
    ('oscar_wilde', 'oscar@example.com', 39, 81000.00, false),
    ('paula_abdul', 'paula@example.com', 44, 76000.00, true),
    ('quentin_beck', 'quentin@example.com', 31, 59000.00, true),
    ('rachel_green', 'rachel@example.com', 28, 52000.00, true),
    ('steve_rogers', 'steve@example.com', 35, 71000.00, true),
    ('tina_turner', 'tina@example.com', 42, 84000.00, false),
    ('ulrich_stern', 'ulrich@example.com', 37, 69000.00, true),
    ('victoria_secret', 'victoria@example.com', 30, 63000.00, true),
    ('walter_white', 'walter@example.com', 50, 115000.00, true),
    ('xena_warrior', 'xena@example.com', 32, 58000.00, false),
    ('yuri_gagarin', 'yuri@example.com', 40, 87000.00, true),
    ('zara_larsson', 'zara@example.com', 25, 41000.00, true),
    ('adam_levine', 'adam@example.com', 38, 93000.00, true),
    ('betty_white', 'betty@example.com', 55, 102000.00, true),
    ('carl_sagan', 'carl@example.com', 47, 98000.00, false),
    ('debbie_harry', 'debbie@example.com', 34, 74000.00, true),
    ('elvis_presley', 'elvis@example.com', 42, NULL, true),
    ('frank_sinatra', 'frank@example.com', 51, 125000.00, true),
    ('greta_thunberg', 'greta@example.com', 21, 35000.00, true),
    ('henry_ford', 'henry@example.com', 56, 145000.00, false),
    ('iris_west', 'iris@example.com', 29, 56000.00, true),
    ('james_bond', 'james@example.com', 45, 110000.00, true),
    ('kate_middleton', 'kate@example.com', 39, 89000.00, true),
    ('leonardo_dicaprio', 'leonardo@example.com', 46, 135000.00, true),
    ('madonna_ciccone', 'madonna@example.com', 53, 105000.00, false),
    ('neil_armstrong', 'neil@example.com', NULL, 95000.00, true),
    ('oprah_winfrey', 'oprah@example.com', 57, 175000.00, true),
    ('peter_parker', 'peter@example.com', 24, 48000.00, true),
    ('queen_elizabeth', 'queen@example.com', 65, 200000.00, true),
    ('robert_downey', 'robert@example.com', 49, 142000.00, false),
    ('sandra_bullock', 'sandra@example.com', 48, 118000.00, true),
    ('tom_hanks', 'tom@example.com', 54, 128000.00, true),
    ('uma_thurman', 'uma@example.com', 44, 96000.00, true),
    ('vin_diesel', 'vin@example.com', 47, 108000.00, true),
    ('will_smith', 'will@example.com', 50, 138000.00, false),
    ('xavier_charles', 'xavier@example.com', 58, 152000.00, true),
    ('yoko_ono', 'yoko@example.com', 60, 98000.00, true),
    ('zack_snyder', 'zack@example.com', 46, 112000.00, true),
    ('amy_adams', 'amy@example.com', 41, 86000.00, true),
    ('brad_pitt', 'brad@example.com', 52, 148000.00, false),
    ('cate_blanchett', 'cate@example.com', 45, 132000.00, true),
    ('denzel_washington', 'denzel@example.com', 58, 165000.00, true),
    ('emma_watson', 'emma@example.com', 30, 78000.00, true),
    ('faye_dunaway', 'faye@example.com', 62, 88000.00, true),
    ('gary_oldman', 'gary@example.com', 55, 122000.00, false),
    ('helen_mirren', 'helen@example.com', 64, 108000.00, true),
    ('idris_elba', 'idris@example.com', 48, 115000.00, true),
    ('jennifer_lawrence', 'jennifer@example.com', 29, 95000.00, true),
    ('keanu_reeves', 'keanu@example.com', 51, 138000.00, true),
    ('lupita_nyongo', 'lupita@example.com', 35, 82000.00, false),
    ('morgan_freeman', 'morgan@example.com', 72, 185000.00, true),
    ('natalie_portman', 'natalie@example.com', 38, 98000.00, true),
    ('olivia_colman', 'olivia@example.com', 46, 105000.00, true),
    ('patrick_stewart', 'patrick@example.com', 68, 142000.00, true),
    ('quvenzhane_wallis', 'quvenzhane@example.com', 22, 42000.00, false),
    ('ryan_gosling', 'ryan@example.com', 39, 118000.00, true),
    ('scarlett_johansson', 'scarlett@example.com', 35, 128000.00, true),
    ('timothee_chalamet', 'timothee@example.com', 25, 68000.00, true),
    ('Uma_Stone', 'uma_s@example.com', 32, 92000.00, true),
    ('viola_davis', 'viola@example.com', 54, 115000.00, false),
    ('woody_harrelson', 'woody@example.com', 58, 108000.00, true),
    ('xuxa_meneghel', 'xuxa@example.com', 48, 78000.00, true),
    ('yang_mi', 'yang@example.com', 33, 88000.00, true),
    ('zhang_ziyi', 'zhang@example.com', 41, 102000.00, true),
    ('andrew_garfield', 'andrew@example.com', 37, 95000.00, false),
    ('benedict_cumberbatch', 'benedict@example.com', 44, 128000.00, true),
    ('chris_hemsworth', 'chris@example.com', 38, 135000.00, true),
    ('dakota_johnson', 'dakota@example.com', 31, 72000.00, true),
    ('elizabeth_olsen', 'elizabeth@example.com', 32, 85000.00, true),
    ('florence_pugh', 'florence@example.com', 26, 62000.00, false),
    ('gal_gadot', 'gal@example.com', 36, 118000.00, true),
    ('hailee_steinfeld', 'hailee@example.com', 24, 58000.00, true),
    ('imelda_staunton', 'imelda@example.com', 63, 92000.00, true),
    ('jake_gyllenhaal', 'jake@example.com', 40, 112000.00, true),
    ('kate_winslet', 'kate_w@example.com', 45, 125000.00, false),
    ('leslie_mann', 'leslie@example.com', 48, 88000.00, true),
    ('margot_robbie', 'margot@example.com', 31, 108000.00, true),
    ('nicole_kidman', 'nicole@example.com', 54, 142000.00, true),
    ('oscar_isaac', 'oscar_i@example.com', 42, 98000.00, true),
    ('pedro_pascal', 'pedro@example.com', 46, 115000.00, false),
    ('queen_latifah', 'queen_l@example.com', 51, 108000.00, true),
    ('rami_malek', 'rami@example.com', 40, 95000.00, true),
    ('saoirse_ronan', 'saoirse@example.com', 28, 78000.00, true),
    ('tom_holland', 'tom_h@example.com', 25, 72000.00, true),
    ('dev_patel', 'dev@example.com', 31, 82000.00, true),
    ('florence_welch', 'florence_w@example.com', 35, 76000.00, false),
    ('gemma_chan', 'gemma@example.com', 38, 88000.00, true),
    ('hugh_jackman', 'hugh@example.com', 52, 145000.00, true),
    ('ian_mckellen', 'ian@example.com', 81, 125000.00, true);

-- ==========================================
-- 3. Populate UAT Data (Copy from Prod)
-- ==========================================
INSERT INTO uat.users (username, email, age, salary, is_active)
SELECT username, email, age, salary, is_active FROM prod.users;

-- Create products table for additional testing (Public schema)
CREATE TABLE IF NOT EXISTS public.products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    price NUMERIC(10, 2),
    stock_quantity INTEGER,
    is_available BOOLEAN DEFAULT true
);

-- Insert sample products (100+ records)
INSERT INTO public.products (name, category, price, stock_quantity, is_available) VALUES
    ('Laptop Pro', 'Electronics', 1299.99, 50, true),
    ('Wireless Mouse', 'Electronics', 29.99, 200, true),
    ('Office Chair', 'Furniture', 249.99, 30, true),
    ('Standing Desk', 'Furniture', 599.99, 15, true),
    ('Coffee Maker', 'Appliances', 89.99, NULL, false),
    ('Notebook Set', 'Stationery', 12.99, 500, true),
    ('Monitor 27"', 'Electronics', 349.99, 75, true),
    ('Keyboard RGB', 'Electronics', 79.99, 120, true),
    ('Desk Lamp LED', 'Furniture', 39.99, 85, true),
    ('USB Hub 7-Port', 'Electronics', 24.99, 150, true),
    ('Webcam HD', 'Electronics', 59.99, 90, false),
    ('Headphones Wireless', 'Electronics', 149.99, 60, true),
    ('Monitor Stand', 'Furniture', 49.99, 45, true),
    ('Cable Organizer', 'Accessories', 14.99, 300, true),
    ('Laptop Stand', 'Accessories', 34.99, 110, true),
    ('Power Strip', 'Electronics', 19.99, 200, false),
    ('Air Purifier', 'Appliances', 199.99, 25, true),
    ('Desk Mat XL', 'Accessories', 29.99, 180, true),
    ('Mechanical Keyboard', 'Electronics', 129.99, 55, true),
    ('Gaming Mouse', 'Electronics', 69.99, 95, true),
    ('Monitor Arm', 'Furniture', 89.99, 40, true),
    ('Wireless Charger', 'Electronics', 34.99, 175, false),
    ('Bluetooth Speaker', 'Electronics', 79.99, 85, true),
    ('Desk Drawer', 'Furniture', 59.99, 35, true),
    ('Whiteboard Small', 'Stationery', 24.99, 65, true),
    ('Pen Set Premium', 'Stationery', 19.99, 250, true),
    ('Sticky Notes Pack', 'Stationery', 8.99, 400, true),
    ('Paper Shredder', 'Appliances', 79.99, 20, false),
    ('Filing Cabinet', 'Furniture', 149.99, 18, true),
    ('Bookshelf Compact', 'Furniture', 89.99, 22, true),
    ('Footrest Ergonomic', 'Furniture', 44.99, 55, true),
    ('Wrist Rest', 'Accessories', 16.99, 160, true),
    ('Mousepad Large', 'Accessories', 12.99, 220, true),
    ('External SSD 1TB', 'Electronics', 109.99, 70, false),
    ('USB Flash Drive 64GB', 'Electronics', 14.99, 350, true),
    ('Ethernet Cable 10ft', 'Electronics', 9.99, 280, true),
    ('HDMI Cable 6ft', 'Electronics', 12.99, 190, true),
    ('DisplayPort Cable', 'Electronics', 15.99, 145, true),
    ('Surge Protector', 'Electronics', 29.99, 95, true),
    ('UPS Battery Backup', 'Electronics', 159.99, 30, false),
    ('Router WiFi 6', 'Electronics', 179.99, 45, true),
    ('Network Switch', 'Electronics', 49.99, 55, true),
    ('Printer Laser', 'Electronics', 299.99, 20, true),
    ('Scanner Portable', 'Electronics', 129.99, 35, true),
    ('Ink Cartridge Set', 'Stationery', 44.99, 120, false),
    ('Paper A4 Ream', 'Stationery', 7.99, 500, true),
    ('Stapler Heavy Duty', 'Stationery', 18.99, 85, true),
    ('Paper Clips Box', 'Stationery', 3.99, 600, true),
    ('Binder Clips Assorted', 'Stationery', 6.99, 450, true),
    ('Folder Set', 'Stationery', 11.99, 200, true),
    ('Label Maker', 'Stationery', 39.99, 65, false),
    ('Calculator Scientific', 'Stationery', 24.99, 110, true),
    ('Desk Calendar', 'Stationery', 14.99, 180, true),
    ('Planner 2024', 'Stationery', 19.99, 150, true),
    ('Envelope Pack', 'Stationery', 9.99, 280, true),
    ('Tape Dispenser', 'Stationery', 8.99, 195, true),
    ('Scissors Set', 'Stationery', 12.99, 160, false),
    ('Ruler Set', 'Stationery', 5.99, 300, true),
    ('Correction Tape', 'Stationery', 4.99, 400, true),
    ('Highlighter Set', 'Stationery', 7.99, 350, true),
    ('Marker Set', 'Stationery', 11.99, 275, true),
    ('Pencil Case', 'Stationery', 9.99, 220, true),
    ('Eraser Pack', 'Stationery', 3.99, 450, false),
    ('Sharpener Electric', 'Stationery', 19.99, 75, true),
    ('Desk Organizer', 'Furniture', 34.99, 90, true),
    ('Magazine Holder', 'Furniture', 16.99, 110, true),
    ('Wall Clock', 'Furniture', 29.99, 65, true),
    ('Trash Can Small', 'Furniture', 14.99, 140, true),
    ('Plant Pot Set', 'Furniture', 24.99, 85, false),
    ('Photo Frame Set', 'Furniture', 19.99, 120, true),
    ('Cork Board', 'Furniture', 22.99, 55, true),
    ('Bulletin Board', 'Furniture', 34.99, 40, true),
    ('Coat Rack', 'Furniture', 44.99, 25, true),
    ('Umbrella Stand', 'Furniture', 29.99, 35, true),
    ('Door Mat', 'Furniture', 19.99, 75, false),
    ('Cushion Set', 'Furniture', 39.99, 50, true),
    ('Throw Blanket', 'Furniture', 34.99, 60, true),
    ('Curtains Set', 'Furniture', 49.99, 40, true),
    ('Rug Small', 'Furniture', 59.99, 30, true),
    ('Mirror Wall', 'Furniture', 44.99, 25, true),
    ('Kettle Electric', 'Appliances', 34.99, 95, false),
    ('Toaster 2-Slice', 'Appliances', 29.99, 80, true),
    ('Microwave Compact', 'Appliances', 89.99, 35, true),
    ('Mini Fridge', 'Appliances', 149.99, 20, true),
    ('Blender', 'Appliances', 49.99, 55, true),
    ('Food Processor', 'Appliances', 99.99, 30, true),
    ('Hand Mixer', 'Appliances', 24.99, 70, false),
    ('Rice Cooker', 'Appliances', 44.99, 45, true),
    ('Slow Cooker', 'Appliances', 59.99, 35, true),
    ('Pressure Cooker', 'Appliances', 89.99, 25, true),
    ('Air Fryer', 'Appliances', 99.99, 40, true),
    ('Grill Electric', 'Appliances', 79.99, 30, true),
    ('Waffle Maker', 'Appliances', 34.99, 50, false),
    ('Sandwich Maker', 'Appliances', 24.99, 65, true),
    ('Juicer', 'Appliances', 69.99, 35, true),
    ('Espresso Machine', 'Appliances', 199.99, 20, true),
    ('Water Dispenser', 'Appliances', 129.99, 15, true),
    ('Ice Maker', 'Appliances', 159.99, 18, true),
    ('Fan Desk', 'Appliances', 29.99, 100, false),
    ('Heater Portable', 'Appliances', 49.99, 45, true),
    ('Humidifier', 'Appliances', 44.99, 55, true),
    ('Dehumidifier', 'Appliances', 149.99, 25, true),
    ('Vacuum Handheld', 'Appliances', 79.99, 40, true),
    ('Steam Iron', 'Appliances', 39.99, 60, true),
    ('Sewing Machine', 'Appliances', 199.99, 15, false),
    ('Gaming Chair', 'Furniture', 299.99, 25, true),
    ('Ergonomic Chair Pro', 'Furniture', 449.99, 18, true),
    ('L-Shaped Desk', 'Furniture', 399.99, 12, true),
    ('Adjustable Desk', 'Furniture', 549.99, 20, true),
    ('Conference Table', 'Furniture', 799.99, 8, true);

-- Verify data
SELECT 'prod.users' as table_name, COUNT(*) as row_count FROM prod.users
UNION ALL
SELECT 'uat.users' as table_name, COUNT(*) as row_count FROM uat.users
UNION ALL
SELECT 'public.products' as table_name, COUNT(*) as row_count FROM public.products;
