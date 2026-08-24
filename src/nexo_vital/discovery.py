"""Pre-specified exploratory checks with multiplicity correction."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from statsmodels.stats.multitest import multipletests

from .features import nearest_indicator


def residual_discovery(
    countries: pd.DataFrame, panel: pd.DataFrame, reference_year: int
) -> pd.DataFrame:
    candidates = ("physicians_density", "expected_schooling", "population")
    augmented = countries[["country_iso3", "residual_loo"]].copy()
    for indicator in candidates:
        augmented = augmented.merge(
            nearest_indicator(panel, indicator, reference_year), on="country_iso3", how="left"
        )
    augmented["log_population"] = np.log(augmented["population"])
    tests = {
        "physicians_density": "physicians_density",
        "expected_schooling": "expected_schooling",
        "log_population": "log_population",
    }
    rows: list[dict[str, float | int | str]] = []
    for hypothesis, column in tests.items():
        valid = augmented[["residual_loo", column]].dropna()
        statistic, p_value = spearmanr(valid["residual_loo"], valid[column])
        rows.append(
            {
                "hypothesis": hypothesis,
                "n": len(valid),
                "spearman_rho": float(statistic),
                "p_value_raw": float(p_value),
            }
        )
    result = pd.DataFrame(rows)
    reject, adjusted, _, _ = multipletests(result["p_value_raw"], alpha=0.05, method="fdr_bh")
    result["p_value_fdr_bh"] = adjusted
    result["reject_fdr_05"] = reject
    return result.sort_values("p_value_fdr_bh")
