# Daily Attention Agent (DAA) API Reference

The Daily Attention Agent service runs on **Port 8001** (or via the Gateway at `/daa`). It processes data from multiple sources (via MCP) to prioritize your daily tasks and highlights risks/opportunities.

## Base URLs
- **Direct**: `http://localhost:8001`
- **Via Gateway**: `http://localhost:8000/daa`

---

## 1. Start an Agent Run
**Endpoint**: `POST /run`

Triggers a background analysis of your workspace and communications.

**Request Body**:
```json
{
  "user_id": "satvik_user",
  "workspace_id": "genios_workspace",
  "vip_senders": ["boss@company.com", "investor@venture.com"],
  "keywords": ["urgent", "deadline", "contract"],
  "depth_mode": "deep",
  "output_mode": "brief_only"
}
```

**Response**:
The agent runs in the background to avoid timeouts. It returns a `run_id` immediately.
```json
{
  "run_id": "93b1696e-6c0b-426b-8739-165f12345678",
  "status": "running"
}
```

---

## 2. Check Run Status & Results
**Endpoint**: `GET /status/{run_id}`

Retrieves the current status and the final result (once `status` is `"success"`).

**Response (Success)**:
```json
{
  "status": "success",
  "result": {
    "attention_items": [
      { "item": "Sign the vendor contract", "reason": "Deadline today", "priority": "High" }
    ],
    "risks": ["Upcoming server maintenance might affect deployment"],
    "opportunities": ["Potential collaboration with Design team mentioned in Slack"],
    "warnings": [],
    "run_completed_at": "2026-05-03T17:00:00Z"
  }
}
```

---

## 3. View Run History
**Endpoint**: `GET /history`

Returns a list of all recent agent runs and their current status.

**Response**:
```json
[
  { "run_id": "93b1696e...", "status": "success" },
  { "run_id": "82a0585d...", "status": "error" }
]
```

---

## 4. Root Endpoint
**Endpoint**: `GET /`

**Response**:
```json
{
  "message": "Daily Attention Agent service is running. POST to /run to execute."
}
```
