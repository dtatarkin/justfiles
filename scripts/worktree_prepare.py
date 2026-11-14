#!/usr/bin/env python3
"""Link a worktree to what its main checkout reads but git does not carry.

A worktree holds the tracked files alone. Two kinds of thing a build or a lint
reads are missing from it: a uv workspace member or path source at `../lib`,
which from a worktree made elsewhere names a directory that is not there; and a
file the main checkout keeps ignored, such as an environment file or a local
task-runner include. Each is linked at its relative path in the worktree to the
same relative path in the main checkout, so the worktree reads the main
checkout's copy and follows it as it changes.

Run from inside the worktree. A path already present is left as it is, so a
second run changes nothing. Run with the standard library alone: a fresh
worktree has no environment yet, and this script is what precedes one.
"""

import argparse
import os
import subprocess
import sys
import tomllib
from collections.abc import Iterable
from pathlib import Path, PurePosixPath
from typing import Any

PARENT = ".."


class PrepareError(Exception):
    pass


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def main_checkout(cwd: Path) -> Path:
    """The checkout whose git directory is the common one. In a submodule that
    directory sits under the superproject's `.git/modules`, and the work tree is
    what its `core.worktree` names, which `--show-toplevel` run there reads."""
    common = Path(git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    try:
        return Path(git(common, "rev-parse", "--show-toplevel"))
    except subprocess.CalledProcessError:
        return common.parent


def _source_paths(sources: dict[str, Any]) -> Iterable[str]:
    # A source is a table, or an array of tables split by markers.
    for source in sources.values():
        for entry in source if isinstance(source, list) else [source]:
            if isinstance(entry, dict) and isinstance(entry.get("path"), str):
                yield entry["path"]


def outside_paths(pyproject: Path) -> list[str]:
    """The entries of a uv workspace's members and path sources that climb out
    of the repository, each cut after the first component past its `..`s: a
    member may be a glob, and linking the directory it lies in serves it."""
    if not pyproject.is_file():
        return []
    uv = tomllib.loads(pyproject.read_text(encoding="utf-8")).get("tool", {}).get("uv", {})
    entries = [*uv.get("workspace", {}).get("members", []), *_source_paths(uv.get("sources", {}))]
    paths: list[str] = []
    for entry in entries:
        parts = PurePosixPath(entry).parts
        climb = next((i for i, part in enumerate(parts) if part != PARENT), len(parts))
        if 0 < climb < len(parts):
            path = str(PurePosixPath(*parts[: climb + 1]))
            if path not in paths:
                paths.append(path)
    return paths


def link(worktree: Path, main: Path, relative: str) -> None:
    """Paths are joined lexically, never resolved, so `../lib` lands beside the
    worktree even where the worktree's parent is itself a link."""
    if os.path.isabs(relative):
        raise PrepareError(f"refused {relative}: give a path relative to the checkout")
    target = Path(os.path.normpath(worktree / relative))
    source = Path(os.path.normpath(main / relative))
    if os.path.lexists(target):
        print(f"kept {relative}")
        return
    if not source.exists():
        raise PrepareError(f"missing {relative}: {source} does not exist")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.symlink_to(source)
    print(f"linked {relative} -> {source}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "paths",
        nargs="*",
        help="more paths relative to the checkout to link, such as .env or ../tools",
    )
    arguments = parser.parse_args()
    worktree = Path(git(Path.cwd(), "rev-parse", "--show-toplevel"))
    main = main_checkout(worktree)
    paths = [*outside_paths(worktree / "pyproject.toml"), *arguments.paths]
    failed = False
    for path in dict.fromkeys(paths):
        try:
            link(worktree, main, path)
        except PrepareError as error:
            print(error, file=sys.stderr)
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
