from pathlib import Path

from codey.context import build_context
from codey.database import Database
from codey.models import utc_now
from codey.retrieval import search_files
from codey.scanner import make_file_record


def test_search_files_prefers_matching_path(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    auth = repo / "auth.py"
    other = repo / "other.py"
    auth.write_text("def login():\n    pass\n", encoding="utf-8")
    other.write_text("def unrelated():\n    pass\n", encoding="utf-8")

    db_path = repo / ".codey" / "index.db"
    with Database(db_path) as db:
        db.save_repository(repo, utc_now(), False)
        db.upsert_files([make_file_record(auth, repo), make_file_record(other, repo)])
        results = search_files(db, repo, "auth login")

    assert results
    assert results[0].path == "auth.py"


def test_build_context_includes_relevant_source(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    auth = repo / "auth.py"
    auth.write_text("def authenticate(user):\n    return user.is_valid\n", encoding="utf-8")

    db_path = repo / ".codey" / "index.db"
    with Database(db_path) as db:
        db.save_repository(repo, utc_now(), False)
        db.upsert_files([make_file_record(auth, repo)])
        context, results = build_context(db, repo, "authenticate")

    assert results
    assert "def authenticate" in context


def test_search_files_uses_symbols_and_ignores_lockfiles(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    component = repo / "project-timeline.tsx"
    lockfile = repo / "package-lock.json"
    component.write_text("export function ProjectTimeline() { return null }\n", encoding="utf-8")
    lockfile.write_text('{"timeline": "dependency"}\n', encoding="utf-8")

    db_path = repo / ".codey" / "index.db"
    with Database(db_path) as db:
        db.save_repository(repo, utc_now(), False)
        db.upsert_files([make_file_record(component, repo), make_file_record(lockfile, repo)])
        from codey.models import SymbolRecord
        db.replace_symbols_for_files(
            ["project-timeline.tsx"],
            [SymbolRecord(file_path="project-timeline.tsx", name="ProjectTimeline", symbol_type="function", start_line=1, end_line=1)],
        )
        results = search_files(db, repo, "Where is the portfolio timeline implemented?")

    assert results
    assert results[0].path == "project-timeline.tsx"
    assert all(result.path != "package-lock.json" for result in results)


def test_build_context_is_bounded(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    source = repo / "timeline.py"
    source.write_text("timeline\n" * 20_000, encoding="utf-8")

    db_path = repo / ".codey" / "index.db"
    with Database(db_path) as db:
        db.save_repository(repo, utc_now(), False)
        db.upsert_files([make_file_record(source, repo)])
        context, results = build_context(db, repo, "timeline", max_context_chars=2_000, max_file_chars=1_500)

    assert results
    assert len(context) <= 2_000
    assert "[Context truncated by CodeY]" in context or "[File truncated by CodeY]" in context
