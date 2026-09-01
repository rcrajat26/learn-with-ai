# 02 Java Collections — Immutability and views — INTERMEDIATE (§2.4.7–2.4.10)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [immutable-collections/03a-immutability-tiers-comparison-table.md](03a-immutability-tiers-comparison-table.md) · Next: [immutable-collections/03c-null-queries-and-guava.md](03c-null-queries-and-guava.md)

The five-tier immutability ladder and its comparison table are in
[03-immutability-tiers.md](03-immutability-tiers.md) and
[03a-immutability-tiers-comparison-table.md](03a-immutability-tiers-comparison-table.md).
This file assumes them and asks a narrower question: **what exactly do the `of` factories refuse,
and when?** Every rejection lands in one of five places, and the distinction is the subject.

| Where | Detected by | Example | You get |
|---|---|---|---|
| **Compile time** | absence of an overload | `Map.of` with 11 pairs | "no suitable method found" |
| **Construction time** | private constructor | `Set.of("a","a")` | `IllegalArgumentException` |
| **Construction time** | `Objects.requireNonNull` | `List.of("a", null)` | `NullPointerException` |
| **Query time** | `contains`/`indexOf` guards | `List.of("a").contains(null)` | `NullPointerException` |
| **Mutation time** | `uoe()` in `AbstractImmutableCollection` | `List.of("a").add("b")` | `UnsupportedOperationException` |

Rows 1–3 are this file. Row 4 — the query-time guards, and the `allowNulls` field that decides
them — is [03c-null-queries-and-guava.md](03c-null-queries-and-guava.md).

**No diagram belongs to this row** — the structure a diagram would carry (factory → private
class, by arity) is in the tables below. All transcripts: **Oracle JDK 21.0.7, macOS aarch64**.
Source citations are `/tmp/jc49src/java.base/java/util/`.

---

## 1. Validate-at-construction: duplicate rejection and the arity cap (2.4.7, 2.4.8, 2.4.9)

**Mental model.** `Set.of`/`Map.of` are a **turnstile with a counter**. Each element goes through
one at a time; present a face already admitted and the turnstile slams shut — it does not let the
second silently merge into the first. That is the opposite of `HashSet.add`, a doorman who shrugs
and returns `false`. `List.of` has no turnstile: lists may repeat.

**Why it exists.** Pre-Java-9 the idiom was
`Collections.unmodifiableSet(new HashSet<>(Arrays.asList("retry", "async", "retry")))`. `HashSet`
deduplicates, so a copy-paste error compiled, ran, and quietly held two elements instead of three
forever. A duplicate in a literal argument list is a *typo*, not a *value*, so Java 9 made it an
exception.

**When to reach for which:**

| You have | Use | Duplicates | Nulls |
|---|---|---|---|
| Literal arguments you typed | `Set.of` / `Map.of` | `IllegalArgumentException` | NPE |
| A runtime collection of unknown provenance | `Set.copyOf` / `Map.copyOf` | **silently deduplicated** | NPE |
| More than 10 map pairs, literal | `Map.ofEntries(entry(..), ..)` | `IllegalArgumentException` | NPE |
| A stream | `collect(toUnmodifiableSet())` | silently deduplicated | NPE |
| Duplicates are legitimate data | `new HashSet<>(coll)`, then wrap | silently deduplicated | permitted |

**Insight:** `Set.copyOf` and `Set.of` disagree on purpose. `Set.copyOf` funnels through
`new HashSet<>(coll)` before building, so it *accepts* what `Set.of` rejects. **`of` validates a
literal; `copyOf` sanitises a value.**

### Mechanism

Two-element sets are special-cased; three-and-up go through the open-addressed probe table.
`ImmutableCollections.java` lines 795–802 (`Set12`):

```java
        Set12(E e0, E e1) {
            if (e0.equals(Objects.requireNonNull(e1))) { // implicit nullcheck of e0
                throw new IllegalArgumentException("duplicate element: " + e0);
            }

            this.e0 = e0;
            this.e1 = e1;
        }
```

