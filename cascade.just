mod just 'just.just'

source_file := source_file()
source_dir := parent_directory(source_file)

# List all available recipes
[default]
list: (just::list source_file)

# Run cascade-pins as a Python module straight from source via PYTHONPATH.
# `uv tool run --from file://...` was rejected: uv hashes the wheel cache by
# source path + package version (`0.1.0dev0`), so source edits land in a new
# pin but uv still serves the old cached wheel from
# `~/.cache/uv/sdists-v9/path/<path-hash>/.../justfiles-0.1.0.dev0.whl`. None
# of --refresh-package, --reinstall-package, --reinstall, or --no-cache
# invalidate it. Direct module invocation sidesteps the build/cache layer
# entirely. cascade-pins has zero runtime deps, so PYTHONPATH alone is
# sufficient. `uv run --no-project --python ">=3.12"` just guarantees a
# 3.12+ interpreter without touching the calling project's environment.
#
# Print the cascade plan (no side effects).
[no-cd]
cascade-plan *args:
    PYTHONPATH={{ source_dir }}/src uv run --no-project --python ">=3.12" python -m cascade_pins plan {{ args }}

# Execute the cascade (commit pin bumps; opt into pushing via cascade-push).
[no-cd]
cascade *args:
    PYTHONPATH={{ source_dir }}/src uv run --no-project --python ">=3.12" python -m cascade_pins run {{ args }}

# Execute the cascade and push each parent after its commit.
[no-cd]
cascade-push *args:
    PYTHONPATH={{ source_dir }}/src uv run --no-project --python ">=3.12" python -m cascade_pins run --push {{ args }}

# Structured drift report across the recursive submodule graph.
[no-cd]
check-drift *args:
    PYTHONPATH={{ source_dir }}/src uv run --no-project --python ">=3.12" python -m cascade_pins drift {{ args }}

# Show pinned vs. remote SHAs per node.
[no-cd]
cascade-status *args:
    PYTHONPATH={{ source_dir }}/src uv run --no-project --python ">=3.12" python -m cascade_pins status {{ args }}
