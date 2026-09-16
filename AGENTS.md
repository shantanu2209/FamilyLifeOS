# AGENTS.md — FamilyLifeOS

Instructions for every AI coding agent (Claude Code, Codex, Cursor, Gemini, …) and for humans working in this repository. `CLAUDE.md` only points here. Keep this file as the single source of agent instructions; do not fork per tool.

---

## 1. What this repository is

**FamilyLifeOS** is an India-first, agentic "family operating system": a digital Chief of Staff for a household. It governs Health, Finance, Logistics, Home Operations, Communication, Elder Care, Documents and Learning through specialised worker agents coordinated by a **Supervisor** state machine. It is built natively on India's Digital Public Infrastructure (DPI): Account Aggregator (AA), BBPS, ABHA/ABDM, DigiLocker, ONDC and Bhashini. The atomic unit is the **family** (not the individual), with hierarchical role-based access control over the family graph.

**Current state (2026-09-16): documentation only, pre-development.** There is no application code, no test suite and no CI yet; the repository was put under git on 2026-09-16. The repository holds the strategy blueprint, five Priority-0 technical specifications (four frozen, one draft), a living project tracker and reference material. The next milestone is the **Phase 1 Build Gate** (§7).

The project is run by a solo founder who authors documents under the name **Alfred (Lead Product Architect)**. Specs were hardened through two independent review rounds each and then **frozen**. Treat frozen specs as contracts, not suggestions.

**Project mode (decided 2026-09-17): portfolio first.** The goal is a working kernel and the "Priya pays BESCOM bill" vertical slice against DPI simulators, built to the quality the specs demand. No regulatory licence applications are in progress, so no real-money DPI integration is planned; commercial expansion may follow if the result warrants it. The venture-oriented material in Master Context (phasing budgets, GTM, unit economics) is context, not the current plan. See the Decision Log in `docs/PROJECT_TRACKER.md`.

**The repository is public on GitHub.** `archive/` is local-only and gitignored. Never commit secrets, real PII, consent handles or push tokens; test data is synthetic.

---

## 2. Read this first, in this order

| # | File | Why |
|---|---|---|
| 1 | `AGENTS.md` (this file) | Rules, invariants, status, known gaps |
| 2 | `docs/strategy/Master_Context.md` | Canonical product, technical and strategy blueprint (v2.0) |
| 3 | `docs/PROJECT_TRACKER.md` | What is done, what is next, the build gate, the inconsistency register |
| 4 | `docs/strategy/PRD_FamilyLifeOS_Core.md` and `docs/specs/Tech_Spec_Supervisor_State_Machine.md` | The product requirements and the Supervisor FSM the frozen specs build on |
| 5 | `docs/specs/Data_Model_Schema.md` | Every table, column, index and query. Every other spec references it by name |
| 6 | The spec for the area you are touching | See the map in §3 |

Read whole documents. The specs put hard rules inside callout boxes and code comments, not only in headings.

---

## 3. Document map and status

Everything current lives under `docs/`. Everything historical lives under `archive/` and must not be edited or treated as current.

