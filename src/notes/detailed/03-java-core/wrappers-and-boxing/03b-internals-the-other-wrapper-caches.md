# 03 Java Core — The other wrapper caches — INTERNALS (§3.4, 3.4.5, 3.4.6)

**Target version: Java 21 LTS.** | **Part 3 of 5** | [Index](../00-index.md)
Previous: [Cache configuration and the CDS archive](03a-internals-cache-configuration-and-cds.md) · Next: [The boxing bytecode](03c-internals-boxing-bytecode.md)

Two subjects, and the second is a consequence of the first. `Long`, `Byte`, `Short` and `Character` each carry a private holder class that is, line for line, the same twenty lines as `IntegerCache` with the property read deleted; `Boolean` carries no holder class at all. Every place the four differ from each other is forced by the primitive's range, not chosen, and reading the four side by side is the fastest way to see which parts of `IntegerCache` are *cache design* and which parts are *tunability plumbing*. Once that separation is visible, leaf 3.4.6 answers itself: `Long.valueOf` has no tunable upper bound because `LongCache` has no `high` field for a flag to write.

Everything below is measured or quoted. Library source is quoted from **Oracle JDK 21.0.7 (21.0.7+8-LTS-245, macOS aarch64)** `lib/src.zip`; every number is from a run on that JDK with `UseCompressedOops` on (ergonomic) and `ObjectAlignmentInBytes = 8`.

Division of labour with the siblings. [`01b-cache-coverage-and-reference-equality.md`](01b-cache-coverage-and-reference-equality.md) owns the coverage model at BASICS level — which wrapper caches what, the 127-versus-128 identity flip, `==` on wrappers as reference comparison — and this file does not re-derive it. [`03-internals-boxing.md`](03-internals-boxing.md) owns `Integer.valueOf` and `IntegerCache` line by line, and [`03a-internals-cache-configuration-and-cds.md`](03a-internals-cache-configuration-and-cds.md) owns the saved-property path and `CDS.initializeFromArchive`. This file owns the **other five classes as source**: their structural differences, what each difference is for, and where the specification's promise stops.

---

## 1. Five cache classes, one template, four deliberate deviations (3.4.5)

`[SOURCE]` `[NUM]` The picture: take `IntegerCache`, delete the property read, hard-code the bounds, and you have `LongCache`. Do it again with a different element type and you have `ByteCache`, then `ShortCache`. Do it once more and narrow the range to one side of zero and you have `CharacterCache`. `Boolean` is not in the family — it has two named statics and a ternary. So the whole of 3.4.5 is one template plus four deviations, and each deviation is forced by something about the primitive rather than decided by taste.

### Why it exists

JLS 21 §5.1.7 (boxing conversion) requires that boxing an `int`, `short`, `byte` or `char` value in the range −128 to 127, or either `boolean` value, yields a *shared* instance — two boxings of the same such value must be `==`. That is a language-level guarantee, so it cannot be an optimisation the JDK is free to skip: every one of those six wrappers needs a mechanism. The JDK's own comment in `IntegerCache` says so in five words: `// range [-128, 127] must be interned (JLS7 5.1.7)`.

