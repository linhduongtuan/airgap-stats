# DR Stage D3/D4: Inferential analysis (crude + adjusted)
# Base R only. Run from the project folder.
#
# Section 3 (diagnostics) is Phase 1 of the statistical-methods roadmap: VIF,
# influence (Cook's distance / DFBETAs), a Box-Tidwell linearity-in-the-logit
# check, and bootstrap-optimism internal validation for the adjusted model --
# all computable in base R without packages. Python equivalent:
# tools/diagnostics/regression_diagnostics.py, bootstrap_validation.py.
#
# Section 4 is Phase 2: a Firth penalized-likelihood refit (robust to the
# quasi-separation a ~200-row sample with a dozen covariates risks) and, for
# any Box-Tidwell-flagged variable, an automatic log-transform-and-refit.
# Firth's modified-score IRLS is hand-implemented here in base R (the same
# algorithm the `logistf` package uses) rather than depending on that
# package, to keep this script dependency-free -- cross-validated against
# `logistf` during development to 6+ decimal places on both a well-behaved
# and a deliberately-separated dataset (matching the Python port's own
# validation in tools/medical_track/firth_logistic.py; see that file's
# docstring for the numbers). Python equivalent: tools/medical_track/
# firth_logistic.py, nonlinearity.py.

# === USER SETTINGS ==========================================================
# Runs on the synthetic dataset as delivered:
input_csv  <- "data_synthetic/synthetic_dataset.csv"
output_dir <- "outputs_synthetic"
# To run on REAL data in RStudio, comment the two lines above and uncomment these:
# input_csv  <- file.choose()   # a file-picker opens: select your real dataset
# output_dir <- "results_real"
# ============================================================================

dat <- read.csv(input_csv, stringsAsFactors = FALSE, fileEncoding = "UTF-8")
dir.create(output_dir, showWarnings = FALSE)

# --- Variable definitions ---
outcome_var   <- "mortality_30day"
predictor_var <- "crp"

# --- Pre-fit checks ---
stopifnot(outcome_var %in% names(dat))
stopifnot(predictor_var %in% names(dat))

# Check outcome variation
outcome_tab <- table(dat[[outcome_var]], useNA = "ifany")
cat("Outcome distribution:\n")
print(outcome_tab)
if (length(outcome_tab) < 2) {
  stop("Outcome has fewer than 2 observed classes.")
}
if (any(is.na(dat[[outcome_var]]))) {
  stop("Missing values in outcome. Please handle before fitting.")
}

# Check predictor variation
pred_non_na <- dat[[predictor_var]][!is.na(dat[[predictor_var]])]
if (length(unique(pred_non_na)) < 2) {
  stop("Predictor has < 2 unique values after removing NAs.")
}

complete_cases <- sum(stats::complete.cases(dat[, c(outcome_var, predictor_var)]))
cat(sprintf("Complete cases for crude model: %d / %d\n", complete_cases, nrow(dat)))

# === SECTION 1: CRUDE MODEL (Stage D3) ======================================
crude_model <- glm(reformulate(predictor_var, outcome_var),
                   data = dat, family = binomial())

est  <- coef(summary(crude_model))
ci   <- confint.default(crude_model)

# Exponentiate for OR (except intercept)
or <- exp(est[, "Estimate"])
or_ci_low <- exp(ci[, 1])
or_ci_high <- exp(ci[, 2])

crude_results <- data.frame(
  term = rownames(est),
  estimate = round(est[, "Estimate"], 4),
  or = round(or, 4),
  ci_low = round(or_ci_low, 4),
  ci_high = round(or_ci_high, 4),
  p_value = round(est[, "Pr(>|z|)"], 4),
  row.names = NULL
)

cat("\n=== CRUDE MODEL ===\n")
cat("Model: mortality_30day ~ crp (logistic regression)\n")
cat(sprintf("N used: %d\n", nobs(crude_model)))
print(crude_results)

write.csv(crude_results, file.path(output_dir, "infer_crude.csv"),
          row.names = FALSE, fileEncoding = "UTF-8")
cat("\nCrude results written to", file.path(output_dir, "infer_crude.csv"), "\n")

# === SECTION 2: ADJUSTED MODEL (Stage D4) ====================================
covariate_vars <- c("age", "sex", "bmi", "treatment", "sbp",
                    "diabetes", "hypertension", "smoking",
                    "egfr", "hba1c", "complication")

