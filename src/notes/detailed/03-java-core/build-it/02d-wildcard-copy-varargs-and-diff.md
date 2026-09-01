# 03 Java Core — Generic builds — wildcard copy, generic varargs, and the diff against the JDK — BUILD IT (§4.4 (4.4.8–4.4.10))

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [A self-referential builder and a super type token](02c-generic-builders-tokens-and-varargs.md) · Next: [Enum-shaped builds](03-enums-exceptions-resources.md)

Two things erasure refuses to check, and then the reckoning for the whole section.

The first is **variance**. A method that reads out of one list and writes into another has two
different requirements in one signature, and an invariant `List<T>` on both sides satisfies
neither — not because of a style rule, but because an invariant parameter position generates an
*equality* constraint on the inference variable, and two different equalities have no solution.
`copy(List<? super T> dest, List<? extends T> src)` downgrades both to subtyping constraints,
which do. The signature is the entire lesson; the body is nine lines.

The second is **reifiability**. A varargs parameter is an array parameter with call-site sugar,
so javac has to allocate the array — and when the element type is parameterised there is no
runtime array type to allocate. It fabricates a weaker one, warns that it checked nothing, and
the resulting array can be aliased and written through. The symptom lands as a
`ClassCastException` on a line containing no cast, in code that did nothing wrong.
`@SafeVarargs` silences the warning and verifies nothing; the reifiable parameter shape avoids
the question entirely.

Then the **§4.4 diff table** closes the section, covering everything files 6, 7,
[the builders and tokens file](02c-generic-builders-tokens-and-varargs.md) and this one built,
against what the JDK actually ships.

Every implementation below was compiled and run on **Oracle JDK 21.0.7 (build
21.0.7+8-LTS-245), macOS aarch64 (Apple silicon)**, and every `javac` diagnostic is pasted as
the compiler emitted it. The deliberate compile failures are as much output as the successful
runs.

The QuizStakes types the examples share:

```java
enum RestrictionType { DEPOSIT_BLOCKED, STAKE_BLOCKED, WITHDRAWAL_BLOCKED, SELF_EXCLUDED }
enum RestrictionSource { SYSTEM_ONBOARDING, SYSTEM_COMPLIANCE, ADMIN, CLIENT }

record Restriction(RestrictionType type, RestrictionSource source) {}
record CardRestriction(RestrictionType type, RestrictionSource source, String last4) {}
record LedgerEntry(String position, long minorUnits, String statusCode) {}
```

---

## 4.4.8 `copy` with wildcards, and without `[PROVE]`

The signature is the lesson, so start there. `copy` moves elements out of one list and into
another. The source is read from and never written to; the destination is written to and never
usefully read. Those are two different variance requirements and an invariant `List<T>` on both
sides can satisfy neither.

Work the argument, not the mnemonic:

- `src` is a **producer** of `T`. Every element it yields must be usable as a `T`, so its
  element type may be `T` or any subtype: `List<? extends T>`. The compiler captures the actual
  element type as a fresh variable bounded above by `T`. Reading gives a value assignable to
  `T`. Storing is impossible — the captured type could be any subtype, and no specific `T`
  value is guaranteed to fit it.
- `dest` is a **consumer** of `T`. It must accept every `T`, so its element type may be `T` or
  any supertype: `List<? super T>`. The capture is bounded *below* by `T`. Storing a `T`
  succeeds — `T` is assignable to every supertype of `T`. A typed read fails — the captured type
  could be any supertype, so the only thing the compiler can promise about an element is
  `Object`.

The asymmetry is not a convention. It falls directly out of which direction assignability runs.

### The build

```java
final class AuditSink {

    private static final int COPY_THRESHOLD = 10;

    /**
     * Overwrites the first src.size() slots of dest with the elements of src.
     * dest is a consumer of T, so ? super T; src is a producer of T, so ? extends T.
     */
    static <T> void copy(List<? super T> dest, List<? extends T> src) {
        Objects.requireNonNull(dest, "dest");
        Objects.requireNonNull(src, "src");
        int srcSize = src.size();
        if (dest.size() < srcSize) {
            throw new IndexOutOfBoundsException(
                    "Source does not fit in dest: src.size()=" + srcSize + " dest.size()=" + dest.size());
        }
        if (srcSize < COPY_THRESHOLD
                || (src instanceof java.util.RandomAccess && dest instanceof java.util.RandomAccess)) {
            for (int i = 0; i < srcSize; i++) dest.set(i, src.get(i));
        } else {
            var destIterator = dest.listIterator();
            var srcIterator = src.listIterator();
            for (int i = 0; i < srcSize; i++) {
                destIterator.next();
                destIterator.set(srcIterator.next());
            }
        }
    }

    private AuditSink() {}
}
```

