import os 
import sqlite3

DB_PATH = os.path.join("data", "sample.db")

def main():
    os.makedirs("data", exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS customers")
    cur.execute("DROP TABLE IF EXISTS orders")

    cur.execute(
        '''
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY),
            name TEXT NOT NULL,
            region TEXT NOT NULL,
            signup_date TEXT
        '''
    )

    cur.execute(
        """
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            product TEXT NOT NULL,
            amount REAL NOT NULL,
            order_date TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
        """
    )

    customers = [
        (1, "Acme Corp", "North", "2023-01-15"),
        (2, "Beta LLC", "South", "2023-03-22"),
        (3, "Gamma Inc", "North", "2023-06-10"),
        (4, "Delta Co", "West", "2023-09-05"),
    ]
    cur.executemany("INSERT INTO customers VALUES (?, ?, ?, ?)", customers)

    orders = [
        (1, 1, "Widget", 99.50, "2024-01-10"),
        (2, 1, "Gadget", 149.00, "2024-02-14"),
        (3, 2, "Widget", 75.25, "2024-01-20"),
        (4, 3, "Doohickey", 220.00, "2024-03-01"),
        (5, 4, "Gadget", 310.75, "2024-02-28"),
        (6, 2, "Doohickey", 88.10, "2024-03-15"),
        (7, 3, "Widget", 55.00, "2024-04-02"),
        (8, 1, "Gadget", 199.99, "2024-04-11"),
    ]
    cur.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?)", orders)

    conn.commit()
    conn.close()
    print(f"Seeded {DB_PATH} with {len(customers)} customers and {len(orders)} orders.")
