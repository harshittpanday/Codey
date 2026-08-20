from dataclasses import dataclass
from .retrieval import RetrievedFile
@dataclass(frozen=True)
class ContextResult:text:str;characters:int;files:int
def build_context(files,max_chars):
    parts=[];used=0
    for f in files:
        header=f"\n===== {f.path} =====\n";avail=max_chars-used-len(header)
        if avail<=0:break
        content=f.content if len(f.content)<=avail else f.content[:avail]+"\n...[truncated by CodeY]..."
        block=header+content;parts.append(block);used+=len(block)
    text="".join(parts).strip();return ContextResult(text,len(text),len(parts))
