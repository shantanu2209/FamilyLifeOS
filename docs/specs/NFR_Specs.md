# Non-Functional Requirements (NFR) Specs: FamilyLifeOS

> **Status:** CANONICAL — v2.2 (adds scalability, disaster recovery, degradation order and threat-model sections; portfolio-mode notes) · **Author:** Shantanu Chaudhary (Lead Product Architect) · **Last content change:** 2026-09-17
> **Canonical copy.** Recovered on 2026-09-16 from the claude.ai project "FamilyLife OS" knowledge file `FamilyLifeOS_NFR_Specs_v2_1.md.docx` (the text claude.ai extracted from the Word file, kept verbatim in `archive/claude-project-exports/`). Content is unchanged; Markdown formatting was normalised (tables, list wrapping, escaped characters).
> **Cited elsewhere as:** NFR v2.1, FamilyLifeOS_NFR_Specs_v2_1, NFR §n.
> **Note:** §3 DPI circuit breaker (3 failures → 30 min) is the DPI-gateway layer; the 5-failure module breaker in Master Context §3.4 and PRD §4.6 is a separate layer (Tech_Spec_Module_Registry §6.5). §4 telemetry FSM_Exit_State must stay in sync with Data_Model_Schema §3.6.

**Status:** Phase 1 (Launch Ready v2.1)

**Scope:** Performance, Security, Reliability, and Compliance standards for the V1 Core Kernel.

## 0. Document Governance

