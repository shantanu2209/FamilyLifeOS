# Roadmap: FamilyLifeOS Portfolio Build (2026-09-18 to 2026-12-20)

> **Status:** DRAFT v0.1 — proposed, founder to confirm dates · **Author:** Alfred (Lead Product Architect), drafted with Claude Code · **Last content change:** 2026-09-17
> **Scope:** The 13-week plan from tooling install to a demoable, documented kernel with two vertical slices ("Priya pays the BESCOM electricity bill" and "Nani's medication reminder via proxies") running against DPI simulators, in portfolio mode (tracker → Decision Log, 2026-09-17). Phases, weekly calendar, milestones, effort model, metrics, and the short "what changes if this goes commercial" section. Work packages live in `docs/Execution_Plan.md`; audience and artefacts in `docs/strategy/GTM_Plan.md`.
> **Supersedes:** For planning purposes only: tracker → "Milestone Tracker" (Feb-2026 week numbers, never re-baselined), tracker → "Technology Decisions (Weeks 3-5)", "Team/Hiring Decisions", "Feature Prioritization" and "Operational Decisions", and the tracker's "Test Automation Roadmap" weeks. Master Context §8 (phasing with budgets and licences) stays the reference for commercial mode and is not the current plan.

## 0. Document Governance

| Version | Date | Description of Change | Author |
|---|---|---|---|
| v0.1 | 2026-09-17 | First draft: five phases over 13 weeks, week-by-week calendar, milestones M0–M5, effort model, parked regulatory track, commercial-mode delta, portfolio metrics. Dates proposed for founder confirmation. | Alfred (with Claude Code) |

---

## 1. Planning basis

- **Mode:** portfolio first (tracker → Decision Log). The output is a working kernel plus two slices against WireMock simulators, built to the quality the frozen specs demand. No licences, no real-money DPI integration, no hosting beyond one demo deployment. Commercial expansion is possible later; §8 lists what would change.
- **Team:** one solo founder (evenings and weekends, 10–15 focused hours a week) and four AI agents: Claude Code (architecture, specs, reviews, roadmap), Codex cloud (implementation against frozen specs, second reviewer), Gemini Flash in Antigravity (routine generation from spec tables), a local Ollama model via Codex CLI (mechanical tasks with a verifying script). Coordination is through GitHub issues, labels, branches and PRs under the protocol in `coordination/README.md`; every PR is reviewed by an agent other than its author; the founder merges.
- **Starting state (2026-09-17):** documentation only. Data Model v1.3, Module Registry v1.1, FTS v1.2, CM v1.2, RB v1.2, PRD Core v2.2, NFR v2.2 and Master Context v2.1 are being finalised today; the Finance module PRD is in draft (v0.1) and the Vault and Health PRDs follow; `Security_Threat_Model.md` is P1 and due before any internet-facing deployment. Docker Desktop, Codex CLI, Ollama models and Antigravity are installed on 2026-09-18. Nothing can be built before that.
- **Dates are targets, not commitments.** A solo founder with a day job will lose weeks to life. The plan therefore carries explicit buffer (Week 6, Week 10, Week 13) and fixes the order of work so that a slip moves the calendar, not the sequence. With that said once, the rest of this document commits to concrete dates.
- **Calendar:** Week 1 is a long week (Fri 2026-09-18 to Sun 2026-09-27) so that the install weekend counts; Weeks 2–13 run Monday to Sunday and end on Sun 2026-12-20. Known low-capacity days: Gandhi Jayanti (Fri 2026-10-02), Dussehra (Tue 2026-10-20, confirm), Diwali (Sun 2026-11-08 and the two days after it, confirm). Weeks 7–8 are planned at reduced founder hours.

### 1.1 Scope boundaries for the 13 weeks

**In scope:** the kernel (registry, envelope, sessions, locks, audit chain, Healer, DPI gateway, LLM gateway, notification engine); the Finance module limited to `PAY_BILL` and `CHECK_BALANCE`; the Secure Vault foundation (metadata, DigiLocker simulator, `SHOW_DOCUMENT`); the Health module limited to prescriptions, medications and proxy reminders; a PWA with passkey approval, admin screens and an inbox; four WireMock simulators with contract tests and chaos mode; the crash-scenario suite; observability; one demo deployment; the threat model; the portfolio artefacts.

