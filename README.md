# AirGap Stats

A toolkit for doing statistical analysis with an AI coding agent — Claude Code, Codex, or
OpenCode — **without the real dataset ever reaching the AI**.

The name is literal: the real dataset is *air-gapped* from the AI at every stage, the same way a
secure system is air-gapped from a network. The AI only ever sees a structural description of your
data (variable names, types, a handful of category labels) and a fully synthetic stand-in dataset
it generates itself. Every analysis script it writes is developed and verified against that
synthetic file. Only you ever run the finished script against the real data, on your own machine —
the AI never touches a real value, a real row count, or a real statistic.

## Why

Handing raw research data to an AI service is often not an option — IRB/ethics constraints,
institutional policy, or plain common sense about patient/participant privacy. AirGap Stats lets
you still get the benefit of an AI coding agent for the tedious parts (writing regression code,
running diagnostics, formatting a manuscript-ready table) by restructuring the workflow so the real
data structurally cannot leave your machine, rather than relying on a promise that the AI "won't
look."

## How it works: five stages

```text
A. Pattern extraction     You run a script locally that reads the real data and extracts ONLY
                           variable names, types, category labels, and % missing — no values,
                           no row counts, no statistics.
   Review gate             You review pattern/dataset_pattern.csv before the agent may read it.
B. Synthesis               The agent writes a synthesis script; you run it locally.
                           -> data_synthetic/synthetic_dataset.csv (every value fabricated,
                              no real row ever copied).
B2. Correlated synthesis   Optional. Same contract, extended to preserve approximate pairwise
    (opt-in)                correlation, so a model's convergence can be sanity-checked before
                             touching real data.
D. Analysis on synthetic   The agent writes and self-verifies every analysis script — descriptive,
                            inferential/SEM, diagnostics — against the synthetic data only.
E. Real results            You run the finished scripts on real data yourself and paste back
                            aggregate output (tables, estimates — never row-level data). The agent
                            turns that into manuscript-ready tables and text, never inventing a
                            number that wasn't in your paste.
```

Two analysis tracks are supported, chosen per project:

| Track | Outcome | Method | R packages needed |
|---|---|---|---|
| **Medical** | Observed directly (mortality, complication, readmission) | Crude + adjusted logistic regression, confounding adjustment, survival analysis, propensity-score methods | 0 — base R only |
| **SEM** | Latent construct measured via a Likert scale (satisfaction, burnout, intent) | Confirmatory factor analysis + structural/mediation model | 1 — `lavaan` |

## Quick start

```bash
# 1. R + RStudio, any 4.x build: https://posit.co/download/rstudio-desktop/
# 2. Point an AI coding agent (Claude Code, Codex, or OpenCode) at this folder.
#    Skills are already in place — .claude/skills/, AGENTS.md, .opencode/skill/.
# 3. Ask the agent:
#    "Use dr-workflow-orchestrator. Tôi muốn bắt đầu một dự án phân tích mới. Quy trình gồm những bước nào?"
```

For the Python side (used by the agent itself; you generally don't need to touch this directly):

```bash
uv venv && uv pip install -e .
.venv/bin/python -m tools.smoke_test   # sanity-check every example project still runs
```

**For a full, click-through walkthrough in Vietnamese** — installation, the `file.choose()` data
workflow, and two complete worked examples (one per track) — see
[`INSTALL.md`](INSTALL.md) or the longer illustrated guide,
[`docs/huong-dan-su-dung.html`](docs/huong-dan-su-dung.html) (open it directly in a browser).

## Repository layout

```text
skills/              Canonical skill definitions agents read (dr-00 privacy gate ... dr-05 present
                      results, dr-sem-*, orchestrator, QA gate). Mirrored into .claude/skills/,
                      .opencode/skill/, .agents/skills/ — keep all four in sync.
r-scripts/            Generic R templates: pattern_extract.R, synthesize_data.R,
                       synthesize_correlated.R. Base R only, no packages, no Stage D.
py-scripts/           Generic Python templates — same Stage A/B/B2 contract, plus full Stage D
                       templates (desc.py, infer.py, sem_measurement.py, sem_structural.py, ...).
tools/                Python statistical-methods packages the Python templates import: sap_gate
                       (pre-registration QA), diagnostics, medical_track, sem_track, reporting,
                       plus smoke_test.py / parity_check.py / skills_sync_check.py (maintainer
                       tooling). No R equivalent — R analysis scripts inline the same logic
                       per-project instead (see docs/codebase-tutorial.html Part III).
tests/                One self-contained test_*.py per tools/ package — no pytest, run directly:
                       .venv/bin/python tests/test_<name>.py
projects/              One folder per research question. _template/ is the empty starting point;
                       example-clinical/ and example-survey-sem/ are runnable demo projects (see
                       docs/dr-demo-runbook.md); crp-mortality/ and burnout-mediation/ are the
                       fuller worked examples referenced throughout the docs.
docs/                  codebase-tutorial.html (Python+R developer reference), huong-dan-su-dung.html
                       (Vietnamese end-user manual), statistical-methods-roadmap.html (phase-by-phase
                       implementation status), dr-demo-runbook.md (Vietnamese teaching script).
INSTALL.md             Vietnamese installation + quick-start guide.
CLAUDE.md / AGENTS.md   Agent operating instructions (byte-identical; keep them that way).
```

## Documentation

| Document | Audience | Language |
|---|---|---|
| [`INSTALL.md`](INSTALL.md) | End users — install and run your first project | Vietnamese |
| [`docs/huong-dan-su-dung.html`](docs/huong-dan-su-dung.html) | End users — detailed manual with two full worked examples | Vietnamese |
| [`docs/codebase-tutorial.html`](docs/codebase-tutorial.html) | Developers/maintainers — how every Python and R piece works | English |
| [`docs/statistical-methods-roadmap.html`](docs/statistical-methods-roadmap.html) | Maintainers — implementation status by phase | English |
| [`docs/dr-demo-runbook.md`](docs/dr-demo-runbook.md) | Instructors — a scripted 90-minute live demo | Vietnamese |
| [`CLAUDE.md`](CLAUDE.md) / [`AGENTS.md`](AGENTS.md) | The AI agent itself | English |

## Testing

```bash
# Python: one self-contained script per tools/ package
for f in tests/test_*.py; do .venv/bin/python "$f"; done

# Cross-language drift check: flags any scripts/*.py with no scripts/*.R counterpart or vice versa
.venv/bin/python -m tools.parity_check

# Full smoke test: runs every project's Stage D script against its synthetic dataset
.venv/bin/python -m tools.smoke_test
```

R analysis scripts have no automated suite — they're verified by direct `Rscript` runs
cross-checked against the matching Python output and, for the two hand-implemented algorithms
(Firth regression, the E-value), against published reference values. See
`docs/codebase-tutorial.html` Part V for the full accounting.

## License

Copyright © 2026. All Rights Reserved.

This material is licensed to one registered user only. It may not be copied, modified, shared,
redistributed, sublicensed, published, sold, uploaded to a shared workspace, or provided to any
third party, whether for commercial or non-commercial purposes.
