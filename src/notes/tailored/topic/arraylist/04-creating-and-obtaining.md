# ArrayList — 04 Creating and Obtaining

**Target version: Java 21.** | [Map](00-map.md)
Assumes: the member surface (file 03).
Previous: [03-the-complete-surface.md](03-the-complete-surface.md) · Next: [05-fields-and-the-backing-array.md](05-fields-and-the-backing-array.md)

There are exactly three ways to build an `ArrayList` and at least seven more ways
to obtain something `List`-shaped from existing data. Before touching any of
them, decide what you actually need: a fresh mutable container sized for a known
count, a container sized for an unknown count that will probably stay small, or
a read-only or fixed-size wrapper over data you already have. Getting that
decision wrong is either wasted allocation or a runtime surprise, and both are
covered below.

### The three constructors

A backend engineer reaches for `new ArrayList<>()` by reflex. That reflex hides
a real decision, and the JDK gives you three distinct routes with three distinct
costs.

**Why it exists.** `ArrayList` needs a backing array from the moment it exists,
but the caller rarely knows the eventual size at construction time — and even
when they do, the naive "always allocate `DEFAULT_CAPACITY`" design would waste
memory on every empty or near-empty list an application creates, of which there
are usually millions (one per aggregate, one per DTO field, one per short-lived
collector).

**When each applies.** `ArrayList()` when you don't know the size and the list
might stay empty or small. `ArrayList(int)` when you know — or can estimate —
the final size at construction. `ArrayList(Collection)` when you're building
from data you already have in hand.

**How it works.** The real JDK 21 source for all three:

```java
public ArrayList(int initialCapacity) {
    if (initialCapacity > 0) {
        this.elementData = new Object[initialCapacity];
    } else if (initialCapacity == 0) {
        this.elementData = EMPTY_ELEMENTDATA;
    } else {
        throw new IllegalArgumentException("Illegal Capacity: "+ initialCapacity);
    }
}

public ArrayList() {
    this.elementData = DEFAULTCAPACITY_EMPTY_ELEMENTDATA;
}

public ArrayList(Collection<? extends E> c) {
    Object[] a = c.toArray();
    if ((size = a.length) != 0) {
        if (c.getClass() == ArrayList.class) {
            elementData = a;
        } else {
            elementData = Arrays.copyOf(a, size, Object[].class);
        }
    } else {
        elementData = EMPTY_ELEMENTDATA;
    }
}
```

`ArrayList()` allocates **nothing**. It assigns a shared static empty array and
returns — an empty default-constructed list costs no element storage at all,
just the 24-byte shell (fields, no array body). That is the whole reason this
constructor is cheap to call by the million.

`ArrayList(int initialCapacity)` allocates exactly that many slots up front. The
negative branch throws `IllegalArgumentException`, and the message shape is
exact — verified: `new ArrayList<>(-1)` throws
`IllegalArgumentException: Illegal Capacity: -1`. Zero is not an error; it takes
the `EMPTY_ELEMENTDATA` sentinel path, covered next.

`ArrayList(Collection<? extends E> c)` is the interesting one. It calls
`c.toArray()` and then makes a **type-safety decision**: if the source
collection's runtime class is *exactly* `ArrayList.class`, the returned array is
adopted directly, no copy. For anything else — a `LinkedList`, a `HashSet`, a
third-party `List` implementation, even an `ArrayList` subclass — it re-copies
through `Arrays.copyOf(a, size, Object[].class)`.

**Insight:** the re-copy exists because `Collection.toArray()` is not guaranteed
to return an `Object[]`. A collection can legally back its `toArray()` with a
more specific array type (this shows up with covariant or badly-behaved
implementations), and storing an arbitrary `E` into that array later would throw
`ArrayStoreException` — far from the constructor call that caused it. Forcing
`Arrays.copyOf(a, size, Object[].class)` guarantees the internal array really is
an `Object[]`, closing that hole for every source except the one type
(`ArrayList` itself) the JDK trusts to already behave. This is a real historical
bug class and a strong interview answer: "why does the collection constructor
check `getClass() == ArrayList.class` instead of `instanceof ArrayList`?" —
because a subclass could override `toArray()` and hand back something unsafe;
only the exact class is trusted.

Cost of each route: `ArrayList()` is O(1), zero bytes of element storage.
`ArrayList(int n)` is O(n) to zero-initialize the array, one allocation.
`ArrayList(Collection c)` is O(n) for `c.toArray()` plus, in the common case, a
second O(n) copy — two full passes over the data, not one.

