# 03 Java Core — `MyStringBuilder` — BUILD IT (§4.2 (4.2.1–4.2.4))

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [The MyString intern pool and the diff table](01a-mystring-intern-pool-and-diff.md) · Next: [MyStringBuilder cost and the diff table](01c-mystringbuilder-cost-and-diff.md)

---

A `char[]` that is deliberately bigger than the text it holds, plus an `int` saying how much of
it is real. That is the whole of a string builder. `MyString` (file 1) is a `char[]` whose
length *is* the content length, which is why every edit allocates a new one. Flip that single
assumption — let the array be longer than the content — and append becomes "write one slot,
bump a counter", with an occasional reallocation to buy more room.

Everything else here is a consequence of that flip: how much room to buy (§4.2.1), how each
`append` writes into it (§4.2.2), how the seven mutators keep `count` and the array consistent
(§4.2.3), and what the reallocations cost over a million appends (§4.2.4). The measured
comparison against `+`, the `javap` evidence for how Java 21 actually compiles concatenation,
and the honest gap list against the real `java.lang.StringBuilder` — which does the same thing
over a `byte[]` and is faster for reasons you cannot reproduce in user code — are §4.2.5 and
§4.2.6, in [MyStringBuilder cost and the diff table](01c-mystringbuilder-cost-and-diff.md). The
workload throughout: QuizStakes assembles one audit line per stake settlement, 2.8M a day at a
3,400/sec burst.

---

## §4.2.1 The shape: `char[] value`, `int count`, capacity 16, growth `2 * old + 2`

Two fields, one invariant: `0 <= count <= value.length`. Slots `[0, count)` are content;
slots `[count, value.length)` are slack, whatever bytes happen to be there. `length()` returns
`count`; `capacity()` returns `value.length`. **They are different numbers and confusing them
is the single most common builder mistake.**

**Why a default of 16.** The cost curve is asymmetric: 16 unused chars waste 32 bytes once,
while starting at 1 costs four extra reallocations on the way to 16. There is no derivation
behind 16 beyond "small enough not to matter, large enough to skip the noisy early grows".
`new StringBuilder(String seed)` uses `seed.length() + 16` — a seed usually gets appended to.

**Why the growth is `2 * old + 2` and not `2 * old`.** A multiplicative policy on a value that
can be zero never leaves zero. `new StringBuilder(0)` is legal, and `2 * 0 = 0` would loop
forever. The `+ 2` is the additive term that guarantees forward progress from any capacity,
including 0 and 1. In JDK 21 this is not written as a literal doubling — `AbstractStringBuilder`
routes through `ArraysSupport.newLength`, quoted here from
`java.base/java/lang/AbstractStringBuilder.java` in JDK 21.0.7's `src.zip`:

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

Reading it line by line. `value.length` is in **bytes**, not chars — the real builder holds a
`byte[]`. `coder` is `0` for Latin-1 and `1` for UTF-16, so `<< coder` converts a char count to
a byte count and `>> coder` converts back. `growth` is the minimum extra bytes the caller
actually needs. The third argument, `oldLength + (2 << coder)`, is the *preferred* growth:
preferred new length = `oldLength + oldLength + (2 << coder)` = `2 * oldLength + 2` in the
current unit. That is your `2 * old + 2`, expressed as a growth amount rather than a target.
`newLength` then returns the preferred length when it fits under the soft maximum, and falls
back to the minimum when it does not — the soft maximum, its `hugeLength` fallback and the
`OutOfMemoryError` it throws are in §4.2.6, in
[MyStringBuilder cost and the diff table](01c-mystringbuilder-cost-and-diff.md).

**Insight:** the policy is stated as "preferred growth" precisely so `ArraysSupport.newLength`
can clamp it. Writing `(oldCapacity << 1) + 2` directly gives the same number for small arrays
and an int overflow near the top. Yours does the direct form and handles the overflow by hand,
so you can see what the shared helper buys.

The skeleton, complete:

```java
public class MyStringBuilder implements CharSequence {

    private static final int DEFAULT_CAPACITY = 16;

    private char[] value;
    private int count;

    public MyStringBuilder() {
        this.value = new char[DEFAULT_CAPACITY];
        this.count = 0;
    }

    public MyStringBuilder(int capacity) {
        if (capacity < 0) {
            throw new NegativeArraySizeException("capacity " + capacity);
        }
        this.value = new char[capacity];
        this.count = 0;
    }

    public MyStringBuilder(String seed) {
        this.value = new char[seed.length() + DEFAULT_CAPACITY];
        this.count = 0;
        append(seed);
    }

    @Override
    public int length() {
        return count;
    }

    public int capacity() {
        return value.length;
    }

    @Override
    public char charAt(int index) {
        if (index < 0 || index >= count) {
            throw new StringIndexOutOfBoundsException("index " + index + ", length " + count);
        }
        return value[index];
    }

    @Override
    public CharSequence subSequence(int start, int end) {
        if (start < 0 || end > count || start > end) {
            throw new StringIndexOutOfBoundsException(
                    "start " + start + ", end " + end + ", length " + count);
        }
        return new String(value, start, end - start);
    }

    private void ensureCapacityInternal(int minimumCapacity) {
        if (minimumCapacity - value.length > 0) {
            value = java.util.Arrays.copyOf(value, newCapacity(minimumCapacity));
        }
    }

    private int newCapacity(int minCapacity) {
        int preferred = (value.length << 1) + 2;
        if (preferred < 0) {                       // int overflow
            preferred = Integer.MAX_VALUE - 8;
        }
        int chosen = Math.max(preferred, minCapacity);
        if (chosen < 0) {
            throw new OutOfMemoryError("Required length exceeds implementation limit");
        }
        return chosen;
    }
}
```

`minimumCapacity - value.length > 0` rather than `minimumCapacity > value.length` is copied
from the JDK: it is the overflow-conscious form. If `minimumCapacity` has already wrapped
negative, the subtraction wraps back and the comparison still routes into `newCapacity`, where
the negative is caught; the naive comparison would decide no growth was needed and write past
the end.

**Gotcha:** `charAt` guards against `count`, not `value.length`. Slot `count + 1` exists in the
array and reading it would succeed while returning slack. Bounds checks in a builder are
against the logical length, always.

> A string builder is a `char[]` with spare room plus an `int` fill level; capacity is what it
> can hold, length is what it does hold, and growth buys capacity in multiplicative steps.

---

## §4.2.2 The five `append` overloads, and the `null` surprise

Every `append` is the same three steps: work out how many chars are coming, `ensureCapacityInternal(count + that)`, write them at `value[count]`, advance `count`. What differs is
step one and step three.

```java
    public MyStringBuilder append(String str) {
        if (str == null) {
            return appendNull();
        }
        int len = str.length();
        ensureCapacityInternal(count + len);
        str.getChars(0, len, value, count);
        count += len;
        return this;
    }

    public MyStringBuilder append(char c) {
        ensureCapacityInternal(count + 1);
        value[count++] = c;
        return this;
    }

    public MyStringBuilder append(int i) {
        if (i == Integer.MIN_VALUE) {
            return append("-2147483648");
        }
        int size = stringSize(i);
        ensureCapacityInternal(count + size);
        int end = count + size;
        int pos = end;
        boolean negative = i < 0;
        int magnitude = negative ? -i : i;
        do {
            value[--pos] = (char) ('0' + (magnitude % 10));
            magnitude /= 10;
        } while (magnitude != 0);
        if (negative) {
            value[--pos] = '-';
        }
        count = end;
        return this;
    }

    private static int stringSize(int i) {
        int digits = 1;
        int sign = i < 0 ? 1 : 0;
        int magnitude = i < 0 ? -i : i;
        while (magnitude >= 10) {
            magnitude /= 10;
            digits++;
        }
        return digits + sign;
    }

    public MyStringBuilder append(Object obj) {
        if (obj == null) {
            return appendNull();
        }
        return append(obj.toString());
    }

    private MyStringBuilder appendNull() {
        ensureCapacityInternal(count + 4);
        value[count++] = 'n';
        value[count++] = 'u';
        value[count++] = 'l';
        value[count++] = 'l';
        return this;
    }
```

**`append(int)` without an intermediate `String`.** The obvious implementation is
`append(Integer.toString(i))`, which allocates a `String` and its backing array per call, then
copies out of it and drops both. Instead: size the number with `stringSize`, reserve exactly
that, then write digits **backwards from the end** with `magnitude % 10`, which produces them
least-significant-first and lands them in the right slots with no reversal step. Zero
allocation beyond any growth the reserve triggers. `Integer.MIN_VALUE` is special-cased
because `-Integer.MIN_VALUE` is still `Integer.MIN_VALUE` — negating it overflows, so the
`magnitude` trick cannot work and the literal is the honest answer. The real builder does the
same shape via `Integer.stringSize` and `Integer.getChars`, which write straight into the
builder's own array.

