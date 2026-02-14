-- Schema Objects for testing DataProfiler (PostgreSQL)
-- Creates stored procedures, views, and triggers in prod and uat schemas
-- with deliberate differences (drift) for comparison testing
-- Run AFTER 01-sample-data.sql

-- ==========================================
-- 1. PROD Schema Objects (Golden Standard)
-- ==========================================

-- ----- Stored Procedures / Functions -----

-- Function: get user by ID
CREATE OR REPLACE FUNCTION prod.get_user_by_id(p_user_id INTEGER)
RETURNS TABLE(username VARCHAR, email VARCHAR, salary NUMERIC) AS $$
BEGIN
    RETURN QUERY
    SELECT u.username, u.email, u.salary
    FROM prod.users u
    WHERE u.id = p_user_id;
END;
$$ LANGUAGE plpgsql;

-- Function: get product stats by category
CREATE OR REPLACE FUNCTION prod.get_product_stats(p_category VARCHAR DEFAULT NULL)
RETURNS TABLE(category VARCHAR, product_count BIGINT, avg_price NUMERIC, total_stock BIGINT) AS $$
BEGIN
    RETURN QUERY
    SELECT p.category,
           COUNT(*)::BIGINT,
           ROUND(AVG(p.price), 2),
           SUM(p.stock_quantity)::BIGINT
    FROM prod.products p
    WHERE p_category IS NULL OR p.category = p_category
    GROUP BY p.category
    ORDER BY p.category;
END;
$$ LANGUAGE plpgsql;

-- Function: calculate salary statistics
CREATE OR REPLACE FUNCTION prod.calc_salary_stats()
RETURNS TABLE(total_employees BIGINT, avg_salary NUMERIC, min_salary NUMERIC, max_salary NUMERIC) AS $$
BEGIN
    RETURN QUERY
    SELECT COUNT(*)::BIGINT,
           ROUND(AVG(salary), 2),
           MIN(salary),
           MAX(salary)
    FROM prod.users
    WHERE salary IS NOT NULL AND is_active = true;
END;
$$ LANGUAGE plpgsql;

-- Procedure: deactivate user (no return value)
CREATE OR REPLACE PROCEDURE prod.deactivate_user(p_user_id INTEGER)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE prod.users SET is_active = false WHERE id = p_user_id;
END;
$$;


-- ----- Views -----

-- View: active users summary
CREATE OR REPLACE VIEW prod.v_active_users AS
SELECT id, username, email, age, salary, created_at
FROM prod.users
WHERE is_active = true;

-- View: product inventory
CREATE OR REPLACE VIEW prod.v_product_inventory AS
SELECT id, name, category, price, stock_quantity,
       CASE WHEN stock_quantity > 0 AND is_available THEN 'In Stock'
            WHEN stock_quantity = 0 THEN 'Out of Stock'
            ELSE 'Unavailable' END AS availability_status
FROM prod.products;

-- View: category summary (aggregation)
CREATE OR REPLACE VIEW prod.v_category_summary AS
SELECT category,
       COUNT(*) AS product_count,
       ROUND(AVG(price), 2) AS avg_price,
       SUM(stock_quantity) AS total_stock,
       SUM(CASE WHEN is_available THEN 1 ELSE 0 END) AS available_count
FROM prod.products
GROUP BY category;


-- ----- Triggers -----

-- Audit log table for trigger
CREATE TABLE IF NOT EXISTS prod.user_audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    action VARCHAR(10),
    old_email VARCHAR(100),
    new_email VARCHAR(100),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trigger function: log user email changes
CREATE OR REPLACE FUNCTION prod.fn_log_user_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.email IS DISTINCT FROM NEW.email THEN
        INSERT INTO prod.user_audit_log (user_id, action, old_email, new_email)
        VALUES (NEW.id, 'UPDATE', OLD.email, NEW.email);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: fire on user update
DROP TRIGGER IF EXISTS trg_user_audit ON prod.users;
CREATE TRIGGER trg_user_audit
    AFTER UPDATE ON prod.users
    FOR EACH ROW
    EXECUTE FUNCTION prod.fn_log_user_changes();

-- Trigger function: validate product price
CREATE OR REPLACE FUNCTION prod.fn_validate_product_price()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.price < 0 THEN
        RAISE EXCEPTION 'Product price cannot be negative';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: validate before insert/update on products
DROP TRIGGER IF EXISTS trg_validate_price ON prod.products;
CREATE TRIGGER trg_validate_price
    BEFORE INSERT OR UPDATE ON prod.products
    FOR EACH ROW
    EXECUTE FUNCTION prod.fn_validate_product_price();


-- ==========================================
-- 2. UAT Schema Objects (Simulated Drift)
-- ==========================================

-- ----- Stored Procedures / Functions -----

-- SAME as prod (no drift)
CREATE OR REPLACE FUNCTION uat.get_user_by_id(p_user_id INTEGER)
RETURNS TABLE(username VARCHAR, email VARCHAR, salary NUMERIC) AS $$
BEGIN
    RETURN QUERY
    SELECT u.username, u.email, u.salary
    FROM uat.users u
    WHERE u.id = p_user_id;
END;
$$ LANGUAGE plpgsql;

