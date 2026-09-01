# Ad-hoc Paper 1 — Answer Key

Scoring: 1 = matches the key's marks · 0.5 = right idea with a named gap ·
0 = wrong or blank · — = `[CODE]` deferred to the code batch.

**Q1.** (a) **Sliding window** with a hash map of char→count; expand right,
shrink left while distinct > K — O(n). (b) **Monotonic stack** (decreasing);
each element pushed and popped at most once — O(n) despite the inner while.
(c) **Two pointers** from both ends of the sorted array — O(n), O(1) space; a
hash set also works at O(n) space, but sortedness is the signal for two
pointers. (d) **Binary search on the answer** — "minimize the maximum" is the
signature; search the answer space of possible max-sums, greedily check
feasibility — O(n log(sum)).
Marks: 0.25 each, pattern name AND complexity both required.

**Q2.** `n ≤ 20` admits exponential solutions — 2ⁿ ≈ 10⁶, so bitmask DP,
subset enumeration, or backtracking are intended. `n ≤ 10⁵` rules those out and
points at O(n log n) or O(n) — sorting, a single pass, a heap, or a hash map.
Reading it first stops you designing an elegant O(n²) that times out, and it
tells the interviewer you know the mapping. Rough anchor: ~10⁸ simple
operations per second.

**Q3.** `[CODE]`
```java
int[] twoSum(int[] nums, int target) {
    Map<Integer, Integer> seen = new HashMap<>();
    for (int i = 0; i < nums.length; i++) {
        Integer j = seen.get(target - nums[i]);
        if (j != null) return new int[]{j, i};
        seen.put(nums[i], i);
    }
    return new int[0];
}
```
Marks: compiles and runs; single pass, complement looked up **before**
inserting the current element (inserting first breaks the
same-element-twice rule); O(n) time / O(n) space stated; brute force named as
O(n²) time / O(1) space. Missing the complexity statement = 0.5 — that clause
was asked explicitly (this is the recurring asked-instance pattern).

**Q4.** Slow advances one node, fast two. If fast reaches null there is no
cycle; if they meet, a cycle exists. **The meeting point is not the cycle
start.** To find it: reset one pointer to `head`, leave the other at the
meeting point, then advance **both one step at a time** — they meet at the
first node of the cycle. O(n) time, O(1) space. Naming the reset-to-head step
is the mark; "they meet at the start" is a 0.

**Q5.** `LinkedHashMap`, constructed with `accessOrder = true`
(`new LinkedHashMap<>(16, 0.75f, true)`), overriding
`removeEldestEntry(Map.Entry eldest)` to return `size() > MAX`. The surprising
consequence: in access-order mode **`get()` mutates the map's internal ordering** —
so it is not safe to call concurrently even for reads, and iterating while
getting can throw. Marks: class + constructor flag + method; the get-mutates
consequence is the second mark half.

**Q6.** (a) Throws `ConcurrentModificationException`. Mechanism: the list keeps
a `modCount`; the iterator snapshots it as `expectedModCount` at creation and
compares on every `next()` — a structural modification through the list rather
than the iterator makes them diverge. Note it is **best-effort**, not a
guarantee. (b) `removeIf` performs the removal internally in one pass and keeps
the counts consistent — the idiomatic choice. (c) `Iterator.remove()` is the
low-level correct way: it removes through the iterator and updates
`expectedModCount`. Marks: CME named + the modCount/expectedModCount pair +
both safe alternatives.

**Q7.** Output:
```
before terminal
ann
bob
cal
```
Streams are **lazy**: nothing in the pipeline runs until the terminal operation
(`toList()`), so "before terminal" prints first; then elements flow through
`peek` and `map` **one at a time** (fused), not stage by stage. A second
`s.toList()` throws `IllegalStateException` — **a stream can be consumed only
once**. The `peek` rule: it exists for debugging only, the JDK is permitted to
**skip it entirely** when it can prove the elements are unneeded, so never put
side effects there. Marks: laziness/ordering + single-consumption + the peek rule.

**Q8.** (1) **Duplicate keys** — two users with the same email throw
`IllegalStateException: Duplicate key`. Fix: supply a merge function,
`toMap(User::getEmail, identity(), (a, b) -> a)` (and decide deliberately which
wins). (2) **A null value** — `toMap` throws `NullPointerException` if the value
mapper returns null (unlike `HashMap.put`). Fix: filter nulls out first, or
collect with `groupingBy`/a manual `HashMap`. Test data usually has neither
duplicates nor nulls, which is why it survives to production. Marks: 0.5 each,
cause + fix.

