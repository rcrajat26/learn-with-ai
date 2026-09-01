# 02 Java Collections — `HashMap` — INTERNALS (§3.6 `HashMap` source walk — `putTreeVal`, `find`, `tieBreakOrder` and `comparableClassFor`)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [hash-map/04-internals-d-treeify.md](04-internals-d-treeify.md) · Next: [hash-map/04b-internals-d2-poisson-and-hysteresis.md](04b-internals-d2-poisson-and-hysteresis.md)

---

## The shape of the problem

A treeified bin is a red-black tree whose sort key is **not the key's natural order**. Its primary sort key is the spread hash — a plain `int`. But every node in that bin is there *because it collided*, and in the case that actually matters (a bad `hashCode()`, an attacker, a truncated hash) every one of those `int`s is **identical**. A binary search tree whose comparator returns 0 for every pair is a linked list wearing a costume.

So the tree needs a secondary order, and then a tertiary one. That ladder of fallbacks *is* `find` and `putTreeVal`. Read them as one mechanism and the central fact of treeification falls out: it is a **damage-limitation** structure, not a `TreeMap`. It buys you `O(log n)` only when it can find a real order to sort on, and when it cannot it degrades to something measurably *worse* than the plain chain it replaced.

### The ordering ladder

For two nodes in a tree bin, the comparison that decides placement is, in strict order:

| Rung | What it compares | Cost | What it costs you when it decides |
|---|---|---|---|
| 1 | `p.hash` vs `h` — spread hashes | one `int` compare | Nothing. This is the fast, healthy path: keys land in the same bin but have different hashes. Real `O(log n)`. |
| 2 | `p.key == k \|\| k.equals(pk)` | reference compare, then `equals` | Not an ordering step at all — it is the **hit**, and it returns immediately. |
| 3 | `compareComparables(kc, k, pk)` after `comparableClassFor(k)` passes | one reflective screen (cached in `kc` per call), then a user `compareTo` | Still `O(log n)` search, but every level pays a virtual `compareTo`. |
| 4 | `tieBreakOrder(k, pk)` — class name, then `System.identityHashCode` | string compare + two identity hashes | **Everything.** The order is per-object, so a *lookup* key cannot reproduce it. Search degrades to `O(n)`. |

Rung 4 is where the interesting damage lives, and rung 3 is what a key class has to earn its way onto. The rest of this file is those two rungs.

---

## `find` — the search that is not a binary search

### Mental model

Think of `find` as a binary search that keeps checking whether it is *allowed* to be a binary search. At each node it asks: can I tell which side to go? Hash differs — yes, go. Hash ties but `compareTo` is usable and non-zero — yes, go. Otherwise it admits it cannot tell, **searches the right subtree recursively, and then walks left anyway**. That last arm is the whole story.

### Why it exists

`getNode` (line 573) dispatches to the tree when the bin head is a `TreeNode`, and it must return exactly what a chain scan would have returned — the node whose key is `equals` to the probe. Correctness is non-negotiable; speed is best-effort.

### When it wins and when it loses

It wins whenever rung 1 or rung 3 decides — distinct hashes, or a key class that passes the `Comparable` screen. It loses to a **plain chain** when neither applies: a chain scan of *n* colliding non-`Comparable` keys is `n` `equals` calls with no `TreeNode` overhead; `find` is the same `n` `equals` calls plus recursion frames plus nodes twice the size — exactly the "factor of two in time and space" the class comment concedes (quoted below).

### Mechanism — the source

```java
        final TreeNode<K,V> find(int h, Object k, Class<?> kc) {
            TreeNode<K,V> p = this;
            do {
                int ph, dir; K pk;
                TreeNode<K,V> pl = p.left, pr = p.right, q;
                if ((ph = p.hash) > h)
                    p = pl;
                else if (ph < h)
                    p = pr;
                else if ((pk = p.key) == k || (k != null && k.equals(pk)))
                    return p;
                else if (pl == null)
                    p = pr;
                else if (pr == null)
                    p = pl;
                else if ((kc != null ||
                          (kc = comparableClassFor(k)) != null) &&
                         (dir = compareComparables(kc, k, pk)) != 0)
                    p = (dir < 0) ? pl : pr;
                else if ((q = pr.find(h, k, kc)) != null)
                    return q;
                else
                    p = pl;
            } while (p != null);
            return null;
        }
```
— `java.base/java/util/HashMap.java`, JDK 21, line 2017 (the four-line javadoc at 2013–2016 is omitted from the quote; it states that the `kc` argument caches `comparableClassFor(key)` upon first use). (leaf 3.6.31)

Line by line:

- `TreeNode<K,V> p = this;` — `find` searches from *whatever node it is called on*, not from the root. `getTreeNode` supplies the root; `putTreeVal` deliberately calls it on subtree children.
- `ph > h` → `p = pl`, `ph < h` → `p = pr`. Rung 1. Signed `int` comparison, so negative hashes sort below positive ones — arbitrary but consistent, which is all a search tree needs.
- `(pk = p.key) == k || (k != null && k.equals(pk))` — rung 2, the hit. Identity first because it is free and, for interned strings and enum-like keys, usually true.
- `pl == null` → `p = pr` and `pr == null` → `p = pl`. Cheap short-circuits placed *before* the expensive rungs: with only one child there is nothing to choose, so don't pay for `comparableClassFor` or a `compareTo` to learn that.
- `(kc != null || (kc = comparableClassFor(k)) != null)` — rung 3, with the caching assignment inline. The screen runs at most once per top-level `find`; recursion passes `kc` down.
- `(dir = compareComparables(kc, k, pk)) != 0` — note the `!= 0` guard is part of the *condition*. A `compareTo` that returns 0 for two non-`equals` keys drops through to the next arm rather than picking a side. It must: 0 means "no information", and following either branch would be a guess.
- `(q = pr.find(h, k, kc)) != null` → return; else `p = pl`. **Both subtrees.** This is the arm that matters.

### The diagram

None new here — the treeified bin's layout (`parent`/`left`/`right`/`prev` plus the surviving `next` chain) is D-91 in [04-internals-d-treeify.md](04-internals-d-treeify.md). Read that picture with rung 4 in mind and the dual descent below explains itself.

### `[PROVE]` Why the dual-subtree search is forced, not lazy

Suppose a bin holds *n* keys, all with the same spread hash `h`, none of whose class passes the `Comparable` screen. `putTreeVal` therefore placed every one of them using `tieBreakOrder(k, pk)`, which — the class names being identical — reduces to `System.identityHashCode(a) <= System.identityHashCode(b) ? -1 : 1`.

Now call `map.get(probe)` where `probe` is a *distinct object* that is `equals` to some stored key `s`. `probe` and `s` are different objects, so `System.identityHashCode(probe) != System.identityHashCode(s)` in general. The tree's left/right structure encodes `s`'s identity hash. `probe` does not know it and cannot derive it. **The structure carries zero information the searcher can use.**

So at a hash-tied, non-comparable node, the searcher has exactly two options: guess a side and risk missing a key that is present, or search both. `HashMap` searches both — right recursively, then left iteratively via the loop. Missing a present key would be a correctness bug; being slow is only a performance bug.

Cost: every node is visited, so `find` is **`O(n)`**, not `O(log n)`. And `putTreeVal` calls `find` on the way in (once — see `searched` below), so building a bin of *n* such keys is `n` inserts × `O(n)` search = **`O(n²)`**.

The class comment says this outright:

> ...performance degrades gracefully under accidental or malicious usages in which hashCode() methods return values that are poorly distributed, as well as those in which many keys share a hashCode, **so long as they are also Comparable. (If neither of these apply, we may waste about a factor of two in time and space compared to taking no precautions.** But the only known cases stem from poor user programming practices that are already so slow that this makes little difference.)

— `java.base/java/util/HashMap.java`, JDK 21, lines 166–175 (emphasis added). (leaf 3.6.31)

### `[PROVE]` Measured

Two records with a constant `hashCode()` — everything lands in one bin. One implements `Comparable<itself>`; the other does not. Insert *n* of each into a pre-sized map and time the fill.

```java
import java.util.*;

public class Bench {
    record CmpKey(int id) implements Comparable<CmpKey> {
        @Override public int hashCode() { return 42; }
        @Override public int compareTo(CmpKey o) { return Integer.compare(id, o.id); }
    }
    record PlainKey(int id) {
        @Override public int hashCode() { return 42; }
    }

    static long fill(List<?> keys) {
        Map<Object, Object> m = HashMap.newHashMap(keys.size());
        long t0 = System.nanoTime();
        for (Object k : keys) m.put(k, k);
        long t = System.nanoTime() - t0;
        if (m.size() != keys.size()) throw new AssertionError();
        return t;
    }

    public static void main(String[] a) {
        int[] ns = { 1_000, 2_000, 5_000, 10_000, 20_000 };
        for (int w = 0; w < 3; w++) {                       // warm-up
            List<CmpKey> c = new ArrayList<>();   for (int i = 0; i < 2000; i++) c.add(new CmpKey(i));
            List<PlainKey> p = new ArrayList<>(); for (int i = 0; i < 2000; i++) p.add(new PlainKey(i));
            fill(c); fill(p);
        }
        System.out.printf("%-8s %14s %18s%n", "keys", "Comparable ms", "non-Comparable ms");
        for (int n : ns) {
            List<CmpKey> c = new ArrayList<>();   for (int i = 0; i < n; i++) c.add(new CmpKey(i));
            List<PlainKey> p = new ArrayList<>(); for (int i = 0; i < n; i++) p.add(new PlainKey(i));
            long[] tc = new long[3], tp = new long[3];
            for (int r = 0; r < 3; r++) { tc[r] = fill(c); tp[r] = fill(p); }
            Arrays.sort(tc); Arrays.sort(tp);
            System.out.printf("%-8d %14.2f %18.2f%n", n, tc[1] / 1e6, tp[1] / 1e6);
        }
    }
}
```

