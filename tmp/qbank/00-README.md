# Diagnostic Question Bank — Level Assessment (Backend, ~3–4 YOE)

**Purpose:** Discover your ACTUAL level across the full backend-engineering
landscape. This bank is deliberately broader than `tmp/gaps.md` — it assumes
nothing. Results from this bank will be used to ENHANCE gaps.md (add gaps we
didn't anticipate, confirm or delete ones we guessed), not the other way around.

**Scope:** Everything except system design (HLD), excluded by declaration —
that track starts from zero regardless of what a test would show.

## Files

| File | Topic | Est. time |
|---|---|---|
| `01-dsa-readiness.md` | DSA: timed problems + complexity + DS internals | 90 min |
| `02-java-core.md` | Java language + collections + modern Java | 45 min |
| `03-concurrency-jvm.md` | Threads, memory model, GC, JVM debugging | 45 min |
| `04-spring-framework.md` | DI, proxies, transactions, Spring Boot | 40 min |
| `05-jpa-persistence.md` | JPA/Hibernate mechanics and traps | 35 min |
| `06-sql-databases.md` | Hands-on SQL + indexing + transactions | 50 min |
| `07-networking-os.md` | TCP/HTTP/TLS/DNS + OS fundamentals | 40 min |
| `08-api-web-security.md` | REST design, auth, JWT, CORS, OWASP | 40 min |
| `09-messaging-caching.md` | Queues, delivery semantics, caching | 35 min |
| `10-testing-craft.md` | Testing, git, code review, debugging method | 40 min |
| `11-cloud-aws-devops.md` | AWS, Docker, CI/CD, observability, Linux | 40 min |
| `12-behavioral-inventory.md` | Story audit (not L-scored) | 45 min |
| `13-scoring-and-report.md` | Aggregate results → gaps.md enhancement | 30 min |

Total ≈ 9–10 hours. **Do NOT do this in one sitting.** Spread over 4–6
sessions (~2 topics per session). Fatigue produces false lows.

## Level definitions (used everywhere)

| Level | Name | You can... |
|---|---|---|
| **L0** | Blank | Can't answer, or answer is wrong at the definition level |
| **L1** | Recall | Define it, name it, recognize it — but can't explain how it works |
| **L2** | Mechanism | Explain HOW and WHY it works, to a junior, without hand-waving |
| **L3** | Application | Spot the bug, predict the output, write the code/query correctly |
| **L4** | Judgment | Argue trade-offs, name failure modes, tell a war story, know when NOT to use it |

**Healthy reference profile at 3–4 YOE (backend, Java/Spring):**
- **L3** expected: Java core, Spring, SQL, testing, JPA (if you use it daily)
- **L2** expected: concurrency, JVM, networking, OS, API design, cloud basics
- **L1–L2** acceptable: messaging, caching internals, DevOps depth
- **L0–L1 in a daily-use area = critical gap.** L4 anywhere = bonus signal.

The report step compares your results against this line — deltas become gaps.

## Rules (read before starting)

1. **Closed book.** No search, no AI, no docs. Exceptions marked
   `[OPEN-EDITOR]` (DSA, write-the-query, write-the-test) allow an editor/DB
   but still no search.
2. **Write your answer BEFORE reading the rubric.** Keep answers in
   `tmp/qbank/answers/<topic>.md`. Reading rubrics first inflates results by
   a full level.
3. **Stop rule per ladder:** two consecutive 0-scores ends that ladder;
   record the level reached and move on. A diagnostic that stings is working.
4. **Scoring per question:** `1` = hits the rubric's key points; `0.5` =
   right idea, missing mechanism or minor errors; `0` = wrong, blank, or
   buzzwords only. Be harsh: "I've heard of it" is 0.
5. **Level attained per topic** = highest level where you scored ≥ 50% of
   that level's points AND every level below is also ≥ 50%. No skipping —
   L3 answers on top of a hollow L2 is memorization; record L2.
6. **Breadth checklists** (end of each file): rate each item 0–3
   (0 = never heard of it, 1 = heard of it, 2 = used it, 3 = could teach it).
   Any item marked **[CORE]** rated 0–1 is a gap candidate regardless of
   ladder score. This is the unknown-unknowns net.
7. **Timed items are timed.** Real timer. Over the box = 0.5 max.
8. **Record everything.** Wrong answers are the deliverable — file 13
   consumes your per-question scores and checklist ratings to rewrite gaps.md.

## Question formats

- **explain-back** — teach it to an imaginary junior. Tests mechanism.
- **predict-output** — code/query shown; state what happens and why.
- **spot-the-bug** — code shown; find and fix the defect(s).
- **write-it** `[OPEN-EDITOR]` — produce working code/query/test in a timebox.
- **scenario** — production situation; give concrete first steps and commands.
- **discriminator** — rubric shows what L1 vs L2 vs L4 answers sound like;
  you score by the tier your answer matched.

## Suggested session split

1. 01 (DSA) alone — it's the longest and needs a fresh brain
2. 02 + 03 (Java, Concurrency/JVM)
3. 04 + 05 (Spring, JPA)
4. 06 + 07 (SQL, Networking/OS)
5. 08 + 09 (API/Security, Messaging/Caching)
6. 10 + 11 + 12, then 13 (report)