The two-branch body mirrors `Collections.copy` deliberately: indexed `get`/`set` is fine for a
short list or two random-access lists, but on a large `LinkedList` it degrades to quadratic, so
above the threshold the iterator walk is used instead. `dest.set(i, src.get(i))` type-checks
because `src.get(i)` produces something assignable to `T` and `dest.set` accepts anything
assignable to `T` — the two captures meet at `T` and never have to be related to each other.

```java
public class CopyDemo {
    public static void main(String[] args) {
        List<Restriction> live = List.of(
                new Restriction(RestrictionType.STAKE_BLOCKED, RestrictionSource.SYSTEM_ONBOARDING),
                new Restriction(RestrictionType.WITHDRAWAL_BLOCKED, RestrictionSource.SYSTEM_COMPLIANCE),
                new Restriction(RestrictionType.SELF_EXCLUDED, RestrictionSource.CLIENT));

        List<Object> auditSink = new ArrayList<>(Arrays.asList(new Object[4]));
        AuditSink.<Restriction>copy(auditSink, live);
        System.out.println("audit sink   : " + auditSink);

        List<CardRestriction> cardBlocks = List.of(
                new CardRestriction(RestrictionType.DEPOSIT_BLOCKED, RestrictionSource.ADMIN, "4242"),
                new CardRestriction(RestrictionType.DEPOSIT_BLOCKED, RestrictionSource.ADMIN, "1881"));
        List<Record> recordSink = new ArrayList<>(Arrays.asList(new Record[3]));
        AuditSink.<CardRestriction>copy(recordSink, cardBlocks);
        System.out.println("record sink  : " + recordSink);

        List<Object> inferred = new ArrayList<>(Arrays.asList(new Object[3]));
        AuditSink.copy(inferred, live);
        System.out.println("inferred T   : " + inferred);

        try {
            List<Object> tooSmall = new ArrayList<>(Arrays.asList(new Object[2]));
            AuditSink.<Restriction>copy(tooSmall, live);
        } catch (IndexOutOfBoundsException e) {
            System.out.println("too small    : " + e.getClass().getName() + ": " + e.getMessage());
        }

        try {
            AuditSink.<Restriction>copy(List.of(null, null, null), live);
        } catch (UnsupportedOperationException e) {
            System.out.println("immutable    : " + e.getClass().getName() + " (List.of has no set)");
        } catch (NullPointerException e) {
            System.out.println("immutable    : " + e.getClass().getName() + " (List.of rejects null)");
        }
    }
}
```

```text
audit sink   : [Restriction[type=STAKE_BLOCKED, source=SYSTEM_ONBOARDING], Restriction[type=WITHDRAWAL_BLOCKED, source=SYSTEM_COMPLIANCE], Restriction[type=SELF_EXCLUDED, source=CLIENT], null]
record sink  : [CardRestriction[type=DEPOSIT_BLOCKED, source=ADMIN, last4=4242], CardRestriction[type=DEPOSIT_BLOCKED, source=ADMIN, last4=1881], null]
inferred T   : [Restriction[type=STAKE_BLOCKED, source=SYSTEM_ONBOARDING], Restriction[type=WITHDRAWAL_BLOCKED, source=SYSTEM_COMPLIANCE], Restriction[type=SELF_EXCLUDED, source=CLIENT]]
too small    : java.lang.IndexOutOfBoundsException: Source does not fit in dest: src.size()=3 dest.size()=2
immutable    : java.lang.NullPointerException (List.of rejects null)
```

Three call shapes: `List<Restriction>` into `List<Object>` (destination widened),
`List<CardRestriction>` into `List<Record>` (both widened, since a record's implicit supertype
is `java.lang.Record`), and inference with no explicit witness. The trailing `null` in the first
two outputs is the untouched fourth slot — `copy` overwrites a prefix and does not truncate. The
last case is a bonus finding: `List.of(null, null, null)` never gets as far as being immutable,
because `List.of` rejects `null` elements up front.

### Without wildcards

```java
final class InvariantSink {
    static <T> void copy(List<T> dest, List<T> src) {
        if (dest.size() < src.size()) throw new IndexOutOfBoundsException("Source does not fit in dest");
        for (int i = 0; i < src.size(); i++) dest.set(i, src.get(i));
    }
    private InvariantSink() {}
}
```

The body compiles. The call does not:

```java
List<Restriction> live = List.of(
        new Restriction(RestrictionType.STAKE_BLOCKED, RestrictionSource.SYSTEM_ONBOARDING));
List<Object> auditSink = new ArrayList<>(Arrays.asList(new Object[2]));
InvariantSink.copy(auditSink, live);
```

```text
InvariantCopy.java:18: error: method copy in class InvariantSink cannot be applied to given types;
        InvariantSink.copy(auditSink, live);
                     ^
  required: List<T>,List<T>
  found:    List<Object>,List<Restriction>
  reason: inference variable T has incompatible equality constraints Restriction,Object
  where T is a type-variable:
    T extends Object declared in method <T>copy(List<T>,List<T>)
1 error
```

