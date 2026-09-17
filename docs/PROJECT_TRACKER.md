# FamilyLifeOS — Project Tracker & Living Scratchpad

**Purpose:** Living document to track all pending work, identified gaps, and future considerations.  
**Last Updated:** 2026-09-17 (Spec close-out done: Data Model v1.3 and Module Registry v1.1 await Codex review round 2, the other P0 specs are frozen. Planning documents are at v0.2: sequence-only, no dates or capacity assumptions. Roster is three agents with a repository-based channel under `coordination/`. Next: workstation setup and agent onboarding. See the Decision Log and the change log below.)  
**Previous Update:** 2026-02-21 (Runbook_DPI_Rate_Limits_v1.1 — FROZEN. Two independent reviews (R1: 8.8/10, 4 critical fixes; R2: A+, 2 refinements). Eight hardening fixes: AA hourly TTL drift, BBPS Redis fail-closed, env prefix on all Redis keys, AA coalescing timeout observability, Bhashini low-confidence audit event, ONDC progressive seller blacklist, exponential backoff jitter, per-family Bhashini auto soft-throttle. Phase 1 Build Gate: 3 of 5 P0 docs done — 3 frozen, 0 draft. Next: Tech_Spec_Module_Registry.md.)  
**Maintained By:** Shantanu Chaudhary (Lead Product Architect)  
**Location:** `docs/PROJECT_TRACKER.md` — agent working rules live in `AGENTS.md`  

---

## 🎯 Project Status Overview

### Current Phase: **Pre-Development (Documentation & Architecture Nearly Complete)**
- ✅ Master Context v2.0 defined (comprehensive blueprint)
- ✅ Four of five Priority 0 specs frozen (Data Model v1.2.1, Financial Transaction Safety v1.1, Consent Manager v1.1, DPI Rate Limits v1.1)
- 📝 Tech_Spec_Module_Registry.md drafted (v1.0) — two-reviewer round and freeze pending
- ✅ Repository consolidated to Markdown (2026-09-16); originals archived under `archive/originals/`
- ✅ The four foundational documents that were missing at consolidation (PRD Core v2.1, Supervisor FSM v2.1, NFR v2.1, Vision Parking Lot v2.0) were recovered from the claude.ai project on 2026-09-16 and live under `docs/`
- ⚠️ Fourteen cross-document inconsistencies logged (see register below); none blocking documentation, three blocking implementation
- ❌ Development not started

### Critical Path to Development Start
1. ✅ **COMPLETE:** Foundational documents — all six are in the repository as Markdown (four recovered from the claude.ai project on 2026-09-16)
2. 🔄 **IN PROGRESS:** Complete 5 Priority 0 documents — 4 frozen; Module Registry v1.0 in draft (review + freeze)
3. ⏳ **PENDING:** Resolve Inconsistency Register items 1–3 (resource lock storage, session columns, role vocabulary) via Data Model v1.3
4. ⏳ **PENDING:** Build simulator suite
5. ⏳ **PENDING:** Set up development environment
6. ⏳ **PENDING:** Begin implementation (Phase 1 Build Gate targets)

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

## 📁 Consolidation and Change Log

| Date | Change |
|---|---|
| 2026-09-16 | Repository consolidated. Every `.docx`, duplicate `.md`/`.txt` export, superseded spec version and AI review note moved to `archive/originals/`. Canonical documents converted to Markdown under `docs/` (`strategy/`, `specs/`, `runbooks/`, `reference/`, `templates/`); spec content unchanged, formatting only. `AGENTS.md` (shared agent instructions), `CLAUDE.md` (pointer) and `README.md` added. This tracker carried forward from `FAMILYLIFEOS_PROJECT_TRACKER_UPDATED.md` with: Module Registry draft acknowledged, missing documents listed, Cross-Document Inconsistency Register added, repo-based maintenance steps, stale-timeline warning. |
| 2026-09-16 | Recovered the four foundational documents (PRD Core v2.1, Supervisor State Machine v2.1, NFR v2.1, Vision Parking Lot v2.0) from the claude.ai project "FamilyLife OS" knowledge files and placed them under `docs/` (raw exports in `archive/claude-project-exports/`). Missing Documents section closed; Inconsistency Register items 5, 9 and 14 updated, item 15 added; AGENTS.md carries the project's standing instructions. Repository put under git. |
| 2026-09-17 | Spec close-out: Data Model v1.3, Module Registry v1.1 (review round 1), FTS v1.2, Consent Manager v1.2, Runbook v1.2, Master Context v2.1, PRD Core v2.2, NFR v2.2. Module PRDs, Roadmap, Execution Plan, GTM Plan drafted. Coordination protocol, issue/PR templates, GEMINI.md, local-agent setup added. Inconsistency Register: all 15 items resolved or annotated; two follow-ups open. |
| 2026-09-17 | Agents onboarded (WP-01, WP-02): WSL 2 and Docker Desktop verified; Codex and Gemini passed the role-and-invariants check; Gemini's first PR (#17, docstrings and lint on `tools/docx2md.py`) reviewed by Claude Code in Codex's absence, output byte-identical on all 14 archived Word files. Protocol additions: stage by path in the shared folder; fallback reviewer when the default one is unavailable. WP-47 added (local-model delegation harness for Gemini). Codex is out of credits until its reset; nothing posted yet on #9 and #10. |
| 2026-09-17 | Founder rulings recorded (Decision Log): configurable-defaults principle, Vault OI-1 and OI-6, Health OI-2 and OI-5, Finance OI-6 and OI-7. Consent Manager v1.3 (§2.6 proxy consent) and Data Model v1.3 change 15 (`proxy_consent_user_id`, `PROXY_CONSENT_GRANTED`; taxonomy now 41 codes). Workstation setup simplified (Codex desktop app, no manual Python install). GitHub milestones and the Phase 0–1 issues created. |
| 2026-09-17 | Founder corrections applied: dates, week numbers and founder-hour assumptions removed (Roadmap v0.2, Execution Plan v0.2, GTM Plan v0.2, BOARD); roster reduced to three agents with local models under Gemini; `coordination/STATUS.md` and `coordination/inbox/` added (protocol v0.2) with onboarding messages for Codex and Gemini and the open rulings for the founder; roster, roles and the session close-out rule added to AGENTS.md §6; `docs/reference/Workstation_Setup.md` written from a check of the machine; pen name "Alfred" replaced by Shantanu Chaudhary everywhere (name only, no version bumps); three stale open issues in the Finance PRD marked settled. |
| 2026-09-17 | Decision Log added (portfolio-first scope, public repo without archive, NFR v2.2 path, agent roster direction). Git history recreated without `archive/`; repository published on GitHub. |
| 2026-02-21 | Previous tracker update: Runbook_DPI_Rate_Limits v1.1 frozen; 3 of 5 P0 docs done. |

