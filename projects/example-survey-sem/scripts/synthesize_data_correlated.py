# DR Workflow - Stage B2 (opt-in): correlated synthetic dataset generation
# (Phase 4 of the statistical-methods roadmap)
#
# Runs LOCALLY. Requires: pandas, numpy, scipy.
#
# WHY THIS SCRIPT EXISTS
# scripts/synthesize_data.py (Stage B, the default) generates every column
# *independently* -- deliberately, so no real relationship between
# variables can leak into the synthetic file. The cost of that safety
# margin: an AI agent's code can only be checked for "does it run" on that
# file, never "does the model actually converge under realistic
# correlation" -- which is exactly why every diagnostic/bootstrap section
# in scripts/infer.py documents that degenerate results on the default
# synthetic data are *expected*, not a bug (there's no real signal for a
# model to find in independently-generated columns).
#
# This script trades a little of that safety margin for a much more useful
# test bed: it preserves the *approximate pairwise correlation structure*
# of your real data (via a Gaussian copula) while still generating every
# row from scratch. See py-scripts/synthesize_data_correlated.py's
# docstring for the full privacy design (identical contract to
# synthesize_data.py, extended from per-column ranges to a correlation
# matrix -- all computed locally, at runtime, never written to any file).
#
# REVIEW the output yourself before sharing it, same as the pattern file --
# more so, actually: a correlated synthetic dataset reveals more about your
# real data's structure than the independent one. Prefer
# data_synthetic/synthetic_dataset.csv (Stage B) for everyday verification;
# use this only when you specifically need to check that a model converges.

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "py-scripts"))
from synthesize_data_correlated import synthesize_data_correlated

# === USER SETTINGS ==========================================================
# Uncomment and run locally with your real data -- this cannot run without it
# (there is no correlation structure to preserve without seeing the real
# pairwise relationships, even transiently):
#
# original = pd.read_csv(file.choose())  # RStudio-style picker isn't a Python
#                                          # builtin; use a real file dialog or
#                                          # hardcode the path to your real CSV:
# original = pd.read_csv("/path/to/your/real_data.csv")
#
# synthesize_data_correlated(
#     pattern_csv="pattern/dataset_pattern.csv",
#     data=original,
#     output_csv="data_synthetic/synthetic_dataset_correlated.csv",
#     n=200,
#     seed=2026,
# )
# ============================================================================

if __name__ == "__main__":
    print(
        "This script needs your real dataset loaded locally as `original` "
        "(see the USER SETTINGS comment block above) -- it does not run "
        "standalone the way scripts/synthesize_data.py does. Edit this file "
        "to point at your real CSV, then run the synthesize_data_correlated(...) "
        "call shown above."
    )
