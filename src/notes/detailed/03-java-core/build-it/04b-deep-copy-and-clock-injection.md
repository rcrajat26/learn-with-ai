# 03 Java Core — Value-object builds — a deep-copy utility for a nested object graph — BUILD IT (§4.7.6)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [The two escape bugs, and a List component three ways](04a-defensive-copying-and-collections.md) · Next: [Clock injection and testable time](04f-clock-injection.md)

One build: a deep-copy utility for a nested `PaymentRun` graph, benchmarked against a
serialization round-trip. It is a `[BUILD]` item, so it closes with its own **Diff vs the real
one** table. The other §4.7 build, the `Clock`-injected `BonusExpiryService`, is
[Clock injection and testable time](04f-clock-injection.md); the section-wide §4.7 diff against
what a `record` gives you for free is
[The §4.7 diff against what a record gives you](04d-value-object-diff.md).

Everything below compiled and ran on **Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64
(Apple silicon)**, compressed oops on.

---

## 4.7.6 A deep-copy utility for a nested object graph `[NUM]`

Deep copy is a graph traversal, and every hard part of it is a graph problem, not an object
problem:

| Graph property | What a naive recursive copy does | The symptom in production |
|---|---|---|
| A **cycle** (parent holds child, child holds parent) | recurses forever | `StackOverflowError` in a batch job that passed its unit test |
| A **shared node** (two parents, one child) | copies it twice | two copies of one row drift apart — a data bug, not a slow path |
| **No stopping rule** | drags the heap in through one field | the "copy" pulls a `DataSource` or a `Logger` across |

The first two produce different failures and need the *same* fix. The third is a per-field design
decision no library can make for you.

**The shallow-copy limit, recapped once.** Order 23 closed on it: copying a collection copies the
**references** it holds, so `new ArrayList<>(source)` is a fresh list over the same elements, and a
mutable element is still shared with the caller. A deep copy is the transitive closure of that fix
— copy the container, then each element, then each element's mutable fields, until you reach
objects nobody can mutate. Shallow-versus-deep as a topic belongs to
[`../immutability-and-design/02a-shallow-deep-and-building-blocks.md`](../immutability-and-design/02a-shallow-deep-and-building-blocks.md)
and copying mechanics to
[`../objects-equality-and-lifecycle/02-copying-and-composite-equality.md`](../objects-equality-and-lifecycle/02-copying-and-composite-equality.md).

### The graph

A `PaymentRun` is a batch of approved bank withdrawals with operator sign-off. Two withdrawals in
one run can target the **same** `Instrument` — one client with one bank account withdrawing twice —
which gives the shared node; every `WithdrawalTransaction` holds a back-reference to its run, which
gives the cycle. Every node is mutable on purpose: that is the situation deep copy exists for.

```java
public record MoneyMinor(long units, String currencyCode) implements Serializable {
    public MoneyMinor {
        if (units < 0) throw new IllegalArgumentException("negative units: " + units);
        if (currencyCode == null || currencyCode.length() != 3)
            throw new IllegalArgumentException("bad currency: " + currencyCode);
    }
}

/** A shared node: two withdrawals in the same run can target the same bank instrument. */
public final class Instrument implements Serializable {
    final String instrumentId;
    final String last4;
    final List<String> verificationHistory;   // mutable

    Instrument(String instrumentId, String last4, List<String> verificationHistory) {
        this.instrumentId = instrumentId;
        this.last4 = last4;
        this.verificationHistory = new ArrayList<>(verificationHistory);
    }

    @Override public String toString() {
        return "Instrument[" + instrumentId + " ****" + last4 + " " + verificationHistory + "]";
    }
}

public final class WithdrawalTransaction implements Serializable {
    final String transactionId;
    final MoneyMinor amount;
    Instrument instrument;                 // shared node
    final List<String> statusHistory;      // mutable
    PaymentRun run;                        // back-reference: the cycle

    WithdrawalTransaction(String transactionId, MoneyMinor amount, Instrument instrument,
                          List<String> statusHistory) {
        this.transactionId = transactionId;
        this.amount = amount;
        this.instrument = instrument;
        this.statusHistory = new ArrayList<>(statusHistory);
    }
}

/** Deliberately NOT Serializable: it holds an operator session, not data. */
public final class OperatorSignoff {
    final String operatorId;
    OperatorSignoff(String operatorId) { this.operatorId = operatorId; }
    @Override public String toString() { return "OperatorSignoff[" + operatorId + "]"; }
}

public final class PaymentRun implements Serializable {
    final String runId;
    final List<WithdrawalTransaction> transactions = new ArrayList<>();
    transient OperatorSignoff signoff;     // transient: see the loss demo

    PaymentRun(String runId, OperatorSignoff signoff) {
        this.runId = runId;
        this.signoff = signoff;
    }

    void add(WithdrawalTransaction tx) {
        transactions.add(tx);
        tx.run = this;                     // closes the cycle
    }
}
```

### Strategy 1: hand-written, with an `IdentityHashMap` seen-map

