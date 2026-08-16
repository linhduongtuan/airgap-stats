"""Phase 6 of the statistical-methods roadmap, item 1: "Smoke-test every
new script" -- a permanent, reusable version of the ad hoc verification
pass that was run by hand after the original R->Python translation and
after every phase since.

Discovers every `projects/*/scripts/*.py` file and runs it against its
project's own `data_synthetic/synthetic_dataset.csv`, asserting the exit
contract appropriate to *what kind* of script it is -- "exit 0" is not a
universal pass criterion here, because two of the three script kinds are
supposed to refuse to run without real data:

  - Stage D analysis scripts (desc/infer/plots/survival/psm/sem_measurement/
    sem_structural/sem_invariance): run standalone against the default
    synthetic dataset, must exit 0.
  - Stage A/B privacy-gate scripts (pattern_extract.py, synthesize_data.py):
    take the real dataset via argv; running with no args must exit 1 with
    a usage message, not crash with a traceback. That refusal *is* the
    pass condition -- these scripts must never guess at a real data path.
  - Stage B2 correlated-synthesis templates (synthesize_data_correlated.py):
    designed to be hand-edited, not argv-driven; running unedited must
    exit 0 and print instructions, not crash.
  - Anything else found is reported as `unknown_category` rather than
    silently assumed to be one of the above -- a new script type should
    make this tool ask to be updated, not misjudge it.

CLI:  .venv/bin/python -m tools.smoke_test [--project NAME] [--json]
Exit code: 0 if every script matched its expected contract, 1 otherwise.

Runtime note: the full run executes every Stage D script for real,
including bootstrap loops -- budget a few minutes total (sem_invariance.py
alone documents ~4 minutes at its default n_boot). This is not a fast
pre-commit check; run it after any change to a Stage D script or its
dependencies, not on every commit.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROJECTS_DIR = REPO_ROOT / "projects"

STAGE_D_SCRIPTS = {
    "desc.py", "infer.py", "plots.py", "survival.py", "psm.py",
    "sem_measurement.py", "sem_structural.py", "sem_invariance.py",
}
REQUIRES_REAL_DATA_ARGV = {"pattern_extract.py", "synthesize_data.py"}
EDIT_ME_TEMPLATE = {"synthesize_data_correlated.py"}

DEFAULT_TIMEOUTS = {
    "desc.py": 60, "infer.py": 180, "plots.py": 60, "survival.py": 60, "psm.py": 60,
    "sem_measurement.py": 90, "sem_structural.py": 300, "sem_invariance.py": 420,
    "pattern_extract.py": 30, "synthesize_data.py": 30, "synthesize_data_correlated.py": 30,
}
_FALLBACK_TIMEOUT = 120


def classify(script_name: str) -> str:
    if script_name in STAGE_D_SCRIPTS:
        return "stage_d"
    if script_name in REQUIRES_REAL_DATA_ARGV:
        return "requires_real_data_argv"
    if script_name in EDIT_ME_TEMPLATE:
        return "edit_me_template"
    return "unknown_category"


@dataclass
class ScriptResult:
    project: str
    script: str
    category: str
    status: str  # "pass" | "fail" | "timeout" | "unknown_category"
    returncode: int | None = None
    detail: str = ""

    def to_dict(self) -> dict:
        return {
            "project": self.project, "script": self.script, "category": self.category,
            "status": self.status, "returncode": self.returncode, "detail": self.detail,
        }


def discover_scripts(projects_dir: Path = PROJECTS_DIR, project_filter: str | None = None) -> list[tuple[str, Path]]:
    found: list[tuple[str, Path]] = []
    for project_dir in sorted(projects_dir.iterdir()):
        if not project_dir.is_dir():
            continue
        if project_filter and project_dir.name != project_filter:
            continue
        scripts_dir = project_dir / "scripts"
        if not scripts_dir.is_dir():
            continue
        for script_path in sorted(scripts_dir.glob("*.py")):
            found.append((project_dir.name, script_path))
    return found


def _run(project_dir: Path, script_path: Path, args: list[str], timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script_path), *args],
        cwd=str(project_dir),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def run_one(project: str, script_path: Path, timeout: int | None = None) -> ScriptResult:
    script_name = script_path.name
    category = classify(script_name)
    project_dir = script_path.resolve().parents[1]
    timeout = timeout if timeout is not None else DEFAULT_TIMEOUTS.get(script_name, _FALLBACK_TIMEOUT)

    try:
        if category == "stage_d":
            proc = _run(project_dir, script_path, [], timeout)
            if proc.returncode == 0:
                return ScriptResult(project, script_name, category, "pass", proc.returncode)
            return ScriptResult(project, script_name, category, "fail", proc.returncode,
                                 detail=proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "(no stderr)")

        if category == "requires_real_data_argv":
            proc = _run(project_dir, script_path, [], timeout)
            has_traceback = "Traceback (most recent call last)" in proc.stderr
            if proc.returncode == 1 and not has_traceback:
                return ScriptResult(project, script_name, category, "pass", proc.returncode,
                                     detail="refused to run without real data, as designed")
            if has_traceback:
                return ScriptResult(project, script_name, category, "fail", proc.returncode,
                                     detail="crashed with a traceback instead of a clean usage message")
            return ScriptResult(project, script_name, category, "fail", proc.returncode,
                                 detail=f"expected exit 1 (usage message), got {proc.returncode}")

        if category == "edit_me_template":
            proc = _run(project_dir, script_path, [], timeout)
            if proc.returncode == 0:
                return ScriptResult(project, script_name, category, "pass", proc.returncode)
            return ScriptResult(project, script_name, category, "fail", proc.returncode,
                                 detail=proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "(no stderr)")

        # unknown_category: still run it (no args) so the report shows what
        # happened, but never assert a contract for a script this tool
        # doesn't recognize.
        proc = _run(project_dir, script_path, [], timeout)
        return ScriptResult(project, script_name, category, "unknown_category", proc.returncode,
                             detail="not in STAGE_D_SCRIPTS / REQUIRES_REAL_DATA_ARGV / EDIT_ME_TEMPLATE -- "
                                    "add it to tools/smoke_test.py's classification so this tool can assert its contract")

    except subprocess.TimeoutExpired:
        return ScriptResult(project, script_name, category, "timeout", None, detail=f">{timeout}s")


def run_all(project_filter: str | None = None, timeout_overrides: dict[str, int] | None = None) -> list[ScriptResult]:
    timeout_overrides = timeout_overrides or {}
    results = []
    for project, script_path in discover_scripts(project_filter=project_filter):
        timeout = timeout_overrides.get(script_path.name)
        results.append(run_one(project, script_path, timeout))
    return results


def summarize(results: list[ScriptResult]) -> str:
    lines = []
    n_pass = sum(1 for r in results if r.status == "pass")
    n_other = len(results) - n_pass
    for r in results:
        marker = "PASS" if r.status == "pass" else r.status.upper()
        lines.append(f"[{marker}] {r.project}/{r.script} ({r.category})" + (f" -- {r.detail}" if r.detail else ""))
    lines.append(f"\n{n_pass} passed, {n_other} did not match their expected contract" if n_other else f"\n{n_pass} passed, all scripts matched their expected contract")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=None, help="Only smoke-test this project's scripts/ dir")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON instead of a summary")
    args = parser.parse_args(argv)

    results = run_all(project_filter=args.project)

    if args.json:
        print(json.dumps([r.to_dict() for r in results], indent=2))
    else:
        print(summarize(results))

    return 0 if all(r.status == "pass" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
