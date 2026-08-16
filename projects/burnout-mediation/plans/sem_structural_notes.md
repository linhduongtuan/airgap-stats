# SEM Structural Notes

## How to Run

1. **lavaan required**: `install.packages("lavaan")` (one time).
2. Open `scripts/sem_structural.R` in RStudio.
3. Set working directory to `projects/burnout-mediation/`.
4. Run `source("scripts/sem_structural.R")`.

### Verification on Synthetic Data
Run as-is. Expected outputs in `outputs_synthetic/`:
- `sem_fit.csv`
- `sem_estimates.csv`
- `sem_rsquared.csv`

Non-convergence on synthetic data is **expected** — items are independent so the model won't fit. This is a PASS.

### Real Data Run
Change settings block:
- `input_csv  <- file.choose()`
- `output_dir <- "results_real"`

## Reading REAL Output

### Fit Indices
| Index | Acceptable | Good |
|-------|-----------|------|
| CFI   | >= 0.90   | >= 0.95 |
| TLI   | >= 0.90   | >= 0.95 |
| RMSEA | <= 0.08   | <= 0.06 |
| SRMR  | <= 0.08   | <= 0.05 |
| χ² p-value | > 0.05 | — |

### Key Estimates
- `a path`: Job_Satisfaction → Burnout (expected negative: higher JS → lower burnout)
- `b path`: Burnout → turnover_intent (expected positive: higher burnout → higher intent)
- `c' path`: direct JS → turnover_intent (expected negative)
- `indirect`: a * b (mediation effect)
- `total`: c' + indirect (total effect)

### Standardized Coefficients (std.all)
- Magnitude: |β| < 0.10 small, ~0.30 medium, > 0.50 large

## Dummy Coding
- `gender_num`: 0 = Nữ, 1 = Nam
- `education_dh`: 1 = Đại học, 0 = otherwise
- `education_ts`: 1 = Thạc sĩ, 0 = otherwise
- `education_tien`: 1 = Tiến sĩ, 0 = otherwise
- Reference: THPT

## Limitations
- turnvent_intent is binary (0/1); ML estimator treats it linearly. For more precise inference with binary outcomes, consider `ordered = "turnover_intent"` in the lavaan `sem()` call (DWLS estimator).
- Cross-sectional data → no causal interpretation.
- Synthetic fit values are meaningless; only real-data output matters.
