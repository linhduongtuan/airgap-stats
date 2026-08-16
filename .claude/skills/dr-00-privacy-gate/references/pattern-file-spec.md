# dataset_pattern.csv Specification

The pattern file is a plain CSV with exactly these columns:

| Column | Meaning |
|---|---|
| `variable` | Exact column name in the real dataset |
| `type` | One of: `numeric`, `integer`, `integer_scale`, `binary`, `categorical`, `id_like`, `date`, `unsupported` |
| `levels` | Pipe-separated exact level labels for `binary`/`categorical`, or the observed integer values for `integer_scale`. Empty otherwise. Rare levels appear as `Other`. |
| `n_distinct` | Count of categories — filled only for `binary`/`categorical`/`integer_scale`. Empty for all other types, because for id/continuous variables it would reveal or bound the real row count. |
| `missing_pct` | Percent missing, rounded to 1 decimal |
| `note` | Free-text flags written by the extractor (e.g. "rare levels masked as Other") |

## Type meanings for code generation

- `numeric` / `integer`: continuous or count variable; safe for means, regression.
- `integer_scale`: small set of integer values (often Likert items or scores); `levels` lists the exact response values.
- `binary`: two levels; `levels` gives the exact coding (`0|1`, `Nam|Nữ`, ...). Generated code must use these exact labels.
- `categorical`: use the exact labels in `levels` for factor handling; remember `Other` may exist in real data after masking.
- `id_like`: identifier; exclude from all analysis.
- `date`: date variable; exclude from Table 1 unless converted to intervals.
- `unsupported`: excluded from synthesis; do not use in analysis code.

## What must never appear in this file

- Row counts of the real dataset
- Means, medians, minimums, maximums, SDs, or any other statistic
- Raw values from any row (level labels of categorical variables are the single deliberate exception, and they pass through the user review gate)

If an agent receives a pattern file containing forbidden content, it must warn the user and ask for a regenerated file instead of using it.
