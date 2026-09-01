# 02 Java Collections — Interview, BASICS tier — questions 19–36 (§5.1)

**Target version: Java 21 LTS.** | [Index](00-index.md)
Previous: [90-interview-basics.md](90-interview-basics.md) · Next: [90c-interview-basics-c-puzzles.md](90c-interview-basics-c-puzzles.md)

Second half of the BASICS-tier question set: questions 19–36 of 36. The part summary table and
the answer shape are in [90](90-interview-basics.md); the puzzles are in
[90c](90c-interview-basics-c-puzzles.md).

## Q&A 19–36

### Q19. "`Comparable` vs `Comparator`." (§5.1.23)

**Model answer.** `Comparable` is the type's own natural order — one method, `compareTo`,
implemented by the class itself, so there is exactly one of them. `Comparator` is an external
ordering, so a type can have any number of them, and you pass one where you need it: to
`list.sort`, to a `TreeMap` constructor, to a `PriorityQueue`.

The rule of thumb is: implement `Comparable` when there is one obviously correct order that is
part of the type's identity (`Integer`, `String`, `LocalDate`); use a `Comparator` for everything
else, including every "sort by column X" in a UI. If a type has no single natural order, giving it
one is a design smell.

Two details worth adding. `Comparator` composes: `comparing(Person::lastName).thenComparing(Person::firstName)`,
and `thenComparing` only breaks a tie — it runs when the previous key returns 0. And `reversed()`
flips the sign of the whole chain built so far, so
`comparing(A).thenComparing(B).reversed()` is not "A ascending, B descending".

**If they push:** the recommendation that `compareTo == 0` agree with `equals` is a *should*, not a
*must* — `BigDecimal` breaks it deliberately, and the price is that a `TreeSet<BigDecimal>` treats
`2.0` and `2.00` as the same element while `equals` does not.

**One-line close:** one natural order on the type, any number of external ones — and never
subtract inside either.

### Q20. "Why is `Map` not a `Collection`?" (§5.1.29)

**Model answer.** Because a `Collection` is a bag of single elements and a `Map` is a set of
pairs, and the `Collection` methods do not have a sensible meaning over pairs. What would
`map.add(x)` take? What would `map.iterator()` yield — keys, values, or entries? What would
`map.contains(x)` search? Every answer is a guess, and a guessed answer in a root interface is a
permanent mistake.

Josh Bloch's own explanation is that the two abstractions are genuinely different, and rather than
force one into the other the framework gives you three **views** that bridge them: `keySet()`
returns a `Set<K>`, `values()` a `Collection<V>`, and `entrySet()` a `Set<Map.Entry<K,V>>`. So you
can reach the `Collection` world from a `Map` in whichever direction you actually mean, and the
ambiguity is resolved at the call site instead of in the type hierarchy.

**If they push:** `Map` and `Collection` do share `Iterable`'s world only through those views, and
that is also why `Map` has its own parallel hierarchy — `SortedMap`/`NavigableMap` mirroring
`SortedSet`/`NavigableSet`, and Java 21's `SequencedMap` mirroring `SequencedCollection`.

**One-line close:** a `Map` is pairs, not elements, so the framework bridges with three views
rather than pretending a pair is an element.

### Q21. "What is the difference between `Arrays.asList`, `List.of`, and `Collections.unmodifiableList`?" (§5.1.30)

**Model answer.** Three different things that all get called "read-only".

| | `Arrays.asList(arr)` | `List.of(...)` | `Collections.unmodifiableList(x)` |
|---|---|---|---|
| Since | 1.2 | 9 | 1.2 |
| Class | `java.util.Arrays$ArrayList` | `ImmutableCollections.List12`/`ListN` | `Collections$UnmodifiableRandomAccessList` |
| Backing | the caller's array, by reference | its own array (or two fields) | the wrapped list, by reference |
| `set(i, v)` | **succeeds**, writes through to the array | throws | throws |
| `add`/`remove` | throws | throws | throws |
| `null` elements | allowed | `NullPointerException` at construction | allowed |
| `contains(null)` | `false` | **throws NPE** | `false` |
| Sees source changes | yes, both directions | n/a — it owns its data | yes, one direction |