Three lines per type: look the source node up in a map keyed by *reference identity*; if it is
there, return the copy already made; otherwise create the shell, **put it in the map before
recursing**, then fill it. Registering before recursing is what terminates the cycle — when the
recursion comes back round to the run, the map already holds its half-built copy. It must be
`IdentityHashMap`, not `HashMap`: the key question is "is this the same object", not "is this an
equal object", two `Instrument`s with equal fields are two nodes and must stay two nodes, and a
half-built shell's `hashCode` may not be stable yet.

```java
/**
 * Hand-written deep copy of the PaymentRun graph. The seen-map is keyed by reference identity,
 * so a node reached twice is copied once: that preserves sharing AND terminates cycles.
 */
public final class DeepCopy {

    private DeepCopy() {}

    public static PaymentRun deepCopy(PaymentRun src) {
        return copyRun(src, new IdentityHashMap<>());
    }

    static PaymentRun copyRun(PaymentRun src, Map<Object, Object> seen) {
        if (src == null) return null;
        PaymentRun already = (PaymentRun) seen.get(src);
        if (already != null) return already;

        PaymentRun copy = new PaymentRun(src.runId, src.signoff);   // immutable id holder: share it
        seen.put(src, copy);                                        // register BEFORE recursing
        for (WithdrawalTransaction tx : src.transactions) {
            WithdrawalTransaction txCopy = copyTx(tx, seen);
            copy.transactions.add(txCopy);
            txCopy.run = copy;
        }
        return copy;
    }

    static WithdrawalTransaction copyTx(WithdrawalTransaction src, Map<Object, Object> seen) {
        if (src == null) return null;
        WithdrawalTransaction already = (WithdrawalTransaction) seen.get(src);
        if (already != null) return already;

        // amount is a record over a long and a String: immutable, so share it, never copy it
        WithdrawalTransaction copy = new WithdrawalTransaction(
                src.transactionId, src.amount, null, src.statusHistory);
        seen.put(src, copy);
        copy.instrument = copyInstrument(src.instrument, seen);
        copy.run = copyRun(src.run, seen);
        return copy;
    }

    static Instrument copyInstrument(Instrument src, Map<Object, Object> seen) {
        if (src == null) return null;
        Instrument already = (Instrument) seen.get(src);
        if (already != null) return already;
        Instrument copy = new Instrument(src.instrumentId, src.last4,
                new ArrayList<>(src.verificationHistory));
        seen.put(src, copy);
        return copy;
    }

    /** The same traversal with no seen-map. Written to be run, not to be used. */
    public static PaymentRun naiveCopy(PaymentRun src, boolean followBackReference) {
        PaymentRun copy = new PaymentRun(src.runId, src.signoff);
        for (WithdrawalTransaction tx : src.transactions) {
            WithdrawalTransaction txCopy = new WithdrawalTransaction(
                    tx.transactionId, tx.amount,
                    new Instrument(tx.instrument.instrumentId, tx.instrument.last4,
                            new ArrayList<>(tx.instrument.verificationHistory)),
                    tx.statusHistory);
            // no map, so the shared instrument is copied twice and the cycle never terminates
            txCopy.run = followBackReference ? naiveCopy(tx.run, true) : copy;
            copy.transactions.add(txCopy);
        }
        return copy;
    }
}
```

Two decisions answer the "where does recursion stop" question. `amount` is a `MoneyMinor` record
over a `long` and a `String`, so it is immutable and is **shared, not copied** — copying it
allocates for nothing. `signoff` is an immutable identifier holder and is shared too. Every
immutable node you can name is a subtree the traversal never enters.

```java
public final class SharedNodeDemo {

    static PaymentRun sampleRun() {
        Instrument shared = new Instrument("INS-4417", "8842", List.of("BANK_VERIFIED"));
        PaymentRun run = new PaymentRun("PR-2026-08-29-W1", new OperatorSignoff("OP-207"));
        run.add(new WithdrawalTransaction("WTX-9001", new MoneyMinor(26000, "GBP"), shared, List.of("PENDING_VERIFICATION")));
        run.add(new WithdrawalTransaction("WTX-9002", new MoneyMinor(18050, "GBP"), shared, List.of("PENDING_VERIFICATION")));
        return run;
    }

    public static void main(String[] args) {
        PaymentRun run = sampleRun();
        System.out.println("source sharing:      "
                + (run.transactions.get(0).instrument == run.transactions.get(1).instrument));

        PaymentRun naive = DeepCopy.naiveCopy(run, false);
        System.out.println("naive copy sharing:  "
                + (naive.transactions.get(0).instrument == naive.transactions.get(1).instrument));
        naive.transactions.get(0).instrument.verificationHistory.add("RE_VERIFIED");
        System.out.println("  tx1 instrument: " + naive.transactions.get(0).instrument);
        System.out.println("  tx2 instrument: " + naive.transactions.get(1).instrument);

        PaymentRun deep = DeepCopy.deepCopy(run);
        System.out.println("deep copy sharing:   "
                + (deep.transactions.get(0).instrument == deep.transactions.get(1).instrument));
        System.out.println("deep copy is fresh:  "
                + (deep.transactions.get(0).instrument != run.transactions.get(0).instrument));
        deep.transactions.get(0).instrument.verificationHistory.add("RE_VERIFIED");
        System.out.println("  tx1 instrument: " + deep.transactions.get(0).instrument);
        System.out.println("  tx2 instrument: " + deep.transactions.get(1).instrument);
        System.out.println("  source untouched: " + run.transactions.get(0).instrument);

        System.out.println("cycle intact:        "
                + (deep.transactions.get(0).run == deep && deep.transactions.get(1).run == deep));

        try {
            DeepCopy.naiveCopy(run, true);
            System.out.println("naive copy with the cycle: returned normally");
        } catch (StackOverflowError e) {
            System.out.println("naive copy with the cycle: " + e.getClass().getName());
        }
    }
}
```

