# Descriptive Analysis Notes

## How to Run on Real Data

1. Open `scripts/desc.R` in RStudio.
2. Change the settings block at the top:
   - `input_csv  <- file.choose()`
   - `output_dir <- "results_real"`
3. Set working directory to `projects/burnout-mediation/` (Session > Set Working Directory > Choose Directory).
4. Run `source("scripts/desc.R")`.
5. Select your real dataset CSV when the file picker opens.
6. Output: `results_real/table1.csv` and `results_real/missing_summary.csv`.

## Verification on Synthetic Data

Run the same script without changes (default settings point to synthetic data):
```r
source("scripts/desc.R")
```
Expected output: `outputs_synthetic/table1.csv` and `outputs_synthetic/missing_summary.csv`.

## Output Interpretation

- `table1.csv`: baseline characteristics overall and by turnover_intent group (0 = no intent, 1 = yes).
  - Continuous: mean (SD)
  - Ordinal/Likert (wlb, js_q1–js_q5, bo_q1–bo_q5): median (IQR)
  - Categorical: n (%)
- `missing_summary.csv`: count and percentage of missing values per variable.

## Flagged Issues

- No missing data in the synthetic dataset (pattern file shows 0% missing for all vars).
- `income`, `work_hours`, `work_mode` excluded from Table 1 per analysis plan — can be added if needed.
- All Likert items (js_q1–js_q5, bo_q1–bo_q5) treated as ordinal for display but composite scores shown as mean (SD) for simplicity.