So `Arrays.asList` is fixed-**size**, not read-only: `set`, `sort` and `replaceAll` all write
straight into the array you passed. `List.of` is genuinely immutable and null-hostile. And
`unmodifiableList` blocks *your* writes while leaving the owner of the backing list free to change
what you see — it is a view, not a copy.

**If they push:** the trap in `Arrays.asList` is primitives — `Arrays.asList(new int[]{1,2,3})`
compiles without a warning and gives you a `List<int[]>` of size 1, because a type variable cannot
bind to `int`. The fix is `Arrays.stream(arr).boxed().toList()`.

**One-line close:** fixed-size write-through array view; immutable null-hostile copy; live
read-only wrapper — and only the middle one is actually immutable.

### Q22. "How do `keySet` and `entrySet` relate to the map?" (§5.1.32)

**Model answer.** They are live views with no storage of their own. Each is created lazily on
first call and then cached in a field, so `map.keySet() == map.keySet()` is `true`, and each
forwards every operation to the map. `clear()` on any of the three empties the whole map;
`remove` through them deletes mappings; `add` on any of them throws
`UnsupportedOperationException`, because there is no value to supply.

The part that catches people is what `entrySet()` yields on a `HashMap`: the map's own
`HashMap$Node` objects. So `entry.setValue(v)` writes straight into the map's storage — and it is
not a structural change, so it never bumps `modCount` and never triggers CME. Worse, a retained
entry stays live across a resize (a resize relinks the same nodes) and stays *readable but
detached* after the mapping is removed, at which point `setValue` writes into memory nothing can
reach.

If you want to keep a pair beyond the loop, snapshot it: `Map.entry(e.getKey(), e.getValue())`.

**If they push:** the views' costs differ. `keySet().contains(k)` is O(1) (`containsKey`), but
`values().contains(v)` is O(n) — it is `containsValue`, which walks every bin and every chain.
And `keySet().toArray()`/`values().toArray()` copy, while `entrySet().toArray()` does not override
and hands you the live nodes.

**One-line close:** three cached live doors into the same map, and `entrySet()`'s elements are the
map's real nodes, so treat them as borrowed.

### Q23. "What is `LinkedHashMap` and what does it cost?"

**Model answer.** A `HashMap` with a doubly-linked list threaded through the same nodes. It does
not wrap entries — `LinkedHashMap.Entry extends HashMap.Node` and adds two references, `before`
and `after`, so there is still one object per entry and the cost is +8 bytes: 40 bytes instead of
32 under compressed oops.

What you buy is defined iteration order. By default that is insertion order. Pass `true` to the
three-argument constructor and you get **access order**, where a successful `get` moves the entry
to the tail — which is what makes the ten-line LRU cache work, together with the `protected
removeEldestEntry` hook.

The cost beyond memory: four extra pointer writes per insert and per removal, and worse locality
than a plain `HashMap` on random access. But iteration is *cheaper* — O(size) walking the order
list, against `HashMap`'s O(capacity + size) table scan.

**If they push:** in access order a plain `get` is a structural modification. It performs six
pointer writes and increments `modCount`, so two threads calling `get` concurrently are two
writers, and a `get` inside an iteration over the same map throws CME.

**One-line close:** the same nodes plus `before`/`after`, so +8 bytes an entry for guaranteed order
— and in access order, reads are writes.

### Q24. "What does `Collections.synchronizedList` actually give you?"

**Model answer.** One mutex, and every interface method wrapped in a `synchronized` block on it.
That makes each individual call atomic and gives you the memory visibility a plain `ArrayList`
lacks. It gives you nothing else, and the two gaps matter more than the guarantee.

First, compound actions still race. `if (!list.contains(x)) list.add(x)` is two separate
`synchronized` blocks with a window between them; the wrapper cannot help. You need to hold the
lock across both calls yourself.

