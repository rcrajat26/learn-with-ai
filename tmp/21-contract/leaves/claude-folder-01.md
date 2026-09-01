### §1.1 The `.claude` folder, mapped

1.1.1 `.claude/` is configuration-as-code: a conventional directory the tool discovers, not a
      registry or a database. Everything in it is a file you can diff and commit. `[ZERO]`
1.1.2 The full inventory, one line each: `settings.json`, `settings.local.json`, `CLAUDE.md`,
      `rules/`, `commands/`, `skills/`, `agents/`, `hooks/`, `.mcp.json`, `.lsp.json`,
      `agent-memory/`. `[DOC]`
1.1.3 The user twin at `~/.claude/`: same shapes, machine-wide scope; plus `projects/`,
      `plugins/`, `keybindings.json`, and the tool-owned `~/.claude.json`. `[DOC]`
1.1.4 `~/.claude.json` is written by the tool for the tool — sign-in, MCP registrations, per-project
      trust decisions, `/config` global keys. Do not hand-edit it. `[DOC]` `[TRAP]`
1.1.5 `CLAUDE_CONFIG_DIR` relocates the whole user tree; on Windows `~/.claude` means
      `%USERPROFILE%\.claude`. `[DOC]`
1.1.6 The discovery walk: the tool reads from the session's **primary working directory** and
      every directory above it. Which artefacts walk upward, which load from subdirectories on
      demand, and which do neither. `[DOC]` `[PROVE]`
1.1.7 `[CASE]` The real harness `.claude/`: nine command files, one skill with a `references/`
      subfolder, and a `settings.json` of exactly two keys. Quote it. `[CASE]`
1.1.8 What is *not* in `.claude/` and why: the plugin cache, the transcripts, the auto-memory
      directory. Each lives outside the repo deliberately. `[DOC]`
1.1.9 The single most useful invariant to hold: **if a behaviour surprised you, some file caused
      it, and `/context` plus `/doctor` will name the file.** `[TRAP]`



