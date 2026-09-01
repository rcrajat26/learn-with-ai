# 21 AI for Coding — `ClaudeRunner`: the process boundary — BUILD IT (§4.5.1–4.5.2)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 4 of 6** | [Index](../00-index.md)
Previous: [proving the boundary, and the diff against the real one](04-two-subagents-b.md) · Next: [absolute settings, and resolution order](05-orchestrator-b-ceilings-and-resolution.md)

§4.5 builds **one** Java class, `ClaudeRunner`, cumulatively across eight leaves spread over four
files. This file lays the foundation: a `ProcessBuilder` wrapper around `claude -p
--output-format json` that turns an untyped OS subprocess into a typed `ClaudeEnvelope`, plus the
three exception types that let a caller tell agency, money, and time apart when one runs out. The
next three files (§4.5.3–4.5.8) extend this exact class — an absolute `--settings` path, a
parameter → env → default resolution chain, a bounded retry, a `Semaphore` bulkhead, and a
two-stage pipeline with a per-stage cost report. Nothing here is rewritten later, only added to.
Every command below ran for real against the installed binary, `claude 2.1.251`, from `/tmp` —
nothing in this file is invented output.

## `ClaudeRunner` — the process boundary [BUILD] [JAVA] (§4.5.1)

### Mental model

Think of `ClaudeRunner` as a `@RestController` method that talks to the far side over
`stdin`/`stdout` instead of a socket. **Insight:** the caller never gets typed access to the agent
— everything Claude Code does with a prompt happens inside a process Java can only see as three
untyped channels: a byte stream out (stdout), a byte stream for diagnostics (stderr), and one
integer (the exit code) once the process dies. `ClaudeRunner`'s entire job is converting that
untyped triple into a typed `ClaudeEnvelope`, or throwing a specific exception when it cannot.

### Why it exists

A Java service that wants an LLM to do bounded, reviewable work — "read this diff, write the
review comment" — has three options: call the Anthropic API directly and reimplement tool use,
context management and permission checking from scratch; embed the Claude Agent SDK as a library
dependency; or shell out to the `claude` binary and read back its `--output-format json` envelope,
the way a CI pipeline does. The sdlc-harness took the third path deliberately —
`harness/src/harness/engine/agent.py`'s module docstring calls this "stateless agent invocation": a
fresh `claude -p` per call, full brief in, one JSON envelope out, no `--resume` unless a caller
explicitly asks for one. `ClaudeRunner` is that same shape in Java: no in-process session state, no
shared mutable client, just a command line out and an envelope back.

### When to reach for it, and when not

Wrong tool when the caller is itself already a `claude` conversation — launching `claude -p` from
inside a running Claude Code session is a *nested* invocation, and three earlier files in this
PART 4 build (the hooks and skill files) found the auto-mode classifier sometimes refuses that
shape outright. Also wrong for a tight request/response loop where sub-second latency matters — a
fresh `claude -p` process pays full startup cost every call, which is why `--resume <session_id>`
exists at all (out of scope here). Right tool for exactly the shape the sdlc-harness uses it for: a
CI-adjacent Java service dispatching bounded, reviewable units of agent work that needs a real exit
path — a typed result or a typed exception — for each one.

**Pitfall:** treating a `0` exit code as success. `ClaudeEnvelope.isError()` comes from parsing
`is_error` out of the JSON body, never from the process exit code — a `claude -p` invocation that
hits an API error, a max-turns wall, or a budget wall still very often exits `0`, because from the
operating system's point of view the process ran to completion and printed a well-formed envelope.
The exit code answers "did the process itself survive"; `is_error` answers "did the agent's run
succeed." They are independent booleans and both are on the record below.

### How it works

