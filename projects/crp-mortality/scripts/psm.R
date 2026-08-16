# DR Stage D4 (extension): Propensity-score sensitivity analysis (Phase 2 of
# the statistical-methods roadmap)
# Base R only. Run from the project folder. Python equivalent:
# scripts/psm.py, tools/medical_track/propensity.py.
#
# WHY THIS SCRIPT EXISTS
# scripts/infer.R's adjusted model controls for confounders by adding them
# as covariates. That works, but it silently assumes the model is specified
# correctly (right functional form, no extreme extrapolation across
# regions of the covariate space treated and untreated patients don't share
# equally). Propensity-score matching (PSM) and inverse-probability
# weighting (IPTW) are a differently-flawed comparison method -- they don't
# extrapolate the way a regression does. If the regression-adjusted and the
# PSM/IPTW estimates tell a similar story, that's real evidence the finding
# isn't an artifact of model specification.
#
# SCOPE NOTE
# The primary research question in plans/sap.md is about CRP (continuous),
# not treatment. PSM/IPTW need a *binary* exposure, so this script
# demonstrates the workflow on `treatment` (Phác đồ A vs B) -- a real,
# already-confirmed binary variable in this dataset, not an invented
# dichotomization of CRP. Treat this as a secondary "does treatment affect
# mortality" sensitivity analysis, distinct from the primary CRP question.
#
# STOCHASTIC NOTE: the greedy matching order is set.seed(2026)-randomized in
# R and np.random.default_rng(2026)-randomized in Python -- different RNG
# algorithms, so the exact matched pairs will differ slightly between the
# two languages even with "the same seed" (same category of expected
# difference as the bootstrap counts elsewhere in this project).

# === USER SETTINGS ==========================================================
input_csv  <- "data_synthetic/synthetic_dataset.csv"
output_dir <- "outputs_synthetic"
# To run on REAL data in RStudio, comment the two lines above and uncomment these:
# input_csv  <- file.choose()   # a file-picker opens: select your real dataset
# output_dir <- "results_real"

exposure_var <- "treatment"       # binary exposure -- see scope note above
outcome_var  <- "mortality_30day"
covariate_vars <- c(               # same confounder set as scripts/infer.R, minus the exposure itself
  "crp", "age", "sex", "bmi", "sbp",
  "diabetes", "hypertension", "smoking",
  "egfr", "hba1c", "complication"
)
# ============================================================================

dat <- read.csv(input_csv, stringsAsFactors = FALSE, fileEncoding = "UTF-8")
dir.create(output_dir, showWarnings = FALSE)

missing_cols <- setdiff(c(exposure_var, outcome_var, covariate_vars), names(dat))
if (length(missing_cols) > 0) stop("Missing columns: ", paste(missing_cols, collapse = ", "))

dat$sex <- factor(dat$sex, levels = c("Nữ", "Nam"))

# --- Binary-code the exposure (0/1) for propensity/matching math ---
exposure_levels <- sort(unique(dat[[exposure_var]][!is.na(dat[[exposure_var]])]))
if (length(exposure_levels) != 2) stop(sprintf("%s must have exactly 2 levels; found %s", exposure_var, paste(exposure_levels, collapse = ", ")))
reference_level <- exposure_levels[1]
treated_level <- exposure_levels[2]
dat$`_exposed` <- as.integer(dat[[exposure_var]] == treated_level)
cat(sprintf("Exposure: %s (%s = 1, %s = 0 [reference])\n", exposure_var, treated_level, reference_level))

rhs <- paste(covariate_vars, collapse = " + ")

# === PART 1: PROPENSITY SCORE ================================================
cat(sprintf("\n=== PROPENSITY SCORE: P(%s=%s | covariates) ===\n", exposure_var, treated_level))
ps_formula <- reformulate(covariate_vars, "`_exposed`")
ps_fit <- glm(ps_formula, data = dat, family = binomial())
ps <- predict(ps_fit, type = "response")
dat$`_ps` <- ps
cat(sprintf("PS range: [%.4f, %.4f] | mean exposed: %.4f | mean unexposed: %.4f\n",
            min(ps), max(ps), mean(ps[dat$`_exposed` == 1]), mean(ps[dat$`_exposed` == 0])))

