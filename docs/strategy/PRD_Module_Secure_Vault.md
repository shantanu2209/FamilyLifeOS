# PRD: Secure Vault (module `secure_vault`)

> **Status:** DRAFT v0.3 — Codex's review of v0.2 (8 findings) applied; Codex's targeted re-review pending · **Author:** Shantanu Chaudhary (Lead Product Architect), drafted with Claude Code · **Last content change:** 2026-09-21
> **Scope:** Phase 1, portfolio-first build against DPI simulators. Module-level PRD that Tech_Spec_Module_Registry §1.2 defers to. The Vault is the foundation module (Master Context §5.2, `deactivatable: false`) delivered with vertical slice 1 and kept deliberately minimal: document metadata and DigiLocker retrieval, never document bytes.
> **Depends on:** MR v1.2 §3 (tiers), §4.1 (manifest; `deactivatable: false` boot rule), §5.2 (implicit activation), §6 (incl. §6.3 content references, §6.6 settings and scheduled jobs, §6.7 hooks), §7, §8.1 (boot abort), §9 (`MOD_DOMAIN_REJECTED`) · CM v1.4 §2.3 (data minimisation), §2.5 (minors, age-18 migration), §3.2 (DIGILOCKER_DOCUMENT), §4.2 (grant flow), §5 (CONSENT_REVERIFY), §6.3 (DigiLocker adapter), §7 (expiry watchdog) · DM v1.4 §3.2 (roles, `is_child`), §3.8 (public surface), §3.17 (`v_guardians`), §4.2 (shadow nodes), §6 and §6.1 (audit taxonomy and payloads), §7.1 (purge), §8 (seed), §9.3 (module and family-level table conventions) · RB v1.2 §1 (DigiLocker is not among the five rate-limited DPIs), §9 · FSM v2.1 §2 · Core PRD v2.2 §2, §3 (Scenarios 5, 6, 9), §4.3, §6 · MC §4.4 ("sync, not duplicate"), §5.2, §7.2 · Master PRD Module 5 · PROJECT_TRACKER Decision Log and Phase 1 Build Gate · Tech_Spec_Simulator_Architecture v0.1 §5.4, §6.4 (DigiLocker simulator).

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
| v0.3 | 2026-09-21 | Codex review of PR #22, all 8 findings. (f1) "Not linked" and "hidden" are told apart from who is asking about whom, never from the hidden row: VAULT_002 only where nothing can be hidden from the requester (§8). (f2) Link idempotency is per holder, and a duplicate returns the existing row only to someone who may see it (§4.2, §4.5, §6). (f3) `v_guardians` fix is in Data Model v1.4 §3.17; the spec edits have moved out of this PR into the WP-11 PR. (f4) New §4.7: actor, holder, DigiLocker account owner and consent subject are four things; shared display uses the holder's consent; an admin cannot consent for a managed person. (f5) Effective visibility is computed from live roles; the `on_role_changed` hook only tidies the stored value (§4.6). (f6) Refusals before dispatch are the kernel's audit rows, not this module's log; settings actions added to the log (§4.5). (f7) VAULT codes travel as `domain_code` under `MOD_DOMAIN_REJECTED` (§8). (f8) The reduced admin copy of a reminder is an explicit disclosure policy with its own tests (§4.6). Also: date of birth is now disclosed in the DigiLocker consent (founder ruling 2026-09-21, CM v1.4 §3.2), `milestone_at` is treated as sensitive, audit codes are registered (DM v1.4 §6.1), settings and sweep use MR v1.2 §6.6; OI-2, OI-3, OI-8 closed. | Shantanu Chaudhary (with Claude Code; review by Codex) |

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
2. PERMISSION_CHECK: admin ∈ `allowed_roles`; vault implicitly active. (The DigiLocker consent is checked later, at the Gateway, for the **holder** as subject, §4.7; checking it before the visibility rule would tell a requester whether someone else has connected DigiLocker.) REASONING: VaultAgent finds the `secure_vault.documents` row (`digilocker_reference_id`, expiry 2029-03-14, number redacted to `····4821`) — no external call yet.
3. APPROVAL_GATE (Level 1, NFR biometric mandate for PII display): passkey prompt "Show Ravi's driving licence (KA01 ····4821) from DigiLocker? It will be displayed on this device only and not saved." Ravi approves. CONSENT_REVERIFY reads `consent_records` live (CM §5.2; DigiLocker access token refreshed by the adapter, CM §6.3).
4. EXECUTION: the module returns a content reference (`result.data.content_ref`, MR v1.2 §6.3), not bytes; the kernel's content endpoint resolves it through the DPI Gateway → DigiLocker simulator document API, re-checks surface and consent for this device, and streams to the PWA viewer in memory (CM §6.3 step 5), with a "Verified via DigiLocker (simulator)" badge and the expiry. Nothing is written except `secure_vault.document_access_log (action SHOW, result ALLOWED, device Ravi Phone)`. The viewer closes after 60 s or on navigation. On the Kitchen Tablet the same request is blocked before dispatch and logged as BLOCKED (Core PRD Scenario 9).

### Scenario 2 — Arjun's birth certificate and the age-18 transition (Core PRD Scenario 5)

1. Ravi links Arjun's birth certificate: `LINK_DOCUMENT {doc_type: BIRTH_CERTIFICATE, holder_user_id: Arjun}`. Arjun is a `minor`, so the `DIGILOCKER_DOCUMENT` consent record for the fetch carries `parental_consent_user_id = Ravi` (CM §2.5, passkey by Ravi). The simulator returns the document metadata including the date of birth. The consent screen Ravi saw says so: the `DIGILOCKER_DOCUMENT` disclosure 2.0.0 names the date of birth and the stored milestone (CM v1.4 §3.2, founder ruling 2026-09-21).
2. VaultAgent stores the reference, issuer and issue date, computes `milestone_at = date_of_birth + 18 years` and stores **only** the milestone timestamp — the date of birth is held in memory for that one computation and is never stored, logged, put in an audit payload or sent to a hosted LLM (CM v1.4 §3.2; OI-2 closed). Because a milestone date can be turned back into a birth date, `milestone_at` is itself treated as sensitive: only the document's viewers ever see it, and the audit row carries the milestone type, not the date (DM v1.4 §6.1). Audit `PROXY_ACTION` is not used (Arjun is a minor, not a managed profile); the kernel records the consent grant.
3. Nightly at 03:00 IST (after the 01:00 purge and 02:00 shadow sweep, before the 06:00 consent watchdog) the vault sweep finds `milestone_at ≤ today` for a holder whose role is still `minor` and raises the milestone to the Supervisor (audit code `VAULT_MILESTONE_DETECTED`, actor SYSTEM_ACTOR_UUID; the sweep is a `scheduled_jobs` entry, MR v1.2 §6.6).
4. Ravi gets the Concierge prompt: "Arjun is now an adult. Should I upgrade his access to the Wealth pillar?" Ravi confirms with his passkey → the kernel's Family Management performs `ROLE_CHANGED` `minor → member` (Level 0), and CM §2.5 migrates the parent-granted consents to Arjun's own records with a notification to Arjun listing what exists and how to revoke. Declining leaves everything unchanged; the prompt returns in 30 days, never automatically executed.

