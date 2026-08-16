# DR Workflow - Stage B2 (opt-in): correlated synthetic dataset generation
# (Phase 4 of the statistical-methods roadmap)
#
# Runs LOCALLY in RStudio. Base R only -- requires r-scripts/synthesize_correlated.R
# to already be copied into scripts/ (this file sources it).
#
# WHY THIS SCRIPT EXISTS
# scripts/synthesize_data.R (Stage B, the default) generates every column
# *independently* -- deliberately, so no real relationship between
# variables can leak into the synthetic file. The cost of that safety
# margin: an AI agent's code can only be checked for "does it run" on that
# file, never "does the model actually converge under realistic
# correlation" -- which is exactly why every diagnostic/bootstrap section
# in scripts/infer.R documents that degenerate results on the default
# synthetic data are *expected*, not a bug (there's no real signal for a
# model to find in independently-generated columns).
#
# This script trades a little of that safety margin for a much more useful
# test bed: it preserves the *approximate pairwise correlation structure*
# of your real data (via a Gaussian copula) while still generating every
# row from scratch. See r-scripts/synthesize_correlated.R's header for the
# full privacy design (identical contract to synthesize_data.R, extended
# from per-column ranges to a correlation matrix -- all computed locally,
# at runtime, never written to any file).
#
# REVIEW the output yourself before sharing it, same as the pattern file --
# more so, actually: a correlated synthetic dataset reveals more about your
# real data's structure than the independent one. Prefer
# data_synthetic/synthetic_dataset.csv (Stage B) for everyday verification;
# use this only when you specifically need to check that a model converges.

source("scripts/synthesize_correlated.R")

# === USER SETTINGS ==========================================================
# Uncomment and run locally with your real data -- this cannot run without it
# (there is no correlation structure to preserve without seeing the real
# pairwise relationships, even transiently):
#
# original <- read.csv(file.choose())   # a file-picker window opens: select your real dataset
#
# synthesize_correlated(
#   pattern_csv = "pattern/dataset_pattern.csv",
#   data = original,
#   output_csv = "data_synthetic/synthetic_dataset_correlated.csv",
#   n = 200,
#   seed = 2026
# )
# ============================================================================

cat(
  "This script needs your real dataset loaded locally as `original` ",
  "(see the USER SETTINGS comment block above) -- it does not run ",
  "standalone the way scripts/synthesize_data.R does. Edit this file ",
  "to point at your real CSV, then run the synthesize_correlated(...) ",
  "call shown above.\n", sep = ""
)
