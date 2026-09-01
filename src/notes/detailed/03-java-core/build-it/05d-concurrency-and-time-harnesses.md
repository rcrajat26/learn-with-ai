# 03 Java Core — Diagnostic harnesses — the `SimpleDateFormat` race, and the `DateTimeFormatter` that does not fail — BUILD IT (§4.8, leaf 4.8.9)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [The overload-resolution harness](05j-overload-resolution-harness.md) · Next: [The DST harness](05i-dst-harness.md)

---

## 4.8.9 The `SimpleDateFormat` race, reproduced with eight threads `[BUILD]` `[PROVE]` `[SOURCE]`

`SimpleDateFormat` keeps its working state **in a field**. `DateFormat` declares
`protected Calendar calendar`, and every `format` call does `calendar.setTime(date)` then reads field
after field back out of that same `Calendar`; every `parse` call fills a per-call `CalendarBuilder`
and then does `calb.establish(calendar)`, which clears the shared `Calendar` and repopulates it. A
second scratchpad sits beside it, `protected NumberFormat numberFormat`, whose minimum and maximum
integer digits are mutated in place for every numeric field written. So two threads calling `format`
on one instance are not racing on a flag you could make `volatile`; they are **two computations
sharing one scratchpad**. Thread A sets the calendar to its entry's instant, thread B overwrites it,
thread A reads back B's minutes and seconds, and emits a well-formed timestamp for a moment that
never happened.

The failure that matters is not the exception. It is the audit row that looks right.

### The mechanism in the JDK 21 source `[SOURCE]`

From `java.base/java/text/DateFormat.java` in JDK 21.0.7 `src.zip`, line 194:

```java
    protected Calendar calendar;
```

One field, `protected`, no synchronization, shared by every caller of the instance. The javadoc of
the same class, lines 143–151, documents the hazard itself:

```java
 * <h2><a id="synchronization">Synchronization</a></h2>
 *
 * <p>
 * Date formats are not synchronized.
 * It is recommended to create separate format instances for each thread.
 * If multiple threads access a format concurrently, it must be synchronized
 * externally.
 * @apiNote Consider using {@link java.time.format.DateTimeFormatter} as an
 * immutable and thread-safe alternative.
```

Line by line: "not synchronized" is the class admitting it holds mutable state; "separate format
instances for each thread" is fix 2 or 3 below; "synchronized externally" is fix 4; the `@apiNote` is
fix 1. The hazard has been documented since JDK 1.1 and a shared `static SimpleDateFormat` is still
one of the commonest bugs in Java — the documentation sits in the class nobody opens.

`SimpleDateFormat.java` line 977, in the private `format` every public `format` funnels into:

```java
    private StringBuffer format(Date date, StringBuffer toAppendTo,
                                FieldDelegate delegate) {
        // Convert input date to time field list
        calendar.setTime(date);
```

That is the write. Every pattern field is then served from the same object; line 1154, inside
`subFormat`:

```java
            value = calendar.get(field);
```

That is the read. Between line 977 and the last `calendar.get` there are as many reads as the pattern
has fields — for `yyyy-MM-dd'T'HH:mm:ss.SSS`, seven `get` calls, seven windows in which another
thread's `setTime` can land. `Calendar.get` also *computes* fields lazily (`complete` → `updateTime`
→ `GregorianCalendar.computeFields`), so a concurrent `setTime` can catch that recomputation
mid-flight, which is where the `ClassCastException` below comes from.

The `parse` side, lines 1478 and 1563:

```java
        CalendarBuilder calb = new CalendarBuilder();
```
```java
            parsedDate = calb.establish(calendar).getTime();
```

The `CalendarBuilder` is a per-call local, which is fine. Line 1563 is not: `establish` clears the
**shared** `calendar`, pushes the accumulated fields into it and calls `getTime()`, so two threads
arriving together resolve one `Calendar` holding a mixture of both field sets into a `Date`.

**Insight:** the bug is not "unsynchronized access to a field". One logical operation — format one
date — is a write followed by seven reads of one shared object, so it is not atomic, and no field
modifier can widen a critical section.

> A `SimpleDateFormat` instance is a scratchpad with a method interface: each call writes the
> scratchpad and then reads it back, so any two concurrent calls on the same instance compute over
> each other's intermediate state.

### The harness

Eight workers, named for what they do, formatting and parsing `FundsLedger` audit stamps. Every
result is checked against a reference rendering computed single-threaded before any worker starts,
so a wrong-but-plausible string is counted rather than missed. One harness runs six strategies — the
bug, two control experiments, three fixes — and keeps one stack trace per distinct exception type.

