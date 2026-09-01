# 02 Java Collections — Code-reading drills and the revision schedule (§5.3)

**Target version: Java 21 LTS.** | [Index](00-index.md)
Previous: [93b-drills.md](93b-drills.md)

The last file in the set. Five code-reading drills — say what each snippet prints, and why it is not
what it looks like — and then the schedule that turns all of this into recall rather than
recognition.

**Every transcript below was produced by compiling and running the exact code shown.** Toolchain:
`javac`/`java` 21.0.7+8-LTS-245 (`/Library/Java/JavaVirtualMachines/jdk-21.jdk`), Apple M4 Pro,
arm64, `javac -Xlint:all`, zero warnings, zero errors, no flags needed at run time. Every line is
deterministic across runs — nothing here prints an identity hash, a salted iteration order or a
wall-clock figure.

## §5.3.6 The code-reading drills

Read each program, commit to an answer, and only then open the transcript. The point of the drill is
the *gap* between what you predicted and what it prints — that gap is the thing you will still
remember in a month.

### Drill 1 — a comparator that redefines identity

```java
// Drill1.java

import java.util.*;

public class Drill1 {
    public static void main(String[] args) {
        Set<String> ci = new TreeSet<>(String.CASE_INSENSITIVE_ORDER);
        ci.add("Key");
        ci.add("KEY");
        ci.add("key");
        System.out.println("size          = " + ci.size());
        System.out.println("contents      = " + ci);
        System.out.println("contains(key) = " + ci.contains("key"));

        Set<String> hs = new HashSet<>(List.of("Key", "KEY", "key"));
        System.out.println("HashSet size  = " + hs.size());
        System.out.println("ci.equals(hs) = " + ci.equals(hs));
        System.out.println("hs.equals(ci) = " + hs.equals(ci));

        System.out.println("---");
        Set<java.math.BigDecimal> tree = new TreeSet<>();
        tree.add(new java.math.BigDecimal("2.0"));
        tree.add(new java.math.BigDecimal("2.00"));
        Set<java.math.BigDecimal> hash = new HashSet<>();
        hash.add(new java.math.BigDecimal("2.0"));
        hash.add(new java.math.BigDecimal("2.00"));
        System.out.println("TreeSet<BigDecimal> size = " + tree.size() + " -> " + tree);
        System.out.println("HashSet<BigDecimal> size = " + hash.size());
        System.out.println("compareTo == 0 ? " + (new java.math.BigDecimal("2.0")
                .compareTo(new java.math.BigDecimal("2.00")) == 0)
                + " ; equals ? " + new java.math.BigDecimal("2.0")
                .equals(new java.math.BigDecimal("2.00")));
    }
}
```

<details><summary>Output and why</summary>

```
size          = 1
contents      = [Key]
contains(key) = true
HashSet size  = 3
ci.equals(hs) = false
hs.equals(ci) = false
---
TreeSet<BigDecimal> size = 1 -> [2.0]
HashSet<BigDecimal> size = 2
compareTo == 0 ? true ; equals ? false
```

**The `TreeSet` holds one element and the `HashSet` holds three, from the same three strings.**
`TreeSet` decides membership with `compare(a, b) == 0`, and a case-insensitive comparator says all
three are the same element — so the second and third `add` return `false` and the survivor is
whichever arrived **first**, `"Key"`. A `HashSet` uses `equals`, and the three strings are not
`equals`.

**Both `equals` comparisons are `false`**, and for a reason worth stating: `AbstractSet.equals`
requires the same size before it compares anything, so 1 against 3 fails immediately in both
directions. This is a comparator inconsistent with `equals`, and the visible consequence is that
`contains` and `equals` answer different questions — `ci.contains("key")` is `true` even though no
element `equals` `"key"`.

**The `BigDecimal` block is the same trap in the JDK's own types**, which is why it is the standard
example. `new BigDecimal("2.0").compareTo(new BigDecimal("2.00")) == 0` while `equals` is `false`,
because `equals` compares scale. So a `TreeSet` keeps one and a `HashSet` keeps two, from identical
input, and neither is a bug.

