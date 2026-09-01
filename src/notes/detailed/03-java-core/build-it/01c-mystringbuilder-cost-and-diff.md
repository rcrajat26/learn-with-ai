# 03 Java Core — `MyStringBuilder` — cost, indified concat, and the diff against `java.lang.StringBuilder` — BUILD IT (§4.2 (4.2.5, 4.2.6))

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [MyStringBuilder](01b-mystringbuilder.md) · Next: [MyInteger and a boxing cache](02-myinteger-and-generics.md)

---

The implementation is finished — `char[] value`, `int count`, capacity 16, growth `2 * old + 2`,
seven mutators, sixteen reallocations to reach a million characters. All of it is in
[MyStringBuilder](01b-mystringbuilder.md) (§4.2.1–§4.2.4). Two questions are left, and both are
answered by measurement rather than by reading the code: what the thing actually costs against
the three alternatives a QuizStakes audit line could be built with (§4.2.5), and what the real
`java.lang.StringBuilder` does that you cannot reproduce in user code (§4.2.6).

The first answer contains a version trap that has outlived its truth by fifteen years. On Java 21
`+=` inside a loop does **not** compile to a `StringBuilder` per iteration; `javap` says it is one
`invokedynamic` per iteration, and it is still quadratic for a completely different reason. That
is the centre of §4.2.5.

---

## §4.2.5 Four ways to build a line, measured `[NUM]`

**This is not JMH.** No forking, no `Blackhole`, no dead-code-elimination guard beyond a
`volatile String sink`, and the JIT's compilation state is whatever five warm-up rounds left it
as. Relative comparisons within this one run are meaningful; the absolute nanoseconds are not
portable. `../cost-model/02-master-cost-table.md` owns the canonical harness and says the same
thing about itself; guide 06 owns JMH.

The four variants did **not** run at the same `n`, and pretending otherwise would be the whole
lie of this benchmark. Variant 3 is quadratic: at `n = 1,000,000` it would copy
`n(n-1)/2 = 499,999,500,000` chars and never finish inside a note. It ran at `n = 4,000`, and the
comparison is made on per-character cost, not on wall clock.

Each variant is a static method wrapping its loop in a `System.nanoTime()` pair and assigning
the result to `static volatile String sink`. The four loop bodies, which are the only part that
differs:

```java
    MyStringBuilder b = new MyStringBuilder();
    for (int i = 0; i < n; i++) { b.append('x'); }          // 1
    sink = b.toString();

    StringBuilder b = new StringBuilder();
    for (int i = 0; i < n; i++) { b.append('x'); }          // 2
    sink = b.toString();

    String line = "";
    for (int i = 0; i < n; i++) { line += 'x'; }            // 3
    sink = line;

    for (int i = 0; i < repeats; i++) {                     // 4
        line = "AA-" + 801 + " client=" + clientId + " CLIENT_BONUS_RESERVED=" + i;
    }
    sink = line;
```

Five warm-up rounds of all four, then one measured round of each:

```console
NOT JMH: no fork, no Blackhole, volatile sink only.
1 MyStringBuilder.append loop  n= 1,000,000     1.041 ms     1.04 ns/char
2 StringBuilder.append loop    n= 1,000,000     0.823 ms     0.82 ns/char
3 String += in a loop          n=     4,000     0.590 ms   147.53 ns/char
4 one + expression, 6 operands  reps=  200,000     2.996 ms    14.98 ns/line

variant 3 per-char cost is 179x variant 2's at n=4,000
variant 3 chars actually copied = n(n-1)/2 = 7,998,000 for n=4,000
extrapolated to n=1,000,000 that is 499,999,500,000 char copies
```

Three readings.

**Mine is within 27% of the JDK's** (1.04 vs 0.82 ns/char) on a pure `append(char)` loop. That
gap is compact strings and the intrinsics, not algorithm: the real builder wrote 1,000,000
Latin-1 chars as 1,000,000 **bytes** and copied half as much memory as your `char[]` did on
every grow.

