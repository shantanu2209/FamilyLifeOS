# Workstation Setup (founder's PC)

> **Status:** GUIDE — written 2026-09-17 from a check of the actual machine · **Owner:** Shantanu Chaudhary
> **Purpose:** Everything that has to be installed or signed in to on the founder's Windows 11 PC before the three agents (Claude Code, Codex, Gemini in Antigravity) can work on this repository and before the Build Gate infrastructure can run. This is Execution Plan WP-01. A fuller developer guide (`Development_Environment_Setup.md`, WP-14) follows once there is code to run.
> **Related:** `docs/reference/Local_Agent_Setup.md` (model choice and Ollama tuning), `coordination/README.md` (how the agents work together).

---

## 1. What the machine has today (checked 2026-09-17)

| Item | State | Action |
|---|---|---|
| Windows 11 Home 26200, i7-12700F, 64 GB RAM, RTX 3070 Ti 8 GB | — | — |
| Git 2.55, GitHub CLI 2.97 (signed in as `shantanu2209`) | ✅ installed | none |
| Node.js v24.19 / npm | ✅ installed | none (needed later for `web/`) |
| uv 0.12.9 | ✅ installed | none |
| Python | 3.10.11 (the project uses 3.12) | none: uv downloads 3.12 by itself the first time the project is synced; 3.10 stays untouched |
| Ollama 0.34.1 | ✅ installed, **no models pulled** | optional (step 5) |
| Google Antigravity | ✅ installed at `D:\Antigravity` | sign in, open the repo (step 4) |
| WSL 2 | ❌ **not installed** | step 1 |
| Docker Desktop | ❌ not installed | step 2 |
| Codex desktop app | ✅ the founder has it | open the repository in it (step 3). The Codex CLI is **not** needed |
| VS Code | not found | not needed; Antigravity is the editor |

Order matters only for steps 1 → 2 (Docker Desktop needs WSL 2). Steps 3–5 are independent of each other.

---

## 2. Steps

### Step 1 — WSL 2 (needs one reboot)

Docker Desktop on Windows 11 Home runs on the WSL 2 backend. In an **administrator** PowerShell:

```powershell
wsl --install
```

This enables the Virtual Machine Platform and WSL features and installs Ubuntu. **Reboot** when it asks. After the reboot an Ubuntu window opens and asks you to create a Linux username and password (local to WSL; nothing to do with this project). Then check:

```powershell
wsl --status
wsl -l -v
```

Expect "Default Version: 2" and Ubuntu listed with VERSION 2. If `wsl --install` complains about virtualisation, enable Intel VT-x in the BIOS (on 12th-gen Intel boards it is usually on already; Task Manager → Performance → CPU shows "Virtualization: Enabled").

### Step 2 — Docker Desktop

```powershell
winget install -e --id Docker.DockerDesktop
```

Start Docker Desktop once, accept the service agreement yourself (it is free for personal use), keep "Use WSL 2 based engine" ticked, and skip the sign-in (not needed). Then, in a new terminal:

```powershell
docker run --rm hello-world
docker compose version
```

Settings worth changing: **Resources → WSL integration** → enable for Ubuntu; **General** → untick "Start Docker Desktop when you sign in" if you don't want it always running (it takes 2–4 GB of RAM while idle). Nothing in this repository needs Docker until WP-17, but CI parity problems are cheaper to find now.

### Step 3 — Codex desktop app (the second agent)

No install: the founder already uses the Codex desktop app. The Codex CLI was only needed as a harness for a local-model agent, and local models now sit under Gemini in Antigravity.

1. In the Codex app, add `D:\FamilyLifeOS` as a project (local folder). Codex reads `AGENTS.md` by itself.
2. Keep approvals on for commands and for anything outside the folder.
3. First prompt:

   > Read AGENTS.md, coordination/README.md and your inbox at coordination/inbox/codex/. Tell me your role, what you must never do, three invariants from AGENTS.md section 4, and what your first task is. Do not change any files yet.

   If the answer is right, tell it to go ahead with the first task in its inbox (review round 2; findings only, no spec edits).

### Step 4 — Antigravity (the third agent: Gemini)

