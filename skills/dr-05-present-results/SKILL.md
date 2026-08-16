---
name: dr-05-present-results
description: "Stage E of the DR workflow: turn prior DR plans and real RStudio output into traceable manuscript-ready result tables and Results text in results_real/. Use when the user has run the project's scripts on the real dataset locally and pastes the output, for either the medical track (crude/adjusted models) or the SEM track (measurement + structural models)."
---

# DR Stage E: Present Results

Use this skill after Stage D is complete and the user has run the project's scripts on the real dataset in RStudio.

The goal is to present results clearly without changing the analysis. Every number and claim must trace back to prior plans or user-provided RStudio output.

## Coordination Contract

When called by `dr-workflow-orchestrator`, follow the project's plan files and `dr_workflow_state.yaml`.

After producing outputs:

- Report the exact files created.
- Do not mark the workflow complete yourself unless `results_real/results_traceability_check.yaml` is ready.
- Say that `dr-output-qa-gate` should check Stage E before the workflow is considered complete.

## Required Inputs

Medical track:

- `plans/analysis_plan.yaml`, `plans/inferential_analysis_plan.yaml`, `plans/confounding_adjustment_plan.yaml`
- RStudio output pasted by the user (or CSVs the user copied into `results_real/` from their real run: `table1.csv`, `infer_crude.csv`, `infer_crude_vs_adjusted.csv`)

SEM track:

- `plans/analysis_plan.yaml`, `plans/sem_measurement_plan.yaml`, `plans/sem_structural_plan.yaml`
- User-provided real output: alpha summary, CFA fit, `sem_estimates.csv`, `sem_fit.csv`, or pasted console output

Optional, either track (Phase 5 of the statistical-methods roadmap — only if the user provides it from their real run, never from `outputs_synthetic/`):

- Medical: `infer_adjusted_vif.csv`, `infer_adjusted_bootstrap_validation.csv`, `infer_adjusted_box_tidwell.csv`/`infer_adjusted_firth.csv` — Phase 1/2 diagnostics, reference implementation `tools/diagnostics/` (Python).
- SEM: `reliability_summary.csv`, `convergent_validity.csv`, `discriminant_validity_htmt.csv`, `sem_mediation.csv` — Phase 1/3 diagnostics, reference implementation `tools/sem_track/` (Python).
- `plans/sap.md` Section H (missing-data strategy) and the SEM plan files' `constructs[].items` — read for the auto-populated limitations paragraph, not real-run output at all; safe to read even before the real run happens.

Real data lives outside the repo; never read it, never ask for its path or filename. Never invent results from synthetic data or from `outputs_synthetic/`.

If pasted output contains the real dataset's file path or filename, do not repeat it in any artifact, and remind the user they can trim such lines before pasting.

**Text output only.** What the user pastes at this stage must be aggregate text: tables, estimates, CIs, p-values, fit indices. Never accept, request, or open a figure generated from real data — a boxplot or scatter is row-level data rendered as pixels, and one outlier dot is one identifiable participant. If the user offers a figure from their real run, decline, explain in one sentence why, and offer the alternative: describe the pattern in words, or paste the correlation matrix as numbers. Real-run figures produced by `scripts/plots.R` live outside the repo by design; leave them there.

## Workflow

1. Read the project's plan files for the active track.
2. Extract the research question, variables/constructs, model families, and effect measures.
3. Parse the user-provided RStudio output.
4. If the user also provided diagnostics output (VIF, bootstrap validation, bootstrap mediation), extract it. Separately, read `plans/sap.md` Section H and the SEM plan files' `constructs[].items` for the three auto-populated limitation flags (Phase 5 of the statistical-methods roadmap) — this step doesn't need real-run output and can happen even in a `placeholder_only` run. See `references/traceability-check-template.md`. The reference implementation for both extractions is Python: `tools/reporting/diagnostics_extraction.py` and `tools/reporting/limitations_extraction.py` — call `build_diagnostics_extracted(...)` / `build_limitations_pulled_forward(...)` directly (with real-run CSV text and plan-file text as arguments) rather than deriving the numbers by hand; both are tested against every project's real plan files in `tests/test_reporting.py`.
5. Create `results_real/results_traceability_check.yaml`, including `diagnostics_extracted` and `limitations_pulled_forward`.
6. If key numbers are missing or outputs conflict with the plans, stop and ask.
7. Format the manuscript result table(s), adding the optional Diagnostics Table when step 4 found real diagnostics output.
8. Write the Results paragraph, adding the optional Diagnostics / Bootstrap Indirect Effect sentences when applicable.
9. Write `results_real/present_results.md` with table, paragraph, footnote, and limitations — the limitations section is the union of any study-specific limitation plus every `limitations_pulled_forward` entry whose `include_in_limitations` is `true`.

## Required Outputs

Always produce, inside `results_real/`:

- `results_traceability_check.yaml`
- `manuscript_results_table.md`
- `results_paragraph.md`
- `present_results.md`

Use `references/traceability-check-template.md`.
Use `references/results-reporting-rules.md`.
Use `references/manuscript-table-template.md`.
Use `references/results-paragraph-template.md`.

For the SEM track, the manuscript table reports fit indices and structural path estimates (unstandardized + standardized, 95% CI, p-value); adapt the templates accordingly and include a brief measurement sentence (alpha / CFA fit) before the structural results.

## Traceability Rule

Every reported number must come from user-provided real-run output. Every interpretation must match the plans from Stages D1-D4.

If the user has not provided real output, create placeholders only and label them as placeholders. Do not fill numeric values from the synthetic run.

Exception: `limitations_pulled_forward`'s three flags (Phase 5) come from plan files, not real-run output — they describe pre-registered decisions (missing-data strategy, construct item counts) that exist before any result does, and the synthetic-verification note is a fact about the workflow, not a number from any run. It's fine to populate that block even in a `placeholder_only` run.

## Stop Conditions

Stop and ask the user for clarification when:

- Real output is absent and the user expects final numeric results.
- Output uses a different outcome, predictor, construct, or effect measure than the plans.
- Adjusted covariates or structural paths in the output conflict with the plans.
- A required estimate, CI, p-value, or fit index is missing.

## Formatting Defaults

- Estimates and CIs: 2 decimal places; p-values: 3 decimals or `<0.001`; fit indices: 2-3 decimals.
- Effect size first, confidence interval second, p-value last.

## Boundaries

Do not run new analysis.
Do not change models, covariates, items, or paths.
Do not write a full Discussion section.
Do not claim the result is guaranteed publication-ready.
Do not make causal claims unless the study design and prior plans explicitly support causal language.

## Teaching Line

Publication-ready means the reader can understand, check, and trust the result at a reasonable level.
