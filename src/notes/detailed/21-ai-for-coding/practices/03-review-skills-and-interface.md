# 21 AI for Coding — the review skills and the interface — INTERMEDIATE (§2.7.9–2.7.12)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 2 of 6** | [Index](../00-index.md)
Previous: [prompting and giving the agent what it needs](02-prompting-and-context.md) · Next: [script or prompt: the central judgment](../deterministic-vs-agentic/01-the-central-judgment.md)

**A scope note before the content.** The manifest names this file "the bundled review skills, and the
interface," carried over from when `/code-review` and `/security-review` were planned for this slot.
Your leaf file (`prac-03`) does not contain that material — those two skills were already covered, and
their bundled-skill status already verified, in the previous file's self-test (Q9). Leaf-file text wins
over manifest summary per the standing contract, so this file instead covers what §2.7.9–2.7.12 actually
say: where handing work to an agent is the wrong call, one worked Java example end to end, `statusLine`,
and keybindings. The header and neighbor links stay as specified; the content follows the leaves.

## 1. Where an agent is a bad fit

**Mental model.** Every practice in this area — plan mode, test-first, small tasks, precise prompts —
is about raising the odds that delegating a task goes well. This one is about the prior question:
should you delegate it at all. Some tasks are shaped so that delegating costs more than it saves, no
matter how well you apply the other four practices.

**Why it exists.** An agent's floor cost is not zero. Writing the prompt, watching the diff, running
the verification, and re-reading the result all take wall-clock time and tokens even when the change is
trivial. That floor is fixed per delegation; it does not shrink for a small task the way the model's
own output does.

**Three shapes where the floor cost loses:**

| Shape | Why the agent loses | What to do instead |
|---|---|---|
| A one-line change you already understand | You already hold the diagnosis and the fix in your head; writing a prompt that conveys both takes longer than typing the line | Type the line |
| Anything needing taste you cannot express in words | A prompt is the only channel; if you cannot state the acceptance criterion, the agent cannot converge on it, and neither can a test (§2.7.2) | Do it yourself, or do a partial pass and hand the mechanical remainder to the agent |
| Anything whose verification costs more than doing the work | If checking the agent's diff carefully takes as long as writing the diff by hand, delegation bought nothing — see the review-cost trade in §2.7.1 (plan mode) applied one level down | Do it yourself; save delegation for tasks where verification is cheap relative to authorship |

**How it works.** All three shapes share one mechanism: the agent has no notion of your fixed cost of
context-switching or of implicit taste. It will happily produce a diff for a one-line fix, and the diff
will very likely be correct — the failure is not in the model's output, it is in the arithmetic of
whether asking was worth it.

**Gotcha:** the "verification costs more than the work" case is easy to miss because it is invisible
until you actually try to review the diff. A five-line change to a hot-path concurrency primitive can
cost you twenty minutes of careful reading that a five-line change to a logging statement would not —
the diff size tells you nothing about the review cost.

**Interview:** "when would you *not* use an agent for a coding task?" — name a task where you already
hold the fix, one where the acceptance criterion is unspeakable, and one where reviewing the diff costs
more than writing it yourself; all three are about the fixed cost of delegation exceeding the cost it
replaces, not about the model's competence.

> Delegate when the fixed cost of prompting, watching and verifying is smaller than the cost of doing
> the work yourself — not by default.

## 2. A worked Java example end to end `[JAVA]` `[PROVE]`

**Task:** add an idempotency key to a Spring Boot order-creation endpoint, so that a client retrying a
timed-out `POST` does not create two orders. This section runs the whole loop — plan, failing test,
implementation, review — and then shows two places the agent's first draft was wrong and the exact test
that caught each one, applying the test-first discipline from §2.7.2 without re-deriving it.

**Plan** (per the four-part prompt shape from §2.7.5): goal — a repeated `POST /api/orders` with the
same `Idempotency-Key` header and body returns the original response and creates no second row; the
same key with a *different* body is rejected with `409 Conflict`; constraint — correctness must hold
under concurrent retries, not just sequential ones; done-condition — three tests below all pass; output
location — `OrderController`, `IdempotencyService`, `IdempotencyRecord`, and their tests, nothing else.

**Failing tests first:**

