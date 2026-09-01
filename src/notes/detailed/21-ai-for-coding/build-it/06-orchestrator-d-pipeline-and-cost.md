# 21 AI for Coding — the per-stage cost report, and the diff against the real one — BUILD IT (§4.5.7–4.5.8)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 4 of 6** | [Index](../00-index.md)
Previous: [the bulkhead and the bounded retry](06-orchestrator-c-bulkhead-and-retry.md) · Next: [a plugin](07-a-plugin-a.md)

The previous file built a two-stage pipeline — `PipelineStage1` reviews a Java excerpt,
`PipelineStage2` classifies that review's severity — and proved, by re-running stage 2 alone and
checksumming both files before and after, that neither stage writes the path it reads. It deferred
one thing explicitly: a cost panel per stage, tokens and dollars read back out of each envelope. This
file builds that panel, wires it into the same pipeline, and runs the whole thing again for real
numbers. It then closes `ClaudeRunner` with the single largest table in PART 4 — a design-property
diff against the real `harness/src/harness/engine/agent.py`, including the one leg of that file no
earlier note has covered: `--resume` continuation legs.

## A cost report read out of the envelopes already in hand [BUILD] [JAVA] (§4.5.7)

### Mental model

Every `ClaudeEnvelope` this class has ever returned already carries `totalCostUsd` and a `usage`
map — nothing new has to be measured, only collected. `CostReport` is a ledger, not a meter: it
never calls `claude`, never touches a network, and never estimates anything. It takes the receipts
`ClaudeRunner.run()` was already handing back and lines them up, one row per stage, with a total row
underneath.

### Why it exists

`cost-model/03-internals-b-ceilings-and-reading-it-back.md` established the underlying claim this
section applies rather than re-derives: the `-p --output-format json` envelope **is the telemetry
record**. Before that envelope existed as a structured, parseable thing, "how much did this cost"
was answerable only by watching a dashboard or asking a human who was staring at one when the call
ran — an anecdote, not a metric, and certainly not something a budget could be checked against
automatically. A per-stage report is that same claim applied one level up: a **pipeline** cost total
answers "was this run expensive," but it cannot answer "which stage was expensive," and an
orchestrator that cannot answer the second question cannot **attribute** an overspend to the stage
that caused it — only guess, or re-instrument after the fact. You cannot budget a stage you do not
measure, and you cannot hold a stage accountable for spend you never recorded against its own name.

### When to reach for it, and when not

Reach for a per-stage report the moment a pipeline has more than one `ClaudeRunner.run()` call in
it — which is `§4.5.6`'s two-stage pipeline exactly. Skip it for a single bare `run()` call: the
`ClaudeEnvelope` returned already **is** that call's complete cost report, and wrapping one number in
a table with one row adds a class for no benefit. The report earns its keep exactly where there is
more than one row to total.

### How it works

`ClaudeRunner` and its envelope are **unchanged** by this leaf — `CostReport` reads `totalCostUsd()`
and `usage()` off a `ClaudeEnvelope` it is handed, using only the public accessors §4.5.1 already
defined. No new field is added to `ClaudeEnvelope`, no new flag is added to `run()`'s command line.
`CostReport.record(stageName, envelope)` is called once per stage, in the same order the pipeline's
own stages ran, and `printTo` sums four token categories plus the dollar total across every recorded
row:

