import requests
import os

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

def call_ollama(prompt: str) -> str:
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
            return '{"priority":"MEDIUM","category":"FYI","intent":"WAIT","confidence":0.2,"reasoning":"Ollama HTTP error"}'

        data = resp.json()

        if "response" in data:
            return data["response"]

        if "error" in data:
            return '{"priority":"MEDIUM","category":"FYI","intent":"WAIT","confidence":0.2,"reasoning":"Ollama error: ' + data["error"] + '"}'

        # Unknown shape
        return '{"priority":"MEDIUM","category":"FYI","intent":"WAIT","confidence":0.2,"reasoning":"Ollama returned unexpected payload"}'

    except Exception as e:
        return '{"priority":"MEDIUM","category":"FYI","intent":"WAIT","confidence":0.1,"reasoning":"Ollama exception occurred"}'
