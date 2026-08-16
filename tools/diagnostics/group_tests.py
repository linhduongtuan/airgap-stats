"""Formal group-comparison tests for Table 1, auto-selected the way
`plans/sap.md` Section G requires: the test branches at runtime on a
normality/expected-cell-count check, with the branch and its reason recorded,
never fixed in advance (nobody has seen the real data's distribution).

Continuous: Shapiro-Wilk per group -> Welch's t-test (2 groups) / one-way
ANOVA (>2 groups) if all groups look normal, else Mann-Whitney U / Kruskal-Wallis.

Categorical: chi-squared if every expected cell count clears the threshold
(5, the standard rule of thumb), else Fisher's exact -- scipy's `fisher_exact`
supports r x c tables, not just 2x2, so this isn't limited to binary variables.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

SHAPIRO_MIN_N = 3


def _welch_anova(samples: list[np.ndarray]) -> tuple[float, float]:
    """Welch's one-way ANOVA (Welch 1951) -- does not assume equal group
    variances, for consistency with the 2-group branch (Welch's t-test) and
    with R's `oneway.test(..., var.equal = FALSE)`, which is R's default and
    implements the same formula. `scipy.stats.f_oneway` assumes equal
    variances, which would be an unjustified assumption here -- nobody has
    seen the real data's group variances any more than its normality.
    """
    k = len(samples)
    n = np.array([len(s) for s in samples], dtype=float)
    m = np.array([s.mean() for s in samples])
    v = np.array([s.var(ddof=1) for s in samples])
    w = n / v
    sum_w = w.sum()
    grand_mean = (w * m).sum() / sum_w

    numerator = (w * (m - grand_mean) ** 2).sum() / (k - 1)
    tmp = ((1 - w / sum_w) ** 2 / (n - 1)).sum()
    denominator = 1 + (2 * (k - 2) / (k**2 - 1)) * tmp
    f_stat = float(numerator / denominator)

    df1 = k - 1
    df2 = (k**2 - 1) / (3 * tmp)
    p_value = float(stats.f.sf(f_stat, df1, df2))
    return f_stat, p_value


@dataclass
class GroupTestResult:
    variable: str
    kind: str  # "continuous" | "categorical"
    n_groups: int
    test_used: str
    statistic: float | None
    p_value: float | None
    branch_reason: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_row(self) -> dict[str, Any]:
        """Flat dict suitable for a Table 1 CSV column."""
        return {
            "variable": self.variable,
            "test": self.test_used,
            "statistic": round(self.statistic, 4) if self.statistic is not None else None,
            "p_value": round(self.p_value, 4) if self.p_value is not None else None,
            "branch_reason": self.branch_reason,
        }


def _shapiro_normal(x: np.ndarray) -> tuple[bool, float | None]:
    """True if the sample does not reject normality at alpha=0.05.

    Too few points or a constant sample can't be tested meaningfully -- treated
    as "not confirmed normal" (the conservative branch), not as an error.
    """
    x = x[~np.isnan(x)]
    if len(x) < SHAPIRO_MIN_N or len(np.unique(x)) < 2:
        return False, None
    _stat, p = stats.shapiro(x)
    return bool(p >= 0.05), float(p)


def compare_continuous(data: pd.DataFrame, var: str, group: str) -> GroupTestResult:
    """Compare a continuous variable across the levels of `group`."""
    sub = data[[var, group]].dropna()
    groups = sorted(sub[group].unique())
    samples = [sub.loc[sub[group] == g, var].to_numpy(dtype=float) for g in groups]
    k = len(groups)

    if k < 2 or any(len(s) == 0 for s in samples):
        return GroupTestResult(
            var, "continuous", k, "none", None, None,
            "fewer than 2 groups with data -- no test possible",
        )

    normality: dict[str, dict[str, Any]] = {}
    all_normal = True
    for g, s in zip(groups, samples):
        ok, p = _shapiro_normal(s)
        normality[str(g)] = {"shapiro_p": p, "normal": ok, "n": len(s)}
        all_normal = all_normal and ok

    if k == 2:
        if all_normal:
            stat, p = stats.ttest_ind(samples[0], samples[1], equal_var=False)
            test_used, reason = "welch_t_test", "both groups pass Shapiro-Wilk (p>=0.05) -> two-sample t-test (Welch)"
        else:
            stat, p = stats.mannwhitneyu(samples[0], samples[1], alternative="two-sided")
            test_used, reason = "mann_whitney_u", "at least one group fails Shapiro-Wilk (p<0.05) -> Mann-Whitney U"
    else:
        if all_normal:
            stat, p = _welch_anova(samples)
            test_used, reason = "welch_anova", f"{k} groups, all pass Shapiro-Wilk -> Welch's one-way ANOVA (unequal variances)"
        else:
            stat, p = stats.kruskal(*samples)
            test_used, reason = "kruskal_wallis", f"{k} groups, at least one fails Shapiro-Wilk -> Kruskal-Wallis"

    return GroupTestResult(
        var, "continuous", k, test_used, float(stat), float(p), reason,
        {"normality": normality, "group_ns": {str(g): len(s) for g, s in zip(groups, samples)}},
    )


def compare_categorical(data: pd.DataFrame, var: str, group: str, min_expected: float = 5.0) -> GroupTestResult:
    """Compare a categorical variable across the levels of `group`."""
    sub = data[[var, group]].dropna()
    table = pd.crosstab(sub[var], sub[group])
    n_groups = table.shape[1]

    if table.shape[0] < 2 or n_groups < 2:
        return GroupTestResult(
            var, "categorical", n_groups, "none", None, None,
            "fewer than 2 levels on one side of the table -- no test possible",
        )

    chi2, p_chi2, _dof, expected = stats.chi2_contingency(table)
    min_exp = float(expected.min())

    if min_exp >= min_expected:
        test_used = "chi_squared"
        stat, p = float(chi2), float(p_chi2)
        reason = f"min expected cell count {min_exp:.1f} >= {min_expected:g} -> chi-squared"
    else:
        stat, p = stats.fisher_exact(table.to_numpy())
        stat, p = float(stat), float(p)
        test_used = "fisher_exact"
        reason = f"min expected cell count {min_exp:.1f} < {min_expected:g} -> Fisher's exact"

    return GroupTestResult(
        var, "categorical", n_groups, test_used, stat, p, reason,
        {"min_expected_cell_count": min_exp, "table_shape": list(table.shape)},
    )
