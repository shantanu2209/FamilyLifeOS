# Tech Spec: Module Registry & Agent Communication Contract

**Status:** Phase 1 (v1.1 — review round 1 applied by Claude Code on 2026-09-17; review round 2 by Codex pending; freezes on approval)

**Purpose:** To define the contract that makes any FamilyLifeOS module implementable: the module manifest schema, the Supervisor→Worker dispatch envelope, the Core vs. Service tier rules, and the isolation model. This document is the last Priority 0 specification of the Phase 1 Build Gate.

## 0. Document Governance

| **Version** | **Date** | **Description of Change** | **Author** |
|---|---|---|---|
| v1.0 | 2026-07-03 | Initial specification: manifest schema, dispatch envelope v1.0, tier rules, isolation model, registration flow, error taxonomy. | Shantanu Chaudhary |
| v1.1 | 2026-09-17 | Review round 1 (see §13). Seven fixes: (1) `MOD_EXECUTION_UNCONFIRMED` no longer moves the session to FAILED — it stays in EXECUTION so the Healer's zombie sweep (FTS §6.4) can find it (§6.3, §9, §10); (2) `requires_consent_providers` narrowed to real consent providers (aa, abha, digilocker, ondc); BBPS and Bhashini are DPI providers, not consent providers (§4.1, §4.2, §10); (3) PAY_BILL example sets `biometric_required_above_paise: 0` — every BBPS bill payment needs biometric approval (FTS §2.2 G4); (4) audit writes go through the two-function protocol `fn_lock_audit_tail` / `fn_append_audit` with the hash computed in application code (Data Model v1.3 §3.18) instead of an undefined single function (§7.2, §10); (5) resource lock is the `core.resource_lock` table (Data Model v1.3 §3.11) (§7.3); (6) registry DDL and the four kernel views now have a single source in Data Model v1.3 §3.14–3.17; OI-2 closed; (7) cross-references updated to the current document versions; Master Context and NFR back-annotations recorded. | Shantanu Chaudhary (with Claude Code) |

**Cross-references (authoritative, do not duplicate):**

| Document | What this spec defers to it |
|---|---|
| Master_Context v2.1 | Module list (Eight Pillars), phase prioritization, communication protocol baseline (§3.4, now annotated for the Phase 1 monolith), DPI risk profiles |
| Data Model v1.3 | Core tables incl. `resource_lock` (§3.11), registry tables (§3.14–3.15), role permissions and kernel views (§3.16–3.17), audit write functions (§3.18), action codes (§6), module table convention (§9.3) |
| Tech_Spec_Supervisor_State_Machine v2.1 | FSM states, automation tiers, TTL policy, idempotency key lifecycle |
| Tech_Spec_Financial_Transaction_Safety v1.2 (frozen) | Two-phase commit (payment + audit), zombie detection, Healer recovery, gates G1–G5 |
| Tech_Spec_Consent_Manager v1.2 (frozen) | Consent handle lifecycle, purpose registry, CONSENT_REVERIFY semantics, revocation propagation |
| Runbook_DPI_Rate_Limits v1.2 (frozen) | Per-provider rate limits, request coalescing, DPI-level circuit breakers, backoff-with-jitter sequences |
| PRD_FamilyLifeOS_Core v2.2 | Roles, scenarios, shared system services, conflict-resolution matrix |

---

## 1. Scope

### 1.1 In scope (this document)

1. **Module manifest** — the JSON schema every module must ship, validated at boot.
2. **Dispatch envelope** — the `ModuleRequest` / `ModuleResponse` contract between the Supervisor and Worker Agents.
3. **Tier model** — Core Modules vs. Service Modules, and the permitted call graph between them.
4. **Isolation model** — how module boundaries are enforced in code, in the database, and at runtime.
5. **Registration & discovery** — boot sequence, family-level activation, intent routing.
6. **Error taxonomy** — standardized error codes and their mapping to Supervisor FSM transitions.

### 1.2 Explicitly out of scope (deferred)

- **Full per-module interfaces** (every intent of FinanceAgent, HealthAgent, etc.) — these belong to the module PRDs and module tech specs (P1). This document defines the contract those specs must conform to, plus one worked example.
- **Third-party module marketplace** — Vision Parking Lot item. The manifest schema is designed not to preclude it, but no marketplace mechanics (signing, sandboxed untrusted code, revenue share) are specified here.
- **Dynamic hot-loading of modules** — Phase 1 registration is static at boot. Restart-to-register is acceptable for a solo-operated deployment.
- **Multi-region / sharded dispatch** — Phase 3 concern per Master Context §3.5.

---

## 2. Architecture Decision: Modular Monolith with a Transport-Agnostic Contract

### 2.1 The decision

**Phase 1 runs all modules in-process inside a single FastAPI deployable.** Modules are Python packages under `modules/`, loaded at boot by the Registry. There are no per-module containers, no Kubernetes, no inter-service network calls between the Supervisor and Worker Agents.

**However, all Supervisor↔Module communication uses a JSON-serializable envelope (§6) as if it crossed a network boundary.** In Phase 1 the "transport" is a direct function call; the envelope is constructed, validated, and passed as a dict. When a module later needs to be extracted into its own container (Phase 2+, per Master Context §3.5 scaling triggers), only the transport adapter changes — the contract does not.

### 2.2 Rationale

1. **Solo-founder feasibility.** One deployable, one CI pipeline, one log stream, one thing to be paged about. Microservices at 0 users is an anti-goal (Project Tracker: "no Kubernetes for 100 users").
2. **Latency budget.** NFR v2.1 allocates <400ms for inter-agent communication inside a <2.0s end-to-end budget. An in-process call costs microseconds; a REST hop on Indian mobile-adjacent infrastructure costs 20–80ms plus serialization plus failure modes. We spend the budget on DPI calls, which are the actual bottleneck.
3. **Failure surface.** Every network boundary is a place where "zombie" states can be born. Phase 1 keeps the only irreversible network boundaries at the DPI edge (BBPS, AA, etc.), where the Financial Transaction Safety spec already handles them.
4. **Migration is preserved, not prepaid.** The envelope contract, per-module DB schemas, and per-module connection pools mean extraction is a mechanical exercise later, not a rewrite.

### 2.3 Deviation notice (Master Context §3.3/§3.4)

Master Context v2.0 lists "REST APIs with JWT authentication" for agent communication and "Docker containers, Kubernetes" for deployment. This spec **narrows** that for Phase 1: the envelope carries the same semantics REST would (auth context, timeout, retry, circuit breaking) without the network hop. JWT between internal agents is unnecessary when they share a process; actor identity travels inside the envelope and is validated by the Supervisor before dispatch. The Master Context values (30s timeout, 3 retries with exponential backoff, circuit breaker) are retained as envelope-level semantics in §6.5. RabbitMQ is likewise deferred: Phase 1 async work uses the Postgres-backed `offline_task_queue` already specified in Data_Model_Schema v1.2.1 §3.9. Back-annotated into Master Context v2.1 §3.3–3.4 on 2026-09-17.

