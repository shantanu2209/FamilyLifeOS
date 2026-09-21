# FamilyLifeOS — Project Tracker

> **Status:** LIVING — maintained by Claude Code on the founder's behalf · **Owner:** Shantanu Chaudhary (Lead Product Architect) · restructured 2026-09-17
> **What lives here, and only here:** the current state in a few lines, the Decision Log, the change log, the list of documents still to be written, the Cross-Document Inconsistency Register, open gaps and risks, the Phase 1 Build Gate checklist, the near-term parking lot, retrospectives.
> **What does not live here:** document versions and statuses (`docs/INDEX.md`, generated from each document's header); the plan (`docs/strategy/Roadmap.md` for phases and gates, `docs/Execution_Plan.md` for work packages); what is being worked on right now (the GitHub project board, https://github.com/users/shantanu2209/projects/2, and `coordination/STATUS.md`); agent rules (`AGENTS.md`). The tracker's February 2026 sections are kept unmaintained in `docs/reference/Project_Tracker_Snapshot_2026-02.md`.

---

## 📍 Current state

_As of: 2026-09-21_

- **Phase:** Roadmap Phase 1 (spec close-out). No application code yet.
- **Agents:** Claude Code, Codex and Gemini are onboarded, each in its own worktree.
- **Specs:** Codex's round-2 review (2026-09-21) required changes everywhere it looked: 29 findings on the Data Model, Consent Manager and Module Registry, 31 on four open pull requests. All are answered in one batch: Data Model v1.4, Consent Manager v1.4, Module Registry v1.2 and Financial Transaction Safety v1.3 (WP-11), and revisions of the Vault, Health and Finance PRDs, the simulator spec and the test strategy. The four specs are unfrozen until Codex's targeted re-review passes; the DPI runbook stays frozen.
- **In review:** the WP-11 pull request and PRs #22, #25, #20, #23, in that merge order. See the project board for the live list.
- **Build Gate:** blocked on that re-review and on scaffolding and CI (Codex, #5 and #6). Checklist below.
- **Waiting on the founder:** nothing blocking. Branch protection on `main` (require the `docs` check).

---

## 🧭 Decision Log

Decisions that shape scope and process. Add a row whenever one is made; agents must not reopen a logged decision without flagging it.

| Date | Decision | Rationale / implications |
|---|---|---|
| 2026-09-17 | **Project mode: portfolio first.** Build the kernel and the "Priya pays BESCOM bill" vertical slice against DPI simulators. No FIU/BBPOU/HIU licence applications for now. Commercial expansion stays possible; the venture-oriented sections of Master Context (phasing budgets, GTM, unit economics) are kept but are not the current plan. | Removes the 6–12 month regulatory lead time from the critical path. Real-money DPI integration cannot happen without licences, so Phase 1 quality is proven by simulator contract tests and the crash-scenario suite. Roadmap (item 5) and execution plan (item 8) are re-baselined on this basis. |
| 2026-09-17 | **Repository is public on GitHub; `archive/` is excluded from git entirely.** | Public repos get unlimited free GitHub Actions minutes. The archive (Word originals, superseded versions, AI review notes, raw claude.ai exports) stays on disk only and is gitignored; nothing in the public history contains it. No secrets, real PII or consent handles may ever be committed. |
| 2026-09-17 | **Requirements: NFR v2.2 rather than a separate requirements document.** Functional requirements stay in PRD Core §4; the NFR gets the missing sections (scalability targets, disaster recovery, degradation strategy, breaker-layer note). PRD Core gets a v2.2 refresh at item 11 together with module PRDs for Vault, Finance and Health. | Avoids a duplicate requirements document that would drift from the PRD. |
| 2026-09-17 | **Multi-agent roster (first direction; superseded the same day by the three-agent roster below):** Claude Code for architecture, specs and reviews; Codex for implementation against frozen specs; a Gemini Flash-class model in Google Antigravity for routine, low-judgement work; a local Ollama model for mechanical instruction-following tasks. Coordination happens through the repository (GitHub issues, PRs, labels and a `coordination/` folder), not through the founder relaying messages. One agent's output is always reviewed by a different agent before merge. | Saves Claude/Codex usage for the work that needs judgement, and doubles as a learning exercise in coordinating cloud and local agents. |
| 2026-09-17 | **Local model recommendation (originally "local agent stack"; local models now sit under Gemini's lane, see the three-agent row below):** Ollama on the founder's RTX 3070 Ti (8 GB) + 64 GB RAM; everyday model `qwen3.5:9b` (6.6 GB, tools, fits the GPU); optional heavy model `qwen3.6:35b` (MoE, ~3 B active, 23 GB, runs from RAM); harness = Codex CLI with `local` / `local-heavy` profiles and `codex exec` for scripted runs; Aider as fallback harness. Gemma 4 rejected for the agent role (tool refusal and looping in hands-on reports, far behind Qwen on software-engineering benchmarks); gpt-oss:20b kept only as a smoke-test alternative. Guide: `docs/reference/Local_Agent_Setup.md`. | Tokens/s on this machine still to be measured (smoke tests §6 of the guide). Docker Desktop is not installed yet and is needed before the Build Gate infrastructure. |
| 2026-09-17 | **Inconsistency Register items 1–3 resolved (founder ruling):** the resource lock is a dedicated `core.resource_lock` table; the session column stays `fsm_state` and gains `intent_type`, `bbps_transaction_ref_id`, `healer_poll_count`, `session_notes`; roles are renamed `spouse → member`, `child → minor`. Applied in Data Model v1.3 with consequential edits in FTS v1.2, Consent Manager v1.2, Runbook v1.2, Module Registry v1.1. | Nothing is built yet, so all three are free changes now and expensive later. |
| 2026-09-17 | **Review process for the two open specs:** Claude Code ran review round 1 on the Module Registry (7 fixes → v1.1, log in MR §13); Codex runs round 2 on Module Registry v1.1 and Data Model v1.3 once set up; both freeze on approval. | Keeps the two-reviewer discipline the frozen specs were built with, using two different model families. |
| 2026-09-17 | **Security_Threat_Model.md moved from late-P0 to P1**, due before any internet-facing deployment (portfolio demo included). Scope fixed in NFR v2.2 §9. | In portfolio mode there are no real DPI webhooks, so the attack surface arrives with the demo deployment, not with the first line of code. |
| 2026-09-17 | **Technology choices (item 13):** Python 3.12 via uv, ruff, import-linter, pre-commit; PWA frontend (React + Vite + TypeScript, Vitest, Playwright) with WebAuthn passkeys standing in for biometrics; pluggable LLM gateway (deterministic stub for tests, local `qwen3.5:9b` for development, hosted model for demo — confirmed as Claude Haiku, see below); no agent framework, plain SDK calls + Pydantic; PII boundary: hosted LLMs see only the utterance and non-PII context; Docker Compose locally; hosting deferred to the demo (single container host in an India region). | Reversible choices made now so agents stop asking. The LLM provider affects cost and data residency, hence the explicit confirmation request. |
| 2026-09-17 | **Coordination protocol adopted** (`coordination/README.md`): GitHub issues from the Agent-task template with one `agent:*` label; `agent-<name>/issue-<n>` branches; PR template; review by a different agent than the author; founder merges; Decision Log and register are not reopened by agents; weekly board sync. `GEMINI.md` added so Antigravity reads `AGENTS.md`. | Removes the founder from the relay path; the process itself becomes a portfolio artefact. |
| 2026-09-17 | **Planning documents drafted:** `docs/strategy/Roadmap.md` (portfolio roadmap, milestones M0–M5; the first draft's 13-week calendar was withdrawn, see the next row), `docs/Execution_Plan.md` (work packages WP-xx with owner/reviewer/verification and issue seeds), `docs/strategy/GTM_Plan.md` (portfolio-mode GTM). Module PRDs for Secure Vault, Finance and Health drafted at v0.1. **The module PRD scopes are proposals until the founder confirms.** | Item 5/8/9/11 of the founder's list. |
| 2026-09-17 | **No dates and no capacity assumptions in any plan (founder ruling).** The project paused once before; how many hours the founder can give and when things will be done are unknown and must not be assumed. Roadmap v0.2, Execution Plan v0.2 and GTM Plan v0.2 are ordered by dependency and gated by exit criteria; GitHub milestones carry no due dates; sizes S/M/L are relative. Supersedes the "13-week" wording in the row above. | A plan that assumes a cadence turns every pause into a slipped plan. Order and gates survive a pause; dates do not. If an external deadline ever appears it is logged here as a decision. |
| 2026-09-17 | **Roster is three agents: Claude Code, Codex, Gemini in Antigravity.** Local Ollama models are not a roster member; Gemini orchestrates them inside Antigravity as sub-agents and stays accountable for their output. The `agent:local` label is retired. Supersedes the four-agent direction and narrows the "Local agent stack" row above to a model recommendation. Roles: AGENTS.md §6 and `coordination/README.md` §1. | Three lanes are as much as one person can merge behind. The local-model experiment continues, but inside one agent's lane where it cannot add coordination load. |
| 2026-09-17 | **Communication channel between the agents:** GitHub issues assign work; `in-progress` label plus `coordination/STATUS.md` show who is doing what; PR reviews carry review verdicts; `coordination/inbox/<recipient>/` carries agent-to-agent and agent-to-founder messages (one file per message, moved to `done/` when handled); `coord:` commits for those two paths may go straight to `main`. Protocol v0.2 in `coordination/README.md`. | Everything is in the repository, so any agent can resume from a cold start and the founder is not the relay. |
| 2026-09-17 | **Default hosted LLM: Claude Haiku**, behind the pluggable LLM gateway (stub for tests, local Ollama for development). Confirmed by the founder. | Closes the open item in the technology-choices row. The PII boundary still applies: the hosted model sees only the utterance and non-PII context. An Anthropic API key is needed at WP-29, not before. |
| 2026-09-17 | **Founder named in the documents: Shantanu Chaudhary.** The pen name "Alfred" is replaced across AGENTS.md, the tracker, the specs' governance tables and the strategy documents (name only; no spec version bumps). | Two names for one person confused the agents' instructions. The claude.ai project and the local archive still show the old name. |
| 2026-09-17 | **Standing rule: rulings are presented in chat at the end of each session**, with explanation, implications and a recommendation, plus what is already decided and the defaults that apply if the founder does not object (AGENTS.md §6). A copy goes to `coordination/inbox/founder/`. | The founder should not have to dig through documents to find what is waiting on them. |
| 2026-09-17 | **Design principle: recommended values are defaults, not constants.** Where a rule is a matter of family preference (who is reminded and when, who sees which document, when a dose counts as missed), the recommended value ships as the default and the family can adjust it; how, and how far, is designed when the section concerned is detailed. Safety gates are the exception and are not adjustable: the five payment gates, no admin override of a blocked balance check, consent rules, the public-surface block, audit logging. | Founder ruling. Keeps Phase 1 simple (defaults only) without closing the door on customisation, and states up front what will never be a setting. |
| 2026-09-17 | **Vault document visibility (OI-6):** default by document class — family documents (RC, insurance, property) visible to admins and members; personal identity documents (PAN, passport, licence) private to the holder; per-document switch for the holder. Adjustable; degree decided when `SHOW_DOCUMENT` is detailed. | Adds a `visibility` attribute to vault document metadata in the Vault PRD v0.2. |
| 2026-09-17 | **Vault expiry reminders (OI-1):** default recipients are the holder (if an adult) and the admins, at 30 and 7 days; for minor, managed and passive holders, the admins and the primary proxy. Adjustable. | — |
| 2026-09-17 | **Consent for a managed profile (Health OI-2):** the primary proxy grants with their own passkey, recorded in the new `consent_records.proxy_consent_user_id`; the secondary proxy only when the primary is unavailable; audit action `PROXY_CONSENT_GRANTED`. Consent Manager v1.3 §2.6 and Data Model v1.3 (change 15) carry it; both go to Codex review round 2. | Done before the re-freeze so it costs no migration. The Consent Manager is therefore no longer fully frozen until round 2 approves the one addition. |
| 2026-09-17 | **Defaults accepted:** dose MISSED after 2 × notify timeout (adjustable); `CHECK_BALANCE` denied for `elder` (any per-family grant goes through `role_module_permissions`, settled in MR round 2); no admin override of a blocked balance check (not adjustable); passkeys as the biometric stand-in with a dev-only PIN off in the demo build; typed intent in the first end-to-end test; branch protection without "include administrators" so `coord:` commits can reach `main`. | — |
| 2026-09-17 | **Codex runs as the Codex desktop app, not the CLI.** The CLI was only needed as the harness for a local-model agent; local models now sit under Gemini in Antigravity. Python 3.12 is not installed by hand either: uv downloads it the first time the project is synced. Workstation setup is therefore WSL 2, Docker Desktop, and signing the two agents in. | Less to install. `tools/agent-local.ps1` and `tools/codex-config.example.toml` remain as an unused optional harness. |
| 2026-09-17 | **Go-ahead given for GitHub milestones (no due dates) and the Phase 0–1 issues.** Created the same day from Execution Plan Appendix A. | Issues whose dependencies are open carry `blocked`. |
| 2026-09-17 | **While Codex is unavailable (credits reset on Sunday):** the round-2 spec reviews (#9, #10) wait for Codex; the specs stay unfrozen until then and all other work continues against the current text (expect small changes at the freeze). Scaffolding and CI (#5, #6) also wait for Codex. Claude Code reviews Gemini's PRs in the meantime (fallback-reviewer rule). | Keeps the two-model-family review and each agent's lane intact; nothing on the near-term list needs the freeze. |
| 2026-09-17 | **One git worktree per agent:** `D:\FamilyLifeOS` (founder, Claude Code, always `main`), `D:\FamilyLifeOS-codex`, `D:\FamilyLifeOS-gemini`. Coordination commits go through `tools/coord.ps1`. Protocol v0.3. | A shared checkout let one agent's commit sweep up another's edits; with code it would also mean branches switching under a working agent. |
| 2026-09-17 | **No Jira; a GitHub Projects board over the existing issues.** | Jira would be a second source of truth that every agent needs new access to, and it loses the issue–PR link. The board gives the visual view with nothing to sync. |
---

| 2026-09-17 | **One home per fact; living documents checked by script.** Document versions and states live only in each document's Status line, with `docs/INDEX.md` generated from them. The plan has two levels and no more: Roadmap (phases, gates, milestones) and Execution Plan (work packages). Live status is the GitHub issues, milestones and project board, not a file: `coordination/BOARD.md` is retired and the board is kept in step by `tools/board_sync.py`. The tracker keeps the current state, decisions, change log, register, open gaps, Build Gate and parking lot; its February 2026 sections moved verbatim to `docs/reference/Project_Tracker_Snapshot_2026-02.md`. `tools/docs_index.py --check`, `tools/living_docs_check.py` and (once merged) `tools/xref_check.py --strict` run on every pull request. | An audit found the tracker's status overview days out of date and the same facts hand-copied in up to nine places. Discipline failed within a day; a failing check does not. The Roadmap and Execution Plan stay Markdown because they hold reasoning, gates and definitions, which change rarely; GitHub's roadmap view needs dates, which this project does not use. |
| 2026-09-21 | **Erase the person, keep an empty placeholder.** The nightly purge deletes a person's data and empties their `users` row in place (`purged_at`); the row is never deleted. Audit rows are never rewritten or cascaded. | Founder ruling on Codex #10 finding 5. "Purge after 24 hours" and "audit rows are append-only and point at the user" could not both hold. DM v1.4 §7.1, CM v1.4 §2.2. The threat model reviews the list of what is kept. |
| 2026-09-21 | **Child protections follow a marker, not the role.** `users.is_child`: always true for `minor`, optional for `managed` (an infant has no login). Parental consent and the no-analytics rule key on it. | Founder ruling on Codex #10 finding 10. The proxy-consent rule had treated every managed profile as an adult. DM v1.4 §3.2, CM v1.4 §2.5–2.6. |
| 2026-09-21 | **Date of birth is disclosed in the DigiLocker consent.** Read in memory to derive milestones, never stored or logged; the milestone is stored and treated as sensitive. Disclosure 2.0.0, material change. | Founder ruling on Codex #10 finding 17. Keeps the "Arjun turns 18" milestone; no real user has consented under the old wording. CM v1.4 §3.2. |
| 2026-09-21 | **Admin copies of medication alerts cover dependants only.** For managed profiles and children, admins get copies by default (adjustable). An adult's alerts reach anyone else only if that adult turns sharing on. | Founder ruling on Codex PR #25 finding 5. A family preference must not give an admin another adult's health data. Health PRD v0.3 §4.6. |
| 2026-09-21 | **The kernel owns both phases of a payment.** Phase 1 and Phase 2, the session and every `BILL_PAYMENT_*` audit row are the kernel's; the module owns its business row and ledger. New first-party purpose HEALTH_MEDICATION_REMINDERS. Per-family settings are typed module tables, no settings service. | Codex round-2 recommendations accepted by Claude Code within the existing rulings (no safety gate becomes a setting). FTS v1.3 §4.6, MR v1.2 §6.4–6.7, CM v1.4 §3.2, DM v1.4 §9.3. |
---

## 📁 Consolidation and Change Log

| Date | Change |
|---|---|
| 2026-09-21 | WP-11 (#11): Codex's round-2 verdicts on #9 and #10 applied as one change-controlled revision: Data Model v1.4, Consent Manager v1.4, Module Registry v1.2, FTS v1.3 (FTS was frozen; §4, §5.3, §6, §11.3 edited under change control). AGENTS.md invariants 7, 12, 13, 17, 19, 22, 23, 35 updated. Data Model "change 16" (`v_guardians`) moved out of PR #22 into this revision. Register items 19–27 added. |
| 2026-09-17 | `Tech_Spec_Simulator_Architecture.md` drafted at v0.1 (WP-12): four WireMock simulators, scenario contract table for stub generation, BBPS state machine for crash scenarios A–D and the Healer, chaos driver, contract tests, simulated-versus-real table. Six open issues, one of which (payment request carries a VPA and account number versus invariant 9) is a candidate register item for the threat model. Claude Code now has its own worktree (`D:\FamilyLifeOS-claude`) for branch work. |
| 2026-09-17 | Living-documents restructure (#27): tracker reduced from about 1,000 lines to about 250 with a "Current state" block; February 2026 sections moved to a snapshot file; `coordination/BOARD.md` retired; version and status columns removed from AGENTS.md and README in favour of the generated `docs/INDEX.md`; AGENTS.md §7 and §8 reduced to rules and pointers; Roadmap v0.3 and Execution Plan v0.4 stop recording status; Module Registry given a standard Status line; new tools `docs_index.py`, `living_docs_check.py`, `board_sync.py`; workflow `docs-checks`. The first run of the new check found a leftover week number in the Execution Plan, now removed. |
| 2026-09-16 | Repository consolidated. Every `.docx`, duplicate `.md`/`.txt` export, superseded spec version and AI review note moved to `archive/originals/`. Canonical documents converted to Markdown under `docs/` (`strategy/`, `specs/`, `runbooks/`, `reference/`, `templates/`); spec content unchanged, formatting only. `AGENTS.md` (shared agent instructions), `CLAUDE.md` (pointer) and `README.md` added. This tracker carried forward from `FAMILYLIFEOS_PROJECT_TRACKER_UPDATED.md` with: Module Registry draft acknowledged, missing documents listed, Cross-Document Inconsistency Register added, repo-based maintenance steps, stale-timeline warning. |
| 2026-09-16 | Recovered the four foundational documents (PRD Core v2.1, Supervisor State Machine v2.1, NFR v2.1, Vision Parking Lot v2.0) from the claude.ai project "FamilyLife OS" knowledge files and placed them under `docs/` (raw exports in `archive/claude-project-exports/`). Missing Documents section closed; Inconsistency Register items 5, 9 and 14 updated, item 15 added; AGENTS.md carries the project's standing instructions. Repository put under git. |
| 2026-09-17 | Spec close-out: Data Model v1.3, Module Registry v1.1 (review round 1), FTS v1.2, Consent Manager v1.2, Runbook v1.2, Master Context v2.1, PRD Core v2.2, NFR v2.2. Module PRDs, Roadmap, Execution Plan, GTM Plan drafted. Coordination protocol, issue/PR templates, GEMINI.md, local-agent setup added. Inconsistency Register: all 15 items resolved or annotated; two follow-ups open. |
| 2026-09-17 | Worktrees created (`D:\FamilyLifeOS-codex`, `D:\FamilyLifeOS-gemini`) and `tools/coord.ps1` tested; PR #17 merged (M0 reached in substance: agent-authored, cross-reviewed, founder-merged; CI does not exist yet); WP-01 closed; PR #19 (WP-47 local-model harness) reviewed, three small changes requested; measured `qwen3.5:9b` on the founder's machine: 43.7 tokens/s with thinking off, 100% GPU at 4K context, 16%/84% CPU/GPU at 16K; GitHub Projects board created and populated (<https://github.com/users/shantanu2209/projects/2>). |
| 2026-09-17 | Agents onboarded (WP-01, WP-02): WSL 2 and Docker Desktop verified; Codex and Gemini passed the role-and-invariants check; Gemini's first PR (#17, docstrings and lint on `tools/docx2md.py`) reviewed by Claude Code in Codex's absence, output byte-identical on all 14 archived Word files. Protocol additions: stage by path in the shared folder; fallback reviewer when the default one is unavailable. WP-47 added (local-model delegation harness for Gemini). Codex is out of credits until its reset; nothing posted yet on #9 and #10. |
| 2026-09-17 | Founder rulings recorded (Decision Log): configurable-defaults principle, Vault OI-1 and OI-6, Health OI-2 and OI-5, Finance OI-6 and OI-7. Consent Manager v1.3 (§2.6 proxy consent) and Data Model v1.3 change 15 (`proxy_consent_user_id`, `PROXY_CONSENT_GRANTED`; taxonomy now 41 codes). Workstation setup simplified (Codex desktop app, no manual Python install). GitHub milestones and the Phase 0–1 issues created. |
| 2026-09-17 | Founder corrections applied: dates, week numbers and founder-hour assumptions removed (Roadmap v0.2, Execution Plan v0.2, GTM Plan v0.2, BOARD); roster reduced to three agents with local models under Gemini; `coordination/STATUS.md` and `coordination/inbox/` added (protocol v0.2) with onboarding messages for Codex and Gemini and the open rulings for the founder; roster, roles and the session close-out rule added to AGENTS.md §6; `docs/reference/Workstation_Setup.md` written from a check of the machine; pen name "Alfred" replaced by Shantanu Chaudhary everywhere (name only, no version bumps); three stale open issues in the Finance PRD marked settled. |
| 2026-09-17 | Decision Log added (portfolio-first scope, public repo without archive, NFR v2.2 path, agent roster direction). Git history recreated without `archive/`; repository published on GitHub. |
| 2026-02-21 | Previous tracker update: Runbook_DPI_Rate_Limits v1.1 frozen; 3 of 5 P0 docs done. |

---

---

## 📋 Documents still to be written

Existing documents and their versions are in `docs/INDEX.md`. This table lists only what does not exist yet, and what earlier plans called for that has been absorbed elsewhere.

| Priority | Document | Purpose | Where it is planned |
|---|---|---|---|
| P1 | `docs/specs/Test_Automation_Strategy.md` | Test tiers, determinism rules, CI gates | Written, in review (PR #23); the PR removes this row |
| P1 | `docs/specs/Security_Threat_Model.md` | Entry points, trust boundaries, abuse cases, mitigations; required before any internet-facing deployment | Execution Plan WP-42; checklist under "Open gaps" below; NFR v2.2 §9 |
| P1 | `docs/reference/Development_Environment_Setup.md` | Fresh-clone guide once there is code | WP-14 |
| P1 | `docs/specs/UX_Error_Message_Library.md` | User-facing strings for FIN, MOD, VAULT and HEALTH codes in English and Hindi | Not yet a work package; needed before the PWA shows errors (WP-30) |
| P2 | `docs/reference/Architecture_Overview.md`, `docs/strategy/Build_Log.md`, `docs/runbooks/Runbook_Demo_Deployment.md` | Portfolio artefacts and the demo runbook | WP-43, WP-44 |
| — | Golden utterance set (English, Hindi, Hinglish) | Routing-accuracy tests | WP-29; Test strategy OI-3 |

Absorbed or dropped (so that nobody writes them again): `Tech_Spec_Supervisor_Concurrency_Control.md` → FTS §9 and Data Model §3.11 (`resource_lock`). `Tech_Spec_Audit_Log_Implementation.md` → Data Model §3.6, §3.18 and FTS §11.3. `Tech_Spec_Scalability_Architecture.md` and `Disaster_Recovery_Plan.md` → NFR v2.2 §6–§7 state the targets; nothing is built for them in portfolio mode. `Tech_Spec_Observability_Stack.md` → WP-41. `CI_CD_Pipeline_Spec.md` and `Testing_Strategy.md` → `Test_Automation_Strategy.md` §7. `API_Documentation.md` → generated from the FastAPI application. `Marketing_GTM_Strategy.md` → `GTM_Plan.md`; commercial GTM stays in Master Context §14. `User_Onboarding_Flow.md` → P4, not planned.

---

## ⚠️ Cross-Document Inconsistency Register

Found during the 2026-09-16 consolidation by reading every document end to end; resolved or annotated on 2026-09-17 after the founder's rulings. Abbreviations: DM = Data_Model_Schema, FTS = Tech_Spec_Financial_Transaction_Safety, CM = Tech_Spec_Consent_Manager, RB = Runbook_DPI_Rate_Limits, MR = Tech_Spec_Module_Registry, MC = Master_Context. Implementers must not pick a side on any item marked open; add new conflicts as rows.

| # | Topic | The conflict (as found) | Resolution | Status |
|---|---|---|---|---|
| 1 | Resource lock storage | DM §3.7 column vs FTS §9 separate table | Founder ruling: dedicated table. DM v1.3 §3.11 (`resource_lock` with released_at/release_reason, partial unique index); Q7 rewritten; FTS v1.2 §9.2 note maps `DELETE` to the release UPDATE; MR v1.1 §7.3 updated. | ✅ Resolved 2026-09-17 |
| 2 | Session column names | DM `fsm_state` vs FTS/CM `session_status`; four columns missing | Founder ruling: keep `fsm_state`, add columns. DM v1.3 §3.7 adds intent_type, bbps_transaction_ref_id, healer_poll_count, session_notes; FTS v1.2 and CM v1.2 renamed throughout. | ✅ Resolved 2026-09-17 |
| 3 | Role vocabulary | DM/MC spouse, child vs PRD/MR member, minor vs CM upper-case | Founder ruling: rename the DB now. DM v1.3 §3.2, §4, Q1, Q2, §8 use admin, member, minor, elder, staff, managed, passive; CM v1.2 lowercase; MC v2.1 §2.2 note. | ✅ Resolved 2026-09-17 |
| 4 | Agent transport and deployment | MC §3.3–3.4 REST/JWT/RabbitMQ/K8s vs MR §2 monolith | MC v2.1 §3.3–3.4 annotated for the Phase 1 monolith. | ✅ Annotated 2026-09-17 |
| 5 | Circuit-breaker thresholds | NFR 3 vs MC/PRD 5 | Two layers (DPI gateway vs module). Notes in NFR v2.2 §3, PRD v2.2 §4.6, MC v2.1 §3.4; MR §6.5 unchanged. | ✅ Annotated 2026-09-17 |
| 6 | Audit hash formula | MC §6.1 DB CHECK vs DM §3.6 app-computed | MC v2.1 §6 defers to DM; DM v1.3 clarifies NULL previous_hash → '' and adds the write protocol (§3.18). | ✅ Resolved 2026-09-17 |
| 7 | Audit action codes | Different sets across DM, FTS, RB, CM, MR | DM v1.3 §6 is the union (40 codes); BILL_PAYMENT_SUCCESS → BILL_PAYMENT_EXECUTED, CONSENT_REVOKED → CONSENT_WITHDRAWN; RB v1.2 §10.3 query fixed. Typed payloads still P1 (Audit Log spec). | ✅ Resolved 2026-09-17 |
| 8 | Healer cadence | 5 min (FTS) vs 15 min (DM §7.4 comment, FSM §1.4) | DM v1.3 §7.4 runs every 5 minutes and no longer aborts EXECUTION sessions (latent bug found in the same pass); FSM §1.4 header note already marks the placeholder as superseded. | ✅ Resolved 2026-09-17 |
| 9 | Biometric threshold | NFR ₹2,000 vs FTS ₹100 vs FTS G4 all amounts | G4 is operative for BBPS; ₹100 is the FSM tier boundary. FTS v1.2 §1.3 reworded; NFR v2.2 §2.2 layering note; MR v1.1 PAY_BILL example = 0. | ✅ Resolved 2026-09-17 |
| 10 | `offline_task_queue.status = 'cancelled'` | CM used it; DM CHECK lacked it | DM v1.3 §3.9 adds 'cancelled'; CM v1.2 comment. | ✅ Resolved 2026-09-17 |
| 11 | `fetch_count_today` semantics | DM daily counter/Q6 check vs RB hourly Redis enforcement | DM v1.3 §3.5, Q6, §7.3 and RB v1.2 §3.1: Redis enforces, the column is bookkeeping for renewal inheritance and audit. | ✅ Resolved 2026-09-17 |
| 12 | Tables defined outside the Data Model | consent_records, disclosures, registry tables, views | All folded into DM v1.3 §3.12–3.17 (expiry index renamed idx_consent_records_expiry); CM v1.2 and MR v1.1 point at it as the DDL source. | ✅ Resolved 2026-09-17 |
| 13 | Module Registry date | 2026-07-03 vs 2026-02-21 elsewhere | Authored date kept; tracker corrected. | ✅ Done 2026-09-16 |
| 14 | Missing foundational documents | PRD Core, FSM, NFR, Vision Parking Lot absent | Recovered from the claude.ai project; now under docs/. | ✅ Done 2026-09-16 |
| 15 | Resource-lock scope | PRD §6 per user vs FTS §9.4 per family | PRD v2.2 §6 now says per family; PRD §9 keeps a note for a possible per-user case (payer identity in the key) to decide during the Finance PRD review. | ✅ Annotated; follow-up open |
| 16 | *(found 2026-09-17)* `requires_consent_providers` listed bbps and bhashini | No such consent handles exist; PAY_BILL could never pass the gate | MR v1.1 narrowed the enum to aa, abha, digilocker, ondc; DM v1.3 added 'ONDC' to consent_handles.provider so ONDC_ADDRESS_SHARE can be gated. | ✅ Resolved 2026-09-17 |
| 17 | *(found 2026-09-17)* `MOD_EXECUTION_UNCONFIRMED` sent sessions to FAILED | Healer sweeps only EXECUTION; unconfirmed payments would vanish from recovery | MR v1.1 §9: session stays in EXECUTION with the lock held; Healer resolves. | ✅ Resolved 2026-09-17 |
| 18 | *(found 2026-09-17)* `core.fn_append_audit` undefined and would have moved hashing into the DB | Contradicted DM §3.6 (app-computed, canonical JSON) | DM v1.3 §3.18 two-function protocol; MR v1.1 §7.2 grants both. | ✅ Resolved 2026-09-17 |
| 19 | *(found 2026-09-21, Codex PR #20 f3)* What CONSENT_REVERIFY detects | CM §5.2 polls the provider only when `revalidation_required` is set; the simulator spec claimed the gate catches any external revocation | CM v1.4 §5.2 states the limit; the simulator spec and test strategy test the flag path and the provider-error path separately and claim no more | ✅ Resolved 2026-09-21 (documented limit, no behaviour change) |
| 20 | *(Codex #9 f1)* Who writes Phase 2 | MR v1.1 had the module write the payment audit row; FTS §4.3 needs audit and session in one transaction | Kernel owns Phase 1 and Phase 2; FTS v1.3 §4.6, MR v1.2 §6.7 | ✅ Resolved 2026-09-21 |
| 21 | *(Codex #10 f5)* Purge versus append-only audit | DM §7.1 hard-deleted users; `audit_log.user_id` and four other columns reference them | Founder ruling: empty the row in place. DM v1.4 §7.1, CM v1.4 §2.2 | ✅ Resolved 2026-09-21 |
| 22 | *(Codex #10 f6)* Deletion aborted EXECUTION sessions | DM §4.3 and CM §2.2 aborted them; DM §7.4, FTS and AGENTS invariant 19 forbid it | DM v1.4 §4.3, CM v1.4 §2.2: never abort EXECUTION; purge waits for the Healer | ✅ Resolved 2026-09-21 |
| 23 | *(Codex #10 f10)* "Managed means adult" | CM v1.3 §2.6 versus DM §3.2 (infants are managed) | Founder ruling: `users.is_child`. DM v1.4 §3.2, CM v1.4 §2.5–2.6 | ✅ Resolved 2026-09-21 |
| 24 | *(Codex #10 f11–f12)* State and intent names that are not stored values | MR `BLOCKED`, CM `CONSENT_REVERIFY_FAILED`, FTS override exit state, FTS `BILL_PAYMENT` intent and biller path | DM v1.4 §3.7 mapping table and `resource_key`; FTS v1.3 §5.3, §11.3 | ✅ Resolved 2026-09-21 |
| 25 | *(found 2026-09-21)* FTS §4.5 crash scenario B versus §6.4 | The crash table said NOT_FOUND → FAILED; §6.4's hard rule says resubmit with the original key within 24 h | FTS v1.3 §4.5 follows §6.4 | ✅ Resolved 2026-09-21 |
| 26 | *(found 2026-09-21)* Free text in an audit payload | FTS §11.3 writes the admin's typed `reason` into `ADMIN_SESSION_OVERRIDE` details; DM §6 allows no free text (a reason can name a person) | Not resolved in WP-11: needs a decision on where the reason lives (a kernel table with its own retention, or a fixed reason list). Goes to `Tech_Spec_Audit_Log_Implementation.md` and the threat model | ⏳ Open |
| 27 | *(found 2026-09-21)* CM §4.1 still prints the v1.3 `consent_records` DDL | DM v1.4 §3.12 is the only DDL source and has three more columns and a composite FK | CM v1.4 §4.1 carries a warning; the copy is removed at the next CM revision | ⏳ Open (low) |

Open follow-ups: (a) Codex's targeted re-review of DM v1.4, CM v1.4, MR v1.2 and FTS v1.3, then re-freeze; items 26 and 27; (b) item 15's per-user case, decided in the Finance module PRD review.

---

---

## 🚨 Open gaps and risks

Resolved gaps from the February list (zombie recovery, family graph schema, consent lifecycle, DPI rate limits, concurrency control, audit log implementation, scalability and disaster-recovery targets, test strategy) are in the snapshot file with what resolved them. Still open:

#### 8b. Security Threat Model Missing *(P1 since 2026-09-17; was late-P0 — see Decision Log)*
**Issue:** System handles DPI webhooks, health data, financial execution, and biometric auth — but no formal adversarial model exists  
**Risk:** First external DPI integration creates attack surface that hasn't been mapped  
**Impact:** Undiscovered privilege escalation, webhook forgery, or Redis poisoning in production  
**Escalation Reason:** Both independent reviewers (Round 3) explicitly flagged this as required before first external integration, not post-MVP. Webhook endpoints for `revalidation_required` are live attack surface.  
**Action Required:**
- [ ] Map all entry points (API endpoints, DPI webhooks, push notifications, biometric callbacks)
- [ ] Define trust boundaries (what's trusted: authenticated admin session; untrusted: DPI webhook payloads, ONDC seller responses)
- [ ] Document token storage risk (AA/ABHA consent handles in DB — what happens if DB is compromised?)
- [ ] Model webhook forgery risk (attacker flips `revalidation_required` for all users — DoS on every transaction)
- [ ] Document privilege escalation paths (can a Staff user escalate to Admin? Can a shadow node exploit invite flow?)
- [ ] Document insider DBA tampering scenario (audit log hash chain verification is the mitigation — confirm it's sufficient)
- [ ] Document Redis poisoning scenario (corrupted session state — what's the blast radius?)
- [ ] Map DPDP Act breach notification obligations against each threat scenario  
**Owner:** TBD  
**Deadline:** before any internet-facing deployment, demo included (Roadmap Phase 4); scope fixed in NFR v2.2 §9 (Security_Threat_Model.md)

#### 6. Error Message Taxonomy Missing
**Issue:** Only happy-path scenarios documented, no error states  
**Risk:** Poor user experience, hard to debug production issues  
**Impact:** High support burden, user frustration  
**Action Required:**
- [ ] Create error code taxonomy (FIN_001: Insufficient balance, FIN_002: Bill payment failed, HEALTH_001: ABHA consent expired, etc.)
- [ ] Write user-facing messages in English + Hindi for each error code
- [ ] Design error state UI (wireframes for inline errors, modal errors, toast notifications)
- [ ] Add resolution guidance for each error type ("Check bank balance", "Retry in 5 minutes", "Contact support")
**Owner:** TBD  
**Deadline:** Week 3 (UX_Error_Message_Library.md)

*Status 2026-09-17:* the code taxonomies exist (FIN_001–FIN_015 in FTS §10; MOD codes in the Module Registry §9; VAULT and HEALTH codes proposed in the module PRDs). What is missing is the message library itself and the error-state UI, listed under "Documents still to be written".

### Strategic Risk Register

- **⚠ "Cathedral before church" risk** *(Raised by Reviewer 1, Feb 2026. Confirmed by Reviewer 1 post-v1.1)*: Architecture maturity is 8.7/10. Vertical slice readiness is 0/10. These are correctly decoupled — but the risk is that doc phase extends indefinitely. **Hard gate enforced:** No P2 feature docs begin until the Phase 1 Build Gate is passed (see below). Architecture is a means to ship, not an end.

---

## 🏗️ Phase 1 Build Gate

*Defined by Reviewer 1 (CTO-mode review, Feb 2026). These are the specific crash scenarios that must pass before any new feature docs are written. This gate converts "architecturally coherent" to "actually ships."*

**Pre-conditions (P0 docs that must exist first):**
- [x] Data_Model_Schema v1.3 written (2026-09-17) — Codex review round 2 pending, then re-freeze
- [x] Tech_Spec_Financial_Transaction_Safety v1.2 — FROZEN
- [x] Tech_Spec_Consent_Manager v1.3 — v1.2 FROZEN text plus §2.6 (proxy consent); Codex round 2 pending
- [x] Runbook_DPI_Rate_Limits v1.2 — FROZEN
- [x] Tech_Spec_Module_Registry v1.1 — review round 1 applied; Codex round 2 pending, then freeze
- [x] Inconsistency Register items 1–3 resolved in Data Model v1.3 (2026-09-17)
- [x] PRD Core v2.2, Supervisor FSM v2.1 and NFR v2.2 in the repository and aligned
- [ ] Codex review round 2 complete; both documents frozen
- [ ] Tooling on the founder's machine (WSL 2, Docker Desktop; Codex desktop app and Antigravity opened on the repository)

**Infrastructure to build (Docker Compose — no more, no less):**
- [ ] PostgreSQL (with all 10 schema tables from Data Model v1.2.1)
- [ ] Redis (for supervisor_sessions hot state + Healer distributed lock)
- [ ] WireMock for BBPS simulator (5 scenarios: SUCCESS, FAILED, PENDING, NOT_FOUND, 429, Timeout)
- [ ] WireMock for AA simulator (balance fetch, consent validation)
- [ ] Environment variables template

**Build targets (in this order):**
- [ ] resource_lock table + acquire/release logic
- [ ] supervisor_sessions lifecycle (IDLE → EXECUTION → SUCCESS_CONFIRMATION / FAILED)
- [ ] audit_log write with hash chain (canonical JSON, SHA-256)
- [ ] Healer cron (distributed lock, priority queue, per-run cap, system circuit breaker)
- [ ] FinanceAgent → BBPS call + Phase 2 commit

**Crash simulation checklist (all 4 must pass before gate opens):**
- [ ] **Crash Scenario A:** Server crashes after Phase 1 COMMIT, before BBPS call → Healer detects zombie (NOT_FOUND) → marks FAILED → releases lock
- [ ] **Crash Scenario B:** Server crashes after BBPS SUCCESS, before Phase 2 COMMIT → Healer detects zombie (SUCCESS) → queues AUDIT_LOG_WRITE (P1) → writes audit log → notifies user
- [ ] **Crash Scenario C:** Phase 2 DB crash (COMMIT fails) → identical to B above (session stays in EXECUTION, Healer reconciles)
- [ ] **Crash Scenario D:** Server crashes after Phase 2 COMMIT, before lock release → Healer detects stale lock on SUCCESS_CONFIRMATION session → releases lock

**Playwright E2E test (1 test, must pass):**
- [ ] "Priya pays BESCOM bill" — full flow: voice intent → RBAC → resource lock → AA balance fetch → biometric approval → CONSENT_REVERIFY → BBPS call → Phase 2 commit → push notification → lock release → audit log verified

**Gate status: 🔴 BLOCKED** (Codex review round 2 of Data Model v1.3 and Module Registry v1.1 pending; tooling installation pending). Work packages for the gate are WP-xx in `docs/Execution_Plan.md`.

---

## 📌 Near-term parking lot

Long-term vision items are in `docs/strategy/Vision_Parking_Lot.md`.

### Schema Evolution (Deferred from Data_Model_Schema v1.2 review)
*These items were raised in post-review feedback and deliberately deferred. Schema is frozen at v1.2. Revisit each item at the trigger conditions listed.*

- **Push token column encryption** (`device_registry.push_token`): Leaked push tokens can enable phishing. At Phase 1 scale (10-100 families, single-server DB), column-level encryption adds operational complexity that isn't justified. Revisit when database backups are being shared externally or at 10K+ families. Implementation: pgcrypto `PGP_SYM_ENCRYPT` or application-layer encrypt before INSERT.

- **🔶 Audit log payload schema enforcement** *(escalated — required before first real user, not post-MVP)*: Mandate pre-defined typed payload shapes per action code to prevent accidental PII leakage in `details` JSONB. Currently relies on developer discipline + comment warnings. Full enforcement (Pydantic model per action code, validated before INSERT) belongs in `Tech_Spec_Audit_Log_Implementation.md` (P1 doc, Week 4). **Must be implemented before any real user data enters the system.** Reviewer 1 specifically flagged this as high-value pre-launch item.

- ~~**Webhook signature validation for `revalidation_required` flag**~~: ✅ **CLOSED** by Tech_Spec_Consent_Manager_v1.0 §9. Full HMAC validation specified: JWS signature validation for Sahamati AA webhooks (§9.3), JWT validation for ABDM ABHA webhooks (§9.4), replay prevention via Redis txnid/jti deduplication (10-min TTL), 5-minute timestamp window, JWKS cache with 24h refresh, safe-default rejection when JWKS unavailable. Attack surface fully addressed.

- **supervisor_sessions table partitioning by month**: At Phase 1 scale, the sessions table will have thousands of rows, not millions. Partition by `created_at` month when approaching 100K+ families or if cleanup jobs show table bloat. Implementation: PostgreSQL declarative partitioning (`PARTITION BY RANGE (created_at)`).

- **audit_log archiving / partitioning for 7-year retention**: 7-year legal retention with high-volume writes will produce a very large table. Partition by month; archive partitions older than 2 years to cold storage (S3 Glacier with Parquet + Athena for querying). Trigger: when approaching 10K families with active financial transactions.

- **Rolling window rate limiting for AA fetches**: Current implementation uses calendar-day `fetch_count_today` reset at midnight UTC. AA's actual rate limit may be a rolling 1-hour window. Verify Sahamati network documentation once FIU license is granted and adjust if needed. Calendar-day is a reasonable approximation until then.

- **`(user_id, status)` secondary index on consent_handles**: Marginal performance gain for queries filtering on status alone. The existing `idx_consent_user_provider` composite index covers all current query patterns. Add only if query profiling reveals a slow path.

- **`offline_task_queue` composite idempotency key** *(Phase 1.1)*: Adding `UNIQUE (family_id, task_type, payload->>'idempotency_key') WHERE status IN ('pending','processing')` to the offline_task_queue table would prevent duplicate queue entries if the retry scheduler misfires (e.g. Healer cron fires twice in quick succession due to a deployment restart). Currently tasks rely on payload-level idempotency keys being honoured by the executing worker, which is correct but a belt-and-suspenders DB-level constraint would eliminate the class entirely. Not required for Phase 1 (Healer runs at 5-minute intervals; duplicate firing window is narrow). Add in Phase 1.1 when the Healer is battle-tested and the duplicate scenario has been observed or not. Reviewer 1 flagged as Phase 1.1 refinement.

- **FIN_012 (Debit Confirmed, No ACK) — AA-assisted auto-verification** *(Phase 1.1 — deferred pending AA integration)*: Reviewer 2 suggested that when FIN_012 fires, the Healer could autonomously fetch the bank statement via AA to verify the debit, before alerting Admin. This is architecturally sound — AA can pull the last 24h of transactions from the bank, confirming whether ₹X was debited. If confirmed via AA, Healer can auto-resolve with higher confidence and reduce Admin alert volume. **Deferred reason:** requires AA consent to be live and FinanceAgent data fetch to be working (Tech_Spec_Consent_Manager.md, P0 Week 2). Cannot safely add AA auto-verification to Healer before consent lifecycle is specified. Add in Phase 1.1 after first successful end-to-end AA data fetch in production. Required additions: (a) Healer calls FinanceAgent.fetch_recent_transactions(consent_handle, since=T-24h); (b) matches amount + timestamp to debit; (c) only auto-resolves if match confidence is high; (d) otherwise falls back to Admin alert.

---

## 🔁 Retrospectives

One note per milestone (Roadmap M0–M5).

- (none yet; add one per milestone M0–M5)

---

## 🔄 How this document stays current

1. **One home per fact** (AGENTS.md §6). This file never repeats a document's version, the plan, or who is working on what.
2. **Checked by script on every pull request** (`.github/workflows/docs-checks.yml`): `tools/docs_index.py --check` (the index matches the document headers), `tools/living_docs_check.py` (no version tables outside the index, no calendar in the plans, this file's current state is not older than its newest log entry, retired sections stay retired) and, once merged, `tools/xref_check.py --strict` (no dangling or stale references).
3. **Who writes what:** a decision → a Decision Log row the day it is made (whoever records the ruling). A document changing status, a gap closing, a new inconsistency → a change-log row in the same pull request. The "Current state" block → Claude Code at the end of every working session, after running the checks and `tools/board_sync.py`.
4. **After a pause of any length:** Claude Code runs the three checks and the board sync first, reads `coordination/STATUS.md` and the inboxes, and rewrites "Current state" before anyone builds.
