# Data Readiness Summary

## Status
needs_review

## Workflow Track
sem (confirmed by user)

## What Is Clear
- Outcome: `turnover_intent` (binary 0/1)
- Main predictor: Job Satisfaction latent construct (js_q1–js_q5, Likert 1-5)
- Mediator: Burnout latent construct (bo_q1–bo_q5, Likert 1-5)
- Controls: age, gender, education, tenure_years
- 300 synthetic rows; all pattern columns match the synthetic CSV
- No missing data in synthetic dataset (pattern shows 0% missing for all vars)

## What Needs Confirmation
- Need user to check if js_q1–js_q5 and bo_q1–bo_q5 need reverse coding (check original questionnaire)
- `income`, `work_hours`, `work_mode`, `wlb` — unused so far; include as extra controls or exclude?

## Potential Blockers
- `turnover_intent` is binary → SEM needs DWLS estimator in lavaan, which is supported
- Education is categorical with 4 levels → handle as ordered or dummy-code

## Suggested User Confirmation
- Confirm track: SEM (done)
- Confirm outcome: turnover_intent
- Confirm main predictor: Job Satisfaction latent
- Confirm mediator: Burnout latent
- Confirm controls: age, gender, education, tenure_years