`ProcessBuilder` starts the child process; `Process.waitFor(Duration)` — a Java 19+ overload used
here as the wall-clock ceiling in §4.5.2 — blocks until the child exits or the duration elapses. In
between, something easy to get wrong: **both** `stdout` and `stderr` must be drained *while the
process runs*, on their own threads, not read sequentially after it exits. `claude -p` can write
megabytes of transcript to stdout; the OS pipe buffer backing that stream is typically 64 KiB on
Linux and macOS. If nothing is reading it, the child blocks on its own `write()` once the buffer
fills, and the parent — sitting in `waitFor` — waits for a process that is itself waiting for a
reader that will never come. Two Java 21 virtual threads, `Thread.ofVirtual().start(...)`, one per
stream, solve this for the cost of two cheap threads per invocation — no platform thread pool
needed, which matters once §4.5.5 adds a `Semaphore` bounding many of these running concurrently.

![D-96 — `ClaudeRunner` and the process boundary. The `Semaphore` and the bounded retry arrive in §4.5.5.](../diagrams/D-96-claude-runner-process-boundary.svg)

**D-96** — `ClaudeRunner` and the process boundary. This file builds everything left of the hard
vertical line except the `Semaphore` bulkhead and the bounded retry box — those are §4.5.5. On the
process side, this file's command line carries only `--output-format json`, `--max-turns` and
`--max-budget-usd`; `--settings <absolute path>`, `--agent` and `--permission-mode` arrive in later
files. The diagram's three ceiling-exception labels — `AgentTimeoutException`,
`AgentTurnLimitException`, `AgentBudgetExceededException` — match the sealed naming table below and
the compiled Java exactly. (The diagram originally used a `Claude…`-prefixed naming for those three
exceptions; it has since been corrected to the `Agent…` names the code actually uses.) Everything
else the diagram draws — the record's five fields, the 500-character snippet, the exit-code/`is_error`
independence — matches the code below exactly.

### Code — the artefact for §4.5.1

```java
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.List;
import java.util.Map;

public final class ClaudeRunner {

    private static final int SNIPPET_LIMIT = 500;
    private static final ObjectMapper MAPPER = new ObjectMapper();

    public record ClaudeEnvelope(
            int exitCode,
            String stdoutJson,
            boolean isError,
            double totalCostUsd,
            Map<String, Integer> usage) {}

    private final Duration timeout;

    public ClaudeRunner(Duration timeout) {
        this.timeout = timeout;
    }

    public ClaudeEnvelope run(String prompt) throws IOException, InterruptedException {
        List<String> command = List.of(
                "claude", "-p", prompt,
                "--output-format", "json");

        Process process = new ProcessBuilder(command).start();

        StreamCapture stdoutCapture = new StreamCapture(process.getInputStream());
        StreamCapture stderrCapture = new StreamCapture(process.getErrorStream());
        Thread stdoutReader = Thread.ofVirtual().start(stdoutCapture);
        Thread stderrReader = Thread.ofVirtual().start(stderrCapture);

        boolean finished = process.waitFor(timeout);
        if (!finished) {
            process.destroyForcibly();
            joinQuietly(stdoutReader);
            joinQuietly(stderrReader);
            throw new IllegalStateException(
                    "claude -p did not exit within " + timeout.toMillis() + "ms wall clock");
        }
        joinQuietly(stdoutReader);
        joinQuietly(stderrReader);
        int exitCode = process.exitValue();

        String stdout = stdoutCapture.text();
        String stderr = stderrCapture.text();
        JsonNode root = parseOrCaptureSnippet(stdout, stderr);
        return toEnvelope(exitCode, stdout, root);
    }

    private JsonNode parseOrCaptureSnippet(String stdout, String stderr) {
        String trimmed = stdout == null ? "" : stdout.strip();
        if (!trimmed.isEmpty()) {
            try {
                return MAPPER.readTree(trimmed);
            } catch (IOException parseFailure) {
                // fall through: capture what actually printed, bounded, below
            }
        }
        String source = !trimmed.isEmpty() ? trimmed : (stderr == null ? "" : stderr.strip());
        String snippet = source.substring(0, Math.min(SNIPPET_LIMIT, source.length()));
        System.err.println("[ClaudeRunner] unparseable envelope, first " + SNIPPET_LIMIT
                + " chars: " + snippet);
        return null;
    }

    private ClaudeEnvelope toEnvelope(int exitCode, String stdout, JsonNode root) {
        if (root == null) {
            return new ClaudeEnvelope(exitCode, stdout, true, 0.0, Map.of());
        }
        boolean isError = root.path("is_error").asBoolean(false);
        double totalCostUsd = root.path("total_cost_usd").asDouble(0.0);
        JsonNode usageNode = root.path("usage");
        Map<String, Integer> usage = usageNode.isMissingNode()
                ? Map.of()
                : Map.of(
                        "input_tokens", usageNode.path("input_tokens").asInt(0),
                        "output_tokens", usageNode.path("output_tokens").asInt(0),
                        "cache_read_input_tokens", usageNode.path("cache_read_input_tokens").asInt(0),
                        "cache_creation_input_tokens", usageNode.path("cache_creation_input_tokens").asInt(0));
        return new ClaudeEnvelope(exitCode, stdout, isError, totalCostUsd, usage);
    }

    private static void joinQuietly(Thread thread) {
        try {
            thread.join(Duration.ofSeconds(2).toMillis());
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    private static final class StreamCapture implements Runnable {
        private final InputStream source;
        private volatile String text = "";

        StreamCapture(InputStream source) {
            this.source = source;
        }

        @Override
        public void run() {
            try {
                text = new String(source.readAllBytes(), StandardCharsets.UTF_8);
            } catch (IOException e) {
                text = "";
            }
        }

        String text() {
            return text;
        }
    }
}
```

