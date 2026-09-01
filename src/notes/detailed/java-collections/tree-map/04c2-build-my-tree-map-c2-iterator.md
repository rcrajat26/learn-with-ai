# 02 Java Collections — TreeMap — INTERNALS (§4.6.1, part 5 of 6)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [tree-map/04c-build-my-tree-map-c-navigable-and-iterator.md](04c-build-my-tree-map-c-navigable-and-iterator.md) · Next: [tree-map/04d-build-my-tree-map-d-diff-and-demo.md](04d-build-my-tree-map-d-diff-and-demo.md)

Carries forward `MyTreeMap<K,V>`'s `root`, `size`, `modCount`, the private
static `successor(Entry<K,V> t)`, `getFirstEntry()`/`firstEntry()`, and
`deleteEntry(Entry<K,V> p)` from earlier parts of this series. This file's
one job: the `Iterator<Map.Entry<K,V>>` that walks the tree in key order.

## The fail-fast in-order iterator

**Mental model.** A red-black tree already IS a sorted structure; you don't
need a stack, a Morris-traversal trick, or a snapshot array to walk it in
order. You need exactly one pointer — call it `next` — seeded at the
leftmost node, and one operation to advance it: `successor`, which this
series already built in part 2 (`04b-build-my-tree-map-b-deletion.md`) as
the "leftmost of right subtree, else climb past right-child ancestors"
rule. Iteration is that pointer walk, one hop per `next()` call, plus a
tripwire: a single `int` counter (`modCount`) that every structural
mutator increments, and that the iterator snapshots once at construction
and compares on every `next()`/`remove()`. The tripwire is not a lock — it
does not prevent concurrent mutation, it only detects that one happened
and refuses to keep walking a structure that may have shifted underneath
it.

**Why it exists.** `Map` (and by extension every `NavigableMap`) exposes
iteration through `entrySet()`/`keySet()`/`values()`, and this project has
already documented the same convention twice: the `ArrayList` iterator
notes and the `HashMap` iterator notes both establish "fail-fast on
structural modification via a `modCount` comparison, best-effort, not a
concurrency guarantee." `TreeMap` does not get a special exemption — a
`TreeMap` iterator that silently produced garbage (or looped forever)
after a concurrent `put` would be a worse citizen than one that throws
`ConcurrentModificationException` the moment it notices. Building this
iterator is also what makes `entryIterator()` (and, in the real JDK,
`entrySet().iterator()`) possible at all — without it there is no
supported way to walk a `MyTreeMap` in sorted order other than repeatedly
calling `higherEntry`, which is correct but reissues a full O(log n)
descent per step instead of amortized O(1).

**When it fires, when it doesn't.**

- Fires: any direct structural call on the map — `put` with a new key,
  `remove`, `clear` — made *while* an iterator is live and before that
  iterator's next `next()`/`remove()` call. Each of those bumps `modCount`
  without the iterator's knowledge, so the comparison fails.
- Does not fire: the iterator's own `remove()`. It performs the exact same
  `deleteEntry` structural change, but it immediately resynchronizes
  `expectedModCount` to the new `modCount` afterward — the mutation is
  sanctioned and accounted for, not concurrent.
- Does not fire: calling `setValue` on the `Map.Entry` handed back by
  `next()`. `setValue` on a live node changes a value in place; it is not
  a structural change (no rotation, no re-linking, no size change), so it
  never touches `modCount` and never trips the check.

**How it works.**

```java
final class EntryIterator implements Iterator<Map.Entry<K,V>> {
    Entry<K,V> next;
    Entry<K,V> lastReturned;
    int expectedModCount;

    EntryIterator() {
        next = getFirstEntry(root);
        expectedModCount = modCount;
    }

    @Override
    public boolean hasNext() {
        return next != null;
    }

    @Override
    public Map.Entry<K,V> next() {
        if (next == null) {
            throw new NoSuchElementException();
        }
        if (modCount != expectedModCount) {
            throw new ConcurrentModificationException();
        }
        Entry<K,V> e = next;
        lastReturned = e;
        next = successor(e);
        return e; // live node: setValue on it mutates the backing map
    }

    @Override
    public void remove() {
        if (lastReturned == null) {
            throw new IllegalStateException();
        }
        if (modCount != expectedModCount) {
            throw new ConcurrentModificationException();
        }
        // deleteEntry, in the two-children case, overwrites lastReturned's
        // key/value with its successor's and unlinks the successor node
        // instead. Resolve `next` from state that is still trustworthy
        // *before* that happens, or the walk lands on the wrong key.
        if (lastReturned.left != null && lastReturned.right != null) {
            next = lastReturned;
        }
        deleteEntry(lastReturned);
        expectedModCount = modCount;
        lastReturned = null;
    }
}

public Iterator<Map.Entry<K,V>> entryIterator() {
    return new EntryIterator();
}
```

