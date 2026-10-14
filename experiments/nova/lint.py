"""Dependency/side-effect boundary lint plus Python syntax and whitespace checks."""
import ast
from pathlib import Path
import sys
import tabnanny

ALLOWED = {"__future__", "argparse", "ast", "contextlib", "copy", "hashlib", "itertools", "json", "math", "pathlib",
           "random", "re", "sqlite3", "statistics", "sys", "tabnanny", "unicodedata"}


def check():
    errors = []
    for path in sorted(Path(__file__).parent.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
        tabnanny.check(str(path))
        compile(tree, str(path), "exec")
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [] if node.level else [node.module]
            else:
                modules = []
            for module in modules:
                if module != "experiments.narrative_mechanics" and module.split(".")[0] not in ALLOWED:
                    errors.append(f"{path.name}:{node.lineno}: forbidden dependency {module}")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec", "__import__"}:
                errors.append(f"{path.name}:{node.lineno}: dynamic execution forbidden")
        for line, content in enumerate(text.splitlines(), 1):
            if content.rstrip() != content or "\t" in content:
                errors.append(f"{path.name}:{line}: whitespace")
    return errors


if __name__ == "__main__":
    findings = check()
    print("\n".join(findings) if findings else "PASS: syntax, whitespace, dependency isolation")
    sys.exit(bool(findings))
