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
