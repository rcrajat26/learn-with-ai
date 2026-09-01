### §0.3 The agent loop

0.3.1 The loop in three steps, written out: assemble request → model emits text or a tool call →
      harness executes the tool, appends the result, repeat. `[ZERO]`
0.3.2 A **tool** is a function the harness exposes to the model as a name, a description, and a
      JSON input schema. Show one real schema. `[ZERO]` `[DOC]`
0.3.3 The model does not *call* the tool. It emits a `tool_use` block naming the tool and the
      arguments; the harness decides whether to run it. This distinction is the entire basis of
      the permission system. `[ZERO]` `[TRAP]`
0.3.4 A `tool_result` message goes back into the transcript. So tool output is context, and a
      verbose tool is a context leak. `[ZERO]`
0.3.5 A **turn**: one model response plus any tools it triggers. Why `--max-turns` bounds agency
      and a wall-clock timeout bounds time, and why you need both. `[NUM]`
0.3.6 The model chooses tools **from their descriptions alone**. A vague description produces a
      misused tool. `[TRAP]`
0.3.7 Walk a complete real loop end to end: "rename this method" → Grep → Read → Edit → done, with
      the transcript growing at each step and the token count stated after each. `[PROVE]` `[NUM]`
0.3.8 The built-in tools, by category: file (Read, Write, Edit, Glob, Grep), shell (Bash),
      web (WebFetch, WebSearch), delegation (Agent, SendMessage), meta (Skill, ToolSearch),
      task/UI (TodoWrite, AskUserQuestion). `[DOC]` `[RESEARCH]`
0.3.9 Deferred tools and `ToolSearch`: why the full schema of every tool is not loaded up front,
      and what that buys. `[DOC]` `[VERSION]`
0.3.10 **Extended thinking**: the model can emit reasoning tokens before answering; they cost
       tokens and are configurable. `alwaysThinkingEnabled`, `showThinkingSummaries`, the
       `effort` levels `low|medium|high|xhigh|max`. `[DOC]` `[NUM]`
0.3.11 Where "Claude Code" sits: it is *the harness*. The CLI, the VS Code/JetBrains extensions,
       the desktop app and the web app are different front ends over the same loop and the same
       settings files. `[ZERO]` `[DOC]`
0.3.12 The Agent SDK / API as the same loop with the harness written by you. One-paragraph
       orientation; full treatment in §3.8. `[X-REF 21]`