`incompatible equality constraints Restriction,Object` names the mechanism precisely. An
invariant parameter position generates an **equality** constraint on the inference variable, and
`T = Object` and `T = Restriction` cannot both hold. The wildcards downgrade those to
*subtyping* constraints — `Object :> T` and `T :> Restriction` — which have the solution
`T = Restriction`. That is the whole of what PECS is doing.

### Both halves of the asymmetry, as compile errors

```java
public class PecsViolations {
    static <T> void illegalStoreIntoProducer(List<? extends T> src, T value) {
        T read = src.get(0);          // legal: every element IS-A T
        src.set(0, value);            // illegal
        System.out.println(read);
    }

    static <T> void illegalTypedReadFromConsumer(List<? super T> dest, T value) {
        dest.set(0, value);           // legal: T IS-A every supertype of T
        Object safe = dest.get(0);    // legal
        T typed = dest.get(0);        // illegal
        System.out.println(safe + " " + typed);
    }
}
```

```text
PecsViolations.java:8: error: incompatible types: T cannot be converted to CAP#1
        src.set(0, value);            // illegal
                   ^
  where T is a type-variable:
    T extends Object declared in method <T>illegalStoreIntoProducer(List<? extends T>,T)
  where CAP#1 is a fresh type-variable:
    CAP#1 extends T from capture of ? extends T
PecsViolations.java:17: error: incompatible types: CAP#1 cannot be converted to T
        T typed = dest.get(0);        // illegal
                          ^
  where T is a type-variable:
    T extends Object declared in method <T>illegalTypedReadFromConsumer(List<? super T>,T)
  where CAP#1 is a fresh type-variable:
    CAP#1 extends Object super: T from capture of ? super T
2 errors
```

The two `CAP#1` descriptions are the argument in the compiler's own words.
`CAP#1 extends T` — bounded above, so a `T` will not go in. `CAP#1 extends Object super: T` —
bounded below by `T` and above only by `Object`, so what comes out is only known to be `Object`.
Note the pleasing detail that the *only* value legally storable into a `List<? extends T>` is
`null`, which is a member of every reference type.

Variance in full, including `super` bounds on type parameters, wildcard capture rules, and why
arrays are covariant while generics are not:
[`../generics/01b-variance-and-wildcards.md`](../generics/01b-variance-and-wildcards.md).

> `? extends T` means "read-only in `T`"; `? super T` means "write-only in `T`". A method that
> does both to the same list cannot use either.

---

## 4.4.9 Heap pollution with generic varargs, and `@SafeVarargs` `[PROVE]`

A varargs parameter is an array parameter with call-site sugar: javac allocates the array and
fills it. When the element type is parameterised — a list of restrictions — the array javac must
allocate is not **reifiable**: there is no runtime type `List<Restriction>[]`, only `List[]`.
So javac creates a `List[]`, hands it over as if it were typed, and warns that it could not
check anything.

The gap that opens is that the array's runtime element type (`List`) is wider than its declared
element type (a list of restrictions). Alias it as `Object[]` — legal without a cast, since
arrays are covariant — and every array store check the VM performs is against `List`, which any
list passes. Store a list of strings. The array is now lying about its contents, which is what
**heap pollution** means: a variable whose runtime contents violate its declared type parameter.

### The demonstration

```java
public class HeapPollution2 {

    // No @SafeVarargs, and this method both stores into the array and lets it escape.
    static <T> List<T>[] polluteAndEscape(List<T>... pages) {
        Object[] erased = pages;
        erased[0] = List.of("STAKE_BLOCKED");
        return pages;
    }

    public static void main(String[] args) {
        List<Restriction> onboarding = new ArrayList<>(List.of(
                new Restriction(RestrictionType.STAKE_BLOCKED, RestrictionSource.SYSTEM_ONBOARDING)));
        List<Restriction> compliance = new ArrayList<>(List.of(
                new Restriction(RestrictionType.WITHDRAWAL_BLOCKED, RestrictionSource.SYSTEM_COMPLIANCE)));

        List<Restriction>[] pages = polluteAndEscape(onboarding, compliance);
        System.out.println("pages.getClass()   : " + pages.getClass().getName());
        System.out.println("pages[0].getClass(): " + pages[0].getClass().getName());
        Restriction blocked = pages[0].get(0);
        System.out.println("unreachable: " + blocked);
    }
}
```

The compiler warns in both places, and both warnings are worth reading:

```text
HeapPollution2.java:7: warning: [unchecked] Possible heap pollution from parameterized vararg type List<T>
    static <T> List<T>[] polluteAndEscape(List<T>... pages) {
                                                     ^
  where T is a type-variable:
    T extends Object declared in method <T>polluteAndEscape(List<T>...)
HeapPollution2.java:19: warning: [unchecked] unchecked generic array creation for varargs parameter of type List<Restriction>[]
        List<Restriction>[] pages = polluteAndEscape(onboarding, compliance);
                                                    ^
2 warnings
```

