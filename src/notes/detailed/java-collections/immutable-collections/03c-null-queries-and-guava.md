# 02 Java Collections — Immutability and views — INTERMEDIATE (§2.4.11–2.4.13)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [immutable-collections/03b-immutability-tiers-b-factory-rules.md](03b-immutability-tiers-b-factory-rules.md) · Next: [immutable-collections/04-internals-immutable-collections.md](04-internals-immutable-collections.md)

[03b](03b-immutability-tiers-b-factory-rules.md) covered the rejections that happen at
**construction** time — duplicates, nulls, the arity cap. This file covers the one that happens at
**query** time, the least intuitive and the one most likely to reach production: `contains(null)`
on an unmodifiable collection sometimes throws `NullPointerException` and sometimes answers
`false`. It then compares the JDK factories against Guava's `Immutable*`, whose ordering guarantee
is the mirror image of `Set.of`'s.

**No diagram belongs to this row.** The structure a diagram would carry — which implementation
answers a null probe how — is the matrix in §1, filled by running every cell. All transcripts:
**Oracle JDK 21.0.7, macOS aarch64**. Source citations are `/tmp/jc49src/java.base/java/util/`.

---

## 1. The null-query matrix: why `contains(null)` sometimes throws (2.4.11, 2.4.12)

**Mental model.** Two lists that both refuse mutation are not the same *kind* of list. `ListN`
carries one boolean, `allowNulls`, and it changes the meaning of a null probe. `false` — the list
is *guaranteed* null-free, so `contains(null)` cannot be a real question; it is a caller bug;
throw. `true` — the list may hold nulls, so the query is legitimate; answer it. Same class, same
interface, opposite behaviour, decided by one field.

**Why it exists.** `Stream.toList()` (Java 16) had to be null-tolerant — streams may contain nulls,
and `toList()` returns an unmodifiable list of whatever the stream had. Reusing `ListN` was cheaper
than adding a class, so `ListN` grew the flag. `allowNulls` is the seam between the Java 9
null-hostile factories and the Java 16 null-tolerant terminal operation.

**When it matters.** Any time a null probe reaches a collection you did not construct yourself — a
method parameter, a field from configuration, a library result. Defensive `contains(null)` checks
are the classic trigger. It does not matter if you built the collection with `List.of` in the same
method: you already know it holds no nulls, so the question never needs asking.

### The measured matrix `[RESEARCH]`

Every cell filled by running it, not by reasoning. This is the deliverable of the row.

| Source | Runtime class | `contains(null)` | `indexOf(null)` | `lastIndexOf(null)` |
|---|---|---|---|---|
| `List.of()` | `ListN` (`allowNulls=false`) | **NPE** | **NPE** | **NPE** |
| `List.of("a")` / `List.of("a","b")` | `List12` | **NPE** | **NPE** | **NPE** |
| `List.of(a..e)` | `ListN` (`allowNulls=false`) | **NPE** | **NPE** | **NPE** |
| `List.of(a..e).subList(0,3)` | `SubList` | **NPE** | **NPE** | **NPE** |
| `List.of(a,b,c).reversed()` (Java 21) | `ReverseOrderListView$Rand` | **NPE** | **NPE** | **NPE** |
| `List.copyOf(List.of(a,b,c))` | `ListN` (`allowNulls=false`) | **NPE** | **NPE** | **NPE** |
| `List.copyOf(stream.toList())` | `ListN` (`allowNulls=false`) | **NPE** | **NPE** | **NPE** |
| `Stream.of(a,b,c).toList()` (Java 16) | `ListN` (`allowNulls=true`) | `false` | `-1` | `-1` |
| `Stream.of(a,null).toList()` | `ListN` (`allowNulls=true`) | `true` | `1` | `1` |
| `Collections.unmodifiableList(arrayList)` | `UnmodifiableRandomAccessList` | `false` | `-1` | `-1` |
| `Arrays.asList(a,b)` | `Arrays$ArrayList` | `false` | `-1` | `-1` |
| `new ArrayList<>(List.of(a,b))` | `ArrayList` | `false` | `-1` | `-1` |
| `Collections.emptyList()` | `Collections$EmptyList` | `false` | `-1` | `-1` |
| `Collections.singletonList(a)` | `Collections$SingletonList` | `false` | `-1` | `-1` |

