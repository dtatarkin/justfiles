mod just 'just.just'

source_file := source_file()

# List all available recipes
[default]
list: (just::list source_file)

# Read workspace member directory names (space-separated) from `pyproject.toml`
# in the consumer's working directory. Internal helper for other recipes.
[private]
[no-cd]
_members:
    @python3 -c "import tomllib, pathlib; cfg = tomllib.loads(pathlib.Path('pyproject.toml').read_text()); print(*cfg['tool']['uv']['workspace']['members'])"

# Use BEFORE editing files inside a workspace-member submodule so commits
# land on a real branch, not a dangling HEAD. `member` may be a workspace
# member name or `all` (all members listed in pyproject.toml).
#
# Switch a workspace-member submodule to its tracking branch (main) and fast-forward
[no-cd]
edit member:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ "{{ member }}" = "all" ]; then
        members=$(just --justfile {{ source_file }} _members)
    else
        members="{{ member }}"
    fi
    for m in $members; do
        echo "=== $m ==="
        (cd "$m" && git switch main && git pull --ff-only)
    done

# Show pinned-vs-current SHA and working-tree state for each workspace member.
[no-cd]
status:
    #!/usr/bin/env bash
    set -euo pipefail
    members=$(just --justfile {{ source_file }} _members)
    git submodule status $members

# Use AFTER `edit` (or manual `git checkout`) inside a member, and after
# any changes inside the member have been pushed to its upstream. Doesn't
# push this repo. `member` may be a member name or `all` (one bump commit
# per advanced member).
#
# Capture a workspace-member submodule's current SHA as a new pin in this repo
[no-cd]
bump member:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ "{{ member }}" = "all" ]; then
        members=$(just --justfile {{ source_file }} _members)
    else
        members="{{ member }}"
    fi
    bumped=0
    for m in $members; do
        current=$(git -C "$m" rev-parse HEAD)
        pinned=$(git ls-tree HEAD "$m" | awk '{print $3}')
        if [ "$current" = "$pinned" ]; then
            echo "$m: no bump (pin matches HEAD)"
            continue
        fi
        short=$(git -C "$m" rev-parse --short=12 HEAD)
        git add "$m"
        git commit -m "Bump $m pin to $short"
        bumped=$((bumped + 1))
    done
    if [ "$bumped" -eq 0 ]; then
        echo "Nothing to bump."
    fi
