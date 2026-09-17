# PRD: FamilyLifeOS Core (The Micro-Kernel)

> **Status:** CANONICAL — v2.2 (v2.1 plus specification map, three error scenarios and three annotations) · **Author:** Shantanu Chaudhary (Lead Product Architect) · **Last content change:** 2026-09-17
> **Canonical copy.** Recovered on 2026-09-16 from the claude.ai project "FamilyLife OS" knowledge file `PRD_FamilyLifeOS_Core_v2_1.md.docx` (the text claude.ai extracted from the Word file, kept verbatim in `archive/claude-project-exports/`). Content is unchanged; Markdown formatting was normalised (tables, list wrapping, escaped characters).
> **Cited elsewhere as:** PRD v2.1, PRD_FamilyLifeOS_Core_v2_1, Core PRD, PRD Scenario n, PRD §n.
> **Note:** The scenario-driven Core PRD that every tech spec cites. The January module-level Master_PRD.md is a different, earlier document.

**Status:** Phase 1 (Launch Ready v2.1)

**Author:** Shantanu Chaudhary (Lead Product Architect)

**Primary Agent:** Supervisor Agent (The Orchestrator / Concierge)

**Engineering Lead:** TBD

**Design Lead:** TBD

**Approvers:** Director

## 0. Document Governance

| **Version** | **Date** | **Description of Change** | **Author** |
|---|---|---|---|
| v1.0-2.0 | 2026-02-13 | Iterative refinements (Execution Pivot, Gold Master). | Shantanu Chaudhary |
| v2.1 | 2026-02-13 | **Refinement Release:** Added Resource-Level Locking, SOS Passive Reconciliation, and Telemetry refinements. | Shantanu Chaudhary |
| v2.2 | 2026-09-17 | **Spec-alignment release:** §4.8 specification map linking every requirement to the frozen specs that implement it; Scenarios 12–14 (crash mid-payment, concurrent payment, consent revoked mid-flow) close the tracker's "only happy paths" gap; §4.6 circuit-breaker layering and Consent Manager reference; §4.7 Healer cadence (5 minutes) and audit write protocol; §6 Concurrent Intents scoped per family (Inconsistency Register item 15); §8 portfolio-first note; §9 DPI rate-limit issue closed by the Runbook. Role names unchanged; Data Model v1.3 now uses them. | Shantanu Chaudhary (with Claude Code) |

## 1. The One-Pager (Executive Summary)

- **Overview:** FamilyLifeOS Core is the foundational "Micro-Kernel" of a venture-scale Family Operating System. It is a headless, agentic engine designed to orchestrate Health, Wealth, and Logistics for the Indian household by leveraging Digital Public Infrastructure (DPI) like ABHA, Account Aggregator (AA), and ONDC.

- **The Problem (The Friction):** Modern households suffer from "Decision Fatigue" and "Digital Fragmentation." Families juggle dozens of siloed apps (banking, health, school, staff management) with no shared context. There is no system that understands that a "Low Bank Balance" should automatically deprioritize "Vacation Planning". Furthermore, household trust requires undisputed logs of who approved what.

- **Objectives (The Outcome):**

    1. **Centralized Intelligence:** Establish a single **Family Graph** that acts as the source of truth for relationships, roles, and permissions.

    2. **Omni-Modal Concierge:** Provide a seamless interface supporting Text, Voice (Bhashini), and Visual Inputs (Images).

    3. **Autonomous Orchestration:** Use a Supervisor-Worker model where specialized agents perform tasks but report to a central human-governed kernel.

    4. **Resilience & Trust:** Ensure operation during DPI downtimes (Graceful Degradation) and maintain a tamper-proof **Signed Log** of all critical family decisions.

- **Constraints:**

    - **India-First:** Must prioritize Bhashini (vernacular voice) and India Stack rails.

    - **Privacy-First:** Zero-Knowledge handles; raw passwords or non-consented data are never stored.

    - **Human Sovereignty:** Agents suggest; Humans decide. Autonomous module installation is strictly forbidden.

## 2. Personas & The Family Graph (The RBAC Model)

### Access Control Matrix (RBAC)

