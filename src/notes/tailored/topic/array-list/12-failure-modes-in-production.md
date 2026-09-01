# `ArrayList` — 12 Failure modes in production

**Target version: Java 21 LTS.** | [Map](00-map.md)
Assumes: the add/grow mechanism (files 05, 06), the fail-fast protocol (file 08), and the footprint arithmetic (file 10).
Previous: [11 Choosing `ArrayList` and its alternatives](11-choosing-array-list-and-its-alternatives.md) · Next: [13 Version history and stale claims](13-version-history-and-stale-claims.md)

Every misuse below compiles, passes a unit test against a small fixture, and ships. Each is a known mechanism — `add`'s four unsynchronized steps, `clear()` nulling slots without touching the array, `SubList`'s `offset`-into-the-root arithmetic — meeting a condition test fixtures never create: a shared list, a long-lived list, a 500,000-row input, a reference held past the point that made it valid. Nothing here is a new fact; it is the ten shapes the facts you already have take on when the code around them is wrong.

## The ten misuses at a glance

| # | Misuse | Production symptom | Fix |
|---|---|---|---|
| 1 | Buffer the whole input before processing | `OutOfMemoryError`, or GC thrash that slows before it dies | Stream and process in bounded batches |
| 2 | `clear()` a long-lived list and keep it | Heap dump: `size()` 0, a large `Object[]` still retained | `trimToSize()`, or replace with a fresh list |
| 3 | Two threads `add()` to one shared list | An element vanishes; `size()` short by one | Confine + publish immutably, or a concurrent structure |
| 4 | Two threads `add()` to one shared list | `NullPointerException` reading `[0, size)` far from any write | Same as #3 |
| 5 | Two threads `add()` while one grows | `ArrayIndexOutOfBoundsException`, or silent truncation | Same as #3 |
| 6 | Pass `Arrays.asList(...)` where mutation is expected | `UnsupportedOperationException`, only on the mutating path | `new ArrayList<>(Arrays.asList(...))` |
| 7 | Return `subList(...)` from a repository method | CME on next access, no visible concurrent edit | `List.copyOf(view)` at the boundary |
| 8 | `remove(0)` in a loop, or `removeAll(list)` | Fine at 40k rows, ~150× worse at 500k | `ArrayDeque`; a `HashSet` argument |
| 9 | Mutate a list inside `forEach`/a stream over it | Intermittent CME under load, never in a test | Collect first, mutate after |
| 10 | An `ArrayList` as, or against, a `HashMap` key while mutable | CME thrown out of `hashCode()`/`equals()` | Never key a map on a mutable collection |

Rows 3–5 are one mechanism wearing three faces — the answer to **Q-35**, worked in full below. Rows 1, 2,
7 get the full eight-beat treatment; each carries a cost claim and a real alternative. Rows 6, 8, 9, 10
close the file as `## Pitfalls`, single named gotchas rather than shapes with tradeoffs. No diagram
accompanies this file — every failure here is a code-and-symptom pair. Diagrams D-10 (growth-and-copy
arithmetic) and D-13 (the fail-fast escape) already carry the two pictures this file leans on.

## Primary concepts

### Unbounded accumulation as an OOM source

**Mental model.** Reading an entire external input into one `ArrayList` before touching a record is
building a second, private copy of the whole file in the heap, sized to whatever the file happens to be
that day.

**Why it exists.** `list.add(record)` inside a `while (reader.hasNext())` loop is the first thing anyone writes, and it is correct against a 40-record fixture — no batching, no checkpointing, one finished list at the end.

**When it applies, and when it does not.** Fine when the input size is bounded and known — a `PaymentRun`'s `itemIds`, a page of 50 operator-queue cases. Wrong the moment the input is an external file whose size is a property of the calendar: QuizStakes's month-end bank statement file is **500,000 records** against **40,000** on an ordinary day (Appendix A.5).

**How it works.** File 10's arithmetic: a 4-byte compressed-oop slot plus up to 33% slack from 1.5× growth; the sequence measured to 100,000 elements took **24** `grow` calls, ending at capacity 106,710 — 6,710 wasted slots. At 500,000 objects every `grow()` past the first several is a full `Arrays.copyOf` of everything so far, live alongside the old array until the copy finishes. Old-gen occupancy climbs, GCs get less effective, and the process slows before `OutOfMemoryError` ends it — usually after §15.5's partial-failure requirement (**499,600 must still credit** even when 400 fail matching) is already violated, because nothing was processed until the read finished.

