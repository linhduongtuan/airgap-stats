# Statistical Analysis Plan — example-survey-sem

> **Note on provenance — weaker than crp-mortality/burnout-mediation.** Same
> situation as `example-clinical/plans/sap.md`: `dr_workflow_state.yaml` was stuck
> at its fresh-project template even though `scripts/desc.R`,
> `scripts/sem_measurement.R`, `scripts/sem_structural.R`, and their Python
> mirrors already existed, complete, with output in `outputs_synthetic/`. Every
> role below is reverse-engineered from script content
> (`source: inferred_from_script`), not from a recorded conversation. Review
> before trusting this as a real pre-registration.

## A. Research question

Do job satisfaction and burnout, together with remote-work arrangement, predict
turnover intention? `assumed` — restated from `scripts/sem_structural.R`'s model
(`turnover_intent ~ burnout + jobsat + remote`); the original question was never
recorded anywhere in the project.

## B. Workflow track and mode

```text
track:  sem
mode:   all_steps
```

Track: taken from `dr_workflow_state.yaml`'s `workflow_track: "sem"` field.
Mode: recorded retroactively as `all_steps` — the measurement model, structural
model, and descriptive script all already existed as a complete set.

## C. Constructs and variable roles

| Construct | Items | Role | Basis |
|---|---|---|---|
| jobsat | js_q1, js_q2, js_q3, js_q4, js_q5 | main_predictor (latent) | assumed |
| burnout | bo_q1, bo_q2, bo_q3, bo_q4, bo_q5 | parallel predictor (latent) — **not** a mediator here | assumed |

Unlike `burnout-mediation`, this project's `scripts/sem_structural.R` has **no**
`burnout ~ jobsat` path. `jobsat` and `burnout` are both direct predictors of
`turnover_intent`; there is no indirect-effect decomposition to report.

| Variable | Type (from pattern) | Role | Basis |
|---|---|---|---|
| turnover_intent | binary | outcome | assumed |
| work_mode | categorical | source of `remote` covariate + Table 1 group variable | assumed |
| remote (derived: work_mode == "Remote") | binary | confounder (structural model) | assumed |
| age | integer | not_used_in_sem | assumed |
| gender | binary | not_used_in_sem | assumed |
| education | categorical | not_used_in_sem | assumed |
| tenure_years | numeric | not_used_in_sem | assumed |
| income | integer | not_used | assumed |
| work_hours | numeric | not_used | assumed |
| wlb | integer_scale | not_used | assumed |
| job_satisfaction (composite score) | numeric | not_used | assumed |
| burnout_score (composite score) | numeric | not_used | assumed |
| respondent_id | id_like | excluded | confirmed |

Four demographic variables (age, gender, education, tenure_years) are profiled in
Table 1 but **never entered as structural-model covariates**, with no documented
reason — flagged again in K. Contrast with `burnout-mediation`, which uses exactly
these four as structural covariates.

### C1. Observed covariates — one reason each

| Covariate | Why it is in the model | Basis |
|---|---|---|
| remote | Work arrangement plausibly influences turnover intent independent of job satisfaction/burnout | assumed |

`remote` is the *only* observed covariate in the structural model — everything
else in C's "not_used" rows was profiled descriptively but never offered as a
model covariate.

## D. Table 1

```text
stratified:   yes
stratify_by:  work_mode
p_values:     no
```

Matches `scripts/desc.R`'s `group_var <- "work_mode"`. Note this stratifies by
work arrangement, **not** by the outcome `turnover_intent` — unusual for this
kind of model; see K.

## E. Figures

Not generated. Stage D2b (visual exploration) was never run for this project —
there is no `scripts/plots.R` or `scripts/plots.py`.

## F. Model and effect measure

```text
Measurement model (Stage D3-SEM):
  jobsat  =~ js_q1 + js_q2 + js_q3 + js_q4 + js_q5
  burnout =~ bo_q1 + bo_q2 + bo_q3 + bo_q4 + bo_q5

Structural model (Stage D4-SEM), direct-effects only (no mediation path):
  turnover_intent (binary outcome) ~ burnout + jobsat + remote
  -> standardized path coefficients (STDYX)
```

## G. Conditional choices

| Situation | If assumption holds | If violated |
|---|---|---|
| Comparing continuous variables (age, income, work_hours, tenure_years) across the 3 work_mode groups (once Table 1 group tests land — Phase 1) | one-way ANOVA | Kruskal-Wallis (three groups, so this is not a simple two-sample test) |
| Cell counts for gender × work_mode or education × work_mode (an r×c table) | chi-squared | Fisher's exact / simulated p-value (any expected cell count < 5) |

The SEM estimator choice (ML vs. WLSMV/DWLS) is its own dedicated, structured
decision — see `plans/sem_measurement_plan.yaml: measurement_model.estimator`
and Section K below.

## H. Missing data

```text
strategy:            complete_case
variables_affected:  none
imputation_model:    none
basis:                confirmed
```

Every one of the 22 columns in `pattern/dataset_pattern.csv` shows
`missing_pct: 0`. This one is a direct read of the pattern file, independent of
the rest of this document's provenance caveats.

## I. Multiplicity

```text
planned_comparisons:  1
correction_method:    none_single_comparison
basis:                confirmed
```

One pre-specified multivariable structural model (`turnover_intent ~ burnout +
jobsat + remote`). Three simultaneous predictors in **one** pre-specified model is
standard multivariable regression, not three independent hypothesis tests — no
multiplicity correction applies.

## J. What we will not do

- No testing every construct or covariate as an alternative outcome predictor.
- No adding structural paths (e.g. a jobsat → burnout mediation path) after seeing fit indices.
- No reporting an unplanned moderation or interaction effect.

## K. Open assumptions

- **The whole variable-role table is inferred from code, not confirmed by a
  user.** Central caveat of this document — see the provenance note at the top.
- age, gender, education, tenure_years, income, work_hours, wlb are profiled in
  Table 1 but never entered as structural-model covariates. No documented
  rationale exists; may be an incomplete model rather than a deliberate scoping
  choice. Worth comparing against `burnout-mediation`, which does use
  age/gender/education/tenure_years.
- Table 1 stratified by `work_mode` rather than by the outcome `turnover_intent`
  — atypical; flagged rather than silently accepted.
- **Estimator — resolved for the Python scripts, open for R.**
  `scripts/sem_measurement.R`/`sem_structural.R` call
  `cfa(model, data = dat, std.lv = TRUE)` / `sem(model, data = dat, std.lv = TRUE,
  warn = FALSE)` with no `ordered =` argument — plain ML on 5-point Likert items
  *and* on the binary `turnover_intent` used directly as an observed regression
  target. `scripts/sem_measurement.py`/`sem_structural.py` now fit via DWLS
  (semopy's WLSMV-equivalent, `tools/sem_track`) with every Likert item and
  `turnover_intent` declared ordinal, as Phase 3 of the statistical-methods
  roadmap; `plans/sem_measurement_plan.yaml` now records `method: DWLS`,
  `basis: confirmed`. The R scripts still use plain ML — not yet ported. The
  structural fit uses a two-step factor-score-regression approach rather than
  one joint DWLS fit (semopy 2.3.11's WLS solver is numerically unstable for a
  joint fit this size — see `tools/sem_track/mediation.py`'s docstring).
- No strong multicollinearity assumed between jobsat, burnout, and remote; not
  yet checked.
- This SAP was recorded retroactively, with a weaker provenance trail than
  crp-mortality/burnout-mediation (see top-of-document note).
