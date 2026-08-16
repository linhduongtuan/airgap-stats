# Crude Vs Adjusted Reporting

Step 4 should produce a compact comparison of the main predictor estimate before and after adjustment.

## Table Structure

```text
Table. Crude and adjusted association between [predictor] and [outcome]

Model        Estimate      95% CI        p-value      Covariates
Crude        ...           ...           ...          None
Adjusted     ...           ...           ...          age, sex, ...

Footnote: Adjusted model includes [covariates]. Estimates are [OR/beta/HR/RR] from [model family].
```

## Interpretation Order

Interpret in this order:

1. Effect estimate magnitude
2. Direction of association
3. Width and position of 95% CI
4. p-value last
5. Change from crude to adjusted

## Useful Language

Use:

- "After adjustment for ..., the association was ..."
- "The estimate changed from ... to ..."
- "This suggests that part of the crude association may be explained by ..."
- "This remains an adjusted association, not proof of causality."

Avoid:

- "caused"
- "independently caused"
- "proved"
- "eliminated confounding"
- "treatment effect" unless the design supports that language

## Notes File

`confounding_adjustment_notes.md` should include:

- The crude model formula
- The adjusted model formula
- Covariates included
- Covariates excluded, if any
- Whether covariates were confirmed or assumed
- Any model stability warnings
- A plain-language interpretation template
