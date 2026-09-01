# Valuation — MEDIUM Paper 5 (taken by accident, labeled E5)

**Answers:** `tmp/papers/answers/E5-paper.txt` — the file contains answers to
`tmp/papers/medium/paper-5.md`, NOT easy paper 5. Evaluated against
`tmp/papers/medium/paper-5-key.md`.
**Score: 3.5 / 19** (Q1 code deferred). **Do not read this as regression** —
it's a tier jump taken without the between-tier study the plan prescribes.
Easy paper 5 (with the ACID retest Q10b) is still pending at
`tmp/papers/easy/paper-5.md`.

## What this accident actually bought us

An honest, unprepped measurement of the medium bar. Two conclusions:

1. **The medium tier is not yet accessible — as the gap map predicted.**
   Nearly every blank maps one-to-one onto an already-flagged study item.
   Nothing here is a surprise; it's confirmation with sharper coordinates.
2. **Even at medium tier, real signal got through** where foundations
   exist: the hybrid-cache design answer (Q16) was the paper's best and
   scored full marks.

## Per-question (abbreviated for the blanks)

| Q | Topic | Score | Note |
|---|---|---|---|
| 1 | `[CODE]` longest substring | **—** | Deferred (list: E2 Q2, E4 Q2, M5 Q1). |
| 2 | PriorityQueue internals | **0** | peek O(1) guessed right for the wrong reason (it's the array-backed **heap's root**, not "end of queue"); poll is O(log n), not O(n); iteration order is array order, not sorted. Heap internals → study list. |
| 3 | Immutable DateRange | **0.5** | final class/fields, no setters — right. The explicitly-demanded part was missed: **defensive copies** of mutable params in the constructor AND getters (`new Date(start.getTime())`) — without them the caller mutates your "immutable" state through the shared reference. |
| 4 | Modern Java | **0.5** | Records + Optional with uses: fine. Functional interfaces/streams are Java 8 — the modern half (sealed interfaces, pattern-matching switch, virtual threads, text blocks) is unknown, self-flagged. Worth a chapter before medium tier; it's also plan Week 15 material. |
| 5 | Double-checked locking | **0.5** | Sketch structurally right (both null-checks + synchronized). The volatile reason given (cache staleness/visibility) is the partial answer — the specific killer is **instruction reordering**: the reference can be published before the constructor finishes, so another thread sees a non-null, half-constructed object. |
| 6 | OOM kinds | **0** | StackOverflowError is not an OOM. The three: heap space, unable-to-create-native-thread, Metaspace; flag: `-XX:+HeapDumpOnOutOfMemoryError`. |
| 7 | LazyInitializationException | **0** | Blank — confirms gaps.md §2.1 (JPA foundations before sharp edges). Connects directly to E4's missed fetch-defaults. |
| 8 | N+1 | **0** | Blank — same §2.1 confirmation. These two are the highest-value JPA interview topics at your YOE. |
| 9 | Keyset pagination | **0** | Blank — indexing-depth gap flagged in E3 valuation, now confirmed at medium tier. |
| 10 | Lost update | **0** | Blank — transactions/isolation study item (pairs with the pending ACID retest). |
| 11 | WebSocket/polling/SSE | **0.5** | Polling + scorecard example: right. Terminology conflation to fix: **WebSocket** = persistent bidirectional connection (established via HTTP **Upgrade** handshake — the asked mechanism); **SSE** = server→client stream over plain HTTP; **webhook** = server-to-server HTTP callback (your "payment completion callback" example is a webhook, not SSE). |
| 12 | epoll / C10K | **0** | "Threads take turns" is the thread-per-connection model — the question asks what *replaces* it: readiness-based multiplexing (`epoll`) — one thread watches thousands of sockets, kernel reports which are ready. |
| 13 | Rate limiting | **0** | Blank. |
| 14 | OAuth2 client credentials | **0** | Blank — plan Week 15/Day 73 territory; expected at this stage. |
| 15 | SQS vs Kafka | **0** | Blank — the broker-mechanics gap (E3+E4 pattern) at its medium-tier depth. |
| 16 | Caffeine vs Redis hybrid | **1** | **Best answer of the paper.** Read-heavy → in-process; updates → central Redis; hybrid near-cache with invalidate-and-refill; and you spotted the remaining problem (stale reads during propagation) unprompted. This is the level your cache answers have held at all tier long. |
| 17 | Mockito specifics | **0.5** | (a) void methods — correct (also: spies). (b/c) missing: ArgumentCaptor grabs the actual argument object for rich assertions; verify-everything welds tests to implementation. |
| 18 | revert/reset/checkout | **0** | Blank — E2 showed git basics are fine; the recovery-tools layer (revert vs reset, reflog) isn't there yet. |
| 19 | OOMKilled vs OOM | **0** | Blank — container/JVM memory interplay, ops-depth gap as expected. |
| 20 | Alert design | **0** | Blank — observability judgment, expected blank pre-plan. |

## Findings → `qbank/13-scoring-and-report.md` + gaps.md

1. **Medium-tier entry gate confirmed, with a concrete syllabus.** The
   blanks cluster exactly on: JPA sharp edges (Q7/Q8), transactions/
   isolation (Q10 + pending ACID), indexing/pagination mechanics (Q9),
   broker mechanics (Q15), heap/PQ internals (Q2), git recovery tools
   (Q18), ops depth (Q19/Q20), auth flows (Q13/Q14). That list — not the
   full medium tier — is the study program between tiers.
2. **NEW (small): WebSocket/SSE/webhook terminology conflation** — cheap,
   interview-visible fix; one comparison table read.
3. **NEW (small): DCL volatile reason known only as visibility** — the
   reordering/half-constructed-object story is the medium-tier answer.
4. **Strength confirmed under pressure: caching design.** Full marks at a
   tier above current level, unprompted staleness caveat. Consistent with
   every easy-tier caching result. Treat as a banked strength.
5. **M5 is now spent** as a clean instrument (questions seen, corrections
   above) — the medium tier retains M1–M4 as fresh papers, which is
   plenty; M5's topics all reappear across M1–M4 and the qbank ladders.

## Actions taken

- No paper modifications: M1–M4 remain fresh and already cover everything
  M5 tested; the between-tier syllabus above is study guidance, not paper
  surgery.
- Deferred code list updated: E2 Q2, E4 Q2, **M5 Q1**.
- gaps.md §9 appended with the M5-preview evidence.

## Sequencing instruction (corrected path)

1. **Take the real easy paper 5** — `tmp/papers/easy/paper-5.md`, 21
   questions including the ACID retest (Q10b). The E4 pre-study list
   (ACID, fetch defaults, DLQ path, CI-vs-CD, PreparedStatement) still
   applies.
2. Then the **deferred code session**: one file, answers to E2 Q2
   (palindrome), E4 Q2 (char frequencies), E5 Q10 (SQL, if you defer it),
   M5 Q1 (longest substring).
3. Then the easy-tier wrap-up valuation + the between-tier syllabus from
   finding #1, THEN medium papers starting at M1.

Tip to avoid a repeat: papers live in `tmp/papers/easy/`, `medium/`,
`hard/` — check the folder and the header line (easy = "20/21 questions,
suggested 60–65 min") before starting a sitting.