**The rule to take away:** in a `TreeMap`/`TreeSet`, the comparator *is* the definition of key
identity. If it disagrees with `equals`, every `contains`/`equals`/`size` question needs you to know
which mechanism is answering it.

</details>

### Drill 2 — three ways to poison a view

```java
// Drill2.java

import java.util.*;

public class Drill2 {
    public static void main(String[] args) {
        List<String> parent = new ArrayList<>(List.of("a", "b", "c", "d", "e", "f"));
        List<String> window = parent.subList(1, 4);
        System.out.println("window            = " + window);

        window.set(0, "B");
        System.out.println("after window.set  parent=" + parent);

        parent.set(5, "F");
        System.out.println("after parent.set  window=" + window + "  (set is not structural)");

        window.clear();
        System.out.println("after window.clear parent=" + parent + " window=" + window);

        List<String> again = parent.subList(0, 2);
        parent.add("g");
        try {
            System.out.println(again.get(0));
        } catch (ConcurrentModificationException e) {
            System.out.println("stale view read  -> ConcurrentModificationException");
        }

        List<String> sorted = new ArrayList<>(List.of("c", "a", "b"));
        Iterator<String> it = sorted.iterator();
        sorted.sort(Comparator.naturalOrder());
        try {
            it.next();
        } catch (ConcurrentModificationException e) {
            System.out.println("iterator across sort -> ConcurrentModificationException");
        }
        System.out.println("sorted            = " + sorted);
    }
}
```

<details><summary>Output and why</summary>

```
window            = [b, c, d]
after window.set  parent=[a, B, c, d, e, f]
after parent.set  window=[B, c, d]  (set is not structural)
after window.clear parent=[a, e, F] window=[]
stale view read  -> ConcurrentModificationException
iterator across sort -> ConcurrentModificationException
sorted            = [a, b, c]
```

Four behaviours, and the interesting part is which mutations are tolerated.

**`window.set(0, "B")` writes through to the parent** — a view is a window, not a copy, so
`parent` becomes `[a, B, c, d, e, f]`.

**`parent.set(5, "F")` does not poison the view**, and the view reads the new value. `set` is not a
*structural* modification, so `modCount` does not move and the sublist's check still passes. People
expect any parent write to invalidate the view; only size-changing ones do.

**`window.clear()` is a range delete.** It removes `[1, 4)` from the parent in one
`System.arraycopy`, leaving `[a, e, F]` — and this is the only public route to `removeRange`, which is
`protected`. Note the view is now empty but still valid.

**`parent.add("g")` poisons the second view**, and the exception arrives on the *next read* of the
view, not at the moment of the mutation. The check is against the **root**'s `modCount`, so mutating
a grandparent invalidates a nested sublist too.

**And `sort` is structural.** An iterator taken before `sorted.sort(...)` throws on its next `next()`,
because `ArrayList.sort` bumps `modCount` even though the size never changed. The same is true of
`replaceAll`. That is the one that catches people in a "sort then continue processing" loop.

</details>

### Drill 3 — a set with two equal elements

```java
// Drill3.java

import java.util.*;

public class Drill3 {

    static final class Tag {
        String name;

        Tag(String name) {
            this.name = name;
        }

        @Override
        public boolean equals(Object o) {
            return o instanceof Tag t && t.name.equals(name);
        }

        @Override
        public int hashCode() {
            return name.hashCode();
        }

        @Override
        public String toString() {
            return "Tag(" + name + ")";
        }
    }

    public static void main(String[] args) {
        Set<Tag> tags = new HashSet<>();
        Tag t = new Tag("alpha");
        tags.add(t);
        System.out.println("contains before = " + tags.contains(t));

        t.name = "beta";                       // mutate a hashed field
        System.out.println("contains after  = " + tags.contains(t));
        System.out.println("remove          = " + tags.remove(t));
        System.out.println("size            = " + tags.size());
        System.out.println("iteration       = " + tags);
        System.out.println("contains a fresh equal Tag(beta) = " + tags.contains(new Tag("beta")));

        tags.add(new Tag("beta"));
        System.out.println("after adding an equal element, size = " + tags.size());
        System.out.println("iteration       = " + sortedByName(tags));

        Set<Tag> rebuilt = new HashSet<>(tags);
        System.out.println("rebuilt size    = " + rebuilt.size() + " (rehashed on copy)");
        System.out.println("rebuilt contains Tag(beta) = " + rebuilt.contains(new Tag("beta")));
    }

    static List<String> sortedByName(Collection<Tag> c) {
        List<String> names = new ArrayList<>();
        for (Tag tag : c) {
            names.add(tag.name);
        }
        names.sort(Comparator.naturalOrder());
        return names;
    }
}
```

