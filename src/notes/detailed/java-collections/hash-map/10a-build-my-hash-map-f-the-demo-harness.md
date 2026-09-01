# 02 Java Collections — `HashMap` — INTERNALS (§4.3 `MyHashMap<K,V>` — the demo harness and the differential test)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [hash-map/10-build-my-hash-map-e-set-linked-and-diff.md](10-build-my-hash-map-e-set-linked-and-diff.md) · Next: [hash-map/10b-build-my-hash-map-g-diff-and-collision-dos.md](10b-build-my-hash-map-g-diff-and-collision-dos.md)

---

Every printed line quoted in files 06 through 10 came out of one program. This file is that program, so you can run it and get the same bytes. It ends with the piece that actually proves the build correct: a 200,000-operation differential test against `java.util.HashMap`, comparing not just final contents but every single return value along the way.

**How the code blocks assemble.** `Demo.java` is the concatenation, in order, of the three blocks labelled `// Demo.java` in this file. It depends on `MyHashMap.java` ([06](06-build-my-hash-map.md), [06a](06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md), [07](07-build-my-hash-map-b-put-get-resize.md), [08](08-build-my-hash-map-c-treeify-and-defaults.md), [09](09-build-my-hash-map-d-views-and-iterator.md)) and on `MyHashSet.java`, `MyLinkedHashMap.java` and `LruCache.java` ([10](10-build-my-hash-map-e-set-linked-and-diff.md)). `Bench.java` is in [10b](10b-build-my-hash-map-g-diff-and-collision-dos.md).

To build and run, with JDK 21 on the path:

```
javac -Xlint:all -d out MyHashMap.java MyHashSet.java MyLinkedHashMap.java LruCache.java Demo.java Bench.java
java -cp out Demo
```

That produces **zero warnings and zero errors** on `javac 21.0.7` / `java 21.0.7+8-LTS-245`, and the output's md5 is **`4dd3a26f8346237a6d5929a8952b8a25`**. If yours differs, something in your transcription differs.

This file has no diagram — D-147 is in [10b](10b-build-my-hash-map-g-diff-and-collision-dos.md).

---

## 1. The two poisoned key types

Supporting fact, three beats.

**Mechanism.** Both records return a constant `hashCode()` of 0, so every instance lands in bucket 0 no matter the capacity. They differ in exactly one thing: `Poison` declares `implements Comparable<Poison>` and passes `comparableClassFor`; `PoisonNC` does not and fails it. That single difference is what separates a treeified bin from a chain, and it is the whole experiment in [10b](10b-build-my-hash-map-g-diff-and-collision-dos.md).

**Gotcha.** A `record` gets `equals` and `hashCode` generated, and you may override either. Overriding `hashCode` alone — as here — leaves the generated component-wise `equals` in place, so the pair is still consistent: equal records still have equal hash codes. Overriding `equals` alone would break that contract and the map would misbehave in ways that have nothing to do with collisions.

> **Definition.** A poisoned key is one whose `hashCode()` deliberately collides for all instances, reducing the hash table to whatever its per-bin structure happens to be.

