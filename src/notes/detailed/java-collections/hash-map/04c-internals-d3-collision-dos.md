# 02 Java Collections — `HashMap` — INTERNALS (§3.6 `HashMap` source walk — collision DoS, and treeification versus randomised hashing)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [hash-map/04b-internals-d2-poisson-and-hysteresis.md](04b-internals-d2-poisson-and-hysteresis.md) · Next: [hash-map/05-internals-e-sizing-and-iteration.md](05-internals-e-sizing-and-iteration.md)

A hash map's O(1) promise is **statistical, not structural**. The work per operation is bounded by the length of one bin, and bins stay short only because keys are assumed to land roughly uniformly. That assumption is load-bearing, and it is an assumption about *the keys*, not about the map. On a web server the keys are form parameter names, JSON object keys, HTTP header names and query-string parameters — every one of them chosen by whoever sent the request. An attacker who picks keys that all hash to the same bin has not found a bug in `HashMap`; they have attacked the assumption directly, and the data structure does exactly what it was told to.

Everything below follows from that framing: the arithmetic of what happens when the assumption fails, and the two different places the JDK tried to repair it.

---

## Hash-collision DoS: n colliding keys, and the O(n²) that follows

*Leaf 3.6.35. `[PROVE]` `[RESEARCH]`*

### Mental model

Picture the healthy map as a wide, shallow filing cabinet: a thousand drawers, one or two folders in each, and finding a folder means opening one drawer and glancing at it. Now picture an attacker who has arranged for every folder to be filed in drawer 7. The cabinet is unchanged. The lookup code is unchanged. But every filing operation now means pulling out drawer 7 and reading every folder already in it, to check you are not filing a duplicate. The tenth folder costs nine reads; the ten-thousandth costs 9,999. Nobody broke in — they just handed you paperwork sorted the wrong way.

### Why it exists — the problem, and what came before

Before 2011 essentially every mainstream language shipped a hash table with a *public, deterministic, fast, non-cryptographic* hash function. That is three good properties and one fatal one. Fast and non-cryptographic means the function is cheap to invert or to search for preimages; public and deterministic means the attacker can do that search offline, once, and reuse the result against every server on the internet running that language. The pre-2011 mitigation was, in practice, that nobody had bothered — the attack was known in the literature (Crosby and Wallach, USENIX Security 2003) but had not been packaged per-platform.

That changed at the 28th Chaos Communication Congress in December 2011: Alexander Klink and Julian Wälde presented **"Efficient Denial of Service Attacks on Web Application Platforms"**, packaging the attack against PHP, Python, Java, Ruby, ASP.NET and the V8 JavaScript engine simultaneously. The coordinated advisory is **oCERT-2011-003**, which credits both researchers and lists Java (all versions), Apache Tomcat ≤ 7.0.22, Jetty ≤ 7.5.4, Oracle GlassFish ≤ 3.1.1, Apache Geronimo, JRuby ≤ 1.6.5, PHP ≤ 5.3.8, Python ≤ 2.7.3, Ruby ≤ 1.8.7-p356, Rack ≤ 1.3.5, Plone and V8 as affected. The Tomcat entry is **CVE-2011-4858**: "Apache Tomcat before 5.5.35, 6.x before 6.0.35, and 7.x before 7.0.23 computes hash values for form parameters without restricting the ability to trigger hash collisions predictably, which allows remote attackers to cause a denial of service (CPU consumption) by sending many crafted parameters."

### When this matters, and when it does not

It matters exactly when **key strings cross a trust boundary**. Request parameters, header names, JSON/XML element names, uploaded CSV column headers, cache keys derived from user input. It does not matter for keys you generate — enum names, column names from your own schema, IDs from your own sequence — because the attacker cannot choose them. The sibling that wins where `HashMap` loses here is any structure with a **worst-case** rather than average-case bound: `TreeMap` is O(log n) per operation unconditionally, at the price of O(log n) on the healthy path too, where `HashMap` is O(1). For untrusted key sets that is often the right trade.

### How it works — the arithmetic

`putVal` (JDK 21 `HashMap.java` line **631**) walks the bin looking for an existing equal key before appending. With every key in one bin, inserting the *i*-th key walks a chain of length *i*−1:

```
0 + 1 + 2 + ... + (n-1)  =  n(n-1)/2  =  Θ(n²)
```

| n keys, all colliding | comparisons on insert | uniform case (λ ≈ 0.5) |
|---|---|---|
| 1,000 | 499,500 | ~500 |
| 10,000 | 49,995,000 | ~5,000 |
| 100,000 | 4,999,950,000 | ~50,000 |

