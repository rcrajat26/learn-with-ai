### §1.3 `CLAUDE.md` and the memory system

1.3.1 Two mechanisms, clearly separated: `CLAUDE.md` files (you write, instructions) and **auto
      memory** (Claude writes, learnings). Both load every session. `[DOC]`
1.3.2 Both are **context, not enforced configuration.** Claude reads them and tries; a hook is the
      only guarantee. Repeat this sentence in the guide; it is the most-missed fact here. `[DOC]`
      `[TRAP]`
1.3.3 The four `CLAUDE.md` locations in load order: managed policy path (per-OS), `~/.claude/
      CLAUDE.md`, `./CLAUDE.md` or `./.claude/CLAUDE.md`, `./CLAUDE.local.md`. `[DOC]`
1.3.4 The managed policy paths, exactly: macOS `/Library/Application Support/ClaudeCode/CLAUDE.md`,
      Linux/WSL `/etc/claude-code/CLAUDE.md`, Windows `C:\Program Files\ClaudeCode\CLAUDE.md`.
      `[DOC]`
1.3.5 How they load: **concatenated, not overriding** — root-down ordering, so the file nearest
      your working directory is read last, and `CLAUDE.local.md` after `CLAUDE.md` at each level.
      `[DOC]` `[PROVE]`
1.3.6 Subdirectory `CLAUDE.md` files load **on demand**, when Claude reads a file in that
      directory — not at launch. `[DOC]`
1.3.7 `@path` imports: relative to the importing file, recursive to a **maximum depth of four
      hops**, skipped inside code spans and fences. `[DOC]` `[NUM]`
1.3.8 `[TRAP]` An import does not save context — the imported file loads at launch too. Splitting
      a large `CLAUDE.md` into imports buys organisation only. `[TRAP]` `[DOC]`
1.3.9 External imports (paths resolving outside the working directory) trigger a one-time approval
      dialog for project files; user-scope files are trusted. Why the dialog exists. `[DOC]`
1.3.10 Size guidance: **target under 200 lines**; a file over 4 MiB is skipped entirely; longer
       files measurably reduce adherence. `[DOC]` `[NUM]`
1.3.11 `[PROVE]` Measure the cost of your own `CLAUDE.md`: token count × turns in a session =
       tokens spent on it. Do the arithmetic for the reader's actual global file. `[PROVE]` `[NUM]`
1.3.12 Writing instructions that get followed: specific over vague, verifiable over aspirational,
       structured over prose, consistent over contradictory. Three before/after pairs. `[DOC]`
1.3.13 Block-level HTML comments are stripped before injection — free maintainer notes. `[DOC]`
