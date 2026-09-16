# Non-Functional Requirements (NFR) Specs: FamilyLifeOS

> **Status:** CANONICAL — v2.1 (Phase 1, Launch Ready); scalability and DR sections still to be written · **Author:** Alfred (Lead Product Architect) · **Last content change:** 2026-02-13
> **Canonical copy.** Recovered on 2026-09-16 from the claude.ai project "FamilyLife OS" knowledge file `FamilyLifeOS_NFR_Specs_v2_1.md.docx` (the text claude.ai extracted from the Word file, kept verbatim in `archive/claude-project-exports/`). Content is unchanged; Markdown formatting was normalised (tables, list wrapping, escaped characters).
> **Cited elsewhere as:** NFR v2.1, FamilyLifeOS_NFR_Specs_v2_1, NFR §n.
> **Note:** §3 DPI circuit breaker (3 failures → 30 min) is the DPI-gateway layer; the 5-failure module breaker in Master Context §3.4 and PRD §4.6 is a separate layer (Tech_Spec_Module_Registry §6.5). §4 telemetry FSM_Exit_State must stay in sync with Data_Model_Schema §3.6.

**Status:** Phase 1 (Launch Ready v2.1)

**Scope:** Performance, Security, Reliability, and Compliance standards for the V1 Core Kernel.

## 0. Document Governance

| **Version** | **Date** | **Description of Change** | **Author** |
|---|---|---|---|
| v0.1 | 2026-02-13 | Initial draft defining standard performance and security budgets. | Alfred |
| v1.0 | 2026-02-13 | **Operational Hardening:** Added Idempotency requirements for financial safety. Relaxed latency targets (<2.0s) to align with India network realities. Added Data Localization (DPDP) mandates. | Alfred |
| v2.0 | 2026-02-13 | **Execution Release:** Mandated Rate Limiting and Idempotency Persistence Timing. | Alfred |
| v2.1 | 2026-02-13 | **Refinement Release:** Expanded Telemetry hygiene fields. | Alfred |

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

- **Data at Rest:** AES-256 for all local databases (SQLite/Realm) and Cloud Databases.

- **Data in Transit:** TLS 1.3 enforced for all API calls.

- **Zero-Knowledge:** The "Vault" encryption keys must be derived from the User's Master Password/Biometric. The Server **never** sees the raw key.

### 2.2. Authentication

- **Session Timeout:** 15 minutes for Finance/Vault modules; 30 days for HomeOps/Logistics.

- **Biometric Mandate:** Required for any transaction > ₹2000 or any PII data export.

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

## 4. Observability & Logging

- **Standard Telemetry:** Log Module_ID, Intent_Type, Latency, and Success_Status.

- **Telemetry Expansion (v2.1):**

    - FSM_Exit_State (SUCCESS / FAILED / ABORTED)

    - Automation_Tier (Level 0 / 1 / 2)

    - Cache_Hit_Ratio (Hit vs Miss)

- **Anonymity:** **NEVER** log PII (Names, Phone Numbers, UPI IDs) in application logs. Use UUIDs.

- **Crash Reporting:** Integration with Sentry/Crashlytics for immediate fatal error tracking.

## 5. Compliance & Data Retention

- **Data Localization:** All Family Graph and Vault data must reside on servers physically located in India (DPDP Act compliance).

- **Audit Log Retention:** 7 Years (Financial/Legal standard).

- **Account Deletion:** "Right to be Forgotten" - User deletion must purge all Cloud Data within 24 hours and revoke all AA/ABHA Consents immediately.
