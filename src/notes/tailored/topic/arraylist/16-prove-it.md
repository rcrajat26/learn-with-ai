# ArrayList — 16 Prove It

**Target version: Java 21.** | [Map](00-map.md)
Assumes: everything from files 05 through 08 — the fields, growth, the mutation operations, and fail-fast.
Previous: [15-interop-streams-and-concurrency.md](15-interop-streams-and-concurrency.md) · Next: [17-interview.md](17-interview.md)

Files 05–08 stated claims as fact. This file re-derives four of them by
writing code, compiling and running it on JDK 21.0.7, and pasting the output
that actually came back — not a plausible reconstruction of it.

### Exercise 1 — build the list from scratch

**Mental model, and why it exists as an exercise.** `ArrayList` is one
`Object[]`, a live-count, and a policy for replacing the array when it runs
out of room. File 06's `grow()` walk tells you *that* growth is
`oldCapacity + (oldCapacity >> 1)` clamped at `Integer.MAX_VALUE - 8`, not that
you understood *why* the two empty-array sentinels exist. Writing
`LedgerEntryList<E>` — a minimal list holding `LedgerEntry` records, presized
to 4 because a `Movement` has 2 to 4 entries — and watching it reproduce the
real numbers is the proof.

**The mechanism, at source level.** The two constructors that matter:

```java
public LedgerEntryList() {
    this.elementData = DEFAULTCAPACITY_EMPTY_ELEMENTDATA;
}

public LedgerEntryList(int initialCapacity) {
    if (initialCapacity > 0) {
        this.elementData = new Object[initialCapacity];
    } else if (initialCapacity == 0) {
        this.elementData = EMPTY_ELEMENTDATA;
    } else {
        throw new IllegalArgumentException("Illegal Capacity: " + initialCapacity);
    }
}
```

`DEFAULTCAPACITY_EMPTY_ELEMENTDATA` and `EMPTY_ELEMENTDATA` are both `{}` — same
value, same length, deliberately kept as **two separate objects** so `grow` can
tell them apart by reference (`==`), not by content:

```java
private Object[] grow(int minCapacity) {
    int oldCapacity = elementData.length;
    if (oldCapacity > 0 || elementData != DEFAULTCAPACITY_EMPTY_ELEMENTDATA) {
        int newCapacity = newLength(oldCapacity,
                minCapacity - oldCapacity,   // minimum growth
                oldCapacity >> 1);           // preferred growth
        return elementData = Arrays.copyOf(elementData, newCapacity);
    } else {
        return elementData = new Object[Math.max(DEFAULT_CAPACITY, minCapacity)];
    }
}

private static int newLength(int oldLength, int minGrowth, int prefGrowth) {
    int prefLength = oldLength + Math.max(minGrowth, prefGrowth);
    if (0 < prefLength && prefLength <= SOFT_MAX_ARRAY_LENGTH) {
        return prefLength;
    }
    return hugeLength(oldLength, minGrowth);
}

private static int hugeLength(int oldLength, int minGrowth) {
    int minLength = oldLength + minGrowth;
    if (minLength < 0) {
        throw new OutOfMemoryError(
                "Required array length " + oldLength + " + " + minGrowth + " is too large");
    }
    return (minLength <= SOFT_MAX_ARRAY_LENGTH) ? SOFT_MAX_ARRAY_LENGTH : minLength;
}
```

`add` and removal reuse the real shape exactly — the vacated-slot nulling is not
cosmetic:

```java
private void fastRemove(Object[] es, int i) {
    modCount++;
    final int newSize;
    if ((newSize = size - 1) > i) {
        System.arraycopy(es, i + 1, es, i, newSize - i);
    }
    // vacate the slot so the removed element is not held alive by the dead
    // tail of the backing array — a shrinking list otherwise leaks whatever
    // it used to hold, invisible to any test that checks size().
    es[size = newSize] = null;
}
```

The rest — `get`/`set` via `Objects.checkIndex`, `add(int,E)` with
`rangeCheckForAdd`, `remove(Object)`, `clear`, `toString` — follows the same
source directly and adds nothing new to watch; the full compiled file is 230
lines.

