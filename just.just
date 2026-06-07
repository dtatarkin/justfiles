source_file := source_file()

[default]
[doc("List all available recipes")]
list justfile=source_file:
    just --justfile {{ justfile }} --list

[doc("Format justfile")]
[no-cd]
format justfile=source_file:
    just --fmt --unstable --justfile {{ justfile }}

[doc("Configure completion for the Bash shell")]
[linux]
bash-completion:
    just --completions bash > ~/.bashrc.d/just.sh
