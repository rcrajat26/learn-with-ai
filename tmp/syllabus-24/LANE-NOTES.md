# Lane notes — orchestrator record, not part of the syllabus

### Notes for the orchestrator — lane A

**Leaf counts per section, with the arithmetic.**

Conceptual frame: §1.1 = 13, §1.2 = 13, §1.3 = 14, §1.4 = 15, §1.5 = 14 → 13+13+14+15+14 = **69**.

Creational: §1.6 = 14, §1.7 = 12, §1.8 = 12, §1.9 = 16, §1.10 = 18, §1.11 = 15, §1.12 = 15 →
14+12+12+16+18+15+15 = **102**.

Structural: §1.13 = 12, §1.14 = 11, §1.15 = 15, §1.16 = 13, §1.17 = 12, §1.18 = 11, §1.19 = 15 →
12+11+15+13+12+11+15 = **89**.

**Lane total: 69 + 102 + 89 = 260 leaves** across 19 sections (target 250, +4.0%, inside ±15%).
Front matter is not leaf-counted. No section is under 8 or over 25. Every `*(N leaves)*` marker was
counted on disk with `grep -c` per section range, not estimated.

**Tag counts for the lane**, counted on disk over the §1.1–§1.19 body only (front matter and these
trailing blocks excluded; a leaf may carry more than one tag):
`[API]` 42, `[TRAP]` 32, `[X-REF nn]` 32, `[DECIDE]` 25, `[SOURCE]` 24, `[PROVE]` 23, `[NUM]` 21,
`[VERSION-TRAP]` 14, `[SAY]` 13, `[TABLE]` 11, `[BUILD]` 9, `[INCIDENT]` 5, `[RESEARCH]` 4,
`[SMELL]` 4, `[FLOW]` 1, `[DIAG]` 0.

The 32 `[X-REF nn]` markers break down as: 16 → 13, 25 → 4, 06 → 4, 05 → 4, 07 → 3, and one each
to 22, 10, 08, 03. Guide 16 dominating is a consequence of the brief's "testability consequence"
obligation on every pattern section — one marker per pattern.

`[DIAG]` is unused in lane A by design — a decompiled proxy class, an ArchUnit failure report and a
generated SQL line all belong to PART 3 and PART 4. If the orchestrator wants `[DIAG]` represented in
PART 1, the natural host is §1.15 (a decompiled `$Proxy0`), but it duplicates §3.7 and I left it
there.

**Things I could not verify, named, with the constant and the source that would settle it.**

1. **`Long.valueOf` / `Short.valueOf` have no tunable cache bound** (§1.19.10). I confirmed from
   JDK-6968657 that the `Integer` cache's **low** bound is deliberately not configurable and that
   `AutoBoxCacheMax` applies to `Integer`, but I did not fetch `Long.java` / `Short.java` to prove
   no equivalent property exists. Tagged `[RESEARCH]`. Settled by reading `LongCache` and
   `ShortCache` in the JDK 21 `java.lang` sources.
2. **JEP 491's exact shipping release and residual pinning cases** (§1.12.10). Search results
   consistently say JDK 24 and "native code / foreign functions still pin", and I read the JEP
   summary, but I did not fetch openjdk.org/jeps/491 in full. Tagged `[RESEARCH]`. Settled by the
   JEP text itself plus the JDK 24 release notes.
3. **Scalar-replacement defeaters as an exhaustive list** (§1.12.8). Shipilev's quark names
   control-flow merges, non-inlined instance calls and identity-dependent code, and explicitly does
   *not* discuss `-XX:+DoEscapeAnalysis`, `-XX:+EliminateAllocations` or
   `EliminateAllocationArraySizeLimit`. I therefore did **not** state any flag or numeric limit.
   Tagged `[RESEARCH]`. Settled by `c2_globals.hpp` in the HotSpot sources if the write pass wants
   the flag names and defaults.
4. **The class-initialisation-lock citation.** The current guide (line 158) cites **JLS 12.4.2**; my
   §1.10.4 cites **JVMS §5.5**. Both describe the same mechanism from different specs (JLS 12.4.2 is
   the language-level detailed initialisation procedure; JVMS 5.5 is the JVM-level one with the
   init lock). This is not a contradiction, but the write pass and §3.3 must pick one primary
   citation and use it consistently across §1.10, §1.3.3 and §3.3, or the reader will think one is
   wrong. My recommendation: cite **JVMS §5.5** for the lock and **JLS §12.4.2** for the
   "initialised on first active use" rule.
5. **`spring.aop.proxy-target-class` in Spring Boot 3.5.x specifically.** The
   `matchIfMissing = true` condition is documented on the Boot 2.1 Javadoc page I found and is
   widely reported as unchanged through 3.x, but I did not read the 3.5.x source of
   `AopAutoConfiguration`. §1.15.13 is tagged `[VERSION-TRAP]` `[API]` `[SOURCE]` and the write pass
   must quote the 3.5.x class. Settled by
   `spring-boot-autoconfigure/src/main/java/org/springframework/boot/autoconfigure/aop/AopAutoConfiguration.java`
   at the 3.5.x tag.

**One correction the orchestrator should route to whoever owns the write pass.** Lines 293–312 of
`src/topics/24-design-patterns-architecture.md` imply that a JDK dynamic proxy is what Spring
reaches for and that CGLIB is the fallback. That is true of plain Spring Framework and **false of
Spring Boot**, where CGLIB is the default. §1.15.13 exists to fix it, and the guide's current
wording is the exact stale claim delta 8 targets.

**Judged out of scope, and where I sent it.** The JMM barrier semantics behind `volatile` (§1.10.6–7)
→ `[X-REF 05]` with the mechanism stated in one paragraph. Inline-cache degradation and the measured
cost of a virtual call (§1.5.11, §1.15.14) → `[X-REF 06]` for mechanism and §3.1 / §3.21 for the
numbers, with `[X-REF 25]` for the JMH harness. Collector live-set accounting (§1.12.9) →
`[X-REF 06]`. Connection-pool sizing arithmetic (§1.12.13) → `[X-REF 10]`. `Integer` cache as a
language-substrate fact (§1.19.6) → `[X-REF 03]`, kept here as the flyweight instance. Cluster-wide
singleton / leader election (§1.10.17) → `[X-REF 22]`. Every one of these still has a leaf here, per
the brief's rule that a bible does not send the reader away empty-handed.

**Cross-references I emitted into sections I do not own**, so the orchestrator can check they exist:
§1.20 (strategy), §1.21 (template method), §1.26 (visitor/expression problem), §1.27 (iterator),
§1.29 (non-GoF vocabulary), §1.30 (SOLID), §1.32 (DI/IoC), §1.33 (the census table), §2.3
(structural disambiguation), §2.5 (confusable pairs), §2.8 (LSP), §2.10 (DIP), §2.11 (other
principles / fragile base class), §2.14 (anti-patterns), §2.15 (smells), §2.16 (refactorings), §2.17
(architecture styles), §2.25 (integration patterns / ACL), §2.26 (resilience), §2.28 (testability),
§2.29 (enforcement/ArchUnit), §3.1 (dispatch), §3.2 (escape analysis), §3.3 (class init), §3.4
(volatile/DCL), §3.5 (enum singleton/`readResolve`), §3.6 (`Cloneable` source walk), §3.7 (JDK proxy
internals), §3.8 (CGLIB/self-invocation), §3.13 (sealed types), §3.14 (immutability at JIT level),
§3.21 (measuring design decisions), §4.3 (`ServiceLoader` plugin registry).

---

### Notes for the orchestrator — lane B

**Leaf counts per section, and the arithmetic.**