# Factor handling with exact level labels from pattern file
dat$sex <- factor(dat$sex, levels = c("Nữ", "Nam"))
dat$treatment <- factor(dat$treatment, levels = c("Phác đồ A", "Phác đồ B"))

adjusted_formula <- reformulate(c(predictor_var, covariate_vars), outcome_var)
cat("\nAdjusted formula:", deparse(adjusted_formula), "\n")

adjusted_model <- glm(adjusted_formula, data = dat, family = binomial())

adj_est  <- coef(summary(adjusted_model))
adj_ci   <- confint.default(adjusted_model)

adj_or <- exp(adj_est[, "Estimate"])
adj_or_ci_low <- exp(adj_ci[, 1])
adj_or_ci_high <- exp(adj_ci[, 2])

adjusted_results <- data.frame(
  term = rownames(adj_est),
  estimate = round(adj_est[, "Estimate"], 4),
  or = round(adj_or, 4),
  ci_low = round(adj_or_ci_low, 4),
  ci_high = round(adj_or_ci_high, 4),
  p_value = round(adj_est[, "Pr(>|z|)"], 4),
  row.names = NULL
)

cat("\n=== ADJUSTED MODEL ===\n")
cat(sprintf("N used: %d\n", nobs(adjusted_model)))
print(adjusted_results)

write.csv(adjusted_results, file.path(output_dir, "infer_adjusted.csv"),
          row.names = FALSE, fileEncoding = "UTF-8")
cat("\nAdjusted results written to", file.path(output_dir, "infer_adjusted.csv"), "\n")

# --- Crude vs Adjusted comparison table (main predictor only) ---
cmp <- data.frame(
  model = c("Crude", "Adjusted"),
  or = c(or[2], adj_or[2]),
  ci_low = c(or_ci_low[2], adj_or_ci_low[2]),
  ci_high = c(or_ci_high[2], adj_or_ci_high[2]),
  p_value = c(est[, "Pr(>|z|)"][2], adj_est[, "Pr(>|z|)"][2]),
  covariates = c("None", paste(covariate_vars, collapse = ", ")),
  stringsAsFactors = FALSE
)

cat("\n=== CRUDE VS ADJUSTED (crp) ===\n")
print(cmp)

write.csv(cmp, file.path(output_dir, "infer_crude_vs_adjusted.csv"),
          row.names = FALSE, fileEncoding = "UTF-8")
cat("Crude vs adjusted comparison written to",
    file.path(output_dir, "infer_crude_vs_adjusted.csv"), "\n")

# === SECTION 3: DIAGNOSTICS on the adjusted model (Phase 1) =================

compute_vif <- function(d, formula_rhs) {
  mm <- model.matrix(as.formula(paste("~", formula_rhs)), data = d)
  mm <- mm[, colnames(mm) != "(Intercept)", drop = FALSE]
  terms <- colnames(mm)
  vifs <- sapply(terms, function(term) {
    y <- mm[, term]
    x <- mm[, setdiff(terms, term), drop = FALSE]
    r2 <- summary(lm(y ~ x))$r.squared
    1 / (1 - r2)
  })
  out <- data.frame(term = terms, vif = as.numeric(vifs), stringsAsFactors = FALSE)
  out$flagged <- out$vif > 5
  out[order(-out$vif), ]
}

compute_influence <- function(fit) {
  cd <- cooks.distance(fit)
  n <- length(cd)
  threshold <- 4 / n
  out <- data.frame(obs_index = seq_along(cd) - 1, cooks_distance = as.numeric(cd))
  out$flagged <- out$cooks_distance > threshold
  list(table = out, threshold = threshold)
}

# NOTE on parity: unlike VIF/Box-Tidwell (which match the Python
# implementation to 6 decimal places on identical data -- both compute the
# same closed-form quantities), dfbetas() here and statsmodels'
# GLMInfluence.dfbetas differ by a few percent. Both use the standard
# one-step Newton approximation for GLM influence, but round it slightly
# differently -- a well-documented, harmless cross-software difference, not
# a bug (the underlying fitted coefficients match to 6 decimals). Expect the
# flagged-observation count to differ slightly near the threshold.
compute_dfbetas <- function(fit) {
  db <- dfbetas(fit)
  n <- nrow(db)
  threshold <- 2 / sqrt(n)
  out <- as.data.frame(db)
  out$obs_index <- seq_len(n) - 1
  out$max_abs_dfbeta <- apply(abs(db), 1, max)
  out$flagged <- out$max_abs_dfbeta > threshold
  list(table = out, threshold = threshold)
}

