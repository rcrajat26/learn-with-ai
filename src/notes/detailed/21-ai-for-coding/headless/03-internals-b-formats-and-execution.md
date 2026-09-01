# 21 AI for Coding — formats, sessions and background execution — ADVANCED (INTERNALS) (§3.6.6–3.6.9)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 3 of 6** | [Index](../00-index.md)
Previous: [the headless surface](03-internals-a-the-surface.md) · Next: [a wrapper's failure taxonomy](03-internals-c-the-failure-taxonomy.md)

The previous file established `claude -p` as a function call, tabled the three output formats and two
input formats, and quoted a real envelope in full. Every one of those calls was **one-shot**: one
process, one prompt, one exit. This file is about what changes once a caller needs more than one
shot — resuming the same conversation from a second process, running a task nobody is watching, and
knowing which flags a production wrapper actually reaches for versus which it only reads about once.
`session_id`, the field this file leans on hardest, was already in the previous file's envelope table
as "the argument to `--resume`/`-r`" — this file cashes that promissory note in.

### 1. The flag set a production wrapper needs — a checklist, not a tutorial

`[DOC]` §3.6.6 asks for a checklist, and a checklist is what it gets: every flag re-verified against
`cli-reference` on 2026-08-30, with a pointer to where each is taught in depth rather than re-teaching
flags this guide already owns elsewhere.

| Flag | What it does | Taught in depth |
|---|---|---|
| `--agent` | Overrides the `agent` setting for this session | Part 2, subagents/personas |
| `--output-format` | `text` / `json` / `stream-json` | Previous file, §2 |
| `--max-turns` | Caps agentic turns, **print mode only**, no limit by default; exits with an error at the limit | Below, §1a |
| `--permission-mode` | Starts the session in one of the six modes | Part 1, permissions (§1.4.25) |
| `--setting-sources` | Which of `user`, `project`, `local` load | Part 1, settings precedence (§1.2) |
| `--settings` | A settings JSON file or inline string, ≤2 MiB, overriding matching keys for this session only | Part 1, settings precedence |
| `--model` | Session model override; alias or full name | Part 3, effort-and-routing |
| `--effort` | Session effort override; does not persist | Part 3, effort-and-routing |
| `--add-dir` | Grants file access to extra directories — **not** their `.claude/` configuration | Part 1, directories and trust |
| `--append-system-prompt` | Appends text to the default system prompt | Below, §1b |
| `--resume` / `-r` | Resumes a session by ID or name, or opens a picker | Below, §2 |
| `--max-budget-usd` | A dollar ceiling on API spend, **print mode only**; subagent spend counts toward it | Below, §1c |
| `--session-id` | Pins the session's UUID instead of letting Claude Code generate one | Below, §2 |
| `--no-session-persistence` | Nothing is written to disk; nothing is resumable, **print mode only** | Below, §2 |
| `--allowed-tools` | Pre-approves matching tool calls | Part 1, permissions |
| `--disallowed-tools` | Removes or denies matching tools | Part 1, permissions |
| `--mcp-config` | Loads MCP servers from files or strings | Below, §1d |
| `--verbose` | Turns on debugging/streaming detail alongside `stream-json` | Previous file, §4 |

Four of these earn a few lines here because no other file in this guide owns them by name:

**§1a — `--max-turns`.** `[NUM]` No default limit; when set, an exceeded limit is a hard error, not a
graceful stop with partial output. `[TRAP]` **Pitfall:** treating `--max-turns` as a budget control.
The symptom: a wrapper sets `--max-turns 10` to "cap spend" and instead gets a run that dies mid-task
at turn 10 with nothing usable, because turns and dollars are different axes — a single turn can call
three tools and cost fifty cents, or call none and cost a cent. The fix: cap dollars with
`--max-budget-usd` (§1c) and cap turns with `--max-turns` for a different reason — runaway agentic
loops, not spend. **Why people believe it:** "turns" sounds like a proxy for "amount of work done," and
work sounds like a proxy for cost, but the exchange rate between the two is not fixed.

**§1b — `--append-system-prompt`.** Appends to, never replaces, the default system prompt — a headless
wrapper that wants "always write tests before implementation" stated for every call adds it here rather
than re-authoring the whole system prompt. `[VERSION]` `--setting-sources` §1.2's PART 1 treatment
already covers the file-based equivalent (`CLAUDE.md`); this flag is the process-argument form for a
wrapper that has no file to write to, such as a stateless Lambda invocation.

**§1c — `--max-budget-usd`.** `[VERSION]` The cap-enforcement behavior — spawning a subagent past the
cap fails with `Budget limit reached`, and Claude Code actively stops background subagents still
running when the cap is crossed — requires **Claude Code v2.1.217 or later**; on an older binary the
flag may be accepted but not enforced the same way. Subagent spend counts toward the parent's cap, so a
wrapper that sets `--max-budget-usd 5.00` on the top-level call is capping the whole tree, not just the
top-level model calls.

**§1d — `--mcp-config`.** `[VERSION]` Combined with `-p`, Claude Code waits for still-pending MCP
servers to finish connecting before running the first turn, up to the `MCP_TIMEOUT` startup timeout
(30 seconds by default) — a server with a cached tool list skips the wait and connects lazily on first
use instead. This wait-for-connection behavior requires **v2.1.221 or later**. `[TRAP]` **Pitfall:** a
CI job that adds a new MCP server and immediately calls a tool from it in the first turn, timing out on
an older binary that does not wait — the fix is either the version floor or a warm first turn that does
not depend on the new server.

No SVG is assigned to §3.6.6; the previous file's D-80 already draws the flags that produce the
envelope this checklist points a caller at, and nothing here needs a new picture.

### 2. Session identity — what a session ID actually pins, and what resuming it restores

**Mental model.** A Claude Code session is not "the model remembering a conversation" — PART 0
established that the model has no memory between calls and that every turn re-sends the whole context
window. A **session** is Claude Code's own record of that growing context window, addressed by a UUID
and persisted to disk as a transcript. `--resume` does not wake up a dormant model; it hands the next
`claude -p` process the same transcript to re-send as if the conversation had never stopped.

**Why it exists.** A single `claude -p` call is one function call. A wrapper that needs a *multi-call*
conversation — a code-review bot that asks a follow-up after a human comments, a CI pipeline that
re-invokes the same task after fixing one file — cannot hold that state in the calling process, because
the calling process is not what remembers anything; the transcript is. Session persistence is what
makes "the next process invocation continues where the last one left off" possible at all.

**How it works.** `[DOC]` Re-verified against `cli-reference`, 2026-08-30. Five flags jointly control
identity and continuity:

| Flag | Effect | Requires |
|---|---|---|
| `--session-id <uuid>` | Pins the session to a caller-supplied UUID instead of a generated one | Must be a valid UUID |
| `--resume <id-or-name>` / `-r` | Resumes a specific session, or opens an interactive picker with none given | — |
| `--continue` / `-c` | Loads the most recent conversation in the current directory | Skips background sessions, `-p`/SDK sessions and `/loop` sessions unless the call itself is `-p --continue` |
| `--fork-session` | On resume, issues a **new** session ID instead of reusing the original | Used with `--resume` or `--continue` |
| `--no-session-persistence` | Nothing is written to disk at all | Print mode only; `CLAUDE_CODE_SKIP_PROMPT_HISTORY` does the same in any mode |

`[VERSION]` `--resume`'s ID search widened in **v2.1.223**: before that version the search covered only
the current project directory and its git worktrees; from v2.1.223 on, an unmatched ID search continues
across every other project on the machine. A wrapper pinning to an older binary cannot assume a session
started in one checkout is resumable from another.

`[PROVE]` This is not constructed — it is four real `claude -p` calls made while writing this file,
against Claude Code v2.1.251:

```bash
$ claude -p "Reply with the single word: acorn." --output-format json
```
```json
{ "session_id": "0f828489-aa6a-4a1a-88cf-9c2c726c55be", "result": "acorn",
  "usage": { "cache_creation_input_tokens": 11356, "cache_read_input_tokens": 10476 },
  "total_cost_usd": 0.077304 }
```
```bash
$ claude -p --resume 0f828489-aa6a-4a1a-88cf-9c2c726c55be \
    "What was the single word you replied with in your previous message? Answer with just that word." \
    --output-format json
```
```json
{ "session_id": "0f828489-aa6a-4a1a-88cf-9c2c726c55be", "result": "acorn",
  "usage": { "cache_creation_input_tokens": 54, "cache_read_input_tokens": 21832 },
  "total_cost_usd": 0.0113885 }
```

Two things this second call proves, neither of which is a matter of trust: first, `session_id` in the
reply is **identical** to the one passed in — resuming does not mint a new identity. Second,
`cache_read_input_tokens` rose from 10,476 to 21,832, a jump of 11,356 tokens — exactly the first call's
`cache_creation_input_tokens`. That is the first turn's entire context (system prompt, tool
definitions, the first exchange) being re-read from cache and re-sent as the prefix of the second call,
not recalled by a stateful model. Resuming a session is re-sending its whole prior transcript, cheaply,
because it was cached — the same "context window as the argument list of the next call" mechanic from
PART 0, now demonstrated across two separate OS processes rather than two turns of one.