| **Version** | **Date** | **Description of Change** | **Author** |
|---|---|---|---|
| v0.1 | 2026-02-13 | Initial draft defining standard performance and security budgets. | Shantanu Chaudhary |
| v1.0 | 2026-02-13 | **Operational Hardening:** Added Idempotency requirements for financial safety. Relaxed latency targets (<2.0s) to align with India network realities. Added Data Localization (DPDP) mandates. | Shantanu Chaudhary |
| v2.0 | 2026-02-13 | **Execution Release:** Mandated Rate Limiting and Idempotency Persistence Timing. | Shantanu Chaudhary |
| v2.1 | 2026-02-13 | **Refinement Release:** Expanded Telemetry hygiene fields. | Shantanu Chaudhary |
| v2.2 | 2026-09-17 | **Completeness release** (closes the tracker's NFR gaps): new §6 Scalability Targets, §7 Disaster Recovery, §8 Performance Degradation Order, §9 Security Threat Model reference, §10 Compliance checklist pointer; §2.1 and §2.2 annotated for the PWA build and the biometric-gate layering; §3 circuit-breaker layering note (Inconsistency Register item 5); §4 telemetry enum sync rule with Data Model §3.6. No existing budget or mandate changed. | Shantanu Chaudhary (with Claude Code) |

## 1. Performance & Latency Budgets

| **Metric** | **Budget** | **Rationale** |
|---|---|---|
| **Router Overhead** | < 200ms | The time Core takes to identify Intent and select an Agent. |
| **Inter-Agent Handoff** | < 400ms | Time for Supervisor to pass context to Worker. |
| **End-to-End Latency** | **< 2.0s** | 95th Percentile for full Voice Query -> Voice Response loop (Accounting for Bhashini + LLM + TTS). |
| **App Load Time (Cold)** | < 2s | "Time to Interactive" on mid-range Android devices. |
| **Offline Queue Sync** | < 30s | Time to sync queued tasks once connectivity is restored. |

## 2. Security & Data Privacy

### 2.1. Encryption Standards

- **Data at Rest:** AES-256 for all local databases (SQLite/Realm) and Cloud Databases. *(v2.2: the portfolio build is a PWA; "local databases" applies to the deferred native apps. Browser storage holds no financial or health data — only session tokens and UI preferences.)*

- **Data in Transit:** TLS 1.3 enforced for all API calls.

- **Zero-Knowledge:** The "Vault" encryption keys must be derived from the User's Master Password/Biometric. The Server **never** sees the raw key.

### 2.2. Authentication

- **Session Timeout:** 15 minutes for Finance/Vault modules; 30 days for HomeOps/Logistics.

- **Biometric Mandate:** Required for any transaction > ₹2000 or any PII data export. *(v2.2 layering: this is the system-wide floor. BBPS bill payments require approval at any amount — Tech_Spec_Financial_Transaction_Safety §2.2 gate G4 — and a module manifest may only lower the threshold, never raise it — Tech_Spec_Module_Registry §4.1. In the PWA, WebAuthn platform passkeys stand in for device biometrics.)*

## 3. Reliability, Uptime & Transaction Safety

- **System Uptime SLA:** 99.9% (approx. 43 mins downtime/month allowed).

- **Idempotency Requirement:**

    - **Financial Operations:** All Payment and Consent tokens must be idempotent. Retrying a pay_bill() call with the same transaction_id must NOT result in a double charge.

    - **Persistence Timing:** The Idempotency Key MUST be persisted to the database **before** the external API call is initiated.

- **Rate Limiting (Backpressure):**

    - **AA Refreshes:** Max 3 full refreshes per user per hour to prevent Account Aggregator IP bans.

    - **Retry Logic:** If rate limit is hit, return user-friendly "Data is updating, please wait" message.

- **DPI Circuit Breakers:**

    - If BBPS fails 3 times consecutively, switch FinanceAgent UI to "Status: Maintenance" for 30 minutes.

    - Do not retry immediately. Use Exponential Backoff (1s, 2s, 4s, 8s).

- **Breaker Layering (v2.2):** the rule above is the **DPI-gateway** breaker; per-provider thresholds and open durations are in Runbook_DPI_Rate_Limits §8.2 (AA/BBPS 3 → 30 min, ABHA 3 → 20 min, Bhashini 5 → 10 min, ONDC per-seller blacklist). The **module-level** breaker (5 consecutive failures → module OPEN 30 min) is Master Context §3.4 / Tech_Spec_Module_Registry §6.5. HTTP 429 never counts as a failure at either layer.

## 4. Observability & Logging

- **Standard Telemetry:** Log Module_ID, Intent_Type, Latency, and Success_Status.

- **Telemetry Expansion (v2.1):**

    - FSM_Exit_State (SUCCESS / FAILED / ABORTED) *(v2.2: must stay identical to the `audit_log.fsm_exit_state` CHECK in Data Model §3.6; a new exit state is added to both in one change.)*

    - Automation_Tier (Level 0 / 1 / 2)

    - Cache_Hit_Ratio (Hit vs Miss)

- **Anonymity:** **NEVER** log PII (Names, Phone Numbers, UPI IDs) in application logs. Use UUIDs.

- **Crash Reporting:** Integration with Sentry/Crashlytics for immediate fatal error tracking.

## 5. Compliance & Data Retention

- **Data Localization:** All Family Graph and Vault data must reside on servers physically located in India (DPDP Act compliance).

- **Audit Log Retention:** 7 Years (Financial/Legal standard).

- **Account Deletion:** "Right to be Forgotten" - User deletion must purge all Cloud Data within 24 hours and revoke all AA/ABHA Consents immediately.

## 6. Scalability Targets [v2.2]

| Target | Portfolio build (current) | Commercial Phase 1 | Commercial Phase 2+ |
|---|---|---|---|
| Families | 1–10 (Sharma seed + testers) | 10,000 on one deployable (Master Context §3.5) | 100,000 with sharding by family_id; 1M+ multi-region |
| Concurrent sessions | ≤ 10 | 500 | scale-out, stateless API workers |
| API throughput | not a target; correctness and latency budgets (§1) are | 50 requests/s sustained, 200 burst | horizontal |
| Database | single PostgreSQL 15 in Docker Compose | single managed instance with read replica for verification jobs | shard by family_id |
| Healer | one instance; distributed lock still enforced (FTS §6.1.1) | one instance | one per shard, lock per shard |
| Load test (k6) | the Playwright slice under 10 concurrent users | 1,000 concurrent users × 5 calls/min, P95 < 2.0 s, errors < 0.1 % | per-shard |

## 7. Disaster Recovery [v2.2]

- **Objectives:** RTO 4 hours, RPO 1 hour (tracker decision). Portfolio build: RTO best-effort, RPO 24 hours (nightly dump), because no real family data exists.
- **Backups:** nightly full backup plus continuous WAL archiving (commercial); nightly `pg_dump` to a second disk (portfolio). Audit-log retention is 7 years (§5), so backups of `audit_log` partitions are retained for 7 years and verified quarterly with the hash-chain job (Data Model §7.2).
- **Failover:** primary region failure → restore in the secondary India region within 15 minutes of decision; DNS switch; DPI webhooks re-registered. Redis is disposable: sessions are reconciled from the PostgreSQL journal on boot (FSM §1.3), so Redis loss costs at most in-flight approvals, which are re-prompted.
- **Drills:** quarterly restore drill measuring actual RTO/RPO; results logged in the tracker.
- **Runbook:** Disaster_Recovery_Plan.md (P2) holds the step-by-step; this section holds the objectives.

## 8. Performance Degradation Order [v2.2]

When capacity or a dependency degrades, shed load in this order, never the reverse:

1. Voice → text input (Bhashini soft-throttle and org budget, Runbook §7.2).
2. Non-critical fetch TTLs extended (health records 7 d → on-demand only; school circulars 12 h → 24 h) and stale-data banners shown.
3. ONDC search and product analytics disabled.
4. Level 2 semi-automatic actions paused (recurring payments wait for the next window).
5. New Level 1 executions queued in `offline_task_queue` with an honest message.

Never shed: the five pre-execution gates, CONSENT_REVERIFY, audit writes, the Healer, or SOS handling. If those cannot run, the system refuses new financial intents rather than running them unsafely (fail closed, Runbook §2.4).

## 9. Security Threat Model Reference [v2.2]

`Security_Threat_Model.md` is a P1 document due before any internet-facing deployment (portfolio demo or commercial). It must cover: entry points (API, DPI webhooks, push callbacks, WebAuthn ceremonies); trust boundaries (authenticated sessions trusted; webhook payloads, ONDC seller responses and LLM outputs untrusted); consent-handle storage compromise; webhook forgery (revalidation_required denial of service — interim control: Consent Manager §9); privilege escalation across roles and shadow nodes; insider DBA tampering (control: hash chain, Data Model §3.6); Redis poisoning blast radius; DPDP breach-notification mapping. Until it exists, the interim controls are the ones cited in the specs.

## 10. Compliance Checklist Pointer [v2.2]

The pre-launch security audit, compliance requirements (DPDP, RBI AA, NPCI BBPS, ABDM, IT Act) and ongoing security practices are tracked as checklists in `docs/PROJECT_TRACKER.md` → "Security & Compliance Checklist". In portfolio mode they are informational; they become gating when the project goes commercial.
