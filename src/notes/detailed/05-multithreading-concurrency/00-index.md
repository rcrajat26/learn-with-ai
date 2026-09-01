# 05 Multithreading and Concurrency — index and file plan

**Target version: Java 21 LTS.** Java 22–25 divergences are marked `[VERSION-TRAP]` inline at the
point of each claim.

| Field | Value |
|---|---|
| Topic | 05 Multithreading and Concurrency |
| Source prompt | `src/metadata/prompts/05-multithreading-concurrency-prompt.md` |
| Prompt SHA-256 | `3cf728f713b43a6c62ac5ab129b5822c60186117feaeb896383144bec8833a6b` |
| Prompt last modified | 2026-08-31 17:18:25, 363939 bytes, 4102 lines |
| Syllabus leaves | 1141 (Part 1: 470, Part 2: 198, Part 3: 207, Part 4: 69, Part 5: 197) across 65 numbered sections |
| Diagram manifest | 218 ids, D-001 … D-218. 59 are `table` type (rendered as Markdown tables, no SVG); 159 are standalone SVGs in `diagrams/` |
| Note files planned | 78 (77 note files + this index) |
| Example domain | QuizStakes — `src/scenario/scenario.md` (read-only) |

**On resume:** if the prompt's SHA-256 no longer matches the value above, every row reverts to
`planned` and the set is rebuilt. Otherwise dispatch only the rows marked `planned` or `blocked`.

---

## Deviations from the prompt's OUTPUT CONTRACT, and why

1. **Output root is `src/notes/detailed/05-multithreading-concurrency/`**, matching the prompt's
   own `# OUTPUT CONTRACT` and the sibling sets `03-java-core/` and `04-modern-java/`. The
   dispatching message named `multithreading-concurrency/` (no number) while also instructing
   "follow the prompt exactly"; the numbered form satisfies the prompt and the sibling convention.
