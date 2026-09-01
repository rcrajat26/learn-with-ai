# 02 Java Collections — Immutability and views — INTERMEDIATE (§2.3.17–2.3.19)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [immutable-collections/02-immutable-factories.md](02-immutable-factories.md) · Next: [immutable-collections/02b-entries-snapshots-and-stream-terminals.md](02b-entries-snapshots-and-stream-terminals.md)

All source citations below are from JDK 21 `lib/src.zip`. All transcripts were produced on
**java 21.0.7+8-LTS-245, HotSpot 64-bit Server VM, macOS/aarch64 (Darwin 25.5.0)**.

The previous file established two orthogonal axes — *write-blocking* (does a mutator throw?)
and *isolation* (do the source's later mutations show through?). This file adds a third that no
factory addresses: **depth** — can the *elements* still change? That is settled by the element
type, never by the collection.

---

## Shallow vs deep immutability (§2.3.17) `[TRAP]`

**Mental model.** An immutable collection freezes the *arrows*, never the *boxes*. `List.of`
guarantees that slot 0 will always point at the same object. It guarantees nothing whatsoever
about that object's contents.

**Why it matters.** Immutability is usually adopted for a downstream property — safe sharing
across threads, safe use as a `HashMap` key, safe caching. Every one of those properties needs
*deep* immutability. A shallowly immutable list of mutable elements delivers none of them
while looking, in code review, exactly like the safe thing.

**When to reach for it (and when not).** `List.of` is sufficient when the elements are
themselves immutable — `String`, boxed primitives, `LocalDate`, records with only immutable
components, enums. When elements are mutable, the sibling that actually wins is a copy at the
element level: `list.stream().map(Element::copy).toList()`, or better, make the element type
immutable.

**Mechanism.** There is nothing to explain in the collection: `ListN.elements` is
`private final E[]` (`ImmutableCollections.java:663-664`). `final` on an array field prevents
reassigning the field. It does not prevent `elements[0].mutate()`. No JVM mechanism can, short
of the element type refusing to expose mutators. The same is true of `List12`'s
`private final E e0` / `private final Object e1` (`ImmutableCollections.java:556-560`): the
fields are final, the objects they name are whatever their own types allow.

**Diagram:** none applies to this leaf — the mechanism is the absence of a mechanism, and D-38
(in `02-immutable-factories.md`) already carries the reference-vs-copy picture that would be
reused here.

**Example.** Two flavours: a plain mutable object, and the sharper case — a record, which
people assume is immutable.

```java
StringBuilder sb = new StringBuilder("hello");
List<StringBuilder> shallow = List.of(sb);
System.out.println("before append: " + shallow);
sb.append(", world");
System.out.println("after  append: " + shallow);
try {
    shallow.set(0, new StringBuilder("replaced"));
} catch (UnsupportedOperationException e) {
    System.out.println("shallow.set(0, ..) -> " + e.getClass().getName());
}

record Box(StringBuilder sb) {}
Box box = new Box(new StringBuilder("v1"));
List<Box> boxes = List.of(box);
box.sb().append("+v2");
System.out.println("record with mutable component: " + boxes);
```

Real output:

```
before append: [hello]
after  append: [hello, world]
shallow.set(0, ..) -> java.lang.UnsupportedOperationException
record with mutable component: [Box[sb=v1+v2]]
```

`set` throws — the list is structurally frozen. And yet the list's contents changed twice.
The record case is worse than the `StringBuilder` case because `record` reads as a guarantee:
`Box` is shallowly immutable (its `sb` field is `final`), the list is shallowly immutable, and
the whole thing is still mutable through `box.sb()`. Two layers of "immutable" compose to
"mutable".

**Pitfall:** *"`List.copyOf` gives me a safe snapshot."* **Symptom:** a cached or
cross-thread-shared "snapshot" whose element values drift after capture; a `HashSet<List<T>>`
where `contains` starts returning `false` for a list that is in it, because an element's
`hashCode` changed. **Fix:** copy the elements too. `List.copyOf(src)` copies references only:

```java
static class Counter { int n; public String toString() { return "Counter(" + n + ")"; } }

Counter c1 = new Counter();
List<Counter> counters = List.copyOf(List.of(c1));
c1.n = 42;
System.out.println("List.copyOf did not deep-copy: " + counters);
```

```
List.copyOf did not deep-copy: [Counter(42)]
```

`List.copyOf` returned the source instance here anyway (see §2.3.16 in the previous file), but
that is beside the point: even in the branch where it *does* allocate, the new array holds the
same element references. There is no deep-copy factory in `java.util`, and there cannot be —
the JDK does not know how to clone an arbitrary `E`.

**Insight:** immutability is a property of a *type*, propagated bottom-up. You cannot buy it at
the collection layer. The only way to get a deeply immutable `List<T>` is for `T` to be deeply
immutable, all the way down.

> **Definition.** Java's immutable collections are *shallowly* immutable: the set of element
> references is fixed, the state of the referenced objects is not, so deep immutability
> requires an immutable element type.

---

## Defensive copying at API boundaries (§2.3.18)

**Mental model.** Your getter is a contract about *time*. Returning a copy says "here is what
was true when you asked". Returning a view says "here is a window; keep looking and you will
see changes". Pick the one you meant, then say so in the javadoc.

**Why it exists.** A getter returning the field directly leaks control of your invariants: the
caller can `clear()` your collection, and no code in your class runs. The historical fix
(Bloch, *Effective Java*, Item 50) is "make defensive copies when needed", written before Java
had cheap immutable collections; today the same advice has a much cheaper implementation.

**When to reach for which.** This is the decision the leaf exists for. Three options, so a
table.

| Getter body | Caller sees later mutations? | Caller can mutate? | Allocation per call | Use when |
|---|---|---|---|---|
| `return field;` | yes | **yes** | none | never on a public API — *unless* the field is already an immutable collection, in which case this is the best answer |
| `return Collections.unmodifiableList(field);` | **yes** | no | one small wrapper object, no element copy, O(1) | caller *should* track your updates; collection is large; call is hot |
| `return List.copyOf(field);` | no (snapshot) | no | O(n) — one `toArray` plus one `ListN` array, so two arrays; **free** when `field` is already immutable | caller must not see later mutations; caller may hold the result long-term or across threads |

The decision rule, one line each:

- **Copy** when the caller must not observe your later mutations — the result may be cached,
  logged, sent to another thread, used as a map key, or held past the current call.
- **View** when the caller *should* observe your later mutations and you only want to block
  writes, or when O(n) per call is too expensive.
- **Neither** — the best option — when the field is *itself* an immutable collection.
  Then `return field;` is already safe, and `List.copyOf(field)` costs nothing because it
  returns `field` (see §2.3.16). Store immutable, return directly.

**Mechanism.** There is no new machinery here; the leaf is entirely a composition of the two
mechanisms from the previous file. `List.copyOf` snapshots because `listCopy` either returns an
already-immutable argument or builds a fresh array from `coll.toArray()`
(`ImmutableCollections.java:167-176`). `Collections.unmodifiableList` stays live because
`UnmodifiableList.get` forwards to the stored source reference
(`Collections.java:1491`, `1501`). Choosing between them *is* choosing between those two
implementations.

**Example.** The shapes side by side, with the constructor side also defended:

```java
final class Order {
    private final List<String> lineItems;          // immutable field: copy once, at construction

    Order(List<String> lineItems) {
        this.lineItems = List.copyOf(lineItems);   // caller cannot mutate our state later
    }

    List<String> lineItems() {
        return lineItems;                          // already immutable: no copy, no wrapper
    }
}

final class Cart {
    private final List<String> items = new ArrayList<>();   // genuinely mutable field

    void add(String item) { items.add(Objects.requireNonNull(item)); }

    /** Live, read-only window: reflects later {@link #add} calls. */
    List<String> liveItems() {
        return Collections.unmodifiableList(items);
    }

    /** Stable snapshot: unaffected by later {@link #add} calls. */
    List<String> snapshot() {
        return List.copyOf(items);
    }
}
```

Both getters on `Cart` are correct; they are correct about *different things*, and the javadoc
is doing real work. A reviewer cannot tell which one a caller needs — only the caller can.

**Insight:** the strongest version of this leaf is that defensive copying belongs in the
**constructor**, not the getter. `Order` copies once and then hands out the field forever at
zero cost. A class that copies in every getter is paying repeatedly for a mutable field it did
not need. Cheap immutable factories turned "defensive copy on every boundary crossing" into
"normalise to immutable once at the edge".

**Gotcha.** Neither option gives you depth or thread safety.
`Collections.unmodifiableList(field)` protects the *field*, not the *elements* (§2.3.17), and
it adds no synchronisation — a caller iterating the returned view while you `add` gets
`ConcurrentModificationException` from the underlying `ArrayList`'s iterator, which the view's
iterator wraps (`Collections.java:1073-1078`). `List.copyOf` performs its `toArray` in one
call, but `toArray` on an `ArrayList` is not atomic against a concurrent writer either, so it
can observe a torn size. For genuine concurrency use `CopyOnWriteArrayList`, or copy under the
same lock your writers take.

> **Definition.** At an API boundary, return `List.copyOf(field)` when the caller needs a
> snapshot, `Collections.unmodifiableList(field)` when the caller needs a live read-only
> window, and prefer an immutable field so the getter can return it directly.

---

## `Collections.singletonList` vs `List.of` (§2.3.19) `[TRAP]` `[RESEARCH]`

**Mental model.** `singletonList` is `List.of`'s Java 1.3 ancestor for exactly one element:
one field, no array, no wrapper. `List.of(x)`'s `List12` is the same idea rebuilt with two
extra properties — null-hostility, and `@Stable`-annotated fields the JIT can constant-fold.

**Why it exists.** Java 1.3 had no immutable collection framework, but single-element lists
were common enough (as method arguments, as `Collections.nCopies`-style constants) to justify a
dedicated one-field class rather than `new ArrayList<>(1)` plus a wrapper. `List.of(x)`
superseded it in Java 9.

**The syllabus claim, checked — and it is wrong.** The syllabus asserts that of
`Collections.singletonList` and `List.of`, *"one is mutable-via-`set`"*. **Neither is.**
`[SOURCE]`

```java
// Collections.java:5157-5167 (excerpted)
private static class SingletonList<E>
    extends AbstractList<E>
    implements RandomAccess, Serializable {

    @SuppressWarnings("serial") // Conditionally serializable
    private final E element;

    SingletonList(E obj)                {element = obj;}
```

Line by line: `SingletonList` is `private static` — you can only reach it through the factory
`Collections.singletonList` (`Collections.java:5150-5152`), so nobody can subclass it. It
extends `AbstractList`, which is the load-bearing fact. It stores the sole element in one
`private final E element` field — no array, so no per-element indirection and no array header.
The constructor does **not** null-check, which is why `singletonList(null)` is legal. And
critically, the class **does not override `set(int, E)`**, so the inherited implementation runs:

```java
// AbstractList.java:137-139
public E set(int index, E element) {
    throw new UnsupportedOperationException();
}
```

`AbstractList` provides `set` as an optional operation whose default is refusal — a subclass
that wants a settable list must override it. `SingletonList` does not, so `set` throws.
`add(int, E)` and `remove(int)` are likewise not overridden and likewise throw from
`AbstractList`. Verified by running it, both calls in try/catch:

```java
List<String> single = Collections.singletonList("a");
System.out.println("singletonList class = " + single.getClass().getName());
try {
    String old = single.set(0, "b");
    System.out.println("set SUCCEEDED, old=" + old + " now=" + single);
} catch (UnsupportedOperationException e) {
    System.out.println("singletonList.set(0,\"b\") -> " + e.getClass().getName());
}
try {
    List.of("a").set(0, "b");
} catch (UnsupportedOperationException e) {
    System.out.println("List.of(\"a\").set(0,\"b\")  -> " + e.getClass().getName());
}
```

```
singletonList class = java.util.Collections$SingletonList
singletonList.set(0,"b") -> java.lang.UnsupportedOperationException
List.of("a").set(0,"b")  -> java.lang.UnsupportedOperationException
```

Both throw. **The mutable-via-`set` single-element list the syllabus is thinking of is
`Arrays.asList(x)`**, whose `Arrays$ArrayList.set` writes through to the backing array — that
mechanism has its own file at
[01d-arrays-aslist.md](01d-arrays-aslist.md); read it there rather than re-deriving it. Do not
repeat the `singletonList` version of the claim in an interview.

**What the real differences are.** Two, and both are testable:

1. **Nulls.** `singletonList(null)` is legal and gives `[null]`, because the `SingletonList`
   constructor performs no check. `List.of(null)` throws NPE from the `List12` constructor's
   `Objects.requireNonNull` (`ImmutableCollections.java:563`).
2. **`sort`.** `SingletonList` overrides `sort` as an *empty method*
   (`Collections.java:5196-5198`): `@Override public void sort(Comparator<? super E> c) { }`
   — a silent no-op, on the reasoning that sorting one element cannot change anything.
   `List.of(...)` inherits `AbstractImmutableList.sort`, which throws
   (`ImmutableCollections.java:263`). This is the only asymmetry that could be mistaken for
   mutability, and it is not one: nothing changes, the call simply does not complain.

Note the contrast within `SingletonList` itself: `sort` is an empty override, but `removeIf`
(`Collections.java:5188-5191`) and `replaceAll` (`Collections.java:5192-5195`) are overridden
to **throw**. `replaceAll` could actually change the element, so it must refuse; `sort` cannot,
so it need not.

```java
System.out.println("singletonList(null) = " + Collections.singletonList(null));
try {
    System.out.println("List.of((String) null) = " + List.of((String) null));
} catch (NullPointerException e) {
    System.out.println("List.of((String) null) -> " + e.getClass().getName());
}
List<String> s2 = Collections.singletonList("a");
s2.sort(null);
System.out.println("singletonList.sort(null) did NOT throw; list = " + s2);
try {
    List.of("a", "b").sort(null);
} catch (UnsupportedOperationException e) {
    System.out.println("List.of(a,b).sort(null) -> " + e.getClass().getName());
}
System.out.println("List.copyOf(singletonList(\"a\")) class = "
        + List.copyOf(Collections.singletonList("a")).getClass().getName());
```

```
singletonList(null) = [null]
List.of((String) null) -> java.lang.NullPointerException
singletonList.sort(null) did NOT throw; list = [a]
List.of(a,b).sort(null) -> java.lang.UnsupportedOperationException
List.copyOf(singletonList("a")) class = java.util.ImmutableCollections$List12
```

The last line ties back to §2.3.16: `SingletonList` is neither `List12` nor `ListN`, so it
fails `listCopy`'s fast-path test and gets copied into a `List12` rather than returned as-is.

| | `Collections.singletonList(x)` | `List.of(x)` |
|---|---|---|
| Since | 1.3 | 9 |
| Class | `Collections$SingletonList` | `ImmutableCollections$List12` |
| Storage | one `private final E element` | `private final E e0` + `Object e1` sentinel |
| `x == null` | allowed, yields `[null]` | `NullPointerException` |
| `set`/`add`/`remove` | `UnsupportedOperationException` (inherited, `AbstractList`) | `UnsupportedOperationException` (`AbstractImmutableList`) |
| `sort(cmp)` | **silent no-op** (`Collections.java:5196-5198`) | `UnsupportedOperationException` (`ImmutableCollections.java:263`) |
| `replaceAll` | `UnsupportedOperationException` (`Collections.java:5192-5195`) | `UnsupportedOperationException` |
| `List.copyOf` returns it? | no — copies to `List12` | **yes, same instance** |
| `RandomAccess` | yes | yes |
| Serializable | yes | yes |

**When to reach for which.** Use `List.of(x)` in all new code. Reach for `singletonList` only
when you must represent a single `null` element, or when you are constrained to a pre-Java-9
source level. **Version trap:** engineers and interviewers who learned Java before 9 still
teach `singletonList` as *the* single-element idiom; the answer to give is "`List.of(x)` since
Java 9, `singletonList` only for the null case".

**Interview:** *"Which of `singletonList(x)` and `List.of(x)` can be modified?"* — Neither can
be structurally modified; `singletonList` accepts a null element and silently accepts `sort`
as a no-op, and the mutable single-element list you may be thinking of is `Arrays.asList(x)`.

> **Definition.** `Collections.singletonList(x)` and `List.of(x)` are both structurally
> immutable single-element lists; `singletonList` permits a null element and treats `sort` as a
> no-op, while `List.of` rejects nulls and rejects `sort`.

---

## Pitfalls

### Treating an immutable list of mutable objects as thread-safe

**Wrong**

```java
record Session(StringBuilder log) {}

static final List<Session> SESSIONS = List.of(new Session(new StringBuilder()));

// two threads, no synchronisation
SESSIONS.get(0).log().append("a");   // StringBuilder is not thread-safe
SESSIONS.get(0).log().append("b");   // torn state, possibly ArrayIndexOutOfBoundsException
```

The list is safely published and never changes shape, so the *list* is thread-safe. The element
is not, and the element is where the mutation happens.

**Right**

```java
record Session(String id, List<String> log) {}

static final List<Session> SESSIONS =
        List.of(new Session("s1", List.of()));       // deeply immutable

// mutation becomes replacement, not in-place edit
static Session withEntry(Session s, String entry) {
    return new Session(s.id(), Stream.concat(s.log().stream(), Stream.of(entry)).toList());
}
```

**Why people believe it:** "immutable objects are thread-safe" is a true rule, and `List.of`
plus `record` both read as immutability declarations. Both are shallow, and shallow plus
shallow composes to nothing.

### Believing `Collections.singletonList(x).set(0, y)` succeeds

**Wrong**

```java
List<String> one = Collections.singletonList("a");
one.set(0, "b");                       // "it's a mutable single-element list"
System.out.println(one);               // never reached
```

Throws `UnsupportedOperationException` from `AbstractList.set` (`AbstractList.java:137-139`),
because `Collections.SingletonList` (`Collections.java:5157-5159`) never overrides `set`.

**Right**

```java
// If you genuinely need a settable single-element list:
List<String> one = Arrays.asList("a");   // set writes through to the backing array
one.set(0, "b");
System.out.println(one);                 // [b]

// If you need an immutable one — the normal case:
List<String> fixed = List.of("a");       // Java 9+, rejects null
```

**Why people believe it:** `Arrays.asList(x)` and `Collections.singletonList(x)` are both
1.2/1.3-era single-element list factories that block *size* changes, so they get filed together
in memory. Only `Arrays.asList` is array-backed and therefore settable.

### Copying defensively in the getter instead of the constructor

**Wrong**

```java
final class Report {
    private final List<Row> rows;                 // mutable ArrayList handed in

    Report(List<Row> rows) { this.rows = rows; }   // caller keeps a live reference!

    List<Row> rows() { return List.copyOf(rows); } // O(n) on every single call
}
```

Two bugs in four lines. The constructor stored the caller's list, so the caller can still
mutate `Report`'s state. And the getter pays an O(n) copy per call to defend against a leak the
constructor created.

**Right**

```java
final class Report {
    private final List<Row> rows;

    Report(List<Row> rows) { this.rows = List.copyOf(rows); }  // copy once, at the edge

    List<Row> rows() { return rows; }                          // already immutable: free
}
```

**Why people believe it:** *Effective Java*'s "make a defensive copy" is remembered as advice
about getters, because the canonical example is a leaking getter. The rule is really "copy at
every boundary crossing" — and if you copy on the way *in*, there is no boundary left to defend
on the way out.

---

## Cheat sheet

| Question | Answer |
|---|---|
| Immutability depth of `List.of` / `copyOf` | **shallow** — element references frozen, element state not |
| Frozen by `List.of` | the arrows (which object each slot names) |
| Not frozen by `List.of` | the boxes (the state of those objects) |
| `record` + `List.of` | still mutable if a record component is mutable |
| Deep-copy factory in `java.util` | none exists; `T` must be immutable |
| Only route to deep immutability | an immutable element type, all the way down |
| Getter, caller needs a snapshot | `List.copyOf(field)` — O(n), two arrays |
| Getter, caller should track updates | `Collections.unmodifiableList(field)` — O(1) wrapper |
| Getter, field already immutable | `return field;` — zero cost, best answer |
| Where defensive copying belongs | the **constructor**, not the getter |
| Does either getter option give thread safety? | no — use `CopyOnWriteArrayList` or a lock |
| `singletonList(x).set(0, y)` | `UnsupportedOperationException` (`AbstractList.java:137-139`) |
| `List.of(x).set(0, y)` | `UnsupportedOperationException` (`AbstractImmutableList`) |
| `Arrays.asList(x).set(0, y)` | **succeeds** — writes through to the array (see `01d`) |
| `singletonList(x).sort(cmp)` | silent **no-op** (`Collections.java:5196-5198`) |
| `List.of(a, b).sort(cmp)` | `UnsupportedOperationException` (`ImmutableCollections.java:263`) |
| `singletonList(x).replaceAll(f)` | `UnsupportedOperationException` (`Collections.java:5192-5195`) |
| `singletonList(null)` vs `List.of(null)` | `[null]` vs `NullPointerException` |
| `List.copyOf(singletonList("a"))` | copies into a `List12` — not the fast path |
| Which to use in new code | `List.of(x)`; `singletonList` only for a null element |

---

## Self-test

**Q1.** `record Point(int[] coords) {}` and `List.of(new Point(new int[]{1,2}))`. Is that list
safe to share across threads?

<details><summary>Answer</summary>

No. The list is structurally immutable and safely published, and `Point.coords` is `final`, so
the *reference graph* is frozen. But `int[]` contents are mutable: any holder of the `Point`
can write `p.coords()[0] = 99` and every reader of the list sees it — with no happens-before
edge, so readers may see torn or stale values. Both `record` and `List.of` provide only shallow
immutability, and shallow plus shallow is still mutable. Fix: make the component immutable
(`List<Integer>`, or two `int` components), or copy the array in the canonical constructor
*and* in the accessor.

</details>

**Q2.** Your service holds `private final Set<String> features`, populated once at startup and
never changed. What should the getter return, and why is that the cheapest correct answer?

<details><summary>Answer</summary>

Assign `this.features = Set.copyOf(source)` in the constructor and have the getter
`return features;`. Because the field is then an `ImmutableCollections` set, there is nothing
for the caller to mutate, so the getter needs no wrapper and no copy — zero allocation per call
and no indirection on reads. Even if you defensively write `return Set.copyOf(features)`,
`Set.copyOf` returns `features` itself (`Set.java:729-730`), so it also costs nothing. The
alternatives are strictly worse: `unmodifiableSet(features)` allocates a wrapper per call for
no benefit, and copying per call is O(n) for a value that cannot change.

</details>

**Q3.** True or false: `Collections.singletonList("a").set(0, "b")` succeeds. Justify from
source.

<details><summary>Answer</summary>

False — it throws `UnsupportedOperationException`. `Collections.SingletonList` extends
`AbstractList` (`Collections.java:5157-5159`) and does not override `set`, so the inherited
`AbstractList.set` runs, whose entire body is `throw new UnsupportedOperationException();`
(`AbstractList.java:137-139`). The single-element list that *does* accept `set` is
`Arrays.asList("a")`, whose `Arrays$ArrayList.set` writes through to the backing array. Two
things `singletonList` *does* permit that `List.of` does not: a null element
(`singletonList(null)` yields `[null]`, because its constructor performs no null check) and
`sort`, which `SingletonList` overrides as an empty method (`Collections.java:5196-5198`).

</details>

**Q4.** `Collections.singletonList("a").sort(cmp)` does not throw, but
`Collections.singletonList("a").replaceAll(f)` does. Why is that not an inconsistency?

<details><summary>Answer</summary>

Because only one of them could actually change the list. Sorting a one-element list is a no-op
by definition, so `SingletonList` overrides `sort` with an empty body
(`Collections.java:5196-5198`) rather than refusing a call that cannot do harm. `replaceAll`
applies a function to the element and stores the result, which *would* change the list, so it
is overridden to throw (`Collections.java:5192-5195`). `List.of(...)` takes the stricter line
and throws for both, via `AbstractImmutableList` (`ImmutableCollections.java:261`, `263`) — the
Java 9 factories chose uniform refusal over per-method reasoning. Both designs are defensible;
you just have to know which one you are holding.

</details>

**Q5.** You need a `List` that (a) rejects all mutation, (b) may contain nulls, and (c) is a
snapshot independent of its source. Which factory do you use?

<details><summary>Answer</summary>

None of the single factories covered here does all three. `List.of`/`List.copyOf` satisfy (a)
and (c) but reject nulls. `singletonList` satisfies all three but only for one element.
`Collections.unmodifiableList` satisfies (a) and (b) but not (c). The composition that works is
`Collections.unmodifiableList(new ArrayList<>(source))` — the `ArrayList` copy gives you (c) and
tolerates nulls (b), and the wrapper gives you (a); because the copy is private and
unreachable, nobody can mutate it through the back door. `Arrays.asList(src.toArray())` is
*not* an answer: `set` writes through to the array. `Stream.toList()` also qualifies for (a),
(b) and (c) if you already have a stream — its `ListN` is built with `allowNulls == true`.

</details>

**Q6.** A getter returns `Collections.unmodifiableList(items)`. The caller iterates the result
in a `for-each` while your code, on the same thread, calls a method that appends to `items`.
What happens, and would `List.copyOf` have avoided it?

<details><summary>Answer</summary>

The caller gets `ConcurrentModificationException`. The view's iterator wraps the source
`ArrayList`'s iterator (`Collections.java:1073-1078`), which checks `modCount` on every `next`;
your `add` bumped it. Yes, `List.copyOf(items)` would have avoided it — the caller would be
iterating an independent `ListN` with no `modCount` link to `items` at all. That is a good
illustration of the leaf's rule in reverse: if the caller is going to *iterate* what you hand
back while you keep mutating, they needed a snapshot, not a window. Note that neither option
makes the getter thread-safe against a concurrent writer; `copyOf`'s `toArray` is not atomic
either.

</details>

---

## Open questions

None. Every claim in this file is backed by a JDK 21.0.7 source citation, a run transcript
above, or both.

---

**Leaves covered:** 2.3.17–2.3.19 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 598
