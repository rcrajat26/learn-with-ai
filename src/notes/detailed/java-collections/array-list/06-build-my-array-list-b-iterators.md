# 02 Java Collections — `ArrayList` — INTERNALS (§4.1 `MyArrayList<E>` — the fail-fast iterators)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [array-list/05-build-my-array-list.md](05-build-my-array-list.md) · Next: [array-list/07-build-my-array-list-c-sublist-and-equality.md](07-build-my-array-list-c-sublist-and-equality.md)

Part two of four. [05](05-build-my-array-list.md) built the storage core; this file adds the two nested iterators. The complete compiling class is the concatenation of the code blocks in 05 through [08](08-build-my-array-list-d-bulk-sort-spliterator-and-diff.md), in order.

Everything here rests on one field from [05](05-build-my-array-list.md): the inherited `modCount`, bumped by `add`, `add(int,E)`, `remove` and `removeRange`, and pointedly *not* bumped by `set`. Two iterators read it; neither owns it.

---

## The two cursors, side by side

| | `Itr` | `ListItr extends Itr` |
|---|---|---|
| Interface | `Iterator<E>` | `ListIterator<E>` |
| Fields | `cursor`, `lastRet`, `expectedModCount` | inherits all three, adds none |
| Direction | forward only | forward and backward |
| Methods it defines | `hasNext`, `next`, `remove`, `checkForComodification` | `hasPrevious`, `previous`, `nextIndex`, `previousIndex`, `set`, `add` |
| Methods it inherits | — | `hasNext`, `next`, `remove`, `checkForComodification` |
| Can mutate | delete only | delete, replace, insert |
| Resyncs `expectedModCount` | in `remove` | in `remove` (inherited) and `add`; **not** in `set` |
| Created by | `iterator()` | `listIterator()`, `listIterator(int)` |
| Start position | always 0 | any index `0` to `size` inclusive |

`ListItr` adds six methods and zero fields. Everything it does is expressible in terms of the three pieces of state `Itr` already carries, which is why the JDK writes it as a subclass (`java.base/java/util/ArrayList.java`, JDK 21, line 1102) rather than a parallel implementation.

The three fields mean:

- `cursor` — the index of the element `next()` would return. It sits *between* elements; see [D-10](../diagrams/D-10-listiterator-cursor.svg).
- `lastRet` — the index of the element most recently returned by `next()` or `previous()`, or `-1` if there is none. It is the target of `remove` and `set`.
- `expectedModCount` — the value of the list's `modCount` at the moment this iterator last agreed with the list.

---

### Fail-fast `Itr` (4.1.7)

**Mental model.** An iterator is a cursor plus a snapshot of the list's structural version. Every read compares the snapshot to the live counter. It is a tripwire, not a lock — it detects the bug, it does not prevent it.

**Why it exists.** Structurally modifying a list while iterating it produces silently wrong results: skipped elements, or reads past the new end. Java chose to make that loud. `modCount` is incremented by every structural change; the iterator captures it at construction and rechecks it before every read. The alternative designs are a snapshot copy (what `CopyOnWriteArrayList` does — correct, but O(n) per iterator) and a lock (what `Vector` did — correct, and a scalability disaster). Fail-fast costs one `int` per iterator and one comparison per element.

**When it protects you and when it does not.** It fires reliably on `next`, `remove` and `previous` after a structural change made outside the iterator. It does *not* fire when you remove the second-to-last element in a for-each loop, because `hasNext()` is `cursor != size` and after that removal `cursor` happens to equal the new `size`; the loop exits early without calling `next()` again. The result is a silent skip, not an exception. [03-internals-c-views-and-iterators.md](03-internals-c-views-and-iterators.md) has the frame-by-frame walk and [D-31a](../diagrams/D-31a-second-to-last-remove-frame1.svg) the picture. It also gives no guarantee at all under concurrency: `modCount` is a plain non-volatile `int`.

