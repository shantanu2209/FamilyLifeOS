# FamilyLifeOS

An India-first, agentic family operating system: a digital Chief of Staff for a household, built natively on India's Digital Public Infrastructure (Account Aggregator, BBPS, ABHA/ABDM, DigiLocker, ONDC, Bhashini). Specialised worker agents are orchestrated by a Supervisor state machine; the family, not the individual, is the atomic unit.

**Status:** specifications and plans, no application code yet. Portfolio-first scope: the kernel and one end-to-end bill-payment slice against DPI simulators, then a second slice for a managed profile's medication reminders. Where the project stands today: [project tracker → Current state](docs/PROJECT_TRACKER.md). What is being worked on: the [project board](https://github.com/users/shantanu2209/projects/2).

## Working here

Start with [AGENTS.md](AGENTS.md). It is the single set of instructions for humans and for every AI agent (Claude Code, Codex, Gemini in Antigravity) and lists the reading order, the non-negotiable invariants, the technology decisions and the known gaps. [coordination/README.md](coordination/README.md) is the working protocol: issues, labels, branches, cross-agent reviews, a status file and per-agent inboxes. The three agents' roles are in both (AGENTS.md §6).

## Documents

[docs/INDEX.md](docs/INDEX.md) lists every document with its version, state and last change. It is generated from the documents' own headers, so it is the one list that cannot drift. Starting points:

| For | Read |
|---|---|
| What the product is and why | [Master Context](docs/strategy/Master_Context.md), [Core PRD](docs/strategy/PRD_FamilyLifeOS_Core.md) |
| How it must behave | [docs/specs/](docs/specs/) and [docs/runbooks/](docs/runbooks/), starting with the [Data Model](docs/specs/Data_Model_Schema.md) |
| The order of work | [Roadmap](docs/strategy/Roadmap.md) (phases, gates, milestones) and [Execution Plan](docs/Execution_Plan.md) (work packages) |
| Decisions, open gaps, the Build Gate | [Project tracker](docs/PROJECT_TRACKER.md) |
| How the agents work together | [coordination/README.md](coordination/README.md), [STATUS](coordination/STATUS.md) |
| Setting up a machine | [Workstation setup](docs/reference/Workstation_Setup.md) |

All foundational documents are in the repository as of 2026-09-16; the Core PRD, Supervisor State Machine spec, NFR spec and Vision Parking Lot were recovered from the claude.ai project. The only referenced document not yet written is the Security Threat Model. See AGENTS.md §3.1.

## Tools

`tools/docx2md.py` converts a Word document to Markdown (headings, lists, tables, code boxes as fenced blocks, callouts as quotes). It is what produced the files under `docs/` and is the way to bring any future Word document into the repository. Standard library only, no dependencies.

`tools/agent-local.ps1` and `tools/codex-config.example.toml` are an optional manual harness for running a local Ollama model through Codex CLI. Local models are not part of the agent roster; Gemini orchestrates them inside Antigravity (AGENTS.md §6). What to install on the PC: [docs/reference/Workstation_Setup.md](docs/reference/Workstation_Setup.md).

`tools/docs_index.py`, `tools/living_docs_check.py` and `tools/board_sync.py` keep the living documents honest: the first generates `docs/INDEX.md`, the second fails the build when status or plans are duplicated or go stale, the third sets the project board from issue state and labels.

## Archive

`archive/` (not in this repository; it lives only on the founder's machine and is gitignored) holds every file as it was before the September 2026 consolidation: the Word documents, superseded spec versions, duplicate text exports, AI review notes and the raw claude.ai exports. Everything current was carried into `docs/`.
