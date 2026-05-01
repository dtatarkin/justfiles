## 1. OpenSpec scaffolding

- [x] 1.1 Confirm `openspec/config.yaml` exists with a `schema: spec-driven` line and a `context:` block describing `justfiles`'s role. (Authored as part of this change.)
- [x] 1.2 Confirm `openspec/project.md` exists and describes the repo's role, conventions, and independence rule.
- [x] 1.3 Confirm `openspec/changes/` and `openspec/specs/` directories exist (the latter empty until this change archives).

## 2. pyproject.toml updates

- [x] 2.1 Add a `[project.scripts]` table (or extend the existing one) with `cascade-pins = "cascade_pins.cli:main"`.
- [x] 2.2 Confirm the build backend's `packages` (or equivalent) source list includes `src/cascade_pins`. If the existing pyproject does not yet declare a `src/`-layout, add it now.
- [x] 2.3 Add a `dev` dependency on `pytest` and (optionally) `pytest-cov` if not already present.
- [x] 2.4 Add a runtime dependency on `typer` (or `click`) for the CLI; or use `argparse` from stdlib (decide in design.md). If using stdlib, no new dependency. *(Chose `argparse` from stdlib — no new runtime dependency.)*

## 3. Source modules — implement

- [x] 3.1 `src/cascade_pins/__init__.py` exposing `main` from `cli.py`.
- [x] 3.2 `src/cascade_pins/cli.py` with subcommands `plan`, `run`, `drift`, `status`. `run` accepts `--push`, `--no-uv-lock`, `--branch`, `--root`, `--dry-run`, `--message`.
- [x] 3.3 `src/cascade_pins/graph.py` parsing `git submodule status --recursive` and per-node `git rev-parse origin/<branch>` into a typed `Graph` data class with `nodes: list[Node]`, where `Node` carries `path`, `parent`, `pinned_sha`, `remote_sha`, `has_pyproject: bool`.
- [x] 3.4 `src/cascade_pins/plan.py` computing `Plan = list[Bump]` in topological (deepest-first) order, where `Bump` carries `(parent, child, old_sha, new_sha)` plus a `bundle_with` reference for sibling-bumps that share a parent commit. *(Bundling exposed via `Plan.by_parent()` rather than a per-Bump reference field; semantics equivalent.)*
- [x] 3.5 `src/cascade_pins/execute.py` running a plan: per parent, fetch+ff each bumped child, run `uv lock` if `has_pyproject`, conditionally stage `uv.lock`, stage submodule pointers, commit with templated message, push if `--push`. Bails on uv-lock conflicts and push rejections without rolling back prior commits in the run.
- [x] 3.6 `src/cascade_pins/git_ops.py` and `src/cascade_pins/uv_ops.py` — subprocess helpers wrapping `git` and `uv` invocations with structured `CompletedProcess` results, surfacing nonzero exits via typed exceptions.
- [x] 3.7 `src/cascade_pins/messages.py` — multi-line commit-message templating per design.md D5; reads `git log <old>..<new> --pretty=%s` from the bumped child and (best-effort) the child's `openspec/changes/archive/` directory listing to find newly-archived changes.

## 4. Tests

- [x] 4.1 `tests/test_graph.py` — parse synthetic `git submodule status --recursive` strings; assert correct `Graph` shape; cover edge cases (newly-uninitialised submodules with `-` prefix; modified submodules with `+` prefix; recursion depth ≥ 2).
- [x] 4.2 `tests/test_plan.py` — toposort over fixture graphs (linear, fan-out, fan-in); assert deepest-first ordering; assert sibling-bumps are bundled per parent.
- [x] 4.3 `tests/test_messages.py` — snapshot tests of templated commit messages for: single-subrepo bump with N upstream commits and M archived changes; multi-subrepo bump; bump with no upstream commits (no-op edge case).
- [x] 4.4 `tests/test_execute_e2e.py` — integration test with a tmp-dir fixture: `git init --bare` for three remote repos; `git clone` + `git submodule add` chain to wire grandparent → parent → child; commit changes in `child`; run `cascade-pins run`; assert parent and grandparent receive correct commits with correct SHAs and `uv.lock` files (where applicable). Use `pytest`'s `tmp_path` fixture. *(uv.lock branch covered by unit tests; e2e uses `no_uv_lock=True` to keep the test offline-safe.)*
- [x] 4.5 `tests/test_drift.py` — fixture graph with intentional drift (same-named submodule at two different SHAs); assert `cascade-pins drift` reports it and exits nonzero.

