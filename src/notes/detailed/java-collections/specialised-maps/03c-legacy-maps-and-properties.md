# 02 Java Collections — Specialised maps and sets — INTERMEDIATE (§2.9.15–2.9.16)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [specialised-maps/03b-weak-hash-map.md](03b-weak-hash-map.md) · Next: [specialised-maps/04-internals-identity-weak.md](04-internals-identity-weak.md)

The previous two files covered maps that are specialised by *semantics* —
[`IdentityHashMap`](03-identity-and-weak.md) redefines key equality,
[`WeakHashMap`](03b-weak-hash-map.md) redefines key lifetime. This file covers two things
specialised by *history*: `Hashtable`, the pre-framework hash map that still turns up in
interview questions and in code from 2004, and `Properties`, which inherits from it and
should not.

---

## `Hashtable` vs `HashMap` vs `ConcurrentHashMap` — the three-way table

### Mental model first

Three answers to "a hash map, but thread-safe?" given twenty years apart. `Hashtable`
(1998, Java 1.0) wraps one monitor around the whole object: correct, and a hard serial
bottleneck. `HashMap` (1998, Java 1.2) drops the lock entirely and hands the concurrency
problem back to you. `ConcurrentHashMap` (2004, Java 1.5) puts a lock on each *bin*, so
threads touching different keys almost never meet.

### The table

| Axis | `Hashtable` | `HashMap` | `ConcurrentHashMap` |
|---|---|---|---|
| Since | 1.0 | 1.2 | 1.5 |
| Null key | rejected (NPE from `key.hashCode()`) | one allowed | rejected (`CHM:994` "Neither the key nor the value can be null") |
| Null value | rejected (`Hashtable.java:475-477` explicit NPE) | allowed | rejected |
| Locking | whole object — every method `synchronized` | none | per-bin: CAS to install the first node, `synchronized (f)` on the bin head otherwise (`CHM:1019`, `:1031`) |
| Iterator semantics | `keySet`/`entrySet`/`values` iterators fail-fast; `keys()`/`elements()` `Enumeration`s **not** fail-fast (`Hashtable.java:89-99`) | fail-fast, `ConcurrentModificationException` | weakly consistent (`CHM:1229`) — never throws CME, may or may not reflect concurrent writes |
| `size()` exactness | exact, under the lock | exact | an estimate; prefer `mappingCount()` (`long`, since 1.8) |
| Ordering | none | none | none |
| Default capacity | **11** (`Hashtable.java:217`) | 16 | 16 |
| Index computation | `(hash & 0x7FFFFFFF) % tab.length` (`:354`) | `hash & (n-1)` | `hash & (n-1)` |
| Growth | `(oldCapacity << 1) + 1` (`:412`) | `oldCapacity << 1` | `oldCapacity << 1` |
| Collision handling | chaining only, no treeify | chaining, treeify at 8 per bin | chaining, treeify at 8 per bin |
| Verdict | legacy — do not use in new code | single-threaded / externally-confined default | the concurrent default |

### Why `Hashtable` is not just "the old `HashMap`"

Two structural differences, both visible in the table above and both consequences of
`Hashtable` predating the collections framework.

**It uses modulo indexing on a non-power-of-two table.** Default capacity is 11
(`Hashtable.java:217`: `this(11, 0.75f)`), growth is `(oldCapacity << 1) + 1` (`:412`) —
so the sequence is 11, 23, 47, 95 — and the bucket index is
`(hash & 0x7FFFFFFF) % tab.length` (`:354`). The mask clears the sign bit so the modulo
cannot go negative; the modulo itself is an integer division, which is why `Hashtable` is
slower per operation than `HashMap`'s single `hash & (n-1)` mask. A prime-ish table length
was the 1990s answer to poor `hashCode` distributions; `HashMap` instead keeps power-of-two
lengths and spreads the hash with `h ^ (h >>> 16)`.

