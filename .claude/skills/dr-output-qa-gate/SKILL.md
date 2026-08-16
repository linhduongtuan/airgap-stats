---
name: dr-output-qa-gate
description: "Quality gate for DR workflow outputs. Use to check whether artifacts from dr-* stage skills meet their required contracts (privacy, file locations, script verification, traceability) before the orchestrator advances the project to the next stage."
---

# DR Output QA Gate

Use this skill to evaluate whether a DR workflow stage has produced the required artifacts in the active project folder and whether the user can safely move on.

This skill does not create statistical analysis. It checks contracts.

## QA Status

Return exactly one status:

- `pass`: required artifacts exist and satisfy the stage contract.
- `needs_revision`: artifacts exist but require correction before proceeding.
- `blocked`: required artifact or user input is missing.

## Output Format

```yaml
qa_status: "pass / needs_revision / blocked"
project: ""
checked_stage: ""
required_artifacts: []
missing_artifacts: []
issues: []
next_allowed_step: ""
user_action_required: ""
```

## Global Contracts (checked at every stage)

- All artifacts live inside the active project folder; nothing written elsewhere.
- No artifact contains real-data statistics (means, medians, min/max, real row counts).
- No artifact contains the real dataset's file path or filename.
- No real data exists inside the repo (the real dataset stays outside; scripts reach it only via `file.choose()` in the user's RStudio session).
- No figure derived from real data exists inside the repo, and none was opened or accepted by the agent. Figures are row-level data; scripts that draw them must write real-run output to `file.path(dirname(input_csv), "dr_figures")`, outside the pack. Only figures under `outputs_synthetic/figures/` may exist in the repo.
- Generated R code is base R only (SEM track: plus lavaan) with no `install.packages()` calls.

Block if any global contract fails.

## Verification Contract (every script-producing stage)

"Verified" means the script was actually run against the synthetic dataset and exited cleanly. It does **not** mean the agent ran it. The deliverable is code the user runs on their own machine; most agents running this pack have no R.

Accept either provenance:

- `agent`: the agent ran `Rscript <script>` and reported the result.
- `user`: the agent had no R, handed over the exact command, and the user reported a clean run.

Rules:

- Return `blocked` only if the script has been run by nobody, or was run and failed.
- **Never return `blocked` merely because the agent lacks R.** The correct status then is `needs_revision`, with `user_action_required` naming the exact command to run.
- Never accept "verified" when no run happened. Loosen *who* ran it, never *whether* it ran.
- Check the delivered script's SETTINGS block is in **synthetic mode**, so the user can run it without editing first. A script delivered in `file.choose()` mode fails this contract.
- Record the provenance in the state file as `verified_by`.

## Stage Contracts

### Stage A: Pattern Extraction

Pass if:

- `pattern/dataset_pattern.csv` exists with only the spec columns (variable, type, levels, n_distinct, missing_pct, note).
- The state file records `pattern_reviewed_by_user: true` after an explicit user confirmation.

Block if:

- The pattern file contains statistics or raw values beyond level labels.
- The review gate was skipped.
- Real data upload is being requested anywhere.

### Stage B/C: Synthesis

Pass if:

- `scripts/synthesize_data.R` exists (base R only).
- `data_synthetic/synthetic_dataset.csv` exists and its columns match the pattern file.

Block if the synthetic file is missing or columns disagree with the pattern.

### Stage D1: Understand Dataset

Required: `plans/analysis_plan.yaml`, `plans/data_readiness_summary.md`.

Pass if outcome and main predictor (or outcome construct) are present or explicitly marked for confirmation; variable roles include source and confidence; `workflow_track` is confirmed; readiness is `ready` or `needs_review` without blockers.

Block if the plan is missing, no outcome can be identified, or the pattern file and synthetic CSV disagree on core columns.

### Stage D1b: Analysis SAP and Mode

Required: `plans/sap.md`; `analysis_mode` and `sap_approved` recorded in the state file.

Pass if the SAP states, explicitly and in one place: every variable's role (outcome, main predictor, confounders, id_like/excluded); whether Table 1 is stratified and by which variable; which variables appear in which figure; and the model family plus effect measure derived from those roles. Every decision must carry `confirmed` or `assumed`. Distribution-dependent choices must be written conditionally, never fixed, since nobody has seen the real data. `analysis_mode` is `all_steps` or `step_by_step`, and `sap_approved: true` reflects an explicit user approval. The SAP also states a missing-data strategy (Section H: `complete_case` or `multiple_imputation`, with `variables_affected` read from the pattern file's `missing_pct`) and a multiplicity plan (Section I: `planned_comparisons` and a `correction_method`, `none_single_comparison` only valid when the count is 1).

Block if code was generated before the SAP was approved, if any variable is left without a role, if a distribution-dependent method was fixed without a stated fallback, or if the missing-data strategy or multiplicity plan is absent.

Prefer running `python -m tools.sap_gate <project_dir>` over re-deriving this contract by eye — it mechanically checks the missing-data and multiplicity sections (and, at D4/D3-SEM, the confounder-selection and estimator fields below) and returns the same `qa_status` vocabulary used here.

Flag as `needs_revision` if most roles are `assumed` while `analysis_mode` is `all_steps` — batching on guesswork multiplies one wrong role across every generated script. Recommend `step_by_step` instead.

### Stage D2: Descriptive Analysis

Required: `scripts/desc.R`, `plans/descriptive_analysis_notes.md`, verification outputs in `outputs_synthetic/`.

Pass if variables come from `analysis_plan.yaml` or a user override; id_like/date/unsupported variables are excluded by default; the user was asked to confirm variables/grouping (or approved them in the SAP); the script satisfies the Verification Contract.

