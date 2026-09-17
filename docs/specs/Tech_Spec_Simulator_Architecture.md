# Tech Spec: DPI Simulator Architecture

_WireMock simulators for Account Aggregator, BBPS, ABHA and DigiLocker: layout, scenario contract, stateful payment behaviour, chaos mode, contract tests, and an honest account of what is simulated_

> **Status:** DRAFT v0.1 — for review (Codex) · **Author:** Shantanu Chaudhary (Lead Product Architect), drafted with Claude Code · **Last content change:** 2026-09-17
> **Priority:** P1. Execution Plan WP-12. The Build Gate's WireMock scenarios (tracker → Phase 1 Build Gate) and the stub-generation packages WP-18 and WP-34 depend on §5 of this document.
> **Written against:** Runbook_DPI_Rate_Limits v1.2 (frozen), Financial Transaction Safety v1.2 (frozen), Consent Manager v1.3, Data Model v1.3 and Module Registry v1.1 (the last three await Codex review round 2; section references are re-checked at the freeze, WP-11).
> **Cited elsewhere as:** Simulator spec, SIM §n.

## 0. Document Governance

| Version | Date | Description of Change | Author |
|---|---|---|---|
| v0.1 | 2026-09-17 | First draft (amended the same day, before review, with what the module PRDs v0.2 needed: breaker probe endpoints B17, A12, H9; bad FHIR bundles selected by HIP id; healthy balance matched to the Finance PRD; a revoked document and a second DigiLocker account): four simulators, scenario contract table, BBPS stateful behaviour for crash scenarios A–D and the Healer, chaos driver, contract tests, request-journal assertions, simulated-versus-real table. | Shantanu Chaudhary (with Claude Code) |

> ℹ **What this document is not.** It does not describe the real DPI APIs. No sandbox credentials exist in portfolio mode (tracker → Decision Log, 2026-09-17), so nothing here has been verified against Sahamati, NPCI, ABDM or DigiLocker. The endpoint shapes are the ones the frozen specs already use; where this document adds one, it says so and marks it as the FamilyLifeOS **gateway contract**, not as a fact about the DPI (AGENTS.md §6: do not invent DPI facts).

## Table of Contents

- **1. Scope and Principles**
- **2. Topology** — containers, ports, environment, directory layout
- **3. How a Test Selects a Scenario** — identifiers, `X-Simulate-*` headers, and who may send them
- **4. Stateful Behaviour** — BBPS payment state machine, idempotency, the status API, AA consent approval
- **5. Scenario Contract** — the table stubs are generated from
- **6. Response Payloads** — canonical bodies per endpoint
- **7. Latency and Chaos Mode**
- **8. Contract Tests and Request-Journal Assertions**
- **9. Simulated versus Real**
- **10. Work Split and Definition of Done**
- **11. Open Issues**
- **12. Q&A**

---

## 1. Scope and Principles

### 1.1 What this spec owns

- The four simulators the two portfolio slices need: **AA** (balance fetch, consent status), **BBPS** (bill fetch, payment, payment status), **ABHA** (consent request, prescription fetch), **DigiLocker** (authorisation, issued-document list, document fetch).
- The **scenario contract** (§5): for every behaviour the application must survive, one row naming the stub file, the trigger, the response and the test that consumes it. Gemini generates stub JSON from this table (WP-18 for AA and BBPS, WP-34 for ABHA and DigiLocker); a stub that is not in the table does not get written.
- The stateful behaviour the Financial Transaction Safety crash scenarios and the Healer need (FTS §4.5, §6.4).
- Chaos mode (RB §9.4) and the contract tests (RB §9.5), made implementable.

### 1.2 What it does not own

- Rate-limit budgets, circuit-breaker thresholds and backoff: Runbook (RB §2, §4, §8). The simulators only *produce* the 429s, 500s and delays those mechanisms react to.
- The DPI gateway's client code, retries and error mapping: RB and FTS §3.
- **ONDC and Bhashini.** Out of scope for the portfolio build (Roadmap §1.1). The Bhashini low-confidence stub in RB §9.3 stays where it is and is not extended here; ONDC has no stub.
- **Inbound DPI webhooks** (consent revoked on the AA app, ABDM callbacks). CM §9 specifies their verification; driving them from a simulator is parked until the threat model (§11, OI-3).

### 1.3 Principles

1. **The application cannot tell.** The DPI gateway talks to a base URL. In development that URL is a simulator; nothing else in the application knows. No `if simulator:` branches outside the gateway's header forwarding rule (§3.2) and the UI banner (§2.3).
2. **Every behaviour is a named scenario with a test.** No stub exists without a row in §5, and no row exists without a consuming test.
3. **Deterministic by default, random only on request.** Scenarios are selected by identifiers or headers, never by chance. Randomness lives only in chaos mode, and chaos mode is seeded.
4. **Vanilla WireMock.** No custom Java extensions, no community state extension. The cost is that stateful scenarios are global per simulator and tests that use them reset state first and do not run in parallel against the same simulator (§4.4). That cost is accepted for a solo-founder build (AGENTS.md §4 item 36).
5. **Synthetic data only.** Every identifier, amount, name and document in a stub is invented. The repository is public.
6. **Say what is fake.** §9 lists every place the simulator is simpler than the real thing. The portfolio write-up reuses that table verbatim (GTM Plan §7).

