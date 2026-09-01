# ArrayList — 01 What It Guarantees

**Target version: Java 21.** | [Map](00-map.md)
Assumes: no prior knowledge of ArrayList.
Next: [02-where-it-sits.md](02-where-it-sits.md)

### The ordered-sequence contract

`ArrayList` is not "a collection of things" — it is a sequence with an index.
The mental model: think of a numbered row of lockers, `0` through `size - 1`,
each holding exactly one reference (or `null`). Insertion order is the row's
left-to-right order, and that same order is what iteration walks. Nothing
reshuffles the lockers on its own.

Before generic collections existed, Java code held ordered, growable data in a
raw array plus a hand-rolled length counter, or in `Vector` (synchronized on
every call, a cost almost nobody wanted). `ArrayList`, added in the Collections
Framework (Java 1.2), is the un-synchronized, generic-friendly replacement:
same ordered-row idea, none of the locking tax.

It applies whenever the reader needs a mutable, ordered, index-addressed bag of
elements and does not need uniqueness or sort order. It loses to `HashSet` when
uniqueness matters more than order, to `TreeMap`/`TreeSet` when sorted order
must be maintained continuously rather than sorted on demand, and — the
contrast this file leans on — to `List.of(...)` when the list is meant to never
change again.

At this depth, "how it works" is one sentence: a `List<E>` backed by a single
array, where `size` tracks how many of the array's slots are live and the rest
are spare capacity paid for in advance. `get(i)` and `set(i, e)` go straight to
`array[i]`. Nothing about *how* the array grows belongs here — file 06 owns
the mechanism; this file only needs you to know that it does grow, on demand,
when it fills up.

This file has no diagram — the type hierarchy that earns one belongs to file
02, which hasn't been introduced yet.

```java
List<LedgerEntry> entries = new ArrayList<>();
entries.add(debitEntry);   // index 0
entries.add(creditEntry);  // index 1
entries.add(debitEntry);   // index 2 — same entry object twice, both legal
entries.add(null);         // index 3 — ArrayList accepts a null element

System.out.println(entries.size());        // 4
System.out.println(entries.get(0) == entries.get(2)); // true — a duplicate reference

// List.of is null-hostile — this is the contrast that matters:
List<LedgerEntry> fixed = List.of(debitEntry, creditEntry);
// List.of(debitEntry, null) would throw NullPointerException immediately
```

**Insight:** the contract says nothing about *content* — no uniqueness, no
sort order, no non-null requirement. It only promises that whatever you put in
comes back out in the order you put it in, positionally addressable by `int`
index. Every other property some readers assume onto `ArrayList` — sortedness,
distinctness, null-rejection — is a property of a *different* type they're
thinking of.

**Pitfall:** assuming a fresh `ArrayList<>()` behaves like `List.of(...)` for
construction purposes. `new ArrayList<>(List.of(a, null, b))` throws at
`List.of` construction time, before the `ArrayList` is even built — the
hostility is `List.of`'s, not `ArrayList`'s. `ArrayList` itself will hold that
`null` all day.

> An `ArrayList` is a mutable, resizable, index-addressed sequence that
> preserves insertion order as iteration order, and permits duplicate elements
> and `null` values.

### The resizable-array premise

The mental model: one contiguous strip of memory, sized larger than what's
currently stored, with a marker (`size`) for where the live data ends. Every
other property of `ArrayList` — its speed profile, its cost profile, even
which `Collections` algorithm gets chosen for it (concept 3) — falls out of
that one structural choice.

It exists because a plain Java array is fixed-length the moment it's
allocated, and real code rarely knows its final size up front. Something has
to sit between "I want array-speed access" and "I don't know how big this gets"
— that something is `ArrayList`.

It applies when most of your access pattern is "walk it" or "index into it,"
and you're willing to pay for occasional resizing to get that. It loses to
`LinkedList` when the dominant operation is inserting or removing at an
*arbitrary interior position* on a large sequence — a linked structure moves
pointers there, an array-backed one moves elements. (In practice, for a
`Movement`'s 2-to-4 entries, that difference is invisible; it matters at
thousands of elements, not four.)

The mechanism at this depth stops at: it's backed by one array, and index
access reads or writes a single slot directly; there is no traversal. Growth —
what triggers it, by how much, what it costs — is file 06's job, named here
only as "it happens automatically when the array fills."

