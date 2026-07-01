mod just
mod git
mod git-submodule
mod pre-commit

source_file := source_file()

[default]
[doc("List all available recipes")]
list: (just::list source_file)

[doc("Run a command in the project environment")]
run *args:
    uv run {{ args }}

[doc("Run tests with pytest")]
test *args: (run "pytest" args)

[doc("Run pre-commit hooks for all files")]
lint: pre-commit::run

[doc("Push to the remote")]
push *args:
    git push {{ args }}