```java
// Demo.java
import java.util.ArrayList;
import java.util.ConcurrentModificationException;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class Demo {

    record Poison(int id) implements Comparable<Poison> {
        @Override public int hashCode() { return 0; }
        @Override public int compareTo(Poison o) { return Integer.compare(id, o.id); }
    }

    record PoisonNC(int id) {
        @Override public int hashCode() { return 0; }
    }

    public static void main(String[] args) {
        section("1. spread and tableSizeFor");
        System.out.println("spread(null)                = " + MyHashMap.spread(null));
        System.out.println("spread(\"Aa\")                = " + MyHashMap.spread("Aa")
                + "  (raw " + "Aa".hashCode() + ")");
        System.out.println("spread(\"BB\")                = " + MyHashMap.spread("BB")
                + "  (raw " + "BB".hashCode() + ")");
        for (int c : new int[] {0, 1, 2, 5, 16, 17, 1000}) {
            System.out.println("tableSizeFor(" + c + ")" + " ".repeat(Math.max(0, 15 - String.valueOf(c).length()))
                    + "= " + MyHashMap.tableSizeFor(c));
        }

        section("2. lazy table allocation");
        MyHashMap<String, Integer> lazy = new MyHashMap<>(100);
        System.out.println("after new MyHashMap<>(100): table=" + (lazy.table == null ? "null" : "len " + lazy.table.length)
                + ", threshold=" + lazy.threshold);
        lazy.put("first", 1);
        System.out.println("after first put:            table=len " + lazy.table.length
                + ", threshold=" + lazy.threshold);

        MyHashMap<String, Integer> lazyDefault = new MyHashMap<>();
        System.out.println("after new MyHashMap<>():    table=" + (lazyDefault.table == null ? "null" : "len")
                + ", threshold=" + lazyDefault.threshold);
        lazyDefault.put("a", 1);
        System.out.println("after first put:            table=len " + lazyDefault.table.length
                + ", threshold=" + lazyDefault.threshold);

        section("3. put, get, null key, replace");
        MyHashMap<String, Integer> m = new MyHashMap<>();
        System.out.println("put(a,1)      -> " + m.put("a", 1));
        System.out.println("put(a,2)      -> " + m.put("a", 2));
        System.out.println("put(null,99)  -> " + m.put(null, 99));
        System.out.println("get(null)     -> " + m.get(null));
        System.out.println("null lands in bucket " + ((m.table.length - 1) & MyHashMap.spread(null)));
        System.out.println("containsKey(a)=" + m.containsKey("a") + ", containsKey(z)=" + m.containsKey("z"));
        System.out.println("getOrDefault(z, -1) = " + m.getOrDefault("z", -1));
        m.put("nullValued", null);
        System.out.println("getOrDefault(nullValued, -1) = " + m.getOrDefault("nullValued", -1)
                + "  (mapping exists, so the default is NOT used)");
        System.out.println("remove(a)     -> " + m.remove("a") + ", size=" + m.size());

        section("4. resize preserves relative order inside a bin");
        MyHashMap<Integer, String> r = new MyHashMap<>(16, 0.75f);
        for (int i = 0; i < 12; i++) r.put(i * 16, "v" + (i * 16));
        System.out.println("cap=" + r.table.length + " bin[0] before resize: " + binToString(r, 0));
        r.put(192, "v192");
        System.out.println("cap=" + r.table.length + " bin[0] after  resize: " + binToString(r, 0));
        System.out.println("cap=" + r.table.length + " bin[16] after resize: " + binToString(r, 16));
        System.out.println("lo/hi split rule: (hash & oldCap)==0 stays at j, else moves to j+oldCap");

        section("5. treeify screen and the sorted bin");
        MyHashMap<Poison, Integer> tree = new MyHashMap<>(64, 0.75f);
        for (int i = 20; i >= 1; i--) tree.put(new Poison(i), i);
        Poison probe = new Poison(1);
        System.out.println("Comparable keys : binIsSorted=" + tree.binIsSorted(probe)
                + ", binLength=" + tree.binLengthOf(probe) + ", get(Poison(7))=" + tree.get(new Poison(7)));
        System.out.println("sorted bin contents (first 8): " + firstN(tree, 8));

        MyHashMap<PoisonNC, Integer> chain = new MyHashMap<>(64, 0.75f);
        for (int i = 20; i >= 1; i--) chain.put(new PoisonNC(i), i);
        System.out.println("non-Comparable  : binIsSorted=" + chain.binIsSorted(new PoisonNC(1))
                + ", binLength=" + chain.binLengthOf(new PoisonNC(1))
                + ", get(PoisonNC(7))=" + chain.get(new PoisonNC(7)));
        System.out.println("comparableClassFor(\"s\")        = " + MyHashMap.comparableClassFor("s"));
        System.out.println("comparableClassFor(Poison(1))  = " + MyHashMap.comparableClassFor(new Poison(1)));
        System.out.println("comparableClassFor(PoisonNC(1))= " + MyHashMap.comparableClassFor(new PoisonNC(1)));

        section("6. sorted bin stays correct under removal");
        for (int i = 1; i <= 20; i += 2) tree.remove(new Poison(i));
        System.out.println("after removing the 10 odd keys: size=" + tree.size()
                + ", binLength=" + tree.binLengthOf(probe)
                + ", get(Poison(7))=" + tree.get(new Poison(7))
                + ", get(Poison(8))=" + tree.get(new Poison(8)));
```