`--fork-session` on the same conversation:

```bash
$ claude -p --resume 0f828489-aa6a-4a1a-88cf-9c2c726c55be --fork-session \
    "Reply with the single word: birch." --output-format json
```
```json
{ "session_id": "e64437f7-908a-4a4d-b33f-4ab9e625b23f", "result": "birch" }
```

A new UUID, not the one that was resumed — the transcript up to the fork point is copied forward, but
the original session `0f828489…` is left untouched for a second, independent continuation. This is the
mechanism a wrapper reaches for to try two different next steps from the same checkpoint without either
one corrupting the other.

`--no-session-persistence`, and what resuming it produces:

```bash
$ claude -p --no-session-persistence "Reply with the single word: pebble." --output-format json
```
```json
{ "session_id": "dc9cd10f-5e45-4f02-86e4-c194d1ff27ad", "result": "pebble" }
```
```bash
$ claude -p --resume dc9cd10f-5e45-4f02-86e4-c194d1ff27ad "What word did you just say?" \
    --output-format json
No conversation found with session ID: dc9cd10f-5e45-4f02-86e4-c194d1ff27ad
$ echo $?
1
```

`[TRAP]` **Pitfall:** assuming `--output-format json` guarantees a JSON object on every exit path. The
symptom above is real: the resume attempt was called with `--output-format json` and still printed a
bare, unquoted line of plain text to stdout, exited `1`, and produced no JSON object at all. The fix: a
wrapper's parser must handle "process exited nonzero with non-JSON stdout" as its own branch *before*
attempting to parse — `--output-format` governs the shape of a **completed run's** result, not of a
pre-flight failure that occurs before a run starts. **Why people believe it:** every other exit path
this file and the previous one exercised did honor the flag, so it reads as an unconditional contract
until the one failure mode that occurs before the envelope machinery is even reached.