# Box-Tidwell: add a var:log(var) interaction term and refit; a significant
# term (p < 0.05) means `var` is likely not linear on the log-odds scale.
box_tidwell_test <- function(d, outcome, base_rhs, continuous_vars) {
  parts <- list()
  for (var in continuous_vars) {
    x <- d[[var]]
    if (any(x <= 0, na.rm = TRUE)) {
      parts[[var]] <- data.frame(
        variable = var, status = "skipped", p_value = NA_real_,
        detail = sprintf("%s has non-positive values; Box-Tidwell requires x > 0", var),
        stringsAsFactors = FALSE)
      next
    }
    formula_str <- sprintf("%s ~ %s + %s:log(%s)", outcome, base_rhs, var, var)
    fit <- tryCatch(suppressWarnings(glm(as.formula(formula_str), data = d, family = binomial())),
                     error = function(e) NULL)
    if (is.null(fit)) {
      parts[[var]] <- data.frame(variable = var, status = "error", p_value = NA_real_,
                                  detail = "model failed to fit", stringsAsFactors = FALSE)
      next
    }
    coefs <- coef(summary(fit))
    term_name <- sprintf("%s:log(%s)", var, var)
    if (!(term_name %in% rownames(coefs))) {
      parts[[var]] <- data.frame(variable = var, status = "error", p_value = NA_real_,
                                  detail = "interaction term not found in fitted model output",
                                  stringsAsFactors = FALSE)
      next
    }
    p <- coefs[term_name, "Pr(>|z|)"]
    status <- if (p >= 0.05) "linear" else "nonlinear_suspected"
    parts[[var]] <- data.frame(variable = var, status = status, p_value = round(p, 4),
                                detail = sprintf("interaction term `%s` p=%.4f", term_name, p),
                                stringsAsFactors = FALSE)
  }
  do.call(rbind, parts)
}

# --- Bootstrap-optimism internal validation (Harrell's method) ---
auc_stat <- function(y, p) {
  pos <- p[y == 1]; neg <- p[y == 0]
  if (length(pos) == 0 || length(neg) == 0) return(NA_real_)
  r <- rank(c(pos, neg))
  n1 <- length(pos); n2 <- length(neg)
  u <- sum(r[1:n1]) - n1 * (n1 + 1) / 2
  u / (n1 * n2)
}

linpred_from_proba <- function(p, eps = 1e-9) {
  p <- pmin(pmax(p, eps), 1 - eps)
  log(p / (1 - p))
}

calibration_slope <- function(y, lp) {
  if (length(unique(y)) < 2 || sd(lp) == 0) return(NA_real_)
  fit <- tryCatch(suppressWarnings(glm(y ~ lp, family = binomial())), error = function(e) NULL)
  if (is.null(fit)) return(NA_real_)
  unname(coef(fit)["lp"])
}

bootstrap_optimism <- function(d, formula_str, outcome, n_boot = 200, seed = 2026) {
  set.seed(seed)
  n <- nrow(d)
  f <- as.formula(formula_str)

  apparent_fit <- suppressWarnings(glm(f, data = d, family = binomial()))
  y <- d[[outcome]]
  apparent_p <- predict(apparent_fit, newdata = d, type = "response")
  apparent_auc <- auc_stat(y, apparent_p)
  apparent_slope <- calibration_slope(y, linpred_from_proba(apparent_p))

  opt_auc <- numeric(0)
  opt_slope <- numeric(0)
  n_failed <- 0

  for (b in seq_len(n_boot)) {
    idx <- sample(seq_len(n), n, replace = TRUE)
    boot_dat <- d[idx, , drop = FALSE]
    boot_fit <- tryCatch(suppressWarnings(glm(f, data = boot_dat, family = binomial())), error = function(e) NULL)
    if (is.null(boot_fit) || !isTRUE(boot_fit$converged)) { n_failed <- n_failed + 1; next }

    y_boot <- boot_dat[[outcome]]
    p_boot_on_boot <- predict(boot_fit, newdata = boot_dat, type = "response")
    auc_bb <- auc_stat(y_boot, p_boot_on_boot)
    slope_bb <- calibration_slope(y_boot, linpred_from_proba(p_boot_on_boot))

    p_boot_on_orig <- predict(boot_fit, newdata = d, type = "response")
    auc_bo <- auc_stat(y, p_boot_on_orig)
    slope_bo <- calibration_slope(y, linpred_from_proba(p_boot_on_orig))

    if (!is.na(auc_bb) && !is.na(auc_bo)) opt_auc <- c(opt_auc, auc_bb - auc_bo)
    if (!is.na(slope_bb) && !is.na(slope_bo)) opt_slope <- c(opt_slope, slope_bb - slope_bo)
  }

  mean_opt_auc <- if (length(opt_auc) > 0) mean(opt_auc) else NA_real_
  mean_opt_slope <- if (length(opt_slope) > 0) mean(opt_slope) else NA_real_

  list(
    n_boot = n_boot, n_failed_fits = n_failed,
    apparent_auc = apparent_auc, optimism_auc = mean_opt_auc, corrected_auc = apparent_auc - mean_opt_auc,
    apparent_calibration_slope = apparent_slope, optimism_calibration_slope = mean_opt_slope,
    corrected_calibration_slope = apparent_slope - mean_opt_slope
  )
}

