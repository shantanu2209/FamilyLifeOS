# AGENTS.md — FamilyLifeOS

Instructions for every AI coding agent (the roster is Claude Code, Codex and Gemini in Antigravity; §6 says who does what) and for humans working in this repository. `CLAUDE.md` and `GEMINI.md` only point here. Keep this file as the single source of agent instructions; do not fork per tool.

---

## 1. What this repository is

**FamilyLifeOS** is an India-first, agentic "family operating system": a digital Chief of Staff for a household. It governs Health, Finance, Logistics, Home Operations, Communication, Elder Care, Documents and Learning through specialised worker agents coordinated by a **Supervisor** state machine. It is built natively on India's Digital Public Infrastructure (DPI): Account Aggregator (AA), BBPS, ABHA/ABDM, DigiLocker, ONDC and Bhashini. The atomic unit is the **family** (not the individual), with hierarchical role-based access control over the family graph.

**Current state (2026-09-17): documentation complete, pre-development; tooling install and agent onboarding under way.** There is no application code, no test suite and no CI yet; the repository was put under git on 2026-09-16. The repository holds the strategy blueprint, the Core PRD and three module PRDs, the technical specifications (Financial Transaction Safety, Consent Manager and the DPI runbook frozen; Data Model v1.3 and Module Registry v1.1 awaiting Codex review round 2; Supervisor State Machine and NFR canonical), a roadmap, an execution plan, a GTM plan, a living project tracker, the coordination protocol and reference material. The next milestone is the **Phase 1 Build Gate** (§7).

The project is run by its founder and lead product architect, **Shantanu Chaudhary**. Documents written before 2026-09-17 carried the pen name "Alfred"; that was the same person, and the name has been replaced throughout (the claude.ai project and the local archive still show it). Specs were hardened through two independent review rounds each and then **frozen**. Treat frozen specs as contracts, not suggestions.

**Project mode (decided 2026-09-17): portfolio first.** The goal is a working kernel and the "Priya pays BESCOM bill" vertical slice against DPI simulators, built to the quality the specs demand. No regulatory licence applications are in progress, so no real-money DPI integration is planned; commercial expansion may follow if the result warrants it. The venture-oriented material in Master Context (phasing budgets, GTM, unit economics) is context, not the current plan. See the Decision Log in `docs/PROJECT_TRACKER.md`.

**The repository is public on GitHub.** `archive/` is local-only and gitignored. Never commit secrets, real PII, consent handles or push tokens; test data is synthetic.

---

## 2. Read this first, in this order

| # | File | Why |
|---|---|---|
| 1 | `AGENTS.md` (this file) | Rules, invariants, status, known gaps |
| 2 | `docs/strategy/Master_Context.md` | Canonical product, technical and strategy blueprint (v2.1) |
| 3 | `docs/PROJECT_TRACKER.md` | What is done, what is next, the build gate, the inconsistency register |
| 4 | `docs/strategy/PRD_FamilyLifeOS_Core.md` and `docs/specs/Tech_Spec_Supervisor_State_Machine.md` | The product requirements and the Supervisor FSM the frozen specs build on |
| 5 | `docs/specs/Data_Model_Schema.md` | Every table, column, index and query. Every other spec references it by name |
| 6 | The spec for the area you are touching | See the map in §3 |
| 7 | `coordination/README.md` | How work is assigned, branched, reviewed and merged across the agents |
| 8 | `coordination/inbox/<you>/` and `coordination/STATUS.md` | Messages addressed to you, and what the other agents are doing right now. Read both at the start of every session |

Read whole documents. The specs put hard rules inside callout boxes and code comments, not only in headings.

---

## 3. Document map and status

Everything current lives under `docs/`. Everything historical lives under `archive/` and must not be edited or treated as current.

