# Tech Spec: DPI Simulator Architecture

_WireMock simulators for Account Aggregator, BBPS, ABHA and DigiLocker: layout, scenario contract, stateful payment behaviour, chaos mode, contract tests, and an honest account of what is simulated_

> **Status:** DRAFT v0.2 — Codex's review of v0.1 (8 findings) applied; Codex's targeted re-review pending · **Author:** Shantanu Chaudhary (Lead Product Architect), drafted with Claude Code · **Last content change:** 2026-09-21
> **Priority:** P1. Execution Plan WP-12. The Build Gate's WireMock scenarios (tracker → Phase 1 Build Gate) and the stub-generation packages WP-18 and WP-34 depend on §5 of this document.
> **Written against:** Runbook_DPI_Rate_Limits v1.2 (frozen), Financial Transaction Safety v1.3, Consent Manager v1.4, Data Model v1.4 and Module Registry v1.2 (the last four are the WP-11 revision and await Codex's re-review; section references are re-checked at the freeze).
> **Cited elsewhere as:** Simulator spec, SIM §n.

## 0. Document Governance

| Version | Date | Description of Change | Author |
|---|---|---|---|
| v0.1 | 2026-09-17 | First draft (amended the same day, before review, with what the module PRDs v0.2 needed: breaker probe endpoints B17, A12, H9; bad FHIR bundles selected by HIP id; healthy balance matched to the Finance PRD; a revoked document and a second DigiLocker account): four simulators, scenario contract table, BBPS stateful behaviour for crash scenarios A–D and the Healer, chaos driver, contract tests, request-journal assertions, simulated-versus-real table. | Shantanu Chaudhary (with Claude Code) |
| v0.2 | 2026-09-21 | Codex review of PR #20, all 8 findings. (f1) BBPS payment state is bound to the **idempotency key**: fixtures install a small per-key WireMock scenario through the admin API, so key A replayed, key B unseen and two keys for one biller are all testable in one test; references carry the whole key (§4.2–4.4). (f2) `/payment/status` has a schema per outcome, a FAILED outcome, `executed_at`, and rules for key-only, ref-only and mismatched lookups (§6.1). (f3) What the revocation test does and does not prove is stated; new row A13, the provider refusing a revoked handle (§5.2, §11 OI-3). (f4) The normal prescription bundle holds prescriptions only; an over-broad bundle is its own negative scenario H10 (§5.3, §6.3). (f5) Business dates in stub bodies come from the test clock through fixtures, never from WireMock's `now` (§7.1). (f6) The scenario table is a complete generation contract: static files versus per-key templates, state guards, listed variants, one canonical balance, status-specific validation (§5, §8.1). (f7) Chaos stubs have stable ids and are cleaned up by reset; the seed reproduces fault windows, not request outcomes (§7.2, §8.2). (f8) Crash B asserts zero payment calls before the crash and exactly one after, with the persisted key (§4.3). OI-1 settled on Codex's recommendation: synthetic instrument values are materialised in memory by the simulator adapter, application storage holds opaque references (§6.1). Aligned with MR v1.2 `phase`. | Shantanu Chaudhary (with Claude Code; review by Codex) |

> ℹ **What this document is not.** It does not describe the real DPI APIs. No sandbox credentials exist in portfolio mode (tracker → Decision Log, 2026-09-17), so nothing here has been verified against Sahamati, NPCI, ABDM or DigiLocker. The endpoint shapes are the ones the frozen specs already use; where this document adds one, it says so and marks it as the FamilyLifeOS **gateway contract**, not as a fact about the DPI (AGENTS.md §6: do not invent DPI facts).

## Table of Contents

- **1. Scope and Principles**
- **2. Topology** — containers, ports, environment, directory layout
- **3. How a Test Selects a Scenario** — identifiers, `X-Simulate-*` headers, and who may send them
- **4. Stateful Behaviour** — key-bound BBPS payment state, idempotency, the status API, AA consent approval
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

**Who may send them.** Only the DPI gateway, only when `SIMULATOR_MODE=true`, and only from a `simulate` directive carried in the test's request context. The API edge strips every inbound `X-Simulate-*` header, so a user or a browser can never set one. Tests assert all of it: headers stripped at the edge; headers not forwarded when `SIMULATOR_MODE=false`; **no ordinary input can manufacture the directive** (a JSON body field, query parameter, cookie or entity value named `simulate` or `X-Simulate-*` is ignored; the directive is a server-side context variable that only the test harness sets); and with `SIMULATOR_MODE=false` the gateway drops every test directive, including `recovery`-unrelated ones such as forced delays, before building a request. Priorities, lowest number wins: chaos stubs 0; header stubs 1; **per-key stubs installed by fixtures 2, and their mismatch guard 3** (§4.2); identifier stubs 5; happy-path catch-alls 10.

---

## 4. Stateful Behaviour

### 4.1 Why state is needed

The Healer asks BBPS what happened to a payment (FTS §6.4) and must get different answers depending on whether the payment was ever submitted. Crash scenario B ("crash after Phase 1 COMMIT, before the BBPS call") requires `NOT_FOUND`; scenario C ("crash after BBPS SUCCESS, before Phase 2") requires `SUCCESS` for the same kind of question. A stateless stub cannot do both.

### 4.2 BBPS payment state is bound to the idempotency key

v0.1 kept one WireMock scenario per *kind of biller*. After key A had paid, the simulator was simply "Paid": an unseen key B got a duplicate SUCCESS, and a status query for B reported money moved that was never sent. Resetting between tests hid that instead of testing it, and the one property the simulator exists to prove (one key, one payment; another key, another payment) could not be asserted. v0.2 binds state to the key, still with vanilla WireMock.

**Mechanism.** WireMock scenarios are named state machines, and a name can be anything. The fixture `register_payment(key, plan)` (§8.2) creates, through `POST /__admin/mappings`, a handful of mappings that belong to a scenario named `pay-<key>` and match **only that key**: `POST /payment` with body `$.idempotency_key == <key>`, and `GET /payment/status` with query `idempotency_key == <key>` or `transaction_ref_id == <ref of that key>`. Every such mapping carries `metadata: {"dynamic": true, "key": "<key>"}` and a deterministic id (`uuid5(NAMESPACE, key + ":" + step)`), so registering twice is idempotent and cleanup is one call (§8.2). WireMock documents scenarios as named state machines (wiremock.org, "Stateful behaviour"); it offers no per-key store, and this design does not pretend it does: there is one tiny scenario per key.

**How the test knows the key.** The application generates the key (FTS §5.1). The idempotency-key factory is an injected seam (Test Automation Strategy §4); integration and crash tests give it a fixed sequence, so the test knows key A and key B before it starts, registers a plan for each, and then drives the application.

**Plans** (what the per-key scenario does):

```text
plan "ok"            Started ──POST──▶ Paid
                     POST in Paid      → 200 SUCCESS, duplicate=true, same ref, same executed_at   (FIN_004 path, FTS §5.5)
                     status: Started → NOT_FOUND · Paid → SUCCESS

plan "pending"       Started ──POST──▶ Pending1 ──status──▶ Pending2 ──status──▶ Settled
                     POST in Pending1/Pending2/Settled → 200 with the CURRENT status, duplicate=true; never moves the state back
                     status: NOT_FOUND → PENDING → PENDING → SUCCESS

plan "stuck"         Started ──POST──▶ Stuck          status → PENDING, always; POST again → PENDING, duplicate=true
                     (the 30-minute and 4-hour branches of FTS §6.4 are reached with the Healer's injected clock, not by waiting)

plan "timeout_paid"  Started ──POST (12 000 ms delay, client gives up at 10 s)──▶ Paid        status → SUCCESS with ref and executed_at
plan "failed"        Started ──POST──▶ Failed         200 FAILED, debit_confirmed=false       status → FAILED, debit_confirmed=false
plan "failed_debit"  Started ──POST──▶ FailedDebit    200 FAILED, debit_confirmed=true        status → FAILED, debit_confirmed=true
plan "never"         (no POST mapping at all)         status → NOT_FOUND, always              (crash scenario B before recovery)
```

- **`transaction_ref_id` carries the whole key:** `BBPS-TXN-` + the key's 32 hex digits, upper-cased (41 characters; `supervisor_sessions.bbps_transaction_ref_id` is VARCHAR(100)). v0.1 used the first eight characters, which two keys can share.
- **Unregistered keys** fall through to the static, stateless catch-alls (priority 10): `POST /payment` → 200 SUCCESS with the derived ref, `duplicate: false`; `GET /payment/status` → NOT_FOUND. That is enough for the demo and for the end-to-end happy path, which never asks for a status, and it is deliberately **not** enough for any test about idempotency, recovery or the Healer: those must register their keys, and `journal_assertions` (§8.3) fails a test that reaches the status endpoint with an unregistered key.
- **Biller identifiers still choose the plan in end-to-end tests and the demo** (§3.1): the e2e harness runs the application with the seeded key factory, reads the biller of the scenario under test, and registers the matching plan (`SIM_PENDING_001` → "pending", `SIM_TIMEOUT_001` → "timeout_paid", and so on) for the next key before the user flow starts. A biller with a `SIM_` prefix and no registered key gets a 500 `SIM_KEY_NOT_REGISTERED`, so a forgotten registration is loud.
- **Mismatch guard (priority 3), one per registered key:** a status request that names this key together with a `transaction_ref_id` that is not this key's ref gets 400 `KEY_REF_MISMATCH`. Without it the request would fall through to the catch-all NOT_FOUND and invite a resubmission.

### 4.3 How the crash scenarios use it

| FTS §4.5 scenario | Test injects | Registered plan for the session's key | Healer sees |
|---|---|---|---|
| A — crash before Phase 1 COMMIT | process killed at `before_phase1` | none needed (no call is made) | nothing to reconcile; session rehydrates, user re-approves; journal: no `POST /payment` |
| B — crash after Phase 1, before BBPS call | killed at `phase1_commit` | "ok" | `NOT_FOUND` (state Started) → resubmission with the **original** key (FTS v1.3 §4.5, §6.4) → Paid |
| C — crash after BBPS SUCCESS, before Phase 2 | killed at `bbps_success` | "ok" | `SUCCESS` → `reconcile()` → `AUDIT_LOG_WRITE` |
| D — Phase 2 COMMIT fails | forced DB error at `phase2_begin` | "ok" | same as C |
| (lock) crash after Phase 2, before lock release | killed at `phase2_commit` | "ok" | stale lock released |

**Scenario B's journal assertion (v0.2).** The crash is *before* the first payment call, so v0.1's "both `POST /payment` requests carried the same key" rewarded a call that must never happen. Assert instead: **zero** `POST /payment` for the key before the crash; after recovery **exactly one**, carrying the session's persisted key; the module's ledger row was `pending` and the dispatch carried `recovery: {mode: resubmit}` (MR v1.2 §6.4). Two same-key POSTs are a different test, `test_idempotency.py`: key A paid, key A sent again → `duplicate: true`, same ref, same `executed_at`; key B, unseen, same biller → a fresh SUCCESS with a different ref; status(B) before B is sent → NOT_FOUND. All in one test, no reset in between.

### 4.4 What is still global

- The AA and ABHA **consent-approval** scenarios (§4.5, H2) and A9's slow fetch are global per simulator. Tests that use them are marked `@pytest.mark.sim_serial`, run in a separate pytest invocation that owns the simulators exclusively (Test Automation Strategy §4), and start with `reset_simulator(dpi)`.
- BBPS payment tests no longer need that: each works on its own keys and may run in parallel with others. They clean up with `unregister_payment(key)` or rely on the session-level reset.
- `reset_simulator(dpi)` resets scenarios, clears the journal **and removes every mapping whose metadata says `dynamic` or `chaos`** (§8.2), returning the simulator to the files on disk.

### 4.5 AA consent approval

`POST /Consent` returns a handle; `GET /Consent/{handle}` answers `PENDING` once and `ACTIVE` afterwards (scenario `aa-consent-approve`), so the 30-second poll in CM §6.1.1 Step 6d is exercised with an injected clock. `SIM-AA-REJECT` goes `PENDING` → `REJECTED`; `SIM-AA-NEVER` stays `PENDING` so the 10-minute timeout path runs.

---

## 5. Scenario Contract

The table Gemini generates stubs from, with no design choices left to the generator. Two kinds of row: **static** rows are files under `wiremock/<dpi>/mappings/`, loaded at start-up; **template** rows (marked ⓣ) are JSON templates under `wiremock/<dpi>/templates/` that `register_payment` fills in per key (§4.2) and installs through the admin API. A template never exists as a live mapping on disk. **File** is relative to the folder of its kind. **Trigger** is what the stub matches in addition to method and URL. **Consumer** is the test module that must exist and fail without the stub. `H:` means a header from §3.2; `ID:` an identifier from §3.1.

### 5.1 BBPS (`sim-bbps`) — WP-18

| # | Scenario | File | Method and URL | Trigger | Response | Consumer |
|---|---|---|---|---|---|---|
| B1 | Bill fetch | `bbps_bill_fetch_ok.json` | `POST /bill/fetch` | any biller without `SIM_` | 200, §6.1 body, `due_paise` by biller (BESCOM 284700) | `tests/integration/test_finance_pay_bill.py` |
| B2 | No bill due | `bbps_bill_fetch_none.json` | `POST /bill/fetch` | `ID: SIM_NOBILL_001` | 200, `status: NO_BILL_DUE` | same |
| B3 | Unknown biller | `bbps_bill_fetch_unknown.json` | `POST /bill/fetch` | `ID: SIM_UNKNOWN_001` | 404, `errorCode: BILLER_NOT_FOUND` | same |
| B4 | Pay, unregistered key (demo, e2e happy path) | `bbps_pay_default.json` | `POST /payment` | biller without `SIM_`; no per-key mapping matched | 200 `SUCCESS`, ref from key, `duplicate: false`; stateless | e2e "Priya pays BESCOM bill" |
| B4k ⓣ | Pay, success, per key | `pay_ok__post_started.json`, `pay_ok__post_paid.json` | `POST /payment` | body key == K; scenario `pay-K` in `Started` / in `Paid` | `Started`: 200 `SUCCESS`, `duplicate: false` → `Paid`. `Paid`: 200 `SUCCESS`, `duplicate: true`, same ref and `executed_at` (this is v0.1's B5) | `test_finance_pay_bill.py`, `tests/integration/test_idempotency.py` |
| B5 | `SIM_` biller with an unregistered key | `bbps_pay_unregistered.json` | `POST /payment` | `biller_id` begins `SIM_`; no per-key mapping matched | 500 `SIM_KEY_NOT_REGISTERED` | harness self-test |
| B6 ⓣ | Pay, pending, per key | `pay_pending__post_started.json`, `pay_pending__post_later.json` (one mapping per later state: `Pending1`, `Pending2`, `Settled`) | `POST /payment` | body key == K | `Started`: 200 `PENDING` → `Pending1`. Later states: 200 with that state's status, `duplicate: true`, **state unchanged** | `tests/crash_scenarios/test_pending.py` |
| B7 ⓣ | Pay, stuck pending, per key | `pay_stuck__post_started.json`, `pay_stuck__post_stuck.json` | `POST /payment` | body key == K | `Started`: 200 `PENDING` → `Stuck`. `Stuck`: `PENDING`, `duplicate: true` | `tests/integration/test_healer_escalation.py` |
| B8 ⓣ | Pay, failed, per key | `pay_failed__post.json` | `POST /payment` | body key == K | 200 `FAILED`, `debit_confirmed: false`, `bbps_error_code: INSUFFICIENT_FUNDS` → `Failed` | `test_finance_pay_bill.py` |
| B9 ⓣ | Pay, failed after debit, per key | `pay_failed_debit__post.json` | `POST /payment` | body key == K | 200 `FAILED`, `debit_confirmed: true` → `FailedDebit` | same |
| B10 ⓣ | Pay, timeout then paid, per key | `pay_timeout__post.json` | `POST /payment` | body key == K | 12 000 ms fixed delay, then B4k's `Started` body → `Paid` | `tests/crash_scenarios/test_scenario_c.py` |
| B11 | Status, unknown key | `bbps_status_default.json` | `GET /payment/status` | no per-key mapping matched | 200 `NOT_FOUND` (§6.1 schema `status_not_found`) | `tests/crash_scenarios/test_scenario_b.py` (with plan "never") |
| B12 ⓣ | Status, per key, one mapping per state of the plan | `status__<state>.json` for `Started`, `Paid`, `Settled`, `Pending1`, `Pending2`, `Stuck`, `Failed`, `FailedDebit` | `GET /payment/status` | query key == K, **or** query ref == ref(K) with no key; scenario `pay-K` in that state | `Started` → `NOT_FOUND`; `Paid`/`Settled` → `SUCCESS` + ref + `executed_at`; `Pending1` → `PENDING` → `Pending2`; `Pending2` → `PENDING` → `Settled`; `Stuck` → `PENDING`; `Failed`/`FailedDebit` → `FAILED` + `debit_confirmed` | `test_scenario_c.py`, `test_scenario_d.py`, `test_pending.py`, `test_healer_failed.py` |
| B13 ⓣ | Status, key and ref disagree | `status__mismatch.json` (priority 3) | `GET /payment/status` | query key == K and a `transaction_ref_id` that is not ref(K) | 400 `KEY_REF_MISMATCH` | `test_gateway_bbps.py` |
| B14 | Rate limited | `bbps_rate_limit.json` | any | `H: X-Simulate-Rate-Limit: bbps` | 429, `Retry-After: 3600` | `tests/integration/test_gateway_bbps.py` |
| B15 | Biller down | `bbps_consecutive_failures.json` (RB §9.2, unchanged) | `POST /payment` | `H: X-Simulate-Failures: bbps-circuit` | 500 `BILLER_UNREACHABLE` | `tests/dpi_contracts/test_bbps.py`, breaker test |
| B16 | Status API down | `bbps_status_unreachable.json` | `GET /payment/status` | `H: X-Simulate-Failures: bbps-circuit` | 503 | `tests/integration/test_healer_poll_count.py` |
| B17 | Breaker probe | `bbps_biller_info.json` | `POST /biller/fetch` | — | 200, biller name and category; no bill, no money (RB §8.3: the half-open probe) | `tests/integration/test_gateway_bbps.py` |

The tracker's Build Gate list ("SUCCESS, FAILED, PENDING, NOT_FOUND, 429, timeout") is B4/B4k, B8, B6/B12, B11, B14 and B10. Which mappings a plan installs: "ok" = B4k (2) + B12 for `Started`, `Paid` + B13; "pending" = B6 (4) + B12 for `Started`, `Pending1`, `Pending2`, `Settled` + B13; "stuck" = B7 (2) + B12 `Started`, `Stuck` + B13; "timeout_paid" = B10 + B4k's `Paid` mapping + B12 `Started`, `Paid` + B13; "failed" / "failed_debit" = B8 / B9 + a same-state replay mapping + B12 `Started`, `Failed` / `FailedDebit` + B13; "never" = B12 `Started` + B13. Precedence inside one key: a mapping matches on key **and** `requiredScenarioState`, so exactly one applies.

### 5.2 Account Aggregator (`sim-aa`) — WP-18

| # | Scenario | File | Method and URL | Trigger | Response | Consumer |
|---|---|---|---|---|---|---|
| A1 | Consent request | `aa_consent_create.json` | `POST /Consent` | — | 200, `consentHandle` (templated UUID) | `tests/integration/test_consent_aa.py` |
| A2 | Consent pending → active | `aa_consent_status_*.json` (2 files) | `GET /Consent/{handle}` | scenario `aa-consent-approve` | `PENDING`, then `ACTIVE` | same |
| A3 | Consent rejected | `aa_consent_rejected.json` | `GET /Consent/{handle}` | `ID: SIM-AA-REJECT` | `REJECTED` | same |
| A4 | Consent never approved | `aa_consent_never.json` | `GET /Consent/{handle}` | `ID: SIM-AA-NEVER` | `PENDING` always | same (timeout path) |
| A5 | Consent revoked (status poll) | `aa_consent_revoked.json` | `GET /Consent/{handle}` | `ID: SIM-AA-REVOKED` | `REVOKED` | `tests/integration/test_consent_reverify.py`: with `revalidation_required` **already TRUE** (set through the webhook handler's own repository method, §11 OI-3), gate G5 polls, reads `REVOKED` and fails safe |
| A6 | FI request | `aa_fi_request.json`, plus variants `aa_fi_request_low.json` (`consentHandle == SIM-AA-LOWBAL` → `sessionId` begins `low-`) and `aa_fi_request_slow.json` (`SIM-AA-SLOW` → `slow-`) | `POST /FI/request` | default / reserved handle | 200, `sessionId` (default begins `ok-`) | `test_gateway_aa.py` |
| A7 | FI fetch, healthy balance | `aa_fi_fetch_ok.json` | `GET /FI/fetch/{sessionId}` | default | 200, §6.2 body, balance 1 825 040 paise (the figure in Finance PRD Scenario 1) | `test_finance_pay_bill.py` (gate G3 passes) |
| A8 | FI fetch, low balance | `aa_fi_fetch_low.json` | `GET /FI/fetch/{sessionId}` | `ID: SIM-AA-LOWBAL` handle on the preceding request | balance 100 000 paise (below 284 700 + 5 000 buffer) | same (G3 blocks, FIN code per FTS §10) |
| A9 | FI fetch, not ready | `aa_fi_fetch_wait_1.json`, `aa_fi_fetch_wait_2.json`, `aa_fi_fetch_slow_ready.json` | `GET /FI/fetch/{sessionId}` | `sessionId` begins `slow-`; scenario `aa-fi-slow`: `Started` → `Wait1` → `Ready` | 202 (empty body), 202, then A7's body; global scenario, `sim_serial` | `test_gateway_aa.py` (30 s poll limit with injected clock) |
| A10 | Rate limited | `aa_rate_limit.json` (RB §9.1, unchanged) | `POST /FI/request` | `H: X-Simulate-Rate-Limit: aa` | 429, `Retry-After: 1800` | `tests/dpi_contracts/test_aa.py` |
| A11 | AA down | `aa_consecutive_failures.json` | `POST /FI/request` | `H: X-Simulate-Failures: aa-circuit` | 500 | breaker test; degradation script (MC §4.7) |
| A13 | Provider refuses a revoked handle | `aa_fi_request_revoked.json` | `POST /FI/request` | `consentHandle == SIM-AA-REVOKED` | 403, `errorCode: CONSENT_REVOKED` | `test_consent_reverify.py`: local record active, flag **FALSE**, no webhook: G5 passes (by design, CM v1.4 §5.2), the fetch is refused by the provider, the gateway maps it to the CONSENT_007 path, the record is marked revoked, **no payment is attempted** |
| A12 | Breaker probe | `aa_consent_status_probe.json` | `GET /Consent/status` | — | 200, `status: UP` (RB §8.3: a status check, not an FI fetch) | `test_gateway_aa.py` |

Because `GET /FI/fetch/{sessionId}` does not carry the consent handle, A8 and A9 are selected by a `sessionId` prefix that A6's variants return for the reserved handles (`SIM-AA-LOWBAL` → `sessionId` beginning `low-`).

### 5.3 ABHA (`sim-abha`) — WP-34

| # | Scenario | File | Method and URL | Trigger | Response | Consumer |
|---|---|---|---|---|---|---|
| H1 | Consent request | `abha_consent_init.json` | `POST /v0.5/consent-requests/init` | — | 202, `id` | `tests/integration/test_consent_abha.py` |
| H2 | Consent granted | `abha_consent_status_*.json` | `GET /sim/consent-requests/{id}` | scenario `abha-consent-approve` | `REQUESTED`, then `GRANTED` + `artefact_id` | same |
| H3 | Health-information request | `abha_hi_request.json` | `POST /v0.5/health-information/cm/request` | — | 202, `transaction_id` | `tests/integration/test_health_prescription.py` |
| H4 | Bundle, clean | `abha_hi_bundle_ok.json` + `__files/nani_prescription.json` | `GET /sim/health-information/{transaction_id}` | default | 200, FHIR R4 Bundle: 2 MedicationRequest **and nothing else**: the consent is `ABHA_PRESCRIPTION` with `hiTypes: [Prescription]`, so the normal answer stays inside it (v0.2) | same; e2e "Nani's medication reminder" |
| H5 | Bundle, partial | `abha_hi_bundle_partial.json` + `__files/nani_prescription_partial.json` | same | `ID: hip_id SIM-HIP-PARTIAL` in the H3 request (the `transaction_id` it returns begins `partial-`) | 200, one MedicationRequest missing `dosageInstruction` | `test_health_fhir_partial.py` (RB §5.3: partial data, no breaker trip) |
| H6 | Bundle, malformed | `abha_hi_bundle_malformed.json` | same | `ID: hip_id SIM-HIP-MALFORMED` (`transaction_id` begins `malformed-`) | 200, RB §9.4's malformed body | same (`parse_quality = FAILED`) |
| H10 | Bundle, over-broad | `abha_hi_bundle_overbroad.json` + `__files/nani_prescription_overbroad.json` | same | `ID: hip_id SIM-HIP-OVERBROAD` (`transaction_id` begins `overbroad-`) | 200, the two MedicationRequests plus one `Observation` and one `DiagnosticReport` the consent does not cover | `test_health_scope.py`: the two prescriptions are stored; the other resources are dropped before parsing, appear in no table, log line, audit payload or outbound call, and the dropped count is reported (CM §2.3; Health PRD §4.1) |
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
| D5 ⓣ | Document expiring | `dl_issued_item.json` (template) | installed by `register_document(account, doctype, valid_to)` | bearer token's account part | the D4 list for that account with one more item whose `valid_to` is the **explicit date the test passes**, computed from the test clock (e.g. test clock's today + 20 days). WireMock's own clock is never used for a business date (§7.1) | `test_vault_expiry.py` (30- and 7-day reminder defaults; also run at an IST-midnight boundary) |
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

// POST /payment  → 200   schema pay_success
{ "status": "SUCCESS", "transaction_ref_id": "BBPS-TXN-550E8400E29B41D4A716446655440000",
  "idempotency_key": "550e8400-e29b-41d4-a716-446655440000", "duplicate": false,
  "executed_at": "2026-09-21T15:11:42Z" }

// POST /payment  → 200   schema pay_pending
{ "status": "PENDING", "idempotency_key": "550e8400-…", "duplicate": false }

// POST /payment  → 200   schema pay_failed
{ "status": "FAILED", "bbps_error_code": "INSUFFICIENT_FUNDS", "debit_confirmed": false,
  "idempotency_key": "550e8400-…" }
```

**`GET /payment/status`**: query parameters `idempotency_key` (optional) and `transaction_ref_id` (optional); at least one is required (neither → 400 `MISSING_LOOKUP`). The Healer always has the key; it has the ref only if the payment call returned before the crash. One schema per outcome, and the gateway's response model is a tagged union on `status`:

| Outcome | Schema | Body | Fields the Healer needs (FTS v1.3 §6.3–6.4) |
|---|---|---|---|
| `SUCCESS` | `status_success` | `{ "status": "SUCCESS", "transaction_ref_id": "BBPS-TXN-…", "idempotency_key": "…", "executed_at": "<RFC 3339 UTC>", "amount_paise": 284700 }` | `transaction_ref_id` even when the client never saw one (timeout case); `executed_at` becomes the audit row's `occurred_at` |
| `FAILED` | `status_failed` | `{ "status": "FAILED", "idempotency_key": "…", "bbps_error_code": "…", "debit_confirmed": true \| false, "failed_at": "<RFC 3339 UTC>" }` | `debit_confirmed: true` → the refund branch (FTS §8) |
| `PENDING` | `status_pending` | `{ "status": "PENDING", "idempotency_key": "…", "transaction_ref_id": null \| "BBPS-TXN-…" }` | elapsed time is the Healer's own clock, not the simulator's |
| `NOT_FOUND` | `status_not_found` | `{ "status": "NOT_FOUND" }` | nothing else; inside 24 h → resubmit with the same key |
| key and ref disagree | `error` | 400 `{ "error": "KEY_REF_MISMATCH" }` | treated as *unknown*: no resubmission, admin alert (FIN_011 path) |
| status API down (B16) | — | 503 | poll count + 1 |

`executed_at` and `failed_at` are fixed when the per-key mappings are registered (the fixture passes them, from the test clock), so the first answer, a replayed POST and every status answer for a key agree to the second.

**Payment instrument values (settles OI-1, on Codex's recommendation).** AGENTS invariant 9 forbids *persisting* UPI ids and account numbers in the application database; it does not forbid an adapter from having a value in memory for the one call that needs it. For this build: `upi_vpa` and `customer_params.account_no` are **synthetic values held by the simulator adapter's fixture configuration** (`wiremock/bbps/fixtures/instruments.json`, keyed by an opaque `payment_instrument_ref`). Application tables, envelopes and the module's `billers.customer_params` hold only the opaque reference; the adapter resolves it in memory immediately before the call; request bodies are redacted from application logs (only the key, biller and amount are logged). A real deployment would resolve the reference inside the gateway's credential boundary, which is a threat-model topic (WP-42), and never in a module table. Stub generation must not turn these two fields into a storage requirement.

`/bill/fetch` and `/payment/status` are not shown in FTS; their shapes are fixed here as the gateway contract. FTS names the status call only as `GET_BBPS_STATUS(idempotency_key, transaction_ref_id)`.

### 6.2 Account Aggregator

```jsonc
// GET /FI/fetch/{sessionId}  → 200   (plain JSON; the real payload is encrypted, §9)
{ "sessionId": "ok-7f3a…", "status": "READY",
  "accounts": [ { "fip_id": "SIMBANK", "fi_type": "DEPOSIT", "masked_account": "XXXX0001",
                  "balance_paise": 1825040, "as_of": "{{request.headers.X-Sim-As-Of}}" } ] }
```

`balance_paise` 1 825 040 is the one canonical healthy balance (row A7, Finance PRD Scenario 1); v0.1 showed 5 000 000 here. `as_of` echoes the business time the gateway sends in `X-Sim-As-Of` (§7.1); when the header is absent (demo) the static mapping falls back to WireMock's `now`.

### 6.3 ABHA

`__files/nani_prescription.json` is a FHIR R4 `Bundle` of type `collection` with two `MedicationRequest` resources (a twice-daily and a once-daily medicine, synthetic names from a published generic list, `dosageInstruction.timing` filled) and nothing else. `nani_prescription_overbroad.json` (H10) adds an `Observation` and a `DiagnosticReport` for the negative test. The patient reference is `nani.sharma@sbx`, the synthetic ABHA address the Health PRD uses for Nani (no reserved prefix, so she gets the happy path). A second hospital sending bad data for the same patient is the realistic case, which is why H5 and H6 are selected by HIP id and not by patient. No real person, practitioner or hospital appears; the HIP is `SIM-HIP-001` "Simulated Clinic".

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

**Two kinds of time (v0.2).** *Transport time* is real: delays, client timeouts and `deadline_at` run on the monotonic clock of the process that waits, and B10's 12 seconds are 12 real seconds (the one slow test in the suite). *Business time* is simulated: due dates, `valid_to`, `executed_at`, consent expiry, "20 days from now". WireMock is a separate process with its own wall clock, and its templating helper `now` reads that clock (wiremock.org, "Response templating"); advancing the application's injected clock does not move it. Therefore:

- No mapping that a deterministic test depends on may compute a business date from `now`. Business dates are **explicit values**: passed by the fixture that installs the mapping (`register_payment(..., executed_at=)`, `register_document(..., valid_to=)`), or echoed from the request (`X-Sim-As-Of`, which the gateway sets from the application clock in `SIMULATOR_MODE`).
- Static happy-path mappings used only by the demo and the real-time e2e run may use `now`.
- Boundary tests that must exist: a fixed clock; a document that expires "today" at 23:59 IST and at 00:01 IST the next day; a consent that expires between approval and execution. None of them may depend on the host's date.

### 7.2 Chaos mode

RB §9.4 describes chaos as a YAML file with failure rates. WireMock has no per-request failure probability, so the file is interpreted by a small driver, `tools/sim_chaos.py` (standard library plus PyYAML as a dev dependency):

1. Read `wiremock/chaos_config.yaml` (shape unchanged from RB §9.4) and seed a random generator with `CHAOS_SEED`.
2. Once a second, for each enabled scenario, draw a number; with probability `failure_rate` **install** the scenario's failure stub on the matching simulator, otherwise **remove** it. Every chaos stub (files under `wiremock/chaos/`, priority 0) has a **stable id**, `uuid5(NAMESPACE, scenario_name)`, and `metadata: {"chaos": true}`. Install is `PUT /__admin/mappings/{id}` (create or replace: idempotent); remove is `DELETE /__admin/mappings/{id}` (a 404 is fine).
3. On start **and** on exit (normal, SIGINT, SIGTERM) the driver removes every mapping with `chaos: true` metadata (`POST /__admin/mappings/remove-by-metadata`). A driver that was killed hard cannot clean up, which is why `reset_simulator` does the same (§8.2) and why the deterministic suites call it at session start: WireMock resets scenarios and removes mappings through different admin calls, and v0.1's reset did only the first.
4. Log every switch with a timestamp and the generator's draw.

**What the seed reproduces.** The same `CHAOS_SEED` reproduces the same sequence of fault *windows*. It does not reproduce which requests fall inside them: that depends on scheduling and latency, so two runs with one seed can differ in outcome. Chaos results are therefore read statistically (rates over a run, WP-41), never as a deterministic regression test, and a failure found under chaos is turned into a deterministic test with headers or a registered plan before it is fixed. Request-level replay would need the request timeline recorded and re-driven; that is not built.

Over a run, the share of seconds in which a failure stub is active approaches `failure_rate`. That is a coarser model than per-request failure and is stated as such in §9. The chaos run (WP-41) passes when the application returns no 5xx of its own, every failure surfaces as a FIN or MOD code, and breakers open and close as RB §8 says (Roadmap §8, "Resilience score").

---

## 8. Contract Tests and Request-Journal Assertions

### 8.1 Contract tests (`tests/dpi_contracts/`)

RB §9.5 asks that stubs "match real DPI API schemas". Without sandbox access that cannot be proven, so the contract is defined as follows:

- Each endpoint has a JSON Schema under `wiremock/<dpi>/schemas/`, with a header comment giving its **provenance**: "from FTS §2.3", "from CM §6.1.1", or "gateway contract, this spec §6", and the date.
- Schemas are per **(endpoint, outcome)**, not per endpoint: `pay_success`, `pay_pending`, `pay_failed`, the four `status_*` schemas, `error`. Responses that are not JSON bodies are validated for what they are: D1's 302 by status, `Location` and the echoed `state`; A9's 202 by status and empty body; D6 by status, `Content-Type: application/pdf` and a non-empty body.
- Test 1: every static stub response and every **rendered** template response (each plan registered once with a sample key, each state visited) validates against the schema of its outcome.
- Test 2: the gateway's Pydantic response model for that endpoint accepts every stub response and rejects a mutated one (a required field removed).
- Test 3: RB §9.5's three tests, as written.
- When a real sandbox becomes available (Roadmap §6), the schemas are the single thing to re-verify; stubs and models follow from them.

### 8.2 Helpers (`tests/fixtures/simulators.py`)

| Helper | Does |
|---|---|
| `reset_simulator(dpi)` | `POST /__admin/scenarios/reset`, `DELETE /__admin/requests`, and `POST /__admin/mappings/remove-by-metadata` for `dynamic: true` and for `chaos: true`; afterwards the live mappings equal the files on disk (asserted by a harness self-test that counts them) |
| `register_payment(key, plan, executed_at=None, amount_paise=None)` | Renders the plan's templates for that key (§4.2, §5.1) and installs them with deterministic ids; idempotent |
| `unregister_payment(key)` | Removes that key's mappings by metadata |
| `register_document(account, doctype, valid_to)` | D5: adds one issued document with an explicit date |
| `set_scenario_state(dpi, scenario, state)` | `PUT /__admin/scenarios/{scenario}/state`; with `scenario = pay-<key>` it starts a test in `Paid` without making a payment |
| `journal(dpi, method, url_pattern)` | `POST /__admin/requests/find`; returns the matching requests |
| `simulate(**headers)` | context manager that sets the `simulate` directive the gateway turns into `X-Simulate-*` headers (§3.2) |

### 8.3 Journal assertions every payment test makes

1. At most one `POST /payment` per idempotency key, unless the test is *about* a same-key replay, in which case all of them carry the same key (AGENTS.md §4 item 16). Crash scenario B: zero before the crash, exactly one after (§4.3).
1a. No `POST /payment` is ever sent from a `phase: prepare` dispatch (MR v1.2 §6.2); the journal entry's `X-Dispatch-Phase` header, set by the gateway in `SIMULATOR_MODE`, is `execute`.
2. The AA balance fetch (`POST /FI/request`) precedes `POST /payment` in time (gate order, AGENTS.md §4 item 18).
3. No request body sent to any simulator contains a seed user's name, phone number or email (a list in the fixture). The payment body's `upi_vpa` and `account_no` equal the synthetic values in the adapter's fixture file and appear in **no** application table or log line (§6.1).
3a. No status lookup is made with a key that was never registered (§4.2); a test that does so is mis-set-up and fails.
4. When a gate fails, there is **no** `POST /payment` in the journal at all.

---

## 9. Simulated versus Real

| Area | Real DPI | Simulator | Why it is acceptable here |
|---|---|---|---|
| Access | Licensed entities only (FIU, BBPOU, HIU, DigiLocker partner) | Open HTTP on localhost | Portfolio mode; no licences (Decision Log) |
| BBPS API | Reached through a BBPOU's own API; shapes vary by provider | One invented REST shape (§6.1), based on FTS §2.3 | The gateway isolates the shape; a real BBPOU adapter replaces it |
| BBPS idempotency | Provider-specific; FTS assumes 24-hour dedup by key | Dedup per key, by a per-key WireMock scenario that fixtures install (§4.2); unregistered keys are stateless | One key is one payment and two keys are two, in one test; the 24-hour boundary is tested with an injected clock in the Healer, not in the simulator |
| AA data | Encrypted FI payload (key exchange between FIU and FIP), signed requests, detached JWS | Plain JSON, no signatures | Cryptography belongs to the threat model and the real adapter; the flow (consent → request → session → fetch) is preserved |
| AA consent approval | User approves in an AA app | Status flips after one poll | The polling, timeout and rejection paths are all exercised |
| ABDM data flow | Asynchronous callbacks, encrypted FHIR bundles | Polling on `/sim/...` paths, plain FHIR | Same reasoning; the FHIR parsing and partial-parse handling are real |
| DigiLocker | Aadhaar OTP login, real OAuth consent screen, signed XML/PDF | Immediate redirect with a code; a synthetic PDF | The authorisation-code flow, token refresh and "bytes never stored" rule are real |
| Rate limits | Enforced by the network | Never enforced; 429 only when a test asks for it | The application's own budget tracker (RB §2) is the thing under test |
| Latency and failure | Whatever the day brings | Log-normal delay; chaos in one-second windows | Coarse; the seed repeats the fault windows, not the outcomes (§7.2) |
| Webhooks | Revocations and callbacks arrive signed | Not simulated yet (OI-3) | Verification code is specified (CM §9) and is a threat-model deliverable. Until then signature checking, replay protection and the 503-on-missing-keys rule are **untested**, and a revocation that arrives by no webhook is caught at the provider's refusal (A13), not at gate G5 |
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
| OI-1 | ~~FTS §2.3's payment request carries `upi_vpa` and `customer_params.account_no`, which invariant 9 forbids storing.~~ **Settled for this build 2026-09-21** (Codex's recommendation): synthetic values live in the simulator adapter's fixture file and are materialised in memory for the call; application storage holds an opaque `payment_instrument_ref`; request bodies are redacted from logs (§6.1). Where a real deployment resolves the reference stays open. Related: Finance PRD OI-4. | LOW (was MEDIUM) | Security_Threat_Model.md (WP-42): the gateway's credential boundary |
| OI-2 | ~~Payment state is global per simulator.~~ **Closed in v0.2:** per-key scenarios installed by fixtures (§4.2). Still global: the AA/ABHA approval scenarios and A9 (§4.4). An alternative that needs no pre-registration, a WireMock serve-event webhook that installs the key's mappings when the first `POST /payment` arrives, was not chosen: it is asynchronous, so a fast replay could race it. | LOW | Revisit only if pre-registration becomes a burden in e2e tests |
| OI-3 | Inbound webhooks (AA revocation, ABDM callbacks) are not simulated. **v0.1 claimed that CONSENT_REVERIFY "covers revocation by polling (A5)"; that was wrong.** CM §5.2 polls the provider only when `revalidation_required` is already TRUE, and only a verified webhook (or the watchdog) sets it. What the suite proves instead: (a) flag TRUE → G5 polls, reads A5's `REVOKED`, fails safe. The test sets the flag by calling the **same repository method the webhook handler calls**, not by raw SQL, so everything after signature verification is exercised. (b) flag FALSE, handle revoked at the provider, no webhook → G5 passes, the provider refuses the fetch (A13), the gateway maps that to the CONSENT_007 path and no payment is attempted. **Not proven:** JWS/JWT verification, replay protection, 503 when keys are missing (CM §9), and any claim that an unseen external revocation is detected *before* the provider call. Inconsistency Register item 19; CM v1.4 §5.2 states the same limit. | MEDIUM | With the threat model (WP-42): a signed-webhook sender in `tests/fixtures/` using a test key |
| OI-4 | `/bill/fetch`, `/payment/status`, the DigiLocker `issued` list and the `/sim/...` ABHA paths are defined here, not in a frozen spec. | LOW | Codex review confirms them as the gateway contract; FTS and CM reference this spec at their next revision |
| OI-5 | RB §9's stub paths (`wiremock/mappings/…`) differ from §2.2's per-DPI folders. | LOW | RB v1.3 adopts the per-DPI path; no behavioural change |
| OI-6 | Latency medians (§7.1) are chosen, not measured. | LOW | Replace with measured values if a sandbox ever becomes available |

---

## 12. Q&A

| Asked by | Question | Answer |
|---|---|---|
| Engineering | Why WireMock and not a small FastAPI fake, which could keep per-key state? | RB §9 (frozen) already commits to WireMock, the stubs are declarative JSON a routine agent can generate and a reviewer can read, and the admin API gives the request journal for free. A Python fake would be a second application to test. Per-key state is obtained by installing one small named scenario per key (§4.2), which costs a fixture, not an extension. |
| Engineering | Why both identifiers and headers? | End-to-end tests and the demo should not need test-only plumbing, so they use identifiers. Lower-level tests need to force a failure on a healthy identifier, which only a header can do, and RB §9 already defines headers. |
| Security | Can a user trigger a simulated failure in the demo by sending `X-Simulate-Failures`? | No. The API edge strips `X-Simulate-*`; only the gateway adds them, from a directive that exists only in test contexts (§3.2). Both halves have tests. |
| Product | The demo shows a payment succeeding. How does a viewer know it is fake? | `SIMULATOR_MODE=true` puts a permanent "SIMULATOR" banner in the UI (§2.3), and the write-up carries the §9 table. |
| Reviewer | How is crash scenario C tested without killing the server at the right microsecond? | Two ways: a real process kill at the named crash point `bbps_success` (Test Automation Strategy §4) for the literal crash, and the "timeout_paid" plan (B10), where the simulator "pays" and the client times out. Both leave the session in EXECUTION with money moved, which is the state the Healer must repair. |
| Reviewer | Does the simulator prove the DPI integration works? | No, and it does not claim to. It proves that the application's safety machinery (gates, idempotency, two-phase commit, the Healer, breakers, degradation) behaves correctly against the failure modes the specs enumerate. §9 says what would have to be redone against a real sandbox. |
