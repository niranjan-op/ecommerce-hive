# =============================================================================
# analytics.py
# High-level analytics functions.
#
# Each function executes one or more HiveQL queries and returns a DataFrame.
# Visualization and dashboard code is kept separate (dashboard/app.py).
# =============================================================================

import pandas as pd
from python.hive_connection import execute_query


# ---------------------------------------------------------------------------
# Overview / summary metrics
# ---------------------------------------------------------------------------

def get_summary_metrics() -> dict:
    """
    Returns a dict with:
        total_revenue, total_orders, total_customers, avg_order_value
    """
    df = execute_query("""
        SELECT
            COUNT(DISTINCT o.order_id)                                    AS total_orders,
            COUNT(DISTINCT o.customer_id)                                 AS total_customers,
            ROUND(SUM(CASE WHEN o.order_status='Delivered'
                           THEN o.total_amount ELSE 0 END), 2)            AS total_revenue,
            ROUND(AVG(o.total_amount), 2)                                 AS avg_order_value
        FROM fact_orders o
    """)
    row = df.iloc[0]
    return {
        "total_orders":    int(row["total_orders"]),
        "total_customers": int(row["total_customers"]),
        "total_revenue":   float(row["total_revenue"]),
        "avg_order_value": float(row["avg_order_value"]),
    }


# ---------------------------------------------------------------------------
# Product analytics
# ---------------------------------------------------------------------------

def get_top_products(by: str = "revenue", limit: int = 10) -> pd.DataFrame:
    """
    Top products by 'revenue' or 'units_sold'.

    Returns columns: product_name, category, revenue / units_sold
    """
    if by == "revenue":
        return execute_query(f"""
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
            LIMIT {limit}
        """)
    else:
        return execute_query(f"""
            SELECT
                p.product_name,
                p.category,
                SUM(oi.quantity) AS units_sold
            FROM fact_order_items oi
            JOIN dim_products p ON oi.product_id = p.product_id
            GROUP BY p.product_name, p.category
            ORDER BY units_sold DESC
            LIMIT {limit}
        """)


def get_revenue_by_category() -> pd.DataFrame:
    """Revenue and units sold per product category."""
    return execute_query("""
        SELECT
            p.category,
            ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue,
            SUM(oi.quantity)                            AS units_sold
        FROM fact_order_items oi
        JOIN dim_products p ON oi.product_id = p.product_id
        JOIN fact_orders  o ON oi.order_id   = o.order_id
        WHERE o.order_status = 'Delivered'
        GROUP BY p.category
        ORDER BY revenue DESC
    """)


# ---------------------------------------------------------------------------
# Geographic analytics
# ---------------------------------------------------------------------------

def get_revenue_by_state() -> pd.DataFrame:
    """Revenue, order count, and customer count per state."""
    return execute_query("""
        SELECT
            c.state,
            ROUND(SUM(o.total_amount), 2) AS revenue,
            COUNT(DISTINCT o.order_id)    AS total_orders,
            COUNT(DISTINCT o.customer_id) AS active_customers
        FROM fact_orders  o
        JOIN dim_customers c ON o.customer_id = c.customer_id
        WHERE o.order_status = 'Delivered'
        GROUP BY c.state
        ORDER BY revenue DESC
    """)


def get_revenue_by_city(limit: int = 20) -> pd.DataFrame:
    """Top cities by revenue."""
    return execute_query(f"""
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
        LIMIT {limit}
    """)


# ---------------------------------------------------------------------------
# Time analytics
# ---------------------------------------------------------------------------

def get_monthly_revenue(
    year: int = None,
    category: str = None,
    state: str = None,
) -> pd.DataFrame:
    """
    Monthly revenue, optionally filtered by year, category, or state.

    Returns columns: order_year, order_month, monthly_revenue, order_count
    """
    joins  = ""
    wheres = ["o.order_status = 'Delivered'"]

    if category:
        # LEFT SEMI JOIN keeps each order once even if it has several items in
        # the category (a plain JOIN would add the order total once per item).
        joins  += f"""
        LEFT SEMI JOIN (
            SELECT oi.order_id FROM fact_order_items oi
            JOIN dim_products p ON oi.product_id = p.product_id
            WHERE p.category = '{category}'
        ) cat ON o.order_id = cat.order_id"""

    if state:
        joins  += " JOIN dim_customers c ON o.customer_id = c.customer_id"
        wheres.append(f"c.state = '{state}'")

    if year:
        wheres.append(f"o.order_year = {year}")

    where_clause = " AND ".join(wheres)

    return execute_query(f"""
        SELECT
            o.order_year,
            o.order_month,
            ROUND(SUM(o.total_amount), 2) AS monthly_revenue,
            COUNT(DISTINCT o.order_id)    AS order_count
        FROM fact_orders o
        {joins}
        WHERE {where_clause}
        GROUP BY o.order_year, o.order_month
        ORDER BY o.order_year, o.order_month
    """)


# ---------------------------------------------------------------------------
# Customer analytics
# ---------------------------------------------------------------------------

def get_top_customers(limit: int = 10) -> pd.DataFrame:
    """Top customers by total spending."""
    return execute_query(f"""
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
        LIMIT {limit}
    """)


# ---------------------------------------------------------------------------
# Payment analytics
# ---------------------------------------------------------------------------

def get_payment_method_distribution() -> pd.DataFrame:
    """Transaction count and revenue by payment method."""
    return execute_query("""
        SELECT
            payment_method,
            COUNT(*)                        AS total_transactions,
            ROUND(SUM(payment_value), 2)    AS total_amount
        FROM fact_payments
        GROUP BY payment_method
        ORDER BY total_transactions DESC
    """)


def get_payment_installments() -> pd.DataFrame:
    """How many payments were split into 1, 2, 3 … instalments."""
    return execute_query("""
        SELECT
            payment_installments,
            COUNT(*) AS txn_count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentage
        FROM fact_payments
        GROUP BY payment_installments
        ORDER BY payment_installments
    """)


# ---------------------------------------------------------------------------
# Order status analytics
# ---------------------------------------------------------------------------

def get_order_status_distribution() -> pd.DataFrame:
    """Order count and percentage by status."""
    return execute_query("""
        SELECT
            order_status,
            COUNT(*)  AS order_count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentage,
            ROUND(SUM(total_amount), 2) AS total_value
        FROM fact_orders
        GROUP BY order_status
        ORDER BY order_count DESC
    """)
