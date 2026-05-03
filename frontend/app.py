import streamlit as st
import requests
import time
import json
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Gateway Configuration
GATEWAY_URL = "http://localhost:8000"
DAA_RUN_URL = f"{GATEWAY_URL}/daa/run"
DAA_STATUS_URL = f"{GATEWAY_URL}/daa/status/{{run_id}}"
EMAIL_RUN_URL = f"{GATEWAY_URL}/email/run"
EMAIL_RESUME_URL = f"{GATEWAY_URL}/email/resume"
EMAIL_STATE_URL = f"{GATEWAY_URL}/email/state/{{thread_id}}"

st.set_page_config(
    page_title="GeniOS Agents Frontend",
    page_icon="🧠",
    layout="wide"
)

# --- Session State Initialization ---
if "email_thread_id" not in st.session_state:
    st.session_state.email_thread_id = None
if "email_interrupt_payload" not in st.session_state:
    st.session_state.email_interrupt_payload = None

def render_feedback_section():
    st.markdown("---")
    st.subheader("📝 Help Us Improve")
    with st.expander("Provide Anonymous Feedback", expanded=False):
        with st.form("feedback_form"):
            st.write("Your feedback is saved anonymously and helps us improve the Daily Attention Agent.")
            rating = st.slider("How would you rate your experience?", 1, 5, 5)
            comments = st.text_area("What features would you like to see or what could be improved?")
            
            submitted = st.form_submit_button("Submit Feedback")
            if submitted:
                SUPABASE_URL = os.getenv("SUPABASE_URL")
                SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

                payload = {
                    "rating": rating,
                    "comments": comments.strip()
                }
                
                if not SUPABASE_URL or not SUPABASE_ANON_KEY:
                    st.warning("Feedback not sent: Supabase credentials are missing in .env file.")
                else:
                    headers = {
                        "apikey": SUPABASE_ANON_KEY,
                        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
                        "Content-Type": "application/json"
                    }
                    
                    try:
                        response = requests.post(SUPABASE_URL, headers=headers, json=payload)
                        response.raise_for_status()
                        st.success("Thank you! Your feedback has been sent to the developers securely.")
                    except requests.exceptions.HTTPError as e:
                        error_msg = response.text
                        st.error(f"Failed to send feedback: {e}\n\nDetails: {error_msg}")
                    except Exception as e:
                        st.error(f"Failed to send feedback: {str(e)}")