Block if `analysis_plan.yaml` is missing, no variables are selected, or the script was run and failed on synthetic data.

### Stage D2b: Visual Exploration (optional)

Required if the stage was run: `scripts/plots.R`, `plans/visual_exploration_notes.md`, figures in `outputs_synthetic/figures/`.

Pass if plotted variables come from `analysis_plan.yaml`, a user override, or the approved SAP; the delivered script writes real-run figures outside the repo via `dirname(input_csv)`; a small-cell guard (n < 5) is present; the script satisfies the Verification Contract.

Figures render correctly as well as run. If the agent has R, it should open the PNGs under `outputs_synthetic/figures/` and check them. If it does not, the notes file must instead give the user a short visual checklist — correlation diagonal reads 1.00, matrix is symmetric, axis labels are not clipped. Do not block on the agent having looked at an image.

Block if the script would write real-data figures into the repo, if the small-cell guard is missing, or if the script was run and failed on synthetic data.

**Never block a project for not having run this stage.** If `scripts/plots.R` is absent, return `pass` with a note that D2b was skipped; D3 may proceed.

### Stage D3 (Medical): Inferential Analysis

Required: `plans/inferential_analysis_plan.yaml`, `scripts/infer.R` (crude section), `plans/inferential_analysis_notes.md`.

Pass if the research question is restated; outcome and predictor match D1; the analysis is crude/unadjusted; effect measure and model are documented; user confirmation is `confirmed` or `assumed`; the script satisfies the Verification Contract.

Block if outcome or predictor is missing, covariates were added without explicit request or SAP approval, or the script was run and failed.

### Stage D3 (SEM): Measurement Model

Required: `plans/sem_measurement_plan.yaml`, `scripts/sem_measurement.R`, `plans/sem_measurement_notes.md`.

Required also (Phase 3 — Python mirror): `outputs_synthetic/reliability_summary.csv` (alpha + omega), `convergent_validity.csv` (AVE/CR), `discriminant_validity_htmt.csv`.

Pass if item groups are confirmed or clearly `needs_review`; alpha (and, for the Python script, omega) is computed; the CFA syntax matches confirmed constructs; the script satisfies the Verification Contract; notes state that synthetic fit is meaningless. `measurement_model.estimator` is a structured decision — `method` (`ML`, `WLSMV`, or `DWLS`) plus a one-line `rationale` — made before fit indices exist, not a free-text comment deferring the choice to "documented in notes." Likert items default to `WLSMV` or `DWLS`; `ML` requires a stated reason (e.g. items are effectively continuous with >=7 response categories).

Block if constructs cannot be confirmed at all. Flag `needs_revision` if `measurement_model.estimator` is a bare string instead of the structured `method`/`rationale` block, or (Python mirror) if the Phase 3 reliability/validity outputs above don't exist.

### Stage D4 (Medical): Confounding Adjustment

Required: `plans/confounding_adjustment_plan.yaml`, updated `scripts/infer.R`, `plans/confounding_adjustment_notes.md`, `outputs_synthetic/infer_crude_vs_adjusted.csv`, and the Phase 1 diagnostics outputs (`infer_adjusted_vif.csv`, `infer_adjusted_influence.csv`, `infer_adjusted_dfbetas.csv`, `infer_adjusted_box_tidwell.csv`, `infer_adjusted_bootstrap_validation.csv`).

Pass if outcome, predictor, model family, and effect measure match D3; covariates are user-confirmed (individually or via the SAP) or marked `assumed`; the crude section is untouched; the full script satisfies the Verification Contract. The plan also states `variables.covariates.confounder_selection`: a `method` (`dag`, `change_in_estimate`, or `literature_fixed_list`), a one-line `criteria`, and — for `change_in_estimate` — a `threshold_pct`. This is the rule that produced the covariate list, not the list itself; a bare covariate list without a stated selection method is `needs_revision`.

Block if covariates are missing and adjustment is required, or the adjusted model changes the research question without confirmation. Flag `needs_revision` if `confounder_selection` is absent, or if the five diagnostics outputs above don't exist (Phase 1 — see `dr-04-confounding-adjustment`'s Diagnostics section).

### Stage D4 (SEM): Structural Model

Required: `plans/sem_structural_plan.yaml`, `scripts/sem_structural.R`, `plans/sem_structural_notes.md`. Required also (Phase 3 — Python mirror, mediation models only): `outputs_synthetic/sem_mediation.csv` with `ci_low`/`ci_high` columns populated (bootstrap CIs, not bare point estimates) and `outputs_synthetic/sem_model_comparison.csv`.

Pass if the measurement model is unchanged from D3; every structural path was shown to and confirmed by the user (individually or via the SAP); dummy coding is documented; the script satisfies the Verification Contract (a clean exit carrying a clear non-convergence message on synthetic data counts as verified).

Block if the measurement model was silently altered or paths were not confirmed. Flag `needs_revision` if a mediation model's indirect/direct/total effects are reported without bootstrap CIs (Phase 3 — see `dr-sem-02-structural-model`'s Diagnostics section).

### Stage E: Present Results

Required, in `results_real/`: `results_traceability_check.yaml`, `manuscript_results_table.md`, `results_paragraph.md`, `present_results.md`.

Pass if every number comes from user-provided real-run output; tables and paragraph match the plans; the mismatches list is empty.

Block if real output is missing while final numeric results are expected, or if outcome/predictor/effect measure/covariates/paths conflict with prior plans.

## Boundaries

Do not repair artifacts unless the user explicitly asks.
Do not invent missing values.
Do not approve a stage just because files exist; check the contract.
