from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from .database import Database
from .git import collect_commits,discover_repository,open_repository
from .parser import parse_file
from .scanner import discover_files,make_file_record
@dataclass(frozen=True)
class IndexResult:
    repository:Path;files_discovered:int;files_indexed:int;symbols_discovered:int;commits_analyzed:int;git_available:bool

def index_repository(path:Path)->IndexResult:
    requested=path.resolve();root=discover_repository(requested) or requested;paths=discover_files(root);records=[make_file_record(root,p) for p in paths];symbols=[]
    for r,p in zip(records,paths): symbols.extend(parse_file(r.path,r.language,p.read_text(encoding="utf-8",errors="replace")))
    git=discover_repository(root) is not None; commits=collect_commits(open_repository(root)) if git else []
    with Database(root/".codey"/"index.db") as db:
        db.save_repository(root,git);db.upsert_files(records);db.remove_missing_files({r.path for r in records});db.conn.execute("DELETE FROM symbols");db.conn.executemany("INSERT INTO symbols(file_path,name,symbol_type,start_line,end_line) VALUES(?,?,?,?,?)",[(s.file_path,s.name,s.symbol_type,s.start_line,s.end_line) for s in symbols]);db.replace_git_history(commits)
    return IndexResult(root,len(paths),len(records),len(symbols),len(commits),git)