---

## 📂 Repository Layout

```text
FamilyLifeOS/
├── AGENTS.md                      # single set of instructions for all agents and humans
├── CLAUDE.md                      # points to AGENTS.md
├── GEMINI.md                      # points to AGENTS.md (Gemini / Antigravity)
├── .github/                       # issue template (agent task) and PR template
├── coordination/                  # working protocol, handoff template, board
├── README.md                      # human overview + document map
├── docs/
│   ├── PROJECT_TRACKER.md         # this document
│   ├── Execution_Plan.md          # work packages WP-xx (draft v0.1)
│   ├── strategy/
│   │   ├── Master_Context.md      # v2.0 canonical blueprint
│   │   ├── PRD_FamilyLifeOS_Core.md # v2.2 Core PRD
│   │   ├── PRD_Module_Secure_Vault.md / PRD_Module_Finance.md / PRD_Module_Health.md   # draft v0.1
│   │   ├── Roadmap.md             # draft v0.2 (portfolio-first, sequence-only)
│   │   ├── GTM_Plan.md            # draft v0.1 (portfolio mode)
│   │   ├── Vision_Parking_Lot.md  # v2.0 long-term backlog (recovered 2026-09-16)
│   │   ├── Vision_Journey.md      # Jan 2026 white paper (reference)
│   │   └── Master_PRD.md          # Jan 2026 module-level master PRD (reference)
│   ├── specs/
│   │   ├── Tech_Spec_Supervisor_State_Machine.md    # v2.1 canonical
│   │   ├── NFR_Specs.md                             # v2.2 canonical
│   │   ├── Data_Model_Schema.md                     # v1.3 — review round 2 pending
│   │   ├── Tech_Spec_Financial_Transaction_Safety.md # FROZEN v1.2
│   │   ├── Tech_Spec_Consent_Manager.md             # v1.3 (frozen v1.2 + §2.6 in review)
│   │   └── Tech_Spec_Module_Registry.md             # v1.1 — review round 2 pending
│   ├── runbooks/
│   │   └── Runbook_DPI_Rate_Limits.md               # FROZEN v1.2
│   ├── reference/
│   │   ├── DPI_Integration_Primer.md                # Jan 2026 DPI cheat sheet
│   │   ├── Workstation_Setup.md                     # what to install on the founder's PC (WP-01)
│   │   └── Local_Agent_Setup.md                     # local model choice and Ollama tuning (Gemini's sub-agents)
│   └── templates/
│       └── PRD_Template.md
└── archive/
    ├── README.md                  # maps every original to its current home   (archive/ is local-only, gitignored)
    ├── claude-project-exports/    # raw text of the four documents recovered from the claude.ai project
    └── originals/                 # untouched pre-consolidation files (docx, duplicates, old versions)
```

New documents from the Document Status Matrix go to: `docs/specs/` (`Tech_Spec_*`, `Security_Threat_Model.md`), `docs/runbooks/` (`Runbook_*`, `Disaster_Recovery_Plan.md`), `docs/strategy/` (PRDs, GTM, Vision Parking Lot), `docs/reference/` (UX error library, API docs, dev environment setup).

---

## ✅ Recovered Documents (2026-09-16)

The four foundational documents that were absent at consolidation were found as knowledge files in the claude.ai project "FamilyLife OS" and brought in as Markdown (the text claude.ai had extracted from the `.md.docx` uploads, normalised; raw exports kept in `archive/claude-project-exports/`).

| Document | Now at | Notes |
|---|---|---|
| PRD_FamilyLifeOS_Core_v2_1 | `docs/strategy/PRD_FamilyLifeOS_Core.md` | 11 scenarios, 7-role RBAC matrix, automation tiers, conflict-resolution matrix, shared services, KPIs |
| Tech_Spec_Supervisor_State_Machine_v2_1 | `docs/specs/Tech_Spec_Supervisor_State_Machine.md` | FSM diagram (mermaid), state definitions, TTL policy, idempotency keys; §1.4 Healer placeholder superseded by FTS v1.1 |
| FamilyLifeOS_NFR_Specs_v2_1 | `docs/specs/NFR_Specs.md` | Latency budgets, encryption, biometric mandate, idempotency and rate-limit mandates, DPI circuit breaker, telemetry enum, retention |
| Vision_Parking_Lot_v2_0 | `docs/strategy/Vision_Parking_Lot.md` | Long-term deferred features with trigger conditions |

Still not written: `Security_Threat_Model.md` (late-P0, gap 8b) — target path `docs/specs/Security_Threat_Model.md`.

The claude.ai project also holds Data Model v1.2.1, Master Context v2.0 and the updated tracker (the same versions as this repository). It does **not** hold the Consent Manager, Financial Transaction Safety, DPI Rate Limits runbook or Module Registry specs; upload them there if the project stays in use, or treat this repository as the only source.

---

## 📊 Document Inventory & Health Check

### **Foundational Documents**

| Document | Version | Grade (Feb 2026 review) | In repository? |
|----------|---------|------|-------|
| Master Context | v2.1 | **A** | ✅ `docs/strategy/Master_Context.md` |
| Project Tracker (this document) | Living | **A** | ✅ `docs/PROJECT_TRACKER.md` |
| PRD_FamilyLifeOS_Core | v2.2 | **A-** | ✅ `docs/strategy/PRD_FamilyLifeOS_Core.md` |
| Tech_Spec_Supervisor_State_Machine_v2_1 | v2.1 | **B+** | ✅ `docs/specs/Tech_Spec_Supervisor_State_Machine.md` (recovered 2026-09-16) |
| NFR_Specs | v2.2 | **B** (v2.1); gaps closed in v2.2 | ✅ `docs/specs/NFR_Specs.md` |
| Vision_Parking_Lot_v2_0 | v2.0 | **B+** | ✅ `docs/strategy/Vision_Parking_Lot.md` (recovered 2026-09-16) |

Also in the repository, outside the February review set: `docs/strategy/Vision_Journey.md` (Jan 2026 white paper), `docs/strategy/Master_PRD.md` (Jan 2026 module-level master PRD — not the Core PRD), `docs/reference/DPI_Integration_Primer.md`, `docs/templates/PRD_Template.md`.

**Overall Assessment (Feb 2026):** B+ (Very Good, Ready for Development). The per-document assessments below were written on 2026-02-21 against the then-uploaded files and are kept as the reference grades.

---

### **1. Master Context v2.0** - Grade: A ✅

**Status:** Comprehensive foundational blueprint - no updates needed

