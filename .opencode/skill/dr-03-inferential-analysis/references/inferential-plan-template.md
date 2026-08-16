# Inferential Analysis Plan Template

Write `plans/inferential_analysis_plan.yaml` using this structure.

```yaml
dr_step: D3
plan_version: 2

inputs:
  analysis_plan: "plans/analysis_plan.yaml"
  synthetic_dataset: "data_synthetic/synthetic_dataset.csv"
  dataset_pattern: "pattern/dataset_pattern.csv"

research_question:
  user_input: ""
  confirmed_question: ""
  question_type:
    value: "unknown"
    source: "analysis_plan"
    confidence: "low"

variables:
  outcome:
    name: null
    type: "unknown"
    source: "analysis_plan"
    confidence: "low"
  main_predictor:
    name: null
    type: "unknown"
    source: "analysis_plan"
    confidence: "low"

analysis_decision:
  scope: "crude_unadjusted"
  primary_method:
    value: "needs_clarification"
    reason: ""
  effect_measure:
    value: "needs_clarification"
    reason: ""
  model_or_test:
    value: ""
    formula: ""
    reason: ""

assumptions_to_check:
  - ""

reporting:
  estimate: ""
  uncertainty: "95% CI (Wald, confint.default)"
  p_value: true
  plain_language_interpretation: true
  causal_language_allowed: false

script:
  file: "scripts/infer.R"
  section: "crude"
  verified_on_synthetic: false

user_confirmation:
  status: "confirmed / assumed / needs_review"
  notes: ""

readiness:
  status: "ready / needs_review / not_ready"
  blocking_issues: []
  review_issues: []
  assumptions: []

next_step:
  skill: "dr-04-confounding-adjustment"
  note: "Adjusted analysis and covariate control are handled in Stage D4."
```

## Source Labels

Use: `user_confirmation`, `analysis_plan`, `pattern_file`, `synthetic_data_inspection`, `heuristic`.

## Confirmation Status

Use:

- `confirmed`: user explicitly approved the plan
- `assumed`: user asked to proceed or did not know what to choose
- `needs_review`: important method or variable choice remains uncertain
