from pathlib import Path

import pytest

from cascade_pins import messages as messages_mod
from cascade_pins.messages import render_commit_message
from cascade_pins.plan import Bump


class _Stub:
    subjects: dict[tuple[str, str, str], list[str]]
    archives: dict[tuple[str, str, str], list[str]]


@pytest.fixture
def stub(monkeypatch: pytest.MonkeyPatch) -> _Stub:
    """Replace _subjects_between and _archived_changes by patchable doubles."""
    s = _Stub()
    s.subjects = {}
    s.archives = {}

    def fake_subjects(child_dir: Path, old: str, new: str) -> list[str]:
        return s.subjects.get((str(child_dir), old, new), [])

    def fake_archives(child_dir: Path, old: str, new: str) -> list[str]:
        return s.archives.get((str(child_dir), old, new), [])

    monkeypatch.setattr(messages_mod, "_subjects_between", fake_subjects)
    monkeypatch.setattr(messages_mod, "_archived_changes", fake_archives)
    return s


def test_single_bump_with_subjects_and_archives(stub: _Stub) -> None:
    stub.subjects = {
        ("/tmp/g/parent-a/common", "aaaaaaaaa", "bbbbbbbbb"): [
            "Add new feature",
            "Fix bug",
        ]
    }
    stub.archives = {
        ("/tmp/g/parent-a/common", "aaaaaaaaa", "bbbbbbbbb"): [
            "change-A",
            "change-B",
        ]
    }
    bumps = [
        Bump(
            parent="parent-a",
            child="parent-a/common",
            old_sha="aaaaaaaaa",
            new_sha="bbbbbbbbb",
        )
    ]
    msg = render_commit_message("/tmp/g", bumps)
    assert msg.startswith("Bump common pins\n")
    assert "common @ aaaaaaa..bbbbbbb" in msg
    assert "  Add new feature" in msg
    assert "  Fix bug" in msg
    assert "  (archived: change-A, change-B)" in msg


def test_multi_subrepo_bump_lists_each_child(stub: _Stub) -> None:
    bumps = [
        Bump(
            parent="root",
            child="root/lib1",
            old_sha="aaaaaaa",
            new_sha="bbbbbbb",
        ),
        Bump(
            parent="root",
            child="root/lib2",
            old_sha="ccccccc",
            new_sha="ddddddd",
        ),
    ]
    msg = render_commit_message("/tmp/g", bumps)
    assert msg.startswith("Bump lib1, lib2 pins\n")
    assert "lib1 @ aaaaaaa..bbbbbbb" in msg
    assert "lib2 @ ccccccc..ddddddd" in msg


def test_no_archives_omits_archived_section(stub: _Stub) -> None:
    stub.subjects = {("/tmp/g/lib", "aaa", "bbb"): ["Open change-X proposal"]}
    stub.archives = {("/tmp/g/lib", "aaa", "bbb"): []}
    bumps = [Bump(parent="", child="lib", old_sha="aaa", new_sha="bbb")]
    msg = render_commit_message("/tmp/g", bumps)
    assert "(archived:" not in msg
    assert "  Open change-X proposal" in msg


def test_summary_appended_to_first_line(stub: _Stub) -> None:
    bumps = [Bump(parent="", child="lib", old_sha="aaa", new_sha="bbb")]
    msg = render_commit_message("/tmp/g", bumps, summary="post-archive cascade")
    first = msg.splitlines()[0]
    assert first == "Bump lib pins: post-archive cascade"


def test_empty_bumps_raises() -> None:
    with pytest.raises(ValueError):
        render_commit_message("/tmp/g", [])
