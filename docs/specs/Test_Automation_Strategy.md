# Test Automation Strategy

_What is tested at which level, how tests stay deterministic, what CI enforces, and who writes what, for the portfolio build_

> **Status:** DRAFT v0.1 — for review (Codex) · **Author:** Shantanu Chaudhary (Lead Product Architect), drafted with Claude Code · **Last content change:** 2026-09-17
> **Priority:** P1. Execution Plan WP-13. Formalises the tracker's "Test Automation Strategy" section for the stack chosen in AGENTS.md §5, and replaces it; the tracker keeps a pointer.
> **Depends on:** AGENTS.md §4 (invariants), §5 (stack), §6 (working rules) · FTS v1.2 §4.5 (crash scenarios), §6 (Healer) · Tech_Spec_Simulator_Architecture v0.1 (SIM) §3–§5, §8 · NFR v2.2 §1, §6 · Execution Plan §7 (Definition of Done), §7.2 (invariant coverage map) · Roadmap §5, §8.
> **Cited elsewhere as:** Test strategy, TAS §n.

## 0. Document Governance

| Version | Date | Description of Change | Author |
|---|---|---|---|
| v0.1 | 2026-09-17 | First version. Tiers and directories, invariant-named tests, determinism rules, scenario catalogue tied to simulator rows, CI jobs and gates, flaky-test policy, security checks, agent responsibilities, explicit non-goals. Drops the tracker section's assumptions that do not fit the project: a hired QA engineer, Jest and Supertest for the backend, Appium, anonymised production data, a calendar of weekly and monthly runs. | Shantanu Chaudhary (with Claude Code) |

---

## 1. Scope and Principles

This is a payments-and-health product built by one person and three AI agents. Tests are the only reviewer that never gets tired, so the strategy is strict where money, consent and the audit log are involved and deliberately plain everywhere else.

1. **The invariants are the test plan.** Every testable invariant in AGENTS.md §4 has at least one test named after it (§3). A reviewer reads test names before reading code.
2. **Crash scenarios are written first.** FTS §4.5's scenarios exist as failing tests before the Healer exists (Roadmap §5). They are the Build Gate.
3. **Deterministic or deleted.** No sleeps, no wall-clock, no real network, no real LLM in any gating test (§4). A test that fails one run in fifty is a defect in the test or in the product, and is treated as one (§7).
4. **One runner per language.** pytest drives everything in Python, including Playwright (`pytest-playwright`); Vitest covers `web/` units. No second backend test framework.
5. **The simulators are part of the test system.** Scenario selection, resets and journal assertions follow SIM §3, §4.4 and §8. This document does not restate them.
6. **Tests travel with the change.** A PR that changes behaviour without changing tests is rejected in review (Execution Plan §7, item 2), whoever wrote it.
7. **No plan by calendar.** Nothing here runs "weekly" or "monthly". Every suite is triggered by an event: a commit, a PR, a merge, a milestone, or a person asking (AGENTS.md §6, no dates).

---

## 2. Tiers, Directories and Tools

| Tier | Directory | Tool | What belongs here | Talks to | Share of tests (guide, not gate) |
|---|---|---|---|---|---|
| Unit | `tests/unit/` | pytest | Pure logic: FSM transitions, hash-chain canonicalisation, gate ordering, idempotency-key lifecycle, budget arithmetic, IST window maths, manifest validation, visibility rules, FHIR field extraction, error mapping | nothing (no DB, no Redis, no HTTP) | ~60 % |
| Integration | `tests/integration/` | pytest + Testcontainers (PostgreSQL 15, Redis) + the WireMock simulators | Anything that needs real SQL semantics or real Redis: resource lock races, cardinality races with `SELECT … FOR UPDATE`, audit chain under concurrent writers, Lua budget scripts, breaker state, migrations, kernel views and grants, module isolation (a module role cannot read `core` tables) | containers only | ~30 % |
| Crash scenarios | `tests/crash_scenarios/` | pytest, integration fixtures, `CRASH_AFTER` hook, Healer `run_once()` with injected clock | FTS §4.5 A–D and the lock-release case; pending and stuck-pending payments; Healer caps and its own breaker | containers + `sim-bbps`, `sim-aa` | counted in integration |
| DPI contracts | `tests/dpi_contracts/` | pytest + jsonschema | SIM §8.1: stub ↔ schema ↔ gateway model agreement; RB §9.5's three tests | simulators | small |
| End-to-end | `tests/e2e/` | pytest-playwright (Chromium; virtual WebAuthn authenticator) | Whole flows through the PWA: "Priya pays BESCOM bill", "Nani's medication reminder via proxies", the Kitchen Tablet block, Vault show-and-hide | full Compose stack | ~10 %, and few |
| Web unit | `web/src/**/*.test.ts(x)` | Vitest + Testing Library | Component states: approval screen, SIMULATOR banner, visibility chip, error rendering from i18n keys | nothing | as needed |
| Load | `tests/load/` | k6 | The two slices under light concurrency; P95 per NFR §1 | demo deployment or local Compose | on demand |