```java
public final class LedgerAuditRace {

    static final int WORKERS = 8;
    static final String PATTERN = "yyyy-MM-dd'T'HH:mm:ss.SSS";
    static final TimeZone UTC = TimeZone.getTimeZone("UTC");

    /** One ledger entry: the instant it was written, and the exact text it must render as. */
    record LedgerEntry(long epochMillis, String expectedText) {}

    /** What a FundsLedger audit writer has to be able to do. */
    interface AuditWriter {
        String render(long epochMillis) throws Exception;
        long readBack(String text) throws Exception;
    }

    /** A named way of obtaining an AuditWriter for one worker thread. */
    record Strategy(String name, Supplier<AuditWriter> perWorker) {}

    static SimpleDateFormat newLegacyFormat() {
        SimpleDateFormat f = new SimpleDateFormat(PATTERN);
        f.setTimeZone(UTC);
        return f;
    }

    /** The bug, exactly as production writes it: one static formatter, no lock. */
    static final SimpleDateFormat SHARED_LEGACY_STAMP = newLegacyFormat();

    static final AuditWriter SHARED_UNLOCKED = new AuditWriter() {
        public String render(long ms) { return SHARED_LEGACY_STAMP.format(new Date(ms)); }
        public long readBack(String t) throws ParseException {
            return SHARED_LEGACY_STAMP.parse(t).getTime();
        }
    };

    /** Fix 4: the same shared instance, every call inside a block synchronized on it. */
    static final AuditWriter SHARED_SYNCHRONIZED = new AuditWriter() {
        public String render(long ms) {
            synchronized (SHARED_LEGACY_STAMP) { return SHARED_LEGACY_STAMP.format(new Date(ms)); }
        }
        public long readBack(String t) throws ParseException {
            synchronized (SHARED_LEGACY_STAMP) { return SHARED_LEGACY_STAMP.parse(t).getTime(); }
        }
    };

    /** Fix 2: one instance per thread, reached through a ThreadLocal. */
    static final ThreadLocal<SimpleDateFormat> THREAD_LOCAL_STAMP =
            ThreadLocal.withInitial(LedgerAuditRace::newLegacyFormat);

    static final AuditWriter THREAD_LOCAL = new AuditWriter() {
        public String render(long ms) { return THREAD_LOCAL_STAMP.get().format(new Date(ms)); }
        public long readBack(String t) throws ParseException {
            return THREAD_LOCAL_STAMP.get().parse(t).getTime();
        }
    };

    /** Fix 3: a brand-new instance for every call. */
    static final AuditWriter FRESH_PER_CALL = new AuditWriter() {
        public String render(long ms) { return newLegacyFormat().format(new Date(ms)); }
        public long readBack(String t) throws ParseException {
            return newLegacyFormat().parse(t).getTime();
        }
    };

    /** Fix 1, the real one: one shared static DateTimeFormatter. */
    static final DateTimeFormatter SHARED_MODERN_STAMP =
            DateTimeFormatter.ofPattern(PATTERN).withZone(ZoneOffset.UTC);

    static final AuditWriter SHARED_MODERN = new AuditWriter() {
        public String render(long ms) { return SHARED_MODERN_STAMP.format(Instant.ofEpochMilli(ms)); }
        public long readBack(String t) {
            return SHARED_MODERN_STAMP.parse(t, LocalDateTime::from)
                                      .toInstant(ZoneOffset.UTC).toEpochMilli();
        }
    };

    /** Control experiment: an owned SimpleDateFormat, constructed once per worker thread. */
    static AuditWriter ownedLegacy() {
        SimpleDateFormat mine = newLegacyFormat();
        return new AuditWriter() {
            public String render(long ms) { return mine.format(new Date(ms)); }
            public long readBack(String t) throws ParseException { return mine.parse(t).getTime(); }
        };
    }

    static final List<Strategy> STRATEGIES = List.of(
            new Strategy("shared static SimpleDateFormat, no lock", () -> SHARED_UNLOCKED),
            new Strategy("one SimpleDateFormat per worker",         LedgerAuditRace::ownedLegacy),
            new Strategy("shared SimpleDateFormat, synchronized",   () -> SHARED_SYNCHRONIZED),
            new Strategy("ThreadLocal<SimpleDateFormat>",           () -> THREAD_LOCAL),
            new Strategy("new SimpleDateFormat per call",           () -> FRESH_PER_CALL),
            new Strategy("shared static DateTimeFormatter",         () -> SHARED_MODERN));

    /** 64 distinct ledger-entry timestamps and their reference renderings. */
    static LedgerEntry[] ledgerEntries() {
        DateTimeFormatter truth = DateTimeFormatter.ofPattern(PATTERN).withZone(ZoneOffset.UTC);
        long base = Instant.parse("2026-03-14T09:17:04.221Z").toEpochMilli();
        LedgerEntry[] entries = new LedgerEntry[64];
        for (int i = 0; i < entries.length; i++) {
            long ms = base + i * 4_207L;
            entries[i] = new LedgerEntry(ms, truth.format(Instant.ofEpochMilli(ms)));
        }
        return entries;
    }

    static final class Tally {
        final AtomicLong ok = new AtomicLong();
        final AtomicLong formatWrong = new AtomicLong();
        final AtomicLong parseWrong = new AtomicLong();
        final Map<String, AtomicInteger> thrown = new ConcurrentHashMap<>();
        /** One sample per distinct failure kind, so one loud kind cannot crowd out the rest. */
        final Map<String, String> sampleByKind = new ConcurrentHashMap<>();
        /** One full stack trace per distinct exception type. */
        final Map<String, String> traceByType = new ConcurrentHashMap<>();

        void threw(String op, Throwable t, String who) {
            thrown.computeIfAbsent(t.getClass().getSimpleName(), k -> new AtomicInteger())
                  .incrementAndGet();
            sampleByKind.putIfAbsent(op + "-" + t.getClass().getSimpleName(),
                    op + " threw " + t.getClass().getName() + ": "
                    + escape(String.valueOf(t.getMessage())) + "  on " + who);
            traceByType.computeIfAbsent(t.getClass().getName(), k -> {
                StringWriter sw = new StringWriter();
                t.printStackTrace(new PrintWriter(sw));
                return "thrown on " + who + "\n" + sw;
            });
        }
        long failures() { return formatWrong.get() + parseWrong.get() + threwTotal(); }
        long threwTotal() { return thrown.values().stream().mapToLong(AtomicInteger::get).sum(); }
    }

    static Tally runOnce(Strategy strategy, int iterations, LedgerEntry[] entries)
            throws InterruptedException {
        Tally tally = new Tally();
        CountDownLatch start = new CountDownLatch(1);
        CountDownLatch done = new CountDownLatch(WORKERS);
        for (int w = 0; w < WORKERS; w++) {
            final int workerIndex = w;
            Thread worker = new Thread(() -> {
                AuditWriter writer = strategy.perWorker().get();
                try { start.await(); }
                catch (InterruptedException e) { Thread.currentThread().interrupt(); return; }
                String who = Thread.currentThread().getName();
                for (int i = 0; i < iterations; i++) {
                    LedgerEntry entry = entries[(workerIndex * 7 + i) & 63];
                    try {
                        String text = writer.render(entry.epochMillis());
                        if (entry.expectedText().equals(text)) {
                            tally.ok.incrementAndGet();
                        } else {
                            tally.formatWrong.incrementAndGet();
                            tally.sampleByKind.putIfAbsent("format-wrong",
                                    "format wanted " + entry.expectedText()
                                    + "  got " + escape(text) + "  on " + who);
                        }
                    } catch (Throwable ex) {
                        tally.threw("format", ex, who);
                    }
                    try {
                        long ms = writer.readBack(entry.expectedText());
                        if (ms == entry.epochMillis()) {
                            tally.ok.incrementAndGet();
                        } else {
                            tally.parseWrong.incrementAndGet();
                            tally.sampleByKind.putIfAbsent("parse-wrong",
                                    "parse  wanted " + entry.epochMillis() + "  got " + ms
                                    + "  from " + entry.expectedText() + "  on " + who);
                        }
                    } catch (Throwable ex) {
                        tally.threw("parse", ex, who);
                    }
                }
                done.countDown();
            }, workerIndex == WORKERS - 1 ? "paymentRunWorker" : "ledgerAuditWorker" + workerIndex);
            worker.start();
        }
        start.countDown();
        done.await();
        return tally;
    }

    /** Never put a raw control byte into a report: corrupt output can hold anything. */
    static String escape(String s) {
        if (s == null) return "null";
        StringBuilder sb = new StringBuilder(s.length() + 8);
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c < 0x20 || c == 0x7f) sb.append(String.format("\\u%04x", (int) c));
            else sb.append(c);
        }
        return sb.toString();
    }

    public static void main(String[] args) throws Exception {
        int runs = args.length > 0 ? Integer.parseInt(args[0]) : 20;
        int iterations = args.length > 1 ? Integer.parseInt(args[1]) : 20_000;
        LedgerEntry[] entries = ledgerEntries();
        long opsPerRun = (long) WORKERS * iterations * 2;
        System.out.printf("runs=%d  workers=%d  iterations/worker=%d  -> %,d checked operations "
                + "per run (one format + one parse each)%n%n", runs, WORKERS, iterations, opsPerRun);

        for (Strategy strategy : STRATEGIES) {
            long ok = 0, formatWrong = 0, parseWrong = 0, threw = 0;
            long minFail = Long.MAX_VALUE, maxFail = 0;
            int badRuns = 0;
            Map<String, Integer> byType = new TreeMap<>();
            Map<String, String> samples = new TreeMap<>();
            Map<String, String> traces = new TreeMap<>();
            for (int r = 0; r < runs; r++) {
                Tally t = runOnce(strategy, iterations, entries);
                ok += t.ok.get();
                formatWrong += t.formatWrong.get();
                parseWrong += t.parseWrong.get();
                threw += t.threwTotal();
                long fail = t.failures();
                minFail = Math.min(minFail, fail);
                maxFail = Math.max(maxFail, fail);
                if (fail > 0) badRuns++;
                t.thrown.forEach((k, v) -> byType.merge(k, v.get(), Integer::sum));
                t.sampleByKind.forEach(samples::putIfAbsent);
                t.traceByType.forEach(traces::putIfAbsent);
            }
            System.out.printf("""
                    === %s ===
                      correct          %,13d of %,13d
                      silently wrong   %,13d   (format %,d, parse %,d)
                      threw            %,13d
                      failing runs     %d of %d   per-run failures %,d to %,d
                    """, strategy.name(), ok, runs * opsPerRun, formatWrong + parseWrong,
                    formatWrong, parseWrong, threw, badRuns, runs,
                    minFail == Long.MAX_VALUE ? 0 : minFail, maxFail);
            if (!byType.isEmpty()) System.out.println("  exception types  " + byType);
            samples.forEach((k, v) -> System.out.println("  sample: " + v));
            traces.forEach((k, v) -> System.out.println("---- " + k + " ----\n" + v));
            System.out.println();
        }
    }
}
```

