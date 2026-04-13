source_file := source_file()

# List all available recipes
[default]
list justfile=source_file:
    just --justfile {{ justfile }} --list

# Format justfile
[no-cd]
format justfile=source_file:
    just --fmt --unstable --justfile {{ justfile }}

# Configure completion for the Bash shell
[linux]
bash-completion:
    just --completions bash > ~/.bashrc.d/just.sh
