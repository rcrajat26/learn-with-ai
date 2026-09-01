### §2.6 Context economy in practice

2.6.1 Read a real `/context` line by line and attribute every token: system prompt, tool schemas,
      memory files, skill listing, MCP schemas, conversation, free space. `[PROVE]` `[BUILD]`
2.6.2 The startup tax, itemised with numbers for the reader's own machine. `[NUM]` `[PROVE]`
2.6.3 The four biggest avoidable costs, ranked: unbounded command output, whole-file reads where a
      symbol lookup would do, a bloated always-on `CLAUDE.md`, and chatty MCP servers. `[NUM]`
2.6.4 Bounding tool output as a discipline: `head`/`tail`/`--quiet`/`-q`, targeted `grep` over
      `cat`, `git diff --stat` before `git diff`. `[BUILD]`
