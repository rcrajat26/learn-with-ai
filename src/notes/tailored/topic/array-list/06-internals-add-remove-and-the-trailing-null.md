# `ArrayList` — 06 Internals: add, remove and the trailing null

**Target version: Java 21 LTS.** | [Map](00-map.md)
Assumes: the field set, the sentinels, and how grow computes capacity (file 05).
Previous: [05 Internals — fields, sentinels and growth](05-internals-fields-sentinels-and-growth.md) · Next: [07 Internals — bulk removal and exception safety](07-internals-bulk-removal-and-exception-safety.md)

File 05 walked `elementData`, the two identity sentinels, and `grow(minCapacity)`
delegating to `ArraysSupport.newLength` with its 1.5× preferred growth. This
file does not re-derive that arithmetic — it walks `add(E)`, `add(int, E)`,
`remove(int)`, and `remove(Object)` statement by statement, so "what does
`add` cost" stops being a guess. Examples use the QuizStakes ledger's
`List<LedgerEntry>` per `Movement` and a `Client`'s `List<Restriction>` (§9,
§11) — both `ArrayList` in the reference implementation.

## Primary concept: `add(E)` and the `MaxInlineSize` helper split

**Mental model, and why it exists.** `add(E)` looks like a one-liner. It is
actually two methods, split because `add(E)` sits on the hottest possible path
— a loop calling `list.add(x)` millions of times — and C1, the JIT's fast
tier, only inlines a call site if the callee's bytecode is small enough. The
method is split so the public entry point stays tiny and inlinable while the
heavier grow-capable logic lives off that path:

```java
/**
 * This helper method split out from add(E) to keep method
 * bytecode size under 35 (the -XX:MaxInlineSize default value),
 * which helps when add(E) is called in a C1-compiled loop.
 */
private void add(E e, Object[] elementData, int s) {
    if (s == elementData.length)
        elementData = grow();
    elementData[s] = e;
    size = s + 1;
}

public boolean add(E e) {
    modCount++;
    add(e, elementData, size);
    return true;
}
```

`MaxInlineSize` and `C1MaxInlineSize`, read from `-XX:+PrintFlagsFinal` on this
JDK 21.0.7 build, are both **35** bytes of bytecode. `add(E)` — increment, one
delegating call, `return true` — is trivially under that, so C1 inlines the
outer call; `grow()` stays cold in the uninlined helper.

**When it applies, and when it does not.** The split only pays off for the
common, no-resize path — traced, `list.add(entry)` at `size == 3`, capacity 10
runs `modCount++`, calls the helper with `s = 3`, finds `3 == 10` false (no
grow), stores `elementData[3] = e`, sets `size = 4`. `add(int, E)` below has no
analogous split — it already needs the arraycopy and bounds check inline, so
there is no cheap sub-path to carve out.

**Demonstration.**

```java
List<Restriction> restrictions = new ArrayList<>();
restrictions.add(new Restriction("STAKE_BLOCKED", "SYSTEM_ONBOARDING", Instant.now(), null, false));
restrictions.add(new Restriction("WITHDRAWAL_BLOCKED", "SYSTEM_ONBOARDING", Instant.now(), null, false));
System.out.println(restrictions.size()); // 2
```

**The gotcha, and the insight.** `add(int, E)` with `index == size` also
appends, but slower — a bounds check plus a zero-length `arraycopy` — so never
write `add(list.size(), e)` where `add(e)` will do. The split itself is a
JIT-inlining decision, named with a real JVM flag and default in the comment.

> **`add(E)` appends via a tiny, C1-inlinable helper that does one comparison,
> one array store, and one increment; `grow()` runs only on the helper's cold
> branch.**

## Primary concept: `add(int, E)` as one `System.arraycopy`

**Mental model, and why it exists.** Insert at a position: make a hole, drop
the element in. `List` promises positional insertion, not just append, and an
array cannot insert mid-sequence without moving something, so `ArrayList` pays
that cost explicitly: the entire "make a hole" step is one `System.arraycopy`
moving everything from `index` onward one slot right, into the *same* array,
overlapping itself. Right for a genuine one-off insertion near the tail; wrong
inside a loop inserting at a fixed low index — see `addFirst` below.

```java
public void add(int index, E element) {
    rangeCheckForAdd(index);
    modCount++;
    final int s;
    Object[] elementData;
    if ((s = size) == (elementData = this.elementData).length)
        elementData = grow();
    System.arraycopy(elementData, index, elementData, index + 1, s - index);
    elementData[index] = element;
    size = s + 1;
}
```

