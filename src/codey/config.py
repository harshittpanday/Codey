from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class CodeYConfig:
    repository: Path
    database: Path
    ollama_url: str = "http://127.0.0.1:11434"
    model: str = "qwen2.5-coder:3b"
    timeout: float = 180.0
    max_context_chars: int = 10000
    max_files: int = 6

    @classmethod
    def for_repository(cls, repository: Path) -> "CodeYConfig":
        root = repository.resolve()
        timeout=float(os.getenv("CODEY_OLLAMA_TIMEOUT","180")); budget=int(os.getenv("CODEY_MAX_CONTEXT_CHARS","10000")); files=int(os.getenv("CODEY_MAX_FILES","6"))
        if timeout <= 0 or budget <= 0 or files <= 0: raise ValueError("CODEY_OLLAMA_TIMEOUT, CODEY_MAX_CONTEXT_CHARS and CODEY_MAX_FILES must be positive.")
        return cls(root, root/".codey"/"index.db", os.getenv("CODEY_OLLAMA_URL","http://127.0.0.1:11434").rstrip("/"), os.getenv("CODEY_MODEL","qwen2.5-coder:3b"), timeout, budget, files)
