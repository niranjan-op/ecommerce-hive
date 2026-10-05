# =============================================================================
# analytics_pandas.py
# Pandas-based implementations of every analytics function in analytics.py.
#
# This module provides IDENTICAL return signatures to analytics.py but reads
# from CSV files instead of Apache Hive.  The dashboard uses this when:
#   • Hive / HiveServer2 is not running
#   • The user explicitly selects "Demo Mode"
#
# This is also a useful educational comparison:
#   pandas  → works on a single machine, fast for small data
#   Hive    → distributed, scales to billions of rows on a cluster
# =============================================================================

import os
import pandas as pd
from python.config import DATA_DIR

# ---------------------------------------------------------------------------
# Load CSVs once and cache them in memory
# ---------------------------------------------------------------------------

_CACHE: dict = {}


def _load(name: str) -> pd.DataFrame:
    """Load a CSV from DATA_DIR, cache after first read."""
    if name not in _CACHE:
        path = os.path.join(DATA_DIR, f"{name}.csv")
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Data file not found: {path}\n"
                f"Run the data generator first:\n"
                f"  python data_generator/generate_data.py\n"
                f"  — or —\n"
                f"  python data_generator/kaggle_loader.py"
            )
        _CACHE[name] = pd.read_csv(path)
    return _CACHE[name].copy()


# ---------------------------------------------------------------------------
# Overview / summary metrics
# ---------------------------------------------------------------------------

def get_summary_metrics() -> dict:
    orders = _load("orders")
    customers = _load("customers")
    delivered = orders[orders["order_status"] == "Delivered"]
    return {
        "total_orders":    len(orders),
        "total_customers": customers["customer_id"].nunique(),
        "total_revenue":   round(float(delivered["total_amount"].sum()), 2),
        "avg_order_value": round(float(orders["total_amount"].mean()), 2),
    }


# ---------------------------------------------------------------------------
# Product analytics
# ---------------------------------------------------------------------------

def get_top_products(by: str = "revenue", limit: int = 10) -> pd.DataFrame:
    items    = _load("order_items")
    products = _load("products")
    orders   = _load("orders")

    df = items.merge(products, on="product_id").merge(orders[["order_id", "order_status"]], on="order_id")

    if by == "revenue":
        df = df[df["order_status"] == "Delivered"]
        df["revenue"] = df["quantity"] * df["unit_price"]
        result = (
            df.groupby(["product_name", "category"])["revenue"]
            .sum().reset_index()
            .sort_values("revenue", ascending=False)
            .head(limit)
        )
        result["revenue"] = result["revenue"].round(2)
        return result
    else:
        result = (
            df.groupby(["product_name", "category"])["quantity"]
            .sum().reset_index()
            .rename(columns={"quantity": "units_sold"})
            .sort_values("units_sold", ascending=False)
            .head(limit)
        )
        return result


def get_revenue_by_category() -> pd.DataFrame:
    items    = _load("order_items")
    products = _load("products")
    orders   = _load("orders")

    df = (items
          .merge(products, on="product_id")
          .merge(orders[["order_id", "order_status"]], on="order_id"))
    df = df[df["order_status"] == "Delivered"]
    df["revenue"] = df["quantity"] * df["unit_price"]

    result = (df.groupby("category")
               .agg(revenue=("revenue", "sum"), units_sold=("quantity", "sum"))
               .reset_index()
               .sort_values("revenue", ascending=False))
    result["revenue"] = result["revenue"].round(2)
    return result


# ---------------------------------------------------------------------------
# Geographic analytics
# ---------------------------------------------------------------------------

def get_revenue_by_state() -> pd.DataFrame:
    orders    = _load("orders")
    customers = _load("customers")

    df = orders[orders["order_status"] == "Delivered"].merge(
        customers[["customer_id", "state"]], on="customer_id"
    )
    result = (df.groupby("state")
               .agg(revenue=("total_amount", "sum"),
                    total_orders=("order_id", "nunique"),
                    active_customers=("customer_id", "nunique"))
               .reset_index()
               .sort_values("revenue", ascending=False))
    result["revenue"] = result["revenue"].round(2)
    return result