**Out of scope, by decision, not by omission:** ONDC and Bhashini simulators (the Bhashini stub in RB §9.3 stays parked; ONDC has none yet); WhatsApp and SMS channels; native iOS/Android shells; RabbitMQ, Kafka and Kubernetes (AGENTS.md §5, MR §2.3); disaster recovery and scalability implementation (NFR v2.2 §6–§7 state the targets; nothing is built for them); penetration testing; audit-log archival and partitioning (tracker parking lot); `PAY_RECURRING` and any Level 2 automation; the third-party module marketplace and everything in `Vision_Parking_Lot.md`; real DPI sandboxes and licence applications (§7). Each item has a named trigger in the document that parks it.

---

## 2. Phases

### Phase 0 — Tooling and agent onboarding (Week 1: 2026-09-18 → 2026-09-27)

- **Goal:** every agent can take an issue, work on a branch, open a PR and be reviewed by another agent, with CI green on `main`.
- **Deliverables:** Docker Desktop (WSL 2), Codex CLI, Ollama models (`qwen3.5:9b`, optionally `qwen3.6:35b`) and Antigravity installed; local-agent smoke tests passed and tokens/s recorded in the tracker's Decision Log (Local_Agent_Setup §6); GitHub labels, milestones and branch protection on `main` (the issue and PR templates already exist under `.github/`); repository scaffolding (uv, Python 3.12, `ruff`, pre-commit, import-linter contract per MR §7.1) and a CI workflow running `ruff`, import-linter and `pytest` on every PR; issues created for the Phase 0 and Phase 1 work packages; AGENTS.md §6 updated with the agent roster and review matrix.
- **Definition of done:** one PR authored by the local agent, reviewed by Claude Code or Codex, merged by the founder, with CI green.
- **Exit criteria:** WP-01 to WP-07 closed (Execution Plan); `uv run pytest` and `uv run lint-imports` pass on `main`; `tools/agent-local.ps1 -Issue <n>` produces a reviewable PR.
- **Main risks:** Windows/WSL 2 friction with Docker Desktop and Testcontainers (mitigation: CI on Linux runners is the source of truth; local runs are a convenience); the 9B local model failing Codex's tool protocol (mitigation: `local-heavy`, then Aider per Local_Agent_Setup §8).
- **Agents:** founder installs and configures; Claude Code drafts templates, CI and the issue set; Codex builds the scaffolding; local agent runs the smoke tests and the first mechanical PR.

### Phase 1 — Spec close-out (Weeks 1–2: 2026-09-18 → 2026-10-04)

- **Goal:** freeze the two specs the build depends on and write the three documents implementation needs (simulator architecture, test strategy, dev environment). Resolve inconsistency register items 1–3 for good.
- **Deliverables:** Codex review round 2 of Module Registry and Data Model v1.3; fixes applied with version bumps and governance rows; both frozen; `Tech_Spec_Simulator_Architecture.md` (WireMock stubs for AA, BBPS, ABHA, DigiLocker; scenario headers in the RB §9 `X-Simulate-*` style; BBPS PENDING→SUCCESS state machine; chaos mode per RB §9.4; contract tests per RB §9.5) with stub JSON generated by Gemini; `Test_Automation_Strategy.md` formalised from the tracker section for the chosen stack; `Development_Environment_Setup.md`; Finance module PRD accepted (Vault and Health PRDs accepted before Phase 3).
- **Definition of done:** the tracker's Build Gate pre-conditions are all ticked; AGENTS.md §3, §7 and the README status table say FROZEN for DM v1.3 and MR; no open register item blocks implementation.
- **Exit criteria:** WP-09 to WP-16 closed; a Gemini cross-reference sweep finds no dangling section references across the v1.x/v2.x document set.
- **Main risks:** review round 2 reopening settled decisions (mitigation: reviewers are told the Decision Log is closed; findings are filed as issues, not fixed in place); scope creep in the simulator spec (mitigation: only the four DPIs the two slices need; ONDC and Bhashini stubs are parked).
- **Agents:** Codex reviews; Claude Code applies fixes and authors the three documents; Gemini generates stub JSON and runs the cross-reference sweep; local agent syncs the tracker matrix.

