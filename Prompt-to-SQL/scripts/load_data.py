import sqlite3
from pathlib import Path 
import pandas as pd 

ROOT = Path(__file__).resolve().parent.parent 
RAW_DATA_DIR = ROOT / "data" / "raw"
DB_PATH = ROOT / "data" / "olist.db"

TABLE_MAPPING = {
    "olist_orders_dataset.csv": "orders",
    "olist_order_items_dataset.csv": "order_items",
    "olist_products_dataset.csv": "products",
    "olist_customers_dataset.csv": "customers",
    "olist_sellers_dataset.csv": "sellers",
    "olist_order_payments_dataset.csv": "order_payments",
    "olist_order_reviews_dataset.csv": "order_reviews",
    "olist_geolocation_dataset.csv": "geolocation",
    "product_category_name_translation.csv": "category_translation",
}

def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df 

def load_all() -> None:
    DB_PATH.parent.mkdir(parents = True, exist_ok = True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    for csv_name, table_name in TABLE_MAPPING.items():
        csv_path = RAW_DATA_DIR / csv_name
        if not csv_path.exists():
            print(f"Skipping {csv_name}")
            continue 
        df = clean_columns(pd.read_csv(csv_path))
        df.to_sql(table_name, conn, if_exists="replace", index = False)
        print(f"{table_name:25s} {len(df):>10,} rows")
    conn.close()
    print(f"\nDatabase ready: {DB_PATH}")


if __name__ == "__main__":
    load_all()
