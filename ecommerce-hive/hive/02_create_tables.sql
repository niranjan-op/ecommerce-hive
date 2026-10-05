-- =============================================================================
-- 02_create_tables.sql
-- Creates:
--   1. External staging tables (CSV format, pointing to HDFS raw data)
--   2. Dimension tables  (ORC format)
--   3. Fact tables       (ORC format, orders partitioned by year/month)
--
-- WHY ORC?
-- ---------
-- ORC (Optimised Row Columnar) stores data column-by-column rather than
-- row-by-row.  For analytical queries that touch only a few columns of a
-- very wide table this means:
--   • Far less I/O  – only the needed columns are read from disk.
--   • Better compression – values in the same column share data types and
--     often have similar values, so they compress well.
--   • Predicate push-down – Hive can skip entire row-groups based on min/max
--     statistics stored inside the ORC file itself.
-- This makes ORC an ideal format for a data warehouse running aggregation
-- and JOIN queries over hundreds of millions of rows.
-- =============================================================================

USE ecommerce;

-- ---------------------------------------------------------------------------
-- SECTION 1 — STAGING TABLES (External, CSV)
-- These tables point directly to the raw CSV files in HDFS.
-- "External" means Hive does NOT own the data: dropping the table leaves
-- the CSV files untouched.
-- ---------------------------------------------------------------------------

DROP TABLE IF EXISTS stg_customers;
CREATE EXTERNAL TABLE stg_customers (
    customer_id       INT,
    city              STRING,
    state             STRING        -- Brazilian state code, e.g. SP
)
ROW FORMAT DELIMITED
  FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '/user/hive/warehouse/ecommerce/staging/customers'
TBLPROPERTIES ('skip.header.line.count'='1');


DROP TABLE IF EXISTS stg_products;
CREATE EXTERNAL TABLE stg_products (
    product_id   INT,
    product_name STRING,
    category     STRING,
    price        DECIMAL(10,2)
)
ROW FORMAT DELIMITED
  FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '/user/hive/warehouse/ecommerce/staging/products'
TBLPROPERTIES ('skip.header.line.count'='1');


DROP TABLE IF EXISTS stg_orders;
CREATE EXTERNAL TABLE stg_orders (
    order_id      INT,
    customer_id   INT,
    order_date    STRING,
    order_status  STRING,
    total_amount  DECIMAL(12,2)
)
ROW FORMAT DELIMITED
  FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '/user/hive/warehouse/ecommerce/staging/orders'
TBLPROPERTIES ('skip.header.line.count'='1');


DROP TABLE IF EXISTS stg_order_items;
CREATE EXTERNAL TABLE stg_order_items (
    order_id   INT,
    product_id INT,
    quantity   INT,
    unit_price DECIMAL(10,2)
)
ROW FORMAT DELIMITED
  FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '/user/hive/warehouse/ecommerce/staging/order_items'
TBLPROPERTIES ('skip.header.line.count'='1');


DROP TABLE IF EXISTS stg_payments;
CREATE EXTERNAL TABLE stg_payments (
    payment_id           INT,
    order_id             INT,
    payment_method       STRING,
    payment_installments INT,
    payment_value        DECIMAL(12,2),
    payment_date         STRING
)
ROW FORMAT DELIMITED
  FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '/user/hive/warehouse/ecommerce/staging/payments'
TBLPROPERTIES ('skip.header.line.count'='1');


-- ---------------------------------------------------------------------------
-- SECTION 2 — DIMENSION TABLES (Managed, ORC)
-- Managed tables: Hive controls the data lifecycle.
-- Dropping a managed table also deletes the underlying HDFS data.
-- ---------------------------------------------------------------------------

DROP TABLE IF EXISTS dim_customers;
CREATE TABLE dim_customers (
    customer_id       INT,
    city              STRING,
    state             STRING
)
STORED AS ORC
TBLPROPERTIES ('orc.compress'='SNAPPY');


DROP TABLE IF EXISTS dim_products;
CREATE TABLE dim_products (
    product_id   INT,
    product_name STRING,
    category     STRING,
    price        DECIMAL(10,2)
)
STORED AS ORC
TBLPROPERTIES ('orc.compress'='SNAPPY');


-- ---------------------------------------------------------------------------
-- SECTION 3 — FACT TABLES (Managed, ORC, orders partitioned by year/month)
--
-- PARTITIONING:
--   Partitioning divides the data physically into separate HDFS sub-directories
--   (one per year+month).  When a query filters on order_year/order_month,
--   Hive reads only the matching partitions instead of the entire table.
--   For time-series analytics this can reduce I/O by orders of magnitude.
-- ---------------------------------------------------------------------------

-- Enable dynamic partitioning so we can INSERT from a SELECT statement.
SET hive.exec.dynamic.partition        = true;
SET hive.exec.dynamic.partition.mode   = nonstrict;
SET hive.exec.max.dynamic.partitions   = 10000;

DROP TABLE IF EXISTS fact_orders;
CREATE TABLE fact_orders (
    order_id      INT,
    customer_id   INT,
    order_date    DATE,
    order_status  STRING,
    total_amount  DECIMAL(12,2)
)
PARTITIONED BY (order_year INT, order_month INT)
STORED AS ORC
TBLPROPERTIES ('orc.compress'='SNAPPY');


DROP TABLE IF EXISTS fact_order_items;
CREATE TABLE fact_order_items (
    order_id   INT,
    product_id INT,
    quantity   INT,
    unit_price DECIMAL(10,2)
)
STORED AS ORC
TBLPROPERTIES ('orc.compress'='SNAPPY');


DROP TABLE IF EXISTS fact_payments;
CREATE TABLE fact_payments (
    payment_id           INT,
    order_id             INT,
    payment_method       STRING,
    payment_installments INT,
    payment_value        DECIMAL(12,2),
    payment_date         DATE
)
STORED AS ORC
TBLPROPERTIES ('orc.compress'='SNAPPY');


-- Confirm table creation
SHOW TABLES;