---

## 3. Module Tiers

### 3.1 Tier definitions

| Tier | Name | Members (Phase 1) | Properties |
|---|---|---|---|
| **Kernel** | Not modules | Supervisor FSM, Consent Manager, Audit Writer, DPI Gateway, Registry itself | Always present, never deactivatable, not described by manifests. Defined by their own frozen specs. |
| **Core** | Worker Agents (the Eight Pillars) | Phase 1: `secure_vault`, `finance`, `health` (per Master Context §5.1) | Own a database schema, register **intents**, receive Supervisor dispatches, may call Service Modules and the DPI Gateway. |
| **Service** | Shared System Services | `notification_engine`, `translation` (Bhashini wrapper), `ocr`, `payment_routing` (per PRD §5) | Stateless utilities. Register **capabilities**, not intents. Invoked by the Kernel or by Core Modules. Never dispatched user intents, never call other modules. |

### 3.2 The permitted call graph (deny-by-default)

```
User → Supervisor (Kernel)
Supervisor → Core Module            [intent dispatch, §6]        ALLOWED
Supervisor → Service Module         [capability call]            ALLOWED
Core Module → Service Module        [capability call]            ALLOWED
Core Module → DPI Gateway (Kernel)  [provider call]              ALLOWED
Core Module → Core Module                                        FORBIDDEN
Service Module → anything                                        FORBIDDEN (leaf nodes)
Any Module → Kernel internals (FSM, Consent DB, Audit table)     FORBIDDEN (see §7)
```

**Why Core→Core is forbidden:** cross-domain reasoning is exactly what the Conflict Resolution Engine exists for (Master Context §3.2). If FinanceAgent could query HealthAgent directly, budget/health conflicts would be resolved ad hoc inside whichever module called first, invisibly to the Supervisor. Instead, when a Core Module needs another domain's data, it returns `status: "conflict"` or `status: "needs_data"` in its response (§6.4) and the Supervisor orchestrates the second dispatch. The Module Dependency Graph in Master Context §5.2 (Vault→Finance, Health→Elder Care) describes **data and activation-order dependencies**, not permission to call.

**Why Service Modules are leaf nodes:** a Service Module that could call other modules is a Core Module wearing a disguise, and it would create cycles in the boot-time dependency resolution (§8.2). If the Notification Engine ever needs family-graph context, that context is passed in by the caller.

---

## 4. Module Manifest

Every module ships a `manifest.json` at its package root. The manifest is the module's **only** self-description; the Registry trusts nothing a module says at runtime that contradicts its manifest.

