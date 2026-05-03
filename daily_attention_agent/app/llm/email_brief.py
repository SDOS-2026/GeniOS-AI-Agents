from daily_attention_agent.app.llm.client import get_llm, GEMINI_MODEL
import json
from daily_attention_agent.app.models.llm_output import EmailBrief
from pydantic import ValidationError

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
        Sender: {signal.raw_metadata.get("last_sender","")}
        """
        
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config={"temperature": 0.3},
            )

            text = response.text.strip()
            
            # Clean up markdown code blocks if present
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()

            data = json.loads(text)
            validated = EmailBrief(**data)
            results[signal.record_id] = validated.model_dump()

        except Exception as e:
            print(f"[WARNING] Gemini briefing failed for {signal.record_id}, falling back to Groq: {e}")
            from daily_attention_agent.app.llm.client import groq_email_brief
            fallback_brief = groq_email_brief(prompt)
            
            if fallback_brief:
                results[signal.record_id] = fallback_brief
            else:
                results[signal.record_id] = {
                    "brief": f"(Briefing failed) {signal.title}",
                    "reasoning": ["Validation error or service unavailable"]
                }

    return results
