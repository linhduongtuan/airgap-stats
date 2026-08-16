---
name: dr-00-privacy-gate
description: "Stages A-C of the DR workflow: set up local pattern extraction from the real dataset, walk the user through reviewing dataset_pattern.csv, and generate the local synthesis script that creates the synthetic dataset. Use when a DR project has no reviewed dataset_pattern.csv or no synthetic_dataset.csv yet, or when the user asks how to prepare data for AI-assisted analysis without uploading real data."
---

# DR Stage A-C: Privacy Gate

Use this skill at the start of every DR project. It produces the local scripts (R by default, or the Python mirror) that let the user extract a structural pattern from the real dataset and generate a fully synthetic dataset — without the agent ever seeing real data. An optional additional script (Stage B2, available in both languages) can preserve the real data's pairwise correlation structure in a second, still-reviewed synthetic file.

**The real dataset lives OUTSIDE this repo**, wherever the user keeps it on their machine. You never see it, never ask where it is, and never write its path or filename into any file. Whenever a script needs the real data, the user selects it interactively in RStudio with `file.choose()` — the path exists only inside their RStudio session.

## Stage A: Pattern Extraction

1. Copy `r-scripts/pattern_extract.R` into the project's `scripts/` folder — and, when the pack's Python mirror is in use, `py-scripts/pattern_extract.py` as `scripts/pattern_extract.py` instead (same contract, same exported columns; pick one language per project, not both).
2. Give the user these exact commands to run in RStudio (working directory = project folder, set via Session > Set Working Directory > Choose Directory):

```r
source("scripts/pattern_extract.R")
original <- read.csv(file.choose())   # a file-picker window opens: select your real dataset
extract_pattern(original, output_csv = "pattern/dataset_pattern.csv")
```

Python mirror (run locally, not in this chat):

```python
import pandas as pd
from pattern_extract import extract_pattern
original = pd.read_csv("/path/to/your/real_data.csv")  # never share this path with the agent
extract_pattern(original, output_csv="pattern/dataset_pattern.csv")
```

3. Tell the user what the script does and does not export: variable names, types, categorical levels (rare levels masked as "Other"), missing percentage — and nothing else. No row counts, no statistics, no raw values, no file path.

## Review Gate (mandatory)

Before you read `pattern/dataset_pattern.csv`:

1. Ask the user to open the file and check every entry in the `levels` column.
2. Ask explicitly: "Have you reviewed dataset_pattern.csv and confirmed that no level label is sensitive or identifying?"
3. Only after an explicit yes, read the pattern file, print its content back in a compact table, and record `pattern_reviewed_by_user: true` in the state file.

If the user finds a sensitive label, tell them to edit or delete that label in the CSV (and later map it manually when running analysis code on real data), then review again.

## Stage B: Synthesis Script

After the review gate passes:

1. Copy `r-scripts/synthesize_data.R` into `scripts/` — or, when the pack's Python mirror is in use, `py-scripts/synthesize_data.py` as `scripts/synthesize_data.py`.
2. Give the user these commands:

```r
source("scripts/synthesize_data.R")
original <- read.csv(file.choose())   # select the real dataset again
synthesize_data(
  pattern_csv = "pattern/dataset_pattern.csv",
  data = original,
  output_csv = "data_synthetic/synthetic_dataset.csv",
  n = 200,
  seed = 2026
)
```

Python mirror:

```python
import pandas as pd
from synthesize_data import synthesize_data
original = pd.read_csv("/path/to/your/real_data.csv")
synthesize_data(
    pattern_csv="pattern/dataset_pattern.csv",
    data=original,
    output_csv="data_synthetic/synthetic_dataset.csv",
    n=200,
    seed=2026,
)
```

Explain: passing `data = original` only lets the script pick plausible numeric ranges locally at runtime; ranges are never written to any shared file. `n` is chosen freely and unrelated to the real sample size. For a SEM project, suggest `n = 300` so lavaan (or, in the Python mirror, semopy) is comfortable.

If the pattern file describes variables the generic function cannot handle, write a project-specific synthesis script instead, in the same language — base R only for `.R`, standard library + pandas/numpy/scipy only for `.py` — same privacy rules either way.

Every column in `data_synthetic/synthetic_dataset.csv` is generated **independently** of every other column, by design — there is no real correlation structure to leak. The cost of that safety margin is that Stage D scripts can only prove "the code runs" on this file, never "the model actually converges under realistic correlation" (a logistic fit near-separated or an ordinal CFA that never converges on independent columns is expected, not a bug). If that limitation matters for what you're testing, see Stage B2 below.

