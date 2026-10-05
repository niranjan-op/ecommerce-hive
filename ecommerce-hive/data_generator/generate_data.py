"""
generate_data.py
----------------
Synthetic e-commerce data generator for the Hive analytics project.

Usage:
    python generate_data.py                         # default sizes
    python generate_data.py --orders 1000000        # 1 million orders

Output: CSV files written to ../data/
"""

import argparse
import csv
import os
import random
import time
from datetime import datetime, timedelta

import faker

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_CUSTOMERS   = 10_000
DEFAULT_PRODUCTS    = 2_000
DEFAULT_ORDERS      = 100_000

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

fake = faker.Faker("en_IN")
random.seed(42)
fake.seed_instance(42)

# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

CATEGORIES = [
    "Electronics", "Clothing", "Books",
    "Home & Kitchen", "Sports", "Beauty", "Grocery",
]

CATEGORY_PRODUCTS = {
    "Electronics": [
        "Smartphone", "Laptop", "Tablet", "Smartwatch", "Earbuds",
        "Bluetooth Speaker", "Power Bank", "Webcam", "LED Monitor",
        "Mechanical Keyboard", "Gaming Mouse", "USB Hub", "Router",
        "Hard Disk", "Pen Drive", "Action Camera", "Smart TV",
        "Air Purifier", "Electric Kettle", "Trimmer",
    ],
    "Clothing": [
        "Cotton T-Shirt", "Denim Jeans", "Formal Shirt", "Kurti",
        "Saree", "Leggings", "Jacket", "Hoodie", "Track Pants",
        "Ethnic Kurta", "Salwar Suit", "Casual Shorts", "Polo Shirt",
        "Blazer", "Raincoat", "Sweater", "Cargo Pants", "Churidar",
        "Anarkali Dress", "Jodhpuri Suit",
    ],
    "Books": [
        "Data Structures & Algorithms", "Clean Code", "Python Crash Course",
        "The Alchemist", "Wings of Fire", "Atomic Habits",
        "Rich Dad Poor Dad", "Sapiens", "The Art of War",
        "Operating System Concepts", "Database Management Systems",
        "Machine Learning Basics", "Digital Marketing Handbook",
        "Indian History Vol 1", "Vedic Mathematics",
        "Competitive Programming", "GATE CSE Guide",
        "English Grammar", "Organic Chemistry", "Calculus Made Easy",
    ],
    "Home & Kitchen": [
        "Pressure Cooker", "Non-Stick Pan", "Mixer Grinder",
        "Rice Cooker", "Induction Cooktop", "Microwave Oven",
        "Refrigerator", "Water Purifier", "Vacuum Cleaner",
        "Washing Machine", "Iron Box", "Ceiling Fan", "Table Fan",
        "LED Bulb Pack", "Curtain Set", "Bed Sheet", "Pillow Cover",
        "Dinner Set", "Thermos Flask", "Chopping Board",
    ],
    "Sports": [
        "Cricket Bat", "Football", "Badminton Racket", "Tennis Ball",
        "Yoga Mat", "Skipping Rope", "Dumbbell Set", "Resistance Bands",
        "Gym Gloves", "Running Shoes", "Cycling Helmet", "Knee Guard",
        "Swimming Goggles", "Table Tennis Paddle", "Carrom Board",
        "Chess Set", "Basketball", "Volleyball", "Hockey Stick",
        "Archery Set",
    ],
    "Beauty": [
        "Face Wash", "Moisturizer", "Sunscreen SPF 50", "Lipstick",
        "Foundation", "Mascara", "Kajal", "Face Serum",
        "Hair Conditioner", "Shampoo", "Body Lotion", "Perfume",
        "Nail Paint", "BB Cream", "Compact Powder",
        "Hair Dryer", "Straightener", "Eyeshadow Palette",
        "Blush", "Makeup Remover",
    ],
    "Grocery": [
        "Basmati Rice 5kg", "Whole Wheat Atta", "Toor Dal 1kg",
        "Sunflower Oil 1L", "Mustard Oil 500ml", "Sugar 1kg",
        "Salt 1kg", "Turmeric Powder", "Red Chilli Powder",
        "Coriander Powder", "Garam Masala", "Tea Powder 250g",
        "Coffee Powder 200g", "Biscuit Pack", "Oats 1kg",
        "Honey 500g", "Ghee 500ml", "Coconut Milk", "Cornflakes",
        "Dry Fruits Mix",
    ],
}

