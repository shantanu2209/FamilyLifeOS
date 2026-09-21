# Test Automation Strategy

_What is tested at which level, how tests stay deterministic, what CI enforces, and who writes what, for the portfolio build_

> **Status:** DRAFT v0.2 — Codex's review of v0.1 (8 findings) applied; Codex's targeted re-review pending · **Author:** Shantanu Chaudhary (Lead Product Architect), drafted with Claude Code · **Last content change:** 2026-09-21
> **Priority:** P1. Execution Plan WP-13. Formalises the February 2026 "Test Automation Strategy" section of the tracker (now in `docs/reference/Project_Tracker_Snapshot_2026-02.md`) for the stack chosen in AGENTS.md §5, and replaces it.
> **Depends on:** AGENTS.md §4 (invariants), §5 (stack), §6 (working rules) · FTS v1.3 §4.5 (crash scenarios), §4.6, §6 (Healer) · Tech_Spec_Simulator_Architecture v0.2 (SIM) §3–§5, §7–§8 · Data Model v1.4 §3.18 (audit protocol tests), §6.1 (typed payloads) · Module Registry v1.2 §6.4–6.7, §8.1 · NFR v2.2 §1, §6 · Execution Plan §7 (Definition of Done), §7.2 (invariant coverage map) · Roadmap §5, §8.
> **Cited elsewhere as:** Test strategy, TAS §n.

## 0. Document Governance

| Version | Date | Description of Change | Author |
|---|---|---|---|
| v0.1 | 2026-09-17 | First version. Tiers and directories, invariant-named tests, determinism rules, scenario catalogue tied to simulator rows, CI jobs and gates, flaky-test policy, security checks, agent responsibilities, explicit non-goals. Drops the tracker section's assumptions that do not fit the project: a hired QA engineer, Jest and Supertest for the backend, Appium, anonymised production data, a calendar of weekly and monthly runs. | Shantanu Chaudhary (with Claude Code) |
| v0.2 | 2026-09-21 | Codex review of PR #23, all 8 findings. (f1) One clock contract across Python, SQL, Redis, the simulators and the browser, with business time separated from transport time (§4.1). (f2) A crash test kills a real process at a named point and recovers in a fresh one; forced database failure is a separate injection (§4.2). (f3) The crash suite runs on every pull request; no path filter stands between a change and the required verdict (§7). (f4) The invariant gate reads **executed results** and an explicit, reviewed applicability map; skip, xfail, deselect and quarantine fail it (§3). (f5) Simulator isolation is ownership, not a marker (§4.3). (f6) The AA budget test proves local denial with a healthy provider; a provider 429 is a different test (§5.4). (f7) Audit payloads are checked against typed allowlists, and privacy tests use adversarial input, including PII inside the utterance (§5.5). (f8) A retry can collect diagnostics but can never turn a safety or invariant failure green (§7.1). Scenario additions from the whole review batch (#9, #10, PRs #22, #25, #20) are in §5; the docs checks stay in CI (§7). | Shantanu Chaudhary (with Claude Code; review by Codex) |

---

## 1. Scope and Principles

This is a payments-and-health product built by one person and three AI agents. Tests are the only reviewer that never gets tired, so the strategy is strict where money, consent and the audit log are involved and deliberately plain everywhere else.

1. **The invariants are the test plan.** Every testable invariant in AGENTS.md §4 has at least one test named after it (§3). A reviewer reads test names before reading code.
2. **Crash scenarios are written first.** FTS §4.5's scenarios exist as failing tests before the Healer exists (Roadmap §5). They are the Build Gate.
3. **Deterministic or deleted.** No sleeps, no wall-clock, no real network, no real LLM in any gating test (§4). A test that fails one run in fifty is a defect in the test or in the product, and is treated as one (§7).
4. **One runner per language.** pytest drives everything in Python, including Playwright (`pytest-playwright`); Vitest covers `web/` units. No second backend test framework.
5. **The simulators are part of the test system.** Scenario selection, per-key payment plans, resets and journal assertions follow SIM §3, §4 and §8. This document does not restate them.
6. **Tests travel with the change.** A PR that changes behaviour without changing tests is rejected in review (Execution Plan §7, item 2), whoever wrote it.
7. **No plan by calendar.** Nothing here runs "weekly" or "monthly". Every suite is triggered by an event: a commit, a PR, a merge, a milestone, or a person asking (AGENTS.md §6, no dates).

---

## 2. Tiers, Directories and Tools

