# `ArrayList` — 04 Constructors and factories

**Target version: Java 21 LTS.** | [Map](00-map.md)
Assumes: the member surface and which members are optional operations (file 03).
Previous: [03 The complete member surface](03-the-complete-member-surface.md) · Next: [05 Internals — fields, sentinels and growth](05-internals-fields-sentinels-and-growth.md)

File 03 gave you every member `ArrayList` answers to and where each is declared. This file
answers a narrower question: when a QuizStakes expression hands you a `List<X>`, what runtime
class is behind it, what capacity does it start at, and what does the wrong choice cost? Nine
call-site expressions look interchangeable. Only five hand you a real, mutable
`java.util.ArrayList` — the three constructors, `clone()`, and `Collectors.toList()`. The rest
compile identically and behave nothing alike.

## The nine-route map

| # | Expression | Runtime class | Initial capacity | Mutability |
|---|---|---|---|---|
| 1 | `new ArrayList<>()` | `java.util.ArrayList` | 0 (grows to 10 on first `add`) | mutable |
| 2 | `new ArrayList<>(n)` | `java.util.ArrayList` | `n` (0 if `n == 0`) | mutable |
| 3 | `new ArrayList<>(c)` | `java.util.ArrayList` | `c.size()` (adopted or copied) | mutable |
| 4 | `list.clone()` | `java.util.ArrayList` | `size()` (shrink-to-fit) | mutable, shallow |
| 5 | `stream().collect(Collectors.toList())` | `java.util.ArrayList` | unspecified | mutable |
| 6 | `List.of(...)` / `List.copyOf(...)` | `ImmutableCollections$List12`/`$ListN` | fixed | immutable |
| 7 | `Arrays.asList(arr)` | `java.util.Arrays$ArrayList` | fixed at `arr.length` | fixed-size, write-through |
| 8 | `stream().toList()` | `ImmutableCollections$ListN` | fixed | immutable |
| 9 | `list.subList(from, to)` | `java.util.ArrayList$SubList` | n/a — a view | mutable, write-through, not `Serializable` |

Rows 1–5 are the diagram's five real `ArrayList`s: the four **construction routes** (three
constructors plus `clone()`, which allocates a fresh backing array through `Object.clone()`)
and the one collector that still returns `ArrayList` today. Rows 6–9 are look-alikes. Two more
non-shape-producing routes, both from file 03's member walk, round out the picture:
`Collections.unmodifiableList(list)` (`Collections$UnmodifiableRandomAccessList`, a view) and
`list.reversed()` (`ReverseOrderListView$Rand`, mutable, write-through).

![Nine ways to obtain a `List`; five of them hand you a real `ArrayList` — the four construction routes plus `Collectors.toList()`. The runtime class is what decides whether `add` throws.](diagrams/D-04-construction-routes.svg)

---

### The three constructors and their capacities

**Mental model.** `ArrayList` has one internal shape — `Object[] elementData` plus `int
size` — and three ways to hand you a fresh one: tell it nothing, a number, or a `Collection`
to copy from. Each answers one question: how big should the backing array be before the first
`add`?

**Why it exists.** One constructor would force every caller to pay for a default-sized array
whether needed or not, and give collection-to-collection copies no faster path than looping
`add`. Three constructors let the caller state what it knows: nothing, an estimate, or an
exact source.

**When it applies, and when it does not.** Use `new ArrayList<>(n)` when the final size (or a
close bound) is known before the first `add`. Use `new ArrayList<>()` when the size is
unknown and additions are exploratory. Use `new ArrayList<>(c)` when duplicating or detaching
from an existing collection — never by looping `add` yourself.

**How it works.** Quoted verbatim, JDK 21.0.7, lines 154–188:

```java
public ArrayList(int initialCapacity) {
    if (initialCapacity > 0) {
        this.elementData = new Object[initialCapacity];
    } else if (initialCapacity == 0) {
        this.elementData = EMPTY_ELEMENTDATA;
    } else {
        throw new IllegalArgumentException("Illegal Capacity: "+
                                           initialCapacity);
    }
}

public ArrayList() {
    this.elementData = DEFAULTCAPACITY_EMPTY_ELEMENTDATA;
}
```