```console
source sharing:      true
naive copy sharing:  false
  tx1 instrument: Instrument[INS-4417 ****8842 [BANK_VERIFIED, RE_VERIFIED]]
  tx2 instrument: Instrument[INS-4417 ****8842 [BANK_VERIFIED]]
deep copy sharing:   true
deep copy is fresh:  true
  tx1 instrument: Instrument[INS-4417 ****8842 [BANK_VERIFIED, RE_VERIFIED]]
  tx2 instrument: Instrument[INS-4417 ****8842 [BANK_VERIFIED, RE_VERIFIED]]
  source untouched: Instrument[INS-4417 ****8842 [BANK_VERIFIED]]
cycle intact:        true
naive copy with the cycle: java.lang.StackOverflowError
```

**Insight:** the naive copy's failure is not "slower". Re-verifying `INS-4417` on `WTX-9001` left
`WTX-9002` reading `[BANK_VERIFIED]`, so one instrument now carries two verification histories
inside one payment run — nothing throws, nothing logs, and the operator signing the run sees
whichever the screen happened to load. The seen-map turns that into `true` on line 5.

> **Deep copy is a graph traversal with a memo table: an identity-keyed map from source node to
> copied node, populated before the recursion descends, is simultaneously the fix for shared nodes
> and the fix for cycles.**

### Strategy 2: a serialization round-trip

```java
/** Deep copy by serialization round-trip. Cycles and shared nodes come for free. */
public final class SerialCopy {

    private SerialCopy() {}

    public static byte[] toBytes(Serializable graph) throws IOException {
        ByteArrayOutputStream sink = new ByteArrayOutputStream(1 << 16);
        try (ObjectOutputStream out = new ObjectOutputStream(sink)) {
            out.writeObject(graph);
        }
        return sink.toByteArray();
    }

    @SuppressWarnings("unchecked")
    public static <T extends Serializable> T fromBytes(byte[] bytes)
            throws IOException, ClassNotFoundException {
        try (ObjectInputStream in = new ObjectInputStream(new ByteArrayInputStream(bytes))) {
            return (T) in.readObject();
        }
    }

    public static <T extends Serializable> T roundTrip(T graph)
            throws IOException, ClassNotFoundException {
        return fromBytes(toBytes(graph));
    }

    /** Big-endian 8-byte patch of one long value in a serialized stream. */
    public static void patchLong(byte[] stream, long from, long to) {
        byte[] needle = eightBytes(from);
        int at = -1, hits = 0;
        for (int i = 0; i + 8 <= stream.length; i++) {
            boolean match = true;
            for (int j = 0; j < 8; j++) {
                if (stream[i + j] != needle[j]) { match = false; break; }
            }
            if (match) { hits++; at = i; }
        }
        if (hits != 1) throw new IllegalStateException("expected 1 occurrence of " + from
                + " in the stream, found " + hits);
        System.arraycopy(eightBytes(to), 0, stream, at, 8);
    }

    private static byte[] eightBytes(long v) {
        byte[] b = new byte[8];
        for (int i = 0; i < 8; i++) b[i] = (byte) (v >>> (56 - 8 * i));
        return b;
    }
}
```

**Why it handles cycles and sharing for free.** `ObjectOutputStream` keeps its own identity map, a
handle table. The first time it meets an object it writes `TC_OBJECT`, the class descriptor and the
field data, and assigns the object the next handle (numbering starts at `0x7E0000`); the second
time it meets the *same reference* it writes `TC_REFERENCE` plus that handle, four bytes and
nothing else. `ObjectInputStream` keeps the mirror table and resolves the back-reference to the
object it already built. That is exactly the `IdentityHashMap` of strategy 1, implemented once
inside the JDK — the honest reason people reach for the round-trip, and a good one. Four costs
follow.

**Cost 1: every class in the graph must be `Serializable`, and the failure is at runtime.** With
`signoff` non-`transient`:

```text
java.io.NotSerializableException: OperatorSignoff
	at java.base/java.io.ObjectOutputStream.writeObject0(ObjectOutputStream.java:1200)
	at java.base/java.io.ObjectOutputStream.defaultWriteFields(ObjectOutputStream.java:1585)
	at java.base/java.io.ObjectOutputStream.writeSerialData(ObjectOutputStream.java:1542)
	at java.base/java.io.ObjectOutputStream.writeOrdinaryObject(ObjectOutputStream.java:1451)
	at java.base/java.io.ObjectOutputStream.writeObject0(ObjectOutputStream.java:1194)
	at java.base/java.io.ObjectOutputStream.writeObject(ObjectOutputStream.java:358)
	at SerialCopy.toBytes(SerialCopy.java:16)
	at NotSerializableDemo.main(NotSerializableDemo.java:9)
```

