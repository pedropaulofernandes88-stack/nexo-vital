import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def test_observatory_json_has_academic_invariants():
    raw = (ROOT / "dashboard" / "data" / "observatory.json").read_text(encoding="utf-8")
    assert "NaN" not in raw and "Infinity" not in raw
    data = json.loads(raw)
    assert data["meta"]["causal_claim"] is False
    assert data["coverage"]["analytical_countries"] >= 150
    metrics = data["model"]["metrics"]
    assert 0 < metrics["loo_predictive_r_squared"] < metrics["r_squared_association"] < 1
    assert metrics["conformal_empirical_coverage"] >= metrics["conformal_nominal_coverage"]
    assert (
        metrics["countries_below"] + metrics["countries_within"] + metrics["countries_above"]
        == metrics["n_countries"]
    )
    assert len(data["model"]["repeated_cv_summary"]) == 3
    assert len(data["segmentation"]["cluster_selection"]) == 7


def test_exported_tables_have_expected_cardinality():
    countries = pd.read_csv(ROOT / "artifacts" / "tables" / "country_results.csv")
    cv = pd.read_csv(ROOT / "artifacts" / "tables" / "repeated_cross_validation.csv")
    bootstrap = pd.read_csv(ROOT / "artifacts" / "tables" / "cluster_bootstrap_stability.csv")
    assert len(countries) == 159
    assert len(cv) == 200
    assert len(bootstrap) == 500
    assert not countries.duplicated("country_iso3").any()
