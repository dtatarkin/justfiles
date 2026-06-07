mod just 'just.just'

source_file := source_file()

[default]
[doc("List all available recipes")]
list: (just::list source_file)

[doc("Show the remote name for the current branch")]
[no-cd]
remote-name:
    @git config --get branch.$(git branch --show-current).remote

[doc("Show the remote tracking branch")]
[no-cd]
remote-branch:
    @git rev-parse --abbrev-ref --symbolic-full-name @{u}

[doc("Show the remote URL for the current branch")]
[no-cd]
remote-url:
    @git remote get-url $(just --justfile {{ source_file }} remote-name)

[doc("Show remote branch and URL")]
[no-cd]
remote:
    @cd {{ invocation_directory() }}; echo {{ YELLOW }}$(just --justfile {{ module_file() }} remote-branch) {{ GREEN }}$(just --justfile {{ module_file() }} remote-url){{ NORMAL }}

[doc("Fetch all remotes and tags")]
[no-cd]
fetch *args:
    git fetch --all --tags {{ args }}

[doc("Push with submodule check")]
[no-cd]
push *args:
    git push --recurse-submodules=on-demand {{ args }}

[doc("Pull with submodule check")]
[no-cd]
pull *args:
    git pull --all --jobs 2 --tags --ff-only {{ args }}

[doc("Add a new git worktree for the given commit-ish")]
[no-cd]
worktree-add name commit-ish *options:
    git worktree add {{ options }} ../{{ name }}-{{ commit-ish }} {{ commit-ish }}

[doc("List all git worktrees")]
[no-cd]
worktree-list *args:
    git worktree list {{ args }}
