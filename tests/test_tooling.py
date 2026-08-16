"""Self-contained smoke tests for tools.smoke_test, tools.parity_check, and
tools.skills_sync_check -- no pytest required.

Run with:  .venv/bin/python tests/test_tooling.py

Uses small fixture scripts/directories built in a temp dir rather than
re-running the real project scripts a second time (that already happens
when someone runs `python -m tools.smoke_test` directly) -- these tests
check the classification and pass/fail *logic* itself, including the
mismatch cases (a script that gets the wrong exit code for its category).
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.parity_check import check_project
from tools.skills_sync_check import check_mirror, fix_mirror
from tools.smoke_test import classify, discover_scripts, run_one

_passed = 0
_failed: list[str] = []


def check(name: str, condition: bool) -> None:
    global _passed
    if condition:
        _passed += 1
    else:
        _failed.append(name)
        print(f"FAIL: {name}")


_tmp = Path(tempfile.mkdtemp(prefix="dr_tooling_test_"))

# ---------------------------------------------------------------------------
# tools.smoke_test.classify
# ---------------------------------------------------------------------------

check("classify: desc.py is stage_d", classify("desc.py") == "stage_d")
check("classify: sem_invariance.py is stage_d", classify("sem_invariance.py") == "stage_d")
check("classify: pattern_extract.py requires real data", classify("pattern_extract.py") == "requires_real_data_argv")
check("classify: synthesize_data.py requires real data", classify("synthesize_data.py") == "requires_real_data_argv")
check("classify: synthesize_data_correlated.py is the edit-me template", classify("synthesize_data_correlated.py") == "edit_me_template")
check("classify: an unrecognized script name is unknown_category", classify("some_new_script.py") == "unknown_category")

# ---------------------------------------------------------------------------
# tools.smoke_test.discover_scripts
# ---------------------------------------------------------------------------

proj_a = _tmp / "discover" / "proj_a" / "scripts"
proj_a.mkdir(parents=True)
(proj_a / "desc.py").write_text("print('hi')\n")
(proj_a / "desc.R").write_text("cat('hi')\n")  # not .py -- must not be discovered
(proj_a / "__pycache__").mkdir()
(proj_a / "__pycache__" / "desc.cpython-312.pyc").write_bytes(b"\x00")
proj_b_no_scripts = _tmp / "discover" / "proj_b_no_scripts_dir"
proj_b_no_scripts.mkdir(parents=True)  # a project dir with no scripts/ subfolder at all

discovered = discover_scripts(projects_dir=_tmp / "discover")
discovered_names = [(proj, p.name) for proj, p in discovered]
check("discover_scripts: finds the .py script", ("proj_a", "desc.py") in discovered_names)
check("discover_scripts: does not pick up the .R sibling", ("proj_a", "desc.R") not in discovered_names)
check("discover_scripts: does not descend into __pycache__", not any("__pycache__" in str(p) for _, p in discovered))
check("discover_scripts: a project with no scripts/ dir contributes nothing", not any(proj == "proj_b_no_scripts_dir" for proj, _ in discovered_names))

proj_filtered = discover_scripts(projects_dir=_tmp / "discover", project_filter="proj_a")
check("discover_scripts: --project filter narrows to just that project", all(proj == "proj_a" for proj, _ in proj_filtered))

# ---------------------------------------------------------------------------
# tools.smoke_test.run_one -- contract matching, including mismatches
# ---------------------------------------------------------------------------

run_proj = _tmp / "run" / "run_proj" / "scripts"
run_proj.mkdir(parents=True)

(run_proj / "desc.py").write_text("print('ok')\n")  # stage_d, exits 0 -- should PASS
(run_proj / "infer.py").write_text("import sys; sys.exit(1)\n")  # stage_d, exits 1 -- should FAIL (wrong contract)
(run_proj / "pattern_extract.py").write_text(
    "import sys\nif len(sys.argv) < 2:\n    print('Usage: ...')\n    sys.exit(1)\n"
)  # requires_real_data_argv, exits 1 with usage msg on no args -- should PASS
(run_proj / "synthesize_data.py").write_text("raise RuntimeError('boom')\n")  # exits 1 but via traceback -- should FAIL
(run_proj / "synthesize_data_correlated.py").write_text("print('edit me')\n")  # edit_me_template, exits 0 -- should PASS
(run_proj / "some_new_script.py").write_text("print('mystery')\n")  # unknown_category -- reported, never asserted

r_desc = run_one("run_proj", run_proj / "desc.py")
check("run_one: a stage_d script that exits 0 -> pass", r_desc.status == "pass")

r_infer = run_one("run_proj", run_proj / "infer.py")
check("run_one: a stage_d script that exits 1 -> fail (wrong contract, not silently accepted)", r_infer.status == "fail")

r_pattern = run_one("run_proj", run_proj / "pattern_extract.py")
check("run_one: requires_real_data_argv script refusing cleanly (exit 1, no traceback) -> pass", r_pattern.status == "pass")

r_synth = run_one("run_proj", run_proj / "synthesize_data.py")
check("run_one: requires_real_data_argv script that crashes with a traceback -> fail, not pass-by-coincidence",
      r_synth.status == "fail" and "traceback" in r_synth.detail.lower())

r_corr = run_one("run_proj", run_proj / "synthesize_data_correlated.py")
check("run_one: edit_me_template script that exits 0 -> pass", r_corr.status == "pass")

r_unknown = run_one("run_proj", run_proj / "some_new_script.py")
check("run_one: an unrecognized script name is reported, never silently marked pass/fail",
      r_unknown.status == "unknown_category")

# A stage_d script that hangs past its timeout -> timeout, not a false pass.
(run_proj / "plots.py").write_text("import time; time.sleep(5)\n")
r_timeout = run_one("run_proj", run_proj / "plots.py", timeout=1)
check("run_one: a script that exceeds its timeout is reported as timeout, not pass", r_timeout.status == "timeout")

# ---------------------------------------------------------------------------
# tools.parity_check.check_project
# ---------------------------------------------------------------------------

parity_proj = _tmp / "parity" / "proj" / "scripts"
parity_proj.mkdir(parents=True)
for name in ["desc.py", "desc.R", "infer.py", "infer.R", "psm.py", "sem_invariance.py"]:
    (parity_proj / name).write_text("# fixture\n")

parity = check_project(parity_proj)
check("check_project: matched stems include desc and infer", set(parity.matched) == {"desc", "infer"})
check("check_project: py_only includes psm and sem_invariance", set(parity.py_only) == {"psm", "sem_invariance"})
check("check_project: r_only is empty for this fixture", parity.r_only == [])
check("check_project: in_sync is False when any asymmetry exists", parity.in_sync is False)

fully_synced_proj = _tmp / "parity" / "synced_proj" / "scripts"
fully_synced_proj.mkdir(parents=True)
for name in ["desc.py", "desc.R"]:
    (fully_synced_proj / name).write_text("# fixture\n")
synced = check_project(fully_synced_proj)
check("check_project: in_sync is True when every stem has both languages", synced.in_sync is True)

empty_proj = _tmp / "parity" / "empty_proj" / "scripts"
empty_proj.mkdir(parents=True)
empty = check_project(empty_proj)
check("check_project: an empty scripts/ dir is trivially in_sync (0/0)", empty.in_sync is True)

# ---------------------------------------------------------------------------
# tools.skills_sync_check.check_mirror / fix_mirror
# ---------------------------------------------------------------------------

sk_canonical = _tmp / "skills_sync" / "skills"
(sk_canonical / "dr-00-privacy-gate").mkdir(parents=True)
(sk_canonical / "dr-00-privacy-gate" / "SKILL.md").write_text("canonical v2\n")
(sk_canonical / "dr-01-understand-dataset").mkdir(parents=True)
(sk_canonical / "dr-01-understand-dataset" / "SKILL.md").write_text("unchanged\n")

sk_mirror = _tmp / "skills_sync" / "mirror"
(sk_mirror / "dr-00-privacy-gate").mkdir(parents=True)
(sk_mirror / "dr-00-privacy-gate" / "SKILL.md").write_text("stale v1\n")  # changed
(sk_mirror / "dr-01-understand-dataset").mkdir(parents=True)
(sk_mirror / "dr-01-understand-dataset" / "SKILL.md").write_text("unchanged\n")  # matches
(sk_mirror / "dr-02-descriptive-analysis").mkdir(parents=True)
(sk_mirror / "dr-02-descriptive-analysis" / "SKILL.md").write_text("leftover\n")  # extra

drift = check_mirror(sk_mirror, canonical=sk_canonical)
check("check_mirror: flags the changed file", drift.changed == ["dr-00-privacy-gate/SKILL.md"])
check("check_mirror: flags the extra file", drift.extra == ["dr-02-descriptive-analysis/SKILL.md"])
check("check_mirror: matching file is not flagged as changed or missing",
      "dr-01-understand-dataset/SKILL.md" not in drift.changed
      and "dr-01-understand-dataset/SKILL.md" not in drift.missing)
check("check_mirror: in_sync is False when drift exists", drift.in_sync is False)

sk_missing_mirror = _tmp / "skills_sync" / "does_not_exist_yet"
missing = check_mirror(sk_missing_mirror, canonical=sk_canonical)
check("check_mirror: a mirror dir that doesn't exist reports every canonical file as missing",
      set(missing.missing) == {"dr-00-privacy-gate/SKILL.md", "dr-01-understand-dataset/SKILL.md"})

fix_mirror(sk_mirror, canonical=sk_canonical)
fixed = check_mirror(sk_mirror, canonical=sk_canonical)
check("fix_mirror: re-syncing makes the mirror in_sync", fixed.in_sync is True)
check("fix_mirror: the stale content was overwritten with canonical's",
      (sk_mirror / "dr-00-privacy-gate" / "SKILL.md").read_text() == "canonical v2\n")
check("fix_mirror: the leftover extra file was removed",
      not (sk_mirror / "dr-02-descriptive-analysis").exists())

sk_synced_canonical = _tmp / "skills_sync" / "synced_only" / "skills"
sk_synced_mirror = _tmp / "skills_sync" / "synced_only" / "mirror"
(sk_synced_canonical / "dr-00-privacy-gate").mkdir(parents=True)
(sk_synced_canonical / "dr-00-privacy-gate" / "SKILL.md").write_text("same\n")
(sk_synced_mirror / "dr-00-privacy-gate").mkdir(parents=True)
(sk_synced_mirror / "dr-00-privacy-gate" / "SKILL.md").write_text("same\n")
already_synced = check_mirror(sk_synced_mirror, canonical=sk_synced_canonical)
check("check_mirror: two identical trees report in_sync True with no findings",
      already_synced.in_sync is True
      and not already_synced.missing and not already_synced.extra and not already_synced.changed)

# ---------------------------------------------------------------------------
shutil.rmtree(_tmp, ignore_errors=True)

print(f"\n{_passed} passed, {len(_failed)} failed")
if _failed:
    print("Failed checks:")
    for name in _failed:
        print(f"  - {name}")
    sys.exit(1)
print("ALL TESTS PASSED")
