---
name: dr-02-descriptive-analysis
description: "Stage D2 of the DR workflow: generate a plain base-R descriptive analysis script from plans/analysis_plan.yaml plus the synthetic dataset, then verify it runs with Rscript. Use when the agent needs to create scripts/desc.R for sample description, baseline characteristics, and a publication-ready Table 1 before inferential or SEM analysis."
---

# DR Stage D2: Descriptive Analysis

Use this skill after `dr-01-understand-dataset` has produced `plans/analysis_plan.yaml`. It applies to both tracks (medical and SEM).

The goal is to describe the study sample clearly before inference. The main artifact is a plain R script, `scripts/desc.R`, that the user runs locally in RStudio on the real dataset.

## Coordination Contract

When called by `dr-workflow-orchestrator`, follow `plans/analysis_plan.yaml` and the project's `dr_workflow_state.yaml`.

After producing outputs:

- Report the exact files created and the verification result.
- Do not advance to D3 yourself.
- Say that `dr-output-qa-gate` should check Stage D2 before the workflow proceeds.

## Inputs

Expected inputs:

- `plans/analysis_plan.yaml`
- `data_synthetic/synthetic_dataset.csv`
- `pattern/dataset_pattern.csv` (for exact types and levels)
- Optional user preference for grouping variable, variable order, or p-values

Real data lives outside the repo; never read it, never ask for its path or filename. Generate code whose settings block switches to `file.choose()` for the real run, so the user selects the file interactively in RStudio.

## Workflow

1. Read `plans/analysis_plan.yaml` first.
2. Identify variables to describe: outcome, main predictor, covariates, group variable. SEM track: describe scale items via their construct scores if planned, plus key demographics.
3. Propose a short configuration to the user: table variables, grouping variable, whether to include p-values.
4. Ask whether the user wants to adjust it. If the user does not know or says proceed, use the default from `analysis_plan.yaml`.
5. Generate `scripts/desc.R` following `references/desc-script-template.md`.
6. Verify: run `Rscript scripts/desc.R` from the project folder. Fix errors and rerun until it exits cleanly and writes outputs into `outputs_synthetic/`.
7. Write `plans/descriptive_analysis_notes.md`: how to run on real data, how to read the output, plus any flagged issues.

## Default Configuration

```text
table1_variables = main_predictor + outcome + covariates + group_variable
                   - id_like variables - date variables - unsupported variables
```

Default grouping: the main predictor when it is binary or categorical; no grouping otherwise.
Default p-values: `include_p_values = false` unless the user asks.

Before writing code, show the proposed configuration concisely and ask for confirmation.

## Required Outputs

Always produce:

- `scripts/desc.R` (verified on synthetic data)
- `plans/descriptive_analysis_notes.md`
- Verification outputs in `outputs_synthetic/` (e.g. `table1.csv`)

Use `references/descriptive-analysis-rules.md` for summary rules.
Use `references/desc-script-template.md` for the script structure.

## Base R Constraint

Base R only: no dplyr, no gtsummary, no ggplot2, no rmarkdown. Summaries via `mean`, `sd`, `median`, `quantile`, `table`, `aggregate`; tests via `t.test`, `wilcox.test`, `chisq.test`, `fisher.test`; tables via `write.csv`; figures via `png()` + base graphics. Never include `install.packages()`.

## Boundaries

Do not run inferential models in this step.
Do not interpret associations or causality.
Do not silently include id_like or unsupported variables.
Do not claim the synthetic dataset's descriptive results are the study findings; outputs in `outputs_synthetic/` exist only to prove the code runs.

## Teaching Line

Descriptive analysis answers: who did we study?
