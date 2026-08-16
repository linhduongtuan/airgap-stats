# DR Stage D2: Descriptive analysis / Table 1
# Requires: pandas, scipy. Run from the project folder.
#
# Group-comparison tests (Phase 1 of the statistical-methods roadmap): each
# variable's test is chosen at runtime by tools.diagnostics.group_tests --
# Shapiro-Wilk decides t-test/ANOVA vs. Mann-Whitney/Kruskal-Wallis for
# continuous variables, and the minimum expected cell count decides
# chi-squared vs. Fisher's exact for categorical ones. Nobody has seen the
# real data's distribution, so this must branch at runtime, never be fixed
# in advance (see plans/sap.md Section G).
#
# SYNTHESIS-MODE CHECK (Phase 4): last verified clean against both Stage B
# (independent synthesis, the default below) and Stage B2 (correlated
# synthesis -- see synthesize_data_correlated.py) as of 2026-08-15. The
# Stage B2 check used a stand-in file (this project's own Stage B output fed
# in as if it were real data, only to exercise the code path) -- re-verify
# against a genuine Stage B2 file once you generate one from real data.

# === USER SETTINGS ==========================================================
input_csv  = "data_synthetic/synthetic_dataset.csv"
output_dir = "outputs_synthetic"
# To run on REAL data, comment the two lines above and uncomment these:
# input_csv  = input("Path to real dataset CSV: ").strip()
# output_dir = "results_real"
# ============================================================================

import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.diagnostics import compare_categorical, compare_continuous

dat = pd.read_csv(input_csv, encoding="utf-8")

# --- Variables from plans/analysis_plan.yaml ---
group_var        = "mortality_30day"
continuous_vars   = ["age", "bmi", "sbp", "egfr", "hba1c", "crp"]
categorical_vars  = ["sex", "treatment", "diabetes", "hypertension", "smoking", "complication"]

missing_cols = [v for v in continuous_vars + categorical_vars + [group_var] if v not in dat.columns]
if missing_cols:
    raise ValueError(f"Missing columns in data: {', '.join(missing_cols)}")


def summ_cont(x: pd.Series) -> str:
    x = x.dropna()
    return f"{x.mean():.1f} ({x.std():.1f})" if len(x) > 0 else "NA"


# --- Build Table 1 ---
group_vals   = sorted(dat[group_var].dropna().unique())
group_labels = [f"Group_{v}" for v in group_vals]
group_map    = dict(zip(group_labels, group_vals))   # label -> actual value

rows: list[dict[str, object]] = []
test_log: list[str] = []

# --- N per group ---
n_row: dict[str, object] = {"characteristic": "N", "level": "-", "Overall": len(dat), "test": "-", "p_value": None}
for glab, gval in group_map.items():
    n_row[glab] = int((dat[group_var] == gval).sum())
rows.append(n_row)

# --- Continuous variables ---
for var in continuous_vars:
    result = compare_continuous(dat, var, group_var)
    test_log.append(f"{var}: {result.branch_reason}")
    row: dict[str, object] = {
        "characteristic": var, "level": "-", "Overall": summ_cont(dat[var]),
        "test": result.test_used, "p_value": result.p_value,
    }
    for glab, gval in group_map.items():
        row[glab] = summ_cont(dat.loc[dat[group_var] == gval, var])
    rows.append(row)

# --- Categorical variables ---
for var in categorical_vars:
    result = compare_categorical(dat, var, group_var)
    test_log.append(f"{var}: {result.branch_reason}")
    first = True
    for lev in sorted(dat[var].dropna().unique()):
        n_total = int((dat[var] == lev).sum())
        total_n = int(dat[var].notna().sum())
        row = {
            "characteristic": var,
            "level": str(lev),
            "Overall": f"{n_total} ({100 * n_total / max(total_n, 1):.1f}%)",
            "test": result.test_used if first else "",
            "p_value": result.p_value if first else None,
        }
        first = False
        for glab, gval in group_map.items():
            grp     = dat.loc[dat[group_var] == gval, var]
            n_grp   = int((grp == lev).sum())
            grp_tot = int(grp.notna().sum())
            row[glab] = f"{n_grp} ({100 * n_grp / max(grp_tot, 1):.1f}%)"
        rows.append(row)

table1 = pd.DataFrame(rows, columns=["characteristic", "level", "Overall"] + group_labels + ["test", "p_value"])

# --- Save outputs ---
os.makedirs(output_dir, exist_ok=True)
out_path = os.path.join(output_dir, "table1.csv")
table1.to_csv(out_path, index=False, encoding="utf-8")
print(f"Table 1 written to {out_path}")
print(table1.to_string(index=False))

print(f"\nGroup comparison tests (auto-selected at runtime, by {group_var}):")
for line in test_log:
    print(f"  - {line}")
print(
    "\nNOTE: p-values on this synthetic dataset are meaningless by design "
    "(columns are simulated independently). Only the branch selection logic "
    "is being verified here."
)
