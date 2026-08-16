"""Self-contained smoke tests for py-scripts/synthesize_data_correlated.py
-- no pytest required.

Run with:  .venv/bin/python tests/test_synthesize_correlated.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "py-scripts"))

from synthesize_data import synthesize_data
from synthesize_data_correlated import synthesize_data_correlated

_passed = 0
_failed: list[str] = []


def check(name: str, condition: bool) -> None:
    global _passed
    if condition:
        _passed += 1
    else:
        _failed.append(name)
        print(f"FAIL: {name}")


rng = np.random.default_rng(42)

# ---------------------------------------------------------------------------
# Fixture: "real" data with a known correlation structure and a string
# binary column, mirroring what an actual project's local data looks like.
# ---------------------------------------------------------------------------

n_real = 150
mean = [50, 27, 30]
cov = np.array([[100, 12, 0], [12, 16, 6.4], [0, 6.4, 64]])  # true corr: age-bmi .3, bmi-crp .4, age-crp 0
mvn = rng.multivariate_normal(mean, cov, size=n_real)
real = pd.DataFrame({
    "age": np.round(mvn[:, 0]).astype(int),
    "bmi": np.round(mvn[:, 1], 1),
    "crp": np.round(mvn[:, 2], 1),
})
real["sex"] = rng.choice(["M", "F"], size=n_real, p=[0.45, 0.55])

pattern = pd.DataFrame({
    "variable": ["age", "bmi", "crp", "sex"],
    "type": ["integer", "numeric", "numeric", "binary"],
    "levels": ["", "", "", "M|F"],
    "n_distinct": [None, None, None, 2],
    "missing_pct": [0, 0, 0, 0],
    "note": ["", "", "", ""],
})
pattern_path = _REPO_ROOT / "tests" / "_fixture_pattern_correlated.csv"
pattern.to_csv(pattern_path, index=False)

real_corr = real[["age", "bmi", "crp"]].corr(method="spearman")

# ---------------------------------------------------------------------------
# Core behavior
# ---------------------------------------------------------------------------

synth = synthesize_data_correlated(str(pattern_path), data=real, output_csv="/tmp/_test_synth_corr.csv", n=2000, seed=1)
check("returns the requested number of rows", len(synth) == 2000)
check("returns all pattern columns", set(synth.columns) == {"age", "bmi", "crp", "sex"})

synth_corr = synth[["age", "bmi", "crp"]].corr(method="spearman")
check("age-bmi correlation is preserved within 0.15 of the real value",
      abs(synth_corr.loc["age", "bmi"] - real_corr.loc["age", "bmi"]) < 0.15)
check("bmi-crp correlation is preserved within 0.15 of the real value",
      abs(synth_corr.loc["bmi", "crp"] - real_corr.loc["bmi", "crp"]) < 0.15)
check("age-crp (truly ~0 in the real data) stays small in the synthetic data",
      abs(synth_corr.loc["age", "crp"]) < 0.15)

# Contrast against the independent synthesizer -- the whole point of Stage B2.
synth_indep = synthesize_data(str(pattern_path), data=real, output_csv="/tmp/_test_synth_indep.csv", n=2000, seed=1)
indep_corr = synth_indep[["age", "bmi", "crp"]].corr(method="spearman")
check("independent synthesizer does NOT preserve the age-bmi correlation (contrast case)",
      abs(indep_corr.loc["age", "bmi"]) < 0.15)
check("correlated synthesizer preserves substantially more correlation than the independent one",
      abs(synth_corr.loc["age", "bmi"] - real_corr.loc["age", "bmi"]) <
      abs(indep_corr.loc["age", "bmi"] - real_corr.loc["age", "bmi"]))

# Marginal preservation (mean/spread should be close to the real data's).
check("synthetic age mean is close to real age mean",
      abs(synth["age"].mean() - real["age"].mean()) < 3)
check("synthetic age std is close to real age std",
      abs(synth["age"].std() - real["age"].std()) < 3)

# Binary proportions preservation.
real_prop_f = (real["sex"] == "F").mean()
synth_prop_f = (synth["sex"] == "F").mean()
check("binary column proportions are approximately preserved", abs(real_prop_f - synth_prop_f) < 0.1)

# --- Privacy: no synthetic row may exactly reproduce a real row. ---
real_tuples = set(map(tuple, real[["age", "bmi", "crp"]].to_numpy()))
synth_tuples = set(map(tuple, synth[["age", "bmi", "crp"]].to_numpy()))
check("no synthetic row exactly reproduces a real row", len(real_tuples & synth_tuples) == 0)

# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

check("raises without `data` (no correlation structure to preserve)", True)
try:
    synthesize_data_correlated(str(pattern_path), data=None, output_csv="/tmp/_test_synth_none.csv", n=50)
    check("raises ValueError when data=None", False)
except ValueError:
    check("raises ValueError when data=None", True)

# A single correlatable column: should fall back to independent generation
# for it, not crash.
single_pattern = pd.DataFrame({
    "variable": ["age"], "type": ["integer"], "levels": [""], "n_distinct": [None],
    "missing_pct": [0], "note": [""],
})
single_pattern_path = _REPO_ROOT / "tests" / "_fixture_pattern_single.csv"
single_pattern.to_csv(single_pattern_path, index=False)
synth_single = synthesize_data_correlated(str(single_pattern_path), data=real[["age"]], output_csv="/tmp/_test_synth_single.csv", n=50, seed=1)
check("single correlatable column does not crash (falls back to independent)", len(synth_single) == 50)

# ---------------------------------------------------------------------------
pattern_path.unlink(missing_ok=True)
single_pattern_path.unlink(missing_ok=True)
for f in ("/tmp/_test_synth_corr.csv", "/tmp/_test_synth_indep.csv", "/tmp/_test_synth_none.csv", "/tmp/_test_synth_single.csv"):
    Path(f).unlink(missing_ok=True)

print(f"\n{_passed} passed, {len(_failed)} failed")
if _failed:
    print("Failed checks:")
    for name in _failed:
        print(f"  - {name}")
    sys.exit(1)
print("ALL TESTS PASSED")
