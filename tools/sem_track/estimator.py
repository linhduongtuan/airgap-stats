"""Ordinal-aware CFA/SEM fitting -- Phase 3's highest-priority item.

Likert items are ordinal, not continuous. Fitting them with ML (which
assumes continuous, multivariate-normal data) is the wrong default; the
methodologically correct choice is WLSMV/DWLS on the polychoric correlation
matrix (Flora & Curran 2004; Rhemtulla et al. 2012 for evidence that this
actually matters for 5-point-or-fewer scales). semopy's `obj='DWLS'` +
`ordinal:` declaration implements this (via the patches in compat.py).

`estimator="ML"` is still available and is a defensible choice when items
have >= 7 response categories or are effectively continuous -- see
plans/sem_measurement_plan.yaml's `estimator.rationale` field (Phase 0).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd
import semopy

from . import compat as _compat  # noqa: F401  (import applies the patches)

_OBJ_MAP = {"ML": "MLW", "WLS": "WLS", "DWLS": "DWLS"}


@dataclass
class FitResult:
    model: semopy.Model
    estimator: str
    converged: bool
    loadings: pd.DataFrame
    fit_indices: dict[str, float]
    params: pd.DataFrame  # full model.inspect(std_est=True) output


def build_cfa_syntax(constructs: dict[str, list[str]], ordinal_items: list[str] | None = None) -> str:
    """Build lavaan/semopy model syntax for a measurement model.

    `ordinal_items` defaults to every item across every construct -- the
    common case for a survey where all Likert items get the same estimator.
    Pass an explicit (possibly empty) list to override.
    """
    if ordinal_items is None:
        ordinal_items = [item for items in constructs.values() for item in items]

    lines = []
    if ordinal_items:
        lines.append("ordinal: " + " ".join(ordinal_items))
    for construct, items in constructs.items():
        lines.append(f"{construct} =~ " + " + ".join(items))
    return "\n".join(lines)


def fit_measurement_model(
    data: pd.DataFrame,
    constructs: dict[str, list[str]],
    estimator: str = "DWLS",
    ordinal_items: list[str] | None = None,
) -> FitResult:
    """Fit a CFA measurement model. `estimator`: "DWLS" (default, for
    Likert items), "WLS", or "ML" (continuous items only)."""
    if estimator not in _OBJ_MAP:
        raise ValueError(f"estimator must be one of {list(_OBJ_MAP)}")

    syntax = build_cfa_syntax(constructs, ordinal_items)
    model = semopy.Model(syntax)
    solver_result = model.fit(data, obj=_OBJ_MAP[estimator])

    params = model.inspect(std_est=True)
    loadings = params[params["op"] == "~"].reset_index(drop=True)

    stats = semopy.calc_stats(model)
    fit_indices = _extract_fit_indices(stats)

    converged = bool(getattr(solver_result, "success", False))
    return FitResult(model=model, estimator=estimator, converged=converged,
                      loadings=loadings, fit_indices=fit_indices, params=params)


def factor_scores(fit: FitResult, data: pd.DataFrame) -> pd.DataFrame:
    """Regression factor scores from a fitted measurement model, one column
    per construct -- continuous proxies for the latent constructs, used by
    `mediation.bootstrap_mediation`'s two-step approach when a full joint
    structural model is numerically unstable (see that module's docstring).
    """
    return fit.model.predict_factors(data)


def fit_structural_model(
    data: pd.DataFrame,
    syntax: str,
    estimator: str = "DWLS",
    ordinal_items: list[str] | None = None,
) -> FitResult:
    """Fit a full structural model from raw semopy/lavaan syntax (measurement
    + structural equations already written out) -- for cases
    `fit_measurement_model`'s simple one-construct-per-block builder doesn't
    cover (mediation paths, covariates, labeled parameters for `:=` effects).

    CAVEAT: with `estimator="DWLS"`/`"WLS"` and many ordinal indicators
    (roughly: more than one construct's worth of Likert items plus
    structural paths), semopy 2.3.11's solver can stall at its starting
    values instead of raising an error -- check `.converged` and treat a
    `False` here as "this model shape doesn't fit reliably with semopy's
    WLS solver," not as evidence about the actual structural relationship.
    For mediation specifically, prefer `mediation.bootstrap_mediation`,
    which sidesteps this via factor-score regression. This function remains
    reliable for measurement-model-only fits and smaller structural models
    (few ordinal indicators, or a continuous distal outcome).
    """
    if estimator not in _OBJ_MAP:
        raise ValueError(f"estimator must be one of {list(_OBJ_MAP)}")

    full_syntax = syntax
    if ordinal_items:
        full_syntax = "ordinal: " + " ".join(ordinal_items) + "\n" + syntax

    model = semopy.Model(full_syntax)
    solver_result = model.fit(data, obj=_OBJ_MAP[estimator])

    params = model.inspect(std_est=True)
    loadings = params[params["op"] == "~"].reset_index(drop=True)
    stats = semopy.calc_stats(model)
    fit_indices = _extract_fit_indices(stats)
    converged = bool(getattr(solver_result, "success", False))

    return FitResult(model=model, estimator=estimator, converged=converged,
                      loadings=loadings, fit_indices=fit_indices, params=params)


def _extract_fit_indices(stats: pd.DataFrame) -> dict[str, float]:
    """semopy's calc_stats returns a 1-row DataFrame with columns like
    'chi2', 'CFI', 'RMSEA', ... -- normalize to the lowercase names used
    throughout this repo's plan YAMLs. SRMR is not always present in
    semopy's output (a known semopy limitation, not something this wrapper
    can add); reported as NaN when absent rather than silently omitted.
    """
    row = stats.iloc[0] if isinstance(stats, pd.DataFrame) else stats
    lookup = {str(k).lower(): float(v) for k, v in row.items()}
    wanted = {
        "cfi": "cfi", "tli": "tli", "rmsea": "rmsea", "srmr": "srmr",
        "chi2": "chi2", "chi2 p-value": "chi2_pvalue", "dof": "dof", "dof baseline": "dof_baseline",
        "aic": "aic", "bic": "bic",
    }
    out = {}
    for src_key, out_key in wanted.items():
        out[out_key] = lookup.get(src_key, float("nan"))
    return out