```java
import java.io.PrintStream;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public final class CostReport {

    public record StageCost(
            String stageName,
            boolean isError,
            double costUsd,
            int inputTokens,
            int outputTokens,
            int cacheReadTokens,
            int cacheCreationTokens) {

        static StageCost from(String stageName, ClaudeRunner.ClaudeEnvelope envelope) {
            Map<String, Integer> usage = envelope.usage();
            return new StageCost(
                    stageName,
                    envelope.isError(),
                    envelope.totalCostUsd(),
                    usage.getOrDefault("input_tokens", 0),
                    usage.getOrDefault("output_tokens", 0),
                    usage.getOrDefault("cache_read_input_tokens", 0),
                    usage.getOrDefault("cache_creation_input_tokens", 0));
        }
    }

    private final List<StageCost> stages = new ArrayList<>();

    public void record(String stageName, ClaudeRunner.ClaudeEnvelope envelope) {
        stages.add(StageCost.from(stageName, envelope));
    }

    public void printTo(PrintStream out) {
        out.printf("%-8s %-7s %-10s %-9s %-9s %-10s %-12s%n",
                "stage", "isError", "costUsd", "inputTok", "outputTok", "cacheRead", "cacheCreate");
        double totalCost = 0.0;
        int totalInput = 0, totalOutput = 0, totalCacheRead = 0, totalCacheCreate = 0;
        for (StageCost s : stages) {
            out.printf("%-8s %-7s %-10.6f %-9d %-9d %-10d %-12d%n",
                    s.stageName(), s.isError(), s.costUsd(), s.inputTokens(), s.outputTokens(),
                    s.cacheReadTokens(), s.cacheCreationTokens());
            totalCost += s.costUsd();
            totalInput += s.inputTokens();
            totalOutput += s.outputTokens();
            totalCacheRead += s.cacheReadTokens();
            totalCacheCreate += s.cacheCreationTokens();
        }
        out.printf("%-8s %-7s %-10.6f %-9d %-9d %-10d %-12d%n",
                "TOTAL", "-", totalCost, totalInput, totalOutput, totalCacheRead, totalCacheCreate);
    }
}
```

Wiring it into the pipeline is one extra field and two extra one-line calls dropped into
`PipelineStage1`/`PipelineStage2`'s bodies from the previous file — `PipelineWithCostReport` below is
the merged result, not a rewrite of either stage's logic:

```java
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;

public final class PipelineWithCostReport {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    public static void main(String[] args) throws IOException, InterruptedException {
        CostReport report = new CostReport();

        Path inputPath = Path.of("/tmp/claude-runner-test/pipeline/input.txt");
        Path stage1OutputPath = Path.of("/tmp/claude-runner-test/pipeline/stage1-review.txt");
        Path stage2OutputPath = Path.of("/tmp/claude-runner-test/pipeline/stage2-verdict.txt");

        // Stage 1 — unchanged from PipelineStage1, plus one line: record into the report.
        String sourceCode = Files.readString(inputPath);
        ClaudeRunner stage1Runner = ClaudeRunner.resolve(
                10, 1.00, 90L, "acceptEdits", "user,project", null, null, Map.of());
        String stage1Prompt = "Review these two Java methods for correctness bugs only. "
                + "Reply with at most 3 bullet points, no preamble:\n\n" + sourceCode;
        ClaudeRunner.ClaudeEnvelope stage1Envelope = stage1Runner.run(stage1Prompt);
        Files.writeString(stage1OutputPath, stage1Envelope.stdoutJson());
        report.record("stage1", stage1Envelope);
        System.out.println("stage1: wrote " + stage1OutputPath + " (isError=" + stage1Envelope.isError()
                + ", totalCostUsd=" + stage1Envelope.totalCostUsd() + ")");

        // Stage 2 — unchanged from PipelineStage2, plus one line: record into the report.
        String stage1Stdout = Files.readString(stage1OutputPath);
        JsonNode root = MAPPER.readTree(stage1Stdout);
        String review = root.path("result").asText("");
        ClaudeRunner stage2Runner = ClaudeRunner.resolve(
                5, 1.00, 90L, "acceptEdits", "user,project", null, null, Map.of());
        String stage2Prompt = "A code review found the following. If it names a real correctness bug, "
                + "reply with exactly one word: CRITICAL. If it only suggests style or found nothing "
                + "wrong, reply with exactly one word: NONE. No other output.\n\n" + review;
        ClaudeRunner.ClaudeEnvelope stage2Envelope = stage2Runner.run(stage2Prompt);
        Files.writeString(stage2OutputPath, stage2Envelope.stdoutJson());
        report.record("stage2", stage2Envelope);
        System.out.println("stage2: read " + stage1OutputPath + ", wrote " + stage2OutputPath
                + " (isError=" + stage2Envelope.isError() + ", totalCostUsd=" + stage2Envelope.totalCostUsd() + ")");

        System.out.println();
        report.printTo(System.out);
    }
}
```