| **Role** | **Access Level** | **Description & Core Use Case** |
|---|---|---|
| **Admin (Head of House)** | Full System Control | Sole authority to Add/Remove members, activate/deactivate modules, and set global conflict logic. **Receives system-wide default notifications.** |
| **Member (Spouse/Adult)** | Co-Owner | Full visibility into shared Wealth/Health; can act as a Proxy for Managed Profiles. |
| **Minor (Child)** | Guarded Access | Access to Logistics (School/Play) and Education; Wealth/Vault data is strictly hidden. |
| **Elder (Parent)** | Assisted Access | Optimized for Bhashini voice commands; includes high-priority SOS and vitals tracking. |
| **Staff (Driver/Maid)** | Context-Limited | Access only to Attendance, P2P Payroll, and specific Home-Ops tasks. No visibility into Family Wealth. |
| **Managed Profile** | No Direct Login | (Pets, Infants, Seniors) Nodes tracked for data/reminders but managed by a Primary/Secondary Proxy. |
| **Passive Node** | Zero Interaction | Members who refuse or cannot use the app. Data is tracked for the Admin, but the OS never nudges/contacts them. |

## 3. Comprehensive User Scenarios

- **Scenario 1 (The "Puppy" Module Guidance):** The Admin mentions in passing to the Concierge, "We're planning to get a puppy soon." The Concierge mines this intent and responds: "I noticed you're getting a pet. I can activate the 'Pet Care' module..." Activation only occurs after Admin biometric confirmation.

- **Scenario 2 (Managed Profiles & Default Admin Notify):** Nani is a **Managed Profile**. The Admin assigns the Spouse as **Primary Proxy**. When Nani's medicine is due, the Spouse receives the nudge. **Crucially, the Admin is also notified by default**. If the Spouse marks it "Done," it disappears from the Admin's feed instantly to prevent double-dosing.

- **Scenario 3 (Vision-Based Health Context):** A user takes a **Photo** of the open pantry and asks, "What can I cook for Dad that fits his sugar-free diet?" The Core analyzes the image ingredients, checks Dad's ABHA health records via the HealthAgent, and suggests a compliant recipe. **(Disclaimer: Best Effort -- Informational Only -- No Medical Guarantee).**

- **Scenario 4 (Onboarding Staff & Payroll):** The Admin says, "Add Ramesh as our Driver." The Core creates a **Shadow Node**, sends a WhatsApp invite with restricted Staff permissions, and triggers the FinanceAgent to draft a P2P payroll intent for the 1st of the month.

- **Scenario 5 (The "Arjun" Role Transition):** Arjun's birth certificate in the Vault indicates he has turned 18. The Supervisor Agent notifies the Admin: "Arjun is now an Adult. Should I upgrade his access to the Wealth Pillar?"

- **Scenario 6 (Vision-Based Property Tax):** The Admin takes a photo of a physical tax notice and types, "Check if this is paid." The Core uses OCR via the VaultAgent, queries BBPS history via the FinanceAgent, and confirms the payment status.

- **Scenario 7 (The SOS Emergency State):** An elderly parent shouts, "Help, I fell" near a smart speaker. The Core enters **Global SOS State**. It halts all *new* background tasks and blocks *new* execution intents, but **Passive Reconciliation (Healer)** continues to run to ensure system consistency.

- **Scenario 8 (Graceful Degradation / DPI Downtime):** The FinanceAgent attempts to pay the electricity bill, but the BBPS network is down (504 Gateway Timeout). Instead of failing/crashing, the Core queues the transaction in the **Offline Retry Manager** and informs the Admin: "BBPS is unresponsive. I have queued the bill. I will retry in 1 hour."

- **Scenario 9 (Device & Surface Context):** A child asks the Kitchen Tablet (a "Public Surface"), "What is our bank balance?" The Core detects the hardware context and voice ID, blocking the response: "I can only display financial data to the Admin on a private device."

- **Scenario 10 (Consent Expiry Watchdog):** The Core's **Consent Lifecycle Manager** detects that the ABHA consent for "Apollo Hospital" expires in 3 days. It proactively prompts the Admin via the Concierge: "Health access for Apollo expires soon. Renew for 1 year?"

- **Scenario 11 (Compromised Dependency & Quarantine):** The HomeOpsAgent attempts to fetch prices from a 3rd-party ONDC seller. The Core detects an unsigned payload or unusual latency spike. It immediately quarantines the connection, blocks the data flow, and alerts the Admin of a "Security Block."

- **Scenario 12 (Crash Mid-Payment) [v2.2]:** Priya approves the BESCOM bill. BBPS confirms the payment, and the server crashes before the audit row is written. The session stays in EXECUTION with its resource lock held. Within five minutes the Healer polls BBPS, finds SUCCESS, writes the audit row through the audit write protocol, releases the lock and pushes "₹2,847 paid to BESCOM". No money is lost and no second payment is possible (Tech_Spec_Financial_Transaction_Safety §4.5, §6).

