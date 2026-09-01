# Valuation — Medium Paper 1

**Answers:** `tmp/papers/answers/M1-paper.txt` · **Key:** `tmp/papers/medium/paper-1-key.md`
**Score: 6.5 / 19** (Q9 code deferred to the all-medium code session).
**Context that matters:** the E5 wrap-up predicted ~10–12/20 *after* the
between-tier study, and the code-session valuation set a redo gate before
M1. The gate wasn't run and several answers show the primer-2/syllabus
material isn't in yet (details below) — so read 6.5/19 as "medium tier,
unprepped," consistent with the M5 preview (3.5/19), not as a ceiling.
(Q15/Q16's "Now aware" read as typos for "Not aware" — corrected me if wrong.)

## Per-question

| Q | Topic | Score | Verdict |
|---|---|---|---|
| 1 | equals/hashCode contract | **0.5** | Mechanism half-there (different buckets). Missing: the contract itself — **equal objects MUST return equal hashCodes** — and the concrete symptoms: `get(equalKey)` misses, logical duplicates coexist. |
| 2 | HashMap put | **0.5** | Skeleton right (bucket → chain on collision → resize+redistribute), and the elements-may-split-on-rehash insight is genuinely good. Corrections: capacity **doubles** (1.5× is ArrayList), resize triggers at **load factor 0.75**, and buckets ≥8 entries **treeify** to red-black trees (Java 8+). |
| 3 | `remove(10)` | **1** | Behavior + fix both right. Noted your request — this is now in `tmp/primers/quick-notes.md` (new running notes file). The name for the mechanism: **overload resolution** picks `remove(int index)` over `remove(Object)`. |
| 4 | Integer cache | **0.5** | Second and third outputs right with correct reasoning — but `a == b` for 127 prints **true**: autoboxing caches −128..127, so both 127s are the SAME object. The cache is the entire point of the question; added to quick-notes. |
| 5 | synchronized vs volatile | **0.5** | Half of each: synchronized = mutual exclusion (missing **visibility**, its second guarantee); volatile = main-memory visibility (missing ordering, missing atomicity-NOT-guaranteed). The examples you couldn't produce are primer-2 part 4 verbatim: `volatile boolean running` flag = sufficient; `counter++` = not. This is the second miss on that exact item. |
| 6 | Check-then-act | **0** | "Make it async" doesn't touch the bug: `containsKey`+`put` is a compound action — two threads both see absent and both run the expensive load. Fix: `cache.computeIfAbsent(key, this::loadFromDb)` — atomic per key. The insight being tested: **a concurrent collection makes single ops atomic, never compound ones.** |
| 7 | Proxy mechanism | **0** | Blank — the tier's most load-bearing Spring question. Answer in one line: Spring wraps the bean in a **proxy** that runs transaction/cache logic around the real call; limitation: self-calls bypass it. This blank formally confirms gaps.md §2.1 (foundations before sharp edges). |
| 8 | Self-invocation | **0** | The prediction given is wrong in the dangerous direction: `this.audit(o)` **bypasses the proxy**, so `REQUIRES_NEW` is silently ignored — audit joins the outer transaction (it does NOT get its own). Fixes: move audit to a separate bean, or self-inject the proxy. "Make it async/non-transactional" changes the requirement rather than fixing the mechanism. Q7+Q8 fall together — learn the proxy model and both become obvious. |
| 9 | `[CODE]` top-2 per dept | **—** | Deferred to the all-medium code session (with M5 Q1 and the redo gate still owed). |
| 10 | Composite index | **0.5** | (b) ✓, (c) right outcome. (a) wrong: `WHERE customer_id = 42` uses the index fine — the **leftmost-prefix rule**: `(customer_id, created_at)` is sorted by customer_id first, so leading-column queries seek directly; only created_at-alone (c) can't. Also: B-tree indexes are sorted structures, not "group hashes." |
| 11 | URL walkthrough | **0.5** | Order and DNS-caching right; both handshakes honestly flagged unknown. The two missing sentences: TCP = **SYN → SYN-ACK → ACK**; TLS = server proves identity via **certificate chain**, then both sides agree symmetric **session keys**. |
| 12 | Timeouts | **0.5** | Connect vs read distinction right. What each *tells you*: connect-fail = host down/wrong port/firewall (not just latency); read-fail = connected but server slow/stuck. The default many Java clients ship: **none — infinite** (that's why "hangs" happens at all; 10/30s is what you *should set*, not what you get). |
| 13 | PUT/PATCH/POST | **1** | Best answer of the paper — semantics, idempotency per method, and the PATCH-array-append nuance is exactly the right example. |
| 14 | Pagination | **0** | Blank — was on the M5-preview syllabus (keyset). Now covered in primer-3 §3 quick form; full treatment stays on the syllabus. |
| 15 | Delivery semantics | **0** | Blank. Primer-2 part 2 gives the lifecycle; the taxonomy is one line on top: ack BEFORE processing = at-most-once (can lose), ack AFTER = at-least-once (can duplicate — the practical default), exactly-once = at-least-once + **idempotent consumer**. Now also in primer-3 §4. |
| 16 | Cache-aside | **0** | Chapter requested → **primer-3 §1**. Note: you already *do* half of this — your E2 TTL answer described the cache-aside read path perfectly. The gap is the named pattern + the write path (delete-vs-update race). Vocabulary gap more than concept gap. |
| 17 | Mock/stub/fake | **0** | Chapter requested → **primer-3 §2** (taxonomy + the what-to-mock decision rule). |
| 18 | Clock injection | **0** | Blank — will be central in the medium code session (M4 Q17 needs it). Primer-3 §5 one-pager. |
| 19 | IAM roles | **0.5** | Direction partially off: granularity isn't the differentiator (access keys attach to the same policy engine). The mechanical answer: roles give **temporary, auto-rotated credentials** vended by the platform — no static secret to leak, rotate, or commit. |
| 20 | Liveness/readiness | **0.5** | Definitions right. Actors: liveness → orchestrator (restarts); readiness → load balancer (routes). The storm: liveness wired to a DB outage = orchestrator restart-loops perfectly healthy pods during the outage. |

## Section rollup

| Section | Score | Note |
|---|---|---|
| DSA/Internals | 1/2 | Structure knowledge forming; constants wrong |
| Java Core | 1.5/2 | remove-overload solid; Integer cache new trap logged |
| Concurrency | 0.5/2 | Volatile examples = repeat miss; compound-action blind spot |
| Spring/JPA | 0/2 | **Proxy model = the single highest-leverage study item on the board** |
| SQL & DB | 0.5/1 | Leftmost-prefix rule missing (code deferred) |
| Networking | 1/2 | Skeleton right, handshake internals owed |
| API/Security | 1/2 | PUT/PATCH/POST full marks; pagination blank |
| Messaging/Caching | 0/2 | Both blanks; both now chaptered in primer-3 |
| Testing | 0/2 | Test-doubles taxonomy + Clock — primer-3 |
| Cloud | 1/2 | Halves on both |

## Findings

1. **The unprepped-entry hypothesis is confirmed by the data:** predicted
   10–12 after study, actual 6.5 without it; the misses cluster on primer-2
   items (volatile examples, delivery semantics) and the M5-preview
   syllabus (pagination, proxy model, test doubles). The instrument is
   working — but taking M2 in this state will just re-measure the same
   thing. **Recommendation: pause papers; run the redo gate + primer-2 +
   primer-3 + syllabus (~1 week); then M2.**
2. **Highest-leverage single item: the Spring proxy model** (Q7+Q8 = 0/2
   together, and it unlocks @Transactional/@Cacheable/self-invocation/AOP
   questions across M2–M4 and real interviews). §2.1 now confirmed at
   medium tier.
3. **Concurrency depth gap distinct from the repaired basics:**
   compound-action reasoning (Q6) and the volatile examples (2nd miss).
   The easy-tier closure stands; the medium layer needs the qbank 03
   ladder as study material, not just papers.
4. **New traps logged to quick-notes:** Integer cache −128..127; HashMap
   doubling/0.75/treeify constants; leftmost-prefix rule; infinite default
   timeouts.
5. **Requests fulfilled:** running notes file created
   (`tmp/primers/quick-notes.md` — your Q3 "add to notes" plus today's
   traps); chapters written (`tmp/primers/primer-3.md`: cache-aside, test
   doubles, keyset pagination quick form, delivery semantics, Clock).

## Actions taken

- `tmp/primers/quick-notes.md` — created (running keep-list; future "add
  this to notes" requests append here).
- `tmp/primers/primer-3.md` — created (5 short chapters, all requested or
  blank-driven).
- `tmp/gaps.md` §9 — M1 evidence appended.
- No paper modifications: M2–M4 already retest everything here.
- Deferred code list: E2 Q2, E4 Q2, E5 Q10, M5 Q1 (redo gate) + M1 Q9.

## Sequencing recommendation (stronger than usual)

The last three data points (M5 3.5, code session 1/3, M1 6.5) all say the
same thing: the bottleneck is now STUDY, not measurement. One focused week
— redo gate, primer-2 self-check, primer-3, proxy model, then M2 — should
move the next score into double digits. Taking M2 sooner spends a fresh
paper to learn what we already know.