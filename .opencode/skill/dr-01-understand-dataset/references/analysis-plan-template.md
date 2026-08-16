# Analysis Plan Template

Write `plans/analysis_plan.yaml` using this structure. Keep the file practical rather than exhaustive.

```yaml
dr_step: D1
plan_version: 2

inputs:
  dataset_pattern: "pattern/dataset_pattern.csv"
  synthetic_dataset: "data_synthetic/synthetic_dataset.csv"
  research_question_user_input: ""

workflow_track:
  value: "unknown"        # medical / sem
  source: "not_available"
  confidence: "low"

dataset:
  unit_of_analysis:
    value: "unknown"
    source: "not_available"
    confidence: "low"
  synthetic_n_rows: null   # note: the real n is deliberately unknown to the agent

research_question:
  plain_language: ""
  question_type:
    value: "unknown"
    options_considered:
      - "descriptive"
      - "comparative"
      - "associative"
      - "predictive"
    source: "not_available"
    confidence: "low"

variables:
  outcome:
    name: null
    type: "unknown"
    source: "not_available"
    confidence: "low"
    notes: ""
  main_predictor:
    name: null
    type: "unknown"
    source: "not_available"
    confidence: "low"
    notes: ""
  covariates: []
  group_variable:
    name: null
    source: "not_available"
    confidence: "low"
  excluded_variables: []   # id_like, date, unsupported, user-excluded

# SEM track only
constructs:
  - construct_name: ""
    items: []
    response_values: ""    # from integer_scale levels, e.g. "1|2|3|4|5"
    item_source: "user_confirmation / inferred_from_names"
    reverse_coded_items: []

variable_inventory:
  - name: ""
    type: "unknown"        # from pattern file
    roles:
      - "unspecified"
    missing_pct: null      # from pattern file
    action: "keep"
    notes: ""

recommended_analysis:
  descriptive_grouping:
    variable: null
    reason: ""
  primary_model:
    value: "needs_clarification"
    reason: ""
  effect_measure:
    value: "needs_clarification"
    reason: ""

readiness:
  status: "needs_review"
  blocking_issues: []
  review_issues: []
  assumptions: []

next_step:
  skill: "dr-02-descriptive-analysis"
  needs_user_confirmation:
    - "confirm workflow track"
    - "confirm outcome"
    - "confirm main predictor"
    - "confirm covariates (medical) or constructs (sem)"
```

## Source Labels

Use these values for `source`:

- `user_question`
- `pattern_file`
- `user_note`
- `synthetic_data_inspection`
- `heuristic`
- `not_available`

## Confidence Labels

Use:

- `high`: explicitly stated by the user
- `medium`: strongly suggested by the pattern file and variable structure
- `low`: guessed from names, types, or incomplete context

## Analysis Logic Hints

Use conservative provisional recommendations:

- Binary outcome with association question: `logistic_regression`
- Continuous outcome with association question: `linear_regression`
- Categorical outcome with more than two levels: `multinomial_or_ordinal_model_needs_review`
- Time-to-event outcome with time and event variables: `survival_analysis_needs_review`
- Latent construct relationships with item-level measures: `sem_track`
- No clear outcome: `needs_clarification`

Do not recommend advanced causal methods in Stage D1 unless the user explicitly asks.
