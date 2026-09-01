# 03 Java Core — Diagnostic harnesses — the inner-class retention harness — BUILD IT (§4.8, 4.8.6)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [The constant-inlining harness](05b-inlining-and-retention-harnesses.md) · Next: [Pass-by-value and overload-resolution harnesses](05c-dispatch-and-value-harnesses.md)

---

A 24-byte object sits in a registry and pins 234 KiB of bank withdrawals that settled yesterday.
Nothing in the source says so. The registry holds a `Runnable`; the `Runnable` holds an operator id;
and between the two is a field the compiler added, pointing at the `PaymentRun` the `Runnable` was
created inside. Drop every reference you can see and the run stays alive, because the reference you
cannot see is still holding it. That asymmetry is the file: the size of an inner-class instance tells
you nothing about its cost, because its cost is the transitive closure of its enclosing instance, and
one keyword deletes the field and the closure with it.

A non-static nested class — an *inner* class in JLS §8.1.3 terms — has in every instance an implicit
reference to the enclosing instance it was created from, and `javac` materialises that as a synthetic
field named `this$0` plus an extra leading constructor parameter.
`../inheritance-and-dispatch/04-internals-nested-classes.md` owns the field and the JLS rules behind
it; `../inheritance-and-dispatch/02-nested-classes.md` owns the four nested-class kinds and carries
**D-050**, the picture of `this$0` keeping the enclosing object alive.
`../objects-equality-and-lifecycle/03-lifecycle-and-references.md` owns reference strength;
`../objects-equality-and-lifecycle/03a-finalization-cleanup-and-leaks.md` owns leaks and `Cleaner`.
Order 20 (`03j-cleaner-and-diff.md`) already proved the neighbouring trap — a `Cleaner` action that
captures the object it is meant to clean, so the action never runs — with `javap` evidence and a
`CountDownLatch.await(5, SECONDS)` instrument over five runs. None of them answers the question this
file owns: **how many bytes**, and how you find out.

## §4.8.6 — The retention harness `[BUILD]` `[NUM]` `[PROVE]`

### The shape, and why these numbers

QuizStakes batches bank withdrawals: 7,000 per day across 4 payout windows, so ~1,750 per window.
A `PaymentRun` loads one window's `WithdrawalTransaction` list, an operator signs it off, and the run
is discarded. The sign-off *action* goes into `PendingActions`, a long-lived singleton registry,
because the audit trail outlives the batch. Small object, long life; big object, short life; and the
small one declared inside the big one. I sized the window at **4,000** transactions: above the
observed peak window, and chosen so the payload lands near a quarter-megabyte — large enough to be an
unmistakable class-histogram row, small enough to run in a default heap with no GC tuning.

Footprint on **Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64**, compressed oops on:
object header 12 bytes, array header 16 bytes, reference 4 bytes, 8-byte alignment.

| Object | Fields | Raw | Padded | Count | Bytes |
|---|---|---|---|---|---|
| `MoneyMinor` | 12 header + 8 `long` | 20 | 24 | 4,000 | 96,000 |
| `WithdrawalTransaction` | 12 header + 8 `long` + 4 ref + 4 ref | 28 | 32 | 4,000 | 128,000 |
| `Object[]` backing the list | 16 header + 4 × 4,000 | 16,016 | 16,016 | 1 | 16,016 |
| `ArrayList` | 12 header + 4 `modCount` + 4 `size` + 4 ref | 24 | 24 | 1 | 24 |
| `PaymentRun` | 12 header + 8 `long` + 4 ref | 24 | 24 | 1 | 24 |
| **Retained total** | | | | | **240,064** |

240,064 bytes = **234.4 KiB**. `statusCode` is the single interned literal `"BWD-700"` shared by all
4,000 records, so it contributes once and is excluded per-element — which is also why the 24-byte
`MoneyMinor` form is used here rather than the 64-byte `BigDecimal`-backed `Money`
(`../numbers-and-money/03-internals-bigdecimal.md` owns that layout).

The holder that pins all of it is **24 bytes**: 12 header + 4 `operatorId` ref + 4 `this$0` ref = 20,
padded to 24. Ratio 240,064 / 24 = **10,002.7 : 1**.

### The enclosing class, non-static inner class version

```java
import java.util.ArrayList;
import java.util.List;

record MoneyMinor(long minorUnits) { }

record WithdrawalTransaction(long transactionId, MoneyMinor amount, String statusCode) { }

/** A batch of approved bank withdrawals. Short-lived: one window, then discarded. */
final class PaymentRun {

    static final String PENDING_SIGN_OFF = "BWD-700";

    private final long runId;
    private final List<WithdrawalTransaction> window;

    PaymentRun(long runId, int windowSize) {
        this.runId = runId;
        this.window = new ArrayList<>(windowSize);
        for (int i = 0; i < windowSize; i++) {
            window.add(new WithdrawalTransaction(i, new MoneyMinor(26_000L + i), PENDING_SIGN_OFF));
        }
    }

    int windowSize() { return window.size(); }

    /** Registered in a long-lived registry, so it outlives the run. Reads one field of it. */
    final class WindowSignOff implements Runnable {
        private final String operatorId;

        WindowSignOff(String operatorId) { this.operatorId = operatorId; }

        @Override public void run() {
            System.out.println("sign-off recorded by operator " + operatorId + " for run " + runId);
        }
    }

    WindowSignOff signOffAction(String operatorId) { return new WindowSignOff(operatorId); }
}
```