**The `null` policy.** `append((String) null)` and `append((Object) null)` both append the four
characters `n`, `u`, `l`, `l`. They do not throw. Nothing in the builder ever dereferences the
argument on the null path — `appendNull` writes literals.

```java
        String missingCoupon = null;
        Object missingVerdict = null;

        MyStringBuilder mine = new MyStringBuilder();
        mine.append("coupon=").append(missingCoupon)
            .append(" verdict=").append(missingVerdict);
```

Real output, Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64:

```console
MyStringBuilder : [coupon=null verdict=null] length=24
StringBuilder   : [coupon=null verdict=null] length=24
identical       : true
append(int)     : [AA-801 ACTIVATED reserved=-42]
MIN_VALUE       : [-2147483648]
```

**Pitfall:** a QuizStakes audit line built with `+` or `append` from a nullable field silently
ships the text `null` into the ledger's description column instead of failing fast. The
symptom is a support ticket six weeks later about `coupon=null` rows. The fix is at the call
site — `Objects.requireNonNullElse(coupon, "NONE")` — never at the builder, because the
builder's behaviour here is specified and other callers rely on it.

**Interview:** "does `append(null)` throw?" The bare literal does not even compile against
`java.lang.StringBuilder`. `javac` 21.0.7: `error: reference to append is ambiguous / both
method append(CharSequence) in StringBuilder and method append(char[]) in StringBuilder match`.
Cast it and the `String`/`CharSequence`/`Object` overloads all append `"null"`, while
`append((char[]) null)` throws `NullPointerException` from `System.arraycopy`. That asymmetry is
the real answer they are fishing for.

> `append` is reserve-then-write-then-advance; the `null` argument is data, not an error, and
> becomes the four-character text `null`.

---

## §4.2.3 The seven mutators, complete

```java
    public void ensureCapacity(int minimumCapacity) {
        if (minimumCapacity > 0) {
            ensureCapacityInternal(minimumCapacity);
        }
    }

    public void trimToSize() {
        if (count < value.length) {
            value = java.util.Arrays.copyOf(value, count);
        }
    }

    public void setLength(int newLength) {
        if (newLength < 0) {
            throw new StringIndexOutOfBoundsException("newLength " + newLength);
        }
        ensureCapacityInternal(newLength);
        if (count < newLength) {
            java.util.Arrays.fill(value, count, newLength, '\u0000');
        }
        count = newLength;
    }

    public MyStringBuilder insert(int offset, String str) {
        if (offset < 0 || offset > count) {
            throw new StringIndexOutOfBoundsException("offset " + offset + ", length " + count);
        }
        String s = (str == null) ? "null" : str;
        int len = s.length();
        if (len == 0) {
            return this;
        }
        ensureCapacityInternal(count + len);
        System.arraycopy(value, offset, value, offset + len, count - offset);
        s.getChars(0, len, value, offset);
        count += len;
        return this;
    }

    public MyStringBuilder delete(int start, int end) {
        if (start < 0 || start > count || start > end) {
            throw new StringIndexOutOfBoundsException(
                    "start " + start + ", end " + end + ", length " + count);
        }
        int cappedEnd = Math.min(end, count);
        int removed = cappedEnd - start;
        if (removed > 0) {
            System.arraycopy(value, cappedEnd, value, start, count - cappedEnd);
            count -= removed;
        }
        return this;
    }

    public MyStringBuilder reverse() {
        boolean hasSurrogates = false;
        int n = count - 1;
        for (int j = (n - 1) >> 1; j >= 0; j--) {
            int k = n - j;
            char cj = value[j];
            char ck = value[k];
            value[j] = ck;
            value[k] = cj;
            if (Character.isSurrogate(cj) || Character.isSurrogate(ck)) {
                hasSurrogates = true;
            }
        }
        if (hasSurrogates) {
            reverseAllValidSurrogatePairs();
        }
        return this;
    }

    private void reverseAllValidSurrogatePairs() {
        for (int i = 0; i < count - 1; i++) {
            char c2 = value[i];
            if (Character.isLowSurrogate(c2)) {
                char c1 = value[i + 1];
                if (Character.isHighSurrogate(c1)) {
                    value[i++] = c1;
                    value[i] = c2;
                }
            }
        }
    }

    public MyStringBuilder reverseNaive() {   // kept only to demonstrate the corruption
        for (int i = 0, j = count - 1; i < j; i++, j--) {
            char tmp = value[i];
            value[i] = value[j];
            value[j] = tmp;
        }
        return this;
    }

    @Override
    public String toString() {
        return new String(value, 0, count);
    }
```

