-- =============================================================================
-- 03_load_data.sql
-- Loads data from external staging tables into the analytical ORC tables.
--
-- Run this AFTER:
--   1. CSV files have been uploaded to HDFS (scripts/run_pipeline.sh)
--   2. 02_create_tables.sql has been executed
-- =============================================================================

USE ecommerce;

-- Dynamic partition settings (must be set per session)
SET hive.exec.dynamic.partition       = true;
SET hive.exec.dynamic.partition.mode  = nonstrict;
SET hive.exec.max.dynamic.partitions  = 10000;

-- Tez execution engine recommended for better performance
-- SET hive.execution.engine = tez;

-- ---------------------------------------------------------------------------
-- Dimension: customers
-- ---------------------------------------------------------------------------
INSERT OVERWRITE TABLE dim_customers
SELECT
    customer_id,
    city,
    state
FROM stg_customers
WHERE customer_id IS NOT NULL;

-- ---------------------------------------------------------------------------
-- Dimension: products
-- ---------------------------------------------------------------------------
INSERT OVERWRITE TABLE dim_products
SELECT
    product_id,
    product_name,
    category,
    price
FROM stg_products
WHERE product_id IS NOT NULL;

-- ---------------------------------------------------------------------------
-- Fact: orders  (partitioned by year and month)
-- ---------------------------------------------------------------------------
INSERT OVERWRITE TABLE fact_orders PARTITION (order_year, order_month)
SELECT
    order_id,
    customer_id,
    TO_DATE(order_date)          AS order_date,
    order_status,
    total_amount,
    YEAR(TO_DATE(order_date))    AS order_year,
    MONTH(TO_DATE(order_date))   AS order_month
FROM stg_orders
WHERE order_id IS NOT NULL;

-- ---------------------------------------------------------------------------
-- Fact: order_items
-- ---------------------------------------------------------------------------
INSERT OVERWRITE TABLE fact_order_items
SELECT
    order_id,
    product_id,
    quantity,
    unit_price
FROM stg_order_items
WHERE order_id IS NOT NULL;

-- ---------------------------------------------------------------------------
-- Fact: payments
-- ---------------------------------------------------------------------------
INSERT OVERWRITE TABLE fact_payments
SELECT
    payment_id,
    order_id,
    payment_method,
    payment_installments,
    payment_value,
    TO_DATE(payment_date) AS payment_date
FROM stg_payments
WHERE payment_id IS NOT NULL;

-- ---------------------------------------------------------------------------
-- Quick row-count validation
-- ---------------------------------------------------------------------------
-- NOTE: "rows" is a reserved keyword in Hive, so the alias is row_count.
SELECT 'dim_customers'   AS tbl, COUNT(*) AS row_count FROM dim_customers   UNION ALL
SELECT 'dim_products'    AS tbl, COUNT(*) AS row_count FROM dim_products     UNION ALL
SELECT 'fact_orders'     AS tbl, COUNT(*) AS row_count FROM fact_orders      UNION ALL
SELECT 'fact_order_items'AS tbl, COUNT(*) AS row_count FROM fact_order_items UNION ALL
SELECT 'fact_payments'   AS tbl, COUNT(*) AS row_count FROM fact_payments;
