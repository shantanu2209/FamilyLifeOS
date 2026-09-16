# GEMINI.md

All project instructions for this repository live in `AGENTS.md`, which is shared with Claude Code, Codex and the local agent. Read it in full before doing anything here, then `coordination/README.md` for the working protocol.

Your role (label `agent:gemini`): routine generation with a clear source of truth — WireMock stubs from the runbook's tables, Alembic migration files from the Data Model's DDL, test fixtures from the seed data, cross-reference checks, PR summaries. You do not make design decisions, you do not touch the payment, consent or audit code paths, and you never edit `docs/specs/`, `docs/runbooks/` or `AGENTS.md`. Every piece of work ends in a pull request from the template, labelled `agent:gemini` and `needs-review`, reviewed by Codex or Claude Code.

Do not add project instructions to this file. Put them in `AGENTS.md` so every agent sees the same rules.
