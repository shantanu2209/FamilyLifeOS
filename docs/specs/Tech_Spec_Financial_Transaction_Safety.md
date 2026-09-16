# Tech Spec: Financial Transaction Safety

_Payment execution protocol, two-phase commit, the Healer, zombie recovery, refunds, FIN error taxonomy_

> **Status:** FROZEN — v1.1 (Hardened; reviewer verdict: launch readiness verified) · **Author:** Alfred (Lead Product Architect) · **Last content change:** 2026-02-21
> **Canonical copy.** Converted to Markdown on 2026-09-16 from `Tech_Spec_Financial_Transaction_Safety_v1.1.docx` (original kept in `archive/originals/`). Content is unchanged; only formatting was converted. Superseded versions in the archive: `Tech_Spec_Financial_Transaction_Safety_v1.0.docx`.
> **Cited elsewhere as:** Tech_Spec_Financial_Transaction_Safety v1.1, Financial Safety spec, FTS §n.
> **Note:** Depends on: Data_Model_Schema v1.2.1 • Tech_Spec_Supervisor_FSM v2.1 (not in repository) • NFR v2.1 (not in repository).

## 0. Document Governance

| Version | Date | Description of Change | Author |
|---|---|---|---|
| v1.0 | 2026-02-21 | Initial release. Payment execution protocol; two-phase commit; idempotency key lifecycle; Healer algorithm (5-min cron, AUDIT_LOG_WRITE priority); zombie classification decision tree; refund policy; concurrent payment prevention (resource_lock); FIN_001–FIN_015 error taxonomy; manual escalation protocol. | Alfred |
| v1.1 | 2026-02-21 | Hardening patch (two independent reviewer rounds). Four changes: (1) §6.4 NOT_FOUND — explicit hard rule: Healer must reuse original idempotency_key, never generate new, with rationale. (2) §6.1 expanded — distributed lock promoted from Q&A to §6.1.1 (first-class algorithm); per-run processing cap added as §6.1.2; system-level circuit breaker added as §6.1.3. (3) §6.3 — AUDIT_LOG_WRITE exception block cross-references system circuit breaker at §6.1.3. (4) §11.3 — manual override now specifies SELECT FOR UPDATE on latest audit_log row + previous_hash recomputed inside same transaction to prevent hash chain corruption under concurrency. Reviewer 2: LAUNCH READINESS VERIFIED. | Alfred |

> 📋 STATUS: HARDENED v1.1 — Architecture Frozen
> This document specifies the complete financial transaction safety protocol for FamilyLifeOS v1.
> It is the authoritative definition of: the Healer cron algorithm, the two-phase commit protocol,
> zombie state recovery, refund policy, and the FIN error taxonomy.
> v1.1 hardening: Healer distributed lock, per-run cap, system circuit breaker promoted to §6.1;
> NOT_FOUND key reuse hard rule added to §6.4; manual override hash chain concurrency fixed in §11.3.
> Two independent reviewers: Reviewer 2 verdict — LAUNCH READINESS VERIFIED.
> Change-control: any modification to §4 (Two-Phase Commit) or §6 (Healer) requires a new version
> number, written migration plan, and review before implementation.

## Table of Contents

- **1. Scope & Design Principles** — What this spec covers • What it explicitly does not cover • 5 core principles
- **2. The Payment Execution Protocol** — Step-by-step: Pay BESCOM Bill • Happy path • Pre-execution gates • Post-execution
- **3. Failure Classification Taxonomy** — Retryable vs Terminal • Decision tree • Failure modes by FSM state
- **4. Two-Phase Commit Protocol** — Phase 1: payment execution • Phase 2: audit log + session update • Crash scenarios
- **5. Idempotency Key Lifecycle** — Generation • Persistence timing • Collision detection • TTL • BBPS idempotency behaviour
- **6. The Healer: Background Reconciliation Algorithm** — §6.1.1 Distributed lock • §6.1.2 Per-run cap (starvation prevention) • §6.1.3 System circuit breaker • P1 AUDIT_LOG_WRITE • P2 Zombies • Backoff schedule
- **7. Zombie State Classification & Recovery Decision Tree** — Zombie definition • Classification by elapsed time • Auto-resolve vs escalate thresholds
- **8. Refund Policy & Auto-Initiation Rules** — When auto-refund • When admin review • Refund tracking • BBPS refund limitations
- **9. Concurrent Payment Prevention** — Resource lock protocol • Conflict response • Lock TTL • Deadlock prevention
- **10. Financial Error Code Taxonomy** — FIN_001–FIN_015 • Retryable flag • User-facing message • Healer action
- **11. Manual Escalation Protocol** — Admin dashboard view • Admin actions • Escalation triggers • Resolution checklist
- **12. Q&A** — Engineering • Finance/Legal • Operations

## 1. Scope & Design Principles

### 1.1 What This Spec Covers

This document specifies the safety envelope for all financial transactions executed by FamilyLifeOS in v1. The primary DPI rail is BBPS (Bharat Bill Payment System) for bill payments, with UPI as the underlying payment instrument. The reference flow throughout this document is the canonical 'Pay BESCOM electricity bill' scenario — the first vertical slice planned for production.
This spec defines:
- The exact sequence of operations from biometric approval to success confirmation
- The two-phase commit protocol that makes payment + audit log atomic
- The idempotency key lifecycle (generation, persistence timing, collision handling, TTL)
- The Healer cron algorithm in full — replacing the placeholder in FSM v2.1 §1.4
- Zombie transaction classification and recovery decision thresholds
- Refund policy: when the system auto-alerts admin vs when Healer auto-resolves
- Concurrent payment prevention using the resource_lock mechanism from the Data Model
- The FIN_001–FIN_015 error taxonomy with retry classification and user messages

### 1.2 What This Spec Does Not Cover

- Consent token lifecycle — covered in Tech_Spec_Consent_Manager.md (P0, Week 2)
- AA data fetch safety — covered in Tech_Spec_Consent_Manager.md
- ONDC commerce order safety — architecture mirrors this spec; details deferred to ONDC module
- UPI VPA (Virtual Payment Address) management — implementation detail, not safety concern
- Merchant onboarding or biller registration on BBPS — infrastructure, not runtime safety
- Anti-fraud / AML (Anti-Money Laundering) — deferred to Security_Threat_Model.md

### 1.3 Design Principles

> ✅ DESIGN PRINCIPLE: Idempotency is non-negotiable. Every external API call carries a UUID_v4 idempotency key persisted to the database before the call is made. Re-execution of the same key is always safe.

> ✅ DESIGN PRINCIPLE: The audit log is part of the transaction, not a side effect. A payment is not 'done' until both the BBPS response and the audit log write succeed. The two-phase commit protocol enforces this.

> ✅ DESIGN PRINCIPLE: Human sovereignty above Level 2. No autonomous financial execution. Every bill payment above ₹100 requires explicit biometric approval. The Healer may reconcile, but cannot approve new payments.

> ✅ DESIGN PRINCIPLE: Prefer explicit failure over silent success. If the system cannot confirm an outcome, it surfaces this to the Admin immediately rather than assuming success or silently discarding the transaction.

> ✅ DESIGN PRINCIPLE: Solo-founder operational reality. This spec must work without a 24/7 on-call engineer. The Healer handles the 2am crash. Admin escalation is the final safety net. All automated recovery must be idempotent, logged, and auditable.