D-97 (embedded in the previous file, not re-embedded here) already draws both stages and the
checksummed re-run; nothing about that picture changes — this leaf adds a column of numbers
alongside it, not a new shape.

### Prove it — §4.5.7

Real, against the installed `claude 2.1.251`, from `/tmp/claude-runner-test`, the whole pipeline
re-run end to end with the report wired in:

```
$ javac -d out -cp "$CP" ClaudeRunner.java CostReport.java PipelineWithCostReport.java
$ java -cp "out:$CP" PipelineWithCostReport
stage1: wrote /tmp/claude-runner-test/pipeline/stage1-review.txt (isError=false, totalCostUsd=0.14553249999999998)
stage2: read /tmp/claude-runner-test/pipeline/stage1-review.txt, wrote /tmp/claude-runner-test/pipeline/stage2-verdict.txt (isError=false, totalCostUsd=0.06482800000000001)

stage    isError costUsd    inputTok  outputTok cacheRead  cacheCreate 
stage1   false   0.145532   2         194       0          22314       
stage2   false   0.064828   2         8         13147      9098        
TOTAL    -       0.210361   4         202       13147      31412       
```

`[PROVE]` Line by line: stage 1 billed **$0.145532** — the more expensive stage, because it is the
first call in this fresh session and pays `22314` cache-creation tokens establishing the prompt
cache from cold, with `0` cache-read tokens to offset it, on top of a `194`-token review reply. Stage
2 billed **$0.064828** — cheaper per-token despite `9098` more output than input, because it reused
`13147` cache-read tokens against the prefix stage 1's call had already primed. The **TOTAL** row is
not printed by summing two dollar figures by hand — it is `printTo`'s own running `totalCost`
accumulator, `0.145532 + 0.064828 = 0.210360…`, printed to six decimal places as `0.210361`
(floating-point rounding on the last digit, not a bug in the addition). This run's actual review
content, quoted rather than described: stage 1 flagged that `brokenResolveMaxTurns` cannot
distinguish an explicit `0` from "not supplied," that both methods throw an unhandled
`NumberFormatException` on a malformed environment value, and that neither validates a negative
resolved turn count — three real, load-bearing findings, none invented for this file. Stage 2's
verdict on that review: `CRITICAL`.

### What this costs

The whole prove step above billed **$0.210361** total — the two real `claude -p` calls the pipeline
itself makes, nothing extra. `CostReport` itself adds no billed call of any kind: `record` and
`printTo` are pure Java over numbers a `ClaudeEnvelope` had already computed before this file ever
ran. That is the report's entire value proposition stated as a cost claim: it turns two numbers a
caller would otherwise have to grep out of two separate JSON files, by hand, after the fact, into one
table, for the price of exactly zero additional tokens.