The uniform column is Θ(n): each insert touches a bin of expected length ~λ, and λ is held near 0.5 by the load factor. Ten thousand keys is the difference between five thousand comparisons and fifty million — four orders of magnitude, from key choice alone.

**Insight:** the attack's whole force is *asymmetry*. The attacker spends one HTTP POST containing *n* parameters — Θ(n) bytes, sent once, over a slow link. The server spends Θ(n²) CPU parsing it into a map, and it spends that on a request-handling thread it cannot easily abandon. Klink and Wälde's demonstration reported that a PHP target could be kept at full CPU on one Intel i7 core with a sustained upload of roughly 70–100 kbit/s. **Unverified:** that bandwidth figure comes from contemporary press coverage of the talk rather than from the slides themselves; the per-platform table of request size against CPU seconds was not re-confirmed against a primary source for these notes. The mechanism — sublinear bandwidth buying superlinear CPU — is confirmed by oCERT-2011-003, which describes "specially crafted HTTP requests" causing CPU utilisation "up to 100%" for durations measured in hours.

### Where the diagram would go

The measured collision curves are **D-147**, embedded with the build-it demo in [10-build-my-hash-map-e-set-linked-and-diff.md](10-build-my-hash-map-e-set-linked-and-diff.md); the treeified bin itself is **D-91** in [04-internals-d-treeify.md](04-internals-d-treeify.md). Nothing new is drawn here.

### Concrete example — generating the colliding keys

`String.hashCode()` is the polynomial `s[0]*31^(n-1) + s[1]*31^(n-2) + ... + s[n-1]`. Two characters are enough to find a collision by hand:

```
"Aa" -> 'A'*31 + 'a' = 65*31 + 97 = 2015 + 97 = 2112
"BB" -> 'B'*31 + 'B' = 66*31 + 66 = 2046 + 66 = 2112
```

Because the function is a polynomial with a fixed base, the contribution of a two-character block depends only on the block and on its position — so substituting `"BB"` for `"Aa"` at any position leaves the total unchanged. Concatenation therefore *preserves* collision: any string assembled from *k* blocks each drawn from `{"Aa", "BB"}` collides with all 2^k of its siblings. Sixteen characters buys 256 colliding keys; thirty-two characters buys 65,536; forty characters buys over a million.

```java
import java.util.*;

public class CollisionGen {

    /** Every string built from k pieces of {"Aa","BB"} shares one hashCode, because
     *  String.hashCode() is the polynomial s[0]*31^(n-1) + ... + s[n-1] and the two
     *  pieces are equal under it at every position. */
    static List<String> collidingStrings(int k) {
        List<String> out = new ArrayList<>(1 << k);
        out.add("");
        for (int i = 0; i < k; i++) {
            List<String> next = new ArrayList<>(out.size() * 2);
            for (String s : out) {
                next.add(s + "Aa");
                next.add(s + "BB");
            }
            out = next;
        }
        return out;
    }

    public static void main(String[] args) {
        System.out.println("\"Aa\".hashCode() = " + "Aa".hashCode()
                + "   by hand: 'A'*31 + 'a' = " + (65 * 31 + 97));
        System.out.println("\"BB\".hashCode() = " + "BB".hashCode()
                + "   by hand: 'B'*31 + 'B' = " + (66 * 31 + 66));
        System.out.println("equal hashes, unequal strings: "
                + ("Aa".hashCode() == "BB".hashCode()) + " / " + "Aa".equals("BB"));

        for (int k : new int[] { 8, 12, 16 }) {
            List<String> keys = collidingStrings(k);
            int h = keys.get(0).hashCode();
            for (String s : keys) {
                if (s.hashCode() != h) throw new AssertionError("not colliding: " + s);
            }
            Set<String> distinct = new TreeSet<>(keys);
            System.out.printf("k=%2d  keys=%,8d  distinct=%,8d  length=%d chars  shared hashCode=%d  example=%s%n",
                    k, keys.size(), distinct.size(), keys.get(0).length(), h, keys.get(0));
        }
    }
}
```

Real output, JDK 21.0.7+8-LTS-245 on Apple M4 Pro:

```
"Aa".hashCode() = 2112   by hand: 'A'*31 + 'a' = 2112
"BB".hashCode() = 2112   by hand: 'B'*31 + 'B' = 2112
equal hashes, unequal strings: true / false
k= 8  keys=     256  distinct=     256  length=16 chars  shared hashCode=2118287872  example=AaAaAaAaAaAaAaAa
k=12  keys=   4,096  distinct=   4,096  length=24 chars  shared hashCode=-1133886720  example=AaAaAaAaAaAaAaAaAaAaAaAa
k=16  keys=  65,536  distinct=  65,536  length=32 chars  shared hashCode=2067858432  example=AaAaAaAaAaAaAaAaAaAaAaAaAaAaAaAa
```