Second — and this is the one people are surprised by — `iterator()`, `spliterator()` and `stream()
` return the **raw underlying** objects with no synchronization at all. The source comment says so
outright. So iterating a synchronized collection requires `synchronized (theWrapper) { ... }`
around the *whole loop*, not around each call, or you get `ConcurrentModificationException` or
worse.

**If they push:** the derived views do share the outer mutex — `synchronizedMap(m).keySet()`,
`values()` and `entrySet()` are each constructed with the identical `mutex` field, in both JDK 8
and JDK 21, so the folklore warning to "check your JDK version" is unfounded. The real caveats are
the two above.

**One-line close:** per-call atomicity and visibility, but iteration and compound actions are
still yours to lock — and for a map, `ConcurrentHashMap` is the better answer.

### Q25. "What does `Collections.nCopies(3, x)` allocate?"

**Model answer.** One object, holding one reference. `nCopies` returns an immutable `CopiesList`
with a single `final E element` field and a size, so all n slots are the same reference — there is
no array and no copying, and it is O(1) in memory whatever n is.

That is exactly why it is dangerous with a mutable element: `List<List<String>> rows =
Collections.nCopies(3, new ArrayList<>())` gives you three views of *one* list, so adding to
"row 0" adds to all three. The same trap appears with `Arrays.fill(arr, new ArrayList<>())` and
with any "initialise a grid" one-liner.

**If they push:** it is a good fit for padding or for a repeated-value argument to `addAll`, and
because `CopiesList` declares no `set` override, `set` throws — unlike `Arrays.asList`, which is
the neighbouring rung on the immutability ladder and does write through.

**One-line close:** one shared reference n times, not n copies — fine for immutable elements, a bug
factory for mutable ones.

### Q26. "Is `Collections.sort` stable, and does it copy?"

**Model answer.** Yes and yes. Since Java 8, `Collections.sort(list)` just calls
`list.sort(null)`, and the default `List.sort` implementation copies to an array, calls
`Arrays.sort`, then writes back through a `ListIterator`. `ArrayList` overrides it to sort
`elementData` in place, which is why it avoids the copy — but it still bumps `modCount`, so any
iterator you were holding is poisoned.

The algorithm for objects is **TimSort**: an adaptive, stable merge sort. Stability matters
because it lets you sort by a secondary key first and then by the primary key, and get a
(primary, secondary) ordering. Best case O(n) on already-sorted input, worst case O(n log n),
O(n/2) extra space.

Primitives get a different algorithm — dual-pivot quicksort, in place, **not** stable — because
`int`s have no identity beyond their value, so there is nothing for stability to preserve.

**If they push:** the exception `IllegalArgumentException: Comparison method violates its general
contract!` comes from TimSort discovering that your comparator is inconsistent — usually
int-subtraction overflow, a non-transitive comparator, or mutation of the elements during the sort.

**One-line close:** stable TimSort for objects with a copy-and-write-back unless the list overrides
it, unstable dual-pivot quicksort for primitives.

### Q27. "`getOrDefault` versus `containsKey` plus `get` — and how do you count occurrences?"

**Model answer.** `getOrDefault(k, d)` is one lookup instead of two, and it returns the default
only when the key is **absent** — if the key is present and mapped to `null`, you get `null`, not
the default. That distinction is the whole reason `containsKey` still exists: `get` returning
`null` is ambiguous between "absent" and "mapped to null".

For counting, the idiom is `map.merge(key, 1, Integer::sum)`. It stores `1` directly when the key
is absent (the remapping function is not even called) and applies the function when it is present.
The alternatives: `map.computeIfAbsent(k, x -> new ArrayList<>()).add(v)` for a multimap,
`Collectors.counting()` when you are already in a stream, and
`ConcurrentHashMap<K, LongAdder>` under real contention.

