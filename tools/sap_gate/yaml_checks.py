"""Pull the Phase 0 blocks out of the D4 / D3-SEM plan YAML files."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import yaml

from .schema import CheckResult, check_confounder_selection, check_ordinal_estimator


def load_yaml(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else None


def check_confounding_adjustment_plan(path: Path) -> tuple[Optional[CheckResult], bool]:
    """Returns (result, file_found). ``result`` is None if the file doesn't exist --
    that's a missing *artifact*, distinct from an artifact that exists but fails
    its Phase 0 check, so the caller can tell the two apart."""
    data = load_yaml(path)
    if data is None:
        return None, False

    covariates: dict[str, Any] = (
        data.get("variables", {}).get("covariates", {}) if isinstance(data.get("variables"), dict) else {}
    )
    confounder_selection = covariates.get("confounder_selection") if isinstance(covariates, dict) else None
    included = covariates.get("included") if isinstance(covariates, dict) else None

    return check_confounder_selection(confounder_selection, included), True


def check_sem_measurement_plan(path: Path) -> tuple[Optional[CheckResult], bool]:
    data = load_yaml(path)
    if data is None:
        return None, False

    measurement_model = data.get("measurement_model", {})
    estimator = measurement_model.get("estimator") if isinstance(measurement_model, dict) else None

    return check_ordinal_estimator(estimator), True