```java
    @Override
    public Iterator<E> iterator() {
        return new Itr();
    }

    private class Itr implements Iterator<E> {
        int cursor;       // index of the next element to return
        int lastRet = -1; // index last returned; -1 if none / already removed
        int expectedModCount = modCount;

        Itr() {
        }

        @Override
        public boolean hasNext() {
            return cursor != size;
        }

        @Override
        public E next() {
            checkForComodification();
            int i = cursor;
            if (i >= size) {
                throw new NoSuchElementException();
            }
            Object[] es = MyArrayList.this.elementData;
            if (i >= es.length) {
                throw new ConcurrentModificationException();
            }
            cursor = i + 1;
            return elementAt(es, lastRet = i);
        }

        @Override
        public void remove() {
            if (lastRet < 0) {
                throw new IllegalStateException();
            }
            checkForComodification();
            try {
                MyArrayList.this.remove(lastRet);
                cursor = lastRet;
                lastRet = -1;
                expectedModCount = modCount;
            } catch (IndexOutOfBoundsException ex) {
                throw new ConcurrentModificationException();
            }
        }

        final void checkForComodification() {
            if (modCount != expectedModCount) {
                throw new ConcurrentModificationException();
            }
        }
    }
```

Four lines carry decisions, and they are the four most-asked lines in the whole class.

**`hasNext()` is `cursor != size`, not `cursor < size`.** Deliberate. Under concurrent shrinkage `cursor` can exceed `size`, and `!=` keeps the loop running one more step into `next()`, where the comodification check fires properly. `<` would exit silently. The tripwire is placed where it can report.

**`if (i >= es.length) throw new ConcurrentModificationException()`** looks redundant — `i < size` was just checked, and `size <= elementData.length` always holds. Under a data race it is not: another thread may have replaced `elementData` with a *shorter* array between the two reads, which is exactly what `trimToSize` does ([07](07-build-my-array-list-c-sublist-and-equality.md)). Without this line the next statement throws `ArrayIndexOutOfBoundsException`, naming a symptom. With it, the caller gets the exception that names the cause.

**`cursor = lastRet` in `remove`.** After deleting the element at `lastRet`, everything to its right slid one position left, so the next unvisited element is now sitting *at* `lastRet`. Setting `cursor = lastRet` is what makes `it.remove()` not skip an element — the single most common hand-rolled-iterator bug.

**`expectedModCount = modCount` in `remove`.** The outer `remove` bumped `modCount`; this resyncs the snapshot so the iterator forgives its own change. That is the entire reason `Iterator.remove()` is legal during iteration and `list.remove()` is not. `lastRet = -1` alongside it enforces one removal per `next` — a second `remove()` throws `IllegalStateException`.

The `try`/`catch (IndexOutOfBoundsException)` wrapper translates a bounds failure into a `ConcurrentModificationException`. `lastRet` was valid when it was set; if the delegated `remove` now finds it out of range, the list shrank underneath the iterator, and that is the honest diagnosis.

**Verified.** Adding to the list inside a for-each throws `ConcurrentModificationException`. Draining `[a, b, c, d]` with `it.remove()` on `"b"` yields `[a, c, d]` — no exception, no skipped element:

```
for-each + add mid-iteration   -> ConcurrentModificationException
Itr.remove drained without CME -> [a, c, d]
```

**Interview:** *Is fail-fast a thread-safety guarantee?* No. `modCount` is a plain non-volatile `int` and the check is documented as best-effort. It catches single-threaded mistakes reliably and concurrent ones only sometimes. For real concurrency use `CopyOnWriteArrayList`, whose iterator is a weakly-consistent snapshot and never throws.

> A fail-fast iterator is a cursor carrying a version snapshot, resynced only by its own mutations, checked on every read — a debugging aid with no thread-safety semantics.

---

### `ListItr` with `previous`, `set` and `add` (4.1.8)

**Mental model.** `ListIterator`'s cursor sits *between* elements, not on one. `nextIndex()` and `previousIndex()` name the two neighbours and always differ by exactly 1. `lastRet` records which neighbour you most recently stepped over, and it is the target of `set` and `remove`.

