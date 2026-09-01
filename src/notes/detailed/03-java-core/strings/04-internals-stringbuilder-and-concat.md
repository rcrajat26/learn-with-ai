# 03 Java Core — `StringBuilder` internals — INTERNALS (§3.3, 3.3.1–3.3.8)

**Target version: Java 21 LTS.** | **Part 3 of 5** | [Index](../00-index.md)
Previous: [The StringTable, interning and deduplication](03b-internals-stringtable-and-interning.md) · Next: [Indified concatenation](04b-internals-indified-concat.md)

A `StringBuilder` is a `byte[]`, a one-byte encoding flag, and a character count. Every claim below is read off the JDK 21 source of `java.lang.AbstractStringBuilder` and `jdk.internal.util.ArraysSupport` — quoted from `lib/src.zip` of Oracle JDK 21.0.7 (macOS aarch64, `CompactStrings = true`). The running example is `PaymentRun` rendering one line of the nightly bank payout file for a `WithdrawalTransaction`.

---

## The field map (3.3.1)

`StringBuilder` and `StringBuffer` hold no character state of their own. All of it lives on the shared superclass, which is `sealed`:

```java
abstract sealed class AbstractStringBuilder implements Appendable, CharSequence
    permits StringBuilder, StringBuffer {
    byte[] value;
    byte coder;
    boolean maybeLatin1;
    int count;

    private static final byte[] EMPTYVALUE = new byte[0];
```

Line by line: `value` is the storage, bytes not chars. `coder` is the encoding tag — `LATIN1 = 0` or `UTF16 = 1`, the same two constants `String` uses. `maybeLatin1` is a hint, discussed below. `count` is the number of characters currently used, always `<= value.length >> coder`. `EMPTYVALUE` is a shared zero-length array used by the no-arg superclass constructor that exists only so subclasses can be deserialised — a deserialised builder must have a non-null `value` before its fields are read back.

| Field / member | Type | Declared on | What it is for |
|---|---|---|---|
| `value` | `byte[]` | `AbstractStringBuilder` | The buffer. Latin-1: one byte per char. UTF-16: two bytes per char, little-endian pairs. Not `final` — replaced on every growth. |
| `coder` | `byte` | `AbstractStringBuilder` | `0` = Latin-1, `1` = UTF-16. Doubles as the shift amount for byte/char conversion. |
| `maybeLatin1` | `boolean` | `AbstractStringBuilder` | Set true by any method that can *delete* characters from a UTF-16 buffer, meaning the buffer may now be compressible back to Latin-1. |
| `count` | `int` | `AbstractStringBuilder` | Characters in use. `length()` returns it; `capacity()` returns `value.length >> coder`. |
| `EMPTYVALUE` | `static final byte[]` | `AbstractStringBuilder` | Shared empty buffer for the serialization-only constructor. |
| `toStringCache` | `transient String` | `StringBuffer` only | Caches the last `toString()` result; nulled by every mutator. |
| — | — | `StringBuilder` | Adds nothing but constructors, covariant `append` return types, and `toString()`. |

`maybeLatin1` is misread from its name constantly, so read its own javadoc:

```java
    /**
     *  The attribute indicates {@code value} might be compressible to LATIN1 if it is UTF16-encoded.
     *  An inflated byte array becomes compressible only when those non-latin1 chars are deleted.
     *  We simply set this attribute in all methods which may delete chars. Therefore, there are
     *  false positives. Subclasses and String need to handle it properly.
     */
```

It is not "this builder is currently Latin-1" — that is `coder == 0`. It is a *pessimistic* flag meaning "a UTF-16 buffer had characters removed, so a compression attempt might now succeed". `setLength`, `deleteCharAt`, `delete`, `replace` and `reverse` set it unconditionally, hence the admitted false positives. It is consumed in exactly one interesting place, `String`'s package-private builder constructor:

```java
    String(AbstractStringBuilder asb, Void sig) {
        byte[] val = asb.getValue();
        int length = asb.length();
        if (asb.isLatin1()) {
            this.coder = LATIN1;
            this.value = Arrays.copyOfRange(val, 0, length);
        } else {
            // only try to compress val if some characters were deleted.
            if (COMPACT_STRINGS && asb.maybeLatin1) {
                byte[] buf = StringUTF16.compress(val, 0, length);
                if (buf != null) {
                    this.coder = LATIN1;
                    this.value = buf;
                    return;
                }
            }
            this.coder = UTF16;
            this.value = Arrays.copyOfRange(val, 0, length << 1);
        }
    }
```

A Latin-1 builder copies `length` bytes and is done. A UTF-16 builder only pays for a `StringUTF16.compress` scan when `maybeLatin1` is set — the flag exists purely to keep that scan off the common path. If compression succeeds the resulting `String` is Latin-1 even though the builder was UTF-16; if it fails, `length << 1` bytes are copied.

> **Definition.** `AbstractStringBuilder` is a mutable `(byte[] value, byte coder, int count)` triple where capacity is measured in characters and storage in bytes, and `coder` is both the encoding tag and the shift between the two.

---

## `newCapacity` is `2 x old + 2`, not doubling (3.3.2, 3.3.3)

