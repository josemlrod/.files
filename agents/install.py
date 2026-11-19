#!/usr/bin/env python3
"""Wire the agent setup in this folder into Claude Code, Cursor, and OpenCode.

    ./install.py                 link files and add hook entries
    ./install.py --dry-run       print what would change, change nothing
    ./install.py --uninstall     remove the links and hook entries this script adds
    ./install.py --agents claude,cursor

Files are symlinked, so editing them edits this repo. Config files shared with
other tools (settings.json, hooks.json, opencode.jsonc, CLAUDE.md, ~/.zshenv) are merged:
only this setup's entries are added or removed, and the rest is left alone.
Anything replaced is first copied to ~/.agents-install-backup/<timestamp>/.
Review data and per-machine rules live in ~/knowledge/review and are never
touched, except that local/rules.md is created empty when missing.
"""
import argparse
import datetime
import json
import os
import shlex
import shutil
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
HOME = Path.home()
SKILLS = ["pre-pr", "review-retro", "unslop", "show-me"]
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
BACKUP = HOME / ".agents-install-backup" / STAMP
LOCAL_RULES = HOME / "knowledge" / "review" / "local" / "rules.md"
# Agents' shells get these variables, which point git's hooks at ~/.agents/git-hooks:
# a read-only folder holding a read-only stub, _run, and one link to it per hook name.
# The stub runs review/git-hooks/_dispatch, which runs the review check on pushes and
# then each repo's own hooks. Git never rewrites the stub, so a hook installer an
# agent runs (lefthook, pre-commit, simple-git-hooks) can't rename, add, or write
# through anything there: it fails instead of replacing the gate.
GIT_HOOKS = HOME / ".agents" / "git-hooks"
DISPATCH = HOME / ".agents" / "review" / "git-hooks" / "_dispatch"
STUB_NAME = "_run"
REVIEW_DATA = HOME / "knowledge" / "review"
# Paths are written in at install time, so a command's HOME or REVIEW_DATA_DIR
# can't change which gate runs or which review data it reads. Test suites often
# change HOME; with this, hooks keep working and see the real state. Bash startup
# input (BASH_ENV, ENV, SHELLOPTS, BASHOPTS) is cleared, and `bash -p` also skips
# exported functions, so a `set -e; export SHELLOPTS` in a calling script can't
# make every hook fail.
STUB = f"""#!/bin/sh
# Written by ~/.files/agents/install.py. Every git hook name here links to this file.
REVIEW_HOOK_NAME=$(basename "$0") REVIEW_HOOK_DIR=$(cd "$(dirname "$0")" && pwd -P) \\
  exec /usr/bin/env -u BASH_ENV -u ENV -u SHELLOPTS -u BASHOPTS \\
  REVIEW_DATA_DIR={shlex.quote(str(REVIEW_DATA))} /bin/bash -p {shlex.quote(str(DISPATCH))} "$@"
"""
HOOK_NAMES = ("applypatch-msg pre-applypatch post-applypatch pre-commit pre-merge-commit prepare-commit-msg "
              "commit-msg post-commit pre-rebase post-checkout post-merge pre-push pre-receive update "
              "proc-receive post-receive post-update reference-transaction push-to-checkout pre-auto-gc "
              "post-rewrite sendemail-validate fsmonitor-watchman p4-changelist p4-prepare-changelist "
              "p4-post-changelist p4-pre-submit post-index-change").split()