`new ArrayList<>(n)` for `n > 0` allocates on the spot — capacity exactly `n`, no rounding.
`new ArrayList<>(0)` and `new ArrayList<>()` both measure capacity **0** before the first
`add`, but point at two different shared empty arrays (`EMPTY_ELEMENTDATA` versus
`DEFAULTCAPACITY_EMPTY_ELEMENTDATA`) — file 05 explains why that distinction exists and how
it changes the first `add`. Negative capacity throws
`IllegalArgumentException("Illegal Capacity: " + n)` immediately.

A QuizStakes stake reservation always produces exactly four `LedgerEntry` rows — debit
`CLIENT_CASH_AVAILABLE` and `CLIENT_BONUS_AVAILABLE`, credit `CLIENT_CASH_RESERVED` and
`CLIENT_BONUS_RESERVED`:

```java
record LedgerEntry(String position, java.math.BigDecimal amount) {}

List<LedgerEntry> stakeReservedEntries = new ArrayList<>(4);
stakeReservedEntries.add(new LedgerEntry("CLIENT_CASH_AVAILABLE", debitCash));
stakeReservedEntries.add(new LedgerEntry("CLIENT_BONUS_AVAILABLE", debitBonus));
stakeReservedEntries.add(new LedgerEntry("CLIENT_CASH_RESERVED", creditCash));
stakeReservedEntries.add(new LedgerEntry("CLIENT_BONUS_RESERVED", creditBonus));
```

`new ArrayList<>(4)` wastes nothing; `new ArrayList<>()` over-allocates to 10 — six wasted
reference slots per `Movement`, and the ledger posts roughly 19.8M entries a day (Appendix
A.3), so it's a standing tax with no offsetting benefit since the size was known throughout.
The cost is measured: 100 000 sequential `add` calls take **584 µs** on `new ArrayList<>()`
and **358 µs** on `new ArrayList<>(100000)`, a **39 %** saving from one constructor argument.
The escape hatch when the size arrives *after* construction is `ensureCapacity(int)` — see
the pitfall below for its one surprising guard clause.

**Gotcha.** `new ArrayList<>(size)` where `size` comes from a subtraction that can go negative
throws `IllegalArgumentException` at construction — a crash far from its real cause if the
call is buried in a factory method.

> **Definition.** The two non-collection constructors differ only in eagerness:
> `ArrayList(int)` allocates now, `ArrayList()` defers until the first mutation.

---

### The collection constructor's exact-class fast path

**Mental model.** `new ArrayList<>(c)` looks like it always copies `c`'s elements into a new
array. It doesn't — it adopts `c`'s own array outright when it can prove that's safe, and
copies only when it can't.

**Why it exists.** If `c` is itself a plain `ArrayList`, its `toArray()` already allocates a
fresh `Object[]` nobody else references. Copying that array again would be a second
allocation and a second `arraycopy` for no safety benefit.

**When it applies, and when it does not.** Only when `c.getClass() == ArrayList.class` — a
plain `ArrayList`, not a subclass, not `LinkedList`, not `List.of(...)`, not
`Arrays.asList(...)`. Everything else takes the copying branch, because its `toArray()` result
might still be aliased elsewhere.

**How it works.** Quoted verbatim, lines 97–109:

```java
public ArrayList(Collection<? extends E> c) {
    Object[] a = c.toArray();
    if ((size = a.length) != 0) {
        if (c.getClass() == ArrayList.class) {
            elementData = a;
        } else {
            elementData = Arrays.copyOf(a, size, Object[].class);
        }
    } else {
        // replace with empty array.
        elementData = EMPTY_ELEMENTDATA;
    }
}
```

`c.getClass() == ArrayList.class` is an **exact class test**, deliberately not `instanceof`:
a subclass could override `toArray()` to return an array still referenced elsewhere, which
`instanceof` would let slip through the no-copy path. An empty source lands on
`EMPTY_ELEMENTDATA`, **not** `DEFAULTCAPACITY_EMPTY_ELEMENTDATA` — so
`new ArrayList<>(List.of())` grows to capacity 1 on its first `add`, following the
`new ArrayList<>(0)` sequence, not the default-10 sequence.