| Tier | Directory | Tool | What belongs here | Talks to | Share of tests (guide, not gate) |
|---|---|---|---|---|---|
| Unit | `tests/unit/` | pytest | Pure logic: FSM transitions, hash-chain canonicalisation, gate ordering, idempotency-key lifecycle, budget arithmetic, IST window maths, manifest validation, visibility rules, FHIR field extraction, error mapping | nothing (no DB, no Redis, no HTTP) | ~60 % |
| Integration | `tests/integration/` | pytest + Testcontainers (PostgreSQL 15, Redis) + the WireMock simulators | Anything that needs real SQL semantics or real Redis: resource lock races, cardinality races with `SELECT … FOR UPDATE`, audit chain under concurrent writers, Lua budget scripts, breaker state, migrations, kernel views and grants, module isolation (a module role cannot read `core` tables) | containers only | ~30 % |
| Crash scenarios | `tests/crash_scenarios/` | pytest, integration fixtures, the application run as a **subprocess** with named crash points (§4.2), Healer `run_once()` in a fresh process with the test clock | FTS §4.5 A–D and the lock-release case; pending and stuck-pending payments; Healer caps and its own breaker | containers + `sim-bbps`, `sim-aa` | counted in integration |
| DPI contracts | `tests/dpi_contracts/` | pytest + jsonschema | SIM §8.1: stub ↔ schema ↔ gateway model agreement; RB §9.5's three tests | simulators | small |
| End-to-end | `tests/e2e/` | pytest-playwright (Chromium; virtual WebAuthn authenticator) | Whole flows through the PWA: "Priya pays BESCOM bill", "Nani's medication reminder via proxies", the Kitchen Tablet block, Vault show-and-hide | full Compose stack | ~10 %, and few |
| Web unit | `web/src/**/*.test.ts(x)` | Vitest + Testing Library | Component states: approval screen, SIMULATOR banner, visibility chip, error rendering from i18n keys | nothing | as needed |
| Load | `tests/load/` | k6 | The two slices under light concurrency; P95 per NFR §1 | demo deployment or local Compose | on demand |

Rules of placement: if a test needs a database it is not a unit test; if it needs a browser it is an end-to-end test; if it can be a unit test it must be one. Markers: `@pytest.mark.integration`, `crash`, `contract`, `e2e`, `safety` (any test whose failure means a safety property broke: every invariant-named test, every crash test, the public-surface, visibility, consent-scope and double-payment assertions, at whatever tier), `sim_serial` (SIM §4.4; an ownership rule, §4.3), `quarantine` (§7).

---

## 3. Invariant-Named Tests

- A test that protects an invariant from AGENTS.md §4 is named `test_invariant_<n>_<what_it_proves>`, for example `test_invariant_16_idempotency_key_persisted_before_external_call`, `test_invariant_17_lock_released_only_after_phase2_commit`, `test_invariant_6_public_surface_never_shows_vault_metadata`.
- The map of invariants to test modules and work packages is Execution Plan §7.2 and is not copied here.
- **The gate reads what ran, not what exists (v0.2).** A test that is collected but skipped, xfailed, deselected by a marker expression or quarantined proves nothing, and v0.1's collection-based check would have passed it. `tools/check_invariant_tests.py` (written with WP-32) therefore takes two inputs: the **applicability map** `tests/invariants.toml`, and the **JUnit XML of the jobs that just ran** (`unit`, `integration`, `crash`, `e2e`). For every invariant the map marks *required* at the current milestone it demands at least one test named `test_invariant_<n>_…` with outcome **passed** in those reports. `skipped`, `xfailed`, `xpassed`, `error`, absent from the reports, or carrying the `quarantine` marker all fail the gate, each with its own message. The job runs last and `needs:` the test jobs.
- **Applicability is a reviewed file, not a guess.** `tests/invariants.toml` has one entry per invariant of AGENTS.md §4: `required_from = "M2" | "M3" | "M4"`, or `status = "review_criterion"` (36, 37), or `status = "not_yet_applicable"` with a `reason` and the work package that will bring it. A change to the file is reviewed like a test deletion (§12). The current milestone is a single value in the same file, changed by the PR that closes a milestone. Initial content:

  | Invariants | Required from | Note |
  |---|---|---|
  | 1, 2, 6, 7 | M2 | Proven on the Finance slice's own queries and endpoints; the generated role × intent matrix (WP-25) and the public-surface test arrive in M2 |
  | 3, 4, 5 | M3 | Cardinality races, last admin, bidirectional edges need family management (WP-37). v0.1 said "M2 as far as Finance touches them" while scheduling their tests at WP-37; the map says M3 and the M2 gate does not pretend otherwise |
  | 8, 9, 10, 11 | M2 | Consent gate, no raw credentials, CONSENT_REVERIFY live, only a human grants |
  | 12 | M3 | Children and managed profiles (WP-35) |
  | 13 | not yet applicable | Account deletion (no work package yet); listed, never silently skipped |
  | 14 | not yet applicable | Webhook verification: needs the signed-webhook sender (SIM OI-3, WP-42) |
  | 15–24 | M2 | Payment execution and the audit log |
  | 25–28 | M2 for AA and BBPS; M3 adds ABHA | One entry per invariant with a per-provider test list |
  | 29 | M2 for the finance degradation script; M3 for health | Missing from v0.1's list |
  | 30–35 | M2 | Module architecture |
  | 36, 37 | review criterion | Not tests |

- Renumbering an invariant in AGENTS.md means renaming its tests in the same PR. The script makes forgetting that visible.

---

## 4. Determinism Rules