```java
List<LedgerEntry> entries = new ArrayList<>();
entries.add(debitEntry);
entries.add(creditEntry);

LedgerEntry third = entries.get(1);          // direct slot read — no walking
entries.add(0, chargebackEntry);             // insert at the front

// after the insert, every existing element shifted one slot to the right
// to make room at index 0 — that's the cost of positional insert on an
// array-backed structure, paid regardless of how the array happened to grow
```

**Tradeoff:** index access (`get`, `set`) is a single array read or write — the
capability everything else is traded for. The cost lands on `add(int, E)` and
`remove(int)` away from the tail: every element after the touched index has to
shift by one slot. Appending at the end (`add(E)`) usually skips the shift
entirely, which is exactly why append-only structures like `Movement.entries`
fit an array-backed list so well — but note that `Movement.entries` is
deliberately **immutable** once built (see the callout below), because the
domain wants append-once, not append-forever mutability.

**Interview:** "why is `ArrayList.get` O(1) but `ArrayList.add(0, x)` O(n)?" —
because `get` reads one array slot directly by index, while inserting at the
front has to shift every existing element one position over to open the slot;
appending at the end is the one insert that usually avoids that shift.

> `ArrayList` trades the cost of shifting elements on positional insert/remove
> for direct, constant-time access to any index.

### RandomAccess as a marker

The mental model: `RandomAccess` is a sticky note on the class, not a set of
tools. Open `java.util.RandomAccess` and there is nothing inside it — no
methods, no fields, no constants:

```java
public interface RandomAccess {
}
```

It exists because `List` has two structurally different implementations —
array-backed (`ArrayList`) and node-linked (`LinkedList`) — and generic
algorithms written against the `List` interface can't tell which one they've
been handed just by looking at the type. Before this marker, a generic
algorithm had no cheap way to choose between "index in a loop" and "walk with
an iterator" without measuring.

It applies to any `List` where indexed access is genuinely fast; it should
never be implemented by a list where `get(i)` has to walk from the head, which
is exactly why `LinkedList` does *not* implement it.

The mechanism, at this file's depth: implementing `RandomAccess` makes no code
run and adds no behavior. What it does is let *other* code branch on
`instanceof RandomAccess`. `Collections.binarySearch`, `Collections.shuffle`,
`Collections.reverse`, and `Collections.fill` each check for it and pick an
index-based loop when it's present, falling back to an iterator-based walk
when it's absent — because an iterator walk over a `LinkedList` is fast, but a
thousand `get(i)` calls over the same `LinkedList` would each re-walk from the
head.

```java
List<LedgerEntry> entries = new ArrayList<>();
entries.add(debitEntry);
entries.add(creditEntry);

System.out.println(entries instanceof RandomAccess); // true

// Collections.binarySearch sees RandomAccess and uses an index-based
// binary search directly against entries.get(mid); handed a LinkedList
// holding the same elements, it would fall back to walking a ListIterator
// instead, because repeated get(mid) calls on a linked structure would
// each cost a full walk from one end.
```

**Insight:** an empty interface still changes real program behaviour, because
Java's dispatch on `instanceof` lets library code make a decision purely from
*which marker interfaces a type declares* — no method call required. The
"marker" pattern trades a compile-time capability declaration for a run-time
`if`.

**Pitfall:** assuming `RandomAccess` itself is *why* `ArrayList.get` is fast.
It isn't — the array-backed structure (concept 2) is why. `RandomAccess` is
just the declaration that lets other code *find out* that fact without timing
it.

> `RandomAccess` is a zero-method marker interface whose only effect is that
> library algorithms check for it and choose an index-based strategy instead
> of an iterator-based one.

### The absence of thread safety

The mental model: `ArrayList` behaves like a notebook one person writes in at
a time — it has no lock, no latch, nothing that makes two writers, or a reader
and a writer, safe to touch it simultaneously.

It exists this way because `Vector`, the original ordered growable list,
synchronized every method whether or not the caller ever touched it from more
than one thread — nearly all callers paid a lock for a guarantee they never
needed. `ArrayList` is the deliberate un-synchronized replacement; callers who
do need thread safety are expected to reach for it explicitly, either
`Collections.synchronizedList(...)` or a concurrent structure such as
`CopyOnWriteArrayList`.

It applies wherever a list is confined to one thread, or to code that already
serializes access some other way (a single-writer queue, a lock the caller
holds). It loses outright the moment two threads can call a mutating method on
the same instance concurrently without external coordination — that case
needs one of the alternatives just named, not this type.

