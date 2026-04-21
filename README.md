# GeniOS AI Agents 🧠🤖

Welcome to the **GeniOS AI Agents** repository. This project is a suite of intelligent, autonomous agents designed to streamline personal and professional workflows using state-of-the-art LLMs, graph-based orchestration, and long-term semantic memory.

---

## 🚀 Current Status: Active Development

The project currently consists of two core agentic systems, each focusing on a specific domain of productivity. Both agents leverage **Gemini 2.5 Flash** for reasoning and **LangGraph** for structured execution.

### 1. 📧 EmailAgent (V1.2)
A comprehensive Gmail assistant that goes beyond simple automation.
- **Intelligent Classification**: Automatically categorizes incoming mail by Sender Type, Intent, and Priority.
- **RAG-Powered Drafting**: Uses **Supabase (pgvector)** to remember your writing style and past interactions, ensuring every draft feels personal and contextually accurate.
- **Safety First**: Implements triple-guardrail protection (PII scanning, Domain validation, and Tone enforcement).
- **Human-in-the-Loop**: Never sends an email without explicit approval; creates drafts for your review first.

### 2. 📅 Daily Attention Agent (V1.0)
Your read-only Executive Assistant for a focused start to the day.
- **Signal Analysis**: Aggregates data from Gmail and Google Calendar.
- **Risk Detection**: Flags calendar conflicts, overloaded schedules, and missing meeting links.
- **Executive Briefing**: Generates a concise "Attention List" of the top items requiring your focus today.
- **Reliability**: Uses persistent local caching (`llm_cache.json`) and deterministic fallbacks to handle API rate limits gracefully.

---

## 🛠️ Tech Stack

| Component | Technology |
| :--- | :--- |
| **LLMs** | Gemini 2.5 Flash, Gemini 1.5 Pro |
| **Orchestration** | LangGraph (Stateful Workflows) |
| **Memory** | Supabase + pgvector (Semantic Retrieval) |
| **APIs** | Google Workspace (Gmail, Calendar) |
| **Safety** | Custom Regex-based PII Detectors, Domain Whitelisting |
| **UI/UX** | Interactive CLI (Streamlit Web Dashboard in progress) |

---

## 📂 Project Structure

```text
.
├── EmailAgent/               # Stateful Gmail drafting & classification agent
│   ├── app/                  # Logic, Graph, Nodes, and Memory implementation
│   └── main.py              # CLI Entry point
├── daily_attention_agent/    # Read-only summarization & risk detection agent
│   ├── app/                  # LangGraph workflow & connectors
│   └── email_llm_cache.json  # Local persistence
├── requirements.txt          # Root dependencies (unified interface)
└── README.md                 # This file
```

---

## 🎯 Upcoming Milestones

1.  **Unified Web Interface**: Migration of CLI tools to a unified **Streamlit** dashboard.
2.  **Cross-Agent Coordination**: Enabling the EmailAgent to use context from the Daily Attention Agent.
3.  **Slack/Jira Integration**: Expanding the signal sources to include enterprise communication tools.
4.  **Advanced Evaluation**: Implementing an Evals pipeline to measure agent performance and safety scores.

---

## ⚙️ Setup

Each agent contains its own environment configuration and requirements.
1.  Navigate to the specific agent directory (e.g., `cd EmailAgent`).
2.  Follow the setup instructions in the local `README.md`.
3.  Ensure your `.env` file is populated with the required Google and Gemini credentials.

---

*GeniOS: Intelligence where it matters most.*
