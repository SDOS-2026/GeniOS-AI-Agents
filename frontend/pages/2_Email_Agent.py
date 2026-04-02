from __future__ import annotations

import streamlit as st

from common import run_agent_command


st.set_page_config(page_title="Email Agent", layout="wide")
st.title("Email Agent")
st.caption("CLI-style page: type command, run, then follow only required next step")

user_id = st.text_input("User ID", value=st.session_state.get("email_user_id", "default_user"))
user_prompt = st.text_area(
    "You",
    value=st.session_state.get("email_prompt", ""),
    height=100,
    placeholder="check inbox | reply to latest email | compose email to HR",
)
run_clicked = st.button("Run", type="primary")

st.session_state["email_user_id"] = user_id
st.session_state["email_prompt"] = user_prompt

if run_clicked:
    if not user_prompt.strip():
        st.error("Enter a command first.")
        st.stop()
    with st.spinner("Running..."):
        analyzed = run_agent_command(
            "email",
            "analyze_prompt",
            {
                "user_prompt": user_prompt,
                "user_id": user_id,
            },
        )
    st.session_state["email_analyzed"] = analyzed
    st.session_state.pop("email_inbox", None)
    st.session_state.pop("email_summary", None)
    st.session_state.pop("email_reply_draft", None)
    st.session_state.pop("email_compose_draft", None)

analysis = st.session_state.get("email_analyzed")
if not analysis:
    st.info("Enter a command and click Run.")
    st.stop()

if not analysis.get("ok"):
    st.error(analysis.get("error", "Command failed"))
    if analysis.get("stderr"):
        st.code(analysis["stderr"], language="text")
    st.stop()

parsed = analysis["result"]
mode = parsed.get("mode", "UNKNOWN")

st.write(f"Mode: {mode}")
if parsed.get("reasoning"):
    st.write("Reasoning:")
    for line in parsed.get("reasoning", []):
        st.write(f"- {line}")

if mode in {"CHECK_INBOX", "REPLY"}:
    st.subheader("Inbox")
    limit = st.number_input("Limit", min_value=1, max_value=20, value=5, step=1)
    priority = st.selectbox("Priority", ["ANY", "HIGH", "MEDIUM", "LOW"], index=0)
    fetch_clicked = st.button("Fetch", type="primary")

    if fetch_clicked:
        with st.spinner("Fetching inbox..."):
            inbox = run_agent_command(
                "email",
                "fetch_inbox",
                {
                    "user_id": user_id,
                    "limit": int(limit),
                    "priority": priority,
                    "user_prompt": user_prompt,
                },
            )
        st.session_state["email_inbox"] = inbox

    inbox = st.session_state.get("email_inbox")
    if inbox and inbox.get("ok"):
        emails = inbox["result"].get("emails", [])
        st.write(f"Fetched: {len(emails)}")

        if emails:
            labels = [
                f"{i + 1}. {email.get('from', 'Unknown')} | {email.get('subject', 'No Subject')}"
                for i, email in enumerate(emails)
            ]
            selected_index = st.selectbox("Select email", options=list(range(len(emails))), format_func=lambda i: labels[i])
            selected_email = emails[selected_index]

            st.write(f"From: {selected_email.get('from', 'Unknown')}")
            st.write(f"Subject: {selected_email.get('subject', 'No Subject')}")
            st.text_area("Body", value=selected_email.get("body", ""), height=180, key="email_selected_body", disabled=True)

            col1, col2 = st.columns(2)
            with col1:
                summarize_clicked = st.button("Summarize")
            with col2:
                draft_reply_clicked = st.button("Draft Reply")

            if summarize_clicked:
                with st.spinner("Summarizing..."):
                    summary = run_agent_command("email", "summarize_thread", {"raw_thread": selected_email})
                st.session_state["email_summary"] = summary

            summary = st.session_state.get("email_summary")
            if summary and summary.get("ok"):
                st.text_area("Summary", value=summary["result"].get("summary", ""), height=120, key="email_summary_box")

            if draft_reply_clicked or mode == "REPLY":
                with st.spinner("Drafting reply..."):
                    reply_draft = run_agent_command(
                        "email",
                        "draft_reply",
                        {
                            "raw_thread": selected_email,
                            "summary": (summary or {}).get("result", {}).get("summary") or selected_email.get("body", ""),
                            "classification": selected_email.get("classification", {}),
                            "risk_flags": [],
                            "compose_memory": [],
                            "reply_memory": [],
                        },
                    )
                st.session_state["email_reply_draft"] = reply_draft

    reply_draft = st.session_state.get("email_reply_draft")
    if reply_draft and reply_draft.get("ok"):
        state = reply_draft["result"]
        st.subheader("Reply Draft")
        to_value = ", ".join(state.get("recipient", {}).get("to", []))
        cc_value = ", ".join(state.get("recipient", {}).get("cc", []))
        bcc_value = ", ".join(state.get("recipient", {}).get("bcc", []))

        to_text = st.text_input("To", value=to_value, key="reply_to")
        cc_text = st.text_input("CC", value=cc_value, key="reply_cc")
        bcc_text = st.text_input("BCC", value=bcc_value, key="reply_bcc")
        subject_text = st.text_input("Subject", value=state.get("subject", ""), key="reply_subject")
        body_text = st.text_area("Draft", value=state.get("draft", ""), height=220, key="reply_draft_text")

        approve = st.checkbox("I approve sending this reply", key="reply_approve")
        send_clicked = st.button("Send Reply", type="primary", disabled=not approve)
        if send_clicked:
            send_result = run_agent_command(
                "email",
                "send_message",
                {
                    "approval_status": "APPROVED",
                    "recipient": {
                        "to": [item.strip() for item in to_text.split(",") if item.strip()],
                        "cc": [item.strip() for item in cc_text.split(",") if item.strip()],
                        "bcc": [item.strip() for item in bcc_text.split(",") if item.strip()],
                    },
                    "subject": subject_text,
                    "draft": body_text,
                    "attachments": [],
                    "thread_id": state.get("thread_id"),
                    "reply_message_id": state.get("reply_message_id"),
                },
            )
            if send_result.get("ok") and send_result.get("result", {}).get("ok"):
                st.success("Reply sent")
            else:
                st.error(send_result.get("error", "Failed to send"))