GIT_ENV = {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.hooksPath", "GIT_CONFIG_VALUE_0": str(GIT_HOOKS)}
OLD_HOOKS_VALUES = {str(HOME / ".agents" / "review" / "git-hooks")}  # earlier installs pointed here
ZSHENV = HOME / ".zshenv"
ZSHENV_START = "# >>> agent review gate (managed by ~/.files/agents/install.py) >>>"
ZSHENV_END = "# <<< agent review gate <<<"
ZSHENV_BLOCK = f"""{ZSHENV_START}
# Cursor's agent shells set CURSOR_AGENT, and OpenCode's bash tool sets
# OPENCODE_SESSION_ID. In those shells, point git's hooks at the review gate.
# Your own terminals, including OpenCode's terminal panel, don't set either.
if [ -n "${{CURSOR_AGENT:-}}${{OPENCODE_SESSION_ID:-}}" ]; then
  export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.hooksPath GIT_CONFIG_VALUE_0="$HOME/.agents/git-hooks"
fi
{ZSHENV_END}
"""
LOCAL_RULES_HEADER = """# Code review workflow: rules for this machine

Loaded after `~/.agents/review/RULES.md` in every agent session. Rules here are
specific to this machine's repos and are never committed. The review-retro skill
adds rules here when you approve them.
"""

DRY = False
CHANGES = []


def say(action, what):
    CHANGES.append(action)
    print(f"  {action:<8} {what}")


def rel(p):
    p = Path(p)
    return "~/" + str(p.relative_to(HOME)) if p.is_relative_to(HOME) else str(p)


def backup(path):
    """Move or copy `path` under BACKUP, keeping its path relative to HOME."""
    dest = BACKUP / Path(path).relative_to(HOME)
    if DRY:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    if Path(path).is_symlink() or Path(path).is_file():
        shutil.copy2(path, dest, follow_symlinks=False)
    else:
        shutil.copytree(path, dest, symlinks=True)
    return dest


# ---------------------------------------------------------------- symlinks

def link(dest, target=None, src=None):
    """Make `dest` a symlink to `target` (default: absolute `src`)."""
    target = str(target or src)
    if dest.is_symlink() and os.readlink(dest) == target:
        print(f"  {'ok':<8} {rel(dest)}")
        return
    if dest.is_symlink() or dest.exists():
        say("backup", f"{rel(dest)} -> {rel(BACKUP / dest.relative_to(HOME))}")
        backup(dest)
        if not DRY:
            if dest.is_dir() and not dest.is_symlink():
                shutil.rmtree(dest)
            else:
                dest.unlink()
    say("link", f"{rel(dest)} -> {target if target.startswith('..') else rel(target)}")
    if not DRY:
        dest.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(target, dest)


def unlink(dest, target=None, src=None):
    target = str(target or src)
    if dest.is_symlink() and os.readlink(dest) == target:
        say("unlink", rel(dest))
        if not DRY:
            dest.unlink()


def shared_links():
    """Links every agent uses."""
    return [(SRC / "review", HOME / ".agents/review", None)] + \
        [(SRC / "skills" / s, HOME / ".agents/skills" / s, None) for s in SKILLS]


def links(agents):
    out = []
    if "claude" in agents:
        out += [(None, HOME / ".claude/skills" / s, f"../../.agents/skills/{s}") for s in SKILLS]
        out.append((SRC / "claude/hooks/unslop-context.sh", HOME / ".claude/hooks/unslop-context.sh", None))
    if "cursor" in agents:
        for f in ("unslop-context.sh", "review-rules.sh"):
            out.append((SRC / "cursor/hooks" / f, HOME / ".cursor/hooks" / f, None))
    if "opencode" in agents:
        out.append((SRC / "opencode/plugins/review-gate.js", HOME / ".config/opencode/plugins/review-gate.js", None))
        out.append((SRC / "opencode/AGENTS.md", HOME / ".config/opencode/AGENTS.md", None))
    return out


# ---------------------------------------------------------------- JSON configs

def read_json(path, default):
    if not path.exists():
        return default, True
    text = path.read_text()
    try:
        return json.loads(text), text.endswith("\n")
    except json.JSONDecodeError:
        return None, True


def write_json(path, data, newline, before):
    after = json.dumps(data, indent=2, ensure_ascii=False) + ("\n" if newline else "")
    if path.exists() and path.read_text() == after:
        return
    if before is not None and json.loads(after) == before:
        return
    if path.exists():
        backup(path)
    say("update", rel(path))
    if not DRY:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(after)


def claude_hooks():
    unslop = HOME / ".claude/hooks/unslop-context.sh"
    review = HOME / ".agents/review/bin/review"
    return {
        "SessionStart": ({"matcher": "*"}, {"type": "command", "command": f"bash '{unslop}' session", "timeout": 10}),
        "UserPromptSubmit": ({}, {"type": "command", "command": f"bash '{unslop}' prompt", "timeout": 10}),
        "PreToolUse": ({"matcher": "Bash"}, {"type": "command", "command": f"{review} hook claude-pre", "timeout": 30}),
        "PostToolUse": ({"matcher": "Edit|Write|MultiEdit"},
                        {"type": "command", "command": f"{review} hook claude-post", "timeout": 60}),
    }


def merge_claude_settings(uninstall):
    path = HOME / ".claude/settings.json"
    if uninstall and not path.exists():
        return
    data, newline = read_json(path, {})
    if data is None:
        say("skip", f"{rel(path)} is not valid JSON; add the hooks by hand (see agents/README.md)")
        return
    before = json.loads(json.dumps(data))
    env = data.setdefault("env", {})
    ours = {k: {v} | (OLD_HOOKS_VALUES if k == "GIT_CONFIG_VALUE_0" else set()) for k, v in GIT_ENV.items()}
    if uninstall:
        for k in GIT_ENV:
            if env.get(k) in ours[k]:
                del env[k]
    elif any(k in env and env[k] not in ours[k] for k in GIT_ENV):
        say("skip", f"{rel(path)} already sets GIT_CONFIG_* in env; point core.hooksPath at "
            f"{rel(GIT_HOOKS)} by hand so git runs the review check")
    else:
        env.update(GIT_ENV)
    if not env:
        del data["env"]
    hooks = data.setdefault("hooks", {})
    for event, (group_keys, hook) in claude_hooks().items():
        groups = hooks.setdefault(event, [])
        present = any(h.get("command") == hook["command"] for g in groups for h in g.get("hooks", []))
        if uninstall:
            for g in groups:
                g["hooks"] = [h for h in g.get("hooks", []) if h.get("command") != hook["command"]]
            hooks[event] = [g for g in groups if g.get("hooks")]
            if not hooks[event]:
                del hooks[event]
        elif not present:
            groups.append({**group_keys, "hooks": [hook]})
    if not hooks:
        del data["hooks"]
    write_json(path, data, newline, before if path.exists() else None)


def cursor_hooks():
    review = HOME / ".agents/review/bin/review"
    h = HOME / ".cursor/hooks"
    return {
        "sessionStart": [{"command": f"bash '{h / 'unslop-context.sh'}'"},
                         {"command": f"bash '{h / 'review-rules.sh'}'"}],
        "beforeShellExecution": [{"command": f"{review} hook cursor-shell", "timeout": 30}],
        "afterFileEdit": [{"command": f"{review} hook cursor-edit", "timeout": 60}],
    }


def merge_cursor_hooks(uninstall):
    path = HOME / ".cursor/hooks.json"
    if uninstall and not path.exists():
        return
    data, newline = read_json(path, {"version": 1, "hooks": {}})
    if data is None:
        say("skip", f"{rel(path)} is not valid JSON; add the hooks by hand (see agents/README.md)")
        return
    before = json.loads(json.dumps(data))
    hooks = data.setdefault("hooks", {})
    for event, entries in cursor_hooks().items():
        current = hooks.setdefault(event, [])
        ours = {e["command"] for e in entries}
        if uninstall:
            hooks[event] = [e for e in current if e.get("command") not in ours]
            if not hooks[event]:
                del hooks[event]
        else:
            have = {e.get("command") for e in current}
            current += [e for e in entries if e["command"] not in have]
    write_json(path, data, newline, before if path.exists() else None)


def merge_opencode(uninstall):
    base = HOME / ".config/opencode"
    path = next((p for p in (base / "opencode.jsonc", base / "opencode.json") if p.exists()),
                base / "opencode.jsonc")
    if uninstall and not path.exists():
        return
    ours = [str(HOME / ".agents/skills/unslop/SKILL.md"), str(HOME / ".agents/review/RULES.md"), str(LOCAL_RULES)]
    data, newline = read_json(path, {"$schema": "https://opencode.ai/config.json"})
    if data is None:
        say("skip", f"{rel(path)} has comments or is not plain JSON. Add these to \"instructions\" by hand: "
            + ", ".join(ours) + '; and set permission.skill["show-me"] to "ask".')
        return
    before = json.loads(json.dumps(data))
    instr = data.setdefault("instructions", [])
    # OpenCode allows `permission` and `permission.skill` to be a plain action string
    # such as "allow". Only an object can hold a per-skill rule.
    perm = data.get("permission", {})
    skill = perm.get("skill", {}) if isinstance(perm, dict) else None
    if uninstall:
        data["instructions"] = [i for i in instr if i not in ours]
        if not data["instructions"]:
            del data["instructions"]
        if isinstance(skill, dict) and skill.get("show-me") == "ask":
            del skill["show-me"]
            if not skill:
                del perm["skill"]
            if not perm:
                del data["permission"]
    else:
        instr += [i for i in ours if i not in instr]
        if isinstance(skill, dict):
            data.setdefault("permission", perm).setdefault("skill", skill).setdefault("show-me", "ask")
        else:
            say("skip", f'{rel(path)} sets permission as a string; set permission.skill["show-me"] to "ask" '
                "by hand if you want /show-me to ask first")
    write_json(path, data, newline, before if path.exists() else None)


# ---------------------------------------------------------------- CLAUDE.md

CLAUDE_IMPORTS = ["@~/.agents/review/RULES.md", "@~/knowledge/review/local/rules.md"]
CLAUDE_HEADING = "# Code review workflow"


def merge_claude_md(uninstall):
    path = HOME / ".claude/CLAUDE.md"
    text = path.read_text() if path.exists() else ""
    lines = text.split("\n")
    if uninstall:
        new = [l for l in lines if l.strip() not in CLAUDE_IMPORTS]
        # Drop the heading if nothing but blank lines follows it before the next heading.
        if CLAUDE_HEADING in new:
            i = new.index(CLAUDE_HEADING)
            j = i + 1
            while j < len(new) and not new[j].strip():
                j += 1
            if j == len(new) or new[j].startswith("#"):
                del new[i:j]
        out = "\n".join(new).rstrip("\n") + "\n" if any(l.strip() for l in new) else ""
    else:
        missing = [imp for imp in CLAUDE_IMPORTS if imp not in (l.strip() for l in lines)]
        if not missing:
            return
        if CLAUDE_IMPORTS[0] in lines:
            i = lines.index(CLAUDE_IMPORTS[0])
            lines[i + 1:i + 1] = missing
            out = "\n".join(lines)
        else:
            out = text.rstrip("\n") + ("\n\n" if text.strip() else "") + CLAUDE_HEADING + "\n\n" \
                + "\n".join(missing) + "\n"
    if out == text:
        return
    if path.exists():
        backup(path)
    say("update", rel(path))
    if not DRY:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(out)


# ---------------------------------------------------------------- main

def hooks_folder(uninstall):
    """Make (or remove) ~/.agents/git-hooks: a read-only stub, _run, and one link to it
    per git hook name, in a read-only folder. Git never touches the stub, so nothing
    a hook installer does can replace or write through to the gate."""
    stub = GIT_HOOKS / STUB_NAME
    dispatch = DISPATCH.resolve()
    if dispatch.exists() and not os.access(dispatch, os.W_OK) and not DRY:
        dispatch.chmod(0o755)  # an earlier install made the repo file read-only
    if uninstall:
        if not GIT_HOOKS.is_dir():
            return
        say("remove", rel(GIT_HOOKS))
        if not DRY:
            GIT_HOOKS.chmod(0o755)
            for p in GIT_HOOKS.iterdir():
                if (p.is_symlink() and os.readlink(p) in (STUB_NAME, str(DISPATCH))) or \
                        (p == stub and p.is_file() and not p.is_symlink()):  # any version of our stub
                    p.chmod(0o755) if not p.is_symlink() else None
                    p.unlink()
            if not any(GIT_HOOKS.iterdir()):
                GIT_HOOKS.rmdir()
        return
    entries = {p.name: p for p in GIT_HOOKS.iterdir()} if GIT_HOOKS.is_dir() else {}
    links_ok = all(entries.get(n) and entries[n].is_symlink() and os.readlink(entries[n]) == STUB_NAME
                   for n in HOOK_NAMES)
    stub_ok = stub.is_file() and not stub.is_symlink() and stub.read_text() == STUB and not os.access(stub, os.W_OK)
    extra = sorted(set(entries) - set(HOOK_NAMES) - {STUB_NAME})
    if links_ok and stub_ok and not extra and not os.access(GIT_HOOKS, os.W_OK):
        print(f"  {'ok':<8} {rel(GIT_HOOKS)}")
        return
    if extra:
        say("backup", f"{rel(GIT_HOOKS)}: {', '.join(extra)} (not ours)")
    say("update", f"{rel(GIT_HOOKS)} ({len(HOOK_NAMES)} hook links to a read-only stub)")
    if DRY:
        return
    if GIT_HOOKS.is_dir():
        GIT_HOOKS.chmod(0o755)
        for name in extra:
            p = GIT_HOOKS / name
            backup(p)
            shutil.rmtree(p) if p.is_dir() and not p.is_symlink() else p.unlink()
    GIT_HOOKS.mkdir(parents=True, exist_ok=True)
    if stub.exists() or stub.is_symlink():
        stub.chmod(0o755) if not stub.is_symlink() else None
        stub.unlink()
    stub.write_text(STUB)
    stub.chmod(0o555)
    for name in HOOK_NAMES:
        p = GIT_HOOKS / name
        if p.is_symlink() or p.exists():
            p.unlink()
        os.symlink(STUB_NAME, p)
    GIT_HOOKS.chmod(0o555)


def merge_zshenv(uninstall):
    """Add or remove the managed block in ~/.zshenv, which zsh reads for every shell,
    including the non-interactive ones Cursor and OpenCode run commands in."""
    text = ZSHENV.read_text() if ZSHENV.exists() else ""
    start, end = text.find(ZSHENV_START), text.find(ZSHENV_END)
    current = text[start:end + len(ZSHENV_END) + 1] if start >= 0 and end > start else None
    if uninstall:
        if current is None:
            return
        out = text.replace(current, "")
    elif current == ZSHENV_BLOCK:
        return
    elif current is not None:
        out = text.replace(current, ZSHENV_BLOCK)
    else:
        out = text + ("\n" if text and not text.endswith("\n") else "") + ZSHENV_BLOCK
    if ZSHENV.exists():
        backup(ZSHENV)
    say("update", rel(ZSHENV))
    if not DRY:
        ZSHENV.write_text(out)


def detect_agents():
    found = []
    if (HOME / ".claude").is_dir() or shutil.which("claude"):
        found.append("claude")
    if (HOME / ".cursor").is_dir() or shutil.which("cursor-agent"):
        found.append("cursor")
    if (HOME / ".config/opencode").is_dir() or shutil.which("opencode"):
        found.append("opencode")
    return found


def main():
    global DRY
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--uninstall", action="store_true")
    ap.add_argument("--agents", help="comma-separated subset of claude,cursor,opencode (default: the ones installed)")
    a = ap.parse_args()
    DRY = a.dry_run
    if sys.version_info < (3, 9):
        sys.exit("Needs Python 3.9 or newer.")
    agents = a.agents.split(",") if a.agents else detect_agents()
    bad = set(agents) - {"claude", "cursor", "opencode"}
    if bad:
        sys.exit(f"Unknown agent: {', '.join(sorted(bad))}")

    verb = "Uninstalling" if a.uninstall else "Installing"
    print(f"{verb} agent setup from {rel(SRC)} for: {', '.join(agents) or 'no agents found'}"
          + (" (dry run)" if DRY else ""))

    print("Links")
    # On a partial uninstall, keep the shared links while another installed agent uses them.
    others = sorted(set(detect_agents()) - set(agents)) if a.uninstall else []
    if others:
        print(f"  {'keep':<8} ~/.agents/review and ~/.agents/skills links, still used by {', '.join(others)}")
    for src, dest, target in ([] if others else shared_links()) + links(agents):
        (unlink if a.uninstall else link)(dest, target=target, src=src)
    if not others:
        hooks_folder(a.uninstall)

    print("Config")
    if "claude" in agents:
        merge_claude_settings(a.uninstall)
        merge_claude_md(a.uninstall)
    if "cursor" in agents:
        merge_cursor_hooks(a.uninstall)
    if "opencode" in agents:
        merge_opencode(a.uninstall)
    # One ~/.zshenv block covers Cursor and OpenCode; keep it while either is still installed.
    if {"cursor", "opencode"} & set(agents) and not (a.uninstall and {"cursor", "opencode"} & set(others)):
        merge_zshenv(a.uninstall)

    if not a.uninstall and not LOCAL_RULES.exists():
        say("create", rel(LOCAL_RULES))
        if not DRY:
            LOCAL_RULES.parent.mkdir(parents=True, exist_ok=True)
            LOCAL_RULES.write_text(LOCAL_RULES_HEADER)

    for tool, why in (("git", "the review gate"), ("gh", "the PR harvest and base-branch lookup")):
        if not shutil.which(tool):
            print(f"  {'warn':<8} {tool} not found; {why} needs it")

    if not CHANGES:
        print("Nothing to change.")
    elif not DRY and any(c in ("backup", "update") for c in CHANGES):
        print(f"Backups: {rel(BACKUP)}")
    if "opencode" in agents and not DRY and CHANGES:
        print("OpenCode loads plugins in a background service: run `opencode service restart`.")


if __name__ == "__main__":
    main()