Note in section 5 the explicit `new MyHashMap<>(64, 0.75f)`: capacity 64 is `MIN_TREEIFY_CAPACITY`, so the bin treeifies at the eighth key rather than provoking a resize. With the default capacity of 16, twenty colliding keys would resize the table three times before the bin was ever allowed to convert — and after those resizes the twenty keys would still all be in bin 0, because their hash is 0 and `0 & anything == 0`. Resizing does not help against a constant hash code, which is exactly why `treeifyBin` gives up on resizing at 64.

---

## 2. Sections 7 to 14 — the behaviours quoted in files 08, 09 and 10

```java
// Demo.java
        section("7. the four default methods and their null semantics");
        MyHashMap<String, Integer> d = new MyHashMap<>();
        d.put("keep", 1);
        d.put("nullv", null);
        System.out.println("computeIfAbsent(new, k -> 10)      -> " + d.computeIfAbsent("new", k -> 10));
        System.out.println("computeIfAbsent(new, k -> 99)      -> " + d.computeIfAbsent("new", k -> 99)
                + "   (present, function not called)");
        System.out.println("computeIfAbsent(skip, k -> null)   -> " + d.computeIfAbsent("skip", k -> null)
                + " ; containsKey(skip)=" + d.containsKey("skip") + "  (no entry inserted)");
        System.out.println("computeIfAbsent(nullv, k -> 7)     -> " + d.computeIfAbsent("nullv", k -> 7)
                + "   (null value counts as absent)");
        System.out.println("compute(keep, (k,v) -> null)       -> " + d.compute("keep", (k, v) -> null)
                + " ; containsKey(keep)=" + d.containsKey("keep") + "  (entry REMOVED)");
        System.out.println("merge(hits, 1, Integer::sum)       -> " + d.merge("hits", 1, Integer::sum));
        System.out.println("merge(hits, 1, Integer::sum)       -> " + d.merge("hits", 1, Integer::sum));
        System.out.println("merge(hits, 1, (a,b) -> null)      -> " + d.merge("hits", 1, (a, b) -> null)
                + " ; containsKey(hits)=" + d.containsKey("hits") + "  (entry REMOVED)");
        MyHashMap<String, Integer> pia = new MyHashMap<>();
        pia.put("x", null);
        System.out.println("putIfAbsent(x,5) with x->null      -> " + pia.putIfAbsent("x", 5)
                + " ; get(x)=" + pia.get("x") + "  (null value OVERWRITTEN)");
        pia.put("y", 1);
        System.out.println("putIfAbsent(y,5) with y->1         -> " + pia.putIfAbsent("y", 5)
                + " ; get(y)=" + pia.get("y") + "   (kept)");

        section("8. recursive computeIfAbsent is detected");
        MyHashMap<String, Integer> rec = new MyHashMap<>();
        try {
            rec.computeIfAbsent("outer", k -> {
                rec.put("inner", 1);
                return 2;
            });
            System.out.println("no exception -- detection FAILED");
        } catch (ConcurrentModificationException e) {
            System.out.println("caught " + e.getClass().getName() + " as expected");
        }
        System.out.println("map after the failed call: " + new java.util.TreeMap<>(rec));

        section("9. live views");
        MyHashMap<String, Integer> v = new MyHashMap<>();
        for (String k : List.of("a", "b", "c", "d")) v.put(k, k.charAt(0) - 'a');
        System.out.println("keySet   = " + v.keySet());
        System.out.println("values   = " + v.values());
        System.out.println("entrySet = " + v.entrySet());
        v.keySet().remove("a");
        System.out.println("after keySet().remove(\"a\")   : map=" + v + ", size=" + v.size());
        v.entrySet().removeIf(e -> e.getValue() == 2);
        System.out.println("after entrySet().removeIf(v==2): map=" + v);
        Iterator<Map.Entry<String, Integer>> it = v.entrySet().iterator();
        Map.Entry<String, Integer> e0 = it.next();
        e0.setValue(100);
        System.out.println("entry.setValue(100) writes through: map=" + v);
        it.remove();
        System.out.println("iterator.remove() : map=" + v + ", size=" + v.size());
        System.out.println("keySet.contains(b)=" + v.keySet().contains("b")
                + ", values.contains(3)=" + v.values().contains(3));

        section("10. fail-fast");
        MyHashMap<Integer, Integer> ff = new MyHashMap<>();
        for (int i = 0; i < 5; i++) ff.put(i, i);
        try {
            for (Integer k : ff.keySet()) {
                if (k == 2) ff.put(99, 99);
            }
            System.out.println("no exception -- fail-fast FAILED");
        } catch (ConcurrentModificationException ex) {
            System.out.println("structural put during iteration -> ConcurrentModificationException");
        }
        MyHashMap<Integer, Integer> ff2 = new MyHashMap<>();
        for (int i = 0; i < 5; i++) ff2.put(i, i);
        Iterator<Integer> safe = ff2.keySet().iterator();
        while (safe.hasNext()) if (safe.next() % 2 == 0) safe.remove();
        System.out.println("iterator.remove() during iteration is fine: " + ff2);

        section("11. MyHashSet");
        MyHashSet<String> set = new MyHashSet<>();
        System.out.println("add(x)   -> " + set.add("x"));
        System.out.println("add(x)   -> " + set.add("x"));
        System.out.println("add(y)   -> " + set.add("y"));
        System.out.println("contains(y)=" + set.contains("y") + ", size=" + set.size());
        System.out.println("remove(y)-> " + set.remove("y") + ", remove(z)-> " + set.remove("z"));
        System.out.println("set=" + set + ", equals(Set.of(\"x\"))=" + set.equals(java.util.Set.of("x")));
        MyHashSet<Integer> fromColl = new MyHashSet<>(List.of(3, 1, 2, 3, 1));
        System.out.println("new MyHashSet<>(List.of(3,1,2,3,1)) = " + fromColl);

        section("12. MyLinkedHashMap: insertion order");
        MyLinkedHashMap<String, Integer> lhm = new MyLinkedHashMap<>();
        for (String k : List.of("zebra", "apple", "mango", "kiwi", "fig")) lhm.put(k, k.length());
        System.out.println("MyLinkedHashMap  : " + lhm.keySet());
        System.out.println("java.util version: " + new LinkedHashMap<>(orderedPairs()).keySet());
        MyHashMap<String, Integer> plain = new MyHashMap<>();
        for (String k : List.of("zebra", "apple", "mango", "kiwi", "fig")) plain.put(k, k.length());
        System.out.println("MyHashMap        : " + plain.keySet() + "  (hash order, not insertion order)");
        lhm.put("apple", 99);
        System.out.println("re-put existing key does not reorder: " + lhm.keySet());
        lhm.remove("mango");
        System.out.println("after remove(mango): " + lhm.keySet());

        section("13. MyLinkedHashMap: access order");
        MyLinkedHashMap<String, Integer> ao = new MyLinkedHashMap<>(16, 0.75f, true);
        for (String k : List.of("a", "b", "c", "d")) ao.put(k, 1);
        System.out.println("initial      : " + ao.keySet());
        ao.get("a");
        System.out.println("after get(a) : " + ao.keySet());
        ao.get("c");
        System.out.println("after get(c) : " + ao.keySet());
        ao.put("b", 2);
        System.out.println("after put(b) : " + ao.keySet() + "  (put on an existing key also counts as access)");

        section("14. a working LRU cache");
        LruCache<String, String> lru = new LruCache<>(3);
        for (String k : List.of("k1", "k2", "k3")) lru.put(k, "v" + k);
        System.out.println("filled to capacity : " + lru.keySet());
        lru.get("k1");
        System.out.println("touch k1           : " + lru.keySet());
        lru.put("k4", "vk4");
        System.out.println("insert k4 (evicts) : " + lru.keySet() + ", size=" + lru.size());
        lru.put("k5", "vk5");
        System.out.println("insert k5 (evicts) : " + lru.keySet());
        System.out.println("get(k2) after evict: " + lru.get("k2"));
```