One at the **declaration** ("possible heap pollution") and one at every **call site**
("unchecked generic array creation"). The call-site warning is the noisy one, and removing it
for callers is the practical reason `@SafeVarargs` exists.

```text
pages.getClass()   : [Ljava.util.List;
pages[0].getClass(): java.util.ImmutableCollections$List12
Exception in thread "main" java.lang.ClassCastException: class java.lang.String cannot be cast to class Restriction (java.lang.String is in module java.base of loader 'bootstrap'; Restriction is in unnamed module of loader 'app')
	at HeapPollution2.main(HeapPollution2.java:22)
```

`[Ljava.util.List;` — the array's runtime type has no type argument at all, which is why the
`aastore` of a list of strings raised nothing. And the failure is reported at
`HeapPollution2.java:22`, which is:

```java
Restriction blocked = pages[0].get(0);
```

There is **no cast on that line**. The blame lands on a caller that did nothing wrong. The cast
is one javac inserted, visible only in the bytecode:

```text
     106: aaload
     108: invokeinterface #76,  2           // InterfaceMethod java/util/List.get:(I)Ljava/lang/Object;
     113: checkcast     #17                 // class Restriction
     116: astore        4
```

`List.get` erases to return `Object`, so every generic read is followed by a `checkcast` to the
declared type parameter. Under normal circumstances that check is provably redundant. Once the
heap is polluted it is the thing that fires, at a source line the reader will stare at for
twenty minutes. **That displacement between cause and symptom is the entire lesson**, and it is
why javac warns at the declaration rather than waiting for a failure.

### Fix one: `@SafeVarargs`, and its precondition

```java
@SafeVarargs
static <T> int countPages(List<T>... pages) {
    int total = 0;
    for (List<T> page : pages) total += page.size();
    return total;
}
```

```text
@SafeVarargs countPages : 2
```

Compiles warning-free at the declaration and at every call site. The annotation is a
**programmer assertion**, not a check. `java.lang.SafeVarargs`' own javadoc in JDK 21 states the
contract and its two preconditions:

> A programmer assertion that the body of the annotated method or constructor does not perform
> potentially unsafe operations on its varargs parameter. Applying this annotation to a method
> or constructor suppresses unchecked warnings about a *non-reifiable* variable arity (vararg)
> type and suppresses unchecked warnings about parameterized array creation at call sites.

Concretely, the method must satisfy both of:

1. it never **stores** into the varargs array, and
2. it never lets the array **escape** — not returned, not assigned to a field, not passed to
   anything that might keep it, and not aliased to a wider array type through which a store
   could happen.

`countPages` only reads and only iterates, so it qualifies. `polluteAndEscape` violates both.
The javadoc's own counterexample is the same aliasing this file demonstrated, and it says
plainly that the unsafe store "compiles without warnings" — so annotating an unsafe method
silences the only warning that would have caught it.

Where the annotation is legal in Java 21, from that same javadoc's normative list — it is a
compile-time error if the declaration is a fixed-arity method or constructor, or is a variable
arity method that is neither `static` nor `final` nor `private`:

| Declaration | Legal in 21? | Verified how |
|---|---|---|
| `static` method | yes | compiles |
| `final` instance method | yes | compiles |
| `private` instance method | yes (**since Java 9**) | compiles at `--release 9` and `21`, rejected at `--release 8` |
| constructor | yes | compiles |
| non-`final`, non-`private` instance method | **no** | compile error, below |
| fixed-arity method | **no** | per javadoc |

The rejection, measured:

```text
SafeVarargsPlacement.java:17: error: Invalid SafeVarargs annotation. Instance method <T>plainInstanceRejected(List<T>...) is neither final nor private.
    <T> int plainInstanceRejected(List<T>... pages) { return pages.length; }
            ^
1 error
```

The reason is that an overridable method cannot make the assertion on its overriders' behalf —
a subclass could override it with a body that pollutes, while the call site still sees the
annotation on the base declaration. The Java 9 change is visible directly:

```text
--- release 8 ---
PrivateSafeVarargs8.java:4: error: Invalid SafeVarargs annotation. Instance method <T>privateInstance(List<T>...) is not final.
    private <T> int privateInstance(List<T>... pages) { return pages.length; }
1 error
--- release 9 ---
--- release 21 ---
```

Java 8 demanded `static` or `final`; Java 9 added `private`, because a private method is not
overridable either and the earlier rule was simply incomplete. Interviewers ask for the Java 8
form, so know both.

### Fix two: do not take a varargs parameter

