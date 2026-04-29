from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from . import git_ops
from .graph import basename
from .plan import Bump

_SHA_RE = re.compile(r"^[0-9a-f]+$")


def _short(sha: str, n: int = 7) -> str:
    return sha[:n] if _SHA_RE.match(sha) else sha


def render_commit_message(
    graph_root: str | Path,
    bumps: Sequence[Bump],
    *,
    summary: str | None = None,
) -> str:
    if not bumps:
        raise ValueError("render_commit_message requires at least one bump")
    names = [basename(b.child) for b in bumps]
    first = "Bump " + ", ".join(names) + " pins"
    if summary:
        first = first + ": " + summary
    body: list[str] = []
    for bump in bumps:
        child_dir = Path(graph_root) / bump.child
        body.append("")
        body.append(f"{basename(bump.child)} @ {_short(bump.old_sha)}..{_short(bump.new_sha)}")
        for subj in _subjects_between(child_dir, bump.old_sha, bump.new_sha):
            body.append(f"  {subj}")
        archives = _archived_changes(child_dir, bump.old_sha, bump.new_sha)
        if archives:
            body.append(f"  (archived: {', '.join(archives)})")
    return first + "\n" + "\n".join(body).rstrip() + "\n"


def _subjects_between(child_dir: Path, old_sha: str, new_sha: str) -> list[str]:
    if not _SHA_RE.match(old_sha) or not _SHA_RE.match(new_sha):
        return []
    try:
        out = git_ops.run_git(child_dir, "log", f"{old_sha}..{new_sha}", "--pretty=%s").stdout
    except git_ops.GitError:
        return []
    return [s for s in (line.strip() for line in out.splitlines()) if s]


def _archived_changes(child_dir: Path, old_sha: str, new_sha: str) -> list[str]:
    if not _SHA_RE.match(old_sha) or not _SHA_RE.match(new_sha):
        return []
    try:
        out = git_ops.run_git(
            child_dir,
            "log",
            f"{old_sha}..{new_sha}",
            "--diff-filter=A",
            "--name-only",
            "--pretty=format:",
            "--",
            "openspec/changes/archive/",
        ).stdout
    except git_ops.GitError:
        return []
    names: list[str] = []
    seen: set[str] = set()
    prefix = "openspec/changes/archive/"
    for raw in out.splitlines():
        line = raw.strip()
        if not line.startswith(prefix):
            continue
        first_seg = line[len(prefix) :].split("/", 1)[0]
        if first_seg and first_seg not in seen:
            seen.add(first_seg)
            names.append(first_seg)
    return names
