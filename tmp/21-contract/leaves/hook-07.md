### §2.3 Hooks

2.3.25 `[INCIDENT]` The removed auto-reindex. This `SessionStart` hook used to pull two handbook
       clones and delta-reindex a RAG store on every session start with **no cross-session
       coordination**. Observed: every concurrent session independently decided a reindex was due,
       hundreds of concurrent embedder processes, **100+ GB** of abandoned partial indexes,
       machines unusable, and no recovery — *because starting a session was the trigger for the
       next pile-up.* State the general law: anything expensive or stateful in a `SessionStart`
       hook needs a lock or must not be there. `[INCIDENT]` `[CASE]` `[NUM]`
2.3.26 `[CASE]` `prod-guard-bash.sh` / `prod-guard-lib.sh` / `prod-guard-session-start.sh` as the
       blocking-guard pattern: a `PreToolUse` non-zero exit is the only guard the model cannot
       talk its way past. `[CASE]`
2.3.27 `[BUILD]` Write three hooks and prove each: a `PostToolUse` formatter on `Edit|Write`; a
       `PreToolUse` deny on a destructive command with a JSON `permissionDecision`; a
       `SessionStart` that injects the current branch and open-PR count. `[BUILD]` `[PROVE]`
2.3.28 `[TRAP]` A hook that reads state the model can change, or that assumes a single session, or
       that writes to a shared path without a lock. Three symptoms and three fixes. `[TRAP]`