| Method | Throws | Note |
|---|---|---|
| `ensureCapacity(int)` | nothing | non-positive argument is a silent no-op, matching the JDK; never shrinks |
| `trimToSize()` | nothing | reallocates down to exactly `count`; the only way to give slack back |
| `setLength(int)` | `StringIndexOutOfBoundsException` if negative | grows with `\u0000` padding, shrinks by moving `count` only |
| `insert(int, String)` | `StringIndexOutOfBoundsException` if `offset` outside `[0, count]` | `null` becomes `"null"`, consistent with `append` |
| `delete(int, int)` | `StringIndexOutOfBoundsException` if `start` outside `[0, count]` or `start > end` | `end` past `count` is clamped, not an error |
| `reverse()` | nothing | surrogate-pair fix-up pass |
| `toString()` | nothing | copies; the returned `String` is independent of later mutation |

**`insert` is one `arraycopy` plus one write.** The self-overlapping
`System.arraycopy(value, offset, value, offset + len, count - offset)` shifts the tail right;
`arraycopy` behaves as if the source were copied to a temporary first, so overlap is safe. Hand
that loop yourself and, done forwards, it smears the first char across the tail.

**`delete` clamps `end` but not `start`**, matching the JDK: `delete(3, Integer.MAX_VALUE)` is
the idiomatic "truncate from here", while a `start` past the end is a caller bug.

**`setLength` beyond `count` null-pads.** Not spaces — the actual zero character, `\u0000`.

**`reverse` and the surrogate pair.** A non-BMP code point is two `char` values, high surrogate
then low. A plain char-wise reverse reverses those too, producing low-then-high, which is not a
valid pair — the code point is destroyed and the text no longer round-trips through UTF-8. The
real `StringBuilder`'s UTF-16 path calls `StringUTF16.reverse`, which sets a `hasSurrogates`
flag during the swap loop and then calls `reverseAllValidSurrogatePairs` to swap each
low-then-high neighbour back. Your `reverse` is that algorithm, demonstrated on a
`MyStringBuilder` holding `run` followed by U+1F3B2 GAME DIE:

```console
payload      : \uD83C\uDFB2 chars=2 codePoints=1
naive rev    : \uDFB2\uD83Cnur valid=false
fixed rev    : \uD83C\uDFB2nur valid=true
jdk rev      : \uD83C\uDFB2nur matchesMine=true
```

The naive result puts the low surrogate first — `valid=false` from a well-formedness scan. The
fix-up restores the pair and the output is identical to `java.lang.StringBuilder.reverse`. The
rest of the mutator output, same run:

```console
start        : [stake=4.20 bonus=0.42] len=21 cap=37
insert(0,..) : [AA-801 stake=4.20 bonus=0.42] len=28 cap=37
delete(7,18) : [AA-801 bonus=0.42] len=17
insert(999)  : StringIndexOutOfBoundsException: offset 999, length 17
delete(5,2)  : StringIndexOutOfBoundsException: start 5, end 2, length 17
setLength(24): [CLIENT_BONUS_RESERVED\u0000\u0000\u0000] len=24
setLength(6) : [CLIENT] len=6 cap=37
trimToSize   : cap=6
fresh cap    : 16
ensureCap100 : 100
ensureCap4   : 100 (no shrink)
```

Read three things off it. `cap=37` on a 21-char seed is `21 + 16` from the `String` constructor.
`setLength(24)` shows the three padding positions rendered as escape text — the builder really
holds three `\u0000` chars there, and printing them raw would put NUL bytes in your terminal.
`setLength(6)` leaves `cap=37`: shrinking the length never returns memory, only `trimToSize`
does, and it dropped 37 to 6.

