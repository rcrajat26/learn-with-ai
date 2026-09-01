# 03 Java Core — `String`: the API surface — BASICS (§1.10)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [Boxing internals](../wrappers-and-boxing/03-internals-boxing.md) · Next: [The string pool](01b-the-string-pool.md)

## The type contract (1.10.1)

`String`'s declaration is the map before the streets. Five interfaces, each buying something specific.

| Interface | What it buys | Consequence you can be asked about |
|---|---|---|
| `final class` (not an interface) | No subclass can break immutability or override `equals` | You cannot mock or decorate `String`; wrap it (`IdempotencyKey(String value)`) instead |
| `java.io.Serializable` | Wire format with `serialVersionUID = -6849794470754667710L` | Fixed since 1.0; a `String` written by JDK 8 deserialises on 21 |
| `Comparable<String>` | `compareTo` → sortable, `TreeMap` key | Order is UTF-16 code-unit order, **not** locale collation (1.10.21) |
| `CharSequence` | Common read API with `StringBuilder`, `CharBuffer`, `Segment` | `CharSequence` deliberately does not specify `equals` (1.10.22) |
| `Constable`, `ConstantDesc` (Java 12+) | `describeConstable()` returns `Optional<String>`; `String` is its own nominal descriptor | Lets `invokedynamic` bootstrap methods and `condy` carry strings as constants |

Verified against the JDK 21 declaration: `public final class String implements java.io.Serializable, Comparable<String>, CharSequence, Constable, ConstantDesc`.

---

## Immutability and the field set (1.10.1–1.10.3, 1.10.5)

A `String` is not a container of characters. It is a **small immutable header pointing at a byte array it will never let go of and never write to again**. Once the constructor returns, every field that matters is frozen; the only mutable field in the whole class is a memoised hash. That single fact is what makes `String` usable as a map key, as a lock-free shared constant, and as the identity of a class or a file path inside the JVM's own security checks.

### Why it exists

`String` was mutable-by-array in nobody's design, because the platform needs to hand the same character data to code it does not trust. If `SecurityManager` checks a file path and the caller can mutate the path afterwards, every check is a time-of-check-to-time-of-use bug. Before immutable strings, the alternative was defensive copying at every boundary — which is exactly what C code does with `strdup`, and exactly the cost `String` removes.

### How it works — the field set (1.10.2)

```java
public final class String
        implements java.io.Serializable, Comparable<String>, CharSequence,
                   Constable, ConstantDesc {

    @Stable
    private final byte[] value;   // never written after the constructor

    private final byte coder;     // LATIN1 = 0, UTF16 = 1

    private int hash;             // memoised String.hashCode(), 0 = not yet computed

    private boolean hashIsZero;   // true once we prove the real hash is 0

    static final boolean COMPACT_STRINGS;   // true on JDK 21 unless -XX:-CompactStrings

    private static final long serialVersionUID = -6849794470754667710L;
}
```

Line by line: `value` holds the encoded bytes — **not** chars — and `@Stable` tells the JIT that after the first non-default read the contents will never change, so it may constant-fold loads out of the array. `coder` says how to decode `value`: `0` means one byte per character (Latin-1), `1` means two bytes per UTF-16 code unit, little-endian pairs. `hash` and `hashIsZero` are the two non-final fields, and they are benign races: any thread that recomputes gets the same answer (1.10.19). `COMPACT_STRINGS` is a `static final` set in a static initialiser from a JVM flag, so the JIT folds the Latin-1 fast paths to unconditional code.

**Insight:** immutability here is a *design* invariant, not a language one. `value` is `final`, but `byte[]` contents are mutable — nothing in the JLS stops `String` from writing to it. The guarantee holds because every method that produces different content allocates a new array, and because no method ever leaks `value` (`toCharArray()`, `getBytes()`, and `chars()` all copy or decode).

![D-029 — Inside a `String`](../diagrams/D-029-inside-a-string.svg)

**D-029** — Inside a `String` holding `"SCREENING_IN_PROGRESS"`: look at the 24-byte object (12-byte header, `value` reference, `hash`, `coder`, `hashIsZero`, padded up under `ObjectAlignmentInBytes = 8`) versus the 40-byte `byte[]` (16-byte header plus 21 Latin-1 bytes, padded from 37). 64 bytes total for 21 characters.

### What immutability buys (1.10.3) — worked through

`ApplicationHistory` writes an audit row per status transition for 2.4M registered clients. Each row records the status name. If the name string were mutable, each of the four claims below would fail:

```java
record HistoryRow(ApplicationId applicationId, String statusName, Instant at) {}

final class ApplicationHistory {

    // ONE String instance, shared by every row ever written for this status.
    private static final String SCREENING = "AA-500 SCREENING_IN_PROGRESS";

    private final List<HistoryRow> rows = new CopyOnWriteArrayList<>();
    private final Map<String, Integer> countByStatus = new ConcurrentHashMap<>();

    void recordScreeningStarted(ApplicationId id) {
        rows.add(new HistoryRow(id, SCREENING, Instant.now()));
        countByStatus.merge(SCREENING, 1, Integer::sum);
    }
}
```

1. **Thread safety without synchronisation.** `SCREENING` is published once by the class initialiser, which the JVMS makes safe under the locking of `<clinit>`. Every reader on every one of the 3,400/sec settlement threads sees fully-initialised bytes. No `volatile`, no lock.
2. **Safe map key.** `countByStatus` buckets by `hashCode()`. A mutable key mutated after insertion lands in the wrong bucket and becomes unfindable — the entry leaks and `get` returns `null` for a key that is provably present.
3. **Cached hash.** Legal *only* because content is frozen. `merge` on a 28-char key recomputes nothing after the first call.
4. **Safe sharing and interning.** Because two equal strings are interchangeable, the JVM may collapse them to one instance and G1 may deduplicate their arrays. Sharing 2.4M references to one 64-byte object instead of 2.4M copies is ~150 MB saved. The pool that performs that collapse, `intern()` (1.10.24), and constant folding are covered in `01b-the-string-pool.md`.

### `new String("x")` is almost always wrong (1.10.5)

**Pitfall:** the belief is that `new String(s)` is a useful defensive copy, the way `new ArrayList<>(list)` is. Symptom: an extra 24-byte object per call, a lost `==` fast path, a lost pooled identity, and code that reads as if `String` were mutable. `new String("AA-801")` allocates a fresh header that points at the *same* `value` array as the literal (the copy constructor shares the array precisely because the source cannot change it), so you pay for the header and gain nothing. Fix: write the literal, or `String.valueOf(x)`. The one legitimate use is trimming a huge backing array — `new String(bigString.substring(0, 8))` is unnecessary post-Java-7 (1.10.18), so in practice the legitimate use has been gone since 2011.

> A `String` is a `final`, `Serializable`, `Comparable`, `CharSequence` façade over a `private final byte[]` plus a `coder`, whose contents are never rewritten after construction, which is what licenses hash caching, interning, and lock-free sharing.

### Construction forms (1.10.4)

| Form | Allocates a `String`? | Copies the bytes? | Use when |
|---|---|---|---|
| `"AA-801"` literal | No — resolved from the pool | No | Always, for known text |
| `new String("AA-801")` | Yes | No (shares `value`) | Effectively never (1.10.5) |
| `String.valueOf(obj)` | Only if `obj != null` returns new | Depends on `toString()` | Null-safe rendering; returns `"null"` |
| `String.valueOf(char[])` | Yes | Yes | Chars from a parser buffer |
| `String.copyValueOf(char[])` | Yes | Yes | Identical to the above; a 1.0-era alias |
| `new String(byte[], Charset)` | Yes | Yes, after decoding | Bytes off a socket or file |
| `new String(char[], int, int)` | Yes | Yes, the range only | Sub-range of a reusable buffer |

Prefer the explicit `Charset` overloads. The no-charset overloads use the default charset, which is UTF-8 since Java 18 (JEP 400) and was platform-dependent before — code written pre-18 that "worked" on Linux and mangled bytes on a Windows build box was reading that difference.

---

## The reading, searching and comparing surface

**Reading (1.10.6)**

| Method | Returns | Mechanism note |
|---|---|---|
| `length()` | UTF-16 code units | `value.length >> coder`; not the character count for emoji or astral planes |
| `charAt(int)` | one code unit | `char`, so a surrogate half for anything above U+FFFF |
| `codePointAt(int)` | full code point | Combines a surrogate pair when it finds a valid high/low |
| `isEmpty()` | `length() == 0` | Never allocates |
| `isBlank()` (11) | empty or all-whitespace | Uses `Character.isWhitespace`, like `strip()` |
| `chars()` | `IntStream` of code units | Widening `char`→`int`; no surrogate combining |
| `codePoints()` | `IntStream` of code points | Combines surrogate pairs |
| `toCharArray()` | fresh `char[]` | Always copies — inflates Latin-1 to two bytes per char |
| `getBytes(Charset)` | fresh `byte[]` | Always copies; encodes, so a Latin-1 string to UTF-8 may grow |

