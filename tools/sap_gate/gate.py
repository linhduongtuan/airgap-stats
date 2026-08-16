"""Orchestrates the four Phase 0 checks for one project and produces a
report in the same shape ``dr-output-qa-gate`` already uses, so it drops
straight into that skill's workflow instead of inventing a second format.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .sap_parser import parse_sap
from .schema import CheckResult, check_missing_data_plan, check_multiplicity_plan
from .yaml_checks import check_confounding_adjustment_plan, check_sem_measurement_plan

_STATUS_RANK = {"pass": 0, "needs_revision": 1, "blocked": 2}


def _read_track(project_dir: Path) -> str | None:
    analysis_plan = project_dir / "plans" / "analysis_plan.yaml"
    if not analysis_plan.exists():
        return None
    try:
        import yaml

        data = yaml.safe_load(analysis_plan.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    track = data.get("workflow_track", {})
    return track.get("value") if isinstance(track, dict) else None


def run_phase0_gate(project_dir: str | Path) -> dict[str, Any]:
    project_dir = Path(project_dir)
    project_name = project_dir.name

    required_artifacts = ["plans/sap.md"]
    missing_artifacts: list[str] = []
    not_yet_applicable: list[str] = []
    issues: list[str] = []
    checks: list[CheckResult] = []

    track = _read_track(project_dir)

    # --- plans/sap.md: missing_data (H) + multiplicity (I) -----------------
    sap_path = project_dir / "plans" / "sap.md"
    if sap_path.exists():
        parsed = parse_sap(sap_path.read_text(encoding="utf-8"))
        md_result = check_missing_data_plan(parsed.missing_data)
        mult_result = check_multiplicity_plan(parsed.multiplicity)
        checks.extend([md_result, mult_result])
    else:
        missing_artifacts.append("plans/sap.md")
        issues.append(
            "plans/sap.md does not exist -- Stage D1b (dr-01b-analysis-sap) must run and be "
            "approved before Phase 0 can be checked at all."
        )

    # --- D4 medical: confounder_selection -----------------------------------
    confounding_path = project_dir / "plans" / "confounding_adjustment_plan.yaml"
    if track in (None, "medical") and confounding_path.exists():
        required_artifacts.append("plans/confounding_adjustment_plan.yaml")
        result, _found = check_confounding_adjustment_plan(confounding_path)
        if result is not None:
            checks.append(result)
    elif track == "medical":
        not_yet_applicable.append(
            "plans/confounding_adjustment_plan.yaml (Stage D4 not reached yet -- fine if the "
            "project hasn't gotten there; check again once it has)"
        )

    # --- D3-SEM: ordinal estimator -----------------------------------------
    sem_measurement_path = project_dir / "plans" / "sem_measurement_plan.yaml"
    if track in (None, "sem") and sem_measurement_path.exists():
        required_artifacts.append("plans/sem_measurement_plan.yaml")
        result, _found = check_sem_measurement_plan(sem_measurement_path)
        if result is not None:
            checks.append(result)
    elif track == "sem":
        not_yet_applicable.append(
            "plans/sem_measurement_plan.yaml (Stage D3-SEM not reached yet -- fine if the "
            "project hasn't gotten there; check again once it has)"
        )

    for c in checks:
        issues.extend(f"[{c.name}] {msg}" for msg in c.issues)

    if missing_artifacts:
        overall = "blocked"
    elif checks:
        overall = max((c.status for c in checks), key=lambda s: _STATUS_RANK[s])
    else:
        # No sap.md gap and nothing else applicable yet (e.g. project has no
        # plans/ at all -- Stage D1 hasn't even run).
        overall = "blocked"
        if not missing_artifacts:
            missing_artifacts.append("plans/analysis_plan.yaml")
            issues.append("No plans/ artifacts found at all -- Stage D1 (dr-01-understand-dataset) hasn't run.")

    if overall == "pass":
        next_allowed_step = "Stage D2 (dr-02-descriptive-analysis) may proceed."
        user_action_required = ""
    elif overall == "needs_revision":
        next_allowed_step = "Fix the flagged Phase 0 items in plans/sap.md (or the D4/D3-SEM plan), then re-run this gate."
        user_action_required = "Review the `issues` list and confirm or correct each flagged decision."
    else:
        next_allowed_step = "Blocked -- do not generate further analysis scripts until missing artifacts exist."
        user_action_required = "Produce the artifacts under `missing_artifacts`, or complete the SAP sections they depend on."

    return {
        "qa_status": overall,
        "project": project_name,
        "checked_stage": "Phase 0 pre-registration (roadmap items: missing data, multiplicity, "
        "confounder selection, ordinal estimator)",
        "required_artifacts": required_artifacts,
        "missing_artifacts": missing_artifacts,
        "not_yet_applicable": not_yet_applicable,
        "checks": [
            {"name": c.name, "status": c.status, "issues": c.issues} for c in checks
        ],
        "issues": issues,
        "next_allowed_step": next_allowed_step,
        "user_action_required": user_action_required,
    }