> The mutators exist to keep `count` and `value` consistent under edits; every one of them is a
> bounds check, an `arraycopy`, and a `count` adjustment.

---

## §4.2.4 What a million appends actually cost `[PROVE]` `[NUM]`

Start at 16 and apply `2 * old + 2` on demand. A single-char `append` triggers growth exactly
when `count == value.length`, so the number of chars copied by grow number *i* equals the
capacity *before* that grow. The capacities are therefore
16, 34, 70, 142, … each `2 * previous + 2`, and the copy costs are the same sequence one step
behind. Total work is a geometric series, and that is the whole amortisation argument.

![D-131 — MyStringBuilder growth trace for 2 * old + 2](../diagrams/D-131-mystringbuilder-growth.svg)

**D-131** — `MyStringBuilder` growth trace: 16 reallocations to reach 1,000,000 characters.

The harness needs no instrumentation inside the class — `capacity()` is public, so watch it:

```java
        final int n = 1_000_000;
        MyStringBuilder ledgerLine = new MyStringBuilder();
        int grows = 0;
        long charsCopied = 0;
        for (int i = 0; i < n; i++) {
            int before = ledgerLine.capacity();
            ledgerLine.append('x');
            int after = ledgerLine.capacity();
            if (after != before) {
                grows++;
                charsCopied += before;   // grows when count == old cap, so copied == old cap
                System.out.printf("%4d | %7d | %7d | %12d%n", grows, before, after, before);
            }
        }
```

Real output, Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64:

```console
grow | old cap | new cap | chars copied
   1 |      16 |      34 |           16
   2 |      34 |      70 |           34
   3 |      70 |     142 |           70
   4 |     142 |     286 |          142
   5 |     286 |     574 |          286
   6 |     574 |    1150 |          574
   7 |    1150 |    2302 |         1150
   8 |    2302 |    4606 |         2302
   9 |    4606 |    9214 |         4606
  10 |    9214 |   18430 |         9214
  11 |   18430 |   36862 |        18430
  12 |   36862 |   73726 |        36862
  13 |   73726 |  147454 |        73726
  14 |  147454 |  294910 |       147454
  15 |  294910 |  589822 |       294910
  16 |  589822 | 1179646 |       589822

appended chars      : 1000000
reallocations       : 16
final capacity      : 1179646
final length        : 1000000
chars copied total  : 1179598
bytes copied total  : 2359196
copied / n          : 1.1796 n (bound is about 2 n)
end slack (chars)   : 179646
end slack (bytes)   : 359292
after trimToSize    : cap=1000000
```

### The bound, worked through

Let the last grow copy `C` chars, so the capacities copied are `C`, `C/2` (roughly), `C/4`, …
down to 16. Because each capacity is a little over twice the previous, the sum is bounded by
the geometric series

```text
C + C/2 + C/4 + C/8 + [each remaining term at most half the one before] < 2C
```

`C` is at most `n`, because the final grow happens while the content is still shorter than `n`.
So total chars copied is **bounded by about 2n**, independent of how many grows there were. Over
`n` appends that is at most about 2 copies per appended char: **O(1) amortised**, even though
the single append that triggers grow 16 copies 589,822 chars and is emphatically not O(1).

Against the measured numbers: the last grow copied `C = 589,822`, twice that is 1,179,644, and
the measured total is 1,179,598 — under `2C` by 46, the accumulated effect of the `+ 2` terms
making each capacity slightly *more* than double its predecessor, so each earlier term is
slightly less than half the next. Against `n` the ratio is 1,179,598 / 1,000,000 = **1.1796 n**.

**Why 1.1796 and not something near 2.** The `2n` bound is worst case, reached when `n` lands
just past a capacity boundary: grow at 589,822 and stop at 589,823 appends, and you have copied
1,179,598 chars for 589,823 appended — ratio 2.0. Stopping at 1,000,000 is 69% of the way
through the last capacity window, so that 589,822-char copy is amortised over 410,178 more
appends than the worst case allows. The measured ratio therefore sweeps between roughly 1.0 and
2.0 depending on where `n` falls. **The bound is stable; the ratio is not.**

