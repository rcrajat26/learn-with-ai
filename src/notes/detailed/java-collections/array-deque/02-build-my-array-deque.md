# 02 Java Collections — `ArrayDeque` — INTERNALS (§4.4 `MyArrayDeque<E>` — the two designs, the fields and the core operations)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [array-deque/01-internals.md](01-internals.md) · Next: [array-deque/03-build-my-array-deque-b-grow-iterator-and-diff.md](03-build-my-array-deque-b-grow-iterator-and-diff.md)

Reading `ArrayDeque` tells you the invariant. Writing it tells you which lines exist only to defend the invariant, and that turns out to be most of them.

**The class is presented in two parts.** `MyArrayDeque.java` is the concatenation, in order, of every code block in this file and in [03](03-build-my-array-deque-b-grow-iterator-and-diff.md) that is labelled **`MyArrayDeque.java`**. `PowerOfTwoDeque.java`, below, is a second and completely standalone file — it exists to make the pre-JDK-9 design concrete side by side with the current one. Both build under JDK 21.0.7 with `-Xlint:all` and zero warnings; the compile command and the full demo output are at the end of [03](03-build-my-array-deque-b-grow-iterator-and-diff.md).

This file covers the two designs, the field set, the circular helpers, null rejection, the four primitive operations and everything derived from them. Growth, the iterator and the diff table are in [03](03-build-my-array-deque-b-grow-iterator-and-diff.md).

---

### Two designs for the same ring, and why the JDK switched

**Mental model.** A circular buffer needs one operation: "advance this index by one, wrapping at the end." There are exactly two cheap ways to do it. Force the array length to a power of two and the wrap is a bitwise AND with `length - 1`, because the AND simply discards the carry. Allow any length and the wrap is a compare-and-branch. The first is one instruction; the second is one instruction plus a branch the predictor gets right essentially every time, because it is taken once per lap.

**Why it exists.** The power-of-two design was the obvious choice in 2006, when `ArrayDeque` shipped in Java 6, and it is still the right choice for a fixed-capacity ring buffer where you pick the capacity yourself. It stops being right for a *growable* deque, because the constraint propagates: if the length must be a power of two, then the initial capacity must be rounded up (`new ArrayDeque<>(1000)` allocating 1024, `new ArrayDeque<>(1_100_000)` allocating 2,097,152) and growth must be exact doubling, since 1.5× of a power of two is not one.

**When to reach for which.** Power-of-two masking when the capacity is fixed at construction and never grows — a JCTools-style SPSC queue, an audio ring, a fixed-depth history buffer. Branch-based helpers when the structure grows, so that capacity can be exact and the growth factor can be chosen for its memory profile rather than forced by an arithmetic constraint.

**How it works.** Here is the classic design, complete and compiling. It is a faithful reduction of `java/util/ArrayDeque.java` as it stood in JDK 8u202, down to the field names.