`Objects.requireNonNull(e1)` rejects a null second argument and returns it; `e0.equals(...)`
dereferences `e0`, so a null *first* argument throws NPE from the receiver — that is what
"implicit nullcheck of e0" means, and it is why both positions throw despite only one explicit
check. Equal elements produce `IllegalArgumentException` carrying the offender.

Lines 917–930 (`SetN`), the general arm:

```java
        SetN(E... input) {
            size = input.length; // implicit nullcheck of input

            elements = (E[])new Object[EXPAND_FACTOR * input.length];
            for (int i = 0; i < input.length; i++) {
                E e = input[i];
                int idx = probe(e); // implicit nullcheck of e
                if (idx >= 0) {
                    throw new IllegalArgumentException("duplicate element: " + e);
                } else {
                    elements[-(idx + 1)] = e;
                }
            }
        }
```

`EXPAND_FACTOR` is `2` (line 140), so the table is twice the element count — the invariant that at
least one slot stays null is what lets `probe` terminate. `probe` returns a **non-negative index**
when the element is already present and the **encoded insertion point** `-(idx + 1)` when it is
not; a non-negative result is therefore exactly "duplicate", and the check costs nothing beyond
the probe you were already doing.

`MapN` lines 1183–1200 is the same shape over an interleaved key/value table:

```java
            for (int i = 0; i < input.length; i += 2) {
                    K k = Objects.requireNonNull((K)input[i]);
                    V v = Objects.requireNonNull((V)input[i+1]);
                int idx = probe(k);
                if (idx >= 0) {
                    throw new IllegalArgumentException("duplicate key: " + k);
                } else {
                    int dest = -(idx + 1);
                    table[dest] = k;
                    table[dest+1] = v;
                }
            }
```

Keys *and* values are null-checked; only keys are duplicate-checked. Two identical values under
different keys are legal.

### A consequence of the probe table: iteration order is salted per JVM run

Because `SetN`/`MapN` place elements at `probe`-determined slots, and the probe sequence is
perturbed by a salt seeded once per JVM, **`Set.of`/`Map.of` iteration order is deliberately
unstable across JVM runs and stable within one run.** Two runs of the same program:

```
run 1:  Set.of order: [a, f, e, d, c, b]
run 2:  Set.of order: [a, b, c, d, e, f]
```

Three consecutive prints inside a single JVM, by contrast, were identical
(`[a, b, c, d, e, f]` all three times). That combination — stable locally, different in CI — is
what makes an order-dependent assertion so hard to diagnose. The randomisation is intentional: it
exists so nobody can accidentally depend on the order.
[03c](03c-null-queries-and-guava.md) uses this same transcript as the evidence base for the Guava
ordering contrast, where the guarantee runs the other way.

### The arity cap `[NUM]`

The cap is not a runtime limit — it is **the absence of an overload**. Counted from the sources:

| Factory | Fixed-arity overloads | Argument counts | Varargs escape | Total |
|---|---|---|---|---|
| `List.of` | 11 (`List.java` 920–1129) | 0, 1, 2 … 10 elements | `of(E...)` line 1161 | **12** |
| `Set.of` | 11 (`Set.java` 454–662) | 0, 1, 2 … 10 elements | `of(E...)` line 695 | **12** |
| `Map.of` | 11 (`Map.java` 1347–1624) | 0, 2, 4 … 20 arguments | `ofEntries(Entry...)` 1663 | **12** |

`Map.of` arithmetic explicitly: arguments are key/value **interleaved**, so an *n*-pair overload
takes `2n` arguments. Declared overloads run `2n` for `n = 0..10`, i.e. argument counts
**0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20 — 11 overloads, 0–10 pairs, 20 arguments maximum.**
An eleventh pair has no overload, so it is a *compile error*, not an exception.

### Proof — every throw inside its own try/catch

