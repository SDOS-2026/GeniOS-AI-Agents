**directory structure**


daily_attention_agent/
│
├── README.md
├── pyproject.toml / requirements.txt
├── .env.example
│
├── app/
│   ├── main.py                    # Entry point (API / CLI / job trigger)
│   ├── graph.py                   # LangGraph definition + wiring
│   ├── state.py                   # DAAState (single source of truth)
│
│   ├── config/
│   │   ├── defaults.py            # scoring thresholds, caps
│   │   ├── vip.py                 # VIP sender config
│   │   └── keywords.py            # urgency keywords
│
│   ├── connectors/                # Tool integrations (READ-ONLY)
│   │   ├── __init__.py
│   │   ├── base.py                # Connector contract
│   │   ├── gmail/
│   │   │   ├── client.py          # Auth + API calls
│   │   │   ├── fetch.py           # Fetch raw signals
│   │   │   └── normalize.py       # Gmail → UnifiedSignal
│   │   └── calendar/
│   │       ├── client.py
│   │       ├── fetch.py
│   │       └── normalize.py
│
│   ├── models/                    # Strict schemas (Pydantic)
│   │   ├── unified_signal.py
│   │   ├── attention_item.py
│   │   ├── evidence.py
│   │   └── action_payload.py
│
│   ├── rules/                     # Deterministic logic (NO LLM)
│   │   ├── email_rules.py
│   │   ├── calendar_rules.py
│   │   └── scoring.py
│
│   ├── llm/                       # Optional intelligence layer
│   │   ├── client.py              # OpenAI / provider wrapper
│   │   ├── prompts.py             # JSON-only prompts
│   │   ├── summarize.py
│   │   └── drafts.py
│
│   ├── brief/                     # Output assembly
│   │   ├── generator.py
│   │   └── formatter.py
│
│   ├── guardrails/                # Trust & safety
│   │   ├── validate_schema.py
│   │   ├── validate_evidence.py
│   │   ├── no_side_effects.py
│   │   └── cost_caps.py
│
│   ├── storage/                   # Persistence (V1 minimal)
│   │   ├── repository.py
│   │   └── models.py
│
│   └── utils/
│       ├── time.py
│       ├── dedupe.py
│       └── logging.py
│
├── tests/
│   ├── connectors/
│   ├── rules/
│   ├── graph/
│   └── fixtures/
│
└── scripts/
    ├── run_daily.py               # Scheduled run
    └── run_local.py               # Dev testing







# Daily Attention Agent (V1)

This project implements a read-only Executive Assistant Agent that analyzes
Gmail and Google Calendar to surface daily attention items.

---

## 🔐 Google OAuth Setup (Required)

This agent uses **read-only Google OAuth access** for:
- Gmail (metadata only)
- Google Calendar (events only)

No emails are sent.
No calendar events are modified.

---

### Required Environment Variables

Create a `.env` file in the project root with:

GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REFRESH_TOKEN=your_google_refresh_token
GOOGLE_TOKEN_URI=https://oauth2.googleapis.com/token


⚠️ Never commit `.env` to version control.

---

### How to Obtain Credentials

#### 1. Create Google Cloud Project
- Go to https://console.cloud.google.com/
- Create a new project

#### 2. Enable APIs
Enable:
- Gmail API
- Google Calendar API

#### 3. Configure OAuth Consent Screen
- Type: External
- Add scopes:
  - gmail.readonly
  - calendar.readonly
- Add your email as a test user

#### 4. Create OAuth Client ID
- Type: Desktop App
- Save Client ID and Client Secret

#### 5. Generate Refresh Token (One-Time)

Run the provided script:

```bash
python scripts/get_refresh_token.py
Authorize the app and copy the printed refresh token.

Running the Agent
pip install -r requirements.txt
python -m app.main
🔒 Security Guarantees
Read-only Google scopes

No email sending

No calendar modification

No token files written to disk

Credentials loaded from environment only


---