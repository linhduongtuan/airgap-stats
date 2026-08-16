"""Time-to-event modeling: Kaplan-Meier estimation (with a log-rank test
between groups) and Cox proportional-hazards regression.

Both wrap statsmodels' `statsmodels.duration` submodule directly (already a
declared dependency via statsmodels, no new package) -- this module exists
to give the DR workflow's usual "fit, extract a tidy table, explain the
branch" shape, not to reimplement survival analysis from scratch.

Dichotomizing an outcome at a fixed follow-up window (e.g. `mortality_30day`)
throws away information a genuine time-to-event column would use. This
module is for projects where an actual time-to-event/censoring column
exists -- confirm with the user which column plays that role before using
it; a duration-shaped column (e.g. length of stay) is not automatically the
right survival time without that confirmation. See plans/sap.md.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from statsmodels.duration.hazard_regression import PHReg
from statsmodels.duration.survfunc import SurvfuncRight, survdiff


@dataclass
class KaplanMeierResult:
    curves: dict[str, pd.DataFrame]  # group label -> survival table
    median_survival: dict[str, float]
    logrank_stat: float | None
    logrank_p: float | None
    n_groups: int


def kaplan_meier(
    data: pd.DataFrame,
    time_col: str,
    event_col: str,
    group_col: str | None = None,
) -> KaplanMeierResult:
    """Kaplan-Meier survival curve(s), with a log-rank test between groups
    when `group_col` is given and has >= 2 levels with events.

    `event_col` must be 1 = event occurred, 0 = censored (administrative
    end of follow-up, loss to follow-up, etc.) -- the standard
    right-censoring convention `SurvfuncRight` expects.
    """
    sub = data[[time_col, event_col] + ([group_col] if group_col else [])].dropna()
    curves: dict[str, pd.DataFrame] = {}
    medians: dict[str, float] = {}

    if group_col is None:
        sf = SurvfuncRight(sub[time_col].to_numpy(), sub[event_col].to_numpy())
        curves["Overall"] = sf.summary()
        medians["Overall"] = float(sf.quantile(0.5))
        return KaplanMeierResult(curves, medians, None, None, 1)

    groups = sorted(sub[group_col].unique())
    for g in groups:
        gsub = sub[sub[group_col] == g]
        sf = SurvfuncRight(gsub[time_col].to_numpy(), gsub[event_col].to_numpy())
        curves[str(g)] = sf.summary()
        medians[str(g)] = float(sf.quantile(0.5))

    logrank_stat = logrank_p = None
    if len(groups) >= 2:
        result = survdiff(sub[time_col].to_numpy(), sub[event_col].to_numpy(), sub[group_col].to_numpy())
        # statsmodels returns (chi2, p, ...) as a plain tuple, not a named result
        logrank_stat, logrank_p = float(result[0]), float(result[1])

    return KaplanMeierResult(curves, medians, logrank_stat, logrank_p, len(groups))


@dataclass
class CoxPHResult:
    table: pd.DataFrame
    nobs: int
    n_events: int
    converged: bool


def cox_ph(data: pd.DataFrame, formula_rhs: str, time_col: str, event_col: str) -> CoxPHResult:
    """Cox proportional-hazards regression. `formula_rhs` is the same kind
    of right-hand side used elsewhere in this repo (e.g. the adjusted
    logistic model's covariate string) -- reusing it means a project's
    already-confirmed covariate list carries over without rewriting it.
    """
    sub = data.dropna(subset=[time_col, event_col])
    formula = f"{time_col} ~ {formula_rhs}"
    model = PHReg.from_formula(formula, data=sub, status=event_col)
    fit = model.fit()

    ci = fit.conf_int()
    table = pd.DataFrame({
        "term": fit.model.exog_names,
        "log_hr": fit.params.round(4),
        "hr": np.exp(fit.params).round(4),
        "ci_low": np.exp(ci[:, 0]).round(4),
        "ci_high": np.exp(ci[:, 1]).round(4),
        "p_value": fit.pvalues.round(4),
    }).reset_index(drop=True)

    return CoxPHResult(
        table=table,
        nobs=int(fit.model.exog.shape[0]),
        n_events=int(sub[event_col].sum()),
        converged=True,  # PHReg.fit() raises rather than returning a non-converged result
    )
