from __future__ import annotations

from pathlib import Path

from .database import Database
from .retrieval import SearchResult, search_files


DEFAULT_MAX_FILES = 4
DEFAULT_MAX_FILE_CHARS = 7_000
DEFAULT_MAX_CONTEXT_CHARS = 18_000


def build_context(
    database: Database,
    repository_root: Path,
    query: str,
    *,
    max_files: int = DEFAULT_MAX_FILES,
    max_file_chars: int = DEFAULT_MAX_FILE_CHARS,
    max_context_chars: int = DEFAULT_MAX_CONTEXT_CHARS,
) -> tuple[str, list[SearchResult]]:
    """Build a bounded, high-signal source context for the local model."""
    results = search_files(database, repository_root, query, limit=max_files)
    if not results:
        return "", []

    sections: list[str] = []
    used_chars = 0
    included_results: list[SearchResult] = []

    for result in results:
        file_path = repository_root / result.path
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        content = content[:max_file_chars]
        if len(content) == max_file_chars:
            content += "\n\n[File truncated by CodeY]"

        section = f"===== {result.path} =====\n{content}"
        remaining = max_context_chars - used_chars
        if remaining <= 0:
            break

        if len(section) > remaining:
            if remaining < 300:
                break
            section = section[:remaining] + "\n[Context truncated by CodeY]"

        sections.append(section)
        included_results.append(result)
        used_chars += len(section) + 2

    return "\n\n".join(sections), included_results