### Scenario 3 — Ramesh needs the RC at a checkpost

Ramesh, on his own phone: *"Gaadi ka RC dikhao."* PERMISSION_CHECK fails (staff ∉ `allowed_roles`); `MOD_PERMISSION_DENIED`, and the **kernel** writes `ROLE_VIOLATION` to the audit log. The Vault is never dispatched, so its own access log has no row for this (v0.3: v0.2 asked for one, which would have needed either a dispatch of a forbidden intent or a kernel write into the module's schema; both are wrong. The family's "who tried what" view reads kernel refusals from the audit feed and module-level blocks from the access log). Ravi receives a high-severity alert (Core PRD §6) — which in this case is a legitimate request the product cannot serve yet: Ravi shows the RC from his own phone. Per-document sharing to staff is OI-5 (P2), not a Phase 1 workaround.

### Scenario 4 — Expired DigiLocker consent and a simulator outage

Priya asks for her insurance policy a year after linking. CONSENT_REVERIFY finds her `DIGILOCKER_DOCUMENT` record expired (the watchdog notified her at T-7/T-3/T-1 days, CM §7.2). VAULT_001 routes her to renewal (CM §7.3: new record, new OAuth reference; passkey) and then resumes. Later the DigiLocker simulator returns three consecutive 500s; there is no DigiLocker breaker in RB §8.2, so the module applies the AA defaults as a self-imposed policy (assumption, OI-4): `SHOW_DOCUMENT` returns VAULT_003 with "DigiLocker is temporarily unavailable; your document list is still here", while `LIST_DOCUMENTS` (local metadata) keeps working.

### Scenario 5 — Priya's PAN is hers (visibility, founder ruling 2026-09-17)

1. Ravi, on his own phone: *"Priya ka PAN dikhao."* The kernel's PERMISSION_CHECK passes (admin ∈ `allowed_roles`). In REASONING the VaultAgent applies the visibility rule (§4.6): the document is `personal`, its holder is an adult, its visibility is `holder_only`, and Ravi is not the holder. Result: VAULT_006, "I can't show that. Documents that belong to someone else are visible only if they have shared them." Ravi gets exactly this answer, with the same fields and the same code path, whether Priya has a PAN linked and hidden or has none linked at all: the choice between VAULT_002 and VAULT_006 is made from who is asking about whom (§8), before any document row is looked at. Access log: `SHOW`, `BLOCKED`, reason `VISIBILITY`. No `ROLE_VIOLATION`, no alert: asking is not an offence.
2. Tax season. Priya, on her phone: *"PAN ko family ke saath share karo."* → `SET_DOCUMENT_VISIBILITY {document_id, visibility: family_adults}`. Widening is Level 1: passkey prompt "Let Ravi see your PAN (····2K7F) in the family vault? You can undo this at any time." Audit `VAULT_VISIBILITY_CHANGED`, details `{document_id, holder_user_id, from, to, cause: holder_choice}` (DM v1.4 §6.1).
3. Ravi repeats his request; it now follows Scenario 1 with his own passkey. In April Priya narrows it back to `holder_only`; narrowing is Level 0, no passkey, same audit code.
4. `LIST_DOCUMENTS` for Ravi never showed the PAN while it was `holder_only`: not as a card, not as a count.

### Scenario 6 — The licence is about to expire (reminder defaults)

The 03:00 sweep finds Ravi's driving licence 30 days from expiry. Defaults (§4.6): the holder is reminded at 30 and 7 days; the admins get a copy. Ravi is both. Had it been Priya's `holder_only` licence, Ravi's copy would read "One of Priya's personal documents expires on 14 March" with no type and no number. That copy tells Ravi something the list would not (that Priya has a personal document, and a date); it is a deliberate, limited disclosure chosen by the founder as the default safety net, specified as its own policy in §4.6 and switchable off by Priya. Priya can mute admin copies for that one document; Ravi can change the family's lead times to 60/30/7. For Nani's (managed) insurance card the reminder goes to the admins and to Priya as primary proxy, never to Nani. A reminder about Arjun's passport, were one linked, would go to Ravi and Priya as his parents, whoever the admins are.

## 4. Functional Requirements (The "Agentic" Loop)

### 4.1 The loop for link, show and milestone

