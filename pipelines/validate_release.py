"""Release gate: data, statistical artifacts, static assets and independence checks."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nexo_vital.contracts import coverage, load_global_panel  # noqa: E402


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    checks: list[str] = []
    snapshot = ROOT / "data" / "snapshots" / "global_indicators_2000_2022.csv"
    panel = load_global_panel(snapshot)
    c = coverage(panel)
    require(c.rows == 33_043, f"cardinalidade global inesperada: {c.rows}")
    require(c.indicators == 9 and c.min_year == 2000 and c.max_year == 2022, "cobertura global")
    checks.append("contrato global: 33.043 linhas, 9 indicadores, sem chave duplicada")

    json_path = ROOT / "dashboard" / "data" / "observatory.json"
    raw = json_path.read_text(encoding="utf-8")
    require("NaN" not in raw and "Infinity" not in raw, "JSON não finito")
    data = json.loads(raw)
    metrics = data["model"]["metrics"]
    require(data["meta"]["causal_claim"] is False, "metadado causal")
    require(data["coverage"]["analytical_countries"] == 159, "recorte analítico")
    require(metrics["conformal_empirical_coverage"] >= 0.8, "cobertura conformal")
    require("ridge_nested_loo_benchmark" in data["model"], "benchmark Ridge ausente")
    checks.append("artefato analítico: JSON finito, 159 países, banda e Ridge presentes")

    table_expectations = {
        "country_results.csv": 159,
        "repeated_cross_validation.csv": 200,
        "cluster_bootstrap_stability.csv": 500,
    }
    for filename, expected in table_expectations.items():
        count = len(pd.read_csv(ROOT / "artifacts" / "tables" / filename))
        require(count == expected, f"{filename}: {count} != {expected}")
    checks.append("cardinalidade acadêmica: países=159, CV=200, bootstrap=500")

    html = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
    ids = re.findall(r'\bid="([^"]+)"', html)
    require(len(ids) == len(set(ids)), "IDs HTML duplicados")
    require("http://" not in html and "https://" not in html, "dependência remota no HTML")
    for asset in re.findall(r'(?:src|href)="([^"]+)"', html):
        if asset.startswith("#"):
            continue
        require((ROOT / "dashboard" / asset).exists(), f"asset ausente: {asset}")
    checks.append("dashboard: IDs únicos e assets locais resolvidos")

    source_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in ROOT.rglob("*")
        if path.is_file()
        and path.suffix.lower() in {".py", ".js", ".html", ".css", ".md"}
        and "vendor" not in path.parts
    ).lower()
    forbidden = (
        "thai" + "iceu",
        "health inequality" + " explorer",
        "global health outcomes" + " atlas",
    )
    require(
        not any(term in source_text for term in forbidden),
        "marca ou atribuição de projeto anterior",
    )
    checks.append("independência: sem marcas ou atribuições de projetos anteriores")

    result = subprocess.run(
        ["node", "--check", str(ROOT / "dashboard" / "scripts" / "app.js")],
        capture_output=True,
        text=True,
        check=False,
    )
    require(result.returncode == 0, result.stderr)
    checks.append("JavaScript: node --check aprovado")

    manifest = json.loads(
        (ROOT / "data" / "snapshots" / "manifest.json").read_text(encoding="utf-8")
    )
    listed = {item["path"]: item for item in manifest["files"]}
    for relative in (
        "data/snapshots/global_indicators_2000_2022.csv",
        "data/snapshots/who_glass_antibiotics_2016_2023.csv",
        "data/snapshots/oecd_pharmaceutical_consumption_2010_2023.csv",
    ):
        path = ROOT / relative
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        require(listed[relative]["sha256"] == digest, f"hash divergente: {relative}")
    checks.append("proveniência: hashes dos três snapshots analíticos conferidos")

    report = {"status": "approved", "checks": checks}
    target = ROOT / "artifacts" / "validation_report.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
