# Confounding Adjustment Rules

These rules guide the core Step 4 demo. Keep it simple and tied to the prior crude model.

## What Adjustment Means Here

Adjustment asks:

> Does the association between the main predictor and outcome remain after accounting for selected covariates?

It does not prove causality by itself.

## Covariate Selection

Prefer covariates selected from:

- User confirmation
- `analysis_plan.yaml`
- Prior clinical or domain reasoning
- Pre-specified study plan

Do not select covariates only because they have p < 0.05.

## Variables To Treat Carefully

Warn before including:

- Mediators: variables on the pathway from predictor to outcome
- Colliders: variables influenced by both predictor and outcome or their causes
- Post-exposure variables: variables measured after treatment/exposure
- Highly sparse categorical variables
- Variables with high missingness

Do not attempt formal DAG analysis in this core skill. Mention DAGs as an advanced extension only when relevant.

## Model Continuity From Step 3

Use the same model family as Step 3:

- Crude logistic regression -> adjusted logistic regression
- Crude linear regression -> adjusted linear regression
- Crude Cox model -> adjusted Cox model
- Crude Poisson/negative binomial -> adjusted count model

If the model family needs to change, ask for user confirmation and document why.

## Overfitting Checks

Flag `needs_review` when:

- Too many covariates for the available sample size
- Logistic regression has few events per covariate
- Categorical covariates have sparse levels
- Complete-case data loss may be substantial

For teaching purposes, keep the adjusted model small and interpretable.

## Readiness Flags

Set `not_ready` if:

- Step 3 plan is missing.
- Outcome or main predictor differs from Step 3 without user confirmation.
- No covariates are available and the user has not confirmed proceeding without adjustment.
- Required variables are absent from the synthetic CSV/schema.

Set `needs_review` if:

- Covariates are assumed rather than confirmed.
- Covariate rationale is unclear.
- Missingness or sparse categories may affect the adjusted model.
- The user uses causal language for an observational design.
