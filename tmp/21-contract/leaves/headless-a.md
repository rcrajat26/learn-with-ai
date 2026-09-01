### §3.6 Headless mode — the programmable surface

3.6.1 `claude -p "<task>"` — one prompt in, one envelope out. The whole basis of automation.
      `[DOC]`
3.6.2 `--output-format text|json|stream-json` and `--input-format text|stream-json`. What each is
      for. `[DOC]`
3.6.3 The JSON envelope's fields: result text, `is_error`, `session_id`, cost, token counts,
      duration. Show a real one. `[DOC]` `[PROVE]`
3.6.4 `stream-json` and `--include-partial-messages`, `--include-hook-events`,
      `--forward-subagent-text`, `--replay-user-messages`. When streaming is worth the complexity.
      `[DOC]`
3.6.5 `--json-schema` for schema-validated output — the difference between parsing prose and
      receiving data. `[DOC]` `[VERSION]`
3.6.6 The flag set a production wrapper needs, as a checklist: `--agent`, `--output-format`,
      `--max-turns`, `--permission-mode`, `--setting-sources`, `--settings`, `--model`, `--effort`,
      `--add-dir`, `--append-system-prompt`, `--resume`, `--max-budget-usd`, `--session-id`,
      `--no-session-persistence`, `--allowed-tools`, `--disallowed-tools`, `--mcp-config`,
      `--verbose`. `[DOC]`
3.6.7 Session control in automation: `--session-id` (must be a UUID), `--fork-session`,
      `--continue`, `--resume`, `--no-session-persistence`. `[DOC]`
3.6.8 `claude setup-token` for CI; what an unattended run must *not* have. `[DOC]`
3.6.9 Background and remote execution: `--bg`, `claude attach|logs|stop|respawn|rm`,
      `claude daemon status`, `--cloud`, `--environment`, `--teleport`. One paragraph each.
      `[DOC]`
