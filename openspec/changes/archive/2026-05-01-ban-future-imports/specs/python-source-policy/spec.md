## ADDED Requirements

### Requirement: No `from __future__` imports in first-party source

No first-party Python source file in this repository — files under `src/cascade_pins/` and `tests/` — SHALL contain a `from __future__ import ...` statement. The repository's Python floor is `>=3.12` (declared in `pyproject.toml`'s `[project] requires-python`); every behaviour-changing `__future__` flag is either already unconditional in 3.12 or is the deferred-evaluation `annotations` opt-in we have decided not to use. Annotations in first-party source SHALL be evaluated eagerly (the default).

The repository's lint configuration (`[tool.ruff.lint]` in `pyproject.toml`) SHALL enable a rule that fails on any `from __future__ import ...` line, so the rule is enforced automatically and survives without manual policing. The standard recipe `ruff check` (the `cascade-pins` capability already invokes ruff as part of its own quality gate) SHALL surface any violation.

This requirement is scoped to first-party source. `justfiles` is general-purpose and does not vendor any submodules of its own; the requirement therefore has no out-of-tree carve-out clause analogous to those used by sibling subrepos that pin nested submodules.

#### Scenario: first-party source contains no `__future__` imports

- **GIVEN** a clean checkout of this repository at any commit on `main` after this change is archived
- **WHEN** an operator runs `git grep -nE '^[[:space:]]*from __future__' -- 'src/' 'tests/'` from the repository root
- **THEN** the command exits with status 1 (no matches) and produces no output

#### Scenario: lint fails on a regression

- **GIVEN** the lint configuration declared in `pyproject.toml` and the rule selection added by this change (`TID` family enabled, `__future__` listed under `[tool.ruff.lint.flake8-tidy-imports.banned-api]`)
- **WHEN** an author adds a `from __future__ import annotations` line to any file under `src/` or `tests/` and runs `ruff check .`
- **THEN** ruff reports a violation citing the offending file and line as `TID251` with the configured message
- **AND** the lint command exits with non-zero status, blocking the change from passing CI

#### Scenario: pre-existing `__future__` imports are removed

- **GIVEN** the thirteen first-party files that today contain `from __future__ import annotations`:
  - `src/cascade_pins/__init__.py`
  - `src/cascade_pins/cli.py`
  - `src/cascade_pins/execute.py`
  - `src/cascade_pins/git_ops.py`
  - `src/cascade_pins/graph.py`
  - `src/cascade_pins/messages.py`
  - `src/cascade_pins/plan.py`
  - `src/cascade_pins/uv_ops.py`
  - `tests/test_drift.py`
  - `tests/test_execute_e2e.py`
  - `tests/test_graph.py`
  - `tests/test_messages.py`
  - `tests/test_plan.py`
- **WHEN** this change is archived
- **THEN** none of those files contain a `from __future__ import ...` line
- **AND** any forward reference that previously required string-deferred evaluation has been resolved either by string-quoting the annotation or by moving the import under an `if TYPE_CHECKING:` guard with a quoted-string annotation
- **AND** `mypy --strict src/cascade_pins` and the project's full pytest suite both pass

#### Scenario: downstream consumers are out of scope

- **GIVEN** any consumer that vendors this repository as a git submodule (e.g. the `comprehender` umbrella, `beholder`, `backoffice`)
- **WHEN** that consumer's working tree contains a Python file with `from __future__ import ...` because the consumer itself has not yet completed its own corresponding cleanup
- **THEN** this requirement is NOT considered violated for `justfiles`
- **AND** the responsibility for cleaning the consumer's first-party tree lies with that consumer's own repository policy (each one has its own equivalent OpenSpec change or non-OpenSpec cleanup PR)
- **AND** when this repository publishes a clean SHA, downstream consumers SHALL bump their pin (a non-OpenSpec activity tracked via the cascade-pins recipes)