The 500-character bound on the parse-failure snippet is not arbitrary. It is the same number
`headless/03-internals-c-the-failure-taxonomy.md` established for the real harness: `agent.py`
line 293 reads `snippet = (proc.stdout or proc.stderr or "").strip()[:500]`, with the comment
directly above it explaining why — "a zero-cost envelope failure was only diagnosable by
reproducing it interactively" before that line existed. `ClaudeRunner.SNIPPET_LIMIT` reuses the
exact figure so a caller reading both codebases sees one convention, not two arbitrary ones.

### Prove it — §4.5.1

Compiled and run from `/tmp/claude-runner-test`, against Jackson 2.18.3/2.18.2 on the local
classpath and Java 25 (source-compatible with the Java 21 target used throughout):

```
$ javac -d out -cp "$CP" ClaudeRunner.java
$ java -cp "out:$CP" ClaudeRunner
happy path: exitCode=0 isError=false totalCostUsd=0.012086999999999999 usage={input_tokens=2, output_tokens=5, cache_creation_input_tokens=0, cache_read_input_tokens=21994}
```

**Unverified — recorded, not glossed over:** this leaf's packet named an expected blocker — a
nested `claude` invocation refused by the auto-mode classifier, as three earlier PART 4 files hit.
Every `claude -p` call in this file, launched from a `ProcessBuilder` child of this agent session,
returned a normal envelope with **no refusal**. Not root-caused here; carried to
`## Open questions` rather than asserted as fixed.

The unparseable-input path, proven against a genuine truncated envelope rather than invented text —
the first 640 characters of the real happy-path `stdout` above, simulating a process killed
mid-stream:

```
[ClaudeRunner] unparseable envelope, first 500 chars: {"duration_api_ms":3888,"stop_reason":"end_turn","session_id":"d4b035bc-7089-4b2d-984f-e97d1f35c1b4","total_cost_usd":0.012086999999999999,"usage":{"input_tokens":2,"cache_creation_input_tokens":0,"cache_read_input_tokens":21994,"output_tokens":5,"output_tokens_details":{"thinking_tokens":0},"server_tool_use":{"web_search_requests":0,"web_fetch_requests":0},"service_tier":"standard","cache_creation":{"ephemeral_1h_input_tokens":0,"ephemeral_5m_input_tokens":0},"inference_geo":"global","iteration
truncated-input parse result: null
```

