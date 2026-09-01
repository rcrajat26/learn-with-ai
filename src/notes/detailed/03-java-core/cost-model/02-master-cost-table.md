# 03 Java Core — The master cost table, and what the JIT does to it — INTERMEDIATE (§2.1)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [Arrays](../arrays/01-basics.md) · Next: [What the harness can and cannot measure](02a-measurement-and-amortisation.md)

`../arrays/01-basics.md` finished the tour of the language's data shapes. This file prices the operations you perform on them: one table over the twenty-three core operations, the allocation model underneath the numbers, and the column that matters most — which of those operations the JIT deletes outright before your code ever executes them.

Every nanosecond figure below was measured on **Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64 (Apple silicon)**, with the harness reproduced in full in section 1. **The harness is not JMH**: no forking, no `Blackhole`, no dead-code-elimination guard beyond a `volatile` sink field, and the JIT's compilation state is whatever it happens to be when the timing loop runs. Three full runs were taken and each row quotes the spread across them. Relative comparisons within one run are meaningful; the absolute figures are not portable to your machine, and guide 06 owns JMH, which is the tool for a number you would put in a capacity plan. Nothing in this file is that.

---

## 1. One table over the core operations (2.1.1)

`[NUM]` A cost table is not a price list. Nobody remembers that a monomorphic virtual call measured 1.15 ns and an interface call measured 1.80 ns, and nobody should — the two are indistinguishable on any machine but this one, on any afternoon but this one. What a cost table is, and the only thing worth carrying into an interview or a design review, is a **ranking with orders of magnitude**: five bands, each roughly ten times the one below it, and the ability to say which band an operation sits in and *why it sits there* rather than one band up or down.

The five bands, named once and used for the rest of the file:

| Band | Range on this build | What lives there | What puts an operation here |
|---|---|---|---|
| **0 — eliminable** | below ~0.6 ns, i.e. at or under the harness floor | constant-folded concat (0.0755), cached `hashCode` in a plain loop (0.327–0.383), non-escaping allocation (0.301–0.559), non-escaping box+unbox (0.312) | the operation does not happen at all: `javac` folded it, or C2 removed it |
| **1 — a few nanoseconds** | ~1–5 ns | field read, array access, every kind of call, `instanceof`, cast, boxing, `substring`, `equals`, `BigDecimal.add`, `LocalDate.plusDays`, an escaping allocation, a preallocated stackless throw | a handful of machine instructions, possibly a cache-resident load |
| **2 — tens of nanoseconds** | ~8–65 ns | `String` concat (8.01–9.95 two operands, 15.63–16.88 five), `System.nanoTime` (9.18–9.70), `currentTimeMillis` (13.55–13.70), `Instant.now` (19.79–20.30), `intern` (61.81–65.33) | an allocation that really happens, a native call out of Java, or a VM-internal data structure |
| **3 — hundreds** | ~280 ns | exception construction, `throw`+`catch` | a stack walk: work proportional to something other than the operand |
| **4 — thousands and up** | 13,000–20,000 ns | first cold `Method.invoke` (13,791, single sample), exception construction at depth 1000 (16,483) | one-off code generation, or an unbounded walk |

**Insight:** the bands are not a property of the operation, they are a property of the operation *plus the compiler's view of it*. The same `new LedgerEntry(...)` sits in band 0 or band 1 depending only on whether it escapes its method, and the same `"CLIENT_" + suffix` sits in band 0 or band 2 depending only on whether the suffix is a compile-time constant. That is why the fifth column of the table below carries more information than the fourth.

### Why it exists

Every optimisation argument you will ever have is really an argument about which band something sits in. "Should we cache this?" is "is the thing being cached in band 2 or band 0?" "Is the exception on this path a problem?" is "band 3 at what frequency?" The table exists so that the argument runs on measured bands rather than on folklore — and the folklore is unusually bad here, because most of it was formed on JVMs before escape analysis was on by default, and because the operations people fear (boxing, allocation) turn out to be conditionally free while the ones nobody mentions (`intern`, `Instant.now`) turn out to be several times to twenty times dearer than a field read (`20.30 / 3.02 = 6.7` for `Instant.now`, `63.22 / 3.02 = 20.9` for `intern`, against the 3.02–3.34 ns field-read row).

### When to reach for it, and when not

Reach for the table when you are deciding *shape* — should this be a return value or a throw, should this string be built or interned, should this timestamp be captured per ledger entry or per batch. Do not reach for it to predict a latency: a single PSP authorise at p50 240 ms is **240,000,000 ns**, and a whole band-3 exception construction (278.05–282.39 ns, call it 280) is that divided by:

```
0.240 s / 280 ns = 240,000,000 ns / 280 ns ≈ 857,000
```

— one part in roughly **857,000** of that request. The table matters where the operation runs at thousands per second on CPU you are paying for, which in QuizStakes means exactly three paths: **stake reserve at 1,200/sec peak**, **settlement burst at 3,400/sec**, and **ledger write at 13,600/sec peak**.

### How it works

The harness, so you can judge the numbers rather than trust them. A `LongUnaryOperator` body called in a warmup loop, then a timed loop, `System.nanoTime()` around the loop, total divided by iteration count. Warmup 500,000 iterations, measurement 5,000,000, except where a row's note says otherwise:

```java
static volatile long SINK;
static volatile Object OSINK;

static void bench(String label, int warmup, int iters, LongUnaryOperator body) {
    long acc = 0;
    for (int i = 0; i < warmup; i++) acc += body.applyAsLong(i);
    SINK = acc;
    acc = 0;
    long t0 = System.nanoTime();
    for (int i = 0; i < iters; i++) acc += body.applyAsLong(i);
    long t1 = System.nanoTime();
    SINK = acc;
    System.out.printf("%-38s %10.2f ns/op%n", label, (double) (t1 - t0) / iters);
}
```

driven with QuizStakes fixtures:

```java
static final String POS_A = new String("CLIENT_BONUS_RESERVED");
static final LedgerEntry ENTRY = new LedgerEntry(420L, POS_A);
static final long[] AMOUNTS = new long[1024];   // filled 400..1423

bench("empty loop (lambda call only)",  500_000, 5_000_000, i -> i & 1);
bench("instance field read",            500_000, 5_000_000, i -> ENTRY.amountMinor);
bench("array element read (long[])",    500_000, 5_000_000, i -> AMOUNTS[(int) (i & 1023)]);
bench("virtual call, monomorphic",      500_000, 5_000_000, i -> ENTRY.amountMinor());
bench("intern, already interned",       500_000, 5_000_000,
      i -> "CLIENT_BONUS_RESERVED".intern().length());
```

Two caveats that are not decoration, because they change how three rows must be read:

1. **The lambda indirection is itself a floor.** The empty-loop baseline measured **0.51–0.63 ns/op** across the three runs. Any row within roughly 1 ns of that is *at or under the harness floor*, and its number means "too cheap to separate from the measurement apparatus," not "costs exactly this."
2. **The lambda indirection also prevents hoisting.** The same operation measured in a plain loop can come out roughly 5× cheaper (`1.89 / 0.38 = 5.0`): `String.hashCode` is **1.89 ns** through the lambda and **0.38 ns** in a plain loop, because the plain loop lets C2 hoist the cached-hash read out of the loop entirely. **Both numbers are real; they measure different things.** `02a-measurement-and-amortisation.md` makes that the point rather than an inconsistency.

The 8-byte-alignment arithmetic that the allocation column depends on, worked once here and reused throughout. `LedgerEntry` carries one `long` and one reference. Under compressed oops — on by default, `UseCompressedOops = true` as an ergonomic decision on this build — the header is 12 bytes (8-byte mark word plus 4-byte compressed class pointer), a `long` is 8 bytes, and a reference field is 4 bytes:

```
12-byte header             = 12 bytes
1 long   (amountMinor)     =  8 bytes
1 reference (position)     =  4 bytes
                             --------
total                      = 24 bytes
rounded to 8-byte align    = 24 bytes   (ObjectAlignmentInBytes = 8; already aligned)
```

`../objects-equality-and-lifecycle/05-internals-object-layout.md` owns header arithmetic and field reordering in full; this is the one instance the table needs.

### Diagram

**D-064** is a `table` in the topic's diagram manifest, so a Markdown table is its correct and only rendering — no SVG exists for it and none should be created. One row per operation named in leaf 2.1.1, in the leaf's own order, so coverage can be checked against the leaf directly. Where the measurement produced two variants of one operation, the operation keeps a single row and both figures appear in the ns cell.

