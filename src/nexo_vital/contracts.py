"""Fail-fast contracts for every analytical input."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .catalog import INDICATORS


class ContractError(ValueError):
    """Raised when a snapshot cannot support a trustworthy analysis."""


GLOBAL_COLUMNS = (
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
)


@dataclass(frozen=True, slots=True)
class Coverage:
    rows: int
    countries: int
    years: int
    indicators: int
    min_year: int
    max_year: int


def load_global_panel(path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    missing = sorted(set(GLOBAL_COLUMNS).difference(frame.columns))
    if missing:
        raise ContractError(f"Colunas obrigatórias ausentes: {missing}")
    frame = frame.loc[:, GLOBAL_COLUMNS].copy()
    frame["year"] = pd.to_numeric(frame["year"], errors="raise").astype("int16")
    frame["value"] = pd.to_numeric(frame["value"], errors="raise").astype(float)
    if frame[list(GLOBAL_COLUMNS)].isna().any().any():
        bad = frame.columns[frame.isna().any()].tolist()
        raise ContractError(f"Valores ausentes em campos canônicos: {bad}")
    if not frame["country_iso3"].str.fullmatch(r"[A-Z]{3}").all():
        raise ContractError("ISO3 inválido")
    unknown = sorted(set(frame["indicator_id"]).difference(INDICATORS))
    if unknown:
        raise ContractError(f"Indicadores fora do catálogo: {unknown}")
    duplicated = frame.duplicated(["country_iso3", "year", "indicator_id"], keep=False)
    if duplicated.any():
        sample = frame.loc[duplicated, ["country_iso3", "year", "indicator_id"]].head()
        raise ContractError(f"Chave país-ano-indicador duplicada:\n{sample}")
    if not np.isfinite(frame["value"]).all():
        raise ContractError("O painel contém valores não finitos")
    _validate_catalog_alignment(frame)
    return frame.sort_values(["country_iso3", "year", "indicator_id"], ignore_index=True)


def _validate_catalog_alignment(frame: pd.DataFrame) -> None:
    for indicator_id, group in frame.groupby("indicator_id", observed=True):
        spec = INDICATORS[indicator_id]
        for column, expected in (
            ("indicator_code", spec.code),
            ("unit", spec.unit),
            ("source", spec.source),
        ):
            actual = set(group[column])
            if actual != {expected}:
                raise ContractError(
                    f"{indicator_id}: {column}={sorted(actual)} diverge de {expected!r}"
                )


def coverage(frame: pd.DataFrame) -> Coverage:
    return Coverage(
        rows=len(frame),
        countries=frame["country_iso3"].nunique(),
        years=frame["year"].nunique(),
        indicators=frame["indicator_id"].nunique(),
        min_year=int(frame["year"].min()),
        max_year=int(frame["year"].max()),
    )


def analytical_cross_section(
    frame: pd.DataFrame, year: int, required: tuple[str, ...]
) -> pd.DataFrame:
    subset = frame.loc[frame["year"].eq(year)]
    wide = subset.pivot(index="country_iso3", columns="indicator_id", values="value")
    metadata = subset.groupby("country_iso3", observed=True)[
        ["country_name", "region", "income_group"]
    ].first()
    result = metadata.join(wide).dropna(subset=list(required)).reset_index()
    if result.empty:
        raise ContractError(f"Nenhuma observação completa para {year} e {required}")
    return result