| Section | Leaves |
|---|---|
| §1.20 Strategy | 18 |
| §1.21 Template method | 14 |
| §1.22 State | 15 |
| §1.23 Observer | 20 |
| §1.24 Command | 13 |
| §1.25 Chain of responsibility | 15 |
| §1.26 Visitor and double dispatch | 17 |
| §1.27 Iterator | 13 |
| §1.28 Mediator, memento, interpreter | 16 |
| §1.29 The non-GoF vocabulary | 23 |
| §1.30 SOLID at vocabulary level | 11 |
| §1.31 Layered architecture | 13 |
| §1.32 DI and IoC | 18 |
| §1.33 The pattern census | 10 |
| **PART 1 subtotal (§1.20–§1.33)** | **216** |
| §2.1 Master pattern-selection table | 16 |
| §2.2 Creational decision procedure | 14 |
| §2.3 Structural intent disambiguation | 16 |
| §2.4 Behavioural disambiguation | 18 |
| §2.5 The confusable pairs | 18 |
| **PART 2 subtotal (§2.1–§2.5)** | **82** |
| **Lane B total** | **298** |

Arithmetic: 18+14+15+20+13+15+17+13+16+23+11+13+18+10 = **216** for Part 1 (brief target ≈190,
so +13.7%, inside the ±15% band). 16+14+16+18+18 = **82** for Part 2 (brief target ≈80, +2.5%).
216 + 82 = **298** against a lane target of ≈270, i.e. **+10.4%** — inside ±15%. Counts were
verified on disk by counting lines matching `^[0-9]+\.[0-9]+\.[0-9]+ ` per section, not estimated.

Three sections exceed the brief's soft 25-leaf ceiling? No — the largest is §1.29 at 23. Three
sections sit at 10–11 (§1.33, §1.30), below the "almost certainly under-enumerated" threshold of
8 but close to it; both are deliberate. §1.33 is 10 leaves **plus a 23-row table**, so its real
content is ~33 named mappings; §1.30 is intentionally thin because §2.6–§2.10 (lane C) own SOLID
in depth and duplicating it here would create exactly the redundancy the brief warns about.

**Tag counts for the lane** (occurrences of each tag across all 298 leaves; a leaf may carry
several):

| Tag | Count |
|---|---|
| `[PROVE]` | 78 |
| `[API]` | 54 |
| `[SAY]` | 53 |
| `[DECIDE]` | 52 |
| `[TRAP]` | 46 |
| `[RESEARCH]` | 32 |
| `[NUM]` | 25 |
| `[BUILD]` | 24 |
| `[X-REF nn]` | 22 |
| `[SMELL]` | 16 |
| `[TABLE]` | 14 |
| `[VERSION-TRAP]` | 12 |
| `[FLOW]` | 9 |
| `[SOURCE]` | 6 |
| `[INCIDENT]` | 4 |
| `[DIAG]` | 0 |
| **Total tag occurrences** | **447** |

Counted on disk over the leaf region only (everything above `### Sources consulted`), so the tag
names appearing in this notes block are excluded. `[VERSION-TRAP]` is counted separately from
`[TRAP]` — the two are disjoint. Average 1.5 tags per leaf.

All 22 `[X-REF nn]` tags are genuine **sibling-guide** pointers (16×6, 06×5, 05×4, 08×2, 04×2,
20×1, 14×1, 07×1); there are **no intra-guide `[X-REF 24]` tags**, per the cross-lane convention
that an intra-guide pointer is a bare inline `(§N.M)`. Every leaf in the lane carries at least one
tag.

History: §2.5.16 was retagged `[X-REF 24]` → `[TABLE]` during the cross-lane `[X-REF]` sweep — its
text already named §1.3 inline so no parenthetical was needed, and `[TABLE]` is what the leaf
actually obliges (five parallel category/example pairs is a ≥3-item comparison).

`[DIAG]` is zero for this lane by design: it demands a real artefact (a decompiled proxy, an
ArchUnit failure report, a stack trace) and every such artefact in this topic belongs to
PART 3 (§3.7, §3.8, §3.13, §3.19, §3.20) or PART 4. A basics-tier leaf that promised a decompiled
class would duplicate lane E. `[INCIDENT]` is low (4) for the same reason — §3.22 owns the
postmortems; the four here are the ones whose *design* lesson is inseparable from the failure
(§1.23.6 latency coupling, §1.23.7 rollback coupling, §1.25.12 filter ordering,
§1.29.23 document-buffer OOM).

**Anything I could not verify, named, with the constant and the source that would settle it.**

1. **`ApplicationFilterChain.internalDoFilter` does not exist in current Tomcat.** Multiple
   secondary sources (and stack traces in the wild) reference
   `ApplicationFilterChain.internalDoFilter(ApplicationFilterChain.java:269)`, but the current
   `main` source I fetched has only `doFilter`. It appears the private method was inlined at some
   point. §1.25.4 therefore names only `doFilter`, `addFilter` and `release`. **What would settle
   it:** the Tomcat 9.0.x source tag, where `internalDoFilter` was present, versus 10.1.x/11.x.
   If the write pass wants to name it, it must state the Tomcat version.
2. **`INCREMENT = 10`** is confirmed as `public static final int` in the fetched source, but its
   *semantics* (the array-growth step in `addFilter`) I did not read the body of. Tagged `[API]`,
   not `[NUM]`, for that reason.
3. **The Evans/Fowler specification operation names** — `remainderUnsatisfiedBy`, `asQuery`,
   `subsumes`, and whether the paper says "building to order" or "generation" — come from
   secondary sources because `martinfowler.com/apsupp/spec.pdf` returned unparseable binary.
   §1.29.7 carries `[RESEARCH]`. **What would settle it:** the PDF itself, read as text.
4. **`IntegerCache` bounds in §1.33's flyweight row** are stated as −128..127, which is the
   documented default, but the **upper** bound is settable via
   `-XX:AutoBoxCacheMax=<high>` / `java.lang.Integer.IntegerCache.high`. Lane A owns §1.19
   (flyweight) and lane E owns §3.x; I have not duplicated the property name there. Flagging it so
   whichever lane owns the constant states the tunability rather than the bare 127.
5. **Whether `Observable`/`Observer` were removed** (not merely deprecated) in any current JDK.
   §1.23.20 and §1.33's row 19 say "deprecated since Java 9", which I am confident of; I did not
   verify against a JDK 25 API diff whether they are now marked for removal.
   **What would settle it:** the `java.util.Observable` javadoc for the JDK 25 API.
6. **Spring's flyweight cell is marked "absent"** — a judgement, not a verified fact. Spring's
   `ConcurrentReferenceHashMap`-backed annotation metadata caches are *caching*, not an
   intrinsic/extrinsic state split, which is why I called it absent. If the orchestrator prefers a
   populated cell, `org.springframework.core.annotation.AnnotationUtils`' caches are the closest
   candidate and the row should say "caching, not flyweight" rather than a bare type name.
7. **The 11-receiver-type megamorphic claim in §1.20.13.** The JIT's megamorphic threshold is a
   HotSpot implementation detail (the virtual-call inline cache degrades past **2** receiver
   types, and `-XX:TypeProfileWidth` defaults to 2), so "past bimorphic" is right and "11 types"
   is the count of §9.3's catalog rows, not a JIT constant. §3.1 (lane E) owns the constant; I
   have deliberately not stated a threshold number here.

**Anything I judged out of this topic's scope, and where I sent it.**

- Observer's `ApplicationEventMulticaster` internals, the `TransactionSynchronization` registration
  path, the listener-leak heap analysis, and the `ConcurrentModificationException` site → **§3.19**,
  cross-referenced from §1.23.4, §1.23.13 and §1.23.14. Lane B states the mechanism in one leaf and
  points.
