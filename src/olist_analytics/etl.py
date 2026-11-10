"""Chunked and repeatable CSV-to-PostgreSQL pipeline."""
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text

from .config import data_dir, database_url
from .quality import validate_data_dir, check_database

ORDER = ["customers", "sellers", "products", "category_translation", "orders", "order_items", "payments", "reviews", "geolocation"]
TABLES = {"category_translation": "category_translation"}
DATE_COLUMNS = {
    "orders": ["order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date", "order_delivered_customer_date", "order_estimated_delivery_date"],
    "order_items": ["shipping_limit_date"], "reviews": ["review_creation_date", "review_answer_timestamp"],
}
NUMERIC_COLUMNS = {"order_items": ["price", "freight_value"], "payments": ["payment_value"], "geolocation": ["geolocation_lat", "geolocation_lng"]}

def load_frame(path: Path, table: str) -> pd.DataFrame:
    frame = pd.read_csv(path)
    for column in DATE_COLUMNS.get(table, []):
        frame[column] = pd.to_datetime(frame[column], errors="coerce")
    for column in NUMERIC_COLUMNS.get(table, []):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if table == "order_items":
        frame["order_item_id"] = frame["order_item_id"].astype("int64")
    if table == "payments":
        frame["payment_sequential"] = frame["payment_sequential"].astype("int64")
        frame["payment_installments"] = frame["payment_installments"].astype("int64")
    if table == "reviews":
        frame["review_score"] = frame["review_score"].astype("int64")
    return frame

def run_etl(folder: Path, url: str) -> list[dict[str, object]]:
    paths = validate_data_dir(folder)  # Fail before touching database if input is incomplete.
    engine = create_engine(url, pool_pre_ping=True)
    schema_sql = Path(__file__).resolve().parents[2] / "sql" / "schema.sql"
    analytics_sql = Path(__file__).resolve().parents[2] / "sql" / "analytics.sql"
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql(schema_sql.read_text())
            conn.exec_driver_sql("TRUNCATE TABLE geolocation, reviews, payments, order_items, orders, category_translation, products, sellers, customers CASCADE")
            for name in ORDER:
                frame = load_frame(paths[name], name)
                # 5k keeps multi-row inserts below PostgreSQL's bind-parameter limit.
                frame.to_sql(name, conn, if_exists="append", index=False, chunksize=5_000, method="multi")
                print(f"Loaded {len(frame):,} rows into {name}")
            conn.exec_driver_sql(analytics_sql.read_text())
        results = check_database(engine)
        print(f"Data quality: {len(results)} checks passed")
        return results
    finally:
        engine.dispose()

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", help="Folder containing the nine Olist CSV files")
    parser.add_argument("--database-url", help="SQLAlchemy PostgreSQL URL (defaults to DATABASE_URL)")
    args = parser.parse_args()
    run_etl(data_dir(args.data_dir), args.database_url or database_url())

if __name__ == "__main__":
    main()