| Path | What it is | Version / status |
|---|---|---|
| `docs/strategy/Master_Context.md` | Canonical blueprint: identity, family graph, architecture, DPI strategy and risks, modules, data model summary, security, phasing, metrics, competition, revenue, GTM | **v2.1 — canonical**; inline notes mark where later specs narrowed it (§3.3–3.4, §6, §8) |
| `docs/strategy/Vision_Journey.md` | Strategic white paper (Jan 2026): how the product went from a portfolio app to a family OS | Reference / history |
| `docs/strategy/Master_PRD.md` | "Holistic LifeOS" master PRD v2.1 (Jan 2026): module-level requirements and DPI touchpoints | Reference. **Not** the scenario-driven Core PRD below |
| `docs/strategy/PRD_FamilyLifeOS_Core.md` | Core PRD: one-pager, 7-role RBAC matrix, 14 user scenarios, functional requirements, specification map (§4.8), shared services, conflict-resolution matrix, KPIs | **v2.2 — canonical** |
| `docs/strategy/PRD_Module_Secure_Vault.md`, `PRD_Module_Finance.md`, `PRD_Module_Health.md` | Module PRDs for the three Phase 1 modules: scenarios, agentic loop, manifest excerpt, owned schema, DPI touchpoints via simulators, conflict matrix, error codes | **DRAFT v0.1** (2026-09-17), founder review pending |
| `docs/strategy/Roadmap.md` | Portfolio-first roadmap: phases with entry and exit gates, ordered steps, milestones M0–M5, what changes if commercial. No dates and no capacity assumptions, by decision | **DRAFT v0.2** |
| `docs/Execution_Plan.md` | Work packages WP-xx in dependency order with owner agent, reviewer, verification and issue seeds | **DRAFT v0.2** |
| `docs/strategy/GTM_Plan.md` | Portfolio-mode go-to-market: audience, positioning, artefacts, demo script; commercial GTM stays in Master Context §14 | **DRAFT v0.2** |
| `docs/strategy/Vision_Parking_Lot.md` | Deferred capabilities with trigger conditions: blockchain audit log, live spatial reasoning, sub-800 ms latency, hardware presence, voting, future modules | v2.0 reference (recovered 2026-09-16) |
| `docs/specs/Data_Model_Schema.md` | Kernel schema `core`: 16 tables, 4 views, audit write functions, 12 operational queries, 41-code audit taxonomy, lifecycle jobs, seed data, v1.3 change summary | **v1.3 — revision in review** (Codex round 2), then re-freeze. v1.2.1 was frozen |
| `docs/specs/Tech_Spec_Financial_Transaction_Safety.md` | Payment gates, two-phase commit, idempotency, the Healer, zombie recovery, refunds, FIN error codes | **FROZEN v1.2** (v1.1 protocol; names aligned with Data Model v1.3) |
| `docs/specs/Tech_Spec_Consent_Manager.md` | DPDP-native consent framework, purpose registry, `consent_records`, CONSENT_REVERIFY, DPI adapters, expiry watchdog, revocation, webhook security | **v1.3 — frozen v1.2 text plus one addition** (§2.6 proxy consent for managed profiles) awaiting Codex round 2 |
| `docs/specs/Tech_Spec_Module_Registry.md` | Module manifest schema, Supervisor→module dispatch envelope, tiers, isolation model, registration, error taxonomy, review log | **v1.1 — review round 1 applied**; round 2 (Codex) pending; freezes on approval. Last P0 doc before the build gate |
| `docs/specs/Tech_Spec_Supervisor_State_Machine.md` | Supervisor FSM (state diagram, state definitions, persistence, Healer placeholder), automation tiers, TTL policy, idempotency keys | **v2.1 — canonical** (recovered 2026-09-16); implementation depth lives in the frozen P0 specs |
| `docs/specs/NFR_Specs.md` | Latency budgets, encryption, authentication, idempotency and rate-limit mandates, DPI circuit breaker, telemetry, compliance, scalability targets, disaster recovery, degradation order | **v2.2 — canonical** |
| `docs/runbooks/Runbook_DPI_Rate_Limits.md` | Rate limits for all five DPIs, Redis budget tracker, circuit breakers, coalescing, WireMock stubs, on-call runbook | **FROZEN v1.2** (two clarifications) |
| `docs/reference/Workstation_Setup.md` | What to install and sign in to on the founder's PC (WSL 2, Docker Desktop; Codex desktop app and Antigravity pointed at the repository; optional Ollama models) | Guide (WP-01) |
| `docs/reference/Local_Agent_Setup.md` | Local model choice and Ollama tuning for the founder's machine. Local models are sub-agents of Gemini, not a roster member; the Codex CLI harness described there is an optional manual fallback | Reference |
| `coordination/` | Working protocol (README), `STATUS.md` (who is doing what), `inbox/` (agent-to-agent and agent-to-founder messages), handoff template, Now/Next/Later board | Living |
| `docs/reference/DPI_Integration_Primer.md` | Early (Jan 2026) DPI cheat sheet: Beckn/ONDC flow, AA entity chain, ABHA/FHIR flow, Bhashini APIs, conflict object | Reference. Its JSON schemas and security notes are superseded by the Data Model and Master Context |
| `docs/templates/PRD_Template.md` | Deep-dive PRD template for module or feature PRDs | Template |
| `docs/PROJECT_TRACKER.md` | Living scratchpad: status, gaps, test strategy, build gate, parking lot, inconsistency register | Living document |
| `archive/` | Every original file (docx, duplicate md/txt, superseded versions, AI review notes) and the raw claude.ai exports | Historical, read-only, **local-only (gitignored, not on GitHub)** |