### Phase 2 — Build Gate and kernel slice (Weeks 2–6: 2026-09-28 → 2026-11-01)

- **Goal:** pass the tracker's Phase 1 Build Gate exactly as written, in its order.
- **Deliverables (in build order, mirroring tracker → Phase 1 Build Gate):** Docker Compose with PostgreSQL (all core tables from DM v1.3), Redis, WireMock BBPS (SUCCESS, FAILED, PENDING, NOT_FOUND, 429, timeout) and WireMock AA (balance fetch, consent validation), `.env.example`; Alembic `V001__initial_schema` from the DM v1.3 DDL; kernel skeleton and SDK envelope (MR §6); `resource_lock` acquire/release (DM v1.3 §3.11, FTS §9); `supervisor_sessions` lifecycle (FSM §1, DM v1.3 §3.7); audit log write with hash chain through `fn_lock_audit_tail` / `fn_append_audit` (DM v1.3 §3.18, FTS §11.3); Healer cron with distributed lock, priority queue, per-run cap and system circuit breaker (FTS §6); Module Registry boot and dispatch-time checks (MR §7.3, §8.1); DPI gateway for BBPS and AA with budgets and breakers (RB §2, §4, §8); FinanceAgent `PAY_BILL` with the five gates and Phase 2 commit (FTS §2, MR §10); crash scenarios A–D as automated tests (FTS §4.5); LLM gateway with a deterministic stub; minimal PWA approval screen with WebAuthn passkeys standing in for biometric approval; the single Playwright test "Priya pays BESCOM bill".
- **Definition of done:** the four crash scenarios and the Playwright test pass in CI on `main`; the gate checklist in the tracker is fully ticked; `main` is tagged `v0.1.0-build-gate`.
- **Exit criteria:** gate status in the tracker changed from BLOCKED to PASSED with the CI run linked; invariants in AGENTS.md §4 items 15–24 each have at least one unit test named after them.
- **Main risks:** see §6 (WebAuthn in a PWA, Healer concurrency tests, LLM parsing quality); Alembic migration drifting from the DM v1.3 DDL (mitigation: a schema-diff test that fails CI on any difference).
- **Agents:** Codex implements every build target; Claude Code reviews each PR against the cited spec section; Gemini drafts Docker Compose, the Alembic migration, WireMock stubs and fixtures, with Codex reviewing; local agent handles lint, docstrings and tracker sync. Week 6 is buffer; if the gate passes in Week 5, Phase 3 starts early.

### Phase 3 — Vault foundation, Health second slice, PWA (Weeks 7–10: 2026-11-02 → 2026-11-29)

- **Goal:** prove the kernel is a kernel: a second module family (Health) and the foundational Vault run through the same registry, envelope, consent and audit paths without touching them.
- **Deliverables:** Secure Vault module (document metadata only, DigiLocker simulator sync per CM §6.3, `SHOW_DOCUMENT` "show my licence" with the public-surface block); Health module (ABHA simulator prescription → FHIR partial-parse handling per RB §5.3 → medications → reminder schedule → proxy nudges per PRD Scenario 2); notification engine as a service module with a push stand-in; family graph admin screens in the PWA (members, roles, proxies, devices, module activation per MR §8.2); Scenario 5 age-18 trigger; the second Playwright test "Nani's medication reminder via proxies".
- **Definition of done:** both E2E tests pass in one CI run; Health and Vault import only the SDK (import-linter green); no change to kernel payment, consent or audit code was needed to add them (if one was, it is recorded as a kernel gap, not hidden).
- **Exit criteria:** M3 sign-off; tracker Document Status Matrix updated; Vault and Health PRDs marked accepted.
- **Main risks:** FHIR R4 parsing rabbit hole (mitigation: parse three resource types only — MedicationRequest, DiagnosticReport, Observation — per CM §6.2.2); admin screens absorbing founder hours (mitigation: table-driven screens, no design pass until Phase 4); Diwali week capacity.
- **Agents:** Codex builds; Claude Code reviews and writes the Health/Vault i18n key lists; Gemini generates DigiLocker and ABHA stubs and FHIR fixtures; local agent keeps docs and tracker in sync.