CATEGORY_PRICE_RANGE = {
    "Electronics":    (500,  80000),
    "Clothing":       (200,   5000),
    "Books":          (100,   1500),
    "Home & Kitchen": (300,  50000),
    "Sports":         (200,  15000),
    "Beauty":         (100,   5000),
    "Grocery":        (50,    2000),
}

# Indian cities with their states
INDIAN_CITIES = [
    ("Mumbai", "Maharashtra"), ("Delhi", "Delhi"),
    ("Bangalore", "Karnataka"), ("Hyderabad", "Telangana"),
    ("Ahmedabad", "Gujarat"), ("Chennai", "Tamil Nadu"),
    ("Kolkata", "West Bengal"), ("Surat", "Gujarat"),
    ("Pune", "Maharashtra"), ("Jaipur", "Rajasthan"),
    ("Lucknow", "Uttar Pradesh"), ("Kanpur", "Uttar Pradesh"),
    ("Nagpur", "Maharashtra"), ("Indore", "Madhya Pradesh"),
    ("Thane", "Maharashtra"), ("Bhopal", "Madhya Pradesh"),
    ("Visakhapatnam", "Andhra Pradesh"), ("Patna", "Bihar"),
    ("Vadodara", "Gujarat"), ("Ghaziabad", "Uttar Pradesh"),
    ("Ludhiana", "Punjab"), ("Agra", "Uttar Pradesh"),
    ("Nashik", "Maharashtra"), ("Faridabad", "Haryana"),
    ("Meerut", "Uttar Pradesh"), ("Rajkot", "Gujarat"),
    ("Kalyan", "Maharashtra"), ("Vasai", "Maharashtra"),
    ("Varanasi", "Uttar Pradesh"), ("Srinagar", "Jammu & Kashmir"),
    ("Aurangabad", "Maharashtra"), ("Dhanbad", "Jharkhand"),
    ("Amritsar", "Punjab"), ("Navi Mumbai", "Maharashtra"),
    ("Allahabad", "Uttar Pradesh"), ("Ranchi", "Jharkhand"),
    ("Howrah", "West Bengal"), ("Coimbatore", "Tamil Nadu"),
    ("Jabalpur", "Madhya Pradesh"), ("Gwalior", "Madhya Pradesh"),
    ("Vijayawada", "Andhra Pradesh"), ("Jodhpur", "Rajasthan"),
    ("Madurai", "Tamil Nadu"), ("Raipur", "Chhattisgarh"),
    ("Kota", "Rajasthan"), ("Guwahati", "Assam"),
    ("Chandigarh", "Punjab"), ("Solapur", "Maharashtra"),
    ("Hubli", "Karnataka"), ("Mysore", "Karnataka"),
]

ORDER_STATUSES   = ["Delivered", "Delivered", "Delivered", "Cancelled", "Failed", "Returned"]
PAYMENT_METHODS  = ["UPI", "Credit Card", "Debit Card", "Net Banking", "Cash on Delivery", "Wallet"]
PAYMENT_STATUSES = ["Success", "Success", "Success", "Failed", "Pending"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def rand_date(start: datetime, end: datetime) -> datetime:
    delta = end - start
    return start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))


def fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

def generate_customers(n: int):
    print(f"  Generating {n:,} customers …")
    rows = []
    start = datetime(2020, 1, 1)
    end   = datetime(2024, 12, 31)
    for i in range(1, n + 1):
        city, state = random.choice(INDIAN_CITIES)
        rows.append({
            "customer_id":       i,
            "name":              fake.name(),
            "age":               random.randint(18, 65),
            "gender":            random.choice(["Male", "Female"]),
            "city":              city,
            "state":             state,
            "registration_date": fmt(rand_date(start, end)),
        })
    return rows


