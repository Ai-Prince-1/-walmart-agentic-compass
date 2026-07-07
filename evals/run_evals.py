"""Evaluation runner (spec §9) — Evaluation-Driven Development.

Trajectory-aware, not output-only: Day 3 warns output-only scoring passes
20-40% more false positives. For each case we check (a) which sub-agent
handled it and which tool it called — the trajectory — and (b) LLM-as-judge
scoring of the output against criteria, judged TWICE with criteria/output
positions swapped to eliminate ordering bias (Day 3 non-negotiable).

Usage:  GOOGLE_API_KEY=... python evals/run_evals.py
"""
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google import genai
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from compass.agent import root_agent

CASES = json.loads((Path(__file__).parent / "cases.json").read_text())
JUDGE_MODEL = "gemini-2.5-flash"


async def run_case(runner, session_service, case):
    session = await session_service.create_session(app_name="compass-evals", user_id="eval")
    content = types.Content(role="user", parts=[types.Part(text=case["input"])])
    agents_seen, tools_seen, final_text = set(), set(), ""
    async for event in runner.run_async(
        user_id="eval", session_id=session.id, new_message=content
    ):
        if getattr(event, "author", None):
            agents_seen.add(event.author)
        for part in (event.content.parts if event.content else []) or []:
            if getattr(part, "function_call", None):
                tools_seen.add(part.function_call.name)
            if getattr(part, "text", None) and event.is_final_response():
                final_text += part.text
    return agents_seen, tools_seen, final_text


def judge(client, criteria, output) -> bool:
    """LLM-as-judge, run twice with positions swapped; pass = both passes."""
    def ask(a, b, order):
        prompt = (
            f"You are a strict evaluator. {order}\n"
            f"BLOCK A:\n{a}\n\nBLOCK B:\n{b}\n\n"
            "Does the agent output satisfy ALL the criteria? Reply with exactly "
            "one word: PASS or FAIL."
        )
        resp = client.models.generate_content(model=JUDGE_MODEL, contents=prompt)
        return "PASS" in (resp.text or "").upper()

    crit = "\n".join(f"- {c}" for c in criteria)
    first = ask(crit, output, "Block A is the criteria; Block B is the agent output.")
    second = ask(output, crit, "Block A is the agent output; Block B is the criteria.")
    return first and second


async def main():
    if not os.environ.get("GOOGLE_API_KEY"):
        sys.exit("Set GOOGLE_API_KEY first.")
    client = genai.Client()
    session_service = InMemorySessionService()
    runner = Runner(agent=root_agent, app_name="compass-evals", session_service=session_service)

    results = []
    for case in CASES:
        agents_seen, tools_seen, output = await run_case(runner, session_service, case)
        trajectory_ok = True
        notes = []
        if case["expected_agent"] and case["expected_agent"] not in agents_seen:
            trajectory_ok = False
            notes.append(f"expected agent {case['expected_agent']}, saw {agents_seen or '{}'}")
        if case["expected_tool"] and case["expected_tool"] not in tools_seen:
            trajectory_ok = False
            notes.append(f"expected tool {case['expected_tool']}, saw {tools_seen or '{}'}")
        output_ok = judge(client, case["output_criteria"], output or "(empty)")
        passed = trajectory_ok and output_ok
        results.append((case["id"], trajectory_ok, output_ok, passed, "; ".join(notes)))
        print(f"[{'PASS' if passed else 'FAIL'}] {case['id']}  "
              f"trajectory={'ok' if trajectory_ok else 'FAIL'} "
              f"output={'ok' if output_ok else 'FAIL'}  {('(' + '; '.join(notes) + ')') if notes else ''}")

    total = sum(1 for r in results if r[3])
    print(f"\n{'='*60}\nRESULT: {total}/{len(results)} cases passed "
          f"(gate: >= {len(results)-1})\n{'='*60}")
    sys.exit(0 if total >= len(results) - 1 else 1)


if __name__ == "__main__":
    asyncio.run(main())
