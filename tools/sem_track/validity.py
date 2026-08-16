"""Convergent and discriminant validity: AVE, composite reliability (CR),
and the HTMT ratio -- none of which the pre-Phase-3 measurement model
checked. Two constructs can each have fine alpha/omega and still not be
empirically distinguishable from each other (a real risk for something
like Job Satisfaction and Burnout, which are conceptually near-opposites
and likely to correlate highly) -- HTMT is the check for that.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def average_variance_extracted(std_loadings: pd.Series) -> float:
    """AVE = mean of squared standardized loadings. >= 0.50 is the
    conventional threshold (Fornell & Larcker 1981) -- the construct
    explains at least half the variance in its own items, on average.
    """
    return float((std_loadings ** 2).mean())


def composite_reliability(std_loadings: pd.Series) -> float:
    """CR = (sum of loadings)^2 / [(sum of loadings)^2 + sum of (1 - loadings^2)].
    Numerically the same formula as McDonald's omega when the error
    variances are `1 - loading^2` (i.e. the standardized model) -- CR and
    omega are reported separately by convention, but they are not
    independent pieces of evidence.
    """
    sum_loadings = float(std_loadings.sum())
    sum_errors = float((1 - std_loadings ** 2).sum())
    denom = sum_loadings ** 2 + sum_errors
    return (sum_loadings ** 2) / denom if denom > 0 else float("nan")


def htmt(data: pd.DataFrame, construct_a_items: list[str], construct_b_items: list[str]) -> float:
    """Heterotrait-monotrait ratio of correlations (Henseler, Ringle &
    Sarstedt 2015). Below 0.85 (strict) or 0.90 (lenient) supports
    discriminant validity -- above that, the two constructs are not
    reliably distinguishable from raw correlations alone.
    """
    all_items = construct_a_items + construct_b_items
    corr = data[all_items].corr().abs()

    heterotrait = corr.loc[construct_a_items, construct_b_items].to_numpy()
    het_mean = heterotrait.mean()

    def monotrait_mean(items: list[str]) -> float:
        if len(items) < 2:
            return float("nan")
        sub = corr.loc[items, items].to_numpy()
        n = len(items)
        off_diag = sub[~np.eye(n, dtype=bool)]
        return float(off_diag.mean())

    mono_a = monotrait_mean(construct_a_items)
    mono_b = monotrait_mean(construct_b_items)
    denom = np.sqrt(mono_a * mono_b)
    return float(het_mean / denom) if denom > 0 else float("nan")


def htmt_matrix(data: pd.DataFrame, constructs: dict[str, list[str]]) -> pd.DataFrame:
    """HTMT for every pair of constructs, as a symmetric matrix (diagonal NaN)."""
    names = list(constructs.keys())
    out = pd.DataFrame(np.nan, index=names, columns=names)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            value = htmt(data, constructs[a], constructs[b])
            out.loc[a, b] = value
            out.loc[b, a] = value
    return out