`rangeCheckForAdd` runs before `modCount++`, so a rejected call claims no
structural change. Then the same grow-if-full check as `add(E)`'s helper. Then
the mechanism: `System.arraycopy(elementData, index, elementData, index + 1, s
- index)` — source `[index, s)`, destination `[index + 1, s + 1)`, same array,
overlapping whenever `index < s`. `System.arraycopy` is a JVM intrinsic
engineered to get overlapping same-array copies right — as if copied through a
temporary buffer — compiling to a tuned bulk move, not a Java loop. Cost:
`O(size - index)`, always — `index == 0` shifts the whole array; `index ==
size` (append via this overload) shifts nothing.

![One `arraycopy` moves the whole tail. Inserting at 0 moves everything; inserting at `size` moves nothing.](diagrams/D-07-add-at-index-arraycopy.svg)

**Demonstration.** Invariant 7 (§11.7) requires `LedgerEntry` rows to be
**append-only** — a correction is a new compensating entry, never an insertion
ahead of existing ones. `add(0, e)` would compile and run but violate that
invariant; the append is the only correct call, and also the cheap one:

```java
List<LedgerEntry> entries = new ArrayList<>();
entries.add(new LedgerEntry("PSP_RECEIVABLE", 1000, Instant.now()));
entries.add(new LedgerEntry("CASH_AVAILABLE", 1000, Instant.now()));
// WRONG, violates invariant 7: entries.add(0, new LedgerEntry("CASH_AVAILABLE", -1000, Instant.now()));
// RIGHT — a new compensating entry, appended after everything before it:
entries.add(new LedgerEntry("CASH_AVAILABLE", -1000, Instant.now()));
entries.add(new LedgerEntry("PSP_RECEIVABLE", -1000, Instant.now()));
System.out.println(entries.size()); // 4
```

**The gotcha:** `addFirst(E)`, below, looks purpose-built for cheap head
insertion because it has its own name — it is not, it is this method at `index == 0`.

> **`add(int, E)` is one `System.arraycopy` widening a gap at `index` by
> shifting everything from `index` to `size` one slot right, in place; the
> intrinsic makes the overlapping move correct, not the cost cheap.**

## Supporting fact: `addFirst(E)` — vocabulary, not a fast path

`public void addFirst(E element) { add(0, element); }` — the whole method.
**Pitfall:** the Java 21 `SequencedCollection` retrofit (JEP 431) gave
`ArrayList` a `Deque`-shaped vocabulary — `addFirst`/`addLast`/`getFirst`/
`getLast`/`removeFirst`/`removeLast` — inviting the assumption of shared
performance with `LinkedList`/`ArrayDeque`. `addFirst` compiles to the full
`O(size)` shift above, every call — measured at **314 ms** for 100 000 calls,
against **< 1 ms** for `add(e)` and **< 1 ms** for `LinkedList.add(0, e)`,
whose head insertion really is O(1).

> **`addFirst(E)` is `add(0, element)` — the retrofit added the name, not the algorithm.**

## Primary concept: `remove(int)`, `fastRemove`, and the trailing null

**Mental model, and why it exists.** Arrays have no "delete a slot," so removal
is the mirror of insertion: shift the tail left to close the hole, keeping the
list dense so `get(i)` stays a plain index — then explicitly erase the now-stale
duplicate left sitting past the new end.

```java
public E remove(int index) {
    Objects.checkIndex(index, size);
    final Object[] es = elementData;
    @SuppressWarnings("unchecked") E oldValue = (E) es[index];
    fastRemove(es, index);
    return oldValue;
}

private void fastRemove(Object[] es, int i) {
    modCount++;
    final int newSize;
    if ((newSize = size - 1) > i)
        System.arraycopy(es, i + 1, es, i, newSize - i);
    es[size = newSize] = null;
}
```

`remove(int)` bounds-checks, captures the old value, and delegates to
`fastRemove`, which skips the re-check (hence "fast"). Inside: `newSize = size
- 1`; if `newSize > i` — something follows the removed slot —
`System.arraycopy(es, i + 1, es, i, newSize - i)` shifts it left by one, the
same overlapping pattern as `add(int, E)`, reversed.

The statement that matters most here is `es[size = newSize] = null`, read
right to left: `size = newSize` assigns the smaller size, and that
assignment's *value* (`newSize`) indexes the array write that follows — one
statement, two jobs, publishing the new size and nulling the slot now past the
logical end but still holding the old last element.

**Why the null matters, as a cost.** Without it, that slot still holds a live
reference; `size` no longer counts it, but the GC only sees a reachable array
with a reachable reference inside — the object stays alive, unreachable to
your program but not the collector, for as long as the array survives: a
one-object leak per `remove` call on a long-lived list.

![The shift closes the gap; the explicit null is what lets the removed `LedgerEntry` be collected. Capacity is unchanged.](diagrams/D-08-fastremove-trailing-null.svg)

**Demonstration.** Lifting a `Restriction` by position (§9.2, `ACTIVE →
LIFTED`):

