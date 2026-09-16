# Runbook: DPI Rate Limits

_Rate limits, Redis budget tracker, circuit breakers and on-call response for AA, BBPS, ABHA, ONDC and Bhashini_

> **Status:** FROZEN — v1.2 (v1.1 thresholds unchanged; two clarifications) · **Author:** Alfred (Lead Product Architect) · **Last content change:** 2026-09-17
> **Canonical copy.** Converted to Markdown on 2026-09-16 from `Runbook_DPI_Rate_Limits_v1.1.docx` (original kept in `archive/originals/`). Content is unchanged; only formatting was converted. Superseded versions in the archive: `Runbook_DPI_Rate_Limits_v1.0.docx`.
> **Cited elsewhere as:** Runbook_DPI_Rate_Limits v1.1, RB §n.

### Document Governance

| Version | Date | Description | Author |
|---|---|---|---|
| v1.0 | 2026-02-21 | Initial release. Rate limit reference table for all five DPIs. Redis budget tracker design. Per-DPI circuit breaker state machines with exact thresholds. Request coalescing algorithm. Backpressure handling. Degraded-mode UX copy. WireMock simulator config. Monitoring thresholds and alert runbook. | Alfred |
| v1.1 | 2026-02-21 | Hardening — six fixes after first independent review: (1) §2.2 AA hourly TTL changed from fixed 3600s to seconds_until_next_hour_ist() — prevents floating rate window when first increment is near the hour boundary; (2) §2.4 BBPS Redis-failure behaviour changed to fail-closed — financial execution must not proceed without rate limit tracking; (3) §2.1 environment prefix added to all Redis keys ({env}: prefix) — prevents staging chaos tests from corrupting production circuit breaker state; (4) §3.2 AA coalescing timeout now emits log.warning + metrics counter — essential for forensic debugging of AA budget exhaustion; (5) §7.3 Bhashini low-confidence ASR now writes audit_log VOICE_ASR_LOW_CONFIDENCE — enables forensic trace of looping voice retries burning org budget; (6) §6.2 ONDC seller blacklist progressive expiry (1h first, 24h on 3rd offence in 24h). Plus: (7) §4.4 jitter added to exponential backoff — prevents thundering-herd on HALF_OPEN probe; (8) §7.2 per-family automatic soft-throttle at 10% of org Bhashini budget — stops single runaway consumer without manual intervention. | Alfred |
| v1.2 | 2026-09-17 | Clarifications, no threshold changes: (1) §3.1 states that the Redis hourly bucket is the AA enforcement point and `consent_handles.fetch_count_today` is bookkeeping for renewal inheritance and audit (Inconsistency Register item 11; Data Model v1.3 Q6 and §7.3 agree); (2) §10.3 on-call query fixed to use `audit_log.timestamp` (the column is not `created_at`) and the action codes VOICE_INTENT_PROCESSED / VOICE_ASR_LOW_CONFIDENCE are now in the Data Model v1.3 §6 taxonomy (item 7). | Alfred (with Claude Code) |

> ✅ STATUS: HARDENED v1.1 — Architecture Frozen
> This runbook is the authoritative source for DPI rate limit handling in FamilyLifeOS.
> v1.1 passed two independent reviews. Eight hardening fixes applied across six issues:
>   (1) AA hourly TTL drift fixed (seconds_until_next_hour_ist)  (2) BBPS Redis-failure fail-closed
>   (3) Environment prefix on all Redis keys  (4) Coalescing timeout observability
>   (5) Bhashini low-confidence audit event  (6) ONDC progressive seller blacklist
>   (7) Jitter on exponential backoff  (8) Per-family Bhashini auto soft-throttle
> Dependencies: consent_handles.fetch_count_today and last_fetched_at (Data_Model_Schema v1.2.1),
> consent records rate-limit inheritance on renewal (Consent_Manager v1.1 §7.3),
> circuit breaker state referenced in NFR v2.1 §3.

## Table of Contents

- **1. Rate Limit Master Reference** — All five DPIs in one table • Limit type • Window • Source • Enforcement point
- **2. Redis Budget Tracker Design** — Key schema • Atomic increment pattern • Window reset • Org-level vs user-level keys
- **3. Account Aggregator (AA) — Detailed Spec** — 3 fetches/hour enforced • Coalescing algorithm • Stale-data handling • Backpressure UX
- **4. BBPS — Detailed Spec** — 50 tx/day enforced • Circuit breaker (3 failures → 30 min) • Backoff sequence • Zombie interaction
- **5. ABHA — Detailed Spec** — 10 consent grants/day • 85% uptime reality • FHIR parse failures • Degraded-mode fallback
- **6. ONDC — Detailed Spec** — 100 searches/day soft limit • Seller quality variance • Circuit breaker for catalog failures
- **7. Bhashini — Detailed Spec** — 1000 ASR calls/day org-wide • Confidence thresholding • Dialect failure fallback • Budget allocation
- **8. Cross-DPI Circuit Breaker State Machine** — CLOSED / OPEN / HALF-OPEN states • Transition thresholds • Per-DPI config table
- **9. WireMock Simulator Configuration** — Rate limit responses • Circuit breaker simulation • Chaos mode • Contract compliance tests
- **10. Monitoring, Alerts, and On-Call Runbook** — Prometheus metrics • Alert thresholds • Step-by-step on-call response per DPI
- **11. Q&A** — Engineering questions on edge cases and implementation choices

## 1. Rate Limit Master Reference

All rate limits are as of February 2026. DPI providers update their limits without public notice — verify against the relevant sandbox portal before each major release.

| DPI | Limit | Window | Scope | Hard or Soft | Source | Our Enforcement Point |
|---|---|---|---|---|---|---|
| AA (Sahamati) | 3 FI fetches | Per hour | Per user / per consent handle | Hard | RBI / Sahamati FIU agreement | consent_handles.fetch_count_today + Redis hourly bucket |
| BBPS | 50 transactions | Per day | Per user | Hard | NPCI BBPS operating guidelines | Redis daily bucket per user_id |
| ABHA (ABDM) | 10 consent grants | Per day | Per user | Hard | ABDM HIU policy | Redis daily bucket per user_id |
| ONDC | 100 searches | Per day | Per user | Soft | ONDC network policy (unenforced) | Redis daily bucket — advisory, not blocking |
| Bhashini | 1000 ASR calls | Per day | Per organisation (all users combined) | Hard | Bhashini API subscription tier | Redis org-level daily bucket |

> ℹ INFO: Hard limits enforced by the DPI provider result in HTTP 429 responses that block operations for the affected user or organisation. Soft limits (ONDC) are advisory — exceeding them degrades catalog accuracy but does not block API responses. Our enforcement is pre-emptive for hard limits (we refuse the call before making it) and monitoring-only for soft limits.

> ⚠ WARNING: AA's 3 fetch/hour limit is per consent handle, not per user account. A user with two AA consent handles (e.g., HDFC and ICICI separate consents) gets 3 fetches/hour for each handle independently. Track limits at the handle level (consent_handles.fetch_count_today), not at the user level.

## 2. Redis Budget Tracker Design

### 2.1 Key Schema

All rate limit state lives in Redis. The database (consent_handles.fetch_count_today) is the persistent record used for renewal inheritance (Consent Manager §7.3) and audit purposes. Redis is the enforcement layer — it is faster, avoids DB write overhead on every fetch, and resets automatically via TTL expiry.

