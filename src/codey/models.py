from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def relative_path(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()

@dataclass(frozen=True)
class FileRecord:
    path: str; extension: str; language: str; size: int; sha256: str; modified_at: str; lines: int

@dataclass(frozen=True)
class SymbolRecord:
    file_path: str; name: str; symbol_type: str; start_line: int; end_line: int

@dataclass(frozen=True)
class CommitFileRecord:
    path: str; additions: int; deletions: int

@dataclass(frozen=True)
class CommitRecord:
    sha: str; author: str; timestamp: str; message: str; parents: tuple[str, ...]; files: tuple[CommitFileRecord, ...]