`parseOrCaptureSnippet` correctly falls through to the snippet branch — a truncated JSON object
still fails `MAPPER.readTree`, exactly as a process killed by the wall clock in §4.5.2 would leave
a half-written envelope behind.

### What this costs

The happy-path call above billed **$0.0121** — cheap because the run reused a warm prompt cache
(`cache_read_input_tokens: 21994` against only `input_tokens: 2`). A cold-cache call to the same
model line, observed earlier in the same session, billed **$0.1383** for an identical one-word
reply — an eleven-fold difference driven entirely by cache state, not by anything `ClaudeRunner`
does. The snippet-capture demonstration cost nothing extra: it re-parses text already paid for, in
process, with no second subprocess.

**Insight:** the dollar cost lives entirely on the far side of the process boundary. Nothing in
`ClaudeRunner` itself has its own cost; the only line that costs money is the one that starts the
child process, and the amount is not knowable until `total_cost_usd` comes back in the envelope.
That asymmetry is exactly why §4.5.2's budget ceiling is enforced *after* a call completes, not
before it starts.

No gotcha beyond the pipe-buffer deadlock and the exit-code pitfall already stated above in full.

> **`ClaudeRunner`** is a `ProcessBuilder` wrapper that turns one `claude -p --output-format json`
> subprocess into one typed `ClaudeEnvelope`, treating the process's exit code and its parsed
> `is_error` field as two independent signals rather than one.

## The three ceilings [BUILD] [JAVA] (§4.5.2)

### Mental model

Three independent circuit breakers guarding three independent resources: **turns** (how many
back-and-forths the agent gets with itself and its tools), **dollars** (what the API calls inside
those turns cost), and **wall-clock time** (how long the calling thread is willing to sit in
`waitFor`). A caller can hit any one of the three without hitting either of the others — a fast,
cheap agent can still blow through a turn count doing excessive tool exploration; a slow but
turn-frugal agent can still blow a wall-clock budget; a single expensive model call can exceed a
dollar ceiling in one turn flat. Three resources, three independent failure modes, three distinct
exception types — a caller catching `AgentBudgetExceededException` and retrying with a bigger
budget must never accidentally also catch and mask an `AgentTimeoutException`, because the right
response to each is different.

### Why it exists

`cost-model/03-internals-b-ceilings-and-reading-it-back.md` tabled this as **D-78** and the real
`harness/src/harness/engine/agent.py` carries the incident that motivated it, verbatim in its own
source comment above `DEFAULT_MAX_TURNS`:

```python
DEFAULT_TIMEOUT = 1800
# Raised again, 80 -> 160, 2026-08-10 (agent-progress-all-stages--S1
# dogfood): the coder produced substantial, correct, spec-matching work (13
# green tests + the target module's fix) but exhausted the full 80-turn leg
# before ever reaching a commit, costing $5.16 for zero landed work — a
# fresh story's first leg is disproportionately reads/exploration, not a
# runaway.
DEFAULT_MAX_TURNS = 160
```

**[INCIDENT]** What broke: an 80-turn cap killed a coding leg that had already produced thirteen
green tests and a correct fix, mid-way through, before it reached a commit. What it cost: **$5.16**
billed for zero landed work — real spend with nothing to show for it, because the ceiling fired
before the one action (the commit) that would have made the work durable. The fix: raise the
default to 160 turns. The general law: **a ceiling that fires before the unit of work is durable
converts a near-success into a total loss.** `DEFAULT_TIMEOUT = 1800` (thirty minutes) remains the
binding wall-clock backstop regardless of the turn count — raising `HARNESS_AGENT_MAX_TURNS` alone
moves only one of the two ceilings.