- **Trigger:** a request on a private device (`LINK_DOCUMENT`, `LIST_DOCUMENTS`, `SHOW_DOCUMENT`, `SET_DOCUMENT_VISIBILITY`, `UNLINK_DOCUMENT`); the nightly 03:00 IST sweep (expiry within 30 days, age-18 milestones) declared as a `scheduled_jobs` entry and run per family by the kernel scheduler (MR v1.2 §6.6); the kernel's consent watchdog for `DIGILOCKER_DOCUMENT` renewals (CM §7).
- **Information gathering:** actor role and `acting_as` from the envelope; holder role from `v_family_members`; parents, legal guardians and proxies of a dependent holder from `v_guardians`; the document's own stored consent reference (§4.7; `v_active_consents` is only a hint for the UI, never the authorisation, DM v1.4 §3.17); device surface from `v_device_surfaces`; local `secure_vault.documents`; the DigiLocker simulator's document list/metadata endpoint (link) or document endpoint (show) through the DPI Gateway, with the OAuth token handled by the Consent Manager adapter (CM §6.3).
- **Analysis logic (deterministic):** the requester may see or act on a document only if the visibility rule of §4.6 names them a viewer (the kernel has already checked that they are `admin` or `member`); every list, count and error message is filtered by the same rule, so nothing reveals a document the requester cannot see; reminders follow the same rule with **one named exception**, the reduced admin copy (§4.6 "Reminder copy policy"); expiry badge = red ≤ 7 days, amber ≤ 30 days; `milestone_at ≤ today AND holder.is_child` (DM v1.4 §3.2) → milestone; a DigiLocker response that says the document is revoked or expired overrides local metadata (DPI truth wins). No inference on document content beyond the metadata fields the simulator returns.
- **Execution / fulfilment:** `LINK_DOCUMENT` writes one `secure_vault.documents` row inside a transaction with its idempotency ledger row and the audit write protocol of DM v1.4 §3.18 through the SDK's `AuditClient` (`VAULT_DOCUMENT_LINKED`); `SHOW_DOCUMENT` returns a content reference that the kernel resolves and streams to the client in memory (MR v1.2 §6.3), and writes only an access-log row; `SET_DOCUMENT_VISIBILITY` updates one row with the audit write protocol (`VAULT_VISIBILITY_CHANGED`); `UNLINK_DOCUMENT` soft-deletes; the sweep sends expiry reminders (recipients and lead times from `secure_vault.family_settings`, §4.6) and milestone prompts through `notification_engine` to private devices. The Vault never changes a role and never calls Finance or Health (MR §3.2).

### 4.2 Features In (Prioritised)

- **`LINK_DOCUMENT` [M]:** DigiLocker-simulator reference plus redacted metadata. An adult links their **own** documents from their own DigiLocker consent; a dependent's documents are linked by one of that dependent's guardian viewers (§4.6): a parent or legal guardian for a child (parental consent path, CM v1.4 §2.5), the **primary proxy** for a managed profile (proxy consent, CM v1.4 §2.6; an admin who is not the proxy can link only when the proxy's consent for that person already exists, and is otherwise told that the proxy has been asked, §4.7), an admin for elder and passive holders. Nobody links a document into another adult's name. Class and default visibility are set at link time (§4.6). Idempotent on `(family_id, holder, digilocker_reference_id)`: see §6 row 1 for what a duplicate returns and to whom.
- **`SHOW_DOCUMENT` [M]:** Scenario 1; passkey, CONSENT_REVERIFY, in-memory rendering, access log, 60 s auto-close.
- **`LIST_DOCUMENTS` [M]:** the document metadata the requester is a viewer of, with expiry badges; no DPI call.
- **Visibility model [M]:** document class, `visibility` attribute, defaults and `SET_DOCUMENT_VISIBILITY` as in §4.6; Scenario 5.
- **Access log [M]:** every SHOW / LIST / LINK / UNLINK / VISIBILITY / SETTINGS / REMINDER action **that reaches the module**, allowed or blocked, with actor, device and result (`secure_vault.document_access_log`). Refusals made by the kernel before dispatch (role, public surface, activation) are kernel audit rows (`ROLE_VIOLATION`), not rows here.
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

Valid against MR v1.2 §4.1 and its semantic rules (§4.3). Consent is purpose-bound and subject-bound: the subject of `DIGILOCKER_DOCUMENT` is always the **holder** (`subject: entity`, `holder_user_id`; when the entity is null the Supervisor fills it with the actor before validation). For `SHOW_DOCUMENT` the entry is `when: external_call`, so consent is checked by the Gateway only after the module's visibility rule has passed; checked earlier, a `MOD_CONSENT_MISSING` would tell Ravi whether Priya has connected DigiLocker.

```json
{
  "manifest_version": 1,
  "module_id": "secure_vault",
  "version": "0.1.0",
  "tier": "core",
  "envelope_versions": ["1.0"],
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
      "requires_consent_purposes": [
        { "purpose_code": "DIGILOCKER_DOCUMENT", "subject": "entity", "subject_entity": "holder_user_id", "when": "dispatch" }
      ],
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
      "requires_consent_purposes": [
        { "purpose_code": "DIGILOCKER_DOCUMENT", "subject": "entity", "subject_entity": "holder_user_id", "when": "external_call" }
      ],
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
      "intent_code": "SET_VAULT_SETTING",
      "description": "Change one family-level Vault setting within its bounds (admin only).",
      "automation_tier_ceiling": 0,
      "allowed_roles": ["admin"],
      "mutating": true,
      "requires_consent_providers": [],
      "entities_schema": {
        "type": "object",
        "additionalProperties": false,
        "required": ["setting", "value", "expected_settings_version"],
        "properties": {
          "setting": { "enum": ["reminder_lead_days", "admins_get_copies"] },
          "value": {},
          "expected_settings_version": { "type": "integer", "minimum": 0 }
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
  "scheduled_jobs": [
    { "job_code": "vault_nightly_sweep", "handler": "nightly_sweep", "every_seconds": 86400, "scope": "family", "max_run_ms": 10000 }
  ],
  "domain_errors": [
    { "domain_code": "VAULT_002", "message_key": "vault.error.not_linked" },
    { "domain_code": "VAULT_005", "message_key": "vault.error.document_invalid" },
    { "domain_code": "VAULT_006", "message_key": "vault.error.not_available" },
    { "domain_code": "VAULT_007", "message_key": "vault.error.setting_rejected" }
  ],
  "resource_budgets": { "p95_handler_ms": 200, "hard_timeout_ms": 15000, "read_budget_ms": 1500 }
}
```

The kernel scheduler runs the sweep once per family per day; the 03:00 IST slot of Scenario 2 is the scheduler's start time for daily jobs, after the kernel's 01:00 purge and 02:00 shadow sweep. `SHOW_DOCUMENT`'s 3-second objective (§1) is an `execute` of a Level 1 read with a passkey step in the middle; the 1,500 ms read budget applies to `LIST_DOCUMENTS` and to the `prepare` part of SHOW.

### 4.5 Owned schema (`secure_vault`)

DM §9.3 conventions; role `role_module_secure_vault` (MR §7.2). `user_id` is the **holder**, `created_by_user_id` the actor. No column can hold bytes: a CI test asserts that no `BYTEA`, `TEXT` over 4 KB or object-store write exists in this schema (§8 metric). Four tables:

| Table | Purpose | Notes |
|---|---|---|
| `secure_vault.documents` | Metadata and DigiLocker reference per linked document | Redacted number only; `milestone_at` replaces the date of birth |
| `secure_vault.document_access_log` | Every read, list, link, unlink and block | Module-level; the kernel audit log gets only writes |
| `secure_vault.family_settings` | The family's adjustable defaults (§4.6) | Family-level table (DM v1.4 §9.3 exception): one row per family, created on first change; absent row = shipped defaults; `settings_version` for optimistic writes (MR v1.2 §6.6) |
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
  consent_record_ref       UUID         NOT NULL,             -- consent_records.record_id whose SUBJECT is the holder (§4.7); reference only
  provider_account_user_id UUID         NOT NULL REFERENCES core.users(user_id),  -- whose DigiLocker account the document comes from (§4.7):
                                                                -- the holder for an adult; the linking guardian or proxy for a dependent
  issuer_name              VARCHAR(120),
  doc_number_redacted      VARCHAR(12),                       -- last four characters only, e.g. '····4821'
  issue_date               DATE,
  expiry_date              DATE,                              -- NULL for documents that do not expire
  milestone_at             DATE,                              -- birth certificates: date_of_birth + 18 years; DOB itself never stored.
                                                              -- SENSITIVE derived data (reversible to a birth date): viewers only, never in audit details
  verified                 BOOLEAN      NOT NULL DEFAULT TRUE, -- DigiLocker-issued; uploads (P2) would be FALSE
  doc_class                VARCHAR(10)  NOT NULL CHECK (doc_class IN ('family','personal')),          -- derived from doc_type at link time (§4.6)
  visibility               VARCHAR(15)  NOT NULL CHECK (visibility IN ('family_adults','holder_only','guardians')),
  admin_reminder_copy      BOOLEAN      NOT NULL DEFAULT TRUE, -- holder may switch off admin copies for a holder_only document
  reminders_muted          BOOLEAN      NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), deleted_at TIMESTAMPTZ
  -- v0.3: uniqueness is per HOLDER. With (family_id, reference) alone, a second adult submitting a reference
  -- they knew from before it was hidden got the hidden row back (Codex f2). A holder's row is always visible
  -- to anyone entitled to link for that holder, so a conflict on this key never reveals a hidden document.
  -- Partial, so an unlinked document can be linked again.
);
CREATE UNIQUE INDEX idx_vault_docs_unique_live ON secure_vault.documents(family_id, user_id, digilocker_reference_id)
  WHERE deleted_at IS NULL;
