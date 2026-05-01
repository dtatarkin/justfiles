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
    # root -> parent-a -> common  (all outdated)
    g = _graph(
        _node("parent-a", pinned="aaa", remote="AAA"),
        _node(
            "parent-a/common",
            pinned="bbb",
            remote="BBB",
            parent="parent-a",
        ),
    )
    plan = compute_plan(g)
    parents = [b.parent for b in plan.bumps]
    # Deepest parent first: "parent-a" (parent of common), then "" (root, parent of parent-a).
    assert parents == ["parent-a", ""]


def test_no_outdated_means_empty_plan() -> None:
    g = _graph(
        _node("parent-a", pinned="aaa", remote="aaa"),
        _node("parent-a/common", pinned="bbb", remote="bbb", parent="parent-a"),
    )
    assert compute_plan(g).bumps == ()


def test_sibling_bumps_share_parent_and_are_grouped() -> None:
    g = _graph(
        _node("parent-a", pinned="aaa", remote="aaa"),
        _node("parent-a/lib1", pinned="11", remote="X1", parent="parent-a"),
        _node("parent-a/lib2", pinned="22", remote="X2", parent="parent-a"),
    )
    plan = compute_plan(g)
    grouped = dict(plan.by_parent())
    # Two libs share parent "parent-a" → one bundled commit at parent-a.
    assert sorted(b.child for b in grouped["parent-a"]) == [
        "parent-a/lib1",
        "parent-a/lib2",
    ]
    # And parent-a itself gets propagated upward as a root bump.
    assert any(b.child == "parent-a" for b in grouped[""])


def test_fanout_then_root_bump_orders_correctly() -> None:
    # root has TWO outdated children, each has one outdated child of its own.
    g = _graph(
        _node("parent-a", pinned="aaa", remote="AAA"),
        _node("parent-b", pinned="bbb", remote="BBB"),
        _node(
            "parent-a/common",
            pinned="11",
            remote="X1",
            parent="parent-a",
        ),
        _node(
            "parent-b/common",
            pinned="22",
            remote="X2",
            parent="parent-b",
        ),
    )
    plan = compute_plan(g)
    by_parent = plan.by_parent()
    # First two groups: parent-a and parent-b (depth 1) in some order.
    # Last group: "" (root, depth 0).
    assert by_parent[-1][0] == ""
    assert {by_parent[0][0], by_parent[1][0]} == {"parent-a", "parent-b"}


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
