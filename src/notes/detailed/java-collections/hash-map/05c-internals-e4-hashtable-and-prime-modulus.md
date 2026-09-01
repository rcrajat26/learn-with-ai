# 02 Java Collections — `HashMap` — INTERNALS (§3.6 `HashMap` source walk — the `Hashtable` contrast, and power-of-two versus prime modulus)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [hash-map/05b-internals-e2-views-hooks-and-hashtable.md](05b-internals-e2-views-hooks-and-hashtable.md) · Next: [hash-map/06-build-my-hash-map.md](06-build-my-hash-map.md)

---

## 3.6.46 / 3.6.47 — the `Hashtable` contrast, and why power-of-two beat prime modulus

### Mental model

Two hash tables ship in the same `java.util`, written a decade and a design philosophy apart. `Hashtable` (1996) follows the textbook: prime-ish capacity, modulo bucketing, raw `hashCode()`, a lock on every method. `HashMap` (1998, rebuilt in 2008 and again in 2011) inverts every one of those choices. Reading them side by side is the clearest available explanation of *why* `HashMap` looks the way it does — every line of `hash()`, every `& (n - 1)`, every bit of the lo/hi resize split is an answer to something `Hashtable` did.

And the received wisdom about what `Hashtable` actually does turns out to be wrong in an interesting place, so start there.

### The finding — the growth sequence is odd, not prime

Everyone repeats that `Hashtable` uses prime capacities because a prime modulus distributes well. Check it. The default capacity is 11 and the growth rule is `(oldCapacity << 1) + 1`:

```java
import java.math.BigInteger;

public class HtCaps {
    static String factor(int n) {
        StringBuilder sb = new StringBuilder();
        int rem = n;
        for (int d = 2; (long) d * d <= rem; d++) {
            while (rem % d == 0) { sb.append(d).append(" x "); rem /= d; }
        }
        sb.append(rem);
        return sb.toString();
    }

    public static void main(String[] args) {
        int cap = 11;
        System.out.printf("%-4s %-12s %-7s %s%n", "step", "capacity", "prime?", "factorisation");
        for (int i = 0; i < 15; i++) {
            boolean prime = BigInteger.valueOf(cap).isProbablePrime(50);
            System.out.printf("%-4d %-12d %-7s %s%n", i, cap, prime, prime ? "(prime)" : factor(cap));
            cap = (cap << 1) + 1;
        }
    }
}
```

Real output, JDK 21.0.7+8-LTS-245, Apple M4 Pro (arm64):

```
step capacity     prime?  factorisation
0    11           true    (prime)
1    23           true    (prime)
2    47           true    (prime)
3    95           false   5 x 19
4    191          true    (prime)
5    383          true    (prime)
6    767          false   13 x 59
7    1535         false   5 x 307
8    3071         false   37 x 83
9    6143         true    (prime)
10   12287        false   11 x 1117
11   24575        false   5 x 5 x 983
12   49151        false   23 x 2137
13   98303        false   197 x 499
14   196607       false   421 x 467
```

Six of the first fifteen are prime, and **6,143 is the last of them** — nothing in the sequence is prime after it. `(c << 1) + 1` guarantees only **oddness** — it never yields an even divisor, which is enough to dodge the crudest power-of-two aliasing, but it is not the prime-modulus property the textbooks recommend. Every `Hashtable` past about twelve thousand slots is running a composite modulus with small factors: 12,287 = 11 × 1117 means every hash congruent to the same value mod 11 aliases in a structured way. The syllabus word "prime-ish" is doing real work, and the popular claim is false from the fourth capacity onward.

That reframes the whole comparison. `Hashtable` is not paying for a division to buy a prime's mixing properties. It is paying for a division and, at realistic sizes, not getting the prime.

### Why the two designs exist

