from app.llm.gemini import call_gemini
from app.llm.ollama import call_ollama
from google.genai.errors import ClientError
from app.guardrails.pii_detector import PIIDetector

# Instantiate PII Detector
pii_detector = PIIDetector()

def call_llm(prompt: str, task: str) -> str:
    # --- PII Guardrail Integration ---
    # Scrub potential PII from the prompt before it leaves the system
    safe_prompt = pii_detector.anonymize_text(prompt)
    
    if safe_prompt != prompt:
        print(f"🛡️ PII Guardrail activated: Scrubbed sensitive data from '{task}' prompt.")
        # Optional: log scrubbed diffs if valid logging setup exists
        
    try:
        return call_gemini(safe_prompt)
    except ClientError as e:
        # Quota / rate limit / API errors
        print(f"⚠️ Gemini failed ({task}):", e)
        return call_ollama(safe_prompt)
    except Exception as e:
        print(f"⚠️ LLM error ({task}):", e)
        return call_ollama(safe_prompt)