**Searching (1.10.7)** — `indexOf` and `lastIndexOf` each come in four overloads: `(int codePoint)`, `(int codePoint, int fromIndex)`, `(String)`, `(String, int fromIndex)`. All four use a plain scan, not Boyer-Moore, so a substring search is O(n·m) worst case; the escape hatch for hot repeated searching over one large text is a compiled `Pattern` or an index you build yourself. `contains(CharSequence)` is `indexOf(s.toString()) >= 0`. `startsWith`/`endsWith` are bounded `regionMatches`. `matches(String regex)` compiles a fresh `Pattern` on **every call** — cost: full regex compilation per invocation; escape hatch: hoist a `static final Pattern`.

**Comparing (1.10.8)**

| Method | Ignores case? | Locale-aware? | Notes |
|---|---|---|---|
| `equals(Object)` | No | No | Identity → `coder` → byte compare (1.10.20) |
| `equalsIgnoreCase` | Yes | No | Per-code-point folding, no `Locale` parameter at all |
| `compareTo` | No | No | UTF-16 code-unit order (1.10.21) |
| `compareToIgnoreCase` | Yes | No | Folds both sides to lower then upper, root-locale rules |
| `contentEquals(CharSequence)` | No | No | The way to compare a `String` to a `StringBuilder` |
| `regionMatches(int, String, int, int)` | No | No | Bounded compare, no allocation |
| `regionMatches(boolean, int, String, int, int)` | Optional | No | The `ignoreCase` flag form |

**Producing (1.10.9)** — every one of these returns a new `String`; none mutate.