`Hashtable` predates the Collections Framework. It was written for JDK 1.0, retrofitted to implement `Map` in Java 1.2, and its API shape — `Enumeration`, `synchronized` everywhere, `contains()` meaning *contains value* — is 1996 preserved in amber. `HashMap` was the 1.2 replacement, freed from the lock and free to choose its own capacity discipline.

This file covers the **hashing mechanics** only. The legacy-API story — `Vector`, `Stack`, `Enumeration`, why these classes are retained but not recommended — is §2.15 in [`../framework/07-legacy-a-vector-stack-hashtable.md`](../framework/07-legacy-a-vector-stack-hashtable.md).

### When to reach for it, and when not

Never, in new code. There is no workload where `Hashtable` wins. Need thread safety with real throughput and atomic compound operations? `ConcurrentHashMap`. Need a synchronised wrapper to satisfy a legacy interface? `Collections.synchronizedMap(new HashMap<>())`, which at least lets you pick the lock object. Need a plain map? `HashMap`. `Hashtable` survives because `System.getProperties()` returns one and removing it would break the world.

### How it works — the contrast

| Aspect | `Hashtable` (JDK 21) | `HashMap` (JDK 21) |
|---|---|---|
| Default capacity | 11 (`public Hashtable() { this(11, 0.75f); }`, line 216) | 16 (`DEFAULT_INITIAL_CAPACITY = 1 << 4`, line 238) |
| Growth rule | `int newCapacity = (oldCapacity << 1) + 1;` (line 412) | `newCap = oldCap << 1` (line 693) |
| Index computation | `(hash & 0x7FFFFFFF) % tab.length` (lines 354, 382, 445, 482, 509) | `(n - 1) & hash` |
| Hash spreading | none — raw `key.hashCode()` | `h ^ (h >>> 16)` |
| Null key | rejected (`NullPointerException` from `key.hashCode()`) | one permitted, hashed to 0, always bin 0 |
| Null value | rejected explicitly at the top of `put` | permitted |
| Long bin | chains forever, O(n) | treeifies at 8 nodes with capacity ≥ 64, O(log n) |
| Thread safety | `synchronized` on every public method | none |
| Iteration | `Enumeration` (`keys()`, `elements()`) **and** `Iterator` | `Iterator` only |
| Maximum capacity | `MAX_ARRAY_SIZE = Integer.MAX_VALUE - 8` (line 397) | `MAXIMUM_CAPACITY = 1 << 30` (line 245) |

Verified behaviourally on JDK 21.0.7+8-LTS-245, Apple M4 Pro (arm64) — capacity read reflectively with `--add-opens java.base/java.util=ALL-UNNAMED`:

```
new Hashtable<>() capacity      = 11
after 9 puts (threshold 8)      = 23
Hashtable.put(null, v)          -> NullPointerException
Hashtable.put(k, null)          -> NullPointerException
HashMap.put(null, null)         -> ok, {null=null}
Hashtable.keys() is an          Enumeration
```

Threshold arithmetic, for the record: `threshold = (int) Math.min(11 × 0.75f, MAX_ARRAY_SIZE + 1)` = **8**, so the ninth put triggers `rehash()` and the table goes 11 → (11 << 1) + 1 = **23**. Both numbers confirmed above.

The index expression, in context:

```java
    public synchronized V put(K key, V value) {
        // Make sure the value is not null
        if (value == null) {
            throw new NullPointerException();
        }

        // Makes sure the key is not already in the hashtable.
        Entry<?,?> tab[] = table;
        int hash = key.hashCode();
        int index = (hash & 0x7FFFFFFF) % tab.length;
        @SuppressWarnings("unchecked")
        Entry<K,V> entry = (Entry<K,V>)tab[index];
        for(; entry != null ; entry = entry.next) {
            if ((entry.hash == hash) && entry.key.equals(key)) {
                V old = entry.value;
                entry.value = value;
                return old;
            }
        }

        addEntry(hash, key, value, index);
        return null;
    }
```
— `java.base/java/util/Hashtable.java`, JDK 21, line 473. (leaf 3.6.46)

