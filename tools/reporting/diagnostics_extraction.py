"""Parse real-run diagnostic CSVs into the `diagnostics_extracted` schema
documented in `skills/dr-05-present-results/references/traceability-check-template.md`.

Every function here takes CSV **text** (a string), not a file path, and
returns `available=False` gracefully when handed `None`/empty input --
Stage E's whole point is that this data only ever comes from what the user
pastes or copies from their real RStudio session, never from
`outputs_synthetic/`. Nothing in this module reads a file itself; callers
decide where the text came from.

Column names and thresholds are taken directly from the scripts that
produce them, not re-derived:
  - VIF: `tools/diagnostics/regression_diagnostics.compute_vif` (columns
    `term, vif, flagged`; flag threshold `VIF_FLAG_THRESHOLD = 5.0`).
  - Bootstrap validation: `tools/diagnostics/bootstrap_validation.bootstrap_optimism`
    (columns include `n_boot, apparent_auc, corrected_auc,
    corrected_calibration_slope`).
  - Box-Tidwell: `tools/diagnostics/regression_diagnostics.box_tidwell_test`
    (`status` in `{linear, nonlinear_suspected, skipped, error}`).
  - Bootstrap mediation: `tools/sem_track/mediation.MediationBootstrapResult`,
    written to CSV with `path` values like `"a (JS -> Burnout)"`,
    `"c' (JS -> TO direct)"`, `"indirect (a*b)"`, `"total (c'+a*b)"` --
    matched here by prefix, not exact string, since the parenthetical
    description is project-specific (see `projects/burnout-mediation/scripts/sem_structural.py`'s `label_map`).
"""

from __future__ import annotations

import io
import math
from dataclasses import dataclass, field

import pandas as pd

VIF_FLAG_THRESHOLD = 5.0


def _read_csv(text: str | None) -> pd.DataFrame | None:
    if not text or not text.strip():
        return None
    return pd.read_csv(io.StringIO(text))


def _is_nan(x: object) -> bool:
    try:
        return isinstance(x, float) and math.isnan(x)
    except TypeError:
        return False


# ---------------------------------------------------------------------------
# VIF
# ---------------------------------------------------------------------------


@dataclass
class VifExtraction:
    available: bool = False
    max_vif: float | None = None
    flagged_terms: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"available": self.available, "max_vif": self.max_vif, "flagged_terms": self.flagged_terms}


def extract_vif(csv_text: str | None) -> VifExtraction:
    df = _read_csv(csv_text)
    if df is None or df.empty or "vif" not in df.columns or "term" not in df.columns:
        return VifExtraction()
    max_vif = float(df["vif"].max())
    if "flagged" in df.columns:
        flagged_mask = df["flagged"].astype(str).str.strip().str.lower().isin({"true", "1"})
    else:
        flagged_mask = df["vif"] > VIF_FLAG_THRESHOLD
    flagged_terms = df.loc[flagged_mask, "term"].astype(str).tolist()
    return VifExtraction(available=True, max_vif=round(max_vif, 4), flagged_terms=flagged_terms)


# ---------------------------------------------------------------------------
# Bootstrap internal validation
# ---------------------------------------------------------------------------


@dataclass
class BootstrapValidationExtraction:
    available: bool = False
    n_boot: int | None = None
    apparent_auc: float | None = None
    corrected_auc: float | None = None
    corrected_calibration_slope: float | None = None

    def to_dict(self) -> dict:
        return {
            "available": self.available,
            "n_boot": self.n_boot,
            "apparent_auc": self.apparent_auc,
            "corrected_auc": self.corrected_auc,
            "corrected_calibration_slope": self.corrected_calibration_slope,
        }