```java
// PowerOfTwoDeque.java  —  a standalone second file
/**
 * The classic pre-JDK-9 design, for comparison: capacity forced to a power of
 * two so that wraparound is a single AND.
 */
public class PowerOfTwoDeque<E> {

    private Object[] elements;
    private int head;
    private int tail;

    private static final int MIN_INITIAL_CAPACITY = 8;

    public PowerOfTwoDeque() {
        elements = new Object[16];
    }

    public PowerOfTwoDeque(int numElements) {
        elements = new Object[calculateSize(numElements)];
    }

    /** Rounds up to the next power of two, floored at 8. */
    private static int calculateSize(int numElements) {
        int initialCapacity = MIN_INITIAL_CAPACITY;
        if (numElements >= initialCapacity) {
            initialCapacity = numElements;
            initialCapacity |= (initialCapacity >>> 1);
            initialCapacity |= (initialCapacity >>> 2);
            initialCapacity |= (initialCapacity >>> 4);
            initialCapacity |= (initialCapacity >>> 8);
            initialCapacity |= (initialCapacity >>> 16);
            initialCapacity++;
            if (initialCapacity < 0) initialCapacity >>>= 1;
        }
        return initialCapacity;
    }

    public void addFirst(E e) {
        if (e == null) throw new NullPointerException();
        elements[head = (head - 1) & (elements.length - 1)] = e;
        if (head == tail) doubleCapacity();
    }

    public void addLast(E e) {
        if (e == null) throw new NullPointerException();
        elements[tail] = e;
        if ((tail = (tail + 1) & (elements.length - 1)) == head) doubleCapacity();
    }

    @SuppressWarnings("unchecked")
    public E pollFirst() {
        int h = head;
        E result = (E) elements[h];
        if (result == null) return null;
        elements[h] = null;
        head = (h + 1) & (elements.length - 1);
        return result;
    }

    @SuppressWarnings("unchecked")
    public E pollLast() {
        int t = (tail - 1) & (elements.length - 1);
        E result = (E) elements[t];
        if (result == null) return null;
        elements[t] = null;
        tail = t;
        return result;
    }

    /** Only ever called when head == tail, i.e. the buffer is exactly full. */
    private void doubleCapacity() {
        assert head == tail;
        int p = head;
        int n = elements.length;
        int r = n - p;                 // elements to the right of p
        int newCapacity = n << 1;
        if (newCapacity < 0) throw new IllegalStateException("Sorry, deque too big");
        Object[] a = new Object[newCapacity];
        System.arraycopy(elements, p, a, 0, r);
        System.arraycopy(elements, 0, a, r, p);
        elements = a;
        head = 0;
        tail = n;
    }

    public int size() {
        return (tail - head) & (elements.length - 1);
    }

    public int capacity() {
        return elements.length;
    }
}
```

Three things to notice, because each one is a *consequence* of the mask rather than an independent choice.

`calculateSize` is the classic bit-smear: OR the value with itself shifted by 1, 2, 4, 8 and 16, which fills every bit below the highest set bit, then add one to carry up to the next power of two. The final `if (initialCapacity < 0) initialCapacity >>>= 1` catches a request above 2³⁰, where the smear-and-increment overflows into the sign bit.

`doubleCapacity` is much simpler than JDK 21's `grow`, and that is the mask's one real gift: because it is only ever called when the buffer is exactly full, the head-side leg is always `elements[head..length)` and the tail-side leg is always `elements[0..head)`, so two unconditional `arraycopy` calls into a fresh array normalise the deque with `head = 0`. No wrap test, no null-out loop. Compare with the JDK 21 version in [03](03-build-my-array-deque-b-grow-iterator-and-diff.md), which must handle growth from any state and therefore needs the un-wrap slide.

The reserved-slot invariant is present in both designs. `head == tail` still means empty here, and the array still holds `length - 1` elements at most. The mask is orthogonal to the reserved slot — it is a common confusion that the power-of-two capacity is what makes the empty test work. It is not.

![ArrayDeque before and after: JDK 8's power-of-two capacity with (head - 1) & (elements.length - 1), versus JDK 21's arbitrary capacity 17 with head = dec(head, 17), and a VERSION TRAP banner](../diagrams/D-78-arraydeque-mask-vs-helpers.svg)

The measured difference, from the demo in [03](03-build-my-array-deque-b-grow-iterator-and-diff.md), running both classes over the same insertions on JDK 21.0.7:

```
request 1000: pow2    = 1024, java21-style = 1001
after 1000 adds: pow2 = 1024, java21-style = 1001, sizes 1000/1000
after 1001 adds: pow2 = 1024, java21-style = 1501
java21-style ladder   = 17 -> 36 -> 74 -> 111 -> 166 -> 249 -> 373 -> 559 -> 838
power-of-two ladder   = 16 -> 32 -> 64 -> 128 -> 256 -> 512 -> 1024
```

Read the two ladders against each other. The power-of-two ladder has 6 steps to reach 1024; the Java 21 ladder has 8 to reach 838. More copies, but every intermediate array is smaller, and the *sum* of the freed arrays can eventually satisfy a later request — the same block-reuse argument that decided `ArrayList`'s 1.5× factor, worked through in [array-list/04](../array-list/04-amortised-analysis.md). Note also the third line: at 1001 elements the power-of-two deque is still inside its 1024 slots while the exact-capacity one has just grown to 1501. Below the rounding boundary the mask design wins on copy count; above it, it wins on nothing and loses up to 2× on memory.

