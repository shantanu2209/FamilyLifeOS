"""Cross-reference integrity checker for FamilyLifeOS documentation.

Scans all Markdown documentation files for document and section cross-references,
resolving abbreviations (DM, FTS, CM, RB, MR, MC, FSM, NFR, PRD, tracker, SIM, TAS),
bare section references, and markdown links. Validates target document existence,
heading/section existence, and reports version mismatches (HISTORICAL / FORWARD / STALE)
and planned/missing document references.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

# Canonical document mappings (relative to repo root)
DOC_ALIASES: dict[str, str] = {
    # Shorthand acronyms from AGENTS.md §4, protocol, and founder instructions
    "DM": "docs/specs/Data_Model_Schema.md",
    "FTS": "docs/specs/Tech_Spec_Financial_Transaction_Safety.md",
    "CM": "docs/specs/Tech_Spec_Consent_Manager.md",
    "RB": "docs/runbooks/Runbook_DPI_Rate_Limits.md",
    "MR": "docs/specs/Tech_Spec_Module_Registry.md",
    "MC": "docs/strategy/Master_Context.md",
    "FSM": "docs/specs/Tech_Spec_Supervisor_State_Machine.md",
    "NFR": "docs/specs/NFR_Specs.md",
    "PRD": "docs/strategy/PRD_FamilyLifeOS_Core.md",
    "Core PRD": "docs/strategy/PRD_FamilyLifeOS_Core.md",
    "PRD Core": "docs/strategy/PRD_FamilyLifeOS_Core.md",
    "tracker": "docs/PROJECT_TRACKER.md",
    "PROJECT_TRACKER": "docs/PROJECT_TRACKER.md",
    "SIM": "docs/specs/Tech_Spec_Simulator_Architecture.md",
    "TAS": "docs/specs/Test_Automation_Strategy.md",
    "Runbook": "docs/runbooks/Runbook_DPI_Rate_Limits.md",
    "DPI Rate Limits": "docs/runbooks/Runbook_DPI_Rate_Limits.md",
    "Rate Limits runbook": "docs/runbooks/Runbook_DPI_Rate_Limits.md",
    "DPI Rate Limits runbook": "docs/runbooks/Runbook_DPI_Rate_Limits.md",
    "Runbook_DPI_Rate_Limits": "docs/runbooks/Runbook_DPI_Rate_Limits.md",
    # Expanded document names and variations
    "Data Model Schema": "docs/specs/Data_Model_Schema.md",
    "Data Model": "docs/specs/Data_Model_Schema.md",
    "Data_Model_Schema": "docs/specs/Data_Model_Schema.md",
    "Financial Transaction Safety": "docs/specs/Tech_Spec_Financial_Transaction_Safety.md",
    "Tech_Spec_Financial_Transaction_Safety": "docs/specs/Tech_Spec_Financial_Transaction_Safety.md",
    "Financial Safety spec": "docs/specs/Tech_Spec_Financial_Transaction_Safety.md",
    "FTS spec": "docs/specs/Tech_Spec_Financial_Transaction_Safety.md",
    "Consent Manager": "docs/specs/Tech_Spec_Consent_Manager.md",
    "Tech_Spec_Consent_Manager": "docs/specs/Tech_Spec_Consent_Manager.md",
    "Module Registry": "docs/specs/Tech_Spec_Module_Registry.md",
    "Tech_Spec_Module_Registry": "docs/specs/Tech_Spec_Module_Registry.md",
    "Master Context": "docs/strategy/Master_Context.md",
    "Master_Context": "docs/strategy/Master_Context.md",
    "Supervisor State Machine": "docs/specs/Tech_Spec_Supervisor_State_Machine.md",
    "Tech_Spec_Supervisor_State_Machine": "docs/specs/Tech_Spec_Supervisor_State_Machine.md",
    "NFR Specs": "docs/specs/NFR_Specs.md",
    "NFR_Specs": "docs/specs/NFR_Specs.md",
    "PRD_FamilyLifeOS_Core": "docs/strategy/PRD_FamilyLifeOS_Core.md",
    "Tech_Spec_Simulator_Architecture": "docs/specs/Tech_Spec_Simulator_Architecture.md",
    "Test_Automation_Strategy": "docs/specs/Test_Automation_Strategy.md",
    "Roadmap": "docs/strategy/Roadmap.md",
    "Execution Plan": "docs/Execution_Plan.md",
    "Execution_Plan": "docs/Execution_Plan.md",
    "GTM Plan": "docs/strategy/GTM_Plan.md",
    "GTM_Plan": "docs/strategy/GTM_Plan.md",
    "Master PRD": "docs/strategy/Master_PRD.md",
    "Master_PRD": "docs/strategy/Master_PRD.md",
    "Vision Journey": "docs/strategy/Vision_Journey.md",
    "Vision_Journey": "docs/strategy/Vision_Journey.md",
    "Vision Parking Lot": "docs/strategy/Vision_Parking_Lot.md",
    "Vision_Parking_Lot": "docs/strategy/Vision_Parking_Lot.md",
    "Workstation Setup": "docs/reference/Workstation_Setup.md",
    "Workstation_Setup": "docs/reference/Workstation_Setup.md",
    "Local Agent Setup": "docs/reference/Local_Agent_Setup.md",
    "Local_Agent_Setup": "docs/reference/Local_Agent_Setup.md",
    "DPI Integration Primer": "docs/reference/DPI_Integration_Primer.md",
    "DPI_Integration_Primer": "docs/reference/DPI_Integration_Primer.md",
    "PRD_Module_Finance": "docs/strategy/PRD_Module_Finance.md",
    "Finance PRD": "docs/strategy/PRD_Module_Finance.md",
    "PRD_Module_Health": "docs/strategy/PRD_Module_Health.md",
    "Health PRD": "docs/strategy/PRD_Module_Health.md",
    "PRD_Module_Secure_Vault": "docs/strategy/PRD_Module_Secure_Vault.md",
    "Vault PRD": "docs/strategy/PRD_Module_Secure_Vault.md",
    "Security_Threat_Model": "docs/specs/Security_Threat_Model.md",
    "Threat Model": "docs/specs/Security_Threat_Model.md",
    "coordination/README.md": "coordination/README.md",
    "coordination/README": "coordination/README.md",
    "AGENTS": "AGENTS.md",
    "AGENTS.md": "AGENTS.md",
    "PRD_Template": "docs/templates/PRD_Template.md",
    "PRD Template": "docs/templates/PRD_Template.md",
}

# Documents that are planned but not yet written (paths only, no PR numbers).
# If a planned document materialises on disk, it is automatically treated as present.
PLANNED_DOCS: set[str] = {
    "docs/specs/Security_Threat_Model.md",
}

# Module PRD aliases that must NOT resolve to Core PRD when cited as "this PRD"
# or "PRD v0.x" inside those files.
_MODULE_PRD_FILES: set[str] = {
    "docs/strategy/PRD_Module_Finance.md",
    "docs/strategy/PRD_Module_Health.md",
    "docs/strategy/PRD_Module_Secure_Vault.md",
}

# Regex patterns for document-shaped names that should be reported as UNKNOWN_DOC
# if they aren't in the alias map.
_DOC_SHAPED_PATTERNS = re.compile(
    r"\b(Tech_Spec_\w+|Runbook_\w+|PRD_\w+|\w+_Strategy)\b"
)

SEC_TOKEN_PATTERN = r"(?:[0-9]+(?:\.[0-9]+)*|[Qq]\d+|[Gg]\d+|[Mm]\d+|WP-\d+|Step\s*\d+)"
DASH_PATTERN = r"[\u2013\u2014\-]"

# Patterns indicating a version citation is HISTORICAL rather than stale.
# Governance table rows, change logs, recovery notes, converted/superseded text.
_HISTORICAL_PATTERNS = re.compile(
    r"(?:"
    r"\|\s*v?\d"  # governance table row: starts with | vN
    r"|(?:converted|recovered|superseded|was|renamed|replaced|original|archived|folded)"
    r"|~~"  # struck-through text
    r"|decision\s*log"
    r"|change\s*(?:log|summary)"
    r"|(?:Document\s+)?Governance"
    r")",
    re.IGNORECASE,
)


def _normalise_version(ver: str) -> str:
    """Normalise version strings: v2_0 -> 2.0, v1.2.1 -> 1.2.1, etc."""
    v = ver.lstrip("v").strip()
    v = v.replace("_", ".")
    return v


def read_document_version(file_path: Path) -> str | None:
    """Read a document's current version from its Status line or governance table.

    Looks for patterns like:
      > **Status:** v1.3 — frozen
      > **Status:** DRAFT v0.2
      | v1.3 | 2026-09-17 | ... | (last row of governance table)
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError:
        return None

    # Strategy 1: Look for > **Status:** line (most documents)
    status_re = re.compile(
        r">\s*\*{0,2}Status\*{0,2}:\*{0,2}\s+"
        r"(?:(?:DRAFT|FROZEN|CANONICAL)\s*[^\dv]*?)?"
        r"v?(\d+(?:[._]\d+)+)",
        re.IGNORECASE,
    )
    for line in lines:
        m = status_re.search(line)
        if m:
            return _normalise_version(m.group(1))

    # Strategy 2: Last governance table row with a version
    gov_ver_re = re.compile(r"^\|\s*v?(\d+(?:[._]\d+)*)\s*\|")
    last_gov_ver = None
    for line in lines:
        m = gov_ver_re.match(line)
        if m:
            last_gov_ver = _normalise_version(m.group(1))

    return last_gov_ver


