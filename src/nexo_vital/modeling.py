"""Association model, robust inference and strictly out-of-sample diagnostics."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import hypergeom
from sklearn.base import clone
from sklearn.linear_model import LinearRegression, RidgeCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import LeaveOneOut, RepeatedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from statsmodels.stats.outliers_influence import variance_inflation_factor

from .features import design_matrix


@dataclass(slots=True)
class ModelBundle:
    countries: pd.DataFrame
    coefficients: pd.DataFrame
    vif: pd.DataFrame
    influence: pd.DataFrame
    metrics: dict[str, float | int]
    repeated_cv: pd.DataFrame
    regional_performance: pd.DataFrame
    concentration_test: dict[str, float | int | str]
    sensitivity: pd.DataFrame
    ridge_benchmark: dict[str, float]


def _estimator():
    return make_pipeline(StandardScaler(), LinearRegression())


def _quantile_higher(values: np.ndarray, probability: float) -> float:
    try:
        return float(np.quantile(values, probability, method="higher"))
    except TypeError:  # numpy < 1.22
        return float(np.quantile(values, probability, interpolation="higher"))


def fit_association_model(
    cross_section: pd.DataFrame,
    features: tuple[str, ...],
    alpha: float = 0.20,
    random_state: int = 20260824,
) -> ModelBundle:
    x_raw = design_matrix(cross_section, features)
    y = cross_section["life_expectancy"].astype(float).to_numpy()
    n = len(cross_section)

    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(x_raw)
    x_sm = sm.add_constant(x_scaled, has_constant="add")
    robust = sm.OLS(y, x_sm).fit(cov_type="HC3")
    names = ["intercept", *features]
    confidence = robust.conf_int(alpha=0.05)
    coefficients = pd.DataFrame(
        {
            "term": names,
            "estimate": robust.params,
            "std_error_hc3": robust.bse,
            "statistic": robust.tvalues,
            "p_value": robust.pvalues,
            "ci95_low": confidence[:, 0],
            "ci95_high": confidence[:, 1],
        }
    )

    vif = pd.DataFrame(
        {
            "feature": features,
            "vif": [variance_inflation_factor(x_scaled, index) for index in range(len(features))],
        }
    )

    influence_raw = robust.get_influence()
    cooks = influence_raw.cooks_distance[0]
    leverage = influence_raw.hat_matrix_diag

    loo = LeaveOneOut()
    loo_prediction = cross_val_predict(_estimator(), x_raw, y, cv=loo, n_jobs=None)
    residual = y - loo_prediction
    absolute_residual = np.abs(residual)
    conformal_level = min(1.0, np.ceil((n + 1) * (1 - alpha)) / n)
    radius = _quantile_higher(absolute_residual, conformal_level)
    position = np.where(residual < -radius, "below", np.where(residual > radius, "above", "within"))

    countries = cross_section.copy()
    countries["predicted_life_expectancy_loo"] = loo_prediction
    countries["residual_loo"] = residual
    countries["absolute_residual_loo"] = absolute_residual
    countries["prediction_band_low"] = loo_prediction - radius
    countries["prediction_band_high"] = loo_prediction + radius
    countries["position"] = position
    countries["cooks_distance"] = cooks
    countries["leverage"] = leverage

    influence = countries[
        ["country_iso3", "country_name", "cooks_distance", "leverage", "residual_loo"]
    ].sort_values("cooks_distance", ascending=False)

    repeated_cv = _repeated_cv(x_raw, y, random_state)
    regional = _regional_metrics(countries)
    concentration = _regional_concentration(countries)
    sensitivity = _sensitivity(cross_section, features, radius)
    ridge_benchmark = _nested_ridge_loo(x_raw, y)

    rmse = float(mean_squared_error(y, loo_prediction) ** 0.5)
    metrics: dict[str, float | int] = {
        "n_countries": n,
        "n_features": len(features),
        "r_squared_association": float(robust.rsquared),
        "adjusted_r_squared_association": float(robust.rsquared_adj),
        "loo_predictive_r_squared": float(r2_score(y, loo_prediction)),
        "loo_rmse_years": rmse,
        "loo_mae_years": float(mean_absolute_error(y, loo_prediction)),
        "conformal_nominal_coverage": 1 - alpha,
        "conformal_empirical_coverage": float(np.mean(absolute_residual <= radius)),
        "conformal_radius_years": radius,
        "countries_below": int(np.sum(position == "below")),
        "countries_within": int(np.sum(position == "within")),
        "countries_above": int(np.sum(position == "above")),
        "max_vif": float(vif["vif"].max()),
        "influential_cook_threshold": int(np.sum(cooks > 4 / n)),
    }
    return ModelBundle(
        countries=countries,
        coefficients=coefficients,
        vif=vif,
        influence=influence,
        metrics=metrics,
        repeated_cv=repeated_cv,
        regional_performance=regional,
        concentration_test=concentration,
        sensitivity=sensitivity,
        ridge_benchmark=ridge_benchmark,
    )


def _nested_ridge_loo(x: pd.DataFrame, y: np.ndarray) -> dict[str, float]:
    """Tune the penalty inside every outer LOO training set to avoid optimistic leakage."""
    alphas = np.logspace(-3, 3, 49)
    predictions = np.empty(len(y), dtype=float)
    selected: list[float] = []
    for train, test in LeaveOneOut().split(x):
        estimator = make_pipeline(
            StandardScaler(),
            RidgeCV(alphas=alphas, cv=5, scoring="neg_mean_squared_error"),
        )
        estimator.fit(x.iloc[train], y[train])
        predictions[test] = estimator.predict(x.iloc[test])
        selected.append(float(estimator.named_steps["ridgecv"].alpha_))
    return {
        "loo_predictive_r_squared": float(r2_score(y, predictions)),
        "loo_rmse_years": float(mean_squared_error(y, predictions) ** 0.5),
        "loo_mae_years": float(mean_absolute_error(y, predictions)),
        "selected_alpha_median": float(np.median(selected)),
        "selected_alpha_min": float(np.min(selected)),
        "selected_alpha_max": float(np.max(selected)),
    }


def _repeated_cv(x: pd.DataFrame, y: np.ndarray, random_state: int) -> pd.DataFrame:
    splitter = RepeatedKFold(n_splits=10, n_repeats=20, random_state=random_state)
    rows: list[dict[str, float | int]] = []
    for fold, (train, test) in enumerate(splitter.split(x), start=1):
        model = clone(_estimator()).fit(x.iloc[train], y[train])
        predicted = model.predict(x.iloc[test])
        rows.append(
            {
                "fold": fold,
                "repeat": (fold - 1) // 10 + 1,
                "rmse_years": float(mean_squared_error(y[test], predicted) ** 0.5),
                "mae_years": float(mean_absolute_error(y[test], predicted)),
                "bias_years": float(np.mean(y[test] - predicted)),
            }
        )
    return pd.DataFrame(rows)


def _regional_metrics(countries: pd.DataFrame) -> pd.DataFrame:
    def summarize(group: pd.DataFrame) -> pd.Series:
        return pd.Series(
            {
                "n": len(group),
                "bias_years": group["residual_loo"].mean(),
                "mae_years": group["absolute_residual_loo"].mean(),
                "rmse_years": np.sqrt(np.mean(np.square(group["residual_loo"]))),
                "below_share": group["position"].eq("below").mean(),
            }
        )

    return (
        countries.groupby("region", observed=True)
        .apply(summarize, include_groups=False)
        .reset_index()
        .sort_values("bias_years")
    )


def _regional_concentration(countries: pd.DataFrame) -> dict[str, float | int | str]:
    target = "Sub-Saharan Africa"
    universe = len(countries)
    region_total = int(countries["region"].eq(target).sum())
    selected = countries.loc[countries["position"].eq("below")]
    draws = len(selected)
    observed = int(selected["region"].eq(target).sum())
    p_value = float(hypergeom.sf(observed - 1, universe, region_total, draws)) if draws else 1.0
    return {
        "region": target,
        "universe_countries": universe,
        "region_countries": region_total,
        "below_countries": draws,
        "observed_in_region": observed,
        "expected_in_region": float(draws * region_total / universe),
        "enrichment_ratio": float(observed / (draws * region_total / universe))
        if draws and region_total
        else 0.0,
        "hypergeometric_one_sided_p_value": p_value,
    }


def _sensitivity(
    cross_section: pd.DataFrame, features: tuple[str, ...], reference_radius: float
) -> pd.DataFrame:
    candidates = {
        "main": features,
        "with_under5": ("under5_mortality", *features),
        "without_tobacco": tuple(f for f in features if f != "tobacco_prevalence"),
        "resources_only": ("gdp_per_capita_ppp", "health_spending_ppp"),
    }
    y = cross_section["life_expectancy"].to_numpy()
    rows: list[pd.DataFrame] = []
    for specification, spec_features in candidates.items():
        x = design_matrix(cross_section, spec_features)
        prediction = cross_val_predict(_estimator(), x, y, cv=LeaveOneOut())
        residual = y - prediction
        rows.append(
            pd.DataFrame(
                {
                    "country_iso3": cross_section["country_iso3"],
                    "specification": specification,
                    "residual": residual,
                    "position": np.where(
                        residual < -reference_radius,
                        "below",
                        np.where(residual > reference_radius, "above", "within"),
                    ),
                    "predictive_r_squared": r2_score(y, prediction),
                    "rmse_years": mean_squared_error(y, prediction) ** 0.5,
                }
            )
        )
    combined = pd.concat(rows, ignore_index=True)
    stability = (
        combined.assign(is_main=lambda d: d["specification"].eq("main"))
        .pivot(index="country_iso3", columns="specification", values="position")
        .reset_index()
    )
    stability["stable_all_specs"] = stability[[*candidates]].nunique(axis=1).eq(1)
    return combined.merge(stability[["country_iso3", "stable_all_specs"]], on="country_iso3")