**It carries a pre-`Map` API.** `keys()` and `elements()` return `Enumeration`, not
`Iterator`, and those `Enumeration`s are explicitly **not** fail-fast (`:95-99`) while the
`keySet`/`entrySet`/`values` iterators retrofitted in 1.2 are. It also has
`contains(Object value)` — a *value* search, which reads like `containsKey` and is not. And
`rehash()` is `protected` (`:407`), an extension point nobody wants.

**Pitfall:** *wrong belief* — "`Collections.synchronizedMap(new HashMap<>())` is the modern
replacement for `Hashtable`." *Symptom* — no scalability improvement at all; the profile
still shows every thread queued on one monitor, and compound operations
(`if (!m.containsKey(k)) m.put(k, v)`) are still racy because the wrapper only makes each
individual call atomic. *Fix* — `ConcurrentHashMap`, and use its atomic composites
(`putIfAbsent`, `computeIfAbsent`, `merge`) rather than check-then-act.

CHM's table layout, `sizeCtl`, treeification and `CounterCell`-based sizing are covered in
the `concurrent-collections/` files; this file needs only the decision axes.

**Interview:** "Why does `ConcurrentHashMap` forbid null values when `HashMap` allows
them?" — Because in a concurrent map `get` returning `null` would be irreducibly
ambiguous between "absent" and "mapped to null", and unlike single-threaded code you
cannot resolve it with a follow-up `containsKey`: the mapping may change between the two
calls. Forbidding null makes `null` mean exactly "absent".

> **`Hashtable`** is the pre-framework, whole-object-synchronized hash map with modulo
> indexing on an 11-based capacity sequence and an `Enumeration` API; it is superseded for
> single-threaded use by `HashMap` and for concurrent use by `ConcurrentHashMap`, and
> survives only because `Properties` extends it.

---

## `Properties` and `System.getProperties()`

### Mental model first

A `Map<String,String>` wearing a `Map<Object,Object>` costume, with a linked list of
fallback maps behind it. `getProperty` walks that fallback chain and refuses to return
anything that is not a `String`; the inherited `Map` methods do neither. So the same object
answers two different questions depending on which half of its API you ask, and the two
answers routinely disagree.

### The inheritance wart

`Properties extends Hashtable<Object,Object>` (`Properties.java:144`), and that
inheritance is the textbook example of inheritance-for-implementation gone wrong. The
class wants to be a `Map<String,String>` with a defaults chain; it inherited a
`Map<Object,Object>`, so `put(Object, Object)` will accept an `Integer` value that
`getProperty` then refuses to return. You cannot fix it without breaking source
compatibility, so it has stood since Java 1.0. Even `setProperty` leaks it
(`:229-231`): it takes `(String, String)` but returns `Object`, because it is a thin
`return put(key, value)` and `put`'s return type is fixed by the superclass.

Modern JDKs made the wart stranger, not better. Since Java 9 the actual storage is a
delegate, not the inherited table (`Properties.java:167`):

```java
    private transient volatile ConcurrentHashMap<Object, Object> map;
```

Every `Hashtable` method is overridden to forward to `map`. So the superclass's table is
vestigial, `Properties` is genuinely thread-safe rather than merely `synchronized`
(`Properties.java:132-133`), and the javadoc has to state explicitly that "The
`Properties` class does not inherit the concept of a load factor from its superclass"
(`:135-137`). The inheritance now buys nothing but the type.

**Insight:** this is why `Properties` is fast and correct under concurrent reads despite
its ancestry, and also why passing a `Properties` where a `Hashtable` is expected is
harmless — the `Hashtable` half is a facade. What it does *not* fix is the type looseness:
the `Object`-typed API is public and cannot be narrowed.

### `getProperty` is not `get`

```java
    public String getProperty(String key) {
        Object oval = map.get(key);
        String sval = (oval instanceof String) ? (String)oval : null;
        Properties defaults;
        return ((sval == null) && ((defaults = this.defaults) != null)) ? defaults.getProperty(key) : sval;
    }
```

