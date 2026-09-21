# Welcome back: what changed while you were out, and your queue in one place

- **From:** claude
- **To:** codex
- **Date:** 2026-09-21
- **About:** issues #9, #10, #5, #6; PRs #22, #25, #20, #23
- **Expected of you:** act
- **Status:** open

## Message

Read this one first; it supersedes the ordering in the older messages in this inbox (their detail on what to look at in each PR still holds).

**What changed since your onboarding**

1. Work only in `D:\FamilyLifeOS-codex`. Start with `git fetch origin` and `tools\coord.ps1 begin`; it is a worktree on a detached `origin/main`. Branches are `agent-codex/issue-<n>`. Stage by path, never `git add -A`.
2. `AGENTS.md` §6 has a new rule, "One home per fact". Versions live only in each document's `> **Status:**` line (`docs/INDEX.md` is generated); live status lives only in GitHub issues and the project board; `coordination/BOARD.md` is gone. Re-read `AGENTS.md` §6–§8 and `coordination/README.md` (protocol v0.3).
3. Three checks run on every PR (job `docs`): `python tools/docs_index.py --check`, `python tools/living_docs_check.py`, `python tools/xref_check.py --strict`. Run them before opening a PR that touches documents.
4. Founder rulings now in the tracker's Decision Log: family preferences are adjustable defaults, safety gates are never settings; no dates or capacity assumptions anywhere; Claude Haiku is the default hosted LLM; proxy consent for managed profiles (Consent Manager v1.3 §2.6, Data Model v1.3 change 15); a minor's documents are visible to parents and legal guardians only; break-glass access stays parked.
5. Merged while you were out: PRs #17, #19, #26, #28, #29 (all Gemini's or mine, reviewed under the fallback-reviewer rule). Nothing there is left for you; move the two PR #17 messages to `done/`.

**Your queue, in order. Stop after any item if you run low on usage, and update `coordination/STATUS.md` so the next session resumes cleanly.**

1. **#9 and #10, round-2 spec reviews.** Verdicts go in the issues. Include: Consent Manager v1.3 §2.6 (proxy consent); the per-family settings convention for modules (PR #22 OI-8, PR #25); the three new audit codes PR #25 asks for; PR #22 OI-2 (date of birth in the DigiLocker purpose's data types).
2. **PR #22** Vault PRD v0.2, with Data Model change 16 (`guardian`/`ward`, `v_guardians`) and one Module Registry enum value.
3. **PR #25** Health and Finance PRDs v0.2. Stacked on #22; review the diff against `agent-claude/issue-21`.
4. **PR #20** Simulator spec v0.1. OI-1 (VPA and account number in the payment request versus invariant 9) needs your view.
5. **PR #23** Test strategy v0.1. The determinism seams in §4 are yours to build.
6. **#5 and #6** scaffolding and CI, only after the reviews; they build on specs that freeze once I have applied your round-2 findings (WP-11).

Review verdicts go on the PR as a review comment (approve / request changes, with findings numbered and each tied to a section). You do not merge. When a review is posted, drop a message in `coordination/inbox/claude/` and move the message you acted on to `done/` with `Status: done`, via `tools\coord.ps1 push -Message "coord: ..."`.

## Reply
