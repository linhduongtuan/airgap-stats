# DR Stage D2: Descriptive analysis / Table 1
# Requires: pandas, scipy. Run from the project folder.
#
# Group-comparison tests (Phase 1 of the statistical-methods roadmap): when a
# `group_var` is set, each variable's test is chosen at runtime by
# tools.diagnostics.group_tests -- Shapiro-Wilk decides t-test/ANOVA vs.
# Mann-Whitney/Kruskal-Wallis for continuous variables, and the minimum
# expected cell count decides chi-squared vs. Fisher's exact for categorical
# ones. Nobody has seen the real data's distribution when this script is
# generated, so the branch must be chosen at runtime, never fixed in advance
# (see plans/sap.md Section G). With `group_var = None` (the default) this
# script still runs standalone -- it just skips the comparison tests and
# reports an ungrouped Table 1, same as before this phase.

from __future__ import annotations
import os
import sys
from pathlib import Path

import pandas as pd

# === USER SETTINGS ==========================================================
# Runs on the synthetic dataset as delivered:
input_csv  = "data_synthetic/synthetic_dataset.csv"
output_dir = "outputs_synthetic"
# To run on REAL data, comment the two lines above and uncomment these:
# input_csv  = input("Path to real dataset CSV: ").strip()
# output_dir = "results_real"

# Variables — set explicitly or leave None to auto-detect
group_var        = None    # grouping column; None = Overall only, no tests
continuous_vars  = None    # None = auto-detect numeric columns
categorical_vars = None    # None = auto-detect object/categorical columns
# ============================================================================

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.diagnostics import compare_categorical, compare_continuous


def _summ_cont(series: pd.Series) -> str:  # type: ignore[type-arg]
    s = series.dropna()
    return f"{s.mean():.1f} ({s.std():.1f})" if len(s) > 0 else "NA"


def _build_rows(
    dat: pd.DataFrame,
    continuous_vars: list[str],
    categorical_vars: list[str],
    group_var: str | None,
    group_map: dict[str, object],
) -> tuple[list[dict[str, object]], list[str]]:
    run_tests = group_var is not None
    rows: list[dict[str, object]] = []
    test_log: list[str] = []

    n_row: dict[str, object] = {"characteristic": "N", "level": "-", "Overall": len(dat)}
    if run_tests:
        n_row["test"], n_row["p_value"] = "-", None
    for glab, gval in group_map.items():
        n_row[glab] = int((dat[group_var] == gval).sum())  # type: ignore[index]
    rows.append(n_row)

    for var in continuous_vars:
        row: dict[str, object] = {"characteristic": var, "level": "-", "Overall": _summ_cont(dat[var])}
        if run_tests:
            result = compare_continuous(dat, var, group_var)  # type: ignore[arg-type]
            test_log.append(f"{var}: {result.branch_reason}")
            row["test"], row["p_value"] = result.test_used, result.p_value
        for glab, gval in group_map.items():
            row[glab] = _summ_cont(dat.loc[dat[group_var] == gval, var])  # type: ignore[index]
        rows.append(row)

    for var in categorical_vars:
        if run_tests:
            result = compare_categorical(dat, var, group_var)  # type: ignore[arg-type]
            test_log.append(f"{var}: {result.branch_reason}")
        first = True
        for lev in sorted(dat[var].dropna().unique()):
            n_total = int((dat[var] == lev).sum())
            total_n = int(dat[var].notna().sum())
            cat_row: dict[str, object] = {
                "characteristic": var,
                "level": str(lev),
                "Overall": f"{n_total} ({100 * n_total / max(total_n, 1):.1f}%)",
            }
            if run_tests:
                cat_row["test"] = result.test_used if first else ""
                cat_row["p_value"] = result.p_value if first else None
            first = False
            for glab, gval in group_map.items():
                grp     = dat.loc[dat[group_var] == gval, var]  # type: ignore[index]
                n_grp   = int((grp == lev).sum())
                grp_tot = int(grp.notna().sum())
                cat_row[glab] = f"{n_grp} ({100 * n_grp / max(grp_tot, 1):.1f}%)"
            rows.append(cat_row)
    return rows, test_log


def run(
    input_csv: str,
    output_dir: str,
    group_var: str | None,
    continuous_vars: list[str] | None,
    categorical_vars: list[str] | None,
) -> None:
    dat = pd.read_csv(input_csv, encoding="utf-8")

    if group_var is not None and group_var not in dat.columns:
        raise ValueError(f"group_var '{group_var}' not found in dataset.")

    if continuous_vars is None:
        skip = {group_var} if group_var else set()
        continuous_vars = [
            c for c in dat.select_dtypes(include="number").columns
            if c not in skip and dat[c].dropna().nunique() > 2
        ]
        print(f"Auto-detected continuous: {continuous_vars}")

    if categorical_vars is None:
        skip = {group_var} if group_var else set()
        categorical_vars = [
            c for c in dat.columns
            if c not in skip
            and not pd.api.types.is_numeric_dtype(dat[c])
            and dat[c].dropna().nunique() / max(len(dat[c].dropna()), 1) < 0.9
        ]
        print(f"Auto-detected categorical: {categorical_vars}")

    missing_cols = [
        v for v in continuous_vars + categorical_vars + ([group_var] if group_var else [])
        if v not in dat.columns
    ]
    if missing_cols:
        raise ValueError(f"Missing columns in dataset: {missing_cols}")

    if group_var is not None:
        group_vals   = sorted(dat[group_var].dropna().unique())
        group_labels = [f"Group_{v}" for v in group_vals]
        group_map: dict[str, object] = dict(zip(group_labels, group_vals))
    else:
        group_labels = []
        group_map    = {}

    rows, test_log = _build_rows(dat, continuous_vars, categorical_vars, group_var, group_map)
    cols = ["characteristic", "level", "Overall"] + group_labels
    if group_var is not None:
        cols += ["test", "p_value"]
    table1 = pd.DataFrame(rows, columns=cols)
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "table1.csv")
    table1.to_csv(out_path, index=False, encoding="utf-8")
    print(f"Table 1 written to {out_path}")
    print(table1.to_string(index=False))

    if test_log:
        print(f"\nGroup comparison tests (auto-selected at runtime, by {group_var}):")
        for line in test_log:
            print(f"  - {line}")
        print(
            "\nNOTE: p-values on the delivered synthetic dataset are meaningless by "
            "design (columns are simulated independently). Only the branch-selection "
            "logic is being verified here; interpret p-values only on the real-data run."
        )


run(
    input_csv=input_csv,
    output_dir=output_dir,
    group_var=group_var,
    continuous_vars=continuous_vars,
    categorical_vars=categorical_vars,
)
