## ADDED Requirements

### Requirement: CLI surface

`cascade-pins` SHALL expose four subcommands: `plan`, `run`, `drift`, and `status`. The console script entry point SHALL be `cascade_pins.cli:main` and SHALL be invokable as `cascade-pins <subcommand>` from any consumer's venv that has the `justfiles` package available (typically via `uv tool run --with file://<path-to-justfiles> cascade-pins`).

`run` SHALL accept the flags `--push`, `--no-uv-lock`, `--branch <name>` (default `main`), `--root <path>` (default `cwd`), `--dry-run`, and `--message <text>` (overrides templated body for this run only).

`plan` SHALL share the `--branch`, `--root`, and `--no-uv-lock` flags but SHALL NOT accept `--push` or `--dry-run` (it has no side effects).

`drift` SHALL accept `--root <path>` and exit nonzero on detected drift.

`status` SHALL accept `--root <path>` and `--branch <name>`.

#### Scenario: invoking the console script

- **GIVEN** a consumer venv with `justfiles` available via `uv tool`
- **WHEN** the operator runs `uv tool run --with file://<justfiles-path> cascade-pins plan`
- **THEN** the command exits with status 0 and prints either an empty plan ("no bumps needed") or an itemised plan in deepest-first order

#### Scenario: --dry-run implies --no-push

- **GIVEN** an outdated graph
- **WHEN** the operator runs `cascade-pins run --dry-run --push`
- **THEN** no commits or pushes occur
- **AND** stdout describes what would have happened, identical to `cascade-pins plan` output

### Requirement: Graph construction

`cascade-pins` SHALL build its working graph from `git submodule status --recursive` invoked at the configured root. For each discovered node, the tool SHALL fetch its origin remote (`git -C <node-path> fetch --quiet`) and read the remote-branch head (`git -C <node-path> rev-parse origin/<branch>`). The resulting `Graph` data structure SHALL carry, for each node: its filesystem path, its parent's filesystem path (or none for the root), its pinned SHA (the SHA recorded by the parent's submodule entry), its remote-branch SHA, and a boolean indicating whether the node has a `pyproject.toml`.

The graph SHALL be acyclic by construction (git submodule semantics enforce this). The tool SHALL panic with a clear error if a cycle is detected.

#### Scenario: graph captures pinned vs. remote SHAs

- **GIVEN** a parent repository whose submodule pointer for `child` is at SHA `aaaa...`
- **AND** `child`'s `origin/main` head is at SHA `bbbb...`
- **WHEN** `cascade-pins plan` runs at the parent
- **THEN** the graph node for `child` has `pinned_sha == "aaaa..."` and `remote_sha == "bbbb..."`
- **AND** the planner classifies this node as outdated

#### Scenario: graph honours the --branch flag

- **WHEN** `cascade-pins plan --branch develop` runs
- **THEN** the per-node remote SHA is read from `origin/develop`, not `origin/main`

### Requirement: Topological cascade order

`cascade-pins run` SHALL execute pin bumps in deepest-first topological order. A parent's bump SHALL NOT begin until each of its children that appears in the plan has been pushed (when `--push` is set) or at least committed (when `--push` is not set). Sibling bumps that share a parent SHALL be bundled into a single parent commit.

#### Scenario: leaf-first ordering

- **GIVEN** a graph with three layers (umbrella → beholder → comprehender-common) where `comprehender-common` has unpushed commits
- **WHEN** `cascade-pins run --push` executes
- **THEN** `comprehender-common`'s push happens first
- **AND** `beholder`'s pin-bump commit and push happen next
- **AND** `umbrella`'s pin-bump commit and push happen last

#### Scenario: sibling bumps bundled in one parent commit

- **GIVEN** `beholder` has TWO outdated children (`mtproto-kit` and `comprehender-common`)
- **WHEN** `cascade-pins run` executes
- **THEN** `beholder` receives exactly ONE commit that bumps both children's pins
- **AND** the commit's message body lists both children's old/new SHA prefixes

### Requirement: Conditional uv.lock handling

When a parent has a `pyproject.toml` and `--no-uv-lock` is not set, `cascade-pins run` SHALL invoke `uv lock` in that parent after fast-forwarding its nested checkouts. If `uv.lock` is modified by the lock run, it SHALL be staged alongside the submodule pointers; if unchanged, it SHALL NOT be staged. If `uv lock` exits nonzero (resolution conflict, unsatisfiable workspace), `cascade-pins run` SHALL bail with the verbatim `uv` error and SHALL NOT roll back commits already made for parents earlier in the plan.

#### Scenario: uv.lock unchanged after pin bump

