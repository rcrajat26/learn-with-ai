# Understanding Ledger

What the candidate reliably knows, per topic, as measured by the diagnostic papers —
not what the study plan intends to teach. This is the counterpart to
`src/knowledge/gaps.md`: gaps says what is missing, this says what is banked.

**Evidence universe (as of 2026-08-21):** easy papers E1–E5 (99 scored answers),
the deferred easy-tier code session (3 items), the accidental medium preview M5,
and medium papers M1–M2 — valuations in `tmp/valuations/`, raw answers in
`tmp/papers/answers/`, running evidence log in `tmp/gaps.md` §9.
No hard-tier data exists. Medium tier was taken **without** the prescribed
between-tier study, so medium scores measure an unprepped state, not a ceiling.

**Reconciled against `src/knowledge/gaps.md` (pass 2).** Each topic below carries a
cross-link to its gaps.md section. Where gaps.md's per-topic status contradicted a
score here, the score was lowered and the contradiction cited in place — five topics
moved (04, 11, 12, 16, 18) and are marked **[revised]**. Three ad-hoc papers now
exist covering previously unmeasured territory (`tmp/ad-hoc-paper-1..3.md`); they
are **not yet taken**, so they contribute no scores — they appear here only as the
named upcoming measurement for the LOW and NONE rows.

## The scale (from `tmp/qbank/00-README.md`)

| Level | Name | The candidate can... |
|---|---|---|
| **L0** | Blank | Not answer, or answer wrong at the definition level |
| **L1** | Recall | Define it, name it, recognize it — but not explain how it works |
| **L2** | Mechanism | Explain HOW and WHY, to a junior, without hand-waving |
| **L3** | Application | Spot the bug, predict the output, write the code/query correctly |
| **L4** | Judgment | Argue trade-offs, name failure modes, tell a war story, know when NOT to use it |

Half-levels are used where the evidence straddles two bands (e.g. L2.5 = mechanism
solid, application intermittent). Healthy reference for 3–4 YOE backend: L3 in Java
core / Spring / SQL / testing / JPA, L2 in concurrency / JVM / networking / OS /
API / cloud, L1–L2 in messaging / caching internals / DevOps depth.

**Measurement confidence** is about the instrument, not the candidate:

- **HIGH** — probed repeatedly across ≥3 papers, or across two tiers, with a
  consistent signal. The score would survive a retest.
- **LOW** — 2–4 probes, single tier, or a split signal. Directionally right,
  numerically soft.
- **NONE** — not meaningfully measured. Score recorded as `—`; no guess is made.

## At a glance

| # | Topic | Score | Trend | Confidence |
|---|---|---|---|---|
| 01 | DSA fundamentals | **L1.5** | flat theory; code session exposed a write gap | HIGH |
| 02 | Java collections | **L2** | steady easy tier; internals soften at medium | HIGH |
| 03 | Java core | **L2** | 1.5 → 1 → 2 → 1.5 → 2 across E1–E5 | HIGH |
| 04 | Modern Java | **L1** *[revised]* | no retests | LOW |
| 05 | Multithreading & concurrency | **L1.5** | 0.5 → 0.5 → 1.5 → 2.0 → 1.0 (E1–E5), 0.5 at M1 | HIGH |
| 06 | JVM internals | **L1** | no retests | LOW |
| 07 | Spring core | **L1.5** | strong at easy tier, 0/2 on the proxy model at M1 | HIGH |
| 08 | Spring Data JPA | **L1** | 1.5 → 2 → 0.5 → 1.5 → 1.5 (E1–E5), 0 at M5/M1 | HIGH |
| 09 | SQL & databases | **L1.5** | 1 → 1 → 1.5 → 0.5 → 1.5 (E1–E5); ACID 0 → 0.5 | HIGH |
| 10 | Networking | **L1.5** | 1.5 → 2 → 0.5 → 1.5 → 1 (E1–E5), 1/2 at M1 | HIGH |
| 11 | OS & Linux | **—** *[revised]* | — | NONE |
| 12 | API design | **L2** *[revised]* | 2 → 1 → 1.5 → 2.5/3 → 1.5 (E1–E5); full marks at M1 | HIGH |
| 13 | Web security | **L1.5** | password storage 0 → 1 (retest passed) | HIGH |
| 14 | Messaging & queues | **L1** | 1 → 1 → 0.5 → 0.5 → 0.5, then 0 at M1/M2/M5 | HIGH |
| 15 | Caching | **L2.5** | consistently strong E1–E5; full marks at medium tier | HIGH |
| 16 | Testing | **L1** *[revised]* | 1.5 → 1.5 → 2 → 1 → 1.5 (E1–E5), 0/2 at M1 | HIGH |
| 17 | Git craft | **L2** | steady on daily ops; recovery layer untouched | HIGH |
| 18 | Cloud & AWS | **L1** *[revised]* | 1.5 → 0.5 → 2 → 1.5 → 1.5 (E1–E5) | HIGH |
| 19 | Docker & Kubernetes | **L1** | no retests | LOW |
| 20 | Observability & operations | **—** | — | NONE |
| 21 | REST architecture | **L2** | self-assessed; verified against Richardson model | HIGH |

Counts: **16 HIGH**, **3 LOW** (04, 06, 19), **2 NONE** (11, 20).

**Score changes in pass 2**, each forced by a gaps.md status line rather than by new
evidence — no paper has been taken since pass 1:

| Topic | Old | New | Why |
|---|---|---|---|
| 04 Modern Java | L1.5 | **L1** | gaps.md §04 is UNMEASURED with "everything after Java 8" at HIGH severity; two of the three probes sit in the Java-8 corner, so L1.5 generalized one strong stream answer across a guide that spans 8–21. |
| 11 OS & Linux | L1 | **—** | gaps.md §11: "Two questions in nine papers" and "**None established** — the topic has never scored above 0.5." Two probes meets this ledger's own NONE threshold; the process/thread repair I credited here belongs to topic 05, where the retest actually happened. |
| 12 API design | L2.5 | **L2** | gaps.md §12: "MEASURED (basics), UNMEASURED (design specifics) … every question above the definition line came back blank." L2.5 aggregated a genuinely strong basics half across a topic whose design half is untouched. |
| 16 Testing | L1.5 | **L1** | gaps.md §16 rates the test-double taxonomy **CRITICAL** (L0 in a daily-use area), alongside four medium-tier zeros and an inverted integration-test definition. |
| 18 Cloud & AWS | L1.5 | **L1** | gaps.md §18 states the conclusion outright: "real level ≈ **L1, not L2**" — below the reference line for this topic. |

Topics where gaps.md and this ledger already agreed and nothing moved: 01, 02, 03,
05, 06, 07, 08, 09, 10, 13, 14, 15, 17, 19, 20.

## Reading the profile in one paragraph