---

## 2. Topology

### 2.1 Containers

One WireMock container per DPI, so that scenario state, chaos and resets are independent.

| Service | Compose name | Host port | Container port | Base URL env var (read by the DPI gateway) |
|---|---|---|---|---|
| Account Aggregator | `sim-aa` | 8101 | 8080 | `AA_BASE_URL` |
| BBPS | `sim-bbps` | 8102 | 8080 | `BBPS_BASE_URL` |
| ABHA / ABDM | `sim-abha` | 8103 | 8080 | `ABHA_BASE_URL` |
| DigiLocker | `sim-digilocker` | 8104 | 8080 | `DIGILOCKER_BASE_URL` |
| Chaos driver (optional) | `sim-chaos` | — | — | reads `CHAOS_MODE`, `CHAOS_SEED` |

- Image: `wiremock/wiremock`, pinned to an exact 3.x tag in `compose.yml` (WP-17 picks the tag and records it in `Development_Environment_Setup.md`). Started with `--global-response-templating --disable-banner`.
- The Build Gate needs only `sim-aa` and `sim-bbps` (tracker → Phase 1 Build Gate). `sim-abha` and `sim-digilocker` arrive in Phase 3 (WP-34) and sit behind the Compose profile `phase3` until then.
- Inside the Compose network the gateway uses `http://sim-bbps:8080` and so on; host ports exist for tests run from the host and for manual poking.

### 2.2 Directory layout

```text
wiremock/
├── aa/
│   ├── mappings/          # one JSON file per §5 row, named exactly as the row says
│   ├── __files/           # response bodies too large to inline
│   └── schemas/           # JSON Schema per endpoint: the gateway contract (§8.1)
├── bbps/        (same three folders)
├── abha/        (same; __files/ holds the synthetic FHIR bundles)
├── digilocker/  (same)
├── chaos/                 # failure stubs the chaos driver switches on and off (§7.2)
└── chaos_config.yaml      # RB §9.4, unchanged in shape
tools/sim_chaos.py         # the chaos driver (§7.2)
tests/dpi_contracts/       # §8.1
tests/fixtures/simulators.py   # reset, scenario and journal helpers (§8.2)
```

RB §9 shows stub files directly under `wiremock/mappings/`. With one container per DPI they move one level down (`wiremock/aa/mappings/aa_rate_limit.json`); file names and contents are unchanged. This is a layout detail, not a change to the frozen runbook, and RB's next revision should adopt the path.

### 2.3 Environment

| Variable | Meaning | Default |
|---|---|---|
| `SIMULATOR_MODE` | `true` when the base URLs point at simulators. Turns on the UI's permanent "SIMULATOR" banner and permits the gateway to forward `X-Simulate-*` headers (§3.2). Must be `false` in any deployment that talks to a real DPI; the application refuses to start if it is `true` and a base URL is not a simulator host. | `true` in Compose |
| `SIM_LATENCY` | `off`, `realistic` (§7.1) | `off` in CI, `realistic` in the demo |
| `CHAOS_MODE` | `true` starts the chaos driver's loop | `false` |
| `CHAOS_SEED` | Seed for the chaos driver's random generator; logged at start | `20260917` |

---

## 3. How a Test Selects a Scenario

Two mechanisms, for two kinds of test.

### 3.1 Identifiers (end-to-end tests, the demo, manual use)

The scenario is chosen by a **value the application sends anyway**: the biller id, the AA consent handle, the ABHA address, the DigiLocker document type. An end-to-end test or a demo therefore needs no test-only plumbing: Priya paying `BESCOM_KA_001` succeeds; a biller linked as `SIM_PENDING_001` stays pending first. Reserved prefixes:

| Prefix | Used in | Example |
|---|---|---|
| `SIM_` | BBPS `biller_id` | `SIM_FAILED_001` |
| `SIM-AA-` | AA `consentHandle` | `SIM-AA-LOWBAL` |
| `SIM-HIP-` | ABHA `hip_id` in the health-information request | `SIM-HIP-PARTIAL` |
| `SIM_` | DigiLocker `doctype` | `SIM_EXPIRED_DL` |

Identifiers without a reserved prefix get the happy path. The reference biller is `BESCOM_KA_001` (FTS §2.3); the Finance PRD's other linked billers (Airtel, BWSSB) get ids of the same form when its fixtures are written, and the seed family's consent handles (DM §8) map to healthy balances.

### 3.2 `X-Simulate-*` headers (integration and contract tests)

RB §9 selects failure stubs with request headers. That stays the canonical mechanism for tests below the end-to-end level, because a header can force a failure on an otherwise healthy identifier.

| Header | Values | Meaning |
|---|---|---|
| `X-Simulate-Rate-Limit` | `aa`, `bbps`, `abha` | 429 with `Retry-After` (RB §9.1) |
| `X-Simulate-Failures` | `bbps-circuit`, `aa-circuit`, `abha-circuit` | 500, repeatable, to open a breaker (RB §9.2) |
| `X-Simulate-Scenario` | any scenario name from §5 | Forces that row's response regardless of identifiers |
| `X-Simulate-Delay-Ms` | integer | Fixed delay before the normal response |

