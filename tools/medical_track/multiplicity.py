"""Benjamini-Hochberg FDR control -- only relevant once a SAP's Section I
(`plans/sap.md`) pre-registers more than one planned comparison. A thin,
tested wrapper around statsmodels' own validated implementation rather than
a hand-rolled re-derivation of a procedure that's easy to get subtly wrong
(the ordering/step-up logic in particular).
"""

from __future__ import annotations

import pandas as pd
from statsmodels.stats.multitest import multipletests


def benjamini_hochberg(p_values: pd.Series, alpha: float = 0.05) -> pd.DataFrame:
    """Benjamini-Hochberg step-up FDR control.

    Returns a DataFrame indexed like `p_values` with the original p-value,
    the BH-adjusted p-value, and a `reject` boolean at the given `alpha`.
    NaN p-values are excluded from the procedure and returned as NaN/False.
    """
    valid = p_values.dropna()
    if valid.empty:
        return pd.DataFrame({
            "p_value": p_values, "p_adjusted": pd.Series(index=p_values.index, dtype=float),
            "reject": pd.Series(False, index=p_values.index),
        })

    reject, p_adj, _, _ = multipletests(valid.to_numpy(), alpha=alpha, method="fdr_bh")

    out = pd.DataFrame({"p_value": p_values})
    out["p_adjusted"] = pd.Series(p_adj, index=valid.index).reindex(p_values.index)
    out["reject"] = pd.Series(reject, index=valid.index).reindex(p_values.index).fillna(False)
    return out
