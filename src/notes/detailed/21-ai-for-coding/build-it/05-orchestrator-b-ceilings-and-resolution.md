# 21 AI for Coding — absolute settings, and resolution order — BUILD IT (§4.5.3–4.5.4)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 4 of 6** | [Index](../00-index.md)
Previous: [`ClaudeRunner`: the process boundary](05-orchestrator-a-the-runner.md) · Next: [the bulkhead and the bounded retry](06-orchestrator-c-bulkhead-and-retry.md)

The previous file's `ClaudeRunner` had one job: turn a `claude -p --output-format json` subprocess
into a typed `ClaudeEnvelope`, with three ceilings guarding turns, dollars and wall-clock time. This
file adds the two things a caller needs before that class is safe to point at a real, multi-worktree
CI fleet: an absolute `--settings` path that survives a launcher moving `cwd` out from under it, and
a resolution chain — parameter, then environment, then default — for every knob, built so that an
explicit `0` never gets silently promoted back into a default. Both extend the exact class from the
previous file. Nothing already proven is retested from scratch; nothing already working is rewritten.

## `--settings <absolute path>`, and the incident it prevents [BUILD] [JAVA] (§4.5.3)

### Mental model

A `claude -p` call reading its settings the ordinary way is like a Spring Boot service reading
`application.yml` from `classpath:` — it works as long as the process starts from where the author
expected. `--settings <absolute path>` is the equivalent of pinning that lookup to
`file:/etc/myservice/application.yml` instead: the value comes from a specific place on disk,
stated once, that no launcher, container, or worktree can move out from under it.

### Why it exists