CREATE INDEX idx_vault_docs_family_created ON secure_vault.documents(family_id, created_at DESC);
CREATE INDEX idx_vault_docs_expiry    ON secure_vault.documents(expiry_date)  WHERE deleted_at IS NULL AND expiry_date IS NOT NULL;
CREATE INDEX idx_vault_docs_milestone ON secure_vault.documents(milestone_at) WHERE deleted_at IS NULL AND milestone_at IS NOT NULL;

CREATE TABLE secure_vault.document_access_log (
  access_id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  family_id          UUID        NOT NULL REFERENCES core.families(family_id) ON DELETE CASCADE,
  user_id            UUID        NOT NULL REFERENCES core.users(user_id) ON DELETE CASCADE,   -- actor
  document_id        UUID        REFERENCES secure_vault.documents(document_id),               -- NULL for LIST and blocked lookups
  action             VARCHAR(10) NOT NULL CHECK (action IN ('SHOW','LIST','LINK','UNLINK','VISIBILITY','MILESTONE','SETTINGS','REMINDER')),
  -- SETTINGS = a family_settings change (document_id NULL); REMINDER = a per-document reminder toggle
  -- (admin_reminder_copy, reminders_muted). setting_code says which; values are in the audit row
  -- (VAULT_SETTINGS_CHANGED) for family settings and in the documents row for per-document toggles.
  setting_code       VARCHAR(30) CHECK (setting_code IN ('reminder_lead_days','admins_get_copies','admin_reminder_copy','reminders_muted')),
  CONSTRAINT chk_vault_setting_code CHECK ((action IN ('SETTINGS','REMINDER')) = (setting_code IS NOT NULL)),
  result             VARCHAR(10) NOT NULL CHECK (result IN ('ALLOWED','BLOCKED','FAILED')),
  block_reason       VARCHAR(20) CHECK (block_reason IN ('VISIBILITY','NOT_HOLDER','CONSENT','DPI','BOUNDS','STALE_VERSION')),
                                                              -- module-level reasons only. ROLE and PUBLIC_SURFACE refusals happen
                                                              -- before dispatch and are kernel audit rows (ROLE_VIOLATION), v0.3
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
  settings_version       INTEGER   NOT NULL DEFAULT 1,      -- +1 on every change; writes are WHERE settings_version = $expected
  updated_by             UUID      NOT NULL REFERENCES core.users(user_id),  -- must be an admin (app-layer check)
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);  -- family-level table: no user_id, no deleted_at (DM v1.4 §9.3)