Sets and maps, same run:

| Source | Runtime class | Probe | Result |
|---|---|---|---|
| `Set.of()` / `Set.of(a..e)` | `SetN` | `contains(null)` | **NPE** |
| `Set.of(a)` / `Set.of(a,b)` | `Set12` | `contains(null)` | **NPE** |
| `Set.copyOf(hashSet)` | `Set12` | `contains(null)` | **NPE** |
| `Collections.unmodifiableSet(hashSet)` | `UnmodifiableSet` | `contains(null)` | `false` |
| `Map.of()` / `Map.of(3 pairs)` | `MapN` | `containsKey`/`get`/`containsValue` | **NPE** (all three) |
| `Map.of(a,1)` | `Map1` | `containsKey`/`get`/`containsValue` | **NPE** (all three) |
| `Collections.unmodifiableMap(hashMap)` | `UnmodifiableMap` | `containsKey(null)` / `get(null)` | `false` / `null` |
| `Map.copyOf(hashMap containing a null key)` | — | at construction | **NPE** |

**Correction to the syllabus — 2.4.11 is wrong as stated.** It says "throws NPE on some
implementations and returns false on others", which reads as if some `List.of` results are
lenient. **None are.** Every product of `List.of`, `List.copyOf`, `Set.of`, `Set.copyOf`, `Map.of`
and `Map.copyOf` throws, at **every** arity, including the empty ones, the `subList` views and the
Java 21 `reversed()` views. The lenient rows are exactly two families: **`Stream.toList()`**, a
`ListN` with `allowNulls == true` (Java 16 — this is the version fact that changes the answer);
and **the pre-Java-9 wrappers** — `Collections.unmodifiableList/Set/Map`, `Arrays.asList`,
`emptyList`, `singletonList` — which delegate to a null-tolerant backing collection. Nothing in
between. The syllabus does not say *why*, and the why is the whole content.

### The guards, quoted

`ImmutableCollections.java` 719–731, `ListN`:

```java
        @Override
        public int indexOf(Object o) {
            if (!allowNulls && o == null) {
                throw new NullPointerException();
            }
            Object[] es = elements;
            for (int i = 0; i < es.length; i++) {
                if (Objects.equals(o, es[i])) {
                    return i;
                }
            }
            return -1;
        }
```

`!allowNulls && o == null` is the entire mechanism: the probe is rejected only when the list
promised to be null-free. The loop then uses null-safe `Objects.equals`, because when `allowNulls`
is true a null `o` must still be comparable. `lastIndexOf` (734–748) is the same guard with a
descending loop. The field itself, lines 665–673:

```java
        @Stable
        private final boolean allowNulls;

        // caller must ensure that elements has no nulls if allowNulls is false
        private ListN(E[] elements, boolean allowNulls) {
            this.elements = elements;
            this.allowNulls = allowNulls;
        }
```

`@Stable` lets the JIT treat it as a constant after initialisation, so the guard folds away — the
flag costs nothing at steady state. The comment is the contract that `listFromArray`'s defensive
copy exists to uphold (see [03b](03b-immutability-tiers-b-factory-rules.md)).

**`contains` is not overridden in `ListN` at all.** `AbstractImmutableList` lines 329–332:

```java
        @Override
        public boolean contains(Object o) {
            return indexOf(o) >= 0;
        }
```

**That single line collapses 2.4.11 and 2.4.12 into one fact.** `contains(null)` throws for
exactly the reason `indexOf(null)` throws — there is no separate null policy for `contains`.
Anyone who expects the two to differ is looking for a second mechanism that does not exist.

`List12` has no flag because it structurally cannot hold nulls (its constructor `requireNonNull`s
both fields), so it hard-codes the rejection — lines 595–605:

```java
        @Override
        public int indexOf(Object o) {
            Objects.requireNonNull(o);
            if (o.equals(e0)) {
                return 0;
            } else if (e1 != EMPTY && o.equals(e1)) {
                return 1;
            } else {
                return -1;
            }
        }
```

`SubList` reaches through to the root for the flag — lines 497–511:

```java
        private boolean allowNulls() {
            return root instanceof ListN && ((ListN<?>)root).allowNulls;
        }

        @Override
        public int indexOf(Object o) {
            if (!allowNulls() && o == null) {
                throw new NullPointerException();
            }
            for (int i = 0, s = size(); i < s; i++) {
                if (Objects.equals(o, get(i))) {
                    return i;
                }
            }
            return -1;
        }
```

