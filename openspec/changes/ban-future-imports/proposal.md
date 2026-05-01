## Why

`justfiles`'s first-party Python source (`src/cascade_pins/` plus `tests/`) carries thirteen `from __future__ import annotations` lines today — six in source modules, seven in tests. The Python floor declared in `pyproject.toml` is `>=3.12`; every behaviour-changing `__future__` flag is either already unconditional in 3.12 or is the deferred-evaluation `annotations` opt-in. The umbrella that pins this subrepo (`comprehender`) has already amended its `repository-structure` spec to forbid `from __future__` imports anywhere in the system, and it explicitly names `justfiles` as a subrepo expected to (a) carry zero such imports and (b) configure its lint toolchain to fail on regressions. Today the umbrella-side audit grep `git grep --recurse-submodules -nE '^[[:space:]]*from __future__'` is non-clean because of this subrepo.

This proposal removes those imports from `justfiles`'s own source tree and configures `ruff` to forbid the construct going forward. `justfiles` is general-purpose (no consumer-specific knowledge), so the change has no downstream contract impact — only a tightening of this repo's lint policy and a one-line change on top of every Python file currently carrying the import.

## What Changes

- **Remove `from __future__ import annotations`** from every first-party Python file under `src/cascade_pins/` and `tests/`. Today's hits (13 files):
  - `src/cascade_pins/__init__.py:1`
  - `src/cascade_pins/cli.py:1`
  - `src/cascade_pins/execute.py:1`
  - `src/cascade_pins/git_ops.py:1`
  - `src/cascade_pins/graph.py:1`
  - `src/cascade_pins/messages.py:1`
  - `src/cascade_pins/plan.py:1`
  - `src/cascade_pins/uv_ops.py:1`
  - `tests/test_drift.py:1`
  - `tests/test_execute_e2e.py:1`
  - `tests/test_graph.py:1`
  - `tests/test_messages.py:1`
  - `tests/test_plan.py:1`
- **Configure ruff to forbid `from __future__ import ...`** in `pyproject.toml`'s `[tool.ruff.lint]` table. The mechanism is `flake8-tidy-imports`'s `TID251` rule, exposed by ruff under the `TID` selector and configured via a `[tool.ruff.lint.flake8-tidy-imports.banned-api]` block that bans the `__future__` module with a self-documenting message. (The `FA` family is the *opposite* of what we want — it enforces *adding* `from __future__ import annotations`. See `design.md` D1.)
- **BREAKING (lint-policy):** any subsequent PR that adds `from __future__ import ...` to `justfiles`'s source fails `ruff check`.
- **Verify mypy strict still passes** after each cluster of removals. None of the touched modules use forward references that would have required string-deferred evaluation (the `cascade_pins` codebase is self-contained: types defined within the module are referenced after their definitions; cross-module references are concrete names already imported eagerly), but the per-file rhythm in §3 of `tasks.md` keeps the rhythm honest by re-running `mypy --strict src/cascade_pins/` after each removal and stopping if a regression appears.
- Out of scope: editing files in any consumer that vendors `justfiles` as a submodule (e.g. `comprehender`, `beholder`, `backoffice`). Pin bumps in those parents are tracked outside OpenSpec via the cascade-pins recipes once this change lands and a clean SHA is published.

## Capabilities

### New Capabilities

- `python-source-policy`: a new capability holding cross-cutting rules about first-party Python source in this repository. Today it is introduced with a single requirement (the `__future__` ban); it provides a natural home for any future Python source-level policy (e.g. import ordering, banned stdlib idioms, docstring conventions) that does not belong inside the `cascade-pins` capability spec.

### Modified Capabilities

None.

## Impact

- **Code edits:** 13 `.py` files in `justfiles`'s first-party tree. Each edit is a single-line deletion at the top of the file. `ruff format` may want to collapse the now-empty leading blank line (handled per file in `tasks.md`).
- **Lint config:** add the `TID` selector to `[tool.ruff.lint].select` and a `[tool.ruff.lint.flake8-tidy-imports.banned-api]` block in `pyproject.toml`. No change to the existing `mypy`, `pytest`, or `hatchling` configuration.
- **Runtime behaviour:** annotations in the affected modules become eagerly-evaluated. `cascade_pins` does not introspect annotations at runtime (no pydantic, no msgspec, no FastAPI, no dataclasses with `field(...)` resolution); the only consumer of types is `mypy`, which reads source rather than runtime annotations. No behaviour change is expected.
- **Submodule pin bumps:** none in this proposal — `justfiles` has no submodules of its own. The umbrella (and any sibling that pins `justfiles`) bumps the `justfiles` SHA via cascade-pins after this change archives. That is plain commit work, not OpenSpec.
- **Reversibility:** trivial — re-add `from __future__ import annotations` to any module that turns out to need lazy annotations (would also require relaxing or per-file-`noqa`-ing the `TID251` rule). The ruff rule is one `pyproject.toml` line away from disabled.
- **No interaction** with the only other OpenSpec artefact in this repo (the archived `add-cascade-pins-tool` change). The current change touches lint config and import lines; cascade-pins capability behaviour is unaffected.