| Path | What it is | Version / status |
|---|---|---|
| `docs/strategy/Master_Context.md` | Canonical blueprint: identity, family graph, architecture, DPI strategy and risks, modules, data model summary, security, phasing, metrics, competition, revenue, GTM | **v2.0 — canonical**. Sections 3.3–3.4 and 6.1 are partly superseded (see §8) |
| `docs/strategy/Vision_Journey.md` | Strategic white paper (Jan 2026): how the product went from a portfolio app to a family OS | Reference / history |
| `docs/strategy/Master_PRD.md` | "Holistic LifeOS" master PRD v2.1 (Jan 2026): module-level requirements and DPI touchpoints | Reference. **Not** the scenario-driven Core PRD below |
| `docs/strategy/PRD_FamilyLifeOS_Core.md` | Core PRD v2.1: one-pager, 7-role RBAC matrix, 11 user scenarios, functional requirements, shared services, conflict-resolution matrix, KPIs, GTM | **v2.1 — canonical** (recovered from the claude.ai project 2026-09-16) |
| `docs/strategy/Vision_Parking_Lot.md` | Deferred capabilities with trigger conditions: blockchain audit log, live spatial reasoning, sub-800 ms latency, hardware presence, voting, future modules | v2.0 reference (recovered 2026-09-16) |
| `docs/specs/Data_Model_Schema.md` | 10 core PostgreSQL tables, full DDL, 12 operational queries, audit action taxonomy, lifecycle jobs, seed data | **FROZEN v1.2.1** |
| `docs/specs/Tech_Spec_Financial_Transaction_Safety.md` | Payment gates, two-phase commit, idempotency, the Healer, zombie recovery, refunds, FIN error codes | **FROZEN v1.1** ("launch readiness verified") |
| `docs/specs/Tech_Spec_Consent_Manager.md` | DPDP-native consent framework, purpose registry, `consent_records`, CONSENT_REVERIFY, DPI adapters, expiry watchdog, revocation, webhook security | **FROZEN v1.1** |
| `docs/specs/Tech_Spec_Module_Registry.md` | Module manifest schema, Supervisor→module dispatch envelope, tiers, isolation model, registration, error taxonomy | **DRAFT v1.0 — pending review**. Last P0 doc before the build gate |
| `docs/specs/Tech_Spec_Supervisor_State_Machine.md` | Supervisor FSM (state diagram, state definitions, persistence, Healer placeholder), automation tiers, TTL policy, idempotency keys | **v2.1 — canonical** (recovered 2026-09-16); implementation depth lives in the frozen P0 specs |
| `docs/specs/NFR_Specs.md` | Latency budgets, encryption, authentication, idempotency and rate-limit mandates, DPI circuit breaker, telemetry, compliance and retention | **v2.1 — canonical** (recovered 2026-09-16); scalability and DR sections still to be written |
| `docs/runbooks/Runbook_DPI_Rate_Limits.md` | Rate limits for all five DPIs, Redis budget tracker, circuit breakers, coalescing, WireMock stubs, on-call runbook | **FROZEN v1.1** |
| `docs/reference/DPI_Integration_Primer.md` | Early (Jan 2026) DPI cheat sheet: Beckn/ONDC flow, AA entity chain, ABHA/FHIR flow, Bhashini APIs, conflict object | Reference. Its JSON schemas and security notes are superseded by the Data Model and Master Context |
| `docs/templates/PRD_Template.md` | Deep-dive PRD template for module or feature PRDs | Template |
| `docs/PROJECT_TRACKER.md` | Living scratchpad: status, gaps, test strategy, build gate, parking lot, inconsistency register | Living document |
| `archive/` | Every original file (docx, duplicate md/txt, superseded versions, AI review notes) and the raw claude.ai exports | Historical, read-only, **local-only (gitignored, not on GitHub)** |

### 3.1 Recovered and still-missing documents

The four foundational documents that were absent at consolidation (Core PRD v2.1, Supervisor State Machine v2.1, NFR v2.1, Vision Parking Lot v2.0) were recovered on 2026-09-16 from the claude.ai project "FamilyLife OS", where they exist as knowledge files, and now live under `docs/` (see the map above). Only one referenced document does not exist yet:

- `Security_Threat_Model.md` — not yet written; escalated to late-P0, required before any external DPI integration. Target path `docs/specs/Security_Threat_Model.md`.

The claude.ai project does **not** hold the Consent Manager, Financial Transaction Safety, DPI Rate Limits or Module Registry specs; this repository is the only place they exist.

---

## 4. Non-negotiable invariants

These come from the frozen specs. Code, tests, new docs and refactors must honour them. Section references use DM = Data Model Schema, FTS = Financial Transaction Safety, CM = Consent Manager, RB = DPI Rate Limits runbook, MR = Module Registry, MC = Master Context.