Nothing in the type system predicted this. `toBytes` takes `Serializable` and `PaymentRun` is
`Serializable`; the compiler cannot see one field five frames down. Adding a `Logger`, a
`DataSource` or a Spring proxy to any node breaks the copy in production, not in the build.

**Cost 2: `transient` makes it a lossy copy, silently.** The fix for cost 1 is `transient`, and now
the round-trip returns a run with no sign-off. Bank withdrawals require operator sign-off by domain
rule; the copy has lost the field that proves it, and again nothing throws:

```console
stream size: 651 bytes
sharing preserved:  true
cycle preserved:    true
fresh nodes:        true
source signoff:     OperatorSignoff[OP-207]
copy   signoff:     null   <-- transient, silently lost
```

**Cost 3: `readObject` runs no constructor, so every invariant you enforce in one is unenforced.**
The sharpest cost. `StakeSplit` as an ordinary class with the domain invariant — the two portions
summing exactly to the stake, the canonical 3.33 splitting as 0.33 bonus + 3.00 cash, in minor
units 333 = 33 + 300:

```java
/** Ordinary class, invariant enforced in the constructor: the two portions sum to the stake. */
public final class StakeSplit implements Serializable {
    static int constructions = 0;

    private final long bonusUnits;
    private final long cashUnits;
    private final long stakeUnits;

    StakeSplit(long stakeUnits, long bonusUnits, long cashUnits) {
        if (bonusUnits + cashUnits != stakeUnits)
            throw new IllegalArgumentException(
                    "split " + bonusUnits + "+" + cashUnits + " != stake " + stakeUnits);
        this.stakeUnits = stakeUnits;
        this.bonusUnits = bonusUnits;
        this.cashUnits = cashUnits;
        constructions++;
    }

    long created() { return bonusUnits + cashUnits - stakeUnits; }

    @Override public String toString() {
        return "StakeSplit[stake=" + stakeUnits + " bonus=" + bonusUnits
                + " cash=" + cashUnits + "]";
    }
}
```

One valid `StakeSplit` serializes to 93 bytes. Described rather than pasted: bytes 0–1 are the
magic `0xAC 0xED`, bytes 2–3 the version `0x00 0x05`, then `TC_OBJECT` `0x73`, `TC_CLASSDESC`
`0x72`, the name `StakeSplit`, its computed `serialVersionUID`, and three field descriptors each
introduced by the type code `0x4A` — `'J'`, the JVM descriptor letter for `long` — named
`bonusUnits`, `cashUnits`, `stakeUnits`. **Primitive fields are written in field-name alphabetical
order**, which is why `bonusUnits` comes first though the constructor takes the stake first. The
three values follow as eight big-endian bytes each at offsets `0x45`, `0x4D`, `0x55`: 33, 300, 333.
Patching `0x45` from 33 to 34 is what the rounding rule forbids — rounding the bonus portion up
gives 0.34 + 3.00 = 3.34 against a 3.33 stake, creating a penny:

```console
valid split:        StakeSplit[stake=333 bonus=33 cash=300]  created=0
round-tripped:      StakeSplit[stake=333 bonus=33 cash=300]
constructor calls during readObject: 0
tampered split:     StakeSplit[stake=333 bonus=34 cash=300]
money created:      1 minor units
```

Line 3 is the mechanism, line 5 the consequence: **zero** constructor invocations across the whole
round-trip, so the sum check never ran, and a `final` field now holds a value its constructor would
have rejected. [`../serialization/02-serialization.md`](../serialization/02-serialization.md) owns
serialization, including the constructor-bypass allocation path and the `readObject` /
`readResolve` hooks that are your only place to re-check.

Records are the exception, and the contrast is worth running. Record deserialization invokes the
**canonical constructor** with the stream's component values, so `MoneyMinor`'s check fires — same
tamper, record target:

```console
record rejected:    java.io.InvalidObjectException: negative units: -333
  caused by:        java.lang.IllegalArgumentException: negative units: -333
```

That asymmetry — an ordinary class silently accepting a state its constructor forbade, a record
rejecting it — is one of the strongest arguments for making value objects records, and
[The §4.7 diff against what a record gives you](04d-value-object-diff.md) takes it further: it
proves that `readObject` is ignored on a record, and that `readResolve` is honoured but unreachable
once the canonical constructor has thrown.

**Cost 4:** deserializing untrusted bytes is a remote-code-execution surface via `readObject`
gadget chains on the classpath — guide 13's territory and
[`../serialization/02-serialization.md`](../serialization/02-serialization.md)'s. It does not apply
to bytes you produced yourself a microsecond earlier, and it is why the technique must never be
reachable from an endpoint.

### The benchmark `[NUM]`

