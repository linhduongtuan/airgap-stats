# DR Workflow - Stage B2 (opt-in): correlated synthetic dataset generation
#
# Runs LOCALLY. Requires: pandas, numpy, scipy.
#
# WHY THIS SCRIPT EXISTS
# scripts/synthesize_data.py generates every column *independently* -- by
# design, so no real relationship between variables can ever leak into the
# synthetic file. The cost: an AI agent's code can only be checked for
# "does it run" on that file, never "does the model actually converge under
# realistic correlation" -- which is exactly why every SEM/logistic script
# in this pack documents that non-convergence or degenerate fit indices on
# the default synthetic data are *expected*, not a bug.
#
# This script trades a little of that safety margin for a much more useful
# test bed: it preserves the *approximate pairwise correlation structure*
# of the real data (via a Gaussian copula) while still generating every
# row from scratch -- no real row is copied, ever. Use it when you want to
# verify a regression/SEM script actually converges before touching real
# data, not just that it runs.
#
# PRIVACY DESIGN (same contract as synthesize_data.py, extended)
# - Every value is freshly generated. No real row is ever copied (see
#   tests/test_synthesize_correlated.py for an explicit check of this).
# - `data` (the real DataFrame) is REQUIRED here -- unlike the independent
#   synthesizer, there is no correlation structure to preserve without it.
# - The correlation matrix, empirical quantiles, and level proportions used
#   to parameterize generation are computed LOCALLY, AT RUNTIME, and are
#   NEVER written to any file. Only the fabricated synthetic rows are
#   written -- identical in kind to how synthesize_data.py reads numeric
#   ranges locally without persisting them, just extended to a full
#   correlation matrix instead of per-column min/max.
# - REVIEW the synthetic output yourself before sharing it, same as the
#   pattern file. A correlated synthetic dataset reveals *more* about your
#   real data's structure than the independent one (e.g. "these two
#   variables move together") even though no individual value is real --
#   that is the deliberate trade this script makes. Prefer
#   synthesize_data.py's default independent synthesis unless you
#   specifically need the AI agent to validate model convergence.

import os
import sys
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import norm

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from synthesize_data import _gen_column, _get_levels, _inject_missing  # reuse for uncorrelated columns

_CORRELATABLE_TYPES = {"numeric", "integer", "integer_scale", "binary"}


def _nearest_psd_correlation(r: np.ndarray, eps: float = 1e-8) -> np.ndarray:
    """Clip negative eigenvalues and renormalize to unit diagonal -- a
    small, standard fix for a correlation matrix that drifted slightly off
    positive-semi-definite due to pairwise-complete-observations deletion.
    """
    eigvals, eigvecs = np.linalg.eigh(r)
    eigvals_clipped = np.clip(eigvals, eps, None)
    r_psd = eigvecs @ np.diag(eigvals_clipped) @ eigvecs.T
    d = np.sqrt(np.diag(r_psd))
    r_psd = r_psd / np.outer(d, d)
    np.fill_diagonal(r_psd, 1.0)
    return r_psd


def _numeric_proxy(col: pd.Series) -> pd.Series:
    """A numeric, rank-correlatable version of `col`. Already-numeric
    columns pass through unchanged; a binary/ordinal column stored as
    strings (e.g. "M"/"F", "Nuữ"/"Nam") is rank-encoded by sorted
    label order so Spearman correlation (which only needs ranks) is still
    well-defined. This encoding is derived from the real data locally and
    is never written anywhere, same as everything else in this module.
    """
    if pd.api.types.is_numeric_dtype(col):
        return col
    codes, _uniques = pd.factorize(col, sort=True)
    return pd.Series(codes, index=col.index).replace(-1, np.nan)


def _local_correlation_matrix(data: pd.DataFrame, cols: list[str]) -> np.ndarray:
    """Spearman rank correlation among `cols`, computed locally, projected
    to the nearest valid (positive-semi-definite) correlation matrix.
    Never written to any file by this module -- callers must not persist it.
    """
    numeric_df = pd.DataFrame({c: _numeric_proxy(data[c]) for c in cols})
    r = numeric_df.corr(method="spearman").to_numpy()
    r = np.nan_to_num(r, nan=0.0)
    np.fill_diagonal(r, 1.0)
    return _nearest_psd_correlation(r)


