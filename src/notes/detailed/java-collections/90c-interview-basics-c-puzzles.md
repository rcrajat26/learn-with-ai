# 02 Java Collections — Interview, BASICS tier — predict-the-output puzzles (§5.1)

**Target version: Java 21 LTS.** | [Index](00-index.md)
Previous: [90b-interview-basics-b-questions-19-36.md](90b-interview-basics-b-questions-19-36.md) · Next: [91-interview-intermediate.md](91-interview-intermediate.md)

Five puzzles at BASICS depth. Read each program, write down what you think it prints, **then**
open the answer. Guessing and being wrong is the point; recognising the shape later is the payoff.

**Every transcript on this page was produced by compiling and running the exact code shown.**
Toolchain: `javac`/`java` 21.0.7+8-LTS-245 (`/Library/Java/JavaVirtualMachines/jdk-21.jdk`),
Apple M4 Pro, arm64, `-Xlint:all`, zero warnings, zero errors. Where a line of output is not
specified by the JDK — `HashSet` iteration order is the only such case here — the puzzle says so
and the printed line is marked as one instance rather than as the guaranteed answer.

## Puzzle 1 — three sets, three orders (§5.1.33)

```java
// SetOrder.java

import java.util.*;

public class SetOrder {
    public static void main(String[] args) {
        List<String> input = List.of("delta", "alpha", "charlie", "bravo", "alpha");

        Set<String> hash = new HashSet<>(input);
        Set<String> linked = new LinkedHashSet<>(input);
        Set<String> tree = new TreeSet<>(input);

        System.out.println("sizes: " + hash.size() + " " + linked.size() + " " + tree.size());
        System.out.println("hash:   " + hash);
        System.out.println("linked: " + linked);
        System.out.println("tree:   " + tree);
        System.out.println("tree.first=" + ((TreeSet<String>) tree).first()
                + " tree.last=" + ((TreeSet<String>) tree).last());
        System.out.println("linked.getFirst=" + ((LinkedHashSet<String>) linked).getFirst());

        Set<String> nullHash = new HashSet<>();
        System.out.println("HashSet add(null): " + nullHash.add(null));
        try {
            new TreeSet<String>().add(null);
        } catch (NullPointerException e) {
            System.out.println("TreeSet add(null): NullPointerException");
        }
    }
}
```

<details><summary>Output and why</summary>

```
sizes: 4 4 4
hash:   [bravo, alpha, delta, charlie]
linked: [delta, alpha, charlie, bravo]
tree:   [alpha, bravo, charlie, delta]
tree.first=alpha tree.last=delta
linked.getFirst=delta
HashSet add(null): true
TreeSet add(null): NullPointerException
```

Four facts, one of which is not a guarantee.

**Sizes are all 4.** The input has five entries with `"alpha"` twice; every `Set` dedupes by
`equals`/`hashCode` — except `TreeSet`, which dedupes by `compare(...) == 0`. Here the two agree.

**`linked` is insertion order** — first-seen order, so the duplicate `"alpha"` keeps its original
position rather than moving to the end. Re-adding an existing element to a `LinkedHashSet` does not
reorder it.

**`tree` is sorted** by `String`'s natural order, which is UTF-16 code-unit order, not locale order.
For human-visible sorting you want `Collator.getInstance(locale)`.

**`hash` is the line that is not a guarantee.** `HashSet` iteration order is unspecified: the
javadoc says the class "makes no guarantees as to the iteration order". The invariant you may rely
on is only that it contains the same four elements. What the order actually *is* comes from
`hash & (capacity − 1)` per element and is deterministic for a given JDK build and key set — this
run printed `[bravo, alpha, delta, charlie]` in three consecutive JVM starts — but it changes on
resize, on a different key set, and potentially on a different JDK. Treat the printed line as one
instance, never as the answer, and never assert on it in a test.

**Nulls.** `HashSet` accepts one `null` (it is a `HashMap` key, and `null` hashes to 0).
`TreeSet.add(null)` throws even on an **empty** set under natural ordering, because the
implementation routes through `compare`.

**Java 21 detail:** `linked.getFirst()` works because `LinkedHashSet` implements `SequencedSet`.
The same call on a `HashSet` does not compile — `HashSet` is not sequenced, since it has no order to
be first in.

</details>

## Puzzle 2 — a stack that iterates backwards (§5.1.39)