```java
// Wrong: 500,000 add() calls before the loop below even starts.
List<BankStatementRecord> records = new ArrayList<>();
try (var reader = BankStatementReader.open(monthEndFile)) {
    BankStatementRecord r;
    while ((r = reader.next()) != null) records.add(r);
}
for (BankStatementRecord r : records) matchingService.match(r);

// Right: bounded buffer, drained on the way in.
static final int BATCH_SIZE = 2_000;
List<BankStatementRecord> batch = new ArrayList<>(BATCH_SIZE);
try (var reader = BankStatementReader.open(monthEndFile)) {
    BankStatementRecord r;
    while ((r = reader.next()) != null) {
        batch.add(r);
        if (batch.size() == BATCH_SIZE) { matchingService.matchAll(batch); batch.clear(); }
    }
    if (!batch.isEmpty()) matchingService.matchAll(batch);
}
```

The bounded version's peak live set is `BATCH_SIZE` regardless of file size, and it gets §15.5's partial
failure right for free — a batch that fails matching does not block the batches before or after it.

**The gotcha.** `new ArrayList<>()` for the accumulator is worse than `new ArrayList<>(expectedSize)`,
even guessed, because every unplanned `grow()` copies everything so far. **Pitfall:** a
`removeAll`/`retainAll` filter against the batch (misuse #8) turns a bounded-memory fix into a
bounded-memory-but-quadratic-time one.

> **Definition.** Unbounded accumulation is buffering an entire external input in one `ArrayList` before any of it is consumed — bounded only by the input's size, never by the process's.

### The retained-capacity leak

**Mental model.** `clear()` empties the list the way emptying a drawer empties its contents — the drawer
itself, at its former size, stays exactly there.

**Why it exists.** From file 08's `## 6`:

```java
public void clear() {
    modCount++;
    final Object[] es = elementData;
    for (int to = size, i = size = 0; i < to; i++)
        es[i] = null;
}
```

It nulls every slot and sets `size` to 0, but never touches `elementData`. Deliberate and cheap: `clear()`
then reuse at a similar size is common, and reallocating on every clear would punish it.

**When it applies, and when it does not.** Right for a list about to be refilled to a similar size — a
per-request scratch buffer. Wrong for a list that held a one-time peak and now sits idle, because the
array stays retained at that peak's size for as long as the field lives.

**How it works.** A long-lived `PaymentRun` coordinator's `itemIds` list — grown to the largest run ever processed, then `clear()`-ed between runs and kept as an instance field — keeps its high-water-mark array alive across every smaller run after. Appendix A.6 notes a `PaymentRun` *object* is "promoted, discarded wholesale" at 5–40 minutes, but a field that only gets `clear()`-ed is never discarded; it stays promoted, sized for the biggest run.

```java
final class PaymentRunCoordinator {
    private final List<PaymentItemId> workingSet = new ArrayList<>();

    void runBatch(List<PaymentItemId> items) {
        workingSet.addAll(items);   // grows to fit the largest run ever seen
        process(workingSet);
        workingSet.clear();         // size() == 0, capacity unchanged
    }
}
```

A heap dump between runs shows `workingSet.size() == 0` and a backing `Object[]` retained at whatever the largest batch was — say 500,000 references at 4 bytes under compressed oops: roughly 2 MB held for every ordinary run afterward, for a field whose logical content is empty.

**Fix, with its cost named.** `workingSet.trimToSize()` right after `clear()` reallocates down to `size` — here, `EMPTY_ELEMENTDATA`, cost zero — but pays for a fresh `Arrays.copyOf` on the next `addAll`. Replacing the field outright is cheaper when the old array is about to be garbage anyway; it is *not* cheaper if the coordinator is mid-reuse at a reasonable size.

**The gotcha.** A large empty-looking array retained by a non-empty-looking field is the heap-dump
signature; `size()` alone will not show it. **Insight:** capacity is `elementData.length`, not a tracked
field (file 01), so no API reports the leak — only a heap dump or `trimToSize()`'s before/after does.

> **Definition.** The retained-capacity leak is a long-lived list whose backing array stays sized to its historical peak because `clear()` nulls elements, not the array, and nothing calls `trimToSize()` or replaces it.

### What actually happens under concurrent mutation

**Mental model.** `add(E)` is not one operation that might race with another `add(E)`. It is four
separate, unsynchronized field operations, and a second thread can land its own four operations anywhere
between yours.

**Why "not thread-safe" is not an answer.** It names a fact and hides the mechanism that tells you which
symptom is in front of you — file 05/06's `add` walk and file 08's `modCount` fields already give every
piece needed to derive it. **When it applies:** any time an `ArrayList` reference is handed to more than
one thread and at least one mutates it — including a "mostly read" list, because even pure reads race with
someone else's writes.

**How it works — the six steps, named.** `add(E)`, unchanged from file 05:

```java
public boolean add(E e) {
    modCount++;                      // (1)
    add(e, elementData, size);       // (2) reads elementData and size
    return true;
}

private void add(E e, Object[] elementData, int s) {
    if (s == elementData.length)     // (3)
        elementData = grow();        // (4) allocate + copy + field reassign
    elementData[s] = e;               // (5)
    size = s + 1;                     // (6)
}
```

There is **no synchronization and no `volatile` anywhere** in this path. `size` and `elementData` are
plain fields — nothing guarantees one thread ever *sees* another's write. Six symptoms fall out of naming
an interleaving of steps (1)–(6) across two threads, `A` and `B`, both appending `LedgerEntry` rows to one
shared `ArrayList` during the **3,400/sec settlement burst** (Appendix A.2):

1. **A lost element.** `A`/`B` read the same `s` at (2), both store at (5) — `B` overwriting `A` — both
   set `size = s + 1` at (6). One `LedgerEntry` gone with no trace: a `Movement` that no longer sums to
   zero (§11.7 invariant 1), surfaced only by a reconciliation break (§14.3).
2. **A trailing `null` inside `[0, size)`.** `A` completes (6) before `B` reaches its (5) store. A reader
   iterating `[0, size)` right then reads `null` at a live index and gets an NPE calling `entry.amount()`.
3. **`ArrayIndexOutOfBoundsException` from inside `add`.** `A` reassigns `elementData` at (4) while `B`'s
   call already captured the *old*, shorter array as its local parameter at (2) — parameters are copied at
   call time, so `B`'s (5) store runs past the end of that stale array.
4. **A silently truncated list after concurrent growth.** `A`/`B` read the same `oldCapacity`, both
   `Arrays.copyOf` it into two different new arrays, and whichever field assignment lands last wins
   outright — the loser's copy, and anything appended to it, is discarded with no exception.
5. **A corrupted `size` that outlives the writers.** Any interleaving of (6) leaving `size` inconsistent
   with what is stored persists with no exception at the moment of corruption — the worst case, because
   every later read is simply wrong with no signal.
6. **Stale reads with no mutation at all.** A pure reader can see an arbitrarily old `size`/`elementData`
   indefinitely, because neither field is `volatile`. Handing a built list to a worker with no
   `synchronized` block, `volatile` write, or safely-constructed `final` field gives it no
   `happens-before` edge to the writes that built it.

**A runnable demonstration — five consecutive real runs.**

```java
int threads = 4, perThread = 25_000;
List<String> shared = new ArrayList<>();
CountDownLatch ready = new CountDownLatch(threads);
CountDownLatch start = new CountDownLatch(1);
CountDownLatch done = new CountDownLatch(threads);
Map<String, Integer> exceptionTally = new ConcurrentHashMap<>();

for (int t = 0; t < threads; t++) {
    new Thread(() -> {
        ready.countDown();
        try { start.await(); } catch (InterruptedException e) { throw new RuntimeException(e); }
        for (int i = 0; i < perThread; i++) {
            try {
                shared.add("LedgerEntry-" + UUID.randomUUID());   // stands in for a settlement-burst append
            } catch (RuntimeException ex) {
                exceptionTally.merge(ex.getClass().getName(), 1, Integer::sum);
            }
        }
        done.countDown();
    }).start();
}
ready.await();
start.countDown();                 // release all four threads together
done.await();

long nulls = 0;
for (int i = 0; i < shared.size(); i++) if (shared.get(i) == null) nulls++;
System.out.println("expected size " + (threads * perThread) + ", actual size " + shared.size()
        + " (lost " + (threads * perThread - shared.size()) + "), nulls inside [0,size) = " + nulls
        + ", exceptions from add = " + (exceptionTally.isEmpty() ? "none" : exceptionTally));
```

Five consecutive runs of this program in one JVM, JDK 21.0.7 (Oracle, aarch64, macOS), `-Xmx1g`:

```
run 1: expected size 100000, actual size 30313 (lost 69687), nulls inside [0,size) = 832, exceptions from add = {java.lang.ArrayIndexOutOfBoundsException=2}
run 2: expected size 100000, actual size 29145 (lost 70855), nulls inside [0,size) = 298, exceptions from add = none
run 3: expected size 100000, actual size 32323 (lost 67677), nulls inside [0,size) = 2934, exceptions from add = none
run 4: expected size 100000, actual size 31708 (lost 68292), nulls inside [0,size) = 480, exceptions from add = {java.lang.ArrayIndexOutOfBoundsException=1}
run 5: expected size 100000, actual size 29065 (lost 70935), nulls inside [0,size) = 561, exceptions from add = none
```

Read the numbers mechanically, not as noise. Roughly **70% of the appends were lost** in every run — not a rare interleaving, the *normal* outcome under this much contention, which is the opposite of what "not thread-safe" leads people to expect. Nulls inside `[0, size)` appeared in **every** run and swung by an order of magnitude, 298 to 2,934 — a reader's `NullPointerException` is a live hazard here, not a theoretical one. And `ArrayIndexOutOfBoundsException` from inside `add` showed up in only **two of the five** runs — the loudest symptom is also the least reliable one, which is why the silent corruption in the other three runs is the dangerous part: nothing there told anyone a problem occurred. The outcome is still genuinely nondeterministic — a sixth run could land anywhere — and these five runs make that point rather than weaken it.

**Fixes, each with its cost.**

| Fix | Cost | When it is right |
|---|---|---|
| Confine + publish `List.copyOf(list)` | One copy, once | Cheapest, the right default |
| `Collections.synchronizedList(list)` | Every call pays the monitor; **iteration is still broken** unless you hold the wrapper's monitor for the whole traversal | Individual calls, no shared iteration |
| `CopyOnWriteArrayList` | O(n) copy per **write** | Read-mostly; catastrophic at 3,400/sec |
| Per-thread accumulator, merged at the end | One merge, once | Independent producers, known join point |
| `ConcurrentLinkedQueue` / `BlockingQueue` | Lock-free or blocking | A genuine producer–consumer |

`synchronizedList` deserves the plain statement it usually does not get: it makes each *individual call*
atomic, but safe iteration still requires holding the wrapper's own monitor for the whole loop — skipping
that is why people still get a CME. And **`ConcurrentModificationException` is not a thread-safety
mechanism**: file 08 already showed it is a best-effort *single-thread* detector that can miss even there.
Under genuine multi-threaded use a race may throw CME, may not, or may produce any of the six symptoms
above with no exception at all. Never catch it as a substitute for synchronization.

> **Definition.** Concurrent mutation of a shared `ArrayList` is not "undefined behaviour" in the abstract — it is a specific, derivable outcome of which unsynchronized field operation from `add`'s four-step body each thread happened to interleave with; every symptom above is a derivation, not a separate bug.

### The view that outlives its root

**Mental model.** `subList(from, to)` hands back a window with `offset` and `size` fields of its own,
pointed at the same backing array as the list it came from — not a copy, a coordinate system.

**Why it exists.** File 08's `## 12` walk: `SubList` is four ints and two references, every access
`root.elementData(offset + index)`. That makes `subList` O(1) and write-through to the root — the reason
`list.subList(from, to).clear()` is a documented idiom for deleting a range.

**When it applies, and when it does not.** Right for a short-lived local window — trim, sort, or clear a
range in the same method, then let it go out of scope. Wrong the moment it crosses a method boundary while
the root keeps mutating independently, because nothing in the view's type signature (`List<E>`) says
"coordinate window" rather than "owned collection."

**How it works.** A structural change made *through the root* leaves the view in a state the Javadoc calls
**undefined** — not "throws". In practice, on JDK 21.0.7, it throws CME on the view's next access, because
the root's `modCount` moved past what `checkForComodification` cached at construction. But "undefined" is
not a contract — an alternate implementation could do anything else, including returning a wrong answer
silently, so depending on the CME specifically is depending on an accident.

```java
// Wrong — the view is handed to a caller who does not know it is a window.
public List<LedgerEntry> recentEntries(List<LedgerEntry> allEntries, int page) {
    int from = page * 50, to = Math.min(from + 50, allEntries.size());
    return allEntries.subList(from, to);          // still backed by allEntries
}
// Elsewhere: var p = repo.recentEntries(allEntries, 3);
// allEntries.add(newlyPostedEntry);              // root mutated
// p.get(0);                                      // ConcurrentModificationException

// Right — detach at the boundary.
public List<LedgerEntry> recentEntries(List<LedgerEntry> allEntries, int page) {
    int from = page * 50, to = Math.min(from + 50, allEntries.size());
    return List.copyOf(allEntries.subList(from, to));
}
```

**The gotcha.** The symptom looks like a bug in whatever code touches the root afterward, because the
exception is thrown from the *view*, at a call site with no textual connection to the mutation that caused
it. **Pitfall:** `Collections.unmodifiableList(list.subList(a, b))` fixes the wrong problem — the view is
still write-through *from* the root and still throws CME the moment the root changes. Only detaching with
a copy removes the coupling.

> **Definition.** `subList` returns a live coordinate window into its root, not an independent list, and a structural change to the root while a caller outside the creating method still holds that window is behaviour the Javadoc explicitly declines to define.

## Pitfalls

### `Arrays.asList(...)` is a fixed-size adapter, not a mutable list

**Wrong**
```java
List<InstrumentId> instrumentIds = Arrays.asList(rawIds);   // Arrays$ArrayList
instrumentIds.add(newInstrumentId);   // -> UnsupportedOperationException
```

**Right**
```java
List<InstrumentId> instrumentIds = new ArrayList<>(Arrays.asList(rawIds));
instrumentIds.add(newInstrumentId);   // works, does not write through to rawIds
```

**Why people believe it:** the parameter type is `List<T>`, and `Arrays.asList` supports `get`, `set`, and
iteration fine in any read-only test — `set` even writes through to the original array — so the mutating
gap surfaces only on the one `add`/`remove` path a small fixture never exercises.

### `remove(0)` in a loop, or `removeAll` against a `List`

**Wrong**
```java
while (!pendingWithdrawals.isEmpty()) {
    process(pendingWithdrawals.remove(0));            // O(n) shift, every call
}
staleReservations.removeAll(closedReservationIds);    // a List argument: O(n·m)
```

**Right**
```java
Deque<WithdrawalTransaction> pending = new ArrayDeque<>(pendingWithdrawals);
while (!pending.isEmpty()) process(pending.pollFirst());   // amortised O(1)
staleReservations.removeAll(new HashSet<>(closedReservationIds));   // O(n)
```

**Why people believe it:** both compile against a `List` argument, both pass a 40-record test in well
under a millisecond, and nothing in the code signals that `batchRemove`'s `c.contains(es[r])` (file 08,
`## 8`) is an O(m) linear scan per element of the receiver.

