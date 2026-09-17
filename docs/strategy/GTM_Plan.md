# GTM Plan: Portfolio Mode

> **Status:** DRAFT v0.2 — no dates (founder ruling 2026-09-17); artefacts follow milestones · **Author:** Shantanu Chaudhary (Lead Product Architect), drafted with Claude Code · **Last content change:** 2026-09-17
> **Scope:** How the portfolio build reaches the people it is for: hiring managers and technical leaders evaluating the founder's product and AI-engineering skills, potential collaborators, and later potential co-founders or investors. Audience, positioning, artefacts and their cadence against the Roadmap milestones M2–M5, the demo script, what is deliberately not done, and the risks to the narrative. Applies to portfolio mode only (tracker → Decision Log, 2026-09-17).
> **Supersedes:** For the portfolio phase only: the tracker matrix row "Marketing_GTM_Strategy.md (P4, post-MVP)", which this document fulfils in portfolio form. Master Context §14 and PRD Core §8 (personas, acquisition channels, launch plan, pricing messaging) are not superseded; they remain the commercial-mode GTM and are referenced, not rewritten, in §6.

## 0. Document Governance

| Version | Date | Description of Change | Author |
|---|---|---|---|
| v0.1 | 2026-09-17 | First draft: audiences, positioning and proof points, artefacts and milestone cadence, two-flow demo script under ten minutes, portfolio-mode non-goals, narrative risks and the boundary statement. | Shantanu Chaudhary (with Claude Code) |
| v0.2 | 2026-09-17 | Milestone dates removed (artefacts are published when a milestone is reached, whenever that is); roster is three agents; the "Alfred" pen name retired in favour of the founder's name. | Shantanu Chaudhary (with Claude Code) |

---

## 1. What "go to market" means in portfolio mode

There is no market in the commercial sense: no beta families, no pricing, no acquisition spend. The product being taken to market is the **evidence** that the founder can specify an India-first agentic system to production standards, run a team of AI agents against those specs with real review discipline, and ship a kernel whose financial-safety claims are proven by tests rather than asserted. The audience is people who evaluate that evidence. Everything here is therefore about making the evidence findable, legible in ten minutes, and honest about what is simulated.

---

## 2. Audiences and what each needs to see

| Audience | What they are deciding | What they need to see in the first ten minutes | Where it lives |
|---|---|---|---|
| Hiring managers for product and AI-engineering roles | Can this person turn ambiguity into specs, and specs into working, safe software with AI agents? | The review-hardened spec set; the crash-scenario suite passing; the multi-agent workflow with numbers (PRs merged, rejection rate); the demo video | README, Build Log, video |
| Technical leaders (architects, staff engineers, CTOs) | Are the architectural decisions sound and are the invariants actually enforced? | The modular monolith decision (MR §2), the three isolation layers (MR §7), the two-phase commit and Healer (FTS §4, §6), invariant-named tests, the schema-diff test | Architecture Overview, AGENTS.md §4, `tests/` |
| Potential collaborators | Could I contribute without a week of onboarding? | The coordination protocol (roster, labels, review pairs), issues with spec references and verification commands, the Definition of Done, a dev-environment guide that works from a fresh clone | `coordination/README.md`, Execution Plan §7, GitHub issues, Development_Environment_Setup |
| Later: co-founders or investors | Is there a venture here and a path to real DPI integration? | The portfolio result as execution proof; Master Context §8 (licences, phasing), §13 (unit economics) and §14 (GTM) as the commercial plan; Roadmap §6–§7 on what restarts the regulatory track | Master Context, Roadmap §7 |

---

## 3. Positioning and proof points

**Positioning sentence:** an India-first agentic family OS, specified to production standards and built by a coordinated team of AI agents under one human architect.

Every claim in that sentence has a proof point that a reader can open:

| Claim | Proof point | Artefact |
|---|---|---|
| India-first, DPI-native | Designed against AA, BBPS, ABHA, DigiLocker request/response shapes (dated Feb 2026) with contract tests; rate limits, breakers and IST windows from RB §1–§8 implemented, not described | `tests/dpi_contracts/`, gateway code, Simulator spec |
| Agentic, with human sovereignty | Supervisor FSM with an approval gate; Level 3 automation structurally impossible (MR §4.1, invariant 15); the Healer reconciles but never approves | FSM tests, registry schema, Healer tests |
| Specified to production standards | Five P0 specs, each through two independent review rounds, frozen and change-controlled; an inconsistency register that was worked down, not hidden | `docs/specs/`, tracker register, governance tables |
| Financially safe | Two-phase commit, idempotency key reuse, resource locks, and crash scenarios A–D passing in CI (FTS §4.5) | `tests/crash_scenarios/`, CI badge, the crash-and-recover demo |
| Built by coordinated AI agents | Issues and PRs labelled by agent; every PR reviewed by a different agent; per-agent merged-PR and rejection counts; Gemini's PRs next to Codex's and Claude's | GitHub history, Build Log §"How the agents worked", AGENTS.md §6 |
| Under one human architect | The Decision Log; the founder's merges; the specs' design decisions and Q&A sections written in one voice | Tracker Decision Log, spec Q&A |

What to showcase, in priority order: the frozen specs and their review trail; the multi-agent workflow; the crash-scenario suite; the DPI-native design against simulators; the two demo flows. The demo flows come last on purpose: they are the least differentiated part on their own and the most convincing once the reader knows what stands behind them.

---

## 4. Channels, artefacts and cadence

| Artefact | Purpose | Owner | Ready at |
|---|---|---|---|
| GitHub repository with README as landing page | The single entry point: what it is, a 60-second GIF of the bill-pay flow, the boundary statement (§7), how to run it, how the agents work here, the document map | Claude drafts, founder edits (Execution Plan WP-44) | Interim update at M2; final at M5 |
| Build Log (`docs/strategy/Build_Log.md`, cross-posted as a long-form article) | The narrative: problem, spec-first approach, review process, agent workflow with numbers, the crash suite, what is simulated, what would change commercially | Claude drafts, founder edits (WP-44) | M5 |
| Architecture Overview (`docs/reference/Architecture_Overview.md`, one page, one diagram) | The technical reader's second click | Claude, diagram text by Gemini (WP-44) | M5 |
| Demo video, 4–6 minutes | The hiring manager's first click: both flows including crash-and-recover, captions carrying the boundary statement | Founder records; Claude scripts (WP-45) | M5 |
| Demo URL (India region, TLS, synthetic data, invite link) | For conversations, not for discovery; shared with named people | Codex builds, founder hosts (WP-43) | M4 |
| LinkedIn posts at milestones | Short, specific, one artefact each; no hype | Founder, Claude drafts | M2, M3, M5 |

**Cadence tied to the Roadmap milestones:**

- **M2 — Build Gate passed.** Post 1: "Four crash scenarios a bill-payment agent must survive" with a 30-second clip of the Healer recovering Scenario B and a link to the tests. README gains the CI badge and the gate status.
- **M3 — Two slices, one kernel.** Post 2: "Adding a second module without touching the payment path" on the registry, envelope and isolation layers, with the import-linter contract as the punchline.
- **M4 — Demo live.** No public post. The URL goes to a short list of people the founder wants a conversation with, together with the demo script in §5.
- **M5 — Portfolio release.** Build Log published; video published; Architecture Overview linked; Post 3: "What one human and three AI agents shipped", with the measured Roadmap §8 metrics and the honest list of what was cut.

Two posts before M5 at most. The repository has to be readable when someone clicks through, which is why the README update precedes every post.

---

## 5. Demo script (under ten minutes)

Both flows run against the demo host (or Compose locally) with the seeded Sharma family (DM §8): Ravi (admin), Priya (member, primary proxy for Nani), Arjun (minor), Nani (managed profile), Ramesh (staff), and the Kitchen Tablet as a public surface. Amounts and references follow FTS §2.3. The "SIMULATOR" banner stays visible throughout.

### 5.1 "Priya pays the BESCOM electricity bill" with crash-and-recover (about six minutes)

