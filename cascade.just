mod just 'just.just'

source_file := source_file()
source_dir := parent_directory(source_file)

# List all available recipes
[default]
list: (just::list source_file)

# `--refresh-package justfiles` forces uv to re-resolve and re-build the
# tool from {{ source_dir }} on each invocation. Without it, uv keys its
# cache on the package version (`0.1.0dev0`), so a submodule pin bump that
# brings in new cascade-pins source would still hit the old cached archive.
# Cost: ~1s rebuild (no runtime deps), paid by every cascade invocation.
#
# Print the cascade plan (no side effects).
[no-cd]
cascade-plan *args:
    uv tool run --refresh-package justfiles --from file://{{ source_dir }} cascade-pins plan {{ args }}

# Execute the cascade (commit pin bumps; opt into pushing via cascade-push).
[no-cd]
cascade *args:
    uv tool run --refresh-package justfiles --from file://{{ source_dir }} cascade-pins run {{ args }}

# Execute the cascade and push each parent after its commit.
[no-cd]
cascade-push *args:
    uv tool run --refresh-package justfiles --from file://{{ source_dir }} cascade-pins run --push {{ args }}

# Structured drift report across the recursive submodule graph.
[no-cd]
check-drift *args:
    uv tool run --refresh-package justfiles --from file://{{ source_dir }} cascade-pins drift {{ args }}

# Show pinned vs. remote SHAs per node.
[no-cd]
cascade-status *args:
    uv tool run --refresh-package justfiles --from file://{{ source_dir }} cascade-pins status {{ args }}