`new ArrayList<>(windowSize)` is load-bearing: it allocates the backing array at exactly 4,000, so
the 16,016-byte figure is exact rather than whatever growth step `ArraysSupport.newLength` lands on
(`../strings/04-internals-stringbuilder-and-concat.md` owns that rule).

### The harness

`System.gc()` is a hint, not a guarantee, so nothing here trusts one call or a sleep. The instrument
is a `WeakReference` registered with a `ReferenceQueue`: if the referent becomes weakly unreachable
the collector clears the reference and enqueues it, so `queue.remove(200)` returns non-null. Twenty
attempts with a bounded 200 ms wait each means a `false` result is a positive finding for
*retention*, not a timeout. `jcmd <pid> GC.class_histogram` is corroboration — it counts live
instances and total bytes per class after an implicit full GC.

```java
import java.lang.ref.ReferenceQueue;
import java.lang.ref.WeakReference;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;

public final class RetentionHarness {

    /** The long-lived registry. In production this is a Spring singleton bean. */
    private static final List<Runnable> SIGN_OFF_REGISTRY = new ArrayList<>();

    private static final int WINDOW_SIZE = 4_000;

    public static void main(String[] args) throws Exception {
        ReferenceQueue<PaymentRun> queue = new ReferenceQueue<>();

        PaymentRun run = new PaymentRun(9_001L, WINDOW_SIZE);
        System.out.println("window size        = " + run.windowSize());

        WeakReference<PaymentRun> watch = new WeakReference<>(run, queue);
        SIGN_OFF_REGISTRY.add(run.signOffAction("operator-40"));

        run = null;

        boolean cleared = false;
        for (int attempt = 1; attempt <= 20 && !cleared; attempt++) {
            System.gc();
            cleared = queue.remove(200L) != null;
        }

        System.out.println("registry size      = " + SIGN_OFF_REGISTRY.size());
        System.out.println("weak ref cleared   = " + (watch.get() == null));
        System.out.println("enqueued in queue  = " + cleared);
        histogram();
        System.out.println("registry still holds: " + SIGN_OFF_REGISTRY.get(0).getClass().getName());
    }

    private static void histogram() throws Exception {
        long pid = ProcessHandle.current().pid();
        String home = System.getProperty("java.home");
        ProcessBuilder pb = new ProcessBuilder(home + "/bin/jcmd", Long.toString(pid), "GC.class_histogram");
        pb.redirectErrorStream(true);
        Process p = pb.start();
        String out = new String(p.getInputStream().readAllBytes());
        p.waitFor(20, TimeUnit.SECONDS);
        System.out.println("--- GC.class_histogram (rows of interest) ---");
        for (String line : out.split("\n")) {
            if (line.contains("PaymentRun") || line.contains("WithdrawalTransaction")
                    || line.contains("MoneyMinor") || line.contains("WindowSignOff")) {
                System.out.println(line.strip());
            }
        }
    }
}
```

### The before case: measured

```console
$ java -cp out-leak RetentionHarness
window size        = 4000
registry size      = 1
weak ref cleared   = false
enqueued in queue  = false
--- GC.class_histogram (rows of interest) ---
5:          4000         128000  WithdrawalTransaction
6:          4000          96000  MoneyMinor
271:             1             24  PaymentRun
272:             1             24  PaymentRun$WindowSignOff
```

Two independent instruments agree. The `WeakReference` never cleared across twenty forced
collections, so the `PaymentRun` is still strongly reachable. The histogram names the bytes: rows 5
and 6 are `4000 × 32 = 128000` and `4000 × 24 = 96000`, matching the table exactly, and rows 272 and
273 confirm the `PaymentRun` and its holder at 24 bytes each. The array and list rows are not printed
because the filter shows only domain classes.

```text
128,000 (WithdrawalTransaction) + 96,000 (MoneyMinor) + 16,016 (Object[4000])
      +     24 (ArrayList)      +     24 (PaymentRun)  =  240,064 bytes retained
```

Five consecutive runs gave `weak ref cleared = false` in all five. Deterministic. At 4 payout windows
a day the registry gains 240,064 bytes per window: 960,256 bytes/day, ~343 MB/year. That is the leak
that gets a heap-dump ticket eleven months after the release that caused it.

### The after case: `static`, and the one field lifted

```java
    /** Registered in a long-lived registry. Static, and carries the one value it needs. */
    static final class WindowSignOff implements Runnable {
        private final String operatorId;
        private final long runId;

        WindowSignOff(String operatorId, long runId) {
            this.operatorId = operatorId;
            this.runId = runId;
        }

        @Override public void run() {
            System.out.println("sign-off recorded by operator " + operatorId + " for run " + runId);
        }
    }

    WindowSignOff signOffAction(String operatorId) { return new WindowSignOff(operatorId, runId); }
```

