# DR Stage D3/D4: Inferential analysis (crude + adjusted)
# Requires: pandas, numpy, statsmodels, scipy, patsy. Run from the project folder.
#
# Section 3 (diagnostics) is Phase 1 of the statistical-methods roadmap: VIF,
# influence (Cook's distance / DFBETAs), a Box-Tidwell linearity-in-the-logit
# check, and bootstrap-optimism internal validation for the adjusted model.
# None of this existed before -- the adjusted model previously shipped with
# no check that its own assumptions held.
#
# Section 4 is Phase 2: a Firth penalized-likelihood refit (robust to the
# quasi-separation a ~200-row sample with a dozen covariates risks) and, for
# any Box-Tidwell-flagged variable, an automatic log-transform-and-refit.
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

# Variables — set these for your project
outcome_var   = "mortality_30day"   # binary outcome column
predictor_var = "crp"               # main predictor column
covariate_vars = [                  # adjustment covariates for the adjusted model
    "age", "sex", "bmi", "treatment", "sbp",
    "diabetes", "hypertension", "smoking",
    "egfr", "hba1c", "complication",
]
# ============================================================================

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.diagnostics import (
    bootstrap_optimism,
    box_tidwell_test,
    compute_dfbetas,
    compute_influence,
    compute_vif,
)
from tools.medical_track import firth_logistic_regression, log_transform_if_skewed

dat = pd.read_csv(input_csv, encoding="utf-8")
os.makedirs(output_dir, exist_ok=True)

# --- Pre-fit checks ---
for v in [outcome_var, predictor_var]:
    if v not in dat.columns:
        print(
            f"Column '{v}' not found. Update outcome_var / predictor_var in USER SETTINGS.\n"
            "For SEM projects (surveys), use sem_measurement.py + sem_structural.py instead."
        )
        sys.exit(0)

print("Outcome distribution:")
print(dat[outcome_var].value_counts(dropna=False))
if dat[outcome_var].nunique() < 2:
    raise ValueError("Outcome has fewer than 2 observed classes.")
if dat[outcome_var].isna().any():
    raise ValueError("Missing values in outcome. Please handle before fitting.")

pred_non_na = dat[predictor_var].dropna()
if pred_non_na.nunique() < 2:
    raise ValueError("Predictor has < 2 unique values after removing NAs.")

complete = dat[[outcome_var, predictor_var]].dropna()
print(f"Complete cases for crude model: {len(complete)} / {len(dat)}")


# --- Helper: extract OR table from a fitted statsmodels logit model ---
def extract_results(model):
    params = model.params
    ci     = model.conf_int()
    return pd.DataFrame({
        "term":     params.index,
        "estimate": params.round(4),
        "or":       np.exp(params).round(4),
        "ci_low":   np.exp(ci.iloc[:, 0]).round(4),
        "ci_high":  np.exp(ci.iloc[:, 1]).round(4),
        "p_value":  model.pvalues.round(4),
    }).reset_index(drop=True)


# === SECTION 1: CRUDE MODEL (Stage D3) ======================================
crude_formula = f"{outcome_var} ~ {predictor_var}"
crude_fit     = smf.logit(crude_formula, data=dat).fit(disp=False)
crude_results = extract_results(crude_fit)

print("\n=== CRUDE MODEL ===")
print(f"Model: {outcome_var} ~ {predictor_var} (logistic regression)")
print(f"N used: {int(crude_fit.nobs)}")
print(crude_results.to_string(index=False))

crude_path = os.path.join(output_dir, "infer_crude.csv")
crude_results.to_csv(crude_path, index=False, encoding="utf-8")
print(f"\nCrude results written to {crude_path}")


# === SECTION 2: ADJUSTED MODEL (Stage D4) ===================================
covariate_vars = [v for v in covariate_vars if v in dat.columns]

# Set reference levels to match R factor() calls in infer.R
dat["sex"]       = pd.Categorical(dat["sex"],       categories=["Nữ", "Nam"])
dat["treatment"] = pd.Categorical(dat["treatment"], categories=["Phác đồ A", "Phác đồ B"])

# statsmodels treats pd.Categorical with C() — use Q() for reserved names
def quote(v):
    return f'Q("{v}")'

rhs = " + ".join([predictor_var] + [quote(v) for v in covariate_vars])
adj_formula = f"{outcome_var} ~ {rhs}"
print(f"\nAdjusted formula: {adj_formula}")