`(hash & 0x7FFFFFFF) % tab.length` is **two operations doing one job**, and both halves are load-bearing.

The `& 0x7FFFFFFF` is not part of the bucketing. `0x7FFFFFFF` is `Integer.MAX_VALUE` — all 31 low bits set, sign bit clear — so the `AND` forces the value non-negative. It has to be there because Java's `%` takes the sign of its **left** operand: `-7 % 11` evaluates to `-7`, not to `4`, and `tab[-7]` throws `ArrayIndexOutOfBoundsException`. Roughly half of all `hashCode()` values are negative, so without the mask `Hashtable` would fail on the first negative hash it saw.

The `%` then does the actual bucketing. `HashMap` needs neither step: `(n - 1) & hash` with `n` a power of two produces a value in `[0, n)` by construction, sign bit and all, because the mask has zeros in every bit above `log2(n) - 1`.

Note also that `hash` here is the **raw** `key.hashCode()`. There is no spreading step. The modulus is supposed to be doing the mixing — which brings the whole argument back to whether it is worth what it costs.

### The diagram

A side-by-side of an 11-slot table under `% 11` against a 16-slot table under `& 15` would make the aliasing visible, but this file ships no new diagrams — the table geometry is drawn in [05-internals-e-sizing-and-iteration.md](05-internals-e-sizing-and-iteration.md).

### `[PROVE]` / `[NUM]` — mask versus modulo, in three registers

The introductory statement of this argument is leaf 3.6.16 in [01b-internals-a2-hash-spread-and-sizing.md](01b-internals-a2-hash-spread-and-sizing.md); this is the fuller treatment.

**Register one: instruction cost.** `(n - 1) & hash` is a single bitwise `AND`. On both x86-64 and aarch64 it is a one-cycle, fully pipelined ALU operation, and where the result immediately feeds an array load the mask often folds into the addressing computation, costing nothing distinguishable at all.

Integer division is different *in kind*, not merely in degree. It executes on a separate divider unit that is **not pipelined**, so consecutive divisions serialise against each other rather than overlapping, and its latency is roughly an order of magnitude above an ALU op. That structural gap — one pipelined cycle versus a serialising multi-cycle unit — is a fact and can be stated flatly.

**Unverified:** the syllabus's specific "~20–40 cycles" figure. That is a plausible range for x86-64 32-bit `idiv` on several microarchitectures, but it varies by vendor, generation and operand width, and aarch64's `sdiv` has a different (generally lower) latency again. No named instruction-latency table — Agner Fog's tables, the Intel SDM optimisation appendix, or the Arm software optimisation guide for the specific core — was available to consult here, so the number is not asserted. The qualitative claim stands without it.

The caveat that makes the honest version interesting: when the divisor is a **compile-time constant**, both HotSpot's C2 and every C compiler replace division with a multiply-and-shift reciprocal, and the gap collapses to almost nothing. `Hashtable` gets no such help. `tab.length` is a field read whose value changes at every `rehash()`, so the JIT has no constant to fold and emits a genuine division. This is the one place where "the compiler optimises it away" — usually the right instinct — does not apply.

**Register two: measure it in Java.** A harness with the divisor in a non-final instance field, so nothing can be constant-folded:

```java
import java.util.Random;

public class MaskVsMod {
    // non-final, non-static: the JIT cannot constant-fold the divisor
    int nPow2 = 1 << 20;
    int nPrime = 1_048_573; // largest prime below 2^20

    long mask(int[] h) {
        long acc = 0;
        int n = nPow2;
        for (int x : h) acc += (n - 1) & x;
        return acc;
    }

    long modulo(int[] h) {
        long acc = 0;
        int n = nPrime;
        for (int x : h) acc += (x & 0x7FFFFFFF) % n;
        return acc;
    }

    public static void main(String[] args) {
        int[] h = new int[1 << 22];
        Random r = new Random(42);
        for (int i = 0; i < h.length; i++) h[i] = r.nextInt();

        MaskVsMod b = new MaskVsMod();
        long sink = 0;
        for (int i = 0; i < 20; i++) { sink += b.mask(h); sink += b.modulo(h); }

        int reps = 30;
        long t0 = System.nanoTime();
        for (int i = 0; i < reps; i++) sink += b.mask(h);
        long tMask = System.nanoTime() - t0;

        t0 = System.nanoTime();
        for (int i = 0; i < reps; i++) sink += b.modulo(h);
        long tMod = System.nanoTime() - t0;

        double perMask = (double) tMask / reps / h.length;
        double perMod  = (double) tMod  / reps / h.length;
        System.out.printf("elements per rep : %,d%n", h.length);
        System.out.printf("mask   (n-1)&h        : %.3f ns/element%n", perMask);
        System.out.printf("modulo (h&0x7FFFFFFF)%%n: %.3f ns/element%n", perMod);
        System.out.printf("modulo / mask         : %.2fx%n", perMod / perMask);
        System.out.println("sink=" + sink);
    }
}
```

Real output — Apple M4 Pro (arm64), JDK 21.0.7+8-LTS-245 (`Java HotSpot(TM) 64-Bit Server VM, build 21.0.7+8-LTS-245, mixed mode, sharing`):

```
elements per rep : 4,194,304
mask   (n-1)&h        : 0.262 ns/element
modulo (h&0x7FFFFFFF)%n: 0.515 ns/element
modulo / mask         : 1.96x
sink=219891456884150
```

**Unverified:** single-shot wall clock, not JMH; the shape is the finding, not the digits.

And the honest reading is that **1.96× is far less than the raw instruction-latency gap would predict**. At 0.262 ns/element the mask loop is already close to memory bandwidth for a 16 MB `int[]`, the divider unit overlaps with the loads rather than stalling behind them, and both loops sit near the auto-vectorisation boundary. Say it plainly: at this scale the JIT and the memory system hide most of the difference. In a real `HashMap.get`, where a cache-missing array load and a virtual `equals()` call dominate the profile, the index arithmetic is a small share of the total. Anyone quoting "modulo is 40× slower than masking" as a *`HashMap`* fact is quoting an instruction table, not a map.

**Register three — the argument that actually decided it, and it is not about cycles.** Power-of-two capacity makes resize a single bit test.

Because capacity doubles, the new mask has exactly one more bit than the old one. An entry's new index is therefore either its old index, or its old index plus `oldCap` — and which one is decided by `(e.hash & oldCap) == 0`. `HashMap.resize` splits each bin into a `lo` list and a `hi` list in a single pass, computing no hashes, performing no divisions and calling no `equals`. See [03a-internals-c1-lo-hi-split.md](03a-internals-c1-lo-hi-split.md).

`Hashtable.rehash` has no such structure available to it:

```java
    protected void rehash() {
        int oldCapacity = table.length;
        Entry<?,?>[] oldMap = table;

        // overflow-conscious code
        int newCapacity = (oldCapacity << 1) + 1;
        if (newCapacity - MAX_ARRAY_SIZE > 0) {
            if (oldCapacity == MAX_ARRAY_SIZE)
                // Keep running with MAX_ARRAY_SIZE buckets
                return;
            newCapacity = MAX_ARRAY_SIZE;
        }
        Entry<?,?>[] newMap = new Entry<?,?>[newCapacity];

        modCount++;
        threshold = (int)Math.min(newCapacity * loadFactor, MAX_ARRAY_SIZE + 1);
        table = newMap;
```
— `java.base/java/util/Hashtable.java`, JDK 21, line 407. The per-entry relocation loop that follows this excerpt has been cut from the quote; it walks every old bin and recomputes `(e.hash & 0x7FFFFFFF) % newCapacity` for every single entry. (leaf 3.6.46)

There is no relationship between `x % 11` and `x % 23`. Knowing an entry's old bucket tells you nothing whatever about its new one, so every entry must be re-divided from scratch.

