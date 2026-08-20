import sys
from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from .ai import OllamaClient,OllamaError
from .config import CodeYConfig
from .context import build_context
from .database import Database
from .indexer import index_repository
from .retrieval import retrieve
app=typer.Typer(help="CodeY — local-first project understanding.");console=Console()
def db(path):return Database(CodeYConfig.for_repository(path.resolve()).database)
@app.command()
def index(path:Path=typer.Argument(Path("."),exists=True,file_okay=False,dir_okay=True)):
    try:
        console.print("[bold]CodeY[/bold]\n─────\nIndexing repository...\n");r=index_repository(path);console.print("✓ Repository detected" if r.git_available else "• Git repository not detected; file indexing only");console.print(f"✓ {r.files_discovered} files discovered\n✓ {r.files_indexed} files indexed\n✓ {r.symbols_discovered} symbols discovered\n✓ {r.commits_analyzed} commits analyzed\n\n[bold green]Index complete.[/bold green]")
    except Exception as e:console.print(f"[red]✗ Indexing failed:[/red] {e}");raise typer.Exit(1) from e
@app.command()
def status(path:Path=typer.Argument(Path("."),exists=True,file_okay=False,dir_okay=True)):
    p=CodeYConfig.for_repository(path.resolve()).database
    if not p.exists():console.print("No index found. Run `codey index .` first.");raise typer.Exit(1)
    with Database(p) as d:s=d.get_status()
    r=s["repository"];console.print(f"Repository: {r['path']}\nFiles: {s['files']}\nSymbols: {s['symbols']}\nCommits: {s['commits']}\nGit: {'available' if r['git_available'] else 'not detected'}\nLast indexed: {r['last_indexed']}\n\nLanguages");[console.print(f"  {l}: {n}") for l,n in s['languages']]
@app.command()
def files(path:Path=typer.Argument(Path("."),exists=True,file_okay=False,dir_okay=True)):
    with db(path) as d:rows=d.list_files()
    t=Table();[t.add_column(c) for c in ("Path","Language","Lines","Size")];[t.add_row(r['path'],r['language'],str(r['lines']),f"{r['size']:,} B") for r in rows];console.print(t)
@app.command()
def commits(path:Path=typer.Argument(Path("."),exists=True,file_okay=False,dir_okay=True),limit:int=typer.Option(20,min=1,max=500)):
    with db(path) as d:rows=d.list_commits(limit)
    if not rows:console.print("No Git commits indexed.");return
    t=Table();[t.add_column(c) for c in ("SHA","Author","Date","Message")];[t.add_row(r['sha'][:10],r['author'],r['timestamp'][:10],r['message']) for r in rows];console.print(t)
@app.command()
def symbols(path:Path=typer.Argument(Path("."),exists=True,file_okay=False,dir_okay=True)):
    with db(path) as d:rows=d.list_symbols()
    t=Table();[t.add_column(c) for c in ("Name","Type","File","Lines")];[t.add_row(r['name'],r['symbol_type'],r['file_path'],f"{r['start_line']}-{r['end_line']}") for r in rows];console.print(t)
@app.command()
def info(path:Path=typer.Argument(Path("."),exists=True,file_okay=False,dir_okay=True)):
    root=path.resolve();c=CodeYConfig.for_repository(root);console.print(f"Path: {root}\nGit repository: {'yes' if (root/'.git').exists() else 'no'}\nCodeY database: {c.database}")
@app.command()
def ask(prompt:str=typer.Argument(...),path:Path=typer.Option(Path("."),"--path",exists=True,file_okay=False,dir_okay=True),debug:bool=typer.Option(False,"--debug")):
    root=path.resolve();c=CodeYConfig.for_repository(root)
    if not c.database.exists():console.print("[red]✗ No CodeY index found.[/red] Run `codey index .` first.");raise typer.Exit(2)
    try:
        with Database(c.database) as d:results=retrieve(d,root,prompt,c.max_files)
        ctx=build_context(results,c.max_context_chars)
        console.print("Relevant files:");[console.print(f"  {x.path} (score={x.score:.1f}; {'+'.join(x.reasons)})") for x in results]
        if not results:console.print("[yellow]No relevant files found.[/yellow]");return
        full=f"You are CodeY, a local codebase understanding tool. Answer only from the supplied repository context. Do not invent files, APIs, architecture, or history. If context is insufficient, say so. Mention exact file paths when useful.\n\nQuestion:\n{prompt}\n\nRepository context:\n{ctx.text}"
        if debug:console.print(f"\nAI pipeline debug\n  Retrieved files: {ctx.files}\n  Context characters: {ctx.characters:,}\n  Prompt characters: {len(full):,}\n  Approx. prompt tokens: {len(full)//4:,}\n  Context budget: {c.max_context_chars:,} chars\n  Timeout: {c.timeout:g}s")
        console.print(f"\nModel: {c.model}\n");console.print(OllamaClient(c.ollama_url,c.model,c.timeout).ask(full))
    except ValueError as e:console.print(f"[red]✗ {e}[/red]");raise typer.Exit(2) from e
    except OllamaError as e:console.print(f"[red]✗ AI request failed:[/red] {e}");raise typer.Exit(1) from e
    except Exception as e:console.print(f"[red]✗ CodeY failed:[/red] {e}");raise typer.Exit(1) from e
if __name__=="__main__":app()
