# Coordination Protocol

How the founder and the four AI agents work together on this repository without the founder relaying messages between them. The repository itself is the communication channel: GitHub issues carry tasks, labels route them, branches and pull requests carry the work, and reviews are done by a different agent than the author. `AGENTS.md` holds the rules every agent obeys; this file holds the process.

> **Status:** v0.1 · adopted 2026-09-17 · **Owner:** Alfred (Lead Product Architect)

---

## 1. Roster

| Agent | Label | Best at | Never does |
|---|---|---|---|
| **Claude Code** (this desktop app) | `agent:claude` | Architecture, specs and their revisions, reviews of everything, roadmap and execution planning, cross-document consistency | Merge its own PRs |
| **Codex cloud** | `agent:codex` | Implementation against frozen specs, tests, second reviewer on specs and on Claude's PRs | Edit frozen specs without a version bump |
| **Gemini Flash in Antigravity** | `agent:gemini` | Routine generation: WireMock stubs from spec tables, Alembic migration files from DDL, test fixtures, cross-reference checks, PR summaries, README housekeeping | Decide anything; touch payment, consent or audit code paths |
| **Local model** (Ollama via Codex CLI, `tools/agent-local.ps1`) | `agent:local` | Mechanical tasks with a verifying script or test: lint fixes, docstrings, tracker status sync, commit messages | Anything under `docs/specs/`, `docs/runbooks/`, `AGENTS.md`; merging |
| **Founder** (Alfred) | assignee | Decisions, merges, credentials, anything outward-facing | — |

Escalation goes up this table: local → Gemini → Codex → Claude → founder. A task that needs judgement the assigned agent doesn't have gets relabelled, not guessed at.

## 2. Task intake

1. Every unit of work is a GitHub issue created from the **Agent task** template (`.github/ISSUE_TEMPLATE/agent_task.yml`). It states the goal, the spec sections that govern it, the definition of done, and how it is verified.
2. Exactly one `agent:*` label says who does it. Add `spec` for document work, `build-gate` for Phase 1 Build Gate work, `blocked` when waiting on a decision.
3. Issues are seeded from `docs/Execution_Plan.md` (work packages WP-xx). The issue title carries the WP id.
4. The founder (or Claude Code on the founder's behalf) is the only one who creates or relabels issues. Agents may open a **follow-up issue** for things they find, labelled `needs-triage`, but must not assign it to themselves.

## 3. Working an issue

1. Branch from `main`: `agent-<name>/issue-<n>` (the local launcher does this automatically). Never commit to `main` directly.
2. Read `AGENTS.md`, then the spec sections the issue cites. Cite section numbers in commit messages and PR descriptions.
3. Stay inside the issue's scope. Anything else becomes a follow-up issue.
4. Verify before opening the PR: run the command or test the issue names; paste the result in the PR.
5. Open the PR from the template (`.github/PULL_REQUEST_TEMPLATE.md`), reference the issue (`Closes #n`), keep the agent label, add `needs-review`.
6. Fill the handoff block (`coordination/HANDOFF_TEMPLATE.md`) in the PR description: what changed, what was verified, what the reviewer should look at first, open questions.

## 4. Review and merge

- **Different agent than the author, always.** Default pairs: local → Gemini or Codex; Gemini → Codex; Codex → Claude; Claude → Codex. The founder can review anything.
- The reviewer checks the PR template's list: scope matches the issue, no edits under frozen paths without a version bump, verification actually passes, cross-references correct, no secrets or real PII, tracker updated if status changed.
- Review verdicts are PR reviews (approve / request changes) with comments on lines, so the author agent can act on them without the founder relaying.
- Only the founder merges. Squash-merge; the PR title becomes the commit subject.
- After merge, the author agent (or the local agent on a `tracker sync` issue) updates `docs/PROJECT_TRACKER.md` if a document status, gap, or decision changed.

## 5. Frozen documents

`docs/specs/*` (frozen ones), `docs/runbooks/*` and `AGENTS.md` change only through a Claude Code or Codex PR that bumps the version, adds a Document Governance row, and updates dependents. A PR that touches them without that is rejected in review regardless of content.

## 6. Decisions and blockers

- Decisions are recorded in `docs/PROJECT_TRACKER.md` → Decision Log, dated, with rationale. Agents must not reopen a logged decision; if one looks wrong, open an issue labelled `blocked` explaining why and stop.
- The Cross-Document Inconsistency Register (same file) lists known conflicts. An agent that finds a new one adds a row via PR; it does not pick a side in code.
- Anything outward-facing (publishing, deploying, spending money, credentials) is the founder's, full stop.

## 7. Rhythm

- **Daily (founder, 10 minutes):** merge approved PRs, triage `needs-triage`, unblock `blocked`.
- **Weekly (Claude Code):** tracker health check — status matrix, register, Decision Log; propose next week's issues from the Execution Plan; update `coordination/BOARD.md`.
- **Per milestone (Roadmap M0–M5):** retrospective note appended to `coordination/BOARD.md`; GTM artefact per `docs/strategy/GTM_Plan.md`.

## 8. How each agent gets its instructions

| Agent | Reads on start | Task source | Output |
|---|---|---|---|
| Claude Code | `CLAUDE.md` → `AGENTS.md` (automatic) | issues `agent:claude`; direct requests from the founder | PRs, spec revisions, tracker updates |
| Codex cloud / CLI | `AGENTS.md` (automatic) | issues `agent:codex` | PRs with tests |
| Gemini / Antigravity | `GEMINI.md` → `AGENTS.md` | issues `agent:gemini` | PRs |
| Local (Codex CLI `--profile local`) | `AGENTS.md` (automatic) | issues `agent:local` via `tools/agent-local.ps1` | PRs labelled `agent:local` + `needs-review` |

Agents without GitHub API access work from the issue text pasted into their prompt by the founder or by the launcher script; their output is still a PR.

## 9. Files in this folder

- `README.md` — this protocol.
- `HANDOFF_TEMPLATE.md` — the block every PR description and cross-agent handoff uses.
- `BOARD.md` — Now / Next / Later view of the work, synced weekly from the issues. Issues are the source of truth; the board is the readable summary.
