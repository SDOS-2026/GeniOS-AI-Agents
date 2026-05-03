import os
import json
from typing import List, Optional
from dotenv import load_dotenv
from google import genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY missing from .env")

if not GEMINI_MODEL:
    raise RuntimeError("GEMINI_MODEL missing from .env")

from daily_attention_agent.app.models.llm_output import BatchScoredResponse, ScoredItem
from pydantic import ValidationError

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

client = genai.Client(api_key=GEMINI_API_KEY)

def get_llm():
    return client

groq_client = None
if GROQ_API_KEY:
    try:
        from groq import Groq
        groq_client = Groq(api_key=GROQ_API_KEY)
    except ImportError:
        print("[WARNING] groq package not found. Groq fallback disabled.")

def groq_batch_priority(prompt: str) -> List[ScoredItem]:
    """
    Fallback call to Groq when Gemini fails.
    """
    if not groq_client:
        return []

    print("[DEBUG] groq fallback start")
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model=GROQ_MODEL,
            response_format={"type": "json_object"},
        )
        text = chat_completion.choices[0].message.content
        return safe_extract_batch(text)
    except Exception as e:
        print(f"[ERROR] Groq fallback failed: {e}")
        return []

def groq_email_brief(prompt: str) -> Optional[dict]:
    """
    Fallback call to Groq for email briefing.
    """
    if not groq_client:
        return None

    print("[DEBUG] groq brief fallback start")
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model=GROQ_MODEL,
            response_format={"type": "json_object"},
        )
        text = chat_completion.choices[0].message.content
        data = json.loads(text)
        from daily_attention_agent.app.models.llm_output import EmailBrief
        validated = EmailBrief(**data)
        return validated.model_dump()
    except Exception as e:
        print(f"[ERROR] Groq brief fallback failed: {e}")
        return None

def safe_extract_batch(text: str) -> List[ScoredItem]:
    """
    Safely parses and validates LLM output using Pydantic.
    """
    # Clean up markdown code blocks if present
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    
    text = text.strip()

    try:
        data = json.loads(text)
        # Handle cases where the LLM returns a naked list instead of a wrapped object
        if isinstance(data, list):
            validated = BatchScoredResponse(items=data)
        elif isinstance(data, dict) and "items" in data:
            validated = BatchScoredResponse(**data)
        else:
            # Try to force parse individual items if the structure is odd
            validated = BatchScoredResponse(items=data)
            
        return validated.items
    except (json.JSONDecodeError, ValidationError) as e:
        print(f"[ERROR] LLM Output Validation Failed: {e}")
        print(f"[DEBUG] Raw failed output: {text}")
        return []

def gemini_calendar_batch_priority(signals):
    print("[DEBUG] cal llm start")
    events = []

    for s in signals:
        meta = s.raw_metadata
        event_key = f"{s.record_id}_{s.timestamp.isoformat()}"

        events.append({
            "id": event_key,
            "calendar_context": meta.get("calendar_name"),
            "title": s.title,
            "description": s.snippet,
            "attendees": meta.get("attendee_count"),
            "has_link": meta.get("has_meet_link"),
            "time": str(s.timestamp),
        })

    prompt = f"""
    You are prioritizing calendar events for a personal assistant.
    The goal is to determine what deserves attention today.

    Key reasoning principles:
    • Unique commitments (deadlines, interviews, presentations, reviews) are higher priority.
    • Routine scheduled activities that occur frequently (classes, daily meetings, standing events) are lower priority.
    • Events happening soon should be prioritized slightly higher.
    • Events names can provide context about the event type.

    Score meaning:
    90-100 → critical commitment
    70-89 → important event requiring preparation
    40-69 → normal scheduled event
    10-39 → routine or low-importance event
    0-9 → informational reminder

    Return STRICT JSON list:
    [
    {{
        "id": "...",
        "score": number,
        "category": "commitment | meeting | routine | deadline | personal | other",
        "reasons": ["short explanation"]
    }}
    ]

    Events:
    {json.dumps(events, indent=2)}
    """
    
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
        items = safe_extract_batch(response.text)
    except Exception as e:
        print(f"[WARNING] Gemini cal scoring failed, falling back to Groq: {e}")
        items = groq_batch_priority(prompt)

    results = {item.id: item.model_dump() for item in items}
    print("[DEBUG] cal llm end")    
    return results

def gemini_gmail_batch_priority(signals):
    print("[DEBUG] gmail llm start")
    emails = []

    for s in signals:
        meta = s.raw_metadata

        emails.append({
            "id": s.record_id,
            "sender": meta.get("last_sender"),
            "subject": s.title,
            "snippet": s.snippet,
            "time": str(s.timestamp),
        })

    prompt = f"""
    You are prioritizing emails for a personal assistant.
    The goal is to determine which emails require immediate attention today.

    Key reasoning principles:
    • Action-oriented emails (requests for approval, meeting coordination, urgent questions) are higher priority.
    • VIP senders (executives, direct reports, key clients) are higher priority.
    • Informational emails (newsletters, status updates without action, generic announcements) are lower priority.
    • Personal emails or social notifications are lower priority.

    Score meaning:
    90-100 → critical action required immediately
    70-89 → important email needing attention today
    40-69 → normal business communication
    10-39 → low priority / informational news
    0-9 → spam or automated notifications

    Return STRICT JSON list:
    [
    {{
        "id": "...",
        "score": number,
        "category": "actionable | informational | social | promotional | personal | other",
        "reasons": ["short explanation"]
    }}
    ]

    Emails:
    {json.dumps(emails, indent=2)}
    """
    
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
        items = safe_extract_batch(response.text)
    except Exception as e:
        print(f"[WARNING] Gemini gmail scoring failed, falling back to Groq: {e}")
        items = groq_batch_priority(prompt)

    results = {item.id: item.model_dump() for item in items}
    print("[DEBUG] gmail llm end")    
    return results

