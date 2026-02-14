#!/usr/bin/env python3
"""
Initialize MSSQL schema objects (stored procedures, views, triggers) with test data.
Creates objects in both prod and uat schemas with deliberate drift for comparison testing.
Run AFTER init-mssql.py

Usage: python init-scripts/mssql/init-mssql-schema-objects.py
"""

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


def run_sql(sql, database='testdb'):
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
    print("=" * 60)
    print("Creating MSSQL Schema Objects (Procedures, Views, Triggers)")
    print("=" * 60)

    # ==========================================
    # 1. PROD Schema Objects (Golden Standard)
    # ==========================================
    print("\n📦 Creating PROD stored procedures...")

    # Procedure: get user by ID
    run_sql("""
        IF OBJECT_ID('prod.get_user_by_id', 'P') IS NOT NULL DROP PROCEDURE prod.get_user_by_id;
    """)
    run_sql("""
        CREATE PROCEDURE prod.get_user_by_id @user_id INT
        AS
        BEGIN
            SELECT username, email, salary
            FROM prod.users
            WHERE id = @user_id;
        END
    """)
    print("   ✅ prod.get_user_by_id")

    # Procedure: get product stats
    run_sql("""
        IF OBJECT_ID('prod.get_product_stats', 'P') IS NOT NULL DROP PROCEDURE prod.get_product_stats;
    """)
    run_sql("""
        CREATE PROCEDURE prod.get_product_stats @category NVARCHAR(50) = NULL
        AS
        BEGIN
            SELECT category,
                   COUNT(*) AS product_count,
                   ROUND(AVG(price), 2) AS avg_price,
                   SUM(stock_quantity) AS total_stock
            FROM prod.products
            WHERE @category IS NULL OR category = @category
            GROUP BY category
            ORDER BY category;
        END
    """)
    print("   ✅ prod.get_product_stats")

    # Function: calculate average salary
    run_sql("""
        IF OBJECT_ID('prod.calc_avg_salary', 'FN') IS NOT NULL DROP FUNCTION prod.calc_avg_salary;
    """)
    run_sql("""
        CREATE FUNCTION prod.calc_avg_salary()
        RETURNS DECIMAL(10,2)
        AS
        BEGIN
            DECLARE @avg_sal DECIMAL(10,2);
            SELECT @avg_sal = ROUND(AVG(salary), 2)
            FROM prod.users
            WHERE salary IS NOT NULL AND is_active = 1;
            RETURN @avg_sal;
        END
    """)
    print("   ✅ prod.calc_avg_salary")

    # Procedure: deactivate user
    run_sql("""
        IF OBJECT_ID('prod.deactivate_user', 'P') IS NOT NULL DROP PROCEDURE prod.deactivate_user;
    """)
    run_sql("""
        CREATE PROCEDURE prod.deactivate_user @user_id INT
        AS
        BEGIN
            UPDATE prod.users SET is_active = 0 WHERE id = @user_id;
        END
    """)
    print("   ✅ prod.deactivate_user")

    # ---- PROD Views ----
    print("\n📦 Creating PROD views...")

    run_sql("""
        IF OBJECT_ID('prod.v_active_users', 'V') IS NOT NULL DROP VIEW prod.v_active_users;
    """)
    run_sql("""
        CREATE VIEW prod.v_active_users AS
        SELECT id, username, email, age, salary, created_at
        FROM prod.users
        WHERE is_active = 1;
    """)
    print("   ✅ prod.v_active_users")

    run_sql("""
        IF OBJECT_ID('prod.v_product_inventory', 'V') IS NOT NULL DROP VIEW prod.v_product_inventory;
    """)
    run_sql("""
        CREATE VIEW prod.v_product_inventory AS
        SELECT id, name, category, price, stock_quantity,
               CASE WHEN stock_quantity > 0 AND is_available = 1 THEN 'In Stock'
                    WHEN stock_quantity = 0 THEN 'Out of Stock'
                    ELSE 'Unavailable' END AS availability_status
        FROM prod.products;
    """)
    print("   ✅ prod.v_product_inventory")

    run_sql("""
        IF OBJECT_ID('prod.v_category_summary', 'V') IS NOT NULL DROP VIEW prod.v_category_summary;
    """)
    run_sql("""
        CREATE VIEW prod.v_category_summary AS
        SELECT category,
               COUNT(*) AS product_count,
               ROUND(AVG(price), 2) AS avg_price,
               SUM(stock_quantity) AS total_stock,
               SUM(CASE WHEN is_available = 1 THEN 1 ELSE 0 END) AS available_count
        FROM prod.products
        GROUP BY category;
    """)
    print("   ✅ prod.v_category_summary")

    # ---- PROD Triggers ----
    print("\n📦 Creating PROD triggers...")

    # Audit log table
    run_sql("""
        IF NOT EXISTS (SELECT * FROM sys.tables t JOIN sys.schemas s ON t.schema_id = s.schema_id
                       WHERE t.name = 'user_audit_log' AND s.name = 'prod')
        BEGIN
            CREATE TABLE prod.user_audit_log (
                id INT IDENTITY(1,1) PRIMARY KEY,
                user_id INT,
                action NVARCHAR(10),
                old_email NVARCHAR(100),
                new_email NVARCHAR(100),
                changed_at DATETIME2 DEFAULT GETDATE()
            );
        END
    """)

    run_sql("""
        IF OBJECT_ID('prod.trg_user_audit', 'TR') IS NOT NULL DROP TRIGGER prod.trg_user_audit;
    """)
    run_sql("""
        CREATE TRIGGER prod.trg_user_audit
        ON prod.users
        AFTER UPDATE
        AS
        BEGIN
            INSERT INTO prod.user_audit_log (user_id, action, old_email, new_email)
            SELECT i.id, 'UPDATE', d.email, i.email
            FROM inserted i
            JOIN deleted d ON i.id = d.id
            WHERE i.email <> d.email;
        END
    """)
    print("   ✅ prod.trg_user_audit")

    run_sql("""
        IF OBJECT_ID('prod.trg_validate_price', 'TR') IS NOT NULL DROP TRIGGER prod.trg_validate_price;
    """)
    run_sql("""
        CREATE TRIGGER prod.trg_validate_price
        ON prod.products
        INSTEAD OF INSERT
        AS
        BEGIN
            IF EXISTS (SELECT 1 FROM inserted WHERE price < 0)
            BEGIN
                RAISERROR('Product price cannot be negative', 16, 1);
                RETURN;
            END
            INSERT INTO prod.products (name, category, price, stock_quantity, is_available)
            SELECT name, category, price, stock_quantity, is_available FROM inserted;
        END
    """)
    print("   ✅ prod.trg_validate_price")

    # ==========================================
    # 2. UAT Schema Objects (Simulated Drift)
    # ==========================================
    print("\n📦 Creating UAT stored procedures (with drift)...")

    # SAME as prod
    run_sql("""
        IF OBJECT_ID('uat.get_user_by_id', 'P') IS NOT NULL DROP PROCEDURE uat.get_user_by_id;
    """)
    run_sql("""
        CREATE PROCEDURE uat.get_user_by_id @user_id INT
        AS
        BEGIN
            SELECT username, email, salary
            FROM uat.users
            WHERE id = @user_id;
        END
    """)
    print("   ✅ uat.get_user_by_id (same)")

    # DRIFT: different implementation — adds discount info
    run_sql("""
        IF OBJECT_ID('uat.get_product_stats', 'P') IS NOT NULL DROP PROCEDURE uat.get_product_stats;
    """)
    run_sql("""
        CREATE PROCEDURE uat.get_product_stats @category NVARCHAR(80) = NULL
        AS
        BEGIN
            SELECT category,
                   COUNT(*) AS product_count,
                   ROUND(AVG(price), 2) AS avg_price,
                   SUM(stock_quantity) AS total_stock,
                   ROUND(AVG(COALESCE(discount_percent, 0)), 2) AS avg_discount
            FROM uat.products
            WHERE @category IS NULL OR category = @category
            GROUP BY category
            ORDER BY category;
        END
    """)
    print("   ✅ uat.get_product_stats (DRIFT: adds avg_discount)")

    # DRIFT: different function — salary_band instead of calc_avg_salary
    run_sql("""
        IF OBJECT_ID('uat.calc_salary_band', 'FN') IS NOT NULL DROP FUNCTION uat.calc_salary_band;
    """)
    run_sql("""
        CREATE FUNCTION uat.calc_salary_band(@salary DECIMAL(12,2))
        RETURNS NVARCHAR(20)
        AS
        BEGIN
            DECLARE @band NVARCHAR(20);
            IF @salary IS NULL SET @band = 'Unknown'
            ELSE IF @salary < 50000 SET @band = 'Junior'
            ELSE IF @salary < 100000 SET @band = 'Mid'
            ELSE IF @salary < 150000 SET @band = 'Senior'
            ELSE SET @band = 'Executive';
            RETURN @band;
        END
    """)
    print("   ✅ uat.calc_salary_band (DRIFT: replaces calc_avg_salary)")

    # SAME as prod
    run_sql("""
        IF OBJECT_ID('uat.deactivate_user', 'P') IS NOT NULL DROP PROCEDURE uat.deactivate_user;
    """)
    run_sql("""
        CREATE PROCEDURE uat.deactivate_user @user_id INT
        AS
        BEGIN
            UPDATE uat.users SET is_active = 0 WHERE id = @user_id;
        END
    """)
    print("   ✅ uat.deactivate_user (same)")

    # DRIFT: extra procedure not in prod
    run_sql("""
        IF OBJECT_ID('uat.bulk_deactivate_test_users', 'P') IS NOT NULL DROP PROCEDURE uat.bulk_deactivate_test_users;
    """)
    run_sql("""
        CREATE PROCEDURE uat.bulk_deactivate_test_users
        AS
        BEGIN
            UPDATE uat.users SET is_active = 0
            WHERE username LIKE 'load_test%' OR username LIKE 'temp_%';
        END
    """)
    print("   ✅ uat.bulk_deactivate_test_users (DRIFT: extra)")

    # ---- UAT Views ----
    print("\n📦 Creating UAT views (with drift)...")

    # DRIFT: includes middle_name
    run_sql("""
        IF OBJECT_ID('uat.v_active_users', 'V') IS NOT NULL DROP VIEW uat.v_active_users;
    """)
    run_sql("""
        CREATE VIEW uat.v_active_users AS
        SELECT id, username, email, age, salary, middle_name, created_at
        FROM uat.users
        WHERE is_active = 1;
    """)
    print("   ✅ uat.v_active_users (DRIFT: +middle_name)")

    # DRIFT: includes sku and discount_percent
    run_sql("""
        IF OBJECT_ID('uat.v_product_inventory', 'V') IS NOT NULL DROP VIEW uat.v_product_inventory;
    """)
    run_sql("""
        CREATE VIEW uat.v_product_inventory AS
        SELECT id, name, category, price, stock_quantity, sku, discount_percent,
               CASE WHEN stock_quantity > 0 AND is_available = 1 THEN 'In Stock'
                    WHEN stock_quantity = 0 OR stock_quantity IS NULL THEN 'Out of Stock'
                    ELSE 'Unavailable' END AS availability_status
        FROM uat.products;
    """)
    print("   ✅ uat.v_product_inventory (DRIFT: +sku, +discount_percent)")

    # DRIFT: includes avg_discount
    run_sql("""
        IF OBJECT_ID('uat.v_category_summary', 'V') IS NOT NULL DROP VIEW uat.v_category_summary;
    """)
    run_sql("""
        CREATE VIEW uat.v_category_summary AS
        SELECT category,
               COUNT(*) AS product_count,
               ROUND(AVG(price), 2) AS avg_price,
               SUM(stock_quantity) AS total_stock,
               SUM(CASE WHEN is_available = 1 THEN 1 ELSE 0 END) AS available_count,
               ROUND(AVG(COALESCE(discount_percent, 0)), 2) AS avg_discount
        FROM uat.products
        GROUP BY category;
    """)
    print("   ✅ uat.v_category_summary (DRIFT: +avg_discount)")

    # DRIFT: extra view not in prod
    run_sql("""
        IF OBJECT_ID('uat.v_test_users', 'V') IS NOT NULL DROP VIEW uat.v_test_users;
    """)
    run_sql("""
        CREATE VIEW uat.v_test_users AS
        SELECT id, username, email, middle_name
        FROM uat.users
        WHERE username LIKE 'new_hire%'
           OR username LIKE 'intern_%'
           OR username LIKE 'load_test%'
           OR username LIKE 'temp_%';
    """)
    print("   ✅ uat.v_test_users (DRIFT: extra)")

    # ---- UAT Triggers ----
    print("\n📦 Creating UAT triggers (with drift)...")

    # Audit log table (extra column: changed_by)
    run_sql("""
        IF NOT EXISTS (SELECT * FROM sys.tables t JOIN sys.schemas s ON t.schema_id = s.schema_id
                       WHERE t.name = 'user_audit_log' AND s.name = 'uat')
        BEGIN
            CREATE TABLE uat.user_audit_log (
                id INT IDENTITY(1,1) PRIMARY KEY,
                user_id INT,
                action NVARCHAR(10),
                old_email NVARCHAR(150),
                new_email NVARCHAR(150),
                changed_at DATETIME2 DEFAULT GETDATE(),
                changed_by NVARCHAR(50) DEFAULT SUSER_NAME()
            );
        END
    """)

    # DRIFT: logs changed_by
    run_sql("""
        IF OBJECT_ID('uat.trg_user_audit', 'TR') IS NOT NULL DROP TRIGGER uat.trg_user_audit;
    """)
    run_sql("""
        CREATE TRIGGER uat.trg_user_audit
        ON uat.users
        AFTER UPDATE
        AS
        BEGIN
            INSERT INTO uat.user_audit_log (user_id, action, old_email, new_email, changed_by)
            SELECT i.id, 'UPDATE', d.email, i.email, SUSER_NAME()
            FROM inserted i
            JOIN deleted d ON i.id = d.id
            WHERE i.email <> d.email;
        END
    """)
    print("   ✅ uat.trg_user_audit (DRIFT: +changed_by)")

    # DRIFT: missing trg_validate_price (intentionally not created)
    print("   ⚠️  uat.trg_validate_price NOT created (DRIFT: missing)")

    # DRIFT: extra trigger — set created_at
    run_sql("""
        IF OBJECT_ID('uat.trg_set_created_at', 'TR') IS NOT NULL DROP TRIGGER uat.trg_set_created_at;
    """)
    run_sql("""
        CREATE TRIGGER uat.trg_set_created_at
        ON uat.users
        INSTEAD OF INSERT
        AS
        BEGIN
            INSERT INTO uat.users (username, email, age, salary, is_active, middle_name, created_at)
            SELECT username, email, age, salary, is_active, middle_name, GETDATE()
            FROM inserted;
        END
    """)
    print("   ✅ uat.trg_set_created_at (DRIFT: extra)")

    # ==========================================
    # Summary
    # ==========================================
    print("\n" + "=" * 60)
    print("✅ MSSQL Schema Objects initialization completed!")
    print("=" * 60)
    print("\nDrift summary between prod and uat:")
    print("  Procedures: prod has calc_avg_salary, uat has calc_salary_band + bulk_deactivate_test_users")
    print("  Views:      uat.v_active_users has extra middle_name column")
    print("              uat has extra v_test_users view")
    print("  Triggers:   prod has trg_validate_price, uat does not")
    print("              uat has extra trg_set_created_at trigger")


if __name__ == '__main__':
    main()