## 2. The Payment Execution Protocol

### 2.1 Reference Flow: Pay BESCOM Electricity Bill

The canonical flow. All other BBPS bill payments follow the identical protocol with different biller_id values. The automation tier for this flow is Level 1 (Agent prepares, User approves via biometric).

### 2.2 Pre-Execution Gates (Must Pass in Order)

The system must pass all five gates before entering EXECUTION state. Failure at any gate aborts cleanly — no external API has been called, no money has moved.

| Gate | Check | Failure Action | FSM State |
|---|---|---|---|
| G1  RBAC | User role permits finance module access. Staff/Child/Passive roles rejected. | FIN_AUTH_001: 403 Forbidden. Alert Admin. | INTENT_ANALYSIS |
| G2  Resource Lock | Acquire UNIQUE lock on (family_id, 'BBPS_' + biller_id). Prevents concurrent payment to same biller. | FIN_009: 409 Conflict. Inform user a payment is already in progress. | REASONING |
| G3  Balance Fetch | Force-fetch bank balance via AA (bypasses TTL). Block if fetch fails or balance < bill amount + ₹50 buffer. | FIN_006 (stale) or FIN_005 (insufficient). Release lock. | REASONING |
| G4  Biometric Auth | Admin/Spouse provides fingerprint or Face ID. Required for all BBPS payments (all amounts, per Product decision). | FIN_008: Auth failed. Release lock. User may retry. | AWAITING_APPROVAL |
| G5  CONSENT_REVERIFY | Re-check AA consent handle status in DB. Block if status != 'active'. Prevents TOCTOU race on consent revocation. | FIN_007: Consent expired. Route to consent renewal flow. Release lock. | CONSENT_REVERIFY |

### 2.3 The Happy Path (Step-by-Step)

After all 5 gates pass, the following sequence executes atomically where possible. Steps marked [DB] are database operations. Steps marked [EXT] are external API calls.

```sql
T+0   [DB]  Generate idempotency_key = UUID_v4()
      [DB]  UPDATE supervisor_sessions SET
                  session_status = 'EXECUTION',
                  idempotency_key = $key,
                  updated_at = NOW()
            WHERE session_id = $session_id
      -- POINT OF NO RETURN: session is now in EXECUTION.
      -- If server crashes after this line, Healer will reconcile.

T+1   [EXT] POST https://bbps.api/payment
            {
              'biller_id':        'BESCOM_KA_001',
              'amount_paise':     284700,          -- ₹2,847.00
              'upi_vpa':          'family@hdfcbank',
              'idempotency_key':  $key,
              'customer_params':  { 'account_no': '...' }
            }
      -- Timeout: 10 seconds. If no response → FIN_001 (Zombie recovery).

T+2a  [EXT SUCCESS] BBPS returns 200 + transaction_ref_id = 'BBPS-TXN-2847001'

T+2b  [DB]  BEGIN TRANSACTION  -- PHASE 2: atomic pair
      [DB]    INSERT INTO audit_log (
                family_id, user_id, action, details,
                previous_hash, current_hash, fsm_exit_state
              ) VALUES (
                $family_id, $user_id, 'BILL_PAYMENT_EXECUTED',
                '{"biller_id":"BESCOM_KA_001","amount_paise":284700,
                  "transaction_ref_id":"BBPS-TXN-2847001",
                  "idempotency_key":"$key","automation_tier":1}',
                $previous_hash, SHA256(...), 'SUCCESS'
              )
      [DB]    UPDATE supervisor_sessions SET
                  session_status = 'SUCCESS_CONFIRMATION',
                  updated_at = NOW()
              WHERE session_id = $session_id
      [DB]  COMMIT
      -- If COMMIT fails → AUDIT_LOG_WRITE queued (see §4.3). Session stays EXECUTION.

T+3   [DB]  DELETE FROM resource_lock
            WHERE family_id = $family_id AND resource_key = 'BBPS_BESCOM_KA_001'
      -- Release AFTER audit COMMIT. Never before.

T+4   [PUSH] Notify user: '✅ ₹2,847 paid to BESCOM. Ref: BBPS-TXN-2847001'
      [PUSH] Log WhatsApp/SMS confirmation if enabled in family preferences.
```

> 🔴 CRITICAL: Resource lock must be released AFTER Phase 2 COMMIT, never before. Releasing the lock before the audit log is written would allow a second concurrent payment attempt to start before the first is confirmed.

### 2.4 Sequence Diagram Summary

```text
User         App            FinanceAgent     BBPS API       Database
 |            |                  |               |              |
 |--'Pay'---->|                  |               |              |
 |            |--Intent--------->|               |              |
 |            |<-G1/G2/G3 check-|               |              |
 |            |--Show bill+amount|               |              |
 |<--Confirm--|                  |               |              |
 |--Biometric>|                  |               |              |
 |            |--G4/G5 pass----->|               |              |
 |            |                  |--Write key--->|              |
 |            |                  |               |<--[DB: key]--| T+0
 |            |                  |--POST payment>|              | T+1
 |            |                  |<--200+txn_ref-|              | T+2a
 |            |                  |               |--[Phase 2]-->| T+2b
 |            |                  |               |<--COMMIT-----|
 |            |                  |               |--[rel lock]->| T+3
 |<--✅ Push--|                  |               |              | T+4
```

## 3. Failure Classification Taxonomy

### 3.1 Two Axes of Classification

Every failure mode has two classification axes that determine the recovery path:
- Retryable vs Terminal: can we safely re-attempt the operation with the same idempotency key?
- Pre-execution vs Post-execution: did money leave the account before the failure?
Post-execution failures where money has moved are the most dangerous class. These require Healer reconciliation or Admin review — not silent discard.

### 3.2 Failure Mode Matrix

| Failure Mode | Phase | Retryable? | Money Moved? | Recovery Path | Error Code |
|---|---|---|---|---|---|
| BBPS timeout (>10s) | EXT call | Yes | Unknown | Healer: poll BBPS status | FIN_001 |
| BBPS 429 rate limit | EXT call | Yes (delayed) | No | Queue with backoff, notify user | FIN_002 |
| BBPS biller not found (404) | EXT call | No | No | FAILED state, notify user | FIN_003 |
| BBPS duplicate key ACK | EXT call | N/A | Already done | Return previous success result | FIN_004 |
| Insufficient balance | G3 gate | No (this session) | No | FAILED, notify user to top up | FIN_005 |
| AA fetch failed / stale balance | G3 gate | Yes | No | Retry AA fetch, block payment | FIN_006 |
| AA consent expired | G5 gate | After renew | No | Route to consent renewal flow | FIN_007 |
| Biometric auth failed | G4 gate | Yes (user retry) | No | Allow 3 attempts, then lock | FIN_008 |
| Resource lock conflict | G2 gate | After lock releases | No | 409 Conflict, inform user | FIN_009 |
| Audit log write failure (post-payment) | Phase 2 DB | Yes (Healer) | Yes | AUDIT_LOG_WRITE queued, Healer retries | FIN_010 |
| Zombie: session stuck in EXECUTION | Phase 2 | Via Healer poll | Unknown | Healer polls BBPS, classifies, resolves | FIN_011 |
| Debit confirmed, no BBPS success ACK | Phase 2 | No (admin review) | Yes | Admin alert, manual resolution | FIN_012 |
| Amount exceeds daily family limit | G1 gate | No | No | FAILED, notify Admin to review limit | FIN_013 |
| Session rehydration failed (Redis miss) | Server restart | Yes | No (pre-execution) | Rehydrate from PG journal, re-request biometric | FIN_014 |
| BBPS refund confirmed | Healer | N/A | Reversed | Log BILL_PAYMENT_REFUNDED, notify user | FIN_015 |

