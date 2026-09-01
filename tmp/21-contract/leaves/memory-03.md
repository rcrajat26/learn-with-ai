### §1.3 `CLAUDE.md` and the memory system

1.3.21 **Auto memory**: the four types Claude records (`user`, `feedback`, `project`, `reference`),
       what it deliberately skips, and that it does not save every session. `[DOC]`
1.3.22 Auto-memory storage: `~/.claude/projects/<project>/memory/` with a `MEMORY.md` index plus
       one topic file per memory; keyed on the git repo so worktrees share it; machine-local.
       `[DOC]`
1.3.23 Only the **first 200 lines or 25 KB of `MEMORY.md`** loads at session start; topic files are
       read on demand. What happens when the index exceeds the limit. `[DOC]` `[NUM]`
1.3.24 `autoMemoryEnabled`, `autoMemoryDirectory`, `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`, and the
       `/memory` toggle. The `modified` frontmatter timestamp. `[DOC]` `[VERSION]`
1.3.25 Auto memory does **not** load into subagents (a fork excepted); a subagent's own `memory`
       field is a separate directory. `[DOC]`
1.3.26 What survives `/compact`: project-root `CLAUDE.md` is re-read from disk and re-injected;
       nested files and path-scoped rules reload only when re-matched; conversation-only
       instructions are gone. `[DOC]` `[TRAP]`
1.3.27 `/memory`, `/context`, `/init`, `/import`, and the `InstructionsLoaded` hook as the four
       ways to find out what actually loaded. `[DOC]`
1.3.28 `[TRAP]` "Claude ignored my CLAUDE.md." The diagnostic ladder: did it load (`/context`), is
       it specific enough, does another file contradict it, and should it have been a hook.
       `[TRAP]` `[DOC]`
1.3.29 `[CASE]` Read the reader's own two-level setup — the 125-line global `~/.claude/CLAUDE.md`
       and the project `.claude/CLAUDE.md` — and account for what each costs and whether each
       entry belongs there or in a skill. `[CASE]` `[BUILD]`