```java
// StackOrder.java

import java.util.*;

public class StackOrder {
    public static void main(String[] args) {
        Stack<String> legacy = new Stack<>();
        Deque<String> deque = new ArrayDeque<>();
        LinkedList<String> linked = new LinkedList<>();

        for (String s : List.of("a", "b", "c")) {
            legacy.push(s);
            deque.push(s);
            linked.push(s);
        }

        System.out.println("Stack       toString: " + legacy);
        System.out.println("ArrayDeque  toString: " + deque);
        System.out.println("LinkedList  toString: " + linked);

        System.out.println("Stack       for-each: " + join(legacy));
        System.out.println("ArrayDeque  for-each: " + join(deque));
        System.out.println("LinkedList  for-each: " + join(linked));

        System.out.println("Stack.search(\"c\") = " + legacy.search("c"));
        System.out.println("Stack.search(\"a\") = " + legacy.search("a"));
        System.out.println("Stack.search(\"zz\") = " + legacy.search("zz"));
        System.out.println("pop order:  " + legacy.pop() + deque.pop() + linked.pop());

        try {
            deque.push(null);
        } catch (NullPointerException e) {
            System.out.println("ArrayDeque.push(null): NullPointerException");
        }
        linked.push(null);
        System.out.println("LinkedList.push(null) accepted, size=" + linked.size());
    }

    static String join(Collection<String> c) {
        StringJoiner j = new StringJoiner(" ");
        for (String s : c) {
            j.add(s);
        }
        return j.toString();
    }
}
```

<details><summary>Output and why</summary>

```
Stack       toString: [a, b, c]
ArrayDeque  toString: [c, b, a]
LinkedList  toString: [c, b, a]
Stack       for-each: a b c
ArrayDeque  for-each: c b a
LinkedList  for-each: c b a
Stack.search("c") = 1
Stack.search("a") = 3
Stack.search("zz") = -1
pop order:  ccc
ArrayDeque.push(null): NullPointerException
LinkedList.push(null) accepted, size=3
```

**All three pop `c` first** — they agree about what a stack *is*. They disagree about what
iterating one means.

`java.util.Stack` extends `Vector`, so its iteration is the `List`'s: index 0 upward, which is
**bottom-to-top** — the reverse of pop order. `ArrayDeque.push` is `addFirst`, and its iteration
runs from `head`, so it is **top-to-bottom**, matching pop order. `LinkedList.push` is also
`addFirst`, same result. This is the single strongest reason to prefer `ArrayDeque` for a stack: the
`for`-each order is the one you meant.

**`Stack.search` is 1-based from the top,** not 0-based, and returns `-1` on a miss. The top
element is at distance 1. Nobody guesses this correctly; it is a 1.0-era signature.

**Nulls.** `ArrayDeque` rejects `null` because `null` is its free-slot marker. `LinkedList`
accepts it, which is the one remaining reason to choose `LinkedList` as a deque. Note the final
size is 3: `linked` had `[c, b, a]`, `pop()` removed `c` leaving 2, then `push(null)` brought it
back to 3.

</details>

## Puzzle 3 — five ways to remove during iteration (§5.1.43)