## Stage B2 (optional): Correlated Synthesis

Only offer this after Stage B's independent synthetic dataset exists and has been reviewed. It is never a substitute for Stage B — it is an additional, still-local, still-reviewed file for exercising Stage D code against something less trivially independent before the real run.

Available in both languages — `py-scripts/synthesize_data_correlated.py` (Python) and `r-scripts/synthesize_correlated.R` (R, base R only, no packages). It approximates the real dataset's *pairwise correlation structure* via a Gaussian copula (Spearman rank correlation → nearest positive-semi-definite correlation matrix → inverse-transform through each variable's own empirical marginal) while still generating every row from scratch — no real row is ever copied or read into any output. Numeric/integer/ordinal/binary columns are correlated this way; everything else (free-text categoricals, IDs, dates) falls back to Stage B's independent generation.

1. Copy `py-scripts/synthesize_data_correlated.py` into `scripts/synthesize_data_correlated.py`, **or**, for the R mirror, copy both `r-scripts/synthesize_correlated.R` into `scripts/synthesize_correlated.R` (the library) and its accompanying wrapper into `scripts/synthesize_data_correlated.R` (two files, not one — R has no package/import system, so unlike the Python mirror the library and the project wrapper can't share one filename; the wrapper `source()`s the library, both need to be present). Ready-made templates for every combination exist at `projects/crp-mortality/scripts/` — all are fully generic, copy verbatim into any project.
2. Give the user these commands:

```python
import pandas as pd
from synthesize_data_correlated import synthesize_data_correlated
original = pd.read_csv("/path/to/your/real_data.csv")   # never share this path with the agent
synthesize_data_correlated(
    pattern_csv="pattern/dataset_pattern.csv",
    data=original,
    output_csv="data_synthetic/synthetic_dataset_correlated.csv",
    n=200,
    seed=2026,
)
```

R mirror:

```r
source("scripts/synthesize_correlated.R")
original <- read.csv(file.choose())   # a file-picker window opens: select your real dataset
synthesize_correlated(
  pattern_csv = "pattern/dataset_pattern.csv",
  data = original,
  output_csv = "data_synthetic/synthetic_dataset_correlated.csv",
  n = 200,
  seed = 2026
)
```

3. Same review gate as Stage B's file: the user opens `synthetic_dataset_correlated.csv` and confirms nothing in it looks identifying before it is used or discussed. Tell them explicitly that a correlated synthetic file reveals *more* about the real data's structure than the independent one (e.g. "these two variables move together") even though no individual value is real — that is the deliberate trade this stage makes, which is why it stays opt-in and reviewed rather than the default.
4. Point Stage D scripts at `data_synthetic/synthetic_dataset_correlated.csv` only for a convergence/sanity check, then point them back at the default independent file (or real data) for anything that gets reported. Every Stage D script's header should say which synthesis mode it was last verified against — if you add or regenerate a script, add that note.

## Stage C: Synthetic Dataset

When the user confirms `data_synthetic/synthetic_dataset.csv` exists, read it, confirm the columns match the pattern file, and update the state file. Then hand back to `dr-workflow-orchestrator`, which routes to `dr-01-understand-dataset`. (Whether `synthetic_dataset_correlated.csv` from Stage B2 also exists is worth noting in the state file, but it never gates progress — Stage B2 is optional.)

See `references/pattern-file-spec.md` for the pattern file format.

## Boundaries

Never ask for the real dataset, its file path, its folder, or its filename; the user selects it with `file.choose()` and that knowledge stays in RStudio.
Never tell the user to copy real data into the repo. If you notice real data inside the repo (e.g. a `data_real/` folder someone created), warn the user to move it back out; never read it.
Never write real statistics of any kind into pattern or plan files.
Generated scripts must never print the real data path or filename to the console.
Never skip the review gate, even if the user seems in a hurry.
Do not clean, recode, or wrangle data in this skill; it prepares structure only.
Base R only in generated R scripts (standard library + pandas/numpy/scipy only for the Python mirror); no package installation.
Everything above applies equally to Stage B2: the real dataset is read locally at runtime only, never written to any output file, and the review gate is not optional just because the file is "more synthetic."

## Teaching Line

The AI only ever knows what you deliberately typed or reviewed. The real data — and even its location — never leaves your machine.
