"""Bootstrap-optimism internal validation (Harrell's method) for a logistic
model: how much of the apparent AUC and calibration slope is overfitting to
this exact sample, estimated by repeatedly refitting on bootstrap resamples
and testing each refit on the original data.

No new dependency: the AUC/C-statistic is computed from the
Mann-Whitney-U <-> AUC identity (`scipy.stats.mannwhitneyu`), which is exact,
not an approximation, and avoids adding scikit-learn as a dependency just for
`roc_auc_score`.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats


@dataclass
class BootstrapValidationResult:
    n_boot: int
    n_failed_fits: int
    apparent_auc: float
    optimism_auc: float
    corrected_auc: float
    apparent_calibration_slope: float
    optimism_calibration_slope: float
    corrected_calibration_slope: float

    def to_row(self) -> dict:
        return {
            "n_boot": self.n_boot,
            "n_failed_fits": self.n_failed_fits,
            "apparent_auc": round(self.apparent_auc, 4),
            "optimism_auc": round(self.optimism_auc, 4),
            "corrected_auc": round(self.corrected_auc, 4),
            "apparent_calibration_slope": round(self.apparent_calibration_slope, 4),
            "optimism_calibration_slope": round(self.optimism_calibration_slope, 4),
            "corrected_calibration_slope": round(self.corrected_calibration_slope, 4),
        }


def _auc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """C-statistic via the Mann-Whitney U <-> AUC identity: AUC = U / (n_pos * n_neg)."""
    pos = y_score[y_true == 1]
    neg = y_score[y_true == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    u_stat, _p = stats.mannwhitneyu(pos, neg, alternative="greater")
    return float(u_stat / (len(pos) * len(neg)))


def _linpred_from_proba(p: np.ndarray, eps: float = 1e-9) -> np.ndarray:
    p = np.clip(p, eps, 1 - eps)
    return np.log(p / (1 - p))


def _calibration_slope(outcome: np.ndarray, linpred: np.ndarray) -> float:
    """Slope of outcome ~ linear_predictor. 1.0 = perfectly calibrated;
    < 1 is the classic signature of overfitting (predictions too extreme)."""
    df = pd.DataFrame({"y": outcome, "lp": linpred})
    if df["y"].nunique() < 2 or df["lp"].std() == 0:
        return float("nan")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit = smf.logit("y ~ lp", data=df).fit(disp=False, maxiter=200)
    return float(fit.params["lp"])


def bootstrap_optimism(
    data: pd.DataFrame,
    formula: str,
    outcome: str,
    n_boot: int = 200,
    seed: int = 2026,
) -> BootstrapValidationResult:
    """Harrell's bootstrap-optimism procedure.

    For each of `n_boot` resamples (with replacement, same size as `data`):
    refit the model on the resample, evaluate it on the resample itself
    (training/"bootstrap" performance) and on the original `data` (test
    performance). The average gap between the two is the optimism; apparent
    performance minus optimism is the corrected estimate of how the model
    will perform on new data.
    """
    rng = np.random.default_rng(seed)
    n = len(data)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        apparent_fit = smf.logit(formula, data=data).fit(disp=False, maxiter=200)
    y = data[outcome].to_numpy()
    apparent_p = apparent_fit.predict(data).to_numpy()
    apparent_auc = _auc(y, apparent_p)
    apparent_slope = _calibration_slope(y, _linpred_from_proba(apparent_p))

    optimism_auc: list[float] = []
    optimism_slope: list[float] = []
    n_failed = 0

    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        boot_data = data.iloc[idx].reset_index(drop=True)

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                boot_fit = smf.logit(formula, data=boot_data).fit(disp=False, maxiter=200)
            if not boot_fit.mle_retvals.get("converged", True):
                n_failed += 1
                continue
        except Exception:  # noqa: BLE001 -- a failed bootstrap refit is data, not a crash
            n_failed += 1
            continue

        y_boot = boot_data[outcome].to_numpy()
        p_boot_on_boot = boot_fit.predict(boot_data).to_numpy()
        auc_boot_on_boot = _auc(y_boot, p_boot_on_boot)
        slope_boot_on_boot = _calibration_slope(y_boot, _linpred_from_proba(p_boot_on_boot))

        p_boot_on_orig = boot_fit.predict(data).to_numpy()
        auc_boot_on_orig = _auc(y, p_boot_on_orig)
        slope_boot_on_orig = _calibration_slope(y, _linpred_from_proba(p_boot_on_orig))

        if not (np.isnan(auc_boot_on_boot) or np.isnan(auc_boot_on_orig)):
            optimism_auc.append(auc_boot_on_boot - auc_boot_on_orig)
        if not (np.isnan(slope_boot_on_boot) or np.isnan(slope_boot_on_orig)):
            optimism_slope.append(slope_boot_on_boot - slope_boot_on_orig)

    mean_opt_auc = float(np.mean(optimism_auc)) if optimism_auc else float("nan")
    mean_opt_slope = float(np.mean(optimism_slope)) if optimism_slope else float("nan")

    return BootstrapValidationResult(
        n_boot=n_boot,
        n_failed_fits=n_failed,
        apparent_auc=apparent_auc,
        optimism_auc=mean_opt_auc,
        corrected_auc=apparent_auc - mean_opt_auc,
        apparent_calibration_slope=apparent_slope,
        optimism_calibration_slope=mean_opt_slope,
        corrected_calibration_slope=apparent_slope - mean_opt_slope,
    )
