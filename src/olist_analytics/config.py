"""Runtime configuration loaded from environment and optional .env file."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

EXPECTED_FILES = {
    "customers": "olist_customers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}


def data_dir(override: str | None = None) -> Path:
    value = override or os.getenv("DATA_DIR")
    if not value:
        raise ValueError("Set DATA_DIR in .env or pass --data-dir pointing to the Olist CSV folder")
    return Path(value).expanduser().resolve()


def database_url() -> str:
    value = os.getenv("DATABASE_URL")
    if not value:
        raise ValueError("Set DATABASE_URL in .env, for example postgresql+psycopg://.../olist")
    return value
