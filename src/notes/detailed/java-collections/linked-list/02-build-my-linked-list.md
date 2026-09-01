# 02 Java Collections — `LinkedList` — INTERNALS (§4.2 `MyLinkedList<E>` — nodes, pointer surgery and the deque surface)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [linked-list/01-internals.md](01-internals.md) · Next: [linked-list/03-build-my-linked-list-b-iterators-and-benchmark.md](03-build-my-linked-list-b-iterators-and-benchmark.md)

The class is presented in two parts: the complete compiled source of `MyLinkedList<E>` is the concatenation, in printed order, of every fenced `java` block in this file — except the standalone `GcProbe` class and the two blocks under `## Pitfalls` — followed by every fenced `java` block in `03-build-my-linked-list-b-iterators-and-benchmark.md` up to and including `reversed()`. Nothing is elided; `javac -Xlint:all` accepts that concatenation with zero warnings on JDK 21.0.7.

## The map: state, and who owns it

`java.util.LinkedList` is three fields and a node class; everything else is navigation over it.

| Field | Ours | `java.util.LinkedList` | Purpose |
|---|---|---|---|
| `size` | `private int size = 0` | `transient int size = 0` (`java.base/java/util/LinkedList.java`, JDK 21, line 94) | O(1) `size()`; also the pivot for `node(int)` |
| `first` | `private Node<E> first` | `transient Node<E> first` (line 99) | head sentinel-free pointer; `null` iff empty |
| `last` | `private Node<E> last` | `transient Node<E> last` (line 104) | tail pointer; makes `addLast` O(1) |
| `modCount` | inherited from `AbstractList` | inherited from `AbstractList` | fail-fast iteration |
| `Node.item` / `prev` / `next` | `E` / `Node<E>` / `Node<E>` | same (line 981) | payload plus the two links |

The JDK's fields are `transient` because `LinkedList` hand-rolls `writeObject`/`readObject`, serialising the elements rather than the node graph; ours are plain `private`, which is the first row of the diff table in file 03. There are **no sentinel nodes**: `first == null` is the empty test, and every link/unlink method pays with an explicit `if (pred == null)` or `if (next == null)` branch — a sentinel-headed design deletes those branches at the cost of one permanently-allocated node, and the JDK chose branches.

## Choosing the base class

`MyLinkedList<E> extends AbstractSequentialList<E> implements List<E>, Deque<E>` — the same declaration `java.util.LinkedList` uses, minus `Cloneable, Serializable`. `AbstractSequentialList` is the honest base. As `../framework/08-abstract-skeletons.md` in this set works through, `AbstractList` implements its bulk operations on top of `get(int)`, so an `AbstractList`-backed linked list makes `addAll` or `equals` an O(n²) pointer chase. `AbstractSequentialList` inverts that: it builds everything on the single abstract `listIterator(int)`, so each operation walks the chain once. What we inherit rather than write:

| Inherited from | Methods we do not write |
|---|---|
| `AbstractSequentialList` | `get(int)`, `set(int, E)`, `add(int, E)`, `remove(int)`, `addAll(int, Collection)`, `iterator()` |
| `AbstractList` | `indexOf`, `lastIndexOf`, `equals`, `hashCode`, `subList`, `listIterator()`, `clear()`, `modCount` itself |
| `AbstractCollection` | `contains`, `isEmpty`, `addAll(Collection)`, `removeAll`, `retainAll`, `toArray()`, `toArray(T[])`, `toString` |
| `Collection`/`Iterable` defaults | `stream`, `parallelStream`, `forEach`, `removeIf`, `spliterator()` |

**Insight:** every one of those inherited methods routes through `listIterator(int)`, which routes through `node(int)`. Implement `size()` and `listIterator(int)` honestly and a hundred lines of `List` behaviour appear at exactly the cost the mechanism deserves. The inherited `spliterator()` is the exception — a real cost, priced in file 03's diff table.

### The state and the node — part 1 of the class

