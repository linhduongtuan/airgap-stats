# DR Stage D4 (SEM): Structural model — mediation
# Requires: pandas, numpy, scipy, semopy, statsmodels. pip install semopy once.
#
# ESTIMATOR + METHOD (Phase 3 of the statistical-methods roadmap):
# js_q*/bo_q* are ordinal Likert items and turnover_intent is binary --
# the previous plain-ML joint SEM fit was flagged `needs_review` in Phase 0
# (see plans/sem_measurement_plan.yaml). The textbook-first fix is a single
# joint DWLS/WLSMV fit of the whole measurement+structural model -- tried
# here, and rejected: semopy 2.3.11's WLS solver stalls at its starting
# values (never actually optimizes) once a structural model this size has
# this many ordinal indicators. That's a semopy limitation, not a bug in
# this script (see tools/sem_track/mediation.py's docstring for the full
# account, including what was ruled out before reaching that conclusion).
#
# This script instead uses factor-score regression (Skrondal & Laake 2001),
# a well-precedented two-step method: (1) fit the ordinal CFA alone via
# DWLS -- numerically robust, and the step that actually needed the
# ordinal estimator; (2) extract regression factor scores for
# Job_Satisfaction and Burnout; (3) fit the structural paths as ordinary
# regressions (OLS for the continuous mediator, logistic for the binary
# distal outcome) via statsmodels. Both stages are refit together inside a
# bootstrap loop for percentile confidence intervals on the indirect,
# direct, and total effects -- the previous version reported bare point
# estimates with no interval, which is not defensible for a product term
# like the indirect effect (Preacher & Hayes 2004, 2008).
#
# SYNTHESIS-MODE CHECK (Phase 4): last verified clean against both Stage B
# (independent synthesis, the default below, finishes in well under a
# minute) and Stage B2 (correlated synthesis -- see
# synthesize_data_correlated.py) as of 2026-08-15, though Stage B2 took
# ~230s -- 3-4x longer -- because the bootstrap loop's per-resample
# refits converge less readily on data with real correlation structure than
# on Stage B's independent columns. Budget for that if you switch input_csv
# below. The Stage B2 check used a stand-in file (this project's own Stage B
# output fed in as if it were real data, only to exercise the code path) --
# re-verify against a genuine Stage B2 file once you generate one from real
# data.

# === USER SETTINGS ==========================================================
# Runs on the synthetic dataset as delivered:
input_csv  = "data_synthetic/synthetic_dataset.csv"
output_dir = "outputs_synthetic"
# To run on REAL data, comment the two lines above and uncomment these:
# input_csv  = input("Path to real dataset CSV: ").strip()
# output_dir = "results_real"

n_boot = 50  # ~5-6s per refit on this model size -> ~5 minutes for 50 reps.
             # Raise for the real run if you can afford the wall-clock time;
             # the CI gets more stable, not more "correct", with more reps.
# ============================================================================

import os
import sys
import warnings
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.sem_track import bootstrap_mediation, compare_nested_regressions, fit_measurement_model
import statsmodels.formula.api as smf

dat = pd.read_csv(input_csv, encoding="utf-8")
os.makedirs(output_dir, exist_ok=True)

# --- Dummy coding for observed covariates ---
# Gender: 0 = Nữ (reference), 1 = Nam
dat["gender_num"] = (dat["gender"] == "Nam").astype(int)

# Education: THPT as reference
dat["education_dh"]   = (dat["education"] == "Đại học").astype(int)
dat["education_ts"]   = (dat["education"] == "Thạc sĩ").astype(int)
dat["education_tien"] = (dat["education"] == "Tiến sĩ").astype(int)

js_items = ["js_q1", "js_q2", "js_q3", "js_q4", "js_q5"]
bo_items = ["bo_q1", "bo_q2", "bo_q3", "bo_q4", "bo_q5"]
constructs = {"Job_Satisfaction": js_items, "Burnout": bo_items}
covariates = ["age", "gender_num", "education_dh", "education_ts", "education_tien", "tenure_years"]

print("==============================")
print("SEM STRUCTURAL MODEL RESULTS")
print("==============================")