The mechanism, at this depth: no method is `synchronized`; compound operations
like "check size, then add" are not atomic as a unit even though each
individual call looks self-contained; and — the subtle half readers usually
miss — the fail-fast behaviour some people lean on as a safety net is
explicitly **best-effort by contract**, not a guarantee. The javadoc's own
words: a fail-fast iterator throws `ConcurrentModificationException` on a
best-effort basis, and correctness must never depend on it. Treat a thrown CME
as a debugging aid that sometimes fires when the list was mutated during
iteration — not as proof of safety when it stays quiet, and not as a mechanism
you're allowed to rely on. The exact reason it can stay quiet is file 08's
job.

```java
List<LedgerEntry> entries = new ArrayList<>();
entries.add(debitEntry);
entries.add(creditEntry);
entries.add(chargebackEntry);

// Two threads calling entries.add(...) on the SAME instance with no external
// synchronization is undefined behaviour — no exception is promised, and a
// silently corrupted internal array (a lost element, a wrong size) is a real
// outcome, not a worst case someone made up.
```

**Gotcha:** a for-each loop that removes the second-to-last element from an
`ArrayList` does **not** throw `ConcurrentModificationException` — the loop
simply exits one iteration early and the last element is never visited,
silently. The check only ever compares against an internal `size`/cursor pair
at the *next* `next()` call; if there is no next call because the loop thinks
it's already done, the check never runs. Depending on CME to catch every
concurrent-modification bug is depending on a contract that explicitly says
"best effort."

**Interview:** "is `ArrayList` thread-safe?" — no, and the honest follow-up is
that its fail-fast iterator is not a substitute for thread safety either,
because the javadoc defines it as best-effort, not guaranteed.

> `ArrayList` provides no synchronization of any kind, and its fail-fast
> iterator check is a best-effort debugging aid rather than a correctness
> guarantee.

## Pitfalls

### Believing a single `add` or `get` call is inherently safe under concurrency because it "looks atomic"

**Wrong**
```java
// Thread A and Thread B both hold a reference to the same ArrayList<LedgerEntry>
// and both call entries.add(newEntry) with no external lock.
```
No exception is guaranteed here at all — the danger isn't a crash you can
catch, it's silent corruption: a dropped element, an inconsistent `size`, or
occasionally a real exception from a torn internal array read.

**Right**
Wrap it with `Collections.synchronizedList(new ArrayList<>())` and synchronize
externally on the returned list for any operation that isn't already atomic
(including iteration), or use `CopyOnWriteArrayList` when reads vastly
outnumber writes.

**Why people believe it:** a single method call has no visible "in-between"
state from the caller's side, so it's easy to assume the JVM enforces
atomicity — but atomicity is a promise a data structure has to make
explicitly, and `ArrayList` never does.

### Believing `ConcurrentModificationException` reliably fires whenever a list is mutated during iteration

**Wrong**
```java
List<String> codes = new ArrayList<>(List.of("AO-100", "AO-400", "AA-700"));
for (String code : codes) {
    if (code.equals("AO-400")) {
        codes.remove(code); // removes the second-to-last element
    }
}
// No exception. "AA-700" is silently never visited.
```

**Right**
Use `Iterator.remove()` (or `removeIf`) instead of mutating the backing list
mid-iteration, and never treat "no exception was thrown" as proof that nothing
went wrong — the check is best-effort by contract, as stated in the fourth
concept above.

**Why people believe it:** it does fire for *most* removals, which is enough
successful demonstrations in casual testing to build false confidence that
it's a guarantee rather than a heuristic.

### Believing `RandomAccess` makes access faster by itself, or that it declares methods to override

**Wrong**
```java
class MyList<E> extends AbstractList<E> implements RandomAccess {
    // "I implemented RandomAccess, so get() is now fast" — no override required,
    // no speed granted; get(i) is still whatever AbstractList.get does.
}
```

**Right**
`RandomAccess` has zero members — implementing it changes nothing about your
`get`/`set` performance. Only implement it on a type whose indexed access is
*already* fast, so that library algorithms that check for the marker make the
correct choice.

**Why people believe it:** the name sounds like a capability being granted,
when it's actually a claim being declared — the fast access has to already
exist in the implementation before the marker is honest.

### Believing `List.of(...)` and `new ArrayList<>()` accept the same inputs

**Wrong**
```java
List<LedgerEntry> entries = List.of(debitEntry, null); // throws NullPointerException
```

**Right**
```java
List<LedgerEntry> entries = new ArrayList<>();
entries.add(debitEntry);
entries.add(null); // perfectly legal
```