Because the test is `root instanceof ListN && root.allowNulls`, a `SubList` whose root is a
`List12` gets `false` and therefore throws — which the matrix confirms. A `SubList` over a
`Stream.toList()` result would inherit `true`.

**Insight:** sets and maps need no flag at all, because **no** immutable set or map implementation
permits nulls — there is nothing for a flag to select between. Four spellings of one policy:

| Class | Line | How it rejects null |
|---|---|---|
| `SetN.contains` | 943 | explicit `Objects.requireNonNull(o)` |
| `Set12.contains` | 816 | `return o.equals(e0) || e1.equals(o);` — implicit dereference |
| `MapN.containsKey` | 1206 | explicit `Objects.requireNonNull(o)` |
| `Map1.get` | 1123 | `return o.equals(k0) ? v0 : null;` — implicit dereference |

This is also why `Set.copyOf`/`Map.copyOf` use a simpler fast-path test than `List.copyOf` — plain
`instanceof AbstractImmutableSet`/`AbstractImmutableMap`, no `allowNulls` clause, because there is
no null-tolerant variant to exclude.

### Runnable harness — fill the matrix yourself

Every probe sits inside its own try/catch, so the program runs to completion.

```java
import java.util.*;
import java.util.stream.Stream;

public class NullMatrix {
    static String attempt(java.util.function.Supplier<Object> p) {
        try { return String.valueOf(p.get()); }
        catch (Throwable t) { return "THROWS " + t.getClass().getSimpleName(); }
    }

    static void row(String label, List<String> l) {
        System.out.printf("%-30s impl=%-42s contains=%-26s indexOf=%-26s lastIndexOf=%s%n",
                label, l.getClass().getName(),
                attempt(() -> l.contains(null)),
                attempt(() -> l.indexOf(null)),
                attempt(() -> l.lastIndexOf(null)));
    }

    public static void main(String[] args) {
        System.out.println("java.version=" + System.getProperty("java.version")
                + " os=" + System.getProperty("os.name") + "/" + System.getProperty("os.arch"));
        row("List.of(a..e)", List.of("a", "b", "c", "d", "e"));
        row("List.of(a..e).subList(0,3)", List.of("a", "b", "c", "d", "e").subList(0, 3));
        row("List.of(a,b,c).reversed()", List.of("a", "b", "c").reversed());
        row("Stream.of(a,b,c).toList()", Stream.of("a", "b", "c").toList());
        row("Stream.of(a,null).toList()", Stream.of("a", (String) null).toList());
        row("List.copyOf(stream.toList())", List.copyOf(Stream.of("a", "b", "c").toList()));
        row("Collections.unmodifiableList", Collections.unmodifiableList(new ArrayList<>(List.of("a", "b"))));
        // Add rows for List.of(), List.of(a), Arrays.asList, emptyList and singletonList
        // to reproduce the remaining rows of the table above.
        Map<String, Integer> m = Map.of("a", 1, "b", 2, "c", 3);
        System.out.println("Set.of.contains(null)    -> " + attempt(() -> Set.of("a", "b").contains(null)));
        System.out.println("Map.of.containsKey(null) -> " + attempt(() -> m.containsKey(null)));
        System.out.println("Map.of.get(null)         -> " + attempt(() -> m.get(null)));
        System.out.println("Map.of.containsValue()   -> " + attempt(() -> m.containsValue(null)));
    }
}
```

Real output, abridged to the impl and `contains` columns — the full three-column run over all
fourteen sources is what the matrix above was built from:

```
java.version=21.0.7 os=Mac OS X/aarch64
List.of(a..e)                  impl=java.util.ImmutableCollections$ListN    contains=THROWS NullPointerException
List.of(a..e).subList(0,3)     impl=java.util.ImmutableCollections$SubList  contains=THROWS NullPointerException
List.of(a,b,c).reversed()      impl=java.util.ReverseOrderListView$Rand     contains=THROWS NullPointerException
Stream.of(a,b,c).toList()      impl=java.util.ImmutableCollections$ListN    contains=false
Stream.of(a,null).toList()     impl=java.util.ImmutableCollections$ListN    contains=true
List.copyOf(stream.toList())   impl=java.util.ImmutableCollections$ListN    contains=THROWS NullPointerException
Collections.unmodifiableList   impl=java.util.Collections$UnmodifiableRandomAccessList contains=false
Set.of.contains(null)    -> THROWS NullPointerException
Map.of.containsKey(null) -> THROWS NullPointerException
Map.of.get(null)         -> THROWS NullPointerException
Map.of.containsValue()   -> THROWS NullPointerException
```

