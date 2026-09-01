### §2.1 Subagents

2.1.16 Persistent agent memory: `memory: user|project|local` and the three directories it maps to.
       `[DOC]`
2.1.17 Resuming a subagent via `SendMessage` with its ID or name; where subagent transcripts live
       (`~/.claude/projects/{project}/{sessionId}/subagents/`). `[DOC]` `[VERSION]`
2.1.18 Invocation, three levels: natural language (Claude decides), `@"name (agent)"` mention
       (guaranteed), `claude --agent <name>` or the `agent` setting (whole session). `[DOC]`
2.1.19 The cost model: a subagent costs roughly **2×** the tokens of inline work because context
       must be re-supplied; a team of agents 3–4×. State when that is worth it. `[NUM]` `[PROVE]`
