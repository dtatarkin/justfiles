mod just 'just.just'

source_file := source_file()

# List all available recipes
[default]
list: (just::list source_file)

# Run pre-commit with custom arguments
[no-cd]
pre-commit *args:
    just run pre-commit {{ args }}

# Install the git hook scripts
install: (pre-commit "install")

# Uninstall the git hook scripts
uninstall: (pre-commit "uninstall")

# Update pre-commit hooks to latest versions
autoupdate: (pre-commit "autoupdate")

# Run all pre-commit hooks
run *args="--all-files": (pre-commit "run" args)

# Validate pre-commit config and manifest
validate: (pre-commit "validate-config") (pre-commit "validate-manifest")
