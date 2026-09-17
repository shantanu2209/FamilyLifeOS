# Data Model Schema

_FamilyLifeOS Core — Canonical Database Specification_

> **Status:** v1.3 — REVISION IN REVIEW (unfrozen 2026-09-17 for founder-approved changes; re-freezes after Codex review round 2), Phase 1 (Foundation) · **Author:** Shantanu Chaudhary (Lead Product Architect) · **Last content change:** 2026-09-17
> **Canonical copy.** Converted to Markdown on 2026-09-16 from `Data_Model_Schema_v1.2.1.docx` (original kept in `archive/originals/`). v1.2.1 content was converted unchanged; the v1.3 revision was then made directly in this Markdown file (see §9.4 for the change summary). Superseded versions in the archive: `Data_Model_Schema.docx` (v1.0–v1.1), `Data_Model_Schema_v1.2.docx`.
> **Cited elsewhere as:** Data Model v1.3, Data_Model_Schema v1.2.1 (frozen predecessor), Data_Model_Schema_v1_2_1, DM §n.

## 0. Document Governance

| Version | Date | Description of Change | Author |
|---|---|---|---|
| v1.0 | 2026-02-21 | Initial release. Full schema, ERD, graph traversal queries, cardinality enforcement, RBAC queries, lifecycle management, and seed data. | Shantanu Chaudhary |
| v1.1 | 2026-02-21 | Post-review hardening: canonical JSON serialisation for hash computation; state-appropriate session expiry (remove default); partial unique index for consent_handles; revalidation_required flag for external revocation; bidirectional relationship atomicity mandate; resource_lock unique index + Healer lock-null; SYSTEM actor + SHADOW_NODE_EXPIRED taxonomy; cardinality FOR UPDATE mandate. | Shantanu Chaudhary |
| v1.2 | 2026-02-21 | Architecture freeze release: soft-delete consistency mandate (new §4.3); CHECK constraints on users (shadow_node ↔ shadow_expires_at) and consent_handles (revoked_at, expires_at > granted_at); tracker updated with typed payload models escalation and webhook signature validation note. TOC added. | Shantanu Chaudhary |
| v1.2.1 | 2026-02-21 | Documentation patch (no DDL changes): Q1 query annotated to clarify SYSTEM_ACTOR family isolation; audit_log.fsm_exit_state comment linked to NFR v2.1 telemetry enum. Tracker: Security_Threat_Model.md escalated from P1 to late-P0; offline_task_queue composite idempotency key added to parking lot. | Shantanu Chaudhary |
| v1.3 | 2026-09-17 | Revision for the founder decisions of 2026-09-17 and Inconsistency Register items 1–3, 7, 8, 10–12 (see §9.4 for the full list): roles renamed spouse→member, child→minor; resource lock moved to its own `resource_lock` table (§3.11); `supervisor_sessions` gains intent_type, bbps_transaction_ref_id, healer_poll_count, session_notes; `offline_task_queue.status` gains 'cancelled'; `consent_handles.provider` gains 'ONDC'; `consent_records`, `consent_ui_disclosures` and the enforce_dpi_handle trigger folded in from Consent Manager v1.1 (§3.12–3.13); registry tables folded in from Module Registry (§3.14–3.15); `role_module_permissions` and the four kernel views (§3.16–3.17); audit write protocol `fn_lock_audit_tail` / `fn_append_audit` (§3.18); action taxonomy widened to the union across specs (§6); session-expiry cleanup no longer aborts EXECUTION sessions (§7.4); NULL previous_hash serialises as '' (§3.6, Q12); seed UUIDs made valid (§8); all kernel objects in schema `core` (§1.1). No database exists yet, so V001 is authored from this version. | Shantanu Chaudhary (with Claude Code) |

## Table of Contents

- **1. Purpose & Design Philosophy** — 1.1 Core Design Principles • 1.2 Scope
- **2. Entity-Relationship Overview** — ERD diagram of the ten original core tables plus a note on the v1.3 additions
- **3. Table Definitions (Full DDL)** — 3.1 families • 3.2 users • 3.3 family_relationships • 3.4 proxy_assignments • 3.5 consent_handles • 3.6 audit_log (NFR-linked) • 3.7 supervisor_sessions • 3.8 device_registry • 3.9 offline_task_queue • 3.10 updated_at trigger • 3.11 resource_lock • 3.12 consent_records • 3.13 consent_ui_disclosures • 3.14 module_registry & intent_routes • 3.15 family_module_activations • 3.16 role_module_permissions • 3.17 kernel views • 3.18 audit write protocol
- **4. Cardinality Rules & Application-Layer Enforcement** — 4.1 Admin Minimum Constraint • 4.2 Shadow Node Rules • 4.3 Soft Delete Consistency Mandate
- **5. Graph Traversal & Operational Queries** — Q1 All Members (SYSTEM_ACTOR note) • Q2 RBAC Check • Q3 Proxies • Q4 Admins • Q5 Consent Expiry Watchdog • Q6 CONSENT_REVERIFY • Q7 Resource Lock • Q8 Audit Feed • Q9 Shadow Purge • Q10 Healer Queue • Q11 Relationship Map • Q12 Hash Chain Verify
- **6. Audit Log Action Taxonomy** — 40 standardised action codes (union across all specs) • SYSTEM_ACTOR_UUID convention
- **7. Data Lifecycle Management** — 7.1 Soft Delete & DPDP • 7.2 Hash Chain Schedule • 7.3 Rate Limit Reset • 7.4 Session Expiry Cleanup
- **8. Seed Data (Development & Testing)** — Sharma Family canonical test scenario
- **9. Migration Notes & Schema Evolution** — 9.1 Stability Commitment • 9.2 Alembic • 9.3 Module Table Convention • 9.4 v1.3 Change Summary & Migration Plan
- **10. Open Issues & Q&A** — Resolved issues • 7 Q&A entries

## 1. Purpose & Design Philosophy

This document is the canonical database specification for FamilyLifeOS. It defines every table, column, index, constraint, and query pattern that the engineering team will use to implement the Core Kernel. Every other technical document (FSM Spec, Financial Transaction Safety, Consent Manager) depends on this schema being stable and agreed upon before implementation begins.

> ⚠ REVISION IN REVIEW (v1.3): unfrozen on 2026-09-17 to apply three founder-approved decisions (role names, resource lock table, session columns) and to fold in the tables that Consent Manager v1.1 and Module Registry v1.0 had defined outside this document. Codex runs review round 2; on approval the document re-freezes. v1.2.1 passed two independent reviews.
> Schema changes after a freeze require: a written migration plan (Alembic file), review of all affected queries in Section 5, backward-compatible changes only, and team announcement before merging.
> All other P0 documents reference this schema by table and column name. If any other document's DDL differs from this one, this document wins.

### 1.1 Core Design Principles

- Family-as-unit: The family_id is the top-level partition key for all data. Everything belongs to a family, not just an individual.
- Privacy-by-default: No raw credentials, passwords, Aadhaar numbers, or UPI IDs are stored in the application database. Only consent handles and UUIDs.
- Soft-delete over hard-delete: User data is never immediately purged on deletion requests. A deleted_at timestamp is set; a nightly purge job executes the actual removal after 24 hours (DPDP Act compliance window).
- Append-only audit: The audit_log table is append-only. No UPDATE or DELETE operations are permitted on it. Tamper detection is via hash chain.
- Application-layer cardinality: Business rules like 'max 2 admins per family' are enforced in the application service layer, not via database constraints. The database stores the data; the service enforces the rules. This avoids complex deferred constraint failures.
- Managed services: This schema targets AWS RDS for PostgreSQL (version 15+). No extensions beyond pgcrypto (for UUID generation) are required. The portfolio build runs the same DDL on PostgreSQL 15+ in Docker Compose.
- Kernel schema (v1.3): every table, view and function in this document lives in the PostgreSQL schema `core`. Kernel code connects with `search_path = core`, so the DDL and queries below are written unqualified. Each Core Module owns its own schema named after its module_id and may read `core` only through the whitelisted views in §3.17 and write audit rows only through the functions in §3.18 (Module Registry §7.2).

### 1.2 Scope of This Document

- Covered: Core Family Graph tables (families, users, relationships, proxies, consent handles, audit log), session persistence, device registry, offline task queue, and since v1.3: the resource lock, first-party consent records and disclosures, the module registry and per-family activations, role permissions, the kernel views modules may read, and the audit write functions.
- Not covered: Module-specific tables (Finance, Health, Vault, HomeOps). These are defined in the module PRDs and specs. Each module owns its own schema (§9.3) and always references core.users.user_id and core.families.family_id as foreign keys.

## 2. Entity-Relationship Overview