`[NUM]`, the arithmetic that settles it. Resizing a table holding 1,048,576 entries costs:

- `HashMap`: one `AND` and one comparison per node — **1,048,576 single-bit tests**, each a pipelined one-cycle ALU op, plus the pointer relinking.
- `Hashtable`: one `AND` plus one full integer division per node — **1,048,576 divisions** on a non-pipelined functional unit, plus the same relinking.

The mask is a small, largely hidden win per lookup. The split is a large, unhideable win per resize, on an operation that already stalls the application thread for the whole table. That asymmetry is what decided the design.

### The honest cost of the choice

Masking keeps only the **low** `log2(n)` bits of the hash and discards everything above them. A `hashCode()` whose entropy lives above bit 20 — and plenty do, including any hash built by shifting a discriminator into the high half — collides catastrophically under a mask, and a prime modulus would have mixed those bits in for free.

That, and only that, is why `hash()` exists:

```java
    static final int hash(Object key) {
        int h;
        return (key == null) ? 0 : (h = key.hashCode()) ^ (h >>> 16);
    }
```
— `java.base/java/util/HashMap.java`, JDK 21. (leaf 3.6.47)

`h ^ (h >>> 16)` folds the high half down onto the low half so the mask has something worth looking at. So `HashMap` pays one shift and one xor on **every** put, get and remove, forever, to buy a one-instruction index and a bit-test resize. That is the trade, stated whole — and it is the sentence to remember, because it explains why a "textbook says use a prime" answer is not wrong so much as incomplete. The spread function itself is owned by [01b-internals-a2-hash-spread-and-sizing.md](01b-internals-a2-hash-spread-and-sizing.md).

**Pitfall:** *"`Hashtable` is just a thread-safe `HashMap`."* Every public method is `synchronized` on the table instance. That makes each individual call atomic and nothing more: `if (!ht.containsKey(k)) ht.put(k, v);` is still a race, because another thread can interleave between the two synchronized calls. And because the lock is exclusive, readers serialise against readers — throughput on a read-heavy workload collapses to a single core no matter how many you have. `ConcurrentHashMap` gives you both the atomic compound operations (`putIfAbsent`, `computeIfAbsent`, `merge`) and genuinely concurrent reads. See [`../concurrent-collections/01-thread-safety-and-wrappers.md`](../concurrent-collections/01-thread-safety-and-wrappers.md).

**Insight:** the two design choices are not independent. `Hashtable` uses no spread function *because* it has a prime-ish modulus; `HashMap` needs a spread function *because* it has a mask. Neither is "the mixing step" on its own — the pair (index function, spread function) has to be designed together, and each design picked a coherent pair. What `Hashtable` did not anticipate is that its modulus stops being prime after the third resize, which leaves it with neither a spread function nor a prime.

**Interview:** *"Why is `HashMap`'s capacity a power of two when the textbooks say use a prime?"* Because the mask is one instruction where the modulo is a non-pipelined division, and — far more importantly — because doubling moves each entry either nowhere or exactly `oldCap` slots forward, so a resize is one bit test per node instead of a full rehash. The price is that masking throws away the high bits, which is why `HashMap` runs `h ^ (h >>> 16)` first.

**Version note.** `Hashtable`'s default capacity (11), its `(oldCapacity << 1) + 1` growth rule and its `(hash & 0x7FFFFFFF) % tab.length` index are unchanged in JDK 21 from the class's original design. **Unverified against JDK 8 source:** `/tmp/jdk8src/java/util/` on this machine contains only `HashMap.java`, `LinkedHashMap.java` and `ArrayDeque.java` — there is no JDK 8 `Hashtable.java` available to diff, so "unchanged" rests on the JDK 21 source plus the class's `@since 1.0` stability, not on a side-by-side comparison. `HashMap`, by contrast, changed materially in the same window: treeification arrived in Java 8, and the JDK 8 `HashMap.java` present here confirms the `(n - 1) & hash` index and `h ^ (h >>> 16)` spread were already in place then.