**The demonstration.** One program adds 400 elements to a `LedgerEntryList<Integer>`
and a real `ArrayList<Integer>` in lockstep, reading the real one's
`elementData` by reflection. Run with
`java --add-opens java.base/java.util=ALL-UNNAMED GrowthDemo`, the real output:

```
LedgerEntryList capacity sequence: 10 15 22 33 49 73 109 163 244 366 549
real ArrayList  capacity sequence: 10 15 22 33 49 73 109 163 244 366 549
match: true
```

**Gotcha.** `Math.max(minGrowth, prefGrowth)` means the *minimum* growth wins
whenever it exceeds 1.5x — a single `addAll` of 1,000 onto a capacity-10 list
grows straight to 1,010, not 15. `add(E)` never exercises this since
`minGrowth` is always 1 there; only bulk operations reach it.

> **Definition:** a hand-written list that matches `ArrayList`'s field layout,
> constructors, and `grow` logic reproduces its exact capacity sequence, which
> means the sequence is a property of the *algorithm*, not of anything hidden
> inside the JDK.

### Exercise 2 — the fail-fast iterator, and its blind spot

**Mental model, and why it exists.** The iterator is not watching the list for
damage; it is counting laps and comparing a stamp. `hasNext()` answers "have I
returned `size` elements yet", nothing more — the JDK chose the cheapest
possible stopping condition and paid for that cheapness with the blind spot
this exercise reproduces.

**The mechanism.** `LedgerEntryList`'s inner `Itr`, copied field-for-field from
the real one:

```java
private class Itr implements Iterator<E> {
    int cursor;
    int lastRet = -1;
    int expectedModCount = modCount;

    public boolean hasNext() {
        return cursor != size;
    }

    public E next() {
        checkForComodification();
        int i = cursor;
        if (i >= size) throw new NoSuchElementException();
        Object[] elementData = LedgerEntryList.this.elementData;
        if (i >= elementData.length) throw new ConcurrentModificationException();
        cursor = i + 1;
        return (E) elementData[lastRet = i];
    }

    final void checkForComodification() {
        if (modCount != expectedModCount) throw new ConcurrentModificationException();
    }
}
```

Note what `hasNext()` does **not** do: call `checkForComodification()`. That
single omission is the whole mechanism below.

**The demonstration.** Two for-each loops over `["AO-100", "AO-400", "AA-700"]`,
removing by value mid-iteration. Compiled and run directly:

```
--- Case A: remove the LAST element during a for-each ---
visiting AO-100
visiting AO-400
visiting AA-700
threw java.util.ConcurrentModificationException
surviving list: [AO-100, AO-400]

--- Case B: remove the SECOND-TO-LAST element during a for-each ---
visiting AO-100
visiting AO-400
no exception thrown
surviving list: [AO-100, AA-700]
```

Case B is the payoff. After removing `"AO-400"` at index 1, `size` drops to 2
and `cursor` is already 2 (it was incremented when `"AO-400"` was returned).
`hasNext()` evaluates `2 != 2`, gets `false`, and the loop ends — `next()` is
never called again, so `checkForComodification()` never runs, so no exception
fires, and `"AA-700"` is silently never visited.

**Gotcha.** Writing `hasNext()` as `cursor < size` "fixes" nothing observable,
since `cursor` never exceeds `size` here — the comparison was never the guard
against comodification. The JDK keeps `!=` as the narrowest possible "have I
finished" check; this iterator was never designed to catch every mutation,
only ones that change `modCount` between two `next()` calls.

> **Definition:** fail-fast iteration detects structural modification only at
> the moments it calls `next()`, so a mutation that also changes what "the end"
> means can retire the loop before that detection ever runs.

### Exercise 3 — the capacity probe

**Mental model, and why it exists.** `ArrayList` has no public way to ask "how
much room do you have" — `size()` answers a different question. The only way
to see capacity from outside is to read the private `elementData` field
directly; every capacity number quoted in files 05–07 was produced this way,
and this exercise is that tool, in full, so the reader can run it rather than
trust it.

**The mechanism.**

```java
static int realCapacity(ArrayList<?> list) throws Exception {
    Field f = ArrayList.class.getDeclaredField("elementData");
    f.setAccessible(true);
    return ((Object[]) f.get(list)).length;
}
```

