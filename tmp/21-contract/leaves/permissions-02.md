### §1.4 The permission system

1.4.11 **Wrapper stripping**: `timeout`, `time`, `nice`, `nohup`, `stdbuf`, `command`, `builtin`,
       `noglob`, and bare `xargs` are stripped before matching. `command -v` and `nocorrect` are
       not. Known-safe leading env assignments are stripped for allow rules; deny rules match
       past any assignment. `[DOC]` `[NUM]`
1.4.12 `[TRAP]` Environment runners are **not** stripped: `Bash(devbox run *)` matches
       `devbox run rm -rf .`. Same class: `npx`, `docker exec`, `direnv exec`, `mise exec`.
       Write runner+inner rules instead. `[TRAP]` `[DOC]`
1.4.13 Exec wrappers that a prefix rule cannot auto-approve: `watch`, `setsid`, `ionice`, `flock`,
       and `find` with `-exec`/`-delete`. `[DOC]`
1.4.14 The built-in **read-only command set** that never prompts in any mode (`ls`, `cat`, `echo`,
       `pwd`, `head`, `tail`, `grep`, `find`, `wc`, `which`, `diff`, `stat`, `du`, `cd`, read-only
       `git`), that it is not configurable, and the glob/redirect cases that still prompt. `[DOC]`
1.4.15 Redirections add a check on the target path. `[DOC]`
