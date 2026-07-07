# 🧭 Walmart Agentic Compass

A governed, read-only, multi-agent advisor that guides Walmart executives and
technology professionals through adopting enterprise AI agents *the right way*
— grounded in the Google × Kaggle 5-Day Agentic Engineering program and a
Walmart strategic brief. **The agent is built the way it teaches you to
build:** skills library, read/draft/act tier enforcement, evaluation-driven
development, token circuit breaker, MCP tooling, ADK multi-agent orchestration.

> Independent capstone project for the Kaggle "AI Agents: Intensive Vibe
> Coding" Capstone (Agents for Business track). Not affiliated with Walmart Inc.

## Architecture

```
User ──▶ FastAPI (rate limit + daily circuit breaker)
              │ SSE
              ▼
     compass_orchestrator (ADK, gemini-2.5-flash)   ← guardrail tripwire on every agent
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

## Quickstart (local)

```bash
pip install -r requirements.txt
# 1. Put the 6 source PDFs into corpus/  (Day 1–4 whitepapers + Walmart brief + capstone doc)
python scripts/build_index.py           # ~30s, writes corpus_index/chunks.json
# 2. Run
export GOOGLE_API_KEY=your_ai_studio_key   # free tier works
python main.py                          # open http://localhost:8080
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

## Deploy to Cloud Run

```bash
gcloud run deploy agentic-compass --source . --region us-central1 \
  --allow-unauthenticated --max-instances 1 --min-instances 0 \
  --set-env-vars GOOGLE_API_KEY=YOUR_KEY,DAILY_REQUEST_CAP=300
```

The public endpoint is protected by a **financial circuit breaker** (per-IP
rate limit + global daily cap) — the token-spend ceiling this agent teaches
(Walmart brief §5A) also protects the deployment.

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
- **Corpus files:** not committed (size/licensing); add the PDFs locally and
  run the indexer.
