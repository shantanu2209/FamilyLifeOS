# PRD: Secure Vault (module `secure_vault`)

> **Status:** DRAFT v0.2 — founder rulings of 2026-09-17 applied; independent review (Codex, WP-15) pending · **Author:** Shantanu Chaudhary (Lead Product Architect), drafted with Claude Code · **Last content change:** 2026-09-17
> **Scope:** Phase 1, portfolio-first build against DPI simulators. Module-level PRD that Tech_Spec_Module_Registry §1.2 defers to. The Vault is the foundation module (Master Context §5.2, `deactivatable: false`) delivered with vertical slice 1 and kept deliberately minimal: document metadata and DigiLocker retrieval, never document bytes.
> **Depends on:** MR v1.1 §3 (tiers), §4.1 (manifest; `deactivatable: false` boot rule), §5.2 (implicit activation), §6, §7, §8.1 (boot abort), §9 · CM v1.3 §2.3 (data minimisation), §2.5 (minors, age-18 migration), §3.2 (DIGILOCKER_DOCUMENT), §4.2 (grant flow), §5 (CONSENT_REVERIFY), §6.3 (DigiLocker adapter), §7 (expiry watchdog) · DM v1.3 §3.2 (roles), §3.8 (public surface), §4.2 (shadow nodes), §6 (audit taxonomy), §8 (seed), §9.3 (module table convention), plus DM v1.3 decisions (roles `minor`/`member`, `core` schema) · RB v1.2 §1 (DigiLocker is not among the five rate-limited DPIs), §9 · FSM v2.1 §2 · Core PRD v2.2 §2, §3 (Scenarios 5, 6, 9), §4.3, §6 · MC §4.4 ("sync, not duplicate"), §5.2, §7.2 · Master PRD Module 5 · PROJECT_TRACKER Decision Log and Phase 1 Build Gate · Tech_Spec_Simulator_Architecture v0.1 §5.4, §6.4 (DigiLocker simulator).

Status: In-Progress
Author: Shantanu Chaudhary (Lead Product Architect)
Primary Agent: VaultAgent (`modules.secure_vault.agent:VaultAgent`)
Engineering Lead: Shantanu Chaudhary (solo founder)
Design Lead: Shantanu Chaudhary
Approvers: Shantanu Chaudhary, after one independent review round

## 0. Document Governance

| Version | Date | Description of Change | Author |
|---|---|---|---|
| v0.1 | 2026-09-17 | Initial draft for the Phase 1 portfolio build. | Shantanu Chaudhary (with Claude Code) |
| v0.2 | 2026-09-17 | Founder rulings applied. (1) Visibility model replaces the co-owner assumption: document classes, a `visibility` attribute with defaults by class and holder, new intent `SET_DOCUMENT_VISIBILITY`, error VAULT_006, no admin override of another adult's personal documents (OI-6 closed; break-glass parked as OI-7). (2) Expiry reminders: default recipients and lead times, adjustable per family and per document (OI-1 closed). (3) New §4.6 "Settings and defaults": what a family can adjust, how far, and what is never a setting (Decision Log: defaults, not constants). (4) Who links whose documents tightened: adults link their own, guardians link dependents'. (5) `UNLINK_DOCUMENT` opened to the holder. (6) DigiLocker stub names aligned with the simulator spec. (7) Second founder ruling the same day: a minor's personal documents are seen by the minor's **parents and any marked legal guardian**, not by every adult and not by admins as such; this needs the new kernel view `v_guardians` and the `guardian` relationship type (Data Model v1.3 change 16, in the same PR). | Shantanu Chaudhary (with Claude Code) |

## 1. The One-Pager (Executive Summary)

