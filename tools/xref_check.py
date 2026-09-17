"""Cross-reference integrity checker for FamilyLifeOS documentation.

Scans all Markdown documentation files for document and section cross-references,
resolving abbreviations (DM, FTS, CM, RB, MR, MC, FSM, NFR, PRD, tracker, SIM, TAS),
bare section references, and markdown links. Validates target document existence,
heading/section existence, and reports version mismatches and pending-merge references.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
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
}

# Documents in active review / open PRs (#20, #22, #23) or unwritten
SPECIAL_STATUS_DOCS: dict[str, str] = {
    "docs/specs/Tech_Spec_Simulator_Architecture.md": "Pending merge (PR #20)",
    "docs/specs/Test_Automation_Strategy.md": "Pending merge (PR #23)",
    "docs/specs/Security_Threat_Model.md": "Unwritten P1 doc (AGENTS.md §3.1)",
}

# Canonical document versions as of M0/M1
CANONICAL_VERSIONS: dict[str, str] = {
    "docs/specs/Data_Model_Schema.md": "1.3",
    "docs/specs/Tech_Spec_Financial_Transaction_Safety.md": "1.2",
    "docs/specs/Tech_Spec_Consent_Manager.md": "1.3",
    "docs/runbooks/Runbook_DPI_Rate_Limits.md": "1.2",
    "docs/specs/Tech_Spec_Module_Registry.md": "1.1",
    "docs/specs/Tech_Spec_Supervisor_State_Machine.md": "2.1",
    "docs/specs/NFR_Specs.md": "2.2",
    "docs/strategy/Master_Context.md": "2.1",
    "docs/strategy/PRD_FamilyLifeOS_Core.md": "2.2",
    "docs/strategy/Master_PRD.md": "2.1",
    "docs/strategy/Vision_Parking_Lot.md": "2.0",
    "docs/strategy/PRD_Module_Finance.md": "0.1",
    "docs/strategy/PRD_Module_Health.md": "0.1",
    "docs/strategy/PRD_Module_Secure_Vault.md": "0.1",
    "docs/strategy/Roadmap.md": "0.2",
    "docs/Execution_Plan.md": "0.3",
    "docs/strategy/GTM_Plan.md": "0.2",
}

SEC_TOKEN_PATTERN = r"(?:[0-9]+(?:\.[0-9]+)*|[Qq]\d+|[Gg]\d+|[Mm]\d+|WP-\d+|Step\s*\d+)"
DASH_PATTERN = r"[\u2013\u2014\-]"


@dataclass
class XRefFinding:
    source_file: str
    line_number: int
    raw_text: str
    target_doc: str | None
    target_section: str | None
    cited_version: str | None
    canonical_version: str | None
    status: str  # VALID | PENDING_MERGE | DANGLING_DOC | DANGLING_SECTION | VERSION_MISMATCH
    detail: str


class DocIndex:
    """Indexes document headings, sections, and anchors."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.sections_by_doc: dict[str, set[str]] = {}
        self.anchors_by_doc: dict[str, set[str]] = {}
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


def check_all_references(repo_root: Path) -> list[XRefFinding]:
    """Scan all documentation files and validate cross-references."""
    index = DocIndex(repo_root)
    findings: list[XRefFinding] = []

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

                # Check if target is a special / pending-merge document
                if target_path in SPECIAL_STATUS_DOCS:
                    reason = SPECIAL_STATUS_DOCS[target_path]
                    findings.append(
                        XRefFinding(
                            source_file=rel_src,
                            line_number=line_no,
                            raw_text=raw_text,
                            target_doc=target_path,
                            target_section=raw_sec,
                            cited_version=cited_ver,
                            canonical_version=CANONICAL_VERSIONS.get(target_path),
                            status="PENDING_MERGE",
                            detail=f"{target_path} is {reason}",
                        )
                    )
                    continue

                full_target_file = repo_root / target_path
                if not full_target_file.exists():
                    findings.append(
                        XRefFinding(
                            source_file=rel_src,
                            line_number=line_no,
                            raw_text=raw_text,
                            target_doc=target_path,
                            target_section=raw_sec,
                            cited_version=cited_ver,
                            canonical_version=CANONICAL_VERSIONS.get(target_path),
                            status="DANGLING_DOC",
                            detail=f"Target file does not exist on disk: '{target_path}'",
                        )
                    )
                    continue

                # 2. Version Mismatch Check
                canon_ver = CANONICAL_VERSIONS.get(target_path)
                if cited_ver and canon_ver:
                    norm_cited = cited_ver.lstrip("v")
                    norm_canon = canon_ver.lstrip("v")
                    if norm_cited != norm_canon:
                        findings.append(
                            XRefFinding(
                                source_file=rel_src,
                                line_number=line_no,
                                raw_text=raw_text,
                                target_doc=target_path,
                                target_section=raw_sec,
                                cited_version=cited_ver,
                                canonical_version=canon_ver,
                                status="VERSION_MISMATCH",
                                detail=f"Cited v{norm_cited}, but {os.path.basename(target_path)} status is v{norm_canon}",
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
                    # (common in self-describing clauses, changelogs, or when citing an external doc alongside local sections)
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
                                canonical_version=CANONICAL_VERSIONS.get(rel_src),
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
    pending = [f for f in findings if f.status == "PENDING_MERGE"]
    version_mismatches = [f for f in findings if f.status == "VERSION_MISMATCH"]
    dangling_sections = [f for f in findings if f.status == "DANGLING_SECTION"]
    dangling_docs = [f for f in findings if f.status == "DANGLING_DOC"]

    total = len(findings)
    print("======================================================================")
    print("          FamilyLifeOS Documentation Cross-Reference Sweep            ")
    print("======================================================================\n")
    print(f"Total References Scanned: {total}")
    print(f"  - Valid References:     {len(valid)}")
    print(f"  - Pending Merge (PRs):  {len(pending)}")
    print(f"  - Version Mismatches:   {len(version_mismatches)}")
    print(f"  - Dangling Sections:    {len(dangling_sections)}")
    print(f"  - Dangling Documents:   {len(dangling_docs)}")
    print("----------------------------------------------------------------------\n")

    if pending:
        print(
            f"### Pending Merge References ({len(pending)} references to PR #20, PR #23, or P1 specs)"
        )
        # Group by target doc
        by_doc: dict[str, list[XRefFinding]] = {}
        for f in pending:
            by_doc.setdefault(f.target_doc or "unknown", []).append(f)
        for doc, doc_findings in by_doc.items():
            print(f"  Target: {doc} ({doc_findings[0].detail})")
            for f in doc_findings[:5]:
                print(f"    [{f.source_file}:{f.line_number}] '{f.raw_text}'")
            if len(doc_findings) > 5:
                print(f"    ... and {len(doc_findings) - 5} more references")
        print()

    if version_mismatches:
        print(
            f"### Version Mismatches ({len(version_mismatches)} references citing older/different versions)"
        )
        for f in version_mismatches:
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
        help="Show detailed valid reference samples",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with non-zero status if dangling references are found",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    args = parse_args(argv)
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
    if args.strict and dangling:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