| | Power-of-two mask (JDK 6–8) | Branch helpers (JDK 9+) |
|---|---|---|
| Wraparound | `(i + 1) & (len - 1)` — one AND | `if (++i >= len) i = 0` — compare + cmov |
| `new Deque<>(1000)` allocates | 1024 | 1001 |
| Worst-case rounding waste | just under 2× | zero |
| Growth factor | forced ×2 | `< 64 ? +2 : ×1.5`, freely chosen |
| Grow when wrapped | two unconditional `arraycopy`, `head` reset to 0 | `copyOf` then a conditional un-wrap slide |
| `size()` | `(tail - head) & (len - 1)` | `sub(tail, head, len)` |
| Reserved empty slot | yes | yes |
| Good for | fixed-capacity rings | growable deques |

**Pitfall:** the wrong belief is that the mask and the reserved slot are the same mechanism, so dropping the mask must also change the emptiness test. The symptom is a reimplementation that adds a `size` field "because `head == tail` no longer works", then has to write it on every mutation. The fix is to see that they are independent: the reserved slot gives you `head == tail ⟹ empty` at *any* capacity, and the mask is purely an index-arithmetic optimisation.

**Interview:** "How would you implement a deque on an array?" — Circular window, `head` at the first element, `tail` at the next free slot, one slot always reserved so `head == tail` means empty. Then say which wrap strategy and why: mask if the capacity is fixed, branch helpers if it grows, and note that the JDK switched from the first to the second in JDK 9 precisely so that capacity could be exact.

> The power-of-two mask buys one instruction per index step at the cost of forcing both capacity rounding and pure doubling; branch-based helpers give those two freedoms back for the price of a perfectly-predicted branch.

---

## The class head, the fields and the constructors

```java
// MyArrayDeque.java
import java.util.AbstractCollection;
import java.util.Arrays;
import java.util.ConcurrentModificationException;
import java.util.Deque;
import java.util.Iterator;
import java.util.NoSuchElementException;
import java.util.Objects;

/**
 * A reimplementation of java.util.ArrayDeque in the Java 21 style: a circular
 * window over an Object[] of arbitrary length, with one slot always free.
 */
public class MyArrayDeque<E> extends AbstractCollection<E> {

    /** The backing array. Every cell not holding an element is null. */
    Object[] elements;

    /** Index of the first element; equal to tail when the deque is empty. */
    int head;

    /** Index of the next free slot. elements[tail] is always null. */
    int tail;

    private static final int MAX_ARRAY_SIZE = Integer.MAX_VALUE - 8;

    public MyArrayDeque() {
        elements = new Object[16 + 1];
    }

    public MyArrayDeque(int numElements) {
        elements = new Object[(numElements < 1) ? 1
                            : (numElements == Integer.MAX_VALUE) ? Integer.MAX_VALUE
                            : numElements + 1];
    }
```

`extends AbstractCollection<E>` is the same base the JDK uses, and it is worth knowing what it buys: `isEmpty`, `contains`, `toArray`, `remove(Object)`, `containsAll`, `addAll`, `removeAll`, `retainAll`, `clear` and `toString`, all written in terms of `iterator()` and `size()`. That is why the only two methods `AbstractCollection` declares abstract are those two — and why a correct `iterator()` is not optional decoration here, it is load-bearing for a third of the public surface. This build overrides `isEmpty`, `contains`, `clear` and `remove(Object)` anyway, each for a specific reason given at the point of the override; everything else is inherited.

The three fields are package-private rather than `private`, exactly as in the JDK, so the nested `DeqIterator` reaches them without a synthetic accessor. There is deliberately **no** `size` field and **no** `modCount` field. Both are absences you have to justify, and both are justified below.

The constructors are the JDK's, `+ 1` and all. The `numElements == Integer.MAX_VALUE` arm is not paranoia: `Integer.MAX_VALUE + 1` wraps to `Integer.MIN_VALUE`, and `new Object[Integer.MIN_VALUE]` throws `NegativeArraySizeException` — a bizarre failure for a caller who asked for a large deque and expected, at worst, `OutOfMemoryError`.

