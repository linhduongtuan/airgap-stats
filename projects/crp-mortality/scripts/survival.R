# DR Stage D3/D4 (extension): Time-to-event analysis (Phase 2 of the
# statistical-methods roadmap)
# Requires the `survival` package -- bundled with every R installation
# (it ships as a "recommended" package, the same tier as `MASS`), so this
# never needs install.packages() in practice; not a base-R primitive
# (no coxph()/survfit() in base `stats`), which is why it's named
# explicitly here rather than silently assumed like everything else in
# this project's R scripts.
#
# WHY THIS SCRIPT EXISTS
# scripts/infer.R dichotomizes the outcome at a fixed 30-day window
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
# better time column exists. See plans/sap.md. Python equivalent:
# scripts/survival.py, tools/medical_track/survival.py.

# === USER SETTINGS ==========================================================
input_csv  <- "data_synthetic/synthetic_dataset.csv"
output_dir <- "outputs_synthetic"
# To run on REAL data in RStudio, comment the two lines above and uncomment these:
# input_csv  <- file.choose()   # a file-picker opens: select your real dataset
# output_dir <- "results_real"

time_col  <- "length_of_stay"   # PROXY time-to-event column -- see caveat above
event_col <- "mortality_30day"  # 1 = event (death), 0 = censored
group_col <- "treatment"        # stratify the Kaplan-Meier curves by this
covariate_vars <- c(             # same adjustment set as scripts/infer.R, for comparability
  "crp", "age", "sex", "bmi", "treatment", "sbp",
  "diabetes", "hypertension", "smoking",
  "egfr", "hba1c", "complication"
)
# ============================================================================

library(survival)

dat <- read.csv(input_csv, stringsAsFactors = FALSE, fileEncoding = "UTF-8")
dir.create(output_dir, showWarnings = FALSE)

required_cols <- c(time_col, event_col, group_col, covariate_vars)
missing_cols <- setdiff(required_cols, names(dat))
if (length(missing_cols) > 0) stop("Missing columns: ", paste(missing_cols, collapse = ", "))

# --- Set factor references to match scripts/infer.R ---
dat$sex       <- factor(dat$sex,       levels = c("Nữ", "Nam"))
dat$treatment <- factor(dat$treatment, levels = c("Phác đồ A", "Phác đồ B"))

cat(sprintf("Time column: %s (PROXY -- see caveat at the top of this script)\n", time_col))
cat(sprintf("Event column: %s | N = %d | events = %d\n", event_col, nrow(dat), sum(dat[[event_col]])))

# === PART 1: KAPLAN-MEIER =====================================================
cat(sprintf("\n=== KAPLAN-MEIER, stratified by %s ===\n", group_col))

km_formula <- as.formula(sprintf("Surv(%s, %s) ~ %s", time_col, event_col, group_col))
km_fit <- survfit(km_formula, data = dat)
km_summary <- summary(km_fit)

# Split the pooled summary back out per stratum (survfit()'s `strata`
# vector is parallel to every other column) and write one CSV per group,
# matching the Python port's per-group file naming exactly.
strata_labels <- if (!is.null(km_summary$strata)) {
  sub(paste0("^", group_col, "="), "", as.character(km_summary$strata))
} else {
  rep(group_col, length(km_summary$time))  # only happens with a single stratum
}
km_table_all <- data.frame(
  Time = km_summary$time,
  `Surv prob` = km_summary$surv,
  `Surv prob SE` = km_summary$std.err,
  `num at risk` = km_summary$n.risk,
  `num events` = km_summary$n.event,
  check.names = FALSE
)

# Median survival time per group (NA = not reached within follow-up).
median_table <- summary(km_fit)$table
median_col <- if (is.matrix(median_table)) median_table[, "median"] else median_table["median"]
median_names <- if (is.matrix(median_table)) sub(paste0("^", group_col, "="), "", rownames(median_table)) else group_col

for (label in unique(strata_labels)) {
  rows <- km_table_all[strata_labels == label, , drop = FALSE]
  med <- median_col[median_names == label]
  med_str <- if (length(med) == 1 && !is.na(med)) sprintf("%.1f", med) else "not reached"
  cat(sprintf("  %s=%s: n=%d steps, median survival time = %s\n", group_col, label, nrow(rows), med_str))
  out_path <- file.path(output_dir, sprintf("survival_km_%s.csv", gsub(" ", "_", label)))
  write.csv(rows, out_path, row.names = FALSE, fileEncoding = "UTF-8")
}

if (length(unique(dat[[group_col]])) >= 2) {
  logrank <- survdiff(km_formula, data = dat)
  logrank_p <- 1 - pchisq(logrank$chisq, length(logrank$n) - 1)
  cat(sprintf("\nLog-rank test across %s groups: chi2 = %.4f, p = %.4f\n", group_col, logrank$chisq, logrank_p))
} else {
  cat("\nLog-rank test not computed (fewer than 2 groups with data).\n")
}

# === PART 2: COX PROPORTIONAL HAZARDS =========================================
cox_formula <- as.formula(sprintf("Surv(%s, %s) ~ %s", time_col, event_col, paste(covariate_vars, collapse = " + ")))
cat("\n=== COX PROPORTIONAL HAZARDS ===\n")
cat("Formula:", deparse(cox_formula), "\n")

# NOTE on parity: coxph()'s default tie-handling is Efron's method;
# statsmodels' PHReg (tools/medical_track/survival.py) defaults to Breslow's.
# Efron is the more accurate approximation and R's own default for good
# reason -- kept here rather than downgrading to `ties = "breslow"` just to
# match Python bit-for-bit. Confirmed during development that switching to
# `ties = "breslow"` reproduces the Python coefficients exactly, so this is
# a known, well-documented cross-software default difference (like DFBETAs
# in scripts/infer.R), not a bug -- expect small (not qualitative)
# coefficient differences between the two languages' output on tied data.
cox_fit <- coxph(cox_formula, data = dat)
cox_coef <- summary(cox_fit)$coefficients   # coef, exp(coef), se(coef), z, Pr(>|z|)
cox_ci <- confint(cox_fit)                  # log-HR CI

cox_table <- data.frame(
  term = rownames(cox_coef),
  log_hr = round(cox_coef[, "coef"], 4),
  hr = round(cox_coef[, "exp(coef)"], 4),
  ci_low = round(exp(cox_ci[, 1]), 4),
  ci_high = round(exp(cox_ci[, 2]), 4),
  p_value = round(cox_coef[, "Pr(>|z|)"], 4),
  row.names = NULL
)

cat(sprintf("N = %d | events = %d\n", cox_fit$n, cox_fit$nevent))
print(cox_table, row.names = FALSE)

cox_path <- file.path(output_dir, "survival_cox_ph.csv")
write.csv(cox_table, cox_path, row.names = FALSE, fileEncoding = "UTF-8")
cat("\nCox PH results written to", cox_path, "\n")

cat(
  "\nNOTE: on this synthetic dataset, results are meaningless by design ",
  "(columns are simulated independently, and length_of_stay is not a ",
  "confirmed true time-to-event column even conceptually). This script ",
  "verifies the code runs; interpret nothing from these numbers. On real ",
  "data, confirm the time column with the user before reporting this ",
  "analysis (see the caveat at the top of this file).\n", sep = ""
)
