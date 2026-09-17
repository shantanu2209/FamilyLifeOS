# PRD: Secure Vault (module `secure_vault`)

> **Status:** DRAFT v0.1 — pending review · **Author:** Alfred (Lead Product Architect), drafted with Claude Code · **Last content change:** 2026-09-17
> **Scope:** Phase 1, portfolio-first build against DPI simulators. Module-level PRD that Tech_Spec_Module_Registry §1.2 defers to. The Vault is the foundation module (Master Context §5.2, `deactivatable: false`) delivered with vertical slice 1 and kept deliberately minimal: document metadata and DigiLocker retrieval, never document bytes.
> **Depends on:** MR v1.1 §3 (tiers), §4.1 (manifest; `deactivatable: false` boot rule), §5.2 (implicit activation), §6, §7, §8.1 (boot abort), §9 · CM v1.2 §2.3 (data minimisation), §2.5 (minors, age-18 migration), §3.2 (DIGILOCKER_DOCUMENT), §4.2 (grant flow), §5 (CONSENT_REVERIFY), §6.3 (DigiLocker adapter), §7 (expiry watchdog) · DM v1.3 §3.2 (roles), §3.8 (public surface), §4.2 (shadow nodes), §6 (audit taxonomy), §8 (seed), §9.3 (module table convention), plus DM v1.3 decisions (roles `minor`/`member`, `core` schema) · RB v1.2 §1 (DigiLocker is not among the five rate-limited DPIs), §9 · FSM v2.1 §2 · Core PRD v2.2 §2, §3 (Scenarios 5, 6, 9), §4.3, §6 · MC §4.4 ("sync, not duplicate"), §5.2, §7.2 · Master PRD Module 5 · PROJECT_TRACKER Decision Log and Phase 1 Build Gate.

Status: In-Progress
Author: Alfred (Lead Product Architect)
Primary Agent: VaultAgent (`modules.secure_vault.agent:VaultAgent`)
Engineering Lead: Alfred (solo founder)
Design Lead: Alfred
Approvers: Alfred, after one independent review round

## 0. Document Governance

| Version | Date | Description of Change | Author |
|---|---|---|---|
| v0.1 | 2026-09-17 | Initial draft for the Phase 1 portfolio build. | Alfred (with Claude Code) |

## 1. The One-Pager (Executive Summary)

- **Overview:** The Secure Vault is the Core-tier module that knows which verified documents a family holds — driving licence, PAN, birth certificate, vehicle RC, insurance policy — as DigiLocker references, and fetches a verified copy on request without ever storing it. It is non-deactivatable: the Registry refuses to boot without it (MR §4.1, §8.1), and Finance and Health list it in `data_dependencies` so it must be active before they are (MR §8.2). In Phase 1 it does three things well: link, list, show; plus one derived fact — the age-18 milestone that drives Core PRD Scenario 5.
- **The Problem (The Friction):** "Where is the RC?" at a checkpost; "which insurance expires this month?"; "Arjun turns 18 and still has a child's access". Documents are scattered across DigiLocker, WhatsApp forwards and a drawer, and nobody notices an expiry until it costs money. MC §4.4's principle applies: documents stay in the government vault; FamilyLifeOS syncs metadata and retrieves on demand.
- **Objectives (The Outcome):**
    1. "Show my driving licence" by voice or text renders a DigiLocker-simulator copy on a private device in ≤ 3 s after passkey approval, with nothing persisted (CM §6.3).
    2. A family-level document list with expiry badges, readable only by admin and member roles, blocked for minor, staff and every public surface.
    3. The birth-certificate milestone: when a `minor` holder reaches 18, the admin is asked — never told — whether to upgrade the role (Core PRD Scenario 5, CM §2.5).
    4. Every read and every block is written to a module access log; every link/unlink to the kernel audit log.
- **Constraints:** Portfolio mode — DigiLocker only via WireMock; no DigiLocker partner registration. Solo founder — no encrypted blob store, no key management in Phase 1 (MC §7.2 encryption applies to uploads, which are out). Zero document bytes in any FamilyLifeOS table or bucket (invariant 9 extended). No Aadhaar numbers, ever; only DigiLocker references and redacted metadata (CM §3.2 data types). Level 3 forbidden; role changes stay Level 0 in the kernel.

## 2. Personas & The Family Graph (RBAC)

