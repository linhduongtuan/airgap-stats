# SAP Template

Structure for `plans/sap.md`. Keep it basic and skimmable — the tracks already supply the analysis structure, so this document only records decisions the user must own.

Write the SAP in the user's language (Vietnamese by default). Mark every decision `confirmed` or `assumed`.

---

## A. Research question

Restate it precisely, in one or two sentences. If the user's wording is ambiguous, state your reading and mark it `assumed`.

## B. Workflow track and mode

```text
track:  medical | sem
mode:   all_steps | step_by_step
```

One line each on why.

## C. Variable roles

One row per column in the dataset. No column may be missing.

| Variable | Type (from pattern) | Role | Basis |
|---|---|---|---|
| mortality_30day | binary | outcome | confirmed |
| crp | continuous | main_predictor | confirmed |
| age | continuous | confounder | assumed |
| patient_id | id_like | excluded | confirmed |
| dbp | continuous | not_used | assumed |

Roles: `outcome`, `main_predictor`, `confounder`, `id_like` (excluded), `not_used`.

**SEM track:** replace this with a construct table — construct name, its items, and whether the grouping is `confirmed` or `assumed`. Observed covariates keep the table above.

### C1. Confounders — one reason each

This is the item most likely to be wrong, and the one the user is best placed to correct. Never present it as a bare list.

| Confounder | Why it is in the model | Basis |
|---|---|---|
| age | Associated with both CRP and mortality; classic confounder | assumed |
| sex | Precision only; not expected to confound | assumed |

Tell the user they can strike any individual row.

## D. Table 1

```text
stratified:   yes | no
stratify_by:  <variable> | none
p_values:     yes | no
```

State it even when the answer is "not stratified".

## E. Figures

| Figure | Variables | Grouped by |
|---|---|---|
| Correlation heatmap | age, bmi, sbp, egfr, hba1c, crp | — |
| Boxplot series | same continuous set | mortality_30day |

SEM track: heatmap uses scale items ordered by construct; boxplot series shows one box per item.

## F. Model and effect measure

One line, derived from the roles and the outcome type:

```text
Binary outcome + continuous main predictor
  -> logistic regression
  -> odds ratio (OR) with 95% CI, per 1-unit increase in CRP
  -> crude model first, then adjusted for the confounders in C1
```

The user does not have to invent this, but must see it. It is the scientific claim of the study.

## G. Conditional choices

Every method that depends on distribution, written as a branch with its fallback. You have not seen the real data and must not fix these.

| Situation | If assumption holds | If violated |
|---|---|---|
| Comparing CRP across two groups | t-test | Wilcoxon rank-sum |
| Cell counts in a 2×2 table | chi-squared | Fisher exact |

The generated script must branch at runtime and print which branch it chose and why.

## H. Missing data

State the missing-data strategy before any script is generated. `missing_pct` per variable is already in `pattern/dataset_pattern.csv` — use it; do not guess.

```text
strategy:            complete_case | multiple_imputation
variables_affected:  <variables with non-trivial missing_pct, from the pattern file>
imputation_model:    <e.g. "predictive mean matching, m=20"> | none
basis:                confirmed | assumed
```

One line on why. `complete_case` is a defensible default only when `missing_pct` is low (rule of thumb: under ~5%) for every variable used in the model; otherwise prefer `multiple_imputation` or mark the item `needs_review` in Section K and ask the user.

## I. Multiplicity

State the multiplicity plan before any script is generated, even when the answer is "not applicable."

```text
planned_comparisons:  <count of predictors/outcomes tested under this SAP>
correction_method:    none_single_comparison | bonferroni | benjamini_hochberg
basis:                confirmed | assumed
```

One line on why. `none_single_comparison` is only valid when `planned_comparisons` is 1. Section H of the neighbouring list ("What we will not do") already forbids testing every variable against the outcome — this section is what happens if the SAP itself plans more than one comparison.

## J. What we will not do

A short list, to keep the analysis honest — especially in `all_steps`, where a lot of code is generated without a midpoint check.

- No testing of every variable against the outcome.
- No adding covariates after seeing results.
- No reporting a subgroup finding that was not planned here.

## K. Open assumptions

Collect every `assumed` decision in one list at the end, so the user sees them together rather than scattered through the document.

If this list is long and the mode is `all_steps`, recommend `step_by_step`.
