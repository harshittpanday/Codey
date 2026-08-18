from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib import error, request


class OllamaError(RuntimeError):
    """Raised when CodeY cannot communicate with the local Ollama server."""


@dataclass(frozen=True)
class OllamaClient:
    base_url: str = "http://127.0.0.1:11434"
    model: str = "qwen2.5-coder:3b"
    timeout: float = 120.0

    @classmethod
    def from_environment(cls) -> "OllamaClient":
        return cls(
            base_url=os.getenv("CODEY_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/"),
            model=os.getenv("CODEY_MODEL", "qwen2.5-coder:3b"),
        )

    def ask(self, prompt: str) -> str:
        if not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.base_url}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read()
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace").strip()
            raise OllamaError(f"Ollama returned HTTP {exc.code}: {detail or exc.reason}") from exc
        except error.URLError as exc:
            raise OllamaError(
                "Could not connect to Ollama at "
                f"{self.base_url}. Make sure Ollama is running."
            ) from exc
        except TimeoutError as exc:
            raise OllamaError("The Ollama request timed out.") from exc

        try:
            result = json.loads(raw)
            content = result["message"]["content"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise OllamaError("Ollama returned an invalid response.") from exc

        if not isinstance(content, str) or not content.strip():
            raise OllamaError("Ollama returned an empty response.")
        return content.strip()
