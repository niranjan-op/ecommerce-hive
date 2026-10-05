import sys
sys.path.insert(0, '.')
from python.analytics_pandas import (
    get_summary_metrics, get_revenue_by_category, get_top_customers
)

m = get_summary_metrics()
print("=== REAL OLIST DATA SUMMARY ===")
print("  Orders    :", m["total_orders"])
print("  Customers :", m["total_customers"])
print("  Revenue   :", m["total_revenue"])
print("  Avg Order :", m["avg_order_value"])
print()
print("Revenue by Category:")
print(get_revenue_by_category().to_string(index=False))
print()
print("Top 5 Customers:")
df = get_top_customers(5)
print(df[["name","city","state","total_spent","orders_placed"]].to_string(index=False))
