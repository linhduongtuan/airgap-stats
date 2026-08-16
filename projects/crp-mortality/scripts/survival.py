# DR Stage D3/D4 (extension): Time-to-event analysis (Phase 2 of the
# statistical-methods roadmap)
# Requires: pandas, numpy, statsmodels. Run from the project folder.
#
# WHY THIS SCRIPT EXISTS
# scripts/infer.py dichotomizes the outcome at a fixed 30-day window
# (mortality_30day: 0/1). That throws away information a genuine
# time-to-event analysis would use -- two patients who both died within 30
# days are treated identically whether death came on day 2 or day 29.
#
# CAVEAT -- CONFIRM BEFORE TRUSTING THIS ON REAL DATA
# There is no dedicated "time to death or censoring" column in this
# dataset. This script uses `length_of_stay` as the survival time, which is
# a plausible but NOT confirmed proxy (it measures hospital stay duration,
# which is *correlated* with time-to-death for patients who die in-hospital,
# but is not the same thing, and says nothing about patients discharged
# alive and lost to longer-term follow-up). Do not report this as if it
# were a true time-to-death analysis without the user confirming what
# `length_of_stay` actually represents for the real cohort, and whether a
# better time column exists. See plans/sap.md.
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

time_col  = "length_of_stay"   # PROXY time-to-event column -- see caveat above
event_col = "mortality_30day"  # 1 = event (death), 0 = censored
group_col = "treatment"        # stratify the Kaplan-Meier curves by this
covariate_vars = [              # same adjustment set as scripts/infer.py, for comparability
    "crp", "age", "sex", "bmi", "treatment", "sbp",
    "diabetes", "hypertension", "smoking",
    "egfr", "hba1c", "complication",
]
# ============================================================================

import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.medical_track import cox_ph, kaplan_meier

dat = pd.read_csv(input_csv, encoding="utf-8")
os.makedirs(output_dir, exist_ok=True)

missing_cols = [v for v in [time_col, event_col, group_col] + covariate_vars if v not in dat.columns]
if missing_cols:
    raise ValueError(f"Missing columns: {', '.join(missing_cols)}")

# --- Set factor references to match scripts/infer.py ---
dat["sex"]       = pd.Categorical(dat["sex"],       categories=["Nữ", "Nam"])
dat["treatment"] = pd.Categorical(dat["treatment"], categories=["Phác đồ A", "Phác đồ B"])

print(f"Time column: {time_col} (PROXY -- see caveat at the top of this script)")
print(f"Event column: {event_col} | N = {len(dat)} | events = {int(dat[event_col].sum())}")

# === PART 1: KAPLAN-MEIER =====================================================
print(f"\n=== KAPLAN-MEIER, stratified by {group_col} ===")
km = kaplan_meier(dat, time_col, event_col, group_col=group_col)

for label, curve in km.curves.items():
    median = km.median_survival[label]
    median_str = f"{median:.1f}" if median == median else "not reached"  # NaN check
    print(f"  {group_col}={label}: n={len(curve)} steps, median survival time = {median_str}")
    curve.to_csv(os.path.join(output_dir, f"survival_km_{label.replace(' ', '_')}.csv"), encoding="utf-8")

if km.logrank_p is not None:
    print(f"\nLog-rank test across {group_col} groups: chi2 = {km.logrank_stat:.4f}, p = {km.logrank_p:.4f}")
else:
    print("\nLog-rank test not computed (fewer than 2 groups with data).")

# === PART 2: COX PROPORTIONAL HAZARDS =========================================
rhs = " + ".join(f'Q("{v}")' for v in covariate_vars)
print(f"\n=== COX PROPORTIONAL HAZARDS ===")
print(f"Formula: {time_col} ~ {rhs} (status = {event_col})")

cox_result = cox_ph(dat, rhs, time_col, event_col)
print(f"N = {cox_result.nobs} | events = {cox_result.n_events}")
print(cox_result.table.to_string(index=False))

cox_path = os.path.join(output_dir, "survival_cox_ph.csv")
cox_result.table.to_csv(cox_path, index=False, encoding="utf-8")
print(f"\nCox PH results written to {cox_path}")

print(
    "\nNOTE: on this synthetic dataset, results are meaningless by design "
    "(columns are simulated independently, and length_of_stay is not a "
    "confirmed true time-to-event column even conceptually). This script "
    "verifies the code runs; interpret nothing from these numbers. On real "
    "data, confirm the time column with the user before reporting this "
    "analysis (see the caveat at the top of this file)."
)