def generate_products(n: int):
    print(f"  Generating {n:,} products …")
    rows = []
    product_id = 1
    per_cat = n // len(CATEGORIES)
    for cat in CATEGORIES:
        templates = CATEGORY_PRODUCTS[cat]
        lo, hi    = CATEGORY_PRICE_RANGE[cat]
        for j in range(per_cat):
            base_name = templates[j % len(templates)]
            variant   = f"({fake.word().capitalize()})" if j >= len(templates) else ""
            rows.append({
                "product_id":   product_id,
                "product_name": f"{base_name} {variant}".strip(),
                "category":     cat,
                "price":        round(random.uniform(lo, hi), 2),
            })
            product_id += 1
    return rows


def generate_orders_and_items(n_orders: int, customers, products):
    print(f"  Generating {n_orders:,} orders …")
    orders      = []
    order_items = []
    payments    = []

    product_map = {p["product_id"]: p for p in products}
    customer_ids = [c["customer_id"] for c in customers]

    start    = datetime(2022, 1, 1)
    end      = datetime(2024, 12, 31)
    item_id  = 1
    pay_id   = 1

    for oid in range(1, n_orders + 1):
        order_date     = rand_date(start, end)
        order_status   = random.choice(ORDER_STATUSES)
        customer_id    = random.choice(customer_ids)
        n_items        = random.choices([1, 2, 3, 4, 5], weights=[40, 30, 15, 10, 5])[0]
        selected       = random.sample(products, min(n_items, len(products)))

        total_amount = 0.0
        for prod in selected:
            qty        = random.randint(1, 5)
            unit_price = prod["price"]
            total_amount += qty * unit_price
            order_items.append({
                "order_id":   oid,
                "product_id": prod["product_id"],
                "quantity":   qty,
                "unit_price": round(unit_price, 2),
            })
            item_id += 1

        orders.append({
            "order_id":     oid,
            "customer_id":  customer_id,
            "order_date":   fmt(order_date),
            "order_status": order_status,
            "total_amount": round(total_amount, 2),
        })

        pay_date   = order_date + timedelta(minutes=random.randint(1, 60))
        pay_status = "Success" if order_status == "Delivered" else random.choice(PAYMENT_STATUSES)
        payments.append({
            "payment_id":     pay_id,
            "order_id":       oid,
            "payment_method": random.choice(PAYMENT_METHODS),
            "payment_status": pay_status,
            "payment_date":   fmt(pay_date),
        })
        pay_id += 1

        if oid % 10_000 == 0:
            print(f"    … {oid:,} orders done")

    return orders, order_items, payments


# ---------------------------------------------------------------------------
# CSV writers
# ---------------------------------------------------------------------------

def write_csv(filename: str, rows: list, fieldnames: list):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    size_mb = os.path.getsize(path) / (1024 * 1024)
    print(f"    Wrote {len(rows):,} rows -> {filename}  ({size_mb:.1f} MB)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Synthetic e-commerce data generator")
    parser.add_argument("--customers", type=int, default=DEFAULT_CUSTOMERS)
    parser.add_argument("--products",  type=int, default=DEFAULT_PRODUCTS)
    parser.add_argument("--orders",    type=int, default=DEFAULT_ORDERS)
    args = parser.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)

    t0 = time.time()
    print("\n=== E-Commerce Data Generator ===\n")

    customers = generate_customers(args.customers)
    write_csv("customers.csv", customers,
              ["customer_id", "name", "age", "gender", "city", "state", "registration_date"])

    products = generate_products(args.products)
    write_csv("products.csv", products,
              ["product_id", "product_name", "category", "price"])

    orders, order_items, payments = generate_orders_and_items(args.orders, customers, products)

    write_csv("orders.csv", orders,
              ["order_id", "customer_id", "order_date", "order_status", "total_amount"])
    write_csv("order_items.csv", order_items,
              ["order_id", "product_id", "quantity", "unit_price"])
    write_csv("payments.csv", payments,
              ["payment_id", "order_id", "payment_method", "payment_status", "payment_date"])

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.1f}s  |  "
          f"orders={len(orders):,}  items={len(order_items):,}  payments={len(payments):,}")
    print(f"Files written to: {os.path.abspath(DATA_DIR)}\n")


if __name__ == "__main__":
    main()
