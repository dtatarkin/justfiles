mod just 'just.just'

source_file := source_file()
source_dir := parent_directory(source_file)

# List all available recipes
[default]
list: (just::list source_file)

# First invocation builds the cascade-pins tool into uv's tool cache;
# subsequent runs hit the cache. Pass any extra cascade-pins flags as args.
#
# Print the cascade plan (no side effects).
[no-cd]
cascade-plan *args:
    uv tool run --with file://{{ source_dir }} cascade-pins plan {{ args }}

# First invocation builds the cascade-pins tool into uv's tool cache;
# subsequent runs hit the cache.
#
# Execute the cascade (commit pin bumps; opt into pushing via cascade-push).
[no-cd]
cascade *args:
    uv tool run --with file://{{ source_dir }} cascade-pins run {{ args }}

# First invocation builds the cascade-pins tool into uv's tool cache;
# subsequent runs hit the cache.
#
# Execute the cascade and push each parent after its commit.
[no-cd]
cascade-push *args:
    uv tool run --with file://{{ source_dir }} cascade-pins run --push {{ args }}

# First invocation builds the cascade-pins tool into uv's tool cache;
# subsequent runs hit the cache.
#
# Structured drift report across the recursive submodule graph.
[no-cd]
check-drift *args:
    uv tool run --with file://{{ source_dir }} cascade-pins drift {{ args }}

# First invocation builds the cascade-pins tool into uv's tool cache;
# subsequent runs hit the cache.
#
# Show pinned vs. remote SHAs per node.
[no-cd]
cascade-status *args:
    uv tool run --with file://{{ source_dir }} cascade-pins status {{ args }}
