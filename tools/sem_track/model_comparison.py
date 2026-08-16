"""Nested model comparison -- e.g. full mediation (no direct path) vs.
partial mediation (direct path free) -- via a chi-square difference test
plus AIC/BIC. The pre-Phase-3 structural-model scripts asserted one
specified model without ever comparing it to a simpler nested alternative.

Two functions, matched to where each is numerically reliable (see
mediation.py's docstring for why this split exists):
- `compare_nested_models` -- SEM chi-square difference test on two
  `estimator.FitResult` objects. Reliable for measurement-model
  comparisons (e.g. one-factor vs. two-factor CFA); not recommended for
  full structural models with many ordinal indicators, where semopy's
  solver can silently stall (check `.converged` on both fits first).
- `compare_nested_regressions` -- a likelihood-ratio test on two
  statsmodels regression fits, for comparing nested structural paths from
  the two-step factor-score-regression approach `mediation.py` uses (e.g.
  the b/c' regression with vs. without the direct path term).
"""

from __future__ import annotations

from dataclasses import dataclass

from scipy import stats as scipy_stats

from .estimator import FitResult


@dataclass
class ModelComparisonResult:
    chi2_full: float
    chi2_restricted: float
    df_full: float
    df_restricted: float
    delta_chi2: float
    delta_df: float
    p_value: float
    aic_full: float
    aic_restricted: float
    bic_full: float
    bic_restricted: float
    preferred: str


def compare_nested_models(
    fit_full: FitResult,
    fit_restricted: FitResult,
    alpha: float = 0.05,
) -> ModelComparisonResult:
    """Chi-square difference test. `fit_restricted` must be `fit_full` with
    one or more paths dropped/constrained (i.e. nested inside it, with
    strictly fewer free parameters) -- e.g. `fit_full` = partial mediation
    (direct path free), `fit_restricted` = full mediation (direct path
    omitted). A significant Delta-chi2 favors keeping the extra path(s);
    non-significant favors the simpler, restricted model.
    """
    chi2_full = fit_full.fit_indices["chi2"]
    chi2_restricted = fit_restricted.fit_indices["chi2"]
    df_full = fit_full.fit_indices["dof"]
    df_restricted = fit_restricted.fit_indices["dof"]

    delta_df = df_restricted - df_full
    if delta_df <= 0:
        raise ValueError(
            "fit_restricted must have more degrees of freedom (fewer free parameters) "
            "than fit_full -- are the models really nested, in that order?"
        )
    delta_chi2 = chi2_restricted - chi2_full
    p_value = float(scipy_stats.chi2.sf(delta_chi2, delta_df)) if delta_chi2 >= 0 else float("nan")

    if p_value == p_value and p_value < alpha:
        preferred = "full (less restricted) -- the dropped path(s) matter"
    else:
        preferred = "restricted (more parsimonious) -- the dropped path(s) don't earn their keep"

    return ModelComparisonResult(
        chi2_full=chi2_full, chi2_restricted=chi2_restricted,
        df_full=df_full, df_restricted=df_restricted,
        delta_chi2=round(delta_chi2, 4), delta_df=delta_df,
        p_value=round(p_value, 4) if p_value == p_value else float("nan"),
        aic_full=fit_full.fit_indices["aic"], aic_restricted=fit_restricted.fit_indices["aic"],
        bic_full=fit_full.fit_indices["bic"], bic_restricted=fit_restricted.fit_indices["bic"],
        preferred=preferred,
    )


@dataclass
class RegressionComparisonResult:
    llf_full: float
    llf_restricted: float
    df_full: int
    df_restricted: int
    lr_stat: float
    delta_df: int
    p_value: float
    aic_full: float
    aic_restricted: float
    bic_full: float
    bic_restricted: float
    preferred: str


def compare_nested_regressions(fit_full, fit_restricted, alpha: float = 0.05) -> RegressionComparisonResult:
    """Likelihood-ratio test for two nested statsmodels regression fits
    (e.g. from `mediation.py`'s two-step b/c' regression, fit once with the
    direct path term and once without it -- `fit_restricted` is the one
    missing term(s)). LR = 2*(llf_full - llf_restricted) ~ chi2(delta_df).
    """
    llf_full = float(fit_full.llf)
    llf_restricted = float(fit_restricted.llf)
    df_full = int(fit_full.df_model)
    df_restricted = int(fit_restricted.df_model)

    delta_df = df_full - df_restricted
    if delta_df <= 0:
        raise ValueError(
            "fit_full must have more free parameters than fit_restricted -- "
            "are the models really nested, in that order?"
        )
    lr_stat = 2 * (llf_full - llf_restricted)
    p_value = float(scipy_stats.chi2.sf(lr_stat, delta_df)) if lr_stat >= 0 else float("nan")

    if p_value == p_value and p_value < alpha:
        preferred = "full (less restricted) -- the dropped term(s) matter"
    else:
        preferred = "restricted (more parsimonious) -- the dropped term(s) don't earn their keep"

    return RegressionComparisonResult(
        llf_full=llf_full, llf_restricted=llf_restricted,
        df_full=df_full, df_restricted=df_restricted,
        lr_stat=round(lr_stat, 4), delta_df=delta_df,
        p_value=round(p_value, 4) if p_value == p_value else float("nan"),
        aic_full=float(fit_full.aic), aic_restricted=float(fit_restricted.aic),
        bic_full=float(fit_full.bic), bic_restricted=float(fit_restricted.bic),
        preferred=preferred,
    )