```text
# Redis key schema for all DPI rate limits
# TTL on each key = time until the window resets (auto-expire = auto-reset)
#
# ── ENVIRONMENT PREFIX (Fix 3 — v1.1) ───────────────────────────────────
# ALL keys are prefixed with the deployment environment.
# Pattern: {env}:{key}  where env = 'prod' | 'staging' | 'dev'
# Set via environment variable: REDIS_ENV_PREFIX='prod'
# Without this prefix, a staging chaos test that opens the BBPS circuit
# breaker on a shared Redis instance will suppress production bill payments.
# This is not theoretical — it happens during late-night load tests.
#
# All key examples below show the {env}: prefix. In code:
#   key = f'{settings.REDIS_ENV_PREFIX}:dpi:aa:fetch:{handle_id}:{hour}'

# ── Account Aggregator ──────────────────────────────────────────────────
# Per consent handle, per hour (handle is the AA rate limit scope)
{env}:dpi:aa:fetch:{consent_handle_id}:{YYYY-MM-DD-HH}
  Type:  STRING (integer counter)
  TTL:   seconds_until_next_hour_ist() — see §2.2 Fix 1 note
  Max:   3
  Example key: prod:dpi:aa:fetch:ch-abc-123:2026-02-21-14
  Example val: '2'  (2 fetches used this hour, 1 remaining)

# ── BBPS ────────────────────────────────────────────────────────────────
# Per user, per calendar day (IST)
{env}:dpi:bbps:tx:{user_id}:{YYYY-MM-DD}
  Type:  STRING (integer counter)
  TTL:   Seconds until midnight IST (dynamic — see §2.3)
  Max:   50
  Example key: prod:dpi:bbps:tx:usr-xyz-789:2026-02-21
  Example val: '12'

# ── ABHA ────────────────────────────────────────────────────────────────
# Per user, per calendar day (consent grants only — not data fetches)
{env}:dpi:abha:consent:{user_id}:{YYYY-MM-DD}
  Type:  STRING (integer counter)
  TTL:   Seconds until midnight IST
  Max:   10

# ── ONDC ────────────────────────────────────────────────────────────────
# Per user, per calendar day (advisory — does not block)
{env}:dpi:ondc:search:{user_id}:{YYYY-MM-DD}
  Type:  STRING (integer counter)
  TTL:   Seconds until midnight IST
  Max:   100 (advisory threshold for monitoring alert only)

# ── Bhashini ────────────────────────────────────────────────────────────
# Org-level, per calendar day (ALL users share one budget)
{env}:dpi:bhashini:asr:{YYYY-MM-DD}
  Type:  STRING (integer counter)
  TTL:   Seconds until midnight IST
  Max:   1000

# ── Bhashini per-family soft-throttle (Fix 8 — v1.1) ───────────────────
# Per family_id, per calendar day (advisory — routes to text, does not hard-block)
{env}:dpi:bhashini:asr:family:{family_id}:{YYYY-MM-DD}
  Type:  STRING (integer counter)
  TTL:   Seconds until midnight IST
  Threshold: 100 (10% of org budget — triggers auto soft-throttle for that family)

# ── Circuit breaker state ───────────────────────────────────────────────
# Per DPI, no TTL (managed by circuit breaker logic — see §8)
{env}:dpi:cb:{provider}:state          → 'CLOSED' | 'OPEN' | 'HALF_OPEN'
{env}:dpi:cb:{provider}:failure_count  → integer (resets on CLOSED transition)
{env}:dpi:cb:{provider}:opened_at      → epoch timestamp (when OPEN state entered)
{env}:dpi:cb:{provider}:half_open_at   → epoch timestamp (when HALF_OPEN entered)
  Example: prod:dpi:cb:bbps:state = 'OPEN'
           prod:dpi:cb:bbps:opened_at = '1740143200'
  Staging: staging:dpi:cb:bbps:state = 'OPEN'  ← isolated, cannot affect prod
```

### 2.2 Atomic Increment Pattern

All budget checks and increments use a Lua script executed atomically. This prevents the TOCTOU race where two concurrent requests both read 'under budget' and both increment, overshooting the limit.

```python
-- Lua script: check_and_increment.lua
-- Executed via EVALSHA for atomic check + increment
-- KEYS[1] = Redis key (e.g., 'dpi:aa:fetch:ch-abc-123:2026-02-21-14')
-- ARGV[1] = max allowed value (e.g., '3')
-- ARGV[2] = TTL in seconds (e.g., '3600')
-- Returns: {current_count, allowed}
--   allowed = 1 → increment was applied, call permitted
--   allowed = 0 → limit already reached, call blocked

local current = redis.call('GET', KEYS[1])
local count = tonumber(current) or 0
local max   = tonumber(ARGV[1])

if count >= max then
  return {count, 0}  -- blocked
end

local new_count = redis.call('INCR', KEYS[1])
if new_count == 1 then
  -- First increment in this window — set TTL
  redis.call('EXPIRE', KEYS[1], tonumber(ARGV[2]))
end
return {new_count, 1}  -- allowed
```

```python
# Python call site (application layer)
def check_dpi_budget(redis_client, key, max_val, ttl_seconds):
    result = redis_client.evalsha(
        CHECK_AND_INCREMENT_SHA,  # pre-loaded script hash
        1,                         # num keys
        key,                       # KEYS[1]
        str(max_val),              # ARGV[1]
        str(ttl_seconds)           # ARGV[2]
    )
    count, allowed = result
    return bool(allowed), int(count)

# ── Fix 1 (v1.1): AA hourly TTL ─────────────────────────────────────────
# WRONG (v1.0): ttl_seconds=3600
#   A fetch at 14:59:50 sets TTL=3600 → key expires 15:59:50.
#   The rate window floats by up to 59m59s instead of resetting on the hour.
#   A user who hits their limit at 14:59 can fetch again at 15:00 (correct)
#   but also had access from 14:00 to 14:59 PLUS from 14:00 to 15:59 in overlap.
#
# CORRECT (v1.1): ttl_seconds=seconds_until_next_hour_ist()
#   Key expires precisely at the next hour boundary in IST.
#   A fetch at 14:59:50 sets TTL=10 seconds — key expires at 15:00:00.
#   Budget resets cleanly on the clock hour, matching Sahamati's expectation.

def seconds_until_next_hour_ist():
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.now(ist)
    next_hour = (now_ist + timedelta(hours=1)).replace(
        minute=0, second=0, microsecond=0
    )
    return max(1, int((next_hour - now_ist).total_seconds()))
    # max(1, ...) prevents zero or negative TTL at exact hour boundary

# Usage — AA fetch check (corrected call site):
hour_key = f'{REDIS_ENV_PREFIX}:dpi:aa:fetch:{consent_handle_id}:{now_ist.strftime("%Y-%m-%d-%H")}'
ttl      = seconds_until_next_hour_ist()
allowed, count = check_dpi_budget(redis, hour_key, max_val=3, ttl_seconds=ttl)
if not allowed:
    raise RateLimitError('AA_FETCH_LIMIT', retry_after_seconds=ttl_remaining(hour_key))
```

### 2.3 Window Reset: Calendar Day (IST)

BBPS, ABHA, ONDC, and Bhashini limits reset at midnight IST. The Redis TTL for daily keys must be set to the number of seconds remaining until midnight IST at the time of the first increment — not a fixed 86400 seconds. A fixed 86400 TTL set at 11:45 PM means the key expires at 11:45 PM the next day, allowing up to 48 hours of limit accumulation.

```python
# TTL calculation for daily-reset keys
import pytz
from datetime import datetime, timedelta

def seconds_until_midnight_ist():
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.now(ist)
    midnight_ist = (now_ist + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return int((midnight_ist - now_ist).total_seconds())

# Pass this value as ARGV[2] in check_and_increment.lua
# The key will auto-expire exactly at midnight IST.
ttl = seconds_until_midnight_ist()  # e.g., 3600 at 11pm, 86399 at 00:00:01
```

### 2.4 Redis Failure Handling

> ⚠ WARNING: If Redis is unavailable during a budget check, the safe default is to ALLOW the request and log a warning — do not block user operations due to Redis downtime. The DPI itself will return HTTP 429 if the limit is truly exceeded. EXCEPTION: BBPS must fail-closed (see below).