### Target Personas

- **Key persona:** Ravi (`admin`) — links documents for the family, answers the milestone prompt, receives expiry escalations.
- **Key persona:** Priya (`member`) — retrieves her own and family documents; links Nani's papers as primary proxy.
- **Secondary personas:** Arjun (`minor`, holder of a birth certificate he cannot see); Ramesh (`staff`, who legitimately needs the RC but is out of scope in Phase 1, OI-5); Nani (`managed`, documents held on her behalf).

### Access Control Matrix

Baseline Core PRD §2 ("Wealth/Vault data is strictly hidden" for minors) and DM Q2 (vault for admin and member only).

| Role | Vault access | Can | Cannot | Enforcement note |
|---|---|---|---|---|
| admin | Full | `LINK_DOCUMENT`, `LIST_DOCUMENTS`, `SHOW_DOCUMENT`, `UNLINK_DOCUMENT` for any family member's documents; answer milestone prompts; receive expiry escalations | Retrieve on a public surface; store a document copy; change a role from inside the Vault (kernel Level 0 action) | Vault is implicitly active for every family (MR §5.2) |
| member | Co-owner | Link, list, show own and family documents; link on behalf of managed profiles they proxy | Unlink a document another adult linked (admin only); answer milestone prompts | `PROXY_ACTION` audit when `acting_as` is set |
| minor | None | — | Any vault intent; even the metadata of documents about themselves | Documents are linked by a parent with `parental_consent_user_id` (CM §2.5); attempt → BLOCKED + `ROLE_VIOLATION` |
| elder | None in Phase 1 | — | Any vault intent | DM Q2; an elder's own documents are linked and shown by admin/member; revisit in P2 |
| staff | None | — | Any vault intent, including the vehicle RC | Per-document sharing is P2 (OI-5); attempt → BLOCKED + admin alert |
| managed | Holder only | Have documents linked on their behalf | Anything directly | Holder `user_id` = managed profile; actor = proxy |
| passive | Holder only, admin-visible | Have documents linked by the admin for the admin's own use | Anything; is never notified | Expiry reminders for a passive holder go to the admin only |

## 3. User Scenarios / Use Cases

Seed as in DM §8. Ravi holds an active `DIGILOCKER_DOCUMENT` consent (simulator OAuth reference in `consent_handles`). Linked at setup: Ravi's driving licence (`DRIVING_LICENCE`, expires 2029-03-14), Priya's vehicle RC and insurance, Arjun's birth certificate.

### Scenario 1 — "Show my driving licence" (Master PRD Module 5 voice retrieval)

1. Ravi, Ravi Phone, at a traffic stop: *"Mera driving licence dikhao."* INTENT_ANALYSIS → `SHOW_DOCUMENT {doc_type: DRIVING_LICENCE, holder_user_id: Ravi}` at confidence 0.94.
2. PERMISSION_CHECK: admin ∈ `allowed_roles`; vault implicitly active; active DigiLocker consent handle exists (`v_active_consents`). REASONING: VaultAgent finds the `secure_vault.documents` row (`digilocker_reference_id`, expiry 2029-03-14, number redacted to `····4821`) — no external call yet.
3. APPROVAL_GATE (Level 1, NFR biometric mandate for PII display): passkey prompt "Show Ravi's driving licence (KA01 ····4821) from DigiLocker? It will be displayed on this device only and not saved." Ravi approves. CONSENT_REVERIFY reads `consent_records` live (CM §5.2; DigiLocker access token refreshed by the adapter, CM §6.3).
4. EXECUTION: DPI Gateway → DigiLocker simulator document API; the bytes stream to the PWA viewer in memory (CM §6.3 step 5), with a "Verified via DigiLocker (simulator)" badge and the expiry. Nothing is written except `secure_vault.document_access_log (action SHOW, result ALLOWED, device Ravi Phone)`. The viewer closes after 60 s or on navigation. On the Kitchen Tablet the same request is blocked before dispatch and logged as BLOCKED (Core PRD Scenario 9).

### Scenario 2 — Arjun's birth certificate and the age-18 transition (Core PRD Scenario 5)

