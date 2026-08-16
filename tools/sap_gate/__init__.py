"""Phase 0 pre-registration gate for the DR workflow.

Mechanically checks the four Phase 0 decisions from the statistical-methods
roadmap: missing-data strategy, multiplicity plan, confounder-selection
method, and the SEM ordinal-estimator decision. All four exist so a modeling
choice is on paper *before* any result has been seen -- this package is what
makes that a checkable fact instead of a hope.

Entry point: ``python -m tools.sap_gate <project_dir>``.
"""

from .gate import run_phase0_gate

__all__ = ["run_phase0_gate"]