Imports: `java.io.PrintWriter`, `StringWriter`; `java.text.ParseException`, `SimpleDateFormat`;
`java.time.Instant`, `LocalDateTime`, `ZoneOffset`, `format.DateTimeFormatter`; `java.util.Date`,
`List`, `Map`, `TimeZone`, `TreeMap`, `concurrent.ConcurrentHashMap`, `concurrent.CountDownLatch`,
`concurrent.atomic.AtomicInteger`, `concurrent.atomic.AtomicLong`, `function.Supplier`.

### What it printed

Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64 (Apple silicon), compressed oops on.
`javac -Xlint:all` compiled it with no output whatsoever. `java LedgerAuditRace 20 20000` — 20 runs
of 8 workers × 20,000 iterations, 320,000 checked operations per run, 6,400,000 per strategy:

```console
=== shared static SimpleDateFormat, no lock ===
  correct              3,506,620 of     6,400,000
  silently wrong       2,873,198   (format 2,394,716, parse 478,482)
  threw                   20,182
  failing runs     20 of 20   per-run failures 138,059 to 187,708
  exception types  {ArrayIndexOutOfBoundsException=3184, ClassCastException=7722, NumberFormatException=9276}
  sample: format threw java.lang.ArrayIndexOutOfBoundsException: Index -1 out of bounds for length 13  on ledgerAuditWorker3
  sample: format threw java.lang.ClassCastException: class sun.util.calendar.Gregorian$Date cannot be cast to class sun.util.calendar.JulianCalendar$Date (sun.util.calendar.Gregorian$Date and sun.util.calendar.JulianCalendar$Date are in module java.base of loader 'bootstrap')  on ledgerAuditWorker0
  sample: format wanted 2026-03-14T09:18:03.119  got 2026-03-14T09:19:31.466  on ledgerAuditWorker2
  sample: parse threw java.lang.ArrayIndexOutOfBoundsException: Index 12614 out of bounds for length 13  on ledgerAuditWorker3
  sample: parse threw java.lang.ClassCastException: class sun.util.calendar.Gregorian$Date cannot be cast to class sun.util.calendar.JulianCalendar$Date (sun.util.calendar.Gregorian$Date and sun.util.calendar.JulianCalendar$Date are in module java.base of loader 'bootstrap')  on ledgerAuditWorker6
  sample: parse threw java.lang.NumberFormatException: For input string: ""  on ledgerAuditWorker3
  sample: parse  wanted 1773479988294  got 1772237988294  from 2026-03-14T09:19:48.294  on ledgerAuditWorker5
```

The other five strategy blocks were identical apart from the heading: `correct 6,400,000 of
6,400,000`, `silently wrong 0   (format 0, parse 0)`, `threw 0`, `failing runs 0 of 20`.

Of 6,400,000 operations: 3,506,620 correct (54.8%), **2,873,198 silently wrong (44.9%)**, 20,182
thrown (0.32%) — silently wrong outnumbers thrown **142 to 1**, and 2,394,716 of 3,200,000 format
calls returned the wrong timestamp (**74.8%**) against 15.0% of parse calls.

