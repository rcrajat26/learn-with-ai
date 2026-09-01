### §2.3 Hooks

2.3.15 Which decision field each event honours — the table. `PreToolUse` takes
       `permissionDecision`; `Stop` takes `continue`; `PostToolUse` takes none because it already
       ran. `[DOC]`
2.3.16 Hook decisions **do not bypass permission rules**: a matching deny still blocks and a
       matching ask still prompts, whatever the hook returned. `[DOC]` `[TRAP]`
2.3.17 Path placeholders and env vars: `${CLAUDE_PROJECT_DIR}`, `${CLAUDE_PLUGIN_ROOT}`,
       `${CLAUDE_PLUGIN_DATA}`, `CLAUDE_CODE_REMOTE`, `CLAUDE_EFFORT`,
       `CLAUDE_PLUGIN_OPTION_*`. `[DOC]`