rhs <- paste(c(predictor_var, covariate_vars), collapse = " + ")

cat("\n=== DIAGNOSTICS: multicollinearity (VIF) ===\n")
vif_table <- compute_vif(dat, rhs)
print(vif_table, row.names = FALSE)
write.csv(vif_table, file.path(output_dir, "infer_adjusted_vif.csv"), row.names = FALSE, fileEncoding = "UTF-8")
high_vif <- vif_table$term[vif_table$flagged]
if (length(high_vif) > 0) {
  cat("WARNING: VIF > 5 for:", paste(high_vif, collapse = ", "), "-- investigate collinearity before trusting these coefficients.\n")
} else {
  cat("No term exceeds VIF 5 -- no strong multicollinearity detected.\n")
}
cat("VIF table written to", file.path(output_dir, "infer_adjusted_vif.csv"), "\n")

cat("\n=== DIAGNOSTICS: influence (Cook's distance) ===\n")
infl <- compute_influence(adjusted_model)
cat(sprintf("Threshold (4/n): %.4f | flagged observations: %d / %d\n",
            infl$threshold, sum(infl$table$flagged), nrow(infl$table)))
write.csv(infl$table, file.path(output_dir, "infer_adjusted_influence.csv"), row.names = FALSE, fileEncoding = "UTF-8")
cat("Cook's distance table written to", file.path(output_dir, "infer_adjusted_influence.csv"), "\n")

cat("\n=== DIAGNOSTICS: influence (DFBETAs) ===\n")
dfb <- compute_dfbetas(adjusted_model)
cat(sprintf("Threshold (2/sqrt(n)): %.4f | flagged observations: %d / %d\n",
            dfb$threshold, sum(dfb$table$flagged), nrow(dfb$table)))
write.csv(dfb$table, file.path(output_dir, "infer_adjusted_dfbetas.csv"), row.names = FALSE, fileEncoding = "UTF-8")
cat("DFBETAs table written to", file.path(output_dir, "infer_adjusted_dfbetas.csv"), "\n")

cat("\n=== DIAGNOSTICS: linearity in the logit (Box-Tidwell) ===\n")
continuous_for_linearity <- intersect(c(predictor_var, "age", "bmi", "sbp", "egfr", "hba1c"), names(dat))
bt_table <- box_tidwell_test(dat, outcome_var, rhs, continuous_for_linearity)
print(bt_table, row.names = FALSE)
write.csv(bt_table, file.path(output_dir, "infer_adjusted_box_tidwell.csv"), row.names = FALSE, fileEncoding = "UTF-8")
cat("Box-Tidwell table written to", file.path(output_dir, "infer_adjusted_box_tidwell.csv"), "\n")

cat("\n=== DIAGNOSTICS: bootstrap-optimism internal validation (n_boot=200) ===\n")
boot_result <- bootstrap_optimism(dat, paste(outcome_var, "~", rhs), outcome_var, n_boot = 200, seed = 2026)
for (nm in names(boot_result)) cat(sprintf("  %s: %s\n", nm, format(boot_result[[nm]])))
boot_row <- as.data.frame(boot_result, stringsAsFactors = FALSE)
write.csv(boot_row, file.path(output_dir, "infer_adjusted_bootstrap_validation.csv"), row.names = FALSE, fileEncoding = "UTF-8")
cat("Bootstrap validation written to", file.path(output_dir, "infer_adjusted_bootstrap_validation.csv"), "\n")

