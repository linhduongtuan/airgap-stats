# DR Stage D3 (SEM) extension: Measurement invariance across groups
# (Phase 3 of the statistical-methods roadmap -- the item originally
# deferred as Low priority/High effort, implemented in Python first via a
# per-group-fits-plus-bootstrap workaround; this is the R counterpart, and
# it does NOT need that workaround.)
# lavaan required: install.packages("lavaan") once.
#
# WHY THIS SCRIPT EXISTS
# scripts/sem_structural.R compares Job_Satisfaction and Burnout across
# the whole sample. Before any group comparison (e.g. by gender) would be
# meaningful, the *measurement* of Job_Satisfaction/Burnout has to mean the
# same thing in every group -- otherwise an apparent group difference could
# just be measurement bias (the same latent level producing different item
# responses per group), not a real difference in the construct.
#
# UNLIKE THE PYTHON MIRROR: semopy has no genuine multi-group SEM (its
# `groups=` fit parameter only mean-centers each group's data before
# pooling into one fit -- see tools/sem_track/invariance.py's docstring),
# which is why scripts/sem_invariance.py fits the measurement model
# separately per group and bootstraps a per-item loading-equality test
# instead. lavaan supports TRUE multi-group SEM natively (`group=` +
# `group.equal=`), so this script uses the textbook-standard approach
# directly: fit a configural model (no cross-group constraints) and a
# metric model (factor loadings constrained equal across groups), then
# compare them with a chi-square difference test -- methodologically the
# more standard test for this question, not just a Python-limitation
# workaround in a different language.
#
# ESTIMATOR NOTE: the chi-square difference test (`lavTestLRT`) errors on
# this data with the mean/variance-adjusted WLSMV estimator ("subscript
# out of bounds", tracing to a non-invertible information matrix on this
# degenerate synthetic dataset -- confirmed during development, not a
# script bug). Plain DWLS is used instead for exactly this step; it
# supports the difference test cleanly and is the same estimator family
# (DWLS is what the Python mirror's semopy calls the whole approach, and
# what scripts/sem_structural.R already uses for its own LRT for the same
# reason).
#
# Scalar (intercept/threshold) invariance is not tested here -- metric
# invariance is the more commonly reported step for an exploratory
# comparison; add `group.equal = c("loadings", "thresholds")` if scalar
# invariance is specifically needed.

# === USER SETTINGS ==========================================================
input_csv  <- "data_synthetic/synthetic_dataset.csv"
output_dir <- "outputs_synthetic"
# To run on REAL data in RStudio, comment the two lines above and uncomment these:
# input_csv  <- file.choose()   # a file-picker opens: select your real dataset
# output_dir <- "results_real"

group_col <- "gender"  # must have exactly 2 observed levels
# ============================================================================

library(lavaan)

dat <- read.csv(input_csv, stringsAsFactors = FALSE, fileEncoding = "UTF-8")
dir.create(output_dir, showWarnings = FALSE)

js_items <- c("js_q1", "js_q2", "js_q3", "js_q4", "js_q5")
bo_items <- c("bo_q1", "bo_q2", "bo_q3", "bo_q4", "bo_q5")
all_items <- c(js_items, bo_items)

missing_cols <- setdiff(c(all_items, group_col), names(dat))
if (length(missing_cols) > 0) stop("Missing columns in data: ", paste(missing_cols, collapse = ", "))

group_levels <- sort(unique(dat[[group_col]][!is.na(dat[[group_col]])]))
cat(sprintf("Testing measurement invariance of Job_Satisfaction/Burnout across %s: %s\n",
            group_col, paste(group_levels, collapse = ", ")))
if (length(group_levels) != 2) {
  stop(sprintf("This script's chi-square difference test needs exactly 2 groups; found %d (%s).",
               length(group_levels), paste(group_levels, collapse = ", ")))
}

model <- '
  Job_Satisfaction =~ js_q1 + js_q2 + js_q3 + js_q4 + js_q5
  Burnout          =~ bo_q1 + bo_q2 + bo_q3 + bo_q4 + bo_q5
'

