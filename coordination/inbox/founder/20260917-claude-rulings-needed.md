# Rulings needed (as of 2026-09-17)

- **From:** claude
- **To:** founder
- **Date:** 2026-09-17
- **About:** module PRDs v0.1, Roadmap §9, Execution Plan §9
- **Expected of you:** answer
- **Status:** open

## Message

The same list was given in chat at the end of the 2026-09-17 session, with explanations and implications. Short form here so the other agents can see what is pending. Rulings go into the tracker's Decision Log.

### A. Needs your ruling (product decisions nobody else should make)

1. **Vault OI-6 — are one adult's documents visible to the other adult by default?** Recommendation: shared by default for family-level documents (RC, insurance, property), private by default for personal identity documents (PAN, passport, licence), with a per-document switch for the holder.
2. **Vault OI-1 — who gets document-expiry reminders, and when?** Recommendation: the holder (if an adult) and the admins at 30 and 7 days; for minor, managed and passive holders, the admins and the primary proxy only.
3. **Health OI-2 — who consents on behalf of a managed profile (Nani)?** Recommendation: the primary proxy, with their own passkey, recorded in a new `proxy_consent_user_id` column (Consent Manager v1.3 + Data Model change, best folded into the pending re-freeze).
4. **Go-ahead to create the GitHub labels, milestones (no due dates) and the Phase 0–1 issues** from Execution Plan Appendix A. Recommendation: yes, after your tooling install so the board does not show work that cannot start.

### B. Defaults I will apply unless you object

5. Health OI-5 — a dose is MISSED after 2 × `notify_timeout_mins`; per-medication windows later.
6. Finance OI-6 — `CHECK_BALANCE` is denied for the `elder` role (matches DM Q2 and Core PRD §2).
7. Finance OI-7 — no admin override of a blocked balance check in Phase 1.
8. Passkeys (WebAuthn) as the biometric stand-in, with a dev-only PIN fallback that is off in the demo build.
9. The first end-to-end test types the intent as text; the browser speech stand-in arrives in Phase 4.
10. Branch protection on `main` without "include administrators", so `coord:` commits to `coordination/` can go straight to `main`.

### C. Not needed yet (will come back at the milestone named)

- Demo host provider (before M4). Video visibility, public or unlisted (before M5). Legal read of the medical disclaimer wording (before the demo is shared). Per-user resource-lock case (Finance PRD review, WP-15).

## Reply