Nothing else in the file changed. A static nested class has no enclosing instance to read `runId`
from, so you copy the 8 bytes you actually wanted instead of pinning the graph that contains them.

```console
$ java -cp out-fixed RetentionHarness
window size        = 4000
registry size      = 1
weak ref cleared   = true
enqueued in queue  = true
--- GC.class_histogram (rows of interest) ---
268:             1             24  PaymentRun$WindowSignOff
```

The collector reclaimed the `PaymentRun`; its row and both payload rows are gone from the histogram.
The holder is still 24 bytes — 12 header + 4 `operatorId` + 8 `runId` — but that is now all it holds.

```text
before: 240,064 bytes retained per registered sign-off
after :      24 bytes retained per registered sign-off
freed : 240,064 - 24 = 240,040 bytes, a 99.990 % reduction
```

> **Definition.** A non-static nested class instance holds a synthetic reference to the enclosing
> instance that created it, so its retained size is not its own 16–24 bytes but the entire object
> graph reachable from that enclosing instance.

### The mechanism in the class file `[BYTECODE]`

```console
$ javap -c -p 'out-leak/PaymentRun$WindowSignOff.class'
Compiled from "PaymentRun.java"
final class PaymentRun$WindowSignOff implements java.lang.Runnable {
  private final java.lang.String operatorId;

  final PaymentRun this$0;

  PaymentRun$WindowSignOff(PaymentRun, java.lang.String);
    Code:
       0: aload_0
       1: aload_1
       2: putfield      #1                  // Field this$0:LPaymentRun;
       5: aload_0
       6: invokespecial #7                  // Method java/lang/Object."<init>":()V
       9: aload_0
      10: aload_2
      11: putfield      #13                 // Field operatorId:Ljava/lang/String;
      14: return
```

There is a field the source never declared: `final PaymentRun this$0`. The constructor descriptor
gained a leading `PaymentRun` parameter the source never wrote, so `aload_1` is the enclosing instance
and `aload_2` is `operatorId`. Note the order: `putfield this$0` at offset 2 runs *before*
`invokespecial Object.<init>` at offset 6. `javac` assigns the enclosing reference ahead of the
superclass constructor precisely so an overridable method invoked from a superclass constructor can
still see it — the trap order 27 (`05a-construction-and-init-harnesses.md`) covers from the other side.

`javac` names the field `this$0` by convention; the digit is nesting depth, so a class nested two deep
also carries `this$1`. JLS §3.8 permits `$` in identifiers but reserves it by convention for
compiler-generated names, which is why seeing it in a heap dump means "the compiler did this".

```console
$ javap -p 'out-fixed/PaymentRun$WindowSignOff.class'
final class PaymentRun$WindowSignOff implements java.lang.Runnable {
  private final java.lang.String operatorId;
  private final long runId;
  PaymentRun$WindowSignOff(java.lang.String, long);
  public void run();
}
```

No `this$0`, no leading `PaymentRun` parameter, every field declared in the source. Nothing hidden.

### Version trap: `javac` 21 already elides an unused `this$0`

Delete `+ " for run " + runId` from `run()`, so the inner class touches no enclosing state, change
nothing else, and the retention disappears — on `javac` 21, but not on `javac` 17. Same source, same
JVM 21.0.7, two compilers:

```console
$ /Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home/bin/javac -d out-before PaymentRun.java RetentionHarness.java
$ java -cp out-before RetentionHarness
weak ref cleared   = true
enqueued in queue  = true
--- GC.class_histogram (rows of interest) ---
301:             1             16  PaymentRun$WindowSignOff

$ /Library/Java/JavaVirtualMachines/jdk-17.jdk/Contents/Home/bin/javac -d out-b17 PaymentRun.java RetentionHarness.java
$ java -cp out-b17 RetentionHarness
weak ref cleared   = false
enqueued in queue  = false
--- GC.class_histogram (rows of interest) ---
5:          4000         128000  WithdrawalTransaction
6:          4000          96000  MoneyMinor
271:             1             24  PaymentRun
272:             1             24  PaymentRun$WindowSignOff
```

The class files, both read with `javap -p`:

| Compiler | Field | Constructor descriptor | Instance size | Enclosing collected |
|---|---|---|---|---|
| `javac` 17.0.15 | `final PaymentRun this$0;` | `(PaymentRun, String)` | 24 bytes | no |
| `javac` 21.0.7 | none | `(PaymentRun, String)` | 16 bytes | yes |
| `javac` 25 (GraalVM 25.0.1) | none | `(PaymentRun, String)` | 16 bytes | yes |

**Insight:** `javac` 21 still *passes* the enclosing instance — the descriptor is unchanged — but no
longer stores it, so the argument is dropped on the floor and the enclosing object becomes
unreachable the moment the constructor returns. The instance shrinks from 24 to 16 bytes: the 4-byte
reference plus the padding it forced. **Unverified:** the exact release that introduced the elision.
JDK 18, 19 and 20 are not installed here, so the measured bound is "after 17.0.15, at or before
21.0.7".

The trap runs both ways. Do not rely on the elision — it fires only when the inner class reads
*nothing* from the enclosing instance, and one later edit that adds a field read silently restores the
leak with no change to the declaration. And do not tell an interviewer that an inner class on Java 21
*always* has a `this$0` field, because it does not.

