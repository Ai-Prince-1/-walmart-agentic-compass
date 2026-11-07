# 🧭 Walmart Agentic Compass

### 🔗 Project page: **https://ai-prince-1.github.io/-walmart-agentic-compass/**
Try the governance scorecard in your browser, and open the live agent from the same page when it's running.

A governed, read-only, multi-agent advisor that guides Walmart executives and
technology professionals through adopting enterprise AI agents *the right way*
— grounded in the Google × Kaggle 5-Day Agentic Engineering program and a
Walmart strategic brief I created based on the white papers shared in the program. **The agent is built the way it teaches you to
build:** skills library, read/draft/act tier enforcement, evaluation-driven
development, token circuit breaker, MCP tooling, ADK multi-agent orchestration.

> Independent capstone project for the Kaggle "AI Agents: Intensive Vibe
> Coding" Capstone (Agents for Business track). Not affiliated with Walmart Inc.

![tests](https://github.com/Ai-Prince-1/-walmart-agentic-compass/actions/workflows/tests.yml/badge.svg)

## How it works (plain English)

| Layer | What it is | In this project |
|---|---|---|
| **1. Knowledge (data)** | A searchable index built from PDFs | The Google × Kaggle agent-engineering whitepapers and a Walmart strategy brief, chunked into `corpus_index/chunks.json`. Answers cite source and page. |
| **2. Reasoning (the middle)** | A Python app using Google's Agent Development Kit (ADK) and the Gemini 2.5 Flash-Lite model | A router agent sends each question to one of three specialists. They call read-only tools (corpus search, readiness scorecard) served over MCP. Guardrails screen input and cap spend. |
| **3. Interface (front end)** | Two web pages | The **live agent**: a chat page served by the same FastAPI app on Google Cloud Run, which sleeps when idle. The **project page**: a static showcase on GitHub Pages (`docs/`), with the scorecard running in the browser. |

The Gemini API key is stored in Google Secret Manager and injected at runtime. It never appears in the code, the repo or the browser.

## What this demonstrates

| Skill | Where |
|---|---|
| Multi-agent orchestration (Google ADK): one router, three specialists | `compass/agent.py` |
| Tool design + MCP server (FastMCP, stdio) | `mcp_server/server.py` |
| Governance by architecture: read-only tools only, fail-closed scorecard | `mcp_server/server.py`, `compass/guardrails.py` |
| Cost controls: per-visitor rate limit + daily request cap | `main.py` |
| Evaluation-driven development: trajectory checks + position-swapped LLM judge | `evals/` |
| Automated tests that run without an API key (CI on every push) | `tests/`, `.github/workflows/tests.yml` |

## Architecture

```
User ──▶ FastAPI (rate limit + daily circuit breaker)
              │ SSE
              ▼
     compass_orchestrator (ADK, gemini-2.5-flash-lite)   ← guardrail tripwire on every agent
       ├── curriculum_mentor    ── search_corpus ──┐
       ├── strategy_advisor     ── search_corpus ──┤── corpus_index/chunks.json
       └── governance_auditor   ── readiness_scorecard  (deterministic ladder logic)
                                    ▲
                 mcp_server/server.py (FastMCP, stdio) exposes both tools over MCP
```

- Each sub-agent loads **only its own SKILL.md** (progressive disclosure —
  the Day 3 principle behind the documented ~98% token reduction). The
  orchestrator sees only the routing trigger blocks.
- Every SKILL.md carries **3 positive + 3 negative triggers** (Day 3's
  routing-accuracy requirement).
- **Zero ambient authority:** no action tools exist anywhere in this codebase.
  The read-only tier is enforced by capability absence, not by prompt.
- A pre-built index (`corpus_index/chunks.json`) is included, so the app runs
  without the PDFs. You only need them to rebuild the index.

## Quickstart (local)

```bash
pip install -r requirements.txt
export GOOGLE_API_KEY=your_ai_studio_key   # free tier works
python main.py                             # open http://localhost:8080
```

Optional: to rebuild the search index, add the course PDFs to `corpus/`
(see `corpus/README.md`) and run `python scripts/build_index.py` (~30s).

## Tests (no API key needed)

```bash
pip install -r requirements-dev.txt
pytest -q          # corpus search, scorecard, guardrails, rate limits, web app
```

## Evaluation (Evaluation-Driven Development)

The 9 eval cases in `evals/cases.json` were written **before** the skills —
per Day 3's EDD workflow. The runner is trajectory-aware (checks which
sub-agent and tool actually ran, not just the output — Day 3 documents that
output-only scoring passes 20–40% more false positives) and uses
LLM-as-judge with **position-swapped double judging** to eliminate ordering
bias.

