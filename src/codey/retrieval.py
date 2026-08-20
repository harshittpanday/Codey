from __future__ import annotations
import re
from dataclasses import dataclass
from pathlib import Path
from .database import Database
@dataclass(frozen=True)
class RetrievedFile:
    path:str;score:float;reasons:tuple[str,...];content:str
STOP={"what","where","when","why","how","does","is","are","the","this","that","with","from","into","before","after","which","and","or","for","codey","file","files","code","project"}
def terms_from_query(q): return list(dict.fromkeys(w for w in re.findall(r"[A-Za-z_][A-Za-z0-9_.-]{2,}",q.lower()) if w not in STOP))
def retrieve(db:Database,root:Path,query:str,max_files=6):
    terms=terms_from_query(query); scored=[]
    for row in db.all_files():
        p=row["path"];abs=root/p
        try:text=abs.read_text(encoding="utf-8",errors="replace")
        except OSError:continue
        symbols=[x["name"] for x in db.symbols_for_file(p)];lowp=p.lower();lowc=text.lower();score=0;reasons=[]
        for t in terms:
            if t in lowp:score+=10;reasons.append("path") if "path" not in reasons else None
            if t in lowc:score+=min(lowc.count(t),8)*1.5;reasons.append("content") if "content" not in reasons else None
            if any(t in s.lower() for s in symbols):score+=5;reasons.append("symbol") if "symbol" not in reasons else None
        if score:scored.append(RetrievedFile(p,score,tuple(reasons),text))
    scored.sort(key=lambda x:(-x.score,len(x.content),x.path));return scored[:max_files]