**Insight:** the slack tells the same story from the other side. Capacity 1,179,646 against
1,000,000 used is **179,646 unused slots = 359,292 wasted bytes**, held for as long as the
builder lives. `trimToSize()` reclaims it — the run shows capacity dropping to exactly
1,000,000 — at the cost of one more full copy, so it is worth it only if the builder outlives
the append phase. If the next call is `toString()`, that copies anyway and trimming first is
pure waste.

**Interview:** "why is `StringBuilder.append` O(1) if it sometimes reallocates?" Because the
reallocations are geometrically spaced, so total copy work across `n` appends is bounded by a
constant multiple of `n`. Guide 01 owns amortised analysis as a technique; this is the instance.

At QuizStakes scale: 2.8M settlement audit lines a day at roughly 120 chars each. From the
default 16 that is 3 grows per line, copying 16 + 34 + 70 = 120 chars = 240 bytes, or 672 MB of
pointless copying per day. `new StringBuilder(128)` makes it zero grows.

The implementation is now complete. What it costs against the three alternatives, how Java 21
actually compiles `+`, and the mandatory "Diff vs the real one" table continue in
[MyStringBuilder cost and the diff table](01c-mystringbuilder-cost-and-diff.md) (§4.2.5, §4.2.6).

---

## Pitfalls

### Believing `append(null)` throws

**Wrong**

```java
String coupon = null;   // no coupon supplied on this first deposit

MyStringBuilder wrong = new MyStringBuilder();
try {
    wrong.append("DEP-301 CAPTURED coupon=").append(coupon);
    System.out.println("no throw       : [" + wrong + "] length=" + wrong.length());
} catch (NullPointerException e) {
    System.out.println("threw NPE      : " + e);
}
```

Real output, Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64:

```console
no throw       : [DEP-301 CAPTURED coupon=null] length=28
jdk builder    : [DEP-301 CAPTURED coupon=null] length=28
contains 'null': true
right          : [DEP-301 CAPTURED coupon=NONE]
```

The `catch` never runs. `appendNull` writes the four literal characters `n`, `u`, `l`, `l` and
never dereferences the argument, so the audit line grows by 4 and the ledger's description column
receives the text `null` as if it were data. `java.lang.StringBuilder` does the same thing, to the
same length. Nothing fails, nothing logs, and the row is wrong six weeks before anyone notices.

**Right**

```java
MyStringBuilder right = new MyStringBuilder();
right.append("DEP-301 CAPTURED coupon=")
     .append(Objects.requireNonNullElse(coupon, "NONE"));
```

```console
right          : [DEP-301 CAPTURED coupon=NONE]
```

The fix belongs at the call site, not in the builder. `append`'s `"null"` behaviour is specified
in the javadoc and other callers rely on it; changing it in `MyStringBuilder` would make your
class quietly incompatible with the type it is modelling. Decide the substitute where you know
the domain meaning — `"NONE"` for an absent coupon, and a hard `Objects.requireNonNull` for a
field that genuinely must be present.

**Why people believe it:** every other null-hostile API in `java.lang` throws, and the habit of
expecting `NullPointerException` from a null argument is otherwise well trained. The builder is
the exception because `"null"` is the specified rendering of a null reference throughout Java's
text output — `String.valueOf(null Object)`, `println(null Object)` and `append` all agree. It
also does not help that the bare `note.append(null)` fails at compile time with an ambiguity
error, which readers remember as "it rejects null".

### Believing a char-wise reverse is correct

**Wrong**

```java
for (int i = 0, j = count - 1; i < j; i++, j--) {
    char tmp = value[i]; value[i] = value[j]; value[j] = tmp;
}
```

On `run` followed by U+1F3B2 GAME DIE:

```console
naive rev    : \uDFB2\uD83Cnur valid=false
```

The two surrogates were swapped along with everything else, so the low surrogate now precedes
the high one. That is not a valid pair; the code point is gone, and encoding the result to UTF-8
produces replacement characters rather than round-tripping.

**Right**

Track whether any surrogate was touched during the swap loop, then repair the pairs:

```java
if (hasSurrogates) {
    for (int i = 0; i < count - 1; i++) {
        char c2 = value[i];
        if (Character.isLowSurrogate(c2)) {
            char c1 = value[i + 1];
            if (Character.isHighSurrogate(c1)) {
                value[i++] = c1;
                value[i] = c2;
            }
        }
    }
}
```

```console
fixed rev    : \uD83C\uDFB2nur valid=true
jdk rev      : \uD83C\uDFB2nur matchesMine=true
```

