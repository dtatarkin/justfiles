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


def _ensure_on_branch(repo: Path, branch: str) -> None:
    """If `repo`'s HEAD is detached, switch to `branch` (creating it if needed)."""
    r = git_ops.run_git(repo, "symbolic-ref", "--quiet", "HEAD", check=False)
    if r.returncode == 0:
        return
    git_ops.run_git(repo, "checkout", branch)


def _fast_forward_to_origin(repo: Path, branch: str, label: str) -> None:
    """Fetch and fast-forward `repo`'s `branch` to `origin/<branch>`.

    Without this, the parent's `git push` at the end of an iteration races
    against any concurrent push to origin and is rejected with "fetch first".
    A non-fast-forward state aborts cleanly so the operator can resolve the
    divergence rather than have cascade-pins guess.
    """
    git_ops.fetch(repo)
    r = git_ops.run_git(repo, "merge", "--ff-only", f"origin/{branch}", check=False)
    if r.returncode != 0:
        raise RuntimeError(
            f"{label}: local branch {branch} is not a fast-forward of "
            f"origin/{branch}. Resolve manually (git pull --rebase, or merge) "
            f"and re-run cascade-pins."
        )


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

        # Make sure the parent commits land on the configured branch, not a
        # detached HEAD — otherwise a later `git push` from that nested
        # checkout fails with "not currently on a branch".
        _ensure_on_branch(parent_dir, graph.branch)

        # Pull any concurrent origin work into the parent before we commit on
        # it. Without this, push at the end of the iteration races and is
        # rejected with "fetch first" whenever someone else has advanced
        # origin between plan time and push time.
        _fast_forward_to_origin(parent_dir, graph.branch, parent_path or "<root>")

        for bump in resolved:
            child_dir = root / bump.child
            if bump.child in new_shas:
                # Propagated bump: we committed in this child earlier in the
                # run, so its branch HEAD is already at the new SHA.
                continue
            git_ops.fetch(child_dir)
            _ensure_on_branch(child_dir, graph.branch)
            head = git_ops.run_git(child_dir, "rev-parse", "HEAD").stdout.strip()
            if head != bump.new_sha:
                git_ops.run_git(child_dir, "merge", "--ff-only", bump.new_sha)

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

        # `parent_has_pyproject` does not imply a local uv.lock: workspace
        # members have a pyproject.toml but the lockfile lives at the outer
        # workspace root. Their `uv lock` invocation above updates that outer
        # lockfile, which the outer parent's iteration stages on its own.
        if parent_has_pyproject and not opts.no_uv_lock and (parent_dir / "uv.lock").is_file():
            r = git_ops.run_git(parent_dir, "diff", "--quiet", "uv.lock", check=False)
            if r.returncode != 0:
                git_ops.run_git(parent_dir, "add", "uv.lock")

        # If origin already had every bump (e.g. a concurrent cascade-pins run
        # pushed the same plan first and we just fast-forwarded into it), the
        # index now matches HEAD — `git commit` would fail with "nothing to
        # commit". Treat that as success and propagate the parent's HEAD SHA
        # so deeper-up parents resolve correctly.
        diff = git_ops.run_git(parent_dir, "diff", "--cached", "--quiet", check=False)
        if diff.returncode == 0:
            sha = git_ops.run_git(parent_dir, "rev-parse", "HEAD").stdout.strip()
            committed.append((parent_path, sha))
            new_shas[parent_path] = sha
            continue

        msg = messages.render_commit_message(plan.root, resolved, summary=opts.message)
        git_ops.run_git(parent_dir, "commit", "-m", msg)

        sha = git_ops.run_git(parent_dir, "rev-parse", "HEAD").stdout.strip()
        committed.append((parent_path, sha))
        new_shas[parent_path] = sha

        if opts.push:
            git_ops.run_git(parent_dir, "push", "origin", graph.branch)
            pushed.append(parent_path)

    return ExecuteResult(committed=committed, pushed=pushed)
