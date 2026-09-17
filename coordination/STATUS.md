# Status

Who is working on what, right now. One section per agent; **edit only your own section**. Keep it to a few lines: current item (issue, branch), what you are waiting for, last finished item. Update it when you pick something up and when you stop. Commit with a `coord:` subject straight to `main` (`coordination/README.md` §5).

## Claude Code (`agent:claude`)

- **Working on:** PR #29 (xref tool follow-up: skip generated docs, planned docs read from the tracker, new baseline) waiting for Gemini's review; it turns `main`'s docs check green again.
- **Waiting for:** Gemini: review of #29. Founder: merge #29. Codex: PRs #22, #25, #20, #23 (all rebased onto the restructured main) and the round-2 reviews (#9, #10).
- **Last finished (2026-09-17):** rebased #22, #25, #20, #23; regenerated the index on each.
- **Next:** after #29 merges, a last trivial rebase of the four so their checks go green; then the threat model outline.

## Codex (`agent:codex`)

- **Working on:** #9 (WP-09) Module Registry v1.1 round-2 review, then #10 (WP-10) Data Model v1.3 and Consent Manager §2.6 review. Findings only on the issues; no spec edits.
- **Waiting for:** —
- **Last finished:** —

## Gemini in Antigravity (`agent:gemini`)

- **Working on:** #16 (WP-16) cross-reference sweep tool (`tools/xref_check.py`, branch `agent-gemini/issue-16`). Baseline ratchet added and pushed.
- **Waiting for:** Claude final review / merge on PR #26.
- **Last finished:** PR #28 reviewed (living-documents restructure).


## Founder

- **Doing:** workstation setup (#1): WSL 2 and Docker Desktop installed and verified 2026-09-17; remaining: first prompts to Codex and Gemini.
- **Rulings pending:** none (2026-09-17 batch closed; see `coordination/inbox/founder/done/`).