### Mutating a list while a `forEach` or stream operation runs over it

**Wrong**
```java
completedRuns.forEach(run -> {
    if (run.isStale()) completedRuns.remove(run);   // structural change mid-forEach
});
```

**Right**
```java
List<PaymentRun> stale = completedRuns.stream().filter(PaymentRun::isStale).toList();
completedRuns.removeAll(stale);
```

**Why people believe it:** `Itr.forEachRemaining`'s `modCount` check fires only at the very end, so a
mid-loop mutation sometimes finishes on a torn view and sometimes throws, depending on where the mutation
landed — neither outcome shows up reliably under a small, fast test.

### Trusting `equals`/`hashCode` never to throw

**Wrong**
```java
Map<List<InstrumentId>, ReconciliationBatch> batches = new HashMap<>();
batches.put(instrumentIdList, batch);   // instrumentIdList still mutable
// later, on a resize or a get(): -> ConcurrentModificationException from hashCode()
```

**Right**
```java
Map<List<InstrumentId>, ReconciliationBatch> batches = new HashMap<>();
batches.put(List.copyOf(instrumentIdList), batch);
```

**Why people believe it:** `equals`/`hashCode` read as pure queries, so nobody expects either to throw.
File 08's `## 7` walk shows both snapshot `modCount` and check it after — a CME from inside `hashCode()` is
disorienting precisely because the calling code, often a `HashMap` internal, never touched the list.

