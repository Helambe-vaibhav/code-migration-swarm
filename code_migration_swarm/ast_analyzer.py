"""
ast_analyzer.py
---------------
AST-based static dependency analysis and legacy code pattern detection.
Computes topological dependency ordering for safe module migration sequencing.
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Any
from graphlib import TopologicalSorter, CycleError

from .state import ASTAnalysisResult, ASTClassInfo, ASTFunctionInfo


class CodeASTAnalyzer:
    """
    Analyzes Python source trees via native AST parsing to build dependency DAGs,
    detect deprecated architectural patterns, and guide migration sequence.
    """

    DEPRECATED_PATTERNS = {
        "urllib2": "requests/urllib2: Legacy Python 2/3 urllib2 import; modern alternative: httpx or aiohttp",
        "requests": "requests: Synchronous blocking HTTP client; recommend migrating to async httpx.AsyncClient",
        "time.sleep": "time.sleep: Synchronous thread-blocking sleep; recommend asyncio.sleep()",
        "raw_sql_interpolation": "sql: Potentially unsafe string-formatted SQL query; recommend SQLAlchemy 2.0 ORM or asyncpg parameterized queries",
        "missing_type_hints": "typing: Function lacks explicit type annotations",
        "legacy_dict_methods": "dict: Deprecated dict methods (has_key, iteritems, itervalues)",
        "bare_except": "exception: Anti-pattern bare except clause",
    }

    def __init__(self, project_root: str):
        self.project_root = Path(project_root).resolve()

    def discover_python_files(self) -> List[Path]:
        """Finds all non-hidden python files excluding tests/venv."""
        files = []
        for p in self.project_root.rglob("*.py"):
            parts = p.parts
            if any(part.startswith(".") or part in ("venv", ".venv", "__pycache__", "build", "dist") for part in parts):
                continue
            files.append(p)
        return sorted(files)

    def analyze_file(self, file_path: Path) -> ASTAnalysisResult:
        rel_path = str(file_path.relative_to(self.project_root))
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(file_path))
        except Exception as e:
            return ASTAnalysisResult(
                file_path=rel_path,
                summary=f"AST parse error: {str(e)}"
            )

        imports: List[str] = []
        internal_deps: List[str] = []
        classes: List[ASTClassInfo] = []
        functions: List[ASTFunctionInfo] = []
        deprecated: List[str] = []
        complexity = 1

        all_known_modules = {p.stem for p in self.discover_python_files()}

        for node in ast.walk(tree):
            # Complexity increment
            if isinstance(node, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With, ast.Assert)):
                complexity += 1

            # Imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
                    base_mod = alias.name.split(".")[0]
                    if base_mod in all_known_modules:
                        internal_deps.append(base_mod)
                    if alias.name in ("urllib2", "requests"):
                        deprecated.append(self.DEPRECATED_PATTERNS.get(alias.name, alias.name))

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
                    base_mod = node.module.split(".")[0]
                    if base_mod in all_known_modules:
                        internal_deps.append(base_mod)
                    if node.module in ("urllib2", "requests"):
                        deprecated.append(self.DEPRECATED_PATTERNS.get(node.module, node.module))

            # Classes
            elif isinstance(node, ast.ClassDef):
                bases = [ast.unparse(b) for b in node.bases]
                methods = [m.name for m in node.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]
                doc = ast.get_docstring(node)
                classes.append(ASTClassInfo(name=node.name, bases=bases, methods=methods, docstring=doc))

            # Functions (module-level)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = [a.arg for a in node.args.args]
                has_hints = any(a.annotation is not None for a in node.args.args) or (node.returns is not None)
                if not has_hints and len(args) > 0 and args != ["self"] and args != ["cls"]:
                    deprecated.append(f"Function '{node.name}' lacks type annotations.")

                calls = []
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Call):
                        call_repr = ast.unparse(sub.func)
                        calls.append(call_repr)
                        if "time.sleep" in call_repr:
                            deprecated.append(self.DEPRECATED_PATTERNS["time.sleep"])
                        if any(term in call_repr.lower() for term in ("execute", "cursor")) and "%" in ast.unparse(sub):
                            deprecated.append(self.DEPRECATED_PATTERNS["raw_sql_interpolation"])

                functions.append(ASTFunctionInfo(
                    name=node.name,
                    args=args,
                    is_async=isinstance(node, ast.AsyncFunctionDef),
                    docstring=ast.get_docstring(node),
                    has_type_hints=has_hints,
                    calls=calls[:15]
                ))

            # Bare except
            elif isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    deprecated.append(self.DEPRECATED_PATTERNS["bare_except"])

        return ASTAnalysisResult(
            file_path=rel_path,
            imports=sorted(list(set(imports))),
            internal_dependencies=sorted(list(set(internal_deps))),
            classes=classes,
            functions=functions,
            deprecated_patterns=sorted(list(set(deprecated))),
            cyclomatic_complexity=complexity,
            summary=f"{len(classes)} classes, {len(functions)} functions, {len(deprecated)} legacy patterns detected."
        )

    def build_dependency_graph(self) -> Dict[str, List[str]]:
        """
        Maps relative file paths to list of relative file paths they depend on.
        """
        py_files = self.discover_python_files()
        stem_to_rel = {f.stem: str(f.relative_to(self.project_root)) for f in py_files}
        graph: Dict[str, List[str]] = {}

        for f in py_files:
            rel = str(f.relative_to(self.project_root))
            analysis = self.analyze_file(f)
            deps = []
            for dep_stem in analysis.internal_dependencies:
                if dep_stem in stem_to_rel and stem_to_rel[dep_stem] != rel:
                    deps.append(stem_to_rel[dep_stem])
            graph[rel] = sorted(list(set(deps)))

        return graph

    def get_migration_order(self) -> List[str]:
        """
        Returns list of file paths in topological migration order (leaf modules first).
        """
        graph = self.build_dependency_graph()
        # TopologicalSorter expects node: {predecessors}
        sorter = TopologicalSorter()
        for node, deps in graph.items():
            sorter.add(node, *deps)

        try:
            order = list(sorter.static_order())
            return order
        except CycleError:
            # Fallback to depth/complexity order if circular imports exist
            return sorted(list(graph.keys()), key=lambda k: len(graph[k]))
