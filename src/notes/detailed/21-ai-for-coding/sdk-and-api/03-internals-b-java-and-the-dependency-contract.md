# 21 AI for Coding — Java, and the dependency contract — ADVANCED (INTERNALS) (§3.8.5–3.8.8)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 3 of 6** | [Index](../00-index.md)
Previous: [three levels of building on Claude](03-internals-a-three-levels.md) · Next: [orchestration shapes and fan-out](../orchestration/03-internals-a-shapes-and-fan-out.md)

The previous file established the three levels — CLI in `-p` mode, the Agent SDK, the raw Messages API — and what each gives up, and re-verified that an SDK session's relationship to workspace trust is the same subtle case as `-p`: for a folder nobody has ever trusted, the committed `permissions.allow` rules are withheld with a `this workspace has not been trusted` stderr warning, exactly like a headless CLI run. This file closes out §3.8 with the two leaves aimed squarely at the reader's own language — the Java options at level 2/3, and what it actually means to treat a `claude -p` call the way you already treat any other remote dependency.

## §3.8.5 Agent SDK specifics: `resolveSettings()`, `managedSettings`, `parentSettingsBehavior`, and the trust shorthand `[DOC]`

**Mechanism.** Re-verified against the two permitted pages this leaf could plausibly live on — `code.claude.com/docs/en/sub-agents` and `code.claude.com/docs/en/settings` (2026-08-30) — before writing it. Neither page names `resolveSettings()`, `managedSettings`, or `parentSettingsBehavior`; the `sub-agents` page confirms the Agent SDK exists and interacts with subagent configuration (`CLAUDE_AGENT_SDK_DISABLE_BUILTIN_AGENTS`, fork-mode defaults differing "in non-interactive mode... and in the Agent SDK") but does not document these three names, and the `settings` page's own precedence table — "Managed settings" ranked above "Command line," above "Project local," above "Shared project," above "User" — confirms the five-layer order these functions compose, without naming the SDK-side function that composes it. The Agent SDK's own reference lives at `code.claude.com/docs/en/agent-sdk/`, outside the nine pages this guide's `[DOC]` obligation is scoped to, and no local install of `@anthropic-ai/claude-agent-sdk` or `claude-agent-sdk` is available in this environment to inspect directly (the technique the previous file used for the raw Messages API, reading the installed `anthropic` Python client's type definitions). This leaf therefore states the mechanism as the syllabus and D-84's own framing describe it — consistent with how §3.8.1 already treated the same three names — and marks the **exact function/field spelling** `**Unverified:**` below, rather than silently asserting it against a page that does not carry it.

Three names carry the whole leaf:

- **`resolveSettings()`** — the SDK-exposed function that composes the settings precedence chain (§1.2: managed → command line → project local → shared project → user) into one resolved object *before* the SDK assembles its first request. This is not a convenience wrapper around a file read; it is the same precedence arithmetic §1.2.2–§1.2.3 already taught, run once, up front, by SDK code instead of by the CLI binary.
- **`managedSettings`** — the top-ranked layer in that chain, sourced from an enterprise-deployed configuration file rather than anything the calling process wrote. The SDK does not let a caller opt out of `managedSettings` by omitting it from `settingSources` — it is composed regardless, which is the whole point of a layer an organization uses to enforce a floor no individual session can lower.
- **`parentSettingsBehavior`** — the knob level 1 does not expose at all. It controls whether the *calling* Node or Python process's already-loaded settings apply to the SDK session it spawns. `"isolated"` starts settings resolution clean, ignoring whatever the parent process had loaded; the alternative lets the parent's resolved settings flow into the child SDK session. A service that spawns many short-lived SDK sessions inside one long-running process almost always wants `"isolated"` — otherwise the first session's resolved settings quietly become every later session's floor, an inheritance nobody asked for.

