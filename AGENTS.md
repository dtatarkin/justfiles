# Justfile conventions for AI agents

This file is the **single source of truth** for how justfiles are written across
the projects that vendor this repo as their `justfiles/` submodule. It rides the
submodule into every consumer, so wherever you find it (`justfiles/AGENTS.md` or
`../justfiles/AGENTS.md`), the rules below apply to any `justfile`, `*.just`, or
`.just` file in that project.

Edit the conventions **here only**. Do not copy them into per-project files.

When creating or editing a justfile, conform to everything below. When in doubt,
read the existing modules in this repo (`git.just`, `just.just`, `pre-commit.just`,
`uv-workspace.just`, `git-submodule.just`) — they are the worked examples.

## Reuse before you author

The strongest convention: **don't re-implement what a shared module already does.**
On a uv/Python project, `mod` the modules from this repo instead of writing local
git / submodule / lint / format recipes:

```just
mod just          '../justfiles/just.just'
mod git           '../justfiles/git.just'
mod git-submodule '../justfiles/git-submodule.just'
mod pre-commit    '../justfiles/pre-commit.just'
mod uv-workspace  '../justfiles/uv-workspace.just'
```

A project's own `justfile` should shrink to: these imports, plus the handful of
recipes that are genuinely specific to that project. If you catch yourself writing
a generic `git push` / `submodule update` / `pre-commit run` recipe, stop and
import the module instead.

## Every module file

A reusable module is `<name>.just`. It MUST open with this preamble:

```just
mod just 'just.just'          # only if the module calls just::list / other just:: recipes

source_file := source_file()

[default]
[doc("List all available recipes")]
list: (just::list source_file)
```

- `source_file := source_file()` lets recipes reference their own file for
  `just --justfile {{ source_file }} ...` cross-recipe calls. Always assign it.
- Every module exposes a `[default] list` recipe so a bare `just <module>` prints
  its recipes. Delegate to `just::list` rather than re-spelling `just --list`.
- Declare a `mod <dep> '<dep>.just'` line for every sibling module the file calls.

## Recipe rules

- **Help text via `[doc("…")]`, always.** Every recipe that shows up in
  `just --list` carries an explicit `[doc("…")]` attribute holding its one-line
  help. Do **not** rely on the bare-comment fallback: `just` would take only the
  *last* `#` line above the recipe as the description, which silently breaks the
  moment you add multi-line rationale above it. The `[doc("…")]` is the help text,
  full stop.
- **Comments are rationale only — never the help text.** Use `#` lines above a
  recipe for the *why*, examples, gotchas, or when-to-run notes. **Never duplicate**
  the `[doc("…")]` string in a comment. A recipe that needs no extra context has
  just its `[doc("…")]` and no comment at all.
- **Separate a rationale comment from the recipe with one blank line.** This is not
  cosmetic: `just` binds the comment line *touching* a recipe as a doc-comment, and
  `just --fmt` then **deletes that line** because the `[doc("…")]` attribute
  supersedes it — silently dropping your last rationale line. Always leave a blank
  line between the comment block and the `[doc("…")]`:

  ```just
  # dbt wants these at the subcommand level, not the top level, so we re-shape
  # `dbt <cmd> [args]` into `dbt <cmd> --project-dir … --profiles-dir … [args]`.

  [doc("Wrap `dbt` with the project/profiles dir baked in (e.g. `just dbt run`)")]
  dbt cmd *args:
      uv run dbt {{ cmd }} --project-dir dbt_proj --profiles-dir dbt_proj {{ args }}

  [doc("Run pytest across the test suite")]
  test *args:
      uv run pytest {{ args }}
  ```

- **Don't hand-order attributes — `just --fmt` sorts them alphabetically**
  (`[default]`, `[doc("…")]`, `[linux]`, `[no-cd]`, `[private]`, …). Write them in
  any order and let the formatter normalize; the pre-commit `format-justfile` hook
  enforces it.
- **`[no-cd]`** on any recipe meant to act in the **caller's** directory (most git,
  submodule, and lint recipes). Without it, `just` runs the recipe from the module's
  own directory, which is almost never what a shared recipe wants.
- **`[private]` + `_underscore` prefix** for internal helpers that should not appear
  in `--list` (e.g. `_members`). Private recipes have no help text, so they carry
  **no** `[doc("…")]` — a `#` rationale comment is fine.
- **Shebang for multi-line shell.** A recipe with more than one shell statement uses
  a shebang body with strict mode:

  ```just
  [doc("…")]
  recipe arg:
      #!/usr/bin/env bash
      set -euo pipefail
      ...
  ```

  Single commands stay as a plain recipe line — no shebang.
- **Call another recipe as a dependency, not from the shell body.** When a recipe
  only forwards to another recipe, use just's dependency-call syntax
  `recipe: (other "arg" …)` instead of a `just other arg …` line in the body. The
  call is resolved at parse time, spawns no nested `just` process, and reads as
  composition:

  ```just
  # prefer
  [doc("List the per-session keys in the sessions KV bucket")]
  sessions-ls: (nats "kv" "ls" "comprehender-sessions")

  # not
  [doc("List the per-session keys in the sessions KV bucket")]
  sessions-ls:
      just nats kv ls comprehender-sessions
  ```

  Variadic args pass straight through — `test *args: (run "pytest" args)`. Two cases
  keep the `just …` body form because a dependency call can't express them:

  - the value must be computed in the shell, e.g. inside a command substitution
    `$(…)` (`@git remote get-url $(just --justfile {{ source_file }} remote-name)`);
  - the target recipe is **out of scope** — a dependency only resolves recipes in
    this file plus its imported modules, so a module recipe that forwards to one the
    *consumer* defines (e.g. `pre-commit::pre-commit` → the consumer's `run`) must
    call `just run …` in the body.

  Reach across modules with `{{ module_file() }}` and locate the caller with
  `{{ invocation_directory() }}`.
- **Thin tool wrappers** follow the `run`/`*args` shape:

  ```just
  [doc("Run a command in the project environment")]
  run *args:
      uv run {{ args }}

  [doc("Start an IPython shell in the project environment")]
  ipython *args: (run "ipython" args)
  ```

## Consumer (per-project) files

- The project entrypoint is `justfile`. It pulls in shared modules and optionally a
  project-local file:

  ```just
  import? ".just"          # optional: only if the local file exists

  mod test 'test.just'     # project-local submodules live alongside

  source_file := source_file()
  set dotenv-load          # only when the project uses a .env

  [default]
  [doc("List all available recipes")]
  list: (just::list source_file)
  ```

- **`.just` holds the local imports + local recipes**; it is generated from a
  committed **`.just.example`** at bootstrap (`cp --no-clobber`), so `.just` is the
  place for machine-local paths/values and stays out of the committed example.
- **`mod?` / `import?` (optional)** for anything that must parse *before* the
  `justfiles/` submodule is checked out — keeps a non-recursive clone from failing
  to parse. Use the optional form for every reference into the submodule from a
  bootstrap-reachable file.

## Formatting & enforcement

- Format with `just just::format <justfile>` (wraps `just --fmt --unstable`). Run it
  before committing any justfile change.
- This repo's `.pre-commit-config.yaml` runs the `format-justfile` hook, so CI/commit
  hooks reject unformatted justfiles. Don't fight the formatter — let it normalize
  spacing and alignment.

## Scope & provenance

These conventions govern the projects that vendor this submodule. They are not
specific to one AI tool — Claude Code, Codex, Cursor, and others all read the rules
through whatever pointer the consuming project sets up (a root `AGENTS.md` /
`CLAUDE.md` line). Keep this file tool-neutral.