ps_path <- file.path(output_dir, "psm_propensity_scores.csv")
write.csv(dat[, c("_exposed", "_ps")], ps_path, row.names = FALSE, fileEncoding = "UTF-8")
cat("Propensity scores written to", ps_path, "\n")

# === PART 2: MATCHING =========================================================
cat("\n=== PROPENSITY-SCORE MATCHING (1:1 nearest neighbor, no replacement) ===\n")

# Greedy 1:1 nearest-neighbor matching without replacement, on the logit of
# the propensity score (matching on the raw probability compresses
# distances near 0 and 1, which distorts "nearest"). Matches beyond the
# caliper are dropped rather than forced -- a bad match is worse than no
# match. Default caliper is 0.2 SD of the logit-PS (Austin 2011).
psm_match <- function(exposed, ps, seed = 2026, caliper = NULL) {
  eps <- 1e-6
  p <- pmin(pmax(ps, eps), 1 - eps)
  logit_ps <- log(p / (1 - p))
  if (is.null(caliper)) caliper <- 0.2 * sd(logit_ps)

  treated_idx <- which(exposed == 1)
  control_idx <- which(exposed == 0)

  set.seed(seed)
  treated_order <- sample(treated_idx)

  control_remaining <- control_idx
  rows <- list()
  for (t in treated_order) {
    if (length(control_remaining) == 0) break
    distances <- abs(logit_ps[control_remaining] - logit_ps[t])
    best_pos <- which.min(distances)
    best_c <- control_remaining[best_pos]
    best_dist <- distances[best_pos]
    if (best_dist <= caliper) {
      rows[[length(rows) + 1]] <- data.frame(treated_idx = t, control_idx = best_c, distance = round(best_dist, 4))
      control_remaining <- control_remaining[-best_pos]
    }
  }
  pairs <- if (length(rows) > 0) do.call(rbind, rows) else data.frame(treated_idx = integer(0), control_idx = integer(0), distance = numeric(0))
  list(pairs = pairs, caliper = caliper, n_treated = length(treated_idx), n_matched = nrow(pairs))
}

match <- psm_match(dat$`_exposed`, ps, seed = 2026)
cat(sprintf("Caliper (0.2 SD of logit-PS): %.4f\n", match$caliper))
cat(sprintf("Matched %d / %d exposed patients\n", match$n_matched, match$n_treated))

if (match$n_matched > 0) {
  matched_treated <- dat[[outcome_var]][match$pairs$treated_idx]
  matched_control <- dat[[outcome_var]][match$pairs$control_idx]
  risk_treated <- mean(matched_treated)
  risk_control <- mean(matched_control)
  if (risk_control > 0) {
    matched_rr <- risk_treated / risk_control
    cat(sprintf("Matched-pair outcome risk -- exposed: %.4f | unexposed: %.4f | RR: %.4f\n",
                risk_treated, risk_control, matched_rr))
  } else {
    cat("Matched-pair RR undefined (0 events in matched controls)\n")
  }
}

match_path <- file.path(output_dir, "psm_matched_pairs.csv")
write.csv(match$pairs, match_path, row.names = FALSE, fileEncoding = "UTF-8")
cat("Matched pairs written to", match_path, "\n")

# === PART 3: IPTW =============================================================
cat("\n=== INVERSE-PROBABILITY-OF-TREATMENT WEIGHTING (stabilized) ===\n")

