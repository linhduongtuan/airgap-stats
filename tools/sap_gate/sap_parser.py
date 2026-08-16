"""Parse ``plans/sap.md`` into sections, and pull the two Phase 0 key:value
blocks (missing data, multiplicity) out of it.

The SAP is prose written by an agent for a human, not machine-generated YAML
-- so this parser is deliberately forgiving: it locates sections by heading
*text* ("missing data", "multiplicity"), not by the letter in front of them,
so a renumbered or locally-edited SAP still validates.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_HEADING_RE = re.compile(r"^##\s+([A-Z][0-9]*)\.\s+(.+?)\s*$", re.MULTILINE)
_FENCE_RE = re.compile(r"```(?:text)?\n(.*?)```", re.DOTALL)


@dataclass
class Section:
    letter: str
    title: str
    body: str


def split_sections(markdown: str) -> list[Section]:
    """Split a SAP markdown document on ``## <Letter>. <Title>`` headings."""
    matches = list(_HEADING_RE.finditer(markdown))
    sections: list[Section] = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
        sections.append(Section(letter=m.group(1), title=m.group(2), body=markdown[start:end]))
    return sections


def find_section(sections: list[Section], keyword: str) -> Section | None:
    """First section whose title contains ``keyword`` (case-insensitive)."""
    kw = keyword.lower()
    for s in sections:
        if kw in s.title.lower():
            return s
    return None


def parse_kv_block(text: str) -> dict[str, str] | None:
    """Parse the first fenced block's ``key: value`` lines into a dict.

    Returns ``None`` if the section has no fenced block at all (a hard
    "this decision was never written down" signal, distinct from an empty
    dict, which would mean the fence exists but every line was unparsable).
    """
    fence = _FENCE_RE.search(text)
    if fence is None:
        return None
    out: dict[str, str] = {}
    for line in fence.group(1).splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip()
    return out


@dataclass
class ParsedSap:
    sections: list[Section]
    missing_data: dict[str, str] | None
    multiplicity: dict[str, str] | None


def parse_sap(markdown: str) -> ParsedSap:
    sections = split_sections(markdown)

    missing_data_section = find_section(sections, "missing data")
    multiplicity_section = find_section(sections, "multiplicity")

    return ParsedSap(
        sections=sections,
        missing_data=parse_kv_block(missing_data_section.body) if missing_data_section else None,
        multiplicity=parse_kv_block(multiplicity_section.body) if multiplicity_section else None,
    )
