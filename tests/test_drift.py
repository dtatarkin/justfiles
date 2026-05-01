from __future__ import annotations

from cascade_pins.cli import main
from cascade_pins.graph import Graph, Node


def _node(path: str, pinned: str, parent: str | None = None) -> Node:
    return Node(
        path=path,
        parent=parent,
        pinned_sha=pinned,
        remote_sha=pinned,
        local_sha=pinned,
        has_pyproject=False,
    )


def test_drift_command_exits_nonzero_on_drift(monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    drift_graph = Graph(
        root="/tmp/x",
        branch="main",
        nodes=(
            _node("parent-a", "aaa"),
            _node("parent-a/common", "111", parent="parent-a"),
            _node("parent-b", "bbb"),
            _node("parent-b/common", "222", parent="parent-b"),
        ),
    )

    from cascade_pins import graph as graph_mod

    monkeypatch.setattr(graph_mod, "build_graph", lambda *a, **k: drift_graph)
    from cascade_pins import cli as cli_mod

    monkeypatch.setattr(cli_mod, "graph", graph_mod)

    rc = main(["drift", "--root", "."])
    captured = capsys.readouterr()
    assert rc != 0
    assert "drift detected" in captured.out
    assert "common" in captured.out


def test_drift_command_exits_zero_when_clean(monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    clean_graph = Graph(
        root="/tmp/x",
        branch="main",
        nodes=(
            _node("parent-a", "aaa"),
            _node("parent-a/lib", "111", parent="parent-a"),
            _node("parent-b", "bbb"),
            _node("parent-b/lib", "111", parent="parent-b"),
        ),
    )
    from cascade_pins import graph as graph_mod

    monkeypatch.setattr(graph_mod, "build_graph", lambda *a, **k: clean_graph)
    from cascade_pins import cli as cli_mod

    monkeypatch.setattr(cli_mod, "graph", graph_mod)

    rc = main(["drift", "--root", "."])
    captured = capsys.readouterr()
    assert rc == 0
    assert "no drift" in captured.out
