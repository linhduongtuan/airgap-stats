"""Phase 1 diagnostics & validation infrastructure for the DR workflow.

Five checks from the statistical-methods roadmap, none of which existed
before: formal Table 1 group-comparison tests, multicollinearity (VIF),
influence diagnostics (Cook's distance / DFBETAs), a linearity-in-the-logit
check (Box-Tidwell), and bootstrap-optimism internal validation.

Every function here operates on an already-loaded pandas DataFrame or an
already-fitted statsmodels result -- this package has no opinion on where the
data came from (synthetic or real), matching the rest of the DR workflow.
"""

from .group_tests import GroupTestResult, compare_categorical, compare_continuous
from .regression_diagnostics import (
    box_tidwell_test,
    compute_dfbetas,
    compute_influence,
    compute_vif,
)
from .bootstrap_validation import BootstrapValidationResult, bootstrap_optimism

__all__ = [
    "GroupTestResult",
    "compare_continuous",
    "compare_categorical",
    "compute_vif",
    "compute_influence",
    "compute_dfbetas",
    "box_tidwell_test",
    "BootstrapValidationResult",
    "bootstrap_optimism",
]