Section 12's `java.util version:` line is not decoration. It builds a real `java.util.LinkedHashMap` from the same five keys in the same order and prints its key set beside ours; if the overlay were wrong in any way that reordered entries, the two lines would differ and you would see it immediately.

---

## 3. The differential test

**Mental model.** Reading your own implementation to check it is correct is close to useless — you will read what you meant. A differential test does not read anything. It drives two implementations with the same random operation stream and asserts that they answer identically, on every single call. Any divergence, anywhere, in any code path the stream happens to reach, shows up as one boolean going false.

**Why it exists.** The behaviours quoted in files 06 through 10 are hand-picked: they demonstrate what the prose claims. Hand-picked examples cannot find the bug you did not think of. This test reaches paths nobody wrote an example for — a `merge` that removes the last entry in a bin that later resizes, a `remove` on a key that was never there, a `put` that replaces a value in a bin about to be treeified.

**When it is not enough.** It only exercises `Integer` keys, so it never reaches the `SortedBin` path (`Integer.hashCode()` is the value, and 3,000 distinct values across a 4,096-slot table give bins of length one or two). Sections 5 and 6 cover the sorted bin by construction, and [10b](10b-build-my-hash-map-g-diff-and-collision-dos.md) covers it under load. A complete job would add a `Poison`-keyed differential run; that is a real gap and it is stated as one.

