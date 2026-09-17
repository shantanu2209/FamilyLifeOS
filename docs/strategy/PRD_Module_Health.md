# PRD: Health & Wellness (module `health`)

> **Status:** DRAFT v0.1 — pending review · **Author:** Shantanu Chaudhary (Lead Product Architect), drafted with Claude Code · **Last content change:** 2026-09-17
> **Scope:** Phase 1, portfolio-first build against DPI simulators. Module-level PRD that Tech_Spec_Module_Registry §1.2 defers to. Owns vertical slice 2, "Nani's medication reminder via her proxies" (Core PRD Scenario 2).
> **Depends on:** CM v1.2 §2.3 (data minimisation), §2.5 (minors), §3.2 (ABHA_PRESCRIPTION, ABHA_DIAGNOSTICS, ABHA_VITALS), §4.2 (grant flow), §5 (CONSENT_REVERIFY), §6.2 (ABHA adapter), §7 (expiry watchdog), §9.4 (ABDM webhook) · RB v1.2 §5 (ABHA limits, FHIR parse handling, degraded mode), §8.2 (ABHA breaker), §9.4 (chaos `abha_fhir_malformed`) · MR v1.1 §3, §4, §6, §7, §9 · DM v1.3 §3.4 (proxy_assignments, conflict rules), §3.8 (public surface), §3.9 (`HEALTH_FETCH` task), §8 (seed), §9.3, plus DM v1.3 decisions (roles, `core` schema) · FSM v2.1 §2, §3.1 (health records TTL 7 days) · Core PRD v2.2 §2, §3 (Scenarios 2, 3, 9, 10), §4.4 (proxy framework), §5, §6 · MC §4.3, §4.6, §4.7 · PROJECT_TRACKER Decision Log and Phase 1 Build Gate.

Status: In-Progress
Author: Shantanu Chaudhary (Lead Product Architect)
Primary Agent: HealthAgent (`modules.health.agent:HealthAgent`)
Engineering Lead: Shantanu Chaudhary (solo founder)
Design Lead: Shantanu Chaudhary
Approvers: Shantanu Chaudhary, after one independent review round; medical-disclaimer wording needs a legal read (OI-1)

## 0. Document Governance

| Version | Date | Description of Change | Author |
|---|---|---|---|
| v0.1 | 2026-09-17 | Initial draft for the Phase 1 portfolio build. | Shantanu Chaudhary (with Claude Code) |

## 1. The One-Pager (Executive Summary)

- **Overview:** HealthAgent is the Core-tier module that turns ABHA-linked prescriptions into a medication schedule and drives reminders to the right humans — the proxies of a managed profile, with the admin informed by default. In Phase 1 it is the second vertical slice and the first exercise of the Managed Profile & Proxy Framework (Core PRD §4.4), of a non-financial DPI with an 85 % uptime reality (MC §4.6), and of the "parse what you can, say what you couldn't" rule for FHIR bundles (RB §5.3).
- **The Problem (The Friction):** Nani has no phone. Her prescriptions live in a hospital's ABDM record, a WhatsApp photo and a paper strip. Priya reminds her in the morning, Ravi asks in the evening whether it happened, and twice a month nobody is sure — so either a dose is missed or it is given twice. MC §1.1: "No visibility into parents' health."
- **Objectives (The Outcome):**
    1. Fetch a prescription for a managed profile through the ABHA simulator under a recorded consent, storing parsed fields only (CM §2.3).
    2. Propose a deterministic schedule from the prescription; a proxy confirms it; nothing is scheduled by inference alone.
    3. Nudge the primary proxy at the due time, escalate to the secondary after `notify_timeout_mins`, notify the admin by default, and make "Done" a single family-wide state so a dose is never given twice (Core PRD Scenario 2, §4.4).
    4. Degrade honestly: a malformed FHIR bundle produces a PARTIAL record with a visible warning, never a silent gap or a crash (RB §5.3); ABDM downtime leaves local reminders working (RB §5.4).
- **Constraints:** Portfolio mode — no HIU registration, ABHA only through WireMock (Decision Log 2026-09-17). Solo founder — reminder logic must be deterministic and testable, not LLM-judged. No medical advice: every health surface carries the Core PRD Scenario 3 disclaimer; the module never suggests dose changes, interactions or "take two now". Level 3 forbidden; a fetch is Level 1 with a passkey. No health detail on public-surface devices (DM §3.8). Retention: parsed prescription fields 7 years (CM §3.2), cache freshness 7 days (FSM §3.1).

## 2. Personas & The Family Graph (RBAC)

### Target Personas

- **Key persona:** Nani — Savitri Sharma, `managed`, no phone, no login; the subject of every record and reminder.
- **Key persona:** Priya (`member`, primary proxy) — grants consent on Nani's behalf, confirms the schedule, receives the 08:00 nudge, marks Done.
- **Secondary personas:** Ravi (`admin`, secondary proxy) — default notifications, escalation target, sees the same single state; Ramesh (`staff`) and Arjun (`minor`) — locked out; a future `elder` with her own phone — self-service via TTS (not in the seed).

### Access Control Matrix