**Why it exists.** `Iterator` can only delete. `ListIterator` is the interface that lets you rewrite a list *in place* during a single pass — replace, insert, delete, and walk backwards — without index arithmetic and without tripping the fail-fast check. Before it, the alternative was an index loop, which is correct on `ArrayList` and quadratic on `LinkedList`; `ListIterator` is the abstraction that makes one algorithm efficient on both.

**When to reach for it, and when not.** Reach for it when a single pass does more than one kind of edit, or when the edit depends on the previous element. When you only need conditional deletion, `removeIf` is shorter and faster ([08](08-build-my-array-list-d-bulk-sort-spliterator-and-diff.md)). When you only need replacement, `replaceAll` is clearer. When you need neither, a plain for-each is cheaper — `ListItr` allocates an object that a for-each over an array-backed list also allocates, but the extra six methods buy nothing you use.

```java
    @Override
    public ListIterator<E> listIterator() {
        return new ListItr(0);
    }

    @Override
    public ListIterator<E> listIterator(int index) {
        rangeCheckForAdd(index, size);
        return new ListItr(index);
    }

    private class ListItr extends Itr implements ListIterator<E> {
        ListItr(int index) {
            super();
            cursor = index;
        }

        @Override
        public boolean hasPrevious() {
            return cursor != 0;
        }

        @Override
        public int nextIndex() {
            return cursor;
        }

        @Override
        public int previousIndex() {
            return cursor - 1;
        }

        @Override
        public E previous() {
            checkForComodification();
            int i = cursor - 1;
            if (i < 0) {
                throw new NoSuchElementException();
            }
            Object[] es = MyArrayList.this.elementData;
            if (i >= es.length) {
                throw new ConcurrentModificationException();
            }
            cursor = i;
            return elementAt(es, lastRet = i);
        }

        @Override
        public void set(E e) {
            if (lastRet < 0) {
                throw new IllegalStateException();
            }
            checkForComodification();
            MyArrayList.this.set(lastRet, e);
        }

        @Override
        public void add(E e) {
            checkForComodification();
            int i = cursor;
            MyArrayList.this.add(i, e);
            cursor = i + 1;
            lastRet = -1;
            expectedModCount = modCount;
        }
    }

    @Override
    public void forEach(Consumer<? super E> action) {
        Objects.requireNonNull(action);
        final int expectedModCount = modCount;
        final Object[] es = elementData;
        final int s = size;
        for (int i = 0; modCount == expectedModCount && i < s; i++) {
            action.accept(elementAt(es, i));
        }
        if (modCount != expectedModCount) {
            throw new ConcurrentModificationException();
        }
    }
```

`previous()` sets `lastRet = i` and `cursor = i` to the *same* value, whereas `next()` sets `lastRet = i` and `cursor = i + 1`. That asymmetry is the between-elements model made concrete: stepping backwards leaves the cursor on the near side of the element just returned, stepping forwards leaves it on the far side. Both leave `lastRet` pointing at the element itself, so `set` works identically in either direction — and alternating `next()` then `previous()` returns the *same* element twice, which is the documented contract and surprises people.

`set` does not resync `expectedModCount`, and does not need to, because `MyArrayList.set` does not bump `modCount`. `add` does resync, because `MyArrayList.add(int, E)` does.

`add` sets `lastRet = -1`. Insertion is not a traversal, so there is no "last returned element" afterwards, and calling `set` immediately after `add` throws `IllegalStateException`. It also inserts at `cursor` and *then* advances it, so the new element lands behind the cursor and is not returned by a subsequent `next()`. Inserting inside a `while (lit.hasNext())` loop therefore terminates rather than looping forever.

`forEach` is included here because it is the third traversal path and the only one with no iterator object at all. It reads `modCount` in the loop condition rather than calling `checkForComodification`, which lets it exit the loop on interference and throw once, outside the hot path. The JDK does the same at line 1511.