Note rows 4 and 5 against row 6: `Stream.toList()` answers `false`, but wrapping the same value in
`List.copyOf` makes it throw. That is the next subsection.

### The gotcha — `List.copyOf` hardens

The most surprising cell in the matrix: `List.copyOf(stream.toList())`. The input answers
`contains(null)` with `false`; the output throws. `ImmutableCollections.java` 167–176:

```java
    static <E> List<E> listCopy(Collection<? extends E> coll) {
        if (coll instanceof List12 || (coll instanceof ListN<?> c && !c.allowNulls)) {
            return (List<E>)coll;
        } else if (coll.isEmpty()) { // implicit nullcheck of coll
            return List.of();
        } else {
            return (List<E>)List.of(coll.toArray());
        }
    }
```

The fast path requires `!c.allowNulls`, so a null-tolerant `ListN` fails the test, falls through
to `List.of(coll.toArray())`, and comes back as a fresh `allowNulls == false` `ListN`. Measured:

```
List.copyOf(List.of)         same instance? true
List.copyOf(stream.toList()) same instance? false
```

**Pitfall:** *Wrong belief* — "`List.copyOf` on an already-unmodifiable list is free, so I can
sprinkle it defensively at API boundaries." *Symptom* — a `Stream.toList()` result is copied on
every call in a hot path; separately, code that previously did `list.contains(null)` starts
throwing NPE after someone inserted a `List.copyOf` upstream. *Fix* — `copyOf` is free only for
`List12` and null-*hostile* `ListN`. If your value came from `Stream.toList()` and you want the
null-hostile guarantee, that copy is the price and the NPE is the point; if you did not want it,
stop calling `copyOf`.

The same seam explains a smaller oddity carried in [03b](03b-immutability-tiers-b-factory-rules.md):
`List.of()` and `Stream.empty().toList()` are two different singletons (`EMPTY_LIST`,
`allowNulls == false`; `EMPTY_LIST_NULLS`, `allowNulls == true`) that are `equals` yet disagree
about `contains(null)`.

**Interview:** "Does `List.of("a").contains(null)` throw?" — Yes, `NullPointerException`:
`AbstractImmutableList.contains` delegates to `indexOf`, and `List12.indexOf` starts with
`Objects.requireNonNull`. Follow-up: "and `Stream.of("a").toList().contains(null)`?" — `false`,
because that `ListN` was built with `allowNulls == true` (Java 16+).

> **Definition.** Null-probe behaviour on an unmodifiable `List` is decided by `ListN`'s
> `allowNulls` field, consulted by `indexOf`/`lastIndexOf` and hence by `contains`, which merely
> delegates to `indexOf`: every `List.of`/`copyOf`/`Set.of`/`Map.of` product has
> `allowNulls == false` and throws `NullPointerException`, `Stream.toList()` has
> `allowNulls == true` and answers `false`/`-1`, and the legacy `Collections.unmodifiable*`
> wrappers inherit their backing collection's tolerance.

---

## 2. Guava `ImmutableList`/`ImmutableMap` versus the JDK factories (2.4.13)

**Mental model.** Guava's `Immutable*` are what `List.of`/`Map.of` would have been if designed for
**construction across many statements** rather than one literal call. The JDK factory is a one-shot
expression; Guava's is a builder you can carry around, hand to a loop, and close at the end.
Everything else follows from that difference in shape.

Coordinates checked against Maven Central, August 2026: **`com.google.guava:guava:33.7.1-jre`**
(the `-android` flavour targets Android / Java 8 desugaring). Guava is not on this file's classpath
and no dependency was added, so **there is no Guava transcript here**; everything below is from the
published Javadoc, and anything I could not confirm is marked `**Unverified:**`.