### Family graph and access
1. `family_id` is the partition key on every table. Every query is family-scoped. (DM §1.1)
2. RBAC is deny-by-default and enforced in the application layer at every endpoint and before every dispatch. (DM Q2, MR §7.3)
3. Cardinality per family: admins 1–2, spouse ≤2, child ≤10, elder ≤4, staff ≤5, managed ≤10, passive ≤10; exactly one primary proxy and at most one secondary per managed profile. Checks run inside a transaction with `SELECT … FOR UPDATE` on the family row. (DM §4)
4. The last admin can never be removed or demoted. (DM §4.1)
5. Relationship edges are bidirectional and both edges are written in one transaction. (DM §3.3)
6. A device flagged `is_public_surface` never shows finance, health, vault documents or member PII, whoever is logged in. (DM §3.8, MR §6.2)
7. Soft delete: every query that joins `users` filters `deleted_at IS NULL` unless it is explicitly historical. Hard purge runs nightly at 01:00 IST after 24 h. (DM §4.3, §7.1)

### Consent and privacy
8. No data is collected, accessed or processed without an active `consent_records` row for a registered `purpose_code`. Unknown purpose = blocked operation. (CM §3)
9. The application database never stores raw credentials, tokens, Aadhaar numbers, UPI IDs or account numbers. Only opaque consent handles and UUIDs. Consent travels by reference inside envelopes. (DM §1.1, MC §7, MR §6.1)
10. `CONSENT_REVERIFY` runs immediately before any external execution, always reads live from the database (never a cache), and fails safe when the DPI cannot be reached. (CM §5)
11. Consent is granted only by a human via biometric or PIN. The Supervisor may prompt for consent; it can never grant it. (CM §1.3)
12. Minors need `parental_consent_user_id`; no analytics or behavioural collection for minors. (CM §2.5)
13. On account deletion: abort non-terminal sessions, revoke DPI consents at T+0, keep the 24 h soft-delete window for first-party data only. (CM §2.2)
14. DPI webhooks are verified (JWS for Sahamati, JWT for ABDM), replay-protected (5-minute window, `txnid`/`jti` cache) and rejected with 503 when the signing keys are unavailable. (CM §9)

### Financial execution
15. Automation Level 3 is forbidden in V1; manifests cap `automation_tier_ceiling` at 2. BBPS bill payments require biometric approval. The Healer reconciles; it never approves or creates a payment. (MR §4.1, FTS §2.2, FTS §6.1)
16. One UUIDv4 idempotency key per session, generated at `INTENT_ANALYSIS`, persisted to `supervisor_sessions` in the Phase 1 COMMIT **before** any external call. Retries and Healer re-submissions reuse the original key. Never generate a new key for the same payment. (FTS §5, §6.4)
17. Two-phase commit: Phase 1 moves the session to `EXECUTION` with the key; then the external call; Phase 2 writes the audit row and the session update in one transaction. The resource lock is released only after the Phase 2 COMMIT. (FTS §4)
18. Five pre-execution gates, in order: RBAC → resource lock → forced AA balance fetch → biometric → CONSENT_REVERIFY. (FTS §2.2)
19. A session in `EXECUTION` for more than 5 minutes is a zombie. The Healer runs every 5 minutes under a Redis distributed lock, processes `AUDIT_LOG_WRITE` tasks first, applies per-run caps and a system-level circuit breaker. (FTS §6–7)
20. Financial errors use the `FIN_001`–`FIN_015` taxonomy. Raw codes are never shown to users. (FTS §10)

### Audit log
21. `audit_log` is append-only; the application DB user has no UPDATE or DELETE on it. (DM §3.6)
22. `current_hash = SHA256(log_id || user_id || action || canonical_details || previous_hash)` where `canonical_details = json.dumps(details, sort_keys=True, separators=(',', ':'))`, computed in application code, chained per family, verified daily. (DM §3.6, §7.2)
23. Only standardised action codes (DM §6 plus the CM §4.4 additions). `details` carries UUIDs and amounts only, never PII. System jobs write as `SYSTEM_ACTOR_UUID`. (DM §6)
24. Any writer that competes with the Healer locks the latest audit row with `SELECT … FOR UPDATE` before computing `previous_hash`. (FTS §11.3)

