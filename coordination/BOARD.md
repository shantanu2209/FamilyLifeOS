# Board

Readable summary of the work. GitHub issues are the source of truth; this file is synced weekly (Claude Code) or by a `tracker sync` issue (local agent). Dates are targets from `docs/strategy/Roadmap.md`.

_Last synced: 2026-09-17 (initial)_

## Now (this week)

| Item | Owner | Status |
|---|---|---|
| Install Docker Desktop (WSL 2), Codex CLI, Ollama models, Antigravity | founder | planned 2026-09-18 |
| Local agent smoke tests (`docs/reference/Local_Agent_Setup.md` §6) and record tokens/s | founder + local | after install |
| Codex review round 2: Data Model v1.3 and Module Registry v1.1 → freeze | agent:codex | after Codex login |
| Seed Phase 0/1 issues from `docs/Execution_Plan.md` | agent:claude | after founder approves the plan |
| Confirm roadmap dates and the LLM-provider default | founder | open |

## Next (weeks 2–3)

| Item | Owner |
|---|---|
| Tech_Spec_Simulator_Architecture.md (WireMock AA/BBPS/ABHA/DigiLocker, chaos mode, contract tests) | agent:claude, stubs by agent:gemini |
| Test_Automation_Strategy.md and Development_Environment_Setup.md formalised | agent:claude |
| Repo scaffolding: uv project, ruff, import-linter contract, CI workflow | agent:codex |
| Docker Compose + Alembic V001 from Data Model v1.3 | agent:gemini drafts, agent:codex reviews |

## Later

- Build Gate targets in order (resource lock → sessions → audit chain → Healer → FinanceAgent → crash scenarios A–D → Playwright "Priya pays BESCOM") — agent:codex
- LLM gateway with deterministic stub; PWA approval screen with WebAuthn — agent:codex
- Vault foundation, Health second slice, notification engine — agent:codex, PRDs by agent:claude
- Security_Threat_Model.md (P1, before any internet-facing deployment) — agent:claude
- Observability, demo deployment, portfolio write-up — mixed

## Blocked

- Nothing blocked as of 2026-09-17 beyond tool installation.

## Retrospectives

- (none yet; add one per milestone M0–M5)
