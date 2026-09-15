mod just 'just.just'

source_file := source_file()

[default]
[doc("List all available recipes")]
list: (just::list source_file)

# The prompt is a module variable so the recipe body stays short. `'''` is a raw
# string: the backticks and quotes inside it are literal.

commit_prompt := '''
Write a commit message for the changes that are already staged in this
repository, and commit them.

How to work:

1. Read the staged changes with `git diff --cached`. Use `git status --short`
   and `git log --oneline -20` for context, and read a file when the diff alone
   does not explain the change.
2. Follow this repository's own commit-message conventions — its CLAUDE.md,
   AGENTS.md or CONTRIBUTING.md, and the style of its recent log. Where nothing
   states a convention: a concise imperative subject under 72 characters, a
   blank line, then a body explaining why. Always English.
3. Commit with `git commit -m "<message>"`. Put the whole message in one or more
   `-m` values, with literal newlines inside the quoted value. Never build the
   message with a command substitution, a heredoc, `-F`, or an editor.

Hard rules:

- Commit exactly what is staged, nothing else. Never run `git add`, `git rm`,
  `git stash`, `git commit -a`, or anything else that changes what is staged.
- Never bypass the commit hooks: no `--no-verify`, no `-n`, no `SKIP=`, no
  `--amend`.
- Never push. Never create, switch or delete a branch.
- Never edit a file. The commit is your only write action.
- If nothing is staged, stop and say so. Never create an empty commit.
- If a hook fails or the commit is rejected, stop. Report what failed and quote
  the output. Do not restage hook-modified files, and do not retry with hooks
  disabled.

Finish with one line: the short hash and subject of the commit you made, or why
you made none.
'''

# Two flags carry a decision. `--model sonnet` is deliberate, and so is the
# absence of `--effort`: the default effort is the point. The prompt travels on
# stdin because `--allowedTools` is variadic and swallows a positional prompt
# that follows it.
#
# The allowlist is the whole permission posture: with `--permission-prompts
# none` nothing else can be approved, so an unlisted tool is denied rather than
# prompted. The `--disallowedTools` entries are redundant against that and are
# there for the case where the target repository's own settings allow more.
#
# A session that declines to commit — a hook rejected it, the diff made no sense
# — still exits 0, so the recipe compares HEAD itself and fails when nothing
# landed. Without that, `just … commit-staged && git push` would push nothing.

[doc("Commit the staged changes with a message written by headless Claude")]
[no-cd]
commit-staged:
    #!/usr/bin/env bash
    set -euo pipefail
    if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
        echo 'commit-staged: not a git repository' >&2
        exit 1
    fi
    base=$(git rev-parse --verify --quiet HEAD || git hash-object -t tree /dev/null)
    if git diff --cached --quiet "$base"; then
        echo 'commit-staged: nothing is staged' >&2
        exit 1
    fi
    before=$(git rev-parse --verify --quiet HEAD || true)
    printf '%s\n' {{ quote(commit_prompt) }} \
        | claude --print --model sonnet --strict-mcp-config --permission-prompts none \
            --allowedTools Read Grep Glob 'Bash(git status:*)' 'Bash(git diff:*)' 'Bash(git log:*)' 'Bash(git show:*)' 'Bash(git commit:*)' \
            --disallowedTools Edit Write 'Bash(git add:*)' 'Bash(git push:*)' 'Bash(git reset:*)' 'Bash(git commit --no-verify:*)' 'Bash(git commit -n:*)'
    if [ "$(git rev-parse --verify --quiet HEAD || true)" = "$before" ]; then
        echo 'commit-staged: no commit was made' >&2
        exit 1
    fi