### Phase 4 — Voice stand-in, observability, threat model, demo deployment, write-up (Weeks 11–13: 2026-11-30 → 2026-12-20)

- **Goal:** make it showable and honest: a public demo URL with synthetic data, dashboards that prove the metrics in §9, a threat model before anything faces the internet, and the portfolio artefacts.
- **Deliverables:** voice stand-in (browser speech API with the confidence gate from RB §7.3, labelled "not Bhashini"); structured logs and Prometheus metrics named in RB §10.1 and MR §11 with a Grafana dashboard; k6 run producing the slice P95; `Security_Threat_Model.md` (tracker gap 8b checklist); demo deployment on a single VM or container host in an India region with TLS and no real data; portfolio write-up (build log), one-page architecture overview, README as landing page; 4–6 minute demo video; retrospective and tracker re-baseline.
- **Definition of done:** demo URL reachable over TLS; dashboard shows both flows; threat model reviewed by Codex; write-up and video published; the M5 retro records the commercial-or-not decision.
- **Exit criteria:** every metric in §9 has a measured value at M5.
- **Main risks:** deployment work eating the write-up time (mitigation: deploy is a Codex task with a checklist; the founder only holds the cloud account); the threat model turning into a P0 rewrite (mitigation: it documents mitigations and gaps; gaps become issues, not blockers, unless they affect the demo deployment itself).
- **Agents:** Claude Code authors the threat model, write-up and video script; Codex builds the voice stand-in, observability and deployment; Gemini writes PR summaries and the architecture diagram text; the founder records the video and owns the cloud account. Week 13 is buffer.

### Gating summary

| Phase | Cannot start until | Is done when | Buffer |
|---|---|---|---|
| 0 | The founder's install day (2026-09-18) | First agent PR merged with CI green (M0) | None; a slip here pushes everything |
| 1 | Codex is logged in and can read the repository (WP-01) | DM v1.3 and MR frozen; Build Gate pre-conditions ticked (M1) | Absorbed by Phase 2's Week 6 |
| 2 | M1, plus Compose running locally | Crash A–D and the Playwright test green on `main`; tag `v0.1.0-build-gate` (M2) | Week 6 |
| 3 | M2, plus the Vault and Health PRDs accepted | Both E2E tests green in one CI run; tag `v0.2.0-two-slices` (M3) | Week 10 |
| 4 | M3; the threat model before the deployment | Demo URL, dashboard, write-up, video, retrospective (M4, M5) | Week 13 |

A phase may start early when its entry condition is met early; it never starts on schedule with its entry condition unmet, because the order is the plan.

---

## 3. Week-by-week calendar

