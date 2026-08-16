"""Self-contained smoke tests for tools.sap_gate -- no pytest required.

Run with:  .venv/bin/python tests/test_sap_gate.py

Each test builds an isolated fixture project directory under a tempdir (never
touches the real projects/*), runs a check, and asserts the result. Exits 0
and prints "ALL TESTS PASSED" only if every assertion holds.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.sap_gate.gate import run_phase0_gate
from tools.sap_gate.sap_parser import parse_kv_block, parse_sap
from tools.sap_gate.schema import (
    check_confounder_selection,
    check_missing_data_plan,
    check_multiplicity_plan,
    check_ordinal_estimator,
)

_passed = 0
_failed: list[str] = []


def check(name: str, condition: bool) -> None:
    global _passed
    if condition:
        _passed += 1
    else:
        _failed.append(name)
        print(f"FAIL: {name}")


# ---------------------------------------------------------------------------
# schema.py: missing data
# ---------------------------------------------------------------------------

check(
    "missing_data: complete block passes",
    check_missing_data_plan(
        {"strategy": "complete_case", "variables_affected": "none", "basis": "confirmed"}
    ).status
    == "pass",
)

check(
    "missing_data: absent block is blocked",
    check_missing_data_plan(None).status == "blocked",
)

check(
    "missing_data: bad strategy enum is blocked",
    check_missing_data_plan({"strategy": "drop_everything", "basis": "confirmed"}).status == "blocked",
)

check(
    "missing_data: MI without imputation_model is needs_revision",
    check_missing_data_plan(
        {"strategy": "multiple_imputation", "variables_affected": "age", "basis": "confirmed"}
    ).status
    == "needs_revision",
)

# ---------------------------------------------------------------------------
# schema.py: multiplicity
# ---------------------------------------------------------------------------

check(
    "multiplicity: single comparison + none_single_comparison passes",
    check_multiplicity_plan(
        {"planned_comparisons": "1", "correction_method": "none_single_comparison", "basis": "confirmed"}
    ).status
    == "pass",
)

check(
    "multiplicity: 3 comparisons + none_single_comparison is blocked (contradiction)",
    check_multiplicity_plan(
        {"planned_comparisons": "3", "correction_method": "none_single_comparison", "basis": "confirmed"}
    ).status
    == "blocked",
)

check(
    "multiplicity: 3 comparisons + benjamini_hochberg passes",
    check_multiplicity_plan(
        {"planned_comparisons": "3", "correction_method": "benjamini_hochberg", "basis": "confirmed"}
    ).status
    == "pass",
)

check(
    "multiplicity: non-integer planned_comparisons is blocked",
    check_multiplicity_plan(
        {"planned_comparisons": "many", "correction_method": "bonferroni", "basis": "confirmed"}
    ).status
    == "blocked",
)

# ---------------------------------------------------------------------------
# schema.py: confounder selection
# ---------------------------------------------------------------------------

check(
    "confounder_selection: dag method with criteria passes",
    check_confounder_selection(
        {"method": "dag", "criteria": "from causal diagram", "basis": "confirmed"}, ["age", "sex"]
    ).status
    == "pass",
)

check(
    "confounder_selection: missing block with covariates present is blocked",
    check_confounder_selection(None, ["age", "sex"]).status == "blocked",
)

check(
    "confounder_selection: missing block with no covariates is only needs_revision",
    check_confounder_selection(None, []).status == "needs_revision",
)

check(
    "confounder_selection: change_in_estimate without threshold is blocked",
    check_confounder_selection(
        {"method": "change_in_estimate", "criteria": "10% rule", "basis": "confirmed"}, ["age"]
    ).status
    == "blocked",
)

check(
    "confounder_selection: change_in_estimate with threshold passes",
    check_confounder_selection(
        {
            "method": "change_in_estimate",
            "criteria": "10% rule",
            "change_in_estimate_threshold_pct": 10,
            "basis": "confirmed",
        },
        ["age"],
    ).status
    == "pass",
)

# ---------------------------------------------------------------------------
# schema.py: ordinal estimator
# ---------------------------------------------------------------------------

check(
    "ordinal_estimator: bare string is blocked",
    check_ordinal_estimator("ML (default)").status == "blocked",
)

check(
    "ordinal_estimator: WLSMV with basis confirmed passes",
    check_ordinal_estimator({"method": "WLSMV", "rationale": "ordinal items", "basis": "confirmed"}).status
    == "pass",
)

check(
    "ordinal_estimator: ML without rationale is needs_revision",
    check_ordinal_estimator({"method": "ML", "basis": "confirmed"}).status == "needs_revision",
)

check(
    "ordinal_estimator: ML with rationale and confirmed basis passes",
    check_ordinal_estimator(
        {"method": "ML", "rationale": ">=7-point scale, effectively continuous", "basis": "confirmed"}
    ).status
    == "pass",
)

check(
    "ordinal_estimator: unknown method is blocked",
    check_ordinal_estimator({"method": "GLS", "basis": "confirmed"}).status == "blocked",
)

# ---------------------------------------------------------------------------
# sap_parser.py
# ---------------------------------------------------------------------------

_SAMPLE_SAP = """\
# Statistical Analysis Plan