elif mode == "COMPOSE":
    st.subheader("Compose")
    to_text = st.text_input("To", value=st.session_state.get("compose_to", ""))
    cc_text = st.text_input("CC", value=st.session_state.get("compose_cc", ""))
    bcc_text = st.text_input("BCC", value=st.session_state.get("compose_bcc", ""))
    subject_text = st.text_input("Subject", value=st.session_state.get("compose_subject", ""))
    body_prompt = st.text_area("Message", value=st.session_state.get("compose_prompt", ""), height=180)
    tone = st.selectbox("Tone", ["professional", "friendly", "direct", "warm"], index=0)
    brevity = st.selectbox("Brevity", ["default", "concise"], index=0)
    edit_instructions = st.text_area("Edit instructions", value=st.session_state.get("compose_edit", ""), height=100)
    generate_clicked = st.button("Generate Draft", type="primary")

    st.session_state["compose_to"] = to_text
    st.session_state["compose_cc"] = cc_text
    st.session_state["compose_bcc"] = bcc_text
    st.session_state["compose_subject"] = subject_text
    st.session_state["compose_prompt"] = body_prompt
    st.session_state["compose_edit"] = edit_instructions

    if generate_clicked:
        with st.spinner("Generating draft..."):
            compose_draft = run_agent_command(
                "email",
                "compose_email",
                {
                    "user_prompt": body_prompt,
                    "recipient": {
                        "to": [item.strip() for item in to_text.split(",") if item.strip()],
                        "cc": [item.strip() for item in cc_text.split(",") if item.strip()],
                        "bcc": [item.strip() for item in bcc_text.split(",") if item.strip()],
                    },
                    "subject": subject_text,
                    "body": body_prompt,
                    "attachments": [],
                    "tone": tone,
                    "brevity": brevity,
                    "edit_instructions": edit_instructions,
                    "compose_memory": [],
                    "summary": body_prompt,
                },
            )
        st.session_state["email_compose_draft"] = compose_draft

    compose_draft = st.session_state.get("email_compose_draft")
    if compose_draft and compose_draft.get("ok"):
        state = compose_draft["result"]
        st.subheader("Compose Draft")
        final_to = st.text_input("Final To", value=", ".join(state.get("recipient", {}).get("to", [])), key="compose_final_to")
        final_cc = st.text_input("Final CC", value=", ".join(state.get("recipient", {}).get("cc", [])), key="compose_final_cc")
        final_bcc = st.text_input("Final BCC", value=", ".join(state.get("recipient", {}).get("bcc", [])), key="compose_final_bcc")
        final_subject = st.text_input("Final Subject", value=state.get("subject", ""), key="compose_final_subject")
        final_body = st.text_area("Final Draft", value=state.get("draft", ""), height=240, key="compose_final_body")

        approve = st.checkbox("I approve sending this email", key="compose_approve")
        send_clicked = st.button("Send Email", type="primary", disabled=not approve)
        if send_clicked:
            send_result = run_agent_command(
                "email",
                "send_message",
                {
                    "approval_status": "APPROVED",
                    "recipient": {
                        "to": [item.strip() for item in final_to.split(",") if item.strip()],
                        "cc": [item.strip() for item in final_cc.split(",") if item.strip()],
                        "bcc": [item.strip() for item in final_bcc.split(",") if item.strip()],
                    },
                    "subject": final_subject,
                    "draft": final_body,
                    "attachments": [],
                },
            )
            if send_result.get("ok") and send_result.get("result", {}).get("ok"):
                st.success("Email sent")
            else:
                st.error(send_result.get("error", "Failed to send"))

else:
    st.warning("Mode is UNKNOWN. Try a clearer command.")