**Gotcha — the trust shorthand, restated precisely so it does not drift back into folklore.** §3.8.1's gotcha already re-verified this in full; the compressed form worth carrying forward here is: **"SDK session counts as trusted" names one narrow internal check — whether an untracked `.claude/settings.local.json` is treated as the caller's own file — never the general permission surface.** For a repository nobody has trusted, `resolveSettings()` still withholds the committed `permissions.allow` list and `additionalDirectories`, with the identical stderr warning a `-p` run prints. Wiring the Agent SDK into a service buys none of the trust `-p` does not already have.

> `resolveSettings()` is the SDK doing §1.2's precedence chain on the caller's behalf, `managedSettings` is the layer no session can opt out of, and `parentSettingsBehavior` is the one knob — inherit the spawning process's settings, or start clean — that only exists at this level.

## §3.8.6 Why the harness chose subprocesses over the SDK `[CASE]`

**Mechanism.** The previous file already quoted `harness/src/harness/engine/agent.py`'s module docstring and RFC 0001's "SDK quarantine" line for the process-isolation-as-test-seam and vendor-neutrality arguments — read it there rather than here. This leaf's obligation is the two remaining reasons the syllabus names: **the same binary engineers use interactively**, and **no SDK version coupling**. Both are stated explicitly, in different words, in `docs/adr/0016-deterministic-stateless-engine.md`'s Decision section, point 4:

```
4. **Agents via `claude -p --agent <persona>`.** This loads the *registered* agent
   (`~/.claude/agents/self-review.md`, `backend-architect.md`, …) with its own system
   prompt, tools, and model — the parity mechanism for an auto-spawned subagent. We do
   **not** use `--append-system-prompt` as the identity mechanism (it only appends to the
   default prompt). Model is overridden to `sonnet` per the workflow (personas default to
   opus). The per-run brief (instruction + plan + RFC + prior feedback) is the `-p` task.
```

**Same binary, named as "parity."** The ADR calls `--agent <persona>` "the parity mechanism for an auto-spawned subagent" — the exact registered `.claude/agents/*.md` file (system prompt, tool grants, model) that a human engineer's interactive Claude Code session would load for that same subagent is the file the harness's `claude -p` subprocess loads too. There is no second, SDK-side definition of what `backend-architect` means to keep in sync; one file, one binary, one behavior, whether a human triggers it from a terminal or the harness triggers it from a Python loop. Point 6 of the same ADR extends the same argument to permissions: `--setting-sources user,project` inherits `.claude/settings.json` — "including its 16 deny rules" — rather than the harness re-encoding its own idea of what is forbidden. Choosing the Agent SDK here would mean re-deriving both the persona-loading semantics and the settings-precedence semantics inside SDK-specific code, maintained separately from the CLI's, with no guarantee the two stay identical release over release.

**No SDK version coupling, named as a cost the harness would rather not carry.** §3.8.1's cheat sheet already states the general shape: an Agent SDK package version and the installed `claude` binary version must be compatible, a mismatch is a real failure mode, and a `-p` subprocess call carries none of that coupling — the harness depends only on the CLI's documented flags and its JSON output shape, both of which are the same interactively-used surface that changes far more conservatively release to release than an in-process library's type signatures would. `agent.py`'s own module docstring frames the same subprocess call as "stateless: a fresh `claude -p` per call, full brief in, one JSON envelope out" — a contract that is exactly as stable as the CLI's own command-line interface, independent of whichever language SDK version happens to be installed in the harness's Python environment that week.

**Why it would break under level 2.** An Agent SDK session in Python or TypeScript does not load a `.claude/agents/*.md` file by path the way `--agent <persona>` does — it registers tool handlers and a system prompt in code, at the call site. Porting the harness to the SDK would mean either duplicating every persona's system prompt and tool grants into SDK-side registration code (immediately divergent from the file an interactive engineer edits) or building a loader that re-reads the same `.md` files and reconstructs the SDK's registration calls from them — new code, a new failure surface, for a guarantee the subprocess boundary already gives away for free.

## §3.8.7 The Java view: no first-party Java SDK `[JAVA]`

