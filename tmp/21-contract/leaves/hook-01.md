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
