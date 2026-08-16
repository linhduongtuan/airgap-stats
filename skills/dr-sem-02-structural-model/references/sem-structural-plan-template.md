# SEM Structural Plan Template

Write `plans/sem_structural_plan.yaml` using this structure.

```yaml
dr_step: D4_sem
plan_version: 2

inputs:
  analysis_plan: "plans/analysis_plan.yaml"
  sem_measurement_plan: "plans/sem_measurement_plan.yaml"
  synthetic_dataset: "data_synthetic/synthetic_dataset.csv"

link_to_d3:
  measurement_model_unchanged: true
  constructs_used: []

structural_model:
  outcome: ""
  paths:
    - from: ""
      to: ""
      rationale: ""
  covariates_observed: []
  dummy_coding:
    - variable: ""
      coding: ""
  lavaan_syntax: |
    ...

reporting:
  fit_indices: ["cfi", "tli", "rmsea", "srmr"]
  estimates: "unstandardized + standardized, 95% CI, p-value"
  r_squared: true
  causal_language_allowed: false

script:
  file: "scripts/sem_structural.R"
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
  skill: "dr-05-present-results"
```
