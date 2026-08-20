from __future__ import annotations
from dataclasses import dataclass
import httpx
class OllamaError(RuntimeError):pass
@dataclass(frozen=True)
class OllamaClient:
    base_url:str;model:str;timeout:float
    def ask(self,prompt:str)->str:
        if not prompt.strip():raise ValueError("Prompt cannot be empty.")
        try:
            with httpx.Client(timeout=self.timeout) as client:r=client.post(f"{self.base_url}/api/generate",json={"model":self.model,"prompt":prompt,"stream":False,"options":{"temperature":0.1}});r.raise_for_status()
        except httpx.ConnectError as e:raise OllamaError(f"Could not connect to Ollama at {self.base_url}. Make sure Ollama is running.") from e
        except httpx.TimeoutException as e:raise OllamaError(f"The Ollama request timed out after {self.timeout:g}s. Try a smaller context budget or increase CODEY_OLLAMA_TIMEOUT.") from e
        except httpx.HTTPStatusError as e:raise OllamaError(f"Ollama returned HTTP {e.response.status_code}: {e.response.text[:500]}") from e
        except httpx.HTTPError as e:raise OllamaError(f"Ollama request failed: {e}") from e
        answer=r.json().get("response")
        if not isinstance(answer,str) or not answer.strip():raise OllamaError("Ollama returned an empty response.")
        return answer.strip()
