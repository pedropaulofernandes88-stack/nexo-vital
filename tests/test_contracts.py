from pathlib import Path

import pandas as pd
import pytest

from nexo_vital.contracts import ContractError, coverage, load_global_panel

ROOT = Path(__file__).resolve().parents[1]


def test_snapshot_respects_canonical_contract():
    panel = load_global_panel(ROOT / "data" / "snapshots" / "global_indicators_2000_2022.csv")
    result = coverage(panel)
    assert result.rows > 30_000
    assert result.countries >= 200
    assert result.indicators == 9
    assert result.min_year == 2000
    assert result.max_year == 2022


def test_duplicate_country_year_indicator_is_rejected(tmp_path):
    source = pd.read_csv(ROOT / "data" / "snapshots" / "global_indicators_2000_2022.csv", nrows=2)
    invalid = pd.concat([source, source.iloc[[0]]], ignore_index=True)
    path = tmp_path / "invalid.csv"
    invalid.to_csv(path, index=False)
    with pytest.raises(ContractError, match="duplicada"):
        load_global_panel(path)
