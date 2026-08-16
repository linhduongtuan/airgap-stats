# DR Stage D2: Descriptive analysis  (example-survey-sem, SEM track)
# Requires: pandas, scipy. Run from the project folder.
#
# Group-comparison tests (Phase 1 of the statistical-methods roadmap): each
# variable's test is chosen at runtime by tools.diagnostics.group_tests --
# see plans/sap.md Section G. work_mode has 3 levels, so the continuous
# branch is one-way ANOVA / Kruskal-Wallis here, not a two-sample test.
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

group_var        = "work_mode"
continuous_vars   = ["age", "income", "work_hours", "tenure_years"]
categorical_vars  = ["gender", "education", "turnover_intent"]

all_vars = [group_var] + continuous_vars + categorical_vars
missing_cols = [v for v in all_vars if v not in dat.columns]
if missing_cols:
    raise ValueError(f"Missing columns: {', '.join(missing_cols)}")

groups = sorted(dat[group_var].dropna().unique())


def summ_cont(x: pd.Series) -> str:
    x = x.dropna()
    return f"{x.mean():.1f} ({x.std():.1f})"


def summ_cat_level(x: pd.Series, lvl) -> str:
    x = x.dropna()
    n = int((x == lvl).sum())
    pct = 100 * n / len(x) if len(x) > 0 else 0.0
    return f"{n} ({pct:.1f}%)"


rows: list[dict[str, object]] = []
test_log: list[str] = []


def add_row(char: str, level: str, overall: str, per_group: list[str], test: str = "", p_value=None) -> None:
    row: dict[str, object] = {
        "characteristic": char, "level": level, "Overall": overall, "test": test, "p_value": p_value,
    }
    for g, val in zip(groups, per_group):
        row[f"{group_var}={g}"] = val
    rows.append(row)


for v in continuous_vars:
    per_group = [summ_cont(dat.loc[dat[group_var] == g, v]) for g in groups]
    result = compare_continuous(dat, v, group_var)
    test_log.append(f"{v}: {result.branch_reason}")
    add_row(v, "mean (SD)", summ_cont(dat[v]), per_group, result.test_used, result.p_value)

for v in categorical_vars:
    result = compare_categorical(dat, v, group_var)
    test_log.append(f"{v}: {result.branch_reason}")
    first = True
    for lvl in sorted(dat[v].dropna().unique()):
        per_group = [summ_cat_level(dat.loc[dat[group_var] == g, v], lvl) for g in groups]
        add_row(
            v, str(lvl), summ_cat_level(dat[v], lvl), per_group,
            result.test_used if first else "", result.p_value if first else None,
        )
        first = False

table1 = pd.DataFrame(rows)
os.makedirs(output_dir, exist_ok=True)
out_path = os.path.join(output_dir, "table1.csv")
table1.to_csv(out_path, index=False, encoding="utf-8")
print(f"N = {len(dat)} | Table 1 written to {out_path}\n")
print(table1.to_string(index=False))

print(f"\nGroup comparison tests (auto-selected at runtime, by {group_var}):")
for line in test_log:
    print(f"  - {line}")
print(
    "\nNOTE: p-values on this synthetic dataset are meaningless by design "
    "(columns are simulated independently). Only the branch selection logic "
    "is being verified here."
)