**Why it exists.** `ImmutableList`/`ImmutableMap` predate Java 9 by roughly a decade. Before
`List.of`, the alternatives were `Collections.unmodifiableList(new ArrayList<>(..))` — a *view*,
so the backing list could still change — or hand-rolled copies. Guava gave the ecosystem genuine
immutable-by-construction collections, and the Java 9 factories are explicitly the JDK's answer.

### The comparison

| Axis | `List.of` / `Map.of` (JDK 9+) | Guava `ImmutableList` / `ImmutableMap` |
|---|---|---|
| **Builder** | none; one expression, or `collect(toUnmodifiableList())` | `ImmutableList.builder()`, `ImmutableMap.builder()`, incremental `add`/`put`/`addAll`, terminal `build()` |
| **Arity limit** | `Map.of` capped at 10 pairs by overload count | none — builder for anything larger |
| **Iteration order** | `List` insertion order; **`Set.of`/`Map.of` salted per JVM run** | documented insertion / encounter order for `ImmutableSet` and `ImmutableMap` too |
| **Duplicate keys** | `IllegalArgumentException`, always | `build()`/`buildOrThrow()` (since 31.0) throw; **`buildKeepingLast()`** (since 31.1) keeps the last value |
| **Value-ordered maps** | none | `orderEntriesByValue(Comparator)` (since 19.0), stable on ties |
| **Nulls at construction** | rejected everywhere | rejected; `copyOf` throws NPE "if any of elements is null" |
| **Nulls at query** | `contains(null)` **throws** (§1) | **Unverified:** documented to return `false` rather than throw, but I could not confirm 33.x behaviour from source in this session |
| **`asList` views** | `Map.keySet()` is a plain `Set`; no `asList` | `ImmutableCollection.asList()` returns "an `ImmutableList` containing the same elements, in the same order"; `keySet()` is an `ImmutableSet`, `values()` an `ImmutableCollection`, `entrySet()` an `ImmutableSet` |
| **Cost** | zero dependencies | ~3 MB jar; a notorious version-conflict source in large dependency trees |

The **ordering** row is the one worth internalising, and it is the axis where the two libraries
make opposite promises. From [03b](03b-immutability-tiers-b-factory-rules.md): `Set.of`/`Map.of`
place elements at `probe`-determined slots in an open-addressed table, and the probe sequence is
perturbed by a salt seeded once per JVM. Two runs of the same program:

```
run 1:  Set.of order: [a, f, e, d, c, b]
run 2:  Set.of order: [a, b, c, d, e, f]
```

Stable within a run, different across runs — deliberately, so nobody can depend on it. Guava
promises the reverse: entries "appear in the result `ImmutableMap` in encounter order", and "the
iteration order is specified by the method used to create this map. Typically, this is insertion
order." If a test asserts on a set's serialised order, or the output is a config file a human
diffs, that guarantee is the reason to reach for Guava.

The **`asList` views** row is the third named axis and the subtlest. `ImmutableMap.keySet()`
returns an `ImmutableSet` rather than a `Set`, `values()` an `ImmutableCollection`, and
`ImmutableCollection.asList()` an `ImmutableList` "containing the same elements, in the same
order". The immutable type therefore survives every projection — you can hand a `keySet()` to a
method requiring an `ImmutableSet` without a copy. The JDK's `Map.of(..).keySet()` is declared as
a plain `Set`, so the guarantee is real at runtime but invisible in the type, and there is no
`asList()` at all.

### The builder, concretely

```java
// Guava — illustrative; not executed here (no Guava on the classpath).
static ImmutableList<String> enabledFeatures(Config cfg) {
    ImmutableList.Builder<String> b = ImmutableList.builder();
    b.add("core");
    if (cfg.async()) { b.add("async"); }
    for (String plugin : cfg.plugins()) { b.add(plugin); }
    return b.build();                      // insertion order guaranteed
}

static ImmutableMap<String, Integer> limits(Map<String, Integer> defaults,
                                            Map<String, Integer> overrides) {
    return ImmutableMap.<String, Integer>builder()
            .putAll(defaults)
            .putAll(overrides)             // may repeat keys from defaults
            .buildKeepingLast();           // Guava 31.1+: last wins instead of throwing
}
```

`buildKeepingLast()` has no JDK equivalent whatsoever. `build()` is documented as equivalent to
`buildOrThrow()` (31.0), which is the name to prefer when you *do* want the exception.

