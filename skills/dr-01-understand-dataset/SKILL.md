---
name: dr-01-understand-dataset
description: "Stage D1 of the DR workflow: understand the dataset from its reviewed pattern file and synthetic CSV before analysis. Use when the agent needs to turn pattern/dataset_pattern.csv, data_synthetic/synthetic_dataset.csv, and a research question into plans/analysis_plan.yaml, a data readiness summary, and a confirmed workflow track (medical or SEM)."
---

# DR Stage D1: Understand Dataset

Use this skill to create the first reusable analysis artifact of a project: `plans/analysis_plan.yaml`.

Inputs come from the privacy gate: the user-reviewed `pattern/dataset_pattern.csv` and the fully synthetic `data_synthetic/synthetic_dataset.csv`. Treat synthetic data as a code-generation aid only; never claim scientific findings from it.

## Coordination Contract

When called by `dr-workflow-orchestrator`, follow the artifact paths and current state from the project's `dr_workflow_state.yaml`.

After producing outputs:

- Report the exact files created.
- Do not advance to D2 yourself.
- Say that `dr-output-qa-gate` should check Stage D1 before the workflow proceeds.

## Priority Order

When assigning variable roles, use this order:

1. User-provided research question or study description
2. Variable types and levels from `pattern/dataset_pattern.csv`
3. Variable names and structure of the synthetic CSV
4. Heuristics, marked clearly as inferred and low confidence

If the question is ambiguous, still create `analysis_plan.yaml`, but mark uncertain fields with `confidence: low` and set readiness to `needs_review`.

## Track Decision

Decide the workflow track with the user:

- `medical`: observed outcome and predictors, regression + confounding adjustment (dr-02, dr-03, dr-04).
- `sem`: latent constructs measured by item sets (Likert scales, questionnaires), measurement model + structural model (dr-02, dr-sem-01, dr-sem-02).

Propose a track based on the research question and pattern (`integer_scale` item groups suggest SEM), then ask the user to confirm. Record `workflow_track` in both `analysis_plan.yaml` and the state file.

## Workflow

1. Read `pattern/dataset_pattern.csv` first (only if the state file records it as user-reviewed).
2. Inspect the synthetic CSV enough to confirm columns match the pattern.
3. Parse the user research question.
4. Assign variable roles with a `source` and `confidence` for each role. For SEM, group items into constructs and confirm with the user.
5. Propose the workflow track and confirm it.
6. Choose a provisional primary analysis logic based on outcome type and question type.
7. Run a light data readiness review.
8. Write `plans/analysis_plan.yaml`.
9. Write `plans/data_readiness_summary.md`.

## Required Outputs

Always produce:

- `plans/analysis_plan.yaml`
- `plans/data_readiness_summary.md`

Use the template in `references/analysis-plan-template.md`.
Use the readiness criteria in `references/data-readiness-rules.md`.

## Boundaries

Do not generate analysis code in this step.
Do not clean the data in this step.
Real data lives outside the repo; never read it, never ask for its path or filename. Do not ask for real data or real statistics.
Do not overstate inferred variable roles as certain.
Do not treat the synthetic dataset as evidence for scientific interpretation.

## Teaching Line

If we do not know each variable's role, we are not ready to analyze.