Rules of placement: if a test needs a database it is not a unit test; if it needs a browser it is an end-to-end test; if it can be a unit test it must be one. Markers: `@pytest.mark.integration`, `crash`, `contract`, `e2e`, `sim_serial` (SIM §4.4), `quarantine` (§7).

---

## 3. Invariant-Named Tests

- A test that protects an invariant from AGENTS.md §4 is named `test_invariant_<n>_<what_it_proves>`, for example `test_invariant_16_idempotency_key_persisted_before_external_call`, `test_invariant_17_lock_released_only_after_phase2_commit`, `test_invariant_6_public_surface_never_shows_vault_metadata`.
- The map of invariants to test modules and work packages is Execution Plan §7.2 and is not copied here.
- `tools/check_invariant_tests.py` (written with WP-32) reads the numbered invariants from AGENTS.md §4 and the collected test names, and fails CI when an invariant that is in scope for the current milestone has no test. In scope at M2: 1–7 as far as the Finance slice touches them, 8–11, 15–24, 25–28 for AA and BBPS, 30–35. At M3 add 12 (minors, managed profiles), the Vault visibility matrix and ABHA's 25–28. Invariants 36–37 are review criteria, not tests. Invariants 13 and 14 (account deletion, webhooks) are tested when the features exist; until then the script lists them as "not yet applicable", never silently skips them.
- Renumbering an invariant in AGENTS.md means renaming its tests in the same PR. The script makes forgetting that visible.

---

## 4. Determinism Rules

| Source of nondeterminism | Rule |
|---|---|
| Time | All time comes from an injectable `Clock`. Tests use a fake clock and advance it; no `sleep`, no `datetime.now()` in product code outside the clock. The Healer's 5-minute cadence, the 30-minute and 4-hour zombie branches, the 24-hour idempotency window, IST midnight resets and consent expiry are all tested by advancing the clock |
| Background work | The Healer, the expiry watchdog and module sweeps expose `run_once()`. Tests call it. No test waits for a scheduler |
| Crashes | `CRASH_AFTER=<point>` aborts the process path at a named point in the two-phase commit. The hook is compiled in only when `APP_ENV=test`; a unit test asserts that it is inert otherwise |
| Identifiers | UUIDs are generated through an injectable factory so a test can pin the idempotency key it then looks for in the simulator journal |
| Randomness | Backoff jitter takes a seeded generator in tests. Chaos mode is seeded (`CHAOS_SEED`, SIM §7.2) and never part of a gating job |
| Network | Only the simulators and Testcontainers. The test network has no route out; a test that needs the internet is wrong |
| LLM | Gating tests use the deterministic stub behind the LLM gateway. The golden utterance set (about fifty English, Hindi and Hinglish utterances with expected intents) runs against the stub in CI as a gate, and against the local and hosted models as a **report** only (Roadmap §8, routing accuracy) |
| Simulator state | `reset_simulator()` at the start of every stateful test; `sim_serial` tests run in one worker (SIM §4.4) |
| Order | Tests must pass in random order (`pytest-randomly`) and alone. Shared state between tests is a defect |
| Browser | Playwright's virtual authenticator stands in for passkeys; traces and screenshots are kept on failure |

---

## 5. Scenario Catalogue

The tracker's "must have" list, rewritten for this build. **Sim** refers to a row of SIM §5. Each scenario names its tier and the work package whose PR brings the test; the tests for a build target arrive with that target, not later.

### 5.1 Financial safety (Build Gate)