<details><summary>Output and why</summary>

```
contains before = true
contains after  = false
remove          = false
size            = 1
iteration       = [Tag(beta)]
contains a fresh equal Tag(beta) = false
after adding an equal element, size = 2
iteration       = [beta, beta]
rebuilt size    = 1 (rehashed on copy)
rebuilt contains Tag(beta) = true
```

**A `HashSet` containing two elements that are `equals` to each other.** That is the line to sit
with, because it should be impossible.

The mechanism: `HashSet` is a `HashMap`, and the element's bin was chosen from its hash **at
insertion time** and cached in a `final int`. Mutating `name` changed what `hashCode()` returns, so
every subsequent lookup computes a different bin and finds nothing — `contains` is `false`, `remove`
is `false`, even with the *same reference*, because the bin walk starts from the wrong slot and never
reaches the node.

So the original element is **unreachable by key and fully alive**: `size()` is 1 and iteration prints
`Tag(beta)`. Then `add(new Tag("beta"))` hashes to the *correct* bin for `"beta"`, finds nothing
there, and inserts — giving a set of size 2 whose two elements are `equals`.

**The last two lines are the diagnostic worth remembering.** Copying the set into a new `HashSet`
rehashes every element under its *current* state, so the duplicate collapses and `size` drops from 2
to 1. If a set's size falls when you copy it, you have found a mutated key.

**Note that `contains` failed even for the identical reference.** The bin walk does compare
`(k = e.key) == key` before `equals` — but it only reaches that comparison for nodes in the bin the
*current* hash selects, and the node is not in that bin. This is why the unit test that holds one
object and never mutates it passes forever.

</details>

### Drill 4 — five ways `Collectors` will surprise you

```java
// Drill4.java

import java.util.*;
import java.util.stream.*;

public class Drill4 {

    record Person(String name, String city, Integer age) {}

    public static void main(String[] args) {
        List<Person> people = List.of(
                new Person("ana", "lisbon", 34),
                new Person("bo", "porto", 29),
                new Person("cy", "lisbon", 41),
                new Person("ana", "faro", 50));

        try {
            people.stream().collect(Collectors.toMap(Person::name, Person::age));
        } catch (IllegalStateException e) {
            System.out.println("toMap duplicate key -> IllegalStateException: " + e.getMessage());
        }

        Map<String, Integer> merged = people.stream()
                .collect(Collectors.toMap(Person::name, Person::age, Integer::sum, LinkedHashMap::new));
        System.out.println("with merge + LinkedHashMap = " + merged);
        System.out.println("class                      = " + merged.getClass().getSimpleName());

        List<Person> withNull = new ArrayList<>(people);
        withNull.add(new Person("dee", "braga", null));
        try {
            withNull.stream().collect(Collectors.toMap(Person::name, Person::age, Integer::sum));
        } catch (NullPointerException e) {
            System.out.println("toMap null value    -> NullPointerException");
        }
        Map<String, List<Integer>> grouped = withNull.stream()
                .collect(Collectors.groupingBy(Person::city,
                        TreeMap::new,
                        Collectors.mapping(Person::age, Collectors.toList())));
        System.out.println("groupingBy tolerates a null VALUE = " + grouped);

        Map<String, Long> counts = people.stream()
                .collect(Collectors.groupingBy(Person::city, TreeMap::new, Collectors.counting()));
        System.out.println("counting            = " + counts);

        List<Integer> collected = people.stream().map(Person::age).collect(Collectors.toList());
        List<Integer> streamed = people.stream().map(Person::age).toList();
        System.out.println("collect(toList) class = " + collected.getClass().getName());
        System.out.println("Stream.toList  class  = " + streamed.getClass().getName());
        collected.add(99);
        System.out.println("collect(toList) is mutable, size now " + collected.size());
        try {
            streamed.add(99);
        } catch (UnsupportedOperationException e) {
            System.out.println("Stream.toList().add   -> UnsupportedOperationException");
        }
        System.out.println("Stream.toList() permits null? "
                + Stream.of("x", null).toList());
        try {
            Stream.of("x", (String) null).collect(Collectors.toUnmodifiableList());
        } catch (NullPointerException e) {
            System.out.println("toUnmodifiableList with null -> NullPointerException");
        }
    }
}
```

