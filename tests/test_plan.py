from __future__ import annotations

from cascade_pins.graph import Graph, Node
from cascade_pins.plan import compute_plan


def _node(
    path: str,
    pinned: str,
    remote: str,
    parent: str | None = None,
) -> Node:
    return Node(
        path=path,
        parent=parent,
        pinned_sha=pinned,
        remote_sha=remote,
        local_sha=remote,
        has_pyproject=False,
        remote_ahead=remote != pinned and bool(remote),
    )


def _graph(*nodes: Node) -> Graph:
    return Graph(root="/tmp/x", branch="main", nodes=nodes)


def test_linear_chain_orders_deepest_first() -> None:
    # umbrella -> beholder -> common  (all outdated)
    g = _graph(
        _node("beholder", pinned="aaa", remote="AAA"),
        _node(
            "beholder/common",
            pinned="bbb",
            remote="BBB",
            parent="beholder",
        ),
    )
    plan = compute_plan(g)
    parents = [b.parent for b in plan.bumps]
    # Deepest parent first: "beholder" (parent of common), then "" (root, parent of beholder).
    assert parents == ["beholder", ""]


def test_no_outdated_means_empty_plan() -> None:
    g = _graph(
        _node("beholder", pinned="aaa", remote="aaa"),
        _node("beholder/common", pinned="bbb", remote="bbb", parent="beholder"),
    )
    assert compute_plan(g).bumps == ()


def test_sibling_bumps_share_parent_and_are_grouped() -> None:
    g = _graph(
        _node("beholder", pinned="aaa", remote="aaa"),
        _node("beholder/lib1", pinned="11", remote="X1", parent="beholder"),
        _node("beholder/lib2", pinned="22", remote="X2", parent="beholder"),
    )
    plan = compute_plan(g)
    grouped = dict(plan.by_parent())
    # Two libs share parent "beholder" → one bundled commit at beholder.
    assert sorted(b.child for b in grouped["beholder"]) == [
        "beholder/lib1",
        "beholder/lib2",
    ]
    # And beholder itself gets propagated upward as a root bump.
    assert any(b.child == "beholder" for b in grouped[""])


def test_fanout_then_root_bump_orders_correctly() -> None:
    # umbrella has TWO outdated children, each has one outdated child of its own.
    g = _graph(
        _node("beholder", pinned="aaa", remote="AAA"),
        _node("backoffice", pinned="bbb", remote="BBB"),
        _node(
            "beholder/common",
            pinned="11",
            remote="X1",
            parent="beholder",
        ),
        _node(
            "backoffice/common",
            pinned="22",
            remote="X2",
            parent="backoffice",
        ),
    )
    plan = compute_plan(g)
    by_parent = plan.by_parent()
    # First two groups: beholder and backoffice (depth 1) in some order.
    # Last group: "" (root, depth 0).
    assert by_parent[-1][0] == ""
    assert {by_parent[0][0], by_parent[1][0]} == {"beholder", "backoffice"}


def test_bump_carries_old_and_new_sha() -> None:
    g = _graph(
        _node("lib", pinned="ababab", remote="cdcdcd"),
    )
    plan = compute_plan(g)
    assert len(plan.bumps) == 1
    bump = plan.bumps[0]
    assert bump.parent == ""
    assert bump.child == "lib"
    assert bump.old_sha == "ababab"
    assert bump.new_sha == "cdcdcd"
