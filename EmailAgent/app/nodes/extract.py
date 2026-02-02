import json
import re
from app.llm.router import call_llm


def extract_node(state):
    thread = state["raw_thread"]

    prompt = f"""
You are an information extraction engine for emails.

STRICT RULES:
- Extract ONLY information explicitly present
- Do NOT infer missing data
- If something is unclear, mark it as ambiguous
- Output MUST be valid JSON
- Do NOT include markdown or explanations outside JSON

Extract the following fields:
- people: list of names mentioned
- organizations: list of organizations mentioned
- dates: list of explicit dates (ISO format if possible)
- deadlines: list of deadlines mentioned
- times: list of times mentioned
- actionable_entities: list (e.g. contract, invoice, meeting)
- ambiguities: list of unclear references

Email thread:
{thread}

OUTPUT FORMAT (JSON ONLY):
{{
  "people": [],
  "organizations": [],
  "dates": [],
  "deadlines": [],
  "times": [],
  "actionable_entities": [],
  "ambiguities": []
}}
"""

    raw_response = call_llm(prompt, "extraction")

    # --- Defensive JSON extraction ---
    def extract_json(text: str):
        try:
            return json.loads(text)
        except Exception:
            pass

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass

        return None

    extracted = extract_json(raw_response)

    # --- Safe fallback ---
    if extracted is None:
        extracted = {
            "people": [],
            "organizations": [],
            "dates": [],
            "deadlines": [],
            "times": [],
            "actionable_entities": [],
            "ambiguities": ["Extraction failed or unclear"]
        }

    state["extracted_details"] = extracted
    return state