`format wanted 2026-03-14T09:18:03.119 got 2026-03-14T09:19:31.466` is another worker's ledger entry
rendered under this worker's call: not garbage, a **valid timestamp for the wrong entry**. No
formatted string in any run came out malformed — the corruption swaps field *values*, never the
literal characters between them, so every wrong stamp still matched the pattern exactly. And
`parse wanted 1773479988294 got 1772237988294` is a parse that succeeded, threw nothing, and landed
**14.4 days early**: a `postedAt` that silently moves a row between reporting periods.

**Interview:** "What happens if two threads share a `SimpleDateFormat`?" — the expected answer is
"it throws"; the better answer is "it mostly does not throw, it returns a well-formed timestamp for
a different moment, on roughly three-quarters of format calls under eight-way contention."

Per-run extremes: **138,059 to 187,708 failures per run** of 320,000 operations, 43.1% to 58.7%,
with 20 of 20 runs failing. Repeating the sweep moves the totals — three sweeps gave 2,873,198,
2,865,235 and 2,827,575 silently-wrong results, with `ClassCastException` counts of 7,722, 3,549 and
5,407, and in shorter sweeps that type sometimes did not appear at all. The honest claim is a range:
**43–59% of operations wrong and 0.1–0.4% throwing.** `ArrayIndexOutOfBoundsException` also moves
*site* — `Calendar.getDisplayName` in this run, `DigitList.fitsIntoLong` in another.

`ParseException` and `NullPointerException` appeared in no run here, which is explicable rather than
lucky: `SimpleDateFormat` is lenient by default, so a corrupted field set is almost always still
*resolvable* into some `Date`, and `ParseException` is thrown only when `parse` returns `null`.
Treat the tail of this distribution as open.

### The stack traces `[PROVE]`

Same run, same harness. It printed three; two are quoted in full below. The third, the
`ArrayIndexOutOfBoundsException`, opened at `java.util.Calendar.getDisplayName(Calendar.java:2149)`
then `java.text.SimpleDateFormat.subFormat(SimpleDateFormat.java:1160)` — a field index of `-1` read
out of a 13-element array, because a concurrent `setTime` reset the field just validated.

```console
---- java.lang.ClassCastException ----
thrown on ledgerAuditWorker0
java.lang.ClassCastException: class sun.util.calendar.Gregorian$Date cannot be cast to class sun.util.calendar.JulianCalendar$Date (sun.util.calendar.Gregorian$Date and sun.util.calendar.JulianCalendar$Date are in module java.base of loader 'bootstrap')
	at java.base/sun.util.calendar.JulianCalendar.getCalendarDateFromFixedDate(JulianCalendar.java:186)
	at java.base/java.util.GregorianCalendar.computeFields(GregorianCalendar.java:2385)
	at java.base/java.util.GregorianCalendar.computeTime(GregorianCalendar.java:2787)
	at java.base/java.util.Calendar.updateTime(Calendar.java:3427)
	at java.base/java.util.Calendar.complete(Calendar.java:2293)
	at java.base/java.util.Calendar.get(Calendar.java:1858)
	at java.base/java.text.SimpleDateFormat.subFormat(SimpleDateFormat.java:1154)
	at java.base/java.text.SimpleDateFormat.format(SimpleDateFormat.java:1001)
	at java.base/java.text.SimpleDateFormat.format(SimpleDateFormat.java:971)
	at java.base/java.text.DateFormat.format(DateFormat.java:378)
	at LedgerAuditRace$1.render(LedgerAuditRace.java:54)
	at LedgerAuditRace.lambda$runOnce$5(LedgerAuditRace.java:171)
	at java.base/java.lang.Thread.run(Thread.java:1583)

---- java.lang.NumberFormatException ----
thrown on ledgerAuditWorker3
java.lang.NumberFormatException: For input string: ""
	at java.base/java.lang.NumberFormatException.forInputString(NumberFormatException.java:67)
	at java.base/java.lang.Long.parseLong(Long.java:719)
	at java.base/java.lang.Long.parseLong(Long.java:832)
	at java.base/java.text.DigitList.getLong(DigitList.java:196)
	at java.base/java.text.DecimalFormat.parse(DecimalFormat.java:2228)
	at java.base/java.text.SimpleDateFormat.subParse(SimpleDateFormat.java:1937)
	at java.base/java.text.SimpleDateFormat.parse(SimpleDateFormat.java:1545)
	at java.base/java.text.DateFormat.parse(DateFormat.java:397)
	at LedgerAuditRace$1.readBack(LedgerAuditRace.java:56)
	at LedgerAuditRace.lambda$runOnce$5(LedgerAuditRace.java:184)
	at java.base/java.lang.Thread.run(Thread.java:1583)
```

Neither carried a cause, so there are no JVM `... N more` fold lines in this capture.

Each trace names one of the two scratchpads. The `ClassCastException` is `calendar`: two threads
inside `computeFields` at once, one holding a `Gregorian$Date` where the other's recomputation
expects a `JulianCalendar$Date`. The `NumberFormatException` is `numberFormat`: `DigitList` is a
mutable digit buffer inside the shared `DecimalFormat`, and two interleaved fills leave it holding a
digit string — here the empty string — that `Long.parseLong` refuses.

### The two control experiments: state-sharing, not visibility `[PROVE]`

Both are strategies in the harness above, from the sweep just quoted, and both reported
6,400,000 of 6,400,000 correct with 0 failing runs: **(1)** give each worker its own instance
(`ownedLegacy()`), changing no formatter code and adding no barrier — only removing the sharing;
**(2)** keep one shared instance and wrap every call in `synchronized (SHARED_LEGACY_STAMP)`.

Together they settle the diagnosis. Experiment 1 would not have helped if the problem were a stale
read of a correctly-computed value — there would have been no second value to read. Experiment 2
keeps the sharing and adds mutual exclusion, which is what an invariant spanning several operations
on one object requires; a `volatile` publishes each write and still lets the reads interleave.

**Pitfall:** a shared `SimpleDateFormat` looks like a visibility bug because the symptom is "wrong
value read". It is an atomicity bug: the unit that must be atomic is the whole `format` call.

---

