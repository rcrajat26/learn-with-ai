### §2.1 Subagents

2.1.11 The four built-ins and what each is for: `Explore` (read-only search), `Plan` (read-only
       research), `general-purpose`, `claude` (catch-all). `[DOC]`
2.1.12 Foreground vs background execution; `background: true`; `Ctrl+B`;
       `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1`; how permission prompts surface from a background
       agent. `[DOC]`
2.1.13 **Forks** (`/subtask`, `context: fork`): inherit the whole conversation and system prompt,
       share the prompt cache (cheaper), cannot spawn further forks. When a fork beats a fresh
       agent. `[DOC]`
2.1.14 Limits and guardrails, with numbers: default **20** concurrent subagents
       (`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`), nesting depth **3**
       (`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`), and the tools never available in a subagent
       (`AskUserQuestion`, `EndConversation`, `EnterPlanMode`, `Workflow`). `[DOC]` `[NUM]`
2.1.15 Naming rules: no `:` (reserved for plugin scoping), no leading `-`. `[DOC]`
2.1.16 Persistent agent memory: `memory: user|project|local` and the three directories it maps to.
       `[DOC]`
2.1.17 Resuming a subagent via `SendMessage` with its ID or name; where subagent transcripts live
       (`~/.claude/projects/{project}/{sessionId}/subagents/`). `[DOC]` `[VERSION]`
2.1.18 Invocation, three levels: natural language (Claude decides), `@"name (agent)"` mention
       (guaranteed), `claude --agent <name>` or the `agent` setting (whole session). `[DOC]`
2.1.19 The cost model: a subagent costs roughly **2×** the tokens of inline work because context
       must be re-supplied; a team of agents 3–4×. State when that is worth it. `[NUM]` `[PROVE]`