```bash
python evals/run_evals.py    # gate: ≥8/9
```

## MCP server (standalone)

```bash
python mcp_server/server.py     # stdio MCP server: search_corpus + readiness_scorecard
```

## Live demo hosting (about $0 a month)

| Piece | Where | Cost |
|---|---|---|
| Project page | GitHub Pages, from `docs/` | Free |
| Live agent | Google Cloud Run: 0 minimum instances (sleeps when idle), 1 maximum (caps spend) | Free tier covers demo traffic |
| Model | Gemini API free tier, using a key from a Google project **without billing**, so it can't incur charges | Free |
| Key storage | Google Secret Manager | Free tier |
| Monthly check | GitHub Actions wakes the agent and asks one question. If it fails, GitHub emails you. | Free |

**One-time setup (about 15 minutes):**
1. Create a Gemini API key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey). Keys don't expire, so there's nothing to refresh monthly.
2. Open [Google Cloud Shell](https://shell.cloud.google.com), select a project with billing enabled (Cloud Run requires it; set a $1 budget alert), then run:
   ```bash
   git clone https://github.com/Ai-Prince-1/-walmart-agentic-compass.git
   cd -- -walmart-agentic-compass && bash deploy/cloudrun.sh
   ```
   The script asks for the key (input is hidden) and, optionally, a demo passcode. It stores both in Secret Manager and prints your live URL.
3. In this repo, open **Settings → Secrets and variables → Actions**:
   - Add a variable `COMPASS_LIVE_URL` set to the printed URL.
   - If you set a passcode, also add a secret `COMPASS_DEMO_PASSCODE`.
4. Paste the same URL into `docs/config.js`, which turns on the "Talk to the live agent" button on the project page.

**Before a demo:** open the live URL a minute early so it's awake. To check on demand, go to **Actions → Monthly live demo check → Run workflow**.

## Kaggle concept checklist

| Course concept | Where demonstrated |
|---|---|
| Multi-agent system (ADK) | `compass/agent.py` — orchestrator + 3 sub-agents |
| MCP Server | `mcp_server/server.py` (FastMCP, standalone runnable) |
| Antigravity | Build/iteration process shown in the video |
| Security features | Zero-ambient-authority tier, `compass/guardrails.py` tripwire + audit log, circuit breaker in `main.py`, live governance sidebar |
| Deployability | `Dockerfile` + Cloud Run deploy (video) |
| Agent skills | `compass/skills/*/SKILL.md` (Day 3 trigger format) + EDD evals |

## Honest limitations (by design, documented per Day 4's own discipline)

- **Search:** scored keyword matching over a closed, trusted corpus — not
  embeddings. A closed corpus is also the mitigation for RAG-poisoning
  (Pillar 2); production RAG would need ingestion defenses.
- **MCP:** the server is a genuine, standalone MCP server, but the agents
  import its functions natively at runtime for single-container robustness on
  Cloud Run. Production MCP would add contextual authorization and server
  identity verification against MCP spoofing (Day 4).
- **Guardrail filters:** the regex tripwire is defense-in-depth and an
  observability signal — Day 4 is explicit that static filters are not a
  perimeter. The perimeter here is architectural: no action tools exist.
- **Sessions:** in-memory; reset on Cloud Run cold starts. Fine for a demo.
- **Corpus files:** the course whitepaper PDFs are not committed; add them
  locally to rebuild the index. The committed index does contain text
  extracted from them so the demo runs out of the box. The strategic brief
  PDF (my own document) is committed.
- **Guardrail false positives:** the secrets pattern also trips on honest
  questions that mention "credentials" or "API keys". It's a deliberate
  over-block for a public demo.
