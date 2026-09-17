# PRD: Financial Command Center (module `finance`)

> **Status:** DRAFT v0.2 — founder rulings of 2026-09-17 applied, settled open issues closed; independent review (Codex, WP-15) pending · **Author:** Shantanu Chaudhary (Lead Product Architect), drafted with Claude Code · **Last content change:** 2026-09-17
> **Scope:** Phase 1, portfolio-first build against DPI simulators. Module-level PRD that Tech_Spec_Module_Registry §1.2 defers to. Owns vertical slice 1, "Priya pays the BESCOM electricity bill".
> **Depends on:** FTS v1.2 §2 (gates G1–G5), §4 (two-phase commit), §5 (idempotency key lifecycle), §6–§7 (Healer, zombie classification), §9 (resource lock), §10 (FIN codes), §11 (escalation) · MR v1.1 §3 (tiers, call graph), §4 (manifest schema), §6 (envelope; §6.4 ledger), §7 (isolation), §9 (MOD codes), §10 (worked PAY_BILL) · CM v1.3 §3.2 (AA_BALANCE_FETCH), §4.2 (grant flow), §5 (CONSENT_REVERIFY), §6.1 (AA adapter) · DM v1.3 §3.4, §3.7–§3.9, §8 (Sharma seed), §9.3 (module table convention) plus the DM v1.3 decisions (lowercase Core-PRD roles, separate `resource_lock` table, kernel schema `core`) · RB v1.2 §2–§4, §8, §9 · FSM v2.1 §2 (tiers), §3.1 (TTL) · Core PRD v2.2 §2, §5, §6 · Tech_Spec_Simulator_Architecture v0.1 §4, §5.1–5.2, §6.1–6.2 (BBPS and AA simulators) · PROJECT_TRACKER Decision Log (2026-09-17) and Phase 1 Build Gate.

Status: In-Progress
Author: Shantanu Chaudhary (Lead Product Architect)
Primary Agent: FinanceAgent (`modules.finance.agent:FinanceAgent`)
Engineering Lead: Shantanu Chaudhary (solo founder; Codex implements against the frozen specs)
Design Lead: Shantanu Chaudhary
Approvers: Shantanu Chaudhary, after one independent review round by a different agent

## 0. Document Governance

| Version | Date | Description of Change | Author |
|---|---|---|---|
| v0.1 | 2026-09-17 | Initial draft for the Phase 1 portfolio build. | Shantanu Chaudhary (with Claude Code) |
| v0.2 | 2026-09-17 | (1) Open issues settled by the spec close-out are closed: session stays in EXECUTION after `MOD_EXECUTION_UNCONFIRMED` (MR v1.1 §9), cleanup never aborts EXECUTION sessions (DM v1.3 §7.4), action code `BILL_PAYMENT_EXECUTED`. (2) Founder rulings: `CHECK_BALANCE` denied for `elder`; no admin override of a blocked balance check. (3) The resource lock is released by UPDATE, never DELETE (DM v1.3 §3.11). (4) New §4.6 "Settings and defaults": a family may make payment safety stricter, never looser. (5) Scenarios and stubs aligned with the simulator spec: deterministic scenario billers instead of chaos for the zombie scenario, `/bill/fetch`, `/payment/status`, transaction reference derived from the key. | Shantanu Chaudhary (with Claude Code) |

## 1. The One-Pager (Executive Summary)

- **Overview:** FinanceAgent is the Core-tier worker module that owns BBPS bill payment and Account Aggregator balance visibility for a family. In Phase 1 it exists to prove the kernel: one intent, `PAY_BILL`, run end-to-end through every gate, the two-phase commit, the idempotency ledger and the Healer. It is the first module through the Module Registry because it exercises invariants 15–20 and 30–34 of AGENTS.md §4, and it is the subject of the only Playwright test the Build Gate requires.
- **The Problem (The Friction):** The BESCOM bill is due on the 25th. One spouse pays it from PhonePe, the other from the bank app; the second payment sits in "pending" for two days and nobody knows whether money left. There is no shared record of who approved what, and no household-level view of what is due this week. Master Context §1.1 lists "Bills slip through cracks" as a headline pain point.
- **Objectives (The Outcome):**
    1. Pay a linked BBPS bill from a text or voice request with exactly one passkey approval, in under 30 s of simulator time (MR §6.5 hard timeout).
    2. Never double-pay: one idempotency key per session (FTS §5), a family-scoped resource lock per biller (FTS §9), and a module ledger that returns the stored envelope on any re-dispatch (MR §6.4).
    3. Never lose track of money: a session stuck in EXECUTION becomes a known outcome within two Healer runs (FTS §6–§7); every payment lands in the hash-chained audit log.
    4. Prove it: Crash Scenarios A–D and the "Priya pays BESCOM bill" E2E test pass against WireMock (PROJECT_TRACKER, Phase 1 Build Gate).
- **Constraints:** Portfolio mode — no FIU/BBPOU licences, no real money, WireMock only (Decision Log 2026-09-17); UPI VPA management, biller onboarding and AML are out of FTS scope (§1.2). Solo founder — no on-call; the Healer plus admin escalation is the safety net (FTS §1.3). Level 3 is forbidden; every BBPS payment needs a passkey regardless of amount (FTS §2.2 G4). Money is integer paise. The module sees only its own schema and the whitelisted kernel views it declares (MR §7.2). No native app: PWA with WebAuthn passkeys, browser speech as the voice stand-in.

## 2. Personas & The Family Graph (RBAC)

### Target Personas

- **Key persona:** Priya Sharma (`member`) — pays household bills day to day from her own phone; Hindi preferred.
- **Key persona:** Ravi Sharma (`admin`) — receives the default notifications, owns the Financial Safety view (FTS §11.2) and the manual override (FTS §11.3).
- **Secondary personas:** Ramesh Kumar (`staff`, driver) and Arjun Sharma (`minor`, 17) exist in this PRD to be provably locked out; Nani (`managed`) has no direct finance interaction in Phase 1.

### Access Control Matrix

Baseline is Core PRD §2; DM Q2 maps roles to modules; the manifest's `allowed_roles` (§4.4) and `v_module_permissions` enforce it at PERMISSION_CHECK (MR §7.3 step 4). Deny-by-default: anything not listed is blocked.