## The `DateTimeFormatter` version that does not fail `[BUILD]` `[SOURCE]`

One field and two call sites — strategy 6 in the harness:

```java
    static final DateTimeFormatter AUDIT_STAMP =
            DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss.SSS").withZone(ZoneOffset.UTC);

    String render(long ms) { return AUDIT_STAMP.format(Instant.ofEpochMilli(ms)); }

    long readBack(String text) {
        return AUDIT_STAMP.parse(text, LocalDateTime::from).toInstant(ZoneOffset.UTC).toEpochMilli();
    }
```

Same eight workers, same 6,400,000 checked operations, same twenty runs:
`correct 6,400,000 of 6,400,000`, `silently wrong 0`, `threw 0`, `failing runs 0 of 20`.

"It is immutable" is a label, not a mechanism. The mechanism, read out of
`java.base/java/time/format/DateTimeFormatter.java` in JDK 21.0.7 `src.zip`:

- **Every field is `final`.** Lines 521–545 declare exactly seven, all `private final`:
  `printerParser`, `locale`, `decimalStyle`, `resolverStyle`, `resolverFields`, `chrono`, `zone`.
  No `Calendar`, no `NumberFormat`, no digit buffer, no scratch field at all. `withZone`,
  `withLocale` and `withResolverStyle` return a **new** formatter rather than mutating this one,
  which is why `withZone(ZoneOffset.UTC)` chains onto the factory instead of acting as a setter.
- **`format` builds its state in locals.** Line 1877 is
  `StringBuilder buf = new StringBuilder(32); formatTo(temporal, buf); return buf.toString();`, and
  line 1903 inside `formatTo` is `new DateTimePrintContext(temporal, this)` — fresh objects per call,
  unreachable from the formatter, with `this` passed in read-only.
- **`parse` does the same.** Line 2097 in `parseResolved0` allocates a `ParsePosition`, line 2167 in
  `parseUnresolved0` allocates `new DateTimeParseContext(this)`, and all accumulated parse state
  lives in that per-call context.
- **The class's own `@implSpec`, line 512: `This class is immutable and thread-safe.`** The class is
  `final` (line 516), so no subclass can add a mutable field behind that guarantee.

The corollary is usable: **a `DateTimeFormatter` is correct as a `static final` field and a
`SimpleDateFormat` never is.** `private static final SimpleDateFormat` is a defect however long it
has sat in production without an incident report.

> `DateTimeFormatter` is thread-safe because a call has nowhere to write except its own locals: all
> seven of the formatter's fields are `final`, the class is `final`, and both `format` and `parse`
> allocate a fresh context per invocation.

`../date-and-time/02d-formatting-and-parsing.md` owns `DateTimeFormatter` and parsing as a topic,
`../date-and-time/03b-internals-temporal-spi-and-formatter.md` the printer-parser internals,
`../date-and-time/02-date-and-time.md` the `java.time` type map, and
`../date-and-time/03c-internals-precision-scale-and-legacy-bridging.md` `Date`/`Instant` bridging.
Guide 05 owns the memory model; guide 20 owns observability. Leaf 4.8.10 is
[The DST harness](05i-dst-harness.md).

---

## The four fixes, ranked, with what each costs

Cost figures come from a second run: the eight-worker `check` shape shown in the Pitfalls section
below, with the correctness comparison replaced by a wall-clock timer and a `volatile Object` sink,
500,000 calls per worker, one warm-up pass then one measured pass; allocation from
`com.sun.management.ThreadMXBean.getThreadAllocatedBytes` deltas over 500,000 calls after a
200,000-call warm-up. **This is not JMH** — no forking, no `Blackhole`, and the JIT's compilation
state is whatever it reached. `../cost-model/02-master-cost-table.md` owns the house harness.

```console
== eight workers, 500,000 format calls each, measured pass (NOT JMH) ==
  synchronized shared SimpleDateFormat        3,454,089 calls/sec  (   290 ns/call wall)
  ThreadLocal<SimpleDateFormat>               8,548,264 calls/sec  (   117 ns/call wall)
  new SimpleDateFormat per call               3,226,997 calls/sec  (   310 ns/call wall)
  shared static DateTimeFormatter            19,887,297 calls/sec  (    50 ns/call wall)
== allocation, ThreadMXBean deltas over 500,000 calls ==
  SimpleDateFormat.format, reused instance     632.0 bytes/call
  new SimpleDateFormat per call, then format  2440.0 bytes/call
  DateTimeFormatter.format                     304.0 bytes/call
  construct a SimpleDateFormat only           1720.0 bytes/call
```

**1. Migrate to `java.time` and `DateTimeFormatter` — the real fix.** Zero failures, 50 ns/call
under eight-way contention, 304 bytes/call, one shared `static final` field and no lock. The cost is
migration: `Date`/`Calendar` at the boundaries becomes `Instant`/`LocalDateTime`, which for an audit
writer is `Instant.ofEpochMilli` at the edge and nothing else.

**2. `ThreadLocal<SimpleDateFormat>`.** Zero failures, 117 ns/call, the fastest legacy fix — no lock
and no construction. Two honest costs: **one instance retained per thread for the thread's life**,
which at 1,720 bytes per formatter is about 344 KB on a 200-thread pool, small, but on a pooled
executor "the thread's life" is the pool's life and not the request's; and in a container that
reuses threads across redeployments, a `ThreadLocal` whose value's class came from the old
application classloader keeps that classloader alive — a real leak.
`../objects-equality-and-lifecycle/03a-finalization-cleanup-and-leaks.md` and guide 05 own
`ThreadLocal` leak mechanics.

**3. A new instance per call.** Zero failures, and the simplest change to review — delete the field,
inline the constructor. 310 ns/call under eight workers, 2,440 bytes of which 1,720 is the formatter
itself. Do not dismiss it on those numbers: at the ledger's **230/sec sustained** that is
230 × 310 ns ≈ **0.07 ms of CPU per second** and ≈ **561 KB/sec** of young-generation garbage; even
at the **13,600/sec peak**, 4.2 ms/sec and 33 MB/sec. It is only wrong inside a tight per-row loop
over the ledger's ~19.8M entries/day, where the 1,720-byte construction dominates the 632-byte
format.