`Properties.java:1146-1151`. Two behaviours `get` does not have. The `instanceof String`
test silently converts a non-`String` value to `null` — a type check, not a cast, so no
`ClassCastException`. And if the local lookup produced nothing, it recurses into
`this.defaults` (`protected volatile Properties defaults`, `:159`), which is the second
constructor argument. The recursion is unbounded in depth, so defaults chain arbitrarily.
`get`, `containsKey` and `size` see only the local level.

`stringPropertyNames()` (`:1209-1213`) is the bridge between the two views: it walks the
defaults chain, keeps only entries whose key *and* value are both `String`, and returns
`Collections.unmodifiableSet(h.keySet())` over a freshly built `HashMap` — so it is a
**snapshot copy**, not a live view. Mutating the `Properties` afterwards does not change
the returned set.

`System.getProperties()` returns the live, mutable, shared `Properties` object — not a
copy. Mutating it changes what `System.getProperty` sees for the rest of the JVM's life,
which is both the mechanism behind `-D` overrides applied programmatically and a
process-global mutable singleton you should treat as read-mostly.

### A minimal concrete example

```java
import java.util.Properties;

public class PropsDemo {
    public static void main(String[] args) {
        Properties base = new Properties();
        base.setProperty("db.url", "jdbc:postgresql://localhost/app");
        base.setProperty("db.pool", "10");

        Properties override = new Properties(base);   // base becomes `defaults`
        override.setProperty("db.pool", "50");

        System.out.println("getProperty(db.url)  = " + override.getProperty("db.url"));
        System.out.println("get(db.url)          = " + override.get("db.url"));
        System.out.println("getProperty(db.pool) = " + override.getProperty("db.pool"));
        System.out.println("override.size()      = " + override.size());
        System.out.println("containsKey(db.url)  = " + override.containsKey("db.url"));

        // The Hashtable inheritance lets a non-String value in through put().
        override.put("db.timeout", 30);               // Integer, not String
        System.out.println("get(db.timeout)         = " + override.get("db.timeout"));
        System.out.println("getProperty(db.timeout) = " + override.getProperty("db.timeout"));
        System.out.println("stringPropertyNames()   = " + override.stringPropertyNames());

        try {
            override.put("bad", null);
        } catch (NullPointerException e) {
            System.out.println("put(k, null) -> " + e.getClass().getSimpleName()
                    + " (Hashtable rejects nulls)");
        }

        Properties sys = System.getProperties();
        System.out.println("System.getProperties() identity-equal on second call: "
                + (sys == System.getProperties()));
        sys.setProperty("my.injected.flag", "on");
        System.out.println("System.getProperty(my.injected.flag) = "
                + System.getProperty("my.injected.flag"));
        System.out.println("java.version = " + sys.getProperty("java.version"));
    }
}
```

Real output, JDK 21.0.7+8-LTS-245:

```
getProperty(db.url)  = jdbc:postgresql://localhost/app
get(db.url)          = null
getProperty(db.pool) = 50
override.size()      = 1
containsKey(db.url)  = false
get(db.timeout)         = 30
getProperty(db.timeout) = null
stringPropertyNames()   = [db.pool, db.url]
put(k, null) -> NullPointerException (Hashtable rejects nulls)
System.getProperties() identity-equal on second call: true
System.getProperty(my.injected.flag) = on
java.version = 21.0.7
```

`size() == 1` and `containsKey("db.url") == false` while `getProperty("db.url")`
succeeds — the `Map` view and the property view disagree, by design.
`getProperty("db.timeout")` is `null` even though `get` returns `30`, and
`stringPropertyNames()` omits `db.timeout` while including the inherited `db.url`. Four
inconsistencies in one twelve-line program, all traceable to the `Hashtable` inheritance.

> **`Properties`** is a `Hashtable<Object,Object>` subclass that since Java 9 stores its
> data in an internal `ConcurrentHashMap`, adds a recursive `defaults` chain and a
> `String`-only type filter on top of the inherited `Map` API, and is exposed live and
> mutable through `System.getProperties()`.

