# CodeY

CodeY is a local-first developer tool for understanding codebases with local AI. It indexes files, code structure (AST symbols), and Git history into a local SQLite database, retrieves focused context for a question, and sends only that relevant context to a locally running Ollama model.

## Installation & Setup

```powershell
# Install dependencies into virtual environment
uv sync

# Run tests
uv run pytest
```

## Running CodeY

You can run CodeY using `uv run` or directly via your virtual environment:

```powershell
# Using uv (recommended)
uv run codey <command> [options]

# Using the active virtual environment directly (Windows)
& ".\.venv\Scripts\codey.exe" <command> [options]

# Using Python module syntax
& ".\.venv\Scripts\python.exe" -m codey.cli <command> [options]
```

## Command Reference

### 1. Indexing & Inspection

#### `codey index [PATH]`
Scans and indexes the target repository into `.codey/index.db`.
```powershell
# Index current directory
uv run codey index .

# Index an external project
uv run codey index "C:\path\to\repo"
```

#### `codey status [PATH]`
Displays project stats (file count, symbol count, commit count, Git availability, last indexed timestamp, and language breakdown).
```powershell
uv run codey status
```

#### `codey files [PATH]`
Lists all indexed files with language, line count, and file size in a formatted table.
```powershell
uv run codey files
```

#### `codey symbols [PATH]`
Lists all parsed code symbols (functions, classes, methods, interfaces, structs) and their line numbers.
```powershell
uv run codey symbols
```

#### `codey commits [PATH] [--limit N]`
Shows Git commit history and author information.
```powershell
# Show latest 20 commits (default)
uv run codey commits

# Show up to 50 commits
uv run codey commits --limit 50
```

#### `codey info [PATH]`
Shows repository metadata and the SQLite index database path.
```powershell
uv run codey info
```

---

### 2. Local AI Assistant (`ask` & `explain`)

Requires [Ollama](https://ollama.com) running locally with a model installed (e.g. `qwen2.5-coder:3b`).

```powershell
# Verify Ollama is running and models are installed
ollama list
```

#### `codey ask "<PROMPT>" [--path PATH] [--debug]`
Retrieves relevant source files using keyword and symbol matching, builds a compact context window, and queries the local AI model.

```powershell
# Ask about architecture and features
uv run codey ask "Where is user authentication implemented?"

# Ask about database / storage layer
uv run codey ask "How does the database indexing and storage layer work?"

# Query a specific repository path
uv run codey ask "What endpoints and routes are defined?" --path "C:\path\to\repo"

# Query with debug details (shows retrieved files, scoring, and context token estimates)
uv run codey ask "How are git commits collected and analyzed?" --debug
```

#### `codey explain <TARGET> [--path PATH] [--debug]`
Explains a specific indexed symbol (function, class, method, struct, type) or file path using targeted codebase context and the local AI model.

```powershell
# Explain a file
uv run codey explain src/codey/ai.py

# Explain a symbol
uv run codey explain OllamaClient

# Explain with debug details
uv run codey explain parse_file --debug
```

---

## Configuration

Customize Ollama and retrieval budgets using environment variables:

| Variable | Default | Description |
| :--- | :--- | :--- |
| `CODEY_MODEL` | `qwen2.5-coder:3b` | Ollama model name used for answering questions. |
| `CODEY_OLLAMA_URL` | `http://127.0.0.1:11434` | Base URL of the local Ollama instance. |
| `CODEY_OLLAMA_TIMEOUT` | `180` | AI request timeout in seconds. |
| `CODEY_MAX_CONTEXT_CHARS` | `10000` | Character budget for retrieved context sent to the model. |
| `CODEY_MAX_FILES` | `6` | Maximum number of top-matching files retrieved per query. |

The context budget is intentionally limited so lightweight local models do not get overwhelmed with excessive prompt tokens.

---

## Supported Languages (Tree-Sitter Parsing)

CodeY has built-in Tree-sitter AST parsers for extracting functions, methods, classes, types, and structs from:
- **Python** (`.py`)
- **TypeScript / TSX** (`.ts`, `.tsx`)
- **JavaScript / JSX** (`.js`, `.jsx`)
- **Go** (`.go`)
- **Rust** (`.rs`)
- **Java** (`.java`)

*(File scanning and retrieval also supports Markdown, JSON, CSS, HTML, TOML, YAML, XML, SQL, Shell, PowerShell, etc.)*

---

## Design Boundary

CodeY understands and explains an existing codebase. It does not autonomously modify files. The system is local/offline-first and has no required cloud AI API, web UI, authentication system, or hosted database.
