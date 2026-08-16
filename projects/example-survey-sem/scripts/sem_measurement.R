# DR Stage D3 (SEM): Measurement model  (example-survey-sem)
# Base R + lavaan only. Run from the project folder. Python equivalent:
# scripts/sem_measurement.py, tools/sem_track/{estimator,reliability,validity}.py.
#
# ESTIMATOR (Phase 3 of the statistical-methods roadmap): js_q*/bo_q* are
# 5-point Likert items -- ordinal, not continuous. This script fits the CFA
# with lavaan's WLSMV estimator on the polychoric correlation matrix
# (declaring every item ordinal via `ordered=`), replacing the previous
# plain-ML fit that plans/sem_measurement_plan.yaml had flagged
# `needs_review` in Phase 0. Also new: McDonald's omega, AVE/composite
# reliability, and the HTMT ratio between jobsat and burnout.

# === USER SETTINGS ==========================================================
input_csv  <- "data_synthetic/synthetic_dataset.csv"
output_dir <- "outputs_synthetic"
# To run on REAL data in RStudio, change the two lines above to:
# input_csv  <- file.choose()   # cua so chon file se hien ra: chon file du lieu that cua ban
# output_dir <- "results_real"
# ============================================================================

library(lavaan)  # install.packages("lavaan") once, before first use

dat <- read.csv(input_csv, stringsAsFactors = FALSE, fileEncoding = "UTF-8")
dir.create(output_dir, showWarnings = FALSE)

constructs <- list(
  jobsat  = c("js_q1", "js_q2", "js_q3", "js_q4", "js_q5"),
  burnout = c("bo_q1", "bo_q2", "bo_q3", "bo_q4", "bo_q5")
)
all_items <- unlist(constructs, use.names = FALSE)
stopifnot(all(all_items %in% names(dat)))

# --- Cronbach's alpha in base R (no psych) ---
cronbach_alpha <- function(items_df) {
  items_df <- items_df[stats::complete.cases(items_df), , drop = FALSE]
  k <- ncol(items_df)
  if (k < 2) return(NA_real_)
  item_vars <- apply(items_df, 2, stats::var)
  total_var <- stats::var(rowSums(items_df))
  (k / (k - 1)) * (1 - sum(item_vars) / total_var)
}
alpha_summary <- data.frame(
  construct = names(constructs),
  n_items   = vapply(constructs, length, integer(1)),
  alpha     = round(vapply(constructs, function(it) cronbach_alpha(dat[, it]), numeric(1)), 3),
  row.names = NULL)
write.csv(alpha_summary, file.path(output_dir, "alpha_summary.csv"), row.names = FALSE, fileEncoding = "UTF-8")
cat("Cronbach's alpha (base R):\n"); print(alpha_summary, row.names = FALSE); cat("\n")

# --- Scale scores (row mean, >=50% items non-missing) ---
for (cn in names(constructs)) {
  it <- constructs[[cn]]
  n_ok <- rowSums(!is.na(dat[, it]))
  dat[[paste0(cn, "_score")]] <- ifelse(n_ok >= ceiling(length(it) * 0.5),
                                        rowMeans(dat[, it], na.rm = TRUE), NA_real_)
}

# === CFA in lavaan, WLSMV estimator on declared-ordinal items ===============
cat("=== CFA (WLSMV estimator, ordinal items) ===\n")
model <- '
  jobsat  =~ js_q1 + js_q2 + js_q3 + js_q4 + js_q5
  burnout =~ bo_q1 + bo_q2 + bo_q3 + bo_q4 + bo_q5
'
fit <- tryCatch(
  cfa(model, data = dat, ordered = all_items, estimator = "WLSMV"),
  error = function(e) { message("CFA did not fit: ", conditionMessage(e)); NULL }
)

if (!is.null(fit) && isTRUE(lavInspect(fit, "converged"))) {
  fi <- fitMeasures(fit, c("cfi", "tli", "rmsea", "srmr"))
  print(round(fi, 4))
  fi_df <- data.frame(measure = names(fi), value = as.numeric(fi), stringsAsFactors = FALSE)
  write.csv(fi_df, file.path(output_dir, "cfa_fit.csv"), row.names = FALSE, fileEncoding = "UTF-8")

  pe <- parameterEstimates(fit, standardized = TRUE)
  write.csv(pe, file.path(output_dir, "cfa_estimates.csv"), row.names = FALSE, fileEncoding = "UTF-8")

  # Loadings only ("=~" rows), lhs=construct/rhs=item in lavaan's own
  # orientation -- kept here as construct/item for clarity (no need to
  # match semopy's lval/rval naming since this project's Python mirror
  # writes cfa.params -- the full parameter table -- directly to
  # cfa_estimates.csv rather than a separate loadings-only file).
  loadings <- pe[pe$op == "=~", c("lhs", "rhs", "std.all")]
  names(loadings) <- c("construct", "item", "std_loading")

  # --- Reliability: alpha + omega, from the CFA's own standardized loadings ---
  mcdonald_omega <- function(std_loadings) {
    sum_loadings <- sum(std_loadings)
    sum_errors <- sum(1 - std_loadings^2)
    denom <- sum_loadings^2 + sum_errors
    if (is.na(denom) || denom <= 0) return(NA_real_)
    (sum_loadings^2) / denom
  }

  cat("\n=== Reliability: Cronbach's Alpha + McDonald's Omega ===\n")
  rel_rows <- lapply(names(constructs), function(cn) {
    std <- loadings$std_loading[loadings$construct == cn]
    data.frame(construct = cn, n_items = length(constructs[[cn]]),
               alpha = round(cronbach_alpha(dat[, constructs[[cn]]]), 3),
               omega = round(mcdonald_omega(std), 3))
  })
  reliability_summary <- do.call(rbind, rel_rows)
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
  val_rows <- lapply(names(constructs), function(cn) {
    std <- loadings$std_loading[loadings$construct == cn]
    data.frame(construct = cn, AVE = round(average_variance_extracted(std), 3),
               CR = round(composite_reliability(std), 3))
  })
  validity_summary <- do.call(rbind, val_rows)
  print(validity_summary, row.names = FALSE)
  cat("(AVE >= 0.50 and CR >= 0.70 are the conventional 'good' thresholds -- Fornell & Larcker 1981)\n")
  write.csv(validity_summary, file.path(output_dir, "convergent_validity.csv"), row.names = FALSE, fileEncoding = "UTF-8")

  # --- Discriminant validity: HTMT(jobsat, burnout) ---
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
    mono_a <- monotrait_mean(items_a); mono_b <- monotrait_mean(items_b)
    denom <- sqrt(mono_a * mono_b)
    if (is.na(denom) || denom <= 0) return(NA_real_)
    het_mean / denom
  }

  cat("\n=== Discriminant Validity: HTMT(jobsat, burnout) ===\n")
  htmt_value <- htmt_ratio(dat, constructs$jobsat, constructs$burnout)
  cat(sprintf("HTMT = %.3f (< 0.85 strict / < 0.90 lenient supports discriminant validity)\n", htmt_value))
  write.csv(
    data.frame(construct_a = "jobsat", construct_b = "burnout", htmt = round(htmt_value, 3)),
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
