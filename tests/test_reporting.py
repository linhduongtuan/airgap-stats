"""Self-contained smoke tests for tools.reporting -- no pytest required.

Run with:  .venv/bin/python tests/test_reporting.py

Uses frozen, verbatim snapshots of real project output (captured from an
actual scripts/infer.py / sem_structural.py run on crp-mortality /
burnout-mediation's synthetic data) as fixtures wherever the branch they
exercise actually occurs in this repo, plus small inline synthetic
fixtures for the branches none of the 4 real projects happen to trigger
(a flagged VIF, a nonlinear-suspected variable, a non-"none"
variables_affected, a single-item construct, full/partial mediation
conclusions).

Deliberately NOT read live from projects/*/outputs_synthetic/ at test
time: those directories are shared between each project's .R and .py
scripts (by design, throughout this repo), so re-running either language's
script overwrites the same file the other language just wrote -- a test
that read the live file would flake depending on which script ran last,
not on whether tools.reporting's extraction code is correct. Frozen
snapshots make this test about the extraction logic only.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.reporting import (
    build_diagnostics_extracted,
    build_limitations_pulled_forward,
    extract_bootstrap_mediation,
    extract_bootstrap_validation,
    extract_missing_data_flag,
    extract_nonlinearity_refit,
    extract_single_item_constructs,
    extract_vif,
    synthetic_verification_note,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_passed = 0
_failed: list[str] = []


def check(name: str, condition: bool) -> None:
    global _passed
    if condition:
        _passed += 1
    else:
        _failed.append(name)
        print(f"FAIL: {name}")


def _read(rel_path: str) -> str:
    return (_REPO_ROOT / rel_path).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Frozen snapshots of real Python-generated project output (captured
# 2026-08-16 from crp-mortality/scripts/infer.py and
# burnout-mediation/scripts/sem_structural.py on the synthetic dataset as
# shipped) -- see the module docstring for why these are frozen strings
# rather than live file reads.
# ---------------------------------------------------------------------------

_CRP_MORTALITY_VIF_CSV = """term,vif,flagged
"Q(\"\"complication\"\")",1.136454672621503,False
"Q(\"\"sbp\"\")",1.0947515831282337,False
"Q(\"\"age\"\")",1.0791146703175813,False
"Q(\"\"sex\"\")[T.Nam]",1.0768468694176423,False
crp,1.0727336069473141,False
"Q(\"\"bmi\"\")",1.0625553412171844,False
"Q(\"\"smoking\"\")",1.0552558232595575,False
"Q(\"\"treatment\"\")[T.Phác đồ B]",1.0449668126207428,False
"Q(\"\"hba1c\"\")",1.0330287726570513,False
"Q(\"\"hypertension\"\")",1.031760425220946,False
"Q(\"\"diabetes\"\")",1.0314148955292177,False
"Q(\"\"egfr\"\")",1.0285042354064362,False
"""

_CRP_MORTALITY_BOOTSTRAP_VALIDATION_CSV = """n_boot,n_failed_fits,apparent_auc,optimism_auc,corrected_auc,apparent_calibration_slope,optimism_calibration_slope,corrected_calibration_slope
200,0,0.6073,0.1061,0.5012,1.0,0.6214,0.3786
"""

_CRP_MORTALITY_FIRTH_CSV = """term,estimate,or,ci_low,ci_high,p_value
Intercept,0.1761,1.1926,0.2972,4.7855,0.8038
"Q(\"\"sex\"\")[T.Nam]",-0.198,0.8204,0.4558,1.4764,0.509
"Q(\"\"treatment\"\")[T.Phác đồ B]",0.3209,1.3784,0.7737,2.4557,0.276
crp,0.0032,1.0032,0.9933,1.0133,0.5245
"Q(\"\"age\"\")",0.0041,1.0041,0.9938,1.0144,0.4396
"Q(\"\"bmi\"\")",-0.0056,0.9944,0.9844,1.0046,0.2818
"Q(\"\"sbp\"\")",-0.0015,0.9985,0.9885,1.0086,0.7694
"Q(\"\"diabetes\"\")",0.2087,1.232,0.6905,2.1983,0.48
"Q(\"\"hypertension\"\")",-0.359,0.6984,0.393,1.2412,0.2211
"Q(\"\"smoking\"\")",0.1107,1.1171,0.6245,1.9982,0.7089
"Q(\"\"egfr\"\")",-0.0028,0.9972,0.9875,1.0071,0.5793
"Q(\"\"hba1c\"\")",-0.0019,0.9981,0.988,1.0083,0.7084
"Q(\"\"complication\"\")",-0.1454,0.8646,0.4721,1.5836,0.6376
"""

_CRP_MORTALITY_BOX_TIDWELL_CSV = """variable,status,p_value,detail
crp,linear,0.6994,interaction term `crp:np.log(crp)` p=0.6994
age,skipped,,age has non-positive values; Box-Tidwell requires x > 0
bmi,linear,0.7621,interaction term `bmi:np.log(bmi)` p=0.7621
sbp,linear,0.065,interaction term `sbp:np.log(sbp)` p=0.0650
egfr,linear,0.1409,interaction term `egfr:np.log(egfr)` p=0.1409
hba1c,linear,0.2736,interaction term `hba1c:np.log(hba1c)` p=0.2736
"""

_BURNOUT_MEDIATION_SEM_MEDIATION_CSV = """path,estimate,ci_low,ci_high
a (JS -> Burnout),0.2998,-0.5649,4.8405
b (Burnout -> TO | JS),1.6147,-20.4698,24.1405
c' (JS -> TO direct),-0.1564,-24.4627,4.6636
indirect (a*b),0.484,-25.2772,9.7386
total (c'+a*b),0.3276,-13.9389,1.5941
"""


# ---------------------------------------------------------------------------
# VIF
# ---------------------------------------------------------------------------

vif_real = extract_vif(_CRP_MORTALITY_VIF_CSV)
check("VIF: real crp-mortality file marks available", vif_real.available)
check("VIF: real crp-mortality max_vif matches file (~1.1365)", abs(vif_real.max_vif - 1.1365) < 1e-3)
check("VIF: no flagged terms in crp-mortality (all VIF well under 5)", vif_real.flagged_terms == [])

vif_flagged_csv = "term,vif,flagged\nage,1.2,False\nbmi,7.5,True\n"
vif_flagged = extract_vif(vif_flagged_csv)
check("VIF: synthetic fixture flags the term with vif > 5", vif_flagged.flagged_terms == ["bmi"])
check("VIF: synthetic fixture max_vif is 7.5", vif_flagged.max_vif == 7.5)

vif_no_flagged_col = extract_vif("term,vif\nage,1.2\nbmi,7.5\n")
check("VIF: derives flagged from threshold when no `flagged` column present",
      vif_no_flagged_col.flagged_terms == ["bmi"])

vif_empty = extract_vif(None)
check("VIF: None input is unavailable, not a crash", vif_empty.available is False and vif_empty.max_vif is None)
vif_blank = extract_vif("   ")
check("VIF: blank-string input is unavailable", vif_blank.available is False)
vif_malformed = extract_vif("not,a,vif,file\n1,2,3,4\n")
check("VIF: malformed CSV (no vif/term columns) is unavailable, not a crash", vif_malformed.available is False)

# ---------------------------------------------------------------------------
# Bootstrap validation
# ---------------------------------------------------------------------------

bv_real = extract_bootstrap_validation(_CRP_MORTALITY_BOOTSTRAP_VALIDATION_CSV)
check("Bootstrap validation: real file marks available", bv_real.available)
check("Bootstrap validation: n_boot matches file (200)", bv_real.n_boot == 200)
check("Bootstrap validation: apparent_auc matches file (~0.6073)", abs(bv_real.apparent_auc - 0.6073) < 1e-3)
check("Bootstrap validation: corrected_auc matches file (~0.5012)", abs(bv_real.corrected_auc - 0.5012) < 1e-3)
check("Bootstrap validation: corrected_calibration_slope matches file (~0.3786)",
      abs(bv_real.corrected_calibration_slope - 0.3786) < 1e-3)

bv_empty = extract_bootstrap_validation(None)
check("Bootstrap validation: None input is unavailable", bv_empty.available is False)

# ---------------------------------------------------------------------------
# Nonlinearity / Firth refit
# ---------------------------------------------------------------------------

nlr_real = extract_nonlinearity_refit(_CRP_MORTALITY_FIRTH_CSV, _CRP_MORTALITY_BOX_TIDWELL_CSV)
check("Nonlinearity: real files mark available", nlr_real.available)
check("Nonlinearity: firth_refit_terms excludes the intercept",
      "Intercept" not in nlr_real.firth_refit_terms and "intercept" not in [t.lower() for t in nlr_real.firth_refit_terms])
check("Nonlinearity: firth_refit_terms is non-empty for crp-mortality's adjusted model",
      len(nlr_real.firth_refit_terms) > 0)
check("Nonlinearity: no variable flagged nonlinear_suspected in crp-mortality's Box-Tidwell run",
      nlr_real.log_or_spline_terms == [])

bt_flagged_csv = "variable,status,p_value,detail\ncrp,linear,0.7,x\nage,nonlinear_suspected,0.01,y\n"
nlr_flagged = extract_nonlinearity_refit(None, bt_flagged_csv)
check("Nonlinearity: synthetic fixture flags the nonlinear_suspected variable",
      nlr_flagged.log_or_spline_terms == ["age"])
check("Nonlinearity: firth_refit_terms empty when no firth CSV given", nlr_flagged.firth_refit_terms == [])

nlr_empty = extract_nonlinearity_refit(None, None)
check("Nonlinearity: both-None input is unavailable", nlr_empty.available is False)

# ---------------------------------------------------------------------------
# Bootstrap mediation
# ---------------------------------------------------------------------------

med_real = extract_bootstrap_mediation(_BURNOUT_MEDIATION_SEM_MEDIATION_CSV, n_boot=200)
check("Mediation: real burnout-mediation file marks available", med_real.available)
check("Mediation: a matches file (0.2998)", abs(med_real.a - 0.2998) < 1e-4)
check("Mediation: b matches file (1.6147)", abs(med_real.b - 1.6147) < 1e-4)
check("Mediation: c_prime matches file (-0.1564)", abs(med_real.c_prime - (-0.1564)) < 1e-4)
check("Mediation: indirect matches file (0.484)", abs(med_real.indirect - 0.484) < 1e-4)
check("Mediation: conclusion is 'none' -- the real file's indirect CI includes 0",
      med_real.mediation_conclusion == "none")

# Synthetic fixtures for the two conclusion branches the real project data
# doesn't happen to hit: indirect CI excluding 0, with c' CI either
# including 0 (full mediation) or also excluding 0 (partial mediation).
med_full_csv = (
    "path,estimate,ci_low,ci_high\n"
    "a (X -> M),0.5,0.2,0.8\n"
    "b (M -> Y),0.6,0.3,0.9\n"
    "c' (X -> Y direct),0.05,-0.2,0.3\n"
    "indirect (a*b),0.3,0.1,0.5\n"
    "total (c'+a*b),0.35,0.1,0.6\n"
)
med_full = extract_bootstrap_mediation(med_full_csv, n_boot=500)
check("Mediation: full-mediation fixture (indirect excludes 0, c' includes 0) -> 'full'",
      med_full.mediation_conclusion == "full")
check("Mediation: n_boot is threaded through", med_full.n_boot == 500)

med_partial_csv = (
    "path,estimate,ci_low,ci_high\n"
    "a (X -> M),0.5,0.2,0.8\n"
    "b (M -> Y),0.6,0.3,0.9\n"
    "c' (X -> Y direct),0.4,0.1,0.7\n"
    "indirect (a*b),0.3,0.1,0.5\n"
    "total (c'+a*b),0.7,0.4,1.0\n"
)
med_partial = extract_bootstrap_mediation(med_partial_csv)
check("Mediation: partial-mediation fixture (both indirect and c' exclude 0) -> 'partial'",
      med_partial.mediation_conclusion == "partial")

med_none_csv = (
    "path,estimate,ci_low,ci_high\n"
    "a (X -> M),0.1,-0.2,0.4\n"
    "b (M -> Y),0.1,-0.3,0.5\n"
    "c' (X -> Y direct),0.4,0.1,0.7\n"
    "indirect (a*b),0.01,-0.1,0.15\n"
    "total (c'+a*b),0.41,0.05,0.8\n"
)
check("Mediation: indirect CI including 0 -> 'none' regardless of c'",
      extract_bootstrap_mediation(med_none_csv).mediation_conclusion == "none")

med_empty = extract_bootstrap_mediation(None)
check("Mediation: None input is unavailable, not a crash", med_empty.available is False)
med_no_indirect = extract_bootstrap_mediation("path,estimate,ci_low,ci_high\na (X -> M),0.5,0.2,0.8\n")
check("Mediation: a file with no 'indirect' row is unavailable rather than partially filled",
      med_no_indirect.available is False)

# ---------------------------------------------------------------------------
# build_diagnostics_extracted (combined)
# ---------------------------------------------------------------------------

combined = build_diagnostics_extracted(
    vif_csv_text=_CRP_MORTALITY_VIF_CSV,
    bootstrap_validation_csv_text=_CRP_MORTALITY_BOOTSTRAP_VALIDATION_CSV,
)
check("build_diagnostics_extracted: has all four sub-blocks",
      set(combined.keys()) == {"vif", "bootstrap_validation", "nonlinearity_refit", "bootstrap_mediation"})
check("build_diagnostics_extracted: vif sub-block available", combined["vif"]["available"])
check("build_diagnostics_extracted: unset sub-blocks stay unavailable, not omitted",
      combined["nonlinearity_refit"]["available"] is False and combined["bootstrap_mediation"]["available"] is False)

# ---------------------------------------------------------------------------
# Missing-data flag
# ---------------------------------------------------------------------------

md_real = extract_missing_data_flag(_read("projects/crp-mortality/plans/sap.md"))
check("Missing-data: real crp-mortality sap.md parses strategy=complete_case", md_real.strategy == "complete_case")
check("Missing-data: real crp-mortality has variables_affected: none -> empty list", md_real.variables_affected == [])
check("Missing-data: not included in limitations when variables_affected is empty",
      md_real.include_in_limitations is False)

md_synth = (
    "## H. Missing data\n\n```text\nstrategy:            complete_case\n"
    "variables_affected:  age, bmi\nimputation_model:    none\nbasis:                confirmed\n```\n"
)
md_flagged = extract_missing_data_flag(md_synth)
check("Missing-data: synthetic fixture parses variables_affected as a list",
      md_flagged.variables_affected == ["age", "bmi"])
check("Missing-data: included in limitations when complete_case + non-empty variables_affected",
      md_flagged.include_in_limitations is True)

md_mi = (
    "## H. Missing data\n\n```text\nstrategy:            multiple_imputation\n"
    "variables_affected:  age, bmi\nimputation_model:    pmm, m=20\nbasis:                confirmed\n```\n"
)
check("Missing-data: multiple_imputation strategy is never flagged as the complete-case caveat",
      extract_missing_data_flag(md_mi).include_in_limitations is False)

md_empty = extract_missing_data_flag(None)
check("Missing-data: None input defaults to not-included, not a crash", md_empty.include_in_limitations is False)
md_no_section = extract_missing_data_flag("# Some other document\n\nNo Section H here.\n")
check("Missing-data: a document with no Section H defaults safely", md_no_section.strategy == "")

# ---------------------------------------------------------------------------
# Single-item constructs
# ---------------------------------------------------------------------------

sem_real = extract_single_item_constructs(_read("projects/burnout-mediation/plans/sem_measurement_plan.yaml"))
check("Single-item: burnout-mediation's real constructs (5 items each) are not flagged",
      sem_real.flagged_constructs == [] and sem_real.include_in_limitations is False)

sem_single_item_yaml = (
    "constructs:\n"
    "  - construct_name: \"Overall_Satisfaction\"\n"
    "    items:\n"
    "      - \"single_q\"\n"
    "  - construct_name: \"Burnout\"\n"
    "    items:\n"
    "      - \"bo_q1\"\n"
    "      - \"bo_q2\"\n"
)
sem_flagged = extract_single_item_constructs(sem_single_item_yaml)
check("Single-item: fixture flags the construct with exactly one item",
      sem_flagged.flagged_constructs == ["Overall_Satisfaction"])
check("Single-item: multi-item construct in the same file is not flagged",
      "Burnout" not in sem_flagged.flagged_constructs)
check("Single-item: included in limitations when at least one construct is flagged",
      sem_flagged.include_in_limitations is True)

sem_two_files = extract_single_item_constructs(sem_single_item_yaml, "constructs: []\n")
check("Single-item: flags persist across multiple plan files passed in",
      sem_two_files.flagged_constructs == ["Overall_Satisfaction"])

check("Single-item: no arguments defaults safely", extract_single_item_constructs().flagged_constructs == [])
check("Single-item: None/empty text among args is skipped, not a crash",
      extract_single_item_constructs(None, "").flagged_constructs == [])

# ---------------------------------------------------------------------------
# Synthetic-verification note (always true)
# ---------------------------------------------------------------------------

check("Synthetic-verification note is always included", synthetic_verification_note().include_in_limitations is True)

# ---------------------------------------------------------------------------
# build_limitations_pulled_forward (combined)
# ---------------------------------------------------------------------------

lim_combined = build_limitations_pulled_forward(
    _read("projects/crp-mortality/plans/sap.md"),
    [_read("projects/burnout-mediation/plans/sem_measurement_plan.yaml")],
)
check("build_limitations_pulled_forward: has all three sub-blocks",
      set(lim_combined.keys()) == {"missing_data", "single_item_constructs", "synthetic_verification_note"})
check("build_limitations_pulled_forward: synthetic_verification_note always true",
      lim_combined["synthetic_verification_note"]["include_in_limitations"] is True)

lim_defaults = build_limitations_pulled_forward()
check("build_limitations_pulled_forward: works with no arguments (medical-track project, no SEM plans)",
      lim_defaults["single_item_constructs"]["flagged_constructs"] == []
      and lim_defaults["synthetic_verification_note"]["include_in_limitations"] is True)

# ---------------------------------------------------------------------------
print(f"\n{_passed} passed, {len(_failed)} failed")
if _failed:
    print("Failed checks:")
    for name in _failed:
        print(f"  - {name}")
    sys.exit(1)
print("ALL TESTS PASSED")
