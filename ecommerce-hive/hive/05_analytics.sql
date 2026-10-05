-- =============================================================================
-- 05_analytics.sql
-- All HiveQL analytical queries for the e-commerce data warehouse.
--
-- These queries demonstrate:
--   • Aggregations (SUM, COUNT, AVG)
--   • GROUP BY with multiple columns
--   • JOINs between fact and dimension tables
--   • Date functions (YEAR, MONTH, DATE_FORMAT)
--   • Window functions (LAG for month-over-month growth)
--   • ORDER BY and LIMIT
--   • CASE expressions
--   • Subqueries / CTEs
-- =============================================================================

USE ecommerce;

-- ===========================================================================
-- SECTION A — BASIC AGGREGATION
-- ===========================================================================

-- A1. Total revenue from delivered orders
SELECT ROUND(SUM(total_amount), 2) AS total_revenue
FROM fact_orders
WHERE order_status = 'Delivered';

-- A2. Total number of orders
SELECT COUNT(*) AS total_orders
FROM fact_orders;

-- A3. Average order value (all orders)
SELECT ROUND(AVG(total_amount), 2) AS avg_order_value
FROM fact_orders;

-- A4. Total number of unique customers
SELECT COUNT(DISTINCT customer_id) AS total_customers
FROM dim_customers;

-- A5. Summary dashboard metrics (single query)
SELECT
    COUNT(DISTINCT o.order_id)                                    AS total_orders,
    COUNT(DISTINCT o.customer_id)                                 AS total_customers,
    ROUND(SUM(CASE WHEN o.order_status='Delivered'
                   THEN o.total_amount ELSE 0 END), 2)            AS total_revenue,
    ROUND(AVG(o.total_amount), 2)                                 AS avg_order_value
FROM fact_orders o;


-- ===========================================================================
-- SECTION B — PRODUCT ANALYTICS
-- ===========================================================================

-- B1. Top 10 products by units sold
SELECT
    p.product_name,
    p.category,
    SUM(oi.quantity) AS units_sold
FROM fact_order_items oi
JOIN dim_products p ON oi.product_id = p.product_id
GROUP BY p.product_name, p.category
ORDER BY units_sold DESC
LIMIT 10;

-- B2. Top 10 products by revenue
SELECT
    p.product_name,
    p.category,
    ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
FROM fact_order_items oi
JOIN dim_products p ON oi.product_id = p.product_id
JOIN fact_orders  o ON oi.order_id   = o.order_id
WHERE o.order_status = 'Delivered'
GROUP BY p.product_name, p.category
ORDER BY revenue DESC
LIMIT 10;

-- B3. Revenue by category
SELECT
    p.category,
    ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue,
    SUM(oi.quantity)                            AS units_sold
FROM fact_order_items oi
JOIN dim_products p ON oi.product_id = p.product_id
JOIN fact_orders  o ON oi.order_id   = o.order_id
WHERE o.order_status = 'Delivered'
GROUP BY p.category
ORDER BY revenue DESC;

-- B4. Units sold by category
SELECT
    p.category,
    SUM(oi.quantity) AS units_sold
FROM fact_order_items oi
JOIN dim_products p ON oi.product_id = p.product_id
GROUP BY p.category
ORDER BY units_sold DESC;

-- B5. Average order value by category
SELECT
    p.category,
    ROUND(AVG(o.total_amount), 2) AS avg_order_value
FROM fact_orders o
JOIN fact_order_items oi ON o.order_id   = oi.order_id
JOIN dim_products     p  ON oi.product_id = p.product_id
WHERE o.order_status = 'Delivered'
GROUP BY p.category
ORDER BY avg_order_value DESC;


-- ===========================================================================
-- SECTION C — GEOGRAPHIC ANALYTICS
-- ===========================================================================

-- C1. Revenue by city (top 20)
SELECT
    c.city,
    c.state,
    ROUND(SUM(o.total_amount), 2) AS revenue,
    COUNT(DISTINCT o.order_id)    AS total_orders
FROM fact_orders  o
JOIN dim_customers c ON o.customer_id = c.customer_id
WHERE o.order_status = 'Delivered'
GROUP BY c.city, c.state
ORDER BY revenue DESC
LIMIT 20;

