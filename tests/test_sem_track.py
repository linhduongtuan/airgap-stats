"""Self-contained smoke tests for tools.sem_track -- no pytest required.

Run with:  .venv/bin/python tests/test_sem_track.py

Bootstrap-based tests use a small n_boot (10-15) purely to verify the
mechanics (shape, sensible CI ordering) -- each rep refits a full ordinal
CFA (~1-6s depending on model size), so a statistically well-powered
n_boot=200 run takes minutes, appropriate for a one-off project script
verification but not for a test suite that should run in seconds.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.sem_track import (
    average_variance_extracted,
    bootstrap_mediation,
    build_cfa_syntax,
    composite_reliability,
    compare_nested_models,
    compare_nested_regressions,
    configural_check,
    cronbach_alpha,
    factor_scores,
    fit_measurement_model,
    fit_structural_model,
    htmt,
    mcdonald_omega,
    metric_invariance_bootstrap,
    reliability_from_cfa,
)
from tools.sem_track.compat import _bivariate_cdf_patched, _univariate_cdf_patched

_passed = 0
_failed: list[str] = []


def check(name: str, condition: bool) -> None:
    global _passed
    if condition:
        _passed += 1
    else:
        _failed.append(name)
        print(f"FAIL: {name}")


rng = np.random.default_rng(2026)

# ---------------------------------------------------------------------------
# compat.py -- the two scipy/numpy compatibility patches, verified against
# closed-form results (independent of semopy's own internals).
# ---------------------------------------------------------------------------

p_full_plane = _bivariate_cdf_patched([-np.inf, -np.inf], [np.inf, np.inf], 0.5)
check("compat: bivariate_cdf over the whole plane integrates to 1", abs(p_full_plane - 1.0) < 1e-9)

rho = 0.6
p_orthant = _bivariate_cdf_patched([0, 0], [np.inf, np.inf], rho)
p_orthant_expected = 0.25 + np.arcsin(rho) / (2 * np.pi)  # classic bivariate-normal orthant probability
check("compat: bivariate_cdf orthant probability matches closed form", abs(p_orthant - p_orthant_expected) < 1e-9)

p_uni = _univariate_cdf_patched(-1, 1)
from scipy.stats import norm as _norm
check("compat: univariate_cdf matches norm.cdf difference", abs(p_uni - (_norm.cdf(1) - _norm.cdf(-1))) < 1e-9)
check("compat: univariate_cdf over the whole line integrates to 1", abs(_univariate_cdf_patched(-np.inf, np.inf) - 1.0) < 1e-9)

# ---------------------------------------------------------------------------
# Simulated ordinal data with a genuine single-factor structure, used by
# several tests below.
# ---------------------------------------------------------------------------


def _make_ordinal_items(latent: np.ndarray, loadings: list[float], n: int, noise_sd: float = 0.6) -> dict:
    items = {}
    for i, load in enumerate(loadings):
        cont = load * latent + rng.normal(0, noise_sd, n)
        cuts = np.quantile(cont, [0.15, 0.35, 0.65, 0.85])
        items[f"i{i}"] = np.digitize(cont, cuts) + 1
    return items


n = 300
eta = rng.normal(0, 1, n)
single_factor_items = _make_ordinal_items(eta, [0.8, 0.75, 0.7, 0.85, 0.6], n)
single_df = pd.DataFrame(single_factor_items)

# ---------------------------------------------------------------------------
# estimator.py
# ---------------------------------------------------------------------------

syntax = build_cfa_syntax({"F": list(single_df.columns)})
check("estimator: build_cfa_syntax includes an ordinal declaration", syntax.startswith("ordinal:"))
check("estimator: build_cfa_syntax includes the =~ line", "F =~" in syntax)

cfa_fit = fit_measurement_model(single_df, {"F": list(single_df.columns)}, estimator="DWLS")
check("estimator: DWLS CFA converges on genuine single-factor ordinal data", cfa_fit.converged)
check("estimator: CFI indicates good fit (>0.95) on a correctly-specified model", cfa_fit.fit_indices["cfi"] > 0.95)
check("estimator: RMSEA indicates good fit (<0.08) on a correctly-specified model", cfa_fit.fit_indices["rmsea"] < 0.08)
check("estimator: loadings are all positive (as simulated)", (cfa_fit.loadings["Est. Std"] > 0).all())

scores = factor_scores(cfa_fit, single_df)
check("estimator: factor_scores returns one row per observation", len(scores) == len(single_df))
check("estimator: factor_scores has one column for the construct", "F" in scores.columns)

# ---------------------------------------------------------------------------
# reliability.py
# ---------------------------------------------------------------------------

# Known worked example: 3 perfectly-correlated items -> alpha = 1.
perfect = pd.DataFrame({"a": range(50), "b": range(50), "c": range(50)}).astype(float)
check("cronbach_alpha: perfectly correlated items -> alpha ~= 1.0", abs(cronbach_alpha(perfect) - 1.0) < 1e-6)

# Independent noise items -> alpha should be low (near 0, can dip slightly negative).
noise_items = pd.DataFrame({f"n{i}": rng.normal(0, 1, 300) for i in range(5)})
check("cronbach_alpha: independent noise items -> low alpha", cronbach_alpha(noise_items) < 0.3)

rel = reliability_from_cfa(single_df, "F", list(single_df.columns), cfa_fit.loadings)
check("reliability_from_cfa: alpha is reasonable for a well-behaved 5-item scale", 0.5 < rel.alpha < 1.0)
check("reliability_from_cfa: omega was actually computed (not None)", rel.omega is not None)
check("reliability_from_cfa: omega is close to alpha for roughly-equal loadings", abs(rel.omega - rel.alpha) < 0.15)

# Manual omega worked example: loadings [0.8, 0.8], errors [0.36, 0.36]
# -> omega = (1.6)^2 / (2.56 + 0.72) = 2.56 / 3.28
manual_omega = mcdonald_omega(pd.Series([0.8, 0.8]), pd.Series([0.36, 0.36]))
check("mcdonald_omega: matches hand-worked example", abs(manual_omega - (2.56 / 3.28)) < 1e-9)

# ---------------------------------------------------------------------------
# validity.py
# ---------------------------------------------------------------------------

loadings_08 = pd.Series([0.8, 0.8, 0.8])
check("AVE: loadings of 0.8 -> AVE = 0.64", abs(average_variance_extracted(loadings_08) - 0.64) < 1e-9)
check("AVE: below the 0.5 threshold is detectable", average_variance_extracted(pd.Series([0.5, 0.5, 0.5])) < 0.5)

cr = composite_reliability(loadings_08)
check("composite_reliability: 0.8 loadings give CR > 0.8 (conventional 'good' threshold)", cr > 0.8)

# HTMT: two truly distinct constructs should be well below the 0.85/0.90 thresholds.
m2 = rng.normal(0, 1, n)  # independent of eta
distinct_items = _make_ordinal_items(m2, [0.8, 0.75, 0.7, 0.85, 0.6], n)
distinct_df = pd.DataFrame(distinct_items)
distinct_df.columns = [f"d{i}" for i in range(5)]
combined_df = pd.concat([single_df.reset_index(drop=True), distinct_df.reset_index(drop=True)], axis=1)
htmt_distinct = htmt(combined_df, list(single_df.columns), list(distinct_df.columns))
check("htmt: two independently-generated constructs are well below 0.85", htmt_distinct < 0.85)

# HTMT: a construct compared with a near-duplicate of itself should be high.
near_dup_df = single_df.copy()
near_dup_df.columns = [f"dup{i}" for i in range(5)]
htmt_dup = htmt(pd.concat([single_df, near_dup_df], axis=1), list(single_df.columns), list(near_dup_df.columns))
check("htmt: near-identical item sets give a high HTMT (>0.85)", htmt_dup > 0.85)

# ---------------------------------------------------------------------------
# mediation.py -- two-step bootstrap, small n_boot for test-suite speed
# ---------------------------------------------------------------------------

X = rng.normal(0, 1, n)
M = 0.6 * X + rng.normal(0, 0.8, n)
med_items_x = _make_ordinal_items(X, [0.85, 0.8, 0.75, 0.8], n)
med_items_m = _make_ordinal_items(M, [0.85, 0.8, 0.75, 0.8], n)
med_df = pd.DataFrame({f"x_{k}": v for k, v in med_items_x.items()})
for k, v in med_items_m.items():
    med_df[f"m_{k}"] = v
logit_y = 0.4 * M - 0.3 * X
med_df["y_bin"] = (rng.uniform(size=n) < 1 / (1 + np.exp(-logit_y))).astype(int)

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    med_boot = bootstrap_mediation(
        med_df,
        constructs={"X": [c for c in med_df.columns if c.startswith("x_")],
                    "M": [c for c in med_df.columns if c.startswith("m_")]},
        mediator="M", predictor="X", outcome="y_bin", outcome_is_binary=True,
        n_boot=10, seed=1,
    )
check("bootstrap_mediation: returns all 5 path point estimates", set(med_boot.point) == {"a", "b", "c_prime", "indirect", "total"})
check("bootstrap_mediation: indirect effect equals a*b", abs(med_boot.point["indirect"] - med_boot.point["a"] * med_boot.point["b"]) < 1e-9)
check("bootstrap_mediation: total effect equals c_prime + indirect", abs(med_boot.point["total"] - (med_boot.point["c_prime"] + med_boot.point["indirect"])) < 1e-9)
check("bootstrap_mediation: recovers the correct sign of the a path (X->M positive)", med_boot.point["a"] > 0)
check("bootstrap_mediation: CI bounds are ordered (low <= high) for every path with data",
      all(med_boot.ci_low[k] <= med_boot.ci_high[k] for k in med_boot.point if med_boot.ci_low[k] == med_boot.ci_low[k]))
frame = med_boot.to_frame()
check("bootstrap_mediation: to_frame returns 5 rows", len(frame) == 5)

# ---------------------------------------------------------------------------
# model_comparison.py
# ---------------------------------------------------------------------------

# compare_nested_models on two stable measurement-model fits: a model with
# one extra free item should never fit *worse* (lower/equal chi2, since it
# is strictly less restricted) -- use two CFA fits on subsets of the same
# item pool.
fit_4item = fit_measurement_model(single_df.iloc[:, :4], {"F": list(single_df.columns[:4])}, estimator="DWLS")
fit_5item = fit_measurement_model(single_df, {"F": list(single_df.columns)}, estimator="DWLS")
check("compare_nested_models: both fits converged (precondition for a meaningful comparison)",
      fit_4item.converged and fit_5item.converged)

# compare_nested_regressions: a classic worked LR-test scenario -- a
# predictor with a real effect should be significantly better than dropping it.
import statsmodels.formula.api as smf
lr_df = pd.DataFrame({"y": rng.normal(0, 1, 200)})
lr_df["x1"] = rng.normal(0, 1, 200)
lr_df["y"] = 2.0 * lr_df["x1"] + rng.normal(0, 0.5, 200)  # strong real effect
fit_full = smf.ols("y ~ x1", data=lr_df).fit()
fit_restricted = smf.ols("y ~ 1", data=lr_df).fit()
lr_result = compare_nested_regressions(fit_full, fit_restricted)
check("compare_nested_regressions: detects a strong real predictor (p < 0.001)", lr_result.p_value < 0.001)
check("compare_nested_regressions: prefers the full model when the term matters", lr_result.preferred.startswith("full"))

lr_df["x_noise"] = rng.normal(0, 1, 200)
fit_full_noise = smf.ols("y ~ x1 + x_noise", data=lr_df).fit()
fit_restricted_noise = smf.ols("y ~ x1", data=lr_df).fit()
lr_result_noise = compare_nested_regressions(fit_full_noise, fit_restricted_noise)
check("compare_nested_regressions: does not falsely favor an irrelevant added term", lr_result_noise.p_value > 0.05)

# ---------------------------------------------------------------------------
# invariance.py -- small n_boot (10) for test-suite speed; see the
# interactive validation (n_boot=20, documented in invariance.py's
# module docstring rationale) for the fuller check this was based on.
# ---------------------------------------------------------------------------


def _make_inv_items(eta: np.ndarray, loadings: list[float], noise_sd: float = 0.6) -> dict:
    out = {}
    for i, load in enumerate(loadings):
        cont = load * eta + rng.normal(0, noise_sd, len(eta))
        cuts = np.quantile(cont, [0.15, 0.35, 0.65, 0.85])
        out[f"q{i}"] = np.digitize(cont, cuts) + 1
    return out


n_grp = 200
eta_a = rng.normal(0, 1, n_grp)
eta_b = rng.normal(0, 1, n_grp)

# Invariant scenario: identical loadings in both groups.
same_loadings = [0.8, 0.75, 0.7, 0.85, 0.6]
inv_df = pd.concat([
    pd.DataFrame(_make_inv_items(eta_a, same_loadings)).assign(grp="A"),
    pd.DataFrame(_make_inv_items(eta_b, same_loadings)).assign(grp="B"),
], ignore_index=True)

conf_inv = configural_check(inv_df, {"F": [f"q{i}" for i in range(5)]}, "grp")
check("configural_check: fits both groups", all(f.converged for f in conf_inv.fits.values()))
check("configural_check: good fit (CFI>0.9) in both groups on genuinely single-factor data",
      all(f.fit_indices["cfi"] > 0.9 for f in conf_inv.fits.values()))

metric_inv = metric_invariance_bootstrap(inv_df, {"F": [f"q{i}" for i in range(5)]}, "grp", n_boot=10, seed=1)
check("metric_invariance_bootstrap: returns one row per item", len(metric_inv) == 5)
check("metric_invariance_bootstrap: false-positive rate is low on genuinely invariant data (<=2 of 5 flagged)",
      metric_inv["flagged_noninvariant"].sum() <= 2)

# Non-invariant scenario: one item's loading collapses in group B.
diff_loadings_b = [0.8, 0.75, 0.05, 0.85, 0.6]
noninv_df = pd.concat([
    pd.DataFrame(_make_inv_items(eta_a, same_loadings)).assign(grp="A"),
    pd.DataFrame(_make_inv_items(eta_b, diff_loadings_b)).assign(grp="B"),
], ignore_index=True)

metric_noninv = metric_invariance_bootstrap(noninv_df, {"F": [f"q{i}" for i in range(5)]}, "grp", n_boot=10, seed=1)
check("metric_invariance_bootstrap: detects the deliberately non-invariant item (q2)",
      bool(metric_noninv.loc[metric_noninv["item"] == "q2", "flagged_noninvariant"].iloc[0]))
check("metric_invariance_bootstrap: the flagged item's difference matches the true injected gap (~0.75)",
      abs(metric_noninv.loc[metric_noninv["item"] == "q2", "difference"].iloc[0] - 0.75) < 0.2)

# ---------------------------------------------------------------------------
print(f"\n{_passed} passed, {len(_failed)} failed")
if _failed:
    print("Failed checks:")
    for name in _failed:
        print(f"  - {name}")
    sys.exit(1)
print("ALL TESTS PASSED")
