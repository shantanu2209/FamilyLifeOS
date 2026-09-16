# FamilyLifeOS

An India-first, agentic family operating system: a digital Chief of Staff for a household, built natively on India's Digital Public Infrastructure (Account Aggregator, BBPS, ABHA/ABDM, DigiLocker, ONDC, Bhashini). Specialised worker agents are orchestrated by a Supervisor state machine; the family, not the individual, is the atomic unit.

**Status (September 2026):** documentation only, pre-development. Portfolio-first scope: the kernel and one end-to-end bill-payment slice against DPI simulators. The strategy blueprint, the Core PRD, the Supervisor state machine spec and the NFR spec are canonical; four of the five Priority-0 technical specifications are frozen and the fifth (Module Registry) is in draft. The next milestone is the Phase 1 Build Gate described in the project tracker.

## Working here

Start with [AGENTS.md](AGENTS.md). It is the single set of instructions for humans and for every AI agent (Claude Code, Codex, others) and lists the reading order, the non-negotiable invariants, the technology decisions and the known gaps.

## Documents

| Area | Path | Status |
|---|---|---|
| Blueprint | [docs/strategy/Master_Context.md](docs/strategy/Master_Context.md) | v2.0, canonical |
| Vision white paper | [docs/strategy/Vision_Journey.md](docs/strategy/Vision_Journey.md) | Reference (Jan 2026) |
| Master PRD | [docs/strategy/Master_PRD.md](docs/strategy/Master_PRD.md) | v2.1 reference (Jan 2026) |
| Core PRD | [docs/strategy/PRD_FamilyLifeOS_Core.md](docs/strategy/PRD_FamilyLifeOS_Core.md) | v2.1, canonical |
| Vision parking lot | [docs/strategy/Vision_Parking_Lot.md](docs/strategy/Vision_Parking_Lot.md) | v2.0 reference |
| Supervisor state machine | [docs/specs/Tech_Spec_Supervisor_State_Machine.md](docs/specs/Tech_Spec_Supervisor_State_Machine.md) | v2.1, canonical |
| Non-functional requirements | [docs/specs/NFR_Specs.md](docs/specs/NFR_Specs.md) | v2.1, canonical |
| Data model | [docs/specs/Data_Model_Schema.md](docs/specs/Data_Model_Schema.md) | Frozen v1.2.1 |
| Financial transaction safety | [docs/specs/Tech_Spec_Financial_Transaction_Safety.md](docs/specs/Tech_Spec_Financial_Transaction_Safety.md) | Frozen v1.1 |
| Consent manager | [docs/specs/Tech_Spec_Consent_Manager.md](docs/specs/Tech_Spec_Consent_Manager.md) | Frozen v1.1 |
| Module registry | [docs/specs/Tech_Spec_Module_Registry.md](docs/specs/Tech_Spec_Module_Registry.md) | Draft v1.0 |
| DPI rate limits runbook | [docs/runbooks/Runbook_DPI_Rate_Limits.md](docs/runbooks/Runbook_DPI_Rate_Limits.md) | Frozen v1.1 |
| DPI integration primer | [docs/reference/DPI_Integration_Primer.md](docs/reference/DPI_Integration_Primer.md) | Reference (Jan 2026) |
| PRD template | [docs/templates/PRD_Template.md](docs/templates/PRD_Template.md) | Template |
| Project tracker | [docs/PROJECT_TRACKER.md](docs/PROJECT_TRACKER.md) | Living |

All foundational documents are in the repository as of 2026-09-16; the Core PRD, Supervisor State Machine spec, NFR spec and Vision Parking Lot were recovered from the claude.ai project. The only referenced document not yet written is the Security Threat Model. See AGENTS.md §3.1.

## Tools

`tools/docx2md.py` converts a Word document to Markdown (headings, lists, tables, code boxes as fenced blocks, callouts as quotes). It is what produced the files under `docs/` and is the way to bring any future Word document into the repository. Standard library only, no dependencies.

## Archive

`archive/` (not in this repository; it lives only on the founder's machine and is gitignored) holds every file as it was before the September 2026 consolidation: the Word documents, superseded spec versions, duplicate text exports, AI review notes and the raw claude.ai exports. Everything current was carried into `docs/`.
