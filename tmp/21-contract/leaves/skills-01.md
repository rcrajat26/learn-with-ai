### §1.5 Skills and slash commands

1.5.1 The merge, stated first because every older article gets it wrong: **custom commands are
      skills.** `.claude/commands/deploy.md` and `.claude/skills/deploy/SKILL.md` both create
      `/deploy` and behave the same way. `[DOC]` `[VERSION]` `[TRAP]`
1.5.2 What a skill *is*: a markdown file of instructions that the tool injects into the
      conversation when invoked. Not code, not a tool, not a plugin. `[ZERO]`
1.5.3 The four locations and the conflict order: enterprise → personal (`~/.claude/skills/`) →
      project (`.claude/skills/`); a skill at any level overrides a bundled skill of the same name
      but not its aliases; plugin skills are namespaced `plugin:skill` and cannot conflict; a
      skill beats a same-named `commands/` file. `[DOC]`
1.5.4 Nested `.claude/skills/` below the working directory become available when Claude reads a
      file in that subtree — the monorepo mechanism. `[DOC]`
1.5.5 **Progressive disclosure**, the central idea: only the frontmatter `description` (plus
      `when_to_use`) is in context up front; the body loads when the skill fires. This is why 50
      skills cost almost nothing and 50 skills' worth of `CLAUDE.md` costs everything. `[DOC]`
      `[NUM]`
1.5.6 The listing budget: combined `description` + `when_to_use` is truncated at **1,536
      characters**; `skillListingBudgetFraction` and `skillListingMaxDescChars` tune the listing.
      `[DOC]` `[NUM]`
1.5.7 Frontmatter, every field: `name`, `description`, `when_to_use`, `argument-hint`, `arguments`,
      `disable-model-invocation`, `user-invocable`, `allowed-tools`, `disallowed-tools`, `model`,
      `effort`, `context`, `agent`, `background`, `hooks`, `paths`, `shell`, `metadata`, `license`,
      `compatibility`. `[DOC]`
1.5.8 `[TRAP]` `allowed-tools` **pre-approves, it does not restrict.** It grants permission for
      the invoking turn only and clears on your next message; every other tool stays callable.
      `disallowed-tools` is the field that removes tools. `[TRAP]` `[DOC]`
1.5.9 Frontmatter is read only when the opening `---` is the file's first line; otherwise the whole
      file is content. Boolean fields accept `yes/no/on/off/1/0`. `[DOC]` `[VERSION]` `[TRAP]`
1.5.10 Who invokes: `disable-model-invocation: true` for human-only workflows,
       `user-invocable: false` for model-only background knowledge, `paths:` to gate automatic
       activation by file glob. `[DOC]`