**Variant 3's 147.53 ns/char is not a constant.** It is `n = 4,000`'s number. Double `n` and it
roughly doubles, because the per-character cost grows linearly with `n` — that is what quadratic
total cost means. The 179x factor is likewise an artefact of `n = 4,000`; at `n = 40,000` it
would be about ten times larger.

**Variant 4 is not a loop at all**, so its unit is ns per assembled line, not per char. 14.98 ns
for a 6-operand line is the indified-concat path doing one exact-sized allocation.

### The bytecode, and a version trap

Since Java 9 (JEP 280), `javac` compiles a string concatenation *expression* to an
`invokedynamic` against `StringConcatFactory.makeConcatWithConstants`. The bootstrap method
builds a `MethodHandle` chain that computes the exact final length from the arguments, allocates
the result array once, and fills it — no builder, no growth, no intermediate. Before Java 9 the
same expression compiled to a `new StringBuilder()`, one chained `append` per operand, and a
`toString()`. `../strings/04-internals-stringbuilder-and-concat.md` owns that mechanism in full.

The trap is what this does to the old advice. Here is `javap -c -p` on the loop body of
`line += 'x';` under JDK 21.0.7:

```text
  static java.lang.String loopPlus(int);
    Code:
       0: ldc           #7                  // String
       2: astore_1
       3: iconst_0
       4: istore_2
       5: iload_2
       6: iload_0
       7: if_icmpge     23
      10: aload_1
      11: invokedynamic #9,  0              // InvokeDynamic #0:makeConcatWithConstants:(Ljava/lang/String;)Ljava/lang/String;
      16: astore_1
      17: iinc          2, 1
      20: goto          5
      23: aload_1
      24: areturn
```

There is **no `new StringBuilder` in the loop body.** Instruction 11 is one `invokedynamic` per
iteration, taking the accumulated `String` and returning a fresh one. So the widely-repeated
claim that `+` in a loop "compiles to a `StringBuilder` per iteration" is **version-stale on
Java 21** — and the code is still quadratic, for the reason that actually matters: the indy call
allocates a new `String` of length `i + 1` and copies all `i` accumulated chars into it, every
iteration. The compilation strategy changed; the asymptotics did not.

To see the pre-9 shape, ask `javac` for it — `-XDstringConcat=inline` selects the legacy
strategy, and the `StringBuilder` allocation appears inside the loop exactly where the old
advice said it was:

```text
       7: if_icmpge     36
      10: new           #9                  // class java/lang/StringBuilder
      13: dup
      14: invokespecial #11                 // Method java/lang/StringBuilder."<init>":()V
      17: aload_1
      18: invokevirtual #12                 // Method java/lang/StringBuilder.append:(Ljava/lang/String;)Ljava/lang/StringBuilder;
      21: bipush        120                 // 'x'
      23: invokevirtual #16                 // Method java/lang/StringBuilder.append:(C)Ljava/lang/StringBuilder;
      26: invokevirtual #19                 // Method java/lang/StringBuilder.toString:()Ljava/lang/String;
      29: astore_1
```

`new` at 10, inside the loop, discarded at 29 after one `toString`. One builder, one backing
array and one result `String` per iteration.

And variant 4, the single expression with four dynamic operands:

```text
  static java.lang.String oneExpression(java.lang.String, int, java.lang.String, long);
    Code:
       0: iload_1
       1: aload_0
       2: aload_2
       3: lload_3
       4: invokedynamic #13,  0             // InvokeDynamic #1:makeConcatWithConstants:(ILjava/lang/String;Ljava/lang/String;J)Ljava/lang/String;
       9: areturn
```