The following diagram describes the relationships between core tables. Cardinality notation: ||—|| (exactly one), ||—o{ (one to zero-or-many), }o—o{ (many-to-many via join table).

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                         FAMILYLIFEOS CORE ERD                           │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────┐           ┌──────────────────┐        ┌────────────────────┐
│   families   │ 1      *  │      users        │ 1   * │ family_relationships│
│──────────────│───────────│──────────────────│────────│────────────────────│
│ family_id PK │           │ user_id PK        │        │ relationship_id PK  │
│ family_name  │           │ family_id FK      │        │ family_id FK        │
│ sub_tier     │           │ role              │        │ from_user_id FK     │
│ sub_expires  │           │ display_name      │        │ to_user_id FK       │
└──────────────┘           │ phone_number      │        │ relationship_type   │
                           │ verification      │        └────────────────────┘
                           │ shadow_node       │
                           │ preferred_lang    │        ┌────────────────────┐
                           │ deleted_at        │ 1   *  │  proxy_assignments │
                           └──────────────────┘────────│────────────────────│
                                    │                   │ proxy_id PK         │
                                    │                   │ managed_user_id FK  │
                                    │ 1              *  │ proxy_user_id FK    │
                           ┌──────────────────┐        │ proxy_rank          │
                           │  consent_handles  │        │ conflict_rule       │
                           │──────────────────│        └────────────────────┘
                           │ consent_id PK     │
                           │ user_id FK        │        ┌────────────────────┐
                           │ provider          │        │   audit_log        │
                           │ external_id       │        │────────────────────│
                           │ status            │        │ log_id PK          │
                           │ expires_at        │        │ family_id FK       │
                           │ data_scope JSONB  │        │ user_id FK         │
                           └──────────────────┘        │ action             │
                                                        │ details JSONB      │
┌──────────────────────┐                               │ previous_hash      │
│  supervisor_sessions │                               │ current_hash       │
│──────────────────────│                               └────────────────────┘
│ session_id PK        │
│ family_id FK         │   ┌──────────────────────┐   ┌────────────────────┐
│ user_id FK           │   │  device_registry     │   │ offline_task_queue │
│ fsm_state            │   │──────────────────────│   │────────────────────│
│ intent_payload JSONB │   │ device_id PK         │   │ task_id PK         │
│ idempotency_key      │   │ user_id FK           │   │ family_id FK       │
│ created_at           │   │ device_type          │   │ user_id FK         │
│ expires_at           │   │ is_public_surface    │   │ task_type          │
└──────────────────────┘   │ push_token           │   │ payload JSONB      │
                           └──────────────────────┘   │ status             │
                                                       │ retry_count        │
                                                       │ next_retry_at      │
                                                       └────────────────────┘
```

> ℹ  Module tables (e.g., finance.transactions, health.records, secure_vault.documents) are NOT defined here.
> Each module owns its own schema. All module tables use users.user_id and families.family_id as FKs.
> The core schema above is the stable foundation that module schemas depend on.

> ℹ  v1.3 additions not drawn above: resource_lock (family_id, session_id → supervisor_sessions, acquired_by → users) • consent_records (user_id, family_id, consent_handle_id → consent_handles, parental_consent_user_id → users) • consent_ui_disclosures (referenced by consent_records.consent_ui_version) • module_registry ← intent_routes • family_module_activations (family_id, module_id → module_registry, activated_by → users) • role_module_permissions (role, module_id). Definitions in §3.11–3.18.

## 3. Table Definitions (Full DDL)

All tables use PostgreSQL 15+. UUIDs are generated via gen_random_uuid() (requires pgcrypto, enabled by default on AWS RDS). All timestamps are stored as TIMESTAMPTZ (UTC). Application code is responsible for timezone conversion.

> Convention: Every table has a created_at TIMESTAMPTZ DEFAULT NOW(). Tables with mutable rows also have updated_at.
> updated_at is maintained by a trigger (see Section 3.11 for trigger definition).
> Soft-deletes use deleted_at TIMESTAMPTZ NULL. A NULL value means the row is active.

### 3.1 families

The top-level entity. Every other row in the system belongs to a family. Subscription tier is enforced at the application layer — the database simply stores the value.
```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE families (
  family_id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  family_name        VARCHAR(100) NOT NULL,
  -- Subscription: 'free' | 'pro' | 'enterprise'
  subscription_tier  VARCHAR(20)  NOT NULL DEFAULT 'free'
                     CHECK (subscription_tier IN ('free', 'pro', 'enterprise')),
  subscription_expires_at  TIMESTAMPTZ,         -- NULL = free tier (no expiry)
  -- Soft delete: NULL = active, non-NULL = deletion pending
  deleted_at         TIMESTAMPTZ,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- No additional indexes needed: family_id is PK (clustered)
-- families table is small; full scan acceptable for admin queries
```

| Column | Type | Nullable | Description |
|---|---|---|---|
| family_id | UUID | NO | Primary key. Partition key for all child tables. |
| family_name | VARCHAR(100) | NO | Display name. E.g. 'Sharma Family'. Not unique — two families can have the same name. |
| subscription_tier | VARCHAR(20) | NO | free \| pro \| enterprise. Default: free. Enforced at app layer. |
| subscription_expires_at | TIMESTAMPTZ | YES | NULL for free tier. Pro/Enterprise: expiry date for auto-renewal checks. |
| deleted_at | TIMESTAMPTZ | YES | Set on deletion request. Purge job removes row after 24h. |
| created_at / updated_at | TIMESTAMPTZ | NO | Audit timestamps. |

### 3.2 users

Every human (and managed entity) in the system has a user row. This includes actual users who log in (admin, member, minor, elder, staff), non-login managed profiles (managed role: pets, infants, elderly without devices), and passive nodes (passive role: family members who refuse to use the app).
```sql
CREATE TABLE users (
  user_id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  family_id           UUID        NOT NULL REFERENCES families(family_id) ON DELETE CASCADE,

  -- Identity & Auth
  phone_number        VARCHAR(15) UNIQUE,       -- NULL for managed/passive nodes
  email               VARCHAR(255),             -- Optional; used for notifications
  display_name        VARCHAR(100) NOT NULL,    -- 'Ravi Sharma', 'Nani', 'Tommy (Dog)'

  -- Role: determines default RBAC permissions
  -- admin   = Head of House (full control)
  -- member  = Co-Owner: spouse or other adult (shared control)   [v1.3: was 'spouse']
  -- minor   = Child under 18 (guarded access)                    [v1.3: was 'child']
  -- elder   = Parent/In-law (assisted access + SOS)
  -- staff   = Driver/Maid/Cook (context-limited)
  -- managed = No login (pet, infant, senior without device)
  -- passive = No interaction (refuses app)
  role                VARCHAR(20) NOT NULL
                      CHECK (role IN ('admin','member','minor','elder','staff','managed','passive')),

  -- Verification tier: determines trust level for financial operations
  -- unverified   = just created (shadow node or new invite)
  -- otp_verified = confirmed via WhatsApp/SMS OTP
  -- kyc_verified = Aadhaar e-KYC completed (required for staff handling finances)
  verification_status VARCHAR(20) NOT NULL DEFAULT 'unverified'
                      CHECK (verification_status IN ('unverified','otp_verified','kyc_verified')),

  -- Shadow node: created by Admin before user accepts invite
  -- shadow_node = TRUE means user has NOT yet accepted the invite
  -- shadow_expires_at: if not accepted by this date, row is auto-purged
  shadow_node         BOOLEAN     NOT NULL DEFAULT FALSE,
  shadow_expires_at   TIMESTAMPTZ,             -- Only set when shadow_node = TRUE
  -- Invariant: a shadow node must always have an expiry date set.
  -- A non-shadow node must never have one (prevents orphaned expiry dates).
  CONSTRAINT chk_shadow_expiry CHECK (
    (shadow_node = TRUE  AND shadow_expires_at IS NOT NULL) OR
    (shadow_node = FALSE AND shadow_expires_at IS NULL)
  ),

  -- Localization
  preferred_language  VARCHAR(10) NOT NULL DEFAULT 'en'
                      CHECK (preferred_language IN ('en','hi','te','kn','ta','mr','gu','pa','bn','ml')),

  -- Soft delete
  deleted_at          TIMESTAMPTZ,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Composite index: most common query pattern (find all members of a family by role)
CREATE INDEX idx_users_family_role ON users(family_id, role) WHERE deleted_at IS NULL;

-- Phone lookup: OTP login flow
CREATE UNIQUE INDEX idx_users_phone ON users(phone_number) WHERE phone_number IS NOT NULL;

-- Shadow node expiry scan: nightly cron job
CREATE INDEX idx_users_shadow_expiry ON users(shadow_expires_at)
  WHERE shadow_node = TRUE AND deleted_at IS NULL;
```

> ⚠  CARDINALITY RULES (Application-Layer Enforcement — NOT database constraints):
>    • Admins per family: 1–2. Check count before INSERT when role = 'admin'.
>    • Members per family: 0–2. Check count before INSERT when role = 'member'.
>    • Elders per family: 0–4. Check count before INSERT when role = 'elder'.
>    • Staff per family: 0–5. Check count before INSERT when role = 'staff'.
>    • Minors per family: 0–10. Check count before INSERT when role = 'minor'.
>    Enforcement query: SELECT COUNT(*) FROM users WHERE family_id=$1 AND role=$2 AND deleted_at IS NULL

### 3.3 family_relationships

A directed graph of relationships between users. Relationships are bidirectional by convention — if Ravi is the 'parent' of Arjun, there should be a 'child' edge from Arjun to Ravi. The application layer is responsible for creating both edges on member addition.

> ⚠  ATOMICITY REQUIREMENT: Bidirectional edges MUST be written in a single database transaction.
> A crash between the first and second INSERT produces an incoherent graph (Ravi is Arjun's parent, but Arjun has no parent edge).
> The service layer MUST expose a single create_relationship(family_id, user_a, user_b, type) function that wraps both INSERTs in BEGIN / COMMIT.
> Direct INSERT calls to family_relationships outside this function are forbidden.

```sql
CREATE TABLE family_relationships (
  relationship_id  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  family_id        UUID        NOT NULL REFERENCES families(family_id) ON DELETE CASCADE,
  from_user_id     UUID        NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  to_user_id       UUID        NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,

  -- Valid relationship types (directed edge semantics):
  -- 'spouse'   = from_user is married to to_user
  -- 'parent'   = from_user is parent of to_user
  -- 'child'    = from_user is child of to_user
  -- 'sibling'  = from_user is sibling of to_user
  -- 'in_law'   = from_user is in-law of to_user
  -- 'guardian' = from_user is the legal guardian of to_user (v1.3 change 16; set by an admin, Level 0 with passkey;
  --              meant for a minor whose parents are not in the family or not alive)
  -- 'ward'     = from_user is the ward of to_user (reverse edge of 'guardian')
  -- 'employer' = from_user employs to_user (admin → staff)
  -- 'employee' = from_user works for to_user (staff → admin)
  relationship_type VARCHAR(20) NOT NULL
                    CHECK (relationship_type IN
                      ('spouse','parent','child','sibling','in_law','guardian','ward','employer','employee')),

  -- is_active: FALSE for relationships in dissolved households (divorce, separation)
  -- Inactive edges are retained for audit purposes
  is_active        BOOLEAN     NOT NULL DEFAULT TRUE,

  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- Prevent duplicate directed edges
  UNIQUE(from_user_id, to_user_id, relationship_type)
);

-- Find all relationships for a family (admin dashboard)
CREATE INDEX idx_rel_family ON family_relationships(family_id) WHERE is_active = TRUE;

-- Traverse outbound edges for a user (who does user X relate to?)
CREATE INDEX idx_rel_from_user ON family_relationships(from_user_id) WHERE is_active = TRUE;

-- Traverse inbound edges (who is related TO user X?)
CREATE INDEX idx_rel_to_user ON family_relationships(to_user_id) WHERE is_active = TRUE;
```

> Edge Case — Divorced Parents: Both parents can be 'admin' in their own separate family graphs.
> The child user is linked to both via relationship edges across two family_id values.
> Cross-family consent requires explicit Admin approval from both families.
> The current V1 schema does NOT support cross-family relationships. This is a Phase 3+ feature.

### 3.4 proxy_assignments

Defines who manages a Managed Profile node. A managed profile (e.g., elderly parent, infant, pet) has no login capability. Actions on their behalf are taken by their assigned proxies. A managed profile has exactly 1 primary proxy and optionally 1 secondary proxy.
```sql
CREATE TABLE proxy_assignments (
  proxy_id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  family_id               UUID        NOT NULL REFERENCES families(family_id) ON DELETE CASCADE,
  managed_user_id         UUID        NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  proxy_user_id           UUID        NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,

  -- 'primary'   = main caregiver; receives all nudges first
  -- 'secondary' = backup; receives nudge if primary doesn't act within notify_timeout_mins
  proxy_rank              VARCHAR(10) NOT NULL CHECK (proxy_rank IN ('primary','secondary')),

  -- How to resolve conflicting instructions from primary and secondary proxy:
  -- 'hierarchy'     = Primary proxy's action always wins; secondary is overridden silently
  -- 'notify_block'  = Conflicting actions pause execution and alert both proxies + Admin
  -- Set per managed profile during setup. Default: 'hierarchy'
  conflict_resolution_rule VARCHAR(20) NOT NULL DEFAULT 'hierarchy'
                           CHECK (conflict_resolution_rule IN ('hierarchy','notify_block')),

  -- How long (minutes) to wait before escalating to secondary proxy
  notify_timeout_mins     INTEGER     NOT NULL DEFAULT 60
                          CHECK (notify_timeout_mins BETWEEN 5 AND 1440),

  assigned_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- Enforce max 2 proxies: exactly 1 primary + 0-1 secondary
  UNIQUE(managed_user_id, proxy_rank)
);

-- Look up proxies for a managed profile
CREATE INDEX idx_proxy_managed ON proxy_assignments(managed_user_id);

-- Look up all managed profiles for a proxy user (e.g., Spouse manages Nani + Dog Tommy)
CREATE INDEX idx_proxy_user ON proxy_assignments(proxy_user_id);
```

| Scenario | Primary Proxy | Secondary Proxy | conflict_resolution_rule | Outcome |
|---|---|---|---|---|
| Nani's medicine due | Spouse | Admin | hierarchy | Spouse gets nudge. If Spouse marks Done, Admin sees it as resolved. No secondary nudge. |
| Nani's medicine: both proxies act simultaneously | Spouse | Admin | hierarchy | Spouse action wins. Admin's action is rejected silently. System logs both. |
| Contested expense for Nani | Spouse | Admin | notify_block | Both actions paused. Both proxies + Admin receive alert to resolve manually. |
| Tommy (dog) vet appointment | Admin | (none) | hierarchy | Admin is sole proxy. No escalation path needed. |

### 3.5 consent_handles

Stores references to DPI consent grants. This table NEVER stores raw credentials, Aadhaar numbers, or financial account details. It stores only the external consent ID (an opaque handle issued by the AA/ABHA/DigiLocker framework) and metadata about the consent's scope and validity.
```sql
CREATE TABLE consent_handles (
  consent_id          UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID          NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  family_id           UUID          NOT NULL REFERENCES families(family_id) ON DELETE CASCADE,

  -- Which DPI issued this consent handle
  provider            VARCHAR(20)   NOT NULL CHECK (provider IN ('AA','ABHA','DigiLocker','ONDC')),

  -- The opaque handle issued by the DPI framework. Never a password or account number.
  -- For AA: the consentHandle UUID from Sahamati network
  -- For ABHA: the HIU consent request ID
  -- For DigiLocker: the OAuth access_token reference ID
  -- For ONDC: the order-scoped address-share reference (purpose ONDC_ADDRESS_SHARE, Consent Manager §3.2)  [v1.3]
  external_consent_id VARCHAR(255)  NOT NULL,

  -- Lifecycle status
  status              VARCHAR(20)   NOT NULL DEFAULT 'active'
                      CHECK (status IN ('active','expired','revoked','pending')),
  -- 'pending' = consent request sent to user, not yet granted
  -- 'active'  = consent granted and valid
  -- 'expired' = past expires_at, must renew before next use
  -- 'revoked' = user explicitly withdrew consent

  granted_at          TIMESTAMPTZ,  -- NULL while status = 'pending'
  expires_at          TIMESTAMPTZ   NOT NULL,
  revoked_at          TIMESTAMPTZ,  -- Set when status = 'revoked'

  -- What data this consent covers (provider-specific structure)
  -- AA example:  {"fi_types": ["DEPOSIT", "MUTUAL_FUNDS"], "fip_ids": ["HDFC","ICICI"]}
  -- ABHA example:{"hi_types": ["Prescription", "DiagnosticReport"], "hips": ["Apollo"]}
  data_scope          JSONB         NOT NULL DEFAULT '{}',

  -- Rate limit tracking (avoid hitting DPI refresh limits)
  last_fetched_at       TIMESTAMPTZ,  -- When data was last actually fetched using this consent
  fetch_count_today     INTEGER       NOT NULL DEFAULT 0,  -- Persistence/advisory counter, reset daily (§7.3).
                                                          -- NOT an enforcement point: the Redis hourly bucket is (Runbook §2–3).
                                                          -- Read by renewal inheritance (CM §7.3) and audit tooling.  [v1.3 clarification]

  -- External revocation flag: set to TRUE when a DPI webhook notifies us of a status change
  -- (e.g., user revokes consent directly on the AA portal, not through FamilyLifeOS).
  -- The next CONSENT_REVERIFY check will force a live re-validation regardless of TTL.
  -- Reset to FALSE after successful re-validation.
  revalidation_required BOOLEAN       NOT NULL DEFAULT FALSE,

  created_at            TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

  -- Prevent duplicate external handles across providers
  UNIQUE(external_consent_id, provider),

  -- Sanity checks: catch programmer errors at write time
  -- revoked consents must have a revocation timestamp
  CONSTRAINT chk_revoked_at CHECK (
    status != 'revoked' OR revoked_at IS NOT NULL
  ),
  -- expiry must be after grant (catches invalid API responses or mis-ordered timestamps)
  CONSTRAINT chk_expiry_after_grant CHECK (
    granted_at IS NULL OR expires_at > granted_at
  )
);

-- CRITICAL: Only one ACTIVE consent per user per provider.
-- A standard UNIQUE(user_id, provider, status) fails because it also prevents
-- having both an 'expired' and an 'active' row for the same user+provider.
-- Partial unique index is the correct solution.
CREATE UNIQUE INDEX idx_consent_one_active
  ON consent_handles(user_id, provider)
  WHERE status = 'active';

-- Primary lookup: user's active consent for a given provider (CONSENT_REVERIFY state)
CREATE INDEX idx_consent_user_provider ON consent_handles(user_id, provider, status)
  WHERE status = 'active';

-- Expiry watchdog: find consents expiring within 7 days
CREATE INDEX idx_consent_expiry ON consent_handles(expires_at)
  WHERE status = 'active';

-- Rate limit check: find consents fetched recently
CREATE INDEX idx_consent_last_fetched ON consent_handles(user_id, provider, last_fetched_at)
  WHERE status = 'active';

-- Revalidation sweep: find consents flagged by external DPI webhooks
CREATE INDEX idx_consent_revalidation ON consent_handles(user_id, provider)
  WHERE revalidation_required = TRUE AND status = 'active';
```

### 3.6 audit_log

Tamper-proof, append-only log of all write operations. Each entry carries a SHA-256 hash over (log_id, user_id, action, canonical details, previous_hash), forming a hash chain per family. A NULL previous_hash (first row of a family) serialises as the empty string (v1.3 clarification). Any modification to a historical entry invalidates all subsequent hashes, making tampering detectable.
```sql
CREATE TABLE audit_log (
  log_id          UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
  family_id       UUID          NOT NULL REFERENCES families(family_id),
  user_id         UUID          NOT NULL REFERENCES users(user_id),

  -- Action category (standardized enum — see Section 5 for full taxonomy)
  -- Examples: BILL_PAYMENT, ROLE_CHANGE, CONSENT_GRANT, MEMBER_ADDED,
  --           MEMBER_REMOVED, MODULE_ACTIVATED, SOS_TRIGGERED, PROXY_ACTION
  action          VARCHAR(100)  NOT NULL,

  -- Structured payload. NO PII (no phone numbers, Aadhaar, UPI IDs).
  -- Use UUIDs and amounts only. Example:
  -- {"transaction_id": "uuid", "biller_id": "BESCOM", "amount_paise": 50000,
  --  "idempotency_key": "uuid", "automation_tier": 1}
  details         JSONB         NOT NULL,

  -- FSM state at time of action (for observability and telemetry dashboards).
  -- SYNC REQUIREMENT: This enum must stay aligned with NFR v2.1 §4 Telemetry spec,
  -- which defines FSM_Exit_State as one of: SUCCESS | FAILED | ABORTED.
  -- AWAITING_APPROVAL is included here for completeness (actions that were approved
  -- but not yet executed can be logged), but SUCCESS/FAILED/ABORTED are the three
  -- values that feed Prometheus/Grafana dashboards and the Autonomy Score metric.
  -- Any new FSM exit state added to Tech_Spec_Supervisor_State_Machine must be
  -- added here simultaneously. These two docs must never diverge.
  fsm_exit_state  VARCHAR(30)   CHECK (fsm_exit_state IN
                    ('SUCCESS','FAILED','ABORTED','AWAITING_APPROVAL')),

  -- Hash chain for tamper detection
  -- previous_hash: current_hash of the immediately preceding audit_log row
  --                for the same family_id (NULL for the first entry)
  previous_hash   VARCHAR(64),
  -- current_hash = SHA256(log_id || user_id || action || canonical_details || previous_hash)
  -- where canonical_details = json.dumps(details, sort_keys=True, separators=(',', ':'))
  -- CRITICAL: Use canonical JSON serialisation (sorted keys, no spaces).
  -- Python dict str() output is NON-DETERMINISTIC across versions and will produce
  -- false-positive tamper alerts. Always use json.dumps with sort_keys=True.
  -- Computed in APPLICATION CODE before INSERT, not via DB trigger.
  -- Reason: DB-computed hashes are harder to verify externally and create lock-in.
  current_hash    VARCHAR(64)   NOT NULL,

  -- IMMUTABILITY: This table must NEVER have UPDATE or DELETE permissions granted.
  -- Grant only INSERT + SELECT to the application database user.
  timestamp       TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- CRITICAL: Revoke UPDATE and DELETE from app DB user
-- REVOKE UPDATE, DELETE ON audit_log FROM familylifeos_app;
-- Module DB roles have NO privileges on this table at all; they append through
-- fn_lock_audit_tail / fn_append_audit (§3.18). Kernel code uses the same two functions.

-- Query audit trail for a family (paginated, most recent first)
CREATE INDEX idx_audit_family_ts ON audit_log(family_id, timestamp DESC);

-- Query actions by a specific user
CREATE INDEX idx_audit_user ON audit_log(user_id, timestamp DESC);

-- Verify hash chain integrity (daily verification job)
-- Query: SELECT * FROM audit_log WHERE family_id=$1 ORDER BY timestamp ASC
```

> ⚠  IMPORTANT: The database CHECK constraint for hash verification from Master Context v2.0 has been intentionally removed.
> Reason: digest() inside a CHECK constraint is evaluated on every INSERT and every SELECT that checks constraints.
> This creates performance degradation and makes the hash algorithm tightly coupled to the DB engine.
> Instead: Compute current_hash in the application service BEFORE the INSERT call.
> Run a separate nightly integrity verification job (see Section 7.2) that re-verifies the chain.

### 3.7 supervisor_sessions

PostgreSQL journal for FSM state persistence. Redis holds the hot state (fast reads during active sessions). This table is the durable recovery source when Redis is unavailable or the server restarts mid-conversation. On boot, the Supervisor reconciles any AWAITING_APPROVAL or REASONING sessions from this table. Column naming: the state column is `fsm_state`; Financial Transaction Safety v1.2 and Consent Manager v1.2 use this name (their v1.1 texts said `session_status`).
```sql
CREATE TABLE supervisor_sessions (
  session_id        UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
  family_id         UUID          NOT NULL REFERENCES families(family_id) ON DELETE CASCADE,
  user_id           UUID          NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,

  -- Current FSM state (mirrors the Redis hot state)
  fsm_state         VARCHAR(30)   NOT NULL
                    CHECK (fsm_state IN (
                      'IDLE','INTENT_ANALYSIS','AWAITING_CLARIFICATION',
                      'REASONING','AWAITING_APPROVAL','CONSENT_REVERIFY',
                      'EXECUTION','SUCCESS_CONFIRMATION','FAILED','ABORTED','SOS'
                    )),

  -- The full intent that triggered this session
  -- {"raw_input": "Pay electricity bill", "parsed_intent": "PAY_BILL",
  --  "entities": {"biller": "BESCOM", "amount_paise": null},
  --  "automation_tier": 1, "confidence": 0.92}
  intent_payload    JSONB         NOT NULL DEFAULT '{}',

  -- Idempotency key for the action being prepared (if any)
  -- Generated at INTENT_ANALYSIS, used to prevent double-execution on retry
  idempotency_key   UUID,

  -- v1.3: the resource lock moved to its own table, resource_lock (§3.11), keyed by session_id.
  -- The former resource_lock column is gone. Rationale: FTS §9.3 needs locks that can outlive a
  -- session's state transitions and be released independently of them.

  -- Intent type, mirrors intent_payload.parsed_intent for indexed lookups (FTS §5.3)  [v1.3]
  intent_type       VARCHAR(50),

  -- External reference returned by BBPS once a payment is acknowledged (FTS §6.4). NULL until then.  [v1.3]
  bbps_transaction_ref_id VARCHAR(100),

  -- Number of Healer polls performed on this session while it was a zombie (FTS §6.4, §7.3)  [v1.3]
  healer_poll_count INTEGER       NOT NULL DEFAULT 0,

  -- Operational note set by the Healer or an Admin override (FTS §6.4, §11.3). Never PII.  [v1.3]
  session_notes     TEXT,

  -- Sessions expire based on FSM state. The application MUST set this explicitly on INSERT.
  -- Do NOT rely on the DEFAULT. State-appropriate values:
  --   AWAITING_APPROVAL      → NOW() + INTERVAL '5 minutes'  (biometric prompt window)
  --   AWAITING_CLARIFICATION → NOW() + INTERVAL '30 minutes' (user may step away)
  --   REASONING / EXECUTION  → NOW() + INTERVAL '2 minutes'  (should complete fast)
  --   All others             → NOW() + INTERVAL '5 minutes'  (safe default)
  -- Leaving AWAITING_APPROVAL open for 30 minutes is a security hole:
  -- an attacker with brief physical access could approve a queued payment.
  expires_at        TIMESTAMPTZ   NOT NULL,  -- NO DEFAULT: app must set state-appropriate value

  created_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- Find active sessions for a user (check before creating new session)
CREATE INDEX idx_session_user_active ON supervisor_sessions(user_id, fsm_state)
  WHERE fsm_state NOT IN ('IDLE','SUCCESS_CONFIRMATION','FAILED','ABORTED');

-- Recovery on boot: find all sessions that were interrupted mid-flow
CREATE INDEX idx_session_recovery ON supervisor_sessions(fsm_state, expires_at)
  WHERE fsm_state IN ('AWAITING_APPROVAL','CONSENT_REVERIFY','EXECUTION');

-- Collision detection for duplicate payment intents (FTS §5.3)  [v1.3]
CREATE INDEX idx_session_intent_lookup ON supervisor_sessions(family_id, intent_type, created_at DESC)
  WHERE fsm_state NOT IN ('FAILED','ABORTED','SUCCESS_CONFIRMATION');

-- v1.3: idx_session_resource_lock and idx_session_resource_lock_unique were removed with the
-- column. Uniqueness of a live lock is enforced by idx_resource_lock_live on resource_lock (§3.11).
```

### 3.8 device_registry

Tracks registered devices for surface context and push notifications. The is_public_surface flag implements the PRD Scenario 9 requirement: a Kitchen Tablet marked as public will never display financial or health data, regardless of who is logged in or what voice ID is detected.
```sql
CREATE TABLE device_registry (
  device_id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  family_id           UUID         NOT NULL REFERENCES families(family_id) ON DELETE CASCADE,
  -- owner: the user who registered this device (typically Admin)
  owner_user_id       UUID         NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,

  -- Human-readable name set by Admin: 'Kitchen Tablet', 'Dad's Phone', 'Living Room TV'
  device_name         VARCHAR(100) NOT NULL,

  device_type         VARCHAR(20)  NOT NULL
                      CHECK (device_type IN ('mobile','tablet','smart_display','web','desktop')),

  -- PUBLIC SURFACE: if TRUE, this device will NEVER display:
  --   - Bank balances or transaction history
  --   - Health records or medications
  --   - Vault documents
  --   - Any PII for family members
  -- Set to TRUE for shared family displays (kitchen tablet, living room TV).
  is_public_surface   BOOLEAN      NOT NULL DEFAULT FALSE,

  -- FCM/APNs push notification token. Rotated by client on each app launch.
  -- NULL for smart displays / web that don't support push.
  push_token          VARCHAR(500),
  push_token_updated_at TIMESTAMPTZ,

  last_active_at      TIMESTAMPTZ,
  created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_device_family ON device_registry(family_id);
CREATE INDEX idx_device_owner ON device_registry(owner_user_id);
```

### 3.9 offline_task_queue

Holds tasks that could not be executed due to DPI downtime, network failures, or rate limit exhaustion. The Healer (background reconciliation cron job) processes this queue every 5 minutes. This table is intentionally simple — complex retry orchestration belongs in the Financial Transaction Safety spec.
```sql
CREATE TABLE offline_task_queue (
  task_id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  family_id        UUID         NOT NULL REFERENCES families(family_id) ON DELETE CASCADE,
  user_id          UUID         NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,

  -- Task category determines retry strategy and urgency
  task_type        VARCHAR(50)  NOT NULL
                   CHECK (task_type IN (
                     'BILL_PAYMENT',      -- BBPS transaction failed
                     'CONSENT_REFRESH',   -- AA/ABHA data fetch failed
                     'HEALTH_FETCH',      -- ABHA record fetch failed
                     'ONDC_ORDER',        -- ONDC commerce order failed
                     'NOTIFICATION',      -- Push/WhatsApp notification failed
                     'AUDIT_LOG_WRITE'    -- Audit log write failed (CRITICAL)
                   )),

  -- Full serialized payload to re-execute the task
  -- Includes idempotency_key so re-execution is safe
  payload          JSONB        NOT NULL,

  -- Queue lifecycle
  status           VARCHAR(20)  NOT NULL DEFAULT 'pending'
                   CHECK (status IN ('pending','processing','succeeded','failed_permanent','cancelled')),
  -- 'cancelled' [v1.3]: set by revocation propagation when a pending task's consent was revoked
  -- (Consent Manager §8.2 Step 4). Cancelled tasks are never retried.

  retry_count      INTEGER      NOT NULL DEFAULT 0,
  max_retries      INTEGER      NOT NULL DEFAULT 5,
  next_retry_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

  -- Failure reason for the last attempt
  last_error       TEXT,

  -- Expiry: tasks not resolved within 48h are marked failed_permanent
  -- Admin is notified to take manual action
  expires_at       TIMESTAMPTZ  NOT NULL DEFAULT (NOW() + INTERVAL '48 hours'),

  created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Healer cron job: find tasks due for retry
CREATE INDEX idx_queue_retry ON offline_task_queue(next_retry_at, status)
  WHERE status = 'pending';

-- Admin dashboard: show pending tasks for a family
CREATE INDEX idx_queue_family ON offline_task_queue(family_id, status)
  WHERE status IN ('pending','failed_permanent');
```

> ⚠  AUDIT_LOG_WRITE tasks are CRITICAL PRIORITY. If an audit log write fails (e.g., DB write error
> after a successful BBPS payment), the system enters FAILED state. The transaction is marked
> 'Executed but Unconfirmed' in the supervisor_sessions table. The Healer resolves this first,
> before all other queue items. Full protocol in Tech_Spec_Financial_Transaction_Safety.md.

### 3.10 updated_at Auto-Maintenance Trigger

All mutable tables have an updated_at column. Rather than requiring every UPDATE query to set it manually (error-prone), we use a single reusable trigger function.
```sql
-- Reusable trigger function (create once, attach to all mutable tables)
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Attach to each mutable table
CREATE TRIGGER trg_families_updated_at
  BEFORE UPDATE ON families
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_users_updated_at
  BEFORE UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_consent_handles_updated_at
  BEFORE UPDATE ON consent_handles
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_supervisor_sessions_updated_at
  BEFORE UPDATE ON supervisor_sessions
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_device_registry_updated_at
  BEFORE UPDATE ON device_registry
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_offline_task_queue_updated_at
  BEFORE UPDATE ON offline_task_queue
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- v1.3 additions
CREATE TRIGGER trg_consent_records_updated_at
  BEFORE UPDATE ON consent_records
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_module_registry_updated_at
  BEFORE UPDATE ON module_registry
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_intent_routes_updated_at
  BEFORE UPDATE ON intent_routes
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_family_module_activations_updated_at
  BEFORE UPDATE ON family_module_activations
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- NOTE: audit_log, family_relationships, resource_lock, consent_ui_disclosures and
-- role_module_permissions have NO updated_at.
-- audit_log and consent_ui_disclosures are append-only (no UPDATEs permitted)
-- family_relationships uses is_active; resource_lock uses released_at
```

### 3.11 resource_lock (v1.3)

Replaces the former `supervisor_sessions.resource_lock` column. A lock is a row; a **live** lock is a row with `released_at IS NULL`. The partial unique index is the entire concurrency guarantee: two workers racing to pay the same biller both INSERT, and exactly one succeeds. Protocol: Financial Transaction Safety §9.2–9.3 (acquire at gate G2, release only after the Phase 2 COMMIT, stale after 30 minutes).
```sql
CREATE TABLE resource_lock (
  lock_id        UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  family_id      UUID         NOT NULL REFERENCES families(family_id) ON DELETE CASCADE,
  -- Resource key format (FTS §9.2): 'BBPS_' || biller_id for bill payments.
  -- Other resource classes use a class prefix + identifier: 'MEMBER_' || user_id, 'CONSENT_' || consent_id.
  resource_key   VARCHAR(200) NOT NULL,
  session_id     UUID         NOT NULL REFERENCES supervisor_sessions(session_id) ON DELETE CASCADE,
  acquired_by    UUID         NOT NULL REFERENCES users(user_id),
  acquired_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  -- NULL while held. Set on release: Phase 2 COMMIT, FAILED/ABORTED transition,
  -- Healer stale-lock release (FTS §9.3), Admin override (FTS §11.3), session-expiry cleanup (§7.4).
  released_at    TIMESTAMPTZ,
  release_reason VARCHAR(40)
                 CHECK (release_reason IN ('completed','failed','aborted','healer_stale','admin_override','session_expired')),
  CONSTRAINT chk_release_reason CHECK ((released_at IS NULL) = (release_reason IS NULL))
);

-- THE guarantee: at most one live lock per resource per family. The losing INSERT raises a
-- unique violation, which the application maps to FIN_009 'A payment is already in progress.'
CREATE UNIQUE INDEX idx_resource_lock_live ON resource_lock(family_id, resource_key)
  WHERE released_at IS NULL;

-- Healer stale-lock sweep (FTS §9.3): live locks older than 30 minutes
CREATE INDEX idx_resource_lock_stale ON resource_lock(acquired_at) WHERE released_at IS NULL;

-- Release by session (Phase 2 COMMIT path, cleanup job)
CREATE INDEX idx_resource_lock_session ON resource_lock(session_id) WHERE released_at IS NULL;
```

> ⚠  Locks are released by UPDATE (released_at, release_reason), never by DELETE, so that the stale-lock
> sweep and forensic review can see the history. Where FTS v1.1 code blocks say `DELETE FROM resource_lock`,
> read the release UPDATE in Q7. Released rows are purged after 7 days (§7.4 Step 3).

### 3.12 consent_records (v1.3, from Consent Manager v1.1 §4.1)

The first-party consent record (Consent Manager layer 1). Every DPI consent handle has one; first-party purposes (voice processing, device registration) have a record without a handle. Behavioural rules, the purpose registry and the grant/withdraw flows stay in the Consent Manager; this document owns the DDL. One difference from the CM text: the expiry index is named `idx_consent_records_expiry` because `idx_consent_expiry` already exists on consent_handles (§3.5) and index names are unique per schema.
```sql
CREATE TABLE consent_records (
  record_id                UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id                  UUID         NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  family_id                UUID         NOT NULL REFERENCES families(family_id) ON DELETE CASCADE,

  -- Must be a valid code from the purpose registry (Consent Manager §3.2); enforced at application layer
  purpose_code             VARCHAR(50)  NOT NULL,

  -- 'pending' = request sent, not yet confirmed | 'active' | 'expired' = past expires_at
  -- 'revoked' = DPI/external system revoked (webhook) | 'withdrawn' = user withdrew in FamilyLifeOS
  status                   VARCHAR(20)  NOT NULL DEFAULT 'active'
                           CHECK (status IN ('pending','active','expired','revoked','withdrawn')),

  granted_at               TIMESTAMPTZ,              -- NULL while pending
  expires_at               TIMESTAMPTZ  NOT NULL,
  revoked_at               TIMESTAMPTZ,              -- populated for revoked / withdrawn

  -- Jurisdiction and lawful basis ('IN' / DPDP Act 2023 is the only v1 value; Consent Manager §3.3, §10)
  jurisdiction             VARCHAR(10)  NOT NULL DEFAULT 'IN',
  lawful_basis             VARCHAR(40)  NOT NULL DEFAULT 'explicit_consent',

  -- Required for minor users before status = 'active' (Consent Manager §2.5)
  parental_consent_user_id UUID         REFERENCES users(user_id),

  -- Required when user_id is a managed profile: the assigned proxy who granted (Consent Manager v1.3 §2.6)
  proxy_consent_user_id    UUID         REFERENCES users(user_id),

  -- Link to the external DPI handle; NULL for first-party-only purposes
  consent_handle_id        UUID         REFERENCES consent_handles(consent_id),

  -- Purpose-specific scope, e.g. {"fi_types":["DEPOSIT"],"fip_ids":["HDFC"]}
  granted_scope            JSONB        NOT NULL DEFAULT '{}',

  -- Which disclosure the user saw (consent_ui_disclosures.version for this purpose_code)
  consent_ui_version       VARCHAR(20)  NOT NULL,

  created_at               TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  updated_at               TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

  CONSTRAINT chk_granted_before_expiry CHECK (granted_at IS NULL OR expires_at > granted_at),
  CONSTRAINT chk_revoked_has_timestamp CHECK (status NOT IN ('revoked','withdrawn') OR revoked_at IS NOT NULL),
  CONSTRAINT chk_pending_no_grant_time CHECK (status != 'pending' OR granted_at IS NULL)
);

-- Only one ACTIVE consent per user per purpose
CREATE UNIQUE INDEX idx_one_active_consent_per_purpose
  ON consent_records (user_id, purpose_code) WHERE status = 'active';

-- Expiry watchdog (Consent Manager §7.2)
CREATE INDEX idx_consent_records_expiry ON consent_records (expires_at, status) WHERE status = 'active';

-- Parental consent lookup
CREATE INDEX idx_consent_parental ON consent_records (parental_consent_user_id)
  WHERE parental_consent_user_id IS NOT NULL;

-- Proxy consent lookup (Consent Manager v1.3 §2.6)
CREATE INDEX idx_consent_proxy ON consent_records (proxy_consent_user_id)
  WHERE proxy_consent_user_id IS NOT NULL;

-- Consent Manager v1.1 Fix 1: a DPI purpose must never be recorded without its external handle.
-- Without this, a crash between the consent_handles INSERT and the consent_records INSERT leaves
-- consent_handle_id NULL and CONSENT_REVERIFY Check 2 is silently skipped.
CREATE OR REPLACE FUNCTION enforce_dpi_handle() RETURNS trigger AS $$
DECLARE
  -- MUST stay in sync with purpose_registry entries whose dpi_required is set (Consent Manager §3.2).
  -- Adding a DPI purpose_code = registry entry + this array + one Alembic migration, as one change.
  dpi_purposes TEXT[] := ARRAY[
    'AA_BALANCE_FETCH', 'AA_TRANSACTION_HISTORY',
    'ABHA_PRESCRIPTION', 'ABHA_DIAGNOSTICS', 'ABHA_VITALS',
    'DIGILOCKER_DOCUMENT', 'ONDC_ADDRESS_SHARE'
  ];
BEGIN
  IF NEW.purpose_code = ANY(dpi_purposes) AND NEW.consent_handle_id IS NULL THEN
    RAISE EXCEPTION 'DPI consent purpose % requires consent_handle_id. Write the consent_handles row first.', NEW.purpose_code;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_enforce_dpi_handle
  BEFORE INSERT OR UPDATE ON consent_records
  FOR EACH ROW EXECUTE FUNCTION enforce_dpi_handle();
```

### 3.13 consent_ui_disclosures (v1.3, from Consent Manager v1.1 §4.6)

Append-only canonical record of what each consent screen said. `consent_records.consent_ui_version` points at `(purpose_code, version)` here. A row with `is_material_change = TRUE` makes the watchdog queue re-consent for everyone who consented under an older version (Consent Manager §4.6).
```sql
CREATE TABLE consent_ui_disclosures (
  disclosure_id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  purpose_code           VARCHAR(50) NOT NULL,          -- valid purpose registry code
  -- Semantic version. MAJOR: new data types or DPI scope; MINOR: retention/jurisdiction change; PATCH: wording
  version                VARCHAR(20) NOT NULL,
  disclosure_text        TEXT        NOT NULL,          -- exact English text shown; translations rendered at runtime
  data_types_summary     TEXT[]      NOT NULL,          -- e.g. {'Account balance (amount only)','No transaction history'}
  is_material_change     BOOLEAN     NOT NULL,          -- TRUE = existing consents for this purpose must be re-obtained
  material_change_reason TEXT,                          -- required when is_material_change = TRUE
  changed_by             VARCHAR(100) NOT NULL,
  change_rationale       TEXT        NOT NULL,
  effective_from         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT chk_material_reason CHECK (is_material_change = FALSE OR material_change_reason IS NOT NULL),
  UNIQUE (purpose_code, version)
);
-- Append-only: the app DB user gets INSERT + SELECT only.
-- REVOKE UPDATE, DELETE ON consent_ui_disclosures FROM familylifeos_app;
```

### 3.14 module_registry and intent_routes (v1.3, from Module Registry §5.1)

System-wide registration, rebuilt at every boot from the on-disk manifests (Module Registry §8.1). `intent_routes` is materialised so that a duplicate intent_code is a primary-key violation, not a code-review hope.
```sql
CREATE TABLE module_registry (
  module_id       VARCHAR(40) PRIMARY KEY,               -- matches manifest.module_id (^[a-z][a-z0-9_]{2,40}$)
  version         VARCHAR(20) NOT NULL,                  -- semver from the manifest
  tier            VARCHAR(10) NOT NULL CHECK (tier IN ('core','service')),
  manifest        JSONB       NOT NULL,                  -- the full validated manifest
  manifest_sha256 CHAR(64)    NOT NULL,                  -- hash of canonical manifest bytes; drift without a version bump is MODULE_MANIFEST_DRIFT
  status          VARCHAR(20) NOT NULL DEFAULT 'registered' CHECK (status IN ('registered','disabled')),
  registered_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE intent_routes (
  intent_code  VARCHAR(40) PRIMARY KEY,                  -- global uniqueness IS the constraint
  module_id    VARCHAR(40) NOT NULL REFERENCES module_registry(module_id),
  mutating     BOOLEAN     NOT NULL,
  tier_ceiling SMALLINT    NOT NULL CHECK (tier_ceiling BETWEEN 0 AND 2),   -- Level 3 is structurally impossible
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 3.15 family_module_activations (v1.3, from Module Registry §5.2)

Per-family activation by an Admin (Level 0; audit codes MODULE_ACTIVATED / MODULE_DEACTIVATED). Modules whose manifest says `deactivatable: false` (secure_vault) are implicitly active for every family and need no row. Deactivation stops dispatch, not data.
```sql
CREATE TABLE family_module_activations (
  activation_id  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  family_id      UUID        NOT NULL REFERENCES families(family_id) ON DELETE CASCADE,
  module_id      VARCHAR(40) NOT NULL REFERENCES module_registry(module_id),
  status         VARCHAR(10) NOT NULL DEFAULT 'active' CHECK (status IN ('active','inactive')),
  activated_by   UUID        NOT NULL REFERENCES users(user_id),   -- must hold role 'admin' (app-layer check)
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (family_id, module_id)
);

CREATE INDEX idx_activation_family ON family_module_activations(family_id, status);
```

### 3.16 role_module_permissions (v1.3)

The role → module access matrix that Q2 used to keep in application code, now data. Seeded in V001; changed only by migration. `module_id` is deliberately not a foreign key so permissions can be seeded before a module registers. Module ids for modules that do not exist yet (logistics, homeops, comms, eldercare, news) are placeholders that must match their manifests when those modules are written.
```sql
CREATE TABLE role_module_permissions (
  role       VARCHAR(20) NOT NULL CHECK (role IN ('admin','member','minor','elder','staff','managed','passive')),
  module_id  VARCHAR(40) NOT NULL,
  can_access BOOLEAN     NOT NULL DEFAULT TRUE,
  PRIMARY KEY (role, module_id)
);

-- Seed (V001). managed and passive have no rows: no login.
INSERT INTO role_module_permissions (role, module_id) VALUES
  ('admin','secure_vault'),('admin','finance'),('admin','health'),('admin','logistics'),
  ('admin','homeops'),('admin','comms'),('admin','eldercare'),('admin','news'),
  ('member','secure_vault'),('member','finance'),('member','health'),('member','logistics'),
  ('member','homeops'),('member','comms'),('member','eldercare'),('member','news'),
  ('elder','health'),('elder','comms'),('elder','eldercare'),('elder','news'),
  ('minor','logistics'),('minor','comms'),('minor','news'),
  ('staff','homeops');
```

> ℹ  Two checks, both deny-by-default (Module Registry §7.3 step 4): the intent's `allowed_roles` in the manifest AND this matrix.
> The matrix answers "may this role use this module at all"; the manifest answers "may this role trigger this intent".

### 3.17 Kernel views readable by modules (v1.3, Module Registry §7.2 whitelist)

Each Core Module's database role gets SELECT on these five views and nothing else in `core`. They expose references, never token material, phone numbers, emails or push tokens.
```sql
-- What a module may know about the family graph. No phone, email, or shadow expiry.
CREATE VIEW v_family_members AS
SELECT u.family_id, u.user_id, u.display_name, u.role, u.verification_status,
       u.preferred_language, u.shadow_node
FROM users u
WHERE u.deleted_at IS NULL;

-- role → module access, combined with per-family activation. Non-deactivatable modules count as active.
CREATE VIEW v_module_permissions AS
SELECT f.family_id, rmp.role, rmp.module_id,
       (rmp.can_access AND (
          COALESCE((mr.manifest->>'deactivatable')::boolean, TRUE) = FALSE
          OR EXISTS (SELECT 1 FROM family_module_activations fma
                     WHERE fma.family_id = f.family_id
                       AND fma.module_id = rmp.module_id
                       AND fma.status = 'active')
       )) AS can_access
FROM families f
CROSS JOIN role_module_permissions rmp
LEFT JOIN module_registry mr ON mr.module_id = rmp.module_id
WHERE f.deleted_at IS NULL;

-- Consent references only. external_consent_id and data_scope are never exposed to modules;
-- the DPI Gateway resolves handles at call time (Module Registry §6.1 rule 3).
CREATE VIEW v_active_consents AS
SELECT cr.family_id, cr.user_id, cr.record_id, cr.purpose_code, cr.consent_handle_id,
       ch.provider, cr.status, cr.expires_at, ch.revalidation_required
FROM consent_records cr
LEFT JOIN consent_handles ch ON ch.consent_id = cr.consent_handle_id
WHERE cr.status = 'active';

-- Public/private surface per device (PRD Scenario 9). No push tokens.
CREATE VIEW v_device_surfaces AS
SELECT d.family_id, d.device_id, d.owner_user_id, d.device_type, d.is_public_surface
FROM device_registry d;

-- Who is responsible for a dependent (v1.3 change 16). One row per (dependent, guardian, basis).
-- Modules use it to decide who may see or be told about a dependent's data; they never read
-- family_relationships or proxy_assignments directly.
CREATE VIEW v_guardians AS
SELECT fr.family_id, fr.to_user_id AS dependent_user_id, fr.from_user_id AS guardian_user_id,
       CASE fr.relationship_type WHEN 'parent' THEN 'parent' ELSE 'legal_guardian' END AS basis,
       NULL::VARCHAR(10) AS proxy_rank, NULL::VARCHAR(20) AS conflict_resolution_rule, NULL::INTEGER AS notify_timeout_mins
FROM family_relationships fr
JOIN users dep ON dep.user_id = fr.to_user_id   AND dep.deleted_at IS NULL AND dep.role = 'minor'
JOIN users g   ON g.user_id   = fr.from_user_id AND g.deleted_at   IS NULL AND g.role IN ('admin','member')
WHERE fr.relationship_type IN ('parent','guardian') AND fr.is_active
UNION ALL
SELECT pa.family_id, pa.managed_user_id, pa.proxy_user_id,
       'proxy' AS basis, pa.proxy_rank, pa.conflict_resolution_rule, pa.notify_timeout_mins
FROM proxy_assignments pa
JOIN users g ON g.user_id = pa.proxy_user_id AND g.deleted_at IS NULL;

-- Per module, at registration (Module Registry §7.2):
-- GRANT SELECT ON v_family_members, v_module_permissions, v_active_consents, v_device_surfaces, v_guardians TO role_module_<id>;
```

### 3.18 Audit write protocol (v1.3)

Two SECURITY DEFINER functions let any writer (kernel or module) append to `audit_log` without table privileges while keeping two earlier decisions intact: the hash is computed in application code with the canonical JSON of §3.6 (so auditors can verify it without database access), and concurrent writers are serialised per family with a row lock (FTS §11.3). Both calls happen inside one transaction together with the business write they describe (two-phase commit, FTS §4.3).
```sql
-- Step 1 — lock the family's chain head and return its hash (NULL when the family has no rows yet).
-- The row lock is held until COMMIT, so no other writer can append for this family meanwhile.
CREATE OR REPLACE FUNCTION fn_lock_audit_tail(p_family_id UUID)
RETURNS VARCHAR(64)
LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE v_hash VARCHAR(64);
BEGIN
  SELECT current_hash INTO v_hash
  FROM audit_log
  WHERE family_id = p_family_id
  ORDER BY timestamp DESC, log_id DESC
  LIMIT 1
  FOR UPDATE;
  RETURN v_hash;
END $$;

-- Step 2 — append with the hash computed in application code. The function re-reads the chain head
-- and refuses if the caller's previous_hash is stale, so misuse fails loudly instead of corrupting the chain.
CREATE OR REPLACE FUNCTION fn_append_audit(
  p_log_id         UUID,
  p_family_id      UUID,
  p_user_id        UUID,
  p_action         VARCHAR(100),
  p_details        JSONB,
  p_fsm_exit_state VARCHAR(30),
  p_previous_hash  VARCHAR(64),
  p_current_hash   VARCHAR(64)
) RETURNS UUID
LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE v_head VARCHAR(64);
BEGIN
  SELECT current_hash INTO v_head
  FROM audit_log WHERE family_id = p_family_id
  ORDER BY timestamp DESC, log_id DESC LIMIT 1;
  IF v_head IS DISTINCT FROM p_previous_hash THEN
    RAISE EXCEPTION 'AUDIT_CHAIN_HEAD_MISMATCH: head=% given=%', v_head, p_previous_hash;
  END IF;
  INSERT INTO audit_log (log_id, family_id, user_id, action, details, fsm_exit_state,
                         previous_hash, current_hash, timestamp)
  VALUES (p_log_id, p_family_id, p_user_id, p_action, p_details, p_fsm_exit_state,
          p_previous_hash, p_current_hash, NOW());
  RETURN p_log_id;
END $$;

REVOKE ALL ON FUNCTION fn_lock_audit_tail(UUID) FROM PUBLIC;
REVOKE ALL ON FUNCTION fn_append_audit(UUID,UUID,UUID,VARCHAR,JSONB,VARCHAR,VARCHAR,VARCHAR) FROM PUBLIC;
-- GRANT EXECUTE on both to familylifeos_app and to each role_module_<id> at registration.
```

Application side (asyncpg), the only supported way to write an audit row:
```python
async with conn.transaction():
    prev = await conn.fetchval('SELECT fn_lock_audit_tail($1)', family_id)      # NULL -> None
    log_id = uuid.uuid4()
    canonical = json.dumps(details, sort_keys=True, separators=(',', ':'))
    current = hashlib.sha256(
        f'{log_id}{user_id}{action}{canonical}{prev or ""}'.encode('utf-8')     # NULL previous_hash -> ''
    ).hexdigest()
    await conn.fetchval('SELECT fn_append_audit($1,$2,$3,$4,$5,$6,$7,$8)',
                        log_id, family_id, user_id, action, details, fsm_exit_state, prev, current)
    # ... the business write this row describes (e.g. supervisor_sessions update) in the same transaction ...
```

> ⚠  The `details` argument must already be a typed, PII-free payload (UUIDs and amounts only). Typed payload
> models per action code are specified in Tech_Spec_Audit_Log_Implementation.md (P1) and are required before
> any real user data enters the system (tracker parking lot).

## 4. Cardinality Rules & Application-Layer Enforcement

These rules are NOT enforced via database constraints (the complexity of deferred constraints and the need for clear error messages makes app-layer enforcement preferable). Every service method that creates a new user record must call the corresponding validation function before the INSERT.

> ⚠  CONCURRENCY REQUIREMENT: Cardinality checks MUST run inside a transaction with a row-level lock.
> A plain SELECT COUNT(*) followed by INSERT is a race condition: two concurrent Supervisor instances
> can both see COUNT=1, both proceed, and produce 3 admins.
> Correct pattern (Python/asyncpg):
>   async with conn.transaction():
>       await conn.fetchval('SELECT 1 FROM families WHERE family_id=$1 FOR UPDATE', family_id)
>       count = await conn.fetchval('SELECT COUNT(*) FROM users WHERE family_id=$1 AND role=$2 AND deleted_at IS NULL', family_id, role)
>       if count >= max_allowed: raise CardinalityError(...)
>       await conn.execute('INSERT INTO users ...', ...)
> The FOR UPDATE on the families row serialises all concurrent writes for the same family.

| Role | Min | Max | Enforcement Method | Error to Surface to Admin |
|---|---|---|---|---|
| admin | 1 | 2 | SELECT COUNT(*) WHERE family_id=? AND role='admin' AND deleted_at IS NULL | A family can have at most 2 admins. Demote an existing admin first. |
| member | 0 | 2 | SELECT COUNT(*) WHERE family_id=? AND role='member' AND deleted_at IS NULL | A family can have at most 2 members (spouse/adult co-owners). |
| minor | 0 | 10 | SELECT COUNT(*) WHERE family_id=? AND role='minor' AND deleted_at IS NULL | Maximum 10 minors per family. Contact support if you need more. |
| elder | 0 | 4 | SELECT COUNT(*) WHERE family_id=? AND role='elder' AND deleted_at IS NULL | Maximum 4 elders per family (parents + in-laws). |
| staff | 0 | 5 | SELECT COUNT(*) WHERE family_id=? AND role='staff' AND deleted_at IS NULL | Maximum 5 staff members. Offboard an existing staff member first. |
| managed | 0 | 10 | SELECT COUNT(*) WHERE family_id=? AND role='managed' AND deleted_at IS NULL | Maximum 10 managed profiles (pets, infants, non-app seniors). |
| passive | 0 | 10 | SELECT COUNT(*) WHERE family_id=? AND role='passive' AND deleted_at IS NULL | Maximum 10 passive nodes (members who refuse the app). |
| proxy per managed | 1 | 2 | SELECT COUNT(*) WHERE managed_user_id=? | Exactly 1 primary + 0–1 secondary proxy. Add a secondary or remove the existing one. |

### 4.1 Admin Minimum Constraint

The system must always have at least 1 admin per family. This means:
- Deleting the last admin is forbidden. The service must reject this operation with error: 'Cannot remove the only admin. Assign another admin first.'
- Downgrading the last admin's role is also forbidden.
- If an admin uses the 'Right to be Forgotten' (account deletion), a grace period of 24 hours applies. During this window, the system prompts: 'You are the only admin. Please assign another admin before your account is deleted.'

### 4.2 Shadow Node Rules

- Shadow nodes are created with shadow_node = TRUE and shadow_expires_at = NOW() + 7 days.
- Nightly cron job: SELECT * FROM users WHERE shadow_node = TRUE AND shadow_expires_at < NOW() AND deleted_at IS NULL — soft-delete all results.
- When a shadow user accepts the invite: set shadow_node = FALSE, shadow_expires_at = NULL, verification_status = 'otp_verified'.
- Shadow nodes count toward cardinality limits. An admin cannot create a shadow node if the limit is already reached.

### 4.3 Soft Delete Consistency Mandate

This section exists to protect future engineers from a subtle but dangerous class of bug. When a user is soft-deleted (deleted_at IS NOT NULL), their child rows in proxy_assignments, consent_handles, supervisor_sessions, and device_registry are NOT immediately removed — they persist until the 24h hard purge runs. Any query that joins to the users table without filtering deleted_at will silently include deleted users.

> ⚠  MANDATORY RULE: All queries that JOIN or reference the users table MUST include:
>    AND u.deleted_at IS NULL
>    ...unless the query is explicitly intended to retrieve historical data (e.g., audit log reconstruction).
>    This rule applies to all application service code, background jobs, and ad-hoc queries.
>    Failure to apply this filter is a data exposure bug, not just a logic error.

Specific risks if this rule is not followed:
- A soft-deleted Proxy user could still receive medication nudges for a Managed Profile (proxy_assignments rows remain active until hard purge).
- A soft-deleted Staff user could still appear in the family member list, leaking PII.
- A CONSENT_REVERIFY check could succeed on a consent handle belonging to a deleted user, allowing a transaction to proceed on their behalf.

On-delete service responsibilities (in addition to setting deleted_at):
- Immediately deactivate all proxy_assignments where proxy_user_id = deleted user. Do not wait for hard purge.
- Immediately set status = 'revoked' on all consent_handles for the deleted user. Revoke DPI consents via the provider API in the same transaction.
- Immediately abort any supervisor_sessions in AWAITING_APPROVAL or EXECUTION state belonging to the deleted user.
- Revocation of proxy_assignments for managed profiles: if the deleted user was the sole (primary) proxy for a managed profile, alert Admin immediately — the managed profile is now without a caregiver.

> ℹ  The hard purge job (nightly at 01:00 IST) handles the physical removal of rows.
>    Service-layer cleanup above is a safety net against the ~24h window between soft and hard delete.
>    The ON DELETE CASCADE on users → child tables handles hard-delete cleanup automatically.

## 5. Graph Traversal & Operational Queries

These are the 12 most common database operations in FamilyLifeOS. Every query is written as a parameterized PostgreSQL query. Variable names use the $n positional parameter convention. All queries filter on deleted_at IS NULL unless explicitly stated otherwise.

### Q1 — Get All Active Family Members

Used by: Concierge (build context), Admin Dashboard, Notification Engine. Returns all non-deleted, non-passive users for a family, sorted by role priority for display.
```text
SELECT
  u.user_id,
  u.display_name,
  u.role,
  u.verification_status,
  u.shadow_node,
  u.preferred_language
FROM users u
WHERE u.family_id = $1
  AND u.deleted_at IS NULL
  -- $1 must always be a real family_id, never the SYSTEM family UUID.
  -- The SYSTEM_ACTOR user (role='managed', family_id=SYSTEM_FAMILY_UUID) is seeded
  -- in V001 migration and used exclusively for audit_log entries from cron/Healer.
  -- Because this query filters by a specific family_id, the SYSTEM user is naturally
  -- excluded — it lives in its own family partition and can never appear in a real
  -- family's member list. No additional filter is required.
  -- If you ever query users without a family_id filter (e.g. admin tooling),
  -- you MUST add: AND u.family_id != SYSTEM_FAMILY_UUID
ORDER BY
  CASE u.role
    WHEN 'admin'   THEN 1
    WHEN 'member'  THEN 2
    WHEN 'elder'   THEN 3
    WHEN 'minor'   THEN 4
    WHEN 'staff'   THEN 5
    WHEN 'managed' THEN 6
    WHEN 'passive' THEN 7
  END,
  u.display_name;
```

### Q2 — RBAC Permission Check (Can User Access Module?)

Used by: Every API endpoint before serving data. Returns TRUE if the user is permitted to access the specified module. v1.3: the map below is now data in role_module_permissions (§3.16); modules read it through v_module_permissions (§3.17). The application-layer map is kept here as the readable reference and must match the seed.
```sql
-- Step 1: Get user role (fast, uses PK index)
SELECT u.role, u.verification_status, u.family_id
FROM users u
WHERE u.user_id = $1
  AND u.deleted_at IS NULL;

-- Step 2 (application layer): Map role to allowed modules
-- const ROLE_PERMISSIONS = {   // mirrors role_module_permissions seed (§3.16)
--   admin:   ['secure_vault','finance','health','logistics','homeops','comms','eldercare','news'],
--   member:  ['secure_vault','finance','health','logistics','homeops','comms','eldercare','news'],
--   elder:   ['health','comms','eldercare','news'],
--   minor:   ['logistics','comms','news'],
--   staff:   ['homeops'],
--   managed: [],   // no login
--   passive: [],   // no login
-- }
-- if (!ROLE_PERMISSIONS[role].includes(requestedModule)) throw new ForbiddenError();
```

### Q3 — Get Proxies for a Managed Profile

Used by: Notification Engine (who to nudge for Nani's medication?), Proxy Conflict Resolver.
```text
SELECT
  pa.proxy_rank,
  pa.conflict_resolution_rule,
  pa.notify_timeout_mins,
  u.user_id      AS proxy_user_id,
  u.display_name AS proxy_name,
  u.role         AS proxy_role,
  d.push_token,
  d.is_public_surface
FROM proxy_assignments pa
JOIN users u  ON u.user_id = pa.proxy_user_id AND u.deleted_at IS NULL
LEFT JOIN device_registry d ON d.owner_user_id = u.user_id
WHERE pa.managed_user_id = $1   -- e.g., Nani's user_id
ORDER BY
  CASE pa.proxy_rank WHEN 'primary' THEN 1 WHEN 'secondary' THEN 2 END;
```

### Q4 — Get Admin(s) for a Family (Default Notification Target)

Used by: Any event that must always notify the Admin (PRD Scenario 2: even when a Proxy acts, Admin is cc'd).
```text
SELECT
  u.user_id,
  u.display_name,
  u.preferred_language,
  d.push_token
FROM users u
LEFT JOIN device_registry d
  ON d.owner_user_id = u.user_id
  AND d.is_public_surface = FALSE  -- Only notify on private devices
WHERE u.family_id = $1
  AND u.role = 'admin'
  AND u.deleted_at IS NULL
ORDER BY u.created_at ASC;  -- Primary admin was created first
```

### Q5 — Consent Expiry Watchdog (Nightly Cron Job)

Used by: Consent Lifecycle Manager cron job. Finds all consents expiring within the next 7 days and returns them for proactive renewal prompting.
```text
SELECT
  ch.consent_id,
  ch.user_id,
  ch.provider,
  ch.expires_at,
  ch.data_scope,
  u.family_id,
  u.display_name,
  u.preferred_language,
  EXTRACT(DAY FROM (ch.expires_at - NOW())) AS days_until_expiry
FROM consent_handles ch
JOIN users u ON u.user_id = ch.user_id AND u.deleted_at IS NULL
WHERE ch.status = 'active'
  AND ch.expires_at BETWEEN NOW() AND (NOW() + INTERVAL '7 days')
ORDER BY ch.expires_at ASC;
```

### Q6 — CONSENT_REVERIFY (Pre-Execution Check)

Used by: Supervisor FSM, immediately before the EXECUTION state. Must confirm the consent is still active and not rate-limited. This query must complete in <50ms (it is on the critical path of every financial transaction).
```text
SELECT
  ch.consent_id,
  ch.status,
  ch.expires_at,
  ch.fetch_count_today,
  ch.last_fetched_at
FROM consent_handles ch
WHERE ch.user_id = $1
  AND ch.provider = $2    -- 'AA' | 'ABHA' | 'DigiLocker'
  AND ch.status = 'active'
  AND ch.expires_at > NOW()
LIMIT 1;

-- Application layer checks after query:
-- if (!row) → FAILED state: 'Consent not found or expired. Please re-authorize.'
-- Rate limiting is NOT decided here (v1.3): the Redis hourly bucket in Runbook §2–3 is the enforcement
-- point and raises AA_FETCH_LIMIT with a retry_after. fetch_count_today is informational.
```

### Q7 — Resource Lock Check (Concurrent Intent Prevention)

Used by: Supervisor FSM at gate G2 (FTS §2.2, §9.2). v1.3: the lock is a row in resource_lock (§3.11); acquisition is the INSERT itself, so there is no check-then-insert race.
```sql
-- Acquire (gate G2). 0 rows returned = a live lock exists → FIN_009 / MOD_LOCK_CONFLICT.
INSERT INTO resource_lock (family_id, resource_key, session_id, acquired_by)
VALUES ($1, $2, $3, $4)                                   -- $2 e.g. 'BBPS_BESCOM_KA_001'
ON CONFLICT (family_id, resource_key) WHERE released_at IS NULL DO NOTHING
RETURNING lock_id;

-- Who holds it (for the user message 'A payment to BESCOM is already in progress'):
SELECT rl.session_id, rl.acquired_by, rl.acquired_at, s.fsm_state
FROM resource_lock rl
JOIN supervisor_sessions s ON s.session_id = rl.session_id
WHERE rl.family_id = $1 AND rl.resource_key = $2 AND rl.released_at IS NULL;

-- Release — only after the Phase 2 COMMIT (FTS §4.3), or on FAILED/ABORTED, by the Healer, or by override.
UPDATE resource_lock
SET released_at = NOW(), release_reason = $2      -- 'completed' | 'failed' | 'aborted' | 'healer_stale' | 'admin_override'
WHERE session_id = $1 AND released_at IS NULL;
```

### Q8 — Audit Log: Family Activity Feed (Paginated)

Used by: Admin Dashboard, Family Transparency Report. Returns the audit trail for a family, most recent first. Paginated using keyset pagination (not OFFSET) for performance at scale.
```text
-- Page 1 (no cursor)
SELECT
  al.log_id,
  al.action,
  al.details,
  al.fsm_exit_state,
  al.timestamp,
  u.display_name AS actor_name,
  u.role         AS actor_role
FROM audit_log al
JOIN users u ON u.user_id = al.user_id
WHERE al.family_id = $1
ORDER BY al.timestamp DESC
LIMIT 20;

-- Page N (cursor = last seen timestamp + log_id from previous page)
SELECT ... FROM audit_log al
JOIN users u ON u.user_id = al.user_id
WHERE al.family_id = $1
  AND (al.timestamp, al.log_id) < ($2, $3)   -- cursor
ORDER BY al.timestamp DESC, al.log_id DESC
LIMIT 20;
```

### Q9 — Find All Expired Shadow Nodes (Nightly Purge)

Used by: Shadow Node cleanup cron job. Runs nightly at 02:00 IST.
```sql
-- Step 1: Find expired shadows
SELECT user_id, display_name, family_id
FROM users
WHERE shadow_node = TRUE
  AND shadow_expires_at < NOW()
  AND deleted_at IS NULL;

-- Step 2: Soft-delete them (not hard delete — DPDP 24-hour window)
UPDATE users
SET deleted_at = NOW()
WHERE shadow_node = TRUE
  AND shadow_expires_at < NOW()
  AND deleted_at IS NULL;

-- Note: Also cancel any pending proxy_assignments for these users.
-- The ON DELETE CASCADE on users → proxy_assignments handles hard deletes,
-- but soft-deleted users need manual proxy cleanup:
-- DELETE FROM proxy_assignments WHERE managed_user_id IN (list) OR proxy_user_id IN (list);
```

### Q10 — Healer: Find Queued Tasks Due for Retry

Used by: Healer cron job, runs every 5 minutes. Returns tasks ready for retry, ordered by urgency (AUDIT_LOG_WRITE is always first).
```text
SELECT
  task_id,
  family_id,
  user_id,
  task_type,
  payload,
  retry_count,
  max_retries,
  last_error
FROM offline_task_queue
WHERE status = 'pending'
  AND next_retry_at <= NOW()
  AND expires_at > NOW()
ORDER BY
  CASE task_type WHEN 'AUDIT_LOG_WRITE' THEN 1 ELSE 2 END ASC,  -- Audit always first
  next_retry_at ASC
LIMIT 50;   -- Process max 50 tasks per run to avoid lock contention
```

### Q11 — Get Relationship Map (for Supervisor Context)

Used by: Supervisor Agent when building the family graph context object for the LLM. Returns a flat list of relationships to inject into the prompt: 'Ravi is parent of Arjun, spouse of Priya.'
```text
SELECT
  u_from.display_name  AS from_name,
  u_from.role          AS from_role,
  fr.relationship_type,
  u_to.display_name    AS to_name,
  u_to.role            AS to_role
FROM family_relationships fr
JOIN users u_from ON u_from.user_id = fr.from_user_id AND u_from.deleted_at IS NULL
JOIN users u_to   ON u_to.user_id   = fr.to_user_id   AND u_to.deleted_at IS NULL
WHERE fr.family_id = $1
  AND fr.is_active = TRUE
ORDER BY u_from.display_name, fr.relationship_type;
```

### Q12 — Verify Audit Log Hash Chain Integrity

Used by: Daily integrity verification job. Reads all entries for a family in timestamp order, re-computes expected_hash, and flags any mismatch. Run as a read-only operation against a replica, not the primary.
```sql
-- Fetch all entries in chain order for a family
SELECT log_id, user_id, action, details, timestamp, previous_hash, current_hash
FROM audit_log
WHERE family_id = $1
ORDER BY timestamp ASC, log_id ASC;

-- Application verification loop (Python pseudocode):
# import json, hashlib
# prev_hash = None
# for row in rows:
#   # CRITICAL: Use canonical JSON (sorted keys, no spaces).
#   # str(row.details) is NON-DETERMINISTIC and will produce false tamper alerts.
#   canonical_details = json.dumps(row.details, sort_keys=True, separators=(',', ':'))
#   payload = str(row.log_id) + str(row.user_id) + row.action + canonical_details + (prev_hash or '')   # NULL -> '' (v1.3)
#   expected = hashlib.sha256(payload.encode('utf-8')).hexdigest()
#   if expected != row.current_hash:
#     alert_admin(family_id, row.log_id, 'HASH_CHAIN_BROKEN')
#     break
#   prev_hash = row.current_hash
```

## 6. Audit Log Action Taxonomy

Every entry in audit_log.action must use one of the standardized action codes below. This ensures consistent querying, filtering, and reporting. Engineers must NOT use free-text strings for the action field.

System-initiated entries: Some audit events are triggered by automated jobs (cron, Healer) rather than a human user. These entries use a reserved system user UUID defined as a constant in the application config (e.g. SYSTEM_ACTOR_UUID = '00000000-0000-0000-0000-000000000001'). This UUID must exist as a user row in the users table with role='managed' and family_id pointing to a reserved system family. This allows audit_log foreign key constraints to hold without special-casing the schema.

| Action Code | Module | Automation Tier | Description | Defined in |
|---|---|---|---|---|
| BILL_PAYMENT_INITIATED | Finance | Level 1 | User approved a bill payment; Phase 1 committed, execution in progress. | FTS §2.3 |
| BILL_PAYMENT_EXECUTED | Finance | Level 1 | BBPS confirmed the payment; written in the Phase 2 commit. **Replaces v1.2.1's BILL_PAYMENT_SUCCESS.** | FTS §4.3 |
| BILL_PAYMENT_FAILED | Finance | Level 1 | BBPS rejected or the payment failed pre-debit. | FTS §4.4 |
| BILL_PAYMENT_ZOMBIE_FAILED | Finance | system | Healer found BBPS FAILED for a zombie session. | FTS §6.4 |
| BILL_PAYMENT_HEALER_FAILED_CONFIRMATION | Finance | system | Healer found BBPS FAILED while resolving an AUDIT_LOG_WRITE task. | FTS §6.3 |
| BILL_PAYMENT_REFUND_INITIATED | Finance | system | BBPS/PSP refund initiated; carries refund_ref_id. | FTS §8.3 |
| BILL_PAYMENT_REFUND_COMPLETED | Finance | system | Refund credited. | FTS §8.3 |
| AUTO_PAYMENT_EXECUTED | Finance | Level 2 | Recurring payment auto-executed within pre-set limit. | DM v1.2.1 |
| ADMIN_SESSION_OVERRIDE | Finance | Level 0 | Admin forced a session to FAILED or SUCCESS_CONFIRMATION with a reason. | FTS §11.3 |
| CONSENT_GRANTED | Consent | Level 0 | User granted consent for a purpose_code (with handle if DPI). | CM §4.4 |
| CONSENT_RENEWED | Consent | Level 1 | Consent renewed; new record and handle created. | CM §7.3 |
| CONSENT_WITHDRAWN | Consent | Level 0 | User withdrew consent in FamilyLifeOS. **Replaces v1.2.1's CONSENT_REVOKED.** | CM §4.4 |
| CONSENT_REVOKED_EXTERNAL | Consent | system | DPI webhook reported revocation/pause. | CM §9.3 |
| CONSENT_EXPIRED | Consent | system | Watchdog marked a consent expired. | CM §7.2 |
| CONSENT_REVERIFY_PASSED | Consent | system | CONSENT_REVERIFY gate passed. | CM §5 |
| CONSENT_REVERIFY_FAILED | Consent | system | CONSENT_REVERIFY gate failed; session did not execute. | CM §5 |
| PARENTAL_CONSENT_GRANTED | Consent | Level 0 | A parent granted consent on behalf of a minor. | CM §2.5 |
| PROXY_CONSENT_GRANTED | Consent | Level 0 | An assigned proxy granted consent on behalf of a managed profile. | CM v1.3 §2.6 |
| CONSENT_UI_VERSION_CHANGED | Consent | system | A material disclosure change queued re-consent. | CM §4.6 |
| MEMBER_ADDED | Family | Level 0 | Admin added a family member (or shadow node). | DM v1.2.1 |
| MEMBER_REMOVED | Family | Level 0 | Admin removed a family member. | DM v1.2.1 |
| ROLE_CHANGED | Family | Level 0 | Admin changed a member's role. | DM v1.2.1 |
| PROXY_ASSIGNED | Family | Level 0 | Admin assigned a proxy for a managed profile. | DM v1.2.1 |
| PROXY_ACTION | Family | Level 1 | Proxy acted on behalf of a managed profile. | DM v1.2.1 |
| MODULE_ACTIVATED | System | Level 0 | Admin activated a module for the family. | MR §5.2 |
| MODULE_DEACTIVATED | System | Level 0 | Admin deactivated a module. | MR §5.2 |
| MODULE_MANIFEST_DRIFT | System | system | Manifest hash changed without a version bump; module excluded. | MR §5.1 |
| MOD_CALLGRAPH_VIOLATION | System | system | A module called a service it did not declare. | MR §7.1 |
| MOD_CONSENT_STALE | System | system | Module received a reverified_at older than 60 s (Supervisor sequencing bug). | MR §6.2 |
| ROLE_VIOLATION | System | system | A restricted role attempted a sensitive pillar; high-severity Admin alert. | PRD §6 |
| SOS_TRIGGERED | Elder Care | Level 0 | SOS emergency state entered. | DM v1.2.1 |
| SOS_RESOLVED | Elder Care | Level 0 | SOS cleared by Admin. | DM v1.2.1 |
| DEVICE_REGISTERED | System | Level 0 | New device registered to the family. | DM v1.2.1 |
| DATA_EXPORT_REQUESTED | System | Level 0 | Admin requested a data export (DPDP). | CM §4.5 |
| DATA_EXPORT_COMPLETED | System | system | Export delivered; file_size_bytes, delivered_to. | CM §4.5 |
| ACCOUNT_DELETION_REQUESTED | System | Level 0 | User requested account deletion (last entry by the user's own action). | CM §2.2 |
| DATA_DELETION_COMPLETED | System | system | Nightly purge hard-deleted the user's rows (final entry before cascade). | CM §2.2 |
| HASH_CHAIN_VERIFIED | System | system | Integrity check passed. | DM §7.2 |
| SHADOW_NODE_EXPIRED | System | system | Unaccepted shadow node soft-deleted after 7 days; details={shadow_user_id, display_name, expired_at}. | DM §4.2 |
| VOICE_INTENT_PROCESSED | Voice | Level 0 | A voice utterance was transcribed and passed to the Supervisor (no transcript stored). | RB §10.3 |
| VOICE_ASR_LOW_CONFIDENCE | Voice | system | ASR confidence < 0.80; details={confidence, language, transcript_length}. | RB §7.3 |

> ℹ  v1.3 made this table the union of every code written by FTS v1.2, CM v1.2, RB v1.2, MR v1.1 and PRD v2.2 (Inconsistency Register item 7). Two v1.2.1 codes were renamed rather than kept as duplicates: BILL_PAYMENT_SUCCESS → BILL_PAYMENT_EXECUTED and CONSENT_REVOKED → CONSENT_WITHDRAWN. "system" in the tier column means the actor is SYSTEM_ACTOR_UUID. Every code gets a typed, PII-free payload model in Tech_Spec_Audit_Log_Implementation.md (P1).

## 7. Data Lifecycle Management

### 7.1 Soft Delete & DPDP Compliance

The DPDP Act 2023 mandates that user data is purged within 24 hours of a deletion request. Our soft-delete approach satisfies this:
- User requests deletion → Service sets users.deleted_at = NOW() AND revokes all consent_handles immediately.
- User receives confirmation: 'Your account will be fully deleted within 24 hours.'
- Nightly purge job (runs at 01:00 IST) → Hard-deletes all rows where deleted_at < NOW() - 24h across all tables (ON DELETE CASCADE handles child tables).
- If the family has only 1 admin requesting deletion: system requires assigning a new admin first, or allows deletion after 24h grace period with no new admin (family is fully dissolved).

### 7.2 Hash Chain Integrity Verification Schedule

The audit log hash chain must be verified on a regular schedule to detect tampering early:
- Daily: Verify hash chain for all families with write activity in the last 24 hours.
- Weekly: Full verification sweep of all families.
- On demand: Admin can trigger a verification from the dashboard (HASH_CHAIN_VERIFIED action is logged upon success).
- Alert threshold: Any hash mismatch triggers a P0 alert to the engineering team and the affected family's admin.

### 7.3 Consent Fetch Rate Limit Reset

The fetch_count_today column in consent_handles is bookkeeping, not enforcement (v1.3): the Redis hourly bucket in Runbook §2.2 blocks calls. The column feeds renewal inheritance (Consent Manager §7.3) and audit tooling, and is reset daily:
```text
-- Runs at midnight UTC (05:30 IST)
UPDATE consent_handles
SET fetch_count_today = 0
WHERE fetch_count_today > 0;
```

### 7.4 Supervisor Session Expiry Cleanup

Sessions that have timed out without resolution occupy space and can confuse recovery logic. A cleanup job removes stale sessions:
```text
-- Runs every 5 minutes (same cadence as the Healer, FTS §6.1)  [v1.3: was '15 minutes']
-- Step 1: Mark timed-out sessions as ABORTED — but NEVER sessions in EXECUTION.
-- An EXECUTION session past its expires_at is a zombie: money may have moved, and the
-- Healer's sweep (FTS §6.4) looks for fsm_state = 'EXECUTION'. Aborting it here would hide it
-- from the Healer and strand the resource lock.  [v1.3 fix]
UPDATE supervisor_sessions
SET fsm_state = 'ABORTED'
WHERE expires_at < NOW()
  AND fsm_state NOT IN ('IDLE','SUCCESS_CONFIRMATION','FAILED','ABORTED','EXECUTION');

-- Step 2: Release live locks whose session is terminal (resource_lock, §3.11).
UPDATE resource_lock rl
SET released_at = NOW(), release_reason = 'session_expired'
FROM supervisor_sessions s
WHERE s.session_id = rl.session_id
  AND rl.released_at IS NULL
  AND s.fsm_state IN ('ABORTED','FAILED','SUCCESS_CONFIRMATION');

-- Step 3: Purge released locks older than 7 days, then sessions older than 24h.
DELETE FROM resource_lock WHERE released_at < NOW() - INTERVAL '7 days';
DELETE FROM supervisor_sessions
WHERE updated_at < NOW() - INTERVAL '24 hours'
  AND fsm_state IN ('IDLE','SUCCESS_CONFIRMATION','FAILED','ABORTED');
```

## 8. Seed Data (Development & Testing)

The following seed data represents the canonical test family used across all unit tests, integration tests, and simulator runs. This is the 'Sharma Family' scenario referenced throughout the PRD.
```sql
-- ─── SEED 0: reserved SYSTEM family and actor (V001, every environment) ──────────────
-- Used for audit rows written by cron jobs and the Healer (§6). Never shown to users;
-- excluded from every family-facing query by its family_id (Q1).
INSERT INTO families (family_id, family_name, subscription_tier)
VALUES ('00000000-0000-4000-8000-000000000000', 'SYSTEM', 'free');

INSERT INTO users (user_id, family_id, display_name, role, verification_status)
VALUES ('00000000-0000-4000-8000-000000000001', '00000000-0000-4000-8000-000000000000',
        'SYSTEM_ACTOR', 'managed', 'unverified');
-- SYSTEM_FAMILY_UUID = '00000000-0000-4000-8000-000000000000'
-- SYSTEM_ACTOR_UUID  = '00000000-0000-4000-8000-000000000001'

-- ─── SEED: Sharma Family (dev and test profiles only) ────────────────────────────────
-- v1.3: identifiers are now valid UUIDs (the v1.2.1 mnemonics such as 'usr-ravi-…' were not).
-- Mnemonic: family a…01; users b…01 Ravi, b…02 Priya, b…03 Arjun, b…04 Nani, b…05 Ramesh.

-- 1. Create the family
INSERT INTO families (family_id, family_name, subscription_tier)
VALUES ('a0000000-0000-4000-8000-000000000001', 'Sharma Family', 'pro');

-- 2. Create users
INSERT INTO users (user_id, family_id, phone_number, display_name, role, verification_status) VALUES
  -- Admin: Ravi Sharma
  ('b0000000-0000-4000-8000-000000000001', 'a0000000-0000-4000-8000-000000000001',
   '+919876543210', 'Ravi Sharma', 'admin', 'kyc_verified'),
  -- Member (spouse): Priya Sharma
  ('b0000000-0000-4000-8000-000000000002', 'a0000000-0000-4000-8000-000000000001',
   '+919876543211', 'Priya Sharma', 'member', 'otp_verified'),
  -- Minor: Arjun (17 years old)
  ('b0000000-0000-4000-8000-000000000003', 'a0000000-0000-4000-8000-000000000001',
   '+919876543212', 'Arjun Sharma', 'minor', 'otp_verified'),
  -- Managed profile: Nani (Ravi's mother, no phone)
  ('b0000000-0000-4000-8000-000000000004', 'a0000000-0000-4000-8000-000000000001',
   NULL, 'Nani (Savitri Sharma)', 'managed', 'unverified'),
  -- Staff: Ramesh (driver)
  ('b0000000-0000-4000-8000-000000000005', 'a0000000-0000-4000-8000-000000000001',
   '+919876543213', 'Ramesh Kumar', 'staff', 'otp_verified');

-- 3. Create relationships (bidirectional, one transaction — §3.3)
INSERT INTO family_relationships (family_id, from_user_id, to_user_id, relationship_type) VALUES
  ('a0000000-0000-4000-8000-000000000001', 'b0000000-0000-4000-8000-000000000001', 'b0000000-0000-4000-8000-000000000002', 'spouse'),
  ('a0000000-0000-4000-8000-000000000001', 'b0000000-0000-4000-8000-000000000002', 'b0000000-0000-4000-8000-000000000001', 'spouse'),
  ('a0000000-0000-4000-8000-000000000001', 'b0000000-0000-4000-8000-000000000001', 'b0000000-0000-4000-8000-000000000003', 'parent'),
  ('a0000000-0000-4000-8000-000000000001', 'b0000000-0000-4000-8000-000000000003', 'b0000000-0000-4000-8000-000000000001', 'child'),
  ('a0000000-0000-4000-8000-000000000001', 'b0000000-0000-4000-8000-000000000002', 'b0000000-0000-4000-8000-000000000003', 'parent'),  -- Priya → Arjun (v1.3 change 16: v_guardians needs both parents)
  ('a0000000-0000-4000-8000-000000000001', 'b0000000-0000-4000-8000-000000000003', 'b0000000-0000-4000-8000-000000000002', 'child'),
  ('a0000000-0000-4000-8000-000000000001', 'b0000000-0000-4000-8000-000000000001', 'b0000000-0000-4000-8000-000000000004', 'child'),
  ('a0000000-0000-4000-8000-000000000001', 'b0000000-0000-4000-8000-000000000004', 'b0000000-0000-4000-8000-000000000001', 'parent'),
  ('a0000000-0000-4000-8000-000000000001', 'b0000000-0000-4000-8000-000000000001', 'b0000000-0000-4000-8000-000000000005', 'employer'),
  ('a0000000-0000-4000-8000-000000000001', 'b0000000-0000-4000-8000-000000000005', 'b0000000-0000-4000-8000-000000000001', 'employee');

-- 4. Assign proxies for Nani (managed profile)
INSERT INTO proxy_assignments
  (managed_user_id, proxy_user_id, proxy_rank, conflict_resolution_rule, notify_timeout_mins, family_id)
VALUES
  ('b0000000-0000-4000-8000-000000000004', 'b0000000-0000-4000-8000-000000000002', 'primary',   'hierarchy', 60,
   'a0000000-0000-4000-8000-000000000001'),
  ('b0000000-0000-4000-8000-000000000004', 'b0000000-0000-4000-8000-000000000001', 'secondary', 'hierarchy', 60,
   'a0000000-0000-4000-8000-000000000001');

-- 5. Register devices
INSERT INTO device_registry (family_id, owner_user_id, device_name, device_type, is_public_surface) VALUES
  ('a0000000-0000-4000-8000-000000000001', 'b0000000-0000-4000-8000-000000000001', 'Ravi Phone',     'mobile',  FALSE),
  ('a0000000-0000-4000-8000-000000000001', 'b0000000-0000-4000-8000-000000000002', 'Priya Phone',    'mobile',  FALSE),
  ('a0000000-0000-4000-8000-000000000001', 'b0000000-0000-4000-8000-000000000001', 'Kitchen Tablet', 'tablet',  TRUE);
  -- Kitchen Tablet: is_public_surface=TRUE → blocks finance/health queries

-- 6. Module activations (v1.3). secure_vault is non-deactivatable and needs no row.
--    Requires the finance and health rows in module_registry, which boot registration creates (MR §8.1).
INSERT INTO family_module_activations (family_id, module_id, activated_by) VALUES
  ('a0000000-0000-4000-8000-000000000001', 'finance', 'b0000000-0000-4000-8000-000000000001'),
  ('a0000000-0000-4000-8000-000000000001', 'health',  'b0000000-0000-4000-8000-000000000001');

-- 7. Consent disclosure + Priya's AA balance consent (v1.3). The consent_handles row must exist first
--    (trigger enforce_dpi_handle, §3.12).
INSERT INTO consent_ui_disclosures (purpose_code, version, disclosure_text, data_types_summary, is_material_change, changed_by, change_rationale)
VALUES ('AA_BALANCE_FETCH', '1.0.0',
        'FamilyLifeOS will read your HDFC account balance to check funds before a bill payment. Balance is kept for 15 minutes. You can revoke this at any time.',
        ARRAY['Account balance (amount only)', 'No transaction history'], TRUE, 'seed', 'Initial disclosure');

INSERT INTO consent_handles (consent_id, user_id, family_id, provider, external_consent_id, status, granted_at, expires_at, data_scope)
VALUES ('c0000000-0000-4000-8000-000000000001', 'b0000000-0000-4000-8000-000000000002', 'a0000000-0000-4000-8000-000000000001',
        'AA', 'sim-aa-handle-priya-hdfc', 'active', NOW(), NOW() + INTERVAL '1 year',
        '{"fi_types": ["DEPOSIT"], "fip_ids": ["HDFC"]}');

INSERT INTO consent_records (user_id, family_id, purpose_code, status, granted_at, expires_at, consent_handle_id, granted_scope, consent_ui_version)
VALUES ('b0000000-0000-4000-8000-000000000002', 'a0000000-0000-4000-8000-000000000001', 'AA_BALANCE_FETCH', 'active', NOW(), NOW() + INTERVAL '1 year',
        'c0000000-0000-4000-8000-000000000001', '{"fi_types": ["DEPOSIT"], "fip_ids": ["HDFC"]}', '1.0.0');
```

## 9. Migration Notes & Schema Evolution

### 9.1 V1 Stability Commitment

The core schema (families, users, family_relationships, proxy_assignments, consent_handles, audit_log) was frozen at v1.2.1 after two reviews and re-opened once, at v1.3, before any database existed. After the v1.3 re-freeze, changes require:
- A written migration plan (Flyway/Alembic migration file).
- Review of all affected queries listed in Section 5.
- Backward-compatible changes only (add columns, never drop or rename in production).
- Announcement to the engineering team before merging.

### 9.2 Recommended Migration Tool

Use Flyway (Java) or Alembic (Python) for migration management. Since the backend is Python/FastAPI, Alembic is the natural choice. Every migration file is version-numbered and committed to the repository. Migrations run automatically on deployment via the CI/CD pipeline.
```text
# File naming convention
# migrations/versions/V001__initial_schema.sql
# migrations/versions/V002__add_shadow_invites.sql
# migrations/versions/V003__consent_rate_limit_columns.sql

# Run all pending migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1
```

### 9.3 Module Table Convention

When engineers implement module-specific tables (finance_transactions, health_records, etc.), they must follow these conventions for consistency:
- Always include family_id UUID NOT NULL REFERENCES families(family_id) ON DELETE CASCADE.
- Always include user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE (the user who owns or triggered the record).
- Always include created_at TIMESTAMPTZ NOT NULL DEFAULT NOW() and updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW().
- Always include deleted_at TIMESTAMPTZ for soft-delete support.
- Always create an index on (family_id, created_at DESC) as the primary access pattern.
- v1.3: module tables live in the module's own schema (`finance.transactions`, `health.records`, `secure_vault.documents`), owned by that module's database role; foreign keys point at `core.users` and `core.families`. Modules never reference other modules' schemas (Module Registry §7.2).

### 9.4 v1.3 Change Summary & Migration Plan

No database has been created yet, so `V001__initial_schema` is authored directly from this version; there is no v1.2.1 → v1.3 migration script. The Alembic revision must create, in this order: extension pgcrypto; schema `core`; tables §3.1–3.9 and §3.11–3.16; the trigger function and triggers of §3.10; the views of §3.17; the functions of §3.18; the seeds of §8 (SYSTEM family/actor and role_module_permissions in every environment, the Sharma family only in dev and test).

| # | Change | Where | Origin |
|---|---|---|---|
| 1 | Roles renamed: spouse → member, child → minor (DB values lowercase) | §3.2, §4, Q1, Q2, §8 | Founder decision 2026-09-17; Inconsistency Register item 3 |
| 2 | Resource lock moved to its own table with release semantics | §3.11, §3.7, Q7, §7.4 | Founder decision; item 1 (FTS §9 assumed the table) |
| 3 | supervisor_sessions gains intent_type, bbps_transaction_ref_id, healer_poll_count, session_notes; `fsm_state` confirmed as the column name | §3.7 | Founder decision; item 2 |
| 4 | offline_task_queue.status gains 'cancelled' | §3.9 | Item 10 (CM §8.2) |
| 5 | consent_handles.provider gains 'ONDC' | §3.5 | CM §3.2 purpose ONDC_ADDRESS_SHARE (found during MR review) |
| 6 | consent_records, consent_ui_disclosures, enforce_dpi_handle folded in; expiry index renamed idx_consent_records_expiry | §3.12–3.13 | Item 12 |
| 7 | module_registry, intent_routes, family_module_activations folded in | §3.14–3.15 | Item 12 |
| 8 | role_module_permissions table; four kernel views with DDL | §3.16–3.17 | MR OI-2; item 12 |
| 9 | Audit write protocol fn_lock_audit_tail / fn_append_audit; NULL previous_hash serialises as '' | §3.18, §3.6, Q12 | MR §7.2 (function was named but undefined); FTS §11.3 |
| 10 | Action taxonomy = union across specs; BILL_PAYMENT_SUCCESS → BILL_PAYMENT_EXECUTED; CONSENT_REVOKED → CONSENT_WITHDRAWN | §6 | Item 7 |
| 11 | Session-expiry cleanup runs every 5 minutes and never aborts EXECUTION sessions | §7.4 | Item 8, plus a latent bug found in v1.3 review |
| 12 | fetch_count_today is bookkeeping; Redis is the enforcement point | §3.5, Q6, §7.3 | Item 11 |
| 13 | Seed identifiers are valid UUIDs; SYSTEM family/actor, activations and a sample consent seeded | §8 | v1.3 review |
| 14 | All kernel objects live in schema `core`; module schemas per module | §1.1, §9.3 | MR §7.2 |
| 16 | family_relationships gains 'guardian' / 'ward'; new kernel view v_guardians (parents and legal guardians of minors, proxies of managed profiles, with proxy rank, conflict rule and timeout); seed gains the Priya ↔ Arjun parent/child edges | §3.3, §3.17, §8 | Founder ruling 2026-09-17 on Vault visibility for minors; also closes Health PRD OI-4 |
| 15 | consent_records.proxy_consent_user_id + idx_consent_proxy; action PROXY_CONSENT_GRANTED (taxonomy is now 41 codes) | §3.12, §6 | Founder ruling 2026-09-17 on Health PRD OI-2; CM v1.3 §2.6 |

Consequential edits made the same day in other documents: FTS v1.2 (`fsm_state` naming; lock release semantics), Consent Manager v1.2 (`fsm_state`; lowercase role values; 'cancelled'; ONDC provider; DDL now lives here), Module Registry v1.1 (registry DDL, kernel views and audit functions now live here; consent-provider enum narrowed), Runbook v1.2 (fetch_count_today semantics). Review round 2 by Codex covers this document and the Module Registry together.

## 10. Open Issues & Q&A

### Open Issues

| Issue | Priority | Owner | Resolution |
|---|---|---|---|
| ~~RESOLVED v1.1~~ The UNIQUE constraint on consent_handles(user_id, provider, status) prevented having both an 'expired' and 'active' consent for the same user+provider. | CLOSED | Shantanu Chaudhary | Fixed in v1.1: Replaced with partial unique index CREATE UNIQUE INDEX idx_consent_one_active ON consent_handles(user_id, provider) WHERE status = 'active'; |
| ~~RESOLVED v1.1~~ supervisor_sessions resource_lock race condition: two concurrent workers could both SELECT with no lock found and both INSERT, causing double-execution. | CLOSED | Shantanu Chaudhary | Fixed in v1.1: Added CREATE UNIQUE INDEX idx_session_resource_lock_unique ON supervisor_sessions(resource_lock) WHERE resource_lock IS NOT NULL AND fsm_state NOT IN (...). Second INSERT raises unique violation caught by application. |
| The offline_task_queue has no dead-letter queue. Tasks that hit max_retries are marked failed_permanent but not escalated automatically. | MEDIUM | TBD | Add a nightly job that alerts Admin for any failed_permanent tasks older than 1 hour. Define in Tech_Spec_Financial_Transaction_Safety.md. |
| ~~RESOLVED v1.3~~ supervisor_sessions.resource_lock was a VARCHAR (single resource per session). | CLOSED | Shantanu Chaudhary | v1.3: resource_lock is a table (§3.11); a session may hold several locks. Multi-resource atomicity (lock ordering) is still an application-layer concern; document in Tech_Spec_Supervisor_Concurrency_Control.md (P1). |
| Row-level security is not used inside module schemas; family_id scoping is an application-layer convention (§9.3). | LOW | TBD | Acceptable for the Phase 1 single deployable (MR OI-1). Revisit with Phase 2 sharding. |
| The offline_task_queue composite idempotency key `UNIQUE (family_id, task_type, payload->>'idempotency_key') WHERE status IN ('pending','processing')` is still deferred to Phase 1.1 (tracker parking lot). | LOW | TBD | Add once the Healer has run for a while and duplicate firing has or has not been observed. |

### Q&A

| Asked By | Question | Answer |
|---|---|---|
| Engineering | Why not use an enum type in PostgreSQL instead of VARCHAR + CHECK for roles? | PostgreSQL ENUM types are hard to modify (adding a new value requires ALTER TYPE which locks the table). VARCHAR + CHECK constraints can be altered with a simple ALTER TABLE. Given the possibility of adding new role types in Phase 2, VARCHAR is more operationally safe. |
| Engineering | Why is the audit log hash computed in application code rather than a DB trigger? | Three reasons: (1) DB triggers create tight coupling to the database engine, making the hash algorithm impossible to verify without DB access. (2) Application-computed hashes can be independently verified by auditors using any SHA-256 tool. (3) Triggers fire even for DBA-executed queries, making it impossible to detect a DBA who bypasses the application entirely. A separate verification job is a stronger guarantee. |
| Engineering | Should we use PostgreSQL row-level security (RLS) instead of application-layer RBAC? | No for V1. RLS is powerful but adds operational complexity (every query must set role-context variables, debugging is harder, performance is unpredictable). Application-layer RBAC is easier to test, easier to debug, and sufficient for the scale targets. RLS is worth revisiting at 100K+ families. |
| Engineering | Why does device_registry belong to the core schema instead of a separate auth service? | Surface context (public vs private device) is used by the Supervisor FSM at INTENT_ANALYSIS time to block sensitive queries. It must be available in the same transaction as the permission check, not across a service boundary. Co-locating it in the core database avoids a network hop on the critical path of every query. |
| Legal/Compliance | Does the soft-delete approach (24h window) satisfy DPDP Act 2023? | Yes. The DPDP Act requires data to be 'erased without delay' which is interpreted as within 72 hours. Our 24-hour window exceeds this requirement. The key requirement is that the user cannot be re-identified after deletion. We satisfy this by revoking all DPI consents immediately on deletion request (not waiting for the 24h window). |
| Engineering | How does revalidation_required get set? Who sends the AA webhook and who handles it? | The AA framework (Sahamati network) sends a consent status notification to the FIU's registered webhook endpoint when a user revokes consent externally. The webhook handler sets revalidation_required = TRUE for the matching consent_handle row. The next time CONSENT_REVERIFY runs for that consent, it detects the flag, makes a live API call to AA to confirm current status, and either marks the consent 'revoked' or resets the flag to FALSE. This prevents serving stale 'active' data for up to 15 minutes after external revocation. |
| Engineering (v1.3) | Modules now write audit rows through a database function. Doesn't that contradict 'hash computed in application code'? | No. fn_append_audit inserts a hash the caller computed and only verifies that the caller's previous_hash still matches the chain head; it never serialises `details` itself. That matters because jsonb key ordering differs from Python's sort_keys, so a hash computed in the database would not be reproducible by an external auditor with a plain SHA-256 tool. The function exists for privilege isolation (modules have no table access) and for the per-family row lock (fn_lock_audit_tail), not for hashing. |
| Engineering (v1.3) | Why not keep the resource lock on supervisor_sessions and just fix the partial index? | Because the lock's lifetime is not the session's. FTS §9.3 detects stale locks by acquired_at and releases them when the session is terminal; FTS §4.5 crash scenario D is precisely 'session SUCCESS_CONFIRMATION, lock still held'. A column cannot express 'released independently of state', and a row with released_at can. It also allows one session to hold several locks. |
| Engineering | Why does SYSTEM_ACTOR_UUID need to be a real user row rather than NULL in audit_log.user_id? | The audit_log.user_id has a NOT NULL foreign key to users(user_id). Allowing NULL would require removing the FK constraint, breaking referential integrity and making it harder to JOIN for dashboards. Using a seeded system user row keeps the schema consistent. The system family and user are inserted as part of the database migration (V001), never exposed to end users, and filtered out of all family-facing queries. |

**END OF DOCUMENT**
Data_Model_Schema.md  •  FamilyLifeOS  •  v1.3 (revision in review)  •  September 2026
