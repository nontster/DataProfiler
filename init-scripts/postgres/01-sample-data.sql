-- Sample data for testing DataProfiler
-- This script runs automatically when PostgreSQL container starts

-- Create schemas
CREATE SCHEMA IF NOT EXISTS prod;
CREATE SCHEMA IF NOT EXISTS uat;

-- ==========================================
-- 1. Production Environment (Golden Schema)
-- ==========================================

-- prod.users
CREATE TABLE IF NOT EXISTS prod.users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL,
    age INTEGER,
    salary NUMERIC(10, 2),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Production Users Indexes
CREATE INDEX IF NOT EXISTS idx_users_username ON prod.users(username);
CREATE INDEX IF NOT EXISTS idx_users_age_salary ON prod.users(age, salary);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON prod.users(email);

-- prod.products
CREATE TABLE IF NOT EXISTS prod.products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    price NUMERIC(10, 2),
    stock_quantity INTEGER,
    is_available BOOLEAN DEFAULT true
);

-- Production Products Indexes
CREATE INDEX IF NOT EXISTS idx_products_category ON prod.products(category);
CREATE INDEX IF NOT EXISTS idx_products_price ON prod.products(price);


-- ==========================================
-- 2. UAT Environment (Simulated Drift)
-- ==========================================

-- uat.users (schema drifts from prod.users)
CREATE TABLE IF NOT EXISTS uat.users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL,

    -- Drift: different length
    email VARCHAR(150),

    -- Drift: nullable in UAT (vs NOT NULL implicitly by data pattern in Prod)
    age INTEGER,

    -- Drift: different precision
    salary NUMERIC(12, 2),

    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Drift: Extra column in UAT
    middle_name VARCHAR(50)
);

-- UAT Users Indexes
-- Drift: Missing index on username
CREATE INDEX IF NOT EXISTS idx_users_age_salary ON uat.users(age, salary);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON uat.users(email);

-- uat.products (schema drifts from prod.products)
CREATE TABLE IF NOT EXISTS uat.products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,

    -- Drift: different length
    category VARCHAR(80),

    -- Drift: different precision
    price NUMERIC(12, 4),

    stock_quantity INTEGER,
    is_available BOOLEAN DEFAULT true,

    -- Drift: Extra column in UAT
    sku VARCHAR(30),

    -- Drift: Extra column in UAT
    discount_percent NUMERIC(5, 2)
);

-- UAT Products Indexes
-- Drift: Missing index on price
CREATE INDEX IF NOT EXISTS idx_products_category ON uat.products(category);


-- ==========================================
-- 3. Populate PROD Data
-- ==========================================