```java
import java.util.*;

public class RejectionDemo {
    static String attempt(java.util.function.Supplier<Object> s) {
        try { return String.valueOf(s.get()); }
        catch (RuntimeException e) { return e.getClass().getSimpleName() + ": " + e.getMessage(); }
    }

    public static void main(String[] args) {
        System.out.println("Set.of(a,a)            -> " + attempt(() -> Set.of("a", "a")));
        System.out.println("Set.of(a,b,c,a)        -> " + attempt(() -> Set.of("a", "b", "c", "a")));
        System.out.println("Map.of(a=1,a=2)        -> " + attempt(() -> Map.of("a", 1, "a", 2)));
        System.out.println("Map.ofEntries(a=1,a=2) -> "
                + attempt(() -> Map.ofEntries(Map.entry("a", 1), Map.entry("a", 2))));
        System.out.println("List.of(a,a)           -> " + attempt(() -> List.of("a", "a")));

        List<String> dup = List.of("a", "b", "a", "b", "c");
        System.out.println("Set.copyOf(" + dup + ") -> " + Set.copyOf(dup)
                + " size=" + Set.copyOf(dup).size());

        Map.Entry<String, Integer>[] es = new Map.Entry[12];
        for (int i = 0; i < 12; i++) es[i] = Map.entry("k" + i, i);
        Map<String, Integer> big = Map.ofEntries(es);
        System.out.println("Map.ofEntries 12 pairs -> size " + big.size()
                + " impl " + big.getClass().getSimpleName());
    }
}
```

Real output:

```
Set.of(a,a)            -> IllegalArgumentException: duplicate element: a
Set.of(a,b,c,a)        -> IllegalArgumentException: duplicate element: a
Map.of(a=1,a=2)        -> IllegalArgumentException: duplicate key: a
Map.ofEntries(a=1,a=2) -> IllegalArgumentException: duplicate key: a
List.of(a,a)           -> [a, a]
Set.copyOf([a, b, a, b, c]) -> [a, b, c] size=3
Map.ofEntries 12 pairs -> size 12 impl MapN
```

`List.of("a","a")` returning `[a, a]` is the control: duplicate rejection is a set/map property,
never a list property. `Map.of` with all 10 pairs (20 args) measures `size=10 impl=MapN`.

**Pitfall:** *Wrong belief* — "the 10-element limit is a capacity limit; past 10 the factory
throws or degrades." *Symptom* — people build a `HashSet` in a loop "because `Set.of` only holds
10", or hunt for a runtime exception that never comes. *Fix* — an 11th argument to
`Set.of`/`List.of` silently binds `of(E...)` and works at any size (measured: 11 args → `ListN`
size 11). Only `Map.of` lacks a varargs form and forces `Map.ofEntries`.

> **Definition.** The Java 9 `of` factories validate at construction: `Set.of`/`Map.of` throw
> `IllegalArgumentException` on a duplicate element or key (from `Set12`, `SetN`, `MapN`), all
> three factories throw `NullPointerException` on a null argument, and `Map.of`'s 10-pair ceiling
> is a compile-time consequence of having only 11 fixed-arity overloads (0–20 arguments), with
> `Map.ofEntries(Entry...)` as the only varargs escape.

---

## 2. The overload ladder, and what it actually saves (2.4.10)

**Mental model.** Eleven near-identical methods look like generated boilerplate. They are a
**bypass around the varargs machinery**: `f(E...)` compiles at the *call site* into
`new Object[]{a, b, c}` followed by the call, so a varargs-only factory makes the caller pay for
an array before the factory runs an instruction. The ladder exists so `List.of("a")` costs one
object, not two.

**Why it exists.** Small immutable lists are the overwhelmingly common case. The authors spent 11
declarations to keep it minimal, because a factory that allocates a throwaway array per call is a
measurable regression against the `Arrays.asList` it replaces. **When it matters:** arity 1–2,
where array allocation vanishes entirely; it stops mattering at arity 3+ (below).
**Unverified:** whether C2 scalarises the non-escaping array under escape analysis is not measured
here — plausible, unproven; recorded in [03c](03c-null-queries-and-guava.md)'s open questions.

### The honest accounting `[NUM]` `[RESEARCH]`

The syllabus says the overloads exist "to avoid array allocation". **That is true only for arity
0, 1 and 2.** `List.java` lines 920–958:

```java
    static <E> List<E> of() {
        return (List<E>) ImmutableCollections.EMPTY_LIST;
    }

    static <E> List<E> of(E e1) {
        return new ImmutableCollections.List12<>(e1);
    }

    static <E> List<E> of(E e1, E e2) {
        return new ImmutableCollections.List12<>(e1, e2);
    }
```

`EMPTY_LIST` is a shared singleton (`ImmutableCollections.java` line 105,
`EMPTY_LIST = new ListN<>(new Object[0], false)`) so arity 0 allocates nothing. `List12` stores
elements in fields `e0`/`e1`: one object, zero arrays. Arity 3 is different (`List.java` 971):

```java
    static <E> List<E> of(E e1, E e2, E e3) {
        return ImmutableCollections.listFromTrustedArray(e1, e2, e3);
    }
```

`listFromTrustedArray` is itself declared `listFromTrustedArray(Object... input)`
(`ImmutableCollections.java` 212). **So an `Object[3]` is allocated anyway** — the compiler builds
it at *this* call site instead of the user's. The array does not vanish; it moves inside the
library and becomes a *trusted* array. That is the real saving: the 3–10 arms avoid the **second**
array, not the array.

| Call | Route | Arrays | Why |
|---|---|---|---|
| `List.of()` | `EMPTY_LIST` singleton | **0** | shared instance, no object at all |
| `List.of(a)` / `List.of(a,b)` | `new List12<>(..)` | **0** | elements live in fields |
| `List.of(a,b,c)` … `List.of(a..j)` | `listFromTrustedArray` | **1** | trusted array becomes the backing store; no defensive copy |
| `List.of(a..k)` (11+), or `List.of(array)` | `of(E...)` → `listFromArray` | **2** | caller's array is untrusted, so it is copied |

`listFromArray`, lines 187–195, shows the second allocation and says why:

```java
    static <E> List<E> listFromArray(E... input) {
        // copy and check manually to avoid TOCTOU
        E[] tmp = (E[])new Object[input.length]; // implicit nullcheck of input
        for (int i = 0; i < input.length; i++) {
            tmp[i] = Objects.requireNonNull(input[i]);
        }
        return new ListN<>(tmp, false);
    }
```

The comment is the argument. If the list retained the caller's array, a caller holding a
reference could null a slot *after* the check passed, and the "no nulls" invariant that
`contains`/`indexOf` rely on (see [03c](03c-null-queries-and-guava.md)) would be violated
retroactively. `listFromTrustedArray` skips the copy precisely because no caller holds a
reference to the array the compiler just built. Its switch (lines 218–224) collapses small
trusted arrays back down:

```java
        return switch (input.length) {
            case 0  -> (List<E>) ImmutableCollections.EMPTY_LIST;
            case 1  -> (List<E>) new List12<>(input[0]);
            case 2  -> (List<E>) new List12<>(input[0], input[1]);
            default -> (List<E>) new ListN<>(input, false);
        };
```

This is why `List.of(new String[]{"a"})` — which binds varargs, not `of(E)` — still yields a
`List12`. Measured arity → impl: `0 → ListN` (the `EMPTY_LIST` singleton), `1 → List12`,
`2 → List12`, `3 → ListN`, `4 → ListN`. The defensive copy, measured:

```
String[] arr = {"a","b","c","d"}; List<String> l = List.of(arr); arr[0] = "MUTATED";
array now            = [MUTATED, b, c, d]
List.of(array) still = [a, b, c, d]
Arrays.asList(array) = [MUTATED, b, c, d]     (shares the array)
```

### Two canonical empty lists

The arity-0 arm returns a shared singleton, and there is **more than one** of them:

```
List.of() == List.of()                : true
Set.of()  == Set.of()                 : true
Map.of()  == Map.of()                 : true
Stream.empty().toList() == again      : true
List.of() == Stream.empty().toList()  : false
```

`EMPTY_LIST` (line 105, built with `allowNulls == false`) and `EMPTY_LIST_NULLS` (returned by
`listFromTrustedArrayNullsAllowed`, lines 242–249, `allowNulls == true`) are separate instances.
They are `equals` to each other — both empty lists — but they disagree about `contains(null)`:

```
Stream.empty().toList().contains(null): false
List.of().contains(null)              : THROWS NullPointerException
```

The mechanism behind that disagreement is the `allowNulls` field, which is
[03c](03c-null-queries-and-guava.md)'s subject. The fact worth carrying here is narrower: the
arity-0 factories are singletons, but "the empty unmodifiable list" is not a single object.

### Null rejection, per argument position `[RESEARCH]`

Every position throws, and **the message is empty**:

```
List.of((String)null)          -> THROWS NullPointerException
List.of("a", null)             -> THROWS NullPointerException
List.of(null, "b")             -> THROWS NullPointerException
List.of(a,b,null) [3 args]     -> THROWS NullPointerException
List.of((String[])null)        -> THROWS NullPointerException
Set.of((String)null)           -> THROWS NullPointerException
Set.of("a", null)              -> THROWS NullPointerException
Map.of(null, 1)                -> THROWS NullPointerException
Map.of("a", null)              -> THROWS NullPointerException
Map.entry(null, 1)             -> THROWS NullPointerException
List.copyOf(Arrays.asList("a", null)) -> THROWS NullPointerException

List.of 3-arg NPE getMessage() = null
Map.of value NPE getMessage() = null
List.of 5-arg NPE getMessage() = null
```

Helpful NullPointerException messages (JEP 358, on by default since Java 15) only decorate NPEs
the JVM raises from a bytecode dereference; these come from an explicit
`Objects.requireNonNull(x)` with no message, so there is nothing to decorate. On a 20-argument
`Map.of` that is genuinely unpleasant — and a real argument for `Map.ofEntries`, where each
`Map.entry(k, v)` fails on its own source line.

> **Definition.** `List.of`/`Set.of` declare 12 overloads each (11 fixed-arity for 0–10 elements
> plus `of(E...)`) so small calls skip the caller-side varargs array; the allocation is genuinely
> eliminated only at arity 0–2, while arity 3–10 trades the caller's untrusted array for one
> trusted array that becomes the backing store and skips the defensive copy — and any null
> argument in any position throws a message-less `NullPointerException`.

---

## Pitfalls

### Assuming `Set.of` deduplicates like `HashSet`

**Wrong**

```java
static final Set<String> RETRYABLE = Set.of("timeout", "throttled", "timeout");
```

```
IllegalArgumentException: duplicate element: timeout
```

Worse: thrown from a static initialiser, so what you actually see at runtime is
`ExceptionInInitializerError` pointing at a class, not at the typo.

**Right**

```java
// If the duplicate was a typo, delete it — that is what the exception is telling you.
static final Set<String> RETRYABLE = Set.of("timeout", "throttled");

// If duplicates are legitimate runtime data, sanitise instead of validating:
static Set<String> retryable(List<String> fromConfig) {
    return Set.copyOf(fromConfig);   // deduplicates silently
}
```

`Set.copyOf(List.of("a","b","a","b","c"))` returns `[a, b, c]`, size 3 — measured above.

**Why people believe it:** for ten years the idiom was
`unmodifiableSet(new HashSet<>(asList(...)))`, and `HashSet` deduplicates without comment.

### Assuming `Map.of`'s 10-pair cap is a runtime limit

**Wrong**

```java
// "Map.of only holds 10, so I'll loop."
Map<String, Integer> m = new HashMap<>();
for (int i = 0; i < 12; i++) m.put("k" + i, i);
Map<String, Integer> ro = Collections.unmodifiableMap(m);   // a view over a live HashMap
```

The result is tier 2, an unmodifiable *view* — the `HashMap` is still reachable, so it is not
immutable at all.

**Right**

```java
Map<String, Integer> ro = Map.ofEntries(
        Map.entry("k0", 0), Map.entry("k1", 1), Map.entry("k2", 2),
        Map.entry("k3", 3), Map.entry("k4", 4), Map.entry("k5", 5),
        Map.entry("k6", 6), Map.entry("k7", 7), Map.entry("k8", 8),
        Map.entry("k9", 9), Map.entry("k10", 10), Map.entry("k11", 11));
// measured: size 12, impl MapN — no runtime ceiling exists
```

