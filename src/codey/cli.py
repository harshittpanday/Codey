from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .ai import OllamaClient, OllamaError
from .config import CodeYConfig
from .context import build_context
from .database import Database
from .git import discover_repository
from .indexer import index_repository

app = typer.Typer(help="CodeY — local-first project understanding.", no_args_is_help=True)
console = Console()


def _root(path: Path) -> Path:
    requested = path.expanduser().resolve()
    return discover_repository(requested) or requested


def _db(path: Path) -> Database:
    return Database(CodeYConfig.for_repository(_root(path)).database_path)


@app.command()
def index(path: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True, resolve_path=True)) -> None:
    """Index a local repository or directory."""
    console.print("[bold]CodeY[/bold]")
    console.print("─" * 5)
    console.print("Indexing repository...\n")
    try:
        result = index_repository(path)
    except Exception as exc:
        console.print(f"[red]✗ Indexing failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    if result.git_available:
        console.print("[green]✓[/green] Repository detected")
    else:
        console.print("[yellow]•[/yellow] Git repository not detected; file indexing only")
    console.print(f"[green]✓[/green] {result.files_discovered} files discovered")
    console.print(f"[green]✓[/green] {result.files_indexed} files indexed")
    console.print(f"[green]✓[/green] {result.symbols} symbols discovered")
    console.print(f"[green]✓[/green] {result.commits} commits analyzed")
    console.print("\n[bold green]Index complete.[/bold green]")


@app.command()
def ask(
    prompt: str = typer.Argument(..., help="Question or instruction for the local model."),
    path: Path = typer.Option(
        Path("."), "--path", "-p", exists=True, file_okay=False, dir_okay=True,
        help="Repository to ask questions about.",
    ),
) -> None:
    """Ask the local model about an indexed repository."""
    repository_root = path.resolve()
    config = CodeYConfig.for_repository(repository_root)

    if not config.database_path.exists():
        console.print(
            "[red]✗ No CodeY index found.[/red]\n"
            f"Run: codey index {repository_root}"
        )
        raise typer.Exit(code=2)

    try:
        with Database(config.database_path) as database:
            context, results = build_context(database, repository_root, prompt)
            if not results:
                console.print("[yellow]No relevant project files found.[/yellow]")
                raise typer.Exit(code=1)

            console.print("[dim]Relevant files:[/dim]")
            for result in results:
                console.print(f"  [cyan]{result.path}[/cyan] [dim]({result.reason})[/dim]")
            console.print()

            client = OllamaClient.from_environment()
            system_prompt = (
                "You are CodeY, a local software project understanding assistant. "
                "Answer questions using the supplied project context. Do not invent "
                "files, functions, or architecture. If the context is insufficient, "
                "say so clearly."
            )
            model_prompt = (
                f"{system_prompt}\n\nPROJECT CONTEXT:\n{context}\n\n"
                f"USER QUESTION:\n{prompt}"
            )
            console.print(f"[dim]Model: {client.model}[/dim]\n")
            console.print(client.ask(model_prompt))

    except ValueError as exc:
        console.print(f"[red]✗ {exc}[/red]")
        raise typer.Exit(code=2) from exc
    except OllamaError as exc:
        console.print(f"[red]✗ AI request failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc


@app.command()
def status(path: Path = typer.Argument(Path("."), exists=True, file_okay=False, dir_okay=True)) -> None:
    """Show the current local index status."""
    try:
        with _db(path) as db:
            status_data = db.get_status()
    except Exception as exc:
        console.print(f"[red]No usable CodeY index:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    repo = status_data["repository"]
    if repo is None:
        console.print("[yellow]No index found. Run `codey index .` first.[/yellow]")
        raise typer.Exit(code=1)

    console.print(f"[bold]Repository:[/bold] {repo['root_path']}")
    console.print(f"[bold]Files:[/bold] {status_data['files']}")
    console.print(f"[bold]Symbols:[/bold] {status_data['symbols']}")
    console.print(f"[bold]Commits:[/bold] {status_data['commits']}")
    console.print(f"[bold]Git:[/bold] {'available' if repo['git_available'] else 'not detected'}")
    console.print(f"[bold]Last indexed:[/bold] {repo['indexed_at']}")
    console.print("\n[bold]Languages[/bold]")
    for language, count in status_data["languages"]:
        console.print(f"  {language}: {count}")


@app.command(name="files")
def files(path: Path = typer.Argument(Path("."), exists=True, file_okay=False, dir_okay=True)) -> None:
    """List indexed files."""
    with _db(path) as db:
        rows = db.list_files()
    if not rows:
        console.print("[yellow]No indexed files. Run `codey index .` first.[/yellow]")
        return
    table = Table("Path", "Language", "Lines", "Size")
    for row in rows:
        table.add_row(row["path"], row["language"], str(row["line_count"]), f"{row['size_bytes']:,} B")
    console.print(table)


@app.command()
def commits(
    path: Path = typer.Argument(Path("."), exists=True, file_okay=False, dir_okay=True),
    limit: int = typer.Option(20, min=1, max=500, help="Number of commits to show."),
) -> None:
    """Show indexed Git commits."""
    with _db(path) as db:
        rows = db.list_commits(limit)
    if not rows:
        console.print("[yellow]No Git commits indexed.[/yellow]")
        return
    table = Table("SHA", "Author", "Date", "Message")
    for row in rows:
        table.add_row(row["sha"][:10], row["author_name"], row["timestamp"][:10], row["message"].splitlines()[0][:100])
    console.print(table)


@app.command()
def symbols(path: Path = typer.Argument(Path("."), exists=True, file_okay=False, dir_okay=True)) -> None:
    """Show discovered code symbols."""
    with _db(path) as db:
        rows = db.list_symbols()
    if not rows:
        console.print("[yellow]No symbols indexed or no supported source files found.[/yellow]")
        return
    table = Table("Name", "Type", "File", "Lines")
    for row in rows:
        table.add_row(row["name"], row["symbol_type"], row["file_path"], f"{row['start_line']}-{row['end_line']}")
    console.print(table)


@app.command()
def info(path: Path = typer.Argument(Path("."), exists=True, file_okay=False, dir_okay=True)) -> None:
    """Show repository and CodeY index information."""
    root = _root(path)
    console.print(f"[bold]Path:[/bold] {root}")
    console.print(f"[bold]Git repository:[/bold] {'yes' if discover_repository(root) else 'no'}")
    console.print(f"[bold]CodeY database:[/bold] {CodeYConfig.for_repository(root).database_path}")


if __name__ == "__main__":
    app()
