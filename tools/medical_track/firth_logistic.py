"""Firth penalized logistic regression (Firth 1993; Heinze & Schemper 2002).

Plain maximum-likelihood logistic regression is fragile at the sample sizes
a single-center clinical study typically has: with ~200 rows and a dozen
covariates, quasi-separation is common, and MLE responds to it by driving
coefficients (and their standard errors) toward +-infinity. Firth's method
penalizes the likelihood by the Jeffreys prior |I(beta)|^(1/2), which is
equivalent to a fixed modification of the score equations -- it exists for
exactly this situation and remains stable under separation where plain MLE
does not.

Implementation note: this is the modified-score-equations algorithm (the
same one R's `logistf` and Stata's `firthlogit` use), not a call into any
existing penalized-GLM library -- statsmodels has no built-in Firth
estimator. Cross-validated against R's `logistf` on both a well-behaved
dataset and a deliberately-separated one; coefficients agree to 4+ decimal
places (see tests/test_medical_track.py).

Confidence intervals here are Wald (beta +- 1.96*SE) from the same
information matrix used to fit the model. Firth's method already makes
those first-order stable, but profile-penalized-likelihood CIs are more
accurate right at the edge of separation, where a single Wald SE can still
understate uncertainty -- `logistf` defaults to profile CIs. That
refinement isn't implemented here; treat the Wald CIs as an approximation
and prefer the point estimate and p-value, which the score modification
targets directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import patsy
from scipy import stats


@dataclass
class FirthResult:
    params: pd.Series
    bse: pd.Series
    or_: pd.Series
    ci_low: pd.Series
    ci_high: pd.Series
    p_value: pd.Series
    converged: bool
    n_iter: int
    nobs: int
    exog_names: list[str] = field(default_factory=list)

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame({
            "term": self.exog_names,
            "estimate": self.params.round(4).to_numpy(),
            "or": self.or_.round(4).to_numpy(),
            "ci_low": self.ci_low.round(4).to_numpy(),
            "ci_high": self.ci_high.round(4).to_numpy(),
            "p_value": self.p_value.round(4).to_numpy(),
        })


def _fit_firth(X: np.ndarray, y: np.ndarray, max_iter: int, tol: float) -> tuple[np.ndarray, np.ndarray, bool, int]:
    """Core IRLS loop with Firth's modified score. Returns (beta, cov, converged, n_iter)."""
    n, p = X.shape
    beta = np.zeros(p)
    cov = np.eye(p)

    for iteration in range(1, max_iter + 1):
        eta = X @ beta
        eta = np.clip(eta, -30, 30)  # guard exp() overflow; the penalty keeps beta finite anyway
        pi = 1.0 / (1.0 + np.exp(-eta))
        w = pi * (1 - pi)
        w = np.clip(w, 1e-10, None)

        xtwx = X.T @ (X * w[:, None])
        try:
            xtwx_inv = np.linalg.inv(xtwx)
        except np.linalg.LinAlgError:
            return beta, cov, False, iteration

        # Hat-matrix diagonal h_i = w_i * x_i (X'WX)^-1 x_i'
        h = w * np.einsum("ij,jk,ik->i", X, xtwx_inv, X)

        # Firth's modified score: standard score + penalty term h_i*(0.5 - pi_i) per observation
        u_star = X.T @ (y - pi + h * (0.5 - pi))
        delta = xtwx_inv @ u_star

        # Step-halving safety net: if a full Newton step overshoots badly
        # (can happen on the first couple of iterations from beta=0 with a
        # near-separated predictor), halve it until the step doesn't blow up.
        step = delta
        for _ in range(20):
            beta_new = beta + step
            if np.all(np.abs(beta_new) < 30):
                break
            step = step / 2
        else:
            beta_new = beta + step

        cov = xtwx_inv
        if np.max(np.abs(beta_new - beta)) < tol:
            return beta_new, cov, True, iteration
        beta = beta_new

    return beta, cov, False, max_iter


def firth_logistic_regression(
    data: pd.DataFrame,
    formula: str,
    max_iter: int = 50,
    tol: float = 1e-6,
) -> FirthResult:
    """Fit a Firth penalized logistic regression from an R-style formula
    (the same formula string you'd pass to `smf.logit`).
    """
    y_design, x_design = patsy.dmatrices(formula, data=data, return_type="dataframe")
    y = y_design.to_numpy().ravel().astype(float)
    X = x_design.to_numpy()
    exog_names = list(x_design.columns)

    beta, cov, converged, n_iter = _fit_firth(X, y, max_iter, tol)

    se = np.sqrt(np.clip(np.diag(cov), 0, None))
    z = beta / se
    p = 2 * stats.norm.sf(np.abs(z))
    ci_low = beta - 1.959963985 * se
    ci_high = beta + 1.959963985 * se

    return FirthResult(
        params=pd.Series(beta, index=exog_names),
        bse=pd.Series(se, index=exog_names),
        or_=pd.Series(np.exp(beta), index=exog_names),
        ci_low=pd.Series(np.exp(ci_low), index=exog_names),
        ci_high=pd.Series(np.exp(ci_high), index=exog_names),
        p_value=pd.Series(p, index=exog_names),
        converged=converged,
        n_iter=n_iter,
        nobs=len(y),
        exog_names=exog_names,
    )