### The three other forms of the same bug

In modern code the explicit inner class is rarely the form you meet. All four forms below capture the
enclosing instance; only one says so in the source.

```java
final class PaymentRunVariants {

    static final String PENDING_SIGN_OFF = "BWD-700";

    private final long runId;
    private final List<WithdrawalTransaction> window;

    PaymentRunVariants(long runId, int windowSize) {
        this.runId = runId;
        this.window = new ArrayList<>(windowSize);
        for (int i = 0; i < windowSize; i++) {
            window.add(new WithdrawalTransaction(i, new MoneyMinor(26_000L + i), PENDING_SIGN_OFF));
        }
    }

    int windowSize() { return window.size(); }

    /** Variant 2: anonymous class in an instance context. Captures the enclosing instance. */
    Runnable anonymousSignOff(String operatorId) {
        return new Runnable() {
            @Override public void run() {
                System.out.println("anon sign-off by " + operatorId + " for run " + runId);
            }
        };
    }

    /** Variant 3: lambda reading an instance field. Captures the enclosing instance, invisibly. */
    Runnable lambdaSignOff(String operatorId) {
        return () -> System.out.println("lambda sign-off by " + operatorId + " for run " + runId);
    }

    /** Variant 3-fixed: copy the field to a local first. Captures the value, not the instance. */
    Runnable lambdaSignOffCopied(String operatorId) {
        long capturedRunId = runId;
        return () -> System.out.println("lambda sign-off by " + operatorId + " for run " + capturedRunId);
    }

    /** Variant 4: local class declared inside an instance method. Same capture as an inner class. */
    Runnable localClassSignOff(String operatorId) {
        class WindowSignOffLocal implements Runnable {
            @Override public void run() {
                System.out.println("local sign-off by " + operatorId + " for run " + runId);
            }
        }
        return new WindowSignOffLocal();
    }
}
```

The probe builds a fresh 4,000-transaction run per form, registers the action, drops the strong
reference and asks the same `WeakReference` question:

```java
public final class VariantHarness {

    private static final List<Runnable> SIGN_OFF_REGISTRY = new ArrayList<>();
    private static final int WINDOW_SIZE = 4_000;

    public static void main(String[] args) throws Exception {
        probe("anonymous class      ", PaymentRunVariants::anonymousSignOff);
        probe("lambda (field read)  ", PaymentRunVariants::lambdaSignOff);
        probe("lambda (local copy)  ", PaymentRunVariants::lambdaSignOffCopied);
        probe("local class          ", PaymentRunVariants::localClassSignOff);
        System.out.println("registry size = " + SIGN_OFF_REGISTRY.size());
    }

    private static void probe(String label, BiFunction<PaymentRunVariants, String, Runnable> factory)
            throws InterruptedException {
        ReferenceQueue<PaymentRunVariants> queue = new ReferenceQueue<>();
        PaymentRunVariants run = new PaymentRunVariants(9_001L, WINDOW_SIZE);
        WeakReference<PaymentRunVariants> watch = new WeakReference<>(run, queue);
        SIGN_OFF_REGISTRY.add(factory.apply(run, "operator-40"));
        int size = run.windowSize();
        run = null;

        boolean cleared = false;
        for (int attempt = 1; attempt <= 20 && !cleared; attempt++) {
            System.gc();
            cleared = queue.remove(200L) != null;
        }
        System.out.printf("%s window=%d  enclosing collected = %-5s  weakRef null = %s%n",
                label, size, cleared, watch.get() == null);
    }
}
```

```console
$ java -cp out-variants VariantHarness
anonymous class       window=4000  enclosing collected = false  weakRef null = false
lambda (field read)   window=4000  enclosing collected = false  weakRef null = false
lambda (local copy)   window=4000  enclosing collected = true   weakRef null = true
local class           window=4000  enclosing collected = false  weakRef null = false
registry size = 4
```

Three forms retain 240,064 bytes each. The one that does not differs by two lines of source.

The anonymous and local classes carry the field openly, alongside one field per captured local:

```console
$ javap -p 'out-variants/PaymentRunVariants$1.class'
class PaymentRunVariants$1 implements java.lang.Runnable {
  final java.lang.String val$operatorId;
  final PaymentRunVariants this$0;
  PaymentRunVariants$1();
  public void run();
}

$ javap -p 'out-variants/PaymentRunVariants$1WindowSignOffLocal.class'
class PaymentRunVariants$1WindowSignOffLocal implements java.lang.Runnable {
  final java.lang.String val$operatorId;
  final PaymentRunVariants this$0;
  PaymentRunVariants$1WindowSignOffLocal();
  public void run();
}
```

`val$operatorId` is the captured effectively-final local, `this$0` the enclosing instance. `javap`
prints both constructors as no-arg, which is a presentation artefact of the synthetic signature —
the `new` site proves otherwise: `invokespecial PaymentRunVariants$1WindowSignOffLocal."<init>":(LPaymentRunVariants;Ljava/lang/String;)V`.

The lambda is the dangerous one, because there is no field to find:

```console
$ javap -c -p out-variants/PaymentRunVariants.class
  java.lang.Runnable lambdaSignOff(java.lang.String);
    Code:
       0: aload_0
       1: aload_1
       2: invokedynamic #51,  0             // InvokeDynamic #0:run:(LPaymentRunVariants;Ljava/lang/String;)Ljava/lang/Runnable;
       7: areturn

  java.lang.Runnable lambdaSignOffCopied(java.lang.String);
    Code:
       0: aload_0
       1: getfield      #7                  // Field runId:J
       4: lstore_2
       5: aload_1
       6: lload_2
       7: invokedynamic #55,  0             // InvokeDynamic #1:run:(Ljava/lang/String;J)Ljava/lang/Runnable;
      12: areturn

  private static void lambda$lambdaSignOffCopied$1(java.lang.String, long);
  private void lambda$lambdaSignOff$0(java.lang.String);
```

The proof is in two places at once. The factory descriptor: `lambdaSignOff` bootstraps with
`(LPaymentRunVariants;Ljava/lang/String;)`, and `aload_0` is `this`, so the object the
`LambdaMetafactory` produces holds the whole `PaymentRunVariants`. `lambdaSignOffCopied` bootstraps
with `(Ljava/lang/String;J)` — a reference and a primitive `long`, no enclosing instance anywhere.
And the desugared bodies: `lambda$lambdaSignOff$0` is `private void`, an **instance** method, so it
structurally requires a receiver; `lambda$lambdaSignOffCopied$1` is `private static void`. One
`getfield` and one `lstore` before the `invokedynamic` moved the body from instance to static and
deleted 240,040 bytes of retention.

**That local-copy fix is the most practically useful thing in this file.** A lambda that mentions any
instance field, calls any instance method, or writes `this` captures the enclosing instance; hoist the
value into a local and it captures the value instead.

| Form | Captures | Visible in source | In the class file | How you break it |
|---|---|---|---|---|
| Inner (non-static nested) class | enclosing instance, whenever any enclosing state is read | no — the declaration looks self-contained | `final <Enclosing> this$0;` + leading ctor parameter | add `static`, pass the fields it needs |
| Anonymous class in an instance context | enclosing instance + each captured local | no | `this$0` + one `val$<name>` per capture | make it a `static` nested class, or a lambda over locals only |
| Lambda reading an instance field or calling an instance method | enclosing instance + each captured local | no, and there is no field to grep for | captured argument in the `invokedynamic` descriptor; body is a `private` **instance** method | copy the field to a local first; body becomes `private static` |
| Local class in an instance method | enclosing instance + each captured local | no | `this$0` + `val$<name>`, class named `<Enclosing>$1<Name>` | lift to a `static` nested class with explicit parameters |
| Static nested class | nothing implicit | yes — every field declared | only declared fields | nothing to break |

### The one case where non-static is correct

The bug is not "non-static nested class". The bug is **lifetime mismatch**: an inner object that
outlives its enclosing object. When the inner class exists *as part of* its enclosing instance and
cannot outlive it, `this$0` is not overhead — it is the design, and it costs nothing relative to
passing the same reference explicitly. The JDK splits deliberately: `HashMap.Node` is static because
entries escape to callers through `entrySet()` and must not pin the map; `HashMap.HashIterator` is
non-static because an iterator without its map is meaningless and is expected to die first.
QuizStakes has the same split — a `PaymentRun.WindowCursor` walking the run's own transaction list
should be non-static, since it needs `window` on every `next()` and holding a cursor past the run's
life is already a bug the reference merely makes visible.

> **Rule.** Make a nested class `static` unless the instance genuinely needs the enclosing instance's
> state *and* provably cannot outlive it. If it escapes into anything long-lived — a registry, cache,
> listener list, executor queue, `ThreadLocal` or static map — it must be `static`.

### The serialization row, demonstrated

`this$0` is a normal non-`transient` instance field, so serializing a non-static inner class
serializes the enclosing instance too. If the enclosing class is not `Serializable` the write fails —
and the exception names the *enclosing* class, which is the confusing part, because you never asked
to serialize it.

```java
/** Not Serializable. It holds a payload no wire format should ever carry. */
final class PaymentRunSerial {

    private final long runId;
    private final byte[] payoutFile;

    PaymentRunSerial(long runId, int payloadBytes) {
        this.runId = runId;
        this.payoutFile = new byte[payloadBytes];
    }

    /** Serializable, tiny, and drags the whole enclosing instance into the stream. */
    final class WindowSignOff implements Serializable {
        private static final long serialVersionUID = 1L;
        private final String operatorId;

        WindowSignOff(String operatorId) { this.operatorId = operatorId; }

        String describe() { return operatorId + " signed run " + runId; }
    }

    /** Serializable, tiny, and self-contained. */
    static final class WindowSignOffStatic implements Serializable {
        private static final long serialVersionUID = 1L;
        private final String operatorId;
        private final long runId;

        WindowSignOffStatic(String operatorId, long runId) {
            this.operatorId = operatorId;
            this.runId = runId;
        }

        String describe() { return operatorId + " signed run " + runId; }
    }

    WindowSignOff signOffAction(String operatorId) { return new WindowSignOff(operatorId); }

    WindowSignOffStatic staticSignOffAction(String operatorId) {
        return new WindowSignOffStatic(operatorId, runId);
    }
}

public final class SerialTrap {

    public static void main(String[] args) {
        PaymentRunSerial run = new PaymentRunSerial(9_001L, 2_000_000);

        System.out.println("inner  : " + attempt(run.signOffAction("operator-40")));
        System.out.println("static : " + attempt(run.staticSignOffAction("operator-40")));
    }

    private static String attempt(Serializable candidate) {
        try (ByteArrayOutputStream sink = new ByteArrayOutputStream();
             ObjectOutputStream out = new ObjectOutputStream(sink)) {
            out.writeObject(candidate);
            out.flush();
            return "wrote " + sink.size() + " bytes";
        } catch (IOException e) {
            return e.getClass().getName() + ": " + e.getMessage();
        }
    }
}
```