def _copula_uniforms(n: int, corr: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """n x p matrix of Gaussian-copula uniform(0,1) variates with rank
    correlation approximately `corr`."""
    p = corr.shape[0]
    try:
        L = np.linalg.cholesky(corr)
    except np.linalg.LinAlgError:
        # Should not happen after _nearest_psd_correlation, but fall back
        # to an eigen-decomposition square root just in case.
        eigvals, eigvecs = np.linalg.eigh(corr)
        L = eigvecs @ np.diag(np.sqrt(np.clip(eigvals, 0, None)))
    z = rng.standard_normal((n, p)) @ L.T
    return norm.cdf(z)


def _map_uniform_to_marginal(u: np.ndarray, col_type: str, real_col: pd.Series, levs: list[str]) -> list[Any]:
    """Inverse-transform one column of copula uniforms through the
    variable's empirical marginal (computed locally from `real_col`,
    never persisted)."""
    real_col = real_col.dropna()

    if col_type == "numeric":
        return list(np.round(np.quantile(real_col.astype(float), u), 2))

    if col_type == "integer":
        return list(np.round(np.quantile(real_col.astype(float), u)).astype(int))

    if col_type in ("integer_scale", "binary"):
        # Ordinal/binary: map through the LOCAL empirical level
        # proportions (never written to file), via cumulative thresholds --
        # the same idea as an ordinal probit/copula threshold model.
        vals = levs if levs else sorted(real_col.astype(str).unique())
        counts = real_col.astype(str).value_counts()
        probs = np.array([counts.get(str(v), 0) for v in vals], dtype=float)
        if probs.sum() <= 0:
            probs = np.ones(len(vals))
        probs = probs / probs.sum()
        cum = np.cumsum(probs)
        idx = np.searchsorted(cum, u, side="right").clip(0, len(vals) - 1)
        picked = [vals[i] for i in idx]
        if col_type == "binary":
            try:
                return [int(float(x)) if float(x) == int(float(x)) else float(x) for x in picked]
            except (ValueError, TypeError):
                return picked
        try:
            return [int(x) for x in picked]
        except ValueError:
            return picked

    raise ValueError(f"_map_uniform_to_marginal does not support column type: {col_type}")


def synthesize_data_correlated(
    pattern_csv: str = "dataset_pattern.csv",
    data: pd.DataFrame = None,
    output_csv: str = "synthetic_dataset_correlated.csv",
    n: int = 200,
    seed: int = 2026,
) -> pd.DataFrame:
    if data is None:
        raise ValueError(
            "synthesize_data_correlated requires `data` (the real DataFrame, used only "
            "locally at runtime) -- there is no correlation structure to preserve without it. "
            "Use synthesize_data.py's independent synthesizer if you don't have local access "
            "to the real data right now."
        )
    if not os.path.exists(pattern_csv):
        raise FileNotFoundError(f"Pattern file not found: {pattern_csv}")
    if not isinstance(n, int) or n < 10:
        raise ValueError("`n` must be an integer >= 10.")

    pat = pd.read_csv(pattern_csv, encoding="utf-8")
    needed = {"variable", "type", "levels", "missing_pct"}
    if not needed.issubset(pat.columns):
        raise ValueError(f"Pattern file must contain columns: {', '.join(needed)}")

    rng = np.random.default_rng(seed)

    correlatable = [
        str(row["variable"]) for _, row in pat.iterrows()
        if str(row["type"]) in _CORRELATABLE_TYPES and str(row["variable"]) in data.columns
    ]
    correlatable = [c for c in correlatable if data[c].dropna().nunique() > 1]  # a constant column breaks corr()

    out: dict[str, list[Any]] = {}
    actually_correlated: list[str] = []

    if len(correlatable) >= 2:
        actually_correlated = correlatable
        corr = _local_correlation_matrix(data, correlatable)  # local only; never written
        u = _copula_uniforms(n, corr, rng)  # (n, len(correlatable))
        for j, nm in enumerate(correlatable):
            row = pat.loc[pat["variable"] == nm].iloc[0]
            col_type = str(row["type"])
            levs = _get_levels(row["levels"])
            v = _map_uniform_to_marginal(u[:, j], col_type, data[nm], levs)
            out[nm] = _inject_missing(v, row["missing_pct"], col_type, n, rng)
    elif correlatable:
        print(f"Only one correlatable column ({correlatable[0]}); nothing to correlate it with. "
              "Falling back to independent generation for it.")

    # Every other column (categorical with >2 levels, id_like, date,
    # unsupported, or a lone correlatable column) -- same independent
    # generation as synthesize_data.py.
    for _, prow in pat.iterrows():
        nm = str(prow["variable"])
        if nm in out:
            continue
        col_type = str(prow["type"])
        levs = _get_levels(prow["levels"])
        v = _gen_column(col_type, levs, nm, n, rng, data)
        if v is None:
            continue
        out[nm] = _inject_missing(v, prow["missing_pct"], col_type, n, rng)

    synthetic = pd.DataFrame(out)
    os.makedirs(os.path.dirname(os.path.abspath(output_csv)) or ".", exist_ok=True)
    synthetic.to_csv(output_csv, index=False, encoding="utf-8")

    print(f"\n=== correlated synthetic dataset written to: {os.path.abspath(output_csv)} ===")
    print(f"Rows: {len(synthetic)} | Columns: {len(synthetic.columns)}")
    print(f"Correlation-preserving columns ({len(actually_correlated)}): "
          f"{', '.join(actually_correlated) if actually_correlated else 'none'}")
    print("All values are simulated. No real row was copied.")
    print(
        "This file preserves approximate pairwise correlations from your real data -- "
        "review it yourself before sharing, the same as the pattern file, and prefer "
        "the independent synthesizer (synthesize_data.py) unless you specifically need "
        "convergence-testing fidelity.\n"
    )

    return synthetic


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python synthesize_data_correlated.py <pattern.csv> <real_data.csv> <output_synthetic.csv> [n] [seed]")
        print("Note: <real_data.csv> is read locally by this script only; never written anywhere.")
        sys.exit(1)
    _real = pd.read_csv(sys.argv[2], encoding="utf-8")
    _n = int(sys.argv[4]) if len(sys.argv) > 4 else 200
    _seed = int(sys.argv[5]) if len(sys.argv) > 5 else 2026
    synthesize_data_correlated(pattern_csv=sys.argv[1], data=_real, output_csv=sys.argv[3], n=_n, seed=_seed)