Still open from a session-control standpoint, forward-pointing rather than answered here: a Java
orchestrator holding this UUID across process boundaries (a `ClaudeRunner` invoked once per pipeline
stage, from a Spring Boot service that outlives any single `claude` subprocess) has to persist
`session_id` itself — in a database row, a workflow context, a file — because nothing about the Claude
Code process remembers that it was ever asked to keep talking. `build-it/05-orchestrator-a-the-runner.md`
builds exactly that persistence layer; this file only establishes why it is load-bearing rather than
optional plumbing.

**Gotcha.** Covered above as the pre-flight-failure `**Pitfall:**` — no second, separate gotcha beyond
it.

> A session ID names a persisted transcript, not a live model process; `--resume` re-sends that
> transcript as the next call's context, `--fork-session` copies it into a new independent identity, and
> `--no-session-persistence` means there is nothing later to resume at all.

### 3. `claude setup-token` — the CI credential, and what an unattended run must not have

**Mental model.** An interactive `claude` session authenticates once, in a browser, with a human
present to click through consent. A CI job has no browser and no human. `claude setup-token` is the
bridge: it runs the same OAuth flow once, from a machine that *does* have a browser and a human, and
hands back a credential a headless environment can hold instead of ever performing that flow itself.

**Why it exists.** The three ways to authenticate a headless `claude -p` call are not interchangeable,
and conflating them is where CI credential incidents come from:

| Method | What it is | Where it may live | Expiry |
|---|---|---|---|
| Interactive OAuth login | Browser consent flow | Never in CI — no browser, no human | Session-based |
| `ANTHROPIC_API_KEY` | A raw API key, billed per token directly against the API | An env var injected by the CI secret store | Until rotated |
| `claude setup-token` | A long-lived OAuth token generated once interactively | A CI secret store, exported as an env var | Long-lived, revocable |

**How it works.** `[DOC]` Re-verified against `cli-reference`, 2026-08-30, quoted exactly:

> `claude setup-token` — Generate a long-lived OAuth token for CI and scripts. Prints the token to the
> terminal without saving it. Requires a Claude subscription.

**This command was not executed for this file.** Running it prints a live, real credential to
whichever terminal invokes it — the one artefact in this entire leaf set that must never appear in a
transcript, a log file, or this guide, so the fact it "prints the token to the terminal without saving
it" is taken from the documentation, not demonstrated. That restraint is itself the leaf's point:
§3.6.8 asks what an unattended run must **not** have, and the answer is exactly this shape of exposure.

**Code.** What the generated token is for is a headless CI step, never a checked-in file:

```bash
# In the CI secret store, never in the repository:
#   CLAUDE_CODE_OAUTH_TOKEN = <output of `claude setup-token`, run once by a human>
claude -p "Run the story's acceptance tests and report pass/fail." --output-format json
```

**Gotcha.** `[TRAP]` **Pitfall:** treating "the token isn't an API key" as meaning it is safe to echo
into CI logs for debugging. The symptom: a build step does `echo "token: $CLAUDE_CODE_OAUTH_TOKEN"` to
confirm the variable is set, and the token is now sitting in plaintext in a CI log that a wider audience
than the pipeline's owner can read — a long-lived, revocable credential is still a bearer credential; a
lower rotation burden is not the same property as a lower blast radius if leaked. The fix: check
*presence* (`[ -n "$CLAUDE_CODE_OAUTH_TOKEN" ]`), never *value*, in any CI log line. **Why people
believe it:** "long-lived and revocable" reads as "less sensitive," but revocability only helps after
someone notices the leak — nothing about the token's shape stops it from working for anyone who reads
the log before that happens.

> `claude setup-token` moves one interactive OAuth consent step onto a human's machine once, so that
> every subsequent unattended run holds a revocable credential instead of ever performing — or
> having access to perform — a browser login itself.

### 4. Background and remote execution — where output goes when nobody is watching

**Mental model.** Every call in §2 was still synchronous: the calling shell blocked until the process
exited. `--bg`, the cloud flags, and `--teleport` are the three ways Claude Code stops being something a
caller waits on and starts being something a caller checks on later — a shift from "return value" to
"long-running job with a status endpoint," which changes what a caller must ask: not "what did it
return" but "where did it go, and how do I know it's done."

**Why it exists.** A one-shot `-p` call is wrong for a task that runs for an hour, or that a user wants
to dispatch and walk away from. Before background mode, the only options were an actual detached shell
process (`nohup`, `&`, losing the structured envelope entirely) or a cloud product unrelated to the
local CLI. `--bg` gives the local binary its own supervisor process so a long task survives the
terminal that started it, without leaving the machine at all; `--cloud`/`--environment`/`--teleport`
give the same "walk away" property when the task should run somewhere else entirely — a fresh
environment, or infrastructure the local machine does not have.

