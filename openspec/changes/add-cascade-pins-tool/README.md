# add-cascade-pins-tool

Introduce a Python tool, `cascade-pins`, that automates the recursive submodule pin cascade — the rote ritual of "subrepo pushed → fast-forward consumer's nested checkout → re-lock uv → commit pin bump → push consumer → cascade up." The tool walks the recursive submodule graph from any node, computes outdated pins, executes them in topological (deepest-first) order, optionally pushes, and runs a structured drift check at the end.

This change also establishes `justfiles`'s own OpenSpec root (its first), bootstrapping `openspec/config.yaml` and `openspec/project.md` alongside the new capability spec.
