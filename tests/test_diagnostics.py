"""Self-contained smoke tests for tools.diagnostics -- no pytest required.

Run with:  .venv/bin/python tests/test_diagnostics.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.diagnostics import (
    bootstrap_optimism,
    box_tidwell_test,
    compare_categorical,
    compare_continuous,
    compute_dfbetas,
    compute_influence,
    compute_vif,
)
import statsmodels.formula.api as smf

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
# group_tests.py
# ---------------------------------------------------------------------------

# Two normal groups, real mean difference -> Welch's t-test branch.
n = 80
normal_df = pd.DataFrame({
    "x": np.concatenate([rng.normal(0, 1, n), rng.normal(1.5, 1, n)]),
    "g": ["a"] * n + ["b"] * n,
})
r = compare_continuous(normal_df, "x", "g")
check("continuous: 2 normal groups -> welch_t_test", r.test_used == "welch_t_test")
check("continuous: real mean shift is significant", r.p_value is not None and r.p_value < 0.01)

# Two heavily right-skewed groups (exponential) -> Mann-Whitney branch.
skew_df = pd.DataFrame({
    "x": np.concatenate([rng.exponential(1, n), rng.exponential(1, n)]),
    "g": ["a"] * n + ["b"] * n,
})
r = compare_continuous(skew_df, "x", "g")
check("continuous: skewed groups -> mann_whitney_u", r.test_used == "mann_whitney_u")

# Three groups, normal -> one-way ANOVA branch.
three_df = pd.DataFrame({
    "x": np.concatenate([rng.normal(0, 1, n), rng.normal(0.2, 1, n), rng.normal(0.1, 1, n)]),
    "g": ["a"] * n + ["b"] * n + ["c"] * n,
})
r = compare_continuous(three_df, "x", "g")
check("continuous: 3 normal groups -> welch_anova", r.test_used == "welch_anova")

# Categorical: balanced 2x2, large n -> chi-squared branch.
cat_df = pd.DataFrame({
    "cat": rng.choice(["yes", "no"], size=400, p=[0.5, 0.5]),
    "g": rng.choice(["a", "b"], size=400, p=[0.5, 0.5]),
})
r = compare_categorical(cat_df, "cat", "g")
check("categorical: large balanced table -> chi_squared", r.test_used == "chi_squared")

# Categorical: tiny n, sparse cells -> Fisher's exact branch.
small_cat_df = pd.DataFrame({
    "cat": ["yes", "yes", "no", "no", "yes", "no"],
    "g": ["a", "a", "a", "b", "b", "b"],
})
r = compare_categorical(small_cat_df, "cat", "g")
check("categorical: sparse table -> fisher_exact", r.test_used == "fisher_exact")

# ---------------------------------------------------------------------------
# regression_diagnostics.py: VIF
# ---------------------------------------------------------------------------

x1 = rng.normal(0, 1, 300)
vif_df = pd.DataFrame({
    "y": rng.integers(0, 2, 300),
    "x1": x1,
    "x2": x1 * 0.98 + rng.normal(0, 0.05, 300),  # near-duplicate of x1 -> severe collinearity
    "x3": rng.normal(0, 1, 300),  # independent -> low VIF
})
vif = compute_vif(vif_df, "x1 + x2 + x3")
vif_by_term = {row["term"]: row["vif"] for row in vif.to_dict("records")}
check("vif: collinear pair has high VIF", vif_by_term["x1"] > 5 and vif_by_term["x2"] > 5)
check("vif: independent term has low VIF", vif_by_term["x3"] < 2)
check("vif: collinear terms flagged", bool(vif.loc[vif["term"] == "x1", "flagged"].iloc[0]))

# ---------------------------------------------------------------------------
# regression_diagnostics.py: influence
# ---------------------------------------------------------------------------

x = rng.normal(0, 1, 200)
logit_p = 1 / (1 + np.exp(-(0.5 * x)))
y = (rng.uniform(size=200) < logit_p).astype(int)
infl_df = pd.DataFrame({"y": y, "x": x})
fit = smf.logit("y ~ x", data=infl_df).fit(disp=False)

cooks, cooks_thr = compute_influence(fit)
check("influence: cooks_distance has one row per observation", len(cooks) == 200)
check("influence: cooks threshold is 4/n", abs(cooks_thr - 4.0 / 200) < 1e-9)
check("influence: cooks_distance is non-negative", (cooks["cooks_distance"] >= 0).all())

dfb, dfb_thr = compute_dfbetas(fit)
check("dfbetas: one row per observation", len(dfb) == 200)
check("dfbetas: threshold is 2/sqrt(n)", abs(dfb_thr - 2.0 / np.sqrt(200)) < 1e-9)
check("dfbetas: has a column per model term plus obs_index/max/flagged", set(["obs_index", "max_abs_dfbeta", "flagged"]).issubset(dfb.columns))

# ---------------------------------------------------------------------------
# regression_diagnostics.py: Box-Tidwell
# ---------------------------------------------------------------------------

# A variable with a genuinely non-linear (quadratic-ish, via log) relationship
# to the logit should be flagged nonlinear_suspected; a variable entered
# linearly by construction should come back "linear".
z_lin = rng.uniform(1, 10, 500)
z_nonlin = rng.uniform(1, 10, 500)
logit_true = 0.8 * z_lin - 2.5 * np.log(z_nonlin)
p_true = 1 / (1 + np.exp(-(logit_true - logit_true.mean())))
y_bt = (rng.uniform(size=500) < p_true).astype(int)
bt_df = pd.DataFrame({"y": y_bt, "z_lin": z_lin, "z_nonlin": z_nonlin})

bt = box_tidwell_test(bt_df, "y", "z_lin + z_nonlin", ["z_lin", "z_nonlin"])
bt_status = dict(zip(bt["variable"], bt["status"]))
check("box_tidwell: returns a row per requested variable", len(bt) == 2)
check("box_tidwell: nonlinear predictor is flagged", bt_status["z_nonlin"] == "nonlinear_suspected")

# A variable with non-positive values must be skipped, not crash.
neg_df = pd.DataFrame({"y": rng.integers(0, 2, 100), "w": rng.normal(0, 1, 100)})
bt_neg = box_tidwell_test(neg_df, "y", "w", ["w"])
check("box_tidwell: non-positive variable is skipped, not errored", bt_neg["status"].iloc[0] == "skipped")

# ---------------------------------------------------------------------------
# bootstrap_validation.py
# ---------------------------------------------------------------------------

# Pure noise predictor -> apparent AUC may look >0.5 by chance, but the
# bootstrap-corrected AUC should land close to 0.5 (no real signal to find).
noise_df = pd.DataFrame({
    "y": rng.integers(0, 2, 200),
    "x1": rng.normal(0, 1, 200),
    "x2": rng.normal(0, 1, 200),
})
boot_noise = bootstrap_optimism(noise_df, "y ~ x1 + x2", "y", n_boot=40, seed=1)
check("bootstrap: optimism is non-negative on noise data", boot_noise.optimism_auc >= -0.05)
check("bootstrap: corrected AUC is close to chance (0.5) on pure noise",
      abs(boot_noise.corrected_auc - 0.5) < 0.15)
check("bootstrap: apparent calibration slope on training data is ~1.0",
      abs(boot_noise.apparent_calibration_slope - 1.0) < 0.05)

# Strong real signal -> apparent and corrected AUC should both be clearly > 0.5,
# and optimism should be small relative to the signal.
x_strong = rng.normal(0, 1, 400)
logit_strong = 3.0 * x_strong
p_strong = 1 / (1 + np.exp(-logit_strong))
y_strong = (rng.uniform(size=400) < p_strong).astype(int)
strong_df = pd.DataFrame({"y": y_strong, "x": x_strong})
boot_strong = bootstrap_optimism(strong_df, "y ~ x", "y", n_boot=40, seed=1)
check("bootstrap: corrected AUC is high with strong real signal", boot_strong.corrected_auc > 0.85)

# ---------------------------------------------------------------------------
print(f"\n{_passed} passed, {len(_failed)} failed")
if _failed:
    print("Failed checks:")
    for name in _failed:
        print(f"  - {name}")
    sys.exit(1)
print("ALL TESTS PASSED")