CREATE TABLE secure_vault.idempotency_ledger (                 -- MR §6.4, same shape as finance
  idempotency_key UUID PRIMARY KEY,
  family_id UUID NOT NULL REFERENCES core.families(family_id) ON DELETE CASCADE,
  user_id   UUID NOT NULL REFERENCES core.users(user_id) ON DELETE CASCADE,
  intent_code VARCHAR(40) NOT NULL,
  state VARCHAR(10) NOT NULL CHECK (state IN ('pending','final')),         -- MR v1.2 §6.4
  response_envelope JSONB,
  external_ref VARCHAR(100),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), finalised_at TIMESTAMPTZ,
  CHECK ((state = 'final') = (response_envelope IS NOT NULL))
);  -- Vault mutations make no external call after the ledger insert, so a row is 'pending' only inside one transaction
CREATE INDEX idx_vault_ledger_family_created ON secure_vault.idempotency_ledger(family_id, created_at DESC);
```

`purge_user(family_id, user_id)` (MR v1.2 §6.7): soft-deleted and live `documents` rows whose holder or `provider_account_user_id` is the purged user are hard-deleted, with their access-log rows' `document_id` set NULL; access-log rows where the purged user was the actor are deleted; ledger rows are deleted. A document of a dependent that came from the purged guardian's DigiLocker account cannot be fetched any more, so it goes too, and the remaining guardians are told to link it from their own account.

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
| `guardians` | **Child holder** (`is_child`: a `minor`, or a managed infant): the parents and any marked legal guardian (adults with Vault access, from `v_guardians`); if the family has neither, the admins. **Managed holder:** the admins and the primary proxy. **Elder or passive holder:** the admins. | `personal` documents whose holder is a dependent (minor, elder, managed, passive) |

A **legal guardian** is marked by an admin in family management (kernel, Level 0 with passkey; relationship type `guardian`, DM v1.4 §3.3). It is meant for a minor whose parents are not alive or not part of the family; the product cannot verify that and does not try, but the marking is audited. Being an admin does not by itself make someone a viewer of a child's personal documents: a grandfather who administers a joint family sees the family-class documents, not his grandson's birth certificate, unless he is marked as the legal guardian or the parents widen it.

**Who may change it, and how far:**

| Change | Who | Level |
|---|---|---|
| `holder_only` → `family_adults` (share) | The holder only | 1, passkey |
| `family_adults` → `holder_only` (unshare) on a `personal` document | The holder only | 0 |
| `guardians` → `family_adults` (let the other adults see a dependent's document) and back | One of the document's guardian viewers | 1 to widen, 0 to narrow |
| `family`-class document → `holder_only` | The holder | 0; allowed, because it is the holder's document, but the list shows the other adults nothing, so the family loses the expiry safety net: the confirmation text says so |
| Anything that would leave a dependent's document with no viewer | Nobody | Not possible: someone responsible must always be able to see a dependent's papers. If a minor's last parent or guardian leaves the family, the admins become the viewers until a legal guardian is marked |
| An admin widening another adult's `holder_only` document | Nobody | Not possible in Phase 1 (OI-7, break-glass) |

**Effective visibility (v0.3).** The stored `visibility` is a preference; who may see a document is computed at read time from the stored value **and the holder's live role** (`v_family_members`, `v_guardians`), so a role change takes effect at once even if nothing in this schema has been updated yet:

| Holder is now | Stored value | Effective value |
|---|---|---|
| An adult with Vault access (admin, member) | `guardians` | `holder_only` (there are no guardians of an adult; former guardians lose access immediately) |
| A dependent (child, elder, managed, passive) | `holder_only` | `guardians` (a dependent cannot open the Vault, so `holder_only` would leave no viewer) |
| Either | `family_adults` | `family_adults` |

The guardian set itself is always live: a parent whose edge is inactive, a proxy who was replaced, a guardian who left the family or was deleted is not in `v_guardians` and is not a viewer, whatever is stored.

The kernel then calls `on_role_changed` (MR v1.2 §6.7; at-least-once, retried by the Healer). The handler is idempotent: it rewrites stored values to their effective value (Arjun's birth certificate `guardians` → `holder_only` when the kernel records `minor → member`, Scenario 2, with the CM §2.5 consent migration; a member who becomes a managed profile has `holder_only` → `guardians`), writes `VAULT_VISIBILITY_CHANGED` with `cause: role_change` and SYSTEM_ACTOR_UUID, and tells the holder (or the new guardians) what changed. If the hook is late or lost, access is already correct; only the stored value and the notice are late. Nothing is ever widened by the hook: both rewrites narrow or keep the viewer set relative to what the stored value would have meant for the old role.

**Reminder settings:**

| Setting | Default | Bounds | Who | Where |
|---|---|---|---|---|
| Lead times | 30 and 7 days before expiry | One to three values from 60, 30, 14, 7, 3, 1 | Admin | `family_settings.reminder_lead_days` |
| Admins get copies of adult holders' reminders | On | On / off | Admin | `family_settings.admins_get_copies` |
| Admin copy for one `holder_only` document | On, with content reduced to holder name and date | On / off | The holder | `documents.admin_reminder_copy` |
| Mute reminders for one document | Off | On / off | Any viewer who may unlink it | `documents.reminders_muted` |
| Recipients for a dependent's document | The document's guardian viewers | Not adjustable in Phase 1 | — | — |

Settings are changed in the PWA's family-settings screen (`SET_VAULT_SETTING`, Level 0, admin) or on the document card (holder). A family setting follows MR v1.2 §6.6: one transaction with `WHERE settings_version = $expected`, the audit row `VAULT_SETTINGS_CHANGED` (typed `from`/`to`, DM v1.4 §6.1) and an access-log row (`SETTINGS`, `setting_code`); out-of-bounds or stale-version writes are refused with VAULT_007. A per-document toggle writes the documents row and an access-log row (`REMINDER`, `setting_code`). Visibility changes write the kernel audit row as before.

**Reminder copy policy (v0.3).** The visibility rule has exactly one exception, and it is a policy, not a leak:

- **What:** when `family_settings.admins_get_copies` is on (default) **and** the document's `admin_reminder_copy` is on (default), each admin who is *not* a viewer of an adult holder's `holder_only` document receives a reduced expiry reminder.
- **Fields, exhaustively:** the holder's display name and the expiry date. Not the document type, class, number, issuer, or a link to anything. Text key `vault.reminder.reduced_copy`.
- **Why it exists:** founder ruling 2026-09-17 (OI-1): a lapsed licence or policy costs the household money, and the holder may be the one person who does not notice.
- **Who can switch it off:** the holder, per document (`admin_reminder_copy`); an admin, for the whole family (`admins_get_copies`). Nobody can switch it on for a document whose holder switched it off.
- **Never:** on a public surface (reminders go to private devices only); for a dependent's document (those go to the guardian viewers in full); to a member who is not an admin.
- **Tests:** the visibility matrix (§8) asserts 0 leaks with this path excluded, and a separate reminder-policy test asserts that the reduced copy contains exactly the two fields, is absent when either switch is off, and is never produced for a public surface. A reduced copy showing up anywhere else, or carrying a third field, is a privacy regression.

**Never a setting** (MR v1.2 §6.6: a setting never weakens a safety gate): the role block for minor, elder, staff, managed and passive; the public-surface block (AGENTS.md §4 item 6); the passkey and CONSENT_REVERIFY on `SHOW_DOCUMENT`; zero document bytes at rest; the access log; the 60-second viewer; the age-18 prompt being a question to the admin and never an automatic role change.

### 4.7 Four parties, one consent (v0.3)

v0.2 spoke of "the user's DigiLocker consent" as if one person were involved. Up to four are, and the server checks each separately; none of it is taken from the client.

| Party | Who | Stored as |
|---|---|---|
| **Actor** | The authenticated adult making the request; their passkey approves it | `envelope.actor.user_id`; access log `user_id` |
| **Holder** | The person the document is about | `documents.user_id` |
| **Account owner** | Whose DigiLocker account the document is fetched from | `documents.provider_account_user_id`; the OAuth reference is that person's row in `core.consent_handles` |
| **Consent subject** | Whose `DIGILOCKER_DOCUMENT` consent record authorises the processing: always the **holder** | `documents.consent_record_ref` → `core.consent_records.user_id` = holder |

| Holder is | Account owner | Who grants the holder's consent record |
|---|---|---|
| An adult with Vault access | The holder | The holder, for themselves |
| A child (`is_child`) | The parent or legal guardian who links | That parent or guardian: `parental_consent_user_id` (CM v1.4 §2.5); for a managed infant also `proxy_consent_user_id` |
| A managed adult | The primary proxy who links | The **primary proxy**: `proxy_consent_user_id` (CM v1.4 §2.6.1). Not an admin as such |
| Elder or passive | The admin who links | **Open point OI-10:** CM has no rule for who consents for an elder who has a login but no Vault access, or for a passive person. Until it has one, linking for an elder needs the elder's own consent record (granted on their device), and linking for a passive person is **out** of Phase 1 |

Rules:

1. **Link.** The kernel resolves the holder's `DIGILOCKER_DOCUMENT` record before dispatch (`when: dispatch`, subject = holder). If it is missing, the grant flow runs and the *authorised* person is asked: an admin linking Nani's insurance card when no proxy consent exists gets "Priya looks after Nani's consents; I've asked her", and nothing is linked. Being admin never creates the authority to consent (CM v1.4 §2.6.1). The module additionally verifies that the record's subject equals `holder_user_id`, that the handle behind it belongs to `provider_account_user_id`, and that the account owner is the actor (you link from your own account only).
2. **Show.** After the visibility rule passes, the content reference names the document's **stored** `consent_record_ref`. The Gateway fetches with the account owner's handle, not the actor's: when Ravi views Priya's shared PAN, Ravi's passkey approves the display, Priya's consent and Priya's DigiLocker account serve it. Ravi having his own DigiLocker consent is neither needed nor used.
3. **The holder's consent governs shared display.** If that record is expired, withdrawn, revoked, or waiting for proxy re-confirmation (CM v1.4 §2.6.4), nobody is shown the document, sharing or not: VAULT_001, worded for a non-holder as "this document's DigiLocker connection needs renewal; I've let {holder} know", and the holder (or their proxy) gets the renewal prompt. Metadata stays listed.
4. **Withdrawal.** When the holder's consent ends, the documents that hang on it stay linked but unfetchable; `UNLINK` with `reason: consent_ended` runs if it is not renewed within 30 days.

## 5. India Stack (DPI) Touchpoints

Phase 1 touches DigiLocker only, and only through the WireMock simulator. No partner registration exists or is planned in portfolio mode.

- **Identity:** none. Aadhaar is never requested, stored or displayed. DigiLocker's own login is simulated as an OAuth authorisation-code exchange (CM §6.3); FamilyLifeOS holds a token *reference* in `core.consent_handles`, never the token.
- **Data:** purpose code `DIGILOCKER_DOCUMENT` (CM §3.2), one `consent_records` row per **holder** (§4.7), with `parental_consent_user_id` when the holder is a child and `proxy_consent_user_id` when the holder is a managed profile (CM v1.4 §2.5–2.6). Data types, as disclosed in version 2.0.0 of the consent screen (CM v1.4 §3.2): document type, redacted number, issue and expiry dates, and the date of birth read in memory to derive a milestone; the milestone is stored, the date of birth never is.
- **Payments / Commerce:** none.
- **Simulator stubs:** defined in Tech_Spec_Simulator_Architecture §5.4 (rows D1–D8: authorise with a simulator-only account parameter, token, token refused, issued-documents list per DigiLocker account with `holder_ref`, expiring document, document fetch with a synthetic PDF, DigiLocker down, revoked document for VAULT_005) and §6.4. Ravi's and Priya's accounts return different lists, since an adult's documents come from their own account.
- **Rate limits:** DigiLocker is not one of the five budgeted DPIs (RB §1). The module self-imposes 30 document fetches per user per day as an abuse guard, tracked under `{env}:secure_vault:fetch:{user_id}:{YYYY-MM-DD}` (MR §5.3 key namespace).

## 6. Conflict Resolution Matrix

| Conflict scenario | Resolution logic |
|---|---|
| The same DigiLocker document is linked twice | Uniqueness is per holder (`family_id, holder, reference`, live rows). Same holder, same reference: the insert conflicts; the module then applies the **current** visibility rule to the existing row. A viewer gets the existing row back (and who linked it); anyone else gets VAULT_006 and nothing about the row or its creator. In practice the second person is a viewer, because only the holder or the holder's guardians may link for that holder (§4.2); the check is there so that a bug in that rule cannot become a leak. A different holder with the same reference (the RC is in both spouses' DigiLocker accounts) is a separate row with its own visibility. Replaying the *same request* (same idempotency key) returns the ledger's stored envelope, as for any mutation. |
| Member wants to unlink a document they do not hold | Blocked: only the adult holder, or an admin who is a viewer, may unlink. The member is told to ask the holder or an admin; no alert is raised. |
| Admin asks for another adult's `holder_only` document | VAULT_006; no override in Phase 1. The message does not confirm that the document exists. Logged as BLOCKED / `VISIBILITY`; no alert, no `ROLE_VIOLATION`. The way through is to ask the holder to share it (Scenario 5). |
| Holder shares a document, then the two adults fall out | The holder narrows it back to `holder_only` at Level 0, no approval from anyone. What the other adult saw while it was shared is in the access log, which both can read for their own documents. |
| Holder's role changes (minor → member; member → managed) | Access follows the live role at once (effective visibility, §4.6). The `on_role_changed` hook then rewrites the stored value and tells the holder (or the new guardians); it is idempotent and retried, so a crash between the kernel's role change and the module's update delays the notice, never the access change. Nothing is ever widened silently. |
| Guardian, proxy or parent leaves, is replaced or is deleted | They drop out of `v_guardians` (live people, active edges, same family: DM v1.4 §3.17) and stop being a viewer at the next read. If that leaves a child with no parent or guardian in the family, the admin fallback applies. Documents fetched from the departed person's DigiLocker account cannot be fetched any more (§4.7) and are flagged for re-linking. |
| Admin is removed or demoted | They stop being a viewer of elder, managed and passive holders' `guardians` documents at once; `family_adults` documents follow their new role. A minor's documents are unaffected unless the person was also the parent or legal guardian. The last-admin rule (AGENTS.md §4 item 4) plus the admin fallback in §4.6 guarantee every dependent's documents always have a viewer. |
| A minor's parents separate; one parent's edge becomes inactive (DM §3.3 `is_active = FALSE`) | That parent stops being a viewer of the child's `guardians` documents, because `v_guardians` reads active edges only. This is a family-law-shaped corner case: the product follows what the admin records in the family graph and never decides custody. Flagged for the threat model alongside OI-7. |
| Proxies disagree about Nani's documents (Priya links, Ravi unlinks) | Follows the managed profile's `conflict_resolution_rule` (DM §3.4): `hierarchy` → the primary proxy's action stands; `notify_block` → both are paused and the admin is alerted. |
| Request arrives on a public surface | Blocked by the kernel before dispatch regardless of role (DM §3.8, MR §6.2) and recorded in the kernel audit log; the module never sees it. Metadata lists are blocked too, not only document display. The content endpoint repeats the check for the device that actually asks for the bytes. |
| DigiLocker says a linked document is revoked or expired, local metadata says valid | DigiLocker wins (DPI truth). The row is updated, the holder and admin are notified, and `SHOW_DOCUMENT` returns VAULT_005. |
| Admin declines the age-18 prompt | Nothing changes. The prompt returns in 30 days. The Vault never escalates to anyone else and never changes the role itself. |
| Restricted role attempts any vault intent | Refused at PERMISSION_CHECK (`MOD_PERMISSION_DENIED`), kernel `ROLE_VIOLATION` audit entry, high-severity admin alert (Core PRD §6). No module access-log row. |

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
| Manifest, envelope, isolation, boot rules for a non-deactivatable module; settings, scheduled jobs, hooks | MR v1.2 §4, §6, §7, §8.1 |
| Consent grant, renewal, CONSENT_REVERIFY, DigiLocker adapter, parental and proxy consent | CM v1.4 §2.5, §2.6, §4.2, §5, §6.3, §7 |
| Roles, public surface, kernel views, audit write protocol and payloads | DM v1.4 §3.2, §3.8, §3.17, §3.18, §6.1 |
| Automation tiers (LINK, SHOW and widening visibility are Level 1; LIST, UNLINK and narrowing Level 0) | FSM v2.1 §2 |
| TTL | Document metadata: indefinite until unlink or DigiLocker revocation; document bytes: never cached (stricter than FSM §3.1) |

### Error codes

| Code | Meaning | Retryable | User message |
|---|---|---|---|
| VAULT_001 | DigiLocker consent missing or expired | After renewal | "Your DigiLocker connection needs renewal. Tap to reconnect." |
| VAULT_002 | Requested document is not linked | No | "I don't have that document linked yet. Would you like to link it from DigiLocker?" |
| VAULT_003 | DigiLocker unavailable (simulator 5xx / timeout) | Yes | "DigiLocker is temporarily unavailable. Your document list is still here." |
| VAULT_004 | Blocked by role or public surface | No | "Documents can only be shown to an adult family member on a private device." |
| VAULT_005 | DigiLocker reports the document revoked or expired | No | "DigiLocker says this document is no longer valid. Please check with the issuer." |
| VAULT_006 | The requester asked about someone else's document and either is not a viewer of it or there is none; deliberately indistinguishable | No | "I can't show that. Documents that belong to someone else are visible only if they have shared them." |
| VAULT_007 | A settings change was out of bounds or made against a stale `settings_version` | After re-reading | "That setting changed in the meantime. Here is the current value." |

**Mapping to the module envelope (MR v1.2 §9).** `error.code` is always a `MOD_*` code; the VAULT code travels as `error.domain_code`, registered in the manifest's `domain_errors`, and selects the user message. VAULT_001 → `MOD_CONSENT_MISSING`; VAULT_003 → `MOD_DPI_DOWN`; VAULT_004 is the user-facing text of the kernel's own `MOD_PERMISSION_DENIED` (the module never produces it); VAULT_002, VAULT_005, VAULT_006 and VAULT_007 → `MOD_DOMAIN_REJECTED` with their `domain_code`. v0.2 returned bare VAULT codes, which envelope validation would have turned into `MOD_INTERNAL` and an operator alert. `MOD_DOMAIN_REJECTED` raises no `ROLE_VIOLATION` and no admin alert, and does not count toward the module breaker, which is what Scenario 5 needs. Hindi strings belong in UX_Error_Message_Library.md (P1).

**VAULT_002 or VAULT_006: decided without looking at the document (v0.3).** v0.2 returned VAULT_002 when the requester "would be a viewer if it existed", which for a family-class document depended on a row the requester might not be allowed to know about: Ravi asking for Priya's RC got "not linked" when there was none and "can't show that" when Priya had narrowed it, so the two answers together disclosed the hidden document. The rule now uses only who is asking about whom:

| Requester and holder | Can anything of this holder be hidden from this requester? | No viewable document of that type → |
|---|---|---|
| Requester **is** the holder | No | VAULT_002 (with the offer to link) |
| Holder is a dependent and the requester is one of the holder's **current guardian viewers** (§4.6, from `v_guardians` and the fallback rule) | No: `guardians` and `family_adults` both include them | VAULT_002 |
| Anyone else (another adult's documents of **any** class; a dependent the requester is not a guardian of) | Yes | VAULT_006, always |

Implementation rule: the branch is chosen first; then one query returns the documents of that type and holder **that the requester may see**; an empty result gives the branch's code. There is no code path that loads a hidden row and then decides what to say, so the two cases cannot differ in fields, status or, beyond noise, time. `LIST_DOCUMENTS` needs no such rule: it returns what is visible and never says what is not. The matrix test covers hidden-versus-absent for a narrowed family-class document (RC, insurance), for personal documents, and for a dependent's document seen by a non-guardian adult.

### Success metrics

- **Completion rate:** ≥ 90 % of `SHOW_DOCUMENT` requests by permitted roles end in a rendered document without correction.
- **DPI reliability:** ≥ 99 % against the simulator in normal mode; degraded-mode message shown in 100 % of injected outages.
- **Family NPS:** collected with the demo testers only.
- **Zero-bytes invariant:** the CI check of §4.5 passes on every PR (0 violations).
- **Block correctness:** 100 % of minor, staff and public-surface attempts in the test suite are refused before dispatch and appear in the kernel audit log; none reaches the module.
- **Visibility correctness:** a generated matrix test (every role × class × visibility × holder type) shows 0 leaks across `SHOW_DOCUMENT`, `LIST_DOCUMENTS`, `LINK_DOCUMENT` duplicates, reminder text and error messages; for every requester/holder pair in the VAULT_006 branch the response envelope is byte-identical (apart from `request_id` and metrics) for "exists but hidden" and "does not exist", including narrowed family-class documents. The reduced admin reminder copy is tested separately against its own policy (§4.6) and is the only permitted difference.
- **Consent binding:** tests for §4.7: a shared document is fetched with the holder's handle; an expired holder consent blocks every viewer; an admin who is not the proxy cannot cause a consent record for a managed person to be created; a link whose account owner is not the actor is refused.

## 9. GTM & Operations

- **What this module demonstrates (portfolio mode):** "sync, not duplicate" privacy design; consent-gated reads with CONSENT_REVERIFY; the public-surface rule; a Level 0 human decision (age-18 upgrade) that an agent proposes and never executes.
- **Launch plan:** delivered as the foundation with vertical slice 1 (Finance) because Finance and Health declare it in `data_dependencies`; its own demo moment is Scenario 1 in the second half of the demo script (docs/strategy/GTM_Plan.md).
- **Phasing:** Phase 2 of the Roadmap: manifest, schema, `LIST_DOCUMENTS`, boot duties. Phase 3: `LINK_DOCUMENT`, `SHOW_DOCUMENT`, access log, milestone sweep, expiry reminders.

## 10. Open Issues & Q&A

### Open issues

| ID | Issue | Priority | Resolution path |
|---|---|---|---|
| OI-1 | ~~Who receives expiry reminders, and when?~~ **Ruled 2026-09-17:** default is the holder (if an adult) and the admins at 30 and 7 days before expiry; for minor, managed and passive holders, the admins and the primary proxy only. Recipients and lead times are **family-adjustable settings**; how far they can be adjusted is designed when this section is detailed. | CLOSED | Decision Log 2026-09-17. |
| OI-2 | ~~The purpose registry's data types for `DIGILOCKER_DOCUMENT` do not mention date of birth.~~ **Ruled 2026-09-21:** disclose it. CM v1.4 §3.2, disclosure 2.0.0 (material change); date of birth in memory only; `milestone_at` treated as sensitive. | CLOSED | Decision Log 2026-09-21. |
| OI-3 | ~~No scheduling contract; Vault audit codes not registered.~~ **Closed 2026-09-21:** `scheduled_jobs` (MR v1.2 §6.6); five `VAULT_*` codes with typed payloads (DM v1.4 §6, §6.1). | CLOSED | WP-11. |
| OI-4 | No DigiLocker circuit-breaker values exist in RB §8.2; this PRD borrows the AA defaults (3 failures → 30 min). | LOW | RB v1.3 when a second DigiLocker consumer appears. |
| OI-5 | Staff need specific documents (the RC for the driver). Needs a per-document, time-boxed sharing grant. | LOW (P2) | Separate PRD section in Phase 2; do not solve with a role exception. |
| OI-6 | ~~Co-owner model.~~ **Ruled 2026-09-17:** default visibility by document class — family documents (RC, insurance, property) are visible to admins and members; personal identity documents (PAN, passport, licence) are private to the holder. The holder can change it per document; the degree of customisation (per class, per person, admin overrides) is designed when `SHOW_DOCUMENT` is detailed. Managed, elder and passive holders' documents follow the admins (and the primary proxy for a managed profile). **Refined the same day:** a minor's documents follow the minor's parents and any marked legal guardian, not the admins as such (admins only as a fallback when the minor has neither in the family). | CLOSED | Decision Log 2026-09-17; affects `SHOW_DOCUMENT` analysis logic and adds a `visibility` attribute to the document metadata in PRD v0.2. |
| OI-7 | Break-glass: an adult is in hospital and the other needs their PAN or insurance-linked id. Phase 1 has no admin override of `holder_only`. | MEDIUM (P2) | Design with the threat model: a time-boxed, passkey-gated, loudly audited override that notifies the holder; never silent. Until then the answer is "share in advance". |
| OI-8 | ~~Per-family settings convention.~~ **Closed 2026-09-21:** each module owns a typed `family_settings` table; no settings service (MR v1.2 §6.6, DM v1.4 §9.3). | CLOSED | WP-11. |
| OI-9 | ~~The simulator spec's DigiLocker table lacked a revoked-document response and a second account's issued list.~~ **Closed 2026-09-17:** added to Tech_Spec_Simulator_Architecture §5.4 (rows D4, D8) in PR #20. | CLOSED | — |
| OI-10 | Who consents to processing an **elder's** or a **passive** person's documents? CM v1.4 covers adults (self), children (parent or guardian) and managed profiles (proxy) only. | MEDIUM | §4.7 takes the narrow reading: an elder consents for themselves on their own device; passive holders are out of Phase 1. Raise with the threat model; a CM rule would be a version bump. |

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
- [x] Independent review by Codex (2026-09-21, changes required); all 8 findings applied in v0.3; OI-2, OI-3, OI-8 closed.
- [ ] Codex's targeted re-review of v0.3.
