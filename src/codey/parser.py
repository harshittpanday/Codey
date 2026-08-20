from __future__ import annotations
from dataclasses import dataclass
from tree_sitter import Language, Parser
import tree_sitter_go as ts_go, tree_sitter_java as ts_java, tree_sitter_javascript as ts_js, tree_sitter_python as ts_python, tree_sitter_rust as ts_rust, tree_sitter_typescript as ts_ts
from .models import SymbolRecord
@dataclass(frozen=True)
class Grammar: language:str; language_obj:Language
GRAMMARS={"Python":Grammar("Python",Language(ts_python.language())),"JavaScript":Grammar("JavaScript",Language(ts_js.language())),"TypeScript":Grammar("TypeScript",Language(ts_ts.language_typescript())),"Java":Grammar("Java",Language(ts_java.language())),"Go":Grammar("Go",Language(ts_go.language())),"Rust":Grammar("Rust",Language(ts_rust.language()))}
KIND={"function_definition":"function","function_declaration":"function","method_definition":"method","method_declaration":"method","class_definition":"class","class_declaration":"class","interface_declaration":"interface","type_alias_declaration":"type_alias","type_declaration":"type","struct_item":"struct","enum_item":"enum","function_item":"function","impl_item":"impl"}

def _name(n):
    for f in ("name","field_identifier","property_identifier","type_identifier"):
        c=n.child_by_field_name(f)
        if c is not None:return c.text.decode("utf-8",errors="replace")

def parse_file(path:str,language:str,text:str)->list[SymbolRecord]:
    g=GRAMMARS.get(language)
    if not g:return []
    parser=Parser(g.language_obj); tree=parser.parse(text.encode("utf-8",errors="replace")); out=[]
    def visit(n):
        kind=KIND.get(n.type); name=_name(n) if kind else None
        if kind and name: out.append(SymbolRecord(path,name,kind,n.start_point.row+1,n.end_point.row+1))
        for child in n.children: visit(child)
    visit(tree.root_node); return out