**Mental model.** The buffer is a fixed-length tray of bytes with a fill mark (`count`). An append that fits writes past the mark. An append that does not fit allocates a bigger tray, copies the whole old tray into it, and drops the old one for the collector. The only interesting question is how much bigger — and the answer is not "twice".

**Why it exists.** `String` is immutable, so `line = line + field` allocates a fresh array per field: rendering a 140-character payout row out of five fields copies the prefix five times. A growable buffer replaces per-append copying with per-*growth* copying, and if growth is geometric the copying is amortised away. The pre-1.5 answer was `StringBuffer`, which did the same thing with a lock nobody needed.

**When it matters, and when it does not.** It matters when you know the final size and do not say so: the default capacity is 16 characters, and a `PaymentRun` payout file of 7,000 rows built into a default-constructed builder reallocates 16 times before it is done. It does not matter for a builder whose contents fit in 16 characters — a `StatusCode` render such as `AA-801` never grows at all. It also does not matter for a single append of a large chunk, because that append is sized exactly (see the gotcha).

**How it works.** Two methods, both private. First the check:

```java
    private void ensureCapacityInternal(int minimumCapacity) {
        // overflow-conscious code
        int oldCapacity = value.length >> coder;
        if (minimumCapacity - oldCapacity > 0) {
            value = Arrays.copyOf(value,
                    newCapacity(minimumCapacity) << coder);
        }
    }
```

`value.length >> coder` converts the byte length to a character capacity. The comparison is written as a subtraction so that a `minimumCapacity` that has overflowed to a negative value fails the test in the right direction instead of passing it. `Arrays.copyOf` allocates the new byte array and copies `min(old.length, newLength)` bytes — that is, the whole old buffer, live characters and unused tail alike. `newCapacity(minimumCapacity) << coder` converts back from characters to bytes.

Then the sizing decision:

```java
    private int newCapacity(int minCapacity) {
        int oldLength = value.length;
        int newLength = minCapacity << coder;
        int growth = newLength - oldLength;
        int length = ArraysSupport.newLength(oldLength, growth, oldLength + (2 << coder));
        if (length == Integer.MAX_VALUE) {
            throw new OutOfMemoryError("Required length exceeds implementation limit");
        }
        return length >> coder;
    }
```

Everything here except the return value is in **bytes**. `growth` is the minimum extra bytes needed. The third argument is the *preferred* growth, and it is `oldLength + (2 << coder)` — the old byte length again, plus two characters' worth of bytes. That third argument is where the whole growth policy lives:

```java
    public static final int SOFT_MAX_ARRAY_LENGTH = Integer.MAX_VALUE - 8;

    public static int newLength(int oldLength, int minGrowth, int prefGrowth) {
        int prefLength = oldLength + Math.max(minGrowth, prefGrowth); // might overflow
        if (0 < prefLength && prefLength <= SOFT_MAX_ARRAY_LENGTH) {
            return prefLength;
        } else {
            // put code cold in a separate method
            return hugeLength(oldLength, minGrowth);
        }
    }
```

`newLength` returns `oldLength + max(minGrowth, prefGrowth)`. Substituting the preferred growth: `oldLength + (oldLength + (2 << coder))` = `2 * oldLength + (2 << coder)` bytes. Shift that back to characters and you get **`2 * oldCapacity + 2` characters**, for either coder. `0 < prefLength` is the signed-overflow guard; `hugeLength` handles the cold path.

**Insight:** the third argument to `newLength` is a *growth*, not a length. Reading it as a length is exactly how the "it doubles" folklore starts — `oldLength + 2` as a target length would be linear growth, and appends would be O(n) each.

Working the numbers for the payout line, Latin-1, capacity 16 full, one more character wanted:

- `oldLength = 16` bytes, `coder = 0`, `minCapacity = 17` chars.
- `newLength = 17 << 0 = 17`; `growth = 17 - 16 = 1`; preferred growth `= 16 + (2 << 0) = 18`.
- `newLength(16, 1, 18)` = `16 + max(1, 18)` = `34` bytes, inside `SOFT_MAX_ARRAY_LENGTH`.
- `34 >> 0 = 34` characters. `Arrays.copyOf(value, 34 << 0)` allocates 34 bytes and copies 16.

Same builder after inflation, `coder = 1`, capacity 34 chars = 68 bytes, one more character wanted: `newLength = 35 << 1 = 70`, `growth = 2`, preferred growth `= 68 + (2 << 1) = 72`, so `68 + max(2, 72) = 140` bytes, `140 >> 1 = 70` characters. Still `2 * 34 + 2`. The character-domain sequence from the default is therefore fixed: **16 → 34 → 70 → 142 → 286 → 574 → 1150**, and in closed form `c_k = 18 * 2^k - 2`.

**Pitfall:** believing the capacity doubles. Symptom: a pre-size calculated as a power of two, or a memory estimate off by the accumulated `+ 2`, and a printed `capacity()` of 70 where 64 was expected. Fix: the sequence is `c_k = 18 * 2^k - 2`, so pre-size from the real expected character count with `new StringBuilder(n)` and never reason from powers of two. The growth is still geometric, so the amortised guarantee is unaffected — only your arithmetic is.

