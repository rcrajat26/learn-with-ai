# 03 Java Core — Generic containers from scratch — the typesafe heterogeneous container and a generic Stack — BUILD IT (§4.4 (4.4.4, 4.4.5))

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [Generic containers from scratch](02a-generic-containers.md) · Next: [Generic builders, type tokens and varargs](02c-generic-builders-tokens-and-varargs.md)

Two containers, and the shape of each before the details:

| Container | Type parameters | What it models | JDK equivalent |
|---|---|---|---|
| `GateSet` (typesafe heterogeneous container) | none on the class; `<T>` per method | Many values of *different* types in one bag, each slot typed by its key | `AnnotatedElement.getAnnotation` in spirit |
| `ReservationStack<E>` | `E` the element type | LIFO over a growable array | `java.util.ArrayDeque<E>`, legacy `java.util.Stack<E>` |

`GateSet` parameterises the **key** rather than the container, so its type safety is exactly as
strong as the type tokens callers hand it — the two holes in that are the point of 4.4.4.
`ReservationStack` parameterises the container in the ordinary way, and immediately hits the wall
that `new E[n]` does not compile; the one unchecked cast that every array-backed generic collection
in the JDK writes instead is the point of 4.4.5. `Pair`, `Either`, `Result` and `MyOptional` — the
other four members of the family — are in
[Generic containers from scratch](02a-generic-containers.md).

The **"Diff vs the real one" table for the whole of §4.4** is leaf 4.4.10, in
[Generic builders, type tokens and varargs](02c-generic-builders-tokens-and-varargs.md). This file
ships the builds and the evidence; that file scores them against the JDK.

All code below was compiled and run on **Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64
(Apple silicon)**, compressed oops on.

---

## 4.4.4 A typesafe heterogeneous container `[BUILD]` `[PROVE]`

Normally a container's *element type* is parameterised, so a `List<Reservation>` holds one type. A
typesafe heterogeneous container parameterises the **key** instead: the class object is both the
lookup key and the proof of the value's type. `Map<Class<?>, Object>` inside, `<T> T get(Class<T>)`
outside, `Class.cast` bridging.

QuizStakes needs exactly this for `GateSet`: an application accumulates one verdict per gate and the
verdicts have different types. A `Map<String, Verdict>` keyed by gate name forces a downcast at
every read; keyed by class, `gates.get(DocumentVerdict.class)` returns a `DocumentVerdict` with no
cast at the call site.

`Class<T>` is a *type token*: `DocumentVerdict.class` has static type `Class<DocumentVerdict>`, so
`<T> T get(Class<T> type)` infers `T` from the argument alone. The map's value type is `Object`
because it must hold all of them, and `type.cast(value)` is the checked narrowing — `Class.cast` is
the reflective equivalent of a cast expression, and it is what makes an unchecked-free version
possible.

```java
sealed interface Verdict permits DocumentVerdict, ScreeningVerdict, ReviewVerdict, WealthVerdict {
    String statusCode();
}
record DocumentVerdict(String statusCode, String reason, Instant decidedAt, String decidedBy) implements Verdict {}
record ScreeningVerdict(String statusCode, String reason, Instant decidedAt, String decidedBy) implements Verdict {}
record ReviewVerdict(String statusCode, String reason, Instant decidedAt, String decidedBy) implements Verdict {}
record WealthVerdict(String statusCode, String reason, Instant decidedAt, String decidedBy) implements Verdict {}

final class GateSet {

    private final Map<Class<?>, Object> verdicts = new HashMap<>();

    <T extends Verdict> void put(Class<T> type, T verdict) {
        Objects.requireNonNull(type, "type");
        verdicts.put(type, type.cast(verdict));
    }

    /** Deliberately missing the cast on the way in, to show the late failure. */
    <T extends Verdict> void putUnchecked(Class<T> type, T verdict) {
        Objects.requireNonNull(type, "type");
        verdicts.put(type, verdict);
    }

    <T extends Verdict> T get(Class<T> type) {
        return type.cast(verdicts.get(type));
    }

    int size() { return verdicts.size(); }
}
```

```console
slots            = 3
documents        = AA-611 DOCUMENTS_VERIFIED by IDV-VENDOR
screening        = AA-501 SCREENING_CLEAR
wealth (absent)  = null
no cast needed at the call site: statusCode read straight off the record
```

