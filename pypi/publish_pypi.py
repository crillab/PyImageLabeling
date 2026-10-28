"""Build and publish the wheels/sdist on PyPI.

How to release a new version:
- Put the good version in PyImageLabeling/version.json ("version" key).
  The chain is: version.json -> Utils.get_version() -> __version__ in
  PyImageLabeling/__init__.py -> setup.py (reads version.json directly).
- Run this script from pypi/ ; it builds the parent project, then
  uploads and cleans up. Uses Python APIs and the local interpreter
  (no python3/mv/rm shell assumptions), so it works on Windows too.
"""
import glob
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.join(HERE, "..")


def run(cmd):
    print("$ " + " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=PARENT) == 0


input("Type 'enter' to execute: 'python -m build ..'\n")

if not run([sys.executable, "-m", "build", "."]):
    sys.exit("build failed — not publishing.")

# move the artifacts next to this script
for artifact in glob.glob(os.path.join(PARENT, "dist", "*")):
    shutil.move(artifact, HERE)

input("Type 'enter' to publish the wheels on pypi:\n")
ok = run([sys.executable, "-m", "twine", "upload", "--skip-existing",
          "dist/*"])
if not ok:
    sys.exit("twine upload failed.")

input("Type 'enter' to delete the artifacts:\n")
for pattern in ("*.whl", "*.tar.gz"):
    for path in glob.glob(os.path.join(HERE, pattern)):
        os.remove(path)
for leftover in ("dist", "build",
                 os.path.join(PARENT, "PyImageLabeling.egg-info")):
    shutil.rmtree(leftover, ignore_errors=True)
print("done.")
