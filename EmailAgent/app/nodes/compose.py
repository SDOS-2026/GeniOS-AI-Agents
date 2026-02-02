from app.llm.router import call_llm
from app.utils.reasoning import add_reasoning
import json
from app.memory.memory_utils import summarize_compose_memory
from app.utils.json_cleaner import *

def compose_node(state):
    prompt = state.get("user_prompt", "")
    edit_instructions = state.get("edit_instructions", "")
    current_draft = state.get("draft", "")

    recipients = state["recipient"]
    attachments = state["attachments"] or []
    subject = state.get("subject")
    body_hint = state.get("body")

    to_list = recipients.get("to", [])
    cc_list = recipients.get("cc", [])
    bcc_list = recipients.get("bcc", [])

    memories = state.get("compose_memory", []) or []
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
    

    # ================= EDIT MODE (JSON ONLY) =================
    if edit_instructions:

        safe_subject = json.dumps(subject)
        safe_to = json.dumps(to_list)
        safe_cc = json.dumps(cc_list)
        safe_bcc = json.dumps(bcc_list)
        safe_attachments = json.dumps(attachments)
        safe_body = json.dumps(current_draft)
        safe_edit = json.dumps(edit_instructions)

        add_reasoning(state, "User requested edits — applying requested changes while preserving unchanged fields.")
        llm_prompt = f"""
You are a STRICT EMAIL EDITOR.

Return ONLY valid JSON.
NO prose. NO explanations. NO markdown.

Current Email State:
{{
  "subject": {json.dumps(subject)},
  "draft": {json.dumps(current_draft)},
  "recipient": {{
    "to": {safe_to},
    "cc": {safe_cc},
    "bcc": {safe_bcc}
  }},
  "attachments": {attachments},
  "tone": {json.dumps(state.get("tone"))},
  "brevity": {json.dumps(state.get("brevity"))},
  "summary": {json.dumps(state.get("summary"))}
}}

User Requested Changes:
{safe_edit}

IMPORTANT:

- The following fields are mutable arrays and MUST be updated deterministically if mentioned:
  recipient.to, recipient.cc, recipient.bcc, attachments

- Apply add/remove operations EXACTLY as requested.
- Removed items MUST NOT appear in the output.
- Added items MUST appear in the correct array.
- Fields not mentioned by the user MUST be copied unchanged.
- You MUST NOT ignore requested changes.

- Preserve the existing tone unless the user explicitly requests a tone change.
- Do NOT add placeholders.
- Preserve the existing signature; otherwise use "Email Agent" or leave blank.



JSON SCHEMA (MUST MATCH EXACTLY):

{{
  "subject": string,
  "draft": string,
  "recipient": {{
    "to": string[],
    "cc": string[],
    "bcc": string[]
  }},
  "attachments": string[],
  "body": string
}}

Current Email:
{{
  "subject": {json.dumps(subject)},
  "draft": {json.dumps(current_draft)},
  "recipient": {{
    "to": {to_list},
    "cc": {cc_list},
    "bcc": {bcc_list}
  }},
  "attachments": {attachments},
  "tone": {json.dumps(state.get("tone"))},
  "brevity": {json.dumps(state.get("brevity"))},
  "summary": {json.dumps(state.get("summary"))}
}}

User Requested Changes:
{edit_instructions}

IMPORTANT:
- The following fields are MUTABLE ARRAYS and MUST be updated deterministically if mentioned:
  - recipient.to
  - recipient.cc
  - recipient.bcc
  - attachments

- Apply add/remove operations EXACTLY as requested.
- If an item is removed, it MUST NOT appear in the output array.
- If an item is added, it MUST appear in the correct output array.
- If a field is NOT mentioned by the user, copy it unchanged.
- You MUST NOT ignore requested changes.

- Do NOT add placeholders like [Your Name].
- Preserve the existing signature OR use 'Email Agent' OR leave blank.
JSON SCHEMA (MUST MATCH EXACTLY):

{{
  "subject": string,
  "draft": string,
  "recipient": {{
    "to": string[],
    "cc": string[],
    "bcc": string[]
  }},
  "attachments": string[],
  "tone": string,
  "brevity": string,
  "summary": string
}}
"""

        raw = call_llm(llm_prompt, "compose").strip()
        raw= clean_json(raw)
        try:
            # print(raw)
            data = json.loads(raw)
        except json.JSONDecodeError:
            print("❌ Gemini failed to return valid JSON. Edit aborted.")
            state["edit_instructions"] = None
            return state

        # ✅ Apply Gemini edits
        state["subject"] = data["subject"]
        state["recipient"] = data["recipient"]
        state["attachments"] = data["attachments"]
        state["draft"] = data["draft"]
        state["approval_status"] = "REQUIRED"
        state["summary"] = f"Draft prepared for {join(data['recipient']['to']) or 'Unknown'}"
        state["risk_flags"] = ["USER_COMPOSE"]
        state["edit_instructions"] = None
        add_reasoning(state, "Edits applied to draft.")
        return state

    # ================= CREATE MODE (JSON ONLY) =================
    add_reasoning(state, "Creating a new email draft with metadata from the provided intent.")
    llm_prompt = f"""
You are an email writing assistant.

Return ONLY valid JSON.
NO prose. NO explanations. NO markdown.

Context:
To: {join(to_list)}
CC: {join(cc_list)}
BCC: {join(bcc_list)}
Attachments: {attachments}
Existing Subject: {subject}
User Intent: {body_hint or prompt}

Style Hints:
{tone_hint}
{brevity_hint}

Rules:
- If Subject is missing, generate one (MUST be ≤ 8 words).
- Output format:

SUBJECT: <subject>
BODY:
<email body>

- Do NOT include To/CC/BCC in the body.
- Use a professional tone by default.
- If the user explicitly requests a different tone, follow it exactly.
- Do NOT add placeholders.
- Preserve an existing signature; otherwise use "Email Agent" or leave blank.
- No reasoning, explanations, or meta text.
- Output email content only.


JSON SCHEMA (MUST MATCH EXACTLY):

{{
  "subject": string,
  "draft": string,
  "recipient": {{
    "to": string[],
    "cc": string[],
    "bcc": string[]
  }},
  "attachments": string[],
  "tone": string,
  "brevity": string,
  "summary": string
}}
"""

    raw = call_llm(llm_prompt, "compose").strip()
    raw= clean_json(raw)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print(raw)
        print("❌ Gemini failed to return valid JSON. Fallback to simple creation.")
        # Fallback is dangerous here if we need metadata, but for now let's just error or retry? 
        # Ideally we'd retry. For this iteration, let's assume valid JSON or fail.
        # To be safe, we can raise or return a basic error state, but let's try to recover if possible or just fail.
        add_reasoning(state, "JSON generation failed.")
        return state


    state["subject"] = data["subject"]
    state["draft"] = data["draft"]
    state["recipient"] = data["recipient"]
    state["attachments"] = data["attachments"]
    state["tone"] = data["tone"]
    state["brevity"] = data["brevity"]
    state["summary"] = data["summary"]

    print(state["summary"])
    state["approval_status"] = "REQUIRED"
    state["risk_flags"] = ["USER_COMPOSE"]

    add_reasoning(state, "Draft and metadata created.")
    
    state["draft_metadata"] = {
      "tone": data.get("metadata", {}).get("tone") or memory_prefs.get("tone") or "professional",
      "brevity": data.get("metadata", {}).get("brevity") or memory_prefs.get("brevity") or "default",
      "summary": data.get("metadata", {}).get("summary")
    }

    return state
