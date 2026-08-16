# Reporting Effect Measures

Report effect size first, uncertainty second, p-value last.

## Defaults

- Logistic regression: odds ratio (OR), 95% CI, p-value
- Linear regression: beta coefficient or mean difference, 95% CI, p-value
- Two-group continuous comparison: mean difference, 95% CI, p-value
- Nonparametric group comparison: median difference if available, otherwise test statistic/p-value with clear limitation
- Cox model: hazard ratio (HR), 95% CI, p-value
- Poisson/negative binomial model: rate ratio (RR), 95% CI, p-value

## Language

Use association language:

- "was associated with"
- "had higher/lower odds of"
- "had a mean difference of"

Avoid causal language in Step 3:

- "caused"
- "reduced mortality"
- "increased risk because of"
- "protective effect"

## Interpretation Template

Use this structure:

```text
To evaluate the association between [predictor] and [outcome], we fit a crude [model/test].
The estimated [effect measure] was [estimate] (95% CI: [lower] to [upper], p = [p]).
This suggests [plain-language association], before adjustment for potential confounders.
Adjusted analysis is planned in Step 4.
```

## P-value Handling

Do not interpret p-value alone.

If p < 0.05:

- State that there is statistical evidence of association in the crude analysis.

If p >= 0.05:

- State that the crude analysis did not show clear statistical evidence of association.

Always mention effect size and CI before p-value.