### 3.3 Failure Decision Tree

```text
FAILURE OCCURS
│
├── Was money debited? (check BBPS status or bank statement)
│   │
│   ├── NO → Is the error retryable?
│   │         ├── YES → Queue in offline_task_queue with exponential backoff
│   │         └── NO  → Mark session FAILED, release lock, notify user
│   │
│   └── YES (debit confirmed) →
│         ├── Is BBPS transaction_ref_id known?
│         │   ├── YES → Write audit log (Healer), mark SUCCESS_CONFIRMATION
│         │   └── NO  → FIN_012: Admin alert, manual review required
│         └── Did BBPS initiate refund?
│             ├── YES → Track refund_ref_id, poll for completion, log FIN_015
│             └── NO  → Admin alert + BBPS dispute escalation
│
└── Is the session a zombie? (EXECUTION state > 5 minutes)
    └── YES → Healer protocol (see §6)
```

## 4. Two-Phase Commit Protocol

### 4.1 Why Two Phases?

A financial system faces an inherent problem: the external API call (BBPS) and the database write (audit log) cannot be wrapped in a single atomic transaction — the database cannot hold a transaction open across an external HTTP call. The two-phase commit protocol is our solution: Phase 1 executes the payment; Phase 2 persists the evidence. The protocol guarantees that if Phase 2 fails, the Healer can always reconstruct Phase 2 from the idempotency key alone.

### 4.2 Phase 1: Payment Execution

```sql
-- Phase 1 is a DB transaction to set the 'point of no return' state

BEGIN TRANSACTION;
  -- Persist idempotency key BEFORE any external call (NFR v2.1 mandate)
  UPDATE supervisor_sessions
    SET session_status  = 'EXECUTION',
        idempotency_key = $idempotency_key,   -- UUID_v4, generated in INTENT_ANALYSIS
        updated_at      = NOW()
    WHERE session_id = $session_id
      AND session_status = 'CONSENT_REVERIFY'  -- guard: only advance from correct state
      AND family_id = $family_id;              -- row-level security

  -- Verify exactly one row was updated (race condition guard)
  -- If 0 rows: session was already advanced by another process → abort
COMMIT;

-- Only after DB COMMIT: execute external API call
bbps_response = POST_TO_BBPS(payload, idempotency_key=$idempotency_key)

-- Do NOT catch all exceptions here. Let Phase 2 handle based on response.
```

### 4.3 Phase 2: Audit Log + Session Update (Atomic Pair)

```sql
-- Phase 2: DB transaction that atomically writes audit log AND updates session
-- CRITICAL: Both writes happen in one transaction. If the DB crashes mid-Phase-2,
-- the COMMIT fails, the session stays in EXECUTION, and Healer reconciles.

IF bbps_response.status == 'SUCCESS':

  BEGIN TRANSACTION;
    INSERT INTO audit_log (
      log_id, family_id, user_id, action, details,
      previous_hash, current_hash, fsm_exit_state, timestamp
    ) VALUES (
      gen_random_uuid(), $family_id, $user_id,
      'BILL_PAYMENT_EXECUTED',
      -- canonical JSON (sorted keys, no spaces) — see Data Model §3.6
      '{"biller_id":"BESCOM_KA_001","amount_paise":284700,
        "transaction_ref_id":"BBPS-TXN-2847001",
        "idempotency_key":"$key","automation_tier":1,
        "bbps_ack_received_at":"2026-02-21T10:30:00Z"}',
      $previous_hash,
      SHA256(log_id || user_id || action || canonical_details || previous_hash),
      'SUCCESS',
      NOW()
    );

    UPDATE supervisor_sessions
      SET session_status = 'SUCCESS_CONFIRMATION',
          updated_at = NOW()
      WHERE session_id = $session_id;
  COMMIT;

  -- ONLY after COMMIT: release resource lock, notify user
  DELETE FROM resource_lock WHERE family_id=$family_id AND resource_key=$lock_key;
  push_notification(user_id=$user_id, message='✅ ₹2,847 paid to BESCOM')

ELIF bbps_response.status == 'FAILED':
  -- See §4.4 for BBPS FAILED path

ELIF exception (timeout, crash, network error):
  -- Session stays in EXECUTION. Healer picks up after 5 minutes.
  -- Do NOT release resource lock. Healer will release after reconciliation.
  -- Do NOT notify user. Healer will notify after resolution.
```

### 4.4 BBPS FAILED Response Path

```sql
IF bbps_response.status == 'FAILED':

  BEGIN TRANSACTION;
    -- Log the failure for audit trail
    INSERT INTO audit_log (..., action='BILL_PAYMENT_FAILED',
      details='{"reason":"BBPS_REJECTED","bbps_error_code":"' + code + '"}',
      fsm_exit_state='FAILED');

    UPDATE supervisor_sessions
      SET session_status = 'FAILED', updated_at = NOW()
      WHERE session_id = $session_id;

    -- Was money debited despite FAILED status? (some BBPS edge cases)
    -- If bbps_response.debit_confirmed == True: queue for admin review
    INSERT INTO offline_task_queue (task_type='BILL_PAYMENT', payload='{
      "reason":"BBPS_FAILED_AFTER_DEBIT",
      "idempotency_key":"$key",
      "biller_id":"BESCOM_KA_001",
      "amount_paise":284700
    }') WHERE $debit_confirmed == True;
  COMMIT;

  DELETE FROM resource_lock WHERE family_id=$family_id AND resource_key=$lock_key;
  push_notification(user_id=$user_id, message='❌ Payment failed. No money was deducted.')
  -- If debit_confirmed: message='⚠ Payment rejected. Your bank may have debited — we are investigating.'
```

### 4.5 Crash Scenarios & Guaranteed Recovery

| Crash Moment | System State After Restart | Recovery Action | User Impact |
|---|---|---|---|
| Server crashes before Phase 1 COMMIT | Session in previous state (AWAITING_APPROVAL). Idempotency key NOT written. | Session rehydrated from PG journal. User re-prompted for biometric. New idempotency key generated. | Minor: re-approve. No money moved. |
| Server crashes after Phase 1 COMMIT, before BBPS call | Session in EXECUTION. No BBPS call made. | Healer detects zombie after 5 min. BBPS status poll returns 'not found'. Session set to FAILED. Lock released. | Minor: ~5 min delay. No money moved. |
| Server crashes after BBPS SUCCESS, before Phase 2 COMMIT | Session in EXECUTION. Money moved. Audit log NOT written. | Healer detects zombie. BBPS poll confirms SUCCESS. Healer writes audit log (AUDIT_LOG_WRITE task). Session → SUCCESS_CONFIRMATION. | Minimal: user not immediately notified. Healer notifies within 5 min. |
| Phase 2 DB crash mid-transaction (COMMIT fails) | Session in EXECUTION. Audit log partially written (rolled back). | Identical to above — Healer reconciles from BBPS poll + idempotency key. | Minimal: same as above. |
| Server crashes after Phase 2 COMMIT, before lock release | Session SUCCESS_CONFIRMATION. Lock still held in resource_lock. | Healer detects stale lock (held > 30 min, session SUCCESS). Releases lock. | None: user was already notified via push before crash. |

