"""Phase 3 SEM-track statistical upgrades from the roadmap: the ordinal
WLSMV/DWLS estimator, bootstrap mediation CIs, McDonald's omega,
convergent/discriminant validity (AVE/CR/HTMT), and nested model
comparison.

Importing this package applies `compat.py`'s semopy/numpy/scipy patches
(see that module's docstring) -- required for any ordinal/DWLS/WLS fit,
harmless for plain ML fits.
"""

from . import compat as _compat  # noqa: F401  (applies patches on import)
from .estimator import FitResult, build_cfa_syntax, factor_scores, fit_measurement_model, fit_structural_model
from .invariance import ConfiguralResult, ItemInvarianceResult, configural_check, metric_invariance_bootstrap
from .reliability import ReliabilitySummary, cronbach_alpha, mcdonald_omega, reliability_from_cfa
from .validity import average_variance_extracted, composite_reliability, htmt, htmt_matrix
from .mediation import (
    MediationBootstrapResult,
    RegressionBootstrapResult,
    bootstrap_mediation,
    bootstrap_structural_regression,
)
from .model_comparison import (
    ModelComparisonResult,
    RegressionComparisonResult,
    compare_nested_models,
    compare_nested_regressions,
)

__all__ = [
    "FitResult",
    "build_cfa_syntax",
    "factor_scores",
    "fit_measurement_model",
    "fit_structural_model",
    "ConfiguralResult",
    "ItemInvarianceResult",
    "configural_check",
    "metric_invariance_bootstrap",
    "ReliabilitySummary",
    "cronbach_alpha",
    "mcdonald_omega",
    "reliability_from_cfa",
    "average_variance_extracted",
    "composite_reliability",
    "htmt",
    "htmt_matrix",
    "MediationBootstrapResult",
    "RegressionBootstrapResult",
    "bootstrap_mediation",
    "bootstrap_structural_regression",
    "ModelComparisonResult",
    "RegressionComparisonResult",
    "compare_nested_models",
    "compare_nested_regressions",
]