**Insight:** the whole class is designed so that no method needs to know the deque's size. `addLast` does not check "am I full?"; it writes, advances, and *then* notices the collision. `pollFirst` does not check "am I empty?"; it reads the slot and lets `null` answer the question. Every operation is a write-or-read plus one comparison, and the reserved slot is what makes that possible.

---

## The circular helpers

```java
// MyArrayDeque.java
    // ---- circular index arithmetic -------------------------------------

    static int inc(int i, int modulus) {
        if (++i >= modulus) i = 0;
        return i;
    }

    static int dec(int i, int modulus) {
        if (--i < 0) i = modulus - 1;
        return i;
    }

    static int sub(int i, int j, int modulus) {
        if ((i -= j) < 0) i += modulus;
        return i;
    }

    @SuppressWarnings("unchecked")
    static <E> E elementAt(Object[] es, int i) {
        return (E) es[i];
    }

    @SuppressWarnings("unchecked")
    static <E> E nonNullElementAt(Object[] es, int i) {
        E e = (E) es[i];
        if (e == null) throw new ConcurrentModificationException();
        return e;
    }
```

`static`, and taking the modulus as a parameter rather than reading `elements.length`, for the same reason the JDK does it: a static method with no receiver and no field access is trivially inlinable, and passing the modulus lets the caller hoist the array-length load out of a loop.

Note what is *not* here: no `%`. Integer remainder by a non-constant divisor compiles to a hardware division, tens of cycles on most cores and not pipelined. `dec(i, m)` is a decrement, a sign test and a conditional move. That is the entire reason these four lines are worth writing out rather than calling `Math.floorMod`.

`elementAt` is a generic cast helper — "a slight abuse of generics, accepted by javac", as the JDK's own comment puts it — that exists so the unchecked-cast suppression lives in one place instead of at twenty call sites. `nonNullElementAt` is the same read plus the deque's *only* comodification detection, and it is deliberately weak: with no `modCount`, the iterator can only notice a concurrent change when that change happens to have nulled the slot it was about to read. Detection is partial by construction, and the JDK's version carries a Javadoc admitting exactly that.

The type parameter `<E>` on the two static helpers shadows the class's `E`. That is intentional and is what the JDK does — the methods are static so they cannot see the class's type parameter, and the shadowing name keeps call sites readable.

---

### Null rejection, with a message that says why

**Mental model.** `null` is not merely disallowed, it is *spoken for*: it is the value that means "this slot holds no element". Every invariant in the class reads it that way. `pollFirst` uses `e != null` as its emptiness test. `nonNullElementAt` treats a null as corruption. `grow`'s wrap test disambiguates `head == tail` by asking whether `elements[head]` is null. Admit one stored `null` and all three become wrong simultaneously.

**Why it exists.** The `Queue` contract's whole ergonomics rest on it. `poll()` returning `null` means "empty", `peek()` returning `null` means "empty" — those are only unambiguous because a stored null is impossible. The alternative, an `Optional`-returning API or a separate `isEmpty` check before every read, is what `Queue` was designed to avoid.

**When it matters.** When your elements come from a source that can legitimately produce nothing — a parsed optional header, a map lookup, a nullable column. The failure lands at insertion, which is often far from where the null was produced.

**How it works.** The JDK throws a bare `new NullPointerException()` with no message. That is defensible in `java.base`, where the stack trace names `ArrayDeque.addLast` and the reader can look it up; it is not defensible in your own code, so this build spends four lines saying why:

```java
// MyArrayDeque.java
    private static <E> E requireNonNullElement(E e) {
        if (e == null)
            throw new NullPointerException(
                "MyArrayDeque prohibits null elements: null marks an unoccupied "
                + "slot, so a stored null would be indistinguishable from an "
                + "empty deque. Wrap the value in Optional, or use LinkedList.");
        return e;
    }
```

Measured output from the demo:

```
addLast(null)         = NPE: MyArrayDeque prohibits null elements: null marks an
unoccupied slot, so a stored null would be indistinguishable from an empty deque.
Wrap the value in Optional, or use LinkedList.
```

**Pitfall:** the wrong belief is that the null ban is a style rule the API authors chose, so a "more permissive" implementation could simply drop the check. The symptom is a deque that reports the wrong size, silently truncates on iteration, and grows at the wrong moment — because `pollFirst` returning a stored `null` leaves `head` unmoved. The fix is to see the ban as a *representation* consequence: if you want nulls, you need a per-slot occupancy marker, which means either a parallel `boolean[]`, a wrapper object per element, or `LinkedList`'s node-per-element design. Each of those costs more than the ban does.

