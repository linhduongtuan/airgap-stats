# Results Traceability Check Template

Write `results_traceability_check.yaml` before writing final results.

```yaml
dr_step: 5
plan_version: 1

inputs:
  analysis_plan: "analysis_plan.yaml"
  inferential_analysis_plan: "inferential_analysis_plan.yaml"
  confounding_adjustment_plan: "confounding_adjustment_plan.yaml"
  rstudio_output_source: "pasted_output / file / missing"

traceability_check:
  research_question_from_step1: ""
  crude_model_from_step3:
    formula: ""
    model_family: ""
    effect_measure: ""
  adjusted_model_from_step4:
    formula: ""
    model_family: ""
    effect_measure: ""
    covariates: []
  rstudio_output_available: false
  all_required_numbers_found: false
  mismatches: []
  status: "ready / needs_clarification / placeholder_only"

numbers_extracted:
  crude:
    estimate: null
    ci_lower: null
    ci_upper: null
    p_value: null
  adjusted:
    estimate: null
    ci_lower: null
    ci_upper: null
    p_value: null

reporting_decisions:
  table_type: "crude_and_adjusted"
  decimal_places:
    estimate: 2
    ci: 2
    p_value: 3
  causal_language_allowed: false

# --- Phase 5 of the statistical-methods roadmap: optional, only populate the
# sub-blocks that apply to this project's real-run output. Never fill a
# number here from the synthetic run -- leave it null and set available: false.

diagnostics_extracted:
  vif:
    source: "infer_adjusted_vif.csv (real run) or user-pasted output"
    available: false
    max_vif: null
    flagged_terms: []          # term names where vif > 5
  bootstrap_validation:
    source: "infer_adjusted_bootstrap_validation.csv (real run) or user-pasted output"
    available: false
    n_boot: null
    apparent_auc: null
    corrected_auc: null
    corrected_calibration_slope: null
  nonlinearity_refit:
    source: "infer_adjusted_box_tidwell.csv / infer_adjusted_firth.csv (real run)"
    available: false
    firth_refit_terms: []      # terms refit under Firth's penalized likelihood
    log_or_spline_terms: []    # terms transformed after a Box-Tidwell flag
  bootstrap_mediation:         # SEM mediation models only
    source: "sem_mediation.csv (real run) or user-pasted output"
    available: false
    n_boot: null
    a: null
    a_ci_low: null
    a_ci_high: null
    b: null
    b_ci_low: null
    b_ci_high: null
    c_prime: null
    c_prime_ci_low: null
    c_prime_ci_high: null
    indirect: null
    indirect_ci_low: null
    indirect_ci_high: null
    mediation_conclusion: "none / partial / full"   # derived: does the indirect CI exclude 0? does c' CI include 0?

limitations_pulled_forward:
  missing_data:
    source: "plans/sap.md Section H"
    strategy: ""                    # complete_case | multiple_imputation, copied verbatim
    variables_affected: []
    include_in_limitations: false   # true only when strategy == complete_case AND variables_affected is non-empty
  single_item_constructs:
    source: "plans/sem_measurement_plan.yaml or plans/sem_structural_plan.yaml"
    flagged_constructs: []          # constructs whose items list has length 1
    include_in_limitations: false   # true only when flagged_constructs is non-empty
  synthetic_verification_note:
    source: "workflow design -- true for every DR project"
    include_in_limitations: true    # always true; this is a methods-transparency note, not a data limitation
```

## Status Values

Use:

- `ready`: plans and RStudio output align, and required numbers are available.
- `needs_clarification`: mismatch or missing values prevent final writing.
- `placeholder_only`: no numeric output is available, so only templates can be written.

## Mismatch Examples

Record mismatches clearly:

- `Outcome in RStudio output differs from analysis_plan.yaml.`
- `Adjusted covariates in R output differ from Step 4 plan.`
- `Effect measure is OR in plan but HR in output.`
- `p-value missing for adjusted model.`

## Populating `diagnostics_extracted` (Phase 5 of the statistical-methods roadmap)

This block is entirely optional — leave every sub-block at its `available: false` default when the user hasn't provided that diagnostic. Never set `available: true` and fill numbers from `outputs_synthetic/*.csv`; those files exist only to prove the code runs, and Phase 1/2/3's own scripts document that fit is expected to look degenerate there. Only real-run numbers (pasted output, or CSVs the user copied out of their real RStudio session into `results_real/`) belong here. When present, use these fields to fill the Diagnostics Table and Diagnostics/Bootstrap Indirect Effect sentences in the paired templates.

Don't derive `max_vif`, `mediation_conclusion`, etc. by hand — call `tools.reporting.diagnostics_extraction.build_diagnostics_extracted(...)` with the real-run CSV text (VIF, bootstrap validation, Firth/Box-Tidwell, bootstrap mediation) and merge its output into this block's fields; it's the tested reference implementation, including the none/partial/full mediation-conclusion logic.

## Populating `limitations_pulled_forward` (Phase 5 of the statistical-methods roadmap)

Unlike `diagnostics_extracted`, these three flags are read from **plan files** (Stage D1b/D3 artifacts), not from real-run output — they describe decisions made before any result existed, so they're safe to read regardless of whether the real run has happened yet:

- `missing_data`: read `strategy` and `variables_affected` straight from `plans/sap.md` Section H. Set `include_in_limitations: true` only if `strategy` is `complete_case` and `variables_affected` is non-empty (a `complete_case` strategy with zero affected variables has nothing to caveat).
- `single_item_constructs`: scan every construct's `items` list in `plans/sem_measurement_plan.yaml` (and `plans/sem_structural_plan.yaml` if constructs are redefined there); any construct with exactly one item goes into `flagged_constructs`.
- `synthetic_verification_note`: no lookup needed — always `true`. It documents the DR workflow's own privacy design, not something that varies by project.

If a medical-track project has no SEM plan files, or a SEM-track project has no `sap.md` Section H populated (shouldn't happen post-Phase-0, but check), leave that sub-block at its default rather than guessing.

Same as above: call `tools.reporting.limitations_extraction.build_limitations_pulled_forward(sap_md_text, sem_plan_yaml_texts)` rather than re-deriving the parsing by hand — it reuses `tools.sap_gate.sap_parser` for Section H so the two skills never disagree about how to read it.
