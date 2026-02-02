import json

def clean_json(raw: str) -> str:
    raw = raw.strip()

    # Remove markdown fences
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1].strip()

    # Remove leading 'json' line (Gemini sometimes does this)
    if raw.lower().startswith("json"):
        raw = raw.split("\n", 1)[1].strip()

    return raw



def join(lst):
    return ", ".join(lst) if lst else ""