**How it works.** `[DOC]` Re-verified against `cli-reference`, 2026-08-30. `[NUM]` `--bg` **cannot be
combined with `-p`/`--print`** — background sessions and headless print-mode calls are two different
execution surfaces, not composable flags on one call.

| Surface | Invocation | Runs where | How a caller learns it finished |
|---|---|---|---|
| Background, local | `claude --bg "<task>"` | A local supervisor (daemon) process on this machine | `claude logs <id>` / `claude attach <id>`; not a JSON envelope on the invoking shell, because that shell already returned |
| Cloud, ad hoc | `claude --cloud "<task>"` | A web session on claude.ai | The claude.ai session UI, or a follow-up `-p --cloud <session-id-or-url>` |
| Cloud, self-hosted | `claude -p "<task>" --environment ccpool_<id>` | A named self-hosted environment (`ccpool_…`), optionally against `--ref <branch>` instead of local `HEAD` | The same `-p` envelope this file's §2 already covers, once that remote run completes |
| Teleport | `claude --teleport` | Resumes a web session **in the local terminal** | Interactive by definition — this one has no headless form |

`[VERSION]` `--environment` requires **Claude Code v2.1.224 or later**.

Subcommands that manage a background session once `--bg` has started one:

| Command | Effect |
|---|---|
| `claude attach <id>` | Opens the running session in this terminal |
| `claude logs <id>` | Prints recent output from the session |
| `claude stop <id>` (alias `claude kill <id>`) | Stops the session |
| `claude respawn <id>` | Restarts the session, running or stopped, with its conversation intact; `--all` restarts every running session (for example, after a binary upgrade) |
| `claude rm <id>` | Removes the session from the list; the transcript itself stays on disk, resumable through `--resume` |
| `claude daemon status` | Prints the supervisor's pid, version, socket directory and worker count; exits `1` if no supervisor is running |

`[PROVE]` A real background session, started, inspected and torn down while writing this file, against
v2.1.251:

```bash
$ claude --bg "Reply with the single word: lantern, then stop."
Starting background service…
backgrounded · d6be729c
  claude agents             list sessions
  claude attach d6be729c    open in this terminal
  claude logs d6be729c      show recent output
  claude stop d6be729c      stop this session
```

`claude logs d6be729c` did not return a clean, line-oriented log — it returned a captured frame of the
session's own rendered terminal UI, ANSI escape codes and all, with the completed reply ("lantern")
buried inside the control sequences. `[TRAP]` **Pitfall:** wiring `claude logs <id>` into a script that
`grep`s the output for a result string. The symptom: the match is unreliable because the bytes on the
line are terminal-control-sequence-laden, not the plain text a `stream-json` pipe would have given
§2 of the previous file. The fix: a wrapper that needs a machine-parseable result from a background task
resumes its session ID with `-p --resume <id> --output-format json` once it is done, rather than
scraping `logs`. **Why people believe it:** `logs` reads as a log-file convention from every other
long-running-process tool a backend engineer has operated, where the output is plain text by design.

`claude daemon status`, quoted verbatim, while one worker was still running:

```
pid:     92007
version: 2.1.251
uptime:  12s
origin:  transient — started on-demand by `claude --bg` (pid 91999) in /private/tmp
bg workers:   1 running (control.sock), 1 in roster.json
holding this daemon open:
  1 bg worker running (daemon waits for them to settle)
```

**Insight:** the daemon is **transient by default** — it starts on demand the first time something calls
`--bg`, and its own status output says plainly what would let it exit (no workers left, no `claude
agents` view open). A caller does not provision a long-running supervisor ahead of time; the first
background dispatch provisions it, and the last one torn down retires it. After `claude stop d6be729c`
followed by `claude rm d6be729c`, the same `daemon status` call reported `0 running`, `0 in roster.json`,
and "nothing holding this daemon open — will idle-exit shortly" — the lifecycle closing itself with no
separate teardown command required.