```java
import java.util.AbstractSequentialList;
import java.util.Collection;
import java.util.ConcurrentModificationException;
import java.util.Deque;
import java.util.Iterator;
import java.util.List;
import java.util.ListIterator;
import java.util.NoSuchElementException;
import java.util.Objects;
import java.util.function.Consumer;

public class MyLinkedList<E> extends AbstractSequentialList<E>
        implements List<E>, Deque<E> {

    private static class Node<E> {
        E item;
        Node<E> next;
        Node<E> prev;

        Node(Node<E> prev, E element, Node<E> next) {
            this.item = element;
            this.next = next;
            this.prev = prev;
        }
    }

    private int size = 0;
    private Node<E> first;
    private Node<E> last;

    public MyLinkedList() {
    }

    public MyLinkedList(Collection<? extends E> c) {
        for (E e : c)
            linkLast(e);
    }

    @Override
    public int size() {
        return size;
    }
```

**Version trap.** `List` and `Deque` both extend `SequencedCollection` and both declare `reversed()` with their own return type, so a class implementing both **will not compile** unless it overrides `reversed()` with a common subtype — `javac` reports `types Deque<E> and List<E> are incompatible; both define reversed(), but with unrelated return types`. A JDK 21 (JEP 431) problem that did not exist in 17. `java.util.LinkedList` solves it at line 1285 by returning a `LinkedList<E>` **view**; ours returns a `MyLinkedList<E>` **copy**, printed in file 03 and priced in the diff table.

> **Definition.** `MyLinkedList<E>` is a sentinel-free doubly-linked list holding `first`, `last` and `size`, whose `List` surface is generated by `AbstractSequentialList` from a single `listIterator(int)`.

## Pointer surgery: `linkFirst`, `linkLast`, `linkBefore`, `unlink` [4.2.2]

**Mental model.** Four methods, one shape: grab the neighbour pointers into locals *first*, allocate or drop the node, then write the three or four fields back in an order where nothing is read after it has been overwritten. The `if` in each method exists solely because there is no sentinel — the neighbour on one side may be `null`, and then the list's own `first`/`last` field is what needs updating instead of a node field. **Why it exists:** splicing into an array moves O(n) bytes; splicing into a chain writes a bounded number of references — four for a mid-list insert (`newNode.prev`, `newNode.next`, `pred.next`, `succ.prev`) — and that count does not grow with `n`. That is the entire performance case for `LinkedList`, and file 03 measures whether it survives contact with the cost of *finding* the splice point.

```java
    private void linkFirst(E e) {
        final Node<E> f = first;
        final Node<E> newNode = new Node<>(null, e, f);
        first = newNode;
        if (f == null)
            last = newNode;
        else
            f.prev = newNode;
        size++;
        modCount++;
    }

    private void linkLast(E e) {
        final Node<E> l = last;
        final Node<E> newNode = new Node<>(l, e, null);
        last = newNode;
        if (l == null)
            first = newNode;
        else
            l.next = newNode;
        size++;
        modCount++;
    }

    private void linkBefore(E e, Node<E> succ) {
        final Node<E> pred = succ.prev;
        final Node<E> newNode = new Node<>(pred, e, succ);
        succ.prev = newNode;
        if (pred == null)
            first = newNode;
        else
            pred.next = newNode;
        size++;
        modCount++;
    }

    private E unlinkFirst(Node<E> f) {
        final E element = f.item;
        final Node<E> next = f.next;
        f.item = null;
        f.next = null; // help GC
        first = next;
        if (next == null)
            last = null;
        else
            next.prev = null;
        size--;
        modCount++;
        return element;
    }

    private E unlinkLast(Node<E> l) {
        final E element = l.item;
        final Node<E> prev = l.prev;
        l.item = null;
        l.prev = null; // help GC
        last = prev;
        if (prev == null)
            first = null;
        else
            prev.next = null;
        size--;
        modCount++;
        return element;
    }

    private E unlink(Node<E> x) {
        final E element = x.item;
        final Node<E> next = x.next;
        final Node<E> prev = x.prev;

        if (prev == null) {
            first = next;
        } else {
            prev.next = next;
            x.prev = null; // help GC
        }

        if (next == null) {
            last = prev;
        } else {
            next.prev = prev;
            x.next = null; // help GC
        }

        x.item = null; // help GC
        size--;
        modCount++;
        return element;
    }
```

