# Coordination Protocol

How the founder and the three AI agents work together on this repository without the founder relaying messages between them. The repository itself is the communication channel: GitHub issues carry tasks, labels route them, branches and pull requests carry the work, reviews are done by a different agent than the author, and `coordination/STATUS.md` plus `coordination/inbox/` carry everything else one agent needs to tell another. `AGENTS.md` holds the rules every agent obeys; this file holds the process.

> **Status:** v0.2 · 2026-09-17 · **Owner:** Shantanu Chaudhary (founder, Lead Product Architect)
> v0.1 (2026-09-17) had four agents and no message channel. v0.2: three agents (the local-model lane is folded into Gemini's), a status file and per-agent inboxes added, event-driven rhythm instead of a daily/weekly one.

---

## 1. Roster

| Who | Label | Does | Never does |
|---|---|---|---|
| **Claude Code** (desktop app) | `agent:claude` | Architecture; specs and their revisions; reviews of Codex's and Gemini's work; roadmap, execution plan and tracker; cross-document consistency; threat model; write-ups. Runs the tracker health check when work resumes after a pause. | Merge; review its own PRs |
| **Codex** (CLI on the founder's machine, or Codex cloud) | `agent:codex` | Implementation against frozen specs, with tests; second reviewer on specs and on Claude's and Gemini's PRs; CI and deployment scripts | Edit frozen specs without a version bump; reopen logged decisions; merge |
| **Gemini in Antigravity** | `agent:gemini` | Routine generation with a clear source of truth: WireMock stubs from spec tables, Alembic migration files from DDL, test fixtures, FHIR samples, cross-reference sweeps, PR summaries, lint and docstring passes, tracker and README sync. **Orchestrates any local models** (Ollama on the founder's machine) as its own sub-agents for mechanical subtasks. | Decide design questions; touch payment, consent or audit code paths; edit `docs/specs/`, `docs/runbooks/` or `AGENTS.md`; merge |
| **Founder** (Shantanu Chaudhary) | assignee | Decisions, merges, credentials, accounts, anything outward-facing | — |

**Local models are not a fourth agent.** How Gemini uses them inside Antigravity is its own business and is invisible to this protocol, with three conditions: (1) the work is still an `agent:gemini` issue and PR, and Gemini is accountable for every line; (2) Gemini's restrictions apply equally to anything it delegates; (3) Gemini verifies delegated output itself before opening the PR, and the handoff block says which parts a local model produced (one line; it feeds the Roadmap §8 metrics and the founder's learning notes). Setup reference: `docs/reference/Local_Agent_Setup.md`.

Escalation goes up the table: Gemini → Codex → Claude → founder. A task that needs judgement the assigned agent doesn't have gets relabelled (by the founder or Claude Code), not guessed at.

## 2. The channel: what goes where

| You want to… | Use | Notes |
|---|---|---|
| Assign a task | A GitHub issue from the **Agent task** template with exactly one `agent:*` label | §3 |
| Say "I've picked this up" | Add `in-progress` to the issue **and** a line in your section of `coordination/STATUS.md` | §5 |
| See what everyone else is doing | `coordination/STATUS.md`, then `gh issue list --label in-progress` and `gh pr list` | Read it at the start of every session |
| Deliver a review verdict on a PR | A GitHub PR review (approve / request changes) with line comments | §4 |
| Deliver a review of something that is not a PR (a spec, a plan) | Findings posted in the review issue, by severity; large reports as `coordination/reviews/<YYYYMMDD>-<reviewer>-<subject>.md` via PR | The Codex round-2 spec reviews work this way |
| Tell another agent something (handoff, question, warning, "your PR conflicts with mine") | A message file in `coordination/inbox/<recipient>/` | §5 |
| Ask the founder for a ruling | A message in `coordination/inbox/founder/` **and** `blocked` on the issue. Claude Code also lists open rulings in chat at the end of every session (AGENTS.md §6) | Never guess a ruling |
| Record a decision | `docs/PROJECT_TRACKER.md` → Decision Log | §7 |

## 3. Task intake

1. Every unit of work is a GitHub issue created from the **Agent task** template (`.github/ISSUE_TEMPLATE/agent_task.yml`). It states the goal, the spec sections that govern it, the definition of done, and how it is verified.
2. Exactly one `agent:*` label says who does it. Add `spec` for document work, `build-gate` for Phase 1 Build Gate work, `blocked` when waiting on a decision or a dependency.
3. Issues are seeded from `docs/Execution_Plan.md` (work packages WP-xx). The issue title carries the WP id.
4. The founder (or Claude Code on the founder's behalf) is the only one who creates or relabels issues. Agents may open a **follow-up issue** for things they find, labelled `needs-triage`, but must not assign it to themselves.

## 4. Working an issue, review and merge

1. Start of session: read your inbox (`coordination/inbox/<you>/`) and `coordination/STATUS.md`. Then pick up the issue: add `in-progress`, update your STATUS section.
2. Branch from `main`: `agent-<name>/issue-<n>`. Work never goes to `main` directly (the only exception is §5).
3. Read `AGENTS.md`, then the spec sections the issue cites. Cite section numbers in commit messages and PR descriptions. Stay inside the issue's scope; anything else becomes a follow-up issue.
4. Verify before opening the PR: run the command or test the issue names; paste the result in the PR.
5. Open the PR from the template (`.github/PULL_REQUEST_TEMPLATE.md`), reference the issue (`Closes #n`), keep the agent label, add `needs-review`, fill the handoff block (`coordination/HANDOFF_TEMPLATE.md`), and drop a one-line message in the reviewer's inbox pointing at the PR.
6. **Review is by a different agent than the author, always.** Default pairs: Gemini → Codex; Codex → Claude; Claude → Codex. The founder can review anything. The reviewer checks the PR template's list: scope matches the issue, no edits under frozen paths without a version bump, verification actually passes, cross-references correct, no secrets or real PII, tracker updated if status changed.
7. Verdicts are PR reviews with comments on lines, so the author agent can act on them without the founder relaying. The reviewer removes `needs-review` on approval and messages the founder's inbox only if something needs a ruling.
8. Only the founder merges. Squash-merge; the PR title becomes the commit subject. After merge the author removes its STATUS line; tracker updates ride in the same PR when a document status, gap or decision changed.

## 5. STATUS and inbox

**`coordination/STATUS.md`** has one section per agent. Each agent edits only its own section: what it is working on (issue, branch), what it is waiting for, and its last finished item. Keep it to a few lines; history lives in git and in the issues.

**`coordination/inbox/<recipient>/`** holds one file per message, named `YYYYMMDD-<from>-<slug>.md`, written from `coordination/inbox/MESSAGE_TEMPLATE.md`. Recipients are `claude`, `codex`, `gemini`, `founder`. Rules:

- A message has one subject and says what is expected of the recipient (act, answer, or just know). Link the issue or PR; don't paste diffs.
- The recipient handles it, appends a dated reply under `## Reply` if one is needed, sets `Status: done`, and moves the file to `coordination/inbox/<recipient>/done/`. The inbox root therefore always shows exactly what is open.
- Replies that need action go back as a new message in the sender's inbox. No threads longer than one reply per file.
- Messages are coordination, not decisions and not specs. Anything durable belongs in the tracker, a spec or an issue.
- The repository is public: no secrets, no real personal data, nothing you would not put in a PR.

**Committing coordination files.** Changes that touch only `coordination/STATUS.md` and `coordination/inbox/**` may be committed straight to `main` with a subject starting `coord:` (for example `coord: gemini status, message to codex about WP-18`). Pull with rebase first; never force-push. An agent that cannot push to `main` (Codex cloud) includes its coordination changes in its PR, or comments on the issue, and the next local agent mirrors anything urgent. Everything outside those two paths goes through a PR.

## 6. Frozen documents

`docs/specs/*` (frozen ones), `docs/runbooks/*` and `AGENTS.md` change only through a Claude Code or Codex PR that bumps the version, adds a Document Governance row, and updates dependents. A PR that touches them without that is rejected in review regardless of content.

## 7. Decisions and blockers

- Decisions are recorded in `docs/PROJECT_TRACKER.md` → Decision Log, dated, with rationale. Agents must not reopen a logged decision; if one looks wrong, open an issue labelled `blocked` explaining why, message the founder's inbox, and stop.
- The Cross-Document Inconsistency Register (same file) lists known conflicts. An agent that finds a new one adds a row via PR; it does not pick a side in code.
- Anything outward-facing (publishing, deploying, spending money, credentials) is the founder's, full stop.

## 8. Rhythm

There is no calendar (founder ruling 2026-09-17: no target dates, no assumed hours). The rhythm is event-driven:

- **Whenever the founder sits down:** read `coordination/inbox/founder/`, merge approved PRs, triage `needs-triage`, unblock `blocked`.
- **Every agent session:** starts with inbox + STATUS, ends with STATUS updated and handoffs sent. Claude Code additionally ends every session by listing, in chat, the rulings the founder needs to make, with explanation, implications and a recommendation (AGENTS.md §6).
- **After each batch of merges:** Gemini's maintenance pass (Execution Plan WP-08); Claude Code syncs `coordination/BOARD.md` and proposes the next issues from the Execution Plan.
- **Per milestone (Roadmap M0–M5):** retrospective note appended to `coordination/BOARD.md`; GTM artefact per `docs/strategy/GTM_Plan.md`.
- **After a pause of any length:** Claude Code runs a tracker health check (status matrix, register, Decision Log, open PRs, stale STATUS lines) before anyone builds.

## 9. How each agent gets its instructions

| Agent | Reads on start | Task source | Output |
|---|---|---|---|
| Claude Code | `CLAUDE.md` → `AGENTS.md` (automatic), then inbox and STATUS | issues `agent:claude`; direct requests from the founder | PRs, spec revisions, tracker updates, reviews |
| Codex | `AGENTS.md` (automatic), then inbox and STATUS | issues `agent:codex` | PRs with tests, reviews |
| Gemini / Antigravity | `GEMINI.md` → `AGENTS.md`, then inbox and STATUS | issues `agent:gemini` | PRs (it may have used local models to produce them), sweeps, summaries |

An agent without GitHub API access works from the issue text pasted into its prompt by the founder; its output is still a PR.

## 10. Files in this folder

- `README.md` — this protocol.
- `STATUS.md` — who is working on what, one section per agent.
- `inbox/` — per-recipient message folders, `MESSAGE_TEMPLATE.md`, and `done/` subfolders.
- `reviews/` — review reports too large for an issue comment (created when first needed).
- `HANDOFF_TEMPLATE.md` — the block every PR description uses.
- `BOARD.md` — Now / Next / Later view of the work. Issues are the source of truth; the board is the readable summary.
