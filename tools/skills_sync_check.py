"""Skill-mirror sync check -- flags any file under `skills/` (canonical)
that doesn't byte-match its copy in `.claude/skills/`, `.opencode/skill/`,
or `.agents/skills/` (the per-agent mirrors documented in CLAUDE.md /
AGENTS.md: "apply any skill change to all of them").

Unlike tools/parity_check.py's R/Python asymmetry (where some gaps are a
deliberate, scoped choice), there is no legitimate reason for a mirror to
differ from `skills/` -- every mirror should be an exact copy at all
times. So `--fix` here is safe to run unconditionally: it just re-syncs
the mirrors from canonical, it never invents content.

CLI:  .venv/bin/python -m tools.skills_sync_check [--json] [--fix]
Exit code: 0 if every mirror already matched `skills/` byte-for-byte.
1 if drift was found -- whether or not --fix repaired it -- following the
standard auto-fixer convention (like `black`/`isort` under pre-commit): a
run that had to change files still fails so the human re-stages and
commits again, instead of silently committing a fix next to unstaged
mirror changes.
"""

from __future__ import annotations

import argparse
import filecmp
import json
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CANONICAL = REPO_ROOT / "skills"
MIRRORS = [
    REPO_ROOT / ".claude" / "skills",
    REPO_ROOT / ".opencode" / "skill",
    REPO_ROOT / ".agents" / "skills",
]
IGNORE = {".DS_Store", "__pycache__"}


@dataclass
class MirrorDrift:
    mirror: str
    missing: list[str] = field(default_factory=list)   # in canonical, not in mirror
    extra: list[str] = field(default_factory=list)      # in mirror, not in canonical
    changed: list[str] = field(default_factory=list)    # present both sides, differs

    @property
    def in_sync(self) -> bool:
        return not (self.missing or self.extra or self.changed)

    def to_dict(self) -> dict:
        return {
            "mirror": self.mirror, "in_sync": self.in_sync,
            "missing": self.missing, "extra": self.extra, "changed": self.changed,
        }


def _relative_files(root: Path) -> set[str]:
    return {
        str(p.relative_to(root))
        for p in root.rglob("*")
        if p.is_file() and p.name not in IGNORE
    }


def check_mirror(mirror: Path, canonical: Path = CANONICAL) -> MirrorDrift:
    canonical_files = _relative_files(canonical)
    mirror_files = _relative_files(mirror) if mirror.is_dir() else set()

    missing = sorted(canonical_files - mirror_files)
    extra = sorted(mirror_files - canonical_files)
    changed = sorted(
        rel for rel in canonical_files & mirror_files
        if not filecmp.cmp(canonical / rel, mirror / rel, shallow=False)
    )
    try:
        label = str(mirror.relative_to(REPO_ROOT))
    except ValueError:
        label = str(mirror)  # outside REPO_ROOT, e.g. a test fixture
    return MirrorDrift(mirror=label, missing=missing, extra=extra, changed=changed)


def fix_mirror(mirror: Path, canonical: Path = CANONICAL) -> None:
    """Make `mirror` an exact copy of `canonical`, deleting anything extra."""
    if mirror.is_dir():
        shutil.rmtree(mirror)
    shutil.copytree(canonical, mirror, ignore=shutil.ignore_patterns(*IGNORE))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument(
        "--fix", action="store_true",
        help="re-sync every mirror from skills/ instead of just reporting drift",
    )
    args = parser.parse_args()

    before = [check_mirror(mirror) for mirror in MIRRORS]
    had_drift = not all(r.in_sync for r in before)

    if args.fix and had_drift:
        for mirror in MIRRORS:
            fix_mirror(mirror)

    results = [check_mirror(mirror) for mirror in MIRRORS] if args.fix else before

    if args.json:
        print(json.dumps([r.to_dict() for r in results], indent=2))
    else:
        for before_r, after_r in zip(before, results):
            if before_r.in_sync:
                print(f"OK    {after_r.mirror} matches skills/")
                continue
            label = "FIXED" if args.fix else "DRIFT"
            print(f"{label} {before_r.mirror}")
            for rel in before_r.changed:
                print(f"       changed: {rel}")
            for rel in before_r.missing:
                print(f"       missing: {rel}")
            for rel in before_r.extra:
                print(f"       extra:   {rel}")
        if not had_drift:
            print("All skill mirrors are in sync with skills/.")
        elif args.fix:
            print("\nMirrors were re-synced from skills/ -- stage the changes and commit again.")
        else:
            print(
                "\nMirrors are stale. Run "
                "`.venv/bin/python -m tools.skills_sync_check --fix` to re-sync."
            )

    return 1 if had_drift else 0


if __name__ == "__main__":
    sys.exit(main())