**Q9.** Defaults: a `HashMap` of `ArrayList` — so **no ordering guarantee** on
either. For a `TreeMap` of `Set`s:
`groupingBy(Order::getStatus, TreeMap::new, toSet())`. `stream.toList()`
(Java 16+) returns an **unmodifiable** list and permits nulls;
`collect(Collectors.toList())` returns a mutable `ArrayList` with no
unmodifiability guarantee. Marks: defaults + the three-arg overload + the
mutability difference.

**Q10.** (a)
```java
record Money(String currency, BigDecimal amount) {
    Money {
        Objects.requireNonNull(currency, "currency");
        if (amount.signum() < 0) throw new IllegalArgumentException("negative amount");
    }
}
```
The **compact constructor** validates (and may normalise by reassigning the
parameter, e.g. `currency = currency.toUpperCase()`) before the fields are
assigned. (b) Records are **shallowly immutable**: the `List<String> tags`
reference can't be reassigned, but the caller who passed the list can still
mutate it, and `tags()` hands the same reference back out. Fix: defensive-copy
in the compact constructor (`tags = List.copyOf(tags)`) — and avoid array
components entirely, since arrays also break `equals`/`hashCode`.
Marks: compact constructor form (0.5) + shallow immutability with `List.copyOf`
(0.5).

**Q11.**
```java
sealed interface Shape permits Circle, Square {}
record Circle(double r) implements Shape {}
record Square(double side) implements Shape {}

double area(Shape s) {
    return switch (s) {
        case Circle c -> Math.PI * c.r() * c.r();
        case Square q -> q.side() * q.side();
    };
}
```
Benefit: the compiler knows the permitted set is closed, so the switch is
checked for **exhaustiveness** — no `default` branch is needed, and when
someone adds `Triangle` to the permits clause, **every switch that doesn't
handle it fails to compile.** That converts a runtime bug (an unhandled type
silently falling into `default`, or an `IllegalArgumentException` in
production) into a compile error found at the point of change. Marks: sealed
syntax + exhaustive switch without `default` + the compile-error-instead-of-
runtime-bug statement.

**Q12.** (a) The virtual thread **unmounts** from its carrier platform thread
when it hits an instrumented blocking call: its continuation (stack) is parked
on the heap, the carrier is released to run other virtual threads, and it is
remounted when the I/O completes. That unmount-on-block is the whole mechanism.
(b) **Pinning** — blocking while inside a `synchronized` block or in a native
frame prevents unmounting and holds the carrier. Workaround on JDK 21: use
`ReentrantLock` instead of `synchronized` around blocking sections.
(c) They do not help **CPU-bound** work (you still have only N cores), and
replacing a bounded pool **removes your backpressure** — the pool's queue and
max size were an implicit concurrency limit, so add an explicit `Semaphore` or
you will open unbounded connections downstream. Also: do not pool virtual
threads. Marks: 1/3 each.

**Q13.** All are post-Java-8. `var` (10) — local type inference, removes
repeated type noise; compile-time only, no runtime cost. Text blocks (15) —
multi-line string literals without escaping, for SQL/JSON; indentation is set by
the least-indented line **including the closing delimiter**. Switch expressions
(14) — switch that returns a value, arrow form, no fallthrough, must be
exhaustive. `Optional.orElseThrow()` no-arg (10) — the readable replacement for
`get()`. Sequenced collections (21) — uniform `getFirst`/`getLast`/`reversed`
across List, Deque and LinkedHashMap. Marks: 0.2 each; calling any of them
Java 8 is the failure mode this question tests.

**Q14.** (1) `Java heap space` — the heap is genuinely full, from a leak or an
undersized heap. (2) `Metaspace` — class metadata exhausted in native memory,
typically a classloader leak or redeploy churn. (3) `unable to create new
native thread` — the OS refused a thread, usually thread-count or memory
limits, not heap. (4) `Direct buffer memory` — off-heap NIO buffers exhausted.
(`GC overhead limit exceeded` is an acceptable fifth: >98% of time in GC
reclaiming <2%.) The flag: `-XX:+HeapDumpOnOutOfMemoryError` (with
`-XX:HeapDumpPath=...`), ideally alongside `-XX:+ExitOnOutOfMemoryError`, since
an OOM otherwise kills only the one thread and leaves a zombie process.
Marks: 0.75 for at least three messages read correctly, 0.25 for the flag.
**StackOverflowError is not an OOM** — offering it costs the mark.

