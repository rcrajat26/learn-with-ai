# 03 Java Core — Recursive type bounds and the typesafe heterogeneous container — BASICS (§1.21, 1.21.20, 1.21.21)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [Raw types and unchecked warnings](01c-raw-types-and-unchecked-warnings.md) · Next: [Generics in anger](02-in-anger.md)

This file covers two BASICS leaves that look unrelated but share a mechanism: both restore a
type-safety guarantee that a plain generic signature cannot express on its own. §1 reads and proves
the recursive bound `<T extends Comparable<? super T>>` — why it is shaped that way and not the
simpler `<T extends Comparable<T>>`. §2 builds the typesafe heterogeneous container, the pattern
that inverts which side of a generic declaration carries the type parameter. Erasure and reifiability
as general topics belong to `01a-erasure-and-its-consequences.md`; wildcard variance and PECS as a
general topic belong to `01b-variance-and-wildcards.md`; `Class<T>` as a type token, `asSubclass` and
super type tokens belong to `02a-type-tokens-and-generic-reflection.md`; the CRTP self-type pattern
that reuses this same recursive-bound trick belongs to `02b-generic-arrays-and-self-types.md`; the
`Comparable`/`Comparator` API contract belongs to
`../objects-equality-and-lifecycle/02a-composite-equality-and-ordering.md`. This file only teaches
how to *read* the bound and how to *build* the container — not those neighbouring surfaces.

## 1. Recursive type bounds: reading `<T extends Comparable<? super T>>` (1.21.20)

The mental model: a recursive bound is a type parameter that appears again inside its own bound.
`<T extends Comparable<T>>` is not circular the way it looks on first read — it is a constraint that
says "whatever `T` ends up being, it must be a type that can compare *itself* to other instances of
that same type." Nothing about the JVM or `javac` treats this specially; it is an ordinary bound, it
just happens to mention the variable it is bounding. The harder version, `<T extends Comparable<?
super T>>`, loosens "compares itself" to "compares itself, or inherits that ability from something
it is a kind of" — and that loosening is not decoration, it is the difference between a bound that
real class hierarchies satisfy and one that only leaf classes satisfy.

### Why it exists

Before generics (Java 1.4 and earlier), `Comparable` was raw: `compareTo(Object)`, checked at
runtime with an `instanceof` or a `ClassCastException` waiting to happen. Generics let `Comparable`
become `Comparable<T>`, so `compareTo` takes exactly the right type and the compiler checks it. But
the moment a generic method wants to accept "anything comparable" — `Collections.max`, a sort
routine, this file's `laterOf` — it needs a bound that names the type being compared. The naive
`<T extends Comparable<T>>` looks like the obvious translation of "T is Comparable" into generic
syntax. It is almost right, and where it falls short is exactly the case that shows up constantly in
real hierarchies: a base class implements the comparison once, and every subclass inherits it without
overriding `compareTo`.

### The mechanism

Read `<T extends Comparable<T>>` first, in isolation. It says: pick a `T` such that `T` implements
`Comparable<T>` — the type argument to `Comparable` must be `T` itself, exactly. This is satisfied by
`String` (`Comparable<String>`), by `Integer` (`Comparable<Integer>`), by any type that declares its
own `compareTo` against its own type. It rejects a `T` whose `Comparable` implementation names an
*ancestor* type instead of `T`.

`[PROVE]` — building the failing case in QuizStakes terms, on real JDK 21.0.7. Model a settlement
record ordered by when it occurred, with two kinds of settlement sharing that ordering:

```java
import java.time.Instant;

abstract class SettlementRecord implements Comparable<SettlementRecord> {
    private final Instant occurredAt;
    SettlementRecord(Instant occurredAt) { this.occurredAt = occurredAt; }
    Instant occurredAt() { return occurredAt; }
    @Override public int compareTo(SettlementRecord other) {
        return this.occurredAt.compareTo(other.occurredAt);
    }
}

final class CashSettlement extends SettlementRecord {
    CashSettlement(Instant occurredAt) { super(occurredAt); }
}

final class BonusSettlement extends SettlementRecord {
    BonusSettlement(Instant occurredAt) { super(occurredAt); }
}
```

