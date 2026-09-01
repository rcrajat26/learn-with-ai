### §2.5 Plugins and marketplaces

2.5.1 What a plugin is: a self-contained directory of skills, agents, hooks, MCP/LSP configs,
      monitors, `bin/` and default settings, installable and versioned. `[ZERO]` `[DOC]`
2.5.2 Standalone `.claude/` vs plugin — the real trade: iteration speed vs distribution,
      versioning and namespacing. Start standalone, convert when you share. `[DOC]`
2.5.3 The directory layout, every component: `.claude-plugin/plugin.json`, `skills/`, `commands/`,
      `agents/`, `hooks/hooks.json`, `.mcp.json`, `.lsp.json`, `monitors/monitors.json`, `bin/`,
      `settings.json`. `[DOC]`
2.5.4 `[TRAP]` **Only `plugin.json` goes inside `.claude-plugin/`.** Putting `skills/` or `agents/`
      in there silently ships nothing. And the plugin root is the plugin's own directory — never
      `~/.claude/`. `[TRAP]` `[DOC]`