**Q15.** The heap is only part of the JVM's RSS. Outside it: **metaspace**,
**code cache** (JIT-compiled methods), **thread stacks** (~1 MB each, so a
200-thread service is ~200 MB), **direct/NIO buffers**, **GC structures and
internal overhead**. With `-Xmx2g` in a 2Gi container, the process exceeds the
cgroup limit as soon as the heap approaches full, and the **kernel OOM killer**
terminates it: **exit code 137, no stack trace, no heap dump** — visible in
`dmesg` and as `OOMKilled` in Kubernetes, which is a completely different
failure from `OutOfMemoryError`. Instead use
`-XX:MaxRAMPercentage=70` (the JVM then sizes itself from the cgroup limit and
leaves native headroom); note the default is only 25%. Marks: three-plus
non-heap regions (0.5) + OOMKilled/137 named (0.25) + the flag (0.25).

**Q16.** `ClassNotFoundException` is a **checked exception** thrown by an
explicit dynamic lookup — `Class.forName`, `loader.loadClass` — when the name
isn't findable. `NoClassDefFoundError` is an **Error** thrown when the class was
present at compile time and the JVM can't complete its use at runtime. The
common case: the class was found but its **static initializer already threw**,
so the class is marked erroneous and every subsequent reference gets
`NoClassDefFoundError`. Go looking earlier in the log for the
**`ExceptionInInitializerError`** and its cause — that is the real failure; the
`NoClassDefFoundError` is the echo. Marks: checked-vs-Error + dynamic-lookup vs
runtime-use (0.5), the static-initializer/`ExceptionInInitializerError` hunt (0.5).

**Q17.**
1. `top -H -p <pid>` — per-**thread** CPU inside the JVM; note the TID of the
   hot thread (plain `top` only shows the process).
2. Convert the decimal TID to hex: `printf '%x\n' <tid>`.
3. Take a thread dump — `jstack <pid>` (or `jcmd <pid> Thread.print`), **three
   times a few seconds apart**, so you can tell a genuinely stuck/looping stack
   from a sampling coincidence.
4. Find `nid=0x<hex>` in the dump — that frame is the thread burning CPU.

Rule out first: **GC threads**. If the hot threads are `GC task thread`/`G1
Young RemarkTask`, the problem is memory pressure, not application code — check
`jstat -gcutil <pid> 1s` before reading application stacks. Also worth ruling
out: a JIT compiler thread during warmup right after a deploy.
Marks: `top -H` (0.25), hex conversion + `nid` match (0.5), three dumps or the
GC-first check (0.25). Answering "use a profiler" alone = 0.5.

**Q18.** (a) The **old-generation occupancy immediately after a full GC** — the
post-collection floor. Normal churn returns to the same floor; a leak makes the
floor rise monotonically across days. `jstat -gcutil <pid> 5s` shows it; heap
sawtooth alone proves nothing. (b) A **heap dump**
(`jcmd <pid> GC.heap_dump /path/file.hprof`, or automatically via
`-XX:+HeapDumpOnOutOfMemoryError`) and a **thread dump** (`jstack`) — open the
heap dump in **Eclipse MAT** (a class **histogram** diff via `jmap -histo:live`
over time is the cheaper first look). (c) **Retained size** — the memory that
would be freed if the object went away — identifies the culprit, via the
dominator tree and path-to-GC-roots. **Shallow size** is misleading because the
leaking object is usually a small container (a `HashMap` in a singleton bean)
holding an enormous graph: tiny shallow, huge retained. Marks: 1/3 each.

---

## Section mapping (for the valuation)

| Section | Questions | Topic guide |
|---|---|---|
| 1 DSA pattern recognition | Q1–Q4 | `01-dsa-fundamentals.md` |
| 2 Collections internals | Q5–Q6 | `02-java-collections.md` |
| 3 Streams & Optional | Q7–Q9 | `04-modern-java.md` |
| 4 Language features 9–21 | Q10–Q13 | `04-modern-java.md` |
| 5 JVM memory & errors | Q14–Q16 | `06-jvm-internals.md` |
| 6 JVM diagnostics | Q17–Q18 | `06-jvm-internals.md` |

Expected range if the UNMEASURED classification is right: **6–9/18**, with
Section 1 and Q5–Q9 carrying most of it and Sections 4/6 near zero. A score
above 12 would mean topic 04 and 06 are better than the sampling suggested and
their study allocation should shrink.