<details><summary>Output and why</summary>

```
toMap duplicate key -> IllegalStateException: Duplicate key ana (attempted merging values 34 and 50)
with merge + LinkedHashMap = {ana=84, bo=29, cy=41}
class                      = LinkedHashMap
toMap null value    -> NullPointerException
groupingBy tolerates a null VALUE = {braga=[null], faro=[50], lisbon=[34, 41], porto=[29]}
counting            = {faro=1, lisbon=2, porto=1}
collect(toList) class = java.util.ArrayList
Stream.toList  class  = java.util.ImmutableCollections$ListN
collect(toList) is mutable, size now 5
Stream.toList().add   -> UnsupportedOperationException
Stream.toList() permits null? [x, null]
toUnmodifiableList with null -> NullPointerException
```

**The two-argument `toMap` throws on a duplicate key**, and the message even names the two values it
declined to merge. That is usually the behaviour you want — but it means any `toMap` over data you do
not control needs the three-argument form. Here `Integer::sum` gives `ana=84`, and the fourth
argument pins the map type so iteration order is defined.

**`toMap` rejects a null *value*** with an NPE, even though the backing `HashMap` would happily store
one. The reason is mechanical: `toMap` accumulates with `map.merge`, and `merge` treats a null value
as "remove this mapping", so the implementation cannot distinguish them and refuses.
`groupingBy` has no such problem — the null age appears as `[null]` under `braga`, because it is a
*downstream element*, not a map value.

**`counting()` returns `Long`, not `Integer`** — hence `faro=1` rather than any boxing surprise, and
it is the collector to reach for instead of a `toMap` with a merge function.

**Three list-collecting methods, three different contracts.** `collect(Collectors.toList())` gives a
**mutable** list of unspecified type (an `ArrayList` today, and the demo mutates it to prove it);
`Stream.toList()` gives an unmodifiable `ImmutableCollections$ListN` that **permits nulls**; and
`collect(toUnmodifiableList())` gives an unmodifiable list that **rejects** them. If you need
mutability, ask for it by name with `toCollection(ArrayList::new)` rather than relying on the
unspecified one.

</details>

### Drill 5 — enum collections, where the generics stop helping