**If they push:** the null semantics of the default methods are the trap. `compute`, `computeIfPresent`
and `merge` **remove** the entry when the function returns `null`; `computeIfAbsent` returning
`null` inserts nothing. And none of them is atomic on a plain `HashMap` — only on
`ConcurrentHashMap`.

**One-line close:** one lookup, and "absent" is not the same as "mapped to null"; `merge` for
counters, `computeIfAbsent` for multimaps.

### Q28. "How do you use a `Deque` as both a stack and a queue?"

**Model answer.** A `Deque` has both ends, so you pick which end you push to. For a **queue**, add
at the tail and take from the head: `offer`/`addLast` with `poll`/`removeFirst`. For a **stack**,
push and pop at the same end: `push` is `addFirst` and `pop` is `removeFirst`.

The reason to know both names is the throw-versus-null split. `add`, `remove()` and `element()`
throw on a full or empty deque; `offer`, `poll` and `peek` return a sentinel instead. Pick per
call site: a sentinel where emptiness is normal, an exception where it is a bug.

The concrete reason to prefer `ArrayDeque` over `java.util.Stack` is iteration order.
`ArrayDeque` used as a stack iterates top-to-bottom, matching pop order; `Stack` extends `Vector`
and iterates **bottom-to-top**, the opposite of pop order. And `Stack.search` returns a 1-based
distance from the top, with `-1` for a miss, which is a signature nobody expects.

**One-line close:** `push`/`pop` for a stack, `offer`/`poll` for a queue, `ArrayDeque` for both —
and its iteration order is the one that matches your mental model.

### Q29. "When would you write your own collection?"

**Model answer.** Rarely, and for one of four reasons: the JDK has no such shape, you need a
primitive specialisation, you need a hook the JDK class does not expose, or you need a bound the
JDK class refuses to give you.

Shapes the JDK does not have: a multimap, a bidirectional map, a bag/multiset, a fixed-capacity
ring buffer that overwrites rather than grows, an interval map. For those, reach for Guava first —
writing a `Multimap` by hand is easy to start and easy to get wrong, because the interesting part
is removing the key when its value list empties, not adding to it.

Primitive specialisation is the strongest genuine case: `ArrayList<Integer>` costs about five times
`int[]` and adds a pointer chase per element, so a measured hot path may justify an `IntArrayList`
— or, better, fastutil or Eclipse Collections.

If you do write one, extend the right skeleton rather than an interface: `AbstractCollection` needs
only `iterator()` and `size()`, `AbstractList` needs `get` and `size` — but note that
`AbstractList` on a non-random-access structure gives you an O(n²) iteration, which is why
`AbstractSequentialList` exists.

**One-line close:** for a shape the JDK lacks or a primitive you measured; extend the matching
`Abstract*` skeleton, and check Guava before you type.

### Q30. "Does removing entries shrink a `HashMap`?"

**Model answer.** Never. `remove` unlinks the node and decrements `size`, and that is all — the
table array is read for indexing and never written. `clear()` is the same: it nulls every slot,
sets `size` to 0, and keeps both the array and the threshold. So `clear()` costs O(capacity), not
O(size).

The consequence is a real production shape: a map that once held ten million entries keeps a
16,777,216-slot array (`ceil(10M / 0.75)` rounded to `1 << 24`) after being drained — 64 MB of
references under compressed oops, holding nothing. Iterating that drained map is still
O(capacity), so a three-entry map in a grown table walks millions of empty slots; measured in this
set at 1,178,557 ns versus 64 ns for a fresh 16-slot map.

The only fix is to drop the reference and build a new map — `map = HashMap.newHashMap(expected)` on
Java 19+. There is no `trimToSize` on `HashMap`; the JDK has one on `ArrayList` and on
`StringBuilder`, and nowhere else that matters.

**One-line close:** removal frees the nodes, never the table — so replace the map rather than
clearing it if the capacity mattered.

### Q31. "Is `new ArrayList<>(List.of(1, 2))` equal to `List.of(1, 2)`?"