`get(WealthVerdict.class)` returns `null` rather than throwing, because `Class.cast(null)` returns
null — the application is still at `AO-140 WEALTH_PENDING`.

### `[PROVE]` Hole (a) — the raw-type hole

A client holding a **raw** `Class` reference can put a value into the wrong slot, because raw types
disable the generic check that the design depends on:

```java
GateSet leaky = new GateSet();
@SuppressWarnings("rawtypes")
Class rawKey = ScreeningVerdict.class;
leaky.putUnchecked(rawKey,
    new DocumentVerdict("AA-611 DOCUMENTS_VERIFIED", "wrong slot", DECIDED_AT, "IDV-VENDOR"));
```

`javac -Xlint:all` on 21.0.7 — a **warning**, not an error, so this ships:

```console
VerdictBagDemo.java:67: warning: [unchecked] unchecked method invocation: method putUnchecked in class GateSet is applied to given types
        sameLeaky.putUnchecked(rawKey,
                              ^
  required: Class<T>,T
  found:    Class,DocumentVerdict
  where T is a type-variable:
    T extends Verdict declared in method <T>putUnchecked(Class<T>,T)
```

That is the first of the four warnings the run emits — `javac` also reports an `unchecked
conversion` for the key argument itself at the same line, and the pair again at the guarded `put`
below. All four are warnings.

At runtime:

```console
   put succeeded, nothing thrown, 1 slot stored
   failed later, at an unrelated get():
   java.lang.ClassCastException: Cannot cast DocumentVerdict to ScreeningVerdict
```

The bug is at the `put`; the exception lands at a `get` that may be in another service, another
request, another day. `Class.cast` on the **put** side closes the gap:

```console
   failed at the point of the bug:
   java.lang.ClassCastException: Cannot cast DocumentVerdict to ScreeningVerdict
   guarded slots after the rejected put = 0
```

Same exception, thrown at the offending frame, and the map is left unpolluted. That is the whole
justification for `verdicts.put(type, type.cast(verdict))`: the cast is redundant when the caller is
generic and it is the only defence when the caller is raw.

### `[PROVE]` Hole (b) — the non-reifiable-type hole

The key is a `Class` literal, and there is no `Class` literal for a parameterised type. First the
literal itself:

```java
Class<List<String>> agreementRefs = List<String>.class;
```

```console
NonReifiableKey.java:5: error: <identifier> expected
        Class<List<String>> agreementRefs = List<String>.class;
                                                         ^
NonReifiableKey.java:5: error: <identifier> expected
        Class<List<String>> agreementRefs = List<String>.class;
                                                              ^
2 errors
```

The grammar has no production for it — `javac` never reaches a type check. Then the obvious
workaround:

```java
Class<List<String>> agreementRefs = List.class;
```

```console
NarrowKey.java:5: error: incompatible types: Class<List> cannot be converted to Class<List<String>>
        Class<List<String>> agreementRefs = List.class;
                                                ^
1 error
```

`List.class` has type `Class<List>` — the raw type — because there is exactly one `Class` object per
erasure, shared by every parameterisation:

```console
List.class                        = interface java.util.List
one Class object for every List<T> = true
agreementRefs.getClass()          = class java.util.ArrayList
runtime type carries no T          = 1 declared type parameters, none bound
```

So the container can key on `DocumentVerdict` but not on `List<AgreementRef>` versus
`List<RestrictionKey>` — both erase to the same `List.class` key and collide. The escape is a
**super type token**: a class that captures the parameterised type through its own generic
superclass, where the type argument survives in the class file's `Signature` attribute rather than
in a `Class` literal. That is leaf 4.4.7, in
[Generic builders, type tokens and varargs](02c-generic-builders-tokens-and-varargs.md).
Reifiability itself is
[`../generics/03b-internals-reifiable-types-and-generic-arrays.md`](../generics/03b-internals-reifiable-types-and-generic-arrays.md).

> A typesafe heterogeneous container parameterises the key rather than the container, so its safety
> is exactly as strong as the type tokens it is handed: `Class.cast` on both sides closes the
> raw-type hole, and nothing short of a super type token closes the non-reifiable-type hole.

