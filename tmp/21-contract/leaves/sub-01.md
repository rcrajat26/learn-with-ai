### §2.1 Subagents

2.1.1 What a subagent is, mechanically: a **separate context window** running the same loop, given
      a task string, returning a final message. Nothing else crosses the boundary. `[ZERO]`
2.1.2 Definition file locations and precedence, highest first: managed settings → `--agents` CLI
      JSON → `.claude/agents/` → `~/.claude/agents/` → plugin `agents/`. `[DOC]` `[NUM]`
2.1.3 `[TRAP]` Note the inversion against skills: for **agents**, project beats user; for
      **skills**, personal beats project. Two subsystems, two orders. `[TRAP]` `[DOC]`
2.1.4 The file format: YAML frontmatter plus a markdown system prompt. `[DOC]`
2.1.5 Frontmatter, every field: `name`, `description`, `tools`, `disallowedTools`, `model`,
      `permissionMode`, `maxTurns`, `skills`, `mcpServers`, `hooks`, `memory`, `background`,
      `effort`, `isolation`, `color`, `initialPrompt`, `experimental`. `[DOC]`