### 4.1 Manifest JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "familylifeos:module-manifest:1",
  "type": "object",
  "additionalProperties": false,
  "required": ["manifest_version", "module_id", "version", "tier",
               "display_name", "entrypoint", "health_check"],
  "properties": {
    "manifest_version": { "const": 1 },
    "module_id": {
      "type": "string",
      "pattern": "^[a-z][a-z0-9_]{2,40}$",
      "description": "Stable snake_case identifier. Never changes across versions."
    },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+$",
      "description": "Semver. Major bump required for any breaking change to owned schema or intent entities."
    },
    "tier": { "enum": ["core", "service"] },
    "display_name": {
      "type": "object",
      "required": ["en"],
      "description": "BCP-47 keyed display names. Bhashini locales added as translated.",
      "properties": { "en": { "type": "string" } },
      "additionalProperties": { "type": "string" }
    },
    "description": { "type": "string", "maxLength": 500 },
    "deactivatable": {
      "type": "boolean",
      "default": true,
      "description": "false = system cannot boot without this module (e.g. secure_vault)."
    },
    "entrypoint": {
      "type": "string",
      "pattern": "^modules\\.[a-z0-9_]+\\.[a-z0-9_.]+:[A-Za-z_][A-Za-z0-9_]*$",
      "description": "Import path, e.g. 'modules.finance.agent:FinanceAgent'. Class must implement the ModuleProtocol SDK interface."
    },
    "health_check": {
      "type": "string",
      "description": "Method name on the entrypoint class returning {healthy: bool, detail: str} within 2s."
    },
    "intents": {
      "type": "array",
      "description": "Core tier only. Empty/absent for service tier.",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["intent_code", "description", "automation_tier_ceiling",
                     "allowed_roles", "mutating"],
        "properties": {
          "intent_code": {
            "type": "string",
            "pattern": "^[A-Z][A-Z0-9_]{2,40}$",
            "description": "Globally unique across all modules. Duplicate = registration failure."
          },
          "description": { "type": "string" },
          "automation_tier_ceiling": {
            "type": "integer", "minimum": 0, "maximum": 2,
            "description": "Highest automation tier this intent may ever run at. Maximum is 2: Level 3 is forbidden in V1 (FSM spec §2), so the schema itself rejects it."
          },
          "allowed_roles": {
            "type": "array", "minItems": 1,
            "items": { "enum": ["admin", "member", "minor", "elder",
                                 "staff", "managed", "passive"] },
            "description": "RBAC roles permitted to trigger this intent (PRD §2; identical to users.role in Data Model v1.3). Deny-by-default: absent role = blocked at PERMISSION_CHECK."
          },
          "mutating": {
            "type": "boolean",
            "description": "true = requires idempotency_key in dispatch, produces side_effects, subject to CONSENT_REVERIFY and two-phase commit rules."
          },
          "requires_consent_providers": {
            "type": "array",
            "items": { "enum": ["aa", "abha", "digilocker", "ondc"] },
            "description": "Consent providers only — those that issue consent handles (Data Model v1.3 §3.5). BBPS and Bhashini are DPI providers for routing (dpi_providers), not consent providers: payments are gated by biometric approval (FTS §2.2 G4) and voice by the first-party purpose VOICE_INTENT_PROCESSING (CM §3.2). Dispatch is rejected with MOD_CONSENT_MISSING unless an active consent handle exists for each listed provider. (v1.1)"
          },
          "biometric_required_above_paise": {
            "type": ["integer", "null"],
            "description": "Overrides only downward. System floor is ₹2,000 (200000 paise) per NFR §2.2; a module may require biometrics at a lower threshold, never a higher one. 0 means always. Every BBPS bill payment is 0 (FTS §2.2 gate G4). (v1.1)"
          },
          "entities_schema": {
            "type": "object",
            "description": "JSON Schema for intent.entities. Supervisor validates before dispatch; invalid = AWAITING_CLARIFICATION, not module error."
          }
        }
      }
    },
    "capabilities": {
      "type": "array",
      "description": "Service tier only. Named operations, e.g. 'notify.push', 'translate.text'.",
      "items": {
        "type": "object",
        "required": ["capability_code", "description"],
        "properties": {
          "capability_code": { "type": "string", "pattern": "^[a-z][a-z0-9_.]{2,40}$" },
          "description": { "type": "string" },
          "params_schema": { "type": "object" }
        }
      }
    },
    "data_scopes": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "owns_schema": {
          "type": ["string", "null"],
          "pattern": "^[a-z][a-z0-9_]{2,30}$",
          "description": "PostgreSQL schema this module owns (core tier). Must equal module_id. null for service tier."
        },
        "core_read_views": {
          "type": "array",
          "items": { "enum": ["v_family_members", "v_module_permissions",
                               "v_active_consents", "v_device_surfaces"] },
          "description": "Whitelisted kernel views this module's DB role may SELECT (§7.2). Nothing else in core is visible."
        }
      }
    },
    "dpi_providers": {
      "type": "array",
      "items": { "enum": ["aa", "bbps", "abha", "ondc", "digilocker", "bhashini"] },
      "description": "Providers this module is allowed to reach via the DPI Gateway. Gateway rejects calls to undeclared providers. Rate budgets per provider are owned by Runbook_DPI_Rate_Limits v1.1."
    },
    "service_dependencies": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Service module_ids this module calls. Used for boot ordering and call-graph enforcement."
    },
    "data_dependencies": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Core module_ids whose data this module conceptually depends on (Master Context §5.2). Enforces activation ordering only — NOT permission to call (§3.2)."
    },
    "resource_budgets": {
      "type": "object",
      "properties": {
        "p95_handler_ms": {
          "type": "integer", "maximum": 400,
          "description": "Module's own P95 latency budget excluding DPI wait, per NFR inter-agent budget."
        },
        "hard_timeout_ms": {
          "type": "integer", "maximum": 30000,
          "description": "Absolute ceiling per Master Context §3.4. Supervisor enforces via deadline_at (§6.5)."
        }
      }
    }
  },
  "allOf": [
    {
      "if": { "properties": { "tier": { "const": "core" } } },
      "then": { "required": ["intents", "data_scopes"] }
    },
    {
      "if": { "properties": { "tier": { "const": "service" } } },
      "then": {
        "required": ["capabilities"],
        "properties": {
          "intents": { "maxItems": 0 },
          "data_dependencies": { "maxItems": 0 }
        }
      }
    }
  ]
}
```

**Validation posture: fail-closed.** A manifest that fails schema validation means the module is not loaded — it is excluded from the dispatch table and its intents resolve to `MOD_UNAVAILABLE`. If the invalid module has `deactivatable: false`, the application refuses to boot entirely. This is the same principle as BBPS Redis fail-closed: a system that cannot prove its configuration is safe does not get to run.

### 4.2 Example manifest — FinanceAgent (excerpt)

```json
{
  "manifest_version": 1,
  "module_id": "finance",
  "version": "1.0.0",
  "tier": "core",
  "display_name": { "en": "Financial Command Center", "hi": "वित्तीय कमांड केंद्र" },
  "description": "Bill payments (BBPS), account visibility (AA), recurring payment management.",
  "deactivatable": true,
  "entrypoint": "modules.finance.agent:FinanceAgent",
  "health_check": "health",
  "intents": [
    {
      "intent_code": "PAY_BILL",
      "description": "Pay a utility bill via BBPS.",
      "automation_tier_ceiling": 1,
      "allowed_roles": ["admin", "member"],
      "mutating": true,
      "requires_consent_providers": ["aa"],
      "biometric_required_above_paise": 0,
      "entities_schema": {
        "type": "object",
        "required": ["biller_id"],
        "properties": {
          "biller_id": { "type": "string" },
          "amount_paise": { "type": ["integer", "null"], "minimum": 100 },
          "bill_ref": { "type": ["string", "null"] }
        }
      }
    },
    {
      "intent_code": "CHECK_BALANCE",
      "description": "Fetch consolidated balances via Account Aggregator.",
      "automation_tier_ceiling": 0,
      "allowed_roles": ["admin", "member", "elder"],
      "mutating": false,
      "requires_consent_providers": ["aa"]
    },
    {
      "intent_code": "PAY_RECURRING",
      "description": "Execute a pre-authorized recurring payment within safe limits.",
      "automation_tier_ceiling": 2,
      "allowed_roles": ["admin", "member"],
      "mutating": true,
      "requires_consent_providers": ["aa"],
      "biometric_required_above_paise": 0
    }
  ],
  "data_scopes": {
    "owns_schema": "finance",
    "core_read_views": ["v_family_members", "v_module_permissions", "v_active_consents"]
  },
  "dpi_providers": ["aa", "bbps"],
  "service_dependencies": ["notification_engine", "payment_routing"],
  "data_dependencies": ["secure_vault"],
  "resource_budgets": { "p95_handler_ms": 300, "hard_timeout_ms": 30000 }
}
```

---

## 5. Registry Data Model

Two tables. Both live in the `core` schema (kernel-owned; modules cannot read them — the Registry exposes what modules need via `v_module_permissions`). v1.1: the DDL below is reproduced from Data Model v1.3 §3.14–3.15, which is the single DDL source; if they ever differ, the Data Model wins.

### 5.1 `module_registry` — system-wide registration

```sql
CREATE TABLE core.module_registry (
  module_id       VARCHAR(40) PRIMARY KEY,          -- matches manifest.module_id
  version         VARCHAR(20) NOT NULL,             -- semver from manifest
  tier            VARCHAR(10) NOT NULL
                    CHECK (tier IN ('core','service')),
  manifest        JSONB NOT NULL,                   -- the full validated manifest
  manifest_sha256 CHAR(64) NOT NULL,                -- hash of canonical manifest bytes
  status          VARCHAR(20) NOT NULL DEFAULT 'registered'
                    CHECK (status IN ('registered','disabled')),
  registered_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Intent routing uniqueness: one intent_code maps to exactly one module.
-- Enforced at registration time in application code (JSONB extraction),
-- and belt-and-suspenders at the DB level via a materialized routing table:
CREATE TABLE core.intent_routes (
  intent_code  VARCHAR(40) PRIMARY KEY,             -- global uniqueness IS the constraint
  module_id    VARCHAR(40) NOT NULL REFERENCES core.module_registry(module_id),
  mutating     BOOLEAN NOT NULL,
  tier_ceiling SMALLINT NOT NULL CHECK (tier_ceiling BETWEEN 0 AND 2),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Why `manifest_sha256`:** the Registry recomputes the hash of the on-disk manifest at every boot and compares against the DB row. A mismatch means the manifest changed without a version bump — boot logs a CRITICAL forensic event (`MODULE_MANIFEST_DRIFT`) and, for mutating-intent modules, refuses to load the module until the version is bumped. Silent contract drift is how double-payment bugs are born.

**Why `intent_routes` is a table and not just JSONB extraction:** the PRIMARY KEY on `intent_code` makes duplicate intent registration a database error rather than a code-review hope. Registration of a module whose intent collides with an existing route fails atomically.

### 5.2 `family_module_activations` — per-family activation

Modules are activated per family by an Admin (Level 0 action; audit codes `MODULE_ACTIVATED` / `MODULE_DEACTIVATED` exist in Data Model v1.3 §6).

```sql
CREATE TABLE core.family_module_activations (
  activation_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  family_id      UUID NOT NULL REFERENCES families(family_id) ON DELETE CASCADE,
  module_id      VARCHAR(40) NOT NULL REFERENCES core.module_registry(module_id),
  status         VARCHAR(10) NOT NULL DEFAULT 'active'
                   CHECK (status IN ('active','inactive')),
  activated_by   UUID NOT NULL REFERENCES users(user_id),  -- must hold role 'admin'
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (family_id, module_id)
);

CREATE INDEX idx_activation_family ON core.family_module_activations(family_id, status);
```

**Dispatch rule:** the Supervisor rejects an intent with `MOD_NOT_ACTIVATED` when the target module has no `active` row for the family — with one exception: modules with `deactivatable: false` (secure_vault) are implicitly active for every family and need no row.

**Deactivation semantics:** deactivation stops **dispatch**, not data. The module's schema and rows remain (soft-delete philosophy per Data Model conventions). In-flight sessions targeting the module are allowed to complete; queued `offline_task_queue` tasks for the module are paused, not dropped. Data purge is a separate, explicit Admin action (Level 0) — deferred to module PRDs.

### 5.3 Runtime representations

- **In-memory dispatch table** (per process): `{intent_code → (module_instance, IntentSpec)}` built at boot from `intent_routes` + loaded entrypoints. Registry is small (≤ dozens of rows); no Redis caching layer is needed or wanted.
- **Redis usage by modules** (rate counters, hot caches) MUST namespace keys as `{env}:{module_id}:{...}` — the environment prefix rule from Runbook_DPI_Rate_Limits v1.1 applies to every module key, preventing staging→production contamination.

---

## 6. Dispatch Contract (Supervisor → Core Module)

### 6.1 Design rules

1. **The envelope is the network boundary, even when there is no network.** Everything a module needs must be inside the envelope or reachable through its own schema / whitelisted views. Modules never reach into Supervisor state.
2. **JSON-serializable always.** The envelope must round-trip through `json.dumps`/`loads` losslessly (validated in CI by a property test). This is the guarantee that keeps the Phase 2 extraction path open.
3. **Consent travels by reference, never by value.** The envelope carries `consent_id` handles; raw AA/ABHA tokens live only inside the Consent Manager and are resolved by the DPI Gateway at call time. A module compromise cannot exfiltrate tokens it never held (zero-knowledge principle).
4. **Deadlines are absolute.** `deadline_at` is a timestamp, not a relative timeout — relative timeouts silently stretch across retries and queue waits; absolute deadlines don't.

### 6.2 `ModuleRequest` envelope

```json
{
  "envelope_version": "1.0",
  "request_id": "8f14e45f-...-uuid",
  "session_id": "d3b07384-...-uuid",
  "idempotency_key": "a1b2c3d4-...-uuid",
  "family_id": "f9e8d7c6-...-uuid",
  "actor": {
    "user_id": "u-1111-...-uuid",
    "role": "member",
    "acting_as": null
  },
  "intent": {
    "code": "PAY_BILL",
    "entities": { "biller_id": "BESCOM00000KA01", "amount_paise": 50000, "bill_ref": "KA-2026-07-8812" },
    "automation_tier": 1,
    "confidence": 0.92,
    "raw_input": "BESCOM ka bill bhar do"
  },
  "consent": [
    { "consent_id": "c-2222-...-uuid", "provider": "bbps", "reverified_at": "2026-07-03T10:41:57+05:30" }
  ],
  "context": {
    "locale": "hi-IN",
    "device_id": "dev-3333-...-uuid",
    "is_public_surface": false
  },
  "deadline_at": "2026-07-03T10:42:27+05:30",
  "trace": { "trace_id": "tr-4444", "parent_span": "sp-0001" }
}
```

Field rules:

| Field | Rule |
|---|---|
| `request_id` | Unique per dispatch attempt (new UUID on every retry). For logging/tracing only. |
| `idempotency_key` | **Required iff the intent is `mutating: true`.** Generated at INTENT_ANALYSIS, persisted in `supervisor_sessions.idempotency_key` before dispatch (FSM spec §4). Stable across retries. Absent for read intents. |
| `session_id` | FK to `supervisor_sessions`. Lets the module correlate with the resource lock the Supervisor holds. Modules never write to this table. |
| `actor.acting_as` | Non-null when a proxy acts for a managed profile: `{"managed_user_id": "...", "proxy_assignment_id": "..."}`. The Supervisor has already validated the proxy assignment; the module records `PROXY_ACTION` semantics in its audit events. |
| `intent.automation_tier` | The tier this dispatch runs at. Supervisor guarantees `tier ≤ manifest ceiling` and that Level ≥1 approval gates already passed. Modules MUST NOT re-prompt the user. |
| `consent[].reverified_at` | Set by the Supervisor's CONSENT_REVERIFY state immediately before EXECUTION dispatch. Modules treat a mutating dispatch with any `reverified_at` older than 60 seconds as a contract violation → `MOD_CONSENT_STALE` (terminal). Defense in depth against Supervisor bugs. |
| `context.is_public_surface` | When true (kitchen tablet), modules MUST NOT include financial figures or health details in any response destined for display (PRD Scenario 9). |
| `deadline_at` | Now + intent timeout (default 30,000ms per Master Context §3.4, or manifest `hard_timeout_ms` if lower). Modules check it before starting any DPI call and return `MOD_TIMEOUT` proactively if already exceeded. |

### 6.3 `ModuleResponse` envelope

```json
{
  "envelope_version": "1.0",
  "request_id": "8f14e45f-...-uuid",
  "status": "success",
  "result": {
    "display_key": "finance.pay_bill.success",
    "display_params": { "biller_name": "BESCOM", "amount_paise": 50000 },
    "data": { "bbps_txn_ref": "BBPS-9F3A-2026" }
  },
  "side_effects": [
    {
      "type": "external_call",
      "provider": "bbps",
      "external_ref": "BBPS-9F3A-2026",
      "state": "executed_confirmed",
      "amount_paise": 50000
    }
  ],
  "audit_events": [],
  "cache_metadata": null,
  "error": null,
  "clarification": null,
  "conflict": null,
  "metrics": { "handler_ms": 212, "dpi_ms": 1840 }
}
```

`status` is one of:

| Status | Meaning | Supervisor FSM consequence |
|---|---|---|
| `success` | Intent completed. | → SUCCESS_CONFIRMATION |
| `failure` | See `error` object (§9). | RETRYABLE → retry per §6.5; TERMINAL → FAILED, except `MOD_EXECUTION_UNCONFIRMED`, which keeps the session in EXECUTION for the Healer (§9, v1.1) |
| `needs_clarification` | Module cannot proceed without more info; `clarification.missing_entities` lists what. | → AWAITING_CLARIFICATION (state persists if user closes app, per FSM spec) |
| `conflict` | Module detected a cross-domain constraint it is not allowed to resolve (§3.2). `conflict` carries a Conflict Object. | → Conflict Resolution Engine within REASONING |

Field rules:

| Field | Rule |
|---|---|
| `result.display_key` | i18n message key, not prose. The Kernel's Translation service renders it in the user's Bhashini locale. Modules never hardcode user-facing strings. |
| `side_effects` | **Mandatory and exhaustive for mutating intents.** Every external call that may have committed money or state must appear, with `state` ∈ `executed_confirmed` \| `executed_unconfirmed` \| `not_executed`. Any `executed_unconfirmed` entry is what the Healer (Financial Transaction Safety spec) polls and repairs. A mutating response with an empty `side_effects` array asserts "I touched nothing external" — and the module is accountable to that assertion in forensic review. |
| `audit_events` | Kernel-persisted supplementary events only. **Financial mutations do NOT go here:** per the Financial Transaction Safety spec, the module writes its own audit rows inside the same DB transaction as the state change (two-phase commit). Putting them in the response envelope would break atomicity — a crash between module return and kernel persist would lose the audit trail. |
| `cache_metadata` | Required for read intents that serve cached DPI data: `{fetched_at, source_api, expires_at}` per the TTL policy (FSM spec §3). The Supervisor uses it for stale-data warnings and hard stops. |
| `metrics.handler_ms` | Module-side wall time excluding DPI wait. Compared against manifest `p95_handler_ms` in observability dashboards. |

### 6.4 Idempotency behavior (module side)

For every mutating intent, the module MUST:

1. Maintain an idempotency ledger in its own schema, e.g. `finance.idempotency_ledger(idempotency_key UUID PRIMARY KEY, response_envelope JSONB, created_at TIMESTAMPTZ)`.
2. **Persist the key before the external call** (FSM spec §4), inside the same transaction that records the pending state.
3. On receiving a key it has seen: return the stored response envelope verbatim, without re-executing. This includes stored `failure` responses with TERMINAL errors — a terminal failure is a result, not an invitation to retry with the same key.
4. Never garbage-collect ledger rows younger than 7 days (covers the BBPS 48-hour async-settlement window with margin; full retention policy per Financial Transaction Safety spec).

### 6.5 Timeouts, retries, circuit breakers (Supervisor side)

| Mechanism | Setting | Source |
|---|---|---|
| Hard timeout | 30s per dispatch (or manifest value if lower), enforced via `deadline_at` + `asyncio.wait_for` | Master Context §3.4 |
| Retries | Max 3 attempts, backoff 1s → 2s → 4s **with full jitter** (`sleep = random(0, base)`) | Master Context §3.4 + project jitter principle |
| Retry eligibility | Only `error.class == "RETRYABLE"`; mutating intents retried **only** with the identical `idempotency_key`; never retry after `deadline_at` | This spec |
| Module circuit breaker | 5 consecutive `failure`/timeout responses → module `OPEN` for 30 minutes; half-open probe = 1 read intent | Master Context §3.4 |
| DPI provider circuit breaker | Separate layer, owned by the DPI Gateway | Runbook_DPI_Rate_Limits v1.1 |

**Note on the 3-vs-5 discrepancy:** NFR v2.1 states "DPI circuit breakers: 3 failures → 30min"; Master Context §3.4 states 5 failures for module disablement. These are **different breakers at different layers** and both stand: the DPI Gateway trips at 3 consecutive provider failures (protecting rate budgets and the provider relationship), the module breaker trips at 5 (a module can fail for non-DPI reasons). Annotated in NFR v2.2 §3 and PRD Core v2.2 §4.6 on 2026-09-17.

**Breaker-open behavior:** dispatch to an OPEN module returns `MOD_UNAVAILABLE` immediately and the Supervisor invokes the graceful-degradation script for that domain (Master Context §4.7) — e.g., Finance OPEN → queue payment intents to `offline_task_queue`, notify user via WhatsApp on recovery.

---

## 7. Isolation Model (Three Enforcement Layers)

Module boundaries are enforced at three independent layers. Any single layer failing (a bad code review, a misconfigured grant) leaves two more standing.

### 7.1 Layer 1 — Code: import contracts

- Modules live in `modules/{module_id}/` and may import **only**: the Python stdlib, declared third-party dependencies, and `familylifeos.sdk` (envelope dataclasses, `ServiceClient`, `DPIGatewayClient`, `AuditClient`, base `ModuleProtocol`).
- Cross-module imports (`modules.finance` importing `modules.health`) and kernel-internal imports (`familylifeos.kernel.*`) are **forbidden**, enforced by an `import-linter` contract in CI that fails the build. Not a convention — a broken build.
- Service Modules are called through `ServiceClient.call(capability_code, params)`, which validates the caller's manifest `service_dependencies` at runtime. An undeclared service call raises `MOD_CALLGRAPH_VIOLATION` and is logged as a forensic event.

### 7.2 Layer 2 — Database: schema-per-module with dedicated roles

Each Core Module owns exactly one PostgreSQL schema (name = `module_id`) and connects through its own pool bound to a dedicated role:

```sql
-- Provisioned by migration when the module first registers (example: finance)
CREATE SCHEMA finance;
CREATE ROLE role_module_finance LOGIN;                 -- password from secrets manager
GRANT USAGE, CREATE ON SCHEMA finance TO role_module_finance;
ALTER DEFAULT PRIVILEGES IN SCHEMA finance
  GRANT ALL ON TABLES TO role_module_finance;

-- Whitelisted kernel views only (read-only, minimal columns):
GRANT SELECT ON core.v_family_members,
                core.v_module_permissions,
                core.v_active_consents
  TO role_module_finance;

-- Audit is append-only via the two SECURITY DEFINER functions of the audit write protocol
-- (Data Model v1.3 §3.18); no table access. The hash is computed in application code between
-- the two calls, inside one transaction, so auditors can verify it without database access:
GRANT EXECUTE ON FUNCTION core.fn_lock_audit_tail(UUID) TO role_module_finance;
GRANT EXECUTE ON FUNCTION core.fn_append_audit(UUID,UUID,UUID,VARCHAR,JSONB,VARCHAR,VARCHAR,VARCHAR)
  TO role_module_finance;

-- Everything else is invisible. No grant on core tables, no grant on
-- other module schemas, no CREATEROLE, no SUPERUSER. Deny-by-default.
```

Consequences worth stating explicitly:

- A SQL injection or logic bug inside FinanceAgent **cannot** read `health.*`, `core.consent_handles` (raw handles), or `core.audit_log` history, and cannot UPDATE or DELETE audit rows (append-only preserved by the SECURITY DEFINER function, mirroring the tamper-proof audit requirement).
- The kernel views expose exactly what the module table convention (Data Model §9.3) assumes modules need: family membership, per-role module permissions, active consent **references** (`consent_id`, `provider`, `status`, `expires_at` — never token material). Their DDL is Data Model v1.3 §3.17 (v1.1).
- Module tables follow Data Model §9.3 conventions verbatim (family_id, user_id, created_at, updated_at, deleted_at, `(family_id, created_at DESC)` index). Migrations are Alembic, one migration branch per module schema (Data Model §9.2).
- Row-level security within a module's own schema is **not** used in Phase 1 (single-tenant-per-query access patterns, app-layer family_id scoping per convention). Revisit at Phase 2 sharding. Logged as Open Issue OI-1.

### 7.3 Layer 3 — Runtime: dispatch-time enforcement (Supervisor)

Before any dispatch, the Supervisor validates, in order — each check deny-by-default:

1. Intent exists in `intent_routes` → else `MOD_INVALID_INTENT`.
2. Module registered, not `disabled`, breaker not OPEN → else `MOD_UNAVAILABLE`.
3. Module active for this family (§5.2) → else `MOD_NOT_ACTIVATED`.
4. Actor role ∈ manifest `allowed_roles`, cross-checked against `v_module_permissions` → else BLOCKED at PERMISSION_CHECK (never reaches the module).
5. `automation_tier ≤ tier_ceiling`; Level 3 structurally impossible (schema caps at 2).
6. Active consent handle exists for each `requires_consent_providers` entry → else `MOD_CONSENT_MISSING`.
7. Mutating intent: `idempotency_key` present and persisted to `supervisor_sessions`; resource lock acquired by INSERT into `core.resource_lock` (partial unique index, Data Model v1.3 §3.11; released only after the Phase 2 COMMIT) → else `MOD_LOCK_CONFLICT` ("A payment is already in progress").
8. `entities` validate against `entities_schema` → else AWAITING_CLARIFICATION.

The DPI Gateway repeats its own checks at call time (provider declared in manifest, consent handle active, rate budget available) — the module sits between two enforcement layers and is trusted with neither tokens nor budget accounting.

---

## 8. Registration & Discovery Flow

### 8.1 Boot sequence (static registration)

```
1. DISCOVER   Scan modules/*/manifest.json
2. VALIDATE   JSON Schema (§4.1) + envelope_version compatibility.
              Fail → module excluded; if deactivatable=false → ABORT BOOT.
3. HASH       SHA-256 of canonical manifest bytes vs. module_registry row.
              Drift without version bump → CRITICAL log MODULE_MANIFEST_DRIFT;
              mutating-intent modules excluded until version bumped.
4. RESOLVE    Topological sort over service_dependencies + data_dependencies.
              Cycle detected → ABORT BOOT (a cycle is a design error, not a
              runtime condition to survive).
5. REGISTER   Upsert module_registry + rebuild intent_routes in one DB
              transaction. Duplicate intent_code → transaction aborts →
              both offending modules excluded, CRITICAL log.
6. LOAD       Import entrypoints in topological order; instantiate with the
              module's own DB pool + scoped SDK clients.
7. PROBE      Call each module's health_check (2s budget). Unhealthy
              deactivatable module → excluded, Admin notified. Unhealthy
              non-deactivatable module → ABORT BOOT.
8. READY      Dispatch table live. Supervisor reconciles interrupted
              sessions from the PostgreSQL journal (FSM spec §1.3) — only
              after the registry is ready, since recovery may re-dispatch.
```

Boot is idempotent and takes O(seconds). "Restart to register a module" is an accepted Phase 1 property (§1.2).

### 8.2 Family-level activation flow

1. Admin requests activation (Level 0, UI-driven — agents only navigate).
2. Supervisor verifies: requester role = `admin`; all `data_dependencies` already active for the family (Vault before Finance, per Master Context §5.2); module status = `registered`.
3. Insert into `family_module_activations`; append `MODULE_ACTIVATED` audit event.
4. Deactivation mirrors this with the semantics in §5.2 (stops dispatch, keeps data, pauses queued tasks). Deactivating a module that others depend on requires deactivating the dependents first — the Supervisor refuses otherwise (`MOD_DEPENDENCY_ACTIVE`).

### 8.3 Version upgrades

- **Patch/minor** (no schema or entity breaking change): deploy, boot re-registers, done.
- **Major** (breaking change to owned schema or `entities_schema`): Alembic migration ships in the same release; the Registry refuses to load a module whose recorded major version is lower than the DB row's unless a migration marker confirms the migration ran (prevents new code on old schema).
- **Envelope changes:** additive fields are allowed within `envelope_version: "1.0"` (modules must ignore unknown fields — enforced by a CI contract test). Any field removal or semantic change bumps `envelope_version`, and the Supervisor refuses to dispatch to modules declaring an incompatible version. Given the monolith, in practice all modules upgrade in lockstep; the versioning discipline exists to keep the Phase 2 extraction path honest.

---

## 9. Error Taxonomy

All module errors use `error: { code, class, retry_after_ms, message_key, detail }`. `class` ∈ `RETRYABLE` | `TERMINAL`. `message_key` is an i18n key for the UX error library (P1 doc); `detail` is operator-facing and never shown to users.

| Code | Class | Raised by | Supervisor handling |
|---|---|---|---|
| `MOD_TIMEOUT` | RETRYABLE | Supervisor (deadline) or module (proactive) | Retry per §6.5; counts toward breaker |
| `MOD_UNAVAILABLE` | RETRYABLE | Registry (excluded/disabled/breaker OPEN) | No retry now; graceful degradation script; user told feature is temporarily down |
| `MOD_NOT_ACTIVATED` | TERMINAL | Runtime check §7.3(3) | Offer Admin the activation flow |
| `MOD_INVALID_INTENT` | TERMINAL | Runtime check §7.3(1) | FAILED; forensic log (Supervisor bug — routing table and NLU disagree) |
| `MOD_PERMISSION_DENIED` | TERMINAL | Runtime check §7.3(4) | BLOCKED state; audit `ROLE_VIOLATION` per PRD §Trust framework |
| `MOD_CONSENT_MISSING` | TERMINAL | Check §7.3(6) or DPI Gateway | Route user into Consent Manager grant flow, then allow re-initiation (new session) |
| `MOD_CONSENT_REVOKED` | TERMINAL | CONSENT_REVERIFY or Gateway | → FAILED ("Revoked Mid-Flow", FSM diagram); never retried |
| `MOD_CONSENT_STALE` | TERMINAL | Module defense-in-depth (§6.2) | FAILED + CRITICAL forensic log (indicates Supervisor sequencing bug) |
| `MOD_DPI_RATE_LIMITED` | RETRYABLE | DPI Gateway | Honor `retry_after_ms` from Runbook budget accounting; if past `deadline_at`, queue to `offline_task_queue` |
| `MOD_DPI_DOWN` | RETRYABLE | DPI Gateway (provider breaker OPEN) | Degraded-mode script per Master Context §4.7 |
| `MOD_STALE_DATA` | TERMINAL | Module (TTL hard-stop) | Block mutating action ("balance is stale") per FSM spec §3.2; reads degrade to warning instead |
| `MOD_LOCK_CONFLICT` | TERMINAL | Resource lock unique index | "A payment is already in progress." No retry |
| `MOD_EXECUTION_UNCONFIRMED` | TERMINAL* | Module (external call state unknown) | *Not user-retryable.* The Supervisor does **not** move the session to FAILED (v1.1): it leaves it in EXECUTION, keeps the resource lock, and shows the honest message ("payment status being confirmed"). The Healer's zombie sweep (FTS §6.4) finds sessions in EXECUTION older than 5 minutes and resolves them; a FAILED transition would hide the session from that sweep and strand the lock. The `side_effects` entry (`executed_unconfirmed`) is the forensic record. |
| `MOD_CALLGRAPH_VIOLATION` | TERMINAL | SDK runtime (§7.1) | FAILED + CRITICAL forensic log (module bug) |
| `MOD_DEPENDENCY_ACTIVE` | TERMINAL | Activation flow (§8.2) | Explain dependency chain to Admin |
| `MOD_INTERNAL` | TERMINAL | Module (unhandled exception, caught by SDK wrapper) | FAILED; alert; never expose stack traces to users |

Two rules that override everything above:

1. **A mutating intent is never blind-retried.** Retry only with the same idempotency key, only on RETRYABLE errors, only before `deadline_at`, and only when `side_effects` prove nothing external committed (`not_executed`). Anything ambiguous is the Healer's job, not the retry loop's.
2. **Errors fail closed.** An unrecognized error code, a malformed error object, or a response that fails envelope validation is treated as `MOD_INTERNAL` (TERMINAL) — never as a success, never as retryable.

---

## 10. Worked Example — `PAY_BILL` End to End

Ramesh (role: `member`, Hindi locale): *"BESCOM ka bill bhar do"* — ₹500 electricity bill.

```
 1. IDLE → INTENT_ANALYSIS
    Parsed: PAY_BILL {biller_id: BESCOM..., amount_paise: null}, conf 0.92.
    Mutating intent → idempotency_key generated, persisted to
    supervisor_sessions BEFORE anything else.

 2. Amount is unknown, but this does NOT trigger AWAITING_CLARIFICATION:
    PAY_BILL's entities_schema deliberately allows amount_paise: null —
    fetching the due amount from BBPS is the module's job, not the
    user's. Dispatch proceeds.

 3. PERMISSION_CHECK: member ∈ allowed_roles ✓, finance active for
    family ✓, tier 1 ≤ ceiling 1 ✓, active AA consent ✓ (BBPS is not
    a consent provider), core.resource_lock row for
    'BBPS_BESCOM_KA_001' inserted ✓.

 4. REASONING dispatch (read phase): FinanceAgent fetches bill via
    DPI Gateway (bbps declared ✓, budget ok ✓). Response:
    status=success, result.data={due_paise: 50000, bill_ref: ...},
    cache_metadata={fetched_at: now, expires_at: +24h}.

 5. SYNTHESIS → tier 1 → APPROVAL_GATE: biometric prompt
    ("BESCOM ₹500 — approve?"). expires_at = NOW()+5min per
    supervisor_sessions rules. Approved.

 6. CONSENT_REVERIFY: consent c-2222 still active (checked against
    Consent Manager, not cache). reverified_at stamped.

 7. EXECUTION dispatch: ModuleRequest as in §6.2, deadline_at = +30s.
    FinanceAgent, in ONE DB transaction:
      - INSERT finance.idempotency_ledger(key, pending)
      - INSERT finance.transactions(state='INITIATED')
      - prev = core.fn_lock_audit_tail(family_id); hash computed in code;
        core.fn_append_audit(..., 'BILL_PAYMENT_INITIATED', ..., prev, hash)
    COMMIT, then calls DPI Gateway → BBPS.

 8a. BBPS confirms → transaction state CONFIRMED + audit
     BILL_PAYMENT_EXECUTED (same-transaction, two-phase commit per
     Financial Safety spec). Response: status=success,
     side_effects=[{state: executed_confirmed}]. Ledger updated with
     final envelope. → SUCCESS_CONFIRMATION. Notification Engine
     (declared service dependency) sends Hindi push via display_key.

 8b. BBPS times out after payment may have left → module CANNOT claim
     failure or success. Response: status=failure,
     error={code: MOD_EXECUTION_UNCONFIRMED, class: TERMINAL},
     side_effects=[{state: executed_unconfirmed, external_ref: ...}].
     Supervisor leaves the session in EXECUTION (v1.1), keeps the lock,
     honest user message. Healer polls BBPS status API within 5 minutes
     and repairs (confirm or refund), then releases the lock.

 9. Duplicate safety: network flake causes the Supervisor to re-dispatch
    step 7 with the same idempotency_key → FinanceAgent finds the ledger
    row → returns stored envelope verbatim. No second UPI call. Ever.
```

---

## 11. Observability Hooks

Every dispatch emits one structured log line (JSON) at completion:

```json
{ "evt": "module_dispatch", "trace_id": "...", "request_id": "...",
  "module_id": "finance", "intent": "PAY_BILL", "family_id": "...",
  "actor_role": "member", "tier": 1, "status": "success",
  "error_code": null, "handler_ms": 212, "dpi_ms": 1840,
  "total_ms": 2101, "retry_attempt": 0, "breaker_state": "CLOSED" }
```

Metrics (Prometheus naming):

- `module_dispatch_total{module_id, intent, status, error_code}`
- `module_dispatch_duration_ms{module_id, intent}` histogram — alert when P95 > manifest `p95_handler_ms` for 15 min
- `module_breaker_state{module_id}` gauge (0=CLOSED, 1=HALF_OPEN, 2=OPEN) — page on OPEN for any Phase 1 module
- `module_zombie_side_effects_total{module_id}` — any `executed_unconfirmed` increments; sustained rate feeds the Healer dashboards defined in the Financial Safety spec

Forensic events (`MODULE_MANIFEST_DRIFT`, `MOD_CALLGRAPH_VIOLATION`, `MOD_CONSENT_STALE`, duplicate-intent registration failures) are written to the append-only audit log with `automation_tier: system`, satisfying the 7-year retention requirement (NFR v2.1).

---

## 12. Open Issues & Q&A

### Open Issues

| ID | Issue | Priority | Resolution path |
|---|---|---|---|
| OI-1 | No PostgreSQL row-level security inside module schemas; family_id scoping is app-layer per Data Model §9.3 convention. | LOW | Acceptable for Phase 1 single-deployable. Revisit with Phase 2 sharding design (Tech_Spec_Scalability_Architecture.md). |
| OI-2 | ~~`v_module_permissions` view definition had no DDL anywhere.~~ | CLOSED (v1.1) | Data Model v1.3 §3.16 (`role_module_permissions`) and §3.17 (all four kernel views, with grants). |
| OI-3 | Service Module capability calls have no per-capability rate budget (e.g., Bhashini's 1000 ASR calls/day is enforced at the DPI Gateway, but nothing stops a buggy module from burning the budget). | MEDIUM | Per-module DPI quota sub-allocation — extend Runbook_DPI_Rate_Limits at v1.2 when a second Bhashini consumer exists. |
| OI-4 | Manifest `display_name` translations are static; Bhashini-generated names need a review flow. | LOW | Module PRD concern (P1). |
| OI-5 | Import-linter contract does not cover dynamic imports (`importlib`). | LOW | Add a grep-based CI check for `importlib` inside `modules/`; treat any hit as review-required. |

### Q&A

| Asked by | Question | Answer |
|---|---|---|
| Engineering | Why not gRPC between agents — Master Context mentions evaluating protocols? | gRPC buys typed contracts and streaming across a network boundary we deliberately don't have in Phase 1. The typed-contract benefit is captured by JSON Schema validation of the envelope in CI; the cost (protobuf toolchain, another codegen step for a solo founder) buys nothing until extraction actually happens. The envelope maps 1:1 onto gRPC messages if Phase 2 chooses it. |
| Engineering | Why not Docker-per-module for isolation — the tracker checklist listed "Docker/Process/DB-level" as options? | Container isolation protects against untrusted code. All Phase 1 modules are first-party code from one author; the realistic threat is *bugs*, not malice, and bugs are contained by the DB-role layer (blast radius) and the call-graph layer (contract). Containers would add a network boundary — reintroducing the zombie-state surface — to defend against a threat we don't have yet. The manifest carries enough metadata (entrypoint, budgets, dependencies) to containerize any module later without spec changes. Third-party marketplace modules (Vision Parking Lot) WILL require container isolation + manifest signing; that is the trigger, and it is explicitly out of scope (§1.2). |
| Engineering | Why can't a module handle two intents with the same code at different tiers (e.g., PAY_BILL at tier 1 and tier 2)? | The tier is a property of the *dispatch*, not the route. `PAY_RECURRING` (ceiling 2) and `PAY_BILL` (ceiling 1) are different intents because they have different consent pre-authorization semantics. One code → one module → one ceiling keeps `intent_routes` a pure function, which is what makes PERMISSION_CHECK auditable. |
| Product | What happens to a family's data if a module is deactivated for months and its schema migrates in the meantime? | Alembic migrations run at deploy time against the schema regardless of activation status — activation gates dispatch, not migrations. Reactivation therefore always meets a current schema. |
| Security | The Supervisor is in-process with modules — can't a malicious module just call kernel functions directly? | In-process Python cannot stop truly adversarial first-party code; that is why third-party code is out of scope. The layers here make violations *loud* (CI-failing imports, runtime callgraph exceptions, DB permission denials, forensic logs) rather than *impossible*. Impossible requires process isolation — priced into the marketplace trigger, not Phase 1. |
| Product | Does the Registry support A/B-ing two versions of a module? | No. One version per module_id per deployment. Feature flags inside a module are a module concern; parallel versions are a Phase 3 problem. |

---

## 13. Review Log

### Round 1 — Claude Code, 2026-09-17 (applied in v1.1)

| # | Finding | Severity | Resolution |
|---|---|---|---|
| R1-1 | §9 sent `MOD_EXECUTION_UNCONFIRMED` sessions to FAILED, but the Healer (FTS §6.4) only sweeps sessions in EXECUTION. An unconfirmed payment would have become invisible to recovery and its lock stranded. | Critical | Session stays in EXECUTION with the lock held; Healer resolves. §6.3, §9, §10 updated. |
| R1-2 | `requires_consent_providers` listed bbps and bhashini, and the PAY_BILL example required a "bbps consent". No such consent handle exists in the Data Model or the Consent Manager; the gate would never have passed. | Critical | Enum narrowed to aa, abha, digilocker, ondc. PAY_BILL and PAY_RECURRING require ["aa"] (balance check). Data Model v1.3 adds ONDC to consent_handles.provider so ONDC_ADDRESS_SHARE can be gated. |
| R1-3 | PAY_BILL example set `biometric_required_above_paise: 200000`, contradicting FTS §2.2 gate G4 (biometric for every BBPS payment). | High | Example set to 0; description clarifies 0 = always. |
| R1-4 | §7.2 granted EXECUTE on `core.fn_append_audit(...)`, a function no document defined. Defining it naively in PL/pgSQL would have moved hashing into the database, contradicting Data Model §3.6 (hash in application code, canonical JSON) and making auditor verification impossible because jsonb key order differs from `sort_keys`. | High | Two-function protocol in Data Model v1.3 §3.18: lock the chain head, compute the hash in code, append with head re-check. §7.2 and §10 updated. |
| R1-5 | §7.3 step 7 cited a partial unique index on `supervisor_sessions.resource_lock`; FTS assumed a separate table. | Medium | Data Model v1.3 §3.11 makes it a table; step 7 updated. |
| R1-6 | Registry DDL (§5) and the kernel views (§7.2, OI-2) had no single source. | Medium | Data Model v1.3 §3.14–3.17 is the source; §5 says so; OI-2 closed. |
| R1-7 | Cross-reference table pointed at document versions that no longer exist; back-annotation requests to Master Context and NFR were open. | Low | Table updated; annotations made in Master Context v2.1 and NFR v2.2. |

Round 1 did not change the envelope contract (§6.2–6.4), the tier model (§3) or the isolation layers (§7) beyond the items above. Round 2 (Codex) should focus on: the boot sequence under partial failure (§8.1 steps 5–7), whether `deadline_at` + retries can exceed the NFR 2.0 s end-to-end budget for read intents, and the `consent[].reverified_at` 60-second rule against the FSM's AWAITING_APPROVAL window.

**END OF DOCUMENT**

*Phase 1 Build Gate: this is P0 document 5 of 5. On freeze (after review round 2), the Build Gate closes and simulator-suite work begins.*