```java
// RemoveWhileIterating.java

import java.util.*;
import java.util.concurrent.*;

public class RemoveWhileIterating {
    public static void main(String[] args) {
        // A: remove a middle element through the list, inside a for-each
        List<String> a = new ArrayList<>(List.of("a", "b", "c", "d"));
        try {
            for (String s : a) {
                if (s.equals("b")) {
                    a.remove(s);
                }
            }
            System.out.println("A: no exception, list=" + a);
        } catch (ConcurrentModificationException e) {
            System.out.println("A: ConcurrentModificationException, list=" + a);
        }

        // B: remove the SECOND-TO-LAST element through the list
        List<String> b = new ArrayList<>(List.of("a", "b", "c", "d"));
        List<String> seenB = new ArrayList<>();
        try {
            for (String s : b) {
                seenB.add(s);
                if (s.equals("c")) {
                    b.remove(s);
                }
            }
            System.out.println("B: no exception, visited=" + seenB + " list=" + b);
        } catch (ConcurrentModificationException e) {
            System.out.println("B: ConcurrentModificationException, visited=" + seenB);
        }

        // C: remove through the iterator
        List<String> c = new ArrayList<>(List.of("a", "b", "c", "d"));
        for (Iterator<String> it = c.iterator(); it.hasNext(); ) {
            if (it.next().equals("b")) {
                it.remove();
            }
        }
        System.out.println("C: iterator remove, list=" + c);

        // D: the same mutation on a ConcurrentHashMap's key set
        Map<String, Integer> d = new ConcurrentHashMap<>();
        d.put("a", 1);
        d.put("b", 2);
        d.put("c", 3);
        for (String k : d.keySet()) {
            if (k.equals("b")) {
                d.remove(k);
            }
        }
        System.out.println("D: CHM weakly consistent, size=" + d.size());

        // E: the same mutation on a CopyOnWriteArrayList
        List<String> e = new CopyOnWriteArrayList<>(List.of("a", "b", "c", "d"));
        List<String> seenE = new ArrayList<>();
        for (String s : e) {
            seenE.add(s);
            if (s.equals("b")) {
                e.remove(s);
            }
        }
        System.out.println("E: COW snapshot, visited=" + seenE + " list=" + e);
        try {
            Iterator<String> it = e.iterator();
            it.next();
            it.remove();
        } catch (UnsupportedOperationException ex) {
            System.out.println("E: COWIterator.remove -> UnsupportedOperationException");
        }
    }
}
```

<details><summary>Output and why</summary>

```
A: ConcurrentModificationException, list=[a, c, d]
B: no exception, visited=[a, b, c] list=[a, b, d]
C: iterator remove, list=[a, c, d]
D: CHM weakly consistent, size=2
E: COW snapshot, visited=[a, b, c, d] list=[a, c, d]
E: COWIterator.remove -> UnsupportedOperationException
```

**A is the case everyone knows.** The removal bumped `modCount`; the next `next()` compared it
against the snapshot and threw. Note that the removal itself **succeeded** — the list is
`[a, c, d]`. CME is not a rollback.

**B is the case that matters, and it prints no exception.** Removing the second-to-last element
means `size` drops from 4 to 3 exactly when `cursor` has advanced to 3, and `hasNext()` is
`cursor != size`, so the loop exits believing it is done. `"d"` is never visited — `visited=[a, b, c]`
— and nothing is reported. This is why the javadoc calls fail-fast best-effort: the loud failure is
the lucky one.

**C is the fix.** `it.remove()` performs the removal and then resynchronises `expectedModCount`, so
the iterator's own mutation is never mistaken for someone else's.

**D never throws at all.** `ConcurrentHashMap`'s iterators are weakly consistent: they walk live
state, may or may not observe concurrent writes, and have no `modCount`. The map ends at size 2, as
intended. This is the JDK's own answer to "how do I mutate while iterating" — change the
collection, not the loop.

**E is a snapshot.** `CopyOnWriteArrayList`'s iterator captured the four-element array at creation,
so the loop still visits `"d"` even though `"b"` was removed mid-flight — `visited` has all four
while the list ends at `[a, c, d]`. And its `remove()` throws `UnsupportedOperationException`
unconditionally: there is no code path where it succeeds, because the snapshot is not the list.

</details>

## Puzzle 4 — "unmodifiable" is not "immutable" (§5.1.48)

```java
// Unmodifiable.java

import java.util.*;

public class Unmodifiable {
    public static void main(String[] args) {
        List<StringBuilder> source = new ArrayList<>();
        source.add(new StringBuilder("one"));
        source.add(new StringBuilder("two"));

        List<StringBuilder> view = Collections.unmodifiableList(source);
        List<StringBuilder> copy = List.copyOf(source);

        System.out.println("view  before: " + view);
        System.out.println("copy  before: " + copy);

        source.add(new StringBuilder("three"));       // structural change to the backing list
        System.out.println("view  after add: " + view);
        System.out.println("copy  after add: " + copy);

        source.get(0).append("!");                     // mutating an ELEMENT, not the list
        System.out.println("view  after element mutate: " + view);
        System.out.println("copy  after element mutate: " + copy);

        try {
            view.add(new StringBuilder("four"));
        } catch (UnsupportedOperationException e) {
            System.out.println("view.add -> UnsupportedOperationException");
        }
        try {
            copy.set(0, new StringBuilder("x"));
        } catch (UnsupportedOperationException e) {
            System.out.println("copy.set -> UnsupportedOperationException");
        }

        System.out.println("view.getClass()  = " + view.getClass().getName());
        System.out.println("copy.getClass()  = " + copy.getClass().getName());
        System.out.println("Collections.emptyList() == List.of() ? "
                + (Collections.emptyList() == List.of()));
        Collections.emptyList().clear();
        System.out.println("Collections.emptyList().clear() succeeded");
        try {
            List.of().clear();
        } catch (UnsupportedOperationException e) {
            System.out.println("List.of().clear() -> UnsupportedOperationException");
        }
    }
}
```

