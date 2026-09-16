# Handoff Template

Copy into every PR description (below the template's checklist) and into any comment that hands work from one agent to another.

```markdown
## Handoff

**From:** agent:<claude|codex|gemini|local>   **To:** agent:<reviewer>   **Issue:** #<n> (WP-<id>)

### What changed
- <file or area>: <one line>
- <file or area>: <one line>

### Governing spec sections
- <Doc> §<n> — <what it required>
- <Doc> §<n> — <what it required>

### Verification
- Command/test run: `<command>`
- Result: <pass/fail summary, numbers>
- Not verified: <what could not be checked and why>

### Look here first
- <the riskiest change and why>

### Open questions / follow-ups
- <question or "none">; follow-up issue: #<n> or "not needed"

### Assumptions made
- <assumption> — reversible: yes/no
```

Rules: one line per item, section references not prose, and never claim a verification that was not run.