```python
# ── Default behaviour: fail-open (AA, ABHA, ONDC, Bhashini) ─────────────
def check_dpi_budget_safe(redis_client, key, max_val, ttl_seconds,
                           fail_closed=False):
    try:
        return check_dpi_budget(redis_client, key, max_val, ttl_seconds)
    except redis.RedisError as e:
        log.warning('Redis unavailable for budget check',
            key=key, error=str(e), fail_closed=fail_closed)
        metrics.increment('dpi.rate_limit.redis_miss',
            tags={'key_prefix': key.split(':')[2]})  # key[2] after env: prefix
        if fail_closed:
            # ── Fix 2 (v1.1): BBPS must fail-closed ──────────────────────
            # BBPS daily limit is hard (NPCI policy). If we cannot track
            # consumption, we cannot safely allow a financial transaction.
            # This is a different risk class from AA balance fetch:
            #   AA fail-open: worst case = user sees slightly stale balance.
            #   BBPS fail-open: worst case = silent policy breach + confusing
            #     429s from NPCI with no local audit trail.
            # The 'REDIS_UNAVAILABLE' abort reason surfaces in audit_log
            # so the on-call engineer sees it immediately (§10.3).
            return False, -1  # block=True, count unknown
        return True, -1  # allow=True, count unknown

# ── Call sites ───────────────────────────────────────────────────────────
# AA, ABHA, ONDC, Bhashini — fail-open (default)
allowed, count = check_dpi_budget_safe(redis, key, max_val, ttl)

# BBPS — fail-closed (financial execution gate)
allowed, count = check_dpi_budget_safe(redis, key, max_val, ttl, fail_closed=True)
if not allowed and count == -1:
    session.abort_reason = 'BBPS_RATE_LIMIT_TRACKING_UNAVAILABLE'
    notify_user('Payment system is temporarily unavailable. Please try again in a moment.')
    RAISE GateFailure('G3_REDIS_UNAVAILABLE')
```

## 3. Account Aggregator (AA) — Detailed Spec

### 3.1 Limit Summary

| Parameter | Value | Notes |
|---|---|---|
| Hard limit | 3 FI fetches per hour | Per consent handle. A user with 2 handles gets 3/hr each. |
| Uptime (Sahamati network) | 97% | FIP (individual bank) outages additional. HDFC/ICICI: 1-2h outages monthly. |
| Cache TTL (balance) | 15 minutes | Defined in FSM spec §3.1. Force-refresh on any 'Pay' intent. |
| Cache TTL (transactions) | 24 hours | Defined in FSM spec §3.1. Sufficient for dashboard display. |
| Redis key scope | Per consent_handle_id, per hour | Hourly bucket: dpi:aa:fetch:{handle_id}:{YYYY-MM-DD-HH} |
| On limit hit | Return cached data with staleness warning | Do not block the user. Display timestamp of last successful fetch. |
| DB sync field | consent_handles.fetch_count_today | Updated alongside Redis for persistence, renewal inheritance (CM §7.3) and audit. Not an enforcement point: the Redis hourly bucket above is (v1.2 clarification; Data Model v1.3 Q6). |

### 3.2 Request Coalescing Algorithm

When multiple users or sessions need a balance fetch for the same bank account within a short window, coalescing batches them into a single AA API call rather than burning through the 3/hour budget. This matters when a family has two Admins who both open the finance dashboard within seconds of each other.

```sql
COALESCING ALGORITHM — AA balance fetch

On incoming AA fetch request for (consent_handle_id, fi_type):

Step 1: Check cache
  cached = supervisor_sessions.get_cached_balance(user_id, consent_handle_id)
  IF cached AND NOT expired AND NOT force_refresh:
    RETURN cached  # No API call, no budget consumed

Step 2: Check for in-flight fetch (coalescing window)
  inflight_key = f'{REDIS_ENV_PREFIX}:dpi:aa:inflight:{consent_handle_id}:{fi_type}'
  IF redis.EXISTS(inflight_key):
    # Another session is already fetching this data.
    # Wait up to 10 seconds for it to complete.
    result = wait_for_key(
        f'{REDIS_ENV_PREFIX}:dpi:aa:result:{consent_handle_id}:{fi_type}',
        timeout=10
    )
    IF result:
        metrics.increment('dpi.aa.coalescing_hit')  # budget saved
        RETURN result  # Coalesced — no new API call
    # ── Fix 4 (v1.1): Coalescing timeout — explicit log + metric ─────────
    # Timeout means: the first fetch finished but wrote no result (failed)
    # OR the inflight key expired without the result key being written.
    # Either way, we fall through to a new fetch, burning a second budget slot.
    # Without this log, 'why did we use 3 AA slots in 4 minutes?' is
    # impossible to answer from audit_log alone.
    log.warning('AA coalescing timeout — issuing new fetch',
        consent_handle_id=consent_handle_id, fi_type=fi_type,
        waited_seconds=10)
    metrics.increment('dpi.aa.coalescing_timeout',
        tags={'consent_handle_id': consent_handle_id})

Step 3: Acquire inflight lock
  SET inflight_key '1' EX 15 NX  # 15s TTL, only if not exists
  IF SET failed: go back to Step 2 (race — another process just acquired it)

Step 4: Budget check
  hour_key = f'{REDIS_ENV_PREFIX}:dpi:aa:fetch:{consent_handle_id}:{now_hour_ist}'
  ttl      = seconds_until_next_hour_ist()  # Fix 1: not fixed 3600
  allowed, count = check_dpi_budget_safe(redis, hour_key, max=3, ttl=ttl)
  IF NOT allowed:
    DEL inflight_key  # Release lock
    remaining = redis.TTL(hour_key)
    RAISE RateLimitError(retry_after=remaining, message=BUDGET_EXHAUSTED_MESSAGE)

Step 5: Execute AA fetch
  data = POST /FI/request to Sahamati (consent_handle)
  UPDATE consent_handles SET fetch_count_today += 1, last_fetched_at = NOW()

Step 6: Publish result and release lock
  SET f'{REDIS_ENV_PREFIX}:dpi:aa:result:{consent_handle_id}:{fi_type}' data EX 15
  DEL inflight_key
  Cache result in supervisor_sessions with appropriate TTL
  RETURN data
```

### 3.3 Stale Data Handling

| Scenario | Data Age | User-Facing Message | System Action |
|---|---|---|---|
| Dashboard view, cache warm | < 15 min | (no indicator — data is fresh) | Serve cache. No AA call. |
| Dashboard view, cache stale, budget available | > 15 min | (no indicator — silent refresh) | Fetch from AA. Update cache. |
| Dashboard view, cache stale, budget exhausted | > 15 min | "Balance as of [HH:MM]. Refresh available in [N] min." | Serve stale cache. Show timestamp. Do not block. |
| 'Pay' intent, cache warm | < 15 min | (no indicator — proceed to payment) | Force-refresh AA balance regardless of cache. This is the hard-stop path. |
| 'Pay' intent, budget exhausted | any | "Unable to verify balance. Proceed with caution or wait [N] min." | Block payment. Do not proceed without fresh balance. Admin can override. |
| AA API down (circuit breaker OPEN) | any | "Bank data is temporarily unavailable. Last known balance: [amount] at [time]." | Circuit breaker suppresses calls. Serve last cached value with prominent staleness warning. |
| No cache, budget exhausted, 'Pay' intent | none | "Balance check unavailable. Please try again in [N] min." | Hard block. Cannot safely authorise payment without balance data. |

### 3.4 User Message Templates (Bhashini-ready)

```text
# Message templates — display in user's preferred_language via Bhashini
# Use {var} interpolation. Keep messages under 100 characters (SMS-friendly).

BUDGET_EXHAUSTED_MESSAGE = (
  'Balance refresh limit reached. Last checked: {last_fetched_at_relative}. '
  'Next refresh available in {retry_after_minutes} min.'
)

STALE_DATA_WARNING = (
  'Showing balance from {last_fetched_at_relative}. '
  'Live balance unavailable right now.'
)

PAY_BLOCKED_NO_BUDGET = (
  'Cannot verify your balance right now. '
  'Please wait {retry_after_minutes} min or ask Admin to approve manually.'
)

AA_DOWN_WARNING = (
  'Bank connection temporarily unavailable. '
  'Showing balance from {last_fetched_at_relative}.'
)
```

