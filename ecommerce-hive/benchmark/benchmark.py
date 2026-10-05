"""
benchmark.py
------------
Benchmarks one or two HiveQL queries across dataset sizes.

Usage (after generating data at each size):
    python benchmark/benchmark.py

The script expects that the Hive tables have been loaded for each scale.
It records wall-clock time for each query and prints a comparison table.
"""

import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
from python.hive_connection import execute_query, HiveConnectionError

# ---------------------------------------------------------------------------
# Queries to benchmark
# ---------------------------------------------------------------------------

BENCHMARKS = {
    "Revenue by Category (JOIN + GROUP BY)": """
        SELECT
            p.category,
            ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue,
            SUM(oi.quantity) AS units_sold
        FROM fact_order_items oi
        JOIN dim_products p ON oi.product_id = p.product_id
        JOIN fact_orders  o ON oi.order_id   = o.order_id
        WHERE o.order_status = 'Delivered'
        GROUP BY p.category
        ORDER BY revenue DESC
    """,
    "Monthly Revenue (aggregation + partition pruning)": """
        SELECT
            order_year, order_month,
            ROUND(SUM(total_amount), 2) AS monthly_revenue,
            COUNT(*) AS order_count
        FROM fact_orders
        WHERE order_status = 'Delivered'
        GROUP BY order_year, order_month
        ORDER BY order_year, order_month
    """,
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_benchmark():
    results = []

    print("\n=== Hive Query Benchmark ===\n")
    print("NOTE: These times reflect end-to-end Hive execution including")
    print("      MapReduce/Tez job scheduling overhead.  Hive is optimised")
    print("      for throughput on large datasets, not low-latency single queries.\n")

    for query_name, query in BENCHMARKS.items():
        print(f"Running: {query_name}")
        try:
            t0 = time.time()
            df = execute_query(query)
            elapsed = round(time.time() - t0, 2)
            rows = len(df)
            print(f"  → {rows} rows returned in {elapsed}s\n")
            results.append({
                "Query": query_name,
                "Rows Returned": rows,
                "Time (s)": elapsed,
            })
        except HiveConnectionError as e:
            print(f"  ✗ Connection error: {e}\n")
        except Exception as e:
            print(f"  ✗ Query error: {e}\n")

    if results:
        print("\nSummary")
        print("-" * 70)
        result_df = pd.DataFrame(results)
        print(result_df.to_string(index=False))
        print()


if __name__ == "__main__":
    run_benchmark()
