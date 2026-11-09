"""ADK agents for P04. Run `adk web agents` from the project root, or use agents/run.py.

orchestrator ─┬─ rfi_flow (sequential): draft_writer → duplicate_finder → reviewer_router
              └─ spec_checker
Agents propose. The guardrail gate (rfi_assistant/gate.py) decides how each item reaches a person.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from google.adk.agents import LlmAgent, SequentialAgent  # noqa: E402

from rfi_assistant.tools import (  # noqa: E402
    check_life_safety, find_similar_rfis, precheck_submittal, suggest_reviewer, verify_citations,
)

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
RULES = ("You support a Canadian general contractor's project coordinator. Never answer a design question, "
         "approve anything, or change contract price or time. Cite only references a tool confirmed.")

draft_writer = LlmAgent(
    name="draft_writer", model=MODEL, tools=[verify_citations], output_key="draft",
    instruction=f"""{RULES}
Turn the site note into an RFI. First call verify_citations with the drawing and spec section given.
Use only resolved references. Reply in exactly this form:
SUBJECT: <one line, under 90 characters>
QUESTION: <2–4 plain sentences: what the documents show, the conflict, the one thing to confirm>
REFERENCES: <resolved references, comma separated>""",
)

duplicate_finder = LlmAgent(
    name="duplicate_finder", model=MODEL, tools=[find_similar_rfis], output_key="similar",
    instruction=f"""{RULES}
Draft RFI:
{{draft}}
Call find_similar_rfis with the draft's subject and spec section. List the top matches with scores.
If possible_duplicate is set, say which earlier RFI may already answer it. Do not decide; the coordinator does.""",
)

reviewer_router = LlmAgent(
    name="reviewer_router", model=MODEL, tools=[suggest_reviewer, check_life_safety], output_key="routing",
    instruction=f"""{RULES}
Draft RFI:
{{draft}}
Call suggest_reviewer with the drawing and spec section, and check_life_safety with the subject and question.
Report the candidates, their scores and reasons, and whether it is a life-safety topic. Do not pick for the user.""",
)

rfi_flow = SequentialAgent(name="rfi_flow", sub_agents=[draft_writer, duplicate_finder, reviewer_router],
                           description="Drafts an RFI from a site note, checks for duplicates and suggests a reviewer.")

spec_checker = LlmAgent(
    name="spec_checker", model=MODEL, tools=[precheck_submittal], output_key="precheck",
    description="Pre-checks a submittal package against its spec section.",
    instruction=f"""{RULES}
Call precheck_submittal with the submittal number. Summarise the likely outcome, list each gap with its spec
clause, and list unclear items as "needs a person". Then draft a short return note to the subcontractor.""",
)

root_agent = LlmAgent(
    name="orchestrator", model=MODEL, sub_agents=[rfi_flow, spec_checker],
    instruction=f"""{RULES}
If the user gives a site note or field question, transfer to rfi_flow.
If the user gives a submittal number (SUB-…), transfer to spec_checker.
Otherwise ask which one they need.""",
)