<details><summary>Output and why</summary>

```
view  before: [one, two]
copy  before: [one, two]
view  after add: [one, two, three]
copy  after add: [one, two]
view  after element mutate: [one!, two, three]
copy  after element mutate: [one!, two]
view.add -> UnsupportedOperationException
copy.set -> UnsupportedOperationException
view.getClass()  = java.util.Collections$UnmodifiableRandomAccessList
copy.getClass()  = java.util.ImmutableCollections$List12
Collections.emptyList() == List.of() ? false
Collections.emptyList().clear() succeeded
List.of().clear() -> UnsupportedOperationException
```

**The wrapper grew from two elements to three without anyone touching it.**
`Collections.unmodifiableList` is a *view*: `get(i)` forwards to `list.get(i)`, so every change the
owner of `source` makes is visible through it. It blocks your writes, not theirs. If you return one
of these from a getter, you have handed the caller something that can change during their own
iteration — throwing CME in *their* code.

**`List.copyOf` is a snapshot**, so it stayed at two elements. Note the class: `List12`, the
two-element specialisation with fields `e0` and `e1` and no backing array at all, 24 bytes total.

**Both are shallow, and this is the deeper lesson.** After `source.get(0).append("!")` both the
view *and* the immutable copy print `one!`. Neither factory copies the elements; both freeze which
objects are in which slot. There is no deep-copy factory anywhere in `java.util` — the only route
to deep immutability is an immutable element type.

**The last three lines are a separate trap.** `Collections.emptyList()` and `List.of()` are both
shared, allocation-free empty singletons, and they are **different objects** — `==` is `false`,
though `equals` is `true`. Their mutator contracts differ too: the legacy `emptyList()` overrides
`clear` (and `removeIf`, `replaceAll`, `sort`) as silent no-ops, while `List.of().clear()` throws.
Same emptiness, opposite contracts.

</details>

## Puzzle 5 — the `remove` overload, and boxed identity

```java
// RemoveOverload.java

import java.util.*;

public class RemoveOverload {
    public static void main(String[] args) {
        List<Integer> a = new ArrayList<>(List.of(10, 20, 30, 40));
        a.remove(1);
        System.out.println("a.remove(1)               -> " + a);

        List<Integer> b = new ArrayList<>(List.of(10, 20, 30, 40));
        b.remove(Integer.valueOf(1));
        System.out.println("b.remove(Integer.valueOf(1)) -> " + b);

        List<Integer> c = new ArrayList<>(List.of(10, 20, 30, 40));
        c.remove(Integer.valueOf(20));
        System.out.println("c.remove(Integer.valueOf(20)) -> " + c);

        Collection<Integer> d = new ArrayList<>(List.of(10, 20, 30, 40));
        d.remove(1);
        System.out.println("Collection-typed d.remove(1)  -> " + d);

        List<Integer> e = new ArrayList<>(List.of(10, 20, 30, 40));
        try {
            e.remove(9);
        } catch (IndexOutOfBoundsException ex) {
            System.out.println("e.remove(9) -> IndexOutOfBoundsException: " + ex.getMessage());
        }

        Integer boxedSmall1 = 127, boxedSmall2 = 127;
        Integer boxedBig1 = 128, boxedBig2 = 128;
        System.out.println("127 == 127 (boxed): " + (boxedSmall1 == boxedSmall2));
        System.out.println("128 == 128 (boxed): " + (boxedBig1 == boxedBig2));

        Map<Integer, String> m = new HashMap<>();
        m.put(1, "one");
        System.out.println("m.get(1L) = " + m.get(1L));
    }
}
```

<details><summary>Output and why</summary>

