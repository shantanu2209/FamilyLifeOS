# Local Agent Setup (Ollama + Codex CLI on Windows)

> **Status:** GUIDE — written 2026-09-17 for the founder's machine · **Owner:** Alfred
> **Purpose:** Run a local model as the fourth agent in the roster (see `AGENTS.md` §6 and the tracker's Decision Log) so that routine, instruction-following work does not consume Claude or Codex usage. Doubles as a learning exercise in coordinating cloud and local agents.
> **Verified against:** Ollama library pages, the ChatGPT Learn Codex configuration reference, Ollama's FAQ and Codex blog post, the Aider Ollama docs, and 2026 hands-on reports, all fetched on 2026-09-17. Speeds quoted for other people's hardware are marked as such; measure your own with the smoke tests in §6.

---

## 1. The machine

| Component | Value | What it means for local models |
|---|---|---|
| GPU | NVIDIA GeForce RTX 3070 Ti, 8 GB VRAM, driver 580.88, compute 8.6 | About 6.9 GB is actually free; the Windows desktop holds ~1.2 GB. A model plus its KV cache must fit in that to stay fully on the GPU. |
| CPU | Intel i7-12700F, 12 cores / 20 threads | Good enough to run the CPU share of a mixture-of-experts model. |
| RAM | 64 GB (46 GB free at rest) | The important number. Models larger than the GPU spill into RAM; with a small active-parameter MoE model that is still usable. |
| Disk | C: 1.4 TB free, D: 1.7 TB free | No constraint. Point `OLLAMA_MODELS` at D: if you want models off C:. |
| Installed | Ollama 0.34.1 (no models pulled yet), Node.js/npm, Python 3.10, uv | Codex CLI, Aider and Docker are **not** installed. |

---

## 2. Model recommendation

### 2.1 Everyday local model: `qwen3.5:9b`

- 9.65 B dense, Q4_K_M, **6.6 GB** download, capability badges **tools, thinking, vision**, Apache-2.0.
- Measured on an RTX 3070 (same 8 GB class): ~59 tokens/s fully on the GPU at 4K context, 6.8 GB peak VRAM. On this machine, with the desktop holding 1.2 GB and a 16K context, expect a small share of layers on the CPU and roughly 25–40 tokens/s. Still the fastest capable option.
- This is the model for the local agent's job: formatting, docstrings, lint fixes, generated boilerplate, fixture generation, tracker status sync, PR summaries. Anything with a script or test that verifies the result.

### 2.2 Optional heavier local model: `qwen3.6:35b`

- Mixture-of-experts, 35.5 B total with ~3 B active per token, Q4_K_M, **23 GB** download, badges tools, thinking, vision, Apache-2.0. The Qwen 3.6 generation is where Alibaba added "substantial upgrades in agentic coding".
- It cannot fit the GPU; Ollama splits it across GPU and the 64 GB RAM automatically. Because only ~3 B parameters are active per token, that split is usable: reports on comparable setups range from 12 tokens/s (CPU-heavy) to 30+ tokens/s (expert offload tuned). Treat 10–20 tokens/s as the planning assumption until measured.
- Use it for local tasks that need more judgement than the 9B can give but are not worth Claude or Codex usage. Known weaknesses from hands-on reports: occasional identifier hallucination, weaker than the 27B dense model on skills benchmarks.

### 2.3 What was considered and rejected

| Model | Why not (for the agent role) |
|---|---|
| **Gemma 4** (E2B / E4B / 12B / 26B-A4B / 31B, Apr 2026) | Native function calling, strong at maths, vision and 140+ languages. But a May 2026 hands-on comparison found it "refuses to use MCP tools even when asked" and "gets stuck in loops requiring human intervention", and it trails the Qwen 3.6 family by a wide margin on SWE-bench-style work. The 12B Q4 (7.6 GB) would also spill on this GPU. Keep it in mind only for a later multilingual chore such as Hindi UX strings, with a human checking output. |
| **qwen3-coder:30b** (30B-A3B, 19 GB) | Good agentic coder, but superseded by the Qwen 3.6 MoE at the same cost, and there is no sub-10 GB tag. |
| **qwen3.6:27b / qwen3.8:27b** (dense, 18 GB) | Best open-weight coding quality (Qwen 3.6-27B: 77.2 % SWE-bench Verified), but a dense 27B split across CPU and an 8 GB GPU runs at single-digit tokens/s. Not practical here. |
| **gpt-oss:20b** (14 GB, MoE 3.6 B active) | Codex CLI's default local model and the one its harness is tuned for. Runs only with CPU offload on 8 GB; guides for this GPU class advise against it. Worth a single smoke test **only if** `qwen3.5:9b` proves unreliable at Codex's tool protocol. |
| **qwen2.5-coder:7b** | Still widely recommended for 8 GB cards and fine for autocomplete, but it predates the tool-calling and agent training of the 3.5/3.6 generation. |

---

## 3. Harness: Codex CLI for both cloud and local

Why one harness: Codex CLI reads `AGENTS.md` natively, has had native Windows support since March 2026 (PowerShell plus a Windows sandbox), talks to Ollama through the `--oss` flag or a configured provider, and has a non-interactive `codex exec` mode for scripted runs. One tool to learn, two backends. Aider (§8) is the fallback if the small model struggles with Codex's tool-calling protocol.

---

## 4. Step-by-step setup

### Step 1 — Configure Ollama (one-off)

Ollama's default context window is 4,096 tokens, far too small for agent loops. Set these **user environment variables** (Settings → search "environment variables" → "Edit environment variables for your account"), or from PowerShell:

```powershell
setx OLLAMA_CONTEXT_LENGTH 16384
setx OLLAMA_KV_CACHE_TYPE q8_0
setx OLLAMA_FLASH_ATTENTION 1
setx OLLAMA_KEEP_ALIVE 30m
setx OLLAMA_NUM_PARALLEL 1
# optional: keep the model store on D:
setx OLLAMA_MODELS D:\ollama\models
```

Then quit Ollama from the tray icon and start it again so the variables apply.

What they do: `q8_0` halves the KV-cache memory with negligible quality loss, which is what lets 16K context fit next to a 6.6 GB model; flash attention is normally auto-enabled but forcing it avoids surprises; keep-alive stops the model unloading between tool calls; one parallel request keeps VRAM for context. Codex's own recommendation is 32K context; start at 16K, and raise to 32K only if tasks run out of room and `ollama ps` still shows most layers on the GPU.

Check the server is up:

```powershell
curl.exe http://localhost:11434/v1/models
```

### Step 2 — Pull the models

```powershell
ollama pull qwen3.5:9b        # 6.6 GB
ollama pull qwen3.6:35b       # 23 GB, optional heavy model
```

Quick sanity check and a look at the GPU/CPU split:

```powershell
ollama run qwen3.5:9b "Reply with the single word OK"
ollama ps
```

`ollama ps` shows something like `100% GPU` or `18%/82% CPU/GPU`. The second number is the share on the GPU; the more that is on the CPU, the slower generation gets.

### Step 3 — Install Codex CLI (native Windows)

Node.js 22 or newer is required. The package is `@openai/codex`; the unscoped `codex` package on npm is an unrelated project.

```powershell
node --version
npm install -g @openai/codex
codex --version
codex login          # cloud account, for the Codex-cloud agent role; not needed for local runs
```

### Step 4 — Configure Codex profiles

Copy `tools/codex-config.example.toml` to `C:\Users\shant\.codex\config.toml` (create the folder if needed). It defines:

- the default (cloud) behaviour,
- an `ollama` model provider pointing at `http://localhost:11434/v1` with `wire_api = "responses"` (the only value current Codex supports),
- a `local` profile on `qwen3.5:9b` with a 16K context window,
- a `local-heavy` profile on `qwen3.6:35b` with a 32K context window,
- the project trust entry for `D:\FamilyLifeOS` so `codex exec` can run without a prompt,
- `project_doc_max_bytes` raised so the whole of `AGENTS.md` is read.

Two ways to run locally:

```powershell
codex --oss -m qwen3.5:9b            # quick interactive, built-in ollama provider
codex --profile local                 # same, via the profile (context window, approvals set)
```

Never run bare `codex --oss` without `-m`: it defaults to `gpt-oss:20b` and will start a 14 GB download.

### Step 5 — Trust the project once

Run `codex` interactively inside `D:\FamilyLifeOS` once and accept the trust prompt, or rely on the `[projects]` entry in the config. Codex loads project-scoped config only for trusted projects.

---

## 5. How the local agent works inside this project

- **Instructions:** it reads `AGENTS.md` like every other agent. Its permitted scope is listed there under "Local agent". In short: mechanical, verifiable work; never the frozen specs, never the payment, consent or audit code paths, never `AGENTS.md` itself, never merging.
- **Task intake:** GitHub issues labelled `agent:local`. The launcher `tools/agent-local.ps1` reads the issue, creates a branch `agent-local/issue-<n>`, runs `codex exec` with the `local` profile and `workspace-write` sandbox, commits, pushes, and opens a PR labelled `agent:local` and `needs-review`.
- **Review:** a different agent (Claude Code or Codex cloud) reviews every local PR before merge. No self-merge.
- **Non-interactive semantics:** in `codex exec` there is no TTY, so approvals are `never`; the sandbox limits writes to the repo and blocks network. Anything that needs judgement or approval is a sign the task was mis-assigned.

Usage:

```powershell
# work an issue end to end
.\tools\agent-local.ps1 -Issue 12

# ad-hoc task, heavy model, no PR (leaves you on the branch)
.\tools\agent-local.ps1 -Task "Add docstrings to tools/docx2md.py" -Profile local-heavy -NoPR
```

---

## 6. Smoke tests (do these before assigning real work)

Run from `D:\FamilyLifeOS` with the model loaded. They test the three things that vary most across local models in Codex: reading files, editing files, running commands.

```powershell
# 1. Read-only
codex exec --profile local "Read docs/PROJECT_TRACKER.md and list its top-level section headings as a bullet list."

# 2. Edit (on a scratch branch)
git checkout -b scratch/local-smoke
codex exec --profile local --sandbox workspace-write "Add a module-level docstring to tools/docx2md.py that explains usage: python tools/docx2md.py input.docx output.md [heading_shift]. Do not change behaviour."
git diff --stat

# 3. Command execution
codex exec --profile local --sandbox workspace-write "Run: python tools/docx2md.py  (with no arguments) and report the exact error message it prints."

git checkout main; git branch -D scratch/local-smoke
```

While a test runs, in another terminal: `ollama ps` for the GPU/CPU split, and watch the Ollama log (tray icon → View logs) for `eval rate` lines, which give tokens per second. Record the numbers in the tracker's Decision Log row for the local agent.

Pass criteria: test 1 returns real headings; test 2 produces a clean diff that only adds a docstring; test 3 reports the real argparse/IndexError message. If test 2 or 3 fails twice with `qwen3.5:9b`, try the same with `--profile local-heavy`; if that also fails, switch the harness to Aider (§8) before spending more time.

---

## 7. Tuning and troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Generation under ~5 tokens/s on the 9B | Too many layers on the CPU; usually context too large for free VRAM | Close GPU-heavy apps, lower `OLLAMA_CONTEXT_LENGTH` to 8192, confirm `OLLAMA_KV_CACHE_TYPE=q8_0` took effect (restart Ollama). |
| `CUDA out of memory` | Model + KV cache exceeds free VRAM | Same as above, or use `qwen3.5:4b` (3.4 GB) for the smallest tasks. |
| Codex says the model does not support tools, or edits come back as prose | Model or template lacks tool calling | Confirm the tag has the `tools` badge; try `local-heavy`; then Aider. |
| Codex stalls at start in `exec` mode | Project not trusted or approval needed | Add the `[projects]` entry, or run `codex` interactively once and accept trust. |
| Agent loops or repeats itself | Context overflow | Raise context to 32K (accepting CPU spill) or split the task. |
| Task quality poor | Wrong tier of work | Route to Gemini Flash or Codex cloud; the local model is for mechanical tasks only. |

---

## 8. Fallback harness: Aider

Aider is more tolerant of weaker models because its edit formats do not depend on native tool calling, and it is git-aware.

```powershell
python -m pip install aider-install
aider-install
setx OLLAMA_API_BASE http://127.0.0.1:11434
# new terminal, inside the repo
aider --model ollama_chat/qwen3.5:9b
```

Aider auto-sizes the Ollama context to the request plus 8K for the reply; to pin it, create `.aider.model.settings.yml` in the repo:

```yaml
- name: ollama_chat/qwen3.5:9b
  extra_params:
    num_ctx: 16384
```

Aider does not read `AGENTS.md` automatically; add it with `/read-only AGENTS.md` at the start of a session or via `--read AGENTS.md`.

---

## 9. Not yet in place

- **Docker** is not installed. The Phase 1 Build Gate needs PostgreSQL, Redis and WireMock in Docker Compose; install Docker Desktop with the WSL 2 backend before that work starts.
- **Gemini / Antigravity** and the cloud Codex login are the founder's to set up; their roles are defined in `AGENTS.md`.
- Measured tokens/s for both local profiles on this machine: fill in after the smoke tests.
