"""Run the ADK agents on one request and apply the guardrail gate to what the tools returned.

    python agents/run.py "SUB-08-071"
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv  # noqa: E402
from google.adk.runners import InMemoryRunner  # noqa: E402
from google.genai import types  # noqa: E402

from rfi_agent.agent import root_agent  # noqa: E402
from rfi_assistant.gate import apply_gate  # noqa: E402

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


async def run(prompt: str) -> dict:
    runner = InMemoryRunner(agent=root_agent, app_name="p04")
    session = await runner.session_service.create_session(app_name="p04", user_id="coordinator")
    tools, texts = {}, {}
    msg = types.Content(role="user", parts=[types.Part(text=prompt)])
    async for event in runner.run_async(user_id="coordinator", session_id=session.id, new_message=msg):
        for fr in event.get_function_responses() or []:
            tools[fr.name] = fr.response
        if event.content and event.content.parts and any(p.text for p in event.content.parts):
            texts[event.author] = "".join(p.text or "" for p in event.content.parts)
    route, safety = tools.get("suggest_reviewer"), tools.get("check_life_safety")
    cites = tools.get("verify_citations", {"dropped": []})
    gate = apply_gate(route["confidence"], safety["life_safety"], cites["dropped"]) if route and safety else None
    return {"texts": texts, "tools": tools, "gate": gate}


def agent_available() -> bool:
    return bool(os.getenv("GOOGLE_API_KEY"))


if __name__ == "__main__":
    out = asyncio.run(run(" ".join(sys.argv[1:]) or "SUB-08-071"))
    for who, text in out["texts"].items():
        print(f"\n[{who}]\n{text}")
    print("\n[gate]", out["gate"])