```
a.remove(1)               -> [10, 30, 40]
b.remove(Integer.valueOf(1)) -> [10, 20, 30, 40]
c.remove(Integer.valueOf(20)) -> [10, 30, 40]
Collection-typed d.remove(1)  -> [10, 20, 30, 40]
e.remove(9) -> IndexOutOfBoundsException: Index 9 out of bounds for length 4
127 == 127 (boxed): true
128 == 128 (boxed): false
m.get(1L) = null
```

**`List` has two `remove` methods and overload resolution picks by static type, not by intent.**
`remove(int)` deletes *by index*; `remove(Object)` deletes *by value*. A literal `1` is an `int`, so
`a.remove(1)` removes index 1 — the element `20`. Boxing it explicitly selects the other overload,
which looks for the element `1` and finds nothing.

**The reference-typed line is the one that catches experienced people.** `Collection` declares only
`remove(Object)`, so with `d` declared as `Collection<Integer>` the literal `1` is *autoboxed* and
the call becomes remove-by-value — the opposite of what the identical source line does on a
`List`-typed variable. Same expression, different meaning, decided by the declared type.

**And index removal validates the index:** `e.remove(9)` throws
`IndexOutOfBoundsException: Index 9 out of bounds for length 4`, whereas remove-by-value would have
returned `false` quietly.

**The boxed comparisons** show `Integer.valueOf`'s cache: `−128..127` returns shared instances, so
`==` accidentally works there and fails at 128. This is exactly why `equals` is the only correct
comparison for boxed types, and why `==` bugs in this area survive testing.

**The last line** is the same family of bug one level up: `m.get(1L)` passes a `Long`, and
`Long.valueOf(1).equals(Integer.valueOf(1))` is `false` because `equals` checks the class. So the
lookup misses, silently, with no compiler warning — `Map.get` takes `Object`. Watch for it whenever
a map is keyed by a numeric type and the call site does arithmetic.

</details>

## Pitfalls

### Asserting on `HashSet` or `HashMap` iteration order in a test

**Wrong**

```java
Set<String> tags = new HashSet<>(List.of("b", "a", "c"));
assertEquals("[b, a, c]", tags.toString());   // passes today, fails on a JDK upgrade
```

**Right**

```java
Set<String> tags = new HashSet<>(List.of("b", "a", "c"));
assertEquals(Set.of("a", "b", "c"), tags);                       // order-free
assertEquals(List.of("a", "b", "c"), tags.stream().sorted().toList());  // or impose an order
```

**Why people believe it:** the order *is* deterministic for a fixed JDK build and key set, so the
test passes locally and in CI for years. It is not specified, and it changes on resize, on a
different element set, and across JDK versions. The immutable factories go further and randomise
order per JVM run deliberately, precisely to break code that came to depend on it.

### Calling `list.remove(someInt)` on a `List<Integer>`

**Wrong**

```java
List<Integer> ids = new ArrayList<>(List.of(100, 200, 300));
int idToDrop = 200;
ids.remove(idToDrop);          // IndexOutOfBoundsException at runtime
```

**Right**

```java
List<Integer> ids = new ArrayList<>(List.of(100, 200, 300));
int idToDrop = 200;
ids.remove(Integer.valueOf(idToDrop));   // or ids.remove((Integer) idToDrop)
```

**Why people believe it:** the code reads as remove-by-value and compiles without a warning. With
small values it silently removes the wrong element instead of throwing, which is worse.

## Cheat sheet

| Puzzle shape | What it prints | The rule |
|---|---|---|
| `HashSet` `toString` | unspecified order (stable per JDK build) | never assert on it |
| `LinkedHashSet` `toString` | first-seen insertion order | re-adding does not reorder |
| `TreeSet` `toString` | sorted by comparator, UTF-16 for `String` | dedupes by `compare == 0` |
| `TreeSet.add(null)` | NPE even when empty | natural ordering routes through `compare` |
| `Stack` for-each | bottom-to-top | opposite of pop order |
| `ArrayDeque`-as-stack for-each | top-to-bottom | matches pop order |
| `Stack.search(top)` | `1` | 1-based from the top, `-1` on a miss |
| `ArrayDeque.push(null)` | NPE | `null` is the free-slot marker |
| for-each + `list.remove(middle)` | CME, and the removal still happened | CME is detection, not rollback |
| for-each + `list.remove(second-to-last)` | **no exception**, last element skipped | `hasNext()` is `cursor != size` |
| for-each + `it.remove()` | works | resyncs `expectedModCount` |
| for-each over `ConcurrentHashMap` + `remove` | works, never throws | weakly consistent |
| for-each over `CopyOnWriteArrayList` + `remove` | visits the old snapshot | frozen array; `it.remove()` always throws |
| `unmodifiableList(src)` after `src.add` | grew | live view |
| `List.copyOf(src)` after `src.add` | unchanged | snapshot |
| either, after mutating an element | changed | both are shallow |
| `Collections.emptyList() == List.of()` | `false` | different singletons |
| `emptyList().clear()` / `List.of().clear()` | succeeds / throws | opposite mutator contracts |
| `list.remove(1)` on `List<Integer>` | removes **index** 1 | `remove(int)` wins on a `List` |
| same line on a `Collection<Integer>` | removes **value** 1 | only `remove(Object)` exists |
| `Integer` `==` at 127 / 128 | `true` / `false` | `valueOf` cache is `−128..127` |
| `map.get(1L)` on `Map<Integer,String>` | `null` | `Long.equals(Integer)` is `false` |