```java
/**
 * Not JMH: no forking, no Blackhole, one JVM, whatever compilation state the JIT reaches.
 * Relative comparison inside one run is the only thing claimed.
 */
public final class CopyBenchmark {

    static final int TX_PER_RUN = 1_750;      // 7,000 bank withdrawals a day over 4 windows
    static final int INSTRUMENTS = 500;       // each instrument is a shared node
    static final int WARMUP = 20;
    static final int ITERATIONS = 100;

    static volatile Object sink;

    static PaymentRun buildRun() {
        List<Instrument> instruments = new ArrayList<>(INSTRUMENTS);
        for (int i = 0; i < INSTRUMENTS; i++) {
            instruments.add(new Instrument("INS-" + (4000 + i), "8842",
                    List.of("BANK_VERIFIED")));
        }
        PaymentRun run = new PaymentRun("PR-2026-08-29-W1", new OperatorSignoff("OP-207"));
        for (int i = 0; i < TX_PER_RUN; i++) {
            run.add(new WithdrawalTransaction("WTX-" + (9000 + i),
                    new MoneyMinor(26000, "GBP"), instruments.get(i % INSTRUMENTS),
                    List.of("PENDING_VERIFICATION")));
        }
        return run;
    }

    static long allocatedBytes() {
        ThreadMXBean bean = (ThreadMXBean) ManagementFactory.getThreadMXBean();
        return bean.getThreadAllocatedBytes(Thread.currentThread().threadId());
    }

    public static void main(String[] args) throws Exception {
        PaymentRun run = buildRun();
        int nodes = 1 + TX_PER_RUN + INSTRUMENTS;
        System.out.println("graph: 1 PaymentRun + " + TX_PER_RUN + " WithdrawalTransaction + "
                + INSTRUMENTS + " Instrument = " + nodes + " domain nodes");
        System.out.println("serialized size: " + SerialCopy.toBytes(run).length + " bytes");

        for (int i = 0; i < WARMUP; i++) { sink = DeepCopy.deepCopy(run); sink = SerialCopy.roundTrip(run); }

        long a0 = allocatedBytes();
        long t0 = System.nanoTime();
        for (int i = 0; i < ITERATIONS; i++) sink = DeepCopy.deepCopy(run);
        long handNanos = System.nanoTime() - t0;
        long handBytes = allocatedBytes() - a0;

        long a1 = allocatedBytes();
        long t1 = System.nanoTime();
        for (int i = 0; i < ITERATIONS; i++) sink = SerialCopy.roundTrip(run);
        long serialNanos = System.nanoTime() - t1;
        long serialBytes = allocatedBytes() - a1;

        System.out.printf("hand-written deepCopy: %8.3f ms/copy   %,12d bytes/copy%n",
                handNanos / 1e6 / ITERATIONS, handBytes / ITERATIONS);
        System.out.printf("serialization  copy:   %8.3f ms/copy   %,12d bytes/copy%n",
                serialNanos / 1e6 / ITERATIONS, serialBytes / ITERATIONS);
        System.out.printf("ratio:                 %8.1fx time      %13.1fx bytes%n",
                (double) serialNanos / handNanos, (double) serialBytes / handBytes);
    }
}
```

The graph is one payout window: 1,750 `WithdrawalTransaction` (7,000 bank withdrawals a day across
4 banking-partner payout windows) over 500 shared `Instrument` nodes, 2,251 domain nodes, 139,726
bytes serialized. Allocation is `ThreadMXBean.getThreadAllocatedBytes` deltas over 100 iterations
after 20 warm-up iterations, and **this is not JMH** — no forking, no `Blackhole`, a `volatile` sink
and nothing more. [`../cost-model/02-master-cost-table.md`](../cost-model/02-master-cost-table.md)
owns the canonical harness; this is that harness, not a competing one.

Default JIT:

```console
graph: 1 PaymentRun + 1750 WithdrawalTransaction + 500 Instrument = 2251 domain nodes
serialized size: 139726 bytes
hand-written deepCopy:    0.466 ms/copy        287,959 bytes/copy
serialization  copy:      2.432 ms/copy      3,557,572 bytes/copy
ratio:                      5.2x time               12.4x bytes
```

`-XX:-DoEscapeAnalysis`, so C2 cannot scalar-replace anything the count depends on:

```console
hand-written deepCopy:    0.527 ms/copy        287,959 bytes/copy
serialization  copy:      2.187 ms/copy      3,600,284 bytes/copy
ratio:                      4.2x time               12.5x bytes
```

The arithmetic: 287,959 / 2,251 = **~128 B allocated per node copied** by hand, identical under
both JIT configurations — expected, since nothing here is a short-lived non-escaping object, every
node copied is stored into a live graph. The serialization route allocates 3,557,572 / 139,726 =
**~25.5 bytes per byte of stream produced**: the stream itself, the block-data buffer, the handle
table, the `ObjectStreamClass` descriptors, and every intermediate on the read side.