1. Ravi links Arjun's birth certificate: `LINK_DOCUMENT {doc_type: BIRTH_CERTIFICATE, holder_user_id: Arjun}`. Arjun is a `minor`, so the `DIGILOCKER_DOCUMENT` consent record for the fetch carries `parental_consent_user_id = Ravi` (CM §2.5, passkey by Ravi). The simulator returns the document metadata including the date of birth.
2. VaultAgent stores the reference, issuer and issue date, computes `milestone_at = date_of_birth + 18 years` and stores **only** the milestone timestamp — the date of birth is not retained (data minimisation, CM §2.3; the registry's data-type list needs "date of birth (birth certificate only)" added, OI-2). Audit `PROXY_ACTION` is not used (Arjun is a minor, not a managed profile); the kernel records the consent grant.
3. Nightly at 03:00 IST (after the 01:00 purge and 02:00 shadow sweep, before the 06:00 consent watchdog) the vault sweep finds `milestone_at ≤ today` for a holder whose role is still `minor` and raises the milestone to the Supervisor (proposed audit code `VAULT_MILESTONE_DETECTED`, OI-3).
4. Ravi gets the Concierge prompt: "Arjun is now an adult. Should I upgrade his access to the Wealth pillar?" Ravi confirms with his passkey → the kernel's Family Management performs `ROLE_CHANGED` `minor → member` (Level 0), and CM §2.5 migrates the parent-granted consents to Arjun's own records with a notification to Arjun listing what exists and how to revoke. Declining leaves everything unchanged; the prompt returns in 30 days, never automatically executed.

### Scenario 3 — Ramesh needs the RC at a checkpost

Ramesh, on his own phone: *"Gaadi ka RC dikhao."* PERMISSION_CHECK fails (staff ∉ `allowed_roles`); BLOCKED, `MOD_PERMISSION_DENIED`, `ROLE_VIOLATION` in the audit log, and an access-log row (`result BLOCKED`). Ravi receives a high-severity alert (Core PRD §6) — which in this case is a legitimate request the product cannot serve yet: Ravi shows the RC from his own phone. Per-document sharing to staff is OI-5 (P2), not a Phase 1 workaround.

### Scenario 4 — Expired DigiLocker consent and a simulator outage

Priya asks for her insurance policy a year after linking. CONSENT_REVERIFY finds her `DIGILOCKER_DOCUMENT` record expired (the watchdog notified her at T-7/T-3/T-1 days, CM §7.2). VAULT_001 routes her to renewal (CM §7.3: new record, new OAuth reference; passkey) and then resumes. Later the DigiLocker simulator returns three consecutive 500s; there is no DigiLocker breaker in RB §8.2, so the module applies the AA defaults as a self-imposed policy (assumption, OI-4): `SHOW_DOCUMENT` returns VAULT_003 with "DigiLocker is temporarily unavailable; your document list is still here", while `LIST_DOCUMENTS` (local metadata) keeps working.

## 4. Functional Requirements (The "Agentic" Loop)

### 4.1 The loop for link, show and milestone

- **Trigger:** a request on a private device (`LINK_DOCUMENT`, `LIST_DOCUMENTS`, `SHOW_DOCUMENT`, `UNLINK_DOCUMENT`); the nightly 03:00 IST sweep (expiry within 30 days, age-18 milestones) registered through the SDK scheduler (MR v1.1 has no scheduling contract, OI-3); the kernel's consent watchdog for `DIGILOCKER_DOCUMENT` renewals (CM §7).
- **Information gathering:** actor role and `acting_as` from the envelope; holder role from `v_family_members`; DigiLocker consent reference from `v_active_consents`; device surface from `v_device_surfaces`; local `secure_vault.documents`; the DigiLocker simulator's document list/metadata endpoint (link) or document endpoint (show) through the DPI Gateway, with the OAuth token handled by the Consent Manager adapter (CM §6.3).
- **Analysis logic (deterministic):** requester may act on a document if requester is `admin` or `member` of the same family and the holder is any family member (co-owner model, assumption OI-6); expiry badge = red ≤ 7 days, amber ≤ 30 days; `milestone_at ≤ today AND holder.role = 'minor'` → milestone; a DigiLocker response that says the document is revoked or expired overrides local metadata (DPI truth wins). No inference on document content beyond the metadata fields the simulator returns.
- **Execution / fulfilment:** `LINK_DOCUMENT` writes one `secure_vault.documents` row inside a transaction with its idempotency ledger row and the audit write protocol of DM v1.3 §3.18 (`fn_lock_audit_tail` then `fn_append_audit`; `VAULT_DOCUMENT_LINKED`, proposed code — OI-3); `SHOW_DOCUMENT` streams bytes to the client in memory and writes only an access-log row; `UNLINK_DOCUMENT` soft-deletes; the sweep sends expiry reminders and milestone prompts through `notification_engine` to private devices. The Vault never changes a role and never calls Finance or Health (MR §3.2).

### 4.2 Features In (Prioritised)

- **`LINK_DOCUMENT` [M]:** DigiLocker-simulator reference plus redacted metadata for a family member; parental consent path for minors; idempotent on `(family_id, digilocker_reference_id)`.
- **`SHOW_DOCUMENT` [M]:** Scenario 1; passkey, CONSENT_REVERIFY, in-memory rendering, access log, 60 s auto-close.
- **`LIST_DOCUMENTS` [M]:** the family's document metadata with expiry badges; no DPI call.
- **Access log [M]:** every SHOW / LIST / LINK / UNLINK / BLOCKED with actor, device and result (`secure_vault.document_access_log`).
- **Age-18 milestone [M]:** derived `milestone_at` on birth certificates, nightly sweep, admin prompt; the role change stays in the kernel.
- **Boot and activation duties [M]:** valid manifest with `deactivatable: false`, `health_check` within 2 s, implicit activation for every family (MR §5.2, §8.1).
- **Expiry reminders:** 30/7-day notices to the holder (adult) and the admin (OI-1 decides the exact recipients and lead times).
- **`UNLINK_DOCUMENT`:** admin-only soft delete with audit; the DigiLocker document itself is untouched.

### 4.3 Features Out

- **Encrypted blob storage, uploads, zero-knowledge keys (MC §7.2):** "sync, not duplicate" (MC §4.4) means no bytes in Phase 1; key management is a Security_Threat_Model.md topic.
- **OCR of physical documents (Core PRD Scenario 6):** `ocr` service module, P2; the tax-notice flow also needs Finance's `PAYMENT_STATUS`.
- **Aadhaar retrieval or e-KYC:** the number is never stored (invariant 9); staff e-KYC (Core PRD §4.3) is the kernel's Identity & Auth Manager, not the Vault.
- **Per-document sharing to staff or outsiders, DigiYatra credentials (Master PRD Module 4):** P2, needs a sharing grant model (OI-5).
- **Consent-handle storage for Finance/Health:** MC §5.2 says the Vault stores AA/ABHA tokens; under DM §3.5 and CM §1.4 handles live in the kernel's `consent_handles`. The dependency edge survives only as activation order (MR §4.1 `data_dependencies`); MC v2.1 should say so (see report).
- **Document expiry auto-renewal, marksheets/DIKSHA (Master PRD Module 4):** later phases.

### 4.4 Module manifest (Module Registry contract)

Valid against MR §4.1. `SHOW_DOCUMENT` is a read intent that must pass CONSENT_REVERIFY (CM §5.1) — the same MR v1.1 assumption as in the Health PRD (reverify keyed on `requires_consent_providers`).

```json
{
  "manifest_version": 1,
  "module_id": "secure_vault",
  "version": "0.1.0",
  "tier": "core",
  "display_name": { "en": "Secure Vault", "hi": "सुरक्षित तिजोरी" },
  "description": "Family document metadata synced from DigiLocker, on-demand verified retrieval without storage, expiry and age-18 milestones. Non-deactivatable foundation module.",
  "deactivatable": false,
  "entrypoint": "modules.secure_vault.agent:VaultAgent",
  "health_check": "health",
  "intents": [
    {
      "intent_code": "LINK_DOCUMENT",
      "description": "Link a DigiLocker document to a family member as metadata and reference; never stores bytes.",
      "automation_tier_ceiling": 1,
      "allowed_roles": ["admin", "member"],
      "mutating": true,
      "requires_consent_providers": ["digilocker"],
      "entities_schema": {
        "type": "object",
        "additionalProperties": false,
        "required": ["doc_type", "holder_user_id"],
        "properties": {
          "doc_type": { "enum": ["DRIVING_LICENCE", "PAN", "BIRTH_CERTIFICATE", "VEHICLE_RC", "INSURANCE_POLICY"] },
          "holder_user_id": { "type": "string", "format": "uuid" },
          "digilocker_reference_id": { "type": ["string", "null"], "maxLength": 255 }
        }
      }
    },
    {
      "intent_code": "SHOW_DOCUMENT",
      "description": "Retrieve a linked document from DigiLocker and render it in memory on a private device.",
      "automation_tier_ceiling": 1,
      "allowed_roles": ["admin", "member"],
      "mutating": false,
      "requires_consent_providers": ["digilocker"],
      "entities_schema": {
        "type": "object",
        "additionalProperties": false,
        "required": ["doc_type"],
        "properties": {
          "doc_type": { "enum": ["DRIVING_LICENCE", "PAN", "BIRTH_CERTIFICATE", "VEHICLE_RC", "INSURANCE_POLICY"] },
          "holder_user_id": { "type": ["string", "null"], "format": "uuid" }
        }
      }
    },
    {
      "intent_code": "LIST_DOCUMENTS",
      "description": "List the family's linked documents with expiry badges; no DPI call.",
      "automation_tier_ceiling": 0,
      "allowed_roles": ["admin", "member"],
      "mutating": false,
      "requires_consent_providers": [],
      "entities_schema": {
        "type": "object",
        "additionalProperties": false,
        "properties": { "holder_user_id": { "type": ["string", "null"], "format": "uuid" } }
      }
    },
    {
      "intent_code": "UNLINK_DOCUMENT",
      "description": "Soft-delete a linked document's metadata; the DigiLocker document is untouched.",
      "automation_tier_ceiling": 0,
      "allowed_roles": ["admin"],
      "mutating": true,
      "requires_consent_providers": [],
      "entities_schema": {
        "type": "object",
        "additionalProperties": false,
        "required": ["document_id"],
        "properties": { "document_id": { "type": "string", "format": "uuid" } }
      }
    }
  ],
  "data_scopes": {
    "owns_schema": "secure_vault",
    "core_read_views": ["v_family_members", "v_module_permissions", "v_active_consents", "v_device_surfaces"]
  },
  "dpi_providers": ["digilocker"],
  "service_dependencies": ["notification_engine"],
  "data_dependencies": [],
  "resource_budgets": { "p95_handler_ms": 200, "hard_timeout_ms": 15000 }
}
```

### 4.5 Owned schema (`secure_vault`)

DM §9.3 conventions; role `role_module_secure_vault` (MR §7.2). `user_id` is the **holder**, `created_by_user_id` the actor. No column can hold bytes: a CI test asserts that no `BYTEA`, `TEXT` over 4 KB or object-store write exists in this schema (§8 metric). Three tables:

| Table | Purpose | Notes |
|---|---|---|
| `secure_vault.documents` | Metadata and DigiLocker reference per linked document | Redacted number only; `milestone_at` replaces the date of birth |
| `secure_vault.document_access_log` | Every read, list, link, unlink and block | Module-level; the kernel audit log gets only writes |
| `secure_vault.idempotency_ledger` | MR §6.4 ledger for `LINK_DOCUMENT` / `UNLINK_DOCUMENT` | Same shape as the Finance ledger |

```sql
CREATE SCHEMA secure_vault;

CREATE TABLE secure_vault.documents (
  document_id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  family_id                UUID         NOT NULL REFERENCES core.families(family_id) ON DELETE CASCADE,
  user_id                  UUID         NOT NULL REFERENCES core.users(user_id) ON DELETE CASCADE,   -- holder
  created_by_user_id       UUID         NOT NULL REFERENCES core.users(user_id),                      -- actor
  doc_type                 VARCHAR(20)  NOT NULL CHECK (doc_type IN ('DRIVING_LICENCE','PAN','BIRTH_CERTIFICATE','VEHICLE_RC','INSURANCE_POLICY')),
  digilocker_reference_id  VARCHAR(255) NOT NULL,             -- opaque document URI/reference from the simulator; never a token
  consent_record_ref       UUID         NOT NULL,             -- consent_records.record_id, reference only
  issuer_name              VARCHAR(120),
  doc_number_redacted      VARCHAR(12),                       -- last four characters only, e.g. '····4821'
  issue_date               DATE,
  expiry_date              DATE,                              -- NULL for documents that do not expire
  milestone_at             DATE,                              -- birth certificates: date_of_birth + 18 years; DOB itself not stored
  verified                 BOOLEAN      NOT NULL DEFAULT TRUE, -- DigiLocker-issued; uploads (P2) would be FALSE
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), deleted_at TIMESTAMPTZ,
  UNIQUE (family_id, digilocker_reference_id)
);
CREATE INDEX idx_vault_docs_family_created ON secure_vault.documents(family_id, created_at DESC);
CREATE INDEX idx_vault_docs_expiry    ON secure_vault.documents(expiry_date)  WHERE deleted_at IS NULL AND expiry_date IS NOT NULL;
CREATE INDEX idx_vault_docs_milestone ON secure_vault.documents(milestone_at) WHERE deleted_at IS NULL AND milestone_at IS NOT NULL;

CREATE TABLE secure_vault.document_access_log (
  access_id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  family_id          UUID        NOT NULL REFERENCES core.families(family_id) ON DELETE CASCADE,
  user_id            UUID        NOT NULL REFERENCES core.users(user_id) ON DELETE CASCADE,   -- actor
  document_id        UUID        REFERENCES secure_vault.documents(document_id),               -- NULL for LIST and blocked lookups
  action             VARCHAR(10) NOT NULL CHECK (action IN ('SHOW','LIST','LINK','UNLINK','MILESTONE')),
  result             VARCHAR(10) NOT NULL CHECK (result IN ('ALLOWED','BLOCKED','FAILED')),
  block_reason       VARCHAR(20),                             -- 'ROLE' | 'PUBLIC_SURFACE' | 'CONSENT' | 'DPI'
  session_id         UUID, device_id UUID, is_public_surface BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), deleted_at TIMESTAMPTZ
);
CREATE INDEX idx_vault_access_family_created ON secure_vault.document_access_log(family_id, created_at DESC);

CREATE TABLE secure_vault.idempotency_ledger (                 -- MR §6.4, same shape as finance
  idempotency_key UUID PRIMARY KEY,
  family_id UUID NOT NULL REFERENCES core.families(family_id) ON DELETE CASCADE,
  user_id   UUID NOT NULL REFERENCES core.users(user_id) ON DELETE CASCADE,
  intent_code VARCHAR(40) NOT NULL,
  status VARCHAR(10) NOT NULL CHECK (status IN ('pending','final')),
  response_envelope JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), deleted_at TIMESTAMPTZ
);
CREATE INDEX idx_vault_ledger_family_created ON secure_vault.idempotency_ledger(family_id, created_at DESC);
```

## 5. India Stack (DPI) Touchpoints

Phase 1 touches DigiLocker only, and only through the WireMock simulator. No partner registration exists or is planned in portfolio mode.

- **Identity:** none. Aadhaar is never requested, stored or displayed. DigiLocker's own login is simulated as an OAuth authorisation-code exchange (CM §6.3); FamilyLifeOS holds a token *reference* in `core.consent_handles`, never the token.
- **Data:** purpose code `DIGILOCKER_DOCUMENT` (CM §3.2), one `consent_records` row per user who links documents, with `parental_consent_user_id` when the holder is a `minor`. Data types: document type, redacted number, issue and expiry dates. The birth-certificate date of birth is read once to derive `milestone_at` and discarded (OI-2 asks for the registry's data-type list to say so).
- **Payments / Commerce:** none.
- **Simulator stubs needed:** `digilocker_oauth_token.json` (authorisation-code exchange and refresh), `digilocker_issued_documents.json` (list with metadata for the Sharma seed documents), `digilocker_document_fetch.json` (bytes for the five doc types, with a visible "SIMULATOR" watermark), `digilocker_document_revoked.json`, and a failure stub returning HTTP 500 for the outage scenario. RB §9 does not define DigiLocker stubs; they are to be defined in Tech_Spec_Simulator_Architecture (P1).
- **Rate limits:** DigiLocker is not one of the five budgeted DPIs (RB §1). The module self-imposes 30 document fetches per user per day as an abuse guard, tracked under `{env}:secure_vault:fetch:{user_id}:{YYYY-MM-DD}` (MR §5.3 key namespace).

## 6. Conflict Resolution Matrix

| Conflict scenario | Resolution logic |
|---|---|
| Two adults link the same DigiLocker document | `UNIQUE (family_id, digilocker_reference_id)` makes the second insert a no-op; the response returns the existing row and says who linked it. |
| Member wants to unlink a document the admin linked | Blocked: `UNLINK_DOCUMENT` is admin-only. The member is told to ask the admin; no alert is raised. |
| Proxies disagree about Nani's documents (Priya links, Ravi unlinks) | Follows the managed profile's `conflict_resolution_rule` (DM §3.4): `hierarchy` → the primary proxy's action stands; `notify_block` → both are paused and the admin is alerted. |
| Request arrives on a public surface | Blocked before dispatch regardless of role (DM §3.8, MR §6.2); logged as BLOCKED / `PUBLIC_SURFACE`. Metadata lists are blocked too, not only document display. |
| DigiLocker says a linked document is revoked or expired, local metadata says valid | DigiLocker wins (DPI truth). The row is updated, the holder and admin are notified, and `SHOW_DOCUMENT` returns VAULT_005. |
| Admin declines the age-18 prompt | Nothing changes. The prompt returns in 30 days. The Vault never escalates to anyone else and never changes the role itself. |
| Restricted role attempts any vault intent | BLOCKED at PERMISSION_CHECK, `ROLE_VIOLATION` audit entry, high-severity admin alert (Core PRD §6). |

## 7. Design & Generative UI

States, not screens, in the PWA.

- **Voice / text flow:** text-first; the browser speech stand-in arrives in Roadmap Phase 4. Utterances map to four intents; an ambiguous "show my papers" goes to AWAITING_CLARIFICATION with the holder's document list as choices.
- **Document list state:** cards grouped by holder with doc type, redacted number, issuer, and an expiry badge (red ≤ 7 days, amber ≤ 30 days). Never rendered on a public surface; the public-surface state shows "Documents are available on your own device."
- **Approval state (passkey):** "Show Ravi's driving licence (KA01 ····4821) from DigiLocker? It will be displayed on this device only and not saved." Approve / Cancel; the WebAuthn ceremony is the approval. Window: 5 minutes (DM §3.7 AWAITING_APPROVAL expiry).
- **Viewer state:** in-memory render with a "Verified via DigiLocker (simulator)" badge, expiry date, a 60-second countdown, no download or share control, and screenshot discouragement text. Closing or navigating away drops the bytes.
- **Milestone prompt:** a Concierge card for the admin only: "Arjun is now an adult. Should I upgrade his access to the Wealth pillar?" with Yes (passkey) / Not now.
- **Critical alerts:** `ROLE_VIOLATION` alerts go to the admin's private device only; expiry reminders use normal priority.

## 8. Technical Considerations & Success Metrics

### Technical approach

| Concern | Governing spec |
|---|---|
| Manifest, envelope, isolation, boot rules for a non-deactivatable module | MR v1.1 §4, §6, §7, §8.1 |
| Consent grant, renewal, CONSENT_REVERIFY, DigiLocker adapter | CM v1.2 §4.2, §5, §6.3, §7 |
| Roles, public surface, kernel views, audit write protocol | DM v1.3 §3.2, §3.8, §3.17, §3.18 |
| Automation tiers (LINK and SHOW are Level 1; LIST and UNLINK Level 0) | FSM v2.1 §2 |
| TTL | Document metadata: indefinite until unlink or DigiLocker revocation; document bytes: never cached (stricter than FSM §3.1) |

### Error codes (proposed)

| Code | Meaning | Retryable | User message |
|---|---|---|---|
| VAULT_001 | DigiLocker consent missing or expired | After renewal | "Your DigiLocker connection needs renewal. Tap to reconnect." |
| VAULT_002 | Requested document is not linked | No | "I don't have that document linked yet. Would you like to link it from DigiLocker?" |
| VAULT_003 | DigiLocker unavailable (simulator 5xx / timeout) | Yes | "DigiLocker is temporarily unavailable. Your document list is still here." |
| VAULT_004 | Blocked by role or public surface | No | "Documents can only be shown to an adult family member on a private device." |
| VAULT_005 | DigiLocker reports the document revoked or expired | No | "DigiLocker says this document is no longer valid. Please check with the issuer." |

Mapping to the module envelope: VAULT_001 → `MOD_CONSENT_MISSING`, VAULT_003 → `MOD_DPI_DOWN`, VAULT_004 → `MOD_PERMISSION_DENIED`; VAULT_002 and VAULT_005 are `failure` with class TERMINAL (MR §9). Hindi strings belong in UX_Error_Message_Library.md (P1).

### Success metrics

- **Completion rate:** ≥ 90 % of `SHOW_DOCUMENT` requests by permitted roles end in a rendered document without correction.
- **DPI reliability:** ≥ 99 % against the simulator in normal mode; degraded-mode message shown in 100 % of injected outages.
- **Family NPS:** collected with the demo testers only.
- **Zero-bytes invariant:** the CI check of §4.5 passes on every PR (0 violations).
- **Block correctness:** 100 % of minor, staff and public-surface attempts in the test suite are blocked and logged.

## 9. GTM & Operations

- **What this module demonstrates (portfolio mode):** "sync, not duplicate" privacy design; consent-gated reads with CONSENT_REVERIFY; the public-surface rule; a Level 0 human decision (age-18 upgrade) that an agent proposes and never executes.
- **Launch plan:** delivered as the foundation with vertical slice 1 (Finance) because Finance and Health declare it in `data_dependencies`; its own demo moment is Scenario 1 in the second half of the demo script (docs/strategy/GTM_Plan.md).
- **Phasing:** Phase 2 of the Roadmap: manifest, schema, `LIST_DOCUMENTS`, boot duties. Phase 3: `LINK_DOCUMENT`, `SHOW_DOCUMENT`, access log, milestone sweep, expiry reminders.

## 10. Open Issues & Q&A

### Open issues

| ID | Issue | Priority | Resolution path |
|---|---|---|---|
| OI-1 | Who receives expiry reminders, and when? Draft: holder (if adult) and admin at 30 and 7 days; passive and managed holders → admin and primary proxy only. | MEDIUM | Founder decision at PRD review. |
| OI-2 | The purpose registry's data types for `DIGILOCKER_DOCUMENT` do not mention date of birth, which the milestone derivation reads once. | MEDIUM | CM v1.3 registry wording, or drop the derivation and ask the admin for the 18th-birthday date. |
| OI-3 | The Module Registry has no scheduling contract for module-owned nightly sweeps, and the audit codes `VAULT_DOCUMENT_LINKED`, `VAULT_DOCUMENT_UNLINKED`, `VAULT_MILESTONE_DETECTED` are not in DM v1.3 §6. | MEDIUM | MR review round 2 (scheduler hook in the SDK); DM v1.3 taxonomy addition before freeze. |
| OI-4 | No DigiLocker circuit-breaker values exist in RB §8.2; this PRD borrows the AA defaults (3 failures → 30 min). | LOW | RB v1.3 when a second DigiLocker consumer appears. |
| OI-5 | Staff need specific documents (the RC for the driver). Needs a per-document, time-boxed sharing grant. | LOW (P2) | Separate PRD section in Phase 2; do not solve with a role exception. |
| OI-6 | Co-owner model: any admin or member may show any family member's document. Should an adult's own documents be private from the other adult by default? | MEDIUM | Founder decision at PRD review; affects `SHOW_DOCUMENT` analysis logic only. |

### Q&A

| Asked by | Question | Answer |
|---|---|---|
| Engineering | Master Context §5.2 says the Vault stores AA and ABHA consent tokens. Why doesn't it? | The frozen specs moved that responsibility to the kernel: `core.consent_handles` holds opaque references (DM §3.5, CM §1.4) and modules never see token material (MR §6.1). The Vault → Finance/Health edge survives as activation order only. |
| Engineering | Why is `SHOW_DOCUMENT` Level 1 with a passkey if it is a read? | It displays PII on a screen in a public place (the traffic-stop case). NFR §2.2's mandate covers PII export, and the prompt doubles as the human confirmation that the device and moment are right. |
| Product | Why not store the document so it works offline at a checkpost with no network? | Storing bytes turns the Vault into a high-value target and requires key management the solo-founder constraint rules out in Phase 1. Offline display is a P2 question for Security_Threat_Model.md. |

## 11. PRD Checklist

- [x] Title & Author defined.
- [x] Executive One-Pager finalized.
- [x] Family RBAC permissions mapped.
- [x] Agentic Loop logic defined.
- [x] DPI (India Stack) points identified (DigiLocker simulator only).
- [x] Conflict Resolution scenarios handled.
- [x] GTM Approach outlined (portfolio mode).
- [x] Success Metrics set.
- [ ] Independent review round completed and OI-1, OI-2, OI-6 decided by the founder.
