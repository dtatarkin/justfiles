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
[positional-arguments]
fetch *args:
    git fetch --all --tags "$@"

[doc("Push with submodule check")]
[no-cd]
[positional-arguments]
push *args:
    git push --recurse-submodules=on-demand "$@"

[doc("Pull with submodule check")]
[no-cd]
[positional-arguments]
pull *args:
    git pull --all --jobs 2 --tags --ff-only "$@"

# Run from the main checkout. The worktree goes into the repository's lane
# directory, `../<repo>.lanes/<name>`: one directory beside the checkout, named
# after it, holding every worktree an agent works in, so a listing of the parent
# says which project a worktree belongs to and that it is a lane. A new worktree
# starts with every submodule empty, and whatever it builds or lints may need them.

[doc("Add a git worktree for the given commit-ish at ../<repo>.lanes/<name>, with its submodules initialised")]
[no-cd]
[positional-arguments]
worktree-add name commit-ish *options:
    #!/usr/bin/env bash
    set -euo pipefail
    name=$1; commit_ish=$2; shift 2
    top=$(git rev-parse --show-toplevel)
    path="$(dirname "$top")/$(basename "$top").lanes/$name"
    git worktree add "$@" "$path" "$commit_ish"
    git -C "$path" submodule update --init --recursive

# Run from the main checkout. A rebase then a fast-forward, never a merge commit
# or a squash, so each commit of the branch survives and they stay contiguous.
# The rebase rewrites their SHAs, hence the list printed at the end.
#
# A rebase conflict is a judgment call: the recipe stops there, with the worktree
# mid-rebase and the default branch unmoved. Resolve it in the worktree, finish
# the rebase, and run the recipe again.
#
# `git worktree remove` refuses a worktree with initialised submodules, and the
# `--force` that gets past it also discards what only that worktree holds. So
# the recipe first refuses uncommitted work and submodule commits no remote has;
# ignored files count as disposable.
#
# The main checkout is the one whose git directory is the common one. Its path
# is not `git worktree list`'s first entry: in a submodule that entry is the
# git directory under the superproject's `.git/modules`, and the work tree is
# what its `core.worktree` names.
#
# The default branch is what the remotes' HEADs name, whatever the remotes are
# called; a repository with no remote HEAD takes the main checkout's branch.
#
# The worktree's parent, the lane directory `worktree-add` made, goes with the
# last worktree in it; a parent holding anything else is left alone.

[doc("Land a worktree's branch on the default branch by rebase and fast-forward, then delete the branch and worktree")]
[no-cd]
[positional-arguments]
worktree-land branch:
    #!/usr/bin/env bash
    set -euo pipefail
    branch=$1
    common=$(git rev-parse --path-format=absolute --git-common-dir)
    main=$(git -C "$common" rev-parse --show-toplevel 2>/dev/null || dirname "$common")
    default=$(git for-each-ref --format='%(symref:lstrip=3)' 'refs/remotes/*/HEAD' | sort -u)
    default=${default:-$(git -C "$main" branch --show-current)}
    if [[ $(git rev-parse --path-format=absolute --git-dir) != "$common" || $(git branch --show-current) != "$default" ]]; then
        echo "worktree-land: run from the main checkout, $main, on $default" >&2
        exit 1
    fi
    worktree=$(git worktree list --porcelain | awk -v ref="branch refs/heads/$branch" '/^worktree /{n++; path=substr($0,10)} n>1 && $0==ref{print path}')
    if [[ -z $worktree ]]; then
        echo "worktree-land: no linked worktree has $branch checked out; mid-rebase it shows as detached, so finish the rebase there first" >&2
        exit 1
    fi
    at_risk=$(
        git -C "$worktree" status --porcelain --ignore-submodules=all
        git -C "$worktree" submodule foreach --quiet --recursive \
            'if [ -n "$(git status --porcelain; git rev-list --max-count=1 HEAD --branches --not --remotes)" ]; then echo "$displaypath"; fi'
    )
    if [[ -n $at_risk ]]; then
        printf 'worktree-land: %s holds uncommitted work or unpushed submodule commits:\n%s\n' "$worktree" "$at_risk" >&2
        exit 1
    fi
    if ! git -C "$worktree" rebase "$default"; then
        echo "worktree-land: the rebase stopped: $default has not moved and $worktree is left mid-rebase; resolve it there, then rerun" >&2
        exit 1
    fi
    landed=$(git log --reverse --format='%h %s' "$default..$branch")
    git merge --quiet --ff-only "$branch"
    printf 'Landed on %s:\n%s\n' "$default" "$landed"
    git worktree remove --force "$worktree"
    git branch --quiet --delete "$branch"
    rmdir "$(dirname "$worktree")" 2>/dev/null || true

[doc("List all git worktrees")]
[no-cd]
[positional-arguments]
worktree-list *args:
    git worktree list "$@"
