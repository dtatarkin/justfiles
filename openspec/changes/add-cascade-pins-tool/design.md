## Context

The recursive submodule cascade is the dominant operator overhead in the kit-style ecosystem. Every roadmap step in the recent telegram-client extraction has produced a cascade — sometimes spanning four repos (umbrella, beholder, backoffice, plus 1–2 nested library updates). The mechanical shape is invariant:

```
   1. push the moved subrepo(s) to origin
   2. for each (parent, child) pair where child basename ∈ moved set:
        a. git -C parent/child fetch && pull --ff-only origin main
        b. if parent has pyproject.toml: uv lock
        c. stage parent/child (always) and parent/uv.lock (if changed)
        d. commit parent with a message naming the moved subrepos
        e. push parent if --push
   3. cascade up: same loop where the parent becomes a moved subrepo and
      its parent (the umbrella, typically) becomes the new parent
   4. run check-drift; bail if anything is inconsistent
```

The variance is entirely in step 2c's commit message body and the operator's choice of whether to push automatically. Everything else is deterministic given graph state.

## Goals / Non-Goals

**Goals:**

- A single command (`just cascade`) replaces the multi-step hand cascade.
- The tool is callable from any node in the recursive submodule tree (umbrella, beholder, backoffice, …) and walks downward from there, computing the local view of outdated pins.
- The operator retains the push gate by default. `--push` is opt-in.
- Idempotent: a second `cascade run` after a successful one is a no-op.
- Failures (uv lock conflict, push rejection, network errors) surface verbatim and leave the working tree in a recoverable state — never half-committed across multiple parents.
- Drift detection becomes a first-class subcommand with structured output, replacing the umbrella's `awk` one-liner as the canonical drift check.
- `justfiles` becomes the OpenSpec home for this and any future shared Python tooling.

**Non-Goals:**

- Server-side automation (CodePipeline, Lambda, post-receive hooks). The tool runs locally; the operator is the trigger.
- Auto-rebase or auto-merge of `uv.lock` conflicts. The tool surfaces and bails.
- Cross-repo CI orchestration. Each consumer's CI continues to run independently.
- Squash, fixup, or rewrite of commit history. Each cascade produces fresh commits.
- Replacing the umbrella's `just status` recipe (it does a different thing — show pinned vs. local SHAs; cascade-pins compares pinned vs. remote-main).

## Decisions

### D1. CLI surface

```
   cascade-pins plan                    Print the cascade plan; no side effects.
   cascade-pins run [--push]            Execute: fetch+ff, uv lock, commit per
                                        parent. --push pushes after each commit.
   cascade-pins drift                   Structured drift report. Replaces the
                                        umbrella's awk-based check-drift.
   cascade-pins status                  Graph view: per-node pinned vs. remote
                                        SHA, with archived-since-pin OpenSpec
                                        change names.
```

Common flags:

```
   --branch <name>     Compare against this remote branch instead of `main`.
   --root <path>       Walk from <path> instead of the cwd.
   --no-uv-lock        Skip `uv lock` even where pyproject.toml exists.
   --dry-run           Implies --no-push; prints what would be done.
```

`run` subcommand: short-circuits to "no plan" exit 0 when nothing is outdated.

### D2. Graph construction