### When Guava is not worth the dependency

Honestly: **most of the time, now.** The pre-Java-9 reasons are gone — `List.of`, `Set.of`,
`Map.of`, `Map.ofEntries`, the `copyOf` family and `Collectors.toUnmodifiable*` cover the ordinary
cases with no dependency, no version conflict, and better-optimised implementations (`@Stable`
fields, `@jdk.internal.ValueBased` classes, CDS-archived empty singletons). Add Guava only for a
nameable need: (1) documented iteration order on a set or map you assert on or serialise;
(2) `buildKeepingLast()` or `orderEntriesByValue()` — last-wins or value-ordered maps without a
`Collectors.toMap` detour; (3) multi-statement or conditional construction where a builder beats a
stream collect; (4) you already depend on Guava for `Multimap`, `Table`, `RangeSet` or `Cache`.
"We've always used Guava" is not on that list.

> **Definition.** Guava's `Immutable*` (33.7.1-jre as of August 2026) differ from the JDK 9
> factories on three axes: incremental **builders** with `buildOrThrow`/`buildKeepingLast`
> duplicate policies, a **documented iteration order** where `Set.of`/`Map.of` deliberately
> randomise it per JVM run, and `asList()`/`ImmutableSet` **views** that preserve the immutable
> type through `keySet`/`values`/`entrySet` — at the cost of a dependency the JDK factories now
> make unnecessary for most code.

---

## Pitfalls

### Assuming an unmodifiable list answers `contains(null)`

**Wrong**

```java
static boolean hasMissing(List<String> names) { return names.contains(null); }

public static void main(String[] args) {
    try { System.out.println(hasMissing(List.of("a", "b"))); }
    catch (NullPointerException e) { System.out.println("caught NPE — the lesson"); }
}
// prints: caught NPE — the lesson
```

**Right**

```java
static boolean hasMissing(List<String> names) {
    for (String n : names) {          // iteration never probes with null
        if (n == null) return true;
    }
    return false;
}
// Or, if the argument comes from List.of/copyOf, the answer is always false by
// construction and the check can be deleted outright.
```

