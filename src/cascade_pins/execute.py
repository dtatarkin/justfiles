from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from . import git_ops, messages, uv_ops
from .graph import Graph
from .plan import Bump, Plan


@dataclass(frozen=True)
class ExecuteOptions:
    push: bool = False
    no_uv_lock: bool = False
    dry_run: bool = False
    message: str | None = None


@dataclass
class ExecuteResult:
    committed: list[tuple[str, str]]
    pushed: list[str]


def _relpath_under(parent_path: str, child_path: str) -> str:
    if not parent_path:
        return child_path
    if not child_path.startswith(parent_path + "/"):
        raise ValueError(f"{child_path!r} is not under parent {parent_path!r}")
    return child_path[len(parent_path) + 1 :]


def execute_plan(plan: Plan, graph: Graph, opts: ExecuteOptions) -> ExecuteResult:
    root = Path(plan.root)
    by_path = graph.by_path()
    new_shas: dict[str, str] = {}
    committed: list[tuple[str, str]] = []
    pushed: list[str] = []

    for parent_path, group in plan.by_parent():
        parent_dir = root if parent_path == "" else root / parent_path

        resolved: list[Bump] = []
        for b in group:
            target = new_shas.get(b.child) or b.new_sha
            if not target:
                raise RuntimeError(
                    f"could not resolve target SHA for {b.child} (parent={parent_path!r})"
                )
            resolved.append(replace(b, new_sha=target))

        for bump in resolved:
            child_dir = root / bump.child
            git_ops.fetch(child_dir)
            git_ops.run_git(child_dir, "checkout", "--detach", bump.new_sha)

        parent_node = by_path.get(parent_path) if parent_path else None
        if parent_node is not None:
            parent_has_pyproject = parent_node.has_pyproject
        else:
            parent_has_pyproject = (parent_dir / "pyproject.toml").is_file()

        if parent_has_pyproject and not opts.no_uv_lock:
            uv_ops.lock(parent_dir)

        if opts.dry_run:
            committed.append((parent_path, "<dry-run>"))
            continue

        rel_child_paths = [_relpath_under(parent_path, b.child) for b in resolved]
        git_ops.run_git(parent_dir, "add", *rel_child_paths)

        if parent_has_pyproject and not opts.no_uv_lock:
            r = git_ops.run_git(parent_dir, "diff", "--quiet", "uv.lock", check=False)
            if r.returncode != 0:
                git_ops.run_git(parent_dir, "add", "uv.lock")

        msg = messages.render_commit_message(plan.root, resolved, summary=opts.message)
        git_ops.run_git(parent_dir, "commit", "-m", msg)

        sha = git_ops.run_git(parent_dir, "rev-parse", "HEAD").stdout.strip()
        committed.append((parent_path, sha))
        new_shas[parent_path] = sha

        if opts.push:
            git_ops.run_git(parent_dir, "push")
            pushed.append(parent_path)

    return ExecuteResult(committed=committed, pushed=pushed)