**4. `synchronized`.** Zero failures — and the throughput argument against it **does not hold at this
domain's rates**: 3,454,089 format calls/sec across eight contending workers means the ledger's
13,600/sec peak consumes 13,600 ÷ 3,454,089 ≈ **0.39%** of the measured ceiling. The real objections
are elsewhere. It is a **single global monitor on the ledger write path**, so anything slow inside
the block adds latency to all 13,600/sec and couples the p99 to whatever else holds it; and it is
**not enforceable**, since one new call site that formats without the block reinstates the full
44.9% corruption rate with nothing failing at compile time.

| Fix | Correctness | Throughput (8 workers) | Retained memory | Migration cost |
|---|---|---|---|---|
| `DateTimeFormatter` | Correct by construction; the type cannot be misused | 19.9M calls/sec, 50 ns | One shared immutable formatter | Highest: `Date`/`Calendar` boundaries change |
| `ThreadLocal<SimpleDateFormat>` | Correct unless the instance escapes to another thread | 8.5M calls/sec, 117 ns | 1,720 bytes × threads for the pool's life; classloader-leak risk | Low: one field, one `.get()` |
| New instance per call | Correct, and unbreakable by a future caller | 3.2M calls/sec, 310 ns | None | Lowest: delete the field |
| `synchronized` on a shared instance | Correct only if every call site complies | 3.5M calls/sec, 290 ns | One instance | Lowest, but every call site must be found |

**Insight:** three of the four are "stop sharing the scratchpad" and one is "take turns on it". Only
the first kind can be enforced by the type system, which is why the ranking is not about nanoseconds.

---

## Catching it before it ships `[TRAP]`

**`javac` does not help.** Every program here compiled under `javac -Xlint:all` on JDK 21.0.7 with
**no output at all** — no warning for the `static SimpleDateFormat`, none for the concurrent calls
on it; `-Xlint` has no thread-safety category. Static analysis does catch it, with names verified
against the tools' own published catalogues:

| Tool | Check | Catches |
|---|---|---|
| SpotBugs (`StaticCalendarDetector`) | `STCAL_STATIC_SIMPLE_DATE_FORMAT_INSTANCE` | a `static` field of type `DateFormat` or a subclass |
| SpotBugs | `STCAL_INVOKE_ON_STATIC_DATE_FORMAT_INSTANCE` | a call on a static `DateFormat` instance |
| SpotBugs | `STCAL_STATIC_CALENDAR_INSTANCE`, `STCAL_INVOKE_ON_STATIC_CALENDAR_INSTANCE` | the same two, for `Calendar` |
| PMD (`category/java/multithreading.xml`) | `UnsynchronizedStaticFormatter` | a static `java.text.Format` used without a block-level lock |
| SonarQube | `java:S2885` — "Non-thread-safe fields should not be static" | `static` `Calendar`, `DateFormat`, `XPath`, `SchemaFactory` |

Note what all five key on: **`static`**. A `SimpleDateFormat` shared through the instance field of an
injected singleton bean is exactly as broken and matches none of them. Guide 16 owns tooling.

---

## Diff vs the real one

The contract rows are source facts from JDK 21.0.7 `src.zip`: `DateFormat extends Format`
(`DateFormat.java:182`) and `Format implements Serializable, Cloneable` (`Format.java:134`), so every
`SimpleDateFormat` is serializable and cloneable, while `DateTimeFormatter` is `final` (line 516) and
implements nothing. `ParseException extends Exception` (`ParseException.java:50`) is checked;
`DateTimeParseException extends DateTimeException` (line 76) `extends RuntimeException`
(`DateTimeException.java:75`) is not. And `DateTimeFormatter` guards its entry points —
`requireNonNull(text, "text")` at line 2007, `requireNonNull(temporal, "temporal")` at line 1900 —
where `SimpleDateFormat.parse(null)` fails later, inside `text.length()`.

| Axis | `SimpleDateFormat` (JDK 21) | `DateTimeFormatter` (JDK 21) |
|---|---|---|
| Mutable state | `DateFormat.calendar` and `DateFormat.numberFormat`, written on every call | none; seven `private final` fields, class `final` |
| Thread safety | none; 44.9% of 6.4M operations wrong under 8 workers | safe; 0 of 6.4M wrong under the same harness |
| Edge cases | lenient by default: month 13 rolls into January of the next year | `ResolverStyle.SMART` by default; month 13 rejected, naming field and range |
| Null policy | `format((Date) null)` → NPE "date must not be null"; `parse(null)` → NPE from inside `text.length()`, no `requireNonNull` | `requireNonNull` at each entry point, so the NPE names the parameter |
| Bad input | `ParseException`, **checked** — every caller needs a `try` or a `throws` | `DateTimeParseException`, **unchecked**, carrying `getErrorIndex()` |
| Serialization | `Serializable` via `Format`, dragging `Calendar`, `TimeZone`, `DateFormatSymbols` and a cloned `NumberFormat` into the stream | not `Serializable`; `writeObject` throws `NotSerializableException`, and `instanceof Serializable` is a **compile error** |
| Allocation per format | 632 bytes reused, 2,440 bytes if constructed per call (1,720 of that the formatter) | 304 bytes |
| Cost per format | 290 ns under 8 workers with a lock | 50 ns under 8 workers, unlocked |
| Intrinsics | none; plain Java over `StringBuffer` | none; plain Java over `StringBuilder` |
| Why the JDK bothered | — | JSR-310 replaced the whole API because the defect was structural: a formatter keeping per-call state in fields cannot be made thread-safe without a lock, and `Date`/`Calendar`'s mutability and lenient defaults were unfixable without breaking compatibility. `DateFormat`'s own `@apiNote` now points readers at `DateTimeFormatter`. |

## Pitfalls

### A `private static final SimpleDateFormat`

**Wrong**

```java
final class FundsLedgerAuditWriter {
    private static final SimpleDateFormat AUDIT_STAMP =
            new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS");
    String stamp(long epochMillis) { return AUDIT_STAMP.format(new Date(epochMillis)); }
}
```

`final` protects the *reference*, not the `Calendar` behind it. Eight workers, 6,400,000 checked
operations: 2,873,198 silently wrong, 20,182 thrown, 20 of 20 runs failing, 74.8% of format calls
returning a valid-looking timestamp for a different ledger entry.