### 3.1 Recovered and still-missing documents

The four foundational documents that were absent at consolidation (Core PRD v2.1, Supervisor State Machine v2.1, NFR v2.1, Vision Parking Lot v2.0) were recovered on 2026-09-16 from the claude.ai project "FamilyLife OS", where they exist as knowledge files, and now live under `docs/` (see the map above). Only one referenced document does not exist yet:

- `Security_Threat_Model.md` — not yet written. P1 since the portfolio-mode decision (2026-09-17): required before any internet-facing deployment, demo included. Target path `docs/specs/Security_Threat_Model.md`; scope in NFR v2.2 §9.

The claude.ai project does **not** hold the Consent Manager, Financial Transaction Safety, DPI Rate Limits or Module Registry specs; this repository is the only place they exist.

---

## 4. Non-negotiable invariants

These come from the frozen specs. Code, tests, new docs and refactors must honour them. Section references use DM = Data Model Schema, FTS = Financial Transaction Safety, CM = Consent Manager, RB = DPI Rate Limits runbook, MR = Module Registry, MC = Master Context.

### Family graph and access
1. `family_id` is the partition key on every table. Every query is family-scoped. (DM §1.1)
2. RBAC is deny-by-default and enforced in the application layer at every endpoint and before every dispatch. (DM Q2, MR §7.3)
3. Cardinality per family: admins 1–2, member ≤2, minor ≤10, elder ≤4, staff ≤5, managed ≤10, passive ≤10; exactly one primary proxy and at most one secondary per managed profile. Checks run inside a transaction with `SELECT … FOR UPDATE` on the family row. Role codes are admin, member, minor, elder, staff, managed, passive (DM v1.3 §3.2; PRD §2). (DM §4)
4. The last admin can never be removed or demoted. (DM §4.1)
5. Relationship edges are bidirectional and both edges are written in one transaction. (DM §3.3)
6. A device flagged `is_public_surface` never shows finance, health, vault documents or member PII, whoever is logged in. (DM §3.8, MR §6.2)
7. Soft delete: every query that joins `users` filters `deleted_at IS NULL` unless it is explicitly historical. Hard purge runs nightly at 01:00 IST after 24 h. (DM §4.3, §7.1)

### Consent and privacy
8. No data is collected, accessed or processed without an active `consent_records` row for a registered `purpose_code`. Unknown purpose = blocked operation. (CM §3)
9. The application database never stores raw credentials, tokens, Aadhaar numbers, UPI IDs or account numbers. Only opaque consent handles and UUIDs. Consent travels by reference inside envelopes. (DM §1.1, MC §7, MR §6.1)
10. `CONSENT_REVERIFY` runs immediately before any external execution, always reads live from the database (never a cache), and fails safe when the DPI cannot be reached. (CM §5)
11. Consent is granted only by a human via biometric or PIN. The Supervisor may prompt for consent; it can never grant it. (CM §1.3)
12. Minors need `parental_consent_user_id`; no analytics or behavioural collection for minors. Managed profiles need `proxy_consent_user_id`: the primary proxy grants on their behalf, the secondary only when the primary is unavailable. (CM §2.5, CM v1.3 §2.6)
13. On account deletion: abort non-terminal sessions, revoke DPI consents at T+0, keep the 24 h soft-delete window for first-party data only. (CM §2.2)
14. DPI webhooks are verified (JWS for Sahamati, JWT for ABDM), replay-protected (5-minute window, `txnid`/`jti` cache) and rejected with 503 when the signing keys are unavailable. (CM §9)

