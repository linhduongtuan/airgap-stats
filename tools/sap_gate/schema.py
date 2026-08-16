"""Validation rules for the four Phase 0 pre-registration decisions.

Each ``check_*`` function takes the loosely-typed dict parsed out of either
``plans/sap.md`` (by :mod:`tools.sap_gate.sap_parser`) or a ``plans/*.yaml``
plan file, and returns a :class:`CheckResult`. Functions never raise on bad
input -- a malformed or missing block is itself the finding, so every
problem is collected into ``issues`` rather than stopping at the first one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

BASIS_VALUES = {"confirmed", "assumed", "needs_review"}
MISSING_DATA_STRATEGIES = {"complete_case", "multiple_imputation"}
MULTIPLICITY_METHODS = {"none_single_comparison", "bonferroni", "benjamini_hochberg"}
CONFOUNDER_METHODS = {"dag", "change_in_estimate", "literature_fixed_list"}
ESTIMATOR_METHODS = {"ML", "WLSMV", "DWLS"}
ORDINAL_DEFAULT_ESTIMATORS = {"WLSMV", "DWLS"}

# Statuses, in ascending order of severity -- mirrors dr-output-qa-gate's own
# vocabulary so a Phase 0 CheckResult can be folded straight into that
# skill's report without translation.
STATUS_RANK = {"pass": 0, "needs_revision": 1, "blocked": 2}


@dataclass
class CheckResult:
    name: str
    status: str = "pass"  # "pass" | "needs_revision" | "blocked"
    issues: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status == "pass"

    def add(self, status: str, message: str) -> None:
        """Record an issue and raise this check's status if it's more severe."""
        self.issues.append(message)
        if STATUS_RANK[status] > STATUS_RANK[self.status]:
            self.status = status


def _get(block: Optional[dict], key: str) -> Any:
    if not isinstance(block, dict):
        return None
    value = block.get(key)
    if isinstance(value, str):
        value = value.strip()
    return value


def _check_basis(result: CheckResult, block: Optional[dict], where: str) -> None:
    basis = _get(block, "basis")
    if not basis:
        result.add("blocked", f"{where}: `basis` is missing (must be confirmed/assumed/needs_review)")
    elif basis not in BASIS_VALUES:
        result.add("blocked", f"{where}: `basis: {basis}` is not one of {sorted(BASIS_VALUES)}")
    elif basis == "needs_review":
        result.add("needs_revision", f"{where}: basis is `needs_review` -- ask the user to confirm")


def check_missing_data_plan(block: Optional[dict]) -> CheckResult:
    """SAP Section H. Required in every project, both tracks."""
    result = CheckResult(name="missing_data_plan")
    where = "Section H (missing data)"
    if block is None:
        result.add("blocked", f"{where} is missing from plans/sap.md")
        return result

    strategy = _get(block, "strategy")
    if not strategy:
        result.add("blocked", f"{where}: `strategy` is missing")
    elif strategy not in MISSING_DATA_STRATEGIES:
        result.add(
            "blocked",
            f"{where}: `strategy: {strategy}` is not one of {sorted(MISSING_DATA_STRATEGIES)}",
        )
    elif strategy == "multiple_imputation" and not _get(block, "imputation_model"):
        result.add(
            "needs_revision",
            f"{where}: strategy is multiple_imputation but `imputation_model` is not stated",
        )

    if not _get(block, "variables_affected"):
        result.add(
            "needs_revision",
            f"{where}: `variables_affected` is empty -- confirm no variable used in the model has non-trivial missingness",
        )

    _check_basis(result, block, where)
    return result


def check_multiplicity_plan(block: Optional[dict]) -> CheckResult:
    """SAP Section I. Required even when the answer is a single comparison."""
    result = CheckResult(name="multiplicity_plan")
    where = "Section I (multiplicity)"
    if block is None:
        result.add("blocked", f"{where} is missing from plans/sap.md")
        return result

    method = _get(block, "correction_method")
    planned_raw = _get(block, "planned_comparisons")
    planned: Optional[int]
    try:
        planned = int(planned_raw) if planned_raw is not None else None
    except (TypeError, ValueError):
        planned = None
        result.add("blocked", f"{where}: `planned_comparisons: {planned_raw!r}` is not an integer")

    if not method:
        result.add("blocked", f"{where}: `correction_method` is missing")
    elif method not in MULTIPLICITY_METHODS:
        result.add(
            "blocked",
            f"{where}: `correction_method: {method}` is not one of {sorted(MULTIPLICITY_METHODS)}",
        )
    elif method == "none_single_comparison" and planned is not None and planned != 1:
        result.add(
            "blocked",
            f"{where}: correction_method is none_single_comparison but planned_comparisons is {planned}, expected 1",
        )
    elif method != "none_single_comparison" and planned is not None and planned <= 1:
        result.add(
            "needs_revision",
            f"{where}: correction_method is {method} but planned_comparisons is {planned} -- "
            "a single comparison doesn't need multiplicity correction",
        )

    _check_basis(result, block, where)
    return result


def check_confounder_selection(block: Optional[dict], covariates_included: Optional[list]) -> CheckResult:
    """confounding_adjustment_plan.yaml -> variables.covariates.confounder_selection."""
    result = CheckResult(name="confounder_selection")
    where = "confounding_adjustment_plan.yaml: variables.covariates.confounder_selection"
    has_covariates = bool(covariates_included)

    if block is None:
        severity = "blocked" if has_covariates else "needs_revision"
        result.add(severity, f"{where} is missing entirely (covariate list has no stated selection rule)")
        return result

    method = _get(block, "method")
    if not method:
        severity = "blocked" if has_covariates else "needs_revision"
        result.add(severity, f"{where}: `method` is missing")
    elif method not in CONFOUNDER_METHODS:
        result.add("blocked", f"{where}: `method: {method}` is not one of {sorted(CONFOUNDER_METHODS)}")
    else:
        if not _get(block, "criteria"):
            result.add("needs_revision", f"{where}: `criteria` is empty -- state the reasoning in one line")
        if method == "change_in_estimate" and _get(block, "change_in_estimate_threshold_pct") is None:
            result.add(
                "blocked",
                f"{where}: method is change_in_estimate but `change_in_estimate_threshold_pct` is not set",
            )

    _check_basis(result, block, where)
    return result


def check_ordinal_estimator(block: Any) -> CheckResult:
    """sem_measurement_plan.yaml -> measurement_model.estimator."""
    result = CheckResult(name="ordinal_estimator")
    where = "sem_measurement_plan.yaml: measurement_model.estimator"

    if block is None:
        result.add("blocked", f"{where} is missing")
        return result
    if isinstance(block, str):
        result.add(
            "blocked",
            f"{where} is a bare string ({block!r}) -- must be a {{method, rationale, basis}} block, "
            "decided before fit indices exist",
        )
        return result
    if not isinstance(block, dict):
        result.add("blocked", f"{where} has an unrecognized shape ({type(block).__name__})")
        return result

    method = _get(block, "method")
    if not method:
        result.add("blocked", f"{where}: `method` is missing")
    elif method not in ESTIMATOR_METHODS:
        result.add("blocked", f"{where}: `method: {method}` is not one of {sorted(ESTIMATOR_METHODS)}")
    elif method == "ML" and not _get(block, "rationale"):
        result.add(
            "needs_revision",
            f"{where}: method is ML on what is presumably an ordinal Likert item -- "
            f"state a `rationale`, or switch to {sorted(ORDINAL_DEFAULT_ESTIMATORS)}",
        )

    _check_basis(result, block, where)
    return result
