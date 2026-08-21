from pathlib import Path
import pytest
from typer.testing import CliRunner

from codey.ai import OllamaClient, OllamaError
from codey.cli import app
from codey.database import Database
from codey.indexer import index_repository
from codey.models import FileRecord, SymbolRecord


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def sample_repo(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    auth_py = repo / "auth.py"
    auth_py.write_text("def authenticate_user(token: str):\n    return True\n", encoding="utf-8")
    server_py = repo / "server.py"
    server_py.write_text("from auth import authenticate_user\n\nclass Server:\n    def start(self):\n        pass\n", encoding="utf-8")
    index_repository(repo)
    return repo


def test_database_find_file_and_symbols(sample_repo: Path):
    db_path = sample_repo / ".codey" / "index.db"
    with Database(db_path) as db:
        # File lookups
        assert db.find_file("auth.py") is not None
        assert db.find_file("auth.py")["path"] == "auth.py"
        assert db.find_file(r"auth.py")["path"] == "auth.py"
        assert db.find_file("nonexistent.py") is None

        # Symbol lookups
        syms = db.find_symbols("authenticate_user")
        assert len(syms) == 1
        assert syms[0]["name"] == "authenticate_user"
        assert syms[0]["symbol_type"] == "function"
        assert syms[0]["file_path"] == "auth.py"

        # Case-insensitive symbol lookup
        syms_ci = db.find_symbols("AUTHENTICATE_USER")
        assert len(syms_ci) == 1
        assert syms_ci[0]["name"] == "authenticate_user"

        # Class lookup
        server_syms = db.find_symbols("Server")
        assert len(server_syms) == 1
        assert server_syms[0]["symbol_type"] == "class"


def test_explain_file(runner: CliRunner, sample_repo: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        OllamaClient,
        "ask",
        lambda self, prompt: f"Mock explanation for prompt length {len(prompt)}",
    )
    result = runner.invoke(app, ["explain", "auth.py", "--path", str(sample_repo)])
    assert result.exit_code == 0
    assert "Explaining file: auth.py" in result.output
    assert "auth.py" in result.output
    assert "Mock explanation" in result.output


def test_explain_symbol(runner: CliRunner, sample_repo: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        OllamaClient,
        "ask",
        lambda self, prompt: "Mock symbol explanation",
    )
    result = runner.invoke(app, ["explain", "authenticate_user", "--path", str(sample_repo)])
    assert result.exit_code == 0
    assert "Explaining symbol: authenticate_user" in result.output
    assert "auth.py" in result.output
    assert "Mock symbol explanation" in result.output


def test_explain_debug_flag(runner: CliRunner, sample_repo: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        OllamaClient,
        "ask",
        lambda self, prompt: "Mock debug explanation",
    )
    result = runner.invoke(app, ["explain", "Server", "--path", str(sample_repo), "--debug"])
    assert result.exit_code == 0
    assert "Explaining symbol: Server" in result.output
    assert "AI pipeline debug" in result.output
    assert "Retrieved files:" in result.output
    assert "Approx. prompt tokens:" in result.output
    assert "Mock debug explanation" in result.output


def test_explain_not_found(runner: CliRunner, sample_repo: Path):
    result = runner.invoke(app, ["explain", "missing_symbol_or_file", "--path", str(sample_repo)])
    assert result.exit_code == 0
    assert "No indexed file or symbol matching 'missing_symbol_or_file' found." in result.output


def test_explain_no_index(runner: CliRunner, tmp_path: Path):
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    result = runner.invoke(app, ["explain", "main.py", "--path", str(empty_dir)])
    assert result.exit_code == 2
    assert "No CodeY index found" in result.output


def test_explain_empty_target(runner: CliRunner, sample_repo: Path):
    result = runner.invoke(app, ["explain", "   ", "--path", str(sample_repo)])
    assert result.exit_code == 2
    assert "Target cannot be empty" in result.output


def test_explain_ollama_error(runner: CliRunner, sample_repo: Path, monkeypatch: pytest.MonkeyPatch):
    def failing_ask(self, prompt):
        raise OllamaError("Could not connect to Ollama at http://127.0.0.1:11434.")

    monkeypatch.setattr(OllamaClient, "ask", failing_ask)
    result = runner.invoke(app, ["explain", "auth.py", "--path", str(sample_repo)])
    assert result.exit_code == 1
    assert "AI request failed: Could not connect to Ollama" in result.output
