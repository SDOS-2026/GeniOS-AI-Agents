# EmailAgent

EmailAgent is a command-line assistant for reading, drafting, and sending email. It is designed to be safe, stateful, and predictable. Drafts are created from explicit user intent, replies preserve Gmail thread context and messages are only sent after explicit user approval.



---

## Key Functionalities

### 1. Smart Email Ingestion & Classification
*   **Fetch & Organize**: Retrieves recent email threads from Gmail.
*   **Granular Classification**: Automatically categorizes emails using a deterministic keyword-based engine (no LLM cost for this step):
    *   **Sender Type**: Distinguishes between Humans, Organizations, and No-Reply bots.
    *   **Intent**: Identifies if an email requires a reply, is purely informational, or is spam/junk.
    *   **Priority Scoring**: assigns a priority score (High/Medium/Low) based on sender importance and keywords.

### 2. Context-Aware Drafting (RAG)
*   **Memory & Retrieval**: Utilizes **Supabase (pgvector)** to store and retrieve past interactions.
*   **Adaptive Tone**: When drafting a reply or a new email, the agent searches `reply_memory` and `compose_prompt_memory` for similar past successful emails.
*   **Thread Context**: Ingests the full body of previous messages in a thread to ensure replies are factually correct and contextually relevant.

### 3. Interactive CLI Workflow
*   **Inbox Review**: Browse through your classified inbox directly in the terminal.
*   **Summarization**: On-demand summarization of long threads.
*   **Looping Feedback**:
    *   Drafts are presented for review.
    *   You can choose to **EDIT** (refine the prompt and regenerate), **SEND**, or **CANCEL**.

### 4. Safety & Human-in-the-Loop
*   **No Auto-Send**: The agent *never* sends an email without explicit user confirmation.
*   **Draft-First Approach**: All actions result in a Gmail draft first.
*   **Automated Guardrails**:
    *   **G1: PII Protection**: Scans drafts for sensitive data (SSNs, credit cards, API keys, passwords) and prevents accidental leakage.
    *   **G2: Domain Restriction**: Validates recipient domains against allow/block lists. Automatically blocks sending PII to external/unauthorized domains.
    *   **G3: Tone Enforcement**: Analyzes drafts for aggressive language, liability risks (e.g., "guarantee", "promise"), and unprofessional slang to maintain professional standards.
*   **Risk Assessment**: (Optional/Legacy) Logic to flag potential risks in generated content.

### 5. Long-term Memory
*   **Agent Episodes**: Tracks every interaction session.
*   **Learning**: As you edit and approve drafts, the system indexes the final version. Future drafts improve by learning from your specific writing style and preferences stored in the database.


---

## Quick start

1. **Clone repository and checkout branch**
   ```bash
   git clone https://github.com/Satvik-Singh-22/emailagent.git
   cd emailagent
    ```
2. **Create and activate a Python virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux / macOS
   # venv\Scripts\activate    # Windows (PowerShell)
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Obtain and configure Gmail API credentials**

   * Enable the Gmail API in Google Cloud Console.
   * Create OAuth 2.0 client credentials and download the JSON file.
   * Place the downloaded credentials file in the **project root directory** (same level as `main.py`).

5. **Provide LLM and database API keys**

   * An example environment file is provided as `.env.example`.

   Steps:
   1. Create a new file named `.env` in the project root.
   2. Copy the contents of `.env.example` into `.env`.
   3. Replace the placeholder values with your actual keys (e.g., Gemini API key).

6. **Run the program**

   ```bash
   python main.py
   ```

---

## Configuration (environment variables)

Runtime configuration is handled via a `.env` file in the project root.

The repository includes a template:
- `.env.example` — reference template (do not modify directly)

You must create:
- `.env` — actual environment configuration

Required variables:

- `GEMINI_API_KEY` — API key for the Gemini LLM.
- Any additional variables listed in `.env.example` that are required by your setup.

Gmail OAuth credentials:
- The OAuth client credentials JSON file must be present in the **root directory**.
- The application uses the local authentication flow defined in the codebase to access Gmail.

---

## Supabase Database Setup (Memory & Retrieval)

The project uses **Supabase** to store agent episodes, reply history, and embeddings for future retrieval and context-awareness.

This section explains how to create the required tables and enable vector embeddings.

---

### 1. Agent Episodes Table

Stores a high-level record of each agent interaction (compose, reply, etc.).

```sql
create table agent_episodes (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,

  intent text not null,
  outcome text not null,

  created_at timestamptz default now()
);
```