| Role | Health access | Can | Cannot | Enforcement note |
|---|---|---|---|---|
| admin | Full for self and for managed profiles | All intents for self; act for a managed profile only when listed in `proxy_assignments`; receive every managed-profile nudge by default (Core PRD Scenario 2); activate/deactivate the module | See a member's own records without that member's consent scope; change a dose; approve on a public surface | Admin ≠ automatic proxy; DM §3.4 assignment is explicit |
| member | Own records; proxy for assigned managed profiles | `FETCH_PRESCRIPTION`, `LIST_MEDICATIONS`, `ADD_MEDICATION`, `MARK_MEDICATION_TAKEN` for self and for managed profiles where `acting_as` is validated by the Supervisor | Act for a managed profile without an assignment; see other adults' records | `PROXY_ACTION` audit on every acting_as dispatch |
| minor | None in Phase 1 | — | Any health intent | DM Q2 gives `child`/`minor` no health module; parental-consent fetches (CM §2.5) deferred |
| elder | Own records and reminders | Self-service fetch with passkey, own medication list, mark own dose Done; TTS reminders | Any other member's data | Voice stand-in with RB §7.3 thresholds; not in the Sharma seed |
| staff | None | — | Any health intent, including "Nani ki dawai kya hai" | BLOCKED + `ROLE_VIOLATION` + admin alert; caregiver-staff nudges are P2 (OI-6) |
| managed | Subject only; no login | Be the subject of records, schedules and nudges; a single state per task | Anything directly | All actions via primary/secondary proxy with the DM §3.4 conflict rule |
| passive | Tracked, never contacted | Have manually entered medications recorded by the admin for the admin's own view | Receive nudges or any message | Core PRD §2: the OS never nudges a passive node |

## 3. User Scenarios / Use Cases

Seed as in DM §8: Nani (`usr-nani…0004`, `managed`), proxies Priya primary / Ravi secondary, `conflict_resolution_rule = 'hierarchy'`, `notify_timeout_mins = 60`. Nani's ABHA address in the simulator is synthetic (`nani.sharma@sbx`), and is held only inside the consent handle's `data_scope`, never in `health.*`.

### Scenario 1 — Nani's medication reminder via her proxies (the vertical slice)

1. Priya, Priya Phone, 19:30 IST: *"Nani ke prescription se dawai ka reminder set karo."* INTENT_ANALYSIS → `FETCH_PRESCRIPTION {subject_user_id: Nani}` with `actor.acting_as = {managed_user_id: Nani, proxy_assignment_id: …}` validated by the Supervisor (MR §6.2).
2. No active `ABHA_PRESCRIPTION` consent exists for Nani. The Supervisor routes to the CM §4.2 grant flow: Priya, as primary proxy, sees the disclosure in Hindi (drug name, dosage, prescribing doctor; retained 7 years; how to revoke), confirms with her passkey; the ABHA simulator's consent-request/init returns a request id, the simulated approval callback (CM §9.4 JWT) flips the handle to active; `consent_records` + `CONSENT_GRANTED` are written in one transaction. Consent on behalf of a managed profile is not defined by CM v1.2 — assumption recorded in OI-2. ABHA grant budget: 1 of 10 today (RB §5.2).
3. PERMISSION_CHECK passes; APPROVAL_GATE: passkey prompt "Fetch Nani's prescriptions from Apollo (simulator) via ABHA?" (§7). CONSENT_REVERIFY reads live. EXECUTION: HI request through the DPI Gateway (CM §6.2.2), callback delivers a FHIR R4 bundle with two `MedicationRequest`s: Amlodipine 5 mg once daily, morning; Metformin 500 mg twice daily, after meals. Parse quality FULL. Two `health.records` rows hold parsed fields only; the bundle is discarded. `cache_metadata {fetched_at, source_api: 'abha_sim', expires_at: +7 days}`.
4. HealthAgent proposes a schedule from deterministic rules (§4.1): Amlodipine 08:00; Metformin 08:30 and 20:30 IST. Priya edits Metformin to 09:00/21:00 and confirms → `ADD_MEDICATION` writes two `health.medications` rows (`source = 'ABHA'`, `verified = TRUE`); audit `PROXY_ACTION`.
5. Next morning 08:00 IST the sweep creates a `health.medication_events` row (DUE) and `notification_engine` pushes "Nani: Amlodipine 5 mg — 08:00. Mark as given?" to Priya Phone (primary) and, by default, a quieter copy to Ravi Phone. The Kitchen Tablet shows nothing.
6. Priya taps Done at 08:12 → `MARK_MEDICATION_TAKEN` (mutating, idempotency key from the session) → event TAKEN, `resolved_by = Priya`. The card on Ravi's phone clears within one refresh — one state for the whole system (Core PRD §4.4). Had Priya not acted by 09:00 (`notify_timeout_mins`), Ravi would have received the secondary nudge; at 10:00 the event becomes MISSED and both proxies see it, with no advice attached.

### Scenario 2 — A second hospital sends a malformed bundle (FHIR partial parse)

Ravi fetches Nani's records from a second simulated HIP with the chaos scenario `abha_fhir_malformed` (RB §9.4). HTTP 200, but the `MedicationRequest` for Telmisartan has no `dosageInstruction`. The parser keeps drug name and prescriber, records `parse_quality = 'PARTIAL'`, `parse_errors = [{path: 'entry[0].resource.dosageInstruction', error: 'missing'}]`, increments `dpi.abha.fhir_parse_error{hip_id}` and returns success with `display_key health.fhir_parse_warning` ("Some health record details could not be read automatically. Please check the original record from Manipal (simulator)"). The proposed medication appears as a draft that cannot be scheduled until Ravi completes the dosage by hand (`ADD_MEDICATION`, `source = 'ABHA'`, `verified = FALSE`, "Unverified" tag). The circuit breaker is untouched (200 is not a failure). A fully unparseable bundle yields `parse_quality = 'FAILED'`, no draft, and the manual-entry path. More than five parse errors from one HIP in 24 h alert the admin (RB §5.3).