---

## 4.4.5 A generic `Stack<E>` over `(E[]) new Object[]` `[BUILD]` `[PROVE]`

An array-backed LIFO needs an `E[]` field, and `new E[n]` does not compile — the runtime has no `E`
to allocate. Every array-backed generic collection in the JDK resolves this the same way: allocate
`Object[]`, cast to `E[]`, never let it out. Two mechanisms ride along with that decision — a
documented unchecked cast and a null-out on removal — and both are load-bearing.

```java
final class ReservationStack<E> {

    private static final int DEFAULT_CAPACITY = 16;

    private E[] elements;
    private int size;

    ReservationStack() { this(DEFAULT_CAPACITY); }

    ReservationStack(int initialCapacity) {
        if (initialCapacity < 1) throw new IllegalArgumentException("initialCapacity " + initialCapacity);
        // Safe: `elements` is private, never returned, never passed out, and every write
        // goes through push(E), so only E values are ever stored. Nothing outside this
        // class can observe that the runtime type is Object[] rather than E[].
        @SuppressWarnings("unchecked")
        E[] backing = (E[]) new Object[initialCapacity];
        this.elements = backing;
    }

    void push(E element) {
        Objects.requireNonNull(element, "element");
        ensureCapacity(size + 1);
        elements[size++] = element;
    }

    E pop() {
        if (size == 0) throw new EmptyStackException();
        E popped = elements[--size];
        elements[size] = null;   // obsolete reference: without this the popped element
                                 // stays strongly reachable from the backing array
        return popped;
    }

    E peek() {
        if (size == 0) throw new EmptyStackException();
        return elements[size - 1];
    }

    boolean isEmpty() { return size == 0; }

    int size() { return size; }

    int capacity() { return elements.length; }

    private void ensureCapacity(int required) {
        if (required <= elements.length) return;
        int grown = elements.length * 2;
        if (grown < required) grown = required;
        elements = Arrays.copyOf(elements, grown);
    }
}
```

The `@SuppressWarnings("unchecked")` sits on a **local variable declaration**, the narrowest scope
the annotation can reach here — expressions cannot be annotated, so introducing the `backing` local
is what buys the narrow scope. Suppressing on the constructor would also silence a future unchecked
cast added elsewhere in it. Without the suppression, on 21.0.7:

```console
UncheckedBacking.java:4: warning: [unchecked] unchecked cast
        this.elements = (E[]) new Object[initialCapacity];
                              ^
  required: E[]
  found:    Object[]
  where E is a type-variable:
    E extends Object declared in class UncheckedBacking
1 warning
```

The safety argument, spelled out because the suppression obliges it: the field is `private`; no
method returns it or a slice of it or accepts an `E[]` that could be aliased to it; the only write
path is the type-checked `push(E)`. Therefore no code outside the class can observe the array's
runtime type, and the mismatch between that runtime type (`Object[]`) and the declared `E[]` is
unobservable. Change any of the three facts and the argument collapses.

Run from a deliberately small initial capacity of 2 so growth shows:

```console
capacity at construction = 2
push 4.20 -> size=1 capacity=2
push 3.33 -> size=2 capacity=2
push 12.50 -> size=3 capacity=4
peek        = Reservation[GBP 12.50]
pop         = Reservation[GBP 12.50]
pop         = Reservation[GBP 3.33]
size        = 1 isEmpty=false
pop         = Reservation[GBP 4.20]
isEmpty     = true
pop on empty -> java.util.EmptyStackException
```

Growth is `capacity * 2` with a floor at the required size, so 2 becomes 4 on the third push.
Doubling gives amortised O(1) `push`: n pushes copy 2 + 4 + 8 + … < 2n elements in total.

### `[PROVE]` The null-out on `pop`, measured

`elements[size] = null` is not tidiness. Without it the popped element is still referenced by the
array slot, and the array is referenced by a stack that may live for the whole process. A
`WeakReference` settles it — two stacks identical except that `LeakyReservationStack` omits the
null-out:

```java
static String retainedAfterPop(boolean nullOut) throws Exception {
    Reservation held = reservation("4.20");             // carries a 4 KiB audit payload
    WeakReference<Reservation> watch = new WeakReference<>(held);
    if (nullOut) {
        ReservationStack<Reservation> stack = new ReservationStack<>(4);
        stack.push(held);
        stack.pop();              // return value discarded
        KEEP_ALIVE = stack;       // the stack itself outlives the pop, as a field would
    } else {
        LeakyReservationStack<Reservation> stack = new LeakyReservationStack<>(4);
        stack.push(held);
        stack.pop();
        KEEP_ALIVE = stack;
    }
    held = null;                  // drop the only local strong reference
    for (int attempt = 0; attempt < 3; attempt++) {
        System.gc();
        Thread.sleep(50);
    }
    Reservation survivor = watch.get();
    return survivor == null
        ? "popped Reservation was collected"
        : "popped Reservation is STILL reachable: " + survivor;
}
```

```console
   leaky stack (no null-out):   popped Reservation is STILL reachable: Reservation[GBP 4.20]
   correct stack (null-out):    popped Reservation was collected
```

Measured, not asserted. `held = null` matters: without it the live local slot keeps the object alive
and both variants report "STILL reachable", which is a harness artefact rather than a finding — the
first version of this harness had exactly that bug. `System.gc()` is a hint, so this is a
demonstration on 21.0.7 with the default collector rather than a proof across configurations; the
direction of the result is the point and it reproduces here.

At scale the leak is not academic: a per-session stack of pending reservations, 14k steady
concurrent sessions, each retaining one popped `Reservation` with a 4 KiB payload, holds roughly
14,000 x 4,096 bytes ≈ 57 MiB of pure garbage — and the retention tracks the stack's *high water
mark*, never its current size.

### `[PROVE]` The alternative failing: array covariance

Why must the `Object[]` never escape? Because Java arrays are **covariant** — `Money[]` is a subtype
of `Object[]` — and the JVM enforces element types on *store*, at runtime:

```java
Money[] stakes = new Money[2];
Object[] asObjects = stakes;                       // legal: arrays are covariant
asObjects[0] = Money.gbp("4.20");                  // fine
asObjects[1] = "STAKE_BLOCKED";                    // compiles, throws
```

```console
   java.lang.ArrayStoreException: java.lang.String
```

The compiler is satisfied — storing a `String` into an `Object[]` is well-typed — and the check
happens at the `aastore` instruction against the array's *actual* component type. Now the same hole
through a leaked generic array; nothing about the cast changes, only that it escapes:

```java
@SuppressWarnings("unchecked")
static <E> E[] backingArray(int capacity) {
    return (E[]) new Object[capacity];
}

static Money[] leakBacking() {
    return backingArray(2);          // E inferred as Money
}
```

```console
   java.lang.ClassCastException: class [Ljava.lang.Object; cannot be cast to class [LMoney; ([Ljava.lang.Object; is in module java.base of loader 'bootstrap'; [LMoney; is in unnamed module of loader 'app')
```

The cast inside `backingArray` is a no-op at runtime: `E` erases to `Object`, so `(E[])` erases to
`(Object[])` and always succeeds. The failure is the **compiler-inserted** checkcast at the
`leakBacking` return, where `E` was inferred as `Money`. Identical cast, identical annotation; the
only difference is whether the array escapes — which is why the safety argument for
`ReservationStack` turns entirely on confinement and not on the cast. Array covariance in full is
[`../arrays/01a-covariance-and-mutability.md`](../arrays/01a-covariance-and-mutability.md).

> `(E[]) new Object[n]` is safe precisely as long as the array is private, never returned and
> written only through type-checked entry points; the moment it escapes into a context expecting a
> genuinely-typed array, the compiler-inserted checkcast turns silent erasure into a
> `ClassCastException`.
---

## Pitfalls

### Treating a raw `Class` reference as harmless because it only warns

**Wrong**

```java
Class rawKey = ScreeningVerdict.class;                  // raw
gates.putUnchecked(rawKey, someDocumentVerdict);        // warning only, so it ships
```

```console
   put succeeded, nothing thrown, 1 slot stored
   failed later, at an unrelated get():
   java.lang.ClassCastException: Cannot cast DocumentVerdict to ScreeningVerdict
```

**Right**

```java
<T extends Verdict> void put(Class<T> type, T verdict) {
    verdicts.put(type, type.cast(verdict));             // check on the way IN
}
```

