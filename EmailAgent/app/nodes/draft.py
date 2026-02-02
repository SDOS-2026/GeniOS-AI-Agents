from app.llm.router import call_llm
from app.memory.memory_utils import summarize_compose_memory


def draft_node(state):
    summary = state.get("summary", "")
    raw_thread = state.get("raw_thread", {})
    # print(raw_thread)
    classification = state.get("classification", {})
    risk_flags = state.get("risk_flags", [])
    approval_status = state.get("approval_status", "REQUIRED")

    # If approval is required, draft must be extra conservative
    conservative_mode = approval_status == "REQUIRED"
    memories = state.get("reply_memory", []) or []
    memory_prefs = summarize_compose_memory(memories)

    tone_hint = (
        f"Use a {memory_prefs['tone']} tone."
        if memory_prefs.get("tone")
        else ""
    )

    brevity_hint = (
        "Keep the email concise."
        if memory_prefs.get("brevity") == "concise"
        else ""
    )

    prompt = fprompt = f"""
You are an email reply drafting assistant.

TASK:
Write a professional REPLY to an existing email.
This is a DRAFT ONLY.

Context:
Conversation summary:
{summary}

Original email being replied to:
From: {raw_thread.get("from")}
Subject: {raw_thread.get("subject")}
Body:
{raw_thread.get("body")}

Style Guidelines (if applicable):
{tone_hint}
{brevity_hint}

Email category: {classification.get("category")}
Email intent: {classification.get("intent")}
Risk flags: {risk_flags}

STYLE & TONE:
- Match the tone of the original email as closely as possible.
- If the original email's tone is unclear, default to a professional tone.
- If the user explicitly requested a different tone earlier, preserve it exactly.
- Be clear, polite, and context-aware.
- Do NOT overcommit or speculate.

STRICT RULES:
- Produce a reply DRAFT ONLY.
- Do NOT send anything.
- Do NOT make legal, financial, or contractual commitments.
- Do NOT confirm agreements, deadlines, or obligations unless explicitly stated in the original email.
- Ask clarifying questions if information is missing or ambiguous.
- Do NOT add placeholders (e.g., [Sender Name], [Your Name]).
- Preserve the existing signature if present; otherwise use "Email Agent" or leave blank.
- Do NOT mention To / CC / BCC in the body.
- No reasoning, explanations, or meta text.
- Never reference the system, context extraction, or drafting process.

RESPONSE BEHAVIOR:
If the original email content is missing or unclear:
- Do NOT mention missing context, system limitations, or lack of access.
- Write a natural human reply that politely asks the sender to clarify or expand.
- Assume the sender understands the context better than you.

OUTPUT FORMAT (STRICT):
<reply body text only>
"""


    raw_response = call_llm(prompt, "drafting")

    draft = raw_response.strip()
    subject = state["raw_thread"].get("subject", "")
    if subject and not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"
    state["subject"] = subject
    state["subject"] = subject

    # Absolute safety fallback
    if not draft:
        draft = (
            "Thank you for your message. I have reviewed the details and will "
            "get back to you after confirming internally."
        )

    state["draft"] = draft
    return state
