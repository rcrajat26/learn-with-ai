### §3.2 Compaction, mechanically

3.2.1 What compaction does: summarise the transcript, then continue with the summary in place of
      the messages. `[DOC]`
3.2.2 The threshold and how it is configured; what "75%" means against which number. `[NUM]`
3.2.3 The re-attachment algorithm for skills: most recent invocation of each, first 5,000 tokens
      each, 25,000 combined, filled newest-first — so invoking many skills silently evicts the
      earliest. `[DOC]` `[NUM]` `[PROVE]`
3.2.4 `CLAUDE.md` re-read from disk after compaction; nested files and path-scoped rules reload
      only on re-match. `[DOC]`
3.2.5 What is irrecoverably lost, and the fix: put it in a file, not in a message. `[TRAP]`
3.2.6 `PreCompact`/`PostCompact` as the persistence seam; a worked handoff-note hook. `[BUILD]`
3.2.7 Why a fresh session usually beats a thrice-compacted one, argued rather than asserted.
      `[PROVE]`