(`SettlementRecord` is a plain `abstract class`, not `sealed`, because this example needs two
independently-declared subclasses and a sealed hierarchy would need `CashSettlement` and
`BonusSettlement` listed in its `permits` clause — orthogonal to the point being made here, so the
simpler form is used.) Neither subclass overrides `compareTo`; both inherit the one implementation
from `SettlementRecord`, which means both implement `Comparable<SettlementRecord>` — not
`Comparable<CashSettlement>`, not `Comparable<BonusSettlement>`. Now write the naive generic method
and call it with the subclass:

```java
static <T extends Comparable<T>> T laterOf(T a, T b) {
    return a.compareTo(b) >= 0 ? a : b;
}
```

```java
CashSettlement c1 = new CashSettlement(Instant.now());
CashSettlement c2 = new CashSettlement(Instant.now().plusSeconds(60));
CashSettlement later = laterOf(c1, c2);   // does not compile
```

Compiled on JDK 21.0.7 (`javac -Xlint:all`), the real diagnostic is:

```
Fail.java:28: error: incompatible types: inference variable T has incompatible bounds
        CashSettlement later = laterOf(c1, c2);
                                      ^
    equality constraints: SettlementRecord
    upper bounds: CashSettlement,Comparable<T>
  where T is a type-variable:
    T extends Comparable<T> declared in method <T>laterOf(T,T)
1 error
```

Read the diagnostic in pieces. Inference wants `T = CashSettlement` from the argument types (`upper
bounds: CashSettlement`), but `CashSettlement implements Comparable<SettlementRecord>`, and the only
way `CashSettlement` can satisfy `Comparable<T>` for `T = CashSettlement` is if `Comparable<T>` also
unifies with `Comparable<SettlementRecord>` — forcing `T = SettlementRecord` (`equality constraints:
SettlementRecord`). Inference cannot satisfy `T = CashSettlement` and `T = SettlementRecord`
simultaneously, so it fails with "incompatible bounds." The bound `Comparable<T>` demanded that the
type argument to `Comparable` match the inferred type *exactly*, and inheritance broke that match.

Now widen the bound to `<T extends Comparable<? super T>>` and change nothing else:

```java
static <T extends Comparable<? super T>> T laterOf(T a, T b) {
    return a.compareTo(b) >= 0 ? a : b;
}
```

This compiles and runs (JDK 21.0.7, `javac -Xlint:all` — zero warnings, zero errors):

```java
CashSettlement c1 = new CashSettlement(Instant.parse("2026-08-28T10:00:00Z"));
CashSettlement c2 = new CashSettlement(Instant.parse("2026-08-28T10:01:00Z"));
CashSettlement later = laterOf(c1, c2);
System.out.println(later);   // CashSettlement@2026-08-28T10:01:00Z
```

Why does the same inference succeed now? `T = CashSettlement` is still forced by the arguments, but
the bound only requires `CashSettlement implements Comparable<X>` for *some* `X` that `CashSettlement`
is a subtype of, or equal to. `CashSettlement` is a subtype of `SettlementRecord`, and
`CashSettlement implements Comparable<SettlementRecord>` — so `X = SettlementRecord` satisfies
`? super T` (`SettlementRecord` is a supertype of `T = CashSettlement`), and the bound is met without
forcing `T` away from `CashSettlement`. The wildcard is doing exactly the "compares things I am a
kind of" reading from the opening paragraph, cashed out as a real inference constraint. (`? super T`
in a bound position is the same PECS direction as `? super T` in a *parameter* position —
consumer-super — read in full in `01b-variance-and-wildcards.md`; this file only needs the one line
that a `? super` position accepts the named type or any of its supertypes.)

The JDK does not use the naive form anywhere a real hierarchy might appear under it.
`java.util.Collections.max` is declared, verified here directly from `javap -v` against
`java.util.Collections.class` on JDK 21.0.7:

```
public static <T extends java.lang.Object & java.lang.Comparable<? super T>> T max(java.util.Collection<? extends T>);
  descriptor: (Ljava/util/Collection;)Ljava/lang/Object;
  Signature: #591   // <T:Ljava/lang/Object;>(Ljava/util/Collection<+TT;>;Ljava/util/Comparator<-TT;>;)TT;
```

Read every piece. `Collection<? extends T>` is ordinary PECS — the collection is a producer of `T`,
covered in `01b`. `T extends Comparable<? super T>` is this section's bound, doing exactly the job
just proved: accept any element type whose comparison ability may live on an ancestor. The
`Object & Comparable<? super T>` intersection is the piece that looks redundant — every type already
extends `Object` — and it is not decoration either.

**Insight:** the `Object &` is an erasure-compatibility artefact, not a type-safety requirement.
Erasure replaces a type variable with the erasure of its *leftmost* bound (mechanism owned by
`01a-erasure-and-its-consequences.md` and walked at the bytecode level in
`03-internals-erasure.md`). `Collections.max` was generified in Java 5 from a pre-generics signature
whose erased descriptor was `(Ljava/util/Collection;)Ljava/lang/Object;` — it took an `Object`-typed
collection and returned `Object`. If the bound had been written as plain `T extends Comparable<? super
T>`, the leftmost bound would be `Comparable`, erasure would produce
`(Ljava/util/Collection;)Ljava/lang/Comparable;`, and that is a different binary signature —
existing compiled callers would break at link time. Prepending `Object &` forces the leftmost bound
back to `Object`, so the erased descriptor matches the pre-generics one exactly (confirmed above:
`descriptor: (Ljava/util/Collection;)Ljava/lang/Object;`), while the *checked* signature — the one
`javac` enforces at the call site and records in the `Signature` attribute — keeps the full
`Comparable<? super T>` constraint. This is a migration-compatibility trick, not a type-theory
requirement; it exists because `Collections` is JDK 1.0-era code that generics had to slot underneath
without breaking binaries.

**Interview:** "Why does `Collections.max` use `Comparable<? super T>` instead of `Comparable<T>`?"
— walk the `laterOf` failure above: a subtype that inherits `compareTo` from a base class implements
`Comparable<Base>`, not `Comparable<Sub>`, so the exact-match bound rejects the overwhelmingly common
case of inherited comparison. `? super T` accepts the inherited implementation without weakening what
gets checked — `a.compareTo(b)` is still fully type-checked at the call site.

One more recursive-bound shape exists and is deliberately not built here: `<T extends Builder<T>>`,
the self-typed / curiously-recurring-template pattern used for chainable builders so that
`builder.step1().step2()` returns the concrete subtype instead of the declared base type. It is the
same trick — a type parameter bounded by something that mentions itself — aimed at return-type
covariance instead of comparison. That construction, with its own array-covariance and bridge-method
consequences, belongs to `02b-generic-arrays-and-self-types.md`.

> A recursive bound `<T extends Comparable<? super T>>` restricts `T` to types that can compare
> themselves to instances of `T` or any of `T`'s supertypes, which is what lets a subtype's *inherited*
> comparison satisfy the bound instead of only a subtype's own re-declared one.

## 2. The typesafe heterogeneous container (1.21.21)

The mental model: an ordinary generic container parameterises the *container* —
`List<CashEntry>` fixes one element type for every slot, checked once at the declaration. A
heterogeneous container flips which side carries the type: the *keys* each carry their own element
type, the container itself holds `Object`, and there is no single type parameter that could describe
"a `Map` from `Class<DocumentVerdict>` to `DocumentVerdict` and also from `Class<ScreeningVerdict>` to
`ScreeningVerdict`" — Java's type system has no way to write that constraint across a single map's
type parameters. The trick is to give up on the compiler checking the map's contents at the
declaration and get the check back at the read, using the one runtime object that still knows what
type it represents: the `Class` object itself.