This constructor is `Q-12`'s cleanest guarantee: declared on `ArrayList`, invoked with `new`,
statically and dynamically `ArrayList<E>` — no refactor changes that. Contrast
`Collectors.toList()` below, which returns the same class today but promises nothing. So
`new ArrayList<>(List.copyOf(bankWithdrawalApprovals))` always takes the copying branch —
`List.copyOf`'s result is never `ArrayList.class` — and the two lists never alias.

**Gotcha.** The fast path adopts the array itself, not just its contents — sound only because
nothing else holds a reference to the transient array `c.toArray()` produced.

> **Definition.** `new ArrayList<>(c)` copies elements only when it cannot prove the source's
> backing array is exclusively its own to give away.

---

### Which routes give you a real `ArrayList`, and which only look like one

**Mental model.** `List<X>` is a contract, not a class. Nine expressions that all type-check
as `List<X>` compile to nine different runtime classes with different mutation rules — the
compiler enforces none of the differences.

**Why it exists.** `List.of`, `Arrays.asList`, and `Stream.toList` all hand back something
list-shaped without paying for a mutable `ArrayList` the caller won't mutate. Conflating any
of them with `ArrayList` is where `UnsupportedOperationException` comes from at runtime
instead of a compile error.

**When it applies, and when it does not.** If downstream code calls `add`, `remove`,
`removeIf`, or `sort`, only rows 1–5 above are safe. If the list is read-only from the moment
it's built, `Collections.unmodifiableList` or an immutable factory is cheaper and enforces
the guarantee instead of merely intending it.

**How it works.** Two facts, both measured on JDK 21.0.7. First, `stream().toList()` and
`stream().collect(Collectors.toList())` read as interchangeable and are not — `toList()`
returns `ImmutableCollections$ListN`; `Collectors.toList()` returns `java.util.ArrayList`:

```java
List<String> immutable = approvedRunIds.stream().toList();
immutable.add("BR-9911");
// -> java.lang.UnsupportedOperationException

List<String> mutable = approvedRunIds.stream()
        .collect(java.util.stream.Collectors.toList());
mutable.add("BR-9911"); // succeeds
```

Second, `Arrays.asList(arr)` returns `Arrays$ArrayList`, a fixed-size wrapper *over the array
you passed in*: `set` works and writes through to `arr`; `add`/`remove` throw because the
backing store cannot change length:

```java
String[] instrumentIds = {"AA-610", "AA-620"};
List<String> wrapped = Arrays.asList(instrumentIds);
wrapped.set(0, "AA-611");     // succeeds — instrumentIds[0] is now "AA-611"
wrapped.add("AA-630");
// -> java.lang.UnsupportedOperationException
```

**Gotcha.** `Collectors.toList()` returning a mutable `ArrayList` is a fact about the current
implementation, not a promise (`Q-12`): guaranteed today, not by contract, which reserves the
right to change the type's identity, mutability, serializability, or thread-safety. Code that
structurally relies on `ArrayList` should call `Collectors.toCollection(ArrayList::new)`
instead — that *is* a guarantee. Separately, `List.of("x", null)` throws
`NullPointerException`; an `ArrayList` happily stores `null`.

> **Definition.** `List<X>` tells you what operations compile; only the runtime class tells
> you which ones survive a call.

---

### `clone` and deserialization as construction

**Mental model.** `clone()` and Java serialization's `readObject` are both, mechanically,
constructors that never call a constructor — they allocate an `ArrayList` and populate its
fields directly, bypassing all three declared constructors.

**Why it exists.** `Cloneable` and `Serializable` predate the collection constructor as a copy
idiom; serialization still matters as how a `PaymentRun`'s item list survives a disk write or
a boundary crossing and comes back with its exact class intact.