| Time | Step | What is shown | Spec |
|---|---|---|---|
| 0:00 | Open the PWA as Priya on "Priya Phone" (private device). Type, or in Phase 4 say, "Pay the BESCOM electricity bill". | The session panel: `INTENT_ANALYSIS` → `PAY_BILL {biller: BESCOM_KA_001}`, confidence, and the idempotency key already persisted | FSM §1.1; FTS §5.2 |
| 0:40 | Gates run. | G1 RBAC (member ✓); G2 resource lock row on `BBPS_BESCOM_KA_001`; bill fetched from the BBPS simulator: ₹2,847.00 due; G3 forced AA balance fetch from the AA simulator with the ₹50 buffer check | FTS §2.2; MR §10 |
| 1:30 | Approval prompt "BESCOM ₹2,847 — approve?" Priya approves with her passkey (device biometric). | G4 passes; the prompt's five-minute expiry; G5 CONSENT_REVERIFY reads the consent row live | FTS §2.2 G4–G5; CM §5 |
| 2:10 | Execution. | Phase 1 COMMIT (session → `EXECUTION`), one BBPS call, `BBPS-TXN-2847001`, Phase 2 COMMIT (audit row plus session in one transaction), lock released after the commit, push notification in Priya's inbox | FTS §2.3, §4 |
| 2:50 | Verify the audit chain. | `familylifeos audit verify --family <Sharma>` exits 0; the audit row's `details` holds UUIDs and paise only | DM §3.6, Q12 |
| 3:10 | Crash it. Re-run the flow with the crash point `bbps_success` enabled (test build only). | The server dies after BBPS SUCCESS and before Phase 2 COMMIT: session stuck in `EXECUTION`, lock held, no audit row, money "moved" on the simulator | FTS §4.5 row 3 (Scenario B) |
| 4:00 | Run the Healer once. | Zombie detected; BBPS status poll returns SUCCESS; `AUDIT_LOG_WRITE` queued at P1 and processed; audit row written, session `SUCCESS_CONFIRMATION`, lock released, notification sent; the WireMock request journal shows exactly one payment call and the same idempotency key | FTS §6.3–6.4; invariant 16 |
| 5:20 | Optional: while a lock is held, Ravi tries to pay BESCOM too. | FIN_009 "a payment is already in progress"; the lock is per family, not per user | FTS §9.4; Finance PRD Scenario 3 |

### 5.2 "Nani's medication reminder via proxies" (about three minutes)

| Time | Step | What is shown | Spec |
|---|---|---|---|
| 0:00 | Ravi opens Health for Nani (managed profile; Priya primary proxy, Ravi secondary). | Proxy assignments and the admin-default-notify rule | PRD §2, §4.4; DM §3.4 |
| 0:30 | Fetch Nani's prescription from the ABHA simulator. | One `MedicationRequest` parses cleanly; one has a broken dosage and is stored as `PARTIAL` with the RB §5.3 warning; the DPI breaker did not trip | CM §6.2.2; RB §5.3 |
| 1:10 | Reminder schedule created; the demo clock is advanced to the next dose. | The nudge appears in Priya's inbox and in Ravi's (admin default) | Scenario 2 |
| 1:50 | Priya marks the dose "Done". | It disappears from Ravi's feed at once; the medication event is audited | Scenario 2 |
| 2:20 | On the Kitchen Tablet, ask "What medicines does Nani take?" | Blocked: public surfaces never show health data, whoever is logged in | Scenario 9; invariant 6 |
| 2:50 | Close on the Grafana dashboard. | Both flows, Healer runs, breaker states, simulator budgets | RB §10.1; MR §11 |

Total about nine minutes. The 4–6 minute video keeps 5.1 up to the Healer recovery and 5.2 up to the Kitchen Tablet, and cuts the optional step and the dashboard.

---

## 6. Deliberately not done in portfolio mode