```java
List<Restriction> active = new ArrayList<>(List.of(
        new Restriction("DEPOSIT_BLOCKED", "SYSTEM_ONBOARDING", Instant.now(), null, false),
        new Restriction("STAKE_BLOCKED", "SYSTEM_ONBOARDING", Instant.now(), null, false)));
Restriction lifted = active.remove(0); // shifts STAKE_BLOCKED down to index 0
System.out.println(active.size() + " " + lifted.type()); // 1 DEPOSIT_BLOCKED
```

**Cost, with its cause.** `O(size - index)`, symmetric with `add(int, E)`:
index 0 shifts everything; index `size - 1` shifts nothing, degenerating to a
single null-store — `removeLast()` (Java 21) takes exactly that fast path, the
same head/tail asymmetry as `addFirst`.

**Insight:** `clear()`'s loop nulls every slot but never reassigns
`elementData` — **capacity is fully retained after `clear()`**; `trimToSize()`
(file 05) is the only way to give that memory back.

> **`fastRemove` closes the gap with one reversed `arraycopy`, then `es[size =
> newSize] = null` publishes the smaller size and erases the stale reference in
> one statement — without the erasure, the removed object stays reachable to
> the GC for as long as the array does.**

## Primary concept: `remove(Object)` and the labelled-break scan

**Mental model.** `remove(int)` already knows where to cut; `remove(Object)`
must find where first — a linear scan — then cuts in the same place with the
same `fastRemove`.

**Why it exists, and when it applies.** Callers often want "remove this
value" — a specific lifted `Restriction` instance — not "remove whatever sits
at this position." `ArrayList` must scan because nothing is indexed by value.
Use `remove(int)` if the index is already known; use `removeIf` (file 07) to
remove several matches without re-scanning per call.

```java
public boolean remove(Object o) {
    final Object[] es = elementData;
    final int size = this.size;
    int i = 0;
    found: {
        if (o == null) {
            for (; i < size; i++)
                if (es[i] == null)
                    break found;
        } else {
            for (; i < size; i++)
                if (o.equals(es[i]))
                    break found;
        }
        return false;
    }
    fastRemove(es, i);
    return true;
}
```

`found:` names a block, not a loop; `break found` jumps to `fastRemove(es, i)`
below it, with `i` already the matched index — one call shared by both search
branches. No match falls through to `return false`: `fastRemove` never runs,
`modCount` never bumps, a failed `remove` is a deliberate no-op.

**Insight:** the non-null branch calls `o.equals(es[i])` — the **argument's**
`equals` decides, not the stored element's. Unobservable for a symmetric
`equals`; it matters the moment some type's `equals` is asymmetric.

**Demonstration.**

```java
List<Restriction> active = new ArrayList<>();
Restriction coolingOff = new Restriction(
        "COOLING_OFF", "CLIENT", Instant.now(), Instant.now().plus(Duration.ofDays(7)), false);
active.add(new Restriction("STAKE_BLOCKED", "ADMIN", Instant.now(), null, true));
active.add(coolingOff);
System.out.println(active.remove(coolingOff)); // true — scans, matches at 1, fastRemove(es, 1)
System.out.println(active.remove(coolingOff)); // false — scan completes, no match, no state change
```

**Cost, with its cause.** Worst case `O(size)` scan plus `O(size - i)` shift on
a hit. Even a hit at index 0 is `O(size)` overall — unlike its cousins above,
`remove(Object)` has no cheap case.

> **`remove(Object)` linear-scans for the first element equal to the argument
> under `o.equals(es[i])`, sharing one `fastRemove` call between the
> null-search and equals-search branches via a labelled `break found`; it
> removes at most one match and is a silent no-op otherwise.**

## Supporting fact: `get`/`set` and the two exception shapes

`get`/`set` cost one `Objects.checkIndex` bounds check plus one array access
each — intrinsified since JDK 9, often eliminated by the JIT in a counted
loop. Measured: a 200 000-element scan by `get(i)` is **101 µs**. `set` does
**not** bump `modCount` — a value change, not a shape change — unlike every
other mutator here; file 08 covers the iterator consequence.

Two different `IndexOutOfBoundsException` shapes come out of this class,
measured:

```
new ArrayList<>(List.of("A")).get(3)
  -> java.lang.IndexOutOfBoundsException: Index 3 out of bounds for length 1

new ArrayList<>(List.of("A")).add(3, "x")
  -> java.lang.IndexOutOfBoundsException: Index: 3, Size: 1
```

The first is `Objects.checkIndex(index, size)` (`get`/`set`/`remove(int)`),
rejecting `index == size`. The second is `ArrayList`'s own private pair —
`rangeCheckForAdd(int index) { if (index > size || index < 0) throw ... }`,
message `"Index: "+index+", Size: "+size`. `add(int, E)` must **accept**
`index == size` to support append-by-position, so its check is deliberately
one comparison wider, and cannot share `checkIndex`.