The shape is consistent across 140+ scored answers: a solid conceptual scaffold at
the easy tier (~71% aggregate) that thins sharply the moment a question asks for a
mechanism, an unprompted problem shape, or a keyboard. Three topics are genuinely
banked — caching, API/idempotency semantics, and (post-repair) the language
substrate of Java core. Three are load-bearing holes with names attached: the Spring
proxy model, the broker message lifecycle, and code write-fluency. Everything else
sits at L1–L2, which is roughly where the reference profile expects a 3–4 YOE
engineer to be for the peripheral topics and one band below it for the daily-use
ones (JPA, SQL).

---

## 01 — DSA fundamentals

**Score: L1.5** (`tmp/valuations/E1-valuation.md` … `E5-valuation.md` §DSA rollups;
`tmp/valuations/code-session-valuation.md`)

**Trend:** DSA section across E1–E5: 1.5 → 1/1 → 2 → 1/1 → 1.5. Theory flat and
respectable; the code session (1/3) is what moved the score down.

**Commentary.** Complexity reasoning is reliable at mechanism level: the triangular
nested-loop analysis (E2 Q1), binary search preconditions plus log₂(10⁶) ≈ 20 by
head (E3 Q2), and the four-way complexity comparison in E1 Q1 were all clean. The
recursion answer (E5 Q2 — base case, progress, StackOverflowError) was full marks.
Below that surface, three things are missing and they are different in kind:
structure internals (PriorityQueue is "end of the queue," not a binary heap root —
M5 Q2, 0), the vocabulary for what he already does correctly (amortized analysis
blank at M2 Q1 despite explaining ArrayList growth correctly at E4 Q1), and
implementation. The code session is the decisive datum: E2 Q2 came back as a
correct algorithm written in English rather than Java, and M5 Q1 (longest
substring) — the only real algorithm problem in the set — was never attempted.
Cache-locality reasoning is absent too: E5 Q1 explained arrays winning by "bigger
memory in latest hardwares" rather than contiguity and prefetch.

**Calibration note.** He does not over-rate this area; if anything the theory is
better than the score suggests, and the write-fluency gap is a separate axis that
the ledger deliberately lets drag the number down.

**Measurement confidence: HIGH** for what was sampled — five papers plus a dedicated
code session. Scope caveat added in reconciliation: gaps.md §01 is PARTIALLY
MEASURED because "pattern recognition beyond binary search and hashing has **never**
been asked" — sliding window, monotonic stack, fast/slow pointers, BFS/DFS,
backtracking, DP, graphs, tries and union-find are all untouched. The L1.5 therefore
describes complexity reasoning plus write-fluency, not pattern selection.
**Upcoming measurement: ad-hoc paper 1** (Section 1, DSA pattern recognition).

**Gaps: see gaps.md §01 — DSA fundamentals.**

## 02 — Java collections

**Score: L2** (E1 Q2, E3 Q1, E4 Q1, E5 Q3; M1 Q1–Q3; M2 Q3; M5 Q2)

**Trend:** stable at the easy tier; drops to ~L1.5 the moment medium-tier internals
are probed.

**Commentary.** He reasons about which structure fits correctly and consistently —
HashMap vs TreeMap ordering and complexities (E3 Q1), the List/Set/Map defining
properties with sensible examples (E5 Q3), and the `remove(10)` overload-resolution
trap solved outright with the right fix (M1 Q3). The HashMap `put` walkthrough (M1
Q2) had the correct skeleton — bucket, chain on collision, resize and redistribute —
including a genuinely good observation that entries may split across buckets on
rehash. What fails is two-layered: constants and names. Capacity doubling was given
as 1.5× (that is ArrayList), load factor 0.75 and treeification at 8 entries were
absent, `ArrayDeque` could not be named for either the queue or stack role (E1 Q2)
despite the queue/stack logic being right, and ConcurrentModificationException is a
flat blank (M2 Q3). The equals/hashCode contract is half-known: he can describe
"different buckets" but not state the contract or its symptoms (M1 Q1).

**Calibration note.** This is the clearest instance of a pattern that recurs across
the profile — reasoning intact, recall of the identifier missing. It reads far
worse in an interview than it is.

**Measurement confidence: HIGH** — eight probes across both tiers. gaps.md §02 agrees
(MEASURED at easy, PARTIALLY MEASURED at medium) and adds that the internals half of
the guide — LinkedHashMap as an LRU, TreeMap red-black navigation, bucket indexing,
`Iterator.remove`/`removeIf`, EnumSet — is unsampled; **ad-hoc paper 1** (Section 2)
covers the highest-value subset. Score unchanged.

**Gaps: see gaps.md §02 — Java collections.**

## 03 — Java core

**Score: L2** (E1 Q3–Q4, E2 Q3–Q4, E3 Q3–Q4, E4 Q3, E5 Q4; M1 Q4; M2 Q4; M5 Q3)

**Trend:** Java Core section E1–E5: 1.5 → 1 → 2 → 1.5 → 2. Improving, with E3's
`final` answer the single best piece of work in the easy tier.

**Commentary.** The substrate is solid. `==` vs `equals` with correct pool-vs-heap
reasoning (E1 Q3), all three uses of `final` including the reference-vs-contents
nuance on a final List — exactly the trap the question set — plus the unprompted
observation that abstract classes cannot be final (E3 Q3), primitives vs wrappers
(E3 Q4), and generics (E5 Q4). The recurring defect is the *why* clause rather than
the *what*: static was described correctly as class-level but the reason a static
method cannot touch instance fields (no `this`) went unsaid (E4 Q3); checked vs
unchecked exceptions were exemplified correctly but the mechanism was given as
"compiler isn't aware of unchecked," which is the wrong model (E2 Q3); default
methods were attributed to abstract classes as a differentiator (E2 Q4). At the
medium boundary the floor drops: type erasure and PECS are "entirely new" (M2 Q4,
his words), the Integer cache (−128..127) is unknown (M1 Q4), and defensive copying
was omitted from an explicitly immutability-focused question (M5 Q3).

**Calibration note.** Generics is the flagship under-rating: he wrote "Generics
concept is not that clear to me" and then produced a full-marks answer (E5 Q4).
That self-flag was wrong, and the same instinct suppresses good answers elsewhere.

**Measurement confidence: HIGH.** gaps.md §03 concurs (MEASURED, the most heavily
sampled topic after SQL) and files the recurring 0.5s as one gap — "mechanism-level
precision on language rules" — which is the same reading as above. Score unchanged.
Note that BigDecimal and `Optional` are queued in **M4 Q3/Q4**, so they are
deliberately absent from the ad-hoc papers.

**Gaps: see gaps.md §03 — Java core.**

## 04 — Modern Java

**Score: L1** *(revised in pass 2 from L1.5)* (E3 Q8, E4 Q4, M5 Q4)

**Trend:** no retest exists. Optional went from "not sure" at E3 Q8 to being cited
with correct uses at M5 Q4, which is suggestive but unverified.

**Commentary.** Stream pipelines can be traced accurately — E4 Q4 predicted the
output of a lowercase → filter → distinct chain with exact reasoning, which is L3
work on that narrow item. Records and Optional are known at usage level. Everything
after Java 8 is not: sealed interfaces, pattern-matching switch, virtual threads
and text blocks were self-flagged unknown at M5 Q4, and the candidate himself
identified functional interfaces and streams as "the Java 8 half" of his answer.