```console
$ java -cp out-serial SerialTrap
inner  : java.io.NotSerializableException: PaymentRunSerial
static : wrote 121 bytes
```

The inner form cannot be serialized at all. The static form writes 121 bytes: stream header, class
descriptor, `serialVersionUID`, the `operatorId` string and the `long`. The worse outcome is the one
that does *not* throw — had `PaymentRunSerial` implemented `Serializable`, the 121-byte object would
have silently written 2 MB of `payoutFile` onto the wire. No serialized bytes are reproduced here;
the two numbers describe the shape completely.

### What each instrument actually proves

| Instrument | Availability here | Proves | Does not prove |
|---|---|---|---|
| `WeakReference` + `ReferenceQueue`, 20 forced GCs, 200 ms waits | yes — primary evidence | the referent is or is not reachable; a definitive answer for retention | who holds it, or how much it holds |
| `jcmd <pid> GC.class_histogram` | yes — corroboration | live instance count and byte total per class, so retained payload in bytes | the retention path, or which of many instances is the culprit |
| `jcmd <pid> GC.heap_dump` | dump taken — 3,850,319 bytes for this program; **no analyser installed** | nothing on its own | anything, until read by a tool |
| Heap dump + dominator tree (Eclipse MAT) | **not available on this machine** | the retention *path*: which GC root, through which fields, to the retained set | — |
| `javap -c -p` | yes | that the field or captured argument exists in the class file | that it is reached at runtime |
| `getThreadAllocatedBytes` deltas | yes, used elsewhere in this note set | allocation volume | retention |

**Unverified:** the dominator-tree row. I produced a real `.hprof` with `jcmd <pid> GC.heap_dump
-overwrite`, a genuine 3,850,319-byte file, but no MAT-class tool (Eclipse MAT, VisualVM, `jhat`) is
installed here, so I did not read it and describe no dump contents. Every number here comes from
`WeakReference` behaviour, `GC.class_histogram`, or `javap`. Guide 06 owns heap dumps and MAT.

### Diff vs the real one

For a diagnostic harness the honest comparison is against how this is investigated in production.

| Axis | This harness | A real leak investigation | Why the difference matters |
|---|---|---|---|
| **Edge cases** | one holder, one enclosing object, one registry, single-threaded, 4,000 elements | thousands of holders across dozens of registries, sizes spanning three orders of magnitude, many already soft- or weak-held | a `WeakReference` on the object you already suspect is easy; production's hard part is deciding *which* object to watch |
| **Intrinsics / JIT** | escape analysis is irrelevant — everything here escapes into a static list by construction | a short-lived capture may be scalar-replaced entirely, so a form that leaks in one JIT state does not in another | if you probe a *non*-escaping capture, run under `-XX:-DoEscapeAnalysis` as this note set's harnesses do, or you measure C2 rather than your code |
| **Serialization** | demonstrated: inner form throws `NotSerializableException: PaymentRunSerial`, static form writes 121 bytes | usually surfaces as a session-replication or cache-write error naming a class nobody meant to serialize | `this$0` is non-`transient` and you cannot mark it; a `Serializable` enclosing class turns the throw into a silent 2 MB payload |
| **Null policy** | `this$0` is never null — `putfield` precedes `super()`, so there is no unset window | the same, except a deserialized or reflectively-built instance can carry a null `this$0`, and `getfield` then NPEs from a line naming no variable | you cannot defend against it, only avoid needing it |
| **Thread safety** | single-threaded; `System.gc()` is synchronous enough for the assertion | the holder is usually published across threads, and the retained graph may mutate while you dump | a histogram is taken at a safepoint so it is consistent; a `WeakReference` read is not ordered against another thread's last write |
| **Allocation tricks** | `new ArrayList<>(4000)` for an exact 16,016-byte array; one interned `"BWD-700"` shared 4,000 ways | production lists grow by the `newLength` rule and over-allocate; strings are rarely shared | computing expected bytes from element count alone leaves you 20–50 % low on the array and high on the strings |
| **Why the JDK bothers** | it does not "bother": JLS §8.1.3 gives an inner class access to the enclosing instance's members, and a field is the only way to implement that on a JVM with no runtime notion of nesting | the JDK's own code splits on lifetime — `HashMap.Node` static, `HashMap.HashIterator` non-static | the feature is not a mistake; using it where lifetimes diverge is |