Four loads and one call. The constant pieces — `"AA-"`, `" client="`, the literal `801` — are
not on the stack at all; they are folded into the bootstrap's recipe string in the constant pool,
which is what "WithConstants" names. Note the descriptor keeps `int` and `long` unboxed: no
`Integer.toString`, no boxing.

**Interview:** "is `+` slower than `StringBuilder`?" In one expression, no — on Java 9+ it is
usually faster, because it sizes the result exactly and allocates once. In a loop, yes,
catastrophically, because each iteration rebuilds the whole accumulated prefix. The rule is not
about the operator, it is about whether the intermediate result is reused.

---

## §4.2.6 Diff vs `java.lang.StringBuilder`

The real builder does not hold a `char[]`. It extends the package-private
`AbstractStringBuilder`, whose fields in JDK 21 are `byte[] value`, `byte coder` and `int count`,
with capacity in chars being `value.length >> coder`. Probing it reflectively:

```console
fresh          : length=0 capacity()=16 byte[].length=16 coder=0 (LATIN1)
12 Latin-1     : length=12 capacity()=16 byte[].length=16 coder=0 (LATIN1)
+ EURO SIGN    : length=13 capacity()=16 byte[].length=32 coder=1 (UTF16)
MyStringBuilder : cap=16 backing bytes=32 (always char[], no coder)
```

Twelve Latin-1 chars occupy 12 of 16 **bytes**. Appending one EURO SIGN — not representable in
Latin-1 — triggers `inflate()`: a new `byte[]` twice the length, `StringLatin1.inflate` widening
every existing char, `coder` set to `UTF16`. Capacity in chars never changed; the byte array
doubled. `MyStringBuilder` starts at 32 bytes for the same 16 chars and stays there, because a
`char[]` has no narrow representation to inflate from. That is the single biggest gap and it is
not reproducible in user code: `StringLatin1`, `StringUTF16` and the `String(byte[], byte)`
package-private constructor `toString()` needs are all inside `java.lang`.

