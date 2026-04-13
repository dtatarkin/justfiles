mod just 'just.just'

source_file := source_file()

# List all available recipes
[default]
list: (just::list source_file)

# Show the remote name for the current branch
[no-cd]
remote-name:
    @git config --get branch.$(git branch --show-current).remote

# Show the remote tracking branch
[no-cd]
remote-branch:
    @git rev-parse --abbrev-ref --symbolic-full-name @{u}

# Show the remote URL for the current branch
[no-cd]
remote-url:
    @git remote get-url $(just --justfile {{ source_file }} remote-name)

# Show remote branch and URL
[no-cd]
remote:
    @cd {{ invocation_directory() }}; echo {{ YELLOW }}$(just --justfile {{ module_file() }} remote-branch) {{ GREEN }}$(just --justfile {{ module_file() }} remote-url){{ NORMAL }}

# Fetch all remotes and tags
[no-cd]
fetch *args:
    git fetch --all --tags {{ args }}

# Push with submodule check
[no-cd]
push *args:
    git push --recurse-submodules=on-demand {{ args }}

# Pull with submodule check
[no-cd]
pull *args:
    git pull --all --jobs 2 --tags --recurse-submodules --ff-only {{ args }}

# Add a new git worktree for the given commit-ish
[no-cd]
worktree-add name commit-ish *options:
    git worktree add {{ options }} ../{{ name }}-{{ commit-ish }} {{ commit-ish }}

# List all git worktrees
[no-cd]
worktree-list *args:
    git worktree list {{ args }}