**What's Excellent:**
- ✅ 14 comprehensive sections (Identity → GTM Strategy)
- ✅ Full PostgreSQL database schema (6 tables with constraints, indexes)
- ✅ Complete DPI risk assessment with mitigation strategies
  - AA: 97% uptime, 3 fetches/hour limit
  - BBPS: 98% success, zombie transaction risk
  - ABHA: 85% uptime, malformed FHIR bundles
  - ONDC: 60% catalog accuracy, seller fraud risk
  - Bhashini: 95% uptime, accent misrecognition
- ✅ Competitive landscape analysis (vs CRED, Google Assistant, Tata Neu)
- ✅ Revenue model with unit economics (LTV:CAC = 6.4:1)
- ✅ Go-to-market strategy with phased acquisition channels
- ✅ Regulatory roadmap (6-9 month FIU/BBPOU/HIU approval timeline)
- ✅ Quantified success metrics (definitions + targets + measurement)

**Action Required:**
- ✅ None - this is your canonical reference

---

### **2. PRD v2.1** - Grade: A- ✅

**Status:** Strong scenario-driven product definition, minor intentional gaps

**What's Excellent:**
- ✅ 11 comprehensive user scenarios (SOS, graceful degradation, vision-based, device context)
- ✅ Clear RBAC matrix (7 role types: Admin, Member, Minor, Elder, Staff, Managed, Passive)
- ✅ Automation tiers well-defined (Level 0-3, with Level 3 forbidden in V1)
- ✅ Conflict resolution matrix (proxy contradictions, agent disagreements, modal contradictions)
- ✅ Shared system services defined (notification engine, translation, OCR, payment routing, auth)
- ✅ Success metrics and GTM sections

**Minor Gaps (Not Blocking):**
- ⏳ References "Family Graph schema" (will add link once Data_Model_Schema.md exists)
- ⏳ References "Consent Lifecycle Manager" (will add link once Tech_Spec_Consent_Manager.md exists)
- ⏳ Mentions "Background Reconciliation (Healer)" as placeholder (will detail in Tech_Spec_Financial_Transaction_Safety.md)
- ⏳ Could expand error scenarios (but happy paths + graceful degradation are comprehensive)

**Action Required:**
- ✅ None right now - gaps are intentional placeholders for Priority 0 docs
- 📅 **Week 3-4:** Update with references to newly created Priority 0 docs
- 📅 **Week 3-4:** Add error scenarios based on UX_Error_Message_Library.md

---

### **3. Tech Spec: Supervisor FSM v2.1** - Grade: B+ ✅

**Status:** Solid state machine definition, needs implementation depth

**What's Excellent:**
- ✅ Clear state machine diagram (13 states: IDLE → INTENT_ANALYSIS → REASONING → EXECUTION)
- ✅ State persistence layer (Redis hot state + PostgreSQL journal)
- ✅ Automation tiers table (Level 0-3 with examples)
- ✅ TTL policy table (bank balance: 15min, health records: 7 days, bills: 24hr, inventory: indefinite)
- ✅ Idempotency keys properly specified (UUID_v4, persisted before API call)
- ✅ CONSENT_REVERIFY state (prevents TOCTOU attacks)
- ✅ Background reconciliation (Healer) mentioned (15min cron job for zombie transactions)

**Minor Gaps (Not Blocking):**
- ⏳ Error state transition matrix missing (which failures are retryable vs terminal?)
- ⏳ Rollback/compensation logic not detailed ("mark as Executed but Unconfirmed" mentioned but recovery workflow missing)
- ⏳ Concurrency control mentioned in PRD but not specified here (need Redis distributed locks)
- ⏳ TTL enforcement mechanism not specified (cron job? cache layer? database triggers?)
- ⏳ Redis volatility mitigation mentioned but PostgreSQL journal schema not detailed

**Action Required:**
- ✅ None right now - core FSM is solid enough to start
- 📅 **Week 3:** Add error state transition matrix in Tech_Spec_Supervisor_Concurrency_Control.md
- 📅 **Week 4:** Add rollback/compensation details in Tech_Spec_Financial_Transaction_Safety.md

---

### **4. NFR v2.1** - Grade: B ✅

**Status:** Good performance/security targets, missing scalability/DR depth

**What's Good:**
- ✅ Performance budgets defined (router: <200ms, inter-agent: <400ms, end-to-end: <2.0s)
- ✅ Encryption standards (AES-256 at rest, TLS 1.3 in transit, PBKDF2 key derivation)
- ✅ Idempotency requirements for financial operations (must persist key before API call)
- ✅ Rate limiting specified (3 AA refreshes/hour)
- ✅ DPI circuit breakers (3 failures → 30min disable, exponential backoff)
- ✅ Data localization (DPDP compliance - servers in India)
- ✅ Audit log retention (7 years for financial/legal compliance)
- ✅ Biometric mandate (required for transactions >₹2000)

**Gaps (Need Attention):**
- ⚠️ **Missing scalability targets** (concurrent users, API RPS, database sharding strategy)
- ⚠️ **Missing disaster recovery plan** (RTO, RPO, backup strategy, failover procedures)
- ⚠️ **Incomplete DPI rate limits** (only AA mentioned, need comprehensive table for BBPS, ABHA, ONDC, Bhashini)
- ⚠️ **No performance degradation strategy** (what gets throttled when at 95% capacity?)
- ⚠️ **No security threat model reference** (Security_Threat_Model.md escalated to late-P0 — required before first external DPI integration, Week 3)

**Action Required:**
- 🟠 **HIGH PRIORITY - Week 2:** Expand DPI rate limits section (create Runbook_DPI_Rate_Limits.md)
- 🟡 **Medium - Week 5:** Add scalability targets in Tech_Spec_Scalability_Architecture.md
- 🟡 **Medium - Week 5:** Add disaster recovery plan in Disaster_Recovery_Plan.md

---

### **5. Vision Parking Lot v2.0** - Grade: B+ ✅

**Status:** Well-organized long-term vision, good as-is

**What's Good:**
- ✅ Blockchain migration (trigger: >100K users, legal product offering)
- ✅ Live spatial reasoning (deferred due to GPU cost, 4G latency challenges)
- ✅ Sub-800ms latency targets (requires edge processing, on-device SLMs)
- ✅ Surface context awareness (hardware partnerships: Echo Show, Nest Hub)
- ✅ Democratic voting mechanisms (family decision-making)
- ✅ Future modules (LegalTech, Real Estate Manager, Philanthropy Agent)

**Minor Improvements Suggested (Not Urgent):**
- ⏳ Add ROI prioritization (which deferred features have highest impact when triggers hit?)
- ⏳ Add effort estimates (developer-weeks per feature for planning)

**Action Required:**
- ✅ None - keep as-is for long-term vision preservation
- 📅 **Post-MVP:** Review and prioritize when approaching trigger conditions

---

### **6. Project Tracker (This Document)** - Grade: A ✅