**Why people believe it:** "caps at 10" sounds like a capacity constraint. It is the number of
declared overloads, and the failure is a compile error with no runtime component.

### Expecting the factory's NPE to name the bad argument

**Wrong**

```java
// A 12-argument Map.of in a static initialiser. One value is null.
static final Map<String, String> HEADERS = Map.of(
        "accept", "application/json", "accept-encoding", "gzip",
        "user-agent", agent(), "x-trace", traceHeader(),   // returns null in some builds
        "x-tenant", tenant(), "x-region", region());
// NullPointerException, and e.getMessage() is null. Nothing names x-trace.
```

**Right**

```java
static final Map<String, String> HEADERS = Map.ofEntries(
        Map.entry("accept", "application/json"),
        Map.entry("accept-encoding", "gzip"),
        Map.entry("user-agent", agent()),
        Map.entry("x-trace", traceHeader()),   // this line appears in the stack trace
        Map.entry("x-tenant", tenant()),
        Map.entry("x-region", region()));
```

Each `Map.entry(k, v)` is its own call on its own source line, so the stack trace localises the
failure even though the message is still `null`.

**Why people believe it:** JEP 358 helpful NPEs have been on by default since Java 15 and are
usually excellent — but they decorate only NPEs the JVM raises from a bytecode dereference, not
an explicit `Objects.requireNonNull(x)` called with no message argument.

---

## Cheat sheet

| Question | Answer |
|---|---|
| `Set.of("a","a")` | `IllegalArgumentException: duplicate element: a` |
| `Map.of("a",1,"a",2)` / `Map.ofEntries` same | `IllegalArgumentException: duplicate key: a` |
| `List.of("a","a")` | `[a, a]` — lists allow duplicates |
| `Set.copyOf(List.of("a","a"))` | `[a]` — `copyOf` deduplicates |
| `of` vs `copyOf` | `of` validates a literal; `copyOf` sanitises a value |
| `Map.of` maximum pairs | 10 pairs = 20 args; 11 pairs is a **compile error** |
| `Map.of` overloads | 11 fixed-arity (0,2,4…20 args) + `ofEntries(Entry...)` = 12 |
| `List.of`/`Set.of` overloads | 11 fixed-arity (0–10) + `of(E...)` = 12 |
| Arity → impl for `List.of` | 0 → `EMPTY_LIST` singleton; 1–2 → `List12`; 3+ → `ListN` |
| Arrays allocated | 0 for arity 0–2; 1 (trusted) for 3–10; 2 for varargs/array input |
| What arity 3–10 actually saves | the **second** array (the defensive copy), not the array |
| Why the untrusted path copies | TOCTOU — caller could null a slot after the check |
| `List.of(null)`, any position | `NullPointerException`, `getMessage() == null` |
| Which argument was null? | the NPE will not tell you; use `Map.ofEntries` for line-level blame |
| `List.of() == List.of()` | `true` — shared `EMPTY_LIST` singleton |
| `List.of() == Stream.empty().toList()` | `false` — `EMPTY_LIST` vs `EMPTY_LIST_NULLS` |
| `Set.of`/`Map.of` iteration order | salted **per JVM run**; stable within a run |
| `EXPAND_FACTOR` | `2` — probe table is twice the element count |
| `probe(e)` return convention | `>= 0` means already present (duplicate); `-(idx+1)` is the free slot |

---

## Self-test

**Q1.** `Set.of("a","b","a")` versus `Set.copyOf(List.of("a","b","a"))` — what does each return?

<details><summary>Answer</summary>

`Set.of("a","b","a")` throws `IllegalArgumentException: duplicate element: a` from `SetN`'s
constructor (`ImmutableCollections.java` line 925): `probe(e)` returns a non-negative index for an
element already in the table, which is the duplicate signal.

`Set.copyOf(List.of("a","b","a"))` returns `[a, b]`, size 2 — `copyOf` funnels through
`new HashSet<>(coll)` first, which deduplicates silently. The rule: `of` validates a literal you
typed, `copyOf` sanitises a value you received.

