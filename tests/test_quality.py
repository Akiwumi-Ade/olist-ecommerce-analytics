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