---

## Pitfalls

### Treating `Collections.synchronizedMap(new HashMap<>())` as the concurrent upgrade over `Hashtable`

**Wrong**

```java
Map<String, Integer> counts = Collections.synchronizedMap(new HashMap<>());
// still racy: two calls, no atomicity across them
Integer old = counts.get(key);
counts.put(key, old == null ? 1 : old + 1);
```

Every operation serialises on one monitor, exactly like `Hashtable`, and the
check-then-act above loses updates under contention.

**Right**

```java
Map<String, Integer> counts = new ConcurrentHashMap<>();
counts.merge(key, 1, Integer::sum);   // one atomic op, bin-level lock
```

**Why people believe it:** the wrapper is younger than `Hashtable` and lives in the modern
framework, so it looks like the modern answer. It is the same lock granularity with an
extra indirection.

### Mixing `get`/`put` with `getProperty`/`setProperty` on the same `Properties`

**Wrong**

```java
Properties p = new Properties(defaults);
p.put("port", 8080);                       // Integer via the Hashtable API
System.out.println(p.getProperty("port")); // null — instanceof String filter
System.out.println(p.getProperty("host")); // resolves through defaults
System.out.println(p.containsKey("host")); // false — Map view ignores defaults
```

Three surprises, no exceptions.

**Right**

```java
Properties p = new Properties(defaults);
p.setProperty("port", "8080");                        // String only
int port = Integer.parseInt(p.getProperty("port"));   // parse at the edge
// Enumerate through the property view, which honours the defaults chain:
for (String name : p.stringPropertyNames()) { /* ... */ }
```

Pick one half of the API and stay in it. `setProperty`/`getProperty`/`stringPropertyNames`
is the coherent half.

**Why people believe it:** `Properties` *is* a `Map`, so the `Map` methods are visible,
documented and type-check. Nothing signals that they see a different data set than
`getProperty` does.

### Assuming `stringPropertyNames()` is a live view

**Wrong**

```java
Properties p = new Properties();
p.setProperty("a", "1");
Set<String> names = p.stringPropertyNames();
p.setProperty("b", "2");
System.out.println(names);   // [a] — b is missing
```

**Right**

```java
Properties p = new Properties();
p.setProperty("a", "1");
p.setProperty("b", "2");
Set<String> names = p.stringPropertyNames();   // snapshot taken after all writes
System.out.println(names);                     // [a, b]
```

**Why people believe it:** `keySet()`, `values()` and `entrySet()` on every other
`java.util` map *are* live views, so the habit transfers. `stringPropertyNames()`
(`:1209-1213`) builds a fresh `HashMap` by walking the defaults chain and returns
`Collections.unmodifiableSet` over its key set — it has to copy, because there is no single
underlying map that already contains the merged result.

### Mutating `System.getProperties()` and expecting it to be scoped

**Wrong**

```java
@Test
void usesTestRegion() {
    System.getProperties().setProperty("aws.region", "eu-west-1");
    // ... assertions ...
}   // never undone: leaks into every later test in the same JVM
```

**Right**

```java
@Test
void usesTestRegion() {
    String previous = System.setProperty("aws.region", "eu-west-1");
    try {
        // ... assertions ...
    } finally {
        if (previous == null) System.clearProperty("aws.region");
        else System.setProperty("aws.region", previous);
    }
}
```

Better: use your test framework's system-property extension, which does the save/restore
for you.

**Why people believe it:** `getProperties()` reads like an accessor returning a value, and
most getters in the JDK that return a collection return a copy or an unmodifiable view.
This one returns the live singleton.

---

## Cheat sheet

