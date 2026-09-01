### §2.3 Hooks

2.3.21 `[CASE]` The harness's `hooks.json`: three `SessionStart` handlers plus one `PostToolUse`
       with `matcher: "Write|Edit"`, each invoking `bash "${CLAUDE_PLUGIN_ROOT}/hooks/…"`. Quote
       it whole; it is 30 lines and complete. `[CASE]`
2.3.22 `[CASE]` `check-init.sh` as a masterclass in advisory hooks. Every finding is a tagged
       instruction to the model: `[HANDBOOK_ACTIVE]`, `[HANDBOOK_SELECT]`,
       `[HARNESS_BOOTSTRAP_REQUIRED]`, `[HARNESS_UPDATE_AVAILABLE]`,
       `[PLUGIN_DEPENDENCY_UNRESOLVED]`, `[CLI_TOOLS_MISSING]`, `[LSP_SERVERS_SUGGESTED]`.
       Context injection driven by ground truth on the machine, not by model belief. `[CASE]`
2.3.23 `[CASE]` Its defensive shape: `set +e` at the top and `exit 0` at the bottom — an advisory
       hook must never break the session; timeouts and `GIT_HTTP_LOW_SPEED_*` on the network
       call; a `sha256sum`-vs-`shasum` fallback; `LC_ALL=C` so glob collation cannot vary by
       machine. `[CASE]`
2.3.24 `[CASE]` A **content hash instead of a version constant**: the bootstrap nudge hashes
       `SKILL.md` + every `bootstrap-*.sh` and compares against `.claude/.bootstrap-version`, so
       nothing needs bumping when a step is edited — and the writer and the checker must hash the
       identical file set in the identical order or every run nudges spuriously. `[CASE]`
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



