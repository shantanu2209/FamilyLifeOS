# Status

Who is working on what, right now. One section per agent; **edit only your own section**. Keep it to a few lines: current item (issue, branch), what you are waiting for, last finished item. Update it when you pick something up and when you stop. Commit with a `coord:` subject straight to `main` (`coordination/README.md` §5).

## Claude Code (`agent:claude`)

- **Working on:** nothing in flight. All 60 findings of Codex's reviews of 2026-09-21 are answered in one stacked chain: PR #30 (WP-11: Data Model v1.4, Consent Manager v1.4, Module Registry v1.2, FTS v1.3) → #22 (Vault PRD v0.3) → #25 (Health and Finance PRDs v0.3) → #32 (simulator spec v0.2; PR #20 had merged v0.1 before the findings were applied) → #23 (test strategy v0.2). `docs` check green on all five.
- **Waiting for:** Codex's targeted re-review of that chain (message in `coordination/inbox/codex/`). Then the founder merges in chain order; after each merge Claude rebases the next link onto `main` and re-runs the checks before saying it is ready.
- **Last finished (2026-09-21):** the batch above; four founder rulings recorded in the Decision Log (inside PR #30); register items 19–27.
- **Next:** respond to the re-review; then the threat model outline (WP-42 preparation), which now has a concrete list: break-glass access, separated parents, who consents for elder and passive holders (Vault OI-10), the gateway's credential boundary (SIM OI-1), signed webhooks (SIM OI-3), free text in the override audit row (register item 26).

## Codex (`agent:codex`)

- **Working on:** nothing in flight; the requested review queue is complete. #5 and #6 were not started.
- **Waiting for:** Claude's WP-11 spec corrections and revisions to PRs #22, #25, #20 and #23, then targeted re-review before freeze/implementation.
- **Last finished (2026-09-21):** #9, #10, #22, #25, #20, #23 reviewed in order; each changes-required verdict is posted with numbered, section-linked findings. All handoffs sent and Codex inbox messages archived.

## Gemini in Antigravity (`agent:gemini`)

- **Working on:** —
- **Waiting for:** Next assignment from the founder.
- **Last finished:** PR #26 merged (WP-16: cross-reference sweep tool); PR #28 and PR #29 reviewed.


## Founder

- **Doing:** workstation setup (#1): WSL 2 and Docker Desktop installed and verified 2026-09-17; remaining: first prompts to Codex and Gemini.
- **Rulings pending:** none (2026-09-17 batch closed; see `coordination/inbox/founder/done/`).
