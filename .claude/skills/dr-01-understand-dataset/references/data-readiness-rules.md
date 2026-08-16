# Data Readiness Rules

This step is not data cleaning. It only decides whether the project is ready enough for the next DR stage.

## Readiness Status

Use:

- `ready`: outcome (or outcome construct), main predictor, and basic variable roles are clear; no obvious blocker appears in the pattern/synthetic metadata.
- `needs_review`: analysis can continue for teaching/demo purposes, but one or more assumptions need confirmation.
- `not_ready`: a blocker prevents responsible analysis planning.

## Blocking Issues

Set status to `not_ready` if any of these are present:

- No outcome can be identified from user input or the pattern file.
- Outcome exists but the pattern file shows only one level.
- Main predictor is required by the question but cannot be identified.
- Declared outcome or predictor is absent from the pattern file or synthetic CSV.
- Pattern file and synthetic CSV disagree on core column names.
- SEM track: an outcome construct has no identifiable items.

## Review Issues

Set status to `needs_review` if any of these are present:

- Outcome or main predictor is inferred only by heuristic.
- Covariates (medical) or item groups (SEM) are not specified.
- Outcome or main predictor missingness is high in the pattern file.
- Important variables are `id_like`, `unsupported`, or masked heavily as `Other`.
- A categorical variable has many levels.
- Unit of analysis is unknown.
- SEM track: a construct has fewer than 3 items.

## Practical Thresholds

Use these as rough flags, not hard statistical rules:

- Missingness under 5%: usually acceptable.
- Missingness 5-20%: mention as review issue.
- Missingness over 20%: highlight strongly.
- Categorical variable with more than 10 levels: may need recoding before modeling.
- SEM: constructs with 3+ items are workable; 2 items need review.

Note: the real sample size is deliberately unknown to the agent. Sample-size cautions belong in the notes as questions for the user, not as computed checks.

## Summary Format

Write `plans/data_readiness_summary.md` with:

```markdown
# Data Readiness Summary

## Status
ready / needs_review / not_ready

## Workflow Track
medical / sem (confirmed / proposed)

## What Is Clear
- ...

## What Needs Confirmation
- ...

## Potential Blockers
- ...

## Suggested User Confirmation
- Confirm track: ...
- Confirm outcome: ...
- Confirm main predictor: ...
- Confirm covariates / constructs: ...
```

Keep the summary short enough to read during a live demo.
