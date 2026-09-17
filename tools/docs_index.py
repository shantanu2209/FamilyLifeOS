"""Generate docs/INDEX.md from each document's own Status line.

A document's version and status live in exactly one place: the header of the
document itself. This script reads those headers and writes the index that every
other file links to, so nobody maintains a second copy by hand.

    python tools/docs_index.py            # rewrite docs/INDEX.md
    python tools/docs_index.py --check    # exit 1 if docs/INDEX.md is out of date
                                          # or a document has no Status line

Standard library only. The output is deterministic: no timestamps, stable order.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

INDEX_REL = "docs/INDEX.md"
HEADER_LINES = 14  # a Status line must appear this early in the file

STATUS_RE = re.compile(r"^>?\s*\*\*Status:\*\*\s*(.+)$")
VERSION_RE = re.compile(r"\bv(\d+(?:\.\d+)+)\b")
CHANGED_RE = re.compile(r"\*\*Last content change:\*\*\s*([0-9]{4}-[0-9]{2}(?:-[0-9]{2})?)")
STATE_WORDS = (
    "FROZEN",
    "CANONICAL",
    "REVISION IN REVIEW",
    "DRAFT",
    "REFERENCE",
    "GUIDE",
    "TEMPLATE",
    "LIVING",
    "HISTORICAL",
)

GROUPS = (
    ("docs/strategy/", "Strategy and product"),
    ("docs/specs/", "Specifications"),
    ("docs/runbooks/", "Runbooks"),
    ("docs/reference/", "Reference and guides"),
    ("docs/templates/", "Templates"),
    ("docs/", "Plans and tracking"),
)


def read_header(path: Path) -> tuple[str, str | None, str | None]:
    """Return (title, status_text, last_changed) from the top of a document."""
    title = path.stem
    status = None
    changed = None
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle):
            if number >= HEADER_LINES:
                break
            line = line.rstrip("\n")
            if line.startswith("# ") and title == path.stem:
                title = line[2:].strip()
            match = STATUS_RE.match(line)
            if match and status is None:
                status = match.group(1)
                found = CHANGED_RE.search(line)
                if found:
                    changed = found.group(1)
    return title, status, changed


def summarise(status: str) -> tuple[str, str]:
    """Split a Status line into (version, short state)."""
    head = status.split(" · ")[0].strip()
    version_match = VERSION_RE.search(head)
    version = f"v{version_match.group(1)}" if version_match else "—"
    upper = head.upper()
    state = next((word for word in STATE_WORDS if word in upper), "")
    if "REVIEW" in upper and state not in ("REVISION IN REVIEW",):
        state = f"{state}, in review".strip(", ") if state else "In review"
    note = head
    if len(note) > 110:
        note = note[:107].rstrip() + "…"
    return version, f"{state.capitalize() if state else '—'} | {note}"


def build_index(root: Path) -> tuple[str, list[str]]:
    """Return (index_markdown, problems)."""
    problems: list[str] = []
    rows: dict[str, list[str]] = {label: [] for _, label in GROUPS}
    for path in sorted((root / "docs").rglob("*.md")):
        rel = path.relative_to(root).as_posix()
        if rel == INDEX_REL:
            continue
        title, status, changed = read_header(path)
        if status is None:
            problems.append(f"{rel}: no '**Status:**' line in the first {HEADER_LINES} lines")
            continue
        version, state_and_note = summarise(status)
        state, note = state_and_note.split(" | ", 1)
        label = next(label for prefix, label in GROUPS if rel.startswith(prefix))
        link = rel[len("docs/"):]
        rows[label].append(f"| [{title}]({link}) | {version} | {state} | {changed or '—'} | {note} |")

    lines = [
        "# Document Index",
        "",
        "> **Status:** GENERATED — do not edit. Written by `python tools/docs_index.py` from the Status line at the top of each document; CI fails when this file is out of date (`--check`).",
        "",
        "This is the only list of document versions and statuses in the repository. To change what it says, change the document's own header and regenerate. Live work status is on the GitHub project board; decisions and the current state are in `PROJECT_TRACKER.md`.",
        "",
    ]
    for _, label in GROUPS:
        if not rows[label]:
            continue
        lines += [f"## {label}", "", "| Document | Version | State | Last content change | Status line |", "|---|---|---|---|---|"]
        lines += rows[label]
        lines.append("")
    return "\n".join(lines), problems


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--root", default=".", help="repository root (default: .)")
    parser.add_argument("--check", action="store_true", help="verify instead of writing")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    index_text, problems = build_index(root)
    target = root / INDEX_REL

    for problem in problems:
        sys.stderr.write(f"docs_index: {problem}\n")

    if args.check:
        current = target.read_text(encoding="utf-8") if target.exists() else ""
        if current != index_text:
            sys.stderr.write(f"docs_index: {INDEX_REL} is out of date; run python tools/docs_index.py\n")
            return 1
        return 1 if problems else 0

    target.write_text(index_text, encoding="utf-8", newline="\n")
    print(f"docs_index: wrote {INDEX_REL}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