| Scenario | Proves | Tier | Sim | WP |
|---|---|---|---|---|
| Same idempotency key submitted twice | One payment, second call returns the first result (FIN_004 is success) | integration | B4, B5 | WP-27 |
| Crash A, B, C, D and crash before lock release | FTS §4.5 recovery, with the journal showing one key across re-submission | crash | B4, B10–B12 | WP-28 |
| Payment pending, then settles; pending forever | Healer waits, alerts at 30 min, fails at 4 h, all by clock | crash | B6, B7, B13 | WP-24, WP-28 |
| BBPS says FAILED, with and without debit | Audit row, session FAILED, lock released, admin task only when debited | integration | B8, B9 | WP-27 |
| Two adults pay the same biller at once | One wins the `resource_lock` insert; the other gets the "already in progress" message, no second `POST /payment` | integration | B4 | WP-21 |
| Gate order | RBAC → lock → balance → passkey → CONSENT_REVERIFY; a failing gate leaves no `POST /payment` in the journal | integration | A7, A8, A5 | WP-27 |
| Audit chain under competing writers | Healer and request path interleave; chain verifies (DM Q12) | integration | — | WP-23 |
| Healer limits | Distributed lock held by one instance; per-run cap; system breaker opens and closes | integration | B16 | WP-24 |

### 5.2 Consent lifecycle

| Scenario | Proves | Tier | Sim | WP |
|---|---|---|---|---|
| Grant, pending → active; rejected; never approved | CM §6.1.1 paths including the 10-minute timeout by clock | integration | A1–A4 | WP-27 |
| Revoked between approval and execution | CONSENT_REVERIFY reads live and blocks; no payment call | integration | A5 | WP-27 |
| Expiry watchdog | 7-day notice, renewal inherits `fetch_count_today` | integration | — | Phase 3 |
| Consent for a minor and for a managed profile | `parental_consent_user_id` / `proxy_consent_user_id` rules (CM §2.5, v1.3 §2.6), secondary proxy only when the primary is unavailable | integration | H1, H2 | WP-35 |
| DPI purpose without a handle | The `enforce_dpi_handle` trigger rejects the row | integration | — | WP-19 |

### 5.3 Access control and privacy

| Scenario | Proves | Tier | WP |
|---|---|---|---|
| Role × module matrix | Generated from `role_module_permissions`: every role against every intent, deny by default | unit + integration | WP-25 |
| Public surface | Finance, health, vault metadata and member PII never render on the Kitchen Tablet, whoever is logged in | integration + e2e | WP-30, WP-33 |
| Vault visibility matrix | Every role × class × visibility × holder type across show, list, reminder text and error text; VAULT_006 identical for "hidden" and "absent" (Vault PRD §8) | unit (generated) | WP-33 |
| Proxy authority | Only assigned proxies act for a managed profile; `hierarchy` and `notify_block` rules | integration | WP-35 |
| Cardinality and last admin | Limits hold under concurrent inserts; the last admin cannot be removed or demoted | integration | WP-37 |
| Soft delete | Queries joining `users` ignore deleted rows unless marked historical | integration | WP-37 |
| Module isolation | A module's DB role cannot select from `core` tables or another module's schema; import-linter contract holds | integration + CI | WP-05, WP-25 |

### 5.4 DPI resilience

| Scenario | Proves | Tier | Sim | WP |
|---|---|---|---|---|
| AA fourth fetch in an hour | Budget check blocks before the call; cached value served; message shown | integration | A10 | WP-26 |
| 429 is not a failure | Breaker count unchanged after 429s | unit + integration | A10, B14 | WP-26 |
| Three failures open the breaker; half-open probe closes it | RB §8 per-DPI values, by clock | integration | A11, B15, H8 | WP-26, WP-35 |
| Redis down | Budgets fail open, except BBPS which fails closed | integration | — | WP-26 |
| FHIR partial and malformed | Partial data returned and flagged; no breaker trip | unit + integration | H5, H6 | WP-35 |
| Chaos run | No 5xx from the application; every failure surfaces as a FIN or MOD code | on demand | SIM §7.2 | WP-41 |

### 5.5 Security checks that are tests

