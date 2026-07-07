"""Serving layer (spec §11): FastAPI + ADK Runner + circuit breaker.

Financial circuit breaker (spec §8, Layer 3): per-IP rate limit + global daily
request cap. The token-spend ceiling this agent teaches (Walmart brief §5A)
also protects this deployment. Sessions are in-memory: they reset on cold
start — acceptable for a demo; production would use a session service.
"""
import asyncio
import datetime
import json
import os
import time
import uuid
from collections import defaultdict, deque
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from compass.agent import root_agent
from compass.guardrails import guardrail_state

APP_NAME = "walmart-agentic-compass"
DAILY_CAP = int(os.environ.get("DAILY_REQUEST_CAP", "300"))
PER_IP_PER_MIN = 10

app = FastAPI(title=APP_NAME)
session_service = InMemorySessionService()
runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)

# --- Circuit breaker state (Pillar 6 observability + brief §5A) ---
_ip_hits = defaultdict(deque)
_daily = {"date": None, "count": 0}

BREAKER_MSG = (
    "Circuit breaker engaged — the token-spend ceiling this agent teaches "
    "(Walmart brief §5A) also protects this demo. Try again later."
)


def circuit_breaker(ip: str) -> Optional[str]:
    today = datetime.date.today().isoformat()
    if _daily["date"] != today:
        _daily["date"], _daily["count"] = today, 0
    if _daily["count"] >= DAILY_CAP:
        return f"{BREAKER_MSG} (daily cap of {DAILY_CAP} requests reached)"
    now = time.time()
    hits = _ip_hits[ip]
    while hits and now - hits[0] > 60:
        hits.popleft()
    if len(hits) >= PER_IP_PER_MIN:
        return f"{BREAKER_MSG} (per-visitor rate limit)"
    hits.append(now)
    _daily["count"] += 1
    return None


@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "web" / "index.html")


@app.get("/governance")
def governance():
    """Live data for the 'How I'm governed' sidebar — every claim backed by real state."""
    return {
        "tier": "read-only (Tier 1)",
        "action_tools": 0,
        "requests_used_today": _daily["count"],
        "daily_cap": DAILY_CAP,
        "guardrail_trips": guardrail_state["trips"],
        "last_trip": guardrail_state["last_trip"],
        "skills_loaded": ["curriculum-mentor", "strategy-advisor", "governance-auditor"],
    }


@app.post("/chat")
async def chat(request: Request):
    body = await request.json()
    message = (body.get("message") or "").strip()[:4000]
    session_id = body.get("session_id")
    ip = request.client.host if request.client else "unknown"

    blocked = circuit_breaker(ip)
    if blocked:
        return JSONResponse({"error": blocked}, status_code=429)
    if not message:
        return JSONResponse({"error": "Empty message."}, status_code=400)

    if not session_id:
        session = await session_service.create_session(app_name=APP_NAME, user_id="web")
        session_id = session.id
    else:
        session = await session_service.get_session(
            app_name=APP_NAME, user_id="web", session_id=session_id
        )
        if session is None:  # cold start wiped memory
            session = await session_service.create_session(app_name=APP_NAME, user_id="web")
            session_id = session.id

    async def stream():
        yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"
        content = types.Content(role="user", parts=[types.Part(text=message)])
        try:
            async for event in runner.run_async(
                user_id="web", session_id=session_id, new_message=content
            ):
                author = getattr(event, "author", None)
                if author:
                    yield f"data: {json.dumps({'type': 'agent', 'name': author})}\n\n"
                for part in (event.content.parts if event.content else []) or []:
                    if getattr(part, "function_call", None):
                        yield f"data: {json.dumps({'type': 'tool', 'name': part.function_call.name})}\n\n"
                    if getattr(part, "text", None) and event.is_final_response():
                        yield f"data: {json.dumps({'type': 'text', 'text': part.text})}\n\n"
        except Exception as exc:  # surface, don't swallow (Pillar 6)
            print(f"[ERROR] {exc}", flush=True)
            yield f"data: {json.dumps({'type': 'error', 'text': 'Something went wrong. Try again.'})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