`setting-sources-incident/03-internals-a-the-failure.md` and
`setting-sources-incident/03-internals-b-the-fix-and-the-law.md` walk the real incident this flag
fixes in full; this leaf's obligation is to carry it accurately into the Java artefact, not to
re-derive it. The shape: `sdlc-harness`'s coder and reviewer legs each run inside an isolated
per-story `git worktree` (`workspace.py`'s `ensure_worktree`), so their `cwd` is the worktree, never
the harness repository. `--setting-sources project` resolves `.claude/settings.json` from the
session's **primary working directory**, with no worktree fallback — unlike
`.claude/settings.local.json`, which the documentation explicitly redirects to the main checkout's
root. When one such worktree had no `.claude/` of its own (AP-11470, 2026-07-08), the harness's own
`Bash(*)` allow rule never loaded, and the coder was left on the bare `acceptEdits` mode default.

**Two caveats the incident files established, carried here without overstating them:**

- A plain `git worktree add` normally *does* check out a tracked `.claude/settings.json` along with
  everything else — the incident files' own reproduction confirms this. What made *this specific*
  worktree lack one is not established anywhere in the repository or its docs; only that lacking one
  is exactly the condition `--settings <absolute path>` survives, regardless of the reason it arose.
- The harness's destructive-command deny-list was **not** dropped by this bug. ADR 0026 places it at
  **user** scope (`~/.claude/settings.json`), which resolves independently of `cwd` and was already
  loading correctly through `--setting-sources user,project`. The run was **under-permissioned, not
  unguarded** — the symptom was safe commands refused, never a destructive command let through.

### When to reach for it, and when not

Reach for `--settings <absolute path>` whenever the process launching `claude -p` does not control,
or cannot guarantee, its own `cwd` — a per-story worktree, a container mount, a CI checkout step, a
`cron` job. Skip it for an interactive session started by an engineer sitting in the repository root
by hand, where `cwd` already is the intended directory and `--setting-sources project` resolves
correctly on its own; adding an absolute path there buys nothing and adds one more thing to keep in
sync with the repository's actual settings file if it moves.

### How it works

`[DOC]` Re-verified against `cli-reference`, 2026-08-30: `--settings` "Path to a settings JSON file
or an inline JSON string. Values you set here override the same keys in your `settings.json` files
for this session. Keys you omit keep their file-based values. The file must be a regular file no
larger than 2 MiB." `[NUM]` The 2 MiB cap and the per-session, key-level override behavior are both
load-bearing: the flag does not replace the whole settings tree, it layers on top of it, one key at
a time, for the one process it is passed to — the same *session-scoped* precedence position
`cli-reference` and `settings` both place command-line settings in, second only to managed settings
and above every file-based layer.

`[JAVA]` The reason this flag resolves the bug is that it is evaluated **independently of `cwd`**
entirely — a `--settings /abs/path/to/settings.json` argument is a string handed to the CLI, not a
directory walk performed by it. This is the general law `setting-sources-incident/03-internals-b-…`
draws from four separate `cwd`-shaped bugs across this whole guide (`${CLAUDE_PLUGIN_ROOT}`, hook
command paths, this incident, and a bare `cron` job with a relative script path): **a path resolved
against `cwd` is a bug wherever `cwd` is not the thing the author had in mind. Resolve absolutely, or
derive the root explicitly and refuse with a clear message, rather than inventing a fallback.**
`ClaudeRunner` takes the "resolve absolutely" branch of that law — it never attempts to derive a
repository root itself; the caller supplies an already-absolute path or nothing.

No new diagram for this leaf. D-96, embedded in the previous file, already draws `ClaudeRunner`'s
process boundary with a note that `--settings` arrives in a later file — this is that file — and
D-82, in `headless/03-internals-d-resolution-order.md`, draws the resolution chain §4.5.4 below
builds in Java. The six-link SVG chain for both leaves is satisfied by those two existing pointers;
neither is re-embedded here.

### Code — the artefact for §4.5.3

Everything from the §4.5.1–4.5.2 listing is **unchanged**: `ClaudeEnvelope`, the three exception
classes and the `AgentCeilingException` sealed interface, `parseOrCaptureSnippet`, `toEnvelope`,
`joinQuietly`, and `StreamCapture` — none of them are reprinted below. What §4.5.3 adds is one new
field, `settingsPath`, and the comment-plus-flag block inside `run()` that is this leaf's actual
deliverable — the comment is not decoration, it is the artefact a maintainer reads before ever
touching this method again:

```java
    private final String settingsPath; // nullable: the one two-tier knob, no default

    public ClaudeEnvelope run(String prompt) throws IOException, InterruptedException {
        List<String> command = new ArrayList<>(List.of(
                "claude", "-p", prompt,
                "--output-format", "json",
                "--max-turns", String.valueOf(maxTurns),
                "--max-budget-usd", String.valueOf(maxBudgetUsd),
                "--permission-mode", permissionMode,
                "--setting-sources", settingSources));

        // §4.5.3 — the §3.7 incident this flag exists to prevent.
        //
        // sdlc-harness's coder/reviewer legs run headless inside an isolated
        // per-story git worktree (workspace.py's ensure_worktree), so their `cwd`
        // is the worktree, never the harness repo. `--setting-sources project`
        // resolves `.claude/settings.json` from the session's PRIMARY WORKING
        // DIRECTORY with no worktree fallback — unlike `.claude/settings.local.json`,
        // which the docs explicitly redirect to the main checkout's root. When the
        // worktree had no `.claude/` of its own (AP-11470, 2026-07-08, see
        // docs/adr/0016's Follow-up), the harness's own `Bash(*)` allow rule never
        // loaded, and the coder was left on the bare `acceptEdits` mode default:
        // Read/Edit and the seven-command filesystem allowlist (mkdir, touch, rm,
        // rmdir, mv, cp, sed) kept working, while `mvn`, `git commit`, `chmod` and
        // `java` were all hard-denied with no human present to approve them. Two
        // caveats worth keeping precise, not overstated: (1) a plain worktree
        // normally DOES inherit a tracked `.claude/settings.json` via the ordinary
        // `git worktree add` checkout, so what made THIS worktree lack one is not
        // established, only that lacking one is exactly what this flag survives
        // regardless of the reason; (2) the harness's destructive-command deny-list
        // was NOT dropped by this bug — ADR 0026 places it at USER scope
        // (`~/.claude/settings.json`), which resolves independently of `cwd` and
        // was already loading correctly. The run was under-permissioned, not
        // unguarded. The general law: a path resolved against `cwd` is a bug
        // wherever `cwd` is not the directory the author had in mind — resolve
        // absolutely, or derive the root explicitly and refuse with a clear
        // message, rather than falling back silently. `--settings <absolute path>`
        // is the "resolve absolutely" half of that law: evaluated independently of
        // `cwd`, it loads regardless of which directory this process happens to be
        // launched from.
        if (settingsPath != null) {
            command.add("--settings");
            command.add(settingsPath);
        }

        Process process = new ProcessBuilder(command).start();
        // ... unchanged from §4.5.2 below this line: stream draining, waitFor,
        // parseOrCaptureSnippet, toEnvelope, the ceiling-subtype check.
    }
```

`permissionMode` and `settingSources` also appear in the command line here for the first time —
D-96's caption in the previous file named both as arriving in a later file, and §4.5.4 below is what
resolves their values, so they are introduced together with the fields that supply them rather than
hardcoded here.

### Prove it — §4.5.3

Real, against the installed `claude 2.1.251`, from `/tmp/claude-runner-test` — a settings file
whose only content is a `Bash(echo:*)` deny rule, exercised with and without `--settings`:

```
$ cat /tmp/claude-runner-test/settings-demo.json
{
  "permissions": {
    "deny": ["Bash(echo:*)"]
  }
}

$ claude -p "Run: echo settings-test-marker" --output-format json --permission-mode acceptEdits --max-turns 5
..."is_error":false,"num_turns":2,"subtype":"success"...,"result":"`settings-test-marker`",...

$ claude -p "Run: echo settings-test-marker" --output-format json --permission-mode acceptEdits --max-turns 5 \
    --settings /tmp/claude-runner-test/settings-demo.json
...,"permission_denials":[{"tool_name":"Bash","tool_use_id":"toolu_01PUoEE8jCNcPHjeaNDubvdJ",
"tool_input":{"command":"echo settings-test-marker","description":"Echo test marker"}}],...,
"is_error":false,"num_turns":2,"subtype":"success",...,"result":"Permission denied — the command wasn't run.",...
```

Same prompt, same flags, only `--settings` added — the first call's `echo` runs and prints the
marker; the second call's `permission_denials` array is populated and the command never executes.
`ClaudeRunner`'s own `main` reproduces this through the class rather than the bare CLI:

```
$ java -cp "out:$CP" ClaudeRunner
baseline (no --settings): isError=false result-bearing stdout length=2021
with --settings deny-Bash(echo:*): isError=false permission_denials populated=true
```

`isError` stays `false` in both cases — a denied tool call is not itself an agent error, it is the
agent successfully reporting that a tool it tried to use was refused, the same `is_error`/exit-code
independence the previous file's pitfall names. What changed between the two runs is entirely
attributable to the `--settings` flag, launched from the same `cwd` both times — proof the flag's
effect does not depend on where the process starts.

### What this costs

Both `claude -p` calls above billed together: on the order of **$0.03–$0.05** — two short prompts
against a model already warm from the previous file's session, each producing a two-turn envelope
(one turn requesting the `Bash` tool, one turn reporting the result or the denial). The `--settings`
flag itself adds no per-call cost of its own; it is a local file read the CLI performs before the
first API call, not a network round trip.

**Insight:** the same asymmetry the previous file named for `--max-budget-usd` applies here in
reverse. A budget ceiling cannot stop money already spent because it is checked between calls; a
settings file loaded via an absolute path *can* stop a Bash call before it runs, because permission
evaluation happens inside the same process, before any tool executes — the incident this flag fixes
was never about money, it was about the wrong set of rules being consulted at all.

No gotcha beyond the two caveats already stated above in full: the missing-`.claude/`-in-a-worktree
condition is not fully explained, and the deny-list survived the incident at user scope regardless.

> `--settings <absolute path>` loads a specific settings file independently of `cwd`, restoring
> exactly the permission layer a `cwd`-relative `--setting-sources project` silently drops when a
> launcher's working directory is not the repository the caller had in mind.

## Resolution order: parameter, then environment, then default — and the zero that must survive [BUILD] [JAVA] (§4.5.4)

### Mental model

Picture three checkpoints in a line, each one asked the same question about a different source: "did
someone actually hand me a value here?" — not "is the value I was handed non-zero." The first
checkpoint to answer yes wins, and the chain never proceeds past it. `headless/03-internals-d-resolution-order.md`
draws this as D-82; this leaf builds the same three-checkpoint chain in Java, for real, and proves
the one case that separates a correct implementation from a plausible-looking broken one.

### Why it exists

`headless/03-internals-d-resolution-order.md` traces the real chain in
`harness/src/harness/engine/agent.py`: five environment-backed knobs —
`HARNESS_AGENT_MAX_TURNS`, `HARNESS_AGENT_TIMEOUT`, `HARNESS_PERMISSION_MODE`,
`HARNESS_SETTING_SOURCES`, `HARNESS_AGENT_SETTINGS` — each paired with a module default
(`DEFAULT_PERMISSION_MODE = "acceptEdits"`, `DEFAULT_SETTING_SOURCES = "user,project"`,
`DEFAULT_TIMEOUT = 1800`, `DEFAULT_MAX_TURNS = 160`), so that tuning any one of them for a real run
never requires editing the module and redeploying. The file's central finding: every check in the
chain tests **presence**, not **truthiness** — `is not None` in Python — and the diagram's worked
example is `max_turns=0`: a resolution chain written the "obvious" way, `value or env or default`,
cannot tell "the caller explicitly chose zero" from "the caller passed nothing," and silently
replaces a deliberate `0` with `160`.

`[JAVA]` In Java the same bug wears different clothes. Python's `None` is one reserved value every
type can hold; Java's primitive `int` has no equivalent — it can only ever hold a number, never
"absent." A resolution chain built on a primitive `int maxTurns` field cannot distinguish "the
caller never touched this parameter" from "the caller explicitly passed `0`" no matter how it is
written, because the type itself has already thrown away the distinction before any `if` statement
runs. That is exactly why Java's boxed wrapper types (`Integer`, `Long`, `Double`) and `Optional`
exist: a boxed `Integer` can be `null`, and `null` is Java's own reserved "nothing was passed" value,
the direct analogue of Python's `None`.

### When to reach for it, and when not

Use a presence check (`!= null` on a boxed type) for any knob whose zero, empty string, or `false` is
a legitimate value a caller might deliberately choose — `maxTurns`, a timeout, a budget cap. Plain
truthiness (a blank-string check) is fine, and no less correct, for a knob like `permissionMode`
where an empty string is never a value anyone means to pass — the two checks agree there, so reaching
for the heavier `Optional`/boxed-null machinery buys nothing. Applying presence checking uniformly
where it is not needed is not wrong, only unnecessary ceremony; applying truthiness where presence
was needed is the actual bug.

### How it works

Each of five knobs resolves through up to three tiers. Four of them — `maxTurns`, `timeoutSeconds`,
`permissionMode`, `settingSources` — get parameter → environment → default in full. `settingsPath`
gets only two tiers, parameter → environment, with **no default** — the same shape the Python
original's `settings` knob has, for the same reason: there is no safe hardcoded settings path the
way there is a safe default permission mode, and a wrong guess would either point at nothing or,
worse, at some other invocation's settings file entirely.

| Knob | Env var | Default | Tiers | Falsy value meaningful? |
|---|---|---|---|---|
| `maxTurns` | `HARNESS_AGENT_MAX_TURNS` | `DEFAULT_MAX_TURNS = 160` | 3 | Yes — `0` is a real caller choice |
| `timeoutSeconds` | `HARNESS_AGENT_TIMEOUT` | `DEFAULT_TIMEOUT_SECONDS = 1800` | 3 | Yes — same reasoning as `maxTurns` |
| `permissionMode` | `HARNESS_PERMISSION_MODE` | `DEFAULT_PERMISSION_MODE = "acceptEdits"` | 3 | No — empty string is never a deliberate value |
| `settingSources` | `HARNESS_SETTING_SOURCES` | `DEFAULT_SETTING_SOURCES = "user,project"` | 3 | No — same as above |
| `settingsPath` | `HARNESS_AGENT_SETTINGS` | none | 2 | N/A — falls through to omitting `--settings` entirely |

`maxBudgetUsd` is not in this table: it is not one of the five `HARNESS_*` knobs the real harness
exposes at all, so `ClaudeRunner` gives it exactly one resolution tier — the caller's own explicit
value, or an in-process default with no environment override — rather than inventing an environment
name the real system does not have.

**Pitfall:** writing the "obvious" chain, `paramValue > 0 ? paramValue : ...`, or its Java-flavored
primitive-`int` cousin, `paramValue != 0 ? paramValue : ...`, for a knob whose zero is meaningful.
The symptom, proven below: an explicit `--max-turns 0` silently becomes `160`, and nothing errors —
the caller's instruction is simply replaced by its opposite. **The fix:** resolve through a boxed
type and test `!= null`, never `!= 0` or `> 0`, for exactly the knobs where zero is a real choice.
**Why people believe it:** a primitive `int` parameter looks like the natural, lightweight choice for
"a number the caller might pass," and the ambiguity it introduces has no compiler warning attached —
the code compiles and runs correctly for every value except the one that matters.

### Code — the artefact for §4.5.4

Unchanged from §4.5.1–4.5.3: `ClaudeEnvelope`, the exception hierarchy, `parseOrCaptureSnippet`,
`toEnvelope`, `joinQuietly`, `StreamCapture`, and the `run()` method's `--settings` block added
above. What §4.5.4 adds: the env-var and default constants, the private constructor taking already-
resolved values, and the `resolve` factory plus its four helper methods — including the deliberately
broken version, kept only to be proven wrong in the prove step below and never called from
`resolve` itself:

```java
    // Recognisably parallel to harness/src/harness/engine/agent.py's own
    // HARNESS_AGENT_MAX_TURNS / HARNESS_AGENT_TIMEOUT / HARNESS_PERMISSION_MODE /
    // HARNESS_SETTING_SOURCES / HARNESS_AGENT_SETTINGS and their DEFAULT_* constants.
    private static final String MAX_TURNS_ENV = "HARNESS_AGENT_MAX_TURNS";
    private static final String TIMEOUT_ENV = "HARNESS_AGENT_TIMEOUT";
    private static final String PERMISSION_MODE_ENV = "HARNESS_PERMISSION_MODE";
    private static final String SETTING_SOURCES_ENV = "HARNESS_SETTING_SOURCES";
    private static final String SETTINGS_PATH_ENV = "HARNESS_AGENT_SETTINGS";

    private static final int DEFAULT_MAX_TURNS = 160;
    private static final long DEFAULT_TIMEOUT_SECONDS = 1800;
    private static final String DEFAULT_PERMISSION_MODE = "acceptEdits";
    private static final String DEFAULT_SETTING_SOURCES = "user,project";
    // No DEFAULT_SETTINGS_PATH constant, deliberately — same reason the Python
    // resolution chain has none: a wrong hardcoded path is worse than no path,
    // since it could silently point at some other invocation's settings file.

    private final String permissionMode;
    private final String settingSources;

    private ClaudeRunner(int maxTurns, double maxBudgetUsd, Duration timeout,
                          String permissionMode, String settingSources, String settingsPath) {
        this.maxTurns = maxTurns;
        this.maxBudgetUsd = maxBudgetUsd;
        this.timeout = timeout;
        this.permissionMode = permissionMode;
        this.settingSources = settingSources;
        this.settingsPath = settingsPath;
    }

    public static ClaudeRunner resolve(Integer maxTurns,
                                        Double maxBudgetUsd,
                                        Long timeoutSeconds,
                                        String permissionMode,
                                        String settingSources,
                                        String settingsPath,
                                        Map<String, String> env) {
        int resolvedMaxTurns = resolveMaxTurns(maxTurns, env);
        long resolvedTimeoutSeconds = resolveLong(timeoutSeconds, env.get(TIMEOUT_ENV), DEFAULT_TIMEOUT_SECONDS);
        String resolvedPermissionMode = resolveString(permissionMode, env.get(PERMISSION_MODE_ENV), DEFAULT_PERMISSION_MODE);
        String resolvedSettingSources = resolveString(settingSources, env.get(SETTING_SOURCES_ENV), DEFAULT_SETTING_SOURCES);
        // Two tiers only, like the Python `settings` knob: parameter, then env,
        // then null — never a hardcoded default path.
        String resolvedSettingsPath = settingsPath != null ? settingsPath : env.get(SETTINGS_PATH_ENV);
        // maxBudgetUsd has no environment tier in the real harness at all — it is
        // not one of the five knobs run_agent exposes through HARNESS_* — so it
        // resolves through exactly one tier: the caller's own explicit value, or
        // a conservative in-process default with no env override.
        double resolvedMaxBudgetUsd = maxBudgetUsd != null ? maxBudgetUsd : 1.00;

        return new ClaudeRunner(resolvedMaxTurns, resolvedMaxBudgetUsd,
                Duration.ofSeconds(resolvedTimeoutSeconds), resolvedPermissionMode,
                resolvedSettingSources, resolvedSettingsPath);
    }

    /**
     * The right version: a boxed {@code Integer} parameter, checked for {@code null}
     * — presence, not truthiness — so an explicit {@code 0} survives every tier.
     */
    private static int resolveMaxTurns(Integer paramMaxTurns, Map<String, String> env) {
        if (paramMaxTurns != null) {
            return paramMaxTurns;
        }
        String fromEnv = env.get(MAX_TURNS_ENV);
        if (fromEnv != null) {
            return Integer.parseInt(fromEnv);
        }
        return DEFAULT_MAX_TURNS;
    }

    /**
     * The wrong version, kept here only to be proven wrong below, never called from
     * {@link #resolve}. A primitive {@code int} cannot represent "the caller didn't
     * pass anything" — {@code 0} has to serve double duty as both "explicit zero"
     * and "the sentinel for unset," so this line cannot tell them apart.
     */
    private static int brokenResolveMaxTurns(int paramMaxTurns, Map<String, String> env) {
        if (paramMaxTurns != 0) {
            return paramMaxTurns;
        }
        String fromEnv = env.get(MAX_TURNS_ENV);
        return fromEnv != null ? Integer.parseInt(fromEnv) : DEFAULT_MAX_TURNS;
    }

    private static long resolveLong(Long paramValue, String envValue, long defaultValue) {
        if (paramValue != null) {
            return paramValue;
        }
        if (envValue != null) {
            return Long.parseLong(envValue);
        }
        return defaultValue;
    }

    private static String resolveString(String paramValue, String envValue, String defaultValue) {
        if (paramValue != null && !paramValue.isBlank()) {
            return paramValue;
        }
        if (envValue != null && !envValue.isBlank()) {
            return envValue;
        }
        return defaultValue;
    }
```

### Prove it — §4.5.4

Real, against the same compiled class, no mock objects:

```
$ java -cp "out:$CP" ClaudeRunner
resolveMaxTurns(0, {}) = 0
resolveMaxTurns(null, {}) = 160
brokenResolveMaxTurns(0, {}) = 160 (should have been 0; the primitive can't tell zero from unset)
resolveMaxTurns(null, {HARNESS_AGENT_MAX_TURNS=5}) = 5
```

`[PROVE]` Line by line: `resolveMaxTurns(0, {})` returns `0` — the explicit zero survives, exactly
D-82's worked example landed in Java. `resolveMaxTurns(null, {})` returns `160` — an absent parameter
correctly falls through to `DEFAULT_MAX_TURNS`. `brokenResolveMaxTurns(0, {})` returns `160`, not
`0` — the wrong version, called with the identical input `resolveMaxTurns` handled correctly, cannot
tell "explicit zero" from "unset" because both look identical to `paramMaxTurns != 0`, and silently
produces the default instead of honoring the caller's instruction. `resolveMaxTurns(null, {HARNESS_AGENT_MAX_TURNS=5})`
returns `5` — the environment tier fires correctly when the parameter tier is absent.

### What this costs

Nothing in tokens or dollars — every call in this section's prove step is pure Java, no subprocess,
no network, no `claude` invocation. That is deliberate: a resolution bug does not need an LLM in the
loop to reproduce or to fix, and testing it as pure Java rather than through a live `claude -p` call
is both cheaper and more precise, since the assertion is about Java's own type system, not about
anything the CLI does.

**Insight:** the entire defect and its fix live in the type signature, not in the logic inside the
method. `resolveMaxTurns(Integer paramMaxTurns, ...)` and `brokenResolveMaxTurns(int paramMaxTurns, ...)`
differ in exactly one place — boxed versus primitive — and that one difference is what makes the
first method capable of expressing "absent" at all. No amount of care inside the method body fixes a
primitive parameter; the type has already discarded the information the method needs.

No gotcha beyond the pitfall already stated in full above.

> A resolution chain must test **presence**, not **truthiness**, for every knob whose zero, empty
> string, or `false` is a legitimate explicit choice — a boxed type checked for `null` in Java, `is
> not None` in Python — because a primitive type or a truthiness check cannot represent "nothing was
> passed" at all, and silently substitutes the default for the caller's own explicit zero.

---

**What the next file adds:** §4.5.5–4.5.6, `build-it/06-orchestrator-c-bulkhead-and-retry.md` —
a `Semaphore` bulkhead bounding how many `ClaudeRunner.run()` calls may execute concurrently, and a
bounded retry that preserves the last parsed envelope across attempts rather than discarding it on
each failure.

## Pitfalls

- **Belief:** `--setting-sources project` loads "the project's settings" in the everyday sense — the
  repository the engineer thinks of as home. **Symptom:** inside a launcher that sets `cwd` to
  anything other than the repository root (a worktree, a container, a CI checkout), the flag resolves
  `.claude/settings.json` against that other directory and silently finds nothing there, with no
  error. **Fix:** pass `--settings <absolute path>` whenever the launching process does not control
  its own `cwd`. **Why people believe it:** `.claude/settings.local.json` genuinely does redirect to
  the main checkout's root inside a worktree, so the belief generalizes past the one file it is
  actually documented for.
- **Belief:** a resolution chain written `value or env or default` (or its Java cousin, `value != 0
  ? value : ...`) is a safe, idiomatic way to layer configuration sources. **Symptom:** an explicit
  `0`, `""`, or `false` — a caller's deliberate choice — is silently replaced by the environment or
  default tier, with no error, because the falsy check cannot distinguish "explicitly chosen" from
  "not passed." **Fix:** test presence (`is not None` in Python, `!= null` on a boxed type in Java)
  for every knob whose falsy value is meaningful; reserve truthiness checks for knobs, like a
  permission mode string, where the two checks always agree. **Why people believe it:** the
  short-circuit form reads as terse, idiomatic code, and it is correct for the majority of knobs in
  the same function — the trap is applying it uniformly to the one knob where it silently breaks.

## Cheat sheet

| Concern | Mechanism | Detail |
|---|---|---|
| Absolute settings | `--settings <absolute path>` | evaluated independently of `cwd`; accepts a path or inline JSON; overrides matching keys per session; 2 MiB file cap |
| The incident it fixes | `--setting-sources project` resolves against `cwd` | per-story worktree has a different `cwd` than the harness repo; no worktree fallback for `.claude/settings.json` (unlike `.claude/settings.local.json`) |
| What broke | Harness's `Bash(*)` allow rule never loaded | `mvn`, `git commit`, `chmod`, `java` refused; `acceptEdits`'s own seven-command filesystem allowlist kept working |
| What did NOT break | The destructive-command deny-list | Lives at **user** scope (ADR 0026), resolves independently of `cwd`, was never dropped |
| Resolution order | parameter → environment → default | tested by presence, not truthiness, wherever the falsy value is meaningful |
| The knob with only 2 tiers | `settingsPath` / `HARNESS_AGENT_SETTINGS` | no default — falls through to omitting `--settings` entirely |
| Presence vs truthiness in Java | boxed `Integer`/`Long` checked `!= null` vs. primitive `int` checked `!= 0` | primitive cannot represent "absent" at all |
| Env vars (recognisably parallel to the real harness) | `HARNESS_AGENT_MAX_TURNS`, `HARNESS_AGENT_TIMEOUT`, `HARNESS_PERMISSION_MODE`, `HARNESS_SETTING_SOURCES`, `HARNESS_AGENT_SETTINGS` | defaults `160`, `1800`, `"acceptEdits"`, `"user,project"`, none |

## Self-test

<details><summary>1. Why does `--settings <absolute path>` fix the worktree incident when `--setting-sources project` does not?</summary>
`--setting-sources project` only says a project layer should be consulted; it still finds that layer
by resolving `.claude/settings.json` against `cwd`, which fails silently when `cwd` is an isolated
worktree with no `.claude/` of its own. `--settings <absolute path>` names the file directly, so its
resolution never depends on `cwd` at all.
</details>

<details><summary>2. What did NOT break during the AP-11470 incident, and why not?</summary>
The harness's destructive-command deny-list did not break. ADR 0026 places it at user scope
(`~/.claude/settings.json`), which resolves from the home directory independent of `cwd`, so it kept
loading correctly through `--setting-sources user,project` even while the project-scope `Bash(*)`
allow rule was silently missing.
</details>

<details><summary>3. Why does `resolveMaxTurns(0, {})` return `0` while `brokenResolveMaxTurns(0, {})` returns `160`, given the same input?</summary>
`resolveMaxTurns` takes a boxed `Integer` and checks `!= null`, so an explicit `0` is recognized as
present and returned immediately. `brokenResolveMaxTurns` takes a primitive `int` and checks `!= 0`,
so the value `0` is indistinguishable from "nothing was passed" and falls through to the default,
`160`.
</details>

<details><summary>4. Why does `settingsPath` resolve through only two tiers instead of three?</summary>
There is no safe hardcoded default settings path, the way there is a safe default permission mode or
turn count — a wrong guess would either point at nothing or, worse, at some other invocation's
settings file. So `settingsPath` resolves parameter, then environment, and falls through to `null`
(the flag is simply omitted) rather than to a `DEFAULT_SETTINGS_PATH` constant.
</details>

<details><summary>5. Why is a truthiness check (`isBlank()`) acceptable for `permissionMode` but not for `maxTurns`?</summary>
An empty string is never a value anyone deliberately means to pass for a permission mode, so a
truthiness-style blank check and a presence check agree there — either is correct. `0` genuinely is a
value a caller might deliberately choose for `maxTurns`, so only a presence check (`!= null` on a
boxed type) distinguishes it from "not passed."
</details>

<details><summary>6. What would happen if `maxBudgetUsd` were resolved with a three-tier `HARNESS_AGENT_MAX_BUDGET` environment variable?</summary>
It would misrepresent the real harness: `max_budget_usd` is not one of the five `HARNESS_*` knobs
`run_agent` actually exposes. `ClaudeRunner` gives it exactly one resolution tier — the caller's
explicit value or an in-process default — rather than inventing an environment-variable name the
system being modeled does not have.
</details>

## Open questions

None.

---

**Leaves covered:** 4.5.3–4.5.4 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none — D-96 in the previous file draws the class and the boundary, D-82 in `headless/03-internals-d` draws the resolution chain
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 534