| Operation | Complexity | Allocations per call | Measured ns (JDK 21.0.7, this harness) | Can the JIT eliminate it? | QuizStakes hot path where it appears |
|---|---|---|---|---|---|
| `String` concat (`+`) | O(n) in the total operand length | result `String` + its `byte[]`; 2-operand indified concat allocates both | 8.01–9.95 (2 operands) · 15.63–16.88 (5 operands) · **0.0755 when every operand is a compile-time constant** | **Entirely, but only when all operands are constant** — `javac` folds it to one interned literal (JLS 15.29) before C2 sees it. With one non-constant operand, no: the `byte[]` escapes into the result | Settlement burst, 3,400/sec — an audit line per settlement |
| `StringBuilder.append` | O(1) **amortised**, O(n) for the append that reallocates | fresh `new StringBuilder(64)` + one append: the builder + its `byte[]`. Reused builder after `setLength(0)`: **none** | 4.81–4.98 (fresh builder + one append) · 3.87–4.08 (append into a reused builder, no alloc) | Partly — a builder that never escapes can be scalar-replaced, but a builder whose `toString()` result is returned cannot | Settlement burst, 3,400/sec — building the audit line |
| `substring` | O(n) in the **copied** length, not the source length | copying path: one `String` + its `byte[]`. `substring(0,0)`: **none** — returns the shared `""` | 1.41–1.65 (`(0,21)` of a 53-char string) · 1.20–1.68 (`(0,0)`) | Yes here, when non-escaping — both rows are within ~1 ns of the floor because the 21-byte copy was eliminated | Ledger write, 13,600/sec — slicing a `StatusCode` out of a composite key |
| `equals` | O(k) in the compared length; O(1) when lengths differ | none | 2.21–2.41 (equal, 21 chars, distinct instances) · 1.66–1.76 (differing at char 0, different lengths) | No, but it is already band 1; the length pre-check is what makes the unequal case cheaper | Ledger write, 13,600/sec — position-name comparison |
| `hashCode` | O(n) on the first call, O(1) on every later one (cached in the `hash` field) | none | 1.89–1.95 through the lambda · **0.327–0.383 in a plain loop** | Yes — the cached read is loop-invariant and C2 hoists it out entirely, which is the ~5–6× gap between the two figures (`1.89 / 0.383 = 4.9`, `1.95 / 0.327 = 6.0`) | Ledger write, 13,600/sec — position key into a `HashMap` |
| `intern` | O(1) expected — a hash probe of the VM's `StringTable` (`StringTableSize = 65536`) | **none on the already-interned path** — it returns the existing canonical instance | 61.81–64.65 (already-interned literal) · 63.65–65.33 (fresh `new String(...)` each call, 1M iters) | **No — it is a native call into the VM, not Java code C2 can inline.** Measured indistinguishable whether or not the string was already interned | Ledger write, 13,600/sec — the row that pays for itself in section 1's arithmetic |
| Boxing (`Integer.valueOf`) | O(1) | in cache (−128..127): **none**, returns `IntegerCache.cache[i + 128]`. Out of cache **and escaping**: one `Integer` | 1.35–1.62 in cache · 1.33–1.63 out of cache (1000..2023) — **indistinguishable** · 0.312 non-escaping in a plain loop, 2.512 with `-XX:-DoEscapeAnalysis` | **Yes, when non-escaping** — which is why in-cache and out-of-cache measured the same here. The cache is about **identity** (`==`), not about this figure | Stake reserve, 1,200/sec — minor-unit amounts crossing a boxed collection boundary |
| Unboxing (`Integer.intValue`) | O(1) | none | 1.42–1.66 (after an in-cache box) | Yes when the box it pairs with was also eliminated — the box+unbox pair measured 0.312 ns as a unit | Stake reserve, 1,200/sec — same boundary, the other direction |
| `instanceof` | O(1) for an exact or shallow check | none | 1.49–1.63 (true) | **Often, when the receiver type is already known** — C2 frequently removes it after inlining. The 1.5 ns figure sits ~1 ns above the floor and is a class-word load plus a compare, not "a type check costs 1.6 ns in general" | Settlement burst, 3,400/sec — `switch` over a sealed `Verdict` hierarchy |
| Cast (`checkcast`) | O(1) | none | 1.67–1.90 | Often, on the same grounds as `instanceof` — same class-word load, same compare, removed when the type is provable | Settlement burst, 3,400/sec — narrowing a `Verdict` after the pattern match |
| Virtual call | O(1) — a vtable index, not a search | none | 1.15–1.38 (monomorphic) · 1.92–2.49 (bimorphic, two receiver types alternating) | **Yes when monomorphic** — inlined away to a guard plus the body. Bimorphic becomes two type checks plus two inlined bodies; megamorphic falls back to a real vtable dispatch | Ledger write, 13,600/sec — `Movement.amountMinor()` per entry |
| Interface call | O(1) — an itable lookup, not a search | none | 1.75–1.86 (monomorphic) | Yes when monomorphic, on the same inline-cache path as the virtual call; `../inheritance-and-dispatch/03-internals-dispatch.md` owns why the itable's fallback path is dearer than the vtable's | Ledger write, 13,600/sec — `FundsLedger` behind its interface |
| Reflective call (`Method.invoke`) | O(1) once warmed | argument array, plus the JDK's generated accessor once per method | 5.65–7.12 through the lambda · 4.54 warmed in a plain loop · **13,791 on the first cold call (single sample, not an average)** | **No — but the JDK generates and JIT-compiles an accessor after enough invocations**, which is why warmed is only ~4.6× a direct call (`4.54 / 0.99 = 4.6`) rather than the folklore's orders of magnitude. `02a-measurement-and-amortisation.md` prices this against `MethodHandle` | Not on a hot path — paid at startup, by the framework |
| Exception creation | **O(depth)** — `fillInStackTrace()` captures `min(depth, MaxJavaStackTraceDepth = 1024)` frames | the exception, its message `String`, and the internal backtrace | 278.05–282.39 (`new InsufficientFundsException(msg)` at depth ~5, not thrown, 2M iters) | **No — the stack walk is unconditional.** A preallocated stackless instance skips it, but that is a code change, not a compiler one | Stake reserve, 1,200/sec — if `InsufficientFundsException` is used as a shortfall signal, which `../exceptions/02c-cost-and-control-flow.md` argues it should not be |
| Exception throw/catch | O(depth), dominated by the same capture; the unwind itself is a per-method range lookup | none beyond the construction above | 282.48–284.49 (`throw`+`catch` at depth ~5, 2M iters) · **1.34–1.46 for a preallocated stackless instance** | No for the capture; the unwind is already cheap. The gap between the two figures — `282.48 / 1.46 = 193`, `284.49 / 1.34 = 212`, so ~190–210× — is entirely `fillInStackTrace()` | Stake reserve, 1,200/sec — same call site as the row above |
| Array access | O(1) | none | 2.02–2.13 (read, `long[]`, masked index) · 1.72–1.78 (store) | The bounds check often, when the index is provably in range; the load itself no — but it is band 1 already | Ledger write, 13,600/sec — the batched `long[]` of minor-unit amounts |
| Field access | O(1) | none | 3.02–3.34 (instance field read, `entry.amountMinor`) | No — the load is the operation. Reads of a `final` field of a constant receiver fold; this row is neither | Ledger write, 13,600/sec — every field of every `LedgerEntry` |
| `BigDecimal.add` | O(1) when both values are compact (fit a `long`); O(n) in digits once `intVal` is a real `BigInteger` | one `BigDecimal` on the result path; compact values avoid the `BigInteger` | 2.50–2.58 (both scale 2, both compact) | Yes when the result does not escape — the compact path is arithmetic on a `long` field | Settlement burst, 3,400/sec — summing a `StakeSplit` back to the stake |
| `BigDecimal.divide` | O(1) compact, O(n) in digits otherwise; the scale and `RoundingMode` arguments are what keep it terminating | one `BigDecimal`, plus intermediates on the non-compact path | 3.28–3.44 (`divide(THREE, 2, HALF_UP)`) · 4.44–5.17 for `multiply` then `setScale(2, DOWN)` | Same as `add` — eliminable when non-escaping | Settlement burst, 3,400/sec — the 10%-of-stake bonus split |
| `LocalDate.plusDays` | O(1) — epoch-day arithmetic then a re-derivation of y/m/d | one `LocalDate` (immutable, so always a new instance on the escaping path) | 3.26–3.36 (`plusDays(30)`) | Yes when non-escaping — three `int` fields, scalar-replaceable | Not on a hot path — bonus expiry is 30 days from grant, computed once per grant at 8/sec |
| `Instant.now` | O(1) | one `Instant` | 19.79–20.30 (2M iters) | **No — it is a call into the OS clock**, and the `Instant` wrapper around it is the cheaper half | Ledger write, 13,600/sec — one timestamp per entry |
| `System.currentTimeMillis` | O(1) | **none** — returns a primitive `long` | 13.55–13.70 | No — same OS clock call, without the wrapper allocation | Ledger write, 13,600/sec — the cheaper timestamp, at millisecond resolution |
| `System.nanoTime` | O(1) | **none** — returns a primitive `long` | 9.18–9.70 | **No — native VM call into the monotonic clock.** It is also the harness's own instrument, which is why the harness times a loop and divides rather than timing each iteration | Not on a hot path — measurement only, never a ledger timestamp (it is monotonic, not wall-clock) |

