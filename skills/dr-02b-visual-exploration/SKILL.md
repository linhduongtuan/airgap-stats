---
name: dr-02b-visual-exploration
description: "Stage D2b of the DR workflow: generate a base-R visual exploration script (correlation heatmap + boxplot series) from plans/analysis_plan.yaml and the synthetic dataset, then verify it runs with Rscript and inspect the rendered PNGs. Use after dr-02-descriptive-analysis when the user wants to see relationships between variables before modelling, for either the medical or SEM track."
---

# DR Stage D2b: Visual Exploration

Use this skill after `dr-02-descriptive-analysis` has produced a verified `scripts/desc.R`. It applies to both tracks.

The goal is to let the researcher *see* distributions and associations before any model is fitted. The main artifact is `scripts/plots.R`, which the user runs locally in RStudio on the real dataset.

This stage is **optional and non-blocking**: a project may advance to D3 without it. Never mark a project incomplete because it lacks figures.

## Coordination Contract

When called by `dr-workflow-orchestrator`, follow `plans/analysis_plan.yaml` and the project's `dr_workflow_state.yaml`.

After producing outputs:

- Report the exact files created and the verification result.
- Do not advance to D3 yourself.
- Say that `dr-output-qa-gate` may check Stage D2b, and that D3 can proceed either way.

## Inputs

- `plans/analysis_plan.yaml`
- `data_synthetic/synthetic_dataset.csv`
- `pattern/dataset_pattern.csv` (for types and levels)
- SEM track: `plans/sem_measurement_plan.yaml` if it already exists, for construct grouping
- Optional user preference for which variables to plot and the grouping variable

Real data lives outside the repo; never read it, never ask for its path or filename.

## The Figure Privacy Rule

Figures differ from tables and must be handled differently. A table in this workflow is aggregate (means, SDs, counts). **A boxplot or scatter is row-level data rendered as pixels: every point is one participant, and an outlier dot is often the most identifiable person in the study.**

Three consequences, all mandatory. See `references/figure-privacy-rules.md`.

1. **Real figures never enter the repo.** The generated script writes real-run figures to `file.path(dirname(input_csv), "dr_figures")` — beside the user's real dataset, outside the pack. The agent never learns that path. Synthetic figures go to `outputs_synthetic/figures/`.
2. **Real figures never come back to the agent.** Aggregate text output may be pasted at Stage E, as it always could. Images generated from real data may not. If the user offers one, decline and explain why.
3. **The agent may open synthetic figures only.** Reading a PNG under `outputs_synthetic/figures/` is expected and is part of verification. Never open anything under a `dr_figures/` folder or any user-supplied image of real data.

## Workflow

1. Read `plans/analysis_plan.yaml` (and the SEM measurement plan if present).
2. Select variables:
   - Medical track: numeric variables for the heatmap; the outcome or main predictor as the boxplot grouping variable.
   - SEM track: scale items ordered by construct for the heatmap; item distributions for the boxplot series.
3. Show the proposed figure list and grouping to the user and ask for confirmation. Defaults apply if the user says proceed.
4. Generate `scripts/plots.R` following `references/plots-script-template.md`.
5. Verify on synthetic data. If R is available to you, run `Rscript scripts/plots.R` from the project folder and fix errors until it exits cleanly. If it is not, say so and hand the user the exact command; their run is the verification. Never claim a run that did not happen.
6. **Check that the figures render, not just that the script exits.** A script can exit 0 and still produce an upside-down matrix or clipped labels.
   - With R: open the PNGs under `outputs_synthetic/figures/` and look at them. Confirm the correlation diagonal reads 1.00, the off-diagonal is symmetric, axis labels are not clipped, and text is legible.
   - Without R: put that same checklist in the notes file so the user checks it when they run.
7. Leave the settings block in **synthetic mode** so the user can run the script immediately without editing. The real-run lines stay commented directly beneath, one comment swap away.
8. Write `plans/visual_exploration_notes.md`: the command to run it on synthetic, how to switch to real data, where real figures will appear, how to read each figure, the visual checklist, and the privacy rule.

## Default Configuration

```text
heatmap_variables = numeric variables from analysis_plan.yaml
                    - id_like variables - date variables
                    (SEM track: scale items, ordered by construct)
boxplot_group     = outcome if binary/categorical, else main predictor, else none
                    (SEM track: no grouping; one box per item)
show_individual_points = TRUE
```

`show_individual_points` defaults to `TRUE`. Outliers carry real analytic meaning and the figure never leaves the user's machine, so hiding them protects nobody and costs information. Document the flag; let the user set it to `FALSE` if they intend to show the figure to others.

## Required Outputs

- `scripts/plots.R` (verified on synthetic data, delivered in synthetic mode)
- `plans/visual_exploration_notes.md`
- Verification figures in `outputs_synthetic/figures/`

## Base R Constraint

Base R graphics only: `png(type = "cairo")`, `image()`, `boxplot()`, `axis()`, `text()`, `rect()`, `colorRampPalette()`, `layout()`. No ggplot2, no corrplot, no pheatmap, no lattice. Never include `install.packages()`.

Use `type = "cairo"` in `png()`: it renders Vietnamese diacritics reliably and works headless.

## Small-Cell Guard

Do not draw a box for a group with fewer than 5 observations. Such a box is statistically meaningless and discloses those individuals. Warn and skip the figure instead.

## Boundaries

Do not run statistical tests or report p-values from figures.
Do not interpret a correlation as an effect, an adjusted association, or causality.
Do not treat patterns in synthetic figures as findings. On synthetic data, correlations are near zero and SEM items show no block structure by construction; say so plainly rather than describing the noise.
Do not add a figure the user did not confirm.

## Teaching Line

A correlation heatmap shows what moves together; it does not show what causes what. The model still has to be fitted.