2. **Fifteen of the contract's files are split further**, as the contract's own closing paragraph
   permits and requires ("If any single file becomes unwieldy, split it further … and register the
   new files in `00-index.md`"). No content is merged or dropped; every split is at a concept
   boundary. The splits are listed in the file plan below with an `a`/`b` suffix.
3. **`94-interview-questions-and-drills.md` is split six ways** (`94a`–`94f`). §5.1's 132 questions
   with full spoken-length answers cannot fit one file. `94f` carries §5.2, §5.3, Part 5's own
   wrap-up, and the set-wide flat `## Atomic concept checklist`.
4. **The per-tier interview files carry the prompt's 10 Q&As, not a subject-scaled count.** The
   generator's default is ten Q&As plus two per subject folder beyond the fifth, which for this
   topic's eighteen Part 1 subjects would be thirty-six. The prompt's `# TASK` hard instruction
   fixes it at "10 interview Q&As with full model answers" plus five predict-the-output puzzles
   per part, and Part 5 already carries the exhaustive bank — 132 questions in `94a`–`94e` and
   55 traps in `94f`. Scaling `90`–`93` as well would duplicate that bank and force each wrap-up
   past the split threshold for no added coverage. `90`–`93` therefore carry the summary table,
   10 Q&As and 5 puzzles, each spanning every subject in its part.
5. **`92-interview-internals.md` carries a pointer, not a copy, of the checklist.** The canonical
   flat `## Atomic concept checklist` lives at the end of `94f-trap-index-and-drills.md` per the
   prompt. `92` carries a `## Atomic concept checklist` heading with a one-line pointer to it, so
   that downstream parsers keyed on either location resolve.

---

## Reading orders

**First careful pass, cover to cover** — follow the file plan in the order it is written below.
It runs foundations → threads → thread safety → `synchronized` → `volatile`/JMM → `wait`/`notify`
→ atomics → locks → synchronizers → collections → queues → executors → `CompletableFuture` →
fork/join → `ThreadLocal` → virtual threads → structured concurrency → liveness → the master
tables → the cross-cutting Part 2 files → Part 4's build-it set → the interview files. Each
subject folder runs BASICS → INTERMEDIATE → INTERNALS, so a first-pass reader who wants to defer
the internals can skip every `internals` file and come back.

**Night-before re-read, in this order:**

1. `94f-trap-index-and-drills.md` — §5.2's 55 traps, the numbers drill (D-214), the version drill (D-215).
2. `master-tables/01-the-master-tables.md` — the cost, latency, footprint, guarantee and progress tables.
3. `version-delta/01-java-5-to-25.md` — what changed in 21 / 24 / 25 and in which direction.
4. `90-interview-basics.md`, `91-interview-intermediate.md`, `92-interview-internals.md`, `93-interview-build-it.md` — the four wrap-ups.
5. `94a`–`94e` — the 132 questions, skimming the answer shape rather than reading it.
6. The five `## Cheat sheet` blocks of whichever subject folders you are weakest in.

---

## File plan

Every leaf in the prompt's syllabus appears in exactly one row. Nav links are the previous and
next rows **in this table's order**; the first row omits `Previous:` and the last omits `Next:`.

Tier key: **B** = PART 1 BASICS, **I** = PART 2 INTERMEDIATE, **X** = PART 3 INTERNALS,
**BLD** = PART 4 BUILD IT, **Q** = PART 5 INTERVIEW.

| # | File | § | Leaves | Tier | Diagrams owned | Est. lines | Status | Lines |
|---|---|---|---|---|---|---|---|---|
| 1 | `foundations/01-basics-why-concurrency.md` | §1.1 | 1.1.1–1.1.10 (10) | B | D-001, D-002, D-003, D-004, D-005 | 320 | written | 516 |
| 2 | `foundations/02-basics-os-substrate.md` | §1.2 | 1.2.1–1.2.15 (15) | B | D-006, D-007, D-008, D-009 | 380 | written | 544 |
| 3a | `threads/01-basics-thread-api.md` | §1.3 | 1.3.1–1.3.9 (9) | B | D-010 | 380 | written | 587 |
| 3b | `threads/01b-basics-thread-api-builder-and-removals.md` | §1.3 | 1.3.10–1.3.18 (9) | B | D-011, D-012 | 380 | written | 600 |
| 4 | `threads/02-basics-lifecycle-and-states.md` | §1.4 | 1.4.1–1.4.12 (12) | B | D-013, D-014, D-015 | 340 | written | 559 |
| 5 | `threads/03-basics-interruption.md` | §1.5 | 1.5.1–1.5.14 (14) | B | D-016, D-017, D-018 | 360 | written | 584 |
| 6 | `thread-safety/01-basics-vocabulary.md` | §1.6 | 1.6.1–1.6.13 (13) | B | D-019, D-020, D-021, D-022 | 350 | written | 600 |
| 7 | `thread-safety/02-basics-races.md` | §1.7 | 1.7.1–1.7.12 (12) | B | D-023, D-024, D-025, D-026 | 360 | written | 599 |
| 8 | `synchronized/01-basics.md` | §1.8 | 1.8.1–1.8.18 (18) | B | D-027, D-028, D-029, D-030 | 440 | written | 600 |
| 9a | `volatile-and-jmm/01-basics-volatile.md` | §1.9 | 1.9.1–1.9.7 (7) | B | D-031, D-032 | 400 | written | 456 |
| 9b | `volatile-and-jmm/01b-basics-volatile-cost-and-arrays.md` | §1.9 | 1.9.8–1.9.14 (7) | B | D-033, D-034 | 400 | written | 589 |
| 10 | `volatile-and-jmm/02a-basics-happens-before.md` | §1.10 | 1.10.1–1.10.13 (13) | B | D-036, D-037, D-038 | 400 | written | 595 |
| 11 | `volatile-and-jmm/02b-basics-reordering-and-barriers.md` | §1.10 | 1.10.14–1.10.26 (13) | B | D-035, D-039, D-040, D-041, D-042 | 400 | written | 596 |
| 12 | `volatile-and-jmm/03a-basics-final-fields-and-publication.md` | §1.11 | 1.11.1–1.11.14 (14) | B | D-043, D-044 | 400 | written | 598 |
| 13 | `volatile-and-jmm/03b-basics-lazy-init-and-singletons.md` | §1.11 | 1.11.15–1.11.22 (8) | B | D-045, D-046, D-047 | 330 | written | 565 |
| 14 | `wait-notify/01-basics.md` | §1.12 | 1.12.1–1.12.16 (16) | B | D-048, D-049, D-050 | 410 | written | 600 |
| 15 | `atomics/01a-basics-cas-and-atomics.md` | §1.13 | 1.13.1–1.13.15 (15) | B | D-051, D-052, D-053 | 410 | written | 518 |
| 16 | `atomics/01b-basics-adders-varhandles-ordering.md` | §1.13 | 1.13.16–1.13.29 (14) | B | D-054, D-055, D-056 | 400 | written | 349 |
| 17 | `locks/01a-basics-reentrantlock-and-rwlock.md` | §1.14 | 1.14.1–1.14.18 (18) | B | D-057, D-058, D-059 | 440 | written | 408 |
| 18 | `locks/01b-basics-stampedlock-and-locksupport.md` | §1.14 | 1.14.19–1.14.29 (11) | B | D-060, D-061, D-062 | 360 | written | 531 |
| 19 | `synchronizers/01-basics.md` | §1.15 | 1.15.1–1.15.18 (18) | B | D-063, D-064, D-065 | 450 | written | 598 |
| 20 | `concurrent-collections/01a-basics-maps-and-iterators.md` | §1.16 | 1.16.1–1.16.14 (14) | B | D-066, D-067, D-070, D-071 | 410 | written | 596 |
| 21 | `concurrent-collections/01b-basics-sorted-cow-and-queues.md` | §1.16 | 1.16.15–1.16.24 (10) | B | D-068, D-069 | 330 | written | 465 |
| 22 | `queues/01-basics-blockingqueue.md` | §1.17 | 1.17.1–1.17.18 (18) | B | D-072, D-073, D-074, D-075 | 450 | written | 600 |
| 23 | `executors/01-basics-executor-framework.md` | §1.18 | 1.18.1–1.18.19 (19) | B | D-076, D-077 | 450 | written | 595 |
| 24 | `executors/02a-basics-threadpoolexecutor-submission.md` | §1.19 | 1.19.1–1.19.11 (11) | B | D-078, D-079, D-080 | 400 | written | 520 |
| 25 | `executors/02b-basics-threadpoolexecutor-tuning.md` | §1.19 | 1.19.12–1.19.22 (11) | B | D-081, D-082 | 380 | written | 599 |
| 26 | `executors/03-basics-scheduled-executors.md` | §1.20 | 1.20.1–1.20.10 (10) | B | D-083, D-084 | 330 | written | 599 |
| 27 | `completable-future/01a-basics-composition.md` | §1.21 | 1.21.1–1.21.14 (14) | B | D-085, D-086, D-087, D-088, D-089, D-090 | 440 | written | 598 |
| 28 | `completable-future/01b-basics-executors-timeouts-lifecycle.md` | §1.21 | 1.21.15–1.21.27 (13) | B | — | 400 | written | 600 |
| 29 | `fork-join/01-basics.md` | §1.22 | 1.22.1–1.22.16 (16) | B | D-091, D-092 | 420 | written | 565 |
| 30 | `thread-local/01-basics.md` | §1.23 | 1.23.1–1.23.13 (13) | B | D-093, D-094 | 370 | written | 327 |
| 31 | `virtual-threads/01-basics-the-model.md` | §1.24 | 1.24.1–1.24.19 (19) | B | D-095, D-096, D-097, D-098, D-099 | 460 | written | 591 |
| 32 | `structured-concurrency/01-basics.md` | §1.25 | 1.25.1–1.25.16 (16) | B | D-100, D-101, D-102, D-103 | 420 | written | 579 |
| 33 | `liveness/01-basics-failures.md` | §1.26 | 1.26.1–1.26.20 (20) | B | D-104, D-105, D-106 | 480 | written | 600 |
| 34 | `90-interview-basics.md` | Part 1 wrap-up over §1.1–§1.26 | — | Q | — | 420 | written | 401 |
| 35 | `master-tables/01-the-master-tables.md` | §2.1 | 2.1.1–2.1.8 (8) | I | D-107, D-108, D-109, D-110, D-111 | 420 | written | 414 |
| 36 | `locks/03-contention-economics.md` | §2.2 | 2.2.1–2.2.14 (14) | I | D-112, D-113, D-114, D-115 | 400 | written | 600 |
| 37 | `locks/02-choosing-a-primitive.md` | §2.3 | 2.3.1–2.3.14 (14) | I | D-116, D-117, D-118 | 390 | written | 600 |
| 38 | `executors/04-pool-sizing.md` | §2.4 | 2.4.1–2.4.18 (18) | I | D-119, D-120, D-121 | 450 | written | 600 |
| 39 | `atomics/02-the-atomicity-decision.md` | §2.5 | 2.5.1–2.5.10 (10) | I | D-122, D-123, D-124 | 350 | written | 549 |
| 40 | `concurrent-collections/02-the-collection-decision.md` | §2.6 | 2.6.1–2.6.14 (14) | I | D-125, D-126 | 390 | written | 599 |
| 41 | `queues/02-backpressure-design.md` | §2.7 | 2.7.1–2.7.12 (12) | I | D-127, D-128, D-129 | 370 | written | 561 |
| 42 | `completable-future/02-in-anger.md` | §2.8 | 2.8.1–2.8.14 (14) | I | D-130, D-131 | 400 | written | 600 |
| 43 | `virtual-threads/02-in-production.md` | §2.9 | 2.9.1–2.9.14 (14) | I | D-132, D-133, D-134 | 400 | written | 600 |
| 44 | `thread-safety/03-class-design.md` | §2.10 | 2.10.1–2.10.16 (16) | I | D-135, D-136 | 420 | written | 485 |
| 45 | `thread-local/02-context-propagation.md` | §2.11 | 2.11.1–2.11.10 (10) | I | D-137 | 340 | written | 528 |
| 46 | `observability/01-testing-and-verifying.md` | §2.12 | 2.12.1–2.12.14 (14) | I | D-138, D-139 | 400 | written | 600 |
| 47 | `utility-surface/01-the-adjacent-apis.md` | §2.13 | 2.13.1–2.13.16 (16) | I | D-140 | 410 | written | 551 |
| 48 | `beyond-one-jvm/01-distributed-analogues.md` | §2.14 | 2.14.1–2.14.8 (8) | I | D-141, D-142 | 300 | written | 497 |
| 49 | `version-delta/01-java-5-to-25.md` | §2.15 | 2.15.1–2.15.16 (16) | I | D-143, D-144 | 410 | written | 595 |
| 50 | `91-interview-intermediate.md` | Part 2 wrap-up over §2.1–§2.15 | — | Q | — | 420 | written | 401 |
| 51 | `synchronized/02-internals-header-and-mark-word.md` | §3.1 | 3.1.1–3.1.8 (8) | X | D-145, D-146, D-147 | 320 | written | 519 |
| 52 | `synchronized/03-internals-monitors.md` | §3.2 | 3.2.1–3.2.18 (18) | X | D-148, D-149, D-150, D-151, D-152 | 470 | written | 599 |
| 53 | `volatile-and-jmm/04-internals-jit-and-barriers.md` | §3.3 | 3.3.1–3.3.12 (12) | X | D-153, D-155 | 380 | written | 599 |
| 54 | `volatile-and-jmm/05-internals-safepoints.md` | §3.4 | 3.4.1–3.4.10 (10) | X | D-156, D-157 | 340 | written | 446 |
| 55 | `locks/04a-internals-aqs-queue-and-acquire.md` | §3.5 | 3.5.1–3.5.13 (13) | X | D-158, D-159, D-160, D-161, D-162, D-164 | 440 | written | 596 |
| 56 | `locks/04b-internals-aqs-conditions-and-mappings.md` | §3.5 | 3.5.14–3.5.22 (9) | X | D-163 | 340 | written | 528 |
| 57 | `locks/05-internals-locksupport-and-os.md` | §3.6 | 3.6.1–3.6.10 (10) | X | D-165 | 340 | written | 533 |
| 58 | `volatile-and-jmm/06-internals-jmm-formally.md` | §3.7 | 3.7.1–3.7.15 (15) | X | D-154, D-166, D-167, D-168 | 430 | written | 597 |
| 59 | `concurrent-collections/03a-internals-chm-table-and-resize.md` | §3.8 | 3.8.1–3.8.12 (12) | X | D-169, D-170, D-171, D-172 | 430 | written | 435 |
| 60 | `concurrent-collections/03b-internals-chm-trees-counting-traversal.md` | §3.8 | 3.8.13–3.8.24 (12) | X | D-173, D-174, D-175 | 410 | written | 424 |
| 61 | `atomics/03-internals-striped64-and-false-sharing.md` | §3.9 | 3.9.1–3.9.14 (14) | X | D-176, D-177 | 400 | written | 600 |
| 62 | `executors/05a-internals-queue-internals.md` | §3.10 | 3.10.1–3.10.11 (11) | X | D-178 | 390 | written | 599 |
| 63 | `executors/05b-internals-executor-and-future-internals.md` | §3.10 | 3.10.12–3.10.24 (13) | X | D-179, D-180, D-181, D-182, D-183, D-184 | 450 | written | 600 |
| 64 | `fork-join/02-internals-work-stealing.md` | §3.11 | 3.11.1–3.11.16 (16) | X | D-185, D-186, D-187, D-188, D-189 | 450 | written | 599 |
| 65 | `virtual-threads/03a-internals-continuations-and-mounting.md` | §3.12 | 3.12.1–3.12.11 (11) | X | D-190, D-191 | 400 | written | 351 |
| 66a | `virtual-threads/03b-internals-io-pinning-and-dumps.md` | §3.12 | 3.12.12–3.12.19 (8) | X | D-192, D-193 | 430 | written | 460 |
| 66b | `virtual-threads/03c-internals-cost-flock-and-scoped-values.md` | §3.12 | 3.12.20–3.12.22 (3) | X | D-194 | 300 | written | 383 |
| 67a | `observability/02-internals-runtime-observability.md` | §3.13 | 3.13.1–3.13.7 (7) | X | D-195, D-196, D-197, D-198 | 440 | written | 560 |
| 67b | `observability/03-internals-profiling-and-metrics.md` | §3.13 | 3.13.8–3.13.12 (5) | X | D-197 | 380 | written | 464 |
| 68 | `92-interview-internals.md` | Part 3 wrap-up over §3.1–§3.13 | — | Q | — | 430 | written | 349 |
| 69a | `build-it/01-locks-from-first-principles.md` | §4.1 | 4.1.1–4.1.4 (4) | BLD | D-199, D-201 | 450 | written | 579 |
| 69b | `build-it/01b-queue-locks-and-reentrancy.md` | §4.1 | 4.1.5–4.1.10 (6) | BLD | D-200 | 480 | planned | |
| 70a | `build-it/02-building-on-aqs.md` | §4.2 | 4.2.1–4.2.4 (4) | BLD | D-202 | 450 | planned | |
| 70b | `build-it/02b-aqs-fairness-and-conditions.md` | §4.2 | 4.2.5–4.2.7 (3) | BLD | — | 420 | planned | |
| 71a | `build-it/03-bounded-blocking-queue.md` | §4.3 | 4.3.1–4.3.3 (3) | BLD | D-203 | 470 | planned | |
| 71b | `build-it/03b-timed-drain-and-spsc-ring.md` | §4.3 | 4.3.4–4.3.7 (4) | BLD | D-204 | 470 | planned | |
| 72a | `build-it/04-non-blocking-stacks-and-aba.md` | §4.4 | 4.4.1–4.4.4 (4) | BLD | D-205 | 470 | planned | |
| 72b | `build-it/04b-lock-free-queue-and-striping.md` | §4.4 | 4.4.5–4.4.8 (4) | BLD | — | 470 | planned | |
| 72c | `build-it/04c-cow-list-mini-chm-and-diffs.md` | §4.4 | 4.4.9–4.4.11 (3) | BLD | — | 450 | planned | |
| 73a | `build-it/05-a-thread-pool-from-scratch.md` | §4.5 | 4.5.1–4.5.5 (5) | BLD | D-206 | 500 | planned | |
| 73b | `build-it/05b-factories-context-and-completion.md` | §4.5 | 4.5.6–4.5.9 (4) | BLD | — | 450 | planned | |
| 74a | `build-it/06-work-stealing-deque.md` | §4.6 | 4.6.1–4.6.3 (3) | BLD | D-207 | 450 | planned | |
| 74b | `build-it/06b-mini-forkjoin-pool.md` | §4.6 | 4.6.4–4.6.7 (4) | BLD | — | 470 | planned | |
| 75a | `build-it/07-structured-concurrency-from-scratch.md` | §4.7 | 4.7.1–4.7.4 (4) | BLD | D-208 | 470 | planned | |
| 75b | `build-it/07b-a-minimal-completablefuture.md` | §4.7 | 4.7.5–4.7.6 (2) | BLD | — | 420 | planned | |
| 76a | `build-it/08-visibility-and-update-harnesses.md` | §4.8 | 4.8.1–4.8.5 (5) | BLD | D-209, D-210 | 470 | planned | |
| 76b | `build-it/08b-starvation-leak-and-race-harnesses.md` | §4.8 | 4.8.6–4.8.10 (5) | BLD | — | 470 | planned | |
| 76c | `build-it/08c-backpressure-and-dump-reading.md` | §4.8 | 4.8.11–4.8.12 (2) | BLD | D-211, D-212 | 420 | planned | |
| 77 | `93-interview-build-it.md` | Part 4 wrap-up over §4.1–§4.8 | — | Q | — | 420 | planned | |
| 78 | `94a-interview-questions-fundamentals.md` | §5.1 | 5.1.1–5.1.33 (33) | Q | — | 480 | planned | |
| 79 | `94b-interview-questions-locks-and-atomics.md` | §5.1 | 5.1.34–5.1.60 (27) | Q | — | 450 | planned | |
| 80 | `94c-interview-questions-collections-and-executors.md` | §5.1 | 5.1.61–5.1.91 (31) | Q | — | 480 | planned | |
| 81 | `94d-interview-questions-liveness-and-loom.md` | §5.1 | 5.1.92–5.1.115 (24) | Q | — | 430 | planned | |
| 82 | `94e-interview-design-and-judgement.md` | §5.1 | 5.1.116–5.1.132 (17) | Q | — | 500 | planned | |
| 83 | `94f-trap-index-and-drills.md` | §5.2, §5.3 + Part 5 wrap-up | 5.2.1–5.2.55, 5.3.1–5.3.10 (65) | Q | D-213, D-214, D-215, D-216, D-217, D-218 | 550 | planned | |

Row count is 83 because the contract's 70 files became 77 after the splits, plus this index.

### Folds recorded

No row was folded. The smallest planned files are `volatile-and-jmm/03b` (8 leaves, 330 lines) and
`beyond-one-jvm/01` (8 leaves, 300 lines); both clear the ~120-line floor comfortably because
their leaves carry `[PROVE]`, `[SOURCE]` and diagram obligations.

### Sibling floor applied

`master-tables/`, `utility-surface/`, `beyond-one-jvm/` and `version-delta/` are single-file
subject folders rather than sections inside a parent, because the prompt's OUTPUT CONTRACT names
them as their own files and each is a genuine lookup destination (the cost tables, the adjacent
API surface, the distributed analogue table, the version timeline).

---

## Per-row detail

Primary concepts and the QuizStakes example assignment for each row. Two rows never tell
contradictory stories about the same entity.

| # | File | Primary concepts (2–6) | QuizStakes example assignment |
|---|---|---|---|
| 1 | foundations/01 | throughput vs latency vs blocking-tolerance; Amdahl's law; the USL; Little's law; the four server threading models | Stake reservations at 1,200/sec peak; PSP authorise p50 240 ms / p99 11 s; 55k peak concurrent sessions; four ways `PaymentService` could get its thread count |
| 2 | foundations/02 | the share/own split; context-switch mechanics and cost; platform-thread footprint; where the thread limit comes from | A `FundsLedger` instance on the shared heap; a `Money stake` local; 10 000 threads ≈ 10 GB; `OutOfMemoryError: unable to create native thread` under a container `pids.max` |
| 3 | threads/01 | `start()` vs `run()` and `IllegalThreadStateException`; `sleep`/`yield` have no synchronization semantics (JLS 17.3); `Thread.Builder` and the virtual-thread rejections; the removal timeline | A `StakeSettlementWorker implements Runnable`; a `ThreadFactory` naming threads `settlement-ingest-3` |
| 4 | threads/02 | the six `Thread.State` values; socket read reports RUNNABLE; BLOCKED vs WAITING in a dump; virtual-thread states | A thread in `CardPayments` blocked reading the PSP socket; twelve threads BLOCKED on one `FundsLedger` monitor; forty `getTask` waiters |
| 5 | threads/03 | interruption as a cooperative bit; the two legal responses; the interruptible inventory; cancellation by closing a socket | Cancelling an in-flight `DocumentVerification` call to the identity vendor (p99 38 s) when the operator abandons the `ReviewCase` |
| 6 | thread-safety/01 | the five-level taxonomy; the three kinds of confinement plus instance confinement; atomicity/visibility/ordering as independent; the four ways state escapes | `Money` immutable, `FundsLedger` thread-safe, `Collections.synchronizedList` conditionally; `Account` leaking its `List<Restriction>` |
| 7 | thread-safety/02 | race condition vs data race; `count++` as three logical steps; check-then-act; 64-bit tearing and word tearing; x86-TSO vs AArch64 | A stake-reservation counter going 41 → 42 instead of 43; `restrictions.containsKey(RestrictionKey(STAKE_BLOCKED, ADMIN))` then `put`; a torn 64-bit ledger balance |
| 8 | synchronized/01 | the two guarantees; the three monitors; reentrancy and why it is necessary; the wrong-lock-object family; block vs method bytecode | `FundsLedger.reserveStake` synchronized on `this` vs `FundsLedger.class`; a `private final Object lock`; `javap -c` of the reserve path |
| 9 | volatile-and-jmm/01 | what `volatile` gives and does not; the cache-flush myth; the hoisted stop flag; volatile on an array reference | A `volatile boolean draining` on a `PaymentRun` worker; `volatile Money[] buckets` over the four client positions |
| 10 | volatile-and-jmm/02a | the JMM as a contract; JLS 17.4.2 action tuples; the six synchronizes-with edges; happens-before as a transitive closure; DRF-SC | Publishing a `Reservation` from `PaymentService` to `FundsLedger`; the `j.u.c` edge from `BlockingQueue.put` to `take` on the withdrawal queue |
| 11 | volatile-and-jmm/02b | happens-before is not a timeline; benign data races; out-of-thin-air and 17.4.8; the four barrier categories; roach motel | The `r1 = x; y = r1` pair over two ledger positions; `System.out.println` accidentally fixing a racy `BonusService` test |
| 12 | volatile-and-jmm/03a | JLS 17.5 and the freeze action; "correctly constructed"; the four ways `this` escapes; unsafe publication showing defaults; the five safe-publication mechanisms | `StakeSplit(Money bonusPortion, Money cashPortion)` with its sum-exactly invariant; a `Reservation` published through a plain field showing `amount == null` |
| 13 | volatile-and-jmm/03b | broken and fixed DCL; the holder idiom and JVMS 5.5; the enum singleton; class-initialisation deadlock | `BonusService` as the lazily-initialised singleton; two mutually-referencing static initialisers in `ClientRestrictions` and `AccountActivation` |
| 14 | wait-notify/01 | `wait` releases exactly one monitor; the wait set and JLS 17.2; the `while` loop's two reasons; `notify` vs `notifyAll` and the lost wakeup | A bounded queue of `WithdrawalTransaction`s awaiting a `PaymentRun`, with two producers and two consumers in one wait set |
| 15 | atomics/01a | CAS and the retry loop; the progress guarantees; the 16-class inventory; `updateAndGet`'s may-run-twice contract; ABA | A stake-reservation counter at 3,400 settlements/sec; a Treiber stack of pending `WithdrawalTransaction`s for the ABA walk-through with stamps 7 → 8 → 9 |
| 16 | atomics/01b | `LongAdder`/`Striped64` at the API level; the `AtomicLong`/`LongAdder` crossover; the `VarHandle` access-mode taxonomy; the four ordering levels; `ThreadLocalRandom` | The 3,400/sec settlement counter as a `LongAdder`; `DoubleAdder`'s non-reproducible sum over `Money` amounts |
| 17 | locks/01a | the `lock`/`try`/`finally` idiom; fairness vs barging; multiple `Condition`s on one lock; read-write locks and the upgrade deadlock | One `ReentrantLock` guarding a wallet's four buckets; `notFull`/`notEmpty` on the withdrawal queue; a `ClientRestrictions` cache read-dominated at 99 % |
| 18 | locks/01b | the `StampedLock` optimistic-read protocol; its three traps; the park permit | A cached `LimitSet(dailyDeposit, maxStake, monthlyLoss)` snapshot read optimistically on every stake |
| 19 | synchronizers/01 | the two latch shapes; the broken barrier; semaphore permits are unowned; `Phaser` vs the other two; the `j.u.c` happens-before edges | A start gate for a 1,200/sec load test; a phase barrier across a `PaymentRun`'s four windows/day; `Semaphore(20)` in front of the connection pool |
| 20 | concurrent-collections/01a | why `synchronizedMap` is not enough; the three iterator-consistency models; why CHM forbids null; the atomic compound API; `computeIfAbsent` under the bin lock | A `ConcurrentHashMap<ClientId, ClientRestrictions>` over 2.4M registered clients; `merge(clientId, 1L, Long::sum)` counting stake reservations |
| 21 | concurrent-collections/01b | `ConcurrentSkipListMap` and its O(n) `size()`; copy-on-write's O(n) write; there is no concurrent `List`; views vs copies vs snapshots | A `CopyOnWriteArrayList` of `NotificationService` listeners (right) versus 2.8M stake appends (a disaster) |
| 22 | queues/01 | the four method families; one lock vs two; `SynchronousQueue`'s zero capacity; every queue must have a bound; the full producer–consumer assembly | `WithdrawalTransaction`s feeding a `PaymentRun`: 7k/day bank withdrawals, batched, with poison pills equal to the consumer count |
| 23 | executors/01 | task submission decoupled from execution policy; the interface stack and `AutoCloseable` (19); `submit` swallows the exception; `CompletionService`; two-phase shutdown | `AssessmentService` fanning out to the identity vendor and the watchlist provider; results in completion order |
| 24 | executors/02a | the four-step submission algorithm and the double-check; the `newFixedThreadPool` and `newCachedThreadPool` traps; the four rejection policies | A settlement pool at 3,400/sec burst; `Integer.MAX_VALUE` queue filling the heap with queued stake settlements |
| 25 | executors/02b | the dynamic knobs and hooks; pool sizing from Little's law; `availableProcessors()` in a container; starvation by task dependency | 8 cores, U = 0.9, W = 100 ms, C = 2 ms → 367; a `beforeExecute` hook restoring MDC for the `ApplicationGateway` |
| 26 | executors/03 | fixed rate vs fixed delay; one exception cancels every future run; the scheduler is effectively fixed-size; `setRemoveOnCancelPolicy` | The bonus-expiry sweep (30 days from grant) scheduled every 5 s, with one run overrunning to 12 s |
| 27 | completable-future/01a | the three shapes and which thread runs the callback; `thenApply` vs `thenCompose`; `allOf`/`anyOf`; the exception family and wrapping | The affordability assessment chain: look up the `Client`, fetch the `Wallet`, combine with `LimitSet`; identity failing at 300 ms beating the watchlist at 1.4 s |
| 28 | completable-future/01b | the common-pool trap and the parallelism < 2 fallback; timeouts that do not cancel; `cancel(boolean)` ignoring its argument; `minimalCompletionStage` | The same assessment chain with an explicit `AssessmentService` executor at every stage, `orTimeout` against the watchlist's 30 s timeout |
| 29 | fork-join/01 | the divide-and-conquer skeleton; LIFO-local / FIFO-steal; the common pool's width; `ManagedBlocker`; the sequential threshold | A parallel fold over one day's ~19.8M `LedgerEntry` rows to reconcile `HOUSE_REVENUE` |
| 30 | thread-local/01 | `ThreadLocal` lives in the Thread; the two halves of the pool leak; `InheritableThreadLocal`'s wrong timing; the virtual-thread warning | A per-request security context for client 2 401 993 leaking into the next request on the same pool thread |
| 31 | virtual-threads/01 | scale not speed; mounting and unmounting; the carrier pool; pinning on 21 and JEP 491 on 24; never pool, bound with a `Semaphore` | 55k peak concurrent sessions costed both ways; the Netflix tracing-library pinning incident; `Semaphore(20)` in front of the connection pool |
| 32 | structured-concurrency/01 | a scope is a tree with a lifetime; `ShutdownOnFailure` vs `allOf`; `Subtask` states and the illegal calls; `ScopedValue` vs `ThreadLocal` | `AssessmentService` forking the identity vendor (p50 900 ms) and the watchlist provider (p50 1.4 s) under one scope |
| 33 | liveness/01 | the four Coffman conditions and which fix breaks which; the transfer deadlock and the tie lock; livelock/starvation/convoy; what the detector cannot see | `transfer(accountA, accountB)` racing its mirror between two client accounts; a poison `WithdrawalTransaction` redelivered forever |
| 34 | 90-interview-basics | Part 1 summary table; 10 Q&As at spoken length; 5 predict-the-output puzzles | Draws only on entities already used in rows 1–33 |
| 35 | master-tables/01 | the master cost table; the latency ladder; the memory-footprint table; the guarantee table; the progress table; the escalation ladder | Every row costed against QuizStakes volumes: 1,200 reservations/sec, 3,400 settlements/sec, 2.8M/day |
| 36 | locks/03 | the contention cost model; the lock word ping-pong; splitting vs striping; the contention cliff; uncontended locks are not slow | One `state` lock over `Account` split into a restrictions lock and a balances lock; Amdahl's 20× ceiling for a 5 % critical section |
| 37 | locks/02 | the eight-row `synchronized` vs `ReentrantLock` table; when RW-lock and `StampedLock` earn their keep; the escalation ladder; the price of fairness | Choosing a primitive for `FundsLedger.reserveStake` vs a `ClientRestrictions` read cache at 99 % reads |
| 38 | executors/04 | the CPU- and I/O-bound formulas derived from Little's law; sizing the queue; the four-parameter matrix; `availableProcessors()` in a container; queue time vs execution time | 8 cores × 0.9 × 51 = 367; a 1000-deep queue in front of a 50 ms service; a 0.5-CPU cgroup reporting 1 |
| 39 | atomics/02 | five ways to count; the `AtomicLong`/`LongAdder` crossover; compute-under-the-bin-lock workarounds; the immutable-snapshot-in-an-`AtomicReference` pattern | The 3,400/sec settlement counter; a `WalletSnapshot` record holding all four buckets swapped by one `compareAndSet` |
| 40 | concurrent-collections/02 | the four-way map table; the queue selection table; the three concurrent `Set` options; bulk ops are not atomic; views/copies/snapshots | The `ClientRestrictions` map, the `NotificationService` listener registry, the withdrawal work list — three different right answers |
| 41 | queues/02 | the four backpressure mechanisms; blocking the producer only works if it is the source; `drainTo` batching; total vs per-key ordering | A three-stage withdrawal pipeline with its own bounded queue per stage; per-`ClientId` partitioning of settlements |
| 42 | completable-future/02 | the executor discipline made enforceable; the thread-hop cost; context does not follow a hop; "first successful" by hand; the debuggability argument | The five-stage affordability assessment with MDC trace ids and 20 async hops costed |
| 43 | virtual-threads/02 | the migration checklist; the `ThreadLocal` cache regression (200 → 443 267); downstream resource exhaustion; residual pinning after JEP 491; the CLOSE_WAIT signature | 14 000 concurrent sessions hitting a 20-connection pool; `ulimit -n` as the new bound |
| 44 | thread-safety/03 | the design sequence; when delegation is valid and when it is not; the private lock argument; client-side locking's failure mode; the racy-single-check idiom | `LimitSet(dailyDeposit, maxStake, monthlyLoss)` with a `dailyDeposit <= monthlyLoss` constraint that delegation cannot preserve |
| 45 | thread-local/02 | the five propagation mechanisms; MDC's mandatory `finally`; the leak audit; `ThreadLocal` as context never as cache | The `ApplicationGateway` trace id crossing an `AssessmentService` executor boundary |
| 46 | observability/01 | why unit tests do not find concurrency bugs; the latch harness; jcstress and the Dekker litmus test; JMH `@Group`; static analysis | A stress test over `FundsLedger.reserveStake` asserting the `StakeSplit` sum invariant at 8 threads × 1,000,000 |
| 47 | utility-surface/01 | `nanoTime` as the only correct deadline basis; overflow-safe deadline arithmetic; `ThreadMXBean`; `Flow` and `defaultBufferSize() = 256`; the parallel array utilities | A 30 s watchlist timeout written as `System.nanoTime() - deadline >= 0` |
| 48 | beyond-one-jvm/01 | every primitive's distributed analogue; why a distributed lock needs a fencing token; `@Version` as the CAS of the persistence layer; the duplicated scheduled job | A `PaymentRun` lease held across a GC pause, with fencing tokens 33 and 34 |
| 49 | version-delta/01 | the Java 5 → 25 timeline; JEP 374, 444, 491, 506, 505, 450/519; the deprecation graveyard; the interview rule on stating direction | No new domain material; reuses the entities of rows 1–48 |
| 50 | 91-interview-intermediate | Part 2 summary table; 10 Q&As; 5 puzzles | Draws only on entities already used in rows 35–49 |
| 51 | synchronized/02 | the 64-bit object layout; the multiplexed mark word; identity hash forcing a state change; compact object headers (24 experimental / 25 default) | A `Reservation` instance laid out byte by byte |
| 52 | synchronized/03 | lightweight locking and the displaced header; what forces inflation; the `ObjectMonitor` two-queue design; adaptive spinning; biased locking is gone | Contenders on the `FundsLedger` monitor pushed onto `_cxq`; `Object.wait` on the withdrawal queue moving a thread to `_WaitSet` |
| 53 | volatile-and-jmm/04 | lock elision and coarsening; hoisting the non-volatile read; what `volatile` compiles to per architecture; x86-TSO; AArch64 | A non-escaping `StringBuilder` building an audit line; the missing-`volatile` `draining` flag on Graviton |
| 54 | volatile-and-jmm/05 | what a safepoint is; TTSP as distinct from pause; the guaranteed interval; safepoint bias in profilers; virtual threads and safepoints | A `-Xlog:safepoint*` triple during a nightly ledger reconciliation over 19.8M rows |
| 55 | locks/04a | AQS's contract and the five template methods; what `state` means per synchronizer; the CLH variant; the backwards-from-tail walk; the acquire loop; shared-mode propagation | `ReentrantLock` guarding a wallet; `Semaphore(3)` with five waiters cascading |
| 56 | locks/04b | `ConditionObject`'s second queue and the transfer; full release on `await`; fair vs unfair `tryAcquire`; why `StampedLock` is not AQS-based; the mapping table | The withdrawal queue's `notFull`/`notEmpty` conditions with hold count 2 saved and restored |
| 57 | locks/05 | the permit model; the three reasons `park` returns; the Linux `Parker`/futex path; `park(Object blocker)` and the dump line; virtual-thread `park` | A `PaymentRun` worker parked on the withdrawal queue, shown as `parking to wait for <0x…>` |
| 58 | volatile-and-jmm/06 | the JMM as a constraint on executions; happens-before consistency's two clauses; the committed-sets construction; the five litmus tests; IRIW; final-field formalisation; the cookbook table | Two ledger positions in the store-buffering test; `StakeSplit`'s final fields in the freeze walk-through |
| 59 | concurrent-collections/03a | CAS-install then bin lock; the named constants and `spread`; `sizeCtl`'s four meanings; `initTable`; cooperative strided `transfer`; the lo/hi split | The 2.4M-client `ClientRestrictions` map resizing 16 → 32 with two threads helping |
| 60 | concurrent-collections/03b | treeify at 8 / untreeify at 6 / only above 64; `TreeBin`'s list-and-tree duality; `baseCount` + `CounterCell[]`; `ReservationNode`; the traverser; per-entry cost | The same restriction map: bin cost arithmetic at 2.4M entries |
| 61 | atomics/03 | `Striped64`'s structure and probe; growth to NCPU; `@Contended`; false sharing and the 128-byte pad; the racy `sum()`; why `LongAdder` has no CAS | The 3,400/sec settlement counter's cells; `a[0]`/`a[1]` vs `a[0]`/`a[16]` measured |
| 62 | executors/05a | the Michael–Scott queue and the lagging tail; the self-link trick; GC as the reclamation scheme; the dual-queue design; `ArrayBlockingQueue` vs `LinkedBlockingQueue` internals; the leader thread | The withdrawal queue's internals; `DelayQueue` behind the bonus-expiry sweep |
| 63 | executors/05b | `ctl`'s bit packing; the run-state graph; `Worker` as an AQS lock; `runWorker`/`getTask`; `DelayedWorkQueue`; `FutureTask`'s state machine; `CompletableFuture`'s Treiber stack | The settlement pool's `ctl` read during a `shutdownNow` |
| 64 | fork-join/02 | the `WorkQueue` array and deque protocol; `ctl` in 64 bits; `helpJoin`; compensation and `ManagedBlocker`; `CountedCompleter`; the two real production bugs | A parallel fold over 95k card deposits with `CountedCompleter` |
| 65 | virtual-threads/03a | delimited continuations; `VirtualThread`'s fields and internal state machine; mounting and freeze/thaw with lazy copy; `StackChunk` as a GC'd object; the scheduler; the park path | A virtual thread calling the card PSP at 240 ms p50, unmounting and resuming on a different carrier |
| 66 | virtual-threads/03b | the poller for sockets and the file-I/O gap; pinning implementation and JEP 491; why `jstack` cannot see them; the JSON dump structure; cost arithmetic; `ThreadFlock` and `ScopedValue` internals | 1M × 2 KB = 2 GB written out; `jcmd Thread.dump_to_file -format=json` over the assessment scopes |
| 67 | observability/02 | the annotated `jstack` dump; the three dump signatures; `nid` to `top -H`; the JFR event set and its thresholds; what none of them can show | A real contention dump on the `FundsLedger` monitor; the 20 ms `jdk.JavaMonitorEnter` threshold hiding short frequent contention |
| 68 | 92-interview-internals | Part 3 summary table; 10 Q&As; 5 puzzles; a pointer to the set-wide checklist in `94f` | Draws only on entities already used in rows 51–67 |
| 69 | build-it/01 | TAS and TTAS; the ticket lock; CLH vs MCS spin location; backoff; a reentrant mutex on `AtomicReference<Thread>` | Every lock guards `FundsLedger.reserveStake`; measured at 1/2/8/64 threads with 100 ns and 100 µs sections |
| 70 | build-it/02 | `SimpleMutex` on AQS; `CountingSemaphore` in shared mode; `OneShotLatch`; the reentrant variant; a fair variant; a `Condition` | The same reserve-stake critical section, and a bounded withdrawal buffer on the hand-built condition |
| 71 | build-it/03 | `wait`/`notifyAll` version; two-`Condition` version; two-lock version; timed `offer`/`poll` with `awaitNanos`; `drainTo`; the SPSC ring | A bounded queue of `WithdrawalTransaction`s, capacity 1,000 |
| 72 | build-it/04 | `TreiberStack` and the ABA demo; why plain Java is usually ABA-safe; `MichaelScottQueue` and linearization; a mini `Striped64`; a CoW list; a mini CHM | The pending-withdrawal stack, the settlement queue, the 3,400/sec counter |
| 73 | build-it/05 | v1 workers over a queue; v2 your own `Future`; v3 packed `ctl` and the four-step algorithm; v4 core/max and rejection; v5 hooks; a `ThreadFactory`; a context-propagating decorator; a `CompletionService` | The settlement pool rebuilt, named `settlement-ingest-N` |
| 74 | build-it/06 | the work-stealing deque and the single unavoidable CAS; growing without losing steals; `MiniForkJoinPool`; `MiniRecursiveTask` and help-by-executing | A parallel sum over one day's `LedgerEntry` rows and a parallel merge sort of `WithdrawalTransaction`s |
| 75 | build-it/07 | `MiniScope` with owner and LIFO checks; shutdown-on-failure; shutdown-on-success for hedging; `joinUntil` and its honest limitation; a minimal `CompletableFuture` | The two-vendor assessment fan-out rebuilt from scratch |
| 76 | build-it/08 | the visibility harness; the lost-update harness; deadlock/livelock/starvation harnesses; the false-sharing harness; the `ThreadLocal` leak harness; the pinning harness; the backpressure harness | 8 threads × 1,000,000 increments on a stake-reservation counter; a fast producer and slow consumer over the withdrawal queue |
| 77 | 93-interview-build-it | Part 4 summary table; 10 Q&As; 5 puzzles | Draws only on entities already used in rows 69–76 |
| 78 | 94a | 33 fundamentals questions with full spoken-length answers | Reuses the entities of Part 1 |
| 79 | 94b | 27 lock, synchronizer and atomic questions | Reuses the entities of Parts 1 and 3 |
| 80 | 94c | 31 collection, executor and future questions | Reuses the entities of Parts 1 and 3 |
| 81 | 94d | 24 liveness, diagnostic and Loom questions | Reuses the entities of Parts 1, 2 and 3 |
| 82 | 94e | 17 design-and-judgement questions | Reuses the entities of Part 4 |
| 83 | 94f | the 55-item trap index; the ten drills; Part 5's wrap-up; the flat set-wide `## Atomic concept checklist` | No new domain material |

---

## Leaf ledger

Every syllabus section, its leaf range, its leaf count, and the file that owns it. The union is
1141 leaves. An unassigned leaf is a planning bug, not a deferral.

| § | Leaves | Count | Owning file |
|---|---|---|---|
| §1.1 | 1.1.1–1.1.10 | 10 | `foundations/01-basics-why-concurrency.md` |
| §1.2 | 1.2.1–1.2.15 | 15 | `foundations/02-basics-os-substrate.md` |
| §1.3 | 1.3.1–1.3.18 | 18 | `threads/01-basics-thread-api.md` |
| §1.4 | 1.4.1–1.4.12 | 12 | `threads/02-basics-lifecycle-and-states.md` |
| §1.5 | 1.5.1–1.5.14 | 14 | `threads/03-basics-interruption.md` |
| §1.6 | 1.6.1–1.6.13 | 13 | `thread-safety/01-basics-vocabulary.md` |
| §1.7 | 1.7.1–1.7.12 | 12 | `thread-safety/02-basics-races.md` |
| §1.8 | 1.8.1–1.8.18 | 18 | `synchronized/01-basics.md` |
| §1.9 | 1.9.1–1.9.14 | 14 | `volatile-and-jmm/01-basics-volatile.md` |
| §1.10 | 1.10.1–1.10.13 | 13 | `volatile-and-jmm/02a-basics-happens-before.md` |
| §1.10 | 1.10.14–1.10.26 | 13 | `volatile-and-jmm/02b-basics-reordering-and-barriers.md` |
| §1.11 | 1.11.1–1.11.14 | 14 | `volatile-and-jmm/03a-basics-final-fields-and-publication.md` |
| §1.11 | 1.11.15–1.11.22 | 8 | `volatile-and-jmm/03b-basics-lazy-init-and-singletons.md` |
| §1.12 | 1.12.1–1.12.16 | 16 | `wait-notify/01-basics.md` |
| §1.13 | 1.13.1–1.13.15 | 15 | `atomics/01a-basics-cas-and-atomics.md` |
| §1.13 | 1.13.16–1.13.29 | 14 | `atomics/01b-basics-adders-varhandles-ordering.md` |
| §1.14 | 1.14.1–1.14.18 | 18 | `locks/01a-basics-reentrantlock-and-rwlock.md` |
| §1.14 | 1.14.19–1.14.29 | 11 | `locks/01b-basics-stampedlock-and-locksupport.md` |
| §1.15 | 1.15.1–1.15.18 | 18 | `synchronizers/01-basics.md` |
| §1.16 | 1.16.1–1.16.14 | 14 | `concurrent-collections/01a-basics-maps-and-iterators.md` |
| §1.16 | 1.16.15–1.16.24 | 10 | `concurrent-collections/01b-basics-sorted-cow-and-queues.md` |
| §1.17 | 1.17.1–1.17.18 | 18 | `queues/01-basics-blockingqueue.md` |
| §1.18 | 1.18.1–1.18.19 | 19 | `executors/01-basics-executor-framework.md` |
| §1.19 | 1.19.1–1.19.11 | 11 | `executors/02a-basics-threadpoolexecutor-submission.md` |
| §1.19 | 1.19.12–1.19.22 | 11 | `executors/02b-basics-threadpoolexecutor-tuning.md` |
| §1.20 | 1.20.1–1.20.10 | 10 | `executors/03-basics-scheduled-executors.md` |
| §1.21 | 1.21.1–1.21.14 | 14 | `completable-future/01a-basics-composition.md` |
| §1.21 | 1.21.15–1.21.27 | 13 | `completable-future/01b-basics-executors-timeouts-lifecycle.md` |
| §1.22 | 1.22.1–1.22.16 | 16 | `fork-join/01-basics.md` |
| §1.23 | 1.23.1–1.23.13 | 13 | `thread-local/01-basics.md` |
| §1.24 | 1.24.1–1.24.19 | 19 | `virtual-threads/01-basics-the-model.md` |
| §1.25 | 1.25.1–1.25.16 | 16 | `structured-concurrency/01-basics.md` |
| §1.26 | 1.26.1–1.26.20 | 20 | `liveness/01-basics-failures.md` |
| §2.1 | 2.1.1–2.1.8 | 8 | `master-tables/01-the-master-tables.md` |
| §2.2 | 2.2.1–2.2.14 | 14 | `locks/03-contention-economics.md` |
| §2.3 | 2.3.1–2.3.14 | 14 | `locks/02-choosing-a-primitive.md` |
| §2.4 | 2.4.1–2.4.18 | 18 | `executors/04-pool-sizing.md` |
| §2.5 | 2.5.1–2.5.10 | 10 | `atomics/02-the-atomicity-decision.md` |
| §2.6 | 2.6.1–2.6.14 | 14 | `concurrent-collections/02-the-collection-decision.md` |
| §2.7 | 2.7.1–2.7.12 | 12 | `queues/02-backpressure-design.md` |
| §2.8 | 2.8.1–2.8.14 | 14 | `completable-future/02-in-anger.md` |
| §2.9 | 2.9.1–2.9.14 | 14 | `virtual-threads/02-in-production.md` |
| §2.10 | 2.10.1–2.10.16 | 16 | `thread-safety/03-class-design.md` |
| §2.11 | 2.11.1–2.11.10 | 10 | `thread-local/02-context-propagation.md` |
| §2.12 | 2.12.1–2.12.14 | 14 | `observability/01-testing-and-verifying.md` |
| §2.13 | 2.13.1–2.13.16 | 16 | `utility-surface/01-the-adjacent-apis.md` |
| §2.14 | 2.14.1–2.14.8 | 8 | `beyond-one-jvm/01-distributed-analogues.md` |
| §2.15 | 2.15.1–2.15.16 | 16 | `version-delta/01-java-5-to-25.md` |
| §3.1 | 3.1.1–3.1.8 | 8 | `synchronized/02-internals-header-and-mark-word.md` |
| §3.2 | 3.2.1–3.2.18 | 18 | `synchronized/03-internals-monitors.md` |
| §3.3 | 3.3.1–3.3.12 | 12 | `volatile-and-jmm/04-internals-jit-and-barriers.md` |
| §3.4 | 3.4.1–3.4.10 | 10 | `volatile-and-jmm/05-internals-safepoints.md` |
| §3.5 | 3.5.1–3.5.13 | 13 | `locks/04a-internals-aqs-queue-and-acquire.md` |
| §3.5 | 3.5.14–3.5.22 | 9 | `locks/04b-internals-aqs-conditions-and-mappings.md` |
| §3.6 | 3.6.1–3.6.10 | 10 | `locks/05-internals-locksupport-and-os.md` |
| §3.7 | 3.7.1–3.7.15 | 15 | `volatile-and-jmm/06-internals-jmm-formally.md` |
| §3.8 | 3.8.1–3.8.12 | 12 | `concurrent-collections/03a-internals-chm-table-and-resize.md` |
| §3.8 | 3.8.13–3.8.24 | 12 | `concurrent-collections/03b-internals-chm-trees-counting-traversal.md` |
| §3.9 | 3.9.1–3.9.14 | 14 | `atomics/03-internals-striped64-and-false-sharing.md` |
| §3.10 | 3.10.1–3.10.11 | 11 | `executors/05a-internals-queue-internals.md` |
| §3.10 | 3.10.12–3.10.24 | 13 | `executors/05b-internals-executor-and-future-internals.md` |
| §3.11 | 3.11.1–3.11.16 | 16 | `fork-join/02-internals-work-stealing.md` |
| §3.12 | 3.12.1–3.12.11 | 11 | `virtual-threads/03a-internals-continuations-and-mounting.md` |
| §3.12 | 3.12.12–3.12.22 | 11 | `virtual-threads/03b-internals-io-pinning-and-dumps.md` |
| §3.13 | 3.13.1–3.13.12 | 12 | `observability/02-internals-runtime-observability.md` |
| §4.1 | 4.1.1–4.1.10 | 10 | `build-it/01-locks-from-first-principles.md` |
| §4.2 | 4.2.1–4.2.7 | 7 | `build-it/02-building-on-aqs.md` |
| §4.3 | 4.3.1–4.3.7 | 7 | `build-it/03-bounded-blocking-queue.md` |
| §4.4 | 4.4.1–4.4.11 | 11 | `build-it/04-non-blocking-structures.md` |
| §4.5 | 4.5.1–4.5.9 | 9 | `build-it/05-a-thread-pool-from-scratch.md` |
| §4.6 | 4.6.1–4.6.7 | 7 | `build-it/06-work-stealing-and-mini-forkjoin.md` |
| §4.7 | 4.7.1–4.7.6 | 6 | `build-it/07-structured-concurrency-and-futures.md` |
| §4.8 | 4.8.1–4.8.12 | 12 | `build-it/08-diagnostic-harnesses.md` |
| §5.1 | 5.1.1–5.1.33 | 33 | `94a-interview-questions-fundamentals.md` |
| §5.1 | 5.1.34–5.1.60 | 27 | `94b-interview-questions-locks-and-atomics.md` |
| §5.1 | 5.1.61–5.1.91 | 31 | `94c-interview-questions-collections-and-executors.md` |
| §5.1 | 5.1.92–5.1.115 | 24 | `94d-interview-questions-liveness-and-loom.md` |
| §5.1 | 5.1.116–5.1.132 | 17 | `94e-interview-design-and-judgement.md` |
| §5.2 | 5.2.1–5.2.55 | 55 | `94f-trap-index-and-drills.md` |
| §5.3 | 5.3.1–5.3.10 | 10 | `94f-trap-index-and-drills.md` |

**Totals check.** Part 1: 10+15+18+12+14+13+12+18+14+26+22+16+29+29+18+24+18+19+22+10+27+16+13+19+16+20 = **470**.
Part 2: 8+14+14+18+10+14+12+14+14+16+10+14+16+8+16 = **198**.
Part 3: 8+18+12+10+22+10+15+24+14+24+16+22+12 = **207**.
Part 4: 10+7+7+11+9+7+6+12 = **69**.
Part 5: 132+55+10 = **197**. Union = **1141**.

---

## Diagram ownership

The file that **owns** each id embeds it at the point of explanation. Where a manifest row lists
leaves belonging to more than one file, the other files may embed the same path — never a copy.

| Owner file | Diagram ids |
|---|---|
| `foundations/01` | D-001, D-002, D-003, D-004, D-005 |
| `foundations/02` | D-006, D-007, D-008, D-009 |
| `threads/01` | D-010, D-011, D-012 |
| `threads/02` | D-013, D-014, D-015 |
| `threads/03` | D-016, D-017, D-018 |
| `thread-safety/01` | D-019, D-020, D-021, D-022 |
| `thread-safety/02` | D-023, D-024, D-025, D-026 |
| `synchronized/01` | D-027, D-028, D-029, D-030 |
| `volatile-and-jmm/01` | D-031, D-032, D-033, D-034 |
| `volatile-and-jmm/02a` | D-036, D-037, D-038 |
| `volatile-and-jmm/02b` | D-035, D-039, D-040, D-041, D-042 |
| `volatile-and-jmm/03a` | D-043, D-044 |
| `volatile-and-jmm/03b` | D-045, D-046, D-047 |
| `wait-notify/01` | D-048, D-049, D-050 |
| `atomics/01a` | D-051, D-052, D-053 |
| `atomics/01b` | D-054, D-055, D-056 |
| `locks/01a` | D-057, D-058, D-059 |
| `locks/01b` | D-060, D-061, D-062 |
| `synchronizers/01` | D-063, D-064, D-065 |
| `concurrent-collections/01a` | D-066, D-067, D-070, D-071 |
| `concurrent-collections/01b` | D-068, D-069 |
| `queues/01` | D-072, D-073, D-074, D-075 |
| `executors/01` | D-076, D-077 |
| `executors/02a` | D-078, D-079, D-080 |
| `executors/02b` | D-081, D-082 |
| `executors/03` | D-083, D-084 |
| `completable-future/01a` | D-085, D-086, D-087, D-088, D-089, D-090 |
| `fork-join/01` | D-091, D-092 |
| `thread-local/01` | D-093, D-094 |
| `virtual-threads/01` | D-095, D-096, D-097, D-098, D-099 |
| `structured-concurrency/01` | D-100, D-101, D-102, D-103 |
| `liveness/01` | D-104, D-105, D-106 |
| `master-tables/01` | D-107, D-108, D-109, D-110, D-111 |
| `locks/03` | D-112, D-113, D-114, D-115 |
| `locks/02` | D-116, D-117, D-118 |
| `executors/04` | D-119, D-120, D-121 |
| `atomics/02` | D-122, D-123, D-124 |
| `concurrent-collections/02` | D-125, D-126 |
| `queues/02` | D-127, D-128, D-129 |
| `completable-future/02` | D-130, D-131 |
| `virtual-threads/02` | D-132, D-133, D-134 |
| `thread-safety/03` | D-135, D-136 |
| `thread-local/02` | D-137 |
| `observability/01` | D-138, D-139 |
| `utility-surface/01` | D-140 |
| `beyond-one-jvm/01` | D-141, D-142 |
| `version-delta/01` | D-143, D-144 |
| `synchronized/02` | D-145, D-146, D-147 |
| `synchronized/03` | D-148, D-149, D-150, D-151, D-152 |
| `volatile-and-jmm/04` | D-153, D-155 |
| `volatile-and-jmm/05` | D-156, D-157 |
| `locks/04a` | D-158, D-159, D-160, D-161, D-162, D-164 |
| `locks/04b` | D-163 |
| `locks/05` | D-165 |
| `volatile-and-jmm/06` | D-154, D-166, D-167, D-168 |
| `concurrent-collections/03a` | D-169, D-170, D-171, D-172 |
| `concurrent-collections/03b` | D-173, D-174, D-175 |
| `atomics/03` | D-176, D-177 |
| `executors/05a` | D-178 |
| `executors/05b` | D-179, D-180, D-181, D-182, D-183, D-184 |
| `fork-join/02` | D-185, D-186, D-187, D-188, D-189 |
| `virtual-threads/03a` | D-190, D-191 |
| `virtual-threads/03b` | D-192, D-193 |
| `virtual-threads/03c` | D-194 |
| `observability/02` | D-195, D-196, D-197, D-198 |
| `observability/03` | D-197 (re-embedded at the `/proc` walk; same file, never a copy) |
| `build-it/01` | D-199, D-201 |
| `build-it/01b` | D-200 |
| `build-it/02` | D-202 |
| `build-it/03` | D-203 |
| `build-it/03b` | D-204 |
| `build-it/04` | D-205 |
| `build-it/05` | D-206 |
| `build-it/06` | D-207 |
| `build-it/07` | D-208 |
| `build-it/08` | D-209, D-210 |
| `build-it/08c` | D-211, D-212 |
| `94f` | D-213, D-214, D-215, D-216, D-217, D-218 |

### Substitutions

None recorded yet. A `D-NNN` an illustrator reports as not renderable is recorded here with a
one-line reason, and its owning file renders a Markdown table at that point instead of an embed.

### Rendered as Markdown tables by manifest instruction (no SVG file)

The manifest's `Type` column says `table` for these 59 ids, so the owning file carries a Markdown
table and `diagrams/` holds no file for them:

D-005, D-011, D-017, D-019, D-022, D-027, D-029, D-031, D-033, D-036, D-038, D-039, D-046,
D-052, D-055, D-056, D-061, D-063, D-066, D-069, D-072, D-080, D-086, D-090, D-103, D-105,
D-106, D-107, D-109, D-110, D-115, D-116, D-119, D-122, D-126, D-127, D-136, D-137, D-138,
D-139, D-141, D-144, D-146, D-154, D-161, D-162, D-166, D-170, D-195, D-196, D-198, D-199,
D-203, D-210, D-212, D-213, D-214, D-215, D-218.

The remaining **159** ids are standalone SVGs in `diagrams/`.

---

## Open questions

Populated as writer and illustrator envelopes return `unverified` lines. Six figures are flagged by
the prompt's own research pass as needing re-verification before they are printed, and are carried
here from the outset:

1. `jdk.virtualThreadScheduler.maxPoolSize` defaulting to **256** (leaves 1.24.4, 2.9.9, 3.12.9) —
   **substantially settled.** A fetch of `VirtualThread.java` at jdk-21+35 gives the default as
   `Integer.max(parallelism, 256)`, which confirms the 256 figure. The fetch went through a
   summarising model rather than a literal line-numbered read, so
   `virtual-threads/03a-internals-continuations-and-mounting.md` still carries it as
   `**Unverified:**`. A direct read of the source line would close it.
2. `ForkJoinPool` common-pool `maximumPoolSize = 256 + parallelism` and `common.maximumSpares = 256`
   (3.11.9, 3.11.13) — **partially settled.** `ForkJoinPool.java` at jdk-21+35 confirms
   `DEFAULT_COMMON_MAX_SPARES = 256` and the RC/TC/SS/ID `ctl` bit layout. No `maximumPoolSize` or
   `minimumRunnable` **constant** exists in that source — they are constructor parameters, so the
   `256 + parallelism` figure is a documented default that could not be confirmed from source.
   D-188 labels it "documented default, unconfirmed"; any file quoting it must do the same.
3. The mark-word tag-bit encoding (3.1.3) and the `ObjectMonitor` field names (3.2.7) — confirm
   against the OpenJDK HotSpot `Synchronization Using The ObjectMonitorTable` wiki page.
4. The post-JDK-14 AQS bit-flag constants (3.5.9) — read from `AbstractQueuedSynchronizer.java` at
   the jdk-21 tag, and state which JDK's source is being described.
5. Every `ConcurrentHashMap` constant in 3.8.3 and 3.8.4 — re-read from `ConcurrentHashMap.java`,
   not from a secondary article.
6. The park/unpark and context-switch cost figures in 2.1.2 and 3.6.6 — **present as
   order-of-magnitude, explicitly stated as such, never as measured constants.** No authoritative
   per-instruction table was found during the prompt's research pass.

10. **Settled during this run, no longer open.** Verified against the per-release JEP listings on
    `javaalmanac.io`: JEP 491 (`synchronized` no longer pins) was **delivered final in JDK 24**;
    JEP 506 (scoped values) is **final in JDK 25**; structured concurrency is **still preview in
    JDK 25** (JEP 505, fifth preview); JEP 519 (compact object headers) is **delivered in JDK 25**,
    though whether it is on *by default* there remains unconfirmed by that source.

12. OpenTelemetry `Context`/`Scope` method names and Micrometer `ContextSnapshot` signatures
    (`captureAll`/`wrap`/`setThreadLocalsFrom`) in `thread-local/02-context-propagation.md` —
    WebFetch reached only landing pages, not the interface javadoc. Flagged `**Unverified:**`
    inline.

11. The USL σ and κ values (0.02, 0.0006) used in the worked contention-cliff illustration in
    `locks/03-contention-economics.md` are stated inline as illustrative, not measured production
    figures.

9. JEP 505's exact `Joiner` static factory names (`allSuccessfulOrThrow`,
   `anySuccessfulResultOrThrow`, `awaitAll`, `awaitAllSuccessfulOrThrow`) in
   `structured-concurrency/01-basics.md` — taken from the JEP text and corroborated by secondary
   sources, but structured concurrency was still preview at time of writing and JEP 525/533 may
   rename them. Re-check when the API finalises.