```java
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@AutoConfigureMockMvc
class OrderControllerIdempotencyTest {

    @Autowired MockMvc mockMvc;
    @Autowired OrderRepository orderRepository;

    @Test
    void sameKeyAndBodyCreatesExactlyOneOrder() throws Exception {
        String body = """
                {"sku":"SKU-4471","quantity":2,"customerId":"CUST-1029"}""";

        MvcResult first = mockMvc.perform(post("/api/orders")
                        .header("Idempotency-Key", "a1e6-retry-001")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isCreated())
                .andReturn();

        MvcResult second = mockMvc.perform(post("/api/orders")
                        .header("Idempotency-Key", "a1e6-retry-001")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isCreated())
                .andReturn();

        assertThat(second.getResponse().getContentAsString())
                .isEqualTo(first.getResponse().getContentAsString());
        assertThat(orderRepository.count()).isEqualTo(1);
    }

    @Test
    void sameKeyDifferentBodyIsRejected() throws Exception {
        mockMvc.perform(post("/api/orders")
                        .header("Idempotency-Key", "a1e6-retry-002")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""{"sku":"SKU-4471","quantity":2,"customerId":"CUST-1029"}"""))
                .andExpect(status().isCreated());

        mockMvc.perform(post("/api/orders")
                        .header("Idempotency-Key", "a1e6-retry-002")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""{"sku":"SKU-4471","quantity":5,"customerId":"CUST-1029"}"""))
                .andExpect(status().isConflict());
    }

    @Test
    void concurrentRequestsWithSameKeyCreateExactlyOneOrder() throws Exception {
        String body = """
                {"sku":"SKU-9902","quantity":1,"customerId":"CUST-2231"}""";
        int threads = 8;
        ExecutorService pool = Executors.newFixedThreadPool(threads);
        CountDownLatch ready = new CountDownLatch(threads);
        CountDownLatch go = new CountDownLatch(1);
        List<Future<Integer>> results = new ArrayList<>();
        for (int i = 0; i < threads; i++) {
            results.add(pool.submit(() -> {
                ready.countDown();
                go.await();
                return mockMvc.perform(post("/api/orders")
                                .header("Idempotency-Key", "a1e6-race-003")
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(body))
                        .andReturn().getResponse().getStatus();
            }));
        }
        ready.await();
        go.countDown();
        pool.shutdown();
        for (Future<Integer> result : results) {
            assertThat(result.get()).isIn(200, 201);
        }
        assertThat(orderRepository.count()).isEqualTo(1);
    }
}
```

**Mistake #1 — no body-hash check.** The agent's first `IdempotencyService` checked only whether the
key had been seen before, and if so replayed the stored response unconditionally:

```java
Optional<IdempotencyRecord> existing = repository.findByIdempotencyKey(idempotencyKey);
if (existing.isPresent()) {
    return ResponseEntity.status(existing.get().getResponseStatus())
            .body(fromJson(existing.get().getResponseBody(), responseType));
}
```

`sameKeyDifferentBodyIsRejected` caught it immediately: the second call reused key
`a1e6-retry-002` with `quantity` changed from `2` to `5`, and the assertion expected `409` but the
service returned the cached `201` from the first call — a client reusing a key by accident (a common
bug in retry libraries that key on URL rather than on a fresh UUID per attempt) would have silently
gotten the wrong order confirmed back. The fix hashes the request body and compares hashes before
replaying, throwing `IdempotencyKeyReusedException` on a mismatch.

**Mistake #2 — no protection against a concurrent race.** The corrected code still read
`findByIdempotencyKey`, saw nothing, and inserted — with no database constraint stopping two threads
from both passing that read at the same time. `concurrentRequestsWithSameKeyCreateExactlyOneOrder`
caught it non-deterministically: across a handful of runs, `orderRepository.count()` came back as `2`
on some runs and `1` on others, because whichever of the eight threads happened to interleave its read
before the other's write won a duplicate insert — exactly the failure mode a sequential test can never
see. Sequential tests (the first two above) passed every time; only the concurrent one exposed it,
which is why `[STAFF]` review checklists for anything idempotency-shaped require a concurrency test,
not just a repeat-call test.

**Corrected, final implementation:**