### Scenario 3 — Both proxies act on the same dose

Priya marks the 21:00 Metformin dose Taken at 21:05; Ravi, not seeing the refresh, marks it Skipped at 21:05:02. Rule `hierarchy` (DM §3.4): the primary's action wins, Ravi's is rejected silently with an audit row for both (`PROXY_ACTION`, then HEALTH_006 in the second envelope), and Ravi's card shows "Marked as given by Priya at 21:05". Under `notify_block` the event would pause in CONTESTED and both proxies plus the admin would be alerted to resolve it. A double tap by Priya alone is absorbed by the idempotency ledger and the `UNIQUE (medication_id, due_at)` constraint.

### Scenario 4 — The kitchen tablet, the driver, and ABDM going down

Ravi asks the Kitchen Tablet "Nani ki dawai ho gayi?" — `is_public_surface` blocks the response before dispatch: "I can only show health details on a private device" (Core PRD Scenario 9). Ramesh asks his phone the same question — BLOCKED, `ROLE_VIOLATION`, admin alert. That evening the ABHA simulator returns three consecutive 500s; the ABHA breaker opens for 20 minutes (RB §8.2). Priya's refresh returns `MOD_DPI_DOWN` → degraded mode (RB §5.4): "Government health records are temporarily unavailable. Your locally stored health information is still accessible." The 21:00 nudge fires normally from `health.medications`; manual entry stays allowed; new consent grants and fetches are blocked; the expected-restore time is shown.

### Scenario 5 — Consent expiry watchdog (Core PRD Scenario 10)

Eleven months later the 06:00 IST watchdog (CM §7.2) finds Nani's `ABHA_PRESCRIPTION` record expiring in 3 days and notifies Priya, with a copy to Ravi because the purpose is a DPI purpose. Renewal follows CM §7.3 (new record and handle, old one expired) and consumes one of the day's 10 ABHA grants. If ignored, fetches fail at CONSENT_REVERIFY with HEALTH_001 while reminders keep running from the local schedule.

## 4. Functional Requirements (The "Agentic" Loop)

### 4.1 The loop for prescriptions and reminders

- **Trigger:** a proxy's or member's request on a private device (`FETCH_PRESCRIPTION`, `ADD_MEDICATION`, `LIST_MEDICATIONS`); a UI action on a nudge (`MARK_MEDICATION_TAKEN`); the module's 5-minute sweep (`sweep_due_medications()`, registered through the SDK scheduler — MR v1.1 has no scheduling contract, see OI-3) which creates DUE events, sends nudges, escalates and marks MISSED; the kernel's consent expiry watchdog (CM §7) which only produces a renewal CTA.
- **Information gathering:** actor role and `acting_as` from the envelope; family membership, proxy rank, `conflict_resolution_rule` and `notify_timeout_mins` for managed members from `v_family_members` (assumption: DM v1.3 exposes proxy columns in the view, MR OI-2); device surfaces from `v_device_surfaces`; consent references from `v_active_consents`; the ABHA simulator HI request through the DPI Gateway (consent artefact, `hiTypes ['Prescription']`, CM §6.2.2); local `health.medications` and `health.medication_events`.
- **Analysis logic (deterministic; the LLM only classifies intent):** FHIR R4 `MedicationRequest` → `{drug_name, dosage_text, timing, prescriber, authored_on}`; each missing or malformed field is a `parse_errors` entry, not an exception; `parse_quality` = FULL if all four core fields parse, PARTIAL if drug name parses, FAILED otherwise. Timing → default slots: once daily 08:00; twice daily 08:30/20:30; thrice 08:00/14:00/20:30; "after meals" shifts +30 min; unknown timing → draft with no slots. The proxy always confirms slots. Escalation: DUE → NUDGED (primary) → secondary nudge at `notify_timeout_mins` → MISSED at 2 × `notify_timeout_mins` (assumption). Nothing computes "what to do about a missed dose".
- **Execution / fulfilment:** `FETCH_PRESCRIPTION` writes `health.records` (parsed fields only, CM §2.3) and returns `cache_metadata`; `ADD_MEDICATION` and `MARK_MEDICATION_TAKEN` write their tables inside one transaction with the idempotency ledger row and a `PROXY_ACTION` audit through `core.fn_append_audit` when `acting_as` is set; nudges go through `notification_engine` to private devices only, with the admin copy per Core PRD Scenario 2. No ONDC, no UHI, no payments; a medicine purchase would return `status: conflict` to the Supervisor.

### 4.2 Features In (Prioritised)

- **`FETCH_PRESCRIPTION` [M]:** ABHA simulator fetch for self or a managed profile under `ABHA_PRESCRIPTION`, Level 1 with passkey, CONSENT_REVERIFY, parsed fields only, 7-day cache metadata.
- **Schedule proposal + `ADD_MEDICATION` [M]:** deterministic slot rules, proxy confirmation, ABHA-sourced (`verified`) or manual ("Unverified", MC §4.7) entries.
- **Proxy nudges with escalation [M]:** primary → secondary after `notify_timeout_mins`, admin default copy, MISSED marking; private devices only.
- **`MARK_MEDICATION_TAKEN` [M]:** single family-wide state, idempotent, DM §3.4 conflict rule applied.
- **FHIR partial-parse handling [M]:** PARTIAL/FAILED records, warning copy, per-HIP error counting and admin alert (RB §5.3).
- **`LIST_MEDICATIONS` [M]:** today's plan for a subject with DUE/TAKEN/MISSED status; the source of the live card.
- **Degraded mode [M]:** local reminders and manual entry continue when the ABHA breaker is OPEN (RB §5.4).
- **Consent expiry CTA:** renewal entry point for CM §7 notifications.
- **`FETCH_DIAGNOSTICS`:** `ABHA_DIAGNOSTICS` reports as read-only records (Phase 1.1, manifest 0.2.0).

