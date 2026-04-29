# Project context

`justfiles` is a shared library of `just` recipe modules consumed by every repository in the kit-style ecosystem. It started as a recipe-only repo (modules for `git`, `git-submodule`, `just`, `pre-commit`, `uv-workspace`) and is growing to host Python entry points for tasks where bash ergonomics break down — graph algorithms, structured subprocess handling, multi-line commit-message templating.

## Role and properties

- **Library tier — general-purpose.** No consumer-specific knowledge. No NATS subjects, no project identifiers, no business rules.
- **Vendored, not published.** Consumers add this as a git submodule and either `mod`-import recipe modules into their `justfile`, or invoke Python entry points via `uv run`.
- **OpenSpec-driven.** All non-trivial changes go through proposal → design → specs → tasks.

## Conventions

- **Distribution**: name `justfiles`, distributed only as a git submodule.
- **Tooling**: `uv`, `hatchling` (or `uv_build` — the existing pyproject's choice stands), `ruff`, `mypy` (strict), `pre-commit`.
- **Layout**: `src/`-layout for Python entry points (introduced as needed). Recipe modules (`*.just`) live at the repository root for `mod`-import compatibility.

## Independence

This repository does not reference any parent project, sibling consumer, or specific application of the recipes. References to general-purpose tools (`git`, `uv`, `just`, `hatchling`, `pre-commit`) are permitted and expected.
