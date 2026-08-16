"""Phase 5 of the statistical-methods roadmap: automated extraction for
Stage E (dr-05-present-results)'s ``results_traceability_check.yaml``.

The two roadmap items ("Extend results templates", "Auto-populated
limitations stub") were first implemented as prose instructions for an
agent to follow by hand (see the skill's reference templates). This
package is the missing piece: real, tested extraction code, matching the
`diagnostics_extracted` / `limitations_pulled_forward` YAML schema written
into `skills/dr-05-present-results/references/traceability-check-template.md`.

Two independent halves:

- :mod:`tools.reporting.diagnostics_extraction` -- parses **real-run**
  diagnostic CSVs (VIF, bootstrap validation, Box-Tidwell/Firth,
  bootstrapped mediation) into the `diagnostics_extracted` block. Every
  function here takes CSV *text*, not a file path -- Stage E only ever
  sees output the user pastes or copies in from their real run, never a
  path into the repo (real output lives in `results_real/`, outside
  version control by convention).
- :mod:`tools.reporting.limitations_extraction` -- reads **plan files**
  (`plans/sap.md` Section H, `plans/sem_measurement_plan.yaml` /
  `plans/sem_structural_plan.yaml`) for the three auto-pulled limitation
  flags. Unlike diagnostics, these are safe to read before the real run
  happens -- they describe decisions made at Stage D1b/D3, not results.
"""

from tools.reporting.diagnostics_extraction import (
    BootstrapMediationExtraction,
    BootstrapValidationExtraction,
    NonlinearityRefitExtraction,
    VifExtraction,
    build_diagnostics_extracted,
    extract_bootstrap_mediation,
    extract_bootstrap_validation,
    extract_nonlinearity_refit,
    extract_vif,
)
from tools.reporting.limitations_extraction import (
    LimitationsPulledForward,
    MissingDataFlag,
    SingleItemConstructsFlag,
    SyntheticVerificationFlag,
    build_limitations_pulled_forward,
    extract_missing_data_flag,
    extract_single_item_constructs,
    synthetic_verification_note,
)

__all__ = [
    "VifExtraction",
    "BootstrapValidationExtraction",
    "NonlinearityRefitExtraction",
    "BootstrapMediationExtraction",
    "extract_vif",
    "extract_bootstrap_validation",
    "extract_nonlinearity_refit",
    "extract_bootstrap_mediation",
    "build_diagnostics_extracted",
    "MissingDataFlag",
    "SingleItemConstructsFlag",
    "SyntheticVerificationFlag",
    "LimitationsPulledForward",
    "extract_missing_data_flag",
    "extract_single_item_constructs",
    "synthetic_verification_note",
    "build_limitations_pulled_forward",
]
