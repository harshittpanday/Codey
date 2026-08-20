from pathlib import Path
from codey.scanner import discover_files,language_for
def test_language_detection():assert language_for(Path("main.py"))=="Python" and language_for(Path("app.tsx"))=="TypeScript"
def test_scanner_ignores_common_dirs(tmp_path):
 (tmp_path/"src").mkdir();(tmp_path/"node_modules").mkdir();(tmp_path/"src"/"main.py").write_text("x");(tmp_path/"node_modules"/"bad.js").write_text("x");assert [p.name for p in discover_files(tmp_path)]==["main.py"]
def test_gitignore(tmp_path):
 (tmp_path/".gitignore").write_text("secret.txt\n");(tmp_path/"keep.txt").write_text("ok");(tmp_path/"secret.txt").write_text("no");assert "secret.txt" not in [p.name for p in discover_files(tmp_path)]
