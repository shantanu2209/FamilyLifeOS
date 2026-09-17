# Project Tracker — Historical Snapshot (February 2026 sections)

> **Status:** HISTORICAL — not maintained · **Owner:** Shantanu Chaudhary · **Last content change:** 2026-09-17
> **What this is:** the sections removed from `docs/PROJECT_TRACKER.md` on 2026-09-17, verbatim. Most were written in February 2026 for a venture-style plan with week and month numbers, a hired QA engineer and hosting decisions; some were kept current until September. They are superseded by: `docs/INDEX.md` (document status), `docs/strategy/Roadmap.md` and `docs/Execution_Plan.md` (the plan), `docs/specs/Test_Automation_Strategy.md` (testing), `docs/reference/Workstation_Setup.md` (environment), AGENTS.md §5 (technology decisions) and the GitHub project board (next actions). **Do not act on anything here and do not update it.** It exists so that the reasoning of the time is not lost. Version numbers, week numbers and statuses below are as they were.

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

---

## 📌 Near-Term Parking Lot (Ideas for Next 3-6 Months)

**Note:** Long-term vision items (12-24+ months) are in `docs/strategy/Vision_Parking_Lot.md` (v2.0)







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

*(Schema evolution items, the strategic risk register and the Phase 1 Build Gate remain in the living tracker.)*

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

---

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
