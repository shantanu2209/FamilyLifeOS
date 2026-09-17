# Roadmap: FamilyLifeOS Portfolio Build

> **Status:** DRAFT v0.2 — sequence-only plan, no dates or capacity assumptions (founder ruling 2026-09-17) · **Author:** Shantanu Chaudhary (Lead Product Architect), drafted with Claude Code · **Last content change:** 2026-09-17
> **Scope:** The order of work from tooling install to a demoable, documented kernel with two vertical slices ("Priya pays the BESCOM electricity bill" and "Nani's medication reminder via proxies") running against DPI simulators, in portfolio mode (tracker → Decision Log). Phases, gates, milestones, risks, metrics, and a short "what changes if this goes commercial" section. Work packages live in `docs/Execution_Plan.md`; audience and artefacts in `docs/strategy/GTM_Plan.md`.
> **Supersedes:** For planning purposes only: tracker → "Milestone Tracker" (Feb-2026 week numbers), tracker → "Technology Decisions", "Team/Hiring Decisions", "Feature Prioritization" and "Operational Decisions", and the tracker's "Test Automation Roadmap" weeks. Master Context §8 (phasing with budgets and licences) stays the reference for commercial mode and is not the current plan.

## 0. Document Governance

| Version | Date | Description of Change | Author |
|---|---|---|---|
| v0.1 | 2026-09-17 | First draft: five phases over 13 weeks, week-by-week calendar, milestones M0–M5 with dates, effort model in founder hours, four-agent roster. | Shantanu Chaudhary (with Claude Code) |
| v0.2 | 2026-09-17 | Founder ruling: no assumption about hours per week and no target dates. Calendar, dated decision points and the hours-based effort model removed; the plan is now an ordered sequence with gates. Roster reduced to three agents (Claude Code, Codex, Gemini in Antigravity); local models are an internal matter of the Gemini lane. Hosted LLM default set to Claude Haiku. | Shantanu Chaudhary (with Claude Code) |

---

## 1. Planning basis

- **Mode:** portfolio first (tracker → Decision Log). The output is a working kernel plus two slices against WireMock simulators, built to the quality the frozen specs demand. No licences, no real-money DPI integration, no hosting beyond one demo deployment. Commercial expansion is possible later; §7 lists what would change.
- **No dates, no capacity assumption.** The project has paused before and may again. This roadmap therefore fixes **order and gates**, not a calendar: a phase starts when its entry condition is met and is done when its exit condition is met, however long that takes. Nothing in the repository should state a target date or an expected number of founder hours. If a date ever matters (for example an external deadline), it goes in the tracker's Decision Log as a decision, not here as an assumption.
- **Team:** the founder and three AI agents: Claude Code (architecture, specs, reviews, planning), Codex (implementation against frozen specs, second reviewer), Gemini in Antigravity (routine generation from spec tables; it may delegate mechanical subtasks to local models it orchestrates itself, and stays accountable for the result). Coordination is through GitHub issues, labels, branches and PRs plus the repository channel under `coordination/` (protocol: `coordination/README.md`); every PR is reviewed by an agent other than its author; the founder merges.
- **Starting state (2026-09-17):** documentation only. Data Model v1.3 and Module Registry v1.1 await Codex review round 2; FTS v1.2 and RB v1.2 are frozen; CM v1.3 is the frozen v1.2 text plus one addition (§2.6 proxy consent) that goes through the same round 2; PRD Core v2.2, NFR v2.2 and Master Context v2.1 are aligned; module PRDs for Vault, Finance and Health are at draft v0.1; `Security_Threat_Model.md` is P1, due before any internet-facing deployment. Tooling to install is listed in `docs/reference/Workstation_Setup.md`. Nothing can be built before that.

### 1.1 Scope boundaries

**In scope:** the kernel (registry, envelope, sessions, locks, audit chain, Healer, DPI gateway, LLM gateway, notification engine); the Finance module limited to `PAY_BILL` and `CHECK_BALANCE`; the Secure Vault foundation (metadata, DigiLocker simulator, `SHOW_DOCUMENT`); the Health module limited to prescriptions, medications and proxy reminders; a PWA with passkey approval, admin screens and an inbox; four WireMock simulators with contract tests and chaos mode; the crash-scenario suite; observability; one demo deployment; the threat model; the portfolio artefacts.