The `distinct` column is the assertion that matters: 65,536 pairwise-different strings, one shared `hashCode`. This generator is textbook material; the design of `String.hashCode` and why base 31 was chosen belong to [`../contracts/03-equals-hashcode-jdk.md`](../contracts/03-equals-hashcode-jdk.md), which owns that leaf.

### Treeification's bound — stated honestly

Once a bin reaches `TREEIFY_THRESHOLD = 8` (line **260**) *and* the table has reached `MIN_TREEIFY_CAPACITY = 64` (line **275**), `treeifyBin` (line **761**) converts the bin to a red-black tree. Insert *i* into a tree of size *i*−1 then costs O(log i), and the total becomes:

```
Σ log i  =  Θ(n log n)
```

For n = 10,000 that is roughly 130,000 comparisons instead of 50,000,000 — a factor of ~380 on paper.

**But the bound only holds if the keys are `Comparable`.** A red-black tree needs a total order; hash codes are all equal here, so ordering falls back to `compareTo` when the key class is a genuine `Comparable<C>`, and otherwise to `tieBreakOrder`, which orders by `System.identityHashCode`. A lookup key that is `equals`-equal to a stored key does not share its identity hash, so `TreeNode.find` cannot prune — it must search both subtrees, and the insert loop stays Θ(n²) while paying 56 bytes per node instead of 32 and a tree walk instead of a list walk. [04a-internals-d1-puttreeval-and-comparable.md](04a-internals-d1-puttreeval-and-comparable.md) owns `comparableClassFor`/`tieBreakOrder` (leaves 3.6.31–3.6.32) and the `find` mechanism; the `TreeNode` byte cost is 3.6.30 in [04-internals-d-treeify.md](04-internals-d-treeify.md).

The class comment concedes it (JDK 21 `HashMap.java`, lines 160–200; javadoc line-prefixes stripped):

> performance degrades gracefully under accidental or malicious usages in which hashCode() methods return values that are poorly distributed, as well as those in which many keys share a hashCode, **so long as they are also Comparable. (If neither of these apply, we may waste about a factor of two in time and space compared to taking no precautions.** But the only known cases stem from poor user programming practices that are already so slow that this makes little difference.)

**Insight — the sharpest point in this file:** `String` is `Comparable`, and `String` is precisely what an attacker controls on a web request. So the JDK's defence happens to cover the entire realistic attack surface. A custom key type of your own that is *not* `Comparable` gets no protection whatsoever, and no warning.

### Measure it

Insert *n* keys with identical hash codes. `Hashtable` is the control: JDK 21's `Hashtable.java` contains zero occurrences of `TreeNode` or `treeify`, so it is a bin that provably never treeifies.

```java
import java.util.*;

public class CollisionBench {

    /** Comparable key with a fixed hashCode — treeification can order it by compareTo. */
    record CmpKey(int id) implements Comparable<CmpKey> {
        @Override public int hashCode() { return 0; }
        @Override public int compareTo(CmpKey o) { return Integer.compare(id, o.id); }
    }

    /** Same key, NOT Comparable — treeification falls back to tieBreakOrder. */
    record PlainKey(int id) {
        @Override public int hashCode() { return 0; }
    }

    static long timeHashtable(int n) {          // control: Hashtable has no tree bins
        Hashtable<CmpKey, Integer> m = new Hashtable<>();
        long t0 = System.nanoTime();
        for (int i = 0; i < n; i++) m.put(new CmpKey(i), i);
        long t = System.nanoTime() - t0;
        if (m.size() != n) throw new AssertionError();
        return t;
    }

    static long timeComparable(int n) {
        HashMap<CmpKey, Integer> m = new HashMap<>();
        long t0 = System.nanoTime();
        for (int i = 0; i < n; i++) m.put(new CmpKey(i), i);
        long t = System.nanoTime() - t0;
        if (m.size() != n) throw new AssertionError();
        return t;
    }

    static long timeNotComparable(int n) {
        HashMap<PlainKey, Integer> m = new HashMap<>();
        long t0 = System.nanoTime();
        for (int i = 0; i < n; i++) m.put(new PlainKey(i), i);
        long t = System.nanoTime() - t0;
        if (m.size() != n) throw new AssertionError();
        return t;
    }

    static double medianMs(java.util.function.IntToLongFunction f, int n) {
        long[] r = new long[3];
        for (int i = 0; i < 3; i++) r[i] = f.applyAsLong(n);
        Arrays.sort(r);
        return r[1] / 1_000_000.0;
    }

    public static void main(String[] args) {
        for (int w = 0; w < 3; w++) { timeHashtable(500); timeComparable(500); timeNotComparable(500); }
        System.out.printf("%8s %14s %14s %18s%n", "keys", "Hashtable ms", "tree/Cmp ms", "tree/notCmp ms");
        for (int n : new int[] { 1000, 2000, 5000, 10000, 20000 }) {
            System.out.printf("%,8d %14.2f %14.2f %18.2f%n", n,
                    medianMs(CollisionBench::timeHashtable, n),
                    medianMs(CollisionBench::timeComparable, n),
                    medianMs(CollisionBench::timeNotComparable, n));
        }
    }
}
```

