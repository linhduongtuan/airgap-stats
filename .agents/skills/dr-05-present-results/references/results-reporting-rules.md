# Results Reporting Rules

Use these rules when converting model output into manuscript-ready results.

## Core Principles

- Report effect size first.
- Report 95% confidence interval second.
- Report p-value last.
- State the model used.
- State covariates adjusted for.
- Use association language unless causal language is justified by design and prior plans.

## Do Not Invent Numbers

Only use numbers from user-provided RStudio output.

If a number is absent:

- Ask the user for the missing output, or
- Use a placeholder such as `[adjusted OR]`, clearly labeled as a placeholder.

Never use numeric results from synthetic data as the final research result.

## Language

Use:

- "To assess the association between..."
- "In the crude analysis..."
- "After adjustment for..."
- "was associated with..."
- "had higher/lower odds of..."

Avoid:

- "caused"
- "proved"
- "eliminated confounding"
- "independently caused"
- "treatment effect" unless justified

## P-value Handling

Use p-values as supporting evidence, not the main result.

Format:

- `p = 0.043`
- `p < 0.001`
- Avoid `p = 0.000`

## Limitations

Include 2-3 honest limitations when requested or when writing `present_results.md`.

Common limitation types:

- Observational design limits causal interpretation.
- Residual confounding may remain.
- Missing data or complete-case analysis may affect estimates.
- Small sample or sparse events may reduce precision.
- Measurement limitations may affect variable validity.

Three of these are no longer a free choice each time (Phase 5 of the statistical-methods roadmap): the missing-data/complete-case caveat, the single-item-measurement caveat, and a synthetic-verification transparency note are pulled forward automatically from plan files via `limitations_pulled_forward` in `results_traceability_check.yaml` — see `traceability-check-template.md` and `results-paragraph-template.md`'s "Limitations Paragraph (auto-populated)" section. Add study-specific limitations (observational design, residual confounding, small sample) on top of those, not instead of them.

Keep limitations specific to the actual plan and output.