```java
static <T> int countPagesReifiable(List<List<T>> pages) {
    int total = 0;
    for (List<T> page : pages) total += page.size();
    return total;
}
```

```text
reifiable countPages    : 2
```

No annotation, no warning, no assertion, nothing to get wrong. `List<List<T>>` is a perfectly
ordinary reifiable-at-runtime object — the generic information is checked statically and the
runtime object is just an `ArrayList` of `ArrayList`s, with no array store check to subvert.
The cost is `List.of(a, b)` at the call site instead of bare `a, b`. That is the trade: one pair
of parentheses against a class of bug that surfaces as a `ClassCastException` in unrelated code.
Take the parentheses unless the method is on a public API's hot path and the ergonomics matter,
which is the case `List.of` and `EnumSet.of` are in and yours probably is not.

Full treatment of the unchecked-warning taxonomy, `-Xlint:varargs` versus `-Xlint:unchecked`,
and the JLS rules on non-reifiable types:
[`../generics/03c-internals-heap-pollution-and-safevarargs.md`](../generics/03c-internals-heap-pollution-and-safevarargs.md).

**Interview:** "What does `@SafeVarargs` do?" — it suppresses two warnings and asserts a
property the compiler cannot verify. It makes nothing safe. The correct follow-up answer is the
two-part precondition: no store into the array, no escape of the array.

> Heap pollution is a variable whose runtime contents contradict its declared type parameter.
> Generic varargs is the commonest way to create it, because the array javac fabricates is
> typed more weakly at runtime than at compile time.

---

## 4.4.10 §4.4 diff table: this section's builds against the JDK

Covering everything §4.4 built across files 6, 7, 8 and this one.