**Out of scope, by decision, not by omission:** ONDC and Bhashini simulators (the Bhashini stub in RB §9.3 stays parked; ONDC has none yet); WhatsApp and SMS channels; native iOS/Android shells; RabbitMQ, Kafka and Kubernetes (AGENTS.md §5, MR §2.3); disaster recovery and scalability implementation (NFR v2.2 §6–§7 state the targets; nothing is built for them); penetration testing; audit-log archival and partitioning (tracker parking lot); `PAY_RECURRING` and any Level 2 automation; the third-party module marketplace and everything in `Vision_Parking_Lot.md`; real DPI sandboxes and licence applications (§6). Each item has a named trigger in the document that parks it.

---

## 2. Phases

### Phase 0 — Tooling and agent onboarding

- **Goal:** every agent can take an issue, work on a branch, open a PR and be reviewed by another agent, with CI green on `main`.
- **Deliverables:** WSL 2 and Docker Desktop installed; the Codex desktop app opened on the repository; Antigravity signed in and reading `GEMINI.md` → `AGENTS.md` (`docs/reference/Workstation_Setup.md`); GitHub labels, milestones (without due dates) and branch protection on `main` (the issue and PR templates already exist under `.github/`); repository scaffolding (uv, Python 3.12, `ruff`, pre-commit, import-linter contract per MR §7.1) and a CI workflow running `ruff`, import-linter and `pytest` on every PR; issues created for the Phase 0 and Phase 1 work packages; each agent has read its inbox under `coordination/inbox/` and posted its first line in `coordination/STATUS.md`.
- **Definition of done:** one PR authored by Gemini or Codex, reviewed by a different agent, merged by the founder, with CI green.
- **Exit criteria:** the Phase 0 work packages are closed (Execution Plan); `uv run pytest` and `uv run lint-imports` pass on `main`.
- **Main risks:** Windows/WSL 2 friction with Docker Desktop and Testcontainers (mitigation: CI on Linux runners is the source of truth; local runs are a convenience); an agent not picking up `AGENTS.md` automatically (mitigation: the pointer files `CLAUDE.md` and `GEMINI.md`, and a first-task check that the agent can state three invariants from §4).
- **Agents:** founder installs and configures; Claude Code drafts CI and the issue set; Codex builds the scaffolding; Gemini produces the first routine PR.

### Phase 1 — Spec close-out

- **Goal:** freeze the two specs the build depends on and write the three documents implementation needs (simulator architecture, test strategy, development environment).
- **Deliverables:** Codex review round 2 of Module Registry v1.1 and Data Model v1.3; fixes applied with version bumps and governance rows; both frozen; `Tech_Spec_Simulator_Architecture.md` (WireMock stubs for AA, BBPS, ABHA, DigiLocker; scenario headers in the RB §9 `X-Simulate-*` style; BBPS PENDING→SUCCESS state machine; chaos mode per RB §9.4; contract tests per RB §9.5) with stub JSON generated by Gemini; `Test_Automation_Strategy.md` formalised from the tracker section for the chosen stack; `Development_Environment_Setup.md`; Finance module PRD accepted (Vault and Health PRDs accepted before Phase 3).
- **Definition of done:** the tracker's Build Gate pre-conditions are all ticked; AGENTS.md §3, §7 and the README status table say FROZEN for DM v1.3 and MR; no open register item blocks implementation.
- **Exit criteria:** the Phase 1 work packages are closed; a Gemini cross-reference sweep finds no dangling section references across the document set.
- **Main risks:** review round 2 reopening settled decisions (mitigation: reviewers are told the Decision Log is closed; findings are filed as issues, not fixed in place); scope creep in the simulator spec (mitigation: only the four DPIs the two slices need).
- **Agents:** Codex reviews; Claude Code applies fixes and authors the three documents; Gemini generates stub JSON, runs the cross-reference sweep and keeps the tracker matrix in sync.