- **GIVEN** a parent whose `pyproject.toml` is unchanged and whose pin bump produces no transitive resolution changes
- **WHEN** `cascade-pins run` executes for that parent
- **THEN** `uv lock` runs successfully
- **AND** `uv.lock` is unchanged (`git diff --quiet uv.lock` succeeds)
- **AND** only the submodule pointer is staged for the commit

#### Scenario: uv.lock conflict bails the run

- **GIVEN** a workspace where `uv lock` reports an unsatisfiability error
- **WHEN** `cascade-pins run` reaches the affected parent
- **THEN** the tool exits nonzero immediately
- **AND** any commits made for earlier parents in this run remain in place
- **AND** the working tree of the failing parent is left unstaged for operator inspection

### Requirement: Push gate

`cascade-pins run` without `--push` SHALL commit each parent's pin bump but SHALL NOT push. The tool SHALL emit a final summary listing each parent that received a commit and the suggested push command.

`cascade-pins run --push` SHALL push each parent's branch to its remote after the parent's commit succeeds. A push rejection SHALL abort the run; subsequent parents in the plan are not processed.

#### Scenario: --push omitted leaves commits unpushed

- **GIVEN** an outdated graph
- **WHEN** `cascade-pins run` executes (no `--push`)
- **THEN** every affected parent has a new commit on its local `main`
- **AND** none of those commits has been pushed
- **AND** stdout lists the affected parent paths and the suggested `git -C <path> push` command for each

### Requirement: Idempotency

`cascade-pins run` invoked when no node is outdated SHALL exit 0 with a message like "no bumps needed" and SHALL produce no commits.

#### Scenario: second run after success is a no-op

- **GIVEN** a graph that was just cascaded successfully
- **WHEN** `cascade-pins run` is invoked again
- **THEN** the tool exits 0 with "no bumps needed"
- **AND** the working tree is unchanged

### Requirement: Drift detection

`cascade-pins drift` SHALL walk the graph at the configured root and group nodes by basename. If two or more nodes in the same basename group have different pinned SHAs, the tool SHALL print a structured report listing each conflicting group with its SHAs and paths, and exit nonzero. Otherwise it SHALL exit 0 with "no drift".

#### Scenario: same-name submodule at two different SHAs

- **GIVEN** a graph where `comprehender-common` appears as a nested submodule of both `beholder` and `backoffice` at different pinned SHAs
- **WHEN** `cascade-pins drift` runs
- **THEN** the tool prints a structured report listing `comprehender-common` with both SHAs and both parent paths
- **AND** exits nonzero

#### Scenario: clean graph

- **GIVEN** a graph where every same-name group has a single SHA
- **WHEN** `cascade-pins drift` runs
- **THEN** the tool prints "no drift" and exits 0

### Requirement: Templated commit messages

Each pin-bump commit's message body SHALL be templated from per-bump information: each bumped child name and its old/new SHA prefixes (7 chars each), the subjects of the child's commits introduced by the bump (`git log <old>..<new> --pretty=%s`), and (best-effort) the names of OpenSpec changes archived in the child since the previous pin (computed by listing the child's `openspec/changes/archive/` directory and filtering to entries created since the old SHA). The first line of the message SHALL be `Bump <comma-separated-child-names> pins` with an optional summary appended after a colon.

The operator MAY override the templated body via `cascade-pins run --message "..."`; the synthesised first line is preserved unless the operator's message starts with one of the recognised first-line prefixes.

#### Scenario: message body lists archived changes

- **GIVEN** a `child` repo whose pin bump from `aaa..bbb` introduces commits that archived two OpenSpec changes (`change-A`, `change-B`)
- **WHEN** `cascade-pins run` commits the parent's pin bump
- **THEN** the parent's commit message body includes a section like `child @ aaa..bbb` followed by the changed-commit subjects
- **AND** that section ends with `(archived: change-A, change-B)`

#### Scenario: message body for spec-only bump (no archives)

- **GIVEN** a child whose bump introduces only one commit, an `Open <change-name>` proposal commit (no archives)
- **WHEN** the parent's pin bump commits
- **THEN** the message body lists the proposal commit's subject
- **AND** the `(archived: ...)` section is omitted

### Requirement: Out-of-scope behaviour

`cascade-pins` SHALL NOT perform server-side automation, auto-merge `uv.lock` conflicts, rebase or rewrite commit history, run cross-repo CI orchestration, or replace the umbrella's `just status` recipe (which surfaces a different view: pinned vs. local SHAs, not pinned vs. remote-main SHAs).

#### Scenario: tool refuses to rewrite history

- **GIVEN** a parent repo with existing pin-bump commits on `main`
- **WHEN** `cascade-pins run` runs
- **THEN** the tool only adds new commits on top of `main`
- **AND** does not amend, squash, or rebase any prior commit
