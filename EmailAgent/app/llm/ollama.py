import requests
import os

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

def _fallback_response(task: str, error_text: str) -> str:
    task = (task or "").lower()

    if task in {"drafting", "summarization"}:
        return ""

    if task == "compose":
        return (
            '{"subject":"Draft","draft":"Thank you for your email. I will review and respond shortly.",'
            '"recipient":{"to":[],"cc":[],"bcc":[]},"attachments":[],"tone":"professional",'
            '"brevity":"default","summary":"Draft created from fallback."}'
        )

    return (
        '{"priority":"MEDIUM","category":"FYI","intent":"WAIT",'
        f'"confidence":0.2,"reasoning":"{error_text}"'
        "}"
    )


def call_ollama(prompt: str, task: str = "general") -> str:
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": "llama3.1:latest",
                "prompt": prompt,
                "stream": False
            },
            timeout=60
        )

        if resp.status_code != 200:
            return _fallback_response(task, "Ollama HTTP error")

        data = resp.json()

        if "response" in data:
            return data["response"]

        if "error" in data:
            return _fallback_response(task, f"Ollama error: {data['error']}")

        # Unknown shape
        return _fallback_response(task, "Ollama returned unexpected payload")

    except Exception:
        return _fallback_response(task, "Ollama exception occurred")
