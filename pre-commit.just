mod just 'just.just'

source_file := source_file()

[default]
[doc("List all available recipes")]
list: (just::list source_file)

[doc("Run pre-commit with custom arguments")]
[no-cd]
[positional-arguments]
pre-commit *args:
    just run pre-commit "$@"

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