- **Overview:** The Secure Vault is the Core-tier module that knows which verified documents a family holds — driving licence, PAN, birth certificate, vehicle RC, insurance policy — as DigiLocker references, and fetches a verified copy on request without ever storing it. It is non-deactivatable: the Registry refuses to boot without it (MR §4.1, §8.1), and Finance and Health list it in `data_dependencies` so it must be active before they are (MR §8.2). In Phase 1 it does three things well: link, list, show; plus one derived fact — the age-18 milestone that drives Core PRD Scenario 5.
- **The Problem (The Friction):** "Where is the RC?" at a checkpost; "which insurance expires this month?"; "Arjun turns 18 and still has a child's access". Documents are scattered across DigiLocker, WhatsApp forwards and a drawer, and nobody notices an expiry until it costs money. MC §4.4's principle applies: documents stay in the government vault; FamilyLifeOS syncs metadata and retrieves on demand.
- **Objectives (The Outcome):**
    1. "Show my driving licence" by voice or text renders a DigiLocker-simulator copy on a private device in ≤ 3 s after passkey approval, with nothing persisted (CM §6.3).
    2. A family-level document list with expiry badges, readable only by admin and member roles, blocked for minor, staff and every public surface, and filtered by each document's visibility: family documents are shared between the adults, personal identity documents belong to their holder unless the holder shares them (§4.6).
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
| admin | Full, within visibility | Link, list, show and unlink their own documents, family-class documents, and the documents of dependents they are a guardian viewer of (§4.6: elder, managed and passive holders always; a minor only as parent or legal guardian, or when the minor has neither in the family); change visibility of those dependents' documents; change the family's reminder settings; answer milestone prompts; receive expiry reminders | See, list, show or unlink another adult's `holder_only` document (no override in Phase 1, OI-7); retrieve on a public surface; store a document copy; change a role from inside the Vault (kernel Level 0 action) | Vault is implicitly active for every family (MR §5.2); visibility is enforced in the module's analysis step, after the kernel's role check |
| member | Own documents and shared ones | Link, list, show and unlink their own documents; list and show family-class documents and anything another adult has shared; link and see the documents of minors they are a parent or legal guardian of and of managed profiles they are **primary proxy** for; change visibility of their own documents | See another adult's `holder_only` document; see a dependent's `guardians` document unless they are the minor's parent or legal guardian, or the managed profile's primary proxy; unlink a document they do not hold; answer milestone prompts; change family settings | `PROXY_ACTION` audit when `acting_as` is set |
| minor | None | — | Any vault intent; even the metadata of documents about themselves | Documents are linked by a parent with `parental_consent_user_id` (CM §2.5); attempt → BLOCKED + `ROLE_VIOLATION` |
| elder | None in Phase 1 | — | Any vault intent | DM Q2; an elder's documents are linked by an admin and default to `guardians` visibility; revisit in P2 |
| staff | None | — | Any vault intent, including the vehicle RC | Per-document sharing is P2 (OI-5); attempt → BLOCKED + admin alert |
| managed | Holder only | Have documents linked on their behalf | Anything directly | Holder `user_id` = managed profile; actor = proxy |
| passive | Holder only, admin-visible | Have documents linked by the admin for the admin's own use | Anything; is never notified | Expiry reminders for a passive holder go to the admins only |

## 3. User Scenarios / Use Cases

Seed as in DM §8. Ravi and Priya each hold an active `DIGILOCKER_DOCUMENT` consent (simulator OAuth references in `consent_handles`); an adult's documents come from that adult's own DigiLocker account, a dependent's from a guardian's. Linked at setup: by Ravi, his driving licence (`DRIVING_LICENCE`, personal, `holder_only`, expires 2029-03-14) and Arjun's birth certificate (personal, holder is a minor, `guardians`: visible to his parents Ravi and Priya through `v_guardians`); by Priya, the vehicle RC and the insurance policy (family class, `family_adults`) and her PAN (personal, `holder_only`).

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

### Scenario 5 — Priya's PAN is hers (visibility, founder ruling 2026-09-17)

1. Ravi, on his own phone: *"Priya ka PAN dikhao."* The kernel's PERMISSION_CHECK passes (admin ∈ `allowed_roles`). In REASONING the VaultAgent applies the visibility rule (§4.6): the document is `personal`, its holder is an adult, its visibility is `holder_only`, and Ravi is not the holder. Result: VAULT_006, "I can't show that. Personal documents are visible only to their holder unless they choose to share them." The message is the same whether or not such a document is linked, so it does not leak existence. Access log: `SHOW`, `BLOCKED`, reason `VISIBILITY`. No `ROLE_VIOLATION`, no alert: asking is not an offence.
2. Tax season. Priya, on her phone: *"PAN ko family ke saath share karo."* → `SET_DOCUMENT_VISIBILITY {document_id, visibility: family_adults}`. Widening is Level 1: passkey prompt "Let Ravi see your PAN (····2K7F) in the family vault? You can undo this at any time." Audit `VAULT_VISIBILITY_CHANGED` (proposed code, OI-3), details `{document_id, from, to}`.
3. Ravi repeats his request; it now follows Scenario 1 with his own passkey. In April Priya narrows it back to `holder_only`; narrowing is Level 0, no passkey, same audit code.
4. `LIST_DOCUMENTS` for Ravi never showed the PAN while it was `holder_only`: not as a card, not as a count.

### Scenario 6 — The licence is about to expire (reminder defaults)

