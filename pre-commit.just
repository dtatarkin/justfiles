mod just 'just.just'

source_file := source_file()

[default]
[doc("List all available recipes")]
list: (just::list source_file)

# No runner is named here. `pre-commit` and `prek` read the same configuration
# and share every subcommand this module calls, so which one runs is the
# consuming repository's choice: the one its own `run` recipe can start —
# `pre-commit` when that resolves, `prek` when it does not.
#
# `PRE_COMMIT_RUNNER` overrides the probe. It is an environment variable rather
# than a `just` one because the choice has to cross the nested `just` calls
# below, and a `--set` override stops at the first of them. A consuming justfile
# pins it with `export PRE_COMMIT_RUNNER := "prek"`.

[doc("Print the hook runner these recipes call")]
[no-cd]
runner:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ -n "${PRE_COMMIT_RUNNER:-}" ]; then
        echo "$PRE_COMMIT_RUNNER"
    elif just run pre-commit --version >/dev/null 2>&1; then
        echo pre-commit
    else
        echo prek
    fi

[doc("Run the hook runner with custom arguments")]
[no-cd]
[positional-arguments]
pre-commit *args:
    just run "$(just --justfile {{ source_file }} runner)" "$@"

[doc("Install the git hook scripts")]
install: (pre-commit "install")

[doc("Uninstall the git hook scripts")]
uninstall: (pre-commit "uninstall")

[doc("Update pre-commit hooks to latest versions")]
autoupdate: (pre-commit "autoupdate")

# A dependency call would space-join the variadic into a single argument, so
# this one forwards through a nested `just` instead: the user's arguments travel
# as real argv and keep their boundaries.

[doc("Run all pre-commit hooks")]
[no-cd]
[positional-arguments]
run *args="--all-files":
    just --justfile {{ source_file }} pre-commit run "$@"

[doc("Validate pre-commit config and manifest")]
validate: (pre-commit "validate-config") (pre-commit "validate-manifest")
