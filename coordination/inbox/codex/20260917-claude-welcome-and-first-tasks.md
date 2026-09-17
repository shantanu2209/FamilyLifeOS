# Welcome, and your first two tasks

- **From:** claude
- **To:** codex
- **Date:** 2026-09-17
- **About:** WP-09, WP-10 (then WP-05, WP-06) in `docs/Execution_Plan.md`
- **Expected of you:** act
- **Status:** open

## Message

You are one of three agents on this repository (Claude Code, you, Gemini in Antigravity). The founder, Shantanu Chaudhary, makes decisions and merges; nobody else does either.

Before anything else, read in this order: `AGENTS.md` (whole file; §4 invariants and §6 roster and working rules matter most), `coordination/README.md` (the protocol: issues, labels, branches, review pairs, this inbox, `STATUS.md`), then `docs/PROJECT_TRACKER.md` → Decision Log. Logged decisions are closed; if one looks wrong, say so in an issue labelled `blocked`, do not work around it.

Your lane: implementation against frozen specs, with tests, and second reviewer for Claude's and Gemini's PRs. You review; Claude reviews you.

First tasks, in order (GitHub issues #9 and #10, then #5 and #6; issue number = WP number for Phases 0–1):

1. **WP-09 — review round 2 of `docs/specs/Tech_Spec_Module_Registry.md` v1.1.** §13 of that spec is the round-1 review log and says what round 2 should focus on. Check it against AGENTS.md §4 items 30–35 and against the frozen FTS v1.2, CM v1.2 and RB v1.2.
2. **WP-10 — review round 2 of `docs/specs/Data_Model_Schema.md` v1.3.** Its last section summarises the v1.3 changes (resource lock table, session columns, role rename, folded-in consent and registry tables, the audit write protocol `fn_lock_audit_tail` → `fn_append_audit`). Confirm the DDL is internally consistent and expressible as one Alembic migration, and that FTS §9.2/§11.3, CM §4.1/§4.6 and MR §5/§7.2 agree with it.

   Include the one addition made after the freeze: **Consent Manager v1.3 §2.6** (proxy consent for managed profiles; column `consent_records.proxy_consent_user_id`, action `PROXY_CONSENT_GRANTED`; Data Model v1.3 change 15). Everything else in the Consent Manager is the frozen v1.2 text and is not up for review.

For both: **do not edit the specs.** Post findings by severity (blocker / should-fix / nit), each with document, section and a proposed wording. Claude Code applies accepted fixes (WP-11) and the specs freeze. Three module PRDs list open issues that may bear on your review: `docs/strategy/PRD_Module_Secure_Vault.md` §11 (OI-2, OI-3), `PRD_Module_Finance.md` (OI-3, OI-6, OI-7), `PRD_Module_Health.md` (OI-2, OI-3, OI-4).

3. After the reviews: **WP-05** (uv + Python 3.12 scaffolding, ruff, pre-commit, import-linter contract) and **WP-06** (CI workflow). Branch `agent-codex/issue-<n>`, PR from the template, `needs-review`, reviewer is Claude.

When you start, add your lines to `coordination/STATUS.md` (your section only) and move this file to `coordination/inbox/codex/done/` with `Status: done`.

## Reply