</details>

**Q2.** Why does `Map.of` stop at 10 pairs, and what kind of error do you get at 11?

<details><summary>Answer</summary>

No runtime cap exists. `Map.java` declares 11 fixed-arity `of` overloads taking `2n` arguments for
`n = 0..10` — argument counts 0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20. An eleventh pair means 22
arguments and no such overload exists, so it is a **compile error** ("no suitable method found"),
never an exception. The escape hatch is `Map.ofEntries(Entry...)` (line 1663), varargs and
unbounded — measured at 12 pairs it returns a `MapN` of size 12.

</details>

**Q3.** The syllabus says the fixed-arity `List.of` overloads exist "to avoid array allocation".
Where is that true, and where is it not?

<details><summary>Answer</summary>

True for arity 0, 1 and 2 only. `of()` returns the shared `EMPTY_LIST` singleton (zero
allocation); `of(E)` and `of(E,E)` construct a `List12` holding elements in fields (one object,
no array).

From arity 3 up, `List.of` delegates to `listFromTrustedArray(Object... input)` (line 212), which
is *itself* varargs — so an `Object[3]` is allocated at that call site. The array does not
disappear; it moves inside the library, where it is *trusted* (no caller holds a reference) and
can be reused as `ListN`'s backing store without a defensive copy.

Accounting: 0 arrays for arity 0–2, 1 for arity 3–10, 2 on the `of(E...)` path where
`listFromArray` (line 187) must copy the untrusted array before checking it — "copy and check
manually to avoid TOCTOU". So the 3–10 arms avoid the *second* array, not the array.

</details>

**Q4.** What TOCTOU risk does `listFromArray` guard against, and why does it matter?

<details><summary>Answer</summary>

If `ListN` retained the caller's array, a caller holding a reference could null a slot *after* the
null check passed. The list would then hold a null while advertising `allowNulls == false`.

That matters because `indexOf`/`contains` treat `allowNulls == false` as a *guarantee*: they throw
on a null probe on the grounds that the question cannot have a true answer (see
[03c](03c-null-queries-and-guava.md)). A retroactively nulled slot would falsify that reasoning —
`contains(null)` would throw NPE on a list that actually contained a null. So `listFromArray`
copies into a fresh `Object[]` and `requireNonNull`s the copy, closing the window.

`listFromTrustedArray` needs no copy because the array it receives was built by the compiler at a
call site inside `List.of`; no caller can reach it.

</details>

**Q5.** A 20-argument `Map.of` in a static initialiser throws NPE. How do you find the bad
argument?

<details><summary>Answer</summary>

Not from the message — `e.getMessage()` is literally `null`. Measured on JDK 21.0.7:
`List.of("a",null,"c")`, `Map.of("a",null)` and `List.of("a","b","c","d",null)` all produce an
NPE whose `getMessage()` is `null`.

JEP 358 helpful NPE messages (default since Java 15) only decorate NPEs the JVM raises from a
bytecode dereference. These come from an explicit `Objects.requireNonNull(x)` with no message
argument, so there is nothing to decorate.

The practical fix is to rewrite as `Map.ofEntries(Map.entry(k, v), ...)`. Each `Map.entry` call
sits on its own source line, so the stack trace localises the failure even though the message
stays `null`.

</details>

**Q6.** A test asserts on `Set.of("a","b","c").toString()`. It passes locally and fails in CI. Why?

<details><summary>Answer</summary>

`SetN`/`MapN` place elements at `probe`-determined slots in an open-addressed table, and the probe
sequence is perturbed by a salt seeded once per JVM. So iteration order is **randomised per JVM
run and stable within a run** — exactly the shape that passes repeatedly on one machine and fails
on a fresh JVM. Two runs of the same program in this file gave `[a, f, e, d, c, b]` and
`[a, b, c, d, e, f]`; three prints inside one JVM were identical.

The randomisation is deliberate: it exists so nobody can depend on the order. Fix the test by
asserting set equality rather than string form.

</details>

---

**Leaves covered:** 2.4.7–2.4.10 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 602
