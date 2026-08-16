---
name: dr-workflow-orchestrator
description: "Coordinate the DR research data analysis workflow across per-project folders: privacy gate (pattern extraction, synthetic data), analysis on synthetic data in the medical or SEM track, and real-results reporting. Use when the user wants to start or resume a DR project, asks what to do next, checks workflow status, or needs routing across dr-* skills."
---

# DR Workflow Orchestrator

Use this skill to coordinate the DR workflow. It does not perform statistical analysis. It manages projects, state, artifact checks, and routing to the correct dr-* step skill.

## Project Model

Every research question lives in its own folder under `projects/`. All outputs for a question are created only inside its project folder. Never write project artifacts anywhere else.

```text
projects/<project-name>/
  dr_workflow_state.yaml
  pattern/              dataset_pattern.csv (user-reviewed)
  data_synthetic/       synthetic_dataset.csv
  plans/                analysis_plan.yaml and step plans
  scripts/              all generated .R scripts
  outputs_synthetic/    tables/figures produced when verifying scripts on synthetic data
  results_real/         user-pasted RStudio output and final result documents
```

**The real dataset is never inside the repo.** It stays wherever the user keeps it; scripts access it only through `file.choose()` in the user's RStudio session. The agent never knows its path.

To start a new research question: copy `projects/_template/` to `projects/<new-name>/` and initialize `dr_workflow_state.yaml` with the project name. Tell the user to keep their real dataset outside the pack folder, exactly where it already is.

If the user's request does not name a project and more than one exists, ask which project is active before doing anything else.

## Core Workflow

```text
Stage A  dr-00-privacy-gate: agent writes scripts/pattern_extract.R;
         user runs it in RStudio on the real data -> pattern/dataset_pattern.csv;
         user reviews the pattern file (review gate) before the agent may read it.

Stage B  dr-00-privacy-gate: agent reads the reviewed pattern file and writes
         scripts/synthesize_data.R.

Stage C  user runs it in RStudio -> data_synthetic/synthetic_dataset.csv.
         From here the agent may read the synthetic dataset.

Stage D  analysis on synthetic data:
  D1  dr-01-understand-dataset  -> plans/analysis_plan.yaml (+ track decision)
  D1b dr-01b-analysis-sap       -> plans/sap.md (+ mode decision)
      REQUIRED in both modes. No analysis code may be written before the
      user approves the SAP.
  Medical track:
    D2  dr-02-descriptive-analysis     -> scripts/desc.R
    D2b dr-02b-visual-exploration      -> scripts/plots.R   (optional)
    D3  dr-03-inferential-analysis     -> scripts/infer.R (crude section)
    D4  dr-04-confounding-adjustment   -> scripts/infer.R (adjusted section)
  SEM track (public health / social sciences):
    D2  dr-02-descriptive-analysis     -> scripts/desc.R
    D2b dr-02b-visual-exploration      -> scripts/plots.R   (optional)
    D3  dr-sem-01-measurement-model    -> scripts/sem_measurement.R
    D4  dr-sem-02-structural-model     -> scripts/sem_structural.R
  Each script must be verified by running it with Rscript on the synthetic
  dataset before its stage is marked complete.

Stage E  user runs the scripts on the real data in RStudio and pastes the
         output; dr-05-present-results writes final tables and Results text
         into results_real/. Numbers come only from user-provided output.
```

Use `dr-output-qa-gate` to check each stage before advancing.

## Analysis Modes

After Stage C, when the user asks to run the analysis, `dr-01b-analysis-sap` records `analysis_mode`. Both modes require an approved SAP first, and both produce the same separate script files with the same contents. Only the approval rhythm differs.

```text
step_by_step  generate one script -> user runs it locally on the SYNTHETIC
              dataset -> user confirms it works -> generate the next one

all_steps     generate every script for the track in one pass, verifying each
              on synthetic as you go
```

In `all_steps`, apply **fail-stop**: if a script fails verification, stop there and report which stage broke. Never stack later scripts on top of a broken one. Finish by reporting a table of files generated, verification status, and every decision that was `assumed` rather than `confirmed`.

You are not the runtime. The deliverable is code the user runs on their own machine — see the Verification Duty in CLAUDE.md. Never stall a stage because you have no R.

## State File

Maintain `dr_workflow_state.yaml` inside the active project folder using the structure from `projects/_template/dr_workflow_state.yaml`. Update it after every completed action. When resuming a session, read it first and continue from `current_stage`.

## Routing Rules

Route by artifacts inside the active project, not by guesswork:

- No project folder yet: create one from `projects/_template/`.
- `pattern/dataset_pattern.csv` missing or not user-reviewed: route to `dr-00-privacy-gate` (Stage A).
- Pattern reviewed but `data_synthetic/synthetic_dataset.csv` missing: route to `dr-00-privacy-gate` (Stage B/C).
- `plans/analysis_plan.yaml` missing: route to `dr-01-understand-dataset`.
- Track undecided: have `dr-01-understand-dataset` confirm `workflow_track` with the user.
- `plans/sap.md` missing or `sap_approved` not true: route to `dr-01b-analysis-sap`. Never generate analysis code before this returns an approved SAP, in either mode.
- `scripts/desc.R` missing or unverified: route to `dr-02-descriptive-analysis`.
- `scripts/desc.R` verified and `scripts/plots.R` missing: offer `dr-02b-visual-exploration` (both tracks). This stage is optional: suggest it once, and if the user declines or does not answer, continue to D3. Never block on it.
- Medical track: `scripts/infer.R` crude section missing -> `dr-03-inferential-analysis`; adjusted section missing -> `dr-04-confounding-adjustment`.
- SEM track: `scripts/sem_measurement.R` missing -> `dr-sem-01-measurement-model`; `scripts/sem_structural.R` missing -> `dr-sem-02-structural-model`.
- Final reporting requested but no user-provided RStudio output: ask the user to run the scripts on real data and paste the output.
- Output available: route to `dr-05-present-results`.

## Response Pattern

When the user asks what to do next, respond with:

```text
Project: ...
Current stage: ...
Stage QA: pass / needs_revision / blocked
Next step: ...
Why: ...
What I need from you: ...
```

Keep it short.

## Boundaries

Never read real data, ask for its location, or tell the user to copy it into the repo. If real data appears inside the repo (e.g. a user-created `data_real/` folder), warn the user to move it out; never read it.
Never open a figure generated from real data, and never accept one pasted by the user. Figures are row-level data; only aggregate text output may be pasted. Synthetic figures under `outputs_synthetic/figures/` are fine to open.
Never write project outputs outside the active project folder.
Do not run statistical analysis directly; route to step skills.
Do not create final results without user-provided RStudio output.
Do not skip the pattern review gate or the user confirmations required by D2/D3/D4.
Do not proceed past a stage whose QA status is `blocked`.
