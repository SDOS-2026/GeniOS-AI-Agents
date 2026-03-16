import os
import json
from dotenv import load_dotenv
from google import genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY missing from .env")

if not GEMINI_MODEL:
    raise RuntimeError("GEMINI_MODEL missing from .env")

client = genai.Client(api_key=GEMINI_API_KEY)


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
    • Events with many attendees may require preparation.
    • Calendar names can provide context about the event type.

    Important guidance:
    If multiple events appear to be part of a repeating schedule or routine timetable,
    they should receive LOW importance scores.

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
    
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt
    )


    text = response.text.strip()

    # DEBUG: show raw Gemini output
    # print("\n====== GEMINI RAW RESPONSE ======")
    # print(text)
    # print("=================================\n")


    if "```" in text:
        text = text.split("```")[1].replace("json", "").strip()

    text = text.replace("json", "").strip()

    data = json.loads(text)

    results = {item["id"]: item for item in data}

    print("[DEBUG] cal llm end")    
    return results