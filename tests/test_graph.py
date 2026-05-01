from __future__ import annotations

from cascade_pins.graph import (
    Graph,
    Node,
    detect_drift,
    parse_submodule_status,
)

SAMPLE_RECURSIVE = """\
 8842d2110000000000000000000000000000000a parent-a (heads/main)
 11112222000000000000000000000000000000bb parent-a/lib-x (heads/main)
+22223333000000000000000000000000000000cc parent-a/lib-y (heads/main)
-33334444000000000000000000000000000000dd parent-b (heads/main)
 44445555000000000000000000000000000000ee parent-b/lib-x (heads/main)
"""


def test_parse_submodule_status_extracts_all_nodes() -> None:
    parsed = parse_submodule_status(SAMPLE_RECURSIVE)
    paths = [p.path for p in parsed]
    assert paths == [
        "parent-a",
        "parent-a/lib-x",
        "parent-a/lib-y",
        "parent-b",
        "parent-b/lib-x",
    ]


def test_parse_submodule_status_captures_flags() -> None:
    parsed = {p.path: p for p in parse_submodule_status(SAMPLE_RECURSIVE)}
    assert parsed["parent-a"].flag == " "
    assert parsed["parent-a/lib-y"].flag == "+"
    assert parsed["parent-b"].flag == "-"


def test_parse_submodule_status_handles_no_describe() -> None:
    text = " 8842d2110000000000000000000000000000000a some/path\n"
    parsed = parse_submodule_status(text)
    assert len(parsed) == 1
    assert parsed[0].path == "some/path"
    assert parsed[0].describe is None


def test_parse_submodule_status_skips_blank_and_garbage() -> None:
    text = "\nnot a submodule line\n 8842d2110000000000000000000000000000000a a (b)\n"
    parsed = parse_submodule_status(text)
    assert len(parsed) == 1
    assert parsed[0].path == "a"


def _node(
    path: str,
    pinned: str,
    parent: str | None = None,
    remote: str | None = None,
    local: str | None = None,
) -> Node:
    return Node(
        path=path,
        parent=parent,
        pinned_sha=pinned,
        remote_sha=remote if remote is not None else pinned,
        local_sha=local if local is not None else pinned,
        has_pyproject=False,
    )


def test_detect_drift_returns_groups_with_multiple_shas() -> None:
    g = Graph(
        root="/tmp/x",
        branch="main",
        nodes=(
            _node("parent-a", "aaa"),
            _node("parent-a/lib-x", "111", parent="parent-a"),
            _node("parent-b", "bbb"),
            _node("parent-b/lib-x", "222", parent="parent-b"),
        ),
    )
    drift = detect_drift(g)
    assert "lib-x" in drift
    assert {n.pinned_sha for n in drift["lib-x"]} == {"111", "222"}


def test_detect_drift_clean_graph_returns_empty() -> None:
    g = Graph(
        root="/tmp/x",
        branch="main",
        nodes=(
            _node("parent-a", "aaa"),
            _node("parent-a/lib", "111", parent="parent-a"),
            _node("parent-b", "bbb"),
            _node("parent-b/lib", "111", parent="parent-b"),
        ),
    )
    assert detect_drift(g) == {}