**Interview:** why two message shapes from one class? `get` family rejects
`index == size`; `add(int, E)` must accept it to support append-by-position, so
it carries its own wider `rangeCheckForAdd`.

## Pitfalls

### "A failed `remove(Object)` call must throw or signal something"

**Wrong**
```java
active.remove(new Restriction("COOLING_OFF", "CLIENT", Instant.now(), null, false));
// no exception — but did it work? Silently returns false, list unchanged.
```

**Right**
```java
if (!active.remove(coolingOffInstance)) {
    // handle "nothing matched" explicitly
}
```

**Why people believe it:** `remove(int)` throws for an invalid position, so it
is natural to expect the same from `remove(Object)`. But every object is a
legal argument — there is no "invalid value" — so the contract is a boolean.

## Cheat sheet

| Method | Bounds check | Shift | Cost | `modCount`? |
|---|---|---|---|---|
| `get(int)` | `Objects.checkIndex`, rejects `index==size` | none | O(1) | no |
| `set(int, E)` | `Objects.checkIndex` | none | O(1) | **no** |
| `add(E)` | none | none | O(1) amortized, C1-inlinable | yes |
| `add(int, E)` | `rangeCheckForAdd`, accepts `index==size` | right, one `arraycopy` | O(size − index) | yes |
| `addFirst(E)` | delegates to `add(0, e)` | right, full array | O(size) — not O(1) | yes |
| `remove(int)` | `Objects.checkIndex` | left, `arraycopy` in `fastRemove` | O(size − index) | yes |
| `remove(Object)` | none — scans instead | left, via `fastRemove` on hit | O(size) worst case | yes, only on a hit |
| `clear()` | none | none — nulls in place | O(size) | yes |

## Self-test

**Q1.** Why does `add(E)` split into a public one-liner and a private
three-argument helper, and what is the measured cost gap between `add(0, e)`
and plain `add(e)`?

<details><summary>Answer</summary>

The split keeps public `add(E)` under C1's inlining budget — bytecode size
under 35, `-XX:MaxInlineSize`'s measured default — so it stays inlinable in
hot loops while the grow-capable logic sits off that path. Separately,
`add(0, e)` costs 314 ms for 100 000 calls versus under 1 ms for `add(e)`,
because it runs a full `arraycopy` shifting every element right each call.

</details>

**Q2.** What two jobs does `es[size = newSize] = null` do in `fastRemove`, and
what breaks without the `= null`?

<details><summary>Answer</summary>

It assigns the smaller `size` (the expression evaluates to `newSize`) and uses
that value to index the null-write on the now-stale trailing slot. Without the
null, that slot still holds a live reference; the array is still reachable, so
the removed object cannot be collected until the array itself is replaced — a
per-`remove` memory leak.

</details>

**Q3.** Why does `remove(Object)` use a labelled `break found` instead of two
ordinary loops each calling `fastRemove` directly, and whose `equals` decides
the match?

<details><summary>Answer</summary>

To share one `fastRemove(es, i)` call and one `return true` between the
null-search and `equals`-search branches instead of duplicating it at the end
of each. The match is decided by `o.equals(es[i])` — the argument's `equals`,
not the stored element's — unobservable for symmetric `equals`, but it matters
if some type's `equals` is asymmetric.

</details>

**Q4.** Why do `get(3)` and `add(3, "x")` on a one-element list throw
differently worded exceptions?

<details><summary>Answer</summary>

`get` uses `Objects.checkIndex(index, size)`, rejecting `index == size`.
`add(int, E)` uses its own `rangeCheckForAdd` (`index > size || index < 0`) —
one comparison wider, because `add` must accept `index == size` to support
appending by position — building its own message via `outOfBoundsMsg`.

</details>

**Q5.** Does `set(int, E)` invalidate a live iterator, and does `clear()`
shrink the backing array?

<details><summary>Answer</summary>

Neither. `set` never increments `modCount` because it changes a value, not the
shape — every other mutator here bumps `modCount` once per call. `clear()`
only nulls each slot for GC purposes and never reassigns `elementData`;
`trimToSize()` is the only method that shrinks the array.

</details>

**Q6.** Why is inserting a correcting `LedgerEntry` at index 0 wrong for the
QuizStakes ledger, independent of cost?

<details><summary>Answer</summary>

Ledger invariant 7 (§11.7) requires append-only entries — a correction is a new
compensating movement, never an insertion ahead of existing entries. `add(0,
entry)` would compile and run but rewrite history rather than append a
compensating entry; the only correct call is `add(entry)`, which is also the
cheap one.

</details>

---

**Questions answered:** Q-19, Q-20
**Sets up:** Next: what happens when you remove many elements at once, and the bitset the JDK reaches for.
**Diagrams included:** D-07, D-08
**Target version:** Java 21 LTS
**Lines:** 430
