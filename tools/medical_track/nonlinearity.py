"""Non-linear biomarker handling: what to do once Phase 1's Box-Tidwell test
(`tools/diagnostics/regression_diagnostics.box_tidwell_test`) flags a
variable as `nonlinear_suspected`.

Two remedies, in order of how much structure they assume:
1. Log-transform, when the variable is skewed and strictly positive (the
   common case for biomarkers like CRP) -- keeps the model a plain logistic
   regression with one term per variable.
2. A restricted cubic spline basis (Harrell 2015), when a monotonic
   transform isn't enough -- replaces the single linear term with a small
   set of basis columns capturing a smooth non-linear shape.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class TransformDecision:
    variable: str
    action: str  # "log_transform" | "keep_linear" | "not_applicable"
    reason: str
    skewness: float | None = None


def log_transform_if_skewed(
    x: pd.Series,
    skew_threshold: float = 1.0,
) -> TransformDecision:
    """Decide whether a continuous variable should be log-transformed.

    A log-transform is suggested when the variable is strictly positive and
    its skewness exceeds `skew_threshold` (1.0 is a common rule-of-thumb cut
    for "substantially skewed"; distributions are symmetric at 0).
    Non-positive variables can't be log-transformed at all -- reported as
    `not_applicable`, the same convention `box_tidwell_test` uses, not
    silently skipped.
    """
    xs = x.dropna()
    if (xs <= 0).any():
        return TransformDecision(
            variable=str(x.name), action="not_applicable",
            reason="variable has non-positive values; cannot log-transform",
        )
    skewness = float(stats.skew(xs))
    if skewness > skew_threshold:
        return TransformDecision(
            variable=str(x.name), action="log_transform",
            reason=f"skewness {skewness:.2f} > {skew_threshold:g} -- right-skewed enough to log-transform",
            skewness=skewness,
        )
    return TransformDecision(
        variable=str(x.name), action="keep_linear",
        reason=f"skewness {skewness:.2f} <= {skew_threshold:g} -- not skewed enough to need a transform",
        skewness=skewness,
    )


def restricted_cubic_spline_basis(
    x: pd.Series | np.ndarray,
    n_knots: int = 4,
    knots: list[float] | None = None,
) -> pd.DataFrame:
    """Harrell's restricted cubic spline basis (Regression Modeling
    Strategies, 2015, eq. 2.24) -- `n_knots - 2` basis columns, linear
    outside the outer knots, smooth cubic between them.

    Default knot placement follows Harrell's recommended percentiles for
    3-6 knots (Table 2.1); pass `knots` explicitly to override.
    """
    orig_index = x.index if isinstance(x, pd.Series) else None
    x = np.asarray(x, dtype=float)
    if knots is None:
        default_pct = {
            3: [10, 50, 90],
            4: [5, 35, 65, 95],
            5: [5, 27.5, 50, 72.5, 95],
            6: [5, 23, 41, 59, 77, 95],
        }
        pct = default_pct.get(n_knots)
        if pct is None:
            pct = np.linspace(5, 95, n_knots).tolist()
        knots = np.percentile(x[~np.isnan(x)], pct).tolist()
    knots = sorted(knots)
    k = len(knots)
    if k < 3:
        raise ValueError("restricted_cubic_spline_basis needs at least 3 knots")

    t_last = knots[-1]
    t_first = knots[0]
    span = t_last - t_first

    columns = {}
    for j in range(k - 2):
        tj = knots[j]
        term = (
            np.clip(x - tj, 0, None) ** 3
            - np.clip(x - knots[k - 2], 0, None) ** 3 * (t_last - tj) / span
            + np.clip(x - t_last, 0, None) ** 3 * (knots[k - 2] - tj) / span
        )
        columns[f"spline_{j + 1}"] = term / (span ** 2)  # scale for numerical stability

    return pd.DataFrame(columns, index=orig_index)