-- Production Users (99 records — established employees)
INSERT INTO prod.users (username, email, age, salary, is_active) VALUES
    ('john_doe', 'john@company.com', 35, 75000.00, true),
    ('jane_smith', 'jane@company.com', 42, 92000.00, true),
    ('bob_wilson', 'bob@company.com', 51, 105000.00, true),
    ('alice_johnson', 'alice@company.com', 38, 82000.00, true),
    ('charlie_brown', 'charlie@company.com', 45, 98000.00, true),
    ('diana_prince', 'diana@company.com', 39, NULL, true),
    ('edward_stark', 'edward@company.com', 55, 130000.00, true),
    ('fiona_green', 'fiona@company.com', 33, 68000.00, true),
    ('george_lucas', 'george@company.com', 48, 115000.00, true),
    ('hannah_montana', 'hannah@company.com', 29, 58000.00, true),
    ('ivan_petrov', 'ivan@company.com', 44, 88000.00, true),
    ('julia_roberts', 'julia@company.com', 41, 95000.00, true),
    ('kevin_hart', 'kevin@company.com', 36, 72000.00, false),
    ('laura_palmer', 'laura@company.com', 32, 64000.00, true),
    ('mike_tyson', 'mike@company.com', 50, 108000.00, true),
    ('nancy_drew', 'nancy@company.com', 28, 55000.00, true),
    ('oscar_wilde', 'oscar@company.com', 46, 99000.00, false),
    ('paula_abdul', 'paula@company.com', 43, 86000.00, true),
    ('quentin_beck', 'quentin@company.com', 37, 76000.00, true),
    ('rachel_green', 'rachel@company.com', 34, 70000.00, true),
    ('steve_rogers', 'steve@company.com', 40, 91000.00, true),
    ('tina_turner', 'tina@company.com', 47, 102000.00, false),
    ('ulrich_stern', 'ulrich@company.com', 39, 79000.00, true),
    ('victoria_secret', 'victoria@company.com', 36, 74000.00, true),
    ('walter_white', 'walter@company.com', 52, 125000.00, true),
    ('xena_warrior', 'xena@company.com', 33, 66000.00, false),
    ('yuri_gagarin', 'yuri@company.com', 45, 97000.00, true),
    ('zara_larsson', 'zara@company.com', 27, 52000.00, true),
    ('adam_levine', 'adam@company.com', 41, 93000.00, true),
    ('betty_white', 'betty@company.com', 58, 115000.00, true),
    ('carl_sagan', 'carl@company.com', 49, 106000.00, false),
    ('debbie_harry', 'debbie@company.com', 38, 82000.00, true),
    ('elvis_presley', 'elvis@company.com', 44, NULL, true),
    ('frank_sinatra', 'frank@company.com', 53, 132000.00, true),
    ('greta_thunberg', 'greta@company.com', 25, 48000.00, true),
    ('henry_ford', 'henry@company.com', 57, 148000.00, false),
    ('iris_west', 'iris@company.com', 31, 62000.00, true),
    ('james_bond', 'james@company.com', 46, 118000.00, true),
    ('kate_middleton', 'kate@company.com', 40, 95000.00, true),
    ('leonardo_dicaprio', 'leonardo@company.com', 48, 140000.00, true),
    ('madonna_ciccone', 'madonna@company.com', 54, 112000.00, false),
    ('neil_armstrong', 'neil@company.com', NULL, 105000.00, true),
    ('oprah_winfrey', 'oprah@company.com', 59, 185000.00, true),
    ('peter_parker', 'peter@company.com', 26, 54000.00, true),
    ('queen_elizabeth', 'queen@company.com', 65, 210000.00, true),
    ('robert_downey', 'robert@company.com', 50, 148000.00, false),
    ('sandra_bullock', 'sandra@company.com', 49, 125000.00, true),
    ('tom_hanks', 'tom@company.com', 56, 138000.00, true),
    ('uma_thurman', 'uma@company.com', 45, 102000.00, true),
    ('vin_diesel', 'vin@company.com', 48, 115000.00, true),
    ('will_smith', 'will@company.com', 52, 142000.00, false),
    ('xavier_charles', 'xavier@company.com', 60, 158000.00, true),
    ('yoko_ono', 'yoko@company.com', 62, 108000.00, true),
    ('zack_snyder', 'zack@company.com', 47, 118000.00, true),
    ('amy_adams', 'amy@company.com', 43, 92000.00, true),
    ('brad_pitt', 'brad@company.com', 54, 155000.00, false),
    ('cate_blanchett', 'cate@company.com', 46, 138000.00, true),
    ('denzel_washington', 'denzel@company.com', 59, 172000.00, true),
    ('emma_watson', 'emma@company.com', 32, 85000.00, true),
    ('faye_dunaway', 'faye@company.com', 63, 98000.00, true),
    ('gary_oldman', 'gary@company.com', 56, 128000.00, false),
    ('helen_mirren', 'helen@company.com', 65, 115000.00, true),
    ('idris_elba', 'idris@company.com', 49, 122000.00, true),
    ('jennifer_lawrence', 'jennifer@company.com', 31, 102000.00, true),
    ('keanu_reeves', 'keanu@company.com', 53, 145000.00, true),
    ('lupita_nyongo', 'lupita@company.com', 38, 88000.00, false),
    ('morgan_freeman', 'morgan@company.com', 72, 192000.00, true),
    ('natalie_portman', 'natalie@company.com', 40, 105000.00, true),
    ('olivia_colman', 'olivia@company.com', 47, 112000.00, true),
    ('patrick_stewart', 'patrick@company.com', 68, 148000.00, true),
    ('ryan_gosling', 'ryan@company.com', 41, 125000.00, true),
    ('scarlett_johansson', 'scarlett@company.com', 37, 135000.00, true),
    ('timothee_chalamet', 'timothee@company.com', 27, 72000.00, true),
    ('viola_davis', 'viola@company.com', 55, 122000.00, false),
    ('woody_harrelson', 'woody@company.com', 59, 115000.00, true),
    ('gemma_chan', 'gemma@company.com', 39, 92000.00, true),
    ('hugh_jackman', 'hugh@company.com', 53, 152000.00, true),
    ('ian_mckellen', 'ian@company.com', 81, 135000.00, true),
    ('andrew_garfield', 'andrew@company.com', 38, 98000.00, false),
    ('benedict_cumberbatch', 'benedict@company.com', 45, 132000.00, true),
    ('chris_hemsworth', 'chris@company.com', 39, 140000.00, true),
    ('dakota_johnson', 'dakota@company.com', 33, 78000.00, true),
    ('elizabeth_olsen', 'elizabeth@company.com', 34, 92000.00, true),
    ('florence_pugh', 'florence@company.com', 28, 68000.00, false),
    ('gal_gadot', 'gal@company.com', 37, 125000.00, true),
    ('hailee_steinfeld', 'hailee@company.com', 26, 62000.00, true),
    ('jake_gyllenhaal', 'jake@company.com', 42, 118000.00, true),
    ('kate_winslet', 'kate_w@company.com', 46, 132000.00, false),
    ('margot_robbie', 'margot@company.com', 33, 115000.00, true),
    ('nicole_kidman', 'nicole@company.com', 55, 148000.00, true),
    ('oscar_isaac', 'oscar_i@company.com', 43, 105000.00, true),
    ('pedro_pascal', 'pedro@company.com', 47, 122000.00, false),
    ('rami_malek', 'rami@company.com', 41, 102000.00, true),
    ('saoirse_ronan', 'saoirse@company.com', 29, 82000.00, true),
    ('tom_holland', 'tom_h@company.com', 27, 78000.00, true),
    ('dev_patel', 'dev@company.com', 33, 88000.00, true),
    ('leslie_mann', 'leslie@company.com', 49, 95000.00, true),
    ('queen_latifah', 'queen_l@company.com', 52, 115000.00, true),
    ('imelda_staunton', 'imelda@company.com', 64, 98000.00, true);