**How it works.** A fixed seed (42) so the run is reproducible; a key space of 3,000 against 200,000 operations, so collisions, replacements and removals of live keys all happen constantly; four operations chosen uniformly. Every one of them **returns something**, and the return value is compared — not just the final state. Then three whole-map assertions at the end: `size`, `equals` both ways round via `AbstractMap.equals`, and an entry-set comparison through `java.util.HashSet`, which independently exercises `Node.hashCode()` and `Node.equals`.

```java
// Demo.java
        section("15. inherited from AbstractMap, not overridden");
        MyHashMap<String, Integer> x = new MyHashMap<>();
        x.put("a", 1);
        x.put("b", 2);
        MyHashMap<String, Integer> y = new MyHashMap<>();
        y.put("b", 2);
        y.put("a", 1);
        System.out.println("x.equals(y)   = " + x.equals(y) + "   (AbstractMap.equals, order independent)");
        System.out.println("x.hashCode()  = " + x.hashCode() + ", y.hashCode() = " + y.hashCode());
        System.out.println("x.equals(java.util.Map.of(\"a\",1,\"b\",2)) = " + x.equals(Map.of("a", 1, "b", 2)));
        System.out.println("toString      = " + x);
        MyHashMap<String, Integer> copy = new MyHashMap<>(Map.of("p", 1));
        copy.putAll(Map.of("q", 2));
        System.out.println("putAll        = " + new java.util.TreeMap<>(copy));

        section("16. agreement with java.util.HashMap over a randomised workload");
        java.util.Random rnd = new java.util.Random(42);
        MyHashMap<Integer, Integer> mine = new MyHashMap<>();
        java.util.HashMap<Integer, Integer> theirs = new java.util.HashMap<>();
        boolean agree = true;
        for (int i = 0; i < 200_000 && agree; i++) {
            int k = rnd.nextInt(3000);
            switch (rnd.nextInt(4)) {
                case 0 -> agree = eq(mine.put(k, i), theirs.put(k, i));
                case 1 -> agree = eq(mine.remove(k), theirs.remove(k));
                case 2 -> agree = eq(mine.get(k), theirs.get(k));
                default -> agree = eq(mine.merge(k, 1, Integer::sum), theirs.merge(k, 1, Integer::sum));
            }
            if (agree) agree = mine.size() == theirs.size();
        }
        System.out.println("200,000 mixed ops, seed 42, key space 3000");
        System.out.println("every return value and size agreed : " + agree);
        System.out.println("final size " + mine.size() + " ; maps equal : " + mine.equals(theirs));
        System.out.println("entrySet as a java.util.HashSet equal : "
                + new java.util.HashSet<>(mine.entrySet()).equals(new java.util.HashSet<>(theirs.entrySet())));
    }

    static boolean eq(Object a, Object b) {
        return java.util.Objects.equals(a, b);
    }

    static Map<String, Integer> orderedPairs() {
        LinkedHashMap<String, Integer> lm = new LinkedHashMap<>();
        for (String k : List.of("zebra", "apple", "mango", "kiwi", "fig")) lm.put(k, k.length());
        return lm;
    }

    static String binToString(MyHashMap<Integer, String> map, int index) {
        List<String> out = new ArrayList<>();
        for (MyHashMap.Node<Integer, String> e = map.table[index]; e != null; e = e.next) out.add(String.valueOf(e.key));
        return out.toString();
    }

    static String firstN(MyHashMap<Poison, Integer> map, int n) {
        List<Integer> out = new ArrayList<>();
        for (Poison p : map.keySet()) {
            out.add(p.id());
            if (out.size() == n) break;
        }
        return out.toString();
    }

    static void section(String title) {
        System.out.println();
        System.out.println("== " + title + " " + "=".repeat(Math.max(0, 66 - title.length())));
    }
}
```