-- C2. Revenue by state
SELECT
    c.state,
    ROUND(SUM(o.total_amount), 2) AS revenue,
    COUNT(DISTINCT o.order_id)    AS total_orders,
    COUNT(DISTINCT o.customer_id) AS active_customers
FROM fact_orders  o
JOIN dim_customers c ON o.customer_id = c.customer_id
WHERE o.order_status = 'Delivered'
GROUP BY c.state
ORDER BY revenue DESC;


-- ===========================================================================
-- SECTION D — TIME ANALYTICS
-- ===========================================================================

-- D1. Monthly revenue
SELECT
    order_year,
    order_month,
    ROUND(SUM(total_amount), 2) AS monthly_revenue,
    COUNT(*)                    AS order_count
FROM fact_orders
WHERE order_status = 'Delivered'
GROUP BY order_year, order_month
ORDER BY order_year, order_month;

-- D2. Monthly order count (all statuses)
SELECT
    order_year,
    order_month,
    COUNT(*) AS order_count
FROM fact_orders
GROUP BY order_year, order_month
ORDER BY order_year, order_month;

-- D3. Month-over-month revenue growth using LAG window function
SELECT
    order_year,
    order_month,
    monthly_revenue,
    LAG(monthly_revenue) OVER (ORDER BY order_year, order_month) AS prev_revenue,
    ROUND(
        (monthly_revenue - LAG(monthly_revenue) OVER (ORDER BY order_year, order_month))
        * 100.0
        / NULLIF(LAG(monthly_revenue) OVER (ORDER BY order_year, order_month), 0),
    2) AS growth_pct
FROM (
    SELECT
        order_year,
        order_month,
        ROUND(SUM(total_amount), 2) AS monthly_revenue
    FROM fact_orders
    WHERE order_status = 'Delivered'
    GROUP BY order_year, order_month
) monthly
ORDER BY order_year, order_month;


-- ===========================================================================
-- SECTION E — CUSTOMER ANALYTICS
-- ===========================================================================

-- E1. Top 10 customers by total spending
SELECT
    c.customer_id,
    c.city,
    c.state,
    ROUND(SUM(o.total_amount), 2) AS total_spent,
    COUNT(DISTINCT o.order_id)    AS orders_placed
FROM fact_orders  o
JOIN dim_customers c ON o.customer_id = c.customer_id
WHERE o.order_status = 'Delivered'
GROUP BY c.customer_id, c.city, c.state
ORDER BY total_spent DESC
LIMIT 10;

-- E2. Average spending per customer
SELECT
    ROUND(AVG(customer_total), 2) AS avg_spending_per_customer
FROM (
    SELECT customer_id, SUM(total_amount) AS customer_total
    FROM fact_orders
    WHERE order_status = 'Delivered'
    GROUP BY customer_id
) cust;

-- E3. Order frequency distribution (how many customers placed N orders)
SELECT
    orders_placed,
    COUNT(*) AS customer_count
FROM (
    SELECT customer_id, COUNT(DISTINCT order_id) AS orders_placed
    FROM fact_orders
    GROUP BY customer_id
) freq
GROUP BY orders_placed
ORDER BY orders_placed;


-- ===========================================================================
-- SECTION F — PAYMENT ANALYTICS
-- ===========================================================================

-- F1. Payments and amount paid by payment method
SELECT
    payment_method,
    COUNT(*)                      AS total_transactions,
    ROUND(SUM(payment_value), 2)  AS total_amount
FROM fact_payments
GROUP BY payment_method
ORDER BY total_transactions DESC;

-- F2. Instalment distribution
SELECT
    payment_installments,
    COUNT(*)                                          AS txn_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentage
FROM fact_payments
GROUP BY payment_installments
ORDER BY payment_installments;

-- F3. Average payment value and instalments per payment method
SELECT
    payment_method,
    ROUND(AVG(payment_value), 2)        AS avg_payment_value,
    ROUND(AVG(payment_installments), 2) AS avg_installments
FROM fact_payments
GROUP BY payment_method
ORDER BY avg_payment_value DESC;


-- ===========================================================================
-- SECTION G — ORDER STATUS ANALYTICS
-- ===========================================================================

-- G1. Order status distribution
SELECT
    order_status,
    COUNT(*)                                          AS order_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentage,
    ROUND(SUM(total_amount), 2)                       AS total_value
FROM fact_orders
GROUP BY order_status
ORDER BY order_count DESC;