### 4.3 Features Out

- **Vitals from wearables (`ABHA_VITALS`), SOS, fall detection:** Elder Care Protocol, Phase 3 (MC §5.1); SOS is a kernel state (Core PRD Scenario 7).
- **UHI appointment booking, ONDC pharmacy orders (Master PRD Module 1):** commerce rails, ONDC seller risk (MC §4.6), Phase 3.
- **Diet / pantry-photo guidance (Core PRD Scenario 3):** needs vision and a medical-content policy; out of Phase 1.
- **Drug-interaction or dose-change suggestions:** liability and no licensed drug database; the module never advises.
- **Parental-consent fetches for minors (CM §2.5):** no health access for `minor` in Phase 1 (DM Q2).
- **Photo/OCR of paper prescriptions:** `ocr` service module is P2; manual entry covers the gap.
- **Raw FHIR bundle storage, document upload:** forbidden by CM §2.3; Vault documents are metadata-only.

### 4.4 Module manifest (Module Registry contract)

Valid against MR §4.1. `FETCH_PRESCRIPTION` is a read intent (`mutating: false`) that must still pass CONSENT_REVERIFY per CM §5.1 — assumption for MR v1.1: the Supervisor runs CONSENT_REVERIFY for every intent whose `requires_consent_providers` is non-empty, not only mutating ones.

```json
{
  "manifest_version": 1,
  "module_id": "health",
  "version": "0.1.0",
  "tier": "core",
  "display_name": { "en": "Health & Wellness", "hi": "स्वास्थ्य और कल्याण" },
  "description": "ABHA prescription fetch, medication schedules and proxy reminders for family members and managed profiles. Phase 1 vertical slice: Nani's medication reminder.",
  "deactivatable": true,
  "entrypoint": "modules.health.agent:HealthAgent",
  "health_check": "health",
  "intents": [
    {
      "intent_code": "FETCH_PRESCRIPTION",
      "description": "Fetch prescriptions for a family member or managed profile via ABHA and store parsed fields only.",
      "automation_tier_ceiling": 1,
      "allowed_roles": ["admin", "member", "elder"],
      "mutating": false,
      "requires_consent_providers": ["abha"],
      "entities_schema": {
        "type": "object",
        "additionalProperties": false,
        "required": ["subject_user_id"],
        "properties": {
          "subject_user_id": { "type": "string", "format": "uuid" },
          "hi_types": { "type": "array", "items": { "enum": ["Prescription"] }, "default": ["Prescription"] },
          "hip_id": { "type": ["string", "null"] },
          "since_days": { "type": "integer", "minimum": 1, "maximum": 730, "default": 365 }
        }
      }
    },
    {
      "intent_code": "ADD_MEDICATION",
      "description": "Create or complete a medication schedule (from a parsed record or manual entry).",
      "automation_tier_ceiling": 0,
      "allowed_roles": ["admin", "member", "elder"],
      "mutating": true,
      "requires_consent_providers": [],
      "entities_schema": {
        "type": "object",
        "additionalProperties": false,
        "required": ["subject_user_id", "drug_name", "dosage_text", "schedule_times", "source"],
        "properties": {
          "subject_user_id": { "type": "string", "format": "uuid" },
          "record_id": { "type": ["string", "null"], "format": "uuid" },
          "drug_name": { "type": "string", "maxLength": 120 },
          "dosage_text": { "type": "string", "maxLength": 200 },
          "schedule_times": { "type": "array", "minItems": 1, "maxItems": 6, "items": { "type": "string", "pattern": "^([01][0-9]|2[0-3]):[0-5][0-9]$" } },
          "start_date": { "type": "string", "format": "date" },
          "end_date": { "type": ["string", "null"], "format": "date" },
          "source": { "enum": ["ABHA", "MANUAL"] }
        }
      }
    },
    {
      "intent_code": "MARK_MEDICATION_TAKEN",
      "description": "Resolve a due medication event as TAKEN or SKIPPED; one state for the whole family.",
      "automation_tier_ceiling": 0,
      "allowed_roles": ["admin", "member", "elder"],
      "mutating": true,
      "requires_consent_providers": [],
      "entities_schema": {
        "type": "object",
        "additionalProperties": false,
        "required": ["event_id", "outcome"],
        "properties": {
          "event_id": { "type": "string", "format": "uuid" },
          "outcome": { "enum": ["TAKEN", "SKIPPED"] },
          "note": { "type": ["string", "null"], "maxLength": 200 }
        }
      }
    },
    {
      "intent_code": "LIST_MEDICATIONS",
      "description": "Today's medication plan and event status for a subject.",
      "automation_tier_ceiling": 0,
      "allowed_roles": ["admin", "member", "elder"],
      "mutating": false,
      "requires_consent_providers": [],
      "entities_schema": {
        "type": "object",
        "additionalProperties": false,
        "properties": {
          "subject_user_id": { "type": ["string", "null"], "format": "uuid" },
          "day": { "type": ["string", "null"], "format": "date" }
        }
      }
    }
  ],
  "data_scopes": {
    "owns_schema": "health",
    "core_read_views": ["v_family_members", "v_module_permissions", "v_active_consents", "v_device_surfaces"]
  },
  "dpi_providers": ["abha"],
  "service_dependencies": ["notification_engine"],
  "data_dependencies": ["secure_vault"],
  "resource_budgets": { "p95_handler_ms": 300, "hard_timeout_ms": 30000 }
}
```

