"""Generate a sample SQLite database (Chinook-style) for the DataAssistant demo.

Creates: customers, products, orders, order_items
Realistic enough to demonstrate joins, aggregations, date filters.
"""
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DEFAULT_DB_PATH = Path.cwd() / "sample.db"


def seed_db(db_path: Path = DEFAULT_DB_PATH, seed: int = 42) -> Path:
    """Create and populate the sample database. Returns the path."""
    random.seed(seed)
    db_path = Path(db_path)
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Schema
    cursor.executescript("""
    CREATE TABLE customers (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        country TEXT NOT NULL,
        signup_date TEXT NOT NULL
    );

    CREATE TABLE products (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL,
        active INTEGER NOT NULL DEFAULT 1
    );

    CREATE TABLE orders (
        id INTEGER PRIMARY KEY,
        customer_id INTEGER NOT NULL,
        order_date TEXT NOT NULL,
        status TEXT NOT NULL,
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    );

    CREATE TABLE order_items (
        id INTEGER PRIMARY KEY,
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id),
        FOREIGN KEY (product_id) REFERENCES products(id)
    );

    CREATE INDEX idx_orders_date ON orders(order_date);
    CREATE INDEX idx_orders_customer ON orders(customer_id);
    CREATE INDEX idx_items_order ON order_items(order_id);
    """)

    # Customers
    countries = ["US", "UK", "Canada", "Germany", "France", "Japan", "Australia", "India"]
    for i in range(1, 51):
        cursor.execute(
            "INSERT INTO customers (id, name, email, country, signup_date) VALUES (?, ?, ?, ?, ?)",
            (
                i,
                f"Customer {i}",
                f"customer{i}@example.com",
                random.choice(countries),
                (datetime.utcnow() - timedelta(days=random.randint(30, 730))).strftime("%Y-%m-%d"),
            ),
        )

    # Products
    products = [
        ("Premium Plan", "Subscription", 49.99),
        ("Basic Plan", "Subscription", 9.99),
        ("Enterprise Plan", "Subscription", 199.99),
        ("API Credits 1k", "Credits", 10.00),
        ("API Credits 10k", "Credits", 90.00),
        ("API Credits 100k", "Credits", 800.00),
        ("Setup Service", "Service", 500.00),
        ("Training Session", "Service", 250.00),
        ("Annual Support", "Support", 1200.00),
        ("Quarterly Support", "Support", 350.00),
    ]
    for i, (name, category, price) in enumerate(products, start=1):
        cursor.execute(
            "INSERT INTO products (id, name, category, price, active) VALUES (?, ?, ?, ?, 1)",
            (i, name, category, price),
        )

    # Orders + items — last 90 days
    statuses = ["completed", "completed", "completed", "completed", "pending", "refunded"]
    order_id = 1
    item_id = 1
    today = datetime.utcnow()
    for days_ago in range(90):
        order_date = (today - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        # Variable orders per day, more in recent days
        n_orders = random.randint(2, 6) if days_ago < 30 else random.randint(1, 4)
        for _ in range(n_orders):
            customer_id = random.randint(1, 50)
            status = random.choice(statuses)
            cursor.execute(
                "INSERT INTO orders (id, customer_id, order_date, status) VALUES (?, ?, ?, ?)",
                (order_id, customer_id, order_date, status),
            )
            # Each order has 1-3 items
            for _ in range(random.randint(1, 3)):
                product_id = random.randint(1, len(products))
                quantity = random.randint(1, 4)
                unit_price = products[product_id - 1][2]
                cursor.execute(
                    "INSERT INTO order_items (id, order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?, ?)",
                    (item_id, order_id, product_id, quantity, unit_price),
                )
                item_id += 1
            order_id += 1

    conn.commit()
    conn.close()
    return db_path


if __name__ == "__main__":
    path = seed_db()
    print(f"Seeded database at {path}")
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    for table in ["customers", "products", "orders", "order_items"]:
        count = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {count} rows")
    conn.close()