**Verified.** On `[a, c]`, after `next()` then `add("b")`: the list is `[a, b, c]` and `nextIndex()` is `2`. `previous()` then returns `"b"`, and `set("B")` gives `[a, B, c]`. Calling `set` immediately after `add` on a fresh iterator throws `IllegalStateException`:

```
ListItr.add after 'a'         -> [a, b, c] nextIndex=2
ListItr.previous              -> b
ListItr.set on previous       -> [a, B, c]
ListItr.set right after add   -> IllegalStateException
```

**Insight:** every one of `ListItr`'s six methods is arithmetic on `cursor` and `lastRet` plus a delegation to the outer list. The iterator holds no elements and copies nothing; it is twelve bytes of state over a live array.

**Interview:** *What index range does `listIterator(int)` accept?* `0` through `size` inclusive — it is a cursor position, not an element position, so it uses `rangeCheckForAdd` semantics and not `Objects.checkIndex`.

> `ListIterator` is a between-elements cursor whose `lastRet` field names the element just stepped over, making in-place replace, insert and delete legal within a single fail-fast pass.

---

## Pitfalls

### Assuming `it.remove()` and `list.remove()` are interchangeable inside a loop

**Wrong**

```java
MyArrayList<String> l = new MyArrayList<>(List.of("a", "b", "c"));
for (String s : l) {
    if (s.equals("a")) {
        l.add("d");      // structural change behind the iterator's back
    }
}
// ConcurrentModificationException
```

**Right**

```java
var it = l.iterator();
while (it.hasNext()) {
    if (it.next().equals("b")) {
        it.remove();     // resyncs expectedModCount, rewinds cursor
    }
}
// [a, c, d] -- no exception, nothing skipped
```

`Itr.remove()` ends with `expectedModCount = modCount`, forgiving the change it made itself, and `cursor = lastRet`, so the element that slid into the vacated slot is still visited. Nothing outside the iterator can do either.

**Why people believe it:** both calls are spelled `remove`, both act on the same list, and the failure is a runtime exception rather than a compile error — so the distinction never has to be learned until it bites.

### Trusting `hasNext()` to catch a removal you made yourself

**Wrong**

```java
MyArrayList<String> l = new MyArrayList<>(List.of("a", "b", "c"));
for (String s : l) {
    if (s.equals("b")) {   // the second-to-last element
        l.remove(s);
    }
}
System.out.println(l);     // [a, c] -- and NO exception was thrown
```

**Right**

```java
l.removeIf(s -> s.equals("b"));   // single pass, always correct, see file 08
```

After removing the second-to-last element, `size` becomes 2 and `cursor` is already 2, so `hasNext()` — which is `cursor != size` — returns `false` and the loop exits before `next()` can run the comodification check. The removal succeeded; the exception you were relying on to catch the bad pattern never fired. Remove any *other* element and it throws.

**Why people believe it:** the same code throws for every other position, so the pattern looks reliably fail-fast right up until the one case where it silently is not.

### Calling `set` on a `ListIterator` right after `add`

**Wrong**

```java
ListIterator<String> lit = list.listIterator();
lit.add("z");
lit.set("y");        // IllegalStateException -- intent was "insert z, then correct it to y"
```

**Right**

```java
ListIterator<String> lit = list.listIterator();
lit.add("y");        // just insert the value you want
// or, to edit an element you have actually traversed:
lit.next();
lit.set("y");        // legal: lastRet names the element next() returned
```

`add` sets `lastRet = -1` precisely because insertion is not a traversal — there is no "element just stepped over" for `set` to target. The same rule makes `remove()` illegal immediately after `add()`, and illegal twice in a row.

**Why people believe it:** `set` reads like "write to the cursor", but it is defined as "replace the element last returned by `next` or `previous`", and `add` returns nothing.

---

## Cheat sheet