8. Container-specific `ThreadLocal` leak-detector behaviour on redeploy (leaf 1.23.7), and the
   interaction of `Thread.Builder.inheritInheritableThreadLocals(false)` with virtual-thread
   carrier re-mounting (leaf 1.23.11) — both flagged `**Unverified:**` inline in
   `thread-local/01-basics.md`.

7. The JDK 27 removal timeline for the empty `ThreadPoolExecutor.finalize()` method (leaf 1.19.22,
   `executors/02b`) — sourced from an `inside.java` quality-outreach post, not a shipped release
   note, because JDK 27 has not released. Re-check when it does.

`openjdk.org` returned HTTP 403 to every direct fetch during the prompt build. Re-fetch every JEP
through a mirror (`javaalmanac.io`, `bugs.openjdk.org`, `cr.openjdk.org`) or use the JDK release
notes and the `openjdk/jdk` repository before quoting JEP text verbatim.

---

## Diagram manifest (from prompt)

Copied verbatim from `# DIAGRAM MANIFEST` of the source prompt, so that a resumed run never needs
the prompt to know what a `D-NNN` depicts.

Rules the manifest assumes and you must follow:

- One idea per diagram. Prefer more, smaller diagrams over one dense one.
- Where the `Must show` column asks for *frames*, produce that many clearly separated,
  individually labelled panels inside the one SVG, each captioned with the frame number and what
  changed since the previous frame.
