# SEM Measurement Notes

## How to Run

1. **Install lavaan** (one time): `install.packages("lavaan")` in R console.
2. Open `scripts/sem_measurement.R` in RStudio.
3. Set working directory to `projects/burnout-mediation/`.
4. Run `source("scripts/sem_measurement.R")`.

### Verification on Synthetic Data
Run as-is (default settings point to synthetic data).
Expected outputs in `outputs_synthetic/`:
- `alpha_summary.csv`
- `cfa_fit.csv` (may say "did not converge" — that's OK)
- `cfa_loadings.csv` (only if converged)

### Real Data Run
Change settings block:
- `input_csv  <- file.choose()`
- `output_dir <- "results_real"`

## Interpreting REAL Output

### Cronbach's Alpha
- >= 0.70: acceptable internal consistency
- >= 0.80: good
- < 0.70: may need item revision; check if removing an item improves alpha

### CFA Fit Indices (on Real Data)
| Index | Acceptable | Good |
|-------|-----------|------|
| CFI   | >= 0.90   | >= 0.95 |
| TLI   | >= 0.90   | >= 0.95 |
| RMSEA | <= 0.08   | <= 0.06 |
| SRMR  | <= 0.08   | <= 0.05 |

### Standardized Loadings
- >= 0.50: acceptable
- >= 0.70: good
- If an item loads < 0.40, consider dropping it (after user confirmation)

## Important Caveats
- Fit values from synthetic data are meaningless — items are generated independently.
- Reliability (alpha) and CFA fit support internal consistency and factor structure. They do not establish construct validity or measurement invariance.
- If the CFA fails to converge on real data, try `ordered = c("js_q1","js_q2",...)` for ordinal treatment.