## 4. BBPS — Detailed Spec

### 4.1 Limit Summary

| Parameter | Value | Notes |
|---|---|---|
| Hard limit | 50 transactions per day | Per user. Resets at midnight IST. |
| Uptime | 98% success rate | 2% fail due to biller downtime — not NPCI infrastructure. |
| Circuit breaker threshold | 3 consecutive failures → OPEN | 30-minute OPEN period. Defined in NFR v2.1 §3. |
| Backoff sequence | 1s, 2s, 4s, 8s (then give up) | 4 attempts total. No retry after 8s failure — enter OPEN. |
| Zombie window | > 5 min in PENDING = zombie | Healer polls BBPS status API. See Financial Safety spec §4. |
| Redis key scope | Per user_id, per calendar day (IST) | Key: dpi:bbps:tx:{user_id}:{YYYY-MM-DD} |
| On limit hit | Block with clear message and reset time | Hard block — payment cannot proceed. No stale-data fallback. |

### 4.2 Pre-Execution Budget Check

The BBPS budget check happens at Gate G3 (pre-execution validation) in the Financial Safety spec §2.2, before the idempotency key is persisted. If the budget is exhausted, the session moves to ABORTED without writing the idempotency key — the transaction never starts.

```text
# Gate G3 — BBPS budget check (runs before Phase 1 two-phase commit)

day_key = f'dpi:bbps:tx:{user_id}:{today_ist}'
ttl     = seconds_until_midnight_ist()
allowed, count = check_dpi_budget(redis, day_key, max=50, ttl=ttl)

IF NOT allowed:
  session.state = 'ABORTED'
  session.abort_reason = 'BBPS_DAILY_LIMIT_EXCEEDED'
  notify_user(
    message=BBPS_LIMIT_MESSAGE.format(
      used=50, resets_at=midnight_ist_formatted()
    )
  )
  RAISE GateFailure('G3_BBPS_BUDGET_EXHAUSTED')

# On successful payment execution (Phase 2 commit complete):
# The increment already happened at G3 check time.
# If payment fails after G3, the budget counter is NOT decremented.
# Rationale: we cannot safely un-count an attempt that may have partially
# reached NPCI. The 50/day budget is conservative enough to absorb failures.
```

### 4.3 Circuit Breaker for BBPS

BBPS failures are predominantly biller-side (specific billers go down, not NPCI infrastructure). The circuit breaker fires on consecutive failures to any BBPS endpoint — it does not distinguish between biller-specific and network failures, because we cannot reliably distinguish them from the API response alone.

```text
BBPS CIRCUIT BREAKER TRANSITIONS

State: CLOSED (normal operation)
  → On success:   reset failure counter
  → On failure:   increment dpi:cb:bbps:failure_count
  → If failure_count >= 3:
      SET dpi:cb:bbps:state 'OPEN'
      SET dpi:cb:bbps:opened_at {now_epoch}
      SET dpi:cb:bbps:failure_count 0
      ALERT: 'BBPS circuit breaker OPEN — 3 consecutive failures'

State: OPEN (suppressing calls for 30 minutes)
  → All BBPS calls immediately return:
      RateLimitError('BBPS_CIRCUIT_OPEN', retry_after=remaining_open_seconds)
  → User sees: BBPS_DOWN_MESSAGE
  → After 30 minutes from opened_at:
      SET dpi:cb:bbps:state 'HALF_OPEN'
      SET dpi:cb:bbps:half_open_at {now_epoch}

State: HALF_OPEN (probe — allow one test transaction)
  → Allow exactly one BBPS call through (the probe)
    Lock: SET dpi:cb:bbps:probe_lock '1' EX 60 NX
    If lock acquired: this request is the probe
    If lock not acquired: treat as OPEN (another probe is in flight)
  → On probe success:
      SET dpi:cb:bbps:state 'CLOSED'
      DEL dpi:cb:bbps:opened_at, dpi:cb:bbps:half_open_at
      ALERT: 'BBPS circuit breaker CLOSED — service restored'
  → On probe failure:
      SET dpi:cb:bbps:state 'OPEN'
      SET dpi:cb:bbps:opened_at {now_epoch}  # reset 30-min timer
      ALERT: 'BBPS circuit breaker re-OPEN — probe failed'
```

### 4.4 Exponential Backoff Sequence with Jitter

| Attempt | Base Delay | Jitter (± random) | Actual Sleep Range | On Failure Action | CB Count |
|---|---|---|---|---|---|
| 1 (initial) | 0s | +0–100ms | 0–100ms | Record failure. Wait. | +1 |
| 2 | 1s | +0–100ms | 1.0–1.1s | Record failure. Wait. | +1 |
| 3 | 2s | +0–100ms | 2.0–2.1s | Record failure. Wait. | +1 → ≥3 → OPEN |
| 4 | 4s | +0–100ms | 4.0–4.1s | Session → FAILED. No retry. | N/A (already OPEN) |
| (suppressed) | — | — | — | CB OPEN. Calls suppressed 30 min. | Reset to 0 |

> ℹ INFO: Fix 7 (v1.1): Jitter prevents thundering-herd on HALF_OPEN probe recovery. Without jitter, if multiple sessions are waiting for BBPS to recover and all attempt retry at the same millisecond, they hit the DPI simultaneously — creating a self-inflicted spike exactly when the service is most fragile. The probe lock (§8.3) already serialises the HALF_OPEN probe itself; jitter handles the queue of waiting sessions that follow. Formula: sleep = base_delay + random.uniform(0, 0.1)

```python
import random

BACKOFF_DELAYS = [0, 1, 2, 4]  # seconds (4 attempts)

for attempt, base_delay in enumerate(BACKOFF_DELAYS):
    jitter = random.uniform(0, 0.1)  # 0–100ms uniform jitter
    sleep_seconds = base_delay + jitter
    if sleep_seconds > 0:
        time.sleep(sleep_seconds)
    try:
        result = call_bbps(payload)
        circuit_breaker.record_success()
        return result
    except (HTTPError5xx, Timeout, ConnectionRefused) as e:
        circuit_breaker.record_failure()  # may transition to OPEN
        if attempt == len(BACKOFF_DELAYS) - 1:
            raise BBPSExhaustedError('All retries failed') from e
        log.warning('BBPS attempt failed', attempt=attempt+1, error=str(e))

# BBPS_DOWN_MESSAGE — shown when circuit breaker is OPEN
BBPS_DOWN_MESSAGE = (
  'Bill payment is temporarily unavailable. '
  'Service expected to resume by {expected_restore_time}. '
  'Your bill due date: {bill_due_date}. We will remind you when service is restored.'
)

BBPS_LIMIT_MESSAGE = (
  'Daily payment limit reached ({used} of 50 payments used). '
  'Limit resets at midnight ({resets_at} IST).'
)
```

## 5. ABHA — Detailed Spec

### 5.1 Limit Summary

| Parameter | Value | Notes |
|---|---|---|
| Hard limit | 10 consent grants per day | Per user. This is grants (new consents), not data fetches. |
| Data fetch limit | Not explicitly rate-limited by ABDM | ABDM HIU policy limits consent grants, not subsequent fetches from an active consent. |
| Uptime | 85% | Lowest of all DPIs. Frequent HIP (hospital) outages. ABDM infra unstable. |
| FHIR parse failure rate | High (variable by HIP) | Bundles often missing required fields or wrong date formats. |
| Circuit breaker threshold | 3 consecutive failures → OPEN | 20-minute OPEN period (shorter than BBPS — ABDM outages tend to be shorter). |
| Redis key scope | Per user_id, per calendar day (IST) | Key: dpi:abha:consent:{user_id}:{YYYY-MM-DD} |
| On limit hit | Block new consent grants for rest of day | Existing active consents continue to work — only new grants are blocked. |