```java
@Entity
@Table(name = "idempotency_records",
        uniqueConstraints = @UniqueConstraint(columnNames = "idempotency_key"))
public class IdempotencyRecord {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "idempotency_key", nullable = false, unique = true)
    private String idempotencyKey;

    @Column(name = "request_body_hash", nullable = false)
    private String requestBodyHash;

    @Column(name = "response_body", nullable = false, columnDefinition = "TEXT")
    private String responseBody;

    @Column(name = "response_status", nullable = false)
    private int responseStatus;

    protected IdempotencyRecord() {
        // required by JPA
    }

    public IdempotencyRecord(String idempotencyKey, String requestBodyHash,
            String responseBody, int responseStatus) {
        this.idempotencyKey = idempotencyKey;
        this.requestBodyHash = requestBodyHash;
        this.responseBody = responseBody;
        this.responseStatus = responseStatus;
    }

    public String getIdempotencyKey() { return idempotencyKey; }
    public String getRequestBodyHash() { return requestBodyHash; }
    public String getResponseBody() { return responseBody; }
    public int getResponseStatus() { return responseStatus; }
}

@Service
public class IdempotencyService {

    private final IdempotencyRecordRepository repository;
    private final ObjectMapper objectMapper;

    public IdempotencyService(IdempotencyRecordRepository repository, ObjectMapper objectMapper) {
        this.repository = repository;
        this.objectMapper = objectMapper;
    }

    @Transactional
    public <T> ResponseEntity<T> executeIdempotently(String idempotencyKey, Object requestBody,
            Class<T> responseType, Supplier<ResponseEntity<T>> action) {
        String bodyHash = sha256(toJson(requestBody));
        Optional<IdempotencyRecord> existing = repository.findByIdempotencyKey(idempotencyKey);
        if (existing.isPresent()) {
            return replay(existing.get(), bodyHash, responseType);
        }
        ResponseEntity<T> response = action.get();
        IdempotencyRecord record = new IdempotencyRecord(idempotencyKey, bodyHash,
                toJson(response.getBody()), response.getStatusCode().value());
        try {
            repository.saveAndFlush(record);
        } catch (DataIntegrityViolationException lostRace) {
            return replay(repository.findByIdempotencyKey(idempotencyKey)
                    .orElseThrow(() -> lostRace), bodyHash, responseType);
        }
        return response;
    }

    private <T> ResponseEntity<T> replay(IdempotencyRecord record, String bodyHash, Class<T> responseType) {
        if (!record.getRequestBodyHash().equals(bodyHash)) {
            throw new IdempotencyKeyReusedException(record.getIdempotencyKey());
        }
        return ResponseEntity.status(record.getResponseStatus())
                .body(fromJson(record.getResponseBody(), responseType));
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("Could not serialize idempotency payload", e);
        }
    }

    private <T> T fromJson(String json, Class<T> type) {
        try {
            return objectMapper.readValue(json, type);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("Could not deserialize idempotency payload", e);
        }
    }

    private String sha256(String value) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(digest);
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 unavailable", e);
        }
    }
}

@RestController
@RequestMapping("/api/orders")
public class OrderController {

    private final IdempotencyService idempotencyService;
    private final OrderService orderService;

    public OrderController(IdempotencyService idempotencyService, OrderService orderService) {
        this.idempotencyService = idempotencyService;
        this.orderService = orderService;
    }

    @PostMapping
    public ResponseEntity<OrderResponse> createOrder(
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @RequestBody CreateOrderRequest request) {
        return idempotencyService.executeIdempotently(
                idempotencyKey,
                request,
                OrderResponse.class,
                () -> ResponseEntity.status(HttpStatus.CREATED).body(orderService.placeOrder(request)));
    }
}
```

The `@UniqueConstraint(columnNames = "idempotency_key")` is what turns the race from silent duplication
into a caught `DataIntegrityViolationException` — the database enforces the guarantee the Java-level
`if (existing.isPresent())` check could not, because two transactions can both evaluate that check as
false before either commits.

**Review.** Running `/code-review` (bundled skill, established in §2.7.6) over this diff against the
sdlc-harness `code-review.yaml` rubric's concurrency-correctness criterion — already quoted in the
previous file — is the fresh-context pass that should have caught mistake #2 before the concurrent test
ran; the test is what actually proved it, which is the point of test-first: a review is an opinion,
`orderRepository.count()` after eight parallel threads is a fact.

**No SVG for this leaf:** the manifest assigns this row no diagram; see D-64 (`practices/01`) for plan
mode and D-41 (`skills/06`) for the mechanism decision tree if either is the picture you actually need.