Byte-identical to `java.lang.StringBuilder.reverse`, which does the same thing via
`StringUTF16.reverse`.

**Why people believe it:** two-pointer reverse is the canonical correct answer for an array, and
a `char[]` looks like an array of characters. It is not — it is an array of UTF-16 *code units*,
and one user-visible character can occupy two of them. Every test written with ASCII passes.

### Believing `capacity()` and `length()` are the same thing

**Wrong**

```java
StringBuilder note = new StringBuilder("CLIENT_BONUS_RESERVED");
note.setLength(6);
System.out.println("freed bytes: " + note.capacity());   // expected 6
```

```console
setLength(6) : [CLIENT] len=6 cap=37
```

`length()` is 6 and `capacity()` is still 37. Shrinking the length moves `count` and nothing
else: the array is untouched, no memory is returned, and a long-lived builder that was once
large stays large. The 37 is itself instructive — `21 + 16` from the `String` constructor, not
21.

**Right**

```java
note.setLength(6);
note.trimToSize();          // reallocates down to exactly count
```

```console
trimToSize   : cap=6
```

Only worth doing when the builder outlives the shrink. If the next call is `toString()`, that
copies anyway and trimming first is a wasted allocation.

**Why people believe it:** `String.length()` and its array length really are the same number, so
the mental model carries over from the immutable type where it happens to be true. In a builder
the two diverge by construction — the slack is the entire reason append is cheap. After 1,000,000
appends `MyStringBuilder` reports `length=1000000` against `capacity=1179646`: **179,646 unused
slots, 359,292 bytes.**

---

## Cheat sheet

| Fact | Value |
|---|---|
| Fields | `char[] value`, `int count` (real one: `byte[] value`, `byte coder`, `int count`) |
| Invariant | `0 <= count <= value.length` |
| Default capacity | 16 chars |
| `new MyStringBuilder(String seed)` capacity | `seed.length() + 16` |
| Growth | `2 * old + 2`; the `+ 2` makes capacity 0 grow |
| JDK 21 growth call | `ArraysSupport.newLength(oldLength, growth, oldLength + (2 << coder))` |
| Overflow-safe growth test | `minimumCapacity - value.length > 0`, never `>` |
| Grows to reach 1,000,000 chars from 16 | 16 |
| Capacity sequence | 16, 34, 70, 142, 286, 574, 1150, 2302, 4606, 9214, 18430, 36862, 73726, 147454, 294910, 589822, 1179646 |
| Final capacity / slack | 1,179,646 / 179,646 chars = 359,292 bytes |
| Chars copied / bound | 1,179,598 = 1.1796 n, bound about 2 n |
| Amortised append | O(1); worst single append O(n) |
| `append(int)` | `stringSize` then digits written backwards from the end; no intermediate `String` |
| `Integer.MIN_VALUE` | special-cased as a literal; negating it overflows |
| `append(null)` | `String`, `CharSequence`, `Object` overloads append `"null"`; `char[]` throws NPE; unqualified `null` is ambiguous |
| `setLength(bigger)` pads with | `\u0000` |
| `setLength(smaller)` frees | nothing; only `trimToSize()` does |
| `insert(int, String)` | one self-overlapping `arraycopy` right, then one `getChars` |
| `delete(start, end)` | clamps `end` to `count`; rejects bad `start` |
| `reverse()` | char-wise swap plus surrogate-pair fix-up |
| `charAt` bounds against | `count`, never `value.length` |
| QuizStakes sizing | 120-char audit line from default 16 = 3 grows, 240 bytes copied, 672 MB/day at 2.8M lines |

---

## Self-test

**Q1.** Why does the growth formula add 2 instead of just doubling?

<details><summary>Answer</summary>

Because capacity 0 is reachable and legal — `new StringBuilder(0)` — and `2 * 0 = 0`, so a
purely multiplicative policy would never grow and `ensureCapacity` would spin or fail. The
additive term guarantees strict forward progress from any starting capacity, including 0 and 1.
In JDK 21 it appears as the preferred-growth argument `oldLength + (2 << coder)` handed to
`ArraysSupport.newLength`, which makes the preferred new length `2 * oldLength + 2` in the
current coder's unit.

</details>

**Q2.** Appending 1,000,000 chars one at a time from a default builder: how many reallocations,
and how many characters are copied?