**Right**

```java
final class FundsLedgerAuditWriter {
    private static final DateTimeFormatter AUDIT_STAMP =
            DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss.SSS").withZone(ZoneOffset.UTC);
    String stamp(long epochMillis) { return AUDIT_STAMP.format(Instant.ofEpochMilli(epochMillis)); }
}
```

Same harness: 6,400,000 of 6,400,000 correct, 0 thrown, 0 of 20 runs failing.

**Why people believe it:** `static final` is the idiom for a shared immutable constant and is
genuinely correct for `Pattern`, `DateTimeFormatter` and `BigDecimal`. `SimpleDateFormat` looks like
it belongs on that list, and nothing in its name, its API or its `final` declaration says it holds
per-call state.

### Believing `volatile`, or a `synchronized` method on your own wrapper, fixes it

**Wrong**

```java
/** Belief 1: `volatile` makes the shared formatter safe. */
static volatile SimpleDateFormat VOLATILE_STAMP = newLegacyFormat();

/** Belief 2: a `synchronized` method on my own wrapper makes it safe. */
static final class LedgerAuditWriter {
    private static final SimpleDateFormat AUDIT_STAMP = newLegacyFormat();
    synchronized String stamp(long epochMillis) { return AUDIT_STAMP.format(new Date(epochMillis)); }
}

// Driven by an eight-worker checked loop identical in shape to runOnce above — 200,000 iterations
// per worker, every result compared with the reference rendering:
check("volatile SimpleDateFormat field", (w, ms) -> VOLATILE_STAMP.format(new Date(ms)));

LedgerAuditWriter[] four = { new LedgerAuditWriter(), new LedgerAuditWriter(),
                             new LedgerAuditWriter(), new LedgerAuditWriter() };
check("synchronized method, 4 writer instances", (w, ms) -> four[w % four.length].stamp(ms));

LedgerAuditWriter one = new LedgerAuditWriter();
check("synchronized method, 1 writer instance", (w, ms) -> one.stamp(ms));

check("synchronized (LEGACY_STAMP) block", (w, ms) -> {
    synchronized (LEGACY_STAMP) { return LEGACY_STAMP.format(new Date(ms)); }
});
```

```console
== eight workers, 200000 format calls each ==
  volatile SimpleDateFormat field            wrong    593,131  threw       0  of  1,600,000 calls
  synchronized method, 4 writer instances    wrong    435,221  threw       0  of  1,600,000 calls
  synchronized method, 1 writer instance     wrong          0  threw       0  of  1,600,000 calls
  synchronized (LEGACY_STAMP) block          wrong          0  threw       0  of  1,600,000 calls
```

**Right** — lock the object that holds the state, or stop sharing it:

```java
    static String stamp(long epochMillis) {
        synchronized (LEGACY_STAMP) { return LEGACY_STAMP.format(new Date(epochMillis)); }
    }
```

`synchronized (LEGACY_STAMP)` is one monitor whatever the wrapper count — the fourth output line.

**Why people believe it:** both beliefs are half-right, the worst kind. `volatile` does fix
visibility, so it fixes the bug people *think* this is; it cannot fix atomicity, and the unit that
must be atomic is the whole `format` call. And a `synchronized` method genuinely is a lock — on
`this`, the wrapper, while the state lives in a `static` field shared by every wrapper. Four
wrappers means four monitors and four threads inside one `Calendar`, which is why the third line
(one wrapper, one monitor) reports 0 and the second reports 435,221: it passes the unit test that
creates one writer and fails behind a factory.

### Believing the race only produces exceptions

**Wrong**

```java
    String stamp(long epochMillis) {
        try {
            return SHARED_LEGACY_STAMP.format(new Date(epochMillis));   // shared, unlocked
        } catch (RuntimeException e) {
            return SAFE_FALLBACK.format(Instant.ofEpochMilli(epochMillis));
        }
    }
```

The `catch` is a monitoring plan dressed as a fix. Over 6,400,000 operations: 20,182 throws it would
see against 2,873,198 wrong values it cannot — **142 times more likely to be silent than loud** —
and every wrong string still matched `yyyy-MM-dd'T'HH:mm:ss.SSS`, so no regex or length check
downstream rejects it either.

**Right**

Verify against a reference value, not against whether something threw:

```java
    String expected = truth.format(Instant.ofEpochMilli(entry.epochMillis()));
    String actual = writer.render(entry.epochMillis());
    if (!expected.equals(actual)) { /* count it: this is the failure that matters */ }
```

which is what `LedgerAuditRace` does, and the only reason the 44.9% figure is visible at all.

**Why people believe it:** every race they debugged before announced itself with a
`ConcurrentModificationException` or obviously broken output, and the folk advice for
`SimpleDateFormat` is "you get weird exceptions" — accurate about the 0.32% that is easy to notice.

### Believing `SimpleDateFormat` rejects month 13

**Wrong**

```java
    SimpleDateFormat stamp = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS");
    Date postedAt = stamp.parse("2026-13-14T09:17:04.221");   // month 13 from an upstream feed
```

Run against all three formatters, this input prints:

```console
== month 13 on a ledger-entry timestamp ==
  SimpleDateFormat.isLenient()           : true
  legacy, lenient (the default)         -> returned Thu Jan 14 14:47:04 IST 2027
  legacy, setLenient(false)             -> java.text.ParseException: Unparseable date: "2026-13-14T09:17:04.221"
  modern, ResolverStyle.SMART (default) -> java.time.format.DateTimeParseException: Text '2026-13-14T09:17:04.221' could not be parsed: Invalid value for MonthOfYear (valid values 1 - 12): 13
```

No exception, and the extra month rolls the year forward: an eleven-month error on a ledger
timestamp. (`Date.toString` renders in the default zone, `IST` here, which is why 09:17 UTC prints
as 14:47; `../date-and-time/02a-instant-local-and-zoned.md` owns that.)

**Right**

```java
    DateTimeFormatter stamp = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss.SSS");
    LocalDateTime postedAt = stamp.parse("2026-13-14T09:17:04.221", LocalDateTime::from);
```

which throws `DateTimeParseException` naming the field and its valid range, as the last line above
shows. On the legacy class the equivalent is `stamp.setLenient(false)`.

