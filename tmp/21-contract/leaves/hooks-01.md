### §2.3 Hooks

2.3.1 What a hook is: a command **the harness runs** at a lifecycle event, not something the model
      decides to run. Therefore the only mechanism that *guarantees* something happens. `[ZERO]`
      `[DOC]`
2.3.2 The configuration schema: `hooks.<Event>[] → { matcher, hooks: [{ type, … }] }`, plus
      `if`, `timeout`, `statusMessage`, `once`. `[DOC]`
2.3.3 The five handler types: `command`, `http`, `mcp_tool`, `prompt`, `agent`. What each is for,
      and that the last two put a model in the enforcement path. `[DOC]` `[VERSION]`
2.3.4 `command` handler fields: `command`, `args`, `async`, `asyncRewake`, `shell`. `[DOC]`
2.3.5 `http` handler: `url`, `headers`, `allowedEnvVars`, plus the `allowedHttpHookUrls` and
      `httpHookAllowedEnvVars` settings that fence it. `[DOC]`
2.3.6 The full event catalogue (32 events as of v2.1.2xx), grouped so it is learnable rather than
      memorised: session lifecycle (`SessionStart`, `Setup`, `SessionEnd`), prompt
      (`UserPromptSubmit`, `UserPromptExpansion`), tools (`PreToolUse`, `PostToolUse`,
      `PostToolUseFailure`, `PostToolBatch`), permissions (`PermissionRequest`,
      `PermissionDenied`), turn (`Stop`, `StopFailure`), subagents (`SubagentStart`,
      `SubagentStop`), tasks (`TaskCreated`, `TaskCompleted`, `TeammateIdle`), context
      (`PreCompact`, `PostCompact`, `InstructionsLoaded`), environment (`ConfigChange`,
      `CwdChanged`, `DirectoryAdded`, `FileChanged`), worktrees (`WorktreeCreate`,
      `WorktreeRemove`), MCP (`Elicitation`, `ElicitationResult`), UI (`Notification`,
      `MessageDisplay`). `[DOC]` `[NUM]` `[RESEARCH]`
2.3.7 Which events **can block** and which cannot — the table, because reaching for a hook that
      cannot block is the most common design error here. `[DOC]` `[NUM]`
2.3.8 `matcher` semantics: `*`/empty/omitted matches all; `|` or `,` for an exact list; anything
      with special characters is a regex. `[DOC]`
2.3.9 Matcher values differ per event: tool name for tool events, session type
      (`startup|resume|clear|compact|fork`) for `SessionStart`, end reason for `SessionEnd`, agent
      type for subagent events, config source for `ConfigChange`, error type for `StopFailure`,
      filenames for `FileChanged`. `[DOC]`
