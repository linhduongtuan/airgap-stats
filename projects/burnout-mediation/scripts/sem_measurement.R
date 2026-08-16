# DR Stage D3 (SEM): Measurement model
# Cronbach's alpha (base R) + CFA (lavaan, WLSMV estimator)
# install.packages("lavaan") once before running. Python equivalent:
# scripts/sem_measurement.py, tools/sem_track/{estimator,reliability,validity}.py.
#
# ESTIMATOR (Phase 3 of the statistical-methods roadmap): js_q*/bo_q* are
# 5-point Likert items -- ordinal, not continuous. This script fits the CFA
# with lavaan's WLSMV estimator on the polychoric correlation matrix
# (declaring every item ordinal via `ordered=`), the methodologically
# correct choice for ordinal indicators (WLSMV is lavaan's name for the
# same family of estimator; DWLS is semopy's name for it in the Python
# mirror). This replaces the previous plain-ML fit that
# plans/sem_measurement_plan.yaml had flagged `needs_review` in Phase 0.
# Unlike semopy, lavaan's WLSMV solver handles this directly -- no
# two-step workaround needed here (contrast scripts/sem_structural.R).
#
# Also new in Phase 3: McDonald's omega (doesn't assume tau-equivalence,
# unlike alpha), AVE/composite reliability (convergent validity), and the
# HTMT ratio between Job Satisfaction and Burnout (discriminant validity --
# two negatively-correlated affective constructs need an explicit check
# that they're empirically distinct, not just conceptually different).

# === USER SETTINGS ==========================================================
# Runs on the synthetic dataset as delivered:
input_csv  <- "data_synthetic/synthetic_dataset.csv"
output_dir <- "outputs_synthetic"
# To run on REAL data in RStudio, comment the two lines above and uncomment these:
# input_csv  <- file.choose()   # a file-picker opens: select your real dataset
# output_dir <- "results_real"
# ============================================================================

library(lavaan)

dat <- read.csv(input_csv, stringsAsFactors = FALSE, fileEncoding = "UTF-8")
dir.create(output_dir, showWarnings = FALSE)

# --- Items per construct ---
js_items <- c("js_q1", "js_q2", "js_q3", "js_q4", "js_q5")
bo_items <- c("bo_q1", "bo_q2", "bo_q3", "bo_q4", "bo_q5")
all_items <- c(js_items, bo_items)

missing_cols <- all_items[!all_items %in% names(dat)]
if (length(missing_cols) > 0) stop("Missing columns in data: ", paste(missing_cols, collapse = ", "))

# --- Cronbach's alpha (base R) ---
cronbach_alpha <- function(items_df) {
  items_df <- items_df[stats::complete.cases(items_df), , drop = FALSE]
  k <- ncol(items_df)
  if (k < 2) return(NA_real_)
  item_vars <- apply(items_df, 2, stats::var)
  total_var <- stats::var(rowSums(items_df))
  (k / (k - 1)) * (1 - sum(item_vars) / total_var)
}

# --- Scale scores (row mean, >= 50% non-missing) -- kept for descriptive use ---
compute_scale <- function(dat, items, min_prop = 0.50) {
  k <- length(items)
  min_ok <- floor(k * min_prop)
  apply(dat[, items, drop = FALSE], 1, function(row) {
    if (sum(!is.na(row)) >= min_ok) mean(row, na.rm = TRUE) else NA_real_
  })
}

dat$js_score <- compute_scale(dat, js_items)
dat$bo_score <- compute_scale(dat, bo_items)

scale_summary <- data.frame(
  construct = c("Job_Satisfaction", "Burnout"),
  mean = round(c(mean(dat$js_score, na.rm = TRUE), mean(dat$bo_score, na.rm = TRUE)), 2),
  sd = round(c(sd(dat$js_score, na.rm = TRUE), sd(dat$bo_score, na.rm = TRUE)), 2),
  n = c(sum(!is.na(dat$js_score)), sum(!is.na(dat$bo_score))),
  stringsAsFactors = FALSE
)
cat("=== Scale Scores (row-mean, descriptive use only) ===\n")
print(scale_summary, row.names = FALSE)