### 4.5 Owned schema (`health`)

DM §9.3 conventions; role `role_module_health` (MR §7.2); FKs to `core.*` created by the migration role. `user_id` is the **subject** (Nani), `created_by_user_id` the actor. Four tables:

| Table | Purpose | Notes |
|---|---|---|
| `health.records` | Parsed FHIR fields per fetched resource; never the bundle | `parse_quality` FULL / PARTIAL / FAILED; `expires_at` is cache freshness (7 days), the row itself is retained per CM §3.2 (7 years) |
| `health.medications` | Confirmed schedules | `source` ABHA / MANUAL; `verified` mirrors the "Unverified" tag |
| `health.medication_events` | One row per due slot; the single family-wide state | `UNIQUE (medication_id, due_at)` is the double-dose guard |
| `health.idempotency_ledger` | MR §6.4 ledger for the two mutating intents | Same shape as `finance.idempotency_ledger` |

```sql
CREATE SCHEMA health;

CREATE TABLE health.records (
  record_id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  family_id           UUID        NOT NULL REFERENCES core.families(family_id) ON DELETE CASCADE,
  user_id             UUID        NOT NULL REFERENCES core.users(user_id) ON DELETE CASCADE,   -- subject
  created_by_user_id  UUID        NOT NULL REFERENCES core.users(user_id),                      -- actor (proxy or self)
  consent_record_ref  UUID        NOT NULL,                       -- consent_records.record_id, reference only
  hip_id              VARCHAR(60) NOT NULL, hip_name VARCHAR(120),
  fhir_resource_type  VARCHAR(30) NOT NULL CHECK (fhir_resource_type IN ('MedicationRequest','DiagnosticReport','Observation')),
  fhir_resource_ref   VARCHAR(120) NOT NULL,                      -- resource id inside the bundle, not the bundle
  parsed_fields       JSONB       NOT NULL DEFAULT '{}',          -- drug_name, dosage_text, timing, prescriber, authored_on
  parse_quality       VARCHAR(10) NOT NULL CHECK (parse_quality IN ('FULL','PARTIAL','FAILED')),
  parse_errors        JSONB       NOT NULL DEFAULT '[]',          -- [{path, error}]
  fetched_at          TIMESTAMPTZ NOT NULL, source_api VARCHAR(40) NOT NULL, expires_at TIMESTAMPTZ NOT NULL,  -- FSM §3.1
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), deleted_at TIMESTAMPTZ,
  UNIQUE (family_id, hip_id, fhir_resource_ref)
);
CREATE INDEX idx_records_family_created ON health.records(family_id, created_at DESC);

CREATE TABLE health.medications (
  medication_id       UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  family_id           UUID        NOT NULL REFERENCES core.families(family_id) ON DELETE CASCADE,
  user_id             UUID        NOT NULL REFERENCES core.users(user_id) ON DELETE CASCADE,   -- subject
  created_by_user_id  UUID        NOT NULL REFERENCES core.users(user_id),
  record_id           UUID        REFERENCES health.records(record_id),                        -- NULL for manual entries
  drug_name           VARCHAR(120) NOT NULL, dosage_text VARCHAR(200) NOT NULL,
  schedule_times      JSONB       NOT NULL,                       -- ["08:00","20:30"] IST
  start_date          DATE        NOT NULL, end_date DATE,
  source              VARCHAR(10) NOT NULL CHECK (source IN ('ABHA','MANUAL')),
  verified            BOOLEAN     NOT NULL DEFAULT FALSE,          -- TRUE only when derived from a FULL ABHA record
  status              VARCHAR(10) NOT NULL DEFAULT 'active' CHECK (status IN ('draft','active','paused','completed')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), deleted_at TIMESTAMPTZ
);
CREATE INDEX idx_medications_family_created ON health.medications(family_id, created_at DESC);
CREATE INDEX idx_medications_active ON health.medications(user_id) WHERE status = 'active' AND deleted_at IS NULL;

CREATE TABLE health.medication_events (
  event_id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  family_id           UUID        NOT NULL REFERENCES core.families(family_id) ON DELETE CASCADE,
  user_id             UUID        NOT NULL REFERENCES core.users(user_id) ON DELETE CASCADE,   -- subject
  medication_id       UUID        NOT NULL REFERENCES health.medications(medication_id),
  due_at              TIMESTAMPTZ NOT NULL,
  status              VARCHAR(10) NOT NULL DEFAULT 'DUE' CHECK (status IN ('DUE','NUDGED','ESCALATED','TAKEN','SKIPPED','MISSED','CONTESTED')),
  nudged_primary_at   TIMESTAMPTZ, nudged_secondary_at TIMESTAMPTZ,
  resolved_by_user_id UUID        REFERENCES core.users(user_id), resolved_at TIMESTAMPTZ,
  idempotency_key     UUID        UNIQUE,                         -- from the MARK_MEDICATION_TAKEN dispatch
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), deleted_at TIMESTAMPTZ,
  UNIQUE (medication_id, due_at)                                  -- the double-dose guard
);
CREATE INDEX idx_events_family_created ON health.medication_events(family_id, created_at DESC);
CREATE INDEX idx_events_open ON health.medication_events(due_at) WHERE status IN ('DUE','NUDGED','ESCALATED');

CREATE TABLE health.idempotency_ledger (                          -- MR §6.4, same shape as finance
  idempotency_key UUID PRIMARY KEY,
  family_id UUID NOT NULL REFERENCES core.families(family_id) ON DELETE CASCADE,
  user_id   UUID NOT NULL REFERENCES core.users(user_id) ON DELETE CASCADE,
  intent_code VARCHAR(40) NOT NULL,
  status VARCHAR(10) NOT NULL CHECK (status IN ('pending','final')),
  response_envelope JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), deleted_at TIMESTAMPTZ
);
CREATE INDEX idx_health_ledger_family_created ON health.idempotency_ledger(family_id, created_at DESC);
```