**Reconciliation (pass 2): score lowered L1.5 → L1.** gaps.md §04 marks the topic
UNMEASURED, rates "everything after Java 8" **HIGH** severity, and observes that
offering streams and functional interfaces as "modern" dates the mental model to
2014. Two of the three probes sample the Java-8 corner, so L1.5 was generalizing one
strong stream-prediction answer across a guide that spans Java 8 through 21. Within
that corner alone the evidence still reads ≈L2.5; across the guide it is L1.
`Optional` is separately **IN VERIFICATION** at M4 Q3, so it is not an ad-hoc target.

**Measurement confidence: LOW** — three probes, one tier each, no retest. The
Java-8-fine / Java-9-21-blank split is directionally trustworthy; the exact level
is not. **Upcoming measurement: ad-hoc paper 1** (Sections 3 and 4 — streams and
`Optional`, then language features 9–21), which gaps.md notes covers this topic
heavily.

**Gaps: see gaps.md §04 — Modern Java (8–21).**

## 05 — Multithreading & concurrency

**Score: L1.5** (E1 Q5–Q6, E2 Q5–Q6, E3 Q5–Q6, E4 Q5–Q6, E5 Q5–Q6; M1 Q5–Q6;
M2 Q5, Q7; M5 Q5)

**Trend (the best-documented in the whole ledger):** section score across
E1 → E2 → E3 → E4 → E5 = **0.5 → 0.5 → 1.5 → 2.0 → 1.0**, then **0.5/2 at M1**.
The 0.5 → 2.0 climb is the primer (`tmp/primers/concurrency-primer.md`) working,
verified on two independent retests: heap-vs-stack (E3 Q5, a direct retest of the
E1 Q5 zero) and start-vs-run (E4 Q5).

**Commentary.** This is the one area where a repair has been observed end to end,
and it is worth naming precisely what was repaired: the memory model (objects on
heap, references and primitive locals on stack), thread lifecycle basics, `start()`
vs `run()`, and GC eligibility. Those are now reliably L2. Three things were not
repaired. First — the asterisk on the closure — **volatile**: at E5 Q5 he answered
that `volatile int counter; counter++` is thread-safe, despite primer §3 covering
it verbatim, and missed the same distinction again at M1 Q5, making it a two-paper
miss on identical material. Second, compound actions: `containsKey` + `put` was not
recognized as a check-then-act race, and the proposed fix ("make it async") does
not touch the bug (M1 Q6); the underlying insight — a concurrent collection makes
single operations atomic, never compound ones — is absent. Third, everything above
the basics: thread pools were "not aware" (E2 Q5), ThreadPoolExecutor blank (M2 Q6),
BLOCKED vs WAITING blurred (E5 Q6), and double-checked locking's volatile is
understood as visibility rather than reordering (M5 Q5). Deadlock sits oddly in
between — recognized on sight at M2 Q5, but the two-lock circular-wait setup has
never been written out (E3 Q6 was submitted as an unfilled `***ADD ANSWER HERE***`
placeholder).

**Calibration note.** The volatile miss is the clearest over-trust in the profile:
stated confidently, twice, wrong both times, on material he has read. Contrast with
generics, where he hedged and was right. Confidence is currently anti-correlated
with correctness on exactly these two clusters.

**Measurement confidence: HIGH** — eleven probes across three tiers with two clean
retests. gaps.md §05 counts thirteen and calls it "the most-instrumented topic, and
the only completed study→verify loop in the whole exercise" — same conclusion. It
also rates thread-pool mechanics **HIGH** with the sharper detail that the primer's
§4 already covered it and M2 Q6 (blank) postdates the primer, making it a second
remediation failure alongside volatile. Score unchanged.

**Gaps: see gaps.md §05 — Multithreading & concurrency.**

## 06 — JVM internals

**Score: L1** (E3 Q5, E4 Q6; M5 Q6, Q19)

**Trend:** no retests within this topic.

**Commentary.** Two easy-tier items landed: garbage collection by unreachability,
including the correct note that `System.gc()` is only a hint (E4 Q6), and the
heap/stack division (E3 Q5). Beyond that there is nothing. The OOM taxonomy is
wrong at the definition level — StackOverflowError was offered as a kind of OOM,
and heap space / unable-to-create-native-thread / Metaspace were not named (M5 Q6);
the container-vs-JVM memory interaction behind OOMKilled is blank (M5 Q19). The
entire diagnostic toolkit named in `src/topics/06-jvm-internals.md` — jstack, jcmd,
jmap, jstat, thread and heap dumps, container flags — has never been probed by any
paper, so its absence from this ledger is an instrument gap, not a finding.

**Measurement confidence: LOW** — four probes, two of them easy-tier one-liners,
and the topic's largest sub-area untested. gaps.md §06 goes one step further and
marks the topic UNMEASURED; the score is retained at L1 rather than dropped to `—`
because four probes clear this ledger's NONE threshold and they agree with each
other (conceptual passes, diagnostic blanks). Treat L1 as provisional until the
paper is taken. **Upcoming measurement: ad-hoc paper 1** (Section 5 memory and
errors, Section 6 the jcmd/jstack/jmap/jstat diagnostic toolkit).

**Gaps: see gaps.md §06 — JVM internals.**

## 07 — Spring core

**Score: L1.5** (E1 Q7–Q8, E2 Q7, E4 Q7, E5 Q7; M1 Q7–Q8)

**Trend:** Spring/JPA section E1–E5: 1.5 → 2 → 0.5 → 1.5 → 1.5 (the E3 dip is an
`Optional` miss, not a Spring one). Then **0/2 at M1** on the proxy pair.

**Commentary.** Application-level Spring is genuinely fluent: dependency injection
and constructor injection with IoC, decoupling, testability and
dependencies-resolved-before-bean-creation all present unprompted (E1 Q7); Boot
starters, auto-configuration and the embedded server (E2 Q7); profile overrides
(E4 Q7); `@RestController` = controller + `@ResponseBody`, JSON rather than a view,
Jackson doing the serialization (E5 Q7). Stereotype annotations were 0.5 — the
"semantic markers over identical mechanics" framing is right, but `@Repository`'s
persistence-exception translation, the one that is not decorative, was missed
(E1 Q8). Against that, **the proxy model is a 0/2**: Q7 (how `@Transactional` and
`@Cacheable` actually intercept a call) was left blank, and Q8's self-invocation
prediction was wrong in the dangerous direction — he expects `this.audit(o)` with
`REQUIRES_NEW` to get its own transaction, when the call bypasses the proxy entirely
and silently joins the outer one. M1's valuation calls this "the single
highest-leverage study item on the board," and that judgment holds: the two
questions fall together, and the mechanism unlocks AOP, caching, and transaction
questions across the remaining papers.