**Interview:** "Why should a nested class be static?" — a non-static one holds a synthetic reference
to the enclosing instance, so any inner-class object that escapes into something long-lived retains its
whole enclosing object graph; `static` removes the reference, and the class then declares everything it
holds.

## Pitfalls

### Believing a small inner-class object has a small footprint

**Wrong**

```java
SIGN_OFF_REGISTRY.add(run.signOffAction("operator-40")); // "it's a 24-byte Runnable"
```

```console
--- GC.class_histogram (rows of interest) ---
5:          4000         128000  WithdrawalTransaction
6:          4000          96000  MoneyMinor
271:             1             24  PaymentRun
272:             1             24  PaymentRun$WindowSignOff
```

Shallow size 24 bytes; retained size 240,064 bytes.

**Right**

Make the class `static` and pass the values it needs. Same 24-byte object, and the payload rows
vanish from the histogram:

```java
    static final class WindowSignOff implements Runnable {
        private final String operatorId;
        private final long runId;
        WindowSignOff(String operatorId, long runId) {
            this.operatorId = operatorId;
            this.runId = runId;
        }
        @Override public void run() {
            System.out.println("sign-off recorded by operator " + operatorId + " for run " + runId);
        }
    }
```

**Why people believe it:** every sizing tool reports *shallow* size by default.
`Instrumentation.getObjectSize` returns 24, the histogram row says 24, and the class body has two
fields. Retained size is a different question, and only a dominator tree answers it directly.

### Believing a lambda does not capture `this` because there is no `this$0`

**Wrong**

```java
Runnable signOff = () -> System.out.println("sign-off by " + operatorId + " for run " + runId);
```

```console
lambda (field read)   window=4000  enclosing collected = false  weakRef null = false
```

**Right**

```java
long capturedRunId = runId;
Runnable signOff = () -> System.out.println("sign-off by " + operatorId + " for run " + capturedRunId);
```

```console
lambda (local copy)   window=4000  enclosing collected = true   weakRef null = true
```

The `invokedynamic` descriptor changes from `(LPaymentRunVariants;Ljava/lang/String;)Ljava/lang/Runnable;`
to `(Ljava/lang/String;J)Ljava/lang/Runnable;`, and the desugared body from `private void` to
`private static void`.

**Why people believe it:** lambdas were sold as "not inner classes", and they genuinely are not — no
synthetic class file per lambda, no `this$0` field, no `javap -p` row to grep for. The capture moved
from a field into an `invokedynamic` argument, so it is real but invisible to every search you would
think to run.

### Believing `static` on a nested class is a style preference

**Wrong**

```java
final class WindowSignOff implements Runnable { }   // "checkstyle nit, ignore it"
```

```console
weak ref cleared   = false
enqueued in queue  = false
```

**Right**

```java
static final class WindowSignOff implements Runnable { }
```

```console
weak ref cleared   = true
enqueued in queue  = true
```

240,040 bytes per registered instance, ~343 MB/year at 4 payout windows a day.

**Why people believe it:** on `javac` 21 the elision makes it *look* like a preference — if the inner
class reads nothing from its enclosing instance, both forms behave identically and the non-static one
is 16 bytes. It is a preference right up to the first commit that adds a field read, at which point
the same declaration starts leaking with nothing visible in the diff.

### Believing `System.gc()` proves anything on its own

**Wrong**

```java
run = null;
System.gc();
Thread.sleep(500);
System.out.println("free = " + Runtime.getRuntime().freeMemory());
```

`freeMemory()` reports heap regions, not one object, and moves by megabytes for unrelated reasons.
`System.gc()` is documented as a *suggestion*, and `-XX:+DisableExplicitGC` makes it a silent no-op.

**Right**

```java
WeakReference<PaymentRun> watch = new WeakReference<>(run, queue);
run = null;
boolean cleared = false;
for (int attempt = 1; attempt <= 20 && !cleared; attempt++) {
    System.gc();
    cleared = queue.remove(200L) != null;
}
System.out.println("collected = " + cleared);
```

`cleared` is the collector's own verdict on reachability, not an inference from a heap total.

**Why people believe it:** `System.gc()` plus a `freeMemory()` delta usually *looks* right in a toy
program, because a toy program's whole heap is the object under test. The signal disappears the moment
anything else is allocating.

## Cheat sheet