**When it applies, and when it does not.** Use `clone()` only when an `ArrayList`-typed
shallow duplicate is specifically needed despite its awkward, unchecked-cast API —
`new ArrayList<>(original)` does the same job with a checked type. Serialization applies only
across a boundary that requires it.

**How it works.** `clone()`, quoted verbatim, lines 712–722:

```java
public Object clone() {
    try {
        ArrayList<?> v = (ArrayList<?>) super.clone();
        v.elementData = Arrays.copyOf(elementData, size);
        v.modCount = 0;
        return v;
    } catch (CloneNotSupportedException e) {
        throw new InternalError(e);
    }
}
```

`clone()` is shallow — elements are shared, only the backing array is duplicated — allocates
at `size`, not the original's capacity (a clone is always shrink-to-fit), and resets
`modCount` to 0, independent of the original's mutation count. It returns `Object`, so callers
need `(ArrayList<LedgerEntry>) source.clone()`; `new ArrayList<>(source)` gives the same
result with no unchecked cast, which is why `clone()` survives mostly as legacy.

Deserialization does the analogous job for a `PaymentRun`'s persisted items — a bank payout
file carries roughly 1 800 records (Appendix A.5). `writeObject` writes `size` elements, not
capacity-many, and `readObject` allocates exactly `new Object[size]`:

```java
private void readObject(java.io.ObjectInputStream s)
    throws java.io.IOException, ClassNotFoundException {
    s.defaultReadObject();
    s.readInt(); // ignored — historically "capacity", kept for clone() compatibility
    if (size > 0) {
        Object[] elements = new Object[size];
        for (int i = 0; i < size; i++) elements[i] = s.readObject();
        elementData = elements;
    } else if (size == 0) {
        elementData = EMPTY_ELEMENTDATA;
    } else {
        throw new java.io.InvalidObjectException("Invalid size: " + size);
    }
}
```

A deserialized list's capacity is always exactly `size` — zero slack. `elementData` is
`transient` for exactly this reason: a `PaymentRun` item list at capacity 2 000 holding 1 800
items serializes 1 800 objects, never the slack. Both `clone()` and deserialization
**guarantee** the runtime class is `ArrayList` (`Q-12`): the class name travels in the
serialized stream, and `super.clone()` always returns the same runtime class it was called on.

**Gotcha.** Calling `clone()` on a variable declared `List<X>` doesn't compile — `Cloneable`
exposes no `clone()` on the interface, so the static type must already be `ArrayList<X>`.
`new ArrayList<>(source)` accepts any `Collection<? extends X>` instead.

> **Definition.** `clone()` and deserialization both build an `ArrayList` by direct field
> assignment, shrink-to-fit at `size`, with no constructor in the call path.

---

## Pitfalls

### "`stream().toList()` and `Collectors.toList()` are the same call"

**Wrong**
```java
List<String> ids = pendingRunIds.stream().toList();
ids.removeIf(id -> id.startsWith("TEST"));
// -> java.lang.UnsupportedOperationException
```

**Right**
```java
List<String> ids = pendingRunIds.stream()
        .collect(java.util.stream.Collectors.toList());
ids.removeIf(id -> id.startsWith("TEST")); // succeeds
```

**Why people believe it:** both read as "give me a `List` from this stream" and solve the
same collecting problem — nothing at the call site signals that one is the JDK-16 addition
returning an immutable snapshot and the other predates it, returning a mutable `ArrayList`.

### "The collection constructor always copies"

**Wrong belief:** `new ArrayList<>(source)` always produces a new array, so mutating the
result can never affect anything `source`'s array still points at.

**Right:** when `source.getClass() == ArrayList.class` the array itself is adopted, not
copied — safe only because nothing else references that transient array. For any other
source type the copying branch runs and the belief happens to hold.

**Why people believe it:** "constructor" implies "fresh state," true for every non-`ArrayList`
source — the fast path is an internal optimisation invisible from the API.

### "`ensureCapacity` before a known-size loop always helps"

**Wrong**
```java
List<LedgerEntry> entries = new ArrayList<>();
entries.ensureCapacity(5); // "pre-sizing for speed"
```

