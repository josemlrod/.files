# .files

Config for the tools I use for development every day.

Each tool gets its own folder. The live config path on my machine is a symlink into this repo, so editing the config edits the repo. To save a change, commit and push from `~/.files`.

## Tools

| Tool | File in repo | Linked from |
| --- | --- | --- |
| Rex | `rex/init.lua` | `~/.config/rex/init.lua` |
| Claude Code, Cursor, OpenCode | `agents/` | `~/.agents/`, `~/.claude/`, `~/.cursor/`, `~/.config/opencode/`. See [agents/README.md](agents/README.md). |

## Rex appearance

Rex keeps its theme, font, and layout settings in macOS preferences, not in `init.lua`. `rex/defaults.sh` writes them back with `defaults write`. It covers the light and dark themes, the terminal font and size, the tab style, the sidebar, pane density, and animation style.

The symlink keeps `init.lua` in sync, but nothing does that for these settings. After changing one in Rex's settings window, update the repo:

```sh
~/.files/rex/save-defaults.sh
cd ~/.files && git commit -am "rex: update appearance" && git push
```

The terminal font is 0xProto Nerd Font Mono. Install it before applying the settings.

## Setting up a new machine

```sh
git clone https://github.com/josemlrod/.files.git ~/.files
mkdir -p ~/.config/rex
ln -sf ~/.files/rex/init.lua ~/.config/rex/init.lua

brew install --cask font-0xproto-nerd-font
# Quit Rex first, then:
~/.files/rex/defaults.sh
```

For the agent setup, run `~/.files/agents/install.py` after cloning. It links its own files and merges its hook entries into the agents' configs.