> **Definition.** `Hashtable` buckets with `(hash & 0x7FFFFFFF) % tab.length` over an odd — initially prime, composite from the fourth resize onward — capacity that grows by `2n+1`; `HashMap` buckets with `(n - 1) & hash` over a power-of-two capacity that doubles, trading away the high bits of the hash (recovered by `h ^ (h >>> 16)`) in exchange for a one-instruction index and a resize that relocates each entry by a single bit test.

---

## Pitfalls

### Assuming `Hashtable` capacities are prime

**Wrong**

```java
// "Hashtable uses primes, so the modulo distributes hashes well."
Hashtable<Integer, String> ht = new Hashtable<>();
for (int i = 0; i < 9_000; i++) ht.put(i * 11, "v");   // capacity is now 12287
```
The capacity sequence reaches 12,287 once the population passes the threshold at 6,143 (0.75 × 6143 = 4,607), and 12,287 = **11 × 1117**. For any key `h = 11k`, `11k mod (11 × 1117) = 11 × (k mod 1117)` — so every index is itself a multiple of 11. Those 9,000 entries land in 1,117 usable buckets out of 12,287, an 11× collision multiplier, in the exact case a prime modulus was supposed to protect against.

**Right**

```java
Map<Integer, String> m = new HashMap<>(1 << 14);   // power of two, explicit sizing
for (int i = 0; i < 9_000; i++) m.put(i * 11, "v");
```
`HashMap` masks and then relies on `h ^ (h >>> 16)` for mixing, and `Integer.hashCode()` returns the value itself, so multiples of 11 spread across the low bits normally. If you genuinely need a prime modulus, you must recompute a prime at every resize — which `Hashtable` does not do.

**Why people believe it:** the *initial* capacity 11 is prime, and the textbook rationale for modulo bucketing is always stated in terms of primes, so the property gets attributed to the implementation without anyone checking step 3 of the sequence. The rule `(c << 1) + 1` guarantees oddness only.

### Reaching for `Hashtable` when you need thread safety

**Wrong**

```java
Hashtable<String, Integer> counts = new Hashtable<>();
// called from many threads
if (!counts.containsKey(k)) {
    counts.put(k, 1);          // another thread can land between the two calls
} else {
    counts.put(k, counts.get(k) + 1);   // read-modify-write, also racy
}
```
Both calls are individually atomic and the sequence is not. Counts are lost under contention, and every reader blocks every other reader on the same monitor.

**Right**

```java
ConcurrentHashMap<String, Integer> counts = new ConcurrentHashMap<>();
counts.merge(k, 1, Integer::sum);   // one atomic compound operation
```
`merge` performs the whole read-modify-write under a per-bin lock, and reads on other bins proceed concurrently.

**Why people believe it:** the javadoc says `Hashtable` is synchronized, and "synchronized" reads as "safe". Per-method synchronization gives you atomicity of *calls*, which is almost never the granularity a program actually needs.

## Cheat sheet