Source: `git submodule status --recursive` (already called by the umbrella's existing recipes). Each line yields `(pinned_sha, path, branch_or_tag)`. The script then runs `git -C <path> rev-parse origin/<branch>` (after a quick `git -C <path> fetch --quiet`) for each node to learn the remote `main` head.

The graph is a tree (each submodule has exactly one parent in any given checkout); no cycle handling needed. Toposort is a simple depth-first post-order traversal.

### D3. Toposort: deepest first

Bumping a parent's pin to a SHA that origin doesn't know yet produces a broken state. So we cascade in dependency order:

```
   layer N+1 (deepest): subrepos whose own contents have moved.
                        Push these first.
   layer N:             parents of layer N+1. After their children push,
                        they fast-forward and bump.
   layer N-1:           parents of layer N. Same.
   …
   layer 0 (root):      umbrella. Last.
```

The script computes layers as DFS-post-order on the graph; subrepos at the same layer can be processed in any order (they have no dependency on each other).

### D4. Conditional `uv.lock` staging

After bumping a parent's submodule pointer:

- If the parent has a `pyproject.toml`, run `uv lock`.
- If `uv.lock` changed (`git diff --quiet uv.lock` returns nonzero), stage it.
- If `uv lock` exits nonzero (conflict or unsatisfiable), bail with the error message; do NOT stage anything; leave the working tree dirty for operator inspection.

The recent extraction work has shown that many cascades have `uv.lock` no-ops (spec-only changes don't move package metadata). The conditional stage avoids spurious "no-op" lockfile commits.

### D5. Commit message templating

Per-parent message body, multi-line:

```
Bump <comma-separated-children> pins<: optional summary>

<child-name-1> @ <old-sha-prefix>..<new-sha-prefix>
  <subject 1>
  <subject 2>
  …
  (archived: change-name-1, change-name-2)

<child-name-2> @ <old-sha-prefix>..<new-sha-prefix>
  …
```

Subject lines come from `git -C parent/child log <old>..<new> --pretty=%s`. Archived change names come from a directory listing of `parent/child/openspec/changes/archive/` filtered to entries created since the previous pin (best-effort; if the consumer doesn't have OpenSpec, this section is omitted).

The first line ("Bump … pins …") is always synthesised; the body is informational and operator-overridable via `cascade-pins run --message "..."`.

**Alternatives considered:**

- *No body* (just the first line). Rejected: the recent cascade history shows operators frequently want to know "what archived changes did this pin actually carry?" — synthesising it removes a manual git-log step.
- *Conventional Commits format*. Out of scope; this is internal-only and our convention is descriptive single-line summaries with prose bodies.

### D6. Push gate

Default: `cascade-pins run` commits but does not push. Output ends with `to push, run: ...` listing each parent that was committed. `cascade-pins run --push` pushes after each commit.

`run --push` aborts on first push rejection (e.g., remote moved). The operator resolves and re-runs.

**Alternatives considered:**

- *Always push*. Rejected: the project convention is operator-gated pushes.
- *Push only the leaf children, not parents*. Rejected: makes parent commits effectively dead until manually pushed.

### D7. Idempotency

`cascade-pins run` after a successful previous run computes an empty plan and exits 0 with "no bumps needed." This is the `plan empty → noop` short-circuit.

A run interrupted mid-execution (e.g., uv lock conflict at parent N out of M) leaves prior parents' commits in place. The next run starts from the current graph state — typically only parent N onward — so the partial work isn't redone, just continued.

### D8. Distribution to consumers

`justfiles` is currently a recipe-only submodule. To make `cascade-pins` invokable from a consumer's venv, two paths:

1. Each consumer adds `justfiles` to `[tool.uv.workspace] members` and `[project] dependencies`. Tool becomes available as `uv run cascade-pins`. Cost: one more workspace member per consumer; affects the umbrella's `repository-structure` spec (which enumerates members for beholder and backoffice — those would gain `justfiles`).
2. The recipes use `uv tool run --with file:./justfiles cascade-pins` (or a similar `uv tool install` step in `init`). Tool runs in its own ephemeral venv; consumers' workspaces are unchanged.

This change adopts (2). Rationale: keeps consumer pyprojects untouched; mirrors how `pre-commit` hooks already invoke tools without forcing them into the workspace; the umbrella's `repository-structure` spec needs no amendment.

The recipes in `cascade.just` look like:

```just
cascade-plan:
    uv tool run --with file://{{ source_dir }}/.. cascade-pins plan

cascade *args:
    uv tool run --with file://{{ source_dir }}/.. cascade-pins run {{ args }}
```

`source_dir` is `just`'s built-in for the path of the recipe file's directory; `{{ source_dir }}/..` resolves to `justfiles/` itself when consumed via `mod cascade 'justfiles/cascade.just'`.

**Alternatives considered:**

- *Hard-code `cascade-pins` as a console script and expect it on `$PATH`*. Rejected: requires global install or per-venv install; defeats the "submodule = self-contained" principle.
- *Vendor as a single-file script, no package*. Rejected: testability is poor; reuse from other recipes is awkward.

### D9. Drift detection becomes structured

Today's umbrella `check-drift` (an `awk` one-liner) prints `DRIFT: name — sha1 vs sha2` lines and exits nonzero. `cascade-pins drift` produces:

```
   drift detected (3 names)
     comprehender-common  (2 SHAs)
       8842d21  → ./beholder/comprehender-common/
       01c2844  → ./backoffice/comprehender-common/
     telegram-client      (2 SHAs)
       …
```

Plus exit status. The recipe `check-drift` (in `cascade.just`) wraps `cascade-pins drift`. The umbrella's existing `check-drift` (awk) can switch to delegating once cascade-pins is available; that switch is a separate, optional follow-up.

### D10. Test strategy

- **Unit tests**: graph parsing (synthetic `git submodule status` strings), toposort (synthetic graphs of varying shapes), commit-message templating (snapshot tests).
- **Integration test**: a tmp-dir fixture sets up three repos with `git init --bare` remotes in a tempdir, links them via `git submodule add`, makes commits in the leaf, and runs `cascade-pins run`. Asserts the parent and grandparent receive correct commits with correct SHAs. ~150 lines of fixture + assertions.
- **Smoke test**: a recipe in `cascade.just` that runs `cascade-pins plan` against the project tree and asserts exit-0; useful as a CI gate later.

### D11. OpenSpec scaffolding

`justfiles` had no `openspec/` until this change. We bootstrap it with:

- `openspec/config.yaml` carrying a `context:` block describing the repo's role.
- `openspec/project.md` mirroring the format used by sibling library repos (`comprehender-common`, `mtproto-kit`, `telegram-client`).
- This change directory itself.

After archive, `openspec/specs/cascade-pins/` becomes the first promoted capability spec.

## Risks / Trade-offs

- **First Python tool in `justfiles` raises the maintenance bar.** What was a recipe-only repo grows a real Python package, tests, type checking, and a console script. Mitigation: this change is self-contained; the package is one module under `src/cascade_pins/`; subsequent Python tools (if any) follow the same pattern and a precedent exists.
- **`uv tool run --with file://...` semantics on first invocation.** First run downloads/builds; subsequent runs are cached. Operator may see a "first cascade is slow" warning. Mitigation: document in the recipe's comment.
- **Graph parsing relies on git's output format.** If `git submodule status --recursive`'s format changes, parsing breaks. Mitigation: parser is small and well-tested; cover format with explicit tests; pin a `git --version` baseline in the spec.
- **Toposort assumes no cycles.** Submodule graphs are by construction acyclic (a submodule cannot include its own parent). The script asserts acyclicity and panics if violated; a cycle would be a graph-corruption bug, not a normal state.
- **`uv lock` failures are not always recoverable.** A lockfile conflict requires operator judgment. The tool bails; the operator inspects, fixes, re-runs. This is a feature, not a regression.
- **Commit-message body might leak sensitive change names.** OpenSpec change names are descriptive, not secret. No risk identified.
- **Distribution path D8(2) ties cascade-pins to `uv tool` semantics.** If `uv tool` ever changes its `--with file://` resolution model, the recipe wrapper breaks. Mitigation: the alternative D8(1) remains an escape hatch; switching is a one-line change per consumer.
- **`justfiles`'s OpenSpec root is brand new.** Future contributors authoring proposals here will be its first AI-assisted users. The `context:` block in `config.yaml` is intentionally explicit about library-tier rules so AI-assisted proposals don't drift into project-tier territory.