```console
   failed at the point of the bug:
   java.lang.ClassCastException: Cannot cast DocumentVerdict to ScreeningVerdict
   guarded slots after the rejected put = 0
```

**Why people believe it:** the container's own code is fully generic and warning-free, so the safety
feels total. It is only as strong as its weakest *caller*, and a raw type at any call site switches
the check off for that call while leaving the compiler at warning level.

### Believing there is a `Class` literal for a parameterised type

**Wrong**

```java
Class<List<AgreementRef>> key = List<AgreementRef>.class;
```

```console
NonReifiableKeyProbe.java:5: error: <identifier> expected
        Class<List<AgreementRef>> key = List<AgreementRef>.class;
                                                           ^
NonReifiableKeyProbe.java:5: error: <identifier> expected
        Class<List<AgreementRef>> key = List<AgreementRef>.class;
                                                                ^
2 errors
```

Falling back to the raw literal does not narrow, and forcing it through anyway makes two logically
distinct slots share one key:

```console
NarrowKeyProbe.java:5: error: incompatible types: Class<List> cannot be converted to Class<List<AgreementRef>>
        Class<List<AgreementRef>> key = List.class;
                                            ^
1 error
```

```java
slots.put(List.class, List.of(new AgreementRef("TERMS", "v7")));
slots.put(List.class, List.of(new RestrictionKey("STAKE_BLOCKED", "ADMIN")));
```

```console
slots after two puts = 1
get(List.class)      = [RestrictionKey[type=STAKE_BLOCKED, source=ADMIN]]
```

**Right** — give each slot a reifiable nominal type of its own, so the key is a distinct class:

```java
record AgreementRefs(List<AgreementRef> values) {}
record RestrictionKeys(List<RestrictionKey> values) {}

static <T> void put(Class<T> type, T value) { slots.put(type, type.cast(value)); }
static <T> T get(Class<T> type)             { return type.cast(slots.get(type)); }
```

```console
slots after two puts = 2
agreements  = [AgreementRef[documentId=TERMS, version=v7]]
restrictions = [RestrictionKey[type=STAKE_BLOCKED, source=ADMIN]]
```

The other route is a **super type token**, which captures the parameterised type through a generic
superclass so the type argument survives in the `Signature` attribute. That build is leaf 4.4.7, in
[Generic builders, type tokens and varargs](02c-generic-builders-tokens-and-varargs.md).

**Why people believe it:** `Class<T>` is generic, `DocumentVerdict.class` really does have type
`Class<DocumentVerdict>`, and `List<AgreementRef>` is a type — so the literal looks like it must
exist. It does not, at two independent levels: the grammar has no production for a type argument
before `.class`, and even if it did there is exactly one `Class` object per erasure, shared by every
parameterisation, so there is nowhere for the `AgreementRef` to be recorded.

### Believing `(E[]) new Object[n]` is inherently unsafe

**Wrong** — the same cast, allowed to escape:

```java
@SuppressWarnings("unchecked")
static <E> E[] backingArray(int capacity) { return (E[]) new Object[capacity]; }
static Money[] leakBacking() { return backingArray(2); }
```

```console
   java.lang.ClassCastException: class [Ljava.lang.Object; cannot be cast to class [LMoney; ([Ljava.lang.Object; is in module java.base of loader 'bootstrap'; [LMoney; is in unnamed module of loader 'app')
```

**Right** — the identical cast, confined:

```java
@SuppressWarnings("unchecked")
E[] backing = (E[]) new Object[initialCapacity];
this.elements = backing;   // private field, never returned, written only via push(E)
```

```console
push 12.50 -> size=3 capacity=4
peek        = Reservation[GBP 12.50]
pop         = Reservation[GBP 12.50]
```

**Why people believe it:** the unchecked warning is real and the annotation feels like hiding
something. The warning says the compiler cannot *prove* the cast, not that the cast is wrong. Its
price is that you write down the confinement argument — and honour it.

---

## Cheat sheet

