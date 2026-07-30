mod just
mod git
mod git-submodule
mod pre-commit

source_file := source_file()

[default]
[doc("List all available recipes")]
list: (just::list source_file)

[doc("Run a command in the project environment")]
[positional-arguments]
run *args:
    uv run "$@"

[doc("Run tests with pytest")]
[positional-arguments]
test *args:
    just --justfile {{ source_file }} run pytest "$@"

[doc("Run pre-commit hooks for all files")]
lint: pre-commit::run

[doc("Push to the remote")]
[positional-arguments]
push *args:
    git push "$@"