### Financial execution
15. Automation Level 3 is forbidden in V1; manifests cap `automation_tier_ceiling` at 2. BBPS bill payments require biometric approval. The Healer reconciles; it never approves or creates a payment. (MR §4.1, FTS §2.2, FTS §6.1)
16. One UUIDv4 idempotency key per session, generated at `INTENT_ANALYSIS`, persisted to `supervisor_sessions` in the Phase 1 COMMIT **before** any external call. Retries and Healer re-submissions reuse the original key. Never generate a new key for the same payment. (FTS §5, §6.4)
17. Two-phase commit: Phase 1 moves the session to `EXECUTION` with the key; then the external call; Phase 2 writes the audit row and the session update in one transaction. The resource lock is a row in `core.resource_lock` (DM v1.3 §3.11), acquired by INSERT at gate G2 and released by UPDATE only after the Phase 2 COMMIT, never deleted. (FTS §4, §9)
18. Five pre-execution gates, in order: RBAC → resource lock → forced AA balance fetch → biometric → CONSENT_REVERIFY. (FTS §2.2)
19. A session in `EXECUTION` for more than 5 minutes is a zombie. The Healer runs every 5 minutes under a Redis distributed lock, processes `AUDIT_LOG_WRITE` tasks first, applies per-run caps and a system-level circuit breaker. Nothing else may move an EXECUTION session out of that state: not the session-expiry cleanup (DM v1.3 §7.4) and not a `MOD_EXECUTION_UNCONFIRMED` response (MR v1.1 §9). (FTS §6–7)
20. Financial errors use the `FIN_001`–`FIN_015` taxonomy. Raw codes are never shown to users. (FTS §10)

### Audit log
21. `audit_log` is append-only; the application DB user has no UPDATE or DELETE on it. (DM §3.6)
22. `current_hash = SHA256(log_id || user_id || action || canonical_details || previous_hash)` where `canonical_details = json.dumps(details, sort_keys=True, separators=(',', ':'))` and a NULL previous_hash serialises as `''`; computed in application code, chained per family, verified daily. Every writer uses the two-call protocol `fn_lock_audit_tail` → hash in code → `fn_append_audit` inside one transaction; modules have no privileges on the table. (DM v1.3 §3.6, §3.18, §7.2)
23. Only standardised action codes (DM §6 plus the CM §4.4 additions). `details` carries UUIDs and amounts only, never PII. System jobs write as `SYSTEM_ACTOR_UUID`. (DM §6)
24. Any writer that competes with the Healer locks the latest audit row with `SELECT … FOR UPDATE` before computing `previous_hash`. (FTS §11.3)

### DPI resilience
25. Rate limits as of Feb 2026: AA 3 fetches/hour per consent handle; BBPS 50 transactions/day per user; ABHA 10 consent grants/day per user; ONDC 100 searches/day (soft); Bhashini 1000 ASR calls/day org-wide with a 100/day per-family soft throttle. Verify against sandbox portals before each release. (RB §1, §7.2)
26. Budget checks use the atomic Lua check-and-increment; TTLs align to the IST hour or midnight; every Redis key is prefixed `{env}:`. (RB §2)
27. If Redis is unavailable, budget checks fail open, except BBPS which fails closed. (RB §2.4)
28. Circuit breakers per DPI: AA and BBPS open after 3 consecutive failures for 30 min, ABHA for 20 min, Bhashini after 5 for 10 min; ONDC uses per-seller blacklisting instead. HTTP 429 never counts as a failure. Backoff uses jitter. (RB §4.4, §8)
29. When a DPI is down, run the graceful-degradation script for that domain instead of failing the product. (MC §4.7)

### Module architecture (MR v1.1, Codex review round 2 pending)
30. Phase 1 is a modular monolith: one FastAPI deployable, modules as Python packages under `modules/`, and a JSON-serialisable `ModuleRequest`/`ModuleResponse` envelope even for in-process calls. (MR §2, §6)
31. Call graph is deny-by-default: Supervisor→Core, Supervisor→Service, Core→Service and Core→DPI Gateway are allowed; Core→Core and Service→anything are forbidden. Cross-domain needs go back to the Supervisor as `conflict` or `needs_data`. (MR §3.2)
32. Each core module owns one PostgreSQL schema named after its `module_id`, connects with its own role, and sees only whitelisted kernel views. Audit writes go through a SECURITY DEFINER function. (MR §7.2)
33. Manifest validation fails closed. Duplicate intent codes abort registration. Manifest hash drift without a version bump blocks modules with mutating intents. (MR §4, §5, §8)
34. Unrecognised or malformed errors are `MOD_INTERNAL` (terminal). Mutating intents are never blind-retried. (MR §9)
35. `requires_consent_providers` may name only providers that issue consent handles: aa, abha, digilocker, ondc. BBPS and Bhashini are DPI providers for routing, not consent providers; a bill payment is gated by biometric approval and by an active AA consent for the balance check. (MR v1.1 §4.1)