| Fact | Value |
|---|---|
| `Hashtable` since / default capacity | 1.0 / **11**, load factor 0.75 |
| `Hashtable` growth | `(oldCapacity << 1) + 1` → 11, 23, 47, 95 |
| `Hashtable` index | `(hash & 0x7FFFFFFF) % tab.length` — modulo, not mask |
| `Hashtable` locking | every method `synchronized` on the whole object |
| `Hashtable` nulls | key and value both rejected (`:475-477`) |
| `Hashtable` iterators | `keySet`/`entrySet`/`values` fail-fast; `keys()`/`elements()` `Enumeration`s **not** |
| `Hashtable` oddity | `contains(Object)` searches **values**; `rehash()` is `protected` |
| `HashMap` nulls | one `null` key, any number of `null` values |
| `CHM` since / nulls | 1.5 / neither key nor value may be null (`CHM:994`) |
| `CHM` locking | CAS to install first node, `synchronized (f)` on bin head (`:1019`, `:1031`) |
| `CHM` iterators | weakly consistent (`:1229`), never throw CME |
| `CHM` size | `size()` is an estimate; `mappingCount()` returns `long`, since 1.8 |
| `synchronizedMap` | same single lock as `Hashtable` — not an upgrade |
| `Properties` supertype | `extends Hashtable<Object,Object>` (`:144`) |
| `Properties` real storage | `private transient volatile ConcurrentHashMap<Object,Object> map` (`:167`), since Java 9 |
| `Properties` thread safety | genuinely thread-safe (`:132-133`); load factor not inherited (`:135-137`) |
| `defaults` | `protected volatile Properties defaults` (`:159`), second ctor arg, recursion unbounded |
| `getProperty` | `instanceof String` filter, then recurse into `defaults` (`:1146-1151`) |
| `get`/`containsKey`/`size` | local level only, no type filter |
| `setProperty` | `(String, String)` in, `Object` out (`:229-231`) |
| `stringPropertyNames()` | snapshot copy, unmodifiable, walks defaults, `String`-only (`:1209-1213`) |
| `System.getProperties()` | live, mutable, shared singleton — not a copy |

---

## Self-test

**Q1.** `override.getProperty("db.url")` returns a value but `override.get("db.url")` returns `null` and `override.size()` is 1. Explain.

<details><summary>Answer</summary>

`override` was constructed as `new Properties(base)`, so `base` is its `defaults`, not its
contents. `get`, `containsKey` and `size` are inherited `Map` operations and see only the
local level, which holds one entry (`db.pool`). `getProperty` (`Properties.java:1146-1151`)
first checks the local `map`, and on a miss recurses into `this.defaults` — so it finds
`db.url` in `base`. The `Map` view and the property view legitimately disagree, which is
why you should never mix `get`/`put` with `getProperty`/`setProperty` on the same object.

</details>

**Q2.** Why does `ConcurrentHashMap` reject null values when `HashMap` accepts them?

<details><summary>Answer</summary>

In `HashMap`, `get` returning `null` is ambiguous between "no mapping" and "mapped to
null", and you disambiguate with `containsKey`. In a concurrent map that follow-up is
useless: the mapping can change between `get` and `containsKey`, so the ambiguity is
irreducible. Forbidding null makes `null` mean exactly "absent", which is what every
atomic method (`putIfAbsent`, `computeIfAbsent`, `merge`) needs in order to have a
well-defined contract. `Hashtable` also rejects both null keys and null values
(`Hashtable.java:475-477`), though for the less principled reason that it predates the
question.

</details>

**Q3.** `Hashtable`'s default capacity is 11 and it grows by `2n+1`, while `HashMap` uses 16 and doubles. What follows from that difference?

<details><summary>Answer</summary>

`Hashtable`'s table length is never a power of two (11, 23, 47, 95, …), so it cannot use a
bit mask to find a bucket. It computes `(hash & 0x7FFFFFFF) % tab.length` (`:354`) — the
mask clears the sign bit so the remainder cannot be negative, and the `%` is an integer
division, which is materially slower than `HashMap`'s single `hash & (n-1)`. The
odd/prime-ish length was the 1990s mitigation for `hashCode` implementations that
clustered in the low bits. `HashMap` solved the same problem differently: keep power-of-two
lengths for cheap masking, and spread the hash first with `h ^ (h >>> 16)`. `Hashtable`
also has no treeification, so a pathological bucket stays a linked list at O(n).

