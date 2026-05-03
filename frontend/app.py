import streamlit as st
import requests
import time
import json
from datetime import datetime

# Gateway Configuration
GATEWAY_URL = "http://localhost:8000"
DAA_RUN_URL = f"{GATEWAY_URL}/daa/run"
DAA_STATUS_URL = f"{GATEWAY_URL}/daa/status/{{run_id}}"

st.set_page_config(
    page_title="GeniOS DAA Frontend",
    page_icon="🧠",
    layout="wide"
)

st.title("📅 Daily Attention Agent (DAA)")
st.markdown("Your executive assistant for a focused start to the day.")

# --- Sidebar for Configuration ---
st.sidebar.header("Configuration")
user_id = st.sidebar.text_input("User ID", value="user_123")
workspace_id = st.sidebar.text_input("Workspace ID", value="workspace_default")

st.sidebar.subheader("Signal Filters")
vip_senders_input = st.sidebar.text_area("VIP Senders (comma separated)", value="boss@example.com, important@client.com")
keywords_input = st.sidebar.text_area("Keywords (comma separated)", value="urgent, invoice, project alpha")

st.sidebar.subheader("Execution Options")
depth_mode = st.sidebar.selectbox("Depth Mode", ["quick", "deep"])
output_mode = st.sidebar.selectbox("Output Mode", ["brief_only", "full_report"])

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
                # --- Supabase Configuration ---
                # Replace these with your actual Supabase project URL and Anon Key
                SUPABASE_URL = "https://nklvdwywvabddoemmadh.supabase.co/rest/v1/feedback"
                SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5rbHZkd3l3dmFiZGRvZW1tYWRoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkxNDMwNTYsImV4cCI6MjA4NDcxOTA1Nn0.Q7BBC9j_P3SzGll2q6wZMWef05_xpDqAY9jGWKYkmz0"
                
                payload = {
                    "rating": rating,
                    "comments": comments.strip()
                }
                
                # Prevent sending if placeholders are not updated
                if not SUPABASE_URL or "YOUR_PROJECT_REF" in SUPABASE_URL:
                    st.warning("Feedback not sent: Supabase credentials are not configured yet. Please update app.py.")
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

# --- Main Area ---

if st.button("🚀 Run Agent", type="primary"):
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

render_feedback_section()