**Interview:** "Why can't you put null in an `ArrayDeque`?" — Because `null` is the sentinel for an empty array slot, so a stored null would make `poll()` returning null ambiguous and would break the emptiness test. Same reason for `PriorityQueue` and the concurrent queues; `LinkedList` allows nulls because it stores each element in a `Node`, so node *presence* is the marker.

> `null` is not a rejected value in an array-backed deque, it is a reserved one — the marker for an unoccupied slot — and the prohibition is what makes `poll()` returning `null` mean exactly one thing.

---

### The four primitives, and the twenty methods defined from them

**Mental model.** There are only four real methods: put at the front, put at the back, take from the front, take from the back. `add`, `offer`, `push`, `pop`, `peek`, `poll`, `element`, `remove`, and both `First`/`Last` spellings of each, are one-line adaptations that differ only in what they do when the deque is empty — return `null` or throw. Writing them any other way duplicates the index arithmetic and gives you four places to get the wrap wrong.

**Why it exists.** `Deque` is a wide interface — twelve insertion and removal methods before you count the inherited `Collection` and `Queue` ones — precisely because it is trying to be the union of a stack API, a queue API and a two-ended API. Collapsing it to four primitives is what keeps the implementation honest.

**How it works.**

```java
// MyArrayDeque.java
    // ---- the four primitive operations ---------------------------------

    public void addFirst(E e) {
        requireNonNullElement(e);
        final Object[] es = elements;
        es[head = dec(head, es.length)] = e;
        if (head == tail) grow(1);
    }

    public void addLast(E e) {
        requireNonNullElement(e);
        final Object[] es = elements;
        es[tail] = e;
        if (head == (tail = inc(tail, es.length))) grow(1);
    }

    public E pollFirst() {
        final Object[] es = elements;
        final int h = head;
        E e = elementAt(es, h);
        if (e != null) {
            es[h] = null;
            head = inc(h, es.length);
        }
        return e;
    }

    public E pollLast() {
        final Object[] es = elements;
        final int t = dec(tail, es.length);
        E e = elementAt(es, t);
        if (e != null) es[tail = t] = null;
        return e;
    }
```

The asymmetry between `addFirst` and `addLast` is forced by what the two indices mean. `head` points at an *occupied* slot, so `addFirst` must move it before writing. `tail` points at a *free* slot, so `addLast` writes first and moves after. Get that backwards and the first element you add lands on top of the last one.

Both grow *after* the write, when the collision has already happened. That is why `grow`'s wrap test needs the `es[head] != null` disambiguation covered in [03](03-build-my-array-deque-b-grow-iterator-and-diff.md): at that instant, and only at that instant, `head == tail` means full rather than empty.

`pollFirst` nulls the vacated slot before advancing `head`. Skip that line and the polled element stays strongly reachable for the lifetime of the deque — the classic retention leak, identical in kind to `ArrayList.fastRemove`'s trailing null and `LinkedList.unlink`'s three erasures. It also breaks the invariant that every non-element cell is null, which the iterator's `nonNullElementAt` depends on.

`pollLast` computes `t = dec(tail, es.length)` once and reuses it in the write `es[tail = t] = null`, which both nulls the slot and retracts `tail` in one expression.

The rest of the surface:

```java
// MyArrayDeque.java
    // ---- everything else is defined in terms of those four -------------

    public E peekFirst() {
        return elementAt(elements, head);
    }

    public E peekLast() {
        final Object[] es = elements;
        return elementAt(es, dec(tail, es.length));
    }

    public E removeFirst() {
        E e = pollFirst();
        if (e == null) throw new NoSuchElementException();
        return e;
    }

    public E removeLast() {
        E e = pollLast();
        if (e == null) throw new NoSuchElementException();
        return e;
    }

    public E getFirst() {
        E e = peekFirst();
        if (e == null) throw new NoSuchElementException();
        return e;
    }

    public E getLast() {
        E e = peekLast();
        if (e == null) throw new NoSuchElementException();
        return e;
    }

    @Override public boolean add(E e)  { addLast(e); return true; }
    public boolean offer(E e)          { addLast(e); return true; }
    public void push(E e)              { addFirst(e); }
    public E pop()                     { return removeFirst(); }
    public E poll()                    { return pollFirst(); }
    public E peek()                    { return peekFirst(); }
```

