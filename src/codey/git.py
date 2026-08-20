from __future__ import annotations
from pathlib import Path
from git import InvalidGitRepositoryError, NoSuchPathError, Repo
from .models import CommitFileRecord, CommitRecord
class GitRepositoryError(RuntimeError): pass

def discover_repository(path:Path)->Path|None:
    try: repo=Repo(path,search_parent_directories=True)
    except (InvalidGitRepositoryError,NoSuchPathError,OSError): return None
    return Path(repo.working_tree_dir).resolve() if not repo.bare and repo.working_tree_dir else None

def open_repository(path:Path)->Repo:
    try:return Repo(path)
    except (InvalidGitRepositoryError,NoSuchPathError) as e:raise GitRepositoryError(f"Not a Git repository: {path}") from e

def collect_commits(repo:Repo,limit:int|None=None)->list[CommitRecord]:
    out=[]
    for c in repo.iter_commits(max_count=limit) if limit is not None else repo.iter_commits():
        changed=[]
        if c.parents:
            for d in c.diff(c.parents[0],create_patch=False):
                if d.b_path or d.a_path:
                    changed.append(CommitFileRecord(d.b_path or d.a_path,d.diff.count(b"\n+"),d.diff.count(b"\n-")))
        else:
            for p,s in c.stats.files.items(): changed.append(CommitFileRecord(p,int(s.get("insertions",0)),int(s.get("deletions",0))))
        out.append(CommitRecord(c.hexsha,str(c.author),c.committed_datetime.isoformat(),c.message.strip(),tuple(p.hexsha for p in c.parents),tuple(changed)))
    return out
