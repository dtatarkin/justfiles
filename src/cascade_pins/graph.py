import re
from dataclasses import dataclass
from pathlib import Path

from . import git_ops

_STATUS_LINE_RE = re.compile(
    r"^(?P<flag>[ +\-U])(?P<sha>[0-9a-f]{40}) (?P<path>.+?)(?: \((?P<describe>.+)\))?$"
)


@dataclass(frozen=True)
class ParsedNode:
    flag: str
    pinned_sha: str
    path: str
    describe: str | None


def parse_submodule_status(text: str) -> list[ParsedNode]:
    nodes: list[ParsedNode] = []
    for raw in text.splitlines():
        m = _STATUS_LINE_RE.match(raw)
        if not m:
            continue
        nodes.append(
            ParsedNode(
                flag=m.group("flag"),
                pinned_sha=m.group("sha"),
                path=m.group("path"),
                describe=m.group("describe"),
            )
        )
    return nodes


@dataclass(frozen=True)
class Node:
    path: str
    parent: str | None
    pinned_sha: str
    remote_sha: str
    local_sha: str
    has_pyproject: bool
    remote_ahead: bool = False


@dataclass(frozen=True)
class Graph:
    root: str
    branch: str
    nodes: tuple[Node, ...]

    def by_path(self) -> dict[str, Node]:
        return {n.path: n for n in self.nodes}

    def children_of(self, path: str | None) -> list[Node]:
        return [n for n in self.nodes if n.parent == path]


def _parent_of(path: str, all_paths: set[str]) -> str | None:
    candidates = [p for p in all_paths if p != path and path.startswith(p + "/")]
    if not candidates:
        return None
    return max(candidates, key=lambda p: len(p))


def build_graph(
    root: str | Path,
    branch: str = "main",
    *,
    fetch: bool = True,
) -> Graph:
    root_abs = str(Path(root).resolve())
    raw = git_ops.submodule_status_recursive(root_abs)
    parsed = parse_submodule_status(raw)
    paths = {p.path for p in parsed if p.flag != "-"}
    nodes: list[Node] = []
    for p in parsed:
        if p.flag == "-":
            continue
        node_dir = str(Path(root_abs) / p.path)
        if fetch:
            git_ops.fetch(node_dir)
        try:
            remote = git_ops.rev_parse(node_dir, f"origin/{branch}")
        except git_ops.GitError:
            remote = ""
        try:
            local = git_ops.rev_parse(node_dir, "HEAD")
        except git_ops.GitError:
            local = p.pinned_sha
        remote_ahead = False
        if remote and remote != p.pinned_sha:
            r = git_ops.run_git(
                node_dir,
                "merge-base",
                "--is-ancestor",
                p.pinned_sha,
                remote,
                check=False,
            )
            remote_ahead = r.returncode == 0
        nodes.append(
            Node(
                path=p.path,
                parent=_parent_of(p.path, paths),
                pinned_sha=p.pinned_sha,
                remote_sha=remote,
                local_sha=local,
                has_pyproject=(Path(node_dir) / "pyproject.toml").is_file(),
                remote_ahead=remote_ahead,
            )
        )
    return Graph(root=root_abs, branch=branch, nodes=tuple(nodes))


def basename(path: str) -> str:
    return path.rsplit("/", 1)[-1]


def detect_drift(graph: Graph) -> dict[str, list[Node]]:
    by_name: dict[str, list[Node]] = {}
    for node in graph.nodes:
        by_name.setdefault(basename(node.path), []).append(node)
    drifty: dict[str, list[Node]] = {}
    for name, nodes in by_name.items():
        if len({n.pinned_sha for n in nodes}) > 1:
            drifty[name] = nodes
    return drifty
