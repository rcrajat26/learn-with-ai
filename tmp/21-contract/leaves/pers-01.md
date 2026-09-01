### §2.2 Personas: `--agent` vs `--append-system-prompt` vs `--system-prompt`

2.2.1 `--agent <name>` loads a **registered** agent — its full system prompt, model and tool
      allowlist. The parity mechanism for programmatically spawning a subagent. `[DOC]`
2.2.2 `--append-system-prompt <text>` **appends to the default** system prompt. The default persona
      is still there; you decorated it. `[DOC]` `[TRAP]`
2.2.3 `--system-prompt` / `--system-prompt-file` **replace** the whole thing. What you lose.
      `[DOC]`
2.2.4 `--append-subagent-system-prompt` for every subagent; `--exclude-dynamic-system-prompt-sections`
      to move per-machine sections out of the cached prefix. `[DOC]` `[VERSION]`