Real output, sections 15 and 16 — the only two not already quoted in an earlier file:

```
x.equals(y)   = true   (AbstractMap.equals, order independent)
x.hashCode()  = 192, y.hashCode() = 192
x.equals(java.util.Map.of("a",1,"b",2)) = true
toString      = {a=1, b=2}
putAll        = {p=1, q=2}
```
```
200,000 mixed ops, seed 42, key space 3000
every return value and size agreed : true
final size 1999 ; maps equal : true
entrySet as a java.util.HashSet equal : true
```

The `agree` flag is also the loop's continuation condition, so the run stops at the first divergence rather than reporting only the last. A failure would leave `agree` false with the map state frozen at the failing operation.

**Pitfall:** `mine.equals(theirs)` alone would be a weak test. It compares final contents and says nothing about return values, so a `put` that returns the wrong previous value, or a `remove` that returns `null` when it should return a value, passes it every time. Comparing each call's return is what makes the test worth running.

**Insight:** `new java.util.HashSet<>(mine.entrySet())` is doing real work. It hashes every one of our `Node` objects with our `Node.hashCode()`, and compares them with our `Node.equals` against the JDK's own `Node` instances. If our `Map.Entry` contract implementation were wrong — say `hashCode` returned the cached spread hash instead of `keyHash ^ valueHash` — this line would fail while everything else passed.

**Interview:** *"How would you test a hash map you wrote?"* — Differential testing against `java.util.HashMap` over a randomised operation stream with a fixed seed, comparing every return value and not just the end state, plus targeted tests for the paths random `Integer` keys never reach: null keys, null values, collision-poisoned bins, and iteration during modification.

