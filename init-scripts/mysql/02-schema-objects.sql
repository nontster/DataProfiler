-- Schema Objects for testing DataProfiler (MySQL)
-- Creates stored procedures, views, and triggers in prod and uat databases
-- with deliberate differences (drift) for comparison testing
-- Run AFTER 01-sample-data.sql

-- ==========================================
-- 1. PROD Schema Objects (Golden Standard)
-- ==========================================
USE prod;

-- ----- Stored Procedures -----

DELIMITER //

-- Procedure: get user by ID
CREATE PROCEDURE get_user_by_id(IN p_user_id INT)
BEGIN
    SELECT username, email, salary
    FROM users
    WHERE id = p_user_id;
END //

-- Procedure: get product stats by category
CREATE PROCEDURE get_product_stats(IN p_category VARCHAR(50))
BEGIN
    SELECT category,
           COUNT(*) AS product_count,
           ROUND(AVG(price), 2) AS avg_price,
           SUM(stock_quantity) AS total_stock
    FROM products
    WHERE p_category IS NULL OR category = p_category
    GROUP BY category
    ORDER BY category;
END //

-- Function: calculate average salary for active users
CREATE FUNCTION calc_avg_salary()
RETURNS DECIMAL(10,2)
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE avg_sal DECIMAL(10,2);
    SELECT ROUND(AVG(salary), 2) INTO avg_sal
    FROM users
    WHERE salary IS NOT NULL AND is_active = 1;
    RETURN avg_sal;
END //

-- Procedure: deactivate user
CREATE PROCEDURE deactivate_user(IN p_user_id INT)
BEGIN
    UPDATE users SET is_active = 0 WHERE id = p_user_id;
END //

DELIMITER ;


-- ----- Views -----

-- View: active users summary
CREATE OR REPLACE VIEW v_active_users AS
SELECT id, username, email, age, salary, created_at
FROM users
WHERE is_active = 1;

-- View: product inventory
CREATE OR REPLACE VIEW v_product_inventory AS
SELECT id, name, category, price, stock_quantity,
       CASE WHEN stock_quantity > 0 AND is_available = 1 THEN 'In Stock'
            WHEN stock_quantity = 0 THEN 'Out of Stock'
            ELSE 'Unavailable' END AS availability_status
FROM products;

-- View: category summary
CREATE OR REPLACE VIEW v_category_summary AS
SELECT category,
       COUNT(*) AS product_count,
       ROUND(AVG(price), 2) AS avg_price,
       SUM(stock_quantity) AS total_stock,
       SUM(CASE WHEN is_available = 1 THEN 1 ELSE 0 END) AS available_count
FROM products
GROUP BY category;


-- ----- Triggers -----

-- Audit log table for trigger
CREATE TABLE IF NOT EXISTS user_audit_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    action VARCHAR(10),
    old_email VARCHAR(100),
    new_email VARCHAR(100),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

DELIMITER //

-- Trigger: log user email changes
CREATE TRIGGER trg_user_audit
    AFTER UPDATE ON users
    FOR EACH ROW
BEGIN
    IF OLD.email <> NEW.email THEN
        INSERT INTO user_audit_log (user_id, action, old_email, new_email)
        VALUES (NEW.id, 'UPDATE', OLD.email, NEW.email);
    END IF;
END //

-- Trigger: validate product price before insert
CREATE TRIGGER trg_validate_price_insert
    BEFORE INSERT ON products
    FOR EACH ROW
BEGIN
    IF NEW.price < 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Product price cannot be negative';
    END IF;
END //

-- Trigger: validate product price before update
CREATE TRIGGER trg_validate_price_update
    BEFORE UPDATE ON products
    FOR EACH ROW
BEGIN
    IF NEW.price < 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Product price cannot be negative';
    END IF;
END //

DELIMITER ;


-- ==========================================
-- 2. UAT Schema Objects (Simulated Drift)
-- ==========================================
USE uat;

-- ----- Stored Procedures -----

DELIMITER //

-- SAME as prod (no drift)
CREATE PROCEDURE get_user_by_id(IN p_user_id INT)
BEGIN
    SELECT username, email, salary
    FROM users
    WHERE id = p_user_id;
END //

