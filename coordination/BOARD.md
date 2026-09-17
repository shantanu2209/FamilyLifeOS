# Board

Readable summary of the work. GitHub issues are the source of truth; Claude Code syncs this file after each batch of merges. There are no dates here by decision (tracker → Decision Log, 2026-09-17): the columns are an order, not a schedule.

_Last synced: 2026-09-17_

## Now

| Item | Owner | Status |
|---|---|---|
| Workstation setup: WSL 2, Docker Desktop; Codex app and Antigravity opened on the repo (`docs/reference/Workstation_Setup.md`) — WP-01 | founder | in progress |
| Onboard Codex and Gemini: inbox message, first STATUS line; Gemini's first trivial PR — WP-02 | founder + agents | after WP-01 |
| Codex review round 2: Data Model v1.3, Module Registry v1.1, Consent Manager v1.3 §2.6 → freeze — WP-09, WP-10, WP-11 | agent:codex, then agent:claude | ready to start |
| Labels, milestones, Phase 0–1 issues — WP-03, WP-04 | agent:claude | done 2026-09-17; branch protection (WP-03) is the founder's |

## Next

| Item | Owner |
|---|---|
| Repo scaffolding: uv project, ruff, import-linter contract, CI workflow — WP-05, WP-06 | agent:codex |
| Tech_Spec_Simulator_Architecture.md (WireMock AA/BBPS/ABHA/DigiLocker, chaos mode, contract tests) — WP-12 | agent:claude, stubs by agent:gemini |
| Test_Automation_Strategy.md; Development_Environment_Setup.md — WP-13, WP-14 | agent:claude; agent:gemini |
| Docker Compose + Alembic V001 from Data Model v1.3 — WP-17, WP-19 | agent:gemini drafts, agent:codex reviews |

## Later

- Build Gate targets in order (resource lock → sessions → audit chain → Healer → FinanceAgent → crash scenarios A–D → Playwright "Priya pays BESCOM") — agent:codex
- LLM gateway with deterministic stub (hosted default: Claude Haiku); PWA approval screen with WebAuthn — agent:codex
- Vault foundation, Health second slice, notification engine — agent:codex, PRDs by agent:claude
- Security_Threat_Model.md (P1, before any internet-facing deployment) — agent:claude
- Observability, demo deployment, portfolio write-up — mixed

## Blocked

- Nothing blocked beyond tool installation.

## Retrospectives

- (none yet; add one per milestone M0–M5)