def extract_bootstrap_validation(csv_text: str | None) -> BootstrapValidationExtraction:
    df = _read_csv(csv_text)
    required = {"n_boot", "apparent_auc", "corrected_auc", "corrected_calibration_slope"}
    if df is None or df.empty or not required.issubset(df.columns):
        return BootstrapValidationExtraction()
    row = df.iloc[0]
    return BootstrapValidationExtraction(
        available=True,
        n_boot=int(row["n_boot"]),
        apparent_auc=round(float(row["apparent_auc"]), 4),
        corrected_auc=round(float(row["corrected_auc"]), 4),
        corrected_calibration_slope=round(float(row["corrected_calibration_slope"]), 4),
    )


# ---------------------------------------------------------------------------
# Non-linearity handling (Box-Tidwell flags, Firth refit)
# ---------------------------------------------------------------------------


@dataclass
class NonlinearityRefitExtraction:
    available: bool = False
    firth_refit_terms: list[str] = field(default_factory=list)
    log_or_spline_terms: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "available": self.available,
            "firth_refit_terms": self.firth_refit_terms,
            "log_or_spline_terms": self.log_or_spline_terms,
        }


def extract_nonlinearity_refit(
    firth_csv_text: str | None = None,
    box_tidwell_csv_text: str | None = None,
) -> NonlinearityRefitExtraction:
    firth_df = _read_csv(firth_csv_text)
    bt_df = _read_csv(box_tidwell_csv_text)
    if firth_df is None and bt_df is None:
        return NonlinearityRefitExtraction()

    firth_terms: list[str] = []
    if firth_df is not None and "term" in firth_df.columns:
        # The whole adjusted model is refit under Firth's penalized likelihood
        # (not a per-term choice) -- every non-intercept term's reported
        # estimate in this file comes from that refit.
        firth_terms = [t for t in firth_df["term"].astype(str).tolist() if t.lower() != "intercept"]

    log_spline_terms: list[str] = []
    if bt_df is not None and {"variable", "status"}.issubset(bt_df.columns):
        flagged = bt_df.loc[bt_df["status"].astype(str) == "nonlinear_suspected", "variable"]
        log_spline_terms = flagged.astype(str).tolist()

    return NonlinearityRefitExtraction(
        available=firth_df is not None or bt_df is not None,
        firth_refit_terms=firth_terms,
        log_or_spline_terms=log_spline_terms,
    )


# ---------------------------------------------------------------------------
# Bootstrap mediation (SEM track, mediation models only)
# ---------------------------------------------------------------------------

_PATH_PREFIXES = {
    "a": ("a ", "a("),
    "b": ("b ", "b("),
    "c_prime": ("c'",),
    "indirect": ("indirect",),
    "total": ("total",),
}


def _match_path(path: str, key: str) -> bool:
    prefixes = _PATH_PREFIXES[key]
    return any(path.strip().lower().startswith(p) for p in prefixes)


def _ci_excludes_zero(lo: float | None, hi: float | None) -> bool | None:
    if lo is None or hi is None or _is_nan(lo) or _is_nan(hi):
        return None
    return not (lo <= 0 <= hi)


@dataclass
class BootstrapMediationExtraction:
    available: bool = False
    n_boot: int | None = None
    a: float | None = None
    a_ci_low: float | None = None
    a_ci_high: float | None = None
    b: float | None = None
    b_ci_low: float | None = None
    b_ci_high: float | None = None
    c_prime: float | None = None
    c_prime_ci_low: float | None = None
    c_prime_ci_high: float | None = None
    indirect: float | None = None
    indirect_ci_low: float | None = None
    indirect_ci_high: float | None = None
    mediation_conclusion: str = "none"

    def to_dict(self) -> dict:
        d = {
            "available": self.available,
            "n_boot": self.n_boot,
            "a": self.a, "a_ci_low": self.a_ci_low, "a_ci_high": self.a_ci_high,
            "b": self.b, "b_ci_low": self.b_ci_low, "b_ci_high": self.b_ci_high,
            "c_prime": self.c_prime, "c_prime_ci_low": self.c_prime_ci_low, "c_prime_ci_high": self.c_prime_ci_high,
            "indirect": self.indirect, "indirect_ci_low": self.indirect_ci_low, "indirect_ci_high": self.indirect_ci_high,
            "mediation_conclusion": self.mediation_conclusion,
        }
        return d


