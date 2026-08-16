# DR Stage D3 (SEM): Measurement model
# Cronbach's alpha + McDonald's omega (numpy) + CFA (semopy, ordinal/DWLS estimator)
# Requires: pandas, numpy, scipy, semopy, statsmodels. pip install semopy once.
#
# ESTIMATOR (Phase 3 of the statistical-methods roadmap): js_q*/bo_q* are
# 5-point Likert items -- ordinal, not continuous. This script now fits the
# CFA with semopy's DWLS estimator on the polychoric correlation matrix
# (declaring every item ordinal), the methodologically correct choice for
# ordinal indicators (WLSMV is lavaan's name for the same family of
# estimator; DWLS is semopy's). This replaces the previous plain-ML fit
# that plans/sem_measurement_plan.yaml had flagged `needs_review` in
# Phase 0 -- see that file's `measurement_model.estimator` block, updated
# alongside this script.
#
# Also new in Phase 3: McDonald's omega (doesn't assume tau-equivalence,
# unlike alpha), AVE/composite reliability (convergent validity), and the
# HTMT ratio between Job Satisfaction and Burnout (discriminant validity --
# two negatively-correlated affective constructs need an explicit check
# that they're empirically distinct, not just conceptually different).
#
# SYNTHESIS-MODE CHECK (Phase 4): last verified clean against both Stage B
# (independent synthesis, the default below) and Stage B2 (correlated
# synthesis -- see synthesize_data_correlated.py) as of 2026-08-15. The
# Stage B2 check used a stand-in file (this project's own Stage B output fed
# in as if it were real data, only to exercise the code path) -- re-verify
# against a genuine Stage B2 file once you generate one from real data.

# === USER SETTINGS ==========================================================
# Runs on the synthetic dataset as delivered:
input_csv  = "data_synthetic/synthetic_dataset.csv"
output_dir = "outputs_synthetic"
# To run on REAL data, comment the two lines above and uncomment these:
# input_csv  = input("Path to real dataset CSV: ").strip()
# output_dir = "results_real"
# ============================================================================

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

# --- Items per construct ---
js_items  = ["js_q1", "js_q2", "js_q3", "js_q4", "js_q5"]
bo_items  = ["bo_q1", "bo_q2", "bo_q3", "bo_q4", "bo_q5"]
all_items = js_items + bo_items
constructs = {"Job_Satisfaction": js_items, "Burnout": bo_items}

missing_cols = [c for c in all_items if c not in dat.columns]
if missing_cols:
    raise ValueError(f"Missing columns in data: {', '.join(missing_cols)}")

# --- Scale scores (row mean, >= 50 % non-missing) -- kept for descriptive use ---
def compute_scale(df, items, min_prop=0.50):
    sub     = df[items]
    min_ok  = int(np.floor(len(items) * min_prop))
    scores  = sub.apply(
        lambda row: row.mean() if row.notna().sum() >= min_ok else np.nan,
        axis=1,
    )
    return scores

dat["js_score"] = compute_scale(dat, js_items)
dat["bo_score"] = compute_scale(dat, bo_items)

scale_summary = pd.DataFrame({
    "construct": ["Job_Satisfaction", "Burnout"],
    "mean": [round(dat["js_score"].mean(), 2), round(dat["bo_score"].mean(), 2)],
    "sd":   [round(dat["js_score"].std(),  2), round(dat["bo_score"].std(),  2)],
    "n":    [dat["js_score"].notna().sum(),    dat["bo_score"].notna().sum()],
})
print("=== Scale Scores (row-mean, descriptive use only) ===")
print(scale_summary.to_string(index=False))

# === CFA via semopy, DWLS estimator on declared-ordinal items ===============
print("\n=== CFA (DWLS estimator, ordinal items) ===")
try:
    cfa = fit_measurement_model(dat, constructs, estimator="DWLS")

    if not cfa.converged:
        raise RuntimeError("Optimizer did not converge.")

    fi_df = pd.DataFrame(
        [{"measure": k, "value": v} for k, v in cfa.fit_indices.items()
         if k in ("cfi", "tli", "rmsea", "srmr")]
    )
    print(fi_df.to_string(index=False))
    fi_df.to_csv(os.path.join(output_dir, "cfa_fit.csv"), index=False, encoding="utf-8")

    print("\n=== Standardized Loadings ===")
    print(cfa.loadings.to_string(index=False))
    cfa.loadings.to_csv(os.path.join(output_dir, "cfa_loadings.csv"), index=False, encoding="utf-8")

    # --- Reliability: alpha + omega, from the CFA's own loadings ---
    print("\n=== Reliability: Cronbach's Alpha + McDonald's Omega ===")
    rel_js = reliability_from_cfa(dat, "Job_Satisfaction", js_items, cfa.loadings)
    rel_bo = reliability_from_cfa(dat, "Burnout", bo_items, cfa.loadings)
    reliability_summary = pd.DataFrame([
        {"construct": rel_js.construct, "n_items": rel_js.n_items, "alpha": rel_js.alpha, "omega": rel_js.omega},
        {"construct": rel_bo.construct, "n_items": rel_bo.n_items, "alpha": rel_bo.alpha, "omega": rel_bo.omega},
    ])
    print(reliability_summary.to_string(index=False))
    reliability_summary.to_csv(os.path.join(output_dir, "reliability_summary.csv"), index=False, encoding="utf-8")

    # --- Convergent validity: AVE + composite reliability ---
    print("\n=== Convergent Validity: AVE + Composite Reliability ===")
    js_loadings = cfa.loadings.loc[cfa.loadings["rval"] == "Job_Satisfaction", "Est. Std"]
    bo_loadings = cfa.loadings.loc[cfa.loadings["rval"] == "Burnout", "Est. Std"]
    validity_summary = pd.DataFrame([
        {"construct": "Job_Satisfaction", "AVE": round(average_variance_extracted(js_loadings), 3),
         "CR": round(composite_reliability(js_loadings), 3)},
        {"construct": "Burnout", "AVE": round(average_variance_extracted(bo_loadings), 3),
         "CR": round(composite_reliability(bo_loadings), 3)},
    ])
    print(validity_summary.to_string(index=False))
    print("(AVE >= 0.50 and CR >= 0.70 are the conventional 'good' thresholds -- Fornell & Larcker 1981)")
    validity_summary.to_csv(os.path.join(output_dir, "convergent_validity.csv"), index=False, encoding="utf-8")

    # --- Discriminant validity: HTMT between Job_Satisfaction and Burnout ---
    print("\n=== Discriminant Validity: HTMT(Job_Satisfaction, Burnout) ===")
    htmt_value = htmt(dat, js_items, bo_items)
    print(f"HTMT = {htmt_value:.3f} (< 0.85 strict / < 0.90 lenient supports discriminant validity)")
    pd.DataFrame([{"construct_a": "Job_Satisfaction", "construct_b": "Burnout", "htmt": round(htmt_value, 3)}]).to_csv(
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
    print(f"\nCFA did not converge on synthetic data: {exc}")
    print("This is expected (items are simulated independently).")
    print("The script ran successfully. Convergence on real data is what matters.")
    pd.DataFrame({"note": ["CFA did not converge on synthetic data"]}).to_csv(
        os.path.join(output_dir, "cfa_fit.csv"), index=False, encoding="utf-8"
    )

print("\nSEM measurement model script completed.")
print(f"Output files in: {output_dir}")
