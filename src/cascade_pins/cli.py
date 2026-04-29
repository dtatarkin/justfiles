from __future__ import annotations

import argparse
import sys

from . import execute, graph
from . import plan as plan_mod


def _add_common(p: argparse.ArgumentParser, *, with_branch: bool = True) -> None:
    p.add_argument("--root", default=".", help="Walk from <path> instead of cwd.")
    if with_branch:
        p.add_argument(
            "--branch",
            default="main",
            help="Compare against this remote branch (default: main).",
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cascade-pins",
        description=(
            "Cascade nested-submodule pin bumps in topological order. "
            "Reads `git submodule status --recursive` to build a graph, "
            "then commits each parent's pin bumps deepest-first."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_plan = sub.add_parser("plan", help="Print the cascade plan; no side effects.")
    _add_common(p_plan)
    p_plan.add_argument("--no-uv-lock", action="store_true")

    p_run = sub.add_parser("run", help="Execute the cascade.")
    _add_common(p_run)
    p_run.add_argument("--push", action="store_true")
    p_run.add_argument("--no-uv-lock", action="store_true")
    p_run.add_argument("--dry-run", action="store_true")
    p_run.add_argument("--message", default=None)

    p_drift = sub.add_parser("drift", help="Report drift across same-name submodules.")
    _add_common(p_drift, with_branch=False)

    p_status = sub.add_parser("status", help="Show pinned vs. remote SHAs per node.")
    _add_common(p_status)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    handlers = {
        "plan": _cmd_plan,
        "run": _cmd_run,
        "drift": _cmd_drift,
        "status": _cmd_status,
    }
    return handlers[ns.cmd](ns)


def _cmd_plan(ns: argparse.Namespace) -> int:
    g = graph.build_graph(ns.root, branch=ns.branch)
    p = plan_mod.compute_plan(g)
    if not p.bumps:
        print("no bumps needed")
        return 0
    for parent_path, group in p.by_parent():
        label = parent_path or "."
        print(f"@ {label}")
        for bump in group:
            print(f"  {bump.child}: {bump.old_sha[:7]} -> {bump.new_sha[:7]}")
    return 0


def _cmd_run(ns: argparse.Namespace) -> int:
    g = graph.build_graph(ns.root, branch=ns.branch)
    p = plan_mod.compute_plan(g)
    if not p.bumps:
        print("no bumps needed")
        return 0
    if ns.dry_run:
        for parent_path, group in p.by_parent():
            label = parent_path or "."
            print(f"@ {label}")
            for bump in group:
                print(f"  {bump.child}: {bump.old_sha[:7]} -> {bump.new_sha[:7]}")
        return 0
    opts = execute.ExecuteOptions(
        push=ns.push,
        no_uv_lock=ns.no_uv_lock,
        dry_run=False,
        message=ns.message,
    )
    result = execute.execute_plan(p, g, opts)
    print(f"committed {len(result.committed)} parent(s)")
    for parent, sha in result.committed:
        label = parent or "."
        print(f"  {label} -> {sha[:7]}")
    if not ns.push:
        print("\nto push, run:")
        for parent, _ in result.committed:
            label = parent or "."
            print(f"  git -C {label} push")
    return 0


def _cmd_drift(ns: argparse.Namespace) -> int:
    g = graph.build_graph(ns.root, branch="main", fetch=False)
    drifty = graph.detect_drift(g)
    if not drifty:
        print("no drift")
        return 0
    print(f"drift detected ({len(drifty)} names)")
    for name, nodes in drifty.items():
        shas = sorted({n.pinned_sha for n in nodes})
        print(f"  {name}  ({len(shas)} SHAs)")
        for n in nodes:
            print(f"    {n.pinned_sha[:7]}  -> ./{n.path}/")
    return 1


def _cmd_status(ns: argparse.Namespace) -> int:
    g = graph.build_graph(ns.root, branch=ns.branch)
    for n in g.nodes:
        marker = "*" if n.remote_sha and n.pinned_sha != n.remote_sha else " "
        remote_disp = (n.remote_sha or "?")[:7]
        print(f"{marker} {n.path}: {n.pinned_sha[:7]} -> {remote_disp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
