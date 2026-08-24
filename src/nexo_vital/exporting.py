"""Stable JSON and tabular export boundaries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def records(frame: pd.DataFrame, digits: int = 6) -> list[dict[str, Any]]:
    normalized = frame.copy()
    float_columns = normalized.select_dtypes(include=["floating"]).columns
    normalized[float_columns] = normalized[float_columns].round(digits)
    normalized = normalized.replace({np.nan: None, np.inf: None, -np.inf: None})
    return normalized.to_dict(orient="records")


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return None if not np.isfinite(value) else round(float(value), 6)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def write_json(path: str | Path, payload: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(json_safe(payload), ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def write_table(path: str | Path, frame: pd.DataFrame) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(target, index=False)