```java
// Drill5.java

import java.util.*;

public class Drill5 {

    enum Day { MON, TUE, WED, THU, FRI }

    enum Colour { RED, GREEN }

    public static void main(String[] args) {
        EnumSet<Day> week = EnumSet.of(Day.WED, Day.MON, Day.FRI);
        System.out.println("iteration order   = " + week + "  (ordinal, not insertion)");
        System.out.println("range(TUE, THU)   = " + EnumSet.range(Day.TUE, Day.THU));
        System.out.println("complementOf      = " + EnumSet.complementOf(week));
        System.out.println("allOf size        = " + EnumSet.allOf(Day.class).size());

        Set<Day> mutable = EnumSet.noneOf(Day.class);
        mutable.add(Day.TUE);
        System.out.println("EnumSet is mutable, size = " + mutable.size());

        mismatchedTypes();

        Map<Day, String> plan = new EnumMap<>(Day.class);
        plan.put(Day.FRI, "release");
        plan.put(Day.MON, "plan");
        plan.put(Day.WED, null);
        System.out.println("EnumMap order     = " + plan);
        System.out.println("null VALUE stored = " + plan.containsKey(Day.WED)
                + " ; get -> " + plan.get(Day.WED));
        try {
            plan.put(null, "x");
        } catch (NullPointerException e) {
            System.out.println("null KEY          -> NullPointerException");
        }
        System.out.println("get(null) quietly = " + plan.get(null));
        System.out.println("entry class from a copy = "
                + new ArrayList<>(plan.entrySet()).get(0).getClass().getSimpleName());
    }

    /**
     * The generics are defeated deliberately: this is how the bug reaches production, through a raw
     * type or an erased {@code Collection<?>} boundary. The behaviour below is what the JDK does
     * once the compiler is out of the way.
     */
    @SuppressWarnings({"rawtypes", "unchecked"})
    static void mismatchedTypes() {
        Set days = EnumSet.of(Day.MON, Day.TUE);
        Set colours = EnumSet.of(Colour.RED);
        System.out.println("before mismatch   = " + days);
        System.out.println("removeAll(other enum) = " + days.removeAll(colours) + " -> " + days);
        System.out.println("containsAll(other)    = " + days.containsAll(colours));
        System.out.println("retainAll(other enum) = " + days.retainAll(colours) + " -> " + days
                + "   <- silently emptied");
        try {
            days.addAll(colours);
        } catch (ClassCastException e) {
            System.out.println("addAll(other enum)    -> ClassCastException");
        }
    }
}
```

<details><summary>Output and why</summary>

```
iteration order   = [MON, WED, FRI]  (ordinal, not insertion)
range(TUE, THU)   = [TUE, WED, THU]
complementOf      = [TUE, THU]
allOf size        = 5
EnumSet is mutable, size = 1
before mismatch   = [MON, TUE]
removeAll(other enum) = false -> [MON, TUE]
containsAll(other)    = false
retainAll(other enum) = true -> []   <- silently emptied
addAll(other enum)    -> ClassCastException
EnumMap order     = {MON=plan, WED=null, FRI=release}
null VALUE stored = true ; get -> null
null KEY          -> NullPointerException
get(null) quietly = null
entry class from a copy = SimpleEntry
```

**Iteration is ordinal order, not insertion order** — `of(WED, MON, FRI)` prints
`[MON, WED, FRI]`. That follows from the representation: membership is a bit position derived from
`ordinal()`, so there is nowhere for insertion order to be stored. It also means reordering the enum
constants silently changes iteration order, `range()`'s meaning, and every persisted ordinal.

**The mismatched-type block is the reason this drill exists.** Four bulk operations, four different
behaviours when the argument is an `EnumSet` of a *different* enum: `removeAll` returns `false` and
changes nothing; `containsAll` returns `false`; `addAll` throws `ClassCastException`; and
**`retainAll` silently empties the receiver**. The silent one is the dangerous one, and it is
perfectly logical — "keep only elements also present in the argument" is vacuously satisfied by
nothing — which is exactly why no exception is thrown.

**`EnumMap` allows a null value and rejects a null key.** The value goes in via a private sentinel,
so `containsKey(WED)` is `true` while `get(WED)` is `null`. `put(null, ...)` throws, because a key
needs an `ordinal()` — but `get(null)` returns `null` quietly rather than throwing, because
`isValidKey` screens it out first. Asymmetric, and worth knowing before you write a null check.

**And the entry class from the copy is `SimpleEntry`, not `EnumMap$Entry`.** `fillEntryArray` builds
`AbstractMap.SimpleEntry` **snapshots**, which is precisely why the folklore that
`EnumMap.EntryIterator` reuses one entry object survives casual experiment: the obvious test —
collect the entry set into a list and inspect it — cannot observe the iterator's real behaviour at
all. `EntryIterator.next()` allocates a fresh `Entry(index++)` per call, and that entry reads
`vals[index]` live.

</details>

## §5.3.7 The spaced-repetition schedule

The set is 155 files. Reading it end to end once produces recognition, not recall — and interviews
test recall. This schedule is built on one rule: **each pass is a different *kind* of work**, because
re-reading the same material the same way is what produces the illusion of knowing it.

### The four-week cycle