**A prediction that did not hold.** The expectation going in was one to two orders of magnitude on
time. Five runs measured **4.2x to 5.3x**, with the byte ratio a stable 12.4x–12.5x. Reporting that
rather than adjusting the claim: 20 warm-up plus 100 measured round-trips of a 140 KB stream is
enough for C2 to compile the field-copy paths `ObjectStreamClass` sets up, so serialization is not
paying interpreted reflection costs; and the hand-written copy is not free either, at 2,251
allocations plus 2,251 `IdentityHashMap` insertions and lookups. The **allocation** ratio is the
number to quote: stable across runs and across JIT configurations, causally clear, and the one that
reaches a GC log.

**Scaled to the domain, then the honest conclusion.** 7,000 bank withdrawals a day in 4
`PaymentRun` windows is 4 copies of this graph per day: 9.7 ms/day of serialization copying against
1.8 ms/day hand-written, 14 MB/day of allocation against 1.2 MB/day. Neither decides anything. At
this rate the round-trip is fast enough and choosing it would be defensible **on performance** —
what disqualifies it is costs 1 through 4, every one of which is a correctness or security cost.
Separating those two axes is what the question is really testing. The 5x would start to matter at
stake-settlement rates, 2.8M/day and 3,400/sec in burst, which is exactly where nobody deep-copies
anything.

### Diff vs the real one

The JDK's own copying mechanisms: `Object.clone` plus `Cloneable`, and `ObjectOutputStream` as a
graph walker.

| Axis | This build | The real JDK mechanism |
|---|---|---|
| Edge cases | cycles and shared nodes handled by the seen-map; `null` handled at every entry; depth bounded by graph depth, not node count | `Object.clone()` handles none of them — it is a **shallow** field-for-field copy; `ObjectOutputStream` handles both, via its per-stream handle table |
| Intrinsics | none; plain allocation and field stores | `Object.clone()` is `@IntrinsicCandidate` native, and C2 intrinsifies array clone into a bulk copy — a hand-written copier has no such path |
| Serialization | serialization used *as* the copy mechanism; the hand-written path is independent of it | the stream carries class descriptors, `serialVersionUID` and a handle table, all overhead a copy does not need |
| Null policy | explicit `null` in, `null` out at every level | `clone()` throws `NullPointerException` on a null receiver like any instance call; `writeObject(null)` writes `TC_NULL` and round-trips to `null` |
| Thread safety | none: concurrent mutation during the traversal yields a torn copy; the caller must hold the graph still | the same for both JDK mechanisms, and `ObjectOutputStream` will additionally surface a `ConcurrentModificationException` from a collection's own writer |
| Allocation tricks | shares immutable nodes (`MoneyMinor`, `OperatorSignoff`); ~128 B/node measured | the round-trip allocates the block buffer, the handle table, a cached `ObjectStreamClass` per class and the byte array: ~25.5 bytes per stream byte |
| Why the JDK bothers | it does not — there is no `deepCopy` in the JDK, on purpose | `Cloneable` is a known design mistake: the interface declares **no** `clone` method so it cannot be called through the interface type, `clone()` is shallow, and `CloneNotSupportedException` is checked with no recovery a caller can perform. `ObjectOutputStream` exists for persistence and RPC; copying is a side effect people discovered |

### The recommendation this leaf is actually about

**Do not deep-copy at all if you can make the graph immutable.** An immutable graph needs no copy:
the "copy" is the same reference, sharing is free and correct, cycles cannot be built through final
fields, and there is nothing for a caller to mutate behind your back. That is why order 21 spent
its effort on `Money` and `MoneyMinor` as records, and order 23 on `List.copyOf` components, rather
than on a copier. Deep copy is what you do when you have inherited a mutable graph you cannot
change — a JPA entity graph, a legacy DTO tree, a bean hierarchy generated by a tool.

Three one-liners. **Record "wither" methods** (`withStatus(String)` returning a new instance with
one component changed) give mutation-shaped ergonomics on an immutable node at one allocation per
change instead of a whole-graph traversal — [04d](04d-value-object-diff.md). **`Cloneable` is
unsuitable** for anything nested: `clone()` is shallow, the interface declares no `clone` method,
and `CloneNotSupportedException` is checked for nothing —
[`../objects-equality-and-lifecycle/01c-object-methods.md`](../objects-equality-and-lifecycle/01c-object-methods.md).
**A copy constructor or static copy factory** is the recommended replacement for `clone()`, and is
what `DeepCopy` above is with a seen-map bolted on to make it graph-safe.

---

## Pitfalls

### A naive recursive deep copy duplicating a shared node

**Wrong**

```java
WithdrawalTransaction txCopy = new WithdrawalTransaction(
        tx.transactionId, tx.amount,
        new Instrument(tx.instrument.instrumentId, tx.instrument.last4,
                new ArrayList<>(tx.instrument.verificationHistory)),
        tx.statusHistory);
```

```console
naive copy sharing:  false
  tx1 instrument: Instrument[INS-4417 ****8842 [BANK_VERIFIED, RE_VERIFIED]]
  tx2 instrument: Instrument[INS-4417 ****8842 [BANK_VERIFIED]]
```

One instrument, `INS-4417`, now has two verification histories inside one `PaymentRun`.