Real output — **Apple M4 Pro, arm64, JDK 21.0.7+8-LTS-245, median of three runs**:

```
    keys   Hashtable ms    tree/Cmp ms     tree/notCmp ms
   1,000           0.93           0.43               1.99
   2,000           3.66           0.42               3.40
   5,000          26.03           0.70              28.09
  10,000         106.20           1.08             126.87
  20,000         382.29           1.66             546.13
```

**Unverified:** these are single-shot wall clock, not JMH — the shape is the finding, not the absolute milliseconds.

And the shape is unmistakable. The `Hashtable` column, doubling n each step past 5,000: 26.03 → 106.20 → 382.29, roughly **quadrupling** — the n² signature, exactly as `n(n−1)/2` predicts. The `Comparable` column: 0.70 → 1.08 → 1.66, roughly **doubling**, which is n log n behaving like n over a small range of n. At 20,000 keys that is 1.66 ms against 382 ms: a **~230× difference**, from nothing but the key type implementing `Comparable`.

The third column is the honest caveat made visible: 546 ms against the control's 382 ms. Treeifying non-`Comparable` colliding keys is *slower than not treeifying at all*, because `find` degenerates to a two-sided search over a structure that costs 56 bytes per node — the "factor of two in time and space" the class comment warns about, measured.

### The gotcha

`MIN_TREEIFY_CAPACITY = 64` means a small map never treeifies at all: below a table length of 64, `treeifyBin` resizes instead ([02b-internals-b2-bincount-and-treeifybin.md](02b-internals-b2-bincount-and-treeifybin.md), leaf 3.6.22). For an attack that is irrelevant — the attacker sends 10,000 parameters, the table grows past 64 immediately — but it means a *microbenchmark* with 50 colliding keys measures a linked list and proves nothing about tree bins.

### Mitigations that actually work

| Mitigation | What it costs | Where it fails | Real-world uptake |
|---|---|---|---|
| Cap parsed parameter count at the framework boundary | One config value; rejects legitimate giant forms | Only covers the boundary you capped | Universal — the 2011 fix everywhere |
| Randomised/keyed hash for untrusted input (e.g. SipHash) | Slower hash on every op; iteration order varies | Bounds nothing if the seed leaks or luck runs out | Python 3.3+, Ruby 1.9+, Perl |
| Never use attacker-controlled strings as map keys | Redesign; often impractical for request parsing | Discipline, unenforced by the compiler | Rare |
| Worst-case-bounded structure (`TreeMap`, sorted array) | O(log n) on the healthy path too | Requires `Comparable` keys | Occasional, for known-hostile input |

The 2011 fix was overwhelmingly the first row. oCERT-2011-003's fixed-version list is a list of platforms that shipped input caps or hash changes within weeks: Tomcat ≥ 5.5.35 / 6.0.35 / 7.0.23, Jetty ≥ 7.6.0.RC3, PHP ≥ 5.3.9 / 5.4.0RC4, Python ≥ 2.6.8 / 2.7.3 / 3.1.5 / 3.2.3, Ruby ≥ 1.8.7-p357, Rack ≥ 1.1.3 / 1.2.5 / 1.3.6 / 1.4.0. Tomcat's specific mechanism is the `maxParameterCount` attribute on the `Connector`, defaulting to 10,000, with a negative value meaning unlimited — introduced in the 7.0.23 fix. **Unverified:** the `maxParameterCount` default of 10,000 and the negative-means-unlimited semantics are from Tomcat 7 connector documentation surfaced in search rather than fetched from the Tomcat 7.0.23 changelog directly; the attribute name and its role in the CVE-2011-4858 fix are confirmed. The reason the cap dominated is that it is a one-line change that works regardless of what the language's map does — you do not have to trust the runtime.

> **Definition.** *Hash-collision DoS* is an attack that supplies n keys engineered to share a hash bin, converting a hash table's amortised Θ(n) bulk insert into Θ(n²), so that Θ(n) bytes of attacker input buy Θ(n²) server CPU.

---

## Why the JDK fixed the data structure rather than the hash function

*Leaf 3.6.36. `[RESEARCH]`*

### Mental model