**Measurement confidence: HIGH** — seven probes across both tiers, with the medium
result unambiguous. gaps.md §07 rates the proxy model **CRITICAL** (L0 in a
daily-use framework area) rather than merely highest-leverage, and records it as
CHAPTERED but unverified, with M3 Q7/Q8 and M4 Q7/Q8 as the queued retests. That is
a severity sharpening, not a contradiction; score unchanged at L1.5, which already
reflects the 0/2.

**Gaps: see gaps.md §07 — Spring core.**

## 08 — Spring Data JPA

**Score: L1** (E2 Q8, E3 Q7, E4 Q8; M2 Q8; M5 Q7–Q8)

**Trend:** easy-tier JPA items scored well (E2 Q8 full marks); every medium-tier
JPA item is a zero.

**Commentary.** What exists is the annotation surface: `@Entity`, `@Id` and
`@GeneratedValue` all correctly described (E2 Q8), and `@Transactional`'s outcome
semantics — all commit or all roll back (E3 Q7, though the question's first clause,
what *starts* when the method is entered, went unanswered). LAZY vs EAGER are
defined correctly but the per-association defaults are unknown (E4 Q8) — which
matters because those defaults are the root of most N+1 stories. Everything at
mechanism level is blank: the persistence context and entity states
(transient/managed/detached/removed — M2 Q8), `LazyInitializationException`
(M5 Q7), and the N+1 problem itself (M5 Q8). For a daily-use technology in the
reference profile's L3 column, L1 is the largest single delta in this ledger.

**Measurement confidence: HIGH** — six probes, consistent across tiers. gaps.md §08
raises both JPA sharp edges (LazyInitializationException, N+1) and entity lifecycle
states to **CRITICAL** on the L0-in-a-daily-use-area rule, with M4 Q7/Q8 as the
retests; it also notes the schema-migration answer (E5 Q8 = 0.5) belongs here rather
than under SQL. Score unchanged at L1 — the largest delta against the reference
profile in this ledger.

**Gaps: see gaps.md §08 — Spring Data JPA.**

## 09 — SQL & databases

**Score: L1.5** (E1 Q9–Q10, E2 Q9–Q10, E3 Q9–Q10, E4 Q9–Q10, E5 Q8–Q9, Q10b;
M1 Q10; M2 Q9–Q10; M5 Q9–Q10; code session E5 Q10)

**Trend:** SQL section E1–E5: 1 → 1 → 1.5 → 0.5 → 1.5. **ACID specifically: 0 (E4
Q10) → 0.5 (E5 Q10b retest)** — partial repair, gap still open.

**Commentary.** Relational concepts are present and better than the candidate's own
self-assessment: WHERE vs HAVING both defined correctly (E1 Q9), primary/foreign/
unique key properties (E3 Q9), DELETE vs TRUNCATE vs DROP with correct selectivity
(E5 Q9). The defects are in mechanics and in composition. Mechanics: `WHERE x =
NULL` was believed to throw when it silently returns zero rows (E4 Q9); indexes are
"faster search, costs space," missing both what they accelerate (ranges, sorts,
joins) and the real cost, index maintenance on every write (E3 Q10); the
leftmost-prefix rule for composite indexes is unknown, and B-trees were described as
"group hashes" (M1 Q10); planner behaviour, NOT IN with NULLs, keyset pagination and
lost-update anomalies are all blank (M2 Q9–Q10, M5 Q9–Q10). Composition is the more
interview-relevant half: at E2 Q10 he produced GROUP BY and HAVING correctly *when
the question named the operations*, but at the code session, where "total per
customer exceeding 10,000" only implied aggregation, he wrote a row-level filter
with no GROUP BY at all. Prompted recall exists; unprompted recognition of the
problem shape does not.