### How it works

Each ceiling maps to one flag and one distinct exception:

| Ceiling | Flag | Exception thrown | Real envelope signal (v2.1.251, observed) |
|---|---|---|---|
| Turns | `--max-turns <n>` | `AgentTurnLimitException` | `is_error: true`, `subtype: "error_max_turns"`, `terminal_reason: "max_turns"` |
| Dollars | `--max-budget-usd <amount>` (**v2.1.217+** for cap-enforcement; confirmed live on 2.1.251) | `AgentBudgetExceededException` | `is_error: true`, `subtype: "error_max_budget_usd"`, `terminal_reason: "budget_exhausted"` |
| Wall clock | `Process.waitFor(Duration)` — no `claude` flag; enforced entirely on the Java side | `AgentTimeoutException` | none — the process is killed by `destroyForcibly()` before it can print an envelope at all |

The turn and budget ceilings are the CLI's own doing: `claude` decides it has run out of turns or
dollars, finishes cleanly, and prints an envelope whose `subtype` says which one fired. `run_agent`'s
own retry loop in `harness/src/harness/engine/agent.py` (lines 296–309) treats `subtype ==
"error_max_turns"` as **terminal**, never retried inside the loop — "the claude CLI's turn counter
resets per invocation, so retrying here would silently just buy 80 more turns under the same
'attempt.'" `ClaudeRunner` reads the same `subtype` field to pick which exception to throw. The
wall-clock ceiling is different in kind: enforced entirely by the JVM, and by the time it fires
there is usually no envelope to read at all — the process is killed mid-write, the same
"half-written JSON" shape the 500-character snippet path in §4.5.1 exists to make diagnosable.

**Pitfall:** assuming `--max-budget-usd` stops spend *before* it happens. It does not, and the
prove step below shows the real number. The cap is checked between model calls, not inside one —
a single expensive call already in flight is not interrupted mid-call, so the actual spend recorded
against a tight cap can land well above it. **Why people believe it:** "budget" reads like a
pre-authorization limit on a payment card, where the issuer declines the charge before it clears;
here it is closer to a post-hoc expense report — the ceiling decides whether the *next* call is
allowed to start, after the *current* one has already been paid for.

### Code — the artefact for §4.5.2

`parseOrCaptureSnippet`, `toEnvelope`, `joinQuietly` and `StreamCapture` are **unchanged** from the
§4.5.1 listing above — not reprinted here, since reprinting an unchanged method body verbatim adds
nothing a diff wouldn't already show. What §4.5.2 adds, in full: the sealed exception hierarchy,
the two extra constructor parameters, the two extra command-line flags, and the `subtype` check
after the envelope comes back. Dropped into the §4.5.1 class in place of its old constructor and
`run()` method, this is the complete, compiling class for §4.5.2:

```java
    public sealed interface AgentCeilingException
            permits AgentTimeoutException, AgentTurnLimitException, AgentBudgetExceededException {}

    public static final class AgentTimeoutException extends RuntimeException
            implements AgentCeilingException {
        public AgentTimeoutException(String message) {
            super(message);
        }
    }

    public static final class AgentTurnLimitException extends RuntimeException
            implements AgentCeilingException {
        private final int maxTurns;

        public AgentTurnLimitException(String message, int maxTurns) {
            super(message);
            this.maxTurns = maxTurns;
        }

        public int maxTurns() {
            return maxTurns;
        }
    }

    public static final class AgentBudgetExceededException extends RuntimeException
            implements AgentCeilingException {
        private final double maxBudgetUsd;

        public AgentBudgetExceededException(String message, double maxBudgetUsd) {
            super(message);
            this.maxBudgetUsd = maxBudgetUsd;
        }

        public double maxBudgetUsd() {
            return maxBudgetUsd;
        }
    }

    private final int maxTurns;
    private final double maxBudgetUsd;
    private final Duration timeout;

    public ClaudeRunner(int maxTurns, double maxBudgetUsd, Duration timeout) {
        this.maxTurns = maxTurns;
        this.maxBudgetUsd = maxBudgetUsd;
        this.timeout = timeout;
    }

    public ClaudeEnvelope run(String prompt) throws IOException, InterruptedException {
        List<String> command = List.of(
                "claude", "-p", prompt,
                "--output-format", "json",
                "--max-turns", String.valueOf(maxTurns),
                "--max-budget-usd", String.valueOf(maxBudgetUsd));

        Process process = new ProcessBuilder(command).start();

        StreamCapture stdoutCapture = new StreamCapture(process.getInputStream());
        StreamCapture stderrCapture = new StreamCapture(process.getErrorStream());
        Thread stdoutReader = Thread.ofVirtual().start(stdoutCapture);
        Thread stderrReader = Thread.ofVirtual().start(stderrCapture);

        boolean finished = process.waitFor(timeout);
        if (!finished) {
            process.destroyForcibly();
            joinQuietly(stdoutReader);
            joinQuietly(stderrReader);
            throw new AgentTimeoutException(
                    "claude -p did not exit within " + timeout.toMillis()
                            + "ms wall clock: " + String.join(" ", command));
        }
        joinQuietly(stdoutReader);
        joinQuietly(stderrReader);
        int exitCode = process.exitValue();

        String stdout = stdoutCapture.text();
        String stderr = stderrCapture.text();
        JsonNode root = parseOrCaptureSnippet(stdout, stderr);
        ClaudeEnvelope envelope = toEnvelope(exitCode, stdout, root);

        if (envelope.isError()) {
            String subtype = (root != null && root.has("subtype")) ? root.get("subtype").asText() : "";
            if ("error_max_turns".equals(subtype)) {
                throw new AgentTurnLimitException(
                        "claude -p hit --max-turns " + maxTurns + " before finishing", maxTurns);
            }
            if ("error_max_budget_usd".equals(subtype)) {
                throw new AgentBudgetExceededException(
                        "claude -p hit --max-budget-usd " + maxBudgetUsd + " before finishing",
                        maxBudgetUsd);
            }
        }
        return envelope;
    }
```

No fixed retry, no `--settings`, no `Semaphore` here — §4.5.3–4.5.4 build the parameter → env →
default resolution chain (reading an env var such as `HARNESS_AGENT_MAX_TURNS`, with the
`is not None`-equivalent Java check that keeps an explicit `0` alive rather than treating it as
"unset"), and §4.5.5 adds the bulkhead and the retry.

### Prove it — §4.5.2

All four scenarios below ran against the same class, real `claude` binary, in the same process:

```
$ java -cp "out:$CP" ClaudeRunner
happy path: exitCode=0 isError=false totalCostUsd=0.012086999999999999 usage={input_tokens=2, output_tokens=5, cache_creation_input_tokens=0, cache_read_input_tokens=21994}
caught AgentTurnLimitException: claude -p hit --max-turns 1 before finishing maxTurns=1
caught AgentBudgetExceededException: claude -p hit --max-budget-usd 1.0E-4 before finishing maxBudgetUsd=1.0E-4
caught AgentTimeoutException: claude -p did not exit within 200ms wall clock: claude -p Write a 500-word essay on distributed consensus. --output-format json --max-turns 20 --max-budget-usd 1.0
```

The turn-limit case used the prompt "List the files in the current directory, then read one of
them, then summarize it in detail" against `--max-turns 1` — enough tool use to guarantee more than
one turn is needed. The budget case used `--max-budget-usd 0.0001` — small enough that essentially
any real call exceeds it. Both confirmed independently at the CLI:

```
$ claude -p "List the files..." --output-format json --max-turns 1
{"...":"...","terminal_reason":"max_turns","is_error":true,"num_turns":2,"subtype":"error_max_turns","errors":["Reached maximum number of turns (1)"],...}

$ claude -p "Say PONG" --output-format json --max-budget-usd 0.0001
{"...":"total_cost_usd":0.06197725,"terminal_reason":"budget_exhausted","is_error":true,"num_turns":1,"subtype":"error_max_budget_usd","errors":["Reached maximum budget ($0.0001)"],...}
```

The second line is the pitfall stated above, made concrete with real numbers: the requested
ceiling was **$0.0001**; the amount actually billed before the ceiling fired was **$0.06197725** —
**619 times** the requested cap, because the ceiling could only refuse the *next* call, not
interrupt the one already in progress.

### What this costs

Summed across every real `claude -p` invocation this leaf made (happy path, turn-limited attempt,
budget-limited attempt, plus the two CLI-only confirmation runs; the timeout case billed nothing —
it was killed before any envelope could report a cost): **on the order of $0.20** for the whole
§4.5.2 proof pass. The single largest line item was the budget-ceiling demonstration itself, at
$0.062 — proving a $0.0001 cap does not cap a single call costs meaningfully more than the cap it
demonstrates, worth knowing before running this against a production budget rather than a
throwaway one.

**Interview:** "why three exception types instead of one `RunnerException` with a reason code?" —
the caller's remediation differs by ceiling: turn-limit means "give this task a `--max-turns`
override and resubmit," budget means "the task or the budget granularity is wrong," timeout means
"the process may still be running work that will never be collected — nothing to resume." Three
sealed-permitted types let the compiler flag a caller that only handles one case as incomplete; a
reason-code string pushes that distinction into every caller's own `if`-chain instead.

No gotcha beyond the two already stated in full above (exit-code independence, budget-ceiling
reactivity).

> **The three ceilings** — `--max-turns`, `--max-budget-usd`, and a JVM-side
> `Process.waitFor(Duration)` — bound agency, money, and time independently, each surfacing as its
> own exception type so a caller can decide whether to retry without first parsing a reason string.

## Pitfalls

- **Belief:** a `0` exit code from `claude -p` means the agent's task succeeded. **Symptom:** a
  caller checking only `process.exitValue()` silently accepts a turn-exhausted or
  budget-exhausted run as success, since both still exit `0` in the cases observed above. **Fix:**
  always parse `is_error` and `subtype` from the JSON body; never branch on exit code alone. **Why
  people believe it:** `git`, `mvn`, `make` all treat exit code as the single source of truth for
  success/failure, and `claude -p` mostly does too — except in exactly these ceiling cases.
- **Belief:** `--max-budget-usd` pre-authorizes spend like a payment-card hold, so the bill lands
  at or below the cap. **Symptom:** the real test above billed **$0.062** against a **$0.0001**
  cap — 619 times over. **Fix:** treat it as a between-calls circuit breaker, not a per-call spend
  limiter; the first call's actual cost is unbounded by the cap. **Why people believe it:** the
  word "budget" suggests pre-authorization; the enforcement point (between calls, not inside one)
  is not obvious from the flag name.
- **Belief:** reading `process.getInputStream()` fully, then `getErrorStream()`, after `waitFor()`
  returns is a safe simplification. **Symptom:** any `claude -p` call whose combined output
  exceeds ~64 KiB deadlocks — child blocked writing, parent blocked in `waitFor`, forever, never
  timing out. **Fix:** drain both streams concurrently on their own threads for the process's
  whole lifetime — the virtual-thread `StreamCapture` pattern above. **Why people believe it:**
  small test prompts rarely fill a pipe buffer, so the bug is invisible until production.

## Cheat sheet

