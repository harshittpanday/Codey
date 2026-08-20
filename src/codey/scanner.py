from __future__ import annotations
import hashlib, os
from pathlib import Path
from gitignore_parser import parse_gitignore
from .models import FileRecord, relative_path
MAX_FILE_SIZE=2*1024*1024
COMMON_IGNORED_DIRS={".git",".codey",".venv","venv","node_modules","__pycache__",".pytest_cache",".mypy_cache",".ruff_cache","dist","build",".next",".nuxt",".turbo","coverage","target",".idea",".vscode"}
LANGUAGES={".py":"Python",".js":"JavaScript",".jsx":"JavaScript",".ts":"TypeScript",".tsx":"TypeScript",".java":"Java",".go":"Go",".rs":"Rust",".md":"Markdown",".json":"JSON",".css":"CSS",".html":"HTML",".htm":"HTML",".toml":"TOML",".yaml":"YAML",".yml":"YAML",".xml":"XML",".sql":"SQL",".sh":"Shell",".ps1":"PowerShell"}

def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def is_binary(path:Path)->bool:
    try:
        with path.open("rb") as f: sample=f.read(8192)
    except OSError: return True
    return b"\0" in sample

def language_for(path:Path)->str: return LANGUAGES.get(path.suffix.lower(),"Unknown")

def build_gitignore(root:Path):
    p=root/".gitignore"
    return parse_gitignore(str(p),root) if p.is_file() else (lambda _:False)

def discover_files(root:Path)->list[Path]:
    root=root.resolve(); ignored=build_gitignore(root); out=[]
    for current,dirs,names in os.walk(root):
        cp=Path(current); dirs[:]=[d for d in dirs if d not in COMMON_IGNORED_DIRS and not ignored(cp/d)]
        for name in names:
            p=cp/name
            try:
                rel=relative_path(root,p)
                if ignored(p) or rel.startswith(".git/") or rel.startswith(".codey/") or p.stat().st_size>MAX_FILE_SIZE or is_binary(p): continue
                out.append(p)
            except OSError: continue
    return sorted(out)

def make_file_record(root:Path,path:Path)->FileRecord:
    st=path.stat(); text=path.read_text(encoding="utf-8",errors="replace")
    return FileRecord(relative_path(root,path),path.suffix.lower(),language_for(path),st.st_size,sha256_file(path),str(st.st_mtime_ns),text.count("\n")+(1 if text else 0))
