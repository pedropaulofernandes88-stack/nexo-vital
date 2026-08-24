import numpy as np
import pandas as pd
import pytest

from nexo_vital.features import design_matrix


def test_declared_positive_features_are_logged():
    frame = pd.DataFrame({"gdp_per_capita_ppp": [1.0, np.e], "tobacco_prevalence": [10.0, 20.0]})
    result = design_matrix(frame, ("gdp_per_capita_ppp", "tobacco_prevalence"))
    assert result["gdp_per_capita_ppp"].tolist() == pytest.approx([0.0, 1.0])
    assert result["tobacco_prevalence"].tolist() == [10.0, 20.0]


def test_nonpositive_log_input_is_rejected():
    frame = pd.DataFrame({"health_spending_ppp": [0.0]})
    with pytest.raises(ValueError, match="estritamente positivo"):
        design_matrix(frame, ("health_spending_ppp",))