| Method | Since | Behaviour worth remembering |
|---|---|---|
| `substring(int[, int])` | 1.0 | Copies since 7 (1.10.18); returns `this` when the range is the whole string |
| `concat(String)` | 1.0 | Returns `this` if the argument is empty; single array copy |
| `replace(char, char)` | 1.0 | Literal, no regex |
| `replace(CharSequence, CharSequence)` | 5 | Literal despite taking strings — quotes the target internally |
| `replaceAll` / `replaceFirst` | 1.4 | **Regex** target, and `$` and `\` are live in the replacement |
| `toUpperCase` / `toLowerCase` | 1.0 | No-`Locale` form uses the default locale (1.10.11) |
| `trim()` | 1.0 | Code points ≤ U+0020 only (1.10.10) |
| `strip` / `stripLeading` / `stripTrailing` | 11 | `Character.isWhitespace`, Unicode-aware |
| `repeat(int)` | 11 | One allocation of exactly the final size |
| `indent(int)` | 12 | Adds/removes leading spaces per line; normalises line endings to `\n` |
| `stripIndent()` | 15 | The incidental-indentation algorithm text blocks use |
| `translateEscapes()` | 15 | Interprets `\n`, `\t`, `\uXXXX` in already-loaded text |
| `formatted(Object)` | 15 | Instance-side `String.format`, varargs, default locale |
| `transform(Function)` | 12 | Applies a function to `this`; lets a parse chain read left-to-right |

**Splitting and joining (1.10.12)** — `split(String regex)` is `split(regex, 0)`; `String.join` has a varargs form and a `Iterable<? extends CharSequence>` form, both delegating to `StringJoiner`; `lines()` (11) returns a lazy `Stream<String>` that splits on `\n`, `\r`, or `\r\n` without allocating an array — the right tool for the 6.5k/day bank statement files, because it never materialises the whole file as an array.

**Formatting (1.10.15)** — a specifier is `%[argument_index$][flags][width][.precision]conversion`. `%s`, `%d`, `%f`, `%x`, `%n`. The `,` flag and `%f` are **locale-sensitive**: `String.format("%,.2f", 1234.5)` is `1,234.50` under `Locale.UK` and `1.234,50` under `Locale.GERMANY`. For anything a machine will re-parse — a ledger export, a payment file — pass `Locale.ROOT` explicitly.

`String.format` is slow relative to concatenation (1.10.16) `[NUM]`: it allocates a `Formatter`, parses the format string character by character on every call, and boxes every primitive argument. Order of magnitude on typical JDK 21 hardware: `+` concatenation of two strings is tens of nanoseconds, a `StringBuilder` chain similar, `String.format` a few hundred nanoseconds to low microseconds. At 19.8M ledger entries a day that is seconds of CPU; inside the 3,400/sec settlement burst it is measurable. Cost of avoiding it: concatenation code is less readable and cannot reorder arguments. Escape hatch: keep `String.format` for logging that is guarded off in production and for operator-facing messages, and use plain concatenation on the ledger write path.

### `String.hashCode` (1.10.19) `[X-REF 02]`

```java
public int hashCode() {
    int h = hash;
    if (h == 0 && !hashIsZero) {
        h = isLatin1() ? StringLatin1.hashCode(value)
                       : StringUTF16.hashCode(value);
        if (h == 0) {
            hashIsZero = true;
        } else {
            hash = h;
        }
    }
    return h;
}
```

The function is the sum over `i` from `0` to `n-1` of `s[i] * 31^(n-1-i)` — `s[0]*31^(n-1)` for the first character down to `s[n-1]*31^0` for the last — computed as `h = 31*h + s[i]` in `int` arithmetic with wraparound. `[NUM]` For `"AA"`: `('A' = 65)`, `h = 31*65 + 65 = 2080`. The memo has a two-field design because `hash == 0` is ambiguous — `""` and `"polygenelubricants"` both hash to 0 — so before Java 13 those strings recomputed on every call; `hashIsZero` (added in JDK 13, JDK-8221723) records the proof once. The `hash`/`hashIsZero` writes are an unsynchronised benign race: every thread computes the identical value. Full walk of `StringLatin1.hashCode` and the collision consequences for `HashMap`: `03-internals-string.md`, and the general `equals`/`hashCode` contract in guide `02`.

### `String.equals` (1.10.20)

```java
public boolean equals(Object anObject) {
    if (this == anObject) {
        return true;
    }
    return (anObject instanceof String aString)
            && (!COMPACT_STRINGS || this.coder == aString.coder)
            && StringLatin1.equals(value, aString.value);
}
```

Three gates in order: reference identity (the common case for pooled literals, one instruction), then `coder` — two strings with different coders can never be equal because the compaction rule makes Latin-1 encoding canonical for any string that fits in Latin-1 — then a raw `byte[]` compare that ignores the coder entirely, since equal coders means equal encodings. Note `instanceof String aString` and not `getClass()`: legal because `String` is `final`. Full source walk in `03-internals-string.md`.

### `compareTo` is not collation (1.10.21) `[X-REF 02]`

`compareTo` subtracts UTF-16 code units at the first differing index, returning `length() - other.length()` if one is a prefix. So `"Z" < "a"` (90 < 97) and `"ä" > "z"` (U+00E4 = 228 > 122) — an operator sorting a client list gets `Zutphen` before `apple` and `ätna` last. **Pitfall-adjacent:** for anything a human reads, use `Collator.getInstance(locale)` (locale collation, tertiary strength by default) or a `Comparator` over a `Collator`-produced `CollationKey` when you sort repeatedly. Cost: `Collator` is slower and not `Serializable`-stable across JDK versions; escape hatch: keep `compareTo` for machine keys such as `StatusCode` ordering, where deterministic byte order is the requirement.

### `CharSequence` has no `equals` (1.10.22)

`CharSequence` specifies `length`, `charAt`, `subSequence`, `toString`, plus default `chars`/`codePoints`, and deliberately **does not** refine `equals`/`hashCode`. **Pitfall:** `sb1.equals(sb2)` on two `StringBuilder`s with identical content is `false` — `StringBuilder` inherits `Object.equals`, so it is identity. Symptom: a cache keyed by `CharSequence` never hits. Fix: `s.contentEquals(sb)`, or normalise to `String` at the boundary. Since Java 11 `CharSequence.compare(a, b)` gives you a lexicographic comparison without materialising strings.

### `String` in `switch` (1.10.23)

`switch` on a `String` (Java 7+) compiles to a two-stage lowering: a `lookupswitch` on `hashCode()` selecting a candidate, an `equals` call to confirm it (hash collisions produce a chain), then a second `tableswitch` on a synthetic index to reach the real bodies. Consequence: an old-style `switch (statusName)` with a `null` selector throws `NullPointerException` on the `hashCode()` call, before any `default:` label is considered. A Java 21 pattern-matching `switch` may write `case null ->` explicitly and then handles it.

---

## `substring` copies since Java 7 (1.10.18) `[VERSION-TRAP]`

Picture `BankDeposits` reading a 4 KB fixed-width statement line and keeping only the 8-character reference `"BDP-101 "`. Two mental models, one per era: in Java 6 the small string was a **window** onto the big array; since Java 7u6 it is an **independent copy**.

### Why it changed

The window was O(1) and allocation-light, which is why it existed: `substring` on a parser hot loop cost one 32-byte header. The failure mode was retention. A `String` holding `offset = 0, count = 8` still referenced the whole `char[]`, so the 8-character reference kept 4 KB alive. Parse 6,500 statement lines a day into a long-lived index and you retain ~26 MB of statement text to store ~52 KB of references — a leak with no leaking code. JDK-4513622 tracked it for years; JDK 7u6 removed `offset` and `count` from `String` and made `substring` copy.

### The numbers `[NUM]`

A 4,096-character Latin-1 statement line. Java 6: `char[4096]` = 16-byte header + 8,192 bytes = 8,208 bytes, retained in full by the substring, plus a 32-byte `String` header (`value`, `offset`, `count`, `hash`) → **8,240 bytes retained per reference**. Java 21: `byte[8]` = 16-byte header + 8 bytes, padded to 24, plus the 24-byte `String` → **48 bytes retained**, and the 4 KB line becomes garbage at the next collection. 172× less retained memory, at the cost of an 8-byte `System.arraycopy` per call.

![D-030 — `substring`: copy since 7, shared before](../diagrams/D-030-substring-copy.svg)

**D-030** — Compare the two arrows out of the substring object: Java 6 points *into* the 4 KB `char[]` with `offset`/`count`, Java 7+ points at its own 8-byte `byte[]`. The 4 KB array is unreachable on the right.

```java
final class BankDeposits {