### Phase 2 — Build Gate and kernel slice

- **Goal:** pass the tracker's Phase 1 Build Gate exactly as written, in its order.
- **Deliverables (in build order, mirroring tracker → Phase 1 Build Gate):** Docker Compose with PostgreSQL (all core tables from DM v1.3), Redis, WireMock BBPS (SUCCESS, FAILED, PENDING, NOT_FOUND, 429, timeout) and WireMock AA (balance fetch, consent validation), `.env.example`; Alembic `V001__initial_schema` from the DM v1.3 DDL; kernel skeleton and SDK envelope (MR §6); `resource_lock` acquire/release (DM v1.3 §3.11, FTS §9); `supervisor_sessions` lifecycle (FSM §1, DM v1.3 §3.7); audit log write with hash chain through `fn_lock_audit_tail` / `fn_append_audit` (DM v1.3 §3.18, FTS §11.3); Healer cron with distributed lock, priority queue, per-run cap and system circuit breaker (FTS §6); Module Registry boot and dispatch-time checks (MR §7.3, §8.1); DPI gateway for BBPS and AA with budgets and breakers (RB §2, §4, §8); FinanceAgent `PAY_BILL` with the five gates and Phase 2 commit (FTS §2, MR §10); crash scenarios A–D as automated tests (FTS §4.5); LLM gateway with a deterministic stub; minimal PWA approval screen with WebAuthn passkeys standing in for biometric approval; the single Playwright test "Priya pays BESCOM bill".
- **Definition of done:** the four crash scenarios and the Playwright test pass in CI on `main`; the gate checklist in the tracker is fully ticked; `main` is tagged `v0.1.0-build-gate`.
- **Exit criteria:** gate status in the tracker changed from BLOCKED to PASSED with the CI run linked; invariants in AGENTS.md §4 items 15–24 each have at least one unit test named after them.
- **Main risks:** see §5 (WebAuthn in a PWA, Healer concurrency tests, LLM parsing quality); Alembic migration drifting from the DM v1.3 DDL (mitigation: a schema-diff test that fails CI on any difference).
- **Agents:** Codex implements every build target; Claude Code reviews each PR against the cited spec section; Gemini drafts Docker Compose, the Alembic migration, WireMock stubs and fixtures, with Codex reviewing, and handles lint, docstrings and tracker sync.

### Phase 3 — Vault foundation, Health second slice, PWA

- **Goal:** prove the kernel is a kernel: a second module family (Health) and the foundational Vault run through the same registry, envelope, consent and audit paths without touching them.
- **Deliverables:** Secure Vault module (document metadata only, DigiLocker simulator sync per CM §6.3, `SHOW_DOCUMENT` "show my licence" with the public-surface block); Health module (ABHA simulator prescription → FHIR partial-parse handling per RB §5.3 → medications → reminder schedule → proxy nudges per PRD Scenario 2); notification engine as a service module with a push stand-in; family graph admin screens in the PWA (members, roles, proxies, devices, module activation per MR §8.2); Scenario 5 age-18 trigger; the second Playwright test "Nani's medication reminder via proxies".
- **Definition of done:** both E2E tests pass in one CI run; Health and Vault import only the SDK (import-linter green); no change to kernel payment, consent or audit code was needed to add them (if one was, it is recorded as a kernel gap, not hidden).
- **Exit criteria:** M3 sign-off; tracker Document Status Matrix updated; Vault and Health PRDs marked accepted.
- **Main risks:** FHIR R4 parsing rabbit hole (mitigation: parse three resource types only — MedicationRequest, DiagnosticReport, Observation — per CM §6.2.2); admin screens absorbing effort (mitigation: table-driven screens, no design pass until Phase 4).
- **Agents:** Codex builds; Claude Code reviews and writes the Health/Vault i18n key lists; Gemini generates DigiLocker and ABHA stubs and FHIR fixtures and keeps docs and tracker in sync.

### Phase 4 — Voice stand-in, observability, threat model, demo deployment, write-up