**Mechanism.** Anthropic ships the Agent SDK for TypeScript and Python only; **Unverified:** whether a first-party Java client exists for the raw Messages API itself (distinct from the Agent SDK) was already flagged as an open question in the previous file and is not re-litigated here. What is settled, and is this leaf's actual content, is that a Java 21 caller has exactly two honest routes, corresponding to level 3 and level 1 of §3.8.1's table, and no route corresponding to level 2 — there is no `resolveSettings()`, no `parentSettingsBehavior`, nothing to call.

**Route A — `HttpClient` against the raw Messages API (level 3 semantics).** JDK 21's `java.net.http.HttpClient` is enough; no third-party HTTP library is required.

```java
HttpClient client = HttpClient.newHttpClient();

String requestBody = """
    {
      "model": "claude-opus-4-6-20260115",
      "max_tokens": 1024,
      "system": "You are a build-fix assistant for a Java 21 / Spring Boot 3.x repository.",
      "messages": [
        {"role": "user", "content": "The build fails with a NullPointerException in ClaudeRunner.parseEnvelope. Diagnose it."}
      ],
      "tools": []
    }
    """;

HttpRequest request = HttpRequest.newBuilder()
        .uri(URI.create("https://api.anthropic.com/v1/messages"))
        .header("x-api-key", System.getenv("ANTHROPIC_API_KEY"))
        .header("anthropic-version", "2023-06-01")
        .header("content-type", "application/json")
        .timeout(Duration.ofSeconds(60))
        .POST(HttpRequest.BodyPublishers.ofString(requestBody))
        .build();

HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
```

Every responsibility §3.8.3's Python loop demonstrated missing by construction — parsing `content` for `tool_use` blocks, dispatching them, appending `tool_result` blocks, re-calling, bounding the loop with your own turn count — is equally missing here and equally yours to write; the Java route to level 3 gives up exactly what the Python route gives up, because it is the same API.

**Route B — `ProcessBuilder` around the CLI (level 1 semantics).** This is the harness's own choice (§3.8.6), ported to Java:

```java
ProcessBuilder builder = new ProcessBuilder(
        "claude", "-p", "Summarize the failing tests in this repository and propose one fix.",
        "--output-format", "json",
        "--max-turns", "20",
        "--permission-mode", "acceptEdits",
        "--setting-sources", "user,project"
);
builder.directory(new File("/repo/worktrees/story-4471"));
builder.redirectErrorStream(false);

Process process = builder.start();
boolean finished = process.waitFor(Duration.ofSeconds(1800));
if (!finished) {
    process.destroyForcibly();
    throw new AgentTimeoutException("claude -p exceeded the 1800s wall-clock bound");
}
String stdout = new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
```

**The place the analogy breaks, stated precisely as `[JAVA]` requires.** "`ProcessBuilder` around `claude -p` is like calling a REST client" is not enough on its own — the break is that a `Process` gives you raw bytes on `stdout`/`stderr` and an exit code, never a typed response object; every one of the Messages API's typed fields (`stop_reason`, `usage.input_tokens`, the `ToolUseBlock` shape §3.8.3 read from the installed Python client) exists here only as whatever your own JSON parsing recovers from the `--output-format json` envelope's text. Route A gets typed fields for free from an HTTP client library that understands the API's schema; Route B gets a subprocess boundary and pays for typed fields with your own deserialization code.

