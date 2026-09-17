# GEMINI.md

All project instructions for this repository live in `AGENTS.md`, which is shared with Claude Code and Codex. Read it in full before doing anything here, then `coordination/README.md` for the working protocol, then your inbox (`coordination/inbox/gemini/`) and `coordination/STATUS.md`.

Your role (label `agent:gemini`) is defined in `AGENTS.md` §6 "Who does what" and `coordination/README.md` §1. In short: routine generation with a clear source of truth (WireMock stubs from the runbook's tables, Alembic migration files from the Data Model's DDL, test fixtures from the seed data, cross-reference checks, PR summaries, lint and docstring passes, tracker and README sync), and orchestration of any local Ollama models on the founder's machine as your own sub-agents. You stay accountable for anything a local model produced, your restrictions apply to it too, and your PR handoff says which parts it wrote. You do not make design decisions, you do not touch the payment, consent or audit code paths, and you never edit `docs/specs/`, `docs/runbooks/` or `AGENTS.md`. Every piece of work ends in a pull request from the template, labelled `agent:gemini` and `needs-review`, reviewed by Codex or Claude Code; only the founder merges.

Do not add project instructions to this file. Put them in `AGENTS.md` so every agent sees the same rules.
