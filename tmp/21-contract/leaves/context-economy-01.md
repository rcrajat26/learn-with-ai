### §2.6 Context economy in practice

2.6.1 Read a real `/context` line by line and attribute every token: system prompt, tool schemas,
      memory files, skill listing, MCP schemas, conversation, free space. `[PROVE]` `[BUILD]`
2.6.2 The startup tax, itemised with numbers for the reader's own machine. `[NUM]` `[PROVE]`
2.6.3 The four biggest avoidable costs, ranked: unbounded command output, whole-file reads where a
      symbol lookup would do, a bloated always-on `CLAUDE.md`, and chatty MCP servers. `[NUM]`
2.6.4 Bounding tool output as a discipline: `head`/`tail`/`--quiet`/`-q`, targeted `grep` over
      `cat`, `git diff --stat` before `git diff`. `[BUILD]`
2.6.5 **Autocompaction**: `autoCompactEnabled`, `autoCompactWindow`, `--autocompact`,
      `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`. What compaction actually is — a summary replacing the
      transcript. `[DOC]`
2.6.6 What survives compaction, exhaustively: project-root `CLAUDE.md` re-read from disk;
      most-recent skill invocations within the 5,000/25,000-token budget; nothing else that lived
      only in conversation. `[DOC]` `[NUM]`
2.6.7 `PreCompact` / `PostCompact` hooks as the seam to persist state across a compaction. `[DOC]`
2.6.8 `/compact` vs `/clear` vs a fresh session vs `--fork-session`: four different reset
      semantics. `[NUM]`
2.6.9 The prompt-cache economics of session shape: append-only conversations stay cached; anything
      that changes the prefix does not. Why a 5-minute idle gap has a price. `[NUM]` `[PROVE]`
2.6.10 Isolation as the primary lever, restated with arithmetic: burn 150K in a subagent, return
       200 words. Compare against doing the same work inline. `[PROVE]` `[NUM]`
2.6.11 A working session protocol for this reader: `/context` at start, compact at a task
       boundary, `/clear` per feature, subagent for anything verbose, one file per lane. `[BUILD]`
2.6.12 `[TRAP]` Compacting mid-task instead of at a boundary. The summary keeps the narrative and
       drops the specifics you were about to use. `[TRAP]`