-- Production Products (111 records — full catalog)
INSERT INTO prod.products (name, category, price, stock_quantity, is_available) VALUES
    ('Laptop Pro 16', 'Electronics', 1499.99, 50, true),
    ('Laptop Air 13', 'Electronics', 999.99, 75, true),
    ('Wireless Mouse Pro', 'Electronics', 49.99, 200, true),
    ('Wireless Mouse Basic', 'Electronics', 19.99, 350, true),
    ('Office Chair Standard', 'Furniture', 249.99, 30, true),
    ('Office Chair Executive', 'Furniture', 499.99, 15, true),
    ('Standing Desk Electric', 'Furniture', 699.99, 20, true),
    ('Coffee Maker Drip', 'Appliances', 89.99, 60, true),
    ('Coffee Maker Espresso', 'Appliances', 299.99, 25, true),
    ('Notebook Set Premium', 'Stationery', 18.99, 500, true),
    ('Monitor 27" 4K', 'Electronics', 449.99, 45, true),
    ('Monitor 32" Curved', 'Electronics', 599.99, 30, true),
    ('Keyboard Mechanical', 'Electronics', 129.99, 120, true),
    ('Keyboard Wireless', 'Electronics', 59.99, 180, true),
    ('Desk Lamp LED Pro', 'Furniture', 49.99, 85, true),
    ('USB Hub 7-Port', 'Electronics', 29.99, 150, true),
    ('Webcam 4K', 'Electronics', 99.99, 70, true),
    ('Headphones Wireless ANC', 'Electronics', 249.99, 40, true),
    ('Headphones Wired Studio', 'Electronics', 149.99, 55, true),
    ('Monitor Stand Bamboo', 'Furniture', 59.99, 45, true),
    ('Cable Organizer Set', 'Accessories', 14.99, 300, true),
    ('Laptop Stand Aluminum', 'Accessories', 44.99, 110, true),
    ('Power Strip Smart', 'Electronics', 34.99, 200, true),
    ('Air Purifier HEPA', 'Appliances', 249.99, 25, true),
    ('Desk Mat XXL', 'Accessories', 34.99, 180, true),
    ('Gaming Mouse RGB', 'Electronics', 79.99, 95, true),
    ('Monitor Arm Dual', 'Furniture', 129.99, 35, true),
    ('Wireless Charger Qi', 'Electronics', 39.99, 175, true),
    ('Bluetooth Speaker Pro', 'Electronics', 99.99, 65, true),
    ('Desk Drawer Organizer', 'Furniture', 69.99, 35, true),
    ('Whiteboard 3x4', 'Stationery', 44.99, 40, true),
    ('Pen Set Executive', 'Stationery', 29.99, 250, true),
    ('Sticky Notes Mega Pack', 'Stationery', 12.99, 400, true),
    ('Paper Shredder Cross-Cut', 'Appliances', 99.99, 20, true),
    ('Filing Cabinet 3-Drawer', 'Furniture', 189.99, 18, true),
    ('Bookshelf 5-Tier', 'Furniture', 119.99, 22, true),
    ('Footrest Ergonomic Pro', 'Furniture', 54.99, 55, true),
    ('Wrist Rest Gel', 'Accessories', 19.99, 160, true),
    ('Mousepad XXL', 'Accessories', 16.99, 220, true),
    ('External SSD 1TB', 'Electronics', 109.99, 70, true),
    ('External SSD 2TB', 'Electronics', 179.99, 35, true),
    ('USB Flash Drive 128GB', 'Electronics', 19.99, 350, true),
    ('Ethernet Cable Cat6 10ft', 'Electronics', 12.99, 280, true),
    ('HDMI Cable 8K 6ft', 'Electronics', 19.99, 190, true),
    ('DisplayPort Cable 1.4', 'Electronics', 17.99, 145, true),
    ('Surge Protector 8-Outlet', 'Electronics', 39.99, 95, true),
    ('UPS Battery 1500VA', 'Electronics', 199.99, 25, true),
    ('Router WiFi 6E', 'Electronics', 229.99, 40, true),
    ('Network Switch 8-Port', 'Electronics', 59.99, 55, true),
    ('Printer Laser Color', 'Electronics', 399.99, 15, true),
    ('Scanner Flatbed', 'Electronics', 149.99, 30, true),
    ('Ink Cartridge Set XL', 'Stationery', 54.99, 120, true),
    ('Paper A4 Premium 5-Ream', 'Stationery', 34.99, 200, true),
    ('Stapler Electric', 'Stationery', 29.99, 85, true),
    ('Paper Clips Jumbo Box', 'Stationery', 5.99, 600, true),
    ('Folder Set Hanging', 'Stationery', 16.99, 200, true),
    ('Label Maker Pro', 'Stationery', 49.99, 50, true),
    ('Calculator Financial', 'Stationery', 34.99, 80, true),
    ('Planner Weekly', 'Stationery', 24.99, 150, true),
    ('Envelope Pack Business', 'Stationery', 12.99, 280, true),
    ('Tape Dispenser Heavy', 'Stationery', 12.99, 195, true),
    ('Scissors Professional', 'Stationery', 16.99, 160, true),
    ('Highlighter Set 12-Color', 'Stationery', 11.99, 350, true),
    ('Marker Whiteboard Set', 'Stationery', 14.99, 275, true),
    ('Pencil Mechanical Set', 'Stationery', 12.99, 220, true),
    ('Desk Organizer Bamboo', 'Furniture', 44.99, 90, true),
    ('Magazine Rack Wall', 'Furniture', 24.99, 110, true),
    ('Wall Clock Modern', 'Furniture', 39.99, 65, true),
    ('Trash Can Smart', 'Furniture', 49.99, 50, true),
    ('Plant Pot Ceramic Set', 'Furniture', 34.99, 85, true),
    ('Photo Frame Digital', 'Furniture', 59.99, 40, true),
    ('Cork Board XL', 'Furniture', 34.99, 55, true),
    ('Coat Rack Standing', 'Furniture', 54.99, 25, true),
    ('Cushion Lumbar Support', 'Furniture', 44.99, 70, true),
    ('Rug Anti-Fatigue', 'Furniture', 69.99, 30, true),
    ('Kettle Smart', 'Appliances', 49.99, 95, true),
    ('Toaster 4-Slice', 'Appliances', 49.99, 60, true),
    ('Microwave Inverter', 'Appliances', 149.99, 30, true),
    ('Mini Fridge 3.5cu', 'Appliances', 189.99, 20, true),
    ('Blender Pro', 'Appliances', 79.99, 45, true),
    ('Food Processor 12-Cup', 'Appliances', 129.99, 25, true),
    ('Hand Mixer 5-Speed', 'Appliances', 34.99, 70, true),
    ('Rice Cooker Digital', 'Appliances', 59.99, 45, true),
    ('Slow Cooker 6-Quart', 'Appliances', 69.99, 35, true),
    ('Pressure Cooker Electric', 'Appliances', 119.99, 25, true),
    ('Air Fryer XL', 'Appliances', 129.99, 40, true),
    ('Grill Indoor Electric', 'Appliances', 99.99, 30, true),
    ('Waffle Maker Belgian', 'Appliances', 44.99, 50, true),
    ('Juicer Cold Press', 'Appliances', 89.99, 30, true),
    ('Water Dispenser Hot/Cold', 'Appliances', 159.99, 15, true),
    ('Ice Maker Countertop', 'Appliances', 179.99, 18, true),
    ('Fan Tower', 'Appliances', 49.99, 80, true),
    ('Heater Ceramic', 'Appliances', 59.99, 45, true),
    ('Humidifier Ultrasonic', 'Appliances', 54.99, 55, true),
    ('Dehumidifier 30-Pint', 'Appliances', 179.99, 20, true),
    ('Vacuum Robot', 'Appliances', 299.99, 25, true),
    ('Steam Iron Professional', 'Appliances', 49.99, 60, true),
    ('Gaming Chair Racing', 'Furniture', 349.99, 25, true),
    ('Ergonomic Chair Mesh', 'Furniture', 549.99, 18, true),
    ('L-Shaped Desk Oak', 'Furniture', 449.99, 12, true),
    ('Adjustable Desk Bamboo', 'Furniture', 649.99, 20, true),
    ('Conference Table 8ft', 'Furniture', 899.99, 8, true),
    ('Webcam Ring Light', 'Electronics', 39.99, 100, true),
    ('USB-C Dock 12-in-1', 'Electronics', 79.99, 65, true),
    ('Tablet Stand Adjustable', 'Accessories', 29.99, 130, true),
    ('Screen Protector Kit', 'Accessories', 14.99, 250, true),
    ('Cleaning Kit Electronics', 'Accessories', 19.99, 180, true),
    ('Backpack Laptop 17"', 'Accessories', 59.99, 75, true),
    ('Sleeve Laptop 15"', 'Accessories', 24.99, 120, true),
    ('Docking Station USB4', 'Electronics', 199.99, 30, true),
    ('Smart Plug WiFi 4-Pack', 'Electronics', 29.99, 150, true);