**Insight:** a report that reads only from envelopes already returned cannot lie about what a stage
spent, but it also cannot see what a stage spent if that stage's `run()` call threw before returning
one — an `AgentTimeoutException` carries no envelope at all (§4.5.5's `Optional.empty()`), so a
pipeline stage that times out contributes a **blank** row to this report, not a zero-cost one. A
caller reading `TOTAL` after a partial failure is reading a total across whichever stages actually
returned, not across every stage that was attempted — the same distinction `runWithRetry` already
draws between "no exception" and "an exception with no envelope to unwrap."

No gotcha beyond the one stated above: a report built purely from returned envelopes is silent about
attempts that never produced one.

> A per-stage cost report is the envelope-as-telemetry principle applied above the single call: it
> turns "how much did the pipeline cost" — a total nobody can act on — into "how much did each named
> stage cost," which is the unit a budget, an alert, or a post-incident attribution actually needs.

## Diff vs the real one: `harness/src/harness/engine/agent.py` [CASE] (§4.5.8)

### Mental model

Eight leaves across four files built one Java class by reading one real Python module end to end and
choosing, deliberately, which of its behaviors to reproduce and which to narrow. This table is the
one place that choice is laid out property by property, so a reader who has read all four files does
not have to reassemble the comparison from six different asides.

### Why it exists

Six earlier files in this guide already quoted pieces of `agent.py` for their own purposes —
persona loading, the failure taxonomy, the resolution order, the retry classification. Repeating
those quotes here would duplicate work already done correctly; this leaf's job is to **cite** each
one by file, add the one property nothing else has covered — `--resume` continuation legs — and lay
every property side by side in one table, because a table read once beats six asides read in six
different files.

### How it works

Six properties `ClaudeRunner` shares scope with `agent.py` on, one row each, plus the constants that
back two of those rows individually. **Excluded from the table, with reason:** the `--effort`,
`--model`, and `--add-dir` flags `agent.py` also resolves — `ClaudeRunner` never took on model or
effort selection or an extra writable directory as part of its scope across any of the eight leaves,
so there is no divergence to report, only an absent feature; and the `DEFAULT_MAX_CONCURRENT_RUNS`
constant already has its own comparison row below rather than being folded into "resolution order,"
since it resolves through exactly one tier, not three, and stands better on its own.

| Design property | Yours (`ClaudeRunner`) | The real one (`agent.py`) | Why the difference |
|---|---|---|---|
| Persona loading + frontmatter stripping | None — every `run()` call takes a raw prompt `String`; there is no `--agent` flag anywhere in the command line built across §4.5.1–§4.5.6 | `load_agent_prompt()` loads a persona `.md` and strips its `--- … ---` frontmatter with the `_FRONTMATTER` regex, walked character-class by character-class in `personas/02-cases-persona-loading.md` | Out of scope by construction: this eight-leaf build never needed a registered `--agent` identity — `PipelineStage1`/`PipelineStage2` both pass a bare task string, closer to `agent.py`'s `system_prompt`/`--append-system-prompt` path than to `--agent` |
| Envelope extraction | `parseOrCaptureSnippet` makes exactly one attempt — `MAPPER.readTree(stdout.strip())` — and falls straight to the 500-character snippet on any failure | `extract_json_envelope` tries `json.loads` first, then falls back to `JSONDecoder().raw_decode` scanned from each `{` in the string — no regex anywhere, per `personas/02-cases-persona-loading.md`'s finding | The real one tolerates a noisy stdout with log lines wrapped around the JSON object; `ClaudeRunner` assumes stdout is either clean JSON or nothing parseable at all. This is a real gap, not a stylistic choice — a `claude -p` call that ever printed a stray banner line before its JSON would defeat `parseOrCaptureSnippet` where `extract_json_envelope` would still find the object |
| The retry loop's classification | Terminal on **any** unparseable envelope and **every** ceiling (`error_max_turns`, `error_max_budget_usd`); retries only `AgentTimeoutException` and process-launch `IOException` — full table and reasoning in `06-orchestrator-c-bulkhead-and-retry.md` §4.5.5 | Retries an unparseable envelope **and** a general `is_error: true` result too; only `subtype == "error_max_turns"` is carved out as terminal, per the same file's citation of `agent.py` lines 296–309 | Already argued in full in the cited file: neither is more correct — the real loop buys resilience against transient agent-side flakiness at the cost of multiplying spend on failures that reproduce identically; this narrower version buys predictable spend at the cost of surfacing more unretried failures, on the assumption that no outer CI continuation layer exists to catch what the inner loop doesn't |
| Resolution order (parameter → env → default) | Boxed `Integer`/`Long`/`String` params checked `!= null` for `maxTurns`/`timeoutSeconds`; blank-checked `String`s for `permissionMode`/`settingSources`; `settingsPath` two-tier, no default — full derivation in `05-orchestrator-b-ceilings-and-resolution.md` §4.5.4 | `max_turns if max_turns is not None else int(os.environ.get(...))`; `permission_mode or os.environ.get(...) or DEFAULT_PERMISSION_MODE`; `settings` two-tier via `or`, no default — same shape, `agent.py` lines 242–257 | No meaningful divergence: this is one property where the Java and Python versions match property-for-property, including which knobs get a presence check versus a truthiness check and why. Recorded here for completeness of the table, not because there is a trade to explain |
| `--resume` continuation legs | None — every `ClaudeRunner.run()` call is a fresh, independent process; no field on the class ever holds a `session_id`, and no method accepts one | `resume_session_id` (when set) adds `--resume <id>` to the command line (line 271); `continuation.py`'s `run_coder_with_continuations` sets it to the **prior leg's own `session_id`** specifically when that leg exhausted `--max-turns`, judged independently by a "progress verifier" persona, bounded by a depth/leniency curve and a cumulative dollar ceiling | `ClaudeRunner`'s bounded retry (§4.5.5) only ever retries *infrastructure* failures with a *fresh* process; it has no mechanism at all for "the agent made real progress but ran out of turns, resume the same conversation instead of starting over." The real one added this specifically because a turn-exhausted leg with no continuation just becomes a dead end — exactly the AP-12200 shape `05-orchestrator-a-the-runner.md` §4.5.2 already quotes in full |
| `DEFAULT_MAX_TURNS = 160` | Same constant, same value, adopted verbatim | `DEFAULT_MAX_TURNS = 160`, with the AP-12200 incident comment above it (raised from 80) — quoted in full in `05-orchestrator-a-the-runner.md` §4.5.2 | No divergence — this file's constant is the real one, copied rather than reinvented, precisely so a maintainer reading both codebases finds one number, not two that drift apart over time |
| `DEFAULT_TIMEOUT = 1800` / `DEFAULT_PERMISSION_MODE = "acceptEdits"` / `DEFAULT_SETTING_SOURCES = "user,project"` | Same three constants, same three values, same names minus the `HARNESS_` env-var prefix mirrored instead as `MAX_TURNS_ENV` etc. — `05-orchestrator-b-ceilings-and-resolution.md` §4.5.4 | Same three constants, module-level in `agent.py`, each with its own one-line recorded reason inline in the source (timeout is the wall-clock backstop regardless of turn count; `acceptEdits`/`user,project` are the safe unattended defaults) | No divergence in value; recorded here because the leaf asks for "every default constant with its recorded reason," and these three carry theirs in the real file's own comments, already quoted in the cited files rather than re-quoted here |
| Concurrency bulkhead (`Semaphore`, `DEFAULT_MAX_CONCURRENT_RUNS = 4`) | One resolution tier only — caller's value, or the default, no environment override — `06-orchestrator-c-bulkhead-and-retry.md` §4.5.5 | **No equivalent at all.** `agent.py` and `continuation.py` have no concurrency-bounding construct; the real harness's own fan-out limits, where they exist, live at the orchestration layer above this module, not inside `run_agent` itself | `ClaudeRunner` added a bulkhead because the sub-agent guide's own §2.1.14 finding — the platform's 20-concurrent-subagent ceiling — is a limit *something else* enforces; the bulkhead is a limit *this code* enforces on itself, before that ceiling fires. This is a genuine addition, not a narrowing, and the table records it as such rather than forcing it into a row implying the real one has one too |

`--resume`'s mechanics, verified against `cli-reference` rather than recalled: **`[DOC]`** the page
states `--resume` "Resume a specific session by ID or name, or show an interactive picker to choose a
session," and separately notes that **before v2.1.223** its ID search covered only the current
project directory and its git worktrees, while the current line searches "the current project
directory and its git worktrees, then every other project on this machine" — a version trap for
anyone who last read this page before that release. The documentation page is silent on the JSON
envelope's cost/token fields entirely; `total_cost_usd` and `usage` are observed-envelope facts, not
documented ones, consistent with every earlier file in this build treating them the same way.

**What a continuation leg is, and why an orchestrator needs one.** A continuation leg is a second
(or third, or fourth) `claude -p --resume <session_id>` call that picks up **the same conversation**
a prior call left off, rather than starting a fresh one. `agent.py`'s own module docstring states the
general design rule plainly: agents are stateless, "no `--resume`," cross-attempt memory is a cold
feedback file the outer loop hands back in, never a live session. `continuation.py` is the deliberate,
narrow exception to that rule: when a coder leg hits `error_max_turns` — turn exhaustion, not an
error, not a crash — restarting cold and reconstructing 160 turns of context from a feedback file
throws away exactly the reasoning trace that got the agent to "13 green tests and a correct fix" in
the AP-12200 incident. Resuming the same session_id instead lets the model continue **from its own
prior state**, not from an engineer's summary of that state.

**A continuation leg is not free**, and this file is not the one that measured why:
`headless/03-internals-b-formats-and-execution.md` already proved that a resumed call re-sends the
entire prior transcript, visible as a jump in `cache_read_input_tokens`/`cache_creation_input_tokens`
rather than a small delta — resuming a session does not mean "the model remembers for free," it means
"the full prior conversation is billed again as cache-read tokens on every leg," cheaper than
re-deriving the same context from raw tool calls but never zero. It beats starting fresh exactly when
the cost of re-sending an already-primed transcript is smaller than the cost of losing the agent's own
in-progress reasoning and re-deriving it — which is precisely the trade `continuation.py`'s dollar
ceiling and depth/leniency curve exist to bound, rather than allow to run unchecked leg after leg.

**Interview:** "your orchestrator never resumes a session — is that a bug?" — no, it is a stated scope
boundary: `ClaudeRunner`'s bounded retry (§4.5.5) only handles infrastructure failures with fresh
processes, and this table records the omission explicitly rather than silently. A resume mechanism is
buildable on top of the same class — capture `session_id` from the envelope, thread it through a new
`--resume` branch in `run()`'s command list the same way `--settings` was added in §4.5.3 — but it was
never built across these eight leaves, and the honest answer names that rather than implying parity
with `continuation.py` that does not exist.

No gotcha beyond the one already stated for envelope extraction: a noisy stdout defeats
`parseOrCaptureSnippet` where the real one's `raw_decode` scan would still find the object.

> **`ClaudeRunner` and `agent.py` share the same core shape** — a stateless `claude -p
> --output-format json` subprocess wrapper with a parameter → environment → default resolution chain
> — and diverge in exactly the places this table names: no persona loading, a single-attempt envelope
> parse instead of a tolerant scan, a narrower terminal-by-default retry, no continuation mechanism,
> and one addition the real one has no counterpart for at all, a self-enforced concurrency bulkhead.

## `ClaudeRunner` is complete

Eight leaves, four files, one class, extended and never rewritten. What each leaf built, in the order
it was built:

| § | File | What it added |
|---|---|---|
| 4.5.1 | `05-orchestrator-a-the-runner.md` | The `ProcessBuilder`/`ClaudeEnvelope` core: two virtual threads draining stdout/stderr concurrently, `parseOrCaptureSnippet`'s 500-character bound, `is_error` read from JSON rather than exit code |
| 4.5.2 | `05-orchestrator-a-the-runner.md` | Three ceilings — `--max-turns`, `--max-budget-usd`, `Process.waitFor(Duration)` — each its own exception type, proven live including the 619-fold budget overshoot |
| 4.5.3 | `05-orchestrator-b-ceilings-and-resolution.md` | `--settings <absolute path>`, evaluated independently of `cwd`, proven live against a real `Bash(echo:*)` deny rule |
| 4.5.4 | `05-orchestrator-b-ceilings-and-resolution.md` | Parameter → environment → default resolution for five knobs, boxed types checked `!= null` so an explicit `0` survives, proven against a deliberately broken sibling method |
| 4.5.5 | `06-orchestrator-c-bulkhead-and-retry.md` | `AgentCeilingException.envelope()` so a ceiling hit no longer discards its billed cost; a classified `runWithRetry`; a fair `Semaphore` bulkhead proven by wall clock (36.1s at 1 permit, 9.1s at 4) |
| 4.5.6 | `06-orchestrator-c-bulkhead-and-retry.md` | `PipelineStage1`/`PipelineStage2`, proven independently re-runnable by re-running stage 2 alone and checksumming stage 1's untouched output |
| 4.5.7 | this file | `CostReport`, reading tokens and dollars back out of envelopes already returned, run for real against the same two-stage pipeline: `$0.210361` total, stage 1 `$0.145532`, stage 2 `$0.064828` |
| 4.5.8 | this file | The design-property diff against `agent.py` — five narrowings, one exact match, one pure addition, and the one gap this table names rather than hides: no `--resume` continuation leg |

Every command in all four files ran against the installed `claude 2.1.251`. Nothing in the class was
invented, and nothing proven early was re-tested from scratch later — each file built on the last
file's compiled, working code.

## Pitfalls

- **Belief:** a pipeline's total cost is enough to manage its budget. **Symptom:** a two-stage run
  costs `$0.210361`, and nothing about that single number says stage 1 spent more than twice what
  stage 2 did, or why — an alert on the total fires with no lead on which stage to look at. **Fix:**
  record cost per named stage, as `CostReport` does, so a budget check and a post-incident
  attribution both have a row to point at rather than a lump sum. **Why people believe it:** a total
  is the number that answers "did we blow the budget," which is the first question anyone asks — it
  just is not the number that answers the second question, "on what."
- **Belief:** an envelope-reading cost report is a complete accounting of a pipeline run.
  **Symptom:** a stage that throws `AgentTimeoutException` contributes no row at all — not a
  zero-cost row, an absent one — because `Optional.empty()` never reaches `CostReport.record`. A
  `TOTAL` read after a partial failure looks like the full pipeline's cost when it is only the cost
  of the stages that returned. **Fix:** treat a report's silence about a stage as a signal to check
  for a thrown exception, not as proof that stage cost nothing. **Why people believe it:** the report
  looks complete because every row it does print is accurate — the gap is in what never became a row.
- **Belief:** matching the real harness's persona loading, retry breadth, and continuation mechanism
  is what "finishing" this class would mean. **Symptom:** treating the omissions in the diff table
  above as bugs to fix rather than scope this build never took on. **Fix:** read the "why the
  difference" column before assuming any row names a defect — most name a deliberate narrowing (a
  bounded orchestrator with no outer CI layer, unlike `agent.py`'s) or an addition the real one simply
  never needed (the bulkhead). **Why people believe it:** parity with a real system reads like the
  natural finish line for a from-scratch reimplementation of it.

## Cheat sheet

| Concern | Mechanism | Detail |
|---|---|---|
| Cost per stage | `CostReport.record(name, envelope)` + `printTo` | Reads `totalCostUsd()`/`usage()` off envelopes already returned; no new `claude` call |
| This run's real total | `PipelineWithCostReport` | `$0.210361` — stage1 `$0.145532` (cold cache, 22314 cache-creation tokens), stage2 `$0.064828` (warm, 13147 cache-read tokens) |
| What a silent row means | Report built only from returned envelopes | A stage that threw `AgentTimeoutException` (no envelope) is **absent**, not zero-cost |
| Persona loading | Not in `ClaudeRunner` at all | Real one: `load_agent_prompt()` + `_FRONTMATTER` regex, cited from `personas/02-cases-persona-loading.md` |
| Envelope extraction | Single `readTree` attempt, snippet on failure | Real one: `json.loads` then `raw_decode` scan from each `{` — more tolerant of noisy stdout |
| Retry breadth | Terminal on any ceiling + any unparseable envelope | Real one retries unparseable + general `is_error`; only `error_max_turns` terminal — see `06-orchestrator-c` |
| Resolution order | Boxed types, `!= null` where zero is meaningful | Matches the real one property-for-property — no divergence |
| `--resume` | Not implemented — every call is fresh | Real one: `continuation.py` resumes the same `session_id` across turn-exhaustion legs only, bounded by depth and a dollar ceiling |
| Concurrency bulkhead | `Semaphore(n, true)`, one resolution tier | Real one has none — a pure Java-side addition, no counterpart to diverge from |

## Self-test

<details><summary>1. Why does stage 1 cost more than stage 2 in this run's actual numbers, despite stage 2's prompt containing more text (the full review)?</summary>
Stage 1 is the first call in a fresh session, so it pays `22314` cache-creation tokens establishing
the prompt cache from cold with `0` cache-read tokens to offset it. Stage 2 runs against an
already-primed cache and reuses `13147` cache-read tokens, which are billed far cheaper than the
cache-creation tokens stage 1 had to pay — the same warm/cold asymmetry §4.5.1 first measured.
</details>

<details><summary>2. A pipeline stage throws `AgentTimeoutException`. What does `CostReport`'s `TOTAL` row show for that run?</summary>
Whatever the other stages' envelopes summed to — nothing accounts for the timed-out stage at all,
because `AgentTimeoutException.envelope()` returns `Optional.empty()` and nothing ever calls
`report.record` for it. The row is absent, not zero.
</details>

<details><summary>3. Name the one property in the diff table where `ClaudeRunner` and `agent.py` do not diverge at all.</summary>
The resolution order: parameter → environment → default, presence-checked wherever a falsy value
(`0`, blank) is meaningful and truthiness-checked elsewhere. Both `05-orchestrator-b-ceilings-and-resolution.md`
and this file's table find the two implementations match property-for-property.
</details>

<details><summary>4. What does `--resume` do according to `cli-reference`, and what changed about it in v2.1.223?</summary>
It resumes a specific session by ID or name, or shows an interactive picker. Before v2.1.223, ID
search covered only the current project directory and its git worktrees; from v2.1.223 on, it also
searches every other project on the machine after that.
</details>

<details><summary>5. Why is a continuation leg (`--resume <session_id>`) not free, even though it "just" continues a conversation?</summary>
`headless/03-internals-b-formats-and-execution.md` measured that a resumed call re-sends the entire
prior transcript, visible as a jump in `cache_read_input_tokens`/`cache_creation_input_tokens` rather
than a small delta. The whole prior conversation is billed again on every leg — cheaper than
re-deriving lost context from scratch, but never zero.
</details>

<details><summary>6. Why does `agent.py`'s own module docstring say "No `--resume`" when `continuation.py` clearly uses it?</summary>
The docstring states the general design rule for ordinary stateless calls: no session memory,
cross-attempt context is a cold feedback file. `continuation.py` is a deliberate, narrow exception to
that rule, scoped only to a coder leg that hit `error_max_turns` — turn exhaustion specifically, never
an ordinary retry — judged independently by a progress verifier and bounded by a budget ceiling, not
a general-purpose relaxation of the stateless design.
</details>

<details><summary>7. `ClaudeRunner` has a `Semaphore` bulkhead; `agent.py` has none. Is this a narrowing or an addition?</summary>
An addition. Every other row in the diff table where the two diverge is `ClaudeRunner` doing *less*
than the real one (no persona loading, a less tolerant envelope parse, a narrower retry, no
continuation mechanism). The bulkhead is the one row running the other direction — `ClaudeRunner`
built a self-enforced concurrency cap that the real harness's `run_agent`/`continuation` modules never
needed, because their own fan-out limits live at a different layer entirely.
</details>

## Open questions

None.

---

**Leaves covered:** 4.5.7–4.5.8 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none — D-96 and D-97 in the three preceding files draw the class, the boundary and the pipeline
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 432