Initial capacities, from the constructors: `new StringBuilder()` calls `super(16)`, so 16 characters. `new StringBuilder(String s)` computes `s.length() + 16` — and copies `s.coder()` too, so a builder seeded with a non-Latin-1 `String` starts life at UTF-16 with no inflation ever needed. `new StringBuilder(0)` is legal and gives `byte[0]`; growth from zero is `2 * 0 + 2 = 2` characters, then 6, 14, 30 — the `+ 2` is what stops a zero-capacity buffer from being stuck at zero.

![D-099 — `newCapacity` and the coder shift](../diagrams/D-099-newcapacity-coder-shift.svg)

**D-099** — `newCapacity` and the coder shift. Look at the three frames in order: frame 1 is `byte[16]` at `coder = LATIN1 = 0`, where `value.length >> coder` is 16 characters; frame 2 is the growth `oldLength + (2 << coder)` = 16 + 2 routed through `ArraysSupport.newLength` to 34 bytes, which is still 34 characters; frame 3 is `inflate()` flipping `coder` to `UTF16 = 1`, where the same 34 characters now occupy 68 bytes. The character count on the tray never changes in frame 3 — only the byte length does.

**Code.** A capacity probe over the real payout-line render. `byteLength` reads the private field, so run with `--add-opens java.base/java.lang=ALL-UNNAMED`; everything else is plain Java 21.

```java
record Money(BigDecimal amount, Currency currency) {}

record WithdrawalTransaction(String reference, Money amount, String destinationInstrument) {}

final class PayoutLineProbe {

    private static final Field VALUE = valueField();

    private static Field valueField() {
        try {
            Field f = Class.forName("java.lang.AbstractStringBuilder").getDeclaredField("value");
            f.setAccessible(true);
            return f;
        } catch (ReflectiveOperationException e) {
            throw new ExceptionInInitializerError(e);
        }
    }

    static int byteLength(StringBuilder sb) {
        try {
            return ((byte[]) VALUE.get(sb)).length;
        } catch (IllegalAccessException e) {
            throw new AssertionError("run with --add-opens java.base/java.lang=ALL-UNNAMED", e);
        }
    }

    static void probe(String step, StringBuilder sb) {
        System.out.printf("%-14s length=%-4d capacity=%-4d bytes=%-4d%n",
                step, sb.length(), sb.capacity(), byteLength(sb));
    }

    static String payoutLine(WithdrawalTransaction tx) {
        StringBuilder line = new StringBuilder();
        probe("new", line);                                        // capacity 16, bytes 16
        line.append(tx.reference());                               // "BWD-7714-0000913" is 16 chars
        probe("reference", line);                                  // capacity 16, bytes 16
        line.append('|');                                          // needs 17 -> grow
        probe("separator", line);                                  // capacity 34, bytes 34
        line.append(tx.amount().amount().toPlainString())
            .append('|')
            .append(tx.amount().currency().getCurrencyCode())
            .append('|')
            .append(tx.destinationInstrument());
        probe("full row", line);                                   // capacity 70, bytes 70
        return line.toString();
    }

    public static void main(String[] args) {
        payoutLine(new WithdrawalTransaction(
                "BWD-7714-0000913",
                new Money(new BigDecimal("260.00"), Currency.getInstance("GBP")),
                "GB29NWBK60161331926819"));
    }
}
```

**Gotcha.** `Math.max(minGrowth, prefGrowth)` cuts both ways. Append one 980,000-character block to a default builder and `minGrowth` wins: the buffer becomes exactly 980,000 bytes with **zero** headroom, so the very next `append('\n')` reallocates again — a full 980,000-byte copy for one character. Either pre-size with `new StringBuilder(1_000_000)` or append the small tail first. And at the top end, `hugeLength` clamps to `SOFT_MAX_ARRAY_LENGTH = Integer.MAX_VALUE - 8 = 2,147,483,639` bytes when the preferred length overflows but the minimum still fits, returns the raw `minLength` when even that exceeds the soft cap, and throws `OutOfMemoryError("Required array length <old> + <growth> is too large")` on true overflow. If it hands back exactly `Integer.MAX_VALUE`, `newCapacity` throws `OutOfMemoryError("Required length exceeds implementation limit")`. So the practical character ceiling is 2,147,483,639 at Latin-1 and 1,073,741,819 at UTF-16, and the failure is an `Error`, not an exception you can sensibly catch.

> **Definition.** `newCapacity` grows a builder to `2 * oldCapacity + 2` characters, or to the exact minimum when the requested append is larger than that, subject to a soft array-length cap that turns into `OutOfMemoryError`.

---

## The coder shift: capacity in characters, array in bytes (3.3.4)

**Mental model.** One number, `coder`, does two jobs: it names the encoding and it *is* the exponent relating the two units. Characters `<< coder` gives bytes; bytes `>> coder` gives characters. No diagram of its own — frames 2 and 3 of D-099 above are the picture.

**Why it exists.** Before JDK 9 the buffer was `char[]`, so capacity and array length were the same number and no conversion existed. Compact strings (JEP 254) moved storage to `byte[]` with a per-instance encoding, which split the two units apart. Encoding the ratio as a shift amount rather than a multiplier keeps every conversion a single instruction and lets the same expression serve both coders.

