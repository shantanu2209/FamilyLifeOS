# Tech Spec: Module Registry & Agent Communication Contract

> **Status:** v1.2 — REVISION IN REVIEW (Codex round-2 findings applied; freezes after Codex's targeted re-review), Phase 1 · **Author:** Shantanu Chaudhary (Lead Product Architect) · **Last content change:** 2026-09-21

**Purpose:** To define the contract that makes any FamilyLifeOS module implementable: the module manifest schema, the Supervisor→Worker dispatch envelope, the Core vs. Service tier rules, and the isolation model. This document is the last Priority 0 specification of the Phase 1 Build Gate.

## 0. Document Governance

| **Version** | **Date** | **Description of Change** | **Author** |
|---|---|---|---|
| v1.0 | 2026-07-03 | Initial specification: manifest schema, dispatch envelope v1.0, tier rules, isolation model, registration flow, error taxonomy. | Shantanu Chaudhary |
| v1.1 | 2026-09-17 | Review round 1 (see §13). Seven fixes: (1) `MOD_EXECUTION_UNCONFIRMED` no longer moves the session to FAILED — it stays in EXECUTION so the Healer's zombie sweep (FTS §6.4) can find it (§6.3, §9, §10); (2) `requires_consent_providers` narrowed to real consent providers (aa, abha, digilocker, ondc); BBPS and Bhashini are DPI providers, not consent providers (§4.1, §4.2, §10); (3) PAY_BILL example sets `biometric_required_above_paise: 0` — every BBPS bill payment needs biometric approval (FTS §2.2 G4); (4) audit writes go through the two-function protocol `fn_lock_audit_tail` / `fn_append_audit` with the hash computed in application code (Data Model v1.3 §3.18) instead of an undefined single function (§7.2, §10); (5) resource lock is the `core.resource_lock` table (Data Model v1.3 §3.11) (§7.3); (6) registry DDL and the four kernel views now have a single source in Data Model v1.3 §3.14–3.17; OI-2 closed; (7) cross-references updated to the current document versions; Master Context and NFR back-annotations recorded. | Shantanu Chaudhary (with Claude Code) |
| v1.2 | 2026-09-21 | Review round 2 by Codex (issue #9, 12 findings; see §13) plus the module-side consequences of its PRD reviews. (1) The kernel owns Phase 1 and Phase 2 of a payment; modules never write the payment audit rows or the session (§6.3, §6.7, §10). (2) `phase: prepare \| execute` in the envelope; only `execute` can end a mutating session (§6.2, §6.3). (3) After the EXECUTION commit, a missing, invalid or late response keeps the session in EXECUTION for the Healer (§6.5, §9). (4) Idempotency ledger has states `pending` and `final`, a row lock for concurrent duplicates, and a kernel-authorised same-key resubmission (§6.4). (5) Consent is resolved per intent by exact purpose and subject: new manifest field `requires_consent_purposes`; the envelope carries consent record references (§4.1, §6.2, §7.3). (6) Boot failures propagate to dependents at every stage and routes are published only for the final ready set (§8.1). (7) Semantic manifest validation, `envelope_versions`, identifier lengths (§4.1, §4.3). (8) `needs_data` response status; voice/Bhashini path is kernel-orchestrated (§3.2, §6.3). (9) Module breaker counts only availability failures (§6.5). (10) Family settings and scheduled jobs: bounded SDK contracts, new manifest field `scheduled_jobs` (§6.6). (11) Read-path latency budget under one deadline (§6.5). (12) `USAGE` on schema core; five kernel views (§7.2). Also: kernel-called module hooks `reconcile`, `purge_user`, `on_role_changed` (§6.7); `MOD_DOMAIN_REJECTED` with a registered `domain_code` for business refusals (§9). | Shantanu Chaudhary (with Claude Code; review by Codex) |

**Cross-references (authoritative, do not duplicate):**

| Document | What this spec defers to it |
|---|---|
| Master_Context v2.1 | Module list (Eight Pillars), phase prioritization, communication protocol baseline (§3.4, now annotated for the Phase 1 monolith), DPI risk profiles |
| Data Model v1.4 | Core tables incl. `resource_lock` (§3.11), registry tables (§3.14–3.15), role permissions and kernel views (§3.16–3.17), audit write functions (§3.18), action codes (§6), module table convention (§9.3) |
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
| **Service** | Shared System Services | `notification_engine`, `translation` (text post-processing: glossary, transliteration, i18n key rendering; **not** a Bhashini client, v1.2), `ocr`, `payment_routing` (per PRD §5) | Stateless utilities. Register **capabilities**, not intents. Invoked by the Kernel or by Core Modules. Never dispatched user intents, never call other modules. |

### 3.2 The permitted call graph (deny-by-default)

```
User → Supervisor (Kernel)
Supervisor → Core Module            [intent dispatch, §6]        ALLOWED
Supervisor → Service Module         [capability call]            ALLOWED
Core Module → Service Module        [capability call]            ALLOWED
Core Module → DPI Gateway (Kernel)  [provider call]              ALLOWED
Supervisor → DPI Gateway (Kernel)   [kernel-internal, v1.2]      ALLOWED (voice: Bhashini ASR/NMT/TTS)
Core Module → Core Module                                        FORBIDDEN
Service Module → anything                                        FORBIDDEN (leaf nodes)
Any Module → Kernel internals (FSM, Consent DB, Audit table)     FORBIDDEN (see §7)
```

**Why Core→Core is forbidden:** cross-domain reasoning is exactly what the Conflict Resolution Engine exists for (Master Context §3.2). If FinanceAgent could query HealthAgent directly, budget/health conflicts would be resolved ad hoc inside whichever module called first, invisibly to the Supervisor. Instead, when a Core Module needs another domain's data, it returns `status: "conflict"` or `status: "needs_data"` in its response (§6.4) and the Supervisor orchestrates the second dispatch. The Module Dependency Graph in Master Context §5.2 (Vault→Finance, Health→Elder Care) describes **data and activation-order dependencies**, not permission to call.

**Voice and translation (v1.2).** v1.1 called `translation` a "Bhashini wrapper", which the graph above forbids: a Service Module may call nothing, and the only path to a DPI is the Gateway. The compliant path: the **Supervisor** calls Bhashini through the DPI Gateway (budget, breaker and the first-party purpose VOICE_INTENT_PROCESSING are checked there like any other provider call), and hands the returned text to the `translation` service only for leaf work that needs no network (glossary substitution, rendering a `display_key` with parameters). The logged call-graph decision stands; no Service → Gateway edge is added.

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
  "required": ["manifest_version", "module_id", "version", "tier", "envelope_versions",
               "display_name", "entrypoint", "health_check"],
  "properties": {
    "manifest_version": { "const": 1 },
    "module_id": {
      "type": "string",
      "pattern": "^[a-z][a-z0-9_]{2,30}$",
      "description": "Stable snake_case identifier, 3 to 31 characters (v1.2: it is also the PostgreSQL schema and role name, and fits module_registry.module_id VARCHAR(40)). Never changes across versions."
    },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+$",
      "description": "Semver. Major bump required for any breaking change to owned schema or intent entities."
    },
    "tier": { "enum": ["core", "service"] },
    "envelope_versions": {
      "type": "array", "minItems": 1, "items": { "enum": ["1.0"] },
      "description": "v1.2. Envelope versions this module can receive and produce (§8.3). Required; boot rejects a module that does not list the running kernel's version."
    },
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
            "pattern": "^[A-Z][A-Z0-9_]{2,39}$",
            "description": "Globally unique across all modules, 3 to 40 characters (intent_routes.intent_code VARCHAR(40)). Duplicate = registration failure."
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
          "requires_consent_purposes": {
            "type": "array",
            "items": {
              "type": "object", "additionalProperties": false,
              "required": ["purpose_code", "subject"],
              "properties": {
                "purpose_code": { "type": "string", "description": "A code in the Consent Manager purpose registry (CM §3.2). Unknown code = manifest rejected." },
                "subject": { "enum": ["actor", "acting_as_or_actor", "entity"], "description": "Whose consent: the authenticated actor; the managed profile when acting_as is set, else the actor; or the user named by entities[subject_entity]." },
                "subject_entity": { "type": "string", "description": "Required when subject = entity, e.g. 'holder_user_id'." },
                "when": { "enum": ["dispatch", "external_call"], "default": "dispatch", "description": "dispatch = must be active before any dispatch. external_call = checked by the Gateway only if the module makes that call (e.g. a read served from the module's own tables)." }
              }
            },
            "description": "v1.2. THE authorisation input (§7.3 step 6). 'An active handle with this provider' is not consent for this purpose: a handle for AA_TRANSACTION_HISTORY must not satisfy a balance check. First-party purposes with no provider (VOICE_INTENT_PROCESSING, HEALTH_MEDICATION_REMINDERS) are listed here too. requires_consent_providers must equal the set of providers of these purposes (semantic validation, §4.3)."
          },
          "biometric_required_above_paise": {
            "type": ["integer", "null"], "minimum": 0, "maximum": 200000,
            "description": "v1.2: bounded by the schema. Overrides only downward. System floor is ₹2,000 (200000 paise) per NFR §2.2; a module may require biometrics at a lower threshold, never a higher one. 0 means always. Every BBPS bill payment is 0 (FTS §2.2 gate G4). (v1.1)"
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
          "description": "PostgreSQL schema this module owns (core tier). Must equal module_id; must be null for service tier. Both rules are enforced by semantic validation (§4.3), not by this description."
        },
        "core_read_views": {
          "type": "array",
          "items": { "enum": ["v_family_members", "v_module_permissions",
                               "v_active_consents", "v_device_surfaces", "v_guardians"] },
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
    "scheduled_jobs": {
      "type": "array",
      "description": "v1.2, core tier only (§6.6). Work the kernel scheduler triggers on the module's behalf.",
      "items": {
        "type": "object", "additionalProperties": false,
        "required": ["job_code", "handler", "every_seconds", "scope"],
        "properties": {
          "job_code": { "type": "string", "pattern": "^[a-z][a-z0-9_]{2,39}$" },
          "handler": { "type": "string", "description": "Method name on the entrypoint class." },
          "every_seconds": { "type": "integer", "minimum": 60, "maximum": 86400 },
          "scope": { "const": "family", "description": "The kernel calls the handler once per family for which the module is active; there are no cross-family jobs." },
          "max_run_ms": { "type": "integer", "maximum": 30000, "default": 10000 }
        }
      }
    },
    "domain_errors": {
      "type": "array",
      "description": "v1.2 (§9). Business refusal codes this module may put in error.domain_code.",
      "items": {
        "type": "object", "additionalProperties": false, "required": ["domain_code", "message_key"],
        "properties": {
          "domain_code": { "type": "string", "pattern": "^[A-Z]{3,10}_[0-9]{3}$" },
          "message_key": { "type": "string" }
        }
      }
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
        },
        "read_budget_ms": {
          "type": "integer", "maximum": 1500, "default": 1500,
          "description": "v1.2. Budget for a non-mutating dispatch, DPI time included, so that the 2-second end-to-end read target (NFR §1) holds (§6.5)."
        }
      }
    }
  },
  "allOf": [
    {
      "if": { "properties": { "tier": { "const": "core" } } },
      "then": { "required": ["intents", "data_scopes"],
                "properties": { "data_scopes": { "required": ["owns_schema", "core_read_views"] } } }
    },
    {
      "if": { "properties": { "tier": { "const": "service" } } },
      "then": {
        "required": ["capabilities"],
        "properties": {
          "intents": { "maxItems": 0 },
          "scheduled_jobs": { "maxItems": 0 },
          "data_dependencies": { "maxItems": 0 }
        }
      }
    }
  ]
}
```

**Validation posture: fail-closed.** A manifest that fails schema validation means the module is not loaded — it is excluded from the dispatch table and its intents resolve to `MOD_UNAVAILABLE`. If the invalid module has `deactivatable: false`, the application refuses to boot entirely. This is the same principle as BBPS Redis fail-closed: a system that cannot prove its configuration is safe does not get to run.

### 4.3 Semantic validation (v1.2)

JSON Schema cannot express rules that compare two fields or look outside the file. The Registry runs these after schema validation, with the same fail-closed posture; each has a counterexample manifest in the test suite that must be rejected:

| # | Rule | Rejected example |
|---|---|---|
| S1 | core tier: `data_scopes.owns_schema == module_id`; service tier: `owns_schema` is null or absent | finance manifest with `owns_schema: "health"`; `data_scopes: {}` on a core module |
| S2 | every `purpose_code` in `requires_consent_purposes` exists in the purpose registry; `requires_consent_providers` equals the providers of those purposes; every such provider is in `dpi_providers` | purpose `AA_BALANCE_FETCH` with providers `[]` |
| S3 | a `mutating` intent whose module lists `bbps` in `dpi_providers` and whose entities can carry an amount has `biometric_required_above_paise == 0` (FTS §2.2 G4) | PAY_BILL with threshold 100000 |
| S4 | `automation_tier_ceiling` ≤ 2 (schema) and ≤ 1 for any intent that can reach BBPS outside a pre-authorised mandate | — |
| S5 | `envelope_versions` contains the kernel's envelope version | module built for "2.0" only |
| S6 | `subject = entity` names a `subject_entity` that exists in `entities_schema.properties` | — |
| S7 | every `scheduled_jobs[].handler` and the `health_check` exist on the entrypoint class (checked at LOAD, §8.1 step 6) | typo in handler name |
| S8 | every `core_read_views` entry is in the whitelist; every `service_dependencies` / `data_dependencies` id is a discovered module of the right tier | dependency on a module that is not on disk |

### 4.2 Example manifest — FinanceAgent (excerpt)

```json
{
  "manifest_version": 1,
  "module_id": "finance",
  "version": "1.0.0",
  "tier": "core",
  "envelope_versions": ["1.0"],
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
      "requires_consent_purposes": [ { "purpose_code": "AA_BALANCE_FETCH", "subject": "actor" } ],
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
      "requires_consent_providers": ["aa"],
      "requires_consent_purposes": [ { "purpose_code": "AA_BALANCE_FETCH", "subject": "actor" } ]
    },
    {
      "intent_code": "PAY_RECURRING",
      "description": "Execute a pre-authorized recurring payment within safe limits.",
      "automation_tier_ceiling": 2,
      "allowed_roles": ["admin", "member"],
      "mutating": true,
      "requires_consent_providers": ["aa"],
      "requires_consent_purposes": [ { "purpose_code": "AA_BALANCE_FETCH", "subject": "actor" } ],
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
  "phase": "execute",
  "recovery": null,
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
    { "consent_record_id": "r-2222-...-uuid", "purpose_code": "AA_BALANCE_FETCH",
      "subject_user_id": "u-1111-...-uuid", "provider": "aa", "consent_id": "c-2222-...-uuid",
      "reverified_at": "2026-07-03T10:41:57+05:30" }
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
| `phase` (v1.2) | `prepare` or `execute`. **Read intents** are always `execute`. A **mutating** intent is dispatched as `prepare` any number of times during REASONING (fetch the bill, force the live balance check of FTS gate G3, compute what will be shown for approval) and as `execute` exactly once per attempt, only after every gate has passed and the kernel's Phase 1 COMMIT has put the session in EXECUTION. In `prepare` the module MUST NOT call any mutating provider operation, MUST NOT touch the idempotency ledger, and its `success` means "ready for approval", never "done" (§6.3). The DPI Gateway refuses a mutating provider operation (BBPS payment, ONDC confirm) from a dispatch whose phase is not `execute`. |
| `recovery` (v1.2) | Null except on a Healer-ordered same-key resubmission: `{"mode": "resubmit", "reason": "provider_not_found"}`. Only the kernel sets it, only after the provider's status API answered NOT_FOUND inside the provider's idempotency window (FTS §6.4). It is what permits a module to call the provider again for a ledger row that is `pending` (§6.4). |
| `session_id` | FK to `supervisor_sessions`. Lets the module correlate with the resource lock the Supervisor holds. Modules never write to this table. |
| `actor.acting_as` | Non-null when a proxy acts for a managed profile: `{"managed_user_id": "...", "proxy_assignment_id": "..."}`. The Supervisor has already validated the proxy assignment; the module records `PROXY_ACTION` semantics in its audit events. |
| `intent.automation_tier` | The tier this dispatch runs at. Supervisor guarantees `tier ≤ manifest ceiling` and that Level ≥1 approval gates already passed. Modules MUST NOT re-prompt the user. |
| `consent[]` (v1.2) | One entry per `requires_consent_purposes` item that applied, resolved by the kernel for the **exact purpose and subject** (§7.3 step 6). References only: `consent_record_id` always; `consent_id` (the handle's UUID, never the external handle) and `provider` when the purpose has a DPI handle, else null. v1.1's example showed `provider: "bbps"`; BBPS is not a consent provider. |
| `consent[].reverified_at` | Stamped **after** approval, immediately before the `execute` dispatch; a stamp taken before the biometric prompt is never reused. Set by the Supervisor's CONSENT_REVERIFY state immediately before EXECUTION dispatch. Modules treat a mutating dispatch with any `reverified_at` older than 60 seconds as a contract violation → `MOD_CONSENT_STALE` (terminal). Defense in depth against Supervisor bugs. |
| `context.is_public_surface` | When true (kitchen tablet), modules MUST NOT include financial figures or health details in any response destined for display (PRD Scenario 9). |
| `deadline_at` | Mutating `execute`: now + intent timeout (default 30,000ms per Master Context §3.4, or manifest `hard_timeout_ms` if lower). Reads and `prepare`: now + `read_budget_ms` (§6.5). One deadline per user request, preserved across retries. Modules check it before starting any DPI call and return `MOD_TIMEOUT` proactively if already exceeded. |

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
| `success` | `phase: execute` → intent completed. `phase: prepare` → ready for approval; `result.data.prepared` holds what the approval screen shows. | `execute`: the kernel runs Phase 2 (§6.7), then → SUCCESS_CONFIRMATION. `prepare`: stays in REASONING and continues to the gates; **never** SUCCESS_CONFIRMATION |
| `failure` | See `error` object (§9). | RETRYABLE → retry per §6.5; TERMINAL → FAILED, except `MOD_EXECUTION_UNCONFIRMED`, which keeps the session in EXECUTION for the Healer (§9, v1.1) |
| `needs_clarification` | Module cannot proceed without more info; `clarification.missing_entities` lists what. | → AWAITING_CLARIFICATION (state persists if user closes app, per FSM spec) |
| `needs_data` (v1.2) | The module needs another domain's data that only the Supervisor may fetch (§3.2). `needs_data.requests` lists `{intent_code, entities, reason_key}`; each must be a **read** intent. Allowed in `prepare` and in read intents, never in `execute`. | Supervisor checks RBAC/consent for each request as for any dispatch, runs them, and re-dispatches the original with `context.supplied_data`; at most 2 rounds, then FAILED with `MOD_INTERNAL` |
| `conflict` | Module detected a cross-domain constraint it is not allowed to resolve (§3.2). `conflict` carries a Conflict Object. | → Conflict Resolution Engine within REASONING |

Field rules:

| Field | Rule |
|---|---|
| `result.display_key` | i18n message key, not prose. The Kernel's Translation service renders it in the user's Bhashini locale. Modules never hardcode user-facing strings. |
| `side_effects` | **Mandatory and exhaustive for mutating intents.** Every external call that may have committed money or state must appear, with `state` ∈ `executed_confirmed` \| `executed_unconfirmed` \| `not_executed`. Any `executed_unconfirmed` entry is what the Healer (Financial Transaction Safety spec) polls and repairs. A mutating response with an empty `side_effects` array asserts "I touched nothing external" — and the module is accountable to that assertion in forensic review. |
| `audit_events` | Kernel-persisted supplementary events only. **Payment outcomes do NOT go here, and since v1.2 the module does not write them either:** `BILL_PAYMENT_INITIATED`, `_EXECUTED`, `_FAILED` and the Healer codes are written by the **kernel**, in the Phase 1 and Phase 2 transactions that also move the session (FTS §4.2–4.3; §6.7 below). v1.1 had the module write the payment audit row next to its own state change and return before the session moved; FTS requires audit row and session update in one transaction, and a crash between the two left an audited, successful payment sitting in EXECUTION for the Healer to audit a second time. A module still writes, through `AuditClient` inside its own transaction, the audit rows for its **own** registered codes (Data Model v1.4 §6.1: settings changes, document links, medication events). |
| `cache_metadata` | Required for read intents that serve cached DPI data: `{fetched_at, source_api, expires_at}` per the TTL policy (FSM spec §3). The Supervisor uses it for stale-data warnings and hard stops. |
| `result.data` content references (v1.2) | The envelope is JSON; document bytes, PDFs and streams never travel in it. A module that wants the client to see content returns `result.data.content_ref` = `{provider, document_id, consent_record_id}`; the kernel's content endpoint resolves it through the DPI Gateway, re-checks RBAC, public surface and consent for the requesting device, and streams to the PWA. The module never holds the bytes. |
| `metrics.handler_ms` | Module-side wall time excluding DPI wait. Compared against manifest `p95_handler_ms` in observability dashboards. |

### 6.4 Idempotency behavior (module side)

Applies to `phase: execute` of mutating intents only. v1.2 replaces "seen key → return the stored envelope": that rule could not say what is stored while the outcome is unknown, so a crash between persisting the key and calling the provider left a row with nothing to return, and the Healer's same-key resubmission (FTS §6.4) had no way in.

```sql
-- in the module's own schema, e.g. finance.idempotency_ledger
idempotency_key   UUID PRIMARY KEY,
family_id         UUID NOT NULL,
state             VARCHAR(10) NOT NULL CHECK (state IN ('pending','final')),
response_envelope JSONB,                       -- NULL while pending; set exactly once
external_ref      VARCHAR(100),                -- provider reference as soon as one is known
created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
finalised_at      TIMESTAMPTZ,
CHECK ((state = 'final') = (response_envelope IS NOT NULL))
```

| On `execute` with key K | The module does |
|---|---|
| K unseen | Transaction A: INSERT ledger (K, `pending`) + business row `INITIATED`; COMMIT. **Then** the provider call with K. Then transaction B: business row → outcome, ledger → `final` with the response envelope; COMMIT. Return the envelope. |
| K is `final` | Return the stored envelope, with `request_id` replaced by the current request's and `replayed: true` added. This includes stored terminal failures: a terminal failure is a result. No provider call. |
| K is `pending`, `recovery` is null | The outcome is unknown and this dispatch has no authority to find out. Return `failure` / `MOD_EXECUTION_UNCONFIRMED` with `side_effects: [{state: "executed_unconfirmed"}]`. No provider call. (A Supervisor retry after a lost response lands here.) |
| K is `pending`, `recovery.mode == "resubmit"` | The kernel has established NOT_FOUND at the provider. Call the provider **with K** (the provider's own idempotency makes this safe even if its status API was lagging), then transaction B as above. |
| Two dispatches with K at once | Every path above starts with `SELECT … FROM ledger WHERE idempotency_key = K FOR UPDATE` inside its first transaction (or the INSERT, whose unique violation sends the loser to that SELECT). The loser waits, then sees the winner's state. |

Rules:

1. **Never store an unconfirmed outcome as `final`.** A timeout leaves the row `pending`. Only a provider answer (success or definite failure), or `reconcile()` (§6.7), finalises it.
2. `final` is written once. A second attempt to finalise with a different outcome raises and alerts; it is never silently overwritten.
3. Never garbage-collect ledger rows younger than 7 days (covers the BBPS 48-hour async-settlement window with margin; full retention policy per Financial Transaction Safety spec); never collect a `pending` row at all.

### 6.5 Timeouts, retries, circuit breakers (Supervisor side)

| Mechanism | Setting | Source |
|---|---|---|
| Hard timeout | 30s per dispatch (or manifest value if lower), enforced via `deadline_at` + `asyncio.wait_for` | Master Context §3.4 |
| Retries | Max 3 attempts, backoff 1s → 2s → 4s **with full jitter** (`sleep = random(0, base)`) | Master Context §3.4 + project jitter principle |
| Retry eligibility | Only `error.class == "RETRYABLE"`; mutating intents retried **only** with the identical `idempotency_key`; never retry after `deadline_at` | This spec |
| Module circuit breaker | 5 consecutive **availability failures** → module `OPEN` for 30 minutes. v1.2: an availability failure is `MOD_TIMEOUT`, `MOD_INTERNAL`, a response that fails envelope validation, or a failed health probe. **Not counted, and they do not reset the count either:** `MOD_DPI_RATE_LIMITED` (HTTP 429 never counts as a failure at any layer, NFR §3, Runbook §4.4), `MOD_DPI_DOWN` (the provider's breaker handles it), every consent, permission, activation, lock, stale-data and `MOD_DOMAIN_REJECTED` refusal (a module that says "no" correctly is healthy). Any `success`, `needs_clarification`, `needs_data` or `conflict` resets the count. Half-open: after 30 minutes one **read** intent is let through; success closes the breaker, an availability failure re-opens it for another 30 minutes. Mutating intents are never the probe. | Master Context §3.4 |
| Read-path budget (v1.2) | A non-mutating dispatch (reads and `prepare`) gets `deadline_at = now + read_budget_ms` (default and ceiling 1,500 ms), **DPI time included**, leaving 500 ms of the NFR §1 2-second P95 target for NLU, RBAC and rendering. Retries share that one deadline; in practice a read gets one attempt plus at most one retry. When the budget runs out the module (or the Supervisor on its behalf) answers from cache with `cache_metadata` and a staleness note if the TTL policy allows it, else `MOD_TIMEOUT` with the degradation script. `p95_handler_ms` excludes DPI wait and is not the end-to-end guarantee. The 30-second ceiling applies to `execute` of mutating intents only. | NFR §1 |
| DPI provider circuit breaker | Separate layer, owned by the DPI Gateway | Runbook_DPI_Rate_Limits v1.1 |

**Note on the 3-vs-5 discrepancy:** NFR v2.1 states "DPI circuit breakers: 3 failures → 30min"; Master Context §3.4 states 5 failures for module disablement. These are **different breakers at different layers** and both stand: the DPI Gateway trips at 3 consecutive provider failures (protecting rate budgets and the provider relationship), the module breaker trips at 5 (a module can fail for non-DPI reasons). Annotated in NFR v2.2 §3 and PRD Core v2.2 §4.6 on 2026-09-17.

**After the EXECUTION commit, no response means "unknown", never "failed" (v1.2).** Once the kernel's Phase 1 COMMIT has put a session in EXECUTION and the `execute` dispatch has started, the SDK wrapper treats every outcome that is not a valid envelope as *outcome unknown*: an unhandled exception in the module, a cancelled task, `deadline_at` passing, a response that fails envelope validation, a `failure` whose `side_effects` do not prove `not_executed` for every external call. In all of these the session **stays in EXECUTION**, the resource lock stays held, the user sees "payment status being confirmed", and the Healer resolves it (FTS §6.4). The original error is kept for operators in `session_notes` (code only) and in the structured log (detail). `MOD_INTERNAL` → FAILED applies only when the wrapper can prove the module never reached its provider call: the module raised before transaction A of §6.4 committed (no ledger row for the key), which the wrapper checks through the module's `ledger_state(idempotency_key)` SDK method; if that check itself fails, the answer is again *unknown*.

**Breaker-open behavior:** dispatch to an OPEN module returns `MOD_UNAVAILABLE` immediately and the Supervisor invokes the graceful-degradation script for that domain (Master Context §4.7) — e.g., Finance OPEN → queue payment intents to `offline_task_queue`, notify user via WhatsApp on recovery.

### 6.6 Family settings and scheduled work (v1.2)

The three Phase 1 PRDs all need per-family settings and two of them need timers. Both get a small, bounded contract; neither gets a framework.

**Settings.** Each module that has settings owns a typed table `<module_id>.family_settings` (Data Model v1.4 §9.3: one row per family, one column per setting with a CHECK for its bounds, `settings_version`). No row = shipped defaults. There is no kernel settings service and no key-value table.

- Every setting is declared in the module's PRD with: default, bounds, who may change it, and whether a change **loosens** or **tightens**. A change is a mutating intent of the module (`SET_<MODULE>_SETTING` family), so RBAC, the envelope and the ledger apply as to any other mutation.
- The write is one transaction in the module's schema: `UPDATE … SET <col> = $new, settings_version = settings_version + 1 WHERE family_id = $1 AND settings_version = $expected` (0 rows → re-read and refuse with `MOD_DOMAIN_REJECTED`, so two admins cannot interleave a read-modify-write), plus the `<MODULE>_SETTINGS_CHANGED` audit row through `AuditClient` with the typed payload of Data Model v1.4 §6.1.
- **A setting never weakens a safety gate.** Payment gates G1–G5, consent rules, the public-surface block and audit logging are not settings (AGENTS §6, "Defaults, not constants"). A setting may only make them stricter. Semantic validation cannot see this; the PRD review does, and the invariant tests pin it.
- A validation that spans kernel data (Health's missed-dose window versus `proxy_assignments.notify_timeout_mins`) is run by the module against the kernel views at write time **and** re-checked when it reads the setting, because the kernel value can change later without the module being told.

**Scheduled work.** Modules declare `scheduled_jobs` in the manifest; the **kernel scheduler** owns the clock.

- For each job and each family where the module is registered, not breaker-OPEN, and **active** (§5.2), the scheduler calls `handler(JobRequest{job_code, family_id, run_id, scheduled_for, deadline_at})`. A deactivated module's jobs do not run.
- At most one run of a job per family at a time: the scheduler takes a Redis lock `{env}:job:{module_id}:{job_code}:{family_id}` with TTL = `max_run_ms` + margin. Handlers must still be idempotent per `(job_code, family_id, scheduled_for)`: a crash after the work and before the lock release means the same slot may be offered again.
- A timer is not a permission. Inside a job the module has the same database role and the same SDK clients as in a dispatch: any provider call goes through the DPI Gateway, which checks purpose-bound consent for the **subject** of the work (there is no actor), budget and breaker. Notifications go through `notification_engine` with recipients the module resolved from the kernel views at run time, never from a list cached at schedule time. No consent, or no entitled recipient, means the job skips that item and records why.
- Audit rows written from a job use `SYSTEM_ACTOR_UUID` as the actor.
- The Healer and the consent watchdog are kernel jobs and are not declared this way.

### 6.7 Kernel-called module hooks (v1.2)

Three moments where the kernel must reach into a module's data without being given access to its tables. Each is an SDK method on `ModuleProtocol`, called in-process with a JSON-serialisable request, idempotent, and a no-op by default.

| Hook | Called by, when | Contract |
|---|---|---|
| `reconcile(ReconcileRequest{idempotency_key, session_id, family_id, outcome, external_ref, occurred_at})` with `outcome` ∈ `executed` \| `failed` \| `not_executed` | The **Healer**, after the provider's status API gave a definite answer for a zombie session (FTS §6.4), and **before** the kernel's Phase 2 transaction | In one module transaction: business row → the outcome **and** ledger row → `final` with a synthesised envelope. Already final with the same outcome → no-op, return ok. Already final with a different outcome → raise (alert; the Healer leaves the session in EXECUTION for an admin). `not_executed` finalises only when the Healer has decided **not** to resubmit (outside the provider's idempotency window); when it resubmits it sends an `execute` dispatch with `recovery` instead (§6.4) |
| `purge_user(family_id, user_id)` | The nightly purge (Data Model v1.4 §7.1 step 2), inside that user's purge | Delete or anonymise every row in the module's schema that is about this person. Must leave nothing that names them |
| `on_role_changed(family_id, user_id, old_role, new_role, old_is_child, new_is_child)` | The kernel's role-change service, **after** its own transaction commits; retried by the Healer from `offline_task_queue` (task type `MODULE_HOOK`) until it returns ok | Re-apply role-dependent defaults (Vault PRD §4.6). Because delivery is at-least-once and may lag, a module must not let stored role-dependent values grant access meanwhile: authorisation is computed from the **live** kernel views at read time, the stored value is only a preference |

**Who writes what in a payment (the v1.2 answer to "who owns Phase 2").**

| Step | Kernel (one transaction each) | Module |
|---|---|---|
| Phase 1 | session → `EXECUTION` with the idempotency key; audit `BILL_PAYMENT_INITIATED` | — |
| execute dispatch | — | transaction A (ledger `pending`, business row `INITIATED`) → provider call → transaction B (business outcome, ledger `final`) → return envelope |
| Phase 2 | audit `BILL_PAYMENT_EXECUTED` or `_FAILED` **and** session → `SUCCESS_CONFIRMATION` or `FAILED`, then release the lock | — |
| Crash anywhere after Phase 1 | Healer: provider status → `reconcile()` → Phase 2. Every step is idempotent, so a crash between them repeats harmlessly | `reconcile()` as above |

The module's transaction B and the kernel's Phase 2 are two transactions on purpose: they run under different database roles. What makes the pair safe is order and idempotency, not atomicity: B first, Phase 2 second, and the session leaves EXECUTION only in Phase 2, so any gap is a zombie the Healer closes. The payment is audited exactly once because only the kernel writes those codes.

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

-- v1.2: USAGE (never CREATE) on core. Without it every grant below fails with
-- "permission denied for schema core" on the deny-by-default database this spec asks for.
GRANT USAGE ON SCHEMA core TO role_module_finance;

-- Whitelisted kernel views only (read-only, minimal columns); the manifest's core_read_views decides which:
GRANT SELECT ON core.v_family_members,
                core.v_module_permissions,
                core.v_active_consents
  TO role_module_finance;

-- Audit is append-only via the two SECURITY DEFINER functions of the audit write protocol
-- (Data Model v1.3 §3.18); no table access. The hash is computed in application code between
-- the two calls, inside one transaction, so auditors can verify it without database access:
GRANT EXECUTE ON FUNCTION core.fn_lock_audit_tail(UUID) TO role_module_finance;
GRANT EXECUTE ON FUNCTION core.fn_append_audit(UUID,UUID,UUID,VARCHAR,JSONB,VARCHAR,VARCHAR,VARCHAR,TIMESTAMPTZ)
  TO role_module_finance;
-- The functions are schema-qualified, pin search_path and run as a no-login owner (Data Model v1.4 §3.18).

-- Everything else is invisible. No grant on core tables, no grant on
-- other module schemas, no CREATEROLE, no SUPERUSER. Deny-by-default.
```

Consequences worth stating explicitly:

- A SQL injection or logic bug inside FinanceAgent **cannot** read `health.*`, `core.consent_handles` (raw handles), or `core.audit_log` history, and cannot UPDATE or DELETE audit rows (append-only preserved by the SECURITY DEFINER function, mirroring the tamper-proof audit requirement).
- Provisioning test (v1.2, runs in CI against PostgreSQL 15 as `role_module_finance`): SELECT on each granted view succeeds; both audit functions execute; SELECT on `core.users`, `core.consent_handles`, `core.audit_log`, `core.audit_chain_heads` and on `health.*` fails with permission denied; CREATE in `core` fails; a temp table named `audit_log` does not capture an audit write.
- A row in a kernel view is a candidate reference, never an authorisation (Data Model v1.4 §3.17).
- The kernel views expose exactly what the module table convention (Data Model §9.3) assumes modules need: family membership, per-role module permissions, active consent **references** (`consent_id`, `provider`, `status`, `expires_at` — never token material). Their DDL is Data Model v1.4 §3.17; v1.2 adds `v_guardians` to the whitelist.
- Module tables follow Data Model §9.3 conventions verbatim, including its v1.4 exception for family-level tables such as `family_settings` (family_id, user_id, created_at, updated_at, deleted_at, `(family_id, created_at DESC)` index). Migrations are Alembic, one migration branch per module schema (Data Model §9.2).
- Row-level security within a module's own schema is **not** used in Phase 1 (single-tenant-per-query access patterns, app-layer family_id scoping per convention). Revisit at Phase 2 sharding. Logged as Open Issue OI-1.

### 7.3 Layer 3 — Runtime: dispatch-time enforcement (Supervisor)

Before any dispatch, the Supervisor validates, in order — each check deny-by-default:

1. Intent exists in `intent_routes` → else `MOD_INVALID_INTENT`.
2. Module registered, not `disabled`, breaker not OPEN → else `MOD_UNAVAILABLE`.
3. Module active for this family (§5.2) → else `MOD_NOT_ACTIVATED`.
4. Actor role ∈ manifest `allowed_roles`, cross-checked against `v_module_permissions` → else BLOCKED at PERMISSION_CHECK (never reaches the module).
5. `automation_tier ≤ tier_ceiling`; Level 3 structurally impossible (schema caps at 2).
6. **Purpose-bound consent (v1.2).** For each `requires_consent_purposes` entry with `when: dispatch`: resolve the **subject** (actor; or the managed profile in `acting_as`, which the Supervisor has verified against `proxy_assignments`; or the user named by `subject_entity`, who must be a live member of the same family), then require an active, unexpired `consent_records` row for exactly that `(subject, purpose_code)` with `proxy_reconfirm_required = FALSE`, and, where the purpose has a DPI handle, an active unexpired handle → else `MOD_CONSENT_MISSING`. The resolved references go into `consent[]`. A handle for a different purpose with the same provider does not count. This check reads the tables, not `v_active_consents`. It is a pre-check: CONSENT_REVERIFY (CM §5.2) repeats it live, for the same purpose and subject, immediately before any `execute` dispatch, and the Gateway repeats it per call for `when: external_call` entries.
7. Mutating intent: `idempotency_key` present and persisted to `supervisor_sessions`; resource lock acquired by INSERT into `core.resource_lock` (partial unique index, Data Model v1.3 §3.11; released only after the Phase 2 COMMIT) → else `MOD_LOCK_CONFLICT` ("A payment is already in progress").
8. `entities` validate against `entities_schema` → else AWAITING_CLARIFICATION.

The DPI Gateway repeats its own checks at call time (provider declared in manifest; the operation's registered purpose has an active consent record for the subject and, where applicable, an active handle; mutating operations only in `phase: execute`; rate budget available) — the module sits between two enforcement layers and is trusted with neither tokens nor budget accounting.

---

## 8. Registration & Discovery Flow

### 8.1 Boot sequence (static registration)

v1.2 makes one rule apply at every step instead of at two: **a module that fails any step is excluded, exclusion propagates to everything that depends on it, and if the excluded set ever contains a non-deactivatable module the boot aborts.** Routes are written once, at the end, for the modules that survived everything.

```
1. DISCOVER   Scan modules/*/manifest.json.
2. VALIDATE   JSON Schema (§4.1) + semantic validation (§4.3, except S7).      Fail → EXCLUDE.
3. HASH       SHA-256 of canonical manifest bytes vs. module_registry row.
              Drift without version bump → CRITICAL log + audit
              MODULE_MANIFEST_DRIFT; a module with mutating intents → EXCLUDE.
4. RESOLVE    Build the graph over service_dependencies + data_dependencies
              of the modules still standing.
              Dependency id not discovered, or already excluded → EXCLUDE the dependent.
              Cycle → ABORT BOOT (a cycle is a design error, not a runtime
              condition to survive).
5. LOAD       Import entrypoints in topological order; instantiate with the
              module's own DB pool + scoped SDK clients; check S7.
              ImportError, constructor error, missing handler → EXCLUDE.
6. PROBE      Call each module's health_check (2s budget).  Unhealthy → EXCLUDE.
7. PROPAGATE  Repeat until nothing changes: any module with a service or data
              dependency in the excluded set → EXCLUDE. (Steps 2–6 call this
              after each exclusion too; this pass catches late failures.)
              Excluded set contains a module with deactivatable=false → ABORT BOOT,
              naming the root cause and the chain.
8. REGISTER   One DB transaction: upsert module_registry for the READY set
              (excluded modules present in the table → status='disabled'),
              DELETE all intent_routes, INSERT routes for the READY set only.
              Duplicate intent_code among READY modules → the transaction
              aborts → EXCLUDE both owners, PROPAGATE, and retry REGISTER
              once with the smaller set.
9. READY      Dispatch table live, built from the same READY set. Admins are
              told which modules were excluded and why. The Supervisor
              reconciles interrupted sessions from the PostgreSQL journal
              (FSM spec §1.3) only now, since recovery may re-dispatch.
```

Because routes are replaced wholesale in step 8, a route left over from an earlier boot can never make an excluded module dispatchable; §7.3 step 2 also checks `status` and the in-memory READY set on every dispatch. Required boot tests: missing dependency; dependency excluded by a late PROBE failure; ImportError in a module others depend on; duplicate intent between two modules; manifest drift on a non-deactivatable module (must abort); each leaves no route for any excluded module.

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

All module errors use `error: { code, class, retry_after_ms, message_key, detail, domain_code }`. `code` is always one of the `MOD_*` codes below; `domain_code` (v1.2, optional) is a business code the module registered in its manifest `domain_errors` (`FIN_009`, `VAULT_006`, `HEALTH_004`), used for the user-facing message and for metrics, never for control flow in the Supervisor. `class` ∈ `RETRYABLE` | `TERMINAL`. `message_key` is an i18n key for the UX error library (P1 doc); `detail` is operator-facing and never shown to users.

| Code | Class | Raised by | Supervisor handling |
|---|---|---|---|
| `MOD_TIMEOUT` | RETRYABLE | Supervisor (deadline) or module (proactive) | Retry per §6.5; counts toward breaker |
| `MOD_UNAVAILABLE` | RETRYABLE | Registry (excluded/disabled/breaker OPEN) | No retry now; graceful degradation script; user told feature is temporarily down |
| `MOD_NOT_ACTIVATED` | TERMINAL | Runtime check §7.3(3) | Offer Admin the activation flow |
| `MOD_INVALID_INTENT` | TERMINAL | Runtime check §7.3(1) | FAILED; forensic log (Supervisor bug — routing table and NLU disagree) |
| `MOD_PERMISSION_DENIED` | TERMINAL | Runtime check §7.3(4) | The request never reaches the module. Persisted as session `FAILED` with `session_notes = 'MOD_PERMISSION_DENIED'` ("BLOCKED" is a word for this outcome, not a stored state: Data Model v1.4 §3.7); kernel audit `ROLE_VIOLATION` per PRD §Trust framework |
| `MOD_DOMAIN_REJECTED` (v1.2) | TERMINAL | Module (a business rule said no: hidden or absent document, limit exceeded, invalid setting) | FAILED, user sees the `message_key` of the registered `domain_code`. **Not** a role violation and no admin alert; does not count toward the breaker; never retried. A module that must not reveal *why* (Vault: hidden versus absent) returns the same `domain_code`, `message_key` and timing for both |
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
| `MOD_INTERNAL` | TERMINAL | Module (unhandled exception, caught by SDK wrapper) | FAILED; alert; never expose stack traces to users. **Exception (v1.2):** in an `execute` dispatch after the kernel's Phase 1 COMMIT the session is not moved to FAILED unless non-execution is proven (§6.5); it stays in EXECUTION for the Healer |

Two rules that override everything above:

1. **A mutating intent is never blind-retried.** Retry only with the same idempotency key, only on RETRYABLE errors, only before `deadline_at`, and only when `side_effects` prove nothing external committed (`not_executed`). Anything ambiguous is the Healer's job, not the retry loop's.
2. **Errors fail closed.** An unrecognized error code, a malformed error object, an unregistered `domain_code`, or a response that fails envelope validation is treated as `MOD_INTERNAL` (TERMINAL) — never as a success, never as retryable.
3. **Unknown is not failed (v1.2).** Rule 2 decides how an error is *classified*; §6.5 decides what happens to a *session that may already have paid*. Once Phase 1 has committed, only proof of non-execution, a definite provider answer, or the Healer moves the session out of EXECUTION.

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

 3. PERMISSION_CHECK (FTS gate G1): member ∈ allowed_roles ✓, finance
    active for family ✓, tier 1 ≤ ceiling 1 ✓, active consent record for
    purpose AA_BALANCE_FETCH, subject = Ramesh ✓ (exact purpose, §7.3
    step 6; BBPS is not a consent provider).
    Gate G2: core.resource_lock row for 'BBPS_BESCOM00000KA01' inserted ✓;
    supervisor_sessions.resource_key set to the same value.

 4. REASONING, dispatch phase=prepare: FinanceAgent fetches the bill via
    the DPI Gateway (bbps declared ✓, budget ok ✓) and performs gate G3,
    the FORCED live AA balance fetch (no cache, FTS §2.2). No ledger row,
    no mutating provider call: the Gateway would refuse one in this phase.
    Response: status=success, result.data.prepared={due_paise: 50000,
    bill_ref: ..., funds_sufficient: true, balance_checked_at: now}.
    "success" here means ready for approval; the session stays in
    REASONING.

 5. SYNTHESIS → tier 1 → gate G4: biometric prompt
    ("BESCOM ₹500 — approve?"). expires_at = NOW()+5min per
    supervisor_sessions rules. Approved.

 6. Gate G5, CONSENT_REVERIFY: the AA_BALANCE_FETCH record of Ramesh is
    read live (Consent Manager §5.2, never a cache or a view).
    reverified_at stamped now, after approval.

 7. KERNEL Phase 1, one transaction: session → EXECUTION with the
    idempotency key; audit BILL_PAYMENT_INITIATED via
    fn_lock_audit_tail / fn_append_audit. COMMIT.
    Then dispatch phase=execute, deadline_at = +30s. FinanceAgent:
      transaction A: INSERT finance.idempotency_ledger(key, 'pending'),
                     INSERT finance.transactions(state='INITIATED'); COMMIT
      DPI Gateway → BBPS payment with the key
      transaction B: transactions → CONFIRMED, ledger → 'final' with the
                     envelope; COMMIT

 8a. BBPS confirmed → response status=success,
     side_effects=[{state: executed_confirmed, external_ref: ...}].
     KERNEL Phase 2, one transaction: audit BILL_PAYMENT_EXECUTED +
     session → SUCCESS_CONFIRMATION. COMMIT, then the lock is released
     (UPDATE released_at). Notification Engine sends the Hindi push via
     display_key. The module wrote no payment audit row.

 8b. BBPS times out after the payment may have left → the module cannot
     claim failure or success. Ledger stays 'pending'. Response:
     status=failure, error={code: MOD_EXECUTION_UNCONFIRMED, class:
     TERMINAL}, side_effects=[{state: executed_unconfirmed}].
     The session stays in EXECUTION, the lock stays held, honest user
     message. Within 5 minutes the Healer asks BBPS:
       SUCCESS   → finance.reconcile(outcome=executed) → kernel Phase 2.
       FAILED    → finance.reconcile(outcome=failed) → audit
                   BILL_PAYMENT_ZOMBIE_FAILED + session FAILED, lock released.
       NOT_FOUND → within 24 h: dispatch phase=execute with the SAME key and
                   recovery={mode: resubmit}; the ledger row is 'pending', so
                   the module calls BBPS again with that key (§6.4).

 8c. The module crashes, returns garbage, or the deadline passes during
     step 7 → identical to 8b from the Supervisor's side: unknown, not
     failed (§6.5). The error is kept for operators.

 9. Duplicate safety: a network flake makes the Supervisor re-dispatch
    step 7 with the same key. Ledger 'final' → stored envelope returned
    (replayed: true). Ledger 'pending' → MOD_EXECUTION_UNCONFIRMED, no
    provider call; the Healer decides. No second UPI call. Ever.
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

### Round 2 — Codex, 2026-09-21 (applied in v1.2)

Verdict on issue #9: changes required, 12 findings, all accepted. Where each went:

| Finding | Subject | Applied in |
|---|---|---|
| 1 (P1) | Phase 2 had two owners | §6.3 `audit_events` rule, §6.7 ownership table, §10; FTS v1.3 §4.6 |
| 2 (P1) | Preparation and payment were the same dispatch; G3 missing from the example | §6.2 `phase`, §6.3 `success` row, §10 steps 4–7 |
| 3 (P1) | Invalid response after execution hid an unknown payment | §6.5 "unknown is not failed", §9 rule 3, §10 step 8c |
| 4 (P1) | Pending ledger key had no recovery path | §6.4 states and table, `recovery`, §6.7 `reconcile` |
| 5 (P1) | Provider presence is not consent | §4.1 `requires_consent_purposes`, §6.2 `consent[]`, §7.3 step 6; bbps example corrected |
| 6 (P1) | Boot failures did not propagate | §8.1 |
| 7 (P2) | Manifest rules that were only descriptions | §4.1 bounds and `envelope_versions`, §4.3 |
| 8 (P2) | `needs_data` missing; translation could not reach Bhashini | §6.3, §3.1–3.2 |
| 9 (P2) | Breaker counted refusals | §6.5 |
| 10 (P2) | Settings and scheduled work | §6.6, manifest `scheduled_jobs`; Data Model v1.4 §9.3 |
| 11 (P2) | Deadline did not budget the read SLO | §6.5 read-path budget, `read_budget_ms` |
| 12 (P2) | No USAGE on schema core | §7.2; Data Model v1.4 §3.17 |

From Codex's PRD reviews the same day: role-change delivery and live authorisation (PR #22 finding 5) → §6.7 `on_role_changed`; denial logging (PR #22 finding 6) stays a kernel audit row, `ROLE_VIOLATION`, because the module is never dispatched; business errors through envelope validation (PR #22 finding 7) → `MOD_DOMAIN_REJECTED` + `domain_code`; content transport (PR #22 dependency note) → §6.3 content references; ledger completion in `reconcile` (PR #25 finding 7) → §6.7. Open-issue dispositions from the verdict are unchanged: OI-1 stays accepted, OI-3 and OI-4 stay deferred, OI-5 stays a CI guardrail.

**END OF DOCUMENT**

*Phase 1 Build Gate: this is P0 document 5 of 5. On freeze (after Codex's re-review of v1.2), the Build Gate closes and simulator-suite work begins.*
