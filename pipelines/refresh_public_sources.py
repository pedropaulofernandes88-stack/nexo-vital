"""Refresh public snapshots without depending on any predecessor repository.

This pipeline mutates snapshots deliberately. Run it only when opening a new data
release, inspect schema changes, then rebuild and validate every derived artifact.
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nexo_vital.acquisition import (  # noqa: E402
    who_gho_indicator,
    world_bank_countries,
    world_bank_indicator,
)
from nexo_vital.catalog import INDICATORS  # noqa: E402
from nexo_vital.contracts import load_global_panel  # noqa: E402

SNAPSHOTS = ROOT / "data" / "snapshots"
OWID_TOTAL = "https://ourworldindata.org/grapher/antibiotic-consumption-rate.csv?v=1&csvType=full&useColumnShortNames=false"
OWID_AWARE = (
    "https://ourworldindata.org/grapher/antibiotic-usage-by-surveillance-category-stacked.csv"
)
OECD_API = "https://sdmx.oecd.org/public/rest/data/OECD.ELS.HD,HEALTH_PHMC@DF_PHMC_CONSUM,1.0/....C02+C03+C07+C08+C09+A10+C10+N06A?startPeriod=2010&dimensionAtObservation=AllDimensions"


def download_csv(url: str, accept: str = "text/csv") -> pd.DataFrame:
    request = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": "NexoVital/0.1"})
    with urllib.request.urlopen(request, timeout=180) as response:
        return pd.read_csv(io.BytesIO(response.read()))


def refresh_global() -> Path:
    countries = world_bank_countries()
    frames: list[pd.DataFrame] = []
    who_dimensions = {
        "life_expectancy": {"Dim1": "SEX_BTSX"},
        "physicians_density": {},
        "obesity_prevalence": {"Dim1": "SEX_BTSX", "Dim2": "AGEGROUP_YEARS18-PLUS"},
    }
    for indicator_id, spec in INDICATORS.items():
        if indicator_id in who_dimensions:
            values = who_gho_indicator(spec.code, dimensions=who_dimensions[indicator_id])
        else:
            values = world_bank_indicator(spec.code)
        values = values.drop(columns=["country_name"], errors="ignore").merge(
            countries, on="country_iso3", how="inner", validate="many_to_one"
        )
        values["indicator_id"] = indicator_id
        values["indicator_code"] = spec.code
        values["source"] = spec.source
        values["unit"] = spec.unit
        frames.append(values)
    result = pd.concat(frames, ignore_index=True)[
        [
            "country_iso3",
            "country_name",
            "region",
            "income_group",
            "year",
            "indicator_id",
            "indicator_code",
            "source",
            "unit",
            "value",
        ]
    ]
    target = SNAPSHOTS / "global_indicators_2000_2022.csv"
    result.sort_values(["country_iso3", "year", "indicator_id"]).to_csv(target, index=False)
    load_global_panel(target)
    return target


def _coverage_caveat(iso3: str) -> str:
    community = {"AUT", "DEU", "ISL"}
    public = {"HND", "KWT", "OMN", "PNG", "RWA", "SAU", "ZAF", "TLS", "GBR"}
    partial = {
        "BTN",
        "BFA",
        "CIV",
        "ETH",
        "FRA",
        "GAB",
        "GEO",
        "LAO",
        "MYS",
        "MLI",
        "CHE",
        "TUN",
        "PSE",
    }
    incomplete = {"NPL", "KEN", "QAT"}
    if iso3 in community:
        return "Somente uso na comunidade"
    if iso3 in public:
        return "Somente setor público"
    if iso3 in partial:
        return "Classes antibióticas parcialmente cobertas"
    if iso3 in incomplete:
        return "Fontes incompletas"
    if iso3 == "PRT":
        return "Medicamentos antituberculose incompletos"
    return ""


def refresh_glass() -> Path:
    total = download_csv(OWID_TOTAL).rename(
        columns={"Entity": "country_name", "Code": "country_iso3", "Year": "year"}
    )
    total_column = next(
        column for column in total if column not in {"country_name", "country_iso3", "year"}
    )
    total = total.rename(columns={total_column: "total_ddd_per_1000_day"})
    aware = download_csv(OWID_AWARE).rename(
        columns={
            "Entity": "country_name",
            "Code": "country_iso3",
            "Year": "year",
            "Access antibiotics": "access_ddd",
            "Watch antibiotics": "watch_ddd",
            "Reserve antibiotics": "reserve_ddd",
            "Antibiotics not classified or recommended": "unclassified_ddd",
        }
    )
    aware = aware.drop(columns=["country_name"], errors="ignore")
    result = total.merge(aware, on=["country_iso3", "year"], how="left", validate="one_to_one")
    aware_total = result[["access_ddd", "watch_ddd", "reserve_ddd", "unclassified_ddd"]].sum(
        axis=1, min_count=1
    )
    result["access_share_pct"] = 100 * result["access_ddd"] / aware_total
    result["coverage_caveat"] = result["country_iso3"].map(_coverage_caveat)
    result["interpretive_quadrant"] = ""
    target = SNAPSHOTS / "who_glass_antibiotics_2016_2023.csv"
    result.to_csv(target, index=False)
    return target


def refresh_oecd() -> Path:
    raw = download_csv(OECD_API)
    raw = raw.loc[raw["UNIT_MEASURE"].eq("DDD_10P3HB")].copy()
    raw["TIME_PERIOD"] = pd.to_numeric(raw["TIME_PERIOD"], errors="coerce")
    raw["OBS_VALUE"] = pd.to_numeric(raw["OBS_VALUE"], errors="coerce")
    raw = raw.dropna(subset=["TIME_PERIOD", "OBS_VALUE"])
    direct = {
        "A10": ("antidiabetics", "Antidiabéticos"),
        "C10": ("lipid_modifying", "Modificadores de lipídios"),
        "N06A": ("antidepressants", "Antidepressivos"),
    }
    rows: list[pd.DataFrame] = []
    for atc, (class_id, class_name) in direct.items():
        part = raw.loc[raw["PHARMACEUTICAL"].eq(atc)].copy()
        part["class_id"] = class_id
        part["class_name"] = class_name
        part["atc"] = atc
        rows.append(part)
    anti_codes = {"C02", "C03", "C07", "C08", "C09"}
    anti = (
        raw.loc[raw["PHARMACEUTICAL"].isin(anti_codes)]
        .groupby(["REF_AREA", "TIME_PERIOD"], observed=True)
        .agg(
            OBS_VALUE=("OBS_VALUE", "sum"),
            OBS_STATUS=("OBS_STATUS", lambda v: next((x for x in v if pd.notna(x)), "")),
        )
        .reset_index()
    )
    anti["class_id"] = "antihypertensives"
    anti["class_name"] = "Anti-hipertensivos (composição OECD)"
    anti["atc"] = "+".join(sorted(anti_codes))
    rows.append(anti)
    combined = pd.concat(rows, ignore_index=True)
    countries = world_bank_countries()[["country_iso3", "country_name"]]
    combined = combined.rename(
        columns={
            "REF_AREA": "country_iso3",
            "TIME_PERIOD": "year",
            "OBS_VALUE": "ddd_per_1000_day",
            "OBS_STATUS": "oecd_status",
        }
    ).merge(countries, on="country_iso3", how="left")
    combined["country_name"] = combined["country_name"].fillna(combined["country_iso3"])
    target = SNAPSHOTS / "oecd_pharmaceutical_consumption_2010_2023.csv"
    combined[
        [
            "country_name",
            "country_iso3",
            "year",
            "class_id",
            "class_name",
            "atc",
            "ddd_per_1000_day",
            "oecd_status",
        ]
    ].sort_values(["country_iso3", "year", "class_id"]).to_csv(target, index=False)
    return target


def sha256(path: Path) -> str:
    content = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    digest = hashlib.sha256(content).hexdigest()
    return digest


def main() -> None:
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    refreshed = [refresh_global(), refresh_glass(), refresh_oecd()]
    audit = {
        "refreshed_at": datetime.now(UTC).isoformat(),
        "files": [
            {"path": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in refreshed
        ],
    }
    (SNAPSHOTS / "refresh_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