-- ==========================================
-- 4. Populate UAT Data (different dataset)
-- ==========================================

-- UAT Users (80 records — mix of new hires, different salaries, more NULLs)
INSERT INTO uat.users (username, email, age, salary, is_active, middle_name) VALUES
    ('john_doe', 'john@testmail.io', 35, 72000.00, true, NULL),
    ('jane_smith', 'jane@testmail.io', 42, 89000.00, true, 'Marie'),
    ('bob_wilson', 'bob@testmail.io', 51, 102000.00, true, NULL),
    ('alice_johnson', 'alice@testmail.io', 38, 79000.00, false, 'Grace'),
    ('charlie_brown', 'charlie@testmail.io', NULL, 95000.00, true, NULL),
    ('diana_prince', 'diana@testmail.io', 39, NULL, true, 'Athena'),
    ('edward_stark', 'edward@testmail.io', 55, 128000.00, true, NULL),
    ('fiona_green', 'fiona@testmail.io', 33, 65000.00, false, NULL),
    ('george_lucas', 'george@testmail.io', 48, 112000.00, true, 'Walton'),
    ('hannah_montana', 'hannah@testmail.io', 29, 55000.00, true, NULL),
    ('kevin_hart', 'kevin@testmail.io', 36, 70000.00, true, 'Darnell'),
    ('laura_palmer', 'laura@testmail.io', 32, 61000.00, true, NULL),
    ('mike_tyson', 'mike@testmail.io', 50, 105000.00, true, 'Gerard'),
    ('nancy_drew', 'nancy@testmail.io', 28, 53000.00, true, NULL),
    ('oscar_wilde', 'oscar@testmail.io', NULL, 96000.00, false, 'Fingal'),
    ('rachel_green', 'rachel@testmail.io', 34, 68000.00, true, 'Karen'),
    ('steve_rogers', 'steve@testmail.io', 40, 88000.00, true, 'Grant'),
    ('tina_turner', 'tina@testmail.io', 47, 99000.00, false, NULL),
    ('walter_white', 'walter@testmail.io', 52, 122000.00, true, 'Hartwell'),
    ('yuri_gagarin', 'yuri@testmail.io', 45, 94000.00, true, NULL),
    ('adam_levine', 'adam@testmail.io', 41, 90000.00, true, 'Noah'),
    ('betty_white', 'betty@testmail.io', 58, 112000.00, true, NULL),
    ('carl_sagan', 'carl@testmail.io', NULL, 103000.00, false, 'Edward'),
    ('frank_sinatra', 'frank@testmail.io', 53, 130000.00, true, 'Albert'),
    ('greta_thunberg', 'greta@testmail.io', 25, 46000.00, true, NULL),
    ('henry_ford', 'henry@testmail.io', 57, 145000.00, true, NULL),
    ('iris_west', 'iris@testmail.io', 31, 60000.00, true, 'Ann'),
    ('james_bond', 'james@testmail.io', 46, 115000.00, true, NULL),
    ('kate_middleton', 'kate@testmail.io', 40, 92000.00, true, NULL),
    ('leonardo_dicaprio', 'leonardo@testmail.io', 48, 138000.00, true, 'Wilhelm'),
    ('oprah_winfrey', 'oprah@testmail.io', 59, 180000.00, true, 'Gail'),
    ('peter_parker', 'peter@testmail.io', 26, 52000.00, true, 'Benjamin'),
    ('tom_hanks', 'tom@testmail.io', 56, 135000.00, true, 'Jeffrey'),
    ('uma_thurman', 'uma@testmail.io', 45, 100000.00, true, 'Karuna'),
    ('vin_diesel', 'vin@testmail.io', 48, 112000.00, true, NULL),
    ('will_smith', 'will@testmail.io', NULL, 140000.00, false, 'Carroll'),
    ('xavier_charles', 'xavier@testmail.io', 60, 155000.00, true, NULL),
    ('amy_adams', 'amy@testmail.io', 43, 89000.00, true, 'Lou'),
    ('brad_pitt', 'brad@testmail.io', 54, 152000.00, false, 'William'),
    ('cate_blanchett', 'cate@testmail.io', 46, 135000.00, true, NULL),
    ('emma_watson', 'emma@testmail.io', 32, 82000.00, true, 'Charlotte'),
    ('gary_oldman', 'gary@testmail.io', 56, 125000.00, false, 'Leonard'),
    ('helen_mirren', 'helen@testmail.io', 65, 112000.00, true, NULL),
    ('idris_elba', 'idris@testmail.io', 49, 119000.00, true, NULL),
    ('jennifer_lawrence', 'jennifer@testmail.io', 31, 99000.00, true, 'Shrader'),
    ('keanu_reeves', 'keanu@testmail.io', 53, 142000.00, true, 'Charles'),
    ('morgan_freeman', 'morgan@testmail.io', 72, 188000.00, true, NULL),
    ('natalie_portman', 'natalie@testmail.io', 40, 102000.00, true, NULL),
    ('olivia_colman', 'olivia@testmail.io', NULL, 109000.00, true, 'Sarah'),
    ('patrick_stewart', 'patrick@testmail.io', 68, 145000.00, true, NULL),
    ('ryan_gosling', 'ryan@testmail.io', 41, 122000.00, true, 'Thomas'),
    ('scarlett_johansson', 'scarlett@testmail.io', 37, 132000.00, true, 'Ingrid'),
    ('viola_davis', 'viola@testmail.io', 55, 119000.00, false, NULL),
    ('gemma_chan', 'gemma@testmail.io', 39, 89000.00, true, NULL),
    ('hugh_jackman', 'hugh@testmail.io', 53, 149000.00, true, 'Michael'),
    ('chris_hemsworth', 'chris@testmail.io', 39, 137000.00, true, NULL),
    ('elizabeth_olsen', 'elizabeth@testmail.io', 34, 89000.00, true, 'Chase'),
    ('gal_gadot', 'gal@testmail.io', 37, 122000.00, true, NULL),
    ('margot_robbie', 'margot@testmail.io', 33, 112000.00, true, 'Elise'),
    ('nicole_kidman', 'nicole@testmail.io', 55, 145000.00, true, 'Mary'),
    -- UAT-only users (new hires not yet in prod)
    ('new_hire_01', 'newhire01@testmail.io', 24, 42000.00, true, NULL),
    ('new_hire_02', 'newhire02@testmail.io', 22, 40000.00, true, 'James'),
    ('new_hire_03', 'newhire03@testmail.io', 26, 45000.00, true, NULL),
    ('new_hire_04', 'newhire04@testmail.io', 23, NULL, true, NULL),
    ('new_hire_05', 'newhire05@testmail.io', NULL, 43000.00, false, 'Test'),
    ('intern_alpha', 'intern_a@testmail.io', 20, 28000.00, true, NULL),
    ('intern_beta', 'intern_b@testmail.io', 21, 28000.00, true, NULL),
    ('contractor_01', 'contract01@testmail.io', 35, NULL, true, NULL),
    ('contractor_02', 'contract02@testmail.io', 40, NULL, true, 'External'),
    ('temp_user_01', 'temp01@testmail.io', NULL, 35000.00, true, NULL),
    ('test_admin', 'admin@testmail.io', 30, 65000.00, true, 'Admin'),
    ('qa_tester', 'qa@testmail.io', 28, 55000.00, true, NULL),
    ('dev_tester', 'dev_test@testmail.io', 32, 62000.00, true, NULL),
    ('staging_user', 'staging@testmail.io', NULL, NULL, false, 'Staging'),
    ('demo_account', 'demo@testmail.io', 25, 50000.00, true, NULL),
    ('load_test_01', 'loadtest01@testmail.io', NULL, NULL, true, NULL),
    ('load_test_02', 'loadtest02@testmail.io', NULL, NULL, true, NULL),
    ('load_test_03', 'loadtest03@testmail.io', NULL, NULL, true, 'Perf'),
    ('smoke_test', 'smoke@testmail.io', 30, 55000.00, true, NULL),
    ('regression_user', 'regression@testmail.io', 28, 52000.00, true, 'QA');