| | Route A — `HttpClient` (level 3) | Route B — `ProcessBuilder` (level 1) |
|---|---|---|
| What ships | JDK 21 standard library only | JDK 21 standard library only, plus the installed `claude` binary |
| Loop ownership | Yours — read `tool_use`, dispatch, re-call | The CLI's — invisible, you get the final envelope |
| Settings/permissions | None — you build it | `.claude/settings.json` and friends, unmodified (subject to §3.8.1's trust caveat) |
| Version coupling | To the Messages API's stability guarantees only | None to Claude Code — the CLI binary versions independently |
| Typed response | Only what you deserialize yourself | Only what you deserialize yourself, from noisier text |
| Java maturity | JDK 21 idiomatic, no external dependency | JDK 21 idiomatic, no external dependency |

**Code — the shape this becomes at scale.** PART 4 §4.5 builds Route B out into a full `ClaudeRunner` class across eight leaves, with a `ClaudeEnvelope` record replacing the raw `String stdout` above and named exception types (`AgentTimeoutException`, `AgentTurnLimitException`, `AgentBudgetExceededException`) replacing the bare `throw` shown here. See `build-it/05-orchestrator-a-the-runner.md`; it is not rebuilt in this file.

**Gotcha:** `Process.waitFor(Duration)` returns `false` on timeout — it does **not** throw and does **not** kill the process for you. A `ProcessBuilder` caller who checks only the return value of `waitFor()` without an `if (!finished) process.destroyForcibly()` branch leaves an orphaned `claude` subprocess running past the caller's own timeout, still burning tokens toward whatever budget it was given.

> Java has no first-party Agent SDK; the two honest routes are a JDK 21 `HttpClient` call against the raw Messages API (level 3 semantics, typed nothing, your own loop) or a `ProcessBuilder` around `claude -p` (level 1 semantics, the harness's own choice, typed nothing either, but the loop is not yours to write).

## §3.8.8 An agent call is a remote dependency `[X-REF 12]` `[JAVA]`

**One self-contained paragraph, per the cross-reference rule.** `src/topics/12-api-design.md` owns the general treatment of REST contracts, idempotency keys, versioning and rate limiting; the mechanism worth carrying here in full is its idempotency-key pattern (§5 of that guide): a client-generated key, an insert-first row with a UNIQUE constraint so a concurrent duplicate is rejected at the database rather than raced in application code, the work and its response recorded in the same transaction, a replay returning the stored response on a `COMPLETED` row, and a `409` on a row still `IN_PROGRESS` — the mechanism that makes a retried `POST` safe rather than merely convenient. Read that guide's §5 for the full walkthrough, including the SQL and the state machine; this leaf does not repeat it.

**The framing.** A `claude -p` subprocess on localhost has every property that makes an HTTP call to another service worth wrapping in resilience patterns: unbounded latency (a stuck tool call, a model that keeps calling `run_build` because the fix never lands — §3.8.3's gotcha, unbounded here too), partial failure (the process dies mid-run, or returns malformed stdout), non-determinism (§0.1's "same input, different output" applies per retry), and a real cost per call (§3.4's four billed quantities, non-zero even on a failed attempt). An engineer who would never call a payment API without a timeout routinely shells out to an agent with none. Treating the call as a remote dependency means the same five reflexes apply, mapped onto the concrete mechanism this dependency actually has.

![D-85 — An agent call is a remote dependency: five rings the reader already knows, mapped onto `claude -p`.](../diagrams/D-85-agent-call-as-remote-dependency.svg)

**D-85** — An agent call is a remote dependency. Five rings the reader already knows, mapped onto `claude -p`.

| Ring | Standard mechanism | Mapped onto `claude -p` | Where it's exact / where it isn't |
|---|---|---|---|
| Timeout | A wall-clock deadline on the call | The subprocess's wall-clock kill — `harness/src/harness/engine/agent.py`'s `DEFAULT_TIMEOUT = 1800` (seconds), enforced via `subprocess.run(..., timeout=resolved_timeout)`, catching `subprocess.TimeoutExpired` | Exact. A stuck `claude -p` is killed the same way a stuck HTTP call is aborted by a client-side deadline. |
| Retry with backoff | Bounded retries, backing off between attempts, on a classified-retryable failure | `run_agent`'s own loop: `for _ in range(max(1, retries))`, default `retries=3`, re-invoking the full command on a launch failure, a timeout, or an unparseable envelope | **Not clean.** See below — retry here is bounded *and classified*, not blanket. |
| Idempotency | A client-supplied key that lets a safe retry resume rather than duplicate | The envelope's `session_id`, reused via `claude -p --resume <id>` | **Weaker than a REST idempotency key.** See below. |
| Circuit breaker | Trip on a sustained failure rate, short-circuit further calls without paying for them | A failure-rate trip over recent `AgentResult.is_error` outcomes, external to `agent.py` itself | **Ambiguous failure signal.** See below. |
| Bulkhead | Bound concurrent calls so one hot caller cannot starve the rest | A `Semaphore` permit count around concurrent `claude -p` invocations | Exact in shape; the concurrency model underneath is `05-multithreading-concurrency.md`'s territory — one line, not repeated here. |

**Retry is not free and not always safe.** §3.6.10–§3.6.12 already established that a contract failure retried is a contract failure repeated, and that the last parsed envelope must survive the retry or the attempt becomes unbillable work with nothing to show for it. `run_agent` embodies exactly this discipline rather than a blanket "retry on any failure": it keeps `last: Optional[AgentResult]` across iterations — `last = res  # keep the parsed error envelope (cost/tokens preserved)` — so a final failure still returns whatever cost and tokens the last attempt burned, never silently discarding them. More pointedly, it classifies one failure as **not retryable at all**: `if res.subtype == "error_max_turns": return res` immediately, with the comment explaining why — "the claude CLI's turn counter resets per invocation, so retrying here would silently just buy 80 more turns under the same 'attempt', masking the exhaustion from the continuation mechanism." Turn exhaustion is terminal for that call; only a launch failure, a timeout, or an unparseable stdout blob is worth another attempt. This is the retry ring's honest form: bounded, and gated on a classification of *why* the prior attempt failed, exactly as §3.6's contract-failure material already demanded of any retry on a parsed response.

**Idempotency is weaker here than in a REST contract.** A `session_id`, resumed via `--resume`, buys **deduplication of work** — the agent continues the same conversation state rather than starting the whole multi-turn task over from a blank context — but it does not buy deduplication of *effect* the way a payment API's idempotency key does. `12-api-design.md`'s pattern guarantees a specific side effect happens at most once because the database enforces it at the constraint level. `--resume` guarantees no such thing: if the agent's first attempt already ran `git commit` before the process was killed by the timeout, resuming the session does not undo that commit or know it happened — the resumed conversation simply continues, unaware unless the caller's own state tracking (the harness's per-story worktree and its `dev_pipeline:` checkpoint key) records what already landed. Say plainly what the session id is: a resumption key for conversational state, not a mutation guard.

**The circuit breaker's failure signal is ambiguous.** A REST circuit breaker trips on a clean signal — HTTP 5xx, a connection refusal, a timeout — that reliably means the *dependency* is unhealthy. `AgentResult.is_error: bool` conflates two different failures: the agent process could not be reached or parsed at all (a real dependency-health signal — a genuine analog to a 5xx), or the agent ran successfully as a process and produced a well-formed envelope whose `is_error: true` field means the *task* failed — a bad diagnosis, a fix that didn't compile, a persona that gave up. The second case says nothing about whether the next call to `claude -p` will succeed; it says the previous *prompt* did not land. A circuit breaker wired to trip on raw `is_error` rate will open on a run of genuinely hard tasks and refuse easy ones right behind them, which is the wrong trigger. The dependency-health signal worth tripping a breaker on is closer to `subprocess.TimeoutExpired`, `OSError`, and the unparseable-envelope branch — process-level failures — kept separate from a task-level `is_error: true` on a well-formed envelope.

**Bulkhead.** A `Semaphore` initialized with the number of concurrent `claude -p` calls a caller is willing to run at once is the direct Java shape of this ring:

```java
private final Semaphore concurrencyLimit = new Semaphore(4);

public ClaudeEnvelope callWithBulkhead(String task) throws InterruptedException {
    concurrencyLimit.acquire();
    try {
        return runOnce(task); // the ProcessBuilder call from §3.8.7, Route B
    } finally {
        concurrencyLimit.release();
    }
}
```

A fifth concurrent caller blocks on `acquire()` until a permit frees up, rather than the fifth `claude -p` subprocess launching anyway and the five sharing whatever rate limit or cost budget the caller has — the same reason a connection-pool bulkhead exists in front of a database. The concurrency model underneath `Semaphore` — what a permit actually blocks, how this differs from a bounded thread pool, where a virtual thread changes the calculus — is `05-multithreading-concurrency.md`'s territory, not repeated here.

**Retry, shown in Java, preserving the last envelope.** `run_agent`'s Python discipline — keep `last` across attempts, return it unretried on a terminal subtype — has a direct Java shape: a loop that narrows on the exception type, not a blanket `catch (Exception e)`.

```java
public ClaudeEnvelope callWithBoundedRetry(String task, int maxAttempts) {
    ClaudeEnvelope last = null;
    for (int attempt = 0; attempt < Math.max(1, maxAttempts); attempt++) {
        try {
            ClaudeEnvelope envelope = runOnce(task); // §3.8.7's ProcessBuilder call
            if (!envelope.isError()) {
                return envelope;
            }
            last = envelope; // preserve cost/tokens even on a failed attempt
            if (envelope.subtype() == ClaudeEnvelope.Subtype.ERROR_MAX_TURNS) {
                return envelope; // terminal — never retried, per run_agent's own rule
            }
        } catch (AgentTimeoutException e) {
            last = ClaudeEnvelope.timedOut(e.getMessage());
            // retryable: fall through to the next attempt
        }
    }
    return last != null ? last : ClaudeEnvelope.noResult();
}
```

`ClaudeEnvelope.Subtype.ERROR_MAX_TURNS` mirrors `agent.py`'s own `res.subtype == "error_max_turns"` check verbatim in spirit — a sealed enum standing in for the string-valued field the Python envelope carries, so a caller cannot misspell the terminal case the way a raw string comparison could.

**Circuit breaker, shown in Java, tripping on process health rather than task success.** The distinction the case-study section argued in prose — a broken subprocess is a dependency-health signal, a well-formed `is_error: true` envelope is not — has to be encoded as two separate counters, not one:

```java
public final class DependencyHealthBreaker {
    private final AtomicInteger consecutiveProcessFailures = new AtomicInteger(0);
    private static final int TRIP_THRESHOLD = 5;
    private volatile boolean open = false;

    public void recordProcessFailure() { // AgentTimeoutException, launch failure, unparseable envelope
        if (consecutiveProcessFailures.incrementAndGet() >= TRIP_THRESHOLD) {
            open = true;
        }
    }

    public void recordProcessSuccess() { // the subprocess ran and produced a well-formed envelope
        consecutiveProcessFailures.set(0);
        open = false;
    }

    public boolean isOpen() { return open; }
    // A well-formed envelope with isError() == true never calls either method here —
    // task failure is not dependency failure, per §3.8.8's ambiguous-signal argument.
}
```

**PART 4 §4.5 assembles all five rings around one `ClaudeRunner` class**, with the bulkhead and the bounded, classified retry shown together against real code; see `build-it/06-orchestrator-c-bulkhead-and-retry.md`.

> An agent call is a remote dependency with unbounded latency, partial failure, non-determinism and a real cost per call, and it earns the same five reflexes as any other dependency — timeout, retry, idempotency, circuit breaker, bulkhead — except the retry must be classified rather than blanket, the idempotency key deduplicates work rather than effect, and the circuit breaker's trip signal must separate a broken process from a merely-failed task.

## Pitfalls

- **Belief:** "an SDK session counts as trusted, so it's fine to skip re-checking workspace trust when embedding the Agent SDK in a service." **Outcome:** a fresh SDK session against a never-trusted repository withholds `permissions.allow` and `additionalDirectories` exactly like `-p`, with the identical stderr warning — the trust shorthand covers one narrow `settings.local.json` check, never the general permission surface. **Fix:** gate trust at the path (`hasTrustDialogAccepted`) regardless of whether the caller is `-p` or the SDK; do not treat "SDK" as a synonym for "already trusted." **Why people believe it:** the phrase "counts as accepted" is real documentation language, attached to a narrower claim than the one it gets generalized into.
- **Belief:** "retrying a failed `claude -p` call is always the safe move, the same way retrying a failed GET is." **Outcome:** retrying an `error_max_turns` result silently buys another 80–160 turns under the same nominal "attempt," masking real turn exhaustion from any continuation logic watching for it — `run_agent` deliberately returns immediately instead. **Fix:** classify the failure before retrying: a launch/timeout/parse failure is retryable, a turn-exhaustion subtype is terminal for that call and belongs to a continuation mechanism, not a blind retry loop. **Why people believe it:** "retry on any exception" is the default shape of a naive retry wrapper, and it happens to be safe for the two most common failure modes (timeout, launch failure) here, which hides the one case where it is not.
- **Belief:** "a `session_id` used with `--resume` makes the call idempotent, the same way an idempotency key makes a `POST` safe to retry." **Outcome:** a resumed session continues the same conversation but does not undo or know about a side effect (a commit, a file write) the killed prior attempt already made — nothing enforces at-most-once *effect* the way `12-api-design.md`'s database-constraint pattern does for a REST call. **Fix:** treat `session_id` as work-deduplication only; track already-landed side effects separately (the harness's per-story checkpoint state is exactly this tracking). **Why people believe it:** both mechanisms are called "the key that makes a retry safe" in casual conversation, but only one of them is backed by a uniqueness constraint at the point the effect happens.

## Cheat sheet

| Concept | One line |
|---|---|
| `resolveSettings()` | SDK-side composition of §1.2's precedence chain before the first request |
| `managedSettings` | Composed regardless of `settingSources` — the floor no session can opt out of |
| `parentSettingsBehavior` | `"isolated"` (clean slate) vs inheriting the spawning process's resolved settings — a level-2-only knob |
| Trust shorthand | "SDK counts as trusted" = one `settings.local.json` check only; untrusted-folder `allow` rules still withheld |
| Why subprocess over SDK | Same registered persona file (`--agent`), same deny-list (`--setting-sources`), no SDK↔binary version coupling |
| Java Route A | `HttpClient` → level 3 semantics, your own loop, typed nothing |
| Java Route B | `ProcessBuilder` around `claude -p` → level 1 semantics, the harness's own choice |
| `Process.waitFor(Duration)` | Returns `false` on timeout — does not throw, does not kill; you must `destroyForcibly()` yourself |
| Timeout ring | `DEFAULT_TIMEOUT = 1800`s, `subprocess.run(..., timeout=...)` |
| Retry ring | Bounded (`retries=3` default), classified — `error_max_turns` is terminal, not retried |
| Idempotency ring | `session_id` + `--resume` — dedupes work, not effect |
| Circuit breaker ring | Trip on process-level failure, not on task-level `is_error: true` |
| Bulkhead ring | `Semaphore` permit count around concurrent `claude -p` calls |

## Self-test

1. What does `parentSettingsBehavior: "isolated"` actually change, and what would happen without it in a long-running service spawning many SDK sessions?
<details><summary>Answer</summary>It makes each new SDK session's settings resolution start clean, ignoring whatever the spawning Node/Python process already had resolved. Without it, the first session's resolved settings quietly become the floor every later session in that same process inherits — an unintended coupling between unrelated sessions.</details>

2. Does `managedSettings` participate in resolution if a caller omits it from `settingSources`?
<details><summary>Answer</summary>Yes — it is composed regardless. It is the top-ranked layer precisely because it enforces an organizational floor no individual session, caller, or `settingSources` list can opt out of.</details>

3. Name the two specific ADR-0016 reasons (not the process-isolation-as-test-seam reason from the previous file) the harness chose `claude -p` subprocesses over the Agent SDK.
<details><summary>Answer</summary>`--agent <persona>` loads the exact same registered `.claude/agents/*.md` file an interactive engineer's session would load — "the parity mechanism," one definition, one binary, no drift between an SDK-side re-registration and the file engineers edit. And the subprocess carries no SDK-package-to-CLI-binary version coupling — the harness depends only on the CLI's documented flags and JSON output shape, not an in-process library's type signatures.</details>

4. What does `Process.waitFor(Duration)` return on timeout, and what is the consequence of checking only that return value?
<details><summary>Answer</summary>It returns `false`; it does not throw and does not kill the process. A caller that checks the boolean without following up with `process.destroyForcibly()` leaves an orphaned `claude` subprocess running past its own timeout, still consuming tokens.</details>

5. Why does `run_agent` return immediately on `subtype == "error_max_turns"` instead of retrying it like any other failure?
<details><summary>Answer</summary>Because the CLI's turn counter resets per invocation — retrying would silently grant another full turn budget under the same nominal "attempt," hiding genuine turn exhaustion from any continuation mechanism that needs to see it as terminal for that call.</details>

6. What does a `claude -p --resume <session_id>` retry actually guarantee, and what does it not guarantee?
<details><summary>Answer</summary>It guarantees the resumed call continues the same conversational state rather than restarting the task from a blank context — deduplication of work. It does not guarantee at-most-once side effects: if the prior attempt already committed a file before being killed, resuming the session neither undoes nor is aware of that, unlike a database-constraint-backed REST idempotency key.</details>

7. Why is `AgentResult.is_error: true` a poor circuit-breaker trip signal on its own?
<details><summary>Answer</summary>It conflates a process-level failure (the subprocess couldn't be reached, timed out, or produced unparseable output — a genuine dependency-health signal) with a task-level failure (a well-formed envelope reporting the agent's own task didn't succeed). A breaker tripped on raw `is_error` rate opens because of a run of hard tasks, not because the dependency itself is unhealthy.</details>

8. What is the Java shape of the bulkhead ring, and what does exceeding its capacity do to a fifth concurrent caller?
<details><summary>Answer</summary>A `Semaphore` initialized to the maximum concurrent `claude -p` calls allowed. A fifth caller beyond that capacity blocks on `acquire()` until a permit is released, rather than launching a fifth subprocess that shares the same rate limit or cost budget as the other four.</details>

**Interview:** "Where does an idempotency key from a REST API map onto an agent call, and is the mapping exact?" — the honest answer, in one breath: a resumed `session_id` deduplicates the *work* of a multi-turn conversation, never the *effect* of a tool call the agent already ran, because nothing enforces at-most-once execution the way a database uniqueness constraint does for a REST idempotency key — say that distinction out loud, don't just say "yes, session id."

**Insight:** the five rings compose in a fixed order for a reason — bulkhead outermost (decide whether to even attempt the call), then circuit breaker (decide whether the dependency looks healthy enough to try), then idempotency (decide whether this is a fresh attempt or a resumption), then retry (decide whether to try again on failure), then timeout innermost (bound each individual attempt). D-85 draws them nested in exactly this order for that reason — an inner ring's failure is what an outer ring counts toward its own decision, not the other way round.

## Open questions

**Unverified:** the exact spelling and call signature of `resolveSettings()`, and whether `managedSettings` and `parentSettingsBehavior` are the literal field names in the current `@anthropic-ai/claude-agent-sdk` / `claude-agent-sdk` type definitions, as opposed to the syllabus's own paraphrase of the mechanism. Neither name appears on `code.claude.com/docs/en/sub-agents` or `code.claude.com/docs/en/settings`, the two permitted pages most likely to carry them; the authoritative source is `code.claude.com/docs/en/agent-sdk/`, outside this guide's nine-page `[DOC]` scope, and no local SDK install was available to inspect directly. Settle by installing `@anthropic-ai/claude-agent-sdk` (or `claude-agent-sdk` for Python) and reading its exported types, the same technique the previous file used for the raw Messages API's installed Python client.

---

**Leaves covered:** 3.8.5–3.8.8 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** D-85
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 275
