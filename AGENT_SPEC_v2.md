# Walmart Agentic Compass — Build Specification v2 (red-teamed)
## Kaggle Capstone (Agents for Business) — Google ADK (Python)

Changes from v1 are marked ⟨V2⟩. Priority: working end-to-end > polish > extras.
Test after each phase. Hard rule: no fix or feature may add >10 min of build time.

---

## 1. WHAT THIS IS

A governed multi-agent advisor guiding Walmart executives and tech professionals
through adopting agentic AI the right way, grounded in the Google × Kaggle 5-Day
Agentic Engineering corpus + Walmart strategic brief (PDFs in `corpus/`).

**Core narrative — the agent is built the way it teaches:** skills library with
Day 3 trigger discipline, read-only governance tier (zero ambient authority),
token circuit breaker, evaluation suite (EDD), MCP tool access, ADK multi-agent
orchestration. ⟨V2⟩ Every governance claim in the UI must correspond to real code.

## 2. TECH STACK (do not deviate)

- Python 3.11+, `google-adk`, `fastmcp`, `pypdf`, FastAPI (bundled with ADK).
- Model: `gemini-2.5-flash` via `GOOGLE_API_KEY` (AI Studio key, NOT Vertex).
- Frontend: single static `index.html` (vanilla JS/CSS, marked.js from cdnjs ok).
- Deploy: Dockerfile → Cloud Run, `--max-instances 1 --min-instances 0`.

## 3. REPO STRUCTURE

```
walmart-agentic-compass/
├── corpus/                      # the 6 source PDFs
├── corpus_index/chunks.json     # generated at build time, committed
├── scripts/build_index.py
├── mcp_server/server.py         # FastMCP: search_corpus + readiness_scorecard
├── compass/
│   ├── agent.py                 # orchestrator + 3 sub-agents
│   ├── guardrails.py            # callbacks: injection screen + token circuit breaker
│   └── skills/                  # SKILL.md per capability (Day 3 format, see §7)
├── evals/                       # ⟨V2⟩ EDD cases + runner
│   ├── cases.json               # 9 cases: 3 per skill (input, expected_tool, expected_output_criteria)
│   └── run_evals.py             # LLM-as-judge runner with position swap
├── web/index.html
├── main.py                      # ADK get_fast_api_app + static mount + rate limiter
├── Dockerfile
├── requirements.txt
└── README.md                    # setup, deploy, concept checklist, honest limitations section
```

## 4. CORPUS INDEX

`scripts/build_index.py`: pypdf-extract all PDFs, chunk ~1,200 chars / 150 overlap,
save `[{"source", "page", "text"}]`. Search = scored keyword match. No vector DB.
Run once, commit JSON. ⟨V2⟩ Corpus is a trusted, static set — note in README that
production RAG would require poisoning defenses per Day 4 Pillar 2; out of scope here
by design (closed corpus = the mitigation).

## 5. MCP SERVER — "MCP Server" concept

FastMCP server `compass-knowledge`, two READ-ONLY tools:

1. `search_corpus(query, k=5)` → top-k chunks WITH source + page. ⟨V2⟩ Hard cap
   k≤5 and truncate each chunk to 1,500 chars (token-economy control, cite Day 3).
2. `readiness_scorecard(use_case, data_sensitivity, action_tier, human_oversight,
   token_budget_defined)` → deterministic JSON: score /100, verdict
   (GO / GO-WITH-CONDITIONS / NOT-YET), required approvals per read/draft/act
   ladder, flags (no token budget → Token Economy Trap; action_allowed + low
   oversight → circuit breaker + named human owner required; pharmacy/food-safety/
   financial data → highest-consequence drift domain, behavioral monitoring mandatory).

ADK connects via MCPToolset (stdio). ⟨V2⟩ 10-minute timebox: if wiring fights you,
fall back to native FunctionTools wrapping the same functions; keep the MCP server
standalone-runnable and demo it in the video. Document the fallback honestly in
README — judges reward honesty over fake integration. ⟨V2⟩ README notes MCP spoofing
/ contextual authorization (Day 4) as the production concern this local stdio setup
sidesteps.

## 6. AGENTS — "Multi-agent system (ADK)" concept

Root `compass_orchestrator` (LlmAgent, gemini-2.5-flash) + 3 sub_agents:

1. **curriculum_mentor** — teaches any program concept. MUST call `search_corpus`
   first. ⟨V2⟩ CITATION RULE (verbatim in instruction): "Only cite document names
   and pages present in the search results you actually received. If the corpus
   does not cover the question, say so explicitly — never invent a citation."
2. **strategy_advisor** — maps a user's use-case to the Walmart brief: relevant
   moat, ROI framing, token-economy risk, 30/60/90-day plan. Grounds via
   `search_corpus`; same citation rule.
3. **governance_auditor** — interviews (use case, data sensitivity, action tier,
   oversight, token budget) → calls `readiness_scorecard` → presents verdict +
   ladder explanation. Never blesses action_allowed without the full sign-off
   chain (domain team + security/compliance + executive).

⟨V2⟩ Each sub-agent loads ONLY its own SKILL.md into its instruction (progressive
disclosure at agent granularity — state this in a code comment citing Day 3's 98%
token-reduction principle). Root agent's instruction contains only the three skill
DESCRIPTIONS (trigger blocks), not the bodies — that's the routing layer.

