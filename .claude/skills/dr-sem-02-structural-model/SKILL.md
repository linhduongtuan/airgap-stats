---
name: dr-sem-02-structural-model
description: "Stage D4 of the DR workflow, SEM track: specify and confirm the structural model connecting latent constructs and observed variables, then generate scripts/sem_structural.R (lavaan) and verify it with Rscript. Use after the measurement model stage when the research question maps constructs to outcomes via directional paths."
---

# DR Stage D4 (SEM): Structural Model

Use this skill after `dr-sem-01-measurement-model` has produced a verified measurement model. The goal is to answer the research question by modeling paths between constructs (and observed covariates), on top of the confirmed measurement model.

## Coordination Contract

When called by `dr-workflow-orchestrator`, follow `plans/analysis_plan.yaml`, `plans/sem_measurement_plan.yaml`, and the project's `dr_workflow_state.yaml`.

After producing outputs:

- Report the exact files created and the verification result.
- Do not advance to Stage E yourself.
- Say that `dr-output-qa-gate` should check Stage D4 (SEM) before the workflow proceeds.

## Inputs

- `plans/analysis_plan.yaml`
- `plans/sem_measurement_plan.yaml`
- `data_synthetic/synthetic_dataset.csv`
- User confirmation of structural paths and covariates

Real data lives outside the repo; never read it, never ask for its path or filename.

## Workflow

1. Read both plan files. Keep the measurement model exactly as confirmed in D3; do not silently change items.
2. Translate the research question into structural paths (e.g. `turnover_intent ~ burnout + jobsat + work_mode`). Latent constructs use their measurement definitions; observed predictors/covariates enter directly.
3. Show the full lavaan model syntax to the user and ask for confirmation of every path before generating code.
4. Write `plans/sem_structural_plan.yaml`.
5. Generate `scripts/sem_structural.R` per `references/sem-structural-rules.md`.
6. Verify: `Rscript scripts/sem_structural.R` on the synthetic data; fix until it runs cleanly (tryCatch around fitting; exit 0 with a clear message if synthetic data does not converge but the model syntax is valid).
7. Write `plans/sem_structural_notes.md`: how to run on real data, how to read path estimates and fit indices, and honest limitations.

## Confirmation Prompt

```text
Measurement model (from D3, unchanged):
  ...

Proposed structural paths for the research question:
  outcome_construct ~ predictor_construct + covariate_1 + ...

Effect reporting: standardized and unstandardized path coefficients,
95% CI, p-values, plus model fit (CFI, TLI, RMSEA, SRMR).

Do you confirm these paths, or do you want to add/remove/redirect any path?
```

If the user requests paths that change the research question, route back through the orchestrator instead of silently complying.

## Required Outputs

- `plans/sem_structural_plan.yaml`
- `scripts/sem_structural.R` (verified on synthetic data) and, when the pack's Python mirror is in use, `scripts/sem_structural.py`
- `plans/sem_structural_notes.md`
- For a mediation model: bootstrap confidence intervals on the indirect, direct, and total effects -- see Diagnostics below

Use `references/sem-structural-rules.md`.
Use `references/sem-structural-plan-template.md`.

## Diagnostics (Phase 3 of the statistical-methods roadmap)

- **Bootstrap CIs for mediation, not a bare point estimate.** The indirect effect (a x b) is a product of two coefficients; its sampling distribution is not normal even when a and b individually are (Sobel's normal-theory test is conservative and no longer the recommended default -- Preacher & Hayes 2004, 2008). Report percentile (or bias-corrected) bootstrap CIs for indirect, direct, and total effects, not just the point estimates.
- **Nested model comparison.** Compare the specified model against a simpler nested alternative (e.g. full mediation, direct path fixed at zero, vs. partial mediation, direct path free) via a chi-square difference test (or, for the two-step approach below, a likelihood-ratio test) plus AIC/BIC -- don't assert one specified model without checking whether its extra parameter(s) earn their keep.
- **Estimator carries over from Stage D3.** The measurement portion keeps whatever estimator `dr-sem-01` settled on (WLSMV/DWLS for ordinal items); don't silently refit it as ML here.
- **Numerical stability, Python/semopy specifically.** A single joint WLS/DWLS fit of the *whole* structural model (measurement + structural paths together) is semopy 2.3.11's textbook-first approach, but its solver can stall (silently fail to optimize, not crash) once the model has more than a handful of ordinal indicators plus structural paths. The robust fallback is factor-score regression (Skrondal & Laake 2001): fit the CFA alone (numerically stable), extract regression factor scores, then fit the structural path(s) as ordinary regressions (OLS/logistic) on those scores -- bootstrapped together so the interval reflects both stages' uncertainty. `tools/sem_track` implements this as the default (`bootstrap_mediation` for one-mediator models, `bootstrap_structural_regression` for parallel/direct-effects models); mirror its approach if writing the R equivalent rather than assuming the one-step joint fit will just work at any model size.

## Package Constraint

Base R plus `lavaan` only. Never auto-install.

## Boundaries

Do not change the measurement model without user confirmation.
Do not chase modification indices; mention them at most as an advanced note.
Do not test every possible path; model the research question.
Do not make causal claims from cross-sectional SEM; paths are directional hypotheses, not proven causation.
Do not interpret synthetic-run estimates or fit as findings.

## Teaching Line

A structural model is a stated hypothesis about directions, not a machine that proves them.
