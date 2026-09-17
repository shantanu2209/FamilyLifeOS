"""Checks that keep the living documents from drifting or duplicating each other.

Each fact has one home (AGENTS.md section 6, "One home per fact"). These rules fail the
build when a second copy reappears or a living document goes stale:

  R1  coordination/BOARD.md must not exist (the GitHub project board is the live view).
  R2  README.md and AGENTS.md carry no document versions or states in tables; docs/INDEX.md does.
  R3  Plans carry no calendar: no week or month numbers, no due dates, no hours per week,
      and no date later than the tracker's newest log entry (a future date is a target date).
  R4  The tracker's "Current state" is not older than its newest Decision Log or change-log row.
  R5  Retired tracker sections stay retired.
  R6  AGENTS.md section 7 has no checklist; the Build Gate checklist lives in the tracker.

    python tools/living_docs_check.py [--root .]

Standard library only. Exit code 1 on any finding.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

TRACKER = "docs/PROJECT_TRACKER.md"
PLANS = ("docs/strategy/Roadmap.md", "docs/Execution_Plan.md", "docs/strategy/GTM_Plan.md", "coordination/README.md")
NO_VERSION_TABLES = ("README.md", "AGENTS.md")
RETIRED_TRACKER_HEADINGS = (
    "Project Status Overview",
    "Repository Layout",
    "Document Inventory & Health Check",
    "Document Status Matrix",
    "Test Automation Strategy",
    "Development Environment Needs",
    "Milestone Tracker",
    "Next Actions",
    "Success Metrics Dashboard",
)

ISO_DATE = re.compile(r"\b(20[0-9]{2}-[01][0-9]-[0-3][0-9])\b")
CALENDAR_WORDS = re.compile(
    r"\b(?:Weeks?|Months?)\s+[0-9]+\b|\bdue_on\b|\bhours?\s+(?:a|per)\s+week\b|\bper\s+week\b", re.IGNORECASE
)
VERSION_IN_ROW = re.compile(r"\bv[0-9]+\.[0-9]+|\bFROZEN\b|\bDRAFT\b|\bCANONICAL\b")
AS_OF = re.compile(r"_As of:\s*(20[0-9]{2}-[01][0-9]-[0-3][0-9])_")


def read(root: Path, rel: str) -> list[str]:
    path = root / rel
    return path.read_text(encoding="utf-8").splitlines() if path.exists() else []


def section(lines: list[str], heading_contains: str) -> list[str]:
    """Lines of the first level-2 section whose heading contains the text."""
    out: list[str] = []
    inside = False
    for line in lines:
        if line.startswith("## "):
            if inside:
                break
            inside = heading_contains.lower() in line.lower()
            continue
        if inside:
            out.append(line)
    return out


def newest_log_date(tracker: list[str]) -> str | None:
    dates: list[str] = []
    for name in ("Decision Log", "Change Log"):
        for line in section(tracker, name):
            if line.startswith("| 20"):
                dates.append(line[2:12])
    return max(dates) if dates else None


def check(root: Path) -> list[str]:
    findings: list[str] = []
    tracker = read(root, TRACKER)

    # R1
    if (root / "coordination/BOARD.md").exists():
        findings.append("R1 coordination/BOARD.md exists; the GitHub project board is the live view")

    # R2
    for rel in NO_VERSION_TABLES:
        for number, line in enumerate(read(root, rel), 1):
            if line.startswith("|") and "docs/" in line and VERSION_IN_ROW.search(line):
                findings.append(f"R2 {rel}:{number} a table row states a document's version or state; that belongs in docs/INDEX.md")

    # R3
    newest = newest_log_date(tracker)
    for rel in PLANS:
        for number, line in enumerate(read(root, rel), 1):
            if re.match(r"\| v[0-9]", line) or line.startswith(">"):
                continue  # governance rows and header lines record history, not plans
            if CALENDAR_WORDS.search(line):
                findings.append(f"R3 {rel}:{number} calendar wording in a plan: {CALENDAR_WORDS.search(line).group(0)!r}")
            if newest:
                for date in ISO_DATE.findall(line):
                    if date > newest:
                        findings.append(f"R3 {rel}:{number} date {date} is later than the tracker's newest log entry ({newest}): a target date")

    # R4
    state = section(tracker, "Current state")
    as_of = next((m.group(1) for line in state if (m := AS_OF.search(line))), None)
    if not tracker:
        findings.append(f"R4 {TRACKER} is missing")
    elif as_of is None:
        findings.append(f"R4 {TRACKER} has no '## Current state' section with an '_As of: YYYY-MM-DD_' line")
    elif newest and as_of < newest:
        findings.append(f"R4 {TRACKER} current state is as of {as_of}, but the logs have an entry dated {newest}: update the current state")

    # R5
    for number, line in enumerate(tracker, 1):
        if line.startswith("## "):
            for retired in RETIRED_TRACKER_HEADINGS:
                if retired.lower() in line.lower():
                    findings.append(f"R5 {TRACKER}:{number} retired section is back: {line.strip()!r}")

    # R6
    agents = read(root, "AGENTS.md")
    for line in section(agents, "7. "):
        if re.match(r"\s*- \[[ xX]\]", line):
            findings.append("R6 AGENTS.md section 7 contains a checklist; the Build Gate checklist lives in the tracker")
            break

    return findings


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--root", default=".", help="repository root (default: .)")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    findings = check(Path(args.root).resolve())
    for finding in findings:
        print(f"living_docs_check: {finding}")
    if not findings:
        print("living_docs_check: all rules pass")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