- Inline-cache degradation, `TypeProfileWidth`, and the measured cost of a strategy interface →
  **§3.1** (lane E), cross-referenced from §1.20.13. See note 7 above.
- Iterator allocation being scalar-replaced → **§3.2**, cross-referenced from §1.27.13.
- `PermittedSubclasses`, the `typeSwitch` bootstrap and `MatchException` → **§3.13**,
  cross-referenced from §1.26.10.
- The `final`-method/CGLIB interaction and the self-invocation bypass → **§3.8** (guide `07`),
  cross-referenced from §1.21.5.
- Outbox mechanics, saga transport and delivery semantics → **§2.25**/**§3.17** and guide `14`,
  cross-referenced from §1.23.13 and §1.23.16.
- Snapshotting, upcasting and version-based optimistic concurrency → **§3.16**/**§3.18** and guide
  `08`, cross-referenced from §1.28.10.
- Aggregate boundary rules → **§2.22** (lane D), cross-referenced from §1.22.11.
- Package-by-layer vs by-feature in depth, and layered-vs-hexagonal-vs-clean as a fitness
  comparison → **§2.17**/**§2.19** (lane D), cross-referenced from §1.31.9 and §1.31.13. §1.31
  deliberately stops at "layered is the default, here is the symptom it stopped being one".
- SOLID in depth, GRASP, connascence, and the anti-pattern catalogue → **§2.6–§2.14** (lane C),
  cross-referenced from §1.30. §1.30 is vocabulary only, by the brief's own split.
- Test doubles per pattern → **§2.28** (lane D) and guide `16`, cross-referenced from §1.20.17,
  §1.21.13, §1.22.15, §1.26.17, §1.31.12 and §1.32.11.
- ArchUnit rules, JPMS enforcement and fitness functions → **§2.29**/**§3.20**, cross-referenced
  from §1.29.20.

**One format note the orchestrator should know:** §1.33 and §2.1–§2.5 each carry a large table
*inside* a leaf (§1.33.2, §2.1.3, §2.3.2, §2.4.2, §2.5.2). The table is the leaf's content, per
the `[TABLE]` tag, and is **not** counted as additional leaves. If the totals table wants a
"named mappings" figure separate from the leaf count, those five tables contribute 23 + 27 + 4 +
5 + 29 = **88** table rows on top of the 298 leaves.

---

### Notes for the orchestrator — lane C

**Leaf count per section and the arithmetic.** §2.6 = 20; §2.7 = 20; §2.8 = 22; §2.9 = 20;
§2.10 = 20; §2.11 = 32; §2.12 = 15; §2.13 = 32; §2.14 = 77.
`20 + 20 = 40`; `+22 = 62`; `+20 = 82`; `+20 = 102`; `+32 = 134`; `+15 = 149`; `+32 = 181`;
`+77 = 258`. **Lane total = 258 leaves** against a 240 target (+7.5%, inside the ±15% band).
Counts were verified on disk by counting lines matching `^2\.<n>\.` per section, not estimated.

§2.14 carries 77 rather than the brief's ~65 because the orchestrator restored the process and
organisational anti-patterns as §2.14.67–2.14.77, all `[X-REF 26]`. §2.14 is therefore three
sub-blocks: intra-service (2.14.1–2.14.61), distributed at the boundary (2.14.62–2.14.66,
`[X-REF 22]`), organisational (2.14.67–2.14.77, `[X-REF 26]`). The write pass should keep that
grouping visible, because the third sub-block is pointed-at material and must not be developed at
the same depth as the first.

**Tag counts for the lane** (occurrences of each tag across all 247 leaves; a leaf may carry only
one tag, and every leaf carries exactly one):

| Tag | Count |
|---|---|
| `[PROVE]` | 40 |
| `[SOURCE]` | 37 |
| `[X-REF nn]` | 32 |
| `[BUILD]` | 32 |
| `[SMELL]` | 31 |
| `[TRAP]` | 20 |
| `[DECIDE]` | 18 |
| `[API]` | 15 |
| `[SAY]` | 10 |
| `[INCIDENT]` | 8 |
| `[NUM]` | 7 |
| `[TABLE]` | 4 |
| `[VERSION-TRAP]` | 2 |
| `[RESEARCH]` | 1 |
| `[FLOW]` | 1 |
| `[DIAG]` | 0 |
| **Total** | **258** |

The total equals the leaf total exactly, which is the check that every leaf carries one and only one
terminating tag. `[DIAG]` is deliberately unused in this lane, per the orchestrator: lane E owns the
ArchUnit failure report at §3.20 and lane F owns the manifest, so §2.10.17 needs no promotion.

The `[X-REF nn]` breakdown by target guide, all sibling-guide pointers, no intra-guide pointers
remaining: 26 ×11, 22 ×5, 03 ×2, 04 ×2, 05 ×2, 08 ×2, 16 ×2, 06 ×1, 07 ×1, 14 ×1, 17 ×1, 20 ×1,
25 ×1 — **32 occurrences, all 32 terminating.** The one former in-line `[X-REF nn]` (§2.6.13, where
the tag was used mid-sentence as a noun) is gone with this sweep.

**History trace, so the retagging is recoverable.** Five leaves lost their only tag to the
self-referential `[X-REF 24]` sweep and were retagged on approval, each by what the leaf obliges the
write pass to do: §2.7.14 → `[BUILD]` (a refactoring move plus a startup assertion to write);
§2.10.9 → `[PROVE]` and §2.10.12 → `[PROVE]` (port/adapter as DIP is an argument to work through);
§2.10.17 → `[API]` (the leaf is a literal ArchUnit rule expression); §2.11.14 → `[SOURCE]`
(Meyer 1988 and Young c. 2010 are both quotable). No other leaf's tag was touched by the sweep.

The intra-guide pointers those tags became: §2.6.13 → §2.15 (already inline, tag deleted);
§2.7.14 → §2.16; §2.10.9 → §2.17 (already inline, tag deleted); §2.10.12 → §2.25; §2.10.17 → §2.29;
§2.11.14 → §2.23 (already inline, tag deleted). Three were already named inline and three were not,
against the orchestrator's estimate of four and three.

**What I could not verify, named with the constant and the source that would settle it:**

1. **Martin's `D` normalisation.** Sources agree on `D = |A + I − 1|` (range 0..1) and separately
   report a non-normalised `D = |A + I − 1| / √2`. I could not open Martin's own 1996 *C++ Report*
   paper — `https://staff.cs.utu.fi/~jounsmed/doos_06/material/DesignPrinciplesAndPatterns.pdf`
   failed with a TLS error ("unable to verify the first certificate"). §2.13.12 states both forms
   and marks the normalised one as what tools report. **Settled by:** *Agile Software Development:
   Principles, Patterns, and Practices* (2002), ch. 20, "Distance from the Main Sequence".
2. **`A = Na/Nc` denominator.** Secondary sources split between `Nc` = *total* classes (correct,
   keeps `A` in 0..1) and `Nc` = *concrete* classes (makes `A` unbounded). I have asserted "total"
   and made the misstatement itself a trap in §2.13.11. **Settled by:** the same chapter.
3. **Postel's law's RFC number.** Wikipedia's robustness-principle article attributes it to the
   early TCP/IP specifications; the search summary said "the 1979 IPv4 specification". RFC 760 (IP)
   and RFC 761 (TCP) are both January 1980, and RFC 1122 §1.2.2 restates it. §2.11.32 cites
   "RFC 760/761, 1980" and carries `[RESEARCH]`. **Settled by:** reading RFC 761 §2.10 directly.
