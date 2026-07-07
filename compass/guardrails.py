"""Guardrails (spec §8) — layered, honestly framed per Day 4.

Layer 1 (primary, architectural — not in this file): zero ambient authority.
No action tools exist anywhere in this codebase. The read-only tier is
enforced by capability ABSENCE, not by prompt. (Day 4, Pillar 5.)

Layer 2 (this file, defense-in-depth): a before_model_callback tripwire that
screens obvious injection/extraction patterns and logs every trip. Day 4 is
explicit that static filters alone are insufficient — this is a tripwire and
an observability signal (Pillar 6), not the perimeter.
"""
import datetime
import re
from typing import Optional

from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from google.genai import types

# Screened patterns -> Pillar mapping in comments
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",  # Pillar 4: injection
    r"reveal\s+(your\s+)?(system\s+prompt|instructions)",        # Pillar 4: extraction
    r"you\s+are\s+now\s+(dan|developer\s+mode|unrestricted)",    # Pillar 4: jailbreak persona
    r"(api[_\s-]?key|password|credential|secret\s+token)",       # Pillar 2: secrets probing
    r"(execute|run|issue|send)\s+.*(refund|payment|transfer)\s+now",  # Pillar 5: action coercion
]
INTERNAL_DATA_PATTERNS = [
    r"walmart('s)?\s+(internal|confidential|proprietary)\s+(data|numbers|sales)",
]

_compiled = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]
_compiled_internal = [re.compile(p, re.IGNORECASE) for p in INTERNAL_DATA_PATTERNS]

# In-memory trip counter surfaced by the UI governance sidebar
guardrail_state = {"trips": 0, "last_trip": None}


def _log(kind: str, snippet: str):
    ts = datetime.datetime.utcnow().isoformat()
    guardrail_state["trips"] += 1
    guardrail_state["last_trip"] = ts
    # Pillar 7: audit trail — every screened event is logged with timestamp
    print(f"[GUARDRAIL][{ts}] {kind} tripped: {snippet[:120]!r}", flush=True)


def screen_input(callback_context: CallbackContext, llm_request: LlmRequest) -> Optional[LlmResponse]:
    """before_model_callback: returns a canned LlmResponse to short-circuit
    the model call when a tripwire fires; returns None to proceed."""
    last_user_text = ""
    for content in reversed(llm_request.contents or []):
        if content.role == "user" and content.parts:
            last_user_text = " ".join(p.text or "" for p in content.parts if getattr(p, "text", None))
            break
    if not last_user_text:
        return None

    for pattern in _compiled:
        if pattern.search(last_user_text):
            _log("injection", last_user_text)
            return LlmResponse(content=types.Content(role="model", parts=[types.Part(
                text="Tripwire engaged. I'm a read-only advisory agent (Tier 1 on the "
                     "governance ladder I teach) — I don't act on instructions that try to "
                     "override my specification, extract my configuration, or trigger "
                     "actions. That refusal is architectural: no action tools exist in my "
                     "codebase. Happy to explain how this maps to the Day 4 seven-pillar "
                     "security architecture instead."
            )]))
    for pattern in _compiled_internal:
        if pattern.search(last_user_text):
            _log("internal-data", last_user_text)
            return LlmResponse(content=types.Content(role="model", parts=[types.Part(
                text="I only work from the public program corpus (the five whitepapers and "
                     "the strategic brief). I don't have — and won't speculate about — "
                     "Walmart internal data."
            )]))
    return None