Two ways to stop a flooded room. Make the flood unlikely — better seals, a secret about where the pipes run. Or install a drain, so the flood is survivable when it happens anyway. Java 7 tried the seals. Java 8 installed the drain, then *removed the seals*, because a drain lets you build a cheaper wall.

### What Java 7u6 actually shipped

From OpenJDK `jdk7u`, `jdk/src/share/classes/java/util/HashMap.java`:

```java
final int hash(Object k) {
    int h = hashSeed;
    if (0 != h && k instanceof String) {
        return sun.misc.Hashing.stringHash32((String) k);
    }
    h ^= k.hashCode();
    h ^= (h >>> 20) ^ (h >>> 12);
    return h ^ (h >>> 7) ^ (h >>> 4);
}
```

and the property holder in the same file:

```java
static final int ALTERNATIVE_HASHING_THRESHOLD_DEFAULT = Integer.MAX_VALUE;

private static class Holder {
    static final int ALTERNATIVE_HASHING_THRESHOLD;
    static {
        String altThreshold = java.security.AccessController.doPrivileged(
            new sun.security.action.GetPropertyAction(
                "jdk.map.althashing.threshold"));
        // initialization logic follows: parses the property, treats -1 and
        // unset as "use the default", i.e. Integer.MAX_VALUE
    }
}
```

Read what that code does and does not do, because three facts fall straight out of it:

1. **`hashSeed` is per-map and zero by default.** The `if (0 != h && ...)` guard means the alternative path is dead code until a seed is installed.
2. **It only ever applies to `String`.** `k instanceof String` is right there. Any other attacker-influenced key type — a wrapper around a header name, a case-insensitive string class, a tuple — is unprotected.
3. **It is off unless you set a system property.** `ALTERNATIVE_HASHING_THRESHOLD_DEFAULT = Integer.MAX_VALUE`, so no map ever crosses it. Oracle's own Java 7 collections notes give the property's default as `-1` ("disables the alternative hash function") with a *recommended* value of 512 — the sentinel differs from the source constant, but both mean the same thing: **shipped disabled**.

Shipping a security mitigation disabled by default is itself the tell. And Oracle said why, in the Java 7 documentation, unprompted:

> If the alternative hash function is being used, then the iteration order of keys, values, and entities vary for each instance of `HashMap`, `Hashtable`, `HashSet`, and `ConcurrentHashMap`. This change in iteration order may cause compatibility issues with some programs. **This is the reason that the alternative hash function is disabled by default.**

That answers, from a primary source, the question of whether the iteration-order churn caused reported compatibility problems: it caused enough concern that the feature was never turned on. Note also the wider blast radius — `Hashtable`, `WeakHashMap`, `Properties` and `Provider` all inherited the mechanism in 7u6, and all of them had it removed again in 8.

### Why it was unsatisfactory

| Objection | Substantiated by |
|---|---|
| Covered only `String` | The `k instanceof String` guard in the quoted 7u6 source |
| Varied iteration order run to run, breaking order-dependent code | Oracle's Java 7 collections notes, quoted above |
| Cost a seed load and a branch on **every** `hash()` call on every map forever | The quoted source: `int h = hashSeed;` executes unconditionally |
| Required a new private `hash32` field on every `String` instance | JEP 180 Motivation: "at the cost of adding a new (private) field to every String instance" |
| **Bounded nothing** | Argument, below |

The last row is the decisive one and it is not an empirical claim, it is a structural one. A randomised hash makes a colliding key set hard to *find*. It does not make a collided bin *fast*. If the attacker gets lucky, or extracts the seed — through timing, through any endpoint that leaks iteration order, through a heap dump — the Θ(n²) is untouched and waiting. This is defence by keeping a secret, and secrets have a half-life. Worse, it is a tax paid by the 99.999% of maps that will never see a hostile key, in exchange for making the hostile case *improbable* rather than *cheap*.

### Why treeification is the better answer

JEP 180, **"Handle Frequent HashMap Collisions with Balanced Trees"** (author Mike Duigou, owner Brent Christian, delivered in Java 8, issue **JDK-8046170**) states the trade explicitly:

> Earlier work in this area in JDK 8, namely the alternative string-hashing implementation, improved collision performance for string-valued keys only, and it did so at the cost of adding a new (private) field to every String instance. The changes proposed here will improve collision performance for any key type that implements Comparable. The alternative string-hashing mechanism, including the private hash32 field added to the String class, can then be removed.

**Correction to the syllabus:** the leaf suggests JDK-8023463 as the issue to cite. JDK-8023463 is a real HashMap change in Java 8 but is not the treeification JEP; the authoritative citation is **JEP 180 / JDK-8046170**, quoted above, which I could fetch directly. Do not cite 8023463 for treeification.

Argued out, the case for the tree over the seed is four points:

- **It changes the worst case, not the probability of the worst case.** Θ(n log n) holds whether the attacker got lucky, guessed the seed, or read your source code. That is a categorically stronger kind of guarantee than "hard to find".
- **It costs nothing when it does not fire.** By the Poisson argument, a bin of eight under well-distributed hashes occurs less than once in ten million ([04b-internals-d2-poisson-and-hysteresis.md](04b-internals-d2-poisson-and-hysteresis.md), leaves 3.6.33–3.6.34). The healthy path pays a single already-necessary `binCount` increment.
- **It is key-type-agnostic in principle.** JEP 180 says "any key type that implements Comparable" — a strictly larger set than `String`. Honest caveat: it is *not* type-agnostic in practice, since non-`Comparable` keys get the degenerate two-sided `find` measured above, which is worse than nothing.
- **It let the hash function get simpler.** This is the cleanest evidence that the design intent moved. Java 7 needed five shifts and four xors to smear bad hash codes across the table, because a long bin had to be *prevented*. Java 21 needs one shift and one xor, because a long bin merely has to be *survived*:

```java
// JDK 21, HashMap.java line 336 — no seed, no branch, no String special case,
// no system property. Compare with the 7u6 version quoted above.
static final int hash(Object key) {
    int h;
    return (key == null) ? 0 : (h = key.hashCode()) ^ (h >>> 16);
}
```

The class comment immediately above it says so in as many words: "because we use trees to handle large sets of collisions in bins, we just XOR some shifted bits in the cheapest possible way". Leaf 3.6.13 in [01b-internals-a2-hash-spread-and-sizing.md](01b-internals-a2-hash-spread-and-sizing.md) owns the spread function itself.

The price paid, stated plainly: +24 bytes per node in a treeified bin (32 → 56, leaf 3.6.30), and `java.util.HashMap` now depends at runtime on `java.lang.Comparable` *semantics* and on reflection over generic supertypes, via `comparableClassFor`.

### Verifying the removal

Grepping the JDK 8 `java/util/HashMap.java` for `hashSeed` returns **0 occurrences**; grepping for `althashing` **exits non-zero with no match**. Grepping the whole of JDK 21's `java.base/java/util/` for either string returns **nothing at all**. The mechanism is gone, confirmed from the source rather than from documentation.

**Correction to the task brief:** the local JDK 8 tree at `/tmp/jdk8src/java/util/` contains only `ArrayDeque.java`, `HashMap.java` and `LinkedHashMap.java`, so `Hashtable` and `WeakHashMap` could not be grepped for JDK 8. Oracle's Java 8 collections notes cover them from the other side, verbatim: "The features added in 7u6 applied to WeakHashMap and Hashtable (and by extension Properties and Provider) but in JDK 8 these have been removed." JEP 180 adds that `Hashtable` and `WeakHashMap` were reverted to their pre-7u6 state and deliberately did *not* get tree bins — `Hashtable` because legacy code depends on its iteration order, `WeakHashMap` because the weak-key bookkeeping cost too much. My grep of JDK 21 `Hashtable.java` for `TreeNode|treeify` returning 0 is the current-day confirmation, and is why it works as the control in the benchmark.

**Pitfall:** the wrong belief is *"Java 8's `HashMap` is immune to hash-collision DoS."* It is not. It is bounded at Θ(n log n) for `Comparable` keys, effectively unbounded for non-`Comparable` ones (and measurably *worse* than a plain chain there), and a bin does not treeify at all until the table reaches 64. The symptom of believing it is an application with no parameter cap. The fix is to bound untrusted input at the boundary and treat treeification as a safety net, not a defence.

**Interview:** *"Java 7 randomised the hash and Java 8 removed that. Was that a security regression?"* — No. The defence moved from making collisions hard to *find* to making them cheap to *survive*, which is a stronger guarantee (worst case, not probability), costs nothing on the healthy path, and covers any `Comparable` key rather than only `String`.

> **Definition.** *Treeification over randomised hashing* is the JDK 8 decision (JEP 180) to bound collision cost in the bin structure — converting a bin of ≥ 8 to a red-black tree — instead of obscuring collisions with a per-map hash seed, trading a probabilistic, `String`-only, always-on-cost mitigation for a worst-case, `Comparable`-keyed, zero-cost-when-idle one.

---

## Open questions

