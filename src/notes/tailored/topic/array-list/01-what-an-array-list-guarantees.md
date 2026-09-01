# `ArrayList` — 01 What an `ArrayList` guarantees

**Target version: Java 21 LTS.** | [Map](00-map.md)
Assumes: no prior knowledge of ArrayList.
Next: [02 Position in the collections map](02-position-in-the-collections-map.md)

### The positional-index contract

Picture a numbered register: every element sits at an integer position, `0`
through `size() - 1`, and that position is the only address the list ever
uses to find it. There is no key, no hash, no ordering rule based on the
element's value — just "the thing at position 3". That single idea is the
entire contract `List` makes about shape, and `ArrayList` is the
straightforward implementation of it: an array-backed, unsynchronized,
general-purpose list.

It exists to replace `Vector`. Before `ArrayList` arrived in JDK 1.2 (the
class Javadoc carries `@since 1.2`), the only resizable array-backed list in
the JDK was `Vector`, which synchronizes every method whether or not the
caller has more than one thread. `ArrayList` is `Vector` with that tax
removed — same backing-array idea, no built-in lock.

Where it applies: any time the reader cares about *order* and *position* —
"what came third", "what's at index `i`", "insert here". Where it does not:
the moment the read pattern is "do I have this element" rather than "what is
at this position", a `HashSet` answers in O(1) what a `List` can only answer
in O(n); the moment duplicates must be structurally impossible rather than
merely unlikely, a `Set` enforces that and a `List` never will.

Mechanically, `ArrayList<E>` is declared `extends AbstractList<E> implements
List<E>, RandomAccess, Cloneable, java.io.Serializable`. The positional
contract itself lives one level up, on `List`: `get(int)`, `set(int, E)`,
`add(int, E)`, `remove(int)`, `indexOf`, `lastIndexOf`, and the two iterator
factories that walk positions in order. `List` also nails down `equals` and
`hashCode` precisely: two lists are equal exactly when they have the same
size and every corresponding pair of elements is `Objects.equals`, position
by position — so an `ArrayList` can equal a `LinkedList` holding the same
elements in the same order, and `hashCode` is specified as
`hashCode = 31 * hashCode + (e == null ? 0 : e.hashCode())`, accumulated
front to back. Neither computation ever looks at value order — only at
positional order.

Duplicates are legal because nothing in `add` ever compares the incoming
element to what is already there. `add` appends; it does not search.

```java
List<LedgerEntry> legs = new ArrayList<>();
legs.add(new LedgerEntry(UUID.randomUUID(), movementId, PositionRef.of("CASH_AVAILABLE"),
        Direction.DEBIT, Money.of("4.20"), Instant.now()));
legs.add(new LedgerEntry(UUID.randomUUID(), movementId, PositionRef.of("BONUS_AVAILABLE"),
        Direction.DEBIT, Money.of("4.20"), Instant.now()));

System.out.println(legs.get(0).amount());   // 4.20
System.out.println(legs.get(1).amount());   // 4.20 — a genuine second entry, not a duplicate error
```

