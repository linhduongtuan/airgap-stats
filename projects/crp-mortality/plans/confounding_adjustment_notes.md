# Confounding Adjustment Notes — crp-mortality (Stage D4)

## How to Run on Real Data

1. Open `scripts/infer.R` in RStudio.
2. Change settings:
   - `input_csv <- file.choose()`
   - `output_dir <- "results_real"`
3. Run via `source("scripts/infer.R")`.

## Outputs

- `infer_crude.csv` — crude model results
- `infer_adjusted.csv` — adjusted model results (all coefficients)
- `infer_crude_vs_adjusted.csv` — comparison table (CRP only)

## Model Specifications

- **Crude:** `mortality_30day ~ crp`
- **Adjusted:** `mortality_30day ~ crp + age + sex + bmi + treatment + sbp + diabetes + hypertension + smoking + egfr + hba1c + complication`
- Both: logistic regression, OR as effect measure

## Covariates

- **Included (user-confirmed):** age, sex, bmi, treatment, sbp, diabetes, hypertension, smoking, egfr, hba1c, complication
- **Excluded:** dbp, length_of_stay, patient_id

## Interpretation Template

> After adjustment for [covariates], the OR for CRP was [estimate] (95% CI: [lower]–[upper], p = [p]), compared to the crude OR of [crude_estimate] (95% CI: [crude_lower]–[crude_upper]). This suggests that the association between CRP and 30-day mortality [was / was not] substantially attenuated after accounting for potential confounders.

## Notes

- Synthetic results are not scientific findings.
- `complication` may be post-exposure; user included it by choice.
- No convergence issues or complete separation in synthetic run.