## 5. Idempotency Key Lifecycle

### 5.1 Generation

One idempotency key is generated per supervisor_session at the start of the INTENT_ANALYSIS state — before any external API is called. Format: UUID_v4 (RFC 4122). No other format is acceptable. The key is generated in the application layer (Python uuid.uuid4()), never by the database.

```python
# Python — generated once per session, at INTENT_ANALYSIS entry
import uuid
idempotency_key = str(uuid.uuid4())
# Example: '550e8400-e29b-41d4-a716-446655440000'

# Persisted to supervisor_sessions.idempotency_key before any external call
# (NFR v2.1 §3 mandate: 'must be persisted to DB before external API call')
```

### 5.2 Persistence Timing (Critical)

The idempotency key MUST be written to supervisor_sessions as part of the Phase 1 COMMIT, which occurs before the BBPS API call. If the key is generated but not yet persisted, and the server crashes, the key is lost — and on restart, a new key will be generated. This is safe only before Phase 1. After Phase 1, the key must be durable.

> ⚠ WARNING: Never pass an idempotency_key to an external API before persisting it to the database. The BBPS API may process the payment successfully while the crash prevents the key from being saved, leaving no way to identify the duplicate on retry.

### 5.3 Collision Detection

```sql
-- Before generating a new key, check for any recent key for the same intent
-- This prevents two identical payments if user double-taps within a session

SELECT idempotency_key, session_status
FROM supervisor_sessions
WHERE family_id = $family_id
  AND intent_type = 'BILL_PAYMENT'
  AND intent_payload->>'biller_id' = $biller_id
  AND session_status NOT IN ('FAILED', 'ABORTED', 'SUCCESS_CONFIRMATION')
  AND created_at > NOW() - INTERVAL '24 hours';

-- If a row is found: return that session's status to the user.
-- Do NOT create a new session. Do NOT generate a new idempotency key.
```

### 5.4 TTL and Cleanup

- Idempotency keys are valid for 72 hours from creation (covers the 48h offline_task_queue expiry + buffer)
- After 72 hours: the supervisor_session record is archived (session_status = 'ABORTED' if not already terminal)
- The Healer's 48h failed_permanent cutoff for offline_task_queue is the effective operational boundary
- BBPS itself guarantees idempotency for 24 hours per key — our 72h window exceeds this, but Healer retries must always query BBPS status before re-submitting after 24h

### 5.5 BBPS Idempotency Behaviour

BBPS guarantees that submitting the same idempotency_key twice within 24 hours returns the original transaction result without re-executing. This means:
- FIN_004 (duplicate key ACK) is a success path, not an error. Extract transaction_ref_id from the duplicate ACK response and proceed with Phase 2 normally.
- After 24 hours: BBPS will treat a re-submitted key as a new transaction. The Healer must therefore query BBPS status endpoint by transaction_ref_id, not re-submit by idempotency_key, if >24h have elapsed.

## 6. The Healer: Background Reconciliation Algorithm

### 6.1 Overview

The Healer is a cron job that runs every 5 minutes (changed from 15-minute placeholder in FSM v2.1 §1.4 — tracker item resolved). It is the sole automated recovery mechanism for stuck transactions. It runs with SYSTEM_ACTOR_UUID identity and all its actions are written to the audit log.
The Healer operates a strict priority queue. AUDIT_LOG_WRITE tasks are always processed first — they represent confirmed payments without a paper trail, which is the highest-risk state. Bill payment zombies are processed second. All other queue types follow.

#### 6.1.1 Distributed Lock (Non-Overlapping Cron)

The Healer must acquire a global distributed lock before processing any tasks. This prevents two Healer instances from running simultaneously — which could occur during deployment restarts, cron mis-fires, or horizontal scaling.

```python
# At the START of every Healer run — before any task processing
healer_lock = redis.SET(
  key   = 'healer:global_lock',
  value = healer_instance_id,   # unique per cron invocation
  NX    = True,                 # only set if key does not exist (SETNX semantics)
  EX    = 600                   # TTL = 10 minutes (2x max expected run duration)
)

IF healer_lock is None:
  # Lock already held by another instance — skip this run entirely
  log.info('Healer skipped: lock held by another instance')
  exit(0)

# Lock acquired — proceed with task processing
# Lock is released at end of run, or expires automatically after 10 min
# Auto-expiry ensures a crashed Healer does not block the next run indefinitely
try:
  run_healer_priority_queue()
finally:
  redis.DELETE('healer:global_lock')  # explicit release if run completes normally
```

#### 6.1.2 Per-Run Processing Cap (Starvation Prevention)

Each Healer run processes a maximum number of tasks per priority tier. This prevents a large backlog of P1 tasks from consuming the entire run duration, starving zombie detection (P2) — which has real-time recovery implications.

| Priority | Max Tasks Per Run | Rationale |
|---|---|---|
| P1 — AUDIT_LOG_WRITE | 20 tasks | Each task involves 1 BBPS poll + 1 DB transaction. 20 × ~3s = 60s max. AUDIT_LOG_WRITE tasks retry every run so uncapped would block P2. |
| P2 — Zombie Sessions | 30 tasks | Each zombie involves 1 BBPS poll. 30 × ~2s = 60s max. Zombies are time-sensitive (blocking resource locks). |
| P3 — BILL_PAYMENT retries | 50 tasks | Re-submissions are fast (no BBPS poll, just queue). 50 tasks × ~0.5s = 25s max. |
| P4/P5 — LOW priority | 100 tasks combined | Data and notification tasks. Fast. No financial risk if deferred. |

Tasks not processed in the current run remain in 'pending' status and are picked up in the next run (5 minutes later). The cap is a safety valve, not a rate limit — most runs will process far fewer tasks than the cap.

#### 6.1.3 System-Level Circuit Breaker

Individual task failures are handled per-task (retry with backoff). But if the Healer's DB or BBPS connectivity is systemically broken, per-task escalation is insufficient — the Healer will spend the entire run retrying tasks that cannot succeed. The system circuit breaker detects this pattern and escalates at the Healer level.

```python
# System circuit breaker — evaluated once per Healer run, after processing

# Count consecutive BBPS call failures in this run
IF bbps_consecutive_failures >= 5:
  alert_admin(CRITICAL: 'Healer: BBPS unreachable in 5+ consecutive calls. Halting BBPS tasks.')
  # Skip remaining BBPS-dependent tasks for this run
  # Next run will retry — BBPS may have recovered

# Count consecutive DB write failures in this run
IF db_write_consecutive_failures >= 3:
  alert_admin(CRITICAL: 'Healer: DB writes failing. All financial tasks halted.')
  # This is existential — DB failure means audit log cannot be written.
  # Do NOT continue processing. Alert is urgent.
  exit(1)  # non-zero exit triggers PagerDuty / uptime monitor alert

# Count total Healer run failures across runs (persisted in Redis)
healer_global_failure_count = redis.INCR('healer:run_failures') IF this_run_had_any_failure
IF healer_global_failure_count >= 3:
  alert_admin(CRITICAL: 'Healer has failed in 3+ consecutive runs. Manual inspection required.')
  # Reset counter after alert so the next success resets the pattern
  redis.SET('healer:run_failures', 0) IF this_run_succeeded_fully
```