| Axis | `MyStringBuilder` | `java.lang.StringBuilder` (JDK 21) | Why the JDK bothers |
|---|---|---|---|
| Storage | `char[]`, 2 bytes per char always | `byte[]` + `coder`; 1 byte per char while all-Latin-1, inflating to 2 on first non-Latin-1 append | halves footprint and halves bytes copied per grow for the overwhelmingly common ASCII case |
| Growth policy | `(value.length << 1) + 2`, overflow handled by hand | `ArraysSupport.newLength(oldLength, growth, oldLength + (2 << coder))` — same `2 * old + 2` preferred, computed overflow-safely in bytes | one audited overflow-safe helper shared by every growable JDK array |
| Soft maximum | clamps to `Integer.MAX_VALUE - 8` inline | `ArraysSupport.SOFT_MAX_ARRAY_LENGTH = Integer.MAX_VALUE - 8`; `newLength` returns the preferred length if it fits, else falls to `hugeLength`, which returns the soft max when the minimum fits under it, the minimum when it does not, and throws `OutOfMemoryError("Required array length N + M is too large")` when `oldLength + minGrowth` overflows | some JVMs reject arrays a few elements short of `Integer.MAX_VALUE`; the soft max avoids a header-dependent failure |
| At the very limit | `OutOfMemoryError` from the array allocation | `newCapacity` additionally throws `OutOfMemoryError("Required length exceeds implementation limit")` when `newLength` hands back exactly `Integer.MAX_VALUE` | distinguishes "cannot represent this length" from "cannot find this much heap" |
| Class hierarchy | standalone class | `AbstractStringBuilder` shared with `StringBuffer`, which overrides every public method as `synchronized` and is the legacy form kept for source compatibility | one implementation, two thread-safety policies; `StringBuffer` predates `StringBuilder` (added in 1.5) and cannot be removed |
| `arraycopy` | `System.arraycopy` / `Arrays.copyOf` — already an intrinsic when you call it | same calls, plus `StringLatin1`/`StringUTF16` helpers that C2 vectorises, and `@IntrinsicCandidate` compression and inflation loops | bulk char moves become SIMD; this is most of the measured gap |
| `reverse` edge case | surrogate-pair fix-up pass, same algorithm | Latin-1 path skips surrogate handling entirely (a Latin-1 array cannot contain one); UTF-16 path calls `StringUTF16.reverse` | correctness for non-BMP text, at zero cost for the common case |
| Other edge cases | `delete` clamps `end`, `insert` rejects a bad `offset`, `charAt` bounds against `count` | identical policies, plus `appendCodePoint`, `replace`, `deleteCharAt`, `indexOf`, `compareTo`, `chars()`, `codePoints()` | the full `CharSequence` and `Comparable` surface |
| Null policy | `append((String) null)` and `append((Object) null)` append `"null"`; `insert(i, null)` inserts `"null"` | same, **except** `append((char[]) null)` throws `NullPointerException` from `arraycopy`, and the unqualified `append(null)` is a compile-time ambiguity | the `"null"` text is specified in the javadoc; the `char[]` asymmetry is an accident of overload set that is now frozen |
| Thread safety | none, and no documentation claiming otherwise | none, documented explicitly; use `StringBuffer` or confine the builder | unsynchronised is the right default — builders are almost always thread-local |
| Serialization | not `Serializable` | `Serializable`, `serialVersionUID = 4383685877147921099L`, with a custom `writeObject` that writes an `int` count and a `char[]`, not the internal `byte[]`; `StringBuffer` uses `serialPersistentFields` of `value`/`count`/`shared` and `serialVersionUID = 3388685877147921107L` from JDK 1.0.2 | the wire form was fixed before compact strings existed, so JDK 9+ must translate `byte[]`+`coder` back to `char[]` on write |
| Allocation tricks | one `char[]` per grow; `append(int)` writes digits in place with no intermediate `String` | same digit trick via `Integer.stringSize` and `Integer.getChars` writing straight into the builder's array; `toString()` uses a package-private `String` constructor that takes ownership of a freshly built array where possible | avoids one array copy per `toString` that user code cannot avoid |
| `toString()` | `new String(value, 0, count)` — always copies | copies too, but with no coder conversion when the coders already agree | a shared array would break the builder's mutability contract |

**Unverified:** whether older releases wrote the growth literally as `(value.length << 1) + 2` in
`AbstractStringBuilder.newCapacity`. JDK 21.0.7's `src.zip` uses the `ArraysSupport.newLength`
form quoted in §4.2.1 in [MyStringBuilder](01b-mystringbuilder.md); no JDK 8 or 11 source tree
was available in this environment to check the earlier text.

**Interview:** "what would you lose reimplementing `StringBuilder`?" Compact strings, the
vectorised compress/inflate intrinsics, the array-adopting `String` constructor, and the fixed
serial form. Not the algorithm — the algorithm is 200 lines and you can write it.

---

## Pitfalls

### Believing `+` in a loop is fine because the compiler turns it into a `StringBuilder`

**Wrong**

```java
String auditLine = "";
for (int i = 0; i < settlementCount; i++) {
    auditLine += reservations[i].statusCode();   // one fresh String per iteration
}
```

At `n = 4,000` this measured **147.53 ns per character**, against 0.82 ns/char for
`StringBuilder.append`, and it copied `n(n-1)/2 = 7,998,000` characters to produce 4,000. On
Java 21 `javap -c -p` shows the loop body is a single `invokedynamic` to
`makeConcatWithConstants` — no `StringBuilder` at all — and it is still quadratic, because each
call allocates a `String` of the new length and copies the whole accumulated prefix.

**Right**

```java
StringBuilder auditLine = new StringBuilder(settlementCount * 8);
for (int i = 0; i < settlementCount; i++) {
    auditLine.append(reservations[i].statusCode());
}
```

