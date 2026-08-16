# Statistical Analysis Plan — crp-mortality

> **Note on provenance.** This project reached Stage E before `dr-01b-analysis-sap`
> existed (`dr_workflow_state.yaml` recorded `D1b_sap: not_applicable`). This SAP is
> backfilled from the decisions already made and confirmed in `analysis_plan.yaml`,
> `inferential_analysis_plan.yaml`, `confounding_adjustment_plan.yaml`, and their
> `*_notes.md` files, as part of rolling out the Phase 0 pre-registration gate
> (`tools/sap_gate`). It is **not** a blind prospective SAP the way a new project's
> SAP would be — the decisions below were confirmed alongside seeing synthetic (not
> real) output, which is a weaker guarantee than pre-registering before any code
> exists. Sections H and I (missing data, multiplicity) are genuinely new: they were
> never recorded anywhere before this document.

## A. Research question

Association between admission CRP (C-reactive protein) concentration and 30-day
mortality, adjusted for potential risk factors. `confirmed` (`analysis_plan.yaml`,
`source: user_question`, `confidence: high`).

## B. Workflow track and mode

```text
track:  medical
mode:   all_steps
```

Track: confirmed by the user in Stage D1 (`workflow_track.value: medical`).
Mode: recorded retroactively as `all_steps` — every script (`desc.R`, `plots.R`,
`infer.R` crude and adjusted) was already generated and verified in one pass before
this SAP existed, which is what `all_steps` describes.

## C. Variable roles

| Variable | Type (from pattern) | Role | Basis |
|---|---|---|---|
| mortality_30day | binary | outcome | confirmed |
| crp | numeric | main_predictor | confirmed |
| age | integer | confounder | confirmed |
| sex | binary | confounder | confirmed |
| bmi | numeric | confounder | confirmed |
| treatment | binary | confounder | confirmed |
| sbp | integer | confounder | confirmed |
| diabetes | binary | confounder | confirmed |
| hypertension | binary | confounder | confirmed |
| smoking | binary | confounder | confirmed |
| egfr | numeric | confounder | confirmed |
| hba1c | numeric | confounder | confirmed |
| complication | binary | confounder | assumed |
| dbp | integer | not_used | confirmed |
| length_of_stay | integer | not_used | confirmed |
| patient_id | id_like | excluded | confirmed |

`complication` is marked `assumed` rather than `confirmed`, even though the user
included it: see C1.

### C1. Confounders — one reason each

| Confounder | Why it is in the model | Basis |
|---|---|---|
| age | Classic risk factor for both inflammatory markers and mortality | confirmed |
| sex | Baseline demographic; precision covariate | confirmed |
| bmi | Metabolic risk factor associated with both CRP and mortality | confirmed |
| treatment | Treatment arm could confound the CRP–mortality association if arms are unbalanced | confirmed |
| sbp | Cardiovascular risk factor | confirmed |
| diabetes | Comorbidity associated with inflammation and mortality risk | confirmed |
| hypertension | Comorbidity associated with mortality risk | confirmed |
| smoking | Risk factor for both inflammation and mortality | confirmed |
| egfr | Renal function affects CRP clearance and independently predicts mortality | confirmed |
| hba1c | Glycemic control; comorbidity marker | confirmed |
| complication | User asked to include it, but an in-hospital complication may occur *after* CRP is measured — it could be a **mediator**, not a confounder, of the CRP → mortality path. Included by user request; flagged here rather than silently accepted. | assumed |

## D. Table 1

```text
stratified:   yes
stratify_by:  mortality_30day
p_values:     no
```

No p-values in the current `desc.R`/`desc.py` (descriptive-only, per
`descriptive_analysis_notes.md`). Formal group-comparison tests are Phase 1 of the
statistical-methods roadmap, not yet implemented.

## E. Figures

| Figure | Variables | Grouped by |
|---|---|---|
| Correlation heatmap | age, bmi, sbp, dbp, egfr, hba1c, crp, length_of_stay | — |
| Boxplot series | same set | mortality_30day |

Note: the figures deliberately include `dbp` and `length_of_stay`, which are
excluded from the adjusted model — they're kept for exploratory screening even
though they aren't confounders in the causal sense used in C1.

## F. Model and effect measure

```text
Binary outcome (mortality_30day) + continuous main predictor (crp)
  -> logistic regression (glm, binomial family)
  -> odds ratio (OR) with 95% CI, per 1-unit increase in CRP
  -> crude model first (crp only), then adjusted for the confounders in C1
```

## G. Conditional choices

| Situation | If assumption holds | If violated |
|---|---|---|
| Comparing CRP across mortality_30day groups (once Table 1 group tests land — Phase 1) | two-sample t-test | Wilcoxon rank-sum (CRP is a biomarker and commonly right-skewed) |
| Cell counts in a 2×2 categorical comparison (e.g. treatment × mortality_30day) | chi-squared | Fisher's exact (any expected cell count < 5) |

## H. Missing data

```text
strategy:            complete_case
variables_affected:  none
imputation_model:    none
basis:                confirmed
```

Every one of the 16 columns in `pattern/dataset_pattern.csv` shows `missing_pct: 0.0`.
`complete_case` is the correct choice here by the SAP template's own rule of thumb
(defensible under ~5% missing) — there is nothing to impute.

## I. Multiplicity

```text
planned_comparisons:  1
correction_method:    none_single_comparison
basis:                confirmed
```

Exactly one exposure–outcome pair is tested (CRP → 30-day mortality). The crude and
adjusted models are two specifications of the *same* estimand, not two independent
hypotheses, so no multiplicity correction applies.

## J. What we will not do

- No testing of every covariate as its own predictor of mortality_30day.
- No adding covariates to the adjusted model after seeing results.
- No reporting a treatment-arm-stratified or other subgroup finding that was not planned here.

## K. Open assumptions

- `complication` may be a post-exposure mediator rather than a confounder (see C1) — included by user request, not statistical judgment.
- CRP's real-data distribution is unknown; the Table 1 group-comparison test (Section G) is written to branch at runtime once implemented, not fixed in advance.
- No strong multicollinearity is assumed among the 11 adjustment covariates; not yet checked (Phase 1 of the roadmap adds a VIF check).
- This SAP was recorded retroactively (see provenance note at top) — decisions came alongside synthetic-data verification, not blind.