> ℹ INFO: The Healer may not make new payment decisions. It can only reconcile, log, notify, and escalate. It cannot approve a payment, generate a new idempotency key for a fresh transaction, or modify the approved_amount of a session.

### 6.2 Healer Priority Queue

| Priority | Task Type | Condition | Rationale |
|---|---|---|---|
| P1 — CRITICAL | AUDIT_LOG_WRITE | Payment succeeded (BBPS confirmed), audit log INSERT failed. Session in EXECUTION. | Money moved. No paper trail. Highest legal and trust risk. |
| P2 — HIGH | Zombie Sessions | supervisor_sessions WHERE status='EXECUTION' AND updated_at < NOW() - 5min | Money may have moved. Outcome unknown. Blocking resource lock. |
| P3 — MEDIUM | BILL_PAYMENT retries | offline_task_queue WHERE task_type='BILL_PAYMENT' AND status='pending' AND next_retry_at <= NOW() | Payment not yet executed. Money not moved. Retry is safe. |
| P4 — LOW | CONSENT_REFRESH | offline_task_queue WHERE task_type='CONSENT_REFRESH' | Data staleness. No financial risk. |
| P5 — LOW | NOTIFICATION | offline_task_queue WHERE task_type='NOTIFICATION' | User experience. No financial risk. |

### 6.3 P1: AUDIT_LOG_WRITE Recovery Algorithm

```sql
# Healer processes AUDIT_LOG_WRITE tasks FIRST, before all other work.

SELECT * FROM offline_task_queue
WHERE task_type = 'AUDIT_LOG_WRITE'
  AND status = 'pending'
  AND next_retry_at <= NOW()
ORDER BY created_at ASC;  -- oldest first: FIFO for audit chain integrity

FOR each task:
  payload = parse_json(task.payload)
  # payload contains: {
  #   'session_id', 'family_id', 'user_id',
  #   'action', 'details', 'previous_hash', 'amount_paise',
  #   'transaction_ref_id', 'idempotency_key'
  # }

  # 1. Verify the BBPS transaction is still confirmed (paranoia check)
  bbps_status = GET_BBPS_STATUS(transaction_ref_id=payload.transaction_ref_id)

  IF bbps_status == 'SUCCESS':
    # 2. Recompute hash using canonical payload
    current_hash = SHA256(log_id || user_id || action || canonical_details || previous_hash)

    # 3. Write audit log + update session in one atomic transaction
    BEGIN TRANSACTION;
      INSERT INTO audit_log (... all fields ...) VALUES (...)
      UPDATE supervisor_sessions SET session_status='SUCCESS_CONFIRMATION' WHERE session_id=$id
      UPDATE offline_task_queue SET status='succeeded' WHERE task_id=$task_id
    COMMIT;

    # 4. Release resource lock (may still be held)
    DELETE FROM resource_lock WHERE resource_key = payload.resource_key

    # 5. Notify user (may not have been notified yet)
    push_notification('✅ ₹' + amount + ' paid. Ref: ' + transaction_ref_id)

  ELIF bbps_status == 'FAILED':
    # BBPS subsequently failed — mark as FAILED. This is unusual but possible.
    log_audit(action='BILL_PAYMENT_HEALER_FAILED_CONFIRMATION', ...)
    UPDATE supervisor_sessions SET session_status='FAILED'
    UPDATE offline_task_queue SET status='succeeded'  # task resolved, outcome is FAILED
    push_notification('⚠ Payment outcome unclear. Admin has been notified.')
    alert_admin(FIN_012)

  ELIF exception:
    # DB or BBPS unreachable — back off and retry
    increment_retry(task, backoff_schedule)
    IF task.retry_count >= task.max_retries:
      UPDATE offline_task_queue SET status='failed_permanent'
      # TASK-LEVEL: individual task exhausted retries
      alert_admin(CRITICAL: 'Audit log unresolvable for session ' + session_id)
    # SYSTEM-LEVEL: if DB write_consecutive_failures >= 3, system circuit breaker fires
    # (see §6.1.3 — system circuit breaker halts all further processing this run)
```

### 6.4 P2: Zombie Session Recovery Algorithm

```sql
# Find all sessions stuck in EXECUTION for more than 5 minutes
SELECT s.*, r.resource_key
FROM supervisor_sessions s
LEFT JOIN resource_lock r ON r.session_id = s.session_id
WHERE s.session_status = 'EXECUTION'
  AND s.updated_at < NOW() - INTERVAL '5 minutes'
  AND s.family_id != SYSTEM_FAMILY_UUID  -- exclude system sessions
FOR UPDATE;  -- lock rows to prevent concurrent Healer instances

FOR each zombie_session:
  elapsed = NOW() - zombie_session.updated_at

  # Step 1: Query BBPS for authoritative status
  bbps_status = GET_BBPS_STATUS(
    idempotency_key   = zombie_session.idempotency_key,
    transaction_ref_id = zombie_session.bbps_transaction_ref_id  # may be null
  )

  # Step 2: Classify and act (see §7 decision tree)
  MATCH bbps_status:

    CASE 'SUCCESS':
      # Money moved, outcome known — write audit log
      queue_task(AUDIT_LOG_WRITE, priority=P1, payload={session details})
      # Task will be processed in next Healer run (P1 priority)

    CASE 'FAILED':
      # Money did not move (or was reversed by BBPS)
      log_audit(action='BILL_PAYMENT_ZOMBIE_FAILED', actor=SYSTEM_ACTOR_UUID)
      UPDATE supervisor_sessions SET session_status='FAILED'
      DELETE FROM resource_lock WHERE resource_key = zombie_session.resource_key
      push_notification('❌ Payment could not be completed. Please try again.')

    CASE 'PENDING':
      # BBPS still processing — classify by elapsed time
      IF elapsed < 30_min:
        # Normal BBPS processing delay — wait and re-check next run
        pass  # Healer will pick up again in 5 minutes
      ELIF 30_min <= elapsed < 4_hours:
        # Extended delay — alert Admin, keep waiting
        alert_admin(FIN_011, 'BBPS payment pending for ' + elapsed)
      ELIF elapsed >= 4_hours:
        # BBPS SLA exceeded — Admin must take manual action
        UPDATE supervisor_sessions SET session_status='FAILED',
          session_notes='Zombie: BBPS PENDING exceeded 4-hour SLA'
        alert_admin(CRITICAL: FIN_011, 'Manual resolution required')
        push_notification('⚠ Payment timed out. Admin has been notified.')

    CASE 'NOT_FOUND':
      # Key not found on BBPS — payment was never submitted (or BBPS status API is lagging).
      #
      # ⚠ HARD RULE: The Healer MUST reuse the original idempotency_key when re-queuing.
      # It must NEVER generate a new key. Generating a new key would turn a safe re-submission
      # into a fresh payment — bypassing biometric approval and potentially double-charging.
      # If BBPS later processes the 'lost' original request AND the re-submission,
      # the shared idempotency_key guarantees BBPS dedups them. A new key has no such safety.
      #
      IF elapsed < 24_hours:
        # Within BBPS idempotency window — safe to re-submit with original key.
        # BBPS will dedup if the original request was received but status API was lagging.
        queue_task(BILL_PAYMENT, priority=P3, payload={
          resubmit=True,
          idempotency_key=zombie_session.idempotency_key,  # MUST be original key
          session_id=zombie_session.session_id,
          biller_id=..., amount_paise=...
        })
      ELSE:
        # Beyond 24h BBPS idempotency window — re-submission is unsafe.
        # BBPS will treat the original key as a NEW transaction (double payment risk).
        # Mark FAILED; user must retry fresh (which generates a new key with fresh biometric).
        UPDATE supervisor_sessions SET session_status='FAILED'
        push_notification('Payment expired. Please retry from the app.')

    CASE exception (BBPS unreachable):
      # Cannot determine status — increment zombie counter, alert if persistent
      IF zombie_session.healer_poll_count >= 3:
        alert_admin(FIN_011, 'BBPS unreachable for 15+ minutes. Manual check required.')
```

