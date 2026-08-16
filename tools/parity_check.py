"""Phase 6 of the statistical-methods roadmap, item 2: "R/Python parity
check" -- flags a script that exists in `.R` but not `.py` (or vice versa)
in any project's `scripts/` folder, so the two-language mirror can't drift
silently.

This tool only *detects* drift; it does not fix it by generating the
missing file in either language. A flagged gap is not automatically a bug
-- several exist by a deliberate, explicitly-scoped choice (e.g.
`sem_invariance.py` was built Python-only per Phase 3's own decision) and
should stay that way until someone chooses to port it, not get silently
papered over by a tool that invents R or Python code on its own.

CLI:  .venv/bin/python -m tools.parity_check [--project NAME] [--json]
Exit code: 0 if every project's scripts/ dir has matching .R/.py stems,
1 if any asymmetry is found (informational for a human to triage, not
proof of a bug -- see above).
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROJECTS_DIR = REPO_ROOT / "projects"


@dataclass
class ProjectParity:
    project: str
    r_only: list[str] = field(default_factory=list)
    py_only: list[str] = field(default_factory=list)
    matched: list[str] = field(default_factory=list)

    @property
    def in_sync(self) -> bool:
        return not self.r_only and not self.py_only

    def to_dict(self) -> dict:
        return {
            "project": self.project, "in_sync": self.in_sync,
            "r_only": self.r_only, "py_only": self.py_only, "matched": self.matched,
        }


def check_project(scripts_dir: Path) -> ProjectParity:
    project = scripts_dir.resolve().parents[0].name
    r_stems = {p.stem for p in scripts_dir.glob("*.R")}
    py_stems = {p.stem for p in scripts_dir.glob("*.py")}
    return ProjectParity(
        project=project,
        r_only=sorted(r_stems - py_stems),
        py_only=sorted(py_stems - r_stems),
        matched=sorted(r_stems & py_stems),
    )


def check_all(project_filter: str | None = None, projects_dir: Path = PROJECTS_DIR) -> list[ProjectParity]:
    results = []
    for project_dir in sorted(projects_dir.iterdir()):
        if not project_dir.is_dir():
            continue
        if project_filter and project_dir.name != project_filter:
            continue
        scripts_dir = project_dir / "scripts"
        if not scripts_dir.is_dir():
            continue
        results.append(check_project(scripts_dir))
    return results


def summarize(results: list[ProjectParity]) -> str:
    lines = []
    any_drift = False
    for r in results:
        if r.in_sync:
            lines.append(f"[IN SYNC] {r.project} ({len(r.matched)} script(s) with both .R and .py)")
            continue
        any_drift = True
        lines.append(f"[DRIFT]   {r.project}")
        for stem in r.py_only:
            lines.append(f"          {stem}: .py only, no {stem}.R")
        for stem in r.r_only:
            lines.append(f"          {stem}: .R only, no {stem}.py")
    lines.append("")
    lines.append("No drift found." if not any_drift else
                  "Drift found -- review each entry; some are deliberate scoping choices, not bugs "
                  "(check the relevant phase's notes before porting).")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=None, help="Only check this project")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON instead of a summary")
    args = parser.parse_args(argv)

    results = check_all(project_filter=args.project)

    if args.json:
        print(json.dumps([r.to_dict() for r in results], indent=2))
    else:
        print(summarize(results))

    return 0 if all(r.in_sync for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
