"""Source and database data-quality checks."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy.engine import Connection, Engine

from .config import EXPECTED_FILES

SOURCE_KEYS = {
    "customers": ["customer_id"],
    "sellers": ["seller_id"],
    "products": ["product_id"],
    "category_translation": ["product_category_name"],
    "orders": ["order_id"],
    "order_items": ["order_id", "order_item_id"],
    "payments": ["order_id", "payment_sequential"],
    # Olist review_id is reused across orders; the natural key is the pair.
    "reviews": ["review_id", "order_id"],
}

REQUIRED_COLUMNS = {
    "customers": [
        "customer_id",
        "customer_unique_id",
        "customer_zip_code_prefix",
        "customer_city",
        "customer_state",
    ],
    "geolocation": [
        "geolocation_zip_code_prefix",
        "geolocation_lat",
        "geolocation_lng",
        "geolocation_city",
        "geolocation_state",
    ],
    "order_items": [
        "order_id",
        "order_item_id",
        "product_id",
        "seller_id",
        "shipping_limit_date",
        "price",
        "freight_value",
    ],
    "payments": [
        "order_id",
        "payment_sequential",
        "payment_type",
        "payment_installments",
        "payment_value",
    ],
    "reviews": [
        "review_id",
        "order_id",
        "review_score",
        "review_comment_title",
        "review_comment_message",
        "review_creation_date",
        "review_answer_timestamp",
    ],
    "orders": [
        "order_id",
        "customer_id",
        "order_status",
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "products": [
        "product_id",
        "product_category_name",
        "product_name_lenght",
        "product_description_lenght",
        "product_photos_qty",
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm",
    ],
    "sellers": ["seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"],
    "category_translation": ["product_category_name", "product_category_name_english"],
}


def validate_data_dir(folder: Path) -> dict[str, Path]:
    missing = [name for name in EXPECTED_FILES.values() if not (folder / name).is_file()]
    if missing:
        raise FileNotFoundError(
            f"Missing required Olist CSV files in {folder}: {', '.join(missing)}"
        )
    paths = {key: folder / filename for key, filename in EXPECTED_FILES.items()}
    for key, path in paths.items():
        columns = pd.read_csv(path, nrows=0).columns.tolist()
        absent = sorted(set(REQUIRED_COLUMNS[key]) - set(columns))
        if absent:
            raise ValueError(f"{path.name} is missing required columns: {', '.join(absent)}")
        key_columns = SOURCE_KEYS.get(key)
        if key_columns:
            keys = pd.read_csv(path, usecols=key_columns)
            if keys.duplicated(key_columns).any():
                raise ValueError(
                    f"{path.name} contains duplicate key values for: {', '.join(key_columns)}"
                )
    return paths


def check_connection(connection: Connection) -> list[dict[str, object]]:
    """Run named quality checks on a connection, raising for failed invariants."""
    checks = {
        "duplicate customer ids": "SELECT count(*) FROM (SELECT customer_id FROM customers GROUP BY 1 HAVING count(*) > 1) q",
        "duplicate order ids": "SELECT count(*) FROM (SELECT order_id FROM orders GROUP BY 1 HAVING count(*) > 1) q",
        "orphan order customers": "SELECT count(*) FROM orders o LEFT JOIN customers c USING (customer_id) WHERE c.customer_id IS NULL",
        "orphan item orders": "SELECT count(*) FROM order_items i LEFT JOIN orders o USING (order_id) WHERE o.order_id IS NULL",
        "orphan item products": "SELECT count(*) FROM order_items i LEFT JOIN products p USING (product_id) WHERE p.product_id IS NULL",
        "orphan item sellers": "SELECT count(*) FROM order_items i LEFT JOIN sellers s USING (seller_id) WHERE s.seller_id IS NULL",
        "invalid review scores": "SELECT count(*) FROM reviews WHERE review_score NOT BETWEEN 1 AND 5",
        "negative item amounts": "SELECT count(*) FROM order_items WHERE price < 0 OR freight_value < 0",
        "negative payment values": "SELECT count(*) FROM payments WHERE payment_value < 0",
    }
    results = []
    for name, sql in checks.items():
        count = int(connection.exec_driver_sql(sql).scalar_one())
        results.append({"check": name, "violations": count, "passed": count == 0})
    failures = [r for r in results if not r["passed"]]
    if failures:
        raise ValueError(
            "Database quality checks failed: "
            + "; ".join(f"{x['check']} ({x['violations']})" for x in failures)
        )
    return results


def check_database(engine: Engine) -> list[dict[str, object]]:
    """Run quality checks using a short-lived connection from an engine."""
    with engine.connect() as connection:
        return check_connection(connection)
