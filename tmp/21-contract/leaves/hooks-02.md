### §2.3 Hooks

2.3.10 The stdin JSON every event receives: `session_id`, `prompt_id`, `transcript_path`, `cwd`,
       `permission_mode`, `hook_event_name`, `effort.level`; plus `agent_id`/`agent_type` when
       running under a subagent. `[DOC]`
2.3.11 Event-specific stdin payloads: `tool_name`/`tool_input`/`tool_use_id`, `user_input`,
       `last_assistant_message`/`stop_reason`, `file_path`/`change_type`. `[DOC]`
2.3.12 **Exit-code semantics**, precisely: `0` = success (stdout goes to the debug log, except
       `UserPromptSubmit`/`UserPromptExpansion`/`SessionStart` where it is shown to Claude);
       `2` = blocking error and **the only code that blocks without JSON**; anything else =
       non-blocking. `[DOC]` `[NUM]`
2.3.13 `[TRAP]` Exit 2 overrides a JSON `permissionDecision: "allow"` — it blocks regardless.
       `[TRAP]` `[DOC]`
2.3.14 The JSON output contract: `hookSpecificOutput.{hookEventName, permissionDecision,
       permissionDecisionReason, decision, additionalContext, continue, updatedInput, retry,
       systemMessage}` plus top-level `terminalSequence`. `[DOC]`
2.3.15 Which decision field each event honours — the table. `PreToolUse` takes
       `permissionDecision`; `Stop` takes `continue`; `PostToolUse` takes none because it already
       ran. `[DOC]`
2.3.16 Hook decisions **do not bypass permission rules**: a matching deny still blocks and a
       matching ask still prompts, whatever the hook returned. `[DOC]` `[TRAP]`
2.3.17 Path placeholders and env vars: `${CLAUDE_PROJECT_DIR}`, `${CLAUDE_PLUGIN_ROOT}`,
       `${CLAUDE_PLUGIN_DATA}`, `CLAUDE_CODE_REMOTE`, `CLAUDE_EFFORT`,
       `CLAUDE_PLUGIN_OPTION_*`. `[DOC]`
2.3.18 Where hooks may be configured: user/project/local settings, managed policy, plugin
       `hooks/hooks.json`, **skill frontmatter** (rest of session), **subagent frontmatter**
       (while it runs). Six sources. `[DOC]`
2.3.19 `disableAllHooks`, `allowManagedHooksOnly`, `--settings '{"disableAllHooks":true}'`, and
       that individual hooks cannot be disabled — only deleted. `[DOC]`
2.3.20 `/hooks` as the read-only browser: events, counts, matcher groups, handler details and
       source file. The debug log records which hooks matched and how they exited. `[DOC]`
       `[BUILD]`