| Ours | JDK counterpart | Edge cases | Intrinsics | Serialization | Null policy | Thread safety | Allocation tricks | Why the JDK bothers |
|---|---|---|---|---|---|---|---|---|
| `MyOptional<T>` | `java.util.Optional<T>` | JDK adds `or`, `stream`, `ifPresentOrElse`, `orElseThrow()` no-arg; `get()` throws `NoSuchElementException("No value present")` | no intrinsic; the JIT relies on escape analysis to scalar-replace a non-escaping `Optional` | **not `Serializable`, deliberately** — `Serializable.class.isAssignableFrom(Optional.class)` is `false`, and `writeObject` gives `java.io.NotSerializableException: java.util.Optional`; serializability would freeze it as a state-bearing type when it is documented value-based | `Optional.of(null)` throws NPE; `ofNullable` maps null to empty; `Optional` itself is never null by contract | immutable and effectively final fields, so safely publishable; the *contained* value's own safety is the caller's problem | one shared `EMPTY` singleton for the empty case, so `Optional.empty()` allocates nothing | to make "absent" a type-system fact rather than a convention, so a stream terminal op can return one uniformly |
| `Pair<A,B>` | `Map.Entry<K,V>` — and **the JDK ships no general `Pair`** | `Map.entry` rejects nulls; `AbstractMap.SimpleEntry` accepts them; `setValue` is optional and unsupported on immutable entries | no intrinsic | `Map.entry` returns `java.util.KeyValueHolder`, which is **not** `Serializable`; `AbstractMap.SimpleEntry` **is**. Two shapes, two answers | `Map.entry(k, v)` NPEs on either argument; `SimpleEntry` allows both null | `KeyValueHolder` immutable; `SimpleEntry` has mutable `value`, unsynchronised | none beyond the two-field object; `record`-shaped by hand for `equals`/`hashCode` contract compliance with `Map.Entry` | deliberately *not* shipped as `Pair`: a general pair has no domain meaning, `getFirst`/`getSecond` destroys the call site's readability, and a `record` gives you a named two-field type in one line |
| `Result<T,E>` | **neither `Result` nor `Either` exists** in `java.base` | checked exceptions cover the same ground with stack unwinding instead of a return value; `Optional` covers the E-less case | no intrinsic; a thrown exception costs a stack walk, a returned `Result` does not | your `Result` is `Serializable` only if you make it so and only if `T` and `E` are; exceptions are `Serializable` by contract (`Throwable implements Serializable`) | your policy; the JDK's `Optional` refuses null and that is the precedent worth copying | immutable if the payloads are | `Result` allocates one object per call, always; an exception allocates plus fills in a stack trace unless suppressed via the four-arg `Throwable` constructor | the language chose checked exceptions in 1996 and the compiler enforces them, which a return type cannot; adding `Either` now would give two incompatible error idioms in one standard library |
| `copy(List<? super T>, List<? extends T>)` | `Collections.copy` | **throws `IndexOutOfBoundsException("Source does not fit in dest")` and does not grow the destination**, verified against JDK 21 source and by running it; on failure `dest` is left untouched | no intrinsic; large `RandomAccess`-to-`RandomAccess` copies never reach `System.arraycopy` because the `List` interface offers no bulk-set | not applicable — a static method | NPEs from the underlying lists; no explicit null check on the elements | none; a concurrent structural modification of either list during the copy is unspecified | `COPY_THRESHOLD = 10` picks indexed `get`/`set` for short lists and a `ListIterator` walk above it, so a `LinkedList` destination is linear rather than quadratic | it is one of the two places in `java.util` where PECS is visible in a signature everybody reads, and it predates `List.addAll` being enough for most callers |
| typesafe heterogeneous container over `Map<Class<?>, Object>` | `AnnotatedElement.getAnnotation(Class<T>)`, `Collections.checkedList` | `getAnnotation` returns null for absent rather than throwing; `checkedList` throws `ClassCastException` at insertion time, converting a latent pollution into an immediate failure | no intrinsic; `Class.cast` is a plain `checkcast` after a null test and the JIT folds it when the class is a constant | `Class` is `Serializable` but resolves by name on read, so a serialized container is only portable where the classes are | `Class.cast(null)` returns null, so a null value survives the round trip and defeats the type check | `HashMap`-backed, so unsynchronised; wrap or use `ConcurrentHashMap` | `Class.cast` allocates nothing; the pattern's cost is entirely the map | `<T extends Annotation> T getAnnotation(Class<T>)` is the canonical real use: a single map keyed by type, returning the precise static type, with the unchecked cast confined to one library method |
| generic `Stack<E>` over `(E[]) new Object[]` | `ArrayDeque<E>` — and `java.util.Stack`, which nobody should use | `ArrayDeque` **prohibits null elements**, so it cannot represent "a null was pushed"; `Stack` allows null; ours allows whatever the array allows | no intrinsic; `ArrayDeque` growth uses `System.arraycopy`, which is intrinsified | `ArrayDeque` and `Stack` are both `Serializable`; ours is not unless declared so | `ArrayDeque` NPEs on `push(null)` by design, so null cannot be confused with empty | none of the three are thread-safe; `Stack extends Vector` so its methods **are** synchronised, which is exactly why it is slow and still not composably safe | `ArrayDeque` keeps a power-of-two array with head/tail indices and masks instead of shifting, so `pop` moves no elements; a `Vector`-based `Stack` pays `synchronized` on every access | `java.util.Stack`'s own javadoc points at `Deque` and shows `Deque<Integer> stack = new ArrayDeque<Integer>();`; `ArrayDeque`'s javadoc says it "is likely to be faster than `Stack` when used as a stack" |
| `TypeRef<T>` | **nothing in `java.base`** | third-party equivalents: Jackson `TypeReference<T>`, Guice/Guava `TypeLiteral<T>`/`TypeToken<T>`, Spring `ParameterizedTypeReference<T>`; Guava's `TypeToken` additionally resolves type variables against a context type | no intrinsic; `getGenericSuperclass()` parses the `Signature` attribute string on each call unless the JDK caches it | `Type` implementations are not a serialization contract; serialize the `getTypeName()` string and re-resolve | `getActualTypeArguments()` never returns null; a raw subclass yields `Object` from `getGenericSuperclass` and must be rejected explicitly | immutable after construction, so shareable; the class-loading side effect is the hazard, not the state | one anonymous class **loaded per call site** — hoist to `static final` or leak metaspace | the JDK does not bother because `java.base` has no deserialization framework that needs it; the frameworks that do all ship their own |
| `LimitSet.Builder<T extends Builder<T>>` | a `record` | a record gives `equals`/`hashCode`/`toString`/accessors and a canonical constructor for validation, but **cannot be extended**, has no optional-parameter ergonomics, and gets unreadable past about five components | no intrinsic; record accessors are trivially inlined; `record` `equals` is generated, not intrinsified | records are `Serializable` if declared so, and deserialize **through the canonical constructor**, so validation is not bypassed — unlike classic `Serializable`, which skips constructors entirely | yours; put the checks in the product constructor, not the setters, so cross-field invariants can see every field | records are shallowly immutable and safely publishable; a builder is mutable and single-threaded by construction | a builder allocates one extra object per product and is a pure loss when every field is required; a record allocates only the product | the JDK ships no builder framework because there is no one shape; Java 21's answer for the flat immutable-carrier case is `record`, and the self-typed builder is for the hierarchical case a record cannot express |

Two rows are worth restating because they are the ones people get wrong under questioning.
**`Optional` is not `Serializable`, and that is a deliberate design decision**, not an
oversight — measured above as `NotSerializableException`. **`Collections.copy` does not grow the
destination**; it throws `IndexOutOfBoundsException("Source does not fit in dest")`, and the
message string is verbatim from the JDK 21 source at `Collections.java:585`.

---

## Pitfalls

### Believing `List<? extends T>` is a list you can add to

**Wrong**