> **Definition.** A differential test drives a reference implementation and a candidate implementation with the same operation stream and asserts equality of every observable — return values, size, and final state — so that any divergence in any reached code path fails the run.

---

## Pitfalls

### Publishing output you did not re-generate after editing the code

**Wrong**

```
// note says: "prints [a, b, c]"
// code on the page was edited afterwards and now prints [a, c, b]
```

**Right**

```
javac -Xlint:all -d out *.java && java -cp out Demo | md5
# 4dd3a26f8346237a6d5929a8952b8a25 -- compare against the value printed above
```

**Why people do it:** the edit looks cosmetic. Reordering two `put` calls in a demo changes hash-order output; renaming a field changes nothing. You cannot tell which is which by eye, so re-run and compare the digest.

### Building into a shared or stale output directory

**Wrong**

```
javac MyHashMap.java          # writes .class next to the source, silently keeps old ones
java Demo                     # may run a MyHashMap.class from an earlier edit
```

**Right**

```
javac -Xlint:all -d out MyHashMap.java MyHashSet.java MyLinkedHashMap.java LruCache.java Demo.java Bench.java
java -cp out Demo
```

**Why people do it:** in-place compilation is the shortest command. A stale `.class` for a class you did not recompile produces numbers that do not match the code you are reading, and nothing warns you.

### Using the default `java` on a machine with several JDKs

**Wrong**

```
java -version        # GraalVM 25 -- different JIT, different constant folding, different timings
javac Demo.java      # may even target a different release
```

**Right**

```
export JAVA_HOME=$(/usr/libexec/java_home -v 21)
export PATH="$JAVA_HOME/bin:$PATH"
javac -version && java -version    # javac 21.0.7 / 21.0.7+8-LTS-245
```

**Why people do it:** `java -version` gets checked once, at setup, and then never again. Every timing in [10b](10b-build-my-hash-map-g-diff-and-collision-dos.md) depends on the JIT, so naming the exact build is part of the measurement, not paperwork.

---

## Cheat sheet

| Item | Value |
|---|---|
| Build | `javac -Xlint:all -d out MyHashMap.java MyHashSet.java MyLinkedHashMap.java LruCache.java Demo.java Bench.java` |
| Run | `java -cp out Demo` |
| Toolchain | `javac 21.0.7` / `java 21.0.7+8-LTS-245`, Apple M4 Pro, arm64 |
| Compile result | zero warnings, zero errors under `-Xlint:all` |
| Demo output md5 | `4dd3a26f8346237a6d5929a8952b8a25` |
| Source files | 6 — `MyHashMap`, `MyHashSet`, `MyLinkedHashMap`, `LruCache`, `Demo`, `Bench` |
| `Demo` sections | 16 |
| Differential test | 200,000 ops, seed 42, key space 3,000, four operations |
| Compared per call | the return value, then `size` |
| Compared at the end | `size`, `equals` both ways, `entrySet` via `java.util.HashSet` |
| Final size | 1,999 of a possible 3,000 keys |
| Not covered by it | `SortedBin` (Integer keys do not collide enough), null keys, iteration |
| Poisoned key types | `Poison` (passes the screen), `PoisonNC` (fails it) |
| Why capacity 64 in section 5 | equals `MIN_TREEIFY_CAPACITY`, so the bin treeifies rather than resizing |

---

## Self-test

**Q1.** The differential test uses `Integer` keys and never reaches the `SortedBin` code. Why not, and what covers it instead?

<details><summary>Answer</summary>

`Integer.hashCode()` returns the value itself, so 3,000 distinct keys spread across a table that grows to 4,096 slots give bins of length one or two — nowhere near the eight needed to treeify. Sections 5 and 6 of the demo cover the sorted bin directly, by using a key type whose `hashCode()` is constant, and [10b](10b-build-my-hash-map-g-diff-and-collision-dos.md) covers it under load. Adding a `Poison`-keyed differential run would be strictly better and is a stated gap.

</details>