**Why people believe it:** both produce something assignable to `List<E>`, and
nothing about the `List` interface itself forbids `null` — the null-hostility
is a design choice specific to the immutable factory methods, not a rule of
the interface.

## Cheat sheet

| Property | ArrayList |
|---|---|
| Iteration order | Insertion order, always |
| Duplicates | Permitted |
| `null` elements | Permitted (contrast: `List.of` throws NPE on `null`) |
| Mutability | Mutable and resizable |
| Backing structure | One contiguous array plus a `size` counter (mechanism deferred to file 06) |
| Index access (`get`/`set`) | Direct array-slot access |
| Positional insert/remove (not at tail) | Shifts subsequent elements |
| `RandomAccess` | Implemented — empty marker; changes which `Collections` algorithm is chosen |
| Thread safety | None — no synchronization anywhere |
| Fail-fast `CME` | Best-effort by contract, not a guarantee — can silently miss |
| Sorted order | Not guaranteed |
| Uniqueness | Not guaranteed |
| `getFirst()` / `getLast()` (Java 21) | Present; throw `NoSuchElementException` on an empty list |

## Self-test

**Q1.** Does `ArrayList` guarantee sorted order, and if not, what does it guarantee about order?

<details><summary>Answer</summary>

No sorted-order guarantee. It guarantees only that iteration order equals
insertion order — whatever order elements were added in is the order you get
them back in, until something explicitly reorders or mutates the list.

</details>

**Q2.** Why does `new ArrayList<>()` accept `null` as an element while `List.of(a, null)` throws?

<details><summary>Answer</summary>

`ArrayList`'s contract as a general-purpose mutable `List` places no
restriction on `null` elements — a slot can hold a null reference like any
other. `List.of(...)` is a *specific* factory method that was designed to be
null-hostile as a deliberate choice for its immutable, defensively-checked
lists; that hostility belongs to `List.of`, not to the `List` interface or to
`ArrayList` itself.

</details>

**Q3.** `RandomAccess` declares no methods. What does implementing it actually change?

<details><summary>Answer</summary>

It changes nothing about the implementing class's own behaviour or
performance directly. What it changes is how *other* code behaves: generic
algorithms in `java.util.Collections` (`binarySearch`, `shuffle`, `reverse`,
`fill`, and others) check `instanceof RandomAccess` and pick an index-based
loop for lists that implement it, falling back to an iterator-based walk for
lists that don't — because repeated `get(i)` calls are cheap on an
array-backed list but expensive (a full walk each time) on a linked one.

</details>

**Q4.** Is `ArrayList` thread-safe as long as you only ever call `add`, one call at a time from different threads?

<details><summary>Answer</summary>

No. `ArrayList` has no synchronization at all — not even for what looks like a
single call. Concurrent `add` calls from multiple threads with no external
coordination can corrupt internal state (lost elements, a wrong `size`) with
no guaranteed exception. Safety has to come from outside the class:
`Collections.synchronizedList(...)`, an external lock, or a concurrent
alternative like `CopyOnWriteArrayList`.

</details>

**Q5.** A for-each loop over an `ArrayList` removes an element and no `ConcurrentModificationException` is thrown. Does that prove the removal was safe?

<details><summary>Answer</summary>

No. Fail-fast detection is explicitly documented as best-effort — it is not a
correctness guarantee. There is a real, reproducible case (removing the
second-to-last element during a for-each) where no exception fires and the
last element is simply never visited, silently. Absence of `CME` is not
evidence of correctness; it is only evidence that the specific check that
happens to run didn't happen to catch this particular mutation.

</details>

**Q6.** Why can `Movement.entries` afford to be an immutable `List<LedgerEntry>` while other lists in the same codebase are mutable `ArrayList`s?

<details><summary>Answer</summary>

`Movement.entries` is built once and never changes afterward — it represents
a posted, append-only fact (the ledger legs of one movement), so there is
nothing left to mutate after construction and immutability is free safety
with no lost capability. A general-purpose sequence that legitimately needs
elements added, removed, or reordered over its lifetime — a working list built
up incrementally — needs the mutability `ArrayList` provides; the choice is
about whether the list's *lifecycle* includes further changes, not about
`ArrayList` being unsafe or `List.of` being strictly better.

</details>

---

**Questions answered:** Q-01, Q-02, Q-03
**Sets up:** Next: where ArrayList sits in the Java 21 type graph, and what each layer above it contributes.
**Diagrams included:** none
**Target version:** Java 21
**Lines:** 437