`setAccessible(true)` on a `java.base` field needs the module opened at launch,
which is why the command line is not just `java CapacityProbe`.

**The demonstration.** Compiled with `javac CapacityProbe.java`, run with:

```
java --add-opens java.base/java.util=ALL-UNNAMED CapacityProbe
```

Real output:

```
new ArrayList<>() capacity right after construction: 0
new ArrayList<>() capacity after one add: 10
new ArrayList<>(0) capacity after one add: 1
new ArrayList<>(4) capacity after five adds: 6
default-constructed capacity at size 100: 109
capacity after trimToSize(): 100
capacity after clear(): 100
```

Every one of these matches the claims made in files 05–07 exactly, including
the `clear()` row: capacity does not shrink when elements are nulled out.

**Gotcha.** `--add-opens` only works because this is a throwaway diagnostic
running as a single unnamed-module command. In a real modular build, opening
`java.base/java.util` to `ALL-UNNAMED` is a maintenance liability every team
member and CI job must repeat — exactly the reflective access the module
system was built to make visible and deliberate rather than free.

> **Definition:** the reflection probe is a diagnostic for reading a private
> field during development, not a technique to use in production code — the
> module system's `--add-opens` requirement is the language telling you that.

### Exercise 4 — measuring the presizing win

**Mental model, and why it exists.** File 06 states that presizing avoids
grows and their copies — a cost the CPU actually pays, so it should be
measured, not just asserted. Two sizes drawn from the domain: 1,800 (a bank
payout file, batched 4 times a day) and 40,000 (an ordinary daily bank
statement file, which can spike to 500,000 at month end).

**The mechanism.** `LedgerEntryList` exposes `capacity()` for exactly this; the
benchmark controls its own code, so it counts a grow the honest way — comparing
capacity before and after each `add` — rather than inferring it from timing:

```java
static Result run(int n, int presize) {
    LedgerEntryList<LedgerEntry> list =
            presize > 0 ? new LedgerEntryList<>(presize) : new LedgerEntryList<>();
    int grows = 0;
    long copies = 0;
    long start = System.nanoTime();
    for (int i = 0; i < n; i++) {
        int capBefore = list.capacity();
        list.add(new LedgerEntry("E" + i, "M" + (i / 3),
                (i % 2 == 0) ? LedgerEntry.Direction.DEBIT : LedgerEntry.Direction.CREDIT,
                new LedgerEntry.Money(1000 + i, "GBP"), Instant.EPOCH));
        int capAfter = list.capacity();
        if (capAfter != capBefore) {
            grows++;
            copies += capBefore;   // a grow copies every element that existed before this add
        }
    }
    return new Result(grows, copies, System.nanoTime() - start);
}
```

**The demonstration.** Compiled with `javac PresizeBenchmark.java`, run with
`java PresizeBenchmark`. Real output:

```
N = 1800
  without presizing: grows=14 copies=3690 time=28.222667 ms
  with presizing:    grows=0 copies=0 time=0.625708 ms
N = 40000
  without presizing: grows=22 copies=94846 time=8.900291 ms
  with presizing:    grows=0 copies=0 time=5.488208 ms
```

**Gotcha, and honesty about the numbers.** The grow and copy counts are
sturdy: exact integers counted by the code itself, matching the capacity
sequence from Exercise 1 — 14 grows for 1,800 elements, 22 for 40,000. The
timings are not: a single `System.nanoTime` reading with no warmup on a
JIT-compiled runtime, which is why the 40,000-case shows a *smaller* elapsed
time than the 1,800-case despite doing more real work — mostly class-loading
and interpreter-to-JIT overhead, not the cost of the array copies. A
defensible timing claim needs JMH with forked JVMs and warmed-up iterations.
**In an interview, quote the copy counts — 3,690 and 94,846 element-copies
avoided — and neither millisecond figure.**

> **Definition:** presizing does not change what gets stored, only how many
> times the backing array is reallocated and copied to hold it — a count that
> can be measured exactly, unlike wall-clock time on a warm JVM.

## What building it teaches

- The two empty sentinels are the only way `grow` can tell "I was constructed
  with no args and have never grown" apart from "I was explicitly asked for
  zero capacity" without adding a third field just to carry that one bit.
