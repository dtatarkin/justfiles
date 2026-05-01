from dataclasses import dataclass

from .graph import Graph, Node


@dataclass(frozen=True)
class Bump:
    parent: str  # "" for graph root
    child: str  # path relative to graph root
    old_sha: str
    new_sha: str


@dataclass(frozen=True)
class Plan:
    root: str
    bumps: tuple[Bump, ...]

    def by_parent(self) -> list[tuple[str, list[Bump]]]:
        groups: list[tuple[str, list[Bump]]] = []
        for bump in self.bumps:
            if groups and groups[-1][0] == bump.parent:
                groups[-1][1].append(bump)
            else:
                groups.append((bump.parent, [bump]))
        return groups


def _depth(parent_path: str, by_path: dict[str, Node]) -> int:
    if not parent_path:
        return 0
    if parent_path not in by_path:
        return 0
    n: Node = by_path[parent_path]
    d = 1
    while n.parent is not None:
        n = by_path[n.parent]
        d += 1
    return d


def compute_plan(graph: Graph) -> Plan:
    by_path = graph.by_path()

    # Step 1: identify nodes whose pinned SHA is strictly behind origin's branch
    # head (remote_ahead=True). Direct bumps; new_sha is known from graph state.
    outdated: dict[str, str] = {}
    for node in graph.nodes:
        if node.remote_ahead:
            outdated[node.path] = node.remote_sha

    # Step 2: propagate upward. If any child of node N is in outdated, then N's
    # commit will move N's HEAD, and N's parent (if any) must bump N. The
    # post-bump SHA of N is unknown at plan time — execute resolves it.
    changed = True
    while changed:
        changed = False
        for node in graph.nodes:
            if node.path in outdated:
                continue
            for child in graph.children_of(node.path):
                if child.path in outdated:
                    outdated[node.path] = ""
                    changed = True
                    break

    bumps: list[Bump] = []
    for path, new_sha in outdated.items():
        node = by_path[path]
        bumps.append(
            Bump(
                parent=node.parent or "",
                child=node.path,
                old_sha=node.pinned_sha,
                new_sha=new_sha,
            )
        )
    bumps.sort(key=lambda b: (-_depth(b.parent, by_path), b.parent, b.child))
    return Plan(root=graph.root, bumps=tuple(bumps))
