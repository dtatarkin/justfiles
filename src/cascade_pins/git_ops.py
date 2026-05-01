import subprocess
from dataclasses import dataclass
from pathlib import Path


class GitError(RuntimeError):
    def __init__(self, cmd: list[str], returncode: int, stdout: str, stderr: str) -> None:
        self.cmd = cmd
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        super().__init__(f"{' '.join(cmd)} exited {returncode}: {stderr.strip() or stdout.strip()}")


@dataclass(frozen=True)
class GitResult:
    stdout: str
    stderr: str
    returncode: int


def run_git(cwd: str | Path, *args: str, check: bool = True) -> GitResult:
    cmd = ["git", "-C", str(cwd), *args]
    proc = subprocess.run(  # noqa: S603
        cmd, capture_output=True, text=True, check=False
    )
    if check and proc.returncode != 0:
        raise GitError(cmd, proc.returncode, proc.stdout, proc.stderr)
    return GitResult(stdout=proc.stdout, stderr=proc.stderr, returncode=proc.returncode)


def submodule_status_recursive(root: str | Path) -> str:
    return run_git(root, "submodule", "status", "--recursive").stdout


def rev_parse(repo: str | Path, ref: str) -> str:
    return run_git(repo, "rev-parse", ref).stdout.strip()


def fetch(repo: str | Path, *, quiet: bool = True) -> None:
    args = ["fetch"]
    if quiet:
        args.append("--quiet")
    run_git(repo, *args, check=False)