**Right**

```java
Instrument already = (Instrument) seen.get(src);
if (already != null) return already;
Instrument copy = new Instrument(src.instrumentId, src.last4,
        new ArrayList<>(src.verificationHistory));
seen.put(src, copy);
```

```console
deep copy sharing:   true
deep copy is fresh:  true
```

**Why people believe it:** "deep copy means copy everything" is how the phrase reads, and a
descent that copies every node it reaches looks maximally correct. Deep copy means *reproduce the
graph*, and the graph includes the sharing; a copy that turns one node into two has changed the
data, not just its identity.

### Treating a serialization round-trip as a faithful deep copy

**Wrong**

```java
StakeSplit split = new StakeSplit(333, 33, 300);   // 3.33 = 0.33 bonus + 3.00 cash
StakeSplit copy = SerialCopy.roundTrip(split);     // "same object, fresh instance"
```

```console
round-tripped:      StakeSplit[stake=333 bonus=33 cash=300]
constructor calls during readObject: 0
tampered split:     StakeSplit[stake=333 bonus=34 cash=300]
money created:      1 minor units
```

The clean round-trip looks right; the zero constructor calls are why it is not. No invariant
anywhere in the graph was checked, so any stream that is not byte-identical to one you produced
yields an object your constructor would have rejected.

**Right**

```java
public record MoneyMinor(long units, String currencyCode) implements Serializable {
    public MoneyMinor {
        if (units < 0) throw new IllegalArgumentException("negative units: " + units);
    }
}
```

```console
record rejected:    java.io.InvalidObjectException: negative units: -333
  caused by:        java.lang.IllegalArgumentException: negative units: -333
```

Records deserialize through the canonical constructor, so the invariant holds. For an ordinary
class, implement `readObject` to re-run the checks and throw `InvalidObjectException`, or copy by
hand.

**Why people believe it:** the round-trip genuinely does handle cycles and shared nodes, which is
the hard part, so it looks like the complete answer. It solves the graph problem and quietly
abandons the invariant problem, and the two failures look nothing alike in a log.

### Marking a field `transient` to make a graph serializable

**Wrong**

```java
public final class PaymentRun implements Serializable {
    final List<WithdrawalTransaction> transactions = new ArrayList<>();
    transient OperatorSignoff signoff;   // added to silence NotSerializableException
}
```

```console
source signoff:     OperatorSignoff[OP-207]
copy   signoff:     null   <-- transient, silently lost
```

Bank withdrawals require operator sign-off, and the copy has lost the field that records it, with
no exception and no log line.

**Right**

```java
Instrument copy = new Instrument(src.instrumentId, src.last4,
        new ArrayList<>(src.verificationHistory));
// a hand-written copy has no concept of transient: every field you want copied, you copy
```

If serialization must stay, restore the field in `readObject` or re-inject the collaborator after
the round-trip, and assert on it in a test.

**Why people believe it:** `transient` is what the IDE quick-fix offers when
`NotSerializableException` appears, and it does make the exception go away. Its actual meaning is
"this field is not part of the persistent state" — a data-model statement, not error suppression.

## Cheat sheet

| Thing | Answer |
|---|---|
| Deep copy's three hard parts | cycles, shared nodes, where recursion stops |
| The one fix for the first two | identity-keyed seen-map, populated **before** recursing |
| Why `IdentityHashMap` not `HashMap` | key on `==`, not `equals`; half-built shells have unstable hashes |
| Nodes you never copy | immutable ones (`MoneyMinor`, `String`, `Instant`) — share them |
| Why the copier cannot use all-final fields | the shell must be registered in the map, then filled |
| How serialization handles cycles | per-stream handle table, `TC_REFERENCE` + handle on the second encounter (handles start `0x7E0000`) |
| Serialization copy's four costs | must be `Serializable` (runtime failure); `transient` loses data silently; `readObject` bypasses constructors; RCE surface on untrusted bytes |
| Constructor calls during `readObject` | **0** for an ordinary class; **1** canonical constructor for a record, so invariants hold |
| Measured, 2,251-node `PaymentRun` | hand 0.47 ms / 288 KB; serialization 2.4 ms / 3.56 MB; 4.2–5.3x time, 12.4x bytes (JDK 21.0.7, not JMH) |
| Every allocation figure | names its basis and its JIT configuration, or it is not a figure |
| Primitive field order in a stream | alphabetical by field name |
| Scaled to the domain | 4 `PaymentRun` copies/day: 9.7 ms vs 1.8 ms, 14 MB vs 1.2 MB — decides nothing |
| The real recommendation | make the graph immutable; then no copy is needed |
| `clone()` in one line | shallow, `Cloneable` declares no `clone`, exception checked for nothing — use a copy constructor |
| The one live use of `Object.clone` | array cloning, which C2 intrinsifies into a bulk copy |

---

## Self-test

**Q1.** Why does registering a node in the seen-map *before* recursing into its fields matter, and
what breaks if you register it after?

<details><summary>Answer</summary>