<details><summary>Answer</summary>

16 reallocations, and 1,179,598 characters copied — 2,359,196 bytes at 2 bytes per char. The
capacities are 16, 34, 70, 142, 286, 574, 1150, 2302, 4606, 9214, 18430, 36862, 73726, 147454,
294910, 589822, ending at 1,179,646. Each grow copies the capacity it had before it, so the copy
costs are that same sequence shifted by one. The total is 1.1796 n against a theoretical bound of
about 2 n.

</details>

**Q3.** Why is the measured 1.1796 n comfortably under the 2 n bound rather than at it?

<details><summary>Answer</summary>

Because 2 n is the worst case, hit only when `n` falls just past a capacity boundary. The last
grow copied 589,822 chars; had you stopped at 589,823 appends the ratio would be almost exactly
2.0. Stopping at 1,000,000 spreads that copy over 410,178 extra appends. The measured ratio
sweeps between roughly 1.0 and 2.0 depending on where `n` lands in the current doubling window —
the bound is the stable fact, the ratio is not.

</details>

**Q4.** `note.append(null)` on a `StringBuilder` — what happens?

<details><summary>Answer</summary>

Written exactly like that it does not compile. `javac` 21.0.7 says
`error: reference to append is ambiguous / both method append(CharSequence) in StringBuilder and
method append(char[]) in StringBuilder match` — `null` is applicable to both and neither type is
a subtype of the other. Cast it and the answer splits: `append((String) null)`,
`append((CharSequence) null)` and `append((Object) null)` all append the four characters `null`,
because the null path writes literals and never touches the argument.
`append((char[]) null)` throws `NullPointerException` from inside `System.arraycopy`.

</details>

**Q5.** `note.setLength(6)` on a builder holding 21 characters. What is `capacity()` afterwards,
and what would free the memory?

<details><summary>Answer</summary>

Unchanged. Measured: `len=6 cap=37` — 37 because a `String`-seeded builder starts at
`seed.length() + 16`. `setLength` shrinking only assigns `count`; the array is not touched and no
memory is returned. `trimToSize()` reallocates down to exactly `count`, measured going 37 to 6.
Only worth calling when the builder outlives the shrink — if the next call is `toString()`, that
copies anyway and trimming first is a wasted allocation.

</details>

**Q6.** Why does `reverse` need a second pass over the array?

<details><summary>Answer</summary>

Because a non-BMP code point is two `char` values — a high surrogate then a low surrogate — and a
plain two-pointer reverse reverses them too, leaving low-then-high, which is not a valid pair.
The first pass swaps code units and records whether it ever moved a surrogate; the second pass
runs only if it did, walking the array and swapping each low-then-high neighbour pair back into
order. `java.lang.StringBuilder` does exactly this in `StringUTF16.reverse` via a `hasSurrogates`
flag and `reverseAllValidSurrogatePairs`, and skips the whole question on the Latin-1 path
because a Latin-1 array cannot hold a surrogate.

</details>

**Q7.** Why is the capacity test written `minimumCapacity - value.length > 0` rather than
`minimumCapacity > value.length`, and why does `charAt` bound against `count`?

<details><summary>Answer</summary>

The subtraction form is overflow-conscious, copied from the JDK. If `count + len` has already
wrapped past `Integer.MAX_VALUE` into negative territory, the direct comparison
`minimumCapacity > value.length` is false, `ensureCapacityInternal` decides no growth is needed,
and the subsequent write runs off the end of the array. The subtraction wraps back around, stays
positive, and routes into `newCapacity`, where the negative is detected and turned into an
`OutOfMemoryError`. `charAt` bounds against `count` because slots `[count, value.length)`
physically exist and hold slack — whatever was left there by an earlier longer content, or zeros
from a fresh array. Bounding against `value.length` would return that slack as if it were text.
Bounds checks in a builder are always against the logical length.

</details>

---

## Open questions

- none

---

**Leaves covered:** 4.2.1, 4.2.2, 4.2.3, 4.2.4 (4 leaves)
**Leaves deferred:** 4.2.5 and 4.2.6 — moved to [MyStringBuilder cost and the diff table](01c-mystringbuilder-cost-and-diff.md) by the re-split, not dropped
**Diagrams included:** D-131
**Target version:** Java 21 LTS
**Lines:** 855
