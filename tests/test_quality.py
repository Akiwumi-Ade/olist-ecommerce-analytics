from pathlib import Path

import pandas as pd
import pytest

from olist_analytics.etl import load_frame
from olist_analytics.quality import check_connection, validate_data_dir


def test_validate_data_dir_reports_missing_inputs(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="Missing required Olist CSV files"):
        validate_data_dir(tmp_path)


def test_load_frame_parses_order_timestamps(tmp_path: Path):
    path = tmp_path / "orders.csv"
    pd.DataFrame(
        {
            "order_purchase_timestamp": ["2017-01-01 10:00:00"],
            "order_approved_at": [None],
            "order_delivered_carrier_date": [None],
            "order_delivered_customer_date": [None],
            "order_estimated_delivery_date": ["2017-01-10 00:00:00"],
        }
    ).to_csv(path, index=False)
    frame = load_frame(path, "orders")
    assert pd.api.types.is_datetime64_any_dtype(frame["order_purchase_timestamp"])
    assert pd.isna(frame.loc[0, "order_approved_at"])


def test_validate_data_dir_accepts_complete_minimal_files(tmp_path: Path):
    from olist_analytics.config import EXPECTED_FILES
    from olist_analytics.quality import REQUIRED_COLUMNS

    for key, name in EXPECTED_FILES.items():
        pd.DataFrame(columns=REQUIRED_COLUMNS[key]).to_csv(tmp_path / name, index=False)
    result = validate_data_dir(tmp_path)
    assert set(result) == set(EXPECTED_FILES)


def test_validate_data_dir_rejects_missing_schema_column(tmp_path: Path):
    from olist_analytics.config import EXPECTED_FILES
    from olist_analytics.quality import REQUIRED_COLUMNS

    for key, name in EXPECTED_FILES.items():
        columns = REQUIRED_COLUMNS[key]
        if key == "products":
            columns = columns[:-1]
        pd.DataFrame(columns=columns).to_csv(tmp_path / name, index=False)

    with pytest.raises(ValueError, match="olist_products_dataset.csv is missing required columns"):
        validate_data_dir(tmp_path)


def _write_minimal_dataset(folder: Path, review_rows):
    from olist_analytics.config import EXPECTED_FILES
    from olist_analytics.quality import REQUIRED_COLUMNS

    for key, name in EXPECTED_FILES.items():
        rows = review_rows if key == "reviews" else []
        pd.DataFrame(rows, columns=REQUIRED_COLUMNS[key]).to_csv(folder / name, index=False)


def test_review_id_may_repeat_across_orders(tmp_path: Path):
    _write_minimal_dataset(
        tmp_path,
        [
            {"review_id": "same-review", "order_id": "order-1", "review_score": 5},
            {"review_id": "same-review", "order_id": "order-2", "review_score": 4},
        ],
    )
    assert "reviews" in validate_data_dir(tmp_path)


def test_duplicate_review_and_order_pair_is_rejected(tmp_path: Path):
    _write_minimal_dataset(
        tmp_path,
        [
            {"review_id": "same-review", "order_id": "order-1", "review_score": 5},
            {"review_id": "same-review", "order_id": "order-1", "review_score": 4},
        ],
    )
    with pytest.raises(ValueError, match="duplicate key values for: review_id, order_id"):
        validate_data_dir(tmp_path)


class ScalarResult:
    def __init__(self, value: int):
        self.value = value

    def scalar_one(self) -> int:
        return self.value


class FakeConnection:
    def __init__(self, counts: list[int]):
        self.counts = iter(counts)
        self.queries = []

    def exec_driver_sql(self, sql: str) -> ScalarResult:
        self.queries.append(sql)
        return ScalarResult(next(self.counts))


def test_database_quality_checks_pass_when_no_violations():
    connection = FakeConnection([0] * 9)

    results = check_connection(connection)

    assert len(results) == 9
    assert all(result["passed"] for result in results)
    assert len(connection.queries) == 9


def test_database_quality_checks_raise_with_violation_count():
    connection = FakeConnection([0, 2] + [0] * 7)

    with pytest.raises(ValueError, match=r"duplicate order ids \(2\)"):
        check_connection(connection)