def get_revenue_by_city(limit: int = 20) -> pd.DataFrame:
    orders    = _load("orders")
    customers = _load("customers")

    df = orders[orders["order_status"] == "Delivered"].merge(
        customers[["customer_id", "city", "state"]], on="customer_id"
    )
    result = (df.groupby(["city", "state"])
               .agg(revenue=("total_amount", "sum"),
                    total_orders=("order_id", "nunique"))
               .reset_index()
               .sort_values("revenue", ascending=False)
               .head(limit))
    result["revenue"] = result["revenue"].round(2)
    return result


# ---------------------------------------------------------------------------
# Time analytics
# ---------------------------------------------------------------------------

def get_monthly_revenue(
    year: int = None,
    category: str = None,
    state: str = None,
) -> pd.DataFrame:
    orders = _load("orders")
    orders["order_date"] = pd.to_datetime(orders["order_date"])
    orders["order_year"]  = orders["order_date"].dt.year
    orders["order_month"] = orders["order_date"].dt.month

    df = orders[orders["order_status"] == "Delivered"]

    if year:
        df = df[df["order_year"] == year]

    if category:
        items    = _load("order_items")
        products = _load("products")
        cat_orders = (items.merge(products[["product_id", "category"]], on="product_id")
                       [lambda x: x["category"] == category]["order_id"].unique())
        df = df[df["order_id"].isin(cat_orders)]

    if state:
        customers = _load("customers")
        state_customers = customers[customers["state"] == state]["customer_id"].unique()
        df = df[df["customer_id"].isin(state_customers)]

    result = (df.groupby(["order_year", "order_month"])
               .agg(monthly_revenue=("total_amount", "sum"),
                    order_count=("order_id", "nunique"))
               .reset_index()
               .sort_values(["order_year", "order_month"]))
    result["monthly_revenue"] = result["monthly_revenue"].round(2)
    return result


# ---------------------------------------------------------------------------
# Customer analytics
# ---------------------------------------------------------------------------

def get_top_customers(limit: int = 10) -> pd.DataFrame:
    orders    = _load("orders")
    customers = _load("customers")

    df = orders[orders["order_status"] == "Delivered"].merge(
        customers[["customer_id", "city", "state"]], on="customer_id"
    )
    result = (df.groupby(["customer_id", "city", "state"])
               .agg(total_spent=("total_amount", "sum"),
                    orders_placed=("order_id", "nunique"))
               .reset_index()
               .sort_values("total_spent", ascending=False)
               .head(limit))
    result["total_spent"] = result["total_spent"].round(2)
    return result


# ---------------------------------------------------------------------------
# Payment analytics
# ---------------------------------------------------------------------------

def get_payment_method_distribution() -> pd.DataFrame:
    payments = _load("payments")

    result = (payments.groupby("payment_method")
               .agg(total_transactions=("payment_id", "count"),
                    total_amount=("payment_value", "sum"))
               .reset_index()
               .sort_values("total_transactions", ascending=False))
    result["total_amount"] = result["total_amount"].round(2)
    return result


def get_payment_installments() -> pd.DataFrame:
    payments = _load("payments")
    total = len(payments)
    result = (payments.groupby("payment_installments")
              .size().reset_index(name="txn_count")
              .sort_values("payment_installments"))
    result["percentage"] = (result["txn_count"] / total * 100).round(2)
    return result


# ---------------------------------------------------------------------------
# Order status analytics
# ---------------------------------------------------------------------------

def get_order_status_distribution() -> pd.DataFrame:
    orders = _load("orders")
    total = len(orders)
    result = (orders.groupby("order_status")
              .agg(order_count=("order_id", "count"),
                   total_value=("total_amount", "sum"))
              .reset_index()
              .sort_values("order_count", ascending=False))
    result["percentage"] = (result["order_count"] / total * 100).round(2)
    result["total_value"] = result["total_value"].round(2)
    return result
