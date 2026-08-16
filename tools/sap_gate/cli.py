"""CLI for the Phase 0 gate.

Usage:
    python -m tools.sap_gate <project_dir> [--json]

Exit code mirrors severity, so it composes in a CI step or pre-commit hook:
0 = pass, 1 = needs_revision, 2 = blocked, 3 = usage error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from .gate import run_phase0_gate

_EXIT_CODE = {"pass": 0, "needs_revision": 1, "blocked": 2}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m tools.sap_gate",
        description="Check a DR workflow project against the Phase 0 pre-registration gate.",
    )
    parser.add_argument("project_dir", type=Path, help="Path to a project, e.g. projects/crp-mortality")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of YAML")
    args = parser.parse_args(argv)

    if not args.project_dir.exists():
        print(f"error: {args.project_dir} does not exist", file=sys.stderr)
        return 3

    report = run_phase0_gate(args.project_dir)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(yaml.safe_dump(report, sort_keys=False, allow_unicode=True))

    return _EXIT_CODE.get(report["qa_status"], 3)


if __name__ == "__main__":
    raise SystemExit(main())
