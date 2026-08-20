# CodeY

CodeY is a local-first developer tool for understanding codebases with local AI. It indexes files, code structure, and Git history into SQLite, retrieves focused context for a question, and sends only that context to a locally running Ollama model.

## Install

```powershell
uv sync
uv run pytest
```

## Index

```powershell
uv run codey index "C:\path\to\repo"
uv run codey status
uv run codey files
uv run codey symbols
uv run codey commits --limit 20
uv run codey info
```

## Local AI

Install/run Ollama and have a model available, for example `qwen2.5-coder:3b`.

```powershell
ollama list
uv run codey ask "Where is authentication implemented?" --path "C:\path\to\repo"
uv run codey ask "How does the database layer work?" --path "C:\path\to\repo" --debug
```

Environment variables:

- `CODEY_MODEL` — default `qwen2.5-coder:3b`
- `CODEY_OLLAMA_URL` — default `http://127.0.0.1:11434`
- `CODEY_OLLAMA_TIMEOUT` — default `180` seconds
- `CODEY_MAX_CONTEXT_CHARS` — default `10000`
- `CODEY_MAX_FILES` — default `6`

The context budget is intentionally limited so a small local model does not receive an unnecessarily huge prompt.

## Design boundary

CodeY understands and explains an existing codebase. It does not autonomously modify files. The system is local/offline-first and has no required cloud AI API, web UI, authentication system, or hosted database.