**When it matters, and when it does not.** It matters whenever you reason about memory: `capacity()` is characters, the heap cost is `capacity() << coder` bytes plus the 16-byte array header, and a UTF-16 builder therefore costs twice the bytes for the same reported capacity. It does not matter for correctness of your own code, because every public method on the class is in characters — the shift never leaks out.

**How it works.** Three occurrences, all seen above. `value.length >> coder` in `ensureCapacityInternal` is the current capacity in characters. `newCapacity(minimumCapacity) << coder` is the new byte length to allocate. `2 << coder` inside the preferred growth is "two characters, expressed in bytes": `2 << 0 = 2` and `2 << 1 = 4`. Prove the policy is coder-independent: preferred new byte length is `2 * (C << coder) + (2 << coder)` for a capacity `C`, which factors to `(2 * C + 2) << coder`, and shifting back gives `2 * C + 2` characters regardless of coder. The shift cancels — which is the entire reason it is written as a shift.

`trimToSize()` uses the same arithmetic in the other direction, `Arrays.copyOf(value, count << coder)`, shrinking the array to exactly the live characters.

**Code.** The invariant, asserted rather than described:

```java
static void assertCoderInvariant(StringBuilder line) {
    int bytes = PayoutLineProbe.byteLength(line);
    int capacity = line.capacity();
    int coder = bytes / capacity - 1;                   // 0 for Latin-1, 1 for UTF-16
    if ((capacity << coder) != bytes) {
        throw new IllegalStateException("capacity " + capacity + " bytes " + bytes);
    }
    System.out.printf("coder=%d capacity=%d chars -> %d bytes%n", coder, capacity, bytes);
}
```

**Gotcha.** `capacity()` is not a memory figure. A `PaymentRun` builder reporting `capacity() == 1_179_646` holds either 1.18 MB or 2.36 MB depending on a `byte` field you cannot read from outside the JDK. Never budget heap from `capacity()` without knowing the coder.

> **Definition.** `coder` is simultaneously the encoding tag and the char-to-byte shift, so capacity is `value.length >> coder` and allocation is `capacity << coder`.

---

## Coder inflation (3.3.5)

**Mental model.** The buffer is one-byte-per-character right up until a single character that Latin-1 cannot represent arrives. At that instant the whole buffer — used and unused — is rewritten as two-bytes-per-character. There is no partial and no going back within the builder's life.

**Why it exists.** Compact strings are an optimisation for the 90-plus percent of real strings that are Latin-1. A mutable buffer cannot know in advance which it will be, so it starts optimistic and pays a one-time conversion if it guessed wrong.

**When it matters, and when it does not.** It matters for a payout file that appends client display names from `PersonalDetails`: one client with a non-Latin-1 name doubles the byte cost of the entire row being built, and if that row is a 1-MB accumulated block, doubles a megabyte. It does not matter if you seed the builder from an already-UTF-16 `String`, because `new StringBuilder(String s)` copies `s.coder()` and starts at UTF-16.

**How it works.** Any append that may carry a non-Latin-1 character calls `inflateIfNeededFor`, which calls:

```java
    private void inflate() {
        if (!isLatin1()) {
            return;
        }
        byte[] buf = StringUTF16.newBytesFor(value.length);
        StringLatin1.inflate(value, 0, buf, 0, count);
        this.value = buf;
        this.coder = UTF16;
    }
```

Already UTF-16, return — inflation is idempotent. `StringUTF16.newBytesFor(value.length)` allocates `value.length * 2` bytes: the argument is a *character* count, and the old byte length of a Latin-1 buffer equals its character capacity, so the new buffer has the same capacity in characters and twice the bytes. `StringLatin1.inflate` widens `count` characters, zero-extending each byte into a `<hi=0, lo>` pair — only the live characters are converted, not the unused tail. Then `coder` flips, and every subsequent `>> coder` and `<< coder` in the class silently changes meaning.

On the D-099 builder: capacity 34 characters, 34 bytes. One non-Latin-1 append later: still capacity 34 characters, now 68 bytes. Nothing was appended yet at the moment of the flip — 34 bytes of allocation plus a 34-byte widening loop bought exactly zero extra capacity. Frame 3 of D-099 is this step.

**Code.** `U+0141 LATIN CAPITAL LETTER L WITH STROKE` in a client display name, written as an escape to keep the source ASCII:

```java
static String payoutLineWithName(WithdrawalTransaction tx, String clientDisplayName) {
    StringBuilder line = new StringBuilder();
    line.append(tx.reference()).append('|')
        .append(tx.amount().amount().toPlainString());
    PayoutLineProbe.probe("before name", line);      // capacity 34, bytes 34, coder LATIN1

    line.append('|').append(clientDisplayName);      // "\u0141ukasz Kowalczyk"
    PayoutLineProbe.probe("after name", line);       // capacity 70, bytes 140, coder UTF16

    return line.toString();
}
```

The capacity went 34 to 70 by the ordinary `2 * 34 + 2` rule; the byte length went 34 to 140 because inflation doubled the tray *and then* growth doubled it again. Two allocations and two copies for one append.