**ACID, specifically.** E4 Q10 scored 0 with two properties blank and two
misdefined. The E5 Q10b scenario retest recovered Atomicity cleanly
(crash mid-transfer → no half-transfer), which is real progress — but the
**Isolation ↔ Consistency swap persists** (he named Consistency for "the report
never sees intermediate state") and Durability was mapped onto Isolation. Treat
Atomicity as anchored and the other three as not yet learned.

**Measurement confidence: HIGH** — nineteen probes here, sixteen by gaps.md's
narrower attribution (it files E5 Q8 migrations under JPA and M1 Q14 pagination
under API design); either way this is the densest coverage in the set and gaps.md
reaches the same verdict, "MEASURED … the most consistently weak theme across the
whole easy tier." One correction absorbed from gaps.md §09: at M1 Q10 the
leftmost-prefix rule was not merely missing but **inverted** — `WHERE customer_id =
42` on `(customer_id, created_at)` was judged unusable when it seeks directly.
Score unchanged.

**Gaps: see gaps.md §09 — SQL & databases.**

## 10 — Networking

**Score: L1.5** (E1 Q11–Q12, E2 Q12, E3 Q11, E4 Q11–Q12, E5 Q11–Q12; M1 Q11–Q12;
M2 Q11–Q12; M5 Q11–Q12)

**Trend:** Networking/OS section E1–E5: 1.5 → 2 → 0.5 → 1.5 → 1; 1/2 at M1, 0/2 at
M2.

**Commentary.** The vocabulary layer is reliable — TCP vs UDP with correct
guarantees and apt examples (E1 Q11), IP vs port with 80/22 (E2 Q12, above the
bar), loopback (E4 Q11), and a correct DNS walk including TLD delegation and the A
record lookup (E5 Q11, after the A-record blank at E1 Q12). Below it, the
handshakes are a hole he is honest about: the URL-to-page sequence skipped from DNS
straight to "hit the server on 443," omitting the TCP three-way handshake and the
TLS handshake entirely (E5 Q11), and at M1 Q11 he flagged both as unknown outright.
TLS goals as a set (confidentiality, integrity, authentication) are blank (M2 Q12);
HTTPS was answered as encryption only, with the attacker's read-and-modify
capabilities left vague (E3 Q11). Two operational items are worth naming: default
socket timeouts are believed to be finite when most Java clients ship with none —
which is precisely why "it hangs" happens (M1 Q12) — and ephemeral-port exhaustion
under TIME_WAIT was diagnosed as "thread pool exhausted" (M2 Q11), the wrong
mechanism with the right vocabulary. Application-layer transports are conflated:
webhook was offered as an example of SSE (M5 Q11), and epoll-style readiness
multiplexing is unknown (M5 Q12).

**Measurement confidence: HIGH** — thirteen probes across three tiers. gaps.md §10
splits the verdict as "MEASURED (breadth), UNMEASURED (depth) … they cluster on
definitions; every mechanism question came back partial or blank," which is the same
finding stated as a status. It rates the TCP+TLS handshake gap **HIGH** on the
grounds that four probes produced no improvement and the URL→page walk is the
single most-asked networking question in existence. Score unchanged at L1.5, which
is precisely the breadth-without-depth reading.

**Gaps: see gaps.md §10 — Networking.**

## 11 — OS & Linux

**Score: —** *(revised in pass 2 from L1)* (E3 Q12, E4 Q12)

**Trend:** the process/thread memory model went from answered-backwards (E1 Q5, 0)
to correct after the concurrency primer (E3 Q5, 1) — but that retest is credited to
topic 05. No Linux-tooling retest has been run.

**Commentary.** Two distinct sub-areas with different verdicts. Conceptually, the
process-versus-thread model was initially inverted (he had threads sharing the stack
and owning the heap — exactly backwards) and is now repaired at the memory-model
level. Operationally, there is nothing: `top` and `kill` versus `kill -9` scored a
flat zero at E3 Q12 — the cheapest points on that paper — and the topic's whole
command set (ps, lsof, ss, strace, dmesg, journalctl) has never been probed. E5 Q12
showed the shape of the gap well: he defined a firewall correctly but could not
produce the two concrete causes an unreachable app usually has (inbound port not
allowed in the security group; the process bound to 127.0.0.1 rather than 0.0.0.0).
This is keyboard practice, not reading, and the valuations have said so twice.

**Reconciliation (pass 2): score withdrawn, L1 → `—`, confidence LOW → NONE.**
gaps.md §11 is unambiguous: status UNMEASURED, "two questions in nine papers, one of
them a flat zero," and under strengths, "**None established** — the topic has never
scored above 0.5." Two probes is exactly this ledger's NONE threshold. The pass-1
score also leaned on evidence that is not this topic's: the process/thread repair
was retested at E3 Q5 and is credited to topic 05 (concurrency), E5 Q12's firewall
question is networking, and M5 Q12's epoll question is filed under networking too.
Stripping those leaves E3 Q12 (tooling, 0) and E4 Q12 (SSH auth, 0.5) — not enough
to place a level, and no level is guessed. The two confirmed gaps stand on their own
evidence: hands-on tooling is rated **HIGH** by gaps.md, with the prescribed fix
being keyboard practice rather than reading.

**Measurement confidence: NONE.** **Upcoming measurement: ad-hoc paper 2**, which
gaps.md notes is dedicated to this topic (Section 1 processes/threads/signals,
Section 2 diagnosing a sick box); **M4 Q12** (production box triage) is the
separately queued retest for the tooling gap.

**Gaps: see gaps.md §11 — Operating systems & Linux.**

## 12 — API design

**Score: L2** *(revised in pass 2 from L2.5)* (E1 Q13–Q14, E2 Q11, Q13, Q16,
E3 Q14, E4 Q13, E5 Q13; M1 Q13–Q14; M5 Q13)

**Trend:** API/Security section E1–E5: 2 → 1 → 1.5 → 2.5/3 → 1.5 (the E2 dip is the
password-storage miss, a security item). At the medium tier, M1 Q13 was explicitly
the best answer of the paper.

**Commentary.** This is the second banked strength. Status-code semantics are exact
(401 vs 403 vs 404, and the correct observation that 401 means unauthenticated
despite its name — E1 Q13; the full 2xx/4xx/5xx classes at E2 Q11). CRUD-to-verb
mapping including collection-versus-item URIs (E1 Q14), parameter placement across
path/query/body with correct rationale for each (E4 Q13), and `202 Accepted` for
async work (E2 Q16) are all clean. **Idempotency is the anchor**: PUT versus PATCH
versus POST at M1 Q13 earned full marks a full tier above his measured level,
including the PATCH-array-append nuance that distinguishes a memorized answer from
an understood one. The one blemish at easy tier is E3 Q14, where he named GET and
DELETE as idempotent and omitted PUT — the canonical case — which is a recall slip
against an otherwise correct model. Unbanked: pagination in any form (M1 Q14, blank;
keyset at M5 Q9, blank) and rate limiting (M5 Q13, blank).

**Calibration note.** Under-rated. He treats these as easy questions rather than as
the strength they are; the idempotency answer is interview-grade as written.

**Reconciliation (pass 2): score lowered L2.5 → L2.** gaps.md §12's status is
"MEASURED (basics), UNMEASURED (design specifics) … every question above the
definition line came back blank," and its unmeasured list is the substance of the
guide: idempotency keys end to end, versioning strategy, RFC 7807 error contracts,
`ETag`/`If-None-Match`, deprecation sequencing, webhook delivery, token-bucket rate
limiting. L2.5 projected a strong basics half across a topic whose design half has
never been asked. The strength claim itself is unchanged and gaps.md independently
confirms it — M1 Q13 is listed there as "the best answer on that paper," and
gaps.md judges the E3 Q14 PUT omission "arguably closed by the M1 result."

**Measurement confidence: HIGH** for the basics — eleven probes, including a
medium-tier full mark — and NONE for the design half. **Upcoming measurement:
ad-hoc paper 3** (Section 1, API contracts and evolution).

**Gaps: see gaps.md §12 — API design.**

## 13 — Web security

**Score: L1.5** (E2 Q14 → E4 Q14b retest, E3 Q13, E4 Q14, E5 Q13–Q14;
M2 Q12–Q13; M5 Q14)

**Trend:** **password storage 0 (E2 Q14) → 1 (E4 Q14b retest)** — the second
completed repair in the ledger, and the only one on a misconception rather than a
blank.

**Commentary.** Authentication versus authorization is clean, with the correct 401/403
mapping (E3 Q13), and bearer tokens are understood — header transport, issued after
authentication, stolen if not over HTTPS (E5 Q13). The password-storage repair is
worth stating precisely because of what it demonstrates: at E2 he proposed
public/private-key encryption and Diffie-Hellman, a confident wrong mechanism that
reads worse in an interview than a blank; at E4 Q14b, from a different angle, he
identified the key-compromise flaw, described hash-and-compare verification, and
named irreversibility as the distinguishing property. Only the vocabulary polish
remains (salted, deliberately slow, bcrypt/argon2). What is still open: **CORS is
inverted** — he believes the server enforces it, when the browser enforces and the
server merely declares policy, which is exactly why his own curl intuition
contradicted his model (E5 Q14); SQL injection is understood as a concept but the
`PreparedStatement` fix was never produced (E4 Q14); JWT validation steps (M2 Q13),
TLS's guarantee set (M2 Q12) and the OAuth2 client-credentials flow (M5 Q14) are
blank.

**Calibration note.** The password episode is the template for how a misconception
here behaves: stated with confidence, wrong at the mechanism, and repaired in a
single sitting once named. CORS is currently sitting in the same slot.

**Correction absorbed from gaps.md §13.** The CORS entry above understated the
position: the model was not merely still open, its **retest has already failed
once**. `fundamentals-primer-2.md` part 3 named M2 Q14 as its own retest, and M2 Q14
scored 0 (blank). gaps.md escalates CORS MEDIUM → HIGH on that repetition and
classifies it as a study-execution failure rather than a knowledge one. It also
rates JWT validation **HIGH** ([CORE], and stateless auth is the default in this
candidate's stack) and prepared statements **HIGH**, with M4 Q14 as the queued
retest. Score unchanged at L1.5 — the password closure and the AuthN/AuthZ and
bearer-token passes hold it up against three HIGH-severity blanks. One structural
gap worth flagging: **IDOR / broken object-level authorization**, which the guide
names as the most common real vulnerability, has never been asked.

**Measurement confidence: HIGH** — eight probes with an explicit retest.

**Gaps: see gaps.md §13 — Web security.**

## 14 — Messaging & queues

**Score: L1** (E1 Q15, E3 Q15, E4 Q15, E5 Q15; M1 Q15; M2 Q15; M5 Q15)

**Trend:** 1 (E1) → 0.5 (E3) → 0.5 (E4) → 0.5 (E5) → 0 (M1) → 0 (M2) → 0 (M5).
Downward, and the three easy-tier halves are all the *same* error.

**Commentary.** The "why a queue" rationale was correct at E1 Q15 — decoupling,
survival across consumer or network trouble, asynchrony — and producer / consumer /
broker are the right words. Underneath that vocabulary sits **one systematic wrong
model, observed on three consecutive papers**: he believes the broker retries
delivery to consumers and then dead-letters, independent of whether consumers are
running. E3 Q15 answered a consumers-down scenario with "retry to consumers"; E4
Q15 defined the DLQ as holding messages that "couldn't be sent"; E5 Q15 answered a
one-hour consumer outage with messages going to the DLQ. The correct model is the
opposite in the load-bearing respect: with no consumers there are no processing
failures, so messages simply accumulate durably in the queue — that buffering is the
entire point — and the DLQ receives only messages that repeatedly *fail processing*
after N delivery attempts. Everything built on top is consequently blank: delivery
semantics as a taxonomy (M1 Q15), idempotent consumers (M2 Q15), and SQS versus
Kafka (M5 Q15). `tmp/primers/fundamentals-primer-2.md` part 2 exists for exactly
this and has not yet been verified by a retest.

**Calibration note.** This is the second over-trusted belief (with volatile). It is
stated plainly and without hedging every time, which is what allowed it to survive
three papers — a hedge would have prompted a check.

**Measurement confidence: HIGH** — seven probes here, eight by gaps.md's count,
three of them the same retest by another name. gaps.md §14 reaches the identical
verdict ("the source of the record's single most persistent wrong model") and adds
that M2 Q15's idempotent-consumer blank is a **failed retest**: both
`fundamentals-primer-2.md` part 2 and `primer-3.md` §4 named that paper. M3 Q15
(poison message) is the remaining fresh instrument for the lifecycle model. Score
unchanged.

**Gaps: see gaps.md §14 — Messaging & queues.**

## 15 — Caching

**Score: L2.5** (E1 Q16, E2 Q15, E3 Q16, E4 Q16, E5 Q16; M1 Q16; M2 Q16; M5 Q16)

**Trend:** strong on every paper at every tier, including full marks at M5 Q16 — a
medium-tier design question taken on an accidental tier jump with no preparation.

**Commentary.** The strongest topic in the ledger and, notably, the only one where
performance did not degrade with tier. The TTL answer at E2 Q15 was above the bar,
volunteering the small-TTL-versus-staleness trade-off unasked. In-process versus
external caching was answered with the right discriminator (speed versus shared
state) plus the per-instance inconsistency problem at four instances (E4 Q16). And
M5 Q16 — a Caffeine/Redis hybrid design — earned full marks a tier above his level:
read-heavy traffic to the in-process layer, updates through central Redis, near-cache
with invalidate-and-refill, and, unprompted, the residual staleness window during
invalidation propagation. That last clause is L4 behaviour: naming what still breaks
after your own design. The two soft spots are vocabulary rather than reasoning:
"cache-aside" as a named pattern drew a blank at M1 Q16 even though his E2 TTL answer
had already described the cache-aside read path correctly, and the Redis data-structure
inventory (hash, sorted set, list, set, per-key TTL) was not produced at E5 Q16. He
also named the thundering herd correctly at M2 Q16 without being able to list the
mitigations (jitter, single-flight, refresh-ahead).

**Calibration note.** Substantially under-rated by the candidate, and this is the
clearest case. He treats caching as an area he happens to guess well in; the record
says it is the one topic where he reasons at design level under pressure. Full
marks on an accidental medium paper is not luck at n=8.

**One qualification absorbed from gaps.md §15.** The cache-aside blank is not purely
a vocabulary gap as stated above: gaps.md splits it, MEDIUM for the missing name and
**HIGH for the write path**, because "delete the key, don't update it" — and the
reader-repopulates-stale race behind it — is the guide's bolded correctness rule and
was not demonstrated anywhere. That is a genuine hole inside the banked strength.
Score unchanged at L2.5; gaps.md independently calls this "the candidate's single
banked strength" and M5 Q16 "the best single answer in the entire record."

**Measurement confidence: HIGH** — eight probes across three tiers.

**Gaps: see gaps.md §15 — Caching.**

## 16 — Testing

**Score: L1** *(revised in pass 2 from L1.5)* (E1 Q17–Q18, E3 Q17, E4 Q17;
M1 Q17–Q18; M2 Q17; M5 Q17)

**Trend:** Testing/Craft section E1–E5: 1.5 → 1.5 → 2 → 1 → 1.5, then **0/2 at M1**.

**Commentary.** He can read a test and state what behaviour it pins, naming
given-when-then unprompted (E3 Q17), and the working notion of a mock — a
behaviour-mimicking stand-in returning conditioned values instead of hitting a real
database — is correct (E1 Q18). Two definitional inversions sit on top of that: at
E1 Q17 the integration test was described as using dependencies "in mocked format,"
which is the opposite of the point (integration tests use real collaborators —
Testcontainers, real HTTP), and at E4 Q18 continuous integration was defined as
continuous deployment. The `assertEquals` argument order was treated as convention
rather than as the reason failure messages read "expected X but was Y" (E4 Q17).
At medium tier the design layer is absent: the mock/stub/fake taxonomy and the
decision rule for what to mock (M1 Q17), clock injection for testable
time-dependent code (M1 Q18), flaky-test causes (M2 Q17), and Mockito's
ArgumentCaptor plus the cost of over-verification (M5 Q17, half credit for the
void-method case). He asked for a guide on test types at M2 Q17, which is an
accurate read of his own gap.

**Reconciliation (pass 2): score lowered L1.5 → L1.** gaps.md §16 rates the
test-double taxonomy **CRITICAL** by the letter of the scoring rules — L0 in a
daily-use area — and the surrounding evidence supports the lower band: four
medium-tier zeros (mock/stub/fake, Clock injection, flaky tests, plus a half on
Mockito specifics) sitting on top of an *inverted* definition of what an integration
test is, which is an L0/L1 signal on that concept rather than an L2 one. The
easy-tier passes are real but they are recall and reading, not design. gaps.md also
flags that choosing a Spring test slice, Testcontainers-over-H2 (M3 Q17 pending) and
the whole contract/mutation-testing layer are unsampled.

**Measurement confidence: HIGH** — eight probes across both tiers. **Upcoming
measurement: ad-hoc paper 3** (Section 3, testing in practice) for the breadth
half; **M4 Q17** is the queued retest for Clock injection and Mockito.

**Gaps: see gaps.md §16 — Testing.**

## 17 — Git craft

**Score: L2** (E2 Q17–Q18, E3 Q18, E5 Q17–Q18; M2 Q18; M5 Q18)

**Trend:** steady on everyday operations; the recovery layer has been probed once
and returned nothing.

**Commentary.** Daily-driver Git is fluent: commit versus push and fetch versus
pull all four correct, including a correctly hedged note that `git pull --rebase`
exists (E2 Q17); branch-and-PR rationale as a review gate keeping main releasable
(E3 Q18); and a good code-review answer with a sane priority order — correctness
first, optimization next, style last (E5 Q18). Merge-conflict handling is half
known: he identifies when conflicts arise and that a choice must be made between
ours, theirs and both, but not the mechanical steps (edit, strip the `<<<<<<<`
markers, `git add`, then `--continue`) — E2 Q18. Commit-message craft favours
verbosity over a concise subject plus an explanatory body carrying the *why*
(E5 Q17). The recovery toolkit is the clean hole: revert versus reset versus
checkout drew a blank (M5 Q18), reflog and bisect have never been probed, and
`--force-with-lease` was unknown at M2 Q18 along with the rule against rebasing
shared history.

**Scope correction from gaps.md §17.** This topic also owns **debugging
methodology** — the observe → reproduce → falsifiable hypothesis → predict → change
one variable → fix the cause → regression test loop, "what changed?" first,
correlation IDs, and reasoning about rare intermittent bugs. None of it has ever
been asked, so the L2 above describes Git alone. gaps.md rates the recovery-tools
gap **HIGH** (`reset --hard` without knowing reflog is how work gets destroyed) with
**M4 Q18** as the queued retest, and separately records that E5 Q18's code-review
answer resolves the "code review skills" concern from `tmp/gaps.md` §3.1 — it is
explicitly not a gap. Score unchanged.

**Measurement confidence: HIGH** — seven probes; the everyday half is well measured
even though the recovery half rests on one question and the debugging half on none.
**Upcoming measurement: ad-hoc paper 3** (Section 2, git craft and debugging).

**Gaps: see gaps.md §17 — Git craft (and debugging methodology).**

## 18 — Cloud & AWS

**Score: L1** *(revised in pass 2 from L1.5)* (E1 Q19, E2 Q19–Q20, E3 Q19–Q20,
E4 Q19–Q20, E5 Q19–Q20; M1 Q19–Q20; M2 Q20)

**Trend:** Cloud/DevOps section E1–E5: 1.5 → 0.5 → 2 → 1.5 → 1.5. The E2 trough is
informative rather than noisy — E1 sampled service names, E2 sampled operational
depth.

**Commentary.** Service-level knowledge is real: EC2, S3 and RDS correctly
distinguished (E1 Q19), regions versus availability zones with the high-availability
rationale (E3 Q19), rollback via versioned artifacts and a pipeline step (E3 Q20),
container logs shipping to CloudWatch with the correct underlying principle that
logs die with the container (E4 Q19), and horizontal versus vertical scaling — where
he volunteered the leader-election problem for scheduled jobs across instances
(E5 Q19), an above-bar observation. The gap is consistently one layer down, at
operations. Load balancers were described only as spreading traffic when the
question explicitly asked what else they do — health checks, connection draining
for zero-downtime deploys, TLS termination (E2 Q20). Environment variables yielded
one reason of the two required, missing the big ones: secrets stay out of source
control, and one artifact runs everywhere (E2 Q19). IAM roles versus access keys
were framed as a granularity difference rather than the actual one, temporary
auto-rotated credentials with no static secret to leak (M1 Q19). Health checks were
defined without naming who consumes them (M1 Q20 got the liveness/readiness actors
half right; E4 Q20 named none).

**Reconciliation (pass 2): score lowered L1.5 → L1.** gaps.md §18 states the
conclusion directly, carrying it forward from `tmp/gaps.md` §9: "**real level ≈ L1,
not L2**" — below the reference line for this topic — on the grounds that every
question reaching operational depth scored ≤ 0.5, with the E1↔E2 swing as the
cleanest illustration in the record. It also raises secrets management to **HIGH**
([CORE] hygiene, compounding with the Dockerfile finding in topic 19), which the
pass-1 commentary folded into a general ops observation rather than naming. The
strengths above are unchanged and remain real; they are name-the-service and
name-the-concept answers, which is what L1 means.

**Measurement confidence: HIGH** — twelve probes, though clustered at the concept
end; gaps.md counts nine under its narrower attribution and marks the topic
PARTIALLY MEASURED. **Upcoming measurement: ad-hoc paper 3** (Section 4, AWS
mechanics).

**Gaps: see gaps.md §18 — Cloud & AWS.**

## 19 — Docker & Kubernetes

**Score: L1** (E1 Q20, E4 Q19; M1 Q20; M2 Q19; M5 Q19)

**Trend:** no retests.

**Commentary.** The template-versus-running-instance distinction between image and
container is correct, but the mental model underneath it is not: an image was
described as "an OS's copy" when the defining property of a container is that it
shares the **host kernel** — that is the entire difference from a VM — and an image
is an immutable stack of filesystem layers (E1 Q20). Liveness and readiness probes
were defined correctly but without their consumers, and the classic failure mode
(liveness wired to a database dependency, so an outage sends the orchestrator into
a restart loop against healthy pods) was not reached (M1 Q20). The Dockerfile review
at M2 Q19 found the hardcoded password — the security defect, which is the one worth
finding — but missed four build-discipline defects and incorrectly claimed the build
target would not exist. Container-versus-JVM memory and OOMKilled are blank (M5 Q19).
No Kubernetes object model question (Pod, Deployment, Service, Ingress, ConfigMap,
Secret) has been asked at any tier.

**Attribution correction (pass 2).** The container-logs answer (E4 Q19 = 1) cited
above belongs to topics 18 and 20, not here; gaps.md §19 records that within this
topic **nothing has ever scored above 0.5** — "the definitional layer is present in
every answer; nothing above it has been demonstrated," which is L1 stated as prose.
Score therefore unchanged, but it now rests on four probes rather than five.
gaps.md rates Dockerfile hygiene **HIGH** (retest M4 Q19, layers and cache
invalidation) and OOMKilled-vs-OutOfMemoryError **HIGH** (exit 137 and a heap OOM
have opposite fixes).

**Measurement confidence: LOW** — four shallow probes, none above 0.5, and the
entire Kubernetes object model untested. **Upcoming measurement: ad-hoc paper 2**
(Section 3 Docker, Section 4 Kubernetes).

**Gaps: see gaps.md §19 — Docker & Kubernetes.**

## 21 — REST architecture & API fundamentals

**Score: L2** (self-assessed via structured walkthrough; verified against Richardson model and HTTP semantics)

**Trend:** none yet.

**Commentary.** REST foundations are solid at the L2 "mechanism" level. The candidate understands the conceptual scaffold correctly: resource-centric URLs, appropriate HTTP methods for CRUD operations, correct status-code categories, idempotency semantics (though not yet the safe/idempotent orthogonality), and HATEOAS as a return-links pattern. Richardson Maturity Model progression is correct (Level 0 single endpoint with single method → Level 3 HATEOAS), just numbered 1–4 rather than 0–3 — notation, not understanding. The shortfalls are in depth rather than breadth. HTTP caching (Cache-Control, ETags, conditional requests) is absent despite being core REST practice — this sits adjacent to topic 15 (caching) and is the highest-severity miss. Safe vs idempotent conflation, content negotiation, the statelessness constraint as architecture rather than accident, and versioning/deprecation strategies are all undemonstrated. The gap inventory is clean: PUT/PATCH precision, media-type selection, and the RFC 7807 error contract are all vocabulary/practice misses rather than model inversions.

**Calibration note.** Self-assessment was honest about known gaps; no over-confident claims. This is a real L2 — can explain the REST model to a junior — but L2.5 pending the caching integration and a versioning strategy demonstration.

**Measurement confidence: HIGH** — structured evaluation against core reference material (Richardson model as taught, HTTP semantics from RFC 9110), no contradictions in any tested concept, and the gaps identified are all in unmeasured territory (no paper has probed REST). Self-assessment is more reliable than quiz data here.

**Gaps: see gaps.md §21 — REST architecture & API fundamentals.**

---

## 20 — Observability & operations

**Score: —**

**Trend:** none.

**Commentary.** Not measured. Two answers touch the area edgewise: container logs
going to CloudWatch, with the correct principle that applications write to
stdout/stderr and the platform ships them (E4 Q19, full marks), and an alert-design
question that came back blank (M5 Q20). That is one adjacent success and one blank
at a tier above the candidate's level — not enough to place a level. The topic's
substance per `src/topics/20-observability-operations.md` — the three pillars,
structured logging, Micrometer and Prometheus, distributed tracing and context
propagation, SLI/SLO and error budgets, alert design, incident response,
postmortems — has never been asked. No score is recorded rather than guessing one;
the qbank 11 ladder is the instrument that would fix this.

**Two probes reassigned here by gaps.md §20, neither changing the verdict.** The
rollback answer (E3 Q20 = 1 — versioned artifacts and tags, plus a rollback step in
the pipeline) and the CI-versus-CD confusion (E4 Q18 = 0.5, CI defined as deployment)
are filed under this topic rather than under cloud and testing where pass 1 placed
them. gaps.md rates **CI vs CD HIGH** — the scoring rules treat deploy-pipeline
literacy zeros as HIGH, and "what does your CI run?" is a standard screen. Even with
four probes the status stays UNMEASURED: they are deploy-adjacent, and the topic's
core — the three pillars, structured logging and MDC, RED/USE, percentiles and the
cardinality trap, tracing, SLI/SLO and error budgets, alert design — remains
entirely unasked. No score is recorded.

**Measurement confidence: NONE.** **Upcoming measurement: ad-hoc paper 2**
(Section 5, observability, deploys and incidents); **M3 Q20** separately covers logs
versus metrics versus traces.

**Gaps: see gaps.md §20 — Observability & operations.**

---

## Cross-cutting observations

These are not topics, but they change how every score above should be read.
gaps.md's counterpart section is **"Cross-topic findings (not owned by any single
guide)"**, which reaches the same four conclusions and adds a fifth worth carrying
here: an inventory of five written remediation artifacts of which **only the
concurrency primer has a verified effect** — `fundamentals-primer-2.md` is partially
verified (ACID) and partially failed (CORS, idempotent consumer), while `primer-3.md`,
`quick-notes.md` and `study-plan.md` are entirely unverified.

**Code write-fluency is a measured gap, not an inference.** Theory across the easy
tier ran ~71%; the code session produced zero fully-correct artifacts out of three
(`tmp/valuations/code-session-valuation.md`). Three distinct failure modes, all
worth separating: describing an algorithm in English instead of implementing it
(E2 Q2), submitting code that does not compile — the method never returns its map —
together with an unanswered complexity clause (E4 Q2), and failing to recognize an
aggregation problem when the words implied rather than named it (E5 Q10). The last
is the important one, because he had explained WHERE versus HAVING correctly two
papers earlier. Prompted recall is in place; unprompted problem-shape recognition
is not. This is why topics 01 and 09 are scored below their theory evidence.

**The asked-instance habit costs roughly two marks per paper** — about ten
occurrences across the easy tier alone. The pattern is stable: the concept is
correct and the specific clause the question asked goes unanswered (`SELECT *` for
"names and salaries"; "what else does a load balancer do" answered with what it
does; "which join keeps the orphan row" answered with the general distinction).
This inflates the apparent size of several gaps in this ledger — some scores of 0.5
reflect an unfinished answer rather than absent knowledge.

**Calibration runs backwards in a specific, exploitable way.** Self-flagged answers
tend to score full marks (generics at E5 Q4, scaling at E5 Q19, the thundering herd
name at M2 Q16); confidently-stated answers are where the two live misconceptions
sit (volatile atomicity, the SQS-to-DLQ path). Caching and idempotency are
under-rated strengths. The practical reading: hedging predicts correctness here, so
the interview advice is to hedge less on knowledge questions and verify more on
compound mechanism claims.

**Two repairs have completed and are the template.** Concurrency basics ran
0.5 → 0.5 → primer → 1.5 → 2.0 with two independent retests, and password storage
ran 0 → 1 on a differently-angled retest. Both followed the same loop: name the
misconception precisely, write a targeted chapter, retest from a different angle.
Neither was fixed by taking another paper. The items currently sitting where those
two sat — broker lifecycle, Isolation versus Consistency, CORS enforcement, the
Spring proxy model — have chapters written and retests identified but no verified
retest yet.

**The medium tier is measuring study execution, not knowledge.** M5 (3.5/19),
M1 (6.5/19) and M2 (3.0/19) were all taken without the prescribed between-tier
study, and M2's valuation showed four of its zeros landing on topics whose chapters
were already written and named as that paper's retests. Every medium-tier score in
this ledger should be read as a floor. gaps.md rates this **CRITICAL as a process
finding** and draws the consequence for the plan rewrite: enforce study-before-measure
gates rather than merely providing material.

**What the three unrun ad-hoc papers will settle.** They sit at the easy→medium
boundary, deliberately below M3/M4 so they measure breadth without spending the two
remaining fresh medium instruments. Between them they carry every `—` and LOW row in
the at-a-glance table: paper 1 for modern Java, JVM internals and diagnostics, DSA
pattern recognition and collections internals; paper 2 for OS/Linux, Docker and
Kubernetes, and observability; paper 3 for API design specifics, git craft and
debugging, testing breadth and AWS breadth. Until they are taken, five topics in
this ledger (04, 06, 11, 19, 20) rest on four probes or fewer, and two of them
carry no score at all.