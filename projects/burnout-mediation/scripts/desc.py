# DR Stage D2: Descriptive analysis / Table 1
# Requires: pandas, scipy. Run from the project folder.
#
# Group-comparison tests (Phase 1 of the statistical-methods roadmap): each
# variable's test is chosen at runtime by tools.diagnostics.group_tests --
# see plans/sap.md Section G. compare_continuous also covers the ordinal
# (Likert) variable here: it branches on Shapiro-Wilk, and a bounded
# discrete Likert item almost always fails normality, correctly routing to
# Mann-Whitney U -- the standard test for ordinal data anyway.
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

# --- Variables ---
group_var        = "turnover_intent"
continuous_vars   = ["age", "tenure_years", "job_satisfaction", "burnout_score"]
categorical_vars  = ["gender", "education"]
ordinal_vars      = ["wlb", "js_q1", "js_q2", "js_q3", "js_q4", "js_q5",
                      "bo_q1", "bo_q2", "bo_q3", "bo_q4", "bo_q5"]

all_vars = continuous_vars + categorical_vars + ordinal_vars + [group_var]
missing_cols = [v for v in all_vars if v not in dat.columns]
if missing_cols:
    raise ValueError(f"Missing columns in data: {', '.join(missing_cols)}")


# --- Helper: summarize continuous ---
def summ_cont(x: pd.Series) -> str:
    return f"{x.mean():.1f} ({x.std():.1f})"


# --- Helper: summarize ordinal as median (IQR) ---
def summ_ord(x: pd.Series) -> str:
    md = x.median()
    q1 = x.quantile(0.25)
    q3 = x.quantile(0.75)
    return f"{md:.0f} ({q1:.0f}-{q3:.0f})"


# --- Helper: summarize categorical ---
def summ_cat(x: pd.Series) -> pd.DataFrame:
    tab = x.dropna().value_counts()
    return pd.DataFrame({
        "level": tab.index.astype(str),
        "value": [f"{int(n)} ({100 * n / tab.sum():.1f}%)" for n in tab],
    })


# --- Helper: get group N label ---
def group_N(d: pd.DataFrame, gv: str) -> list[str]:
    tab = d[gv].dropna().value_counts().sort_index()
    return [f"{lev} (N={int(n)})" for lev, n in tab.items()]


# --- Build Table 1 ---
groups       = sorted(dat[group_var].dropna().unique())
overall_N    = len(dat)
group_labels = group_N(dat, group_var)

table1_rows: list[dict[str, object]] = []
test_log: list[str] = []


def add_continuous(v: str, label: str) -> None:
    result = compare_continuous(dat, v, group_var)
    test_log.append(f"{v}: {result.branch_reason}")
    row: dict[str, object] = {
        "characteristic": label, "level": "-", "Overall": summ_cont(dat[v].dropna()),
        "test": result.test_used, "p_value": result.p_value,
    }
    for g in groups:
        row[str(g)] = summ_cont(dat.loc[dat[group_var] == g, v].dropna())
    table1_rows.append(row)


def add_ordinal(v: str, label: str) -> None:
    result = compare_continuous(dat, v, group_var)
    test_log.append(f"{v}: {result.branch_reason}")
    row: dict[str, object] = {
        "characteristic": label, "level": "-", "Overall": summ_ord(dat[v].dropna()),
        "test": result.test_used, "p_value": result.p_value,
    }
    for g in groups:
        row[str(g)] = summ_ord(dat.loc[dat[group_var] == g, v].dropna())
    table1_rows.append(row)


def add_categorical(v: str, label: str) -> None:
    overall_tab = summ_cat(dat[v])
    if overall_tab.empty:
        return
    result = compare_categorical(dat, v, group_var)
    test_log.append(f"{v}: {result.branch_reason}")
    first = True
    for _, r in overall_tab.iterrows():
        lev = r["level"]
        row: dict[str, object] = {
            "characteristic": label if first else "",
            "level": lev,
            "Overall": r["value"],
            "test": result.test_used if first else "",
            "p_value": result.p_value if first else None,
        }
        for g in groups:
            sub = dat.loc[dat[group_var] == g, v]
            sub_tab = summ_cat(sub)
            match = sub_tab.loc[sub_tab["level"] == lev, "value"]
            row[str(g)] = match.iloc[0] if len(match) > 0 else "0 (0.0%)"
        table1_rows.append(row)
        first = False


add_continuous("age", "Age, years")
add_continuous("tenure_years", "Tenure, years")
add_continuous("job_satisfaction", "Job satisfaction score")
add_continuous("burnout_score", "Burnout score")
add_ordinal("wlb", "Work-life balance")
add_categorical("gender", "Gender")
add_categorical("education", "Education")

table1 = pd.DataFrame(
    table1_rows,
    columns=["characteristic", "level", "Overall"] + [str(g) for g in groups] + ["test", "p_value"],
)
table1 = table1.rename(columns={"Overall": f"Overall (N={overall_N})"})
table1 = table1.rename(columns=dict(zip([str(g) for g in groups], group_labels)))

# --- Add footnote ---
footnote = (
    "Continuous variables are presented as mean (SD); "
    "ordinal/Likert variables as median (IQR); "
    "categorical variables as n (%)."
)

# --- Save ---
os.makedirs(output_dir, exist_ok=True)
out_path = os.path.join(output_dir, "table1.csv")
table1.to_csv(out_path, index=False, encoding="utf-8")
print(f"Table 1 written to {out_path}\n")
print(table1.to_string(index=False))
print(f"\n {footnote}")

print(f"\nGroup comparison tests (auto-selected at runtime, by {group_var}):")
for line in test_log:
    print(f"  - {line}")
print(
    "\nNOTE: p-values on this synthetic dataset are meaningless by design "
    "(columns are simulated independently). Only the branch selection logic "
    "is being verified here."
)

# --- Missing summary ---
miss_rows = pd.DataFrame({
    "variable":     all_vars,
    "n_missing":    [int(dat[v].isna().sum()) for v in all_vars],
    "pct_missing":  [round(100 * dat[v].isna().mean(), 1) for v in all_vars],
})
miss_path = os.path.join(output_dir, "missing_summary.csv")
miss_rows.to_csv(miss_path, index=False, encoding="utf-8")
print(f"\nMissing summary written to {miss_path}")