**D-064** — The master cost table.

### A concrete example

The `[NUM]` arithmetic the leaf demands, worked explicitly for three rows rather than asserted. All three use the named QuizStakes rates and nothing else.

**`intern` on a `StatusCode` string, once per ledger write.** Ledger write peaks at 13,600/sec, and the measured cost is ~63 ns:

```
13,600 writes/sec × 63 ns = 856,800 ns/sec = 0.857 ms/sec of CPU
```

Under a millisecond of CPU per second — 0.086% of one core. That is the honest size of it. Per call, `intern()` at 61.81–65.33 ns against the two cheapest rows it is usually compared with divides out as:

```
vs cached hashCode (1.89–1.95):   63.22 / 1.95 = 32.4     65.33 / 1.89 = 34.6    -> 32-35x
vs instance field read (3.02–3.34): 63.22 / 3.02 = 20.9     65.33 / 3.34 = 19.6    -> ~20x
```

So roughly **32–35× a cached `hashCode` and ~20× an instance field read** — and at this rate it is still not the thing that will page you. What makes it worth removing is not the 0.86 ms; it is that the call buys nothing, since a `StatusCode` sourced from an enum or a constant is already canonical.

**A 5-operand concat per ledger write.** At the measured 15.63–16.88 ns, taking the midpoint of the range — `(15.63 + 16.88) / 2 = 16.3 ns`:

```
13,600 writes/sec × 16.3 ns = 221,680 ns/sec ≈ 0.22 ms/sec
```

Also small — and the interesting part is how it compares with the 2-operand row (8.01–9.95 ns) for 2.5× the operands:

```
15.63 / 9.95 = 1.6        16.88 / 8.01 = 2.1        -> 1.6-2.1x the cost for 2.5x the operands
```

The cost is **sub-linear in the operand count**: 2.5× the operands buys under 2.1× the time. That is exactly what indified concatenation predicts — `javac` emits an `invokedynamic` to `StringConcatFactory`, whose generated method computes the total length from all operands first and then fills **one** `byte[]` in a single pass, so operand count adds per-operand length arithmetic and copying but not a fresh allocation each. A naive `+`-in-a-loop desugaring (one `StringBuilder` and one intermediate `String` per operand) would be super-linear instead. It still allocates the result `String` and its `byte[]` on every call, which is heap pressure the arithmetic above does not show.

**`InsufficientFundsException` construction on the stake-reserve path.** At 1,200/sec peak and ~280 ns:

```
1,200 reserves/sec × 280 ns = 336,000 ns/sec = 0.336 ms/sec
```

And the counter-example that makes the band model earn its keep — the same exception at a stack depth of 1000, from the depth sweep `02a-measurement-and-amortisation.md` owns in full, costs 16,482.7 ns, so:

```
1,200 reserves/sec × 16,482.7 ns = 19,779,240 ns/sec ≈ 19.8 ms/sec ≈ 2% of one core
```

Same line of code, same rate, band 3 to band 4 purely on call depth — which is the argument for reading the *complexity* column and not just the ns column. Compare the field read on the busiest path of the three: 13,600/sec × 3.2 ns = 43,520 ns/sec, **0.044 ms/sec**, and you have the whole ranking in one comparison.

### The gotcha

**Pitfall:** reading a row within ~1 ns of the floor as a cost. Most of D-064's band-1 figures land between 1.2 and 2.0 ns, against a measured empty-loop baseline of **0.51–0.63 ns**. `substring(0,0)` at 1.20–1.68, `instanceof` at 1.49–1.63, a monomorphic virtual call at 1.15–1.38 and a preallocated stackless throw at 1.34–1.46 are not four operations with four distinct prices — they are four operations that all disappeared into the apparatus. The symptom of getting this wrong is a design argument that turns on a 0.3 ns difference between two rows whose run-to-run spread is larger than the difference: the virtual-call row itself moved 1.15 → 1.38 across three runs of the *same* code, which is more movement than separates it from the `instanceof` row. The fix is to treat everything under about 2 ns as one undifferentiated band 1 and to spend your attention on the boundaries between bands, which are 10× apart and survive any harness.

The five operations actually worth knowing the order of magnitude of, and nothing else from the table:

| Operation | Band | The number to remember |
|---|---|---|
| Field read / array read / a monomorphic call | 1 | "a couple of nanoseconds" — the unit everything else is measured in |
| `String` concat with a non-constant operand | 2 | "under twenty nanoseconds, and it allocates" |
| `Instant.now()` / `currentTimeMillis()` / `nanoTime()` | 2 | "ten to twenty nanoseconds — it leaves the JVM" |
| `intern()` | 2, top end | "61.81–65.33 — 32–35× a cached `hashCode` and ~20× a field read, divisions worked in § 1 and § 3" |
| Exception construction | 3, rising to 4 with depth | "a few hundred at shallow depth, and it climbs per captured frame — the slope is derived in `02a-measurement-and-amortisation.md`" |

> **Definition.** The master cost table is a five-band ranking of the core operations on this build — band 0 for what the compiler removes, band 1 for a few machine instructions, band 2 for a real allocation or a call out of the JVM, band 3 for a stack walk, band 4 for one-off code generation — in which the band an operation occupies is a joint property of the operation and the compiler's view of it, not of the operation alone.

---

## 2. The allocation cost model: TLABs, escape analysis, scalar replacement (2.1.2)

`[X-REF 06]` `[NUM]` "Objects are expensive" is the single most load-bearing piece of folklore in Java performance discussion, and it is conditionally false. The condition is *escape*: an object whose reference provably never leaves the method that created it may never be created, and the measurement below is what that costs — nothing, at the floor. An object that does escape costs a pointer increment and a header write, measured at about 4 ns. Both facts are in the same four-configuration table, which is why that table settles the argument and no amount of reasoning about `new` does.

### Why it exists

The Java allocation path is fast by design, not by accident, because the language gives you no alternative: there is no stack allocation keyword, no arena, no `alloca`. Every object goes on the heap as far as the *language* is concerned, so the runtime has to make the common case of "allocate a small short-lived object" nearly free or the whole idiom collapses. Two mechanisms do that, at two different layers — the TLAB in the allocator, and escape analysis in the compiler — and they are independent: the TLAB makes an allocation that happens cheap, and escape analysis makes some allocations not happen.

### When to reach for it, and when not

Reach for this model whenever someone proposes object pooling, a mutable-accumulator rewrite, or a primitive-array flattening "to avoid allocation" on a path you have not measured. The four-configuration table is the argument that settles whether the allocation was ever there. Do not reach for it to *guarantee* an allocation away: C2's escape-analysis and scalar-replacement heuristics are unspecified and the JVM makes **no documented guarantee** about when either applies, so a design that only works if scalar replacement fires is a design resting on an undocumented decision that a future release may make differently.

### How it works

**TLAB bump-pointer allocation**, the mechanism in one self-contained paragraph. Each thread owns a private slab of Eden — a Thread-Local Allocation Buffer — described by a start pointer, a current bump pointer, and an end pointer. Allocating an object of known size is: check that `bump + size <= end`, write the object's header and fields, advance `bump` by `size`. That is a compare, a few stores and an add, with **no lock and no atomic instruction**, because no other thread can touch this buffer. The slow path runs only when the check fails — the buffer is exhausted — at which point the thread takes a new slab from Eden (which *is* synchronised, but amortised across every allocation the slab serves) or, if Eden is full, triggers a young collection. The flags, all measured on this build via `java -XX:+PrintFlagsFinal -version`:

```
bool   UseTLAB                 = true    {product} {default}
size_t TLABSize                = 0       {product} {default}   (0 = adaptive sizing)
size_t MinTLABSize             = 2048    {product} {default}
uintx  TLABWasteTargetPercent  = 1       {product} {default}
int    ObjectAlignmentInBytes  = 8       {product lp64_product} {default}
bool   DoEscapeAnalysis        = true    {C2 product} {default}
bool   EliminateAllocations    = true    {C2 product} {default}
```

`TLABSize = 0` means the JVM sizes each thread's buffer from that thread's *observed* allocation rate rather than from a fixed constant, with `MinTLABSize = 2048` bytes as the floor and `TLABWasteTargetPercent = 1` bounding how much of a slab it is willing to abandon when a large allocation will not fit the remainder. Guide 06 owns GC, generational heap layout, and what happens after the slab is exhausted; this paragraph is the part you need to price an allocation.

**Escape analysis and scalar replacement.** C2 asks, for each allocation site it has inlined into view, whether the reference can be observed outside the current compilation: stored to a field, returned, passed to a method it did not inline, or published to another thread. If it cannot, the allocation is redundant — the object's fields can live in registers or on the machine stack, and the `new` disappears. That is *scalar replacement*, gated by `EliminateAllocations` and dependent on `DoEscapeAnalysis` having proven non-escape first.

**The measurement that settles "are objects expensive."** `new LedgerEntry(i, POS)` — the 24-byte object whose layout was derived in section 1 — in a tight loop, 20,000,000 iterations (2,000,000 for the escaping row), under four JVM configurations:

```
                                   NON-escaping   ESCAPING   box+unbox (non-escaping)
default (DoEscapeAnalysis=true)        0.559          4.394        0.312
-XX:-DoEscapeAnalysis                  4.008          2.162        2.512
-XX:-EliminateAllocations              0.301          3.746        0.306
-Xint (interpreter only)              42.660         42.155       63.379
```

(The default-configuration non-escaping figure was 0.335 ns in one run and 0.559 in another — both at the harness floor. The range is what is quotable, not either end.)

The settled reading, which is the answer to the question the leaf poses:

- **Turning escape analysis off is what makes the non-escaping allocation cost anything: 0.56 ns → 4.01 ns, a ~7× jump** (`4.008 / 0.559 = 7.2`). With it on, the object is never created and the constructor's two field writes become two register moves. So: **an object that provably does not escape its method frequently costs nothing at all, and one that escapes costs a TLAB bump plus header initialisation — measured at ~4 ns here.** That is the whole cost model, in one measurement, and it is why "objects are expensive" is only sometimes true.
- **The box+unbox row behaves identically** — 0.312 ns with escape analysis on, 2.512 ns with it off. That is the honest way to price boxing: not "16 bytes per `Integer`, unconditionally," but "free when it does not escape, real when it does." It is also why D-064's in-cache and out-of-cache boxing rows measured indistinguishably at 1.3–1.7 ns: the allocation was eliminated in both, so the cache had nothing to save. The in-cache/out-of-cache distinction is about **identity** (`==`) and about escaping allocations. [The cost of boxing](../wrappers-and-boxing/01g-the-cost-of-boxing.md) owns the boxing chapter; do not re-derive it from this row.
- **`-Xint` at 42–63 ns/op is the ceiling with no JIT at all** — `42.66 / 0.559 = 76×` the default non-escaping figure, and `42.66 / 0.301 = 142×` against the low end of that row's range. Worth stating exactly once, because it is the cleanest available measure of how much of every number in this file is the compiler rather than the operation.

**Two anomalies, reported rather than smoothed over.**