-- DRIFT: different implementation — adds discount info
CREATE PROCEDURE get_product_stats(IN p_category VARCHAR(80))
BEGIN
    SELECT category,
           COUNT(*) AS product_count,
           ROUND(AVG(price), 2) AS avg_price,
           SUM(stock_quantity) AS total_stock,
           ROUND(AVG(COALESCE(discount_percent, 0)), 2) AS avg_discount
    FROM products
    WHERE p_category IS NULL OR category = p_category
    GROUP BY category
    ORDER BY category;
END //

-- DRIFT: different function — salary_band instead of calc_avg_salary
CREATE FUNCTION calc_salary_band(p_salary DECIMAL(12,2))
RETURNS VARCHAR(20)
DETERMINISTIC
NO SQL
BEGIN
    IF p_salary IS NULL THEN RETURN 'Unknown';
    ELSEIF p_salary < 50000 THEN RETURN 'Junior';
    ELSEIF p_salary < 100000 THEN RETURN 'Mid';
    ELSEIF p_salary < 150000 THEN RETURN 'Senior';
    ELSE RETURN 'Executive';
    END IF;
END //

-- SAME as prod (no drift)
CREATE PROCEDURE deactivate_user(IN p_user_id INT)
BEGIN
    UPDATE users SET is_active = 0 WHERE id = p_user_id;
END //

-- DRIFT: extra procedure not in prod
CREATE PROCEDURE bulk_deactivate_test_users()
BEGIN
    UPDATE users SET is_active = 0
    WHERE username LIKE 'load_test%' OR username LIKE 'temp_%';
END //

DELIMITER ;


-- ----- Views -----

-- DRIFT: includes middle_name
CREATE OR REPLACE VIEW v_active_users AS
SELECT id, username, email, age, salary, middle_name, created_at
FROM users
WHERE is_active = 1;

-- DRIFT: includes sku and discount_percent
CREATE OR REPLACE VIEW v_product_inventory AS
SELECT id, name, category, price, stock_quantity, sku, discount_percent,
       CASE WHEN stock_quantity > 0 AND is_available = 1 THEN 'In Stock'
            WHEN stock_quantity = 0 OR stock_quantity IS NULL THEN 'Out of Stock'
            ELSE 'Unavailable' END AS availability_status
FROM products;

-- DRIFT: includes avg_discount
CREATE OR REPLACE VIEW v_category_summary AS
SELECT category,
       COUNT(*) AS product_count,
       ROUND(AVG(price), 2) AS avg_price,
       SUM(stock_quantity) AS total_stock,
       SUM(CASE WHEN is_available = 1 THEN 1 ELSE 0 END) AS available_count,
       ROUND(AVG(COALESCE(discount_percent, 0)), 2) AS avg_discount
FROM products
GROUP BY category;

-- DRIFT: extra view not in prod
CREATE OR REPLACE VIEW v_test_users AS
SELECT id, username, email, middle_name
FROM users
WHERE username LIKE 'new_hire%'
   OR username LIKE 'intern_%'
   OR username LIKE 'load_test%'
   OR username LIKE 'temp_%';


-- ----- Triggers -----

-- Audit log table (same structure + extra column)
CREATE TABLE IF NOT EXISTS user_audit_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    action VARCHAR(10),
    old_email VARCHAR(150),
    new_email VARCHAR(150),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    changed_by VARCHAR(50) DEFAULT (CURRENT_USER())
);

DELIMITER //

-- DRIFT: trigger logs extra info (changed_by)
CREATE TRIGGER trg_user_audit
    AFTER UPDATE ON users
    FOR EACH ROW
BEGIN
    IF OLD.email <> NEW.email THEN
        INSERT INTO user_audit_log (user_id, action, old_email, new_email, changed_by)
        VALUES (NEW.id, 'UPDATE', OLD.email, NEW.email, CURRENT_USER());
    END IF;
END //

-- DRIFT: missing trg_validate_price_insert and trg_validate_price_update
-- (intentionally not created — simulates missing triggers)

-- DRIFT: extra trigger not in prod — auto-set created_at
CREATE TRIGGER trg_set_created_at
    BEFORE INSERT ON users
    FOR EACH ROW
BEGIN
    SET NEW.created_at = CURRENT_TIMESTAMP;
END //

DELIMITER ;