## Self-test

**Q1.** In puzzle 3 case A, the exception was thrown — was the element removed?

<details><summary>Answer</summary>

Yes. The list printed `[a, c, d]`. The removal completed and bumped `modCount`; the exception came
later, from the *iterator*, when it noticed the count had changed. `ConcurrentModificationException`
is a report that a mutation happened outside the iterator, not a rollback of it. The same applies
to `removeIf` and `forEach`: the exception arrives after the side effects have already run.

</details>

**Q2.** Change puzzle 3 case B to remove `"b"` instead of `"c"`. Does it still exit silently?

<details><summary>Answer</summary>

No — it throws, exactly like case A. The silent case needs the removed element to be the
second-to-last, so that the decremented `size` and the incremented `cursor` meet on the same value
and `hasNext()` returns `false` before the next `modCount` check. Remove anything earlier and there
is at least one more `next()` call to detect the change. That fragility is the whole point: the
behaviour depends on *which* element you removed, which is why fail-fast is documented as
best-effort.

</details>

**Q3.** Why does `List.copyOf(source)` in puzzle 4 print `List12` rather than `ListN`?

<details><summary>Answer</summary>

Because `source` had exactly two elements at the moment of the copy. The immutable list family
specialises small sizes: 0 elements is the shared `EMPTY_LIST`, 1 or 2 elements is `List12` with
fields `e0` and `e1` and no array at all, and 3 or more is `ListN` with an `Object[]`. `List12`'s
`size()` is `e1 != EMPTY ? 2 : 1`, comparing against a private sentinel object rather than `null`,
so that HotSpot can constant-fold the `@Stable` fields. One `List12` is 24 bytes; the equivalent
`new ArrayList<>(List.of(a, b))` is 48.

</details>

**Q4.** A test asserts `assertEquals(Set.of("a","b","c").toString(), someSet.toString())`. Why is
this worse than asserting on a `HashSet`'s order?

<details><summary>Answer</summary>

Because `Set.of` iteration order is randomised **per JVM run**, not merely unspecified. The
`ImmutableCollections` class initialises a `SALT32L` value from `System.nanoTime()` at class load,
and the `SetN`/`MapN` iterators use it to pick a starting slot and a direction. So the assertion
does not fail consistently — it fails on some runs and passes on others, which is far harder to
diagnose than a stable wrong answer. The salt affects iteration only; `probe()` placement and
lookup are unsalted and fully deterministic.

</details>

**Q5.** You are handed `List<String> config` from a library and told not to modify it. How do you
find out in one line whether it is a view, a fixed-size array wrapper, or immutable?

<details><summary>Answer</summary>

Print `config.getClass().getName()`. `java.util.Collections$UnmodifiableRandomAccessList` (or
`$UnmodifiableList`) is a live view over someone else's list.
`java.util.Arrays$ArrayList` is a fixed-size write-through wrapper around an array — `set` will
succeed. `java.util.ImmutableCollections$List12` or `$ListN` is genuinely immutable, and `$ListN`
may additionally permit nulls if it came from `Stream.toList()`. If you need a guarantee regardless
of what you were handed, take `List.copyOf(config)` — it is a no-op returning the same instance when
the argument is already a null-free immutable list.

</details>

---

**Leaves covered:** 5.1.33, 5.1.39, 5.1.43, 5.1.48 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 616