**Model answer.** Yes. Collection equality is defined by the root interface plus the contents, not
by the class: any two `List`s with equal elements in the same order are `equal`, regardless of
implementation. The same holds for `Set`s (same elements, order irrelevant) and `Map`s (same
entries).

Across root interfaces it is always false: a `List` is never equal to a `Set`, even with identical
contents, because `AbstractList.equals` requires `o instanceof List`.

The hash codes follow the same rule and are worth memorising, because they explain the order
sensitivity: a `List`'s hash is the 31-fold `h = 31*h + e.hashCode()`, so it is order-sensitive; a
`Set`'s is the plain **sum** of element hashes, so it is not; a `Map`'s is the sum of
`key.hashCode() ^ value.hashCode()` per entry.

**If they push:** the identity-based exceptions are what to name. `IdentityHashMap` deliberately
violates this — its `equals` compares by reference identity and is asymmetric against other maps,
so never put one in a `Set`. And a self-referential collection survives `toString` (which guards
with `e == this`) but blows the stack in `hashCode`, which does not guard.

**One-line close:** equal by interface and contents, not by class — and `List` hash is order-sensitive
while `Set` and `Map` hashes are sums.

### Q32. "What does `Iterator.remove()` cost?"

**Model answer.** It depends entirely on the backing structure, which is exactly why the method
exists on the iterator rather than only on the collection — the iterator already knows where it is.

| Collection | `Iterator.remove()` | Why |
|---|---|---|
| `LinkedList` | O(1) | unlink a node it is already holding |
| `HashMap`/`HashSet` | O(1) | splice out of the bin's chain, predecessor known |
| `TreeMap`/`TreeSet` | O(log n) | `deleteEntry` plus rebalancing |
| `ArrayList` | O(n) | one `System.arraycopy` to close the gap |
| `ArrayDeque` | O(min(front, back)) | shift the shorter side |
| immutable collections | `UnsupportedOperationException` | no mutators at all |
| `CopyOnWriteArrayList` | `UnsupportedOperationException` | the iterator holds a frozen snapshot |

Two mechanical facts to add. Calling `remove()` twice in a row throws `IllegalStateException`,
because the first call clears the "last returned" slot. And a successful `remove()` resynchronises
`expectedModCount`, which is precisely why removing through the iterator does not throw CME while
removing through the collection does.

**One-line close:** O(1) on linked and hashed structures, O(n) on `ArrayList`, unsupported on
immutable and copy-on-write.

### Q33. "When do you use a `BitSet`?"

**Model answer.** When your elements are small non-negative `int`s and the domain is dense. A
`BitSet` stores one bit per position in a `long[]`, so a set of the integers 0–1,000,000 costs
about 125 KB, against roughly 48 bytes per element for a `HashSet<Integer>` — a `Node`, a boxed
`Integer`, and a table slot. Bulk operations are word-at-a-time `and`/`or`/`andNot`, so
intersection and union are effectively free.

The three size methods are the trap and they measure three different things: `length()` is the
index of the highest set bit plus one, `size()` is the capacity of the backing `long[]` in bits,
and `cardinality()` is the number of bits actually set. Only `cardinality()` is the member count.

**If they push:** it does not suit a sparse or huge domain — `new BitSet()` sized to a single bit
at index 1,000,000 allocates the whole word array up to there. For sparse integer sets use
`RoaringBitmap`, which compresses per chunk.

**One-line close:** dense small-integer domains, bulk ops as single machine words — and
`cardinality()`, not `size()`, is the count.

### Q34. "What is `EnumSet` and why is it fast?"

**Model answer.** A `Set` implementation specialised for a single enum type, and it is fast
because it does no hashing at all. Every enum constant has an `ordinal()`, so membership is one
bit position: `RegularEnumSet` holds a single `long elements` field and `contains` is
`(elements & (1L << ordinal)) != 0`.