### The lines that carry a decision

**`modCount++` in every mutator, including the link methods** — not just the removals. An iterator parked mid-list is invalidated by an insert elsewhere just as surely as by a removal, because its `nextIndex` no longer matches reality.

**`unlink` nulls `item` unconditionally, but nulls `prev` and `next` only inside the `else` branches.** `x.prev = null` sits in the `else` of `if (prev == null)`: if `prev` *was* null the field already holds null and the assignment would be a wasted write on the hottest removal path. Same for `x.next`. The repeated summary "unlink nulls all three fields" is right about the *outcome* — only because the skipped branches were already null — and wrong about the mechanism. `java.base/java/util/LinkedList.java`, JDK 21, line 220 is the authority.

**`unlinkFirst` nulls `f.item` and `f.next` but never `f.prev`** (line 182) — `f.prev` is already null because `f` was the head; `unlinkLast` is the mirror (line 201). That is why the ends get their own methods.

### Proving the GC nulling actually matters [PROVE]

The nulling only does anything if something still points at the unlinked node, and that something is real: a `ListIterator` holds `lastReturned`, and `java.util.LinkedList.clear()` (line 459) nulls `item`, `next` and `prev` on every node in a loop for exactly this reason, with a comment naming "a reachable Iterator". Without the nulls, one stale node reference pins its payload *and the entire remaining tail* through `next`. `GcProbe` below is a standalone class compiled and run alongside `MyLinkedList` — not part of it: it unlinks two head nodes, one with the nulling and one without, keeps a stale reference to each, and watches two `WeakReference`s.

```java
import java.lang.ref.WeakReference;
final class GcProbe {

    private static final class Cell {
        String item;
        Cell next;
        Cell(String item, Cell next) { this.item = item; this.next = next; }
    }

    private static final Cell[] staleReferences = new Cell[2];

    /** Builds head->tail, "unlinks" head, keeps a stale reference to it, returns weak refs. */
    private static WeakReference<?>[] unlinkAndProbe(String tag, boolean nulling) {
        Cell head = new Cell(new String(tag + "-item"), new Cell(new String(tag + "-tail"), null));
        WeakReference<?>[] refs = { new WeakReference<>(head.item), new WeakReference<>(head.next.item) };
        if (nulling) {          // what MyLinkedList.unlinkFirst does
            head.item = null;
            head.next = null;
        }
        staleReferences[nulling ? 1 : 0] = head;   // the stale reference that makes nulling matter
        return refs;
    }

    public static void main(String[] args) throws InterruptedException {
        WeakReference<?>[] lazy = unlinkAndProbe("lazy", false);
        WeakReference<?>[] kept = unlinkAndProbe("kept", true);
        for (int i = 0; i < 3; i++) { System.gc(); Thread.sleep(120); }
        System.out.println("stale ref held to both unlinked nodes; System.gc() is only a hint");
        System.out.printf("  lazy   node: item alive=%b  tail payload alive=%b%n",
                lazy[0].get() != null, lazy[1].get() != null);
        System.out.printf("  nulled node: item alive=%b  tail payload alive=%b%n",
                kept[0].get() != null, kept[1].get() != null);
        System.out.println("  stale refs still held: " + (staleReferences[0] != null && staleReferences[1] != null));
    }
}
```

Actual output, JDK 21.0.7+8-LTS-245, macOS aarch64 (Apple M4 Pro), default G1:
```
stale ref held to both unlinked nodes; System.gc() is only a hint
  lazy   node: item alive=true  tail payload alive=true
  nulled node: item alive=false  tail payload alive=false
  stale refs still held: true
```
`System.gc()` is a hint, not a command, and `WeakReference` clearing is not guaranteed by the JLS at any particular moment — this run is evidence, not proof. But the asymmetry is the point: the *only* difference between the two halves is the two field writes, and the lazy node's payload plus its whole tail stayed reachable while the nulled one's did not.

> **Definition.** `unlink` splices a node out by rewiring its two neighbours, then nulls `item` unconditionally and nulls `prev`/`next` only on the sides that had a neighbour, so a stale reference to the dead node cannot pin the payload or the rest of the chain.

