"""Read `limitations_pulled_forward`'s three flags from **plan files**, not
real-run output -- unlike diagnostics_extraction, this is safe to run
before the real data has even been analyzed, since it describes decisions
recorded at Stage D1b (SAP) / Stage D3 (SEM measurement plan).

- `missing_data`: reuses `tools.sap_gate.sap_parser.parse_sap` (the same
  parser Phase 0's gate uses) rather than re-deriving a second regex for
  `plans/sap.md` Section H.
- `single_item_constructs`: any construct whose `items` list in
  `plans/sem_measurement_plan.yaml` (or `plans/sem_structural_plan.yaml`,
  if it redefines constructs) has exactly one entry.
- `synthetic_verification_note`: always true; documents the DR workflow's
  own privacy design rather than a project-specific fact.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import yaml

from tools.sap_gate.sap_parser import parse_sap

_NONE_SENTINELS = {"", "none", "n/a", "na", "-"}


def _parse_variable_list(raw: str | None) -> list[str]:
    """`variables_affected` in Section H is free-text, not YAML -- "none"
    (the value every current project uses) means zero variables; anything
    else is read as a comma-separated list."""
    if raw is None:
        return []
    raw = raw.strip()
    if raw.lower() in _NONE_SENTINELS:
        return []
    return [v.strip() for v in raw.split(",") if v.strip()]


@dataclass
class MissingDataFlag:
    source: str = "plans/sap.md Section H"
    strategy: str = ""
    variables_affected: list[str] = field(default_factory=list)
    include_in_limitations: bool = False

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "strategy": self.strategy,
            "variables_affected": self.variables_affected,
            "include_in_limitations": self.include_in_limitations,
        }


def extract_missing_data_flag(sap_md_text: str | None) -> MissingDataFlag:
    if not sap_md_text or not sap_md_text.strip():
        return MissingDataFlag()
    block = parse_sap(sap_md_text).missing_data
    if block is None:
        return MissingDataFlag()
    strategy = (block.get("strategy") or "").strip()
    variables = _parse_variable_list(block.get("variables_affected"))
    include = strategy == "complete_case" and bool(variables)
    return MissingDataFlag(strategy=strategy, variables_affected=variables, include_in_limitations=include)


@dataclass
class SingleItemConstructsFlag:
    source: str = "plans/sem_measurement_plan.yaml or plans/sem_structural_plan.yaml"
    flagged_constructs: list[str] = field(default_factory=list)
    include_in_limitations: bool = False

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "flagged_constructs": self.flagged_constructs,
            "include_in_limitations": self.include_in_limitations,
        }


def extract_single_item_constructs(*plan_yaml_texts: str | None) -> SingleItemConstructsFlag:
    """Pass the text of every SEM plan file that defines `constructs:`
    (typically just `sem_measurement_plan.yaml`; include
    `sem_structural_plan.yaml` too if a project redefines constructs there).
    A construct name repeated across files is only flagged once."""
    flagged: dict[str, None] = {}  # dict, not set, to preserve first-seen order
    for text in plan_yaml_texts:
        if not text or not text.strip():
            continue
        data = yaml.safe_load(text) or {}
        if not isinstance(data, dict):
            continue
        for construct in data.get("constructs") or []:
            if not isinstance(construct, dict):
                continue
            items = construct.get("items") or []
            if isinstance(items, list) and len(items) == 1:
                name = construct.get("construct_name", "<unnamed construct>")
                flagged[name] = None
    return SingleItemConstructsFlag(flagged_constructs=list(flagged), include_in_limitations=bool(flagged))


@dataclass
class SyntheticVerificationFlag:
    source: str = "workflow design -- true for every DR project"
    include_in_limitations: bool = True

    def to_dict(self) -> dict:
        return {"source": self.source, "include_in_limitations": self.include_in_limitations}


def synthetic_verification_note() -> SyntheticVerificationFlag:
    return SyntheticVerificationFlag()


@dataclass
class LimitationsPulledForward:
    missing_data: MissingDataFlag
    single_item_constructs: SingleItemConstructsFlag
    synthetic_verification_note: SyntheticVerificationFlag

    def to_dict(self) -> dict:
        return {
            "missing_data": self.missing_data.to_dict(),
            "single_item_constructs": self.single_item_constructs.to_dict(),
            "synthetic_verification_note": self.synthetic_verification_note.to_dict(),
        }


def build_limitations_pulled_forward(
    sap_md_text: str | None = None,
    sem_plan_yaml_texts: list[str] | None = None,
) -> dict:
    """Build the full `limitations_pulled_forward` block from plan-file
    text. `sap_md_text` is the content of `plans/sap.md`;
    `sem_plan_yaml_texts` is a list of SEM plan YAML file contents (omit
    or pass `None`/`[]` for a medical-track project with no SEM plans)."""
    result = LimitationsPulledForward(
        missing_data=extract_missing_data_flag(sap_md_text),
        single_item_constructs=extract_single_item_constructs(*(sem_plan_yaml_texts or [])),
        synthetic_verification_note=synthetic_verification_note(),
    )
    return result.to_dict()