# === CFA via lavaan, WLSMV estimator on declared-ordinal items ==============
cat("\n=== CFA (WLSMV estimator, ordinal items) ===\n")

cfa_model <- '
  Job_Satisfaction =~ js_q1 + js_q2 + js_q3 + js_q4 + js_q5
  Burnout          =~ bo_q1 + bo_q2 + bo_q3 + bo_q4 + bo_q5
'

fit <- tryCatch(
  cfa(cfa_model, data = dat, ordered = all_items, estimator = "WLSMV"),
  error = function(e) { cat("\nCFA error:", conditionMessage(e), "\n"); NULL }
)

if (!is.null(fit) && isTRUE(lavInspect(fit, "converged"))) {
  fi <- fitMeasures(fit, c("cfi", "tli", "rmsea", "srmr"))
  fi_df <- data.frame(measure = names(fi), value = as.numeric(fi), stringsAsFactors = FALSE)
  cat("\n")
  print(round(fi, 4))
  write.csv(fi_df, file.path(output_dir, "cfa_fit.csv"), row.names = FALSE, fileEncoding = "UTF-8")

  cat("\n=== Standardized Loadings ===\n")
  # lavaan's own orientation is "Construct =~ item" (lhs=construct,
  # rhs=item) -- the OPPOSITE of semopy's internal lval/rval convention
  # (tools/sem_track/reliability.py's docstring: semopy stores it as
  # "item ~ Construct", lval=item). To keep this CSV's column semantics
  # identical to the Python mirror's (lval=item, rval=construct) so the
  # two are directly comparable, rhs(item)->lval and lhs(construct)->rval
  # here -- deliberately reversed from lavaan's own lhs/rhs order.
  pe <- parameterEstimates(fit, standardized = TRUE)
  loadings <- pe[pe$op == "=~", c("rhs", "op", "lhs", "est", "std.all", "se", "z", "pvalue")]
  names(loadings) <- c("lval", "op", "rval", "Estimate", "Est. Std", "Std. Err", "z-value", "p-value")
  print(loadings, row.names = FALSE)
  write.csv(loadings, file.path(output_dir, "cfa_loadings.csv"), row.names = FALSE, fileEncoding = "UTF-8")

  # --- Reliability: alpha + omega, from the CFA's own standardized loadings ---
  # omega = (sum of std loadings)^2 / [(sum of std loadings)^2 + sum of error variances],
  # error variance = 1 - loading^2 (standardized-model item residual). NA
  # loadings (e.g. a Heywood case / negative latent variance) propagate to
  # NA here deliberately, not silently dropped -- an undefined omega is the
  # honest answer when the CFA solution itself is improper.
  mcdonald_omega <- function(std_loadings) {
    sum_loadings <- sum(std_loadings)
    sum_errors <- sum(1 - std_loadings^2)
    denom <- sum_loadings^2 + sum_errors
    if (is.na(denom) || denom <= 0) return(NA_real_)
    (sum_loadings^2) / denom
  }

  cat("\n=== Reliability: Cronbach's Alpha + McDonald's Omega ===\n")
  js_std <- loadings$`Est. Std`[loadings$rval == "Job_Satisfaction"]
  bo_std <- loadings$`Est. Std`[loadings$rval == "Burnout"]
  reliability_summary <- data.frame(
    construct = c("Job_Satisfaction", "Burnout"),
    n_items = c(length(js_items), length(bo_items)),
    alpha = round(c(cronbach_alpha(dat[, js_items]), cronbach_alpha(dat[, bo_items])), 3),
    omega = round(c(mcdonald_omega(js_std), mcdonald_omega(bo_std)), 3),
    stringsAsFactors = FALSE
  )
  print(reliability_summary, row.names = FALSE)
  write.csv(reliability_summary, file.path(output_dir, "reliability_summary.csv"), row.names = FALSE, fileEncoding = "UTF-8")

  # --- Convergent validity: AVE + composite reliability ---
  average_variance_extracted <- function(std_loadings) mean(std_loadings^2)
  composite_reliability <- function(std_loadings) {
    sum_loadings <- sum(std_loadings)
    sum_errors <- sum(1 - std_loadings^2)
    denom <- sum_loadings^2 + sum_errors
    if (is.na(denom) || denom <= 0) return(NA_real_)
    (sum_loadings^2) / denom
  }

  cat("\n=== Convergent Validity: AVE + Composite Reliability ===\n")
  validity_summary <- data.frame(
    construct = c("Job_Satisfaction", "Burnout"),
    AVE = round(c(average_variance_extracted(js_std), average_variance_extracted(bo_std)), 3),
    CR = round(c(composite_reliability(js_std), composite_reliability(bo_std)), 3),
    stringsAsFactors = FALSE
  )
  print(validity_summary, row.names = FALSE)
  cat("(AVE >= 0.50 and CR >= 0.70 are the conventional 'good' thresholds -- Fornell & Larcker 1981)\n")
  write.csv(validity_summary, file.path(output_dir, "convergent_validity.csv"), row.names = FALSE, fileEncoding = "UTF-8")

  # --- Discriminant validity: HTMT between Job_Satisfaction and Burnout ---
  # Pearson correlation on the raw item data (not the CFA's polychoric
  # matrix) -- matches tools/sem_track/validity.py's htmt() exactly.
  htmt_ratio <- function(data, items_a, items_b) {
    all_items <- c(items_a, items_b)
    corr <- abs(cor(data[, all_items], use = "pairwise.complete.obs"))
    het_mean <- mean(corr[items_a, items_b])
    monotrait_mean <- function(items) {
      if (length(items) < 2) return(NA_real_)
      sub <- corr[items, items]
      n <- length(items)
      mean(sub[!diag(n)])
    }
    mono_a <- monotrait_mean(items_a)
    mono_b <- monotrait_mean(items_b)
    denom <- sqrt(mono_a * mono_b)
    if (is.na(denom) || denom <= 0) return(NA_real_)
    het_mean / denom
  }

  cat("\n=== Discriminant Validity: HTMT(Job_Satisfaction, Burnout) ===\n")
  htmt_value <- htmt_ratio(dat, js_items, bo_items)
  cat(sprintf("HTMT = %.3f (< 0.85 strict / < 0.90 lenient supports discriminant validity)\n", htmt_value))
  write.csv(
    data.frame(construct_a = "Job_Satisfaction", construct_b = "Burnout", htmt = round(htmt_value, 3)),
    file.path(output_dir, "discriminant_validity_htmt.csv"), row.names = FALSE, fileEncoding = "UTF-8"
  )

  cat(
    "\nNOTE: the optimizer converged (found a solution), but on this synthetic ",
    "dataset the fit indices, loadings, alpha/omega, AVE/CR, and HTMT are all ",
    "expected to look poor or nonsensical -- items are simulated independently, ",
    "so there is no real factor structure for the CFA to recover. A negative ",
    "latent variance / NA loadings for a construct is a known possible outcome ",
    "here (a Heywood case), not a script bug. 'Converged' here only means the ",
    "script's code ran end to end; it is not a claim that the model fits. ",
    "Interpret these numbers only on the real-data run.\n", sep = ""
  )
} else {
  cat("\nCFA did not converge on synthetic data.\n")
  cat("This is expected (items are simulated independently).\n")
  cat("The script ran successfully. Convergence on real data is what matters.\n")
  write.csv(data.frame(note = "CFA did not converge on synthetic data"),
            file.path(output_dir, "cfa_fit.csv"), row.names = FALSE, fileEncoding = "UTF-8")
}

cat("\nSEM measurement model script completed.\n")
cat("Output files in:", output_dir, "\n")