**Pitfall:** believing inflation costs "two bytes for the non-Latin-1 character". It costs `capacity` extra bytes for the whole buffer, immediately, plus a widening pass over `count` characters — and it is irreversible for that builder. Symptom: a `PaymentRun` batch whose resident size roughly doubles the day a client with a non-Latin-1 name lands in the file, with no code change. Fix: for text known to be non-Latin-1, seed the builder from a UTF-16 `String` or size it deliberately, and keep large accumulating buffers separate from user-supplied names — build one row per builder and write it out, rather than accumulating 7,000 rows in a buffer that any one name can double. The compression path back to Latin-1 exists only in `String`'s constructor via `maybeLatin1`, never in the builder.

> **Definition.** Inflation is the one-way conversion of a builder's whole `byte[]` from Latin-1 to UTF-16 on the first non-Latin-1 character, preserving character capacity and doubling byte footprint.

---

## The growth arithmetic for a million characters (3.3.7), and `toString()` in a loop (3.3.6)

**Mental model.** The realloc count is a logarithm and the copy total is a geometric series that sums to less than the final buffer. That is the whole amortisation argument, and it is worth deriving once rather than trusting.

**Why it does the work it does.** The `PaymentRun` payout file is 7,000 bank withdrawals a day at roughly a 140-character row: 980,000 characters, near enough the million-character case. Built into a default `StringBuilder`, how many reallocations, and how many bytes copied?

**Derivation.** Capacities are `c_k = 18 * 2^k - 2` (check: `c_0 = 16`, `c_1 = 34`, `c_2 = 70`). Reaching one million characters needs `18 * 2^k - 2 >= 1_000_000`, so `2^k >= 55_555.67`; `2^15 = 32_768` is short and `2^16 = 65_536` clears it. **16 reallocations**, final capacity `18 * 65_536 - 2 = 1_179_646` characters.

Each `Arrays.copyOf` copies the whole old array, so at Latin-1 the total bytes copied is the sum of the capacities it grew *out of*:

`sum(k = 0..15) (18 * 2^k - 2)` = `18 * (2^16 - 1) - 32` = `18 * 65_535 - 32` = **1,179,598 bytes**.

Total bytes *allocated* by growth is the sum of the capacities grown *into*: `sum(k = 1..16) (18 * 2^k - 2)` = `18 * (2^17 - 2) - 32` = `18 * 131_070 - 32` = **2,359,228 bytes**, in 16 arrays, all but the last immediately garbage.

| Realloc # | Old capacity (chars) | New capacity (chars) | Bytes copied (Latin-1) |
|---|---|---|---|
| 1 | 16 | 34 | 16 |
| 2 | 34 | 70 | 34 |
| 3 | 70 | 142 | 70 |
| 4 | 142 | 286 | 142 |
| 5 | 286 | 574 | 286 |
| 6 | 574 | 1,150 | 574 |
| 7 | 1,150 | 2,302 | 1,150 |
| 8 | 2,302 | 4,606 | 2,302 |
| 9 | 4,606 | 9,214 | 4,606 |
| 10 | 9,214 | 18,430 | 9,214 |
| 11 | 18,430 | 36,862 | 18,430 |
| 12 | 36,862 | 73,726 | 36,862 |
| 13 | 73,726 | 147,454 | 73,726 |
| 14 | 147,454 | 294,910 | 147,454 |
| 15 | 294,910 | 589,822 | 294,910 |
| 16 | 589,822 | 1,179,646 | 589,822 |
| **Total** | — | — | **1,179,598** |

**The amortised argument in full.** Copying to reach a final capacity `C` totals the sum of every capacity it grew out of, `c_0` through `c_{n-1}`. Since `c_k + 2 = (c_{k+1} + 2) / 2`, that sum is `(C + 2)/2 + (C + 2)/4` plus the remaining halvings down to `(C + 2)/2^n`, less `2n`, and the halving series is bounded by 1, so the whole sum is bounded above by `C + 2`. The final capacity is itself under `2 * (characters appended) + 2`, so total bytes copied is under `2 * n + 4` — **fewer than 2 bytes copied per character appended**, independent of `n`. That is amortised O(1) per append. Here the realised constant is `1_179_598 / 1_000_000 = 1.18` bytes per character. The cost of the guarantee: any single append can trigger a 589,822-byte copy, so latency is spiky even though throughput is linear — and at UTF-16 every figure above doubles, to 2,359,196 bytes copied. The escape hatch: `new StringBuilder(1_000_000)` gives **0 reallocations and 0 bytes copied**, at the price of over-allocating if the estimate is high. `trimToSize()` reclaims the 179,646-character tail if the builder is long-lived. The cost curve for this is plotted as D-066 in [`02-performance-and-text.md`](02-performance-and-text.md); the arithmetic above is the source of that plot.

**Code.** Both shapes, measured against each other:

```java
static int reallocations(int chars, int initialCapacity) {
    StringBuilder line = new StringBuilder(initialCapacity);
    int growths = 0;
    int seen = line.capacity();
    for (int i = 0; i < chars; i++) {
        line.append('0');
        if (line.capacity() != seen) {
            seen = line.capacity();
            growths++;
        }
    }
    return growths;
}

public static void main(String[] args) {
    System.out.println(reallocations(1_000_000, 16));          // 16
    System.out.println(reallocations(1_000_000, 1_000_000));   // 0
}
```

**The `toString()` trap (3.3.6).** `StringBuilder.toString()` is `new String(this)`, which routes to the `String(AbstractStringBuilder, Void)` constructor quoted earlier — an `Arrays.copyOfRange` of `count` (or `count << 1`) bytes, every single call. It is O(count), not O(1), and it does not shrink or reuse the buffer.

```java
// WRONG: a FundsLedger reconciliation over a day of ledger entries
static String reconcile(List<LedgerEntry> entries) {
    StringBuilder sb = new StringBuilder();
    String rendered = "";
    for (LedgerEntry entry : entries) {
        sb.append(entry.position()).append(',')
          .append(entry.amount().amount().toPlainString()).append('\n');
        rendered = sb.toString();          // O(count) copy, once per row
    }
    return rendered;
}
```

The arithmetic: 19,800,000 ledger entries a day at a ~40-character rendered row. The `toString()` on row `i` copies `40 * i` bytes, so the total is `40 * n * (n + 1) / 2`, about `40 * 1.96e14` = **7.8e15 bytes — 7.8 petabytes copied** — to produce the same output a single `toString()` after the loop produces with 792 MB of copying. The appends were amortised O(1); the `toString()` put the O(n^2) straight back.

**Pitfall:** thinking "I used a `StringBuilder`, so the concatenation is linear". The builder makes *appending* linear; `toString()`, `substring()`, `charAt()`-scans and `length()`-checks that copy do not become free by being called on a builder. Symptom: a reconciliation job whose runtime grows quadratically with the day's `LedgerEntry` count — fine in a test with 1,000 rows, an all-night job at 19.8M. Fix: call `toString()` exactly once, outside the loop; if you need a per-row string, build a per-row builder or write the row straight to a `Writer` and never materialise the whole file. `line.setLength(0)` reuses one builder's buffer across rows without any reallocation, which is the right structure for a payout file.

> **Definition.** Appends amortise to under 2 bytes copied per character because growth is geometric; `toString()` is a fresh O(count) array copy on every call, so calling it per iteration restores quadratic cost.

---

## `StringBuffer`: the same class with locks and a cache (3.3.8)

`StringBuffer` is `final class StringBuffer extends AbstractStringBuilder`, adds no character state, and differs in exactly two ways. Every public method is `synchronized` on the buffer instance, and it carries `private transient String toStringCache`, nulled at the top of every mutator (`toStringCache = null;` is the first statement of each `append` overload):

```java
    public synchronized String toString() {
        if (toStringCache == null) {
            return toStringCache = new String(this, null);
        }
        return new String(toStringCache);
    }
```

First `toString()` after a mutation pays the full `Arrays.copyOfRange`. Repeat calls with no mutation between them return `new String(toStringCache)` — the `String` copy constructor, which since JDK 9 shares the `byte[]` and copies only three fields, so it is O(1). The cache only helps the "mutate once, stringify many" pattern that `StringBuffer`'s API encouraged; `StringBuilder` deliberately has no such field, because an unsynchronised builder cannot cheaply know whether a mutation happened.

| | `AbstractStringBuilder` | `StringBuilder` | `StringBuffer` |
|---|---|---|---|
| Visibility | package-private, `sealed` | `public final` | `public final` |
| Locking | none | none | `synchronized` on every public method |
| `toStringCache` | no | no | yes, `transient`, nulled by every mutator |
| `toString()` cost | — | O(count) copy always | O(count) first call, O(1) while unmutated |
| Since | 1.5 (as the shared superclass) | 1.5 | 1.0 |
| When it is correct | never used directly | all single-threaded building — the default | only a genuinely shared mutable buffer, which is nearly always a design bug |

**Pitfall:** reaching for `StringBuffer` because it is "the thread-safe one". Suppose a settlement worker and a reconciliation worker share one buffer for a `PaymentRun` line. Each `append` is atomic, so nothing corrupts memory — and the output is still wrong, because the two workers' fields interleave into one line and no lock held for the duration of a single `append` can prevent that. Symptom: a payout file with rows containing one transaction's reference and another's `Money` amount, appearing only under load, and untestable single-threaded. Fix: one builder per thread, always `StringBuilder`; if a buffer must genuinely be shared, the critical section is the whole row, so hold your own lock around the sequence and the per-call `synchronized` becomes pure overhead. `StringBuilder` exists because that overhead was the common case.

**Interview:** "when would you use `StringBuffer` in new code?" — Never; the lock is per-call, so it cannot make a multi-append sequence atomic, and a builder that needs sharing needs external synchronisation anyway.

> **Definition.** `StringBuffer` is `StringBuilder`'s locked sibling on the same `AbstractStringBuilder` storage, offering per-call mutual exclusion (which composes into nothing useful) plus a `toString` cache.

The other half of the concatenation story — how the compiler turns `"BWD-" + reference` into bytecode, and why that stopped being a `StringBuilder` in JDK 9 — is [Indified concatenation](04b-internals-indified-concat.md).

