"""Reliability: Cronbach's alpha (already used throughout this repo) plus
McDonald's omega, which Phase 3 adds because alpha assumes tau-equivalence
(every item loads on its factor equally) -- an assumption the CFA step
right next to it will usually contradict. Omega uses the CFA's own
standardized loadings and error variances, so it doesn't need that
assumption.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


def cronbach_alpha(items_df: pd.DataFrame) -> float:
    df = items_df.dropna()
    k = df.shape[1]
    if k < 2:
        return float("nan")
    item_vars = df.var(ddof=1)
    total_var = df.sum(axis=1).var(ddof=1)
    return float((k / (k - 1)) * (1 - item_vars.sum() / total_var))


def mcdonald_omega(loadings: pd.Series, error_vars: pd.Series) -> float:
    """omega = (sum of standardized loadings)^2 /
               [(sum of standardized loadings)^2 + sum of error variances]

    `loadings` and `error_vars` should be standardized (both on a 0/1
    correlation-matrix scale) -- e.g. from a single-factor CFA's
    `model.inspect(std_est=True)`, the `~` rows for loadings and the
    `~~` diagonal rows for error variances.
    """
    sum_loadings = float(loadings.sum())
    sum_errors = float(error_vars.sum())
    denom = sum_loadings ** 2 + sum_errors
    if denom <= 0:
        return float("nan")
    return (sum_loadings ** 2) / denom


@dataclass
class ReliabilitySummary:
    construct: str
    n_items: int
    alpha: float
    omega: float | None


def reliability_from_cfa(
    data: pd.DataFrame,
    construct: str,
    items: list[str],
    loadings: pd.DataFrame,
) -> ReliabilitySummary:
    """Convenience wrapper: alpha from raw item data, omega from a fitted
    CFA's loadings table (as returned by `estimator.fit_measurement_model`
    -- the `~` rows of `model.inspect(std_est=True)`, filtered to this
    construct's items).
    """
    alpha = cronbach_alpha(data[items])

    # semopy represents a measurement loading "Construct =~ item" internally
    # as the row item(lval) ~ Construct(rval) -- lval is the item, not the
    # factor. Easy to get backwards; this is the opposite orientation from
    # a structural path like "Y ~ X", where lval=Y is the outcome.
    construct_loadings = loadings[(loadings["rval"] == construct) & (loadings["lval"].isin(items))]
    if construct_loadings.empty:
        omega = None
    else:
        std_loadings = construct_loadings["Est. Std"]
        error_vars = 1 - std_loadings ** 2  # standardized item residual variance
        omega = mcdonald_omega(std_loadings, error_vars)

    return ReliabilitySummary(construct=construct, n_items=len(items), alpha=round(alpha, 3),
                               omega=round(omega, 3) if omega is not None else None)
