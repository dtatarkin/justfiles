mod just
mod git
mod git-submodule
mod pre-commit

source_file := source_file()

# List all available recipes
[default]
list: (just::list source_file)

# Run a command in project environment
run *args:
    uv run {{ args }}

# Run pre-commit hooks for all files
lint: pre-commit::run
