# Email Agent Workflow & Logic

This document describes the low-level logic and exact workflow of the `email_agent`. It covers the architecture, main execution paths, and detailed function (node) logic.

## 1. Architecture Overview

The Email Agent is built using **LangGraph**, a framework for building stateful, multi-agent applications with LLMs. The core of the agent is a **State Graph** that manages the transitions between different logical steps (nodes) while maintaining a persistent state.

- **Framework**: LangGraph
- **LLM**: Google Gemini (Pro/Flash)
- **Email Service**: Gmail API
- **Memory/Database**: Supabase (PostgreSQL with pgvector for embeddings)
- **State Management**: `EmailAgentState` (tracks prompt, intent, emails, drafts, etc.)

---

## 2. Main Execution Paths

The agent's behavior is driven by the user's initial prompt, which is parsed to determine one of three primary "modes" (intents):

### A. Inbox Check Path (`CHECK_INBOX`)
1. **Input Agent**: Detects "Check Inbox" intent.
2. **Fetch**: Retrieves latest emails from Gmail based on filters (e.g., "latest 5", "high priority").
3. **Classify**: Each email is analyzed by LLM-based classifiers for priority, category, and intent.
4. **Inbox Review**: Presents a sorted list to the user.
5. **Action Loop**:
    - **Summarize**: LLM generates a concise summary of a selected email.
    - **Reply**: Transitions to the **Reply Path**.
    - **Done**: Ends the session and writes to memory.

### B. Reply Path (`REPLY`)
1. **Input Agent**: Detects "Reply" intent (or triggered from Inbox Review).
2. **Memory Retrieve**: Fetches relevant historical context (similar past replies) to maintain tone and consistency.
3. **Draft**: LLM generates a reply draft based on the original email, summary, and retrieved memory.
4. **Review**: Shows the draft to the user.
5. **Finalize**: User chooses to **Send**, **Edit** (loops back to Compose node with instructions), or **Cancel**.

### C. Compose Path (`COMPOSE`)
1. **Input Agent**: Detects "Compose" intent.
2. **Memory Retrieve**: Fetches relevant context (past cold emails or style preferences).
3. **Compose**: LLM generates a new email draft and metadata (subject, recipients) in JSON format.
4. **Review**: Shows the draft to the user.
5. **Finalize**: User chooses to **Send**, **Edit**, or **Cancel**.

---

## 3. Node-by-Node Logic

### `input_agent_node` (`app/nodes/input_agent.py`)
- **Purpose**: Acts as the initial router.
- **Logic**:
    - Sends the user prompt to Gemini (`interpret_intent`).
    - Normalizes the response into a structured JSON: `intent`, `parameters` (to, cc, subject, body), and `filters` (priority, limit).
    - If the LLM fails, a regex-based `_fallback_intent` is used to catch common keywords.
    - Sets the `mode` in the graph state.

### `fetch_node` (`app/nodes/fetch.py`)
- **Purpose**: Interfaces with Gmail API.
- **Logic**:
    - Reads `filter_criteria` from state.
    - If priority filtering is requested, it fetches more emails (e.g., 20) to ensure high-priority ones are captured after classification.
    - Calls `fetch_recent_emails` to get raw email data from Gmail.

### `classify_node` (`app/nodes/classify.py`)
- **Purpose**: Enriches emails with semantic metadata.
- **Logic**:
    - Iterates through fetched emails.
    - **Sender Classifier**: Identifies the sender's role or relationship.
    - **Intent Scanner**: Scans subject/body for "action required" or specific intents.
    - **Priority Scorer**: Calculates a score (HIGH, MEDIUM, LOW) based on the sender, content, and urgency.
    - Appends the `classification` object to each email.

### `inbox_review_node` (`app/nodes/inbox_review.py`)
- **Purpose**: Human-in-the-loop interaction for the inbox.
- **Logic**:
    - Filters and sorts emails by priority.
    - Prints a formatted list to the console.
    - Waits for user input to select an email index.
    - Asks for an action: `Summarize` or `Reply`.
    - Updates `user_action` in the state to drive the next graph transition.

### `summarize_node` (`app/nodes/summarize.py`)
- **Purpose**: Condenses email threads.
- **Logic**:
    - Sends the raw email content to Gemini with strict rules (factual, concise, no markdown).
    - Prints the summary and waits for the user to acknowledge before returning to the inbox list.

### `draft_node` / `compose_node` (`app/nodes/draft.py`, `app/nodes/compose.py`)
- **Purpose**: Generates the actual email content.
- **Logic**:
    - **Draft**: Specifically for replies. Uses `original_email_summary` and `reply_memory` to ensure context-aware responses.
    - **Compose**: For new emails. Can handle "Edit Mode" where it takes `edit_instructions` and the `current_draft` to refine the email using a JSON-strict LLM prompt.
    - Both use "Style Hints" (tone, brevity) extracted from memory.

### `review_node` (`app/nodes/review.py`)
- **Purpose**: Final approval gate.
- **Logic**:
    - Displays the draft (To, CC, Subject, Body) and the agent's "Reasoning" (transparency).
    - Asks the user for `[S]end`, `[E]dit`, or `[C]ancel`.
    - If `Edit`, it captures user instructions and sets the path back to the compose node.

### `send_node` (`app/nodes/send.py`)
- **Purpose**: Executes the Gmail send operation.
- **Logic**:
    - Validates recipients (no overlap between To/CC/BCC).
    - Uses `send_email` helper to construct a MIME message.
    - Handles threading by attaching `thread_id` and `in_reply_to` headers if it's a reply.

### `memory_write_node` (`app/memory/memory_write.py`)
- **Purpose**: Persists episodic memory.
- **Logic**:
    - Creates an `episode` record in Supabase.
    - Depending on the outcome, writes to:
        - `reply_memory`: Original summary + reply body + embedding.
        - `compose_prompt_memory`: User prompt + draft body + embedding.
        - `priority_email_memory`: Email content + classification result + embedding.
    - Embeddings allow for semantic retrieval in future interactions.

---

## 4. Low-Level Logic Details

### Intent Recognition
The agent doesn't just look for keywords. It uses a structured prompt to Gemini to extract a schema. For example:
- *"Send a mail to Alice about the meeting tomorrow"* -> `intent: COMPOSE`, `parameters.recipient.to: [alice@example.com]`, `parameters.subject: Meeting tomorrow`.

### Memory Retrieval
Before drafting, the agent performs a Vector Search (using `pgvector`) to find "memories" similar to the current context.
- For **Compose**: Searches past prompts.
- For **Reply**: Searches past replies to similar emails.
The results are used to "prime" the LLM with the user's typical tone and style.

### Resilience & Fallbacks
- **JSON Cleaning**: Uses `json_cleaner.py` to strip LLM-generated prose/markdown from JSON responses.
- **Fallback Intents**: If Gemini is down or fails, regex logic ensures "Check inbox" still works.
- **Safety**: Strict rules in prompts forbid the LLM from making financial or contractual commitments automatically.