| Item | Value / rule |
|---|---|
| `Itr` state | `cursor`, `lastRet = -1`, `expectedModCount = modCount` at construction |
| `ListItr` state | the same three; adds no fields |
| `hasNext()` | `cursor != size`, never `<` |
| `hasPrevious()` | `cursor != 0` |
| `nextIndex()` / `previousIndex()` | `cursor` / `cursor - 1` |
| `next()` postcondition | `lastRet = i`, `cursor = i + 1` |
| `previous()` postcondition | `lastRet = i`, `cursor = i` (same value) |
| `next()` then `previous()` | returns the same element twice — documented, not a bug |
| `Itr.remove()` postcondition | `cursor = lastRet`, `lastRet = -1`, `expectedModCount = modCount` |
| `ListItr.add` postcondition | `cursor++`, `lastRet = -1`, `expectedModCount = modCount` |
| `ListItr.set` | no `modCount` change — `set` on the list is not structural |
| `remove`/`set` with `lastRet < 0` | `IllegalStateException` |
| Two `remove()` in a row | `IllegalStateException` (the first sets `lastRet = -1`) |
| `listIterator(int)` range | `0` to `size` inclusive (`rangeCheckForAdd`) |
| `next()` past the end | `NoSuchElementException` |
| Shorter `elementData` mid-iteration | `ConcurrentModificationException`, not `AIOOBE` |
| Silent-skip case | removing the second-to-last element in a for-each |
| Thread safety | none; `modCount` is a plain non-volatile `int` |
| `forEach` | no iterator object; checks `modCount` in the loop condition, throws once at the end |

---

## Self-test

**Q1.** `hasNext()` is written `cursor != size`. What breaks with `cursor < size`, and what breaks with `cursor <= size`?

<details><summary>Answer</summary>

With `cursor < size`, a concurrently shrunk list makes `cursor` exceed `size`, the test returns `false`, and the loop exits silently — the caller never learns the list was mutated underneath them, because `next()` is where the comodification check lives and it never runs. `!=` keeps the loop going into `next()`, where the tripwire fires. With `cursor <= size` the loop runs one iteration too many on every well-behaved list and `next()` throws `NoSuchElementException` at the end of every normal traversal. `!=` is the only form that both terminates correctly in the normal case and routes the abnormal case to the code that can diagnose it. What it does *not* fix: removing the second-to-last element leaves `cursor == size` exactly, so the loop exits with no exception and one element unvisited.

</details>

**Q2.** `next()` checks `i >= size` and then separately `i >= elementData.length`. Since `size <= elementData.length` always holds, is the second check dead code?

<details><summary>Answer</summary>

Not under a data race. Between the read of `size` and the read of `elementData`, another thread can replace `elementData` with a shorter array — `trimToSize` does exactly that on a list another thread has shrunk. Without the second check the very next statement throws `ArrayIndexOutOfBoundsException`, which names a symptom and not a cause. With it, the caller gets `ConcurrentModificationException`, which correctly identifies unsynchronised concurrent access. It is defence-in-depth for a case the class does not promise to handle, chosen because the diagnostic value is high and the cost is one comparison against a value already in a register.

</details>

**Q3.** Why does `Itr.remove()` set `cursor = lastRet` rather than leaving `cursor` alone?

<details><summary>Answer</summary>

Because the removal shifted every element right of `lastRet` one position left. Before the removal, `cursor` was `lastRet + 1` and pointed at the next unvisited element; after the shift, that element moved down into index `lastRet`. Leaving `cursor` at `lastRet + 1` would step straight over it, so a loop that removes every element would in fact remove every *other* element — the classic symptom, a list that still contains half its contents after a "remove everything" loop. Setting `cursor = lastRet` makes the next `next()` return the element that slid into the gap. This single line is why `Iterator.remove()` is the only safe way to delete during a manual traversal.

</details>

**Q4.** `ListItr.set` does not update `expectedModCount`, but `ListItr.add` does. Why the asymmetry?

<details><summary>Answer</summary>