**Who may send them.** Only the DPI gateway, only when `SIMULATOR_MODE=true`, and only from a `simulate` directive carried in the test's request context. The API edge strips every inbound `X-Simulate-*` header, so a user or a browser can never set one. A unit test asserts both halves (headers stripped at the edge; headers not forwarded when `SIMULATOR_MODE=false`). Stubs matched by header carry WireMock `priority: 1`; identifier stubs `priority: 5`; happy-path catch-alls `priority: 10`.

---

## 4. Stateful Behaviour

### 4.1 Why state is needed

The Healer asks BBPS what happened to a payment (FTS §6.4) and must get different answers depending on whether the payment was ever submitted. Crash scenario B ("crash after Phase 1 COMMIT, before the BBPS call") requires `NOT_FOUND`; scenario C ("crash after BBPS SUCCESS, before Phase 2") requires `SUCCESS` for the same kind of question. A stateless stub cannot do both.

### 4.2 BBPS payment state machine

Implemented with WireMock **Scenarios**. Each behavioural class of biller has its own WireMock scenario name, so their states do not interfere.

```text
Scenario "bbps-pay-ok"  (billers without a SIM_ prefix)

  Started ──POST /payment──▶ Paid
     │                         │
     │ GET /payment/status     │ GET /payment/status      → 200 SUCCESS + transaction_ref_id
     ▼                         │ POST /payment (again)    → 200 SUCCESS, duplicate=true, same ref (FIN_004 path, FTS §5.5)
   200 NOT_FOUND               ▼
                             Paid

Scenario "bbps-pay-pending"  (biller SIM_PENDING_001)

  Started ──POST /payment──▶ Pending1 ──status──▶ Pending2 ──status──▶ Settled
   status → NOT_FOUND         status → PENDING      status → PENDING     status → SUCCESS

Scenario "bbps-pay-stuck"  (biller SIM_PENDING_FOREVER)

  Started ──POST /payment──▶ Stuck        status → PENDING, always
                                          (the 30-minute and 4-hour branches of FTS §6.4 are reached
                                           with the Healer's injected clock, not by waiting)
```

