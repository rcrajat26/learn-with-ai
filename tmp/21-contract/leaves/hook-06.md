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
