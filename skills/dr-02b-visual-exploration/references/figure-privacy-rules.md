# Figure Privacy Rules

Why figures need their own rules, and what those rules are.

## Why a figure is not a table

Everything else this workflow sends back to the agent is **aggregate**: Table 1 holds means, SDs and counts; model output holds coefficients, CIs and p-values. Many rows collapse into one number, so no individual is recoverable.

A figure does not collapse anything:

| Figure element | What it actually is |
|---|---|
| One point in a jittered strip | One participant's exact value |
| A boxplot outlier dot | One participant, usually the most extreme and most identifiable |
| A scatter point | One participant on two variables at once — a quasi-identifier pair |
| Heatmap cell | Aggregate (a correlation over all rows) — the safe part |

So a boxplot of 40 patients is closer to publishing 40 rows of the dataset than to publishing a summary table. Rules follow from that.

## The three rules

### 1. Real figures never enter the repo

The repo is a git repository that a learner may push to GitHub. A figure derived from real data sitting in `results_real/` would be real data committed to a public remote — a silent breach of Golden Rule 1 that requires nobody to do anything wrong.

Generated scripts therefore write real-run figures beside the real dataset:

```r
input_csv  <- file.choose()
output_dir <- file.path(dirname(input_csv), "dr_figures")
```

The path is computed at runtime inside the user's RStudio session. It is outside the pack by the same convention that keeps the dataset outside, and the agent never learns it.

Synthetic figures go to `outputs_synthetic/figures/` and are safe to commit.

### 2. Real figures never come back to the agent

Stage E invites the user to paste real output. That invitation covers **text and aggregate numbers only**. A learner who has just produced a beautiful heatmap of their real data will naturally want to paste it — that is the moment to prevent.

The line to teach:

> Aggregate numbers can be pasted. Pictures of raw rows cannot.

If the user offers or attaches a figure made from real data, decline, say briefly why, and offer the alternative: describe what they see in words, or paste the correlation matrix as numbers if they want help interpreting it.

### 3. The agent opens synthetic figures only

Reading a PNG under `outputs_synthetic/figures/` is expected — it is how the agent verifies the figure renders. Never open anything under a `dr_figures/` folder, and never open a user-supplied image of real data, even if the user asks.

## Small-cell guard

Do not draw a box for a group with fewer than 5 observations. Below that threshold a boxplot is both statistically meaningless and individually disclosive: with n = 2, the median, quartiles and whiskers are the two people's values. Warn and skip.

## What `show_individual_points` is and is not

The flag controls jittered points and boxplot outliers. It defaults to `TRUE`.

This is deliberate. The figure never leaves the user's machine, so suppressing outliers protects nobody while discarding information a clinician needs — the extreme values are frequently the clinically interesting ones. The protection in this design is the **channel** (rules 1 and 2), not blurring the picture.

Set it to `FALSE` only when the user intends to show the figure to someone else — in a slide deck, a manuscript, or a supervision meeting. Say that explicitly in the notes file rather than defaulting to a crippled figure.

## Summary

| Artifact | Location | Agent may read | May be committed |
|---|---|---|---|
| Synthetic figure | `outputs_synthetic/figures/` | Yes | Yes |
| Real figure | `<real data folder>/dr_figures/` | Never | Never (outside repo) |
| Real aggregate text | pasted at Stage E | Yes | Yes |