**Why people believe it:** a parser that accepts `yyyy-MM-dd` and rejects `AA-801 ACTIVATED`
obviously validates its input, so range validation feels implied. `Calendar`'s lenient mode is a 1997
decision about *arithmetic* — `add(MONTH, 1)` on December must roll — that leaked into parsing, and
the default was never changed for compatibility.

## Cheat sheet

| Question | Answer |
|---|---|
| Why is it unsafe? | `DateFormat.calendar` and `DateFormat.numberFormat` are per-call scratchpads; `format` does one `setTime` then seven `calendar.get` calls |
| Visibility or atomicity? | Atomicity. A `volatile` field measured 593,131 wrong of 1,600,000 |
| `static final SimpleDateFormat` | Always a defect; `final` protects the reference only |
| Lenient by default? | `SimpleDateFormat` yes (month 13 → next January); `DateTimeFormatter` no (`ResolverStyle.SMART`) |
| Loud or silent? | Silent. 2,873,198 wrong vs 20,182 thrown per 6.4M ops (142:1) |
| Exceptions seen | `NumberFormatException`, `ClassCastException`, `ArrayIndexOutOfBoundsException`. Not `ParseException`, not NPE |
| Fix ranking (cost, 8 workers) | DTF > `ThreadLocal` > new-per-call > `synchronized`;  DTF 50 ns · `ThreadLocal` 117 ns · new-per-call 310 ns · `synchronized` 290 ns |
| Allocation per format | DTF 304 B · reused SDF 632 B · new-per-call 2,440 B (1,720 B is the instance) |
| Does `synchronized` fail at 13,600/sec? | No — 0.39% of the measured 3.45M/sec. It fails on enforceability and on being a global monitor |
| Static analysis | SpotBugs `STCAL_*`, PMD `UnsynchronizedStaticFormatter`, Sonar `java:S2885`. `javac -Xlint:all` says nothing |

---

## Self-test

**Q1.** Two threads share a `SimpleDateFormat`. Which is more likely: an exception, or a wrong
timestamp with no exception? By how much?

<details><summary>Answer</summary>

A wrong timestamp, by a factor of about 142. Over 6,400,000 checked operations with eight workers on
JDK 21.0.7 the harness counted 2,873,198 silently wrong results against 20,182 throws — 74.8% of the
3,200,000 format calls returned the wrong string, 15.0% of parse calls the wrong instant. Every
wrong string was still shaped like a valid `yyyy-MM-dd'T'HH:mm:ss.SSS` timestamp, so no regex,
length check or eyeball downstream distinguishes it from a correct one.

</details>

**Q2.** Why does making the field `volatile` not help?

<details><summary>Answer</summary>

Because the problem is atomicity, not visibility. `volatile` guarantees each read of the *reference*
sees the latest write, but the reference never changes — the mutation happens inside the object, and
one `format` call is a `calendar.setTime(date)` followed by seven `calendar.get(field)` calls for
this pattern. Another thread's `setTime` can land in any of those seven gaps, and `volatile` cannot
make eight operations on a shared object indivisible. Measured: 593,131 wrong of 1,600,000 calls,
no better than the plain field.

</details>

**Q3.** Which JDK fields are being raced, and how do the stack traces prove it?

<details><summary>Answer</summary>

Two: `DateFormat.calendar` (`protected Calendar calendar`, `DateFormat.java:194`) and
`DateFormat.numberFormat`. The traces separate them. The `ClassCastException`
(`Gregorian$Date cannot be cast to JulianCalendar$Date`) arrives through `Calendar.get` →
`complete` → `updateTime` → `GregorianCalendar.computeFields`, and the
`ArrayIndexOutOfBoundsException` through `Calendar.getDisplayName` with index `-1` on a 13-element
array: both `calendar`. The `NumberFormatException` arrives through `DigitList.getLong` inside
`DecimalFormat.parse`, so that one is `numberFormat`.

</details>

**Q4.** Why is `DateTimeFormatter` thread-safe? "It is immutable" is not an accepted answer.

<details><summary>Answer</summary>

Because a call has nowhere to write except its own locals. All seven fields — `printerParser`,
`locale`, `decimalStyle`, `resolverStyle`, `resolverFields`, `chrono`, `zone`, lines 521–545 — are
`private final`, and the class is `final`, so no subclass can add a mutable one. `format` allocates
`new StringBuilder(32)` and `formatTo` a `DateTimePrintContext` per call; `parse` goes through
`parseResolved0`, which allocates a `ParsePosition` and a `DateTimeParseContext`. The formatter is
passed into those contexts and only read; the `with*` methods return new formatters.

</details>

**Q5.** The ledger peaks at 13,600 writes/sec. Does `synchronized` around a shared
`SimpleDateFormat` meet that, and is it therefore acceptable?

<details><summary>Answer</summary>

It meets it comfortably and is still the worst of the four fixes. The eight-worker harness measured
3,454,089 format calls/sec through the lock, so 13,600/sec is about 0.39% of that ceiling. The real
objections: it puts a single global monitor on the ledger write path, so anything slow inside the
block adds latency to every writer's p99; and its correctness is unenforceable — one new call site
that forgets the block restores the full 44.9% corruption rate with no compile error and no test
failure.

</details>

---

## Open questions

- **Unverified:** the tail of the exception distribution. `ParseException` and `NullPointerException`
  did not appear in any run reported here. Whether they are reachable under this pattern at all, or
  only under patterns with text fields such as `MMM` or `zzz`, would be settled by re-running the
  harness across a matrix of patterns and locales at much higher iteration counts and by reading
  every `return null` path in `SimpleDateFormat.subParse`.
- **Unverified:** whether the 43–59% per-run corruption range and every timing figure hold off this
  one machine (Oracle JDK 21.0.7 build 21.0.7+8-LTS-245, macOS aarch64), since the rate depends on
  how the eight workers are scheduled. Re-running on x86-64 settles it.
- **Unverified:** the retained-heap cost of a `ThreadLocal<SimpleDateFormat>`. The 1,720 bytes quoted
  is *allocated* bytes from `ThreadMXBean` deltas, which bounds retained size from above without
  equalling it, since cached objects such as the `TimeZone` are shared. A heap dump settles it.

---

**Leaves covered:** 4.8.9 (1 leaf)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 897