| Thing | The fact |
|---|---|
| Type token | `Class<T>` as key; `<T> T get(Class<T>)` infers `T` from the argument alone |
| `Class.cast` | reflective cast against a runtime token; returns `null` unchanged; `(T) x` erases to a no-op |
| Where the cast belongs | **both** put and get — redundant for a generic caller, the only defence against a raw one |
| Raw `Class` key | warning only, so it ships; failure lands at a later unrelated `get` |
| `List<String>.class` | grammar error; `List.class` is `Class<List>`, one `Class` per erasure |
| Erased key collision | two parameterisations keyed on `List.class` overwrite: 2 puts, 1 slot |
| Escape for a parameterised key | a nominal wrapper type, or a super type token (leaf 4.4.7) |
| `(E[]) new Object[n]` | safe iff private + never returned + written only through `push(E)` |
| `@SuppressWarnings("unchecked")` | narrowest reachable scope is a local variable declaration |
| Null-out on `pop` | measured: without it the popped element stays reachable from the array |
| Retention scale | 14k sessions x 4 KiB payload ≈ 57 MiB, tracking the high water mark |
| Array covariance | `Money[]` IS-A `Object[]`; a bad store throws `ArrayStoreException` at `aastore` |
| Leaked generic array | fails at the **caller's** compiler-inserted checkcast, not at the cast you wrote |
| Growth policy | `capacity * 2`, floor at required; amortised O(1) push |

---

## Self-test

**Q1.** A typesafe heterogeneous container is fully generic in its own source. Where does its type safety break, and what closes the gap?

<details><summary>Answer</summary>

At a **raw** caller. `Class rawKey = ScreeningVerdict.class;` erases the key's type argument, so
`put(rawKey, someDocumentVerdict)` passes the generic check by disabling it, and `javac` reports only
*"warning: [unchecked] unchecked method invocation"* — so the build ships. If `put` stores without
checking, the mismatch surfaces later at an unrelated `get(ScreeningVerdict.class)` as
*"ClassCastException: Cannot cast DocumentVerdict to ScreeningVerdict"*. Calling `type.cast(verdict)`
inside `put` closes it: same exception, thrown at the offending frame, map left unpolluted. The
second, unclosable gap is non-reifiable keys — no `Class` literal exists for `List<String>`, and
`List.class` is `Class<List>` shared across every parameterisation, so `List<AgreementRef>` and
`List<RestrictionKey>` collide on one key. That needs a super type token.

</details>

**Q2.** Justify `@SuppressWarnings("unchecked")` on `(E[]) new Object[n]` in `ReservationStack`, then say what would invalidate the justification.

<details><summary>Answer</summary>

Three facts make it safe: `elements` is `private`; no method returns it, returns a slice of it, or
accepts an `E[]` that could be aliased to it; the only write path is the type-checked `push(E)`, so
only `E` values are ever stored. Together those mean no code outside the class can observe the
array's runtime type, and the difference between its actual `Object[]` and its declared `E[]` is
unobservable. The annotation goes on a local variable declaration — the narrowest reachable scope,
since expressions cannot be annotated and the constructor would be too broad. Breaking any of the
three invalidates it: a method returning `elements` lets the caller's compiler-inserted checkcast
fail with *"class [Ljava.lang.Object; cannot be cast to class [LMoney;"*, which is precisely what the
`leakBacking` demonstration shows using an identical cast.

</details>

**Q3.** Why is `elements[size] = null` in `pop` a correctness concern, and how was that shown?

<details><summary>Answer</summary>

Without it the popped element stays referenced by the array slot, and the array by a stack that may
live as long as the process, so the object cannot be collected even though the stack logically no
longer holds it — an obsolete reference. Shown with a `WeakReference`: two otherwise identical
stacks, push a `Reservation` carrying a 4 KiB payload, watch it weakly, pop and discard the returned
value, null the last local strong reference, keep the stack alive in a `static volatile` field, then
`System.gc()`. Without the null-out: *"popped Reservation is STILL reachable"*. With it: *"popped
Reservation was collected"*. The `held = null` is essential to the harness — without it the live
local slot keeps the object alive and both report reachable, an artefact rather than a finding.
`System.gc()` is a hint, so this is a demonstration on 21.0.7 with the default collector rather than
a proof. At 14k steady concurrent sessions each retaining one 4 KiB payload, ≈57 MiB stays live, and
the retention tracks the stack's high water mark rather than its current size.

</details>

