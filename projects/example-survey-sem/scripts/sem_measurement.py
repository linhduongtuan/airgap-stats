# DR Stage D3 (SEM): Measurement model  (example-survey-sem)
# Cronbach's alpha + McDonald's omega (numpy) + CFA (semopy, ordinal/DWLS estimator)
# Requires: pandas, numpy, scipy, semopy, statsmodels. pip install semopy once.
#
# ESTIMATOR (Phase 3 of the statistical-methods roadmap): js_q*/bo_q* are
# 5-point Likert items -- ordinal, not continuous. This script fits the CFA
# with semopy's DWLS estimator on the polychoric correlation matrix
# (declaring every item ordinal), replacing the previous plain-ML fit
# that plans/sem_measurement_plan.yaml had flagged `needs_review` in
# Phase 0. Also new: McDonald's omega, AVE/composite reliability, and the
# HTMT ratio between jobsat and burnout.
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
    htmt,
    reliability_from_cfa,
)

dat = pd.read_csv(input_csv, encoding="utf-8")
os.makedirs(output_dir, exist_ok=True)

constructs = {
    "jobsat":  ["js_q1", "js_q2", "js_q3", "js_q4", "js_q5"],
    "burnout": ["bo_q1", "bo_q2", "bo_q3", "bo_q4", "bo_q5"],
}
missing = [v for items in constructs.values() for v in items if v not in dat.columns]
if missing:
    raise ValueError(f"Missing columns in data: {', '.join(missing)}")

# --- Scale scores (row mean, >= 50 % items non-missing) -- descriptive use only ---
for cn, items in constructs.items():
    n_ok   = dat[items].notna().sum(axis=1)
    min_ok = math.ceil(len(items) * 0.5)
    dat[f"{cn}_score"] = np.where(n_ok >= min_ok, dat[items].mean(axis=1), np.nan)

# === CFA in semopy, DWLS estimator on declared-ordinal items ================
print("=== CFA (DWLS estimator, ordinal items) ===")
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

    pe = cfa.params
    pe.to_csv(os.path.join(output_dir, "cfa_estimates.csv"), index=False, encoding="utf-8")

    # --- Reliability: alpha + omega ---
    print("\n=== Reliability: Cronbach's Alpha + McDonald's Omega ===")
    rel_rows = []
    for cn, items in constructs.items():
        rel = reliability_from_cfa(dat, cn, items, cfa.loadings)
        rel_rows.append({"construct": rel.construct, "n_items": rel.n_items, "alpha": rel.alpha, "omega": rel.omega})
    reliability_summary = pd.DataFrame(rel_rows)
    print(reliability_summary.to_string(index=False))
    reliability_summary.to_csv(os.path.join(output_dir, "reliability_summary.csv"), index=False, encoding="utf-8")

    # --- Convergent validity: AVE + composite reliability ---
    print("\n=== Convergent Validity: AVE + Composite Reliability ===")
    validity_rows = []
    for cn in constructs:
        cn_loadings = cfa.loadings.loc[cfa.loadings["rval"] == cn, "Est. Std"]
        validity_rows.append({
            "construct": cn,
            "AVE": round(average_variance_extracted(cn_loadings), 3),
            "CR": round(composite_reliability(cn_loadings), 3),
        })
    validity_summary = pd.DataFrame(validity_rows)
    print(validity_summary.to_string(index=False))
    print("(AVE >= 0.50 and CR >= 0.70 are the conventional 'good' thresholds -- Fornell & Larcker 1981)")
    validity_summary.to_csv(os.path.join(output_dir, "convergent_validity.csv"), index=False, encoding="utf-8")

    # --- Discriminant validity: HTMT ---
    print("\n=== Discriminant Validity: HTMT(jobsat, burnout) ===")
    htmt_value = htmt(dat, constructs["jobsat"], constructs["burnout"])
    print(f"HTMT = {htmt_value:.3f} (< 0.85 strict / < 0.90 lenient supports discriminant validity)")
    pd.DataFrame([{"construct_a": "jobsat", "construct_b": "burnout", "htmt": round(htmt_value, 3)}]).to_csv(
        os.path.join(output_dir, "discriminant_validity_htmt.csv"), index=False, encoding="utf-8"
    )

    print(
        "\nNOTE: the optimizer converged (found a solution), but on this synthetic "
        "dataset the fit indices, loadings, alpha/omega, AVE/CR, and HTMT are all "
        "expected to look poor or nonsensical -- items are simulated independently, "
        "so there is no real factor structure for the CFA to recover. 'Converged' "
        "here only means the script's code ran end to end; it is not a claim that "
        "the model fits. Interpret these numbers only on the real-data run."
    )

except Exception as exc:
    print(f"CFA did not fit: {exc}")
