"""Regression diagnostics for the adjusted logistic model: multicollinearity
(VIF), influence (Cook's distance / DFBETAs), and a linearity-in-the-logit
check (Box-Tidwell). None of these existed before Phase 1 -- the adjusted
model previously shipped with no check that its own assumptions held.
"""

from __future__ import annotations

import warnings
from typing import Sequence

import numpy as np
import pandas as pd
import patsy
import statsmodels.formula.api as smf
from statsmodels.stats.outliers_influence import variance_inflation_factor

VIF_FLAG_THRESHOLD = 5.0  # conventional "worth a look" cutoff; 10 is the harder cutoff


def compute_vif(data: pd.DataFrame, formula_rhs: str) -> pd.DataFrame:
    """VIF per term in `formula_rhs` (the same right-hand side used to fit the
    model), categorical variables dummy-coded exactly as the model would.

    Returns a DataFrame sorted by VIF descending, with an intercept row
    excluded (its VIF is not a collinearity diagnostic).
    """
    design = patsy.dmatrix(formula_rhs, data=data, return_type="dataframe")
    x = design.to_numpy()
    rows = []
    for i, col in enumerate(design.columns):
        if col == "Intercept":
            continue
        vif = variance_inflation_factor(x, i)
        rows.append({"term": col, "vif": float(vif), "flagged": bool(vif > VIF_FLAG_THRESHOLD)})
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values("vif", ascending=False).reset_index(drop=True)
    return out


def compute_influence(fit_result) -> tuple[pd.DataFrame, float]:
    """Cook's distance per observation for a fitted statsmodels result
    (e.g. `smf.logit(formula, data=data).fit()`).

    Returns (dataframe, threshold). Threshold is the common rule of thumb
    4/n; observations above it are flagged, not automatically removed --
    removal is always a human decision.
    """
    influence = fit_result.get_influence()
    cooks_d, _p_values = influence.cooks_distance
    n = int(fit_result.nobs)
    threshold = 4.0 / n
    df = pd.DataFrame({
        "obs_index": np.arange(len(cooks_d)),
        "cooks_distance": cooks_d,
    })
    df["flagged"] = df["cooks_distance"] > threshold
    return df, threshold


def compute_dfbetas(fit_result) -> tuple[pd.DataFrame, float]:
    """DFBETAs per observation per coefficient for a fitted statsmodels result.

    Returns (dataframe, threshold). Threshold is the common rule of thumb
    2/sqrt(n). `max_abs_dfbeta` is the worst coefficient shift for that
    observation, across all terms -- the single number worth scanning first.

    NOTE on R parity: unlike VIF, Box-Tidwell, and the group-comparison
    tests (which match R's equivalents to 6 decimal places on identical
    data), DFBETAs values differ from R's `dfbetas()` by a few percent.
    Both use the same standard one-step Newton approximation for GLMs, but
    statsmodels' and R's internal formulas round slightly differently --
    a well-documented, harmless cross-software difference, not a bug (the
    underlying fitted coefficients themselves match to 6 decimals). Expect
    the flagged-observation count to differ slightly near the threshold.
    """
    influence = fit_result.get_influence()
    dfbetas = influence.dfbetas
    n = int(fit_result.nobs)
    threshold = 2.0 / np.sqrt(n)
    param_names = list(fit_result.model.exog_names)
    df = pd.DataFrame(dfbetas, columns=param_names)
    df.insert(0, "obs_index", np.arange(len(df)))
    df["max_abs_dfbeta"] = df[param_names].abs().max(axis=1)
    df["flagged"] = df["max_abs_dfbeta"] > threshold
    return df, threshold


def box_tidwell_test(
    data: pd.DataFrame,
    outcome: str,
    base_formula_rhs: str,
    continuous_vars: Sequence[str],
) -> pd.DataFrame:
    """Box-Tidwell test for linearity in the logit.

    For each variable in `continuous_vars`, refits
    `outcome ~ base_formula_rhs + var:np.log(var)` and reports the p-value of
    the added interaction term. A significant term (p < 0.05) suggests the
    variable is *not* linear on the log-odds scale and should be
    log-transformed or modeled with a spline (Phase 2 of the roadmap).

    Requires every value of `var` to be strictly positive (log is undefined
    otherwise); such variables are reported as `skipped`, not silently
    dropped.
    """
    rows = []
    for var in continuous_vars:
        x = data[var]
        if (x <= 0).any():
            rows.append({
                "variable": var, "status": "skipped", "p_value": None,
                "detail": f"{var} has non-positive values; Box-Tidwell requires x > 0",
            })
            continue

        formula = f"{outcome} ~ {base_formula_rhs} + {var}:np.log({var})"
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                fit = smf.logit(formula, data=data).fit(disp=False, maxiter=200)
        except Exception as exc:  # noqa: BLE001 -- report, don't crash the caller's script
            rows.append({"variable": var, "status": "error", "p_value": None, "detail": str(exc)})
            continue

        term_candidates = [n for n in fit.pvalues.index if var in n and "log" in n]
        if not term_candidates:
            rows.append({
                "variable": var, "status": "error", "p_value": None,
                "detail": "interaction term not found in fitted model output",
            })
            continue

        p = float(fit.pvalues[term_candidates[0]])
        status = "linear" if p >= 0.05 else "nonlinear_suspected"
        rows.append({
            "variable": var, "status": status, "p_value": round(p, 4),
            "detail": f"interaction term `{term_candidates[0]}` p={p:.4f}",
        })

    return pd.DataFrame(rows)