## 5. India Stack (DPI) Touchpoints

Simulators only in Phase 1 (Decision Log 2026-09-17). ABDM's real flow is asynchronous (HI request → encrypted callback, CM §6.2.2); the simulator answers within the dispatch deadline, and the production adapter would move the wait into a `HEALTH_FETCH` task (DM §3.9) — noted in §8.

- **Identity:** ABHA address of the subject (synthetic in the simulator) lives only in `consent_handles.data_scope`; no ABHA number, no Aadhaar anywhere in `health.*`. Passkey (WebAuthn) stands in for the biometric on consent grant and fetch approval.
- **Data — ABHA / ABDM (consent provider `abha`):** purpose codes `ABHA_PRESCRIPTION` [M] (drug name, dosage, prescriber; 7-year retention; minors only with parental consent), `ABHA_DIAGNOSTICS` (Phase 1.1), `ABHA_VITALS` (out). Grant flow CM §4.2 + §6.2.1 (consent-requests/init, approval callback with an ABDM-style JWT per CM §9.4), fetch CM §6.2.2 with `hiTypes` limited to the granted scope (CM §2.3). Budget: 10 consent grants/day per user (RB §5.2), fetches not rate-limited by ABDM; the module self-limits refreshes to the 7-day TTL unless forced. Breaker: 3 consecutive failures → OPEN 20 min, backoff 1 s/2 s/4 s, probe 15 s (RB §8.2).
- **Stubs:** RB §9.4 chaos `abha_fhir_malformed` (30 % malformed bundles) is the only ABHA stub the runbook defines. Needed and to be defined in Tech_Spec_Simulator_Architecture (P1): consent-request init and approval callback with a signed JWT, HI request returning FHIR R4 `MedicationRequest` bundles for two synthetic HIPs, the HTTP 429 for the grant budget, HIP-outage 500s for the breaker, and fixtures for FULL / PARTIAL / FAILED parse cases.
- **Payments, commerce:** none. **Voice:** browser speech stand-in with RB §7.3 thresholds; TTS reads reminders for `elder` users on private devices.

## 6. Conflict Resolution Matrix

| # | Conflict scenario | Resolution logic |
|---|---|---|
| 1 | Primary and secondary proxy resolve the same dose differently | `proxy_assignments.conflict_resolution_rule` (DM §3.4): `hierarchy` → primary wins, secondary rejected silently, both logged; `notify_block` → event CONTESTED, both proxies + admin alerted, no state change until one resolves it. |
| 2 | Same proxy double-taps Done | Idempotency ledger returns the stored envelope; `UNIQUE (medication_id, due_at)` blocks a second event. |
| 3 | Proxy marks Done, admin (not a proxy) wants to undo | Admin is notified by default but is not a proxy unless assigned (Core PRD Scenario 2 makes Ravi secondary here); a non-proxy admin can only comment, never change the event. |
| 4 | FHIR dosage vs proxy's manual dosage differ | The record keeps both: `parsed_fields` from ABHA, the confirmed `dosage_text` on the medication with `verified = FALSE` when they differ; the card shows "differs from hospital record". Core PRD §6's "visual truth overrides log" applies to photos, which are out of Phase 1. |
| 5 | Health wants a pharmacy order, Finance says balance is low | HealthAgent returns `status: conflict`; the Supervisor conserves resources (Core PRD §6); no Core → Core call (MR §3.2). |
| 6 | ABDM breaker OPEN during a scheduled nudge | Nudges never depend on ABHA; they run from local rows. Fetch requests get `MOD_DPI_DOWN` and the RB §5.4 degraded copy. |
| 7 | Restricted role (staff / minor) or public surface asks about medicines | BLOCKED before dispatch; `ROLE_VIOLATION` audit and admin alert for roles; surface block with no data (Core PRD Scenario 9). |
| 8 | Consent expired mid-day | Fetch fails at CONSENT_REVERIFY (HEALTH_001); local reminders continue; renewal CTA to the proxy and admin (CM §7). |

## 7. Design & Generative UI

