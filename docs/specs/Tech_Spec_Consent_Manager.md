# Tech Spec: Consent Manager

_DPDP-native consent framework, purpose registry, CONSENT_REVERIFY, DPI adapters, expiry watchdog, revocation, webhook security_

> **Status:** v1.4 — REVISION IN REVIEW (Codex round-2 findings applied to §2.2, §2.5, §2.6, §3.2, §4.2–4.4, §5.2, §7.2; awaiting Codex's targeted re-review; the rest is the frozen v1.2 text) · **Author:** Shantanu Chaudhary (Lead Product Architect) · **Last content change:** 2026-09-21
> **Canonical copy.** Converted to Markdown on 2026-09-16 from `Tech_Spec_Consent_Manager_v1.1.docx` (original kept in `archive/originals/`). Content is unchanged; only formatting was converted. Superseded versions in the archive: `Tech_Spec_Consent_Manager_v1.0.docx`.
> **Cited elsewhere as:** Consent Manager v1.4, Tech_Spec_Consent_Manager v1.1, Consent_Manager v1.1, CM §n.

### Document Governance

| Version | Date | Description of Change | Author |
|---|---|---|---|
| v1.0 | 2026-02-21 | Initial release. Full consent framework: DPDP-native first-party consent, purpose registry, consent_records schema, parental consent for minors, data portability, breach protocol, CONSENT_REVERIFY mechanics, AA and ABHA DPI adapters, expiry watchdog, revocation propagation, webhook HMAC security, regulation-agnostic extension points. | Shantanu Chaudhary |
| v1.1 | 2026-02-21 | Hardening. Five fixes applied after first independent review: (1) §4.1 PostgreSQL trigger enforcing consent_handle_id NOT NULL for DPI purpose codes — prevents silent bypass of external consent gate at CONSENT_REVERIFY Check 2; (2) §2.2 deletion sequence now explicitly aborts active supervisor_sessions to prevent orphaned EXECUTION sessions after account deletion; (3) §7.3 renewal flow now inherits fetch_count_today from old handle when revoked within 1 hour — prevents RBI rate-limit evasion via renewal spam; (4) §4.6 consent_ui_disclosures table added — consent_ui_version on consent_records now references an auditable canonical record; (5) §9.3 Step 4 webhook DB writes wrapped in explicit BEGIN/COMMIT — prevents partial state on audit_log failure after consent_handles UPDATE. | Shantanu Chaudhary |
| v1.2 | 2026-09-17 | Alignment release, no behavioural change: (1) `session_status` → `fsm_state` (Data Model v1.3 §3.7); (2) role values written lowercase as stored (`minor`, `admin`, `member`) and the minor check reads `users.role`, not `family_relationships.role` (Inconsistency Register item 3); (3) `offline_task_queue.status = 'cancelled'` is now a valid value (Data Model v1.3 §3.9; item 10); (4) `consent_handles.provider` now includes 'ONDC' so ONDC_ADDRESS_SHARE can carry a handle as the enforce_dpi_handle trigger requires; (5) the `consent_records` and `consent_ui_disclosures` DDL, the trigger, and the audit action codes of §4.4 are now also in Data Model v1.3 (§3.12–3.13, §6); the Data Model is the DDL source and this document remains the behavioural authority. Note the expiry index is named `idx_consent_records_expiry` there. | Shantanu Chaudhary (with Claude Code) |
| v1.3 | 2026-09-17 | One addition by founder ruling (Health PRD OI-2): §2.6 Proxy Consent for Managed Profiles. New nullable column `consent_records.proxy_consent_user_id` (§4.1), its index, the insert-time rule, and the audit action `PROXY_CONSENT_GRANTED` (§4.4). No change to any existing behaviour; minors still use `parental_consent_user_id`. Goes to Codex review round 2 together with Data Model v1.3, then re-freezes. | Shantanu Chaudhary (with Claude Code) |
| v1.4 | 2026-09-21 | Codex review round 2 (issue #10 findings 5–10, 14, 15, 17; PR #25 findings 4 and 6; PR #20 finding 3) and founder rulings of 2026-09-21. (1) §2.2: deletion never aborts an EXECUTION session, and the purge empties the `users` row in place instead of deleting it (Data Model v1.4 §7.1). (2) §2.5: child protections follow `users.is_child`, not the role, so a managed infant keeps them. (3) §2.6 rewritten: availability predicate for the primary proxy; the rule is checked at insert, at pending→active and at renewal, under the family lock; actor and subject are separate throughout; ordinary replacement of a proxy versus deletion of the granting proxy; re-confirmation state `proxy_reconfirm_required` with its own clearing event `PROXY_CONSENT_RECONFIRMED`. (4) §3.2: DIGILOCKER_DOCUMENT discloses the transient use of date of birth and the stored milestone (material change, disclosure 2.0.0); new first-party purpose HEALTH_MEDICATION_REMINDERS. (5) §4.2–4.4: grant writes `proxy_consent_user_id` and both audit rows through the audit protocol; withdrawal authorises the actor against the subject; disclosure row must exist before the grant. (6) §5.2: Check 0 (live subject) and Check 1b (proxy re-confirmation); the limit of flag-driven polling stated. (7) §7.2: notices for a dependent go to the current primary proxy or the guardians. | Shantanu Chaudhary (with Claude Code; review by Codex) |

> ✅ STATUS: HARDENED v1.1 — Architecture Frozen
> This document is the authoritative specification for all consent infrastructure in FamilyLifeOS.
> v1.1 passed two independent reviews. Five hardening fixes applied:
>   (1) DB-layer DPI handle enforcement trigger (§4.1)  (2) Deletion + session abort (§2.2)
>   (3) Rate-limit inheritance on renewal (§7.3)  (4) consent_ui_disclosures table (§4.6)
>   (5) Webhook transaction atomicity (§9.3)
> Scope: every data collection or access event in the product — not just DPI calls.
> The consent_records and consent_ui_disclosures tables are schema additions to Data_Model_Schema v1.2.1
> (backward-compatible). DPI adapters (AA, ABHA) translate first-party consent to external handle
> formats — they do not define consent independently.
> Change-control: §3 (purpose registry), §4 (consent_records/disclosures schema), and §9 (webhook
> security) require a new version number and review before any implementation changes.

## Table of Contents

- **1. Scope & Design Philosophy** — What this spec owns • What it does not own • 6 core principles • Architecture model
- **2. DPDP Act 2023 Obligations (v1 Implementation)** — Consent requirements • Right to erasure • Data minimisation • Breach notification • Minor protection
- **3. Purpose Registry** — Every data collection/access event mapped • Purpose codes • Lawful basis • Retention periods • Jurisdiction fields
- **4. First-Party Consent Framework** — consent_records schema • consent_ui_disclosures table • Grant flow • Revoke flow • Audit trail • Parental consent for minors • Data portability
- **5. CONSENT_REVERIFY: FSM Integration** — What G5 checks exactly • State transition matrix • TTL policy • revalidation_required flag • Exit paths
- **6. DPI Adapter Layer** — AA adapter (Sahamati/RBI) • ABHA adapter (ABDM) • DigiLocker adapter • How first-party maps to external handle
- **7. Consent Expiry Watchdog** — Daily cron spec • 7-day advance notification • Renewal flow • Escalation for ignored expiry
- **8. Revocation Propagation** — User-initiated revocation • External revocation (DPI webhook) • Table update order • Healer coordination
- **9. Webhook Security: HMAC Validation** — Attack surface • Sahamati webhook spec • HMAC-SHA256 validation algorithm • Replay prevention • Failure handling
- **10. Regulation-Agnostic Extension Points** — Jurisdiction field • Pluggable enforcement rules • What adding GDPR looks like • What is not built in v1
- **11. Canonical Flow: Priya Connects HDFC Bank (AA Consent)** — Step-by-step end-to-end • Happy path • Failure modes • Audit log entries
- **12. Q&A** — Engineering, Legal/Compliance, and Operations questions

## 1. Scope & Design Philosophy

### 1.1 What This Spec Owns

The Consent Manager is not a DPI integration module. It is the privacy infrastructure layer of FamilyLifeOS. Every event in which the system collects data from a user, processes data about a user, or accesses data from an external source on a user's behalf requires a consent basis tracked by this spec. This includes:
- Voice recordings captured via Bhashini (even ephemeral ones processed for intent)
- OCR of physical documents or photos containing PII
- AA financial data fetches (bank balances, transaction history)
- ABHA health record access (prescriptions, diagnostics, vitals)
- DigiLocker document retrieval (Aadhaar, PAN, driving licence)
- Device registration (push tokens, device fingerprints)
- Family member data shared across the family graph (one member's data visible to another role)
- ONDC seller interactions where family address is transmitted
- Any analytics or behavioural data collected for product improvement

### 1.2 What This Spec Does Not Own

- Payment execution safety — see Tech_Spec_Financial_Transaction_Safety v1.1
- RBAC role definitions — see PRD v2.1 and Data_Model_Schema v1.2.1
- DPI rate limiting — see Runbook_DPI_Rate_Limits.md (P0, Week 2)
- Security threat modelling — see Security_Threat_Model.md (late-P0, Week 3)
- Module-specific data schemas (Finance tables, Health tables) — see respective module PRDs

### 1.3 Core Design Principles

> ✅ DESIGN PRINCIPLE: Consent-first: No data is collected, accessed, or processed without a recorded consent basis. This is enforced architecturally — the Consent Manager is on the critical path of every DPI call and every data collection event, not a compliance wrapper added later.

> ✅ DESIGN PRINCIPLE: Privacy by Design (GDPR Article 25, adopted regardless of jurisdiction): Consent infrastructure is built into the system from the start. Data minimisation is enforced at collection time. The system collects the minimum data necessary for a declared purpose — and no more.

> ✅ DESIGN PRINCIPLE: Purpose limitation (strict): Consent granted for Purpose A cannot be silently reused for Purpose B. Each consent record is tied to a specific purpose_code. A new use case requires a new consent event.

> ✅ DESIGN PRINCIPLE: Regulation-agnostic architecture: The consent framework is designed so that adding a new jurisdiction (GDPR for EU users, PDPA for Singapore users) is configuration — new rows in the purpose_registry with jurisdiction-specific retention periods and lawful bases — not code refactoring. DPDP Act 2023 is the only jurisdiction implemented in v1.

> ✅ DESIGN PRINCIPLE: Human sovereignty: Consent is always granted by a human, never assumed by the system. The Supervisor may prompt for consent renewal; it cannot grant consent on the user's behalf.

> ✅ DESIGN PRINCIPLE: Audit completeness: Every consent grant, renewal, revocation, and expiry is written to the audit_log. The consent trail is a legal record, not a debug log.

### 1.4 Three-Layer Architecture

The Consent Manager operates as three distinct layers. Understanding this model is essential before reading the rest of the spec:

```text
┌────────────────────────────────────────────────────────────────┐
│  LAYER 1: FamilyLifeOS First-Party Consent Framework           │
│                                                                │
│  purpose_registry  — every data event mapped to a purpose      │
│  consent_records   — user grants/revocations per purpose       │
│  audit_log entries — every consent event recorded              │
│  DPDP obligations enforced at this layer                       │
│  Jurisdiction fields enable future GDPR/PDPA config            │
└────────────────────────┬───────────────────────────────────────┘
                         │ translates first-party consent TO
                         ▼ external handle format
┌────────────────────────────────────────────────────────────────┐
│  LAYER 2: DPI Adapter Layer                                    │
│                                                                │
│  AA Adapter   — maps to Sahamati consent handle format         │
│  ABHA Adapter — maps to ABDM consent artefact format           │
│  DigiLocker Adapter — maps to OAuth access_token reference     │
│  Each adapter translates; does not define consent independently │
└────────────────────────┬───────────────────────────────────────┘
                         │ holds references (not the handles)
                         ▼
┌────────────────────────────────────────────────────────────────┐
│  LAYER 3: External Consent Handles                             │
│                                                                │
│  AA: consentHandle UUID (Sahamati network)                     │
│  ABHA: HIU consent request ID (ABDM)                           │
│  DigiLocker: OAuth access_token reference ID                   │
│  FamilyLifeOS holds references in consent_handles table;       │
│  raw handles are never stored in plaintext in the app DB       │
└────────────────────────────────────────────────────────────────┘
```

> ℹ INFO: The consent_handles table (Data_Model_Schema v1.2.1 §3.5) is the Layer 3 reference store. The consent_records table (new, defined in §4 of this spec) is the Layer 1 first-party record. They are related but distinct. Every consent_handle must have a corresponding consent_record. Not every consent_record has a consent_handle (first-party consents like voice processing do not require an external DPI handle).

## 2. DPDP Act 2023 Obligations (v1 Implementation)

### 2.1 Consent Requirements (Section 6, DPDP Act)

> ⚖ DPDP ACT 2023: Consent must be free, specific, informed, unconditional, and unambiguous. Consent must be given for a specific purpose. The Data Principal (user) must be able to withdraw consent at any time. A record of consent must be maintained.

How FamilyLifeOS satisfies this:

| DPDP Requirement | FamilyLifeOS Implementation | Where Specified |
|---|---|---|
| Free | No service is withheld for refusing a non-essential consent (e.g., analytics). Core functionality consents are clearly distinguished from optional ones in the purpose_registry. | §3 purpose_registry: essential flag |
| Specific | Each consent is tied to exactly one purpose_code. Consent for 'AA_BALANCE_FETCH' does not cover 'AA_TRANSACTION_HISTORY'. Purpose codes are granular by design. | §3 purpose registry |
| Informed | Consent UI must display: purpose plain-text description, data types collected, retention period, and how to revoke — before the user confirms. Language is in the user's preferred language (Bhashini). | §4.2 consent grant flow |
| Unconditional | Consent is not bundled with other agreements. Each purpose_code is presented separately with individual accept/decline. | §4.2 grant flow |
| Unambiguous | Explicit affirmative action required (biometric or PIN confirm). No pre-ticked boxes. No silence-as-consent. | §4.2 grant flow |
| Specific purpose | purpose_code is written to consent_records at grant time and cannot be changed post-grant. A new use requires a new consent event. | §4.1 schema |
| Withdrawal | Any user can revoke any consent from their profile. Revocation propagates within 15 minutes. No friction or waiting period. | §8 revocation |
| Record of consent | Every grant and revocation is written to audit_log with canonical hash chain. The consent_records table is the primary record. | §4.1 schema, §4.4 audit trail |

### 2.2 Right to Erasure (Section 12, DPDP Act)

When a user requests account deletion, the following sequence must complete within 24 hours (our implementation exceeds the 72-hour DPDP mandate):

```text
DELETION REQUEST SEQUENCE (atomic, must complete in order):

T+0:  User submits deletion request (requires biometric confirmation)
      All of the following must execute in a SINGLE TRANSACTION:
      → SET users.deleted_at = NOW()
      → SET consent_records.status = 'revoked' for ALL records (user's own)
      → SET consent_records.revoked_at = NOW() for all active records
      → UPDATE supervisor_sessions
          SET fsm_state = 'ABORTED'
          WHERE user_id = $uid
            AND fsm_state NOT IN ('SUCCESS_CONFIRMATION','FAILED','ABORTED','EXECUTION');
        -- v1.4: every non-terminal session is aborted EXCEPT one in EXECUTION. Such a session may
        -- already have moved money; only the Healer may take it out of EXECUTION (FTS §6–7,
        -- Data Model v1.4 §4.3, §7.4). v1.1 aborted it here "so the audit chain is not orphaned";
        -- that concern is gone because the users row is never deleted (see T+24h), and aborting
        -- hid a possibly-paid bill from the only job that reconciles it. The Healer finishes the
        -- books as SYSTEM_ACTOR_UUID; it needs no consent of the deleted user, because a status
        -- query on a submitted payment reads the biller network, not the user's bank.
      → Records this user granted AS A PROXY for a managed profile are NOT revoked:
          SET proxy_reconfirm_required = TRUE  (§2.6.4)
      → Write audit_log: ACCOUNT_DELETION_REQUESTED
        (This is the last audit entry written by the user's own action.)
      COMMIT;

      POST-TRANSACTION (outside the transaction — DPI revocation is network I/O):
      → REVOKE all DPI consent_handles immediately (AA, ABHA, DigiLocker)
         POST revocation to each provider's API
         (DO NOT wait for 24h window — DPI revocation is immediate)
         IF DPI revocation fails: log warning, proceed. User's right to delete cannot
         be blocked by external API failure. Healer will retry DPI revocation.

T+0 to T+24h: Soft-delete window
      → User can cancel deletion within this window (Admin-only action)
      → All sessions ABORTED, except a payment in EXECUTION that the Healer is reconciling
      → No new DPI calls can be made (all consents revoked)
      → Family still intact if other members exist

T+24h: Nightly purge job (01:00 IST)
      → v1.4 (founder ruling 2026-09-21): ERASE THE PERSON, KEEP AN EMPTY PLACEHOLDER.
        Data Model v1.4 §7.1 is the procedure: skip the user tonight if a session is still in
        EXECUTION; delete the personal child rows by name (devices, relationships, proxy
        assignments, consent handles, module data); empty the users row in place
        (name 'Deleted user', phone/email NULL, purged_at set); keep audit_log rows and
        consent_records rows as evidence (granted_scope reset to '{}').
      → Write audit_log: DATA_DELETION_COMPLETED (actor SYSTEM_ACTOR_UUID) in the same transaction
      → If user was sole Admin: family is dissolved, all members notified
```

> ⚠ WARNING: DPI consent revocation (AA, ABHA) must happen at T+0 — not at the 24-hour purge. A user who has requested deletion must not continue to have active financial or health data access. The soft-delete window is for FamilyLifeOS data only, not for external DPI consent handles.

### 2.3 Data Minimisation

The system must collect only what is necessary for the stated purpose. This is enforced through the purpose_registry's data_types_collected field. At collection time, the agent handling the data must validate that the data it is about to process is listed in the relevant purpose's data_types_collected. If it is not listed — the operation must be blocked and the Supervisor must be notified.
- Voice data: processed in-memory for intent extraction. Transcript is retained only if the user explicitly saves it. Raw audio is never written to disk.
- OCR data: structured fields extracted (date, amount, name). Full image is stored in the encrypted vault only if the user confirms. Raw image is not retained in the database.
- AA financial data: account balance and relevant transactions are fetched. Full transaction history is not fetched unless the purpose_code explicitly requires it.
- ABHA health data: only the hi_types listed in the consent artefact's data_scope are fetched. A prescription consent does not return diagnostic reports.

### 2.4 Data Breach Notification

Under DPDP Act 2023, users must be informed of a data breach 'without undue delay' (interpreted as within 72 hours of discovery). FamilyLifeOS adopts a 72-hour internal response protocol regardless of regulatory mandate, because it forces a pre-built breach response runbook rather than improvising at 2am.

| Time After Discovery | Required Action | Owner |
|---|---|---|
| T+0 to T+2h | Confirm breach is real. Identify affected families and data types. Lock affected DPI consents (revoke all active consent_handles for affected users). | Founder |
| T+2h to T+24h | Assess blast radius. Determine if external DPI data was accessed. Notify CERT-In if breach involves 'sensitive personal data' (financial, health). | Founder + Legal |
| T+24h to T+72h | Push in-app notification to all affected users. Plain-language explanation of what was accessed, what was done about it, and what user should do. | System (push notification) |
| T+72h | File formal report with Data Protection Board of India when regulatory framework is notified. (Board not yet operational as of Feb 2026 — monitor for activation.) | Founder + Legal |

### 2.5 Parental Consent for Minors (Section 9, DPDP Act)

> ⚖ DPDP ACT 2023: Processing of personal data of a child (under 18) requires verifiable parental consent. The Data Fiduciary must not undertake processing that is detrimental to the child or involves tracking, behavioural monitoring, or targeted advertising.

In FamilyLifeOS a **child** is any user with `users.is_child = TRUE` (Data Model v1.4 §3.2): every `minor`, and any `managed` profile marked as a child (an infant has no login, so it cannot hold the minor role). v1.4 moved every rule in this section from the role to that marker (founder ruling 2026-09-21); where the text below says Minor, read child. Children require specific handling:
- Any consent_record for a Minor must have parental_consent_user_id set to a verified Adult or Admin in the same family. The system cannot grant consent on behalf of a Minor without this field populated.
- The Minor's RBAC already restricts access to Vault and Wealth pillars (PRD v2.1). The consent framework adds: no consent for analytics, no consent for behavioural data collection, no consent for any DPI that would create a financial or health record in the Minor's name without explicit Admin approval.
- When a Minor turns 18: the Supervisor detects this via birth certificate data in the Vault (Scenario 5 in PRD v2.1). The Admin is prompted to confirm role upgrade. Upon confirmation, existing consents granted by the parent are migrated to the user's own consent record. The user receives a notification explaining what data exists and that they can revoke any consent.
- Data collected about a Minor while they were under 18 is treated as especially sensitive. It cannot be shared, exported, or used for any purpose beyond the stated family management purpose without a new consent event from the (now adult) user.

```text
-- Enforced at consent_records insert time (application layer, not DB constraint):

IF subject.is_child:                                   # v1.4: was `user.role == 'minor'`
  IF consent_record.parental_consent_user_id IS NULL:
    RAISE ConsentError('A child's consent requires verified parental_consent_user_id')
  # v1.4: the consenting adult must be this child's parent or legal guardian, live, same family.
  g = SELECT 1 FROM v_guardians
      WHERE dependent_user_id = subject.user_id AND guardian_user_id = parental_consent_user_id
        AND family_id = subject.family_id AND basis IN ('parent','legal_guardian')
  IF g IS NULL:
    # Fallback only when the child has NO live parent or guardian in the family: a live admin.
    IF EXISTS(v_guardians rows for subject with basis IN ('parent','legal_guardian'))
       OR NOT is_live_admin(parental_consent_user_id, subject.family_id):
      RAISE ConsentError('Parental consent must come from the child's parent or legal guardian')
  IF purpose_registry[consent_record.purpose_code].minor_allowed == False:
    RAISE ConsentError('This purpose is not permitted for a child')
# A managed child ALSO passes through §2.6: both columns are set, and may name the same person.
```

### 2.6 Proxy Consent for Managed Profiles (added in v1.3, rewritten in v1.4)

A managed profile (users.role = 'managed'; Nani in the Sharma seed) is a person who does not operate the product themselves: usually an adult who cannot or will not, sometimes an infant. DPDP treats a lawful guardian's consent on behalf of a person who cannot consent for themselves like parental consent; FamilyLifeOS records it separately from parental consent so the audit trail says exactly who consented for whom and in what capacity. v1.3 said "a managed profile is an adult"; that was wrong (Data Model §3.2 has always allowed infants) and v1.4 removes it: a managed **child** gets this section **and** §2.5.

Two people are involved in every flow below and they are never the same variable: the **actor** (authenticated, holds the passkey, `session.user_id`) and the **subject** (whose data it is, `consent_records.user_id`). The client may send `acting_as = <subject>`; the server verifies it against `proxy_assignments` and never trusts it.

#### 2.6.1 Who may grant

- The subject's **primary proxy** (proxy_assignments.proxy_rank = 'primary', Data Model §3.4) grants with their own biometric or PIN (§1.3 still holds: only a human grants consent). `proxy_consent_user_id` = that proxy.
- The **secondary proxy** may grant only when the primary is **unavailable**, defined exactly as: the primary's `users` row has `deleted_at IS NOT NULL`, or there is no primary assignment row. Nothing else counts. There is no "suspended" account state in the Data Model, so v1.3's "deleted or suspended" is reduced to what exists; if a suspension state is ever added, it is added to this predicate by a version bump. The audit details then carry `"proxy_rank":"secondary"`.
- An **admin who is not an assigned proxy cannot grant**, link a document that needs the subject's consent, or renew. Being admin gives the right to assign proxies (PROXY_ASSIGNED, Level 0), not to consent for the person. An admin who needs the subject's data either already has a valid existing consent of the subject to rely on, or the system prompts the authorised proxy.
- A managed adult never carries parental_consent_user_id. A managed child carries both columns (§2.5). A `minor` never carries proxy_consent_user_id. An ordinary adult carries neither.

#### 2.6.2 When the rule is checked

Not only "at insert time" (v1.3). The check below runs, inside one transaction that first takes the family lock (`SELECT 1 FROM families WHERE family_id = $1 FOR UPDATE`, the same lock the proxy-assignment and role-change services take, Data Model §4), at each of these moments:

1. INSERT of a consent_record for a managed subject (status `pending` or `active`);
2. the `pending` → `active` transition (the DPI redirect may return minutes later; the assignment may have changed meanwhile);
3. renewal (§7.3), which is a new grant;
4. re-confirmation (§2.6.4).

```text
check_proxy_grant(actor, subject, record):            # inside the family-locked transaction
  REQUIRE subject.deleted_at IS NULL AND subject.role == 'managed'
  REQUIRE actor.deleted_at IS NULL AND actor.role IN ('admin','member')
          AND actor.verification_status IN ('otp_verified','kyc_verified')
  REQUIRE actor.family_id == subject.family_id == record.family_id
  pa = SELECT * FROM proxy_assignments
       WHERE managed_user_id = subject.user_id AND proxy_user_id = actor.user_id
         AND family_id = subject.family_id
  IF pa IS NULL: RAISE ConsentError('Proxy consent must come from an assigned proxy in the same family')
  IF pa.proxy_rank == 'secondary' AND primary_proxy_is_available(subject):
     RAISE ConsentError('Secondary proxy may consent only when the primary proxy is unavailable')
  REQUIRE record.proxy_consent_user_id == actor.user_id      # the column names the human who confirmed
  IF subject.is_child: run the §2.5 check as well
  IF NOT subject.is_child AND record.parental_consent_user_id IS NOT NULL:
     RAISE ConsentError('parental_consent_user_id is for children only')

primary_proxy_is_available(subject):
  RETURN EXISTS (SELECT 1 FROM proxy_assignments pa JOIN users p ON p.user_id = pa.proxy_user_id
                 WHERE pa.managed_user_id = subject.user_id AND pa.proxy_rank = 'primary'
                   AND pa.family_id = subject.family_id AND p.deleted_at IS NULL)
```

A failed check at moment 2 leaves the record `pending`, revokes the just-issued external handle (§4.3 Step 3 path), and tells the current primary proxy that a consent request is waiting for them. The grant writes `CONSENT_GRANTED` and `PROXY_CONSENT_GRANTED` through the audit protocol (Data Model v1.4 §3.18) in the same transaction as the record; both rows carry `user_id` = the actor and `details.subject_user_id` = the subject.

#### 2.6.3 The primary proxy is replaced (ordinary hand-over)

Ravi takes over from Priya; Priya is still in the family. Existing consents **stay valid until they expire**; nothing is flagged; no one has to do anything. From the next watchdog run, renewal notices go to the new primary (§7.2). Medication reminders and other processing continue unchanged. Withdrawal rights move with the role: the new primary can withdraw, the former primary cannot.

#### 2.6.4 The granting proxy's account is deleted (re-confirmation)

Different event, different rule, because the person who vouched for the consent is gone.

- At T+0 of the proxy's deletion (§2.2) every active consent_record with `proxy_consent_user_id` = the deleted user gets `proxy_reconfirm_required = TRUE` (Data Model v1.4 §3.12). The records are **not** revoked and their DPI handles are **not** touched: the consent was validly given for the subject, and the founder's decision stands that a dependent's medication reminders must not stop silently.
- This is **not** `consent_handles.revalidation_required`. v1.3 reused that flag, which does not exist for first-party records and is cleared by §5.2 Check 2 when the *provider* says ACTIVE; a provider's status says nothing about whether the new proxy has looked at the consent.
- While the flag is set: processing of data **already held** under the record continues (reminder schedules, stored documents' metadata). **No new external fetch** passes CONSENT_REVERIFY (§5.2 Check 1b, code CONSENT_009); the expiry watchdog still runs on the record.
- Who clears it: the subject's **current primary proxy** only (or the secondary under the §2.6.1 unavailability rule), by viewing the same disclosure the record points at and confirming with biometric or PIN. The transaction runs `check_proxy_grant` (moment 4), sets `proxy_reconfirm_required = FALSE`, `proxy_reconfirmed_by`, `proxy_reconfirmed_at`, and appends `PROXY_CONSENT_RECONFIRMED`. `proxy_consent_user_id` keeps naming the original grantor: history is not rewritten. The Supervisor, the Healer, an admin who is not the proxy, and a provider status call can never clear it.
- The new primary may instead withdraw (§4.3). Doing nothing is allowed: the record simply expires on its date.
- If the managed profile has no available proxy at all, the admins are alerted (Data Model §4.3, "without a caregiver"); assigning a proxy is the only way forward.
- The deleted proxy's `users` row is emptied, not removed (Data Model v1.4 §7.1), so `proxy_consent_user_id` stays a valid reference and the purge is not blocked by it.

#### 2.6.5 Withdrawal and renewal

The primary proxy or any admin can withdraw a managed profile's consent (§4.3 flow, actor recorded). Withdrawing reduces processing, so it is deliberately open to admins; granting is not. Renewal is a grant: §2.6.1 applies.

## 3. Purpose Registry

### 3.1 Overview

The purpose_registry is the authoritative catalogue of every data event in FamilyLifeOS. It is a static configuration (not a database table — it changes only with new product features, not with user actions). Each entry defines: what data is being collected or accessed, why, for how long it can be retained, which jurisdictions require explicit consent for it, and whether it is permitted for Minor users.
Every consent_record written to the database must reference a valid purpose_code from this registry. If a new feature collects data not covered by an existing purpose_code, a new purpose_code must be added to this registry and reviewed before the feature ships.

> ⚠ WARNING: The purpose registry is not merely documentation. It is enforced: any code path that writes a consent_record with an unknown purpose_code must throw a ConsentError that surfaces to the Supervisor as a system alert. Unknown purpose = blocked operation.

### 3.2 Purpose Registry (v1 — All FamilyLifeOS Data Events)

| Purpose Code | Plain-text Description | Data Types Collected/Accessed | Retention (DPDP) | DPI Required | Minor Allowed | Essential |
|---|---|---|---|---|---|---|
| AA_BALANCE_FETCH | Fetch bank account balance to verify funds before a bill payment | Account balance (amount only). No transaction history. | 15 min (TTL per FSM spec) | AA | No | Yes |
| AA_TRANSACTION_HISTORY | Fetch bank transaction history for financial health dashboard | Transaction list: date, amount, counterparty name | 1 year (RBI mandate, re-consent after) | AA | No | No |
| ABHA_PRESCRIPTION | Access prescriptions from linked hospitals for medication reminders | Prescription: drug name, dosage, prescribing doctor | 7 years (MCI guidelines) | ABHA | With parental consent | No |
| ABHA_DIAGNOSTICS | Access diagnostic reports (blood tests, scans) for health tracking | Diagnostic report: test name, values, reference range | 7 years | ABHA | With parental consent | No |
| ABHA_VITALS | Access vitals from wearable devices linked via ABHA | Heart rate, SpO2, blood pressure, steps | 1 year (re-consent after) | ABHA | With parental consent | No |
| DIGILOCKER_DOCUMENT | Retrieve a specific government document (Aadhaar, PAN, driving licence) from DigiLocker, and work out dates the family should know about (renewals, a child turning 18) | Document type, document number (redacted), issue date, expiry date. **v1.4:** the holder's date of birth is read from the document **in memory only** to work out milestones and is never stored, logged or sent to a hosted LLM; what is stored is the milestone type and the date it falls on | Duration of document validity; milestones are deleted when the document is unlinked | DigiLocker | With parental consent | No |
| HEALTH_MEDICATION_REMINDERS | Keep a medication schedule for a family member and remind the right people when a dose is due or missed (**v1.4, first-party**) | Medicine name and dose timing as entered by the family or taken from a prescription already fetched under ABHA_PRESCRIPTION; dose events (taken, skipped, missed); who was notified | While the schedule is active + 1 year | None | With parental consent | No |
| VOICE_INTENT_PROCESSING | Process voice input to extract user intent via Bhashini | Voice transcript (text only). Raw audio not retained. | Session only (deleted on session end) | Bhashini | Yes (parental consent for Minor) | Yes |
| OCR_DOCUMENT_PROCESSING | Extract structured data (dates, amounts, names) from a photo of a physical document | Extracted fields only. Full image retained in vault only if user confirms. | Image: vault retention. Extracted fields: purpose-specific. | None (in-house OCR engine) | With parental consent | No |
| DEVICE_REGISTRATION | Register device for push notifications and surface-context detection | Device ID, push token, OS type, surface type (public/private) | Duration of device registration | None | With parental consent | Yes |
| FAMILY_DATA_SHARING | Share one family member's non-sensitive data with other members per RBAC rules | Name, schedule, task status — never financial or health data cross-role | Active family membership | None | Yes | Yes |
| ONDC_ADDRESS_SHARE | Share family delivery address with ONDC seller for an order | Delivery address (street, city, pincode) | Duration of order + 30 days for dispute | ONDC | With parental consent | No |
| PRODUCT_ANALYTICS | Collect anonymised usage data to improve the product | Feature usage counts, error rates — no PII, no family identifiers | 1 year rolling | None | No | No |

> ℹ v1.4 notes on the two rows changed above.
> **DIGILOCKER_DOCUMENT** (founder ruling 2026-09-21): adding date of birth is a new data type, so the disclosure goes to a new MAJOR version (2.0.0) with `is_material_change = TRUE` and a `material_change_reason` (§4.6). Anyone who consented under 1.x is asked again before any milestone is derived from their documents; until they do, their documents stay linked and no milestone is computed for them. No real user has consented yet, so in practice V001 seeds 2.0.0 as the first disclosure for this purpose. A milestone date can be turned back into a birth date, so the Vault treats `milestone_at` as sensitive derived data: shown only to people who may see the document, never written to audit details (Data Model v1.4 §6.1).
> **HEALTH_MEDICATION_REMINDERS**: AGENTS invariant 8 says no processing without an active consent record for a registered purpose. Before v1.4 reminders ran under ABHA_PRESCRIPTION alone, which left two gaps: a schedule typed in by hand had no purpose at all, and a schedule taken from a prescription lost its authorisation the day the ABHA consent expired, although nothing was being fetched any more. The reminder purpose is separate, first-party (no DPI handle, so `enforce_dpi_handle` does not apply), granted once per subject when the first schedule is created (by the subject, or by the proxy under §2.6, or with parental consent under §2.5). Expiry or withdrawal of ABHA_PRESCRIPTION stops **fetching**; reminders continue under this purpose. Withdrawal of this purpose stops reminders and the admins are told that it did (never silently). It is not an "essential" purpose: a family can use Health without it.

### 3.3 Jurisdiction-Specific Overrides (v1: DPDP only)

The purpose registry entries above use DPDP Act 2023 retention periods and lawful bases. When a new jurisdiction is added, a jurisdiction_overrides config entry is added for that jurisdiction — the base entry is not modified. At runtime, the Consent Manager selects the applicable rule set based on the user's jurisdiction field.

```yaml
# jurisdiction_overrides config (YAML — not a DB table)
# v1: only 'IN' (India) implemented. GDPR config shown as example structure.

purpose_registry_overrides:
  AA_TRANSACTION_HISTORY:
    IN:  # India — DPDP Act 2023
      lawful_basis: 'explicit_consent'
      retention_days: 365
      re_consent_required: true
    EU:  # GDPR — NOT implemented in v1, shown for architecture illustration
      lawful_basis: 'legitimate_interest OR explicit_consent'
      retention_days: 90
      right_to_erasure: immediate
      dpo_notification_required: true
  PRODUCT_ANALYTICS:
    IN:
      lawful_basis: 'explicit_consent'  # DPDP has no 'legitimate interest' basis
      opt_out_allowed: true
    EU:  # NOT implemented in v1
      lawful_basis: 'legitimate_interest'  # GDPR allows this for analytics
      opt_out_allowed: true
```

> ℹ INFO: DPDP Act 2023 does not have a 'legitimate interest' lawful basis (unlike GDPR Article 6(1)(f)). Every data processing activity in India requires explicit consent or falls under one of the narrow DPDP exemptions. This is why PRODUCT_ANALYTICS requires explicit opt-in for Indian users — it cannot be treated as a default-on collection.

## 4. First-Party Consent Framework

### 4.1 consent_records Table (DDL also in Data Model v1.3 §3.12)

> ⚠ v1.4: **the DDL printed below is the v1.3 text and is no longer complete.** Data Model v1.4 §3.12 is the only DDL source and adds `proxy_reconfirm_required`, `proxy_reconfirmed_by`, `proxy_reconfirmed_at`, the index `idx_consent_proxy_reconfirm` and the composite foreign key `(purpose_code, consent_ui_version)` → `consent_ui_disclosures`. The copy stays here only so that the v1.1 review history still reads; do not author a migration from it.
> ℹ v1.2: this DDL was folded into Data Model v1.3 §3.12 on 2026-09-17, which is now the single DDL source (the expiry index is named `idx_consent_records_expiry` there to avoid clashing with consent_handles' `idx_consent_expiry`). This section is retained for the rationale and the trigger's sync rule.

This table is a backward-compatible addition to the frozen Data Model. It does not modify any existing table. All existing queries in Data_Model_Schema v1.2.1 §5 remain valid.

```sql
CREATE TABLE consent_records (
  -- Primary key
  record_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- Who gave consent
  user_id         UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  family_id       UUID NOT NULL REFERENCES families(family_id) ON DELETE CASCADE,

  -- What they consented to
  purpose_code    VARCHAR(50) NOT NULL,
  -- Must be a valid code from the purpose_registry (enforced at application layer)

  -- Lifecycle status
  status          VARCHAR(20) NOT NULL DEFAULT 'active'
    CHECK (status IN ('pending','active','expired','revoked','withdrawn')),
  -- 'pending'   = consent request sent, user has not yet confirmed
  -- 'active'    = consent granted, currently valid
  -- 'expired'   = past expires_at, must re-consent before use
  -- 'revoked'   = DPI/external system revoked (webhook triggered)
  -- 'withdrawn' = user explicitly withdrew consent via FamilyLifeOS UI

  -- Consent timestamps
  granted_at      TIMESTAMPTZ,        -- NULL while status = 'pending'
  expires_at      TIMESTAMPTZ NOT NULL,
  revoked_at      TIMESTAMPTZ,        -- populated for 'revoked' or 'withdrawn'

  -- Jurisdiction and regulatory context
  jurisdiction    VARCHAR(10) NOT NULL DEFAULT 'IN',
  -- 'IN' = DPDP Act 2023 (only value in v1)
  -- Future: 'EU', 'SG', 'BR' etc.
  lawful_basis    VARCHAR(40) NOT NULL DEFAULT 'explicit_consent',
  -- Determines which enforcement rules apply (from jurisdiction_overrides config)

  -- Parental consent (required for Minor role users)
  parental_consent_user_id UUID REFERENCES users(user_id),
  -- NULL for adult users. For Minor users: must be populated before status='active'

  -- Proxy consent (v1.3, §2.6): required when user_id is a 'managed' profile
  proxy_consent_user_id UUID REFERENCES users(user_id),
  -- The assigned proxy who granted on the managed profile's behalf. NULL for everyone else.

  -- Link to DPI external handle (if applicable)
  consent_handle_id UUID REFERENCES consent_handles(consent_id),
  -- NULL for first-party-only consents (VOICE_INTENT_PROCESSING, DEVICE_REGISTRATION, etc.)
  -- Populated for DPI consents (AA, ABHA, DigiLocker)

  -- The specific data scope agreed to (purpose-code-specific JSON structure)
  granted_scope   JSONB NOT NULL DEFAULT '{}',
  -- AA example:    {"fi_types":["DEPOSIT"],"fip_ids":["HDFC"]}
  -- ABHA example:  {"hi_types":["Prescription"],"hips":["Apollo"]}
  -- Voice example: {"languages":["hi","en"],"retain_transcript":false}

  -- Proof of informed consent (what was shown to the user at grant time)
  consent_ui_version  VARCHAR(20) NOT NULL,
  -- Records which version of the consent UI/disclosure the user saw.
  -- If the disclosure text changes materially, a new consent event is required.

  -- Metadata
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- Constraints
  CONSTRAINT chk_granted_before_expiry CHECK (
    granted_at IS NULL OR expires_at > granted_at
  ),
  CONSTRAINT chk_revoked_has_timestamp CHECK (
    status NOT IN ('revoked','withdrawn') OR revoked_at IS NOT NULL
  ),
  CONSTRAINT chk_pending_no_grant_time CHECK (
    status != 'pending' OR granted_at IS NULL
  )
);

-- Only one ACTIVE consent per user per purpose (prevents duplicate active grants)
CREATE UNIQUE INDEX idx_one_active_consent_per_purpose
  ON consent_records (user_id, purpose_code)
  WHERE status = 'active';

-- Expiry watchdog query support
CREATE INDEX idx_consent_expiry ON consent_records (expires_at, status)
  WHERE status = 'active';

-- Parental consent lookup
CREATE INDEX idx_consent_parental ON consent_records (parental_consent_user_id)
  WHERE parental_consent_user_id IS NOT NULL;

-- Proxy consent lookup (v1.3)
CREATE INDEX idx_consent_proxy ON consent_records (proxy_consent_user_id)
  WHERE proxy_consent_user_id IS NOT NULL;

-- ─────────────────────────────────────────────────────────────────────────
-- FIX 1 (v1.1): DPI handle enforcement trigger
-- Prevents a consent_record for a DPI purpose_code from being written
-- without a linked consent_handle_id. Without this trigger, a crash between
-- consent_handle INSERT and consent_record INSERT leaves consent_handle_id=NULL.
-- CONSENT_REVERIFY Check 2 is silently skipped for NULL handles — meaning
-- payment could execute without a verified external consent. This is catastrophic.
-- ─────────────────────────────────────────────────────────────────────────

-- The canonical list of purpose_codes that require an external DPI handle.
-- Update this list whenever a new DPI purpose_code is added to the registry.
CREATE OR REPLACE FUNCTION enforce_dpi_handle()
RETURNS trigger AS $$
DECLARE
  dpi_purposes TEXT[] := ARRAY[
    'AA_BALANCE_FETCH',
    'AA_TRANSACTION_HISTORY',
    'ABHA_PRESCRIPTION',
    'ABHA_DIAGNOSTICS',
    'ABHA_VITALS',
    'DIGILOCKER_DOCUMENT',
    'ONDC_ADDRESS_SHARE'
  ];
BEGIN
  IF NEW.purpose_code = ANY(dpi_purposes) AND NEW.consent_handle_id IS NULL THEN
    RAISE EXCEPTION
      'DPI consent purpose % requires consent_handle_id to be set. '
      'Write the consent_handle row first, then link it here.',
      NEW.purpose_code;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_enforce_dpi_handle
  BEFORE INSERT OR UPDATE ON consent_records
  FOR EACH ROW EXECUTE FUNCTION enforce_dpi_handle();
-- This trigger fires on both INSERT and UPDATE to catch attempts to NULL-out
-- an existing handle_id after the fact.
```

> 🔴 CRITICAL: The dpi_purposes array in enforce_dpi_handle() MUST be kept in sync with the purpose_registry entries where dpi_required is not None. If a new DPI purpose_code is added to the registry without updating this trigger, the DB-layer enforcement has a gap. The correct process: add the purpose_code to the registry → add it to the trigger function → deploy the Alembic migration together. These are one atomic change.

### 4.2 Consent Grant Flow

The grant flow is triggered when a feature requires a purpose_code that the user does not have an active consent_record for. The Supervisor detects this during INTENT_ANALYSIS and routes to the consent grant sub-flow before proceeding.

```sql
CONSENT GRANT FLOW — canonical sequence

Step 0 (v1.4): RESOLVE actor and subject
  actor   = the authenticated user (session.user_id)
  subject = the person whose data the purpose covers. Usually the actor. For a managed profile it is
            session.acting_as, verified server-side against proxy_assignments (§2.6); for a child it is
            the child. Every query below is keyed by the SUBJECT ($sid); every confirmation and audit
            row names the ACTOR.

Step 1: DETECT missing consent
  Supervisor checks: SELECT * FROM consent_records
    WHERE user_id=$sid AND purpose_code=$code AND status='active'
    AND expires_at > NOW() AND proxy_reconfirm_required = FALSE
  IF no row: proceed to Step 2
  IF row exists: consent already active, proceed with the original intent

Step 2: FETCH purpose details from registry
  purpose = purpose_registry[$code]
  IF purpose not found: RAISE ConsentError (unknown purpose — block operation)
  IF subject.is_child AND purpose.minor_allowed == False:          # v1.4: marker, not role
    RAISE ConsentError('Purpose not permitted for a child')

Step 3: PRESENT consent UI
  Show to user (in their preferred language via Bhashini):
    - Purpose plain-text description
    - Data types that will be collected/accessed
    - Retention period
    - How to revoke (link to settings)
    - If DPI: which external system will be accessed
  Record: consent_ui_version = current UI disclosure version
  v1.4: that (purpose_code, version) row MUST already exist in consent_ui_disclosures; the composite
  foreign key (Data Model v1.4 §3.12) rejects a grant that points at a screen nobody recorded.

Step 4: USER CONFIRMS (explicit affirmative action required)
  Method: biometric (preferred) OR 4-digit PIN
  No pre-ticked boxes. No 'continue = consent' implied.

Step 5: If the subject is a child: VERIFY parental consent (§2.5)
  Notify a parent or legal guardian (v_guardians) with the consent request
  That adult must confirm separately with their own biometric
  parental_consent_user_id = that adult's user_id

Step 5b (v1.4): If the subject is a managed profile: the ACTOR is the proxy (§2.6)
  Step 4's confirmation was the proxy's own biometric. proxy_consent_user_id = actor.user_id
  check_proxy_grant(actor, subject, record) runs in Step 7's transaction, and again at pending→active

Step 6: If DPI required: INITIATE DPI consent flow
  (AA: see §6.1 | ABHA: see §6.2 | DigiLocker: see §6.3)
  This creates the external handle (consent_handle row)
  Wait for external confirmation before Step 7

Step 7: WRITE consent_record (atomic transaction)
  BEGIN TRANSACTION;
    SELECT 1 FROM families WHERE family_id=$fid FOR UPDATE;   -- v1.4: only when subject is managed or a child
    check_proxy_grant(...) / §2.5 check                       -- v1.4
    INSERT INTO consent_records (
      user_id /* the SUBJECT */, family_id, purpose_code, status, granted_at,
      expires_at, jurisdiction, lawful_basis, parental_consent_user_id,
      proxy_consent_user_id /* v1.4 */,
      consent_handle_id, granted_scope, consent_ui_version
    ) VALUES (...);
    -- v1.4: audit rows go through fn_lock_audit_tail / fn_append_audit (Data Model v1.4 §3.18),
    -- never a direct INSERT. user_id of each audit row = the ACTOR.
    APPEND audit (action='CONSENT_GRANTED', details={
      purpose_code, subject_user_id, consent_record_id, expires_at, consent_ui_version,
      parental_consent_user_id (if child), proxy_consent_user_id (if managed), consent_handle_id (if DPI)
    });
    IF child:   APPEND audit (action='PARENTAL_CONSENT_GRANTED', ...)
    IF managed: APPEND audit (action='PROXY_CONSENT_GRANTED', details={
      purpose_code, subject_user_id, proxy_user_id, proxy_rank, consent_record_id })
  COMMIT;

Step 8: RESUME original intent
  Supervisor resumes the flow that triggered the consent requirement
```

### 4.3 Consent Withdrawal Flow (User-Initiated)

```sql
CONSENT WITHDRAWAL — triggered from user's settings > privacy > active consents

Step 1: User selects consent_record to withdraw
  Show: purpose description, what data will no longer be accessible,
  which features will be affected

Step 2: User confirms (biometric required for DPI consents)

Step 3: If DPI consent: REVOKE external handle first
  AA: POST /Consent/revoke to Sahamati (consent_handle.external_consent_id)
  ABHA: POST /consent/revoke to ABDM
  Wait for acknowledgement. If DPI revocation fails: log warning, proceed anyway.
  (User's right to withdraw cannot be blocked by DPI API failure)

Step 4: UPDATE consent_records (atomic transaction with audit_log)
  BEGIN TRANSACTION;
    -- v1.4: authorise the ACTOR against the record's SUBJECT, then update by record and family.
    -- Allowed actors: the subject themselves; for a managed subject, the current primary proxy
    -- (or the secondary under §2.6.1) or any live admin of the family; for a child, a parent or
    -- legal guardian (v_guardians) or any live admin. v1.3 filtered `user_id=$uid`, which made
    -- every withdrawal by a proxy or admin a silent no-op.
    REQUIRE may_withdraw(actor, record)
    UPDATE consent_records
      SET status='withdrawn', revoked_at=NOW(), updated_at=NOW()
      WHERE record_id=$id AND family_id=$fid AND status IN ('active','pending');
    REQUIRE rowcount == 1
    IF consent_handle_id IS NOT NULL:
      UPDATE consent_handles
        SET status='revoked', revoked_at=NOW()
        WHERE consent_id=consent_handle_id;
    APPEND audit (action='CONSENT_WITHDRAWN', user_id = ACTOR, details={
      purpose_code, subject_user_id, consent_record_id, actor_basis, dpi_revocation_acknowledged
    });   -- actor_basis: self | proxy_primary | proxy_secondary | guardian | admin
  COMMIT;

Step 5: PROPAGATE revocation (see §8 — Revocation Propagation)
  Purge any cached data associated with this consent
  Notify affected features that access is no longer permitted
  If Healer has pending tasks using this consent: cancel them
```

### 4.4 Consent Audit Trail

These action codes are part of the audit_log action taxonomy in Data Model §6 (the canonical list). v1.4: every row below also carries `subject_user_id` and `consent_record_id`; the audit row's own `user_id` is the actor. Payloads hold identifiers, enum values and timestamps only; `granted_scope` and `features_affected`, which v1.1 listed, are **not** written to audit details (scope JSON can name banks and hospitals; the record itself holds it).

| Action Code | Trigger | Key Fields in details JSONB |
|---|---|---|
| CONSENT_GRANTED | User grants consent for a purpose_code | purpose_code, granted_scope, expires_at, consent_ui_version, parental_consent_user_id (if Minor), consent_handle_id (if DPI) |
| CONSENT_WITHDRAWN | User withdraws consent from FamilyLifeOS settings | purpose_code, revoked_at, dpi_revocation_acknowledged (bool), features_affected |
| CONSENT_REVOKED_EXTERNAL | DPI webhook notifies of external revocation | purpose_code, provider, webhook_event_id, revalidation_required_set_to: true |
| CONSENT_EXPIRED | Expiry watchdog marks consent as expired | purpose_code, expired_at, renewal_notification_sent (bool) |
| CONSENT_RENEWED | User renews an expired or expiring consent | purpose_code, previous_expires_at, new_expires_at, new_consent_handle_id (if DPI) |
| CONSENT_REVERIFY_PASSED | CONSENT_REVERIFY state gate passed successfully | purpose_code, consent_handle_id, revalidation_required_was: false |
| CONSENT_REVERIFY_FAILED | CONSENT_REVERIFY gate failed — consent revoked or expired | purpose_code, failure_reason, session_id, action_taken |
| PARENTAL_CONSENT_GRANTED | Parent or legal guardian grants consent on behalf of a child | subject_user_id, purpose_code, parent_user_id, basis (parent \| legal_guardian \| admin_fallback), biometric_verified: true |
| PROXY_CONSENT_GRANTED | Assigned proxy grants consent for a managed profile (§2.6); same transaction as CONSENT_GRANTED | subject_user_id, purpose_code, proxy_user_id, proxy_rank, consent_record_id |
| PROXY_CONSENT_RECONFIRMED | Current primary proxy re-confirms a record whose granting proxy was deleted (§2.6.4) | subject_user_id, purpose_code, consent_record_id, original_proxy_user_id, reconfirmed_by, proxy_rank |
| DATA_EXPORT_COMPLETED | Family data export completed (portability) | exported_purposes, format, file_size_bytes, delivered_to |
| CONSENT_UI_VERSION_CHANGED | Consent disclosure text updated — re-consent triggered | purpose_code, old_version, new_version, affected_user_count |

### 4.5 Data Portability

Under DPDP Act 2023 Section 12, users have the right to access their data in a structured, machine-readable format. For FamilyLifeOS, data portability means exporting everything the system holds about the requesting user and, if they are an Admin, the family.

```text
DATA EXPORT REQUEST — triggered by Admin from settings > privacy > export data

Audit_log entry: DATA_EXPORT_REQUESTED (at request time, before processing)

Export package contents (JSON, delivered as encrypted download link):
{
  'export_generated_at': '2026-02-21T14:30:00+05:30',
  'user_id': '...',
  'family_id': '...',
  'consent_records': [ ... all consent_record rows for this user ... ],
  'audit_log_entries': [ ... all audit_log rows where user_id = requesting user ... ],
  'family_members': [ ... name, role, joined_at — no PII for other members ... ],
  'supervisor_sessions': [ ... completed sessions (no EXECUTION state sessions) ... ],
  'vault_document_metadata': [ ... document names, dates — not document contents ... ],
  'aa_transaction_summary': [ ... if AA consent active: last 90 days of transactions ... ],
}

What is NOT exported (system data, not personal data):
  - audit_log entries for other family members
  - resource_lock records
  - offline_task_queue internals
  - Other members' vault contents

Delivery: HTTPS download link (valid 24 hours), AES-256 encrypted,
  decryption key sent separately via SMS to registered number.
Audit_log entry: DATA_EXPORT_COMPLETED (with file_size_bytes, delivered_to)
```

### 4.6 consent_ui_disclosures Table (Fix 4 — v1.1; DDL also in Data Model v1.3 §3.13)

consent_records.consent_ui_version records which disclosure version the user saw when they granted consent. Without a canonical record of what each version said, this field is an unverifiable pointer. If a regulator or court asks 'what did the user consent to on 21 Feb 2026?', the answer must be auditable, not inferred.
The consent_ui_disclosures table is the canonical disclosure record. It is append-only — existing rows are never modified. When disclosure text changes materially, a new row is added with is_material_change=TRUE, and all users who previously granted consent for that purpose_code are queued for re-consent.

```sql
CREATE TABLE consent_ui_disclosures (
  disclosure_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- Which purpose this disclosure covers
  purpose_code    VARCHAR(50) NOT NULL,
  -- Must match a valid code in purpose_registry

  -- Semantic version: MAJOR.MINOR.PATCH
  -- MAJOR: new data types collected or new DPI access scope
  -- MINOR: changed retention periods, new jurisdiction
  -- PATCH: grammar/formatting fixes with no legal change
  version         VARCHAR(20) NOT NULL,

  -- The exact text shown to the user in the consent UI (English base)
  -- Translations are derived at runtime via Bhashini — not stored here
  disclosure_text TEXT NOT NULL,

  -- What the user is agreeing to (structured summary for audit)
  data_types_summary TEXT[] NOT NULL,
  -- e.g. ['Account balance (amount only)', 'No transaction history']

  -- Is this change material enough to require re-consent from existing users?
  is_material_change BOOLEAN NOT NULL,
  -- TRUE  = existing consent_records with older version must be invalidated.
  --         Watchdog queues re-consent notification for affected users.
  -- FALSE = non-material fix. Existing consents remain valid. No user action needed.

  -- Rationale for is_material_change decision (required when is_material_change=TRUE)
  material_change_reason TEXT,

  -- Who made this change and why (internal audit trail)
  changed_by      VARCHAR(100) NOT NULL,
  change_rationale TEXT NOT NULL,

  -- When this disclosure version became effective
  effective_from  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- Append-only: never update or delete disclosure records
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- Prevent accidental duplicate versions for same purpose
  UNIQUE(purpose_code, version)
);

-- Query: find all users whose consent was granted under a now-outdated disclosure
-- (used by watchdog when is_material_change = TRUE is inserted)
-- SELECT cr.user_id, cr.purpose_code, cr.consent_ui_version
--   FROM consent_records cr
--   JOIN consent_ui_disclosures d
--     ON cr.purpose_code = d.purpose_code
--    AND cr.consent_ui_version = d.version
--   WHERE d.is_material_change = TRUE
--     AND d.effective_from > cr.granted_at
--     AND cr.status = 'active';
```

| Version Pattern | is_material_change | Example | User Action Required |
|---|---|---|---|
| 1.0.0 → 1.0.1 | FALSE | Fixed typo 'acount' → 'account' in disclosure text | None — existing consents remain valid |
| 1.0.1 → 1.1.0 | FALSE | Added Hindi translation notes to disclosure | None — no legal change |
| 1.1.0 → 2.0.0 | TRUE | Added 'mutual funds' to AA_BALANCE_FETCH scope (new data type) | All existing AA_BALANCE_FETCH consent holders must re-consent |
| 1.0.0 → 1.1.0 | TRUE | Retention period changed from 15 min to 24 hours | All existing consent holders must re-consent (retention change is material) |

> ⚠ WARNING: When is_material_change=TRUE is inserted, the expiry watchdog's next run must detect all consent_records whose consent_ui_version predates the new disclosure version and queue re-consent notifications. Do not retroactively update existing consent_records — the record of what the user consented to (including the disclosure version they saw) is a legal artefact and must not be modified.

## 5. CONSENT_REVERIFY: FSM Integration

### 5.1 What CONSENT_REVERIFY Is

CONSENT_REVERIFY is Gate G5 in the payment execution protocol (Tech_Spec_Financial_Transaction_Safety v1.1 §2.2). It is the last check before the POINT OF NO RETURN — the moment when the idempotency key is persisted and the external API call is made. The reason it exists as a separate gate (not just a status check at INTENT_ANALYSIS time) is the TOCTOU (Time-of-Check to Time-of-Use) attack window: a user could revoke consent on the AA portal between when the session was created and when the payment is actually executed. Without CONSENT_REVERIFY, that revocation would be invisible to the executing session.
CONSENT_REVERIFY is not only for financial flows. Any flow that reaches an EXECUTION state against a DPI must pass through CONSENT_REVERIFY before the external call. This includes ABHA health record fetches requested by agents and DigiLocker document retrievals.

### 5.2 What CONSENT_REVERIFY Checks (Exact Algorithm)

```sql
CONSENT_REVERIFY GATE — executes immediately before Phase 1 two-phase commit

Inputs:
  - session.user_id          the ACTOR
  - session.subject_user_id  whose data the external call touches ($sid; = actor unless acting_as, v1.4)
  - session.purpose_code     the EXACT registered purpose of this call (e.g., 'AA_BALANCE_FETCH').
                             "Some active consent with the same provider" is never enough (MR v1.2 §7.3)
  - session.consent_handle_id (if DPI consent)

Check 0 (v1.4): the subject is a live member of this family
  IF NOT EXISTS (SELECT 1 FROM users WHERE user_id=$sid AND family_id=$fid AND deleted_at IS NULL):
    FAIL → CONSENT_006

Check 1: consent_records freshness
  record = SELECT * FROM consent_records
    WHERE user_id=$sid AND family_id=$fid AND purpose_code=$code
    AND status='active' AND expires_at > NOW()
  IF no record: FAIL → CONSENT_006 (consent_record not found or expired)

Check 1b (v1.4): proxy re-confirmation (§2.6.4)
  IF record.proxy_reconfirm_required: FAIL → CONSENT_009 (waiting for the new primary proxy)
  # Cleared only by PROXY_CONSENT_RECONFIRMED. Nothing in this gate clears it.

Check 2: revalidation_required flag
  IF record.consent_handle_id IS NOT NULL:
    handle = SELECT * FROM consent_handles WHERE consent_id=record.consent_handle_id
    IF handle.revalidation_required == TRUE:
      # External revocation signalled via webhook — must live-validate with DPI
      live_status = GET_DPI_CONSENT_STATUS(handle.external_consent_id, handle.provider)
      IF live_status != 'active':
        UPDATE consent_handles SET status='revoked', revoked_at=NOW()
        UPDATE consent_records SET status='revoked', revoked_at=NOW()
        FAIL → CONSENT_007 (DPI confirmed revocation)
      ELSE:
        # DPI says still active — webhook may have been erroneous
        UPDATE consent_handles SET revalidation_required=FALSE
        UPDATE consent_records (via handle_id) SET updated_at=NOW()
        # PASS — proceed to Check 3

Check 3: scope adequacy
  # Verify the granted_scope still covers what this session needs
  required_scope = session.required_scope  # set at INTENT_ANALYSIS
  IF NOT scope_is_sufficient(record.granted_scope, required_scope):
    FAIL → CONSENT_008 (scope insufficient for this operation)
    # This can happen if user narrowed consent scope after session creation

PASS: all checks passed → proceed to Phase 1 two-phase commit
FAIL: log audit entry CONSENT_REVERIFY_FAILED; the session is persisted as fsm_state = 'FAILED'
      (or 'ABORTED' where §5.3 says so). "CONSENT_REVERIFY_FAILED" in §5.3 is the name of the outcome and of
      the audit action; it is not a stored state (Data Model v1.4 §3.7 mapping table).
```

> ⚠ v1.4, what this gate does **not** detect. Check 2 asks the provider only when `revalidation_required` is already TRUE, and that flag is set by a verified webhook (§9) or by the watchdog. A consent revoked at the provider while our flag is still FALSE and no webhook has arrived passes this gate; the external call itself then fails at the provider with a consent error, which the DPI Gateway maps to the same CONSENT_007 path. That is the design since v1.0 (polling every provider before every payment would spend the AA budget of 3 fetches an hour on status calls), and it is recorded here so that no test or document claims otherwise (Inconsistency Register item 19; Simulator spec §11 OI-3).

### 5.3 CONSENT_REVERIFY State Transition Matrix

| Check | Result | Session State After | Action | User Message |
|---|---|---|---|---|
| Check 1: record not found | FAIL | CONSENT_REVERIFY_FAILED | Prompt user to grant consent, then restart session | Please re-connect your bank to continue. |
| Check 1: record expired | FAIL | CONSENT_REVERIFY_FAILED | Route to renewal flow (§7.3), then restart session | Your bank connection has expired. Renew to continue. |
| Check 1: record withdrawn | FAIL | CONSENT_REVERIFY_FAILED → ABORTED | Cannot proceed. User withdrew consent deliberately. | You've disconnected this bank. Reconnect from settings to pay bills. |
| Check 2: revalidation_required, DPI confirms revoked | FAIL | CONSENT_REVERIFY_FAILED → ABORTED | Update records, propagate revocation (§8) | Your bank connection was cancelled externally. Please reconnect. |
| Check 2: revalidation_required, DPI confirms active | PASS | Continue to Check 3 | Clear flag, proceed | (no user message) |
| Check 2: DPI unreachable | FAIL (safe default) | CONSENT_REVERIFY_FAILED | Queue CONSENT_REFRESH task. Alert Admin if persistent. | Unable to verify your bank connection. Please try again shortly. |
| Check 3: scope insufficient | FAIL | CONSENT_REVERIFY_FAILED | Prompt user to re-grant consent with required scope | Your bank permission doesn't cover this account. Please update. |
| Check 1b: proxy re-confirmation pending (v1.4) | FAIL | CONSENT_REVERIFY_FAILED | Notify the current primary proxy with the re-confirm action; data already held keeps being processed | This needs a quick confirmation from {proxy_first_name} first. We've asked them. |
| All checks pass | PASS | Proceeds to EXECUTION | Phase 1 two-phase commit begins | (no user message — flow continues) |

### 5.4 TTL Policy for Consent Checks

CONSENT_REVERIFY always reads live from the database — it never uses a cached consent status. This is non-negotiable. The Financial Safety spec's TOCTOU rationale applies here: a cached 'active' status that is 2 minutes old is a security hole.

| Data Type | Cache TTL (FSM Spec) | CONSENT_REVERIFY Behaviour |
|---|---|---|
| Consent record status | None — always live read | Always SELECT from consent_records table. No Redis cache of consent status. |
| revalidation_required flag | None — always live read | Always SELECT from consent_handles. Flag is set by webhook handler within seconds of external revocation. |
| DPI live validation (Check 2 path) | Not cached | Live GET call to DPI API. 5-second timeout. Failure = safe default FAIL. |
| Scope adequacy check | None | Computed from record.granted_scope at check time. Scope can only narrow, never expand without new consent. |

## 6. DPI Adapter Layer

### 6.1 AA Adapter (Account Aggregator — Sahamati Network)

> ℹ INFO: AA integration requires FIU (Financial Information User) registration with RBI. Approval timeline: 6-12 months. All AA flows described here are specified for implementation post-licence. The simulator (WireMock) should implement these flows for pre-licence development and testing.

#### 6.1.1 AA Consent Grant Flow (maps to §4.2 Step 6)

```sql
# When purpose_code requires 'AA' DPI (e.g., AA_BALANCE_FETCH, AA_TRANSACTION_HISTORY)
# This is Step 6 of the consent grant flow in §4.2

Step 6a: Generate consent request object (Sahamati format)
  consent_request = {
    'consentTypes': ['PROFILE', 'SUMMARY', 'TRANSACTIONS'],  # per purpose_code
    'fiTypes': granted_scope['fi_types'],   # e.g., ['DEPOSIT', 'MUTUAL_FUNDS']
    'fipIds': granted_scope['fip_ids'],      # e.g., ['HDFC', 'ICICI']
    'dateRange': { 'from': ..., 'to': ... },
    'consentDisplayLanguages': [user.preferred_language, 'en'],
    'purpose': { 'code': '101', 'text': purpose_registry[purpose_code].description },
    'consentExpiry': NOW() + purpose_registry[purpose_code].default_expiry,
    'dataLife': { 'value': 1, 'unit': 'YEAR' },
    'frequency': { 'value': 3, 'unit': 'HOUR' },  # AA rate limit: 3 fetches/hour
  }

Step 6b: POST /Consent to Sahamati AA gateway
  response = POST /Consent { consent_request }
  IF success: consentHandle = response.consentHandle  # UUID
  IF failure: RAISE ConsentError — user notified, consent flow aborted

Step 6c: Store external handle (before writing consent_record)
  BEGIN TRANSACTION;
    INSERT INTO consent_handles (
      user_id, family_id, provider='AA',
      external_consent_id=consentHandle,
      status='pending',   -- not active until user approves on AA app
      expires_at=consent_request.consentExpiry,
      data_scope=granted_scope
    );
  COMMIT;

Step 6d: User approves consent on their AA app (bank's mobile app or AA app)
  FamilyLifeOS polls GET /Consent/{consentHandle} every 30 seconds
  Timeout: 10 minutes (user has 10 min to approve on AA app)
  IF approved:
    UPDATE consent_handles SET status='active', granted_at=NOW()
    Proceed to Step 7 of grant flow (write consent_record)
  IF rejected by user:
    UPDATE consent_handles SET status='revoked', revoked_at=NOW()
    Abort consent flow. Notify user.
  IF timeout:
    UPDATE consent_handles SET status='expired'
    Abort consent flow. Allow user to retry.
```

#### 6.1.2 AA Data Fetch (Balance / Transactions)

```sql
# After consent is active, data is fetched via the FI (Financial Information) API
# Rate limit: 3 fetches per hour per consent handle (Sahamati network limit)
# Rate limit tracking: consent_handles.fetch_count_today, last_fetched_at

PRE-FETCH CHECK:
  1. CONSENT_REVERIFY gates must pass (§5.2) — always run first
  2. Rate limit check:
     IF fetch_count_today >= 3 AND last_fetched_at > NOW() - 1 HOUR:
       RETURN cached data (use supervisor_sessions cached value if TTL not expired)
       DO NOT call AA API

FETCH:
  POST /FI/request to Sahamati with consentHandle
  Response: sessionId for async data retrieval
  Poll GET /FI/fetch/{sessionId} until data ready (max 30 seconds)

POST-FETCH:
  UPDATE consent_handles SET
    fetch_count_today = fetch_count_today + 1,
    last_fetched_at = NOW()
  Cache result in supervisor_sessions per FSM TTL policy:
    AA_BALANCE_FETCH: 15 minutes
    AA_TRANSACTION_HISTORY: 24 hours
```

#### 6.1.3 AA Consent Handle Statuses (mapping to consent_handles.status)

| Sahamati Status | consent_handles.status | Action |
|---|---|---|
| PENDING | pending | User has not yet approved on AA app. Poll until approved or timeout. |
| ACTIVE | active | Consent valid. Fetch allowed subject to rate limits and CONSENT_REVERIFY. |
| PAUSED | pending (revalidation_required=TRUE) | Sahamati has paused the consent. Treat as requiring revalidation. Do not fetch. |
| REVOKED | revoked | User revoked on AA app. Webhook fires. Propagate revocation (§8). |
| EXPIRED | expired | Past consent expiry. Renewal required. Expiry watchdog handles notification. |

### 6.2 ABHA Adapter (Ayushman Bharat Health Account — ABDM)

> ℹ INFO: ABHA integration requires Health Information User (HIU) registration with NHA/ABDM. Consent artefacts in ABDM use a different format (CM-flow) from AA. The adapter translates FamilyLifeOS first-party consent to the ABDM consent request format.

#### 6.2.1 ABHA Consent Grant Flow

```sql
# When purpose_code = 'ABHA_PRESCRIPTION' | 'ABHA_DIAGNOSTICS' | 'ABHA_VITALS'

Step 6a: Construct ABDM consent request
  consent_request = {
    'purpose': { 'code': 'CAREMGT', 'text': purpose_description },
    'patient': { 'id': user.abha_address },  # e.g., 'priya@abdm'
    'hiu': { 'id': FAMILYLIFEOS_HIU_ID },     # Our registered HIU ID
    'requester': { 'name': 'FamilyLifeOS', 'identifier': ... },
    'hiTypes': granted_scope['hi_types'],  # e.g., ['Prescription']
    'permission': {
      'accessMode': 'VIEW',
      'dateRange': { 'from': ..., 'to': ... },
      'dataEraseAt': NOW() + retention_period,
      'frequency': { 'unit': 'HOUR', 'value': 1, 'repeats': 0 }
    }
  }

Step 6b: POST /v0.5/consent-requests/init to ABDM CM
  response: { 'id': consent_request_id }
  INSERT INTO consent_handles (provider='ABHA', external_consent_id=consent_request_id, status='pending')

Step 6c: User approves on ABHA mobile app or Aarogya Setu
  ABDM fires callback to our webhook on approval/rejection
  Webhook handler: update consent_handles.status = 'active' | 'revoked'
  On active: fetch consent artefact from ABDM, store artefact_id in data_scope
```

#### 6.2.2 ABHA Data Fetch

```text
# ABDM health information flow uses the consent artefact (not the consent handle)

1. POST /v0.5/health-information/cm/request to ABDM CM
   Body: { consent_artefact_id, date_range, callback_url }

2. ABDM decrypts and fetches from HIP (hospital) on our behalf
   FamilyLifeOS receives encrypted FHIR bundle at callback_url

3. Decrypt using HIU's private key
   Parse FHIR R4 resources: MedicationRequest, DiagnosticReport, Observation

4. Store extracted fields only (per data minimisation — §2.3)
   Full FHIR bundle is NOT stored. Parsed fields only.

5. Update consent_handles.last_fetched_at, fetch_count_today
```

### 6.3 DigiLocker Adapter

```text
# DigiLocker uses OAuth 2.0. FamilyLifeOS acts as a registered DigiLocker partner.
# Consent in DigiLocker is the OAuth authorization code flow.

Grant flow:
  1. Redirect user to DigiLocker OAuth endpoint
  2. User logs in with Aadhaar OTP and grants access
  3. DigiLocker returns authorization_code
  4. Exchange for access_token + refresh_token
  5. Store token reference in consent_handles
     (NOT the token itself — store only the reference ID in a secure token vault)

Document fetch:
  1. CONSENT_REVERIFY passes (§5.2)
  2. Use refresh_token to get fresh access_token (DigiLocker tokens: 1 hour TTL)
  3. GET /public/oauth2/1/xml/eaadhaar (or relevant document API)
  4. Return document metadata. User decides whether to store in vault.
  5. Raw document bytes are never written to the FamilyLifeOS database.
     They are passed directly to the requesting agent in memory.
```

## 7. Consent Expiry Watchdog

### 7.1 Overview

The Consent Expiry Watchdog is a daily cron job (runs at 06:00 IST — after the nightly purge at 01:00 IST, before the business day begins) that scans for consents expiring within the next 7 days and sends advance notifications. It also marks consents that have already expired as 'expired' in the database.
The watchdog is separate from the Healer. The Healer handles transaction zombie recovery. The watchdog handles consent lifecycle events. They do not share state or distributed locks.

### 7.2 Watchdog Algorithm

```sql
# Consent Expiry Watchdog — runs daily at 06:00 IST
# No distributed lock needed (runs once per day, no overlap risk)

STEP 1: Mark already-expired consents
  UPDATE consent_records
    SET status='expired', updated_at=NOW()
    WHERE status='active' AND expires_at < NOW();

  FOR each newly expired record:
    INSERT INTO audit_log (action='CONSENT_EXPIRED', details={purpose_code, expired_at})
    IF record.consent_handle_id IS NOT NULL:
      UPDATE consent_handles SET status='expired', updated_at=NOW()
        WHERE consent_id=record.consent_handle_id;

STEP 2: Find consents expiring in next 7 days
  expiring_soon = SELECT cr.*, u.preferred_language, u.user_id, f.family_id
    FROM consent_records cr
    JOIN users u ON cr.user_id = u.user_id
    JOIN families f ON cr.family_id = f.family_id
    WHERE cr.status = 'active'
    AND cr.expires_at BETWEEN NOW() AND NOW() + INTERVAL '7 days';

STEP 3: For each expiring consent, send notification
  days_remaining = CEIL((record.expires_at - NOW()) / INTERVAL '1 day')
  priority = 'HIGH' IF days_remaining <= 1 ELSE 'MEDIUM'

  # v1.4: who is told. A notice goes to someone who can act on it:
  #   subject is an ordinary adult            -> the subject
  #   subject is managed                      -> the CURRENT primary proxy (secondary if the primary is
  #                                              unavailable, §2.6.1), resolved now, not at grant time
  #   subject is a child with a login (minor) -> the child AND the parents / legal guardians (v_guardians)
  # recipients = resolve_consent_recipients(record)   # live users only; if empty -> notify_admin HIGH
  notify_user(user_id=recipients, message=
    f'Your {purpose_registry[record.purpose_code].description} access expires in'
    f' {days_remaining} day(s). Renew to continue.',
    action_url='/settings/consent/{record.record_id}/renew',
    language=user.preferred_language
  )
  # Also notify Admin if purpose_code is DPI (financial or health access)
  IF purpose_registry[record.purpose_code].dpi_required:
    notify_admin(family_id=record.family_id,
      message=f'{user.display_name}\'s {description} access expires in {days_remaining} day(s).'
    )

STEP 4: Escalation for ignored expiry
  # Find consents that expired MORE THAN 3 days ago with no renewal attempt
  stale_expired = SELECT * FROM consent_records
    WHERE status='expired'
    AND expires_at < NOW() - INTERVAL '3 days'
    AND updated_at = expires_at;  -- no renewal attempt made

  FOR each stale record:
    notify_admin(family_id=record.family_id, priority='HIGH',
      message=f'IMPORTANT: {purpose_description} access expired 3+ days ago.
        Any features relying on this will fail until renewed.'
    )
```

### 7.3 Renewal Flow

```sql
# Renewal is triggered from notification CTA or settings > privacy > active consents
# Renewal = revoke old consent + issue new consent grant (Steps 1-8 in §4.2)
# NOT an in-place update — new consent_record and new consent_handle are created

Step 1: Show renewal UI
  Display: current consent details, new expiry date, what user is renewing
  Pre-populate granted_scope with existing record's granted_scope (user can modify)

Step 2: User confirms (biometric required for DPI consents)

Step 3: Capture rate limit state from old handle (Fix 3 — v1.1)
  # Do this BEFORE revoking old handle so we can read its current state.
  old_fetch_count = NULL
  IF old_record.consent_handle_id IS NOT NULL:
    old_handle = SELECT * FROM consent_handles WHERE consent_id = old_record.consent_handle_id
    # Inherit fetch_count_today if the old handle was revoked recently.
    # Without this, a user can spam renewal to reset the AA 3 fetch/hour limit.
    # Sahamati's limit is per-handle, but RBI expects per-user intent.
    # Rule: if old handle was active within the last hour, inherit its count.
    one_hour_ago = NOW() - INTERVAL '1 hour'
    IF old_handle.last_fetched_at IS NOT NULL AND old_handle.last_fetched_at > one_hour_ago:
      old_fetch_count = old_handle.fetch_count_today
      # New handle will inherit this count — effective hourly budget continues.
    ELSE:
      old_fetch_count = 0  # Old handle idle for >1 hour, no inheritance needed

Step 4: Revoke old record
  UPDATE consent_records SET status='expired', revoked_at=NOW()
    WHERE record_id=old_record_id
  IF old consent_handle_id IS NOT NULL:
    Revoke old DPI handle (see §4.3 Step 3)

Step 5: Grant new consent (full §4.2 flow)
  New consent_record created with new expires_at
  New consent_handle created if DPI:
    INSERT INTO consent_handles (...,
      fetch_count_today = COALESCE(old_fetch_count, 0),
      -- Inherit rate-limit state. Renewing does not reset the hourly budget.
      last_fetched_at  = old_handle.last_fetched_at   -- also inherited
    )

Step 6: Write audit_log: CONSENT_RENEWED
  Details: purpose_code, previous_expires_at, new_expires_at,
           new_consent_handle_id, inherited_fetch_count: old_fetch_count
```

## 8. Revocation Propagation

### 8.1 Two Types of Revocation

| Type | Trigger | Detection | Processing Time |
|---|---|---|---|
| User-Initiated (Withdrawal) | User taps 'Disconnect' or 'Revoke' in FamilyLifeOS settings | Synchronous — user action in the app | Immediate (within the request/response cycle) |
| External (DPI Webhook) | User revokes consent on AA app, bank app, ABHA app, or DigiLocker — outside FamilyLifeOS | Asynchronous — DPI fires webhook to our endpoint | Within 60 seconds of webhook receipt (see §9) |

### 8.2 Revocation Propagation Sequence (Both Types)

```sql
# Executed atomically for user-initiated revocation.
# For external revocation: Steps 1-2 execute in webhook handler (§9),
# Steps 3-5 execute via Healer CONSENT_REFRESH task.

Step 1: Update consent_handles (external handle first — must revoke DPI before DB)
  IF external revocation: DPI has already revoked — just update our record
  IF user-initiated: POST revocation to DPI API, then update
  UPDATE consent_handles SET status='revoked', revoked_at=NOW()
  UPDATE consent_records  SET status='revoked'|'withdrawn', revoked_at=NOW()

Step 2: Set revalidation_required (for webhook path — defensive signal to Healer)
  For external revocation: initially set revalidation_required=TRUE on webhook receipt
  After records updated: set revalidation_required=FALSE (revocation confirmed)

Step 3: Purge cached data associated with this consent
  IF purpose_code = 'AA_BALANCE_FETCH' | 'AA_TRANSACTION_HISTORY':
    Invalidate supervisor_sessions cached balance/transaction data for this user
    (Set Redis TTL = 0 for relevant keys, or mark session cache as stale)
  IF purpose_code = 'ABHA_*':
    Purge any in-memory health data associated with this user's session
  DO NOT delete vault documents — those are stored by user choice, not consent-gated

Step 4: Cancel pending Healer tasks that use this consent
  UPDATE offline_task_queue SET status='cancelled'   -- valid status since Data Model v1.3 §3.9
    WHERE payload->>'consent_handle_id' = revoked_handle_id
    AND status = 'pending';

Step 5: Notify affected parties
  Notify user: 'Your [purpose description] access has been disconnected.'
  IF DPI financial consent revoked: notify Admin (financial access interrupted)
  IF DPI health consent revoked: notify Admin only if SOS or active monitoring active

Step 6: Write audit_log
  CONSENT_WITHDRAWN (user-initiated) | CONSENT_REVOKED_EXTERNAL (DPI webhook)
  Details include: purpose_code, revoked_at, tasks_cancelled_count, cache_purged: true
```

### 8.3 What Happens to Active Sessions During Revocation

| Session State at Time of Revocation | Action |
|---|---|
| IDLE / INTENT_ANALYSIS / REASONING | Session aborted cleanly. Next CONSENT_REVERIFY check would have caught this anyway. |
| CONSENT_REVERIFY (waiting for gate) | Gate fails (Check 1 or 2). Session → CONSENT_REVERIFY_FAILED. No money moved. |
| EXECUTION (BBPS call in flight) | Cannot be stopped mid-flight. Healer monitors for completion. If payment succeeds, Healer writes audit log. Admin notified that payment completed despite consent revocation (rare edge case — CONSENT_REVERIFY ran before revocation propagated). |
| SUCCESS_CONFIRMATION | Session already complete. Revocation does not undo the payment. Audit log entry for revocation is written separately. |
| FAILED / ABORTED | Terminal states. Revocation is logged but has no operational effect. |

> ⚠ WARNING: The EXECUTION state edge case (payment in flight when revocation arrives) is real but extremely narrow. The sequence is: user approves payment → CONSENT_REVERIFY passes → user immediately opens AA app and revokes → webhook arrives → payment completes. The correct resolution is: payment stands (user approved it before revocation), revocation applies to future operations. Admin is notified. This is consistent with 'Human sovereignty — agents execute only what the human approved.'

## 9. Webhook Security: HMAC Validation

### 9.1 Attack Surface

The revalidation_required flag on consent_handles is set by DPI webhooks. If the webhook endpoint is unauthenticated, an attacker who discovers the endpoint URL can POST a fabricated revocation event, setting revalidation_required=TRUE for any or all users. This causes every subsequent transaction to fail at G5 CONSENT_REVERIFY (because the live DPI validation call fires). This is a targeted denial-of-service attack that requires no credentials — just the endpoint URL.
This attack surface was flagged as a live threat by both independent reviewers of the Financial Transaction Safety spec. It must be closed before the first external DPI integration goes live.

### 9.2 Sahamati Webhook Specification

```text
# Sahamati AA Network webhook format (FIU webhook documentation)
# Sent to: POST /api/v1/webhooks/aa/consent-notification

Headers:
  Content-Type: application/json
  x-jws-signature: <JWS compact serialization of payload>
  # JWS = JSON Web Signature (RFC 7515)
  # Signed with Sahamati's AA network private key
  # FamilyLifeOS must verify signature using Sahamati's published public key

Body:
{
  'ver': '2.0.0',
  'timestamp': '2026-02-21T10:30:00.000Z',
  'txnid': 'f35761ac-4a18-11e8-96ff-0277a9fbfedc',  # unique per notification
  'Notifier': { 'type': 'AA', 'id': 'sahamati.aa' },
  'ConsentStatusNotification': {
    'consentId': '<UUID of consent in Sahamati system>',
    'consentHandle': '<UUID — maps to consent_handles.external_consent_id>',
    'consentStatus': 'REVOKED' | 'PAUSED' | 'ACTIVE' | 'EXPIRED'
  }
}
```

### 9.3 HMAC Validation Algorithm

```sql
# Webhook handler: POST /api/v1/webhooks/aa/consent-notification
# This handler runs BEFORE any database writes

STEP 1: Extract signature
  jws = request.headers['x-jws-signature']
  IF jws is None: return 401 (reject immediately, no logging of payload)

STEP 2: Verify JWS signature
  # Sahamati publishes its public key at: https://api.sahamati.org.in/.well-known/jwks
  # Cache this key locally (refresh every 24 hours)
  sahamati_public_key = load_cached_jwks() OR fetch_from_sahamati_jwks()
  try:
    verified_payload = jws_verify(jws, sahamati_public_key)
    # jws_verify throws if signature is invalid
  except SignatureVerificationError:
    log.warn('Webhook: invalid JWS signature', remote_ip=request.remote_addr)
    return 401  # Do NOT process. Do NOT set revalidation_required.

STEP 3: Replay prevention
  txnid = verified_payload['txnid']
  timestamp = verified_payload['timestamp']

  # Check timestamp is recent (within 5 minutes — prevents replayed old webhooks)
  IF abs(NOW() - parse_iso(timestamp)) > 5 * 60:  # seconds
    log.warn('Webhook: timestamp outside 5-minute window', txnid=txnid)
    return 400

  # Check txnid not already processed (idempotency — Sahamati may retry)
  IF redis.EXISTS(f'webhook:processed:{txnid}'):
    return 200  # Already processed — acknowledge without re-processing
  redis.SETEX(f'webhook:processed:{txnid}', 600, '1')  # TTL: 10 minutes

STEP 4: Process the notification (wrapped in a DB transaction — Fix 5, v1.1)
  # Without this transaction, audit_log INSERT failure after consent_handles UPDATE
  # leaves the system partially updated: revalidation_required is set but no audit
  # record exists. Partial state is indistinguishable from a successful but unlogged
  # revocation. Wrap everything.
  BEGIN;
    consent_handle_id = verified_payload['ConsentStatusNotification']['consentHandle']
    new_status = verified_payload['ConsentStatusNotification']['consentStatus']

    handle = SELECT * FROM consent_handles
      WHERE external_consent_id = consent_handle_id AND provider = 'AA'
      FOR UPDATE;  # Lock row to prevent concurrent webhook processing

    IF handle is None:
      ROLLBACK;
      log.warn('Webhook: unknown consentHandle', handle=consent_handle_id)
      return 200  # Acknowledge (may be from a different FIU using same Sahamati infra)

    CASE new_status:
      'REVOKED': SET revalidation_required = TRUE   # Full propagation via §8
      'PAUSED':  SET revalidation_required = TRUE   # Treat as requires revalidation
      'ACTIVE':  SET revalidation_required = FALSE  # Consent re-activated
      'EXPIRED': SET status = 'expired'             # Watchdog will also catch this

    UPDATE consent_handles
      SET revalidation_required = ..., status = ..., updated_at = NOW()
      WHERE consent_id = handle.consent_id;

    INSERT INTO audit_log (action='CONSENT_REVOKED_EXTERNAL', details={
      provider: 'AA', external_consent_id: consent_handle_id,
      new_status: new_status, txnid: txnid, processed_at: NOW()
    });
  COMMIT;
  # If COMMIT fails: return 500. Sahamati will retry. Redis txnid key will expire
  # in 10 minutes, so the retry will be processed (not deduped). Safe.

  return 200  # Acknowledge to Sahamati
```

### 9.4 ABHA Webhook Security

```text
# ABDM uses a different callback mechanism: signed JWT in Authorization header
# Endpoint: POST /api/v1/webhooks/abha/consent-notification

Validation sequence:
1. Extract JWT from Authorization: Bearer <token> header
2. Fetch ABDM's JWKS from https://dev.abdm.gov.in/.well-known/openid-configuration
3. Verify JWT signature using ABDM's public key
4. Verify JWT claims: iss=ABDM, aud=FAMILYLIFEOS_HIU_ID, exp > NOW()
5. Extract consent request ID and new status
6. Replay prevention: check jti (JWT ID) in Redis (same pattern as §9.3 Step 3)
7. Process: identical to §9.3 Step 4 for ABHA handles
```

### 9.5 Failure Handling for Webhook Validation

| Failure Scenario | Response Code | Action | revalidation_required Set? |
|---|---|---|---|
| No signature header | 401 | Log warning with remote IP. No DB write. | No |
| Invalid JWS/JWT signature | 401 | Log warning. Alert if >5 invalid signatures in 1 hour (potential attack). | No |
| Timestamp > 5 min old | 400 | Log. May be a delayed retry from Sahamati — safe to reject. | No |
| Duplicate txnid/jti | 200 | Already processed. Acknowledge without re-processing. | No (already set) |
| Unknown consentHandle | 200 | Log. Acknowledge (may be from another FIU). No DB write. | No |
| DB write fails after validation | 500 | Log. Sahamati will retry. revalidation_required not yet set — safe state. | No |
| JWKS fetch fails (Sahamati unreachable) | 503 | Use cached public key (24h TTL). If cache expired: reject all webhooks with 503 until key refreshed. | No |

> 🔴 CRITICAL: If the JWKS cache expires and Sahamati's key endpoint is unreachable, all incoming webhooks must be rejected with 503 — not processed without validation. An unvalidated webhook is indistinguishable from a forged one. The safe default is: reject. Alert Admin. Monitor for Sahamati recovery.

## 10. Regulation-Agnostic Extension Points

### 10.1 What Was Built For Future Jurisdictions

The following design decisions were made specifically to allow adding a new jurisdiction without refactoring:
- jurisdiction field on consent_records — the only field that needs to change per user to activate different rules
- jurisdiction_overrides config (§3.3) — jurisdiction-specific retention periods and lawful bases are configuration, not code
- lawful_basis field on consent_records — captures which legal basis applies, enabling jurisdiction-specific enforcement
- purpose_registry.minor_allowed flag — minor protection rules can be toggled per purpose without schema changes
- Audit trail completeness — GDPR Article 30 (Records of Processing Activities) requires a processing log. Our audit_log already satisfies this.
- Data portability endpoint (§4.5) — built to be regulation-agnostic. GDPR Article 20 portability requires machine-readable format. Our JSON export already satisfies this.

### 10.2 What Adding GDPR Would Actually Require

When FamilyLifeOS has EU users, adding GDPR enforcement is a configuration exercise, not a rebuild:

| GDPR Requirement | What Needs to Change | Effort |
|---|---|---|
| Art. 13/14: Right to information | Consent UI must display retention period and controller identity. Already implemented (§4.2 Step 3). | None — already done |
| Art. 15: Right of access | Data export endpoint (§4.5) already satisfies this. | None — already done |
| Art. 17: Right to erasure | Account deletion (§2.2) already satisfies this. GDPR requires 'without undue delay' — our 24h window qualifies. | None — already done |
| Art. 20: Data portability | JSON export (§4.5) already satisfies this. | None — already done |
| Art. 6: Lawful basis | Add 'legitimate_interest' as a valid lawful_basis value for EU users. Update jurisdiction_overrides config for analytics purpose. | Config change: 1 day |
| Art. 30: Records of processing | Add FAMILYLIFEOS_HIU_ID and FIU registration details to a static RoPA document. Audit_log already captures per-processing records. | Documentation: 1 day |
| Art. 37: DPO appointment | Required if processing at scale. Appoint Data Protection Officer. Not a code change. | Legal/HR: not code |
| 72h breach notification to supervisory authority | Already in breach protocol (§2.4). Update notification targets to include relevant EU DPA. | Config change: 1 day |

### 10.3 What Is Deliberately Not Built in v1

- GDPR legitimate_interest assessment workflow — requires documented balancing test per processing activity. Not needed for India-only users.
- CCPA opt-out pipeline — California Consumer Privacy Act has specific 'Do Not Sell My Personal Information' requirements. Not applicable until US users.
- Data Protection Officer (DPO) portal — GDPR Article 37 DPO appointment and formal records. Not required under DPDP Act for early-stage companies.
- Cross-border data transfer mechanisms (SCCs, BCRs) — only relevant when data flows out of India to EU or vice versa. Not in v1 scope.
- Automated decision-making rights (GDPR Art. 22) — the Supervisor makes recommendations, humans decide. This principle is already in our architecture. Formal GDPR Art. 22 documentation deferred.

## 11. Canonical Flow: Priya Connects HDFC Bank (AA Consent)

### 11.1 Context

This is the reference implementation for all AA consent integration. Priya (MEMBER role, Sharma family) wants to enable the FinanceAgent to fetch her HDFC bank balance for BESCOM bill payment verification. She has never connected HDFC before. No existing consent_record exists for purpose_code='AA_BALANCE_FETCH' for her user_id.

### 11.2 Happy Path (Full Sequence)

```sql
T+0:    Priya says: 'Pay my BESCOM electricity bill'
        Supervisor enters INTENT_ANALYSIS

T+1:    RBAC check passes (MEMBER can access Finance module)
        Supervisor checks for active AA_BALANCE_FETCH consent
        → SELECT FROM consent_records WHERE user_id=Priya AND purpose_code='AA_BALANCE_FETCH'
        → No row found

T+2:    Supervisor routes to Consent Grant Sub-Flow (pauses bill payment intent)

T+3:    Consent UI shown to Priya (Hindi: preferred_language):
        'HDFC बैंक बैलेंस देखने की अनुमति'
        'FamilyLifeOS आपके HDFC खाते का बैलेंस देखेगा।'
        'यह डेटा 15 मिनट के लिए रखा जाएगा।'
        'आप कभी भी इसे वापस ले सकते हैं।'
        [अनुमति दें]  [नहीं]

T+4:    Priya taps 'अनुमति दें', confirms with fingerprint

T+5:    AA Adapter initiates consent request to Sahamati:
        POST /Consent { fi_types:['DEPOSIT'], fip_ids:['HDFC'], expiry: 1 year }
        Response: { consentHandle: 'ch-abc-123' }
        INSERT INTO consent_handles (status='pending', external_consent_id='ch-abc-123')

T+6:    Priya receives push notification:
        'Please approve access on your HDFC NetBanking app'
        (FamilyLifeOS polls Sahamati every 30 seconds)

T+90s:  Priya approves on HDFC app
        Sahamati fires webhook → POST /webhooks/aa/consent-notification
        { consentHandle: 'ch-abc-123', consentStatus: 'ACTIVE' }
        Webhook HMAC validated (§9.3)
        UPDATE consent_handles SET status='active', revalidation_required=FALSE

T+92s:  FamilyLifeOS poll confirms active
        BEGIN TRANSACTION;
          INSERT INTO consent_records (
            purpose_code='AA_BALANCE_FETCH', status='active',
            granted_at=NOW(), expires_at=NOW()+1year,
            consent_handle_id=ch_uuid, granted_scope={fi_types:['DEPOSIT'],fip_ids:['HDFC']}
          );
          INSERT INTO audit_log (action='CONSENT_GRANTED', details={...});
        COMMIT;

T+93s:  Supervisor resumes bill payment intent
        Enters pre-execution gates:
        G3: AA balance fetch → passes (using new consent)
        G5: CONSENT_REVERIFY → passes (record just created, revalidation_required=FALSE)
        → Proceeds to EXECUTION

Audit log entries written:
  1. CONSENT_GRANTED (T+92s)
  2. BILL_PAYMENT_INITIATED (after G5 pass)
```

### 11.3 Failure Modes

| Failure Point | Error | Action | User Experience |
|---|---|---|---|
| Sahamati POST /Consent returns 500 | CONSENT_001: AA gateway error | Log, notify user. Allow retry after 30 seconds. | Bank connection unavailable. Please try again. |
| Priya declines on HDFC app | CONSENT_002: User rejected on AA app | UPDATE consent_handles status='revoked'. Abort consent flow. | You declined bank access. Bill payment cannot proceed without it. |
| 10-minute approval timeout | CONSENT_003: AA consent approval timeout | UPDATE consent_handles status='expired'. Allow retry. | Approval timed out. Please try connecting your bank again. |
| Sahamati JWKS unavailable for webhook | CONSENT_004: Webhook validation failed | Reject webhook with 503. Poller detects status change. Consent proceeds via poll. | (No user impact if poller catches it within 30s) |
| consent_records INSERT fails (DB error) | CONSENT_005: Grant write failure | Log. Sahamati handle is active but our record not written. Alert via system monitor. Manual resolution required. | Bank connected, but we encountered a problem. Please contact support. |

## 12. Q&A

| Asked By | Question | Answer |
|---|---|---|
| Engineering | Why is consent_records a separate table from consent_handles? Couldn't we just extend consent_handles? | consent_handles is the Layer 3 external reference store — it maps to what DPI systems know about us. consent_records is the Layer 1 first-party legal record — it captures what the user agreed to in FamilyLifeOS, in plain language, with parental consent tracking, jurisdiction, and lawful basis. Not all consent_records have consent_handles (voice processing consent, device registration). Merging them would force DPI-specific fields (external_consent_id, provider, fetch_count_today) onto first-party records, and first-party fields (jurisdiction, lawful_basis, parental_consent_user_id) onto DPI records. The two tables represent different concerns at different layers of the architecture (§1.4). |
| Legal/Compliance | Is the DPDP Act 2023 actually in force? The Rules are not yet notified. | Correct. As of February 2026, DPDP Act 2023 has received Presidential assent but the implementing Rules (which specify enforcement details, exemptions, and the Data Protection Board composition) are not yet notified. The Act provisions are not yet in effect. However: (a) implementing the framework now costs less than retrofitting it later, (b) RBI and ABDM consent requirements are already in force via separate regulations, (c) the framework we've built satisfies the Act's requirements as drafted — when Rules are notified, we expect minor config changes rather than architectural changes. Monitor: Ministry of Electronics and IT (MeitY) notifications. |
| Engineering | What happens if a consent_record is active but the DPI's external handle has already expired (out-of-sync state)? | This is the revalidation_required flag's primary use case. If Sahamati's handle expires without our webhook receiving the notification (network failure, webhook delivery failure), our consent_record shows 'active' but the AA handle is expired. CONSENT_REVERIFY Check 2 performs a live DPI status call when revalidation_required=TRUE. But if revalidation_required is FALSE (normal path), we rely on the expiry watchdog catching the discrepancy. Defense: the expiry watchdog (§7) runs daily and can detect consent_records with expires_at mismatches by polling DPI status. For high-value consents (AA financial), the TTL in FSM spec (15 min balance cache) also limits the blast radius — a stale balance fetch fails gracefully rather than using dangerously stale data. |
| Engineering | Can two CONSENT_REVERIFY checks run simultaneously for the same user (race condition)? | Yes, and it's safe. CONSENT_REVERIFY reads from consent_records and consent_handles — both are SELECT queries (no write during the check). The reads are non-conflicting. The only write is when revalidation_required is cleared after a successful live DPI validation — this is an idempotent UPDATE (setting FALSE to FALSE has no effect). Two concurrent CONSENT_REVERIFY checks that both clear revalidation_required produce the same result as one. The resource_lock at G2 ensures only one payment session per (family_id, biller_id) can reach G5 — so true simultaneous CONSENT_REVERIFY for the same payment is already impossible. |
| Legal/Compliance | Under DPDP Act, can FamilyLifeOS use data collected under one purpose for another purpose (purpose creep)? | No. Section 6(3) of DPDP Act explicitly states that a Data Principal's consent is valid only for the specified purpose. Reusing data collected under AA_BALANCE_FETCH for PRODUCT_ANALYTICS (even if anonymised) would require a separate consent for PRODUCT_ANALYTICS. Our purpose_registry enforces this architecturally: the purpose_code on a consent_record is immutable post-grant. Any new use must have its own purpose_code and its own consent_record. This is also why PRODUCT_ANALYTICS is listed in the purpose_registry as 'essential: No' and 'minor_allowed: No' — users must explicitly opt in, and it cannot be bundled with the core product consent. |
| Operations | The AA consent expires after 1 year. What if the user is on holiday and misses the renewal notification? | The expiry watchdog sends notifications at T-7 days, T-3 days, and T-1 day (HIGH priority for last two). If still not renewed at expiry: consent_record becomes 'expired', all AA fetches return CONSENT_REVERIFY_FAILED, and the user is shown the renewal CTA on next app open. No data is lost. The bill payment queue will hold retries for 48 hours (offline_task_queue expiry) — if the user renews within 48 hours, the queued payment can be retried. After 48 hours, the session fails permanently and the user must re-initiate. This is acceptable — a missed electricity bill payment due to consent expiry is recoverable; a missed consent that exposes financial data is not. |
| Engineering | What prevents a compromised Supervisor from granting its own consent for a user? | Three controls: (a) consent_grant requires explicit user biometric confirmation (Step 4 in §4.2) — the Supervisor can present the consent UI but cannot simulate the biometric confirm. (b) consent_records.user_id is set from the authenticated session, not from Supervisor input — the Supervisor cannot grant consent as a different user. (c) The audit_log CONSENT_GRANTED entry includes actor=user_id (the human who confirmed biometrically), not SYSTEM_ACTOR_UUID — any grant with actor=SYSTEM_ACTOR_UUID would be a data integrity violation detectable by the hash chain. The Supervisor can only prompt for consent; it cannot grant it. |

— End of Tech_Spec_Consent_Manager (v1.4, revision in review) —