### Design constraints (MC §10–11)
36. Solo-founder feasibility: managed services, proven tech, one language (Python), no Kubernetes or microservices at zero users.
37. When documents or suggestions conflict, prioritise in this order: user trust, system stability, long-term defensibility, DPI alignment, operational realism. No feature may trade privacy for growth.

---

## 5. Technology decisions (Phase 1)

- **Backend:** Python, FastAPI, single deployable. (MC §3.3, MR §2)
- **Database:** PostgreSQL 15+ (AWS RDS target), `pgcrypto` only, `TIMESTAMPTZ` in UTC, `VARCHAR` + `CHECK` instead of `ENUM`, soft deletes everywhere. (DM §1.1, §3, §10)
- **Migrations:** Alembic, one branch per module schema; `V001__initial_schema` seeds the SYSTEM family and `SYSTEM_ACTOR_UUID`. (DM §9.2)
- **Redis:** hot FSM session state, DPI rate-limit buckets, circuit-breaker state, AA coalescing keys, Healer and probe locks. PostgreSQL `supervisor_sessions` is the durable journal. (DM §3.7, RB §2, FTS §6.1.1)
- **Async work:** PostgreSQL `offline_task_queue` processed by the Healer. No RabbitMQ or Kafka in Phase 1 (deviation from MC §3.3, recorded in MR §2.3).
- **DPI simulators:** WireMock stubs for AA, BBPS, ABHA, ONDC and Bhashini with rate-limit, failure and chaos modes; contract tests keep stubs aligned with real schemas. (RB §9)
- **Testing:** pytest for unit tests, Testcontainers for integration, Playwright for end-to-end, k6 for load. Pyramid 60/30/10, 80 % coverage on core logic, 100 % pass on main. (PROJECT_TRACKER, Test Automation Strategy)
- **Observability:** structured JSON logs, Prometheus metrics with the names given in RB §10 and MR §11, Grafana, PagerDuty for P1 alerts.
- **Hosting:** India regions only (DPDP data localisation). Managed services over self-hosted. (MC §7.4, §10.1)
- **Frontend (decided 2026-09-17):** a PWA — React + Vite + TypeScript, Vitest for unit tests, Playwright for end-to-end. WebAuthn platform passkeys stand in for biometric approval. Native apps are deferred; the NFR's "local database" clause applies to them, not to the PWA.
- **LLM (decided 2026-09-17):** the Supervisor talks to a pluggable **LLM gateway** with a deterministic stub for tests, a local Ollama model (`qwen3.5:9b`) for development, and a hosted model for demo quality, **Claude Haiku by default** (any provider can be swapped in behind the gateway). No LangChain-style framework: plain provider SDK calls behind one interface, Pydantic schemas for intents. **PII boundary:** a hosted LLM receives only the utterance and non-PII context (roles, module names, amounts); never names, phone numbers, account or consent identifiers.
- **Python and packaging:** Python 3.12 managed by uv; ruff for lint/format; import-linter for the module contracts (MR §7.1); pre-commit runs both.
- **Local development:** Docker Compose with PostgreSQL 15, Redis and WireMock; no cloud resources until the demo deployment. **Hosting** is deferred: the demo runs on a single container host in an India region; the commercial choice (AWS ap-south-1 vs others) is made only if the project goes commercial.
- **Money:** integers in paise. **Time:** IST for user-facing windows, UTC in storage. **Languages:** `users.preferred_language` enum (en, hi, te, kn, ta, mr, gu, pa, bn, ml); user-facing strings are i18n keys rendered at runtime, never hardcoded in modules. (DM §3.2, MR §6.3)

---

## 6. Working rules

