# Statistical Analysis Plan — example-clinical

> **Note on provenance — weaker than crp-mortality/burnout-mediation.** This
> project's `dr_workflow_state.yaml` was stuck at its fresh-project template
> (everything `not_started`, `research_question: ""`) even though `scripts/desc.R`,
> `scripts/infer.R`, and their Python mirrors, plus `outputs_synthetic/`, already
> existed and were complete. There is no recorded trail of the user confirming
> variable roles the way there is for crp-mortality or burnout-mediation — every
> role below is **reverse-engineered from what the scripts actually reference**
> (`source: inferred_from_script` in `plans/analysis_plan.yaml`), not from a
> conversation. Treat every `confirmed` tag below with that caveat in mind, and
> review this document before trusting it as a real pre-registration.

## A. Research question

Does treatment arm affect 30-day mortality, adjusted for baseline clinical risk
factors? `assumed` — restated from `scripts/infer.R`'s crude/adjusted structure
(`predictor_var <- "treatment"`, `outcome_var <- "mortality_30day"`); the original
question was never recorded anywhere in the project.

## B. Workflow track and mode

```text
track:  medical
mode:   all_steps
```

Track: taken from `dr_workflow_state.yaml`'s `workflow_track: "medical"` field —
`assumed` in the sense that it was never re-confirmed by the user after the fact,
but it is consistent with every script in the project.
Mode: recorded retroactively as `all_steps` — `desc.R`/`infer.R` (crude + adjusted)
already existed as a complete set before this SAP.

## C. Variable roles

| Variable | Type (from pattern) | Role | Basis |
|---|---|---|---|
| mortality_30day | binary | outcome | assumed |
| treatment | binary | main_predictor | assumed |
| age | integer | confounder | assumed |
| sex | binary | confounder | assumed |
| bmi | numeric | confounder | assumed |
| diabetes | binary | confounder | assumed |
| hypertension | binary | confounder | assumed |
| smoking | binary | confounder | assumed |
| egfr | numeric | confounder | assumed |
| hba1c | numeric | confounder | assumed |
| crp | numeric | confounder | assumed |
| sbp | integer | not_used | assumed |
| dbp | integer | not_used | assumed |
| length_of_stay | integer | not_used | assumed |
| complication | binary | not_used | assumed |
| patient_id | id_like | excluded | confirmed |

Everything but `patient_id` is `assumed`, not `confirmed` — see the provenance
note above. `sbp`, `dbp`, `length_of_stay`, and `complication` are excluded from
both scripts with **no documented reason** (unlike crp-mortality, where
`complication`'s post-exposure risk was at least noted). Flagged again in K.

### C1. Confounders — one reason each

| Confounder | Why it is in the model | Basis |
|---|---|---|
| age | Plausible risk factor for mortality, independent of treatment | assumed |
| sex | Baseline demographic; precision covariate | assumed |
| bmi | Metabolic risk factor plausibly associated with mortality | assumed |
| diabetes | Comorbidity associated with mortality risk | assumed |
| hypertension | Comorbidity associated with mortality risk | assumed |
| smoking | Risk factor for mortality | assumed |
| egfr | Renal function; independently predicts mortality | assumed |
| hba1c | Glycemic control; comorbidity marker | assumed |
| crp | Inflammatory marker at admission; here a covariate, not the exposure of interest (contrast with crp-mortality, where CRP *is* the main predictor) | assumed |

None of these carry a recorded reason beyond "it's in `infer.R`'s covariate list"
— they read as clinically plausible, but nobody has confirmed that reading.

## D. Table 1

```text
stratified:   yes
stratify_by:  treatment
p_values:     no
```

Matches `scripts/desc.R`'s `group_var <- "treatment"`.

## E. Figures

Not generated. Stage D2b (visual exploration) was never run for this project —
there is no `scripts/plots.R` or `scripts/plots.py`. This is a gap, not a decision;
flagged in K.

## F. Model and effect measure

```text
Binary outcome (mortality_30day) + binary main predictor (treatment)
  -> logistic regression (glm, binomial family)
  -> odds ratio (OR) with 95% CI
  -> crude model first (treatment only), then adjusted for the confounders in C1
```

## G. Conditional choices

| Situation | If assumption holds | If violated |
|---|---|---|
| Comparing continuous covariates (age, bmi, egfr, hba1c, crp) across treatment groups (once Table 1 group tests land — Phase 1) | two-sample t-test | Wilcoxon rank-sum |
| Cell counts in a 2×2 categorical comparison (e.g. sex × treatment) | chi-squared | Fisher's exact (any expected cell count < 5) |

## H. Missing data

```text
strategy:            complete_case
variables_affected:  none
imputation_model:    none
basis:                confirmed
```

Every one of the 16 columns in `pattern/dataset_pattern.csv` shows
`missing_pct: 0`. `complete_case` is correct here regardless of the other
provenance caveats — this one is a direct read of the pattern file, not an
inference from code.

## I. Multiplicity

```text
planned_comparisons:  1
correction_method:    none_single_comparison
basis:                confirmed
```

One exposure–outcome pair (treatment → mortality_30day); crude and adjusted are
two specifications of the same estimand, not independent hypotheses.

## J. What we will not do

- No testing of every covariate as its own predictor of mortality_30day.
- No adding covariates to the adjusted model after seeing results.
- No reporting a subgroup finding that was not planned here.

## K. Open assumptions

- **The whole variable-role table is inferred from code, not confirmed by a
  user.** This is the central caveat of this document — see the provenance
  note at the top.
- `sbp`, `dbp`, `length_of_stay`, `complication` are excluded from both scripts
  with no stated reason. Could be a deliberate scoping decision that was never
  written down, or an oversight. Needs a real answer before this project is
  treated as more than a worked demo.
- No Stage D2b visual-exploration script exists for this project (Section E).
- `sex` here is coded `factor(..., levels = c("Nam", "Nữ"))` (Nam as reference) —
  the **opposite reference order** from crp-mortality's
  `factor(..., levels = c("Nữ", "Nam"))`. Not a bug (each project's own OR
  interpretation is still internally consistent), but worth knowing if the two
  projects are ever compared side by side.
- No strong multicollinearity is assumed among the 9 adjustment covariates; not
  yet checked (Phase 1 of the roadmap adds a VIF check).
- This SAP was recorded retroactively, with a weaker provenance trail than
  crp-mortality/burnout-mediation (see top-of-document note).