- **Goal:** make it showable and honest: a public demo URL with synthetic data, dashboards that prove the metrics in §8, a threat model before anything faces the internet, and the portfolio artefacts.
- **Deliverables:** voice stand-in (browser speech API with the confidence gate from RB §7.3, labelled "not Bhashini"); structured logs and Prometheus metrics named in RB §10.1 and MR §11 with a Grafana dashboard; k6 run producing the slice P95; `Security_Threat_Model.md` (tracker gap 8b checklist); demo deployment on a single VM or container host in an India region with TLS and no real data; hosted LLM adapter (Claude Haiku by default) behind the LLM gateway; portfolio write-up (build log), one-page architecture overview, README as landing page; a short demo video; retrospective.
- **Definition of done:** demo URL reachable over TLS; dashboard shows both flows; threat model reviewed by Codex; write-up and video published; the M5 retrospective records the commercial-or-not decision.
- **Exit criteria:** every metric in §8 has a measured value at M5.
- **Main risks:** deployment work crowding out the write-up (mitigation: deploy is a Codex task with a checklist; the founder only holds the cloud account); the threat model turning into a rewrite (mitigation: it documents mitigations and gaps; gaps become issues, not blockers, unless they affect the demo deployment itself).
- **Agents:** Claude Code authors the threat model, write-up and video script; Codex builds the voice stand-in, observability and deployment; Gemini writes PR summaries and the architecture diagram text; the founder records the video and owns the cloud and API accounts.

### Gating summary

| Phase | Cannot start until | Is done when |
|---|---|---|
| 0 | The founder has installed the tooling (`docs/reference/Workstation_Setup.md`) | First agent PR merged with CI green (M0) |
| 1 | Codex is logged in and can read the repository | DM v1.3 and MR frozen; Build Gate pre-conditions ticked (M1) |
| 2 | M1, plus Compose running locally | Crash A–D and the Playwright test green on `main`; tag `v0.1.0-build-gate` (M2) |
| 3 | M2, plus the Vault and Health PRDs accepted | Both E2E tests green in one CI run; tag `v0.2.0-two-slices` (M3) |
| 4 | M3; the threat model before the deployment | Demo URL, dashboard, write-up, video, retrospective (M4, M5) |

A phase never starts with its entry condition unmet, because the order is the plan. Phase 1 document work may overlap Phase 0; nothing else overlaps across a gate.

---

## 3. Sequence within the phases

The order of the larger steps, with the checkpoint that tells you each one is really done. Work packages and their dependencies are in `docs/Execution_Plan.md`.

| Step | Focus | Key outputs | Checkpoint |
|---|---|---|---|
| 1 | Tooling; agent onboarding; review round 2 starts | Tools installed; labels, milestones, branch protection; uv scaffolding, pre-commit, import-linter, CI; Phase 0–1 issues created; agents' first STATUS lines | **M0:** first agent-authored PR merged with CI green |
| 2 | Spec close-out; infrastructure drafts | DM v1.3 and MR frozen; Simulator spec; Test strategy; Dev-environment doc; Docker Compose, `.env.example` and the V001 migration drafted by Gemini | **M1:** specs frozen, Build Gate pre-conditions all ticked |
| 3 | Kernel skeleton, resource lock, sessions | FastAPI app, settings, pools, SDK envelope; V001 merged with schema-diff test; `resource_lock` with concurrency test; `supervisor_sessions` lifecycle with boot reconciliation | Integration suite (Testcontainers) green on `main` |
| 4 | Audit chain, Healer, registry | Audit write protocol + Q12 verifier; Healer with lock, caps, breaker, P1/P2 algorithms; registry boot and dispatch checks | Verifier passes over a seeded chain; `healer run-once` processes a queued AUDIT_LOG_WRITE |
| 5 | DPI gateway, FinanceAgent, crash scenarios | BBPS/AA gateway with Lua budgets, IST TTLs, breakers; FinanceAgent `PAY_BILL` with five gates; crash A–D tests; LLM gateway stub | Crash scenarios A–D green in CI |
| 6 | PWA approval + WebAuthn, Playwright E2E | Approval screen with passkeys; "Priya pays BESCOM bill" E2E; gate sign-off; tag `v0.1.0-build-gate` | **M2:** Build Gate PASSED |
| 7 | Vault foundation; DigiLocker and ABHA stubs | `secure_vault` module, document metadata, DigiLocker sync, `SHOW_DOCUMENT`; stubs and contract tests | Vault intent runs through registry and audit unchanged |
| 8 | Health module | ABHA prescription → medications → reminder schedule; FHIR partial parse; proxy nudge logic | Health integration tests green |
| 9 | Notifications, admin screens, age-18 trigger | Notification engine + push stand-in; family graph admin screens; Scenario 5 job | Admin can activate a module and assign a proxy end to end |
| 10 | Second E2E | "Nani's medication reminder via proxies" Playwright test | **M3:** two slices, one kernel |
| 11 | Voice stand-in, observability | Web Speech stand-in with confidence gate; JSON logs, Prometheus metrics, Grafana dashboard; k6 P95 run | Dashboard shows both flows and Healer activity |
| 12 | Threat model, demo deployment | `Security_Threat_Model.md`; host in an India region, TLS, simulators bundled, synthetic data only | **M4:** demo URL live |
| 13 | Portfolio release; retrospective | Build log, architecture one-pager, README landing, demo video, retrospective | **M5:** portfolio release |

