"""Walmart Agentic Compass — ADK multi-agent system (spec §6).

Architecture = the lesson:
- Skills library (Day 3): each sub-agent loads ONLY its own SKILL.md body —
  progressive disclosure at agent granularity. The orchestrator sees only the
  routing descriptions (trigger blocks), never the bodies. This is the same
  principle behind Day 3's documented ~98% token reduction vs. loading all
  operational context on every interaction.
- Read-only tier (Day 3 ladder): the only tools are search_corpus and
  readiness_scorecard — both read-only. Zero ambient authority (Day 4 P5).
- Guardrail tripwire on every agent (Day 4 P4/P6/P7).

MCP note: mcp_server/server.py exposes these same tools over MCP (stdio) and
is runnable standalone. The agents import the functions natively for runtime
robustness on Cloud Run (single container, no subprocess supervision) — see
README "Honest Limitations". To wire via MCPToolset instead, see the
commented block at the bottom of this file.
"""
import re
from pathlib import Path

from google.adk.agents import Agent

from compass.guardrails import screen_input
from mcp_server.server import readiness_scorecard, search_corpus

MODEL = "gemini-2.5-flash-lite"
SKILLS_DIR = Path(__file__).resolve().parent / "skills"


def load_skill(name: str) -> str:
    return (SKILLS_DIR / name / "SKILL.md").read_text()


def skill_description(name: str) -> str:
    """Extract only the routing description block (triggers) for the
    orchestrator — bodies stay with their own agent (progressive disclosure)."""
    text = load_skill(name)
    match = re.search(r"## Description \(routing\)(.*?)## Instructions", text, re.DOTALL)
    return match.group(1).strip() if match else text[:400]


CITATION_RULE = (
    "CITATION RULE: Only cite document names and page numbers that appear in "
    "search results you actually received in this conversation. If the corpus "
    "does not cover the question, say so explicitly — never invent a citation."
)

curriculum_mentor = Agent(
    name="curriculum_mentor",
    model=MODEL,
    description=skill_description("curriculum-mentor"),
    instruction=(
        "You are the Curriculum Mentor of the Walmart Agentic Compass.\n"
        + CITATION_RULE + "\n\nYour skill specification:\n"
        + load_skill("curriculum-mentor")
    ),
    tools=[search_corpus],
    before_model_callback=screen_input,
)

strategy_advisor = Agent(
    name="strategy_advisor",
    model=MODEL,
    description=skill_description("strategy-advisor"),
    instruction=(
        "You are the Strategy Advisor of the Walmart Agentic Compass.\n"
        + CITATION_RULE + "\n\nYour skill specification:\n"
        + load_skill("strategy-advisor")
    ),
    tools=[search_corpus],
    before_model_callback=screen_input,
)

governance_auditor = Agent(
    name="governance_auditor",
    model=MODEL,
    description=skill_description("governance-auditor"),
    instruction=(
        "You are the Governance Auditor of the Walmart Agentic Compass.\n"
        + CITATION_RULE + "\n\nYour skill specification:\n"
        + load_skill("governance-auditor")
    ),
    tools=[readiness_scorecard, search_corpus],
    before_model_callback=screen_input,
)

root_agent = Agent(
    name="compass_orchestrator",
    model=MODEL,
    description="Routes Walmart leaders to the right specialist for agentic-AI guidance.",
    instruction=(
        "You are the Walmart Agentic Compass — a governed advisor helping "
        "Walmart executives and technology professionals build enterprise AI "
        "agents the right way, per the Google × Kaggle 5-Day Agentic "
        "Engineering program and the Walmart strategic brief.\n\n"
        "On first contact, greet briefly, state: 'I am a read-only advisory "
        "agent (Tier 1 on the governance ladder I teach). I cannot take "
        "actions on any system — by architecture, not by promise.' Then offer "
        "the three modes: Learn a Concept, Assess a Use Case, Audit My "
        "Governance.\n\n"
        "Route every substantive question to exactly one sub-agent using "
        "their trigger descriptions. Do not answer domain questions yourself.\n\n"
        "Sub-agent routing descriptions:\n"
        f"[curriculum_mentor]\n{skill_description('curriculum-mentor')}\n\n"
        f"[strategy_advisor]\n{skill_description('strategy-advisor')}\n\n"
        f"[governance_auditor]\n{skill_description('governance-auditor')}\n"
    ),
    sub_agents=[curriculum_mentor, strategy_advisor, governance_auditor],
    before_model_callback=screen_input,
)

# --- Optional MCPToolset wiring (spec §5) --------------------------------
# from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
# corpus_toolset = MCPToolset(
#     connection_params=StdioServerParameters(
#         command="python", args=["mcp_server/server.py"],
#     )
# )
# ...then pass tools=[corpus_toolset] instead of the native functions.
# Timeboxed fallback per spec §5: native functions above, MCP server
# demonstrated standalone (fastmcp dev / video). Documented in README.
