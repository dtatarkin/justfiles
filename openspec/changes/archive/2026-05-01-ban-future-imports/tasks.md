## 1. Spec amendment

- [x] 1.1 Add the new capability `python-source-policy` with the requirement **"No `from __future__` imports in first-party source"** (per the delta in `specs/python-source-policy/spec.md`), with all four scenarios (clean grep, lint regression, pre-existing files cleaned, downstream consumers out of scope).
- [x] 1.2 Sanity-check that no requirement in the existing `cascade-pins` capability contradicts the new one. (None should — `cascade-pins` covers CLI surface, graph construction, planning, execution, drift, and templating; nothing speaks to `__future__` imports.)
- [x] 1.3 Confirm `pyproject.toml` already declares `requires-python = ">=3.12"`. The new requirement leans on that floor; no `pyproject.toml` Python-version change is needed.

## 2. Lint configuration

- [x] 2.1 In `pyproject.toml`:
  - Extend `[tool.ruff.lint].select` to include `"TID"` (the `flake8-tidy-imports` rule family). Today: `select = ["E", "F", "I", "B", "UP", "SIM"]`. After: `select = ["E", "F", "I", "B", "UP", "SIM", "TID"]`.
  - Add the `[tool.ruff.lint.flake8-tidy-imports.banned-api]` block:
    ```toml
    [tool.ruff.lint.flake8-tidy-imports.banned-api]
    "__future__".msg = "from __future__ imports are forbidden (Python floor is 3.12)"
    ```
  - After this change, `ruff check .` flags every `from __future__ import ...` line as `TID251`.
  - Note: do NOT use the `FA` selector — `flake8-future-annotations` (`FA100`/`FA102`) enforces *adding* `from __future__ import annotations`, the opposite of what we want.
- [x] 2.2 Run `ruff check .` once to confirm exactly 13 `TID251` hits show up across the source and tests trees. (Sanity check before edits.)

## 3. Remove `__future__` imports from first-party source

Per the per-file rhythm in `design.md` §D3 (remove import → mypy strict / pytest → fix any fallout).

Source modules (run `mypy --strict src/cascade_pins` after each cluster):

- [x] 3.1 `src/cascade_pins/__init__.py` — remove line 1.
- [x] 3.2 `src/cascade_pins/cli.py` — remove line 1.
- [x] 3.3 `src/cascade_pins/graph.py` — remove line 1.
- [x] 3.4 `src/cascade_pins/plan.py` — remove line 1.
- [x] 3.5 `src/cascade_pins/execute.py` — remove line 1.
- [x] 3.6 `src/cascade_pins/git_ops.py` — remove line 1.
- [x] 3.7 `src/cascade_pins/uv_ops.py` — remove line 1.
- [x] 3.8 `src/cascade_pins/messages.py` — remove line 1.
- [x] 3.9 Run `mypy --strict src/cascade_pins`. Must be green.

Tests (run `pytest -q` after the test cluster):

- [x] 3.10 `tests/test_graph.py` — remove line 1.
- [x] 3.11 `tests/test_plan.py` — remove line 1.
- [x] 3.12 `tests/test_messages.py` — remove line 1.
- [x] 3.13 `tests/test_execute_e2e.py` — remove line 1.
- [x] 3.14 `tests/test_drift.py` — remove line 1.
- [x] 3.15 Run `pytest -q`. All tests pass.

## 4. Validation

- [x] 4.1 `openspec validate ban-future-imports --strict` passes.
- [x] 4.2 `git grep -nE '^[[:space:]]*from __future__' -- 'src/' 'tests/'` from the repository root yields zero matches.
- [x] 4.3 `ruff check .` exits 0; no `TID251` violations remain.
- [x] 4.4 `ruff format --check` exits 0.
- [x] 4.5 `mypy --strict src/cascade_pins` exits 0.
- [x] 4.6 `pytest -q` is green; integration tests run in their usual time (~1s).

## 5. Downstream coordination (NOT part of this change)

Tracked here for visibility, not as deliverables. Consumers that vendor `justfiles` as a submodule pin its SHA; once this change archives, those consumers can bump their pins via cascade-pins. This is a plain commit per parent, not an OpenSpec change in any of them.

- [ ] 5.1 Once `justfiles` cuts a clean SHA, the umbrella `comprehender` bumps its `justfiles` pin via `just cascade-run`/`just cascade-push`. The umbrella's own audit grep (`git grep --recurse-submodules ...`) becomes clean for `justfiles` paths after that bump.
- [ ] 5.2 Sibling subrepos that pin `justfiles` (`beholder/justfiles/`, `backoffice/justfiles/`) bump their pins via the same flow.

## 6. Commit

- [ ] 6.1 Single commit (or small commit cluster — e.g. one for spec+lint config, one for the actual import removals) on `main` capturing the change artefacts under `openspec/changes/ban-future-imports/`, the `pyproject.toml` edit, and the source/test edits.
- [ ] 6.2 DO NOT PUSH. Operator confirms before pushing.

## 7. Archive

The change archives once first-party cleanup is done and the local quality gate (lint + mypy + pytest) is green. The downstream-coordination items in §5 do NOT block archiving — they are independent-repo bumps tracked outside OpenSpec.

- [ ] 7.1 After spec validation passes and the quality gate is green, archive: `openspec archive ban-future-imports`.
- [ ] 7.2 Verify post-archive: `openspec/specs/python-source-policy/spec.md` exists and contains the new requirement and its scenarios; the change directory has been moved to `openspec/changes/archive/<date>-ban-future-imports/`.