---

## Pitfalls

### Believing `StringBuilder` doubles its capacity

**Wrong**

```java
StringBuilder line = new StringBuilder();      // "capacity 16"
for (int i = 0; i < 40; i++) line.append('0');
System.out.println(line.capacity());           // expected 64 (16 -> 32 -> 64); prints 70
```

**Right**

```java
// newCapacity: ArraysSupport.newLength(oldLength, growth, oldLength + (2 << coder))
//            = oldLength + max(growth, oldLength + (2 << coder))
//            = 2 * oldLength + (2 << coder) bytes = 2 * oldCapacity + 2 chars
// 16 -> 34 -> 70 -> 142 -> 286 -> 574 -> 1150,  c_k = 18 * 2^k - 2
System.out.println(new StringBuilder().capacity());   // 16
```

**Why people believe it:** `ArrayList` really does grow by `oldCapacity + (oldCapacity >> 1)` and `HashMap` really does double, so "collections double" generalises; and the `+ 2` is invisible until you print the third capacity.

### Believing coder inflation costs two bytes

**Wrong**

```java
StringBuilder line = new StringBuilder();
line.append("BWD-7714-0000913|260.00");        // capacity 34, 34 bytes
line.append('\u0141');                    // "one char, so +2 bytes"
// actual: inflate() allocates 68 bytes and widens, then growth allocates 140
```

**Right**

```java
// Build the row that can contain non-Latin-1 text in its own builder,
// or seed from a UTF-16 String so the coder is right from the start.
StringBuilder name = new StringBuilder(clientDisplayName);   // copies s.coder()
StringBuilder row = new StringBuilder(160);                  // Latin-1 fields only
```

**Why people believe it:** every *public* method of the class is in characters, so the byte-level cost of the coder flip is genuinely invisible from the API — `capacity()` does not change when `inflate()` runs.

### Believing a `StringBuilder` makes the whole loop linear

**Wrong**

```java
for (LedgerEntry entry : entries) {
    sb.append(render(entry));
    rendered = sb.toString();      // O(count) copy per row -> ~7.8e15 bytes at 19.8M rows
}
```

**Right**

```java
for (LedgerEntry entry : entries) {
    sb.append(render(entry));
}
String rendered = sb.toString();   // one O(count) copy, ~792 MB at 19.8M rows
// or, per row, reuse the buffer with no reallocation at all:
// line.setLength(0); line.append(render(entry)); writer.write(line, 0, line.length());
```

**Why people believe it:** "use a `StringBuilder`" is taught as the fix for quadratic concatenation without the reason, so the builder reads as the guarantee rather than the appends.

### Believing `StringBuffer` is the safe default because it is thread-safe

**Wrong**

```java
StringBuffer shared = new StringBuffer();       // shared by the settlement worker
shared.append(tx.reference());                  //   and the reconciliation worker
shared.append('|');
shared.append(tx.amount().amount().toPlainString());
// each append is atomic; the row is interleaved garbage
```

**Right**

```java
StringBuilder line = new StringBuilder(160);    // one per thread, no lock
line.append(tx.reference()).append('|')
    .append(tx.amount().amount().toPlainString());
// if a buffer must be shared, the critical section is the row, not the append:
// synchronized (rowLock) { line.setLength(0); appendRow(line, tx); writer.write(line.toString()); }
```

**Why people believe it:** "thread-safe" on the javadoc is read as "safe to share", but the guarantee is per-method mutual exclusion, which never composes into an atomic sequence.

---

## Cheat sheet

| Thing | Value / rule |
|---|---|
| Fields | `byte[] value`, `byte coder`, `boolean maybeLatin1`, `int count`, `static final byte[] EMPTYVALUE` |
| `LATIN1` / `UTF16` | `0` / `1`; also the char-to-byte shift |
| `capacity()` | `value.length >> coder` (characters) |
| Allocation | `capacity << coder` bytes + array header |
| Default capacity | 16 |
| `new StringBuilder(String s)` | `s.length() + 16`, and coder copied from `s.coder()` |
| Growth | `2 * oldCapacity + 2` characters, via `newLength(oldLength, growth, oldLength + (2 << coder))` |
| Capacity sequence | 16, 34, 70, 142, 286, 574, 1150; `c_k = 18 * 2^k - 2` |
| Large single append | `max(minGrowth, prefGrowth)` picks the minimum — exact fit, zero headroom |
| Soft cap | `SOFT_MAX_ARRAY_LENGTH = Integer.MAX_VALUE - 8 = 2,147,483,639` bytes, then `OutOfMemoryError` |
| 1,000,000 chars from 16 | 16 reallocations, final capacity 1,179,646, 1,179,598 bytes copied (Latin-1) |
| Amortised copy cost | under 2 bytes copied per character appended; realised 1.18 at 1M |
| `inflate()` | one-way Latin-1 to UTF-16; capacity unchanged, bytes doubled |
| `toString()` | `Arrays.copyOfRange`, O(count), every call, no cache on `StringBuilder` |
| `trimToSize()` | `Arrays.copyOf(value, count << coder)` |
| `StringBuffer` extras | `synchronized` on every public method, `transient String toStringCache` |
| `maybeLatin1` | "a UTF-16 buffer had chars deleted, compression may succeed"; read only by `String(AbstractStringBuilder, Void)` |

