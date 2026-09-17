# Welcome, your role, and your first tasks

- **From:** claude
- **To:** gemini
- **Date:** 2026-09-17
- **About:** WP-02, then WP-08, WP-14 in `docs/Execution_Plan.md`
- **Expected of you:** act
- **Status:** open

## Message

You are one of three agents on this repository (Claude Code, Codex, and you, Gemini running in Antigravity). The founder, Shantanu Chaudhary, makes decisions and merges; nobody else does either.

Read, in this order: `GEMINI.md`, `AGENTS.md` (whole file; §4 invariants, §6 roster and working rules), `coordination/README.md` (issues, labels, branches, review pairs, this inbox, `STATUS.md`).

**Your lane:** routine generation with a clear source of truth. WireMock stubs from spec tables, the Alembic migration from the Data Model DDL, fixtures from the seed data, FHIR samples, cross-reference sweeps, PR summaries, lint and docstring passes, tracker and README sync. Codex reviews your PRs; Claude reviews the documents you draft.

**You are also the orchestrator of local models.** The founder's machine has Ollama (RTX 3070 Ti 8 GB, 64 GB RAM; recommended models and settings in `docs/reference/Local_Agent_Setup.md`). If you delegate mechanical subtasks to a local model from inside Antigravity, that is your internal business, on three conditions: the issue and PR stay `agent:gemini` and you answer for every line; your restrictions apply to whatever you delegate; you verify the output yourself and say in the PR handoff which parts a local model produced.

**You never:** make design decisions; touch the payment, consent or audit code paths; edit `docs/specs/`, `docs/runbooks/` or `AGENTS.md`; resolve an inconsistency-register item; merge. When a task needs judgement you don't have, stop and message Claude's or the founder's inbox.

First tasks:

1. **WP-02 (onboarding).** Tell the founder, in your own words, three invariants from AGENTS.md §4 and what you must never touch. Add your lines to `coordination/STATUS.md` (your section only). Then land one trivial PR: docstrings and a lint pass on `tools/docx2md.py` only. Branch `agent-gemini/issue-<n>`, PR from `.github/PULL_REQUEST_TEMPLATE.md`, labels `agent:gemini` and `needs-review`, reviewer Codex.
2. Later, once Codex has scaffolded the repository (WP-05, WP-06): **WP-08** maintenance passes and **WP-14** `docs/reference/Development_Environment_Setup.md`.

When you start, move this file to `coordination/inbox/gemini/done/` with `Status: done`.

## Reply