### Documents
- **Markdown only.** Never create or restore `.docx`, `.pptx` or `.txt` duplicates. One H1 per file. Use fenced code blocks for DDL, pseudo-code and JSON.
- **Every spec keeps its Document Governance table** (version, date, change, author) at the top. Bump the version and add a row for any content change. Author is "Shantanu Chaudhary" (add "with <agent>" when an agent drafted it) unless told otherwise.
- **Frozen documents are change-controlled.** Do not edit their content in place for convenience. A change needs: a version bump, a governance-table row, and an update to every dependent doc that names the old rule. Explicitly change-controlled sections: DM §3 and §5; FTS §4 and §6; CM §3, §4 and §9; all thresholds in RB.
- **Place new documents where the tracker's Document Status Matrix says they go:** `docs/specs/` for `Tech_Spec_*`, `docs/runbooks/` for `Runbook_*`, `docs/strategy/` for product and business documents, `docs/reference/` for background material. Use the exact file names listed in the tracker (for example `Security_Threat_Model.md`, `UX_Error_Message_Library.md`) so cross-references resolve.
- **Cross-reference by document name and section** (for example "FTS §6.4"), not by page or by file path alone. Do not duplicate content across specs; link to the owning spec.
- **Update `docs/PROJECT_TRACKER.md`** whenever a document changes status, a gap closes, or a new inconsistency is found. Add a dated line to its "Consolidation and change log".
- **Do not invent DPI facts.** Rate limits, uptime figures and API shapes are dated February 2026 and are flagged as such. If you add one, cite the source and date.
- **Do not edit `archive/`.** It is gitignored and exists only on the founder's machine. If something there turns out to be needed, copy it into `docs/` as Markdown with a provenance note.
- **Word documents that turn up later** are converted with `tools/docx2md.py` (`python tools/docx2md.py input.docx output.md 1`, where the last argument shifts heading levels by one so the file can get a single H1). Then add the standard header block used by the files in `docs/specs/` and archive the `.docx` under `archive/originals/`.

### Code (once implementation starts)
- Follow the Module Registry layout: `modules/{module_id}/manifest.json`, entrypoint `modules.{id}.agent:{Class}`, SDK under `familylifeos/sdk`, kernel under `familylifeos/kernel`. Modules import only the SDK, the standard library and declared dependencies; an import-linter contract enforces this in CI. (MR §7.1)
- Use the seed data in DM §8 (the Sharma family) as the canonical test fixture.
- The first vertical slice is "Priya pays the BESCOM electricity bill" (FTS §2, MR §10). Build in the order given by the build gate (§7).
- Never commit secrets, consent handles, push tokens or real PII. Test data is synthetic.
- Unit-test the invariants in §4 directly: idempotency reuse, hash-chain canonicalisation, cardinality races, soft-delete filters, gate ordering, fail-closed paths.

### Who does what (the roster)
The founder, **Shantanu Chaudhary**, decides, merges, and owns credentials, accounts and anything outward-facing. Three agents do the work. The full protocol is `coordination/README.md`; this is the binding summary.

