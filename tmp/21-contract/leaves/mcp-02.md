### §2.4 MCP — connecting external systems

2.4.6 Tool naming: `mcp__<server>__<tool>`; how it appears in permission rules, hook matchers and
      the tool list. `[DOC]`
2.4.7 The cost of a connected server: every tool's schema is context. A chatty server is a
      permanent tax on every turn. Measure it with `/context`. `[NUM]` `[PROVE]`
2.4.8 Failure modes, including the one in this very session: a configured server that fails to
      connect is a *connection* failure, not a missing capability, and the correct action is to
      report it, not to conclude the feature does not exist. `[TRAP]`
2.4.9 Governance keys: `allowedMcpServers`, `deniedMcpServers`, `allowManagedMcpServersOnly`,
      `disableClaudeAiConnectors`, `allowAllClaudeAiMcps`, `--strict-mcp-config`. `[DOC]`
2.4.10 `--mcp-config` for per-run servers; `requiresUserInteraction` on a tool; elicitation and
       the `Elicitation`/`ElicitationResult` hooks. `[DOC]`
