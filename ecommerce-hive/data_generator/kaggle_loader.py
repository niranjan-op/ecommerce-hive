"""
kaggle_loader.py
----------------
Transforms the Olist Brazilian E-Commerce dataset into the schema used by
this project's Hive tables and pandas analytics.

Dataset: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
  ~99,000 real orders placed in Brazil, 2016-2018

Every value written is taken from the Olist files; nothing is invented.
Columns Olist does not have (customer name, age, gender) are not produced.

Usage:
    # If you have the zip (e.g. archive.zip), run:
    #   python data_generator/kaggle_loader.py --zip path/to/archive.zip
    #
    # If raw CSVs are already in data/olist_raw/, just run:
    #   python data_generator/kaggle_loader.py
    #
    # To download via Kaggle API (requires ~/.kaggle/kaggle.json):
    #   python data_generator/kaggle_loader.py --download

Output:
    data/customers.csv    customer_id, city, state
    data/products.csv     product_id, product_name, category, price
    data/orders.csv       order_id, customer_id, order_date, order_status, total_amount
    data/order_items.csv  order_id, product_id, quantity, unit_price
    data/payments.csv     payment_id, order_id, payment_method,
                          payment_installments, payment_value, payment_date
"""

import argparse
import os
import sys
import zipfile

import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, "..")
DATA_DIR     = os.path.abspath(os.path.join(PROJECT_ROOT, "data"))
RAW_DIR      = os.path.join(DATA_DIR, "olist_raw")

KAGGLE_DATASET = "olistbr/brazilian-ecommerce"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_raw(name):
    path = os.path.join(RAW_DIR, name)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Missing: {path}\n"
            f"Extract the Olist zip to {RAW_DIR} and re-run."
        )
    return pd.read_csv(path)


def extract_zip(zip_path):
    os.makedirs(RAW_DIR, exist_ok=True)
    print(f"  Extracting {zip_path} ...")
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(RAW_DIR)
    print(f"  Extracted to {RAW_DIR}")


def download_via_api():
    os.makedirs(RAW_DIR, exist_ok=True)
    marker = os.path.join(RAW_DIR, "olist_orders_dataset.csv")
    if os.path.exists(marker):
        print("  Raw Olist files already present -- skipping download.")
        return

    kaggle_json = os.path.expanduser("~/.kaggle/kaggle.json")
    if not os.path.exists(kaggle_json):
        print()
        print("  ERROR: Kaggle API credentials not found.")
        print(f"  Expected: {kaggle_json}")
        print()
        print("  To set up:")
        print("    1. Go to https://www.kaggle.com/settings")
        print("    2. Click 'Create New Token' under 'API'")
        print(f"    3. Save kaggle.json to {kaggle_json}")
        sys.exit(1)

    from kaggle.api.kaggle_api_extended import KaggleApi

    print(f"  Downloading {KAGGLE_DATASET} ...")
    api = KaggleApi()
    api.authenticate()
    api.dataset_download_files(KAGGLE_DATASET, path=RAW_DIR, unzip=True)
    print("  Download complete.")


def pretty(s: pd.Series) -> pd.Series:
    """'health_beauty' -> 'Health Beauty', 'sao paulo' -> 'Sao Paulo'."""
    return s.str.replace("_", " ").str.title()