That gives you constant-time everything and, more strikingly, bulk operations as single machine
instructions: union is `elements |= other.elements`, difference is `&= ~`, intersection is `&=`.
No loop, no allocation, no comparison. The whole set object is about 32 bytes regardless of how
many constants it holds.

The choice of implementation is made on the **number of constants in the enum**, not the size of
the set: 64 or fewer gives `RegularEnumSet` with one `long`, more gives `JumboEnumSet` with a
`long[]`. Both are chosen in `EnumSet.noneOf`.

**If they push:** two things people get wrong. `EnumSet` is **mutable** and not thread-safe — a
`final` field only protects the reference, and there is no immutable variant (wrap with
`Set.copyOf`, which loses the bitmask). And the bulk fast paths require the argument to be a
`RegularEnumSet` of the *same* enum type; with a mismatched type, `addAll` throws
`ClassCastException` while `retainAll` silently empties the set.

**One-line close:** ordinals as bit positions in a `long`, so bulk set algebra is one instruction —
and it is mutable, which surprises people.

### Q35. "Why does `Map.of` reject duplicate keys and nulls?"

**Model answer.** Because it is a factory for a *literal*, and a literal with a duplicate key or a
null is almost always a typo. `Map.of("a", 1, "a", 2)` throws
`IllegalArgumentException: duplicate key: a` at construction rather than silently keeping one of
them, and any null key or value throws `NullPointerException`. `Set.of("a", "a")` behaves the
same way.

Contrast `copyOf`, which sanitises a *value* rather than validating a literal:
`Set.copyOf(List.of("a", "a"))` deduplicates and returns a one-element set. Both reject nulls.

The null hostility goes further than construction, and this is the part that bites: on an immutable
collection, even a **query** with `null` throws. `List.of("a").contains(null)`,
`Set.of("a").contains(null)` and `Map.of("a", 1).get(null)` all throw `NullPointerException`,
where the same query on `Collections.unmodifiableList(...)`, `Arrays.asList(...)` or
`Collections.emptyList()` returns `false`/`null` quietly.

**If they push:** `Map.of` caps at **10 pairs** — 11 pairs is a compile error, because the overloads
stop there; use `Map.ofEntries(Map.entry(k, v), ...)` beyond that, which also gives you
line-by-line blame when one of them is null.

**One-line close:** `of` validates a literal and throws, `copyOf` sanitises a value and
deduplicates — and on the `of` family even `contains(null)` throws.

### Q36. "How many bytes is an empty `ArrayList` versus an empty `HashMap`?"

**Model answer.** Both are lazy, and that is the interesting part. `new ArrayList<>()` allocates
one object of about 24 bytes and **no array at all** — it points at a shared static empty array
until the first `add`, which inflates it to capacity 10. `new HashMap<>()` is about 48 bytes and
allocates no table; the `Node[]` appears on the first `put`.

So a `Map<String, List<String>>` holding a thousand keys whose lists are all empty still costs
about a thousand times 24 bytes of `ArrayList` shells plus roughly 144 bytes per key once you count
the `HashMap.Node`, the boxed pieces and the table slot — measured in this set at ~144 bytes per key
for a map of singleton lists, against ~48 for a flat `Map<K,V>`. "Empty collections are free" is
false at scale.

For the arithmetic behind those numbers: a 64-bit HotSpot object header is 12 bytes, an array
header 16, a reference 4 under compressed oops, and everything rounds up to 8. So an `Integer` is
16 bytes, a `HashMap.Node` is 32, a `LinkedHashMap.Entry` 40, and a `TreeNode` 56.

**One-line close:** ~24 and ~48 bytes with nothing allocated yet — lazy, but not free once you have
a million of them.

## Pitfalls

### Treating `Arrays.asList` as immutable

**Wrong**

```java
private static final List<String> MODES = Arrays.asList("read", "write");
// elsewhere
MODES.set(0, "admin");   // succeeds
```

The constant is now `[admin, write]` for the rest of the JVM's life, and if the argument had been
an array variable, that array changed too.

**Right**

