### §2.5 Plugins and marketplaces

2.5.9 Marketplaces: `.claude-plugin/marketplace.json` with `$schema`, `name`, `description`,
      `owner`, `plugins[]`, and `allowCrossMarketplaceDependenciesOn`. `[DOC]`
2.5.10 Cross-marketplace dependencies: Claude Code **refuses to auto-add a marketplace the user
       has not explicitly trusted**, so onboarding must instruct adding both. `[DOC]`
2.5.11 `[TRAP]` An unresolved plugin dependency is nearly silent — a cryptic `/reload-plugins`
       error. `claude plugin list --json` exposes a per-plugin `errors` array; check it. `[TRAP]`
       `[DOC]`
2.5.12 The commands: `/plugin`, `/plugin marketplace add`, `/plugin install`, `/reload-plugins`,
       `claude plugin init|validate|list`, `--plugin-dir` (directory or `.zip`), `--plugin-url`.
       `[DOC]`
2.5.13 Skills-directory plugins via `claude plugin init` — a plugin that auto-loads from
       `~/.claude/skills/` with no marketplace. `[DOC]` `[VERSION]`
2.5.14 Governance: `enabledPlugins`, `blockedMarketplaces`, `extraKnownMarketplaces`,
       `strictKnownMarketplaces`, `strictPluginOnlyCustomization` (and its `.agents`, `.hooks`,
       `.mcp`, `.skills` sub-keys), `disableSideloadFlags`, `pluginTrustMessage`. `[DOC]`
2.5.15 `strictPluginOnlyCustomization` as the enterprise endgame: block skills, agents, hooks and
       MCP from user and project sources so **only reviewed, versioned plugins can extend the
       agent.** Why an org reaches for it. `[DOC]`