Real output, Apple M4 Pro, JDK 21.0.7+8-LTS-245, arm64, median of three runs — **single-shot wall clock, not JMH; the shape is the finding, not the absolute numbers**. `**Unverified:**` the absolute figures below are not JMH-grade and will not reproduce exactly on other hardware.

```
keys      Comparable ms  non-Comparable ms
1000               0.10               0.78
2000               0.20               2.91
5000               0.49              25.90
10000              0.86             123.60
20000              1.48             531.93
```

Read the columns, not the cells. Double *n* and the `Comparable` column **doubles** — `n × log n`, indistinguishable from linear at this scale. Double *n* and the non-`Comparable` column **quadruples** (123.60→531.93 is ×4.3 for ×2 of *n*). That is `O(n²)`; at 20,000 keys the penalty is ×360.

**Insight:** treeification does not save you from a bad `hashCode()`. It saves you from a bad `hashCode()` *on a `Comparable` key*. The fuller three-way version of this experiment — including a bin held below `TREEIFY_THRESHOLD` so it never treeifies at all — and the deliberate-attack framing belong to [04c-internals-d3-collision-dos.md](04c-internals-d3-collision-dos.md) and its D-147.

### The gotcha

`find` recurses on `pr`, but there is no stack-overflow risk: `tieBreakOrder` yields a valid (if meaningless) total order, so the tree stays red-black-balanced and depth stays `O(log n)`. What you lose is the *pruning*, not the balance — a profile of this pathology shows enormous `equals` counts, not a deep stack.

> **`find`** — a tree-bin lookup that descends by hash, then by `compareTo` when the key class passes the `Comparable` screen, and when neither can decide, searches both subtrees rather than risk missing a key that is present.

---

### `getTreeNode` and `compareComparables` (supporting facts)

```java
        final TreeNode<K,V> getTreeNode(int h, Object k) {
            return ((parent != null) ? root() : this).find(h, k, null);
        }
```
— `java.base/java/util/HashMap.java`, JDK 21, line 2043. (leaf 3.6.31)

The whole method is one guard. Callers hold `tab[i]`, the bin head, which `moveRootToFront` normally keeps equal to the root — but concurrent modification or a mid-operation window can leave the head non-root, so a non-null `parent` triggers a walk to `root()` (line 1977) first. `find` is handed `kc == null`, meaning "screen not yet run". `putTreeVal` carries the identical guard.

```java
    @SuppressWarnings({"rawtypes","unchecked"}) // for cast to Comparable
    static int compareComparables(Class<?> kc, Object k, Object x) {
        return (x == null || x.getClass() != kc ? 0 :
                ((Comparable)k).compareTo(x));
    }
```
— `java.base/java/util/HashMap.java`, JDK 21, line 369. (leaf 3.6.32)

**The gotcha lives in `x.getClass() != kc ? 0`.** This is a *second* class check, on the node already in the tree, and it fires per comparison — `comparableClassFor` only vetted the incoming key. If the bin holds a mix of `Base` and `Sub`, this returns 0 for every cross-class pair, which drops that comparison down to rung 4. Returning 0 rather than attempting the compare is the safe answer: an order that some pairs agree on and others do not is not an order, and a red-black tree built on one is corrupt.

> **`compareComparables`** — the guarded `compareTo` call: it returns 0 (meaning "no information") unless both the screened class and the other node's runtime class are exactly the same class.

---

## `putTreeVal` — the ordering ladder in full, and `tieBreakOrder`

### Mental model

`putTreeVal` is a descent that computes `dir` — go left or go right — at every node, then links a new node where the descent falls off the tree. Everything interesting is the four-rung `if/else if` chain that produces `dir`, plus one guarded escape hatch: before it resorts to arbitrary ordering, it does **one** full both-subtrees `find`, because arbitrary ordering means it can no longer trust itself to have looked everywhere.

### Why it exists

`put` cannot just append. It must (a) return the existing node if the key is already present, so the value can be overwritten and the old one returned, and (b) leave a valid red-black tree behind. Rung 4 makes (a) hard, which is why (a) is handled by an explicit search rather than by the descent.

### Mechanism — the source

