# Pre-M3 Study Plan — one ordered program, everything in one place

Rule for every block: read → close the file → answer the self-check ALOUD →
only then tick the box. A ticked box you can't re-answer two days later is
untucked. Realistic pace: 7–10 days at ~1.5h/day alongside normal work.
When all boxes hold, do the code batch, then take M3 closed-book.
Target: M3 ≥ 10/19.

## Day 1–2 — The multiplier: Spring proxy model + JPA states

The single highest-leverage item (M1 Q7/Q8 = 0/2; unlocks M3 Q7/M4 Q6-Q8
class questions and the prep plan's Day 55–65 track).

- [ ] **Proxy model.** Source: M1-valuation Q7/Q8 + medium-1 key Q7/Q8.
  Learn: Spring wraps beans in a proxy (JDK dynamic/CGLIB); the proxy runs
  @Transactional/@Cacheable logic around the real call; `this.method()`
  bypasses it → annotations silently ignored; private/final can't proxy.
  Self-check: explain why REQUIRES_NEW on a self-called method does
  nothing, and give both fixes (separate bean; self-injection).
- [ ] **JPA entity states + persistence context.** Source: medium-2 key Q8.
  transient → managed (tracked in the persistence context = identity map +
  dirty checking) → detached / removed. Why `save()` on a managed entity
  is a no-op; why mutating a managed entity writes SQL without save.
  Self-check: narrate the four states for one Order through a request.

## Day 2–3 — Concurrency, medium layer (basics are repaired; this is the next floor)

- [ ] **Re-run primer-1 self-check §1–§7 aloud** — especially §6 deadlock:
  write the two-lock narrative + global-lock-order fix from memory (M2 Q5
  showed recognition without explanation).
- [ ] **primer-2 part 4: volatile vs atomicity** — missed twice (E5 Q5,
  M1 Q5). Self-check: the flag-vs-counter table + verdict on
  `volatile int counter; counter++`.
- [ ] **Compound actions.** check-then-act is a race even on concurrent
  collections → `computeIfAbsent` / `putIfAbsent` / atomic classes.
  Self-check: fix M1 Q6's cache in one line and say WHY containsKey+put
  can't be fixed by async.
- [ ] **ThreadPoolExecutor.** Source: medium-2 key Q6. core → queue → max →
  rejection, and the unbounded-queue surprise (max never kicks in).
  Self-check: narrate what happens to task #1001.
- [ ] **ConcurrentModificationException.** Source: medium-2 key Q3.
  fail-fast iterators; fixes: `removeIf`, `iterator.remove()`.

## Day 3–4 — Java core holes

- [ ] **Type erasure + PECS.** Source: medium-2 key Q4 + qbank 02 Q4.
  Erasure: generics are compile-time; erased to bounds; no `new T[]`, no
  `instanceof List<String>`. PECS: producer-extends (read), consumer-super
  (write); `copy(List<? super T> dest, List<? extends T> src)`.
  Self-check: explain why you can't add a Dog to `List<? extends Animal>`.
- [ ] **quick-notes.md, full pass** — every bullet re-answerable aloud
  (Integer cache, remove-overload, HashMap constants, amortized ArrayList:
  the M2 Q1 blank was a topic you'd already half-known — copies sum to
  ~2n → O(1) amortized per add; the TERM is "amortized analysis").

## Day 4–5 — SQL & DB (weakest recurring theme)

- [ ] **Primer-2 part 1 (ACID)** — the four-scenario disambiguator until
  reflexive; Isolation↔Consistency swap is your specific bug.
- [ ] **NOT IN + NULL.** Source: medium-2 key Q9. One NULL in the subquery
  → zero rows, silently (three-valued logic). Safe form: NOT EXISTS.
- [ ] **Why the planner skips an index.** Source: medium-2 key Q10. Four:
  low selectivity, function/cast on column, leading wildcard, stale stats.
- [ ] **Leftmost-prefix rule** (M1 Q10 miss) + **keyset pagination**
  (primer-3 §3, write the WHERE clause from memory).
- [ ] **Word-problem SQL reps** — the code-session finding: recognition,
  not recall, is the gap. 5 problems on pgexercises (or paper): each time,
  first ask "is an aggregation hiding in the words?"

## Day 5–6 — Web/security cluster

- [ ] **primer-2 part 3 (CORS)** — browser enforces, preflight OPTIONS,
  Allow-* headers, curl unaffected. Retest: this was M2 Q14, will recur.
- [ ] **JWT validation checklist.** Source: medium-2 key Q13. Signature
  (+ pinned alg, reject `none`), exp, iss, aud; payload readable BY DESIGN
  — signature = integrity/authenticity, not confidentiality.
- [ ] **TLS in three goals.** Source: medium-2 key Q12. Authenticate server
  (cert chain), agree symmetric session keys, integrity; asymmetric only
  at start because it's slow.
- [ ] **TIME_WAIT / port exhaustion.** Source: medium-2 key Q11. Short-lived
  outbound connections → ephemeral ports stuck in TIME_WAIT → "cannot
  assign requested address"; structural fix = pooled keep-alive client.

## Day 6–7 — Messaging, caching, testing

- [ ] **primer-2 part 2 (broker lifecycle)** — the 3-paper miss. One-liner
  ready: consumers down → messages wait; DLQ = repeated processing failures.
- [ ] **primer-3 §4 (delivery semantics)** + **idempotent consumer design**
  (medium-2 key Q15): event id + UNIQUE constraint, same transaction as
  the business write — that's what makes it race-proof.
- [ ] **primer-3 §1 (cache-aside)** + stampede mitigations (M2 key Q16):
  jitter, single-flight, refresh-ahead — you already know the NAME.
- [ ] **primer-3 §2 (test doubles)** + **§5 (Clock)**.
- [ ] **Test types in one pass** (your Q17 request): unit (isolated, fast)
  → slice (@WebMvcTest/@DataJpaTest — one layer with framework) →
  integration (real collaborators via Testcontainers) → E2E (whole system)
  → smoke (few critical paths post-deploy) → acceptance (business-facing
  criteria). Flaky-test causes ×4: shared state, async/sleeps, time,
  external deps — fixes: isolation, Awaitility, Clock, containers.
- [ ] **Git recovery trio.** revert (shared history) / reset (local
  surgery) / restore (one file) + `--force-with-lease` rule + reflog.

## Day 7+ — Code batch (the standing gate), then M3

- [ ] Redo set: isPalindrome (real Java, both variants), charFrequencies
  (compiles, complexity stated), E5 SQL + the two variants.
- [ ] Deferred set: M5 Q1 (longest substring, 25-min box), M1 Q9 (top-2
  per dept — window function), M2 Q2 (twoSum, 15-min box).
- [ ] All compiled/run; lookups marked; one file:
  `tmp/papers/answers/medium-code-session.txt`.
- [ ] Then **M3, closed book**. It verifies: isolation anomalies (ACID),
  broker/DLQ (poison message), N+1 (proxy/JPA study), LEFT-JOIN trap,
  flaky tests, epoll... i.e., nearly this exact list.

## What "done" looks like

Not "read everything" — but every box's self-check answerable aloud, cold,
two days after ticking. That's the standard that took concurrency from
0.5 to 2.0; it's the only loop with a proven result in this project.