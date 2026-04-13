mod just 'just.just'
mod git 'git.just'

source_file := source_file()

# List all available recipes
[default]
list: (just::list source_file)

# Sync submodule URLs recursively
[no-cd]
sync:
    git submodule sync --recursive

# Show remote tracking branches for all submodules
[no-cd]
remote-branch:
    git submodule foreach --recursive "just --justfile {{ source_file }} git::remote-branch; echo"

# Show remote names for all submodules
[no-cd]
remote-name:
    git submodule foreach --recursive "just --justfile {{ source_file }} git::remote-name; echo"

# Show remote branch and URL for all submodules
[no-cd]
remote:
    git submodule foreach --recursive "just --justfile {{ module_file() }} git::remote; echo"

# Add a git submodule to the repository
[no-cd]
add url path branch:
    git submodule add -b {{ branch }} {{ url }} {{ path }}
    git submodule init {{ path }}

# Remove a git submodule from the repository
[no-cd]
remove path:
    git submodule deinit -f {{ path }}
    git rm -f {{ path }}
    rm -rf .git/modules/{{ path }}

# Set the tracking branch for a submodule and update it
[no-cd]
set-branch submodule branch *args="--rebase":
    git config --file .gitmodules submodule.{{ submodule }}.branch {{ branch }}
    git submodule update --remote {{ args }}
    cd {{ submodule }}; git switch {{ branch }}

# Show status of git submodules
[no-cd]
status *args="--recursive":
    git submodule status {{ args }}

# Show verbose status of git submodules
[no-cd]
status-verbose *args="--untracked-files=all":
    git submodule foreach --recursive "git status --short --branch {{ args }}; echo"

# Update all git submodules recursively
[no-cd]
update:
    git submodule update --init --recursive

# Pull all git submodules recursively
[no-cd]
fetch *args:
    git submodule foreach --recursive "git fetch --all {{ args }}; echo"

# Pull all git submodules recursively
[no-cd]
pull *args:
    git submodule foreach --recursive "git pull {{ args }}; echo"

# Push all git submodules recursively
[no-cd]
push *args:
    git submodule foreach --recursive "git push {{ args }}; echo"