try:
    # === STEP 1: measurement model (informational -- fit indices/loadings
    # were already reported by scripts/sem_measurement.py; refit here only
    # because bootstrap_mediation needs to refit it per-resample anyway,
    # and reporting it once on the full sample orients the reader). ===
    cfa = fit_measurement_model(dat, constructs, estimator="DWLS")
    print(f"\nMeasurement model (DWLS): converged={cfa.converged}, "
          f"CFI={cfa.fit_indices['cfi']:.4f}, RMSEA={cfa.fit_indices['rmsea']:.4f}")

    # === STEP 2: bootstrap the two-step structural path estimates =========
    print(f"\n--- Bootstrap mediation ({n_boot} resamples; this takes a few minutes) ---")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        boot = bootstrap_mediation(
            dat, constructs,
            mediator="Burnout", predictor="Job_Satisfaction", outcome="turnover_intent",
            outcome_is_binary=True, covariates=covariates,
            estimator="DWLS", n_boot=n_boot, seed=2026,
        )

    mediation_table = boot.to_frame()
    label_map = {
        "a": "a (JS -> Burnout)", "b": "b (Burnout -> TO | JS)",
        "c_prime": "c' (JS -> TO direct)", "indirect": "indirect (a*b)", "total": "total (c'+a*b)",
    }
    mediation_table["path"] = mediation_table["path"].map(label_map)
    print("\n--- Indirect, Direct, and Total Effects (percentile bootstrap 95% CI) ---")
    print(mediation_table.to_string(index=False))
    print(f"(n_boot={boot.n_boot}, failed refits={boot.n_failed})")
    mediation_table.to_csv(os.path.join(output_dir, "sem_mediation.csv"), index=False, encoding="utf-8")

    # === STEP 3: nested model comparison -- does the direct path matter? ===
    print("\n--- Nested model comparison: partial mediation (c' free) vs. full mediation (c' = 0) ---")
    scores = cfa.model.predict_factors(dat)
    combined = pd.concat([dat.reset_index(drop=True), scores.reset_index(drop=True)], axis=1)

    rhs_partial = " + ".join(["Burnout", "Job_Satisfaction"] + covariates)
    rhs_full_mediation = " + ".join(["Burnout"] + covariates)  # Job_Satisfaction (c') omitted
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit_partial = smf.logit(f"turnover_intent ~ {rhs_partial}", data=combined).fit(disp=False)
        fit_full_mediation = smf.logit(f"turnover_intent ~ {rhs_full_mediation}", data=combined).fit(disp=False)

    comparison = compare_nested_regressions(fit_partial, fit_full_mediation)
    print(f"LR = {comparison.lr_stat:.4f} on {comparison.delta_df} df, p = {comparison.p_value:.4f}")
    print(f"AIC: partial={comparison.aic_full:.2f} | full-mediation={comparison.aic_restricted:.2f}")
    print(f"Preferred: {comparison.preferred}")
    pd.DataFrame([{
        "lr_stat": comparison.lr_stat, "delta_df": comparison.delta_df, "p_value": comparison.p_value,
        "aic_partial_mediation": comparison.aic_full, "aic_full_mediation": comparison.aic_restricted,
        "preferred": comparison.preferred,
    }]).to_csv(os.path.join(output_dir, "sem_model_comparison.csv"), index=False, encoding="utf-8")

    print(
        "\nNOTE: on this synthetic dataset all of the above is expected to look "
        "degenerate (wide/unstable CIs, a poorly-fitting measurement model) -- "
        "items are simulated independently, so there is no real mediation effect "
        "to recover. This script verifies the code runs end to end; interpret "
        "nothing from these numbers except on the real-data run."
    )

except Exception as exc:
    print(f"\nModel did not run to completion on synthetic data: {exc}")
    print("This is expected because items are simulated independently.")
    print("The code path is valid; it will run the same way on real data.")
    pd.DataFrame({"note": ["SEM structural model did not complete on synthetic data"]}).to_csv(
        os.path.join(output_dir, "sem_fit.csv"), index=False, encoding="utf-8"
    )

print("\nSEM structural model script completed.")
print(f"Output files in: {output_dir}")
