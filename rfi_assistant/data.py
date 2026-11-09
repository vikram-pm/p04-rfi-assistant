"""Loads the synthetic project. Agents see RECORD columns only; GROUND TRUTH stays with the evaluator."""
from functools import lru_cache
from pathlib import Path

import pandas as pd

XLSX = Path(__file__).resolve().parent.parent / "data" / "P04_Synthetic_Project_Data.xlsx"
RFI_TRUTH = ["Correct reviewer", "Routing check", "Duplicate of", "Life safety", "Cost / time impact"]
SUB_TRUTH = ["What was missing", "Pre-check catchable"]


@lru_cache
def load() -> dict:
    x = pd.read_excel(XLSX, sheet_name=None)
    rfis, subs = x["RFIs"], x["Submittals"]
    return {
        "rfis": rfis.drop(columns=RFI_TRUTH),
        "rfi_truth": rfis[["RFI #"] + RFI_TRUTH],
        "submittals": subs.drop(columns=SUB_TRUTH),
        "sub_truth": subs[["Submittal #"] + SUB_TRUTH],
        "spec": x["Spec Book"],
        "drawings": x["Drawing Index"],
    }


# What the spec checker reads inside a submittal package (synthetic; one package for the demo).
PACKAGES = {
    "SUB-08-071": [
        {"requirement": "Finish: BHMA 626 satin chromium", "ref": "§2.4.A", "found": "626 satin chromium", "status": "met", "evidence": "p. 3"},
        {"requirement": "Closer: Grade 1, BHMA A156.4", "ref": "§2.5.A", "found": "Grade 2", "status": "gap", "evidence": "p. 7"},
        {"requirement": "Fire rating label, 90-min doors", "ref": "§2.1.C", "found": "Not found", "status": "gap", "evidence": "—"},
        {"requirement": "Electrified strike, power transfer", "ref": "§2.6.B", "found": "Unclear wiring diagram", "status": "unclear", "evidence": "p. 9"},
        {"requirement": "Hinges: 114 mm, ball bearing", "ref": "§2.2.A", "found": "114 mm, ball bearing", "status": "met", "evidence": "p. 2"},
        {"requirement": "Lever trim, accessible return", "ref": "§2.3.B", "found": "Return lever, AODA note", "status": "met", "evidence": "p. 5"},
        {"requirement": "Keying schedule attached", "ref": "§1.5.C", "found": "Appendix A", "status": "met", "evidence": "Appx A"},
        {"requirement": "Closer warranty: 10 years", "ref": "§1.7.A", "found": "10 years", "status": "met", "evidence": "p. 11"},
    ]
}