### Why it exists

A per-application bag of verdicts — one `DocumentVerdict`, one `ScreeningVerdict`, one
`ReviewVerdict`, one `WealthVerdict`, each produced by a different stage of onboarding — cannot be a
`Map<String, Verdict>` without losing the specific subtype at every read (every `get` returns the
sealed `Verdict` supertype, forcing a pattern-matching `switch` just to get back to
`DocumentVerdict`). It cannot be four separate fields either, once the set of verdict kinds is open to
extension or needs to be handled generically by shared infrastructure (audit logging, serialization).
*Effective Java*, Item 33: *Consider typesafe heterogeneous containers*, names exactly this shape:
parameterise the key, not the container.

### The mechanism

The container is `Map<Class<?>, Object>` — a `Class<?>` key (a type token, owned in full by
`02a-type-tokens-and-generic-reflection.md`) mapped to an untyped `Object` value. Nothing in that
declaration ties a particular key to a particular value type; the tie is enforced procedurally, by
the two methods that are the only sanctioned way in or out:

`[BUILD]` — compiled and run on JDK 21.0.7 (`javac -Xlint:all`, no warnings; output shown below is
real):

```java
import java.time.Instant;
import java.util.HashMap;
import java.util.Map;
import java.util.Objects;

sealed interface Verdict permits DocumentVerdict, ScreeningVerdict, ReviewVerdict, WealthVerdict {
    String outcome();
    Instant decidedAt();
}

record DocumentVerdict(String outcome, String reason, Instant decidedAt, String decidedBy) implements Verdict {}
record ScreeningVerdict(String outcome, String reason, Instant decidedAt, String decidedBy) implements Verdict {}
record ReviewVerdict(String outcome, String reason, Instant decidedAt, String decidedBy) implements Verdict {}
record WealthVerdict(String outcome, String reason, Instant decidedAt, String decidedBy) implements Verdict {}

final class VerdictBag {
    private final Map<Class<?>, Object> verdictsByType = new HashMap<>();

    <T extends Verdict> void put(Class<T> type, T instance) {
        verdictsByType.put(Objects.requireNonNull(type), Objects.requireNonNull(instance));
    }

    <T extends Verdict> T get(Class<T> type) {
        return type.cast(verdictsByType.get(Objects.requireNonNull(type)));
    }
}
```

