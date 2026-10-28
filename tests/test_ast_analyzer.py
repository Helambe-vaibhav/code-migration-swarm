"""
tests/test_ast_analyzer.py
--------------------------
Unit tests verifying AST parsing, deprecated pattern detection, and topological sorting.
"""

from pathlib import Path
from code_migration_swarm.ast_analyzer import CodeASTAnalyzer


def test_discover_python_files(tmp_path: Path):
    (tmp_path / "mod_a.py").write_text("x = 1")
    (tmp_path / "mod_b.py").write_text("y = 2")
    (tmp_path / ".hidden.py").write_text("z = 3")

    analyzer = CodeASTAnalyzer(str(tmp_path))
    files = analyzer.discover_python_files()

    names = [f.name for f in files]
    assert "mod_a.py" in names
    assert "mod_b.py" in names
    assert ".hidden.py" not in names


def test_deprecated_pattern_detection(tmp_path: Path):
    code = """
import time
import requests

def fetch_data(url):
    time.sleep(1)
    res = requests.get(url)
    return res.text
"""
    f = tmp_path / "legacy.py"
    f.write_text(code)

    analyzer = CodeASTAnalyzer(str(tmp_path))
    result = analyzer.analyze_file(f)

    assert any("requests" in p for p in result.deprecated_patterns)
    assert any("time.sleep" in p for p in result.deprecated_patterns)


def test_topological_migration_order(tmp_path: Path):
    # base.py is imported by models.py, which is imported by service.py
    (tmp_path / "base.py").write_text("class Base: pass")
    (tmp_path / "models.py").write_text("from base import Base\nclass User(Base): pass")
    (tmp_path / "service.py").write_text("from models import User\ndef get_user(): return User()")

    analyzer = CodeASTAnalyzer(str(tmp_path))
    order = analyzer.get_migration_order()

    # base.py must precede models.py, which must precede service.py
    assert order.index("base.py") < order.index("models.py")
    assert order.index("models.py") < order.index("service.py")