| Question | Why it is open | What would settle it |
|---|---|---|
| The 28C3 per-platform request-size → CPU-seconds table | Only reached press coverage of the talk, not the slides | The original 28C3 slide deck or the recorded talk |
| The 70–100 kbit/s figure for saturating one i7 core | Same — secondary source | Same |
| `maxParameterCount` default of 10,000 in the 7.0.23 fix specifically | Confirmed for Tomcat 7 generally, not from the 7.0.23 changelog | Tomcat 7.0.23 changelog / the Tomcat 7 security advisory page |
| The JDK issue that *removed* alternative hashing | JEP 180 announces the intent; the removal changeset id was not found | OpenJDK JIRA search under JDK-8046170's subtasks |
| JDK 8 `Hashtable`/`WeakHashMap` source confirmation | Files absent from the local JDK 8 tree | Full JDK 8 source drop |

---

## Pitfalls

### Benchmarking collision behaviour with a small map

**Wrong**

```java
// "Proving" tree bins with 50 colliding keys.
record K(int id) implements Comparable<K> {
    @Override public int hashCode() { return 0; }
    @Override public int compareTo(K o) { return Integer.compare(id, o.id); }
}
var m = new HashMap<K, Integer>();
for (int i = 0; i < 50; i++) m.put(new K(i), i);
// No tree bin exists. The table never reached MIN_TREEIFY_CAPACITY = 64,
// so treeifyBin resized instead of treeifying. You measured a linked list.
```

**Right**

```java
// Cross 64 table slots so treeifyBin actually treeifies, and vary n to see the curve.
for (int n : new int[] { 1_000, 10_000, 20_000 }) {
    var m = new HashMap<K, Integer>();
    long t0 = System.nanoTime();
    for (int i = 0; i < n; i++) m.put(new K(i), i);
    System.out.printf("n=%,d  %.2f ms%n", n, (System.nanoTime() - t0) / 1e6);
}
// Now the timings grow ~linearly rather than ~quadratically, which is the
// observable signature of a tree bin.
```

**Why people believe it:** `TREEIFY_THRESHOLD = 8` is the constant everyone memorises, and `MIN_TREEIFY_CAPACITY = 64` is the one nobody mentions. Both must be satisfied.

### Assuming a custom key type gets the same protection as `String`

**Wrong**

```java
// Not Comparable. Fixed hashCode. Believed to be "protected since Java 8".
record HeaderName(String value) {
    @Override public int hashCode() { return 0; }   // stand-in for a badly-distributed real hash
}
// Measured above: 546 ms for 20,000 keys — worse than Hashtable's 382 ms,
// because TreeNode.find must search both subtrees and each node costs 56 bytes.
```

**Right**

```java
record HeaderName(String value) implements Comparable<HeaderName> {
    @Override public int hashCode() { return 0; }
    @Override public int compareTo(HeaderName o) { return value.compareTo(o.value); }
}
// 1.66 ms for 20,000 keys. compareTo gives the red-black tree a real total
// order, so find() prunes one subtree per level.
```

**Why people believe it:** the Java 8 release notes say tree bins improve worst-case behaviour, and omit the `Comparable` precondition that the source comment states plainly.

---

## Cheat sheet

| Item | Value / fact |
|---|---|
| Chain insert of n colliding keys | `n(n-1)/2` comparisons = Θ(n²) |
| Tree insert of n colliding keys | Θ(n log n) — **only if keys are `Comparable`** |
| n = 10,000 | ~50,000,000 comparisons chained vs ~130,000 treed |
| `TREEIFY_THRESHOLD` | 8 (JDK 21 line 260) |
| `MIN_TREEIFY_CAPACITY` | 64 (line 275) — both must be met |
| JDK 21 `hash()` | `(h = key.hashCode()) ^ (h >>> 16)` (line 336) — no seed |
| Java 7u6 `hash()` | seeded, `String`-only, off by default (`Integer.MAX_VALUE` threshold) |
| `jdk.map.althashing.threshold` | Java 7u6 only; removed in Java 8, absent from JDK 21 |
| Treeification JEP | JEP 180 / JDK-8046170 (not JDK-8023463) |
| CVE | CVE-2011-4858 (Tomcat < 5.5.35 / 6.0.35 / 7.0.23) |
| Advisory | oCERT-2011-003; 28C3, Klink & Wälde, Dec 2011 |
| Tomcat fix | `maxParameterCount` on the `Connector` |
| `"Aa"` / `"BB"` | both hash to 2112; 2^k collisions from k blocks |
| Measured, M4 Pro / JDK 21.0.7, n=20,000 | 382 ms chain, 1.66 ms tree+`Comparable`, 546 ms tree+not-`Comparable` |
| No tree bins in | `Hashtable`, `WeakHashMap`, `IdentityHashMap` |
| Real-world mitigation | Cap parameter count at the boundary |

---

## Self-test

**Q1.** Derive the total comparison count for inserting n keys that all collide, and give the figure for n = 100,000.

<details><summary>Answer</summary>

