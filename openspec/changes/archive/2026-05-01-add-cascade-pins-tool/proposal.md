## Why

Every architectural change in a recursive submodule ecosystem (a root repo with nested subrepos) ends with the same ritual: a subrepo gets a new commit, every parent that submodules it must (a) fast-forward its nested checkout, (b) re-lock its `uv.lock` if the parent has a `pyproject.toml`, (c) commit the pin bump (and lockfile if changed), (d) push, (e) the root does the same for its top-level pins, (f) the operator runs `just check-drift` to confirm consistency. Each pass takes 5–15 minutes of operator time and is mechanically identical.

The conventional `check-drift` recipe is a single awk one-liner that reports drift but does not fix it. There is no recipe today that performs the cascade itself — operators chain shell commands by hand or copy them from each successful run.

Three failure modes have shown up under hand-rolled cascades:

1. **Forgotten `uv.lock`**: the operator stages the submodule pointer but forgets the lockfile change, requiring a follow-up commit.
2. **Wrong order**: bumping a parent before its child has been pushed leaves the parent pinning a SHA the remote doesn't know.
3. **Multi-subrepo bumps**: when several subrepos move in one round, the operator manually composes a single bundled commit per parent — error-prone.

A single Python tool removes all three by deriving the cascade plan from the actual graph state and executing it deterministically. The operator's remaining job is review (commit messages, push gate) and judgment (when to *initiate* the cascade); the rote work disappears.

`bash` was considered and rejected: the cascade plan requires a topological sort over a multi-parent graph, conditional `uv.lock` staging, structured commit-message bodies, and graceful handling of `uv lock` conflicts and push rejections. Each of these is awkward in `bash` and natural in Python. The break-even point is the toposort — once you need it, Python wins on every other axis.

The tool ships in `justfiles` because consumers already vendor `justfiles` as a submodule. Hosting `cascade-pins` here means a single implementation is reachable from any working directory in the recursive tree (root, parent, child, etc.), via `uv run cascade-pins ...` once the consumer's `uv` environment is synced.

This is also `justfiles`'s first OpenSpec change. Establishing the OpenSpec root here is a low-cost side effect.

## What Changes

- Establish OpenSpec root: add `openspec/config.yaml` (with `context:` block describing `justfiles`'s role) and `openspec/project.md` describing conventions.
- Introduce `cascade-pins` capability covering: CLI surface, graph-walking algorithm, topological cascade order, conditional `uv.lock` handling, push-gate behaviour, idempotency, and drift detection.
- Implement under `src/cascade_pins/`:
  - `cli.py` — `cascade-pins {plan,run,drift,status}` subcommand surface.
  - `graph.py` — parses `git submodule status --recursive` output into a typed DAG with pinned + remote-`main` SHAs per node.
  - `plan.py` — computes the topologically-ordered set of pin bumps (deepest first); identifies parents needing bumps; pairs each parent's bump with its `uv.lock` refresh requirement.
  - `execute.py` — executes a plan: fetch + ff each child checkout, run `uv lock` per parent that has `pyproject.toml`, conditionally stage `uv.lock` if changed, commit each parent with a templated message, push if `--push`.
  - `git_ops.py` and `uv_ops.py` — subprocess helpers with structured error reporting.
  - `messages.py` — multi-line commit-message templating: per-parent message lists the moved subrepo names, old/new SHA prefixes, and (best-effort) the recently-archived OpenSpec change names from each moved subrepo's `openspec/changes/archive/` directory.
- Wire `pyproject.toml`: add `cascade_pins` package to `[tool.hatch.build.targets.wheel].packages` (or equivalent for the existing build backend), add `[project.scripts] cascade-pins = "cascade_pins.cli:main"`, ensure `uv run cascade-pins ...` works in any consumer's venv that has `justfiles` installed (which today happens via no mechanism; see Decisions for the resolution).
- Add `cascade.just` shared recipe module exposing `cascade-plan`, `cascade`, `cascade-push`, and a replacement `check-drift` (delegates to the Python implementation). Consumers `mod`-import `'justfiles/cascade.just'` to pick up these recipes.
- Add tests under `tests/`: unit tests for graph parsing, toposort, and message templating; an integration test that sets up a synthetic 3-node multi-repo fixture in a tmpdir (using `git init --bare` for remotes) and exercises a full cascade run.
- Update consumers' `justfile` `check-drift` recipes to delegate to `cascade-pins drift` (preserving the operator-visible behaviour while gaining structured output). This is a NON-MANDATORY follow-up — out of scope for this change, but documented as a follow-on opportunity.

## Capabilities

### New Capabilities

- `cascade-pins`: the Python tool's CLI, its graph-walking algorithm, its cascade order, its conditional `uv.lock` handling, its push-gate behaviour, its idempotency contract, its drift detection. The capability spec lives in `specs/cascade-pins/spec.md`.

### Modified Capabilities

None. This is the first capability in `justfiles`'s OpenSpec root.

## Impact

- **New OpenSpec root in `justfiles`.** First-time setup: `openspec/config.yaml`, `openspec/project.md`, `openspec/changes/`, `openspec/specs/`. After this change archives, `openspec/specs/cascade-pins/spec.md` is the first promoted capability.
- **`pyproject.toml` grows.** `[project.scripts]` gains `cascade-pins`; `[tool.hatch.build.targets.wheel].packages` (or equivalent) gains `src/cascade_pins`.
- **Consumer reachability**: `cascade-pins` is invokable from any consumer's venv that has `justfiles` installed as an editable dependency. Today no consumer declares `justfiles` as a Python dep (it's a recipe-only submodule). Two paths forward:
  1. Each consumer adds `justfiles` to its `[tool.uv.workspace] members` and `[project] dependencies`. Existing consumers' workspaces would gain a fourth/fifth member.
  2. Consumers don't add `justfiles` as a workspace member; they invoke the tool via `uv run --with file:./justfiles cascade-pins ...` or via a Python script wrapper in `cascade.just` that uses `uv tool install --from ./justfiles cascade-pins`.
  Path (2) keeps consumer workspaces unchanged; this proposal recommends (2) and documents the recipe wrapper. (1) is a possible future refinement if the workspace-member overhead is acceptable.
- **Drift detection upgraded**: today's awk-based `check-drift` becomes the fallback; the Python implementation produces structured output (per-name groups, conflicting SHAs, suggested fixes) when invoked via `cascade-pins drift`.
- **Operator workflow**: the rote 5-step cascade ritual collapses to one command (`just cascade` for review, `just cascade-push` for one-shot). Push remains operator-gated by default (`--push` opt-in).
- **Out of scope**: server-side automation (CodePipeline, Lambda, hooks); cross-repo CI orchestration; auto-rebase on conflict (the tool surfaces conflicts and bails).