The 03:00 sweep finds Ravi's driving licence 30 days from expiry. Defaults (§4.6): the holder is reminded at 30 and 7 days; the admins get a copy. Ravi is both. Had it been Priya's `holder_only` licence, Ravi's copy would read "One of Priya's personal documents expires on 14 March" with no type and no number, because a reminder must not reveal more than the list would. Priya can mute admin copies for that one document; Ravi can change the family's lead times to 60/30/7. For Nani's (managed) insurance card the reminder goes to the admins and to Priya as primary proxy, never to Nani. A reminder about Arjun's passport, were one linked, would go to Ravi and Priya as his parents, whoever the admins are.

## 4. Functional Requirements (The "Agentic" Loop)

### 4.1 The loop for link, show and milestone

- **Trigger:** a request on a private device (`LINK_DOCUMENT`, `LIST_DOCUMENTS`, `SHOW_DOCUMENT`, `SET_DOCUMENT_VISIBILITY`, `UNLINK_DOCUMENT`); the nightly 03:00 IST sweep (expiry within 30 days, age-18 milestones) registered through the SDK scheduler (MR v1.1 has no scheduling contract, OI-3); the kernel's consent watchdog for `DIGILOCKER_DOCUMENT` renewals (CM §7).
- **Information gathering:** actor role and `acting_as` from the envelope; holder role from `v_family_members`; parents, legal guardians and proxies of a dependent holder from `v_guardians`; DigiLocker consent reference from `v_active_consents`; device surface from `v_device_surfaces`; local `secure_vault.documents`; the DigiLocker simulator's document list/metadata endpoint (link) or document endpoint (show) through the DPI Gateway, with the OAuth token handled by the Consent Manager adapter (CM §6.3).
- **Analysis logic (deterministic):** the requester may see or act on a document only if the visibility rule of §4.6 names them a viewer (the kernel has already checked that they are `admin` or `member`); every list, count, reminder and error message is filtered by the same rule, so nothing reveals a document the requester cannot see; expiry badge = red ≤ 7 days, amber ≤ 30 days; `milestone_at ≤ today AND holder.role = 'minor'` → milestone; a DigiLocker response that says the document is revoked or expired overrides local metadata (DPI truth wins). No inference on document content beyond the metadata fields the simulator returns.
- **Execution / fulfilment:** `LINK_DOCUMENT` writes one `secure_vault.documents` row inside a transaction with its idempotency ledger row and the audit write protocol of DM v1.3 §3.18 (`fn_lock_audit_tail` then `fn_append_audit`; `VAULT_DOCUMENT_LINKED`, proposed code — OI-3); `SHOW_DOCUMENT` streams bytes to the client in memory and writes only an access-log row; `SET_DOCUMENT_VISIBILITY` updates one row with the audit write protocol (`VAULT_VISIBILITY_CHANGED`, proposed — OI-3); `UNLINK_DOCUMENT` soft-deletes; the sweep sends expiry reminders (recipients and lead times from `secure_vault.family_settings`, §4.6) and milestone prompts through `notification_engine` to private devices. The Vault never changes a role and never calls Finance or Health (MR §3.2).

### 4.2 Features In (Prioritised)

