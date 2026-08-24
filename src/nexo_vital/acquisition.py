"""Small, auditable clients for the public APIs used by Nexo Vital."""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    attempts: int = 4
    base_delay_seconds: float = 1.0
    timeout_seconds: int = 90


def get_json(url: str, policy: RetryPolicy | None = None) -> Any:
    policy = policy or RetryPolicy()
    headers = {"User-Agent": "NexoVital/0.1 (reproducible research; public data)"}
    last_error: Exception | None = None
    for attempt in range(policy.attempts):
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=policy.timeout_seconds) as response:
                return json.load(response)
        except Exception as error:  # network boundary: re-raised with context below
            last_error = error
            if attempt + 1 < policy.attempts:
                time.sleep(policy.base_delay_seconds * (2**attempt))
    raise RuntimeError(f"Falha após {policy.attempts} tentativas: {url}") from last_error


def world_bank_indicator(code: str, start: int = 2000, end: int = 2022) -> pd.DataFrame:
    encoded = urllib.parse.quote(code, safe=".")
    url = (
        f"https://api.worldbank.org/v2/country/all/indicator/{encoded}"
        f"?format=json&date={start}:{end}&per_page=20000"
    )
    payload = get_json(url)
    if not isinstance(payload, list) or len(payload) < 2:
        raise RuntimeError(f"Resposta World Bank inesperada para {code}")
    records = payload[1] or []
    rows = [
        {
            "country_iso3": row["countryiso3code"],
            "country_name": row["country"]["value"],
            "year": int(row["date"]),
            "value": float(row["value"]),
        }
        for row in records
        if row.get("value") is not None and len(row.get("countryiso3code", "")) == 3
    ]
    return pd.DataFrame(rows)


def world_bank_countries() -> pd.DataFrame:
    payload = get_json("https://api.worldbank.org/v2/country?format=json&per_page=400")
    records = payload[1]
    return pd.DataFrame(
        [
            {
                "country_iso3": row["id"],
                "country_name": row["name"],
                "region": row["region"]["value"],
                "income_group": row["incomeLevel"]["value"],
            }
            for row in records
            if row["region"]["id"] != "NA"
        ]
    )


def who_gho_indicator(
    code: str,
    start: int = 2000,
    end: int = 2022,
    dimensions: dict[str, str] | None = None,
) -> pd.DataFrame:
    filters = [f"TimeDim ge {start}", f"TimeDim le {end}"]
    filters.extend(f"{name} eq '{value}'" for name, value in (dimensions or {}).items())
    query = urllib.parse.urlencode(
        {
            "$filter": " and ".join(filters),
            "$select": "SpatialDim,TimeDim,NumericValue",
        }
    )
    payload = get_json(f"https://ghoapi.azureedge.net/api/{code}?{query}")
    records = payload.get("value", [])
    frame = pd.DataFrame(
        [
            {
                "country_iso3": row["SpatialDim"],
                "year": int(row["TimeDim"]),
                "value": float(row["NumericValue"]),
            }
            for row in records
            if row.get("NumericValue") is not None and len(row.get("SpatialDim", "")) == 3
        ]
    )
    if frame.duplicated(["country_iso3", "year"]).any():
        raise RuntimeError(f"WHO {code}: dimensões insuficientes; país-ano duplicado")
    return frame
