import requests

from app import config


class OllamaClient:
    """Thin wrapper over Ollama's /api/chat endpoint."""

    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def generate_report(self, system_prompt: str, user_prompt: str) -> str:
        response = requests.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                # Ollama's structural JSON mode: constrains generation to
                # syntactically valid JSON. Doesn't guarantee our schema
                # (the model can still emit valid JSON with the wrong keys),
                # which is why app/analyzer.py still validates the result -
                # this is a strong hint to the sampler, not a contract.
                "format": "json",
                "stream": False,
                # Low temperature: this is an incident report, not creative
                # writing - we want the same evidence to consistently
                # produce the same conclusion, not an interesting new one
                # each time.
                "options": {"temperature": 0.2},
            },
            timeout=config.OLLAMA_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()["message"]["content"]
