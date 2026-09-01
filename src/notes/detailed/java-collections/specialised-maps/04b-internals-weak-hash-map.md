# 02 Java Collections — Specialised maps and sets — INTERNALS (§3.11.8–3.11.14)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [specialised-maps/04a-internals-identity-sizing-and-uses.md](04a-internals-identity-sizing-and-uses.md) · Next: [immutable-collections/01-views-copies-snapshots.md](../immutable-collections/01-views-copies-snapshots.md)

`IdentityHashMap`'s internals are the two preceding files' subject — the interleaved `Object[] table`, the identity-hash scramble and linear probing in [04-internals-identity-weak.md](04-internals-identity-weak.md), its sizing constants, `NULL_KEY` and documented contract violation in [04a-internals-identity-sizing-and-uses.md](04a-internals-identity-sizing-and-uses.md). This file is `WeakHashMap` only, line by line, against the real source. All citations are to `java.base/java/util/WeakHashMap.java` in **JDK 21.0.7+8-LTS-245**. Every transcript below was produced on **macOS (Darwin 25.5.0, arm64), HotSpot 21.0.7+8-LTS-245, default G1**. The BASICS/INTERMEDIATE story — what a `WeakReference` is, when to reach for the class, the call-site survey — is [03b-weak-hash-map.md](03b-weak-hash-map.md); this file owns the mechanism.

---

## Where the class sits, in one table

| Field / constant | Line | Value or type | Why it matters here |
|---|---|---|---|
| `DEFAULT_INITIAL_CAPACITY` | `:142` | `16` | Plain `HashMap` sizing. **Not** `IdentityHashMap`'s `32`. |
| `MAXIMUM_CAPACITY` | `:149` | `1 << 30` | Power-of-two table; `indexFor` masks against `length-1`. |
| `DEFAULT_LOAD_FACTOR` | `:154` | `0.75f` | **Not** `IdentityHashMap`'s implicit two-thirds. |
| `Entry<K,V>[] table` | `:159` | array | Separate chaining via `Entry.next` — **no treeification, ever**. |
| `private int size` | `:164` | raw counter | Mutated by `expungeStaleEntries()`, so it is not the live-key count. |
| `private final ReferenceQueue<Object> queue` | `:179` | one per instance | The GC's mailbox for this map. |
| `int modCount` | `:190` | fail-fast counter | **Not** bumped by expunge — see pitfalls. |

**[NUM]** `MAXIMUM_CAPACITY = 1 << 30 = 1,073,741,824`. A full `Entry[]` of that length costs 2^30 × 4 bytes (compressed oops) = 4,294,967,296 bytes = **4 GiB of references alone**, before a single `Entry` object. That is why the bound exists and why the next doubling would overflow `int`. **Insight:** the class was written by Mark Reinhold for 1.2 and never retrofitted with `HashMap`'s Java 8 machinery — no `TreeNode`, no `TREEIFY_THRESHOLD`, no `spread()`. It still uses the pre-Java-8 supplemental hash at `:308-316`, `h ^= (h >>> 20) ^ (h >>> 12); return h ^ (h >>> 7) ^ (h >>> 4);`, four shifts against `HashMap.hash`'s single `h ^ (h >>> 16)`. So a hostile key distribution degrades a bucket to **O(n)**, not `HashMap`'s O(log n): you buy automatic key eviction and give up treeification.

---

## The entry *is* the reference

### `Entry<K,V> extends WeakReference<Object>` — leaf 3.11.8

**Mental model.** In a `HashMap` the entry is a box holding a key and a value. In a `WeakHashMap` the entry is a *luggage tag the collector is allowed to cut off*. The key is not in a field of the entry — it is in the entry's own `referent` slot, inherited from `java.lang.ref.Reference`. The entry does not *have* a weak reference to its key; the entry **is** the weak reference to its key. Once that sentence lands, four otherwise-arbitrary design decisions fall out on their own.

**Why it exists.** The obvious alternative is worse: `class Entry { WeakReference<K> key; V value; }` allocates two objects per mapping and — the killer — gives you no route from a dequeued reference back to the entry containing it. `ReferenceQueue.poll()` hands you the `Reference`; if the `Reference` is a field *inside* the entry, you have a reference and no idea which bucket it lives in, so you need a second map from reference to entry, which is the problem you were solving. Making the entry itself the `Reference` means `poll()` hands you the entry, carrying its own `hash` and `next`, so cleanup is a straight bucket walk. Before `java.lang.ref` (pre-1.2) you could not build this at all.

**When to imitate it, and when not.** Imitate it when you are writing a cache whose nodes must be reclaimable and you own the node class — Guava's `LocalCache` does exactly this. Do **not** imitate it when the referent is not the natural identity of the node; then `Cleaner` (Java 9+) with a separate state object wins, because subclassing `Reference` and holding a strong field that reaches the referent is precisely the leak in leaf 3.11.11.

**How it works.** The full declaration, `:708-727`:

```java
    /**
     * The entries in this hash table extend WeakReference, using its main ref
     * field as the key.
     */
    private static class Entry<K,V> extends WeakReference<Object> implements Map.Entry<K,V> {
        V value;
        final int hash;
        Entry<K,V> next;

        /**
         * Creates new entry.
         */
        Entry(Object key, V value,
              ReferenceQueue<Object> queue,
              int hash, Entry<K,V> next) {
            super(key, queue);
            this.value = value;
            this.hash  = hash;
            this.next  = next;
        }
```

Every line:

- `private static class Entry<K,V>` — `static`, so no synthetic `this$0` back-pointer to the enclosing map. A non-static inner class would add 4–8 bytes per entry for nothing.
- `extends WeakReference<Object>` — the key lives in `Reference.referent`, a field the JVM special-cases. **The type argument is `Object`, not `K`,** for two real reasons: null keys are stored as the sentinel `NULL_KEY` (`:271`), a bare `Object` that could never satisfy `WeakReference<K>`; and the shared `ReferenceQueue<Object>` at `:179` must accept every entry, but `ReferenceQueue` is invariant in its type parameter, so it cannot receive a `WeakReference<K>`. `getKey()` at `:729-732` pays for this with `@SuppressWarnings("unchecked")`.
- `implements Map.Entry<K,V>` — so `entrySet()` can hand the entry itself out. Consequence: a `Map.Entry` you obtained from a `WeakHashMap` can start returning `null` from `getKey()` in your hands.
- `V value;` — **strong and non-final**. Strong because the map must keep the value alive while the mapping lives; non-final because both `setValue` and `expungeStaleEntries` write it.
- `final int hash;` — cached, and this is the "oh, *that's* why" of the class. Below.
- `Entry<K,V> next;` — chaining link, non-final because expunge and `transfer` rewrite chains.
- `super(key, queue)` — the key is handed to `Reference`'s constructor with the map's own queue. This is the moment the entry is registered with the GC. There is no `this.key = key` anywhere in the class, and no field it could go into.

**Why the key must go through `super(...)` rather than into a field.** `Reference.referent` is not an ordinary field. HotSpot knows its offset (`java_lang_ref_Reference::referent_offset`), treats loads of it as an intrinsic with a GC load barrier, and the collector's reference-processing phase walks discovered `Reference` objects and clears exactly that slot. A field you declare yourself gets none of that. "Put the key in a field" is not a stylistic alternative — it is impossible to make the GC clear it.

