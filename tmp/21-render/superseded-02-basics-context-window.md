# 21 AI for Coding — the context window — BASICS (§0.2)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 0 of 6** | [Index](../00-index.md)
Previous: [what the model is](01-basics-what-the-model-is.md) · Next: [the agent loop](03-basics-the-agent-loop.md)

File 01 established that the model is a stateless function: text in, text out, nothing carried
between calls. That immediately raises a question file 01 deliberately left open: if nothing is
carried between calls, how does a multi-turn conversation work at all, and what stops you from
sending it an infinite amount of text? Both questions have the same answer — the **context
window** — and this file is that answer, in full.

### 1. The context window is a hard ceiling on input plus output together

**Mental model.** Picture a single, fixed-size envelope. Every byte of text the model will read for
this call, and every byte of text it is allowed to write back, has to fit inside that one envelope
together. There is no separate envelope for "what you send" and "what it replies" — they share one
box. `[ZERO]`

**Why it exists.** File 01, §2 explained that a model call is one large computation over the entire
input text at once — every token attends to every other token to build the next probability
distribution. That cost grows sharply as input grows, and the hardware has finite working memory. A
model cannot accept "as much text as you like": some fixed cap on the largest input-plus-output one
call can process has to be chosen, and that cap is the context window.

**How it works.** `[ZERO]` `[NUM]` The **context window** is the maximum number of tokens (file
01, §0.1.3: a token is roughly 3–4 characters of English, or about 0.75 words) one request may
contain, counting the input tokens and the output tokens together, not separately. If your input is
199,000 tokens and the window is 200,000, the model has only 1,000 tokens left to write its
response before it is forcibly cut off — a long input directly shrinks how long an answer is even
allowed to be. This is a **hard** limit, not a soft one: `[ZERO]` there is no "the model tries its
best and trims automatically." Either the request fits, or it is rejected before the model ever
runs, or something outside the model has already shortened the conversation before sending it
(covered fully in §3 below). The model itself has no opinion about the limit and no way to negotiate
it — the limit is enforced by the serving infrastructure, before generation starts.

**Current sizes.** `[NUM]` `[RESEARCH]` `[VERSION]` **Re-verified against
`https://code.claude.com/docs/en/model-config` on 2026-08-29**, per this guide's research protocol,
ahead of writing this section. As of Claude Code v2.1.2xx:

- **200K tokens** is the context window for Opus 4.6 and Sonnet 4.6 without extended context, for
  Opus 4.8 and Opus 5 when running in a 200K configuration (for example on Amazon Bedrock, Google
  Cloud's Agent Platform, or Microsoft Foundry), and for any session started with
  `CLAUDE_CODE_DISABLE_1M_CONTEXT=1` set — that environment variable forces every model, including
  ones with a native 1-million-token window, to be treated as 200K for the purpose of the window
  limit and the compaction math in §6 below.
- **1,000,000 tokens** ("1M", the extended-context tier) is available for Fable 5, Sonnet 5, and
  Opus 4.6 and later, either via the `[1m]` suffix on the model name (`claude --model opus[1m]`,
  `/model sonnet[1m]`) or, for **Sonnet 5 specifically, automatically** — the documentation states
  plainly that on the Anthropic API, "Sonnet 5 always runs with the 1M context window," with no
  suffix needed and no separate 200K variant to opt out of.
- **What 1M costs relative to 200K:** the documentation is explicit that the 1M window "uses
  standard model pricing with no premium for tokens beyond 200K" — the window gets larger, the
  per-token price for input and output stays the same. Where cost changes is *access*, not price:
  on a Max, Team, or Enterprise plan, Opus with 1M context is included in the plan; on a Pro plan,
  or for Sonnet 4.6 with 1M on any subscription plan, the 1M window draws on usage credits instead.
  On API and pay-as-you-go billing, 1M context is available in full with no separate gate.

**What happens at the limit.** `[ZERO]` Two different things can happen; name both so neither is
mistaken for the other:

1. **Rejection.** If an assembled request already exceeds the window, the API refuses the call
   outright before generation — no partial answer, no tokens billed for generation.
2. **Compaction.** Long before rejection, Claude Code (the harness, not the model) proactively
   rewrites the conversation smaller — summarizing older turns — so a normal session practically
   never hits case 1. §6 below works the arithmetic; Part 3's §3.2 covers what compaction keeps.

**Pitfall:** the belief in action is assuming the context window only limits *what you can paste
in* — "as long as my prompt is short, I'm fine." The surprising outcome: a short prompt in a long,
already-lengthy session can still fail or get compacted mid-turn, because the window counts
everything already in the conversation plus the new input plus the entire output the model is about
to write — not the new message in isolation. What actually gets the guarantee: tracking the
*running total* of the conversation, not the size of your latest message; §6 below shows exactly why
conversation length, not message length, is the number that matters. `[TRAP]`

**Why people believe it:** the input box in a chat interface visually resembles a single text field
you fill in per turn, which invites treating each message as billed and limited on its own — the
interface gives no visual cue that everything typed and read in every earlier turn is silently
riding along inside the same envelope.

> The context window is the maximum number of tokens — input and output combined — one API request
> may contain; it is enforced as a hard limit by the serving infrastructure, not a soft budget the
> model manages for itself.

### 2. A request is an ordered list of role-tagged messages

**Mental model.** Forget "a conversation" as a vague, free-flowing thing. At the wire level, every
request Claude Code sends is one concrete data structure: an ordered array of **messages**, and
each message carries a **role** telling the model who "said" it. `[ZERO]`

**Why it exists.** The model in file 01 is one function: text in, text out. But a coding assistant
needs the model to distinguish three different kinds of text riding in that one input — standing
instructions that govern the whole session, what the human actually typed, and what the model itself
said in an earlier turn (so it can tell its own prior words apart from the human's). Tagging every
chunk of text with a role is how a single flat text stream carries that distinction.

**How it works.** `[DOC]` A request body sent to the Claude API is a JSON object with a `system`
field (a string of standing instructions — for Claude Code, this is where the tool definitions and
core operating instructions from file 01, §0.1.6 live) and a `messages` array, where every entry has
exactly a `role` (`"user"` or `"assistant"` — the `"system"` role is not a message-array entry in
this API shape, it is the separate top-level `system` field) and a `content` string. Here is the
literal, complete, parseable JSON for a two-turn conversation — one full exchange already finished,
and the user's next message ready to be sent as the *third* entry in the array:

```json
{
  "model": "claude-sonnet-5",
  "max_tokens": 4096,
  "system": "You are Claude Code, an agentic coding assistant. You have access to tools for reading files, running shell commands, and editing code. Ask before running a command that could be destructive.",
  "messages": [
    {
      "role": "user",
      "content": "What does ConversationController.handle do in this repo?"
    },
    {
      "role": "assistant",
      "content": "ConversationController.handle receives the full conversation as its request body on every call and returns the model's next message; it holds no state between requests."
    },
    {
      "role": "user",
      "content": "Does it cache anything between calls?"
    }
  ]
}
```

Every field explained in prose, because JSON takes no comments: `model` picks which model tier
answers this call (file 01, §0.1.5); `max_tokens` caps how many *output* tokens this specific call
may produce, itself bounded by what is left of the shared window after everything above it; `system`
is sent once per request, not once per session — it rides along on every single call, including this
third one; and `messages` is the ordered history, oldest first, ending on the newest `user` entry
that has not yet been answered. Nothing in this object is a pointer, a session ID, or a reference to
something stored server-side — it is the literal text, present in full, every time.

![D-06 — A request is an ordered list of messages](../diagrams/D-06-request-is-ordered-message-array.svg)

**D-06** — A request is an ordered list of messages. Read the index on each slot and the exact role
names — there are exactly two roles inside `messages` (`user`, `assistant`); `system` is a separate
top-level field, not a third role sharing the array.

**Interview:** "What roles appear in a Claude API request, and where does the system prompt live?"
— `user` and `assistant` are the two roles inside the ordered `messages` array; the system prompt is
not a message with a `"system"` role in that array, it is a separate top-level `system` string sent
alongside `messages` on every request.

> A request is a JSON object holding an ordered array of role-tagged messages (`user`,
> `assistant`) plus a separate top-level `system` string — the entire conversation, structured, sent
> as one object on every call.

### 3. The window is the argument list of the next call, not a memory — and why "it forgot" is rarely a bug

**Mental model.** `[ZERO]` Say this exactly: **the context window is not a memory the model writes
to. It is the argument list of the next call.** Nothing is stored inside the model between requests
— section 2's JSON object above is reconstructed and re-sent, in full, every single time, by
software outside the model. The model does not "have" a context window the way a process has a heap
it can allocate into; the window is a property of the *call*, not a property of "the model" as a
standing entity.

**Why it exists.** This is a direct restatement of file 01, §0.1.1: the model is a pure function
with no field, no `this`, nothing held between invocations. If the model cannot hold state, and yet
a session clearly continues across many turns, the only place that continuity can live is in
whatever gets handed to the *next* call as its argument — there is nowhere else for it to be.

**How it works.** Every one of the three messages in section 2's JSON object above is present
because Claude Code's harness kept them and re-sent them, not because the model remembered anything
from the first two turns while idle between calls. Drop the second message from that array before
sending the third call, and the model has no way to know a `ConversationController.handle` question
was ever asked — not "it forgot in the human sense," but literally: that text is not in this call's
argument, so nothing about it exists for this call at all.

`[JAVA]` **The honest analogy.** Write the harness's job as a Spring Boot controller, stripped to
its essential shape:

```java
@RestController
class ConversationController {

    private final ClaudeClient claudeClient;

    ConversationController(ClaudeClient claudeClient) {
        this.claudeClient = claudeClient;
    }

    @PostMapping("/v1/turns")
    ClaudeEnvelope handle(@RequestBody ConversationRequest request) {
        // No field on this class holds request.messages() between calls.
        // Every message this method sees arrived inside THIS request body,
        // supplied in full by the caller — never recovered from anywhere else.
        return claudeClient.call(request.system(), request.messages());
    }
}

record ConversationRequest(String system, List<Message> messages) {}
record Message(String role, String content) {}
```

`handle` is a completely ordinary, stateless `@RestController` method: no instance field caches
`messages` across invocations, and Spring creates no session for this endpoint. The *client* —
Claude Code's harness, in the real system — is the party responsible for remembering the
conversation: it keeps its own growing `List<Message>`, appends the newest exchange, and resends
the entire, growing list as the request body on every subsequent call. `handle` itself is exactly as
memoryless as `respond` was in file 01, §0.1.1.

![D-07 — The window is the argument list of the next call](../diagrams/D-07-window-is-argument-list.svg)

**D-07** — The window is the argument list of the next call, not a memory: the growing `messages`
array lives in the *caller's* state, is rebuilt and resent whole on every request, and nothing
persists inside the handler between calls.

**Precisely where the analogy breaks**, because "it is like a REST controller" alone is not
sufficient:

1. **No session.** A real Spring app often keeps server-side session state (`HttpSession`, a
   database row keyed by a session ID) precisely so the client need not resend everything.
   `ConversationController.handle` has none, because the real Claude API genuinely has none — no
   session object anywhere in Anthropic's infrastructure holds "this conversation" between calls.
2. **No cookie.** A browser carries a session cookie so the server knows which session's state to
   load. No equivalent token exists in a Claude API call saying "this is conversation #4471, resume
   it" — the only way to resume is to resend the full `messages` array. A "resume session" feature
   (Claude Code's own `--resume`) is the *product* replaying your locally stored transcript back into
   `messages`, never the server recognizing a returning session.
3. **No server-side store, ever, for the conversation itself.** A typical stateful `@RestController`
   still has something backing it — Redis, a database — even when `handle` itself is stateless.
   Claude Code's harness keeps the transcript on the **caller's** side purely so it has something to
   resend; the API side never persists "your conversation" in any store independent of resending it.

**Pitfall:** the belief in action is treating a fluent, contextual-sounding reply as proof the model
"has" the conversation somewhere, the way a stateful service has a session — "it clearly still knows
what `ConversationController` is, so it must be holding it." The surprising outcome: the instant the
harness fails to include that earlier text in the next call's `messages` array — trimmed by
compaction, dropped by a bug, or simply never sent because a new session was started — the model has
no access to it at all, with no partial recollection and no way to ask for it back. What actually
gets the guarantee: the text is present, verbatim or summarized, in *this specific call's* `messages`
array. Nothing else. `[TRAP]`

**Why people believe it:** identical to file 01's version of this pitfall — a long, coherent
back-and-forth is exactly what a stateful conversation with a human looks like, and nothing in the
chat UI's presentation distinguishes "the model remembers" from "the harness re-sent it."

**"It forgot" is almost never a bug in the sense people mean.** `[ZERO]` `[TRAP]` When a model
appears to lose track of something it was told earlier in the same working session, there are
exactly two mechanically different causes, and treating them as the same "forgetting" problem leads
to the wrong fix:

- **Never in context at all.** The fact was never included in any `messages` array sent to the
  model — maybe it lived in a file the model never read, or a decision made in a different session
  entirely (a different, separate `messages` array with none of this history in it). The fix is to
  put the missing information in front of the model explicitly — reference the file, restate the
  decision, or write it into `CLAUDE.md` (Part 1) so it loads automatically at the start of every
  session.
- **Compacted out.** The fact *was* in context earlier in this same session, but a compaction pass
  (section 1's case 2, worked in full in Part 3, §3.2) replaced the older turns — including that
  fact — with a shorter summary, and the summary did not preserve it. The fix is different: either
  make the fact durable (write it to a file or to memory, per Part 1, so a summary cannot drop it)
  or re-state it after compaction rather than assuming it survived.

**Pitfall:** the belief in action is diagnosing every "it forgot" moment as a single, generic model
failure and responding by simply repeating yourself harder or switching models — "the model must be
getting worse, let me try Opus instead." The surprising outcome: if the cause was compaction, a
bigger or "smarter" model has exactly the same blind spot, because the fact is not present in either
model's input at all — no amount of capability recovers information that was never sent. What
actually gets the guarantee: check which of the two causes applies (was it ever sent, or was it
dropped by a summary) before choosing a fix, because "never in context" and "compacted out" call for
different repairs, and only one of them is helped by putting the information in a file that loads
automatically. `[TRAP]`

**Why people believe it:** "forgot" is a single, undifferentiated word borrowed from how humans
describe memory lapses, and it papers over two structurally different, independently diagnosable
failures — whether the information ever entered the argument list, and whether it was later
summarized away.

> The context window is the argument list of the next call, not a memory the model writes to or
> reads from between calls; "it forgot" means either the fact was never in that argument list, or an
> earlier version of the argument list containing it was replaced by a shorter summary — two
> different diagnoses with two different fixes.

### 4. Cost and latency scale with conversation length, not with your last message

**Mental model.** `[ZERO]` Because section 3 established that the *entire* conversation rides along
on every single call, a "quick one-line question" late in a long session is not a quick, cheap
request — it is the full transcript, plus one line, sent and (mostly) reprocessed all over again.

**Why it exists.** This is the direct, unavoidable arithmetic consequence of sections 2 and 3: if
every call resends everything before it, the size of call *N* is roughly the size of call *N − 1*
plus whatever was newly added — so the total amount of text processed across a whole session grows
with every turn added, not just with how much any single turn contains.

**How it works, with the arithmetic printed rather than asserted.** `[PROVE]` `[NUM]` Assume, for
a concrete illustration, a session that starts with 6,000 tokens already in play (the startup
content worked out fully in §6 below) and that each subsequent turn — a user message, the model's
reply, and any tool results in between — adds roughly 800 tokens to the running conversation before
the next call goes out. Call *i*'s input size is then `6,000 + 800 × i` tokens, and the **total**
tokens processed across the whole session is the sum of every call's input, from the first turn to
the last:

| Session length | Per-turn cost formula | Sum across all turns | Total tokens processed |
|---|---|---|---|
| 10 turns | `Σ (6,000 + 800·i)` for `i = 1..10` | `10 × 6,000 + 800 × (1+2+…+10)` | `60,000 + 800 × 55 = 104,000` |
| 100 turns | `Σ (6,000 + 800·i)` for `i = 1..100` | `100 × 6,000 + 800 × (1+2+…+100)` | `600,000 + 800 × 5,050 = 4,640,000` |

The 100-turn session has **10×** as many turns as the 10-turn session, but it processes
`4,640,000 ÷ 104,000 ≈ 44.6×` as many total tokens — not 10×. This is the arithmetic behind
"cost and latency scale with conversation length": because every call resends everything before it,
total token volume grows roughly with the *square* of the number of turns, not linearly with it,
long before any single message got longer. A one-line question at turn 100 is billed (mostly, before
prompt caching's discount — §5 below) against the whole 80,000-token history it drags along, not
against the one line it added.

![D-08 — Cost scales with conversation length](../diagrams/D-08-cost-scales-with-length.svg)

**D-08** — Cost scales with conversation length: as turns accumulate, each call resends the growing
total, so cumulative tokens processed grows faster than the turn count itself.

**Insight:** this is why "just clear old context" (`/clear`, and compaction, §1) is not a
housekeeping nicety — it is the single highest-leverage lever over cost and latency in a long
session, because it resets the base every subsequent call must re-carry.

> Because every call resends the full conversation so far, total tokens processed across a session
> grows with the *sum* of every prior turn's size, not with the length of the newest message — a
> long session's cost and latency are dominated by how long it has run, not by what you just typed.

### 5. Prompt caching: why appending is cheap and editing the beginning is not

**Mental model.** `[ZERO]` Section 4's arithmetic looks alarming until one more mechanism is added:
the API does not actually *recompute* the unchanged part of a request from scratch on every call —
it can reuse work it already did, provided the unchanged part is at the *front* of the request and
matches exactly.

**Why it exists.** Section 2 showed a request is one ordered array with new content appended at the
end. On any normal turn, everything before the newest exchange is byte-for-byte identical to what
was already sent on the previous call. Recomputing that identical prefix from zero, every single
turn, would be pure waste — the fix is to let the serving infrastructure remember that prefix's
already-computed internal state and skip straight to processing only what is new.

**How it works.** `[NUM]` `[RESEARCH]` **Re-verified against
`https://code.claude.com/docs/en/prompt-caching` on 2026-08-29.** The API matches the **start** of
each request — the **prefix** — against content it recently processed for that same model. The
match is exact: change anything anywhere in that prefix and everything after the change point has to
be recomputed, because the cached copy no longer matches. Claude Code deliberately orders each
request so the parts that change least sit first — system prompt, then project context (`CLAUDE.md`,
memory), then the growing conversation last — precisely so that ordinary turns, which only append,
keep the entire front of the request cache-eligible. A **cache read** — reusing an already-processed
prefix — is billed at roughly **10% of the standard input token rate**, per the documentation's own
description of the `cache_read_input_tokens` field ("billed at roughly 10% of the standard input
rate"); a **cache write** — the first time a given prefix is processed and stored for later reuse —
costs *more* than a normal input token, not less, which is the trade a cache is always making: pay a
premium once, so that every subsequent hit is nearly free.

This is why "appending is cheap and editing the beginning is not" is literally true, not a rough
guideline: appending never disturbs the prefix, so existing history still reads from cache at the
10% rate and only the new tail bills at full price. Editing anything earlier — the system prompt, the
loaded tool set, `CLAUDE.md` mid-session — breaks the exact-match prefix there, so everything
downstream, including conversation the developer never touched, is reprocessed at full input price.

![D-09 — Prompt caching: the unchanged prefix](../diagrams/D-09-prompt-caching-prefix.svg)

**D-09** — Prompt caching: turns two and three read the unchanged prefix from cache and pay only
for what is new; turn four changes the system prompt, breaking the prefix match, so the entire
request is reprocessed and rewritten to cache from scratch.

**Cache lifetime.** `[NUM]` `[DOC]` **Re-verified against the same page.** A cached prefix expires
after a period of inactivity, and each request that hits the cache resets that timer. The API
"offers two: a five-minute TTL, and a one-hour TTL." Claude Code's default depends on billing: on a
Claude subscription within plan usage, the **main conversation** defaults to **one hour**; once a
session draws on usage credits, or on an API key or cloud-provider connection, that drops to **five
minutes**. Requests **outside** the main conversation — subagents, workflows, in-process teammates,
forks, compaction, session titles — default to **five minutes** regardless of billing, "except the
server-controlled helper requests, which get one hour." Two settings override these, each accepting
only `5m` or `1h`: **`promptCacheTtl`** for the main conversation, **`subagentPromptCacheTtl`** for
everything else — both require v2.1.242+, and both also have an environment-variable form
(`CLAUDE_CODE_PROMPT_CACHE_TTL`, `CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL`).

**Why a pause past the TTL costs real money.** Step away from a session on a five-minute-TTL
connection for six minutes, and the cached prefix has already expired by the time the next message
goes out. That next call reprocesses the entire conversation history as fresh, uncached input — at
full price, not the 10% cache-read rate — before a new cache entry is written. The longer the
session had grown before the pause (§4's arithmetic), the more expensive that single reprocessing
call is; a six-minute coffee break mid-session can cost more, in that one request, than the rest of
the session combined.

**Interview:** "Why does switching models mid-session make the next response slower and more
expensive?" — Each model has its own separate cache, so a `/model` switch means the very next
request matches no cached prefix at all and reprocesses the entire conversation from scratch at full
input price, even though none of the actual text changed; the same is true of switching effort
level, since the cache is keyed by both model and effort together.

> Prompt caching lets the API reuse an unchanged prefix instead of recomputing it: a cache read costs
> roughly 10% of standard input pricing, so appending to a conversation stays cheap while editing
> anything earlier in it — or letting the cache go cold past its TTL (one hour or five minutes,
> `promptCacheTtl` / `subagentPromptCacheTtl`) — forces a full-price reprocessing of everything after
> the change.

### 6. The 200K budget, itemised: what is left for actual work

**Mental model.** `[ZERO]` Take the number everyone quotes — "200K context window" — and actually
spend it, line by line, the way you would read a budget rather than a headline figure.

**Why it exists.** Sections 1–5 all lean on one implicit fact this section makes explicit: the
200,000-token number is not 200,000 tokens of room for *your* work. A meaningful amount is already
spoken for before a task is typed, and knowing how much is the difference between "the window feels
enormous" and "it ran out sooner than it should have."

**How it works, with the arithmetic printed.** `[PROVE]` `[NUM]` `[DOC]` Documented per-item figures
for what loads automatically into a fresh session, before the first user message, from
`https://code.claude.com/docs/en/context-window`:

| Loaded automatically | Tokens |
|---|---|
| System prompt (core instructions, tool definitions, output formatting) | 4,200 |
| Auto memory (`MEMORY.md`, capped at the first 200 lines or 25 KB) | 680 |
| Environment info (working directory, platform, shell, OS, git snapshot) | 280 |
| MCP tool names (schemas deferred by default; only names load upfront) | 120 |
| Skill listing (one-line descriptions of invocable skills) | 450 |
| **Startup total, before you type anything** | **5,730** |

`200,000 − 5,730 = 194,270` tokens remain after startup content alone, on a fresh session with a
200K window, before compaction is even considered.

Compaction narrows that further. The documentation's own worked figure for Sonnet 5's 1M window
states it "auto-compacts at ~967K tokens by default" — that is, compaction fires at
`967,000 ÷ 1,000,000 ≈ 96.7%` of that window, reserving roughly 3.3% as headroom rather than letting
the conversation run all the way to the hard ceiling. **Unverified:** the documentation does not
publish an equally explicit percentage for the 200K-window case — it states only that a 200K model's
default compaction point is "the 200K boundary," without a numeric reserve stated for that
configuration the way it is for Sonnet 5's 1M window. Applying the 1M case's ~96.7% ratio to 200K as
an *illustrative* extrapolation — not a documented figure — gives `200,000 × 0.967 ≈ 193,400` tokens
as roughly where compaction would fire, leaving about 6,600 tokens of headroom before the hard
ceiling. This extrapolated 200K percentage is recorded in `## Open questions` below rather than
stated as fact.

Combining the documented startup cost with that illustrative compaction point: `193,400 − 5,730 ≈
187,670` tokens are what remain, in a fresh 200K session, for the actual conversation — your prompts,
every file read, every tool result, every reply — before Claude Code proactively starts compacting to
keep the session inside the window at all. `autoCompactWindow` (Part 1 covers its full settings
surface) lets a developer raise or lower that trigger point explicitly, in either direction, rather
than accepting the model's default.

![D-10 — The 200K budget itemised](../diagrams/D-10-200k-budget-itemised.svg)

**D-10** — The 200K budget itemised: startup content, the compaction reserve, and what remains for
actual work, drawn to scale against the full 200,000-token window.

**The five things that consume the window before you type anything**, named here and given their
full treatment in **§3.1**, forward-referenced rather than duplicated: the **system prompt** (core
instructions and tool definitions), **tool schemas** (MCP tool listings, deferred by default so only
names load upfront), **memory files** (`CLAUDE.md` and auto memory), the **skill listing** (one-line
descriptions of invocable skills), and the **environment/git snapshot** (working directory, platform,
shell, OS, branch, recent commits). §3.1 covers exactly when each one loads, what triggers it to grow
mid-session, and what does or does not survive a compaction pass.

**Interview:** "Is a 200K context window actually 200,000 tokens of usable space for my task?" — No:
roughly 5,700 tokens load automatically before any user input at all, and Claude Code proactively
compacts well before the true 200,000-token ceiling to keep headroom in reserve, so the realistic
usable budget for a fresh session's actual conversation is closer to the mid-180,000s than to
200,000 — and it shrinks further as MCP servers, larger memory files, or more skills are added to a
project.

> The 200,000-token window is a starting figure, not a working budget: roughly 5,700 tokens are
> already spent on startup content before you type anything, and Claude Code reserves further
> headroom by compacting before the hard ceiling — so the number worth tracking is what remains
> after both deductions, not the headline 200K.

---

## Pitfalls

| Wrong belief in action | Surprising outcome | What actually gets the guarantee | Why people believe it |
|---|---|---|---|
| "As long as my prompt is short, I'm within the limit." | A short message late in an already-long session can still trigger rejection or compaction. | Track the running total of the whole conversation, not the size of the newest message. | The input box looks like one message is billed and limited on its own; nothing shows the silent history riding along. |
| "It clearly still knows about `ConversationController`, so it must be holding that in memory somewhere." | The instant that text is missing from the next call's `messages` array, all access to it disappears, with no partial recall. | The text is present, verbatim or summarized, in *this specific call's* input — nothing else. | A long, coherent exchange looks exactly like a human conversation with real memory behind it. |
| "It forgot, so the model (or a bigger model) must fix it." | If the cause was compaction, a more capable model has the identical blind spot, because the fact isn't in either model's input at all. | Diagnose which of the two causes applies — never sent, or summarized away — before choosing a fix. | "Forgot" is one word borrowed from human memory lapses, covering two structurally different, separately fixable failures. |

## Cheat sheet

| Concept | The one line |
|---|---|
| Context window | Max tokens per request, input + output together; a hard limit enforced before generation, not a soft budget. |
| Current sizes (Aug 2026) | 200K standard; 1M extended-context (Sonnet 5 automatically, others via `[1m]`), same per-token price beyond 200K. |
| Request shape | JSON object: top-level `system` string + ordered `messages` array of `{role, content}`, roles `user`/`assistant` only. |
| The window is | The argument list of the next call — never a memory the model writes to or reads from between calls. |
| "It forgot" | Two causes only: never in context at all, or compacted out of a summary — different fixes for each. |
| Cost/latency scaling | Scales with total conversation length (roughly the *sum* of every prior turn), not with the newest message's length. |
| Prompt caching | Unchanged prefix reused at ~10% of input price; editing anything before the tail, or letting the cache go cold, forces full-price reprocessing. |
| Cache TTL | One hour (main conversation, subscription, within plan usage) or five minutes (everything else, or non-subscription billing); `promptCacheTtl` / `subagentPromptCacheTtl` override. |
| 200K budget | ~5,730 tokens gone at startup; compaction reserves further headroom before the hard ceiling — usable budget is well under 200,000. |
| Five startup consumers | System prompt, tool schemas, memory files, skill listing, environment/git snapshot — full treatment in §3.1. |

## Self-test

1. Why does the context window limit the length of the model's *response*, not just what you can
   send it?
<details><summary>Answer</summary>
Because the window is a single shared ceiling on input and output tokens together, not two separate
budgets. If the input already uses most of the window, only whatever is left can be spent on the
output — a very long input directly shrinks the maximum length the response is even allowed to
reach.
</details>

2. What is a context window, and why is the whole conversation re-sent every turn?
<details><summary>Answer</summary>
The context window is the maximum number of tokens — input and output combined — one request may
contain; it is a hard limit enforced by the serving infrastructure before generation starts. The
whole conversation is re-sent every turn because the window is the argument list of the next call,
not a memory the model writes to: the model is a stateless function (file 01) with no field carrying
state between calls, so the only place continuity can live is in what gets handed to it as input on
the very next call, in full, every time.
</details>

3. In the Claude API request shape, what roles exist inside the `messages` array, and where does the
system prompt actually live?
<details><summary>Answer</summary>
Only two roles appear inside `messages`: `user` and `assistant`. The system prompt is not a third
role sharing that array — it is a separate top-level `system` string sent alongside `messages` on
every request.
</details>

4. A 100-turn session has 10× as many turns as a 10-turn session. Roughly how many times more total
tokens does it process, and why isn't the answer simply 10×?
<details><summary>Answer</summary>
Using the worked example (6,000-token base, 800 tokens added per turn), the 10-turn session
processes 104,000 total tokens and the 100-turn session processes 4,640,000 — about 44.6×, not 10×.
The answer isn't 10× because every call resends the entire conversation so far, so the total volume
processed across a session is the *sum* of every prior turn's growing size, which grows faster than
the turn count itself.
</details>

5. Why is editing the very first part of a long conversation far more expensive than appending a new
message to the end of it?
<details><summary>Answer</summary>
Prompt caching matches the exact prefix of a request against what was cached from the previous call.
Appending only adds new content after that prefix, so the entire earlier history still hits the
cache at roughly 10% of standard input pricing. Editing anything earlier — the system prompt,
`CLAUDE.md`, the loaded tool set — breaks the exact match at that point, forcing everything after
the edit, including conversation the developer never touched, to be reprocessed and rebilled at full
input price.
</details>

6. What are the two default cache TTLs, and which one applies to a subagent's requests?
<details><summary>Answer</summary>
One hour and five minutes. A subagent's requests fall outside the "main conversation" bucket, so they
default to five minutes regardless of billing — even on a subscription where the main conversation
itself would default to one hour — unless `subagentPromptCacheTtl` is set to request the longer TTL
explicitly.
</details>

7. Roughly how many tokens of a fresh 200K session are already spent before the first user message,
and what accounts for it?
<details><summary>Answer</summary>
Roughly 5,730 tokens: the system prompt (~4,200), auto memory (~680), environment info (~280), MCP
tool names deferred (~120), and the skill listing (~450). None of it is optional content the
developer typed — all five load automatically at session start.
</details>

8. A developer says "it forgot the decision we made an hour ago in this same session — the model
must be getting worse." What two causes should be checked before concluding that, and why does it
matter which one it was?
<details><summary>Answer</summary>
Either the decision was never actually included in any `messages` array sent to the model (never in
context at all — perhaps it lived only in the developer's head or in a file never read), or it was
in context earlier but a compaction pass replaced that portion of history with a summary that didn't
preserve it (compacted out). It matters because the fixes differ: "never in context" is fixed by
explicitly supplying the missing information (or writing it into `CLAUDE.md` so it loads
automatically); "compacted out" is fixed by making the fact durable in a file, or restating it after
compaction — switching to a more capable model fixes neither, since the fact is absent from either
model's input either way.
</details>

9. Why does switching effort level mid-session cost the same kind of penalty as switching models?
<details><summary>Answer</summary>
Because the prompt cache is keyed by both model and effort level together, not by model alone. A
request at a different effort level matches no cached prefix even if every character of the
conversation is identical, so the very next request after an effort change reprocesses the full
history at full input price before a new cache entry is established.
</details>

10. What does `CLAUDE_CODE_DISABLE_1M_CONTEXT=1` actually do, and to which models does it apply?
<details><summary>Answer</summary>
It forces every model — including ones with a native 1-million-token window such as Sonnet 5 or
Fable 5 — to be treated as having a 200K window, both for the hard limit and for the compaction
math that decides when Claude Code proactively summarizes the conversation.
</details>

## Open questions

**Unverified:** the exact ~96.7% compaction-trigger ratio for a **200K**-window session (used in §6
to derive the ~193,400-token figure and the ~187,670-tokens-remaining figure) is an extrapolation
from the *documented* Sonnet 5 figure for its 1M window ("auto-compacts at ~967K tokens by default"),
not a directly documented percentage for the 200K case. `https://code.claude.com/docs/en/context-window`
and `https://code.claude.com/docs/en/settings-reference` describe the 200K default only as compacting
at "the 200K boundary," without stating an explicit numeric reserve the way the 1M case states one.
The direction of the claim — that some headroom is reserved before the hard ceiling, and it is not
100% of the window — is not in question; the precise 200K reserve figure could not be confirmed and
may differ from the illustrative ~6,600-token reserve used above.

---

**Leaves covered:** 0.2.1–0.2.12 (12 leaves)
**Leaves deferred:** none
**Diagrams included:** D-06, D-07, D-08, D-09, D-10
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 600