## `node(int)` and the bidirectional shortcut [4.2.3]

**Mental model.** The list has two entry points: ask for index 3 of 100 and it walks forward from `first`, ask for index 97 and it walks backward from `last`. The worst case is the middle at **⌊(n−1)/2⌋** hops — a constant factor of two off the naive walk, never an asymptotic improvement. Count it on a size-10 list: the backward branch is `for (int i = size - 1; i > index; i--)`, so `get(9)` is 0 hops and `get(8)` is **1** hop. The worst case is **4** hops, reached twice — at index 4 through the forward branch (`4 < 10 >> 1`, so `i = 0, 1, 2, 3`) and at index 5 through the backward branch (`i = 9, 8, 7, 6`). Four, not `size / 2` = 5, because each walk starts *at* an end node rather than one step outside it.

```java
    private Node<E> node(int index) {
        if (index < (size >> 1)) {
            Node<E> x = first;
            for (int i = 0; i < index; i++)
                x = x.next;
            return x;
        } else {
            Node<E> x = last;
            for (int i = size - 1; i > index; i--)
                x = x.prev;
            return x;
        }
    }

    private void checkPositionIndex(int index) {
        if (index < 0 || index > size)
            throw new IndexOutOfBoundsException("Index: " + index + ", Size: " + size);
    }
```

**Why `size >> 1` and not `size / 2`.** For a non-negative `int` they compute the same value, but `/ 2` on a *possibly* negative int must round toward zero, so `javac` emits an extra correction sequence that the shift form does not need. `>> 1` also states the intent: a midpoint pivot on a count that cannot be negative. The JDK writes `>>` at line 577. Copy the habit for midpoints, but note the counter-case — binary search uses `(lo + hi) >>> 1`, the *unsigned* shift, because `lo + hi` genuinely can overflow into negative territory. `size >> 1` cannot.

**Insight:** the shortcut is why `LinkedList.get(size - 1)` is cheap and `get(size / 2)` is the O(n) worst case; benchmarks that only probe index 0 or `size-1` are measuring the shortcut, not the list. Verified at both ends and at the pivot on an eight-element list (`0..7`, so `size >> 1 == 4`):
```
7  node(1) forward branch  get(1)  = 1
8  node(6) backward branch get(6)  = 6
9  size>>1 boundary        get(4)  = 4
```

Index 4 takes the `else` branch — `4 < (8 >> 1)` is `4 < 4`, false — so the pivot element itself is reached backward. **Interview:** "`LinkedList.get(i)` is O(n) — is the halving worth anything?" Only as a constant factor of 2, and only when the access pattern is not sequential; a `for (int i = 0; i < list.size(); i++) list.get(i)` loop stays Θ(n²), the halving just makes it n²/4.

> **Definition.** `node(int)` returns the node at an element index by walking from `first` when `index < (size >> 1)` and from `last` otherwise, giving ⌊(n−1)/2⌋ worst-case hops.

## The `Deque` surface [4.2.4]

**Mental model.** Every `Deque` method translates a name into one of the four link/unlink primitives plus a choice of what to do when the list is empty. The whole API surface is three empty-policies crossed with head/tail:

| Intent | Empty behaviour | Head | Tail |
|---|---|---|---|
| Insert | never fails (unbounded) | `addFirst`, `offerFirst`, `push` | `addLast`, `offerLast`, `add`, `offer` |
| Remove | throw `NoSuchElementException` | `removeFirst`, `pop`, `remove()` | `removeLast` |
| Remove | return `null` | `pollFirst`, `poll` | `pollLast` |
| Inspect | throw `NoSuchElementException` | `getFirst`, `element` | `getLast` |
| Inspect | return `null` | `peekFirst`, `peek` | `peekLast` |

Read the aliases carefully: `push`/`pop`/`peek` are all **head** operations, so `peek()` returns the *most recently pushed* element; `add`/`offer` are **tail** operations, because `Queue` semantics won. Mixing the two vocabularies in one block is how LIFO/FIFO bugs get written.

