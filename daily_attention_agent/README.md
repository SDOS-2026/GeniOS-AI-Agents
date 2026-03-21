# Daily Attention Agent (V1) 🧠📬

An intelligent, read-only Executive Assistant Agent built with **LangGraph** and **Gemini 2.5 Flash**. It analyzes your Gmail and Google Calendar to surface critical updates, identify schedule risks, and prioritize your daily attention items.

---

## ✨ Core Features

### 📨 Smart Email Prioritization
- **LLM-Based Scoring**: Uses Gemini to evaluate the urgency and actionability of your emails.
- **5-Email Focus**: Automatically selects the 5 most recent emails to ensure a concise and focused briefing.
- **Intelligent Fallback**: If LLM quotas are reached, the system falls back to a deterministic rule-based engine (VIP senders, urgent keywords, staleness) so you never miss a beat.

### 📅 Calendar Risk Detection
- **Schedule Analysis**: Detects meeting conflicts, overloaded days, and back-to-back sessions.
- **Contextual Warnings**: Flags events missing meeting links or those scheduled during unusual hours.

### 🛡️ Robust Architecture
- **Persistent Caching**: Scores are cached in `email_llm_cache.json` and `calendar_llm_cache.json`. This avoids redundant LLM calls, maintains performance, and respects API rate limits.
- **State Management**: Built on **LangGraph**, ensuring a robust, stateful execution flow from fetching signals to generating the final brief.
- **Read-Only Security**: The agent uses restricted Google OAuth scopes. It can read your data but cannot send emails or modify your calendar.

---

## 🛠️ Setup & Configuration

### 1. Prerequisites
- Python 3.10+
- A Google Cloud Project with Gmail and Calendar APIs enabled.
- A Gemini API Key from [Google AI Studio](https://aistudio.google.com/).

### 2. Environment Variables
Create a `.env` file in the project root:

```env
# Gemini Config
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash

# Google OAuth Config
GOOGLE_CLIENT_ID=your_id
GOOGLE_CLIENT_SECRET=your_secret
GOOGLE_REFRESH_TOKEN=your_refresh_token
GOOGLE_TOKEN_URI=https://oauth2.googleapis.com/token
```

### 3. Usage
1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Run the Agent**:
   ```bash
   python -m app.main
   ```
3. **Interactive Menu**: Follow the terminal prompts to view your brief, toggle visibility settings, or refresh the feed.

---

## 📁 Project Structure

```text
daily_attention_agent/
├── app/
│   ├── main.py           # Entry point & Interactive Loop
│   ├── graph.py          # LangGraph Workflow Definition
│   ├── state.py          # DAAState Schema
│   ├── connectors/       # Gmail & Calendar API Integrations
│   ├── rules/            # Deterministic Scoring & LLM Fallbacks
│   ├── llm/              # Gemini Client & Batch Prioritization
│   └── models/           # Pydantic Data Models (UnifiedSignal, etc.)
├── email_llm_cache.json  # Persistent Email Cache
├── calendar_llm_cache.json # Persistent Calendar Cache
└── README.md
```

---

## 🔒 Security Guarantees
- **Read-Only**: The agent does not have permission to `write` or `delete` any data in your Google account.
- **Local Persistence**: Caches are stored locally on your machine.
- **Metadata Only**: The agent primarily focuses on email metadata and snippets to maintain privacy.