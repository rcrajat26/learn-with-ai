### §2.1 Subagents

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