| Concern | Mechanism | Detail |
|---|---|---|
| Turn ceiling | `--max-turns <n>` | throws `AgentTurnLimitException`; envelope `subtype: "error_max_turns"` |
| Budget ceiling | `--max-budget-usd <amount>` | throws `AgentBudgetExceededException`; envelope `subtype: "error_max_budget_usd"`; **v2.1.217+**; enforced between calls, not inside one |
| Wall-clock ceiling | `Process.waitFor(Duration)` | throws `AgentTimeoutException`; no envelope at all — process killed by `destroyForcibly()` |
| Success signal | parse `is_error` from the JSON body | never trust the OS exit code alone |
| Parse-failure evidence | `stdout.strip()[:500]` | same 500-character bound as `harness/src/harness/engine/agent.py` line 293 |
| Stream draining | one virtual thread per stream, started before `waitFor` | avoids the 64 KiB pipe-buffer deadlock |
| Envelope fields (this file's record) | `exitCode`, `stdoutJson`, `isError`, `totalCostUsd`, `usage` | matches D-96 exactly |

## Self-test

<details><summary>1. Why does `ClaudeEnvelope.isError()` come from the parsed JSON rather than the process exit code?</summary>
`claude -p` can exit `0` while the agent's run failed — a max-turns or max-budget ceiling fires
cleanly and the process terminates normally from the OS's point of view. Trusting the exit code
alone would treat every ceiling hit as a success.
</details>

<details><summary>2. What goes wrong if stdout/stderr are read sequentially after `waitFor()` instead of concurrently while the process runs?</summary>
If combined output exceeds the OS pipe buffer (~64 KiB), the child blocks on its own `write()` once
the buffer fills because nothing is reading it, and the parent sitting in `waitFor()` is waiting for
a process that is itself permanently stuck. Both sides wait forever.
</details>

<details><summary>3. Why does the parse-failure snippet stop at exactly 500 characters?</summary>
It is lifted directly from the real sdlc-harness, `harness/src/harness/engine/agent.py` line 293:
`snippet = (proc.stdout or proc.stderr or "").strip()[:500]`. Reusing the figure means one
convention across both codebases, not two unrelated ones.
</details>

<details><summary>4. A caller sets `--max-budget-usd 0.10` and the run still bills $0.35. Is `ClaudeRunner` broken?</summary>
No — this is the observed, real behavior: the ceiling is enforced between calls, not inside one. A
model call already in progress when the check runs completes and bills in full; the ceiling only
blocks the *next* call. This file measured a 619-fold overshoot on a $0.0001 cap for the same
reason.
</details>

<details><summary>5. Why three exception types instead of one `RunnerException` with a reason enum?</summary>
Remediation differs by ceiling, and a caller should not have to parse a code to know which resource
ran out. `sealed interface AgentCeilingException permits AgentTimeoutException,
AgentTurnLimitException, AgentBudgetExceededException` lets a `switch` be
exhaustiveness-checked by the compiler — a reason-code enum cannot offer that.
</details>

<details><summary>6. What would `AgentTimeoutException` have to read from the envelope before throwing?</summary>
Nothing — there may be no valid envelope at all. `destroyForcibly()` kills the process before it
necessarily finishes writing complete JSON, the same "half-written JSON" shape the parse-failure
snippet exists to make diagnosable. The timeout branch throws immediately on `!finished`, without
attempting to parse anything.
</details>

<details><summary>7. Why `Process.waitFor(Duration)` rather than `waitFor(long, TimeUnit)`?</summary>
The `Duration` overload (Java 19+) avoids a real bug found while testing this file: converting a
sub-second timeout to whole seconds via `Duration.toSeconds()` truncates — 200 milliseconds becomes
"0 seconds." Passing the `Duration` straight through preserves millisecond resolution.
</details>

## Open questions

- **Unverified:** the expected nested-invocation refusal (see above) did not reproduce in this
  file's testing. Whether the refusal is prompt-shape-dependent, session-shape-dependent, or has
  stopped reproducing on the installed 2.1.251 binary is not established here — settling it needs
  the earlier files' exact refused invocations reproduced side by side.

---

**Leaves covered:** 4.5.1–4.5.2 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** D-96
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 594