| Role | Finance access | Can | Cannot | Enforcement note |
|---|---|---|---|---|
| admin | Full | All four intents; link/unlink billers (Level 0 UI); see the Financial Safety view; override a session (FTS §11.3, fresh passkey + reason); receive every default notification | Approve on a public-surface device; raise `biometric_required_above_paise` above 0; run anything at Level 2 or 3 | Q4 sends admin notifications to private devices only |
| member | Co-owner | `PAY_BILL`, `LIST_BILLS_DUE`, `CHECK_BALANCE`, `PAYMENT_STATUS`; approve own payments with passkey | Override sessions; link billers; see the Financial Safety view; change family settings (§4.6) | Blocked by the same family-scoped lock as admin (FTS §9.4) |
| minor | None | — | Any finance intent; any wealth figure on any device | Attempt → BLOCKED, audit `ROLE_VIOLATION`, high-severity admin alert (Core PRD §6) |
| elder | None in Phase 1 | — | Any finance intent | Ruled 2026-09-17: denied (DM Q2, Core PRD §2). MR §4.2's example that grants `CHECK_BALANCE` to elder is to be corrected in the round-2 review |
| staff | None | — | Any finance intent, including "what is madam's balance" | Attempt → BLOCKED + `ROLE_VIOLATION`; P2P payroll (Core PRD Scenario 4) is out of scope |
| managed | No login | Be the subject of a future expense tag | Trigger anything | `PAY_BILL` rejects a non-null `actor.acting_as` in Phase 1 (§6 row 6) |
| passive | No interaction | — | Anything; is never notified | Family bills are family resources; a passive node is never a payer |

## 3. User Scenarios / Use Cases

All scenarios use the Sharma family seed (DM §8): Ravi admin (`usr-ravi…0001`), Priya member (`usr-priy…0002`), Arjun minor, Nani managed (proxies: Priya primary, Ravi secondary, rule `hierarchy`), Ramesh staff; devices Ravi Phone, Priya Phone (private) and Kitchen Tablet (`is_public_surface = TRUE`). The family's linked biller is `BESCOM_KA_001`; Priya holds an active `AA_BALANCE_FETCH` consent for HDFC (CM §11). Amounts follow FTS §2.3: the bill is ₹2,847.00 = 284700 paise.

### Scenario 1 — Priya pays the BESCOM bill (the vertical slice)

1. 20:41 IST, Priya Phone. Priya taps the mic (browser speech stand-in) and says *"BESCOM ka bill bhar do."* The Supervisor enters INTENT_ANALYSIS, parses `PAY_BILL {biller_id: BESCOM_KA_001, amount_paise: null}` at confidence 0.92, generates the session's UUIDv4 idempotency key and persists it to `supervisor_sessions` before anything else (FTS §5.2). `amount_paise: null` is allowed by the entities schema; fetching the due amount is the module's job (MR §10 step 2).
2. PERMISSION_CHECK: member ∈ `allowed_roles`; finance active for the family; tier 1 ≤ ceiling 1; active AA consent handle exists. G2: `INSERT INTO resource_lock (family_id, 'BBPS_BESCOM_KA_001', session_id, priya, NOW())` succeeds (FTS §9.2).
3. REASONING (read dispatch): FinanceAgent calls the DPI Gateway → BBPS simulator bill fetch (`POST /bill/fetch`, SIM §5.1 B1, §6.1) → `{due_paise: 284700, bill_ref: 'KA-2026-09-8812', due_date: 2026-09-25}` with `cache_metadata {fetched_at, source_api: 'bbps_sim', expires_at: +24h}`. G3: a forced AA balance fetch (TTL bypassed, coalesced per RB §3.2, one of three hourly slots for handle `ch-abc-123`) returns 1825040 paise. Check: 1825040 ≥ 284700 + 5000 buffer — pass.
4. APPROVAL_GATE → AWAITING_APPROVAL with `expires_at = NOW() + 5 min` (DM §3.7). Priya Phone shows the passkey prompt from §7: "BESCOM को ₹2,847.00 — बिल KA-2026-09-8812, देय 25 सितम्बर". Priya approves with her passkey (WebAuthn user verification).
5. G5 CONSENT_REVERIFY reads `consent_records` and `consent_handles` live (never Redis): active, `revalidation_required = FALSE`, scope covers `fi_types ['DEPOSIT']`. `reverified_at` is stamped into the envelope.
6. Phase 1 COMMIT moves the session to EXECUTION with the key (point of no return). EXECUTION dispatch: FinanceAgent, in one transaction, inserts `finance.idempotency_ledger (key, pending)`, `finance.transactions (state = 'INITIATED')` and `core.fn_append_audit('BILL_PAYMENT_INITIATED', …)`, commits, then asks `payment_routing` to format the BBPS payload and posts it through the DPI Gateway with the key (10 s timeout).
7. BBPS simulator returns 200 with a `transaction_ref_id`, written here as `'BBPS-TXN-2847001'` after FTS §2.3; the simulator derives the reference from the idempotency key (SIM §4.2), so tests assert the pattern and that payment and status agree, not a fixed value. The module commits `transactions → CONFIRMED` and stores the final envelope in the ledger, then returns `status: success`, `side_effects: [{provider: bbps, external_ref: 'BBPS-TXN-2847001', state: executed_confirmed, amount_paise: 284700}]`.
8. Phase 2 (kernel, one transaction): audit row `BILL_PAYMENT_EXECUTED` (details: biller_id, amount_paise, transaction_ref_id, idempotency_key, automation_tier 1 — UUIDs and amounts only) plus session → SUCCESS_CONFIRMATION. Only after COMMIT is the lock released: `UPDATE core.resource_lock SET released_at = NOW(), release_reason = 'completed'` (DM v1.3 §3.11; lock rows are never deleted, and where FTS v1.2 still shows a DELETE its §9.2 note says to run this UPDATE). Then `notification_engine` pushes `finance.pay_bill.success` to Priya Phone in Hindi and to Ravi Phone as the admin default notification. The Kitchen Tablet shows nothing.

### Scenario 2 — BBPS times out, the session becomes a zombie, the Healer resolves it

