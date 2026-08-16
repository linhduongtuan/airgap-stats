# Descriptive Analysis Notes — crp-mortality

## How to Run on Real Data

1. Open `scripts/desc.R` in RStudio.
2. Change the settings block:
   - `input_csv <- file.choose()` (select your real dataset when prompted)
   - `output_dir <- "results_real"`
3. Run the script via `source("scripts/desc.R")`.

## Outputs

- `outputs_synthetic/table1.csv` — Table 1 (verification run on synthetic data)
- On real run: `results_real/table1.csv`

## Variables in Table 1

| Type | Variables |
|---|---|
| Continuous (mean ± SD) | age, bmi, sbp, egfr, hba1c, crp |
| Categorical (n %) | sex, treatment, diabetes, hypertension, smoking, complication |
| Group | mortality_30day (0 = alive, 1 = deceased) |
| Excluded | patient_id, dbp, length_of_stay |

## Summary Rules

- Continuous: mean (SD) — clinically familiar variables
- Categorical: n (%) per level
- No p-values included

## Flagged Issues

- None. All variables present with 0% missingness.