adj_fit     = smf.logit(adj_formula, data=dat).fit(disp=False)
adj_results = extract_results(adj_fit)

print("\n=== ADJUSTED MODEL ===")
print(f"N used: {int(adj_fit.nobs)}")
print(adj_results.to_string(index=False))

adj_path = os.path.join(output_dir, "infer_adjusted.csv")
adj_results.to_csv(adj_path, index=False, encoding="utf-8")
print(f"\nAdjusted results written to {adj_path}")


# --- Crude vs Adjusted comparison for the main predictor ---
# Row index 1 = predictor (row 0 is Intercept)
cmp = pd.DataFrame({
    "model":      ["Crude", "Adjusted"],
    "or":         [crude_results.loc[1, "or"],     adj_results.loc[1, "or"]],
    "ci_low":     [crude_results.loc[1, "ci_low"], adj_results.loc[1, "ci_low"]],
    "ci_high":    [crude_results.loc[1, "ci_high"],adj_results.loc[1, "ci_high"]],
    "p_value":    [crude_results.loc[1, "p_value"],adj_results.loc[1, "p_value"]],
    "covariates": ["None", ", ".join(covariate_vars)],
})

print(f"\n=== CRUDE VS ADJUSTED ({predictor_var}) ===")
print(cmp.to_string(index=False))

cmp_path = os.path.join(output_dir, "infer_crude_vs_adjusted.csv")
cmp.to_csv(cmp_path, index=False, encoding="utf-8")
print(f"Crude vs adjusted comparison written to {cmp_path}")


# === SECTION 3: DIAGNOSTICS on the adjusted model (Phase 1) =================

print("\n=== DIAGNOSTICS: multicollinearity (VIF) ===")
vif_table = compute_vif(dat, rhs)
print(vif_table.to_string(index=False))
vif_path = os.path.join(output_dir, "infer_adjusted_vif.csv")
vif_table.to_csv(vif_path, index=False, encoding="utf-8")
high_vif = vif_table.loc[vif_table["flagged"], "term"].tolist()
if high_vif:
    print(f"WARNING: VIF > 5 for: {', '.join(high_vif)} -- investigate collinearity before trusting these coefficients.")
else:
    print("No term exceeds VIF 5 -- no strong multicollinearity detected.")
print(f"VIF table written to {vif_path}")

print("\n=== DIAGNOSTICS: influence (Cook's distance) ===")
cooks_df, cooks_thr = compute_influence(adj_fit)
n_flagged_cooks = int(cooks_df["flagged"].sum())
print(f"Threshold (4/n): {cooks_thr:.4f} | flagged observations: {n_flagged_cooks} / {len(cooks_df)}")
cooks_path = os.path.join(output_dir, "infer_adjusted_influence.csv")
cooks_df.to_csv(cooks_path, index=False, encoding="utf-8")
print(f"Cook's distance table written to {cooks_path}")

print("\n=== DIAGNOSTICS: influence (DFBETAs) ===")
dfbetas_df, dfbetas_thr = compute_dfbetas(adj_fit)
n_flagged_dfbetas = int(dfbetas_df["flagged"].sum())
print(f"Threshold (2/sqrt(n)): {dfbetas_thr:.4f} | flagged observations: {n_flagged_dfbetas} / {len(dfbetas_df)}")
dfbetas_path = os.path.join(output_dir, "infer_adjusted_dfbetas.csv")
dfbetas_df.to_csv(dfbetas_path, index=False, encoding="utf-8")
print(f"DFBETAs table written to {dfbetas_path}")

print("\n=== DIAGNOSTICS: linearity in the logit (Box-Tidwell) ===")
continuous_for_linearity = [v for v in [predictor_var, "age", "bmi", "sbp", "egfr", "hba1c"] if v in dat.columns]
bt_table = box_tidwell_test(dat, outcome_var, rhs, continuous_for_linearity)
print(bt_table.to_string(index=False))
bt_path = os.path.join(output_dir, "infer_adjusted_box_tidwell.csv")
bt_table.to_csv(bt_path, index=False, encoding="utf-8")
print(f"Box-Tidwell table written to {bt_path}")

print("\n=== DIAGNOSTICS: bootstrap-optimism internal validation (n_boot=200) ===")
boot_result = bootstrap_optimism(dat, adj_formula, outcome_var, n_boot=200, seed=2026)
boot_row = boot_result.to_row()
for k, v in boot_row.items():
    print(f"  {k}: {v}")
