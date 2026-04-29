from __future__ import annotations

from cascade_pins.graph import (
    Graph,
    Node,
    detect_drift,
    parse_submodule_status,
)

SAMPLE_RECURSIVE = """\
 8842d2110000000000000000000000000000000a beholder (heads/main)
 11112222000000000000000000000000000000bb beholder/comprehender-common (heads/main)
+22223333000000000000000000000000000000cc beholder/mtproto-kit (heads/main)
-33334444000000000000000000000000000000dd backoffice (heads/main)
 44445555000000000000000000000000000000ee backoffice/comprehender-common (heads/main)
"""


def test_parse_submodule_status_extracts_all_nodes() -> None:
    parsed = parse_submodule_status(SAMPLE_RECURSIVE)
    paths = [p.path for p in parsed]
    assert paths == [
        "beholder",
        "beholder/comprehender-common",
        "beholder/mtproto-kit",
        "backoffice",
        "backoffice/comprehender-common",
    ]


def test_parse_submodule_status_captures_flags() -> None:
    parsed = {p.path: p for p in parse_submodule_status(SAMPLE_RECURSIVE)}
    assert parsed["beholder"].flag == " "
    assert parsed["beholder/mtproto-kit"].flag == "+"
    assert parsed["backoffice"].flag == "-"


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
            _node("beholder", "aaa"),
            _node("beholder/comprehender-common", "111", parent="beholder"),
            _node("backoffice", "bbb"),
            _node("backoffice/comprehender-common", "222", parent="backoffice"),
        ),
    )
    drift = detect_drift(g)
    assert "comprehender-common" in drift
    assert {n.pinned_sha for n in drift["comprehender-common"]} == {"111", "222"}


def test_detect_drift_clean_graph_returns_empty() -> None:
    g = Graph(
        root="/tmp/x",
        branch="main",
        nodes=(
            _node("beholder", "aaa"),
            _node("beholder/lib", "111", parent="beholder"),
            _node("backoffice", "bbb"),
            _node("backoffice/lib", "111", parent="backoffice"),
        ),
    )
    assert detect_drift(g) == {}
