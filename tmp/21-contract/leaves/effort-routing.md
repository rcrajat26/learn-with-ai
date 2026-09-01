### §3.5 Effort, models and routing

3.5.1 Effort levels `low|medium|high|xhigh|max`: what they change, `/effort`, `effortLevel`,
      `--effort`, `CLAUDE_EFFORT`, `${CLAUDE_EFFORT}`. `[DOC]`
3.5.2 Per-skill and per-agent `effort` and `model` overrides, and their lifetime (the turn, not the
      session). `[DOC]`
3.5.3 Routing as a cost decision, with a table: exploration/search → haiku; implementation →
      sonnet; architecture and gnarly debugging → opus. State the escalation path. `[NUM]`
3.5.4 `fallbackModel`, `--fallback-model`, `switchModelsOnFlag`, `advisorModel`, `modelOverrides`
      for Bedrock/Vertex ARNs, `modelPicker`. `[DOC]`
3.5.5 `fastMode` / `/fast` — faster output on the same Opus model, not a downgrade. `[DOC]`
      `[TRAP]`
3.5.6 `[TRAP]` Routing everything to the cheapest model. Where haiku fails, with a concrete
      example of a wrong result that cost more than the saving. `[TRAP]` `[PROVE]`