```java
static <T> void illegalStoreIntoProducer(List<? extends T> src, T value) {
    src.set(0, value);
}
```

```text
PecsViolations.java:8: error: incompatible types: T cannot be converted to CAP#1
        src.set(0, value);            // illegal
                   ^
  where CAP#1 is a fresh type-variable:
    CAP#1 extends T from capture of ? extends T
```

**Right**

Pick the bound from the direction of data flow. If the method stores into the list, the list is
a consumer and the bound is `? super T`:

```java
static <T> void storeIntoConsumer(List<? super T> dest, T value) { dest.set(0, value); }
```

If it must both read `T` and store `T`, neither wildcard works and the parameter has to be an
invariant `List<T>`.

**Why people believe it:** `? extends T` reads as "a wider set of acceptable element types",
which sounds permissive. It is the opposite: the compiler knows the element type is *some*
subtype of `T` but not which, so the only value provably assignable to it is `null`.

### Believing `@SafeVarargs` makes a method safe rather than asserting that it already is

**Wrong**

```java
@SafeVarargs
static <T> List<T>[] polluteAndEscape(List<T>... pages) {
    Object[] erased = pages;
    erased[0] = List.of("STAKE_BLOCKED");
    return pages;
}
```

With the annotation, the declaration and every call site compile **silently**. Without it, javac
at least says `warning: [unchecked] Possible heap pollution from parameterized vararg type
List<T>`. Either way the caller gets:

```text
Exception in thread "main" java.lang.ClassCastException: class java.lang.String cannot be cast to class Restriction
	at HeapPollution2.main(HeapPollution2.java:22)
```

on a line containing no cast.

**Right**

```java
@SafeVarargs
static <T> int countPages(List<T>... pages) {
    int total = 0;
    for (List<T> page : pages) total += page.size();
    return total;
}
```

No store into the array, no escape of the array — the assertion is true, so the annotation is
honest. When in doubt, take `List<List<T>>` instead and the question does not arise.

**Why people believe it:** the name says "safe", and applying it makes the warnings disappear,
which looks like the compiler agreeing. The javadoc is explicit that it is "a programmer
assertion", and it notes that the unsafe aliasing above "compiles without warnings" — the
annotation removes the only signal that would have caught the bug.

### Believing `Collections.copy` grows the destination

**Wrong**

```java
List<String> dest = new ArrayList<>(List.of("CLIENT_CASH_AVAILABLE"));
Collections.copy(dest, List.of("SUSPENSE", "HOUSE_REVENUE"));
```

```text
Collections.copy: java.lang.IndexOutOfBoundsException: Source does not fit in dest
dest after failed copy: [CLIENT_CASH_AVAILABLE]
```

**Right**

```java
List<String> dest = new ArrayList<>(src);              // if you want a fresh copy
// or, to fill an existing sink:
List<Object> auditSink = new ArrayList<>(Arrays.asList(new Object[4]));
AuditSink.<Restriction>copy(auditSink, live);           // dest pre-sized, indices exist
```

```text
audit sink   : [Restriction[type=STAKE_BLOCKED, source=SYSTEM_ONBOARDING], Restriction[type=WITHDRAWAL_BLOCKED, source=SYSTEM_COMPLIANCE], Restriction[type=SELF_EXCLUDED, source=CLIENT], null]
```

**Why people believe it:** the name matches `System.arraycopy` and `Arrays.copyOf`, and
`copyOf` *does* allocate a right-sized result. `Collections.copy` is a `set`-based overwrite of
an existing list, so index `i` must already exist. `new ArrayList<>(10)` sets *capacity*, not
size, and `size()` is still `0` — which is the version of this mistake that survives code
review.

---

## Cheat sheet

| Thing | Form | Key fact |
|---|---|---|
| PECS | producer `? extends T`, consumer `? super T` | invariant position ⇒ **equality** constraint on inference |
| `? extends T` | read `T`, store only `null` | capture `CAP#1 extends T` |
| `? super T` | store `T`, read only `Object` | capture `CAP#1 extends Object super: T` |
| `Collections.copy` | `copy(List<? super T> dest, List<? extends T> src)` | `IndexOutOfBoundsException("Source does not fit in dest")`; never grows; `COPY_THRESHOLD = 10` |
| Generic varargs | array is non-reifiable; runtime type is `[Ljava.util.List;` | two warnings: declaration + every call site |
| Heap pollution symptom | `ClassCastException` at a line with no cast | javac's inserted `checkcast` after an erased `get` |
| `@SafeVarargs` preconditions | no store into the array, no escape of the array | assertion only; verifies nothing |
| `@SafeVarargs` legal on | `static`, `final` instance, `private` instance (**Java 9+**), constructors | error on overridable instance methods and fixed arity |
| Reifiable alternative | `List<List<T>>` instead of a varargs parameter | no annotation, no warning, nothing to get wrong |
| `Optional` serialization | **not `Serializable`** | `NotSerializableException: java.util.Optional` |
| `Map.entry` serialization | `KeyValueHolder`: **not** `Serializable`; `SimpleEntry`: is | and `Map.entry` NPEs on null |