`[TRAP]` **Pitfall:** assuming `claude rm <id>` deletes the conversation. The symptom: a wrapper cleans
up with `rm` after a background task finishes and later cannot find the transcript through `--resume`.
The documented and observed behavior is the opposite: `rm` only drops the session from the *background
management list* — the transcript is untouched on disk and remains reachable through `--resume` exactly
as any other session would be. The fix: `rm` is bookkeeping hygiene, not deletion; nothing in this
surface deletes a transcript.

`--cloud`, `--environment` and `--teleport` were **not executed** for this file — `--cloud` and
`--teleport` operate against a claude.ai web session and `--environment` requires a provisioned
`ccpool_…` self-hosted environment, none of which exists in this run's local sandbox. **Unverified:**
the exact shape of a `--cloud`-created session's follow-up dispatch beyond what `cli-reference` states
(`-p --cloud <session-id-or-url>` queues a message into an existing session) was not observed directly.

No SVG is assigned to §3.6.9; D-81 (the failure taxonomy) and D-82 (the resolution order) in the next
two files are the diagrams this Part still owes, and neither draws execution topology, so this leaf's
"SVG" link is genuinely not applicable — recorded here rather than silently skipped.

**Gotcha.** Folded into the `**Pitfall:**` entries above (`logs` is not machine-parseable; `rm` is not
deletion) — no further gotcha beyond those two.

> `--bg` hands a task to a local, on-demand supervisor process that survives the terminal that started
> it; the cloud flags hand it to infrastructure that is not this machine at all; in every case, "how do
> I know it's done" stops being "the process exited" and becomes "I asked something that outlived the
> call that started it."

## Pitfalls

- **Belief in action:** `--max-turns` is a spend control. **Surprising outcome:** a run can die
  mid-task at the turn ceiling having spent little, or blow past a naive dollar budget in three turns —
  turns and dollars are independent axes. **What actually gets the guarantee:** `--max-budget-usd` for
  dollars, `--max-turns` for runaway loops, set independently. **Why people believe it:** "turns" reads
  as a proxy for "amount of work," and work reads as a proxy for cost.
- **Belief in action:** `--output-format json` guarantees a JSON object on stdout regardless of how the
  call fails. **Surprising outcome:** resuming a non-persisted or unknown session ID printed a bare
  plain-text line and exited `1`, with no JSON object at all, observed directly in this file's §2.
  **What actually gets the guarantee:** parse for "nonzero exit, non-JSON stdout" as its own branch
  before attempting to parse an envelope. **Why people believe it:** every other exit path in this and
  the previous file did honor the flag.
- **Belief in action:** `claude rm <id>` deletes the conversation. **Surprising outcome:** the
  transcript stays on disk and remains reachable through `--resume`; `rm` only removes the background
  management entry. **What actually gets the guarantee:** nothing in this surface deletes a transcript;
  treat `rm` as list hygiene only. **Why people believe it:** `rm` is the universal Unix delete verb.

## Cheat sheet

| Item | Answer |
|---|---|
| Pin a session's UUID | `--session-id <uuid>` |
| Resume a specific session | `--resume <id-or-name>` / `-r` |
| Resume the most recent session in this directory | `--continue` / `-c` |
| Continue but branch into a new identity | `--resume … --fork-session` |
| Never write a transcript at all | `--no-session-persistence` (print mode only) |
| `--resume` ID search scope | Current project + worktrees only before v2.1.223; every project on the machine from v2.1.223 |
| Generate a CI credential | `claude setup-token` — requires a subscription, prints once, never logged |
| Start a local, detachable long-running task | `claude --bg "<task>"` — not combinable with `-p` |
| Check on a background task | `claude attach \| logs \| stop \| respawn \| rm <id>` |
| Diagnose the background supervisor | `claude daemon status` |
| Run on a self-hosted remote environment | `claude -p --environment ccpool_<id>` (v2.1.224+) |
| Dispatch to claude.ai | `claude --cloud "<task>"`; follow up with `-p --cloud <id-or-url>` |
| Pull a web session into this terminal | `claude --teleport` |
| Subagent spend and a budget cap | `--max-budget-usd` counts subagent spend toward the parent's cap (enforcement v2.1.217+) |