- **`LINK_DOCUMENT` [M]:** DigiLocker-simulator reference plus redacted metadata. An adult links their **own** documents from their own DigiLocker consent; a dependent's documents are linked by one of that dependent's guardian viewers (§4.6): a parent or legal guardian for a minor (parental consent path, CM §2.5), the primary proxy or an admin for a managed profile (proxy consent, CM v1.3 §2.6), an admin for elder and passive holders. Nobody links a document into another adult's name. Class and default visibility are set at link time (§4.6). Idempotent on `(family_id, digilocker_reference_id)`.
- **`SHOW_DOCUMENT` [M]:** Scenario 1; passkey, CONSENT_REVERIFY, in-memory rendering, access log, 60 s auto-close.
- **`LIST_DOCUMENTS` [M]:** the document metadata the requester is a viewer of, with expiry badges; no DPI call.
- **Visibility model [M]:** document class, `visibility` attribute, defaults and `SET_DOCUMENT_VISIBILITY` as in §4.6; Scenario 5.
- **Access log [M]:** every SHOW / LIST / LINK / UNLINK / BLOCKED with actor, device and result (`secure_vault.document_access_log`).
- **Age-18 milestone [M]:** derived `milestone_at` on birth certificates, nightly sweep, admin prompt; the role change stays in the kernel.
- **Boot and activation duties [M]:** valid manifest with `deactivatable: false`, `health_check` within 2 s, implicit activation for every family (MR §5.2, §8.1).
- **Expiry reminders:** defaults 30 and 7 days before expiry, to the adult holder and the admins; for dependent holders, to the document's guardian viewers (§4.6). Adjustable per family and per document within the bounds of §4.6; Scenario 6.
- **`UNLINK_DOCUMENT`:** soft delete with audit by the adult holder, or by an admin for any document the admin is a viewer of; the DigiLocker document itself is untouched.

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
      "intent_code": "SET_DOCUMENT_VISIBILITY",
      "description": "Change who in the family can see a linked document. Widening needs the holder's or guardian's passkey; narrowing does not.",
      "automation_tier_ceiling": 1,
      "allowed_roles": ["admin", "member"],
      "mutating": true,
      "requires_consent_providers": [],
      "entities_schema": {
        "type": "object",
        "additionalProperties": false,
        "required": ["document_id", "visibility"],
        "properties": {
          "document_id": { "type": "string", "format": "uuid" },
          "visibility": { "enum": ["family_adults", "holder_only", "guardians"] }
        }
      }
    },
    {
      "intent_code": "UNLINK_DOCUMENT",
      "description": "Soft-delete a linked document's metadata; the DigiLocker document is untouched.",
      "automation_tier_ceiling": 0,
      "allowed_roles": ["admin", "member"],
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
    "core_read_views": ["v_family_members", "v_module_permissions", "v_active_consents", "v_device_surfaces", "v_guardians"]
  },
  "dpi_providers": ["digilocker"],
  "service_dependencies": ["notification_engine"],
  "data_dependencies": [],
  "resource_budgets": { "p95_handler_ms": 200, "hard_timeout_ms": 15000 }
}
```

### 4.5 Owned schema (`secure_vault`)

DM §9.3 conventions; role `role_module_secure_vault` (MR §7.2). `user_id` is the **holder**, `created_by_user_id` the actor. No column can hold bytes: a CI test asserts that no `BYTEA`, `TEXT` over 4 KB or object-store write exists in this schema (§8 metric). Four tables:

| Table | Purpose | Notes |
|---|---|---|
| `secure_vault.documents` | Metadata and DigiLocker reference per linked document | Redacted number only; `milestone_at` replaces the date of birth |
| `secure_vault.document_access_log` | Every read, list, link, unlink and block | Module-level; the kernel audit log gets only writes |
| `secure_vault.family_settings` | The family's adjustable defaults (§4.6) | One row per family, created on first change; absent row = shipped defaults |
| `secure_vault.idempotency_ledger` | MR §6.4 ledger for `LINK_DOCUMENT` / `SET_DOCUMENT_VISIBILITY` / `UNLINK_DOCUMENT` | Same shape as the Finance ledger |

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
  doc_class                VARCHAR(10)  NOT NULL CHECK (doc_class IN ('family','personal')),          -- derived from doc_type at link time (§4.6)
  visibility               VARCHAR(15)  NOT NULL CHECK (visibility IN ('family_adults','holder_only','guardians')),
  admin_reminder_copy      BOOLEAN      NOT NULL DEFAULT TRUE, -- holder may switch off admin copies for a holder_only document
  reminders_muted          BOOLEAN      NOT NULL DEFAULT FALSE,
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
  action             VARCHAR(10) NOT NULL CHECK (action IN ('SHOW','LIST','LINK','UNLINK','VISIBILITY','MILESTONE')),
  result             VARCHAR(10) NOT NULL CHECK (result IN ('ALLOWED','BLOCKED','FAILED')),
  block_reason       VARCHAR(20),                             -- 'ROLE' | 'PUBLIC_SURFACE' | 'VISIBILITY' | 'CONSENT' | 'DPI'
  session_id         UUID, device_id UUID, is_public_surface BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), deleted_at TIMESTAMPTZ
);
CREATE INDEX idx_vault_access_family_created ON secure_vault.document_access_log(family_id, created_at DESC);

CREATE TABLE secure_vault.family_settings (                    -- §4.6; absent row = shipped defaults
  family_id              UUID      PRIMARY KEY REFERENCES core.families(family_id) ON DELETE CASCADE,
  reminder_lead_days     INTEGER[] NOT NULL DEFAULT '{30,7}'
                         CHECK (cardinality(reminder_lead_days) BETWEEN 1 AND 3
                                AND reminder_lead_days <@ ARRAY[60,30,14,7,3,1]),
  admins_get_copies      BOOLEAN   NOT NULL DEFAULT TRUE,   -- copies of adult holders' reminders to the admins
  updated_by_user_id     UUID      NOT NULL REFERENCES core.users(user_id),  -- must be an admin (app-layer check)
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), deleted_at TIMESTAMPTZ
);

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

### 4.6 Settings and defaults (founder rulings 2026-09-17)

Principle (Decision Log, "defaults, not constants"): where a rule is a matter of family preference, the recommended value ships as the default and the family can adjust it within bounds; safety rules are never settings.

**Document class** is derived from `doc_type` and is not editable:

| Class | Document types (Phase 1) | Idea |
|---|---|---|
| `family` | `VEHICLE_RC`, `INSURANCE_POLICY` (later: property papers, utility connection papers) | The household needs it, whoever's name is on it |
| `personal` | `DRIVING_LICENCE`, `PAN`, `BIRTH_CERTIFICATE` (later: passport, voter id) | Identifies one person |

**Visibility** says who, among the adults the kernel already lets into the Vault, is a viewer:

| Value | Viewers | Default for |
|---|---|---|
| `family_adults` | Every admin and member | `family`-class documents, whoever the holder is |
| `holder_only` | The holder | `personal` documents whose holder is an adult with Vault access (admin, member) |
| `guardians` | **Minor holder:** the parents and any marked legal guardian (adults with Vault access, from `v_guardians`); if the family has neither, the admins. **Managed holder:** the admins and the primary proxy. **Elder or passive holder:** the admins. | `personal` documents whose holder is a dependent (minor, elder, managed, passive) |

A **legal guardian** is marked by an admin in family management (kernel, Level 0 with passkey; relationship type `guardian`, DM v1.3 change 16). It is meant for a minor whose parents are not alive or not part of the family; the product cannot verify that and does not try, but the marking is audited. Being an admin does not by itself make someone a viewer of a child's personal documents: a grandfather who administers a joint family sees the family-class documents, not his grandson's birth certificate, unless he is marked as the legal guardian or the parents widen it.

**Who may change it, and how far:**

| Change | Who | Level |
|---|---|---|
| `holder_only` → `family_adults` (share) | The holder only | 1, passkey |
| `family_adults` → `holder_only` (unshare) on a `personal` document | The holder only | 0 |
| `guardians` → `family_adults` (let the other adults see a dependent's document) and back | One of the document's guardian viewers | 1 to widen, 0 to narrow |
| `family`-class document → `holder_only` | The holder | 0; allowed, because it is the holder's document, but the list shows the other adults nothing, so the family loses the expiry safety net: the confirmation text says so |
| Anything that would leave a dependent's document with no viewer | Nobody | Not possible: someone responsible must always be able to see a dependent's papers. If a minor's last parent or guardian leaves the family, the admins become the viewers until a legal guardian is marked |
| An admin widening another adult's `holder_only` document | Nobody | Not possible in Phase 1 (OI-7, break-glass) |

When a holder's role changes, defaults are re-applied once and the holder is told: Arjun's birth certificate moves from `guardians` to `holder_only` when the kernel records `minor → member` (Scenario 2, with the CM §2.5 consent migration); a member who becomes a managed profile has their `holder_only` documents moved to `guardians`.

**Reminder settings:**

| Setting | Default | Bounds | Who | Where |
|---|---|---|---|---|
| Lead times | 30 and 7 days before expiry | One to three values from 60, 30, 14, 7, 3, 1 | Admin | `family_settings.reminder_lead_days` |
| Admins get copies of adult holders' reminders | On | On / off | Admin | `family_settings.admins_get_copies` |
| Admin copy for one `holder_only` document | On, with content reduced to holder name and date | On / off | The holder | `documents.admin_reminder_copy` |
| Mute reminders for one document | Off | On / off | Any viewer who may unlink it | `documents.reminders_muted` |
| Recipients for a dependent's document | The document's guardian viewers | Not adjustable in Phase 1 | — | — |

Settings are changed in the PWA's family-settings screen (Level 0, admin) or on the document card (holder); both write an access-log row, and visibility changes also write the kernel audit row.

**Never a setting:** the role block for minor, elder, staff, managed and passive; the public-surface block (AGENTS.md §4 item 6); the passkey and CONSENT_REVERIFY on `SHOW_DOCUMENT`; zero document bytes at rest; the access log; the 60-second viewer; the age-18 prompt being a question to the admin and never an automatic role change.

## 5. India Stack (DPI) Touchpoints

Phase 1 touches DigiLocker only, and only through the WireMock simulator. No partner registration exists or is planned in portfolio mode.

- **Identity:** none. Aadhaar is never requested, stored or displayed. DigiLocker's own login is simulated as an OAuth authorisation-code exchange (CM §6.3); FamilyLifeOS holds a token *reference* in `core.consent_handles`, never the token.
- **Data:** purpose code `DIGILOCKER_DOCUMENT` (CM §3.2), one `consent_records` row per user who links documents, with `parental_consent_user_id` when the holder is a `minor` and `proxy_consent_user_id` when the holder is a managed profile (CM v1.3 §2.6). Data types: document type, redacted number, issue and expiry dates. The birth-certificate date of birth is read once to derive `milestone_at` and discarded (OI-2 asks for the registry's data-type list to say so).
- **Payments / Commerce:** none.
- **Simulator stubs:** defined in Tech_Spec_Simulator_Architecture §5.4 (rows D1–D8: authorise with a simulator-only account parameter, token, token refused, issued-documents list per DigiLocker account with `holder_ref`, expiring document, document fetch with a synthetic PDF, DigiLocker down, revoked document for VAULT_005) and §6.4. Ravi's and Priya's accounts return different lists, since an adult's documents come from their own account.
- **Rate limits:** DigiLocker is not one of the five budgeted DPIs (RB §1). The module self-imposes 30 document fetches per user per day as an abuse guard, tracked under `{env}:secure_vault:fetch:{user_id}:{YYYY-MM-DD}` (MR §5.3 key namespace).

## 6. Conflict Resolution Matrix

| Conflict scenario | Resolution logic |
|---|---|
| Two adults link the same DigiLocker document | `UNIQUE (family_id, digilocker_reference_id)` makes the second insert a no-op; the response returns the existing row and says who linked it. |
| Member wants to unlink a document they do not hold | Blocked: only the adult holder, or an admin who is a viewer, may unlink. The member is told to ask the holder or an admin; no alert is raised. |
| Admin asks for another adult's `holder_only` document | VAULT_006; no override in Phase 1. The message does not confirm that the document exists. Logged as BLOCKED / `VISIBILITY`; no alert, no `ROLE_VIOLATION`. The way through is to ask the holder to share it (Scenario 5). |
| Holder shares a document, then the two adults fall out | The holder narrows it back to `holder_only` at Level 0, no approval from anyone. What the other adult saw while it was shared is in the access log, which both can read for their own documents. |
| Holder's role changes (minor → member; member → managed) | Defaults are re-applied once at the role change and the holder (or the new guardians) is told what changed. Nothing is ever widened silently. |
| Admin is removed or demoted | They stop being a viewer of elder, managed and passive holders' `guardians` documents at once; `family_adults` documents follow their new role. A minor's documents are unaffected unless the person was also the parent or legal guardian. The last-admin rule (AGENTS.md §4 item 4) plus the admin fallback in §4.6 guarantee every dependent's documents always have a viewer. |
| A minor's parents separate; one parent's edge becomes inactive (DM §3.3 `is_active = FALSE`) | That parent stops being a viewer of the child's `guardians` documents, because `v_guardians` reads active edges only. This is a family-law-shaped corner case: the product follows what the admin records in the family graph and never decides custody. Flagged for the threat model alongside OI-7. |
| Proxies disagree about Nani's documents (Priya links, Ravi unlinks) | Follows the managed profile's `conflict_resolution_rule` (DM §3.4): `hierarchy` → the primary proxy's action stands; `notify_block` → both are paused and the admin is alerted. |
| Request arrives on a public surface | Blocked before dispatch regardless of role (DM §3.8, MR §6.2); logged as BLOCKED / `PUBLIC_SURFACE`. Metadata lists are blocked too, not only document display. |
| DigiLocker says a linked document is revoked or expired, local metadata says valid | DigiLocker wins (DPI truth). The row is updated, the holder and admin are notified, and `SHOW_DOCUMENT` returns VAULT_005. |
| Admin declines the age-18 prompt | Nothing changes. The prompt returns in 30 days. The Vault never escalates to anyone else and never changes the role itself. |
| Restricted role attempts any vault intent | BLOCKED at PERMISSION_CHECK, `ROLE_VIOLATION` audit entry, high-severity admin alert (Core PRD §6). |

## 7. Design & Generative UI

States, not screens, in the PWA.

- **Voice / text flow:** text-first; the browser speech stand-in arrives in Roadmap Phase 4. Utterances map to four intents; an ambiguous "show my papers" goes to AWAITING_CLARIFICATION with the holder's document list as choices.
- **Document list state:** cards grouped by holder with doc type, redacted number, issuer, an expiry badge (red ≤ 7 days, amber ≤ 30 days) and a visibility chip ("Family", "Only me", "Guardians"). Documents the viewer may not see are absent, not greyed out. The holder's card carries the share / unshare control and the reminder toggles. Never rendered on a public surface; the public-surface state shows "Documents are available on your own device."
- **Approval state (passkey):** "Show Ravi's driving licence (KA01 ····4821) from DigiLocker? It will be displayed on this device only and not saved." Approve / Cancel; the WebAuthn ceremony is the approval. Window: 5 minutes (DM §3.7 AWAITING_APPROVAL expiry).
- **Viewer state:** in-memory render with a "Verified via DigiLocker (simulator)" badge, expiry date, a 60-second countdown, no download or share control, and screenshot discouragement text. Closing or navigating away drops the bytes.
- **Milestone prompt:** a Concierge card for the admin only: "Arjun is now an adult. Should I upgrade his access to the Wealth pillar?" with Yes (passkey) / Not now.
- **Critical alerts:** `ROLE_VIOLATION` alerts go to the admin's private device only; expiry reminders use normal priority.

## 8. Technical Considerations & Success Metrics

### Technical approach

| Concern | Governing spec |
|---|---|
| Manifest, envelope, isolation, boot rules for a non-deactivatable module | MR v1.1 §4, §6, §7, §8.1 |
| Consent grant, renewal, CONSENT_REVERIFY, DigiLocker adapter, proxy consent | CM v1.3 §2.6, §4.2, §5, §6.3, §7 |
| Roles, public surface, kernel views, audit write protocol | DM v1.3 §3.2, §3.8, §3.17, §3.18 |
| Automation tiers (LINK, SHOW and widening visibility are Level 1; LIST, UNLINK and narrowing Level 0) | FSM v2.1 §2 |
| TTL | Document metadata: indefinite until unlink or DigiLocker revocation; document bytes: never cached (stricter than FSM §3.1) |

### Error codes (proposed)

| Code | Meaning | Retryable | User message |
|---|---|---|---|
| VAULT_001 | DigiLocker consent missing or expired | After renewal | "Your DigiLocker connection needs renewal. Tap to reconnect." |
| VAULT_002 | Requested document is not linked | No | "I don't have that document linked yet. Would you like to link it from DigiLocker?" |
| VAULT_003 | DigiLocker unavailable (simulator 5xx / timeout) | Yes | "DigiLocker is temporarily unavailable. Your document list is still here." |
| VAULT_004 | Blocked by role or public surface | No | "Documents can only be shown to an adult family member on a private device." |
| VAULT_005 | DigiLocker reports the document revoked or expired | No | "DigiLocker says this document is no longer valid. Please check with the issuer." |
| VAULT_006 | The requester is not a viewer of the document (visibility), or no such document is linked; deliberately indistinguishable | No | "I can't show that. Personal documents are visible only to their holder unless they choose to share them." |

Mapping to the module envelope: VAULT_001 → `MOD_CONSENT_MISSING`, VAULT_003 → `MOD_DPI_DOWN`, VAULT_004 → `MOD_PERMISSION_DENIED`; VAULT_002, VAULT_005 and VAULT_006 are `failure` with class TERMINAL (MR §9). VAULT_002 is returned only when the requester would be a viewer of such a document if it existed (their own, a family-class one, a dependent's); otherwise VAULT_006. Hindi strings belong in UX_Error_Message_Library.md (P1).

### Success metrics

- **Completion rate:** ≥ 90 % of `SHOW_DOCUMENT` requests by permitted roles end in a rendered document without correction.
- **DPI reliability:** ≥ 99 % against the simulator in normal mode; degraded-mode message shown in 100 % of injected outages.
- **Family NPS:** collected with the demo testers only.
- **Zero-bytes invariant:** the CI check of §4.5 passes on every PR (0 violations).
- **Block correctness:** 100 % of minor, staff and public-surface attempts in the test suite are blocked and logged.
- **Visibility correctness:** a generated matrix test (every role × class × visibility × holder type) shows 0 leaks across `SHOW_DOCUMENT`, `LIST_DOCUMENTS`, reminder text and error messages; VAULT_006 is byte-identical for "exists but hidden" and "does not exist".

## 9. GTM & Operations

- **What this module demonstrates (portfolio mode):** "sync, not duplicate" privacy design; consent-gated reads with CONSENT_REVERIFY; the public-surface rule; a Level 0 human decision (age-18 upgrade) that an agent proposes and never executes.
- **Launch plan:** delivered as the foundation with vertical slice 1 (Finance) because Finance and Health declare it in `data_dependencies`; its own demo moment is Scenario 1 in the second half of the demo script (docs/strategy/GTM_Plan.md).
- **Phasing:** Phase 2 of the Roadmap: manifest, schema, `LIST_DOCUMENTS`, boot duties. Phase 3: `LINK_DOCUMENT`, `SHOW_DOCUMENT`, access log, milestone sweep, expiry reminders.

## 10. Open Issues & Q&A

### Open issues

| ID | Issue | Priority | Resolution path |
|---|---|---|---|
| OI-1 | ~~Who receives expiry reminders, and when?~~ **Ruled 2026-09-17:** default is the holder (if an adult) and the admins at 30 and 7 days before expiry; for minor, managed and passive holders, the admins and the primary proxy only. Recipients and lead times are **family-adjustable settings**; how far they can be adjusted is designed when this section is detailed. | CLOSED | Decision Log 2026-09-17. |
| OI-2 | The purpose registry's data types for `DIGILOCKER_DOCUMENT` do not mention date of birth, which the milestone derivation reads once. | MEDIUM | Raise in Codex's round-2 review of CM v1.3 (one line in CM §3.2), or drop the derivation and ask the admin for the 18th-birthday date. |
| OI-3 | The Module Registry has no scheduling contract for module-owned nightly sweeps, and the audit codes `VAULT_DOCUMENT_LINKED`, `VAULT_DOCUMENT_UNLINKED`, `VAULT_VISIBILITY_CHANGED`, `VAULT_MILESTONE_DETECTED` are not in DM v1.3 §6. | MEDIUM | MR review round 2 (scheduler hook in the SDK); DM v1.3 taxonomy addition before freeze. |
| OI-4 | No DigiLocker circuit-breaker values exist in RB §8.2; this PRD borrows the AA defaults (3 failures → 30 min). | LOW | RB v1.3 when a second DigiLocker consumer appears. |
| OI-5 | Staff need specific documents (the RC for the driver). Needs a per-document, time-boxed sharing grant. | LOW (P2) | Separate PRD section in Phase 2; do not solve with a role exception. |
| OI-6 | ~~Co-owner model.~~ **Ruled 2026-09-17:** default visibility by document class — family documents (RC, insurance, property) are visible to admins and members; personal identity documents (PAN, passport, licence) are private to the holder. The holder can change it per document; the degree of customisation (per class, per person, admin overrides) is designed when `SHOW_DOCUMENT` is detailed. Managed, elder and passive holders' documents follow the admins (and the primary proxy for a managed profile). **Refined the same day:** a minor's documents follow the minor's parents and any marked legal guardian, not the admins as such (admins only as a fallback when the minor has neither in the family). | CLOSED | Decision Log 2026-09-17; affects `SHOW_DOCUMENT` analysis logic and adds a `visibility` attribute to the document metadata in PRD v0.2. |

| OI-7 | Break-glass: an adult is in hospital and the other needs their PAN or insurance-linked id. Phase 1 has no admin override of `holder_only`. | MEDIUM (P2) | Design with the threat model: a time-boxed, passkey-gated, loudly audited override that notifies the holder; never silent. Until then the answer is "share in advance". |
| OI-8 | Every module will want per-family settings (this PRD adds `secure_vault.family_settings`; Health has the MISSED threshold; Finance will follow). The Module Registry has no settings contract. | LOW | MR review round 2: either bless "each module owns a `family_settings` table in its schema" as the convention, or add an SDK settings helper. This PRD assumes the former. |
| OI-9 | ~~The simulator spec's DigiLocker table lacked a revoked-document response and a second account's issued list.~~ **Closed 2026-09-17:** added to Tech_Spec_Simulator_Architecture §5.4 (rows D4, D8) in PR #20. | CLOSED | — |

### Q&A

| Asked by | Question | Answer |
|---|---|---|
| Engineering | Master Context §5.2 says the Vault stores AA and ABHA consent tokens. Why doesn't it? | The frozen specs moved that responsibility to the kernel: `core.consent_handles` holds opaque references (DM §3.5, CM §1.4) and modules never see token material (MR §6.1). The Vault → Finance/Health edge survives as activation order only. |
| Engineering | Why is `SHOW_DOCUMENT` Level 1 with a passkey if it is a read? | It displays PII on a screen in a public place (the traffic-stop case). NFR §2.2's mandate covers PII export, and the prompt doubles as the human confirmation that the device and moment are right. |
| Product | Why can't an admin see everything? They run the family. | Founder ruling 2026-09-17: a spouse's PAN is theirs. The admin role is about running the household's shared business, which the `family` class covers, and about responsibility for dependents, which `guardians` covers. An admin override of another adult's identity documents is a different thing and needs a loud, audited design (OI-7), not a quiet default. |
| Product | Doesn't `holder_only` break the expiry safety net? | By default the admins still get a reduced reminder (holder name and date only). The holder can switch even that off for one document; that is their call, and the control says what they lose. |
| Engineering | Why is visibility enforced in the module and not in the kernel's permission check? | The kernel decides whether a role may use the Vault at all (deny-by-default RBAC, DM Q2). Which row a permitted adult may see depends on module data (class, holder, visibility) that the kernel must not know about (MR §7.2 isolation). The matrix test in §8 is what keeps the module honest. |
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
- [x] OI-1 and OI-6 ruled by the founder (2026-09-17) and applied in v0.2.
- [ ] Independent review round completed (Codex, WP-15); OI-2, OI-3, OI-8 settled in the round-2 spec reviews.