**Why it exists.** `Stack` extends `Vector`, is synchronized, and carries an `Enumeration`-era API; the `Deque` Javadoc says outright to prefer `Deque` over `Stack`. `LinkedList` gained `Deque` in Java 6 so one class could serve as list, queue and stack. **When not to reach for it:** for a pure stack or queue with no `null` elements and no index access, `ArrayDeque` wins decisively — contiguous storage, no per-element node allocation, far better locality. `MyLinkedList`'s only structural advantages are `null` tolerance and O(1) splice at a held cursor.

```java
    // ---- Deque: head/tail insertion ----

    @Override
    public void addFirst(E e) {
        linkFirst(e);
    }

    @Override
    public void addLast(E e) {
        linkLast(e);
    }

    @Override
    public boolean offerFirst(E e) {
        linkFirst(e);
        return true;
    }

    @Override
    public boolean offerLast(E e) {
        linkLast(e);
        return true;
    }

    @Override
    public boolean add(E e) {
        linkLast(e);
        return true;
    }

    @Override
    public boolean offer(E e) {
        return add(e);
    }

    @Override
    public void push(E e) {
        addFirst(e);
    }

    // ---- Deque: head/tail removal ----

    @Override
    public E pollFirst() {
        final Node<E> f = first;
        return (f == null) ? null : unlinkFirst(f);
    }

    @Override
    public E pollLast() {
        final Node<E> l = last;
        return (l == null) ? null : unlinkLast(l);
    }

    @Override
    public E poll() {
        return pollFirst();
    }

    @Override
    public E removeFirst() {
        final Node<E> f = first;
        if (f == null)
            throw new NoSuchElementException();
        return unlinkFirst(f);
    }

    @Override
    public E removeLast() {
        final Node<E> l = last;
        if (l == null)
            throw new NoSuchElementException();
        return unlinkLast(l);
    }

    @Override
    public E remove() {
        return removeFirst();
    }

    @Override
    public E pop() {
        return removeFirst();
    }

    // ---- Deque: inspection ----

    @Override
    public E peekFirst() {
        final Node<E> f = first;
        return (f == null) ? null : f.item;
    }

    @Override
    public E peekLast() {
        final Node<E> l = last;
        return (l == null) ? null : l.item;
    }

    @Override
    public E peek() {
        return peekFirst();
    }

    @Override
    public E getFirst() {
        final Node<E> f = first;
        if (f == null)
            throw new NoSuchElementException();
        return f.item;
    }

    @Override
    public E getLast() {
        final Node<E> l = last;
        if (l == null)
            throw new NoSuchElementException();
        return l.item;
    }

    @Override
    public E element() {
        return getFirst();
    }

    // ---- Deque: occurrence removal ----

    @Override
    public boolean removeFirstOccurrence(Object o) {
        for (Node<E> x = first; x != null; x = x.next) {
            if (Objects.equals(o, x.item)) {
                unlink(x);
                return true;
            }
        }
        return false;
    }

    @Override
    public boolean removeLastOccurrence(Object o) {
        for (Node<E> x = last; x != null; x = x.prev) {
            if (Objects.equals(o, x.item)) {
                unlink(x);
                return true;
            }
        }
        return false;
    }

    @Override
    public boolean remove(Object o) {
        return removeFirstOccurrence(o);
    }
```

### What carries a decision here

**`remove()` and `remove(Object)` are different methods with different empty-policies.** `Deque.remove()` is the no-arg head removal that throws; `Collection.remove(Object)` scans and returns `boolean`, and `remove(null)` binds to the `Object` overload — a classic JDK overload trap. **`removeFirstOccurrence` uses `Objects.equals(o, x.item)`, not `o.equals(x.item)`**, which is what makes `remove(null)` work on a list that permits nulls.

**We inherit `clear()` rather than write it, and that costs something.** `AbstractList.clear()` loops the iterator calling `remove()`, so it does unlink each node — correct, and the nulling happens. `java.util.LinkedList` overrides it (line 459) with a direct walk that nulls `item`, `next` and `prev` on every node, avoiding n `modCount` bumps and n `unlink` branch sequences. Ours is correct but slower by a constant factor.