```java
private static final List<String> MODES = List.of("read", "write");
MODES.set(0, "admin");   // UnsupportedOperationException
```

**Why people believe it:** `add` and `remove` do throw, so the list *looks* read-only until someone
calls `set`, `sort` or `replaceAll` — the three methods `Arrays$ArrayList` overrides to write
straight through to the backing array.

### Iterating a `synchronizedList` without holding the lock

**Wrong**

```java
List<String> shared = Collections.synchronizedList(new ArrayList<>());
for (String s : shared) {          // iterator() returned the RAW iterator
    process(s);                    // another thread adds here -> CME
}
```

**Right**

```java
List<String> shared = Collections.synchronizedList(new ArrayList<>());
synchronized (shared) {            // hold the mutex across the WHOLE loop
    for (String s : shared) {
        process(s);
    }
}
```

**Why people believe it:** every other method on the wrapper is synchronized, so it is reasonable to
assume `iterator()` is too. It is not — the source returns the underlying iterator unwrapped, and
the class javadoc tells you to lock the loop yourself.

## Cheat sheet

| Question | The one-line answer |
|---|---|
| `Comparable` vs `Comparator` | one natural order on the type vs any number of external ones |
| `thenComparing` | runs only on a tie; `reversed()` flips the whole chain |
| Why `Map` is not a `Collection` | pairs are not elements; `keySet`/`values`/`entrySet` bridge it |
| `Arrays.asList` | fixed-**size** write-through view of the array; `set` succeeds |
| `List.of` | immutable, null-hostile even on `contains(null)`, arities 0–10 + varargs |
| `unmodifiableList` | live read-only **view**; the owner can still change it |
| `Map.of` cap | 10 pairs; use `Map.ofEntries` beyond that |
| `of` vs `copyOf` | `of` validates a literal (throws on duplicates); `copyOf` sanitises (deduplicates) |
| Map views | lazily created, then cached; `map.keySet() == map.keySet()` |
| `entrySet()` elements on `HashMap` | the map's real `Node`s; `setValue` writes through, no `modCount` |
| Safe pair snapshot | `Map.entry(e.getKey(), e.getValue())` |
| `LinkedHashMap` cost | +8 B/entry (40 vs 32); iteration O(size) not O(capacity + size) |
| Access order | a `get` is a structural write: 6 pointer writes + `modCount++` |
| `synchronizedX` gives | per-call atomicity + visibility; **not** iteration, **not** compound actions |
| `synchronizedMap` views | do share the outer mutex, JDK 8 and 21 alike |
| `nCopies(n, x)` | one shared reference n times; O(1) memory; `set` throws |
| Object sort | TimSort, stable, `MIN_MERGE = 32`, O(n) best case |
| Primitive sort | dual-pivot quicksort, in place, not stable |
| `getOrDefault` | default only when **absent**; a stored `null` is returned as `null` |
| Counter idiom | `merge(k, 1, Integer::sum)` |
| Multimap idiom | `computeIfAbsent(k, x -> new ArrayList<>()).add(v)` |
| Function returns `null` | `compute`/`computeIfPresent`/`merge` **remove**; `computeIfAbsent` inserts nothing |
| Stack order | `ArrayDeque` iterates top-to-bottom; `java.util.Stack` bottom-to-top |
| `Stack.search` | 1-based from the top, `-1` on a miss |
| `HashMap` shrink | never — `remove` and `clear()` keep the table; rebuild instead |
| `clear()` cost | O(capacity) |
| Collection equality | same root interface + same contents; `List` hash is order-sensitive, `Set`/`Map` hashes are sums |
| `Iterator.remove` | O(1) linked/hashed, O(log n) tree, O(n) `ArrayList`, unsupported on immutable/COW |
| `BitSet` sizes | `length()` highest bit + 1, `size()` capacity in bits, `cardinality()` the count |
| `EnumSet` | ordinals as bits in a `long`; ≤64 constants → `RegularEnumSet`; **mutable** |
| Empty footprints | `ArrayList` ~24 B and no array; `HashMap` ~48 B and no table |
| Byte units | header 12, array header 16, ref 4, round to 8 ⇒ `Integer` 16, `Node` 32, `Entry` 40, `TreeNode` 56 |