**Purpose**

* Tracks what the agent attempted (intent)
* Records the final outcome (sent, canceled, edited, etc.)
* Acts as a parent record for memory tables

---

### 2. Reply Memory Table

Stores memory for **reply flows**, including summaries and vector embeddings for semantic retrieval.

```sql
create table reply_memory (
  id uuid primary key default gen_random_uuid(),
  episode_id uuid references agent_episodes(id) on delete cascade,

  original_email_summary text not null,
  reply_summary text not null,

  reply_body text,
  reply_embedding vector(768),

  metadata jsonb,
  created_at timestamptz default now()
);
```

**Purpose**

* Captures what the original email was about
* Stores how the agent replied
* Saves embeddings  for similarity search
* Enables future context reuse and personalization

---

### 3. Compose Prompt Memory Table

Stores memory for **new email composition** flows.

```sql
create table compose_prompt_memory (
  id uuid primary key default gen_random_uuid(),
  episode_id uuid references agent_episodes(id) on delete cascade,

  user_prompt text not null,
  draft_summary text not null,
  draft_body text,

  prompt_embedding vector(768),
  draft_embedding vector(768),

  metadata jsonb,
  created_at timestamptz default now()
);
```

**Purpose**

* Remembers how users phrase compose requests
* Stores generated draft summaries and bodies
* Useful for improving future drafting and retrieval

---

### 4. Priority Email Memory Table

Stores memory for **high-priority emails** (for example, urgent or critical messages) along with vector embeddings for later retrieval and analysis.

```sql
create table priority_email_memory (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,

  email_summary text not null,
  priority text not null check (priority in ('HIGH')),

  category text,
  source text,

  email_embedding vector(768),
  metadata jsonb,

  created_at timestamptz default now()
);
````

**Purpose**

* Persists summaries of high-priority emails
* Stores semantic embeddings for retrieval and ranking
* Enables long-term prioritization and learning
* Can be used for alerting, dashboards, or recall of critical messages

---

### 5. Vector Similarity Functions (Retrieval)

The following SQL functions enable **semantic retrieval** from stored memory using pgvector embeddings.

These functions are used to retrieve relevant past replies or compose prompts based on similarity to the current query.

---

#### 5.1 Match Reply Memory

Retrieves the most similar past replies for a given user.

```sql
create or replace function match_reply_memory (
  query_embedding vector(768),
  match_user_id text,
  match_count int
)
returns table (
  reply_summary text,
  original_email_summary text,
  metadata jsonb,
  similarity float
)
language sql
stable
as $$
  select
    rm.reply_summary,
    rm.original_email_summary,
    rm.metadata,
    1 - (rm.reply_embedding <-> query_embedding) as similarity
  from reply_memory rm
  join agent_episodes ae on rm.episode_id = ae.id
  where ae.user_id = match_user_id
  order by rm.reply_embedding <-> query_embedding
  limit match_count;
$$;
```

**Use case**

* Retrieve similar past replies
* Maintain consistency in tone and structure
* Improve contextual awareness across sessions

---

#### 5.2 Match Compose Prompt Memory

Retrieves similar **successful compose prompts** for a user.

```sql
create or replace function match_compose_prompt_memory (
  query_embedding vector(768),
  match_user_id text,
  match_count int
)
returns table (
  user_prompt text,
  draft_summary text,
  metadata jsonb,
  outcome text,
  similarity float
)
language sql
stable
as $$
  select
    cpm.user_prompt,
    cpm.draft_summary,
    cpm.metadata,
    ae.outcome,
    1 - (cpm.prompt_embedding <-> query_embedding) as similarity
  from compose_prompt_memory cpm
  join agent_episodes ae on cpm.episode_id = ae.id
  where ae.user_id = match_user_id
    and ae.outcome in ('SENT', 'APPROVED')
  order by cpm.prompt_embedding <-> query_embedding
  limit match_count;
$$;
```

**Use case**

* Learn from previously approved or sent drafts
* Improve future email composition quality
* Personalize drafting style per user

---

### 6. How Memory Is Used by the Agent

At a high level:

* Each interaction creates an entry in `agent_episodes`
* Reply flows persist summaries and embeddings in `reply_memory`
* Compose flows persist prompts and drafts in `compose_prompt_memory`
* High-priority emails are stored separately in `priority_email_memory`
* Vector similarity functions enable semantic recall during drafting

This design allows the agent to:

* Remain stateless at runtime
* Build long-term personalized memory
* Improve drafting quality over time without re-training models

---