- `hasNext() != checkForComodification()` is a design choice with a visible,
  reproducible cost — Exercise 2's Case B is that cost made concrete rather
  than described.
- The nulling line in `fastRemove` is one statement that nothing in a
  functional test will ever catch missing; only a heap dump or a leak six
  months later would.
- 1.5x versus 2x is a memory decision, not a speed decision — both are O(1)
  amortized appends; 1.5x simply wastes less average unused capacity per list
  across a large fleet of them, which is why the JDK picked it and never
  revisited it even as CPUs and memory both changed by orders of magnitude.

## Pitfalls

### "Nulling the removed slot is redundant once `size` is decremented"

**Wrong**
```java
private void fastRemove(Object[] es, int i) {
    modCount++;
    final int newSize;
    if ((newSize = size - 1) > i) {
        System.arraycopy(es, i + 1, es, i, newSize - i);
    }
    size = newSize;   // slot at the old last index is never cleared
}
```
No test fails — `get`, `size()`, `toString()` behave identically, since nothing
in the public contract reads past `size`.

**Right**
`es[size = newSize] = null;` nulls the dead slot, or the array holds a live
reference to a "forgotten" object until a future `add` overwrites it — a slow
leak on a long-lived list with sporadic removals.

**Why people believe it:** the API can never observe the stale reference, so it
looks cosmetic — the leak only shows up in a heap dump far from the removal.

### "`hasNext()` should check `modCount` too"

**Wrong** `return cursor != size && modCount == expectedModCount;` — this
changes real behaviour: Exercise 2's Case B would now throw instead of
silently skipping, which sounds like a fix, but no version of `ArrayList`
does this, and it is not part of the documented contract.

**Right**
`hasNext()` stays `cursor != size`. Detection lives only in `next()`, via
`checkForComodification()`. Fail-fast is deliberately best-effort, not a
guarantee — file 08 states this explicitly.

**Why people believe it:** "fail-fast" sounds like "always fails on any
modification," and moving the check into `hasNext()` seems like the way to
make that literally true.

### "`set(index, value)` should bump `modCount` like every other mutator"

**Wrong** Adding `modCount++;` inside `set` before writing the new value — a
raw call to the list's own `set` mid-loop now throws
`ConcurrentModificationException` on the next `next()`, behaviour the real
class does not have.

**Right**
`set` never touches `modCount`: it replaces a slot without changing `size` or
the array's shape, so there is nothing structural to detect. Verified:
`modCount` changes on `add`, `remove`, `clear`, `sort` — not on `set`.

**Why people believe it:** every other mutator in this file bumps `modCount`,
so the pattern looks universal until you ask what it is actually for —
detecting *structural* change, and replacing a value is not structural.

### "Growing by exactly `minCapacity` each time is fine — you always grow by what you need"

**Wrong** `return elementData = Arrays.copyOf(elementData, minCapacity);` —
correct for any single call, but appending N elements one at a time now costs
a full-array copy on **every add**: O(n) copies of O(1) work each, O(n²)
total, not the real O(n) amortized cost.

**Right**
Grow by `Math.max(minGrowth, prefGrowth)`, `prefGrowth` being
`oldCapacity >> 1`. Allocating more than strictly needed makes most future
adds free — the amortized argument depends on growing geometrically, not by
the minimum each time.

**Why people believe it:** "grow by what you need" sounds memory-frugal, and
is — it is also the choice that turns linear list-building quadratic.

### "The soft-max clamp is a hard ceiling near `Integer.MAX_VALUE`"

**Wrong**
Assuming `SOFT_MAX_ARRAY_LENGTH = Integer.MAX_VALUE - 8` is a hard ceiling: a
single `addAll` whose minimum length is `Integer.MAX_VALUE - 5` does **not**
clamp down — `hugeLength` returns `minLength` itself once it exceeds the soft
max, because the caller demonstrably needs that much.

**Right**
The clamp is soft. `newLength` prefers 1.5x under the soft max; `hugeLength`
forces the soft max only while the true requirement is still under it, and
returns the larger real requirement (or throws `OutOfMemoryError`) once it is
not. No `ArrayList` in JDK 21 has a private `MAX_ARRAY_SIZE` field — removed
in JDK 13 in favor of shared `ArraysSupport` logic.