- Every label, constant and value named in `Must show` must be visible as text in the SVG. A
  diagram that omits a named value does not satisfy the manifest.
- Arrows must be directional, orthogonal, and labelled where the direction is not obvious.
- Every diagram is drawn on QuizStakes data. Where the `Must show` cell names domain values
  (`CLIENT_BONUS_AVAILABLE`, 1,200 reservations/sec, a 3.33 stake, the 240 ms PSP p50), use those
  exact values.
- Two-thread interleaving diagrams get a time axis running downwards with one lane per thread, and
  every step numbered so the reader can replay it.
- Never inline `<svg>` in the Markdown. Never draw with ASCII characters.

## Part 1 diagrams

| # | Diagram | Syllabus leaf | Type | Must show |
|---|---|---|---|---|
| D-001 | Concurrency is structure, parallelism is execution | 1.1.3 | before-after | The same four stake-settlement tasks on a single core (interleaved slices on one timeline, "concurrent, zero parallelism") and on four cores (four lanes, "concurrent and parallel"). Total wall time written on both |
| D-002 | Amdahl's law with S = 0.05 | 1.1.5 | cost-curve | Speedup on the y axis against N on the x axis for S = 0.05, with the points N = 1, 2, 8, 64 plotted, the value **15.4×** labelled at N = 64, the asymptote 1/S = 20 drawn as a dashed line, and the formula `1 / (S + (1−S)/N)` printed |
| D-003 | The USL turns downward where Amdahl flattens | 1.1.6 | cost-curve | Both curves on one axis: Amdahl asymptotic to 20, USL peaking and then falling. The σ (contention) and κ (coherence) terms labelled on the USL curve, and the peak thread count marked "adding threads past here makes it slower" |
| D-004 | Little's law sizes the pool | 1.1.7, 1.24.19, 2.4.2 | cost-curve | L = λW plotted for QuizStakes: 1,200 stake reservations/sec at the PSP's 240 ms p50 → **288** concurrent tasks; at the 11 s p99 → **13,200**. A horizontal line at a 200-thread platform pool showing where throughput caps, and the virtual-thread line with no cap in that range |
| D-005 | Four ways a server gets its thread count | 1.1.8 | table | Rows: thread per connection, bounded pool, thread per request on virtual threads, event loop. Columns: threads at 55k peak concurrent sessions, memory, blocking allowed, code style, failure mode when overloaded |
| D-006 | What threads share and what they own | 1.2.3, 1.2.4 | memory-layout | One process box containing the shared region (heap with a `FundsLedger` instance, static fields, metaspace, code cache, fd table) and three thread boxes each owning a stack, PC, registers and TLS. A `Money stake` local drawn inside one stack; an arrow from that local to a shared `Reservation` on the heap labelled "the reference is confined, the object is not" |
| D-007 | What a context switch actually costs | 1.2.6, 1.2.7 | step-sequence, 4 frames | Frame 1: thread A running, its working set in L1/L2. Frame 2: registers saved, stack pointer switched. Frame 3: thread B runs with a cold cache. Frame 4: A resumes and refills. Direct cost ~1–10 µs and cache-refill penalty of tens of µs written on the frames; `vmstat cs` and `voluntary_ctxt_switches` named as the counters |
| D-008 | A platform thread's real footprint | 1.2.8, 1.2.9 | memory-layout | One thread drawn across four regions: ~1 MB reserved stack (virtual, committed page by page) plus a guard page, the ~1 KB `java.lang.Thread` heap object, the JVM `JavaThread`, the OS `task_struct`. Beneath: 10 000 threads ≈ 10 GB reserved address space, arithmetic shown |
| D-009 | Where the thread limit comes from | 1.2.15 | decision-tree | Four gates in series — `ulimit -u`, `/proc/sys/kernel/threads-max`, `pid_max`, container `pids.max` — with the failure at each one ending in `OutOfMemoryError: unable to create native thread`. Heap exhaustion drawn as a separate, different cause |
| D-010 | `start()` versus `run()` versus `start()` twice | 1.3.2, 1.3.3 | before-after | Left: `t.start()` — a new OS thread appears and `run` executes on it. Middle: `t.run()` — no new thread, `run` executes on the caller, both frames on one stack. Right: a second `t.start()` — the exact exception `java.lang.IllegalThreadStateException` printed, with a callout that it is **not** `IllegalStateException` |
| D-011 | The `Thread.Builder` surface | 1.3.11, 1.3.12 | table | Rows: `Thread.ofPlatform()`, `Thread.ofVirtual()`, `Thread.startVirtualThread`, `new Thread(Runnable)`. Columns: `name`/`name(prefix,start)`, `daemon`, `priority`, `stackSize`, `inheritInheritableThreadLocals`, `uncaughtExceptionHandler`, `unstarted`, `start`, `factory` — with "throws" or "ignored" written in every cell a virtual thread rejects |
| D-012 | The `Thread` deprecation and removal timeline | 1.3.14, 2.15.16 | timeline | An axis from Java 1.2 to Java 21 with markers: `stop`/`suspend`/`resume` deprecated (1.2), `ThreadGroup.stop` removed, `countStackFrames` degraded, `getId` deprecated (19), `threadId()` added (19), `stop`/`suspend`/`resume` **removed** in 20 throwing `UnsupportedOperationException`. Each marker carries the release number |
| D-013 | The six `Thread.State` values and every transition | 1.4.1–1.4.8 | state-transition | Six state boxes with every edge labelled by the call that causes it: `start()`, scheduler dispatch, `monitorenter` contention, `wait()`, `notify()`, `sleep`/`join(t)`/`parkNanos`, timeout expiry, `run` returning. The `wait` → **BLOCKED** → `RUNNABLE` path drawn explicitly and labelled "a notified thread must re-acquire the monitor" |
| D-014 | A socket read reports RUNNABLE | 1.4.3 | before-after | Left, what the reader expects: a thread in `SocketInputStream.read` shown as BLOCKED. Right, what the dump says: the same stack with `java.lang.Thread.State: RUNNABLE` quoted verbatim, and the OS-level state "descheduled, invisible to the JVM" beside it |
| D-015 | BLOCKED versus WAITING in a dump | 1.4.9, 3.13.2 | before-after | Left: twelve threads BLOCKED on the same `<0x00000000d5f5b1a8>` monitor with one owner named — labelled "contention incident, find the owner". Right: forty threads WAITING in `getTask` on a pool queue — labelled "normal idle". The distinguishing dump lines quoted on both |
| D-016 | The interrupt flag is a bit, not an event | 1.5.1–1.5.4 | state-transition | The flag as a single boolean with edges: `interrupt()` sets it; `isInterrupted()` reads it; static `Thread.interrupted()` reads **and clears**; a blocking method throwing `InterruptedException` **clears** it. A red path for `catch (InterruptedException e) { }` ending in "the cancellation request no longer exists" |
| D-017 | What is interruptible and what is not | 1.5.5, 1.5.6 | table | Rows: `Object.wait`, `Thread.sleep`, `Thread.join`, `BlockingQueue.put/take`, `Lock.lockInterruptibly`, `Condition.await`, `Semaphore.acquire`, `CountDownLatch.await`, `CyclicBarrier.await`, `Future.get`, `LockSupport.park`, `InterruptibleChannel` ops, `Selector.select`, `synchronized` acquisition, `InputStream.read` on a plain socket, `FileChannel` read. Columns: throws / returns / ignores, does it clear the flag, how you cancel it instead |
| D-018 | The two legal responses to `InterruptedException` | 1.5.4, 1.5.13 | decision-tree | Root: "can your method declare `throws InterruptedException`?" Yes → propagate. No → `Thread.currentThread().interrupt()` in the catch, then return. A third branch, swallow, marked as always a bug with the symptom "a `shutdownNow` that never stops anything" |
| D-019 | The five-level thread-safety taxonomy | 1.6.3 | table | Rows: immutable, thread-safe, conditionally thread-safe, thread-compatible, thread-hostile. Columns: what the caller must do, a JDK example, a QuizStakes example (`Money` immutable, `FundsLedger` thread-safe, `Collections.synchronizedList` conditionally, `ArrayList` compatible, a class that mutates static state hostile), and how the javadoc should say it |
| D-020 | Three kinds of confinement | 1.6.5, 1.6.6 | hierarchy | Ad-hoc (convention only, drawn dashed and labelled fragile), stack confinement (a `StakeSplit` local inside `FundsLedger.reserveStake`, unreachable from other stacks), `ThreadLocal` (a per-thread slot). A fourth box, instance confinement, with a private `final Object lock` guarding the state and no reference escaping |
| D-021 | The four ways state escapes | 1.6.10, 1.11.4 | before-after | One `Account` aggregate drawn four times: returning the internal `List<Restriction>`, storing it in a public field, passing it to an alien listener, and `this` escaping from the constructor via a registration call. Each panel shows the external reference that now aliases internal state, and the defensive fix beneath it |
| D-022 | Atomicity, visibility and ordering are independent | 1.6.9, 2.1.4 | table | Rows: plain field, `volatile`, `AtomicLong`, `synchronized`, `final`, opaque, release/acquire. Columns: atomicity (and for which widths), visibility, ordering, mutual exclusion, progress. Every cell yes/no/partial with the one-clause reason |
| D-023 | `count++` is three logical steps | 1.7.2 | step-sequence, 3 frames | The bytecode `getfield` / `iconst_1` / `iadd` / `putfield` listed, then two threads incrementing a stake-reservation counter from 41: frame 1 both read 41, frame 2 both compute 42, frame 3 both write 42. Final value 42 instead of 43, with the lost update labelled |
| D-024 | Check-then-act loses the race | 1.7.3, 1.7.7 | step-sequence, 3 frames | Two threads running `if (!restrictions.containsKey(key)) restrictions.put(key, r)` for `RestrictionKey(STAKE_BLOCKED, ADMIN)`. Frames show both checks passing, then both puts, and the second overwriting the first. Beside it: both check and act inside one `synchronized` block on the same lock |
| D-025 | A non-volatile `long` can tear | 1.7.8, 1.7.9 | before-after | Left: a 64-bit ledger balance written as two 32-bit halves, a reader observing the new high word and the old low word, with the composed nonsense value written out. Right: word tearing forbidden by JLS 17.6 — a `byte[]` where writing index 3 must not disturb index 2 or 4. References labelled "always atomic" |
| D-026 | x86-TSO hides the bug that AArch64 exposes | 1.7.10, 3.3.8, 3.3.9 | before-after | The same publication code on both architectures. Left, x86-TSO: only StoreLoad reordering permitted, the bug invisible. Right, AArch64: StoreStore and LoadLoad both permitted, the reader seeing the reference before the fields, with the observed default values printed. "It works on my machine" written on the left panel |
| D-027 | The three monitors `synchronized` can take | 1.8.6, 1.8.7 | table | Rows: `synchronized void reserve()` → `this`; `static synchronized void audit()` → `FundsLedger.class`; `synchronized (lock) { }` → the named object. Columns: which monitor, what it excludes, what it does **not** exclude, and the instance-vs-static non-exclusion stated as its own row |
| D-028 | Block versus method: two different bytecode shapes | 1.8.11, 1.8.12 | before-after | Left: `javap -c` of a synchronized block showing `monitorenter`, the body, `monitorexit`, and the **synthetic exception handler** with its second `monitorexit`, with the exception table printed. Right: `javap -v` of a synchronized method showing only the `ACC_SYNCHRONIZED` flag and no monitor bytecodes |
| D-029 | Four ways to lock on the wrong object | 1.8.8, 1.8.9, 1.8.10 | table | Rows: a non-final lock field reassigned, a `String` literal, a boxed `Integer` in −128..127, `Boolean.TRUE`, a `Class` you do not own, two threads on different lock objects. Columns: what the reader believes, what actually happens, the observable symptom, and the fix (`private final Object lock = new Object();`) |
| D-030 | Unlock happens-before the next lock | 1.8.3, 1.10.8 | timeline | Two lanes over one time axis. Thread A writes `CLIENT_CASH_AVAILABLE`, then unlocks monitor m. Thread B locks m, then reads. One labelled happens-before edge from the unlock to the lock, and a second arrow showing that *everything before* the unlock is visible after the lock — not just the guarded field |
| D-031 | What `volatile` gives and what it does not | 1.9.1, 1.9.4, 1.9.8 | table | Rows: visibility of a single field, ordering with surrounding accesses, 64-bit atomicity, compound `count++`, array elements through a volatile reference, fields of a referenced mutable object. Columns: guaranteed / not guaranteed, the reason, and the correct alternative (`AtomicInteger`, `AtomicIntegerArray`, a lock) |
| D-032 | The missing-`volatile` stop flag never stops | 1.9.7, 3.3.5 | before-after | Left: the source loop reading `running` each iteration, and the C2-hoisted form with the read lifted out and the loop reduced to `while (true)`, drawn as pseudo-assembly. Right: the same source with `volatile`, the read staying inside the loop. Both annotated with what the reader observes |
| D-033 | Volatile read is free; volatile write is not | 1.9.12, 3.3.6 | table | Rows: x86-64 volatile read, x86-64 volatile write, AArch64 volatile read, AArch64 volatile write, plain read, plain write, uncontended CAS. Columns: the instruction emitted (`mov`, `mov` + `lock addl $0,(%rsp)`, `ldar`, `stlr`, `lock cmpxchg`), the barrier it implements, and the cost from the latency ladder |
| D-034 | `volatile` on an array reference protects only the reference | 1.9.9 | memory-layout | A `volatile Money[] buckets` field pointing at an array of four elements (`CLIENT_CASH_AVAILABLE`, `CLIENT_CASH_RESERVED`, `CLIENT_BONUS_AVAILABLE`, `CLIENT_BONUS_RESERVED`). The reference slot shaded "volatile"; the four element slots shaded "plain". `AtomicReferenceArray` and `VarHandle` named as the fixes |
| D-035 | Happens-before is a partial order, not a timeline | 1.10.14, 1.10.15 | before-after | Left: two actions with an hb edge, drawn with the ordering constraint. Right: two actions with no edge, drawn as an unordered pair with both execution orders shown and both legal. A banner: "hb constrains visibility, not wall-clock order" |
| D-036 | The six synchronizes-with edges | 1.10.8 | table | Rows: unlock/lock on the same monitor, volatile write/read of the same field, `Thread.start()`, default initialisation, thread termination detection (`join`, `isAlive`), interrupt/detect-interrupt. Columns: the JLS 17.4.4 clause, the two actions, and the QuizStakes example that relies on it |
| D-037 | The derived happens-before edges you actually use | 1.10.9, 1.10.10 | hierarchy | The four base rules (program order, synchronizes-with, transitivity, the constructor/finalizer edge) as roots, with every commonly-cited "rule" drawn as a derived corollary hanging off them: monitor, volatile, `start`, `join`, default init, final-field freeze, and the `j.u.c` edges |
| D-038 | The `java.util.concurrent` happens-before edges | 1.10.11, 1.15.16 | table | Rows quoted from the package summary: place into a concurrent collection → removal; `Runnable` submission → execution start; the async computation → `Future.get`; `Lock.unlock` → subsequent `lock`; `Semaphore.release` → `acquire`; `CountDownLatch.countDown` → `await` return; `Exchanger.exchange` pairs; pre-`await` actions → barrier action → post-`await`. Columns: the releasing action, the acquiring action, what becomes visible |
| D-039 | The four barrier categories, and which x86 permits | 1.10.23, 3.3.7 | table | Rows: LoadLoad, LoadStore, StoreStore, StoreLoad. Columns: what it forbids, permitted on x86-TSO (only StoreLoad is), permitted on AArch64, the HotSpot `OrderAccess` name, and the instruction emitted |
| D-040 | Roach motel: code moves in, never out | 1.10.24 | before-after | A synchronized block with statements above and below it. Left: legal motions — both neighbours sinking/rising *into* the block, drawn with arrows. Right: illegal motions — a statement escaping the block, crossed out. Acquire and release semantics labelled on the two edges of the block |
| D-041 | Out-of-thin-air must be forbidden | 1.10.19, 3.7.4 | step-sequence, 2 frames | The classic `r1 = x; y = r1;` / `r2 = y; x = r2;` pair with both variables starting at 0. Frame 1: the self-justifying cycle that would produce `r1 == r2 == 42`, drawn as a loop of speculative reads. Frame 2: the committed-action construction of JLS 17.4.8 refusing to commit 42, with the commit order numbered |
| D-042 | Why `println` makes the bug disappear | 1.10.26 | before-after | Left: the racy loop failing. Right: the same loop with `System.out.println` inserted, passing — with the `PrintStream`'s internal `synchronized` drawn as the accidental barrier that supplied the missing edge. Labelled "the fix is a side effect, not a fix" |
| D-043 | The freeze action and the dereference chain | 1.11.1, 1.11.2, 3.7.10 | step-sequence, 3 frames | A `StakeSplit` with two `final Money` components. Frame 1: the constructor writes both fields. Frame 2: the **freeze** at the end of the constructor. Frame 3: another thread reads the reference and is guaranteed both components and, transitively, the `BigDecimal` reachable through them. The memory-chain and dereference-chain arrows labelled |
| D-044 | Unsafe publication shows default values | 1.11.11 | step-sequence, 3 frames | A non-final `Reservation` published through a plain field. Frame 1: the constructor's field writes. Frame 2: the reference store reordered *before* them. Frame 3: the reader sees a non-null reference with `amount == null` and `status == null`, both printed. The reordering arrow labelled with who is permitted to do it |
| D-045 | Double-checked locking, broken and fixed | 1.11.15, 1.11.16, 1.11.17 | before-after | Left: the classic broken DCL over `BonusService`, with the reordering that lets a second thread return a partially-constructed instance, numbered. Right: the same with `private static volatile BonusService instance`, the acquire/release edges drawn. A third panel: the local-variable-caching variant with the second volatile read removed |
| D-046 | Five ways to build a singleton, ranked | 1.11.18, 1.11.19, 1.11.20, 5.1.127 | table | Rows: eager static field, holder idiom, DCL with `volatile`, enum, synchronized accessor. Columns: lazy, synchronization on the fast path, class-init lock used (JVMS 5.5), reflection-proof, serialization-proof, lines of code, verdict |
| D-047 | Class-initialisation deadlock is invisible to `jstack` | 1.11.21 | before-after | Two classes whose static initialisers reference each other, two threads entering them simultaneously, the two init locks drawn as a cycle. Beside it: the `jstack` output with **no** "Found one Java-level deadlock" section, and the two threads shown in the class-init state |
| D-048 | `wait()` releases the monitor and re-acquires it | 1.12.3, 3.2.10 | step-sequence, 4 frames | Frame 1: thread holds the monitor, calls `wait()`. Frame 2: the monitor is released and the thread is in the wait set — WAITING. Frame 3: another thread calls `notifyAll()` and the waiter moves to the entry list — **BLOCKED**. Frame 4: it re-acquires and returns from `wait`. The hold count save/restore labelled |
| D-049 | The lost wakeup | 1.12.12, 1.26.14 | timeline | Two lanes. The notifier changes state and calls `notify()` at t1; the waiter reaches `wait()` at t2 > t1 and blocks forever. The condition variable drawn as holding no memory. Beneath: the fixed version with a state variable checked in a `while` loop, the same interleaving now returning immediately |
| D-050 | `notify` can wake the wrong thread | 1.12.11, 1.12.13 | before-after | A wait set holding two producers and two consumers on one bounded stake queue. Left, `notify()`: a producer is woken when only a consumer could proceed, and the signal is gone. Right, `notifyAll()`: all wake, three re-check and go back to waiting, one proceeds. A third panel: two `Condition`s giving each predicate its own wait set, so `signal` is precise |
| D-051 | The CAS retry loop | 1.13.1, 1.13.2, 5.1.52 | flowchart | Read the current value → compute the new one → `compareAndSet` → success exits, failure loops back to the read. The `lock cmpxchg` (x86) and `LDXR`/`STXR` (AArch64) instructions named on the CAS box, and the retry edge labelled "another thread won; nothing is lost, but work is repeated" |
| D-052 | The 16 classes of `java.util.concurrent.atomic` | 1.13.5 | table | All 16 names grouped by family (scalars, arrays, field updaters, marked/stamped references, adders and accumulators). Columns: what it wraps, the compound operations it adds over `volatile`, memory cost, and when to reach for it |
| D-053 | ABA: the value is the same, the world is not | 1.13.13, 4.4.2 | step-sequence, 4 frames | A Treiber stack of pending withdrawal transactions. Frame 1: thread A reads top = node X and is descheduled. Frame 2: thread B pops X, pops Y, pushes X back. Frame 3: A's CAS on X succeeds. Frame 4: the stack now points at a node that was removed, with the lost element named. Beside it, the `AtomicStampedReference` version with the stamp incrementing 7 → 8 → 9 and the CAS failing |
| D-054 | `LongAdder` spreads one counter across cells | 1.13.16, 3.9.2, 3.9.4 | memory-layout | A `base` field plus a `Cell[]` of four `@Contended`-padded cells, each on its own 128-byte line, four threads each hashing to a different cell by `ThreadLocalRandom.getProbe()`. `sum()` drawn as base plus a walk of the cells with no lock, labelled "racy sum". Growth capped at `NCPU` |
| D-055 | The `VarHandle` access-mode taxonomy | 1.13.23 | table | Four groups as row blocks — read (`get`, `getOpaque`, `getAcquire`, `getVolatile`), write (`set`, `setOpaque`, `setRelease`, `setVolatile`), atomic update (the eight compare/exchange and getAndSet forms), numeric and bitwise. Columns: ordering supplied, atomicity, typical use, and whether application code should ever use it |
| D-056 | The four memory-ordering levels | 1.13.24, 3.7.13 | table | Rows: plain, opaque, acquire/release, volatile. Columns: atomicity, coherence, ordering with other variables, the C++11 equivalent (relaxed-without-atomicity, relaxed, acq/rel, seq_cst), the cost, and one JDK usage site |
| D-057 | The `Lock` idiom, and the one placement that matters | 1.14.2, 1.14.3 | before-after | Left: `lock.lock(); try { ... } finally { lock.unlock(); }` — correct, with the acquisition outside the try marked. Right: `try { lock.lock(); ... } finally { lock.unlock(); }` — the failed acquisition path reaching `unlock` and throwing `IllegalMonitorStateException`. A third panel: no `finally` at all, and the permanently wedged service as the symptom |
| D-058 | Barging beats fairness on throughput | 1.14.6, 1.14.7, 1.14.8, 3.5.16 | timeline | Two lanes on one axis. Fair mode: the lock is released, the queue head is unparked, two context switches elapse before it runs. Unfair mode: an arriving thread takes the momentarily-free lock immediately, and the queue head stays parked. Both hand-off costs written, and the `hasQueuedPredecessors()` call named as the entire code difference |
| D-059 | Read-write lock states, and the upgrade that deadlocks | 1.14.15, 1.14.16 | state-transition | States: free, N readers, one writer. Legal edges labelled with the acquiring call, plus the **downgrade** edge (write → read, legal, with the acquire-read-before-release-write ordering shown) and the **upgrade** edge (read → write) drawn crossed out with "self-deadlock: the writer waits for its own read lock" |
| D-060 | The `StampedLock` optimistic-read protocol | 1.14.20, 1.14.24 | flowchart | `tryOptimisticRead()` → read fields into locals → `validate(stamp)` → true returns, false falls back to `readLock()`/`unlockRead`. A side panel showing an inconsistent field pair observed before `validate` fails, with a dereference of it throwing — labelled "do not dereference, index or divide inside the optimistic body" |
| D-061 | `StampedLock`'s three traps in one picture | 1.14.22, 1.14.23, 1.14.26 | table | Rows: reentrancy (self-deadlock), ownership (any thread may unlock any stamp; deserializes unlocked), `newCondition()` on `asReadLock()`/`asWriteLock()` (`UnsupportedOperationException`), stamp recycling after ~1 year. Columns: what the reader assumes from `ReentrantReadWriteLock`, what `StampedLock` does, the symptom |
| D-062 | The park permit does not accumulate | 1.14.27, 3.6.1, 3.6.2 | step-sequence, 3 frames | Frame 1: `unpark(t)` before `park()` — the permit is stored, `park` returns immediately. Frame 2: two `unpark`s then two `park`s — the first returns, the second blocks, because there is at most **one** permit. Frame 3: the three ways `park` returns — spuriously, on interrupt without clearing the flag, on timeout — each requiring a re-check |
| D-063 | Latch versus barrier versus phaser | 1.15.8, 1.15.14, 5.1.42 | table | Rows: `CountDownLatch`, `CyclicBarrier`, `Phaser`. Columns: one-shot or reusable, who counts down, fixed or dynamic parties, a barrier action, arrival index returned, what breaks it, the recovery, and the QuizStakes use (start gate for a load test, phase barrier for a payment run, dynamic registration for operator sessions) |
| D-064 | The two latch shapes | 1.15.2, 1.15.3, 2.12.3 | before-after | Left, start gate: `new CountDownLatch(1)`, N worker threads awaiting, main counting down once so all start together. Right, completion gate: `new CountDownLatch(n)`, main awaiting, each worker counting down **in a `finally`**. The missing-`finally` failure drawn as main hanging forever |
| D-065 | A broken barrier stays broken | 1.15.6 | state-transition | States: intact, tripping, broken. Edges: a participant interrupted, a participant timing out, the barrier action throwing — all leading to broken, and every other participant receiving `BrokenBarrierException`. Only `reset()` returns to intact |
| D-066 | The concurrent collection inventory | 1.16.3, 1.16.23, 2.6.4 | table | One row per class across all 15. Columns: ordering, bounded, null policy, read cost, write cost, iterator model, blocking behaviour, lock count, allocation per element, and the one QuizStakes situation it is right for |
| D-067 | Three iterator-consistency models | 1.16.4, 1.16.5, 2.1.6 | before-after | The same concurrent modification applied under three iterators. Fail-fast: `modCount` mismatch and `ConcurrentModificationException` thrown, best-effort labelled. Weakly consistent: traversal continues, the change may or may not be seen, each element visited at most once. Snapshot: the array captured at iterator creation, later changes invisible, `remove` throwing `UnsupportedOperationException` |
| D-068 | Copy-on-write costs O(n) per write | 1.16.17, 1.16.18, 1.16.20 | cost-curve | Total copies against number of appends, showing the O(n²) curve for a loop of `add`, with the arithmetic for 2.8M appends written out. A second series shows read cost as a flat lock-free line. The listener-registry fit labelled on the low-write end of the axis |
| D-069 | Views, copies and snapshots | 1.16.24, 2.6.10, 2.6.11 | table | Rows: `keySet()`, `values()`, `entrySet()`, `Collections.unmodifiableList`, `List.copyOf`, `toArray()`, a CoW iterator, `subList`. Columns: view or copy, writes through, thread-safe, reflects later changes, and the distinct bug each mistake produces |
| D-070 | Why `ConcurrentHashMap` forbids null | 1.16.7, 1.16.8 | before-after | Left, a nullable map: `get(k)` returns null, and the caller cannot tell "absent" from "mapped to null"; the `containsKey`-then-`get` disambiguation shown racing and giving the wrong answer. Right: null rejected at `put` with `NullPointerException`, and `getOrDefault` as the intended API |
| D-071 | `computeIfAbsent` runs under the bin lock | 1.16.11, 3.8.19 | step-sequence, 3 frames | Frame 1: the bin head locked and a `ReservationNode` (hash `RESERVED = -3`) installed. Frame 2: the mapping function runs while the lock is held — a blocking call inside it drawn stalling every other writer to that bin. Frame 3: recursion — same key throws `IllegalStateException: Recursive update`; a different key in the same bin deadlocks. A note: on a plain `HashMap` the same pattern corrupted the table before Java 9 |
| D-072 | The four `BlockingQueue` method families | 1.17.2 | table | The canonical 4 × 4 grid: insert / remove / examine down the side; throws (`add`, `remove`, `element`), special value (`offer`, `poll`, `peek`), blocks (`put`, `take`, n/a), times out (`offer(e,t,u)`, `poll(t,u)`, n/a) across the top. Every cell filled with the exact method signature |
| D-073 | One lock versus two | 1.17.5, 1.17.6, 1.17.7, 3.10.7, 3.10.8 | memory-layout | Left, `ArrayBlockingQueue`: `items[]` ring with `takeIndex`/`putIndex`/`count`, one `ReentrantLock`, `notEmpty` and `notFull` conditions — producer and consumer contending on one lock. Right, `LinkedBlockingQueue`: linked nodes with `putLock`/`takeLock` at opposite ends and an `AtomicInteger count` in the middle, labelled "head and tail are independent, so two locks are possible; a ring's are not" |
| D-074 | `SynchronousQueue` has capacity zero | 1.17.9 | before-after | Left, the mental model of a queue with a buffer. Right, the reality: a rendezvous point where every `put` waits for a `take`; `size()` = 0, `peek()` = null, `isEmpty()` = true printed as constants. Labelled "a hand-off, not storage", with `newCachedThreadPool` named as its user |
| D-075 | The producer–consumer assembly | 1.17.16, 1.17.17, 2.7.8 | flowchart | Producers → bounded queue (capacity written) → N consumers, with: per-task try/catch inside each consumer, interrupt handling, poison pills equal to the consumer count, and the shutdown order numbered (stop accepting → drain → pill → await with a deadline → force). Withdrawal transactions feeding a `PaymentRun` used as the payload |
| D-076 | The executor interface stack | 1.18.2, 1.18.3 | hierarchy | `Executor` (`execute`) → `ExecutorService` (lifecycle plus `submit`/`invokeAll`/`invokeAny`, `close` since Java 19) → `ScheduledExecutorService`. Each box lists its declared methods; `AutoCloseable` drawn as a second parent of `ExecutorService` and dated Java 19 |
| D-077 | `submit` swallows the exception, `execute` does not | 1.18.8, 5.1.77 | before-after | Left, `execute(runnable)` that throws: the `UncaughtExceptionHandler` fires and the stack trace prints. Right, `submit(callable)` that throws: the throwable is captured into the `FutureTask`, the handler never fires, `afterExecute` sees null, and the exception is visible only through `get()` — with the "nobody calls get" path ending in silence |
| D-078 | The `ThreadPoolExecutor` submission algorithm | 1.19.2, 1.19.3, 3.10.15, 5.1.71 | flowchart | Four numbered decisions in exact order: (1) `workerCount < corePoolSize` → add a worker **even if idle threads exist**; (2) else `workQueue.offer(task)`; (3) else add a worker up to `maximumPoolSize`; (4) else `handler.rejectedExecution`. The **double-check after enqueue** drawn as its own box: re-read `ctl`, remove the task if shut down, add a worker if the pool became empty |
| D-079 | Both `Executors` factories fail, in opposite directions | 1.19.4, 1.19.5, 5.1.72, 5.1.73 | before-after | Left, `newFixedThreadPool(8)`: a `LinkedBlockingQueue` of capacity `Integer.MAX_VALUE` (2 147 483 647 written out), step 3 unreachable, `maximumPoolSize` marked dead code, and the heap filling with queued stake settlements until `OutOfMemoryError`. Right, `newCachedThreadPool`: `SynchronousQueue` capacity 0 plus `maximumPoolSize = Integer.MAX_VALUE`, one new OS thread per un-handed-off task, ending in `unable to create native thread` |
| D-080 | The four rejection policies | 1.19.7, 1.19.8, 1.19.9 | table | Rows: `AbortPolicy`, `CallerRunsPolicy`, `DiscardPolicy`, `DiscardOldestPolicy`. Columns: what happens to the task, what happens to the caller, does it give backpressure, behaviour after `shutdown()` (`CallerRunsPolicy` silently discards), and the failure mode (`DiscardOldestPolicy` with a priority queue drops the highest-priority item) |
| D-081 | Deriving the pool size from Little's law | 1.19.17, 2.4.1–2.4.3 | step-sequence, 3 frames | Frame 1: Little's law stated. Frame 2: the CPU-bound case, `N = cores + 1`, with the "+1" justified by page faults. Frame 3: the I/O-bound case worked for QuizStakes — 8 cores, U = 0.9, W = 100 ms, C = 2 ms → `8 × 0.9 × 51 = 367`, every step of the arithmetic shown, and the conclusion "367 platform threads is the argument for virtual threads" |
| D-082 | Thread-pool starvation by task dependency | 1.19.20, 1.19.21, 4.8.6 | step-sequence, 3 frames | A single-thread executor. Frame 1: task A runs and submits task B to the same pool. Frame 2: A blocks on `B.get()`. Frame 3: B sits in the queue forever with no worker available — permanent deadlock, invisible to the JVM's detector. A second panel generalises to N threads and N such tasks |
| D-083 | `scheduleAtFixedRate` versus `scheduleWithFixedDelay` | 1.20.2, 5.1.79 | timeline | Two lanes on one axis with a period of 5 s and one run overrunning to 12 s. Fixed rate: firings at t0+5, t0+10, t0+15 with the overrun causing back-to-back catch-up runs, drawn bunched. Fixed delay: each run starting 5 s after the previous **completion**, drawn evenly. Every firing time written |
| D-084 | One exception cancels every future run | 1.20.3, 1.20.4, 3.10.20, 5.1.78 | flowchart | `ScheduledFutureTask.run` → `runAndReset` → the body throws → `setException` completes the future exceptionally → `setNextRunTime` and the re-enqueue are **skipped** → nobody calls `get()`, so nothing is logged. The try/catch-inside-the-body fix drawn as the loop that keeps the re-enqueue reachable |
| D-085 | The `CompletableFuture` method map | 1.21.5, 1.21.7, 1.21.10 | hierarchy | Four families as branches: transformation (`thenApply`/`thenAccept`/`thenRun`/`thenCompose`), combination (`thenCombine`/`thenAcceptBoth`/`runAfterBoth`/`applyToEither`/`acceptEither`/`runAfterEither` — 18 methods with the ×3 noted), exception (`exceptionally`/`exceptionallyCompose`/`handle`/`whenComplete`), completion (`complete`/`completeExceptionally`/`obtrude*`). Each leaf carries its arity and the release it arrived in |
| D-086 | Which thread runs the callback | 1.21.3, 1.21.4, 2.1.8, 5.1.84 | table | Rows: `thenApply`, `thenApplyAsync`, `thenApplyAsync(executor)`, plus a row for "the stage was already complete when you attached". Columns: which thread actually runs it (the completing thread, a common-pool thread, your executor, **the calling thread**), whether it is deterministic, and the failure mode when the body blocks |
| D-087 | `thenApply` versus `thenCompose` | 1.21.6, 5.1.83 | before-after | Left: `thenApply` with a function returning a `CompletableFuture`, producing `CompletableFuture<CompletableFuture<Money>>`, the nesting drawn. Right: `thenCompose` flattening to `CompletableFuture<Money>`. Labelled with the `map`/`flatMap` correspondence and a QuizStakes chain: look up the client, then fetch their wallet |
| D-088 | Which stages run when stage 2 of 5 fails | 1.21.11, 2.8.11 | step-sequence, 4 frames | One five-stage chain over an affordability assessment, drawn four times — once each terminated by `thenApply`, `handle`, `whenComplete`, `exceptionally`. Each frame greys the skipped stages, shows where the `CompletionException` wrapping happens, and prints what the terminal call observes |
| D-089 | `allOf` versus `anyOf` | 1.21.8, 1.21.9, 2.8.8, 2.8.9 | before-after | Left, `allOf`: returns `CompletableFuture<Void>`, with the correct `thenApply(v -> list.stream().map(CompletableFuture::join).toList())` re-read drawn. Right, `anyOf`: returns `CompletableFuture<Object>` and completes on the **first to finish including the first to fail** — the identity call failing at 300 ms beating the watchlist succeeding at 1.4 s. "First successful" marked as absent from the JDK |
| D-090 | Exception wrapping across the async APIs | 1.21.12, 1.18.12 | table | Rows: `Future.get`, `CompletableFuture.get`, `CompletableFuture.join`, `exceptionally`, `handle`, `whenComplete`, `ForkJoinTask.join`. Columns: the wrapper type (`ExecutionException`, `CompletionException`, none), checked or unchecked, how to unwrap (`getCause()`), and what a cancelled future throws |
| D-091 | Work stealing: LIFO local, FIFO steal | 1.22.4, 1.22.5, 3.11.3, 5.1.89 | memory-layout | Two worker deques over a parallel ledger fold. The owner pushes and pops at `top` (LIFO, "freshest task, hottest cache"); the thief polls at `base` (FIFO, "biggest remaining chunk, least contention"). The single-element case where both target the same slot highlighted as the only place a CAS is unavoidable |
| D-092 | Everyone shares the common pool | 1.22.6, 1.22.7, 1.21.15, 2.13.14 | hierarchy | `ForkJoinPool.commonPool()` at the centre with parallelism `availableProcessors() − 1` (3 on a 4-core box, the arithmetic shown, plus the caller participating), and arrows in from parallel streams, `CompletableFuture` `*Async` with no executor, `ConcurrentHashMap` bulk ops, `Arrays.parallelSort`. A blocking task drawn occupying one of the three workers, with the starvation consequence labelled |
| D-093 | `ThreadLocal` lives in the Thread, not the ThreadLocal | 1.23.1, 1.23.6, 5.1.101 | memory-layout | Two `Thread` objects, each holding a `ThreadLocalMap` with `Entry` nodes. The `Entry` key drawn as a **weak** reference to the shared `ThreadLocal` object and the value as a **strong** reference to a 2 MB payload. The `ThreadLocal` collected, leaving a null key and a live value reachable from a pool thread that never dies |
| D-094 | The two halves of the thread-pool `ThreadLocal` leak | 1.23.5, 1.23.6, 1.23.8, 5.1.102 | before-after | Left, the correctness half: request A sets the security context for client 2 401 993, the pool thread is reused for request B, and B reads A's context — labelled a security incident class. Right, the memory half: the strong value accumulating across requests. The fix drawn as `try { CTX.set(v); } finally { CTX.remove(); }`, with `set(null)` marked as **not** a fix |
| D-095 | Platform thread versus virtual thread | 1.24.1, 1.24.16, 3.12.20 | memory-layout | Left: a platform thread — an OS thread, ~1 MB reserved stack outside the heap, a `Thread` object. Right: a virtual thread — a `VirtualThread` object plus a `Continuation` plus a growable heap `StackChunk`, a few hundred bytes to a few KB, mounted on a carrier that is itself a platform thread. 55k peak concurrent sessions costed both ways, and 1M × 2 KB = 2 GB written out |
| D-096 | Mounting and unmounting | 1.24.3, 3.12.5, 3.12.6, 3.12.7 | step-sequence, 4 frames | A virtual thread calling the card PSP at a 240 ms p50. Frame 1: mounted, frames on the carrier's stack. Frame 2: the blocking read calls `Continuation.yield`; live frames frozen into a heap `StackChunk` (lazy copy labelled). Frame 3: the carrier picks up a different virtual thread. Frame 4: the poller unparks it, frames thaw incrementally onto a **possibly different** carrier |
| D-097 | The carrier pool | 1.24.4, 3.12.9, 3.12.10, 2.9.9 | memory-layout | The scheduler as a `ForkJoinPool` in FIFO async mode; parallelism = `availableProcessors()`; `maxPoolSize` 256 (**verify before printing**); `jdk.virtualThreadScheduler.parallelism`, `.maxPoolSize` and the Java-21-only `.minRunnable` labelled on the boxes they control; a FIFO queue of runnable virtual threads feeding `CarrierThread`s, contrasted with the LIFO work-stealing used for parallel streams |
| D-098 | Pinning on Java 21, and JEP 491 in Java 24 | 1.24.6–1.24.10, 3.12.15, 3.12.16 | before-after | Left, Java 21: a virtual thread blocking inside a `synchronized` block in a tracing library; `Continuation.yield` fails, the carrier is held, other virtual threads queue behind it, and with parallelism 1 the app stalls; `-Djdk.tracePinnedThreads=full` output shown. Right, Java 24: the monitor owned by the virtual thread, monitor-blocked as a yield point, the carrier freed. A version-trap banner: the flag is **removed** in 24; native/JNI/FFM frames still pin |
| D-099 | Never pool virtual threads; bound with a `Semaphore` | 1.24.13, 1.24.14, 1.24.18, 2.9.4 | before-after | Left: a fixed pool of virtual threads — the anti-pattern, with the pool re-imposing the limit that virtual threads removed. Right: one virtual thread per task plus a `Semaphore(20)` in front of the connection pool, showing the bound moved to the resource that actually has one. The 20-connection ceiling and the queue that forms at the semaphore both labelled |
| D-100 | A structured scope is a tree with a lifetime | 1.25.1–1.25.3, 3.12.21 | hierarchy | `AssessmentService` forking two subtasks under one scope — the identity vendor (p50 900 ms) and the watchlist provider (p50 1.4 s) — each a virtual thread inside the `try`-with-resources boundary they cannot outlive. Beside it the unstructured version with two orphan threads escaping the block, still holding their connections |
| D-101 | `ShutdownOnFailure` versus `allOf` | 1.25.4, 1.25.9, 2.8.13 | timeline | Two lanes on one time axis. Lane 1, `ShutdownOnFailure`: the watchlist call fails at 1.4 s, the identity call is interrupted, `join()` returns, `throwIfFailed()` rethrows with a stack trace that names the parent. Lane 2, `allOf`: the same failure, the identity call still running past the block, marked orphan, and a stack trace showing only the completing thread |
| D-102 | `Subtask` states and the illegal calls | 1.25.5, 1.25.6 | state-transition | States `UNAVAILABLE`, `SUCCESS`, `FAILED` with the transitions caused by `fork`, completion, failure and `shutdown`. Illegal edges labelled with their exceptions: `get()` before `join()` → `IllegalStateException`; fork/join/close from a non-owner thread or an out-of-LIFO-order close → `StructureViolationException` |
| D-103 | `ScopedValue` versus `ThreadLocal` | 1.25.11–1.25.16, 2.11.9, 5.1.114 | table | Rows: mutability, lifetime, how a child thread gets it, cost of inheritance, cleanup required, can a callee set it for its caller, works across a pool boundary, final in which release. Columns: `ThreadLocal`, `InheritableThreadLocal`, `ScopedValue`. The JEP 506 (final in 25) and JEP 487 (`runWhere` removed in 24) dates stated |
| D-104 | The deadlock cycle and the four Coffman conditions | 1.26.1–1.26.5, 5.1.92, 5.1.93 | before-after | Left: `transfer(accountA, accountB)` and `transfer(accountB, accountA)` racing, drawn as a two-node wait-for cycle with each thread's held and wanted lock labelled. Right: the `System.identityHashCode` ordering fix, including the **tie lock** for the hash-collision case. A legend maps each of the four Coffman conditions to the fix that breaks it |
| D-105 | Deadlock, livelock, starvation, convoy | 1.26.11–1.26.13, 5.1.94 | table | Rows: deadlock, livelock, starvation, lock convoy, missed signal. Columns: is any thread running, does CPU rise, what the thread dump shows, the root cause, the fix, and the QuizStakes symptom (a wedged `PaymentRun`, a poison message redelivered forever, a rare writer never running, every settlement serialising behind one slow holder) |
| D-106 | What the deadlock detector cannot see | 1.26.15, 1.26.18, 1.26.19, 5.1.96 | table | Rows: monitor cycle, `ReentrantLock` cycle (ownable synchronizers), `Semaphore` permits, bounded queue, thread-pool task dependency, class-initialisation lock, database lock, distributed lock. Columns: found by `jstack`, found by `findDeadlockedThreads()`, found by `findMonitorDeadlockedThreads()`, and how you detect it instead. A footer: the JVM detects but never breaks a deadlock |

