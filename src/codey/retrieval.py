from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .database import Database


@dataclass(frozen=True)
class SearchResult:
    path: str
    score: float
    reason: str


# Dependency/build artifacts are rarely useful when answering questions about
# an application's implementation and can produce a lot of noisy context.
_IGNORED_NAME_PATTERNS = (
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "bun.lock",
    "uv.lock",
    "poetry.lock",
    "cargo.lock",
)
_IGNORED_DIRS = {"node_modules", ".next", "dist", "build", "coverage", ".git", ".venv"}


def _tokens(text: str) -> set[str]:
    return {
        token.lower()
        for token in re.findall(r"[A-Za-z0-9_]+", text)
        if len(token) >= 2
    }


def _is_noise_path(path: str) -> bool:
    parts = {part.lower() for part in Path(path).parts}
    name = Path(path).name.lower()
    return bool(parts & _IGNORED_DIRS) or name in _IGNORED_NAME_PATTERNS


def _stem_tokens(path: str) -> set[str]:
    name = Path(path).stem.replace("-", "_").replace(".", "_")
    return _tokens(name)


def search_files(
    database: Database,
    repository_root: Path,
    query: str,
    *,
    limit: int = 6,
) -> list[SearchResult]:
    """Find the most relevant source files using deterministic local ranking.

    Ranking intentionally favors file names, paths, and indexed symbols over
    broad content matches. This keeps local LLM prompts small and useful.
    """
    query_tokens = _tokens(query)
    if not query_tokens:
        return []

    symbol_by_file: dict[str, list[str]] = {}
    for symbol in database.list_symbols():
        symbol_by_file.setdefault(symbol["file_path"], []).append(symbol["name"])

    results: list[SearchResult] = []

    for record in database.list_files():
        path = record["path"]
        if _is_noise_path(path):
            continue

        path_tokens = _tokens(path)
        stem_tokens = _stem_tokens(path)
        score = 0.0
        reasons: list[str] = []

        # Filename/path matches are the strongest signal. A question about
        # "timeline" should strongly prefer project-timeline.tsx.
        stem_matches = query_tokens & stem_tokens
        if stem_matches:
            score += len(stem_matches) * 14
            reasons.append("filename")

        path_matches = query_tokens & path_tokens
        if path_matches:
            score += len(path_matches) * 5
            if "filename" not in reasons:
                reasons.append("path")

        # The symbol index is already available, so use it before opening all
        # source files. This is especially useful for questions about classes,
        # components, functions, interfaces, and types.
        symbol_names = symbol_by_file.get(path, [])
        symbol_matches = sum(
            1
            for name in symbol_names
            if query_tokens & _tokens(name)
        )
        if symbol_matches:
            score += symbol_matches * 10
            reasons.append("symbol")

        file_path = repository_root / path
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        content_tokens = _tokens(content)
        content_matches = len(query_tokens & content_tokens)
        if content_matches:
            score += min(content_matches, 4) * 1.5
            reasons.append("content")

        if score > 0:
            results.append(SearchResult(path=path, score=score, reason="+".join(reasons)))

    results.sort(key=lambda result: (-result.score, result.path.lower()))
    return results[:limit]