def to_date(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce").dt.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Transform
# ---------------------------------------------------------------------------

def transform():
    print("  Loading raw Olist CSVs ...")
    raw_cust   = load_raw("olist_customers_dataset.csv")
    raw_orders = load_raw("olist_orders_dataset.csv")
    raw_items  = load_raw("olist_order_items_dataset.csv")
    raw_pay    = load_raw("olist_order_payments_dataset.csv")
    raw_prod   = load_raw("olist_products_dataset.csv")
    transl     = load_raw("product_category_name_translation.csv")

    print(f"  Raw rows: customers={len(raw_cust):,}  orders={len(raw_orders):,}  "
          f"items={len(raw_items):,}  products={len(raw_prod):,}  payments={len(raw_pay):,}")

    # ------------------------------------------------------------------
    # CUSTOMERS
    # Olist has one customer_id per order; customer_unique_id is the person.
    # The dimension holds one row per person with integer ids.
    # ------------------------------------------------------------------
    unique_cust = raw_cust.drop_duplicates("customer_unique_id").reset_index(drop=True)
    uid_to_int  = {uid: i + 1 for i, uid in enumerate(unique_cust["customer_unique_id"])}
    cid_to_int  = {cid: uid_to_int[uid]
                   for cid, uid in zip(raw_cust["customer_id"], raw_cust["customer_unique_id"])}

    customers = pd.DataFrame({
        "customer_id": unique_cust["customer_unique_id"].map(uid_to_int),
        "city":        pretty(unique_cust["customer_city"]),
        "state":       unique_cust["customer_state"],      # e.g. SP, RJ, MG
    })

    # ------------------------------------------------------------------
    # PRODUCTS
    # Olist has no product names, so the label is the English category plus
    # the first 8 characters of Olist's own product id.
    # ------------------------------------------------------------------
    cat_en   = dict(zip(transl["product_category_name"],
                        transl["product_category_name_english"]))
    category = pretty(
        raw_prod["product_category_name"].map(lambda c: cat_en.get(c, c))
    ).fillna("Unknown")

    prod_id_map = {pid: i + 1 for i, pid in enumerate(raw_prod["product_id"])}
    avg_price   = raw_items.groupby("product_id")["price"].mean()

    products = pd.DataFrame({
        "product_id":   raw_prod["product_id"].map(prod_id_map),
        "product_name": category + " (" + raw_prod["product_id"].str[:8] + ")",
        "category":     category,
        "price":        raw_prod["product_id"].map(avg_price).round(2),
    })

    # ------------------------------------------------------------------
    # ORDERS
    # total_amount = sum of item price + freight for the order.
    # ------------------------------------------------------------------
    order_id_map = {oid: i + 1 for i, oid in enumerate(raw_orders["order_id"])}
    order_totals = (raw_items["price"] + raw_items["freight_value"]) \
        .groupby(raw_items["order_id"]).sum()

    orders = pd.DataFrame({
        "order_id":     raw_orders["order_id"].map(order_id_map),
        "customer_id":  raw_orders["customer_id"].map(cid_to_int),
        "order_date":   to_date(raw_orders["order_purchase_timestamp"]),
        "order_status": pretty(raw_orders["order_status"]),  # Delivered, Shipped, Canceled, ...
        "total_amount": raw_orders["order_id"].map(order_totals).fillna(0).round(2),
    })

    # ------------------------------------------------------------------
    # ORDER ITEMS
    # Olist has one row per unit sold, so quantity = rows per order+product.
    # ------------------------------------------------------------------
    items = (raw_items.groupby(["order_id", "product_id"])
             .agg(quantity=("order_item_id", "count"), unit_price=("price", "first"))
             .reset_index())

    order_items = pd.DataFrame({
        "order_id":   items["order_id"].map(order_id_map),
        "product_id": items["product_id"].map(prod_id_map),
        "quantity":   items["quantity"],
        "unit_price": items["unit_price"].round(2),
    })

    # ------------------------------------------------------------------
    # PAYMENTS
    # One row per payment (an order can be paid in several parts).
    # payment_date = when Olist approved the order.
    # ------------------------------------------------------------------
    approved = dict(zip(raw_orders["order_id"],
                        to_date(raw_orders["order_approved_at"])
                        .fillna(to_date(raw_orders["order_purchase_timestamp"]))))

    payments = pd.DataFrame({
        "payment_id":           range(1, len(raw_pay) + 1),
        "order_id":             raw_pay["order_id"].map(order_id_map),
        "payment_method":       pretty(raw_pay["payment_type"]),  # Credit Card, Boleto, ...
        "payment_installments": raw_pay["payment_installments"],
        "payment_value":        raw_pay["payment_value"].round(2),
        "payment_date":         raw_pay["order_id"].map(approved),
    })

    return customers, products, orders, order_items, payments


# ---------------------------------------------------------------------------
# Write CSVs
# ---------------------------------------------------------------------------

def write_csv(df, name):
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, f"{name}.csv")
    df.to_csv(path, index=False)
    size_mb = os.path.getsize(path) / (1024 * 1024)
    print(f"    Wrote {len(df):>8,} rows -> {name}.csv  ({size_mb:.1f} MB)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    import time

    parser = argparse.ArgumentParser(description="Olist Kaggle dataset loader")
    parser.add_argument("--zip",      help="Path to the Olist zip file (e.g. archive.zip)")
    parser.add_argument("--download", action="store_true",
                        help="Download via Kaggle API (requires ~/.kaggle/kaggle.json)")
    args = parser.parse_args()

    t0 = time.time()
    print("\n=== Olist Kaggle Dataset Loader ===")
    print(f"Output : {DATA_DIR}\n")

    # Step 1: get raw files
    print("Step 1 -- Prepare raw data")
    marker = os.path.join(RAW_DIR, "olist_orders_dataset.csv")
    if args.zip:
        extract_zip(args.zip)
    elif args.download:
        download_via_api()
    elif os.path.exists(marker):
        print("  Raw Olist files already present in olist_raw/ -- skipping.")
    else:
        print(f"  ERROR: No raw data found at {RAW_DIR}")
        print("  Options:")
        print("    --zip path/to/archive.zip    (use a downloaded zip)")
        print("    --download                   (download via Kaggle API)")
        sys.exit(1)

    # Step 2: transform
    print("\nStep 2 -- Transform to project schema")
    customers, products, orders, order_items, payments = transform()

    # Step 3: write
    print("\nStep 3 -- Write CSVs")
    write_csv(customers,   "customers")
    write_csv(products,    "products")
    write_csv(orders,      "orders")
    write_csv(order_items, "order_items")
    write_csv(payments,    "payments")

    print(f"\nDone in {time.time()-t0:.1f}s")
    print()


if __name__ == "__main__":
    main()
