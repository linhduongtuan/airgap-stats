# DR Workflow - Stage A: pattern extraction
#
# Runs LOCALLY on the real dataset. Requires: pandas, numpy (stdlib only otherwise).
#
# Purpose:
# Describe the STRUCTURE of a dataset (variable names, types, categorical
# levels, missingness) so an AI agent can later write analysis and synthesis
# code without ever seeing the real data.
#
# Privacy design:
# - This script uploads nothing. It only writes a local CSV file.
# - The pattern file contains NO row-level values, NO row counts,
#   NO means/medians/min/max, NO summary statistics of any kind.
# - Categorical level labels ARE included, because generated analysis code
#   needs exact labels (e.g. factor levels) to run on the real data.
#   Rare levels are masked as "Other" so uncommon (potentially identifying)
#   categories never appear in the pattern file.
# - REVIEW dataset_pattern.csv YOURSELF before sharing it with any AI.
#   If any level label is sensitive, edit or remove it first.

import os
import sys
import pandas as pd
import numpy as np


def extract_pattern(
    data,
    output_csv="dataset_pattern.csv",
    max_levels=15,
    min_level_count=5,
    id_unique_ratio=0.9,
):
    if not isinstance(data, pd.DataFrame):
        raise TypeError("`data` must be a pandas DataFrame.")
    if len(data) == 0:
        raise ValueError("`data` has 0 rows.")
    if any(c == "" for c in data.columns):
        raise ValueError("All columns must have non-empty names.")

    rows = []
    for nm in data.columns:
        x = data[nm]
        miss_pct = round(100 * x.isna().mean(), 1)
        xs = x.dropna()
        n_distinct = int(xs.nunique())
        col_type = "unsupported"
        levels_str = ""
        note = ""

        if pd.api.types.is_datetime64_any_dtype(x):
            col_type = "date"

        elif pd.api.types.is_bool_dtype(x):
            col_type = "binary"
            levels_str = "TRUE|FALSE"

        elif pd.api.types.is_numeric_dtype(x):
            unique_vals = set(xs.unique())
            if n_distinct <= 2 and unique_vals.issubset({0, 1, 0.0, 1.0}):
                col_type = "binary"
                levels_str = "0|1"
            elif len(xs) > 0 and (xs == xs.round()).all() and n_distinct <= 10:
                col_type = "integer_scale"
                levels_str = "|".join(str(int(v)) for v in sorted(xs.unique()))
                note = "small set of integer values; possibly a Likert/score item"
            elif len(xs) > 0 and (xs == xs.round()).all():
                col_type = "integer"
            else:
                col_type = "numeric"

        elif (
            pd.api.types.is_string_dtype(x)
            or pd.api.types.is_object_dtype(x)
            or isinstance(x.dtype, pd.CategoricalDtype)
        ):
            ch = xs.astype(str)
            if len(ch) > 0 and n_distinct / len(ch) >= id_unique_ratio:
                col_type = "id_like"
                note = "high-cardinality; treated as identifier; levels not exported"
            else:
                counts = ch.value_counts()
                keep = counts[counts >= min_level_count].index.tolist()
                keep = keep[:max_levels]
                if len(keep) < len(counts):
                    levels_str = "|".join(keep + ["Other"])
                    note = "rare levels masked as Other"
                else:
                    levels_str = "|".join(keep)
                col_type = (
                    "binary"
                    if (len(keep) <= 2 and len(keep) == len(counts))
                    else "categorical"
                )
        else:
            note = "unsupported column class; excluded from synthesis"

        # n_distinct is exported only where it is a count of categories.
        # For id_like it would equal the real row count, and for continuous
        # variables it would bound the real n - both must stay unknown.
        n_distinct_out = (
            n_distinct
            if col_type in ("binary", "categorical", "integer_scale")
            else None
        )

        rows.append(
            {
                "variable": nm,
                "type": col_type,
                "levels": levels_str,
                "n_distinct": n_distinct_out,
                "missing_pct": miss_pct,
                "note": note,
            }
        )

    pattern = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(os.path.abspath(output_csv)), exist_ok=True)
    pattern.to_csv(output_csv, index=False, encoding="utf-8")

    print(f"\n=== dataset_pattern written to: {os.path.abspath(output_csv)} ===\n")
    print(pattern.to_string(index=False))
    print("\n--- REVIEW BEFORE SHARING WITH ANY AI ---")
    print("1. No row counts, no statistics, no raw values are in this file.")
    print("2. Check every entry in the `levels` column. If a label is sensitive")
    print("   (rare disease, small clinic name, job title...), edit or remove it.")
    print("3. Only after your review, give dataset_pattern.csv to the agent.\n")

    return pattern


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python pattern_extract.py <input.csv> <output_pattern.csv>")
        sys.exit(1)
    df = pd.read_csv(sys.argv[1])
    extract_pattern(df, output_csv=sys.argv[2])
