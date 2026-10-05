"""Guard the dead-code purge against leaving a hole behind.

_commit 10f7bfd_ ("purge dead code") verified each removal by looking for call
sites, then deleted _box_iou() from grounding.py because the only call it
found belonged to text_to_boxes_multi() — deleted in the same pass. The call
that mattered, inside text_to_boxes(), was missed, and text-to-mask raised
NameError on the first DINO box after the forward pass had already run.

Run directly, or under pytest: no undefined name may survive in the package.
"""
import ast
import builtins
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PACKAGE = os.path.join(ROOT, "PyImageLabeling")

BUILTINS = set(dir(builtins))
# module-level names the interpreter provides
IMPLICIT = {"__file__", "__name__", "__doc__", "__package__", "__spec__",
            "__loader__", "__builtins__", "__debug__", "__path__", "WindowsError"}


def undefined_names(path):
    """Names read in a module but never bound in it (crude, low-noise)."""
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        tree = ast.parse(fh.read(), filename=path)

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
        elif isinstance(node, ast.Global):
            bound.update(node.names)

    return [(n.lineno, n.id) for n in used
            if n.id not in BUILTINS and n.id not in IMPLICIT
            and n.id not in bound]


def package_files():
    for dirpath, dirnames, filenames in os.walk(PACKAGE):
        dirnames[:] = [d for d in dirnames
                       if d not in ("__pycache__", "env", "venv", ".venv",
                                    "build", "dist")]
        for name in sorted(filenames):
            if name.endswith(".py"):
                yield os.path.join(dirpath, name)


def test_no_module_has_an_undefined_name():
    problems = []
    for path in package_files():
        for lineno, name in undefined_names(path):
            rel = os.path.relpath(path, ROOT)
            problems.append(f"{rel}:{lineno}: {name}")

    assert not problems, (
        "names read but never bound (a NameError waiting to happen):\n  "
        + "\n  ".join(problems))


def test_purge_helper_agrees():
    """The standalone checker and this module must not drift apart."""
    result = subprocess.run(
        [sys.executable, os.path.join(HERE, "check_undefined_names.py"),
         PACKAGE],
        capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "undefined name(s)" in result.stdout


def test_detector_still_catches_a_missing_helper(tmp_path):
    """A detector that cannot fail is worthless: it must catch the shape of
    the original bug."""
    bad = tmp_path / "bad.py"
    bad.write_text("def f(x):\n    return x + _missing(1)\n",
                   encoding="utf-8")

    found = undefined_names(str(bad))
    assert [name for _, name in found] == ["_missing"]


if __name__ == "__main__":
    sys.exit(subprocess.call(
        [sys.executable, os.path.join(HERE, "check_undefined_names.py"),
         PACKAGE]))