**Status:** Comprehensive living scratchpad, will evolve weekly

**What's Good:**
- ✅ Document status matrix tracking 20+ documents
- ✅ Critical gaps & risks section (11 blocking/high-priority issues)
- ✅ Complete test automation strategy section
- ✅ Milestone tracker with timelines
- ✅ Weekly update workflow defined

**Action Required:**
- 📅 **Weekly:** Review and mark completed tasks
- 📅 **After major decisions:** Add new items to appropriate sections
- 📅 **Before milestones:** Update roadmap, adjust timelines

---

## 📋 Document Status Matrix (Documents to Create)

| Priority | Document Name | Status | Owner | Target Date | Blocker? |
|----------|--------------|--------|-------|-------------|----------|
| **P0** | Data_Model_Schema.md | 🔄 **v1.3 revision** — Codex review round 2 pending, then re-freeze (v1.2.1 was frozen) | Shantanu Chaudhary | 2026-09-17 | 🔴 YES |
| **P0** | Tech_Spec_Financial_Transaction_Safety.md | ✅ **FROZEN v1.2** | Shantanu Chaudhary | 2026-09-17 | 🔴 YES |
| **P0** | Tech_Spec_Consent_Manager.md | ✅ **v1.3** — frozen v1.2 text plus §2.6 (proxy consent), Codex round 2 pending | Shantanu Chaudhary | 2026-09-17 | 🔴 YES |
| **P0** | Tech_Spec_Module_Registry.md | 🔄 **v1.1** — review round 1 applied (MR §13); Codex round 2 pending, then freeze | Shantanu Chaudhary | 2026-09-17 | 🔴 YES |
| **P0** | Runbook_DPI_Rate_Limits.md | ✅ **FROZEN v1.2** | Shantanu Chaudhary | 2026-09-17 | 🔴 YES |
| **P1** | Security_Threat_Model.md | ❌ Not Started (moved from late-P0 on 2026-09-17; scope in NFR v2.2 §9) | Claude Code | Before any internet-facing deployment (Roadmap Phase 4) | 🟠 High |
| **P1** | PRD_Module_Secure_Vault.md / PRD_Module_Finance.md / PRD_Module_Health.md | 📝 **DRAFT v0.1** (2026-09-17) — founder review pending | Shantanu Chaudhary (with Claude Code) | Roadmap Phase 1 | 🟠 High |
| **P1** | Roadmap.md / Execution_Plan.md / GTM_Plan.md | 📝 **DRAFT v0.2** (2026-09-17) — sequence-only, no dates; module PRD scopes pending founder review | Shantanu Chaudhary (with Claude Code) | — | 🟠 High |
| **P1** | Workstation_Setup.md (docs/reference) | ✅ Guide written 2026-09-17 (WP-01) | Shantanu Chaudhary (with Claude Code) | — | 🟠 High |
| **P2** | Local_Agent_Setup.md (docs/reference) | ✅ Reference; local models now sit under Gemini's lane | Shantanu Chaudhary | — | ⚪ |
| **P1** | UX_Error_Message_Library.md | ❌ Not Started | TBD | Week 3 | 🟠 High |
| **P1** | Tech_Spec_Supervisor_Concurrency_Control.md | ❌ Not Started | TBD | Week 3 | 🟠 High |
| **P1** | Tech_Spec_Simulator_Architecture.md | ❌ Not Started | TBD | Week 3 | 🟠 High |
| **P1** | Tech_Spec_Audit_Log_Implementation.md | ❌ Not Started | TBD | Week 4 | 🟠 High |
| **P2** | Tech_Spec_Scalability_Architecture.md | ❌ Not Started | TBD | Week 5 | 🟡 Medium |
| **P2** | Disaster_Recovery_Plan.md | ❌ Not Started | TBD | Week 5 | 🟡 Medium |
| **P2** | Tech_Spec_Observability_Stack.md | ❌ Not Started | TBD | Week 5 | 🟡 Medium |
| **P2** | Test_Automation_Strategy.md | ❌ Not Started | TBD | Week 4 | 🟡 Medium |
| **P2** | CI_CD_Pipeline_Spec.md | ❌ Not Started | TBD | Week 5 | 🟡 Medium |
| **P3** | Development_Environment_Setup.md | ❌ Not Started | TBD | Week 4 | 🔵 Low |
| **P3** | Testing_Strategy.md | ❌ Not Started | TBD | Week 4 | 🔵 Low |
| **P3** | API_Documentation.md | ❌ Not Started | TBD | Week 6 | 🔵 Low |
| **P4** | User_Onboarding_Flow.md | ❌ Not Started | TBD | Post-MVP | ⚪ Nice to Have |
| **P4** | Marketing_GTM_Strategy.md | ➡️ Superseded by GTM_Plan.md (portfolio mode); commercial GTM remains Master Context §14 | — | — | ⚪ |

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

Open follow-ups: (a) Codex review round 2 of DM v1.3 and MR v1.1, then re-freeze; (b) item 15's per-user case, decided in the Finance module PRD review.

---

## 🚨 Critical Gaps & Risks

### 🔴 **BLOCKING ISSUES** (Must resolve before development)

#### ~~1. Zombie Transaction Recovery (Financial Safety)~~ ✅ RESOLVED (Tech_Spec_Financial_Transaction_Safety v1.1)
**Resolved by:** Tech_Spec_Financial_Transaction_Safety_v1.1.docx (Feb 2026). Full Healer algorithm (5-min cron, AUDIT_LOG_WRITE P1 priority, BBPS polling, zombie decision tree by elapsed time). Two-phase commit protocol. FIN_001–FIN_015 error taxonomy. Refund policy. Concurrent payment prevention. Manual escalation protocol. v1.1 hardening: Healer distributed lock (§6.1.1), per-run processing cap (§6.1.2), system-level circuit breaker (§6.1.3), NOT_FOUND idempotency key hard rule (§6.4), manual override hash chain SELECT FOR UPDATE (§11.3). Two independent reviewer rounds. Reviewer 2 verdict: **LAUNCH READINESS VERIFIED**.

#### ~~2. Family Graph Schema Undefined~~ ✅ RESOLVED (Data_Model_Schema v1.2.1)
**Resolved by:** Data_Model_Schema_v1.2.1.docx (Feb 2026). Full schema with 10 tables, 12 traversal queries, cardinality enforcement, seed data. Two independent reviewer approvals. Architecture frozen. v1.2.1 documentation patch: SYSTEM_ACTOR family isolation clarified in Q1, fsm_exit_state linked to NFR v2.1 telemetry enum.