| When | What | How long | Why this, now |
|---|---|---|---|
| **Day 1** | Read, in the index's first-pass order: `framework/01`–`06`, `contracts/01`–`04`, `iteration/01`–`02`, `cost-and-memory/01`. Stop and memorise the null-policy and ordering matrices before going on. | 3–4 h | Everything hashed or sorted depends on the contracts. Reading `HashMap` internals before `equals`/`hashCode` wastes the reading. |
| **Day 2** | `array-list/01`–`04`, `linked-list/01`, `array-deque/01`, `priority-queue/01`–`02`. | 3 h | The simplest internals, and the amortised argument that recurs everywhere. |
| **Day 3** | The atomic concept checklist in [92d](92d-interview-internals-d-atomic-concept-checklist.md), out loud, marking every line you cannot explain in one sentence. **Do not re-read the files yet.** | 45 min | The first *retrieval* pass. The marked lines are your syllabus from here on; without this list you will keep re-reading what you already know. |
| **Day 4–5** | `hash-map/01`–`05c`, then `linked-hash-map/01`–`01c1`, then `sets/01`. | 5–6 h | The centre of the topic. `hash-map/` is 14 files because it earns them. |
| **Day 7** | The numbers drill in [93b](93b-drills.md) §5.3.1 — cold, cover the answers. Then the mechanism drill §5.3.5, out loud. | 40 min | Numbers decay fastest and are cheapest to restore. Day 7 is roughly where the first forgetting curve bites. |
| **Day 8–10** | `tree-map/`, `specialised-maps/`, `sets/02`–`03`, `immutable-collections/01`–`04e`. | 6 h | The second tier of implementations, and the one most candidates skip. |
| **Day 12** | The cost drill §5.3.3 and the which-one drill §5.3.4. Then the five code-reading drills above, predicting before opening each. | 1 h | Cost and choice are what "senior" is tested on. The code-reading drills are the closest thing here to a live interview. |
| **Day 14–16** | `utilities/01`–`07`, `contracts/05`, `iteration/03`, `concurrent-collections/01`–`05c`. | 6 h | Concurrency last, because it composes everything before it. |
| **Day 18** | The trap index in [93](93-drills-and-traps.md) §5.2.1, end to end, covering the "what actually happens" column. Then §5.2.2's version-stale table. | 1 h | The highest-value hour in the schedule: every row is a claim you would otherwise get wrong out loud. |
| **Day 21** | **Build one structure from scratch, from an empty file, without looking.** `MyArrayList` with growth and a fail-fast iterator, or `MyHashMap` with `put`/`get`/`resize`, or an LRU over a `HashMap` plus a sentinel-terminated linked list. Compile it. Run it against the real class on a few thousand random operations. | 3–4 h | This is the pass that converts reading into knowledge. You cannot hand-wave "what happens on resize" after you have written it. |
| **Day 22–24** | The three interview files at your tier — [90](90-interview-basics.md)/[90b](90b-interview-basics-b-questions-19-36.md), [91](91-interview-intermediate.md)/[91b](91b-interview-intermediate-b-questions-19-36.md), [92](92-interview-internals.md)/[92a](92a-interview-internals-a2-questions-10-18.md)/[92b](92b-interview-internals-b-questions-19-36.md) — read as **answer shapes**, not as content. Say each answer out loud before reading the model. | 3 h | You now know the material; what you are practising is the 90-second delivery and the "if they push" follow-up. |
| **Day 25** | All fifteen predict-the-output puzzles: [90c](90c-interview-basics-c-puzzles.md), [91c](91c-interview-intermediate-c-puzzles.md), [92c](92c-interview-internals-c-puzzles-and-checklist.md). Write your prediction down first. | 1.5 h | Fifteen retrieval attempts with immediate, unambiguous feedback. |
| **Day 28** | The checklist again, cold. Compare against your Day 3 marks. Anything still marked goes into a one-page list. | 45 min | The measurement pass. Two marks on the same line across three weeks means the file, not the drill. |

### The night before

Ninety minutes, in this order, and nothing else:

1. [93](93-drills-and-traps.md) §5.2.1 — the trap index. **First**, because it reloads more per minute
   than anything else in the set.