1. Same flow, next month, with the biller linked as `SIM_TIMEOUT_001` in the test fixture: the simulator waits 12 s and then records the payment as made (SIM §5.1 B10; deterministic, where RB §9.4's chaos scenario `bbps_timeout` does the same thing at random). The DPI Gateway aborts at the 10 s timeout (FTS §2.3 T+1) after Phase 1 has committed and the module's INITIATED row exists.
2. FinanceAgent cannot claim success or failure. It returns `status: failure`, `error: {code: MOD_EXECUTION_UNCONFIRMED, class: TERMINAL, message_key: finance.error.FIN_001}` and `side_effects: [{state: executed_unconfirmed, external_ref: null, amount_paise: 284700}]` (MR §9, §10 step 8b). The ledger keeps `pending`.
3. Priya sees FIN_001: "भुगतान में सामान्य से अधिक समय लग रहा है। हम स्थिति जांच रहे हैं।" (FTS §10.2) with no retry button. The session stays in EXECUTION and the lock stays held (FTS §4.3; MR v1.1 §9 now says the same, and nothing but the Healer may move an EXECUTION session, AGENTS.md §4 item 19).
4. T+5 min: the Healer (SYSTEM_ACTOR_UUID, Redis lock `healer:global_lock`) selects the zombie `FOR UPDATE` and polls the BBPS simulator's status endpoint by idempotency key (`GET /payment/status`, SIM §5.1 B12; FTS §6.4). Simulator answer: `SUCCESS`, ref `BBPS-TXN-2847002` — the payment went through, the acknowledgement was lost. The Healer queues `AUDIT_LOG_WRITE` (P1).
5. T+10 min: next run processes P1 first — re-polls BBPS, writes the audit row with the original BBPS timestamp, moves the session to SUCCESS_CONFIRMATION, marks the task `succeeded` in one transaction, releases the lock and pushes "✅ ₹2,847 paid. Ref: BBPS-TXN-2847002" to Priya and Ravi. The module's `finance.transactions` row is moved to CONFIRMED by the reconcile hook (§8, OI-3).
6. Variants exercised with other scenario billers (SIM §5.1 B6, B7, B11, B16): `NOT_FOUND` → Healer re-queues `BILL_PAYMENT` (P3) with the **same** key (FTS §6.4 hard rule); `PENDING` → wait, admin alert at 30 min, FAILED at 4 h (FTS §7.2); BBPS unreachable three polls → admin alert FIN_011. Crash Scenarios A–D of the Build Gate map onto steps 1–5.

### Scenario 3 — Ravi and Priya try to pay BESCOM at the same time

Ravi's session acquires `BBPS_BESCOM_KA_001` at 21:04:10. Priya's session runs G2 at 21:04:12: the `INSERT … ON CONFLICT DO NOTHING` returns zero rows. Priya gets FIN_009 "इस बिलर को भुगतान पहले से प्रगति में है।" with who holds the lock and since when; no key is generated, nothing external is called. Had Priya been paying Airtel (`BBPS_AIRTEL_001`), both would proceed (FTS §9.4). The lock is per family, not per user; Core PRD §6's "per user" wording is superseded (register item 15).

### Scenario 4 — Ramesh asks for the balance; Arjun asks the kitchen tablet

Ramesh, on his own phone: *"Madam ka bank balance kitna hai?"* PERMISSION_CHECK fails (staff ∉ `allowed_roles` for `CHECK_BALANCE`, cross-checked against `v_module_permissions`). The session goes to BLOCKED, `MOD_PERMISSION_DENIED`, audit `ROLE_VIOLATION`, and Ravi receives a high-severity alert (Core PRD §6). Separately, Arjun asks the Kitchen Tablet "how much money do we have?" The device is `is_public_surface = TRUE`, so the Supervisor blocks at INTENT_ANALYSIS before any dispatch: "I can only display financial data to the Admin on a private device" (Core PRD Scenario 9). The same block applies if Ravi himself is logged in on the tablet (AGENTS.md invariant 6).

### Scenario 5 — Bills due this week, with the AA budget exhausted

Ravi, Ravi Phone, 20:55 IST: *"Is hafte koi bill due hai?"* → `LIST_BILLS_DUE {within_days: 7}`. FinanceAgent reads `finance.billers` (BESCOM, Airtel, BWSSB), refreshes any due-amount cache older than 24 h from the BBPS simulator and returns a card: BESCOM ₹2,847 due 25 Sep, Airtel ₹999 due 28 Sep. Ravi: *"Aur balance?"* → `CHECK_BALANCE`. The HDFC handle has used its three fetches this hour (two dashboard opens plus Scenario 1), so the module serves the 14-minute-old cached balance with "Balance as of 20:41. Refresh available in 5 min" (RB §3.3) and `cache_metadata` marking it stale. Ravi: *"Airtel bhi bhar do."* The forced G3 fetch is refused by the budget; the payment is hard-blocked with FIN_006 (RB §3.3 "PAY_BLOCKED_NO_BUDGET"). There is no admin override, by founder ruling (OI-7): this is a payment-safety gate, not a preference (§4.6). Ravi is told when the slot reopens.

## 4. Functional Requirements (The "Agentic" Loop)

### 4.1 The loop for `PAY_BILL`

- **Trigger:** a text or voice-stand-in request on a private device (`PAY_BILL`, `LIST_BILLS_DUE`, `CHECK_BALANCE`, `PAYMENT_STATUS`); a UI action on the "Bills due" card (same intent, modality `ui_action`); the nightly bill-due refresh (FSM §3.1: bill dues, 24 h, nightly cron) which only produces a "due in ≤ 3 days" notification. Not triggers in Phase 1: schedules, low-balance alerts, autopay.
- **Information gathering:** actor role from `v_family_members`; consent reference (never the handle) from `v_active_consents`; device context from `v_device_surfaces` and the envelope's `context.is_public_surface`; the family's linked billers and cached dues from `finance.billers`; BBPS bill fetch through the DPI Gateway (read phase, MR §10 step 4); the forced AA balance fetch at G3 (TTL bypass, coalescing RB §3.2, 3/hour per handle); the BBPS daily budget from Redis (50/day per user, fail-closed on Redis loss, RB §2.4).
- **Analysis logic (deterministic; the LLM never computes money):** `amount = entities.amount_paise` if given and equal to the fetched due, else the fetched due; a mismatch returns `needs_clarification` with both figures. Gates in FTS order: RBAC → lock → balance (`balance_paise ≥ amount_paise + buffer`, buffer 5000 paise unless the family has raised it, §4.6; else FIN_005; no fresh fetch this session, else FIN_006 hard stop) → passkey (always, `biometric_required_above_paise: 0`) → CONSENT_REVERIFY. FTS §5.3 collision check: a non-terminal session for the same biller in the last 24 h returns that session's status and creates no new key. `deadline_at` is checked before every DPI call (MR §6.2). The automation tier of `PAY_BILL` is always 1.
- **Execution / fulfilment:** the FTS §2.3 sequence. Phase 1 COMMIT (kernel) → EXECUTION dispatch → module transaction {ledger `pending`, `transactions INITIATED`, `fn_append_audit('BILL_PAYMENT_INITIATED')`} → `payment_routing` formats the payload → DPI Gateway POST with the idempotency key (10 s timeout; BBPS dedups the key for 24 h, so FIN_004 is a success path) → module transaction {`transactions CONFIRMED` or `FAILED`, ledger `final`} → response with exhaustive `side_effects` → Phase 2 (kernel, one transaction: audit row + session) → lock release → `notification_engine` push to payer and admin, private devices only, via `display_key`. A timeout or crash yields `MOD_EXECUTION_UNCONFIRMED` with `executed_unconfirmed`, and the Healer owns the outcome. The module never re-prompts, never retries a mutating call on its own, and never generates a second key.

### 4.2 Features In (Prioritised)

- **`PAY_BILL` [M]:** one linked BBPS biller, one passkey, family-scoped lock, ledger, audit, notifications; the whole of Scenario 1.
- **Forced AA balance check inside `PAY_BILL` [M]:** G3 with the ₹50 buffer, coalescing and the 3/hour budget; FIN_005/FIN_006 paths.
- **Zombie cooperation [M]:** exhaustive `side_effects`, ledger rows kept ≥ 7 days (MR §6.4), reconcile hook for `finance.transactions` (OI-3), data for the Financial Safety view (FTS §11.2).
- **Biller registry [M]:** `finance.billers` seeded with `BESCOM_KA_001` for the Sharma family; linking is a Level 0 admin UI action in Phase 1, not an intent.
- **Payment notifications [M]:** payer plus admin default (Core PRD §2), Hindi and English `display_key`s, suppressed on public-surface devices.
- **`LIST_BILLS_DUE`:** due amounts per linked biller from the BBPS simulator, 24 h cache with `cache_metadata`, nightly refresh, "due in 3 days" nudge.
- **`CHECK_BALANCE`:** AA balance with the 15-minute TTL and the RB §3.3 staleness messages.
- **`PAYMENT_STATUS`:** answers "did we pay BESCOM this month?" from `finance.transactions` without a DPI call (Core PRD Scenario 6 minus OCR).
- **Daily family amount limit (FIN_013):** admin-set; default is no family limit beyond BBPS's 50 transactions/day. One of the "stricter only" settings of §4.6.

### 4.3 Features Out

- **`PAY_RECURRING` / Level 2 autopay:** needs pre-authorisation semantics and an answer to OI-1 (buffer vs recurring); listed in MR §4.2's example but deferred to manifest 0.2.0.
- **P2P payroll for Ramesh (Core PRD Scenario 4):** a UPI P2P rail, not BBPS; no simulator; outside FTS §1.1.
- **`AA_TRANSACTION_HISTORY` dashboard:** a second purpose code with 1-year retention rules (CM §3.2); no demo value in the slice.
- **Credit / ULI / OCEN (Master PRD §4):** licence-bound and Level 3-adjacent; never Phase 1.
- **Vision-based tax notice check (Core PRD Scenario 6):** needs the `ocr` service module (P2).
- **Refund initiation:** FamilyLifeOS tracks refunds, the UPI PSP initiates them (FTS §8).
- **Biller discovery via intent, multi-biller batch payment:** batch needs multi-resource locks (DM §10 open issue).
- **Real-money integration, UPI VPA management, biller onboarding, AML:** FTS §1.2 and the Decision Log.

### 4.4 Module manifest (Module Registry contract)

Valid against MR §4.1. `requires_consent_providers` uses the MR v1.1 narrowing (consent providers only: aa, abha, digilocker, ondc); BBPS is a routing provider in `dpi_providers`.

```json
{
  "manifest_version": 1,
  "module_id": "finance",
  "version": "0.1.0",
  "tier": "core",
  "display_name": { "en": "Financial Command Center", "hi": "वित्तीय कमांड केंद्र" },
  "description": "BBPS bill payment with a forced AA balance check, bill-due visibility and payment status. Phase 1 vertical slice: PAY_BILL.",
  "deactivatable": true,
  "entrypoint": "modules.finance.agent:FinanceAgent",
  "health_check": "health",
  "intents": [
    {
      "intent_code": "PAY_BILL",
      "description": "Pay a linked utility bill via BBPS after a forced AA balance check and passkey approval.",
      "automation_tier_ceiling": 1,
      "allowed_roles": ["admin", "member"],
      "mutating": true,
      "requires_consent_providers": ["aa"],
      "biometric_required_above_paise": 0,
      "entities_schema": {
        "type": "object",
        "additionalProperties": false,
        "required": ["biller_id"],
        "properties": {
          "biller_id": { "type": "string", "pattern": "^[A-Z0-9_]{3,40}$" },
          "amount_paise": { "type": ["integer", "null"], "minimum": 100 },
          "bill_ref": { "type": ["string", "null"], "maxLength": 60 }
        }
      }
    },
    {
      "intent_code": "LIST_BILLS_DUE",
      "description": "List linked billers with due amounts and dates (BBPS bill fetch, 24 h cache).",
      "automation_tier_ceiling": 0,
      "allowed_roles": ["admin", "member"],
      "mutating": false,
      "requires_consent_providers": [],
      "entities_schema": {
        "type": "object",
        "additionalProperties": false,
        "properties": { "within_days": { "type": "integer", "minimum": 1, "maximum": 30, "default": 7 } }
      }
    },
    {
      "intent_code": "CHECK_BALANCE",
      "description": "Consolidated balance via Account Aggregator with staleness metadata.",
      "automation_tier_ceiling": 0,
      "allowed_roles": ["admin", "member"],
      "mutating": false,
      "requires_consent_providers": ["aa"],
      "entities_schema": { "type": "object", "additionalProperties": false, "properties": {} }
    },
    {
      "intent_code": "PAYMENT_STATUS",
      "description": "Status of recent payments from the module ledger; no DPI call.",
      "automation_tier_ceiling": 0,
      "allowed_roles": ["admin", "member"],
      "mutating": false,
      "requires_consent_providers": [],
      "entities_schema": {
        "type": "object",
        "additionalProperties": false,
        "properties": {
          "biller_id": { "type": ["string", "null"] },
          "since_days": { "type": "integer", "minimum": 1, "maximum": 90, "default": 31 }
        }
      }
    }
  ],
  "data_scopes": {
    "owns_schema": "finance",
    "core_read_views": ["v_family_members", "v_module_permissions", "v_active_consents", "v_device_surfaces"]
  },
  "dpi_providers": ["aa", "bbps"],
  "service_dependencies": ["notification_engine", "payment_routing"],
  "data_dependencies": ["secure_vault"],
  "resource_budgets": { "p95_handler_ms": 300, "hard_timeout_ms": 30000 }
}
```

### 4.5 Owned schema (`finance`)

Conventions per DM §9.3 (family_id, user_id, created_at, updated_at, deleted_at, index on `(family_id, created_at DESC)`), role `role_module_finance` per MR §7.2. The foreign keys to `core.families`/`core.users` are created by the Alembic migration role, which holds REFERENCES on the kernel tables; the runtime module role never needs it. No FK to `core.supervisor_sessions` because the kernel hard-deletes terminal sessions after 24 h (DM §7.4). Four tables:

| Table | Purpose | Notes |
|---|---|---|
| `finance.billers` | The family's linked BBPS billers and the 24 h due-amount cache | `customer_params` holds only the simulator's synthetic consumer id in Phase 1 (OI-4) |
| `finance.transactions` | One row per payment attempt; the module's view of the money | `state` INITIATED → CONFIRMED / FAILED; `idempotency_key` unique |
| `finance.family_settings` | The family's adjustable defaults (§4.6) | One row per family; absent row = shipped defaults |
| `finance.idempotency_ledger` | MR §6.4 ledger; stored envelope returned verbatim on re-dispatch | Rows never garbage-collected before 7 days |

```sql
CREATE SCHEMA finance;

CREATE TABLE finance.billers (
  biller_id        VARCHAR(40)  NOT NULL,                       -- BBPS biller id, e.g. 'BESCOM_KA_001'
  family_id        UUID         NOT NULL REFERENCES core.families(family_id) ON DELETE CASCADE,
  user_id          UUID         NOT NULL REFERENCES core.users(user_id)      ON DELETE CASCADE,  -- admin who linked it
  display_name     VARCHAR(100) NOT NULL,                       -- 'BESCOM (home)'
  category         VARCHAR(20)  NOT NULL CHECK (category IN ('electricity','water','gas','mobile','broadband','dth','other')),
  customer_params  JSONB        NOT NULL DEFAULT '{}',          -- Phase 1: simulator consumer id only (OI-4)
  last_bill_ref    VARCHAR(60),
  last_due_paise   BIGINT       CHECK (last_due_paise IS NULL OR last_due_paise >= 0),
  last_due_date    DATE,
  bill_fetched_at  TIMESTAMPTZ, bill_source_api VARCHAR(40), bill_expires_at TIMESTAMPTZ,   -- FSM §3.1 cache metadata, TTL 24 h
  created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  deleted_at       TIMESTAMPTZ,
  PRIMARY KEY (family_id, biller_id)
);
CREATE INDEX idx_billers_family_created ON finance.billers(family_id, created_at DESC);

CREATE TABLE finance.transactions (
  transaction_id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  family_id                UUID        NOT NULL REFERENCES core.families(family_id) ON DELETE CASCADE,
  user_id                  UUID        NOT NULL REFERENCES core.users(user_id)      ON DELETE CASCADE,  -- payer
  session_id               UUID        NOT NULL,               -- supervisor_sessions.session_id, no FK (DM §7.4 purge)
  idempotency_key          UUID        NOT NULL UNIQUE,        -- FTS §5: one per session, reused by the Healer
  biller_id                VARCHAR(40) NOT NULL,
  bill_ref                 VARCHAR(60),
  amount_paise             BIGINT      NOT NULL CHECK (amount_paise >= 100),
  state                    VARCHAR(10) NOT NULL CHECK (state IN ('INITIATED','CONFIRMED','FAILED')),
  bbps_transaction_ref_id  VARCHAR(64),                        -- set on CONFIRMED (or by the reconcile hook)
  failure_code             VARCHAR(10),                        -- FIN_xxx, only when FAILED
  automation_tier          SMALLINT    NOT NULL DEFAULT 1 CHECK (automation_tier BETWEEN 0 AND 2),
  initiated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  confirmed_at             TIMESTAMPTZ,
  created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  deleted_at               TIMESTAMPTZ
);
CREATE INDEX idx_tx_family_created ON finance.transactions(family_id, created_at DESC);
CREATE INDEX idx_tx_unconfirmed    ON finance.transactions(initiated_at) WHERE state = 'INITIATED';  -- reconcile hook scan

CREATE TABLE finance.family_settings (                          -- §4.6; absent row = shipped defaults
  family_id                UUID     PRIMARY KEY REFERENCES core.families(family_id) ON DELETE CASCADE,
  balance_buffer_paise     BIGINT   NOT NULL DEFAULT 5000 CHECK (balance_buffer_paise BETWEEN 5000 AND 10000000),  -- never below the FTS G3 buffer
  daily_limit_paise        BIGINT   CHECK (daily_limit_paise IS NULL OR daily_limit_paise >= 100),                 -- NULL = no family limit (FIN_013)
  due_nudge_days           SMALLINT NOT NULL DEFAULT 3 CHECK (due_nudge_days BETWEEN 1 AND 7),
  admins_get_success_copies BOOLEAN NOT NULL DEFAULT TRUE,  -- routine success notices only; safety alerts always reach the admins
  updated_by_user_id       UUID     NOT NULL REFERENCES core.users(user_id),   -- an admin (app-layer check)
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), deleted_at TIMESTAMPTZ
);

CREATE TABLE finance.idempotency_ledger (                       -- MR §6.4
  idempotency_key    UUID        PRIMARY KEY,
  family_id          UUID        NOT NULL REFERENCES core.families(family_id) ON DELETE CASCADE,
  user_id            UUID        NOT NULL REFERENCES core.users(user_id)      ON DELETE CASCADE,
  intent_code        VARCHAR(40) NOT NULL,
  status             VARCHAR(10) NOT NULL CHECK (status IN ('pending','final')),
  response_envelope  JSONB,                                    -- verbatim ModuleResponse once final
  created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  deleted_at         TIMESTAMPTZ                               -- never set within 7 days of created_at
);
CREATE INDEX idx_ledger_family_created ON finance.idempotency_ledger(family_id, created_at DESC);
```

### 4.6 Settings and defaults (founder rulings 2026-09-17)

Principle (Decision Log, "defaults, not constants"): family preferences are adjustable defaults; safety gates are never settings. Finance adds one refinement: **a family may make a safety rule stricter, never looser.** The same idea already governs manifests, which may lower a biometric threshold but not raise it (MR §4.1).

| Setting | Default | Bounds | Who | Direction |
|---|---|---|---|---|
| Balance buffer at gate G3 | ₹50 (5000 paise, FTS §2.2) | ₹50 to ₹1,00,000; never below ₹50 | Admin | Stricter only |
| Daily family payment limit (FIN_013) | None | Any amount ≥ ₹1; removing or raising it needs the admin's passkey, lowering it does not | Admin | Stricter freely, looser with a passkey and an audit row |
| "Bill due soon" nudge | 3 days before the due date | 1 to 7 days | Admin | Preference |
| Routine success notices copied to the admins | On (Core PRD §2) | On / off | Admin | Preference |
| Notification language | The recipient's `preferred_language` | Kernel value | Each user | Preference |

Changes are Level 0 admin actions in the PWA, written to the kernel audit log (proposed code `FINANCE_SETTINGS_CHANGED`, details: setting name, old and new value; to be added with OI-3's list) because they change what money may move.

**Never a setting:** the five gates and their order; a passkey for every BBPS payment whatever the amount; the forced balance fetch before paying, and the hard block when it cannot be made (no override, OI-7); one idempotency key per session and the Healer reusing it; the family-scoped lock; no "try again" control on an unknown outcome; Level 3 automation; the role blocks for minor, elder, staff, managed and passive; the public-surface block; safety alerts (FIN_011, FIN_012, `ROLE_VIOLATION`) reaching the admins.

Out of scope for Phase 1 and noted so that it is not reinvented as a setting: a co-approval rule ("payments above ₹X by a member also need an admin's passkey"). It is a second approval gate, which is an FTS change, not a module preference.

## 5. India Stack (DPI) Touchpoints

Phase 1 touches DPIs only through the WireMock simulators (RB §9; Decision Log 2026-09-17). Contract tests (RB §9.5) keep the stubs aligned with the real request/response shapes; nothing here implies a live integration.

- **Identity:** none. No Aadhaar, no e-KYC. Actor identity comes from the authenticated PWA session; the passkey (WebAuthn user verification) stands in for the biometric of FTS G4 and CM §4.2 step 4.
- **Data — Account Aggregator (consent provider `aa`):** purpose code `AA_BALANCE_FETCH` (CM §3.2: balance only, 15-minute retention, essential, not for minors). Grant flow CM §4.2 + §6.1.1 against the AA simulator (POST /Consent, 30 s polling, 10-minute approval window); fetch per CM §6.1.2 with the RB §3 budget (3 fetches/hour per consent handle, hourly TTL aligned to the IST clock) and coalescing (RB §3.2). Stubs: Tech_Spec_Simulator_Architecture §5.2, rows A1–A12 (consent create and status, rejected, never approved, revoked, FI request and fetch with healthy, low and slow variants, `aa_rate_limit.json` from RB §9.1, breaker failures, and the `/Consent/status` probe of RB §8.3); chaos `aa_random_failures` (RB §9.4, 20 % HTTP 500). The JWS-signed consent webhook is not simulated yet (SIM OI-3); revocation is caught by CONSENT_REVERIFY polling (row A5).
- **Payments — BBPS (routing provider `bbps`, not a consent provider):** the per-transaction authorisation is the passkey (G4) plus CONSENT_REVERIFY of the AA purpose (G5). Stubs: Tech_Spec_Simulator_Architecture §5.1, rows B1–B17, which include the Build Gate's six scenarios (SUCCESS B4, FAILED B8, PENDING B6/B13, NOT_FOUND B11, 429 B14, timeout B10), `bbps_consecutive_failures.json` (RB §9.2) and the `/biller/fetch` probe of RB §8.3; chaos `bbps_timeout` (RB §9.4). Duplicate-key behaviour (FIN_004) and the status query are the simulator's payment state machine (SIM §4.2); the 24-hour boundary is tested in the Healer with an injected clock, not in the simulator. `POST /bill/fetch` and `GET /payment/status` are gateway contracts defined in SIM §6.1. Open: FTS §2.3's request carries a VPA and an account number, which invariant 9 forbids storing (SIM OI-1; OI-4 below).
- **Commerce, voice:** none. ONDC is not declared; Bhashini is replaced by the browser speech stand-in with the RB §7.3 confidence thresholds (< 0.80 reject, 0.80–0.90 confirm).

| Budget / breaker | Value (RB, Feb 2026) | Module behaviour |
|---|---|---|
| AA fetches | 3 / hour / consent handle; Redis fail-open | Coalesce; serve cache with staleness text; hard-block `PAY_BILL` without a fresh fetch |
| BBPS transactions | 50 / day / user; Redis fail-closed | Counted at G3 before the key exists; never decremented on failure (RB §4.2) |
| AA breaker | 3 consecutive → OPEN 30 min | `MOD_DPI_DOWN`; reads show last cached balance with warning; payments blocked |
| BBPS breaker | 3 consecutive → OPEN 30 min; 429 never counts | `MOD_DPI_DOWN`; degradation script (Core PRD Scenario 8) |

## 6. Conflict Resolution Matrix

Consistent with Core PRD §6 and DM §3.4. FTS wins where it and the Core PRD differ (register items 13/15).

| # | Conflict scenario | Resolution logic |
|---|---|---|
| 1 | Two family members pay the same biller concurrently | Family-scoped lock `BBPS_{biller_id}` (FTS §9.2); second session gets FIN_009, no key, nothing external. Different billers proceed in parallel. |
| 2 | Same payer double-taps or re-requests within 24 h | FTS §5.3 collision check returns the existing session's status; no new session, no new key. |
| 3 | User-stated amount ≠ fetched due amount | `needs_clarification` with both figures; never pay the larger silently; partial payment is out of scope, so "pay ₹2,500 of ₹2,847" ends in a clear refusal. |
| 4 | Balance insufficient (or unverifiable) and the bill is due today | FIN_005 / FIN_006 hard block (FTS G3). No override, by founder ruling (OI-7, §4.6). Admin default notification carries the due date. |
| 5 | BBPS 50/day exhausted, bill due today | Hard block with reset time; suggest the biller's own channel; offer a reminder at 00:01 IST; admin may mark "paid externally" (RB §11). |
| 6 | Proxy contradiction on an expense tagged to a managed profile | DM §3.4: `hierarchy` → primary's action wins, secondary rejected silently, both logged as `PROXY_ACTION`; `notify_block` → both paused, both proxies + admin alerted. Phase 1: `PAY_BILL` rejects a non-null `acting_as` (`MOD_PERMISSION_DENIED`), so the rule is documented, not exercised. |
| 7 | Agent disagreement — Finance says low balance, Health wants a medicine order | FinanceAgent returns `status: conflict` with the paise headroom; the Supervisor defaults to "Conserve resources" (Core PRD §6). Core → Core calls are forbidden (MR §3.2). |
| 8 | Modal contradiction — photo of a paid receipt vs `PAYMENT_STATUS` unpaid | Visual truth wins (Core PRD §6) but only through an admin "mark paid externally" (Level 0) with an audit row; the module never auto-marks. OCR itself is P2. |
| 9 | BBPS breaker OPEN before approval vs after Phase 1 | Before: queue a reminder task and tell the user "BBPS is unresponsive. I have queued the bill. I will retry in 1 hour" (Core PRD Scenario 8); a fresh passkey is required when it resumes. After Phase 1: the Healer's P3 retry with the original key. No payment executes without a passkey given for that key. |
| 10 | Restricted role (staff / minor) reaches for wealth data | BLOCKED, audit `ROLE_VIOLATION`, high-severity admin alert (Core PRD §6). |

## 7. Design & Generative UI

States, not screens. The PWA renders one Finance "live card" whose state is driven by the session journal; every string is a `display_key` rendered in `users.preferred_language`.

- **Card states:** `bills_due` (linked billers, due dates, staleness stamp) → `bill_fetched` (biller, amount, bill ref, due date, "balance verified n s ago" — the figure itself only on `CHECK_BALANCE`) → `awaiting_approval` (passkey prompt, 5-minute countdown from `expires_at`) → `executing` ("Sending to BBPS…"; the state survives app close) → `success` (BBPS ref, amount, who approved) · `verifying` (FIN_001/FIN_011: "We're checking the status", no retry control — a retry would mean a new key) · `failed` (FIN_003/005/007 with the next action) · `blocked` (role or surface).
- **Passkey approval prompt content:** biller display name, amount as `₹2,847.00` (formatted from paise), bill ref, due date, source bank alias only ("HDFC ····"), consent purpose in plain words ("balance checked via Account Aggregator"), the payer's name, and the countdown. Never a raw account number, consumer number or handle. Approve / Cancel only; no "remember this".
- **Voice stand-in:** Web Speech API for ASR and `speechSynthesis` for TTS on `hi-IN`/`en-IN`; RB §7.3 thresholds apply (< 0.80 → "Sorry, I didn't catch that", 0.80–0.90 → "I heard: … Is that right?"). Bhashini locales are a Phase 2 swap behind the `translation` service.
- **Public-surface rule:** on `is_public_surface` devices the Finance card renders a single "Available on a private device" placeholder; toasts and TTS for financial events are suppressed (DM Q4 notifies private devices only).
- **Admin-only Financial Safety view (FTS §11.2):** active locks, sessions in EXECUTION > 5 min with Healer poll count, pending AUDIT_LOG_WRITE tasks, FIN_012 incidents, 24 h summary; override via FTS §11.3 (fresh passkey + ≥ 20-character reason).
- **Critical alerts:** FIN_011/FIN_012 reach the admin as high-priority push on private devices; never as TTS on a shared speaker.
- **Early sketches:** none; the Playwright test doubles as the interaction script.

## 8. Technical Considerations & Success Metrics

### Technical Approach

| Concern | Governing document | What this module does |
|---|---|---|
| Gate order, 2PC, key lifecycle, Healer, locks, FIN codes | FTS v1.2 §2, §4, §5, §6–§7, §9, §10 | Implements the module side of §2.3; supplies `side_effects`; never approves, never re-keys |
| Manifest, envelope, ledger, isolation, MOD codes | MR v1.1 §4, §6, §7, §9 | §4.4 manifest; `finance.idempotency_ledger`; imports only `familylifeos.sdk` |
| AA consent, CONSENT_REVERIFY, AA adapter | CM v1.3 §3.2, §4.2, §5, §6.1 | Declares `aa`; consumes `consent[].reverified_at`; rejects > 60 s as `MOD_CONSENT_STALE` |
| Budgets, breakers, stubs | RB v1.2 §2–§4, §8, §9; SIM §4–§6 | Reads budget outcomes from the DPI Gateway; never touches Redis budget keys itself |
| Table conventions, roles, seed | DM v1.3 §9.3, §8; DM v1.3 | Schema §4.5; roles `admin`/`member`; `resource_lock` table |
| TTLs and tiers | FSM v2.1 §2, §3.1 | Balance 15 min (forced on pay), bill dues 24 h; tier 1 only |

**Error handling.** Raw codes never reach users (FTS §10.1). The envelope carries the MR code in `error.code`; the FIN code rides in `error.message_key` (`finance.error.FIN_xxx`) and `error.detail` (a convention this PRD and the Health PRD share; to be confirmed in the Module Registry round-2 review). Mapping of the codes this module raises or relays:

| FIN | Envelope code / class | Retryable | User message (English; Hindi per FTS §10.2 / UX_Error_Message_Library P1) |
|---|---|---|---|
| FIN_001 BBPS timeout | `MOD_EXECUTION_UNCONFIRMED` / TERMINAL* | Healer only | Payment is taking longer than usual. We're checking the status. |
| FIN_002 BBPS 429 | `MOD_DPI_RATE_LIMITED` / RETRYABLE | Yes, `retry_after_ms` | Too many requests. Your payment will be retried in a few minutes. |
| FIN_003 biller not found | `MOD_INTERNAL`-class TERMINAL, coded FIN_003 | No | This bill couldn't be found. Please check your account number. |
| FIN_004 duplicate key ACK | success path | — | Payment already processed. |
| FIN_005 insufficient balance | gate failure (kernel) | No | Your bank balance is too low for this payment. |
| FIN_006 stale / failed AA fetch | `MOD_STALE_DATA` / TERMINAL | After budget resets | Couldn't verify your balance. Payment paused for safety. |
| FIN_007 AA consent expired | `MOD_CONSENT_MISSING` / TERMINAL | After renewal | Your bank connection needs renewal. |
| FIN_009 lock conflict | `MOD_LOCK_CONFLICT` / TERMINAL | After release | A payment to this biller is already in progress. |
| FIN_010–FIN_015 | raised by kernel / Healer | per FTS §10.1 | per FTS §10.1 |

**TTLs and windows.** Balance 15 min, forced on any pay (FSM §3.1); bill dues 24 h; session `expires_at` per DM §3.7 (AWAITING_APPROVAL 5 min, REASONING/EXECUTION 2 min; the cleanup job never aborts an EXECUTION session, DM v1.3 §7.4); zombie threshold 5 min (FTS §7.1); Healer every 5 min; idempotency key valid 72 h (FTS §5.4); ledger rows ≥ 7 days (MR §6.4); locks stale after 30 min (FTS §9.3). **Rate limits** as in §5. **Reconcile hook (OI-3):** `FinanceAgent.reconcile(idempotency_key, outcome, external_ref)` moves an INITIATED row to CONFIRMED/FAILED when the Healer resolves a zombie; scans `idx_tx_unconfirmed` as a safety net.

### Success Metrics (The Autonomy Score)

| Metric | Definition | Phase 1 target (simulators) |
|---|---|---|
| Autonomy score | `PAY_BILL` sessions reaching SUCCESS_CONFIRMATION with no admin action (FTS §11.1 triggers) / all sessions | ≥ 95 % with chaos off; manual interventions < 1 % (MC §10.2) |
| DPI reliability | Successful BBPS + AA simulator calls / all calls | 100 % chaos off; ≥ 90 % chaos on, with zero unresolved zombies after 4 h |
| Family NPS | Not measurable in portfolio mode | Replaced by a reviewer walkthrough of Scenarios 1–5 |
| Double-payment count (module-specific) | BBPS simulator payments per idempotency key over the k6 chaos run | 0 across ≥ 1,000 sessions; 100 % of re-dispatches served from the ledger |
| Zombie resolution time (module-specific) | Healer runs from zombie detection to a terminal session state, Crash Scenarios A–D | ≤ 2 runs (≤ 10 min) for A, B, C, D; lock released in every case |
| Handler latency | `metrics.handler_ms` excluding DPI wait | P95 ≤ 300 ms (manifest budget) |

## 9. GTM & Operations

- **Portfolio framing:** this module is the proof that the kernel is real. It demonstrates the five gates, the two-phase commit with a kernel-side audit row, family-scoped locking, idempotent re-dispatch, the Healer's zombie taxonomy and a passkey-based approval, all observable in the Financial Safety view and in the hash-chained audit log. It is not a product launch; MC §14 messaging is context only.
- **Launch plan:** the Playwright test "Priya pays BESCOM bill" plus Crash Scenarios A–D are the release criterion (Build Gate). Demo script = Scenarios 1–5 with the simulator scenario header switched between runs.
- **Timeline & phasing:**
  - **Slice 1 (Finance, first):** `PAY_BILL` [M] items, biller seed, notifications, Healer cooperation, Financial Safety data; manifest 0.1.0.
  - **Phase 1.1:** `LIST_BILLS_DUE`, `CHECK_BALANCE`, `PAYMENT_STATUS`, bill-due nudges, family amount limit; manifest 0.2.0 adds `PAY_RECURRING` only after OI-1 closes.
  - **Later (commercial track only):** real AA/BBPS behind FIU/BBPOU licences (MC §8 Phase 2), P2P payroll, transaction history, OCR-backed Scenario 6.

## 10. Open Issues & Q&A

### Open Issues

- **OI-1 — ₹50 buffer vs Level 2 recurring payments.** G3 checks `balance ≥ amount + 5000 paise` for a human-approved payment. A Level 2 recurring payment has no human in the loop, so the same buffer would let an autopay drain the account to ₹50; a larger safe-limit (per-payee cap plus a per-day cap) and a forced fetch per execution are needed before `PAY_RECURRING` exists. Owner: Shantanu Chaudhary, FTS v1.2 / this PRD v0.2.
- **OI-2 — Session state after `MOD_EXECUTION_UNCONFIRMED`.** **Closed 2026-09-17:** the session stays in EXECUTION; MR v1.1 §9 was corrected to match FTS §4.3 (review log MR §13).
- **OI-3 — Who writes the success audit row, and who fixes `finance.transactions`.** FTS §4.3 writes `BILL_PAYMENT_EXECUTED` and the session update in one kernel transaction; MR §6.3/§10 has the module write its own financial audit rows. This PRD follows FTS (module writes only `BILL_PAYMENT_INITIATED`); a `reconcile()` SDK hook is proposed so the Healer can settle module rows without touching the `finance` schema. The code name is settled: `BILL_PAYMENT_EXECUTED` (DM v1.3 §6, register item 7).
- **OI-4 — Where the consumer number lives.** Paying BESCOM needs a consumer id (FTS §2.3 `customer_params`). Invariant 9 forbids account numbers in the app DB; a utility consumer number is not a bank account but is personal data. Phase 1 stores only the simulator id; production storage (encrypted column, or a DigiLocker/vault reference) is for Security_Threat_Model.md.
- **OI-5 — DM §7.4 session cleanup vs the zombie window.** **Closed 2026-09-17:** DM v1.3 §7.4's cleanup never aborts an EXECUTION session (AGENTS.md §4 item 19).
- **OI-6 — `CHECK_BALANCE` for `elder`.** **Ruled 2026-09-17, closed for Phase 1:** denied (DM Q2, Core PRD §2). `role_module_permissions` is seeded by migration and has no per-family override (DM v1.3 §3.16), so there is no family setting for this today; whether one should exist is a question for the Module Registry round-2 review, not a Phase 1 feature.
- **OI-7 — Admin override of a blocked balance check.** **Ruled 2026-09-17:** no override in Phase 1. This is a payment-safety gate (FTS G3), so it is deliberately not a family-adjustable setting; if an override is ever added it needs its own audit code and passkey.

- **OI-8 — Per-family module settings convention.** This PRD adds `finance.family_settings`; see Vault PRD OI-8 (Module Registry round-2 review).
- **OI-9 — Audit codes for settings changes.** `FINANCE_SETTINGS_CHANGED` is proposed with OI-3's list for the DM v1.3 taxonomy before the freeze.

### Q&A

| Asked By | Question | Answer |
|---|---|---|
| Engineering | Why does `PAY_BILL` require consent provider `aa` and not `bbps`? | Consent providers are data-access frameworks with handles and revocation (AA, ABHA, DigiLocker, ONDC). BBPS is a payment rail authorised per transaction by the passkey at G4; there is no standing BBPS consent to reverify. MR v1.1 narrows the enum accordingly; `bbps` stays in `dpi_providers` for gateway routing. |
| Product | Why can't the user tap "Try again" after FIN_001? | The outcome is unknown, not failed. A retry would need a new session and a new idempotency key, which is a second payment if the first one went through. Only the Healer may re-submit, and only with the original key (FTS §6.4). |
| Engineering | Core PRD §5.4 says the Payment Routing Engine asks the admin for biometric approval. Does `payment_routing` prompt? | No. Under MR the approval gate is the Supervisor's AWAITING_APPROVAL state; `payment_routing` is a leaf Service Module that formats and validates the BBPS payload (MR §3.1). Modules must never re-prompt (MR §6.2). Core PRD v2.2 should reword §5.4. |

## 11. PRD Checklist

- [x] Title & Author defined.
- [x] Executive One-Pager finalized.
- [x] Family RBAC permissions mapped (seven roles, §2).
- [x] Agentic Loop logic defined (§4.1) with manifest and schema.
- [x] DPI (India Stack) points identified (§5, simulators only).
- [x] Conflict Resolution scenarios handled (§6).
- [x] GTM Approach outlined (§9, portfolio framing).
- [x] Success Metrics (Autonomy Score) set (§8).
- [x] OI-2 and OI-5 settled in MR v1.1 / DM v1.3; OI-6 and OI-7 ruled by the founder (2026-09-17).
- [ ] Independent review round completed (Codex, WP-15); OI-3, OI-8 and OI-9 settled in the round-2 spec reviews; OI-1 before `PAY_RECURRING`; OI-4 in the threat model.
