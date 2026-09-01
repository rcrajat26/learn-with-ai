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
2.1.6 `description` is the routing signal — it says *when to delegate*, not what the agent is.
      The combined description budget across custom agents is ~**15,000 tokens**. `[DOC]` `[NUM]`
2.1.7 `tools` as an allowlist vs `disallowedTools` as a denylist; MCP-prefix forms; restricting
      which agents an agent may spawn with `tools: Agent(worker, researcher)`. `[DOC]`
2.1.8 **What loads at subagent startup**: its own system prompt + environment, the delegating task
      message, the full `CLAUDE.md` hierarchy (except Explore/Plan), a git-status snapshot from
      parent session start, preloaded `skills`, the sibling roster. `[DOC]` `[NUM]`
2.1.9 **What does not load**: conversation history, the main output style, auto memory, previously
      read files or invoked skills. Forks are the exception and inherit everything. `[DOC]`
2.1.10 `[TRAP]` Therefore a subagent knows nothing your session learned. Everything it needs goes
       in the task string or a file it is told to read. `[TRAP]`
