# .files

Config for the tools I use for development every day.

Each tool gets its own folder. The live config path on my machine is a symlink into this repo, so editing the config edits the repo. To save a change, commit and push from `~/.files`.

## Tools

| Tool | File in repo | Linked from |
| --- | --- | --- |
| Rex | `rex/init.lua` | `~/.config/rex/init.lua` |

## Setting up a new machine

```sh
git clone https://github.com/josemlrod/.files.git ~/.files
mkdir -p ~/.config/rex
ln -sf ~/.files/rex/init.lua ~/.config/rex/init.lua
```
