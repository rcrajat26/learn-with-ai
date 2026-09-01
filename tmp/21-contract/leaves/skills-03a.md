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
