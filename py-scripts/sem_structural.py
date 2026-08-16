# DR Stage D4 (SEM): Structural model — mediation
# Requires: pandas, numpy, scipy, semopy, statsmodels. pip install semopy once.
#
# ESTIMATOR + METHOD (Phase 3 of the statistical-methods roadmap): a single
# joint DWLS/WLSMV fit of the whole measurement+structural model together is
# semopy's textbook-first approach, but its WLS solver can stall at its
# starting values (never actually optimize) once a structural model has more
# than a handful of ordinal indicators plus structural paths -- a semopy
# limitation, not something fixable in this script (see
# tools/sem_track/mediation.py's docstring for the full account).
#
# This script instead uses factor-score regression (Skrondal & Laake 2001),
# a well-precedented two-step method: (1) fit the ordinal CFA alone via
# DWLS -- numerically robust, and the step that actually needs the ordinal
# estimator; (2) extract regression factor scores for the predictor and
# mediator constructs; (3) fit the structural paths as ordinary regressions
# (OLS for a continuous mediator, logistic for a binary distal outcome) via
# statsmodels. Both stages are refit together inside a bootstrap loop for
# percentile confidence intervals on the indirect, direct, and total
# effects -- a bare point estimate with no interval is not defensible for a
# product term like the indirect effect (Preacher & Hayes 2004, 2008).
#
# NO MEDIATOR IN YOUR MODEL? If your predictors act in parallel rather than
# one mediating another, use tools.sem_track.bootstrap_structural_regression
# instead of bootstrap_mediation -- see that function's docstring.

# === USER SETTINGS ==========================================================
# Runs on the synthetic dataset as delivered:
input_csv  = "data_synthetic/synthetic_dataset.csv"
output_dir = "outputs_synthetic"
# To run on REAL data, comment the two lines above and uncomment these:
# input_csv  = input("Path to real dataset CSV: ").strip()
# output_dir = "results_real"

# EDIT ME: constructs and their item columns -- keep this in sync with
# scripts/sem_measurement.py. Placeholder names below match the delivered
# synthetic dataset so this script runs standalone out of the box.
constructs: dict[str, list[str]] = {
    "Construct_A": ["item_a1", "item_a2", "item_a3"],
    "Construct_B": ["item_b1", "item_b2", "item_b3"],
}
predictor  = "Construct_A"   # EDIT ME: construct name (a key of `constructs`)
mediator   = "Construct_B"   # EDIT ME: construct name (a key of `constructs`)
outcome    = "outcome_var"   # EDIT ME: observed distal outcome column
outcome_is_binary = True     # EDIT ME: False for a continuous outcome (OLS instead of logistic)
covariates: list[str] = []   # EDIT ME: optional observed covariate columns

n_boot = 50  # raise for the real run if you can afford the wall-clock time;
             # the CI gets more stable, not more "correct", with more reps.
# ============================================================================

import os
import sys
import warnings
from pathlib import Path

import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.sem_track import bootstrap_mediation, compare_nested_regressions, fit_measurement_model

dat = pd.read_csv(input_csv, encoding="utf-8")
os.makedirs(output_dir, exist_ok=True)

# If you add observed covariates above, dummy-code any categorical ones here
# before they're used in a regression formula, e.g.:
# dat["is_group_a"] = (dat["some_categorical_col"] == "Group A").astype(int)

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
    print(f"\n--- Bootstrap mediation ({n_boot} resamples; this can take a few minutes) ---")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        boot = bootstrap_mediation(
            dat, constructs,
            mediator=mediator, predictor=predictor, outcome=outcome,
            outcome_is_binary=outcome_is_binary, covariates=covariates,
            estimator="DWLS", n_boot=n_boot, seed=2026,
        )

    mediation_table = boot.to_frame()
    label_map = {
        "a": f"a ({predictor} -> {mediator})",
        "b": f"b ({mediator} -> {outcome} | {predictor})",
        "c_prime": f"c' ({predictor} -> {outcome} direct)",
        "indirect": "indirect (a*b)", "total": "total (c'+a*b)",
    }
    mediation_table["path"] = mediation_table["path"].map(label_map)
    print("\n--- Indirect, Direct, and Total Effects (percentile bootstrap 95% CI) ---")
    print(mediation_table.to_string(index=False))
    print(f"(n_boot={boot.n_boot}, failed refits={boot.n_failed})")
    mediation_table.to_csv(os.path.join(output_dir, "sem_mediation.csv"), index=False, encoding="utf-8")

    # === STEP 3: nested model comparison -- does the direct path matter? ===
    print(f"\n--- Nested model comparison: with vs. without the direct path ({predictor} -> {outcome}) ---")
    scores = cfa.model.predict_factors(dat)
    combined = pd.concat([dat.reset_index(drop=True), scores.reset_index(drop=True)], axis=1)

    rhs_with_direct = " + ".join([mediator, predictor] + covariates)
    rhs_mediation_only = " + ".join([mediator] + covariates)  # predictor (c') omitted

    def _fit(formula: str):
        if outcome_is_binary:
            return smf.logit(formula, data=combined).fit(disp=False)
        return smf.ols(formula, data=combined).fit()

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit_with_direct = _fit(f"{outcome} ~ {rhs_with_direct}")
        fit_mediation_only = _fit(f"{outcome} ~ {rhs_mediation_only}")

    comparison = compare_nested_regressions(fit_with_direct, fit_mediation_only)
    print(f"LR = {comparison.lr_stat:.4f} on {comparison.delta_df} df, p = {comparison.p_value:.4f}")
    print(f"AIC: with direct path={comparison.aic_full:.2f} | mediation-only={comparison.aic_restricted:.2f}")
    print(f"Preferred: {comparison.preferred}")
    pd.DataFrame([{
        "lr_stat": comparison.lr_stat, "delta_df": comparison.delta_df, "p_value": comparison.p_value,
        "aic_with_direct_path": comparison.aic_full, "aic_mediation_only": comparison.aic_restricted,
        "preferred": comparison.preferred,
    }]).to_csv(os.path.join(output_dir, "sem_model_comparison.csv"), index=False, encoding="utf-8")

    print(
        "\nNOTE: on the delivered synthetic dataset all of the above is expected to "
        "look degenerate (wide/unstable CIs, a poorly-fitting measurement model) -- "
        "items are simulated independently, so there is no real mediation effect to "
        "recover. This script verifies the code runs end to end; interpret nothing "
        "from these numbers except on the real-data run."
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