### 6.5 Healer Backoff Schedule

| Attempt | Wait Before Retry | Cumulative Elapsed | Notes |
|---|---|---|---|
| 1st retry | 5 min (next Healer run) | 5 min | Standard Healer interval |
| 2nd retry | 10 min | 15 min | Exponential start |
| 3rd retry | 20 min | 35 min | Admin alert fired if BBPS PENDING |
| 4th retry | 40 min | 75 min |  |
| 5th retry (max) | 80 min | ~2.5 hours | If still unresolved: failed_permanent, Admin critical alert |
| failed_permanent | — | 48 hours max | offline_task_queue expiry. Admin must manually resolve. |

> ⚠ WARNING: AUDIT_LOG_WRITE tasks do not follow the standard backoff schedule. They retry on every Healer run (every 5 min) up to max_retries=10, because they represent confirmed payments without a paper trail. If they hit max_retries, the alert is CRITICAL — not just HIGH.

## 7. Zombie State Classification & Recovery Decision Tree

### 7.1 Zombie Definition

A zombie transaction is any supervisor_session with session_status = 'EXECUTION' whose updated_at timestamp is more than 5 minutes in the past. The 5-minute threshold is derived from: BBPS typical response time (<3 seconds) + network jitter budget (60 seconds) + Healer detection latency (5-minute cron interval) = practical detection point.

> 🔴 CRITICAL: A zombie does not necessarily mean money was lost. It means the system does not yet know the outcome. The Healer's job is to query BBPS and convert the zombie to a known outcome (SUCCESS or FAILED). Admin intervention is only required when the Healer cannot determine the outcome after exhausting retries.

### 7.2 Zombie Classification by Elapsed Time

| Elapsed Time | Classification | BBPS Status Expected | Healer Action | Admin Notified? |
|---|---|---|---|---|
| 5–30 min | Fresh zombie | BBPS PENDING or SUCCESS | Poll BBPS. Act on response. Wait if PENDING. | No |
| 30 min–4 hours | Extended zombie | BBPS PENDING or FAILED | Poll BBPS. Alert Admin. Continue polling every 5 min. | Yes — High priority |
| >4 hours | Critical zombie | BBPS timeout / FAILED | Mark FAILED. Critical Admin alert. Stop polling. | Yes — Critical alert |
| >48 hours | Expired zombie | BBPS records expired | failed_permanent in queue. Manual reconciliation required. | Yes — Emergency escalation |

### 7.3 Full Decision Tree

```text
Is session_status = 'EXECUTION' AND updated_at < NOW() - 5 min?
│
└── YES (zombie detected)
    │
    ├── Query BBPS status
    │   │
    │   ├── SUCCESS → Queue AUDIT_LOG_WRITE (P1). Healer resolves next run.
    │   │
    │   ├── FAILED → Mark session FAILED. Release lock. Notify user.
    │   │           Log BILL_PAYMENT_ZOMBIE_FAILED in audit.
    │   │
    │   ├── PENDING →
    │   │   ├── elapsed < 30 min  → Wait. Healer re-checks in 5 min.
    │   │   ├── elapsed 30–240 min → Alert Admin (High). Keep polling.
    │   │   └── elapsed > 240 min  → Mark FAILED. Alert Admin (Critical).
    │   │
    │   ├── NOT_FOUND →
    │   │   ├── elapsed < 24 hours → Re-queue payment (same idempotency_key).
    │   │   └── elapsed > 24 hours → Mark FAILED. Notify user to retry fresh.
    │   │
    │   └── EXCEPTION (BBPS unreachable) →
    │       ├── poll_count < 3 → Wait. Try again next run.
    │       └── poll_count >= 3 → Alert Admin. BBPS outage suspected.
    │
    └── Resource lock status
        ├── Lock held, session FAILED → Release lock now.
        └── Lock held, session SUCCESS_CONFIRMATION → Release lock now (stale).
```

## 8. Refund Policy & Auto-Initiation Rules

### 8.1 The Core Refund Question

When money leaves a user's account but BBPS cannot confirm successful bill payment, two outcomes are possible: BBPS initiates a refund automatically (the common case for their internal failures), or the money is in a disputed state requiring manual intervention. FamilyLifeOS does not directly initiate UPI refunds — that is handled by the UPI PSP (Payment Service Provider, typically the user's bank). FamilyLifeOS tracks refund status and surfaces it to Admin.

### 8.2 Refund Decision Matrix

| Scenario | BBPS Response | Refund Initiator | FamilyLifeOS Action | Timeline |
|---|---|---|---|---|
| Payment succeeded, bill paid | 200 SUCCESS + txn_ref | N/A | Log success. No refund. | Immediate |
| BBPS rejects, debit not made | 4xx FAILED (pre-debit) | N/A | Mark FAILED. Inform user. | Immediate |
| BBPS error after debit | 5xx after debit confirmed | BBPS auto-refund (T+1–3 days) | Log FIN_012. Track refund_ref_id. Notify user to expect refund. | 3–5 business days |
| Zombie: BBPS PENDING > 4h | PENDING (no resolution) | Admin initiates via BBPS dispute | Alert Admin. Provide session details + idempotency key. | Admin action required |
| BBPS SUCCESS, audit log failed | 200 SUCCESS (confirmed) | N/A — payment succeeded | Healer writes audit log (P1). No refund needed. | 5–10 min (Healer) |
| Bank debit + BBPS NOT_FOUND | NOT_FOUND | BBPS/Bank (varies) | Alert Admin with FIN_012. Provide transaction details for dispute. | Admin + Bank dispute |

### 8.3 Refund Tracking in the System

```sql
-- When BBPS initiates a refund, log it as a separate audit event
-- The Healer polls for refund completion and logs the final status

-- Audit log entry for refund initiated:
INSERT INTO audit_log (
  action = 'BILL_PAYMENT_REFUND_INITIATED',
  details = '{
    "original_transaction_ref_id": "BBPS-TXN-2847001",
    "refund_ref_id": "BBPS-REF-9012345",
    "amount_paise": 284700,
    "expected_credit_date": "2026-02-24",
    "initiated_by": "BBPS_AUTO"
  }',
  fsm_exit_state = 'FAILED'  -- the original payment failed
)

-- Audit log entry when refund completes:
INSERT INTO audit_log (
  action = 'BILL_PAYMENT_REFUND_COMPLETED',
  details = '{
    "refund_ref_id": "BBPS-REF-9012345",
    "credited_at": "2026-02-24T14:22:00Z"
  }',
  fsm_exit_state = 'SUCCESS'  -- the refund itself succeeded
)
```

