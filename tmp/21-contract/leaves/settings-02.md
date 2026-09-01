### §1.2 Settings files, scope, and precedence

1.2.9 The key groups, named so the reader knows where to look: permissions, hooks, plugins/skills,
      context/memory, model/responses, MCP, sandbox, attribution, auth, data/privacy, interface,
      agents/sessions/worktrees, updates, enterprise, global config. `[DOC]`
1.2.10 The dozen keys this reader will actually touch first, with values:
       `permissions`, `hooks`, `env`, `model`, `effortLevel`, `enabledPlugins`,
       `autoCompactEnabled`, `autoCompactWindow`, `autoMemoryEnabled`, `claudeMdExcludes`,
       `statusLine`, `cleanupPeriodDays`. `[DOC]` `[BUILD]`
1.2.11 `env` — settings-supplied environment variables for every session; how they compose across
       scopes, and that they apply to hooks and Bash too. `[DOC]`
1.2.12 `[CASE]` The harness's real `settings.json`: `permissions.allow` of four entries plus
       `enabledPlugins` of four plugins (three official LSP plugins and its own). Quote it and
       explain each entry. `[CASE]`
1.2.13 Verifying a setting actually applied: `/config`, `/permissions`, `claude doctor`'s resolved
       settings, and the invalid-settings dialog. `[BUILD]`
1.2.14 `[TRAP]` A silently-ignored key. Unknown keys, `mcp__` rules with parentheses in a settings
       file, and path rules on tools that never consult them are all accepted and then ignored —
       with a startup warning most people never read. `[TRAP]` `[DOC]`
1.2.15 Managed settings as an org control surface, in one paragraph: what it is for, the
       `allowManaged*Only` locks, and why a developer cannot override it. Full treatment §2.9.
1.2.16 `--setting-sources user,project,local` — choosing which layers load *at all*. Set up the
       incident in §3.7 now; do not resolve it here. `[DOC]`