**Q2.** Why compare the return value of every operation rather than just the final map contents?

<details><summary>Answer</summary>

Because the return values carry information the final state does not. `put` returns the previous value, `remove` returns the removed value, `merge` returns the new value — a bug in any of those leaves the map in the correct final state while lying to the caller on the way there. A test that only checks `mine.equals(theirs)` at the end passes for an implementation whose `put` always returns `null`.

</details>

**Q3.** Section 5 constructs `new MyHashMap<>(64, 0.75f)` rather than using the default. What would happen with the default, and why?

<details><summary>Answer</summary>

With capacity 16, the eighth colliding key would call `treeifyBin`, which sees `tab.length < MIN_TREEIFY_CAPACITY` and calls `resize()` instead of converting. That would repeat as the table doubled to 32 and then 64 — and the keys would still all be in bin 0, because their hash is 0 and `0 & (n-1) == 0` for every `n`. Only once capacity reaches 64 does the bin actually convert. Starting at 64 skips three pointless resizes and makes the demonstration about treeification rather than about growth.

</details>

**Q4.** What does `new java.util.HashSet<>(mine.entrySet())` test that the other assertions do not?

<details><summary>Answer</summary>

Our `Node`'s implementation of the `Map.Entry` contract. Building a `HashSet` from our entry set hashes each of our `Node` objects with our `Node.hashCode()` and compares them with our `Node.equals` against the JDK's `Node` instances in the other set. If `Node.hashCode()` returned the cached spread hash instead of `keyHash ^ valueHash`, or if `equals` did not accept a foreign `Map.Entry`, this line would fail while `mine.equals(theirs)` — which goes through `getNode`, not through entry hashing — still passed.

</details>

**Q5.** Why does the differential loop have `&& agree` in its continuation condition?

<details><summary>Answer</summary>

So it stops at the first divergence. Without it, the loop would run all 200,000 operations and `agree` would report only whether the *last* comparison failed — a bug on operation 12 followed by 199,988 agreeing operations would be invisible, or worse, would leave the two maps so far apart that the final `equals` failure gave no clue where it started. Failing fast keeps the map state frozen at the operation that broke, which is where you want to be standing when you attach a debugger.

</details>

**Q6.** Why record and publish an md5 of the demo output at all?

<details><summary>Answer</summary>

Because a reader typing the code out has no other way to know they got it right. Most transcription errors produce output that still looks plausible — a bin order differs, a size is off by one, a boolean flips — and comparing 118 lines by eye does not catch that. One digest does. It also enforces discipline on the writer: any edit to the published code changes the digest, so the digest cannot stay correct unless the output on the page was regenerated after the last edit.

</details>

---

**Leaves covered:** none new — this file is the runnable harness that produces the output quoted under leaves 4.3.1–4.3.12
**Leaves deferred:** none — 4.3.1–4.3.2 are in [06-build-my-hash-map.md](06-build-my-hash-map.md), 4.3.3 in [06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md](06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md), 4.3.4–4.3.6 in [07-build-my-hash-map-b-put-get-resize.md](07-build-my-hash-map-b-put-get-resize.md), 4.3.7–4.3.8 in [08-build-my-hash-map-c-treeify-and-defaults.md](08-build-my-hash-map-c-treeify-and-defaults.md), 4.3.9–4.3.10 in [09-build-my-hash-map-d-views-and-iterator.md](09-build-my-hash-map-d-views-and-iterator.md), 4.3.11–4.3.12 in [10-build-my-hash-map-e-set-linked-and-diff.md](10-build-my-hash-map-e-set-linked-and-diff.md), 4.3.13–4.3.14 in [10b-build-my-hash-map-g-diff-and-collision-dos.md](10b-build-my-hash-map-g-diff-and-collision-dos.md)
**Diagrams included:** none new — the `put` trace (D-146, frames a–d) is embedded in [06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md](06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md)
**Target version:** Java 21 LTS
**Lines:** 509