`putVal` scans the existing bin before appending, so insert *i* costs *i*−1 comparisons. Summing: `0 + 1 + ... + (n−1) = n(n−1)/2`. For n = 100,000 that is `100000 × 99999 / 2 = 4,999,950,000` — about 5 billion comparisons, from a request body of maybe a few hundred kilobytes.

</details>

**Q2.** Why do `"Aa"` and `"BB"` collide, and why does concatenating blocks from `{"Aa","BB"}` preserve the collision?

<details><summary>Answer</summary>

`String.hashCode()` is `s[0]*31^(n-1) + ... + s[n-1]`. `'A'*31 + 'a' = 65*31 + 97 = 2112` and `'B'*31 + 'B' = 66*31 + 66 = 2112`. Because the hash is a polynomial with fixed base 31, the contribution of a two-character block at a given position depends only on that block's own value and the position's power of 31 — identical for both blocks. So swapping any block for the other leaves the sum unchanged, giving 2^k colliding strings from k blocks.

</details>

**Q3.** Java 8 treeifies overloaded bins. Does that make `HashMap` immune to collision DoS?

<details><summary>Answer</summary>

No, on three counts. (1) It bounds the cost at Θ(n log n), which is still superlinear — enough to hurt at large n. (2) The bound requires `Comparable` keys; without them `TreeNode.find` searches both subtrees and the behaviour is Θ(n²) *and* slower than a plain chain (546 ms vs 382 ms at n = 20,000, measured). (3) No treeification happens at all until the table reaches `MIN_TREEIFY_CAPACITY = 64`. The real defence is still an input cap at the boundary.

</details>

**Q4.** Give three concrete reasons Java 7u6's randomised hashing was a weaker answer than treeification.

<details><summary>Answer</summary>

(1) It applied only to `String` keys — the source guard is literally `k instanceof String` — so any other attacker-influenced key type was unprotected. (2) It shipped disabled by default, because a per-map seed makes iteration order vary between runs, which Oracle's own documentation names as the reason for disabling it. (3) It bounded nothing: it made collisions hard to *find* without making a collided bin *fast*, so a leaked or guessed seed restores the full Θ(n²). Bonus: it cost a seed load and a branch on every `hash()` call on every map, plus a private `hash32` field on every `String` instance.

</details>

**Q5.** Java 7's `hash()` had five shifts and four xors; Java 21's has one of each. Why did the hash function get *simpler* while the threat stayed the same?

<details><summary>Answer</summary>

Because the responsibility moved. In Java 7, the hash function was the only thing standing between a bad `hashCode()` and a pathological bin, so it had to aggressively smear bits to *prevent* long bins. With tree bins, a long bin no longer has to be prevented — only survived — so the spread function only needs to fold the high 16 bits down into the index range (`h ^ (h >>> 16)`) and can be as cheap as possible. The JDK 21 class comment states exactly this reasoning above line 336.

</details>

**Q6.** Why is `Hashtable` the correct control in the benchmark rather than, say, a `HashMap` with treeification somehow disabled?

<details><summary>Answer</summary>

Because you cannot disable treeification in `HashMap` — the constants are `static final` and package-private, and there is no system property (the one that existed, `jdk.map.althashing.threshold`, controlled something else and was removed in Java 8 anyway). `Hashtable` is a real, shipping, chain-only hash table: grepping JDK 21's `Hashtable.java` for `TreeNode|treeify` returns 0 matches, because JEP 180 explicitly declined to add tree bins to it, citing legacy iteration-order dependence. It gives a genuine never-treeifies baseline with no reflection hacks.

</details>

**Q7.** An attacker controls JSON object keys hitting your Spring Boot endpoint. Rank your mitigations.

<details><summary>Answer</summary>

First, cap the input at the boundary — a maximum property count / payload size on the deserializer or the container, mirroring what Tomcat's `maxParameterCount` does for form parameters. This is one line, works regardless of the map implementation, and is what every platform actually shipped in 2011/2012. Second, do not promote untrusted keys into a long-lived map at all — validate against a known schema and drop unknown keys. Third, if you must accept arbitrary keys, they will be `String`, which is `Comparable`, so `HashMap`'s tree bins give you the Θ(n log n) safety net for free — but treat it as a net, not a plan. A worst-case-bounded structure like `TreeMap` is available if the input is known-hostile and the O(log n) healthy-path cost is acceptable.

</details>

---

**Leaves covered:** 3.6.35, 3.6.36 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none new — the measured collision curves (D-147) are embedded with the build-it demo in [10-build-my-hash-map-e-set-linked-and-diff.md](10-build-my-hash-map-e-set-linked-and-diff.md); the treeified bin (D-91) and the inheritance chain (D-96) are in [04-internals-d-treeify.md](04-internals-d-treeify.md)
**Target version:** Java 21 LTS
**Lines:** 509