`put(Class<T> type, T instance)` ties the key and the value to the *same* `T` at the call site — the
compiler will not let a caller pass `DocumentVerdict.class` with a `ScreeningVerdict` instance,
because `T` is inferred once per call and must match both parameters. `get(Class<T> type)` does the
inverse: it takes the token, looks up the raw `Object`, and calls `type.cast(value)` — an instance
method on `Class<T>` that performs a checked, dynamic cast to `T` and throws `ClassCastException`
immediately if the object is not an instance of `type`. `Objects.requireNonNull` on the key in `put`
guards against a `null` `Class` silently corrupting the map (a `null` key would still satisfy
`Map<Class<?>, Object>`'s erased signature, so nothing else catches it).

Round trip, real output:

```java
VerdictBag bag = new VerdictBag();
bag.put(DocumentVerdict.class,
    new DocumentVerdict("VERIFIED", "passport match",
        Instant.parse("2026-08-28T10:00:00Z"), "vendor-x"));
bag.put(ScreeningVerdict.class,
    new ScreeningVerdict("CLEAR", "no watchlist hit",
        Instant.parse("2026-08-28T10:01:00Z"), "watchlist-provider"));

DocumentVerdict doc = bag.get(DocumentVerdict.class);
ScreeningVerdict screening = bag.get(ScreeningVerdict.class);
System.out.println(doc);
System.out.println(screening);
```

```
DocumentVerdict[outcome=VERIFIED, reason=passport match, decidedAt=2026-08-28T10:00:00Z, decidedBy=vendor-x]
ScreeningVerdict[outcome=CLEAR, reason=no watchlist hit, decidedAt=2026-08-28T10:01:00Z, decidedBy=watchlist-provider]
```

`doc` came back as a `DocumentVerdict`, not a `Verdict` — the compiler knows the precise type at the
`get` call site, entirely from the `Class<DocumentVerdict>` literal passed in, with no cast written
in source.

No diagram: the manifest assigns this section none; the round trip above, plus the failure below, is
the picture — a map with one static type and two dynamically-tracked ones.

Three things make this interview material.

**One — why `type.cast(value)` and not `(T)`.** An unchecked cast `(T) verdictsByType.get(type)` would
compile with an `unchecked` warning and then *erase to nothing at all* — no `checkcast` is emitted for
a cast to an erased type variable, so a mismatched value would sail through `get` and blow up later,
at some unrelated line that happens to use the value as if it were the right type, with a stack trace
that points nowhere near the actual bug. `type.cast(value)` fails at the boundary instead, because
`Class.cast` is not erased — it is an ordinary instance method that does `isInstance` at runtime
against the *reified* `Class` object, checked-JDK21.0.7, real trace:

```java
Map<Class<?>, Object> raw = new HashMap<>();
raw.put((Class) DocumentVerdict.class,
    new ScreeningVerdict("CLEAR", "mismatched put", Instant.now(), "test"));
try {
    DocumentVerdict corrupted = DocumentVerdict.class.cast(raw.get(DocumentVerdict.class));
    System.out.println(corrupted);
} catch (ClassCastException e) {
    System.out.println("caught: " + e);
}
```

```
caught: java.lang.ClassCastException: Cannot cast ScreeningVerdict to DocumentVerdict
```

Reaching this state required going around `VerdictBag.put` entirely — through a raw `Map<Class<?>,
Object>` reference with a cast key, which is exactly the kind of API misuse `put`'s matched-`T`
signature exists to make impossible from inside the class. The exception surfaces the instant
`get` calls `.cast(value)`, naming both the expected and actual class, rather than later at whatever
call site first treats the corrupted value as a `DocumentVerdict`.

**Two — the pattern is defeated by a non-reifiable key.** There is no `Class<List<Money>>` object at
runtime, because `List<Money>` and `List<CashEntry>` erase to the same `Class` object,
`List.class`, typed only as the raw `Class<List>` — the same erasure fact that makes `List<Money>`
non-reifiable is exactly why it cannot be a key in this pattern: a heterogeneous container keyed on
`Class<?>` can only ever key on a reifiable type, because "the key carries the value's exact type" is
only true when the `Class` object itself is precise. `List.class` is precise about "a `List`," not
about "a `List` of `Money`," so two unrelated verdict-holding lists of different element types would
collide on the exact same key. The general reifiability rule and the full consequences list live in
`01a-erasure-and-its-consequences.md`; the escape hatch — a "super type token" that captures the full
parameterised type in a `Signature` attribute instead of a `Class` object — is built in
`02a-type-tokens-and-generic-reflection.md`.

**Three — where the JDK and Spring already ship this shape.**

| Where | Key type | What it returns | Notes |
|---|---|---|---|
| `AnnotatedElement.getAnnotation(Class<T>)` | `Class<T>` where `T extends Annotation` | the matching annotation instance, or `null` | `java.lang.reflect`; the container is "everything a method/class/field is annotated with" |
| `Collections.checkedCollection(Collection<E>, Class<E>)` | `Class<E>` | a view that runtime-checks every insertion against the token | not itself a container of mixed types, but the same "carry a `Class` alongside the generic type to recover a runtime check" idea |
| Spring's `ApplicationContext.getBean(Class<T>)` / request-scoped attribute maps | `Class<T>` (or a `String` name resolved to one) | the matching bean or attribute, typed | the container backing a bean factory or a request context is exactly a `Map`-like structure keyed by type, for the same reason: one registry, many unrelated types |

### Gotcha

**Pitfall:** believing the compiler is checking anything about the *values* stored in a `Map<Class<?>,
Object>`. It is not — `Object` accepts anything, and the only enforcement is procedural, inside
`put`/`get`. Anyone who obtains the raw map (a package-private leak, a raw-typed reference, reflection)
can insert a mismatched pair, and the failure will not appear until the next `get` calls `.cast(value)`
on that exact key — demonstrated above, where the corruption happened two statements before the
exception.

> The typesafe heterogeneous container parameterises the key instead of the container — `Map<Class<?>,
> Object>` — and restores compile-time-adjacent safety by tying the key and value to the same type
> parameter in `put`/`get`, with `Class.cast` performing the one runtime check the erased container
> cannot.

## Supporting facts

### `Class<T>` as the runtime witness for `T`

Every `Class` object is reified — it exists at runtime with a real, precise identity — even though the
type variable it instantiates is erased. That is the entire reason a `Class<T>` token can stand in for
"the compile-time-erased `T`" at runtime: `DocumentVerdict.class` is a single, distinct object
(`DocumentVerdict.class == DocumentVerdict.class` is `true`, JIT-obvious and JDK21-confirmed) that a
method can inspect, compare, and cast against, long after `T` itself has vanished from the bytecode.
Full type-token treatment — `asSubclass`, using a token to build a generic array, super type tokens —
is `02a-type-tokens-and-generic-reflection.md`'s.

> A `Class<T>` object is the one piece of `T` that erasure cannot remove, because it is reified data,
> not a compile-time-only type annotation.

### Bounding the key with the value's own hierarchy

`VerdictBag.put`/`get` both write `<T extends Verdict>`, not `<T>` — an unbounded key parameter would
let any `Class<?>` at all serve as a key, including `Class<String>` or `Class<CashEntry>`, defeating
the container's one stated purpose. The bound is not required by the pattern in general (a container
of `Class<?>` to arbitrary `Object` needs no bound at all — that is the `AnnotatedElement` shape), but
it is cheap insurance whenever the container is meant to hold one known family.

