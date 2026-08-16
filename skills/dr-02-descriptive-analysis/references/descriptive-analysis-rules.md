# Descriptive Analysis Rules

These rules guide Stage D2. They are practical defaults, not journal-specific law.

## Guideline Basis

- STROBE emphasizes reporting participants and descriptive data in observational studies.
- SAMPL emphasizes clear reporting of descriptive statistics and uncertainty where appropriate.

Reference links:

- STROBE / EQUATOR: https://www.equator-network.org/reporting-guidelines/strobe/
- SAMPL guideline page: https://www.equator-network.org/reporting-guidelines/sampl/

## Variable Summaries

Use these defaults:

- Continuous, approximately symmetric: mean (SD)
- Continuous, skewed or ordinal-like numeric: median (IQR)
- Binary: n (%)
- Nominal categorical: n (%) for each level
- Ordinal categorical / `integer_scale`: n (%) by level, or median (IQR) if treated as numeric and justified
- Date: exclude from Table 1 unless converted to meaningful intervals
- `id_like` variables: exclude
- `unsupported` variables: exclude

## Normality And Skewness

Do not make normality testing the center of the lesson. Use mean (SD) for familiar clinical variables, median (IQR) for clearly skewed variables. Histograms/summaries are supportive information, not a rigid Shapiro-Wilk gate.

## Grouped Tables

Group by the main predictor or a clinically meaningful comparison group when it helps answer: are the groups comparable at baseline? Do not group by outcome unless the teaching purpose is outcome-stratified description.

## Variable Selection

Default Table 1 variables come from `plans/analysis_plan.yaml`: main predictor, outcome, covariates, group variable. Exclude `id_like`, `date`, `unsupported`, and user-excluded variables by default. Do not automatically include every variable; mention extras in the notes file as optional additions.

Before generating code, present the proposed variables and grouping to the user.

## P-values In Table 1

Optional and context-dependent. Include only when the user requests them. Prefer clear descriptive comparison over p-value hunting. If included:

- Continuous symmetric: `t.test` (2 groups), `aov` (more groups)
- Continuous skewed: `wilcox.test` (2 groups), `kruskal.test` (more groups)
- Categorical: `chisq.test`, or `fisher.test` when expected counts are small

## Footnotes

A good Table 1 footnote states: summary format for continuous variables, summary format for categorical variables, test choices if p-values are shown, abbreviations, and how missing values are handled.

## Readiness Checks For Stage D2

Flag issues in `plans/descriptive_analysis_notes.md` when:

- A selected variable is absent from the synthetic CSV.
- A selected variable is `id_like` or `unsupported` in the pattern file.
- A categorical variable has many levels or heavy `Other` masking.
- Missingness may affect Table 1 interpretation.
- No grouping variable is available but one is expected.
