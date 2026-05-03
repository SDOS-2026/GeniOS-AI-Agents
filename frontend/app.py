import streamlit as st
import requests
import time
import os

# Gateway Configuration
# GATEWAY_URL = "http://localhost:8000"
GATEWAY_URL = os.getenv(
    "GATEWAY_URL",
    "http://localhost:8000"
)
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