-- DRIFT: different implementation — adds middle_name and is_active filter
CREATE OR REPLACE FUNCTION uat.get_product_stats(p_category VARCHAR DEFAULT NULL)
RETURNS TABLE(category VARCHAR, product_count BIGINT, avg_price NUMERIC, total_stock BIGINT, avg_discount NUMERIC) AS $$
BEGIN
    RETURN QUERY
    SELECT p.category,
           COUNT(*)::BIGINT,
           ROUND(AVG(p.price), 2),
           SUM(p.stock_quantity)::BIGINT,
           ROUND(AVG(COALESCE(p.discount_percent, 0)), 2)
    FROM uat.products p
    WHERE p_category IS NULL OR p.category = p_category
    GROUP BY p.category
    ORDER BY p.category;
END;
$$ LANGUAGE plpgsql;

-- DRIFT: completely different function — replaced calc_salary_stats with calc_salary_band
CREATE OR REPLACE FUNCTION uat.calc_salary_band(p_salary NUMERIC)
RETURNS VARCHAR AS $$
BEGIN
    IF p_salary IS NULL THEN RETURN 'Unknown';
    ELSIF p_salary < 50000 THEN RETURN 'Junior';
    ELSIF p_salary < 100000 THEN RETURN 'Mid';
    ELSIF p_salary < 150000 THEN RETURN 'Senior';
    ELSE RETURN 'Executive';
    END IF;
END;
$$ LANGUAGE plpgsql;

-- SAME as prod (no drift)
CREATE OR REPLACE PROCEDURE uat.deactivate_user(p_user_id INTEGER)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE uat.users SET is_active = false WHERE id = p_user_id;
END;
$$;

-- DRIFT: extra procedure not in prod
CREATE OR REPLACE PROCEDURE uat.bulk_deactivate_test_users()
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE uat.users SET is_active = false
    WHERE username LIKE 'load_test%' OR username LIKE 'temp_%';
END;
$$;


-- ----- Views -----

-- DRIFT: includes middle_name (extra column from uat schema drift)
CREATE OR REPLACE VIEW uat.v_active_users AS
SELECT id, username, email, age, salary, middle_name, created_at
FROM uat.users
WHERE is_active = true;

-- DRIFT: includes sku and discount_percent
CREATE OR REPLACE VIEW uat.v_product_inventory AS
SELECT id, name, category, price, stock_quantity, sku, discount_percent,
       CASE WHEN stock_quantity > 0 AND is_available THEN 'In Stock'
            WHEN stock_quantity = 0 OR stock_quantity IS NULL THEN 'Out of Stock'
            ELSE 'Unavailable' END AS availability_status
FROM uat.products;

-- DRIFT: same name but different aggregation (includes discount info)
CREATE OR REPLACE VIEW uat.v_category_summary AS
SELECT category,
       COUNT(*) AS product_count,
       ROUND(AVG(price), 2) AS avg_price,
       SUM(stock_quantity) AS total_stock,
       SUM(CASE WHEN is_available THEN 1 ELSE 0 END) AS available_count,
       ROUND(AVG(COALESCE(discount_percent, 0)), 2) AS avg_discount
FROM uat.products
GROUP BY category;

-- DRIFT: extra view not in prod
CREATE OR REPLACE VIEW uat.v_test_users AS
SELECT id, username, email, middle_name
FROM uat.users
WHERE username LIKE 'new_hire%'
   OR username LIKE 'intern_%'
   OR username LIKE 'load_test%'
   OR username LIKE 'temp_%';


-- ----- Triggers -----

-- Audit log table (same structure)
CREATE TABLE IF NOT EXISTS uat.user_audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    action VARCHAR(10),
    old_email VARCHAR(150),
    new_email VARCHAR(150),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    changed_by VARCHAR(50) DEFAULT CURRENT_USER
);

-- DRIFT: trigger function logs more info (changed_by)
CREATE OR REPLACE FUNCTION uat.fn_log_user_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.email IS DISTINCT FROM NEW.email THEN
        INSERT INTO uat.user_audit_log (user_id, action, old_email, new_email, changed_by)
        VALUES (NEW.id, 'UPDATE', OLD.email, NEW.email, CURRENT_USER);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: fire on user update (same name, different function body → different hash)
DROP TRIGGER IF EXISTS trg_user_audit ON uat.users;
CREATE TRIGGER trg_user_audit
    AFTER UPDATE ON uat.users
    FOR EACH ROW
    EXECUTE FUNCTION uat.fn_log_user_changes();

-- DRIFT: missing trg_validate_price (dropped in UAT)
-- (intentionally not created — simulates a missing trigger)

-- DRIFT: extra trigger not in prod — auto-set created_at
CREATE OR REPLACE FUNCTION uat.fn_set_created_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.created_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_set_created_at ON uat.users;
CREATE TRIGGER trg_set_created_at
    BEFORE INSERT ON uat.users
    FOR EACH ROW
    EXECUTE FUNCTION uat.fn_set_created_at();


-- ==========================================
-- Verify schema objects
-- ==========================================
SELECT 'prod.functions' AS object_type, COUNT(*) AS count
FROM information_schema.routines
WHERE routine_schema = 'prod'
UNION ALL
SELECT 'uat.functions', COUNT(*)
FROM information_schema.routines
WHERE routine_schema = 'uat'
UNION ALL
SELECT 'prod.views', COUNT(*)
FROM information_schema.views
WHERE table_schema = 'prod'
UNION ALL
SELECT 'uat.views', COUNT(*)
FROM information_schema.views
WHERE table_schema = 'uat'
UNION ALL
SELECT 'prod.triggers', COUNT(*)
FROM information_schema.triggers
WHERE trigger_schema = 'prod'
UNION ALL
SELECT 'uat.triggers', COUNT(*)
FROM information_schema.triggers
WHERE trigger_schema = 'uat';
