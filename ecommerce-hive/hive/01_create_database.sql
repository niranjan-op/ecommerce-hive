-- =============================================================================
-- 01_create_database.sql
-- Create the Hive database for the e-commerce analytics project.
-- =============================================================================

-- Drop and recreate for a clean run during development.
-- Remove the DROP line in production.
DROP DATABASE IF EXISTS ecommerce CASCADE;

CREATE DATABASE IF NOT EXISTS ecommerce
  COMMENT 'E-Commerce analytical data warehouse'
  WITH DBPROPERTIES (
    'created_by' = 'BDA Project',
    'purpose'    = 'Analytics and reporting'
  );

USE ecommerce;

SHOW DATABASES;
