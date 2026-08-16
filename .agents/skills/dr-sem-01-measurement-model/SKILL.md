---
name: dr-sem-01-measurement-model
description: "Stage D3 of the DR workflow, SEM track: check latent measurement before structural modeling. Use when a survey/questionnaire project with confirmed constructs needs reliability (Cronbach's alpha in base R) and a CFA measurement model (lavaan), producing plans/sem_measurement_plan.yaml and a verified scripts/sem_measurement.R."
---

# DR Stage D3 (SEM): Measurement Model

Use this skill after D1 has set `workflow_track: sem` and D2 has described the sample. Public health and social science surveys have an extra measurement layer: before modeling relationships between constructs, check whether the items measure their constructs acceptably.

## Coordination Contract

When called by `dr-workflow-orchestrator`, follow `plans/analysis_plan.yaml` and the project's `dr_workflow_state.yaml`.

After producing outputs:

- Report the exact files created and the verification result.
- Do not advance to D4 yourself.
- Say that `dr-output-qa-gate` should check Stage D3 (SEM) before the workflow proceeds.

## Inputs

Expected inputs:

- `plans/analysis_plan.yaml` (with constructs and items from D1)
- `data_synthetic/synthetic_dataset.csv`
- `pattern/dataset_pattern.csv` (item response values from `integer_scale` levels)
- User confirmation of item groups, response ranges, and reverse-coded items

Real data lives outside the repo; never read it, never ask for its path or filename.

## Workflow

1. Read the constructs block of `plans/analysis_plan.yaml`.
2. Confirm with the user: item groups per construct, response range, reverse-coded items. Do not infer reverse coding from item names.
3. Write `plans/sem_measurement_plan.yaml`.
4. Generate `scripts/sem_measurement.R` per `references/sem-measurement-rules.md`:
   - Cronbach's alpha per construct, computed in base R (no psych package).
   - Scale scores (row means with a minimum-completion rule) for descriptive use.
   - CFA measurement model in lavaan: each construct measured by its items; report loadings and fit indices (CFI, TLI, RMSEA, SRMR).
5. Verify: `Rscript scripts/sem_measurement.R` on the synthetic data; fix until it runs cleanly. Warn the user that fit values from synthetic data are meaningless by design (items are simulated independently); only "the code runs" matters.
6. Write `plans/sem_measurement_notes.md`: how to run on real data, thresholds for judging alpha and fit on REAL output, what to do if a construct fails.

## Confirmation Prompt

```text
I understand these constructs:
- [construct]: [items]  (response range: 1-5, reverse-coded: none)
- ...

I will compute Cronbach's alpha (base R), scale scores, and a CFA measurement
model in lavaan. lavaan is the only package this track uses - confirm it is
installed (install.packages("lavaan") once) and confirm the item groups.
```

## Required Outputs

Always produce:

- `plans/sem_measurement_plan.yaml` (including the structured `measurement_model.estimator` block -- see Phase 0/3)
- `scripts/sem_measurement.R` (verified on synthetic data) and, when the pack's Python mirror is in use, `scripts/sem_measurement.py`
- `plans/sem_measurement_notes.md`
- Reliability (alpha + omega), convergent validity (AVE/CR), and discriminant validity (HTMT) outputs -- see Diagnostics below

Use `references/sem-measurement-rules.md`.
Use `references/sem-measurement-plan-template.md`.

## Diagnostics (Phase 3 of the statistical-methods roadmap)

Likert items are ordinal, not continuous -- fitting them with ML (which assumes continuous, multivariate-normal data) is the wrong default:

- **Estimator.** Default to WLSMV (lavaan) / DWLS (semopy, Python) on the polychoric correlation matrix, with every Likert item (and any binary distal outcome used later in the structural model) declared ordinal. `method: ML` requires a stated `rationale` in `measurement_model.estimator` (e.g. >= 7 response categories) -- it is not the default.
- **Reliability.** Report McDonald's omega alongside Cronbach's alpha -- alpha assumes tau-equivalence (equal loadings), which the CFA usually contradicts; omega doesn't need that assumption.
- **Convergent validity.** AVE (>= 0.50) and composite reliability (>= 0.70) per construct.
- **Discriminant validity.** HTMT ratio between every pair of constructs (< 0.85 strict / < 0.90 lenient). Two conceptually-opposite constructs (e.g. satisfaction and burnout) are not automatically empirically distinct -- check it.

The Python reference implementation is `tools/sem_track` (`fit_measurement_model`, `reliability_from_cfa`, `average_variance_extracted`, `composite_reliability`, `htmt`) -- mirror its formulas if writing the R equivalent. Its `compat.py` also documents three real semopy/numpy/scipy compatibility bugs that block ordinal fitting entirely on a current environment; check that module before concluding an ordinal fit is failing for a statistical reason.

## Package Constraint

Base R for everything except the CFA/SEM calls, which use `lavaan` — the single allowed package of the SEM track. Never auto-install; include `library(lavaan)` with a comment noting the one-time install command.

## Boundaries

Do not run the structural model here; that is Stage D4.
Do not decide item grouping purely from statistical output.
Do not remove items automatically without user confirmation.
Do not treat Cronbach's alpha as proof of validity.
Do not interpret fit indices computed on synthetic data as evidence about the instrument.

## Teaching Line

Before modeling relationships between constructs, ask whether the constructs are measured credibly at all.
