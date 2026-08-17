from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CodeYConfig:
    repository_root: Path
    data_dir: Path

    @property
    def database_path(self) -> Path:
        return self.data_dir / "index.db"

    @classmethod
    def for_repository(cls, root: Path) -> "CodeYConfig":
        return cls(repository_root=root, data_dir=root / ".codey")