Exposed as a direct `iterator()`-shaped method (`entryIterator()`) rather
than a full `AbstractSet`-backed `entrySet()`: the real `TreeMap` wraps
this exact iterator inside an `entrySet()` view, but building that view
(size delegation, `contains`, `remove(Object)` by key lookup, etc.) is
orthogonal to the iterator itself and out of scope for this narrow file —
`entryIterator()` gives every behavior this file is responsible for
(in-order walk, fail-fast, iterator-`remove()`) without the extra
scaffolding.

`hasNext()` is deliberately the one method that never touches `modCount`.
It answers "is `next` non-null," full stop — a pure query, side-effect-free
and exception-free, so a caller can always ask "is there more" safely even
against a map known to be mid-corruption. Only the two methods that
*advance or mutate* state — `next()` and `remove()` — perform the check.

**No diagram** — this is a single forward-pointer walk over the same tree
shape already diagrammed in earlier parts of this series; nothing new to
draw.

**Minimal runnable example.** Happy path — in-order print of a small tree
built by inserting `{7, 3, 12, 5, 20, 10}`:

```java
MyTreeMap<Integer,String> m = new MyTreeMap<>();
for (int k : new int[]{7, 3, 12, 5, 20, 10}) {
    m.put(k, "v" + k);
}

Iterator<Map.Entry<Integer,String>> it = m.entryIterator();
while (it.hasNext()) {
    System.out.print(it.next().getKey() + " ");
}
// prints: 3 5 7 10 12 20
```

The printed order is the sorted key order regardless of insertion order or
tree shape — that's the entire point of an in-order walk over a BST.

Separate snippet — mutating the map directly (not through the iterator)
mid-iteration, and printing the real thrown exception:

```java
Iterator<Map.Entry<Integer,String>> it2 = m.entryIterator();
System.out.println(it2.next());   // 3=v3 -- expectedModCount captured at construction
m.put(99, "v99");                 // structural change on the map: modCount++ , iterator not told
try {
    it2.next();                   // 5=v5 was expected; throws instead
} catch (ConcurrentModificationException cme) {
    System.out.println("caught: " + cme);
    // caught: java.util.ConcurrentModificationException
}
```

Honest note on provenance: this trace is hand-derived from the code above,
not from an executed JVM in this authoring session — but it follows
directly and deterministically from `deleteEntry`/`put` bumping `modCount`
and `EntryIterator.next()`'s comparison against `expectedModCount`, both
shown verbatim above.

**The gotcha.** Calling `remove()` before any `next()` call, or twice in a
row with no `next()` in between, must throw `IllegalStateException` — not
NPE, not a silent no-op:

```java
Iterator<Map.Entry<Integer,String>> it3 = m.entryIterator();
it3.next();
it3.remove();
try {
    it3.remove(); // lastReturned was cleared to null by the first remove()
} catch (IllegalStateException ise) {
    System.out.println("caught: " + ise);
    // caught: java.lang.IllegalStateException
}
```

The guard is `lastReturned == null`, checked as the very first line of
`remove()`, before `deleteEntry` is ever reached — `deleteEntry(null)`
would NPE deep inside tree logic instead of failing cleanly at the API
boundary, which is exactly the wrong place for a usage-error diagnostic to
surface.

> **Definition.** The `MyTreeMap` in-order iterator seeds a pointer at the
> tree's leftmost node and advances it one `successor()` hop per `next()`
> call, giving amortized O(1)-per-step sorted-order traversal; it is
> fail-fast, comparing a snapshotted `expectedModCount` against the live
> `modCount` on every `next()`/`remove()`, throwing
> `ConcurrentModificationException` on external structural drift while
> resynchronizing after its own sanctioned `remove()`.

## Pitfalls

- **Wrong:** calling `it.remove()` a second time immediately after the
  first, expecting it to just be a no-op or to remove "the next one
  anyway." **Right:** guard on `lastReturned == null` and throw
  `IllegalStateException`. People believe `remove()` is idempotent because
  many "delete" operations elsewhere in Java are (`Set.remove(x)` on an
  absent `x` just returns `false`); the iterator's `remove()` is a
  stateful command tied to "the entry `next()` most recently handed back,"
  and once consumed there is nothing left to reissue against.