## A. Research question

Does X predict Y?

## H. Missing data

```text
strategy:            complete_case
variables_affected:  none
basis:                confirmed
```

## I. Multiplicity

```text
planned_comparisons:  1
correction_method:    none_single_comparison
basis:                confirmed
```
"""

_parsed = parse_sap(_SAMPLE_SAP)
check("sap_parser: finds 3 sections", len(_parsed.sections) == 3)
check(
    "sap_parser: missing_data block parsed",
    _parsed.missing_data == {"strategy": "complete_case", "variables_affected": "none", "basis": "confirmed"},
)
check(
    "sap_parser: multiplicity block parsed",
    _parsed.multiplicity
    == {"planned_comparisons": "1", "correction_method": "none_single_comparison", "basis": "confirmed"},
)

_parsed_missing = parse_sap("## A. Research question\n\nNo H or I section here.\n")
check("sap_parser: missing section -> None, not KeyError", _parsed_missing.missing_data is None)

check("sap_parser: parse_kv_block returns None with no fence", parse_kv_block("just prose, no fence") is None)


# ---------------------------------------------------------------------------
# gate.py: end-to-end against fixture project directories
# ---------------------------------------------------------------------------

def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


_tmp = Path(tempfile.mkdtemp(prefix="sap_gate_test_"))
try:
    # Case 1: no plans/ at all -> blocked, single missing artifact.
    proj_empty = _tmp / "empty-project"
    proj_empty.mkdir()
    report = run_phase0_gate(proj_empty)
    check("gate: empty project is blocked", report["qa_status"] == "blocked")
    check("gate: empty project flags sap.md missing", "plans/sap.md" in report["missing_artifacts"])

    # Case 2: medical track, sap.md present and valid, D4 plan not reached yet
    # -> pass overall, with confounding_adjustment_plan.yaml reported as
    # not_yet_applicable rather than penalized.
    proj_partial = _tmp / "partial-medical"
    _write(
        proj_partial / "plans" / "analysis_plan.yaml",
        'workflow_track:\n  value: "medical"\n',
    )
    _write(proj_partial / "plans" / "sap.md", _SAMPLE_SAP)
    report = run_phase0_gate(proj_partial)
    check("gate: partial medical project passes on what exists", report["qa_status"] == "pass")
    check(
        "gate: D4 plan correctly marked not_yet_applicable, not missing",
        any("confounding_adjustment_plan.yaml" in s for s in report["not_yet_applicable"])
        and "plans/confounding_adjustment_plan.yaml" not in report["missing_artifacts"],
    )

    # Case 3: medical track, sap.md present, D4 plan present but missing the
    # confounder_selection block entirely -> blocked (real gap, real covariates).
    proj_bad_d4 = _tmp / "bad-d4"
    _write(proj_bad_d4 / "plans" / "analysis_plan.yaml", 'workflow_track:\n  value: "medical"\n')
    _write(proj_bad_d4 / "plans" / "sap.md", _SAMPLE_SAP)
    _write(
        proj_bad_d4 / "plans" / "confounding_adjustment_plan.yaml",
        "variables:\n  covariates:\n    included: ['age', 'sex']\n",
    )
    report = run_phase0_gate(proj_bad_d4)
    check("gate: D4 plan missing confounder_selection is blocked", report["qa_status"] == "blocked")

    # Case 4: SEM track, sap.md present, measurement plan present with a bare
    # string estimator (the pre-Phase-0 shape) -> blocked.
    proj_bad_sem = _tmp / "bad-sem"
    _write(proj_bad_sem / "plans" / "analysis_plan.yaml", 'workflow_track:\n  value: "sem"\n')
    _write(proj_bad_sem / "plans" / "sap.md", _SAMPLE_SAP)
    _write(
        proj_bad_sem / "plans" / "sem_measurement_plan.yaml",
        'measurement_model:\n  estimator: "ML (default), ordered option documented in notes"\n',
    )
    report = run_phase0_gate(proj_bad_sem)
    check("gate: SEM plan with bare-string estimator is blocked", report["qa_status"] == "blocked")

    # Case 5: fully valid SEM project -> pass.
    proj_good_sem = _tmp / "good-sem"
    _write(proj_good_sem / "plans" / "analysis_plan.yaml", 'workflow_track:\n  value: "sem"\n')
    _write(proj_good_sem / "plans" / "sap.md", _SAMPLE_SAP)
    _write(
        proj_good_sem / "plans" / "sem_measurement_plan.yaml",
        "measurement_model:\n"
        "  estimator:\n"
        '    method: "WLSMV"\n'
        '    rationale: "ordinal Likert items"\n'
        '    basis: "confirmed"\n',
    )
    report = run_phase0_gate(proj_good_sem)
    check("gate: fully valid SEM project passes", report["qa_status"] == "pass")

finally:
    shutil.rmtree(_tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
print(f"\n{_passed} passed, {len(_failed)} failed")
if _failed:
    print("Failed checks:")
    for name in _failed:
        print(f"  - {name}")
    sys.exit(1)
print("ALL TESTS PASSED")