### DPI resilience
25. Rate limits as of Feb 2026: AA 3 fetches/hour per consent handle; BBPS 50 transactions/day per user; ABHA 10 consent grants/day per user; ONDC 100 searches/day (soft); Bhashini 1000 ASR calls/day org-wide with a 100/day per-family soft throttle. Verify against sandbox portals before each release. (RB §1, §7.2)
26. Budget checks use the atomic Lua check-and-increment; TTLs align to the IST hour or midnight; every Redis key is prefixed `{env}:`. (RB §2)
27. If Redis is unavailable, budget checks fail open, except BBPS which fails closed. (RB §2.4)
28. Circuit breakers per DPI: AA and BBPS open after 3 consecutive failures for 30 min, ABHA for 20 min, Bhashini after 5 for 10 min; ONDC uses per-seller blacklisting instead. HTTP 429 never counts as a failure. Backoff uses jitter. (RB §4.4, §8)
29. When a DPI is down, run the graceful-degradation script for that domain instead of failing the product. (MC §4.7)

### Module architecture (draft, MR v1.0)
30. Phase 1 is a modular monolith: one FastAPI deployable, modules as Python packages under `modules/`, and a JSON-serialisable `ModuleRequest`/`ModuleResponse` envelope even for in-process calls. (MR §2, §6)
31. Call graph is deny-by-default: Supervisor→Core, Supervisor→Service, Core→Service and Core→DPI Gateway are allowed; Core→Core and Service→anything are forbidden. Cross-domain needs go back to the Supervisor as `conflict` or `needs_data`. (MR §3.2)
32. Each core module owns one PostgreSQL schema named after its `module_id`, connects with its own role, and sees only whitelisted kernel views. Audit writes go through a SECURITY DEFINER function. (MR §7.2)
33. Manifest validation fails closed. Duplicate intent codes abort registration. Manifest hash drift without a version bump blocks modules with mutating intents. (MR §4, §5, §8)
34. Unrecognised or malformed errors are `MOD_INTERNAL` (terminal). Mutating intents are never blind-retried. (MR §9)

### Design constraints (MC §10–11)
35. Solo-founder feasibility: managed services, proven tech, one language (Python), no Kubernetes or microservices at zero users.
36. When documents or suggestions conflict, prioritise in this order: user trust, system stability, long-term defensibility, DPI alignment, operational realism. No feature may trade privacy for growth.

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
- **Money:** integers in paise. **Time:** IST for user-facing windows, UTC in storage. **Languages:** `users.preferred_language` enum (en, hi, te, kn, ta, mr, gu, pa, bn, ml); user-facing strings are i18n keys rendered at runtime, never hardcoded in modules. (DM §3.2, MR §6.3)

---

## 6. Working rules

### Documents
- **Markdown only.** Never create or restore `.docx`, `.pptx` or `.txt` duplicates. One H1 per file. Use fenced code blocks for DDL, pseudo-code and JSON.
- **Every spec keeps its Document Governance table** (version, date, change, author) at the top. Bump the version and add a row for any content change. Author is "Alfred" unless told otherwise.
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

### Local agent (Ollama model run through Codex CLI)
- Setup and rationale: `docs/reference/Local_Agent_Setup.md`. Everyday model `qwen3.5:9b`; heavier local model `qwen3.6:35b`. Launched with `tools/agent-local.ps1` on issues labelled `agent:local`.
- **May do:** formatting, docstrings, lint fixes, boilerplate from templates, test fixtures, WireMock stubs generated from spec tables, keeping the tracker's status matrix in sync, commit messages, PR summaries. Anything with a script or test that verifies the result.
- **Must not do:** edit anything under `docs/specs/` or `docs/runbooks/` (frozen), touch the payment, consent or audit code paths, edit `AGENTS.md`, or merge. It never resolves an inconsistency register item.
- Every local run ends in a PR labelled `agent:local` and `needs-review`; a different agent (Claude Code or Codex cloud) reviews before merge.

