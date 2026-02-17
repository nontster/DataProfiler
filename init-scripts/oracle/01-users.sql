-- Create users for testing DataProfiler (Oracle 21c XE)
-- This script runs automatically when Oracle container starts

-- ==========================================
-- 1. Create Users (Schemas)
-- ==========================================

-- PROD User
DECLARE
   user_exists INT;
BEGIN
   SELECT COUNT(*) INTO user_exists FROM all_users WHERE username = 'PROD';
   IF user_exists = 0 THEN
      EXECUTE IMMEDIATE 'CREATE USER PROD IDENTIFIED BY "password123"';
      EXECUTE IMMEDIATE 'GRANT CONNECT, RESOURCE TO PROD';
      EXECUTE IMMEDIATE 'GRANT CREATE VIEW, CREATE PROCEDURE, CREATE TRIGGER TO PROD';
   END IF;
   -- Always ensure quota
   EXECUTE IMMEDIATE 'GRANT UNLIMITED TABLESPACE TO PROD';
   -- Always grant permissions to allow cross-schema testing & data generation
   EXECUTE IMMEDIATE 'GRANT SELECT ANY TABLE TO PROD';
   EXECUTE IMMEDIATE 'GRANT INSERT ANY TABLE TO PROD';
   EXECUTE IMMEDIATE 'GRANT UPDATE ANY TABLE TO PROD';
   EXECUTE IMMEDIATE 'GRANT DELETE ANY TABLE TO PROD';
END;
/

-- UAT User
DECLARE
   user_exists INT;
BEGIN
   SELECT COUNT(*) INTO user_exists FROM all_users WHERE username = 'UAT';
   IF user_exists = 0 THEN
      EXECUTE IMMEDIATE 'CREATE USER UAT IDENTIFIED BY "password123"';
      EXECUTE IMMEDIATE 'GRANT CONNECT, RESOURCE TO UAT';
      EXECUTE IMMEDIATE 'GRANT CREATE VIEW, CREATE PROCEDURE, CREATE TRIGGER TO UAT';
   END IF;
   -- Always ensure quota
   EXECUTE IMMEDIATE 'GRANT UNLIMITED TABLESPACE TO UAT';
END;
/