</details>

**Q4.** `Properties` is documented as thread-safe and as not inheriting a load factor, despite extending `Hashtable`. What changed, and when?

<details><summary>Answer</summary>

Since Java 9, `Properties` stores nothing in the inherited `Hashtable` table. It holds
`private transient volatile ConcurrentHashMap<Object, Object> map` (`Properties.java:167`)
and overrides every `Hashtable` method to forward to it. So the superclass's table — and
with it the load-factor tuning parameter — is vestigial, which is why the `@apiNote` at
`:135-137` has to say so explicitly, and the concurrency guarantee at `:132-133` comes from
`ConcurrentHashMap` rather than from `synchronized` methods. The inheritance survives purely
for source and binary compatibility: it now buys the type and nothing else.

</details>

**Q5.** Two `Enumeration`-returning methods on `Hashtable` behave differently from its iterators under concurrent modification. Which, and why does the difference exist?

<details><summary>Answer</summary>

`keys()` and `elements()` return `Enumeration`s that are explicitly **not** fail-fast
(`Hashtable.java:95-99`); the iterators from `keySet()`, `entrySet()` and `values()` are
fail-fast and throw `ConcurrentModificationException`. The difference is archaeological:
the `Enumeration` methods shipped in Java 1.0, before `ConcurrentModificationException`
existed, and their behaviour could not be changed without breaking existing code. The
collection views were retrofitted in 1.2 when `Hashtable` was made to implement `Map`, and
they got the then-new fail-fast semantics. So the same object offers two traversal APIs
with two different concurrency contracts.

</details>

**Q6.** Is `stringPropertyNames()` a view or a copy, and what does the answer imply?

<details><summary>Answer</summary>

A copy. `:1209-1213` builds a fresh `HashMap`, calls `enumerateStringProperties(h)` to walk
the local map *and* the whole `defaults` chain keeping only entries whose key and value are
both `String`, then returns `Collections.unmodifiableSet(h.keySet())`. It must copy: there
is no single existing map holding the merged, filtered result, so there is nothing to view.
Implications: writes after the call are invisible in the returned set; the set is
unmodifiable so you cannot use it to remove properties; and the call costs O(total
properties across the chain) rather than being free like `keySet()`.

</details>

**Q7.** Your service reads `System.getProperty("feature.x")` at startup. A test sets it via `System.getProperties().setProperty(...)` and passes; a later unrelated test then fails. Diagnose.

<details><summary>Answer</summary>

`System.getProperties()` returns the live, shared, mutable `Properties` singleton, not a
copy — the demo above confirms `sys == System.getProperties()`. Mutating it is a
process-global side effect that persists for the JVM's lifetime, and test frameworks
normally run a whole module in one JVM. The first test therefore leaves `feature.x` set for
every test that follows, and any test whose behaviour depends on that property (or on the
absence of it) will see the wrong value. Fix: use `System.setProperty` and restore the
previous value in a `finally`, using `System.clearProperty` when there was none, or use the
framework's system-property extension.

</details>

**Q8.** In one line each, when do you choose `Hashtable`, `HashMap`, `ConcurrentHashMap`?

<details><summary>Answer</summary>

`Hashtable`: never in new code — the only legitimate encounters are `Properties`, legacy
APIs whose signatures demand it (`javax.naming` and some JDBC drivers), and interview
questions. `HashMap`: the default whenever the map is confined to one thread or externally
guarded by a lock you already hold, and you want null tolerance and the lowest per-op cost.
`ConcurrentHashMap`: whenever more than one thread touches the map, including the common
case of a cache or registry populated lazily — and then use its atomic composites
(`computeIfAbsent`, `merge`) instead of check-then-act, since that is the whole reason to
prefer it over a synchronized wrapper.

</details>

---

**Leaves covered:** 2.9.15–2.9.16 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 502