4. **"Entity service" as a named anti-pattern.** No fetched source used that exact name; the
   concept (a service per table rather than per capability) is well attested under other names.
   §2.14.63 is written with the mechanism, but the *name*'s attribution is unconfirmed. **Settled
   by:** Richards, *Microservices AntiPatterns and Pitfalls* (O'Reilly, 2016), which the brief's
   version baseline implies is the intended source.
5. **`LCOM4` (§2.6.18)** — I have named it as the cohesion proxy metric; I did not verify which
   tools still compute it (SonarQube removed LCOM4 from its default profile at some point).
   Flagged so the write pass does not promise a Sonar rule that no longer exists.

**Judged out of this topic's scope, and where I sent it:**

- **Resolved by the orchestrator, no longer out of scope.** I had dropped the process and
  organisational anti-patterns on the grounds that no sibling owned process; guide 26
  (`26-behavioral-leadership.md`) does. They are restored as §2.14.67–2.14.77 with one-line
  mechanisms and `[X-REF 26]`: design by committee, Brooks' law / mythical man-month, analysis
  paralysis, NIH syndrome, escalation of commitment, silver bullet, ambiguous viewpoint,
  programming by permutation, organisational silos/stovepipe, moral hazard, cash cow. Two of these
  now have technical siblings inside the lane and are cross-referenced to them rather than
  duplicating: NIH → §2.14.30–2.14.31, escalation of commitment → §2.11.25 and §2.14.60.
- Still dropped from the same completeness probe, as project-management folklore with no design
  mechanism to state: *the corncob*, *blowhard jamboree*, *viewgraph engineering*, *death by
  planning*, *fear of success*, *fire drill*, *the feud*, *smoke and mirrors*, *throw it over the
  wall*, *irrational management*, *intellectual violence*, *e-mail is dangerous*, *tester-driven
  development*. If guide 26 wants any of them it should source them itself; they would be
  name-only leaves here.
- *Stovepipe **system*** (the technical one, point-to-point integration with N² bespoke contracts)
  is §2.14.54; *stovepipe **organisation*** (Conway's law producing that architecture) is
  §2.14.75. Deliberately two leaves, because the mechanism differs.
- *DLL hell* — not a JVM concern; the JVM analogue (*JAR hell*) is folded into §2.14.53.
- *Race hazard* and *busy spin* belong mechanically to guide 05. Busy spin is kept as §2.14.51 with
  `[X-REF 05]` because it is a design-level choice; *race hazard* is dropped as pure 05 territory.
- The **fitness-function / ArchUnit enforcement** treatment that §2.10.17 and §2.13.15 point at is
  lane D's §2.29. I state the rule text in one leaf each and do not develop it.
- **Fowler's smell catalogue** overlaps §2.14 at four points (feature envy, shotgun surgery, middle
  man, primitive obsession). I kept the four leaves because the brief's inventory assigns them to
  §2.14, and wrote them as *failure mechanisms*; lane D's §2.15 should treat the same four as
  *smells with a smallest-safe-move*, which is a different cut of the same concept. **Flagging the
  overlap so the orchestrator does not de-duplicate them into one.**

---

### Notes for the orchestrator — lane D

**Leaf counts per section, and the arithmetic.**

| Section | Leaves |
|---|---|
| §2.15 code smells | 30 |
| §2.16 refactoring catalogue | 25 |
| §2.17 architecture styles | 30 |
| §2.18 fitness table | 12 |
| §2.19 package structure | 12 |
| §2.20 DDD strategic | 25 |
| §2.21 DDD tactical | 25 |
| §2.22 aggregate design | 20 |
| §2.23 CQRS | 18 |
| §2.24 event sourcing | 20 |
| §2.25 integration & decomposition | 30 |
| §2.26 resilience | 22 |
| §2.27 concurrency patterns | 22 |
| §2.28 testability | 15 |
| §2.29 enforcement | 15 |
| §2.30 cost model | 15 |

30+25+30+12+12+25 = 134; 25+20+18+20+30 = 113 (running 247); 22+22+15+15+15 = 89 → **lane D total 336 leaves**
across 16 sections. Against the ≈300 target that is +12%, inside the ±15% band. Every count above was
taken from the numbered leaf lines on disk (`grep -c '^2\.NN\.'`), not estimated.

**Tag counts for the lane** (tag *occurrences* inside §2.15–§2.30 only, excluding these three trailing
blocks; a leaf may carry several tags, so the total exceeds the leaf count). Counted on disk, not
estimated. **452 tag occurrences across 336 leaves — 1.35 tags per leaf.**

| Tag | Count |
|---|---|
| `[X-REF nn]` — all sibling-guide, none intra-guide | 71 |
| `[TRAP]` | 48 |
| `[PROVE]` | 47 |
| `[DECIDE]` | 44 |
| `[API]` | 42 |
| `[RESEARCH]` | 37 |
| `[TABLE]` | 30 |
| `[NUM]` | 29 |
| `[SAY]` | 27 |
| `[SOURCE]` | 25 |
| `[SMELL]` | 24 |
| `[VERSION-TRAP]` | 10 |
| `[FLOW]` | 7 |
| `[DIAG]` | 4 |
| `[BUILD]` | 4 |
| `[INCIDENT]` | 3 |

`[X-REF nn]` targets by frequency: 05 (13), 14 (11), 08 (9), 12 (8), 22 (6), 06 (5), 16 (4), 20 (4),
07 (3), 25 (3), and one each to 13, 15, 17, 18, 19. Fifteen of the twenty-five sibling guides are
pointed at, which matches this lane's position as the architecture/DDD/resilience block.

**Intra-guide pointers are now bare `§N.M`, per the orchestrator's ruling.** All 43 were converted: 39
became a parenthetical `(§N.M)` sitting immediately before the leaf's tag run, and 4 were deleted outright
because the leaf text already carried the bare reference inline (§2.20.21, §2.21.5, §2.21.17, and the
folded continuation line in §2.15.24). `grep -c 'X-REF 24'` over the leaf sections now returns 0, so a
`grep` for `[X-REF` returns exactly the 71 real sibling-guide hand-offs — which was the point of the
ruling.

One note on tag usage: `[SMELL]` appears exactly 24 times, once per Fowler 2e smell, and all 24 sit in
§2.15 — a deliberate invariant the write pass can check with one `grep`.

**What I could not verify, named, with the constant and the source that would settle it.**

1. **The §2.18 fitness table's star ratings.** Richards & Ford publish a 1–5 star scorecard per style in
   *Fundamentals of Software Architecture* (O'Reilly; ch. 9–15 of the 1st ed.), but no source I could reach
   transcribes the full grid. `bagerbach.com`'s reading notes give the ratings **qualitatively** for every
   style (and numerically for service-based: testability/deployability/fault tolerance/availability/agility
   at 4 of 5, scalability 3, elasticity 2), which is what §2.18.2–9 encodes. Every one of those leaves
   carries `[RESEARCH]`. **What would settle it:** the per-style scorecard figures in the book itself
   (1st ed. ISBN 978-1-492-04345-4; 2nd ed. 978-1-098-17551-1) or the scorecard images on
   DeveloperToArchitect.com. The write pass must transcribe from the book, not from my leaves, and must
   confirm whether the 2nd edition changed any rating — I could not check that either.
2. **`[VERSION-TRAP]` on §2.27.20 (structured concurrency).** `StructuredTaskScope` was a preview API in
   Java 21 (JEP 453) and its signature changed in later JDKs — the `ShutdownOnFailure`/`ShutdownOnSuccess`
   subclasses were replaced by a `Joiner`-based API. I could not confirm the exact JDK release and final
   shape within this lane's research budget. **What would settle it:** the JEP history for structured
   concurrency (453 → 480 → 499 → 505) and the `java.util.concurrent.StructuredTaskScope` javadoc for the
   guide's stated JDK 22–25 delta range. The leaf is written to state the Java 21 shape and flag the
   delta; the write pass must fill in which release changed what.
3. **§2.26.12 Resilience4j — resolved by ownership, not by research.** Per the orchestrator, **§3.15 is
   the single authority** for the `CircuitBreakerConfig` property names, their spellings and their
   documented defaults; §2.26.12 no longer lists them. It now names the *shape* of the configuration
   surface (window type and size, minimum call count, failure-rate threshold, slow-call rate and duration,
   open-state wait, half-open probe count) plus the five states I assert (`CLOSED`, `OPEN`, `HALF_OPEN`,
   `DISABLED`, `FORCED_OPEN`), keeps its `[RESEARCH]` tag, and points at §3.15. It also carries the
   warning lane F raised — a default quoted in a tuning example (e.g. `minimumNumberOfCalls = 20`) is a
   chosen value, not the library's documented default. **What would settle the underlying facts:** the
   Resilience4j 2.x `CircuitBreakerConfig` javadoc and the `resilience4j.circuitbreaker.instances.*`
   Spring Boot property reference — for §3.15 to fetch, not this lane.
4. **§2.24.7 snapshot cadence.** "Every 100–500 events" is a widely repeated practitioner figure, sourced
   here from a DZone guide rather than a primary source; there is no canonical constant. The leaf states it
   as a *commonly cited range* and §2.24.8 derives the QuizStakes number from the scenario's own arithmetic
   instead, which is the defensible version. **What would settle it:** nothing — it is a tuning parameter,
   and the write pass should present it as such rather than as a constant.
5. **§2.20.23 distillation patterns.** The seven names are from Evans *DDD* (2003) part IV. I could not
   fetch a primary table of contents to confirm the exact set and spellings (particularly whether
   *Cohesive Mechanisms* and *Abstract Core* are both in the distillation group). Leaf carries
   `[RESEARCH]`. **What would settle it:** Evans, *Domain-Driven Design*, part IV chapter 15 contents.
6. **§2.15.29 non-Fowler smell attributions.** *Bumpy Road*, *Deep Nesting*, *Paragraph of Code* and
   *Variable with Long Scope* appear on sammancoaching.org, which states its entries are original prose
   with names "many of" which come from Fowler 2e — so which of those four are CodeScene/Tornhill coinages
   versus site-original is unconfirmed. The leaf presents them as "named by other catalogues", which is
   true regardless of which catalogue. **What would settle it:** Tornhill's *Software Design X-Rays* /
   CodeScene documentation for Bumpy Road and Deep Nesting.

**What I judged out of this topic's scope, and where I sent it.**

- Broker/partition/consumer-group/delivery-semantics mechanics behind the outbox and saga → `[X-REF 14]`,
  stated once in §2.25.30 as an explicit hand-off so §2.25 does not re-teach transport.
- CAP/PACELC, quorum `R+W>N`, consistent hashing and cross-service capacity arithmetic → `[X-REF 22]`.
  §2.17.2 and §2.25.30 point there; §2.30.11 keeps only the availability *multiplication* because it is a
  cost-model argument for decomposition, not a distributed-systems mechanism.
- JMH harness mechanics for §2.30.5's "measure the megamorphic site" claim → `[X-REF 25]`. This lane
  states *what to measure and why*, never how to build the harness.
- Inline-cache degradation, escape analysis and scalar replacement mechanics → `[X-REF 06]` and lane E's
  §3.1–3.2. §2.30.3–4 state the cost and cite; they do not explain the JIT.
- `@Version` SQL generation, dirty checking and the persistence-context lifecycle → `[X-REF 08]`.
  §2.22.11–12 own it *as aggregate design* and show the statement; the mechanism is guide 08's.
- Test-slice and Testcontainers mechanics behind §2.28.12's fake-vs-integration boundary → `[X-REF 16]`.
- Sidecar deployment mechanics (pod topology, resource overhead) → `[X-REF 19]`; §2.25.25–26 keep only the
  pattern distinction.
- Commit hygiene and `git bisect` mechanics behind §2.16.21 → `[X-REF 17]`.

**Two coordination notes.**

- §2.15's smell→move→test triples and §2.16's catalogue-move names must not be re-enumerated by lane C's
  §2.14 (anti-pattern catalogue). The boundary I assumed: lane C owns *anti-patterns* (god object, anemic
  model, distributed monolith — design-level failures with a failure mechanism), lane D owns *smells*
  (Fowler's code-level hints) and *moves*. §2.15.30 states the distinction explicitly so the merged
  document does not appear to contradict itself.
- §2.19 (package structure) and §2.29 (enforcement) both touched JPMS and the build module, and the
  overlap with lane E's §3.20 is now resolved per the orchestrator: **§3.20 owns all the machinery** —
  `exports`, `requires transitive`, `opens`, `--add-exports`, `jdeps`, and how ArchUnit's `ClassFileImporter`
  and `freeze()` actually work. Three leaves were rewritten in place, so no counts moved: §2.19.8 now
  states only what JPMS changes about *layout* (the boundary becomes a declared file rather than an implied
  package tree) and points at §3.20; §2.29.13 keeps only the one property a rule *author* needs — rules see
  bytecode, so reflection/bean-name/SpEL wiring is invisible, therefore write rules against types — and
  sends the importer mechanics to §3.20; §2.29.14 became the **enforcement ladder** decision leaf
  (convention → package-private → ArchUnit → build module → JPMS), with the `[DECIDE]` rule that you climb
  only as far as the rule's blast radius justifies and that a domain build module is the right rung for
  almost every service. §2.29.7–11 keep the ArchUnit rule *shapes* by API name, which the brief assigns
  here. `[API]` was dropped from those three leaves and `[DECIDE]` added, which is the whole of the tag
  delta: `[API]` 46 → 42, `[DECIDE]` 40 → 44.

---

### Notes for the orchestrator — lane E

**Leaf count per section, with the arithmetic.**

| § | Title (short) | Leaves |
|---|---|---|
| 3.1 | JVM dispatch | 18 |
| 3.2 | Escape analysis | 14 |
| 3.3 | Class initialisation | 14 |
| 3.4 | `volatile`, publication, final freeze | 16 |
| 3.5 | Enum singleton | 12 |
| 3.6 | `Cloneable`/`clone` | 12 |
| 3.7 | JDK dynamic proxy | 16 |
| 3.8 | Subclass proxying | 23 |
| 3.9 | Spring's patterns | 20 |
| 3.10 | The JDK's patterns | 20 |
| 3.11 | Filter chains | 14 |
| 3.12 | Records | 14 |
| 3.13 | Sealed types + exhaustive switch | 16 |
| 3.14 | Immutability at JIT level | 10 |
| 3.15 | Resilience4j internals | 19 |
| 3.16 | Event-sourcing internals | 16 |
| 3.17 | Outbox internals | 16 |
| 3.18 | Optimistic locking | 12 |
| 3.19 | Observer internals | 16 |
| 3.20 | Enforcement mechanics | 14 |
| 3.21 | Measuring design decisions | 12 |
| 3.22 | Failure case studies | 14 |

Arithmetic: `18+14+14+16 = 62`; `+12+12+16+23 = 125`; `+20+20+14+14 = 193`;
`+16+10+19+16 = 254`; `+16+12+16+14 = 312`; `+12+14 = 338`.

**Lane total: 338 leaves** across 22 sections. Every count above was taken by counting
`N.M.K`-prefixed lines on disk, not estimated, and leaf numbering was re-validated as sequential with
no gaps or reuse after the correction round below. Every intra-lane `§3.N.M` pointer was also
re-resolved against the leaf set programmatically — there are no dangling references.

The total moved from 330 to 338 during the correction round: §3.2 gained 2 leaves
(`EliminateAllocationArraySizeLimit`, and the `develop`-only print flags), §3.8 gained 1 (the
`@ConditionalOnBooleanProperty` version delta), §3.11 gained 2 (the `internalDoFilter` boundary and
the `lastServicedRequest` `ThreadLocal`), and §3.15 gained 3 (the `StateTransition` enum, the
unconfirmed-properties leaf, and the per-instance-window arithmetic). 338 is above the brief's
±15% band on 290 (ceiling 333) by 5 leaves; it is 8 above the sum of my own per-section targets.

**RESOLVED BY THE ORCHESTRATOR — CUT NOTHING. 338 IS FINAL. DO NOT ACT ON THE PARAGRAPH BELOW.**
It is retained only as a record of what was considered and declined. The ruling: judge a section
against its own obligation mix, not a global target — all eight leaves above the original 330 came
from fixing real defects found during source verification, so the band was wrong about this lane
rather than the lane being over. §3.20.14 is also to stay whole, on the brief's own rule that a leaf
restating its neighbour is worse than no leaf.

*Declined, for the record:* the four cheapest cuts would have been §3.11.6 (the
`lastServicedRequest` `ThreadLocal`, genuinely peripheral), §3.15.4 (the `StateTransition` count),
§3.8.9 (the annotation version delta, foldable into §3.8.8) and §3.15.14 (the per-instance
arithmetic, foldable into §3.22.6, which already states it) — landing on 334, or 333 with §3.2.5.
None was taken.

**Tag counts for the lane** (occurrences, not distinct leaves — a leaf may carry several):

| Tag | Count |
|---|---|
| `[SOURCE]` | 135 |
| `[API]` | 103 |
| `[PROVE]` | 79 |
| `[TRAP]` | 71 |
| `[NUM]` | 61 |
| `[DECIDE]` | 34 |
| `[X-REF nn]` | 32 |
| `[INCIDENT]` | 20 |
| `[DIAG]` | 20 |
| `[VERSION-TRAP]` | 20 |
| `[RESEARCH]` | 13 |
| `[TABLE]` | 11 |
| `[BUILD]` | 9 |
| `[SAY]` | 8 |
| `[FLOW]` | 7 |
| `[SMELL]` | 3 |

Counted with `grep -o` over the section body only (cut at `### Sources consulted`), so the trailing
blocks' own mentions of tag names are excluded. These are tag **occurrences**, 626 across 338 leaves
(~1.9 per leaf); no leaf is untagged. `[SOURCE]` is the dominant tag as the brief required, and
`[SOURCE]`+`[API]` together appear on the substantial majority of leaves — this is the source-walk
part and the leaves name the class, method, field or constant rather than the behaviour.

No tag outside the brief's legend appears anywhere in the file (verified by inverting a grep of the
legend over every bracketed all-caps token). `[X-REF]` targets used: 04, 05, 06, 07, 08, 10, 12, 13,
14, 15, 22, 25 — no cross-reference into a section this lane does not own without naming the sibling
guide.

**Everything I could not confirm, named, with the source that would settle it.** All eleven are in
the file tagged `[RESEARCH]`; none is an invented identifier, and where I could not confirm a field
name I described the mechanism instead of guessing one.

1. **§3.1.4 / §3.1.14 — the dispatch ns/op figures.** Shipilev's 2015 post and the 2014
   insightfullogic/DZone measurements are on JDK 8-era HotSpot. The *relative ordering* (monomorphic <
   bimorphic ≪ megamorphic) is confirmed and structural; the absolute numbers are not a JDK 21
   baseline. **Settled by:** re-running the `JavaFest`/`MethodDispatch` JMH benchmark on JDK 21, or
   `test/micro/org/openjdk/bench/vm/compiler/` in the JDK source tree. Do not quote the numbers as
   current without that.
2. **§3.2.9 — escape-analysis failure at a control-flow merge.** I could not find a current primary
   source stating that C2's allocation elimination gives up on a phi of two distinct allocations. The
   mechanism is well attested in folklore and consistent with `-XX:+PrintEliminateAllocations` output,
   but it is unconfirmed as a JDK 21 statement. **Settled by:**
   `src/hotspot/share/opto/macro.cpp` (`PhaseMacroExpand::eliminate_allocate_node` /
   `can_eliminate_allocation`) in the JDK 21 source.
3. **§3.4.5 — the x86-64 `volatile` store encoding.** `lock addl $0,(%rsp)` is what HotSpot has
   historically emitted for a StoreLoad fence, but I did not verify it against a JDK 21 disassembly.
   **Settled by:** `-XX:+UnlockDiagnosticVMOptions -XX:+PrintAssembly` on a `volatile` store, or
   `src/hotspot/cpu/x86/assembler_x86.cpp` (`Assembler::membar`).
4. **§3.5.3 — `Enum`'s sealed serialization hooks.** That `Enum.clone()` throws
   `CloneNotSupportedException` is javadoc-confirmed. That `Enum` declares `private final`
   `readObject`/`writeObject`/`readResolve`/`writeReplace` throwing `InvalidObjectException` I could
   not confirm method-by-method; the *effect* (enum singletons are serialization-safe) is confirmed by
   the `writeEnum`/`readEnum` path. **Settled by:** `java.base/java/lang/Enum.java` in the JDK 21
   source.
5. **§3.5.11 — the `ConstructorAccessor` bypass under JPMS.** That the bypass exists is sourced
   (notes.highlysuspect.agency). The specific `--add-opens
   java.base/java.lang.reflect=ALL-UNNAMED` incantation required on JDK 17+ is my inference from the
   JDK 16/17 strong-encapsulation change, not a cited fact. **Settled by:** attempting it on JDK 21
   and reading the `InaccessibleObjectException` message.
6. **§3.7.3 — the proxy cache field name.** The javadoc confirms per-loader caching behaviourally
   ("the existing proxy class will be returned"). The identifier `Proxy.proxyClassCache` and its type
   `WeakCache<ClassLoader, Class<?>[], Class<?>>` are from memory of the JDK source and are
   **unconfirmed**. **Settled by:** `java.base/java/lang/reflect/Proxy.java`. If it cannot be
   confirmed, the write pass should state the behaviour and drop the field name.
7. **§3.7.7 — the `m0`–`m3` convention.** `m0`=`hashCode`, `m1`=`equals`, `m2`=`toString`, interface
   methods from `m3`. This is `ProxyGenerator`'s emission order and is **not specified**; I could not
   confirm it for JDK 21's rewritten `ProxyGenerator` (which was reimplemented on the ASM-based
   `ClassWriter` path). The leaf already says "do not build on it". **Settled by:**
   `java.base/java/lang/reflect/ProxyGenerator.java`, or `-Djdk.proxy.ProxyGenerator.saveGeneratedFiles=true`
   plus `javap -p -c` on the dumped `$Proxy0.class` — which is the artefact the `[DIAG]` leaf should
   show anyway, and the write pass should generate it rather than trust me.
8. **§3.8.3 — Byte Buddy's role in Spring.** I am confident Spring Framework uses its own repackaged
   CGLIB (`org.springframework.cglib`) and **not** Byte Buddy, and that Byte Buddy is Mockito's and
   Hibernate's engine. I could not fetch a primary Spring source saying so in as many words.
   **Settled by:** `grep -r bytebuddy` over the `spring-framework` 6.2 `build.gradle` files, or the
   presence of `spring-core/src/main/java/org/springframework/cglib/`.
9. ~~**§3.11.5 — `ApplicationFilterChain.ALLOCATE = 8`.**~~ **RESOLVED, and I had it wrong.** The
   constant is `public static final int INCREMENT = 10`, confirmed identically at all four Tomcat refs
   fetched (`main`, `11.0.x`, `10.1.x`, `9.0.x`). Growth is linear (`n + INCREMENT`), not the doubling
   I claimed. Both the name and the value in my first draft were reconstructed from a half-memory and
   both were wrong; §3.11.5 now quotes the real declaration. This is precisely the failure mode the
   lane brief warned about, and on this one it was mine rather than the brief's.

10. **§3.11.12 — `ALREADY_FILTERED_SUFFIX`'s value. Still unconfirmed.** The javadoc names the constant
    and says the attribute is `getFilterName() + ALREADY_FILTERED_SUFFIX` but **does not state the
    value**; I have written `".FILTERED"` and the leaf keeps `[RESEARCH]`. **Settled by:**
    `spring-web/src/main/java/org/springframework/web/filter/OncePerRequestFilter.java`. This is now
    the only identifier *value* left unverified in the lane.

11. **§3.15 — the Resilience4j config surface. RESOLVED from source; this lane now owns it.** All
    eleven `DEFAULT_*` constants are quoted from `CircuitBreakerConfig.java` on `master` in §3.15.12's
    table, so the numbers lanes D and F could not confirm are settled in one place. Three
    reconciliations:
    - **Lane F was right.** `DEFAULT_MINIMUM_NUMBER_OF_CALLS = 100` is confirmed, so lane F's §4.6
      `minimumNumberOfCalls = 20` is genuinely a tuning away from the default and its note saying so
      needs no change.
    - **Lane F's `RingBitSet` doubt is resolved.** `RingBitSet` appears nowhere in current
      `CircuitBreaker.java` or `CircuitBreakerMetrics.java`; `FixedSizeSlidingWindowMetrics` backs the
      count-based window in 2.x. §3.15.9 states the boundary and no longer carries `[RESEARCH]`.
    - **Lane D's five-state set is wrong.** The `State` enum has **six** constants — `DISABLED(3,
      false)`, `METRICS_ONLY(5, true)`, `CLOSED(0, true)`, `OPEN(1, true)`, `FORCED_OPEN(4, false)`,
      `HALF_OPEN(2, true)` — quoted verbatim in §3.15.3. `METRICS_ONLY` is the one usually missed.
      Lane D's §2.26 should point at §3.15.3 rather than restate a count.

    **One property remains unconfirmed:** `automaticTransitionFromOpenToHalfOpenEnabled` is **not**
    among the `DEFAULT_*` constants, so its default is a field initialiser I did not read. §3.15.13 now
    says "believed `false`", and I softened §3.15.17 and §3.22.7, which had asserted "(the default)"
    flatly. **Settled by:** the field declarations in the body of `CircuitBreakerConfig.java`, not the
    constants block. Newly confirmed and worth propagating:
    `DEFAULT_WAIT_DURATION_IN_HALF_OPEN_STATE = 0` means "no time limit on the half-open probe window",
    which is the real mechanism behind §3.15.17.

12. **§3.1.8 — `TypeProfileWidth`'s declaring file.** The value (2) and range (0–8) come from the
    OpenJDK HotSpot wiki's TypeProfile page and I am confident in them. But the flag is declared in
    neither `runtime/globals.hpp` nor `opto/c2_globals.hpp` as fetched — both returned "not present",
    which may be truncation of a large file rather than real absence. The leaf now says the declaring
    file is unconfirmed rather than implying one. **Settled by:**
    `grep -rn TypeProfileWidth src/hotspot/` in the JDK 21 tree.

13. **§3.2.9 — escape-analysis failure at a control-flow merge.** Unchanged and still `[RESEARCH]`; the
    OpenJDK EscapeAnalysis wiki discusses no phis. **Settled by:** `src/hotspot/share/opto/macro.cpp`.

**Two flag corrections worth propagating to any lane that mentions escape analysis.** First,
`PrintEscapeAnalysis` and `PrintEliminateAllocations` are declared `develop`, **not** `product` — they
do not exist on a release JDK, so telling a reader to run `-XX:+PrintEliminateAllocations` sends them
into an "Unrecognized VM option" launch failure. §3.2.6 is now a `[TRAP]` about exactly that, with the
product-build alternatives named. Second, `EliminateAllocationArraySizeLimit` is
`product(intx, …, 64, …)` — a hard 64-element ceiling on scalar-replacing an array. On lane A's
caution: `-XX:+DoEscapeAnalysis` **is** confirmed
(`product(bool, DoEscapeAnalysis, true, "Perform escape analysis")`), so I kept it and added the
verbatim declarations for `EliminateAllocations` and `EliminateLocks` beside it. Lane A's underlying
point was right — Shipilev's quark is not a source for flag names — but `c2_globals.hpp` is, and §3.2
now cites that instead. I have still published no defeater list beyond the four failure conditions,
each of which is either mechanism-derived or tagged.

**Citation convention adopted as instructed.** §3.3 quotes the twelve-step procedure and the
initialisation lock from **JVMS §5.5** — it is JVMS's step list, and JVMS's own note that "the
initialization lock is the `Class` object for C" — while §3.3.1 attributes the *first active use*
triggers to **JLS §12.4.2**. §3.4 cites **JLS §17.4.4** for the `volatile` synchronizes-with edge and
**JLS §17.5** for final-field freeze, both correctly JLS since those are language-level rules. No leaf
in this lane cites JLS §12.4.2 for the lock or JVMS §5.5 for the triggers.

**Intra-guide reference convention.** This lane already used bare `§N.M` throughout and `[X-REF nn]`
only for sibling guides — verified by grep, zero occurrences of `[X-REF 24`. No conversion needed.

**Two fetches returned incomplete content and were worked around.**

- The OpenJDK **exhaustiveness guide** returned only the sealed-type half and did not cover the
  enum/`IncompatibleClassChangeError` history. Rather than infer, I fetched **JDK-8294285**, which
  carries the JEP 433 release note verbatim and settles §3.13.12: the change is **JDK 20** (fourth
  preview), final in **JDK 21**. The brief was right that this is easy to get backwards — the trap is
  that `IncompatibleClassChangeError` *still* exists for sealing violations (§3.13.5), so a source
  mentioning ICCE and sealed types in the same paragraph reads like a contradiction. §3.13.13 exists
  specifically to hold that distinction.
- The **`TransactionalEventListener` javadoc** fetch returned only three `TransactionPhase` constants,
  omitting `BEFORE_COMMIT`. That is a summarisation loss, not a Spring change — `BEFORE_COMMIT` is a
  `TransactionPhase` constant in Spring 6.2. §3.19.10 states all four. Flagging it because a write pass
  re-fetching the same URL may get the same truncated answer and "correct" the syllabus wrongly.

**Judged out of scope, and where I sent it.**

- **Kafka partition assignment, consumer-group rebalancing and broker-side ordering** — §3.17.12 needs
  the *statement* that keying by `aggregate_id` gives per-aggregate order, and stops there.
  `[X-REF 14]`.
- **G1 region sizing, humongous-allocation thresholds and the write-barrier implementation** — §3.2.14
  and §3.14.8 state the consequence for pooling and immutability in one clause each. `[X-REF 06]`.
- **JMH harness mechanics as a subject** (fork/warmup semantics, `@Threads`, profilers as JMH plugins)
  — §3.21 uses JMH to answer one question and does not teach it. `[X-REF 25]`.
- **`SecurityFilterChain` contents** (which filters, in what order, and what each does) — §3.11.9–3.11.9
  own the *chain mechanism*; the security semantics are `[X-REF 13]`.
- **Transaction propagation semantics** (`REQUIRED` vs `REQUIRES_NEW` vs `NESTED`, savepoints) —
  §3.19.14 and §3.18.10 name `REQUIRES_NEW` as the mechanism they need. `[X-REF 08]`.
- **CAP/PACELC and cross-service consistency** — §3.16.16 states that projection lag is permanent and
  points on. `[X-REF 22]`.

**One tag judgement to record.** §3.20.14 carries `[DIAG]` and contains both the ArchUnit failure
report *and* the `jdeps`/Maven/Gradle enforcement material, because splitting them would have made a
15th leaf that restated its neighbour — the brief's "a leaf that restates its neighbour is worse than
no leaf". If the orchestrator would rather have 15 leaves with a clean one-artefact-per-leaf shape,
split at "Plus the tooling around it" and renumber; the section count becomes 15 and the lane total
331.

---

### Notes for the orchestrator — lane F

**Leaf counts and the arithmetic.** Counted on disk with
`grep -cE '^[0-9]+\.[0-9]+\.[0-9]+ '` per section, not estimated.

PART 4: §4.1 = 10, §4.2 = 9, §4.3 = 8, §4.4 = 10, §4.5 = 10, §4.6 = 10, §4.7 = 9, §4.8 = 9,
§4.9 = 10, §4.10 = 10, §4.11 = 10, §4.12 = 9, §4.13 = 9, §4.14 = 10, §4.15 = 10.
Sum: 10+9+8+10+10+10+9+9+10+10+10+9+9+10+10 = **143**.

PART 5: §5.1 = 100, §5.2 = 107, §5.3 = 25. Sum: 100+107+25 = **232**.

Lane F leaf total: 143 + 232 = **375**. Plus 32 diagram-manifest rows, which are table entries
and are deliberately not counted as leaves. File length: 1,851 lines.

**Deviation from the brief's sizing, stated explicitly.** The brief asked for ≈110 leaves in
PART 4 and I shipped 143 (+30%), outside the ±15% band. The cause is the "name the parts the
write pass has to ship" instruction colliding with the ≈7-per-section budget: each section
needs, at minimum, an API leaf, a data-structure leaf, a policy/constants leaf, a proof leaf, an
edge-case leaf, a concurrency leaf and the diff table — seven before any section-specific
mechanism. Sections with a real proof obligation (§4.6 windows, §4.10 at-least-once, §4.11 the
win/void asymmetry) needed nine or ten. §5.2 is 107 against ≈90 because the current guide
carries 31 `**Trap:**` markers plus six embedded in the § 8 resilience table, and the brief
required every one restated plus the eight version-stale beliefs; 107 is the count after
merging near-duplicates, not before. **If the orchestrator needs the totals table to match the
brief's ≈110/≈90, tell me which sections to compress and I will cut rather than have you
renumber.** I did not pad: no leaf restates its neighbour.

**Tag counts for the lane** (counted on disk over the leaf sections only, excluding these
trailing blocks): `[TRAP]` 126, `[BUILD]` 92, `[API]` 51, `[PROVE]` 31, `[NUM]` 30,
`[SAY]` 29, `[DECIDE]` 23, `[TABLE]` 17, `[X-REF nn]` 16, `[VERSION-TRAP]` 15, `[DIAG]` 4,
`[INCIDENT]` 3, `[SOURCE]` 3, `[FLOW]` 2, `[RESEARCH]` 1, `[SMELL]` 0. Tags exceed leaf
counts because most leaves carry two or three.

`[SMELL]` is zero in this lane by design — smells belong to §2.15 (lane D). The §5.3 refactoring
katas each carry a smell, a smallest move and a protecting test in the leaf body, but they are
drills rather than catalogue entries, so I left them untagged rather than mis-tag them `[SMELL]`
and duplicate lane D's catalogue.

**Things I could not verify, named with the constant and the source that would settle it.**

1. **Resilience4j 2.x `CircuitBreakerConfig` defaults.** I state
   `failureRateThreshold = 50`, `slidingWindowSize = 100`, `minimumNumberOfCalls = 100`
   (documented) versus the `20` I used in §4.6.2 as a *tuned* value for this domain — the
   documented default is 100 and I chose 20 deliberately for the 40/sec deposit path. The
   `waitDurationInOpenState = 60s` default and `permittedNumberOfCallsInHalfOpenState = 10`
   were not confirmed against a 2.x source. Settled by
   `resilience4j-circuitbreaker/src/main/java/io/github/resilience4j/circuitbreaker/CircuitBreakerConfig.java`
   on the 2.x tag. §4.6.2 is tagged `[NUM]`; the write pass must re-read that file before
   printing any of these numbers as "the default".
2. **`RingBitSet` as the current count-based window implementation.** Secondary sources
   (DeepWiki, Storozhuk's article) name it; the class may have been superseded by
   `FixedSizeSlidingWindowMetrics` in 1.x→2.x. Settled by the
   `io.github.resilience4j.core.metrics` package listing on the 2.x tag. Leaf §4.6.10 names
   both and is tagged `[SOURCE]` so the write pass must quote the real one.
3. **Spring Data JPA `Specification.allOf` / `anyOf` availability.** I attribute them to Spring
   Data 3.x in §4.13.9; not verified against a release note. Settled by the Spring Data JPA
   3.x javadoc for `org.springframework.data.jpa.domain.Specification`. Tagged
   `[VERSION-TRAP]`.
4. **`InvocationHandler.invokeDefault` since Java 16.** Stated in §4.2.4 from memory of
   JDK-8159746 / JEP-adjacent work; not re-verified. Settled by the `java.lang.reflect.InvocationHandler`
   javadoc's `@since` tag.
5. **Debezium `OutboxEventRouter` expected column names.** §4.10.10 names the SMT but I did not
   confirm the current default column set (`aggregatetype`, `aggregateid`, `type`, `payload`).
   Settled by the Debezium outbox-event-router transformation docs for the deployed version.
6. **Devinterview's remaining 70 questions.** The README exposes 15; the rest are behind the
   site. §5.1 is therefore complete against my own coverage frame and against nine other
   sources, but not against that specific list. If completeness against a published bank
   matters, that fetch needs an authenticated or alternative route.

**Out of scope, and where I sent it.** JMH harness mechanics for §4.2.8 and §4.6 cost
measurement → `25` via `[X-REF 25]`. Kafka delivery semantics and consumer-group mechanics
behind §4.10 → `14`. `@Version` SQL generation and `LazyInitializationException` mechanics
behind §4.13.6 and §4.14.8 → `08`. Safe publication and CAS mechanics behind §4.1.8, §4.3.6 and
§4.6.6 → `05`. ClassLoader-per-plugin design behind §4.3.7 → `06`. Testcontainers and test-slice
mechanics behind §4.14.7 → `16`. The behavioural framing of §5.1.98 ("a design decision you got
wrong") → `26`. Cross-service saga transport and distributed-transaction topology → `22`, which
owns everything past the service boundary; §4.10 and §4.16-adjacent leaves stop at the outbox
table and the relay.

**One cross-lane dependency worth flagging.** §5.2 restates traps that lanes A–E own as
paragraphs. I wrote it from `src/topics/24-…` rather than from the other lanes' output, which I
cannot see. If any lane introduces a `[TRAP]` leaf that is not already a `**Trap:**` marker in
the current guide, it will be missing from §5.2 and the orchestrator should hand me the list to
append rather than leaving §5.2 incomplete — §5.2's stated contract is that *every* `[TRAP]` any
lane produces appears there in one line.

**Manifest placement caveat.** D-01 through D-32 reference sections in lanes A–E by number from
the brief's inventory, not from those lanes' written output, so a leaf ref like `§2.13` names the
section rather than a specific leaf. If the orchestrator wants leaf-level refs (`§2.13.7`), that
needs a second pass after the lanes merge.