#### 3. ~~Consent Token Lifecycle Unspecified~~ ✅ FROZEN v1.1 (Tech_Spec_Consent_Manager_v1.1)
**Resolved by:** Tech_Spec_Consent_Manager_v1.1.docx (Feb 2026). Two independent reviewer rounds. Reviewer 1: 9.2/10, 5 issues found (2 critical, 3 important), all fixed in v1.1. Reviewer 2: A+, no defects. v1.1 hardening: (1) PostgreSQL trigger enforce_dpi_handle prevents DPI consent_records with NULL consent_handle_id — closes silent CONSENT_REVERIFY Check 2 bypass; (2) §2.2 deletion sequence now aborts non-terminal supervisor_sessions in single T+0 transaction — prevents orphaned EXECUTION sessions; (3) §7.3 renewal inherits fetch_count_today from old handle if revoked within 1 hour — prevents RBI rate-limit evasion; (4) §4.6 consent_ui_disclosures table — consent_ui_version now points to auditable canonical record with is_material_change flag and re-consent trigger; (5) §9.3 webhook Step 4 wrapped in BEGIN/COMMIT — prevents partial state on audit_log failure after consent_handles UPDATE.

#### ~~4. DPI Rate Limit Budget Missing~~ ✅ RESOLVED (Runbook_DPI_Rate_Limits_v1.1 — FROZEN)
**Resolved by:** Runbook_DPI_Rate_Limits_v1.1.docx (Feb 2026). Two independent reviews. R1: 8.8/10, 4 required fixes. R2: A+, 2 refinements. Eight hardening fixes applied: AA hourly TTL corrected to seconds_until_next_hour_ist(), BBPS Redis-failure changed to fail-closed (financial execution gate), environment prefix on all Redis keys (prevents staging→prod state corruption), AA coalescing timeout now emits log.warning + dpi.aa.coalescing_timeout metric, Bhashini low-confidence ASR writes VOICE_ASR_LOW_CONFIDENCE audit event, ONDC seller blacklist progressive expiry (1h first offence → 24h on 3rd in 24h), jitter on exponential backoff, per-family Bhashini auto soft-throttle at 100 calls/day (10% of org budget). Architecture frozen.

#### 5. Module Communication Protocol — 🔄 v1.1 AFTER REVIEW ROUND 1; ROUND 2 PENDING (Tech_Spec_Module_Registry)
**Issue:** PRD mentions "sandboxing" but no spec for inter-module communication
**Risk:** Cannot implement module isolation or data bridging
**Impact:** Blocks Phase 2 (module expansion)
**Drafted by:** `docs/specs/Tech_Spec_Module_Registry.md` v1.0 — modular monolith with a transport-agnostic JSON envelope; manifest JSON Schema validated fail-closed at boot; Core/Service tiers with a deny-by-default call graph; three-layer isolation (import-linter contracts, schema-per-module DB roles, dispatch-time checks); static boot registration with manifest hash drift detection; `MOD_*` error taxonomy; worked PAY_BILL example.
**Action Required:**
- [x] Define module manifest JSON schema — MR §4
- [x] Specify communication protocol — in-process JSON envelope (MR §2, §6); REST/gRPC deferred to Phase 2 extraction
- [x] Choose isolation mechanism — code + DB-role + runtime layers, no containers in Phase 1 (MR §7)
- [x] Define module data access control rules — schema-per-module, whitelisted kernel views (MR §7.2)
- [x] Specify module registration flow — MR §8
- [x] Review round 1 (Claude Code, 2026-09-17): seven fixes applied → v1.1, log in MR §13
- [ ] Review round 2 (Codex), apply fixes, freeze
- [x] Back-annotate Master Context §3.3–3.4 and NFR §3 (done 2026-09-17: MC v2.1, NFR v2.2)
- [x] OI-2 closed by Data Model v1.3 §3.16–3.17; OI-1, OI-3, OI-4, OI-5 remain open in MR §12
- [x] Inconsistency Register item 3 settled (Data Model v1.3 uses the PRD/MR role names)
**Owner:** Shantanu Chaudhary
**Deadline:** Before the Phase 1 Build Gate opens

---

### 🟠 **HIGH PRIORITY ISSUES** (Needed for robust implementation)

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

#### 7. Concurrency Control Missing
**Issue:** No mechanism to prevent two admins from conflicting actions  
**Risk:** Race conditions, double-spending, data corruption  
**Impact:** Financial errors, family conflicts  
**Action Required:**
- [ ] Implement resource-level locking (Redis distributed locks with TTL)
- [ ] Define conflict resolution for concurrent intents (who wins? admin priority? timestamp?)
- [ ] Choose optimistic vs pessimistic locking per scenario (optimistic for reads, pessimistic for payments)
- [ ] Add deadlock prevention (lock ordering, automatic TTL release after 30s)
**Owner:** TBD  
**Deadline:** Week 3 (Tech_Spec_Supervisor_Concurrency_Control.md)

#### 8. Audit Log Implementation Details Missing
**Issue:** Concept defined, but hashing chain algorithm not specified  
**Risk:** Tampering possible, legal disputes  
**Impact:** Trust erosion, regulatory issues  
**Action Required:**
- [ ] Specify hashing chain algorithm (SHA-256 of: timestamp + user_id + action + previous_hash)
- [ ] Define atomicity guarantee (2-phase commit: payment succeeds THEN audit log writes THEN confirm to user)
- [ ] Implement immutability verification (daily cron job: verify hash chain integrity, alert on tampering)
- [ ] Clarify what gets logged vs what doesn't (log: payments, role changes, consent grants; don't log: PII like phone numbers)
**Owner:** TBD  
**Deadline:** Week 4 (Tech_Spec_Audit_Log_Implementation.md)

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

---

### 🟡 **MEDIUM PRIORITY** (Important for scale)

#### 9. No Scalability Architecture
**Issue:** Docs assume single-server deployment  
**Risk:** Cannot handle 10K+ families  
**Impact:** Growth ceiling, performance degradation  
**Action Required:**
- [ ] Plan horizontal scaling (stateless API servers behind load balancer)
- [ ] Design database sharding (shard by family_id, hash-based distribution)
- [ ] Architect message queue (RabbitMQ/Kafka for async task processing)
- [ ] Define caching strategy (Redis for session state, CDN for static assets)
**Owner:** TBD  
**Deadline:** Week 5 (Tech_Spec_Scalability_Architecture.md)

#### 10. No Disaster Recovery Plan
**Issue:** 99.9% uptime SLA defined, but no DR procedures  
**Risk:** Prolonged downtime on failure  
**Impact:** User trust loss, revenue impact  
**Action Required:**
- [ ] Define RTO (Recovery Time Objective: 4 hours) and RPO (Recovery Point Objective: 1 hour)
- [ ] Plan backup strategy (daily full database backup + continuous WAL archiving)
- [ ] Document failover procedures (primary region fails → auto-failover to secondary region within 15 mins)
- [ ] Schedule quarterly DR drills (simulate failure, test recovery, measure RTO/RPO)
**Owner:** TBD  
**Deadline:** Week 5 (Disaster_Recovery_Plan.md)