| Week | Dates (2026) | Focus | Key outputs | Gate / checkpoint |
|---|---|---|---|---|
| 1 | Fri 18 Sep – Sun 27 Sep (10 days) | Phase 0 tooling; Phase 1 review round 2 starts | Docker/Codex/Ollama/Antigravity installed; local smoke tests recorded; labels, milestones, templates, branch protection; uv scaffolding, pre-commit, import-linter, CI; Phase 0–1 issues created; Codex R2 on MR and DM under way | **M0 (27 Sep):** first agent-authored PR merged with CI green |
| 2 | 28 Sep – 4 Oct | Phase 1 close-out; Phase 2 infrastructure starts | DM v1.3 and MR frozen; Simulator spec; Test strategy; Dev-environment doc; Docker Compose, `.env.example` and the V001 migration drafted by Gemini | **M1 (4 Oct):** specs frozen, Build Gate pre-conditions all ticked |
| 3 | 5 – 11 Oct | Kernel skeleton, resource lock, sessions | FastAPI app, settings, pools, SDK envelope; V001 merged with schema-diff test; `resource_lock` with concurrency test; `supervisor_sessions` lifecycle with boot reconciliation | Checkpoint: integration suite (Testcontainers) green on `main` |
| 4 | 12 – 18 Oct | Audit chain, Healer, registry | `fn_append_audit` + tail lock + Q12 verifier; Healer with lock, caps, breaker, P1/P2 algorithms; registry boot and dispatch checks | Checkpoint: verifier passes over a seeded chain; `healer run-once` processes a queued AUDIT_LOG_WRITE |
| 5 | 19 – 25 Oct (Dussehra Tue 20) | DPI gateway, FinanceAgent, crash scenarios | BBPS/AA gateway with Lua budgets, IST TTLs, breakers; FinanceAgent `PAY_BILL` with five gates; crash A–D tests; LLM gateway stub | Target: crash scenarios A–D green in CI |
| 6 | 26 Oct – 1 Nov | PWA approval + WebAuthn, Playwright E2E, **buffer** | Approval screen with passkeys; "Priya pays BESCOM bill" E2E; gate sign-off; tag `v0.1.0-build-gate` | **M2 (1 Nov):** Build Gate PASSED |
| 7 | 2 – 8 Nov (Diwali Sun 8; reduced hours) | Vault foundation; DigiLocker and ABHA stubs | `secure_vault` module, document metadata, DigiLocker sync, `SHOW_DOCUMENT`; stubs and contract tests | Checkpoint: Vault intent runs through registry and audit unchanged |
| 8 | 9 – 15 Nov (post-Diwali; reduced hours) | Health module | ABHA prescription → medications → reminder schedule; FHIR partial parse; proxy nudge logic | Checkpoint: Health integration tests green |
| 9 | 16 – 22 Nov | Notifications, admin screens, age-18 trigger | Notification engine + push stand-in; family graph admin screens; Scenario 5 job | Checkpoint: admin can activate a module and assign a proxy end to end |
| 10 | 23 – 29 Nov | Second E2E; **buffer** | "Nani's medication reminder via proxies" Playwright test; M3 sign-off | **M3 (29 Nov):** two slices, one kernel |
| 11 | 30 Nov – 6 Dec | Voice stand-in, observability | Web Speech stand-in with confidence gate; JSON logs, Prometheus metrics, Grafana dashboard; k6 P95 run | Checkpoint: dashboard shows both flows and Healer activity |
| 12 | 7 – 13 Dec | Threat model, demo deployment | `Security_Threat_Model.md`; VM in an India region, TLS, simulators bundled, synthetic data only | **M4 (13 Dec):** demo URL live |
| 13 | 14 – 20 Dec | Portfolio release; **buffer**; retro | Build log, architecture one-pager, README landing, demo video, retrospective, tracker re-baseline | **M5 (20 Dec):** portfolio release |

### 3.1 Weekly operating rhythm

The protocol is `coordination/README.md` §7; this is how it maps onto a founder with a day job.

