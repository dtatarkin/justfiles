import os
import subprocess
from pathlib import Path

import pytest

from cascade_pins import execute as execute_mod
from cascade_pins import graph as graph_mod
from cascade_pins import plan as plan_mod


def _run(args: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> str:
    proc = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"{' '.join(args)} (cwd={cwd}) exit {proc.returncode}\n"
            f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
        )
    return proc.stdout


def _git(args: list[str], cwd: Path, env: dict[str, str]) -> str:
    return _run(["git", *args], cwd=cwd, env=env)


@pytest.fixture
def git_env() -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "Test"
    env["GIT_AUTHOR_EMAIL"] = "test@example.com"
    env["GIT_COMMITTER_NAME"] = "Test"
    env["GIT_COMMITTER_EMAIL"] = "test@example.com"
    return env


def _init_bare(path: Path, env: dict[str, str]) -> None:
    path.mkdir(parents=True)
    _run(["git", "init", "--bare", "-b", "main", str(path)], env=env)


def _add_submodule(parent: Path, url: str, sub_path: str, env: dict[str, str]) -> None:
    _git(
        [
            "-c",
            "protocol.file.allow=always",
            "submodule",
            "add",
            "-b",
            "main",
            url,
            sub_path,
        ],
        cwd=parent,
        env=env,
    )


def test_three_layer_cascade(tmp_path: Path, git_env: dict[str, str]) -> None:
    bare = tmp_path / "bare"
    for name in ("child", "parent", "grand"):
        _init_bare(bare / f"{name}.git", env=git_env)

    work = tmp_path / "work"
    work.mkdir()

    # 1) child: one commit, push.
    child = work / "child"
    _run(["git", "clone", str(bare / "child.git"), str(child)], env=git_env)
    (child / "README.md").write_text("hello\n")
    _git(["add", "."], cwd=child, env=git_env)
    _git(["commit", "-m", "init child"], cwd=child, env=git_env)
    _git(["push", "origin", "main"], cwd=child, env=git_env)

    # 2) parent: add child as submodule, commit, push.
    parent = work / "parent"
    _run(["git", "clone", str(bare / "parent.git"), str(parent)], env=git_env)
    _add_submodule(parent, str(bare / "child.git"), "child", git_env)
    _git(["commit", "-m", "init parent with child"], cwd=parent, env=git_env)
    _git(["push", "origin", "main"], cwd=parent, env=git_env)

    # 3) grand: add parent as submodule, init recursively, commit, push.
    grand = work / "grand"
    _run(["git", "clone", str(bare / "grand.git"), str(grand)], env=git_env)
    _add_submodule(grand, str(bare / "parent.git"), "parent", git_env)
    _git(
        [
            "-c",
            "protocol.file.allow=always",
            "submodule",
            "update",
            "--init",
            "--recursive",
        ],
        cwd=grand,
        env=git_env,
    )
    _git(["commit", "-m", "init grand with parent"], cwd=grand, env=git_env)
    _git(["push", "origin", "main"], cwd=grand, env=git_env)

    # 4) Make a new commit in child (separate clone) and push.
    upstream = work / "upstream-child"
    _run(["git", "clone", str(bare / "child.git"), str(upstream)], env=git_env)
    (upstream / "feature.txt").write_text("feature\n")
    _git(["add", "."], cwd=upstream, env=git_env)
    _git(["commit", "-m", "Add feature"], cwd=upstream, env=git_env)
    _git(["push", "origin", "main"], cwd=upstream, env=git_env)
    new_child_sha = _git(["rev-parse", "HEAD"], cwd=upstream, env=git_env).strip()

    # 5) Run cascade-pins from grand.
    g = graph_mod.build_graph(grand, branch="main")
    p = plan_mod.compute_plan(g)
    assert p.bumps, "expected at least one bump"
    result = execute_mod.execute_plan(p, g, execute_mod.ExecuteOptions(no_uv_lock=True))

    # Two parents committed: grand/parent/child's parent (= "parent"), then root ("").
    parents_committed = [parent_path for parent_path, _ in result.committed]
    assert parents_committed == ["parent", ""]

    # 6) Verify: grand's pin for parent now points to parent's nested HEAD;
    # parent's nested HEAD pins child at new_child_sha.
    parent_in_grand = grand / "parent"
    parent_head_in_grand = _git(["rev-parse", "HEAD"], cwd=parent_in_grand, env=git_env).strip()
    grand_pin_for_parent = _git(["ls-tree", "HEAD", "parent"], cwd=grand, env=git_env)
    assert grand_pin_for_parent.split()[2] == parent_head_in_grand

    parent_pin_for_child = _git(["ls-tree", "HEAD", "child"], cwd=parent_in_grand, env=git_env)
    assert parent_pin_for_child.split()[2] == new_child_sha

    # 7) Idempotency: another build+plan should be empty.
    g2 = graph_mod.build_graph(grand, branch="main")
    p2 = plan_mod.compute_plan(g2)
    assert p2.bumps == ()