def render_daa_interface():
    st.title("📅 Daily Attention Agent (DAA)")
    st.markdown("Your executive assistant for a focused start to the day.")

    # --- Sidebar for Configuration ---
    st.sidebar.header("DAA Configuration")
    user_id = st.sidebar.text_input("User ID", value="user_123", key="daa_user_id")
    workspace_id = st.sidebar.text_input("Workspace ID", value="workspace_default", key="daa_workspace_id")

    st.sidebar.subheader("Signal Filters")
    vip_senders_input = st.sidebar.text_area("VIP Senders (comma separated)", value="boss@example.com, important@client.com", key="daa_vips")
    keywords_input = st.sidebar.text_area("Keywords (comma separated)", value="urgent, invoice, project alpha", key="daa_keywords")

    st.sidebar.subheader("Execution Options")
    depth_mode = st.sidebar.selectbox("Depth Mode", ["quick", "deep"], key="daa_depth")
    output_mode = st.sidebar.selectbox("Output Mode", ["brief_only", "full_report"], key="daa_output")

    if st.button("🚀 Run DAA Agent", type="primary"):
        vip_senders = [s.strip() for s in vip_senders_input.split(",") if s.strip()]
        keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]
        
        payload = {
            "user_id": user_id,
            "workspace_id": workspace_id,
            "vip_senders": vip_senders,
            "keywords": keywords,
            "depth_mode": depth_mode,
            "output_mode": output_mode
        }
        
        st.info("Initiating DAA run via Gateway...")
        
        try:
            response = requests.post(DAA_RUN_URL, json=payload)
            response.raise_for_status()
            run_data = response.json()
            run_id = run_data.get("run_id")
            
            if run_id:
                st.success(f"Run started successfully! (Run ID: {run_id})")
                
                with st.spinner("Agent is running... Polling for status..."):
                    status = "running"
                    while status == "running":
                        time.sleep(2)  # poll every 2 seconds
                        status_resp = requests.get(DAA_STATUS_URL.format(run_id=run_id))
                        if status_resp.status_code == 200:
                            status_data = status_resp.json()
                            status = status_data.get("status")
                            
                            if status == "success":
                                st.success("Run completed!")
                                result = status_data.get("result", {})
                                
                                st.header("Executive Briefing")
                                
                                # Attention Items
                                st.subheader("🔥 Attention Items")
                                attention_items = result.get("attention_items", [])
                                if attention_items:
                                    for item in attention_items:
                                        st.markdown(f"- **{item.get('title', 'Item')}** (Score: {item.get('priority_score', 'N/A')}): {item.get('summary', '')}")
                                else:
                                    st.info("No immediate attention items found.")
                                    
                                # Risks
                                st.subheader("⚠️ Risks Identified")
                                risks = result.get("risks", [])
                                if risks:
                                    for risk in risks:
                                        reason_text = risk.get('reason', '')
                                        if isinstance(reason_text, list):
                                            reason_text = ", ".join(reason_text)
                                        st.warning(f"- **{risk.get('title', 'Risk')}**: {reason_text}")
                                else:
                                    st.success("No critical risks identified.")
                                    
                                # Opportunities
                                st.subheader("💡 Opportunities")
                                opportunities = result.get("opportunities", [])
                                if opportunities:
                                    for opp in opportunities:
                                        st.info(f"- **{opp.get('title', 'Opportunity')}**: {opp.get('suggestion', '')}")
                                else:
                                    st.markdown("No specific opportunities flagged.")
                                    
                                # Warnings
                                warnings = result.get("warnings", [])
                                if warnings:
                                    st.subheader("🔔 System Warnings")
                                    for w in warnings:
                                        st.warning(w)
                                        
                            elif status == "error":
                                st.error("Error during agent execution!")
                                st.write(status_data.get("result"))
                                break
                        else:
                            st.error(f"Failed to get status. Status code: {status_resp.status_code}")
                            break
            else:
                st.error("Did not receive a run_id from the Gateway.")
                
        except requests.exceptions.RequestException as e:
            st.error(f"Failed to connect to GeniOS Gateway: {e}")
            st.info("Ensure that the Gateway service is running on port 8000.")