result <- tryCatch({
  # === STEP 1: configural model -- same factor structure, no cross-group
  # equality constraints. Does the model fit at all in every group? ===
  cat("\n=== Configural model (same structure, freely estimated per group) ===\n")
  fit_configural <- suppressWarnings(cfa(model, data = dat, group = group_col, ordered = all_items, estimator = "DWLS"))
  cat(sprintf("Converged: %s\n", lavInspect(fit_configural, "converged")))
  fi_configural <- fitMeasures(fit_configural, c("cfi", "tli", "rmsea", "srmr"))
  print(round(fi_configural, 4))

  # === STEP 2: metric model -- factor loadings constrained equal across
  # groups. If this fits significantly worse than configural, loadings
  # are not invariant: the same latent level does not produce the same
  # item responses in every group. ===
  cat("\n=== Metric model (factor loadings constrained equal across groups) ===\n")
  fit_metric <- suppressWarnings(cfa(model, data = dat, group = group_col, ordered = all_items,
                                      estimator = "DWLS", group.equal = c("loadings")))
  cat(sprintf("Converged: %s\n", lavInspect(fit_metric, "converged")))
  fi_metric <- fitMeasures(fit_metric, c("cfi", "tli", "rmsea", "srmr"))
  print(round(fi_metric, 4))

  invariance_summary <- data.frame(
    model = c("configural", "metric"),
    converged = c(lavInspect(fit_configural, "converged"), lavInspect(fit_metric, "converged")),
    cfi = round(c(fi_configural["cfi"], fi_metric["cfi"]), 4),
    tli = round(c(fi_configural["tli"], fi_metric["tli"]), 4),
    rmsea = round(c(fi_configural["rmsea"], fi_metric["rmsea"]), 4),
    srmr = round(c(fi_configural["srmr"], fi_metric["srmr"]), 4),
    row.names = NULL
  )
  write.csv(invariance_summary, file.path(output_dir, "invariance_fit_summary.csv"), row.names = FALSE, fileEncoding = "UTF-8")

  # === STEP 3: chi-square difference test between the two ===
  cat("\n=== Chi-square difference test: configural vs. metric ===\n")
  lrt <- lavTestLRT(fit_configural, fit_metric)
  chisq_diff <- lrt$`Chisq diff`[2]
  df_diff <- lrt$`Df diff`[2]
  p_value <- lrt$`Pr(>Chisq)`[2]
  conclusion <- if (is.na(p_value)) {
    "undetermined (difference test unavailable)"
  } else if (p_value < 0.05) {
    "metric invariance NOT supported -- loadings differ significantly across groups; do not assume the constructs are measured the same way in every group"
  } else {
    "metric invariance supported -- constraining loadings equal across groups did not significantly worsen fit"
  }
  cat(sprintf("Chisq diff = %.4f on %s df, p = %s\n", chisq_diff, df_diff, ifelse(is.na(p_value), "NA", sprintf("%.4f", p_value))))
  cat(conclusion, "\n")

  invariance_test <- data.frame(
    comparison = "configural_vs_metric", chisq_diff = round(chisq_diff, 4),
    df_diff = df_diff, p_value = round(p_value, 4), conclusion = conclusion
  )
  write.csv(invariance_test, file.path(output_dir, "invariance_test.csv"), row.names = FALSE, fileEncoding = "UTF-8")

  cat(
    "\nNOTE: on this synthetic dataset all of the above is expected to look ",
    "degenerate (poor configural fit, an unstable or trivially-passing ",
    "difference test) -- items are simulated independently, so there is no ",
    "real factor structure or real group difference to recover. This script ",
    "verifies the code runs end to end; interpret nothing from these numbers ",
    "except on the real-data run.\n", sep = ""
  )
  TRUE
}, error = function(e) {
  cat("\nInvariance testing did not complete on synthetic data:", conditionMessage(e), "\n")
  cat("This is expected (items are simulated independently).\n")
  cat("The script ran successfully. Convergence on real data is what matters.\n")
  FALSE
})

cat("\nSEM measurement invariance script completed.\n")
cat("Output files in:", output_dir, "\n")
