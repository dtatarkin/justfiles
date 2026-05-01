## Context

The umbrella `comprehender`'s `repository-structure` spec (requirement: "No `from __future__` imports anywhere in the comprehender system") names `justfiles` as a subrepo expected to enforce the ban via its own lint toolchain. `justfiles`'s `pyproject.toml` already configures ruff with `select = ["E", "F", "I", "B", "UP", "SIM"]`. None of those families flag `from __future__ import ...`:

- `UP` includes `UP010` (unnecessary `__future__` imports), but `UP010` only flags imports of flags that are no-ops in the project's `target-version` (e.g. `division`, `print_function`, `absolute_import`). It does **not** flag `from __future__ import annotations`, which still has runtime semantics in 3.12 (deferred evaluation).
- `FA100` / `FA102` (the `flake8-future-annotations` family) enforce *adding* `from __future__ import annotations` for back-compat with older Python versions — the opposite of what we want.

The rule that *does* catch `from __future__ import annotations` and any other `__future__` import unconditionally is `TID251` (banned-api) from `flake8-tidy-imports`, exposed by ruff under the `TID` selector. Banning the `__future__` module via the `banned-api` table produces a `TID251` violation on every `from __future__ import ...` line, with a custom message visible in the lint output.

This is the same mechanism beholder and backoffice picked for their corresponding subrepo proposals. Picking the same mechanism here keeps the system coherent: an operator who reads the violation message in any subrepo sees the same wording.

## Decisions

### D1. Use ruff's `TID251` (banned-api) with `__future__` configured as banned

The mechanism is `flake8-tidy-imports`'s `TID251` rule, exposed by ruff under the `TID` selector. The configuration:

```toml
[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "SIM", "TID"]

[tool.ruff.lint.flake8-tidy-imports.banned-api]
"__future__".msg = "from __future__ imports are forbidden (Python floor is 3.12)"
```

This produces a `TID251` violation on every `from __future__ import ...` line in scope, with the custom message visible in the lint output. Self-documenting at the point of failure — a contributor reading the violation sees the rationale without needing to consult the spec.

The `select` line keeps the existing families and only appends `"TID"`. The new `[tool.ruff.lint.flake8-tidy-imports.banned-api]` table adds a single entry. No other lint configuration changes.

### D2. Alternatives considered

- **`UP` family (`UP010`).** Ruff already selects `UP`, but `UP010` only flags `__future__` imports whose flags are unconditional no-ops in the project's `target-version`. `from __future__ import annotations` is still a meaningful flag in 3.12 (it changes annotation evaluation semantics), so `UP010` does not flag it. Insufficient.
- **`FA` family (`flake8-future-annotations`, `FA100` / `FA102`).** These rules enforce *adding* `from __future__ import annotations` for back-compat — the opposite of what we want. Selecting `FA` would not flag the existing imports as violations and could even introduce noise demanding their reinstatement elsewhere. Wrong direction; rejected.
- **Pre-commit hook with a custom regex.** Could work — `git grep -nE '^[[:space:]]*from __future__'` exit-1 in a `pre-commit` hook. Rejected as duplicative: ruff is already the enforcement seam for this repo, and `TID251` produces a structured, IDE-surfaceable diagnostic rather than a hook failure with no editor integration.
- **Custom AST check.** Over-engineering for a one-line rule. Rejected.

### D3. Per-file removal rhythm

The 13 affected files are small (cascade_pins is a young codebase). The rhythm:

1. Remove the `from __future__ import annotations` line from one cluster of files (source or tests).
2. Run `mypy --strict src/cascade_pins/` (after each source-cluster) and `pytest -q` (after each test-cluster).
3. Fix any forward-reference fallout. Forward refs go to either string-quoted annotations or `if TYPE_CHECKING:` blocks with quoted-string annotations.

Because cascade_pins's modules are flat (no circular imports today, no forward references that depend on classes defined later in the same module), no fallout is anticipated. The per-file rhythm exists so that, if surprise *does* surface, it is localised to the cluster currently being removed and can be addressed before moving on.

### D4. Test-only `noqa` escape (forward note)

If a future test legitimately needs `from __future__ import annotations` (e.g. a regression test that exercises annotation lazy-evaluation behaviour itself), it can carry a `# noqa: TID251` line-level escape with a comment explaining the exemption. No per-file or per-directory blanket rule is anticipated. None of today's 13 files need it; the escape is mentioned here only as a known-available pressure-relief valve.

### D5. Capability placement

A new capability `python-source-policy` is introduced, holding only this one requirement today. The alternative — attaching the requirement to the existing `cascade-pins` capability — was rejected because the rule is not specific to the cascade-pins tool: it is a cross-cutting Python source policy that would apply to any new tool added to this repo (the project context allows for more entry points to follow cascade-pins). Putting it under `cascade-pins` would couple a general policy to a specific tool's spec.

`python-source-policy` is a natural home for any future cross-cutting Python source rule (e.g. import ordering quirks, banned stdlib idioms, docstring conventions) without polluting the `cascade-pins` capability spec.

## Risks

- **[Risk]** ruff's `TID251` configuration schema or `flake8-tidy-imports` interpretation may shift across ruff versions. The `[dependency-groups].dev` block does not currently pin ruff (it is invoked via `uv tool` or a developer's environment).
  → Mitigation: verify the rule selection with the ruff version actually installed during validation. The `[tool.ruff.lint.flake8-tidy-imports.banned-api]` block has been stable across ruff 0.6 and 0.7. If a future ruff drops or renames the rule, follow up with a small proposal to adjust configuration.
- **[Risk]** A future contributor adds `from __future__ import annotations` back inside a `# noqa: TID251` block to silence the rule "just for this file." The exemption is meant to be exceptional; a reviewer should challenge any such use.
  → Mitigation: §D4 above documents the limited intended use; reviewers can cite this design when challenging unjustified `noqa`.

## Migration

1. **Add the spec amendment** (this change's `python-source-policy` delta) and the new ruff selector + `flake8-tidy-imports.banned-api` block to `pyproject.toml`. Ruff CI now flags the 13 hits as `TID251`.
2. **Remove the imports** per the per-file rhythm in `tasks.md` §3.
3. **Run the full quality gate**: `ruff check`, `ruff format --check`, `mypy --strict src/cascade_pins`, `pytest -q`. All green.
4. **Commit** on `main` (single commit or small cluster). Operator confirms before pushing.
5. **Archive** once CI is green.
6. **Pin bumps** in consumers (umbrella, sibling subrepos) follow as plain commits via cascade-pins — outside this OpenSpec change.
