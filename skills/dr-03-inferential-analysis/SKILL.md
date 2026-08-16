---
name: dr-03-inferential-analysis
description: "Stage D3 of the DR workflow, medical track: create and confirm a crude inferential analysis plan, then generate the crude section of scripts/infer.R in base R and verify it with Rscript. Use when the agent needs to select an unadjusted statistical test/model from the research question, outcome type, and predictor type, producing plans/inferential_analysis_plan.yaml and a runnable crude analysis script."
---

# DR Stage D3 (Medical): Inferential Analysis

Use this skill after D1 has created `plans/analysis_plan.yaml` with `workflow_track: medical` and D2 has described the sample.

The goal is to analyze the main research question before adjustment. This step must be plan-first, code-second.

## Coordination Contract

When called by `dr-workflow-orchestrator`, follow `plans/analysis_plan.yaml`, prior descriptive outputs, and the project's `dr_workflow_state.yaml`.

After producing outputs:

- Report the exact files created and the verification result.
- Do not advance to D4 yourself.
- Say that `dr-output-qa-gate` should check Stage D3 before the workflow proceeds.

## Inputs

Expected inputs:

- `plans/analysis_plan.yaml`
- `data_synthetic/synthetic_dataset.csv`
- `pattern/dataset_pattern.csv`
- Optional user clarification about outcome, predictor, question, effect measure, or method

Real data lives outside the repo; never read it, never ask for its path or filename. Generate code whose settings block switches to `file.choose()` for the real run.

## Workflow

1. Read `plans/analysis_plan.yaml` first.
2. Restate the research question as understood.
3. Identify outcome, main predictor, outcome type, predictor type, and question type.
4. Propose a crude/unadjusted analysis plan.
5. Ask the user to confirm or revise the plan before generating code.
6. On confirmation (or explicit proceed), write `plans/inferential_analysis_plan.yaml`.
7. Generate `scripts/infer.R` with the crude analysis section, following `references/infer-script-spec.md`.
8. Verify: `Rscript scripts/infer.R` from the project folder; fix and rerun until clean.
9. Write `plans/inferential_analysis_notes.md`.

## Confirmation Prompt

Before writing code, show a concise plan:

```text
I understand the main question as:
"..."

For Stage D3, I propose crude/unadjusted analysis:
- Outcome: ...
- Main predictor: ...
- Method: ...
- Effect measure: ...
- Model/test: ...
- Report: estimate, 95% CI, p-value

Confounding adjustment will be handled in Stage D4.
Do you confirm this plan, or do you want to change the outcome, predictor, or method?
```

If the user says they do not know, proceed with the plan from `analysis_plan.yaml` and mark assumptions in the plan.

## Required Outputs

Always produce:

- `plans/inferential_analysis_plan.yaml`
- `scripts/infer.R` (crude section, verified on synthetic data)
- `plans/inferential_analysis_notes.md`

Use `references/inferential-plan-template.md`.
Use `references/inferential-decision-rules.md`.
Use `references/reporting-effect-measures.md`.
Use `references/infer-script-spec.md`.

## Base R Constraint

Base R only: `glm`, `lm`, `t.test`, `wilcox.test`, `chisq.test`, `fisher.test`. Effect estimates and Wald 95% CIs via `coef()` and `confint.default()`; for logistic models exponentiate to ORs. Results written to `outputs_synthetic/` (synthetic run) as CSV plus readable console output. No packages, no `install.packages()`.

## Boundaries

This step is for crude or unadjusted inference.

Do not add covariates to the primary model unless the user explicitly asks.
Do not handle confounding adjustment; leave that to Stage D4.
Do not make causal claims.
Do not run broad screening across every variable.
Do not choose a model just to improve p-values.
Do not treat synthetic-run numbers as scientific findings; they only prove the code runs.

## Teaching Line

Analyze to answer the question, not to hunt for p-values.
