# Results Paragraph Template

Write `results_paragraph.md` using this structure.

## Full Version

```text
To assess the association between [main predictor] and [outcome], we fit a crude [model family] followed by an adjusted model including [covariates]. In the crude analysis, [main predictor] was associated with [outcome] with a [effect measure] of [estimate] (95% CI: [lower] to [upper], p = [p]). After adjustment for [covariates], the [effect measure] was [estimate] (95% CI: [lower] to [upper], p = [p]). These results suggest that [plain-language interpretation], while accounting for the selected covariates. Because this analysis is observational, the findings should be interpreted as adjusted associations rather than causal effects.
```

## Short Version

```text
In an adjusted [model family] evaluating [outcome], [main predictor] was associated with [outcome] with a [effect measure] of [estimate] (95% CI: [lower] to [upper], p = [p]), after adjustment for [covariates].
```

## Placeholder Version

Use this only when numeric RStudio output is unavailable:

```text
To assess the association between [main predictor] and [outcome], we fit a crude [model family] followed by an adjusted model including [covariates]. The final numeric estimates should be inserted from the RStudio output: [effect measure] [estimate] (95% CI: [lower] to [upper], p = [p]).
```

## Writing Rules

- Keep Results factual and concise.
- Avoid long explanation of why the model was chosen; that belongs in Methods.
- Do not repeat every covariate estimate unless the covariate itself is a result of interest.
- Do not overinterpret p-values.
- Do not write a full Discussion section.

## Diagnostics Sentence (optional, medical track — Phase 5 of the statistical-methods roadmap)

Append after the adjusted-model sentence only when the user's real-run output includes a VIF/bootstrap-validation table. Pull the numbers from `diagnostics_extracted` in `results_traceability_check.yaml`, never from the synthetic run.

```text
Multicollinearity was assessed via variance inflation factors (maximum VIF = [max_vif], threshold 5); [no term exceeded this threshold / [term] exceeded this threshold and is interpreted with caution]. Internal validation via bootstrap resampling (n = [n_boot]) yielded an optimism-corrected AUC of [corrected_auc] (apparent AUC [apparent_auc]) and a bootstrap-corrected calibration slope of [corrected_calibration_slope].
```

If a predictor required Firth's penalized likelihood (quasi-separation) or a log-transform/spline (non-linearity flagged by Box-Tidwell), add one sentence naming it:

```text
[Predictor] showed evidence of quasi-separation in the crude model; estimates shown are from Firth's penalized-likelihood refit.
```
```text
[Predictor] was log-transformed before inclusion after a Box-Tidwell test indicated departure from linearity on the logit scale.
```

## Bootstrap Indirect Effect Sentence (SEM track, mediation models only)

Never report indirect/direct/total effects as bare point estimates — they need a bootstrap CI because the indirect effect (a product of two coefficients) is not normally distributed.

```text
The indirect effect of [predictor] on [outcome] through [mediator] was [indirect] (95% bootstrap CI: [indirect_ci_low] to [indirect_ci_high], n = [n_boot] resamples), consistent with [partial / full / no] mediation. The direct effect of [predictor] on [outcome] was [c_prime] (95% CI: [c_prime_ci_low] to [c_prime_ci_high]).
```

State "no mediation" only if the indirect effect's CI includes 0; state "full mediation" only if additionally the direct effect's CI includes 0.

## Limitations Paragraph (auto-populated — Phase 5 of the statistical-methods roadmap)

Build this from `limitations_pulled_forward` in `results_traceability_check.yaml`, not from a free choice each time — see that template for where each flag comes from. Include only the sentences whose `include_in_limitations` is `true`; drop the rest silently rather than leaving a placeholder. This paragraph is additive to, not a replacement for, any study-specific limitation the user or agent identifies separately (e.g. observational design, small sample).

**Missing-data sentence** — include only if `plans/sap.md` Section H recorded `strategy: complete_case` for a project with any non-trivial `missing_pct`:

```text
Complete-case analysis was used per the pre-specified missing-data plan (Section H of the Statistical Analysis Plan); [variables_affected] had missing_pct up to [x]%, which may introduce bias if data are not missing completely at random.
```

**Single-item construct sentence** — include only if any construct in `plans/sem_measurement_plan.yaml` or `plans/sem_structural_plan.yaml` has exactly one item:

```text
[Construct] was measured with a single item; single-item measures cannot have their internal consistency assessed and may carry more measurement error than the multi-item constructs in this study.
```

**Synthetic-verification sentence** — always include; this is a transparency note about the DR workflow itself, not a statistical limitation of the study:

```text
Analysis code was developed and verified end-to-end against a fully synthetic dataset (independently-generated columns, reviewed for re-identification risk) before being run once on the real data; the AI assistant that helped write the code never had access to real values.
```