Registering first is what terminates cycles. `PaymentRun` holds transactions and each transaction
holds a back-reference to the run. Register after, and `copyTx` calling `copyRun(src.run, seen)`
finds nothing in the map, starts a second copy of the run, recurses into the transactions again,
and never terminates — `StackOverflowError`, exactly as the naive version printed. Register first
and the inner `copyRun` finds the half-built shell and returns it, so the field points at the
correct copy even though that copy is unfinished. The consequence is that a graph copier cannot use
all-final fields: something must be assignable after the shell exists.

</details>

**Q2.** A colleague replaces the hand-written copier with `SerialCopy.roundTrip` and every test
passes. Name the two failure modes no test here would have caught.

<details><summary>Answer</summary>

First, a later change adds a non-`Serializable` field to any node — a `Logger`, a `DataSource`, a
Spring-proxied collaborator — and `NotSerializableException` is thrown at runtime five frames
inside `ObjectOutputStream`, with nothing in the type system having warned. The copy is on the
payment-run path, so the failure is a batch that stops.

Second, someone marks that field `transient` to fix the first problem and the copy silently loses
it: `PaymentRun.signoff` went from `OperatorSignoff[OP-207]` to `null` with no exception. A run
whose sign-off is null either fails a downstream compliance check for a reason that points at the
wrong place, or passes one it should not have. Both are invisible to a test that asserts only on
the fields the test knows about, which is every test.

</details>

**Q3.** `constructor calls during readObject: 0`. What constructs the object, and why are records
different?

<details><summary>Answer</summary>

For an ordinary serializable class, `ObjectInputStream` allocates the instance without running any
constructor of that class — it uses a reflective factory that runs the constructor of the nearest
**non-serializable** superclass (`Object` here) and nothing below it — then writes field values
straight in, `final` fields included. So `StakeSplit`'s sum check never ran and the deserialized
`StakeSplit[stake=333 bonus=34 cash=300]` creates a minor unit of money from nothing. Your only
hooks are `readObject`, `readObjectNoData` and `readResolve`, where validation must be duplicated.

Records are specified differently: deserialization reads the component values and then invokes the
**canonical constructor** with them, so `MoneyMinor`'s compact constructor fired on the tampered
stream and `ObjectInputStream` reported `InvalidObjectException: negative units: -333`. Records
cannot even customise this — they ignore `readObject` — which is the point: their serialization
cannot bypass their invariants.

</details>


**Q4.** The benchmark predicted one to two orders of magnitude and measured 4.2x–5.3x. What
explains the smaller gap, and which ratio would you quote?

<details><summary>Answer</summary>

Two things. The serialization side is warmed up: 20 warm-up plus 100 measured round-trips of a
140 KB stream is enough for C2 to compile the field-copy paths `ObjectStreamClass` builds, so it is
not paying interpreted reflection costs. And the hand-written side is not free, at 2,251
allocations plus 2,251 `IdentityHashMap` insertions and lookups.

Quote the **allocation** ratio: 12.4x, or 25.5 bytes allocated per byte of stream. It was stable
across five runs and both JIT configurations, it is causally clear — the stream, the block buffer,
the handle table, the descriptors, all garbage the moment the copy returns — and it is the figure
that reaches a GC log. Then add that at four `PaymentRun` copies a day neither number decides
anything, and the real argument against the round-trip is correctness, not speed. Separating those
axes is what the question is testing.

</details>

**Q5.** Give the one-line case against `Cloneable`, and say what to use instead.

<details><summary>Answer</summary>

`clone()` is a shallow field-for-field copy, so it is wrong for any nested graph; `Cloneable` is a
marker interface that declares **no** `clone` method, so you cannot call `clone()` through the
interface type and every implementor has to override a `protected` `Object` method and widen it;
and `CloneNotSupportedException` is checked, so callers must handle an exception whose only meaning
is "the author forgot the marker" — a compile-time fact expressed as a runtime failure. Use a copy
constructor or a static copy factory instead: `new Instrument(other)` or `DeepCopy.deepCopy(run)`,
which is type-checked, can be generic, can carry a seen-map, and can return a different type.
`Object.clone` retains exactly one good use: array cloning, where `array.clone()` is intrinsified
and is the fastest shallow array copy available.

</details>

**Q6.** Deep copy's third hard part is "where does the recursion stop". How did this build decide,
and what is the general rule?

<details><summary>Answer</summary>

Two nodes in the graph are never copied: `amount`, a `MoneyMinor` record over a `long` and a
`String`, and `signoff`, an immutable identifier holder. Both are shared by reference, because
copying an object nobody can mutate allocates for no benefit and buys no isolation.

The general rule: the traversal stops at every node that is immutable, and every immutable node is
a whole subtree the copier never enters. That is what makes the recommendation at the end of this
leaf more than a slogan — each component you make immutable is not just safer, it is work the
copier stops doing. The corollary is the failure mode: a node that is mutable but that you decided
to share anyway (a `DataSource`, a `Logger`, a cache) is a hole in the isolation the copy was
supposed to give you, so that decision belongs in a comment at the field, not in the copier.

</details>


---

## Open questions

- none

---

**Leaves covered:** 4.7.6 (1 leaf)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 854