## Part 2 diagrams

| # | Diagram | Syllabus leaf | Type | Must show |
|---|---|---|---|---|
| D-107 | The master cost table | 2.1.1 | table | One row per primitive operation, all 21 named in the leaf. Columns: uncontended cost, contended cost, worst case, blocks, allocates, context-switches. Every cost quoted from the latency ladder, not adjectives |
| D-108 | The latency ladder | 2.1.2 | cost-curve | A single logarithmic axis from 1 ns to 1 ms with every rung marked and labelled: L1 1 ns, L2 4 ns, L3 15–40 ns, cache-line transfer 100+ ns, main memory 80–100 ns, uncontended CAS 10–20 ns, contended CAS 100+ ns, park/unpark 1–10 µs, platform thread creation 50–200 µs, virtual thread creation ~1 µs. Marked "order of magnitude, not measured constants" |
| D-109 | The memory-footprint table | 2.1.3 | table | Rows: platform thread, virtual thread, `ReentrantLock` (~48 B broken down), `AtomicLong` (16 B), `LongAdder` with N cells (N × 128 B), `ConcurrentHashMap.Node` (32 B), `ArrayBlockingQueue`, `LinkedBlockingQueue` per element. Columns: heap bytes, off-heap bytes, the arithmetic, and the count at which it matters for QuizStakes |
| D-110 | The five progress guarantees | 2.1.5, 1.13.4, 5.1.53 | table | Rows: blocking, obstruction-free, lock-free, wait-free (bounded), wait-free (population-oblivious). Columns: the guarantee stated precisely, a JDK example, a counter-example, and what a thread being descheduled mid-operation does to the others |
| D-111 | The escalation ladder for "make this safe" | 2.1.7, 2.3.12 | decision-tree | Root: "can you not share it?" descending through confinement → immutability → a single atomic → a concurrent collection → one lock → hand-rolled lock-free. Each rung labelled with cost, and the last rung carrying the warning "this is where you need jcstress" |
| D-112 | The lock word is the bottleneck before the body is | 2.2.1, 2.2.2 | memory-layout | Four cores each with an L1 line holding the lock word, and the line ping-ponging between them on every acquisition — the invalidation arrows drawn and counted. The critical-section body drawn as the only part doing work, with acquisition + release + coherence traffic shaded as overhead |
| D-113 | Splitting versus striping | 2.2.3–2.2.6 | before-after | Left: one `state` lock over `Account` guarding both restrictions and balances. Middle, splitting: one lock per independent invariant. Right, striping: N locks keyed by `hash % N` over one structure, with the note that `size()`/`clear()`/rehash must take **all** of them in a fixed order |
| D-114 | The contention cliff | 2.2.9, 2.2.11, 2.2.13 | cost-curve | Throughput against thread count for one global lock: rising to a peak, flat, then falling. The 8-thread and 64-thread points labelled, σ and κ fitted, and Amdahl's ceiling for a 5 % critical section (20×) drawn as a dashed asymptote |
| D-115 | Uncontended locks are not slow | 2.2.10, 5.1.28 | table | Rows: uncontended `synchronized` (thin), uncontended `ReentrantLock`, elided lock, contended `synchronized` (inflated), contended `ReentrantLock`, CAS, `LongAdder`. Columns: cost, what dominates it, whether the JIT can remove it, and the sentence a candidate should say instead of "locks are slow" |
| D-116 | `synchronized` versus `ReentrantLock` | 2.3.1, 1.14.29, 5.1.34 | table | Eight rows: simplicity, exception safety, timed acquire, interruptible acquire, fairness option, multiple conditions, instrumentation, virtual-thread pinning. Columns: `synchronized` on Java 21, `synchronized` on Java 24+, `ReentrantLock`. The pinning row carries the JEP 491 split explicitly |
| D-117 | Where a read-write lock actually wins | 2.3.4, 1.14.18, 5.1.38 | cost-curve | Throughput against read fraction from 50 % to 99.9 %, three series: `ReentrantLock`, `ReentrantReadWriteLock`, `StampedLock` optimistic. The crossover marked at roughly 90 % reads, and a second axis note that the critical section must be long enough to amortise the shared-count CAS |
| D-118 | Fairness costs an order of magnitude | 2.3.13, 1.14.7 | cost-curve | Acquisitions per second against thread count for fair and unfair `ReentrantLock`, with the 10–100× gap labelled, and a second panel showing the tail-latency distribution where fairness wins |
| D-119 | The four-parameter interaction matrix | 2.4.7, 2.4.8 | table | Rows: the sensible combinations of core size, max size, queue capacity and rejection policy. Columns: what the configuration *means* as a policy, what it does under a burst, what it does under sustained overload, and which QuizStakes workload it suits |
| D-120 | Queue depth is latency you cannot see | 2.4.5, 2.4.6, 2.4.14 | cost-curve | Added latency against queue depth for a 50 ms service: a 1000-deep queue adding up to 50 s before the first rejection, the arithmetic written out. Two series for a short and a long queue, with p99 marked on both, and queue time versus execution time named as the two metrics to export |
| D-121 | `availableProcessors()` in a container | 2.4.11, 2.4.12, 1.19.18, 5.2.51 | before-after | Left: an 8-core host reporting 8. Right: the same JVM under a 0.5-CPU cgroup quota reporting **1**, with `-XX:ActiveProcessorCount` shown as the override. Beneath, every consumer of that number listed — common pool, virtual-thread scheduler, Netty, Tomcat, Reactor, G1 workers — all mis-sizing together |
| D-122 | Five ways to count, and when each wins | 2.5.1, 2.5.2, 5.1.129 | table | Rows: `int` + `synchronized`, `AtomicInteger`, `LongAdder`, `ConcurrentHashMap.merge`, a per-thread counter summed at read. Columns: exact instantaneous read, write throughput at 1/4/16/64 threads, memory, and the verdict for the 3,400/sec settlement counter |
| D-123 | The `AtomicLong`/`LongAdder` crossover | 2.5.2, 1.13.20 | cost-curve | Throughput against writer count with two series, crossing at roughly 2–4 writers, `AtomicLong` collapsing above it and `LongAdder` scaling. A third series shows `LongAdder.sum()` cost rising with the cell count. JMH result shape labelled as the source |
| D-124 | One `AtomicReference` to an immutable snapshot | 2.5.6, 2.5.7 | before-after | Left: two atomics holding `cashAvailable` and `bonusAvailable` separately, with an interleaving that observes an inconsistent pair. Right: one immutable `WalletSnapshot` record swapped by a single `compareAndSet`, with the retry loop and the per-update allocation both labelled |
| D-125 | Choosing a concurrent collection | 2.6.1–2.6.8, 1.16.23 | decision-tree | Root: "does it need ordering?" branching through bounded/unbounded, read/write ratio, blocking or not, and index access. Every leaf names one class, and the index-access leaf ends in "there is no concurrent `List`" with the three workarounds |
| D-126 | The three concurrent `Set` options | 2.6.7 | table | Rows: `ConcurrentHashMap.newKeySet()`, `ConcurrentSkipListSet`, `CopyOnWriteArraySet`. Columns: `contains` cost (O(1) / O(log n) / **O(n)**), `add` cost, ordering, iterator model, and the situation each is right for |
| D-127 | The four backpressure mechanisms | 2.7.1, 2.7.2, 2.7.3 | table | Rows: block the producer, run on the producer (`CallerRunsPolicy`), shed, spill to disk. Columns: what it converts overload into, when it works, when it does not (blocking an HTTP request thread just moves the queue into the socket backlog), and the metric that proves it is happening |
| D-128 | A multi-stage pipeline makes the bottleneck visible | 2.7.5, 2.7.4 | flowchart | Three stages of withdrawal processing, each with its own bounded queue (capacities written) and its own pool (sizes written), and the slowest stage's queue drawn full. `drainTo` batching shown at the consumer with the batch size and the amortised lock acquisition labelled |
| D-129 | Total order needs one consumer; per-key order does not | 2.7.7 | before-after | Left: one consumer preserving total order over settlements, throughput capped at one thread. Right: a hash partition on `ClientId` feeding N consumers, order preserved per client, throughput scaling with N. Kafka's partition model named as the same idea |
| D-130 | Every async stage is a thread hop | 2.8.3, 2.8.4 | timeline | One chain of five `*Async` stages over an affordability assessment, with each hop drawn as a queue push plus a possible unpark, and the accumulated overhead written. Beside it the same chain with the cheap transformations left non-async, running inline on the completing thread |
| D-131 | Context does not follow a stage hop | 2.8.5, 2.11.1–2.11.5 | before-after | Left: MDC trace id set on the request thread, lost on the first `thenApplyAsync`, and the log line printed with an empty trace id. Right: the three fixes drawn — a decorating `Executor`, Micrometer `ContextSnapshot`, and `ScopedValue` plus a structured scope — each showing where the copy happens |
| D-132 | The virtual-thread migration checklist | 2.9.1, 2.9.13, 2.9.14 | flowchart | Ordered gates: audit `synchronized` on blocking paths (Java 21 only) → audit `ThreadLocal` caches → add a `Semaphore` at every bounded downstream → re-size the connection pool → re-point monitoring at in-flight tasks → enable behind a runtime flag per workload. Each gate names the library class most likely to fail it (JDBC driver, connection pool, tracing agent, logging appender, object pool) |
| D-133 | Removing the pool removed the rate limiter | 2.9.4, 1.24.18, 5.1.111 | before-after | Left: a 200-thread pool implicitly capping concurrent database work at 200. Right: virtual threads with no pool, 14 000 concurrent sessions all reaching a 20-connection pool, the queue forming at the connection pool instead — with the `ulimit -n` file-descriptor ceiling drawn as the second new bound |
| D-134 | The `ThreadLocal` cache regression under virtual threads | 2.9.3, 1.23.10, 5.2.39 | before-after | Left, platform pool: 200 threads, 200 cache initialisations. Right, virtual threads: one per task, **443 267** initialisations for the same workload, both numbers printed, no exception thrown, and GC pressure named as the only symptom. Labelled "`ThreadLocal` as context, never as cache" |
| D-135 | When delegation is valid and when it is not | 2.10.2, 2.10.3 | before-after | Left, valid: a class whose only invariants are the delegate's, forwarding to a `ConcurrentHashMap`. Right, invalid: two thread-safe fields `lower` and `upper` with the constraint `lower <= upper`, and the interleaving that violates it with both individual operations succeeding. The single-lock fix drawn beneath |
| D-136 | Thread safety of common JDK types | 2.10.15 | table | Rows: `String`, `StringBuilder`, `StringBuffer`, `SimpleDateFormat`, `DateTimeFormatter`, `Random`, `ThreadLocalRandom`, `SecureRandom`, `BigDecimal`, `ArrayList`, `HashMap`, `LocalDate`. Columns: thread-safe, why or why not (`SimpleDateFormat`'s mutable `Calendar` field named as the actual culprit), contention behaviour, and the modern replacement |
| D-137 | The five context-propagation mechanisms | 2.11.2, 2.11.3, 2.11.10 | table | Rows: manual copy, decorating `Runnable`/`Callable`, decorating `Executor`, Micrometer `ContextSnapshot`, `ScopedValue` + structured concurrency. Columns: works across a pool, works across a structured scope, cleanup required, what it cannot do, and the Spring/OpenTelemetry equivalent |
| D-138 | A jcstress litmus test, read | 2.12.7, 2.12.8, 3.7.7 | table | The store-buffering (Dekker) case with its two actors, and all four outcomes `(0,0)`, `(0,1)`, `(1,0)`, `(1,1)`. Columns: permitted by sequential consistency, permitted by the JMM, observed on x86, observed on AArch64, jcstress classification (`ACCEPTABLE` vs `ACCEPTABLE_INTERESTING`), and the fix |
| D-139 | What each verification tool can and cannot find | 2.12.1, 2.12.11, 3.13.12 | table | Rows: unit test, stress test, jcstress, JMH, ErrorProne `@GuardedBy`, SpotBugs detectors, `ThreadMXBean` watchdog, JFR, async-profiler, thread dump. Columns: finds a lost update, finds a deadlock, finds a data race, finds contention, finds a leak, runs in CI |
| D-140 | `nanoTime` is the only correct deadline basis | 2.13.3, 2.13.4, 3.6.8 | before-after | Left: `currentTimeMillis() >= deadline` with an NTP step backwards, and the timeout firing hours late (or immediately). Right: `System.nanoTime() - deadline >= 0`, monotonic, and overflow-safe — with the subtraction form contrasted against the broken `nanoTime() >= deadline` comparison |
| D-141 | Every primitive's distributed analogue | 2.14.1–2.14.6 | table | Rows: `synchronized`, `ReentrantLock`, `AtomicLong`, CAS, `CountDownLatch`, `volatile`, single-writer confinement, `ScheduledExecutorService`. Columns: the in-JVM guarantee, the distributed replacement (Redis/ZooKeeper/etcd lock, DB sequence or `INCR`, a `@Version` column, a ZooKeeper barrier, a consistent read, leader election, ShedLock), and what guarantee is lost |
| D-142 | Why a distributed lock needs a fencing token | 2.14.3 | timeline | One lane per client plus one for the storage. Client 1 acquires the lease, GC-pauses past expiry, client 2 acquires, then client 1 wakes and writes — the corrupting write drawn. Beneath: the same sequence with monotonically increasing fencing tokens 33 and 34, and the storage rejecting the stale token |
| D-143 | The concurrency version timeline, Java 5 → 25 | 2.15.1–2.15.16 | timeline | One axis with a mark per release. Each mark lists what arrived and what left: `j.u.c` and JSR-133 at 5, fork/join at 7, `CompletableFuture`/`StampedLock`/`LongAdder`/new CHM at 8, `VarHandle`/`Flow` at 9, cgroup awareness at 10, biased locking disabled at 15, virtual threads preview at 19, `Thread.stop` removed at 20, virtual threads final at 21, JEP 491 at 24, scoped values final at 25. Removals drawn in a separate lane below the additions |
| D-144 | The deprecation graveyard | 2.15.16, 1.3.14 | table | Rows: `Thread.stop`, `suspend`, `resume`, `countStackFrames`, `ThreadGroup` management, biased locking, `Timer`, `finalize`-based pool shutdown, `sun.misc.Unsafe` memory access, `AtomicXxxFieldUpdater`. Columns: deprecated in, disabled in, removed in, what happens if you call it today, and the replacement |

## Part 3 diagrams

| # | Diagram | Syllabus leaf | Type | Must show |
|---|---|---|---|---|
| D-145 | The object header on 64-bit HotSpot | 3.1.1, 3.1.8 | memory-layout | A `Reservation` instance drawn byte by byte: 8-byte mark word, 4-byte compressed klass pointer, the fields in HotSpot's size-class order (long, int, short, byte, oop), and padding to the 8-byte boundary. Totals of 12 B with compressed oops and 16 B without, both written |
| D-146 | The mark word is multiplexed | 3.1.2, 3.1.3, 3.1.4 | table | Rows: neutral/unlocked, lightweight (stack-locked), inflated (monitor), marked/forwarded during GC. Columns: the low tag bits (`01`, `00`, `10`, `11`), what the remaining bits hold (identity hash + age, a `BasicLock` pointer, an `ObjectMonitor` pointer, a forwarding pointer), and what transition gets you there. **Verify the encoding against the HotSpot wiki before printing** |
| D-147 | Compact object headers shrink the lock space | 3.1.6, 3.2.13 | before-after | Left: the 96–128-bit header with the klass pointer separate. Right: the 64-bit compact header with the compressed klass pointer folded into the mark word, the monitor pointer no longer fitting, and the `ObjectMonitorTable` side map drawn. 10–20 % heap reduction and the release dates (experimental 24 / default 25) labelled |
| D-148 | The three locking states, and the fourth that is gone | 3.2.1, 3.2.14, 3.2.15 | state-transition | States: unlocked → lightweight (stack-locked) → inflated, with the transition triggers on each edge. Biased locking drawn as a **greyed-out, crossed-through** fourth state annotated "JEP 374, disabled in Java 15, later removed — do not describe this in an interview as current" |
| D-149 | The displaced header | 3.2.2, 3.2.3, 3.2.4 | step-sequence, 4 frames | Frame 1: the neutral mark word. Frame 2: the thread CASes in a pointer to a `BasicLock` in its own frame, saving the old mark word there as the displaced header. Frame 3: a recursive acquisition storing a **zero** displaced header — the hold count with no counter. Frame 4: unlock CASing the displaced header back, and the failure path when the lock inflated while held |
| D-150 | Inside an `ObjectMonitor` | 3.2.6, 3.2.7, 3.2.8, 3.2.9 | memory-layout | The native structure with `_owner`, `_recursions`, `_cxq`, `_EntryList`, `_WaitSet`, `_succ`, `_object`. Contenders pushed LIFO onto `_cxq`, the owner on release moving `_cxq` onto `_EntryList` and unparking `_succ`. Labelled "this is why monitor wakeup order is unspecified and unfair" |
| D-151 | What forces inflation | 3.2.5, 3.1.4, 3.1.5 | decision-tree | Four triggers as branches: another thread contends the stack lock; `wait()` is called and a wait set is needed; `System.identityHashCode` must be stored in the mark word; a JVMTI or monitor-inspection operation demands a real monitor. Each leaf shows the resulting mark-word state and the cost |
| D-152 | Adaptive spinning, then parking | 3.2.11, 3.6.6 | timeline | One contender's path: spin for a duration derived from recent success on this monitor, then park. The CAS cost (10–20 ns) and the park/unpark round trip (1–10 µs) both marked on the axis, showing exactly why spin-then-block is the strategy. `-XX:-UseHeavyMonitors` named as the measurement switch |
| D-153 | Lock elision and lock coarsening | 3.3.1, 3.3.2, 3.3.4 | before-after | Left, elision: a `StringBuilder` proved non-escaping inside one method, with `monitorenter`/`monitorexit` struck out. Right, coarsening: three adjacent synchronized blocks on the same lock merged into one, with the note that "narrow your critical section" can be undone by the compiler — and the counter-note that elision only fires when the lock was already unnecessary |
| D-154 | The JSR-133 cookbook barrier table | 3.7.12, 3.3.7 | table | The classic grid: first operation (normal load/store, volatile load, volatile store, monitor enter/exit) down the side, second operation across the top, and the required barrier in each cell. A second column block gives what each becomes on x86-TSO (mostly no-ops) and on AArch64 (`ldar`/`stlr`/`dmb`) |
| D-155 | x86-TSO: the store buffer is the whole story | 3.3.8 | memory-layout | Two cores each with a store buffer between the core and a coherent cache. A store sitting in the buffer while a subsequent load bypasses it — the one permitted reordering. Loads shown never reordered with loads, stores never with stores. Labelled "this is why most JMM bugs are invisible on your laptop" |
| D-156 | Time to safepoint is not pause time | 3.4.1–3.4.4, 3.4.7 | timeline | One axis with three regions labelled from `-Xlog:safepoint*`: **Reaching safepoint** (TTSP), **At safepoint** (the operation), **Leaving safepoint**. Four threads arriving at different times, with one stuck in a counted `int` loop with no poll dominating TTSP. `GuaranteedSafepointInterval = 1000 ms` marked |
| D-157 | Safepoint bias in a profiler | 3.4.9, 3.4.5 | before-after | Left: a `getStackTrace`-based sampler taking every sample at a safepoint, and the hot method between polls never appearing. Right: `AsyncGetCallTrace`/async-profiler with `-XX:+DebugNonSafepoints`, sampling the real distribution. The mis-attributed frame named in both |
| D-158 | AQS anatomy | 3.5.1–3.5.6 | memory-layout | A `volatile int state`, a dummy `head`, a chain of nodes to `tail`, each node holding a thread reference, `prev`, `next` and a status field. The five template methods listed in a side box, and the state accessors `getState`/`setState`/`compareAndSetState` marked as the only legal way to touch state |
| D-159 | Why AQS sometimes walks backwards from the tail | 3.5.7 | step-sequence, 3 frames | Frame 1: a new node sets `prev` to the current tail. Frame 2: it CASes itself in as the new tail — at this instant `prev` is valid but the predecessor's `next` is still null. Frame 3: `next` is set. A traversal from head hitting the null `next` and restarting **backwards from tail** is drawn and labelled "the single most surprising line in AQS" |
| D-160 | The AQS acquire loop | 3.5.10, 3.5.11 | flowchart | `tryAcquire` → success returns; failure → am I the head's successor? retry once → else enqueue → set the predecessor's status to WAITING → `LockSupport.park` → on wake, re-check. The release path drawn beside it: `tryRelease` → unpark exactly one successor in exclusive mode |
| D-161 | The AQS node status encoding changed | 3.5.8, 3.5.9 | table | Two column groups. JDK 8–14: `CANCELLED = 1`, `SIGNAL = -1`, `CONDITION = -2`, `PROPAGATE = -3`, `0` default, with `Node` subclasses absent. JDK 14+ (what Java 21 runs): bit flags `WAITING = 1`, `COND = 2`, `CANCELLED = 0x80000000`, and `ExclusiveNode`/`SharedNode`/`ConditionNode`. Banner: most blog explanations describe the left column |
| D-162 | What `state` means, per synchronizer | 3.5.4, 5.1.49 | table | Rows: `ReentrantLock`, `Semaphore`, `CountDownLatch`, `ReentrantReadWriteLock`, `ThreadPoolExecutor.Worker`, `FutureTask`, `StampedLock`, `Phaser`, `Exchanger`, `CompletableFuture`. Columns: AQS-based or not, what the 32 bits mean (with the RW lock's 16/16 split and the 65 535 maxima spelled out), exclusive or shared mode |
| D-163 | `Condition.await` transfers a node between two queues | 3.5.14, 3.5.15, 5.1.50 | step-sequence, 4 frames | Frame 1: the thread holds the lock with hold count 2. Frame 2: `await` **fully** releases the state (saving 2), enqueues a `ConditionNode` on the condition queue, and parks. Frame 3: `signal` transfers the node to the sync queue — the thread is not woken directly. Frame 4: it reaches the head, re-acquires, and restores hold count 2 |
| D-164 | Shared mode propagates | 3.5.12 | step-sequence, 3 frames | A `Semaphore(3)` with five waiters. Frame 1: three permits released. Frame 2: the first shared acquire succeeds and returns a remaining count, which propagates the signal to the next node. Frame 3: the cascade — three readers wake, the fourth and fifth stay parked. Contrasted with exclusive mode's one unpark per release |
| D-165 | `park` on a platform thread versus a virtual thread | 3.6.4, 3.6.5, 3.6.9, 3.12.11 | before-after | Left: `LockSupport.park` on a platform thread → `Parker`/`PlatformEvent` → `pthread_cond_wait` → `FUTEX_WAIT`, two context switches costed. Right: the identical API call on a virtual thread → `VirtualThread.park` → state `PARKING` → `Continuation.yield`, no OS thread parked. Labelled "the hinge on which all of Loom turns" |
| D-166 | The five litmus tests | 3.7.7, 3.7.8 | table | Rows: store buffering (Dekker), message passing (publication), IRIW, load buffering, coherence (CoRR). Columns: the program, the surprising outcome, permitted by x86-TSO, permitted by AArch64, permitted by the JMM, and the fix. IRIW's row explains why volatile (seq_cst) is strictly stronger than acquire/release |
| D-167 | Happens-before consistency is not enough | 3.7.3, 3.7.4, 3.7.6 | flowchart | The two clauses of the happens-before consistency rule as gates a candidate execution must pass, then a second gate — the committed-action construction of 17.4.8 — rejecting the out-of-thin-air execution that passed the first. The DRF-SC conclusion drawn as the exit, with the "one racy field anywhere loses SC reasoning in principle" caveat attached |
| D-168 | Final-field semantics need no read-side barrier | 3.7.10, 3.7.11 | step-sequence, 3 frames | Frame 1: the constructor's field writes. Frame 2: the `StoreStore` emitted at the freeze — the only barrier. Frame 3: the reader's dereference, correct because of the data dependency through the reference, with the Alpha exception noted as the one architecture that needed more |
| D-169 | `ConcurrentHashMap`: table, bins, and per-bin locking | 3.8.2, 3.8.8, 3.8.9 | memory-layout | A `Node[] table` of 16 slots. An empty bin having its first node installed by `casTabAt` with no lock. A populated bin with `synchronized (f)` on the head node and a chain behind it. A third bin holding a `TreeBin`. A reader traversing a bin concurrently with a writer, labelled "`get` is lock-free: `val` and `next` are volatile, `tabAt` is an acquire read" |
| D-170 | The `ConcurrentHashMap` constants | 3.8.3, 3.8.4, 3.8.5, 5.3.2 | table | Rows: `MAXIMUM_CAPACITY = 1 << 30`, `DEFAULT_CAPACITY = 16`, `LOAD_FACTOR = 0.75f` (hard-coded), `TREEIFY_THRESHOLD = 8`, `UNTREEIFY_THRESHOLD = 6`, `MIN_TREEIFY_CAPACITY = 64`, `MIN_TRANSFER_STRIDE = 16`, `RESIZE_STAMP_BITS = 16`, `MOVED = -1`, `TREEBIN = -2`, `RESERVED = -3`, `HASH_BITS = 0x7fffffff`. Columns: value, what it controls, what happens either side of it. The `spread` function printed with the reason the sign bit is masked off |
| D-171 | `sizeCtl` is one field with four meanings | 3.8.6, 3.8.7, 3.8.12 | state-transition | Four states of the same field: `0` (default-size table not yet created), positive (next resize threshold, or the requested initial capacity before creation), `-1` (a thread is initialising, won by CAS, losers call `Thread.yield()`), negative-other (resize stamp in the high bits + resizing-thread count + 1 in the low bits). Every transition labelled with the method that causes it |
| D-172 | Resizing is cooperative | 3.8.10, 3.8.11, 5.1.70 | step-sequence, 4 frames | A 16-slot table doubling to 32. Frame 1: `transferIndex` set, stride `MIN_TRANSFER_STRIDE = 16` computed from NCPU. Frame 2: two threads each claiming a range. Frame 3: a moved bin replaced by a `ForwardingNode` with hash `MOVED = -1`; a reader following `nextTable`, a writer calling `helpTransfer`. Frame 4: the lo/hi split — each entry either stays at `i` or moves to `i + oldCap`, decided by `(hash & oldCap) == 0`, with two worked hashes |
| D-173 | Treeify at 8, untreeify at 6, only above 64 | 3.8.13, 3.8.14, 3.8.15 | step-sequence, 3 frames | Frame 1: a bin reaching 8 nodes in a table of 32 — the table **resizes** instead, because `MIN_TREEIFY_CAPACITY = 64`. Frame 2: the same at table size 64 — a `TreeBin` forms, holding both the red-black tree and the `prev`/`next` list view, with its `lockState` read-write lock labelled. Frame 3: shrinking to 6 during a resize, with the 8/6 hysteresis gap named |
| D-174 | Counting with `baseCount` plus `CounterCell[]` | 3.8.17, 3.8.18, 5.1.63 | flowchart | `addCount` → CAS `baseCount` → on failure CAS a random cell → on failure `fullAddCount`, possibly growing the array. `size()` drawn as base plus a walk of the cells with no lock, therefore approximate, and `mappingCount()` named as the `long` version for maps above `Integer.MAX_VALUE` entries |
| D-175 | What a `ConcurrentHashMap` entry costs | 3.8.23 | memory-layout | One `Node` broken into header (12/16 B) + `hash` 4 + `key` ref 4 + `val` ref 4 + `next` ref 4 ≈ 32 B, plus the 4-byte table slot, totalling ~36–40 B before the key and value objects. Scaled to a 2.4M-client restriction map with the total written out |
| D-176 | False sharing | 3.9.6, 3.9.7, 3.9.11, 4.8.5 | memory-layout | One 64-byte cache line holding `a[0]` and `a[1]`, two cores each writing one of them, and every write invalidating the other core's line — the invalidation arrows counted. Beside it `a[0]` and `a[16]` on separate lines with no invalidation. The 128-byte `-XX:ContendedPaddingWidth` default and the Apple M-series 128-byte sector both labelled, with the measured throughput ratio |
| D-177 | `@Contended` and why manual padding fails | 3.9.5, 3.9.8, 3.9.9 | before-after | Left: `Striped64.Cell` annotated `@jdk.internal.vm.annotation.Contended`, the JVM padding it to its own line. Right: the historical `long p1..p7` trick, with HotSpot's field reordering shown moving the padding away from where the author put it. `-XX:-RestrictContended` named as the flag application code would need, and advised against |
| D-178 | The Michael–Scott queue's lagging tail | 3.10.1, 3.10.2, 3.10.3, 4.4.5 | step-sequence, 4 frames | Frame 1: a dummy head and a tail pointing at the last node. Frame 2: an enqueue CASing `next` on the last node while `tail` still lags by one. Frame 3: any thread helping advance `tail`. Frame 4: a dequeued node self-linked (`p.next == p`) so a stale traverser restarts from head. `size()` marked O(n) and approximate |
| D-179 | `ThreadPoolExecutor.ctl` packs state and count | 3.10.12, 3.10.13 | memory-layout | One 32-bit `AtomicInteger` drawn bit by bit: 3 high bits of run state, 29 low bits of worker count. The five constants with their values — `RUNNING = -1<<29`, `SHUTDOWN = 0`, `STOP = 1<<29`, `TIDYING = 2<<29`, `TERMINATED = 3<<29` — and `CAPACITY = (1<<29)-1 = 536 870 911`. Labelled with why they must be read and updated atomically together |
| D-180 | The pool's run-state transitions | 3.10.14, 1.18.15, 5.1.76 | state-transition | Five states with every edge labelled by its cause: `shutdown()`, `shutdownNow()`, queue and pool both empty, `terminated()` returning. The two-phase shutdown idiom overlaid as a numbered path: `shutdown` → `awaitTermination(timeout)` → `shutdownNow` → `awaitTermination` again |
| D-181 | `Worker` is an AQS lock that means "busy" | 3.10.16, 3.10.17 | before-after | Left: `shutdownNow` interrupting a worker parked in `getTask` mid-`poll` — the bug the trick prevents. Right: `Worker extends AbstractQueuedSynchronizer`, non-reentrant, locked only while running a task, so `interruptIdleWorkers` skips the busy ones. `runWorker`/`getTask` shown choosing `poll(keepAliveTime)` versus `take()` by `allowCoreThreadTimeOut` |
| D-182 | `DelayedWorkQueue` and the leader thread | 3.10.19, 3.10.11 | memory-layout | A binary heap of `ScheduledFutureTask`s, each carrying its index-in-heap field so `remove` is O(log n) rather than O(n). One designated leader doing a timed wait on the head's delay while every other waiter waits indefinitely — labelled "avoids a thundering herd of timed waits" |
| D-183 | `FutureTask`'s state machine | 3.10.21 | state-transition | Seven states with their integer values: `NEW = 0`, `COMPLETING = 1`, `NORMAL = 2`, `EXCEPTIONAL = 3`, `CANCELLED = 4`, `INTERRUPTING = 5`, `INTERRUPTED = 6`, and every legal edge. The Treiber stack of `WaitNode` waiters drawn beside it, with `get()` parking on it |
| D-184 | `CompletableFuture` internals | 3.10.22, 3.10.23, 3.10.24, 4.7.5 | memory-layout | A `volatile Object result` holding either a value, the `NIL` sentinel for null, or an `AltResult` wrapping a throwable; and a Treiber stack of `Completion` nodes. Completion drawn popping and firing the stack, with `postComplete`'s recursion unrolling labelled as the protection against a deep chain overflowing the stack |
| D-185 | The `ForkJoinPool` queue array | 3.11.1, 3.11.2 | memory-layout | The `WorkQueue[]` with submission queues in even slots and worker queues in odd slots, an external submitter hashing into a submission queue, and one `WorkQueue` expanded to show `array`, `base` (volatile, steal end), `top` (push/pop end), `phase`, `source`, `nsteals` |
| D-186 | `ForkJoinPool.ctl` in 64 bits | 3.11.5, 3.11.6 | memory-layout | One 64-bit field split from the high end into active count `AC`, total count `TC`, and the id/version of the top of the idle-worker Treiber stack. Every pool state transition drawn as a single CAS on this field, and `signalWork` shown deciding from a `ctl` read rather than a queue scan |
| D-187 | `helpJoin` is why fork/join does not deadlock | 3.11.10, 1.22.3 | step-sequence, 3 frames | Frame 1: a worker forks the left half and computes the right. Frame 2: it reaches `join` on a task another worker stole. Frame 3: instead of blocking it executes that task, or a task the stealer is working on. Labelled "this is why `fork(); compute(); join();` is safe on a fixed-size pool, and why `fork(); fork(); join(); join();` is worse" |
| D-188 | Compensation and `ManagedBlocker` | 3.11.9, 3.11.11, 1.22.10, 1.22.12 | flowchart | A worker about to block: `tryCompensate` spawning or releasing a spare, bounded by `maximumPoolSize` (`256 + parallelism` for the common pool — **verify**), `minimumRunnable` (default 1) and the `saturate` predicate. Beside it the `ManagedBlocker` loop, `isReleasable()` then `block()`, and the unsupported path — plain blocking I/O with no compensation, starving the pool |
| D-189 | `CountedCompleter` joins without blocking | 3.11.12 | step-sequence, 3 frames | A fan-out over 95k card deposits. Frame 1: pending counts set on the completer tree. Frame 2: leaves finishing and calling `tryComplete`, decrementing their parents. Frame 3: the root's `onCompletion` firing with no thread ever having blocked. Named as what `ConcurrentHashMap` bulk ops and `java.util.stream` use |
| D-190 | A delimited continuation | 3.12.1, 3.12.2 | memory-layout | A carrier stack with the `ContinuationScope` entry frame marked, and `yield` unwinding **only** up to that frame — the frames above it copied out, the frames below untouched. `Continuation.run`, `yield(scope)` and `isDone` listed, with the class marked internal and unsupported |
| D-191 | The `VirtualThread` internal state machine | 3.12.3, 3.12.4, 1.4.12 | state-transition | The internal states `NEW`, `STARTED`, `RUNNING`, `PARKING`, `PARKED`, `PINNED`, `YIELDING`, `TERMINATED` plus the `SUSPENDED` bit, with the transitions caused by `start`, mount, `park`, `yield`, `unpark`, pinning and completion. A second column maps each internal state to the `Thread.State` a caller sees, and a note that the internal names appear only in the JSON dump |
| D-192 | Socket I/O goes through a poller, file I/O does not | 3.12.12, 3.12.13, 2.9.8 | before-after | Left: a blocking socket read implemented over non-blocking NIO plus a `sun.nio.ch.Poller` (epoll/kqueue) thread that unparks the virtual thread when the fd is ready — the carrier freed the whole time. Right: a `FileChannel` read on Linux delegated to carrier-blocking work, no io_uring integration, the carrier consumed. `jdk.pollerMode` labelled |
| D-193 | Why `jstack` cannot see a virtual thread | 3.12.18, 3.12.19, 1.24.12, 5.1.110 | before-after | Left: `jstack` walking the JVM's `JavaThread` list, an unmounted virtual thread having no `JavaThread`, and the dump showing only the handful of carriers. Right: `jcmd <pid> Thread.dump_to_file -format=json <file>` with the thread-container structure — one container per `StructuredTaskScope` or executor, parent links drawn — and the note that it omits locks and JNI stats |
| D-194 | `ScopedValue`'s binding chain | 3.12.22, 1.25.13 | memory-layout | An immutable linked `Carrier` chain per thread, one node per binding, with a nested `where(...).run(...)` adding a node rather than mutating. The small per-thread cache keyed on the scoped value's hash drawn beside it, making `get()` close to a field read. Inheritance into a structured subtask drawn as a **pointer copy**, contrasted with `InheritableThreadLocal`'s map copy |
| D-195 | A `jstack` dump, annotated line by line | 3.13.1, 3.13.3 | table | One real dump excerpt with a row per element: the header line fields (`"name" #id [tid] daemon prio os_prio cpu elapsed tid nid state`), the `java.lang.Thread.State` line, the stack frames, `- locked <0x…>`, `- waiting to lock <0x…>`, `- parking to wait for <0x…>`, the "Locked ownable synchronizers" block, and the "Found one Java-level deadlock:" section. Columns: the line, what it means, what it rules out |
| D-196 | The three dump signatures | 3.13.2, 5.1.98, 5.1.99 | table | Rows: monitor contention, pool saturation, pool idleness, deadlock, virtual-thread pinning. Columns: how many threads and in what state, the give-away stack frame, CPU usage, throughput, the next command to run, and the fix |
| D-197 | Finding the thread that is burning a core | 3.13.5, 3.13.11, 5.1.100 | step-sequence, 4 frames | Frame 1: `top -H -p <pid>` showing a hot LWP id in decimal. Frame 2: converting it to hex. Frame 3: matching `nid=0x…` in the thread dump. Frame 4: reading that thread's stack. `/proc/<pid>/task/<tid>/status` shown as the source of the voluntary/involuntary context-switch counts for the same thread |
| D-198 | JFR concurrency events and their thresholds | 3.13.6, 3.13.7, 1.24.11, 2.2.8 | table | Rows: `jdk.JavaMonitorEnter`, `jdk.JavaMonitorWait`, `jdk.JavaMonitorInflate`, `jdk.ThreadPark`, `jdk.ThreadStart`/`End`, `jdk.ThreadSleep`, `jdk.VirtualThreadStart`, `jdk.VirtualThreadEnd`, `jdk.VirtualThreadPinned`, `jdk.VirtualThreadSubmitFailed`, `jdk.ExecutorTaskSubmit`. Columns: enabled by default, default threshold (20 ms where it applies), what it proves, and what it misses at that threshold |

## Part 4 diagrams

| # | Diagram | Syllabus leaf | Type | Must show |
|---|---|---|---|---|
| D-199 | Five spin locks, compared | 4.1.1–4.1.8 | table | Rows: TAS spin lock, test-and-test-and-set, ticket lock, CLH, MCS, backoff. Columns: where each waiter spins (the shared line, the predecessor's node, its own node), coherence traffic per acquisition, FIFO fairness, space per waiter, NUMA suitability, and which one AQS derives from and why |
| D-200 | CLH versus MCS spin location | 4.1.5, 4.1.6, 4.1.7 | memory-layout | Two queues of four waiters. CLH: each spins on its **predecessor's** node flag, the implicit queue drawn through `prev` references. MCS: each spins on **its own** node flag, set by the predecessor on release, the explicit `next` chain drawn. The cache line each waiter touches highlighted in both |
| D-201 | Spin versus park, measured | 4.1.2, 3.6.6 | cost-curve | Throughput against thread count (1, 2, 8, 64) with two series each for a 100 ns and a 100 µs critical section: spin lock and `ReentrantLock`. The crossover regions shaded and labelled with why — spinning wins while the wait is shorter than a park/unpark round trip |
| D-202 | A 25-line AQS mutex | 4.2.1, 4.2.3, 4.2.4 | before-after | Left: `SimpleMutex.tryAcquire` CASing state 0→1 and `tryRelease` setting 0. Right: the reentrant version with a hold count in `state` and the owner in `setExclusiveOwnerThread`, plus the `IllegalMonitorStateException` path on foreign release. `OneShotLatch`'s shared-mode variant shown as a third panel with state 0 = closed, 1 = open |
| D-203 | Three bounded queues, three signalling schemes | 4.3.1–4.3.3 | table | Rows: `synchronized` + `wait`/`notifyAll`, `ReentrantLock` + `notFull`/`notEmpty`, two locks + `AtomicInteger count`. Columns: how many waiters wake per operation, whether producers and consumers contend, allocation per element, the cascading-signal rule, and correctness obligations |
| D-204 | An SPSC ring buffer | 4.3.6 | memory-layout | A power-of-two array with padded `head` and `tail` `AtomicLong`s on separate cache lines, the mask trick `index & (capacity - 1)` printed, and the one-producer/one-consumer invariant that removes the need for CAS. Full and empty conditions written out |
| D-205 | ABA broken and fixed, in your own stack | 4.4.1, 4.4.2, 4.4.3 | before-after | Left: the hand-rolled `TreiberStack` with explicit node pooling, and the recycle sequence that corrupts it. Right: the same with `AtomicStampedReference`, the stamp shown incrementing. A third panel states why the plain, non-pooling Java version is usually ABA-safe: the GC will not reuse a node while a reference is held |
| D-206 | The mini `ThreadPoolExecutor`, version by version | 4.5.1–4.5.5 | step-sequence, 5 frames | Frame 1: N workers over one `BlockingQueue`. Frame 2: `submit` plus your own `Future` state machine. Frame 3: run state and worker count packed into one `AtomicInteger`. Frame 4: core/max sizing with `poll(keepAliveTime)` and the four rejection policies. Frame 5: `beforeExecute`/`afterExecute` and the try/catch that stops a thrown task killing its worker |
| D-207 | The one unavoidable CAS in a work-stealing deque | 4.6.1, 4.6.2 | step-sequence, 3 frames | Frame 1: `top - base > 1`, owner pops at `top` with a plain store, thief polls at `base` with a CAS, no conflict. Frame 2: `top - base == 1`, both target the same slot. Frame 3: the CAS resolving it, with the loser's retry path drawn |
| D-208 | `MiniScope`'s lifetime rules | 4.7.1–4.7.4 | state-transition | Scope states open → joined → closed, with `fork` legal only before `join`, `join` legal only on the owner thread, and `close` required in LIFO order. Illegal edges labelled with the exception each raises. The honest limitation printed: a deadline cannot stop a subtask that ignores interruption |
| D-209 | The visibility harness | 4.8.1 | before-after | The non-volatile stop flag loop that never exits, with the `-XX:+PrintCompilation` output and the hoisted C2 form beside it; then the `volatile` version exiting, with the elapsed time in both cases |
| D-210 | The lost-update harness results | 4.8.2 | table | Rows: `int`, `volatile int`, `AtomicInteger`, `synchronized`, `LongAdder`. Columns: expected final value (N × M), actual final value, elapsed time, and the one-clause reason. Run at 8 threads × 1,000,000 increments over a stake-reservation counter |
| D-211 | The backpressure harness | 4.8.11 | cost-curve | Heap usage and producer rate over time, two series: an unbounded queue (heap climbing to OOM, producer never slowing) and a bounded queue of 1,000 (heap flat, producer rate clamped to the consumer's). Both curves labelled with the moment the behaviour diverges |
| D-212 | One dump per harness | 4.8.12, 3.13.2 | table | Rows: deadlock harness, livelock harness, starvation harness, pinning harness, `ThreadLocal` leak harness. Columns: the distinguishing dump lines, the thread states, what the tool reports (`jstack` deadlock section, JFR `jdk.VirtualThreadPinned`, heap-dump `ThreadLocalMap$Entry`), and the classification a reader should reach in thirty seconds |

## Part 5 diagrams

| # | Diagram | Syllabus leaf | Type | Must show |
|---|---|---|---|---|
| D-213 | The 55-item trap index, grouped | 5.2.1–5.2.55 | table | Every one of the 55 traps as a row. Columns: the wrong belief verbatim, the symptom it produces in production, the fix, and the syllabus leaf that teaches it. Grouped by the same headings as §5.2 |
| D-214 | The numbers drill card | 5.3.2 | table | Every constant in the leaf as a row: 1 MB stack, 64 B cache line, 128 B `@Contended` padding, `TREEIFY_THRESHOLD = 8`, `UNTREEIFY_THRESHOLD = 6`, `MIN_TREEIFY_CAPACITY = 64`, `MIN_TRANSFER_STRIDE = 16`, load factor 0.75, `CAPACITY = 2^29 − 1`, common-pool parallelism `availableProcessors() − 1`, virtual-thread parallelism `availableProcessors()`, maxPoolSize 256, `common.maximumSpares` 256, `Flow.defaultBufferSize() = 256`, pinned threshold 20 ms, `GuaranteedSafepointInterval` 1000 ms, RW-lock 16/16 split (65 535), priorities 1/5/10. Columns: value, what it controls, what changes either side of it |
| D-215 | The version drill | 5.3.6, 2.15.15 | table | Rows: `synchronized` pinning, scoped values, structured concurrency, `Thread.stop`, biased locking, compact object headers, `ExecutorService implements AutoCloseable`, `Unsafe` memory access. Columns: the release, the direction of the change, the JEP number, what is true on Java 21, what is true on Java 25 |
| D-216 | The diagnosis decision tree | 5.3.5, 5.1.98, 5.1.99 | decision-tree | Root: is CPU high or low? High → is it GC, a spin loop, or a livelock retry? Low → are threads BLOCKED (contention), WAITING on a queue (idle or starved), or is the JVM idle with sockets in CLOSE_WAIT (pinning)? Every leaf names the command to run next and the expected evidence |
| D-217 | The two-minute thread-safety answer template | 5.3.10 | step-sequence, 5 frames | One frame per beat: state the invariant → state the policy (confinement, immutability, locking) → state the mechanism → state the cost → state the failure mode you accept. Worked once on "make `FundsLedger.reserveStake` thread-safe", with the actual sentences a candidate would say written in each frame |
| D-218 | The whiteboard set | 5.3.8, 5.1.116–5.1.127 | table | Rows: bounded buffer, thread-safe singleton, rate limiter, LRU cache, alternating printers, dining philosophers. Columns: the primitives it needs, the invariant, the trap the interviewer is watching for, the target time, and the section of Part 4 that builds it |