**Why people believe it:** the name is easy to skim as just "MAX," and older
JDK-8-era write-ups describe the removed field as if still current.

## Cheat sheet

| What | Real, run value |
|---|---|
| Default-constructed capacity sequence to 400 adds | `10 15 22 33 49 73 109 163 244 366 549` — matches real `ArrayList` exactly |
| Remove last element mid for-each | `ConcurrentModificationException` |
| Remove second-to-last element mid for-each | no exception; that element and everything after it up to the true last is silently skipped |
| `new ArrayList<>()` capacity before/after first add | `0` / `10` |
| `new ArrayList<>(0)` capacity after first add | `1` |
| `new ArrayList<>(4)` capacity after 5 adds | `6` |
| Capacity at size 100 (default growth) | `109` |
| Capacity after `trimToSize()` at size 100 | `100`; `clear()` afterward leaves it `100` |
| Presizing 1,800 appends | 14 grows / 3,690 copies avoided |
| Presizing 40,000 appends | 22 grows / 94,846 copies avoided |
| `modCount` bumped by | `add`, `remove`, `clear`, `sort` — not `set` |
| `--add-opens` needed for | reading `elementData` by reflection outside `java.util` |

## Self-test

**Q1.** Why does `LedgerEntryList` need two distinct empty-array constants
instead of one shared `{}`?

<details><summary>Answer</summary>

Because `grow` needs to distinguish "constructed with no arguments" from
"explicitly constructed with capacity zero" using only `elementData`'s
identity, not an extra field. Both start zero-length, so the only way to tell
them apart is `==` against two separately allocated objects. One shared
constant would make a default-constructed list (jump to capacity 10 on first
add) indistinguishable from an explicitly-zero one (grow to exactly 1).

</details>

**Q2.** In Exercise 2, why does removing the second-to-last element during a
for-each cause an element to be skipped, while removing the last element throws
instead?

<details><summary>Answer</summary>

Both cases shrink `size` by one and leave `cursor` unchanged. Removing the
last element leaves `cursor != size` still true, so `hasNext()` returns true,
`next()` runs, and its `checkForComodification()` catches the mismatched
`modCount` and throws. Removing the second-to-last element makes `cursor`
equal the new `size` immediately, so `hasNext()` returns false and the loop
exits before `next()` — and its check — ever runs again.

</details>

**Q3.** What does the capacity probe in Exercise 3 actually require at the JVM
level, and why?

<details><summary>Answer</summary>

It requires `--add-opens java.base/java.util=ALL-UNNAMED` on the `java`
command line, because `Field.setAccessible(true)` on a private field of a
`java.base` class is a reflective access the module system blocks by default.
Without that flag the call throws `InaccessibleObjectException`.

</details>

**Q4.** In the presizing benchmark, which numbers are trustworthy and which are
not, and why?

<details><summary>Answer</summary>

The grow and copy counts are trustworthy: exact integers from instrumenting
the code's own capacity before and after each add, reproducing Exercise 1's
sequence. The wall-clock timings are not: a single `System.nanoTime` reading
with no warmup mostly reflects class-loading and interpreter-to-JIT overhead,
not the true cost of the array copies. A real timing claim needs JMH with
forked JVMs and multiple warmed-up iterations.

</details>

**Q5.** `newLength(oldLength, minGrowth, prefGrowth)` computes
`oldLength + Math.max(minGrowth, prefGrowth)`. When does `minGrowth` end up
larger than `prefGrowth`?

<details><summary>Answer</summary>

`minGrowth` is `minCapacity - oldCapacity` — the room the caller needs right
now. For a single `add` that is always 1, far below `prefGrowth =
oldCapacity >> 1`, so 1.5x wins. For a bulk `addAll` of 1,000 elements onto a
capacity-10 list, `minGrowth` is 990, exceeding `prefGrowth` of 5 — the list
grows straight to what the bulk operation needs, skipping the geometric step.

</details>

---

**Questions answered:** Q-35
**Sets up:** Next: the interview surface — how all of this is actually asked.
**Diagrams included:** none
**Target version:** Java 21
**Lines:** 513