- **Wrong:** letting the iterator's own `remove()` skip resynchronizing
  `expectedModCount`, reasoning that "the iterator already knows what it
  did, so the check is unnecessary." **Right:** set `expectedModCount =
  modCount` as the last step of `remove()`, right after `deleteEntry`
  returns. People believe the check exists purely to catch bugs elsewhere,
  so their own call "doesn't count" — but the check has no way to
  distinguish "the iterator changed `modCount`" from "someone else did";
  skip the resync and the very next `next()` call throws
  `ConcurrentModificationException` against the iterator's *own* legal
  deletion, a self-inflicted false positive that looks like a JDK bug
  until traced back to the missing resync line.

## Cheat sheet

| Aspect | Behavior |
|---|---|
| Seed | `next = getFirstEntry(root)` (leftmost node) in the constructor |
| Advance | `next = successor(e)` inside `next()`, one hop per call |
| `hasNext()` | `next != null`; never checks `modCount`; never throws |
| `next()` throws | `NoSuchElementException` if exhausted; `ConcurrentModificationException` if `modCount != expectedModCount` |
| `remove()` throws | `IllegalStateException` if `lastReturned == null`; `ConcurrentModificationException` if drifted |
| `remove()` resync | `expectedModCount = modCount` after `deleteEntry`, so the iterator's own mutation is never mistaken for external mutation |
| Two-children `remove()` case | set `next = lastReturned` *before* `deleteEntry`, since `deleteEntry` overwrites `lastReturned`'s contents from its successor rather than unlinking it |
| Exposure shape | `entryIterator()` returning `Iterator<Map.Entry<K,V>>` directly (no `entrySet()` wrapper built in this file) |
| Cost per step | O(log n) worst case, amortized O(1) across a full traversal |

## Self-test

1. **Why does `hasNext()` never check `modCount`, while `next()` and
   `remove()` both do?**
   Fold: `hasNext()` is a pure query — it must stay callable and
   exception-free no matter what state the map is in, so a caller can
   always safely ask "is there more" first; only the two methods that
   advance the cursor or mutate the tree need the fail-fast guard, since
   those are the calls whose result would otherwise silently be wrong.

2. **What throws if `remove()` is called immediately after constructing
   the iterator, before any `next()`?**
   Fold: `IllegalStateException`, because `lastReturned` starts `null` and
   the very first line of `remove()` checks for that before touching
   `deleteEntry`.

3. **Why is `expectedModCount` reassigned inside `remove()` but nowhere
   else in the class?**
   Fold: `remove()` is the only structural mutation the iterator itself
   performs; resyncing there means the check only ever fires for
   mutations the iterator did not cause, which is the entire point of the
   mechanism — without the resync, the iterator's own legal delete would
   trip its own next check.

4. **In the two-children delete case inside the iterator's `remove()`,
   why is `next` set to `lastReturned` before calling `deleteEntry`,
   rather than computed as `successor(lastReturned)` after?**
   Fold: `deleteEntry` handles two children by copying the successor's
   key/value into `lastReturned` and physically unlinking the successor
   node instead — so after the call, `lastReturned` is still live but has
   different contents, and calling `successor` on it afterward would walk
   from the wrong key. Capturing `next = lastReturned` beforehand means
   the walk resumes from the node that is about to inherit the correct
   next value, which was already true of the pre-mutation tree shape.

5. **Does calling `entry.setValue(v)` on an entry returned by this
   iterator's `next()` trip `ConcurrentModificationException` on the
   following `next()` call?**
   Fold: no — `setValue` on the live node mutates a value in place and
   never touches `modCount`, because it is not a structural change (no
   rotation, no re-link, no size delta); only structural mutators
   (`put` on a new key, `remove`, `deleteEntry`) increment `modCount`.

6. **Why is `ConcurrentModificationException` described as "best-effort,"
   not a correctness guarantee?**
   Fold: the detector is a single non-volatile `int` compared at a few
   checkpoints; a sufficiently adversarial concurrent writer could
   interleave mutations so that `modCount` happens to match at the moment
   of comparison, evading detection entirely — the JDK's own Javadoc for
   `ArrayList`, `HashMap`, and `TreeMap` all state this in nearly identical
   wording, and this project's iterator matches that same bar deliberately
   rather than trying to exceed it.

7. **Why does this file expose `entryIterator()` directly instead of
   building a full `entrySet()`?**
   Fold: the iterator (seed, advance, fail-fast, iterator-`remove()`) is
   the complete scope of this narrow file; `entrySet()` needs an
   `AbstractSet`-shaped wrapper with its own `size()`, `contains()`, and
   `remove(Object)` delegating to key lookup, which is orthogonal
   plumbing this file's leaf does not require to demonstrate the
   traversal and fail-fast behavior.

8. **What is the asymptotic cost of iterating the entire map once, and
   why is it not `O(n log n)`?**
   Fold: `O(n)` total, because although each individual `successor` call
   is `O(log n)` worst case, the *amortized* cost across a full in-order
   traversal is `O(1)` per step — every edge in the tree is crossed at
   most twice over the whole walk, the same amortization argument used for
   in-order traversal of any binary tree regardless of balance.

---

**Leaves covered:** 4.6.1 (part 5 of 6) (1 leaf, shared across 6 files)
**Leaves deferred:** none — 4.6.1 concludes in 04d
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 316