boot_path = os.path.join(output_dir, "infer_adjusted_bootstrap_validation.csv")
pd.DataFrame([boot_row]).to_csv(boot_path, index=False, encoding="utf-8")
print(f"Bootstrap validation written to {boot_path}")

print(
    "\nNOTE: on this synthetic dataset, VIF/influence/linearity/bootstrap results "
    "are expected to look bland or degenerate -- columns are simulated "
    "independently, so there is no real collinearity, no real outliers, and no "
    "real discrimination to detect. This section verifies the diagnostic code "
    "runs; interpret the numbers only on the real-data run."
)


# === SECTION 4: SENSITIVITY ANALYSES (Phase 2) ==============================

print("\n=== SENSITIVITY: Firth penalized logistic regression (adjusted model) ===")
firth_fit = firth_logistic_regression(dat, adj_formula)
firth_table = firth_fit.to_frame()
print(firth_table.to_string(index=False))
print(f"Converged: {firth_fit.converged} (n_iter={firth_fit.n_iter})")
firth_path = os.path.join(output_dir, "infer_adjusted_firth.csv")
firth_table.to_csv(firth_path, index=False, encoding="utf-8")
print(f"Firth results written to {firth_path}")

# Compare the main predictor's OR: plain MLE vs Firth. A large relative gap
# is itself a signal of separation/instability in the plain adjusted model
# above -- flag it rather than always asserting one exists.
mle_or = adj_results.loc[adj_results["term"] == predictor_var, "or"]
firth_or = firth_table.loc[firth_table["term"] == predictor_var, "or"]
if len(mle_or) and len(firth_or):
    mle_val, firth_val = float(mle_or.iloc[0]), float(firth_or.iloc[0])
    rel_gap = abs(mle_val - firth_val) / max(abs(firth_val), 1e-9)
    verdict = (
        "large relative gap => the plain adjusted model above is less trustworthy than it looks"
        if rel_gap > 0.15 else
        "small gap => no sign of separation/instability in the plain adjusted model"
    )
    print(f"\n{predictor_var} OR -- plain MLE: {mle_val:.4f} | Firth: {firth_val:.4f} ({verdict})")

print("\n=== SENSITIVITY: log-transform for Box-Tidwell-flagged variables ===")
flagged_vars = bt_table.loc[bt_table["status"] == "nonlinear_suspected", "variable"].tolist()
if not flagged_vars:
    print("No variable was flagged nonlinear_suspected in Section 3 -- nothing to transform.")
else:
    dat_transformed = dat.copy()
    transformed_terms = []
    for var in flagged_vars:
        decision = log_transform_if_skewed(dat[var])
        print(f"  {var}: {decision.reason}")
        if decision.action == "log_transform":
            new_col = f"log_{var}"
            dat_transformed[new_col] = np.log(dat_transformed[var])
            transformed_terms.append((var, new_col))

    if transformed_terms:
        # Rebuild the RHS the same way Section 2 did (predictor unquoted,
        # covariates Q(...)-quoted), just substituting the log-transformed
        # name wherever a variable was actually transformed.
        name_map = dict(transformed_terms)  # old name -> new (log_*) name
        new_predictor = name_map.get(predictor_var, predictor_var)
        new_covariates = [name_map.get(v, v) for v in covariate_vars]
        rhs_transformed = " + ".join([new_predictor] + [quote(v) for v in new_covariates])
        adj_formula_transformed = f"{outcome_var} ~ {rhs_transformed}"
        print(f"\nRefit formula: {adj_formula_transformed}")
        transformed_fit = smf.logit(adj_formula_transformed, data=dat_transformed).fit(disp=False)
        transformed_results = extract_results(transformed_fit)
        print(transformed_results.to_string(index=False))
        transformed_path = os.path.join(output_dir, "infer_adjusted_log_transformed.csv")
        transformed_results.to_csv(transformed_path, index=False, encoding="utf-8")
        print(f"Log-transformed refit written to {transformed_path}")
    else:
        print("Flagged variable(s) could not be log-transformed (non-positive values) -- "
              "consider a restricted cubic spline instead (tools.medical_track.restricted_cubic_spline_basis).")

print(
    "\nNOTE: Section 4 is a sensitivity comparison, not a replacement for the "
    "primary adjusted model in Section 2. Report both if they materially "
    "disagree; that disagreement is itself a finding."
)
