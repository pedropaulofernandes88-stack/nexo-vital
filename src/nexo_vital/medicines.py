"""Medication volume/composition analyses that preserve comparability caveats."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from statsmodels.stats.multitest import multipletests


@dataclass(slots=True)
class MedicinesBundle:
    glass_latest: pd.DataFrame
    glass_summary: dict[str, float | int | list[str]]
    glass_associations: pd.DataFrame
    oecd_latest: pd.DataFrame
    oecd_change: pd.DataFrame
    oecd_summary: dict[str, float | int]
    cross_sector_associations: pd.DataFrame


def analyze_medicines(
    glass_path: str, oecd_path: str, global_panel: pd.DataFrame | None = None
) -> MedicinesBundle:
    glass = pd.read_csv(glass_path).sort_values(["country_iso3", "year"])
    latest = glass.groupby("country_iso3", observed=True).tail(1).copy()
    total_median = latest["total_ddd_per_1000_day"].median()
    access_median = latest["access_share_pct"].median()
    latest["volume_band"] = np.where(
        latest["total_ddd_per_1000_day"].ge(total_median), "high", "low"
    )
    latest["access_target"] = np.where(latest["access_share_pct"].ge(70), "meets_70", "below_70")
    latest["paradox_quadrant"] = (
        latest["volume_band"]
        + "_volume__"
        + np.where(latest["access_share_pct"].ge(access_median), "higher_access", "lower_access")
    )
    latest["has_coverage_caveat"] = latest["coverage_caveat"].fillna("").str.strip().ne("")
    valid = latest[["total_ddd_per_1000_day", "access_share_pct"]].dropna()
    rho, p_value = spearmanr(valid.iloc[:, 0], valid.iloc[:, 1])
    associations = pd.DataFrame(
        [
            {
                "comparison": "total_vs_access_share",
                "n": len(valid),
                "spearman_rho": rho,
                "p_value": p_value,
            }
        ]
    )
    summary: dict[str, float | int | list[str]] = {
        "observations": len(glass),
        "countries": latest["country_iso3"].nunique(),
        "latest_year_min": int(latest["year"].min()),
        "latest_year_max": int(latest["year"].max()),
        "total_median": float(total_median),
        "total_min": float(latest["total_ddd_per_1000_day"].min()),
        "total_max": float(latest["total_ddd_per_1000_day"].max()),
        "max_min_ratio": float(
            latest["total_ddd_per_1000_day"].max() / latest["total_ddd_per_1000_day"].min()
        ),
        "countries_meeting_access_70": int(latest["access_share_pct"].ge(70).sum()),
        "countries_with_coverage_caveat": int(latest["has_coverage_caveat"].sum()),
        "explicit_absence_examples": ["Brazil", "China", "India", "United States"],
    }

    oecd = pd.read_csv(oecd_path).sort_values(["class_id", "country_iso3", "year"])
    oecd_latest = oecd.groupby(["class_id", "country_iso3"], observed=True).tail(1).copy()
    baseline = oecd.loc[
        oecd["year"].eq(2011), ["country_iso3", "class_id", "ddd_per_1000_day"]
    ].rename(columns={"ddd_per_1000_day": "ddd_2011"})
    endpoint = oecd.loc[
        oecd["year"].eq(2021), ["country_iso3", "class_id", "ddd_per_1000_day"]
    ].rename(columns={"ddd_per_1000_day": "ddd_2021"})
    change = baseline.merge(endpoint, on=["country_iso3", "class_id"], how="inner")
    change["absolute_change"] = change["ddd_2021"] - change["ddd_2011"]
    change["percent_change"] = 100 * change["absolute_change"] / change["ddd_2011"]
    summary_change = (
        change.groupby("class_id", observed=True)["percent_change"]
        .agg(["count", "mean", "median"])
        .reset_index()
    )
    oecd_summary = {
        "observations": len(oecd),
        "countries": oecd["country_iso3"].nunique(),
        "classes": oecd["class_id"].nunique(),
        "common_country_class_pairs_2011_2021": len(change),
    }
    change = change.merge(summary_change, on="class_id", suffixes=("", "_class"))
    cross_sector = (
        _cross_sector_associations(latest, global_panel)
        if global_panel is not None
        else pd.DataFrame()
    )
    return MedicinesBundle(
        latest,
        summary,
        associations,
        oecd_latest,
        change,
        oecd_summary,
        cross_sector,
    )


def _cross_sector_associations(latest: pd.DataFrame, panel: pd.DataFrame) -> pd.DataFrame:
    indicators = (
        "life_expectancy",
        "under5_mortality",
        "gdp_per_capita_ppp",
        "health_spending_ppp",
    )
    joined = latest[["country_iso3", "year", "total_ddd_per_1000_day", "access_share_pct"]].copy()
    for indicator_id in indicators:
        source = panel.loc[
            panel["indicator_id"].eq(indicator_id),
            ["country_iso3", "year", "value"],
        ]
        values: list[float] = []
        years: list[float] = []
        for row in joined.itertuples(index=False):
            candidates = source.loc[source["country_iso3"].eq(row.country_iso3)].copy()
            if candidates.empty:
                values.append(np.nan)
                years.append(np.nan)
                continue
            candidates["distance"] = (candidates["year"] - row.year).abs()
            nearest = candidates.sort_values(["distance", "year"], ascending=[True, False]).iloc[0]
            if nearest["distance"] > 3:
                values.append(np.nan)
                years.append(np.nan)
            else:
                values.append(float(nearest["value"]))
                years.append(float(nearest["year"]))
        joined[indicator_id] = values
        joined[f"{indicator_id}_year"] = years

    rows: list[dict[str, float | int | str]] = []
    for exposure in ("total_ddd_per_1000_day", "access_share_pct"):
        for outcome in indicators:
            valid = joined[[exposure, outcome]].dropna()
            rho, p_value = spearmanr(valid[exposure], valid[outcome])
            rows.append(
                {
                    "exposure": exposure,
                    "outcome": outcome,
                    "n": len(valid),
                    "spearman_rho": float(rho),
                    "p_value_raw": float(p_value),
                }
            )
    result = pd.DataFrame(rows)
    reject, adjusted, _, _ = multipletests(result["p_value_raw"], alpha=0.05, method="fdr_bh")
    result["p_value_fdr_bh"] = adjusted
    result["reject_fdr_05"] = reject
    return result.sort_values("p_value_fdr_bh")