- **Live card "Today's medicines" (private devices only):** per subject, one chip per slot — DUE (grey), NUDGED (amber, "waiting for Priya"), ESCALATED ("waiting for Priya or Ravi"), TAKEN (green, "given by Priya 08:12"), SKIPPED, MISSED (red, no advice text). Tapping a chip is the `MARK_MEDICATION_TAKEN` UI action. The admin's copy of the card is the same state, read-only unless the admin is an assigned proxy.
- **Nudge content:** subject's display name, drug, dose, slot, "Mark as given?" with Done / Skip actions; no diagnosis, no prescriber, no reason. Secondary nudge adds "Priya hasn't responded yet".
- **Fetch states:** `consent_needed` (CM disclosure in the user's language: what, why, how long, how to revoke) → `awaiting_approval` (passkey prompt: "Fetch Nani's prescriptions from Apollo (simulator) via ABHA? Purpose: medication reminders. Retained per your consent; cached 7 days.") → `fetching` → `parsed_full` / `parsed_partial` (amber banner with the RB §5.3 warning, missing fields highlighted for completion) / `parse_failed` (manual-entry CTA, "Unverified" tag) → `schedule_proposal` (editable slots) → `confirmed`.
- **Disclaimer:** every health surface carries "Best effort — informational only — no medical guarantee" (Core PRD Scenario 3); final wording is OI-1.
- **Voice stand-in:** Web Speech API on `hi-IN`/`en-IN`; RB §7.3 thresholds; TTS reads a due reminder to an `elder` on their own phone, never on a shared speaker.
- **Public-surface rule:** `is_public_surface` devices render "Health details are only shown on private devices"; the module returns `display_key health.public_surface_blocked` with an empty `data` object when the envelope flag is set (MR §6.2), and the kernel blocks earlier anyway.
- **Critical alerts:** MISSED after escalation and repeated FHIR parse failures from one HIP reach the admin as high-priority push; nothing audible on public surfaces.

## 8. Technical Considerations & Success Metrics

### Technical Approach

| Concern | Governing document | What this module does |
|---|---|---|
| Consent purposes, grant flow, reverify, ABHA adapter, watchdog | CM v1.2 §3.2, §4.2, §5, §6.2, §7 | Declares `abha`; parsed fields only; consumes `consent[].reverified_at`; renewal CTA |
| ABHA budget, FHIR parse rule, degraded mode, breaker | RB v1.2 §5, §8.2 | Never trips the breaker on a 200; per-HIP error counter; degraded copy |
| Manifest, envelope, ledger, isolation, MOD codes | MR v1.1 §4, §6, §7, §9 | §4.4 manifest; `health.idempotency_ledger`; SDK-only imports |
| Proxies, conflict rules, public surface, seed | DM v1.3 §3.4, §3.8, §8; DM v1.3 | Reads proxy data from `v_family_members` (assumption); honours `is_public_surface` |
| TTLs and tiers | FSM v2.1 §2, §3.1 | Records cached 7 days, fetched on demand; fetch at tier 1, everything else tier 0 |
| Async ABDM flow | DM §3.9 (`HEALTH_FETCH`) | Simulator is synchronous; production adapter parks the callback wait in the queue |

**Error codes.** Proposed `HEALTH_001`–`HEALTH_006`; the envelope carries the MR code in `error.code` and the HEALTH code in `error.message_key` (`health.error.HEALTH_00n`), the same convention proposed in the Finance PRD for MR v1.1. Raw codes never reach users.

| Code | Meaning | Envelope code / class | Retryable | User message (English; Hindi in UX_Error_Message_Library, P1) |
|---|---|---|---|---|
| HEALTH_001 | ABHA consent missing, expired or withdrawn for the subject | `MOD_CONSENT_MISSING` / TERMINAL | After grant or renewal | Health records for {name} need permission. Tap to connect ABHA. |
| HEALTH_002 | ABHA consent-grant budget exhausted (10/day) | `MOD_DPI_RATE_LIMITED` / RETRYABLE | After midnight IST | Health record connection limit reached for today. Existing connections continue to work. |
| HEALTH_003 | FHIR bundle partially parsed | success with `parse_quality PARTIAL` | — | Some health record details could not be read automatically. Please check the original record from {hospital}. |
| HEALTH_004 | FHIR bundle unreadable | `MOD_INTERNAL`-class TERMINAL, coded HEALTH_004 | No (manual entry offered) | We couldn't read this record. You can add the medicine manually; it will be marked Unverified. |
| HEALTH_005 | ABDM or HIP unavailable (breaker OPEN, 5xx, timeout) | `MOD_DPI_DOWN` / RETRYABLE | Yes, after `retry_after_ms` | Government health records are temporarily unavailable. Your saved reminders still work. |
| HEALTH_006 | Contradictory proxy action on a resolved or contested event | `MOD_LOCK_CONFLICT`-class TERMINAL, coded HEALTH_006 | No | This dose was already marked by {proxy} at {time}. |

**TTLs and windows.** Health records 7 days (FSM §3.1); session `expires_at` per DM §3.7 (AWAITING_APPROVAL 5 min); sweep every 5 min; escalation at `notify_timeout_mins` (seed: 60); MISSED at 2 × `notify_timeout_mins` (assumption); consent 1 year with T-7/T-3/T-1 notices (CM §7). **Rate limits.** ABHA 10 grants/day per user (Redis daily bucket, fail-open); breaker 3 → 20 min; HTTP 429 never counts. **Scheduling.** The 5-minute sweep runs in-process through the SDK scheduler (OI-3); it never dispatches through the Supervisor and only calls `notification_engine`.

### Success Metrics (The Autonomy Score)

| Metric | Definition | Phase 1 target (simulators) |
|---|---|---|
| Autonomy score | Medication events resolved by a proxy nudge alone (no admin manual action, no support) / all events | ≥ 90 % in the demo family over a 14-day simulated run |
| DPI reliability | Successful ABHA simulator fetches (any parse quality) / all fetch attempts | 100 % chaos off; ≥ 85 % chaos on, matching MC §4.6's reality |
| Family NPS | Not measurable in portfolio mode | Reviewer walkthrough of Scenarios 1–5 |
| Double-dose guard (module-specific) | Duplicate TAKEN events for one `(medication_id, due_at)` under concurrent MARK dispatches | 0 across ≥ 500 concurrent-pair tests |
| Parse resilience (module-specific) | Malformed bundles that end as PARTIAL/FAILED records with a warning, not `MOD_INTERNAL` | 100 % of `abha_fhir_malformed` responses; ≥ 95 % of well-formed bundles FULL |
| Handler latency | `metrics.handler_ms` excluding DPI wait | P95 ≤ 300 ms |

## 9. GTM & Operations

- **Portfolio framing:** this module shows the family graph doing work a personal app cannot: a subject with no device, two proxies with an admin-set conflict rule, one shared state, consent recorded for someone who cannot tap "agree", and a DPI whose data is often broken — handled without pretending. It also shows the kernel's isolation (a health bug cannot read `finance.*`) and the surface rule.
- **Launch plan:** Playwright test "Nani's 08:00 reminder" (fetch → schedule → nudge → Done → admin feed clears) plus the malformed-bundle and both-proxies tests. Demo script = Scenarios 1–5.
- **Timeline & phasing:**
  - **Slice 2 (after Finance):** the [M] items above; manifest 0.1.0; simulator fixtures for two HIPs.
  - **Phase 1.1:** `FETCH_DIAGNOSTICS`, consent-renewal UI, `elder` self-service with TTS, adherence summary for the admin.
  - **Later:** vitals and SOS (Elder Care Protocol), UHI/ONDC, OCR of paper prescriptions, parental-consent fetches for minors; real ABDM only behind HIU registration on the commercial track.

## 10. Open Issues & Q&A

### Open Issues

- **OI-1 — Medical-disclaimer wording.** Core PRD Scenario 3 gives "Best Effort — Informational Only — No Medical Guarantee". The module needs a reviewed sentence for nudges, cards and the MISSED state in all ten `preferred_language` values, and a decision on whether MISSED may say anything beyond the fact. Legal read required before the demo is shared.
- **OI-2 — Consent on behalf of a managed profile.** **Ruled 2026-09-17, closed:** the primary proxy grants with their own passkey; the record's `user_id` is the managed profile and the new column `consent_records.proxy_consent_user_id` names the proxy (Consent Manager v1.3 §2.6, Data Model v1.3 §3.12, audit action `PROXY_CONSENT_GRANTED`). The secondary proxy may grant only when the primary is unavailable.
- **OI-3 — Scheduled work and module audit codes.** MR v1.1 has no scheduling contract and the manifest schema forbids extra fields; this PRD assumes an SDK scheduler for the 5-minute sweep. DM §6 has no health action codes; proposed additions `MEDICATION_SCHEDULED`, `MEDICATION_EVENT_RESOLVED`, `HEALTH_RECORD_FETCHED` for the DM v1.3 union (register item 7).
- **OI-4 — Proxy data in kernel views.** **Closed 2026-09-17:** the kernel view `v_guardians` (DM v1.3 change 16) carries `proxy_rank`, `conflict_resolution_rule` and `notify_timeout_mins` for managed profiles, next to parents and legal guardians of minors. Add `v_guardians` to this module's `core_read_views` in PRD v0.2.
- **OI-5 — MISSED threshold.** **Ruled 2026-09-17:** the default is 2 × `notify_timeout_mins`, and it is an adjustable setting (per family now, per medication when the Elder Care Protocol is detailed). Baseline the §8 metric on the default.
- **OI-6 — Caregiver staff.** A live-in caregiver (`staff`) is the realistic person who gives Nani her tablets; Phase 1 gives staff nothing. A per-managed-profile "caregiver nudge" grant is P2 and touches RBAC (Core PRD v2.2).

### Q&A

| Asked By | Question | Answer |
|---|---|---|
| Engineering | Why is `FETCH_PRESCRIPTION` a read intent if it needs a passkey and CONSENT_REVERIFY? | Under MR, `mutating` means external side effects that need an idempotency key and two-phase commit; a fetch commits nothing externally. The passkey comes from the automation tier (Level 1, FSM §2) and the reverify from CM §5.1, which applies to every DPI access. MR v1.1 should state that reverify is keyed on `requires_consent_providers`, not on `mutating`. |
| Product | Why not let the LLM read the prescription and build the schedule? | A wrong dose time is a patient-safety defect, not a UX bug. Slot derivation is a small rule table that a proxy always confirms; the LLM only maps the user's words to an intent. This is also what makes Scenario 2's PARTIAL path testable. |
| Compliance | Why keep `health.records` rows for 7 years if the cache is 7 days? | CM §3.2 sets the retention of prescription data at 7 years (MCI guidelines); `expires_at` only says when the copy is too old to act on. Erasure follows the account-deletion sequence (CM §2.2) and the purpose's `dataEraseAt` in the ABDM artefact. |

## 11. PRD Checklist

- [x] Title & Author defined.
- [x] Executive One-Pager finalized.
- [x] Family RBAC permissions mapped (seven roles, §2).
- [x] Agentic Loop logic defined (§4.1) with manifest and schema.
- [x] DPI (India Stack) points identified (§5, simulators only).
- [x] Conflict Resolution scenarios handled (§6, DM §3.4 rules).
- [x] GTM Approach outlined (§9, portfolio framing).
- [x] Success Metrics (Autonomy Score) set (§8).
- [ ] Legal read of the disclaimer (OI-1) and CM v1.2 rule for managed-profile consent (OI-2).
