# Statistical Analysis Plan — burnout-mediation

> **Note on provenance.** This project reached Stage E before `dr-01b-analysis-sap`
> existed (`dr_workflow_state.yaml` recorded `D1b_sap: not_applicable`). This SAP is
> backfilled from the decisions already made and confirmed in `analysis_plan.yaml`,
> `sem_measurement_plan.yaml`, `sem_structural_plan.yaml`, and their `*_notes.md`
> files, as part of rolling out the Phase 0 pre-registration gate (`tools/sap_gate`).
> It is **not** a blind prospective SAP — the decisions below were confirmed
> alongside seeing synthetic (not real) output. Sections H and I (missing data,
> multiplicity) are genuinely new: they were never recorded anywhere before this
> document. Section K also surfaces an estimator disagreement already flagged in
> `data_readiness_summary.md` and never resolved.

## A. Research question

Whether Burnout mediates the relationship between Job Satisfaction and turnover
intention. `confirmed` (`analysis_plan.yaml`, `source: user_question`,
`confidence: high`).

## B. Workflow track and mode

```text
track:  sem
mode:   all_steps
```

Track: confirmed by the user in Stage D1 (`workflow_track.value: sem`).
Mode: recorded retroactively as `all_steps` — measurement model, structural model,
and descriptive/figure scripts were all generated and verified in one pass before
this SAP existed.

## C. Constructs and variable roles

SEM track: constructs replace the plain variable-role table for the latent items;
observed covariates keep their own table below.

| Construct | Items | Role | Basis |
|---|---|---|---|
| Job_Satisfaction | js_q1, js_q2, js_q3, js_q4, js_q5 | main_predictor (latent) | confirmed |
| Burnout | bo_q1, bo_q2, bo_q3, bo_q4, bo_q5 | mediator (latent) | confirmed |

| Variable | Type (from pattern) | Role | Basis |
|---|---|---|---|
| turnover_intent | binary | outcome | confirmed |
| age | integer | confounder | confirmed |
| gender | binary | confounder | confirmed |
| education | categorical (4 levels) | confounder | confirmed |
| tenure_years | numeric | confounder | confirmed |
| job_satisfaction (composite score) | numeric | not_used | assumed |
| burnout_score (composite score) | numeric | not_used | assumed |
| income | integer | not_used | assumed |
| work_hours | numeric | not_used | assumed |
| work_mode | categorical | not_used | assumed |
| wlb | integer_scale (Likert 1-5) | not_used | assumed |
| respondent_id | id_like | excluded | confirmed |

The four `not_used` observed variables (income, work_hours, work_mode, wlb) were
flagged in `data_readiness_summary.md` as "unused so far; include as extra controls
or exclude?" and never explicitly resolved — carried forward here as `assumed`
rather than silently dropped. The two composite-score columns (`job_satisfaction`,
`burnout_score`) exist for descriptive use only; the SEM model uses the raw items
via the latent constructs above, not these row-mean scores.

### C1. Observed covariates — one reason each

| Covariate | Why it is in the model | Basis |
|---|---|---|
| age | Demographic control; plausible influence on both Burnout and turnover intent | confirmed |
| gender | Demographic control | confirmed |
| education | Demographic control; dummy-coded with THPT as reference | confirmed |
| tenure_years | Organizational-tenure control; plausible influence on both Burnout and turnover intent | confirmed |

## D. Table 1

```text
stratified:   yes
stratify_by:  turnover_intent
p_values:     no
```

No p-values in the current `desc.R`/`desc.py`. Formal group-comparison tests are
Phase 1 of the statistical-methods roadmap, not yet implemented.

## E. Figures

SEM track: heatmap uses scale items ordered by construct; boxplot series shows one
box per item.

| Figure | Variables | Grouped by |
|---|---|---|
| Item correlation heatmap | js_q1–js_q5 (Job Satisfaction), bo_q1–bo_q5 (Burnout), turnover_intent (Turnover) | — (block-outlined by construct) |
| Item boxplot series | same set | — (one box per item, colored by construct) |

## F. Model and effect measure

```text
Latent mediation model:
  Job_Satisfaction (latent, main predictor)
    -> Burnout (latent, mediator)
    -> turnover_intent (binary outcome)
  plus a direct path Job_Satisfaction -> turnover_intent
  controls: age, gender, education, tenure_years (on both Burnout and turnover_intent)
  -> standardized path coefficients (STDYX)
  -> indirect (a x b), direct (c'), and total (c' + a x b) effects
```

## G. Conditional choices

| Situation | If assumption holds | If violated |
|---|---|---|
| Comparing age/tenure_years across turnover_intent groups (once Table 1 group tests land — Phase 1) | two-sample t-test | Wilcoxon rank-sum |
| Cell counts in gender x turnover_intent or education x turnover_intent | chi-squared | Fisher's exact (any expected cell count < 5) |

The SEM estimator choice (ML vs. WLSMV/DWLS for the Likert items and the binary
distal outcome) is its own dedicated, structured decision — see
`plans/sem_measurement_plan.yaml: measurement_model.estimator` and Section K below,
not a Table-1-style branch.

## H. Missing data

```text
strategy:            complete_case
variables_affected:  none
imputation_model:    none
basis:                confirmed
```

Every one of the 22 columns in `pattern/dataset_pattern.csv` shows `missing_pct: 0`.
`complete_case` is the correct choice here — there is nothing to impute.

## I. Multiplicity

```text
planned_comparisons:  1
correction_method:    none_single_comparison
basis:                confirmed
```

One pre-specified structural model is tested (the Job_Satisfaction → Burnout →
turnover_intent mediation with a direct path). The a/b/c'/indirect/total effects
are facets of that one model, not independent hypothesis tests, so no multiplicity
correction applies.

## J. What we will not do

- No testing every construct or covariate as an alternative outcome predictor.
- No adding structural paths after seeing fit indices.
- No reporting an unplanned moderation or interaction effect.

## K. Open assumptions

- **Estimator disagreement — resolved for the Python scripts, open for R.**
  `turnover_intent` is binary and the Job Satisfaction / Burnout items are
  5-point Likert — `data_readiness_summary.md` flagged "SEM needs DWLS
  estimator in lavaan" at Stage D1. `scripts/sem_measurement.py` and
  `scripts/sem_structural.py` now fit via DWLS (semopy's WLSMV-equivalent
  estimator, `tools/sem_track`) as Phase 3 of the statistical-methods
  roadmap; `measurement_model.estimator` in `plans/sem_measurement_plan.yaml`
  now records `method: DWLS`, `basis: confirmed`. `scripts/sem_measurement.R`
  / `sem_structural.R` still use plain ML — the R-side port of Phase 3 has
  not been done. Also note: a single joint DWLS fit of the *full* structural
  model (measurement + mediation paths together) is numerically unstable in
  semopy 2.3.11 for a model this size, so the Python structural script uses
  a two-step factor-score-regression approach instead (see
  `tools/sem_track/mediation.py`'s docstring for why).
- Reverse coding for js_q*/bo_q* items was never checked against the original
  questionnaire; assumed **no reverse coding** (per `sem_measurement_notes.md`).
- income, work_hours, work_mode, wlb are assumed `not_used`; never explicitly
  confirmed either way (see C).
- No strong multicollinearity is assumed among the four observed covariates; not
  yet checked.
- This SAP was recorded retroactively (see provenance note at top) — decisions
  came alongside synthetic-data verification, not blind.