-- UAT Products (90 records — subset catalog with different prices, more out-of-stock)
INSERT INTO uat.products (name, category, price, stock_quantity, is_available, sku, discount_percent) VALUES
    ('Laptop Pro 16', 'Electronics', 1399.9900, 30, true, 'ELEC-LP16-001', 5.00),
    ('Laptop Air 13', 'Electronics', 949.9900, 45, true, 'ELEC-LA13-002', 8.00),
    ('Wireless Mouse Pro', 'Electronics', 44.9900, 150, true, 'ELEC-WMP-003', NULL),
    ('Wireless Mouse Basic', 'Electronics', 17.9900, 200, true, 'ELEC-WMB-004', 10.00),
    ('Office Chair Standard', 'Furniture', 229.9900, 20, true, 'FURN-OCS-005', NULL),
    ('Office Chair Executive', 'Furniture', 469.9900, 8, false, 'FURN-OCE-006', 5.00),
    ('Standing Desk Electric', 'Furniture', 649.9900, 12, true, 'FURN-SDE-007', NULL),
    ('Coffee Maker Drip', 'Appliances', 79.9900, NULL, false, 'APPL-CMD-008', 15.00),
    ('Coffee Maker Espresso', 'Appliances', 279.9900, 15, true, 'APPL-CME-009', 10.00),
    ('Notebook Set Premium', 'Stationery', 16.9900, 300, true, 'STAT-NSP-010', NULL),
    ('Monitor 27" 4K', 'Electronics', 419.9900, 25, true, 'ELEC-M27-011', 5.00),
    ('Monitor 32" Curved', 'Electronics', 569.9900, 18, true, 'ELEC-M32-012', NULL),
    ('Keyboard Mechanical', 'Electronics', 119.9900, 80, true, 'ELEC-KM-013', NULL),
    ('Keyboard Wireless', 'Electronics', 54.9900, 120, true, 'ELEC-KW-014', 10.00),
    ('Desk Lamp LED Pro', 'Furniture', 44.9900, 50, true, 'FURN-DLP-015', NULL),
    ('USB Hub 7-Port', 'Electronics', 27.9900, 100, true, 'ELEC-UH7-016', 5.00),
    ('Webcam 4K', 'Electronics', 89.9900, 40, false, 'ELEC-WC4-017', 10.00),
    ('Headphones Wireless ANC', 'Electronics', 229.9900, 25, true, 'ELEC-HWA-018', NULL),
    ('Monitor Stand Bamboo', 'Furniture', 54.9900, 30, true, 'FURN-MSB-019', NULL),
    ('Cable Organizer Set', 'Accessories', 12.9900, 200, true, 'ACCS-COS-020', NULL),
    ('Laptop Stand Aluminum', 'Accessories', 39.9900, 75, true, 'ACCS-LSA-021', 5.00),
    ('Air Purifier HEPA', 'Appliances', 229.9900, 15, true, 'APPL-APH-022', NULL),
    ('Desk Mat XXL', 'Accessories', 29.9900, 120, true, 'ACCS-DMX-023', NULL),
    ('Gaming Mouse RGB', 'Electronics', 74.9900, 60, true, 'ELEC-GMR-024', NULL),
    ('Monitor Arm Dual', 'Furniture', 119.9900, 20, true, 'FURN-MAD-025', 5.00),
    ('Wireless Charger Qi', 'Electronics', 34.9900, 100, false, 'ELEC-WCQ-026', 15.00),
    ('Bluetooth Speaker Pro', 'Electronics', 94.9900, 40, true, 'ELEC-BSP-027', NULL),
    ('Whiteboard 3x4', 'Stationery', 39.9900, 25, true, 'STAT-WB3-028', NULL),
    ('Pen Set Executive', 'Stationery', 27.9900, 180, true, 'STAT-PSE-029', NULL),
    ('Paper Shredder Cross-Cut', 'Appliances', 89.9900, 12, false, 'APPL-PSC-030', 10.00),
    ('Filing Cabinet 3-Drawer', 'Furniture', 179.9900, 10, true, 'FURN-FC3-031', NULL),
    ('Bookshelf 5-Tier', 'Furniture', 109.9900, 15, true, 'FURN-BS5-032', NULL),
    ('External SSD 1TB', 'Electronics', 99.9900, 45, true, 'ELEC-ES1-033', 10.00),
    ('External SSD 2TB', 'Electronics', 169.9900, 20, true, 'ELEC-ES2-034', NULL),
    ('USB Flash Drive 128GB', 'Electronics', 17.9900, 250, true, 'ELEC-UFD-035', NULL),
    ('HDMI Cable 8K 6ft', 'Electronics', 17.9900, 130, true, 'ELEC-HC8-036', NULL),
    ('Surge Protector 8-Outlet', 'Electronics', 37.9900, 60, true, 'ELEC-SP8-037', 5.00),
    ('UPS Battery 1500VA', 'Electronics', 189.9900, 15, false, 'ELEC-UPS-038', NULL),
    ('Router WiFi 6E', 'Electronics', 219.9900, 25, true, 'ELEC-RW6-039', NULL),
    ('Printer Laser Color', 'Electronics', 379.9900, 8, true, 'ELEC-PLC-040', 5.00),
    ('Scanner Flatbed', 'Electronics', 139.9900, 18, true, 'ELEC-SF-041', NULL),
    ('Ink Cartridge Set XL', 'Stationery', 49.9900, 80, false, 'STAT-ICS-042', 10.00),
    ('Paper A4 Premium 5-Ream', 'Stationery', 32.9900, 150, true, 'STAT-PA4-043', NULL),
    ('Highlighter Set 12-Color', 'Stationery', 10.9900, 250, true, 'STAT-HS12-044', NULL),
    ('Marker Whiteboard Set', 'Stationery', 13.9900, 200, true, 'STAT-MWS-045', NULL),
    ('Desk Organizer Bamboo', 'Furniture', 42.9900, 60, true, 'FURN-DOB-046', NULL),
    ('Wall Clock Modern', 'Furniture', 37.9900, 40, true, 'FURN-WCM-047', NULL),
    ('Trash Can Smart', 'Furniture', 47.9900, 30, true, 'FURN-TCS-048', 5.00),
    ('Plant Pot Ceramic Set', 'Furniture', 32.9900, 55, false, 'FURN-PPC-049', NULL),
    ('Cork Board XL', 'Furniture', 32.9900, 35, true, 'FURN-CBX-050', NULL),
    ('Kettle Smart', 'Appliances', 46.9900, 60, true, 'APPL-KS-051', 5.00),
    ('Toaster 4-Slice', 'Appliances', 47.9900, 40, true, 'APPL-T4S-052', NULL),
    ('Microwave Inverter', 'Appliances', 139.9900, 18, true, 'APPL-MI-053', NULL),
    ('Mini Fridge 3.5cu', 'Appliances', 179.9900, 12, false, 'APPL-MF3-054', 5.00),
    ('Blender Pro', 'Appliances', 74.9900, 30, true, 'APPL-BP-055', NULL),
    ('Rice Cooker Digital', 'Appliances', 54.9900, 30, true, 'APPL-RCD-056', NULL),
    ('Air Fryer XL', 'Appliances', 119.9900, 25, true, 'APPL-AFX-057', NULL),
    ('Vacuum Robot', 'Appliances', 279.9900, 15, true, 'APPL-VR-058', 10.00),
    ('Gaming Chair Racing', 'Furniture', 329.9900, 15, true, 'FURN-GCR-059', 5.00),
    ('Ergonomic Chair Mesh', 'Furniture', 529.9900, 10, true, 'FURN-ECM-060', NULL),
    ('L-Shaped Desk Oak', 'Furniture', 429.9900, 8, false, 'FURN-LSD-061', NULL),
    ('Adjustable Desk Bamboo', 'Furniture', 629.9900, 12, true, 'FURN-ADB-062', 5.00),
    ('Conference Table 8ft', 'Furniture', 879.9900, 5, true, 'FURN-CT8-063', NULL),
    ('Webcam Ring Light', 'Electronics', 37.9900, 70, true, 'ELEC-WRL-064', NULL),
    ('USB-C Dock 12-in-1', 'Electronics', 74.9900, 40, true, 'ELEC-UCD-065', NULL),
    ('Tablet Stand Adjustable', 'Accessories', 27.9900, 90, true, 'ACCS-TSA-066', NULL),
    ('Cleaning Kit Electronics', 'Accessories', 17.9900, 130, true, 'ACCS-CKE-067', NULL),
    ('Backpack Laptop 17"', 'Accessories', 54.9900, 50, true, 'ACCS-BL17-068', 5.00),
    ('Docking Station USB4', 'Electronics', 189.9900, 18, true, 'ELEC-DSU-069', NULL),
    ('Smart Plug WiFi 4-Pack', 'Electronics', 27.9900, 100, true, 'ELEC-SPW-070', NULL),
    -- UAT-only products (testing new catalog items)
    ('VR Headset Pro', 'Electronics', 599.9900, 10, true, 'ELEC-VRP-071', NULL),
    ('AR Glasses Dev Kit', 'Electronics', 899.9900, 5, false, 'ELEC-ARG-072', 15.00),
    ('Smart Whiteboard 55"', 'Electronics', 2499.9900, 3, true, 'ELEC-SW55-073', NULL),
    ('Standing Mat Anti-Fatigue', 'Furniture', 79.9900, 40, true, 'FURN-SMA-074', NULL),
    ('Privacy Screen 27"', 'Accessories', 49.9900, 25, true, 'ACCS-PS27-075', 5.00),
    ('Noise Machine White', 'Appliances', 39.9900, 35, true, 'APPL-NMW-076', NULL),
    ('Desk Bike Under', 'Furniture', 199.9900, 8, true, 'FURN-DBU-077', NULL),
    ('Cable Management Tray', 'Accessories', 24.9900, 60, true, 'ACCS-CMT-078', NULL),
    ('Monitor Light Bar', 'Electronics', 44.9900, 45, true, 'ELEC-MLB-079', NULL),
    ('Acoustic Panel Set', 'Furniture', 89.9900, 20, true, 'FURN-APS-080', 10.00),
    ('Portable Projector Mini', 'Electronics', 349.9900, 12, true, 'ELEC-PPM-081', NULL),
    ('Wireless Presenter', 'Electronics', 29.9900, 80, true, 'ELEC-WP-082', NULL),
    ('Fidget Desk Toy Set', 'Accessories', 14.9900, 100, true, 'ACCS-FDT-083', NULL),
    ('Aroma Diffuser USB', 'Appliances', 24.9900, 50, true, 'APPL-ADU-084', NULL),
    ('Laptop Cooling Pad', 'Accessories', 34.9900, 55, true, 'ACCS-LCP-085', 5.00),
    ('Smart Lamp Color', 'Electronics', 59.9900, 30, true, 'ELEC-SLC-086', NULL),
    ('Document Camera HD', 'Electronics', 149.9900, 15, false, 'ELEC-DCH-087', 10.00),
    ('Keyboard Wrist Pad', 'Accessories', 19.9900, 90, true, 'ACCS-KWP-088', NULL),
    ('Webcam Cover Slide', 'Accessories', 4.9900, 500, true, 'ACCS-WCS-089', NULL),
    ('USB Desk Fan Mini', 'Appliances', 14.9900, 120, true, 'APPL-UDF-090', NULL);


-- Verify data
SELECT 'prod.users' as table_name, COUNT(*) as row_count FROM prod.users
UNION ALL
SELECT 'uat.users' as table_name, COUNT(*) as row_count FROM uat.users
UNION ALL
SELECT 'prod.products' as table_name, COUNT(*) as row_count FROM prod.products
UNION ALL
SELECT 'uat.products' as table_name, COUNT(*) as row_count FROM uat.products;