Because `MyArrayList.set(int, E)` does not increment `modCount` and `MyArrayList.add(int, E)` does. `modCount` counts *structural* modifications — changes to the size, which invalidate cursors held by other iterators. Replacing an element in place changes nothing about the list's shape, so no iterator's position becomes stale and no counter moves; there is nothing for `set` to resync against. Insertion does change the shape, so the outer `add` bumps `modCount`, and the iterator must resync or its own next `checkForComodification` would fire on a change it made itself. `add` also sets `lastRet = -1`, so an immediately following `set` throws `IllegalStateException`.

</details>

**Q5.** `next()` sets `cursor = i + 1` but `previous()` sets `cursor = i`, where both set `lastRet = i`. Explain the asymmetry, and say what `next()` returns if called right after `previous()`.

<details><summary>Answer</summary>

The cursor is a position *between* elements, not on one. Returning element `i` in the forward direction means stepping over it, leaving the cursor on its far side, at `i + 1`. Returning element `i` in the backward direction also means stepping over it, but the far side is now the near side, at `i`. Both directions leave `lastRet = i` because both just traversed element `i`, which is why `set` and `remove` behave identically after either. The consequence: `previous()` followed by `next()` returns the same element twice, and so does `next()` followed by `previous()`. This is the documented `ListIterator` contract, not a defect — an alternating loop makes no progress, and code that assumes reversing direction skips an element is wrong.

</details>

**Q6.** `ListItr` extends `Itr` and adds six methods but zero fields. What does that tell you about the design, and where would it break down?

<details><summary>Answer</summary>

It tells you that bidirectional traversal, in-place replacement and insertion are all expressible as arithmetic on the same three pieces of state a forward iterator already needs: `cursor`, `lastRet` and `expectedModCount`. `hasPrevious` is `cursor != 0`, `previousIndex` is `cursor - 1`, `set` targets `lastRet`, `add` inserts at `cursor`. Nothing new needs remembering. It would break down for a structure where moving backwards is not O(1) from the forward state — a singly linked list, where a backward step requires a re-walk from the head, which is exactly why `Iterator` and `ListIterator` are separate interfaces and why not every collection offers the latter. `java.util.ArrayList` uses the same subclass structure at line 1102, describing it as an optimised version of `AbstractList.ListItr`.

</details>

**Q7.** What index values does `listIterator(int)` accept, and why is the check different from the one `get` uses?

<details><summary>Answer</summary>

`0` through `size` **inclusive**, enforced by `rangeCheckForAdd`. The argument is a cursor position, not an element position — a cursor at `size` is the legal "just past the last element" position from which `hasNext()` is false and `previous()` returns the last element. `get` uses `Objects.checkIndex(index, size)`, whose upper bound is exclusive, because there is no element at index `size` to read. Passing `size` to `listIterator` is legitimate and common (it is how you set up a reverse traversal); passing `size` to `get` is always an error. Two checks, two ranges, two exception messages, and substituting one for the other silently breaks reverse iteration.

</details>

**Q8.** `Itr.remove()` wraps its delegation in `try { ... } catch (IndexOutOfBoundsException ex) { throw new ConcurrentModificationException(); }`. When can that catch actually fire?

<details><summary>Answer</summary>

Only when the list shrank between the moment `lastRet` was assigned by `next()`/`previous()` and the moment `remove` runs. `checkForComodification` immediately before would normally catch that, since any shrink bumps `modCount` — so in single-threaded code the catch is unreachable. It fires under a data race, where another thread shrinks the list after the comodification check passes and before `MyArrayList.remove(lastRet)` does its `Objects.checkIndex`. Translating the resulting `IndexOutOfBoundsException` into `ConcurrentModificationException` gives the caller the diagnosis that matches reality: the index was valid, the list moved. It is the same defensive translation as the `i >= es.length` check inside `next()`, and it is the reason a racy program gets a comprehensible exception rather than a bounds error on an index it never chose.

</details>

---

**Leaves covered:** 4.1.7–4.1.8 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 423
