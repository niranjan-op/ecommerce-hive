-- =============================================================================
-- 04_transform_data.sql
-- Optional post-load transformations and data quality checks.
-- Run after 03_load_data.sql.
-- =============================================================================

USE ecommerce;

-- ---------------------------------------------------------------------------
-- 1. Verify partition distribution
-- ---------------------------------------------------------------------------
SELECT order_year, order_month, COUNT(*) AS order_count
FROM fact_orders
GROUP BY order_year, order_month
ORDER BY order_year, order_month;

-- ---------------------------------------------------------------------------
-- 2. Check for null customer references in orders
-- ---------------------------------------------------------------------------
SELECT COUNT(*) AS orphan_orders
FROM fact_orders o
LEFT JOIN dim_customers c ON o.customer_id = c.customer_id
WHERE c.customer_id IS NULL;

-- ---------------------------------------------------------------------------
-- 3. Check for null product references in order items
-- ---------------------------------------------------------------------------
SELECT COUNT(*) AS orphan_items
FROM fact_order_items oi
LEFT JOIN dim_products p ON oi.product_id = p.product_id
WHERE p.product_id IS NULL;

-- ---------------------------------------------------------------------------
-- 4. Order status distribution (sanity check)
-- ---------------------------------------------------------------------------
SELECT order_status, COUNT(*) AS cnt,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS pct
FROM fact_orders
GROUP BY order_status
ORDER BY cnt DESC;

-- ---------------------------------------------------------------------------
-- 5. Price range per category (data quality)
-- ---------------------------------------------------------------------------
SELECT p.category,
       MIN(oi.unit_price) AS min_price,
       MAX(oi.unit_price) AS max_price,
       ROUND(AVG(oi.unit_price), 2) AS avg_price
FROM fact_order_items oi
JOIN dim_products p ON oi.product_id = p.product_id
GROUP BY p.category
ORDER BY avg_price DESC;