`peekFirst()` on an empty deque reads `elements[head]`, which is the reserved null slot — so it returns `null` without any bounds check or emptiness test. That is not luck; it is the reserved slot paying for itself a third time.

The six one-liners at the bottom are the whole stack-versus-queue duality. `push`/`pop` work the front; `add`/`offer` work the back; `poll`/`peek` work the front. So the same object is a LIFO stack if you use `push`/`pop` and a FIFO queue if you use `add`/`poll`, and — unlike `java.util.Stack` — iteration is head-to-tail, which for stack usage means top-to-bottom. Measured:

```
stack iteration       = [c, b, a]  pop -> c
```

`java.util.Stack`, extending `Vector`, iterates bottom-to-top and would print `[a, b, c]` for the same three pushes. That reversal is the single most common source of quiet bugs when migrating off `Stack`; see [framework/07-legacy-a](../framework/07-legacy-a-vector-stack-hashtable.md).

> The four primitives — `addFirst`, `addLast`, `pollFirst`, `pollLast` — carry all the index arithmetic; every other insertion or removal method is a one-line adaptation that differs only in its empty-deque behaviour.

---

## Size, emptiness and clear

```java
// MyArrayDeque.java
    @Override public int size() {
        return sub(tail, head, elements.length);
    }

    @Override public boolean isEmpty() {
        return head == tail;
    }

    @Override public void clear() {
        final Object[] es = elements;
        for (int i = head, end = tail, to = (i <= end) ? end : es.length;
             ; i = 0, to = end) {
            for (; i < to; i++) es[i] = null;
            if (to == end) break;
        }
        head = tail = 0;
    }
```

`size()` is derived, not stored (leaf 4.4.5). It is O(1) either way, so the trade is: a field costs 4 bytes per deque plus one write on every mutation; the arithmetic costs one array-header read plus a subtract and a predictable branch on every `size()` call. For a structure whose primary use is `while (!q.isEmpty()) q.poll()`, the mutation count dwarfs the `size()` count, so deriving wins.

`isEmpty()` is overridden rather than inherited because `AbstractCollection.isEmpty()` is `size() == 0`, which is the array read plus the subtract plus the branch. `head == tail` is two field reads and a compare.

`clear()` is the first appearance of the two-slice loop shape — unconditional outer `for`, plain counted inner `for`, break at the bottom — that recurs in `contains`, in the iterator's bulk path and in the JDK's `toArray` and `forEach`. It runs the inner loop once when the deque is contiguous and twice when it is wrapped, with a single loop body either way, which is what lets HotSpot treat it as an ordinary counted array loop and apply range-check elimination. The full argument, with the JDK's own class comment, is in [array-deque/01](01-internals.md).

`clear()` nulls the occupied slots but does **not** shrink `elements`. A deque that once held a million elements keeps its 4 MB array until the deque itself becomes unreachable. There is no `trimToSize`; if you need one, `new MyArrayDeque<>(old)` rebuilds at exactly `size + 1`.

---

## Pitfalls

### Writing `addFirst` and `addLast` symmetrically

**Wrong**

```java
public void addFirst(E e) {
    elements[head] = e;                       // write, then move
    head = dec(head, elements.length);
}
```

Output: the first `addFirst` on a fresh deque writes to `elements[0]` and leaves `head` at `length - 1`, pointing at an empty slot. `peekFirst()` returns `null`, `size()` returns 1, and the element is unreachable through the public API.

**Right**

```java
public void addFirst(E e) {
    requireNonNullElement(e);
    final Object[] es = elements;
    es[head = dec(head, es.length)] = e;      // move, then write
    if (head == tail) grow(1);
}
```

**Why people believe it:** `addLast` really is write-then-move, and the two methods look like mirror images. They are not — the mirror is broken by `head` denoting an occupied slot and `tail` a free one.

### Dropping the null-out in `pollFirst`