---

### 🔵 **LOWER PRIORITY** (Development workflow)

#### 11. Test Automation Strategy Missing
**Issue:** No comprehensive testing approach defined (see dedicated section below)  
**Risk:** Bugs in production, slow release cycles  
**Impact:** Quality issues, technical debt  
**Action Required:** See "Test Automation Strategy" section below  
**Owner:** TBD  
**Deadline:** Week 4 (Test_Automation_Strategy.md)

---

## 🧪 Test Automation Strategy

### Overview
**Philosophy:** Automated testing is non-negotiable for financial products. Manual testing cannot catch all edge cases, especially in multi-agent systems with DPI integrations.

### Testing Pyramid

```
           /\
          /  \    10% - E2E Tests (Critical User Flows)
         /____\   
        /      \  30% - Integration Tests (API + DB)
       /________\ 
      /          \ 60% - Unit Tests (Core Logic)
     /____________\
```

### Test Categories & Ownership

#### 1. **Unit Tests** (60% of test suite)
**What:** Test individual functions, classes, modules in isolation  
**Tools:** Jest (JavaScript/TypeScript), pytest (Python)  
**Coverage Target:** 80% for core business logic  
**Examples:**
- Supervisor state transitions (IDLE → INTENT_ANALYSIS → REASONING)
- TTL cache expiry logic
- RBAC permission checks (can child access vault?)
- Idempotency key generation and validation
- Hashing chain algorithm for audit log

**Responsibility:** Every engineer writes unit tests for their code  
**Run Frequency:** On every commit (pre-commit hook)  

---

#### 2. **Integration Tests** (30% of test suite)
**What:** Test interaction between components (API ↔ Database, Supervisor ↔ Worker Agents)  
**Tools:** Supertest (API testing), Testcontainers (DB in Docker)  
**Coverage Target:** All critical API endpoints + database queries  
**Examples:**
- POST /api/v1/finance/pay-bill returns 200 and creates audit log entry
- Consent expiry watchdog correctly identifies expiring consents
- Module registration adds entry to routing table
- Proxy conflict resolution follows admin-set rules
- Redis state persistence and recovery

**Responsibility:** QA engineer + backend engineers  
**Run Frequency:** On every PR (CI pipeline)  

---

#### 3. **End-to-End Tests** (10% of test suite)
**What:** Test complete user flows across entire system (UI → API → DPI → Response)  
**Tools:** Playwright/Cypress (web), Appium (mobile)  
**Coverage Target:** Top 5 critical user journeys  
**Examples:**
- Complete bill payment flow (user types "Pay electricity bill" → biometric approval → BBPS call → success message)
- Health record fetch (user asks for lab reports → ABHA consent grant → data retrieval → display)
- Family member onboarding (admin adds child → sends invite → child accepts → role assigned)
- Consent expiry and renewal (consent expires → user gets notification → one-click renewal → success)
- SOS emergency mode (trigger SOS → halt new tasks → prioritize emergency actions)

**Responsibility:** QA engineer (dedicated role)  
**Run Frequency:** Nightly builds + before production deployment  

---

### Critical Test Scenarios (Must Have)

#### **Financial Safety Tests** 🔴
- [ ] **Idempotency:** Same transaction ID posted twice returns cached result, no double-charge
- [ ] **Zombie Recovery:** Transaction stuck in PENDING for >5 mins triggers reconciliation
- [ ] **Audit Log Atomicity:** If payment succeeds but audit log fails, system enters FAILED state
- [ ] **Rollback:** If BBPS returns error after amount debited, refund is initiated
- [ ] **Concurrency:** Two admins cannot pay same bill simultaneously (409 Conflict)

#### **Consent Lifecycle Tests** 🔴
- [ ] **Grant Flow:** User grants AA consent → token stored → expiry tracked
- [ ] **Expiry Watchdog:** Consent expiring in <7 days triggers notification
- [ ] **Reverification:** CONSENT_REVERIFY state catches revoked consent before execution
- [ ] **Revocation Propagation:** Revoking consent purges cached data and updates status

#### **RBAC Enforcement Tests** 🔴
- [ ] **Child Vault Access:** Child role attempting to access /api/v1/vault returns 403
- [ ] **Staff Finance Block:** Staff role cannot view bank balance
- [ ] **Proxy Authorization:** Only assigned proxies can act on managed profile
- [ ] **Surface Context:** Kitchen Tablet (public device) blocks finance queries

#### **DPI Integration Tests** 🟠
- [ ] **AA Rate Limit:** 4th refresh within 1 hour returns "Please wait" message
- [ ] **BBPS Timeout:** 504 error queues transaction for retry
- [ ] **ABHA Downtime:** Circuit breaker trips after 3 failures, shows maintenance message
- [ ] **ONDC Malformed Response:** Invalid JSON is caught and logged, doesn't crash system

#### **Simulator Validation Tests** 🟠
- [ ] **Contract Compliance:** Mock AA response matches real API schema
- [ ] **State Machine:** BBPS simulator correctly transitions PENDING → SUCCESS
- [ ] **Chaos Mode:** Random failures inject 503 errors as configured

---

### CI/CD Pipeline Integration

#### **Pre-Commit Hooks** (Local Developer Machine)
- Run unit tests for changed files
- Run linters (ESLint, Pylint)
- Check code formatting (Prettier, Black)
- **Time Budget:** <30 seconds

#### **Pull Request Pipeline** (GitHub Actions / GitLab CI)
1. Run all unit tests (must pass 100%)
2. Run integration tests (must pass 100%)
3. Run code coverage check (must be ≥80%)
4. Run security scan (npm audit, Snyk)
5. Generate test report (JUnit XML)
**Time Budget:** <5 minutes

#### **Nightly Build Pipeline**
1. Run full E2E test suite
2. Run performance tests (load testing)
3. Run security penetration tests
4. Generate coverage report
5. Alert team if any test fails
**Time Budget:** <30 minutes

#### **Pre-Deployment Pipeline** (Staging → Production)
1. Run smoke tests on staging environment
2. Run critical E2E flows (top 5 journeys)
3. Verify database migrations
4. Check DPI simulator availability (for staging)
5. Manual approval gate (product lead signs off)
**Time Budget:** <15 minutes

---

### Test Data Management

#### **Synthetic Test Data** (Preferred for Development)
- Use **Faker.js** to generate realistic but fake data
- Example: Fake family with 2 adults, 2 children, 1 elder
- Benefits: No PII concerns, fast generation, consistent