## Cheat sheet

| Misuse | One-line symptom | One-line fix |
|---|---|---|
| Buffer whole input | `OutOfMemoryError`, slows before dying | Bounded batches |
| `clear()`, keep the field | Heap dump: empty `size()`, large `Object[]` | `trimToSize()` or replace |
| Concurrent `add` — lost element | `size()` short | Confine + `List.copyOf`, or a concurrent queue |
| Concurrent `add` — null read | NPE inside `[0, size)` | Same |
| Concurrent `add` during `grow` | AIOOBE, or silent truncation | Same |
| `Arrays.asList` mutated | `UnsupportedOperationException` on `add`/`remove` | Wrap in `new ArrayList<>(...)` |
| `subList` escapes its method | CME with no visible mutation nearby | `List.copyOf(view)` at the boundary |
| `remove(0)` loop / `removeAll(List)` | Quadratic runtime at scale | `ArrayDeque`; `HashSet` argument |
| Mutate during `forEach`/stream | Intermittent CME under load only | Collect, then mutate |
| Mutable list as/against a map key | CME thrown from `hashCode()` | `List.copyOf` before use as a key |
| CME caught and ignored | Corruption continues silently | Never catch it; fix the sharing |

## Self-test

**Q1.** Two threads call `add(E)` on one shared `ArrayList` and neither throws any exception. What is the
strongest guarantee you have about `size()`?

