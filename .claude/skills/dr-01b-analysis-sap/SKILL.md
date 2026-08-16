---
name: dr-01b-analysis-sap
description: "Stage D1b of the DR workflow: draft a basic Statistical Analysis Plan from the analysis plan and synthetic dataset, get explicit user approval of variable roles, Table 1 stratification and figure variables, and record whether the project runs in all_steps or step_by_step mode. Use after dr-01-understand-dataset and before any analysis code is generated, in both tracks and both modes."
---

# DR Stage D1b: Analysis SAP and Mode

Use this skill after `dr-01-understand-dataset` has produced `plans/analysis_plan.yaml`, and before any analysis script exists.

**The SAP is required in both modes.** It is the single place where the user approves the scientific decisions of the project. The mode only determines *when the remaining approvals happen*, not whether the SAP is needed.

## Coordination Contract

When called by `dr-workflow-orchestrator`, follow `plans/analysis_plan.yaml` and the project's `dr_workflow_state.yaml`.

After producing outputs:

- Report the exact files created and the chosen mode.
- Never generate analysis code in this skill.
- Say that `dr-output-qa-gate` should check Stage D1b before code generation starts.

## Inputs

- `plans/analysis_plan.yaml` (variable roles, track)
- `pattern/dataset_pattern.csv` (types and levels)
- `data_synthetic/synthetic_dataset.csv` (column check only)
- The user's research question

Real data lives outside the repo; never read it, never ask for its path or filename. You have not seen the real distributions and must not pretend otherwise.

## The Two Modes

Ask the user which mode they want. Both produce **identical, separate script files** — `desc.R`, `plots.R`, `infer.R` or `sem_*.R`. Mode never merges scripts, renames them, or changes their contents.

| | `step_by_step` | `all_steps` |
|---|---|---|
| SAP approval | Required | Required |
| After approval | Generate one script, stop | Generate every script in one pass |
| Next approval point | User runs that script locally on synthetic and confirms it works | None — already given in the SAP |
| Best for | Learners, or plans with several `assumed` roles | Users confident in the plan |

In `step_by_step`, the user runs each script **on the synthetic dataset on their own machine**. The purpose is only to confirm the code runs and the output has the right shape — right variables, right stratification columns, nothing unexpected. The numbers are meaningless and must never be interpreted.

Mode is a workflow-UX layer only. Downstream skills, `dr-output-qa-gate` and `dr-05-present-results` behave identically either way and need no knowledge of it.

## What the SAP Must Contain

Keep it basic. This is not the full seven-section SAP of the custom branch; the tracks already supply the structure. Required items:

1. **Role of every variable.** A table with one row per column in the dataset: `outcome`, `main_predictor`, `confounder`, `id_like` (excluded), `not_used`. No variable may be left without a role. For the SEM track, items are grouped into constructs instead.
2. **Table 1 stratification.** Whether Table 1 is stratified, and by which variable. State it even when the answer is "not stratified".
3. **Figure variables.** Which variables enter the correlation heatmap, which enter the boxplot series, and what the boxplots are grouped by.
4. **Model and effect measure.** One line, derived by you from the roles and the outcome type — e.g. binary outcome + continuous predictor → logistic regression, reporting OR with 95% CI. The user does not have to invent it, but must see it: it is the scientific claim of the whole study.
5. **Missing-data strategy.** `complete_case` or `multiple_imputation`, named before any script exists — not decided implicitly by whatever `read.csv` happens to drop. Read `missing_pct` per variable from `pattern/dataset_pattern.csv`.
6. **Multiplicity plan.** How many comparisons this SAP plans, and the correction method if more than one. Even a single planned comparison must say so explicitly (`none_single_comparison`).

Every decision carries `confirmed` (the user stated it) or `assumed` (you inferred it). Use `references/sap-template.md`.

Items 5 and 6 are pre-registration gates: `tools/sap_gate` checks them mechanically (`python -m tools.sap_gate <project_dir>`) and blocks Stage D2+ if they are missing, so do not skip them even in `step_by_step` mode.

## The Conditional Branching Rule

You have not seen the real data. The synthetic dataset's distributions were generated from the pattern file, so **its shape is your own invention** and proves nothing about the real distributions.

Therefore any method that depends on distribution must be written **conditionally** in the SAP, with the fallback named:

```text
If CRP is clearly right-skewed  -> Wilcoxon rank-sum
If approximately symmetric      -> two-sample t-test
```

Never fix a distribution-dependent method. The generated script must branch at runtime and print which branch it took and why, so the user sees the decision on their own machine.

This matters most in `all_steps`, where there is no midpoint at which the user could correct a wrong assumption. Batching is safe *because* the code branches, not despite it.

## Workflow

1. Read `plans/analysis_plan.yaml`, the pattern file, and the synthetic CSV column list.
2. Ask which mode the user wants. Record the answer.
3. Draft `plans/sap.md` with the four required items.
4. Summarise the 5-7 most contestable decisions in chat, contestable ones first, each marked `confirmed` or `assumed`. Do not dump the whole SAP into chat.
5. If most roles are `assumed` and the user chose `all_steps`, say so and recommend `step_by_step` instead. Batching multiplies one wrong role across every generated script.
6. **Stop and wait for explicit approval.** Do not write a single line of R before it.
7. On approval, record `analysis_mode` and `sap_approved: true` in the state file, and hand back to the orchestrator.

## Anti-Rubber-Stamp

The confounder list is the most dangerous item in the SAP: confounder choice is domain knowledge, not statistics. Present confounders as a table with a one-line reason each (confounder / precision / suspected effect modifier) so the user can strike individual rows rather than approving a block.

If the user replies only "ok" to a SAP containing several `assumed` decisions, name the assumed ones once more and ask them to confirm those specifically.

## Required Outputs

- `plans/sap.md`
- `analysis_mode` and `sap_approved` recorded in `dr_workflow_state.yaml`

## What the SAP Does Not Replace

The SAP replaces the *conversations* of D2/D3/D4, not their *artifacts*. Downstream skills still write `plans/inferential_analysis_plan.yaml`, `plans/confounding_adjustment_plan.yaml` and their notes files exactly as before — they simply read decisions from the approved SAP instead of asking the user again.

## Boundaries

Do not generate analysis code in this step.
Do not fix a distribution-dependent method.
Do not proceed without explicit approval; silence is not approval.
Do not treat synthetic distributions as evidence about the real data.
Do not expand the SAP into a full methods section; keep it basic and skimmable.

## Teaching Line

Because the AI cannot see your data, the plan is written blind — which is exactly what pre-registration asks for.
