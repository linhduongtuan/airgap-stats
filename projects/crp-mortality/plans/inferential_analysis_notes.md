# Inferential Analysis Notes — crp-mortality (Stage D3)

## How to Run on Real Data

1. Open `scripts/infer.R` in RStudio.
2. Change settings block:
   - `input_csv <- file.choose()` (select your real dataset)
   - `output_dir <- "results_real"`
3. Run via `source("scripts/infer.R")`.

## Outputs

- `outputs_synthetic/infer_crude.csv` — crude logistic regression results (synthetic verification)
- On real run: `results_real/infer_crude.csv`

## Model Summary

- Outcome: mortality_30day (0 = alive, 1 = deceased)
- Predictor: crp (continuous, per 1-unit increase)
- Method: logistic regression (glm, binomial family)
- Effect measure: OR (odds ratio), 95% CI, p-value
- Formula: mortality_30day ~ crp

## Notes

- Crude/unadjusted model only. Adjusted model will be added in Stage D4.
- Synthetic results are not scientific findings; they only prove the code runs.
- No separation issues detected in synthetic run.