| Source of nondeterminism | Rule |
|---|---|
| Time | All **business time** comes from an injectable `Clock`; no `sleep`, no `datetime.now()` in product code outside it. One Python object cannot move PostgreSQL's, Redis's, WireMock's or the browser's clock, so each of those has its own rule in §4.1 |
| Background work | The Healer, the expiry watchdog and module sweeps expose `run_once()`. Tests call it. No test waits for a scheduler |
| Crashes | A real process is killed at a named point and a fresh one recovers from PostgreSQL (§4.2). An exception is not a crash |
| Identifiers | UUIDs are generated through an injectable factory so a test knows the idempotency keys in advance, registers a simulator plan for each (SIM §4.2) and then finds them in the journal |
| Randomness | Backoff jitter takes a seeded generator in tests. Chaos mode is seeded (`CHAOS_SEED`, SIM §7.2) and never part of a gating job |
| Network | Only the simulators and Testcontainers. The test network has no route out; a test that needs the internet is wrong |
| LLM | Gating tests use the deterministic stub behind the LLM gateway. The golden utterance set (about fifty English, Hindi and Hinglish utterances with expected intents) runs against the stub in CI as a gate, and against the local and hosted models as a **report** only (Roadmap §8, routing accuracy) |
| Simulator state | BBPS payment state is per key and needs no serialisation. Tests that use a global simulator scenario own the simulators exclusively (§4.3) |
| Order | Tests must pass in random order (`pytest-randomly`) and alone. Shared state between tests is a defect |
| Browser | Playwright's virtual authenticator stands in for passkeys; traces and screenshots are kept on failure |

### 4.1 The clock contract (v0.2)

Two kinds of time. **Business time** (is this session a zombie, has this consent expired, which IST day is it) is simulated and must be controllable. **Transport time** (timeouts, `deadline_at`, backoff) is real, measured on the monotonic clock of the waiting process, and is kept short in tests instead of being faked.

| Where time lives | How product code must be written | How a test moves it | Boundary tests that must exist |
|---|---|---|---|
| Python | `Clock.now()` (UTC, aware) and `Clock.monotonic()`; nothing else | `FakeClock.advance()` for business time; never for deadlines | — |
| PostgreSQL | **Every business cutoff is a bound parameter computed from `Clock`**: the Healer's zombie selector takes `$cutoff = clock.now() - 5 min`, never `NOW() - INTERVAL '5 minutes'`; likewise session expiry, lock staleness, purge age, consent expiry, the IST `limit_date`. `DEFAULT NOW()` stays on `created_at` / `updated_at`, which are **record-keeping, never read by a decision**. A lint test greps the kernel's and modules' SQL for `NOW()`, `CURRENT_TIMESTAMP` and `clock_timestamp()` outside column defaults and the audit functions and fails on a hit. Where the specs' SQL shows `NOW() - INTERVAL …` (FTS §6.4, DM §7.4, CM §7.2) the implementation binds the cutoff; behaviour is identical in production | Fixtures insert rows with **explicit timestamps** relative to the test clock ("updated_at = clock.now() − 6 min"); the test then advances the clock or not. No test waits and no test depends on the database server's date | Zombie at 4 min 59 s versus 5 min 01 s; stale lock at 30 min; purge at 24 h; a row written "yesterday" IST versus "today" |
| Redis | TTLs are set as **absolute expiry** computed from `Clock` (`EXPIREAT` / `PEXPIREAT` to the next IST hour or midnight, Runbook §2), and the Lua budget script receives `now` as an argument | Real Redis semantics are kept. Tests of the bucket boundary call the script with `now` just before and just after the boundary and assert both the count and the key's `PEXPIRETIME`; one slow-lane test lets a 1-second key really expire, to prove the server honours what was set | AA hourly bucket at hh:59:59 and hh+1:00:00 IST; BBPS daily bucket at 23:59:59 and 00:00:00 IST; breaker open-until |
| Simulators | Business dates in stub bodies are explicit values from fixtures or echoed from `X-Sim-As-Of`; never WireMock's `now` (SIM §7.1) | `register_payment(..., executed_at=)`, `register_document(..., valid_to=)` | Document expiring today at the IST day boundary; `executed_at` identical across POST, replay and status |
| Browser (Playwright) | UI countdowns (the 5-minute approval window, the 60-second document viewer) read an injectable time source in `web/` | `page.clock.install()` / `fastForward()`; the server-side expiry is driven by `FakeClock` through the test control endpoint, which exists only when `APP_ENV=test` | Approval prompt expires client-side and server-side at the same simulated instant; an approval sent after server-side expiry is refused even if the client still shows the prompt |

The end-to-end stack shares one business clock: the API process reads `Clock` from a test control endpoint's state, and the e2e harness advances it there and in the page together. That endpoint is part of the `APP_ENV=test` surface checked in §5.5.

### 4.2 Crashes are process deaths (v0.2)

v0.1's "abort the process path" could be implemented as a raised exception, which runs `finally` blocks, releases application-level locks, closes transactions politely and leaves Redis and in-process state alive. None of that happens when a server dies, so such a test can pass while real recovery fails.