2. [93b](93b-drills.md) §5.3.1 — the numbers, cold.
3. `framework/06-matrices-and-choosing.md` — the three matrices and the decision tree.
4. `cost-and-memory/01-master-cost-table.md` — the table only; skip the prose.
5. `hash-map/01`, `hash-map/03a`, `hash-map/04` — constants, the lo/hi split, treeify. These three
   carry more interview weight than the rest of the set combined.
6. The `## Cheat sheet` section of any file you are shaky on — and *only* the cheat sheet.
7. [92d](92d-interview-internals-d-atomic-concept-checklist.md) as a final self-quiz, at whatever
   pace you can sustain out loud.

**What not to do the night before:** start a build-it file, read a source walk you have not read
before, or re-read anything end to end. New material at this point displaces retrieval practice and
buys nothing.

### If you have one week, not four

Compress by dropping *coverage*, never the retrieval passes:

- **Day 1:** `framework/06` (matrices), `cost-and-memory/01` (cost table), `contracts/02` and
  `contracts/03` (the `equals`/`hashCode` contract).
- **Day 2:** `hash-map/01`, `01b`, `02`, `03`, `03a`, `04`, `04b` — constants, spread, put/get,
  resize, the split, treeify, the Poisson argument.
- **Day 3:** `array-list/01` and `04`; `linked-hash-map/01` and `01b`; `tree-map/01`.
- **Day 4:** [93](93-drills-and-traps.md) in full — trap index plus version-stale table.
- **Day 5:** [93b](93b-drills.md) — all five drills, cold.
- **Day 6:** the fifteen puzzles, and the code-reading drills above.
- **Day 7:** [92d](92d-interview-internals-d-atomic-concept-checklist.md) cold, then the three
  interview files at your tier as answer shapes.

That is roughly 20 hours and it covers what is actually asked. The material it sacrifices —
`build-it/`, the specialised maps, the lock-free queues — is what distinguishes a strong answer from
an adequate one, so put it back in as soon as you have the days.

## Pitfalls

### Re-reading instead of retrieving

**Wrong**

> Read the whole set in week 1. Read it again in week 2. Feel more confident each time.

Fluency at *reading* is not recall. Re-reading a file you have read produces a strong feeling of
knowing and almost no retrievable memory, which is exactly why the confidence rises while the
performance does not.

**Right**

> Read once, then spend every subsequent session **retrieving**: the checklist out loud, the numbers
> drill covered, the puzzles predicted before opening. Only re-read the specific file behind a line
> you failed.

**Why people do it:** re-reading is comfortable and measurable — pages turned — while retrieval is
uncomfortable and produces a list of things you got wrong. The list is the point.

### Skipping the Day 21 build

**Wrong**

> "I have read `array-list/05`–`09` and `hash-map/06`–`10b` twice; I know how they work."

**Right**

> Open an empty file and write `MyHashMap` with `put`, `get` and `resize` from memory. Compile it.
> Run 100,000 random operations against `java.util.HashMap`, comparing the return value and `size`
> after every call.

**Why it matters:** every writer of this set found real bugs that way — a spliterator over-consuming
at a split boundary, a demo that removed the wrong element and silently produced no exception, an
`Entry` that did not implement `Map.Entry`. Reading cannot find those, and neither can an interview
answer that was never tested. The differential test is the part that converts "I think this is how
resize works" into "this is how resize works, and here is what it printed".

## Cheat sheet

| Question | The answer |
|---|---|
| First thing to read | `framework/06` matrices, then `cost-and-memory/01` |
| First retrieval pass | Day 3, the atomic concept checklist, out loud |
| Fastest-decaying material | the numbers — drill on day 7 and again on day 12 |
| Highest value per hour | [93](93-drills-and-traps.md) §5.2.1, the trap index |
| The pass that converts reading into knowledge | Day 21, build one structure from an empty file |
| The three files with the most interview weight | `hash-map/01`, `hash-map/03a`, `hash-map/04` |
| Night-before order | trap index → numbers → matrices → cost table → the three `hash-map` files → cheat sheets → checklist |
| Night before, do not | start a build-it, or read anything new |
| One-week plan | matrices and cost, `hash-map` core, three drills days, puzzles, checklist |
| How to know it worked | a checklist line marked on day 3 and clear on day 28 |
| Drill 1 | comparator defines identity in `TreeMap`/`TreeSet`, not `equals` |
| Drill 2 | `set` is not structural; `sort` is; a range delete is `subList(a,b).clear()` |
| Drill 3 | a mutated key gives a `HashSet` two `equals` elements, and a copy collapses them |
| Drill 4 | `toMap` throws on duplicates and on null values; three list collectors, three contracts |
| Drill 5 | mismatched `EnumSet.retainAll` silently empties; `EnumMap` takes a null value, not a null key |

