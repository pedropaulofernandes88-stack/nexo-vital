"""PCA, competing cluster criteria and bootstrap stability."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import (
    adjusted_rand_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
from sklearn.preprocessing import StandardScaler

from .features import design_matrix


@dataclass(slots=True)
class SegmentationBundle:
    countries: pd.DataFrame
    pca_variance: pd.DataFrame
    pca_loadings: pd.DataFrame
    cluster_selection: pd.DataFrame
    cluster_profiles_k2: pd.DataFrame
    cluster_profiles_k4: pd.DataFrame
    bootstrap_stability: pd.DataFrame


def segment_countries(
    cross_section: pd.DataFrame,
    features: tuple[str, ...],
    random_state: int = 20260824,
    bootstrap_iterations: int = 250,
) -> SegmentationBundle:
    raw = design_matrix(cross_section, features)
    scaled = StandardScaler().fit_transform(raw)
    pca = PCA().fit(scaled)
    scores = pca.transform(scaled)
    pca_variance = pd.DataFrame(
        {
            "component": [f"PC{i}" for i in range(1, len(features) + 1)],
            "explained_variance_ratio": pca.explained_variance_ratio_,
            "cumulative_variance_ratio": np.cumsum(pca.explained_variance_ratio_),
        }
    )
    pca_loadings = pd.DataFrame(
        pca.components_.T,
        index=features,
        columns=[f"PC{i}" for i in range(1, len(features) + 1)],
    ).reset_index(names="feature")

    selection_rows: list[dict[str, float | int]] = []
    labels: dict[int, np.ndarray] = {}
    for k in range(2, 9):
        model = KMeans(n_clusters=k, n_init=50, random_state=random_state).fit(scaled)
        labels[k] = model.labels_
        selection_rows.append(
            {
                "k": k,
                "silhouette": float(silhouette_score(scaled, model.labels_)),
                "davies_bouldin": float(davies_bouldin_score(scaled, model.labels_)),
                "calinski_harabasz": float(calinski_harabasz_score(scaled, model.labels_)),
                "inertia": float(model.inertia_),
            }
        )

    countries = cross_section.copy()
    countries["pc1"] = scores[:, 0]
    countries["pc2"] = scores[:, 1]
    countries["cluster_k2"] = _ordered_labels(labels[2], countries, 2)
    countries["cluster_k4"] = _ordered_labels(labels[4], countries, 4)

    profiles_k2 = _profiles(countries, features, "cluster_k2")
    profiles_k4 = _profiles(countries, features, "cluster_k4")
    stability = pd.concat(
        [
            _bootstrap_ari(scaled, labels[k], k, bootstrap_iterations, random_state + k)
            for k in (2, 4)
        ],
        ignore_index=True,
    )
    return SegmentationBundle(
        countries=countries,
        pca_variance=pca_variance,
        pca_loadings=pca_loadings,
        cluster_selection=pd.DataFrame(selection_rows),
        cluster_profiles_k2=profiles_k2,
        cluster_profiles_k4=profiles_k4,
        bootstrap_stability=stability,
    )


def _ordered_labels(labels: np.ndarray, frame: pd.DataFrame, k: int) -> np.ndarray:
    means = (
        pd.DataFrame({"label": labels, "life": frame["life_expectancy"]})
        .groupby("label")["life"]
        .mean()
    )
    order = {label: rank + 1 for rank, label in enumerate(means.sort_values(ascending=False).index)}
    return np.array([order[label] for label in labels], dtype=int)


def _profiles(frame: pd.DataFrame, features: tuple[str, ...], cluster: str) -> pd.DataFrame:
    aggregations = {feature: (feature, "mean") for feature in features}
    result = frame.groupby(cluster, observed=True).agg(n=("country_iso3", "size"), **aggregations)
    return result.reset_index()


def _bootstrap_ari(
    scaled: np.ndarray,
    reference_labels: np.ndarray,
    k: int,
    iterations: int,
    random_state: int,
) -> pd.DataFrame:
    generator = np.random.default_rng(random_state)
    rows: list[dict[str, float | int]] = []
    for iteration in range(1, iterations + 1):
        sample = generator.integers(0, len(scaled), size=len(scaled))
        model = KMeans(n_clusters=k, n_init=10, random_state=random_state + iteration).fit(
            scaled[sample]
        )
        score = adjusted_rand_score(reference_labels, model.predict(scaled))
        rows.append({"k": k, "iteration": iteration, "adjusted_rand_index": float(score)})
    result = pd.DataFrame(rows)
    result["mean_ari"] = result["adjusted_rand_index"].mean()
    result["median_ari"] = result["adjusted_rand_index"].median()
    result["p05_ari"] = result["adjusted_rand_index"].quantile(0.05)
    return result
