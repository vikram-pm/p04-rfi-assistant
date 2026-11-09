"""Deterministic tools. The ADK agents call these; the evaluator scores them against ground truth."""
import re

from .data import PACKAGES, load

STOP = {"a", "an", "the", "at", "of", "on", "in", "for", "to", "vs", "and", "with", "through", "by"}
LIFE_SAFETY = ["sprinkler", "fire", "alarm", "egress", "exit", "pressurization", "firestop", "rated", "smoke"]
LIFE_SAFETY_EXEMPT = ["fire damper access"]  # maintenance access, not a life-safety question


def _tokens(text: str) -> set:
    return {t for t in re.findall(r"[a-z0-9-]+", text.lower()) if t not in STOP}


def find_similar_rfis(subject: str, spec_section: str = "", before_rfi: str = "", top_k: int = 3) -> dict:
    """Find earlier answered RFIs that may already answer this question.

    Args:
        subject: Subject line of the new RFI.
        spec_section: MasterFormat section, for example "05 12 00".
        before_rfi: Only search RFIs numbered before this one, for example "RFI-040". Empty searches all.
        top_k: Number of matches to return.

    Returns:
        {"matches": [{"rfi", "subject", "score"}], "possible_duplicate": RFI number or None}
    """
    rfis = load()["rfis"]
    pool = rfis[rfis["Status"].isin(["Closed", "Answered"])]
    if before_rfi:
        pool = pool[pool["RFI #"] < before_rfi]
    new = _tokens(subject)
    out = []
    for _, r in pool.iterrows():
        old = _tokens(r["Subject"])
        jaccard = len(new & old) / len(new | old) if new | old else 0
        score = round(0.7 * jaccard + 0.3 * (spec_section == r["Spec section"]), 2)
        out.append({"rfi": r["RFI #"], "subject": r["Subject"], "score": score})
    out = sorted(out, key=lambda m: -m["score"])[:top_k]
    dup = out[0]["rfi"] if out and out[0]["score"] >= 0.6 else None
    return {"matches": out, "possible_duplicate": dup}


def suggest_reviewer(drawing: str, spec_section: str) -> dict:
    """Suggest who should answer an RFI, from the drawing sheet and spec section it cites.

    The drawing's consultant wins a disagreement, because the question is about what that sheet shows.

    Args:
        drawing: Drawing sheet, for example "S-201".
        spec_section: MasterFormat section, for example "05 12 00".

    Returns:
        {"candidates": [{"reviewer", "score", "why"}], "confidence": 0 to 1}
    """
    d = load()
    dwg = d["drawings"].set_index("Sheet")["Consultant"].get(drawing)
    spc = d["spec"].set_index("Section")["Reviewing consultant"].get(spec_section)
    if dwg and spc and dwg == spc:
        why = f"{drawing} and spec {spec_section} both belong to this consultant"
        return {"candidates": [{"reviewer": dwg, "score": 0.92, "why": why}], "confidence": 0.92}
    if dwg and spc:
        return {"candidates": [{"reviewer": dwg, "score": 0.72, "why": f"issued {drawing}"},
                               {"reviewer": spc, "score": 0.28, "why": f"owns spec {spec_section}"}],
                "confidence": 0.72}
    if dwg or spc:
        return {"candidates": [{"reviewer": dwg or spc, "score": 0.65, "why": "only one reference resolved"}],
                "confidence": 0.65}
    return {"candidates": [], "confidence": 0.0}


def check_life_safety(text: str) -> dict:
    """Flag fire, egress and sprinkler topics. Flagged items always go to a person.

    Args:
        text: RFI subject and question.

    Returns:
        {"life_safety": bool, "matched": [keywords]}
    """
    low = text.lower()
    if any(e in low for e in LIFE_SAFETY_EXEMPT):
        return {"life_safety": False, "matched": []}
    hits = [k for k in LIFE_SAFETY if k in low]
    return {"life_safety": bool(hits), "matched": hits}


def verify_citations(drawing: str, spec_section: str) -> dict:
    """Check that each reference resolves to a real sheet or spec section. Unresolved ones are dropped.

    Args:
        drawing: Drawing sheet cited.
        spec_section: Spec section cited.

    Returns:
        {"resolved": [...], "dropped": [...]}
    """
    d = load()
    refs = [(drawing, drawing in set(d["drawings"]["Sheet"])),
            (spec_section, spec_section in set(d["spec"]["Section"]))]
    return {"resolved": [r for r, ok in refs if r and ok], "dropped": [r for r, ok in refs if r and not ok]}


def precheck_submittal(submittal_no: str) -> dict:
    """Compare a submittal package with its spec section before it goes to the consultant.

    Args:
        submittal_no: Submittal number, for example "SUB-08-071".

    Returns:
        {"items": [...], "gaps": [...], "unclear": [...], "likely_outcome": str}
    """
    items = PACKAGES.get(submittal_no)
    if items is None:
        return {"error": f"No package contents for {submittal_no} in the synthetic set."}
    gaps = [i for i in items if i["status"] == "gap"]
    unclear = [i for i in items if i["status"] == "unclear"]
    outcome = "Revise and resubmit (likely)" if gaps else "Ready for consultant review"
    return {"items": items, "gaps": gaps, "unclear": unclear, "likely_outcome": outcome}
