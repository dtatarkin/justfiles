import subprocess
import sys
from pathlib import Path

import pytest

MODULE = Path(__file__).parents[1] / "git.just"
JUST = Path(sys.executable).parent / "just"


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def just(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(JUST), "--justfile", str(MODULE), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def remote_head(main: Path, remote: str, branch: str) -> None:
    """Record what a clone from `remote` would: its branch and its HEAD naming it."""
    git(main, "update-ref", f"refs/remotes/{remote}/{branch}", branch)
    git(main, "symbolic-ref", f"refs/remotes/{remote}/HEAD", f"refs/remotes/{remote}/{branch}")


@pytest.fixture
def main(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    git(path, "init", "-q", "-b", "main")
    git(path, "commit", "-q", "--allow-empty", "-m", "init")
    git(path, "branch", "other")
    return path


def lane(main: Path) -> Path:
    added = just(main, "worktree-add", "lane", "main", "-b", "lane")
    assert added.returncode == 0, added.stderr
    worktree = main.parent / "repo.lanes" / "lane"
    git(worktree, "commit", "-q", "--allow-empty", "-m", "work")
    return worktree


def landed(main: Path, worktree: Path) -> bool:
    return git(main, "log", "-1", "--format=%s", "main") == "work" and not worktree.exists()


class TestWorktreeLand:
    def test_lands_on_the_one_branch_the_remotes_name(self, main: Path) -> None:
        remote_head(main, "origin", "main")
        worktree = lane(main)
        result = just(main, "worktree-land", "lane")
        assert result.returncode == 0, result.stderr
        assert landed(main, worktree)

    def test_lands_on_the_checkout_branch_without_a_remote_head(self, main: Path) -> None:
        worktree = lane(main)
        result = just(main, "worktree-land", "lane")
        assert result.returncode == 0, result.stderr
        assert landed(main, worktree)

    def test_disagreeing_remotes_defer_to_the_checkout_branch(self, main: Path) -> None:
        remote_head(main, "aws", "other")
        remote_head(main, "bitbucket", "main")
        worktree = lane(main)
        result = just(main, "worktree-land", "lane")
        assert result.returncode == 0, result.stderr
        assert landed(main, worktree)

    def test_disagreeing_remotes_refuse_a_checkout_on_neither(self, main: Path) -> None:
        remote_head(main, "aws", "other")
        remote_head(main, "bitbucket", "main")
        worktree = lane(main)
        git(main, "switch", "-q", "-c", "elsewhere")
        result = just(main, "worktree-land", "lane")
        assert result.returncode == 1
        assert "remotes disagree" in result.stderr
        assert "aws/HEAD -> other" in result.stderr
        assert "bitbucket/HEAD -> main" in result.stderr
        assert worktree.exists()

    def test_a_single_remote_head_still_refuses_another_branch(self, main: Path) -> None:
        remote_head(main, "origin", "main")
        worktree = lane(main)
        git(main, "switch", "-q", "other")
        result = just(main, "worktree-land", "lane")
        assert result.returncode == 1
        assert "on main" in result.stderr
        assert worktree.exists()