| Fact | Value |
|---|---|
| Synthetic field name | `this$0` (`this$1` at depth 2); `$` reserved for generated names |
| Where it is assigned | `putfield this$0` **before** `invokespecial Object.<init>` |
| Constructor descriptor | non-static gains a leading `<Enclosing>` parameter; static does not |
| Inner holder with `this$0` | 12 + 4 + 4 = 20 → **24 bytes** padded; without it, 12 + 4 = **16** |
| `javac` 17.0.15 vs 21.0.7 / 25 | 17 emits `this$0` even when unused; 21 and 25 elide it, descriptor unchanged |
| Retained before / after | 128,000 + 96,000 + 16,016 + 24 + 24 = **240,064** → **24**; freed 240,040 (99.990 %) |
| `MoneyMinor` / `WithdrawalTransaction` | 24 / 32 bytes (JDK 21.0.7, macOS aarch64, compressed oops) |
| Lambda capturing `this` | body is `private void`; indy descriptor carries the enclosing type |
| Lambda after local copy | body is `private static void`; no enclosing parameter |
| Anonymous / local class fields | `this$0` + one `val$<name>` per captured local |
| Instruments | reachability: `WeakReference` + `ReferenceQueue` + N forced GCs; bytes: `jcmd GC.class_histogram`; path: heap dump + dominator tree only |
| Serialization | non-static inner + non-`Serializable` enclosing = `NotSerializableException: <Enclosing>` |
| The rule | inner object must not outlive outer; if it escapes anywhere long-lived, `static` |

## Self-test

**Q1.** A `Runnable` in a registry reports 24 bytes in a class histogram. Your heap is 400 MB over
budget and the registry has 12,000 entries. What do you check first?

<details><summary>Answer</summary>

Whether that `Runnable`'s class is a non-static nested class or a lambda that captures `this`.
12,000 × 24 bytes is 288 KB, so the shallow size cannot be the problem; retained size can. Run
`javap -p`: a `final <Enclosing> this$0` field, a class name of the form `<Enclosing>$1`, or a
`lambda$<name>$0` body that is a `private` instance rather than `private static` method all mean each
entry pins an entire enclosing object graph. 400 MB / 12,000 is about 34 KB per entry, exactly the
scale a captured request-or-batch object reaches.

</details>

**Q2.** Why does `putfield this$0` execute before `invokespecial Object.<init>`, when `super()`
normally comes first?

<details><summary>Answer</summary>

Because a superclass constructor may invoke an overridable method that the subclass overrides, and
that override may read enclosing-instance state. If `this$0` were assigned after `super()`, the
override would see `null`. The JVM's constructor rules permit assignments to the current class's own
fields before the superclass constructor call in this compiler-generated case. The related trap — a
superclass constructor calling an overridable method and seeing uninitialised subclass fields — is
order 27, `05a-construction-and-init-harnesses.md`.

</details>

**Q3.** On JDK 21 you compile a non-static nested class that reads nothing from its enclosing
instance, and the enclosing object is collected. Is it safe to leave it non-static?

<details><summary>Answer</summary>

No. `javac` 21.0.7 elides the `this$0` field when unused, which is why it was collected — the
constructor still receives the enclosing instance, it just does not store it. The elision is a
compiler optimisation contingent on the class body, not a language guarantee, and it disappears the
moment an edit adds one field read or instance-method call. `javac` 17.0.15 emits the field
regardless. Measured here: same source, JVM 21.0.7, `javac` 17 retains 240,064 bytes and `javac` 21
retains none.

</details>

**Q4.** What is the two-line fix for a lambda leaking its enclosing instance, and how do you verify
it in the class file?

<details><summary>Answer</summary>

Copy each instance field the lambda needs into a local before the lambda and reference the local.
Verify with `javap -c -p` in two places: the `invokedynamic` factory descriptor should lose its
leading enclosing-class parameter — `(LPaymentRunVariants;Ljava/lang/String;)` becomes
`(Ljava/lang/String;J)` — and the desugared body should change from `private void lambda$<name>$0` to
`private static void lambda$<name>$0`. A static body cannot hold a receiver, so `static` in that
listing is the proof.

</details>

**Q5.** `WindowSignOff implements Serializable`, every declared field is serializable, and
`writeObject` throws `NotSerializableException: PaymentRunSerial`. Explain.

<details><summary>Answer</summary>

`WindowSignOff` is a non-static inner class, so it has a synthetic `final PaymentRunSerial this$0`.
That is a normal non-`transient` instance field, so the serialization machinery walks it, finds the
enclosing class is not `Serializable`, and throws naming it. You cannot mark the field `transient`
because you cannot write modifiers on a compiler-generated field. The fix is `static` plus explicit
fields for whatever the class actually needed. The worse case is when the enclosing class *is*
`Serializable`: no exception, and its entire payload goes onto the wire.

</details>

## Open questions

- The exact JDK release that introduced the `this$0` elision for unused enclosing instances. Measured
  bound: `javac` 17.0.15 emits the field, `javac` 21.0.7 and GraalVM 25.0.1 do not; JDK 18, 19 and 20
  are not installed here. The JDK bug database entry or the `javac` `Lower.java` history would settle it.
- Whether the elision is specified anywhere or is purely a `javac` implementation choice. JLS §8.1.3
  requires *access* to the enclosing instance, not a field, so it is very likely unspecified —
  confirming that needs the JLS chapter 8 text read alongside the `javac` changeset.
- The retention *path* as a dominator tree. A real 3,850,319-byte `.hprof` was produced with
  `jcmd <pid> GC.heap_dump -overwrite`, but no Eclipse MAT, VisualVM or equivalent is installed on
  this machine, so it was not analysed and no dump contents are described. Guide 06 owns this.

---

**Leaves covered:** 4.8.6 (1 leaf)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 897
