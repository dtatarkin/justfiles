#!/usr/bin/env python3
"""Fail if AGENTS.md and CLAUDE.md do not appear as a pair.

Some agent tools auto-load ``CLAUDE.md`` (at the root and in nested
directories) but never ``AGENTS.md``; others read ``AGENTS.md`` but ignore
``CLAUDE.md``. To keep one set of instructions visible to every tool, each
directory that carries one of the two files must also carry the other --
typically as a one-line ``@AGENTS.md`` import stub (or a symlink).

This script walks the working tree, descending into submodule checkouts, and
reports any directory that contains exactly one of the two files. Intentional
single-file directories can be exempted by path prefix.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Iterator
from pathlib import Path

#: Directory names never worth descending into when looking for the pair.
PRUNE_NAMES = {"node_modules", "__pycache__"}


def _should_prune(name: str) -> bool:
    """Whether a directory entry should be skipped during the walk."""
    return name.startswith(".") or name in PRUNE_NAMES or name.endswith(".egg-info")


def _walk(root: Path) -> Iterator[Path]:
    """Yield every directory under ``root``, pruning vendored/hidden trees."""
    for dirpath, dirnames, _filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not _should_prune(d)]
        yield Path(dirpath)


def find_violations(root: Path, exempt: list[str]) -> list[str]:
    """Return human-readable messages for each unpaired directory."""
    exempt_paths = [(root / e).resolve() for e in exempt]
    violations: list[str] = []
    for dirpath in _walk(root):
        has_agents = (dirpath / "AGENTS.md").exists()
        has_claude = (dirpath / "CLAUDE.md").exists()
        if has_agents == has_claude:
            continue
        resolved = dirpath.resolve()
        if any(resolved == e or e in resolved.parents for e in exempt_paths):
            continue
        present, missing = (
            ("AGENTS.md", "CLAUDE.md") if has_agents else ("CLAUDE.md", "AGENTS.md")
        )
        violations.append(f"{dirpath.relative_to(root)}/: has {present} but not {missing}")
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Directory to scan (default: current working directory).",
    )
    parser.add_argument(
        "--exempt",
        action="append",
        default=[],
        metavar="DIR",
        help="Path prefix (relative to --root) to skip; repeatable.",
    )
    args = parser.parse_args(argv)

    violations = find_violations(args.root, args.exempt)
    if not violations:
        return 0

    print("AGENTS.md / CLAUDE.md pairing check failed:", file=sys.stderr)
    for violation in violations:
        print(f"  {violation}", file=sys.stderr)
    print(
        "\nEvery directory that carries one of these files must carry the other "
        "(CLAUDE.md\nis usually a one-line `@AGENTS.md` import stub) so every "
        "agent tool sees the same\ninstructions. Exempt intentional single-file "
        "directories with --exempt.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