> Bounding the container's type parameter with the family it is meant to hold turns "wrong key type"
> from a runtime surprise into a compile error at the `put`/`get` call site.

## Pitfalls

### "`<T extends Comparable<T>>` is the correct bound for anything sortable"

**Wrong**

```java
static <T extends Comparable<T>> T laterOf(T a, T b) {
    return a.compareTo(b) >= 0 ? a : b;
}
// CashSettlement inherits compareTo from SettlementRecord and never overrides it
CashSettlement later = laterOf(c1, c2);
```

```
Fail.java:28: error: incompatible types: inference variable T has incompatible bounds
        CashSettlement later = laterOf(c1, c2);
                                      ^
    equality constraints: SettlementRecord
    upper bounds: CashSettlement,Comparable<T>
```

**Right**

```java
static <T extends Comparable<? super T>> T laterOf(T a, T b) {
    return a.compareTo(b) >= 0 ? a : b;
}
CashSettlement later = laterOf(c1, c2);   // compiles; prints CashSettlement@2026-08-28T10:01:00Z
```

`? super T` lets `CashSettlement`'s *inherited* `Comparable<SettlementRecord>` satisfy the bound
without forcing the inferred type away from `CashSettlement`.

**Why people believe it:** `Comparable<T>` is what appears in almost every tutorial's first example,
because `String` and `Integer` both implement `Comparable<Self>` directly and the naive bound works
for them — the gap only shows up once a base class centralises the comparison and subclasses inherit
rather than re-declare it, which is common in real domain hierarchies and rare in toy examples.

### "An unchecked cast is fine as long as I control both `put` and `get`"

**Wrong**

```java
<T extends Verdict> T get(Class<T> type) {
    return (T) verdictsByType.get(type);   // unchecked, and it erases to nothing
}
// elsewhere, through a raw reference obtained by mistake:
Map raw = verdictsByType;
raw.put(DocumentVerdict.class, new ScreeningVerdict("CLEAR", "mismatched put", Instant.now(), "test"));
DocumentVerdict corrupted = bag.get(DocumentVerdict.class);   // no exception here
someMethodThatAssumesDocumentVerdict(corrupted);              // blows up two frames later
```