This is `Movement.entries` for a stake reservation of 4.20 (the measured
average stake value from the platform's own volume figures) split across a
cash leg and a bonus leg: two distinct `LedgerEntry` records that happen to
carry the same amount. The list's job is to hold them in posting order and
let the ledger's sum-to-zero check walk them by position — not to notice or
care that two entries share a value. Rejecting the second entry as a
"duplicate" would silently corrupt the books.

**Gotcha:** "order" here means *insertion order*, not chronological order
across multiple sources merged together, and not sorted order. A
`List<LedgerEntry>` built by appending entries as they are posted preserves
posting order; if you later merge two such lists, the merged list is not
automatically re-ordered by `postedAt` — that requires an explicit `sort`.
Also, position is not identity: `get(0)` answers "what is currently first",
which can change as the list mutates, unlike a `Map` key that identifies the
same conceptual slot forever.

> An `ArrayList` guarantees that every element has a stable integer position
> from `0` to `size() - 1`, that iterating or indexing visits elements in
> that same insertion order, and that duplicate elements — even
> value-identical ones — are always permitted.

### The four non-guarantees

Four assumptions people carry over from "it's a collection" and `ArrayList`
explicitly does not make: that it is safe across threads, that mutating it
mid-iteration is detected, that it keeps itself sorted, and that its
capacity means anything to the caller. Capacity gets a full concept of its
own below; the first three are worth a single table because they are the
same shape of mistake — reading "the class provides X" where the actual
claim is "the class provides nothing about X, choose your own mechanism."

| Assumption | What actually happens | Cost of getting it wrong | The mechanism that actually provides it |
|---|---|---|---|
| Thread-safe | No synchronization anywhere in `ArrayList` — no lock field exists to acquire | Corrupted internal state, lost elements, or an exception from two threads racing inside `add` | `Collections.synchronizedList(list)` (whole-object lock; iteration still needs external synchronization) or `CopyOnWriteArrayList` (copy-on-write, snapshot iterators) |
| Mutation during iteration is caught | The iterator is *fail-fast on a best-effort basis*, not fail-safe | A structural change can go completely undetected depending on which index it lands on | `Iterator.remove()` / `ListIterator.add()`, or `removeIf(Predicate)`, which mutate safely from inside the traversal |
| Keeps itself sorted | Elements sit in whatever order they were inserted; nothing reorders them automatically | Code that assumes ascending order silently reads garbage comparisons | Call `list.sort(comparator)` explicitly, whenever the current order might be stale |
| Capacity reflects anything the caller can query or rely on | Capacity is an internal implementation detail with no accessor | — covered in full below — | — |

The fail-fast mechanism is real but incomplete by design, and the classic
demonstration is worth walking in the domain rather than taking on faith. A
stake-reserved movement books four legs — cash debit, bonus debit, cash
credit to reserved, bonus credit to reserved:

```java
List<String> legs = new ArrayList<>(
        List.of("CASH_AVAILABLE", "CASH_RESERVED", "BONUS_AVAILABLE", "BONUS_RESERVED"));

for (String position : legs) {
    if (position.equals("CASH_RESERVED")) {
        legs.remove(position);       // throws ConcurrentModificationException
    }
}
```

Removing `"CASH_RESERVED"` — the element at index 1 of 4 — throws. Change the
target to `"BONUS_AVAILABLE"`, the element at index 2, and the same loop
finishes with **no exception at all**, silently leaving `legs` as
`[CASH_AVAILABLE, CASH_RESERVED, BONUS_RESERVED]`. The iterator only checks
for a structural change on its *next* call; removing the second-to-last
element shrinks `size` down to exactly the cursor position that would have
triggered the next call, so the loop's own termination check — "have I
reached the end?" — fires first and the check that would have thrown never
runs. Whether a mid-iteration mutation is caught depends on *which position*
you mutate, which is why the JDK's own documentation calls this behavior
best-effort and warns it "cannot be guaranteed" — treat
`ConcurrentModificationException` as a bug detector you got lucky with, never
as a safety net you can rely on.

**Gotcha:** the inverse mistake is just as common — assuming that because
`ConcurrentModificationException` *can* fire, catching and swallowing it is
a legitimate way to "handle concurrent access." It is neither reliable
detection nor a substitute for actual synchronization; it is what happens to
be observable in the single-threaded case of a list changing size while an
iterator holds a stale cursor.

> `ArrayList` promises order, index and duplicates and nothing past that:
> no thread-safety, no guaranteed detection of concurrent structural change,
> no self-sorting — each of those is a separate, opt-in mechanism the caller
> must choose.

### Null policy

An `ArrayList` slot is just a reference in a plain `Object[]`, and a
reference is allowed to point at nothing. `ArrayList` places no restriction
on that: `null` is a completely ordinary element, storable at any position,
any number of times, with no special-casing anywhere in `add`, `get`, or
`remove`.

That permissiveness exists because `ArrayList` is a general-purpose mutable
container with no reason to reject a value it never inspects. Contrast that
with `List.of(...)` and the other immutable factories added in Java 9,
which reject `null` outright, at construction time, specifically so that
"this reference is absent" can never be confused with "this list happens to
contain the null object" inside code that was handed an immutable list as a
defensive copy:

```java
List.of("clientId-9001", null);
// -> java.lang.NullPointerException
```

The exception fires on the call to `List.of`, before any list exists at all
— which matters because it means a null-tolerant `ArrayList` and a
null-rejecting `List.of` are not interchangeable at the call site, only at
the read site. `Map` draws its own, third line: `HashMap` permits exactly
one `null` key and any number of `null` values, while `Hashtable` and
`ConcurrentHashMap` reject `null` for both keys and values, because a
concurrent map has no safe way to distinguish "no mapping present" from "a
mapping present whose value is null" without an extra check that would
defeat its lock-free reads. Three collections, three different null
policies, none of them accidental.

Where a `null` element is genuinely useful is exactly the case where
"unknown yet" is a real state, not a bug. A bank deposit that arrives before
it can be matched to a client sits in `SUSPENSE` with no attributable
account:

```java
record UnmatchedCredit(String bankReference, Money amount, ClientId attributedTo) {}

List<UnmatchedCredit> suspense = new ArrayList<>();
suspense.add(new UnmatchedCredit("BDP-REF-88213", Money.of("480.00"), null));
// attributedTo is null: this credit has landed in SUSPENSE and has not yet
// been matched to a ClientId. The list holds it exactly as-is until the
// matching job runs and replaces the entry with an attributed one.
```

`ArrayList` is content to hold that record with a `null` field for as long
as the domain needs it to stay unattributed; a `List.of(...)` snapshot of
the same data could not have been built with that field unset.

Position also matters here in a way that is easy to miss: `get(int)` on an
out-of-range index throws `IndexOutOfBoundsException` regardless of size,
but asking an *empty* list for its first or last element throws a different
exception entirely, because there is no position to name at all:

```java
new ArrayList<String>().getFirst();
// -> java.util.NoSuchElementException

new ArrayList<String>().get(0);
// -> java.lang.IndexOutOfBoundsException: Index 0 out of bounds for length 0
```

**Gotcha:** refactoring `new ArrayList<>(List.of(x, null))` into a plain
`List.of(x, null)` "because they hold the same elements" breaks at the
`List.of` call, not later where the `null` is actually read — the failure
moves upstream and the stack trace no longer points at the code that cared
about the `null`.

> `ArrayList` permits `null` at any position, any number of times, with no
> special handling; that is a deliberate contrast with `List.of`, which
> rejects it at construction, and with `HashMap`, which allows exactly one
> `null` key but nothing more.

### `size` versus capacity

`size` and capacity answer two different questions, and only one of them is
part of what `List` promises. `size()` answers "how many elements does this
list logically hold right now" — that is content, and it is part of the
`List` contract, specified and callable. Capacity answers "how big is the
array currently backing this list" — that is implementation, specific to
`ArrayList`, and it has no getter at all. The field that holds it,
`elementData`, is a plain array; capacity is simply `elementData.length`,
read directly, with no method standing between the caller and that fact —
except that the caller can't reach it, because `elementData` is not exposed.

The reason capacity exists as a concept at all is amortized growth: an array
cannot resize itself, so `ArrayList` periodically allocates a bigger one and
copies everything across, and it always allocates *more* than the current
`size` demands so that most `add` calls don't have to pay for a copy. `size`
only needs to track content because `List`'s contract is about content;
capacity is purely how `ArrayList` chooses to implement "resizable" without
resizing on every single call.

![`size` counts elements; `elementData.length` is capacity. Only one of the two is in the `List` contract.](diagrams/D-01-size-vs-capacity.svg)

A freshly constructed default `ArrayList` starts at capacity `0` — not `10`
— and only jumps to a capacity of `10` on the *first* `add`:

```java
List<Movement> burst = new ArrayList<>();
System.out.println(burst.size());     // 0 — size is always readable
// capacity is 0 here too, but there is no burst.capacity() to call and
// confirm it; the only place that number lives is elementData.length,
// and elementData is not exposed outside the class.

burst.add(someMovement);
System.out.println(burst.size());     // 1 — content grew by exactly one element
// capacity is now 10, even though only one element was added: `ArrayList`
// over-allocated on purpose, anticipating more adds during a stake-settlement
// burst that can run at 1,200 reservations per second.
```

`size` is declared as a plain `int`, which is the reason a `List` has a hard
ceiling on element count at `Integer.MAX_VALUE` — not a capacity limit, a
counting limit: past that point there is no valid `int` left to hold the
count, regardless of how much memory is available for the backing array.

**Gotcha:** treating `size() == 0` and "capacity is small" as the same fact.
A default-constructed `ArrayList` and an explicitly-sized `new
ArrayList<>(0)` both report `size() == 0`, and look identical from outside
— but they grow differently from that point on, because the default
constructor's `0` is a sentinel meaning "not yet allocated, go to the normal
default on first add" while an explicit `0` means "actually allocate zero,
grow one element at a time from there." `size()` cannot tell you which one
you are holding; that distinction is a `01-`-file-level fact you should
simply know exists, not something `size()` exposes.

> `size()` is the `List` contract's answer to "how many elements"; capacity
> — `elementData.length` — is `ArrayList`'s own answer to "how big is the
> array underneath", has no accessor, and is never part of what `List`
> promises to any caller.

---

## Pitfalls

### "It's a collection from the standard library, so it must be thread-safe"

**Wrong**
```java
List<Reservation> openReservations = new ArrayList<>();

// thread A
openReservations.add(reservationOne);
// thread B, concurrently
openReservations.add(reservationTwo);
// -> no exception guaranteed either way; possible outcomes include a lost
//    element, a corrupted internal array, or an ArrayIndexOutOfBoundsException
//    thrown from inside add() itself
```

**Right**
```java
List<Reservation> openReservations =
        Collections.synchronizedList(new ArrayList<>());
// every method call is now synchronized on one monitor — but a caller
// iterating it must still hold that same monitor for the whole traversal,
// because the iterator itself is not synchronized
```

**Why people believe it:** `Vector`, the class `ArrayList` was introduced to
replace, *was* synchronized on every method, and the two look interchangeable
from their method signatures — nothing in `ArrayList`'s public surface
signals that the safety was deliberately removed.

### "A `ConcurrentModificationException` will always catch a bad mutation during iteration"

**Wrong**
```java
List<String> legs = new ArrayList<>(
        List.of("CASH_AVAILABLE", "CASH_RESERVED", "BONUS_AVAILABLE", "BONUS_RESERVED"));

for (String position : legs) {
    if (position.equals("BONUS_AVAILABLE")) {
        legs.remove(position);
    }
}
// no exception — legs silently ends up [CASH_AVAILABLE, CASH_RESERVED, BONUS_RESERVED]
```

**Right**
```java
legs.removeIf(position -> position.equals("BONUS_AVAILABLE"));
// or: use an explicit Iterator and call iterator.remove()
```

**Why people believe it:** the very similar-looking removal one position
earlier in the same list *does* throw, so a developer who tested with the
element next-to-last generalizes "removing during a for-each always throws"
from a case that happened to land on the one index where the fail-fast check
still runs before the loop exits.

### "`new ArrayList<>(List.of(x, null))` is a safe way to get a mutable list that might contain a null"

**Wrong**
```java
List<ClientId> attributed = new ArrayList<>(List.of(clientId, null));
// -> java.lang.NullPointerException, thrown by List.of itself — the
//    ArrayList constructor never runs
```

**Right**
```java
List<ClientId> attributed = new ArrayList<>();
attributed.add(clientId);
attributed.add(null);   // legal: ArrayList never rejects null
```

**Why people believe it:** `List.of(...)` is usually a drop-in way to seed
an `ArrayList` with the same elements a hand-built list would hold, so it is
easy to assume its null-handling matches `ArrayList`'s permissive policy
too, when in fact the two collections disagree specifically on this point.

---

## Cheat sheet

| Question | Guarantee |
|---|---|
| Order | Insertion order, always — never re-derived from element value |
| Index access | `get`/`set`/`add`/`remove` all positional, `0` to `size() - 1` |
| Duplicates | Always permitted, including value-identical elements |
| Thread-safety | None — no synchronization anywhere in the class |
| Iteration + mutation | Fail-fast, best-effort only — not guaranteed to detect every case |
| Sorted order | Never automatic — `sort(Comparator)` must be called explicitly |
| `null` elements | Fully permitted, any position, any count |
| Empty list, `getFirst()`/`getLast()` | `NoSuchElementException`, not `IndexOutOfBoundsException` |
| `size()` | Part of the `List` contract; content count as an `int` |
| Capacity (`elementData.length`) | Not part of the `List` contract; no accessor exists |
| Hard element ceiling | `Integer.MAX_VALUE`, because `size` is an `int` |

## Self-test

**Q1.** Two `LedgerEntry` objects in a `List<LedgerEntry>` have the exact
same amount, position, and direction. Does the list reject the second one as
a duplicate?

<details><summary>Answer</summary>

No. `List`'s contract never compares elements to each other on `add` — it
only appends at the next position. Duplicates, including value-identical
ones, are always legal; rejecting them would require an explicit dedup step
the caller writes, not anything `ArrayList` does automatically.

</details>

**Q2.** Why does `ArrayList` have no built-in synchronization at all, when
`Vector` — the class it effectively replaced — synchronizes every method?

<details><summary>Answer</summary>

`ArrayList` was introduced specifically to be the unsynchronized,
general-purpose alternative to `Vector`: most callers never share a list
across threads, and paying a lock-acquisition cost on every single-threaded
`add`/`get` call is pure waste for them. Callers who do need thread-safety
opt in explicitly, via `Collections.synchronizedList` or
`CopyOnWriteArrayList`, rather than everyone paying for a lock they don't
need.

</details>

**Q3.** A `for (String s : legs) { if (...) legs.remove(s); }` loop removes
one element and finishes with no exception. Does that prove removing during
iteration is safe?

<details><summary>Answer</summary>

No. The iterator's fail-fast check only fires on the *next* call after a
structural change; removing an element close enough to the end can shrink
`size` down to exactly the cursor position that would have ended the loop
anyway, so the loop exits normally before the check that would have thrown
ever runs. Whether the exception fires depends on which index was removed,
not on whether the mutation was safe — the JDK's own documentation calls
this best-effort and explicitly says it "cannot be guaranteed."

</details>

**Q4.** Does `ArrayList` keep its elements sorted as they are added?

<details><summary>Answer</summary>

No. Elements sit in whatever order they were inserted; nothing reorders them
automatically. Getting sorted order requires explicitly calling
`list.sort(comparator)` whenever the caller needs the current order to
reflect a value-based ordering.

</details>

**Q5.** `List.of("x", null)` throws immediately. Does `new
ArrayList<String>().add(null)` also throw?

<details><summary>Answer</summary>

No. `ArrayList` places no restriction on `null` elements at all — `add(null)`
succeeds at any position, any number of times. `List.of` is the one that
rejects `null`, specifically because it is meant to guarantee "this
reference is absent" can never be confused with "this list contains the
null object."

</details>

**Q6.** `new ArrayList<String>().getFirst()` and `new
ArrayList<String>().get(0)` are both calls on an empty list. Do they throw
the same exception?

<details><summary>Answer</summary>

No. `get(0)` throws `IndexOutOfBoundsException`, because index `0` is out of
range for a list of length `0`. `getFirst()` throws
`NoSuchElementException`, because on an empty list there is no "first
position" to name at all — it is a different kind of failure, not just a
different message for the same one.

</details>

**Q7.** Two lists are both empty and both report `size() == 0`: one built
with `new ArrayList<>()`, the other with `new ArrayList<>(0)`. Is their
capacity the same?

<details><summary>Answer</summary>

Not necessarily comparable the way `size()` suggests. Both currently hold a
zero-length backing array, but the default constructor's array is a
sentinel meaning "not yet sized — jump to the normal default on the first
`add`," while the explicit `new ArrayList<>(0)` means "grow one element at a
time from here." `size()` reports `0` for both and cannot reveal that
difference; capacity is never exposed by any accessor either way.

</details>

---

**Questions answered:** Q-01, Q-02, Q-03, Q-04
**Sets up:** Next: where ArrayList sits among its supertypes and siblings, and what RandomAccess buys.
**Diagrams included:** D-01
**Target version:** Java 21 LTS
**Lines:** 476
