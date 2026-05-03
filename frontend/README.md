# GeniOS Frontend 🎨

The Streamlit-based graphical user interface for the GeniOS AI Agents. It provides an intuitive, interactive way to communicate with various backend agents (such as the Daily Attention Agent and EmailAgent) through the centralized GeniOS Gateway.

## 🏗️ Architecture Overview

The frontend is built using **Streamlit** to enable rapid development of data-rich web applications. 

- **Port**: 8501
- **Communication**: Interacts with the `gateway` on `http://localhost:8000` which proxies requests to the appropriate background services.
- **State Management**: Uses Streamlit's `st.session_state` to manage chat history, agent states, and user interactions within the session.

## 🚀 Setup & Execution

### 1. Prerequisites
Ensure the backend services (Gateway, MCP Server, EmailAgent, DAA) are running before starting the frontend, or you may face connection errors.

### 2. Running the Frontend
Start the Streamlit UI using the provided script:

```bash
bash start.sh
```

### 3. Usage
- Navigate to `http://localhost:8501` in your browser.
- Use the sidebar or main interface to select the agent you wish to interact with.
- The UI provides real-time feedback, status updates, and formatted outputs from the background agents.