**Wrong**

```java
public E pollFirst() {
    E e = elementAt(elements, head);
    if (e != null) head = inc(head, elements.length);   // no es[h] = null
    return e;
}
```

Output: functionally correct for a while, then two failures. Every polled element stays reachable through the array, so a long-lived queue retains everything that ever passed through it — visible in a heap dump as a large `Object[]` full of live objects the application dropped hours ago. And the iterator's `nonNullElementAt` check is now meaningless, because stale non-null slots sit all over the array.

**Right**

```java
    if (e != null) {
        es[h] = null;          // the element is now collectable
        head = inc(h, es.length);
    }
```

**Why people believe it:** the slot is "outside" the live window, so it feels dead. It is not — the array is one object, and every reference in it is a strong reference for as long as the array lives.

### Assuming `AbstractCollection` gives you a correct `remove(Object)` for free

**Wrong**

```java
// no override; inherit AbstractCollection.remove(Object)
deque.remove(someValue);
```

`AbstractCollection.remove` walks `iterator()` and calls `it.remove()`. That is fine — *provided* the iterator's `remove` compensates for the shift that `delete` performs. This build's does, via the boolean `delete` returns; a naive iterator that just calls `delete(lastRet)` and moves on will skip the element that slid into the vacated slot.

**Right**

The override in [03](03-build-my-array-deque-b-grow-iterator-and-diff.md) still routes through the iterator, but the iterator's `remove` reads `delete`'s return value and steps `cursor` back when the tail side shifted. The demo exercises exactly this, removing every even element across a wrap and checking that nothing is skipped.

**Why people believe it:** for `ArrayList` the equivalent inheritance is harmless, because removal always shifts *left* and the iterator's `cursor = lastRet` resync handles it. A circular buffer can shift in either direction, so one resync rule is not enough.

---

## Cheat sheet

| Piece | This build |
|---|---|
| Base class | `AbstractCollection<E>` — gives `toArray`, `containsAll`, `addAll`, `toString` from `iterator()` + `size()` |
| Fields | `Object[] elements`, `int head`, `int tail`; package-private; no `size`, no `modCount` |
| `head` / `tail` | first element / next free slot; `elements[tail]` always `null` |
| No-arg capacity | `new Object[16 + 1]` = 17 slots, 16 usable |
| `MyArrayDeque(n)` | `n + 1` slots; `n < 1` → 1; `n == Integer.MAX_VALUE` → `Integer.MAX_VALUE` |
| Wrap helpers | `inc`, `dec`, `sub` — static, modulus passed in, one branch each, no `%` |
| Null policy | rejected with an explanatory `NullPointerException` |
| Primitives | `addFirst`, `addLast`, `pollFirst`, `pollLast` — everything else derives |
| `addFirst` | move `head` then write |
| `addLast` | write then move `tail` |
| Grow trigger | after the write, when `head == tail` |
| `size()` | `sub(tail, head, elements.length)` — derived, not stored |
| `isEmpty()` | `head == tail`, overridden to skip `size()` |
| `clear()` | two-slice null-out, `head = tail = 0`; array not shrunk |
| Stack use | `push`/`pop`/`peek` at the front; iteration is top-to-bottom, unlike `java.util.Stack` |
| Power-of-two variant | `PowerOfTwoDeque`, standalone; mask wrap, ×2 growth, rounded capacity |

---

## Self-test

**Q1.** Why does `addFirst` move `head` before writing while `addLast` writes before moving `tail`?

<details><summary>Answer</summary>

Because the two indices denote different things. `head` is the index of an occupied slot — the first element — so the slot it currently points at is taken, and a new front element has to go one position anticlockwise. `tail` is the index of the *next free* slot, so a new back element goes exactly where `tail` already points, and only then does `tail` advance. The methods look like mirror images and are not; writing them symmetrically overwrites the current first element on every `addFirst`.

</details>

**Q2.** `MyArrayDeque` has no `size` field. What does it cost, and what does it buy?

<details><summary>Answer</summary>