### Verified behaviour — real output from the exercise `main`, JDK 21.0.7+8-LTS-245
```
1  after addFirst/addLast on empty : [A, B, C] size=3
2  linkBefore at midpoint          : [A, B, B2, C]
3  unlink first  -> A  list=[B, B2, C]
4  unlink last   -> C  list=[B, B2]
5  before middle unlink            : [B, B2, X, Y]
6  remove("B2") middle -> true  list=[B, X, Y]
10 nulls accepted                  : [null, null, x] contains(null)=true
11 ArrayDeque.addLast(null)        : NullPointerException
12 push/peek                       : [top, middle, bottom] peek=top
13 pop order                       : top,middle,bottom
14 empty pollFirst/pollLast        : null,null
15 empty removeFirst               : NoSuchElementException
```

Lines 10 and 11 are the same call on two `Deque` implementations: `MyLinkedList` accepts `null`, `ArrayDeque` rejects it because it uses `null` in its backing array as the "no element here" marker and cannot distinguish a stored null from an empty slot. **Pitfall:** `peek()` returning `null` is therefore ambiguous on a null-permitting deque — "empty" or "the head element is null". `ArrayDeque` buys an unambiguous `peek()` by banning nulls. If you store nulls, test emptiness with `isEmpty()`, never `peek() == null`.

> **Definition.** The `Deque` surface is fifteen names over four primitives: head-vs-tail crossed with throw-on-empty, return-null-on-empty, and never-fails insertion — with `push`/`pop`/`peek` at the head and `add`/`offer` at the tail.

## Pitfalls

### Copying `node(int)`'s `>> 1` into a binary-search midpoint

**Wrong**
```java
    static int badMid(int lo, int hi) {
        return (lo + hi) >> 1;   // signed shift on a sum that can overflow
    }
```
With `lo = 1_500_000_000`, `hi = 2_000_000_000`, the sum overflows to `-794_967_296` and `>> 1` yields `-397_483_648` — a negative index.

**Right**
```java
    static int goodMid(int lo, int hi) {
        return (lo + hi) >>> 1;  // unsigned shift recovers the true midpoint
    }
```
Run: `badMid = -397483648`, `goodMid = 1750000000`, `sum as int = -794967296`. `>>> 1` recovers the true midpoint because the sum's real value fits in 32 *unsigned* bits.

**Why people believe it:** `node(int)`'s `size >> 1` really is safe. The distinguishing question is whether the halved value can be negative — `size` cannot, `lo + hi` can.

### Assuming `Deque.peek()` gives you the oldest element

**Wrong**
```java
    static String mixedVocabularyPeek() {
        Deque<String> jobs = new MyLinkedList<>();
        jobs.add("first-in");
        jobs.push("urgent");
        return jobs.peek();            // returns "urgent", not "first-in"
    }
```
`add` appends at the tail, `push` prepends at the head, `peek` reads the head — one `push` silently converts a FIFO read into a LIFO read.

**Right**
```java
    static String oneVocabularyPeek() {
        Deque<String> jobs = new MyLinkedList<>();
        jobs.addLast("first-in");      // one vocabulary: tail-in
        jobs.addLast("urgent");
        return jobs.peekFirst();       // "first-in", unambiguous FIFO
    }
```
**Why people believe it:** `peek()` in `Queue` means the head of the queue; `peek()` in `Stack` means the top of the stack. `Deque` inherits the `Queue` name and the `Stack` head, so the word is correct for both readings and useless as a hint.

## Cheat sheet

| Item | Value |
|---|---|
| Declaration | `extends AbstractSequentialList<E> implements List<E>, Deque<E>` |
| Must supply | `size()`, `listIterator(int)` — everything else is inherited or `Deque` |
| Fields | `size`, `first`, `last` (+ inherited `modCount`); no sentinels, `first == null` means empty |
| Link methods | `modCount++`, `size++`, 3–4 reference writes, one null-neighbour branch |
| `unlink` nulls | `item` always; `prev`/`next` only in the non-end branches |
| `unlinkFirst`/`unlinkLast` null | `item`+`next` / `item`+`prev` — the other side was already null |
| `node(int)` | `index < (size >> 1)` → forward from `first`, else backward from `last`; ⌊(n−1)/2⌋ worst case |
| Head ops | `addFirst`, `offerFirst`, `push`, `removeFirst`, `pop`, `remove()`, `pollFirst`, `poll`, `getFirst`, `element`, `peekFirst`, `peek` |
| Tail ops | `addLast`, `offerLast`, `add`, `offer`, `removeLast`, `pollLast`, `getLast`, `peekLast` |
| Throws on empty | `removeFirst`, `removeLast`, `pop`, `remove()`, `getFirst`, `getLast`, `element` |
| Null on empty | `pollFirst`, `pollLast`, `poll`, `peekFirst`, `peekLast`, `peek` |
| Nulls permitted | yes (unlike `ArrayDeque`) |
| JDK 21 gotcha | must override `reversed()` or `List`+`Deque` will not compile |