## 3. `statusLine` and `subagentStatusLine`: cheap situational awareness `[DOC]` `[BUILD]`

**Mental model.** Everything else in this Part has been about a cost that accrues silently — tokens
spent on tone that does nothing (§2.7.6), context that stays resident until compaction (§2.7.7),
effort level chosen once and forgotten (§0.2.6, prior file). `statusLine` is the one place you can make
that invisible number visible without breaking flow: instead of running `/context` to find out where
you stand, the number is rendered on every prompt, for free, because you already asked for the render.

**Why it exists.** The **settings-reference** page documents it plainly:

> `statusLine` — Run your own command to render a status line below the prompt. Topic: Interface and
> terminal. Scope: any settings file.

The mechanism behind that one-line description — the exact JSON shape the setting takes — is not
expanded on the fetched settings-reference page itself; that shape was confirmed instead against the
installed v2.1.251 binary's own settings validator, which is stated here rather than implied as a page
citation:

```
statusLine: {
  type: "command",          // literal "command" — the only supported type
  command: string,          // required — the shell command to run
  padding: number,          // optional
  refreshInterval: number,  // optional, minimum 1 — "re-run the status line command
                             // every N seconds in addition to event-driven updates"
  hideVimModeIndicator: boolean  // optional
}
```

`subagentStatusLine` — "custom per-subagent status line shown in the agent panel; receives row context
as JSON on stdin" per the same binary inspection — takes only `{ type: "command", command: string }`;
no `padding` or `refreshInterval`, because it renders once per row update in the task panel rather than
on a fixed clock.

**How it works.** The command is invoked with a JSON object on stdin. The v2.1.251 binary's own
object-construction code confirms, among other fields, `model`, `cost.total_cost_usd`,
`context_window`, `exceeds_200k_tokens`, `effort.level`, and `thinking.enabled` are all present on that
object — this is the same underlying accounting `/context` and `/cost` read, just delivered on every
render instead of on request. **Unverified:** whether `context_window` on the stdin payload carries a
raw token count or a percentage was not resolvable from the extracted binary strings alone; the script
below treats it as a raw number and prints it unlabeled rather than guessing a unit.

**`[BUILD]`** — a working `statusLine`, wired into a real settings file:

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "statusLine": {
    "type": "command",
    "command": "~/.claude/scripts/cost-and-context-statusline.sh",
    "padding": 0,
    "refreshInterval": 5
  }
}
```

```bash
#!/usr/bin/env bash
set -euo pipefail
trap 'printf "statusline: error rendering, see --debug\n"; exit 0' ERR

payload="$(cat)"

model=$(jq -r '.model.display_name // .model.id // "unknown-model"' <<<"$payload")
effort=$(jq -r '.effort.level // "default"' <<<"$payload")
cost=$(jq -r '.cost.total_cost_usd // 0' <<<"$payload")
context=$(jq -r '.context_window // 0' <<<"$payload")
exceeds=$(jq -r '.exceeds_200k_tokens // false' <<<"$payload")

flag=""
if [ "$exceeds" = "true" ]; then
  flag=" [OVER 200K]"
fi

printf '%s · effort:%s · $%.4f · ctx %s%s\n' "$model" "$effort" "$cost" "$context" "$flag"
```

The failure posture matters here specifically because a status line runs on every render: `set -euo
pipefail` catches a bad `jq` invocation immediately, and the `trap ... ERR` converts any failure into
one harmless printed line and `exit 0` rather than a stack trace flashing under every prompt — a
`statusLine` command is not something you want to fail loudly forty times a minute.

**Prove step** — running the script exactly as the harness would invoke it, piping a representative
payload on stdin:

```
$ echo '{"model":{"display_name":"Claude Opus 5"},"effort":{"level":"high"},"cost":{"total_cost_usd":1.3842},"context_window":142000,"exceeds_200k_tokens":false}' \
    | ~/.claude/scripts/cost-and-context-statusline.sh
