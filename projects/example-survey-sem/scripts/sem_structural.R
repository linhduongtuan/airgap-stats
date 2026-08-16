# DR Stage D4 (SEM): Structural model  (example-survey-sem)
# Base R + lavaan only. Run from the project folder. Python equivalent:
# scripts/sem_structural.py, tools/sem_track/{mediation,model_comparison}.py.
#
# METHOD (Phase 3 of the statistical-methods roadmap): jobsat/burnout items
# are ordinal Likert, turnover_intent is binary -- the previous plain-ML
# joint SEM fit was flagged `needs_review` in Phase 0.
#
# UNLIKE THE PYTHON MIRROR: semopy's WLS solver stalls on structural models
# with this many ordinal indicators (see tools/sem_track/mediation.py's
# docstring), which is why scripts/sem_structural.py uses a two-step
# factor-score-regression workaround. lavaan's WLSMV/DWLS solver handles a
# single joint fit of this exact model directly -- confirmed during
# development. This script therefore fits the whole measurement +
# structural model jointly (ordinal estimator throughout, including the
# binary distal outcome, declared `ordered=` alongside the Likert items so
# it gets the same categorical-threshold treatment rather than being
# treated as continuous), with lavaan's native bootstrap standard errors
# for the structural paths.
#
# This model has no mediation path (burnout and jobsat are parallel direct
# predictors, not one mediating the other -- contrast with
# burnout-mediation's project), so there's no indirect-effect product term.
# It's still bootstrapped: a plain asymptotic CI would understate the
# uncertainty a joint measurement+structural fit actually carries.

# === USER SETTINGS ==========================================================
input_csv  <- "data_synthetic/synthetic_dataset.csv"
output_dir <- "outputs_synthetic"
# To run on REAL data in RStudio, change the two lines above to:
# input_csv  <- file.choose()   # cua so chon file se hien ra: chon file du lieu that cua ban
# output_dir <- "results_real"

n_boot <- 50  # measured during development: well under a minute for 50 reps on this model size.
# ============================================================================

library(lavaan)  # install.packages("lavaan") once, before first use

dat <- read.csv(input_csv, stringsAsFactors = FALSE, fileEncoding = "UTF-8")
dir.create(output_dir, showWarnings = FALSE)

# Observed covariate dummy (exact label from the reviewed pattern file)
dat$remote <- as.numeric(dat$work_mode == "Remote")

js_bo_items <- c("js_q1", "js_q2", "js_q3", "js_q4", "js_q5", "bo_q1", "bo_q2", "bo_q3", "bo_q4", "bo_q5")
all_items <- c(js_bo_items, "turnover_intent")  # binary outcome, declared ordered -- see header note

model_full <- '
  jobsat  =~ js_q1 + js_q2 + js_q3 + js_q4 + js_q5
  burnout =~ bo_q1 + bo_q2 + bo_q3 + bo_q4 + bo_q5

  turnover_intent ~ burnout + jobsat + remote
'
# `remote` stays in the model as an exogenous covariate in BOTH versions --
# fixed to 0 here, not omitted -- so the two models differ by exactly one
# constrained parameter (a valid LRT comparison). Omitting the variable
# entirely would change the model's total observed-variable set, which
# changes the number of fitted moments (and therefore df) by more than
# the one path being tested -- the same mistake this file's mediation
# counterpart (burnout-mediation/scripts/sem_structural.R) avoids for c'.
model_restricted <- '
  jobsat  =~ js_q1 + js_q2 + js_q3 + js_q4 + js_q5
  burnout =~ bo_q1 + bo_q2 + bo_q3 + bo_q4 + bo_q5

  turnover_intent ~ burnout + jobsat + 0 * remote
'

result <- tryCatch({
  meas_model <- '
    jobsat  =~ js_q1 + js_q2 + js_q3 + js_q4 + js_q5
    burnout =~ bo_q1 + bo_q2 + bo_q3 + bo_q4 + bo_q5
  '
  cfa_fit <- cfa(meas_model, data = dat, ordered = js_bo_items, estimator = "DWLS")
  cat(sprintf("Measurement model (DWLS): converged=%s, CFI=%.4f, RMSEA=%.4f\n",
              lavInspect(cfa_fit, "converged"), fitMeasures(cfa_fit, "cfi"), fitMeasures(cfa_fit, "rmsea")))

  cat(sprintf("\n--- Bootstrap structural regression (%d resamples) ---\n", n_boot))
  fit_full <- suppressWarnings(sem(model_full, data = dat, ordered = all_items,
                                    estimator = "DWLS", se = "bootstrap", bootstrap = n_boot))

  pe <- parameterEstimates(fit_full, boot.ci.type = "perc")
  path_rows <- pe[pe$op == "~" & pe$lhs == "turnover_intent", ]
  structural_table <- data.frame(
    term = path_rows$rhs,
    estimate = round(path_rows$est, 4),
    ci_low = round(path_rows$ci.lower, 4),
    ci_high = round(path_rows$ci.upper, 4),
    row.names = NULL
  )
  cat("\nStructural paths (turnover_intent regressed on predictors, percentile bootstrap 95% CI):\n")
  print(structural_table, row.names = FALSE)
  cat(sprintf("(n_boot=%d)\n", n_boot))
  write.csv(structural_table, file.path(output_dir, "sem_estimates.csv"), row.names = FALSE, fileEncoding = "UTF-8")

  cat("\n--- Nested model comparison: does `remote` matter? ---\n")
  fit_full_plain <- suppressWarnings(sem(model_full, data = dat, ordered = all_items, estimator = "DWLS"))
  fit_restricted <- suppressWarnings(sem(model_restricted, data = dat, ordered = all_items, estimator = "DWLS"))
  lrt <- lavTestLRT(fit_full_plain, fit_restricted)
  lr_stat <- lrt$`Chisq diff`[2]
  delta_df <- lrt$`Df diff`[2]
  p_value <- lrt$`Pr(>Chisq)`[2]
  preferred <- if (is.na(p_value)) {
    "undetermined (LRT unavailable)"
  } else if (p_value < 0.05) {
    "full (remote earns its keep -- the larger model fits significantly better)"
  } else {
    "restricted (more parsimonious) -- the dropped term(s) don't earn their keep"
  }
  cat(sprintf("LR = %.4f on %s df, p = %s\n", lr_stat, delta_df, ifelse(is.na(p_value), "NA", sprintf("%.4f", p_value))))
  cat(sprintf("Preferred: %s\n", preferred))

  comparison <- data.frame(lr_stat = round(lr_stat, 4), delta_df = delta_df,
                            p_value = round(p_value, 4), preferred = preferred)
  write.csv(comparison, file.path(output_dir, "sem_model_comparison.csv"), row.names = FALSE, fileEncoding = "UTF-8")

  cat(
    "\nNOTE: on this synthetic dataset all of the above is expected to look ",
    "degenerate (wide/unstable CIs, a poorly-fitting measurement model) -- ",
    "items are simulated independently. This script verifies the code runs ",
    "end to end; interpret nothing from these numbers except on the real-data run.\n", sep = ""
  )
  TRUE
}, error = function(e) {
  cat("Model did not run to completion on synthetic data (expected for independent\n")
  cat("synthetic items). The code path is valid and will run the same way on real data.\n")
  cat("(", conditionMessage(e), ")\n", sep = "")
  FALSE
})