> ⚠ WARNING: FamilyLifeOS tracks refunds but does not initiate them. Refund initiation is the responsibility of the UPI PSP. Admin's role is to provide the user with correct reference numbers and escalation paths for the dispute.

## 9. Concurrent Payment Prevention

### 9.1 The Problem

Two admins (or one admin with two open app sessions) could attempt to pay the same BESCOM bill simultaneously. Without a lock, both payments could succeed — doubling the bill payment and depleting the bank balance. The resource_lock table (Data Model §3.7) is the mechanism that prevents this.

### 9.2 Resource Lock Protocol for Payments

```sql
-- The resource_key format for BBPS payments: 'BBPS_' + biller_id
-- Example: 'BBPS_BESCOM_KA_001'

-- Gate G2: Acquire lock (UPSERT-based, relies on unique partial index)
-- Data Model §3.7: UNIQUE (family_id, resource_key) WHERE released_at IS NULL

INSERT INTO resource_lock (
  family_id, resource_key, session_id, acquired_by, acquired_at
) VALUES (
  $family_id, 'BBPS_BESCOM_KA_001', $session_id, $user_id, NOW()
)
ON CONFLICT (family_id, resource_key) WHERE released_at IS NULL
DO NOTHING;  -- returns 0 rows if conflict

-- Check if insert succeeded (0 rows = lock held by another session)
IF rows_affected == 0:
  -- Lock held: inform user
  RAISE FIN_009  -- 409 Conflict
  -- Include in error: which admin holds the lock, session started at
```

### 9.3 Lock TTL and Stale Lock Detection

- Active resource locks older than 30 minutes are considered stale (normal payment takes <30 seconds)
- Healer checks for stale locks on every run: SELECT * FROM resource_lock WHERE acquired_at < NOW() - INTERVAL '30 min' AND released_at IS NULL
- If the associated session is in SUCCESS_CONFIRMATION, FAILED, or ABORTED: release the stale lock immediately
- If the associated session is in EXECUTION: this is a zombie — process via §6.4 zombie recovery before releasing
- Alert Admin if stale lock detected, regardless of resolution outcome

### 9.4 What Is and Is Not Locked

| Scenario | Lock Key | Allowed? |
|---|---|---|
| Admin A paying BESCOM while Admin B paying BESCOM | 'BBPS_BESCOM_KA_001' | ❌ Blocked — same resource key. Admin B gets FIN_009. |
| Admin A paying BESCOM while Admin B paying Airtel | 'BBPS_BESCOM_KA_001' and 'BBPS_AIRTEL_001' | ✅ Allowed — different resource keys. Both can proceed concurrently. |
| Admin A paying BESCOM while Spouse paying BESCOM | 'BBPS_BESCOM_KA_001' | ❌ Blocked — same family, same biller. Spouse gets FIN_009. |
| Family A paying BESCOM while Family B paying BESCOM | 'BBPS_BESCOM_KA_001' per family_id | ✅ Allowed — resource_lock is scoped to family_id. Different families are isolated. |

## 10. Financial Error Code Taxonomy

### 10.1 FIN Error Codes

All financial errors use the FIN_ prefix. The code is included in the audit log details, surfaced to the Admin dashboard, and (in user-friendly form) shown to the user. Raw error codes are never shown to end users.

| Code | Name | Retryable? | Money Moved? | User Message (English) | Healer Action |
|---|---|---|---|---|---|
| FIN_001 | BBPS timeout | Yes | Unknown | Payment is taking longer than usual. We're checking the status. | Zombie recovery §6.4 |
| FIN_002 | BBPS rate limit (429) | Yes (delayed) | No | Too many requests. Your payment will be retried in a few minutes. | Queue with backoff §6.5 |
| FIN_003 | Biller not found (404) | No | No | This bill couldn't be found. Please check your account number. | None — terminal |
| FIN_004 | Duplicate key ACK | N/A | Done | Payment already processed. ✅ | Write audit log if not written |
| FIN_005 | Insufficient balance | No (this session) | No | Your bank balance is too low for this payment. | None — terminal |
| FIN_006 | Stale balance / AA fetch failed | Yes | No | Couldn't verify your balance. Payment paused for safety. | Queue CONSENT_REFRESH |
| FIN_007 | AA consent expired | After renewal | No | Your bank connection needs renewal. Tap here to reconnect. | Route to consent renewal |
| FIN_008 | Biometric auth failed | Yes (user retry) | No | Fingerprint not recognised. Please try again. | None — user retries |
| FIN_009 | Resource lock conflict | After lock releases | No | A payment to this biller is already in progress. | Stale lock check §9.3 |
| FIN_010 | Audit log write failure | Yes (Healer) | Yes | Payment sent. Finalising records. You'll be notified shortly. | AUDIT_LOG_WRITE P1 §6.3 |
| FIN_011 | Zombie transaction | Via Healer | Unknown | Your payment is being verified. We'll update you shortly. | Zombie recovery §6.4 |
| FIN_012 | Debit confirmed, no ACK | No (admin review) | Yes | Payment status unclear. Admin has been notified. No further action needed. | Admin alert + BBPS dispute |
| FIN_013 | Daily limit exceeded | No | No | This payment exceeds your daily limit. Ask your family admin to review. | None — terminal |
| FIN_014 | Session rehydration failed | Yes | No | Session expired. Please approve the payment again. | Rehydrate from PG journal |
| FIN_015 | Refund confirmed | N/A | Reversed | Your refund of ₹X has been credited. ✅ | Log BILL_PAYMENT_REFUND_COMPLETED |

### 10.2 Hindi User Messages (Key Errors)

High-frequency errors must have verified Hindi translations. These are the top 4 by expected occurrence:

| Code | Hindi Message |
|---|---|
| FIN_001 | भुगतान में सामान्य से अधिक समय लग रहा है। हम स्थिति जांच रहे हैं। |
| FIN_005 | आपके बैंक खाते में पर्याप्त शेष राशि नहीं है। |
| FIN_007 | आपका बैंक कनेक्शन नवीनीकरण के लिए आवश्यक है। पुनः जोड़ने के लिए यहाँ दबाएं। |
| FIN_009 | इस बिलर को भुगतान पहले से प्रगति में है। |

All other Hindi translations to be completed as part of UX_Error_Message_Library.md (P1, Week 3).

## 11. Manual Escalation Protocol

### 11.1 When Admin Intervention Is Required

Most failure scenarios are handled automatically by the Healer. Admin intervention is reserved for cases where the automated system cannot determine the ground truth — typically because BBPS is unreachable for an extended period, or the debit/credit state is genuinely ambiguous.

