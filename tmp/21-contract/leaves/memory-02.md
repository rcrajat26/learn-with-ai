### §1.3 `CLAUDE.md` and the memory system

1.3.14 `.claude/rules/` — modular instruction files, discovered recursively, same priority as
       `.claude/CLAUDE.md` when they have no `paths` frontmatter. `[DOC]`
1.3.15 **Path-specific rules**: `paths:` frontmatter globs, loaded only when Claude touches a
       matching file. The one mechanism that makes a large instruction set affordable. `[DOC]`
1.3.16 `paths` glob mechanics: brace expansion, the shared budget of **1,000 expanded patterns /
       4 MiB**, what happens on overflow, and the `[`-bracket-expression pitfall. `[DOC]` `[NUM]`
       `[VERSION]`
1.3.17 User-level rules in `~/.claude/rules/` load before project rules, giving project rules
       higher priority. Symlinks are supported and cycles are handled. `[DOC]`
1.3.18 `AGENTS.md`: Claude Code does not read it. The `@AGENTS.md` import and the symlink, and why
       the import is preferable on Windows. `[DOC]`
1.3.19 `claudeMdExcludes` for monorepos — glob against absolute paths, merges across layers,
       cannot exclude managed policy. `[DOC]`
1.3.20 `claudeMd` in managed settings: org instructions inline in JSON, honoured only at managed
       scope. `[DOC]`
