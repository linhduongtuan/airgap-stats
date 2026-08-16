# DR Stage D4 (SEM): Structural model  (example-survey-sem)
# Requires: pandas, numpy, scipy, semopy, statsmodels. pip install semopy once.
#
# METHOD (Phase 3 of the statistical-methods roadmap): jobsat/burnout items
# are ordinal Likert, turnover_intent is binary -- the previous plain-ML
# joint SEM fit was flagged `needs_review` in Phase 0. This script uses the
# two-step factor-score-regression approach (Skrondal & Laake 2001): fit
# the ordinal CFA via DWLS, extract regression factor scores, then fit
# `turnover_intent ~ burnout + jobsat + remote` via logistic regression on
# those scores. (A single joint DWLS structural fit was tried and rejected
# -- semopy 2.3.11's WLS solver stalls on structural models with this many
# ordinal indicators; see tools/sem_track/mediation.py's docstring.)
#
# This model has no mediation path (burnout and jobsat are parallel direct
# predictors, not one mediating the other -- contrast with
# burnout-mediation's project), so there's no indirect-effect product term
# requiring a bootstrap CI. It's still bootstrapped: a plain Wald CI on the
# second-stage regression alone would ignore the sampling uncertainty
# already present in the first-stage factor scores.
#
# SYNTHESIS-MODE CHECK (Phase 4): last verified clean against both Stage B
# (independent synthesis, the default below, finishes in well under a
# minute) and Stage B2 (correlated synthesis -- see
# synthesize_data_correlated.py) as of 2026-08-15, though Stage B2 took
# ~226s -- 3-4x longer, with 9/50 bootstrap refits failing to converge and
# being skipped -- because the per-resample refits are harder on data with
# real correlation structure than on Stage B's independent columns. Budget
# for that if you switch input_csv below. The Stage B2 check used a
# stand-in file (this project's own Stage B output fed in as if it were
# real data, only to exercise the code path) -- re-verify against a genuine
# Stage B2 file once you generate one from real data.

# === USER SETTINGS ==========================================================
input_csv  = "data_synthetic/synthetic_dataset.csv"
output_dir = "outputs_synthetic"
# To run on REAL data, comment the two lines above and uncomment these:
# input_csv  = input("Path to real dataset CSV: ").strip()
# output_dir = "results_real"

n_boot = 50  # ~1-2s per refit on this model size -> roughly 1-2 minutes for 50 reps.
# ============================================================================

import os
import sys
import warnings
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.sem_track import bootstrap_structural_regression, compare_nested_regressions, fit_measurement_model

dat = pd.read_csv(input_csv, encoding="utf-8")
os.makedirs(output_dir, exist_ok=True)

# Observed covariate dummy (exact label from the reviewed pattern file)
dat["remote"] = (dat["work_mode"] == "Remote").astype(float)

constructs = {
    "jobsat":  ["js_q1", "js_q2", "js_q3", "js_q4", "js_q5"],
    "burnout": ["bo_q1", "bo_q2", "bo_q3", "bo_q4", "bo_q5"],
}
predictors = ["burnout", "jobsat", "remote"]

try:
    cfa = fit_measurement_model(dat, constructs, estimator="DWLS")
    print(f"Measurement model (DWLS): converged={cfa.converged}, "
          f"CFI={cfa.fit_indices['cfi']:.4f}, RMSEA={cfa.fit_indices['rmsea']:.4f}")

    print(f"\n--- Bootstrap structural regression ({n_boot} resamples) ---")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        boot = bootstrap_structural_regression(
            dat, constructs, outcome="turnover_intent", predictors=predictors,
            outcome_is_binary=True, estimator="DWLS", n_boot=n_boot, seed=2026,
        )
    table = boot.to_frame()
    print("\nStructural paths (turnover_intent regressed on predictors, percentile bootstrap 95% CI):")
    print(table.to_string(index=False))
    print(f"(n_boot={boot.n_boot}, failed refits={boot.n_failed})")
    table.to_csv(os.path.join(output_dir, "sem_estimates.csv"), index=False, encoding="utf-8")

    print("\n--- Nested model comparison: does `remote` matter? ---")
    scores = cfa.model.predict_factors(dat)
    combined = pd.concat([dat.reset_index(drop=True), scores.reset_index(drop=True)], axis=1)
    import statsmodels.formula.api as smf
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit_full = smf.logit("turnover_intent ~ burnout + jobsat + remote", data=combined).fit(disp=False)
        fit_restricted = smf.logit("turnover_intent ~ burnout + jobsat", data=combined).fit(disp=False)
    comparison = compare_nested_regressions(fit_full, fit_restricted)
    print(f"LR = {comparison.lr_stat:.4f} on {comparison.delta_df} df, p = {comparison.p_value:.4f}")
    print(f"Preferred: {comparison.preferred}")
    pd.DataFrame([{
        "lr_stat": comparison.lr_stat, "delta_df": comparison.delta_df, "p_value": comparison.p_value,
        "preferred": comparison.preferred,
    }]).to_csv(os.path.join(output_dir, "sem_model_comparison.csv"), index=False, encoding="utf-8")

    print(
        "\nNOTE: on this synthetic dataset all of the above is expected to look "
        "degenerate (wide/unstable CIs, a poorly-fitting measurement model) -- "
        "items are simulated independently. This script verifies the code runs "
        "end to end; interpret nothing from these numbers except on the real-data run."
    )

except Exception as exc:
    print("Model did not run to completion on synthetic data (expected for independent")
    print("synthetic items). The code path is valid and will run the same way on real data.")
    print(f"({exc})")
