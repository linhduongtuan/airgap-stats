"""Compatibility shims for semopy 2.3.11 (the latest release on PyPI as of
this writing) against numpy>=2.0 and current scipy. Both are real, confirmed
upstream bugs in semopy's ordinal/polychoric-correlation code path, not
issues with this repo's code -- semopy hasn't been updated to match numpy's
2.0 API cleanup or scipy's removal of the legacy `scipy.stats.mvn` module.

Import this module (or anything from `tools.sem_track`, which imports it)
before fitting any ordinal/DWLS/WLS model. Continuous ML fits never hit
either code path and work fine unpatched.

Patch 1 -- semopy.utils.cor / semopy.polycorr.cor:
    Called `np.ma.corrcoef(masked_x, bias=True, rowvar=False)`. `bias` was a
    no-op in numpy for over a decade before being removed entirely in numpy
    2.0 (it never changed corrcoef's output -- corrcoef has always been
    correlation, not covariance, regardless of that flag). Dropping the
    dead kwarg is a behavior-preserving fix, not a workaround.

Patch 2 -- semopy.polycorr.bivariate_cdf (polychoric correlations, ordinal-ordinal):
    Called the deprecated-and-removed `scipy.stats.mvn.mvnun`. Replaced
    with the modern `scipy.stats.multivariate_normal.cdf` via the standard
    rectangle-probability inclusion-exclusion identity:
        P(l0<X<u0, l1<Y<u1) = F(u0,u1) - F(l0,u1) - F(u0,l1) + F(l0,l1)
    Verified against closed-form results before use (independent-box
    probability, and the bivariate-normal orthant probability
    1/4 + arcsin(rho)/(2*pi)) -- see tests/test_sem_track.py.

Patch 3 -- semopy.polycorr.univariate_cdf (polyserial correlations,
continuous-ordinal -- hit whenever a model mixes ordinal items with a
continuous/binary-but-undeclared variable, e.g. a distal outcome):
    Same underlying `mvn.mvnun` call, 1-D case. Replaced with
    `scipy.stats.norm.cdf`, handling +-inf bounds explicitly. Verified
    against closed-form: P(-1<Z<1) matches norm.cdf(1)-norm.cdf(-1), and
    integrating the whole real line gives 1.0.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import multivariate_normal, norm

import semopy.polycorr as _polycorr
import semopy.utils as _utils


def _cor_patched(x: np.ndarray) -> np.ndarray:
    masked_x = np.ma.array(x, mask=np.isnan(x))
    cor = np.ma.corrcoef(masked_x, rowvar=False).data
    if cor.size == 1:
        cor.resize((1, 1))
    return cor


def _bivariate_cdf_patched(lower, upper, corr, means=(0, 0), var=(1, 1)) -> float:
    cov = np.array([[var[0], corr], [corr, var[1]]])
    mvn = multivariate_normal(mean=means, cov=cov)

    def F(pt):
        if np.isneginf(pt[0]) or np.isneginf(pt[1]):
            return 0.0
        return float(mvn.cdf(pt))

    return F(upper) - F([lower[0], upper[1]]) - F([upper[0], lower[1]]) + F(lower)


def _univariate_cdf_patched(lower, upper, mean=0, var=1) -> float:
    sd = np.sqrt(var)
    lo = 0.0 if np.isneginf(lower) else float(norm.cdf(lower, mean, sd))
    hi = 1.0 if np.isposinf(upper) else float(norm.cdf(upper, mean, sd))
    return hi - lo


def apply() -> None:
    """Idempotent -- safe to call multiple times or from multiple modules."""
    _utils.cor = _cor_patched
    _polycorr.cor = _cor_patched
    _polycorr.bivariate_cdf = _bivariate_cdf_patched
    _polycorr.univariate_cdf = _univariate_cdf_patched


apply()