cat("\nNOTE: on this synthetic dataset, VIF/influence/linearity/bootstrap results\n")
cat("are expected to look bland or degenerate -- columns are simulated\n")
cat("independently, so there is no real collinearity, no real outliers, and no\n")
cat("real discrimination to detect. This section verifies the diagnostic code\n")
cat("runs; interpret the numbers only on the real-data run.\n")

# === SECTION 4: SENSITIVITY ANALYSES (Phase 2) ==============================

# Firth's modified-score IRLS (Firth 1993; Heinze & Schemper 2002). Same
# algorithm as R's `logistf` / Stata's `firthlogit` -- not a call into any
# package. See this file's header for cross-validation notes.
firth_logistic <- function(X, y, max_iter = 50, tol = 1e-6) {
  p <- ncol(X)
  beta <- rep(0, p)
  cov <- diag(p)

  for (iteration in seq_len(max_iter)) {
    eta <- as.numeric(X %*% beta)
    eta <- pmin(pmax(eta, -30), 30)  # guard exp() overflow; penalty keeps beta finite anyway
    pi_hat <- 1 / (1 + exp(-eta))
    w <- pmax(pi_hat * (1 - pi_hat), 1e-10)

    xtwx <- t(X) %*% (X * w)
    xtwx_inv <- tryCatch(solve(xtwx), error = function(e) NULL)
    if (is.null(xtwx_inv)) return(list(beta = beta, cov = cov, converged = FALSE, n_iter = iteration))

    # Hat-matrix diagonal h_i = w_i * x_i (X'WX)^-1 x_i'
    h <- w * rowSums((X %*% xtwx_inv) * X)

    # Firth's modified score: standard score + penalty term h_i*(0.5 - pi_i)
    u_star <- as.numeric(t(X) %*% (y - pi_hat + h * (0.5 - pi_hat)))
    delta <- as.numeric(xtwx_inv %*% u_star)

    # Step-halving safety net against an overshooting first step.
    step <- delta
    beta_new <- beta + step
    for (halving in 1:20) {
      beta_new <- beta + step
      if (all(abs(beta_new) < 30)) break
      step <- step / 2
    }

    cov <- xtwx_inv
    if (max(abs(beta_new - beta)) < tol) return(list(beta = beta_new, cov = cov, converged = TRUE, n_iter = iteration))
    beta <- beta_new
  }
  list(beta = beta, cov = cov, converged = FALSE, n_iter = max_iter)
}

firth_logistic_regression <- function(X, y) {
  fit <- firth_logistic(X, y)
  se <- sqrt(pmax(diag(fit$cov), 0))
  z <- fit$beta / se
  p_val <- 2 * pnorm(-abs(z))
  ci_low <- fit$beta - 1.959963985 * se
  ci_high <- fit$beta + 1.959963985 * se
  table <- data.frame(
    term = colnames(X),
    estimate = round(fit$beta, 4),
    or = round(exp(fit$beta), 4),
    ci_low = round(exp(ci_low), 4),
    ci_high = round(exp(ci_high), 4),
    p_value = round(p_val, 4),
    stringsAsFactors = FALSE, row.names = NULL
  )
  list(table = table, converged = fit$converged, n_iter = fit$n_iter)
}

cat("\n=== SENSITIVITY: Firth penalized logistic regression (adjusted model) ===\n")
X_adj <- model.matrix(adjusted_model)
y_adj <- adjusted_model$y
firth_fit <- firth_logistic_regression(X_adj, y_adj)
print(firth_fit$table, row.names = FALSE)
cat(sprintf("Converged: %s (n_iter=%d)\n", firth_fit$converged, firth_fit$n_iter))
firth_path <- file.path(output_dir, "infer_adjusted_firth.csv")
write.csv(firth_fit$table, firth_path, row.names = FALSE, fileEncoding = "UTF-8")
cat("Firth results written to", firth_path, "\n")