### 5.2 Consent Grant Budget Check

```text
# ABHA consent grant budget check — runs at Step 6b of consent grant flow
# (Consent Manager §4.2 Step 6, specifically for purpose_codes: ABHA_*)

day_key = f'dpi:abha:consent:{user_id}:{today_ist}'
ttl     = seconds_until_midnight_ist()
allowed, count = check_dpi_budget(redis, day_key, max=10, ttl=ttl)

IF NOT allowed:
  # Do NOT block existing health access — only new consent grants are blocked.
  # User can still read data from their existing active ABHA consents.
  RAISE ConsentError(
    'ABHA_GRANT_LIMIT_EXCEEDED',
    message=ABHA_GRANT_LIMIT_MESSAGE.format(resets_at=midnight_ist_formatted())
  )

ABHA_GRANT_LIMIT_MESSAGE = (
  'Health record connection limit reached for today. '
  'You can connect new health providers from tomorrow ({resets_at} IST). '
  'Existing health connections continue to work.'
)
```

### 5.3 FHIR Parse Failure Handling

ABDM's 85% uptime figure masks a separate failure mode: malformed FHIR R4 bundles. A HIP (hospital) may respond successfully (HTTP 200) but send a FHIR bundle with missing required fields, wrong date formats, or null medication names. These are not circuit-breaker events — they are data quality events.

```text
FHIR PARSE FAILURE HANDLING

On FHIR bundle parse error:
  1. Log full parse error details (hospital HIP ID, error type, field path)
  2. Metrics: increment 'dpi.abha.fhir_parse_error' with tags {hip_id, error_type}
  3. Return partial data: any successfully parsed fields are returned
     (e.g., if drug name parsed but dosage failed, return drug name + 'dosage unavailable')
  4. Flag the record: health_records.parse_quality = 'PARTIAL' | 'FAILED'
  5. Show user: FHIR_PARSE_WARNING message
  6. DO NOT trip circuit breaker (HTTP 200 = ABDM is up, HIP data is bad)

FHIR_PARSE_WARNING = (
  'Some health record details could not be read automatically. '
  'Please check the original record from {hospital_name} for accuracy.'
)

# Persistent parse failures from same HIP → alert Admin:
# IF fhir_parse_errors_from_hip(hip_id, last_24h) > 5:
#   notify_admin('Health records from {hospital_name} are consistently
#     unreadable. Manual entry may be needed.')
```

### 5.4 ABHA Degraded Mode

> ABHA DEGRADED MODE — when ABDM is down or circuit breaker OPEN
> Show: 'Government health records are temporarily unavailable.'
> Show: 'Your locally stored health information is still accessible.'
> Allow: Access to vault documents (uploaded PDFs, photos of prescriptions).
> Allow: Manually entered medication reminders (not ABHA-sourced).
> Block: New health consent grants. New FHIR data fetches.
> Notify Admin: 'ABHA health service is down. Manual health tracking only.'
> Expected restore: show dpi:cb:abha:opened_at + 20 minutes.

## 6. ONDC — Detailed Spec

### 6.1 Limit Summary

| Parameter | Value | Notes |
|---|---|---|
| Soft limit | 100 searches per day | ONDC network policy. Unenforced — no HTTP 429. Advisory only. |
| Catalog accuracy | 60% | Prices and stock levels are often wrong. This is the primary quality risk, not rate limits. |
| Uptime | Variable by seller | ONDC infrastructure is stable; individual seller nodes are not. |
| Circuit breaker | Not applicable | ONDC failures are seller-specific. No org-wide circuit breaker. Per-seller blacklisting instead. |
| Redis key scope | Per user_id, per calendar day (advisory) | Key: dpi:ondc:search:{user_id}:{YYYY-MM-DD}. Monitoring only. |
| On soft limit hit | Log and alert. Do not block. | User can continue searching. Alert if single user exceeds 80 searches/day. |

### 6.2 Advisory Monitoring

```python
# ONDC search tracking — advisory only, never blocks

On each ONDC search call:
  day_key = f'{REDIS_ENV_PREFIX}:dpi:ondc:search:{user_id}:{today_ist}'
  count = redis.INCR(day_key)
  IF count == 1: redis.EXPIRE(day_key, seconds_until_midnight_ist())

  # Monitoring alerts (do not block user):
  IF count == 80:
    metrics.alert('dpi.ondc.search_approaching_limit',
      tags={'user_id': user_id, 'count': count})
  IF count > 100:
    metrics.alert('dpi.ondc.search_over_limit',
      tags={'user_id': user_id, 'count': count})
    log.warning('ONDC soft limit exceeded — investigate for scraping/abuse')

# ── Fix 6 (v1.1): ONDC seller blacklist — progressive expiry ─────────────
# Fixed 1-hour EX on every blacklist was too permissive.
# A consistently bad seller got a fresh 1-hour window each time,
# causing repeated re-tests against a seller that never recovers.
# Progressive rule: count offences in 24h, escalate TTL.

def blacklist_seller(redis_client, seller_id):
    offence_key   = f'{REDIS_ENV_PREFIX}:dpi:ondc:seller_offences:{seller_id}:{today_ist}'
    blacklist_key = f'{REDIS_ENV_PREFIX}:dpi:ondc:seller_blacklist:{seller_id}'

    offence_count = redis_client.incr(offence_key)
    if offence_count == 1:
        # First offence of the day — set 24h window on the offence counter
        redis_client.expire(offence_key, seconds_until_midnight_ist())

    if offence_count >= 3:
        blacklist_ttl = 86400  # 24 hours — chronic bad seller
        log.warning('ONDC seller persistent failure — 24h blacklist',
            seller_id=seller_id, offence_count=offence_count)
        metrics.alert('dpi.ondc.seller_blacklisted_24h',
            tags={'seller_id': seller_id})
    else:
        blacklist_ttl = 3600   # 1 hour — first or second offence

    redis_client.set(blacklist_key, str(offence_count), ex=blacklist_ttl)

# Calling context: on 3 consecutive failures from same seller_id
# Future ONDC searches: skip sellers where blacklist key exists
def is_seller_blacklisted(redis_client, seller_id):
    return redis_client.exists(
        f'{REDIS_ENV_PREFIX}:dpi:ondc:seller_blacklist:{seller_id}'
    )
```

## 7. Bhashini — Detailed Spec

### 7.1 Limit Summary

| Parameter | Value | Notes |
|---|---|---|
| Hard limit | 1000 ASR calls per day | Org-level. All users share one budget. Not per user. |
| Uptime | 95% | Better than ABHA. Occasional model inference slowdowns during peak. |
| ASR accuracy | Hindi: 90%, Telugu: 70%, Punjabi: 60% | Confidence threshold < 80% triggers fallback to text input. |
| Confidence threshold | 80% | Reject transcription if confidence < 0.8. Do not pass low-confidence intent to Supervisor. |
| Circuit breaker threshold | 5 consecutive failures → OPEN | Higher threshold than BBPS because Bhashini is used for every voice interaction. |
| OPEN period | 10 minutes | Shorter — Bhashini failures are usually transient model inference issues. |
| Redis key scope | Org-level, per calendar day (IST) | Key: dpi:bhashini:asr:{YYYY-MM-DD}. One key for all users. |
| On limit hit | Prompt user to switch to text input | ASR is a UX enhancement, not a core function. Text is the fallback. |

### 7.2 Org-Level Budget Allocation and Per-Family Auto Soft-Throttle