def render_email_interface():
    st.title("📧 Email Agent")
    st.markdown("Your intelligent assistant for managing and drafting emails.")

    # 1. New Request Input Form
    if not st.session_state.email_interrupt_payload:
        with st.form("email_prompt_form"):
            prompt = st.text_area("What do you want the Email Agent to do?", 
                                  placeholder="e.g. 'Draft an email to client@example.com about the new features' or 'Check my latest unread emails'")
            submitted = st.form_submit_button("🚀 Run Email Agent")
            
            if submitted and prompt:
                with st.spinner("Agent is thinking..."):
                    try:
                        response = requests.post(EMAIL_RUN_URL, json={"prompt": prompt})
                        response.raise_for_status()
                        run_data = response.json()
                        
                        st.session_state.email_thread_id = run_data.get("thread_id")
                        status = run_data.get("status")
                        
                        if status == "interrupted":
                            st.session_state.email_interrupt_payload = run_data.get("interrupt_payload")
                            st.rerun()
                        elif status == "done":
                            st.success("Task completed successfully!")
                        else:
                            st.error(f"Agent finished with an unexpected status: {status}")
                            
                    except requests.exceptions.RequestException as e:
                        st.error(f"Failed to connect to GeniOS Gateway: {e}")

    # 2. Interrupt Handling UI
    if st.session_state.email_interrupt_payload:
        st.warning("⚠️ The Email Agent requires your input to proceed.")
        payload = st.session_state.email_interrupt_payload
        
        st.subheader("Agent Request:")
        st.write(payload.get("message", "No message provided"))
        
        # Display drafted email if present (draft_review interrupt)
        if payload.get("interrupt_type") == "draft_review" or payload.get("draft"):
            st.markdown("### Draft Preview")
            st.markdown(f"**To:** {', '.join(payload.get('to', []))}")
            if payload.get('cc'):
                st.markdown(f"**Cc:** {', '.join(payload.get('cc', []))}")
            st.markdown(f"**Subject:** {payload.get('subject', '')}")
            st.text_area("Draft Body", value=payload.get("draft", ""), height=200, disabled=True)

        # Display inbox list if present (inbox_review interrupt)
        if payload.get("interrupt_type") == "inbox_review":
            st.markdown("### 📥 Inbox Selection")
            st.write("Select an email to take action:")
            emails = payload.get("emails", [])
            
            for i, email in enumerate(emails):
                with st.expander(f"{email['from']} — {email['subject']} ({email['priority']})"):
                    st.write(f"**Snippet:** {email['snippet']}")
                    col_sum, col_rep = st.columns([1, 1])
                    if col_sum.button(f"Summarize Email {i}", key=f"sum_{i}"):
                        st.session_state.email_selected_action = {"action": "SUMMARIZE", "email_index": i}
                    if col_rep.button(f"Reply to Email {i}", key=f"rep_{i}"):
                        st.session_state.email_selected_action = {"action": "REPLY", "email_index": i}
            
            if st.button("I'm Done", key="inbox_done"):
                st.session_state.email_selected_action = {"action": "DONE"}

        # Display summary if present (summarize_ack interrupt)
        if payload.get("interrupt_type") == "summarize_ack":
            st.markdown("### 📝 Email Summary")
            st.info(payload.get("summary", "No summary provided"))
            if st.button("✅ Acknowledge & Continue", key="ack_summary"):
                st.session_state.email_selected_action = {"acknowledged": True}
        
        # Global Cancel Button for any interrupt
        if st.button("🚫 Cancel Agent Run", key="global_cancel"):
            st.session_state.email_interrupt_payload = None
            st.session_state.email_thread_id = None
            st.rerun()




        # 3. Decision Processing
        decision_payload = None
        
        # Check if an inbox action was selected
        if "email_selected_action" in st.session_state and st.session_state.email_selected_action:
            decision_payload = st.session_state.email_selected_action
            st.session_state.email_selected_action = None # Clear it
        
        if payload.get("interrupt_type") == "draft_review":
            with st.form("email_resume_form"):
                user_response = st.text_area("Edit Instructions (optional):", 
                                             placeholder="e.g. 'Change the subject to Hello' or 'Make it more professional'")
                
                col1, col2, col3 = st.columns([1, 1, 2])
                with col1:
                    send_submitted = st.form_submit_button("✅ Send Email")
                with col2:
                    edit_submitted = st.form_submit_button("🛠️ Apply Edits")
                with col3:
                    cancel_submitted = st.form_submit_button("❌ Cancel & Clear")
                    
                if cancel_submitted:
                    st.session_state.email_interrupt_payload = None
                    st.session_state.email_thread_id = None
                    st.rerun()
                    
                if send_submitted:
                    decision_payload = {"decision": "SEND"}
                elif edit_submitted:
                    decision_payload = {"decision": "EDIT", "edit_instructions": user_response}

        
        if decision_payload:
            with st.spinner("Resuming agent..."):
                try:
                    response = requests.post(EMAIL_RESUME_URL, json={
                        "thread_id": st.session_state.email_thread_id,
                        "response": decision_payload
                    })
                    response.raise_for_status()
                    resume_data = response.json()
                    
                    status = resume_data.get("status")
                    if status == "interrupted":
                        st.session_state.email_interrupt_payload = resume_data.get("interrupt_payload")
                        st.rerun()
                    elif status == "done":
                        st.success("Task completed successfully!")
                        st.session_state.email_interrupt_payload = None
                        st.session_state.email_thread_id = None
                    else:
                        st.error(f"Agent finished with an unexpected status: {status}")
                        
                except requests.exceptions.RequestException as e:
                    st.error(f"Failed to connect to GeniOS Gateway: {e}")



# --- Main App Logic ---
st.sidebar.title("🧠 GeniOS Agents")
agent_choice = st.sidebar.radio("Select Active Agent", ["Daily Attention Agent", "Email Agent"])

if agent_choice == "Daily Attention Agent":
    render_daa_interface()
else:
    render_email_interface()

render_feedback_section()