The `(T)` cast to an erased type variable emits no `checkcast` — the mismatch survives `get`
completely and surfaces, if at all, at whatever later call site first treats the value as the wrong
type, with a stack trace that does not mention `VerdictBag` at all.

**Right**

```java
<T extends Verdict> T get(Class<T> type) {
    return type.cast(verdictsByType.get(type));
}
```

```
caught: java.lang.ClassCastException: Cannot cast ScreeningVerdict to DocumentVerdict
```

`type.cast(value)` is a real runtime check against the reified `Class` object — it fails exactly at the
`get` call, naming both classes.

**Why people believe it:** an unchecked cast to `T` looks identical in source to a cast to any other
type, and it compiles with only a lint warning (frequently suppressed project-wide), so the fact that
it is silently doing nothing at runtime is invisible until a mismatch actually occurs, often far from
where it was introduced.

### "The container can hold `List<Money>` and `List<CashEntry>` as separate entries"

**Wrong**

```java
Map<Class<?>, Object> bag = new HashMap<>();
bag.put(List.class, List.of(Money.class));      // meant: "the List<Money> slot"
bag.put(List.class, List.of(CashEntry.class));  // overwrites the previous entry — same key
```

Both calls use the identical key, `List.class`, because `List<Money>` and `List<CashEntry>` erase to
the same `Class` object at runtime — there is no `Class<List<Money>>` distinct from
`Class<List<CashEntry>>`.

**Right**

Do not key a heterogeneous container on a parameterised type at all. Either key on the element type
directly (`Class<Money>`, `Class<CashEntry>` — reifiable, works), or use a super type token that
captures the full parameterised type via a `Signature` attribute instead of a `Class` object — the
escape hatch built in `02a-type-tokens-and-generic-reflection.md`.

**Why people believe it:** `Class<?>` looks like "the type," full stop, and nothing about writing
`List.class` signals that the compiler discarded the element type the moment it erased `List<Money>`
to `List` — the loss is invisible at the point of writing the key.

## Cheat sheet

| Form | Reads as | Accepts | Rejects |
|---|---|---|---|
| `<T extends Comparable<T>>` | T compares itself, exactly | leaf types with their own `compareTo` (`String`, `Integer`) | subtypes that inherit `compareTo` from a base class |
| `<T extends Comparable<? super T>>` | T compares itself, or inherits that from an ancestor | the above, plus inheriting subtypes | nothing extra — strictly wider |
| `<T extends Object & Comparable<? super T>>` | same as above, `Object` forced leftmost | — | exists only so erasure keeps `Object` as the erased return type (binary compatibility with pre-generics `Collections.max`) |
| `Map<Class<?>, Object>` + `put(Class<T>, T)`/`get(Class<T>)` | container keyed by type, one slot per distinct `Class` | any reifiable type as a key | parameterised types as keys (`List<Money>` and `List<CashEntry>` collide on `List.class`) |
| `Class.cast(Object)` | checked dynamic cast against a reified `Class` | — | fails loudly with `ClassCastException` naming both classes, at the call site |
| `(T) obj` on an erased `T` | unchecked, no runtime check at all | compiles with a warning | mismatch survives silently past this line |

## Self-test

**Q1.** Why does `<T extends Comparable<T>>` reject a subclass that inherits `compareTo` from its
superclass instead of overriding it?

<details><summary>Answer</summary>

Because the bound requires the type argument to `Comparable` to be exactly `T`. If the subclass never
overrides `compareTo`, it implements `Comparable<Superclass>`, not `Comparable<Subclass>`. When
`javac` infers `T` from the call-site arguments as the subclass type, it also needs `Comparable<T>` to
unify with `Comparable<Superclass>` to satisfy the bound, which forces `T = Superclass` — two
incompatible requirements on the same inference variable, so inference fails with an
"incompatible bounds" error.

</details>