The 1000 ASR call/day limit is org-wide across all family accounts. At early scale (< 50 families), this is not a constraint — a single family averages 10-20 voice interactions per day. At 50 families × 15 calls = 750 calls/day, we approach the limit. Org budget alert threshold: 800 calls (80%). Fix 8 (v1.1) adds an automatic per-family soft-throttle at 10% of the org budget — no manual intervention required.

```python
# ── Org-level budget check ───────────────────────────────────────────────
org_day_key = f'{REDIS_ENV_PREFIX}:dpi:bhashini:asr:{today_ist}'
ttl         = seconds_until_midnight_ist()
org_allowed, org_count = check_dpi_budget_safe(redis, org_day_key, max=1000, ttl=ttl)

IF NOT org_allowed:
  # Entire org budget exhausted. All voice input disabled for rest of day.
  RAISE RateLimitError('BHASHINI_ORG_LIMIT', message=BHASHINI_LIMIT_MESSAGE)

# Org budget monitoring alerts (do not block):
IF org_count == 800:
  metrics.alert('dpi.bhashini.budget_at_80pct', tags={'count': org_count})
IF org_count == 950:
  metrics.alert('dpi.bhashini.budget_critical', tags={'count': org_count})
  notify_admin('Voice recognition is running low. 50 calls remaining.'
               ' Consider upgrading API tier.')

# ── Fix 8 (v1.1): Per-family auto soft-throttle ──────────────────────────
# Problem (v1.0): runbook said 'monitor and manually contact heavy users'.
# That is a weak control — by the time the on-call engineer phones the family,
# the org budget is already gone. Need an automatic gate that fires first.
#
# Rule: if a single family_id has consumed >= 100 ASR calls today (10% of
# org budget of 1000), route their voice requests to text-input prompt.
# This is a soft-throttle — non-blocking. The family can still use all
# features via text. Voice is an enhancement, not a core gate.
#
# 100 calls = 10% of org budget. A family making 100 voice requests in
# a day is either running a bug (looping retry) or extreme edge-case use.
# Normal families: 10–25 calls/day. This threshold has 4x headroom.

PER_FAMILY_SOFT_LIMIT = 100  # 10% of org 1000/day budget

family_day_key = f'{REDIS_ENV_PREFIX}:dpi:bhashini:asr:family:{family_id}:{today_ist}'
family_count   = int(redis.get(family_day_key) or 0)

IF family_count >= PER_FAMILY_SOFT_LIMIT:
  # Do NOT call Bhashini. Prompt for text input instead.
  log.info('Bhashini per-family soft-throttle active',
    family_id=family_id, count=family_count)
  metrics.increment('dpi.bhashini.family_soft_throttled',
    tags={'family_id': family_id})
  IF family_count == PER_FAMILY_SOFT_LIMIT:
    # Alert on first hit, not every subsequent one
    metrics.alert('dpi.bhashini.family_at_limit',
      tags={'family_id': family_id, 'count': family_count})
    notify_admin(f'Family {family_id} has hit Bhashini soft-throttle.
       ({family_count} calls today). Check for looping voice retries.')
  RETURN None, BHASHINI_FAMILY_THROTTLE_MESSAGE

# ── Increment both counters before calling Bhashini ──────────────────────
# Increment family counter (advisory — no blocking Lua script needed)
new_family_count = redis.incr(family_day_key)
IF new_family_count == 1:
    redis.expire(family_day_key, ttl)  # align TTL with midnight IST

# Then call Bhashini (org budget already checked and incremented above)
result = call_bhashini_asr(audio, language=user.preferred_language)

BHASHINI_LIMIT_MESSAGE = (
  'Voice input is unavailable for now. Please type your request instead.'
)

BHASHINI_FAMILY_THROTTLE_MESSAGE = (
  'Voice recognition is taking a short break. Please type your request.'
)
```

### 7.3 Confidence Score Thresholding

```python
# Applied after every Bhashini ASR call, regardless of rate limit status

def process_asr_response(asr_result, user_id, family_id, user_preferred_language):
    confidence = asr_result.get('confidence', 0)
    transcript = asr_result.get('transcript', '')

    IF confidence < 0.80:
        # ── Fix 5 (v1.1): emit audit event on low confidence ─────────────
        # A device with a stuck voice loop will burn the 1000/day org budget
        # without leaving a trace beyond the Redis counter.
        # The audit_log entry gives forensic chain: which user_id, which
        # device, what confidence, what language — essential for §10.3
        # on-call step 'identify heavy users via audit_log'.
        # It also enables accent-bias cluster detection (e.g., if confidence
        # is consistently <0.80 for Telugu users → file Bhashini bug report).
        audit_log.write(
            action='VOICE_ASR_LOW_CONFIDENCE',
            user_id=user_id,
            family_id=family_id,
            details={
                'confidence': round(confidence, 4),
                'language':   user_preferred_language,
                'transcript_length': len(transcript),  # length only, not text
                # Do NOT log transcript — may contain PII (names, amounts, etc.)
            }
        )
        log.info('ASR low confidence — not forwarding to Supervisor',
            confidence=confidence, language=user_preferred_language)
        metrics.histogram('dpi.bhashini.confidence', confidence,
            tags={'language': user_preferred_language})
        return None, LOW_CONFIDENCE_MESSAGE

    IF confidence < 0.90:
        # Medium confidence — pass to Supervisor with a clarification flag.
        metrics.histogram('dpi.bhashini.confidence', confidence,
            tags={'language': user_preferred_language})
        return transcript, CLARIFICATION_PROMPT

    # High confidence — pass directly. No audit event needed.
    return transcript, None

LOW_CONFIDENCE_MESSAGE = (
  "Sorry, I didn't catch that clearly. Please try again or type your request."
)

CLARIFICATION_PROMPT = (
  'I heard: "{transcript}". Is that right?'
)
```

## 8. Cross-DPI Circuit Breaker State Machine

### 8.1 State Definitions

```yaml
States:
  CLOSED     Normal operation. Calls pass through. Failures tracked.
  OPEN       Calls suppressed. DPI considered down. Fixed recovery timer.
  HALF_OPEN  Recovery probe. One call allowed through to test DPI health.

Transitions:
  CLOSED → OPEN       failure_count >= threshold (consecutive failures)
  OPEN → HALF_OPEN    open_duration_seconds elapsed since opened_at
  HALF_OPEN → CLOSED  probe succeeds
  HALF_OPEN → OPEN    probe fails (reset open_duration timer)
```

### 8.2 Per-DPI Configuration

| DPI | Failure Threshold | OPEN Duration | Backoff Sequence | Probe Timeout |
|---|---|---|---|---|
| AA | 3 consecutive | 30 minutes | 1s, 2s, 4s, 8s (4 attempts) | 10 seconds |
| BBPS | 3 consecutive | 30 minutes | 1s, 2s, 4s, 8s (4 attempts) | 15 seconds |
| ABHA | 3 consecutive | 20 minutes | 1s, 2s, 4s (3 attempts) | 15 seconds |
| ONDC | N/A | N/A | N/A (seller blacklisting instead) | N/A |
| Bhashini | 5 consecutive | 10 minutes | 1s, 2s, 4s, 8s, 16s (5 attempts) | 5 seconds |

### 8.3 Counting Rules

- Only CONSECUTIVE failures increment the counter. A success resets failure_count to 0.
- HTTP 429 (rate limit) does NOT count as a failure for circuit breaker purposes. Rate limit responses mean the DPI is up — it is refusing our call, not failing. Only HTTP 5xx, network timeout, and connection refused count.
- HTTP 4xx (other than 429) — depends on the DPI. For AA: 4xx on /FI/request usually means bad consent handle (our bug, not DPI down) — do NOT increment failure count. For BBPS: 4xx on /payment is always a DPI-side issue — DO increment.
- During HALF_OPEN, the probe is a real call to the DPI with a minimal valid payload. For AA: a /Consent/status check (not a full FI fetch). For BBPS: a /biller/fetch (biller info lookup, not a payment). For ABHA: a /health/hip/read (HIP discovery, not a consent grant).

