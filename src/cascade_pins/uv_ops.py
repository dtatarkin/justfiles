import subprocess
from dataclasses import dataclass
from pathlib import Path


class UvError(RuntimeError):
    def __init__(self, cmd: list[str], returncode: int, stdout: str, stderr: str) -> None:
        self.cmd = cmd
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        super().__init__(f"{' '.join(cmd)} exited {returncode}: {stderr.strip() or stdout.strip()}")


@dataclass(frozen=True)
class UvResult:
    stdout: str
    stderr: str
    returncode: int


def run_uv(cwd: str | Path, *args: str, check: bool = True) -> UvResult:
    cmd = ["uv", *args]
    proc = subprocess.run(  # noqa: S603, S607
        cmd, capture_output=True, text=True, cwd=str(cwd), check=False
    )
    if check and proc.returncode != 0:
        raise UvError(cmd, proc.returncode, proc.stdout, proc.stderr)
    return UvResult(stdout=proc.stdout, stderr=proc.stderr, returncode=proc.returncode)


def lock(cwd: str | Path) -> UvResult:
    return run_uv(cwd, "lock")