- **Scenario 13 (Two People Pay the Same Bill) [v2.2]:** Ravi and Priya both say "pay the BESCOM bill" within seconds. The first session acquires the family's lock for that biller; the second is told "A payment to this biller is already in progress" (FIN_009) and never reaches the approval prompt. Different billers proceed in parallel (FTS §9).

- **Scenario 14 (Consent Revoked Mid-Flow) [v2.2]:** Priya approves a payment, then revokes her bank consent on the bank's app before execution. CONSENT_REVERIFY runs live against the database and the DPI, fails, and the session ends without any money moving: "Your bank connection was cancelled externally. Please reconnect." If the BBPS call was already in flight, the payment stands, the revocation applies to future operations, and the Admin is notified (Tech_Spec_Consent_Manager §5, §8.3).

## 4. Functional Requirements (The Core Loop)

### 4.1. The Omni-Modal Concierge (Supervisor Engine) [M]

- **Architecture:** The Concierge is driven by a deterministic **Supervisor State Machine** to manage context, interruptions, and approval gates.

- **Reference Spec:** See *Tech_Spec_Supervisor_State_Machine_v2_1.md* for the FSM Logic, Persistence Layer, and Data Freshness Rules. The implementation-depth specs are mapped in §4.8 (v2.2).

- **Modalities:** Supports Text, Voice (ASR/TTS), Image+Text (Asynchronous), and UI-Action (Widget interactions).

- **Intent Mining:** Captures "Failed Intents" (unsupported requests). Data is stripped of PII and aggregated into an "Unmet Needs" heatmap.

- **Sovereign Command:** Acts as the central gateway for all instructions; no module can be added/deleted without a confirmed "Intent" from the User via the Concierge.

### 4.2. Automation & Approval Gates [M]

- **Tiers:** All actions are classified into Level 0 (Manual), Level 1 (Assisted), or Level 2 (Semi-Auto). Level 3 (Fully Autonomous) is forbidden in V1.

- **Reference Spec:** See *Tech_Spec_Supervisor_State_Machine_v2_1.md* for the Automation Matrix.

### 4.3. Family Management & "Shadow Nodes" [M]

- **Verification Tiers:** OTP-based verification for family; optional Aadhaar e-KYC for high-trust staff (Drivers/Nannies).

- **Shadow Profiles:** Creating a node before the user accepts the invite allows the Admin to pre-populate data.

- **Offboarding (The Kill-Switch):** Deleting a user or module triggers an immediate revocation of all associated Consent Handles (AA/ABHA) and purges all local data caches.

### 4.4. Managed Profile & Proxy Framework [M]

- **Proxy Logic:** Max 2 Proxies per Managed Profile.

- **Conflict Resolution:** Admin sets a "Default Logic" during setup:

    - **Hierarchy:** Primary Proxy's action overrides the Secondary.

    - **Notify & Block:** Conflicting instructions pause the action and alert both proxies + Admin.

- **Task Centralization:** A single "State" for the Managed Profile. If a task is "Done," it is "Done" for the whole system.

### 4.5. Module Registry & Orchestration [M]

- **Micro-Kernel Registry:** Modules register an Intent Manifest (keywords) and Capability Profile (APIs).

- **Sandboxing:** Modules are isolated. A "Logistics" module cannot see "Health" data unless the Supervisor Agent explicitly bridges the context.

- **Core vs. Service Modules:**

    - **Core (Immutable):** Concierge, Vault, Family Management, Finance (Base), Consent Manager.

    - **Service (Removable):** Pet Care, News, Brain Gym, Vacation Planner.

### 4.6. System Resilience & DPI Lifecycle [M]

- **Offline Queue Manager:** Stores failed non-critical tasks in local storage/Redis and retries when connectivity returns.

- **Circuit Breakers:** If a Module fails >5 times in 1 minute, the Core "Trips the Circuit" and disables the module temporarily. *(v2.2: this is the module-level breaker. The DPI-gateway breaker trips a provider after 3 consecutive failures — NFR §3, Runbook_DPI_Rate_Limits §8.2, Tech_Spec_Module_Registry §6.5.)*