## Self-test

1. What does resuming a session actually restore, mechanically — a live model's memory, or something
   else?
<details><summary>Answer</summary>Something else: the persisted transcript. The model itself has no memory between calls; `--resume` re-sends the whole prior transcript as the prefix of the next call. The real run in §2 showed `cache_read_input_tokens` jump by exactly the first call's `cache_creation_input_tokens`, proving the resumed call re-read and re-sent the entire prior context rather than a live process recalling it.</details>

2. Why did resuming a `--no-session-persistence` session fail, and what did the failure output actually look like?
<details><summary>Answer</summary>It failed because nothing was ever written to disk for that session ID to resume — `--no-session-persistence` means there is no transcript. The failure printed a bare plain-text line ("No conversation found with session ID: …") and exited 1, not a JSON object, even though `--output-format json` was passed — the flag governs a completed run's shape, not a pre-flight failure that occurs before a run starts.</details>

3. A wrapper wants to try two different next steps from the same conversation checkpoint without either corrupting the other. Which flag, and why does it need a new session ID rather than reusing the original?
<details><summary>Answer</summary>`--resume <id> --fork-session`. It issues a new UUID because the two continuations must not share one mutable transcript — if both wrote to the same session ID, the second call's turn would be appended after the first's, corrupting whichever branch ran second. A new identity keeps the original checkpoint's session untouched for a second, independent continuation.</details>

4. Why can `--bg` not be combined with `-p`?
<details><summary>Answer</summary>They are two different execution surfaces: `-p` is a synchronous call whose caller blocks for one exit-time result, while `--bg` hands the task to a supervisor process and returns immediately with just a session ID. There is no single call shape that is both "block until the envelope is ready" and "return immediately"; `cli-reference` documents them as mutually exclusive rather than composable.</details>

5. Does `claude rm <id>` delete the conversation? What does it actually do?
<details><summary>Answer</summary>No. It only removes the session from the background-management list (what `claude attach`/`logs`/`stop` can see). The transcript itself stays on disk and remains reachable through `--resume`, exactly as any other session's transcript would be.</details>

6. Why was `claude setup-token` not executed in this file, when the guide otherwise runs what it can?
<details><summary>Answer</summary>Running it prints a real, live OAuth credential to the terminal that invokes it — the one artefact this guide must never place in a transcript, log, or document. The command's documented behavior ("prints the token to the terminal without saving it") is taken from `cli-reference` rather than demonstrated, precisely because demonstrating it would mean leaking a working credential.</details>

7. A background session's log output is fed into a script that `grep`s for a result string, and the match is unreliable. What is actually in that output, and what should the script use instead?
<details><summary>Answer</summary>`claude logs <id>` returns a captured frame of the session's own rendered terminal UI — ANSI escape codes and control sequences included, not a clean line-oriented log — so a result string can be split or altered by those bytes. A wrapper that needs a machine-parseable result should instead resume the session's ID with `-p --resume <id> --output-format json` once it has finished, and read the structured envelope.</details>

## Open questions

- **Unverified:** the exact follow-up dispatch shape for `--cloud <session-id-or-url>` beyond what
  `cli-reference` states was not exercised directly — no claude.ai session was created for this file.
- **Unverified:** `--environment` end-to-end behavior against a real `ccpool_…` self-hosted environment
  was not exercised — no such environment was provisioned in this run's sandbox.

---

**Leaves covered:** 3.6.6–3.6.9 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** none — D-80 in the previous file draws the envelope, and D-81 and D-82 in the next two draw the failure taxonomy and the resolution order
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 423
