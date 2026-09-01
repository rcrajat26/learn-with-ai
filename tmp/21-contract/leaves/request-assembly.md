### §3.1 What is actually in the request

3.1.1 The assembled request, in order: system prompt (built-in + appended), tool schemas, memory
      files as a user message, environment/git snapshot, skill listing, then the conversation.
      `[DOC]` `[PROVE]`
3.1.2 `[TRAP]` `CLAUDE.md` is delivered **as a user message after the system prompt**, not as part
      of the system prompt. That is why it is guidance and not policy, and why
      `--append-system-prompt` behaves differently. `[TRAP]` `[DOC]`
3.1.3 The cached prefix and why the ordering above is not arbitrary: everything stable goes first
      so it can be reused. `--exclude-dynamic-system-prompt-sections` exists to protect this.
      `[NUM]` `[DOC]`
3.1.4 Tool schemas as a cost line: how many tokens the default set is, what an MCP server adds,
      and what deferred tools plus `ToolSearch` save. `[NUM]` `[PROVE]`
3.1.5 The skill listing: `description` + `when_to_use` per skill, capped at 1,536 characters each,
      inside a budget fraction of the window. Compute the cost of 50 skills. `[NUM]` `[PROVE]`
3.1.6 System-reminder blocks: how the harness injects mid-conversation state (file-state notes,
      recalled memories, hook output) and why that text is context rather than instruction.
3.1.7 Reading a real transcript: the JSONL under `~/.claude/projects/<project>/<session>/`, its
      message shapes, and how to count tokens per turn from it. `[BUILD]` `[PROVE]`
3.1.8 `[CASE]` The harness's `telemetry/transcript.py` reads exactly these transcripts to mine
      friction signals. Provenance for the whole calibration loop. `[CASE]`