- **Consent Lifecycle Manager:** Tracks consent_expiry dates for AA/ABHA. Triggers proactive renewal flows. Handles "Revocation Propagation". *(v2.2: specified in Tech_Spec_Consent_Manager — purpose registry §3, grant/withdraw §4, CONSENT_REVERIFY §5, watchdog §7, revocation propagation §8, webhook security §9.)*

### 4.7. The Audit Log (V1 Implementation) [M]

- **Mechanism:** Cryptographically Signed Append-Only Log (e.g., Hashed Rows in PostgreSQL or AWS QLDB).

- **Scope:** Logs all "Write" actions (Payments, Role Changes, Consent Grants).

- **Atomicity:** The Audit Log write must succeed and be confirmed **before** the system executes the user-facing confirmation (UI/Voice success message). If the Log write fails, the system enters the **FAILED** state, marks transaction as "Executed but Unconfirmed", and alerts Admin silently. *(v2.2: the full recovery protocol is Tech_Spec_Financial_Transaction_Safety — two-phase commit §4, Healer every 5 minutes §6, crash scenarios §4.5. The "Background Reconciliation" placeholder is closed.)*

- **Immutability:** Each log entry contains the hash of the previous entry to prevent tampering. *(v2.2: hash chain per family, computed in application code over canonical JSON, written through the audit write protocol — Data Model v1.3 §3.6, §3.18.)*

### 4.8. Specification Map [v2.2]

Every functional requirement above is implemented by a frozen or canonical specification. This table is the index; the specs are authoritative for detail.

| Requirement | Implementing specification |
|---|---|
| Family Graph, roles, proxies, cardinality (§2, §4.3, §4.4) | Data Model v1.3 §3.2–3.4, §4; role codes admin, member, minor, elder, staff, managed, passive |
| Supervisor state machine, automation tiers, TTL policy (§4.1, §4.2) | Tech_Spec_Supervisor_State_Machine v2.1 §1–4; session journal in Data Model v1.3 §3.7 |
| Module registry, sandboxing, Core vs Service modules (§4.5) | Tech_Spec_Module_Registry v1.1 (manifest §4, envelope §6, isolation §7, registration §8, errors §9) |
| Offline queue, circuit breakers, DPI resilience (§4.6, Scenario 8) | Data Model v1.3 §3.9; Runbook_DPI_Rate_Limits v1.2 (budgets §2, per-DPI breakers §8, degraded modes); Master Context §4.7 |
| Consent lifecycle, revocation, minors (§4.3 kill-switch, §4.6, Scenario 10, 14) | Tech_Spec_Consent_Manager v1.2; Data Model v1.3 §3.5, §3.12–3.13 |
| Payments, biometric gates, zombie recovery, refunds (§4.7, §5 item 4, Scenarios 8, 12, 13) | Tech_Spec_Financial_Transaction_Safety v1.2 (gates §2.2, two-phase commit §4, Healer §6, locks §9, FIN codes §10) |
| Audit log (§4.7) | Data Model v1.3 §3.6 (table, hash formula), §3.18 (write protocol), §6 (action taxonomy); typed payloads in Tech_Spec_Audit_Log_Implementation (P1) |
| Public surface rule (Scenario 9) | Data Model v1.3 §3.8 and view v_device_surfaces §3.17; Module Registry §6.2 |
| Performance budgets, encryption, retention, telemetry | NFR v2.2 |
| Vernacular voice, ASR confidence gate (§3.3 of Master PRD, §5 item 2) | Runbook_DPI_Rate_Limits §7; simulator stand-in in Tech_Spec_Simulator_Architecture (P1) |
| Threat model (Scenario 11 and webhook forgery) | Security_Threat_Model.md (P1, before any internet-facing deployment); interim controls in Consent Manager §9 |

## 5. Shared System Services (Common Utilities)

*To prevent redundant engineering, the Core provides these functional services to all modules.*

1. **Unified Notification Engine:** A central router that handles push, SMS, WhatsApp, and in-app alerts based on priority.

2. **Omni-Modal Translation Engine (Bhashini):** A wrapper that automatically translates vernacular voice/text input into English tokens for the Agents, and translates Agent output back into the user's native language.

3. **Document Parsing Engine (OCR):** A centralized AI vision utility that extracts structured data (Dates, Amounts, Names) from physical photos or PDFs.

4. **Payment Routing Engine:** A central utility that formats and stages UPI/BBPS intents. (Modules do not execute payments; they send the request to the Payment Engine, which asks the Admin for biometric approval).