## Self-test

**Q1.** You have three weeks and you have read the whole set once. What is the single highest-value
thing to do next?

<details><summary>Answer</summary>

A cold retrieval pass over the atomic concept checklist in
[92d](92d-interview-internals-d-atomic-concept-checklist.md), out loud, marking every line you cannot
explain in one sentence. It takes 45 minutes and it converts "I have read everything" into a
specific, finite list of gaps — which is the only thing that makes the remaining time efficient.
Without it, the next three weeks get spent re-reading the material you already know, because that is
the material that feels good to read.

</details>

**Q2.** Drill 3 produced a `HashSet` of size 2 whose two elements are `equals`. Give the shortest
diagnostic for this in a live system.

<details><summary>Answer</summary>

Copy the collection and compare sizes: `new HashSet<>(suspect).size() < suspect.size()` means at
least one element's hash has changed since insertion, because the copy rehashes every element under
its *current* state and the duplicates collapse. For a `Map`, the equivalent is
`new HashMap<>(suspect).size() < suspect.size()`. In a heap dump the same finding shows up as a map
whose `size` disagrees with your own bookkeeping, and MAT's `map_collision_ratio` will *not*
necessarily flag it — the entries are in the wrong buckets, not in one bucket.

</details>

**Q3.** Why does the schedule put concurrency last and the contracts first?

<details><summary>Answer</summary>

Because of what each depends on. `equals`/`hashCode` and ordering are load-bearing for every hashed
or sorted structure in the set — reading `HashMap`'s bin walk before you know what `hashCode`
promises means the reading does not stick. Concurrency is the reverse: `ConcurrentHashMap` is
`HashMap`'s bin structure plus CAS and a per-bin monitor, its `TreeBin` is a locked variant of the
same tree, and its resize is the same lo/hi split done cooperatively. Read it first and you learn it
as a list of unrelated facts; read it last and it is three deltas on things you already know.

</details>

**Q4.** The night-before list has seven items and explicitly excludes new material. Why exclude it?

<details><summary>Answer</summary>

Because the marginal value of a *new* fact the night before is close to zero and its cost is not: it
displaces retrieval practice on material you already half-know, and it tends to be the material you
are least able to deliver fluently under pressure. The seven items are all *reload* passes over
things you have already built — the trap index, the numbers, the matrices, the cost table, the three
highest-weight `hash-map` files, cheat sheets, the checklist. The one exception worth making is a
specific gap you know an interviewer will probe, and even then read the one file, not the folder.

</details>

**Q5.** Drill 5's `retainAll` silently emptied the set. Why is that harder to catch than the
`ClassCastException` from `addAll`?

<details><summary>Answer</summary>

Because it is a *successful* operation returning `true`. `addAll` throws, so it fails at the call
site with a stack trace pointing at the mistake. `retainAll` does exactly what the contract says —
keep only the elements also present in the argument — and since no element of a `Day` set is present
in a `Colour` set, the correct answer is the empty set. So there is no exception, no log line, and
the collection is simply empty later, at which point the code that reads it sees "no permissions" or
"no active days" and behaves plausibly. The class of bug is: an operation whose *degenerate* result
is indistinguishable from a legitimate one. The defence is type safety at the boundary — do not let
an `EnumSet` reach a raw `Set` or a `Collection<?>` parameter that will be passed to `retainAll`.

</details>

---

**Leaves covered:** 5.3.6, 5.3.7 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 701
