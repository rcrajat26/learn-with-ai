### §2.2 Personas: `--agent` vs `--append-system-prompt` vs `--system-prompt`

2.2.1 `--agent <name>` loads a **registered** agent — its full system prompt, model and tool
      allowlist. The parity mechanism for programmatically spawning a subagent. `[DOC]`
2.2.2 `--append-system-prompt <text>` **appends to the default** system prompt. The default persona
      is still there; you decorated it. `[DOC]` `[TRAP]`
2.2.3 `--system-prompt` / `--system-prompt-file` **replace** the whole thing. What you lose.
      `[DOC]`
2.2.4 `--append-subagent-system-prompt` for every subagent; `--exclude-dynamic-system-prompt-sections`
      to move per-machine sections out of the cached prefix. `[DOC]` `[VERSION]`
2.2.5 `[CASE]` `engine/agent.py` documents the distinction explicitly and calls `--agent` "the
      parity mechanism for an auto-spawned subagent, not `--append-system-prompt` (which only
      appends to the default prompt)". Quote it. `[CASE]`
2.2.6 `[CASE]` `load_agent_prompt()` strips the `--- … ---` frontmatter before appending, because
      YAML metadata leaking into a system prompt is noise the model tries to interpret. The regex
      and why it is anchored. `[CASE]` `[SOURCE-EQUIV]`
2.2.7 `[TRAP]` Choosing `--append-system-prompt` when you meant `--agent`: the symptom is an agent
      that behaves *almost* right and ignores its tool restrictions, because it never had any.
      `[TRAP]`