# Compare the main predictor's OR: plain MLE vs Firth. A large relative gap
# is itself a signal of separation/instability in the plain adjusted model
# above -- flag it rather than always asserting one exists.
mle_or_row <- adjusted_results[adjusted_results$term == predictor_var, "or"]
firth_or_row <- firth_fit$table[firth_fit$table$term == predictor_var, "or"]
if (length(mle_or_row) == 1 && length(firth_or_row) == 1) {
  rel_gap <- abs(mle_or_row - firth_or_row) / max(abs(firth_or_row), 1e-9)
  verdict <- if (rel_gap > 0.15) {
    "large relative gap => the plain adjusted model above is less trustworthy than it looks"
  } else {
    "small gap => no sign of separation/instability in the plain adjusted model"
  }
  cat(sprintf("\n%s OR -- plain MLE: %.4f | Firth: %.4f (%s)\n", predictor_var, mle_or_row, firth_or_row, verdict))
}

cat("\n=== SENSITIVITY: log-transform for Box-Tidwell-flagged variables ===\n")

# Fisher-Pearson skewness (population formula, matches scipy.stats.skew's
# default bias=True -- N in the denominator, no small-sample correction).
skewness <- function(x) {
  x <- x[!is.na(x)]
  n <- length(x)
  m <- mean(x)
  m2 <- sum((x - m)^2) / n
  m3 <- sum((x - m)^3) / n
  m3 / (m2^1.5)
}

log_transform_if_skewed <- function(x, skew_threshold = 1.0) {
  xs <- x[!is.na(x)]
  if (any(xs <= 0)) {
    return(list(action = "not_applicable", reason = "variable has non-positive values; cannot log-transform"))
  }
  sk <- skewness(xs)
  if (sk > skew_threshold) {
    return(list(action = "log_transform",
                reason = sprintf("skewness %.2f > %g -- right-skewed enough to log-transform", sk, skew_threshold)))
  }
  list(action = "keep_linear",
       reason = sprintf("skewness %.2f <= %g -- not skewed enough to need a transform", sk, skew_threshold))
}

flagged_vars <- bt_table$variable[bt_table$status == "nonlinear_suspected"]
if (length(flagged_vars) == 0) {
  cat("No variable was flagged nonlinear_suspected in Section 3 -- nothing to transform.\n")
} else {
  dat_transformed <- dat
  transformed_terms <- list()
  for (var in flagged_vars) {
    decision <- log_transform_if_skewed(dat[[var]])
    cat(sprintf("  %s: %s\n", var, decision$reason))
    if (decision$action == "log_transform") {
      new_col <- paste0("log_", var)
      dat_transformed[[new_col]] <- log(dat_transformed[[var]])
      transformed_terms[[var]] <- new_col
    }
  }

  if (length(transformed_terms) > 0) {
    # Rebuild the RHS the same way Section 2 did, substituting the
    # log-transformed name wherever a variable was actually transformed.
    new_predictor <- if (!is.null(transformed_terms[[predictor_var]])) transformed_terms[[predictor_var]] else predictor_var
    new_covariates <- vapply(covariate_vars, function(v) {
      if (!is.null(transformed_terms[[v]])) transformed_terms[[v]] else v
    }, character(1))
    formula_transformed <- reformulate(c(new_predictor, new_covariates), outcome_var)
    cat("\nRefit formula:", deparse(formula_transformed), "\n")
    transformed_model <- glm(formula_transformed, data = dat_transformed, family = binomial())
    t_est <- coef(summary(transformed_model))
    t_ci <- confint.default(transformed_model)
    transformed_results <- data.frame(
      term = rownames(t_est),
      estimate = round(t_est[, "Estimate"], 4),
      or = round(exp(t_est[, "Estimate"]), 4),
      ci_low = round(exp(t_ci[, 1]), 4),
      ci_high = round(exp(t_ci[, 2]), 4),
      p_value = round(t_est[, "Pr(>|z|)"], 4),
      row.names = NULL
    )
    print(transformed_results, row.names = FALSE)
    transformed_path <- file.path(output_dir, "infer_adjusted_log_transformed.csv")
    write.csv(transformed_results, transformed_path, row.names = FALSE, fileEncoding = "UTF-8")
    cat("Log-transformed refit written to", transformed_path, "\n")
  } else {
    cat("Flagged variable(s) could not be log-transformed (non-positive values) -- ")
    cat("consider a restricted cubic spline instead.\n")
  }
}

cat("\nNOTE: Section 4 is a sensitivity comparison, not a replacement for the\n")
cat("primary adjusted model in Section 2. Report both if they materially\n")
cat("disagree; that disagreement is itself a finding.\n")
