# Manuscript Result Table Template

Use this structure for `manuscript_results_table.md`.

```markdown
Table 2. Crude and adjusted association between [main predictor] and [outcome]

| Model | Effect estimate | 95% CI | p-value | Adjustment |
|---|---:|---:|---:|---|
| Crude | [estimate] | [lower, upper] | [p] | None |
| Adjusted | [estimate] | [lower, upper] | [p] | [covariates] |

Abbreviations: CI, confidence interval; [OR/HR/RR], [full term].
Note: The adjusted model included [covariates]. Estimates are from [model family].
```

## Formatting

- Use a specific title, not just "Regression results".
- Use the effect measure named in the Step 3/4 plans.
- Keep covariate list in the footnote if the table would become too wide.
- Use consistent decimals.
- Do not include raw R column names if cleaner labels are available.

## If Only Adjusted Results Are Available

Use:

```markdown
Table 2. Adjusted association between [main predictor] and [outcome]

| Predictor | Adjusted [effect measure] | 95% CI | p-value |
|---|---:|---:|---:|
| [main predictor] | [estimate] | [lower, upper] | [p] |

Note: Model adjusted for [covariates].
```

## Diagnostics Table (optional, medical track — Phase 5 of the statistical-methods roadmap)

Include only when the user's real-run output includes a VIF and/or bootstrap-validation table (from `scripts/infer.py`'s Section 3 diagnostics, or the R equivalent). Never fabricate these from the synthetic run — see `traceability-check-template.md`'s `diagnostics_extracted` block for where these numbers must trace back to.

```markdown
Table 3. Regression diagnostics for the adjusted model

| Check | Result | Interpretation |
|---|---:|---|
| Max variance inflation factor (VIF) | [max_vif] | [No | Some] multicollinearity concern (flag threshold: VIF > 5) |
| Internal validation (bootstrap, n = [n_boot]) | Optimism-corrected AUC [corrected_auc] | [Minimal | Some] optimism relative to apparent AUC [apparent_auc] |
| Calibration slope (bootstrap-corrected) | [corrected_calibration_slope] | Values near 1.0 indicate well-calibrated predictions |

Note: VIF and influence diagnostics (Cook's distance, DFBETAs) were reviewed but are reported here only if a term was flagged; see `infer_adjusted_influence.csv` / `infer_adjusted_dfbetas.csv` for the full table if needed.
```

If a predictor was refit under Firth's penalized likelihood (quasi-separation) or after a log-transform/spline (non-linearity flagged by Box-Tidwell), add one row or a footnote naming which predictor and why — do not silently prefer the refit table without saying so.

## Diagnostics Table (optional, SEM track — Phase 5 of the statistical-methods roadmap)

Include only when the user's real-run output includes reliability/validity or bootstrap mediation output (`scripts/sem_measurement.py` / `sem_structural.py`, or the R equivalent).

```markdown
Table 3. Measurement reliability and validity

| Construct | Cronbach's alpha | McDonald's omega | AVE | Composite reliability |
|---|---:|---:|---:|---:|
| [construct 1] | [alpha] | [omega] | [ave] | [cr] |
| [construct 2] | [alpha] | [omega] | [ave] | [cr] |

Note: HTMT between [construct 1] and [construct 2]: [htmt_value] (< 0.85 supports discriminant validity).
```

For a mediation model, report the bootstrapped path decomposition — never a bare point estimate for the indirect effect (it is a product of two coefficients and is not normally distributed):

```markdown
Table 4. Bootstrapped mediation effects (n = [n_boot] resamples)

| Path | Estimate | 95% Bootstrap CI |
|---|---:|---:|
| a ([predictor] → [mediator]) | [a] | [a_ci_low], [a_ci_high] |
| b ([mediator] → [outcome]) | [b] | [b_ci_low], [b_ci_high] |
| c' (direct: [predictor] → [outcome]) | [c_prime] | [c_prime_ci_low], [c_prime_ci_high] |
| Indirect (a×b) | [indirect] | [indirect_ci_low], [indirect_ci_high] |
| Total (c'+a×b) | [total] | [total_ci_low], [total_ci_high] |

Note: Mediation is supported only if the indirect effect's 95% CI excludes 0.
```

For a non-mediation structural model (parallel predictors, no indirect path), use a plain bootstrapped-CI regression table instead of the decomposition table above.
