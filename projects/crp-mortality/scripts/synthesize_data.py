# DR Workflow - Stage B/C: synthetic dataset generation
#
# Runs LOCALLY. Requires: pandas, numpy.
#
# Purpose:
# Generate a fully synthetic dataset from a reviewed dataset_pattern.csv.
# The synthetic dataset exists only so that AI-generated analysis code can be
# tested for "does it run", then re-run unchanged on the real data locally.
#
# Privacy design:
# - Every value is freshly generated. No real row is ever copied.
# - Sample size `n` is chosen by you and is unrelated to the real n.
# - If `data` (the real DataFrame) is supplied, numeric ranges are read from it
#   AT RUNTIME, LOCALLY, only to make simulated numbers plausible. Those
#   ranges are never written into any shared file. If `data` is None,
#   generic default ranges are used instead.
# - Columns are simulated independently: no real correlation structure is
#   reproduced, so results computed on synthetic data are meaningless by
#   design. Only "the code runs" matters here.

import os
import sys
from typing import Any
import numpy as np
import pandas as pd
from datetime import date, timedelta


def _get_levels(s: object) -> list[str]:
    if pd.isna(s) or s == "":  # type: ignore[arg-type]
        return []
    return str(s).split("|")


def _gen_binary(levs: list[str], n: int, rng: np.random.Generator) -> list[Any]:
    vals = levs if levs else ["0", "1"]
    picked = rng.choice(vals, size=n, replace=True)
    try:
        return [int(float(x)) if float(x) == int(float(x)) else float(x) for x in picked]
    except (ValueError, TypeError):
        return list(picked)


def _gen_date(
    nm: str, n: int, rng: np.random.Generator, data: pd.DataFrame | None
) -> list[str]:
    lo_d, hi_d = date(2020, 1, 1), date(2024, 12, 31)
    if data is not None and nm in data.columns:
        try:
            dcol = pd.to_datetime(data[nm], errors="coerce").dropna()
            if len(dcol) > 0:
                lo_d, hi_d = dcol.min().date(), dcol.max().date()
        except Exception:
            pass
    span = (hi_d - lo_d).days
    offsets = rng.integers(0, max(span, 1) + 1, size=n)
    return [(lo_d + timedelta(days=int(d))).isoformat() for d in offsets]


def _inject_missing(
    v: list[Any], miss_pct: object, col_type: str, n: int, rng: np.random.Generator
) -> list[Any]:
    if pd.isna(miss_pct) or float(miss_pct) <= 0 or col_type == "id_like":  # type: ignore[arg-type]
        return v
    n_miss = min(n - 1, round(n * float(miss_pct) / 100))  # type: ignore[arg-type]
    if n_miss <= 0:
        return v
    result: list[Any] = list(v)
    for i in rng.choice(n, size=n_miss, replace=False):
        result[int(i)] = None
    return result


def _gen_column(
    col_type: str,
    levs: list[str],
    nm: str,
    n: int,
    rng: np.random.Generator,
    data: pd.DataFrame | None,
) -> list[Any] | None:
    """Return generated values for one column, or None to skip unsupported types."""
    if col_type == "id_like":
        return [f"id_{i+1}" for i in range(n)]

    if col_type == "binary":
        return _gen_binary(levs, n, rng)

    if col_type == "categorical":
        if not levs:
            raise ValueError(f"Categorical variable without levels: {nm}")
        return list(rng.choice(levs, size=n, replace=True))

    if col_type == "integer_scale":
        try:
            int_vals = [int(x) for x in levs]
        except ValueError:
            raise ValueError(f"integer_scale levels must be numeric for: {nm}")
        return list(rng.choice(int_vals, size=n, replace=True))

    if col_type == "integer":
        lo, hi = _local_range(data, nm, 0, 100)
        lo_i, hi_i = int(round(lo)), int(round(hi))
        return [lo_i] * n if lo_i == hi_i else list(rng.integers(lo_i, hi_i + 1, size=n))

    if col_type == "numeric":
        lo, hi = _local_range(data, nm, 0.0, 100.0)
        return list(np.round(rng.uniform(lo, hi, size=n), 2))

    if col_type == "date":
        return _gen_date(nm, n, rng, data)

    return None  # unsupported — caller skips this column


def _local_range(
    data: pd.DataFrame | None, nm: str, default_lo: float, default_hi: float
) -> tuple[float, float]:
    if data is not None and nm in data.columns and pd.api.types.is_numeric_dtype(data[nm]):
        col = data[nm].dropna()
        if len(col) > 0:
            return float(col.min()), float(col.max())
    return default_lo, default_hi


def synthesize_data(
    pattern_csv="dataset_pattern.csv",
    data=None,
    output_csv="synthetic_dataset.csv",
    n=200,
    seed=2026,
):
    if not os.path.exists(pattern_csv):
        raise FileNotFoundError(f"Pattern file not found: {pattern_csv}")
    if not isinstance(n, int) or n < 10:
        raise ValueError("`n` must be an integer >= 10.")

    pat = pd.read_csv(pattern_csv, encoding="utf-8")
    needed = {"variable", "type", "levels", "missing_pct"}
    if not needed.issubset(pat.columns):
        raise ValueError(f"Pattern file must contain columns: {', '.join(needed)}")

    rng = np.random.default_rng(seed)

    out: dict[str, list[Any]] = {}
    for _, row in pat.iterrows():
        nm       = str(row["variable"])
        col_type = str(row["type"])
        levs     = _get_levels(row["levels"])

        v = _gen_column(col_type, levs, nm, n, rng, data)
        if v is None:
            continue
        out[nm] = _inject_missing(v, row["missing_pct"], col_type, n, rng)

    synthetic = pd.DataFrame(out)
    os.makedirs(os.path.dirname(os.path.abspath(output_csv)), exist_ok=True)
    synthetic.to_csv(output_csv, index=False, encoding="utf-8")

    print(f"\n=== synthetic dataset written to: {os.path.abspath(output_csv)} ===")
    print(f"Rows: {len(synthetic)} | Columns: {len(synthetic.columns)}")
    print("All values are simulated. No real row was copied.")
    print("This file is safe to share with the AI agent (levels come from the")
    print("pattern file you already reviewed).\n")

    return synthetic


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python synthesize_data.py <pattern.csv> <output_synthetic.csv> [n] [seed]")
        sys.exit(1)
    _n = int(sys.argv[3]) if len(sys.argv) > 3 else 200
    _seed = int(sys.argv[4]) if len(sys.argv) > 4 else 2026
    synthesize_data(pattern_csv=sys.argv[1], output_csv=sys.argv[2], n=_n, seed=_seed)
