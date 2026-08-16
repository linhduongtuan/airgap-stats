# Inferential Decision Rules

These rules support crude/unadjusted inferential analysis. They are practical defaults, not replacements for statistical judgment.

## Core Rule

Choose the analysis from the research question and outcome type first.

Do not start by asking "which test gives significance?"

## Common Decision Map

Use these defaults:

- Binary outcome + binary/categorical predictor: logistic regression; report odds ratio.
- Binary outcome + continuous predictor: logistic regression; report odds ratio per unit or per meaningful increment.
- Continuous outcome + binary predictor: linear regression or two-sample t-test; report mean difference.
- Continuous outcome + categorical predictor with more than two groups: linear regression or ANOVA; report mean differences or global test.
- Continuous outcome + continuous predictor: linear regression; report beta coefficient.
- Ordinal outcome: ordinal regression needs review.
- Nominal outcome with more than two categories: multinomial regression needs review.
- Time-to-event outcome: survival analysis needs review, usually Kaplan-Meier/Cox if time and event variables exist.
- Count outcome: Poisson or negative binomial model needs review.

## Question Type

Use:

- Descriptive question: no inferential model unless the user asks for estimation with CI.
- Comparative question: compare groups using outcome and group variable.
- Associative question: model outcome as a function of main predictor.
- Predictive question: Step 3 may not be sufficient; prediction workflow needs separate planning.

## Crude Analysis Boundary

Step 3 should usually use:

```text
outcome ~ main_predictor
```

Do not add covariates here. Covariates belong in Step 4 unless the user explicitly says the current step should include them.

## Basic Checks Before Fitting

Generated R code should check:

- Outcome exists.
- Main predictor exists.
- Outcome has enough variation.
- Predictor has enough variation.
- Missingness in outcome and predictor.
- For logistic regression, both outcome classes are present after complete-case filtering.

## Readiness Flags

Set `not_ready` if:

- Outcome is missing or has one observed class.
- Main predictor is missing or has one observed value.
- The method requires variables that are absent.

Set `needs_review` if:

- Outcome type is uncertain.
- Predictor type is uncertain.
- Sample size is small for the selected model.
- Sparse cells may make logistic regression unstable.
- The question sounds causal but the design is observational.
