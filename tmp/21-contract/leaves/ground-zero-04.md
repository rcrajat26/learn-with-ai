### §0.4 Getting oriented in the tool itself

0.4.1 Install and authenticate; `claude`, `claude auth login`, `claude auth status`. `[BUILD]`
0.4.2 The three ways in: interactive (`claude`), one-shot (`claude -p "…"`), continue
      (`claude -c`, `claude -r <session>`). `[DOC]`
0.4.3 The diagnostic commands that answer "why is it doing that", and the order to try them:
      `/context`, `/doctor`, `/permissions`, `/hooks`, `/memory`, `/config`, `claude --debug`.
      `[DOC]` `[BUILD]`
0.4.4 `/context` in detail — read a real one and account for every row. This is the single most
      important habit in the guide. `[PROVE]` `[BUILD]`
0.4.5 `/compact` and `/clear` — what each throws away, and when to use which. `[DOC]`
0.4.6 `/rewind` and file checkpointing (`fileCheckpointingEnabled`) — the undo you did not know
      you had. `[DOC]` `[VERSION]`
0.4.7 `!` prefix to run a shell command in-session and put its output in context; `@` to reference
      a file; `#` to save to memory. `[DOC]`
0.4.8 Session persistence: where transcripts live (`~/.claude/projects/<project>/`), how long
      (`cleanupPeriodDays`), and that they are plain JSONL you can read. `[DOC]` `[NUM]`
0.4.9 `--safe-mode` and `--bare`: start with all customisation disabled, to answer "is it my
      config or the tool?". `[DOC]` `[VERSION]`
0.4.10 The first-session checklist for this reader specifically: run `/context`, run `/doctor`,
       read your own `~/.claude/CLAUDE.md`, count its lines. `[BUILD]`








