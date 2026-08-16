"""Self-contained smoke tests for tools.medical_track -- no pytest required.

Run with:  .venv/bin/python tests/test_medical_track.py

The Firth tests bake in a cross-validation against R's `logistf` (the
canonical reference implementation) done during development -- see the
hardcoded expected values below and tools/medical_track/firth_logistic.py's
module docstring for how they were obtained.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.medical_track import (
    benjamini_hochberg,
    cox_ph,
    e_value,
    firth_logistic_regression,
    iptw_weights,
    kaplan_meier,
    log_transform_if_skewed,
    propensity_scores,
    psm_match,
    restricted_cubic_spline_basis,
)

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
# firth_logistic.py -- cross-validated against R's logistf
# ---------------------------------------------------------------------------

# Well-behaved data (see firth_logistic.py docstring for how this was
# cross-validated). R logistf gives: Intercept=0.1054584, x1=0.9989356,
# x2=-0.2230824.
_rng42 = np.random.default_rng(42)
_n = 60
_x1 = _rng42.normal(0, 1, _n)
_x2 = _rng42.normal(0, 1, _n)
_logit = 0.8 * _x1 - 0.5 * _x2
_p = 1 / (1 + np.exp(-_logit))
_y = (_rng42.uniform(size=_n) < _p).astype(int)
_normal_df = pd.DataFrame({"y": _y, "x1": _x1, "x2": _x2})

firth_normal = firth_logistic_regression(_normal_df, "y ~ x1 + x2")
check("firth: converges on well-behaved data", firth_normal.converged)
check("firth: intercept matches R logistf to 3dp", abs(firth_normal.params["Intercept"] - 0.1054584) < 1e-3)
check("firth: x1 matches R logistf to 3dp", abs(firth_normal.params["x1"] - 0.9989356) < 1e-3)
check("firth: x2 matches R logistf to 3dp", abs(firth_normal.params["x2"] - (-0.2230824)) < 1e-3)

# Deliberately separated data -- the actual reason Firth exists. Plain MLE's
# x1 coefficient blows up (~4.74, SE ~4.28, identical in R glm() and
# statsmodels); Firth pulls it to a stable, finite value. R logistf gives
# x1 = 2.1492432 on this exact dataset.
_x1_sep = np.concatenate([np.random.default_rng(7).normal(-2, 0.5, 18),
                          np.random.default_rng(7).normal(2, 0.5, 20)[::-1]])
# Reconstruct exactly as in the cross-validation session:
_rng7 = np.random.default_rng(7)
_x1_sep = np.concatenate([_rng7.normal(-2, 0.5, 18), _rng7.normal(2, 0.5, 20), [0.0, 0.1]])
_y_sep = np.concatenate([np.zeros(18, dtype=int), np.ones(20, dtype=int), [1, 0]])
_sep_df = pd.DataFrame({"y": _y_sep, "x1": _x1_sep})

firth_sep = firth_logistic_regression(_sep_df, "y ~ x1")
check("firth: converges on separated data", firth_sep.converged)
check("firth: separated-data x1 matches R logistf to 3dp", abs(firth_sep.params["x1"] - 2.1492432) < 1e-3)
check("firth: separated-data x1 is finite and far from the MLE's blown-up ~4.74",
      firth_sep.params["x1"] < 3.0)

# ---------------------------------------------------------------------------
# nonlinearity.py
# ---------------------------------------------------------------------------

skewed = pd.Series(rng.exponential(2, 300), name="crp")
decision = log_transform_if_skewed(skewed)
check("nonlinearity: exponential (skewed) variable -> log_transform", decision.action == "log_transform")

symmetric = pd.Series(rng.normal(10, 2, 300), name="age")
decision2 = log_transform_if_skewed(symmetric)
check("nonlinearity: normal (symmetric) variable -> keep_linear", decision2.action == "keep_linear")

negative_var = pd.Series(rng.normal(0, 1, 100), name="z")  # crosses zero
decision3 = log_transform_if_skewed(negative_var)
check("nonlinearity: variable with non-positive values -> not_applicable", decision3.action == "not_applicable")

spline_x = rng.uniform(0, 100, 200)
basis = restricted_cubic_spline_basis(spline_x, n_knots=4)
check("nonlinearity: RCS basis has n_knots-2 columns", basis.shape[1] == 2)
check("nonlinearity: RCS basis has one row per input", basis.shape[0] == 200)
check("nonlinearity: RCS basis has no NaNs", not basis.isna().any().any())

# ---------------------------------------------------------------------------
# multiplicity.py
# ---------------------------------------------------------------------------

# Known worked example: p-values where only the smallest few survive BH at 0.05.
p_series = pd.Series([0.001, 0.008, 0.039, 0.041, 0.042, 0.06, 0.074, 0.205, 0.212, 0.6])
bh = benjamini_hochberg(p_series, alpha=0.05)
check("multiplicity: smallest p-value always rejected if any is", bool(bh["reject"].iloc[0]))
check("multiplicity: p_adjusted is monotonically non-decreasing with rank",
      (bh.sort_values("p_value")["p_adjusted"].diff().dropna() >= -1e-9).all())
check("multiplicity: largest p-value (0.6) is not rejected", not bool(bh["reject"].iloc[-1]))

p_with_nan = pd.Series([0.01, np.nan, 0.5])
bh_nan = benjamini_hochberg(p_with_nan)
check("multiplicity: NaN p-value stays NaN/not-rejected", pd.isna(bh_nan["p_adjusted"].iloc[1]) and not bh_nan["reject"].iloc[1])

# ---------------------------------------------------------------------------
# survival.py
# ---------------------------------------------------------------------------

n_surv = 150
group = rng.choice(["A", "B"], size=n_surv)
# Group B has a real, strong hazard increase -> should show up in the log-rank test.
base_time = rng.exponential(10, n_surv)
time = np.where(group == "B", base_time * 0.4, base_time)
event = rng.integers(0, 2, n_surv)
surv_df = pd.DataFrame({"time": time, "event": event, "group": group})

km = kaplan_meier(surv_df, "time", "event", group_col="group")
check("survival: KM produces one curve per group", km.n_groups == 2 and len(km.curves) == 2)
check("survival: KM survival probabilities are monotone non-increasing",
      all((c["Surv prob"].diff().dropna() <= 1e-9).all() for c in km.curves.values()))
check("survival: log-rank test detects the real group difference (p < 0.05)",
      km.logrank_p is not None and km.logrank_p < 0.05)

cox_df = pd.DataFrame({
    "time": rng.exponential(10, 200) * np.exp(-0.5 * (x := rng.normal(0, 1, 200))),
    "event": rng.integers(0, 2, 200),
    "x": x,
})
cox_res = cox_ph(cox_df, "x", "time", "event")
check("survival: Cox PH returns one row for the covariate", len(cox_res.table) == 1)
# time = T0 * exp(-0.5*x) means x shortens survival time -> increases hazard.
# For an exponential baseline this AFT form is exactly HR = exp(0.5) ~= 1.65
# on the PH scale; Cox PH should recover HR > 1 (harmful), close to that.
check("survival: Cox PH recovers the correct direction of effect (HR > 1, hazard-increasing)",
      cox_res.table["hr"].iloc[0] > 1)
check("survival: Cox PH's HR is in the right ballpark of the true exp(0.5)~=1.65",
      1.2 < cox_res.table["hr"].iloc[0] < 2.2)

# ---------------------------------------------------------------------------
# propensity.py
# ---------------------------------------------------------------------------

n_ps = 300
covar = rng.normal(0, 1, n_ps)
treat_p = 1 / (1 + np.exp(-(0.7 * covar)))
treatment = (rng.uniform(size=n_ps) < treat_p).astype(int)
ps_df = pd.DataFrame({"treat": treatment, "covar": covar})

ps = propensity_scores(ps_df, "treat", "covar")
check("propensity: propensity scores are valid probabilities", ((ps > 0) & (ps < 1)).all())
check("propensity: higher covar (predicts treatment) -> higher PS on average",
      ps[ps_df["treat"] == 1].mean() > ps[ps_df["treat"] == 0].mean())

match = psm_match(ps_df, "treat", ps)
check("propensity: psm_match returns at most n_treated pairs", match.n_matched <= match.n_treated)
check("propensity: all matched distances are within the caliper",
      match.pairs.empty or (match.pairs["distance"] <= match.caliper + 1e-9).all())

w = iptw_weights(ps_df["treat"], ps)
check("propensity: IPTW weights are all positive", (w > 0).all())
check("propensity: stabilized IPTW mean weight is close to 1", abs(w.mean() - 1) < 0.3)

# E-value: known worked example from VanderWeele & Ding (2017) -- RR=2 (rare
# outcome / already RR-scale) gives E-value = 2 + sqrt(2*1) = 3.414.
ev = e_value(2.0, measure="RR")
check("e_value: RR=2 gives E-value 3.414 (VanderWeele & Ding worked example)",
      abs(ev["e_value_point"] - 3.4142) < 1e-3)

ev_or = e_value(4.0, ci_bound=1.5, measure="OR", rare_outcome=False)
check("e_value: OR converted via sqrt before the E-value formula", abs(ev_or["rr_scale_estimate"] - 2.0) < 1e-9)
check("e_value: CI-bound E-value <= point E-value (CI bound is closer to null)",
      ev_or["e_value_ci"] <= ev_or["e_value_point"])

ev_crosses = e_value(2.0, ci_bound=0.8, measure="RR")
check("e_value: CI crossing the null gives E-value 1.0 for the CI bound", ev_crosses["e_value_ci"] == 1.0)

# ---------------------------------------------------------------------------
print(f"\n{_passed} passed, {len(_failed)} failed")
if _failed:
    print("Failed checks:")
    for name in _failed:
        print(f"  - {name}")
    sys.exit(1)
print("ALL TESTS PASSED")
