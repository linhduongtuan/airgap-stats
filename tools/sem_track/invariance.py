"""Measurement invariance across groups (e.g. gender, education) -- Phase 3's
remaining item (roadmap priority: Low, effort: High). Before comparing
latent means or structural paths across groups, the measurement model
itself has to mean the same thing in each group; skipping this check and
comparing groups anyway is a common and citable methodological error.

APPROACH -- per-group fits + bootstrap loading comparison, not the
textbook multi-group chi-square difference test:
The standard approach (configural -> metric -> scalar, each tested via a
chi-square difference against the previous, less-constrained model) needs
genuine multi-group SEM: one joint model where loadings are free per group
at the configural step and then constrained equal at the metric step.
semopy has no such feature -- its `groups=` fit parameter only mean-centers
each group's data before pooling everything into a single fit (see its own
docstring: "List of group names to center across"); it does not estimate
or constrain per-group parameters. That's a genuine library limitation,
not a bug to patch around.

The approach used here instead:
1. **Configural check**: fit the measurement model separately in each
   group (each fit uses `estimator.fit_measurement_model`, which *is*
   robust for a single group). Report each group's fit indices --if the
   same factor structure doesn't fit reasonably well in every group,
   nothing past this point is meaningful.
2. **Metric invariance, per item**: bootstrap each group's loadings
   separately, then test whether each item's loading differs between
   groups (CI on the bootstrap difference excluding 0 => that item is
   flagged non-invariant). This is more granular than the omnibus
   metric-vs-configural test -- it names *which* item breaks invariance,
   which is what you need to act on anyway (drop the item, or report
   partial invariance) and is the direction the partial-invariance/
   alignment literature has moved regardless (Muthen & Asparouhov 2014).

Scalar invariance (item intercept/threshold equality) is not implemented
here -- extracting per-group ordinal thresholds from semopy and comparing
them would extend this same pattern, but was out of scope for this pass.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .estimator import FitResult, fit_measurement_model


@dataclass
class ConfiguralResult:
    fits: dict[str, FitResult]  # group value (as str) -> FitResult

    def summary(self) -> pd.DataFrame:
        rows = []
        for group, fit in self.fits.items():
            rows.append({
                "group": group, "converged": fit.converged,
                "cfi": fit.fit_indices["cfi"], "tli": fit.fit_indices["tli"],
                "rmsea": fit.fit_indices["rmsea"],
            })
        return pd.DataFrame(rows)


def configural_check(
    data: pd.DataFrame,
    constructs: dict[str, list[str]],
    group_col: str,
    estimator: str = "DWLS",
) -> ConfiguralResult:
    """Fit the measurement model separately in every level of `group_col`.
    Configural invariance holds qualitatively if every group's fit indices
    look reasonable (conventionally CFI > 0.90-0.95, RMSEA < 0.08) -- there
    is no single test statistic for this step in the per-group-fit
    approach, only a fit-index comparison across groups.
    """
    fits: dict[str, FitResult] = {}
    for g in sorted(data[group_col].dropna().unique()):
        sub = data[data[group_col] == g]
        fits[str(g)] = fit_measurement_model(sub, constructs, estimator=estimator)
    return ConfiguralResult(fits=fits)


@dataclass
class ItemInvarianceResult:
    construct: str
    item: str
    group_a: str
    group_b: str
    loading_a: float
    loading_b: float
    difference: float
    ci_low: float
    ci_high: float
    flagged_noninvariant: bool
    n_boot: int
    n_failed: int


def metric_invariance_bootstrap(
    data: pd.DataFrame,
    constructs: dict[str, list[str]],
    group_col: str,
    estimator: str = "DWLS",
    n_boot: int = 30,
    seed: int = 2026,
    alpha: float = 0.05,
) -> pd.DataFrame:
    """Per-item bootstrap test of loading equality between exactly two
    groups. Refits each group's CFA on a within-group resample, records
    each item's standardized loading, and forms the percentile bootstrap
    CI of (loading_group_a - loading_group_b). An item is flagged
    `flagged_noninvariant` when that CI excludes 0.

    Only supports exactly 2 groups (the common case: e.g. gender). For
    >2 groups, run this pairwise.
    """
    groups = sorted(data[group_col].dropna().unique())
    if len(groups) != 2:
        raise ValueError(f"metric_invariance_bootstrap needs exactly 2 groups, got {len(groups)}: {groups}")
    ga, gb = str(groups[0]), str(groups[1])

    rng = np.random.default_rng(seed)
    sub_a = data[data[group_col] == groups[0]].reset_index(drop=True)
    sub_b = data[data[group_col] == groups[1]].reset_index(drop=True)
    n_a, n_b = len(sub_a), len(sub_b)

    def _loadings(d: pd.DataFrame) -> pd.Series:
        """item -> standardized loading, indexed 'construct::item' to stay unique across constructs."""
        fit = fit_measurement_model(d, constructs, estimator=estimator)
        out = {}
        for construct, items in constructs.items():
            construct_loadings = fit.loadings[
                (fit.loadings["rval"] == construct) & (fit.loadings["lval"].isin(items))
            ]
            for _, row in construct_loadings.iterrows():
                out[f"{construct}::{row['lval']}"] = float(row["Est. Std"])
        return pd.Series(out)

    point_a = _loadings(sub_a)
    point_b = _loadings(sub_b)
    common_keys = [k for k in point_a.index if k in point_b.index]

    boot_diffs: dict[str, list[float]] = {k: [] for k in common_keys}
    n_failed = 0
    for _ in range(n_boot):
        boot_a = sub_a.iloc[rng.integers(0, n_a, size=n_a)].reset_index(drop=True)
        boot_b = sub_b.iloc[rng.integers(0, n_b, size=n_b)].reset_index(drop=True)
        try:
            la = _loadings(boot_a)
            lb = _loadings(boot_b)
        except Exception:
            n_failed += 1
            continue
        for k in common_keys:
            if k in la.index and k in lb.index and la[k] == la[k] and lb[k] == lb[k]:
                boot_diffs[k].append(float(la[k] - lb[k]))

    rows = []
    for k in common_keys:
        construct, item = k.split("::", 1)
        diffs = boot_diffs[k]
        diff_point = float(point_a[k] - point_b[k])
        if diffs:
            lo = float(np.percentile(diffs, 100 * alpha / 2))
            hi = float(np.percentile(diffs, 100 * (1 - alpha / 2)))
        else:
            lo = hi = float("nan")
        flagged = (lo == lo) and not (lo <= 0 <= hi)
        rows.append(ItemInvarianceResult(
            construct=construct, item=item, group_a=ga, group_b=gb,
            loading_a=round(float(point_a[k]), 4), loading_b=round(float(point_b[k]), 4),
            difference=round(diff_point, 4), ci_low=round(lo, 4) if lo == lo else float("nan"),
            ci_high=round(hi, 4) if hi == hi else float("nan"),
            flagged_noninvariant=flagged, n_boot=n_boot, n_failed=n_failed,
        ))

    return pd.DataFrame([vars(r) for r in rows])