One buffer, reused, pre-sized so there are no grows at all. 0.82 ns/char, flat in `n`.

**Why people believe it:** the claim was true and reassuring before Java 9, and the pre-9
compilation really did produce a `StringBuilder` — `javac -XDstringConcat=inline` still shows
`new java/lang/StringBuilder` inside the loop body. What the advice always missed is that a
per-iteration builder is discarded per iteration, so nothing is accumulated across iterations
and the copying is unavoidable either way.

### Believing `StringBuffer` is the thread-safe upgrade you want

**Wrong**

```java
final StringBuffer auditLine = new StringBuffer();          // "thread-safe"
Runnable body = () -> {
    String tag = Thread.currentThread().getName().startsWith("stake") ? "SETTLE" : "PAYRUN";
    for (int i = 0; i < 2000; i++) {
        auditLine.append(tag).append('-').append(i % 10).append(';');
    }
};
Thread stakeSettlementWorker = new Thread(body, "stakeSettlementWorker");
Thread paymentRunWorker = new Thread(body, "paymentRunWorker");
```

Real output, Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64:

```console
append     StringBuffer synchronized=true   StringBuilder synchronized=false
toString   StringBuffer synchronized=true   StringBuilder synchronized=false
setLength  StringBuffer synchronized=true   StringBuilder synchronized=false
shared superclass : true (java.lang.AbstractStringBuilder)
total length      : 36000 (expected 36000)
well-formed rows  : 639 of 4000, contiguous=false
first corruption  : >-7;PAYRUN-8;PAYRUN-SETTLE-0;SETTLE-1<
```

Not one character was lost — 36,000 in, 36,000 out, no corrupted array, no exception. And the
audit log is still garbage: 639 well-formed rows before the first splice, where
`PAYRUN-` from one worker sits directly against `SETTLE-0;` from the other. Each of the four
`append` calls took the lock; the *row* took no lock at all, because a row is four calls. The
lock bought internal-state integrity, which was never the problem. The problem was a compound
operation with no atomicity, and `synchronized` on the individual methods cannot see it.

**Right**

Confine a plain `StringBuilder` to the worker and publish the finished line:

```java
StringBuilder auditLine = new StringBuilder(ROWS * 9);   // thread-confined
for (int i = 0; i < ROWS; i++) {
    auditLine.append(tag).append('-').append(i % 10).append(';');
}
sink.add(auditLine.toString());                          // one safe publication
```

```console
lines published   : 2
total length      : 36000 (expected 36000)
well-formed rows  : 4000 of 4000, contiguous=true
```

Every row intact, no locking anywhere in the append path, and the only cross-thread hand-off is
one immutable `String` into a `ConcurrentLinkedQueue`. If the rows genuinely must interleave into
one buffer, the unit of mutual exclusion is the row, so hold one lock across the whole row —
which is a `synchronized` block you write, not a class you pick.

**Why people believe it:** the javadoc contrast is stated as "`StringBuilder` is not
synchronized, use `StringBuffer` where synchronization is required", which reads like a
drop-in upgrade. It is more accurately a legacy class kept for source compatibility: it predates
`StringBuilder` (which arrived in 1.5), it shares the same `AbstractStringBuilder` body as the
probe above confirms, and it overrides every public method as `synchronized` — so a
single-threaded caller pays a lock on every call for a guarantee no single-threaded caller needs,
while a multi-threaded caller gets a guarantee weaker than the one it actually wanted.

### Believing a `StringBuilder` can grow past `Integer.MAX_VALUE - 8`

**Wrong**

```java
StringBuilder ledgerExport = new StringBuilder();
ledgerExport.ensureCapacity(Integer.MAX_VALUE - 1);      // "reserve the whole export"
StringBuilder sized = new StringBuilder(Integer.MAX_VALUE - 1);
```

Real output, Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64:

```console
start capacity    : 16
ensureCapacity    : java.lang.OutOfMemoryError: Requested array size exceeds VM limit
new StringBuilder : java.lang.OutOfMemoryError: Requested array size exceeds VM limit
soft max          : Integer.MAX_VALUE - 8 = 2147483639
```

Both fail, and neither failure is about heap — a bigger `-Xmx` changes nothing. The message is
HotSpot's array-length check, raised before any memory is requested. `newCapacity` had already
routed the request through `ArraysSupport.newLength`, which returned the minimum (2,147,483,646,
above `SOFT_MAX_ARRAY_LENGTH`), and it was the `byte[]` allocation itself that refused. A builder
is capacity-bounded by an `int` array length, and in practice by a soft maximum eight below it.

**Right**

Never accumulate an unbounded export in a builder. Reuse one small builder per row and stream:

```java
StringBuilder row = new StringBuilder(64);          // reused, never accumulates
try (Writer writer = new BufferedWriter(
        Files.newBufferedWriter(out, StandardCharsets.UTF_8), 1 << 16)) {
    for (int i = 0; i < ROWS; i++) {
        row.setLength(0);
        row.append("CLIENT_BONUS_RESERVED;").append(i % 10).append(";4.20\n");
        writer.write(row.toString());
    }
}
```

```console
rows written      : 20000000
chars written     : 580000000
ceiling (chars)   : 2147483639
peak builder cap  : 64
file bytes        : 580000000
```

One day of QuizStakes ledger entries — 20M rows, 580,000,000 characters — through a builder whose
capacity never left 64. `row.setLength(0)` resets `count` without releasing the array, which is
the whole point: the allocation happens once. Accumulating the same day in one builder would need
580 MB of `byte[]`; the 7.2B-row year, at 29 characters a row, is 208.8 billion characters, about
97 times the ceiling, and no heap size makes that reachable.

**Why people believe it:** `ensureCapacity` is documented as a hint that never shrinks and is
otherwise silent, so it reads like a request that either succeeds or is ignored. And the failure
mode is unfamiliar: `OutOfMemoryError` normally means "buy more heap", whereas
`Requested array size exceeds VM limit` means "this length cannot be represented as a Java array
on this VM, at any heap size". The 8-element gap below `Integer.MAX_VALUE` is
`ArraysSupport.SOFT_MAX_ARRAY_LENGTH`, chosen because some JVMs reject arrays a few elements
short of `Integer.MAX_VALUE` depending on header size.

---

## Cheat sheet

| Fact | Value |
|---|---|
| Measured, not JMH | mine 1.04, JDK 0.82, `+=` 147.53 ns/char (n=4,000), one expression 14.98 ns/line |
| Why the JDK beats mine by 27% | compact strings — 1,000,000 Latin-1 chars as 1,000,000 bytes, half the memory copied per grow — plus vectorised intrinsics |
| `+` in one expression, Java 9+ | `invokedynamic makeConcatWithConstants`, one exact-sized allocation, no builder |
| `+` in a loop, Java 21 | one indy per iteration, still O(n²): `n(n-1)/2` chars copied |
| `n(n-1)/2` at n=4,000 / n=1,000,000 | 7,998,000 / 499,999,500,000 char copies |
| Version trap | "`+` in a loop makes a `StringBuilder` per iteration" is pre-Java-9 only |
| Legacy concat strategy flag | `javac -XDstringConcat=inline` puts `new java/lang/StringBuilder` back in the loop |
| JEP that changed it | JEP 280, Java 9, `StringConcatFactory.makeConcatWithConstants` |
| "WithConstants" means | constant operands folded into the bootstrap recipe in the constant pool, not pushed on the stack |
| Indy descriptor keeps primitives | `(ILjava/lang/String;Ljava/lang/String;J)` — no boxing, no `Integer.toString` |
| Real fields | `byte[] value`, `byte coder`, `int count`; capacity in chars = `value.length >> coder` |
| `coder` values | `0` LATIN1, `1` UTF16 |
| Inflation trigger | first non-Latin-1 append; new `byte[]` twice as long, `StringLatin1.inflate`, `coder = UTF16`; char capacity unchanged |
| Real growth call | `ArraysSupport.newLength(oldLength, growth, oldLength + (2 << coder))` |
| Soft max array length | `ArraysSupport.SOFT_MAX_ARRAY_LENGTH = Integer.MAX_VALUE - 8 = 2147483639` |
| Past the ceiling | `OutOfMemoryError: Requested array size exceeds VM limit`, independent of `-Xmx` |
| `StringBuffer` | same `AbstractStringBuilder`, every public method `synchronized`, legacy since 1.5, per-call lock and no row-level atomicity |
| `StringBuilder` serial form | `serialVersionUID = 4383685877147921099L`, writes `int` count + `char[]` |
| `StringBuffer` serial form | `serialVersionUID = 3388685877147921107L`, `serialPersistentFields` of `value`/`count`/`shared` |
| What you cannot reproduce | compact strings, `StringLatin1`/`StringUTF16` intrinsics, the array-adopting `String` constructor, the frozen serial form |