def test_parent_ahead_of_origin_aborts_cleanly(tmp_path: Path, git_env: dict[str, str]) -> None:
    """If the parent's local branch has diverged from origin (not a
    fast-forward), cascade-pins must abort with a structured error rather
    than commit and then fail at push time with `(fetch first)`.
    """
    bare = tmp_path / "bare"
    for name in ("child", "parent"):
        _init_bare(bare / f"{name}.git", env=git_env)

    work = tmp_path / "work"
    work.mkdir()

    child = work / "child"
    _run(["git", "clone", str(bare / "child.git"), str(child)], env=git_env)
    (child / "README.md").write_text("hello\n")
    _git(["add", "."], cwd=child, env=git_env)
    _git(["commit", "-m", "init child"], cwd=child, env=git_env)
    _git(["push", "origin", "main"], cwd=child, env=git_env)

    parent = work / "parent"
    _run(["git", "clone", str(bare / "parent.git"), str(parent)], env=git_env)
    _add_submodule(parent, str(bare / "child.git"), "child", git_env)
    _git(["commit", "-m", "init parent with child"], cwd=parent, env=git_env)
    _git(["push", "origin", "main"], cwd=parent, env=git_env)

    # Concurrent actor advances origin/main of the parent (a different
    # commit, on the same branch, that the local parent doesn't know about).
    other = work / "other-parent"
    _run(["git", "clone", str(bare / "parent.git"), str(other)], env=git_env)
    (other / "FEATURE.md").write_text("from elsewhere\n")
    _git(["add", "."], cwd=other, env=git_env)
    _git(["commit", "-m", "Concurrent commit elsewhere"], cwd=other, env=git_env)
    _git(["push", "origin", "main"], cwd=other, env=git_env)

    # Local parent makes a divergent commit (no merge base on top).
    (parent / "LOCAL.md").write_text("local\n")
    _git(["add", "."], cwd=parent, env=git_env)
    _git(["commit", "-m", "Divergent local commit"], cwd=parent, env=git_env)

    # Push a new child commit so the planner has something to bump.
    upstream = work / "upstream-child"
    _run(["git", "clone", str(bare / "child.git"), str(upstream)], env=git_env)
    (upstream / "feature.txt").write_text("feature\n")
    _git(["add", "."], cwd=upstream, env=git_env)
    _git(["commit", "-m", "Add feature"], cwd=upstream, env=git_env)
    _git(["push", "origin", "main"], cwd=upstream, env=git_env)

    g = graph_mod.build_graph(parent, branch="main")
    p = plan_mod.compute_plan(g)
    assert p.bumps, "expected at least one bump for child"

    with pytest.raises(RuntimeError, match="not a fast-forward"):
        execute_mod.execute_plan(p, g, execute_mod.ExecuteOptions(no_uv_lock=True))


def test_parent_already_synced_skips_commit(tmp_path: Path, git_env: dict[str, str]) -> None:
    """If origin already has the bump (e.g. a concurrent cascade-pins run
    pushed it first), cascade-pins must fast-forward into it and skip the
    commit cleanly rather than fail with `nothing to commit`.
    """
    bare = tmp_path / "bare"
    for name in ("child", "parent"):
        _init_bare(bare / f"{name}.git", env=git_env)

    work = tmp_path / "work"
    work.mkdir()

    child = work / "child"
    _run(["git", "clone", str(bare / "child.git"), str(child)], env=git_env)
    (child / "README.md").write_text("hello\n")
    _git(["add", "."], cwd=child, env=git_env)
    _git(["commit", "-m", "init child"], cwd=child, env=git_env)
    _git(["push", "origin", "main"], cwd=child, env=git_env)

    parent = work / "parent"
    _run(["git", "clone", str(bare / "parent.git"), str(parent)], env=git_env)
    _add_submodule(parent, str(bare / "child.git"), "child", git_env)
    _git(["commit", "-m", "init parent with child"], cwd=parent, env=git_env)
    _git(["push", "origin", "main"], cwd=parent, env=git_env)

    # New child commit, pushed.
    upstream = work / "upstream-child"
    _run(["git", "clone", str(bare / "child.git"), str(upstream)], env=git_env)
    (upstream / "feature.txt").write_text("feature\n")
    _git(["add", "."], cwd=upstream, env=git_env)
    _git(["commit", "-m", "Add feature"], cwd=upstream, env=git_env)
    _git(["push", "origin", "main"], cwd=upstream, env=git_env)
    new_child_sha = _git(["rev-parse", "HEAD"], cwd=upstream, env=git_env).strip()

    # Concurrent actor already cascaded the bump into the parent and pushed.
    sibling = work / "sibling-parent"
    _run(["git", "clone", str(bare / "parent.git"), str(sibling)], env=git_env)
    _git(
        [
            "-c",
            "protocol.file.allow=always",
            "submodule",
            "update",
            "--init",
            "--recursive",
        ],
        cwd=sibling,
        env=git_env,
    )
    sibling_child = sibling / "child"
    _git(["fetch", "origin", "main"], cwd=sibling_child, env=git_env)
    _git(["checkout", "main"], cwd=sibling_child, env=git_env)
    _git(["merge", "--ff-only", new_child_sha], cwd=sibling_child, env=git_env)
    _git(["add", "child"], cwd=sibling, env=git_env)
    _git(["commit", "-m", "Bump child (sibling cascade)"], cwd=sibling, env=git_env)
    _git(["push", "origin", "main"], cwd=sibling, env=git_env)

    g = graph_mod.build_graph(parent, branch="main")
    p = plan_mod.compute_plan(g)
    assert p.bumps, "expected at least one bump"

    # Local parent runs the cascade. Origin already has the bump; we expect
    # a clean fast-forward + skip rather than an error.
    result = execute_mod.execute_plan(p, g, execute_mod.ExecuteOptions(no_uv_lock=True))
    assert len(result.committed) == 1
    parent_head = _git(["rev-parse", "HEAD"], cwd=parent, env=git_env).strip()
    assert result.committed[0] == ("", parent_head)

    # The parent's pin for child is at new_child_sha.
    pin = _git(["ls-tree", "HEAD", "child"], cwd=parent, env=git_env)
    assert pin.split()[2] == new_child_sha