The design question is therefore not *whether* to cache but *what shape* the mechanism takes. A single generic `Cache<T>` shared by all six would need to box its own keys to index a `Map`, which is circular, and would need a `T[]` it could not allocate without a class literal — so the JDK reached for the private-holder-class idiom five times over instead. Copy-paste in `java.lang` looks like sloppiness until you notice that each copy is specialised to a primitive type that generics cannot abstract over. (The holder-class idiom itself, and why the JVM's per-class initialization lock makes it thread-safe with no synchronization in the source, is [`../classes-and-initialization/03-internals-class-loading-and-init.md`](../classes-and-initialization/03-internals-class-loading-and-init.md).)

When to reach for which mental model: use `IntegerCache` as your reference only when you are reasoning about `Integer`. For the other four, the `IntegerCache` model over-promises — it makes you expect a `low`/`high` pair, a property, and a symmetric range, and exactly one of the four has any of those and none of the four has all three.

### The mechanism

`Long`'s holder class and `valueOf`, quoted in full:

```java
private static final class LongCache {
    private LongCache() {}

    @Stable
    static final Long[] cache;
    static Long[] archivedCache;

    static {
        int size = -(-128) + 127 + 1;

        // Load and use the archived cache if it exists
        CDS.initializeFromArchive(LongCache.class);
        if (archivedCache == null || archivedCache.length != size) {
            Long[] c = new Long[size];
            long value = -128;
            for(int i = 0; i < size; i++) {
                c[i] = new Long(value++);
            }
            archivedCache = c;
        }
        cache = archivedCache;
    }
}

public static Long valueOf(long l) {
    final int offset = 128;
    if (l >= -128 && l <= 127) { // will cache
        return LongCache.cache[(int)l + offset];
    }
    return new Long(l);
}
```

Line by line. `private static final class` plus a private constructor makes the holder uninstantiable and inaccessible outside `Long` — it exists only to own a static field and a `<clinit>`. `@Stable` on `cache` is a `jdk.internal.vm.annotation` hint telling the JIT the field is effectively constant after initialization, so a read of `LongCache.cache` can be constant-folded rather than reloaded; the field is `static final` anyway, but `@Stable` extends that treatment to the array's *elements*. `archivedCache` is the one non-`final` field, because CDS writes it from outside Java code. `int size = -(-128) + 127 + 1;` computes 256. `CDS.initializeFromArchive(LongCache.class)` populates `archivedCache` from the archived heap subgraph if there is one. The `if` rebuilds by loop when there is not, or when the archived array is the wrong length. `cache = archivedCache;` publishes whichever array won. And `valueOf` bounds-tests against two literals, indexes with `(int)l + offset`, and falls through to `new Long(l)` for everything else.

`Byte`, where the bounds test has vanished:

```java
private static final class ByteCache {
    private ByteCache() {}

    @Stable
    static final Byte[] cache;
    static Byte[] archivedCache;

    static {
        final int size = -(-128) + 127 + 1;

        // Load and use the archived cache if it exists
        CDS.initializeFromArchive(ByteCache.class);
        if (archivedCache == null || archivedCache.length != size) {
            Byte[] c = new Byte[size];
            byte value = (byte)-128;
            for(int i = 0; i < size; i++) {
                c[i] = new Byte(value++);
            }
            archivedCache = c;
        }
        cache = archivedCache;
    }
}

public static Byte valueOf(byte b) {
    final int offset = 128;
    return ByteCache.cache[(int)b + offset];
}
```

`Short`, whose holder is `LongCache`'s with `Short` substituted, and whose `valueOf` names an intermediate:

```java
private static final class ShortCache {
    private ShortCache() {}

    @Stable
    static final Short[] cache;
    static Short[] archivedCache;

    static {
        int size = -(-128) + 127 + 1;

        // Load and use the archived cache if it exists
        CDS.initializeFromArchive(ShortCache.class);
        if (archivedCache == null || archivedCache.length != size) {
            Short[] c = new Short[size];
            short value = -128;
            for(int i = 0; i < size; i++) {
                c[i] = new Short(value++);
            }
            archivedCache = c;
        }
        cache = archivedCache;
    }
}

public static Short valueOf(short s) {
    final int offset = 128;
    int sAsInt = s;
    if (sAsInt >= -128 && sAsInt <= 127) { // must cache
        return ShortCache.cache[sAsInt + offset];
    }
    return new Short(s);
}
```

`int sAsInt = s;` is a widening primitive conversion written out rather than left implicit, so the comparison and the index arithmetic both happen in `int` with no repeated promotion at each use.

`Character`, one-sided:

```java
private static final class CharacterCache {
    private CharacterCache(){}

    @Stable
    static final Character[] cache;
    static Character[] archivedCache;

    static {
        int size = 127 + 1;

        // Load and use the archived cache if it exists
        CDS.initializeFromArchive(CharacterCache.class);
        if (archivedCache == null || archivedCache.length != size) {
            Character[] c = new Character[size];
            for (int i = 0; i < size; i++) {
                c[i] = new Character((char) i);
            }
            archivedCache = c;
        }
        cache = archivedCache;
    }
}

public static Character valueOf(char c) {
    if (c <= 127) { // must cache
        return CharacterCache.cache[(int)c];
    }
    return new Character(c);
}
```

`Boolean`, which has no holder class:

```java
public static final Boolean TRUE = new Boolean(true);
public static final Boolean FALSE = new Boolean(false);

public static Boolean valueOf(boolean b) {
    return (b ? TRUE : FALSE);
}
```

`Float` and `Double` have no cache of any kind, which is consistent with §5.1.7 requiring nothing for them, and with the fact that no finite set of `double` values is "the small ones" in any useful sense.

The six side by side:

| Wrapper | `size` expression as written | Cached range | Instances | Bounds check in `valueOf` | Index expression | Archive test | Source comment |
|---|---|---|---|---|---|---|---|
| `Integer` | `int size = (high - low) + 1` | `low`..`high`, `low` fixed at −128, `high` ≥ 127 | 256 by default, more if tuned | `i >= IntegerCache.low && i <= IntegerCache.high` | `i + (-IntegerCache.low)` | `size > archivedCache.length` | `// range [-128, 127] must be interned (JLS7 5.1.7)` |
| `Long` | `int size = -(-128) + 127 + 1` | −128..127 | 256 | `l >= -128 && l <= 127` | `(int)l + offset` | `archivedCache.length != size` | `// will cache` |
| `Byte` | `final int size = -(-128) + 127 + 1` | −128..127 (every `byte`) | 256 | **none** | `(int)b + offset` | `archivedCache.length != size` | none — there is no branch to comment |
| `Short` | `int size = -(-128) + 127 + 1` | −128..127 | 256 | `sAsInt >= -128 && sAsInt <= 127` | `sAsInt + offset` | `archivedCache.length != size` | `// must cache` |
| `Character` | `int size = 127 + 1` | 0..127 | 128 | `c <= 127` | `(int)c` | `archivedCache.length != size` | `// must cache` |
| `Boolean` | no array, no holder class | both values | 2 | not applicable | not applicable | no archive subgraph | none |

The four deviations, in order of how much they change the reader's model.

**Deviation 1 — `ByteCache`: no bounds check at all.** `Byte.valueOf` is two lines, and neither is a test. A `byte` is a signed 8-bit two's-complement value, so its entire domain is −128..127 (see [`../primitives-and-conversions/01-basics.md`](../primitives-and-conversions/01-basics.md) for the widths and ranges); a check for "is this `byte` between −128 and 127" is provably always true, and `javac` would compile it to dead code. This is the cleanest example in `java.lang` of a range guarantee coming from the **type** rather than from a test.

The consequence is worth stating precisely, because it is easy to overstate. On this implementation `Byte.valueOf` can never allocate, so `==` on two `Byte` values obtained through `valueOf` or through autoboxing is always true when the values are equal. Measured: one million `Byte.valueOf` calls over the full range allocated **0 bytes** (`getThreadAllocatedBytes`, after warm-up), against 16,000,000 bytes for a million `new Short((short) n)` in the same harness — the box is not merely cheap, it does not happen. But the *specification* promises sharing only for −128..127, and it is a coincidence of `byte`'s width that this happens to be every value. Lean on the specification, not on the coincidence.

The `(int)b + offset` cast matters for a subtler reason than it looks. `b + offset` would already promote `b` to `int` under binary numeric promotion, so the cast changes no arithmetic — it makes the promotion explicit at the point where the result is used as an array index, which must be an `int`. Written without it the line is still legal; written with it the reader can see that the index is computed in `int` and cannot wrap.

**Deviation 2 — `CharacterCache`: one-sided, therefore no offset.** `size = 127 + 1` is 128, not 256. The range is `0..127`. The index is `(int)c` — the code unit itself, with nothing added — because `char` is an **unsigned** 16-bit code unit, so there is no negative half to offset past. The bounds test is the single comparison `c <= 127`; a `c >= 0` half would be dead code for the same reason `Byte`'s check is.

**Pitfall preview, and it is the one that actually bites:** the "plus or minus 128" model learned on `Integer` is simply wrong for `Character`. `Character.valueOf((char) 128)` is not shared, `Character.valueOf((char) -1)` does not compile, and the cache covers ASCII and nothing else — so a code unit from most of the world's scripts misses it. `char` being an unsigned 16-bit UTF-16 code unit rather than "a character" is [`../primitives-and-conversions/01-basics.md`](../primitives-and-conversions/01-basics.md)'s subject.

**Deviation 3 — `LongCache` and `ShortCache`: literal bounds, and the `!=` archive test.** Both write `size = -(-128) + 127 + 1` rather than computing it from fields, and both test the archive with `archivedCache.length != size` where `IntegerCache` tests `size > archivedCache.length`.

`[NUM]` The arithmetic on that odd expression, on the page: `-(-128)` is `128`; `128 + 127` is `255`; `255 + 1` is `256`. It is a compile-time constant expression under JLS §15.29 — all three operands are literals and both operators are constant-folding — so `javac` puts `256` in the class file and no arithmetic happens at runtime. It is written in that shape to mirror the range's endpoints textually: the `-128` and the `127` you can read off the line are the same `-128` and `127` that appear in `valueOf`'s bounds test three methods later. Changing one and forgetting the other would be visible.

**Insight:** the archive-test operators differ because the two classes are asking different questions. `IntegerCache`'s `size` is variable — `high` may have been raised by a property — so the archived array of 256 is *usable* whenever `size` is 256 or less, and the right test is "is the archive big enough", which is `size > archivedCache.length` in the negative. `LongCache`'s `size` is a compile-time constant 256, so any archived array of a different length is not a smaller-but-usable cache, it is a **stale or wrong archive**, and the right test is exact equality. Same idiom, two different correctness conditions, and the operator is the only place the difference is written down. (The archive path itself, including what `-Xshare:off` does to it, is [`03a-internals-cache-configuration-and-cds.md`](03a-internals-cache-configuration-and-cds.md).)

`Short`'s comment is `// must cache` and `Long`'s is `// will cache`, which is not pedantry: §5.1.7 covers `short` and requires the sharing, while `long` is **not** in §5.1.7's list at all, so `LongCache` is a pure optimisation the JDK chose to provide. `Character`'s comment is `// must cache` for the same reason `Short`'s is. Do not build behaviour on `Long`'s cache the way you may build it on `Short`'s — a conforming JVM could drop `LongCache` and stay conforming.

**Deviation 4 — `Boolean`: not a cache.** No holder class, no array, no lazy initialization, no CDS subgraph. Two `public static final Boolean` fields and a ternary. Two values do not need a data structure, an array of two would cost more in indirection than it saves, and `TRUE` and `FALSE` are part of the public API — they must exist as named objects whether or not `valueOf` uses them, so `valueOf` may as well return them.

Corroboration for "no CDS subgraph", from the measured `-Xlog:cds+heap=info` on JDK 21.0.7:

```
[0.009s][info][cds,heap] resolve subgraph java.lang.Integer$IntegerCache
[0.009s][info][cds,heap] resolve subgraph java.lang.Long$LongCache
[0.009s][info][cds,heap] resolve subgraph java.lang.Byte$ByteCache
[0.009s][info][cds,heap] resolve subgraph java.lang.Short$ShortCache
[0.009s][info][cds,heap] resolve subgraph java.lang.Character$CharacterCache
```

Five caches named; **zero** lines matching `Boolean` in the whole log. `Boolean` therefore has no lazy-initialization story: `TRUE` and `FALSE` are built by `Boolean`'s own `<clinit>`, at whatever moment `Boolean` initialises, which on a bare JVM start is during bootstrap.

`[NUM]` The permanent footprint of all six caches, with the arithmetic. Per-object sizes measured on JDK 21.0.7 by allocating a million of each and reading `getThreadAllocatedBytes`: `Short` 16.000, `Character` 16.000, `Boolean` 16.000, `Integer` 16.000, `Long` 24.000 bytes each. A `Byte` is 16 by the same layout rule (12-byte header + 1-byte field = 13, padded to 16) and could not be measured the same way because `Byte.valueOf` never allocates.

| Cache | Instances | Bytes each | Instance bytes | Array bytes (16-byte header + 4 per compressed reference) |
|---|---|---|---|---|
| `IntegerCache` | 256 | 16 | 4,096 | 16 + 256 × 4 = 1,040 |
| `LongCache` | 256 | 24 | 6,144 | 1,040 |
| `ByteCache` | 256 | 16 | 4,096 | 1,040 |
| `ShortCache` | 256 | 16 | 4,096 | 1,040 |
| `CharacterCache` | 128 | 16 | 2,048 | 16 + 128 × 4 = 528 |
| `Boolean` statics | 2 | 16 | 32 | 0 (no array) |

Instances: 256 + 256 + 256 + 256 + 128 + 2 = **1,154 objects**.
Instance bytes: 4,096 + 6,144 + 4,096 + 4,096 + 2,048 + 32 = **20,512 bytes**.
Array bytes: 1,040 + 1,040 + 1,040 + 1,040 + 528 + 0 = **4,688 bytes**.
Total: 20,512 + 4,688 = **25,200 bytes**, about 24.6 KiB, permanently reachable for the life of the process.

The number that surprises people: the five non-`Integer` caches hold 16,416 instance bytes against `IntegerCache`'s 4,096 — **4.0×** as much. `IntegerCache` is the one everybody discusses and the smallest contributor but one.

**Interview:** "Do all the wrappers cache, and over what ranges?" — Six of eight. `Integer`, `Long`, `Short`, `Byte` over −128..127; `Character` over 0..127 only; `Boolean` via two statics rather than a cache. `Float` and `Double` never. `Byte` covers its entire domain so `Byte.valueOf` has no bounds check and cannot allocate. JLS §5.1.7 mandates the sharing for `int`, `short`, `byte`, `char` and `boolean`; `long`'s cache is the JDK's own choice.

### Diagram

No diagram for this concept. The evidence is five source listings and a six-column comparison; the table above *is* the diagram, and a box-and-arrow rendering of five near-identical arrays would hide the differences the table exists to show.

### A concrete example

A probe over all eight wrappers, with the values taken from the domain rather than invented: a `Character` from a `Jurisdiction` country code, a `Short` from a status-code phase digit and from a full status number, a `Byte` from a disposition digit, a `Long` from a `LedgerEntry` id, an `Integer` from a throughput figure, a `Boolean` from `SELF_EXCLUDED`'s `reversibleByOperator` flag, and a `Double`/`Float` from the average stake value.

```java
public class CacheFamilyProbe {

    record Jurisdiction(String country, String subdivision) {}

    static void report(String label, Object a, Object b) {
        System.out.printf("%-46s shared=%-5s %s%n", label, (a == b),
                (a == b) ? "" : "(two instances)");
    }

    public static void main(String[] args) {
        Jurisdiction jurisdiction = new Jurisdiction("GB", "ENG");

        char asciiCode = jurisdiction.country().charAt(0);      // 'G' = 71
        char nonAsciiCode = '\u20ac';                   // euro sign = 8364
        report("Character 'G' (jurisdiction country code)",
                Character.valueOf(asciiCode), Character.valueOf(asciiCode));
        report("Character U+20AC (currency symbol)",
                Character.valueOf(nonAsciiCode), Character.valueOf(nonAsciiCode));

        short phase = 4;                                        // AO-400 phase digit
        short statusNumber = 400;                               // AO-400 numeric part
        report("Short 4 (status phase digit)",
                Short.valueOf(phase), Short.valueOf(phase));
        report("Short 400 (AO-400 numeric part)",
                Short.valueOf(statusNumber), Short.valueOf(statusNumber));

        byte disposition = 9;                                   // 9 = failed or blocked
        report("Byte 9 (disposition digit)",
                Byte.valueOf(disposition), Byte.valueOf(disposition));
        report("Byte -128 (lowest possible byte)",
                Byte.valueOf(Byte.MIN_VALUE), Byte.valueOf(Byte.MIN_VALUE));
        report("Byte 127 (highest possible byte)",
                Byte.valueOf(Byte.MAX_VALUE), Byte.valueOf(Byte.MAX_VALUE));

        long ledgerEntryId = 19_800_000L;                       // one day of ledger entries
        long bonusGrantsPerSecond = 8L;
        report("Long 19800000 (LedgerEntry id)",
                Long.valueOf(ledgerEntryId), Long.valueOf(ledgerEntryId));
        report("Long 8 (bonus grants per second)",
                Long.valueOf(bonusGrantsPerSecond), Long.valueOf(bonusGrantsPerSecond));

        int peakStakesPerSecond = 1200;
        int operatorsOnShift = 40;
        report("Integer 1200 (peak stake reservations/sec)",
                Integer.valueOf(peakStakesPerSecond), Integer.valueOf(peakStakesPerSecond));
        report("Integer 40 (operators on shift)",
                Integer.valueOf(operatorsOnShift), Integer.valueOf(operatorsOnShift));

        boolean reversibleByOperator = false;                    // SELF_EXCLUDED
        report("Boolean false (reversibleByOperator)",
                Boolean.valueOf(reversibleByOperator), Boolean.valueOf(reversibleByOperator));
        report("Boolean.FALSE vs Boolean.valueOf(false)",
                Boolean.FALSE, Boolean.valueOf(false));

        double averageStake = 4.20;
        float averageStakeFloat = 4.20f;
        report("Double 4.20 (average stake value)",
                Double.valueOf(averageStake), Double.valueOf(averageStake));
        report("Float 4.20f (average stake value)",
                Float.valueOf(averageStakeFloat), Float.valueOf(averageStakeFloat));
    }
}
```

Real output, JDK 21.0.7, no flags:

```
Character 'G' (jurisdiction country code)      shared=true
Character U+20AC (currency symbol)             shared=false (two instances)
Short 4 (status phase digit)                   shared=true
Short 400 (AO-400 numeric part)                shared=false (two instances)
Byte 9 (disposition digit)                     shared=true
Byte -128 (lowest possible byte)               shared=true
Byte 127 (highest possible byte)               shared=true
Long 19800000 (LedgerEntry id)                 shared=false (two instances)
Long 8 (bonus grants per second)               shared=true
Integer 1200 (peak stake reservations/sec)     shared=false (two instances)
Integer 40 (operators on shift)                shared=true
Boolean false (reversibleByOperator)           shared=true
Boolean.FALSE vs Boolean.valueOf(false)        shared=true
Double 4.20 (average stake value)              shared=false (two instances)
Float 4.20f (average stake value)              shared=false (two instances)
```

Read the misses: a status *phase* digit is cached and a status *number* is not; a jurisdiction's leading ASCII letter is cached and a currency symbol is not; a small per-second rate is cached and a peak rate is not; a `LedgerEntry` id is never cached. Every miss is a real value the platform handles by the million.

The second listing, cheap and informative — `-Xlog:class+init` filtered to the cache classes. First on a program that does nothing at all:

```
[0.012s][info][class,init] 137 Initializing 'java/lang/Integer$IntegerCache' (0x0000007000036b28)
[0.013s][info][class,init] 173 Initializing 'java/lang/Boolean' (0x0000007000006100)
[0.013s][info][class,init] 176 Initializing 'java/lang/Character$CharacterCache' (0x000000700002e6e0)
```

Then on `CacheFamilyProbe`:

```
[0.013s][info][class,init] 137 Initializing 'java/lang/Integer$IntegerCache' (0x0000007000036b28)
[0.014s][info][class,init] 173 Initializing 'java/lang/Boolean' (0x0000007000006100)
[0.014s][info][class,init] 176 Initializing 'java/lang/Character$CharacterCache' (0x000000700002e6e0)
[0.017s][info][class,init] 315 Initializing 'CacheFamilyProbe'(no method) (0x0000007001000800)
[0.022s][info][class,init] 441 Initializing 'java/lang/Short$ShortCache' (0x0000007000036728)
[0.023s][info][class,init] 442 Initializing 'java/lang/Byte$ByteCache' (0x0000007000034ff8)
[0.023s][info][class,init] 443 Initializing 'java/lang/Long$LongCache' (0x0000007000039a30)
```

**Insight:** the holder-class laziness is real but three of the six are not lazy in practice. `IntegerCache`, `Boolean` and `CharacterCache` initialise during JVM startup — initialization sequence numbers 137, 173 and 176, all before user code — because the bootstrap itself boxes `int`s and `char`s. `ShortCache`, `ByteCache` and `LongCache` do not appear at all until the probe touches them, at sequence numbers 441 to 443, *after* the application class at 315. So on a typical service the "lazy" caches for `Short`, `Byte` and `Long` are built by application code, on the application thread, on first use — which is when their construction cost, and their CDS archive hit or miss, lands.

### The gotcha

Assuming the four integral caches are interchangeable because their ranges look the same. The ranges are identical; the economics are not. `Long`'s cache holds 24-byte instances rather than 16 — measured 24.000 bytes per `Long` against 16.000 per `Integer`, `Short` and `Character` — so it is the most expensive of the four. And `long` is precisely the type your `LedgerEntry` ids, your `RoundId` sequence numbers and your epoch-millisecond timestamps actually use, none of which is ever in −128..127. So `LongCache` is simultaneously the cache that costs the most and the one that helps least on the paths where boxed `Long` volume is highest. That is not an argument for changing it — 6 KiB is nothing — but it is the reason `-XX:AutoBoxCacheMax` cannot rescue a boxed-id path, which is concept 2.

> **Definition.** `Long`, `Byte`, `Short` and `Character` each carry a private `@Stable`-annotated holder class of the same shape as `IntegerCache` with the property read removed and the bounds written as literals — differing only where the primitive's range forces it (`Byte` needs no bounds check, `Character` needs no negative half or offset, and both `Long` and `Short` test the CDS archive for exact length rather than sufficiency) — while `Boolean` has no cache class at all, just the two eagerly-constructed `TRUE` and `FALSE` statics behind a ternary.

---

## 2. `Long.valueOf` has no knob, and the asymmetry is in the source, not the spec (3.4.6)

`[TRAP]` `[RESEARCH]` The picture, in two lines of contrast. `IntegerCache` declares a `low`/`high` field pair and reads a saved VM property to set `high`; `LongCache` declares neither field, and `Long.valueOf` compares against the literals `-128` and `127` written inline. There is no `LongCache.high` for a flag to write, so there is nothing for `-XX:AutoBoxCacheMax` to point at. The absence of the knob is not a policy decision enforced somewhere — it is the absence of a field.

### Why it exists

Be honest about the epistemics here: this is design archaeology, and only half of it is establishable.

What the source establishes, quoted so the asymmetry is visible rather than asserted. `IntegerCache`'s tunable half:

```java
static final int low = -128;
static final int high;
```

and, inside the same class's static initialiser:

```java
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

Two fields, a property read, a floor of 127 via `Math.max` so the property can only *raise* the bound, and a ceiling so the array stays allocatable. Against that, the whole of `Long`'s bounds logic:

```java
public static Long valueOf(long l) {
    final int offset = 128;
    if (l >= -128 && l <= 127) { // will cache
        return LongCache.cache[(int)l + offset];
    }
    return new Long(l);
}
```

No fields, no property, two literals. `LongCache`'s `size` is likewise the constant expression `-(-128) + 127 + 1`, not `(high - low) + 1`. So the asymmetry is structural and complete: `Integer`'s bound is a runtime-initialised field, `Long`'s is a compile-time constant folded into `valueOf`'s bytecode.

The plausible reading — and it is a **reading**, not a documented rationale — is that `int` is the type that loops, collection sizes, indices, counters and identifiers-as-`int` actually box, so it is the one worth a knob, while `long` in boxed form is either a small counter (already covered by the fixed 256) or an identifier or timestamp (so far outside any plausible cache range that no knob would help). A second supporting reading: `long` is not in JLS §5.1.7's mandate at all, so `LongCache` is discretionary, and the JDK does not usually add configuration surface to a discretionary optimisation. **Unverified:** I could not locate a JEP, a JDK bug entry or a `core-libs-dev` thread stating the decision, so both readings stay labelled as readings. See `## Open questions`.

When it matters that you know this: any time someone proposes a JVM flag as the fix for boxing pressure. The flag exists, it works, and it works on exactly one of the eight wrappers.

### The mechanism

`[RESEARCH]` Measured rather than recalled, on JDK 21.0.7. The probe:

```java
public class FlagReachProbe {
    public static void main(String[] args) {
        System.out.println("Integer.valueOf(1000)   == itself : "
                + (Integer.valueOf(1000) == Integer.valueOf(1000)));
        System.out.println("Long.valueOf(1000L)     == itself : "
                + (Long.valueOf(1000L) == Long.valueOf(1000L)));
        System.out.println("Short.valueOf((short)1000) == itself : "
                + (Short.valueOf((short) 1000) == Short.valueOf((short) 1000)));
        System.out.println("Character.valueOf((char)1000) == itself : "
                + (Character.valueOf((char) 1000) == Character.valueOf((char) 1000)));
        System.out.println("Long.valueOf(127L)      == itself : "
                + (Long.valueOf(127L) == Long.valueOf(127L)));
        System.out.println("Long.valueOf(128L)      == itself : "
                + (Long.valueOf(128L) == Long.valueOf(128L)));
    }
}
```

Three runs. No flags:

```
Integer.valueOf(1000)   == itself : false
Long.valueOf(1000L)     == itself : false
Short.valueOf((short)1000) == itself : false
Character.valueOf((char)1000) == itself : false
Long.valueOf(127L)      == itself : true
Long.valueOf(128L)      == itself : false
```

With `-XX:AutoBoxCacheMax=1000`:

```
Integer.valueOf(1000)   == itself : true
Long.valueOf(1000L)     == itself : false
Short.valueOf((short)1000) == itself : false
Character.valueOf((char)1000) == itself : false
Long.valueOf(127L)      == itself : true
Long.valueOf(128L)      == itself : false
```

With `-Djava.lang.Integer.IntegerCache.high=1000`:

```
Integer.valueOf(1000)   == itself : true
Long.valueOf(1000L)     == itself : false
Short.valueOf((short)1000) == itself : false
Character.valueOf((char)1000) == itself : false
Long.valueOf(127L)      == itself : true
Long.valueOf(128L)      == itself : false
```

One line changes across all three runs. `-XX:AutoBoxCacheMax` is a `{C2 product}` flag with default 128 — the measured `-XX:+PrintFlagsFinal` line is `intx AutoBoxCacheMax = 128 {C2 product} {default}` — and the JVM's only use of it is to set the `java.lang.Integer.IntegerCache.high` saved property, which only `IntegerCache` reads. `Long`, `Short` and `Character` never consult a property, so the flag is invisible to them. Note the last two lines: `Long`'s cache is real and its boundary is exactly where the source says, 127 shared and 128 not, in every run.

**Pitfall:** `-XX:AutoBoxCacheMax` raises the `Integer` cache's upper bound and nothing else. Measuring no change for boxed `Long` is not evidence that the flag is broken and not evidence that boxing is innocent — it is the expected result, and the diagnosis to reach for instead is that the values in question are nowhere near any cache's range. Symptom: a team sets the flag, sees allocation profiles unchanged byte for byte, and concludes the profiler was wrong.

### Diagram

No diagram for this concept. The whole argument is two quoted source fragments and one column of measured booleans; the contrast between a field-plus-property and two literals is already the picture.

### A concrete example

The boxed-`LedgerEntry`-id path, measured. QuizStakes writes roughly **19.8M ledger entries per day** (about 7.2B a year) and ids are large — an id near the year mark is around 7.2 billion, past `Integer.MAX_VALUE`, which is why it is a `long`. Every single one misses every cache at every setting of every flag.

```java
import com.sun.management.ThreadMXBean;
import java.lang.management.ManagementFactory;
import java.util.ArrayList;
import java.util.List;

public class LedgerIdAllocationProbe {

    private static final ThreadMXBean THREADS =
            (ThreadMXBean) ManagementFactory.getThreadMXBean();
    private static final int LEDGER_ENTRIES = 1_000_000;
    private static final long FIRST_ID = 7_200_000_000L;

    private static long allocated() {
        return THREADS.getThreadAllocatedBytes(Thread.currentThread().threadId());
    }

    static List<Long> boxedIds() {
        List<Long> ids = new ArrayList<>(LEDGER_ENTRIES);
        for (int i = 0; i < LEDGER_ENTRIES; i++) {
            ids.add(FIRST_ID + i);
        }
        return ids;
    }

    static long[] primitiveIds() {
        long[] ids = new long[LEDGER_ENTRIES];
        for (int i = 0; i < LEDGER_ENTRIES; i++) {
            ids[i] = FIRST_ID + i;
        }
        return ids;
    }

    private static void measure(String label, java.util.function.Supplier<Object> shape) {
        Object warm = shape.get();
        if (warm == null) throw new AssertionError();
        long before = allocated();
        Object held = shape.get();
        long after = allocated();
        long bytes = after - before;
        System.out.printf("%-34s %,14d bytes  %.3f per element  (kept %s)%n",
                label, bytes, bytes / (double) LEDGER_ENTRIES,
                held.getClass().getSimpleName());
    }

    public static void main(String[] args) {
        System.out.println("AutoBoxCacheMax visible effect on Long: "
                + (Long.valueOf(1000L) == Long.valueOf(1000L)));
        measure("List<Long> of ledger ids", LedgerIdAllocationProbe::boxedIds);
        measure("long[] of the same ids", LedgerIdAllocationProbe::primitiveIds);
    }
}
```

No flags:

```
AutoBoxCacheMax visible effect on Long: false
List<Long> of ledger ids               28,000,040 bytes  28.000 per element  (kept ArrayList)
long[] of the same ids                  8,000,016 bytes  8.000 per element  (kept long[])
```

With `-XX:AutoBoxCacheMax=100000`:

```
AutoBoxCacheMax visible effect on Long: false
List<Long> of ledger ids               28,000,040 bytes  28.000 per element  (kept ArrayList)
long[] of the same ids                  8,000,016 bytes  8.000 per element  (kept long[])
```

Byte for byte identical. The flag changes nothing on this shape and cannot: it does not reach `Long`, and even if a `Long` knob existed, raising a cache bound to 100,000 would not cover an id of 7,200,000,000.

The figures decompose exactly, which is what makes them trustworthy rather than suspiciously round. **28.000 bytes per element** = a 4-byte compressed reference in the `ArrayList`'s backing `Object[]` plus a **24-byte `Long`** (12-byte header + 4 bytes padding + 8-byte `long`). **8.000 bytes per element** for `long[]` is the `long` and nothing else. The residue above the per-element totals is 40 bytes — `ArrayList` 24 plus `Object[]` header 16 — and an independently measured `List<Long>` of the same 1,000,000 elements came to 28,000,200 bytes, the same 28.000 per element. **3.5× the memory and 1,000,000 extra objects for the garbage collector to trace**, for a list of identifiers.

The fix is not a flag. It is `long`, a `long[]`, or a `LongStream` — measured elsewhere in this topic: `Arrays.stream(int[]).asLongStream().sum()` allocates **256 bytes total**, independent of array length. The full cost model for boxing is [`01g-the-cost-of-boxing.md`](01g-the-cost-of-boxing.md), and the cases where the boxing genuinely cannot be removed, together with the primitive-specialised escape hatches that shrink them, are [`01h-when-boxing-is-unavoidable.md`](01h-when-boxing-is-unavoidable.md).

### The gotcha

The mirror-image error: concluding that because `Long` has no knob, `Long` has no cache. It has one, fixed at −128..127, 256 instances, and it fires more often than you would guess — on `signum`-style values, on small per-second rates, on retry counts and disposition digits stored as `long`, and on any enum-ish code widened to `long`. Measured on JDK 21.0.7: `Long.valueOf(127L) == Long.valueOf(127L)` is **true** and `Long.valueOf(128L) == Long.valueOf(128L)` is **false**. Which means boxed-`Long` code has exactly the same 127-versus-128 identity cliff as boxed-`Integer` code, and the same rule applies: never compare boxed values with `==`.

**Interview:** "Can you tune the `Long` cache?" — No. `-XX:AutoBoxCacheMax` and `-Djava.lang.Integer.IntegerCache.high` both set the same saved property, which only `IntegerCache` reads; `LongCache` has no `low`/`high` fields and `Long.valueOf` tests the literals `-128` and `127`, folded into its bytecode. Measured: with `-XX:AutoBoxCacheMax=1000`, `Integer.valueOf(1000) == Integer.valueOf(1000)` becomes true while `Long.valueOf(1000L)`, `Short.valueOf((short) 1000)` and `Character.valueOf((char) 1000)` are all unchanged. The follow-up to volunteer: it would not help anyway, because boxed `long`s in production are ids and timestamps, so the fix is `long`, `long[]` or `LongStream`.

> **Definition.** `Long.valueOf`'s cache bounds are the compile-time literals `-128` and `127` inside the method, with no `low`/`high` fields and no property read anywhere in `LongCache`, so `-XX:AutoBoxCacheMax` — which only sets the saved property `java.lang.Integer.IntegerCache.high` that `IntegerCache` alone reads — has no effect on `Long`, `Short` or `Character`, measured.

---

## Pitfalls

### Setting `-XX:AutoBoxCacheMax` expecting it to help boxed `Long` ledger ids

**Wrong**

```java
// the diagnosis: allocation profiler shows Long dominating the ledger write path
// the "fix": -XX:AutoBoxCacheMax=100000 added to the service's JVM args
List<Long> ledgerEntryIds = new ArrayList<>(1_000_000);
for (int i = 0; i < 1_000_000; i++) {
    ledgerEntryIds.add(7_200_000_000L + i);
}
```

Measured on JDK 21.0.7, with and without the flag:

```
AutoBoxCacheMax visible effect on Long: false
List<Long> of ledger ids               28,000,040 bytes  28.000 per element
```

Identical byte for byte in both runs. The team's next move is usually to distrust the profiler.

**Right**

```java
// the ids are long-valued and dense; hold them as longs
long[] ledgerEntryIds = new long[1_000_000];
for (int i = 0; i < 1_000_000; i++) {
    ledgerEntryIds[i] = 7_200_000_000L + i;
}
// and consume them without reboxing
long highestId = java.util.Arrays.stream(ledgerEntryIds).max().orElseThrow();
```

Measured: `8,000,016` bytes, `8.000` per element, against `28,000,040` and `28.000` — 3.5× less memory and 1,000,000 fewer objects to trace. `Arrays.stream(int[]).asLongStream().sum()` allocates a measured **256 bytes total** regardless of length, so the terminal operation is free too.

**Why people believe it:** the flag is real, it is documented in blog posts as "the boxing cache flag", and it demonstrably works — on `Integer`. Nothing in its name mentions `Integer`, and `AutoBox` sounds like a JVM-wide subsystem rather than one property read by one holder class in one wrapper. The flag's own `PrintFlagsFinal` line, `intx AutoBoxCacheMax = 128 {C2 product} {default}`, does not mention `Integer` either.

### Carrying the plus-or-minus-128 model to `Character`

**Wrong**

```java
record Jurisdiction(String country, String subdivision) {}

// dedupe leading code units of jurisdiction codes; "the cache covers -128..127
// so any code unit we see is shared, and == is fine"
static boolean sameLeadingUnit(Jurisdiction a, Jurisdiction b) {
    Character first = a.country().charAt(0);
    Character second = b.country().charAt(0);
    return first == second;                 // reference comparison
}
```

Measured: for `"GB"` against `"GB"` this returns `true` — `'G'` is 71, inside `0..127`. For a jurisdiction or currency label whose leading code unit is non-ASCII it silently returns `false` for equal values:

```
Character 'G' (jurisdiction country code)      shared=true
Character U+20AC (currency symbol)             shared=false (two instances)
```

`Character`'s cache is `0..127`, 128 entries, indexed by `(int)c` with no offset — `size = 127 + 1` in `CharacterCache` and `if (c <= 127)` in `valueOf`. There is no negative half, and `(char) 128` upward is never shared.

**Right**

```java
static boolean sameLeadingUnit(Jurisdiction a, Jurisdiction b) {
    char first = a.country().charAt(0);     // stay primitive
    char second = b.country().charAt(0);
    return first == second;                 // value comparison, no cache involved
}
```

Or, if the values must be boxed because they live in a collection, `first.equals(second)` or `first.charValue() == second.charValue()`. Staying primitive is better: `charAt` already returns a `char`, so the boxing in the wrong version was pure loss.

**Why people believe it:** every tutorial teaches the cache on `Integer`, where the range is symmetric around zero, and "−128 to 127" becomes the remembered fact rather than "the JLS mandates −128 to 127 where the type has values there". `char` is unsigned, so half that range does not exist, and the surviving half stops at ASCII — which means the belief holds for every test the author is likely to write in English and breaks for most of the world's text.

### Relying on `Byte`'s total coverage to justify `==`

**Wrong**

```java
// dispositions: 0 in progress, 1 success, 5 referred, 9 failed or blocked
static boolean sameDisposition(Byte left, Byte right) {
    return left == right;         // "every byte is cached anyway"
}
```

The premise is even true on this JDK. Measured, `Byte.valueOf` allocated **0 bytes** across 1,000,000 calls spanning the whole range, and `Byte.valueOf(Byte.MIN_VALUE) == Byte.valueOf(Byte.MIN_VALUE)` and the same at `MAX_VALUE` are both `true`, because `Byte.valueOf` has no bounds check and unconditionally indexes `ByteCache.cache[(int)b + offset]`. The code works. It works for an implementation reason, and it also breaks the moment a `Byte` arrives from `new Byte((byte) 9)`, from deserialization, or from any path that did not go through `valueOf` — and it silently returns `false` for `null == null`-adjacent mixtures that a value comparison would have caught differently.

**Right**

```java
static boolean sameDisposition(Byte left, Byte right) {
    return java.util.Objects.equals(left, right);   // null-safe value comparison
}

// or, when neither can be null, do not box at all
static boolean sameDisposition(byte left, byte right) {
    return left == right;
}
```

**Why people believe it:** the reasoning is sound as far as it goes — a `byte` cannot be outside −128..127, the cache covers −128..127, so every `byte` is cached — and it is confirmed by every test they run. What it misses is that the guarantee being leaned on is an *implementation fact about `valueOf`*, while JLS §5.1.7 promises sharing only for boxing conversions in −128..127. That happens to be every `byte` value today, and the coincidence is what makes the habit dangerous: it trains `==`-on-wrappers as a reflex, which then gets carried to `Integer`, `Short` and `Long`, where the same code is a bug at 128.

### Assuming `Boolean` has a cache class, or that `Boolean.valueOf` can allocate

**Wrong**

```java
// "warm up the Boolean cache before the hot path", or worse
Restriction selfExcluded = new Restriction(
        RestrictionType.SELF_EXCLUDED, RestrictionSource.CLIENT,
        new Boolean(false));                  // reversibleByOperator
```

There is nothing to warm: `Boolean` has no holder class, no array and no CDS subgraph. The measured `-Xlog:cds+heap=info` output lists archived subgraphs for `Integer$IntegerCache`, `Long$LongCache`, `Byte$ByteCache`, `Short$ShortCache` and `Character$CharacterCache` and **zero** lines matching `Boolean`. And `new Boolean(false)` does what the cache exists to avoid — it allocates a third `Boolean` object that is `==` to neither `TRUE` nor `FALSE`, measured at 16 bytes each over a million calls.

**Right**

```java
Restriction selfExcluded = new Restriction(
        RestrictionType.SELF_EXCLUDED, RestrictionSource.CLIENT,
        false);                               // autoboxes via Boolean.valueOf
```

`Boolean.valueOf(boolean)` is `return (b ? TRUE : FALSE);` — a ternary over two `public static final` statics built by `Boolean`'s `<clinit>`. It cannot allocate, so there is no cache to warm and no bound to tune. Measured: `Boolean.FALSE == Boolean.valueOf(false)` is `true`. The constructor is terminally deprecated for exactly this reason; the deprecation and the compiler warnings it produces are [`01e-valueof-and-the-deprecated-constructors.md`](01e-valueof-and-the-deprecated-constructors.md).

**Why people believe it:** the phrase "wrapper caches" implies uniformity, and five of the six mechanisms genuinely are the same holder class. `Boolean` is the exception, and it is invisible from the outside — `Boolean.valueOf` behaves exactly as a two-entry cache would, so nothing in observable behaviour distinguishes "two statics" from "a `BooleanCache` of length 2". The distinction only shows up in the CDS log, in `<clinit>` timing, and in the fact that there is no knob and no laziness to reason about.

---

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| Wrappers with a cache | `Integer`, `Long`, `Short`, `Byte`, `Character` (holder class each) + `Boolean` (two statics) |
| Wrappers with no cache | `Float`, `Double` — measured `Float.valueOf(1.0f) == itself` is false |
| `Long`/`Short`/`Byte` range | −128..127, 256 instances each |
| `Character` range | **0..127 only**, 128 instances. No negative half |
| `Boolean` | 2 instances, `TRUE` and `FALSE`, no array |
| Total across all six caches | 1,154 objects, 20,512 instance bytes + 4,688 array bytes = **25,200 bytes** |
| Non-`Integer` caches vs `IntegerCache` | 16,416 vs 4,096 instance bytes — **4.0×** more |
| `LongCache` `size` | `int size = -(-128) + 127 + 1` — a constant expression evaluating to 256 |
| `ByteCache` `size` | same expression, declared `final int size` |
| `CharacterCache` `size` | `int size = 127 + 1` = 128 |
| `IntegerCache` `size` | `(high - low) + 1` — the only computed one |
| `Byte.valueOf` bounds check | **none**. Two lines, unconditional array index |
| Why none | a `byte` cannot be outside −128..127, so the check is dead code |
| `Byte.valueOf` allocation | measured **0 bytes** over 1,000,000 calls across the full range |
| `Character.valueOf` check | `if (c <= 127)` — one-sided, `char` is unsigned |
| `Character` index expression | `(int)c` — no offset, the code unit is the index |
| `Long`/`Byte` index expression | `(int)l + offset` / `(int)b + offset`, `offset` a local `final int = 128` |
| `Short` index expression | `sAsInt + offset`, after an explicit `int sAsInt = s;` |
| Archive test, `Integer` | `size > archivedCache.length` — "big enough", because `size` is variable |
| Archive test, other four | `archivedCache.length != size` — exact, because `size` is a constant |
| Source comments | `Long` `// will cache`; `Short` and `Character` `// must cache`; `Byte` none |
| Why `will` vs `must` | JLS §5.1.7 mandates `short`/`char`; `long` is not in the list, so `LongCache` is discretionary |
| `@Stable` | on `cache` in all five holders — JIT hint that the field and its elements are effectively constant |
| `archivedCache` | the only non-`final` field in each holder; CDS writes it from outside Java |
| CDS subgraphs, measured | `Integer`, `Long`, `Byte`, `Short`, `Character`. **Zero** `Boolean` lines |
| Eager vs lazy, measured | `IntegerCache`, `Boolean`, `CharacterCache` initialise during JVM startup (seq 137/173/176) |
| Lazy in practice | `ShortCache`, `ByteCache`, `LongCache` — not initialised until user code touches them (seq 441–443) |
| `-XX:AutoBoxCacheMax` | `intx`, `{C2 product}`, default **128**. Sets the saved `IntegerCache.high` property |
| Its reach, measured | `Integer` only. `Long`, `Short`, `Character` all unchanged at 1000 with the flag at 1000 |
| `-Djava.lang.Integer.IntegerCache.high` | same effect, same single-wrapper reach |
| `Long` cache tunability | **none**. No `low`/`high` fields; `-128` and `127` are literals inside `valueOf` |
| `Long`'s boundary, measured | `Long.valueOf(127L) == itself` true; `128L` false — same cliff as `Integer` |
| `Long` object size | **24 bytes** (12 header + 4 padding + 8 payload), measured 24.000 over 1M |
| `Integer`/`Short`/`Character`/`Boolean` size | **16 bytes** each, measured 16.000 over 1M |
| `List<Long>` of 1M ids | measured **28,000,040** bytes = 28.000 per element (4-byte ref + 24-byte `Long`) |
| `long[]` of the same | measured **8,000,016** bytes = 8.000 per element. **3.5×** less |
| Flag effect on that shape | byte-for-byte identical with `-XX:AutoBoxCacheMax=100000` and without |
| `LongStream` terminal | `Arrays.stream(int[]).asLongStream().sum()` allocates a measured 256 bytes total |
| Ledger reality | ~19.8M entries/day, ids in the billions — every id misses every cache at every flag setting |
| Rule | never `==` on boxed values; `equals`, `Objects.equals`, or stay primitive |

---

## Self-test

**Q1.** Which of the eight wrappers cache, over what ranges, and how many instances does each hold?

<details><summary>Answer</summary>

Six of eight. `Integer`, `Long`, `Short` and `Byte` cache −128..127, 256 instances each. `Character` caches **0..127 only**, 128 instances — `char` is an unsigned 16-bit code unit, so there is no negative half. `Boolean` has two instances, `TRUE` and `FALSE`, but no cache class at all: no holder, no array, no CDS subgraph, just two `public static final Boolean` statics and `valueOf` returning `(b ? TRUE : FALSE)`. `Float` and `Double` have no cache of any kind — measured, `Float.valueOf(1.0f) == Float.valueOf(1.0f)` is false and `Double.valueOf(1.0) == Double.valueOf(1.0)` is false. Only `Integer`'s upper bound is tunable, and only upward: `Math.max(parseInt(propertyValue), 127)` in `IntegerCache`'s static initialiser means the property can raise `high` but never lower it, and `low` is `static final int low = -128;` and cannot move. Total permanent footprint across all six, from the measured per-object sizes: 256 × 16 + 256 × 24 + 256 × 16 + 256 × 16 + 128 × 16 + 2 × 16 = 20,512 instance bytes, plus 4,688 bytes of backing arrays, for 25,200 bytes and 1,154 objects. The mandate behind all of it is JLS §5.1.7, which requires shared instances for boxing conversions of `int`, `short`, `byte` and `char` in −128..127 and for both `boolean` values — note `long` is not in that list, so `LongCache` is the JDK's own optimisation rather than a requirement.

</details>

**Q2.** `Byte.valueOf` has no bounds check. Why, and what can and cannot be concluded from it?

<details><summary>Answer</summary>

The whole method is `final int offset = 128; return ByteCache.cache[(int)b + offset];` — two lines, no branch. A `byte` is a signed 8-bit two's-complement value, so its entire domain is −128..127, and the cache covers −128..127; a test for "is this `byte` in range" is provably always true and `javac` would emit dead code for it. This is the cleanest example in `java.lang` of a range guarantee coming from the type rather than from a runtime test, and the `(int)b` cast is there to make the promotion to `int` explicit at the point where the value is used as an array index rather than to change any arithmetic — `b + offset` would promote anyway. What you can conclude: on this implementation `Byte.valueOf` can never allocate. Measured, one million `Byte.valueOf` calls spanning the whole range allocated **0 bytes** by `getThreadAllocatedBytes`, against 16,000,000 bytes for a million `new Short((short) n)` in the same harness. So equal `Byte` values obtained through `valueOf` or autoboxing are always `==`. What you cannot conclude is that `==` is *safe* on `Byte`: the specification promises sharing only for −128..127, which merely happens to be every `byte` value today, and the guarantee says nothing about a `Byte` produced by `new Byte((byte) 9)` or by deserialization, both of which bypass `valueOf` entirely. Use `Objects.equals` or stay primitive — not least because the `==`-on-`Byte` habit gets carried to `Integer`, where it is a bug at 128.

</details>

**Q3.** `IntegerCache` tests the archived array with `size > archivedCache.length` and the other four test `archivedCache.length != size`. Why the different operators?

<details><summary>Answer</summary>

Because the two classes are asking different correctness questions, and the operator is the only place the difference is recorded. `IntegerCache`'s `size` is `(high - low) + 1` where `high` is set at runtime from the saved property `java.lang.Integer.IntegerCache.high`, so `size` is variable and may be anything from 256 upward. The archived array is always the default 256 entries, and 256 entries are perfectly usable whenever the requested `size` is 256 or less — so the right question is "is the archive big enough", written in the negative as `size > archivedCache.length` guarding a rebuild. `LongCache`, `ByteCache`, `ShortCache` and `CharacterCache` all compute `size` from a compile-time constant expression — `-(-128) + 127 + 1` for the first three, `127 + 1` for `Character` — so `size` can never be anything but 256 or 128. An archived array of some other length is therefore not a smaller-but-serviceable cache; it is a stale or wrong archive, and exact equality is the right test. There is a measured consequence for `Integer` worth adding: with `-XX:AutoBoxCacheMax=1000`, the `cds,heap` log still shows `initialize_from_archived_subgraph java.lang.Integer$IntegerCache`, so the archive *is* consulted, but `size` = 1129 exceeds `archivedCache.length` = 256 and the `if` rebuilds the array by loop anyway. The archive hit is wasted, which is one reason raising the bound has a startup cost as well as a footprint cost.

</details>

**Q4.** Can you tune the `Long` cache? Prove your answer.

<details><summary>Answer</summary>

No, and the reason is structural rather than a policy. `IntegerCache` declares `static final int low = -128;` and `static final int high;` and sets `high` in its static initialiser from `VM.getSavedProperty("java.lang.Integer.IntegerCache.high")`. `LongCache` declares neither field and reads no property; `Long.valueOf` is `if (l >= -128 && l <= 127)` with both bounds as literals, and `LongCache`'s `size` is the constant expression `-(-128) + 127 + 1`. So the bound is folded into `valueOf`'s bytecode at compile time and there is no field for a flag to write. `-XX:AutoBoxCacheMax` — an `intx` `{C2 product}` flag defaulting to 128, per the measured `PrintFlagsFinal` line — works by setting that one saved property, which only `IntegerCache` reads. Measured on JDK 21.0.7, running the same probe three ways: with no flags, `Integer.valueOf(1000) == itself` is false, and so are the `Long`, `Short` and `Character` equivalents. With `-XX:AutoBoxCacheMax=1000`, the `Integer` line flips to **true** and the other three stay false. With `-Djava.lang.Integer.IntegerCache.high=1000`, identical results. Exactly one line moves across all three runs. The practical follow-up: it would not help even if it existed, because boxed `long`s in production are ids and epoch timestamps — QuizStakes writes ~19.8M ledger entries a day with ids in the billions — so no cache of any size covers them, and the fix is `long`, `long[]` or `LongStream`.

</details>

**Q5.** Where does `Character`'s cache stop, and why is there no negative half?

<details><summary>Answer</summary>

It covers `0..127` and stops there. `CharacterCache`'s `size` is `127 + 1` — 128 entries, not 256 — the loop fills it with `new Character((char) i)` for `i` from 0 to 127, `valueOf` tests `if (c <= 127)` with no lower-bound half, and the index expression is `(int)c` with no offset added. There is no negative half because `char` is an **unsigned** 16-bit UTF-16 code unit with domain 0..65535, so the values a symmetric range would cover do not exist, and a `c >= 0` test would be dead code for the same reason `Byte.valueOf`'s bounds check is. Two consequences for a reader who learned the cache on `Integer`. First, the remembered "plus or minus 128" rule is wrong here in both directions: `Character.valueOf((char) -1)` does not even compile, and `(char) 128` upward is not shared — measured, `Character.valueOf((char) 128) == itself` is false. Second, the cache covers ASCII and nothing else, so a code unit from most of the world's scripts misses it: measured, a jurisdiction's leading `'G'` (71) is shared and a currency symbol at U+20AC (8364) is not. Any code that leans on `==` for boxed `Character` therefore works in English tests and silently returns false for equal non-ASCII values in production.

</details>

**Q6.** Why has `Boolean` no cache class, and what does that change about how you reason about it?

<details><summary>Answer</summary>

Because two values do not need a data structure. `Boolean` has `public static final Boolean TRUE = new Boolean(true);` and the matching `FALSE`, and `valueOf` is the single line `return (b ? TRUE : FALSE);`. An array of two would add an indirection and a bounds check to save nothing, and — the decisive point — `TRUE` and `FALSE` are part of the public API, so they must exist as named objects whether or not `valueOf` uses them. Given that, `valueOf` may as well return them, and there is nothing left for a cache to do. Corroborated by measurement: `-Xlog:cds+heap=info` on JDK 21.0.7 lists archived heap subgraphs for `Integer$IntegerCache`, `Long$LongCache`, `Byte$ByteCache`, `Short$ShortCache` and `Character$CharacterCache`, and **zero** lines matching `Boolean`. What it changes: `Boolean` has no lazy-initialisation story at all. The other five are holder classes, so their arrays are built on first touch — measured, `ShortCache`, `ByteCache` and `LongCache` do not initialise until user code reaches them, at initialization sequence numbers 441 to 443, after the application class at 315. `TRUE` and `FALSE` are built by `Boolean`'s own `<clinit>`, which on a bare JVM start happens during bootstrap at sequence 173. So there is no cache to warm, no bound to tune, no archive to hit or miss, and `Boolean.valueOf` cannot allocate — which is one reason `new Boolean(true)`, which *does* allocate a third instance `==` to neither static, is terminally deprecated.

</details>

**Q7.** `LongCache` writes `int size = -(-128) + 127 + 1;`. What does it evaluate to, when, and why is it written that way?

<details><summary>Answer</summary>

It evaluates to 256, at compile time. The arithmetic: `-(-128)` is `128`, `128 + 127` is `255`, `255 + 1` is `256`. Every operand is a literal and every operator is one JLS §15.29 permits in a constant expression, so `javac` folds the whole thing and puts `256` in the class file — no arithmetic happens at runtime, and the same is true of `ByteCache`'s `final int size = -(-128) + 127 + 1;` and `CharacterCache`'s `int size = 127 + 1;`. It is written in that shape rather than as the literal `256` in order to mirror the range's endpoints textually: the `-128` and `127` you can read off the line are the same `-128` and `127` that appear in `valueOf`'s bounds test a few methods later, so changing one and forgetting the other would be visible on the page. Contrast `IntegerCache`, which writes `int size = (high - low) + 1;` — the only one of the five that genuinely computes, because `high` is a runtime-initialised field that the saved property may have raised. That single difference is the whole of the tunability asymmetry: a computed `size` implies a field, a field implies something a flag can write, and `Long`, `Byte`, `Short` and `Character` have none of it.

</details>

**Q8.** A team profiles the ledger write path, sees boxed `Long` dominating allocation, sets `-XX:AutoBoxCacheMax=100000`, measures no change, and concludes the flag is broken. Diagnose it.

<details><summary>Answer</summary>

The flag is not broken; it does not reach `Long`, and it would not have helped if it did. Two separate facts. First, reach: `-XX:AutoBoxCacheMax` sets the saved VM property `java.lang.Integer.IntegerCache.high`, and `IntegerCache` is the only class that reads it. `LongCache` has no `low`/`high` fields at all, and `Long.valueOf` tests the literals `-128` and `127`, folded into its bytecode at compile time. Measured: with the flag at 1000, `Integer.valueOf(1000) == itself` becomes true while `Long.valueOf(1000L)`, `Short.valueOf((short) 1000)` and `Character.valueOf((char) 1000)` are unchanged. Second, and more important, magnitude: QuizStakes writes about 19.8M ledger entries a day, roughly 7.2B a year, so ids run into the billions — well past `Integer.MAX_VALUE`, which is why they are `long` in the first place. No cache bound of any size covers a value of 7,200,000,000, so even a hypothetical `LongCache.high` knob would change nothing on this path. Measured on the real shape: a presized `List<Long>` of 1,000,000 ids starting at 7,200,000,000 allocated **28,000,040 bytes** — 28.000 per element — and the figure was byte-for-byte identical with and without `-XX:AutoBoxCacheMax=100000`. The 28 bytes decompose as a 4-byte compressed reference in the backing `Object[]` plus a 24-byte `Long` (12-byte header + 4 bytes padding + 8-byte payload). The fix is to stop boxing: the identical `long[]` allocated **8,000,016 bytes**, 8.000 per element, 3.5× less memory and a million fewer objects for the collector to trace, and `Arrays.stream(int[]).asLongStream().sum()` allocates a measured 256 bytes total regardless of length. The wrong conclusion to guard against is the second-order one — "the flag did nothing, so boxing was not the problem" — when the profiler was right all along.

</details>

---

## Open questions

- **Unverified:** why `Integer`'s cache upper bound was made configurable and `Long`'s was not. What is established here is entirely structural and comes from the source: `IntegerCache` declares `low` and `high` as fields and reads `VM.getSavedProperty("java.lang.Integer.IntegerCache.high")`, while `LongCache` declares neither and `Long.valueOf` tests literal `-128` and `127`; both are quoted above, and the behavioural consequence is measured across three flag settings. The two plausible readings offered in the text — that `int` is the type loops and collection sizes actually box, and that `long` is not in JLS §5.1.7's mandate so `LongCache` is discretionary and the JDK does not add configuration surface to discretionary optimisations — are inferences from the source and the specification, not documented rationale. I could not locate a JEP, a JDK bug entry or a `core-libs-dev` thread stating the decision. What would settle it: the JDK bug database entry that introduced `AutoBoxCacheMax` and the `java.lang.Integer.IntegerCache.high` property, or the `core-libs-dev` review thread for it. Nothing in this file depends on the answer — the reach of the flag is measured, not inferred.
- **Unverified:** the exact instance size of a `Byte`. It is stated as 16 bytes from the layout rule (12-byte header with `UseCompressedClassPointers` on, plus a 1-byte field, padded to a multiple of `ObjectAlignmentInBytes = 8`), and `Short`, `Character`, `Boolean` and `Integer` were each measured at exactly 16.000 bytes over 1,000,000 allocations by `getThreadAllocatedBytes`, which makes the rule's prediction well corroborated for 13-to-16-byte objects. `Byte` itself could not be measured the same way, because `Byte.valueOf` never allocates and `new Byte(byte)` is terminally deprecated. What would settle it: JOL (`org.openjdk.jol.info.ClassLayout.parseClass(Byte.class)`), which prints the field offsets and the padding directly. The 25,200-byte total in the cheat sheet moves by 2,048 bytes if `Byte` is not 16.
- **Unverified:** whether the `@Stable` annotation on the five `cache` fields measurably changes generated code for a `valueOf` call, as opposed to being redundant with `static final`. The annotation is present in all five holders and its documented purpose is to extend effectively-constant treatment to an array's *elements*, which `static final` alone does not give — but no compilation output was inspected here, and the claim in the text is limited to what the annotation is for. What would settle it: `-XX:+UnlockDiagnosticVMOptions -XX:+PrintCompilation -XX:+PrintInlining` on a hot loop over `Long.valueOf`, or a `-XX:CompileCommand=print` dump comparing the same loop against a hand-built non-`@Stable` cache.

---

**Leaves covered:** 3.4.5, 3.4.6 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 841