---

## Self-test

**Q1.** On Java 21, does `line += c` inside a loop create a `StringBuilder` per iteration?

<details><summary>Answer</summary>

No. `javap -c -p` shows one `invokedynamic` to
`StringConcatFactory.makeConcatWithConstants` per iteration and no `new java/lang/StringBuilder`
anywhere in the method — that has been true since Java 9 and JEP 280. It is still quadratic
though: each indy call allocates a fresh `String` of length `i + 1` and copies all `i`
accumulated characters into it, so total work is `n(n-1)/2` character copies. The pre-9
`StringBuilder`-per-iteration shape is still available for inspection with
`javac -XDstringConcat=inline`, which puts `new java/lang/StringBuilder` right back in the loop
body.

</details>

**Q2.** The benchmark ran variant 3 at `n = 4,000` and variants 1 and 2 at `n = 1,000,000`. Why,
and what does that do to the 179x figure?

<details><summary>Answer</summary>

Because variant 3 is quadratic. At `n = 1,000,000` it would copy `n(n-1)/2 = 499,999,500,000`
characters and would not finish inside a note. Running it at a smaller `n` is the only way to
report it at all, which is why the comparison is stated as per-character cost rather than wall
clock. The consequence is that neither variant 3's 147.53 ns/char nor the 179x ratio against
variant 2 is a constant: both are properties of `n = 4,000`. Double `n` and the per-character
cost roughly doubles, because that is what quadratic total cost means when you divide by `n`. At
`n = 40,000` the ratio would be about ten times larger. Variants 1 and 2 have flat per-character
costs, so their 1.04-against-0.82 comparison is meaningful as stated.

</details>

**Q3.** In variant 4, `"AA-" + 801 + " client=" + clientId + " CLIENT_BONUS_RESERVED=" + i`, the
`javap` output shows only four loads before the `invokedynamic`. Where did the rest of the
expression go?

<details><summary>Answer</summary>

Into the bootstrap method's recipe string in the constant pool, which is what the
`makeConcatWithConstants` name refers to. The constant pieces — the literals `"AA-"`,
`" client="`, `" CLIENT_BONUS_RESERVED="` and the compile-time constant `801` — are not runtime
values, so they are not pushed on the stack; they are baked into the recipe that the bootstrap
method uses to build the `MethodHandle` chain once, on first execution, after which the call site
is a linked constant. Only the four genuinely dynamic operands are loaded. Note also that the
call descriptor is `(ILjava/lang/String;Ljava/lang/String;J)Ljava/lang/String;` — the `int` and
the `long` stay primitive, so there is no boxing and no `Integer.toString` on the path.

</details>

