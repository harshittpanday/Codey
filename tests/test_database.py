from datetime import datetime, timezone
from pathlib import Path

from codey.database import Database
from codey.models import FileRecord, SymbolRecord


def test_database_upsert_and_symbol_relationship(tmp_path: Path) -> None:
    db_path = tmp_path / ".codey" / "index.db"
    record = FileRecord(
        path="src/main.py",
        extension=".py",
        language="Python",
        size_bytes=20,
        sha256="abc",
        line_count=2,
        modified_at=datetime.now(timezone.utc),
    )
    symbol = SymbolRecord(file_path="src/main.py", name="hello", symbol_type="function_definition", start_line=1, end_line=2)

    with Database(db_path) as db:
        db.upsert_files([record])
        db.replace_symbols_for_files([record.path], [symbol])
        assert len(db.list_files()) == 1
        assert len(db.list_symbols()) == 1
        db.upsert_files([record])
        assert len(db.list_files()) == 1
