"""Runs every RFI tool, then the gate. Used by the app (offline mode) and the evaluator."""
from .gate import apply_gate
from .tools import check_life_safety, find_similar_rfis, suggest_reviewer, verify_citations


def template_draft(note: str, drawing: str, spec_section: str) -> str:
    """Offline stand-in for the Draft writer agent."""
    return (f"Site reports: {note.strip()}\n\n"
            f"Please confirm the requirement shown on {drawing} and in spec section {spec_section}, "
            f"and advise how to proceed.")


def assist_rfi(subject: str, note: str, drawing: str, spec_section: str, before_rfi: str = "") -> dict:
    cites = verify_citations(drawing, spec_section)
    route = suggest_reviewer(drawing, spec_section)
    safety = check_life_safety(f"{subject} {note}")
    return {
        "draft": template_draft(note, drawing, spec_section),
        "similar": find_similar_rfis(subject, spec_section, before_rfi),
        "reviewer": route,
        "life_safety": safety,
        "citations": cites,
        "gate": apply_gate(route["confidence"], safety["life_safety"], cites["dropped"]),
    }