Claude Opus 5 · effort:high · $1.3842 · ctx 142000
```

That line was produced by actually executing the script above with that payload, not composed by hand.

**What this costs:** `refreshInterval: 5` means the harness re-runs this script on a timer every 5
seconds *in addition to* firing it on every render-triggering event (a new assistant message, a tool
result, a mode change) — so a script that takes 200ms to run is 200ms of latency felt on a schedule,
not a one-off. `jq` and a handful of string comparisons cost single-digit milliseconds; a `statusLine`
that shells out to a network call or a slow subprocess would instead impose that latency on every one
of those ticks, which is the actual argument for keeping the command itself trivial rather than a
convenience note.

**Gotcha:** `padding: 0` and a `refreshInterval` are both optional and independent — setting only
`refreshInterval` without touching `padding` is fine; the schema does not require either once `type`
and `command` are present.

> `statusLine` turns a cost you would otherwise have to run `/context` to see into one you see on every
> prompt, at the cost of running your command on the render schedule you configure.

## 4. Keybindings and `~/.claude/keybindings.json` `[DOC]`

**Mechanism.** Custom keybindings live in `~/.claude/keybindings.json`, loaded and validated on
startup and hot-reloaded on change. `settings-reference` documents one related, narrower setting
directly — `keybindingFlavor`, described there as making "`Ctrl+W` delete back to the previous
whitespace, as Bash does," scoped to Interface and terminal, settable in any settings file — but the
full `keybindings.json` file format sits on a page (`/docs/en/keybindings`) outside the nine permitted
for this guide, so the shape below is stated as observed directly from the v2.1.251 binary rather than
cited as a documentation quote. The file is an array of binding blocks, each naming a context and a map
of keys to actions:

```json
{
  "$schema": "https://www.schemastore.org/claude-code-keybindings.json",
  "bindings": [
    { "context": "Chat", "bindings": { "ctrl+e": "chat:externalEditor" } }
  ]
}
```

Contexts observed in the binary's own validator include at least `Global`, `Chat`, and `Autocomplete`;
multi-key chords are supported with their own timeout window before the chord is cancelled.

**Gotcha:** validation runs on load, but a bad binding — an unknown context, or an unrecognized action
name — does not stop Claude Code or surface a visible error; it is silently skipped (the default
binding for that key keeps working) and the reason is logged only under `--debug`. A rebind that
silently "did nothing" is almost always this, not a bug in the harness.

**Definition:**

> `~/.claude/keybindings.json` is a hot-reloaded, per-context list of key-to-action overrides, validated
> on load with failures reported only to the debug log rather than the terminal.

## Pitfalls

- **Belief:** "if my custom keybinding isn't working, the keybindings file must not be loading at
  all." **What actually happens:** the file loads and every *other* binding in it still applies; only
  the one entry with the bad context or unknown action name is skipped, silently, with the default
  binding left in place for that key. **What gets the guarantee:** re-run with `--debug` and check the
  log for `[keybindings] Found N validation issue(s)`, which names the exact offending context or
  action. **Why people believe it:** a keybinding that "does nothing" looks identical whether the whole
  file failed to load or one entry in it was rejected, and the terminal gives no visual signal either
  way.

- **Belief:** "an idempotency key alone is enough to make an endpoint safe to retry." **What actually
  happens:** a naive implementation is safe against sequential retries and still duplicates work under
  a genuine concurrent race, because two requests can both observe "key not seen yet" before either
  commits — exactly mistake #2 in §2. **What gets the guarantee:** a uniqueness constraint enforced by
  the database (not just an application-level existence check) plus a caught
  `DataIntegrityViolationException` that replays the winner's response to the loser. **Why people
  believe it:** the sequential test — call it twice, back to back — passes on the naive version, so it
  looks solved; only a concurrent test exposes the gap, and most teams do not write one for an
  idempotency feature until it duplicates something in production.

## Cheat sheet

| Item | What it is | Key fact |
|---|---|---|
| Bad-fit shapes for delegation | One-liner you already know, taste you can't state, review costlier than the work | Delegation has a fixed floor cost that does not shrink with task size |
| Idempotency key pattern | Hash the body, key on the header, unique-constrain the key column | Sequential tests pass on a naive version; only a concurrency test catches the race |
| `statusLine` | `{type:"command", command, padding?, refreshInterval?, hideVimModeIndicator?}` | Runs on render events *and* on `refreshInterval` seconds — a slow command is felt on a schedule |
| `subagentStatusLine` | `{type:"command", command}` | No `refreshInterval`; fires on per-row task-panel updates instead |
| `~/.claude/keybindings.json` | Array of `{context, bindings}` blocks, `$schema`-validated, hot-reloaded | Bad entries are skipped silently; check `--debug` for `[keybindings]` warnings |
| `keybindingFlavor` | A documented settings-reference key (e.g. Bash-style `Ctrl+W`) | Narrower than the full keybindings file; lives in `settings`/`settings-reference`, not a separate doc page in this guide's set |

## Self-test

1. Why does a five-line diff not tell you how expensive it will be to review?
<details><summary>Answer</summary>Diff size measures how much text changed, not how much reasoning is
required to be confident it is correct; a five-line change to a hot-path concurrency primitive can cost
far more careful reading than a five-line logging change, so the review-cost comparison against
delegation has to be made per task, not inferred from line count.</details>

2. In the idempotency example, why did `sameKeyDifferentBodyIsRejected` pass against the naive first
   implementation's *intent* but fail against its actual behavior?
<details><summary>Answer</summary>The naive implementation checked only whether the idempotency key had
been seen before and, if so, replayed the cached response unconditionally — it never compared the new
request's body against the original. Reusing the key with a changed `quantity` field should return
`409`, but the naive code returned the cached `201` instead, which the test's status-code assertion
caught directly.</details>

3. Why did the concurrency test in §2 sometimes pass and sometimes fail against the same buggy code?
<details><summary>Answer</summary>The bug was a race: two threads could both execute
`findByIdempotencyKey` and see nothing before either thread's insert committed, so whether the race
actually manifested as a duplicate row depended on the JVM's and database's exact interleaving on that
run — a timing-dependent failure, unlike the deterministic body-hash bug.</details>

4. What made the corrected implementation immune to that race, that the naive version lacked?
<details><summary>Answer</summary>A database-level unique constraint on the `idempotency_key` column,
combined with catching `DataIntegrityViolationException` on the losing insert and replaying the
winner's already-committed record — moving the guarantee from an application-level check (which two
concurrent transactions can both pass) to a guarantee the database itself enforces.</details>

5. What is the documented one-line description of `statusLine` on the settings-reference page, and what
   part of its behavior is *not* covered by that page?
<details><summary>Answer</summary>"Run your own command to render a status line below the prompt,"
scoped to Interface and terminal settings, settable in any settings file. The exact JSON schema —
`type`, `command`, `padding`, `refreshInterval`, `hideVimModeIndicator` — is not expanded on the fetched
page and was instead confirmed against the installed binary's own settings validator.</details>

6. Why does `subagentStatusLine` have no `refreshInterval` field while `statusLine` does?
<details><summary>Answer</summary>`subagentStatusLine` renders once per row update in the agent task
panel, driven by the panel's own event stream; there is no fixed clock to attach a polling interval to,
whereas `statusLine` needs `refreshInterval` specifically to catch state changes (like elapsed cost)
that occur between the render-triggering events it otherwise relies on.</details>

7. A `statusLine` command that shells out to a slow network call is configured with `refreshInterval:
   5`. What is the actual cost of that slowness?
<details><summary>Answer</summary>Not just a one-time delay: the harness re-invokes the command on
every render-triggering event *and* on a 5-second timer, so a slow command's latency is paid
repeatedly, on a schedule, for as long as the session runs — not a single fixed cost.</details>

8. A user rebinds `ctrl+e` in `~/.claude/keybindings.json` under an unrecognized context name. What
   happens, and how would they find out why?
<details><summary>Answer</summary>The rest of the file still loads and applies; the one bad entry is
silently skipped, and the previous/default binding for that key keeps working. Nothing appears in the
normal terminal output — the user would need to re-run with `--debug` and look for a
`[keybindings] Found N validation issue(s)` log line naming the unrecognized context.</details>

## Open questions

- Whether the `context_window` field on the `statusLine` stdin payload carries a raw token count or a
  percentage was not resolvable from the extracted v2.1.251 binary strings; the sample script in §3
  prints it unlabeled rather than assuming a unit.
- The full list of valid `keybindings.json` contexts beyond `Global`, `Chat`, and `Autocomplete` was
  truncated in the binary string extraction used to verify this leaf; the three named are confirmed,
  the complete enumeration is not.

---

**Leaves covered:** 2.7.9–2.7.12 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** none — D-64 in `practices/01` draws plan mode and D-41 in `skills/06` draws the mechanism decision tree
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 561
