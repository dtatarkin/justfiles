mod just 'just.just'

source_file := source_file()

[default]
[doc("List all available recipes")]
list: (just::list source_file)

[doc("Run pre-commit with custom arguments")]
[no-cd]
pre-commit *args:
    just run pre-commit {{ args }}

[doc("Install the git hook scripts")]
install: (pre-commit "install")

[doc("Uninstall the git hook scripts")]
uninstall: (pre-commit "uninstall")

[doc("Update pre-commit hooks to latest versions")]
autoupdate: (pre-commit "autoupdate")

[doc("Run all pre-commit hooks")]
run *args="--all-files": (pre-commit "run" args)

[doc("Validate pre-commit config and manifest")]
validate: (pre-commit "validate-config") (pre-commit "validate-manifest")
