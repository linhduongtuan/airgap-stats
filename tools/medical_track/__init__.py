"""Phase 2 medical-track statistical upgrades from the roadmap: Firth
penalized logistic regression, non-linear biomarker handling, time-to-event
modeling, propensity-score sensitivity analysis, and FDR control.

Each module is independent and importable on its own; none of it assumes
the others were run.
"""

from .firth_logistic import FirthResult, firth_logistic_regression
from .nonlinearity import log_transform_if_skewed, restricted_cubic_spline_basis
from .multiplicity import benjamini_hochberg
from .survival import cox_ph, kaplan_meier
from .propensity import e_value, propensity_scores, psm_match, iptw_weights

__all__ = [
    "FirthResult",
    "firth_logistic_regression",
    "log_transform_if_skewed",
    "restricted_cubic_spline_basis",
    "benjamini_hochberg",
    "kaplan_meier",
    "cox_ph",
    "propensity_scores",
    "psm_match",
    "iptw_weights",
    "e_value",
]
