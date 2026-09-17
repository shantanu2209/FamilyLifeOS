# Status

Who is working on what, right now. One section per agent; **edit only your own section**. Keep it to a few lines: current item (issue, branch), what you are waiting for, last finished item. Update it when you pick something up and when you stop. Commit with a `coord:` subject straight to `main` (`coordination/README.md` §5).

## Claude Code (`agent:claude`)

- **Working on:** nothing in flight.
- **Last finished (2026-09-17):** reviewed PR #17 for Gemini (Codex unavailable): approve, ready for the founder to merge. Added WP-47 (issue for Gemini's local-model harness), the stage-by-path rule and the fallback-reviewer rule.
- **Waiting for:** Codex's return for the round-2 reviews (#9, #10); the founder's `gh auth refresh -s project` for the GitHub Projects board.
- **Next:** WP-12 `Tech_Spec_Simulator_Architecture.md` draft; Vault PRD v0.2 with the `visibility` attribute.

## Codex (`agent:codex`)

- **Working on:** #9 (WP-09) Module Registry v1.1 round-2 review, then #10 (WP-10) Data Model v1.3 and Consent Manager §2.6 review. Findings only on the issues; no spec edits.
- **Waiting for:** —
- **Last finished:** —

## Gemini in Antigravity (`agent:gemini`)

- **Working on:** #18 (WP-47) local-model delegation harness (branch `agent-gemini/issue-18`).
- **Waiting for:** —
- **Last finished:** PR #17 merged (WP-02: docstrings and lint pass on `tools/docx2md.py`).


## Founder

- **Doing:** workstation setup (#1): WSL 2 and Docker Desktop installed and verified 2026-09-17; remaining: first prompts to Codex and Gemini.
- **Rulings pending:** none (2026-09-17 batch closed; see `coordination/inbox/founder/done/`).
