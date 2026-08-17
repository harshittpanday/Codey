from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path

from gitignore_parser import parse_gitignore  # type: ignore[import-not-found]

from .models import FileRecord

# Intentionally conservative. These are directories that are almost never useful
# for project understanding and can contain enormous generated trees.
IGNORED_DIR_NAMES = {
    ".git",
    ".codey",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
    "coverage",
    ".next",
    ".turbo",
    "target",
    "out",
    "vendor",
}

LANGUAGES = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".c": "C",
    ".h": "C/C++",
    ".cpp": "C++",
    ".cc": "C++",
    ".hpp": "C++",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".md": "Markdown",
    ".mdx": "MDX",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".xml": "XML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".html": "HTML",
    ".sql": "SQL",
    ".sh": "Shell",
    ".ps1": "PowerShell",
}

MAX_FILE_SIZE = 2 * 1024 * 1024
BINARY_SAMPLE_SIZE = 8192


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_binary(path: Path) -> bool:
    try:
        sample = path.read_bytes()[:BINARY_SAMPLE_SIZE]
    except OSError:
        return True
    return b"\x00" in sample


def language_for(path: Path) -> str:
    return LANGUAGES.get(path.suffix.lower(), "Unknown")


def build_gitignore_matcher(root: Path):
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        return lambda _: False
    return parse_gitignore(str(gitignore), root_directory=str(root))


def discover_files(root: Path) -> list[Path]:
    matcher = build_gitignore_matcher(root)
    discovered: list[Path] = []

    for current, dirnames, filenames in os.walk(root, topdown=True):
        current_path = Path(current)
        dirnames[:] = [
            name
            for name in dirnames
            if name not in IGNORED_DIR_NAMES
            and not matcher(current_path / name)
        ]

        for filename in filenames:
            path = current_path / filename
            if matcher(path) or path.name == ".gitignore":
                continue
            try:
                if path.is_symlink() or not path.is_file():
                    continue
                if path.stat().st_size > MAX_FILE_SIZE or is_binary(path):
                    continue
            except OSError:
                continue
            discovered.append(path)

    return sorted(discovered)


def make_file_record(path: Path, root: Path) -> FileRecord:
    stat = path.stat()
    modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    text = path.read_text(encoding="utf-8", errors="replace")
    return FileRecord(
        path=path.relative_to(root).as_posix(),
        extension=path.suffix.lower(),
        language=language_for(path),
        size_bytes=stat.st_size,
        sha256=sha256_file(path),
        line_count=0 if not text else text.count("\n") + 1,
        modified_at=modified,
    )