It costs one array-header read, one subtract and one predictable branch per `size()` call — `sub(tail, head, elements.length)`. It buys 4 bytes per instance and, much more importantly, removes a write from every single mutation: `addFirst`, `addLast`, `pollFirst`, `pollLast` and `delete` would all have to maintain it. Since the dominant usage pattern is many mutations and few `size()` calls, deriving is the right trade. It also removes a whole class of bug — a size field that drifts out of step with `head`/`tail` is silent, whereas derived size cannot drift.

</details>

**Q3.** What breaks if you allow a `null` element?

<details><summary>Answer</summary>

Three things at once. `pollFirst` uses `e != null` as its combined emptiness test and value fetch, so it would treat a stored null as "empty" and return without advancing `head` — the deque would appear to stall. `nonNullElementAt` treats a null slot as evidence of concurrent modification, so iteration over a deque containing a null would throw `ConcurrentModificationException` on valid data. And `grow`'s wrap test disambiguates `head == tail` by checking `elements[head] != null`, so a null first element would make a full deque look empty and the un-wrap slide would be skipped, scrambling the sequence.

</details>

**Q4.** `new PowerOfTwoDeque<>(1000)` and `new MyArrayDeque<>(1000)`. Compare the allocations, then compare them again after 1001 insertions.

<details><summary>Answer</summary>

At construction: 1024 slots versus 1001. Measured on JDK 21.0.7. After 1000 insertions both are unchanged — the power-of-two deque has 24 slots spare, the exact one has exactly its reserved slot free. The 1001st insertion fills the exact deque and triggers `grow`, taking it to 1501 (`jump = 1000 >> 1 = 500`, since 1001 ≥ 64); the power-of-two deque still fits. So below the rounding boundary the mask design does fewer copies, and above it, it wastes up to 2× memory with no compensating benefit. That asymmetry is why the JDK dropped the constraint once it wanted a non-doubling growth factor.

</details>

**Q5.** Why are `inc`, `dec` and `sub` `static` and given the modulus as a parameter, instead of instance methods reading `elements.length`?

<details><summary>Answer</summary>

Two reasons, both about the JIT. A static method with no receiver and no field access is a trivially inlinable pure function of its arguments; an instance method that reads a field forces the compiler to reason about whether an intervening write could have changed it. And passing the modulus lets the caller load `elements.length` once into a local and reuse it across a loop — which is why every method in this class opens with `final Object[] es = elements`. Making them instance methods would put an array-header read inside every index step.

</details>

**Q6.** `AbstractCollection` declares only `iterator()` and `size()` abstract, yet this build overrides `isEmpty`, `contains` and `clear` anyway. Why each?

<details><summary>Answer</summary>

`isEmpty()`: the inherited version is `size() == 0`, which is an array read plus a subtract plus a branch; `head == tail` is two field reads and a compare. `contains` and `clear`: the inherited versions walk `iterator()`, allocating an iterator object and paying a virtual `next()` per element with the wrap check inside it. The two-slice loop does the same work as one hot counted loop over a raw array, with no allocation and no megamorphic call. None of the three overrides changes behaviour — they are pure cost reductions, which is the normal reason to override a skeleton method.

</details>

**Q7.** A colleague proposes replacing `dec(i, modulus)` with `Math.floorMod(i - 1, modulus)`. What do you say?

<details><summary>Answer</summary>

That it is correct and slower. `Math.floorMod` performs an actual integer remainder, and `%` by a value the compiler cannot prove constant is a hardware division — on the order of twenty to forty cycles on common cores, and not pipelined, so it serialises the dependent chain of index updates. `dec` is a decrement, a sign test and a conditional move, all of which the JIT will fold into the surrounding code. The correctness gain is nil, because `dec`'s precondition — `0 <= i < modulus` — is an invariant every caller in the class already maintains, so the index can never be more than one step out of range.

</details>

---

**Leaves covered:** 4.4.1, 4.4.2, 4.4.3, 4.4.5, 4.4.6 (5 leaves)
**Leaves deferred:** none — 4.4.4, 4.4.7 and 4.4.8 are covered in [03-build-my-array-deque-b-grow-iterator-and-diff.md](03-build-my-array-deque-b-grow-iterator-and-diff.md)
**Diagrams included:** D-78 (re-embedded from [01-internals.md](01-internals.md); no new diagram in this row)
**Target version:** Java 21 LTS
**Lines:** 600