| Trigger | Alert Level | Information Provided to Admin | Admin Actions Available |
|---|---|---|---|
| FIN_012: Debit confirmed, no BBPS ACK | 🔴 Critical | session_id, idempotency_key, transaction_ref_id (if known), amount, biller, timestamp, bank statement screenshot link | 1. Submit BBPS dispute with provided refs<br>2. Contact bank for UPI dispute<br>3. Mark as 'Manually Resolved'<br>4. Override session status |
| FIN_011: Zombie > 4 hours | 🔴 Critical | session_id, elapsed time, BBPS poll count, last BBPS response, idempotency_key | 1. Manually query BBPS portal<br>2. Mark session as FAILED or SUCCESS<br>3. Trigger Healer reconciliation |
| AUDIT_LOG_WRITE: failed_permanent (10 retries) | 🔴 Critical | session_id, payment details, BBPS confirmation, Healer retry log | 1. Manually insert audit log entry<br>2. Run hash chain verification after<br>3. Confirm chain integrity to Admin |
| Stale resource lock > 30 min | 🟠 High | lock details, session status, acquiring user | 1. If session terminal: release lock<br>2. If zombie: trigger manual Healer run |
| Healer: BBPS unreachable > 15 min (3 polls) | 🟠 High | BBPS endpoint status, affected session count | 1. Check BBPS status page<br>2. Decide whether to hold or abort affected sessions |

### 11.2 Admin Dashboard: Financial Safety View

The Admin must have a dedicated Financial Safety section in the dashboard showing:
- Active resource locks: family, biller, acquired_by, elapsed time
- Sessions in EXECUTION > 5 min: session_id, amount, biller, elapsed, Healer poll count
- Pending AUDIT_LOG_WRITE tasks: count, oldest task age
- failed_permanent queue items: list with details and resolution actions
- FIN_012 incidents: list with BBPS dispute filing status
- 24-hour transaction summary: total amount processed, success rate, failure breakdown by code

### 11.3 Manual Override: Session Status

```sql
-- Admin manual override — only available to ADMIN role via secure dashboard endpoint
-- Requires: fresh biometric auth + reason text (min 20 chars)
-- Triggers: mandatory audit log entry before status change

POST /api/v1/admin/sessions/{session_id}/override
{
  'new_status':        'FAILED' | 'SUCCESS_CONFIRMATION',  -- only two valid overrides
  'reason':            'BBPS dispute filed. Ref DISP-2026-001. Refund expected T+3.',
  'biometric_token':   '<fresh biometric proof>',
  'admin_user_id':     '$admin_user_id'
}

-- Server-side implementation (MUST follow this exact order):

BEGIN TRANSACTION;

  -- Step 1: Lock the latest audit_log row for this family.
  -- This prevents the Healer from concurrently writing a new audit entry
  -- between our previous_hash fetch and our INSERT, which would corrupt
  -- the hash chain (our entry would reference a stale previous_hash).
  SELECT log_id, current_hash
  FROM audit_log
  WHERE family_id = $family_id
  ORDER BY timestamp DESC
  LIMIT 1
  FOR UPDATE;  -- row-level lock: Healer must wait until this transaction commits

  -- Step 2: Use the locked row's current_hash as our previous_hash.
  -- Recompute inside the transaction — never use a value fetched before BEGIN.
  previous_hash = locked_row.current_hash
  new_log_id    = gen_random_uuid()
  current_hash  = SHA256(new_log_id || admin_user_id || 'ADMIN_SESSION_OVERRIDE'
                         || canonical_details || previous_hash)

  -- Step 3: Write audit log entry (BEFORE session status change)
  INSERT INTO audit_log (
    log_id, family_id, user_id, action, details,
    previous_hash, current_hash, fsm_exit_state, timestamp
  ) VALUES (
    new_log_id, $family_id, $admin_user_id,
    'ADMIN_SESSION_OVERRIDE',
    '{"session_id":"$session_id","new_status":"$new_status",
      "reason":"$reason","biometric_verified":true}',
    previous_hash, current_hash, $new_status, NOW()
  );

  -- Step 4: Change session status (AFTER audit log write, inside same transaction)
  UPDATE supervisor_sessions
    SET session_status = $new_status, updated_at = NOW()
    WHERE session_id = $session_id;

  -- Step 5: Release resource lock if held
  DELETE FROM resource_lock WHERE session_id = $session_id;

COMMIT;

-- Step 6: Alert all family Admins (outside transaction — notification is non-atomic)
notify_all_admins(family_id=$family_id,
  message='Session override by ' + admin_name + ': ' + reason)
```

> ⚠ WARNING: The SELECT FOR UPDATE on the latest audit_log row is what makes the hash chain safe under concurrency. Without it, a simultaneous Healer write could insert between our fetch and our INSERT, causing our entry to reference a now-stale previous_hash. The FOR UPDATE lock forces the Healer to wait until this transaction commits.

## 12. Q&A

| Asked By | Question | Answer |
|---|---|---|
| Engineering | Why is Phase 2 a DB transaction instead of two separate writes? | Because the audit log and the session status update must be atomic. If we write the audit log and then the server crashes before updating the session, the session stays in EXECUTION and the Healer will try to write the audit log again — creating a duplicate entry. Wrapping both in one COMMIT prevents this. |
| Engineering | What prevents two Healer instances from processing the same zombie simultaneously? | The zombie query uses FOR UPDATE (row-level lock). The second Healer instance will wait at the lock, then see the session is no longer in EXECUTION (first instance already resolved it), and skip it. This is safe because the Healer is idempotent — the same action twice produces the same result. |
| Engineering | Can the Healer ever trigger a new payment? | No. The Healer can re-submit a payment with the same idempotency_key within BBPS's 24-hour window (if the original submission was never received by BBPS). It cannot approve a new payment, change the amount, or generate a new idempotency key. Any new payment requires fresh biometric approval from the user. |
| Finance/Legal | If a payment succeeds but the audit log is temporarily missing (FIN_010), is there a gap in the legal record? | No. The payment is logged as AUDIT_LOG_WRITE in the offline_task_queue with full payload. The Healer resolves this within 5–40 minutes. The audit log entry is written with the original timestamp of the BBPS response, not the Healer write time. The hash chain is reconstructed correctly. There is a brief gap in the chain but it is always filled within the queue's 48-hour expiry. |
| Finance/Legal | Who is liable if BBPS confirms payment but the user claims they never paid? | The audit log hash chain (with BBPS transaction_ref_id) is the non-repudiation record. Under the IT Act (India), cryptographically-signed digital logs are admissible. The BBPS transaction_ref_id can be verified against NPCI's records independently. FamilyLifeOS is not a payment processor — it is a front-end to BBPS. Liability resolution is between the user's bank (UPI PSP) and BBPS. |
| Operations | The Healer runs every 5 min. What if a Healer run takes longer than 5 minutes? | The Healer must be implemented as a non-overlapping cron: the next run starts only after the previous one completes. Implementation: use a distributed lock (Redis SETNX with 10-minute TTL) at the start of each Healer run. If the lock is held, skip this run. Alert if Healer runs consistently take >3 minutes (approaching the 5-minute interval). |
| Operations | What if the Healer itself crashes mid-run? | Healer operations are idempotent. All DB writes are in transactions. If the Healer crashes mid-run, the next run will re-process the same tasks (they are still in 'pending' status). The FOR UPDATE lock will have been released by the crash. No double-execution occurs because BBPS idempotency keys and DB-level status checks prevent it. |

— End of Tech_Spec_Financial_Transaction_Safety_v1.1 —