| Item | `Hashtable` | `HashMap` |
|---|---|---|
| Default capacity | 11 | 16 (`1 << 4`) |
| Growth | `(oldCapacity << 1) + 1` → 11, 23, 47, 95, 191, 383, 767 | `oldCap << 1` → 16, 32, 64, 128 |
| Capacities prime? | 11, 23, 47, 191, 383, 6143 only — **6 of the first 15; 6,143 is the last prime** | n/a |
| Composite examples | 95 = 5×19, 767 = 13×59, 1535 = 5×307, 3071 = 37×83, 12287 = 11×1117 | n/a |
| Index | `(hash & 0x7FFFFFFF) % tab.length` | `(n - 1) & hash` |
| Why the `& 0x7FFFFFFF` | Java's `%` inherits the sign of the left operand; `tab[-7]` throws | not needed — mask yields `[0, n)` by construction |
| Spread function | none, raw `hashCode()` | `h ^ (h >>> 16)` |
| Null key / value | both rejected with `NullPointerException` | one null key (bin 0), any null values |
| Long bin | chains forever, O(n) | treeify at 8 nodes with capacity ≥ 64, O(log n) |
| Thread safety | `synchronized` on every method — atomic calls, racy compounds, readers block readers | none; use `ConcurrentHashMap` |
| Iteration | `Enumeration` + `Iterator` | `Iterator` only |
| Max capacity | `Integer.MAX_VALUE - 8` | `1 << 30` |
| Default threshold | `(int) min(11 × 0.75, MAX+1)` = 8 → resize on 9th put | `16 × 0.75` = 12 |
| Resize cost, 2^20 entries | ~1.05M integer divisions (non-pipelined unit) | ~1.05M single-bit tests `(e.hash & oldCap)` |
| Measured mask vs modulo | 0.515 vs 0.262 ns/element = **1.96×** — M4 Pro, JDK 21.0.7, **Unverified**, not JMH | |
| The deciding argument | not cycles — **resize is one bit test per node** | |
| The price paid | mask discards the high bits, so `hash()`'s xor-shift is mandatory | |

## Self-test

**Q1.** Is `Hashtable`'s capacity sequence prime?

<details><summary>Answer</summary>

Only at first. `(c << 1) + 1` from 11 gives 11, 23, 47, **95 = 5 × 19**, 191, 383, **767 = 13 × 59**, **1535 = 5 × 307**, **3071 = 37 × 83**, 6143, **12287 = 11 × 1117**, and nothing prime thereafter — 6 of the first 15 are prime, and **6,143 is the last of them**. The rule guarantees oddness, not primality. Every production-sized `Hashtable` runs a composite modulus, which is the property the design was supposedly buying with a division.

</details>

**Q2.** `Hashtable` computes `(hash & 0x7FFFFFFF) % tab.length`. Why is the mask there, given the `%` is doing the bucketing?

<details><summary>Answer</summary>

Java's `%` takes the sign of its left operand, so a negative `hashCode()` yields a negative index and `tab[negative]` throws `ArrayIndexOutOfBoundsException`. `0x7FFFFFFF` is `Integer.MAX_VALUE` — all 31 low bits set, sign bit clear — so the `AND` forces the value non-negative before the division. Roughly half of all hash values are negative, so it is not an edge case. `HashMap` needs no equivalent, because `(n - 1) & hash` with a power-of-two `n` lands in `[0, n)` by construction whatever the sign of `hash`.

</details>

**Q3.** State the strongest argument for power-of-two capacity, and it is not the instruction count.

<details><summary>Answer</summary>

Resize. Doubling adds exactly one bit to the mask, so each entry's new index is either its old index or its old index plus `oldCap`, decided by `(e.hash & oldCap) == 0`. `HashMap.resize` splits every bin into a lo-list and a hi-list in one pass with no hashing, no division and no `equals`. `Hashtable.rehash` must recompute `(hash & 0x7FFFFFFF) % newCapacity` for every entry, because `x % 11` tells you nothing about `x % 23`. At 2^20 entries that is 1,048,576 pipelined bit tests versus 1,048,576 divisions on a non-pipelined unit.

</details>

**Q4.** Why is it wrong to say "modulo is 20–40× slower, so `HashMap` is 20–40× faster at indexing"?

<details><summary>Answer</summary>

Two reasons. First, the cycle figure itself is microarchitecture-specific and was not verified here — it is a plausible x86-64 `idiv` range, but aarch64's `sdiv` differs and operand width matters. Second, and more importantly, instruction latency is not throughput in context. Measured on an M4 Pro at 4.2M elements, mask ran 0.262 ns/element against modulo's 0.515 — a 1.96× difference, because the divider overlaps with loads and the loop is near memory bandwidth. In a real `get()` a cache-missing array load and a virtual `equals()` dominate the profile entirely. The correct claim is structural, not numeric: division uses a non-pipelined unit and cannot be constant-folded here because `tab.length` is a runtime value.