**Q4.** `MyStringBuilder` runs a pure `append(char)` loop at 1.04 ns/char against the JDK's 0.82.
The algorithm is identical. Where does the 27% go?

<details><summary>Answer</summary>

Almost entirely into compact strings. Those 1,000,000 characters are all Latin-1, so the real
builder held them in a `byte[]` as 1,000,000 bytes, while `MyStringBuilder` held them in a
`char[]` as 2,000,000 bytes. Every one of the 16 reallocations therefore copied half as much
memory in the JDK's case, and every write touched half as many cache lines. The rest is
`StringLatin1`/`StringUTF16` helpers that C2 vectorises and `@IntrinsicCandidate` compress and
inflate loops. None of it is reachable from user code: `StringLatin1`, `StringUTF16` and the
package-private `String(byte[], byte)` constructor are all inside `java.lang`. The measurement is
also not JMH — no fork, no `Blackhole`, only a `volatile` sink — so the 27% is a within-run
relative figure, not a portable one.

</details>

**Q5.** A `StringBuilder` holds 12 Latin-1 characters at `capacity() == 16`. You append one EURO
SIGN. What changes?

<details><summary>Answer</summary>

`length()` becomes 13 and `capacity()` stays 16, but the backing `byte[]` doubles from 16 to 32
and `coder` flips from `LATIN1` (0) to `UTF16` (1). EURO SIGN is not representable in Latin-1, so
`inflate()` allocates a new `byte[]` of twice the length, `StringLatin1.inflate` widens every
existing character from one byte to two, and the coder is switched. Capacity measured in
characters never changed — it is `value.length >> coder`, and both sides doubled. From then on
the builder pays two bytes per character for everything, including the twelve characters that
would still fit in one. `MyStringBuilder` starts at 32 bytes for the same 16 characters and stays
there, because a `char[]` has no narrow representation to inflate from.

</details>

**Q6.** Why does swapping a shared `StringBuilder` for a `StringBuffer` not fix a corrupted
concurrent audit log?

<details><summary>Answer</summary>

Because the corruption is at the wrong granularity for the lock. `StringBuffer` synchronizes each
public method, so no single `append` can interleave with another and the internal `count`/array
pair is never torn — measured, two workers writing 2,000 rows each produced exactly 36,000
characters with nothing lost. But a row is four `append` calls, and nothing holds the lock across
them, so the other worker's row splices into the middle: 639 well-formed rows before the first
splice, `PAYRUN-` immediately followed by `SETTLE-0;`. The unit of mutual exclusion has to be the
compound operation. Either confine a plain `StringBuilder` to each worker and publish the finished
`String`, or hold one lock across the whole row yourself. As a bonus, the confined version does no
locking at all on the hot path, and `StringBuffer` charges every single-threaded caller a lock for
a guarantee they never asked for.

</details>

---

## Open questions

- Whether JDK 8 and JDK 11 wrote `AbstractStringBuilder`'s growth literally as
  `(value.length << 1) + 2` rather than routing through `ArraysSupport.newLength`. Settled by a
  JDK 8u or 11 `src.zip`, or the OpenJDK Mercurial/Git history of
  `src/java.base/share/classes/java/lang/AbstractStringBuilder.java`. Only JDK 21.0.7's source
  was available here, and it uses the `newLength` form.
- Whether `newCapacity`'s `OutOfMemoryError("Required length exceeds implementation limit")`
  branch is reachable in practice on this machine — it needs a builder within 8 chars of
  `Integer.MAX_VALUE`, roughly 4 GB of live `byte[]` plus a same-sized copy target. Settled by a
  run with a heap above about 12 GB, which was not attempted. The nearer ceiling *is* reachable
  and was measured: `ensureCapacity(Integer.MAX_VALUE - 1)` fails with
  `OutOfMemoryError: Requested array size exceeds VM limit` from the array allocation, not from
  that branch.

---

**Leaves covered:** 4.2.5, 4.2.6 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 536
