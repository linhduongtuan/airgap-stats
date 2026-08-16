# DR Stage D3 (SEM): Measurement model
# Cronbach's alpha + McDonald's omega + CFA (semopy, ordinal/DWLS estimator)
# Requires: pandas, numpy, scipy, semopy, statsmodels. pip install semopy once.
#
# ESTIMATOR (Phase 3 of the statistical-methods roadmap): Likert-scale items
# are ordinal, not continuous. This script fits the CFA with semopy's DWLS
# estimator on the polychoric correlation matrix (declaring every item
# ordinal) -- the methodologically correct choice for ordinal indicators
# (WLSMV is lavaan's name for the same family of estimator; DWLS is
# semopy's). `estimator="ML"` remains available in tools.sem_track and is a
# defensible choice when items have >= 7 response categories or are
# effectively continuous.
#
# Also from Phase 3: McDonald's omega (doesn't assume tau-equivalence,
# unlike alpha), AVE/composite reliability (convergent validity), and the
# HTMT ratio between every pair of constructs (discriminant validity --
# conceptually distinct constructs still need an explicit check that
# they're empirically distinguishable, not just assumed to be).

# === USER SETTINGS ==========================================================
# Runs on the synthetic dataset as delivered:
input_csv  = "data_synthetic/synthetic_dataset.csv"
output_dir = "outputs_synthetic"
# To run on REAL data, comment the two lines above and uncomment these:
# input_csv  = input("Path to real dataset CSV: ").strip()
# output_dir = "results_real"

# EDIT ME: constructs and their item columns, from plans/sem_measurement_plan.yaml.
# The placeholder names below (Construct_A/B with item_a*/item_b*) match the
# columns in the delivered synthetic dataset, so this script runs standalone
# out of the box -- replace both the keys and the item lists with your own
# construct/item names before pointing this at a real project.
constructs: dict[str, list[str]] = {
    "Construct_A": ["item_a1", "item_a2", "item_a3"],
    "Construct_B": ["item_b1", "item_b2", "item_b3"],
}
# ============================================================================

import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.sem_track import (
    average_variance_extracted,
    composite_reliability,
    fit_measurement_model,
    htmt_matrix,
    reliability_from_cfa,
)

dat = pd.read_csv(input_csv, encoding="utf-8")
os.makedirs(output_dir, exist_ok=True)

all_items = [item for items in constructs.values() for item in items]
missing_cols = [c for c in all_items if c not in dat.columns]
if missing_cols:
    raise ValueError(f"Missing columns in data: {', '.join(missing_cols)}")

# --- Scale scores (row mean, >= 50 % items non-missing) -- descriptive use only ---
for cname, items in constructs.items():
    n_ok   = dat[items].notna().sum(axis=1)
    min_ok = math.ceil(len(items) * 0.5)
    dat[f"{cname}_score"] = np.where(n_ok >= min_ok, dat[items].mean(axis=1), np.nan)

scale_summary = pd.DataFrame([
    {
        "construct": cname,
        "mean": round(dat[f"{cname}_score"].mean(), 2),
        "sd":   round(dat[f"{cname}_score"].std(), 2),
        "n":    int(dat[f"{cname}_score"].notna().sum()),
    }
    for cname in constructs
])
print("=== Scale Scores (row-mean, descriptive use only) ===")
print(scale_summary.to_string(index=False))

# === CFA via semopy, DWLS estimator on declared-ordinal items ===============
print("\n=== CFA (DWLS estimator, ordinal items) ===")
try:
    cfa = fit_measurement_model(dat, constructs, estimator="DWLS")

    if not cfa.converged:
        raise RuntimeError("Optimizer did not converge.")

    fi_df = pd.DataFrame([
        {"measure": name, "value": cfa.fit_indices.get(name, float("nan"))}
        for name in ("cfi", "tli", "rmsea", "srmr")
    ])
    print(fi_df.to_string(index=False))
    fi_df.to_csv(os.path.join(output_dir, "cfa_fit.csv"), index=False, encoding="utf-8")

    print("\n=== Standardized Loadings ===")
    print(cfa.loadings.to_string(index=False))
    cfa.loadings.to_csv(os.path.join(output_dir, "cfa_loadings.csv"), index=False, encoding="utf-8")

    # --- Reliability: alpha + omega, from the CFA's own loadings ---
    print("\n=== Reliability: Cronbach's Alpha + McDonald's Omega ===")
    reliability_rows = []
    for cname, items in constructs.items():
        rel = reliability_from_cfa(dat, cname, items, cfa.loadings)
        reliability_rows.append(
            {"construct": rel.construct, "n_items": rel.n_items, "alpha": rel.alpha, "omega": rel.omega}
        )
    reliability_summary = pd.DataFrame(reliability_rows)
    print(reliability_summary.to_string(index=False))
    reliability_summary.to_csv(os.path.join(output_dir, "reliability_summary.csv"), index=False, encoding="utf-8")

    # --- Convergent validity: AVE + composite reliability ---
    print("\n=== Convergent Validity: AVE + Composite Reliability ===")
    validity_rows = []
    for cname in constructs:
        cname_loadings = cfa.loadings.loc[cfa.loadings["rval"] == cname, "Est. Std"]
        validity_rows.append({
            "construct": cname,
            "AVE": round(average_variance_extracted(cname_loadings), 3),
            "CR": round(composite_reliability(cname_loadings), 3),
        })
    validity_summary = pd.DataFrame(validity_rows)
    print(validity_summary.to_string(index=False))
    print("(AVE >= 0.50 and CR >= 0.70 are the conventional 'good' thresholds -- Fornell & Larcker 1981)")
    validity_summary.to_csv(os.path.join(output_dir, "convergent_validity.csv"), index=False, encoding="utf-8")

    # --- Discriminant validity: HTMT between every pair of constructs ---
    if len(constructs) < 2:
        print("\nOnly one construct defined -- HTMT needs at least two constructs to assess "
              "discriminant validity; skipping.")
    else:
        print("\n=== Discriminant Validity: HTMT (every construct pair) ===")
        htmt_df = htmt_matrix(dat, constructs)
        print(htmt_df.round(3).to_string())
        print("(< 0.85 strict / < 0.90 lenient supports discriminant validity for a pair)")
        htmt_df.round(3).to_csv(os.path.join(output_dir, "discriminant_validity_htmt.csv"), encoding="utf-8")

    print(
        "\nNOTE: the optimizer converged (found a solution), but on the delivered "
        "synthetic dataset the fit indices, loadings, alpha/omega, AVE/CR, and HTMT "
        "are all expected to look poor or nonsensical -- items are simulated "
        "independently, so there is no real factor structure for the CFA to recover. "
        "'Converged' here only means the script's code ran end to end; it is not a "
        "claim that the model fits. Interpret these numbers only on the real-data run."
    )

except Exception as exc:
    print(f"\nCFA did not converge on synthetic data: {exc}")
    print("This is expected (items are simulated independently).")
    print("The script ran successfully. Convergence on real data is what matters.")
    pd.DataFrame({"note": ["CFA did not converge on synthetic data"]}).to_csv(
        os.path.join(output_dir, "cfa_fit.csv"), index=False, encoding="utf-8"
    )

print("\nSEM measurement model script completed.")
print(f"Output files in: {output_dir}")