### 8.4 Circuit Breaker Implementation

```python
class CircuitBreaker:
    def __init__(self, provider, redis_client, config):
        self.provider = provider
        self.redis = redis_client
        self.threshold    = config['failure_threshold']
        self.open_seconds = config['open_duration_seconds']

    def _state_key(self):     return f'dpi:cb:{self.provider}:state'
    def _failure_key(self):   return f'dpi:cb:{self.provider}:failure_count'
    def _opened_at_key(self): return f'dpi:cb:{self.provider}:opened_at'

    def get_state(self):
        state = self.redis.get(self._state_key())
        if state is None: return 'CLOSED'  # default
        state = state.decode()
        if state == 'OPEN':
            opened_at = int(self.redis.get(self._opened_at_key()) or 0)
            if time.time() - opened_at >= self.open_seconds:
                self._transition_to_half_open()
                return 'HALF_OPEN'
        return state

    def record_success(self):
        self.redis.set(self._state_key(), 'CLOSED')
        self.redis.set(self._failure_key(), 0)

    def record_failure(self):
        state = self.get_state()
        if state == 'HALF_OPEN':
            self._transition_to_open()  # probe failed
            return
        count = self.redis.incr(self._failure_key())
        if count >= self.threshold:
            self._transition_to_open()

    def _transition_to_open(self):
        pipe = self.redis.pipeline()
        pipe.set(self._state_key(), 'OPEN')
        pipe.set(self._opened_at_key(), int(time.time()))
        pipe.set(self._failure_key(), 0)
        pipe.execute()
        alert(f'CIRCUIT_BREAKER_OPEN: {self.provider}')

    def _transition_to_half_open(self):
        self.redis.set(self._state_key(), 'HALF_OPEN')
        alert(f'CIRCUIT_BREAKER_HALF_OPEN: {self.provider} — sending probe')

    def is_call_allowed(self):
        state = self.get_state()
        if state == 'CLOSED': return True
        if state == 'OPEN':   return False
        if state == 'HALF_OPEN':
            # Only allow one probe through
            probe_key = f'dpi:cb:{self.provider}:probe_lock'
            acquired  = self.redis.set(probe_key, '1', ex=60, nx=True)
            return bool(acquired)
        return False
```

## 9. WireMock Simulator Configuration

All DPI integration testing before live credentials must use WireMock stubs. The simulator must be able to reproduce: normal responses, rate limit responses (HTTP 429), circuit-breaker-triggering failures (HTTP 500), and chaos mode (random failure injection). This section specifies the required stub files.

### 9.1 AA Rate Limit Stub

```text
# File: wiremock/mappings/aa_rate_limit.json
# Activated when: request includes header X-Simulate-Rate-Limit: aa
{
  'request': {
    'method': 'POST',
    'urlPattern': '/FI/request.*',
    'headers': { 'X-Simulate-Rate-Limit': { 'equalTo': 'aa' } }
  },
  'response': {
    'status': 429,
    'headers': {
      'Content-Type': 'application/json',
      'Retry-After': '1800'
    },
    'jsonBody': {
      'errorCode': 'FIU_RATE_LIMIT_EXCEEDED',
      'errorMessage': 'FI fetch limit exceeded. Retry after 1800 seconds.',
      'timestamp': '{{now}}'
    }
  }
}
```

### 9.2 BBPS Circuit Breaker Trigger Stub

```text
# File: wiremock/mappings/bbps_consecutive_failures.json
# Simulates 3 consecutive 500 errors to trigger circuit breaker
{
  'request': {
    'method': 'POST',
    'urlPattern': '/payment.*',
    'headers': { 'X-Simulate-Failures': { 'equalTo': 'bbps-circuit' } }
  },
  'response': {
    'status': 500,
    'headers': { 'Content-Type': 'application/json' },
    'jsonBody': {
      'status': 'FAILURE',
      'errorCode': 'BILLER_UNREACHABLE',
      'message': 'Biller system is down'
    }
  }
}
```

### 9.3 Bhashini Low-Confidence Stub

```text
# File: wiremock/mappings/bhashini_low_confidence.json
{
  'request': {
    'method': 'POST',
    'urlPattern': '/v1/pipeline/compute.*',
    'headers': { 'X-Simulate-Confidence': { 'equalTo': 'low' } }
  },
  'response': {
    'status': 200,
    'jsonBody': {
      'pipelineResponse': [{
        'taskType': 'asr',
        'output': [{ 'source': 'pay bijli bill', 'confidence': 0.62 }]
      }]
    }
  }
}
```

### 9.4 Chaos Mode Configuration

```text
# File: wiremock/chaos_config.yaml
# Enable: set env var CHAOS_MODE=true before starting WireMock

chaos:
  enabled: '{{env.CHAOS_MODE}}'
  scenarios:
    aa_random_failures:
      url_pattern: '/FI/request.*'
      failure_rate: 0.20        # 20% of calls fail
      failure_status: 500
      enabled: true
    bbps_timeout:
      url_pattern: '/payment.*'
      delay_ms: 12000           # 12 second delay (exceeds our 8s backoff max)
      failure_rate: 0.15
      enabled: true
    abha_fhir_malformed:
      url_pattern: '/v0.5/health-information.*'
      failure_rate: 0.30        # 30% return malformed FHIR
      response_body: '{"resourceType":"Bundle","entry":[{"missing_required":true}]}'
      enabled: true
```

### 9.5 Contract Compliance Tests

```python
# Test suite: verify WireMock stubs match real DPI API schemas
# Run: pytest tests/dpi_contracts/ -v

def test_aa_rate_limit_response_format():
    # Activate rate limit stub
    response = client.post('/FI/request',
        headers={'X-Simulate-Rate-Limit': 'aa'})
    assert response.status_code == 429
    assert 'Retry-After' in response.headers
    assert response.json()['errorCode'] == 'FIU_RATE_LIMIT_EXCEEDED'
    # Verify our handler correctly parses and surfaces retry_after
    retry_after = int(response.headers['Retry-After'])
    assert retry_after > 0

def test_circuit_breaker_trips_on_3_bbps_failures():
    # Reset circuit breaker state
    redis.delete('dpi:cb:bbps:state', 'dpi:cb:bbps:failure_count')
    for _ in range(3):
        client.post('/payment', headers={'X-Simulate-Failures': 'bbps-circuit'})
    state = redis.get('dpi:cb:bbps:state')
    assert state == b'OPEN'

def test_bhashini_low_confidence_does_not_reach_supervisor():
    response = simulate_voice_input(
        audio='pay electricity bill',
        headers={'X-Simulate-Confidence': 'low'})
    # Low-confidence ASR must NOT produce a Supervisor intent
    assert response.intent is None
    assert 'try again' in response.user_message.lower()
```

## 10. Monitoring, Alerts, and On-Call Runbook

### 10.1 Prometheus Metrics

| Metric Name | Type | Labels | Description |
|---|---|---|---|
| dpi.rate_limit.hit | Counter | provider, user_id (hashed) | Incremented each time a budget check blocks a call |
| dpi.rate_limit.budget_remaining | Gauge | provider, window | Current remaining budget (polled every 60s) |
| dpi.circuit_breaker.state | Gauge | provider | 0=CLOSED, 1=OPEN, 2=HALF_OPEN |
| dpi.circuit_breaker.open_count | Counter | provider | Number of times circuit breaker has tripped (all time) |
| dpi.api.latency_ms | Histogram | provider, endpoint, status | P50/P95/P99 latency per DPI endpoint |
| dpi.api.error_rate | Gauge | provider, error_type | Rolling 5-minute error rate (5xx + timeouts) |
| dpi.bhashini.confidence | Histogram | language | Distribution of ASR confidence scores |
| dpi.abha.fhir_parse_error | Counter | hip_id, error_type | FHIR bundle parse failures by hospital |
| dpi.rate_limit.redis_miss | Counter | key_prefix | Redis unavailability during budget checks |

