### §3.9 Orchestration patterns

3.9.1 The vocabulary, defined: single session, subagent, fan-out, pipeline, team, workflow. `[ZERO]`
3.9.2 Fan-out with a join: N independent tasks, one aggregation, and the file-boundary requirement
      that makes it safe. `[NUM]`
3.9.3 Pipeline: stage N's output is stage N+1's input, each stage independently re-runnable
      **because no stage writes to its own input.** `[CASE]`
3.9.4 `[CASE]` This repository's own per-topic pipeline as the worked example:
      `topic-enhancer-agent` → `prompt-builder` → `notes-generator` → `gaps-analyzer-agent` →
      `understanding-book-keeper`, with the rule "never write across lanes" and a hard stop when a
      prerequisite is missing. `[CASE]`
