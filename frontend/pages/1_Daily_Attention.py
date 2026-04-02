from __future__ import annotations

from typing import Any

import streamlit as st

from common import format_dt, run_agent_command


st.set_page_config(page_title="Daily Attention", layout="wide")
st.title("Daily Attention Agent")
st.caption("CLI-style page: configure input, run once, review plain output")


def _lines(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, dict):
        out: list[str] = []
        for item in value.values():
            out.extend(_lines(item))
        return out
    if isinstance(value, (list, tuple, set)):
        out: list[str] = []
        for item in value:
            out.extend(_lines(item))
        return out
    text = str(value).strip()
    return [text] if text else []


left, middle, right = st.columns([1.2, 1.2, 1.0])
with left:
    user_id = st.text_input("User ID", value=st.session_state.get("daily_user_id", "user_123"))
    workspace_id = st.text_input("Workspace ID", value=st.session_state.get("daily_workspace_id", "workspace_123"))
with middle:
    vip_text = st.text_area("VIP senders (comma separated)", value=st.session_state.get("daily_vips", "ceo@company.com"), height=90)
    keyword_text = st.text_area("Keywords (comma separated)", value=st.session_state.get("daily_keywords", "urgent, approval, deadline"), height=90)
with right:
    depth_mode = st.selectbox("Depth", ["quick", "deep"], index=0)
    output_mode = st.selectbox("Output", ["brief_only", "brief_with_drafts"], index=0)
    run_clicked = st.button("Run", type="primary", use_container_width=True)

st.session_state["daily_user_id"] = user_id
st.session_state["daily_workspace_id"] = workspace_id
st.session_state["daily_vips"] = vip_text
st.session_state["daily_keywords"] = keyword_text

if run_clicked:
    vip_senders = [item.strip() for item in vip_text.replace("\n", ",").split(",") if item.strip()]
    keywords = [item.strip() for item in keyword_text.replace("\n", ",").split(",") if item.strip()]
    with st.spinner("Running..."):
        st.session_state["daily_result"] = run_agent_command(
            "daily",
            "run",
            {
                "user_id": user_id,
                "workspace_id": workspace_id,
                "vip_senders": vip_senders,
                "keywords": keywords,
                "depth_mode": depth_mode,
                "output_mode": output_mode,
            },
        )

result = st.session_state.get("daily_result")
if not result:
    st.info("Enter input and click Run.")
    st.stop()

if not result.get("ok"):
    st.error(result.get("error", "Run failed"))
    if result.get("stderr"):
        st.code(result["stderr"], language="text")
    st.stop()

data = result["result"]
attention_items = data.get("attention_items", [])
risks = data.get("risks", [])
opportunities = data.get("opportunities", [])
warnings = data.get("warnings", [])

st.write(f"Run started: {format_dt(data.get('run_started_at'))}")
st.write(f"Run completed: {format_dt(data.get('run_completed_at'))}")
st.write(f"Attention items: {len(attention_items)} | Risks: {len(risks)} | Opportunities: {len(opportunities)} | Warnings: {len(warnings)}")

st.subheader("Attention Items")
if not attention_items:
    st.write("(none)")
else:
    for item in attention_items:
        st.markdown("---")
        st.write(f"{item.get('type', 'item').upper()} | {str(item.get('priority_level', '')).upper()} | score={item.get('priority_score', 0)}")
        st.write(f"Title: {item.get('title', 'Untitled')}")
        summary = item.get("summary")
        if summary:
            st.write(f"Summary: {summary}")
        reasons = _lines(item.get("why_flagged", []))
        for reason in reasons:
            st.write(f"- reason: {reason}")
        st.write(f"Action: {item.get('recommended_action', 'Review')}")
        evidence = item.get("evidence", {})
        source_name = evidence.get("calendar_name", evidence.get("tool", "source"))
        st.write(f"Source: {source_name} | Time: {format_dt(evidence.get('timestamp'))}")

st.subheader("Risks")
if not risks:
    st.write("(none)")
else:
    for risk in risks:
        st.write(f"- {risk.get('title', 'Risk')}")
        for line in _lines(risk.get("reason", "")):
            st.write(f"  {line}")
        for line in _lines(risk.get("events", []))[:5]:
            st.write(f"  - {line}")

st.subheader("Opportunities")
if not opportunities:
    st.write("(none)")
else:
    for opportunity in opportunities:
        st.write(f"- {opportunity.get('title', 'Opportunity')}")
        for line in _lines(opportunity.get("suggestion", "")):
            st.write(f"  {line}")

if warnings:
    st.subheader("Warnings")
    for warning in warnings:
        st.write(f"- {warning}")
