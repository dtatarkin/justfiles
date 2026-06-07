mod just 'just.just'
mod git 'git.just'

source_file := source_file()

[default]
[doc("List all available recipes")]
list: (just::list source_file)

[doc("Sync submodule URLs recursively")]
[no-cd]
sync:
    git submodule sync --recursive

[doc("Show remote tracking branches for all submodules")]
[no-cd]
remote-branch:
    git submodule foreach --recursive "just --justfile {{ source_file }} git::remote-branch; echo"

[doc("Show remote names for all submodules")]
[no-cd]
remote-name:
    git submodule foreach --recursive "just --justfile {{ source_file }} git::remote-name; echo"

[doc("Show remote branch and URL for all submodules")]
[no-cd]
remote:
    git submodule foreach --recursive "just --justfile {{ module_file() }} git::remote; echo"

[doc("Add a git submodule to the repository")]
[no-cd]
add url path branch:
    git submodule add -b {{ branch }} {{ url }} {{ path }}
    git submodule init {{ path }}

[doc("Remove a git submodule from the repository")]
[no-cd]
remove path:
    git submodule deinit -f {{ path }}
    git rm -f {{ path }}
    rm -rf .git/modules/{{ path }}

[doc("Set the tracking branch for a submodule and update it")]
[no-cd]
set-branch submodule branch *args="--rebase":
    git config --file .gitmodules submodule.{{ submodule }}.branch {{ branch }}
    git submodule update --remote {{ args }}
    cd {{ submodule }}; git switch {{ branch }}

[doc("Show status of git submodules")]
[no-cd]
status *args="--recursive":
    git submodule status {{ args }}

[doc("Show verbose status of git submodules")]
[no-cd]
status-verbose *args="--untracked-files=all":
    git submodule foreach --recursive "git status --short --branch {{ args }}; echo"

[doc("Update all git submodules recursively")]
[no-cd]
update:
    git submodule update --init --recursive

[doc("Fetch all remotes in each submodule recursively")]
[no-cd]
fetch *args:
    git submodule foreach --recursive "git fetch --all {{ args }}; echo"

[doc("Pull all git submodules recursively")]
[no-cd]
pull *args:
    git submodule foreach --recursive "git pull {{ args }}; echo"

[doc("Push all git submodules recursively")]
[no-cd]
push *args:
    git submodule foreach --recursive "git push {{ args }}; echo"

[doc("Checkout the default branch in all submodules recursively")]
[no-cd]
checkout-default:
    git submodule foreach --recursive 'default=$(git symbolic-ref refs/remotes/origin/HEAD | sed "s@refs/remotes/origin/@@"); git checkout "$default"'