</details>

**Q5.** What does `HashMap` pay for the power-of-two choice?

<details><summary>Answer</summary>

Masking keeps only the low `log2(n)` bits and discards everything above them, so any `hashCode()` whose entropy lives in the high bits collides catastrophically — a prime modulus would have mixed those bits in for free. `HashMap` compensates with `hash()`'s `h ^ (h >>> 16)`, folding the high half down onto the low half, on every put, get and remove. One shift and one xor per operation, forever, to buy a one-instruction index and a bit-test resize.

</details>

**Q6.** How many puts does it take to resize a default `Hashtable`, and what capacity does it land on?

<details><summary>Answer</summary>

Nine, landing on 23. `new Hashtable<>()` calls `this(11, 0.75f)`, so `threshold = (int) Math.min(11 × 0.75f, MAX_ARRAY_SIZE + 1)` = 8. `addEntry` rehashes when `count >= threshold`, so the ninth put triggers it, and `rehash()` computes `(11 << 1) + 1 = 23`. Verified reflectively on JDK 21: capacity 11 before, 23 after nine puts. Compare `HashMap`: threshold 12 on a 16-slot table, resizing to 32 on the thirteenth put.

</details>

**Q7.** Why does `Hashtable` have no equivalent of `HashMap.hash()`?

<details><summary>Answer</summary>

Because the two choices are a matched pair. `Hashtable`'s modulus is meant to do the mixing — a prime divisor involves every bit of the dividend in the result, so a spread step would be redundant. `HashMap`'s mask involves only the low bits, so it *must* spread first. Neither the index function nor the spread function is "the mixing step" alone; they are designed together. The irony is that `Hashtable`'s modulus stops being prime after the third resize, leaving it with neither a spread function nor a prime.

</details>

**Q8.** `Hashtable` is synchronized on every method. Name a two-line program that is still incorrect under concurrency.

<details><summary>Answer</summary>

`if (!ht.containsKey(k)) ht.put(k, v);` — two individually atomic calls with a gap between them, so two threads can both see the key absent and both put. Per-method synchronization gives atomicity of *calls*, never of compound actions. It also serialises readers against readers on one monitor, so read-heavy throughput collapses to a single core. `ConcurrentHashMap.putIfAbsent(k, v)` makes the compound action atomic and lets unrelated bins proceed in parallel.

</details>

## Open questions

- **JDK 8 `Hashtable` diff.** `/tmp/jdk8src/java/util/` on this machine contains only `HashMap.java`, `LinkedHashMap.java` and `ArrayDeque.java`. The claim that `Hashtable`'s default capacity, `2n+1` growth and `(hash & 0x7FFFFFFF) % tab.length` index are identical in JDK 8 and JDK 21 could not be confirmed by diff. A copy of the JDK 8 `java/util/Hashtable.java` would settle it.
- **`idiv` / `sdiv` cycle counts.** The syllabus's "~20–40 cycles" is deliberately not asserted here; no citable instruction-latency table (Agner Fog's tables, Intel SDM optimisation appendix, or the Arm software optimisation guide for the relevant core) was available. Only the structural claim — separate, non-pipelined divider unit — is stated as fact.
- **Benchmark rigour.** The 1.96× mask-versus-modulo figure is single-shot `System.nanoTime` wall clock with a warm-up loop, not JMH. A JMH rerun with `Blackhole` consumption, forked JVMs and a working set small enough to stay in L2 would separate the arithmetic cost from the memory-bandwidth ceiling, and would likely widen the gap.

---

**Leaves covered:** 3.6.46, 3.6.47 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none new — the sizing arithmetic (D-99) is embedded in [05-internals-e-sizing-and-iteration.md](05-internals-e-sizing-and-iteration.md)
**Target version:** Java 21 LTS
**Lines:** 441
