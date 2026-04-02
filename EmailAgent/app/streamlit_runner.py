from __future__ import annotations

import contextlib
import io
import json
import sys
from datetime import datetime
from typing import Any

from app.gmail.client import get_gmail_service
from app.gmail.send import send_email
from app.llm.router import call_llm
from app.nodes.classify import classify_node
from app.nodes.compose import compose_node
from app.nodes.draft import draft_node
from app.nodes.fetch import fetch_node
from app.nodes.input_agent import input_agent_node
from app.utils.json_cleaner import join


def _fallback_summary(thread: dict[str, Any]) -> str:
    sender = str(thread.get("from") or "Unknown sender").strip()
    subject = str(thread.get("subject") or "No subject").strip()
    body = str(thread.get("body") or thread.get("snippet") or "").strip()

    if not body:
        return f"Email from {sender} about '{subject}'."

    lines = [line.strip() for line in body.splitlines() if line.strip()]
    preview = " ".join(lines[:2])
    if len(preview) > 220:
        preview = preview[:217].rstrip() + "..."

    return f"Email from {sender} about '{subject}'. Key message: {preview}"


def _json_safe(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        try:
            return _json_safe(value.model_dump(mode="json"))
        except TypeError:
            return _json_safe(value.model_dump())

    if hasattr(value, "dict") and callable(value.dict):
        try:
            return _json_safe(value.dict())
        except Exception:
            pass

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, dict):
        return {str(key): _json_safe(val) for key, val in value.items()}

    if isinstance(value, list):
        return [_json_safe(item) for item in value]

    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]

    if isinstance(value, set):
        return [_json_safe(item) for item in sorted(value, key=str)]

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    return str(value)


def analyze_prompt(payload: dict[str, Any]) -> dict[str, Any]:
    state = {
        "user_prompt": payload.get("user_prompt", ""),
        "user_id": payload.get("user_id", "default_user"),
        "thread_id": payload.get("thread_id", "unified_session"),
        "emails": [],
        "filter_criteria": {},
        "mode": "UNKNOWN",
    }

    with contextlib.redirect_stdout(io.StringIO()):
        analyzed = input_agent_node(state)

    return _json_safe(analyzed)


def fetch_inbox(payload: dict[str, Any]) -> dict[str, Any]:
    state = {
        "filter_criteria": {
            "priority": payload.get("priority"),
            "time_range": payload.get("time_range"),
            "limit": payload.get("limit"),
        },
        "emails": [],
        "raw_thread": None,
        "user_id": payload.get("user_id", "default_user"),
        "thread_id": payload.get("thread_id", "unified_session"),
    }

    if payload.get("user_prompt"):
        state["user_prompt"] = payload["user_prompt"]
        with contextlib.redirect_stdout(io.StringIO()):
            state = input_agent_node(state)

    with contextlib.redirect_stdout(io.StringIO()):
        state = fetch_node(state)
        state = classify_node(state)

    return _json_safe(state)


def summarize_thread(payload: dict[str, Any]) -> dict[str, Any]:
    thread = payload.get("raw_thread") or {}

    prompt = f"""
You are an email summarization engine.

STRICT RULES:
- Summarize ONLY what is explicitly stated
- Follow the tone given in the email
- Infer the intent or urgency
- Do NOT give opinions or advice
- Do NOT include markdown
- Output plain text only (no JSON)

Write a concise factual summary.

Email thread:
{thread}
"""

    with contextlib.redirect_stdout(io.StringIO()):
        raw_response = call_llm(prompt, "summarization")

    summary = raw_response.strip()
    if not summary:
        summary = _fallback_summary(thread)

    return {"summary": summary}


def draft_reply(payload: dict[str, Any]) -> dict[str, Any]:
    state = {
        "raw_thread": payload.get("raw_thread") or {},
        "summary": payload.get("summary") or payload.get("raw_thread", {}).get("snippet", ""),
        "classification": payload.get("classification") or {},
        "risk_flags": payload.get("risk_flags") or [],
        "approval_status": payload.get("approval_status", "REQUIRED"),
        "reply_memory": payload.get("reply_memory") or [],
        "compose_memory": payload.get("compose_memory") or [],
        "show_reasoning": False,
        "reasoning": [],
    }

    with contextlib.redirect_stdout(io.StringIO()):
        updated = draft_node(state)

    return _json_safe(updated)


def compose_email(payload: dict[str, Any]) -> dict[str, Any]:
    recipients = payload.get("recipient") or {
        "to": payload.get("to") or [],
        "cc": payload.get("cc") or [],
        "bcc": payload.get("bcc") or [],
    }

    state = {
        "user_prompt": payload.get("user_prompt", ""),
        "edit_instructions": payload.get("edit_instructions", ""),
        "draft": payload.get("draft", ""),
        "recipient": recipients,
        "attachments": payload.get("attachments") or [],
        "subject": payload.get("subject"),
        "body": payload.get("body"),
        "compose_memory": payload.get("compose_memory") or [],
        "tone": payload.get("tone"),
        "brevity": payload.get("brevity"),
        "summary": payload.get("summary"),
    }

    with contextlib.redirect_stdout(io.StringIO()):
        updated = compose_node(state)

    return _json_safe(updated)


def send_message(payload: dict[str, Any]) -> dict[str, Any]:
    approval_status = payload.get("approval_status", "APPROVED")
    if approval_status != "APPROVED":
        return {"ok": False, "error": "Email send blocked: approval required"}

    recipients = payload.get("recipient") or {}
    to_list = recipients.get("to") or payload.get("to") or []
    cc_list = recipients.get("cc") or payload.get("cc") or []
    bcc_list = recipients.get("bcc") or payload.get("bcc") or []

    subject = payload.get("subject", "")
    body = payload.get("draft") or payload.get("body") or ""
    thread_id = payload.get("thread_id")
    reply_message_id = payload.get("reply_message_id")
    attachments = payload.get("attachments") or []

    with contextlib.redirect_stdout(io.StringIO()):
        service = get_gmail_service()
        send_email(
            service=service,
            to=", ".join(to_list),
            subject=subject,
            body=body,
            approval_status=approval_status,
            cc=", ".join(cc_list) if cc_list else None,
            bcc=", ".join(bcc_list) if bcc_list else None,
            attachments=attachments,
            thread_id=thread_id,
            in_reply_to=reply_message_id,
            references=reply_message_id,
        )

    return {"ok": True, "message": "Email sent"}


COMMANDS = {
    "analyze_prompt": analyze_prompt,
    "fetch_inbox": fetch_inbox,
    "summarize_thread": summarize_thread,
    "draft_reply": draft_reply,
    "compose_email": compose_email,
    "send_message": send_message,
}


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "error": "Missing command"}), file=sys.stderr)
        return 2

    command = sys.argv[1]
    handler = COMMANDS.get(command)
    if handler is None:
        print(json.dumps({"ok": False, "error": f"Unknown command: {command}"}), file=sys.stderr)
        return 2

    payload_text = sys.stdin.read().strip()
    payload = json.loads(payload_text) if payload_text else {}

    try:
        result = handler(payload)
        print(json.dumps({"ok": True, "result": _json_safe(result)}))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())