| Check | Proves | Tier |
|---|---|---|
| `X-Simulate-*` stripped at the edge; never forwarded when `SIMULATOR_MODE=false` | SIM §3.2 | unit |
| LLM gateway payload | A hosted-model request contains the utterance and non-PII context only; seeded names, phone numbers and identifiers never appear (AGENTS.md §5, PII boundary) | unit |
| Audit `details` | UUIDs and amounts only; a property test rejects anything that looks like a name, phone number, VPA or account number | unit |
| Simulator journal | No request body leaving the application carries seed PII (SIM §8.3) | integration |
| Application DB grants | The app user has no UPDATE or DELETE on `audit_log` | integration |
| `CRASH_AFTER` inert outside tests | §4 | unit |

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
| `lint` | every PR | ruff, import-linter, `tools/check_importlib.py`, fixture PII check, secret scan (gitleaks) | yes | 1 min |
| `unit` | every PR | `tests/unit`, random order, coverage | yes | 2 min |
| `integration` | every PR | `tests/integration`, `tests/dpi_contracts` with Testcontainers and simulators | yes | 6 min |
| `crash` | every PR that touches `familylifeos/kernel`, `modules/finance` or `wiremock/`; always on `main` | `tests/crash_scenarios`, single worker | yes, from WP-28 | 4 min |
| `web` | every PR touching `web/` | Vitest, type check, build | yes, from WP-30 | 3 min |
| `e2e` | every PR to `main` once WP-31 lands | Playwright flows against Compose; one retry, trace kept | yes, from WP-31 | 8 min |
| `invariants` | every PR, from WP-32 | `tools/check_invariant_tests.py` | yes | seconds |
| `audit-deps` | every PR | `pip-audit`, `npm audit --omit=dev` | advisory; a HIGH finding opens an issue | 1 min |
| `load`, `chaos` | on demand, and at M4 and M5 | k6 slice run; chaos run with a recorded seed | no | — |

- **Coverage gate** (enabled by WP-32, informational before): line coverage ≥ 80 % on `familylifeos/kernel` and on each `modules/*` package, and coverage may not fall on a PR. Coverage of `tests/`, migrations and generated code is excluded. The number is a floor, not a goal: a payment-path function with 100 % line coverage and no crash test is not covered.
- **Green `main`.** A red `main` stops feature merges until it is green. The author of the breaking PR fixes or reverts; nobody rebases around it.
- CI runs on Linux runners and is the source of truth; local runs on Windows are a convenience (Roadmap §5).

### 7.1 Flaky tests

1. A test that fails without a code change is reported as an issue labelled `needs-triage` with the run link. It is a bug.
2. It may be marked `@pytest.mark.quarantine` with the issue number in the marker. Quarantined tests still run and report, but do not gate.
3. At most three tests are quarantined at any time, and **never** a test in `tests/crash_scenarios` or an invariant-named test: those block until fixed.
4. No blanket retries. Only `e2e` gets one retry, and a test that needed it is listed in the job summary.

---

## 8. Performance and Load

Portfolio targets, from NFR v2.2 §6 and Roadmap §8: the two slices under ten concurrent users against simulators, each half (intent → approval prompt; approval → confirmation) at P95 < 2.0 s excluding human wait, with `SIM_LATENCY=realistic` so the number is not flattered. The NFR's commercial targets (1 000 concurrent users) are recorded there and are not tested. Results are written to `docs/reference/perf/` with the commit, the seed and the machine, at M4 and M5.

---

## 9. Who Writes What

| Agent | Testing responsibilities |
|---|---|
| Codex | Writes the tests with the code, in the same PR; owns the fixtures module, the crash hook, the Healer's `run_once()` seams; keeps CI within budget |
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
| OI-4 | `e2e` on every PR to `main` costs eight minutes per run on a public repository's free minutes; fine at this volume. | LOW | Revisit only if PR volume makes queueing visible |

---

## 12. Q&A

| Asked by | Question | Answer |
|---|---|---|
| Engineering | Why is 80 % the coverage floor and not higher for payment code? | Because line coverage is the wrong instrument for payment safety. The instruments are the crash scenarios, the invariant-named tests and the journal assertions, all of which gate. Coverage catches untested files, nothing more. |
| Engineering | Why run Playwright from pytest instead of its own runner? | One runner, one fixture system, one report. The end-to-end tests reuse the seed loader, the simulator helpers and the fake clock. |
| Reviewer | What stops an agent from making a failing test pass by weakening it? | Invariant-named and crash tests cannot be quarantined (§7.1), the reviewer is a different agent that reads test diffs first (§9), and a PR that deletes or loosens such a test must say so in its summary or is rejected. |
| Product | How do we know the demo will not flake in front of someone? | The demo uses fixed utterances from the golden set, identifier-selected simulator scenarios and a seeded latency profile. The same flows gate every merge. |
