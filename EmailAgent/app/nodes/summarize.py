import re
from app.llm.router import call_llm
from langgraph.types import interrupt


def _fallback_summary(thread: dict) -> str:
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


def summarize_node(state):
    thread = state["raw_thread"]

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

    raw_response = call_llm(prompt, "summarization")

    # Defensive cleanup (LLMs sometimes add headers or bullets)
    summary = raw_response.strip()

    # Remove markdown if any slipped in
    summary = re.sub(r"^#+\s*", "", summary)
    summary = re.sub(r"^\*\s*", "", summary)

    # Absolute safety fallback
    if not summary:
        summary = _fallback_summary(thread)

    # Interrupt — let the frontend display the summary and acknowledge
    interrupt({
        "interrupt_type": "summarize_ack",
        "message": "I have summarized the email for you.",
        "summary": summary,
    })

    # resume value is ignored — any response continues the graph

    return {"summary": summary, "interrupt_type": "summarize_ack"}
