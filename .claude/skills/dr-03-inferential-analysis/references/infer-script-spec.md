# infer.R Script Specification

`scripts/infer.R` is one plain base R script shared by Stage D3 (crude section) and Stage D4 (adjusted section appended later). The same script runs on synthetic data (agent verification) and real data (user, RStudio) by editing only the settings block.

## Skeleton

```r
# DR Stage D3/D4: Inferential analysis (crude + adjusted)
# Base R only. Run from the project folder.

# === USER SETTINGS ==========================================================
input_csv  <- "data_synthetic/synthetic_dataset.csv"
output_dir <- "outputs_synthetic"
# To run on REAL data in RStudio:
# input_csv  <- file.choose()   # a file-picker window opens: select your real dataset
# output_dir <- "results_real"
# ============================================================================

dat <- read.csv(input_csv, stringsAsFactors = FALSE, fileEncoding = "UTF-8")
dir.create(output_dir, showWarnings = FALSE)

# --- Variable definitions (exact names from the pattern file) ---
outcome_var   <- "..."
predictor_var <- "..."
# Factor handling with EXACT level labels, reference level first:
# dat$treatment <- factor(dat$treatment, levels = c("Phác đồ A", "Phác đồ B"))

# --- Pre-fit checks ---
# stop() if columns are missing; check outcome/predictor variation and
# missingness; for logistic models confirm both outcome classes exist after
# complete-case filtering.

# === SECTION 1: CRUDE MODEL (Stage D3) ======================================
crude_model <- glm(reformulate(predictor_var, outcome_var),
                   data = dat, family = binomial())   # or lm(...) etc.

# Extract estimate, Wald 95% CI, p-value for the main predictor:
est  <- coef(crude_model)
ci   <- confint.default(crude_model)
pval <- summary(crude_model)$coefficients[, 4]
# For logistic regression report OR = exp(est), CI = exp(ci).

crude_results <- data.frame(term = names(est), estimate = ..., ci_low = ...,
                            ci_high = ..., p_value = ...)
write.csv(crude_results, file.path(output_dir, "infer_crude.csv"),
          row.names = FALSE, fileEncoding = "UTF-8")
print(crude_results)

# === SECTION 2: ADJUSTED MODEL (Stage D4 - added by dr-04) ==================
# (dr-04 appends: adjusted model with confirmed covariates, same family and
#  effect measure; crude-vs-adjusted comparison table written to
#  file.path(output_dir, "infer_crude_vs_adjusted.csv"))
```

## Requirements

- Report effect size, 95% CI, then p-value — in that order, in both the CSV and the console output.
- Use the effect measure named in the plan (OR for logistic, beta/mean difference for linear, ...).
- Complete-case handling must be explicit; print how many rows the model used (`nobs()`).
- Console output must be readable on its own, because the user will paste it back for Stage E.
- No packages. No `install.packages()`. No `setwd()`.

## Stage D4 additions

dr-04 edits the same file: keeps Section 1 untouched, fills Section 2 with the adjusted model using the confirmed covariates and the same model family, and writes `infer_crude_vs_adjusted.csv` with rows `crude` and `adjusted` (estimate, 95% CI, p-value, covariates column).