### 3.1 Working rhythm (no calendar)

The protocol is `coordination/README.md`. It is event-driven, not scheduled:

- **Whenever the founder sits down:** read `coordination/inbox/founder/`, merge approved PRs, triage `needs-triage`, unblock `blocked`.
- **At the start of every agent session:** read your inbox and `coordination/STATUS.md`; at the end, update your STATUS section and send any handoff messages.
- **At each checkpoint in the table above:** one line in the tracker's change log; at each milestone, a retrospective note in `coordination/BOARD.md`.
- **When work resumes after a pause:** Claude Code runs a tracker health check first (status matrix, register, Decision Log, open PRs) so the plan reflects reality before anyone builds on it.

### 3.2 Decision points (tied to milestones, not dates)

| When | Decision | Default if undecided |
|---|---|---|
| At M1 | Does MR freeze at v1.1 or bump to v1.2 (did round 2 change content)? | Bump to v1.2 with a governance row |
| Before M2 sign-off | Are crash scenarios A–D green? Are passkeys working on real devices? | No Phase 3 work starts until A–D are green; the gate may pass with Playwright's virtual authenticator, with real-device passkeys moved to Phase 3 |
| At M3 | Which flow leads the video, bill pay or medication? | Bill pay with crash-and-recover |
| Before M4 | Demo host provider and video visibility | Founder's choice among India-region hosts; unlisted video |
| At M5 | Commercial restart, third slice, native shell, or stop and maintain (§4.1) | Stop and maintain |

---

## 4. Milestones

| Milestone | Reached when | You can show someone… |
|---|---|---|
| **M0 — Agents online** | First agent-authored PR merged with CI green | a PR written by one agent, reviewed by another, merged by you, and the labels, inbox messages and branches that made it happen. |
| **M1 — Specs frozen** | DM v1.3 and MR frozen; Build Gate pre-conditions ticked | a frozen spec set with a visible review trail (two rounds, two model families, governance rows) and a simulator spec that says exactly what is real and what is not. |
| **M2 — Build Gate passed** | Crash A–D and the bill-pay E2E green on `main` | four crash scenarios passing in CI and a Playwright run of "Priya pays BESCOM bill" against simulators, with the audit chain verified at the end. |
| **M3 — Two slices, one kernel** | Both E2E tests green in one CI run | Nani's medication reminder reaching Priya and Ravi through the proxy rules, in the same PWA, with the Kitchen Tablet refusing to show it. |
| **M4 — Demo live** | Demo URL reachable, threat model reviewed | a URL in an India region, a Grafana dashboard, and a threat model written before the URL existed. |
| **M5 — Portfolio release** | Write-up and video published, retrospective done | a build log, a short video and a README that a hiring manager can read in ten minutes. |

### 4.1 Beyond M5 (sketch, not a plan)

