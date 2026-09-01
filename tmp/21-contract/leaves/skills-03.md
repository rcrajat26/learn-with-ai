### §1.5 Skills and slash commands

1.5.19 `[CASE]` The harness's `playwright-cli` skill with its `references/` subfolder — a reference
       library that costs nothing until needed. `[CASE]`
1.5.20 `[CASE]` The harness's `bootstrap` skill: `name` / `description` / `when_to_use` /
       `allowed-tools: [Bash, Read, AskUserQuestion]`, and a body that is an **orchestrator, not a
       rewrite** — each step delegates to a tested `bootstrap-*.sh`. Quote the "why deterministic
       scripts and not model judgment" paragraph verbatim. `[CASE]`
1.5.21 `[CASE]` Prompt composition without duplication: `/implement-story` inlines
       `/run-conductor` with a ` ```! ` block running
       `cat "${CLAUDE_PLUGIN_ROOT}/commands/run-conductor.md"`, then states only its binding
       overrides, forwarded flags and **rejected flags**. DRY applied to prompts. `[CASE]`
1.5.22 `[TRAP]` A description that names the **topic** rather than the **trigger** makes the skill
       invisible or always-on. Three bad descriptions rewritten. `[TRAP]`
1.5.23 Built-in and bundled: `/help`, `/compact`, `/clear`, `/context`, `/config`, `/doctor`,
       `/permissions`, `/hooks`, `/memory`, `/init`, `/plugin`, `/agents`, `/rewind`, `/cd`,
       `/add-dir`, `/model`, `/effort`, plus bundled skills such as `/code-review`, `/security-review`,
       `/loop`, `/run`. `[DOC]` `[RESEARCH]`
1.5.24 `skillOverrides`, `disableBundledSkills`, `syncClaudeAiSkills`, `--disable-slash-commands`
       — the visibility and kill switches. `[DOC]`
1.5.25 `[BUILD]` Write a real skill for this repository: one that regenerates a topic guide's
       atomic-concept checklist. Frontmatter, `$ARGUMENTS`, one `` !`command` `` injection, a
       `references/` file. Then invoke it and read `/context` before and after. `[BUILD]` `[PROVE]`
1.5.26 The decision table the reader needs: fact that always applies → `CLAUDE.md`; fact that
       applies to one file type → path-scoped rule; procedure → skill; must-happen → hook;
       verbose-in/small-out → subagent; distribution → plugin. `[NUM]`