```java
List<LedgerEntry> fromScratch = new ArrayList<>();
List<LedgerEntry> presized    = new ArrayList<>(4);
List<LedgerEntry> fromExisting =
    new ArrayList<>(existingLinkedListOfEntries); // always copies: not ArrayList.class
```

**Pitfall:** assuming `ArrayList(Collection)` is always a single pass. If the
source is a `LinkedList` or any non-`ArrayList` `List`, you pay for `toArray()`
*and* `Arrays.copyOf`.

> An `ArrayList(Collection)` constructor call is one array read pass, plus a
> second defensive copy pass unless the source's runtime class is exactly
> `ArrayList` — a narrow trust boundary that exists solely to prevent a later
> `ArrayStoreException`.

### The two empty-array sentinels and lazy allocation

This is the piece that makes the constructors above actually cheap, and it is
the most commonly misunderstood detail of `ArrayList`.

**Mental model.** There are two distinct static `Object[]` instances, both
literally `{}`, both length zero, but **not the same object**:

```java
private static final Object[] EMPTY_ELEMENTDATA = {};
private static final Object[] DEFAULTCAPACITY_EMPTY_ELEMENTDATA = {};
```

Think of them as two different colored empty boxes that look identical from the
outside. `ArrayList()` picks up the "default" colored box; `ArrayList(0)` picks
up the other. Nothing about calling `size()` or `isEmpty()` or printing the list
tells you which box you're holding — the difference is invisible until the list
grows.

**Why it exists.** The JDK wants two things that are in tension: (1) creating an
empty list must cost nothing, because applications create huge numbers of lists
that end up empty or tiny, and (2) a *default-constructed* list that does start
getting elements should jump straight to a sensible starting capacity
(`DEFAULT_CAPACITY = 10`) rather than growing one slot at a time from zero — but
a list explicitly constructed with capacity zero asked for exactly that, and
should be taken at its word: its first growth should be sized for what's being
added, not silently bumped to 10. Two identical-looking empty arrays is the
cheapest way to carry that one bit of information — "which kind of empty am I"
— without adding a boolean field to every `ArrayList` instance. The cost of
carrying that bit this way is a single identity comparison (`==`) against a
static field — effectively free, no extra memory per instance.

**How it works.** `grow()` (mechanism handed to file 06 in full — the 1.5x
factor is not explained here) makes exactly this test:

```java
if (oldCapacity > 0 || elementData != DEFAULTCAPACITY_EMPTY_ELEMENTDATA) {
    // normal growth path
} else {
    return elementData = new Object[Math.max(DEFAULT_CAPACITY, minCapacity)];
}
```

If the current array is empty *and* it is specifically the default-constructed
sentinel, the first real allocation jumps to `DEFAULT_CAPACITY` (10). If the
current array is empty because the caller explicitly asked for capacity 0, that
`==` check fails (wrong sentinel), so it falls into the normal growth branch and
grows to exactly what's needed for the incoming element — 1, not 10.

**The demonstration — verified, real output on JDK 21.0.7:**

```java
List<String> defaultCtor = new ArrayList<>();
defaultCtor.add("AO-100");
// capacity 10

List<String> zeroCtor = new ArrayList<>(0);
zeroCtor.add("AO-100");
// capacity 1
```

```
new ArrayList<>()  then one add  ->  capacity 10
new ArrayList<>(0) then one add  ->  capacity 1
```

Both lists are, from the outside, identical after construction: size 0, empty,
`equals()` each other. Their behavior on the very next `add` diverges by an
order of magnitude in allocated capacity, purely because of which static array
they were handed. That divergence is the entire reason two sentinels exist —
one boolean's worth of information, encoded as object identity.

**Interview:** "Why does `new ArrayList<>()` behave differently from
`new ArrayList<>(0)`?" — Because they hold different static empty-array
sentinels; `grow()` special-cases the default sentinel to jump to
`DEFAULT_CAPACITY` (10) on first growth, while the explicit-zero sentinel grows
normally, i.e., to exactly what's needed. The bug people actually hit: treating
the two as interchangeable "give me an empty list" calls, then being surprised
that presizing to save memory (`new ArrayList<>(0)`) didn't behave like the
plain default when elements start arriving.