## Self-test

**Q1.** Why does `MyLinkedList` extend `AbstractSequentialList` rather than `AbstractList`?

<details><summary>Answer</summary>

`AbstractList` implements its bulk operations on top of the abstract `get(int)`, which is O(n) here, so `addAll`, `equals`, `hashCode` and the default `iterator()` would each become O(n²). `AbstractSequentialList` inverts the dependency: `get`, `set`, `add(int, E)`, `remove(int)`, `addAll(int, Collection)` and `iterator()` are all built on the single abstract `listIterator(int)`, so each traverses the chain exactly once. `java.util.LinkedList` extends `AbstractSequentialList` for this reason.

</details>

**Q2.** `unlink` contains `x.prev = null` and `x.next = null`, but neither is at the top level of the method. Where are they and why?

<details><summary>Answer</summary>

`x.prev = null` is inside the `else` of `if (prev == null)`; `x.next = null` is inside the `else` of `if (next == null)`. If `prev` was already null the write is pure waste on the hottest removal path; same for `next`. Only `x.item = null` is unconditional. "Unlink nulls all three fields" describes the outcome but misdescribes the code.

</details>

**Q3.** An eight-element `MyLinkedList` holds `0..7`. Which direction does `node(4)` walk, and how many hops?

<details><summary>Answer</summary>

Backward. The test `index < (size >> 1)` is `4 < 4`, false, so control falls to the `else` branch starting at `last`, and `for (int i = size - 1; i > index; i--)` runs `i = 7, 6, 5` — three `x.prev` hops, against four walking forward. The run confirms `get(4)` returns `4`.

</details>

**Q4.** Why does `java.util.LinkedList.clear()` walk the whole chain nulling fields instead of just `first = last = null; size = 0;`?

<details><summary>Answer</summary>

Setting the head and tail to null makes the chain unreachable *from the list*, which suffices only if nothing else points into it. An outstanding `ListIterator` holds `lastReturned` and `next` node references, and any survivor pins the entire chain through `next`/`prev`. Nulling each node's fields breaks the chain into isolated nodes, so one stale reference pins at most one dead node. Our inherited `AbstractList.clear()` achieves the same via repeated `unlink`, more slowly.

</details>

**Q5.** In JDK 17 a class could implement both `List` and `Deque` with no extra method. In JDK 21 it cannot. What changed?

<details><summary>Answer</summary>

JEP 431 (Sequenced Collections) added `SequencedCollection` in Java 21, and `List` and `Deque` now declare `reversed()` with covariant return types — `List<E>` and `Deque<E>`. Those are unrelated, so a class implementing both inherits two incompatible signatures and `javac` rejects it with `both define reversed(), but with unrelated return types`. Override `reversed()` returning a type assignable to both; `java.util.LinkedList` returns `LinkedList<E>` at line 1285.

</details>

**Q6.** Which of `add`, `offer`, `push`, `remove()`, `poll`, `peek` operate on the head?

<details><summary>Answer</summary>

`push`, `remove()`, `poll` and `peek` are head operations. `add` and `offer` are tail operations, inherited from `Queue` semantics where insertion is at the tail and removal at the head. So `add` then `peek` is FIFO while `push` then `peek` is LIFO; mixing them in one code path is a silent ordering bug. Use only `addFirst`/`addLast`/`peekFirst`/`peekLast` and the ambiguity disappears.

</details>

---

**Leaves covered:** 4.2.1, 4.2.2, 4.2.3, 4.2.4 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 600