**Q2.** What specifically does changing `Comparable<T>` to `Comparable<? super T>` fix, mechanically?

<details><summary>Answer</summary>

It stops requiring the type argument to `Comparable` to match `T` exactly. `? super T` is satisfied
by `T` itself or any supertype of `T`, so a subclass whose `Comparable` implementation names an
ancestor type still satisfies the bound without forcing the inferred type away from the subclass. The
comparison call itself, `a.compareTo(b)`, remains fully type-checked — the wildcard loosens the bound,
not the check inside the method body.

</details>

**Q3.** Read `public static <T extends Object & Comparable<? super T>> T max(Collection<? extends T>)`
end to end. What is the `Object &` doing there, given that every type already extends `Object`?

<details><summary>Answer</summary>

It is not adding a constraint — it is controlling which bound erasure picks. `javac` erases a type
variable to the erasure of its *leftmost* bound. Without `Object &`, the leftmost (only) bound would
be `Comparable`, and the method's erased return type and erased collection element type would become
`Comparable` instead of `Object`, changing the compiled method's binary descriptor from what it was
before generics existed. Putting `Object` first keeps the erased descriptor as
`(Ljava/util/Collection;)Ljava/lang/Object;`, matching the pre-Java-5 signature, while the full
`Comparable<? super T>` constraint is still enforced by `javac` at every call site and recorded in the
class file's `Signature` attribute for reflection to read.

</details>

**Q4.** In a `Map<Class<?>, Object>`-backed container, why does `get` call `type.cast(value)` instead of
an unchecked `(T)` cast?

<details><summary>Answer</summary>

Because a cast to an erased type variable `T` compiles to no bytecode instruction at all — there is
nothing at runtime for the JVM to check against, since `T` does not exist past compilation. A mismatch
would pass through `get` silently and only surface later, at whatever line first uses the value as the
wrong type, far from the actual bug. `Class.cast` is an ordinary instance method on the reified
`Class<T>` object; it performs a real `isInstance` check and throws `ClassCastException` immediately,
naming the expected and actual classes, right at the container boundary.

</details>

**Q5.** Why can a typesafe heterogeneous container not be keyed on `Class<List<Money>>`?

<details><summary>Answer</summary>

Because that object does not exist. Generics are erased, so `List<Money>` and `List<CashEntry>` — and
every other parameterisation of `List` — share exactly one `Class` object at runtime, `List.class`,
which is only typed as the raw `Class<List>`. Keying the container on that object would collide every
differently-parameterised `List` onto the same slot. Only reifiable types — types whose full
information survives erasure, which excludes any generic type with actual type arguments — can serve
as keys in this pattern.

</details>

**Q6.** What stops a caller of `VerdictBag.put(Class<T> type, T instance)` from passing a key and value
of different types?

<details><summary>Answer</summary>

Both parameters share the same type variable `T`, inferred once per call from both arguments together.
If the compiler infers `T = DocumentVerdict` from the second argument, the first argument must also be
a `Class<DocumentVerdict>` for the call to type-check — passing `ScreeningVerdict.class` alongside a
`DocumentVerdict` instance simply fails to compile. This only holds from inside `VerdictBag`, through
its own typed methods; a caller who obtains the backing `Map<Class<?>, Object>` directly, or goes
through a raw reference, can still bypass it.

</details>

**Q7.** Name one place outside this file's example where the JDK or a framework uses the same
"parameterise the key" idea.

<details><summary>Answer</summary>

`AnnotatedElement.getAnnotation(Class<T>)` in `java.lang.reflect` — a method, class, or field has an
open-ended, extensible set of annotations attached to it, each a different type, and `getAnnotation`
takes the annotation's `Class` token to return the precisely-typed instance rather than a common
supertype. `Collections.checkedCollection(Collection<E>, Class<E>)` uses a `Class` token the same way,
to recover a runtime check that erasure removed from the collection's own type parameter.

</details>

## Open questions

None.

---

**Leaves covered:** 1.21.20, 1.21.21 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 606
