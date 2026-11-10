from pathlib import Path
import pandas as pd
import pytest

from olist_analytics.etl import load_frame
from olist_analytics.quality import validate_data_dir

def test_validate_data_dir_reports_missing_inputs(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="Missing required Olist CSV files"):
        validate_data_dir(tmp_path)

def test_load_frame_parses_order_timestamps(tmp_path: Path):
    path = tmp_path / "orders.csv"
    pd.DataFrame({
        "order_purchase_timestamp": ["2017-01-01 10:00:00"],
        "order_approved_at": [None], "order_delivered_carrier_date": [None],
        "order_delivered_customer_date": [None], "order_estimated_delivery_date": ["2017-01-10 00:00:00"],
    }).to_csv(path, index=False)
    frame = load_frame(path, "orders")
    assert pd.api.types.is_datetime64_any_dtype(frame["order_purchase_timestamp"])
    assert pd.isna(frame.loc[0, "order_approved_at"])

def test_validate_data_dir_accepts_complete_minimal_files(tmp_path: Path):
    from olist_analytics.quality import REQUIRED_COLUMNS
    from olist_analytics.config import EXPECTED_FILES
    for key, name in EXPECTED_FILES.items():
        pd.DataFrame(columns=REQUIRED_COLUMNS[key]).to_csv(tmp_path / name, index=False)
    result = validate_data_dir(tmp_path)
    assert set(result) == set(EXPECTED_FILES)


def _write_minimal_dataset(folder: Path, review_rows):
    from olist_analytics.config import EXPECTED_FILES
    from olist_analytics.quality import REQUIRED_COLUMNS
    for key, name in EXPECTED_FILES.items():
        rows = review_rows if key == "reviews" else []
        pd.DataFrame(rows, columns=REQUIRED_COLUMNS[key]).to_csv(folder / name, index=False)

def test_review_id_may_repeat_across_orders(tmp_path: Path):
    _write_minimal_dataset(tmp_path, [
        {"review_id": "same-review", "order_id": "order-1", "review_score": 5},
        {"review_id": "same-review", "order_id": "order-2", "review_score": 4},
    ])
    assert "reviews" in validate_data_dir(tmp_path)

def test_duplicate_review_and_order_pair_is_rejected(tmp_path: Path):
    _write_minimal_dataset(tmp_path, [
        {"review_id": "same-review", "order_id": "order-1", "review_score": 5},
        {"review_id": "same-review", "order_id": "order-1", "review_score": 4},
    ])
    with pytest.raises(ValueError, match="duplicate key values for: review_id, order_id"):
        validate_data_dir(tmp_path)