## Self-test

**Q1.** `Arrays.asList(1, 2, 3).set(0, 9)` — does it throw?

<details><summary>Answer</summary>

No. It succeeds and writes `9` into the backing array. `Arrays$ArrayList` overrides `set`, `sort`
and `replaceAll` to write through to the array it was given; only the size-changing operations
(`add`, `remove`) throw, and they throw because they are *not* overridden — they fall through to
`AbstractList`'s throwing defaults. If the argument was an array variable rather than a varargs
literal, the caller's array is now modified too.

</details>

**Q2.** You hold a `Map.Entry` from `entrySet()` after removing its key from the map. What does
`entry.setValue("x")` do?

<details><summary>Answer</summary>

It succeeds and writes into a node the map no longer references — an invisible write. On
`HashMap`, `entrySet()` yields the map's own `HashMap$Node` objects; removal unlinks the node from
its bin but the node object is still readable through your reference. So `getKey`/`getValue` still
work, `setValue` still writes, and nothing observes the write. Snapshot with
`Map.entry(k, v)` if you need to keep a pair.

</details>

**Q3.** Why is `Collectors.toList()` different from `Stream.toList()`?

<details><summary>Answer</summary>

`collect(Collectors.toList())` returns a **mutable** list whose concrete type is unspecified by
contract (an `ArrayList` in practice today), and it permits `null` elements.
`Stream.toList()` (Java 16+) returns an unmodifiable `ImmutableCollections$ListN` — always `ListN`,
with no size specialisation — and it **does** permit nulls, unlike `List.of`. The third option,
`collect(Collectors.toUnmodifiableList())`, is unmodifiable *and* rejects nulls with an NPE. So if
you need mutability, ask for it explicitly with `toCollection(ArrayList::new)`.

</details>

**Q4.** A cache is a `HashMap` that grew to 5 million entries and was then cleared each night.
Memory never comes back. Why?

<details><summary>Answer</summary>

`clear()` does not shrink the table. It nulls every slot, sets `size = 0`, bumps `modCount` and
keeps both the `Node[]` and the `threshold`. Five million entries at load factor 0.75 means a
`1 << 23` = 8,388,608-slot array, which is 32 MB of references under compressed oops, retained
forever. It also makes iteration of the now-empty map O(capacity). The only fix is to replace the
map object — `map = HashMap.newHashMap(expected)` on Java 19+ — and let the old array be collected.

</details>

**Q5.** `EnumSet.of(Colour.RED).retainAll(someOtherEnumTypeSet)` — what happens?

<details><summary>Answer</summary>

It silently empties the set. The bulk fast paths require the argument to be a `RegularEnumSet` of
the same element type; on a mismatch each operation degrades differently — `addAll` throws
`ClassCastException`, `removeAll` returns `false` and changes nothing, `containsAll` reduces to
`arg.isEmpty()`, and `retainAll` clears the receiver, because "keep only elements also in the
argument" is vacuously satisfied by nothing. The silent one is the dangerous one.

</details>

**Q6.** Which is the safer default for a getter that returns an internal list, and why:
`Collections.unmodifiableList(field)` or `List.copyOf(field)`?

<details><summary>Answer</summary>

`List.copyOf(field)` in almost every case. The wrapper is O(1) but stays live, so the caller sees
your later mutations — including a mutation halfway through their own iteration, which throws CME
in *their* code. The copy is O(n) and two arrays, but it is an independent snapshot that also
rejects nulls. Return the wrapper only when the caller is *meant* to track updates, and return the
field directly when it is already immutable. Either way, both are shallow — deep immutability needs
an immutable element type.

</details>

---

**Leaves covered:** 5.1.23, 5.1.29, 5.1.30, 5.1.32 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 587
