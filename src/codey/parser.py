from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tree_sitter import Language, Parser

from .models import SymbolRecord


@dataclass(frozen=True)
class Grammar:
    language: str
    grammar: Language


def _load_grammars() -> dict[str, Grammar]:
    grammars: dict[str, Grammar] = {}
    try:
        import tree_sitter_python as tspython
        grammars["Python"] = Grammar("Python", Language(tspython.language()))
    except ImportError:
        pass
    try:
        import tree_sitter_javascript as tsjavascript
        grammars["JavaScript"] = Grammar("JavaScript", Language(tsjavascript.language()))
    except ImportError:
        pass
    try:
        import tree_sitter_typescript as tstypescript
        grammars["TypeScript"] = Grammar("TypeScript", Language(tstypescript.language_typescript()))
        grammars["TSX"] = Grammar("TypeScript", Language(tstypescript.language_tsx()))
    except ImportError:
        pass
    try:
        import tree_sitter_java as tsjava
        grammars["Java"] = Grammar("Java", Language(tsjava.language()))
    except ImportError:
        pass
    try:
        import tree_sitter_go as tsgo
        grammars["Go"] = Grammar("Go", Language(tsgo.language()))
    except ImportError:
        pass
    try:
        import tree_sitter_rust as tsrust
        grammars["Rust"] = Grammar("Rust", Language(tsrust.language()))
    except ImportError:
        pass
    return grammars


GRAMMARS = _load_grammars()

NODE_TYPES: dict[str, tuple[str, ...]] = {
    "Python": (
        "function_definition",
        "class_definition",
    ),
    "JavaScript": (
        "function_declaration",
        "generator_function_declaration",
        "class_declaration",
        "method_definition",
        "lexical_declaration",
        "variable_declaration",
    ),
    "TypeScript": (
        "function_declaration",
        "generator_function_declaration",
        "class_declaration",
        "method_definition",
        "interface_declaration",
        "type_alias_declaration",
        "enum_declaration",
    ),
    "Java": (
        "class_declaration",
        "interface_declaration",
        "method_declaration",
        "constructor_declaration",
        "enum_declaration",
    ),
    "Go": (
        "function_declaration",
        "method_declaration",
        "type_declaration",
    ),
    "Rust": (
        "function_item",
        "struct_item",
        "enum_item",
        "trait_item",
        "impl_item",
        "type_item",
    ),
}

IMPORT_TYPES = {
    "import_statement",
    "import_declaration",
    "import_spec",
    "import_clause",
    "use_declaration",
}
EXPORT_TYPES = {
    "export_statement",
    "export_declaration",
}


def _node_name(node, source: bytes) -> str:
    for field_name in ("name", "declarator"):
        child = node.child_by_field_name(field_name)
        if child is not None:
            value = source[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
            if value:
                return value.split("(", 1)[0].strip()
    for child in node.children:
        if child.type in {"identifier", "type_identifier", "property_identifier", "field_identifier"}:
            return source[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
    return node.type


def parse_file(path: Path, language: str) -> list[SymbolRecord]:
    grammar = GRAMMARS.get(language)
    if grammar is None:
        return []
    source = path.read_bytes()
    parser = Parser(grammar.grammar)
    tree = parser.parse(source)
    symbol_types = set(NODE_TYPES.get(language, ()))
    results: list[SymbolRecord] = []

    def visit(node) -> None:
        if node.type in symbol_types:
            results.append(
                SymbolRecord(
                    file_path=path.as_posix(),
                    name=_node_name(node, source),
                    symbol_type=node.type,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                )
            )
        for child in node.children:
            visit(child)

    visit(tree.root_node)
    return results