### 10.2 Alert Thresholds

| Alert Name | Condition | Severity | Notify |
|---|---|---|---|
| DPI_CIRCUIT_OPEN | dpi.circuit_breaker.state == 1 for any provider | P1 | PagerDuty → Founder immediately |
| AA_BUDGET_CRITICAL | AA budget < 1 fetch remaining this hour for > 10% of users | P2 | Slack #ops-alerts |
| BBPS_DAILY_LIMIT_APPROACHING | BBPS budget > 40/50 for any user | P3 | Slack #ops-alerts |
| BHASHINI_BUDGET_80PCT | Bhashini org budget > 800/1000 | P2 | Slack #ops-alerts + notify Admin |
| BHASHINI_BUDGET_CRITICAL | Bhashini org budget > 950/1000 | P1 | PagerDuty + notify all Admins |
| ABHA_FHIR_ERRORS_ELEVATED | dpi.abha.fhir_parse_error > 10 in last hour | P3 | Slack #ops-alerts |
| DPI_LATENCY_DEGRADED | P95 latency > 3s for any DPI over 5 min window | P2 | Slack #ops-alerts |
| REDIS_MISS_RATE_ELEVATED | dpi.rate_limit.redis_miss > 5 in 5 minutes | P2 | PagerDuty → check Redis health |

### 10.3 On-Call Response Runbook

#### DPI_CIRCUIT_OPEN (P1) — Step-by-step

```text
STEP 1: Identify which DPI
  redis-cli GET dpi:cb:aa:state
  redis-cli GET dpi:cb:bbps:state
  redis-cli GET dpi:cb:abha:state
  redis-cli GET dpi:cb:bhashini:state

STEP 2: Check DPI status page
  AA:       https://sahamati.org.in/status
  BBPS:     https://www.npci.org.in/status  (or ask bank ops channel)
  ABHA:     https://abdm.gov.in/service-status
  Bhashini: https://bhashini.gov.in/status

STEP 3: Check our own error logs
  kubectl logs -l app=dpi-client --since=30m | grep '{provider}'
  Look for: consistent error codes, timeout patterns, auth failures

STEP 4: Determine user impact
  AA OPEN:       Finance dashboard shows stale data. Payment blocked.
  BBPS OPEN:     All bill payments blocked.
  ABHA OPEN:     Health records unavailable. Vault docs still accessible.
  Bhashini OPEN: Voice input unavailable. Text input works.
  Notify affected families if outage > 30 minutes.

STEP 5: Manual circuit breaker reset (ONLY if DPI confirmed healthy)
  redis-cli SET dpi:cb:{provider}:state 'CLOSED'
  redis-cli DEL dpi:cb:{provider}:failure_count
  redis-cli DEL dpi:cb:{provider}:opened_at
  MONITOR: watch for re-tripping within 5 minutes

STEP 6: If DPI is confirmed down and ETA > 2 hours
  Post in-app banner: 'Some features are temporarily unavailable due to
    a government service outage. We will update as soon as it is restored.'
  Enable degraded mode UX (stale data banners, text-input fallback)
```

#### BBPS_DAILY_LIMIT_APPROACHING (P3)

> 🔧 OPERATOR ACTION: Check if the user has legitimate use case (e.g., joint family paying multiple billers). If legitimate: no action needed — they approach the limit, we inform them. If suspicious (possible scraping): review audit_log for session patterns. The 50/day limit is per user — family members have independent budgets.

#### BHASHINI_BUDGET_CRITICAL (P1)

```sql
STEP 1: Check remaining budget
  redis-cli GET dpi:bhashini:asr:{today_date}
  e.g., '967' of 1000 used

STEP 2: Identify heavy users
  SELECT user_id, COUNT(*) as asr_calls
  FROM audit_log
  WHERE action = 'VOICE_INTENT_PROCESSED'
    AND timestamp > NOW() - INTERVAL '24 hours'      -- audit_log's column is timestamp (v1.2 fix)
  GROUP BY user_id ORDER BY asr_calls DESC LIMIT 10;

STEP 3: Immediate actions
  a) Upgrade Bhashini API tier if possible (immediate — contact Bhashini support)
  b) If upgrade not possible: budget rationing
     IF remaining < 50:
       Disable voice input for non-essential queries (PRODUCT_ANALYTICS, ONDC search)
       Reserve remaining budget for finance and health critical paths only

STEP 4: Post-incident
  Add per-user Bhashini budget tracker (advisory) to prevent concentration
  Review whether Bhashini ASR tier needs to be upgraded as standard
```

## 11. Q&A

| Question | Answer |
|---|---|
| Why track AA rate limits at the consent_handle level rather than the user_id level? | Because Sahamati's limit is per FIU consent handle, not per user. A user with an HDFC consent handle and an ICICI consent handle has 3 fetches/hour for each independently — 6 total. If we track at user_id level, we would falsely block legitimate fetches from the second bank after the first bank's handle exhausts its budget. The consent_handle granularity is also already available in the data model (consent_handles table), so no new schema is needed. |
| What if a user exceeds the BBPS 50/day limit before paying an urgent bill (e.g., a bill due today)? | The hard block stands — we cannot exceed NPCI's limit. The correct UX response is: show the limit message with the reset time (midnight IST), show the bill due date prominently, and (if the due date is today) suggest the user pay directly through the biller's website or their bank app, and offer to remind them at 00:01 IST when the limit resets. Admin can also manually mark the bill as paid-externally to suppress reminders. |
| The AA 3 fetches/hour limit seems very restrictive. Is there any way to increase it? | No — it is set by RBI and the Sahamati FIU agreement, not by us. The correct architectural response is the coalescing algorithm (§3.2): if two family members both open the finance dashboard within 60 seconds, the second one gets the result of the first one's fetch rather than burning a second slot. With 15-minute TTL caching and coalescing, 3 fetches/hour is sufficient for a family's normal usage pattern. The scenario where it fails is: multiple users doing forced refreshes in rapid succession. The UX fix is to disable the manual refresh button for non-Admin users. |
| Should HTTP 429 responses from DPIs increment the circuit breaker failure counter? | No. A 429 means the DPI is healthy and responding correctly — it is rejecting our call due to our rate limit, not failing. Treating 429 as a circuit breaker event would open the circuit breaker precisely when we most need it closed (when we've exhausted our budget and need the DPI to remain accessible for the remaining calls). Only 5xx, connection timeout, and connection refused count as circuit breaker failures. |
| Bhashini's 1000 call/day limit is org-wide. Does this mean one heavy voice user can block voice input for all other families? | It could — but fix 8 (v1.1) adds an automatic per-family soft-throttle at 100 calls/day (10% of org budget) that fires before any manual intervention is needed. When a family hits the threshold, their voice requests are silently routed to text-input prompt. They can still use all features — voice is an enhancement, text is the fallback. The on-call runbook (§10.3) gets a Prometheus alert the moment any family hits the threshold, so the forensic investigation (which user_id, which device, looping retry vs. legitimate use) can happen in parallel while the throttle is already in effect. The §7.3 VOICE_ASR_LOW_CONFIDENCE audit event gives the additional forensic chain for accent-bias and retry-loop detection. At > 50 families, upgrade the Bhashini API tier before the 750-call daily run-rate approaches 80%. |
| Should we build a queue for rate-limited requests (instead of blocking the user immediately)? | Not in v1. A queue introduces complexity (queue depth monitoring, queue expiry, notifying users when their queued request finally executes — possibly hours later). For FamilyLifeOS v1 scale, the simpler approach — block with clear message and retry time — is correct. The one exception is the AA coalescing algorithm (§3.2), which effectively queues a second request behind an in-flight first request for up to 10 seconds. That is the right scope for v1. A general request queue is a v2 consideration when usage patterns are better understood. |

— End of Runbook_DPI_Rate_Limits_v1.1 —
