# Confounding Adjustment Plan Template

Write `plans/confounding_adjustment_plan.yaml` using this structure.

```yaml
dr_step: D4
plan_version: 2

inputs:
  analysis_plan: "plans/analysis_plan.yaml"
  inferential_analysis_plan: "plans/inferential_analysis_plan.yaml"
  synthetic_dataset: "data_synthetic/synthetic_dataset.csv"

link_to_d3:
  same_outcome_as_d3: true
  same_predictor_as_d3: true
  same_model_family_as_d3: true
  same_effect_measure_as_d3: true
  crude_model:
    formula: ""
    model_family: ""
    effect_measure: ""

variables:
  outcome:
    name: null
    type: "unknown"
  main_predictor:
    name: null
    type: "unknown"
  covariates:
    included: []
    excluded: []
    source: "analysis_plan / user_confirmation / assumed"
    rationale: ""
    confounder_selection:
      method: "dag / change_in_estimate / literature_fixed_list"
      criteria: ""
      change_in_estimate_threshold_pct: null
      basis: "confirmed / assumed"

adjusted_model:
  formula: ""
  model_family: ""
  effect_measure: ""
  reason: ""

comparison:
  compare_crude_vs_adjusted: true
  main_question: "Does the estimate for the main predictor materially change after adjustment?"
  compare:
    - "estimate magnitude"
    - "estimate direction"
    - "95% CI"
    - "p-value as secondary information"

script:
  file: "scripts/infer.R"
  section: "adjusted"
  verified_on_synthetic: false

user_confirmation:
  status: "confirmed / assumed / needs_review"
  notes: ""

readiness:
  status: "ready / needs_review / not_ready"
  blocking_issues: []
  review_issues: []
  assumptions: []

reporting:
  table_title: "Crude and adjusted association between [predictor] and [outcome]"
  footnote: "Adjusted for [covariates]."
  causal_language_allowed: false

next_step:
  skill: "dr-05-present-results"
```

## Confirmation Status

Use:

- `confirmed`: user explicitly approved the covariate list
- `assumed`: user asked to proceed or did not know what to choose
- `needs_review`: covariate list is weak, unclear, or likely incomplete

## Confounder Selection Method

`confounder_selection` records *how* the covariate list was chosen, not just what it is — pre-registered in the SAP (Section C1) so the method can't be picked after seeing which adjustment "looks best."

- `method: dag` — covariates chosen from a stated causal diagram (confounders of the predictor-outcome relationship, not mediators or colliders). Put the diagram's reasoning in `criteria`.
- `method: change_in_estimate` — start from the full candidate list, drop variables one at a time, keep any whose removal shifts the main-predictor estimate by more than `change_in_estimate_threshold_pct` (10% is the common default). Requires `change_in_estimate_threshold_pct` to be set.
- `method: literature_fixed_list` — covariates fixed in advance from prior published models on this outcome; cite the source in `criteria`.

`tools/sap_gate` flags this block `needs_revision` if it is missing, and `blocked` if `method` is unset while `covariates.included` is non-empty (a covariate list with no stated selection rule).