```java
        final TreeNode<K,V> putTreeVal(HashMap<K,V> map, Node<K,V>[] tab,
                                       int h, K k, V v) {
            Class<?> kc = null;
            boolean searched = false;
            TreeNode<K,V> root = (parent != null) ? root() : this;
            for (TreeNode<K,V> p = root;;) {
                int dir, ph; K pk;
                if ((ph = p.hash) > h)
                    dir = -1;
                else if (ph < h)
                    dir = 1;
                else if ((pk = p.key) == k || (k != null && k.equals(pk)))
                    return p;
                else if ((kc == null &&
                          (kc = comparableClassFor(k)) == null) ||
                         (dir = compareComparables(kc, k, pk)) == 0) {
                    if (!searched) {
                        TreeNode<K,V> q, ch;
                        searched = true;
                        if (((ch = p.left) != null &&
                             (q = ch.find(h, k, kc)) != null) ||
                            ((ch = p.right) != null &&
                             (q = ch.find(h, k, kc)) != null))
                            return q;
                    }
                    dir = tieBreakOrder(k, pk);
                }

                TreeNode<K,V> xp = p;
                if ((p = (dir <= 0) ? p.left : p.right) == null) {
                    Node<K,V> xpn = xp.next;
                    TreeNode<K,V> x = map.newTreeNode(h, k, v, xpn);
                    if (dir <= 0)
                        xp.left = x;
                    else
                        xp.right = x;
                    xp.next = x;
                    x.parent = x.prev = xp;
                    if (xpn != null)
                        ((TreeNode<K,V>)xpn).prev = x;
                    moveRootToFront(tab, balanceInsertion(root, x));
                    return null;
                }
            }
        }
```
— `java.base/java/util/HashMap.java`, JDK 21, line 2133. (leaf 3.6.31)

- `TreeNode<K,V> root = (parent != null) ? root() : this;` — the same head-may-not-be-root guard as `getTreeNode`.
- Rungs 1 and 2 are byte-for-byte the ones in `find`, except that rung 1 sets `dir` instead of moving — the descent is one loop, not two.
- `(kc == null && (kc = comparableClassFor(k)) == null) || (dir = ...) == 0` — read the short-circuit carefully. The left disjunct is true only when the screen has not yet run *and* fails; once `kc` is non-null the left disjunct is false forever and only the `compareTo` is evaluated. If the screen already failed once (`kc` stays `null`), the left disjunct is re-evaluated every level, so `comparableClassFor` runs once **per level** on the failing path, not once per insert. A small extra tax on exactly the path that is already quadratic.
- `boolean searched` — the both-subtrees `find` runs **at most once per insert**, guarded by this flag. Once is enough, and the argument is short: that first `find` starts at `p`'s children and searches *exhaustively* (both sides, all the way down). If the key existed anywhere below `p`, it is returned. And `p` at that moment is the highest node whose hash equals `h`, so the entire hash-equal region of the tree hangs below it. After that search comes back empty, the key provably is not in the tree, and the rest of the loop is only picking a slot.
- `dir = tieBreakOrder(k, pk);` — rung 4, reached only when the search found nothing.

### `tieBreakOrder`

> Tie-breaking utility for ordering insertions when equal hashCodes and non-comparable. We don't require a total order, just a consistent insertion rule to maintain equivalence across rebalancings. Tie-breaking further than necessary simplifies testing a bit.

```java
        static int tieBreakOrder(Object a, Object b) {
            int d;
            if (a == null || b == null ||
                (d = a.getClass().getName().
                 compareTo(b.getClass().getName())) == 0)
                d = (System.identityHashCode(a) <= System.identityHashCode(b) ?
                     -1 : 1);
            return d;
        }
```
— `java.base/java/util/HashMap.java`, JDK 21, line 2058, with its javadoc from lines 2051–2057 quoted above. (leaf 3.6.31)

Two levels. Class name first, separating a `String` from an `Integer` in a mixed bin cheaply. Identity hash second, separating two objects of the same class. It **never returns 0** — `<=` forces `-1`, so even self-comparison yields `-1`. The javadoc is explicit that this is not a mathematical total order, only a *consistent* rule, enough that rebalancing rotations need not re-derive anything.

**The consistency is per-object, and that is the whole defect.** Identity hash is stable for the lifetime of *one* object, so a rotation never reorders existing nodes incorrectly. But it is unrelated across two `equals` objects, so no *lookup* can use it. Hence `find`'s dual descent.

### Insertion — the five lines that do two jobs

```java
                    Node<K,V> xpn = xp.next;
                    TreeNode<K,V> x = map.newTreeNode(h, k, v, xpn);
                    if (dir <= 0) xp.left = x; else xp.right = x;
                    xp.next = x;
                    x.parent = x.prev = xp;
                    if (xpn != null) ((TreeNode<K,V>)xpn).prev = x;
```

`xp.left = x` / `xp.right = x` builds the **tree**. The other four lines splice `x` into the **doubly-linked list** immediately after `xp`. A treeified bin maintains both structures at once; the list is what `untreeify` and iteration use.

- `map.newTreeNode(h, k, v, xpn)` is a hook, overridden in `LinkedHashMap` so its before/after overlay stays maintained on tree inserts.
- **The list order after treeification is no longer insertion order.** New nodes are spliced next to their tree *parent*, not appended at the tail, and `moveRootToFront` hauls the current root to the head of the list on every insert. This is directly observable —

