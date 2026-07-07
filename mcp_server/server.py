"""compass-knowledge MCP server (spec §5).

Demonstrates the MCP Server concept (Day 2): a standardized, governed
connection layer between the agent and its knowledge/tools. Both tools are
READ-ONLY — Tier 1 on the Day 3 read/draft/act ladder. Zero ambient authority:
there is no tool in this codebase capable of mutating any external system.

Run standalone:  python mcp_server/server.py   (stdio transport)
The same functions are importable directly (compass.agent uses them as native
ADK tools — see the Honest Limitations section of the README for why).

Production note (Day 4): a real deployment would add contextual authorization
and server identity verification to defend against MCP spoofing. Out of scope
for a local stdio server by design.
"""
import json
from pathlib import Path

try:
    from fastmcp import FastMCP
    mcp = FastMCP("compass-knowledge")
    HAS_FASTMCP = True
except ImportError:  # fastmcp needs Python >=3.10; agent works fully without it
    HAS_FASTMCP = False

ROOT = Path(__file__).resolve().parent.parent
CHUNKS_PATH = ROOT / "corpus_index" / "chunks.json"

_chunks_cache = None


def _load_chunks():
    global _chunks_cache
    if _chunks_cache is None:
        if not CHUNKS_PATH.exists():
            raise RuntimeError(
                "corpus_index/chunks.json not found. Run: python scripts/build_index.py"
            )
        _chunks_cache = json.loads(CHUNKS_PATH.read_text())
    return _chunks_cache


def search_corpus(query: str, k: int = 5) -> dict:
    """Search the 5-day program corpus + Walmart brief. Returns top-k chunks
    with source document and page number for citation.

    Args:
        query: keywords to search for (e.g. "read draft act ladder").
        k: number of results (hard-capped at 5 — token-economy control, Day 3).
    """
    k = min(int(k), 5)
    terms = [t.lower() for t in query.split() if len(t) > 2]
    if not terms:
        return {"results": []}
    scored = []
    for c in _load_chunks():
        text_l = c["text"].lower()
        score = sum(text_l.count(t) for t in terms)
        if score > 0:
            scored.append((score, c))
    scored.sort(key=lambda x: -x[0])
    results = [
        {
            "source": c["source"],
            "page": c["page"],
            "text": c["text"][:1500],  # truncation cap per spec §5
        }
        for _, c in scored[:k]
    ]
    return {"results": results, "note": "Cite ONLY these sources/pages."}


REQUIRED_APPROVALS = {
    "read_only": ["Domain team approval"],
    "draft_only": ["Domain team approval", "Format owner approval"],
    "action_allowed": [
        "Domain team approval",
        "Security/compliance review",
        "Executive sign-off",
        "Named human owner with escalation authority",
        "Real-time behavioral monitoring + circuit breaker",
    ],
}

HIGH_CONSEQUENCE = {"pharmacy", "food", "financial", "payment", "health", "medical"}


def readiness_scorecard(
    use_case: str,
    data_sensitivity: str,
    action_tier: str,
    human_oversight: str,
    token_budget_defined: bool,
) -> dict:
    """Deterministic governance scorecard per the Day 3 read/draft/act ladder
    and the Walmart brief's risk framework. Returns score, verdict, required
    approvals, and flags.

    Args:
        use_case: one-sentence description of the proposed agent.
        data_sensitivity: e.g. "public", "internal", "pharmacy", "financial".
        action_tier: one of read_only | draft_only | action_allowed.
        human_oversight: one of none | spot_check | review_queue | approval_gate.
        token_budget_defined: whether a token spend baseline + ceiling exists.
    """
    tier = action_tier.strip().lower().replace("-", "_").replace(" ", "_")
    if tier not in REQUIRED_APPROVALS:
        tier = "action_allowed"  # fail closed: unknown tier treated as highest risk
    oversight = human_oversight.strip().lower().replace(" ", "_")
    sens = data_sensitivity.lower()

    score = 100
    flags = []

    if not token_budget_defined:
        score -= 25
        flags.append(
            "Token Economy Trap risk (Day 1 / Walmart brief §5A): no spend "
            "baseline or hard ceiling defined. At transaction scale, costs "
            "compound exponentially, not linearly. Define baseline + "
            "circuit-breaker ceiling before any pilot."
        )
    if tier == "action_allowed" and oversight in {"none", "spot_check"}:
        score -= 35
        flags.append(
            "Action-allowed tier with weak oversight: requires an approval "
            "gate, a named human owner, and automatic circuit-breaking on "
            "trust-score decay (intent drift risk, Day 4)."
        )
    if any(word in sens for word in HIGH_CONSEQUENCE):
        score -= 20
        flags.append(
            "Highest-consequence drift domain (Walmart brief): financial, "
            "food-safety, and pharmacy operations require real-time "
            "behavioral monitoring before any production deployment."
        )
    if tier == "draft_only" and oversight == "none":
        score -= 15
        flags.append("Draft-tier output with no human review defeats the tier's purpose.")

    if score >= 80:
        verdict = "GO"
    elif score >= 55:
        verdict = "GO-WITH-CONDITIONS"
    else:
        verdict = "NOT-YET"

    return {
        "use_case": use_case,
        "score": max(score, 0),
        "verdict": verdict,
        "action_tier": tier,
        "required_approvals": REQUIRED_APPROVALS[tier],
        "flags": flags or ["No blocking flags. Proceed with the standard approval chain."],
        "next_steps": [
            "Write the behavioral specification before any code (Day 1: agentic engineering, not vibe coding).",
            "Encode the workflow as a versioned SKILL.md with 3 positive / 3 negative triggers (Day 3).",
            "Write evaluation cases BEFORE building (Evaluation-Driven Development).",
            "Establish token spend baseline + circuit breaker (Walmart brief §5A).",
        ],
    }


# Register as MCP tools (only when fastmcp is available)
if HAS_FASTMCP:
    mcp.tool()(search_corpus)
    mcp.tool()(readiness_scorecard)

if __name__ == "__main__":
    if HAS_FASTMCP:
        mcp.run()  # stdio transport
    else:
        raise SystemExit("fastmcp not installed (needs Python >=3.10). "
                         "The agent itself runs fine without it: python3 main.py")