def extract_bootstrap_mediation(csv_text: str | None, n_boot: int | None = None) -> BootstrapMediationExtraction:
    df = _read_csv(csv_text)
    if df is None or df.empty or not {"path", "estimate", "ci_low", "ci_high"}.issubset(df.columns):
        return BootstrapMediationExtraction()

    values: dict[str, dict[str, float]] = {}
    for key in _PATH_PREFIXES:
        matched = df[df["path"].astype(str).apply(lambda p, k=key: _match_path(p, k))]
        if matched.empty:
            continue
        row = matched.iloc[0]
        values[key] = {
            "estimate": float(row["estimate"]) if not _is_nan(row["estimate"]) else None,
            "ci_low": float(row["ci_low"]) if not _is_nan(row["ci_low"]) else None,
            "ci_high": float(row["ci_high"]) if not _is_nan(row["ci_high"]) else None,
        }

    if "indirect" not in values:
        return BootstrapMediationExtraction()

    indirect_excludes_zero = _ci_excludes_zero(values["indirect"]["ci_low"], values["indirect"]["ci_high"])
    c_prime_vals = values.get("c_prime", {})
    c_prime_excludes_zero = _ci_excludes_zero(c_prime_vals.get("ci_low"), c_prime_vals.get("ci_high"))

    if indirect_excludes_zero is None:
        conclusion = "none"  # can't tell -- treat conservatively as no supported mediation
    elif not indirect_excludes_zero:
        conclusion = "none"
    elif c_prime_excludes_zero is False:
        conclusion = "full"
    else:
        conclusion = "partial"

    def _get(key: str, field_name: str) -> float | None:
        return values.get(key, {}).get(field_name)

    return BootstrapMediationExtraction(
        available=True,
        n_boot=n_boot,
        a=_get("a", "estimate"), a_ci_low=_get("a", "ci_low"), a_ci_high=_get("a", "ci_high"),
        b=_get("b", "estimate"), b_ci_low=_get("b", "ci_low"), b_ci_high=_get("b", "ci_high"),
        c_prime=_get("c_prime", "estimate"), c_prime_ci_low=_get("c_prime", "ci_low"), c_prime_ci_high=_get("c_prime", "ci_high"),
        indirect=_get("indirect", "estimate"), indirect_ci_low=_get("indirect", "ci_low"), indirect_ci_high=_get("indirect", "ci_high"),
        mediation_conclusion=conclusion,
    )


# ---------------------------------------------------------------------------
# Combined
# ---------------------------------------------------------------------------


def build_diagnostics_extracted(
    vif_csv_text: str | None = None,
    bootstrap_validation_csv_text: str | None = None,
    firth_csv_text: str | None = None,
    box_tidwell_csv_text: str | None = None,
    bootstrap_mediation_csv_text: str | None = None,
    bootstrap_mediation_n_boot: int | None = None,
) -> dict:
    """Build the full `diagnostics_extracted` block. Every argument is
    optional real-run CSV text; omit whatever the user didn't provide.

    Returns only the computed sub-fields (`available`, the numbers/lists) --
    not the static `source:` annotation lines from
    `traceability-check-template.md`, which describe where each sub-block
    is *supposed* to come from and don't change per project. Merge this
    dict's values into a copy of that template rather than treating this
    as the complete YAML block."""
    return {
        "vif": extract_vif(vif_csv_text).to_dict(),
        "bootstrap_validation": extract_bootstrap_validation(bootstrap_validation_csv_text).to_dict(),
        "nonlinearity_refit": extract_nonlinearity_refit(firth_csv_text, box_tidwell_csv_text).to_dict(),
        "bootstrap_mediation": extract_bootstrap_mediation(bootstrap_mediation_csv_text, bootstrap_mediation_n_boot).to_dict(),
    }