## 5. cascade.just (shared recipe module)

- [x] 5.1 Author `cascade.just` exposing recipes per design.md D8: `cascade-plan`, `cascade *args`, `cascade-push`, `check-drift`. Each invokes `uv tool run --with file://{{ source_dir }}/.. cascade-pins ...`. *(Used `{{ source_dir }}` directly — `parent_directory(source_file())` resolves to `justfiles/` itself when consumers `mod`-import via `'justfiles/cascade.just'`.)*
- [x] 5.2 Document the wrapper recipe's first-invocation cost (uv tool builds; subsequent runs are cached) in a comment above each recipe.
- [x] 5.3 Confirm consumers can `mod cascade 'justfiles/cascade.just'` without conflict against existing `mod git`, `mod git-submodule`, etc.

## 6. Validation

- [x] 6.1 `openspec validate add-cascade-pins-tool --strict` passes.
- [x] 6.2 `openspec list` shows `add-cascade-pins-tool` as the sole active change.
- [x] 6.3 `pytest -q` passes; integration test runs in under 30 seconds. *(19 tests pass; e2e test runs in ~1s.)*
- [x] 6.4 `ruff check` and `ruff format --check` pass on `src/cascade_pins/` and `tests/`.
- [x] 6.5 `mypy --strict src/cascade_pins/` passes.
- [x] 6.6 Smoke test: `uv run cascade-pins plan --root .` against a consumer's working tree exits 0 and produces a graph view (no bumps if the tree is up-to-date). *(`justfiles` has no submodules; tool prints "no bumps needed" and exits 0.)*

## 7. Commit and push

- [x] 7.1 Stage the openspec scaffolding (`openspec/config.yaml`, `openspec/project.md`), the change directory, the source under `src/cascade_pins/`, the tests, the new `cascade.just`, and the `pyproject.toml` updates. *(Scaffolding shipped in `ef1f987`; implementation in `1fc5bd5`.)*
- [x] 7.2 Single commit on `main` titled `Open and ship add-cascade-pins-tool` (or split into two: a bootstrap-openspec commit and a feature commit, if that aids review). *(Split into two: `ef1f987` opens + bootstraps OpenSpec; `1fc5bd5` ships the implementation.)*
- [x] 7.3 DO NOT PUSH. Operator confirms before pushing. *(Honored — branch is ahead of origin/main by 2 commits, awaiting operator confirmation.)*

## 8. Archive

- [ ] 8.1 After consumer adoption (see §9 below) and at least one successful end-to-end cascade via `cascade-pins`, archive: `openspec archive add-cascade-pins-tool`. The `cascade-pins` capability is promoted into `openspec/specs/`.

## 9. Consumer adoption (NOT in this change)

These tasks belong to follow-on changes in each consumer's OpenSpec root. Listed here for visibility only.

- [ ] 9.1 (root consumer) Replace any existing `just check-drift` body with a delegation to `cascade-pins drift`. Spec amendment to the consumer's repository-structure spec if the requirement names the tool.
- [ ] 9.2 (root consumer) Add `mod cascade 'justfiles/cascade.just'`. Optional `init` recipe extension to pre-warm `uv tool` cache for `cascade-pins`.
- [ ] 9.3 (intermediate parents) Add `mod cascade 'justfiles/cascade.just'` for symmetric local cascade orchestration. Optional.
- [ ] 9.4 (justfiles itself) Decide whether to retire awk-based `check-drift` recipes in favour of `cascade-pins drift` as the canonical implementation. If yes, spec amendment in `cascade-pins` capability declaring the awk version retired.
