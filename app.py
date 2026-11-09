"""P04 · AI RFI & Submittals assistant (Linarc-style concept). Run: streamlit run app.py"""
import asyncio
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "agents"))
from rfi_assistant.data import load  # noqa: E402
from rfi_assistant.pipeline import assist_rfi  # noqa: E402
from rfi_assistant.tools import precheck_submittal  # noqa: E402

st.set_page_config(page_title="P04 · RFI & Submittals", page_icon="🟧", layout="wide")
st.markdown("""
<style>
.block-container {padding-top: 1rem;}
.bar {background:#0E1A2B; color:#fff; padding:14px 20px; border-radius:8px 8px 0 0; font-weight:700; font-size:18px;}
.bar span {color:#F7941D;}
.proj {background:#0E1A2B; color:#C9CED6; padding:6px 20px 10px; border-radius:0 0 8px 8px; font-size:13px; margin-bottom:12px;}
.ai {background:#FFF4E6; border:1px solid #F7941D; border-radius:8px; padding:12px 16px; margin:8px 0;}
.note {color:#6B7280; font-size:12px; font-style:italic;}
</style>
<div class="bar"><span>✦</span> Linarc-style · RFI &amp; Submittals</div>
<div class="proj">Maple Ridge Medical Centre &nbsp;|&nbsp; Owner – Northgate Health &nbsp;|&nbsp; GC – Lakeshore Builders
&nbsp;|&nbsp; Synthetic data · concept, not a Linarc product</div>
""", unsafe_allow_html=True)

d = load()
rfis, spec, dwg = d["rfis"], d["spec"], d["drawings"]
reviewers = sorted(dwg["Consultant"].unique())


def agent_ready() -> bool:
    try:
        from run import agent_available
        return agent_available()
    except Exception:
        return False


log, draft, sub = st.tabs(["01 · RFI Log", "02 · New RFI + AI Assist", "03 · Submittal Pre-check"])

# ---------- 01 RFI Log ----------
with log:
    flags = []
    for _, r in rfis.iterrows():
        out = assist_rfi(r["Subject"], r["Subject"], r["Drawing"], r["Spec section"], before_rfi=r["RFI #"])
        if out["life_safety"]["life_safety"]:
            flags.append("Life safety · manual")
        elif out["similar"]["possible_duplicate"]:
            flags.append(f"Similar to {out['similar']['possible_duplicate']}")
        else:
            flags.append("")
    view = rfis.assign(**{"AI flag": flags})
    open_ = view["Status"].isin(["Open", "Overdue"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("RFIs", len(view))
    c2.metric("Open", int(open_.sum()))
    c3.metric("Overdue", int((view["Status"] == "Overdue").sum()))
    c4.metric("Avg turnaround (working days)", f"{view['Days to answer'].mean():.1f}")
    flagged = view[open_ & (view["AI flag"] != "")]
    if len(flagged):
        st.markdown(f'<div class="ai"><b>✦ AI insight</b> · {len(flagged)} open RFI(s) flagged: '
                    + ", ".join(f"{a} ({b})" for a, b in zip(flagged["RFI #"], flagged["AI flag"])) + "</div>",
                    unsafe_allow_html=True)
    only_open = st.toggle("Open items only", value=True)
    show = view[open_ | (view["Status"] == "Draft")] if only_open else view
    st.dataframe(show[["RFI #", "Subject", "Discipline", "Assigned reviewer", "Status", "Due", "Days open", "AI flag"]]
                 .sort_values("RFI #", ascending=False), hide_index=True, width="stretch",
                 column_config={"Due": st.column_config.DateColumn(format="MMM D")})

# ---------- 02 New RFI ----------
with draft:
    left, right = st.columns([3, 2], gap="large")
    with left:
        st.subheader("RFI-043 · Draft")
        note = st.text_area("From site", "Embed plates at grid D2 don't line up with the steel shop drawing. "
                                         "Which one governs? Crew is waiting.", height=90)
        subject = st.text_input("Subject", "Embed plate spacing conflict at grid D2")
        a, b = st.columns(2)
        sheet = a.selectbox("Drawing", dwg["Sheet"], index=list(dwg["Sheet"]).index("S-501"))
        section = b.selectbox("Spec section", spec["Section"], index=list(spec["Section"]).index("05 12 00"))
        use_agent = st.toggle("Use Gemini agents (needs GOOGLE_API_KEY)", value=False, disabled=not agent_ready())
        go = st.button("Run AI Assist", type="primary")
    with right:
        if go:
            out = assist_rfi(subject, note, sheet, section, before_rfi="RFI-043")
            if use_agent:
                try:
                    from run import run
                    res = asyncio.run(run(f"Site note: {note}\nDrawing: {sheet}\nSpec section: {section}"))
                    out["draft"] = res["texts"].get("draft_writer", out["draft"])
                except Exception as ex:  # keep the demo working offline
                    st.info(f"Agent unavailable, using offline draft ({ex.__class__.__name__}).")
            st.markdown("**✦ AI draft**")
            st.text_area("Question", out["draft"], height=150, label_visibility="collapsed")
            st.caption("References: " + ", ".join(out["citations"]["resolved"]))
            st.markdown("**Similar RFIs · check before sending**")
            for m in out["similar"]["matches"][:2]:
                st.write(f"{m['rfi']} · {m['subject']} — {m['score']:.0%} match")
            g = out["gate"]
            st.markdown(f"**Reviewer** · {g['reason']}")
            cands = [c["reviewer"] for c in out["reviewer"]["candidates"]]
            if g["mode"] == "one_click":
                st.radio("Reviewer", cands, label_visibility="collapsed")
            elif g["mode"] == "pick_of_two":
                st.radio("Reviewer", cands, index=None, label_visibility="collapsed")
            else:
                st.warning("No suggestion. Choose the reviewer yourself.")
                st.selectbox("Reviewer", reviewers, index=None)
            st.button("Send to reviewer")
            st.markdown('<p class="note">AI draft – not a design instruction. Only the consultant’s response '
                        'becomes the answer.</p>', unsafe_allow_html=True)
        else:
            st.caption("Run AI Assist to draft, check for duplicates and suggest a reviewer.")

# ---------- 03 Submittal pre-check ----------
with sub:
    pre = precheck_submittal("SUB-08-071")
    st.subheader("SUB-08-071 · Door hardware, set HW-12")
    st.caption("Keystone Hardware · Spec 08 71 00 · Reviewer: Studio Arc")
    m = pd.Series([i["status"] for i in pre["items"]]).value_counts()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Checked", len(pre["items"]))
    c2.metric("Met", int(m.get("met", 0)))
    c3.metric("Gaps", int(m.get("gap", 0)))
    c4.metric("Needs a person", int(m.get("unclear", 0)))
    t, p = st.columns([3, 2], gap="large")
    t.dataframe(pd.DataFrame(pre["items"]).rename(columns=str.capitalize), hide_index=True, width="stretch")
    with p:
        st.markdown(f'<div class="ai"><b>✦ Likely outcome</b><br>{pre["likely_outcome"]}</div>', unsafe_allow_html=True)
        note = "Please resubmit HW-12 with: " + "; ".join(f"{g['requirement']} ({g['ref']})" for g in pre["gaps"]) + "."
        st.text_area("Draft return note to sub", note, height=110)
        for u in pre["unclear"]:
            st.warning(f"Below threshold: {u['requirement']} ({u['ref']}) — assigned to you.")
        st.markdown('<p class="note">AI checks the package against the spec. The consultant still reviews '
                    'and stamps it.</p>', unsafe_allow_html=True)
