# SEM Measurement Rules

## Script structure for sem_measurement.R

Same settings-block pattern as all DR scripts:

```r
# === USER SETTINGS ==========================================================
input_csv  <- "data_synthetic/synthetic_dataset.csv"
output_dir <- "outputs_synthetic"
# Real run: input_csv <- file.choose() ; output_dir <- "results_real"
# ============================================================================
```

## Cronbach's alpha in base R (no psych)

```r
cronbach_alpha <- function(items_df) {
  items_df <- items_df[stats::complete.cases(items_df), , drop = FALSE]
  k <- ncol(items_df)
  if (k < 2) return(NA_real_)
  item_vars <- apply(items_df, 2, stats::var)
  total_var <- stats::var(rowSums(items_df))
  (k / (k - 1)) * (1 - sum(item_vars) / total_var)
}
```

Report alpha per construct to `alpha_summary.csv` in the output dir.

## Scale scores

Row mean of confirmed items, requiring at least 50% non-missing items per row; otherwise NA. Handle user-confirmed reverse-coded items explicitly (`reversed = (max + min) - x`), stating the response range.

## CFA in lavaan

```r
library(lavaan)  # install.packages("lavaan") once, before first use

model <- '
  burnout =~ bo_q1 + bo_q2 + bo_q3 + bo_q4 + bo_q5
  jobsat  =~ js_q1 + js_q2 + js_q3 + js_q4 + js_q5
'
fit <- cfa(model, data = dat, std.lv = TRUE)
summary(fit, fit.measures = TRUE, standardized = TRUE)
fitMeasures(fit, c("cfi", "tli", "rmsea", "srmr"))
```

- Item names must match the pattern file exactly.
- Wrap the `cfa()` call in `tryCatch`, and before calling `fitMeasures()`/`parameterEstimates()` guard with `if (!is.null(fit) && lavInspect(fit, "converged"))`. On synthetic data the model may not converge (items are independent); the guard lets the script still exit 0. Non-convergence on synthetic data is a PASS for the "code runs" check.
- Write loadings and fit indices to `cfa_summary.csv` / console.
- If items are strongly ordinal (few response values), mention `ordered = c(...)` as an option in the notes, but default to the continuous ML approach for the core demo.

## Practical thresholds (for REAL output only)

- Alpha >= 0.70: common practical threshold, not an absolute law.
- CFI/TLI >= 0.90 acceptable, >= 0.95 good.
- RMSEA <= 0.08 acceptable, <= 0.06 good.
- SRMR <= 0.08 acceptable.

State these in the notes as guidance for interpreting the user's real RStudio output. Never apply them to synthetic output — synthetic items are independent by design, so poor fit there is expected and meaningless.

## Readiness flags

- `ready`: item groups confirmed, script verified.
- `needs_review`: item grouping inferred, reverse coding uncertain, construct with < 3 items.
- `not_ready`: no item groups can be confirmed, or items lack a shared response scale.

## Validity boundary

Reliability and CFA fit support internal consistency and factor structure. They do not establish construct validity, measurement invariance, or causal interpretation. Say so in the notes.
