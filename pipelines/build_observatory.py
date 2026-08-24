"""Build all analytical and presentation artifacts from immutable snapshots."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nexo_vital.catalog import CLUSTER_FEATURES, CORE_FEATURES  # noqa: E402
from nexo_vital.contracts import analytical_cross_section, coverage, load_global_panel  # noqa: E402
from nexo_vital.discovery import residual_discovery  # noqa: E402
from nexo_vital.exporting import records, write_json, write_table  # noqa: E402
from nexo_vital.medicines import analyze_medicines  # noqa: E402
from nexo_vital.modeling import fit_association_model  # noqa: E402
from nexo_vital.segmentation import segment_countries  # noqa: E402

REFERENCE_YEAR = 2015
REQUIRED = ("life_expectancy", "under5_mortality", *CORE_FEATURES)


def main() -> None:
    snapshot = ROOT / "data" / "snapshots" / "global_indicators_2000_2022.csv"
    panel = load_global_panel(snapshot)
    section = analytical_cross_section(panel, REFERENCE_YEAR, REQUIRED)
    model = fit_association_model(section, CORE_FEATURES)
    segmentation = segment_countries(section, CLUSTER_FEATURES)
    discovery = residual_discovery(model.countries, panel, REFERENCE_YEAR)
    medicines = analyze_medicines(
        ROOT / "data" / "snapshots" / "who_glass_antibiotics_2016_2023.csv",
        ROOT / "data" / "snapshots" / "oecd_pharmaceutical_consumption_2010_2023.csv",
        panel,
    )

    countries = model.countries.merge(
        segmentation.countries[["country_iso3", "pc1", "pc2", "cluster_k2", "cluster_k4"]],
        on="country_iso3",
        how="inner",
        validate="one_to_one",
    )
    stable = (
        model.sensitivity.groupby("country_iso3", observed=True)["stable_all_specs"]
        .first()
        .reset_index()
    )
    countries = countries.merge(stable, on="country_iso3", validate="one_to_one")

    temporal = panel.loc[
        panel["indicator_id"].isin(
            ["life_expectancy", "under5_mortality", "gdp_per_capita_ppp", "health_spending_ppp"]
        ),
        ["country_iso3", "year", "indicator_id", "value"],
    ]
    indicator_coverage = (
        panel.groupby("indicator_id", observed=True)
        .agg(
            observations=("value", "size"),
            countries=("country_iso3", "nunique"),
            years=("year", "nunique"),
            first_year=("year", "min"),
            last_year=("year", "max"),
        )
        .reset_index()
    )
    tourism = pd.read_csv(ROOT / "data" / "snapshots" / "brazil_health_tourism_2014_2019.csv")
    sus = pd.read_csv(ROOT / "data" / "snapshots" / "brazil_sus_foreign_nationality_2021.csv")

    cv_summary = {
        metric: {
            "mean": float(model.repeated_cv[metric].mean()),
            "p05": float(model.repeated_cv[metric].quantile(0.05)),
            "p95": float(model.repeated_cv[metric].quantile(0.95)),
        }
        for metric in ("rmse_years", "mae_years", "bias_years")
    }
    stability_summary = (
        segmentation.bootstrap_stability.groupby("k", observed=True)["adjusted_rand_index"]
        .agg(
            mean="mean",
            median="median",
            p05=lambda values: values.quantile(0.05),
            p95=lambda values: values.quantile(0.95),
        )
        .reset_index()
    )
    sensitivity_summary = (
        model.sensitivity.groupby("specification", observed=True)
        .agg(
            predictive_r_squared=("predictive_r_squared", "first"),
            rmse_years=("rmse_years", "first"),
            stable_countries=("stable_all_specs", "sum"),
        )
        .reset_index()
    )

    payload = {
        "meta": {
            "product": "Nexo Vital",
            "subtitle": "Atlas Global de Saúde, Desenvolvimento e Medicamentos",
            "reference_year": REFERENCE_YEAR,
            "generated_from": "versioned public-data snapshots",
            "causal_claim": False,
        },
        "coverage": {
            **asdict(coverage(panel)),
            "analytical_countries": len(countries),
            "by_indicator": records(indicator_coverage),
        },
        "model": {
            "metrics": model.metrics,
            "coefficients": records(model.coefficients),
            "vif": records(model.vif),
            "regional_performance": records(model.regional_performance),
            "concentration": model.concentration_test,
            "repeated_cv_summary": cv_summary,
            "ridge_nested_loo_benchmark": model.ridge_benchmark,
            "sensitivity": records(sensitivity_summary),
            "influence_top": records(model.influence.head(15)),
            "countries": records(countries),
        },
        "segmentation": {
            "pca_variance": records(segmentation.pca_variance),
            "pca_loadings": records(segmentation.pca_loadings),
            "cluster_selection": records(segmentation.cluster_selection),
            "profiles_k2": records(segmentation.cluster_profiles_k2),
            "profiles_k4": records(segmentation.cluster_profiles_k4),
            "bootstrap_stability": records(stability_summary),
        },
        "discovery": records(discovery),
        "medicines": {
            "glass_summary": medicines.glass_summary,
            "glass_latest": records(medicines.glass_latest),
            "glass_associations": records(medicines.glass_associations),
            "oecd_summary": medicines.oecd_summary,
            "oecd_latest": records(medicines.oecd_latest),
            "oecd_change": records(medicines.oecd_change),
            "cross_sector_associations": records(medicines.cross_sector_associations),
        },
        "brazil": {
            "health_tourism": records(tourism),
            "foreign_nationality_sus": records(sus),
            "measurement_warning": (
                "As séries medem fenômenos distintos: intenção principal de viagem por saúde e "
                "eventos de internação SUS por nacionalidade. Não devem ser somadas."
            ),
        },
        "temporal": records(temporal),
    }
    write_json(ROOT / "dashboard" / "data" / "observatory.json", payload)

    tables = {
        "country_results.csv": countries,
        "hc3_coefficients.csv": model.coefficients,
        "vif.csv": model.vif,
        "influence.csv": model.influence,
        "repeated_cross_validation.csv": model.repeated_cv,
        "regional_performance.csv": model.regional_performance,
        "sensitivity.csv": model.sensitivity,
        "pca_variance.csv": segmentation.pca_variance,
        "pca_loadings.csv": segmentation.pca_loadings,
        "cluster_selection.csv": segmentation.cluster_selection,
        "cluster_bootstrap_stability.csv": segmentation.bootstrap_stability,
        "residual_discovery_fdr.csv": discovery,
        "glass_latest.csv": medicines.glass_latest,
        "oecd_change_2011_2021.csv": medicines.oecd_change,
        "medicines_cross_sector_fdr.csv": medicines.cross_sector_associations,
    }
    for name, table in tables.items():
        write_table(ROOT / "artifacts" / "tables" / name, table)
    write_table(ROOT / "data" / "derived" / "analytical_cross_section_2015.csv", section)
    (ROOT / "artifacts" / "build_summary.json").write_text(
        json.dumps(
            {
                "reference_year": REFERENCE_YEAR,
                "countries": len(countries),
                "model_metrics": model.metrics,
                "concentration": model.concentration_test,
                "cv_summary": cv_summary,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