- **Daily (10 min, founder):** merge approved PRs, triage `needs-triage`, unblock `blocked` (README §7). On weekdays this is the whole founder involvement.
- **Monday (30 min, Claude Code with the founder):** tracker health check, propose the week's issues from the Execution Plan, open the week's WP-08 local-agent issue, sync `coordination/BOARD.md`.
- **Tuesday to Thursday (agents; founder evenings):** Codex and Gemini work their issues; Claude Code reviews as PRs arrive and takes at most one authoring task; the founder reads and merges in one or two sittings rather than on every notification.
- **Saturday (founder's long block, 3–5 h):** the things only the founder can do that week (installs, device passkeys, the cloud account, recording), then the merge backlog.
- **Sunday (30 min, founder):** checkpoint against that week's row above; if it is missed, one line in the tracker says what slipped and whether the buffer week absorbs it. At each milestone a retrospective note goes to `coordination/BOARD.md` → Retrospectives. No re-planning mid-week.

### 3.2 Dated decision points

| Date | Decision | Default if undecided |
|---|---|---|
| Sun 2026-09-27 | Is the local model viable in Codex CLI, or switch to `local-heavy` / Aider (Local_Agent_Setup §6, §8)? | Keep `qwen3.5:9b`, restrict it to docs-only tasks |
| Sun 2026-10-04 | Does MR freeze at v1.1 or bump to v1.2 (did round 2 change content)? | Bump to v1.2 with a governance row |
| Sun 2026-10-25 | Gate go/no-go for Week 6: are crash scenarios A–D green? | Use Week 6 as the buffer it is; no Phase 3 work starts |
| Wed 2026-10-28 | Passkeys working on real devices? | Pass the gate with the virtual authenticator; real devices move to Week 9 |
| Sun 2026-11-29 | Which flow leads the video, bill pay or medication? | Bill pay with crash-and-recover |
| Sun 2026-12-06 | Demo host provider and video visibility | DigitalOcean BLR1; unlisted video |
| Sun 2026-12-20 | Commercial restart, third slice, native shell, or stop and maintain (§5) | Stop and maintain; revisit in Q1 2027 |

---

## 4. Milestones

| Milestone | Target date | You can show someone… |
|---|---|---|
| **M0 — Agents online** | Sun 2026-09-27 | a PR written by a local 9B model, reviewed by Claude Code, merged by you, CI green, and the labels and branches that made it happen. |
| **M1 — Specs frozen** | Sun 2026-10-04 | a frozen spec set with a visible review trail (two rounds, governance rows) and a simulator spec that says exactly what is real and what is not. |
| **M2 — Build Gate passed** | Sun 2026-11-01 | four crash scenarios passing in CI and a Playwright run of "Priya pays BESCOM bill" against simulators, with the audit chain verified at the end. |
| **M3 — Two slices, one kernel** | Sun 2026-11-29 | Nani's medication reminder reaching Priya and Ravi through the proxy rules, in the same PWA, with the Kitchen Tablet refusing to show it. |
| **M4 — Demo live** | Sun 2026-12-13 | a URL in an India region, a Grafana dashboard, and a threat model written before the URL existed. |
| **M5 — Portfolio release** | Sun 2026-12-20 | a build log, a 4–6 minute video and a README that a hiring manager can read in ten minutes. |

---

## 5. Beyond the horizon (sketch, not a plan)

Decided at the M5 retrospective, one of: (a) **commercial restart** per §8; (b) **a third slice** (Home Operations against an ONDC simulator, or the staff payroll P2P path) to test the kernel a third time; (c) **native shell** for real biometrics and push, if the PWA stand-ins are the weakest part of the demo; (d) **stop and maintain**, leaving the repository as a finished portfolio piece. Anything in `Vision_Parking_Lot.md` stays parked; its trigger conditions (100k users, hardware partners) are not in sight.

---

## 6. Effort model

**Founder hours.** 10–15 focused hours a week, 13 weeks, so 130–195 hours in total; Week 1 has 10 days (~18 h); Weeks 7–8 are planned at 6–8 h. Where the hours go, by design: ~40 % reading and merging PRs, ~25 % decisions and spec work with Claude Code, ~20 % things agents cannot do on this machine (installs, Docker on WSL 2, passkeys on real devices, the cloud account, recording), ~15 % write-up and video.

**The binding constraint is review, not generation.** Budget 20 minutes of founder time per PR for the merge decision after the agent review. At 3–4 review hours a week that caps sustainable throughput at about 10 merged PRs a week; the plan assumes 8 in Phase 2 and 6 elsewhere. Anything that raises PR count without raising value (tiny PRs, drive-by refactors) is a cost to the founder, not a gift.

**Agent capacity assumptions.**

| Agent | Assumed capacity | What it is for | What it must not be used for |
|---|---|---|---|
| Claude Code | 3–5 sessions/week, each one spec section, review or scaffold | Architecture, spec fixes, reviews against invariants, roadmap and tracker, threat model, write-up | Bulk boilerplate; anything a script can verify better |
| Codex cloud | 6–10 tasks/week, one PR each, ≤ 1 day of agent time per task | Implementation of build targets against frozen specs; second reviewer for Claude-authored docs | Reopening spec decisions; editing frozen specs |
| Gemini Flash (Antigravity) | Effectively unbounded generation, but every output needs a verifying test | WireMock stubs from spec tables, Alembic migration from DDL, fixtures, FHIR samples, cross-reference sweeps, PR summaries | Anything on the payment, consent or audit paths |
| Local Ollama (`qwen3.5:9b` via Codex CLI) | ~5 issues/week at 25–40 tokens/s, each with a script or test that verifies it | Lint, docstrings, tracker status sync, commit messages, template boilerplate | Frozen specs, AGENTS.md, payment/consent/audit code, merging |

**Most likely to slip, and what to do about it.**

1. **WebAuthn passkeys in a PWA (Week 6).** Platform quirks, HTTPS requirements, device differences, and the founder's own devices are the test lab. Mitigation: server-side verification with a maintained library; Playwright's virtual authenticator for CI so the E2E test never depends on hardware; a dev-only PIN approval behind a flag that is off in the demo build; if passkeys are not working by Wed 28 Oct, the gate passes with the virtual authenticator and real-device passkeys move to Week 9.
2. **Healer concurrency and crash-scenario tests (Weeks 4–5).** Crash points must be injected deterministically and the 5-minute cadence must be controllable. Mitigation: a `CRASH_AFTER=<point>` hook in the two-phase commit path that only exists in test builds; the Healer implemented as a callable `run_once()` with an injectable clock; Testcontainers Postgres and Redis per test module; the four scenarios written first as failing tests before the Healer is built.
3. **LLM intent parsing quality (Weeks 5, 11).** A hosted model can parse "BESCOM ka bill bhar do" well and still be non-deterministic; a local 9B model may not parse it at all. Mitigation: tests run on the deterministic stub; a golden set of ~50 utterances (English, Hindi, Hinglish) with expected intents and a routing-accuracy report; JSON-schema-constrained output with the FSM §1.1 confidence thresholds; the demo uses fixed utterances from the golden set.
4. **Docker on Windows.** WSL 2 file-system performance and Testcontainers quirks can burn an evening. Mitigation: CI on Linux runners is the source of truth; the founder runs Compose, not the full suite, locally.

---

## 7. Regulatory track: parked

Portfolio mode means no FIU, BBPOU or HIU application, no sandbox credentials, no real-money or real-health-data integration, and no DPDP compliance programme beyond what the specs already build in (consent-first, data minimisation, India hosting for the demo). Everything DPI-facing runs against WireMock simulators whose request and response shapes are dated February 2026 (AGENTS.md §6: do not invent DPI facts).

**What would restart it:** any decision to onboard a real family with real money or real health data; a partner willing to provide licensed AA/BBPS access under their registration; or funding that covers the legal and compliance cost Master Context §8 estimates. On restart the order is: `Security_Threat_Model.md` becomes P0 and is completed → sandbox access for each DPI → licence or partner route (6–12 months, MC §8 "Parallel Track") → DR and scalability implementation against NFR v2.2 §6–§7 → real integration behind the same gateway interface the simulators implement.

---

## 8. What changes if this goes commercial

- **Licences:** FIU (RBI/Sahamati), BBPOU (NPCI) and HIU (ABDM) registrations, 6–12 months in parallel with development (MC §8). Until then the simulators remain the only DPI.
- **Hosting:** managed services in India regions only (MC §7.4, §10.1), the DR plan of NFR v2.2 §7 implemented (RTO/RPO, backups, failover), backups, an on-call arrangement that does not need a 24/7 engineer (FTS §1.3 principle 5).
- **Security:** `Security_Threat_Model.md` moves from P1 to P0; external penetration test; audit-log typed payloads enforced before the first real user (tracker parking lot, escalated item).
- **Plan of record:** Master Context §8 (phasing) and §14 (GTM) become the plan again, re-baselined from the M5 state; PRD Core §8 timeline applies; this roadmap and `GTM_Plan.md` are archived as the portfolio phase.
- **Product:** native shell for biometrics and push (PWA stand-ins retire); Bhashini replaces the browser speech stand-in; ONDC and the remaining pillars enter per MC §5.1.
- **Team:** the four-agent roster stays, but a second human reviewer for payment, consent and audit code is the first hire, not the first engineer.

---

## 9. Metrics for the portfolio build

Adapted from Master Context §9 and PRD Core §7 for a build with no users. Every metric is measured from the repository or the demo deployment, never from surveys.

| Metric | Definition | Source | Target at M2 | Target at M5 |
|---|---|---|---|---|
| Autonomy score (demo flows) | Steps in each E2E flow completed without human input, excluding the mandated approval gate (MC §9.1 adapted) | Playwright step log | Bill pay: all steps except G4 approval | Both flows: all steps except approval and the proxy "Done" |
| Crash-scenario pass rate | Scenarios A–D passing per CI run on `main` (FTS §4.5) | CI | 4/4, every run | 4/4, every run, plus Health-side lock/notification scenarios |
| Simulator contract-test coverage | Simulator endpoints used by the slices that have a contract test (RB §9.5) | `tests/dpi_contracts` report | 100 % of BBPS and AA endpoints used | 100 % of BBPS, AA, ABHA, DigiLocker endpoints used |
| Slice P95 latency | Intent submission → approval prompt, and approval → confirmation, excluding human wait (NFR §1: < 2.0 s end to end) | k6 against the demo deployment | Measured once locally | P95 < 2.0 s for each half against simulators |
| Routing accuracy | Golden utterances routed to the correct intent (PRD §7 target > 95 %) | Golden-set report in CI | > 95 % on the stub | > 95 % on the hosted model, reported per language |
| Test coverage | Line coverage on `familylifeos/kernel` and `modules/*` (tracker target 80 %) | `coverage.py` in CI | ≥ 80 % kernel | ≥ 80 % kernel and modules |
| Agent PRs merged per week | PRs merged to `main` with an agent author label | GitHub | ≥ 8/week in Phase 2 | Reported per agent over the 13 weeks |
| Review-rejection rate | PRs sent back for a second round by the reviewing agent, as a share of PRs reviewed | GitHub labels/comments | Measured | < 30 %, reported per author agent |
| Resilience score | Simulator failure modes (429, 500, timeout, malformed FHIR) handled without a 5xx from the app (PRD §7 target 100 %) | Chaos-mode test run | 100 % for BBPS/AA modes | 100 % for all four simulators |

The numbers feed the write-up and the M5 retrospective; they are not vanity metrics because each one maps to a spec promise.

**Reporting cadence.** Crash-scenario pass rate, coverage, routing accuracy and contract-test coverage come out of CI on every run and are read off the badge or the run summary. PR counts and rejection rate are pulled from GitHub at each milestone by a small script (`tools/agent_stats.py`, part of WP-46) and written into the tracker change log. Latency and resilience are measured once at M4 against the demo host and once more at M5 before the write-up freezes the numbers.

---

## 10. Assumptions the founder should confirm

1. Week 1 starts Fri 2026-09-18 and the horizon ends Sun 2026-12-20; weeks run Monday–Sunday after Week 1.
2. Milestone dates M0–M5 as in §4, with Week 6, Week 10 and Week 13 as buffer.
3. Reduced capacity in Weeks 7–8 for Diwali (Sun 2026-11-08) and on Tue 2026-10-20 (Dussehra); confirm the dates and whether other travel or work peaks fall in the window.
4. 10–15 founder hours a week and about 10 merged PRs a week as the throughput ceiling.
5. Passkeys (WebAuthn) as the biometric stand-in, with a dev-only PIN fallback that is disabled in the demo build.
6. Demo hosting in an India region on a single VM or container host (candidate providers in the Execution Plan); the founder holds the cloud account.
7. The Phase 2 E2E test uses typed text as the "voice intent" step; the browser speech stand-in arrives in Phase 4.
8. `Security_Threat_Model.md` precedes the demo deployment (Week 12) and is P1 until then.
9. The LLM provider default: `stub` for tests, `ollama` for local development, `hosted` for the demo (`coordination/BOARD.md` lists this as an open founder decision).
