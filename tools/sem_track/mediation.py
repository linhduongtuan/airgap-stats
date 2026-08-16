"""Bootstrap confidence intervals for mediation effects -- Phase 3's other
high-priority item. The indirect effect a*b is a product of two
coefficients; its sampling distribution is not normal even when a and b
individually are (Sobel's normal-theory test is known to be conservative
and is no longer the recommended default -- Preacher & Hayes 2004, 2008).
The pre-Phase-3 structural-model scripts reported indirect/direct/total as
bare point estimates with no interval at all.

APPROACH -- two-step, not one-step joint SEM:
A full one-step structural model (ordinal CFA + structural regression paths
jointly estimated via DWLS/WLS in a single semopy fit -- see
`estimator.fit_structural_model`) is the textbook-first-choice approach.
It was tried here and rejected: semopy 2.3.11's WLS/DWLS solver stalls at
its starting values (chi2 comes back infinite, the optimizer never actually
moves) once a structural model has more than a handful of ordinal
indicators plus structural paths -- confirmed after ruling out the
numpy/scipy incompatibilities in compat.py as the cause (those are patched
and this failure remains). That's a semopy limitation, not a bug in this
repo's code.

The robust alternative used here is factor-score regression (Skrondal &
Laake 2001) -- a well-precedented two-step method for exactly this
situation:
  1. Fit the ordinal CFA alone (semopy DWLS) -- this step *is* numerically
     robust (verified), and it's the step that actually needs the ordinal
     estimator, since the Likert items are the ordinal data.
  2. Extract regression factor scores for each latent construct
     (`model.predict_factors`).
  3. Fit the structural path(s) as ordinary regressions on those factor
     scores via statsmodels -- OLS for a continuous mediator, logistic for
     a binary distal outcome -- both already battle-tested elsewhere in
     this repo.
Both stages are refit together inside the bootstrap loop, so the interval
reflects sampling variability in the factor scores too, not just the
second-stage regression's own uncertainty.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from .estimator import fit_measurement_model


def _fit_two_step(
    data: pd.DataFrame,
    constructs: dict[str, list[str]],
    mediator: str,
    predictor: str,
    outcome: str,
    outcome_is_binary: bool,
    covariates: list[str],
    estimator: str,
) -> tuple[float, float, float]:
    fit = fit_measurement_model(data, constructs, estimator=estimator)
    scores = fit.model.predict_factors(data)
    combined = pd.concat([data.reset_index(drop=True), scores.reset_index(drop=True)], axis=1)

    rhs_a = " + ".join([predictor] + covariates)
    a_fit = smf.ols(f"{mediator} ~ {rhs_a}", data=combined).fit()
    a = float(a_fit.params[predictor])

    rhs_bc = " + ".join([mediator, predictor] + covariates)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if outcome_is_binary:
            bc_fit = smf.logit(f"{outcome} ~ {rhs_bc}", data=combined).fit(disp=False)
        else:
            bc_fit = smf.ols(f"{outcome} ~ {rhs_bc}", data=combined).fit()
    b = float(bc_fit.params[mediator])
    c_prime = float(bc_fit.params[predictor])
    return a, b, c_prime


@dataclass
class MediationBootstrapResult:
    n_boot: int
    n_failed: int
    point: dict[str, float]
    ci_low: dict[str, float]
    ci_high: dict[str, float]
    ci_method: str

    def to_frame(self) -> pd.DataFrame:
        rows = []
        for name, est in self.point.items():
            lo, hi = self.ci_low[name], self.ci_high[name]
            rows.append({
                "path": name,
                "estimate": round(est, 4) if est == est else None,
                "ci_low": round(lo, 4) if lo == lo else None,
                "ci_high": round(hi, 4) if hi == hi else None,
            })
        return pd.DataFrame(rows)


def bootstrap_mediation(
    data: pd.DataFrame,
    constructs: dict[str, list[str]],
    mediator: str,
    predictor: str,
    outcome: str,
    outcome_is_binary: bool = True,
    covariates: list[str] | None = None,
    estimator: str = "DWLS",
    n_boot: int = 200,
    seed: int = 2026,
    alpha: float = 0.05,
) -> MediationBootstrapResult:
    """Percentile bootstrap CIs for the indirect (a*b), direct (c'), and
    total (c' + a*b) effects of a one-mediator model, via the two-step
    factor-score-regression approach described in this module's docstring.

    `constructs`: {construct_name: [item, ...]} for every latent construct
    in the model (predictor and mediator constructs; `predict_factors`
    needs the full measurement model to score any of them).
    `mediator`, `predictor`: construct names (must be keys of `constructs`).
    `outcome`: an observed column in `data` (the distal outcome).
    `covariates`: observed columns in `data`, included in both the a-path
    and b/c'-path regressions.
    """
    covariates = covariates or []
    rng = np.random.default_rng(seed)
    n = len(data)

    a0, b0, c0 = _fit_two_step(data, constructs, mediator, predictor, outcome,
                                outcome_is_binary, covariates, estimator)
    point = {"a": a0, "b": b0, "c_prime": c0, "indirect": a0 * b0, "total": c0 + a0 * b0}

    boot: dict[str, list[float]] = {"a": [], "b": [], "c_prime": [], "indirect": [], "total": []}
    n_failed = 0
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        boot_data = data.iloc[idx].reset_index(drop=True)
        try:
            a, b, c = _fit_two_step(boot_data, constructs, mediator, predictor, outcome,
                                     outcome_is_binary, covariates, estimator)
        except Exception:
            n_failed += 1
            continue
        if any(v != v for v in (a, b, c)):  # NaN check
            n_failed += 1
            continue
        boot["a"].append(a)
        boot["b"].append(b)
        boot["c_prime"].append(c)
        boot["indirect"].append(a * b)
        boot["total"].append(c + a * b)

    def _percentile_ci(vals: list[float]) -> tuple[float, float]:
        if not vals:
            return float("nan"), float("nan")
        lo = float(np.percentile(vals, 100 * alpha / 2))
        hi = float(np.percentile(vals, 100 * (1 - alpha / 2)))
        return lo, hi

    ci_low: dict[str, float] = {}
    ci_high: dict[str, float] = {}
    for name, vals in boot.items():
        ci_low[name], ci_high[name] = _percentile_ci(vals)

    return MediationBootstrapResult(
        n_boot=n_boot, n_failed=n_failed, point=point,
        ci_low=ci_low, ci_high=ci_high, ci_method="percentile",
    )


@dataclass
class RegressionBootstrapResult:
    n_boot: int
    n_failed: int
    point: dict[str, float]
    ci_low: dict[str, float]
    ci_high: dict[str, float]
    ci_method: str

    def to_frame(self) -> pd.DataFrame:
        rows = []
        for name, est in self.point.items():
            lo, hi = self.ci_low[name], self.ci_high[name]
            rows.append({
                "term": name,
                "estimate": round(est, 4) if est == est else None,
                "ci_low": round(lo, 4) if lo == lo else None,
                "ci_high": round(hi, 4) if hi == hi else None,
            })
        return pd.DataFrame(rows)


def bootstrap_structural_regression(
    data: pd.DataFrame,
    constructs: dict[str, list[str]],
    outcome: str,
    predictors: list[str],
    outcome_is_binary: bool = True,
    estimator: str = "DWLS",
    n_boot: int = 200,
    seed: int = 2026,
    alpha: float = 0.05,
) -> RegressionBootstrapResult:
    """Two-step (CFA -> factor scores -> regression) bootstrap for a
    structural model with **no mediation path** -- parallel/direct effects
    only (e.g. `outcome ~ construct_a + construct_b + observed_covariate`).

    Use `bootstrap_mediation` instead when the model has a genuine
    mediator (a path *into* one of the predictors from another). Bootstrapping
    here still matters even with no product-of-coefficients term: a naive
    Wald CI on the second-stage regression alone ignores the sampling
    uncertainty already present in the first-stage factor scores: this
    refits both stages together, so that uncertainty is included.

    `predictors` may mix construct names (keys of `constructs`) and observed
    column names in `data` -- both are looked up on the same combined frame.
    """
    rng = np.random.default_rng(seed)
    n = len(data)
    rhs = " + ".join(predictors)

    def _fit(d: pd.DataFrame) -> dict[str, float]:
        fit = fit_measurement_model(d, constructs, estimator=estimator)
        scores = fit.model.predict_factors(d)
        combined = pd.concat([d.reset_index(drop=True), scores.reset_index(drop=True)], axis=1)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if outcome_is_binary:
                reg = smf.logit(f"{outcome} ~ {rhs}", data=combined).fit(disp=False)
            else:
                reg = smf.ols(f"{outcome} ~ {rhs}", data=combined).fit()
        return {p: float(reg.params[p]) for p in predictors}

    point = _fit(data)
    boot: dict[str, list[float]] = {p: [] for p in predictors}
    n_failed = 0
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        boot_data = data.iloc[idx].reset_index(drop=True)
        try:
            vals = _fit(boot_data)
        except Exception:
            n_failed += 1
            continue
        if any(v != v for v in vals.values()):
            n_failed += 1
            continue
        for p in predictors:
            boot[p].append(vals[p])

    def _percentile_ci(vals: list[float]) -> tuple[float, float]:
        if not vals:
            return float("nan"), float("nan")
        lo = float(np.percentile(vals, 100 * alpha / 2))
        hi = float(np.percentile(vals, 100 * (1 - alpha / 2)))
        return lo, hi

    ci_low: dict[str, float] = {}
    ci_high: dict[str, float] = {}
    for name, vals in boot.items():
        ci_low[name], ci_high[name] = _percentile_ci(vals)

    return RegressionBootstrapResult(
        n_boot=n_boot, n_failed=n_failed, point=point,
        ci_low=ci_low, ci_high=ci_high, ci_method="percentile",
    )
