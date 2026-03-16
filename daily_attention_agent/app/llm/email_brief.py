from app.llm.client import get_llm, GEMINI_MODEL
import json


def generate_email_briefs(items):

    client = get_llm()

    results = {}

    for item in items:
        signal = item["signal"]
        prompt = f"""
You are generating a short attention brief for an email assistant.
Summarize the email in ONE SHORT sentence.
Provide 1-2 short reasons why it might need attention.
Return STRICT JSON:
{{
 "brief": "short one-line summary",
 "reasoning": ["short reason","short reason"]
}}
Email subject: {signal.title}
Snippet: {signal.snippet}
Sender: {signal.raw_metadata.get("sender","")}
"""
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config={"temperature": 0.3},
        )

        text = response.text.strip()

        # Remove markdown blocks if Gemini adds them
        if "```" in text:
            text = text.replace("```json", "").replace("```", "").strip()

        parsed = json.loads(text)

        results[signal.record_id] = parsed

    return results