#### **Anonymized Production Data** (For Staging)
- Scrub all PII (names, phone numbers, Aadhaar, UPI IDs)
- Replace with synthetic equivalents
- Maintain referential integrity (same family_id across tables)
- Benefits: Realistic data distribution, catches edge cases

#### **Test Fixtures** (For Specific Scenarios)
- Pre-defined JSON files for edge cases
- Example: `family_with_10_children.json`, `user_with_expired_consent.json`
- Stored in `/tests/fixtures` directory

---

### Performance Testing

#### **Load Testing** (Simulate Normal Traffic)
- Tool: k6 or Apache JMeter
- Scenario: 1000 concurrent users, each making 5 API calls/minute
- Measure: API latency (p95 <2s), error rate (<0.1%)
- Run: Weekly

#### **Stress Testing** (Find Breaking Point)
- Scenario: Gradually increase load until system fails
- Find: Maximum concurrent users before degradation
- Document: Results in scalability architecture doc
- Run: Monthly

#### **Chaos Testing** (Inject Random Failures)
- Tool: Chaos Monkey, Gremlin
- Scenario: Randomly kill services, inject network latency, fill disk
- Verify: System recovers gracefully (circuit breakers work)
- Run: Quarterly (controlled chaos in staging)

---

### Test Automation Tooling Stack

| Category | Tool | Purpose |
|----------|------|---------|
| Unit Testing | Jest / pytest | Test individual functions |
| Integration Testing | Supertest / Testcontainers | API + DB testing |
| E2E Testing | Playwright / Cypress | Full user flows (web) |
| Mobile Testing | Appium | Android/iOS app testing |
| API Mocking | WireMock / MSW | Simulate DPI responses |
| Load Testing | k6 | Performance under load |
| Chaos Testing | Chaos Monkey | Resilience testing |
| Test Reporting | Allure / ReportPortal | Visual test reports |
| Coverage | Istanbul / Coverage.py | Code coverage metrics |
| CI/CD | GitHub Actions / GitLab CI | Automated pipelines |

---

### Test Automation Metrics

#### **Key Metrics to Track**
- **Test Coverage:** % of code covered by tests (target: 80%)
- **Test Pass Rate:** % of tests passing (target: 100% in main branch)
- **Flaky Test Rate:** % of tests that fail intermittently (target: <1%)
- **Test Execution Time:** Time to run full suite (target: <30 mins)
- **Defect Escape Rate:** Bugs found in production vs caught in testing (target: <5% escape)

#### **Weekly Dashboard** (To Be Built)
- Total tests: 1,234
- Unit tests: 740 (60%) - ✅ Passing
- Integration tests: 370 (30%) - ⚠️ 2 failing
- E2E tests: 124 (10%) - ✅ Passing
- Coverage: 82% - ✅ Above target
- Avg execution time: 8 minutes - ✅ Under budget

---

### Ownership & Responsibilities

#### **Backend Engineers**
- Write unit tests for all new code (mandatory)
- Write integration tests for new APIs
- Maintain test fixtures
- Fix failing tests before merge

#### **QA Engineer** (Dedicated Role - To Be Hired)
- Design E2E test scenarios
- Build test automation framework
- Maintain Playwright/Appium scripts
- Run performance tests
- Generate weekly test reports
- Coordinate with backend team on integration tests

#### **DevOps/Platform Engineer** (Future Role)
- Set up CI/CD pipelines
- Configure test environments
- Monitor test execution times
- Optimize build/test performance

---

### Test Automation Roadmap

#### **Week 4: Foundation**
- [ ] Choose testing framework (Jest + Playwright recommended)
- [ ] Set up test directory structure (`/tests/unit`, `/tests/integration`, `/tests/e2e`)
- [ ] Configure CI/CD pipeline for automated test runs
- [ ] Write first 10 unit tests (state machine transitions)

#### **Week 5-6: Core Coverage**
- [ ] Unit tests for all supervisor logic (80% coverage)
- [ ] Integration tests for top 5 API endpoints
- [ ] First E2E test (bill payment flow)

#### **Week 7-8: Expand & Refine**
- [ ] Add financial safety tests (idempotency, zombie recovery)
- [ ] Add RBAC enforcement tests
- [ ] Build first load test scenario (100 concurrent users)

#### **Week 9-10: Pre-Launch**
- [ ] Complete E2E test suite (top 5 user journeys)
- [ ] Run chaos tests in staging
- [ ] Achieve 80%+ code coverage
- [ ] Generate test documentation

---

## 🛠️ Development Environment Needs

### Local Setup Requirements
- [ ] Docker Compose file (Postgres, Redis, WireMock)
- [ ] Environment variables template (.env.example)
- [ ] Seed data scripts (sample families, test data)
- [ ] Git hooks for linting and tests
- [ ] README with setup instructions

### CI/CD Pipeline
- [ ] GitHub Actions / GitLab CI config
- [ ] Automated testing on PR
- [ ] Code coverage reporting
- [ ] Security scanning (npm audit, Snyk)
- [ ] Deployment to staging on merge to `develop`

### Observability Stack
- [ ] Logging: Loki or ELK
- [ ] Metrics: Prometheus + Grafana
- [ ] Tracing: Jaeger
- [ ] Alerting: PagerDuty or Opsgenie

---

## 🔐 Security & Compliance Checklist

### Pre-Launch Security Audit
- [ ] OWASP Top 10 mitigation verified
- [ ] Penetration testing by external firm
- [ ] Cryptographic key management reviewed
- [ ] Biometric data handling audited
- [ ] AA/ABHA consent flows legally reviewed

### Compliance Requirements
- [ ] DPDP Act compliance (data localization, consent, deletion)
- [ ] RBI guidelines for Account Aggregator usage
- [ ] NPCI guidelines for BBPS integration
- [ ] ABDM compliance for health data handling
- [ ] IT Act (digital signature validity)

### Ongoing Security
- [ ] Quarterly penetration tests
- [ ] Security patch management process
- [ ] Incident response runbook
- [ ] Bug bounty program (post-launch)

---

## 📌 Near-Term Parking Lot (Ideas for Next 3-6 Months)

**Note:** Long-term vision items (12-24+ months) are in `docs/strategy/Vision_Parking_Lot.md` (v2.0)

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

### Strategic Risk Register

- **⚠ "Cathedral before church" risk** *(Raised by Reviewer 1, Feb 2026. Confirmed by Reviewer 1 post-v1.1)*: Architecture maturity is 8.7/10. Vertical slice readiness is 0/10. These are correctly decoupled — but the risk is that doc phase extends indefinitely. **Hard gate enforced:** No P2 feature docs begin until the Phase 1 Build Gate is passed (see below). Architecture is a means to ship, not an end.

### 🏗️ Phase 1 Build Gate (Must Pass Before Any P2 Docs)

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