| Agent | Label | Does | Never does |
|---|---|---|---|
| **Claude Code** | `agent:claude` | Architecture; specs and their revisions; reviews of Codex's and Gemini's work; roadmap, execution plan and tracker; cross-document consistency; threat model; write-ups; the tracker health check when work resumes after a pause | Merge; review its own work |
| **Codex** | `agent:codex` | Implementation against frozen specs, with tests; CI and deployment scripts; second reviewer on specs and on Claude's and Gemini's PRs | Edit frozen specs without a version bump; reopen logged decisions; merge |
| **Gemini in Antigravity** | `agent:gemini` | Routine generation with a clear source of truth: WireMock stubs from spec tables, Alembic migrations from DDL, fixtures, FHIR samples, cross-reference sweeps, PR summaries, lint and docstring passes, tracker and README sync. Orchestrates any **local models** (Ollama on the founder's machine) as its own sub-agents | Make design decisions; touch payment, consent or audit code paths; edit `docs/specs/`, `docs/runbooks/` or `AGENTS.md`; resolve an inconsistency-register item; merge |

- **Local models are not a roster member.** Gemini may delegate mechanical subtasks to them inside Antigravity. The issue and PR stay `agent:gemini`; Gemini answers for every line, its restrictions apply to whatever it delegates, it verifies the output itself, and its PR handoff says which parts a local model produced. Model choice and tuning: `docs/reference/Local_Agent_Setup.md`.
- **Review pairs:** Gemini → Codex; Codex → Claude; Claude → Codex. Never the author. The founder can review anything. If the default reviewer is unavailable, the other non-author agent reviews and says so.
- **One working folder per agent.** `D:\FamilyLifeOS` (founder and Claude Code, always on `main`), `D:\FamilyLifeOS-codex`, `D:\FamilyLifeOS-gemini` (git worktrees of the same repository). Work only in your own folder. Coordination commits go through `tools\coord.ps1 begin` / `push` (`coordination/README.md` §5). Stage by path; never `git add -A`, `git add .` or `git commit -a`.
- **Definition of Done** for every work package: `docs/Execution_Plan.md` §7.

### Coordination (how work moves between agents)
- The protocol is `coordination/README.md`. Tasks are GitHub issues from the Agent-task template with exactly one `agent:*` label, plus `in-progress` once picked up; work happens on `agent-<name>/issue-<n>` branches; every PR uses the template, carries `needs-review`, and is reviewed by a **different agent** than its author; only the founder merges.
- **Start every session** by reading your inbox (`coordination/inbox/<you>/`) and `coordination/STATUS.md`. **End every session** by updating your own STATUS section and sending any handoff or question as a message file in the recipient's inbox (template: `coordination/inbox/MESSAGE_TEMPLATE.md`). Review verdicts go on the PR; reviews of non-PR material go in the review issue. Changes that touch only `coordination/STATUS.md` and `coordination/inbox/**` go straight to `main` with a `coord:` subject via `tools\coord.ps1`; everything else goes through a PR.
- Decisions live in the tracker's Decision Log and are not reopened by agents. New inconsistencies are added to the register, not resolved in code.
- **Defaults, not constants** (founder ruling 2026-09-17). Where a rule is a family preference (who is reminded and when, who sees which document, when a dose counts as missed), build the recommended value as an adjustable default. Safety gates are never settings: payment gates, consent rules, the public-surface block, audit logging.
- **No dates, no capacity assumptions** (founder ruling 2026-09-17). Do not write target dates, week numbers, or expected founder hours into any document, issue or milestone. Plans are ordered by dependency and gated by exit criteria. Dates of record (when something was decided or changed) are fine.
- After each batch of merges, Claude Code syncs `coordination/BOARD.md` from the issues and proposes the next issues from `docs/Execution_Plan.md`.

### Session close-out: rulings go to the founder in chat (standing rule)
At the end of every working session with the founder, the agent reports **in the chat itself**, as part of the summary of what was done: every question that needs the founder's ruling, each with (a) a plain explanation, (b) the implications of each option where they apply, and (c) the agent's recommendation. Alongside it: what has already been decided that bears on the question, and the defaults the agent will apply if the founder does not object. Do not bury rulings in documents and point to them; documents (and `coordination/inbox/founder/`) get a copy, the chat gets the substance. Once ruled, the decision goes into the tracker's Decision Log.

### Communication
- State assumptions explicitly. When a spec and another spec disagree, do not pick silently; record it in the tracker's inconsistency register (§8) and ask.
- Keep the author persona and tone of the existing documents: direct, specific, reviewer-hardened.

---

## 7. Status and next steps

**Phase 1 Build Gate** (defined in `docs/PROJECT_TRACKER.md`). Nothing from P1/P2 starts until it passes.

Pre-conditions (status 2026-09-17):
- [x] Data Model v1.3 written (roles, resource lock table, session columns, folded-in tables, audit write protocol) — **Codex review round 2 pending, then re-freeze**
- [x] Tech_Spec_Financial_Transaction_Safety v1.2 — frozen
- [x] Tech_Spec_Consent_Manager v1.3 — v1.2 frozen text plus §2.6 (proxy consent), **Codex review round 2 pending**
- [x] Runbook_DPI_Rate_Limits v1.2 — frozen
- [x] Tech_Spec_Module_Registry v1.1 — review round 1 applied (7 fixes, §13) — **Codex review round 2 pending, then freeze**
- [x] PRD Core v2.2, NFR v2.2, Master Context v2.1 — aligned with the specs
- [x] Module PRDs (Vault, Finance, Health), Roadmap, Execution Plan, GTM Plan — drafted 2026-09-17, founder review pending
- [ ] Security_Threat_Model.md — P1, before any internet-facing deployment
- [ ] Tooling on the founder's machine: WSL 2, Docker Desktop; Codex desktop app and Antigravity opened on the repository (`docs/reference/Workstation_Setup.md`)

Then, in order (details and owners in `docs/Execution_Plan.md`):
1. Codex review round 2 of Data Model v1.3 and Module Registry v1.1; apply fixes; freeze both. Seed the Phase 0/1 issues.
2. Infrastructure: Docker Compose with PostgreSQL (all core tables), Redis, WireMock for BBPS (SUCCESS, FAILED, PENDING, NOT_FOUND, 429, timeout) and AA; `.env.example`.
3. Build targets: resource lock acquire/release → `supervisor_sessions` lifecycle → audit log write with hash chain → Healer cron → FinanceAgent BBPS call with Phase 2 commit.
4. Crash simulations A–D (FTS §4.5) and the single Playwright test "Priya pays BESCOM bill" must pass.

There are no target dates (founder ruling 2026-09-17): `docs/strategy/Roadmap.md` gives the order and the gates. The February 2026 week numbers still visible in the tracker's milestone section are historical.

---

## 8. Cross-document inconsistencies — status

All fifteen items found at consolidation were resolved or annotated on 2026-09-17; the register in `docs/PROJECT_TRACKER.md` records where each landed. In short: Data Model v1.3 settled the resource lock (table), the session columns (`fsm_state` plus four new columns), the role vocabulary (member, minor), the `cancelled` status, the ONDC provider, the action-code taxonomy (union; `BILL_PAYMENT_EXECUTED`, `CONSENT_WITHDRAWN`), the Healer cadence in the cleanup job, and `fetch_count_today` semantics. Master Context v2.1, NFR v2.2, PRD v2.2, FTS v1.2, CM v1.2 and RB v1.2 carry the matching annotations. Module Registry v1.1 fixed its own conflicts with the frozen specs (review log in MR §13).

Still open:
1. **Re-freeze.** Data Model v1.3, Module Registry v1.1 and the Consent Manager v1.3 addition (§2.6) are awaiting Codex review round 2. Until then, treat them as the current text but expect small changes.
2. **Per-user lock case.** PRD v2.2 §6 scopes the resource lock per family. If a genuine per-user case appears (two adults, separate accounts, same biller), the resource key must include the payer identity; decide during the Finance module PRD review (PRD §9).

If you find a new conflict, add a row to the tracker's register and stop; do not pick a side in code.

---

## 9. Project instructions carried over from the claude.ai project

The claude.ai project "FamilyLife OS" (February 2026) carries these standing instructions. They apply in this repository too and are the origin of several rules above.

- Master Context v2.0 is the canonical reference; defer to it for strategic and architectural decisions. The Project Tracker is the living scratchpad for status, gaps and priorities.
- Role: help create the Priority 0 specs; give technical guidance on multi-agent architecture, state machines and DPI integration patterns; review and critique decisions against India-specific constraints (network latency, DPI rate limits, regulatory compliance); keep consistency with the established architecture (Supervisor-Worker model, RBAC, zero-knowledge vault, tamper-proof audit log).
- Constraints to always enforce: solo-founder feasibility (managed services over self-hosted, proven tech over bleeding edge); privacy-first (zero-knowledge credential handling, consent-first access, DPDP Act compliance); human sovereignty (agents suggest, humans decide, no autonomous execution above Level 2); DPI-native (AA, BBPS, ABHA, ONDC, DigiLocker, Bhashini; no proprietary lock-in); financial safety (idempotency for all transactions, zombie recovery, two-phase commits).
- When writing a technical spec: read Master Context v2.0 and the relevant PRD and FSM sections first; follow the structure of the existing documents (Document Governance, main content, examples, Q&A); include concrete examples rather than abstract descriptions; specify exact table schemas, API contracts, state machines and error codes; consider failure modes explicitly (DPI down, two admins in conflict).
- Avoid: generic best practices without India-specific context; solutions that need 24/7 on-call; over-engineered architecture (blockchain, microservices, Kubernetes for 100 users); copying competitor patterns without understanding why they fit FamilyLifeOS.
- Tone: direct and technical, detailed and precise in specifications, candid about trade-offs and limitations, and push back when a suggestion violates a core constraint.