- **Harness.** The crash suite starts the API (and, where relevant, the Healer) as **subprocesses** against the Testcontainers PostgreSQL and Redis and the simulators. Named crash points (`before_phase1`, `phase1_commit`, `bbps_success`, `phase2_begin`, `phase2_commit`, plus the module's `after_tx_a` and `after_tx_b`, MR v1.2 §6.4) are compiled-in checkpoints that do nothing unless armed.
- **Arming.** `CRASH_AT=<point>` in the subprocess environment. At the point, the process writes one line to a pipe the test holds (`reached <point>`), then calls `os._exit(137)`: no exception, no `finally`, no `atexit`, no connection close. The test waits on the pipe, not on time, so the boundary is exact.
- **Recovery.** A **fresh** process is started with no crash point armed. It must find everything it needs in PostgreSQL. The test asserts: which transaction had committed (rows present or absent for that exact point); which requests reached WireMock before the death (journal: for `phase1_commit`, none); that the first process's Redis lock, if any, is either expired or taken over by the documented rule, not released by cleanup code; that recovery used the **original** idempotency key; final state and a verified audit chain (DM Q12) with exactly one payment row.
- **Phase 2 database failure** (FTS §4.5 scenario D) is a different injection, not a process death: a fault-injecting connection wrapper makes the Phase 2 COMMIT raise. It stays an in-process test and asserts the same end state through the Healer.
- **"Inert outside tests" has a concrete meaning.** The checkpoints read `CRASH_AT` only when `APP_ENV=test`, and start-up **refuses to boot** (exit code, log line) if `CRASH_AT`, the test control endpoint, or any `X-Simulate` directive source is configured while `APP_ENV` is anything else. The negative test starts the demo configuration with `CRASH_AT=bbps_success` and asserts the refusal.

### 4.3 Who owns a simulator (v0.2)

A marker does not isolate anything: `sim_serial` tests in one worker can still collide with another worker's reset. The rule is ownership.

- **Invocation 1, parallel** (`pytest -n auto -m "not sim_serial"`): unit, integration, contracts, crash. These tests may use only per-request mechanisms (headers) and per-key or per-fixture mappings that they register and remove themselves (SIM §4.2). They never call `reset_simulator`, and a harness guard makes that call raise in this invocation.
- **Invocation 2, exclusive** (`pytest -p no:xdist -m sim_serial`), run **after** invocation 1 in the same job against the same containers: tests that use a global scenario (AA and ABHA approval, A9) or chaos-style dynamic failure stubs. Each starts with `reset_simulator(dpi)`, which also removes dynamic and chaos mappings (SIM §8.2).
- A harness self-test proves the point: two tests that reset and drive the same global scenario are run in invocation 2 in both orders and must both pass; a test marked for invocation 1 that tries to reset fails with the guard's message; after the session, the live mapping count of every simulator equals the file count on disk.
- The e2e job has its own Compose stack and is single-worker.

---

## 5. Scenario Catalogue

The tracker's "must have" list, rewritten for this build. **Sim** refers to a row of SIM §5. Each scenario names its tier and the work package whose PR brings the test; the tests for a build target arrive with that target, not later.

### 5.1 Financial safety (Build Gate)

| Scenario | Proves | Tier | Sim | WP |
|---|---|---|---|---|
| Idempotency, in one test without a reset: key A paid; A sent again; key B, unseen, same biller; status(B) before B is sent | A replays as `duplicate` with the same ref and `executed_at` (FIN_004 is success); B is a fresh payment with a different ref; status(B) was NOT_FOUND | integration | B4k, B11, B12 | WP-27 |
| Crash A, B, C (before and after the module's transaction B), D and crash before lock release | FTS v1.3 §4.5 recovery in a fresh process (§4.2). B: **zero** payment calls before the crash, exactly one after, carrying the persisted key and `recovery: resubmit`. C-after-B: `reconcile()` is a no-op and the payment is audited once | crash | B4k, B10–B12 | WP-28 |
| Pending ledger key | Ledger `pending` + plain re-dispatch → `MOD_EXECUTION_UNCONFIRMED`, no provider call; + `recovery: resubmit` → one call with the same key; two concurrent dispatches with one key → one provider call (MR v1.2 §6.4) | integration | B4k | WP-27 |
| Unknown is not failed | In `execute` after Phase 1: module raises, returns an invalid envelope, or overruns the deadline → session stays EXECUTION, lock held, Healer resolves; the same fault **before** the module's transaction A → FAILED (MR v1.2 §6.5) | integration + crash | B4k, B10 | WP-27 |
| Prepare never pays | No `POST /payment` is sent from a `phase: prepare` dispatch; the Gateway refuses one if a module tries | integration | B1, A7 | WP-27 |
| Family daily limit | Two payers, two billers, the last ₹3,000 of the limit, released together → exactly one passes; a timed-out payment keeps counting; limit lowered between approval and execution → refused; raised → the old limit still binds; resubmission does not reserve twice (Finance PRD §4.6) | integration | B4k, B10 | WP-27 |
| Payment pending, then settles; pending forever | Healer waits, alerts at 30 min, fails at 4 h, all by clock | crash | B6, B7, B12 | WP-24, WP-28 |
| Status answers the Healer must handle | FAILED with and without debit; SUCCESS with a ref the client never saw, `executed_at` written as the audit row's `occurred_at`; key/ref mismatch → no resubmission, admin alert (SIM §6.1) | crash | B12, B13 | WP-24 |
| Payer deletes their account while the payment is in EXECUTION | Session is not aborted; the Healer finishes as SYSTEM_ACTOR; NOT_FOUND is **not** resubmitted; the purge skips the user until the session is terminal (DM v1.4 §4.3, §7.1; FTS v1.3 §6.4) | crash | B10 | when account deletion exists (invariant 13) |
| BBPS says FAILED, with and without debit | Audit row, session FAILED, lock released, admin task only when debited | integration | B8, B9 | WP-27 |
| Two adults pay the same biller at once | One wins the `resource_lock` insert; the other gets the "already in progress" message, no second `POST /payment` | integration | B4 | WP-21 |
| Gate order | RBAC → lock → balance → passkey → CONSENT_REVERIFY; a failing gate leaves no `POST /payment` in the journal | integration | A7, A8, A5 | WP-27 |
| Audit chain under competing writers | Healer and request path interleave; chain verifies (DM Q12) with `chain_seq` 1..n. Required cases (DM v1.4 §3.18): two connections on an **empty** chain; two on an existing chain; two rows in one transaction; a caller whose `search_path` holds its own `audit_log`; a module role attempting direct DML on `audit_log` and `audit_chain_heads` | integration | — | WP-23 |
| Migration and seed | `alembic upgrade head` and the seeds run clean on an empty PostgreSQL 15; the post-registration activation fixture runs after boot (DM v1.4 §8, §9.4); a schema-diff test fails on any difference between the migration and the DM DDL | integration | — | WP-18/19 |
| Healer limits | Distributed lock held by one instance; per-run cap; system breaker opens and closes | integration | B16 | WP-24 |

### 5.2 Consent lifecycle

| Scenario | Proves | Tier | Sim | WP |
|---|---|---|---|---|
| Grant, pending → active; rejected; never approved | CM §6.1.1 paths including the 10-minute timeout by clock | integration | A1–A4 | WP-27 |
| Revoked between approval and execution | Two tests, and no more is claimed (SIM §11 OI-3): (a) `revalidation_required` set through the webhook handler's repository method → G5 polls, reads REVOKED, blocks; (b) flag FALSE, provider has revoked → G5 passes by design, the provider refuses the fetch (A13), the gateway takes the CONSENT_007 path; in both there is no payment call. Withdrawn **in the product** between approval and execution → G5 reads the record live and blocks | integration | A5, A13 | WP-27 |
| Purpose-bound consent | An active AA handle for `AA_TRANSACTION_HISTORY` does not let `PAY_BILL` through (needs `AA_BALANCE_FETCH`); consent of another family member does not count (MR v1.2 §7.3 step 6) | integration | A7 | WP-27 |
| Expiry watchdog | 7-day notice, renewal inherits `fetch_count_today` | integration | — | Phase 3 |
| Consent for a child and for a managed profile | CM v1.4 §2.5–2.6: primary grants; secondary refused while the primary exists, allowed when the primary is deleted; an admin who is not a proxy cannot grant; admin withdrawal works; the rule is re-checked at pending→active after a reassignment; renewal notice goes to the **new** primary; a managed **child** keeps the child restrictions (no analytics purpose) | integration | H1, H2 | WP-35 |
| Granting proxy deleted | Records flagged `proxy_reconfirm_required`; reminders continue; a new ABHA fetch fails with CONSENT_009; only the current primary proxy clears the flag; a provider ACTIVE status does not | integration | H1–H4 | WP-35 |
| Reminder purpose | No `HEALTH_MEDICATION_REMINDERS` consent → no schedule is processed; ABHA consent expired → reminders continue; reminder consent withdrawn → the sweep stops and says so | integration | — | WP-35 |
| Consent scope at the boundary | Over-broad bundle: resources outside the granted `hiTypes` are dropped and appear nowhere (SIM H10) | integration | H10 | WP-35 |
| DPI purpose without a handle | The `enforce_dpi_handle` trigger rejects the row | integration | — | WP-19 |

### 5.3 Access control and privacy

| Scenario | Proves | Tier | WP |
|---|---|---|---|
| Role × module matrix | Generated from `role_module_permissions`: every role against every intent, deny by default | unit + integration | WP-25 |
| Public surface | Finance, health, vault metadata and member PII never render on the Kitchen Tablet, whoever is logged in | integration + e2e | WP-30, WP-33 |
| Vault visibility matrix | Every role × class × visibility × holder type across show, list, duplicate link and error text; hidden versus absent identical **including narrowed family-class documents** and dependents' documents seen by a non-guardian; a duplicate link never returns a row the requester may not see; effective visibility follows a role change before the hook runs (Vault PRD v0.3 §4.6, §6, §8) | unit (generated) + integration | WP-33 |
| Vault reminder copy policy | The reduced admin copy has exactly two fields, is absent when either switch is off, never reaches a public surface; tested apart from the matrix | unit | WP-33 |
| Vault consent binding | A shared document is fetched with the holder's handle; an expired holder consent blocks every viewer; a link whose account owner is not the actor is refused (Vault PRD v0.3 §4.7) | integration | WP-33 |
| Health recipients and deadlines | Each subject kind × `admins_get_copies` × per-medicine sharing: an adult's doses reach no admin unless shared; a managed profile's MISSED always does. Deadlines stored on the dose: a settings or timeout change does not move an open dose; every kernel timeout from 5 to 1440 yields `escalate_at < missed_at` (Health PRD v0.3 §4.6) | unit + integration | WP-35 |
| Proxy authority | Only assigned proxies act for a managed profile; `hierarchy` and `notify_block` rules | integration | WP-35 |
| Cardinality and last admin | Limits hold under concurrent inserts; the last admin cannot be removed or demoted | integration | WP-37 |
| Soft delete | Queries joining `users` ignore deleted rows unless marked historical | integration | WP-37 |
| Module isolation | As the exact provisioned role: granted views and both audit functions work (schema USAGE present); `core` tables, `audit_chain_heads` and other modules' schemas are denied; CREATE in `core` is denied; import-linter contract holds (MR v1.2 §7.2) | integration + CI | WP-05, WP-25 |
| Boot | Missing dependency; dependency excluded by a late probe failure; ImportError in a depended-on module; duplicate intent; manifest drift on a non-deactivatable module (abort). No route exists for any excluded module (MR v1.2 §8.1). Semantic-validation counterexamples S1–S8 are rejected (§4.3) | integration | WP-25 |

### 5.4 DPI resilience

| Scenario | Proves | Tier | Sim | WP |
|---|---|---|---|---|
| AA fourth fetch in an hour: **local** denial | Three slots consumed through the real Redis Lua script, provider healthy (A6/A7 would answer 200). The fourth request is refused by the budget check and the journal shows **no** fourth `POST /FI/request`; cached value served; message shown. A broken budget that forwards the call fails this test, which v0.1's use of the 429 stub would not have caught | integration | A6, A7 (must stay unused) | WP-26 |
| AA provider says 429 | A different test: budget has room, the provider answers 429 (A10) → `MOD_DPI_RATE_LIMITED`, breaker count unchanged | integration | A10 | WP-26 |
| 429 is not a failure | Breaker count unchanged after 429s | unit + integration | A10, B14 | WP-26 |
| Three failures open the breaker; half-open probe closes it | RB §8 per-DPI values, by clock | integration | A11, B15, H8 | WP-26, WP-35 |
| Redis down | Budgets fail open, except BBPS which fails closed: with Redis stopped, the journal shows **no** `POST /payment` and the user gets the fail-closed message; the AA fetch in the same state does reach the simulator | integration | B4k, A6 | WP-26 |
| Module breaker | Five `MOD_DPI_RATE_LIMITED` or refusals in a row do not open it; five timeouts do; the half-open probe is a read intent (MR v1.2 §6.5) | unit + integration | — | WP-25 |
| FHIR partial and malformed | Partial data returned and flagged; no breaker trip | unit + integration | H5, H6 | WP-35 |
| Chaos run | No 5xx from the application; every failure surfaces as a FIN or MOD code | on demand | SIM §7.2 | WP-41 |

### 5.5 Security checks that are tests

| Check | Proves | Tier |
|---|---|---|
| `X-Simulate-*` stripped at the edge; never forwarded when `SIMULATOR_MODE=false`; no body field, query parameter or cookie can create the directive | SIM §3.2 | unit |
| LLM gateway payload | The test captures the **actual outbound request** at the hosted provider's HTTP boundary (a recording transport), not the structured context the code meant to send. Cases: clean utterance; an utterance that itself contains a seed name, a phone number, a VPA, a PAN-shaped and an Aadhaar-shaped string, and a consent handle. Expected: identifiers are redacted to typed placeholders before the hosted call (`<PERSON_1>`, `<PHONE>`), or the request is routed to the local model / refused, as the LLM gateway spec decides; never sent as typed. Structured context is validated against an allowlist schema (roles, module names, amounts), so a new field cannot leak by default (AGENTS.md §5, PII boundary) | unit + integration |
| Audit `details` | Every action code has a typed payload model with `extra = "forbid"` (DM v1.4 §6.1 for module codes; the kernel codes with the planned audit-log implementation spec, tracker parking lot). Tests: each model accepts its canonical example; rejects an unknown key, a free-text value where an enum is declared, and explicit negative cases (a display name, a phone number, a drug name, a document number, a date of birth, an "old/new value" JSON blob). Enum and purpose codes are legitimate payload values, so "UUIDs and amounts only" was too narrow a description. The seed-pattern scan stays as a **supplement** over everything written during the integration run; it is not the proof | unit + integration |
| Simulator journal | No request body leaving the application carries seed PII (SIM §8.3) | integration |
| Application DB grants | The app user has no UPDATE or DELETE on `audit_log` | integration |
| Test-only surface refuses to exist outside tests | Boot is refused when `CRASH_AT`, the test control endpoint or a simulate-directive source is configured with `APP_ENV` ≠ `test` (§4.2) | integration |
| Settings cannot weaken a gate | For each module's settings: no value inside the declared bounds lowers the ₹50 buffer, removes a passkey, reorders gates, or widens who receives another adult's data (MR v1.2 §6.6) | unit |

Penetration testing and webhook forgery tests are out of scope until the threat model (WP-42) says what to test.

---

## 6. Test Data

- **The Sharma family (DM §8) is the canonical fixture.** One loader in `tests/fixtures/` builds it; tests do not hand-write users.
- **Factories for variants**: a family at each cardinality limit, a family with two admins, a minor with a legal guardian and no parents, a managed profile whose primary proxy is deleted, a consent expiring tomorrow. Factories start from the seed and change one thing.
- **Everything is synthetic.** Phone numbers from the `+91 98765 432xx` seed range only; VPAs at `@simbank`; ABHA addresses at `sim.*@abdm`; no real hospital, bank, biller account or person. `tools/check_fixtures_pii.py` (with WP-18) greps fixtures and stubs for patterns that look real (12-digit Aadhaar-shaped numbers, real bank VPA handles, PAN-shaped strings outside the redacted form) and fails CI.
- There is no production data and no "anonymised production data" tier. If a commercial phase ever creates one, it gets its own section then.

---

## 7. CI: Jobs, Gates and Budgets

| Job | Trigger | Runs | Required to merge | Budget |
|---|---|---|---|---|
| `docs` | every PR (exists today, `.github/workflows/docs-checks.yml`) | `tools/docs_index.py --check`, `tools/living_docs_check.py`, `tools/xref_check.py --strict`. WP-06 keeps this job as it is when it adds the rest | yes | 1 min |
| `lint` | every PR | ruff, import-linter, `tools/check_importlib.py`, fixture PII check, secret scan (gitleaks) | yes | 1 min |
| `unit` | every PR | `tests/unit`, random order, coverage | yes | 2 min |
| `integration` | every PR | `tests/integration`, `tests/dpi_contracts` with Testcontainers and simulators: invocation 1 in parallel, then invocation 2 exclusive (§4.3) | yes | 6 min |
| `crash` | **every PR**, from WP-28, and on `main` | `tests/crash_scenarios` | yes, from WP-28 | 4 min |
| `web` | every PR touching `web/` | Vitest, type check, build | yes, from WP-30 | 3 min |
| `e2e` | every PR to `main` once WP-31 lands | Playwright flows against Compose; trace kept; retry rules in §7.1 | yes, from WP-31 | 8 min |
| `invariants` | every PR, from WP-32; runs last, `needs` the test jobs | `tools/check_invariant_tests.py` over the JUnit reports and `tests/invariants.toml` (§3) | yes | seconds |
| `audit-deps` | every PR | `pip-audit`, `npm audit --omit=dev` | advisory; a HIGH finding opens an issue | 1 min |
| `load`, `chaos` | on demand, and at M4 and M5 | k6 slice run; chaos run with a recorded seed | no | — |

- **Why `crash` has no path filter (v0.2).** v0.1 ran it only when `familylifeos/kernel`, `modules/finance` or `wiremock/` changed. Recovery also depends on the SDK envelopes and clients, the migrations, the dependency lockfile, the fixtures, Compose and the workflow file itself, and a path-filtered required check reports nothing when skipped, which branch protection reads as missing or, worse, as satisfied. A complete dependency-aware selector would need its own tests; four minutes on every PR is cheaper and always gives a verdict. The same reasoning applies to every required job here: none is path-filtered except `web`, which always reports (it exits 0 with "no web changes" as its first step and never skips).
- **Coverage gate** (enabled by WP-32, informational before): line coverage ≥ 80 % on `familylifeos/kernel` and on each `modules/*` package, and coverage may not fall on a PR. Coverage of `tests/`, migrations and generated code is excluded. The number is a floor, not a goal: a payment-path function with 100 % line coverage and no crash test is not covered.
- **Green `main`.** A red `main` stops feature merges until it is green. The author of the breaking PR fixes or reverts; nobody rebases around it.
- CI runs on Linux runners and is the source of truth; local runs on Windows are a convenience (Roadmap §5).

### 7.1 Flaky tests

1. A test that fails without a code change is reported as an issue labelled `needs-triage` with the run link. It is a bug.
2. It may be marked `@pytest.mark.quarantine` with the issue number in the marker. Quarantined tests still run and report, but do not gate.
3. At most three tests are quarantined at any time, and **never** a test in `tests/crash_scenarios` or an invariant-named test: those block until fixed.
4. No blanket retries, and **a retry never turns a safety failure green (v0.2).** Tests marked `safety` (§2) gate on their **first** result, at every tier including `e2e`: if a public-surface, visibility, consent-scope, double-payment, crash or invariant assertion fails once, the job is red, whatever a second run says. The harness may re-run such a test once to collect a trace for the report; the re-run's outcome is recorded and ignored. Other `e2e` tests get one retry for infrastructure noise (browser start-up, container readiness), classified by the failure: a retry is allowed only when the first failure was a harness error, not an assertion; every retried test is listed in the job summary and opens a `needs-triage` issue when it recurs.

---

## 8. Performance and Load

Portfolio targets, from NFR v2.2 §6 and Roadmap §8: the two slices under ten concurrent users against simulators, each half (intent → approval prompt; approval → confirmation) at P95 < 2.0 s excluding human wait, with `SIM_LATENCY=realistic` so the number is not flattered. The NFR's commercial targets (1 000 concurrent users) are recorded there and are not tested. Results are written to `docs/reference/perf/` with the commit, the seed and the machine, at M4 and M5.

---

## 9. Who Writes What

| Agent | Testing responsibilities |
|---|---|
| Codex | Writes the tests with the code, in the same PR; owns the fixtures module, the clock contract's seams (§4.1), the crash harness (§4.2), simulator ownership (§4.3), the Healer's `run_once()`; keeps CI within budget |
| Claude Code | Reviews test names and scenarios against the specs before reading the implementation; owns this document and the scenario catalogue; writes the invariant list the checker reads (AGENTS.md §4) |
| Gemini | Generates fixtures, stub JSON, FHIR samples, the role × intent and visibility matrix tables from spec tables; may delegate those to the local model under `.agents/workflows/delegate-to-local.md`; never writes tests for payment, consent or audit paths |
| Founder | Tests passkeys on real devices (WP-30); decides when a quarantined test is deleted rather than fixed |

Review rule for every PR with tests: the reviewer states which invariant or catalogue row each new test serves. A test nobody can place is either missing a catalogue row (add it here) or not needed.

---

## 10. Non-Goals

- Native mobile testing (Appium): there is no native app (AGENTS.md §5).
- Jest, Supertest or any second backend runner; Cypress.
- A hired QA engineer or DevOps engineer; a test-report server (Allure, ReportPortal). CI artefacts and the job summary are enough.
- Anonymised production data; staging environments other than the demo host.
- Penetration tests, fuzzing of DPI webhooks, mutation testing. The first two wait for the threat model; mutation testing is a good P2 idea for `kernel/finance` and nothing more for now.
- Scheduled "weekly", "monthly" or "quarterly" runs.

---

## 11. Open Issues

| # | Issue | Severity | Path |
|---|---|---|---|
| OI-1 | The invariant checker needs a stable way to read invariant numbers from AGENTS.md §4; today they are a numbered Markdown list that has been renumbered once already (35 → 37 items). | LOW | WP-32: parse the list; add a comment anchor per invariant only if parsing proves brittle |
| OI-2 | Testcontainers on Windows through Docker Desktop and WSL 2 is slow; acceptable because CI is the source of truth, but the founder's local loop matters for the demo. | LOW | WP-14 documents a `compose up` + `pytest -m "not integration"` loop |
| OI-3 | The golden utterance set does not exist yet, and who curates the Hindi and Hinglish lines is undecided. | MEDIUM | WP-29: Claude drafts, the founder corrects the Hindi, Gemini expands variants |
| OI-5 | The hosted-LLM privacy test (§5.5) needs a decision the LLM gateway has not written down yet: redact identifiers found in the utterance, route such utterances to the local model, or refuse. | MEDIUM | LLM gateway design (WP-29); the test is written against whichever rule is chosen, and until then asserts only "never sent as typed" |
| OI-4 | `e2e` on every PR to `main` costs eight minutes per run on a public repository's free minutes; fine at this volume. | LOW | Revisit only if PR volume makes queueing visible |

---

## 12. Q&A

| Asked by | Question | Answer |
|---|---|---|
| Engineering | Why is 80 % the coverage floor and not higher for payment code? | Because line coverage is the wrong instrument for payment safety. The instruments are the crash scenarios, the invariant-named tests and the journal assertions, all of which gate. Coverage catches untested files, nothing more. |
| Engineering | Why run Playwright from pytest instead of its own runner? | One runner, one fixture system, one report. The end-to-end tests reuse the seed loader, the simulator helpers and the fake clock. |
| Reviewer | What stops an agent from making a failing test pass by weakening it? | Invariant-named and crash tests cannot be quarantined, skipped or xfailed without turning the `invariants` gate red (§3, §7.1), a change to `tests/invariants.toml` is reviewed like a test deletion, the reviewer is a different agent that reads test diffs first (§9), and a PR that deletes or loosens such a test must say so in its summary or is rejected. |
| Product | How do we know the demo will not flake in front of someone? | The demo uses fixed utterances from the golden set, identifier-selected simulator scenarios and a seeded latency profile. The same flows gate every merge. |
