"""Auto-save snapshots: the write side is Core.auto_save(), this is the
read side.

Core.auto_save() copies the annotation files into <project>/auto_save/ every
few minutes, but until now nothing in the codebase ever read that folder
back. After a native crash the snapshot was only useful if you happened to
know it existed and copied the files by hand.

scan()/needs_recovery()/restore()/close() close that loop:

  * scan() describes the snapshot of a project (no Qt, no model, so it is
    trivially testable and safe to call before the UI exists),
  * needs_recovery() answers the only question that matters: does the
    snapshot hold annotations that are NOT already in the project files?
  * restore() copies the snapshot over the project atomically, then drops it,
  * close() drops a snapshot that has been superseded by a real save.

The snapshot is only *offered*: every decision is made by the caller (a
message box), so declining costs nothing and the snapshot is kept for the
next attempt.
"""
import os
import shutil

DIRNAME = "auto_save"

# What _save_all() writes into a directory. Kept as a suffix filter rather
# than an exact list: a project may hold several masks per image.
JSON_SUFFIX = ".json"
MASK_SUFFIX = ".png"


def autosave_dir(project_dir):
    """Snapshot folder of a project."""
    return os.path.join(project_dir, DIRNAME)


def snapshot_files(directory):
    """Annotation files held by a snapshot folder (sorted, stable order)."""
    try:
        names = os.listdir(directory)
    except OSError:
        return []
    return sorted(
        n for n in names
        if n.endswith(JSON_SUFFIX) or n.endswith(MASK_SUFFIX)
    )


def _project_newest(project_dir):
    """Most recent mtime among the project's own files.

    Sub-directories are skipped on purpose: the snapshot folder is one of
    them, and image sub-folders must not make a fresh snapshot look stale.
    """
    newest = 0.0
    try:
        names = os.listdir(project_dir)
    except OSError:
        return newest
    for name in names:
        path = os.path.join(project_dir, name)
        if os.path.isdir(path):
            continue
        try:
            newest = max(newest, os.path.getmtime(path))
        except OSError:
            continue
    return newest


def scan(project_dir):
    """Describe the snapshot of a project directory.

    Returns a dict with `exists` (bool), `files`, `newest` and
    `project_newest` (mtimes). Never raises: an unreadable directory is
    simply reported as "no snapshot".
    """
    info = {
        "project_dir": project_dir,
        "autosave_dir": None,
        "exists": False,
        "files": [],
        "newest": 0.0,
        "project_newest": 0.0,
    }
    if not project_dir or not os.path.isdir(project_dir):
        return info

    snapshot = autosave_dir(project_dir)
    files = snapshot_files(snapshot)
    if not files:
        return info

    info["autosave_dir"] = snapshot
    info["files"] = files
    info["exists"] = True
    info["newest"] = max(
        os.path.getmtime(os.path.join(snapshot, f)) for f in files)
    info["project_newest"] = _project_newest(project_dir)
    return info


def needs_recovery(project_dir):
    """True when the snapshot is newer than the project itself.

    A snapshot older than the last real save holds nothing new: either the
    user saved normally after it, or Core._save_all() already closed it.
    """
    info = scan(project_dir)
    if not info["exists"]:
        return False
    return info["newest"] > info["project_newest"]


def describe(project_dir):
    """One-paragraph summary for a message box."""
    import datetime

    info = scan(project_dir)
    if not info["exists"]:
        return "No auto-save snapshot found."
    when = datetime.datetime.fromtimestamp(info["newest"]).strftime(
        "%Y-%m-%d %H:%M")
    return (f"{len(info['files'])} annotation file(s) auto-saved at {when}, "
            f"newer than the project files.")


def restore(project_dir):
    """Copy the snapshot over the project, then drop the snapshot.

    Each file is written to a scratch name and renamed, so a crash during
    the restore cannot leave a half-copied mask either. Returns the list of
    restored file names (empty when there was nothing to recover).
    """
    info = scan(project_dir)
    if not info["exists"]:
        return []

    restored = []
    for name in info["files"]:
        src = os.path.join(info["autosave_dir"], name)
        dst = os.path.join(project_dir, name)
        tmp = dst + ".tmp"
        shutil.copyfile(src, tmp)
        os.replace(tmp, dst)
        restored.append(name)

    close(project_dir)
    return restored


def close(project_dir):
    """Delete the snapshot folder. Returns True when it is gone."""
    snapshot = autosave_dir(project_dir)
    if not os.path.isdir(snapshot):
        return True
    shutil.rmtree(snapshot, ignore_errors=True)
    return not os.path.isdir(snapshot)


def candidate_projects(parameters):
    """Project directories worth checking, from the persisted parameters."""
    out = []
    for section in ("save", "load"):
        path = (parameters.get(section) or {}).get("path")
        if not path:
            continue
        path = os.path.normpath(path)
        if os.path.isdir(path) and path not in out:
            out.append(path)
    return out


def pending_recovery(parameters=None):
    """First project holding a snapshot newer than its files, else None."""
    if parameters is None:
        from PyImageLabeling.model.Utils import Utils
        parameters = Utils.load_parameters()
    for project_dir in candidate_projects(parameters):
        if needs_recovery(project_dir):
            return scan(project_dir)
    return None