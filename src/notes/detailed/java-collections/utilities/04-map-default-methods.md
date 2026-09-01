# 02 Java Collections — Utility surfaces — INTERMEDIATE (§2.11)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [utilities/03-sorting-b-primitives.md](03-sorting-b-primitives.md) · Next: [utilities/05-streams-and-collectors.md](05-streams-and-collectors.md)

## 1. Why this section exists

`Map` grew a batch of default methods in Java 8: `getOrDefault`, `putIfAbsent`, `computeIfAbsent`, `computeIfPresent`, `compute`, `merge`, `replaceAll`, `forEach`, `remove(k,v)`, `replace(k,old,new)`. They read like small conveniences, but each one has a null-handling contract that differs subtly from its neighbors, and several are outright traps in interviews and in production code. This file works through the full cluster: what each method does, where its null semantics diverge, the multimap idiom that `computeIfAbsent` enables, why these default implementations are non-atomic on `HashMap` but atomic on `ConcurrentHashMap`, and the specific way recursive `computeIfAbsent` corrupts a `HashMap`.

## 2. Concept 1 — compute / merge / computeIfAbsent null semantics (2.11.1, 2.11.2, 2.11.4, 2.11.5, 2.11.6, 2.11.7)

**[BOTH]** This is the single most interview-relevant cluster in the `Map` default-method surface. Five methods look similar — they all take a key and some function-shaped argument and return a value — but each treats "absent" and "null" differently, and getting this wrong produces either silent no-ops or unexpected removals.

### 2.1 What it is

