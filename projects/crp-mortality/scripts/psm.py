# DR Stage D4 (extension): Propensity-score sensitivity analysis (Phase 2 of
# the statistical-methods roadmap)
# Requires: pandas, numpy, statsmodels, scipy. Run from the project folder.
#
# WHY THIS SCRIPT EXISTS
# scripts/infer.py's adjusted model controls for confounders by adding them
# as covariates. That works, but it silently assumes the model is specified
# correctly (right functional form, no extreme extrapolation across
# regions of the covariate space treated and untreated patients don't share
# equally). Propensity-score matching (PSM) and inverse-probability
# weighting (IPTW) are a differently-flawed comparison method -- they don't
# extrapolate the way a regression does. If the regression-adjusted and the
# PSM/IPTW estimates tell a similar story, that's real evidence the finding
# isn't an artifact of model specification.
#
# SCOPE NOTE
# The primary research question in plans/sap.md is about CRP (continuous),
# not treatment. PSM/IPTW need a *binary* exposure, so this script
# demonstrates the workflow on `treatment` (Phác đồ A vs B) -- a real,
# already-confirmed binary variable in this dataset, not an invented
# dichotomization of CRP. Treat this as a secondary "does treatment affect
# mortality" sensitivity analysis, distinct from the primary CRP question.
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

exposure_var = "treatment"       # binary exposure -- see scope note above
outcome_var  = "mortality_30day"
covariate_vars = [                # same confounder set as scripts/infer.py, minus the exposure itself
    "crp", "age", "sex", "bmi", "sbp",
    "diabetes", "hypertension", "smoking",
    "egfr", "hba1c", "complication",
]
# ============================================================================

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.medical_track import e_value, iptw_weights, propensity_scores, psm_match

dat = pd.read_csv(input_csv, encoding="utf-8")
os.makedirs(output_dir, exist_ok=True)

missing_cols = [v for v in [exposure_var, outcome_var] + covariate_vars if v not in dat.columns]
if missing_cols:
    raise ValueError(f"Missing columns: {', '.join(missing_cols)}")

dat["sex"] = pd.Categorical(dat["sex"], categories=["Nữ", "Nam"])

# --- Binary-code the exposure (0/1) for propensity/matching math ---
exposure_levels = sorted(dat[exposure_var].dropna().unique())
if len(exposure_levels) != 2:
    raise ValueError(f"{exposure_var} must have exactly 2 levels; found {exposure_levels}")
reference_level, treated_level = exposure_levels
dat["_exposed"] = (dat[exposure_var] == treated_level).astype(int)
print(f"Exposure: {exposure_var} ({treated_level} = 1, {reference_level} = 0 [reference])")

rhs = " + ".join(f'Q("{v}")' for v in covariate_vars)

# === PART 1: PROPENSITY SCORE ================================================
print(f"\n=== PROPENSITY SCORE: P({exposure_var}={treated_level} | covariates) ===")
ps = propensity_scores(dat, "_exposed", rhs)
dat["_ps"] = ps
print(f"PS range: [{ps.min():.4f}, {ps.max():.4f}] | mean exposed: {ps[dat['_exposed']==1].mean():.4f} "
      f"| mean unexposed: {ps[dat['_exposed']==0].mean():.4f}")

ps_path = os.path.join(output_dir, "psm_propensity_scores.csv")
dat[["_exposed", "_ps"]].to_csv(ps_path, index=False, encoding="utf-8")
print(f"Propensity scores written to {ps_path}")

# === PART 2: MATCHING =========================================================
print("\n=== PROPENSITY-SCORE MATCHING (1:1 nearest neighbor, no replacement) ===")
match = psm_match(dat, "_exposed", ps, seed=2026)
print(f"Caliper (0.2 SD of logit-PS): {match.caliper:.4f}")
print(f"Matched {match.n_matched} / {match.n_treated} exposed patients")

if match.n_matched > 0:
    matched_treated = dat.loc[match.pairs["treated_idx"], outcome_var].to_numpy()
    matched_control = dat.loc[match.pairs["control_idx"], outcome_var].to_numpy()
    risk_treated = matched_treated.mean()
    risk_control = matched_control.mean()
    matched_rr = risk_treated / risk_control if risk_control > 0 else np.nan
    print(f"Matched-pair outcome risk -- exposed: {risk_treated:.4f} | unexposed: {risk_control:.4f} "
          f"| RR: {matched_rr:.4f}" if risk_control > 0 else "Matched-pair RR undefined (0 events in matched controls)")

match_path = os.path.join(output_dir, "psm_matched_pairs.csv")
match.pairs.to_csv(match_path, index=False, encoding="utf-8")
print(f"Matched pairs written to {match_path}")

# === PART 3: IPTW =============================================================
print("\n=== INVERSE-PROBABILITY-OF-TREATMENT WEIGHTING (stabilized) ===")
w = iptw_weights(dat["_exposed"], ps, stabilized=True)
dat["_iptw"] = w
print(f"Weight range: [{w.min():.4f}, {w.max():.4f}] | mean: {w.mean():.4f} (should be close to 1.0)")

weighted_risk_treated = np.average(dat.loc[dat["_exposed"] == 1, outcome_var], weights=w[dat["_exposed"] == 1])
weighted_risk_control = np.average(dat.loc[dat["_exposed"] == 0, outcome_var], weights=w[dat["_exposed"] == 0])
iptw_rr = weighted_risk_treated / weighted_risk_control if weighted_risk_control > 0 else np.nan
print(f"IPTW-weighted outcome risk -- exposed: {weighted_risk_treated:.4f} | unexposed: {weighted_risk_control:.4f} "
      f"| RR: {iptw_rr:.4f}")

iptw_path = os.path.join(output_dir, "psm_iptw_weights.csv")
dat[["_exposed", "_ps", "_iptw"]].to_csv(iptw_path, index=False, encoding="utf-8")
print(f"IPTW weights written to {iptw_path}")

# === PART 4: E-VALUE ==========================================================
print("\n=== E-VALUE: robustness of the IPTW estimate to unmeasured confounding ===")
if iptw_rr == iptw_rr and iptw_rr > 0:  # not NaN
    ev = e_value(float(iptw_rr), measure="RR")
    print(f"IPTW risk ratio: {ev['estimate']:.4f} -> E-value: {ev['e_value_point']:.4f}")
    print(
        "Interpretation: an unmeasured confounder would need to be associated with both "
        f"{exposure_var} and {outcome_var} by a risk ratio of at least {ev['e_value_point']:.2f} "
        "(each), above and beyond the measured covariates, to fully explain away this estimate."
    )
    ev_path = os.path.join(output_dir, "psm_evalue.csv")
    pd.DataFrame([ev]).to_csv(ev_path, index=False, encoding="utf-8")
    print(f"E-value written to {ev_path}")
else:
    print("E-value not computed (IPTW risk ratio undefined on this run).")

print(
    "\nNOTE: on this synthetic dataset, all of the above is meaningless by design "
    "(columns are simulated independently, so there is no real exposure-outcome "
    "relationship and no real confounding to adjust for). This script verifies "
    "the code runs; interpret nothing from these numbers. This is a secondary "
    "sensitivity analysis of `treatment`, not the primary CRP question in "
    "plans/sap.md -- see the scope note at the top of this file."
)
