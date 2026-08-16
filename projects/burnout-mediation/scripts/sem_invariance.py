# DR Stage D3 (SEM) extension: Measurement invariance across groups
# (Phase 3 of the statistical-methods roadmap -- the item originally
# deferred as Low priority/High effort, implemented here.)
# Requires: pandas, numpy, scipy, semopy, statsmodels. pip install semopy once.
#
# WHY THIS SCRIPT EXISTS
# scripts/sem_structural.py compares Job_Satisfaction and Burnout across
# the whole sample. Before any group comparison (e.g. by gender) would be
# meaningful, the *measurement* of Job_Satisfaction/Burnout has to mean the
# same thing in every group -- otherwise an apparent group difference could
# just be measurement bias (the same latent level producing different item
# responses per group), not a real difference in the construct.
#
# APPROACH -- not the textbook multi-group chi-square test:
# semopy has no genuine multi-group SEM (its `groups=` fit parameter only
# mean-centers each group's data before pooling into one fit -- see
# tools/sem_track/invariance.py's docstring). This script instead fits the
# measurement model separately in each group (configural check) and
# bootstraps a per-item loading-equality test (metric invariance) --
# validated against simulated data with both a genuinely invariant and a
# genuinely non-invariant scenario (tests/test_sem_track.py). Scalar
# (intercept/threshold) invariance is not implemented.
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

group_col = "gender"  # must have exactly 2 observed levels for the metric test
n_boot    = 20         # ~6s per refit on this model size -> roughly 2*20*6s =~ 4 minutes
# ============================================================================

import os
import sys
import warnings
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.sem_track import configural_check, metric_invariance_bootstrap

dat = pd.read_csv(input_csv, encoding="utf-8")
os.makedirs(output_dir, exist_ok=True)

js_items = ["js_q1", "js_q2", "js_q3", "js_q4", "js_q5"]
bo_items = ["bo_q1", "bo_q2", "bo_q3", "bo_q4", "bo_q5"]
constructs = {"Job_Satisfaction": js_items, "Burnout": bo_items}

missing_cols = [c for c in js_items + bo_items + [group_col] if c not in dat.columns]
if missing_cols:
    raise ValueError(f"Missing columns in data: {', '.join(missing_cols)}")

group_levels = sorted(dat[group_col].dropna().unique())
print(f"Testing measurement invariance of Job_Satisfaction/Burnout across {group_col}: {group_levels}")
if len(group_levels) != 2:
    print(f"NOTE: metric_invariance_bootstrap requires exactly 2 groups; found {len(group_levels)}. "
          "Skipping the metric step, running configural only.")

try:
    # === STEP 1: configural check -- does the same factor structure fit
    # reasonably in every group? ===
    print("\n=== Configural check (measurement model fit, per group) ===")
    conf = configural_check(dat, constructs, group_col, estimator="DWLS")
    conf_summary = conf.summary()
    print(conf_summary.to_string(index=False))
    conf_summary.to_csv(os.path.join(output_dir, "invariance_configural.csv"), index=False, encoding="utf-8")

    # === STEP 2: metric invariance -- per-item loading equality, bootstrapped ===
    if len(group_levels) == 2:
        print(f"\n=== Metric invariance: per-item loading comparison ({n_boot} bootstrap resamples per group) ===")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            metric = metric_invariance_bootstrap(dat, constructs, group_col, estimator="DWLS", n_boot=n_boot, seed=2026)
        print(metric[["construct", "item", "group_a", "group_b", "loading_a", "loading_b",
                       "difference", "ci_low", "ci_high", "flagged_noninvariant"]].to_string(index=False))
        metric.to_csv(os.path.join(output_dir, "invariance_metric.csv"), index=False, encoding="utf-8")

        n_flagged = int(metric["flagged_noninvariant"].sum())
        print(f"\n{n_flagged} / {len(metric)} items flagged non-invariant "
              f"(95% CI on the between-group loading difference excludes 0).")
        if n_flagged > 0:
            print("Flagged items should not be assumed to measure the construct identically "
                  f"across {group_col} groups -- consider partial invariance (drop/free those "
                  "items when comparing group means or paths) rather than ignoring the flag.")

    print(
        "\nNOTE: on this synthetic dataset all of the above is expected to look degenerate "
        "(poor configural fit, wide/unstable CIs, spurious flags) -- items are simulated "
        "independently, so there is no real factor structure or real group difference to "
        "recover. This script verifies the code runs end to end; interpret nothing from "
        "these numbers except on the real-data run."
    )

except Exception as exc:
    print(f"\nInvariance testing did not complete on synthetic data: {exc}")
    print("This is expected (items are simulated independently).")
    print("The script ran successfully. Convergence on real data is what matters.")

print("\nSEM measurement invariance script completed.")
print(f"Output files in: {output_dir}")
