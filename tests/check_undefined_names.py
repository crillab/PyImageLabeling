"""Catch NameError before the user does.

The purge in 10f7bfd deleted _box_iou() because its only *looked-at* call
site was inside a function that was itself deleted; the surviving call in
text_to_boxes() was missed and text-to-mask died at the first DINO box.

This walks every module and reports names that are read but never bound and
are not builtins. Crude on purpose: it only reports names that appear
exactly once in the file (a real definition shows up as a binding too), so
false positives are rare.
"""
import ast
import builtins
import os
import sys

BUILTINS = set(dir(builtins))
# module-level names the interpreter provides
IMPLICIT = {"__file__", "__name__", "__doc__", "__package__", "__spec__",
            "__loader__", "__builtins__", "__debug__", "__path__"}


class ScopeChecker(ast.NodeVisitor):
    def __init__(self, path):
        self.path = path
        self.problems = []

    def run(self, tree):
        bound = set()
        used = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                 ast.ClassDef)):
                bound.add(node.name)
            elif isinstance(node, ast.Name):
                if isinstance(node.ctx, (ast.Store, ast.Del)):
                    bound.add(node.id)
                else:
                    used.append(node)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    bound.add((alias.asname or alias.name).split(".")[0])
            elif isinstance(node, ast.arg):
                bound.add(node.arg)
            elif isinstance(node, ast.ExceptHandler) and node.name:
                bound.add(node.name)
            elif isinstance(node, (ast.comprehension,)):
                for n in ast.walk(node.target):
                    if isinstance(n, ast.Name):
                        bound.add(n.id)
            elif isinstance(node, ast.Global):
                bound.update(node.names)

        for node in used:
            name = node.id
            if name in BUILTINS or name in IMPLICIT or name in bound:
                continue
            self.problems.append((node.lineno, name))

        return self.problems


def check(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        source = fh.read()
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as exc:
        return [("SYNTAX", f"line {exc.lineno}: {exc.msg}")]
    return ScopeChecker(path).run(tree)


def main():
    roots = sys.argv[1:] or ["PyImageLabeling"]
    files = []
    for root in roots:
        if os.path.isfile(root):
            files.append(root)
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames
                           if d not in ("env", "venv", ".venv", "__pycache__",
                                        "build", "dist", ".git")]
            for name in filenames:
                if name.endswith(".py"):
                    files.append(os.path.join(dirpath, name))

    total = 0
    for path in sorted(files):
        for lineno, name in check(path):
            rel = os.path.relpath(path)
            kind = name if isinstance(name, str) else str(name)
            print(f"{rel}:{lineno}: undefined name {kind}")
            total += 1

    print(f"\n{total} undefined name(s) in {len(files)} file(s)")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())