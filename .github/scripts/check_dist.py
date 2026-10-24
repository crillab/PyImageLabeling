"""Refuse a distribution that would leak local files or break once installed.

    python .github/scripts/check_dist.py dist

Checks the wheel and the sdist that `python -m build` put in dist/:
- the wheel installs PyImageLabeling/ only (tests/, pypi/ and build-exec/
  used to slip in as top-level packages);
- no per-user parameters.json (every release up to 1.0.13 shipped the
  maintainer's) and no packaged JSON holding a local absolute path;
- the data files the app opens at startup are there;
- no file above MAX_FILE_KB (four uncompressed icons were 1 MB each);
- the archive names carry the version of the packaged version.json.
"""
import json
import re
import sys
import tarfile
import zipfile
from pathlib import Path

PACKAGE = "PyImageLabeling"
REQUIRED = ["__main__.py", "config.json", "default_parameters.json",
            "version.json", "style.css"]
MAX_FILE_KB = 256
LOCAL_PATH = re.compile(r'"(?:/home/|/Users/|[A-Za-z]:[\\/]+Users)')


def wheel_members(path):
    archive = zipfile.ZipFile(path)
    return {info.filename: (info.file_size,
                            lambda name=info.filename: archive.read(name))
            for info in archive.infolist() if not info.is_dir()}


def sdist_members(path):
    archive = tarfile.open(path)
    members = {}
    for member in archive.getmembers():
        if member.isfile():
            # drop the leading "pyimagelabeling-<version>/"
            name = member.name.split("/", 1)[1]
            members[name] = (member.size,
                             lambda m=member: archive.extractfile(m).read())
    return members


def check(path, members):
    errors = []
    package = {name[len(PACKAGE) + 1:]: entry
               for name, entry in members.items()
               if name.startswith(PACKAGE + "/")}

    if path.suffix == ".whl":
        extra = sorted({name.split("/")[0] for name in members}
                       - {PACKAGE}
                       - {n.split("/")[0] for n in members
                          if n.split("/")[0].endswith(".dist-info")})
        if extra:
            errors.append(f"unexpected top-level entries: {extra}")

    for name in REQUIRED:
        if name not in package:
            errors.append(f"missing {PACKAGE}/{name}")
    if not any(n.startswith("icons/") and n.endswith(".png") for n in package):
        errors.append(f"no {PACKAGE}/icons/*.png")

    for name, (size, read) in sorted(members.items()):
        if name.rsplit("/", 1)[-1] == "parameters.json":
            errors.append(f"per-user settings shipped: {name}")
        if size > MAX_FILE_KB * 1024:
            errors.append(f"{name} is {size // 1024} KB "
                          f"(limit {MAX_FILE_KB} KB)")
        if name.endswith(".json") and LOCAL_PATH.search(
                read().decode("utf-8", "replace")):
            errors.append(f"local absolute path in {name}")

    if "version.json" in package:
        version = json.loads(package["version.json"][1]())["version"]
        if f"-{version}" not in path.name:
            errors.append(f"archive name does not carry version {version}")
    return errors


def main(dist):
    archives = sorted(Path(dist).glob("*.whl")) + sorted(
        Path(dist).glob("*.tar.gz"))
    failed = False
    for kind, pattern in (("wheel", "*.whl"), ("sdist", "*.tar.gz")):
        if len(list(Path(dist).glob(pattern))) != 1:
            print(f"FAIL {dist}: expected exactly one {kind}")
            failed = True
    for path in archives:
        members = (wheel_members(path) if path.suffix == ".whl"
                   else sdist_members(path))
        errors = check(path, members)
        print(f"{'FAIL' if errors else 'ok  '} {path.name} "
              f"({len(members)} files)")
        for error in errors:
            print(f"     - {error}")
        failed = failed or bool(errors)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "dist"))
