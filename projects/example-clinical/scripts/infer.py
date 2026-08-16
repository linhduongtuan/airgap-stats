# DR Stage D3/D4: Inferential analysis (crude + adjusted)  (example-clinical)
# Requires: pandas, numpy, statsmodels, scipy, patsy. Run from the project folder.
#
# Section 3 (diagnostics) is Phase 1 of the statistical-methods roadmap: VIF,
# influence (Cook's distance / DFBETAs), a Box-Tidwell linearity-in-the-logit
# check, and bootstrap-optimism internal validation for the adjusted model.
#
# Section 4 is Phase 2: a Firth penalized-likelihood refit (robust to the
# quasi-separation a ~200-row sample with several covariates risks) and, for
# any Box-Tidwell-flagged variable, an automatic log-transform-and-refit.
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

outcome_var   = "mortality_30day"
predictor_var = "treatment"
covariates    = ["age", "sex", "bmi", "diabetes", "hypertension", "smoking", "egfr", "hba1c", "crp"]

# Exact reference level (labels from the reviewed pattern file)
dat["treatment"] = pd.Categorical(dat["treatment"], categories=["Phác đồ A", "Phác đồ B"])
dat["sex"]       = pd.Categorical(dat["sex"],       categories=["Nam", "Nữ"])

missing_cols = [v for v in [outcome_var, predictor_var] + covariates if v not in dat.columns]
if missing_cols:
    raise ValueError(f"Missing columns: {', '.join(missing_cols)}")
if dat[outcome_var].dropna().nunique() < 2:
    raise ValueError("Outcome has fewer than two classes.")


def or_table(model, term: str) -> pd.DataFrame:
    est   = model.params
    ci    = model.conf_int()
    pvals = model.pvalues
    keep  = [name for name in est.index if term in name]
    return pd.DataFrame({
        "term":    keep,
        "OR":      [round(float(np.exp(est[n])), 2) for n in keep],
        "CI_low":  [round(float(np.exp(ci.loc[n, 0])), 2) for n in keep],
        "CI_high": [round(float(np.exp(ci.loc[n, 1])), 2) for n in keep],
        "p_value": [round(float(pvals[n]), 3) for n in keep],
    })


# === SECTION 1: CRUDE MODEL (Stage D3) ======================================
crude     = smf.logit(f"{outcome_var} ~ {predictor_var}", data=dat).fit(disp=False)
crude_res = or_table(crude, predictor_var)
crude_res["model"] = "crude"
crude_res["covariates"] = "None"

crude_path = os.path.join(output_dir, "infer_crude.csv")
crude_res.to_csv(crude_path, index=False, encoding="utf-8")
print(f"Crude model, n = {int(crude.nobs)}")
print(crude_res.to_string(index=False))
print()

# === SECTION 2: ADJUSTED MODEL (Stage D4) ===================================
rhs = f"{predictor_var} + " + " + ".join(covariates)
adj_formula = f"{outcome_var} ~ {rhs}"
adj         = smf.logit(adj_formula, data=dat).fit(disp=False)
adj_res     = or_table(adj, predictor_var)
adj_res["model"] = "adjusted"
adj_res["covariates"] = ", ".join(covariates)

comparison = pd.concat([crude_res, adj_res], ignore_index=True)
cmp_path = os.path.join(output_dir, "infer_crude_vs_adjusted.csv")
comparison.to_csv(cmp_path, index=False, encoding="utf-8")
print(f"Adjusted model, n = {int(adj.nobs)}")
print(comparison.to_string(index=False))


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
cooks_df, cooks_thr = compute_influence(adj)
n_flagged_cooks = int(cooks_df["flagged"].sum())
print(f"Threshold (4/n): {cooks_thr:.4f} | flagged observations: {n_flagged_cooks} / {len(cooks_df)}")
cooks_path = os.path.join(output_dir, "infer_adjusted_influence.csv")
cooks_df.to_csv(cooks_path, index=False, encoding="utf-8")
print(f"Cook's distance table written to {cooks_path}")

print("\n=== DIAGNOSTICS: influence (DFBETAs) ===")
dfbetas_df, dfbetas_thr = compute_dfbetas(adj)
n_flagged_dfbetas = int(dfbetas_df["flagged"].sum())
print(f"Threshold (2/sqrt(n)): {dfbetas_thr:.4f} | flagged observations: {n_flagged_dfbetas} / {len(dfbetas_df)}")
dfbetas_path = os.path.join(output_dir, "infer_adjusted_dfbetas.csv")
dfbetas_df.to_csv(dfbetas_path, index=False, encoding="utf-8")
print(f"DFBETAs table written to {dfbetas_path}")

print("\n=== DIAGNOSTICS: linearity in the logit (Box-Tidwell) ===")
continuous_for_linearity = [v for v in ["age", "bmi", "egfr", "hba1c", "crp"] if v in dat.columns]
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

# Compare the main predictor's OR: plain MLE vs Firth (substring match on
# term, same convention or_table() uses for the categorical dummy name).
mle_predictor_rows = adj_res[adj_res["term"].str.contains(predictor_var)]
firth_predictor_rows = firth_table[firth_table["term"].str.contains(predictor_var)]
if not mle_predictor_rows.empty and not firth_predictor_rows.empty:
    mle_val = float(mle_predictor_rows["OR"].iloc[0])
    firth_val = float(firth_predictor_rows["or"].iloc[0])
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
        name_map = dict(transformed_terms)
        new_predictor = name_map.get(predictor_var, predictor_var)
        new_covariates = [name_map.get(v, v) for v in covariates]
        rhs_transformed = new_predictor + " + " + " + ".join(new_covariates)
        adj_formula_transformed = f"{outcome_var} ~ {rhs_transformed}"
        print(f"\nRefit formula: {adj_formula_transformed}")
        transformed_fit = smf.logit(adj_formula_transformed, data=dat_transformed).fit(disp=False)
        transformed_results = or_table(transformed_fit, predictor_var)
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