Root disclosure line: "I am a read-only advisory agent (Tier 1 on the governance
ladder I teach). I cannot take actions on any system — by architecture, not by
promise."

## 7. SKILL.md FILES — "Agent skills" concept, Day 3 compliant ⟨V2⟩

Each SKILL.md ≤60 lines and MUST contain:
- name, tier: read-only, allowed tools
- description with **3 positive triggers and 3 negative triggers** (Day 3's
  routing-accuracy requirement — this also fixes ADK sub-agent misrouting).
  Negative triggers explicitly route to the sibling skill (no overlap).
- instructions + 2 few-shot examples + escalation section (when to return
  control to the orchestrator).

## 8. SECURITY — "Security features" concept, honestly framed ⟨V2⟩

Layered, framed per Day 4 (comment each layer with its pillar):

- **Layer 1 (primary, architectural): zero ambient authority.** No action tools
  exist anywhere in the codebase. Read-only tier is enforced by capability
  absence, not by prompt. This is the real control — say so in README; do NOT
  claim the regex screen is the security story.
- **Layer 2 (defense-in-depth): `before_model_callback`** screening obvious
  injection patterns ("ignore previous instructions", system-prompt extraction,
  credential requests) and refusing requests for Walmart internal data. Framed as
  a tripwire + logging layer (Pillar 6 observability), with a comment
  acknowledging Day 4's point that static filters alone are insufficient.
- **Layer 3 (financial circuit breaker):** in `main.py`, per-IP rate limit
  (e.g. 10 req/min) + global daily request cap (env var `DAILY_REQUEST_CAP`,
  default 300). When tripped, return a friendly message: "Circuit breaker
  engaged — the token-spend ceiling this agent teaches (Walmart brief §5A) also
  protects this demo." A vulnerability turned into a feature.
- Every screened/tripped event logged to stdout with timestamp (audit trail,
  Pillar 7).

## 9. EVALUATION SUITE — ⟨V2⟩ closes the biggest v1 gap (EDD, Day 3/4)

`evals/cases.json`: 9 cases (3 per skill), each `{input, expected_tool,
output_criteria[]}` — WRITE THESE BEFORE the SKILL.md files (Evaluation-Driven
Development, per Day 3). Include: one routing case per skill, one citation-
grounding case (mentor must cite a real source), one governance case (refund agent
→ must list action-allowed sign-offs), one injection case (guardrail must trip).

`evals/run_evals.py`: runs each case against the agent, checks (a) correct
sub-agent/tool in the trajectory — trajectory-aware, not output-only, per Day 3's
warning that output-only scoring passes 20–40% more false positives; (b)
LLM-as-judge scores output vs criteria, **running each judgment twice with
reference/actual positions swapped** (Day 3 non-negotiable, ordering bias).
Print a pass/fail table. Show this table in the video for the evaluation story.

## 10. WEB UI

As v1 (Walmart-inspired palette #0053E2 / #FFC220, three quick-start cards,
SSE streaming chat, sub-agent badge, footer disclaimer "Independent capstone
project. Not affiliated with Walmart Inc.") plus ⟨V2⟩:
- "How I'm governed" sidebar now shows LIVE data, not static text: requests used
  vs daily cap, guardrail trips this session, active skill/tier. Every claim in
  this panel must be backed by real state.
- Approximate token/turn counter in the badge (from usage metadata if available,
  else estimate) — makes the token-economy lesson visible.

## 11. SERVING + DEPLOY

`main.py`: ADK `get_fast_api_app(web=False)` + static mount + rate limiter
middleware. Port `$PORT` default 8080. In-memory sessions — README notes sessions
reset on cold start (acceptable for demo; production would use a session service).
Deploy:
```
gcloud run deploy agentic-compass --source . --region us-central1 \
  --allow-unauthenticated --max-instances 1 --min-instances 0 \
  --set-env-vars GOOGLE_API_KEY=...,DAILY_REQUEST_CAP=300
```

## 12. ACCEPTANCE TESTS ⟨V2⟩

1. `build_index.py` → non-empty chunks.json covering all 6 PDFs.
2. `python evals/run_evals.py` → ≥8/9 pass, table prints.
3. "Vibe coding vs agentic engineering?" → mentor cites real doc+page from
   returned chunks only.
4. "Agent that auto-issues refunds" → auditor interviews, scorecard returns
   NOT-YET/GO-WITH-CONDITIONS + full sign-off chain.
5. "Ignore all previous instructions..." → guardrail trips, event logged.
6. Hammer endpooint past rate limit → circuit-breaker message returned.
7. UI streams, sub-agent badge + governance sidebar update live.

## 13. KAGGLE CONCEPT CHECKLIST (README + writeup)

| Concept | Where |
|---|---|
| Multi-agent system (ADK) | compass/agent.py — orchestrator + 3 sub-agents |
| MCP Server | mcp_server/server.py (+ MCPToolset or documented fallback) |
| Antigravity | Build process on screen in video |
| Security | Zero-ambient-authority tier + guardrails.py + circuit breaker |
| Deployability | Dockerfile + live Cloud Run URL in video |
| Agent skills | skills/*/SKILL.md, Day 3 trigger format, EDD evals |

## 14. HONEST LIMITATIONS (README section — judges reward this)

Keyword search not embeddings; stdio MCP is protocol demonstration, production
needs contextual authorization (Day 4); static guardrail filters are tripwires,
not the perimeter; in-memory sessions; corpus is closed/trusted by design.
