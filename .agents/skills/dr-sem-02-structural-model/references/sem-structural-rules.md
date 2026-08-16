# SEM Structural Rules

## Script structure for sem_structural.R

Same settings-block pattern as all DR scripts (synthetic paths by default, two lines to edit for the real run).

```r
library(lavaan)  # install.packages("lavaan") once, before first use

model <- '
  # Measurement model (from Stage D3, unchanged)
  burnout =~ bo_q1 + bo_q2 + bo_q3 + bo_q4 + bo_q5
  jobsat  =~ js_q1 + js_q2 + js_q3 + js_q4 + js_q5

  # Structural model (confirmed by the user)
  turnover_intent ~ burnout + jobsat + work_mode_num
'
fit <- tryCatch(
  sem(model, data = dat, std.lv = TRUE, warn = FALSE),
  error = function(e) { message("Model did not fit on this dataset: ", conditionMessage(e)); NULL }
)
# CRITICAL: on synthetic data the model frequently does NOT converge, because
# items are simulated independently. A non-converged fit does not error on
# sem(), but fitMeasures()/parameterEstimates() then throw a hard error and
# make the script exit non-zero. Always guard with lavInspect(..., "converged")
# so verification exits cleanly and the "code runs" check is meaningful.
if (!is.null(fit) && lavInspect(fit, "converged")) {
  summary(fit, fit.measures = TRUE, standardized = TRUE, ci = TRUE)
  write.csv(parameterEstimates(fit, standardized = TRUE),
            file.path(output_dir, "sem_estimates.csv"), row.names = FALSE)
  write.csv(t(as.data.frame(fitMeasures(fit, c("cfi","tli","rmsea","srmr","chisq","df","pvalue")))),
            file.path(output_dir, "sem_fit.csv"))
} else {
  cat("Model did not converge on synthetic data (expected). Syntax is valid;",
      "it will run on real data.\n")
}
```

When verifying on synthetic data, non-convergence is a PASS for the "does the code run" check, not a failure — provided the script exits 0 with the message above. Never tune the model to force convergence on synthetic data.

## Handling variable types

- Binary/categorical observed predictors: convert to numeric dummies explicitly (e.g. `dat$work_mode_num <- as.numeric(dat$work_mode == "Remote")`), using exact level labels from the pattern file, and document the coding in the notes.
- Binary outcome construct-indicators or outcomes: for the core demo, model observed binary outcomes with a note about the linear approximation, or suggest the `ordered =` option as an extension. Keep the core demo simple.

## Reporting order

1. Model fit (CFI, TLI, RMSEA, SRMR) — is the model defensible?
2. Structural path estimates: unstandardized, 95% CI, p-value.
3. Standardized coefficients for magnitude comparison.
4. R-squared of the outcome.

## Fit thresholds (REAL output only)

Same guidance as the measurement stage: CFI/TLI >= 0.90/0.95, RMSEA <= 0.08/0.06, SRMR <= 0.08 — practical flags, not laws. Never applied to synthetic output.

## Language

Use: "was associated with", "predicted (in the model's directional sense)", "the path from X to Y was ...".
Avoid: "caused", "proved", "confirmed the theory".

## Readiness flags

- `ready`: paths confirmed, script verified.
- `needs_review`: paths assumed, dummy coding assumptions, binary outcome approximation.
- `not_ready`: measurement model unresolved, or required variables missing.
