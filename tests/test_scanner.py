from pathlib import Path

from codey.scanner import discover_files, language_for


def test_language_detection() -> None:
    assert language_for(Path("main.py")) == "Python"
    assert language_for(Path("app.tsx")) == "TypeScript"
    assert language_for(Path("README.md")) == "Markdown"
    assert language_for(Path("unknown.weird")) == "Unknown"


def test_scanner_ignores_generated_directories(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "node_modules").mkdir()
    (tmp_path / ".codey").mkdir()
    (tmp_path / "src" / "main.py").write_text("def hello():\n    return 1\n", encoding="utf-8")
    (tmp_path / "node_modules" / "x.js").write_text("x", encoding="utf-8")
    (tmp_path / ".codey" / "index.db").write_bytes(b"\x00")

    paths = discover_files(tmp_path)
    relative = {p.relative_to(tmp_path).as_posix() for p in paths}
    assert relative == {"src/main.py"}
