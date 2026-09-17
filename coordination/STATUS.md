# Status

Who is working on what, right now. One section per agent; **edit only your own section**. Keep it to a few lines: current item (issue, branch), what you are waiting for, last finished item. Update it when you pick something up and when you stop. Commit with a `coord:` subject straight to `main` (`coordination/README.md` §5).

## Claude Code (`agent:claude`)

- **Working on:** four PRs waiting for Codex's review: #22 (#21, Vault PRD v0.2 plus Data Model change 16 `v_guardians`), #25 (#24, Health and Finance PRDs v0.2, stacked on #22), #20 (#12, simulator spec v0.1), #23 (#13, test strategy v0.1). Folder `D:\FamilyLifeOS-claude`.
- **Waiting for:** Codex: those PRs and the round-2 reviews (#9, #10). Gemini: PR for #16.
- **Last finished (2026-09-17):** Health and Finance PRDs v0.2; simulator spec amended with RB §8.3 probe endpoints; test strategy v0.1; Vault PRD v0.2.
- **Next:** nothing queued that does not need Codex; candidates: Core PRD v2.3 touch-ups found along the way (§5.4 wording, visibility), golden utterance set draft, threat model outline.

## Codex (`agent:codex`)

- **Working on:** #9 (WP-09) Module Registry v1.1 round-2 review, then #10 (WP-10) Data Model v1.3 and Consent Manager §2.6 review. Findings only on the issues; no spec edits.
- **Waiting for:** —
- **Last finished:** —

## Gemini in Antigravity (`agent:gemini`)

- **Working on:** #16 (WP-16) cross-reference sweep tool (`tools/xref_check.py`, branch `agent-gemini/issue-16`). PR #26 review changes pushed.
- **Waiting for:** Claude re-review on PR #26.
- **Last finished:** PR #19 merged (WP-47: local-model delegation harness).


## Founder

- **Doing:** workstation setup (#1): WSL 2 and Docker Desktop installed and verified 2026-09-17; remaining: first prompts to Codex and Gemini.
- **Rulings pending:** none (2026-09-17 batch closed; see `coordination/inbox/founder/done/`).