- `transaction_ref_id` is **derived from the idempotency key** by response templating (`BBPS-TXN-` followed by the first eight characters of the key, upper-cased), so `POST /payment` and `GET /payment/status` agree without the simulator remembering anything per key.
- `SIM_TIMEOUT_001` answers `POST /payment` after a 12-second delay (the client times out at 10 s, FTS §2.3) **and moves to `Paid`**. The application sees a timeout, the money has "moved", the Healer later finds `SUCCESS`. This is crash scenario C without killing a process, and it is also the FIN_001 path.
- `SIM_FAILED_001` answers `FAILED` with `debit_confirmed=false`; `SIM_FAILED_DEBIT_001` with `debit_confirmed=true` (FTS §4.4's admin-review branch).

### 4.3 How the crash scenarios use it

| FTS §4.5 scenario | Test injects | Simulator state needed | Healer sees |
|---|---|---|---|
| A — crash before Phase 1 COMMIT | `CRASH_AFTER=before_phase1` | none (no call is made) | nothing to reconcile; session rehydrates, user re-approves |
| B — crash after Phase 1, before BBPS call | `CRASH_AFTER=phase1_commit` | `bbps-pay-ok` in `Started` | `NOT_FOUND` → re-queue with the **original** key (within 24 h) |
| C — crash after BBPS SUCCESS, before Phase 2 | `CRASH_AFTER=bbps_success` | `bbps-pay-ok` in `Paid` | `SUCCESS` → `AUDIT_LOG_WRITE` |
| D — Phase 2 COMMIT fails | `CRASH_AFTER=phase2_begin` with a forced DB error | `Paid` | same as C |
| (lock) crash after Phase 2, before lock release | `CRASH_AFTER=phase2_commit` | `Paid` | stale lock released |

Scenario B has a second half worth a test of its own: after the Healer re-submits with the original key, the journal (§8.2) must show that both `POST /payment` requests carried the **same** `idempotency_key` (AGENTS.md §4 item 16).

### 4.4 The cost of global state

WireMock scenario state is per simulator, not per idempotency key. Consequences, accepted:

- Every test that touches a stateful scenario starts with `reset_simulator('bbps')` (§8.2), which resets scenarios and clears the journal.
- Stateful BBPS tests are marked `@pytest.mark.sim_serial` and run in one worker. Stateless tests run in parallel.
- Two payments to two different healthy billers inside one test share the `bbps-pay-ok` state. Tests that need two independent payments use one healthy biller and `SIM_PENDING_001`. If this becomes a real constraint, the fix is per-biller scenario names generated from a list, not a WireMock extension (OI-2).

### 4.5 AA consent approval

`POST /Consent` returns a handle; `GET /Consent/{handle}` answers `PENDING` once and `ACTIVE` afterwards (scenario `aa-consent-approve`), so the 30-second poll in CM §6.1.1 Step 6d is exercised with an injected clock. `SIM-AA-REJECT` goes `PENDING` → `REJECTED`; `SIM-AA-NEVER` stays `PENDING` so the 10-minute timeout path runs.

---

## 5. Scenario Contract

The table Gemini generates stubs from. **File** is relative to `wiremock/<dpi>/mappings/`. **Trigger** is what the stub matches in addition to method and URL. **Consumer** is the test module that must exist and fail without the stub. `H:` means a header from §3.2; `ID:` an identifier from §3.1.

### 5.1 BBPS (`sim-bbps`) — WP-18

| # | Scenario | File | Method and URL | Trigger | Response | Consumer |
|---|---|---|---|---|---|---|
| B1 | Bill fetch | `bbps_bill_fetch_ok.json` | `POST /bill/fetch` | any biller without `SIM_` | 200, §6.1 body, `due_paise` by biller (BESCOM 284700) | `tests/integration/test_finance_pay_bill.py` |
| B2 | No bill due | `bbps_bill_fetch_none.json` | `POST /bill/fetch` | `ID: SIM_NOBILL_001` | 200, `status: NO_BILL_DUE` | same |
| B3 | Unknown biller | `bbps_bill_fetch_unknown.json` | `POST /bill/fetch` | `ID: SIM_UNKNOWN_001` | 404, `errorCode: BILLER_NOT_FOUND` | same |
| B4 | Pay, success | `bbps_pay_ok.json` | `POST /payment` | scenario `bbps-pay-ok`, state `Started` | 200 `SUCCESS`, ref from key; → `Paid` | `test_finance_pay_bill.py`, e2e "Priya pays BESCOM bill" |
| B5 | Pay, duplicate key | `bbps_pay_duplicate.json` | `POST /payment` | `bbps-pay-ok`, state `Paid` | 200 `SUCCESS`, `duplicate: true`, same ref | `tests/integration/test_idempotency.py` |
| B6 | Pay, pending | `bbps_pay_pending.json` | `POST /payment` | `ID: SIM_PENDING_001` | 200 `PENDING`; → `Pending1` | `tests/crash_scenarios/test_pending.py` |
| B7 | Pay, stuck pending | `bbps_pay_stuck.json` | `POST /payment` | `ID: SIM_PENDING_FOREVER` | 200 `PENDING`; → `Stuck` | `tests/integration/test_healer_escalation.py` |
| B8 | Pay, failed | `bbps_pay_failed.json` | `POST /payment` | `ID: SIM_FAILED_001` | 200 `FAILED`, `debit_confirmed: false`, `bbps_error_code: INSUFFICIENT_FUNDS` | `test_finance_pay_bill.py` |
| B9 | Pay, failed after debit | `bbps_pay_failed_debit.json` | `POST /payment` | `ID: SIM_FAILED_DEBIT_001` | 200 `FAILED`, `debit_confirmed: true` | same |
| B10 | Pay, timeout then paid | `bbps_pay_timeout.json` | `POST /payment` | `ID: SIM_TIMEOUT_001` | 12 000 ms delay, then B4's body; → `Paid` | `tests/crash_scenarios/test_scenario_c.py` |
| B11 | Status, not found | `bbps_status_not_found.json` | `GET /payment/status` | state `Started` of the matching scenario | 200 `NOT_FOUND` | `tests/crash_scenarios/test_scenario_b.py` |
| B12 | Status, success | `bbps_status_success.json` | `GET /payment/status` | state `Paid` or `Settled` | 200 `SUCCESS` + ref | `test_scenario_c.py`, `test_scenario_d.py` |
| B13 | Status, pending | `bbps_status_pending.json` | `GET /payment/status` | states `Pending1`, `Pending2`, `Stuck` | 200 `PENDING` | `test_pending.py` |
| B14 | Rate limited | `bbps_rate_limit.json` | any | `H: X-Simulate-Rate-Limit: bbps` | 429, `Retry-After: 3600` | `tests/integration/test_gateway_bbps.py` |
| B15 | Biller down | `bbps_consecutive_failures.json` (RB §9.2, unchanged) | `POST /payment` | `H: X-Simulate-Failures: bbps-circuit` | 500 `BILLER_UNREACHABLE` | `tests/dpi_contracts/test_bbps.py`, breaker test |
| B16 | Status API down | `bbps_status_unreachable.json` | `GET /payment/status` | `H: X-Simulate-Failures: bbps-circuit` | 503 | `tests/integration/test_healer_poll_count.py` |
| B17 | Breaker probe | `bbps_biller_info.json` | `POST /biller/fetch` | — | 200, biller name and category; no bill, no money (RB §8.3: the half-open probe) | `tests/integration/test_gateway_bbps.py` |

The tracker's Build Gate list ("SUCCESS, FAILED, PENDING, NOT_FOUND, 429, timeout") is B4, B8, B6/B13, B11, B14 and B10.

### 5.2 Account Aggregator (`sim-aa`) — WP-18

| # | Scenario | File | Method and URL | Trigger | Response | Consumer |
|---|---|---|---|---|---|---|
| A1 | Consent request | `aa_consent_create.json` | `POST /Consent` | — | 200, `consentHandle` (templated UUID) | `tests/integration/test_consent_aa.py` |
| A2 | Consent pending → active | `aa_consent_status_*.json` (2 files) | `GET /Consent/{handle}` | scenario `aa-consent-approve` | `PENDING`, then `ACTIVE` | same |
| A3 | Consent rejected | `aa_consent_rejected.json` | `GET /Consent/{handle}` | `ID: SIM-AA-REJECT` | `REJECTED` | same |
| A4 | Consent never approved | `aa_consent_never.json` | `GET /Consent/{handle}` | `ID: SIM-AA-NEVER` | `PENDING` always | same (timeout path) |
| A5 | Consent revoked | `aa_consent_revoked.json` | `GET /Consent/{handle}` | `ID: SIM-AA-REVOKED` | `REVOKED` | `tests/integration/test_consent_reverify.py` (gate G5 fails safe) |
| A6 | FI request | `aa_fi_request.json` | `POST /FI/request` | — | 200, `sessionId` | `test_gateway_aa.py` |
| A7 | FI fetch, healthy balance | `aa_fi_fetch_ok.json` | `GET /FI/fetch/{sessionId}` | default | 200, §6.2 body, balance 1 825 040 paise (the figure in Finance PRD Scenario 1) | `test_finance_pay_bill.py` (gate G3 passes) |
| A8 | FI fetch, low balance | `aa_fi_fetch_low.json` | `GET /FI/fetch/{sessionId}` | `ID: SIM-AA-LOWBAL` handle on the preceding request | balance 100 000 paise (below 284 700 + 5 000 buffer) | same (G3 blocks, FIN code per FTS §10) |
| A9 | FI fetch, not ready | `aa_fi_fetch_wait.json` | `GET /FI/fetch/{sessionId}` | `ID: SIM-AA-SLOW` | 202 twice, then A7 | `test_gateway_aa.py` (30 s poll limit with injected clock) |
| A10 | Rate limited | `aa_rate_limit.json` (RB §9.1, unchanged) | `POST /FI/request` | `H: X-Simulate-Rate-Limit: aa` | 429, `Retry-After: 1800` | `tests/dpi_contracts/test_aa.py` |
| A11 | AA down | `aa_consecutive_failures.json` | `POST /FI/request` | `H: X-Simulate-Failures: aa-circuit` | 500 | breaker test; degradation script (MC §4.7) |
| A12 | Breaker probe | `aa_consent_status_probe.json` | `GET /Consent/status` | — | 200, `status: UP` (RB §8.3: a status check, not an FI fetch) | `test_gateway_aa.py` |

Because `GET /FI/fetch/{sessionId}` does not carry the consent handle, A8 and A9 are selected by a `sessionId` prefix that A6's variants return for the reserved handles (`SIM-AA-LOWBAL` → `sessionId` beginning `low-`).

### 5.3 ABHA (`sim-abha`) — WP-34

| # | Scenario | File | Method and URL | Trigger | Response | Consumer |
|---|---|---|---|---|---|---|
| H1 | Consent request | `abha_consent_init.json` | `POST /v0.5/consent-requests/init` | — | 202, `id` | `tests/integration/test_consent_abha.py` |
| H2 | Consent granted | `abha_consent_status_*.json` | `GET /sim/consent-requests/{id}` | scenario `abha-consent-approve` | `REQUESTED`, then `GRANTED` + `artefact_id` | same |
| H3 | Health-information request | `abha_hi_request.json` | `POST /v0.5/health-information/cm/request` | — | 202, `transaction_id` | `tests/integration/test_health_prescription.py` |
| H4 | Bundle, clean | `abha_hi_bundle_ok.json` + `__files/nani_prescription.json` | `GET /sim/health-information/{transaction_id}` | default | 200, FHIR R4 Bundle: 2 MedicationRequest, 1 Observation | same; e2e "Nani's medication reminder" |
| H5 | Bundle, partial | `abha_hi_bundle_partial.json` + `__files/nani_prescription_partial.json` | same | `ID: hip_id SIM-HIP-PARTIAL` in the H3 request (the `transaction_id` it returns begins `partial-`) | 200, one MedicationRequest missing `dosageInstruction` | `test_health_fhir_partial.py` (RB §5.3: partial data, no breaker trip) |
| H6 | Bundle, malformed | `abha_hi_bundle_malformed.json` | same | `ID: hip_id SIM-HIP-MALFORMED` (`transaction_id` begins `malformed-`) | 200, RB §9.4's malformed body | same (`parse_quality = FAILED`) |
| H7 | Consent budget exhausted | `abha_rate_limit.json` | `POST /v0.5/consent-requests/init` | `H: X-Simulate-Rate-Limit: abha` | 429 | `test_gateway_abha.py` |
| H8 | ABDM down | `abha_consecutive_failures.json` | any `/v0.5/*` | `H: X-Simulate-Failures: abha-circuit` | 500 | breaker test (3 failures → 20 min, RB §8.2); degraded mode (RB §5.4) |
| H9 | Breaker probe | `abha_hip_read.json` | `GET /health/hip/read` | — | 200, one HIP entry `SIM-HIP-001` (RB §8.3: HIP discovery, not a consent grant) | `test_gateway_abha.py` |

`/sim/...` paths are simulator conveniences that replace ABDM's asynchronous callbacks with polling (§9).

### 5.4 DigiLocker (`sim-digilocker`) — WP-34

| # | Scenario | File | Method and URL | Trigger | Response | Consumer |
|---|---|---|---|---|---|---|
| D1 | Authorise | `dl_authorize.json` | `GET /public/oauth2/1/authorize` | — | 302 to `redirect_uri` with `code=sim-code-…` and the caller's `state` | `tests/integration/test_vault_link.py` |
| D2 | Token | `dl_token.json` | `POST /public/oauth2/1/token` | — | 200, synthetic `access_token`, `refresh_token`, `expires_in: 3600` | same |
| D3 | Token refresh refused | `dl_token_revoked.json` | `POST /public/oauth2/1/token` | `refresh_token` beginning `sim-revoked-` | 401 | `test_consent_reverify.py` (Vault path) |
| D4 | Issued documents | `dl_issued_list.json` | `GET /public/oauth2/2/files/issued` | bearer token's account part (`sim-token-<seed user uuid>-…`; the account is chosen at D1 with the simulator-only query parameter `sim_account`) | 200, §6.4 list for that account. Ravi's account: driving licence, vehicle RC, PAN, birth certificate (Arjun). Priya's account: vehicle RC, insurance policy, PAN. An adult's documents come from that adult's own account (Vault PRD v0.2 §4.2) | `test_vault_link.py`, `test_vault_show.py` |
| D5 | Document expiring | within D4 | — | `doctype: SIM_EXPIRING_DL` | licence with `valid_to` 20 days ahead of the injected clock | `test_vault_expiry.py` (30- and 7-day reminder defaults) |
| D6 | Document fetch | `dl_file.json` + `__files/synthetic.pdf` | `GET /public/oauth2/1/file/{uri}` | — | 200, a one-page synthetic PDF | `test_vault_show.py` (bytes never persisted: asserted) |
| D7 | DigiLocker down | `dl_consecutive_failures.json` | any | `H: X-Simulate-Failures: …` with value `digilocker-circuit` | 500 | breaker test (Vault PRD OI-4 borrows the AA values) |
| D8 | Document revoked | `dl_file_revoked.json` | `GET /public/oauth2/1/file/{uri}` | `ID: uri sim-revoked-0001` | 410, `error: document_revoked` | `test_vault_show.py` (VAULT_005; local metadata updated, DigiLocker wins) |

---

## 6. Response Payloads

Canonical bodies. Field names follow the frozen specs where the specs show a payload; everything else is the gateway contract and is validated by the schemas in `wiremock/<dpi>/schemas/` (§8.1). Money is integer paise (AGENTS.md §5).

### 6.1 BBPS

```jsonc
// POST /bill/fetch  → 200
{ "status": "BILL_AVAILABLE", "biller_id": "BESCOM_KA_001",
  "due_paise": 284700, "bill_ref": "KA-2026-09-8812", "due_date": "2026-09-25" }

// POST /payment  (request, per FTS §2.3)
{ "biller_id": "BESCOM_KA_001", "amount_paise": 284700, "upi_vpa": "sharma.family@simbank",
  "idempotency_key": "550e8400-e29b-41d4-a716-446655440000",
  "customer_params": { "account_no": "SIM-CONSUMER-0001" } }

// POST /payment  → 200
{ "status": "SUCCESS", "transaction_ref_id": "BBPS-TXN-550E8400",
  "idempotency_key": "550e8400-e29b-41d4-a716-446655440000", "duplicate": false }

// POST /payment  → 200 (failed)
{ "status": "FAILED", "bbps_error_code": "INSUFFICIENT_FUNDS", "debit_confirmed": false }

// GET /payment/status?idempotency_key=…&transaction_ref_id=…  → 200
{ "status": "SUCCESS | FAILED | PENDING | NOT_FOUND", "transaction_ref_id": "BBPS-TXN-550E8400" }
```

`/bill/fetch` and `/payment/status` are not shown in FTS; their shapes are fixed here as the gateway contract. FTS names the status call only as `GET_BBPS_STATUS(idempotency_key, transaction_ref_id)`.

### 6.2 Account Aggregator

```jsonc
// GET /FI/fetch/{sessionId}  → 200   (plain JSON; the real payload is encrypted, §9)
{ "sessionId": "ok-7f3a…", "status": "READY",
  "accounts": [ { "fip_id": "SIMBANK", "fi_type": "DEPOSIT", "masked_account": "XXXX0001",
                  "balance_paise": 5000000, "as_of": "{{now}}" } ] }
```

### 6.3 ABHA

`__files/nani_prescription.json` is a FHIR R4 `Bundle` of type `collection` with two `MedicationRequest` resources (a twice-daily and a once-daily medicine, synthetic names from a published generic list, `dosageInstruction.timing` filled) and one `Observation`. The patient reference is `nani.sharma@sbx`, the synthetic ABHA address the Health PRD uses for Nani (no reserved prefix, so she gets the happy path). A second hospital sending bad data for the same patient is the realistic case, which is why H5 and H6 are selected by HIP id and not by patient. No real person, practitioner or hospital appears; the HIP is `SIM-HIP-001` "Simulated Clinic".

### 6.4 DigiLocker

```jsonc
// GET /public/oauth2/2/files/issued  → 200
{ "items": [
  { "uri": "sim-dl-0001", "doctype": "DRVLC", "name": "Driving Licence", "issuer": "SIM-TRANSPORT",
    "holder_ref": "b0000000-0000-4000-8000-000000000001", "valid_to": "2031-03-14" },
  { "uri": "sim-rc-0001", "doctype": "RVCER", "name": "Vehicle Registration", "issuer": "SIM-TRANSPORT",
    "holder_ref": "b0000000-0000-4000-8000-000000000001", "valid_to": "2035-08-01" } ] }
```

`holder_ref` is a simulator convenience that ties a document to a seed user (DM §8) without putting a name in the stub.

---

## 7. Latency and Chaos Mode

### 7.1 Latency

`SIM_LATENCY=realistic` applies a log-normal delay per simulator through WireMock's global settings at start-up: AA median 600 ms, BBPS median 900 ms, ABHA median 1 200 ms, DigiLocker median 700 ms, sigma 0.4 for all. These are **plausible figures chosen for the demo, not measurements**; they exist so the P95 numbers in Roadmap §8 are not flattered by a zero-latency network. `off` applies none and is what CI uses.

### 7.2 Chaos mode

RB §9.4 describes chaos as a YAML file with failure rates. WireMock has no per-request failure probability, so the file is interpreted by a small driver, `tools/sim_chaos.py` (standard library plus PyYAML as a dev dependency):

1. Read `wiremock/chaos_config.yaml` (shape unchanged from RB §9.4) and seed a random generator with `CHAOS_SEED`.
2. Once a second, for each enabled scenario, draw a number; with probability `failure_rate` **add** the scenario's failure stub (from `wiremock/chaos/`, priority 0) to the matching simulator through `POST /__admin/mappings`, otherwise **remove** it.
3. Log every switch with a timestamp, so a failed chaos run can be replayed with the same seed.

Over a run, the share of seconds in which a failure stub is active approaches `failure_rate`. That is a coarser model than per-request failure and is stated as such in §9. The chaos run (WP-41) passes when the application returns no 5xx of its own, every failure surfaces as a FIN or MOD code, and breakers open and close as RB §8 says (Roadmap §8, "Resilience score").

---

## 8. Contract Tests and Request-Journal Assertions

### 8.1 Contract tests (`tests/dpi_contracts/`)

RB §9.5 asks that stubs "match real DPI API schemas". Without sandbox access that cannot be proven, so the contract is defined as follows:

- Each endpoint has a JSON Schema under `wiremock/<dpi>/schemas/`, with a header comment giving its **provenance**: "from FTS §2.3", "from CM §6.1.1", or "gateway contract, this spec §6", and the date.
- Test 1: every stub response for that endpoint validates against the schema.
- Test 2: the gateway's Pydantic response model for that endpoint accepts every stub response and rejects a mutated one (a required field removed).
- Test 3: RB §9.5's three tests, as written.
- When a real sandbox becomes available (Roadmap §6), the schemas are the single thing to re-verify; stubs and models follow from them.

### 8.2 Helpers (`tests/fixtures/simulators.py`)

| Helper | Does |
|---|---|
| `reset_simulator(dpi)` | `POST /__admin/scenarios/reset` and `DELETE /__admin/requests` on that simulator |
| `set_scenario_state(dpi, scenario, state)` | `PUT /__admin/scenarios/{scenario}/state`; used to start a test in `Paid` without making a payment (crash scenario C) |
| `journal(dpi, method, url_pattern)` | `POST /__admin/requests/find`; returns the matching requests |
| `simulate(**headers)` | context manager that sets the `simulate` directive the gateway turns into `X-Simulate-*` headers (§3.2) |

### 8.3 Journal assertions every payment test makes

1. Exactly one `POST /payment` per idempotency key, unless the test is about re-submission, in which case **all** of them carry the same key (AGENTS.md §4 item 16).
2. The AA balance fetch (`POST /FI/request`) precedes `POST /payment` in time (gate order, AGENTS.md §4 item 18).
3. No request body sent to any simulator contains a seed user's name, phone number or email (a list in the fixture); only opaque identifiers and amounts leave the application.
4. When a gate fails, there is **no** `POST /payment` in the journal at all.

---

## 9. Simulated versus Real

| Area | Real DPI | Simulator | Why it is acceptable here |
|---|---|---|---|
| Access | Licensed entities only (FIU, BBPOU, HIU, DigiLocker partner) | Open HTTP on localhost | Portfolio mode; no licences (Decision Log) |
| BBPS API | Reached through a BBPOU's own API; shapes vary by provider | One invented REST shape (§6.1), based on FTS §2.3 | The gateway isolates the shape; a real BBPOU adapter replaces it |
| BBPS idempotency | Provider-specific; FTS assumes 24-hour dedup by key | Dedup by WireMock state, global per simulator | Tests reset state; the 24-hour boundary is tested with an injected clock in the Healer, not in the simulator |
| AA data | Encrypted FI payload (key exchange between FIU and FIP), signed requests, detached JWS | Plain JSON, no signatures | Cryptography belongs to the threat model and the real adapter; the flow (consent → request → session → fetch) is preserved |
| AA consent approval | User approves in an AA app | Status flips after one poll | The polling, timeout and rejection paths are all exercised |
| ABDM data flow | Asynchronous callbacks, encrypted FHIR bundles | Polling on `/sim/...` paths, plain FHIR | Same reasoning; the FHIR parsing and partial-parse handling are real |
| DigiLocker | Aadhaar OTP login, real OAuth consent screen, signed XML/PDF | Immediate redirect with a code; a synthetic PDF | The authorisation-code flow, token refresh and "bytes never stored" rule are real |
| Rate limits | Enforced by the network | Never enforced; 429 only when a test asks for it | The application's own budget tracker (RB §2) is the thing under test |
| Latency and failure | Whatever the day brings | Log-normal delay; chaos in one-second windows | Coarse but seeded and repeatable |
| Webhooks | Revocations and callbacks arrive signed | Not simulated yet (OI-3) | Verification code is specified (CM §9) and is a threat-model deliverable |
| Data | Real people | The Sharma family and invented identifiers | Public repository |

---

## 10. Work Split and Definition of Done

| Work | Owner → Reviewer | Package |
|---|---|---|
| This spec | Claude → Codex | WP-12 |
| Compose services for `sim-aa`, `sim-bbps` (then `sim-abha`, `sim-digilocker`) | Gemini drafts → Codex | WP-17 (WP-34) |
| Stub JSON, `__files/`, schemas for AA and BBPS from §5.1–5.2, §6 | Gemini → Codex | WP-18 |
| Stub JSON, FHIR bundles, schemas for ABHA and DigiLocker from §5.3–5.4 | Gemini → Codex | WP-34 |
| `tests/fixtures/simulators.py`, contract tests, journal assertions | Codex → Claude | WP-18 review, WP-26, WP-28 |
| `tools/sim_chaos.py`, `wiremock/chaos/`, chaos run | Codex → Claude | WP-41 |

Done for a stub package means: every row of the relevant §5 table has its file with the exact name; every file's response validates against its schema; `docker compose up sim-aa sim-bbps` starts clean; the consumer tests named in the table exist (they may be `xfail` until the code under test exists, but they must reference the stub); no file contains a real-looking phone number, Aadhaar number, VPA at a real bank handle, or account number (Execution Plan §7.1).

Gemini may delegate stub files to the local model (`.agents/workflows/delegate-to-local.md`): a row of §5 plus §6's body is exactly the kind of bounded, verifiable task that workflow allows, and the schema validation is the verifier.

---

## 11. Open Issues

| # | Issue | Severity | Path |
|---|---|---|---|
| OI-1 | FTS §2.3's payment request carries `upi_vpa` and `customer_params.account_no`. AGENTS.md §4 item 9 forbids storing UPI IDs and account numbers. The simulator accepts synthetic values, but where the real values would come from at call time (a vault reference resolved inside the gateway?) is unspecified. Related: Finance PRD OI-4. | MEDIUM | Security_Threat_Model.md; candidate inconsistency-register item once the threat model is drafted |
| OI-2 | Scenario state is global per simulator (§4.4). Two independent healthy payments in one test share state. | LOW | Generate per-biller scenario names if a test needs it; no extension |
| OI-3 | Inbound webhooks (AA revocation, ABDM callbacks) are not simulated. CONSENT_REVERIFY covers revocation by polling (A5), so the payment path is safe without them. | MEDIUM | With the threat model (WP-42): a signed-webhook sender in `tests/fixtures/` using a test key |
| OI-4 | `/bill/fetch`, `/payment/status`, the DigiLocker `issued` list and the `/sim/...` ABHA paths are defined here, not in a frozen spec. | LOW | Codex review confirms them as the gateway contract; FTS and CM reference this spec at their next revision |
| OI-5 | RB §9's stub paths (`wiremock/mappings/…`) differ from §2.2's per-DPI folders. | LOW | RB v1.3 adopts the per-DPI path; no behavioural change |
| OI-6 | Latency medians (§7.1) are chosen, not measured. | LOW | Replace with measured values if a sandbox ever becomes available |

---

## 12. Q&A

| Asked by | Question | Answer |
|---|---|---|
| Engineering | Why WireMock and not a small FastAPI fake, which could keep per-key state? | RB §9 (frozen) already commits to WireMock, the stubs are declarative JSON a routine agent can generate and a reviewer can read, and the admin API gives the request journal for free. A Python fake would be a second application to test. The global-state cost (§4.4) is small at this scale. |
| Engineering | Why both identifiers and headers? | End-to-end tests and the demo should not need test-only plumbing, so they use identifiers. Lower-level tests need to force a failure on a healthy identifier, which only a header can do, and RB §9 already defines headers. |
| Security | Can a user trigger a simulated failure in the demo by sending `X-Simulate-Failures`? | No. The API edge strips `X-Simulate-*`; only the gateway adds them, from a directive that exists only in test contexts (§3.2). Both halves have tests. |
| Product | The demo shows a payment succeeding. How does a viewer know it is fake? | `SIMULATOR_MODE=true` puts a permanent "SIMULATOR" banner in the UI (§2.3), and the write-up carries the §9 table. |
| Reviewer | How is crash scenario C tested without killing the server at the right microsecond? | Two ways: the `CRASH_AFTER=bbps_success` hook (Roadmap §5) for the literal crash, and `SIM_TIMEOUT_001` (B10), where the simulator "pays" and the client times out. Both leave the session in EXECUTION with money moved, which is the state the Healer must repair. |
| Reviewer | Does the simulator prove the DPI integration works? | No, and it does not claim to. It proves that the application's safety machinery (gates, idempotency, two-phase commit, the Healer, breakers, degradation) behaves correctly against the failure modes the specs enumerate. §9 says what would have to be redone against a real sandbox. |