@dataclass
class XRefFinding:
    source_file: str
    line_number: int
    raw_text: str
    target_doc: str | None
    target_section: str | None
    cited_version: str | None
    canonical_version: str | None
    status: str  # VALID | PLANNED_DOC | MISSING_DOC | DANGLING_SECTION | VERSION_STALE
    #              | VERSION_HISTORICAL | VERSION_FORWARD | UNKNOWN_DOC | DANGLING_DOC
    detail: str


class DocIndex:
    """Indexes document headings, sections, anchors, and reads live versions."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.sections_by_doc: dict[str, set[str]] = {}
        self.anchors_by_doc: dict[str, set[str]] = {}
        self.versions_by_doc: dict[str, str] = {}
        self._index_all()

    def _index_all(self) -> None:
        all_md_files = list(self.repo_root.glob("docs/**/*.md"))
        agents_file = self.repo_root / "AGENTS.md"
        if agents_file.exists():
            all_md_files.append(agents_file)
        coord_readme = self.repo_root / "coordination" / "README.md"
        if coord_readme.exists():
            all_md_files.append(coord_readme)

        for path in all_md_files:
            rel_path = path.relative_to(self.repo_root).as_posix()
            sections: set[str] = set()
            anchors: set[str] = set()

            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        if not line.startswith("#"):
                            continue

                        # Match numbered headings: e.g. ## 4. Invariants or ### 3.11 resource_lock
                        m = re.match(r"^#+\s+([0-9]+(?:\.[0-9]+)*)(?:\.|\b)?", line)
                        if m:
                            sec_num = m.group(1)
                            sections.add(sec_num)
                            parts = sec_num.split(".")
                            for i in range(1, len(parts)):
                                sections.add(".".join(parts[:i]))

                        # Match query / gate / step / WP / milestone identifiers
                        id_matches = re.findall(
                            r"\b(Q\d+|G\d+|Step\s+\d+|WP-\d+|M\d+|P\d+)\b",
                            line,
                            re.IGNORECASE,
                        )
                        for idm in id_matches:
                            norm_id = re.sub(r"\s+", " ", idm).strip()
                            sections.add(norm_id)
                            sections.add(norm_id.upper())

                        # Generate GitHub-style anchor slug
                        heading_text = re.sub(r"^#+\s+", "", line.strip())
                        slug = (
                            re.sub(r"[^\w\- ]", "", heading_text)
                            .strip()
                            .lower()
                            .replace(" ", "-")
                        )
                        if slug:
                            anchors.add(slug)

                if rel_path.endswith("Tech_Spec_Financial_Transaction_Safety.md"):
                    for g in ["G1", "G2", "G3", "G4", "G5"]:
                        sections.add(g)

                self.sections_by_doc[rel_path] = sections
                self.anchors_by_doc[rel_path] = anchors
            except OSError:
                pass

            # Read live version from document
            ver = read_document_version(path)
            if ver:
                self.versions_by_doc[rel_path] = ver


DOC_ALIASES_LOWER = {k.lower(): v for k, v in DOC_ALIASES.items()}
GENERIC_DOC_WORDS = {
    "data model",
    "roadmap",
    "agents",
    "runbook",
    "execution plan",
    "threat model",
    "prd",
    "master prd",
    "vision journey",
    "vision parking lot",
    "workstation setup",
    "local agent setup",
    "dpi integration primer",
    "dpi rate limits",
}


def normalize_doc_name(raw_name: str) -> str | None:
    """Normalize a raw document name or alias to a canonical repository-relative path."""
    clean = raw_name.strip().replace("\\", "/")
    clean = re.sub(r"\.docx?$", "", clean, flags=re.IGNORECASE)
    clean_no_ext = re.sub(r"\.md$", "", clean, flags=re.IGNORECASE)
    # Strip trailing version or annotations like " v1.2 (frozen)" or "_v2_1"
    clean_base = re.sub(
        r"[_\s]+v?\d+(?:[._]\d+)*.*$", "", clean_no_ext, flags=re.IGNORECASE
    ).strip()

    for candidate in [clean, clean_no_ext, clean_base]:
        if candidate in DOC_ALIASES:
            return DOC_ALIASES[candidate]
        c_low = candidate.lower()
        if c_low in DOC_ALIASES_LOWER:
            return DOC_ALIASES_LOWER[c_low]
        base_low = os.path.basename(candidate).lower()
        if base_low in DOC_ALIASES_LOWER:
            return DOC_ALIASES_LOWER[base_low]

    if clean.endswith(".md") and os.path.exists(clean):
        return clean

    return None


def extract_section_tokens(sec_string: str) -> list[str]:
    """Extract individual section tokens from a section string or range."""
    # Split ranges like 3.2-3.4 or 6-7
    dash_range_regex = re.compile(
        rf"([0-9]+(?:\.[0-9]+)*)\s*{DASH_PATTERN}\s*([0-9]+(?:\.[0-9]+)*)"
    )
    tokens: list[str] = []
    for m in dash_range_regex.finditer(sec_string):
        start_s, end_s = m.group(1), m.group(2)
        tokens.append(start_s)
        tokens.append(end_s)
        # If both are integers like 6-7, expand range
        if start_s.isdigit() and end_s.isdigit():
            s_int, e_int = int(start_s), int(end_s)
            if s_int < e_int and (e_int - s_int) <= 20:
                for val in range(s_int + 1, e_int):
                    tokens.append(str(val))

    raw_tokens = re.findall(SEC_TOKEN_PATTERN, sec_string, re.IGNORECASE)
    for t in raw_tokens:
        norm = re.sub(r"\s+", " ", t).strip().rstrip(".,;:")
        if norm and norm not in tokens:
            tokens.append(norm)
    return tokens


def split_clauses_safely(line: str) -> list[tuple[int, int]]:
    """Split line into (start, end) clause spans on delimiters ·, •, ;, |
    only when outside parentheses and code backticks."""
    spans: list[tuple[int, int]] = []
    start = 0
    paren_depth = 0
    in_backtick = False

    for i, ch in enumerate(line):
        if ch == "`":
            in_backtick = not in_backtick
        elif not in_backtick:
            if ch in "([":
                paren_depth += 1
            elif ch in ")]":
                paren_depth = max(0, paren_depth - 1)
            elif paren_depth == 0 and ch in "·•;|":
                if i > start:
                    spans.append((start, i))
                start = i + 1

    if start < len(line):
        spans.append((start, len(line)))
    return spans


def _is_sentence_start(line: str, match_start: int) -> bool:
    """Check if a match position is at the start of a sentence.

    A bare §n at the start of a sentence should mean the current file,
    not inherit a document from a previous clause.
    """
    before = line[:match_start].rstrip()
    if not before:
        return True
    if before[-1] in ".!?:":
        return True
    # Start of a list item
    return bool(re.match(r"^\s*[-*]\s*$", before) or re.match(r"^\s*\d+\.\s*$", before))


def find_references_in_line(
    line: str,
    current_doc: str,
    _line_no: int,
) -> list[tuple[str, str | None, str | None, str | None, str]]:
    """Extract references from a line of text.

    Returns:
        List of (raw_text, doc_identifier, section_string, version_string, ref_type)
    """
    refs: list[tuple[str, str | None, str | None, str | None, str]] = []
    matched_spans: list[tuple[int, int]] = []

    # 1. Markdown file links: [text](path/to/doc.md#anchor)
    link_regex = re.compile(r"\[([^\]]+)\]\(([^)#\s]+\.md)(?:#([a-zA-Z0-9_\-]+))?\)")
    for m in link_regex.finditer(line):
        link_target = m.group(2)
        anchor = m.group(3)
        refs.append((m.group(0), link_target, anchor, None, "markdown_link"))
        matched_spans.append((m.start(), m.end()))

    # Check if line is a Markdown table row with forward doc scoping per cell
    table_cell_docs: list[str | None] = []
    is_table = line.strip().startswith("|") and line.strip().endswith("|")
    if is_table:
        cells = [c.strip() for c in line.strip().split("|")[1:-1]]
        last_doc: str | None = None
        for cell in cells:
            clean_cell = re.sub(r"[`*\[\]]", "", cell).strip()
            norm = normalize_doc_name(clean_cell)
            if norm:
                last_doc = norm
            else:
                m_path = re.search(r"((?:docs/[^\s|`*()]+|AGENTS)\.md)", cell)
                if m_path:
                    norm_p = normalize_doc_name(m_path.group(1))
                    if norm_p:
                        last_doc = norm_p
            table_cell_docs.append(last_doc)

    sorted_aliases = sorted(DOC_ALIASES.keys(), key=len, reverse=True)
    alias_pattern = "|".join(re.escape(a) for a in sorted_aliases)

    # Check for "§ X of <Doc>" pattern first: e.g. §3.3 of Master PRD
    sec_of_doc_regex = re.compile(
        rf"(?:§|section)\s*({SEC_TOKEN_PATTERN})\s+of\s+({alias_pattern})",
        re.IGNORECASE,
    )
    for m in sec_of_doc_regex.finditer(line):
        sec_tok = m.group(1)
        doc_tok = m.group(2)
        refs.append((m.group(0), doc_tok, sec_tok, None, "doc_section"))
        matched_spans.append((m.start(), m.end()))

    # 2. Segment line into clauses by mid-dots (·, •), semicolons (;), or table cells (|)
    doc_cite_regex = re.compile(
        rf"\b({alias_pattern})(?:[_\s]+v?(\d+(?:[._]\d+)*))?(?:\.docx?|\.md)?(?:\b|_)",
        re.IGNORECASE,
    )

    # Regex to find section references inside a scope
    item_tok = rf"(?:§\s*)?{SEC_TOKEN_PATTERN}"
    range_tok = rf"{item_tok}(?:\s*{DASH_PATTERN}\s*{item_tok})?"
    chained_tok = (
        rf"(?:,\s*§\s*{SEC_TOKEN_PATTERN}"
        rf"|,\s*{SEC_TOKEN_PATTERN}(?!\s*(?:%|[a-zA-Z]))"
        rf"|\s*(?:and|or|\+)\s*(?:§\s*)?{SEC_TOKEN_PATTERN})"
    )
    sec_chain_regex = re.compile(
        rf"(?:§|sections?\s+|query\s+|queries\s+)\s*({range_tok}(?:{chained_tok})*)",
        re.IGNORECASE,
    )
    # Gates G1-G5 specifically (never match random numbers as gates)
    gate_regex = re.compile(
        r"\b(?:gates?\s+)?(G[1-5](?:\s*[\u2013\-]\s*G[1-5])?)\b",
        re.IGNORECASE,
    )

    # Split into clauses by major delimiters safely outside parentheses
    clause_spans = split_clauses_safely(line)

    line_last_doc: str | None = None
    last_cell_idx: int = -1

    for c_start, c_end in clause_spans:
        clause = line[c_start:c_end]
        if not clause.strip():
            continue

        if is_table:
            # Count pipes before c_start to determine exact cell index
            cell_idx = line[:c_start].count("|") - 1
            if cell_idx != last_cell_idx:
                last_cell_idx = cell_idx
                line_last_doc = (
                    table_cell_docs[cell_idx]
                    if cell_idx >= 0 and cell_idx < len(table_cell_docs)
                    else None
                )

        clause_default_doc = line_last_doc or current_doc

        # Find document citations within this clause
        doc_matches: list[tuple[int, int, str, str | None]] = []
        for dm in doc_cite_regex.finditer(clause):
            global_start = c_start + dm.start()
            global_end = c_start + dm.end()
            if any(s <= global_start and global_end <= e for s, e in matched_spans):
                continue
            d_alias = dm.group(1)
            d_ver = dm.group(2)

            # Filter generic words like "roadmap" or "data model" when used as normal prose
            if d_alias.lower() in GENERIC_DOC_WORDS:
                has_ext = clause[dm.end() : dm.end() + 3].lower() == ".md"
                has_ver = d_ver is not None
                is_formal = any(
                    d_alias.startswith(p) for p in ["Tech_Spec_", "PRD_", "Runbook_"]
                )
                has_sec = bool(re.search(r"^\s*(?:§|sections?\s+)", clause[dm.end() :]))
                is_backticked = (
                    dm.start() > 0
                    and clause[dm.start() - 1] == "`"
                    and dm.end() < len(clause)
                    and clause[dm.end()] == "`"
                )
                if not (has_ext or has_ver or is_formal or has_sec or is_backticked):
                    continue

            # Inside a module PRD, "PRD v0.x" or "this PRD" should refer to
            # the module PRD itself, not to the Core PRD.
            if (
                current_doc in _MODULE_PRD_FILES
                and d_alias.upper() == "PRD"
                and d_ver
                and _normalise_version(d_ver).startswith("0.")
            ):
                doc_matches.append((dm.start(), dm.end(), current_doc, d_ver))
            else:
                doc_matches.append((dm.start(), dm.end(), d_alias, d_ver))

        if doc_matches:
            # We have one or more document citations in this clause
            for d_idx, (dm_start, dm_end, d_alias, d_ver) in enumerate(doc_matches):
                # Scope of this doc runs until next doc match or end of clause
                scope_start = dm_start
                next_doc_pos = (
                    doc_matches[d_idx + 1][0]
                    if d_idx + 1 < len(doc_matches)
                    else len(clause)
                )
                scope_end = next_doc_pos

                # If this doc was cited inside parentheses, do not let its scope leak out of ')'
                pre_doc = clause[:dm_start]
                if pre_doc.count("(") > pre_doc.count(")"):
                    close_p = clause.find(")", dm_end)
                    if close_p != -1 and close_p < scope_end:
                        scope_end = close_p + 1

                scope_text = clause[scope_start:scope_end]

                # Find all sections in this doc's scope
                found_sec_in_scope = False
                for sm in sec_chain_regex.finditer(scope_text):
                    g_start = c_start + scope_start + sm.start()
                    g_end = c_start + scope_start + sm.end()
                    if any(s <= g_start and g_end <= e for s, e in matched_spans):
                        continue
                    sec_str = sm.group(1)
                    raw_str = sm.group(0)
                    refs.append((raw_str, d_alias, sec_str, d_ver, "doc_section"))
                    matched_spans.append((g_start, g_end))
                    found_sec_in_scope = True

                for gm in gate_regex.finditer(scope_text):
                    g_start = c_start + scope_start + gm.start()
                    g_end = c_start + scope_start + gm.end()
                    if any(s <= g_start and g_end <= e for s, e in matched_spans):
                        continue
                    sec_str = gm.group(1)
                    raw_str = gm.group(0)
                    # Pre-execution gates G1-G5 are canonically defined in FTS §2.2
                    fts_doc = "docs/specs/Tech_Spec_Financial_Transaction_Safety.md"
                    refs.append((raw_str, fts_doc, sec_str, d_ver, "doc_section"))
                    matched_spans.append((g_start, g_end))
                    found_sec_in_scope = True

                # If no section was attached in scope, record document reference itself
                if not found_sec_in_scope:
                    g_start = c_start + dm_start
                    g_end = c_start + dm_end
                    if not any(s <= g_start and g_end <= e for s, e in matched_spans):
                        raw_str = clause[dm_start:dm_end]
                        refs.append((raw_str, d_alias, None, d_ver, "doc_only"))
                        matched_spans.append((g_start, g_end))

            line_last_doc = normalize_doc_name(doc_matches[-1][2]) or doc_matches[-1][2]

            # Any section in this clause before the first doc citation is bare
            first_doc_start = doc_matches[0][0]
            pre_text = clause[:first_doc_start]
            for sm in sec_chain_regex.finditer(pre_text):
                g_start = c_start + sm.start()
                g_end = c_start + sm.end()
                if any(s <= g_start and g_end <= e for s, e in matched_spans):
                    continue
                sec_str = sm.group(1)
                raw_str = sm.group(0)
                # If at sentence start, use current_doc; otherwise inherit
                if _is_sentence_start(line, c_start + sm.start()):
                    fallback = current_doc
                else:
                    fallback = clause_default_doc
                refs.append((raw_str, fallback, sec_str, None, "bare_section"))
                matched_spans.append((g_start, g_end))

            for gm in gate_regex.finditer(pre_text):
                g_start = c_start + gm.start()
                g_end = c_start + gm.end()
                if any(s <= g_start and g_end <= e for s, e in matched_spans):
                    continue
                sec_str = gm.group(1)
                raw_str = gm.group(0)
                fts_doc = "docs/specs/Tech_Spec_Financial_Transaction_Safety.md"
                refs.append((raw_str, fts_doc, sec_str, None, "doc_section"))
                matched_spans.append((g_start, g_end))

        else:
            # No document citation in this clause: all sections are bare
            for sm in sec_chain_regex.finditer(clause):
                g_start = c_start + sm.start()
                g_end = c_start + sm.end()
                if any(s <= g_start and g_end <= e for s, e in matched_spans):
                    continue
                sec_str = sm.group(1)
                raw_str = sm.group(0)
                # If at sentence start, use current_doc; otherwise inherit
                if _is_sentence_start(line, c_start + sm.start()):
                    fallback = current_doc
                else:
                    fallback = clause_default_doc
                refs.append((raw_str, fallback, sec_str, None, "bare_section"))
                matched_spans.append((g_start, g_end))

            for gm in gate_regex.finditer(clause):
                g_start = c_start + gm.start()
                g_end = c_start + gm.end()
                if any(s <= g_start and g_end <= e for s, e in matched_spans):
                    continue
                sec_str = gm.group(1)
                raw_str = gm.group(0)
                fts_doc = "docs/specs/Tech_Spec_Financial_Transaction_Safety.md"
                refs.append((raw_str, fts_doc, sec_str, None, "doc_section"))
                matched_spans.append((g_start, g_end))

    return refs


def _classify_version_mismatch(
    source_line: str,
    cited_ver: str,
    canon_ver: str,
) -> str:
    """Classify a version mismatch as HISTORICAL, FORWARD, or STALE.

    HISTORICAL: the citation is in a Document Governance table row, a change log,
                a struck-through passage, or text about conversion/recovery/superseding.
    FORWARD:    the cited version is higher than the current (a plan, not an error).
    STALE:      everything else (a reference that should be updated).
    """
    norm_cited = _normalise_version(cited_ver)
    norm_canon = _normalise_version(canon_ver)

    # Forward: cited version > canonical version
    cited_parts = [int(x) for x in norm_cited.split(".") if x.isdigit()]
    canon_parts = [int(x) for x in norm_canon.split(".") if x.isdigit()]
    if cited_parts > canon_parts:
        return "VERSION_FORWARD"

    # Historical: governance table, change log, struck-through, converted/recovered
    if _HISTORICAL_PATTERNS.search(source_line):
        return "VERSION_HISTORICAL"

    return "VERSION_STALE"


def check_all_references(repo_root: Path) -> list[XRefFinding]:
    """Scan all documentation files and validate cross-references."""
    index = DocIndex(repo_root)
    findings: list[XRefFinding] = []
    # Track (source_file, line_number, target_doc, target_section) for dedup
    seen_keys: set[tuple[str, int, str | None, str | None]] = set()

    all_files = list(repo_root.glob("docs/**/*.md"))
    agents_file = repo_root / "AGENTS.md"
    if agents_file.exists():
        all_files.append(agents_file)

    for file_path in all_files:
        rel_src = file_path.relative_to(repo_root).as_posix()
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except OSError as err:
            findings.append(
                XRefFinding(
                    source_file=rel_src,
                    line_number=1,
                    raw_text="",
                    target_doc=None,
                    target_section=None,
                    cited_version=None,
                    canonical_version=None,
                    status="DANGLING_DOC",
                    detail=f"Could not open file: {err}",
                )
            )
            continue

        in_code_block = False
        for line_no, line in enumerate(lines, start=1):
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue

            # Also scan for document-shaped names that aren't in the alias map
            for dsm in _DOC_SHAPED_PATTERNS.finditer(line):
                doc_name = dsm.group(1)
                if normalize_doc_name(doc_name) is None:
                    dedup_key = (rel_src, line_no, doc_name, None)
                    if dedup_key not in seen_keys:
                        seen_keys.add(dedup_key)
                        findings.append(
                            XRefFinding(
                                source_file=rel_src,
                                line_number=line_no,
                                raw_text=doc_name,
                                target_doc=doc_name,
                                target_section=None,
                                cited_version=None,
                                canonical_version=None,
                                status="UNKNOWN_DOC",
                                detail=f"Document-shaped name '{doc_name}' not in alias map",
                            )
                        )

            extracted = find_references_in_line(line, rel_src, line_no)
            for raw_text, raw_doc, raw_sec, cited_ver, ref_type in extracted:
                if not raw_doc:
                    continue

                target_path: str | None = None
                if ref_type == "markdown_link":
                    src_dir = (repo_root / rel_src).parent
                    resolved = (src_dir / raw_doc).resolve()
                    try:
                        target_path = resolved.relative_to(
                            repo_root.resolve()
                        ).as_posix()
                    except ValueError:
                        target_path = raw_doc
                else:
                    target_path = normalize_doc_name(raw_doc)

                # Deduplication: skip if we already recorded this exact finding
                dedup_key = (rel_src, line_no, target_path or raw_doc, raw_sec)
                if dedup_key in seen_keys:
                    continue
                seen_keys.add(dedup_key)

                # 1. Document Existence Check
                if not target_path:
                    findings.append(
                        XRefFinding(
                            source_file=rel_src,
                            line_number=line_no,
                            raw_text=raw_text,
                            target_doc=raw_doc,
                            target_section=raw_sec,
                            cited_version=cited_ver,
                            canonical_version=None,
                            status="DANGLING_DOC",
                            detail=f"Unrecognized or unresolved document identifier: '{raw_doc}'",
                        )
                    )
                    continue

                # Check if target file exists on disk
                full_target_file = repo_root / target_path
                if not full_target_file.exists():
                    # Is this a planned document?
                    if target_path in PLANNED_DOCS:
                        findings.append(
                            XRefFinding(
                                source_file=rel_src,
                                line_number=line_no,
                                raw_text=raw_text,
                                target_doc=target_path,
                                target_section=raw_sec,
                                cited_version=cited_ver,
                                canonical_version=None,
                                status="PLANNED_DOC",
                                detail=f"{target_path} is a planned document (not yet written)",
                            )
                        )
                    else:
                        findings.append(
                            XRefFinding(
                                source_file=rel_src,
                                line_number=line_no,
                                raw_text=raw_text,
                                target_doc=target_path,
                                target_section=raw_sec,
                                cited_version=cited_ver,
                                canonical_version=None,
                                status="MISSING_DOC",
                                detail=f"Target file does not exist on disk: '{target_path}'",
                            )
                        )
                    continue

                # 2. Version Mismatch Check — read live version from document
                canon_ver = index.versions_by_doc.get(target_path)
                if cited_ver and canon_ver:
                    norm_cited = _normalise_version(cited_ver)
                    norm_canon = _normalise_version(canon_ver)
                    if norm_cited != norm_canon:
                        mismatch_status = _classify_version_mismatch(
                            line, cited_ver, canon_ver
                        )
                        findings.append(
                            XRefFinding(
                                source_file=rel_src,
                                line_number=line_no,
                                raw_text=raw_text,
                                target_doc=target_path,
                                target_section=raw_sec,
                                cited_version=norm_cited,
                                canonical_version=norm_canon,
                                status=mismatch_status,
                                detail=(
                                    f"Cited v{norm_cited}, but "
                                    f"{os.path.basename(target_path)} status is v{norm_canon}"
                                ),
                            )
                        )

                # 3. Section / Anchor Existence Check
                if not raw_sec:
                    findings.append(
                        XRefFinding(
                            source_file=rel_src,
                            line_number=line_no,
                            raw_text=raw_text,
                            target_doc=target_path,
                            target_section=None,
                            cited_version=cited_ver,
                            canonical_version=canon_ver,
                            status="VALID",
                            detail="Document reference valid",
                        )
                    )
                    continue

                known_sections = index.sections_by_doc.get(target_path, set())
                known_anchors = index.anchors_by_doc.get(target_path, set())

                if ref_type == "markdown_link":
                    if raw_sec in known_anchors or raw_sec in known_sections:
                        findings.append(
                            XRefFinding(
                                source_file=rel_src,
                                line_number=line_no,
                                raw_text=raw_text,
                                target_doc=target_path,
                                target_section=raw_sec,
                                cited_version=cited_ver,
                                canonical_version=canon_ver,
                                status="VALID",
                                detail="Markdown link and anchor valid",
                            )
                        )
                    else:
                        findings.append(
                            XRefFinding(
                                source_file=rel_src,
                                line_number=line_no,
                                raw_text=raw_text,
                                target_doc=target_path,
                                target_section=raw_sec,
                                cited_version=cited_ver,
                                canonical_version=canon_ver,
                                status="DANGLING_SECTION",
                                detail=f"Anchor '#{raw_sec}' not found in {target_path}",
                            )
                        )
                    continue

                tokens = extract_section_tokens(raw_sec)
                missing_secs = []
                for s in tokens:
                    if s not in known_sections and s.upper() not in known_sections:
                        missing_secs.append(s)

                if missing_secs:
                    # Check if all missing sections actually exist in the citing document itself
                    known_self = index.sections_by_doc.get(rel_src, set())
                    if rel_src != target_path and all(
                        s in known_self or s.upper() in known_self for s in missing_secs
                    ):
                        findings.append(
                            XRefFinding(
                                source_file=rel_src,
                                line_number=line_no,
                                raw_text=raw_text,
                                target_doc=rel_src,
                                target_section=raw_sec,
                                cited_version=cited_ver,
                                canonical_version=index.versions_by_doc.get(rel_src),
                                status="VALID",
                                detail="Section reference valid (self-reference in current document)",
                            )
                        )
                        continue

                    findings.append(
                        XRefFinding(
                            source_file=rel_src,
                            line_number=line_no,
                            raw_text=raw_text,
                            target_doc=target_path,
                            target_section=raw_sec,
                            cited_version=cited_ver,
                            canonical_version=canon_ver,
                            status="DANGLING_SECTION",
                            detail=f"Section(s) {missing_secs} not found in {target_path}",
                        )
                    )
                else:
                    findings.append(
                        XRefFinding(
                            source_file=rel_src,
                            line_number=line_no,
                            raw_text=raw_text,
                            target_doc=target_path,
                            target_section=raw_sec,
                            cited_version=cited_ver,
                            canonical_version=canon_ver,
                            status="VALID",
                            detail="Section reference valid",
                        )
                    )

    return findings


def print_report(findings: list[XRefFinding], verbose: bool = False) -> None:
    """Print formatted summary and categorized issues."""
    valid = [f for f in findings if f.status == "VALID"]
    planned = [f for f in findings if f.status == "PLANNED_DOC"]
    missing_docs = [f for f in findings if f.status == "MISSING_DOC"]
    unknown_docs = [f for f in findings if f.status == "UNKNOWN_DOC"]
    stale = [f for f in findings if f.status == "VERSION_STALE"]
    historical = [f for f in findings if f.status == "VERSION_HISTORICAL"]
    forward = [f for f in findings if f.status == "VERSION_FORWARD"]
    dangling_sections = [f for f in findings if f.status == "DANGLING_SECTION"]
    dangling_docs = [f for f in findings if f.status == "DANGLING_DOC"]

    total = len(findings)
    print("======================================================================")
    print("          FamilyLifeOS Documentation Cross-Reference Sweep            ")
    print("======================================================================\n")
    print(f"Total References Scanned: {total}")
    print(f"  - Valid References:     {len(valid)}")
    print(f"  - Planned Documents:    {len(planned)}")
    print(f"  - Missing Documents:    {len(missing_docs)}")
    print(f"  - Unknown Documents:    {len(unknown_docs)}")
    print(f"  - Version Stale:        {len(stale)}")
    print(f"  - Version Historical:   {len(historical)}")
    print(f"  - Version Forward:      {len(forward)}")
    print(f"  - Dangling Sections:    {len(dangling_sections)}")
    print(f"  - Dangling Documents:   {len(dangling_docs)}")
    print("----------------------------------------------------------------------\n")

    if planned:
        print(f"### Planned Document References ({len(planned)} references)")
        # Group by target doc
        by_doc: dict[str, list[XRefFinding]] = {}
        for f in planned:
            by_doc.setdefault(f.target_doc or "unknown", []).append(f)
        for doc, doc_findings in by_doc.items():
            print(f"  Target: {doc} ({doc_findings[0].detail})")
            for f in doc_findings[:5]:
                print(f"    [{f.source_file}:{f.line_number}] '{f.raw_text}'")
            if len(doc_findings) > 5:
                print(f"    ... and {len(doc_findings) - 5} more references")
        print()

    if missing_docs:
        print(f"### Missing Documents ({len(missing_docs)} references)")
        for f in missing_docs:
            print(f"  [{f.source_file}:{f.line_number}] '{f.raw_text}' -> {f.detail}")
        print()

    if unknown_docs:
        print(f"### Unknown Document Names ({len(unknown_docs)} references)")
        for f in unknown_docs:
            print(f"  [{f.source_file}:{f.line_number}] '{f.raw_text}' -> {f.detail}")
        print()

    if stale:
        print(
            f"### Version Stale ({len(stale)} references citing outdated versions — findings)"
        )
        for f in stale:
            print(f"  [{f.source_file}:{f.line_number}] '{f.raw_text}' -> {f.detail}")
        print()

    if historical:
        print(
            f"### Version Historical ({len(historical)} references in governance/change log — not findings)"
        )
        if verbose:
            for f in historical:
                print(
                    f"  [{f.source_file}:{f.line_number}] '{f.raw_text}' -> {f.detail}"
                )
        else:
            print(
                f"  (use --verbose to list all {len(historical)} historical citations)"
            )
        print()

    if forward:
        print(
            f"### Version Forward ({len(forward)} references citing future versions — not findings)"
        )
        for f in forward:
            print(f"  [{f.source_file}:{f.line_number}] '{f.raw_text}' -> {f.detail}")
        print()

    if dangling_docs:
        print(f"### Dangling Documents ({len(dangling_docs)} unresolved documents)")
        for f in dangling_docs:
            print(f"  [{f.source_file}:{f.line_number}] '{f.raw_text}' -> {f.detail}")
        print()

    if dangling_sections:
        print(
            f"### Dangling Sections ({len(dangling_sections)} missing section headings)"
        )
        for f in dangling_sections:
            print(f"  [{f.source_file}:{f.line_number}] '{f.raw_text}' -> {f.detail}")
        print()

    if verbose and valid:
        print(f"### Valid References Sample (first 10 of {len(valid)})")
        for f in valid[:10]:
            print(
                f"  [{f.source_file}:{f.line_number}] '{f.raw_text}' -> {f.target_doc}"
            )
        print()


def run_selftest() -> bool:
    """Build probe files in a temp directory and verify detection counts.

    Creates a minimal repo structure with known references and asserts the tool
    catches invented sections, validates real ones, and classifies version mismatches.
    Returns True on pass, False on failure.
    """
    tmpdir = Path(tempfile.mkdtemp(prefix="xref_selftest_"))
    try:
        # Create minimal directory structure
        (tmpdir / "docs" / "specs").mkdir(parents=True)
        (tmpdir / "docs" / "strategy").mkdir(parents=True)
        (tmpdir / "docs" / "runbooks").mkdir(parents=True)

        # Create a minimal Data Model document with headings
        (tmpdir / "docs" / "specs" / "Data_Model_Schema.md").write_text(
            "# Data Model Schema\n"
            "> **Status:** v1.3 — frozen\n\n"
            "## 1. Overview\n\n"
            "## 3. Tables\n\n"
            "### 3.4 users\n\n"
            "### 3.7 supervisor_sessions\n\n"
            "### 3.9 resource_lock\n\n",
            encoding="utf-8",
        )

        # Create FTS with headings
        (
            tmpdir / "docs" / "specs" / "Tech_Spec_Financial_Transaction_Safety.md"
        ).write_text(
            "# Financial Transaction Safety\n"
            "> **Status:** v1.2 — frozen\n\n"
            "## 2. Architecture\n\n"
            "### 2.2 Pre-execution gates\n\n"
            "## 6. Healer\n\n"
            "### 6.4 Idempotency\n\n",
            encoding="utf-8",
        )

        # Create Consent Manager with headings
        (tmpdir / "docs" / "specs" / "Tech_Spec_Consent_Manager.md").write_text(
            "# Consent Manager\n"
            "> **Status:** v1.3 — frozen\n\n"
            "## 2. Consent Model\n\n"
            "### 2.6 Proxy consent\n\n"
            "## 5. CONSENT_REVERIFY\n\n",
            encoding="utf-8",
        )

        # Create Module Registry
        (tmpdir / "docs" / "specs" / "Tech_Spec_Module_Registry.md").write_text(
            "# Module Registry\n"
            "> **Status:** v1.1 — review\n\n"
            "## 7. Isolation\n\n"
            "### 7.3 RBAC\n\n",
            encoding="utf-8",
        )

        # Create Runbook
        (tmpdir / "docs" / "runbooks" / "Runbook_DPI_Rate_Limits.md").write_text(
            "# DPI Rate Limits Runbook\n"
            "> **Status:** v1.2 — frozen\n\n"
            "## 2. Redis Budget\n\n"
            "### 2.4 Fail-open\n\n"
            "## 8. Circuit Breakers\n\n"
            "### 8.3 Probes\n\n",
            encoding="utf-8",
        )

        # Create NFR
        (tmpdir / "docs" / "specs" / "NFR_Specs.md").write_text(
            "# NFR Specs\n> **Status:** v2.2 — canonical\n\n## 9. Security\n\n",
            encoding="utf-8",
        )

        # Create a Core PRD
        (tmpdir / "docs" / "strategy" / "PRD_FamilyLifeOS_Core.md").write_text(
            "# Core PRD\n"
            "> **Status:** v2.2 — canonical\n\n"
            "## 4. Requirements\n\n"
            "### 4.8 Spec map\n\n"
            "## 5. Shared Services\n\n",
            encoding="utf-8",
        )

        # Create Master Context
        (tmpdir / "docs" / "strategy" / "Master_Context.md").write_text(
            "# Master Context\n"
            "> **Status:** v2.1 — canonical\n\n"
            "## 3. Architecture\n\n"
            "### 3.3 Stack\n\n",
            encoding="utf-8",
        )

        # Create Supervisor FSM
        (
            tmpdir / "docs" / "specs" / "Tech_Spec_Supervisor_State_Machine.md"
        ).write_text(
            "# Supervisor State Machine\n"
            "> **Status:** v2.1 — canonical\n\n"
            "## 4. States\n\n",
            encoding="utf-8",
        )

        # AGENTS.md at root
        (tmpdir / "AGENTS.md").write_text(
            "# AGENTS\n\n## 4. Invariants\n\n## 6. Working rules\n\n",
            encoding="utf-8",
        )

        # Probe file with test references
        (tmpdir / "docs" / "specs" / "probe_test.md").write_text(
            "# Probe Test\n\n"
            # 5 invented sections (should be DANGLING_SECTION)
            "Reference FTS §99.9 for something.\n"
            "Reference DM §3.99 for something.\n"
            "Reference Data Model §42 for something.\n"
            "Reference MR §7.9 for something.\n"
            "Reference CM §12.7 for something.\n"
            # 2 real sections (should be VALID)
            "Reference RB §2.4 for fail-open.\n"
            "Reference Consent Manager §2.6 for proxy.\n"
            # Version mismatch: historical (governance table row)
            "| v1.1 | 2026-01-01 | Initial | with CM v1.1 §5 |\n"
            # Version mismatch: stale
            "See NFR v2.1 §9 for details.\n"
            # Version mismatch: forward
            "This will be in DM v2.0 §1.\n"
            # Chained section ref
            "DM v1.3 §3.4, §3.7–§3.9\n"
            # Unknown doc-shaped name
            "See Tech_Spec_Nonexistent §3.\n"
            # Bare §n at start of sentence (should be current doc)
            "§4 defines the states.\n",
            encoding="utf-8",
        )

        # Run the checker
        result = check_all_references(tmpdir)

        # Filter to only probe file findings
        probe = [f for f in result if f.source_file.endswith("probe_test.md")]

        dangling_secs = [f for f in probe if f.status == "DANGLING_SECTION"]
        valid_secs = [
            f for f in probe if f.status == "VALID" and f.target_section is not None
        ]
        stale_v = [f for f in probe if f.status == "VERSION_STALE"]
        historical_v = [f for f in probe if f.status == "VERSION_HISTORICAL"]
        forward_v = [f for f in probe if f.status == "VERSION_FORWARD"]
        unknown = [f for f in probe if f.status == "UNKNOWN_DOC"]

        errors: list[str] = []

        # 5 invented sections should be dangling
        if len(dangling_secs) < 5:
            errors.append(
                f"Expected >=5 dangling sections, got {len(dangling_secs)}: "
                f"{[(f.raw_text, f.target_doc) for f in dangling_secs]}"
            )

        # At least 2 real sections should be valid
        if len(valid_secs) < 2:
            errors.append(
                f"Expected >=2 valid section refs, got {len(valid_secs)}: "
                f"{[(f.raw_text, f.target_doc) for f in valid_secs]}"
            )

        # At least 1 stale version mismatch
        if len(stale_v) < 1:
            errors.append(
                f"Expected >=1 VERSION_STALE, got {len(stale_v)}: "
                f"{[(f.raw_text, f.detail) for f in stale_v]}"
            )

        # At least 1 historical version mismatch
        if len(historical_v) < 1:
            errors.append(
                f"Expected >=1 VERSION_HISTORICAL, got {len(historical_v)}: "
                f"{[(f.raw_text, f.detail) for f in historical_v]}"
            )

        # At least 1 forward version mismatch
        if len(forward_v) < 1:
            errors.append(
                f"Expected >=1 VERSION_FORWARD, got {len(forward_v)}: "
                f"{[(f.raw_text, f.detail) for f in forward_v]}"
            )

        # At least 1 unknown doc
        if len(unknown) < 1:
            errors.append(
                f"Expected >=1 UNKNOWN_DOC, got {len(unknown)}: "
                f"{[(f.raw_text, f.detail) for f in unknown]}"
            )

        # Chained ref: DM v1.3 §3.4, §3.7–§3.9 should all validate
        chained_valid = [
            f
            for f in probe
            if f.status == "VALID"
            and f.target_doc
            and f.target_doc.endswith("Data_Model_Schema.md")
            and f.target_section
            and any(s in f.target_section for s in ["3.4", "3.7", "3.9"])
        ]
        if len(chained_valid) < 1:
            errors.append(
                f"Expected chained DM §3.4, §3.7–§3.9 to validate, got {len(chained_valid)}"
            )

        if errors:
            print("Selftest FAILED:")
            for e in errors:
                print(f"  - {e}")
            return False

        print("Selftest PASSED.")
        print(f"  Probe findings: {len(probe)} total")
        print(f"    Dangling sections: {len(dangling_secs)}")
        print(f"    Valid sections:    {len(valid_secs)}")
        print(f"    Version stale:     {len(stale_v)}")
        print(f"    Version historical:{len(historical_v)}")
        print(f"    Version forward:   {len(forward_v)}")
        print(f"    Unknown docs:      {len(unknown)}")
        return True

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Scan FamilyLifeOS documentation for cross-reference integrity."
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Root directory of the repository (default: .)",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed valid reference samples and historical version citations",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with non-zero status if dangling references or stale versions are found",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="Run internal self-test with probe references and exit",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    args = parse_args(argv)

    if args.selftest:
        return 0 if run_selftest() else 1

    root_path = Path(args.root).resolve()

    if not root_path.exists():
        sys.stderr.write(f"Error: Repository root '{args.root}' does not exist.\n")
        return 1

    findings = check_all_references(root_path)

    if args.format == "json":
        output_data: dict[str, Any] = {
            "total": len(findings),
            "findings": [asdict(f) for f in findings],
        }
        print(json.dumps(output_data, indent=2))
    else:
        print_report(findings, verbose=args.verbose)

    dangling = [f for f in findings if f.status in ("DANGLING_DOC", "DANGLING_SECTION")]
    stale = [f for f in findings if f.status == "VERSION_STALE"]
    if args.strict and (dangling or stale):
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
