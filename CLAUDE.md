# AirGap Stats v2 — Agent Instructions

You are working inside AirGap Stats: a skills-based toolkit for AI-assisted research data analysis where **the real dataset never reaches the AI**. The user is typically a Vietnamese researcher or student; reply in Vietnamese unless they use another language. Skill files are in English.

The name comes from "air-gapped": the real dataset is physically cut off from the AI at every stage, the same way a secure system is air-gapped from a network. The `dr-*` skill folder names (`dr-00-privacy-gate`, `dr-workflow-orchestrator`, etc.) and `dr_workflow_state.yaml` are unchanged — those are functional identifiers, not the product name, and renaming them is a separate, unstarted piece of work with real breakage risk (skill discovery, mirror sync, cross-references throughout every skill doc and `INSTALL.md`'s literal invocation prompts). Don't rename them opportunistically while touching nearby files.

## Golden Rules (non-negotiable)

1. **The real dataset lives OUTSIDE this repo and stays there.** Never read it, never ask for its path, folder, or filename, and never tell the user to copy it into the repo. Scripts reach it only through `file.choose()` inside the user's RStudio session. If you notice real data inside the repo (e.g. a user-created `data_real/` folder), warn the user to move it out — and never read it, not with Read, not with shell commands, not "just the header".
2. **Never request real data, real summary statistics, or real row counts** from the user. If they try to paste raw data, stop them and point to the privacy gate. If pasted output contains a real file path, do not repeat it in any artifact.
2b. **Never open or accept a figure made from real data.** A boxplot or scatter is row-level data rendered as pixels — one outlier dot is one identifiable participant. Aggregate text (tables, estimates, CIs, fit indices) may be pasted; images from real data may not. Scripts must write real-run figures to `file.path(dirname(input_csv), "dr_figures")`, outside the repo. Figures under `outputs_synthetic/figures/` are synthetic and safe to open.
3. **All outputs of a research question go only inside its own `projects/<name>/` folder.** One research question = one project folder.
4. **Generated R code is base R only.** Two exceptions, both "recommended"-tier packages that ship with every R installation and never need `install.packages()` in practice: `lavaan` in the SEM track, and `survival` for time-to-event analysis (`scripts/survival.R` — `coxph()`/`survfit()` aren't in base `stats`). Anything else implementable in base R with a bit of work stays in base R even when a package exists for it (e.g. Firth's penalized logistic regression is hand-implemented in `scripts/infer.R`'s Section 4 rather than depending on `logistf`, cross-validated against it during development instead). Never emit `install.packages()` inside scripts; mention installs as comments/notes.
5. **Final results use only user-provided real-run output.** Numbers computed on synthetic data are never findings — they only prove code runs.

## How To Work

Start every task through the skills in `skills/` (mirrored in `.claude/skills/`, `.opencode/skill/`, `.agents/skills/`). If your platform did not auto-load them, open `skills/<name>/SKILL.md` and follow it as instructions.

- Entry point and routing: `dr-workflow-orchestrator` (project creation, state, what's next).
- Stages A–C (pattern extraction, review gate, synthetic data): `dr-00-privacy-gate`.
- Stage D1: `dr-01-understand-dataset` (analysis plan + track decision).
- Stage D1b: `dr-01b-analysis-sap` (SAP + mode choice). **Required in both modes.** The user approves variable roles, Table 1 stratification, and plot variables once, then picks `all_steps` (generate every script in one pass) or `step_by_step` (one script at a time, user runs each locally on synthetic before the next). Both modes produce identical, separate script files.
- Stage D2: `dr-02-descriptive-analysis` (desc.R).
- Stage D2b (optional, both tracks): `dr-02b-visual-exploration` (plots.R — correlation heatmap + boxplot series). Never blocks progress to D3.
- Medical track D3/D4: `dr-03-inferential-analysis`, `dr-04-confounding-adjustment` (infer.R).
- SEM track D3/D4: `dr-sem-01-measurement-model`, `dr-sem-02-structural-model`.
- Stage E: `dr-05-present-results` (results_real/).
- Before advancing any stage: `dr-output-qa-gate`.

State lives in `projects/<name>/dr_workflow_state.yaml`. Read it when resuming; update it after every completed action. Always tell the user: current stage, QA status, next step, and what you need from them.

## Verification Duty

**The deliverable of every stage is a runnable script.** The user takes the code and runs it on their own machine; you are not the runtime. Most agents running this pack will not have R installed, and no stage may stall because of that.

Verification on the synthetic dataset is mandatory before the user moves a script to real data — but *who* runs it is flexible:

- R available to you: run `Rscript <script>` from the project folder, fix errors, rerun until it exits cleanly.
- R not available: say so plainly and hand the user the exact command to run locally. Their run is the verification.

Record who verified it (`agent` or `user`) in the state file. Never report a script as verified when it has not actually been run — loosen *who* runs it, never *whether* it ran.

Deliver every generated script with its SETTINGS block in **synthetic mode**, so the user can open it and hit Run immediately. Switching to real data must be a one-line comment change, never an edit the user has to make before the first run.

## Repo Map

```text
skills/           canonical skill definitions (dr-00 ... dr-05, dr-sem-*, orchestrator, qa-gate)
r-scripts/        pattern_extract.R, synthesize_data.R (local privacy-gate templates)
py-scripts/       Python mirror of r-scripts/, plus tools/ callers can't reach directly
                   (desc.py, infer.py, sem_measurement.py, sem_structural.py, plots.py,
                   synthesize_data.py, synthesize_data_correlated.py -- generic templates,
                   copied into a project's scripts/ folder, not run from here directly)
tools/            statistical-methods-roadmap Python packages: sap_gate (Phase 0 QA gate),
                   diagnostics (Phase 1), medical_track (Phase 2), sem_track (Phase 3),
                   reporting (Phase 5 auto-extraction for Stage E), smoke_test.py +
                   parity_check.py (Phase 6 maintainer tooling, see below)
tests/            one self-contained test_*.py per tools/ package -- no pytest required,
                   run directly: `.venv/bin/python tests/test_<name>.py`
projects/         one folder per research question (_template to copy; two worked examples)
docs/             demo runbook (Vietnamese)
INSTALL.md        learner installation guide (Vietnamese)
```

## When Editing This Repo (maintainers)

`skills/` is the canonical copy; `.claude/skills/`, `.opencode/skill/`, and `.agents/skills/` are mirrors — apply any skill change to all of them. Keep skill files in English, learner docs in Vietnamese. Keep artifact filenames consistent everywhere (they are cross-referenced by the orchestrator, QA gate, and docs).

After changing anything under `projects/*/scripts/`, `py-scripts/`, or `tools/`:

- Run `.venv/bin/python -m tools.smoke_test` (Phase 6) -- executes every project's Stage D script against its synthetic dataset and confirms it still exits the way its kind of script is supposed to (a Stage D analysis script exits 0; `pattern_extract.py`/`synthesize_data.py` exit 1 with a usage message when run with no args, by design, since they refuse to guess at real data; `synthesize_data_correlated.py`'s template exits 0 printing edit-me instructions). Budget a few minutes -- it's a real run, not a lint pass.
- Run `.venv/bin/python -m tools.parity_check` (Phase 6) -- flags any script that exists in `.py` but not `.R` for a project, or vice versa. A flagged gap is not automatically a bug (e.g. `sem_invariance.py` is Python-only by a deliberate Phase 3 scoping decision); review before porting, don't auto-generate the missing side.
- Run every file in `tests/` (`for f in tests/test_*.py; do .venv/bin/python "$f"; done`) -- these are cross-checked against known formulas/reference implementations (R's `logistf`, `oneway.test`, VanderWeele & Ding's E-value example), not just "does it run" checks.

`.pre-commit-config.yaml` and `.github/workflows/ci.yml` wrap these for whenever this repo gets a `.git/` directory (it doesn't have one yet) -- the parity check runs informationally on commit and blockingly in CI; the smoke test runs in CI only (too slow for a pre-commit hook) and is `continue-on-error` until a real CI run has confirmed its timing is stable outside this sandbox.
