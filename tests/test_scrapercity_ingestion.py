from __future__ import annotations

import csv
from pathlib import Path

import pytest

from scripts.ingest_scrapercity_phase1 import EXPECTED_COLUMNS, _load_rows


def test_scrapercity_loader_preserves_one_based_row_numbers(tmp_path: Path) -> None:
    path = tmp_path / "leads.csv"
    columns = [f"column_{index}" for index in range(EXPECTED_COLUMNS)]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerow({columns[0]: "first"})
        writer.writerow({columns[0]: "second"})

    rows = _load_rows(path, 0)

    assert [row_number for row_number, _ in rows] == [1, 2]
    assert rows[0][1][columns[0]] == "first"


def test_scrapercity_loader_rejects_schema_drift(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("a,b\n1,2\n", encoding="utf-8")

    with pytest.raises(ValueError, match="expected 42 columns"):
        _load_rows(path, 0)