    private static final int REF_START = 0;
    private static final int REF_END = 8;

    private final Map<String, Money> creditsByReference = new HashMap<>();

    void ingest(String statementLine) {                 // ~4096 chars
        String reference = statementLine.substring(REF_START, REF_END).strip();
        Money credit = Money.of(statementLine.substring(120, 134).strip(), "GBP");
        creditsByReference.put(reference, credit);      // retains 48 bytes, not 8 KB
    }
}
```

**Pitfall:** the old advice `new String(line.substring(0, 8))` to force a copy. Symptom: on Java 7+ it is a pure extra allocation — the substring already copied, so `new String` adds a second header for nothing. Fix: delete the wrapper. State the old truth too, because interviewers ask for it: before 7u6 that wrapper was the documented fix for the retention leak, and `substring` was O(1) rather than O(n).

**Interview:** "Is `substring` O(1)?" — "O(n) in the substring length since 7u6, because it copies; O(1) before that, which is why it leaked the parent array."

> Since Java 7u6, `substring` allocates and copies an independent backing array, trading O(n) copy cost for the removal of unbounded parent-array retention; it returns `this` only when the requested range is the entire string.

---

## `split` is a regex, and it eats trailing empties (1.10.13, 1.10.14)

`split` looks like a delimiter API and is not one. Read it as: **compile the argument as a `Pattern`, find every match, emit the gaps, then walk backwards deleting empty gaps unless you told it not to.** Two independent surprises, one in each half of that sentence.

### Why it is a regex

`split` arrived in Java 1.4 alongside `java.util.regex`, as the string-side convenience for `Pattern.split`. There was no literal-delimiter split, and there still is not — `Pattern.quote` is the escape hatch. The one concession: `Pattern` fast-paths a single-character argument that is not a regex metacharacter, so `split(",")` never builds an NFA. `split(".")` does not qualify, because `.` *is* a metacharacter.

### Surprise one: `"BDP-101.ACME.  ".split(".")` returns a zero-length array (1.10.13)

`.` matches any character except a line terminator. Every one of the 15 characters is a match, so all 16 gaps are empty, so the trailing-empty removal deletes all of them. Length 0, not 15, not 1.

### Surprise two: the limit argument (1.10.14) `[NUM]`

| Limit | Pattern applied | Trailing empties | `"65,,".split(",", limit)` |
|---|---|---|---|
| `0` (the `split(String)` default) | as many times as possible | **removed** | `["65"]`, length 1 |
| negative, e.g. `-1` | as many times as possible | **kept** | `["65", "", ""]`, length 3 |
| `2` | at most 1 split | kept (limit reached) | `["65", ","]`, length 2 |

The arithmetic on `"65,,"`: two matches at indices 2 and 3 produce gaps `"65"`, `""`, `""` — three fields. With `limit == 0` the loop trims from the end while the last field is empty, removing both, leaving 1. Leading empties are never removed: `",,65".split(",")` is `["", "", "65"]`, length 3.

![D-031 — `split` is a regex, and it eats trailing empties](../diagrams/D-031-split-regex.svg)

**D-031** — Left: the same input under `split(".")` (zero fields) and `split("\\.")` (three, the trailing `"  "` surviving because it is not empty). Right: `"65,,"` losing two columns under `split(",")` and keeping them under `split(",", -1)`.

```java
final class BankDepositReferenceParser {

    private static final Pattern DOT = Pattern.compile("\\.");

    /** "BDP-101.ACME.  " -> reference BDP-101, originator ACME. */
    static Optional<BankReference> parse(String raw) {
        String[] parts = DOT.split(raw, -1);            // -1: keep every column
        if (parts.length != 3) {
            return Optional.empty();
        }
        String reference = parts[0].strip();
        String originator = parts[1].strip();
        String memo = parts[2].strip();                 // legitimately empty here
        return reference.startsWith("BDP-")
                ? Optional.of(new BankReference(reference, originator, memo))
                : Optional.empty();
    }
}