**Unverified:** the *escaping* allocation measured **faster** with `-XX:-DoEscapeAnalysis` (2.162 ns) than with it on (4.394 ns) — the opposite of the expected direction, since escape analysis should be neutral for an allocation it cannot eliminate. The plausible reading is a different inlining or loop-unrolling decision taken on a different iteration count (the escaping row ran 2,000,000 iterations against the others' 20,000,000), but this has not been confirmed.

**Unverified:** `-XX:-EliminateAllocations` did **not** restore the non-escaping allocation cost — it measured 0.301 ns, still at the floor, where turning off `DoEscapeAnalysis` moved the same row to 4.008 ns. The plausible reading is that with only a field read after the constructor, the allocation is removed by ordinary dead-code elimination rather than by scalar replacement, so the flag that gates scalar replacement has nothing left to gate. Also unconfirmed.

Both readings are unverified for the same structural reason: **C2's escape-analysis and scalar-replacement heuristics are not specified anywhere, and the JVM makes no documented guarantee about when either applies.** Neither is a rule to invent one from. The settled fact is the direction of the *non-escaping* row, which moved 7× (`4.008 / 0.559 = 7.2`) and is the one the leaf is about; both anomalies are recorded in `## Open questions`.

### Diagram

No diagram for this concept — the manifest assigns D-064 to concept 1 and nothing here. The four-configuration table above *is* the evidence, and a picture of a bump pointer sliding along a buffer would restate its one sentence. Guide 06 carries the TLAB and generational-heap diagrams this concept would otherwise duplicate.

### A concrete example

The two shapes, side by side, on the ledger-write path — identical arithmetic, and only the escape differs:

```java
final class StakeSplitter {

    private static volatile Object OSINK;

    /** Non-escaping: the split never leaves the method. Measured at the floor. */
    static long bonusPortionMinor(long stakeMinor, long bonusAvailableMinor) {
        long tenPercent = stakeMinor / 10;
        StakeSplitMinor split = new StakeSplitMinor(
                Math.min(bonusAvailableMinor, tenPercent),
                stakeMinor - Math.min(bonusAvailableMinor, tenPercent));
        return split.bonusMinor();
    }

    /** Escaping: the same object is published, so it must exist. Measured ~4 ns. */
    static long bonusPortionMinorPublished(long stakeMinor, long bonusAvailableMinor) {
        long tenPercent = stakeMinor / 10;
        StakeSplitMinor split = new StakeSplitMinor(
                Math.min(bonusAvailableMinor, tenPercent),
                stakeMinor - Math.min(bonusAvailableMinor, tenPercent));
        OSINK = split;
        return split.bonusMinor();
    }

    record StakeSplitMinor(long bonusMinor, long cashMinor) {
        StakeSplitMinor {
            if (bonusMinor < 0 || cashMinor < 0) {
                throw new IllegalArgumentException(
                        "split components must be non-negative: " + bonusMinor + "/" + cashMinor);
            }
        }
    }
}
```

On the canonical rounding case — a stake of 3.33, i.e. 333 minor units, against a bonus balance of 500 — `333 / 10 = 33` by integer division, so the split is 33 bonus + 300 cash, which is the domain's mandated 0.33 + 3.00 and reproduces the "bonus portion rounds down" rule as a side effect of the arithmetic. `../numbers-and-money/02-numbers-and-money.md` owns why minor-unit `long` arithmetic and `BigDecimal` are both correct here and which to reach for. (Planned row.)

The record's validation is what makes the second method's object genuinely escape: a compact constructor that can throw keeps the allocation observable, but assignment to `OSINK` is the decisive publication.

### The gotcha

**Pitfall:** designing *for* scalar replacement. The wrong belief is that once you have seen the 0.56 ns figure, you can write allocation-heavy code freely because C2 will remove it. The symptom arrives when the allocation site grows one line — a `log.debug` that captures the object, a metric tag, a new field on a wrapper that pushes the inlining budget over its limit — and the object starts escaping, at which point a loop that was band 0 is band 1 at 4 ns and 24 bytes of Eden per iteration. On the 13,600/sec ledger-write path that is 13,600 × 24 = 326,400 bytes/sec of garbage that was not there in the profile taken last quarter. The fix is not to avoid allocation; it is to know which side of the escape boundary a hot loop's objects are on, and to re-measure after any change to the method that allocates or to the methods it calls, because C2's inlining decisions — and therefore what it can see to prove non-escape — change with both.

> **Definition.** Allocation on HotSpot is a bump-pointer increment inside a lock-free thread-private TLAB, adaptively sized from the thread's observed allocation rate; on top of that, C2's escape analysis and scalar replacement remove the allocation entirely for objects it can prove never leave their method — measured on this build as 0.56 ns non-escaping against 4.01 ns with `-XX:-DoEscapeAnalysis`, and ~4.4 ns for an object that genuinely escapes — with no documented guarantee about when either optimisation applies.

---

## 3. What the JIT can eliminate entirely, and what it cannot (2.1.3)

`[X-REF 06]` The fifth column of D-064 is the whole file compressed into one word per row, and it sorts every operation into three groups that behave differently under load. Some operations *vanish* — the compiled code contains no trace of them. Some are *reduced* — they survive as fewer, cheaper instructions than the bytecode implies. And some are *untouchable* — no compiler can remove them, because they leave the JVM or because their cost is proportional to something outside the operand. Knowing which group an operation is in tells you whether measuring it in a microbenchmark will tell you anything at all.

### Why it exists

The JIT's licence to delete work comes from the same place as its licence to reorder it: the JLS and JVMS specify the *observable* behaviour of a program, not its instruction sequence. If no observation can distinguish "allocated the object then read one field" from "kept the field in a register," the compiler may do the second. That is why the eliminable group is exactly the group whose absence is unobservable, and why the untouchable group is exactly the group whose effect is observable outside the JVM — a clock read, a VM-global table mutation, a stack walk that produces data.

### When to reach for it, and when not

Reach for this classification before writing any microbenchmark, and before believing any number someone else wrote one to produce. An operation in group A measured in a loop measures the compiler; an operation in group C measured in a loop measures the operation. Do not reach for it as a guarantee: group A is "C2 usually can," never "C2 must."

### How it works

**Group A — vanishes entirely.** The compiled code contains nothing corresponding to the source operation.

| Operation | The measured evidence | Why it can vanish |
|---|---|---|
| A non-escaping allocation | 0.559 ns default vs 4.008 ns with `-XX:-DoEscapeAnalysis` | Nothing can observe the object, so its fields become registers |
| A boxed value that never escapes | 0.312 ns on vs 2.512 ns off, box+unbox as a pair | Same argument; the `Integer` is an object like any other |
| A monomorphic virtual call | 1.15–1.38 ns, against a bimorphic 1.92–2.49 ns | One receiver type observed, so the inline cache guards on it once and inlines the body |
| An `instanceof` whose receiver type C2 knows | 1.49–1.63 ns, ~1 ns above the 0.51–0.63 ns floor | The answer is a compile-time constant when the type is provable |
| A loop-invariant cached `hashCode` read | **0.327–0.383 ns in a plain loop vs 1.89–1.95 ns through the lambda** | The `hash` field does not change, so the read hoists out of the loop entirely |
| A concat of compile-time constants | **0.0755 ns/op** | `javac` folded it to one interned literal per JLS 15.29 before C2 saw it |

The 0.0755 ns row is the sharpest single item in this group because it is provably not the cost of building a string; `02a-measurement-and-amortisation.md` owns the constant-folding and dead-code-elimination argument in full (leaf 2.1.7), and `../strings/01b-the-string-pool.md` owns constant folding itself.

**Group B — reduced, not removed.** The operation survives, in a cheaper form than the bytecode suggests.

| Operation | What it becomes | The measured evidence |
|---|---|---|
| Bimorphic call | Two type checks plus two inlined bodies — still a branch, no longer a dispatch | 1.92–2.49 ns against a monomorphic 1.15–1.38 ns |
| Megamorphic call | A real vtable or itable dispatch; the inline cache gives up | Not separately measured on this harness — see `## Open questions` |
| Interface call, monomorphic | An inline cache guard, like the virtual case | 1.75–1.86 ns against the virtual 1.15–1.38 ns |
| Array bounds check | Often hoisted or removed when the index range is provable; the load itself remains | read 2.02–2.13 ns, store 1.72–1.78 ns |
| `StringBuilder` chain whose result is returned | The builder may be scalar-replaced; the result `String` and its `byte[]` cannot be | 3.87–4.08 ns into a reused builder vs 4.81–4.98 ns for a fresh builder plus one append |
| Warmed `Method.invoke` | The JDK generates and JIT-compiles an accessor, so the reflective call inlines partway | 4.54 ns warmed against a 0.99 ns direct call — `4.54 / 0.99 = 4.6×`, not the folklore's orders of magnitude |

`../inheritance-and-dispatch/03-internals-dispatch.md` owns the vtable, the itable and the inline-cache state machine — monomorphic to bimorphic to megamorphic — in full. What this file adds is the price of each state on this build.

**Group C — the JIT cannot touch it.** Three operations from D-064, each for a different structural reason:

| Operation | The measured evidence | Why the JIT cannot touch it |
|---|---|---|
| `intern()` | 61.81–65.33 ns, indistinguishable whether the string was already interned (61.81–64.65) or freshly allocated (63.65–65.33) — the hash probe happens either way. Against the cheap rows: `63.22 / 1.95 = 32.4` and `65.33 / 1.89 = 34.6` versus a cached `hashCode`, `63.22 / 3.02 = 20.9` and `65.33 / 3.34 = 19.6` versus an instance field read — so 32–35× a `hashCode` and ~20× a field read | A native call into the VM's `StringTable` (`StringTableSize = 65536`), not Java code C2 can inline, and its effect — a lookup or insertion in a process-global table — is observable to every other thread. It is the most expensive of D-064's cheap operations and the only band-2 row that buys nothing when the string is already canonical |
| `fillInStackTrace()` (exception construction) | 278.05–282.39 ns for construction alone; `throw`+`catch` at 282.48–284.49 ns adds almost nothing on top — **the cost is the capture, not the unwind.** A preallocated stackless instance thrown and caught measured **1.34–1.46 ns**: `282.48 / 1.46 = 193` and `284.49 / 1.34 = 212`, i.e. ~190–210× cheaper — a code change, not a compiler one | The walk is unconditional in `Throwable`'s constructor and proportional to captured depth, so its cost is a function of where in the call graph the `new` happened rather than of the operand. No compiler can shorten it without changing what `getStackTrace()` returns, which is observable. `../exceptions/02c-cost-and-control-flow.md` owns this in full, including the four-argument `Throwable` constructor and the `fillInStackTrace()` override |
| The three clock reads | `System.nanoTime()` 9.18–9.70 ns, `System.currentTimeMillis()` 13.55–13.70 ns, `Instant.now()` 19.79–20.30 ns. The ordering is the interesting part: `nanoTime` is the *cheapest* of the three despite the folklore that it is the expensive one, `currentTimeMillis` is dearer on this build, and `Instant.now()` adds the wrapper object on top of a `currentTimeMillis`-class call | All three leave the JVM for the OS clock, and the value differs on every call by definition, so the read is neither hoistable nor foldable; its cost is a property of the platform's clock source rather than of Java. `../date-and-time/02-date-and-time.md` owns `java.time`. (Planned row.) |

**Interview:** "which of these can the JIT optimise away?" — the answer that lands is the three-group split with one measured pair as evidence: non-escaping allocation goes from 0.56 ns to 4.01 ns when you turn escape analysis off, which proves group A exists; `intern()` stays at 63 ns no matter what, because it is a native call into a VM-global table, which proves group C exists; and a call's price tracks its inline-cache state — 1.15–1.38 ns monomorphic, 1.92–2.49 ns bimorphic — which is group B.

### Diagram

No diagram for this concept. D-064's fifth column is this section's content in tabular form, and the three group tables above are the argument; a second picture of the same three-way split would be the table redrawn. `../inheritance-and-dispatch/03-internals-dispatch.md` carries the inline-cache diagram that group B's rows depend on.

### A concrete example

The practical consequence, on the ledger-write path — the same method written so that the hot operations fall in group A rather than group C:

```java
final class LedgerAppender {

    private static final StatusCode CAPTURED = StatusCode.of("DEP", 3, 1, "CAPTURED");

    private final FundsLedger ledger;
    private final StringBuilder line = new StringBuilder(96);   // reused, not reallocated

    LedgerAppender(FundsLedger ledger) {
        this.ledger = ledger;
    }

    /** Group C on every field: intern(), Instant.now() per entry, concat per entry. */
    void appendSlow(long amountMinor, String positionName) {
        String position = positionName.intern();                 // ~63 ns, buys nothing
        String audit = "ledger " + position + " " + amountMinor   // ~16 ns + 2 allocations
                + " " + CAPTURED.variant() + " " + Instant.now(); // ~20 ns + 1 allocation
        ledger.append(new LedgerEntry(amountMinor, position), audit);
    }

    /** Group A and B: no intern, one clock read per batch, a reused builder. */
    void appendFast(long amountMinor, LedgerPosition position, long batchEpochMilli) {
        line.setLength(0);                                       // no allocation
        line.append("ledger ").append(position.name())            // ~4 ns per append
            .append(' ').append(amountMinor)
            .append(' ').append(CAPTURED.variant())
            .append(' ').append(batchEpochMilli);
        ledger.append(new LedgerEntry(amountMinor, position.name()), line.toString());
    }
}
```

`appendFast` removes the `intern()` entirely by taking a `LedgerPosition` enum rather than a `String` — the enum constant's name is already canonical, so the group-C call had nothing to canonicalise — and moves the clock read out of the per-entry path by taking the batch's timestamp as a parameter. At 13,600 writes/sec the two changes together are:

```
intern removed:        13,600 × 63 ns = 856,800 ns/sec  = 0.857 ms/sec
clock read removed:    13,600 × 20 ns = 272,000 ns/sec  = 0.272 ms/sec
                                                          -----------
                                                          1.13 ms/sec
```

Roughly 1.1 ms/sec of CPU, or 0.11% of one core. **State the size honestly**: this is not a heroic optimisation, and if it were the only reason to make the change it would not be worth the review. It is worth making because the enum parameter is better typing and the batch timestamp is better semantics — the nanoseconds are a side effect. That is the correct relationship between this table and your code, and the reason the table's ns column is the fourth of six rather than the first.

### The gotcha

**Pitfall:** believing a group-A number is a cost you can budget with. The wrong belief is that "a non-escaping allocation costs 0.56 ns" is a fact about allocation, so a loop doing a million of them costs 0.56 ms. The symptom: a capacity estimate built on group-A figures that is off by an order of magnitude in production, because the real code's allocation escaped — it was stored in a batch list, published to a metrics tag, or passed to a method C2 declined to inline — and the real figure was the 4.39 ns escaping row, or worse, the allocation was in a method too large to inline at all. The fix is to read the fifth column before the fourth: a group-A number is a statement about what the compiler did to *that* loop, and the only way to know what it will do to yours is to measure yours, with JMH, which guide 06 owns.

> **Definition.** Operations split three ways under C2: those it eliminates entirely because their absence is unobservable (non-escaping allocation and boxing, monomorphic calls, provable `instanceof`, loop-invariant cached reads, `javac`-folded constant concat), those it reduces to fewer instructions without removing them (bimorphic and interface calls, bounds checks, reused `StringBuilder` chains, warmed `Method.invoke`), and those it cannot touch because their effect leaves the JVM or their cost is proportional to the call stack rather than the operand (`intern()`, `fillInStackTrace()`, the three clock reads).

---

## Pitfalls

### "Boxing is expensive, so out-of-cache boxing must be much dearer than in-cache"

**Wrong**

```java
// The belief: the second loop should be dramatically slower, because 1000 is
// outside IntegerCache and must allocate.
bench("Integer.valueOf, in cache",     500_000, 5_000_000,
      i -> Integer.valueOf((int) (i & 127)).intValue());
bench("Integer.valueOf, out of cache", 500_000, 5_000_000,
      i -> Integer.valueOf(1000 + (int) (i & 1023)).intValue());
```

Measured on this build, the surprise:

```
Integer.valueOf, inside cache (-128..127)     1.62 / 1.44 / 1.35 ns
Integer.valueOf, outside cache (1000..2023)   1.63 / 1.42 / 1.33 ns
```

Indistinguishable. The out-of-cache allocation is non-escaping in this loop, so C2 eliminates it and the cache has nothing left to save.

**Right**

Price boxing by escape, not by cache membership. The same box+unbox pair, measured with and without escape analysis:

```
box+unbox (non-escaping), default          0.312 ns
box+unbox (non-escaping), -XX:-DoEscapeAnalysis   2.512 ns
```

The honest claim is "free when it does not escape, real when it does." The cache's actual job is **identity**: `Integer.valueOf(127) == Integer.valueOf(127)` is `true` and `Integer.valueOf(128) == Integer.valueOf(128)` is `false`, because `Integer.valueOf` returns `IntegerCache.cache[i + 128]` only within `IntegerCache.low`..`IntegerCache.high`. [The cost of boxing](../wrappers-and-boxing/01g-the-cost-of-boxing.md) owns the cost chapter and the cache's bounds.

**Why people believe it:** the cache genuinely exists, its bounds are genuinely `−128..127` by JLS mandate, and the inference "cache hit avoids allocation, allocation is expensive, therefore cache miss is expensive" is valid reasoning from a false premise. The premise was true on JVMs before escape analysis was on by default, which is where the folklore was formed and why it is still repeated.

### "`intern()` is cheap because it just returns an existing string"

**Wrong**

```java
// Canonicalising a position name on every ledger write, at 13,600/sec peak.
void append(long amountMinor, String positionName) {
    ledger.append(new LedgerEntry(amountMinor, positionName.intern()));
}
```

```
intern() on an already-interned literal      61.81 / 64.65 / 63.22 ns
intern() on a fresh new String(...) each call 63.65 / 64.80 / 65.33 ns
```

The already-interned path is not cheaper. Both pay the same hash probe of the VM's `StringTable`, and at ~63 ns that is 32–35× a cached `hashCode` (`63.22 / 1.95 = 32.4`) and ~20× an instance field read (`63.22 / 3.02 = 20.9`) — the most expensive operation in D-064 that is not an exception.

**Right**

```java
// The position is an enum constant; its name is already canonical.
void append(long amountMinor, LedgerPosition position) {
    ledger.append(new LedgerEntry(amountMinor, position.name()));
}
```

At 13,600 writes/sec that removes 13,600 × 63 ns = 856,800 ns/sec, about 0.86 ms/sec — small in absolute terms, and free to remove, since the enum parameter is the better API regardless. `../strings/01b-the-string-pool.md` owns when `intern()` genuinely earns its cost (a large set of duplicated strings read from an external source, retained long-term).

**Why people believe it:** "returns the canonical instance" reads like a lookup that short-circuits, and the fast path *is* short — one hash probe. What the description hides is that the probe is a **native call into the VM**, so C2 cannot inline it and the JNI-boundary and table-lookup cost is paid on both paths. The `String` javadoc describes the semantics precisely and says nothing about the cost, which is exactly the gap the measurement fills.

### "The JIT will optimise my allocation away, so allocation in a hot loop is free"

**Wrong**

```java
// The belief: this is band 0, because the split never escapes.
long totalBonusMinor(long[] stakesMinor, long bonusAvailableMinor) {
    long total = 0;
    for (long stakeMinor : stakesMinor) {
        StakeSplitMinor split = splitter.split(stakeMinor, bonusAvailableMinor);
        auditTags.put("split", split);        // publishes it — now it escapes
        total += split.bonusMinor();
    }
    return total;
}
```

One line — the `auditTags.put` — moves every iteration's allocation from the 0.301–0.559 ns non-escaping row to the 4.394 ns escaping row, and puts 24 bytes per iteration into Eden that the pre-change profile did not show. On the 13,600/sec ledger-write path that is 13,600 × 24 = 326,400 bytes/sec of garbage.

**Right**

```java
long totalBonusMinor(long[] stakesMinor, long bonusAvailableMinor) {
    long total = 0;
    for (long stakeMinor : stakesMinor) {
        total += splitter.bonusPortionMinor(stakeMinor, bonusAvailableMinor);
    }
    return total;
}
```

Return the primitive the caller actually needs, and the object has nothing to escape into. If the audit tag is genuinely required, hoist it out of the loop and record one aggregate rather than one per stake — which is also the more useful audit record.

**Why people believe it:** the measurement in section 2 is real, and the 0.56 ns figure is genuinely what a non-escaping allocation costs on this build. What does not transfer is the *condition*: C2 proved non-escape for that specific loop with that specific inlining outcome, and it makes **no documented guarantee** about any other. Escape is a property of the whole inlined region, not of the `new` statement, so a change anywhere in the region — including in a method you did not touch, whose growth pushed it past the inlining budget — can silently move the row.

---

## Cheat sheet

| Operation | Band | Measured ns (this build) | Allocations | JIT can eliminate? |
|---|---|---|---|---|
| Constant-folded concat (`"CLIENT_" + "BONUS_RESERVED"`) | 0 | 0.0755 | none | Yes — `javac`, before C2 |
| Non-escaping allocation (24-byte `LedgerEntry`) | 0 | 0.301–0.559 (4.008 with `-XX:-DoEscapeAnalysis`) | none, when eliminated | Yes |
| Non-escaping box+unbox | 0 | 0.312 (2.512 with `-XX:-DoEscapeAnalysis`) | none, when eliminated | Yes |
| Cached `hashCode`, plain loop | 0 | 0.327–0.383 | none | Yes — hoisted |
| Harness floor (empty loop) | — | **0.51–0.63** | none | — |
| Virtual call, monomorphic | 1 | 1.15–1.38 | none | Yes |
| Preallocated stackless `throw`+`catch` | 1 | 1.34–1.46 | none | No, but already at the floor |
| Boxing / unboxing, through the lambda | 1 | 1.33–1.66 (cache membership made no difference) | none in cache | Yes, when non-escaping |
| `substring(0,21)` / `substring(0,0)` | 1 | 1.41–1.65 / 1.20–1.68 | 1 `String` + `byte[]` / none | Yes here |
| `instanceof` / `checkcast` | 1 | 1.49–1.63 / 1.67–1.90 | none | Often |
| Array store / read, `long[]` | 1 | 1.72–1.78 / 2.02–2.13 | none | Bounds check often |
| Interface call, monomorphic | 1 | 1.75–1.86 | none | Yes |
| `String.hashCode`, through the lambda | 1 | 1.89–1.95 | none | Blocked here by the lambda |
| Virtual call, bimorphic | 1 | 1.92–2.49 | none | Reduced, not removed |
| `String.equals`, equal / differing | 1 | 2.21–2.41 / 1.66–1.76 | none | No |
| `BigDecimal.add`, both compact | 1 | 2.50–2.58 | 1 `BigDecimal` | Yes when non-escaping |
| Instance field read | 1 | 3.02–3.34 | none | No |
| `LocalDate.plusDays(30)` | 1 | 3.26–3.36 | 1 `LocalDate` | Yes when non-escaping |
| `BigDecimal.divide(_, 2, HALF_UP)` | 1 | 3.28–3.44 | 1 `BigDecimal` | Yes when non-escaping |
| `StringBuilder.append`, reused / fresh builder | 1 | 3.87–4.08 / 4.81–4.98 | none / builder + `byte[]` | Partly |
| Escaping allocation (24-byte `LedgerEntry`) | 1 | 4.394 | 24 bytes | No — that is the point |
| Reflective call, warmed | 1 | 4.54 plain loop · 5.65–7.12 through the lambda | arg array | No; JDK-generated accessor |
| `System.nanoTime()` | 2 | 9.18–9.70 | none | No — OS clock |
| `System.currentTimeMillis()` | 2 | 13.55–13.70 | none | No — OS clock |
| `String` concat, 2 / 5 non-constant operands | 2 | 8.01–9.95 / 15.63–16.88 | result `String` + `byte[]` | No |
| `Instant.now()` | 2 | 19.79–20.30 | 1 `Instant` | No |
| `intern()` | 2 | 61.81–65.33 | none on the interned path | **No — native VM call** |
| Exception construction, depth ~5 | 3 | 278.05–282.39 | exception + message + backtrace | **No — unconditional stack walk** |
| `throw`+`catch`, depth ~5 | 3 | 282.48–284.49 | as above | No; cost climbs per extra captured frame — slope derived in `02a-measurement-and-amortisation.md` |
| Interpreter-only (`-Xint`) allocation | — | 42.66 non-escaping, 42.16 escaping, 63.38 box+unbox | — | Nothing — no JIT |
| First cold `Method.invoke` | 4 | 13,791 (single sample) | accessor generation | No — one-off, per method |
| Exception construction, depth 1000 | 4 | 16,482.7 | as above | No |
| `UseTLAB` / `TLABSize` / `MinTLABSize` / `TLABWasteTargetPercent` | — | `true` / `0` (adaptive) / `2048` bytes / `1` | — | — |
| `DoEscapeAnalysis` / `EliminateAllocations` / `ObjectAlignmentInBytes` | — | `true` / `true` / `8` | — | — |
| `StringTableSize` / `MaxJavaStackTraceDepth` / `UseCompressedOops` | — | `65536` / `1024` / `true` | — | — |

---

## Self-test

**Q1.** Someone quotes "a monomorphic virtual call costs 1.15 ns and `substring(0,0)` costs 1.20 ns, so they are about the same." What is wrong with the sentence, even though both numbers are correct?

<details><summary>Answer</summary>

Both figures are inside the harness's own noise, so the comparison is meaningless in either direction. The empty-loop baseline — a `LongUnaryOperator` call and nothing else — measured 0.51–0.63 ns/op across three runs, and the virtual-call row itself moved 1.15 → 1.17 → 1.38 across three runs of identical code, which is more movement than separates it from the `substring` row. Both operations are "too cheap to separate from the measurement apparatus," and the correct statement is that they are both in band 1 and neither is worth a design decision. The rows that *are* comparable are ones an order of magnitude apart: `intern()` at 61.81–65.33 ns against a field read at 3.02–3.34 ns is a real ~20× ratio that survives any harness (`63.22 / 3.02 = 20.9`, `65.33 / 3.34 = 19.6`), and exception construction at 278.05–282.39 ns against a preallocated stackless throw at 1.34–1.46 ns is a real ~190–210× ratio (`278.05 / 1.46 = 190`, `282.39 / 1.34 = 211`). The rule is to compare across bands, never within one.

</details>

**Q2.** Are objects expensive in Java? Answer with one measurement.

<details><summary>Answer</summary>

Conditionally, and the condition is escape. A 24-byte `LedgerEntry` — 12-byte header plus an 8-byte `long` plus a 4-byte compressed reference, already 8-aligned — allocated in a tight loop and never allowed to leave the method measured **0.301–0.559 ns/op**, at the harness floor. The same loop under `-XX:-DoEscapeAnalysis` measured **4.008 ns/op**, a ~7× jump (`4.008 / 0.559 = 7.2`), which proves the default figure is not the cost of allocating; it is the cost of not allocating, because C2 proved the object could not be observed and turned the constructor's two field writes into two register moves. An object that genuinely escapes — stored to a `volatile` — measured **4.394 ns**, which is the honest price of a real allocation: a TLAB bump-pointer increment plus header initialisation, with no lock and no atomic. So the answer is: an object that provably does not escape its method frequently costs nothing at all, and one that escapes costs about 4 ns and 24 bytes of Eden. What you cannot do is rely on the first case, because C2's escape-analysis and scalar-replacement heuristics are unspecified and the JVM guarantees nothing about when they apply.

</details>

**Q3.** Why is `intern()` the most expensive of the cheap operations, and why is it no cheaper when the string is already interned?

<details><summary>Answer</summary>

Because it is not Java code. `String.intern()` is a native call into the VM's `StringTable`, a process-global hash table sized by `StringTableSize = 65536` on this build, so C2 cannot inline it, cannot hoist it out of a loop, and cannot elide it — its effect is observable to every other thread in the process. Measured at 61.81–65.33 ns, that is roughly 32–35× a cached `hashCode` (1.89–1.95 ns through the same harness: `63.22 / 1.95 = 32.4`, `65.33 / 1.89 = 34.6`) and ~20× an instance field read (3.02–3.34 ns: `63.22 / 3.02 = 20.9`, `65.33 / 3.34 = 19.6`), which puts it at the top of band 2 alongside the clock reads. It is no cheaper on an already-interned string — 61.81/64.65/63.22 ns for an already-interned literal against 63.65/64.80/65.33 ns for a fresh `new String(...)` each call, indistinguishable — because both paths perform the same hash probe of the table; the only thing "already interned" saves is the insertion, which is not the dominant cost. The practical consequence on the ledger-write path at 13,600/sec is 13,600 × 63 ns = 856,800 ns/sec, about 0.86 ms/sec of CPU, and the reason to remove it is not the 0.86 ms but that a `StatusCode` or ledger position sourced from an enum is already canonical, so the call buys nothing.

</details>

**Q4.** A benchmark reports `"CLIENT_" + "BONUS_RESERVED"` at 0.0755 ns/op. What did it actually measure?

<details><summary>Answer</summary>

Not the concat. 0.0755 ns is below one CPU cycle at any clock this machine runs, so it cannot be the cost of building a string — `javac` folded the two constant operands into one interned literal per JLS 15.29 before the JIT ever saw them (`02a-measurement-and-amortisation.md` owns constant folding and dead-code elimination in full, and `../strings/01b-the-string-pool.md` owns the fold itself).

What *this* file's leaves let you say next is where the figure belongs in the model. It is a band-0 row: band 0 is defined by "the operation does not happen at all," and the fifth column of D-064 marks constant concat as eliminable *entirely, but only when every operand is constant*. Move one operand off the constant side and the same expression leaves band 0 for band 2 — D-064's concat row measures 8.01–9.95 ns for two non-constant operands and 15.63–16.88 ns for five, both of which really allocate a result `String` and its `byte[]`. That is the section-1 insight in one example: the band is a joint property of the operation and the compiler's view of it, not of the operation alone, which is also why the fifth column carries more information than the fourth. Guide 06 owns JMH, `Blackhole` and forking, which are the tool for a number you would put in a capacity plan.

</details>

**Q5.** Which operations in the table can the JIT not eliminate, and what do the three have in common?

<details><summary>Answer</summary>

Three, each for a different mechanism but one shared reason. `intern()` at 61.81–65.33 ns is a native call into the VM's `StringTable`, and its effect on that process-global table is visible to every other thread. `fillInStackTrace()` — the dominant term in exception construction at 278.05–282.39 ns — is an unconditional walk in `Throwable`'s constructor whose result is observable through `getStackTrace()`, and whose cost is proportional to captured depth rather than to any operand, capped at `MaxJavaStackTraceDepth = 1024`. The three clock reads — `System.nanoTime()` at 9.18–9.70 ns, `System.currentTimeMillis()` at 13.55–13.70 ns, `Instant.now()` at 19.79–20.30 ns — leave the JVM for the OS clock and return a different value every call, so they are neither foldable nor hoistable. What they share: their effect is observable **outside** the compiled method, which is exactly the boundary of the JIT's licence. The JLS and JVMS specify observable behaviour, not instruction sequences, so C2 may delete only work whose absence nothing can detect — which is also why the eliminable group is exactly the non-escaping allocations, the monomorphic calls, the provable type checks and the loop-invariant reads.

</details>

**Q6.** Work out the CPU cost of one `Instant.now()` per ledger entry at peak, and say whether it is worth removing.

<details><summary>Answer</summary>

`Instant.now()` measured 19.79–20.30 ns on this build, and the ledger write rate peaks at 13,600/sec, so 13,600 × 20 ns = 272,000 ns/sec = **0.272 ms/sec**, or about 0.027% of one core. Compare it to the busiest cheap operation on the same path — a field read at ~3.2 ns is 13,600 × 3.2 = 43,520 ns/sec, 0.044 ms/sec — and `Instant.now()` is about six to seven times that (`19.79 / 3.34 = 5.9`, `20.30 / 3.02 = 6.7`), which is the ratio the band model predicts (band 2 against band 1). Is it worth removing? Not for the 0.272 ms in isolation; that number would never justify a change on its own, and saying otherwise is how cost tables get misused. It is worth removing when the same change improves the semantics — taking one batch timestamp as a parameter rather than reading the clock per entry gives every entry in a batch a consistent timestamp, which is a correctness property for a double-entry ledger, and the nanoseconds are a side effect. If you must keep a per-entry clock read, `System.currentTimeMillis()` at 13.55–13.70 ns is cheaper than `Instant.now()` because it skips the wrapper allocation, and `System.nanoTime()` at 9.18–9.70 ns is cheapest of the three but is monotonic rather than wall-clock and is therefore wrong for a ledger timestamp.

</details>

**Q7.** Explain the TLAB in one paragraph, and name what the measured flags tell you about it.

<details><summary>Answer</summary>

Each thread owns a private slab of Eden — a Thread-Local Allocation Buffer — described by a start pointer, a bump pointer and an end pointer. Allocating an object of known size is a compare (`bump + size <= end`), a header and field write, and an add to advance `bump`; there is no lock and no atomic instruction, because no other thread can touch this buffer. The slow path runs only when the check fails: the thread takes a fresh slab from Eden, which *is* synchronised but is amortised across every allocation that slab serves, or triggers a young collection if Eden is full. The flags measured on this build via `-XX:+PrintFlagsFinal`: `UseTLAB = true`, so this is the default path; `TLABSize = 0`, meaning adaptive — the JVM sizes each thread's buffer from that thread's observed allocation rate rather than a fixed constant; `MinTLABSize = 2048` bytes as the floor; and `TLABWasteTargetPercent = 1`, bounding how much of a slab the JVM will abandon when a large allocation does not fit the remainder. The measured consequence is the 4.394 ns escaping-allocation row: that is what a bump plus header initialisation actually costs. Guide 06 owns GC and generational heap layout beyond the slab.

</details>

**Q8.** `-XX:-EliminateAllocations` did not restore the cost of the non-escaping allocation. What should you conclude?

<details><summary>Answer</summary>

That you have found something you cannot explain, and that the correct move is to report it rather than to invent a rule. Measured: the non-escaping row was 0.559 ns by default, 4.008 ns under `-XX:-DoEscapeAnalysis`, and **0.301 ns** under `-XX:-EliminateAllocations` — still at the harness floor, so the flag that gates scalar replacement changed nothing. The plausible reading is that with only a field read after the constructor, the allocation is being removed by ordinary dead-code elimination rather than by scalar replacement, so the flag has nothing left to gate; but that is a hypothesis, not a verified finding, and this file marks it unverified. The same applies to the second anomaly in that table: the *escaping* allocation measured **faster** with escape analysis off (2.162 ns) than on (4.394 ns), the opposite of the expected direction, most likely a different inlining or unrolling decision at a different iteration count. The structural reason both stay unverified is that C2's escape-analysis and scalar-replacement heuristics are not specified anywhere and the JVM makes no documented guarantee about when either applies — so there is no document to check the behaviour against, only the C2 source, which guide 06 owns. What is settled is the direction of the non-escaping row under `-XX:-DoEscapeAnalysis`: 0.56 → 4.01 ns, a 7× move (`4.008 / 0.559 = 7.2`), and that is the measurement the leaf is about.

</details>

---

## Open questions

- **Unverified:** why the *escaping* allocation measured faster with `-XX:-DoEscapeAnalysis` (2.162 ns) than with escape analysis on (4.394 ns). The plausible reading is a different inlining or loop-unrolling decision taken on a different iteration count — that row ran 2,000,000 iterations against the other rows' 20,000,000 — but this has not been confirmed. What would settle it: re-running the escaping row at the same 20,000,000 iterations as its neighbours, and a `-XX:+PrintInlining` / `-XX:+PrintCompilation` comparison of the two configurations' compiled output for that loop.
- **Unverified:** why `-XX:-EliminateAllocations` did not restore the non-escaping allocation's cost (0.301 ns, still at the harness floor, against 4.008 ns under `-XX:-DoEscapeAnalysis`). The plausible reading is that with only a field read following the constructor, the allocation is eliminated by ordinary dead-code elimination rather than by scalar replacement, leaving the flag nothing to gate. What would settle it: re-running with a loop body that forces the constructed object's fields to be genuinely consumed but not published, plus a `-XX:+PrintEliminateAllocations`-class diagnostic build or a read of C2's `macro.cpp` escape-state handling, which guide 06 owns.
- **Unverified (standing):** C2's escape-analysis and scalar-replacement heuristics generally. The JVM makes no documented guarantee about when either optimisation applies, so no claim in this file that an allocation "will be" eliminated should be read as more than "was, in this loop, on this build." What would settle it for any given site: measuring that site, with JMH.
- **Unverified:** the cost of a **megamorphic** virtual or interface call on this build. D-064 and section 3's group-B table name it as falling back to a real vtable or itable dispatch, on the strength of the inline-cache mechanism `../inheritance-and-dispatch/03-internals-dispatch.md` owns, but only monomorphic (1.15–1.38 ns) and bimorphic (1.92–2.49 ns) were measured here — no megamorphic row exists, and none is printed. What would settle it: adding a harness row cycling three or more receiver types through the same call site, which is the standard way to force the inline cache past its bimorphic limit.
- **Unverified:** the object-header and allocation figures under any configuration other than compressed oops. `UseCompressedOops = true` is ergonomic on this build, and the 24-byte `LedgerEntry` arithmetic (12-byte header + 8-byte `long` + 4-byte reference) assumes it. `UseCompactObjectHeaders` does not exist on JDK 21, so no smaller header was measurable. What would settle the alternative: re-running under `-XX:-UseCompressedOops`, where the header is 16 bytes and a reference is 8, and re-deriving the row.

---

**Leaves covered:** 2.1.1, 2.1.2, 2.1.3 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** D-064 (rendered as a Markdown table, per the manifest's `Type: table`)
**Target version:** Java 21 LTS
**Lines:** 644