**Right**
```java
List<LedgerEntry> entries = new ArrayList<>(5); // or ensureCapacity only above 10
```

**Why people believe it:** `ensureCapacity` sounds like a universal pre-sizing hint, but
measured on JDK 21.0.7, `new ArrayList<>().ensureCapacity(5)` leaves capacity at **0** — the
guard clause refuses to act when the array is the default-capacity sentinel and the request
is `<= DEFAULT_CAPACITY`, since the list grows to 10 on first `add` anyway.
`ensureCapacity(11)` does take effect.

## Cheat sheet

| Expression | Class | Capacity | Mutable | Guarantee |
|---|---|---|---|---|
| `new ArrayList<>()` | `ArrayList` | 0 → 10 on first add | yes | yes — constructor |
| `new ArrayList<>(n)` | `ArrayList` | `n` (0 if `n==0`) | yes | yes — constructor |
| `new ArrayList<>(c)` | `ArrayList` | `c.size()` | yes | yes — constructor |
| `list.clone()` | `ArrayList` | `size()` | yes, shallow | yes — same class as receiver |
| `.collect(Collectors.toList())` | `ArrayList` | unspecified | yes | **no** — impl detail, use `toCollection` |
| deserialization | `ArrayList` | `size()` | yes | yes — class travels in stream |
| `List.of(...)` / `copyOf` | `ImmutableCollections$*` | fixed | no | n/a |
| `Arrays.asList(arr)` | `Arrays$ArrayList` | fixed | fixed-size, write-through | n/a |
| `stream().toList()` | `ImmutableCollections$ListN` | fixed | no | n/a |
| `subList(from,to)` | `ArrayList$SubList` | n/a, view | yes, write-through | not `ArrayList`, not `Serializable` |

## Self-test

**Q1.** A stake-won movement always produces exactly four `LedgerEntry` rows. Which
constructor, and what's the cost of guessing wrong in either direction?

<details><summary>Answer</summary>

`new ArrayList<>(4)`. Guessing low forces at least one avoidable `grow` call even though the
size is known exactly — pure waste, not amortised cost. Guessing high wastes `n - size`
reference slots for the list's whole lifetime with no future growth to amortise against.

</details>

**Q2.** `new ArrayList<>(someList)` where `someList` is declared `List<String>` but its
runtime type is `LinkedList`. Adopted or copied? Why?

<details><summary>Answer</summary>

Copied. The fast path triggers only when `c.getClass() == ArrayList.class`, an exact test.
`LinkedList` fails it, so the constructor falls through to `Arrays.copyOf(a, size,
Object[].class)` on `someList.toArray()`.

</details>

**Q3.** Is code allowed to rely on `stream().collect(Collectors.toList())` always returning
`ArrayList` and cast the result?

<details><summary>Answer</summary>

No — it's an implementation detail, not a contract. The guaranteed way to get a specifically
`ArrayList`-typed result is `.collect(Collectors.toCollection(ArrayList::new))`.

</details>

**Q4.** What's the measured capacity of `new ArrayList<>()` before any `add`, and how does it
differ internally from `new ArrayList<>(0)`?

<details><summary>Answer</summary>

Both measure capacity 0. They point at two different shared empty arrays —
`DEFAULTCAPACITY_EMPTY_ELEMENTDATA` versus `EMPTY_ELEMENTDATA` — which changes what capacity
the first `add` grows to. File 05 covers the mechanism.

</details>

**Q5.** Why does the collection constructor test `c.getClass() == ArrayList.class` instead of
`c instanceof ArrayList`?

<details><summary>Answer</summary>

A subclass could override `toArray()` to return an array still referenced elsewhere.
`instanceof` would let that subclass take the no-copy path and alias state with whatever else
holds the array. The exact-class test only shortcuts when the source is provably plain
`ArrayList`, whose `toArray()` is known to always allocate fresh.

</details>

---

**Questions answered:** Q-11, Q-12, Q-13
**Sets up:** Next: the three fields and one arithmetic expression that everything so far actually rests on.
**Diagrams included:** D-04
**Target version:** Java 21 LTS
**Lines:** 424
