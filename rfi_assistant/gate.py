"""Guardrail gate: plain rules the PM sets. The model never decides how an item reaches a person."""
ONE_CLICK = 0.85
PICK_OF_TWO = 0.60


def apply_gate(confidence: float, life_safety: bool, dropped_citations: list) -> dict:
    if life_safety:
        return {"mode": "manual", "reason": "Life-safety topic: the coordinator routes it."}
    if dropped_citations:
        return {"mode": "manual", "reason": f"Unresolved reference: {', '.join(dropped_citations)}."}
    if confidence >= ONE_CLICK:
        return {"mode": "one_click", "reason": f"Confidence {confidence:.0%}: reviewer pre-selected."}
    if confidence >= PICK_OF_TWO:
        return {"mode": "pick_of_two", "reason": f"Confidence {confidence:.0%}: coordinator picks from two."}
    return {"mode": "manual", "reason": f"Confidence {confidence:.0%}: below threshold."}
