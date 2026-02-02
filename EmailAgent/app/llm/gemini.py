import os
from dotenv import load_dotenv
from google import genai
import json

load_dotenv() 

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
print("Gemini key loaded:", bool(os.getenv("GEMINI_API_KEY")))

def call_gemini(prompt: str) -> str:
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text

def interpret_intent(user_prompt: str) -> dict:
    """
    Classifies the user prompt into a structured intent.
    Returns JSON string with keys: 'intent', 'parameters'.
    Intents: CHECK_INBOX, COMPOSE, EXIT, UNKNOWN
    """
    system_instruction = (
'''
You are an email command interpreter for a CLI email agent.

Classify the user's message into EXACTLY ONE of these intents:

INTENTS:

1. CHECK_INBOX
- User wants to read, check, search, filter, or list emails.
- Also use CHECK_INBOX when the user requests an action that REQUIRES existing emails (e.g., reply).
- Examples:
  - "check my inbox"
  - "show unread mails"
  - "any urgent emails?"
  - "show last 5 mails"

2. REPLY
- User wants to reply to an EXISTING email.
- This intent REQUIRES inbox context.
- Examples:
  - "reply to last mail"
  - "reply to that email"
  - "respond to the email from Supabase"
- If the user says "last" or "most recent", set filters.limit = 1.
- If the user specifies "last N mails" set filters.limit to N.
- If the user does not specify selection details, leave filters null so the caller can fetch and ask the user.

3. COMPOSE
- User wants to write or draft a NEW email.
- This intent does NOT require inbox context.
- Examples:
  - "write an email to HR"
  - "mail my professor about deadline"

4. UNKNOWN
- Anything that does not clearly match the above.

OUTPUT FORMAT (STRICT JSON ONLY):
Do NOT include markdown, explanations, or extra text.

{
  "intent": "CHECK_INBOX | REPLY | COMPOSE | UNKNOWN",
  "parameters": {
    "recipient": {
      "to": [],
      "cc": [],
      "bcc": []
    },
    "subject": string | null,
    "body": string | null,
    "attachments": []
  },
  "filters": {
    "priority": "HIGH" | "MEDIUM" | "LOW" | "ANY" | null,
    "time_range": string | null,
    "limit": integer | null
  }
}

RULES:
- Always include all keys exactly as shown.
- Do NOT invent defaults. Use null for any filter or parameter the user did not specify.
- If intent = CHECK_INBOX or REPLY:
  - Extract any explicit filters the user mentions (priority, time_range, limit).
  - If the user says "last" or "most recent", set limit = 1.
  - If no filters are specified by the user, return filters with null values (caller will fetch and ask).
- If intent = COMPOSE:
  - Extract recipient fields, subject, body, and attachments exactly as specified by the user.
  - Do NOT add default recipients, subjects, or filters.
  - If a field is not mentioned, use null (for strings) or an empty array (for recipient/attachments).
- If intent = UNKNOWN:
  - Leave parameters with null/empty values and filters null.
'''
   )
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"{system_instruction}\nUser Prompt: {user_prompt}"
    )

    raw_text = (
        response.text
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Gemini returned invalid JSON:\n{raw_text}") from e

    return parsed