### Communication
- State assumptions explicitly. When a spec and another spec disagree, do not pick silently; record it in the tracker's inconsistency register (§8) and ask.
- Keep the author persona and tone of the existing documents: direct, specific, reviewer-hardened.

---

## 7. Status and next steps

**Phase 1 Build Gate** (defined in `docs/PROJECT_TRACKER.md`). Nothing from P1/P2 starts until it passes.

Pre-conditions:
- [x] Data_Model_Schema v1.2.1 — frozen
- [x] Tech_Spec_Financial_Transaction_Safety v1.1 — frozen
- [x] Tech_Spec_Consent_Manager v1.1 — frozen
- [x] Runbook_DPI_Rate_Limits v1.1 — frozen
- [ ] Tech_Spec_Module_Registry v1.0 — **draft, needs the two-reviewer round and freeze**
- [ ] Security_Threat_Model.md — not started (must exist before any external DPI integration)
- [x] The four foundational documents recovered from the claude.ai project and added as Markdown (2026-09-16)

Then, in order:
1. Resolve inconsistency register items 1–3 (resource lock storage, session column names, role vocabulary) with a Data Model v1.3 that also folds in `consent_records`, `consent_ui_disclosures` and the registry tables.
2. Infrastructure: Docker Compose with PostgreSQL (all core tables), Redis, WireMock for BBPS (SUCCESS, FAILED, PENDING, NOT_FOUND, 429, timeout) and AA; `.env.example`.
3. Build targets: resource lock acquire/release → `supervisor_sessions` lifecycle → audit log write with hash chain → Healer cron → FinanceAgent BBPS call with Phase 2 commit.
4. Crash simulations A–D (FTS §4.5) and the single Playwright test "Priya pays BESCOM bill" must pass.

The week numbers in the tracker date from February 2026 and are stale; re-baseline the timeline before planning against them.

---

## 8. Known cross-document inconsistencies

Full detail and resolution paths are in `docs/PROJECT_TRACKER.md` → "Cross-Document Inconsistency Register". Summary, most important first:

