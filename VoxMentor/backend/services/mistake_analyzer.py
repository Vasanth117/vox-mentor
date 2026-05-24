"""
Static code analysis for common mistake patterns using Python's ast module.
For non-Python code, uses simple regex-based heuristics.
"""
import ast
import re
from typing import List


class MistakeAnalyzer:

    # ── Python AST Checks ────────────────────────────────────────────────────

    def analyze_python(self, code: str) -> List[dict]:
        mistakes = []
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return [{"type": "syntax_error", "description": str(e), "severity": "error"}]

        for node in ast.walk(tree):
            # Missing return in function
            if isinstance(node, ast.FunctionDef):
                has_return = any(isinstance(n, ast.Return) and n.value is not None
                                 for n in ast.walk(node))
                if not has_return and node.name not in ("__init__", "main"):
                    mistakes.append({
                        "type": "missing_return",
                        "description": f"Function '{node.name}' has no return statement.",
                        "severity": "warning",
                        "line": node.lineno,
                    })

            # Bare except
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                mistakes.append({
                    "type": "bare_except",
                    "description": "Bare 'except:' catches all exceptions including SystemExit — use 'except Exception:'.",
                    "severity": "warning",
                    "line": node.lineno,
                })

            # Using == for None comparison
            if isinstance(node, ast.Compare):
                for op in node.ops:
                    if isinstance(op, ast.Eq):
                        for comp in node.comparators:
                            if isinstance(comp, ast.Constant) and comp.value is None:
                                mistakes.append({
                                    "type": "none_comparison",
                                    "description": "Use 'is None' instead of '== None'.",
                                    "severity": "info",
                                    "line": node.lineno,
                                })

            # Mutable default argument
            if isinstance(node, ast.FunctionDef):
                for default in node.args.defaults:
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        mistakes.append({
                            "type": "mutable_default_arg",
                            "description": f"Mutable default argument in '{node.name}' — use None and set inside function.",
                            "severity": "warning",
                            "line": node.lineno,
                        })

        return mistakes

    # ── Generic Heuristics ───────────────────────────────────────────────────

    def analyze_generic(self, code: str, language: str) -> List[dict]:
        mistakes = []
        lines = code.splitlines()

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Infinite loop risk: while(true) with no break
            if re.search(r"while\s*\(\s*true\s*\)|while\s*True\s*:", stripped, re.I):
                has_break = any("break" in l for l in lines)
                if not has_break:
                    mistakes.append({
                        "type": "infinite_loop_risk",
                        "description": "while(true) loop detected with no apparent break — could cause infinite loop.",
                        "severity": "warning",
                        "line": i,
                    })

            # Magic numbers
            if re.search(r"[^-\w](?<![.])(?:(?<!\d)\d{3,}(?!\d))", stripped):
                mistakes.append({
                    "type": "magic_number",
                    "description": f"Large literal number on line {i} — consider using a named constant.",
                    "severity": "info",
                    "line": i,
                })

            # Missing semicolon in C/C++
            if language in ("c", "cpp") and stripped and not stripped.endswith((";", "{", "}", "//", "*/")):
                if not stripped.startswith(("#", "//", "/*", "*")) and not stripped.endswith(":"):
                    if any(kw in stripped for kw in ("printf", "scanf", "return", "int ", "float ", "=")):
                        pass  # heuristic — only flag if complex statement

        return mistakes

    def analyze(self, code: str, language: str) -> List[dict]:
        if language.lower() == "python":
            return self.analyze_python(code)
        return self.analyze_generic(code, language)


analyzer = MistakeAnalyzer()
