# SEM Measurement Plan Template

Write `plans/sem_measurement_plan.yaml` using this structure.

```yaml
dr_step: D3_sem
plan_version: 2

inputs:
  analysis_plan: "plans/analysis_plan.yaml"
  synthetic_dataset: "data_synthetic/synthetic_dataset.csv"
  dataset_pattern: "pattern/dataset_pattern.csv"
  item_group_source: "user_confirmation / questionnaire_documentation / inferred_from_names"

constructs:
  - construct_name: ""
    items: []
    item_source: "user_confirmation / inferred_from_names"
    response_range:
      min: null
      max: null
    reverse_coded_items: []
    reliability:
      metric: "cronbach_alpha_base_r"
      threshold_for_real_output: 0.70
      status: "pending_rstudio_output"
    scale_score:
      new_variable: ""
      method: "row_mean"
      minimum_non_missing_proportion: 0.50

measurement_model:
  estimator:
    method: "ML / WLSMV / DWLS"
    rationale: ""
    basis: "confirmed / assumed"
  lavaan_syntax: |
    construct1 =~ item1 + item2 + item3
    construct2 =~ item4 + item5 + item6
  fit_indices_to_report: ["cfi", "tli", "rmsea", "srmr"]
  fit_status: "pending_rstudio_output"

script:
  file: "scripts/sem_measurement.R"
  verified_on_synthetic: false
  note: "Synthetic fit values are meaningless by design; verification only proves the code runs."

user_confirmation:
  status: "confirmed / assumed / needs_review"
  notes: ""

readiness:
  status: "ready / needs_review / not_ready"
  blocking_issues: []
  review_issues: []
  assumptions: []

next_step:
  skill: "dr-sem-02-structural-model"
```

Reliability and fit interpretation are updated only after the user runs the script on real data and pastes the RStudio output.

## Estimator Decision

Decide the estimator here, before any fit index exists — not after, when a struggling RMSEA might quietly tempt a switch.

- `method: WLSMV` or `method: DWLS` — the default for Likert/ordinal items (polychoric correlations, robust to non-normality of a small discrete scale). Prefer `WLSMV` when items have <= 4-5 categories; `DWLS` is a reasonable alternative with similar behavior.
- `method: ML` — only when items are effectively continuous (typically >= 7 response categories, or a summed/averaged scale rather than raw items). State why in `rationale`; `ML` on a 5-point Likert item without a stated reason is a flag, not a default.

`tools/sap_gate` blocks this stage if `estimator` is a bare string rather than the `method`/`rationale`/`basis` block above, and flags `needs_revision` if `method: ML` has no `rationale`.