**Why the entry caches `hash` instead of recomputing it.** The syllabus omits this and interviewers love it. `expungeStaleEntries()` needs a dead entry's bucket index to unlink it, and computing that index needs the hash. But by the time expunge runs, `get()` returns `null` — **the key object is gone and `key.hashCode()` is no longer callable at all.** There is no recovering the index from a cleared reference. The hash *must* have been snapshotted at insertion or the entry could never be located again. `final int hash` is not an optimisation; it is the only thing that makes cleanup possible.

Contrast `HashMap.Node` (`HashMap.java:281-285`): `final int hash; final K key; V value; Node<K,V> next;`. `HashMap.Node` also caches `hash`, but for `HashMap` that is a pure speed win, because `final K key` is right there and `hashCode()` could always be called again. Same field, entirely different necessity. `HashMap.Node` declares **four** fields and extends nothing; `WeakHashMap.Entry` declares **three** and inherits `referent`, `queue`, `next` (the queue's own link) and `discovered` from `Reference`.

![D-118: WeakHashMap.Entry extends WeakReference. Look at where the key lives — in the inherited referent slot the GC is allowed to null out — while value, hash and next are ordinary strong fields the GC never touches. Compare HashMap.Node beside it, where key is a declared final K field that nothing can clear.](../diagrams/D-118-weakhashmap-entry-is-weakreference.svg)

**Minimal concrete example, and leaf 3.11.8's `[PROVE]`.** `EntryIterator.next()` at `:853-855` returns `nextEntry()`, which is the raw `Entry` object — so the claim is directly observable from user code, with no reflection:

```java
public class EntryIsReference {

    public static void main(String[] args) {
        Map.Entry<String, String> weak =
                new WeakHashMap<>(Map.of("k", "v")).entrySet().iterator().next();
        Map.Entry<String, String> strong =
                new HashMap<>(Map.of("k", "v")).entrySet().iterator().next();

        System.out.println("WeakHashMap entry class = " + weak.getClass().getName());
        System.out.println("  instanceof Reference  = " + (weak instanceof Reference<?>));
        System.out.println("HashMap     entry class = " + strong.getClass().getName());
        System.out.println("  instanceof Reference  = " + (strong instanceof Reference<?>));
        System.out.println("referent via Reference.get() = "
                + ((Reference<?>) weak).get() + "   getKey() = " + weak.getKey());
    }
}
```

Real output, HotSpot 21.0.7+8-LTS-245 on macOS arm64:

```
WeakHashMap entry class = java.util.WeakHashMap$Entry
  instanceof Reference  = true
HashMap     entry class = java.util.HashMap$Node
  instanceof Reference  = false
referent via Reference.get() = k   getKey() = k
```

That is the claim, proven rather than asserted. A `Map.Entry` handed out by a `WeakHashMap` **is** a `java.lang.ref.Reference`, and casting it to `Reference` and calling `get()` returns the map's key — the same object `getKey()` returns, because `getKey()` is nothing but `unmaskNull(get())`. The `HashMap` line is the control: its entry is not a `Reference` at all, so there is no referent slot and nothing the collector could clear. **The gotcha.** `Entry` inherits `Reference.get()`, and `getKey()` at `:729-732` is `return (K) WeakHashMap.unmaskNull(get());`. `get()` can return `null` at any instant, so `entry.getKey()` may go `null` mid-loop. Worse, `Entry.hashCode()` at `:758-762` is `Objects.hashCode(k) ^ Objects.hashCode(v)` — so **an entry's own `hashCode()` changes when its key dies**, from `keyHash ^ valueHash` to `0`. Never put a `WeakHashMap`'s `Map.Entry` into another `HashSet`.

> **Definition.** `WeakHashMap.Entry` is a `WeakReference<Object>` that also implements `Map.Entry`: the mapping's key occupies the reference's GC-managed referent slot rather than a declared field, which is simultaneously what lets the key be collected and what lets `ReferenceQueue.poll()` hand cleanup code the exact entry to unlink.

---

## The queue and `expungeStaleEntries()`

### The one method that does all the work — leaf 3.11.9 `[SOURCE]`

**Mental model.** The map has an inbox (`queue`). The GC posts dead entries into it. Nobody reads the inbox on a timer — there is no cleaner thread, no daemon, nothing. It is drained *by the next caller who happens to walk past*, as a side effect of asking the map an ordinary question. A `WeakHashMap` is garbage-collected by its own users, lazily; if nobody calls anything, the mail piles up forever.

**Why it exists.** A background sweeper per map instance would be absurd; a shared sweeper would need locks against user threads. Amortising cleanup onto the calling thread costs nothing when the map is in use and correctly costs nothing when it is not. **When not to accept it:** if reclamation latency matters, `WeakHashMap` is the wrong tool — reach for `Cleaner` or an explicit bounded cache, since no `WeakHashMap` configuration makes cleanup eager.

**How it works.** `:325-355`, in full:

```java
    /**
     * Expunges stale entries from the table.
     */
    private void expungeStaleEntries() {
        for (Object x; (x = queue.poll()) != null; ) {
            synchronized (queue) {
                @SuppressWarnings("unchecked")
                    Entry<K,V> e = (Entry<K,V>) x;
                int i = indexFor(e.hash, table.length);

                Entry<K,V> prev = table[i];
                Entry<K,V> p = prev;
                while (p != null) {
                    Entry<K,V> next = p.next;
                    if (p == e) {
                        if (prev == e)
                            table[i] = next;
                        else
                            prev.next = next;
                        // Must not null out e.next;
                        // stale entries may be in use by a HashIterator
                        e.value = null; // Help GC
                        size--;
                        break;
                    }
                    prev = p;
                    p = next;
                }
            }
        }
    }
```

Every line:

- `for (Object x; (x = queue.poll()) != null; )` — `poll()` is non-blocking and returns `null` the instant the queue is empty, so expunge is O(entries newly dead), not O(table). An idle map with nothing dead pays one read.
- `synchronized (queue)` — the surprising line. `WeakHashMap` is not thread-safe, so this is not guarding the user's threads. `ReferenceQueue`'s own enqueue path synchronizes on the queue, and the JVM's *reference-handler* thread enqueues concurrently with your thread walking the table; the lock serialises this map's unlink against enqueueing on the same queue. Note it is taken **inside** the loop, once per dead entry, deliberately, so a long drain does not hold the lock throughout and stall the reference handler.
- `Entry<K,V> e = (Entry<K,V>) x;` — the cast that only works because the entry *is* the reference.
- `int i = indexFor(e.hash, table.length);` — the bucket, from the cached hash; `indexFor` at `:321-323` is `h & (length-1)`. Impossible without `final int hash`, since `e.get()` is `null` by now. It reads the `table` field directly, not `getTable()`, which would recurse.
- the `prev`/`p` walk — plain singly-linked removal. If the dead entry is the head (`prev == e`) rewrite `table[i]`, else relink `prev.next`. Entries are matched by **identity** (`p == e`) and never by equality; equality is unavailable, the key is gone.
- `// Must not null out e.next;` — load-bearing comment. A `HashIterator` may be parked *on* this entry and its `next()` needs `e.next` to continue; nulling it would strand the iterator at a chain end and silently skip live mappings. So the class deliberately leaves a dangling forward pointer from an unlinked entry into the live chain.
- `e.value = null; // Help GC` — **and this matters even though the entry is being unlinked.** That dangling `e.next` means an unlinked stale entry is still reachable from a live iterator and from other stale entries, so the entry object may outlive its removal by an arbitrary interval and would keep its value alive with it. More sharply: if the value strongly reaches a *different* live key in the same map, retaining the value pins that unrelated mapping. Nulling converts "entry unlinked" into "value actually reclaimable".
- `size--` — decremented here and nowhere else in the GC path. This is why `size()` mutates the map.

**Where it is actually called from — the syllabus is imprecise here.** Leaf 3.11.9 says "invoked from `getTable`, `size`, `resize`, etc." The `etc.` conceals two real exceptions. Verified:

| Call site | Line | Nature |
|---|---|---|
| `getTable()` | `:361` | Direct. The funnel — `get`, `put`, `remove`, `containsKey`, `containsValue`, `resize`, `putAll` and the spliterators reach expunge only through here. |
| `size()` | `:374` | Direct, **behind an `if (size == 0) return 0;` fast path at `:372`**. An empty-looking map never drains. |
| `resize(int)` | `:516` | Direct, *in addition* to the `getTable()` at `:497` — but only in the shrink-restore `else` branch. |
| `clear()` | `:659-673` | **Does NOT call it.** Drains the queue by hand, twice. |
| `HashIterator()` | `:788` | Once only, via `isEmpty()` → `size()`. `hasNext()` at `:792` reads `table` directly. |

`clear()`, `:659-673`, is the first exception. Its body is `while (queue.poll() != null);`, then `modCount++; Arrays.fill(table, null); size = 0;`, then `while (queue.poll() != null);` again. No per-entry unlink is needed because `Arrays.fill` blanks every bucket and `size = 0` resets the counter — the comment at `:660-661` says exactly that. But the queue still must be drained, because **an entry sitting in a `ReferenceQueue` is strongly reachable from the queue**, so undrained mail pins entries and their values even after the table is blank. The second drain's comment blames array allocation, a leftover from when `clear()` allocated a fresh table; today `Arrays.fill` allocates nothing, but the drain still earns its place, because filling a large table takes long enough for a concurrent collector to clear and enqueue more referents mid-`clear()`. The iterator is the second exception, `:769-792`:

```java
        /**
         * Strong reference needed to avoid disappearance of key
         * between hasNext and next
         */
        private Object nextKey;

        HashIterator() {
            index = isEmpty() ? 0 : table.length;
        }

        public boolean hasNext() {
            Entry<K,V>[] t = table;
```

The constructor is the only place iteration expunges — `isEmpty()` funnels to `size()` — and `hasNext()` then reads the `table` field directly, bypassing `getTable()`, so no expunge happens mid-walk. `nextKey`, and its sibling `currentKey` at `:785` ("Strong reference needed to avoid disappearance of key between `nextEntry()` and any use of the entry"), are the good part: the iterator deliberately *strengthens* the key it is about to hand you and holds it until you have moved past. That is why `for (K k : map.keySet())` cannot have `k` turn `null` under you mid-body. It also makes an iterator a leak by design — walking a 1M-entry `WeakHashMap` pins one key at a time, but pins it hard.

**Pitfall:** *"`expungeStaleEntries` bumps `modCount`, so a GC during iteration throws `ConcurrentModificationException`."* Wrong — there is no `modCount++` anywhere in the body. GC-driven removal is deliberately invisible to fail-fast checking, because throwing CME for a removal the user did not cause would make the class unusable. **Symptom:** defensive retry loops around iteration that can never fire. **Fix:** none needed; iteration is safe against expunge, and the strong `nextKey`/`currentKey` are what make it safe.

> **Definition.** `expungeStaleEntries()` is `WeakHashMap`'s entire reclamation mechanism: a non-blocking drain of the per-map `ReferenceQueue` that recomputes each dead entry's bucket from its cached `hash`, unlinks it by identity, nulls its value and decrements `size` — invoked lazily from `getTable()`, `size()` and `resize()` on the caller's thread, never by a background thread.

---

## Null keys, and the two-step key comparison

**`NULL_KEY` masking** — `WeakHashMap` permits one `null` key, but `new WeakReference(null, queue)` is a reference to nothing that is trivially always cleared, so the mapping would evaporate at once. `:268-285` substitutes a sentinel: `private static final Object NULL_KEY = new Object();` with `maskNull(key)` returning `NULL_KEY` for `null` and `unmaskNull(key)` returning `null` for `NULL_KEY`. Every entry point masks on the way in (`get:407`, `getEntry:437`, `put:460`, `removeMapping:631`) and `Entry.getKey():731` unmasks on the way out. This is the first of the two reasons the referent type parameter must be `Object`. **Gotcha:** `NULL_KEY` is a `static final` singleton, so it is strongly reachable from the class forever, so a `null`-keyed mapping in a `WeakHashMap` is **immortal**.

**`matchesKey`, `:287-299`** — comparing a key against a possibly-cleared entry looks trivial and is not:

```java
    private boolean matchesKey(Entry<K,V> e, Object key) {
        // check if the given entry refers to the given key without
        // keeping a strong reference to the entry's referent
        if (e.refersTo(key)) return true;

        // then check for equality if the referent is not cleared
        Object k = e.get();
        return k != null && key.equals(k);
    }
```

`Reference.refersTo(Object)` is `@since 16` per its javadoc, and it is the whole point of this shape. Calling `e.get()` *resurrects* the referent into a strong local for the duration — under a concurrent collector (G1, ZGC, Shenandoah) that means a load barrier and, worse, it can keep alive a referent the collector was about to clear, delaying reclamation by a whole cycle. `refersTo` answers "is your referent this object?" without ever producing a strong reference, so the fast path — identity match, overwhelmingly the common case since you usually pass the same object you put — costs no barrier at all, and `get()` is reached only when identity failed and `equals` is genuinely needed. **Version trap:** before 16 there was no `refersTo`, so this comparison necessarily went through `get()` and paid the barrier on every probe — **Unverified:** the exact pre-16 body, which I could not check without an older `src.zip`; what is verified is that `refersTo` is `@since 16` (`java/lang/ref/Reference.java:372`) and so cannot have appeared here earlier. Notes and blog posts written before 2021 show the `get()`-only form, and so will interviewers who learned it then.

---

## The clearing sequence has an arbitrary gap

### Four stages, and only the last is yours — leaf 3.11.10 `[PROVE]` `[TRAP]`

Removal is a relay race with four legs, run by three parties, and only the last leg is yours.

| Stage | Who | When |
|---|---|---|
| 1. Key becomes weakly reachable | your code, dropping the last strong reference | deterministic |
| 2. GC clears the referent | the collector's reference-processing phase | **arbitrary** |
| 3. GC enqueues the entry on `queue` | the reference-handler thread | shortly after 2, still arbitrary |
| 4. Entry unlinked, `size--`, value nulled | **your** next `size()`/`get()`/`put()`/… | only when you touch the map |

Between stage 1 and stage 4 the entry is still in the table, still counted in `size`, and — the part people miss — **still holding its value strongly alive**.

**[PROVE]** Rather than assert that, observe it. One mapping, both strong references dropped, key and value each watched through an independent `WeakReference` that is *not* registered on the map's queue.

```java
public class ClearingSequence {

    record Key(int id) { }
    record Value(int id) { }

    public static void main(String[] args) throws InterruptedException {
        WeakHashMap<Key, Value> map = new WeakHashMap<>();
        Key key = new Key(1);
        Value value = new Value(1);
        map.put(key, value);

        // Watchers NOT registered on the map's ReferenceQueue.
        WeakReference<Key> keyWatch = new WeakReference<>(key);
        WeakReference<Value> valueWatch = new WeakReference<>(value);
        key = null;    // reachable only via Entry's weak referent slot
        value = null;  // reachable only via Entry.value -- a STRONG field

        for (int i = 1; i <= 5; i++) {
            System.gc(); Thread.sleep(50);
            System.out.println("gc " + i + " (map untouched)  keyAlive="
                    + (keyWatch.get() != null) + "  valueAlive=" + (valueWatch.get() != null));
        }
        System.out.println("--- first map operation: size() = " + map.size() + " ---");
        for (int i = 1; i <= 5; i++) {
            System.gc(); Thread.sleep(50);
            System.out.println("gc " + i + " (after expunge)   valueAlive="
                    + (valueWatch.get() != null));
        }
    }
}
```

Real output, one run, HotSpot 21.0.7+8-LTS-245 on macOS arm64, default G1:

```
gc 1 (map untouched)  keyAlive=false  valueAlive=true
gc 2 (map untouched)  keyAlive=false  valueAlive=true
gc 3 (map untouched)  keyAlive=false  valueAlive=true
gc 4 (map untouched)  keyAlive=false  valueAlive=true
gc 5 (map untouched)  keyAlive=false  valueAlive=true
--- first map operation: size() = 0 ---
gc 1 (after expunge)   valueAlive=false
gc 2 (after expunge)   valueAlive=false
gc 3 (after expunge)   valueAlive=false
gc 4 (after expunge)   valueAlive=false
gc 5 (after expunge)   valueAlive=false
```

Work the argument through. After `gc 1` the key is provably gone — stage 2 completed. The value is provably still alive across five further collections, with no reachability path to it except `Entry.value`. Therefore the `Entry` is still reachable, therefore still linked in the table, therefore stage 4 has not run. The one thing that changes that is the `map.size()` call, and the very next collection reclaims the value. The stage-2-to-stage-4 gap is bounded by nothing but "when does this program next touch this map". **Honesty about the method:** `System.gc()` is a hint, `Thread.sleep(50)` is not a barrier, and this is one run on one JVM with one collector — not a guarantee. What the transcript legitimately establishes is not a timing law but a **contrast under identical pressure**: the key cleared and the value did not, in the same collections, on the same heap. Timing cannot explain a difference in *which* object survived. Under ZGC or `-XX:+UseSerialGC` the row where `keyAlive` flips may move; the fact that `valueAlive` stays `true` until `size()` is called will not.

**Pitfall:** *"When the key is collected, the mapping is gone."* Gone *logically* — you cannot call `get(key)` without the key. But the `Entry`, its cached `hash`, its `next` link and above all its **value** are still on the heap and still counted in `size`, for an unbounded interval. **Symptom:** a `WeakHashMap<Key, byte[1MB]>` cache, written once in a burst and never read again, holds gigabytes indefinitely, and a heap dump shows `WeakHashMap$Entry` retaining arrays whose referents are already `null`. **Fix:** touch the map periodically — `size()`, `isEmpty()`, anything — or use `Cleaner` / an explicit eviction policy if you need bounded reclamation latency.

> **Definition.** Clearing a `WeakHashMap` mapping is a four-stage relay — drop the last strong key reference, GC clears the referent, GC enqueues the entry, and the *next map operation* unlinks it — so an entry and its strongly-held value survive the key's death for an interval bounded only by when the map is next used.

---

## The value that holds its own key

### The canonical `WeakHashMap` leak — leaf 3.11.11 `[PROVE]` `[TRAP]`

**Mental model.** The entry is a tag the GC may cut off, but the value hangs off that tag by a steel cable. Tie the cable's other end back to the key and the tag can never be cut: the key is strongly reachable *through the map itself*, and you have built a strong-keyed `HashMap` that merely looks weak. **When this bites and when it does not:** it bites whenever the value type has any field, however indirect, that reaches the key; it does not bite when values are primitives, boxes, `String`s or immutable tokens, which is why the trap is invisible in toy examples.

The path, spelled out — and nothing on it is weak:

```
map  --strong-->  table[]  --strong-->  Entry  --strong (Entry.value)-->  Session
Session  --strong (Session.owner)-->  Key
```

The `Entry`'s referent slot is weak, but the collector does not care: it clears a referent only when the object is unreachable **by any path**, and this path bypasses the referent slot entirely.

**Why people fall into it.** The back-reference is almost always natural. `Map<Connection, SessionState>` where the state records its connection. `Map<Node, Metadata>` where metadata has a parent pointer. `Map<ClassLoader, Config>` where `Config` caches a `Class` — and a `Class` holds its `ClassLoader`. That last is the classic Tomcat redeploy leak: the whole webapp classloader pinned by a `WeakHashMap` introduced *specifically* to avoid pinning it. **[PROVE]** — two maps, identical shape, one strong back-reference and one weakly wrapped, same heap, same collections:

```java
public class ValueHoldsKey {

    record Key(String name) { }
    record Session(Key owner) { }                       // strong back-reference: the leak
    record SafeSession(WeakReference<Key> owner) { }     // weak back-reference: the fix

    public static void main(String[] args) throws InterruptedException {
        WeakHashMap<Key, Session> leaky = new WeakHashMap<>();
        WeakHashMap<Key, SafeSession> fixed = new WeakHashMap<>();
        Key a = new Key("a");
        Key b = new Key("b");
        leaky.put(a, new Session(a));
        fixed.put(b, new SafeSession(new WeakReference<>(b)));
        a = null;
        b = null;

        System.out.println("start  leaky=" + leaky.size() + "  fixed=" + fixed.size());
        for (int i = 1; i <= 5; i++) {
            System.gc(); Thread.sleep(50);
            System.out.println("gc " + i + "   leaky=" + leaky.size()
                    + "  fixed=" + fixed.size());
        }
    }
}
```

Real output, same JVM and platform:

```
start  leaky=1  fixed=1
gc 1   leaky=1  fixed=0
gc 2   leaky=1  fixed=0
gc 3   leaky=1  fixed=0
gc 4   leaky=1  fixed=0
gc 5   leaky=1  fixed=0
```

Work it through. Both `size()` calls run expunge, so both maps get an equal chance to reclaim on every row. `fixed` reclaims on the first collection; `leaky` never does, through five. The arms differ in exactly one field's declared type — `Key owner` versus `WeakReference<Key> owner` — and they experience identical GC pressure in the same JVM in the same run. Timing is nondeterministic, but timing cannot produce a *systematic* difference between two arms of one run; it would have to clear one and not the other, every time, for one specific reason. The reason is the reachability path.

**Fixes, ranked.** Wrapping is the mechanical fix, not always the best one:

| Fix | Cost | When it wins |
|---|---|---|
| Don't store the back-reference at all | free | Almost always right. Usually the value only needed the key because the API was shaped badly. |
| `WeakReference<K>` around the back-reference | one object per value; `owner.get()` can return `null` | The back-reference is genuinely needed and callers handle `null`. |
| Store a derived immutable token (an id, a `String`, a record of the fields you needed) | none, if the token is small | The value needed *data from* the key, not the key's identity. |
| Give up: explicit LRU, or Caffeine with `weakKeys()` | a dependency | The retention policy is business logic, not a GC accident. |

A `SoftReference` back-reference is **not** a fix: soft references clear only under memory pressure, so you convert a permanent leak into one that resolves just before `OutOfMemoryError`. `WeakHashMap` also gives you no hook to wrap values automatically — there is no `withWeakValues()`, which is exactly why Guava's `CacheBuilder.weakKeys().weakValues()` exists. **Insight:** this leak is the same bug as the `e.value = null` line at `:346`, seen from the other side. That line exists because the JDK authors knew a retained value can pin other keys. Your leak is the case where the value pins its *own* key — which no amount of nulling-on-expunge can help, because expunge never runs.

> **Definition.** The value-holds-key leak is a `WeakHashMap` whose value holds a strong reference reaching its own key, making the key strongly reachable via `map → table → Entry.value → key` and so making the weak referent slot unclearable — turning the map into a permanently-retaining `HashMap` with extra overhead.

---

## Keys that can never be collected

### Three families, one table — leaf 3.11.12 `[TRAP]`

A `WeakHashMap` evicts only when the key becomes weakly reachable. If something else in the JVM holds the key strongly and permanently, the mapping is immortal and the map is a slow, wordy `HashMap`. Seven key kinds, three of which never clear:

| Key kind | Held alive by | Cleared? | Notes |
|---|---|---|---|
| `String` **literal** / `intern()`ed | the string table, rooted from the loading class's resolved constant pool | **Never** (literal) | Interned strings became collectible in principle once the string table left PermGen in 7/8, but a literal lives as long as its class. |
| `new String("x")` | nothing | Yes | Same characters, different object. |
| boxed `Integer` in `[-128, 127]` | `Integer.IntegerCache.cache`, a `static final Integer[]` | **Never** | Autoboxing, `Integer.valueOf` and every `Map<Integer,V>` hit this. |
| boxed `Integer` outside the cache | nothing | Yes | `Integer.valueOf(10_000)` allocates. |
| `Byte`/`Short`/`Long` in `[-128,127]`, `Character` in `[0,127]`, `Boolean.TRUE`/`FALSE` | their own caches, mandated by JLS §5.1.7 | **Never** | Same trap, wider than most people remember. |
| `Class<?>` | its defining `ClassLoader`, rooted while any of its classes is live | **Never**, in practice | `Class` → `ClassLoader` → all its classes. Collectible only when the whole loader is unreachable. |
| `enum` constant | the enum class's `static final` fields | **Never** | Use `EnumMap` — see [02-internals-enum-map-set.md](02-internals-enum-map-set.md). |

**[NUM] The `Integer` cache range, verified rather than recalled.** `java.base/java/lang/Integer.java:1009-1031`:

```java
    private static final class IntegerCache {
        static final int low = -128;
        static final int high;
        @Stable
        static final Integer[] cache;
        static Integer[] archivedCache;

        static {
            // high value may be configured by property
            int h = 127;
            String integerCacheHighPropValue =
                VM.getSavedProperty("java.lang.Integer.IntegerCache.high");
            if (integerCacheHighPropValue != null) {
                try {
                    h = Math.max(parseInt(integerCacheHighPropValue), 127);
                    // Maximum array size is Integer.MAX_VALUE
                    h = Math.min(h, Integer.MAX_VALUE - (-low) -1);
                } catch( NumberFormatException nfe) {
                    // If the property cannot be parsed into an int, ignore it.
                }
            }
            high = h;
```

`low` is a hard-coded `-128` and is **not** configurable. `high` defaults to `127` and *is*, via `-Djava.lang.Integer.IntegerCache.high=N`, clamped below at 127 by the `Math.max` — you can only ever *widen* the cache, never narrow it — and above at `Integer.MAX_VALUE - 128 - 1` by the `Math.min`, because that is the largest array the `(high - low) + 1` sizing can express. The `catch` silently ignores a malformed property. Default size is `(127 - (-128)) + 1 = ` **256** permanently-live `Integer` objects, ≈ 256 × 16 = 4,096 bytes plus a 256-slot array. `@Stable` and `archivedCache` mean the array is CDS-archived, so it is alive before your `main` starts. Only `Integer` has the knob; the other box caches are fixed.

The consequence that catches people: **widening the property widens the trap.** With `-Djava.lang.Integer.IntegerCache.high=100000`, a `WeakHashMap<Integer, V>` keyed by IDs under 100,000 stops evicting entirely.

**[PROVE]** All three families against two controls:

```java
public class NeverClears {

    public static void main(String[] args) throws InterruptedException {
        var literal     = new WeakHashMap<String, String>();
        var fresh       = new WeakHashMap<String, String>();
        var cachedBox   = new WeakHashMap<Integer, String>();
        var uncachedBox = new WeakHashMap<Integer, String>();
        var classKey    = new WeakHashMap<Class<?>, String>();

        literal.put("literalKey", "v");                 // constant-pool interned
        fresh.put(new String("freshKey"), "v");         // ordinary heap String
        cachedBox.put(Integer.valueOf(42), "v");        // inside IntegerCache
        uncachedBox.put(Integer.valueOf(10_000), "v");  // outside IntegerCache
        classKey.put(String.class, "v");                // held by its ClassLoader

        System.out.println("valueOf(127) identical? " + (Integer.valueOf(127) == Integer.valueOf(127))
                + "   valueOf(128) identical? " + (Integer.valueOf(128) == Integer.valueOf(128)));
        for (int i = 1; i <= 5; i++) {
            System.gc(); Thread.sleep(50);
            System.out.println("gc " + i + "  literal=" + literal.size() + " fresh=" + fresh.size()
                    + " cachedBox=" + cachedBox.size() + " uncachedBox=" + uncachedBox.size()
                    + " classKey=" + classKey.size());
        }
    }
}
```

Real output, same JVM and platform:

```
valueOf(127) identical? true   valueOf(128) identical? false
gc 1  literal=1 fresh=0 cachedBox=1 uncachedBox=0 classKey=1
gc 2  literal=1 fresh=0 cachedBox=1 uncachedBox=0 classKey=1
gc 3  literal=1 fresh=0 cachedBox=1 uncachedBox=0 classKey=1
gc 4  literal=1 fresh=0 cachedBox=1 uncachedBox=0 classKey=1
gc 5  literal=1 fresh=0 cachedBox=1 uncachedBox=0 classKey=1
```

The controls make this an argument rather than an anecdote. `fresh` and `uncachedBox` reclaim on the first collection, so collection is demonstrably happening; `literal`, `cachedBox` and `classKey` do not, through five, in the same run. And the identity checks pin down *why* `cachedBox` differs from `uncachedBox`: 127 is the same object twice, 128 is not.

**Pitfall:** *"`WeakHashMap<String, V>` is a self-cleaning cache."* It is, until a key is a literal or `intern()`ed — which for a cache keyed by config names, header names, metric names or table names is **every key**. **Symptom:** the map grows monotonically in production and never in the load test, where keys came from parsed input rather than literals; a heap dump shows `WeakHashMap$Entry` referents that are all live `String`s. **Fix:** never key a `WeakHashMap` on a canonicalised type — `String` literals, small boxes, `Class`, `enum`. Key on identity-bearing domain objects you allocate, or drop `WeakHashMap` for a bounded cache with an explicit policy.

**Interview:** "Why would a `WeakHashMap<Integer, Session>` never shrink?" — Because `Integer.valueOf` returns cached instances for `[-128, 127]` (default, widenable via `-Djava.lang.Integer.IntegerCache.high`), held by a `static final Integer[]`, so those keys are permanently strongly reachable.

---

## `ThreadLocalMap` — the same shape, in `java.lang` — leaf 3.11.13 `[X-REF 05]`

`ThreadLocal`'s storage is a second, independent implementation of exactly this idea. `java.base/java/lang/ThreadLocal.java:371-389`:

```java
        /**
         * The entries in this hash map extend WeakReference, using
         * its main ref field as the key (which is always a
         * ThreadLocal object).  Note that null keys (i.e. entry.get()
         * == null) mean that the key is no longer referenced, so the
         * entry can be expunged from table.  Such entries are referred to
         * as "stale entries" in the code that follows.
         */
        static class Entry extends WeakReference<ThreadLocal<?>> {
            /** The value associated with this ThreadLocal. */
            Object value;

            Entry(ThreadLocal<?> k, Object v) {
                super(k);
                value = v;
            }
        }
```

Same trick — entry *is* the reference, key in the referent slot, `Object value` strong — with three differences that matter. The type parameter is `WeakReference<ThreadLocal<?>>`, not `Object`, because there are no null keys to mask. `super(k)` passes **no queue**: `ThreadLocalMap` has no `ReferenceQueue` at all, so nothing tells it when a key dies and it must instead *probe* for `e.get() == null` during its scans. And the table is open-addressed (`INITIAL_CAPACITY = 16` at `:394`, `nextIndex` wraparound) rather than chained, so cleanup is the far more elaborate `expungeStaleEntry(int)` at `:669`, which must rehash the run following the hole. It opens with `tab[staleSlot].value = null; tab[staleSlot] = null; size--;` — the same "help GC" move as `WeakHashMap:346`, for the same reason.

**The stale-value leak, self-contained.** The `ThreadLocal` object is the weak key; the value is strong. In a thread pool the `Thread` lives for the lifetime of the pool, and `Thread.threadLocals` is a strong field on it, so the chain `Thread → ThreadLocalMap → Entry → value` is entirely strong. Drop the last reference to the `ThreadLocal` itself — it was a local, or its holder class was unloaded — and the *key* clears, leaving an entry with a `null` key and a live value that **no code can ever address**, because addressing it requires the `ThreadLocal` you just lost. It is reclaimed only if some later `get`/`set`/`remove` on that same thread happens to scan across its slot, which on an idle pool thread may be never. If the value's class came from an application classloader, the whole loader is pinned — the standard "webapp failed to unload" report. That is why `ThreadLocal.remove()` exists (`:282-284`, delegating to `remove(Thread)` at `:291`), and why every framework wraps thread-local use in `try { … } finally { tl.remove(); }`. Setting the thread-local to `null` is not equivalent: it leaves the entry in place with a null value, whereas `remove()` calls `expungeStaleEntry` and clears the slot. The threading side — pool hygiene, `InheritableThreadLocal` propagation, virtual threads (where threads are cheap and short-lived, changing the calculus completely) and `ScopedValue` as the Java 21 alternative — belongs to **guide 05 on concurrency and threading**; read the `ThreadLocal` lifecycle discussion there.

**Pitfall:** *"`ThreadLocal` values are cleaned up when the thread finishes."* True for a thread you created and let die outright — `Thread.threadLocals` dies with the `Thread`. **False for every pooled thread**, which is where essentially all server-side `ThreadLocal` use lives. **Symptom:** memory grows with request count rather than with concurrency, and a heap dump shows `ThreadLocalMap$Entry` instances whose referent is `null` and whose value is large. **Fix:** `finally { threadLocal.remove(); }` at every scope boundary, without exception.

---

## `size()` is not an observer

### Leaf 3.11.14 `[TRAP]` `[PROVE]`

`:371-386`:

```java
    public int size() {
        if (size == 0)
            return 0;
        expungeStaleEntries();
        return size;
    }

    public boolean isEmpty() {
        return size() == 0;
    }
```

`size()` calls `expungeStaleEntries()`, which unlinks entries, writes `table[i]`, nulls values and decrements `size`. **`size()` structurally modifies the map.** So does `isEmpty()`, which *is* `size()`; so does `containsKey()`, via `getEntry()` → `getTable()`; so do `containsValue()`, `get()`, and constructing any iterator. In `WeakHashMap` there is no such thing as a read-only operation. **When to reach for `size()` anyway:** only for logging or metrics where an approximate, shrinking count is acceptable. Never as a loop bound, an assertion, or half of a check-then-act.

Note the `if (size == 0) return 0;` fast path: with the raw counter already zero, `size()` skips expunge entirely and does *not* drain the queue — and queued entries are strongly reachable from the queue. Three consequences, in increasing order of trouble:

1. **Two consecutive `size()` calls can disagree**, with no mutation from your code.
2. **`size()` is not O(1).** It is O(entries that died since the last touch), which after a large burst is O(n).
3. **You cannot make a consistent decision from two reads.** In `if (!map.isEmpty()) { var v = map.get(k); }`, `isEmpty()` returning false does not mean `get` will find anything — and not for the usual race reasons: `isEmpty()` may itself have been the call that removed the entry.

**[PROVE].** Two consecutive `size()` calls must be caught disagreeing, which needs a collection to land in the microseconds between them — so this demo uses real allocation pressure from a churn thread rather than `System.gc()` hints. (A companion run that simply put 2,000 mappings with immediately-unreachable keys and then read `size()` reported `first size() = 2000` and `0` on the very next round, with `remove()` never called once: proof that the relay's stages 1–3 leave entries fully counted until something touches the map.)

```java
public class SizeDisagrees {

    static volatile boolean run = true;
    static volatile Object sink;

    public static void main(String[] args) {
        WeakHashMap<Object, byte[]> map = new WeakHashMap<>();
        Thread churn = new Thread(() -> {
            while (run) { sink = new byte[8 * 1024]; }   // pressure -> GC cycles
        });
        churn.setDaemon(true);
        churn.start();

        int found = 0;
        for (int round = 0; round < 200 && found < 3; round++) {
            for (int i = 0; i < 5_000; i++) { map.put(new Object(), new byte[32]); }
            int a = map.size();
            int b = map.size();
            if (a != b) {
                found++;
                System.out.println("round " + round + ": size()=" + a
                        + " then immediately size()=" + b
                        + "   -> observer shrank the map by " + (a - b));
            }
        }
        run = false;
        if (found == 0) {
            System.out.println("no disagreement observed in this run "
                    + "(GC happened not to land between the two calls)");
        }
    }
}
```

Real output of six consecutive runs, `-Xmx256m`, same JVM and platform:

```
no disagreement observed in this run (GC happened not to land between the two calls)
round 11: size()=21297 then immediately size()=21282   -> observer shrank the map by 15
no disagreement observed in this run (GC happened not to land between the two calls)
round 63: size()=31678 then immediately size()=31628   -> observer shrank the map by 50
round 11: size()=36589 then immediately size()=36585   -> observer shrank the map by 4
round 11: size()=23062 then immediately size()=23056   -> observer shrank the map by 6
```

Four of six runs caught it; two did not. That spread is the honest result and it is *also* the lesson — the demo prints an explicit "no disagreement observed" line and exits cleanly when the collector never lands in the window, because a GC-timing experiment that always succeeds is a rigged one. When it does fire it fires unambiguously: two `size()` calls on adjacent source lines, 4 to 50 apart, in a program that never called `remove()`.

**Pitfall:** *"`size()` is a cheap, side-effect-free read, so I can use it in an assertion, a log line, or a loop bound."* **Symptom (mild):** log lines reporting a shrinking map nobody modified, and support tickets about phantom removals. **Symptom (worst):** `for (int i = 0; i < map.size(); i++)` over an index-keyed `WeakHashMap`, or `assert map.size() == expected` firing nondeterministically in CI and never locally. **Fix:** treat every `WeakHashMap` read as a mutation *and* a snapshot; if you need a stable count, copy into a strong structure first — `int n = new HashMap<>(weakMap).size();` — which also pins the keys for the duration, which is the point.

**Interview:** "Can `map.size()` return different values twice in a row in a single-threaded program?" — Yes, on a `WeakHashMap`: `size()` drains the reference queue and decrements the counter, so a collection between the two calls makes the second smaller with no mutation in your code.

> **Definition.** On a `WeakHashMap`, `size()` — and with it `isEmpty()`, `containsKey()`, `get()` and iterator construction — is an observer with side effects: it invokes `expungeStaleEntries()`, structurally modifying the table and decrementing the count, so consecutive calls may disagree and the result is only ever a snapshot.

---

## Pitfalls

### Believing the mapping is gone as soon as the key is collected

**Wrong**

```java
cache.put(new Key(1), new byte[1024 * 1024]);   // key unreachable immediately
System.gc();
// "the key is dead, so the megabyte is freed" -- no. The Entry is still linked,
// Entry.value is a STRONG field, and nothing is reclaimed until a map method runs.
```

Proven above: `valueAlive=true` across five collections while `keyAlive=false`.

**Right**

```java
cache.put(new Key(1), new byte[1024 * 1024]);
System.gc();
cache.size();   // stage 4 -- unlink, size--, e.value = null
// now the byte[] is genuinely unreachable and the next collection reclaims it.
```

**Why people believe it:** the javadoc says entries are removed "when its key is no longer in ordinary use", which reads like a promise about timing. It is a promise about *eventuality*. The class has no thread and no timer; reclamation is piggybacked entirely on the caller.

### Storing a value that refers back to its own key

**Wrong**

```java
record Session(Connection owner, long startedAt) { }   // strong back-reference
sessions.put(c, new Session(c, System.nanoTime()));
c = null;
// sessions.size() stays 1 forever -- proven above, five collections, no change.
```

**Right**

```java
record Session(WeakReference<Connection> owner, long startedAt) { }
sessions.put(c, new Session(new WeakReference<>(c), System.nanoTime()));
c = null;
// evicts on the first collection. Better still: drop the back-reference entirely
// and store only the data the value actually needed -- an id, a host string.
```

**Why people believe it:** "the key is a weak reference, so the map cannot retain it" sounds like a property of the map. It is a property of the *referent slot only*. The collector clears a referent when nothing strongly reaches the object, and a strong path through `Entry.value` is still a strong path — starting at the same map.

### Keying on `String` literals, small boxes, `Class` or `enum`

**Wrong**

```java
byName.put("http.requests", new Metrics());   // constant-pool literal
byUserId.put(42, new Session());              // Integer.valueOf(42) -- cached
// literal=1 cachedBox=1 through five collections, proven above.
```

**Right**

```java
record MetricKey(String name) { }                        // an object you allocate
WeakHashMap<MetricKey, Metrics> byMetric = new WeakHashMap<>();

Map<String, Metrics> bounded = Caffeine.newBuilder()     // or an explicit policy
        .maximumSize(10_000).<String, Metrics>build().asMap();
```

**Why people believe it:** `new String("http.requests")` *does* get collected, so an experiment with dynamically-built keys appears to confirm the design — and then production keys turn out to be literals. Verified: the `Integer` cache is `[-128, 127]` by default (`Integer.java:1010`, `:1019`), widenable upward only.

### Treating `size()` / `isEmpty()` / `containsKey()` as pure reads

**Wrong**

```java
assert map.size() == expected;                    // fires nondeterministically
log.info("cache holds {} entries", map.size());   // shrinks between log lines
if (!map.isEmpty()) {
    var v = map.get(theKey);   // may be null; isEmpty() itself may have expunged it
}
```

Proven above: `size()=21297 then immediately size()=21282`.

**Right**

```java
Map<Object, byte[]> snapshot = new HashMap<>(map);      // strong copy, stable count
log.info("cache holds {} entries", snapshot.size());

byte[] v = map.get(theKey);                            // one call, not check-then-act
if (v != null) { use(v); }
```

**Why people believe it:** every other `java.util` map has a side-effect-free `size()`, and the signature is identical. The javadoc does warn — "This result is a snapshot, and may not reflect unprocessed entries" at `:367-369` — but says nothing about *mutation*, which is the sharper half.

---

## Cheat sheet

| Thing | Fact |
|---|---|
| Entry shape | `private static class Entry<K,V> extends WeakReference<Object> implements Map.Entry<K,V>` (`:712`); declares only `V value` (strong), `final int hash`, `Entry<K,V> next` |
| Key lives in | inherited `Reference.referent`, set by `super(key, queue)` (`:723`). Referent type arg is `Object`, not `K`, because of `NULL_KEY` and the shared `ReferenceQueue<Object>` |
| Why cache `hash` | key is already `null` when expunge runs, so `hashCode()` is uncallable; the cached hash is the only route to the bucket |
| `HashMap.Node` contrast | `final int hash; final K key; V value; Node next;` (`HashMap.java:281-285`) — strong key field, nothing can clear it |
| Queue | `private final ReferenceQueue<Object> queue` (`:179`), one per map, no background thread |
| Expunge body | `:328-355` — `queue.poll()` loop, `synchronized (queue)` per entry, `indexFor(e.hash, table.length)`, identity unlink, `e.value = null; // Help GC` (`:346`), `size--`. Never nulls `e.next` (`:344-345`), never bumps `modCount` |
| Direct expunge call sites | `getTable():361`, `size():374` (behind `size==0`), `resize():516`. `clear()` drains by hand twice instead (`:659-673`); iteration expunges once in the ctor via `isEmpty()` (`:788`) and holds strong `nextKey`/`currentKey` (`:779`, `:785`) |
| Constants | `DEFAULT_INITIAL_CAPACITY=16` (`:142`), `MAXIMUM_CAPACITY=1<<30` (`:149`), `DEFAULT_LOAD_FACTOR=0.75f` (`:154`) |
| Hash function | pre-Java-8 four-shift form (`:308-316`); **no treeification** — worst-case bucket O(n) |
| Null key | masked to `static final NULL_KEY` (`:271`) → that mapping is immortal |
| `matchesKey` | `refersTo(key)` first (no barrier, no resurrection), then `get()` + `equals` (`:291-299`); `refersTo` is Java 16+ |
| Clearing relay | drop key → GC clears referent → GC enqueues → **next map op** unlinks. Gap 2→4 unbounded. |
| Value-holds-key leak | `map → table → Entry.value → key` all strong; fix by removing the back-ref, else wrap in `WeakReference` |
| Never-clearing keys | `String` literals/`intern()`, `Integer` `[-128,127]` (`Integer.java:1010`/`:1019`, widen via `-Djava.lang.Integer.IntegerCache.high`), other box caches, `Class`, `enum` |
| `size()` | O(newly dead), mutates the map, can shrink between adjacent calls; `isEmpty`/`containsKey`/`get`/iteration likewise |
| `ThreadLocalMap.Entry` | `extends WeakReference<ThreadLocal<?>>`, `Object value` strong, **no queue**, open-addressed (`ThreadLocal.java:381-389`). Pooled `Thread` → map → `Entry.value` all strong, key cleared → unaddressable value. Always `finally { tl.remove(); }` |

---

## Self-test

**Q1.** `WeakHashMap.Entry` has no field holding the key. Where is the key, and why can it not simply be a declared field?

<details><summary>Answer</summary>

The key is in `Reference.referent`, inherited from `WeakReference` and populated by `super(key, queue)` at `:723`. It cannot be a declared field because `referent` is not an ordinary field: HotSpot knows its offset, special-cases loads of it with a GC load barrier, and the collector's reference-processing phase clears exactly that slot on discovered `Reference` objects. A field you declare yourself receives none of that, so the GC would have no way to null it. Putting the key there also means `ReferenceQueue.poll()` returns the `Entry` itself, so cleanup needs no reference-to-entry lookup table — the second, equally deliberate half of the design.

</details>

**Q2.** `Entry` caches `final int hash`, exactly like `HashMap.Node`. Is the reason the same?

<details><summary>Answer</summary>

No, and this is the good question in the set. For `HashMap.Node` the cache is a pure optimisation — `final K key` is right there, so `key.hashCode()` could always be recomputed. For `WeakHashMap.Entry` it is a correctness requirement. `expungeStaleEntries()` needs the dead entry's bucket, computed at `:333` as `indexFor(e.hash, table.length)`. By then `e.get()` returns `null`: the key object is gone and `hashCode()` cannot be called on it at all. If the hash had not been snapshotted at insertion, a dead entry could never be located and the map could never reclaim anything. Same field, different necessity.

</details>

**Q3.** Why is the referent type parameter `Object` rather than `K`?

<details><summary>Answer</summary>

Two independent reasons. Null keys are stored as `private static final Object NULL_KEY = new Object()` (`:271`), a bare `Object` that could not be the referent of a `WeakReference<K>`. And the map has one shared `ReferenceQueue<Object>` (`:179`) that must accept every entry; `ReferenceQueue` is invariant in its type parameter, so it cannot be passed to a `WeakReference<K>` constructor. The cost is paid in `getKey()` at `:729-732`, which needs `@SuppressWarnings("unchecked")` to cast back.

</details>

**Q4.** `expungeStaleEntries()` unlinks the entry, so why does it also need `e.value = null`?

<details><summary>Answer</summary>

Because unlinking does not make the entry unreachable. The comment immediately above — `// Must not null out e.next; stale entries may be in use by a HashIterator` (`:344-345`) — means the removed entry keeps a live forward pointer into the chain, and a running iterator may still hold the entry itself. So the `Entry` object can outlive its removal by an arbitrary interval, and while it lives a strong `value` field keeps the value alive with it. More sharply: if that value strongly reaches some *other* live key in the same map, retaining it would pin an unrelated mapping. Nulling converts "entry unlinked" into "value actually reclaimable". The `// Help GC` comment undersells it.

</details>

**Q5.** You put one mapping into a `WeakHashMap`, drop the key, and force five collections without touching the map. What is the state of the value?

<details><summary>Answer</summary>

Still strongly alive. The relay has four stages — you drop the key, the GC clears the referent, the GC enqueues the entry, and then the **next map operation** drains the queue and unlinks. Stages 2 and 3 happened; stage 4 has not, because stage 4 is your call, not the GC's. The `Entry` is still in the table, still counted in `size`, and `Entry.value` is a plain strong field. The transcript above shows `keyAlive=false valueAlive=true` across five collections, then `valueAlive=false` on the first collection after a single `map.size()`. There is no upper bound on the stage-2-to-stage-4 gap.

</details>

**Q6.** A `WeakHashMap<Connection, Session>` never shrinks, and `Session` is a record holding the `Connection` it belongs to. Give the retention path and two fixes.

<details><summary>Answer</summary>

The path is `map → table[] → Entry → Entry.value (Session) → Session.owner (Connection)`, and every link is strong. The `Entry`'s referent slot is weak, but the collector clears a referent only when the object is unreachable by *any* path, and this one bypasses the referent slot entirely — so the key is strongly reachable from the very map meant to release it.

Fix 1, best: delete the back-reference; if `Session` needed data from the connection, store that data (an id, a host string). Fix 2: wrap it — `record Session(WeakReference<Connection> owner, long startedAt)` — and handle `owner.get() == null`. A `SoftReference` is *not* a fix: it clears only under memory pressure, converting a permanent leak into one that resolves just before `OutOfMemoryError`.

</details>

**Q7.** Which of these will a `WeakHashMap` never evict, and why: `"config.timeout"`, `new String("config.timeout")`, `Integer.valueOf(42)`, `Integer.valueOf(42_000)`, `String.class`?

<details><summary>Answer</summary>

Never evicted: `"config.timeout"` (a literal, referenced from the resolved constant pool of the class that loaded it, so it lives as long as that class); `Integer.valueOf(42)` (inside `IntegerCache`'s `static final Integer[]`, range `[-128, 127]` by default per `Integer.java:1010` and `:1019`, widenable upward only via `-Djava.lang.Integer.IntegerCache.high`); `String.class` (held by its defining `ClassLoader`, rooted while any of its classes is live — for `String` that is the bootstrap loader, so effectively forever).

Evicted normally: `new String("config.timeout")` (a distinct heap object, not interned) and `Integer.valueOf(42_000)` (outside the cache, so freshly allocated). The verified transcript shows exactly this split — `fresh=0 uncachedBox=0` versus `literal=1 cachedBox=1 classKey=1` — through five collections in one run.

</details>

**Q8.** Can `map.size()` return two different values on adjacent lines of a single-threaded program?

<details><summary>Answer</summary>

Yes, on a `WeakHashMap`. `size()` at `:371-376` calls `expungeStaleEntries()`, which decrements the `size` field for every entry the GC has enqueued. If a collection lands between the two calls — and the *collector* is not single-threaded even when your program is — the second drains newly-enqueued entries and returns a smaller number, with no mutation from your code. The transcript shows `size()=21297 then immediately size()=21282` (in four of six runs; timing-dependent, which is itself the point). The general lesson is stronger: `isEmpty()`, `containsKey()`, `get()`, `containsValue()` and iterator construction all reach expunge, so the class has no side-effect-free read at all. One exception: `size()` short-circuits at `if (size == 0) return 0;` (`:372`) and does not drain in that case.

</details>

**Q9.** `ThreadLocalMap.Entry` has the same shape as `WeakHashMap.Entry`. Name three differences and the leak that follows.

<details><summary>Answer</summary>

(1) The type parameter is `WeakReference<ThreadLocal<?>>` rather than `Object`, because there are no null keys to mask. (2) The constructor is `super(k)` with **no `ReferenceQueue`** (`ThreadLocal.java:386`) — `ThreadLocalMap` has no queue at all and instead probes for `e.get() == null` during its linear scans. (3) The table is open-addressed with wraparound (`INITIAL_CAPACITY = 16`, `nextIndex`), not chained, so cleanup is the rehash-the-following-run `expungeStaleEntry(int)` at `:669` rather than a simple unlink.

The leak: the value is a strong `Object value`, and `Thread → ThreadLocalMap → Entry → value` is entirely strong. In a pool the `Thread` outlives every request. If the `ThreadLocal` key becomes unreachable, the key clears and you are left with a live value no code can address, because addressing it requires the `ThreadLocal` you lost. It is reclaimed only if a later `get`/`set`/`remove` on that same thread happens to scan its slot — on an idle pool thread, possibly never. Hence `finally { tl.remove(); }`. Pool hygiene, `InheritableThreadLocal`, virtual threads and `ScopedValue` are guide 05's territory.

</details>

---

## Open questions

- The exact body of `matchesKey` before Java 16 (i.e. before `Reference.refersTo` existed). The `@since 16` tag on `refersTo` proves the current form is new, but the older form is reconstructed rather than read. Settled by extracting `src.zip` from a JDK 11 or 15 install.

**Leaves covered:** 3.11.8–3.11.14 (7 leaves)
**Leaves deferred:** none
**Diagrams included:** D-118
**Target version:** Java 21 LTS
**Lines:** 799