- `getOrDefault(k, def)` — pure read. Returns `map.get(k)` if the key is present (even if its value is `null` — wait, `getOrDefault` returns the stored value, which could itself be `null`; more precisely it returns `def` only if the key is *absent*, per the default implementation's use of `containsKey`). Never mutates the map.
- `putIfAbsent(k, v)` — if the key is absent (or mapped to `null`), stores `v` and returns `null`. If the key is present with a non-null value, returns that existing value and does *not* overwrite it.
- `computeIfAbsent(k, mappingFunction)` — if the key is absent (or mapped to `null`), calls `mappingFunction.apply(k)`; if that returns non-null, stores it and returns it; if it returns `null`, no insertion happens and the method returns `null`.
- `computeIfPresent(k, remappingFunction)` — if the key is present with a non-null value, calls `remappingFunction.apply(k, oldValue)`; if the result is non-null, it replaces the value; if the result is `null`, the entry is **removed**.
- `compute(k, remappingFunction)` — unconditional version of the two above: calls `remappingFunction.apply(k, currentValueOrNull)` regardless of presence; non-null result stores/replaces; `null` result removes the entry (or is a no-op if the key was already absent).
- `merge(k, value, remappingFunction)` — if the key is absent or mapped to `null`, stores `value` directly (the remapping function is *not* called). If the key is present with a non-null value, calls `remappingFunction.apply(oldValue, value)`; non-null result replaces; `null` result removes the entry.

### 2.2 Mechanism / how it works internally

All six are `default` methods declared on the `Map` interface (`java.util.Map`), implemented in terms of `get`, `containsKey`, `put`, and `remove`. That is why, on a plain `HashMap`, none of them are atomic — each default implementation performs multiple separate calls into the map's own methods, with no lock held across them. `HashMap` does not override most of these (it overrides `getOrDefault`, `putIfAbsent`, `compute`, `computeIfAbsent`, `computeIfPresent`, `merge`, `replaceAll`, `remove(k,v)`, `replace(k,old,new)` for performance — single tree/bin traversal instead of two — but still without any atomicity guarantee, because a single-threaded traversal offers no protection against concurrent mutation from another thread).

### 2.3 API shape / method signatures

```java
V getOrDefault(Object key, V defaultValue);
V putIfAbsent(K key, V value);
V computeIfAbsent(K key, Function<? super K, ? extends V> mappingFunction);
V computeIfPresent(K key, BiFunction<? super K, ? super V, ? extends V> remappingFunction);
V compute(K key, BiFunction<? super K, ? super V, ? extends V> remappingFunction);
V merge(K key, V value, BiFunction<? super V, ? super V, ? extends V> remappingFunction);
```

### 2.4 Complexity (time / space)

Same asymptotic cost as the underlying `get`/`put`/`remove` for the concrete map — O(1) amortized for `HashMap`, O(log n) for `TreeMap`. The default-method wrapping adds a constant number of extra method calls, not a different complexity class.

### 2.5 Invariants / contracts

- `getOrDefault` never mutates.
- `putIfAbsent` returns the *existing* value (not a boolean) — see the dedicated pitfall in §3.
- `computeIfAbsent` never inserts a `null` result from the mapping function.
- `computeIfPresent`/`compute` treat a `null` remap result as a removal signal.
- `merge`'s remapping function is only invoked when both an existing value and the new `value` argument are non-null; if the key is absent, `value` is stored directly with no function call.
- `merge(k, null, fn)` throws `NullPointerException` immediately — the `value` parameter itself must be non-null, unconditionally, regardless of whether the key is present.

### 2.6 Failure modes / edge cases

The diagram below is the fastest way to hold all six methods' null behavior in your head at once.

![compute/merge null semantics: a 2x2 grid of key-absent/key-present crossed with null/non-null remap result, each cell labelled with its exact outcome (no insertion, insertion, replacement, removal), plus a callout for merge(k, null, fn) throwing NPE on the value argument itself](../diagrams/D-58-compute-merge-null-semantics.svg)

Read the grid as: rows are "key absent" vs "key present (non-null value)"; columns are "function/value evaluates to null" vs "non-null". The two cells that surprise people in interviews are top-right (`computeIfAbsent` with a mapping function that returns `null` — **no insertion**, not an exception) and bottom-left (`computeIfPresent`/`compute` with a `null` remap result on a present key — **removal**, not a no-op). The callout captures that `merge`'s `value` argument is checked eagerly, before any key lookup — `map.merge(k, null, fn)` throws `NullPointerException` even if `k` doesn't exist and `fn` would never be called.

```java
import java.util.HashMap;
import java.util.Map;

public class NullSemanticsDemo {
    public static void main(String[] args) {
        Map<String, Integer> m = new HashMap<>();

        // 2.11.1 getOrDefault vs computeIfAbsent: getOrDefault never inserts.
        System.out.println(m.getOrDefault("a", 0)); // 0
        System.out.println(m.containsKey("a"));      // false — untouched

        // 2.11.2 putIfAbsent returns the EXISTING value, not a boolean.
        Integer prev1 = m.putIfAbsent("a", 1); // key absent -> stores 1
        System.out.println(prev1);              // null (no prior value)
        Integer prev2 = m.putIfAbsent("a", 99); // key present -> ignored
        System.out.println(prev2);              // 1 (the value that was already there)
        System.out.println(m.get("a"));          // 1 — NOT overwritten

        // 2.11.4 computeIfAbsent with a mapping function returning null: no insertion.
        Integer v = m.computeIfAbsent("b", k -> null);
        System.out.println(v);                   // null
        System.out.println(m.containsKey("b"));  // false — nothing was inserted

        // 2.11.5 computeIfPresent / compute returning null REMOVES the entry.
        m.put("c", 5);
        m.computeIfPresent("c", (k, val) -> null);
        System.out.println(m.containsKey("c"));  // false — entry removed

        m.put("d", 5);
        m.compute("d", (k, val) -> null);
        System.out.println(m.containsKey("d"));  // false — entry removed

        // 2.11.6 merge for counters.
        Map<String, Integer> counts = new HashMap<>();
        for (String word : new String[] {"x", "y", "x", "x", "y"}) {
            counts.merge(word, 1, Integer::sum);
        }
        System.out.println(counts); // {x=3, y=2}

        // 2.11.7 merge remapping to null removes the entry.
        counts.merge("x", 0, (oldV, newV) -> null);
        System.out.println(counts.containsKey("x")); // false

        // merge with a null VALUE argument throws, unconditionally.
        try {
            counts.merge("y", null, Integer::sum);
        } catch (NullPointerException e) {
            System.out.println("merge(k, null, fn) threw NPE as documented");
        }
    }
}
```

### 2.7 When to use / when NOT to use

Use `merge` for counters and accumulator maps — it is the shortest, most idiomatic form and reads clearly at the call site. Use `computeIfAbsent` when the "default" is expensive to construct or is itself a mutable container (the multimap idiom in Concept 2). Use `compute`/`computeIfPresent` when the transformation depends on both the key and the *possible absence* of a value in a way `merge` can't express (e.g., different logic when creating vs. updating). Avoid `compute`/`merge` when you need atomicity across threads on a plain `HashMap` — none of these give you that; reach for `ConcurrentHashMap` instead (Concept 3).

### 2.8 Comparisons with alternatives

`getOrDefault(k, def) + 1` computed manually and then `put` back is functionally similar to `merge` for a counter but takes two map operations (`get`, then `put`) instead of one, and is not exception-safe if you forget the `put`. See the mandatory comparison table in §2.11.8 below for the full five-way breakdown.

**Insight:** the six methods above are best memorized as answering one question each: "does this call insert a fresh mapping when it wasn't asked to?" (`computeIfAbsent`: no, on null result), "does this call remove an existing mapping as a side effect of its return value?" (`compute`/`computeIfPresent`/`merge`: yes, on null result), and "which argument's nullness is checked before any map lookup at all?" (`merge`'s `value` parameter).

## 3. Concept 2 — the multimap idiom via computeIfAbsent (2.11.3)

**[BOTH]**

### 3.1 What it is

`Map<K, List<V>>` (or `Map<K, Set<V>>`) is not a first-class type in `java.util` — there is no `Multimap` interface in the JDK (Guava has one). The idiomatic way to build one with core collections is:

```java
map.computeIfAbsent(k, key -> new ArrayList<>()).add(v);
```

### 3.2 Mechanism

`computeIfAbsent` checks whether `k` is present with a non-null value. If not, it calls the lambda to create a fresh `ArrayList`, stores it under `k`, and returns it. If `k` is already present, it returns the existing list directly — no new list is created. Either way, the expression `map.computeIfAbsent(...)` evaluates to a `List<V>` reference, and `.add(v)` is then called on it. The net effect: one call site handles both "first value for this key" and "nth value for this key."

### 3.3 API shape

```java
Map<String, List<Integer>> groups = new HashMap<>();
groups.computeIfAbsent("evens", k -> new ArrayList<>()).add(2);
groups.computeIfAbsent("evens", k -> new ArrayList<>()).add(4);
groups.computeIfAbsent("odds", k -> new ArrayList<>()).add(1);
// groups == {evens=[2, 4], odds=[1]}
```

### 3.4 Complexity

One map lookup/insert (O(1) amortized for `HashMap`) plus one `List.add` (O(1) amortized for `ArrayList`). The naive alternative — check `containsKey`, then either `get` or `put` a new list, then `add` — costs the same asymptotically but takes two or three map operations instead of one and is easy to get wrong (see Pitfalls).

### 3.5 When to use / when NOT to use

Use it whenever you're grouping values by key without pulling in a stream/collector (`Collectors.groupingBy` is the declarative equivalent when you have a whole source collection up front — see file 05). Avoid it inside a loop that also does other lookups on the *same* key inside the lambda — the lambda in `computeIfAbsent` must not touch the enclosing map (see Concept 4).

### 3.6 Comparisons with alternatives

`Collectors.groupingBy(keyFn, Collectors.toList())` builds the same shape in one pass over a `Stream`, but requires the full source up front; `computeIfAbsent` composes naturally inside an incremental loop (e.g., reading records one at a time from a stream/socket).

**Interview:** if asked to implement a word-index (`Map<String, List<Integer>>` mapping word to line numbers) live, `computeIfAbsent` is the one-liner interviewers expect; reaching for `containsKey`/`get`/`put` three-step logic instead is a signal of unfamiliarity with the Java 8 default methods.

## 4. Concept 3 — non-atomicity of default methods on HashMap vs ConcurrentHashMap (2.11.11, 2.11.14)

**[BOTH]** base; **[STAFF]** extension on ConcurrentHashMap internals.

### 4.1 What it is

`remove(k, v)` and `replace(k, oldValue, newValue)` are shaped like compare-and-swap (CAS) operations: "remove this mapping only if it currently maps to exactly this value" / "replace the value only if it currently equals this expected old value." That shape strongly suggests atomicity — but on a plain `HashMap`, it is not atomic. `[TRAP]`

### 4.2 Mechanism

The `Map` interface's default implementations of `remove(k, v)` and `replace(k, old, new)` are literally:

```java
default boolean remove(Object key, Object value) {
    Object curValue = get(key);
    if (!Objects.equals(curValue, value) || (curValue == null && !containsKey(key))) {
        return false;
    }
    remove(key);
    return true;
}
```

That is a `get` followed by a separate `remove` — two distinct calls into the map, with a window between them. On `HashMap`, nothing prevents another thread from mutating the map in that window; the "CAS" is only CAS-*shaped*, not CAS-*guaranteed*.

### 4.3 API shape

```java
boolean remove(Object key, Object value);
boolean replace(K key, V oldValue, V newValue);
```

### 4.4 Failure modes

On a `HashMap` shared across threads without external synchronization, two threads can both read the same `curValue` via `get`, both see it match, and both proceed to remove/replace — the second one "wins" without either racing thread ever knowing the operation was not exclusive. This is the general hazard of unsynchronized `HashMap` access (data races, lost updates, and potentially `HashMap`'s internal structure corruption under concurrent resizing) — `remove(k,v)`/`replace(k,old,new)` do not add any additional protection over plain `get`+`remove` called separately by hand.

### 4.5 [STAFF] Why ConcurrentHashMap is different

`[SOURCE]` **Insight:** the `Map` interface's Javadoc for these default methods explicitly documents that they are not atomic by contract — the interface only specifies *behavior*, not *atomicity*, and leaves atomicity as something a concrete implementation may choose to provide. `ConcurrentHashMap` overrides essentially every one of these default methods (`putIfAbsent`, `computeIfAbsent`, `computeIfPresent`, `compute`, `merge`, `remove(k,v)`, `replace(k,old,new)`, `getOrDefault`, `replaceAll`, `forEach`) with implementations that hold the appropriate internal bin lock (or use CAS loops on the bin's first node) across the entire read-modify-write sequence, so the CAS-shaped contract is actually CAS-*atomic* there. The `ConcurrentHashMap` class Javadoc states this directly: operations such as `putIfAbsent` are performed atomically. This is the concrete reason to reach for `ConcurrentHashMap` instead of `Collections.synchronizedMap(new HashMap<>())` when you need atomic check-then-act semantics — the synchronized wrapper only makes *individual* calls thread-safe, not the two-call sequences these default methods are built from, unless you wrap the whole default-method call in your own external lock.

### 4.6 When to use / when NOT to use

Use plain `HashMap` with these methods only when the map is confined to one thread, or externally guarded by a lock that covers the whole call (not just the internal `get`/`remove` pair, since you don't control that boundary from outside). Use `ConcurrentHashMap` whenever multiple threads need atomic check-then-act on shared map state — that atomicity is the entire reason the class exists beyond thread-safety of individual calls.

## 5. Concept 4 — recursive computeIfAbsent corruption (2.11.12, 2.11.13)

**[BOTH]** mechanism; **[STAFF]** production-incident framing.

### 5.1 What it is

Calling `computeIfAbsent` on a `HashMap` again, on the *same map*, from inside the mapping function passed to an outer `computeIfAbsent` call, is a well-known corruption/deadlock hazard depending on the map type. `[TRAP]` `[X-REF 05]`

```java
Map<Integer, Long> fib = new HashMap<>();

long fibonacci(int n) {
    if (n <= 1) return n;
    return fib.computeIfAbsent(n, k ->
        fibonacci(k - 1) + fibonacci(k - 2)   // recursively calls computeIfAbsent on `fib` again
    );
}
```

### 5.2 Mechanism — the one self-contained paragraph

On a plain `HashMap`, since Java 9, `computeIfAbsent` (and the other Java 8 default-turned-overridden methods) track `modCount` across the single call and throw `ConcurrentModificationException` on a best-effort basis if the map's structure changed during the mapping function's execution — this was JDK-8071667, "HashMap.computeIfAbsent() adds entry that maps to null," which in fixing an entry-corruption bug also added the modCount check, and the change shipped in Java 9 (in Java 8, the check was absent and the mapping function could silently corrupt the map's internal bin structure instead of throwing). A recursive `computeIfAbsent` call on the *same* `HashMap` — whether direct or, as in the Fibonacci example, indirect through a chain of calls — structurally modifies the map while the outer call is still "in flight" for that bin, so the outer call's post-check sees a changed `modCount` and throws `ConcurrentModificationException`. On `ConcurrentHashMap`, the outcome is different and, in production, worse: `ConcurrentHashMap` synchronizes each `computeIfAbsent` call by locking the bin (the `Node` linked list or tree) that the key hashes to, for the duration of the mapping-function call; if the mapping function recursively calls `computeIfAbsent` again with a key that hashes to the *same* bin, the recursive call blocks forever trying to acquire a lock the outer call already holds on the current thread — a self-deadlock, not an exception, and one that is silent until the thread simply never returns. Guide 05 (Concurrency) covers `ConcurrentHashMap`'s locking granularity, the broader "no map operation inside a `ConcurrentHashMap` computation" rule, and the officially documented restriction in full; this file states only the mechanism.

### 5.3 API shape / observable symptom

```java
import java.util.HashMap;
import java.util.Map;

public class RecursiveComputeIfAbsentDemo {
    public static void main(String[] args) {
        Map<Integer, Long> fib = new HashMap<>();
        try {
            System.out.println(fibonacci(fib, 10));
        } catch (java.util.ConcurrentModificationException e) {
            System.out.println("HashMap: recursive computeIfAbsent threw CME (Java 9+ behavior)");
        }
    }

    static long fibonacci(Map<Integer, Long> fib, int n) {
        if (n <= 1) return n;
        return fib.computeIfAbsent(n, k -> fibonacci(fib, k - 1) + fibonacci(fib, k - 2));
    }
}
```

Running this on Java 9+ throws `ConcurrentModificationException` from the outer `computeIfAbsent` call once the recursive call underneath it mutates `fib`. On Java 8, the equivalent code does not throw — it silently risks losing entries or building an inconsistent bin structure, per JDK-8071667's original bug report and the related nested-recursion follow-up, JDK-8172951.

### 5.4 Invariants / contracts

`HashMap.computeIfAbsent`'s Javadoc states, from Java 9 onward: "The mapping function should not modify this map during computation." This is a documented *should not*, enforced only on a best-effort basis via the modCount check — it is not a hard guarantee for every possible mutation pattern, but recursive `computeIfAbsent` on the same key set reliably triggers it.

### 5.5 When to use / when NOT to use

Never call `computeIfAbsent` (or any mutating map method) on the *same map* from inside another map method's function argument, on any map type. If recursive memoization needs a map, either accumulate results in a local variable and `put` them after the recursive calls return (outside any `computeIfAbsent` lambda), or use a two-phase approach: compute the values first with plain recursion into a local cache, then batch-insert.

**Pitfall:** this includes recursion that is not textually obvious — indirect recursion through several method calls that eventually loops back into `computeIfAbsent` on the same map is just as dangerous as the direct self-call shown above, and is a documented cause of real hangs when `ConcurrentHashMap` is involved.

## 6. Supporting facts (2.11.8, 2.11.9, 2.11.10)

### 6.1 The counter-idiom comparison table (2.11.8)

**[BOTH]** — mandatory table, five approaches to "increment a counter keyed by `k`."

| Approach | Code | Atomic on plain `HashMap`? | Atomic on `ConcurrentHashMap`? | Extra allocation per increment | Best for |
|---|---|---|---|---|---|
| `merge` | `map.merge(k, 1, Integer::sum)` | No | Yes | Autoboxing of the new `Integer` sum | General-purpose counters; most idiomatic single-thread or `ConcurrentHashMap` use |
| `computeIfAbsent(...).increment()` with a mutable counter object | `map.computeIfAbsent(k, x -> new MutableInt()).increment()` | No (map op); counter mutation itself can be non-atomic too unless the counter type is thread-safe | No, unless the mutable counter's own `increment()` is atomic (e.g., backed by an `AtomicLong`) | One counter object per new key only | High-throughput single-threaded counting where autoboxing overhead of repeated `Integer` churn matters |
| `getOrDefault(k, 0) + 1` then `put` | `map.put(k, map.getOrDefault(k, 0) + 1)` | No — two separate map calls, wide race window | No — same two-call shape even on `ConcurrentHashMap`, since you're not using its atomic method | Autoboxing of the new sum | Readable one-off code; avoid in hot paths or concurrent contexts |
| `Collectors.counting()` | `stream.collect(Collectors.groupingBy(fn, Collectors.counting()))` | N/A — builds a fresh map, no shared mutable state during the collect | N/A | Builds the whole result map in one pass; no incremental `put` calls | Batch counting over a complete source collection/stream, not incremental updates |
| `ConcurrentHashMap<K, LongAdder>` values | `map.computeIfAbsent(k, x -> new LongAdder()).increment()` | N/A (requires `ConcurrentHashMap` to be safe) | Yes — the `computeIfAbsent` map op is atomic, and `LongAdder.increment()` is independently atomic and contention-friendly | One `LongAdder` per new key only | High-contention concurrent counting where many threads increment the same small set of keys |

**Interview:** the trap in this table is conflating "the map operation that fetches/creates the counter is atomic" with "the counter's own mutation is atomic." `ConcurrentHashMap.computeIfAbsent` guarantees only one `LongAdder` (or one counter object) is ever created and installed per key — it says nothing about what happens when multiple threads call `.increment()` on that shared object afterward, unless the object's own method is itself thread-safe (as `LongAdder.increment()` is).

### 6.2 replaceAll (2.11.9)

**[BOTH]** `replaceAll(BiFunction<K, V, V> function)` walks every entry and replaces each value with `function.apply(key, oldValue)`, in place. No entries are added or removed — the key set is fixed for the duration of the call; only values change.

```java
Map<String, Integer> prices = new HashMap<>(Map.of("apple", 100, "pear", 200));
prices.replaceAll((k, v) -> v * 2);
System.out.println(prices); // {apple=200, pear=400} (iteration order not guaranteed for HashMap)
```

Because it is purely a value rewrite with no structural change (no rehashing, no bin re-linking), it is cheaper than removing and re-inserting every entry, and it is safe from the `ConcurrentModificationException` concerns that plague structural mutation during iteration — as long as `function` itself does not call back into the map.

### 6.3 forEach and why it cannot break (2.11.10)

**[BOTH]** `forEach(BiConsumer<K, V> action)` calls `action.accept(key, value)` for every entry. Because `BiConsumer.accept` returns `void` and there is no checked or unchecked signal a `BiConsumer` can return to tell `forEach` "stop early," there is no way to `break` out of a `Map.forEach` the way you can `break` out of a `for`-each loop over `entrySet()`. The only ways to terminate early are throwing an exception from inside the lambda (control-flow abuse, and the exception propagates out of `forEach` itself, so it must be caught by the caller) or switching to an explicit `for (Map.Entry<K,V> e : map.entrySet())` loop, which supports a normal `break`.

```java
Map<String, Integer> scores = Map.of("a", 1, "b", 2, "c", 3);

// forEach cannot break — this visits every entry regardless.
scores.forEach((k, v) -> System.out.println(k + "=" + v));

// An explicit loop can break early.
for (Map.Entry<String, Integer> e : scores.entrySet()) {
    if (e.getValue() == 2) break;
    System.out.println(e.getKey() + "=" + e.getValue());
}
```

## Pitfalls

**Pitfall:** treating `putIfAbsent`'s return value as a boolean.

```java
// Wrong — this compiles only if you assign to Integer, but the *logic* is wrong
// if you assume "non-null return means it was just inserted."
if (map.putIfAbsent("k", 1) != null) {
    // WRONG intent: "if insertion happened, do X" — actually this branch runs
    // when the key was ALREADY present, the opposite of what many people expect.
}
```

```java
// Right — putIfAbsent returns the value that WAS there (null if the key was absent).
Integer existing = map.putIfAbsent("k", 1);
if (existing == null) {
    // insertion happened — the key was absent before this call
} else {
    // the key already had a value; it was NOT overwritten
}
```

**Pitfall:** assuming a `null`-returning mapping function for `computeIfAbsent` inserts a `null` value.

```java
// Wrong — assumes the key is now present with a null value.
map.computeIfAbsent("k", key -> null);
Integer v = map.get("k");
// v is null, but NOT because "k" maps to null — "k" was never inserted at all.
System.out.println(map.containsKey("k")); // false, contradicting the "it inserted null" assumption
```

```java
// Right — check containsKey (or check the returned value) if presence-after-the-call matters.
Integer v = map.computeIfAbsent("k", key -> expensiveLookup(key));
if (v == null) {
    // no mapping exists for "k" — nothing was inserted, handle explicitly
}
```

**Pitfall:** using `compute`/`computeIfPresent` to "clear" a value without realizing it deletes the entry.

```java
// Wrong — intent was "set the value to a sentinel," but a null result REMOVES the key.
map.compute("k", (key, old) -> null);
System.out.println(map.containsKey("k")); // false — the entry is gone, not "present with null"
```

```java
// Right — if you actually want removal, call remove() directly for clarity;
// reserve compute()'s null-return behavior for cases where removal-on-null is the intent.
map.remove("k");
// or, if computing the removal condition genuinely needs the old value:
map.computeIfPresent("k", (key, old) -> shouldKeep(old) ? old : null);
```

**Pitfall:** relying on `remove(k, v)` / `replace(k, old, new)` for thread-safety on a plain `HashMap`.

```java
// Wrong — looks atomic, is not, on a plain HashMap shared across threads.
Map<String, Integer> shared = new HashMap<>();
// Thread A and Thread B both call this concurrently on the same key/value:
shared.replace("k", 1, 2); // internally: get() then put() — a race window exists between them
```

```java
// Right — use ConcurrentHashMap when multiple threads need atomic check-then-act.
Map<String, Integer> shared = new ConcurrentHashMap<>();
shared.replace("k", 1, 2); // ConcurrentHashMap overrides this with a lock-guarded, truly atomic version
```

**Pitfall:** calling `computeIfAbsent` recursively on the same `HashMap` inside its own mapping function (see Concept 4 in full above) — throws `ConcurrentModificationException` on Java 9+, silently corrupts on Java 8, and deadlocks on `ConcurrentHashMap`. Fix: never mutate the enclosing map from inside a `computeIfAbsent`/`compute`/`merge` function argument; accumulate recursive results outside the lambda.

## Cheat sheet

| Method | Absent key | Present key, fn/value → null | Present key, fn/value → non-null | Atomic on plain HashMap? |
|---|---|---|---|---|
| `getOrDefault(k, def)` | returns `def`, no mutation | n/a (read-only) | n/a (read-only) | n/a — pure read |
| `putIfAbsent(k, v)` | inserts `v`, returns `null` | n/a — value is non-null by definition of "present" | returns existing value, does not overwrite | No |
| `computeIfAbsent(k, fn)` | calls `fn`; null → no insert, returns `null` | calls `fn`; null → no insert | calls `fn`; non-null → inserts, returns it | No (HashMap) / Yes (ConcurrentHashMap) |
| `computeIfPresent(k, fn)` | no-op, returns `null` | calls `fn`; null → **removes** entry | calls `fn`; non-null → replaces value | No (HashMap) / Yes (ConcurrentHashMap) |
| `compute(k, fn)` | calls `fn(k, null)`; null → no-op; non-null → inserts | calls `fn`; null → **removes** entry | calls `fn`; non-null → replaces value | No (HashMap) / Yes (ConcurrentHashMap) |
| `merge(k, v, fn)` | stores `v` directly, `fn` not called | calls `fn(old, v)`; null → **removes** entry | calls `fn(old, v)`; non-null → replaces value | No (HashMap) / Yes (ConcurrentHashMap) |
| `remove(k, v)` / `replace(k, old, new)` | n/a / n/a | CAS-shaped, not CAS-atomic on HashMap | CAS-shaped, not CAS-atomic on HashMap | No (HashMap) / Yes (ConcurrentHashMap) |
| `replaceAll(fn)` | n/a (iterates existing entries only) | rewrites value in place, no structural change | rewrites value in place, no structural change | Per-entry, not whole-map |
| `forEach(action)` | n/a | cannot `break`; exception is the only early-exit | cannot `break`; exception is the only early-exit | n/a |

Counter-idiom quick pick: single-threaded/general → `merge`; batch over a stream → `Collectors.counting()`; high-contention concurrent → `ConcurrentHashMap<K, LongAdder>`.

## Self-test

<details>
<summary>1. What does `map.putIfAbsent("k", 5)` return if `"k"` already maps to `3`?</summary>

`3` — the existing value. It does not overwrite the mapping, and it does not return a boolean.
</details>

<details>
<summary>2. `map.computeIfAbsent("k", x -> null)` is called and `"k"` was absent beforehand. Is `"k"` in the map afterward?</summary>

No. A mapping function that returns `null` causes `computeIfAbsent` to skip insertion entirely; `containsKey("k")` is `false` afterward.
</details>

<details>
<summary>3. `map.compute("k", (k, v) -> null)` is called and `"k"` was present with value `10`. What is the state of `map` afterward?</summary>

The entry for `"k"` is removed. A `null` result from `compute`'s (or `computeIfPresent`'s) remapping function is treated as a removal signal, not as "store null."
</details>

<details>
<summary>4. What does `map.merge("k", null, Integer::sum)` do if `"k"` is not currently in the map?</summary>

It throws `NullPointerException` immediately. `merge`'s `value` parameter is checked for nullness unconditionally, before any lookup of the key, regardless of whether the key would ultimately be absent or present.
</details>

<details>
<summary>5. Why are `remove(k, v)` and `replace(k, old, new)` not safe as atomic CAS operations on a plain `HashMap`?</summary>

Because `Map`'s default implementations of these methods are built from a `get` followed by a separate `remove`/`put` call — two distinct operations with a window between them. Nothing in `HashMap` prevents another thread from mutating the map in that window, so despite the CAS-shaped signature, there is no atomicity guarantee. `ConcurrentHashMap` overrides these methods with lock-guarded implementations that are genuinely atomic.
</details>

<details>
<summary>6. What changed about `HashMap.computeIfAbsent` starting in Java 9, and why?</summary>

Starting in Java 9 (JDK-8071667), `HashMap`'s Java 8 default-method-derived implementations began tracking `modCount` across the call and throw `ConcurrentModificationException` on a best-effort basis if the mapping function structurally modifies the map during its own execution — for example, by recursively calling `computeIfAbsent` on the same map. In Java 8, no such check existed, and the same recursive pattern could silently corrupt the map's internal bin structure instead of throwing.
</details>

<details>
<summary>7. What happens if the same recursive `computeIfAbsent`-on-self pattern is run against a `ConcurrentHashMap` instead of a `HashMap`?</summary>

It deadlocks rather than throwing. `ConcurrentHashMap.computeIfAbsent` holds the lock on the target bin for the duration of the mapping function's execution; a recursive call that hashes to the same bin blocks forever waiting for a lock the current thread already holds on itself.
</details>

<details>
<summary>8. Give the five ways to implement a counter increment discussed in this file, in order from most idiomatic-single-thread to most contention-friendly-concurrent.</summary>

`getOrDefault(k,0)+1` then `put` (least safe, two-call race window) → `merge(k, 1, Integer::sum)` (idiomatic, still non-atomic on plain `HashMap`) → `computeIfAbsent(...).increment()` on a mutable counter (single-thread efficient, avoids autoboxing churn) → `Collectors.counting()` (batch, whole-stream) → `ConcurrentHashMap<K, LongAdder>` values (best for high-contention concurrent counting).
</details>

<details>
<summary>9. Why can't `Map.forEach`'s lambda `break` out of iteration early?</summary>

Because its functional interface parameter is `BiConsumer<K, V>`, whose `accept` method returns `void`. There is no return channel for `forEach` to interpret as "stop." Throwing from inside the lambda or switching to an explicit `entrySet()` loop are the only ways to exit early.
</details>

<details>
<summary>10. Does `replaceAll(BiFunction)` ever add or remove entries?</summary>

No. It only rewrites the value stored at each existing key; the key set is unchanged, and there is no structural modification (no rehashing or resizing triggered by the call itself).
</details>

---

**Leaves covered:** 2.11.1-2.11.14 (14 leaves)
**Leaves deferred:** none
**Diagrams included:** D-58
**Target version:** Java 21 LTS
**Lines:** 468
