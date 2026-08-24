"""Transformations declared once and reused in every model and validation fold."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .catalog import LOG_FEATURES


def design_matrix(frame: pd.DataFrame, features: tuple[str, ...]) -> pd.DataFrame:
    matrix = frame.loc[:, features].astype(float).copy()
    for name in features:
        if name in LOG_FEATURES:
            if matrix[name].le(0).any():
                raise ValueError(f"{name} precisa ser estritamente positivo para log")
            matrix[name] = np.log(matrix[name])
    return matrix


def nearest_indicator(
    panel: pd.DataFrame,
    indicator_id: str,
    reference_year: int,
    max_distance: int = 3,
) -> pd.DataFrame:
    subset = panel.loc[panel["indicator_id"].eq(indicator_id)].copy()
    subset["distance"] = (subset["year"] - reference_year).abs()
    subset = subset.loc[subset["distance"].le(max_distance)]
    subset = subset.sort_values(["country_iso3", "distance", "year"], ascending=[True, True, False])
    return subset.drop_duplicates("country_iso3")[["country_iso3", "year", "value"]].rename(
        columns={"year": f"{indicator_id}_year", "value": indicator_id}
    )
