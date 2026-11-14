import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[2] / "scripts" / "worktree_prepare.py"
PYPROJECT = """\
[tool.uv.workspace]
members = ["../lib", "../libs/*", "inside"]

[tool.uv.sources]
lib = { workspace = true }
tool = { path = "../tool" }
"""


def git(cwd: Path, *args: str) -> None:
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@t",
            "-c",
            "protocol.file.allow=always",
            *args,
        ],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


def prepare(worktree: Path, *paths: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *paths],
        cwd=worktree,
        capture_output=True,
        text=True,
        check=False,
    )


def repository(path: Path) -> Path:
    path.mkdir(parents=True)
    git(path, "init", "-q", "-b", "main")
    (path / "pyproject.toml").write_text(PYPROJECT)
    (path / ".gitignore").write_text(".env\n")
    git(path, "add", ".")
    git(path, "commit", "-q", "-m", "init")
    (path / ".env").write_text("A=1\n")
    for sibling in ("lib", "libs", "tool"):
        (path.parent / sibling).mkdir(exist_ok=True)
    return path


def check_linked(main: Path, worktree: Path) -> None:
    for relative in ("../lib", "../libs", "../tool", ".env"):
        link = Path(os.path.normpath(worktree / relative))
        assert link.is_symlink()
        assert link.readlink() == Path(os.path.normpath(main / relative))
    assert not (worktree.parent / "inside").exists()


@pytest.fixture
def lane(tmp_path: Path) -> tuple[Path, Path]:
    main = repository(tmp_path / "repo")
    worktree = tmp_path / "repo.lanes" / "lane"
    git(main, "worktree", "add", "-q", "--detach", str(worktree))
    return main, worktree


class TestWorktreePrepare:
    def test_links_the_workspace_siblings_and_the_paths_named(
        self, lane: tuple[Path, Path]
    ) -> None:
        main, worktree = lane

        result = prepare(worktree, ".env")

        assert result.returncode == 0, result.stderr
        check_linked(main, worktree)

    def test_a_second_run_keeps_every_path(self, lane: tuple[Path, Path]) -> None:
        _, worktree = lane
        prepare(worktree, ".env")

        result = prepare(worktree, ".env")

        assert result.returncode == 0
        assert all(line.startswith("kept ") for line in result.stdout.splitlines())

    def test_a_path_the_main_checkout_lacks_fails_the_run(self, lane: tuple[Path, Path]) -> None:
        _, worktree = lane

        result = prepare(worktree, ".absent", ".env")

        assert result.returncode == 1
        assert "missing .absent" in result.stderr
        assert (worktree / ".env").is_symlink()

    def test_finds_a_submodule_checkout_through_its_superproject(self, tmp_path: Path) -> None:
        upstream = repository(tmp_path / "upstream" / "repo")
        superproject = tmp_path / "super"
        superproject.mkdir()
        git(superproject, "init", "-q", "-b", "main")
        git(superproject, "submodule", "add", "-q", str(upstream), "repo")
        main = superproject / "repo"
        (main / ".env").write_text("A=1\n")
        for sibling in ("lib", "libs", "tool"):
            (superproject / sibling).mkdir()
        worktree = superproject / "repo.lanes" / "lane"
        git(main, "worktree", "add", "-q", "--detach", str(worktree))

        result = prepare(worktree, ".env")

        assert result.returncode == 0, result.stderr
        check_linked(main, worktree)