5. **Identity & Auth Manager:** Centralized handler for Aadhaar, OTPs, and Biometric verification.

## 6. Conflict Resolution Matrix (Global Rules)

| **Conflict Scenario** | **Resolution Logic** |
|---|---|
| **Proxy Contradiction** | Follows Admin-set rule: Hierarchy (Primary wins) or Notify & Block (Pause & Alert). |
| **Agent Disagreement** | Supervisor defaults to "Conserve Resources" (e.g., Don't spend money). |
| **Modal Contradiction** | Visual Truth (Photo) overrides static Log Data. |
| **DPI Failure** | Queue task. Do not crash. Notify User only if urgent. |
| **Role Violation** | Any restricted role (Child/Staff) attempting to access sensitive pillars (Vault/Wealth) triggers a High-Severity Alert to Admin. |
| **Concurrent Intents** | One active EXECUTION state per **Resource** (e.g., specific Biller ID) per **family** *(v2.2: was "per user"; the frozen lock in Tech_Spec_Financial_Transaction_Safety §9.4 and Data Model v1.3 §3.11 is scoped to the family, so a spouse is blocked while the admin pays the same biller)*. A second request for the *same* resource is blocked; concurrent requests for *different* resources are allowed. |

## 7. Success Metrics (KPIs)

- **Autonomy Score:** % of tasks completed end-to-end without requiring manual Admin intervention.

- **Routing Accuracy:** % of intents sent to the correct Agent (Target: >95%).

- **Resilience Score:** % of DPI failures handled without App Crash (Target: 100%).

- **Inter-Agent Latency:** 95th percentile command routing under **1.5 seconds**. (Relaxed from 800ms to account for India network realities).

- **Family NPS:** Household satisfaction tracked via vernacular conversational feedback.

## 8. GTM Approach & Timeline

### Messaging & Positioning

- **Marketing Angle:** "Your Family's Chief of Staff." Move away from "Another App" to "The Last App You'll Ever Need to Manage Your Home."

- **Trust Anchor:** Heavily promote the "Tamper-Proof Audit Log" and "Zero-Knowledge Vault" to overcome skepticism about AI managing family wealth.

### Timeline & Phasing

- **Phase 1 (The Kernel):** Identity, Supervisor Routing, Omni-Modal Concierge, Signed Audit Log, and Consent Manager.

- **Phase 2 (The V1 Modules):** Integration of Wealth (AA/BBPS) and Health (ABHA).

- **Phase 3 (Expansion):** Third-party Module Registry and Advanced Spatial Reasoning.

*(v2.2: the project currently runs in portfolio-first mode — kernel plus vertical slices against DPI simulators, no licence applications. Dates and sequencing are in docs/strategy/Roadmap.md; this phasing remains the commercial shape.)*

## 9. Open Issues & Q&A

### Open Issues

- ~~**DPI Rate Limits:** Need to assess the strict rate limits of the Account Aggregator framework during peak hours.~~ *(Closed v2.2: Runbook_DPI_Rate_Limits v1.2 covers all five DPIs.)*

- **Resource-lock scope [v2.2]:** §6 now says per family. If a genuine per-user case appears (e.g. two adults with separate accounts at the same biller), the resource key must include the payer identity; decide in Finance module PRD review.

- **Hardware Partnerships:** To fully utilize "Surface Context," we need to evaluate partnerships with Smart Screen OEMs (e.g., Echo Show, Google Nest).

### Q&A

| **Asked By** | **Question** | **Answer** |
|---|---|---|
| **Engineering** | How do we handle video processing costs? | Live Mode is deferred to Phase 3. V1 uses Asynchronous Image Analysis (cheaper, robust). |
| **Legal/Compliance** | Is a signed DB log legally recognized? | Yes, under the IT Act (India), cryptographically signed digital logs are admissible and provide sufficient non-repudiation for V1. |

## 10. PRD Checklist

- [x] Title, Author, and Governance defined.

- [x] Narrative Executive Summary (The "Why") restored.

- [x] 11+ Comprehensive User Scenarios included (SOS, Degradation, Context).

- [x] Multi-modal (Voice, Text, Vision) logic defined.

- [x] Automation Tiers and State Machine logic defined (referenced).

- [x] System-Level Capabilities (Signed Log, Resilience, Consent) added.

- [x] Shared System Services section defined.

- [x] Success Metrics (adjusted), GTM, Phasing, and Q&A restored.

- [x] v2.2: Specification map (§4.8) and error scenarios 12–14 added.