**Why people believe it:** `Collection.contains` is *specified* to permit NPE ("if the specified
element is null and this collection does not permit null elements"), but `ArrayList`, `HashSet` and
every `Collections.unmodifiable*` wrapper answer `false` — so a decade of experience says the
optional clause never fires. Java 9 is the first time it fires routinely.

### Assuming `List.copyOf` is free on an already-unmodifiable list

**Wrong**

```java
public static void main(String[] args) {
    List<String> fromStream = Stream.of("a", "b", "c").toList();
    System.out.println("source contains(null) = " + fromStream.contains(null));
    List<String> copied = List.copyOf(fromStream);   // "free", supposedly
    System.out.println("same instance?        = " + (copied == fromStream));
    try {
        System.out.println("copy contains(null)   = " + copied.contains(null));
    } catch (NullPointerException e) {
        System.out.println("copy contains(null)   = threw " + e.getClass().getSimpleName());
    }
}
```

Output:

```
source contains(null) = false
same instance?        = false
copy contains(null)   = threw NullPointerException
```

**Right**

```java
// listCopy returns the argument unchanged only for List12 and for ListN with
// allowNulls == false. Keep the copy at a boundary if you want the guarantee —
// but expect a real copy, and the NPE, for anything from Stream.toList().
public Report(List<String> lines) { this.lines = List.copyOf(lines); }
```

**Why people believe it:** the `List.copyOf` Javadoc `@implNote` says "If the given Collection is
an unmodifiable List, calling copyOf will generally not create a copy." `Stream.toList()` returns
an unmodifiable list — but "generally" is doing real work there, and the guard
`coll instanceof ListN<?> c && !c.allowNulls` is where it fails.

### Asserting on the iteration order of a `Set.of`

**Wrong**

```java
assertEquals("[accept, accept-encoding, user-agent]",
             Set.of("accept", "accept-encoding", "user-agent").toString());
```

Passes on the developer's machine every time; fails in CI on a different JVM start.

**Right**

```java
assertEquals(Set.of("accept", "accept-encoding", "user-agent"),
             subject.headerNames());          // set equality, order-independent
// If a documented order is genuinely required, use a LinkedHashSet or Guava's ImmutableSet.
```

**Why people believe it:** within one JVM the order *is* stable, so the assertion looks
deterministic under any amount of local re-running; the salt is seeded once per JVM, so only a
fresh process reveals it.

---

## Cheat sheet

| Question | Answer |
|---|---|
| `List.of(..).contains/indexOf/lastIndexOf(null)` | **NPE** — every arity, incl. empty |
| `List.of(..).subList(..).contains(null)` | **NPE** — `SubList.allowNulls()` reads the root |
| `List.of(..).reversed().contains(null)` | **NPE** (Java 21 view) |
| `Stream.of("a").toList().contains(null)` | `false` (`ListN.allowNulls == true`, Java 16+) |
| `Stream.of("a",null).toList().indexOf(null)` | `1` |
| `List.copyOf(stream.toList()).contains(null)` | **NPE** — the copy hardens |
| `Collections.unmodifiableList/Set(x)`, `Arrays.asList`, `emptyList`, `singletonList` | `false` — inherit the backing collection |
| `Set.of(..).contains(null)` | **NPE**, always, all arities |
| `Map.of(..).get/containsKey/containsValue(null)` | **NPE**, all three, all arities |
| `Collections.unmodifiableMap(x).get(null)` | `null` |
| The one field that decides it all | `ImmutableCollections.ListN.allowNulls` (line 667, `@Stable`) |
| The guard, verbatim | `if (!allowNulls && o == null) throw new NullPointerException();` |
| Why `contains` needs no guard of its own | `AbstractImmutableList.contains(o)` is `indexOf(o) >= 0` (line 330) |
| Why `Set`/`Map` need no flag | no immutable `Set`/`Map` impl permits nulls at all |
| `List.copyOf` fast-path test | `coll instanceof List12 \|\| (coll instanceof ListN<?> c && !c.allowNulls)` |
| `Set`/`Map.copyOf` fast-path test | plain `instanceof AbstractImmutableSet`/`AbstractImmutableMap` |
| `Set.of`/`Map.of` iteration order | salted **per JVM run**; stable within a run |
| Guava coordinates (Aug 2026) | `com.google.guava:guava:33.7.1-jre` |
| Guava-only capabilities | builders, `buildKeepingLast()` (31.1), `buildOrThrow()` (31.0), `orderEntriesByValue()` (19.0), documented set/map order, `asList()` views |

---

## Self-test

**Q1.** `List.of("a").contains(null)` throws NPE but `Stream.of("a").toList().contains(null)`
returns `false`. Both are unmodifiable lists. Explain.

<details><summary>Answer</summary>

`ListN` has a `@Stable final boolean allowNulls` (line 667). `List.of` builds it via
`listFromTrustedArray`/`listFromArray`, both passing `false`; `Stream.toList()` (Java 16) builds it
via `listFromTrustedArrayNullsAllowed`, passing `true`. `ListN.indexOf` opens with
`if (!allowNulls && o == null) throw new NullPointerException();` (line 722), and
`AbstractImmutableList.contains(o)` is just `return indexOf(o) >= 0;` (line 330).

`List.of("a")` is actually a `List12`, not a `ListN` — no flag, because its constructor
`requireNonNull`s both fields so it structurally cannot hold a null. It hard-codes
`Objects.requireNonNull(o)` at the top of `indexOf` (line 596). Same outcome, different route.

</details>

**Q2.** Is `List.copyOf(x)` free when `x` is already unmodifiable?

<details><summary>Answer</summary>

Only sometimes. `listCopy` (line 169) returns the argument unchanged when
`coll instanceof List12 || (coll instanceof ListN<?> c && !c.allowNulls)`. A `Stream.toList()`
result is a `ListN` with `allowNulls == true`, so it **fails** the guard and gets copied.
Measured: `List.copyOf(List.of("a","b","c")) == source` is `true`;
`List.copyOf(Stream.of("a","b","c").toList()) == source` is `false`.

The copy is not just an allocation — it changes behaviour. The copy has `allowNulls == false`, so
`contains(null)` throws on the copy while returning `false` on the original.

</details>

**Q3.** Why does `Set.copyOf` need a simpler fast-path test than `List.copyOf`?

<details><summary>Answer</summary>

Because there is no null-tolerant immutable `Set` to exclude. `List.copyOf` must write
`coll instanceof ListN<?> c && !c.allowNulls` because `ListN` covers both the null-hostile
`List.of` products and the null-tolerant `Stream.toList()` products. `Set.copyOf`/`Map.copyOf` use
a plain `instanceof AbstractImmutableSet`/`AbstractImmutableMap`, because **every** immutable set
and map implementation rejects nulls: `SetN.contains` and `MapN.containsKey` call
`Objects.requireNonNull(o)`, `Set12.contains` and `Map1.get` dereference the argument. Related
asymmetry: `Set.copyOf` also **deduplicates** via `new HashSet<>(coll)`, so it accepts duplicate
input where `Set.of` throws `IllegalArgumentException`.

</details>

**Q4.** Does `List.of("a","b","c").subList(0, 2).contains(null)` throw, and what decides it?

<details><summary>Answer</summary>

It throws. `SubList` carries no flag of its own — it asks the root, lines 497–499:
`return root instanceof ListN && ((ListN<?>)root).allowNulls;`. Here the root is a `ListN` with
`allowNulls == false`, so `allowNulls()` is `false` and `indexOf` throws. A `SubList` over a
`List12` root also throws, for a different reason: `root instanceof ListN` is `false`. A `SubList`
over a `Stream.toList()` result would inherit `true`. Java 21's `reversed()` view was measured to
throw as well.

</details>

**Q5.** A test asserts `assertEquals("[a, b, c]", Set.of("a","b","c").toString())`. It passes
locally, fails in CI. Why, and what is the fix?

<details><summary>Answer</summary>

`SetN`/`MapN` place elements at `probe`-determined slots in an open-addressed table, and the probe
sequence is perturbed by a salt seeded once per JVM. Iteration order is therefore randomised **per
JVM run** and stable **within** a run — exactly the shape that passes on repeated local runs and
fails on a fresh JVM. Two runs in this note set gave `[a, f, e, d, c, b]` and `[a, b, c, d, e, f]`;
three prints inside one JVM were identical. The randomisation is deliberate. Fix: assert set
equality, not string form; if a documented order is genuinely required, use a wrapped
`LinkedHashSet` or Guava's `ImmutableSet`.

</details>

**Q6.** Name the one thing Guava's `ImmutableMap` can do that no JDK factory can, and what the JDK
workaround costs.

<details><summary>Answer</summary>

`ImmutableMap.builder().putAll(defaults).putAll(overrides).buildKeepingLast()` — last-value-wins on
duplicate keys, added in Guava 31.1. Every JDK path throws on a duplicate key: `Map.of`,
`Map.ofEntries` and `Collectors.toUnmodifiableMap` all reject it. (`orderEntriesByValue`, 19.0, is a
second such capability.) The workaround is to pre-merge —
`Stream.concat(defaults.entrySet().stream(), overrides.entrySet().stream())
.collect(Collectors.toMap(Map.Entry::getKey, Map.Entry::getValue, (a, b) -> b))` then `Map.copyOf`
— costing an intermediate `HashMap`, a second pass, and the merge intent buried in stream plumbing,
but no dependency.

</details>

---

## Open questions

1. **Guava `ImmutableCollection.contains(null)` at query time.** The JDK side of the matrix is
   fully measured; for Guava I could not confirm whether `contains(null)` returns `false` or throws
   in 33.x — the Javadoc I retrieved covers construction-time null rejection only. Marked
   `**Unverified:**` in §2's table. Settled by adding `com.google.guava:guava:33.7.1-jre` to a
   scratch classpath and running the §1 harness against `ImmutableList.of("a")`, or by reading
   `ImmutableCollection.contains` in the 33.7.1 sources. No dependency was added and no Guava
   transcript was fabricated.
2. **Escape analysis on the arity-3-to-10 trusted array** (carried from
   [03b](03b-immutability-tiers-b-factory-rules.md) §2). One array is allocated for `List.of` arity
   3–10 — that is what the bytecode does; whether C2 scalarises it after inlining is unmeasured and
   marked `**Unverified:**` there. Settled by JMH with `-prof gc` or `-prof perfnorm`, naming CPU
   and JDK build. No timings are published in either file.

---

**Leaves covered:** 2.4.11–2.4.13 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 647
