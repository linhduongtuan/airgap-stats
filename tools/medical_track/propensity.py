"""Propensity-score sensitivity analysis: matching (PSM), inverse-probability
weighting (IPTW), and the E-value for unmeasured confounding.

A companion to the regression-adjusted estimate, not a replacement for it --
the point of running this alongside `infer.py`'s adjusted model is to see
whether a causally-motivated design (balance covariates via matching/
weighting rather than covariate-adjustment) tells a similar story. If it
doesn't, that's worth understanding before making a causal claim.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf


def propensity_scores(data: pd.DataFrame, treatment_col: str, covariates_rhs: str) -> pd.Series:
    """Fit `treatment ~ covariates` via logistic regression and return the
    predicted probability of treatment for every row (the propensity score).
    """
    fit = smf.logit(f"{treatment_col} ~ {covariates_rhs}", data=data).fit(disp=False)
    return fit.predict(data)


@dataclass
class MatchResult:
    pairs: pd.DataFrame  # treated_idx, control_idx, distance
    caliper: float
    n_treated: int
    n_matched: int


def psm_match(
    data: pd.DataFrame,
    treatment_col: str,
    propensity: pd.Series,
    caliper: float | None = None,
    seed: int = 2026,
) -> MatchResult:
    """Greedy 1:1 nearest-neighbor matching without replacement, on the
    logit of the propensity score (matching on the raw probability
    compresses distances near 0 and 1, which distorts "nearest"). Matches
    beyond `caliper` are dropped rather than forced -- a bad match is worse
    than no match. Default caliper is 0.2 SD of the logit-PS, the standard
    rule of thumb (Austin 2011).
    """
    eps = 1e-6
    p = propensity.clip(eps, 1 - eps)
    logit_ps = np.log(p / (1 - p))
    if caliper is None:
        caliper = 0.2 * logit_ps.std()

    treated_idx = data.index[data[treatment_col] == 1].tolist()
    control_idx = data.index[data[treatment_col] == 0].tolist()

    rng = np.random.default_rng(seed)
    treated_order = list(rng.permutation(treated_idx))

    control_remaining = set(control_idx)
    rows = []
    for t in treated_order:
        if not control_remaining:
            break
        t_ps = logit_ps.loc[t]
        distances = {c: abs(logit_ps.loc[c] - t_ps) for c in control_remaining}
        best_c = min(distances, key=distances.get)
        best_dist = distances[best_c]
        if best_dist <= caliper:
            rows.append({"treated_idx": t, "control_idx": best_c, "distance": round(float(best_dist), 4)})
            control_remaining.discard(best_c)

    pairs = pd.DataFrame(rows, columns=["treated_idx", "control_idx", "distance"])
    return MatchResult(pairs=pairs, caliper=float(caliper), n_treated=len(treated_idx), n_matched=len(pairs))


def iptw_weights(treatment: pd.Series, propensity: pd.Series, stabilized: bool = True) -> pd.Series:
    """Inverse-probability-of-treatment weights. Stabilized (the default)
    multiplies by the marginal treatment prevalence, which keeps the weight
    distribution tighter and is the standard recommendation (Hernan &
    Robins, Causal Inference: What If) unless there's a specific reason to
    use the unstabilized form.
    """
    eps = 1e-6
    p = propensity.clip(eps, 1 - eps)
    treated = treatment == 1
    if stabilized:
        p_treated = treatment.mean()
        w = np.where(treated, p_treated / p, (1 - p_treated) / (1 - p))
    else:
        w = np.where(treated, 1 / p, 1 / (1 - p))
    return pd.Series(w, index=treatment.index)


def _e_value_from_rr(rr: float) -> float:
    """VanderWeele & Ding (2017), eq. 2. RR must be expressed >= 1 (flip
    a protective RR < 1 to its reciprocal first -- the E-value is symmetric
    either way, this just keeps one formula)."""
    if rr < 1:
        rr = 1.0 / rr
    return float(rr + np.sqrt(rr * (rr - 1)))


def e_value(
    estimate: float,
    ci_bound: float | None = None,
    measure: str = "OR",
    rare_outcome: bool = False,
) -> dict:
    """E-value (VanderWeele & Ding 2017): the minimum strength of
    association, on the risk-ratio scale, that an unmeasured confounder
    would need with both the exposure and the outcome to fully explain away
    the observed association, above and beyond the measured covariates.

    `estimate` is the point estimate; `ci_bound` should be the confidence
    bound *closer to the null* (e.g. the lower bound if the estimate > 1)
    -- the E-value for that bound answers "how robust is the finding that
    an effect exists at all," a stricter and more useful question than the
    E-value for the point estimate alone.

    `measure`: "OR" (converted to an approximate risk ratio via sqrt(OR),
    the standard approximation for a non-rare outcome -- VanderWeele 2017)
    or "RR" (used as-is). Set `rare_outcome=True` to skip the conversion
    when the outcome prevalence is low enough (rule of thumb: < ~15%) that
    OR already approximates RR closely.
    """
    if measure not in ("OR", "RR"):
        raise ValueError("measure must be 'OR' or 'RR'")

    convert = measure == "OR" and not rare_outcome
    rr = float(np.sqrt(estimate)) if convert else float(estimate)
    rr_ci = (float(np.sqrt(ci_bound)) if convert else float(ci_bound)) if ci_bound is not None else None

    e_point = _e_value_from_rr(rr)
    e_ci = None
    if rr_ci is not None:
        # If the CI bound is on the other side of the null (1.0) from the
        # point estimate, the interval already includes "no effect" -- no
        # unmeasured confounding is needed to explain that away, E-value = 1.
        crosses_null = (rr >= 1 and rr_ci <= 1) or (rr <= 1 and rr_ci >= 1)
        e_ci = 1.0 if crosses_null else _e_value_from_rr(rr_ci)

    return {
        "measure": measure,
        "estimate": estimate,
        "rr_scale_estimate": round(rr, 4),
        "e_value_point": round(e_point, 4),
        "ci_bound": ci_bound,
        "e_value_ci": round(e_ci, 4) if e_ci is not None else None,
    }