1. Start Antigravity (`D:\Antigravity`), sign in with your Google account, and update it if it offers to. Since v1.20.3 (March 2026) Antigravity reads `AGENTS.md` natively as well as `GEMINI.md`; this repository has both, and `GEMINI.md` only adds Gemini's role on top.
2. **File → Open Folder → `D:\FamilyLifeOS`.** Trust the workspace.
3. Model: pick the Gemini Flash-class model for everyday work (the role is routine generation; keep the Pro model for the cross-reference sweep, WP-16, if Flash misses things).
4. Agent settings: start in the mode that **asks before running terminal commands and before writing outside the workspace**. Loosen it later if it gets tedious.
5. Git and GitHub work through what is already on the machine (`git`, `gh`). Make sure pushes use the GitHub no-reply address; it is already set for this repository, check with `git config user.email` in the Antigravity terminal.
6. First prompt, in the agent panel:

   > Read GEMINI.md, AGENTS.md, coordination/README.md and your inbox at coordination/inbox/gemini/. Tell me your role, what you must never touch, three invariants from AGENTS.md section 4, and what your first task is. Do not change any files yet.

   If the answer is right, let it do the first task in its inbox (its STATUS lines, then a docstring-only PR on `tools/docx2md.py`).

### Step 5 — Optional: local models for Antigravity to orchestrate

The roster has three agents. Local models are not one of them; Gemini may use them as sub-agents for mechanical subtasks (`coordination/README.md` §1). This step can wait until the three-agent loop works.

```powershell
[Environment]::SetEnvironmentVariable('OLLAMA_CONTEXT_LENGTH','16384','User')
[Environment]::SetEnvironmentVariable('OLLAMA_KV_CACHE_TYPE','q8_0','User')
[Environment]::SetEnvironmentVariable('OLLAMA_FLASH_ATTENTION','1','User')
[Environment]::SetEnvironmentVariable('OLLAMA_KEEP_ALIVE','30m','User')
[Environment]::SetEnvironmentVariable('OLLAMA_NUM_PARALLEL','1','User')
```

Quit Ollama from the system tray and start it again so it picks the variables up, then:

```powershell
ollama pull qwen3.5:9b
ollama run qwen3.5:9b "Reply with OK"
ollama ps
```

`ollama ps` should show the model mostly or fully on the GPU. Why this model, and the optional heavier `qwen3.6:35b`: `Local_Agent_Setup.md` §2.

**How Antigravity reaches it (state of play, September 2026).** Antigravity does not let you swap its core reasoning model for a local one; community proxy patches that do so break with updates and violate Google's terms, so they are not used here. The supported route is a **tool**: an Ollama MCP server added under Antigravity's MCP settings, which Gemini calls to hand a subtask (a docstring pass, a fixture file) to the local model and then checks the result itself. Which MCP server to use is left to the founder's experiment; record the choice in the tracker's Decision Log. The Codex CLI route in `Local_Agent_Setup.md` is a manual fallback only; nothing in the protocol needs it.

### Later, not now

- **Anthropic API key** for the hosted LLM adapter (Claude Haiku is the default hosted model; tracker → Decision Log). Needed at WP-29 (LLM gateway), not before. It goes in a local `.env` that is gitignored, never in the repository.
- **Playwright browsers**, **k6**: installed by the work packages that need them.
- **A cloud account in an India region**: only at the demo deployment (WP-43).

---

## 3. Done when

- [ ] `wsl --status` shows version 2; `docker run --rm hello-world` prints its greeting; `docker compose version` answers.
- [ ] The Codex app has `D:\FamilyLifeOS` open and Codex can state its role, its limits and three invariants.
- [ ] Antigravity opens `D:\FamilyLifeOS` and Gemini can state its role, its limits and three invariants.
- [ ] (Optional) `ollama ps` shows `qwen3.5:9b` loaded.

The labels, milestones and Phase 0–1 issues already exist on GitHub; the agents start from their inboxes and their issues.

Sources for the Antigravity notes (checked 2026-09-17): [Antigravity rules documentation](https://antigravity.google/docs/rules-workflows/), [AGENTS.md support in Antigravity](https://agentpedia.codes/blog/antigravity-agents-md-guide), [local-model support in Antigravity](https://agentpedia.codes/blog/antigravity-local-models-ollama-setup).
