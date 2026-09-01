# 10 — Testing & Engineering Craft

**What this decides:** whether testing needs a from-scratch track (the plan
assumes working fluency by Day 94), and whether git/code-review/debugging
craft gaps need explicit sessions. Craft is directly probed in L4/L5
interviews and take-homes.

---

## Part A — Testing ladder

### Q1 [L1] explain-back — Unit vs integration vs end-to-end
Define each and state why the pyramid puts unit at the bottom.
**Strong answer:** unit = one component in isolation, fast, precise failure
localization; integration = components + real collaborators (DB, HTTP);
E2E = whole system, user-level. Pyramid: cost/speed/flakiness rise as you
go up; failure localization falls. Bonus: names the inverted-pyramid
(ice-cream cone) smell.

### Q2 [L2] explain-back — Test doubles + what to mock
Mock vs stub vs fake. Then: in a service that calls a repository, a payment
gateway client, and a `PriceCalculator` (pure logic class) — which do you
mock in a unit test and which do you NOT, and why?
**Strong answer:** stub = canned answers; mock = verifies interactions;
fake = working lightweight impl (in-memory repo). Mock the boundaries you
own the interface to (repo, gateway client); do NOT mock the pure logic
class — use the real one (mocking it tests nothing and welds tests to
implementation). Bonus: "don't mock what you don't own" — wrap third-party
clients and mock the wrapper.

### Q3 [L3] write-it `[OPEN-EDITOR — 20 min]` — Test a service
```java
public class DiscountService {
    private final CustomerRepo repo;           // interface you own
    private final Clock clock;
    public DiscountService(CustomerRepo repo, Clock clock) { ... }

    /** 10% for loyalty customers, 20% on their signup anniversary,
     *  0 for blocked customers. Throws if customer unknown. */
    public BigDecimal discountFor(String customerId) { ... }
}
```
Write JUnit 5 + Mockito tests covering the behavior (assume a plausible
implementation).
**Score 1:** ≥4 tests: loyalty 10%, anniversary 20% (fixed `Clock`!),
blocked → 0, unknown → exception (`assertThrows`); given-when-then shape;
BigDecimal compared correctly (`isEqualByComparingTo` or compareTo).
**0.5:** happy paths only, or didn't control the clock. **0:** can't produce
runnable-looking tests in 20 min.

### Q4 [L3] explain-back — Time and randomness
Why is `LocalDate.now()` inside business logic a testing problem, and what's
the standard fix? Same question for `new Random()` / `UUID.randomUUID()`.
**Strong answer:** hidden non-deterministic dependency → untestable
boundaries (the anniversary bug appears only on the anniversary). Fix:
inject `Clock` (`Clock.fixed` in tests) / inject a `Supplier<UUID>`/seeded
Random — make time and randomness dependencies like any other.

### Q5 [L3] scenario — Flaky tests
Name four distinct causes of flaky tests and the fix for each.
**Strong answer (any 4):** shared mutable state / test-order dependence →
isolate, fresh fixtures; async without proper waiting (`Thread.sleep`) →
Awaitility/latches; time dependence → fixed Clock; external/network deps →
containers or fakes; concurrency in code under test → deterministic
executors; leftover DB state → transaction rollback or truncation. Fix
must match cause.

### Q6 [L2] explain-back — Testing the repository layer
H2 in-memory vs Testcontainers-Postgres for repository tests — trade-off
and your pick?
**Strong answer:** H2: fast, zero deps, but a DIFFERENT database — dialect
gaps, missing PG features (JSONB, `ON CONFLICT`), false confidence;
Testcontainers: real engine, slower, needs Docker. Pick Testcontainers for
anything with native SQL/PG features; knows why "tests pass, prod breaks"
happens with H2. (Score honest L1 if you've never tested repositories at all
— record it, that's a finding.)

## Part B — Git & collaboration ladder

### Q7 [L2] explain-back — merge vs rebase, revert vs reset
When is each appropriate? When is force-push acceptable?
**Strong answer:** merge preserves history (shared branches); rebase
rewrites for linear history (LOCAL/private branches only); golden rule:
never rewrite shared history; force-push OK on your own feature branch
(prefer `--force-with-lease`). Revert = new inverse commit (safe on shared);
reset = moves the branch pointer (local surgery). Bonus: interactive rebase
for cleanup before PR.

### Q8 [L3] scenario — Regression hunt
A bug exists on `main` today; you know release `v2.3` (400 commits ago) was
good. Find the culprit commit efficiently.
**Strong answer:** `git bisect` — binary search, ~9 steps for 400 commits;
`git bisect run <test-script>` to automate if a repro script exists.
Manual log-reading = 0.5. Bonus: what to do when the culprit is a giant
merge commit.

### Q9 [L4] discriminator — Code review
You're reviewing a 600-line PR that works but has problems. What do you look
for (priority order), and how do you deliver the feedback?
**L2 answer:** style, naming, bugs. **L4 answer (=1.0):** priority: correctness
/ edge cases → security/data handling → design & maintainability → tests
(do they pin behavior?) → style LAST (linters' job); distinguishes blocking
from nit comments; asks questions instead of commanding ("what happens if X
is null here?"); flags that 600 lines is itself the first problem — ask for
a split; praises what's good. Mentions of review SLAs/PR-size norms = bonus.

## Part C — Debugging methodology

### Q10 [L4] discriminator — The 1% prod bug
A bug hits ~1% of requests in prod; you cannot reproduce it locally.
Describe your systematic approach.
**L1 tier:** "add logs and look." **L3 tier:** form hypotheses from the error
signature; enrich logging around the suspect path (with request/correlation
ids to stitch a request across logs); diff the 1% — common user? payload
shape? instance? time? concurrency?; binary-search the request lifecycle.
**L4 tier (=1.0):** all that PLUS: check recent deploys/flags first
(what changed?); look for the non-uniformity (1% is a clue — retry paths,
race windows, one bad pod, cache miss path); capture a failing example
end-to-end before changing code; write the regression test once found.
Hypothesis-driven + correlation-id fluency is the bar.

---

## Breadth checklist (rate 0–3)

- [CORE] JUnit 5: parameterized tests, `assertThrows`, lifecycle annotations
- [CORE] AssertJ or Hamcrest fluent assertions
- [CORE] Mockito: `verify`, `ArgumentCaptor`, `when/thenReturn` vs `doThrow`
- [CORE] Given-When-Then / Arrange-Act-Assert structure by habit
- [CORE] `git stash`, cherry-pick, `reflog` (the "undo anything" tool — heard of reflog?)
- [CORE] Writing a clear PR description; commit message discipline
- `@MockBean` vs `@Mock` — context restart cost of `@MockBean` (heard of?)
- Test coverage: how measured, and your OPINION on chasing 100%
- Contract testing (heard of? Pact/Spring Cloud Contract)
- Mutation testing (0–1 fine)
- Test naming conventions that describe behavior
- TDD — actually tried red-green-refactor? Opinion?
- CI pipeline stages at your job — can you describe what runs on your PRs?
- Trunk-based vs GitFlow — exposure to the debate
- Pairing/mob experience (0–1 fine, but note for pairing interviews)
- Debugger fluency: conditional breakpoints, evaluate-expression, remote debug (vs println-only)
- Structured logging: log levels used deliberately; what MDC is (heard of?)