# Stabilized IPTW: multiplies by the marginal treatment prevalence, which
# keeps the weight distribution tighter (Hernan & Robins, Causal Inference:
# What If) -- the standard recommendation unless there's a specific reason
# to use the unstabilized form.
iptw_weights <- function(exposed, ps, stabilized = TRUE) {
  eps <- 1e-6
  p <- pmin(pmax(ps, eps), 1 - eps)
  treated <- exposed == 1
  if (stabilized) {
    p_treated <- mean(exposed)
    ifelse(treated, p_treated / p, (1 - p_treated) / (1 - p))
  } else {
    ifelse(treated, 1 / p, 1 / (1 - p))
  }
}

w <- iptw_weights(dat$`_exposed`, ps, stabilized = TRUE)
dat$`_iptw` <- w
cat(sprintf("Weight range: [%.4f, %.4f] | mean: %.4f (should be close to 1.0)\n", min(w), max(w), mean(w)))

weighted_risk_treated <- weighted.mean(dat[[outcome_var]][dat$`_exposed` == 1], w[dat$`_exposed` == 1])
weighted_risk_control <- weighted.mean(dat[[outcome_var]][dat$`_exposed` == 0], w[dat$`_exposed` == 0])
iptw_rr <- if (weighted_risk_control > 0) weighted_risk_treated / weighted_risk_control else NA_real_
cat(sprintf("IPTW-weighted outcome risk -- exposed: %.4f | unexposed: %.4f | RR: %.4f\n",
            weighted_risk_treated, weighted_risk_control, iptw_rr))

iptw_path <- file.path(output_dir, "psm_iptw_weights.csv")
write.csv(dat[, c("_exposed", "_ps", "_iptw")], iptw_path, row.names = FALSE, fileEncoding = "UTF-8")
cat("IPTW weights written to", iptw_path, "\n")

# === PART 4: E-VALUE ==========================================================
cat("\n=== E-VALUE: robustness of the IPTW estimate to unmeasured confounding ===\n")

# VanderWeele & Ding (2017), eq. 2. RR must be expressed >= 1 (flip a
# protective RR < 1 to its reciprocal first -- the E-value is symmetric
# either way, this just keeps one formula).
e_value_from_rr <- function(rr) {
  if (rr < 1) rr <- 1 / rr
  rr + sqrt(rr * (rr - 1))
}

e_value <- function(estimate, ci_bound = NULL, measure = "RR", rare_outcome = FALSE) {
  stopifnot(measure %in% c("OR", "RR"))
  convert <- measure == "OR" && !rare_outcome
  rr <- if (convert) sqrt(estimate) else estimate
  e_point <- e_value_from_rr(rr)
  list(measure = measure, estimate = estimate, rr_scale_estimate = round(rr, 4),
       e_value_point = round(e_point, 4))
}

if (!is.na(iptw_rr) && iptw_rr > 0) {
  ev <- e_value(iptw_rr, measure = "RR")
  cat(sprintf("IPTW risk ratio: %.4f -> E-value: %.4f\n", ev$estimate, ev$e_value_point))
  cat(sprintf(
    "Interpretation: an unmeasured confounder would need to be associated with both %s and %s ",
    exposure_var, outcome_var))
  cat(sprintf("by a risk ratio of at least %.2f (each), above and beyond the measured covariates, ", ev$e_value_point))
  cat("to fully explain away this estimate.\n")
  ev_path <- file.path(output_dir, "psm_evalue.csv")
  write.csv(as.data.frame(ev), ev_path, row.names = FALSE, fileEncoding = "UTF-8")
  cat("E-value written to", ev_path, "\n")
} else {
  cat("E-value not computed (IPTW risk ratio undefined on this run).\n")
}

cat(
  "\nNOTE: on this synthetic dataset, all of the above is meaningless by design ",
  "(columns are simulated independently, so there is no real exposure-outcome ",
  "relationship and no real confounding to adjust for). This script verifies ",
  "the code runs; interpret nothing from these numbers. This is a secondary ",
  "sensitivity analysis of `treatment`, not the primary CRP question in ",
  "plans/sap.md -- see the scope note at the top of this file.\n", sep = ""
)
