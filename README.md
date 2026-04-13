# 🛠️ Justfiles

A modular collection of [just](https://github.com/casey/just) recipes to supercharge your development workflow.

[![Just](https://img.shields.io/badge/just-ready-orange.svg)](https://github.com/casey/just)

## ✨ Features

- **Modular Design:** Import only what you need (Git, Pre-commit, Just utilities, ...).
- **Pre-commit Ready:** Automated formatting and validation for your justfiles.
- **Git Workflows:** Fetch, pull, push with submodule-aware defaults.
- **Submodule Management:** Add, remove, update, and inspect git submodules.
- **Worktree Support:** Create and list git worktrees.

## 🚀 Getting Started

### Prerequisites

- [just](https://github.com/casey/just#installation)

### For Development

- [uv](https://docs.astral.sh/uv/getting-started/installation/) (Required for pre-commit hooks and environment management)

## 🚀 Recommended Setup

The best way to use these recipes in your own project is by adding this repository as a git submodule. This allows you to keep the recipes updated and choose exactly which modules to import.

### 1. Add as a Submodule

In your project's root directory:

```bash
git submodule add https://github.com/dtatarkin/justfiles.git justfiles
```

### 2. Import Modules

In your main `justfile`, use `mod` to add namespaced modules:

```just
mod git 'justfiles/git.just'
mod pre-commit 'justfiles/pre-commit.just'
```

### 3. Update Recipes

To get the latest improvements:

```bash
git submodule update --remote justfiles
```

## 📦 Modules

### Root (`justfile`)

| Recipe | Description |
|--------|-------------|
| `just list` | List all available recipes |
| `just run *args` | Run a command in project environment via `uv run` |
| `just lint` | Run pre-commit hooks for all files |

### Git (`git.just`)

| Recipe | Description |
|--------|-------------|
| `just git fetch` | Fetch all remotes and tags |
| `just git pull` | Pull with submodule check (fast-forward only) |
| `just git push` | Push with submodule check |
| `just git remote` | Show remote branch and URL |
| `just git remote-branch` | Show the remote tracking branch |
| `just git remote-name` | Show the remote name for the current branch |
| `just git remote-url` | Show the remote URL for the current branch |
| `just git worktree-add` | Add a new git worktree for the given commit-ish |
| `just git worktree-list` | List all git worktrees |

### Git Submodule (`git-submodule.just`)

| Recipe | Description |
|--------|-------------|
| `just git-submodule add` | Add a git submodule to the repository |
| `just git-submodule remove` | Remove a git submodule from the repository |
| `just git-submodule set-branch` | Set the tracking branch for a submodule and update it |
| `just git-submodule sync` | Sync submodule URLs recursively |
| `just git-submodule status` | Show status of git submodules |
| `just git-submodule status-verbose` | Show verbose status of git submodules |
| `just git-submodule update` | Update all git submodules recursively |
| `just git-submodule fetch` | Fetch all git submodules recursively |
| `just git-submodule pull` | Pull all git submodules recursively |
| `just git-submodule push` | Push all git submodules recursively |
| `just git-submodule remote` | Show remote branch and URL for all submodules |
| `just git-submodule remote-branch` | Show remote tracking branches for all submodules |
| `just git-submodule remote-name` | Show remote names for all submodules |

### Pre-commit (`pre-commit.just`)

| Recipe | Description |
|--------|-------------|
| `just pre-commit install` | Install the git hook scripts |
| `just pre-commit uninstall` | Uninstall the git hook scripts |
| `just pre-commit run` | Run all pre-commit hooks (defaults to `--all-files`) |
| `just pre-commit autoupdate` | Update pre-commit hooks to latest versions |
| `just pre-commit validate` | Validate pre-commit config and manifest |

### Just Utilities (`just.just`)

| Recipe | Description |
|--------|-------------|
| `just just format` | Format justfile |
| `just just bash-completion` | Configure completion for the Bash shell (Linux) |

## 🛠️ Usage

Simply run `just` to see the available recipes:

```bash
just
```

## 🤝 Contributing

Feel free to open issues or submit pull requests with new modules or improvements!
