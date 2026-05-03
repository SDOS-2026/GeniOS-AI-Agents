# EmailAgent API Reference

The EmailAgent service runs on **Port 8002** (or via the Gateway at `/email`). It uses a stateful LangGraph workflow that supports long-running threads with human-in-the-loop interrupts.

## Base URLs
- **Direct**: `http://localhost:8002`
- **Via Gateway**: `http://localhost:8000/email`

---

## 1. Start a Task
**Endpoint**: `POST /run`

Initiates a new agent workflow based on a natural language prompt.

**Request Body**:
```json
{
  "prompt": "Compose an email to satvik@example.com about the project update"
}
```

**Response (Interrupted)**:
If the agent needs your input (e.g., to review a draft), it will return a `thread_id` and an `interrupt_payload`.
```json
{
  "thread_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "interrupted",
  "interrupt_payload": {
    "type": "draft_review",
    "draft": "Subject: Project Update\n\nHi Satvik, here is the update...",
    "recipient": "satvik@example.com"
  }
}
```

---

## 2. Resume a Task
**Endpoint**: `POST /resume`

Sends a decision back to an interrupted agent.

**Request Body**:
```json
{
  "thread_id": "550e8400-e29b-41d4-a716-446655440000",
  "response": "Approve"
}
```
*Note: The response value depends on what the agent is waiting for (e.g., "Approve", "Cancel", or a modified prompt).*

**Response**:
```json
{
  "thread_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "done",
  "result": { "sent": true }
}
```

---

## 3. Get Thread State
**Endpoint**: `GET /state/{thread_id}`

Retrieves the current values persisted in the database for a specific thread.

**Response**:
```json
{
  "user_prompt": "Compose an email...",
  "emails": [],
  "draft": "...",
  "interrupt_type": "draft_review",
  "sent": false
}
```

---

## 4. Health Check
**Endpoint**: `GET /health`

**Response**:
```json
{
  "service": "email",
  "status": "ok"
}
```