record BankReference(String reference, String originator, String memo) {}
```

**Pitfall (1.10.13):** believing the argument is a literal. Symptom: `split(".")` or `split("|")` returns an empty or single-element array and the parser silently drops every row, so the 6.5k/day bank deposits land in `SUSPENSE` instead of `CLIENT_CASH_AVAILABLE`. Fix: `Pattern.quote(delimiter)`, or escape the metacharacter (`"\\."`), or hoist a `static final Pattern`.

**Pitfall (1.10.14):** believing the field count equals delimiters + 1. Symptom: a CSV row whose last columns are empty yields a short array, and the code either reads the wrong column by index or throws `ArrayIndexOutOfBoundsException` on well-formed input — a bug that only fires on the rows that happen to end blank. Fix: always pass a negative limit when parsing positional data.

**Interview:** "What does `"65,,".split(",")` return?" — "One element, `"65"`; the two trailing empties are stripped because the default limit is 0. Use `-1` to keep them."

> `split` compiles its argument as a regular expression and, with a limit of zero, discards trailing empty fields; a negative limit preserves them and a positive limit caps the number of splits.

---

## Locale- and Unicode-sensitive text methods (1.10.10, 1.10.11)

Both defects here have the same shape: a method reads ambient state (the default locale) or a definition of "whitespace" narrower than the reader expects, and the wrong answer only appears on inputs the developer's machine never produces.

### `trim()` versus `strip()` (1.10.10)

`trim()` predates Unicode-awareness. Its loop is literally `while (st < len && val[st] <= ' ')` — it removes any code point with a value ≤ U+0020, which includes control characters like `\u0000` and `\u0007` and excludes every Unicode space above U+0020. `strip()` (Java 11) uses `Character.isWhitespace`.

| Input character | `trim()` removes | `strip()` removes | Why |
|---|---|---|---|
| `' '` U+0020 | Yes | Yes | ≤ U+0020 and `isWhitespace` |
| `'\t'` U+0009 | Yes | Yes | Both |
| `'\u0000'` NUL | **Yes** | No | ≤ U+0020, but not whitespace |
| `'\u3000'` ideographic space | No | **Yes** | > U+0020, but `isWhitespace` |
| `'\u00A0'` no-break space | No | **No** | `isWhitespace` is `false` for NBSP |

The NBSP row is the one that catches people who "upgraded to `strip()` to be Unicode-safe": `Character.isWhitespace` is defined to exclude non-breaking spaces (U+00A0, U+2007, U+202F) precisely because they are not line-breaking opportunities. Verified against the JDK 21 `Character.isWhitespace` specification.

```java
final class PersonalDetails {

    /** Client-supplied address lines arrive with pasted-in Unicode padding. */
    static String normaliseAddressLine(String raw) {
        return raw.replace('\u00A0', ' ')      // NBSP -> plain space first
                  .replace('\u202F', ' ')      // narrow NBSP
                  .strip();                    // now Unicode-aware trimming works
    }
}
```

**Pitfall:** believing `strip()` handles all invisible padding. Symptom: `"  AA-801\u00A0"` compares unequal to `"AA-801"` after `strip()`, the address-capture step never reaches `AO-121 ADDRESS_CAPTURED`, and the field looks correct in every log. Fix: replace non-breaking spaces explicitly before stripping, as above.

### The Turkish dotless i (1.10.11) `[PROVE]`

`toUpperCase()` with no argument is `toUpperCase(Locale.getDefault())`. For the Turkish locale, Unicode defines a *locale-specific* casing rule: lowercase `i` (U+0069) uppercases to `İ` LATIN CAPITAL LETTER I WITH DOT ABOVE (U+0130), and uppercase `I` lowercases to `ı` DOTLESS SMALL I (U+0131). Work it through on a status name:

```java
String status = "aa-801 activated";