> Two structurally identical empty `Object[]` sentinels let `ArrayList` defer
> allocation to the first `add` while still remembering, for free, whether the
> caller asked for "default" or "exactly zero" — the difference surfaces the
> instant the list grows.

### Copy versus view among `List` sources

There are more than three ways to get a `List` out of existing data, and the
single most important thing to know about each is whether it's a **copy**
(mutating the source leaves it untouched) or a **view** (mutating the source
changes what you're holding).

| Source | Copy or view | Mutable | Null-tolerant | Cost |
|---|---|---|---|---|
| `new ArrayList<>(c)` | copy | yes | yes | O(n), possibly two passes (see above) |
| `List.copyOf(c)` | copy | **no** | **no** — throws `NullPointerException` on a null element | O(n) |
| `Arrays.asList(a)` | **view** over the array | fixed-size — `set` works, `add`/`remove` throw | yes | O(1), no copy |
| `List.of(...)` | copy, no reachable backing store | no | no | O(n) |
| `subList(from, to)` | **view** over the parent's array (file 09) | mutable through the view | inherits parent | O(1) to create |
| `clone()` | shallow copy — new array, same element references | yes | inherits source | O(n) |
| `reversed()` (since 21) | **view** | mutable through the view | inherits source | O(1) to create |
| `stream().toList()` | copy, immutable | no | no | O(n) |
| `Collectors.toList()` | copy, mutability **unspecified by contract** | not guaranteed | usually yes in practice | O(n) |
| `Collectors.toCollection(ArrayList::new)` | copy, guaranteed `ArrayList` | yes | yes | O(n) |

**The trap, with real verified output:**

```
Arrays.asList("DEP-301","DEP-400").add("X")     -> java.lang.UnsupportedOperationException
Arrays.asList("DEP-301","DEP-400").set(0,"X")   -> succeeds -> [X, DEP-400]
List.of("DEP-301","DEP-400").set(0,"X")         -> java.lang.UnsupportedOperationException
```

`Arrays.asList` is **fixed-size, not immutable**: `set` mutates the backing
array in place and succeeds, while `add`/`remove` would change the array's
length, which the view cannot do, so those throw. People call it "immutable"
because `add` fails, then get burned when `set` silently succeeds and mutates
something they thought was frozen. `List.of` is the genuinely immutable one —
every mutator throws, `set` included.

**The rule for telling copy from view without reading documentation:** mutate
the source and read the derived thing. If the derived thing changes, it's a
view; if it doesn't, it's a copy.

```java
List<LedgerEntry> ledgerCopy = List.copyOf(movement.entries());
List<LedgerEntry> ledgerView = movement.entries().reversed();
// mutate movement.entries() is impossible (append-only, no setters) —
// but for a plain ArrayList source this is the test:
List<String> src = new ArrayList<>(List.of("BDP-100", "BDP-200"));
List<String> view = src.reversed();
src.set(0, "BDP-999");
// view now reads [BDP-200, BDP-999] — a view, confirmed by the mutation
```

For `Movement.entries()`, which the domain declares an immutable append-only
list, `List.copyOf(builtEntries)` at construction is the correct route — it
gives a genuinely immutable list, not merely a reference nobody promised not to
mutate.

**Pitfall:** treating `Collectors.toList()` as a guarantee of a mutable
`ArrayList`. The `Collector` contract does not promise any particular
implementation or mutability — current JDKs happen to return a mutable
`ArrayList`, but code that needs a guaranteed mutable `ArrayList` should write
`Collectors.toCollection(ArrayList::new)` instead, which pins both the type and
the mutability.

> A `List` obtained from existing data is either a **copy** — safe to mutate
> independently — or a **view** — mutations on either side are mutations on
> both; the only way to tell them apart from the outside is to mutate one side
> and read the other.

### Observing capacity from outside

Capacity — `elementData.length` — is not exposed by any public method. That is
deliberate: capacity is an implementation detail of *how* the list stores its
elements, not part of what a `List` promises to any caller.

**When it applies.** You want to observe capacity when you're diagnosing memory
retention (a list that grew huge and never shrank), tuning a presizing decision,
or teaching/learning the growth mechanism — not in production business logic.

**How it works.** Since there's no public accessor, the only way to see it is
reflection on the package-private `elementData` field:

```java
import java.lang.reflect.Field;
import java.util.ArrayList;

final class CapacityProbe {
    static int capacityOf(ArrayList<?> list) throws ReflectiveOperationException {
        Field elementData = ArrayList.class.getDeclaredField("elementData");
        elementData.setAccessible(true);
        return ((Object[]) elementData.get(list)).length;
    }

    public static void main(String[] args) throws ReflectiveOperationException {
        var presized = new ArrayList<LedgerEntry>(4);
        System.out.println(capacityOf(presized)); // 4
    }
}
```

Run with the module system's opening flag, since `java.util` is not open by
default in JDK 21:

```
java --add-opens java.base/java.util=ALL-UNNAMED CapacityProbe
```

Verified real run confirming a specific growth step: `new ArrayList<>(4)`, then
five `add` calls, produces capacity **6** — `4 + (4 >> 1) = 6` — because five
elements overflow capacity 4 on the fifth add, triggering exactly one growth
step from the presized base (the 1.5x arithmetic itself belongs to file 06).

**Insight:** `--add-opens` is required precisely because the JDK module system
closed `java.util`'s internals in strong encapsulation — this reflection call
is fighting the platform's own boundary, not working with it.

**The honest framing:** this is a diagnostic and teaching tool, not production
code. Depending on `setAccessible(true)` plus a runtime `--add-opens` flag in
application code is a maintenance liability — a future JDK is free to rename or
restructure `elementData`, and your code breaks with no compiler warning. If
you actually need capacity control in production, that's what `ensureCapacity`
and `trimToSize` are for — size correctly at construction instead of
inspecting internal state afterward.

> Capacity has no public accessor by design; the only way to observe it is
> reflection past the module system's own encapsulation, which is why it
> belongs in a probe, never in shipped code.

---

`ensureCapacity(int n)` grows the backing array to at least `n` slots in one
step, ahead of a batch of adds, so each add doesn't independently trigger
`grow()`. Its real guard: if the list is still holding the default-empty
sentinel and `n <= DEFAULT_CAPACITY`, the call is a no-op — `ensureCapacity(5)`
on a fresh `new ArrayList<>()` does nothing.

`trimToSize()` shrinks the backing array down to exactly `size`, discarding
slack. Verified: a list at capacity 109 holding 100 elements becomes capacity
100 after `trimToSize()`. It bumps `modCount`, so an iterator or `sort` in
progress will see it as a structural modification.

**Pitfall:** believing `clear()` frees the backing array. Verified: a list at
capacity 100 stays at capacity 100 after `clear()` — size drops to 0, but every
slot's reference is merely nulled out, not the array itself. A list that
briefly held the 500,000-record month-end bank statement file keeps a
500,000-slot array alive until you either call `trimToSize()` or drop the
reference entirely, even though it reports `size() == 0`. That is a real
retention bug in long-lived caches or reused buffers, not a theoretical one.

### Presizing decisions from the domain

**Presizing `Movement.entries`.** A movement holds 2 to 4 `LedgerEntry`
records — never more. `new ArrayList<>()` growing to 10 wastes 6 to 8 slots on
every one of roughly 4.95 million movements posted per day; `new ArrayList<>(4)`
allocates exactly what's needed. Since the entries are fixed once assembled,
wrap the result in `List.copyOf(builtEntries)` — copy, not view, genuinely
immutable, unlike `Arrays.asList`.

**Bulk-loading the bank statement file.** The daily ingestion reads 40,000
records normally, 500,000 at month end. If the record count is known before
the read loop (a header line, a fixed batch size),
`ensureCapacity(expectedCount)` or constructing with
`new ArrayList<>(expectedCount)` avoids roughly a dozen intermediate `grow()`
calls, each a full `System.arraycopy` of everything read so far.

## Pitfalls

### Believing `new ArrayList<>()` allocates ten slots immediately

**Wrong**
```java
var list = new ArrayList<String>();
// assuming: backing array is already Object[10] here
```
Reflecting on `elementData` immediately after construction shows a zero-length
array — specifically the shared `DEFAULTCAPACITY_EMPTY_ELEMENTDATA` sentinel,
not a 10-slot array.

**Right**
No allocation happens until the first `add`. `DEFAULT_CAPACITY` (10) is only
realized then, and only because the sentinel identity check in `grow()` detects
this is a default-constructed list.

**Why people believe it:** `DEFAULT_CAPACITY = 10` is well known and widely
quoted, and it's natural to assume the constructor that "uses" it applies it
eagerly, the way `ArrayList(int)` does.

### Believing `new ArrayList<>(0)` and `new ArrayList<>()` are interchangeable

**Wrong**
```java
var a = new ArrayList<String>();
var b = new ArrayList<String>(0);
// treating a and b as equivalent "give me an empty list" calls
a.add("x"); // capacity becomes 10
b.add("x"); // capacity becomes 1 — surprising if you expected symmetry
```

**Right**
They hold different empty-array sentinels. `a` inflates to `DEFAULT_CAPACITY`
on first growth; `b` grows to exactly what's needed, because it explicitly
opted out of the default via capacity `0`. Choose `ArrayList(0)` deliberately
when you expect the list to very likely stay empty and want to avoid the
10-slot default even on first growth.

**Why people believe it:** both print as `[]`, both report `size() == 0` and
`isEmpty() == true`; nothing about the list's observable state before the
first `add` distinguishes them.

### Believing `Arrays.asList` returns something immutable

**Wrong**
```java
List<String> codes = Arrays.asList("DEP-301", "DEP-400");
codes.set(0, "DEP-999"); // succeeds — surprising if you expected "immutable"
codes.add("BDP-100");    // throws UnsupportedOperationException
```

**Right**
`Arrays.asList` is a **fixed-size view** over the array you passed in, not an
immutable list. `set` is allowed because it doesn't change the array's length;
`add`/`remove` throw because they would. For genuine immutability use
`List.of(...)` or `List.copyOf(...)`, both of which reject every mutator.

**Why people believe it:** the class name and its common pairing with "don't
modify this" advice in tutorials make it read as a general-purpose immutable
wrapper, when it's specifically a thin `List` adapter over a fixed-length array.

### Believing `clear()` frees the backing array

**Wrong**
```java
List<String> bulk = new ArrayList<>();
loadFiveHundredThousandRecords(bulk); // capacity grows to ~500k
bulk.clear();
// assuming bulk now holds a tiny or empty backing array
```

**Right**
`clear()` nulls every live slot's reference so the elements become eligible for
GC, but the backing array itself — all 500,000 slots — is untouched and stays
retained as long as the `ArrayList` object is reachable. Call `trimToSize()`
after `clear()` if the large capacity must actually be released, or drop the
reference to the list entirely.

**Why people believe it:** "clearing" a collection reads as "resetting it to
its initial state," and for a freshly constructed list that's true — but a
list that grew large doesn't return to that initial state on `clear()`.

### Believing `Collectors.toList()` guarantees a mutable `ArrayList`

**Wrong**
```java
List<LedgerEntry> entries = movements.stream()
    .flatMap(m -> m.entries().stream())
    .collect(Collectors.toList());
entries.add(extraEntry); // works today, on this JDK's current implementation
```

**Right**
The `Collector` returned by `Collectors.toList()` makes no contractual promise
about mutability or concrete type — only that it's a `List`. Code that needs a
guaranteed mutable `ArrayList` should write
`Collectors.toCollection(ArrayList::new)`, which pins both facts explicitly
instead of relying on current implementation behavior.

**Why people believe it:** every current JDK happens to return a plain mutable
`ArrayList` from `Collectors.toList()`, so the difference between "guaranteed"
and "happens to be true" never surfaces until code is ported or the
implementation changes.

## Cheat sheet

| Route | Allocates now? | Result mutable? | Copy or view | Notes |
|---|---|---|---|---|
| `new ArrayList<>()` | no | yes | — | grows to 10 on first add |
| `new ArrayList<>(0)` | no (empty array, but the *other* sentinel) | yes | — | grows to exactly what's needed |
| `new ArrayList<>(n)`, n>0 | yes, n slots | yes | — | throws `IllegalArgumentException` if n<0 |
| `new ArrayList<>(c)` | yes | yes | copy | double pass unless `c.getClass()==ArrayList.class` |
| `List.copyOf(c)` | yes | no | copy | null-hostile |
| `Arrays.asList(a)` | no | fixed-size (`set` ok, `add`/`remove` throw) | view | over the array `a` |
| `List.of(...)` | yes | no | copy-like, no backing | fully immutable |
| `subList(from,to)` | no | yes | view | over parent's array (file 09) |
| `clone()` | yes | yes | shallow copy | same element refs, new array |
| `reversed()` | no | yes | view | since Java 21 |
| `stream().toList()` | yes | no | copy | |
| `Collectors.toList()` | yes | unspecified | copy | don't rely on mutability |
| `Collectors.toCollection(ArrayList::new)` | yes | yes, guaranteed | copy | pin type + mutability |
| `ensureCapacity(n)` | conditional | — | — | no-op if still default-empty and n≤10 |
| `trimToSize()` | shrinks | — | — | bumps `modCount` |
| observe capacity | — | — | — | reflection + `--add-opens java.base/java.util=ALL-UNNAMED` only |

## Self-test

**Q1.** Why does `new ArrayList<>(0)` followed by one `add` end up at capacity
1, while `new ArrayList<>()` followed by one `add` ends up at capacity 10?

<details><summary>Answer</summary>

They start from different static empty-array sentinels — `EMPTY_ELEMENTDATA`
for the explicit-zero constructor, `DEFAULTCAPACITY_EMPTY_ELEMENTDATA` for the
no-arg constructor. `grow()` checks identity against
`DEFAULTCAPACITY_EMPTY_ELEMENTDATA` specifically; only that sentinel triggers
the jump to `DEFAULT_CAPACITY` (10) on first growth. The explicit-zero sentinel
falls into the normal growth path, which sizes for exactly what's being added.

</details>

**Q2.** Why does `ArrayList(Collection<? extends E> c)` sometimes copy the
array returned by `c.toArray()` and sometimes adopt it directly?

<details><summary>Answer</summary>

It checks `c.getClass() == ArrayList.class`. If true, it trusts the returned
array is already a true `Object[]` and adopts it with no copy. Otherwise it
defensively re-copies via `Arrays.copyOf(a, size, Object[].class)`, because
`Collection.toArray()` is not guaranteed to return an `Object[]` for arbitrary
implementations — storing an incompatible element into an unexpectedly
narrower array type would throw `ArrayStoreException` later, far from this
constructor call.

</details>

**Q3.** Is `Arrays.asList(x, y, z)` mutable or immutable?

<details><summary>Answer</summary>

Neither label is fully correct. It's a fixed-size view over the array passed
in: `set` succeeds because it doesn't change the array's length, but `add` and
`remove` throw `UnsupportedOperationException` because they would. Calling it
"immutable" mispredicts that `set` will fail too.

</details>

**Q4.** A list held 500,000 records during a month-end batch job, then had
`clear()` called on it. What is its capacity now, and why does that matter?

<details><summary>Answer</summary>

Capacity stays at roughly 500,000 — `clear()` nulls the live slots' references
but never shrinks or reallocates the backing array. The list will retain a
500,000-slot `Object[]` for as long as it's reachable, which is a real memory
retention risk if the list is a long-lived field rather than a local variable.
`trimToSize()` after `clear()` is the fix, or dropping the reference entirely.

</details>

**Q5.** You call `ensureCapacity(5)` on a freshly constructed
`new ArrayList<>()`. What happens?

<details><summary>Answer</summary>

Nothing. The guard inside `ensureCapacity` checks whether the list is still
holding the default-empty sentinel and the requested capacity is at most
`DEFAULT_CAPACITY` (10); since 5 ≤ 10, the call is a no-op, because the list
would allocate at least 10 slots on its first growth anyway.

</details>

**Q6.** How would you find out, from outside the class, what an `ArrayList`'s
current capacity is — and why is there no public method for it?

<details><summary>Answer</summary>

There's no public accessor because capacity is an implementation detail, not
part of the `List` contract. The only route is reflection on the
package-private `elementData` field, run with
`--add-opens java.base/java.util=ALL-UNNAMED` since `java.util` is not open by
default. This is a diagnostic technique, not something to depend on in
production — use `ensureCapacity`/`trimToSize` or presize at construction
instead of inspecting internal state.

</details>

**Q7.** Why should `Movement.entries` be built with `new ArrayList<>(4)` rather
than `new ArrayList<>()`, and how should it be exposed once built?

<details><summary>Answer</summary>

A movement has 2 to 4 entries, never more, so `new ArrayList<>(4)` allocates
exactly what's needed instead of growing to 10 and wasting 6 to 8 slots on
every one of roughly 4.95 million movements posted per day. Once the entries
are assembled, wrap them with `List.copyOf(builtEntries)` before exposing them,
so the field is a genuine immutable copy rather than a mutable `ArrayList`
someone could still write to — matching the domain's append-only, no-setters
invariant.

</details>

---

**Questions answered:** Q-09, Q-10, Q-11, Q-12
**Sets up:** Next: the fields behind all of this — what an ArrayList actually is in memory.
**Diagrams included:** none
**Target version:** Java 21
**Lines:** 595
