### §1.4 The permission system

1.4.16 `Read`/`Edit` rules use **gitignore pattern syntax**; the four anchor forms (`//abs`, `~/`,
       `/`, bare); `Read(./.env)`, `Read(./secrets/**)`. `[DOC]`
1.4.17 A `Read` deny also blocks Edit and Write on the same path — but not `NotebookEdit`, so add
       an `Edit` deny too. `[DOC]` `[VERSION]`
1.4.18 `[TRAP]` File permissions are checked against `Edit(path)` and `Read(path)` **only**. A
       `Write(docs/**)`, `NotebookEdit(...)`, `MultiEdit(...)` or `Glob(...)` path rule is accepted
       and never consulted. Use `Edit(...)`/`Read(...)`. `[TRAP]` `[DOC]` `[VERSION]`
1.4.19 `[TRAP]` Read/Edit deny rules cover the built-in file tools and file commands Claude Code
       recognises in Bash (`cat`, `head`, `tail`, `sed`) — **not** an arbitrary subprocess. A
       Python script that opens the file itself is not stopped. Sandbox is the OS-level answer.
       `[TRAP]` `[DOC]`
1.4.20 `WebFetch(domain:example.com)`; allow-or-deny-every-fetch forms. `[DOC]`
1.4.21 MCP rules: `mcp__server`, `mcp__server__*`, `mcp__server__tool`. Parenthesised `mcp__` rules
       in a settings file are skipped; use `--disallowedTools` for parameter matching. `[DOC]`
1.4.22 `Agent(Name)` rules — gate which subagents may run, including the built-ins
       `Agent(Explore)`, `Agent(Plan)`, `Agent(fork)`. `[DOC]`
1.4.23 Parameter matching for deny/ask on any built-in tool: `Tool(param:value)`, e.g.
       `Agent(model:opus)`, `Agent(isolation:worktree)`, `Bash(run_in_background:true)`. One
       parameter per rule; direct fields only; `*` wildcard; compared before normalisation. `[DOC]`
1.4.24 `Cd` rules — not model-invocable; bare deny disables `/cd`; any allow rule switches to
       allowlist mode; `*` is one segment and `**` spans segments. `[DOC]`