- No paid acquisition, no pricing page, no waitlist, no beta families, no referral programme, no corporate or senior-care partnerships, no TV or content marketing. Master Context §14.2–14.3 holds all of that for commercial mode and is not rewritten here.
- No persona-based messaging pillars ("save 12 hours a month"); the portfolio audience is not the household and the claims are unproven without users. MC §14.4 keeps the commercial messaging and trust anchors; this plan reuses only the two trust anchors that are demonstrable now (tamper-evident audit log, no raw credentials in the database).
- No app-store presence, no WhatsApp or SMS channels, no support model, no NPS. PRD §7 and MC §9 metrics that need users are replaced by the Roadmap §8 build metrics.
- No outreach to DPI bodies, sandbox programmes or licensing consultants. The regulatory track is parked (Roadmap §6) and the write-up says so.

---

## 7. Risks to the narrative and how to state it honestly

| Risk | Why it matters | Mitigation |
|---|---|---|
| Simulators mistaken for real integrations | A reader who later learns the DPI calls went to WireMock feels misled, and the whole portfolio loses credibility | The boundary statement below appears in the README, the Build Log, the video captions, every post and the demo UI banner; the Simulator spec carries a "simulated vs real" table; no screenshot or clip omits the banner |
| "The AI did all the work" | Hiring managers discount agent-built code unless the human judgement is visible | Show the Decision Log, the review trail with rejections, the invariants the founder wrote before code existed, and the per-agent statistics; say plainly which parts the agents wrote |
| Over-claiming "production standards" | The specs are production-grade; the deployment is a demo | Say "specified to production standards"; list what is not production (no DR, no licences, no pen test, PWA stand-ins for biometrics, push and voice) in the same breath |
| Regulatory naïveté | Anyone from Indian fintech will ask about FIU/BBPOU/HIU | Roadmap §6–§7 and the Build Log state the licences, the 6–12 month timeline (MC §8) and that they are parked by decision, not by oversight |
| Demo fragility | A live URL that fails in a conversation is worse than no URL | The video is the primary artefact; the URL is invite-only and rehearsed with the §5 script; the k6 run and CI badge carry the reliability claim |
| "Only two flows" | Looks thin next to the eight pillars in the vision | Frame it as a kernel plus two slices chosen to exercise payment safety and the family graph; point to the third-slice option in Roadmap §4.1 |
| Privacy claims without users | "Zero-knowledge" and "no PII to hosted LLMs" are easy to say | Show the scrubber test, the no-bytes-in-database test for the Vault and the audit payload models; do not use "zero-knowledge" for anything the demo does not implement |

**Boundary statement (use verbatim):**

> Every DPI interaction in this project — Account Aggregator, BBPS, ABHA and DigiLocker — goes to WireMock simulators that implement the request and response shapes documented in February 2026. No real money, real health record, real government API or real person's data is involved. FamilyLifeOS holds no FIU, BBPOU or HIU registration; obtaining them is the first step of the commercial track described in Master Context §8, and it has deliberately not been started.

---

## 8. How to tell whether this worked

Modest, observable signals, reviewed at the M5 retrospective (Roadmap §8 covers the build itself):

- The README is readable in ten minutes by someone who has never seen the project (test it on two people before M5).
- Each post links to one artefact that exists and works on the day of posting.
- Conversations that start from the video or the Build Log: count them; the target is a handful of substantive ones, not reach.
- Nobody who reads the material comes away believing real DPI integrations exist. If one person does, the boundary statement is not prominent enough and the artefacts are revised before anything else is published.

---

## 9. Assumptions the founder should confirm

1. The primary audience is hiring managers and technical leaders; co-founders and investors are secondary and later.
2. Public artefacts are the repository, the Build Log, the video and at most three LinkedIn posts (M2, M3, M5); the demo URL is shared privately.
3. The boundary statement in §7 is acceptable as written and will appear verbatim in every artefact.
4. The demo uses the Sharma seed family only; no additional personas are created for the video.
5. Video visibility (public or unlisted). Public artefacts carry the founder's own name; the earlier "Alfred" pen name is retired.
6. Posts are tied to milestones, not dates: a post goes out when its milestone is reached and never before.
