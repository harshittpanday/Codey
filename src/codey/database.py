from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from .models import CommitFileRecord, CommitRecord, FileRecord, SymbolRecord

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS repository (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    root_path TEXT NOT NULL,
    indexed_at TEXT NOT NULL,
    git_available INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY,
    path TEXT NOT NULL UNIQUE,
    extension TEXT NOT NULL,
    language TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    line_count INTEGER NOT NULL,
    modified_at TEXT
);

CREATE TABLE IF NOT EXISTS symbols (
    id INTEGER PRIMARY KEY,
    file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    symbol_type TEXT NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS commits (
    sha TEXT PRIMARY KEY,
    author_name TEXT NOT NULL,
    author_email TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    message TEXT NOT NULL,
    parents TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS commit_files (
    id INTEGER PRIMARY KEY,
    commit_sha TEXT NOT NULL REFERENCES commits(sha) ON DELETE CASCADE,
    path TEXT NOT NULL,
    change_type TEXT NOT NULL,
    additions INTEGER NOT NULL,
    deletions INTEGER NOT NULL,
    UNIQUE(commit_sha, path)
);

CREATE INDEX IF NOT EXISTS idx_files_language ON files(language);
CREATE INDEX IF NOT EXISTS idx_symbols_file ON symbols(file_id);
CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name);
CREATE INDEX IF NOT EXISTS idx_commits_timestamp ON commits(timestamp);
CREATE INDEX IF NOT EXISTS idx_commit_files_path ON commit_files(path);
"""


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.connection: sqlite3.Connection | None = None

    def __enter__(self) -> "Database":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript(SCHEMA)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.connection is not None:
            if exc is None:
                self.connection.commit()
            else:
                self.connection.rollback()
            self.connection.close()
            self.connection = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self.connection is None:
            raise RuntimeError("Database is not open")
        return self.connection

    def save_repository(self, root: Path, indexed_at: datetime, git_available: bool) -> None:
        self.conn.execute(
            """INSERT INTO repository(id, root_path, indexed_at, git_available)
               VALUES(1, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET root_path=excluded.root_path,
                 indexed_at=excluded.indexed_at, git_available=excluded.git_available""",
            (str(root), indexed_at.isoformat(), int(git_available)),
        )

    def upsert_files(self, records: Iterable[FileRecord]) -> None:
        self.conn.executemany(
            """INSERT INTO files(path, extension, language, size_bytes, sha256, line_count, modified_at)
               VALUES(?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(path) DO UPDATE SET extension=excluded.extension,
                 language=excluded.language, size_bytes=excluded.size_bytes,
                 sha256=excluded.sha256, line_count=excluded.line_count,
                 modified_at=excluded.modified_at""",
            [
                (r.path, r.extension, r.language, r.size_bytes, r.sha256, r.line_count,
                 r.modified_at.isoformat() if r.modified_at else None)
                for r in records
            ],
        )

    def remove_missing_files(self, current_paths: set[str]) -> None:
        existing = {row[0] for row in self.conn.execute("SELECT path FROM files")}
        missing = existing - current_paths
        if missing:
            self.conn.executemany("DELETE FROM files WHERE path = ?", [(path,) for path in missing])

    def replace_symbols_for_files(self, file_paths: Iterable[str], symbols: Iterable[SymbolRecord]) -> None:
        paths = list(file_paths)
        if paths:
            self.conn.executemany(
                "DELETE FROM symbols WHERE file_id = (SELECT id FROM files WHERE path = ?)",
                [(path,) for path in paths],
            )
        rows = []
        for symbol in symbols:
            rows.append((symbol.file_path, symbol.name, symbol.symbol_type, symbol.start_line, symbol.end_line))
        self.conn.executemany(
            """INSERT INTO symbols(file_id, name, symbol_type, start_line, end_line)
               SELECT id, ?, ?, ?, ? FROM files WHERE path = ?""",
            [(name, typ, start, end, path) for path, name, typ, start, end in rows],
        )

    def replace_git_history(self, commits: Iterable[CommitRecord], files: Iterable[CommitFileRecord]) -> None:
        self.conn.execute("DELETE FROM commit_files")
        self.conn.execute("DELETE FROM commits")
        self.conn.executemany(
            "INSERT INTO commits(sha, author_name, author_email, timestamp, message, parents) VALUES(?, ?, ?, ?, ?, ?)",
            [(c.sha, c.author_name, c.author_email, c.timestamp.isoformat(), c.message, " ".join(c.parents)) for c in commits],
        )
        self.conn.executemany(
            "INSERT OR IGNORE INTO commit_files(commit_sha, path, change_type, additions, deletions) VALUES(?, ?, ?, ?, ?)",
            [(f.commit_sha, f.path, f.change_type, f.additions, f.deletions) for f in files],
        )

    def get_status(self) -> dict[str, object]:
        repo = self.conn.execute("SELECT * FROM repository WHERE id = 1").fetchone()
        languages = self.conn.execute("SELECT language, COUNT(*) AS count FROM files GROUP BY language ORDER BY count DESC").fetchall()
        return {
            "repository": repo,
            "files": self.conn.execute("SELECT COUNT(*) FROM files").fetchone()[0],
            "symbols": self.conn.execute("SELECT COUNT(*) FROM symbols").fetchone()[0],
            "commits": self.conn.execute("SELECT COUNT(*) FROM commits").fetchone()[0],
            "languages": [(row[0], row[1]) for row in languages],
        }

    def list_files(self) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM files ORDER BY path").fetchall()

    def list_commits(self, limit: int = 20) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM commits ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()

    def list_symbols(self) -> list[sqlite3.Row]:
        return self.conn.execute(
            """SELECT symbols.*, files.path AS file_path FROM symbols
               JOIN files ON files.id = symbols.file_id
               ORDER BY files.path, symbols.start_line, symbols.name"""
        ).fetchall()