status.toUpperCase(Locale.ROOT);          // "AA-801 ACTIVATED"
status.toUpperCase(Locale.of("tr"));      // "AA-801 ACTİVATED"   <- U+0130 at index 10
```

So `status.toUpperCase().equals("AA-801 ACTIVATED")` is `true` on the developer's UK laptop and `false` on a JVM started with `-Duser.language=tr`, or on one whose `Jurisdiction` country is `"TR"` and whose startup code called `Locale.setDefault`. The string lengths still match, `equalsIgnoreCase` still returns `true` (it folds per code point without locale rules), and only the exact `equals` fails — which is why the bug reaches production. `Locale.of(String)` is the Java 19+ factory; `new Locale("tr")` is the older form and its constructors are deprecated for removal.

**Pitfall:** case-normalising protocol tokens with the no-argument overload. Symptom: an `AccountActivation` transition to `AA-801 ACTIVATED` throws `IllegalTransitionException` only for clients in one jurisdiction, and only after someone changed a deployment's default locale. Fix: `toUpperCase(Locale.ROOT)` for every machine-readable token; reserve the default-locale form for text a human in that locale will read.

**Interview:** "When is `toUpperCase()` wrong?" — "Whenever the result is compared or parsed rather than displayed: it uses the ambient default locale, and Turkish maps `i` to `İ`."

> Locale-free text operations are the ones that read no ambient state: `equals`, `compareTo`, `strip`, and every `Locale.ROOT` overload; `toUpperCase()`, `toLowerCase()`, `String.format`, and `formatted` all read `Locale.getDefault()`.

---

## Pitfalls

### Assuming `split` takes a literal delimiter

**Wrong**
```java
String[] parts = "BDP-101.ACME.  ".split(".");
System.out.println(parts.length);           // prints 0, not 3
```

**Right**
```java
private static final Pattern DOT = Pattern.compile("\\.");
String[] parts = DOT.split("BDP-101.ACME.  ", -1);   // length 3
```
The escaped `\\.` matches a literal dot, and the `-1` limit keeps the trailing field. Hoisting the `Pattern` also removes a recompilation per call.

**Why people believe it:** the parameter is named `regex` but typed `String`, and the overwhelmingly common argument — `","` — behaves identically as a literal and a regex, so the abstraction never leaks until someone splits on `.`, `|`, `$`, or `+`.

### Expecting `split` to return one field per delimiter

**Wrong**
```java
String[] cols = "65,,".split(",");
Money amount = Money.of(cols[0], "GBP");
String memo = cols[2];                      // ArrayIndexOutOfBoundsException: 2
```

**Right**
```java
String[] cols = "65,,".split(",", -1);      // ["65", "", ""]
Money amount = Money.of(cols[0], "GBP");
String memo = cols[2];                      // "" — present and empty
```

**Why people believe it:** every example row in every tutorial has a non-empty last column, so the trimming behaviour is invisible until real data arrives with blank trailing fields.

### Case-folding a protocol token with the no-argument `toUpperCase()`

**Wrong**
```java
if (raw.toUpperCase().equals("AA-801 ACTIVATED")) {   // false under -Duser.language=tr
    activate(accountId);
}
```

**Right**
```java
if (raw.toUpperCase(Locale.ROOT).equals("AA-801 ACTIVATED")) {
    activate(accountId);
}
```

**Why people believe it:** the no-argument overload is shorter, and it is correct on every machine whose default locale is English — which is every developer laptop and most CI runners in the team.

### Treating `strip()` as removing all invisible padding

**Wrong**
```java
String line = "12 High Street\u00A0";
line.strip().equals("12 High Street");       // false — NBSP survives
```

**Right**
```java
line.replace('\u00A0', ' ').strip().equals("12 High Street");   // true
```

**Why people believe it:** `strip()` is documented as Unicode-aware, and it is — but `Character.isWhitespace` deliberately excludes non-breaking spaces, which are exactly the characters that arrive from pasted web content.

### Expecting `equals` to work between two `StringBuilder`s

**Wrong**
```java
StringBuilder a = new StringBuilder("AA-801");
StringBuilder b = new StringBuilder("AA-801");
a.equals(b);                                 // false — Object identity
```

**Right**
```java
"AA-801".contentEquals(a);                   // true
CharSequence.compare(a, b) == 0;             // true, Java 11+, no allocation
```

**Why people believe it:** `CharSequence` looks like a value abstraction, so it is natural to assume it refines `equals` — it explicitly does not.

## Cheat sheet

| Thing | Answer |
|---|---|
| Fields | `@Stable final byte[] value`, `final byte coder`, `int hash`, `boolean hashIsZero` |
| `serialVersionUID` | `-6849794470754667710L` |
| Coder values | `LATIN1 = 0`, `UTF16 = 1`; `COMPACT_STRINGS = true` on JDK 21 |
| `hashCode` | `h = 31*h + s[i]`, `int` wraparound; memoised, `hashIsZero` since JDK 13 |
| `equals` gates | `this ==` → `coder` → `byte[]` compare |
| `substring` | Copies since 7u6, O(n); shared with `offset`/`count` before, O(1) but leaked |
| `split(String)` | Regex; limit 0; trailing empties dropped, leading kept |
| `split(re, -1)` | Keeps every trailing empty field |
| `"65,,".split(",")` | `["65"]`, length 1 |
| `"a.b".split(".")` | length 0 |
| `trim()` vs `strip()` | ≤ U+0020 vs `Character.isWhitespace`; neither removes U+00A0 |
| Turkish trap | `"i".toUpperCase(tr)` = `İ` U+0130; use `Locale.ROOT` |
| `String.valueOf(null)` | Binds `char[]` overload → NPE; cast to `(Object)` for `"null"` |
| `matches` / `replaceAll` | Compile a fresh `Pattern` per call; hoist a `static final Pattern` |
| `String.format` | Hundreds of ns to low µs per call; locale-sensitive `%f` and `,` |
| Default charset | UTF-8 since Java 18 (JEP 400) |
| Pool, `intern()`, folding | `01b-the-string-pool.md` |

## Self-test

**Q1.** Why can `String` cache its hash code without synchronisation, and why are there two fields rather than one?

<details><summary>Answer</summary>

Content is frozen after construction, so every thread that computes the hash computes the identical `int`. The write to `hash` is therefore a benign race: a thread may see 0 and recompute, but never a wrong value. Two fields exist because `hash == 0` cannot distinguish "not yet computed" from "computed, and the answer is genuinely 0" — `""` hashes to 0, as does `"polygenelubricants"`. Before JDK 13 those strings recomputed on every call; `hashIsZero`, added in JDK 13, records the proof once.

</details>

**Q2.** `"BDP-101.ACME.  ".split(".")` — what is the array length, and why?

<details><summary>Answer</summary>

Zero. The argument is compiled as a regex, and `.` matches any character except a line terminator, so all 15 characters match. Every field between matches is empty, and with the default limit of 0 `split` deletes trailing empty fields from the end — all of them. Use `"\\."` (three fields: `"BDP-101"`, `"ACME"`, `"  "`) or `Pattern.quote(".")`.

</details>

**Q3.** Why does `split(",")` on `"65,,"` return one element?

<details><summary>Answer</summary>

There are two matches, at indices 2 and 3, producing three fields: `"65"`, `""`, `""`. `split(String)` delegates to `split(regex, 0)`, and a limit of zero means trailing empty fields are removed — the loop trims from the end while the last field is empty, deleting both. `split(",", -1)` returns all three. Leading empties are never removed, so `",,65".split(",")` has length 3.

</details>

**Q4.** Is `substring` O(1)? Answer for Java 21 and for Java 6.

<details><summary>Answer</summary>

Java 21: O(n) in the substring length, because `substring` allocates a new backing array and copies. Java 6 and earlier: O(1), because the returned `String` shared the parent `char[]` and recorded `offset` and `count`. The O(1) version was removed in 7u6 because it retained the parent array — an 8-character reference taken from a 4,096-character statement line kept ~8.2 KB alive instead of ~48 bytes. The old workaround, `new String(s.substring(0, 8))`, is now pure waste.

</details>

**Q5.** A client-supplied address line ends with U+00A0. Does `strip()` remove it, and does `trim()`?

<details><summary>Answer</summary>

Neither. `trim()` removes only code points ≤ U+0020, and U+00A0 is above that. `strip()` uses `Character.isWhitespace`, which is specified to return `false` for the non-breaking spaces U+00A0, U+2007 and U+202F precisely because they are not line-breaking opportunities. So the padding survives both, the comparison against the expected value fails, and the field looks correct in every log. Replace the non-breaking spaces with U+0020 first, then `strip()`. Note the converse case: `trim()` removes control characters such as `\u0000` that `strip()` leaves alone, and `strip()` removes wide Unicode spaces such as `\u3000` that `trim()` leaves alone.

</details>

**Q6.** Why does `String.valueOf(null)` throw, while `String.valueOf((Object) null)` returns `"null"`?

<details><summary>Answer</summary>

Overload resolution, not runtime behaviour. The literal `null` is assignable to both `String.valueOf(Object)` and `String.valueOf(char[])`, so both are applicable, and the JLS picks the most specific — `char[]` is a subtype of `Object`, so the `char[]` overload wins. Its body constructs a `String` from the array and dereferences it, throwing `NullPointerException` at runtime; the compiler never warns. Casting to `(Object)` removes `char[]` from the applicable set, selecting the `Object` overload, which is specified to return `"null"` for a null argument. The same shape bites `println(null)`.

</details>

---

**Leaves covered:** 1.10.1–1.10.23 (23 leaves)
**Leaves deferred:** none
**Diagrams included:** D-029, D-030, D-031
**Target version:** Java 21 LTS
**Lines:** 530