### Technology Decisions (Weeks 3-5)
- **Testing Framework Choice:** Jest vs Vitest for unit tests? (Week 4 decision)
- **Hosting Provider:** AWS vs Azure vs GCP for production? (Week 5 decision)
  - Consider: India data centers, managed services (RDS, Redis), compliance certifications
- **Message Queue:** RabbitMQ vs Kafka for async task processing? (Week 5 decision)
  - RabbitMQ: Simpler, lower overhead
  - Kafka: Better for high-throughput, event sourcing

### Team/Hiring Decisions (Months 2-3)
- **QA Engineer:** Hire full-time vs outsource testing? (Month 2 decision)
  - Lean: Outsource initial testing, hire after 1000 users
  - Quality: Hire dedicated QA in Month 2 for robust testing culture
- **DevOps:** DIY vs hire vs contractor? (Month 3 decision)
  - Bootstrap: Founder does DevOps with managed services (AWS RDS, Heroku)
  - Scale: Hire dedicated DevOps at 5000+ users

### Feature Prioritization (Months 3-4)
- **Which module after Core?** Health vs Finance first in Phase 2? (Month 3 decision)
  - Health: Higher differentiation, elder care is unique value prop
  - Finance: Faster monetization, easier to demonstrate ROI
- **Mobile app timeline:** When to build native iOS/Android vs progressive web app? (Month 4 decision)
  - PWA first for faster iteration, native apps when biometric/push notifications are critical

### Operational Decisions (Months 4-6)
- **Support model:** Chatbot vs human support for beta users? (Month 4 decision)
- **Pricing strategy:** Launch with freemium vs paid-only? (Month 5 decision)
- **Customer success:** Self-service onboarding vs white-glove for first 100 families? (Month 5 decision)

---

## 🗓️ Milestone Tracker

> ⚠️ The week and month numbering below was set on 2026-02-21 and is historical. The current plan is `docs/strategy/Roadmap.md` (draft v0.2, sequence-only: no dates by decision); the work breakdown is `docs/Execution_Plan.md`. This section is kept for the record.

### Month 1: Documentation & Architecture
- **Week 1:** Complete 5 Priority 0 documents (Data Model, Financial Safety, Consent Manager, Module Registry, DPI Rate Limits)
- **Week 2:** Build simulator suite (AA, BBPS, ABHA, ONDC mocks)
- **Week 3:** Complete Priority 1 documents (Error Messages, Concurrency Control, Simulator Architecture, Security Threat Model, Audit Log)
- **Week 4:** Set up development environment + test automation foundation

### Month 2: Core Development
- **Week 5-6:** Family Graph, RBAC, Supervisor FSM implementation
- **Week 7-8:** Consent Manager, Audit Log, Financial Agent (with simulators)

### Month 3: DPI Integration
- **Week 9-10:** Real AA integration (post-FIU approval)
- **Week 11-12:** Real BBPS integration, E2E testing

### Month 4: Beta Launch
- **Week 13:** Internal testing (team + family)
- **Week 14:** Beta launch (100 families, waitlist)
- **Week 15-16:** Bug fixes, stability improvements

---

## 🚀 Next Actions (Immediate)

*(Rewritten 2026-09-17. The detailed sequence is `docs/Execution_Plan.md`, Phase 0 and Phase 1.)*

### Founder
- [ ] Workstation setup, `docs/reference/Workstation_Setup.md` (WP-01): WSL 2, Docker Desktop; open the repository in the Codex desktop app and in Antigravity and give each its first prompt. Optional: an Ollama model for Gemini's sub-agent experiments.
- [ ] Branch protection on `main` (WP-03): pull request and CI checks required, no force pushes, administrators not included. A repository setting, so it is the founder's to switch on (once CI exists, WP-06).

### Claude Code
- [ ] After Codex's round-2 findings: apply accepted fixes, freeze Data Model v1.3 and the Module Registry (WP-11).
- [ ] Draft `Tech_Spec_Simulator_Architecture.md` (WP-12) — the Build Gate's WireMock scenarios need it before Codex starts.

### Codex — brief in `coordination/inbox/codex/`
- [ ] Review round 2: `docs/specs/Tech_Spec_Module_Registry.md` v1.1, `docs/specs/Data_Model_Schema.md` v1.3 and the one addition in `docs/specs/Tech_Spec_Consent_Manager.md` v1.3 §2.6 (WP-09, WP-10). Findings only; Claude Code applies fixes; freeze.
- [ ] Repo scaffolding and CI (WP-05, WP-06).

### Gemini in Antigravity — brief in `coordination/inbox/gemini/`
- [ ] Onboarding (WP-02): state role and limits, first STATUS lines, one docstring-only PR on `tools/docx2md.py` reviewed by Codex.
- [ ] Later: WireMock stub JSON for AA and BBPS from Runbook §9 and the simulator spec; Alembic V001 draft from Data Model v1.3 (reviewed by Codex); maintenance passes (WP-08). Local models may be used as sub-agents; Gemini stays accountable.

## 📊 Success Metrics Dashboard (To Be Built)

### Product Metrics
- Monthly Active Families (MAF)
- Tasks completed autonomously (% requiring no human intervention)
- DPI success rate (AA, BBPS, ABHA uptime from our side)
- Average time saved per family (hours/month)
- Family NPS (Net Promoter Score)

### Technical Metrics
- API uptime (target: 99.9%)
- P95 latency (target: <2s)
- Error rate (target: <0.1%)
- Test coverage (target: >80%)
- Deployment frequency (target: 2x/week)

### Financial Metrics
- Customer Acquisition Cost (CAC)
- Lifetime Value (LTV)
- LTV:CAC ratio (target: >3:1)
- Monthly Recurring Revenue (MRR)
- Churn rate (target: <5%/month)

---

## 🔄 How to Maintain This Document

### Update Frequency
- **Weekly:** Review and update document status, next actions, mark completed tasks
- **After major decisions:** Add new items to near-term parking lot or priority sections
- **Before milestones:** Update roadmap, adjust timelines

### Update Process
1. Edit this Markdown file in place (`docs/PROJECT_TRACKER.md`)
2. Update "Last Updated" at the top and add a dated row to "Consolidation and Change Log"
3. Commit to version control (put the repository under git if it is not yet)
4. Announce updates in team chat (when team exists)

### Ownership
- **Primary Maintainer:** Shantanu Chaudhary (Lead Product Architect)
- **Contributors:** Engineering team (once hired)
- **Reviewers:** Product lead, CTO (when roles filled)

---

**END OF DOCUMENT**  
*This is a living document. It will evolve as the project progresses.*

**Long-term vision (12-24+ months) is maintained separately in `docs/strategy/Vision_Parking_Lot.md`**
