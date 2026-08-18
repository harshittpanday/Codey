# CodeY

CodeY is a local-first developer project memory and understanding tool. MVP 1 builds the foundation: repository files, Git history, and code structure are indexed into a local SQLite database.

**MVP 1 intentionally has no AI, embeddings, RAG, web UI, cloud services, or autonomous coding features.**

## Requirements

- Python 3.13+
- Git
- [uv](https://docs.astral.sh/uv/)

## Install

```bash
uv sync
```

For development:

```bash
uv sync --dev
```

## Run

From a Git repository:

```bash
uv run codey index .
uv run codey status
uv run codey files
uv run codey commits --limit 20
uv run codey symbols
uv run codey info
```

The local index is stored in `.codey/index.db`. `.codey` is ignored by CodeY itself so it does not index its own database.

## Test

```bash
uv run pytest
```

## MVP 1 architecture

```text
CLI
 │
 ▼
Indexer ──► Scanner ──► File metadata
 │
 ├───────► GitPython ──► Commit history
 │
 └───────► Tree-sitter ──► Symbols
 │
 ▼
SQLite
```

The schema keeps repositories, files, symbols, commits, and changed files separate so later versions can add documentation, decisions, embeddings, and memory without rewriting the core index.

## Supported structural parsing

The first parser adapters cover Python, JavaScript, TypeScript/TSX, Java, Go, and Rust when their grammar packages are available. Other files are still indexed as files, but their code structure is not parsed.

## Re-indexing

Running `codey index .` again upserts current file metadata, removes deleted files, replaces their symbol records, and refreshes the Git history. This is intentionally simple and reliable for MVP 1; more granular incremental indexing can come later.


## Local AI

CodeY can now send a prompt to a locally running Ollama model. The default model is `qwen2.5-coder:3b`.

```text
codey ask "What is a Python function?"
```

Configure the local endpoint or model with `CODEY_OLLAMA_URL` and `CODEY_MODEL`. No API key or cloud service is required.