**Q4.** `Money[] stakes = new Money[2]; Object[] asObjects = stakes; asObjects[1] = "STAKE_BLOCKED";` — what happens and why does the compiler allow it?

<details><summary>Answer</summary>

It compiles and throws `java.lang.ArrayStoreException: java.lang.String`. The compiler allows the
assignment because arrays are covariant — `Money[]` is a subtype of `Object[]` — so `asObjects` is a
well-typed `Object[]` and storing a `String` into an `Object[]` is statically legal. The array object
carries its real component type at runtime, and the `aastore` instruction checks every stored
reference against it, throwing with the offending class name as the message. This is exactly why a
`(E[]) new Object[n]` backing array must never escape: its real component type is `Object`, so a
caller who believes it is `Money[]` gets a `ClassCastException` at the compiler-inserted checkcast,
and code storing through a covariant view gets the store check instead.

</details>

**Q5.** `GateSet.get(WealthVerdict.class)` returns `null` for an application still at `AO-140 WEALTH_PENDING` rather than throwing. What is doing that, and why is `Class.cast` used rather than a cast expression?

<details><summary>Answer</summary>

`Class.cast` returns its argument unchanged when the argument is `null` — a null reference is
assignable to every reference type, so there is nothing to check — so `type.cast(verdicts.get(type))`
on a missing key yields `null` instead of failing. That is the right answer for a gate that has not
been decided yet: the slot is genuinely empty, not wrongly typed. A cast *expression* would not work
here at all: `(T) verdicts.get(type)` erases to `(Object)` and is a no-op, so the check the design
depends on would simply not happen, and `javac` would emit an unchecked warning saying so. `Class.cast`
is the reflective equivalent of a cast against a type known only at runtime, and it performs the real
`isInstance` test against the token the caller supplied. That is why it appears on both sides: on
`get` so the value handed back really is a `T`, and on `put` so a raw caller's mistake fails at the
frame that made it rather than at some later, unrelated `get`.

</details>

**Q6.** `ReservationStack` grows by `elements.length * 2` with a floor at the required size. Why doubling rather than a fixed increment, and what does the floor protect?

<details><summary>Answer</summary>

Doubling makes `push` amortised O(1). Growing from 1 to n by repeated doubling copies
2 + 4 + 8 + … elements in total, a geometric series bounded by 2n, so the total copying cost over n
pushes is linear and the per-push average is constant even though individual pushes are O(n). A fixed
increment k gives arithmetic growth: n/k reallocations copying k, 2k, 3k, … elements, which sums to
O(n²/k) — quadratic total work, so a per-session reservation stack that grows to a few thousand
entries would spend most of its time in `Arrays.copyOf`. The price of doubling is up to 2x peak
capacity overshoot and a transient in which both the old and the new array are live, which is the
tradeoff, not a free win. The floor (`if (grown < required) grown = required`) covers the case where
one operation needs more than double — irrelevant for single-element `push`, but the moment a bulk
`pushAll` is added, doubling from a capacity of 2 to 4 would not accommodate a 10-element append and
the array would be left too small, which is exactly the bug `ArraysSupport.newLength` exists to
avoid in the JDK. The run shows the policy at work: capacity 2 at construction, still 2 after two
pushes, 4 on the third.

</details>

---

## Open questions

- The `WeakReference` retention demonstration in 4.4.5 relies on `System.gc()`, which the
  specification defines as a hint. The result is stable across runs on this build with the default
  collector, but a proof rather than a demonstration would need a heap dump after a controlled full
  collection (`jcmd GC.heap_dump` plus a dominator-tree query) or an `-Xlog:gc+ref` trace confirming
  the referent was processed. Guide 06 owns heap-dump tooling.
- Whether any `-Xlint` category plus `-Werror` combination elevates the raw-key unchecked-invocation
  warning to an error is a build-policy question; nothing in the JLS makes it an error. Settling it
  would need a pass over the `javac -Xlint:all` category list.

---

**Leaves covered:** 4.4.4, 4.4.5 (2 leaves)
**Leaves deferred:** the §4.4 "Diff vs the real one" table — owned by
`02c-generic-builders-tokens-and-varargs.md` as leaf 4.4.10, per the batch file table; the super type
token is leaf 4.4.7 in the same file
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 678
