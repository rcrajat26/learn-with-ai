### §1.4 The permission system

1.4.1 The one-sentence foundation: **permission rules are enforced by Claude Code, not by the
      model.** Prompt and `CLAUDE.md` shape what Claude *tries*; rules decide what runs. `[DOC]`
      `[ZERO]`
1.4.2 The three rule lists — `allow`, `ask`, `deny` — and the evaluation order: **deny, then ask,
      then allow; first match wins; specificity does not reorder.** `[DOC]` `[NUM]`
1.4.3 `[TRAP]` A broad deny cannot carry allowlist exceptions: `Bash(aws *)` in deny blocks
      `Bash(aws s3 ls)` in allow. Same for ask over allow. `[TRAP]` `[DOC]`
1.4.4 Deny of a **bare tool name** removes the tool from Claude's context entirely; a **scoped**
      deny leaves the tool visible and blocks matching calls. Two different mechanisms. `[DOC]`
1.4.5 Rule syntax: `Tool` or `Tool(specifier)`. `Bash(*)` ≡ `Bash`. `[DOC]`
1.4.6 Bash specifiers: the rule matches the **whole command text** with `*` standing for any text.
      Put the `*` after the subcommand; the startup warning when you do not. `[DOC]` `[TRAP]`
1.4.7 The wildcard matching table, reproduced and explained: `Bash(npm run build)` vs
      `Bash(npm run *)` vs `Bash(git log * main)` vs `Bash(git * main)` vs `Bash(* --version)` vs
      `Bash(ls *)` vs `Bash(ls*)`. `[DOC]` `[PROVE]`
1.4.8 `[TRAP]` `Bash(git * main)` allows `git -c core.fsmonitor=<script> diff main` — the `*`
      spans options, including options that make git execute a program you name. `[TRAP]` `[DOC]`
1.4.9 **Compound commands**: the recognised separators (`&&`, `||`, `;`, `|`, `|&`, `&`, newline),
      and that each subcommand must match independently. `[DOC]` `[NUM]`
1.4.10 "Yes, and don't ask again" on a compound command saves a **separate rule per subcommand**,
       up to 5. `[DOC]` `[NUM]`
