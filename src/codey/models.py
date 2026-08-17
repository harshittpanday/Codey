from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class FileRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    extension: str = ""
    language: str = "Unknown"
    size_bytes: int = Field(ge=0)
    sha256: str
    line_count: int = Field(ge=0)
    modified_at: datetime | None = None


class SymbolRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    file_path: str
    name: str
    symbol_type: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)


class CommitRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    sha: str
    author_name: str
    author_email: str
    timestamp: datetime
    message: str
    parents: tuple[str, ...] = ()


class CommitFileRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    commit_sha: str
    path: str
    change_type: str
    additions: int = Field(ge=0)
    deletions: int = Field(ge=0)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def relative_path(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()