---

## Self-test

**Q1.** `AuditSink.copy(auditSink, live)` with `List<Object>` and `List<Restriction>` works, but
the invariant `copy(List<T>, List<T>)` fails with "incompatible equality constraints". What is
the mechanical difference?

<details><summary>Answer</summary>

An invariant parameter position generates an **equality** constraint on the inference variable:
`List<Object>` for `List<T>` requires `T = Object`, and `List<Restriction>` for `List<T>`
requires `T = Restriction`. Both cannot hold, so inference fails and javac says exactly that —
`reason: inference variable T has incompatible equality constraints Restriction,Object`. The
wildcards change the constraint kind. `List<? super T>` against `List<Object>` gives the
subtyping constraint `Object :> T`; `List<? extends T>` against `List<Restriction>` gives
`T :> Restriction`. A subtyping pair has a solution — `T = Restriction` satisfies both — where an
equality pair does not. PECS is not a style rule; it is choosing constraint kinds that a solver
can satisfy.

</details>

**Q2.** What is the only value you can legally store into a `List<? extends Restriction>`, and
why?

<details><summary>Answer</summary>

`null`. The wildcard captures as a fresh type variable bounded above by `Restriction` —
javac prints it as `CAP#1 extends T from capture of ? extends T` — so the compiler knows the
list's element type is *some* subtype of `Restriction` but not which one. A `Restriction` value
is not provably assignable to an unknown subtype, and neither is a `CardRestriction`, since the
capture might be some other subtype entirely. `null` is a member of every reference type, so it
is the sole value that type-checks. Practically this makes `? extends` a read-only view, which
is the entire point.

</details>

**Q3.** A `ClassCastException` fires on `Restriction blocked = pages[0].get(0);` — a line with no
cast in it. Explain the mechanism.

<details><summary>Answer</summary>

`List.get` erases to `Object get(int)`, so every generic read is compiled as
`invokeinterface List.get` followed by a `checkcast` to the declared type parameter — visible in
`javap -c` as `113: checkcast #17 // class Restriction`. Normally that check is provably
redundant, because static typing guarantees the element type. But the array came from a generic
varargs parameter, so its runtime type is `[Ljava.util.List;` with no type argument. Some earlier
code aliased it as `Object[]` and stored a `List<String>` into slot 0, which passed the VM's
array store check because a `List` was being stored into a `List[]`. The heap is now polluted:
`pages[0]` is declared `List<Restriction>` and holds a `List<String>`. The compiler-inserted
`checkcast` is the first thing to notice, so the exception is reported at the innocent read site
rather than at the guilty store.

</details>

**Q4.** Where is `@SafeVarargs` legal in Java 21, and what changed in Java 9?

<details><summary>Answer</summary>

Legal on `static` methods, `final` instance methods, `private` instance methods and
constructors. It is a compile-time error on a fixed-arity declaration, and on a variable-arity
instance method that is neither `static` nor `final` nor `private` — javac's wording is
`Invalid SafeVarargs annotation`, followed by the offending method's signature and
`is neither final nor private.` The reason is overridability: a base declaration cannot assert safety on behalf of an override that might
pollute, while call sites see the annotation on the base. Java 8 allowed only `static` and
`final`; Java 9 added `private`, since a private method is not overridable either and the
original rule was simply incomplete. Compiling a private annotated method at `--release 8`
still produces the old error — `is not final` — and at `--release 9` and `21` it compiles clean.

</details>

**Q5.** Why does the JDK ship `Optional` but not `Pair`, `Either` or `Result`?

<details><summary>Answer</summary>

`Optional` exists because the stream API needed one uniform representation for "a terminal
operation produced no value", and that shape is genuinely universal — there is exactly one way
to be absent. `Pair` is refused because a pair has no domain meaning: `getFirst`/`getSecond`
destroys readability at every call site, and since Java 16 a `record` gives you a named
two-field carrier with `equals`, `hashCode` and accessors in one line, which is better than any
general `Pair` could be. `Map.Entry` exists only because maps need a key-value view, not as a
general pair. `Either` and `Result` are refused because Java already committed to checked
exceptions in 1996 and the compiler enforces them, which a return type cannot; adding a
returned-error idiom to `java.base` now would leave two incompatible error-handling conventions
in one standard library. Note also that `Optional` is deliberately **not** `Serializable` —
`writeObject` gives `NotSerializableException: java.util.Optional` — because serializability
would freeze it as a state-bearing type when it is documented as value-based.

</details>

---

## Open questions

- none

---

**Leaves covered:** 4.4.8, 4.4.9, 4.4.10 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 712
