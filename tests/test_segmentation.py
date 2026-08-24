import numpy as np
import pandas as pd

from nexo_vital.catalog import CLUSTER_FEATURES
from nexo_vital.segmentation import segment_countries


def test_segmentation_exports_competing_criteria_and_stability():
    rng = np.random.default_rng(42)
    n = 48
    frame = pd.DataFrame(
        {
            "country_iso3": [f"X{i:02d}" for i in range(n)],
            "life_expectancy": np.r_[rng.normal(62, 2, n // 2), rng.normal(79, 2, n // 2)],
            "under5_mortality": np.r_[rng.lognormal(4, 0.2, n // 2), rng.lognormal(2, 0.2, n // 2)],
            "obesity_prevalence": rng.uniform(8, 35, n),
            "gdp_per_capita_ppp": np.r_[
                rng.lognormal(8.5, 0.2, n // 2), rng.lognormal(10.5, 0.2, n // 2)
            ],
            "health_spending_ppp": np.r_[
                rng.lognormal(5, 0.2, n // 2), rng.lognormal(8, 0.2, n // 2)
            ],
            "tobacco_prevalence": rng.uniform(5, 35, n),
        }
    )
    result = segment_countries(frame, CLUSTER_FEATURES, bootstrap_iterations=5)
    assert result.cluster_selection["k"].tolist() == list(range(2, 9))
    assert len(result.bootstrap_stability) == 10
    assert set(result.countries["cluster_k2"]) == {1, 2}
