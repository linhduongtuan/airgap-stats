---
name: dr-04-confounding-adjustment
description: "Stage D4 of the DR workflow, medical track: create and confirm an adjusted model plan tied to the Stage D3 crude model, then extend scripts/infer.R with the adjusted section in base R and verify it with Rscript. Use when the agent needs to add user-confirmed covariates to the same outcome, predictor, model family, and effect measure from D3."
---

# DR Stage D4 (Medical): Confounding Adjustment

Use this skill after D3 has created `plans/inferential_analysis_plan.yaml`.

The goal is to evaluate whether the main association changes after adjustment for selected covariates. This step must stay tied to the D3 crude model.

## Coordination Contract

When called by `dr-workflow-orchestrator`, follow `plans/analysis_plan.yaml`, `plans/inferential_analysis_plan.yaml`, and the project's `dr_workflow_state.yaml`.

After producing outputs:

- Report the exact files created/updated and the verification result.
- Do not advance to Stage E yourself.
- Say that `dr-output-qa-gate` should check Stage D4 before the workflow proceeds.

## Required Inputs

Minimum inputs:

- `plans/analysis_plan.yaml`
- `plans/inferential_analysis_plan.yaml`
- `scripts/infer.R` (crude section from D3)
- `data_synthetic/synthetic_dataset.csv`
- Covariates from `analysis_plan.yaml` or user confirmation

Real data lives outside the repo; never read it, never ask for its path or filename.

## Workflow

1. Read `plans/analysis_plan.yaml` and `plans/inferential_analysis_plan.yaml`.
2. Confirm D4 keeps the same outcome, main predictor, model family, and effect measure as D3.
3. Identify candidate covariates from `analysis_plan.yaml`.
4. Ask the user to confirm, add, or remove covariates before touching code.
5. If the user does not know, use covariates from `analysis_plan.yaml`, mark confirmation as `assumed`, and flag `needs_review`.
6. Write `plans/confounding_adjustment_plan.yaml`.
7. Extend `scripts/infer.R`: fill Section 2 (adjusted model + crude-vs-adjusted comparison table) per `references/infer-script-spec` in dr-03. Keep Section 1 untouched.
8. Verify: `Rscript scripts/infer.R` from the project folder; fix and rerun until clean.
9. Write `plans/confounding_adjustment_notes.md`.

## Confirmation Prompt

Before writing code, show:

```text
I will keep the Stage D3 research question and crude model:
- Outcome: ...
- Main predictor: ...
- Crude model: ...
- Effect measure: ...

For Stage D4, I propose the adjusted model:
...

Covariates for adjustment:
- ...

Do you confirm this covariate list, or do you want to add/remove variables?
```

If no covariates are available, stop and ask for covariates instead of inventing them.

## Required Outputs

Always produce:

- `plans/confounding_adjustment_plan.yaml` (including the `confounder_selection` block -- see Phase 0)
- `scripts/infer.R` (both sections plus diagnostics, verified on synthetic data)
- `plans/confounding_adjustment_notes.md`
- `outputs_synthetic/infer_crude_vs_adjusted.csv` from the verification run
- `outputs_synthetic/infer_adjusted_vif.csv`, `infer_adjusted_influence.csv`, `infer_adjusted_dfbetas.csv`, `infer_adjusted_box_tidwell.csv`, `infer_adjusted_bootstrap_validation.csv` -- see Diagnostics below

Use `references/adjusted-plan-template.md`.
Use `references/confounding-adjustment-rules.md`.
Use `references/crude-vs-adjusted-reporting.md`.

## Diagnostics (Phase 1 of the statistical-methods roadmap)

The adjusted model ships with its own assumption checks, not just its coefficients -- an adjusted OR with no check that it's trustworthy is not a finished Stage D4:

- **Multicollinearity (VIF).** Flag any term with VIF > 5.
- **Influence.** Cook's distance (threshold `4/n`) and DFBETAs (threshold `2/sqrt(n)`) per observation.
- **Linearity in the logit (Box-Tidwell).** For every continuous covariate, add a `var:log(var)` interaction term and refit; a significant interaction (p < 0.05) means that variable likely needs a log-transform or spline, not a straight-line term.
- **Bootstrap-optimism internal validation.** Refit on >=200 bootstrap resamples, evaluate each refit on both the resample and the original data, and report the apparent vs. optimism-corrected AUC and calibration slope.

All four are base-R-computable without packages (VIF via `1 / (1 - R^2)` from an auxiliary `lm()` of each predictor on the others; Cook's distance via `cooks.distance()`, in base R's `stats`; DFBETAs via `dfbetas()`, also base `stats`; Box-Tidwell via an interaction term in `glm()`; bootstrap via `sample(n, n, replace = TRUE)` in a loop). The reference implementation with the exact thresholds and branching logic is Python: `tools/diagnostics/regression_diagnostics.py` and `tools/diagnostics/bootstrap_validation.py` -- mirror its rules if writing the R equivalent, rather than re-deriving them.

On synthetic data (columns simulated independently) expect these to look bland or degenerate -- no real collinearity, no real outliers, corrected AUC near 0.5. That is the expected, successful outcome; it proves the diagnostic code runs, nothing about the real association.

## Core Constraint

Stage D4 must preserve the D3 analysis target:

```text
same outcome
same main predictor
same model family
same effect measure
```

Only add confirmed covariates unless the user explicitly changes the plan.

## Base R Constraint

Base R only, same rules as D3. The adjusted model is the same `glm`/`lm` call with covariates added to the formula. Wald CIs via `confint.default()`. No packages.

## Boundaries

Do not select covariates only because their p-values are significant.
Do not use stepwise selection by default.
Do not introduce propensity scores, DAGs, mediation, subgroup analysis, or sensitivity analysis in the core demo.
Do not adjust for variables suspected to be mediators or colliders without warning.
Do not make causal claims.
Do not treat synthetic-run numbers as scientific findings.

## Teaching Line

Adjustment is not to make the p-value look better. Adjustment is to make the comparison fairer.
