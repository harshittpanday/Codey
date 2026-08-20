from __future__ import annotations
import sqlite3
from pathlib import Path
from .models import CommitRecord,FileRecord,SymbolRecord,utc_now
class Database:
    def __init__(self,path:Path): self.path=path
    def __enter__(self):
        self.path.parent.mkdir(parents=True,exist_ok=True); self._conn=sqlite3.connect(self.path); self._conn.row_factory=sqlite3.Row; self._initialize(); return self
    def __exit__(self,exc_type,exc,tb):
        self._conn.rollback() if exc_type else self._conn.commit(); self._conn.close()
    @property
    def conn(self): return self._conn
    def _initialize(self):
        cursor=self.conn.cursor()
        repo_cols={row["name"] for row in cursor.execute("PRAGMA table_info(repository)").fetchall()}
        files_cols={row["name"] for row in cursor.execute("PRAGMA table_info(files)").fetchall()}
        if (repo_cols and "path" not in repo_cols) or (files_cols and "size" not in files_cols):
            self.conn.executescript("DROP TABLE IF EXISTS commit_files; DROP TABLE IF EXISTS commits; DROP TABLE IF EXISTS symbols; DROP TABLE IF EXISTS files; DROP TABLE IF EXISTS repository;")
        self.conn.executescript("""PRAGMA foreign_keys=ON; CREATE TABLE IF NOT EXISTS repository(id INTEGER PRIMARY KEY CHECK(id=1),path TEXT NOT NULL,git_available INTEGER NOT NULL,last_indexed TEXT NOT NULL); CREATE TABLE IF NOT EXISTS files(path TEXT PRIMARY KEY,extension TEXT NOT NULL,language TEXT NOT NULL,size INTEGER NOT NULL,sha256 TEXT NOT NULL,modified_at TEXT NOT NULL,lines INTEGER NOT NULL); CREATE TABLE IF NOT EXISTS symbols(id INTEGER PRIMARY KEY,file_path TEXT NOT NULL REFERENCES files(path) ON DELETE CASCADE,name TEXT NOT NULL,symbol_type TEXT NOT NULL,start_line INTEGER NOT NULL,end_line INTEGER NOT NULL); CREATE INDEX IF NOT EXISTS idx_symbols_file ON symbols(file_path); CREATE TABLE IF NOT EXISTS commits(sha TEXT PRIMARY KEY,author TEXT NOT NULL,timestamp TEXT NOT NULL,message TEXT NOT NULL,parents TEXT NOT NULL); CREATE TABLE IF NOT EXISTS commit_files(commit_sha TEXT NOT NULL REFERENCES commits(sha) ON DELETE CASCADE,path TEXT NOT NULL,additions INTEGER NOT NULL,deletions INTEGER NOT NULL,PRIMARY KEY(commit_sha,path));""")
    def save_repository(self,path,git_available): self.conn.execute("INSERT INTO repository VALUES(1,?,?,?) ON CONFLICT(id) DO UPDATE SET path=excluded.path,git_available=excluded.git_available,last_indexed=excluded.last_indexed",(str(path),int(git_available),utc_now()))
    def upsert_files(self,rs): self.conn.executemany("INSERT INTO files VALUES(?,?,?,?,?,?,?) ON CONFLICT(path) DO UPDATE SET extension=excluded.extension,language=excluded.language,size=excluded.size,sha256=excluded.sha256,modified_at=excluded.modified_at,lines=excluded.lines",[(r.path,r.extension,r.language,r.size,r.sha256,r.modified_at,r.lines) for r in rs])
    def remove_missing_files(self,current): self.conn.executemany("DELETE FROM files WHERE path=?",[(p,) for p in {r[0] for r in self.conn.execute("SELECT path FROM files")} - current])
    def replace_git_history(self,cs):
        self.conn.execute("DELETE FROM commit_files");self.conn.execute("DELETE FROM commits")
        self.conn.executemany("INSERT INTO commits VALUES(?,?,?,?,?)",[(c.sha,c.author,c.timestamp,c.message,"\n".join(c.parents)) for c in cs])
        rows=[(c.sha,f.path,f.additions,f.deletions) for c in cs for f in c.files];self.conn.executemany("INSERT INTO commit_files VALUES(?,?,?,?)",rows)
    def get_status(self):
        r=self.conn.execute("SELECT * FROM repository WHERE id=1").fetchone(); langs=self.conn.execute("SELECT language,COUNT(*) count FROM files GROUP BY language ORDER BY count DESC").fetchall();return {"repository":dict(r) if r else None,"files":self.conn.execute("SELECT COUNT(*) FROM files").fetchone()[0],"symbols":self.conn.execute("SELECT COUNT(*) FROM symbols").fetchone()[0],"commits":self.conn.execute("SELECT COUNT(*) FROM commits").fetchone()[0],"languages":[(x["language"],x["count"]) for x in langs]}
    def list_files(self):return self.conn.execute("SELECT * FROM files ORDER BY path").fetchall()
    def list_commits(self,limit=20):return self.conn.execute("SELECT * FROM commits ORDER BY timestamp DESC LIMIT ?",(limit,)).fetchall()
    def list_symbols(self):return self.conn.execute("SELECT * FROM symbols ORDER BY file_path,start_line,name").fetchall()
    def all_files(self):return self.conn.execute("SELECT * FROM files ORDER BY path").fetchall()
    def symbols_for_file(self,path):return self.conn.execute("SELECT * FROM symbols WHERE file_path=? ORDER BY start_line",(path,)).fetchall()
