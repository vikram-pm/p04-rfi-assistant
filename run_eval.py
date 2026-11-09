"""Score the assistant against the ground-truth columns. No API key needed.

    python run_eval.py            # prints the scorecard, writes eval_results.csv
"""
import pandas as pd

from rfi_assistant.data import load
from rfi_assistant.pipeline import assist_rfi
from rfi_assistant.tools import precheck_submittal


def main() -> None:
    d = load()
    rfis = d["rfis"].merge(d["rfi_truth"], on="RFI #")
    rows = []
    for _, r in rfis.iterrows():
        out = assist_rfi(r["Subject"], r["Subject"], r["Drawing"], r["Spec section"], before_rfi=r["RFI #"])
        top = out["reviewer"]["candidates"][0]["reviewer"] if out["reviewer"]["candidates"] else None
        in_two = [c["reviewer"] for c in out["reviewer"]["candidates"][:2]]
        rows.append({
            "RFI #": r["RFI #"],
            "historical_correct": r["Routing check"] == "Correct" if pd.notna(r["Routing check"]) else None,
            "ai_top_correct": top == r["Correct reviewer"],
            "ai_top2_correct": r["Correct reviewer"] in in_two,
            "gate": out["gate"]["mode"],
            "ls_truth": r["Life safety"] == "Yes",
            "ls_flag": out["life_safety"]["life_safety"],
            "dup_truth": r["Duplicate of"] if pd.notna(r["Duplicate of"]) else None,
            "dup_flag": out["similar"]["possible_duplicate"],
            "cites_ok": not out["citations"]["dropped"],
        })
    e = pd.DataFrame(rows)
    e.to_csv("eval_results.csv", index=False)

    hist = e["historical_correct"].dropna()
    one = e[e["gate"] == "one_click"]
    two = e[e["gate"] == "pick_of_two"]
    ls_tp = (e.ls_flag & e.ls_truth).sum()
    dup_tp = (e.dup_flag.notna() & (e.dup_flag == e.dup_truth)).sum()
    pre = precheck_submittal("SUB-08-071")
    truth_gaps = d["sub_truth"].set_index("Submittal #").loc["SUB-08-071", "What was missing"]

    card = [
        ("Routing: historical, first reviewer correct", f"{hist.mean():.0%}", "baseline"),
        ("Routing: AI top suggestion correct", f"{e.ai_top_correct.mean():.0%}", "target 95%"),
        ("Routing: correct reviewer in AI top two", f"{e.ai_top2_correct.mean():.0%}", ""),
        ("Gate: one-click (correct when shown)", f"{len(one)} RFIs ({one.ai_top_correct.mean():.0%})", "must stay 100%"),
        ("Gate: pick of two (correct in options)", f"{len(two)} RFIs ({two.ai_top2_correct.mean():.0%})", ""),
        ("Gate: manual", f"{(e.gate == 'manual').sum()} RFIs", ""),
        ("Life safety: recall", f"{ls_tp}/{e.ls_truth.sum()}", "must be all"),
        ("Life safety: extra flags (safe side)", f"{(e.ls_flag & ~e.ls_truth).sum()}", ""),
        ("Duplicates: caught", f"{dup_tp}/{e.dup_truth.notna().sum()}", ""),
        ("Duplicates: false flags", f"{(e.dup_flag.notna() & (e.dup_flag != e.dup_truth)).sum()}", "coordinator decides"),
        ("Citations resolved", f"{e.cites_ok.mean():.0%}", "100%"),
        ("Submittal SUB-08-071: gaps found", f"{len(pre['gaps'])} (truth: {truth_gaps})", ""),
    ]
    w = max(len(m) for m, _, _ in card)
    print(f"\nP04 scorecard · {len(e)} RFIs\n" + "-" * (w + 40))
    for m, v, note in card:
        print(f"{m:<{w}}  {v:<22} {note}")
    print("\nDetail per RFI: eval_results.csv")


if __name__ == "__main__":
    main()