1. **Resource lock storage.** DM §3.7 models the lock as a column `supervisor_sessions.resource_lock` with a partial unique index; FTS §2.3, §4, §9 and the build gate assume a separate `resource_lock` table (`family_id, resource_key, session_id, acquired_by, acquired_at, released_at`). Pick one via DM v1.3.
2. **Session column names.** DM uses `fsm_state`; FTS and CM use `session_status`. FTS also uses `intent_type`, `bbps_transaction_ref_id`, `healer_poll_count` and `session_notes` on `supervisor_sessions`, none of which exist in DM §3.7.
3. **Role vocabulary.** DM and MC store `admin, spouse, child, elder, staff, managed, passive`; MR manifests and the (missing) PRD v2.1 use `admin, member, minor, elder, staff, managed, passive`; CM uses upper-case `MINOR`, `ADMIN`, `MEMBER`. The frozen DB values win until a migration says otherwise; define the mapping.
4. **Architecture deviation.** MC §3.3–3.4 say REST + JWT between agents, RabbitMQ and Kubernetes; MR §2 (draft) specifies an in-process modular monolith with a JSON envelope and the Postgres task queue. MC needs a v2.1 back-annotation once MR is frozen.
5. **Circuit-breaker thresholds.** NFR §3 says BBPS 3 consecutive failures → 30 min; MC §3.4 and PRD §4.6 say a *module* trips after 5 failures. MR §6.5 resolves this as two layers (DPI gateway 3, module breaker 5); RB §8.2 has per-DPI values. NFR and PRD need the same note.
6. **Audit hash formula.** MC §6.1 keeps a DB CHECK on `SHA256(timestamp||user_id||action||previous_hash)`; DM §3.6 removed the CHECK and defines the hash over `log_id, user_id, action, canonical_details, previous_hash` in application code. DM wins; MC §6 is superseded by DM.
7. **Action-code names.** DM §6 defines `BILL_PAYMENT_INITIATED / SUCCESS / FAILED`; FTS writes `BILL_PAYMENT_EXECUTED`, `BILL_PAYMENT_ZOMBIE_FAILED`, `BILL_PAYMENT_REFUND_*`, `ADMIN_SESSION_OVERRIDE`; RB writes `VOICE_ASR_LOW_CONFIDENCE`; CM adds ten more. The taxonomy in DM §6 needs the union.
8. **Healer cadence.** FTS sets 5 minutes; DM §7.4 still says "every 15 minutes (same cadence as Healer)".
9. **Biometric threshold.** NFR §2.2: above ₹2,000 or any PII export; FTS §1.3: above ₹100 (the ₹100 comes from the FSM §2 automation-tier examples, where it marks the Level 1/Level 2 boundary, not a biometric rule); FTS §2.2 gate G4: all BBPS payments regardless of amount. G4 is the operative rule for bill pay; manifests may only lower a threshold (MR §4.1).
10. **`offline_task_queue.status = 'cancelled'`** (CM §8.2) is not an allowed value in DM §3.9.
11. **`fetch_count_today` semantics.** DM §7.3 resets it daily at midnight UTC and Q6 compares it to the hourly AA limit; RB §2 enforces AA hourly in Redis and treats the DB column as the persistent record for renewal inheritance. State the semantics in one place.
12. **Module Registry date.** Its governance table says 2026-07-03 while every other document says 2026-02-21; the pre-consolidation tracker still listed it as not started.
13. **Resource-lock scope.** PRD §6 allows one active EXECUTION per resource *per user*; FTS §9.4 scopes the lock per *family* (a spouse is blocked while the admin pays the same biller). FTS is the frozen spec; PRD needs the note.

---

## 9. Project instructions carried over from the claude.ai project

The claude.ai project "FamilyLife OS" (February 2026) carries these standing instructions. They apply in this repository too and are the origin of several rules above.

- Master Context v2.0 is the canonical reference; defer to it for strategic and architectural decisions. The Project Tracker is the living scratchpad for status, gaps and priorities.
- Role: help create the Priority 0 specs; give technical guidance on multi-agent architecture, state machines and DPI integration patterns; review and critique decisions against India-specific constraints (network latency, DPI rate limits, regulatory compliance); keep consistency with the established architecture (Supervisor-Worker model, RBAC, zero-knowledge vault, tamper-proof audit log).
- Constraints to always enforce: solo-founder feasibility (managed services over self-hosted, proven tech over bleeding edge); privacy-first (zero-knowledge credential handling, consent-first access, DPDP Act compliance); human sovereignty (agents suggest, humans decide, no autonomous execution above Level 2); DPI-native (AA, BBPS, ABHA, ONDC, DigiLocker, Bhashini; no proprietary lock-in); financial safety (idempotency for all transactions, zombie recovery, two-phase commits).
- When writing a technical spec: read Master Context v2.0 and the relevant PRD and FSM sections first; follow the structure of the existing documents (Document Governance, main content, examples, Q&A); include concrete examples rather than abstract descriptions; specify exact table schemas, API contracts, state machines and error codes; consider failure modes explicitly (DPI down, two admins in conflict).
- Avoid: generic best practices without India-specific context; solutions that need 24/7 on-call; over-engineered architecture (blockchain, microservices, Kubernetes for 100 users); copying competitor patterns without understanding why they fit FamilyLifeOS.
- Tone: direct and technical, detailed and precise in specifications, candid about trade-offs and limitations, and push back when a suggestion violates a core constraint.
