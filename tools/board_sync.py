"""Set the GitHub project board's Status and Agent fields from issue state and labels.

The board is a view over the repository's issues and pull requests; this script makes the
view match the facts so nobody edits the board by hand.

    closed or merged                      -> Done
    open PR, or an issue an open PR closes -> In review
    label `blocked`                       -> Blocked
    label `in-progress`                   -> In progress
    anything else                         -> Ready

    Agent field: from the `agent:*` label; items without one belong to the founder.

Needs the GitHub CLI (`gh`) signed in with the `project` scope. Standard library only.

    python tools/board_sync.py            # apply
    python tools/board_sync.py --dry-run  # show what would change
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys

OWNER = "shantanu2209"
PROJECT_NUMBER = "2"
AGENTS = {"agent:claude": "Claude", "agent:codex": "Codex", "agent:gemini": "Gemini"}


def gh(*args: str) -> str:
    """Run gh and return stdout; stop with its error text on failure."""
    result = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8", check=False)
    if result.returncode != 0:
        sys.exit(f"board_sync: gh {' '.join(args)} failed:\n{result.stderr}")
    return result.stdout


def wanted_status(item: dict, in_review: set[int], is_pr: bool) -> str:
    labels = {label["name"] for label in item["labels"]}
    if item["state"] in ("CLOSED", "MERGED"):
        return "Done"
    if is_pr or item["number"] in in_review:
        return "In review"
    if "blocked" in labels:
        return "Blocked"
    if "in-progress" in labels:
        return "In progress"
    return "Ready"


def wanted_agent(item: dict) -> str:
    labels = {label["name"] for label in item["labels"]}
    return next((name for label, name in AGENTS.items() if label in labels), "Founder")


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dry-run", action="store_true", help="print changes without applying them")
    args = parser.parse_args(argv)

    project = json.loads(gh("project", "view", PROJECT_NUMBER, "--owner", OWNER, "--format", "json"))
    fields = json.loads(gh("project", "field-list", PROJECT_NUMBER, "--owner", OWNER, "--format", "json"))["fields"]
    by_name = {field["name"]: field for field in fields}
    status_options = {option["name"]: option["id"] for option in by_name["Status"]["options"]}
    agent_options = {option["name"]: option["id"] for option in by_name["Agent"]["options"]}

    issues = json.loads(gh("issue", "list", "--state", "all", "--limit", "500", "--json", "number,state,labels,url,title"))
    pulls = json.loads(gh("pr", "list", "--state", "all", "--limit", "500", "--json", "number,state,labels,url,title,body"))
    in_review = {
        int(number)
        for pull in pulls
        if pull["state"] == "OPEN"
        for number in re.findall(r"[Cc]loses #(\d+)", pull["body"] or "")
    }

    board = json.loads(gh("project", "item-list", PROJECT_NUMBER, "--owner", OWNER, "--format", "json", "--limit", "500"))["items"]
    on_board = {item["content"].get("url"): item for item in board if item.get("content")}

    changes = 0
    for item, is_pr in [(issue, False) for issue in issues] + [(pull, True) for pull in pulls]:
        status, agent = wanted_status(item, in_review, is_pr), wanted_agent(item)
        existing = on_board.get(item["url"])
        if existing and existing.get("status") == status and existing.get("agent") == agent:
            continue
        changes += 1
        kind = "PR" if is_pr else "issue"
        print(f"{kind} #{item['number']:<3} -> {status:<11} {agent:<7} {item['title'][:60]}")
        if args.dry_run:
            continue
        item_id = existing["id"] if existing else json.loads(
            gh("project", "item-add", PROJECT_NUMBER, "--owner", OWNER, "--url", item["url"], "--format", "json")
        )["id"]
        for field, option in (("Status", status_options[status]), ("Agent", agent_options[agent])):
            gh("project", "item-edit", "--id", item_id, "--project-id", project["id"],
               "--field-id", by_name[field]["id"], "--single-select-option-id", option)

    print(f"board_sync: {changes} item(s) {'would change' if args.dry_run else 'updated'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