<details><summary>Answer</summary>

None beyond "some integer no greater than the sum of both calls." `add` has no synchronization, so a
lost-element interleaving — both threads read the same `size`, both store, both increment — produces a
short `size()` with no exception anywhere. The absence of a CME proves nothing; that check is
single-thread-oriented and best-effort even there.

</details>

**Q2.** Why does a trailing `null` from concurrent `add` calls turn up inside `[0, size)` rather than past
the end of the list?

<details><summary>Answer</summary>

Because step (6), `size = s + 1`, can complete on one thread before the other thread's step (5) store has
run. `size` bounds iteration, so the instant it increments, index `s` is "inside" the list for every
reader even though nothing has been written there yet.

</details>

**Q3.** Why does `Collections.synchronizedList(list)` not make concurrent iteration safe by itself?

<details><summary>Answer</summary>

It synchronizes each individual method call on one monitor, but the iterator it returns is not
synchronized and is still fail-fast. Safe iteration requires the caller to hold the wrapper's own monitor
for the *entire* traversal: `synchronized (list) { for (var e : list) ... }`. Without that block, a
mid-iteration `add`/`remove` on another thread still races the iterator.

</details>

**Q4.** A `PaymentRunCoordinator` reuses one `ArrayList<PaymentItemId>` field via `addAll` then `clear()`
between runs. After one huge month-end run and many ordinary runs since, a heap dump shows `size() == 0`
but a large backing array still live. What leaked, and why didn't `clear()` catch it?

<details><summary>Answer</summary>

Capacity, not an unreachable object. `clear()` nulls every slot and sets `size` to 0 but never reassigns
`elementData`, so the array stays sized to the largest run ever seen. `trimToSize()` after `clear()`, or
replacing the field with a fresh list, would have caught it.

</details>

**Q5.** Why is "undefined behaviour," not "throws `ConcurrentModificationException`," the correct
description of mutating an `ArrayList` through its root while a `subList` view is held elsewhere?

<details><summary>Answer</summary>

The CME is what the *current* JDK 21.0.7 implementation happens to do — `SubList.checkForComodification`
compares its cached `modCount` to the root's live one — not a documented contract. The Javadoc's own word
is "undefined." Depending on the CME specifically is depending on an implementation accident.

</details>

---

**Questions answered:** Q-34, Q-35
**Sets up:** Next: which of the things you now know were different in earlier JDKs, and which stale claims interviewers still ask for.
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 447