---

## Self-test

**Q1.** A `StringBuilder` is at capacity 16, Latin-1, and needs room for a 17th character. Trace `newCapacity` to the returned number.

<details><summary>Answer</summary>

`oldLength = value.length = 16` bytes. `newLength = minCapacity << coder = 17 << 0 = 17`. `growth = 17 - 16 = 1`. Preferred growth `= oldLength + (2 << coder) = 16 + 2 = 18`. `ArraysSupport.newLength(16, 1, 18)` returns `oldLength + Math.max(minGrowth, prefGrowth) = 16 + 18 = 34`, which is positive and under `SOFT_MAX_ARRAY_LENGTH`, so it is returned as-is. `newCapacity` returns `34 >> 0 = 34` characters, and `ensureCapacityInternal` calls `Arrays.copyOf(value, 34 << 0)` — 34 bytes allocated, 16 copied.

</details>

**Q2.** Why is the growth rule `2 * old + 2` rather than exactly `2 * old`, and why does the `+ 2` become `+ 4` in bytes at UTF-16?

<details><summary>Answer</summary>

The `+ 2` makes growth from a zero-length buffer possible: `new StringBuilder(0)` has `value.length == 0`, and `2 * 0` is still 0, so the sequence would never move; with the `+ 2` it goes 0, 2, 6, 14, 30. The preferred growth is written `oldLength + (2 << coder)` in the byte domain, so it is `+ 2` bytes at Latin-1 and `+ 4` bytes at UTF-16 — both of which are two *characters*. Shifting the result back by `coder` yields `2 * oldCapacity + 2` characters for either coder.

</details>

**Q3.** How many reallocations does appending 1,000,000 characters to a default `StringBuilder` cause, and how many bytes are copied?

<details><summary>Answer</summary>

Capacities are `c_k = 18 * 2^k - 2`. `18 * 2^k - 2 >= 1_000_000` first holds at `k = 16` (`2^15 = 32_768` is short of the required 55,555.67; `2^16 = 65_536` clears it), so **16 reallocations**, final capacity `18 * 65_536 - 2 = 1_179_646`. Bytes copied is the sum of the capacities grown out of: `sum(k=0..15) (18 * 2^k - 2) = 18 * 65_535 - 32 = 1_179_598` bytes at Latin-1, double that at UTF-16. Total growth allocation is `18 * 131_070 - 32 = 2_359_228` bytes in 16 arrays. `new StringBuilder(1_000_000)` makes all of it zero.

</details>

**Q4.** A Latin-1 builder at capacity 34 appends one character outside Latin-1. What exactly happens, and what does it cost?

<details><summary>Answer</summary>

`inflateIfNeededFor` calls `inflate()`: `StringUTF16.newBytesFor(value.length)` allocates `34 * 2 = 68` bytes, `StringLatin1.inflate` widens the `count` live characters into `<hi=0, lo>` pairs, `value` is replaced and `coder` becomes `UTF16`. Capacity is still 34 characters — the flip bought no room — so the append then triggers ordinary growth to `2 * 34 + 2 = 70` characters, `70 << 1 = 140` bytes. Two allocations and two copies for one character, and the builder can never return to Latin-1; only `String`'s constructor may compress, and only when `maybeLatin1` is set.

</details>

**Q5.** Appends are amortised O(1), yet this reconciliation loop is quadratic. Why?

```java
for (LedgerEntry entry : entries) { sb.append(render(entry)); rendered = sb.toString(); }
```

<details><summary>Answer</summary>

`toString()` is `new String(this)`, which runs `Arrays.copyOfRange` over `count` bytes (or `count << 1` at UTF-16) on every call — there is no cache on `StringBuilder`. Row `i` copies proportionally to `i`, so the total is `O(n^2)`: at 19.8M `LedgerEntry` rows of ~40 characters that is `40 * n * (n + 1) / 2`, about 7.8e15 bytes, against 792 MB for one `toString()` after the loop. Fix: stringify once, or reuse the buffer per row with `setLength(0)` and write straight to a `Writer`.

</details>

**Q6.** The settlement worker and the reconciliation worker share one `StringBuffer` for a payout row. Is the output correct?

<details><summary>Answer</summary>

No. `synchronized` on each public method makes each `append` atomic, so the buffer's internal state never corrupts, but the two workers' appends interleave and the rendered row mixes one `WithdrawalTransaction`'s reference with another's `Money` amount. Atomicity of the parts is not atomicity of the sequence: the critical section is the whole row. The fix is one `StringBuilder` per thread; if sharing is unavoidable, hold your own lock around the row and the per-call locking is pure overhead. `StringBuffer`'s only other difference is `toStringCache`, which makes repeat `toString()` calls O(1) between mutations.

</details>

---

**Leaves covered:** 3.3.1-3.3.8 (8 leaves)
**Leaves deferred:** none
**Diagrams included:** D-099
**Target version:** Java 21 LTS
**Lines:** 598