Decided at the M5 retrospective, one of: (a) **commercial restart** per §7; (b) **a third slice** (Home Operations against an ONDC simulator, or the staff payroll P2P path) to test the kernel a third time; (c) **native shell** for real biometrics and push, if the PWA stand-ins are the weakest part of the demo; (d) **stop and maintain**, leaving the repository as a finished portfolio piece. Anything in `Vision_Parking_Lot.md` stays parked.

---

## 5. Constraints and what is most likely to stall

**The binding constraint is review and merge, not generation.** Three agents can produce PRs faster than one person can responsibly merge them. Anything that raises PR count without raising value (tiny PRs, drive-by refactors) is a cost to the founder. Agents therefore keep PRs to one work package each and never open follow-ups on their own initiative beyond a `needs-triage` issue.

**What each agent is for.**

| Agent | What it is for | What it must not be used for |
|---|---|---|
| Claude Code | Architecture, spec fixes, reviews against invariants, roadmap and tracker, threat model, write-up | Bulk boilerplate; anything a script can verify better |
| Codex | Implementation of build targets against frozen specs; second reviewer for Claude-authored docs | Reopening spec decisions; editing frozen specs |
| Gemini (Antigravity) | WireMock stubs from spec tables, Alembic migration from DDL, fixtures, FHIR samples, cross-reference sweeps, PR summaries, lint and docstring passes, tracker sync; may delegate mechanical subtasks to local models it orchestrates | Anything on the payment, consent or audit paths; design decisions |

**Most likely to stall, and what to do about it.**

1. **WebAuthn passkeys in a PWA.** Platform quirks, HTTPS requirements, device differences, and the founder's own devices are the test lab. Mitigation: server-side verification with a maintained library; Playwright's virtual authenticator for CI so the E2E test never depends on hardware; a dev-only PIN approval behind a flag that is off in the demo build.
2. **Healer concurrency and crash-scenario tests.** Crash points must be injected deterministically and the 5-minute cadence must be controllable. Mitigation: a `CRASH_AFTER=<point>` hook in the two-phase commit path that only exists in test builds; the Healer implemented as a callable `run_once()` with an injectable clock; Testcontainers Postgres and Redis per test module; the four scenarios written first as failing tests before the Healer is built.
3. **LLM intent parsing quality.** A hosted model can parse "BESCOM ka bill bhar do" well and still be non-deterministic; a small local model may not parse it at all. Mitigation: tests run on the deterministic stub; a golden set of ~50 utterances (English, Hindi, Hinglish) with expected intents and a routing-accuracy report; JSON-schema-constrained output with the FSM §1.1 confidence thresholds; the demo uses fixed utterances from the golden set.
4. **Docker on Windows.** WSL 2 file-system performance and Testcontainers quirks. Mitigation: CI on Linux runners is the source of truth; the founder runs Compose, not the full suite, locally.
5. **A long pause.** The most likely failure mode, given the project's history. Mitigation: the repository carries all state (tracker, STATUS, inbox, Decision Log), so any agent can resume from a cold start; the resume step in §3.1 is mandatory.

---

## 6. Regulatory track: parked

Portfolio mode means no FIU, BBPOU or HIU application, no sandbox credentials, no real-money or real-health-data integration, and no DPDP compliance programme beyond what the specs already build in (consent-first, data minimisation, India hosting for the demo). Everything DPI-facing runs against WireMock simulators whose request and response shapes are dated February 2026 (AGENTS.md §6: do not invent DPI facts).

**What would restart it:** any decision to onboard a real family with real money or real health data; a partner willing to provide licensed AA/BBPS access under their registration; or funding that covers the legal and compliance cost Master Context §8 estimates. On restart the order is: `Security_Threat_Model.md` becomes P0 and is completed → sandbox access for each DPI → licence or partner route (MC §8 "Parallel Track") → DR and scalability implementation against NFR v2.2 §6–§7 → real integration behind the same gateway interface the simulators implement.

---

## 7. What changes if this goes commercial

