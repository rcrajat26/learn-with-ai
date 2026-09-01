### §1.5 Skills and slash commands

1.5.11 String substitutions: `$ARGUMENTS`, `$ARGUMENTS[N]`, `$N`, named `$name` via the `arguments`
       field, `${CLAUDE_SESSION_ID}`, `${CLAUDE_EFFORT}`, `${CLAUDE_SKILL_DIR}`. `[DOC]`
1.5.12 **Dynamic context injection**: `` !`command` `` runs a shell command *before* the content
       is sent, and its output replaces the placeholder. The fenced ` ```! ` block form for
       multi-line. `[DOC]`
1.5.13 Injection mechanics that bite: substitution runs **once** over the original file and output
       is not re-scanned; the inline form is recognised only at line start or after whitespace, so
       `` KEY=!`cmd` `` stays literal. `[DOC]` `[TRAP]`
1.5.14 `disableSkillShellExecution` turns injection off for user/project/plugin/additional-directory
       skills. Why an org might set it. `[DOC]`
1.5.15 **Skill content lifecycle**: the rendered content enters as one message and *stays* across
       later turns; the file is not re-read; a re-invocation with identical content adds a note,
       not a second copy. Write standing instructions, not one-time steps. `[DOC]`
1.5.16 Skills through compaction: the most recent invocation of each skill is re-attached after the
       summary, **first 5,000 tokens each, 25,000 tokens combined**, filled newest-first — so old
       skills can vanish. `[DOC]` `[NUM]`
1.5.17 `context: fork` + `agent:` + `background:` — run the skill in a forked subagent instead of
       inline. When that is the right shape. `[DOC]` `[VERSION]`
1.5.18 Supporting files: a skill is a *directory*, so `references/`, scripts and data live beside
       `SKILL.md` and are read on demand via `${CLAUDE_SKILL_DIR}`. `[DOC]`
