from __future__ import annotations

from pathlib import Path

from .database import Database
from .git import collect_commits, discover_repository, open_repository
from .models import utc_now
from .parser import parse_file
from .scanner import discover_files, make_file_record


class IndexResult:
    def __init__(self) -> None:
        self.repository_root: Path | None = None
        self.files_discovered = 0
        self.files_indexed = 0
        self.symbols = 0
        self.commits = 0
        self.git_available = False


def index_repository(path: Path) -> IndexResult:
    requested = path.expanduser().resolve()
    root = discover_repository(requested)
    git_available = root is not None
    if root is None:
        root = requested

    if not root.exists() or not root.is_dir():
        raise ValueError(f"Path is not a directory: {root}")

    config_dir = root / ".codey"
    result = IndexResult()
    result.repository_root = root
    result.git_available = git_available

    paths = discover_files(root)
    result.files_discovered = len(paths)
    records = [make_file_record(p, root) for p in paths]

    with Database(config_dir / "index.db") as db:
        db.upsert_files(records)
        db.remove_missing_files({record.path for record in records})
        all_symbols = []
        for record, path in zip(records, paths):
            for symbol in parse_file(path, record.language):
                all_symbols.append(symbol.model_copy(update={"file_path": record.path}))
        db.replace_symbols_for_files([record.path for record in records], all_symbols)
        if git_available:
            repo = open_repository(root)
            commits, commit_files = collect_commits(repo)
            db.replace_git_history(commits, commit_files)
            result.commits = len(commits)
        db.save_repository(root, utc_now(), git_available)
        result.files_indexed = len(records)
        result.symbols = db.conn.execute("SELECT COUNT(*) FROM symbols").fetchone()[0]

    return result