the code is the **Wrong** block under [Pitfalls](#pitfalls) below, and its real output on JDK 21.0.7 is

```
iteration order after treeify: [K[id=3], K[id=0], K[id=1], K[id=2], K[id=4], K[id=5], K[id=6], K[id=7], K[id=8], K[id=9], K[id=10], K[id=11]]
```

`K[id=3]` is the red-black root after the last balance, dragged to the list head by `moveRootToFront`. Everything else survives in insertion order here only because these keys arrive in `compareTo` order; with unordered keys the interleaving is worse. **Any note that describes the surviving `next` chain as "still insertion order" needs qualifying** — it is insertion order *up to* treeification, and thereafter a splice order with the root pulled to the front.

- `moveRootToFront(tab, balanceInsertion(root, x))` — `balanceInsertion` (line 2383) recolours and rotates, and may return a *different* root than it was given; `moveRootToFront` (line 1988) then re-establishes the invariant that `tab[index]` is the root and the list head. The composition is deliberate: the second must consume the first's return. The red-black rotation cases themselves are derived in [../tree-map/02c-internals-a3-fixafterinsertion.md](../tree-map/02c-internals-a3-fixafterinsertion.md); they are not re-derived here.
- `dir <= 0` sends ties left. Since `tieBreakOrder` never returns 0, the `== 0` case can only arrive from `compareComparables` — and rung 3's `dir == 0` already routes into the tie-break branch, so in practice `dir` is never 0 at this line. The `<=` is defensive.

**Interview:** *"What must a key class do to get the full benefit of `HashMap`'s treeification?"* — implement `Comparable<itself>` **directly on the class used as the key**, not on a superclass and not against a supertype parameter. Almost nobody answers this.

> **`putTreeVal`** — a tree-bin insert that descends by hash, then `compareTo`, then an arbitrary identity-based tie-break, performing exactly one exhaustive both-subtrees search before it commits to the arbitrary rung.

---

## `comparableClassFor` — the reflective screen `[RESEARCH]`

### Mental model

Before `HashMap` will let a key's own `compareTo` order a tree, it demands proof that the comparison is *self-consistent across every object that can land in this bin*. The proof it accepts is narrow to the point of pedantry: the class must literally declare `implements Comparable<ThatSameClass>` — not inherit it, not implement it against a supertype, not raw.

### Why it exists

Because a red-black tree built on an inconsistent comparator is silently corrupt — nodes become unreachable, `get` returns null for present keys, `remove` unlinks the wrong subtree. The screen is a **correctness guard, not an optimisation**. Concretely: if `Base implements Comparable<Base>` and `Sub extends Base` are in one bin, `base.compareTo(sub)` and `sub.compareTo(base)` are both `Base`'s logic — but `Sub` may carry state `Base` cannot see, so two nodes can disagree about their relative order depending on which is the receiver. The tree's invariant does not survive that.

### Mechanism — the source

> Returns x's Class if it is of the form "class C implements Comparable<C>", else null.

```java
    static Class<?> comparableClassFor(Object x) {
        if (x instanceof Comparable) {
            Class<?> c; Type[] ts, as; ParameterizedType p;
            if ((c = x.getClass()) == String.class) // bypass checks
                return c;
            if ((ts = c.getGenericInterfaces()) != null) {
                for (Type t : ts) {
                    if ((t instanceof ParameterizedType) &&
                        ((p = (ParameterizedType) t).getRawType() ==
                         Comparable.class) &&
                        (as = p.getActualTypeArguments()) != null &&
                        as.length == 1 && as[0] == c) // type arg is c
                        return c;
                }
            }
        }
        return null;
    }
```
— `java.base/java/util/HashMap.java`, JDK 21, line 345, with its javadoc from lines 341–344 quoted above. (leaf 3.6.32)

- `x instanceof Comparable` — necessary, nowhere near sufficient. Every rejection below is of an object that passes this line.
- `if ((c = x.getClass()) == String.class) return c;` — **Insight:** a hardcoded fast path for exactly one class, with the JDK's own comment `// bypass checks`. `String` is the overwhelmingly common map key and the reflective walk below allocates `Type` objects, so the JDK spends a single reference compare to skip it. One class earns a special case in `java.util.HashMap`; that is how dominant `String` keys are.
- `c.getGenericInterfaces()` — the generic `Type[]` of the interfaces **this exact class declares in its `implements` clause**. Not inherited from a superclass. Not transitively from a superinterface. This single fact causes every surprising rejection.
- The loop demands four things at once: the interface is a `ParameterizedType` (so a raw `Comparable` is out), its raw type is `Comparable.class`, it has exactly one type argument, and that argument is `== c` — **reference-identical** to the class object itself.

### What actually passes

You cannot call `comparableClassFor` from your own code — it is package-private in `java.util`. It *can* be invoked reflectively with the module opened, which is what this program does (`--add-opens java.base/java.util=ALL-UNNAMED`), so the results below are the real JDK method's answers, not a reimplementation.

```java
import java.lang.reflect.*;
import java.time.LocalDate;

public class Screen {
    static Method ccf;
    static { try {
        ccf = Class.forName("java.util.HashMap")
                .getDeclaredMethod("comparableClassFor", Object.class);
        ccf.setAccessible(true);
    } catch (Exception e) { throw new RuntimeException(e); } }

    static String screen(Object x) {
        try { Object r = ccf.invoke(null, x);
              return r == null ? "null (FAILS)" : ((Class<?>) r).getSimpleName() + " (passes)";
        } catch (Exception e) { return "error: " + e; }
    }

    static class Base implements Comparable<Base> { public int compareTo(Base o) { return 0; } }
    static class Sub extends Base { }
    static class WrongArg implements Comparable<Base> { public int compareTo(Base o) { return 0; } }
    @SuppressWarnings("rawtypes")
    static class Raw implements Comparable { public int compareTo(Object o) { return 0; } }
    enum E { A, B }
    record R(int x) implements Comparable<R> {
        public int compareTo(R o) { return Integer.compare(x, o.x); }
    }

    public static void main(String[] a) {
        Object[] xs = { "s", 1, 1L, LocalDate.now(), new Base(), new Sub(),
                        new WrongArg(), new Raw(), E.A, new R(1), new Object() };
        for (Object x : xs)
            System.out.printf("%-14s -> %s%n", x.getClass().getSimpleName(), screen(x));
        System.out.println("\ngetGenericInterfaces() as declared:");
        for (Class<?> c : new Class<?>[]{ Sub.class, E.class, R.class, Integer.class })
            System.out.printf("%-10s %s%n", c.getSimpleName(),
                java.util.Arrays.toString(c.getGenericInterfaces()));
    }
}
```

Real output (`javac Screen.java && java --add-opens java.base/java.util=ALL-UNNAMED Screen`, JDK 21.0.7):

```
String         -> String (passes)
Integer        -> Integer (passes)
Long           -> Long (passes)
LocalDate      -> null (FAILS)
Base           -> Base (passes)
Sub            -> null (FAILS)
WrongArg       -> null (FAILS)
Raw            -> null (FAILS)
E              -> null (FAILS)
R              -> R (passes)
Object         -> null (FAILS)

getGenericInterfaces() as declared:
Sub        []
E          []
R          [java.lang.Comparable<Screen$R>]
Integer    [java.lang.Comparable<java.lang.Integer>, interface java.lang.constant.Constable, interface java.lang.constant.ConstantDesc]
```

| Key class | Passes? | Why |
|---|---|---|
| `String` | yes | Hardcoded bypass at line 348, before any reflection. |
| `Integer`, `Long` | yes | Declare `Comparable<Integer>` / `Comparable<Long>` directly. |
| `record R(int) implements Comparable<R>` | yes | The declared interface is `Comparable<R>` with `as[0] == R.class`. |
| `class Base implements Comparable<Base>` | yes | The canonical passing shape. |
| `class Sub extends Base` | **no** | `Sub.getGenericInterfaces()` is `[]` — the interface is the *superclass's*, not `Sub`'s. |
| `class C implements Comparable<Base>` | **no** | `as[0]` is `Base`, not `C`. |
| `class C implements Comparable` (raw) | **no** | Not a `ParameterizedType`. |
| `enum E` | **no** | `E.getGenericInterfaces()` is `[]`; `Comparable<E>` is declared on `java.lang.Enum<E>`, a superclass. |
| `LocalDate` | **no** | Declares `ChronoLocalDate`; `Comparable<ChronoLocalDate>` lives on that *superinterface*, and its argument would be `ChronoLocalDate`, not `LocalDate`, either way. |
| `Object` | **no** | Not `Comparable` at all. |

Two of those are genuinely surprising, and both were verified rather than recalled. **Enums fail** — `E.getGenericInterfaces()` really is empty. **`LocalDate` fails** — its declared interfaces are `[Temporal, TemporalAdjuster, ChronoLocalDate, Serializable]`, and `Comparable<ChronoLocalDate>` sits on `ChronoLocalDate`: wrong declaring type *and* wrong type argument. In practice neither matters much, since enum and `LocalDate` hashes are well distributed and their bins almost never treeify — but a key type that extends or wraps one inherits the rejection.

### The gotcha

The screen looks at the **incoming key only**. `compareComparables`'s `x.getClass() != kc` check is the matching guard on the node already in the tree, and it fires per comparison. Both are needed: the first rejects a key whose *class shape* is unsafe, the second rejects a *pairing* that is unsafe even when both classes individually pass.

> **`comparableClassFor`** — a reflective screen that returns the key's class only when that class literally declares `implements Comparable<ThatClass>`, so a tree bin never orders nodes with a comparator two of its nodes might disagree about.

---

## Version behaviour: JDK 8 vs JDK 21

Verified by diffing `/tmp/jdk8src/java/util/HashMap.java` against `/tmp/jdk21src/java.base/java/util/HashMap.java`.

| Method | JDK 8 line | JDK 21 line | Behavioural change |
|---|---|---|---|
| `comparableClassFor` | 346 | 345 | **None.** The only difference is cosmetic: JDK 8's indexed `for (int i = 0; i < ts.length; ++i)` became an enhanced `for (Type t : ts)`. Identical semantics. |
| `compareComparables` | 370 | 369 | **None.** Byte-for-byte identical. |
| `find` | 1858 | 2017 | **None** in the body. JDK 21 added one javadoc line, *"Finds the node starting at root p with the given hash and key."* |
| `getTreeNode` | 1888 | 2043 | **None.** |
| `tieBreakOrder` | 1899 | 2058 | **None.** |
| `putTreeVal` | 1974 | 2133 | **None.** Byte-for-byte identical, all 39 lines. |

Stated plainly: **this entire mechanism has not changed since it was introduced in JDK 8.** Everything on this page applies unchanged to 8, 11, 17 and 21. That is unusual for `HashMap` internals — `tableSizeFor` next door, for instance, was rewritten in JDK 9 to use `Integer.numberOfLeadingZeros`.

---

## Pitfalls

### Assuming a treeified bin iterates in key order

**Wrong**

```java
record K(int id) implements Comparable<K> {
    @Override public int hashCode() { return 7; }          // force one bin
    @Override public int compareTo(K o) { return Integer.compare(id, o.id); }
}
Map<K,Integer> m = new HashMap<>();
for (int i = 0; i < 12; i++) m.put(new K(i), i);
System.out.println(m.keySet());
// [K[id=3], K[id=0], K[id=1], K[id=2], K[id=4], K[id=5], K[id=6],
//  K[id=7], K[id=8], K[id=9], K[id=10], K[id=11]]        -- id=3 first
```

**Right**

```java
Map<K,Integer> m = new TreeMap<>();       // or sort a copy of the key set
for (int i = 0; i < 12; i++) m.put(new K(i), i);
System.out.println(m.keySet());
// [K[id=0], K[id=1], K[id=2], K[id=3], K[id=4], K[id=5], K[id=6],
//  K[id=7], K[id=8], K[id=9], K[id=10], K[id=11]]        -- ordering is the contract
```

**Why people believe it:** "treeified bins use `compareTo`" is true, so it sounds like the bin is a sorted structure. It is not. Its primary sort key is the spread hash; `compareTo` is only a tiebreak *within equal hashes*, and only if the screen passes; below that it is identity hash. And iteration never walks the tree at all — it walks the `next` chain, which `moveRootToFront` reorders on every insert. Only `TreeMap`/`LinkedHashMap` make ordering a contract.

---

## Cheat sheet

| Item | Fact |
|---|---|
| Ordering ladder | hash → `equals` (hit, returns) → `compareTo` if screened → `tieBreakOrder` |
| `find` (2017) | Descends by hash/`compareTo`; on a tie with no order, recurses right **then** falls through left |
| Dual descent cost | `O(n)` per lookup; `O(n²)` to build a bin of *n* non-`Comparable` colliding keys |
| Measured penalty | ×360 at 20,000 same-hash keys (M4 Pro, JDK 21.0.7, single-shot) |
| `getTreeNode` (2043) | `((parent != null) ? root() : this).find(h, k, null)` — head-may-not-be-root guard |
| `tieBreakOrder` (2058) | Class name, then `identityHashCode`; **never returns 0**; per-object, so lookups cannot use it |
| `putTreeVal` (2133) | One exhaustive both-subtrees `find` per insert, gated by `boolean searched` |
| Insert links | `xp.left/right = x` (tree) **and** `xp.next`/`x.prev`/`xpn.prev` (list) — both maintained |
| Post-treeify list order | **Not** insertion order — splice-next-to-parent, plus `moveRootToFront` |
| `comparableClassFor` (345) | Passes only `class C implements Comparable<C>`, declared on C itself; `String` bypasses |
| Fails the screen | subclass of a `Comparable` class, `Comparable<Supertype>`, raw `Comparable`, **enum**, **`LocalDate`** |
| `compareComparables` (369) | Returns 0 unless `x.getClass() == kc` — the second, per-comparison class guard |
| JDK 8 vs 21 | All five methods behaviourally identical; only cosmetic loop and javadoc edits |

---

## Self-test

**Q1.** In `find`, why is `pl == null → p = pr` placed *before* the `comparableClassFor` arm rather than after?

<details><summary>Answer</summary>

With only one child there is nothing to choose — the search must go to the non-null side regardless of what any comparison says. Placing the check first avoids paying for a reflective screen and a virtual `compareTo` to learn something already determined by the tree's shape. It is a pure cost optimisation with no behavioural effect.

</details>

**Q2.** Why must `find` search *both* subtrees when the hash ties and no usable `compareTo` exists?

<details><summary>Answer</summary>

Those nodes were placed by `tieBreakOrder`, whose deciding value is `System.identityHashCode` — a property of the specific stored object. The lookup key is a different object that is merely `equals` to it, so it has a different identity hash and cannot reproduce the decision that placed the node. The tree structure therefore encodes nothing the searcher can act on, and guessing a side would miss keys that are present. Searching both is the only correct option.

</details>

**Q3.** A bin holds 10,000 keys, all with hash 42, of a class that does not implement `Comparable`. What is the cost of building it, and does treeification help?

<details><summary>Answer</summary>

`O(n²)`. Each `putTreeVal` performs one exhaustive both-subtrees `find`, which is `O(n)` because no rung above `tieBreakOrder` can decide, and there are *n* inserts. Treeification actively hurts: the class comment concedes "about a factor of two in time and space" versus a plain chain, since `TreeNode` is roughly twice the size of `Node` and you pay recursion and rebalancing on top of the same *n* `equals` calls a chain scan would have made. Measured on an M4 Pro at JDK 21.0.7, 20,000 such keys took 532 ms against 1.5 ms for the same keys made `Comparable`.

</details>

**Q4.** `class Sub extends Base` and `Base implements Comparable<Base>`. Does a tree bin of `Sub` instances use `compareTo`? Why is the JDK's answer the safe one?

<details><summary>Answer</summary>

No. `comparableClassFor` reads `Sub.class.getGenericInterfaces()`, which returns `[]` — the interface is declared on `Base`, and the method deliberately does not walk superclasses. Verified by reflective invocation of the real method on JDK 21.0.7.

It is the safe answer because inherited `compareTo` is not guaranteed consistent across subclasses. If `Sub` and a sibling `Sub2` share a bin, both compare via `Base`'s logic, which may see them as equal while they are not `equals` — or order them differently depending on the receiver. A red-black tree built on a comparator its own nodes disagree about becomes unreachable in parts, and `get` starts returning null for keys that are present. Correctness first, speed second.

</details>

**Q5.** Why does `putTreeVal` guard its both-subtrees `find` with `boolean searched` — why is once per insert enough?

<details><summary>Answer</summary>

The moment the tie-break branch is first entered, `p` is the highest node in the tree whose hash equals `h`, so the entire hash-equal region hangs below `p`. The `find` calls launched from `p.left` and `p.right` are exhaustive — both subtrees, all the way down — so if the key were anywhere in the tree it would be returned right there. When it comes back empty, the key provably is not present, and the remainder of the descent is only choosing an insertion slot. Repeating the search at deeper levels could only re-cover ground already covered.

</details>

**Q6.** After a bin treeifies, is the surviving `next` chain still in insertion order?

<details><summary>Answer</summary>

No. Two things break it. `putTreeVal` splices a new node in *immediately after its tree parent* (`xpn = xp.next; xp.next = x; x.prev = xp; xpn.prev = x`), not at the tail. And `moveRootToFront` pulls the current red-black root to the head of the list after every insert, so a rebalance that changes the root reorders the chain. Demonstrated above: inserting `K[id=0]`..`K[id=11]` into one bin yields an iteration order beginning `K[id=3]`.

</details>

**Q7.** Which of `String`, `Integer`, `LocalDate` and an `enum` pass `comparableClassFor`?

<details><summary>Answer</summary>

`String` and `Integer` pass; `LocalDate` and enums fail. `String` passes via the hardcoded `== String.class` bypass at line 348, before any reflection. `Integer` declares `Comparable<Integer>` directly. An enum's own `getGenericInterfaces()` is empty — `Comparable<E>` is declared on the `java.lang.Enum` superclass. `LocalDate` declares `ChronoLocalDate`, and `Comparable<ChronoLocalDate>` sits on that superinterface with the wrong type argument besides. All four verified by reflectively invoking the real JDK 21.0.7 method.

</details>

**Q8.** Has any of this changed between JDK 8 and JDK 21?

<details><summary>Answer</summary>

Behaviourally, no. `putTreeVal` (JDK 8 line 1974, JDK 21 line 2133) is byte-for-byte identical. `find`, `getTreeNode`, `tieBreakOrder` and `compareComparables` differ only by one added javadoc sentence on `find`. `comparableClassFor` changed an indexed `for` loop to an enhanced `for` — cosmetic. Everything on this page applies unchanged to 8, 11, 17 and 21.

</details>

---

## Open questions

- The absolute benchmark figures in the `[PROVE]` section are `**Unverified:**` as precise measurements — they are single-shot wall clock on one machine (Apple M4 Pro, JDK 21.0.7+8-LTS-245, arm64), not JMH, and include no dead-code-elimination or allocation-profile controls. The *scaling shape* (linear-ish vs quadratic) is reproducible and is the actual claim; the millisecond values are indicative only.

---

**Leaves covered:** 3.6.31, 3.6.32 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none new — the treeified bin (D-91) and the inheritance chain (D-96) are embedded in [04-internals-d-treeify.md](04-internals-d-treeify.md)
**Target version:** Java 21 LTS
**Lines:** 600