- **Licences:** FIU (RBI/Sahamati), BBPOU (NPCI) and HIU (ABDM) registrations in parallel with development (MC §8). Until then the simulators remain the only DPI.
- **Hosting:** managed services in India regions only (MC §7.4, §10.1), the DR plan of NFR v2.2 §7 implemented, an on-call arrangement that does not need a 24/7 engineer (FTS §1.3 principle 5).
- **Security:** `Security_Threat_Model.md` moves from P1 to P0; external penetration test; audit-log typed payloads enforced before the first real user (tracker parking lot, escalated item).
- **Plan of record:** Master Context §8 (phasing) and §14 (GTM) become the plan again, re-baselined from the M5 state; this roadmap and `GTM_Plan.md` are archived as the portfolio phase. A dated plan becomes appropriate at that point, and only then.
- **Product:** native shell for biometrics and push (PWA stand-ins retire); Bhashini replaces the browser speech stand-in; ONDC and the remaining pillars enter per MC §5.1.
- **Team:** the agent roster stays, but a second human reviewer for payment, consent and audit code is the first hire, not the first engineer.

---

## 8. Metrics for the portfolio build

Adapted from Master Context §9 and PRD Core §7 for a build with no users. Every metric is measured from the repository or the demo deployment, never from surveys.

| Metric | Definition | Source | Target at M2 | Target at M5 |
|---|---|---|---|---|
| Autonomy score (demo flows) | Steps in each E2E flow completed without human input, excluding the mandated approval gate (MC §9.1 adapted) | Playwright step log | Bill pay: all steps except G4 approval | Both flows: all steps except approval and the proxy "Done" |
| Crash-scenario pass rate | Scenarios A–D passing per CI run on `main` (FTS §4.5) | CI | 4/4, every run | 4/4, every run, plus Health-side lock/notification scenarios |
| Simulator contract-test coverage | Simulator endpoints used by the slices that have a contract test (RB §9.5) | `tests/dpi_contracts` report | 100 % of BBPS and AA endpoints used | 100 % of BBPS, AA, ABHA, DigiLocker endpoints used |
| Slice P95 latency | Intent submission → approval prompt, and approval → confirmation, excluding human wait (NFR §1: < 2.0 s end to end) | k6 against the demo deployment | Measured once locally | P95 < 2.0 s for each half against simulators |
| Routing accuracy | Golden utterances routed to the correct intent (PRD §7 target > 95 %) | Golden-set report in CI | > 95 % on the stub | > 95 % on the hosted model, reported per language |
| Test coverage | Line coverage on `familylifeos/kernel` and `modules/*` (tracker target 80 %) | `coverage.py` in CI | ≥ 80 % kernel | ≥ 80 % kernel and modules |
| Agent PRs merged | PRs merged to `main` with an agent author label | GitHub | Reported per agent | Reported per agent and per phase |
| Review-rejection rate | PRs sent back for a second round by the reviewing agent, as a share of PRs reviewed | GitHub labels/comments | Measured | < 30 %, reported per author agent |
| Resilience score | Simulator failure modes (429, 500, timeout, malformed FHIR) handled without a 5xx from the app (PRD §7 target 100 %) | Chaos-mode test run | 100 % for BBPS/AA modes | 100 % for all four simulators |

**Reporting.** Crash-scenario pass rate, coverage, routing accuracy and contract-test coverage come out of CI on every run. PR counts and rejection rate are pulled from GitHub at each milestone by a small script (`tools/agent_stats.py`) and written into the tracker change log. Latency and resilience are measured at M4 against the demo host and again at M5 before the write-up freezes the numbers.

---

## 9. Assumptions the founder should confirm

1. Passkeys (WebAuthn) as the biometric stand-in, with a dev-only PIN fallback that is disabled in the demo build.
2. Demo hosting in an India region on a single VM or container host; the founder holds the cloud account.
3. The bill-pay E2E test uses typed text as the "voice intent" step; the browser speech stand-in arrives in Phase 4.
4. `Security_Threat_Model.md` precedes the demo deployment and is P1 until then.
5. Hosted LLM default is Claude Haiku (decided 2026-09-17); `stub` for tests, a local Ollama model for development.
