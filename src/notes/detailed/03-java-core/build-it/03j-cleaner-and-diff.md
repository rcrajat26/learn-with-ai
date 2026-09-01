# 03 Java Core — Exception builds: the Cleaner-based resource holder, and the diff against the JDK's own resource classes — BUILD IT (§4.6.7, §4.6.9)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [CheckedFunction and sneaky-throw](03e-checked-crossing-cleaner-and-diff.md) · Next: [Money two ways](04-value-objects-and-money.md)

---

## §4.6.7 `[BUILD]` `[PROVE]` `[TRAP]` The `Cleaner`-based payout-file holder, twice

### The shape

A `PaymentRun` opens a payout file, streams approved bank withdrawals into it, and hands it to the
banking partner. The file is an OS file descriptor. At 7k bank withdrawals a day across four payout
windows the descriptor count is small — but a descriptor that is never closed is never reclaimed,
and a `PaymentRun` service that leaks one per run walks into `EMFILE` at some unpredictable hour of
some unpredictable week. `try`-with-resources fixes it, when the caller writes it. `Cleaner` is what
catches the caller who did not.

The shape of a `Cleaner` is three moving parts and one rule:

| Part | What it is |
|---|---|
| The registered object | the holder — the thing whose *unreachability* is the trigger |
| The cleaning action | a `Runnable` the cleaner invokes **after** the holder becomes phantom-reachable |
| The `Cleanable` | the handle returned by `register`, whose `clean()` runs the action early and unregisters it |

And the rule, stated in the `Cleaner` class javadoc in as many words:

> Note that the cleaning action must not refer to the object being registered. If so, the object
> will not become phantom reachable and the cleaning action will not be invoked automatically.

That single sentence is the whole trap. The trigger is unreachability. If the action holds a
reference to the holder, the action keeps the holder reachable, the holder never goes phantom, the
action never runs, and the resource leaks — plus the action object and the holder both stay in the
heap forever, so you have traded a descriptor leak for a descriptor leak *and* a memory leak. It is
a self-inflicted reference cycle through the cleaner's own bookkeeping, and every other design rule
in this section is a consequence of it.

**Insight:** the `Cleaner` does not hold your action weakly. `Cleaner.register` builds a
`CleanerImpl.PhantomCleanableRef` — a `PhantomReference` to the *holder*, strongly referencing the
*action*, linked into a list the `CleanerImpl` owns and the cleaner thread walks. So the action is
strongly reachable from a live cleaner for as long as it is registered. Anything the action reaches
is strongly reachable too. Reach the holder from the action and the phantom reference will never
fire.

**Where the mechanisms live.** Reference strength, the phantom-reachability level, and how
finalization used to do this job are owned by
[`../objects-equality-and-lifecycle/03a-finalization-cleanup-and-leaks.md`](../objects-equality-and-lifecycle/03a-finalization-cleanup-and-leaks.md).
In one paragraph: an object is *phantom-reachable* when it is neither strongly, softly nor weakly
reachable, it has been finalized (or has no finalizer), and some `PhantomReference` still points at
it; at that moment the collector enqueues that reference on its `ReferenceQueue`, which is the
notification a `Cleaner` reacts to. `PhantomReference.get()` returns `null` unconditionally in
JDK 21 — the body is literally `return null;` — so a phantom reference can never resurrect its
referent, which is exactly why it is safe to run cleanup off it and was never safe to run cleanup
off `finalize()`.

The synthetic `this$0` field that makes a non-static nested class hold its enclosing instance is
owned by [`../inheritance-and-dispatch/04-internals-nested-classes.md`](../inheritance-and-dispatch/04-internals-nested-classes.md).
In one paragraph: `javac` compiles a non-static member class into a top-level class file with a
synthetic final field named `this$0` typed as the enclosing class, initialised from a synthetic
first constructor parameter. Every `new State(channel)` written inside an instance method therefore
passes `this` silently. Nothing in the source says so; the field only exists in the class file.

### The correct form, complete

```java
import java.io.IOException;
import java.lang.ref.Cleaner;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicInteger;

/** The correct form: a static nested State that holds the handle, never the holder. */
final class PayoutFileHandle implements AutoCloseable {

    private static final Cleaner PAYOUT_CLEANER = Cleaner.create();

    static final AtomicInteger OPEN_DESCRIPTORS = new AtomicInteger();
    static final CountDownLatch CLEANED = new CountDownLatch(1);

    private static final class State implements Runnable {
        private final FileChannel channel;
        private final String runId;

        State(FileChannel channel, String runId) {
            this.channel = channel;
            this.runId = runId;
        }

        @Override
        public void run() {
            try {
                if (channel.isOpen()) {
                    channel.close();
                    System.out.println("  [cleaner] released payout-file descriptor for " + runId);
                }
            } catch (IOException e) {
                System.out.println("  [cleaner] close failed for " + runId + ": " + e);
            } finally {
                OPEN_DESCRIPTORS.decrementAndGet();
                CLEANED.countDown();
            }
        }
    }

    private final State state;
    private final Cleaner.Cleanable cleanable;
    private final String runId;

    PayoutFileHandle(Path file, String runId) throws IOException {
        FileChannel channel = FileChannel.open(file,
                StandardOpenOption.CREATE, StandardOpenOption.WRITE);
        OPEN_DESCRIPTORS.incrementAndGet();
        this.runId = runId;
        this.state = new State(channel, runId);
        this.cleanable = PAYOUT_CLEANER.register(this, state);
    }

    void appendWithdrawal(String instrumentRef, String minorUnits) throws IOException {
        String row = runId + "," + instrumentRef + "," + minorUnits + "\n";
        state.channel.write(ByteBuffer.wrap(row.getBytes(StandardCharsets.UTF_8)));
    }

    @Override
    public void close() {
        cleanable.clean();
    }
}
```

Four decisions in that code, each load-bearing. `State` is `private static final` — static so there
is no `this$0`, and a named class rather than a lambda so the capture set is visible in the field
list. It holds `channel` and `runId`, a handle and a `String`, neither of which reaches the holder;
`runId` is a *copy* of the holder's field, and duplicating an 8-byte compressed-oop reference buys
the independence. The holder keeps a strong reference to `state`, which is the permitted direction —
`appendWithdrawal` needs the channel; the forbidden direction is `state` to holder.

The fourth is that `close()` delegates to `cleanable.clean()` and nothing else, so it is idempotent
without a `closed` flag, without `synchronized`, without a CAS. The `Cleaner.Cleanable` javadoc:

> Unregisters the cleanable and invokes the cleaning action. The cleanable's cleaning action is
> invoked at most once regardless of the number of calls to `clean`.

That is the JDK's guarantee, not mine, and `jdk.internal.ref.PhantomCleanable` earns it:

```java
public final void clean() {
    if (remove()) {          // synchronized (list); returns false if already unlinked
        super.clear();
        performCleanup();
    }
}
```

`remove()` unlinks the node under `synchronized (list)` and returns `false` if `next == this`, i.e.
if it was already unlinked. A second `clean()` finds nothing to do. This is the one place where an
`AutoCloseable` gets idempotence for free.

### The incorrect forms, complete, side by side

Two ways to write the bug. Neither is visible in a diff.

```java
/** The broken form: State is a non-static inner class, so it carries this$0. */
final class LeakyPayoutFileHandle implements AutoCloseable {

    private static final Cleaner PAYOUT_CLEANER = Cleaner.create();

    static final CountDownLatch CLEANED = new CountDownLatch(1);

    private final class State implements Runnable {
        private final FileChannel channel;

        State(FileChannel channel) {
            this.channel = channel;
        }

        @Override
        public void run() {
            try {
                if (channel.isOpen()) {
                    channel.close();
                    System.out.println("  [cleaner] released payout-file descriptor for " + runId);
                }
            } catch (IOException e) {
                System.out.println("  [cleaner] close failed: " + e);
            } finally {
                CLEANED.countDown();
            }
        }
    }

    private final String runId;
    private final State state;
    private final Cleaner.Cleanable cleanable;

    LeakyPayoutFileHandle(Path file, String runId) throws IOException {
        FileChannel channel = FileChannel.open(file,
                StandardOpenOption.CREATE, StandardOpenOption.WRITE);
        this.runId = runId;
        this.state = new State(channel);
        this.cleanable = PAYOUT_CLEANER.register(this, state);
    }

    @Override
    public void close() {
        cleanable.clean();
    }
}
```

The diff against the correct version is `static` deleted and `runId` read from the outer instance
instead of being copied. That is it. Two characters and a field reference.

```java
/** The other broken form: a lambda that mentions an instance field, so it captures this. */
final class LambdaPayoutFileHandle implements AutoCloseable {

    private static final Cleaner PAYOUT_CLEANER = Cleaner.create();

    static final CountDownLatch CLEANED = new CountDownLatch(1);

    private final FileChannel channel;
    private final String runId;
    private final Cleaner.Cleanable cleanable;

    LambdaPayoutFileHandle(Path file, String runId) throws IOException {
        this.channel = FileChannel.open(file,
                StandardOpenOption.CREATE, StandardOpenOption.WRITE);
        this.runId = runId;
        this.cleanable = PAYOUT_CLEANER.register(this, () -> {
            try {
                if (channel.isOpen()) {
                    channel.close();
                    System.out.println("  [cleaner] released payout-file descriptor for " + runId);
                }
            } catch (IOException e) {
                System.out.println("  [cleaner] close failed: " + e);
            } finally {
                CLEANED.countDown();
            }
        });
    }

    @Override
    public void close() {
        cleanable.clean();
    }
}
```

This one reads as the *tidier* of the three. `channel` is a field of the holder, so `channel` inside
the lambda means `this.channel`, so the lambda captures `this`. Nothing in the source says `this`.
`Cleaner`'s own javadoc names this exact failure: "The cleaning action could be a lambda but all too
easily will capture the object reference, by referring to fields of the object being cleaned."

**Pitfall:** a cleaning action that reaches the object it is cleaning never runs. The wrong belief
is that a `Cleaner` cleans up "when the object is done with", so an action written as an inner class
or a lambda over the object's own fields is the natural expression of it. The symptom is silence —
no exception, no log line, no warning, just a descriptor count that climbs across a week and an
`EMFILE` at 03:00 on the fourth payout window. The fix is a `static` nested class that receives the
raw handle as a constructor argument, and a review rule that any `Cleaner.register` whose second
argument is not a `static`-nested-class instance is rejected on sight.

### The evidence, from the class files

`javap -p` on the two `State` classes, side by side:

```console
$ javap -p 'PayoutFileHandle$State.class'
Compiled from "CleanerDemo.java"
final class PayoutFileHandle$State implements java.lang.Runnable {
  private final java.nio.channels.FileChannel channel;
  private final java.lang.String runId;
  PayoutFileHandle$State(java.nio.channels.FileChannel, java.lang.String);
  public void run();
}

$ javap -p 'LeakyPayoutFileHandle$State.class'
Compiled from "CleanerDemo.java"
final class LeakyPayoutFileHandle$State implements java.lang.Runnable {
  private final java.nio.channels.FileChannel channel;
  final LeakyPayoutFileHandle this$0;
  LeakyPayoutFileHandle$State(LeakyPayoutFileHandle, java.nio.channels.FileChannel);
  public void run();
}
```

Read the difference. The correct `State` has two declared fields and a two-argument constructor. The
broken `State` has a third field, `final LeakyPayoutFileHandle this$0`, that appears in no source
line, and a three-argument constructor whose first parameter is the enclosing class. Every `State`
instance therefore strongly references its `LeakyPayoutFileHandle`, the cleaner strongly references
the `State`, and the phantom reference to the holder can never be enqueued.

For the lambda, the capture set is in the `invokedynamic` descriptor. `javap -p` first:

```console
$ javap -p LambdaPayoutFileHandle.class
Compiled from "CleanerDemo.java"
final class LambdaPayoutFileHandle implements java.lang.AutoCloseable {
  private static final java.lang.ref.Cleaner PAYOUT_CLEANER;
  static final java.util.concurrent.CountDownLatch CLEANED;
  private final java.nio.channels.FileChannel channel;
  private final java.lang.String runId;
  private final java.lang.ref.Cleaner$Cleanable cleanable;
  LambdaPayoutFileHandle(java.nio.file.Path, java.lang.String) throws java.io.IOException;
  public void close();
  private void lambda$new$0(java.lang.String);
  static {};
}
```

`private void lambda$new$0(java.lang.String)` — an **instance** method, not a static one. An instance
method needs a receiver, and the receiver is the holder. Now the constructor:

```console
$ javap -c -p LambdaPayoutFileHandle.class
      22: invokestatic  #18                 // Method java/nio/channels/FileChannel.open:(Ljava/nio/file/Path;[Ljava/nio/file/OpenOption;)Ljava/nio/channels/FileChannel;
      25: putfield      #24                 // Field channel:Ljava/nio/channels/FileChannel;
      28: aload_0
      29: aload_2
      30: putfield      #30                 // Field runId:Ljava/lang/String;
      33: aload_0
      34: getstatic     #34                 // Field PAYOUT_CLEANER:Ljava/lang/ref/Cleaner;
      37: aload_0
      38: aload_0
      39: aload_2
      40: invokedynamic #38,  0             // InvokeDynamic #0:run:(LLambdaPayoutFileHandle;Ljava/lang/String;)Ljava/lang/Runnable;
      45: invokevirtual #42                 // Method java/lang/ref/Cleaner.register:(Ljava/lang/Object;Ljava/lang/Runnable;)Ljava/lang/ref/Cleaner$Cleanable;
      48: putfield      #48                 // Field cleanable:Ljava/lang/ref/Cleaner$Cleanable;
      51: return
```

Instruction by instruction from offset 33. `aload_0` at 33 is `this`, pushed as the receiver for the
`putfield` at 48. `getstatic` at 34 loads `PAYOUT_CLEANER`, the receiver for `register`. `aload_0` at
37 is the *first argument to `register`* — the object being monitored. `aload_0` at 38 and `aload_2`
at 39 are the lambda's **captured arguments**, and the `invokedynamic` descriptor at 40 spells them
out: `(LLambdaPayoutFileHandle;Ljava/lang/String;)Ljava/lang/Runnable;`. The `Runnable` handed to
`register` closes over an `LLambdaPayoutFileHandle;` — the very object at offset 37. `aload_0`
appears twice in three instructions: once as the thing to monitor, once as the thing the monitor
holds. That is the cycle, printed.

Note which capture is which. `channel` was read as `this.channel`, so the lambda took `this`.
`runId` inside the lambda resolves to the *constructor parameter*, which shadows the field, so it was
captured separately as a plain `String` at offset 39. One field reference was enough; the second
name cost nothing. There is no source-level signal distinguishing the two.

### Demonstrating the leak

The instrument matters more than the result. `System.gc()` is a hint the JVM is free to ignore;
phantom-reachability processing is asynchronous; and the cleaning action runs on a *different*
thread from `main`. A `Thread.sleep` followed by a hopeful `println` proves nothing — it cannot
distinguish "did not run" from "has not run yet". So each holder counts down a
`CountDownLatch` from inside its cleaning action, and `main` calls `await(5, TimeUnit.SECONDS)`. A
`true` means the action definitely ran and `main` definitely observed it, with the latch supplying
the happens-before edge. A `false` means it did not run within five seconds of five `System.gc()`
calls — evidence, not proof, but the strongest available.

```java
public class CleanerDemo {

    private static void dropAndCollect() {
        for (int attempt = 0; attempt < 5; attempt++) {
            System.gc();
            try {
                Thread.sleep(50);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return;
            }
        }
    }

    public static void main(String[] args) throws Exception {
        Path dir = Files.createTempDirectory("payout-run");

        System.out.println("correct holder, caller forgets close():");
        PayoutFileHandle correct = new PayoutFileHandle(dir.resolve("run-4471.csv"), "PR-4471");
        correct.appendWithdrawal("instr-8812", "26000");
        System.out.println("  open descriptors before drop: " + PayoutFileHandle.OPEN_DESCRIPTORS.get());
        correct = null;
        dropAndCollect();
        boolean correctRan = PayoutFileHandle.CLEANED.await(5, TimeUnit.SECONDS);
        System.out.println("  cleaning action ran within 5s: " + correctRan);
        System.out.println("  open descriptors after: " + PayoutFileHandle.OPEN_DESCRIPTORS.get());

        System.out.println("broken holder (non-static inner State), caller forgets close():");
        LeakyPayoutFileHandle leaky = new LeakyPayoutFileHandle(dir.resolve("run-4472.csv"), "PR-4472");
        leaky = null;
        dropAndCollect();
        boolean leakyRan = LeakyPayoutFileHandle.CLEANED.await(5, TimeUnit.SECONDS);
        System.out.println("  cleaning action ran within 5s: " + leakyRan);

        System.out.println("broken holder (lambda capturing this), caller forgets close():");
        LambdaPayoutFileHandle lambda = new LambdaPayoutFileHandle(dir.resolve("run-4473.csv"), "PR-4473");
        lambda = null;
        dropAndCollect();
        boolean lambdaRan = LambdaPayoutFileHandle.CLEANED.await(5, TimeUnit.SECONDS);
        System.out.println("  cleaning action ran within 5s: " + lambdaRan);

        System.out.println("close() twice on a fresh correct holder:");
        PayoutFileHandle twice = new PayoutFileHandle(dir.resolve("run-4474.csv"), "PR-4474");
        twice.close();
        twice.close();
        System.out.println("  survived two close() calls; open descriptors: "
                + PayoutFileHandle.OPEN_DESCRIPTORS.get());
    }
}
```

Real output, Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64:

```console
$ java CleanerDemo
correct holder, caller forgets close():
  open descriptors before drop: 1
  [cleaner] released payout-file descriptor for PR-4471
  cleaning action ran within 5s: true
  open descriptors after: 0
broken holder (non-static inner State), caller forgets close():
  cleaning action ran within 5s: false
broken holder (lambda capturing this), caller forgets close():
  cleaning action ran within 5s: false
close() twice on a fresh correct holder:
  [cleaner] released payout-file descriptor for PR-4474
  survived two close() calls; open descriptors: 0
```

Three things established. The correct holder's descriptor was released without any `close()` call,
and `OPEN_DESCRIPTORS` went back to zero. Both broken holders' actions did not run — the descriptors
for `run-4472.csv` and `run-4473.csv` stayed open until the JVM exited. And two `close()` calls
produced exactly one `[cleaner]` line and one decrement: the at-most-once guarantee observed rather
than quoted.

**On determinism.** Run five times; all five gave the same three booleans (`true, false, false`).
Not a guarantee — the `true` depends on `System.gc()` being honoured and on the cleaner thread being
scheduled inside five seconds, and a loaded machine or a different collector could turn it into a
spurious `false`. The two `false` results are the robust half: they follow from reachability, not
timing. Report a flaky `true` as flaky; do not report it as a `false`.

### The judgement: safety net, not strategy

A `Cleaner` costs a daemon thread per instance. Measured:

```console
$ java CleanerThreadCount
threads named *Cleaner* at start: 1
after 8 Cleaner.create() calls: 9
delta: 8 (cleaners held: 8)
```

One thread already exists at startup — the JDK's shared `Common-Cleaner`, created by
`jdk.internal.ref.CleanerFactory` as an `InnocuousThread` at `Thread.MAX_PRIORITY - 2`. Each
`Cleaner.create()` adds one more, so eight resource classes each declaring their own
`private static final Cleaner` cost eight always-live daemon threads for work one thread would
serialise fine. That is why the JDK shares `CleanerFactory.cleaner()` across `Inflater`, `Deflater`,
`ZipFile`, `FileCleanable`, `FileChannelImpl`, `NioSocketImpl` and `Arena.ofAuto()`. Share one per
library; the cost of *not* sharing is a thread, and the cost of sharing is that one slow action
delays the others — the `Cleaner` javadoc: "If the cleaning action blocks, it may delay processing
other cleaning actions registered to the same cleaner."

The three approaches, and what each actually costs:

| Approach | When cleanup happens | Deterministic | Costs | Fails when |
|---|---|---|---|---|
| `try`-with-resources alone | at the end of the block, on the caller's thread | yes | nothing beyond a `finally` and suppression bookkeeping | the caller does not write it, or the holder escapes the block |
| `try`-with-resources **plus** a `Cleaner` net | at block end normally; at some unspecified later point if the caller forgot | no for the net | one daemon thread per `Cleaner`, one `PhantomReference` and one action object per instance, plus GC work to enqueue | the action captures the holder; the JVM exits first (`Cleaner` behaviour during `System.exit` is "implementation specific. No guarantees") |
| `finalize()` | at some unspecified point after the object is finalizable | no | an extra GC cycle per finalizable object, a `FinalReference` per instance, resurrection risk, unbounded delay, exceptions silently swallowed | always, in some way — and it is deprecated for removal |

`finalize()`, version facts, all verified in JDK 21: `Object.finalize` carries
`@Deprecated(since="9", forRemoval=true)` in the JDK 21 source, and its javadoc points at
[JEP 421](https://openjdk.org/jeps/421) for "discussion and alternatives", naming
`java.lang.ref.Cleaner`, `PhantomReference` and `AutoCloseable` as the replacements. So: deprecated
since **Java 9**, marked `forRemoval` by JEP 421, and in JDK 21 finalization can be switched off
entirely — `java --help-extra` on 21.0.7 lists `--finalization=<value>` with values `enabled` or
`disabled`, "Finalization is enabled by default", and `java --finalization=disabled -version` runs
clean. **Unverified:** that JEP 421 specifically *targeted JDK 18* — the JEP number and its role are
confirmed from the JDK 21 `Object.finalize` javadoc, but `openjdk.org/jeps/421` returned HTTP 403
from this environment so the target release could not be read from the primary source.

> A `Cleaner` is a safety net for a resource whose leak has a real consequence: it registers a
> `Runnable` that runs after the holder becomes phantom-reachable, on a cleaner-owned thread, at
> most once — and it runs only if that `Runnable` cannot reach the holder.

**Interview:** "Why does your `Cleaner` cleanup never fire?" — because the cleaning action holds a
reference to the object being cleaned, usually via a non-static inner class's `this$0` or a lambda
that touched an instance field, so the object never becomes phantom-reachable.

### Diff vs the real one — `PayoutFileHandle` against the JDK's own `Cleaner` holders

| Axis | `PayoutFileHandle` | `Inflater.InflaterZStreamRef` / `java.io.FileCleanable` |
|---|---|---|
| Edge cases | `channel.isOpen()` guard; a failed close is printed, not propagated | `InflaterZStreamRef.run` reads `address`, zeroes it, calls `end(addr)` only if non-zero — a zeroed address means already released; `FileCleanable` guards on `fd != -1 && handle != -1` |
| Intrinsics | none | none in the cleanup path; the release itself is a `private static native void end(long)` / `cleanupClose0(int, long)` |
| Serialization | not `Serializable`; a live file descriptor has no serial form | same — neither is `Serializable` |
| Null policy | `FileChannel.open` NPEs on a null path; `register` NPEs on either null argument (`Objects.requireNonNull(obj)`, `Objects.requireNonNull(action)`) | `InflaterZStreamRef` explicitly tolerates a null `owner` and registers no cleanable in that case, for subclasses that manage their own lifetime |
| Thread safety | none of my own — `AtomicInteger` for the counter, and `clean()`'s at-most-once is the JDK's; two threads racing `appendWithdrawal` would interleave rows | `InflaterZStreamRef.run` is `synchronized`, and `Inflater` itself guards `address` under a lock, because the cleaner thread and a caller's `end()` can race |
| Allocation tricks | one `State` plus one `PhantomCleanableRef` per holder | `FileCleanable` **extends** `jdk.internal.ref.PhantomCleanable` instead of registering a separate `Runnable`, saving one object per file descriptor — public code cannot do this, `PhantomCleanable` is internal |
| Why the JDK bothers | — | a leaked `z_stream` is native memory the collector cannot see, and a leaked file descriptor is a process-wide limit; both javadocs still say to call `end()`/`close()` explicitly and describe the cleaner as the fallback |

---

## §4.6.9 `[BUILD]` The section-wide §4.6 diff table

Everything §4.6 built, against the JDK class that already solves the same problem. Rows verified
against the JDK 21.0.7 `src.zip` and javadoc; a row with nothing on an axis says so rather than
going blank.

| What we built | JDK counterpart | Edge cases | Intrinsics | Serialization | Null policy | Thread safety | Allocation tricks | Why the JDK bothers |
|---|---|---|---|---|---|---|---|---|
| `QuizStakesException` + `FailureDetail` carrying a `StatusCode` and an immutable context map (order 15) | `java.lang.Throwable` | `getMessage` may be null; a self-suppressing `addSuppressed` throws `IllegalArgumentException`; `initCause` twice throws `IllegalStateException` | no intrinsic in `Throwable` itself; the stack walk is `private native Throwable fillInStackTrace(int)`, and the JIT can elide allocation of a non-escaping throwable | `serialVersionUID = -3042686055658047285L`, "use serialVersionUID from JDK 1.0.2 for interoperability"; `backtrace` is `transient`, so the custom `writeObject` calls `getOurStackTrace()` first to materialise `stackTrace` into the serial form and a null `stackTrace` is written as a one-element sentinel | `null` message and `null` cause both permitted and meaningful; `addSuppressed(null)` throws `NullPointerException` | `addSuppressed` and `getSuppressed` are `public final synchronized`; `fillInStackTrace` is `synchronized` | `UNASSIGNED_STACK` is a shared empty array so an unfilled trace allocates nothing; `SUPPRESSED_SENTINEL` is `Collections.emptyList()` so the `ArrayList` is created lazily on the first `addSuppressed` | a message is for humans and the stack trace is the machine-readable part; our error-code-plus-context design is what `Throwable` deliberately does *not* give you, which is why every real system layers one on top |
| `InsufficientFundsException`, `RestrictedActionException`, `IllegalTransitionException`, `LedgerImbalanceException`, `BonusIneligibleException` (order 15) | `IllegalStateException`, `IllegalArgumentException`, `UnsupportedOperationException` | no state beyond `Throwable`'s | no intrinsic | each declares its own `serialVersionUID`; no custom serial form | inherit `Throwable`'s | inherit `Throwable`'s | none — they are empty subclasses | the JDK's generic unchecked exceptions carry no domain code, so a caller cannot branch on *why*; a domain hierarchy exists precisely to make the code machine-readable |
| The stackless exception via `Throwable(String, Throwable, boolean, boolean)` (order 16) | `jdk.internal.misc.ScopedMemoryAccess.ScopedAccessError` — `super("Invalid memory access", null, false, false)`; also `com.sun.org.apache.xerces.internal.dom.AbortException` — `super(null, null, false, false)` | with `writableStackTrace = false` the constructor sets `stackTrace = null` and skips `fillInStackTrace`, so `getStackTrace()` returns the shared empty `UNASSIGNED_STACK` and `printStackTrace` shows one line; with `enableSuppression = false` it sets `suppressedExceptions = null` and `addSuppressed` then returns after validating its argument only, so try-with-resources silently discards the close failure | no intrinsic | `writeObject` substitutes `SentinelHolder.STACK_TRACE_SENTINEL` for a null `stackTrace`, so a stackless throwable survives a round trip as stackless | still NPEs on `addSuppressed(null)` even when suppression is disabled — validation happens before the disabled check | unchanged | this is *the* allocation trick: skipping the native stack walk is the entire saving, and it scales with depth, which is why the depth-1 versus depth-500 measurement in order 16 diverges | control flow across a subsystem boundary where the trace is never read; the javadoc itself sanctions it for "a virtual machine reusing exception objects under low-memory situations" and for exceptions "repeatedly caught and rethrown… to implement control flow between two sub-systems" |
| The custom `AutoCloseable` with an idempotent `close()` (order 17) | `java.lang.AutoCloseable` vs `java.io.Closeable` | `AutoCloseable.close()` throws `Exception`; `Closeable.close()` narrows it to `IOException` | no intrinsic | neither interface is `Serializable` | neither specifies a null policy — there are no parameters | neither requires thread safety | none | **the distinction people miss:** `Closeable.close()` javadoc — "If the stream is already closed then invoking this method has no effect", a *requirement*. `AutoCloseable.close()` javadoc — "this `close` method is *not* required to be idempotent… However, implementers of this interface are strongly encouraged to make their `close` methods idempotent." Recommendation, not requirement. Both javadocs also advise marking the resource closed **before** throwing |
| The two-resource try-with-resources printing close order and the suppressed exception (order 17) | `java.io.FilterOutputStream.close` | closes are emitted in reverse declaration order, and each close is wrapped so a close failure is added to the primary via `addSuppressed`; `FilterOutputStream.close` does the same by hand: a `closed` flag checked twice around a `synchronized (closeLock)` block, then `flush()` in a `try`, then `out.close()` in the `finally`, and if both fail the flush exception is suppressed **into** the close exception and the close exception is thrown | no intrinsic | not applicable | `FilterOutputStream` NPEs on writing through a null `out` | the `closed` flag is read unsynchronised then re-checked under `closeLock`, so a double `close()` from two threads closes once | the `if (flushException != closeException)` guard avoids the self-suppression `IllegalArgumentException` when `flush()` and `close()` throw the *same* object | a stream chain must not leak the underlying descriptor because an outer `flush()` failed; the JDK chose "release the resource, report the first failure, suppress the second" and try-with-resources encodes the same policy in `javac` |
| The `finally`-return harness that swallows a pending exception (order 18) | nothing — the JDK has no counterpart, because the JDK does not do this | a `return` (or `break`, or `continue`, or a `throw`) inside `finally` discards the in-flight exception entirely; it is not suppressed, not chained, not logged — it is gone | no intrinsic | not applicable | not applicable | not applicable | none | there is no JDK class to point at, which *is* the finding: `javac` permits it, the JLS defines it, and no library in `java.base` uses it. Compare `FilterOutputStream.close` above, which needs exactly this shape and instead rethrows explicitly with `addSuppressed` |
| `CheckedFunction<T,R,E extends Exception>` plus the `unchecked` adapter (order 19) | `java.io.UncheckedIOException` | wraps only `IOException`, nothing wider; `getCause()` is covariantly overridden to return `IOException` so callers unwrap without a cast | no intrinsic | `serialVersionUID = -8134305061645241065L`, plus a custom `readObject` that re-validates the cause is an `IOException` — a hostile stream cannot install a non-`IOException` cause and break `getCause()`'s covariant contract | **both constructors** call `Objects.requireNonNull(cause)`; a null cause is rejected, unlike `RuntimeException` | inherits `Throwable`'s | none | **the single most useful row here.** `Files.lines`, `Stream.map` and every other functional interface in `java.base` declare no checked exception, so when the JDK needed to push an `IOException` through a `Stream` pipeline it reached for exactly workaround one: wrap the checked exception in an unchecked one, keep the cause, and give the caller a typed unwrap. Our `unchecked` adapter is the same move made generic; the JDK's version is narrower on purpose, because a wrapper that accepts any `Exception` tells the caller nothing about what to catch |
| The sneaky-throw utility, and the argument against it (order 19) | nothing in `java.base` uses erasure-based sneaky throw | the throw is invisible to `javac`, so a caller cannot `catch (IOException e)` without a `throws` clause somewhere to license the catch clause, and a `catch (Exception e)` becomes the only option | no intrinsic — the generic cast erases to nothing, so the bytecode is a bare `athrow` | not applicable | not applicable | not applicable | zero: no wrapper object is allocated, which is its only genuine advantage over `UncheckedIOException` | the JDK's answer is `UncheckedIOException` — a real wrapper, a preserved cause, a documented type — not a hole in the checked-exception model. That the JDK had the same problem and chose the allocating solution is the argument |
| The `Cleaner`-based `PayoutFileHandle` (this file, 4.6.7) | `java.lang.ref.Cleaner` and `Cleaner.Cleanable` | `Cleanable.clean()` is "invoked at most once regardless of the number of calls"; all exceptions thrown by a cleaning action are ignored and neither the cleaner nor other actions are affected; behaviour during `System.exit` is "implementation specific. No guarantees" | no intrinsic | not `Serializable` | `register` calls `Objects.requireNonNull` on both `obj` and `action` | the action runs on a cleaner-owned daemon thread, so actions must be prepared to run concurrently with other actions; `Cleaner.create()` rejects a `ThreadFactory` returning a non-`NEW` thread with `IllegalThreadStateException` | `register` allocates one `CleanerImpl.PhantomCleanableRef` per registration; `CleanerFactory.cleaner()` shares one `Common-Cleaner` thread estate-wide so a library need not add one | native memory and OS handles are invisible to the collector, so nothing else in the platform can release them late; `Inflater`'s own javadoc tells subclasses to drop `finalize()` and "use alternative cleanup mechanisms such as `java.lang.ref.Cleaner`" |
| — (the layer underneath) | `PhantomReference` / `ReferenceQueue` | `PhantomReference.get()` is `return null;` unconditionally in JDK 21, so the referent can never be resurrected — the difference from `WeakReference` that makes phantom cleanup safe | no intrinsic; the collector's reference processing is VM-side | `Reference` is not `Serializable` | a `PhantomReference` requires a queue to be useful; the constructor accepts one | `ReferenceQueue.poll`/`remove` are the synchronisation point; `Cleaner` runs one thread blocked in `remove()` | `Reference.clear()` sets `referent = null` so the referent is reclaimable in the next cycle without waiting for the reference object itself | this is the primitive; `Cleaner` is the ergonomic wrapper that adds a thread, a list and the at-most-once guarantee so callers do not hand-roll a queue-draining loop |
| Any of our value/result types (order 19's adapters return them) | `Optional`, `Stream` | — | no intrinsic | **neither is `Serializable`**: `public final class Optional<T> {` has no `implements` clause, and `BaseStream<T, S>` extends only `AutoCloseable`. So an `Optional` field in a serializable aggregate is a `NotSerializableException` waiting to happen, and a `Stream` cannot be a field of anything persisted | `Optional.of` NPEs; `Optional.ofNullable` does not | `Optional` is immutable and safe to publish; a `Stream` is single-use and not thread-safe | `Optional.empty()` returns a shared singleton, so the empty case allocates nothing | `Optional` is documented as a value-based class whose identity is deliberately unspecified — making it `Serializable` would freeze an identity and a serial form the JDK wants free to change. `Stream` is a pipeline, not data; there is nothing coherent to serialise |

---

## Pitfalls

### A cleaning action that captures the object it is cleaning

**Wrong**

```java
private final class State implements Runnable {          // non-static
    private final FileChannel channel;
    State(FileChannel channel) { this.channel = channel; }
    @Override public void run() {
        try { if (channel.isOpen()) { channel.close(); } }
        catch (IOException e) { /* ignored */ }
        finally { CLEANED.countDown(); }
    }
}

// inside the constructor:
this.cleanable = PAYOUT_CLEANER.register(this, new State(channel));
```

```console
broken holder (non-static inner State), caller forgets close():
  cleaning action ran within 5s: false
```

`javap -p` shows why: `final LeakyPayoutFileHandle this$0;` — a field no source line declares.

**Right**

```java
private static final class State implements Runnable {   // static
    private final FileChannel channel;
    private final String runId;
    State(FileChannel channel, String runId) { this.channel = channel; this.runId = runId; }
    @Override public void run() {
        try { if (channel.isOpen()) { channel.close(); } }
        catch (IOException e) { /* logged elsewhere */ }
        finally { OPEN_DESCRIPTORS.decrementAndGet(); CLEANED.countDown(); }
    }
}
```

```console
correct holder, caller forgets close():
  [cleaner] released payout-file descriptor for PR-4471
  cleaning action ran within 5s: true
  open descriptors after: 0
```

`static` removes `this$0`; copying `runId` in removes the last reason to reach outward.

**Why people believe it:** an inner class is the ordinary way to write a helper that belongs to one
outer class, and it usually *is* the right choice. Nothing in the `register(this, state)` call site
hints that this one case inverts the rule, and the failure is silent, so the belief is never
contradicted by a stack trace.

### Treating a `Cleaner` as a substitute for `close()`

**Wrong**

```java
PayoutFileHandle payoutFile = new PayoutFileHandle(dir.resolve("run-4471.csv"), "PR-4471");
payoutFile.appendWithdrawal("instr-8812", "26000");
// no close() — "the Cleaner will handle it"
```

The descriptor stays open until the collector notices, the cleaner thread is scheduled, and the
action completes — an interval with no upper bound. At four payout windows a day the descriptors are
survivable; at 11k card withdrawals a day through a per-request holder they are not, and the failure
arrives as `EMFILE` under load rather than at the leak site.

**Right**

```java
try (PayoutFileHandle payoutFile = new PayoutFileHandle(dir.resolve("run-4471.csv"), "PR-4471")) {
    payoutFile.appendWithdrawal("instr-8812", "26000");
}
```

`close()` calls `cleanable.clean()`, which releases the descriptor now *and* unregisters the action,
so the phantom reference is dropped and the GC never has to process it. The `Cleaner` remains as the
net for the code path that forgets.

**Why people believe it:** the `Cleaner` demonstrably works when you drop the reference, so it looks
like a complete mechanism. `Inflater`'s javadoc is blunt about the intended split — "To release
resources used by this `Inflater`, the `end()` method should be called explicitly" — and only then
mentions the cleaner.

### Believing `System.gc()` guarantees the action runs

**Wrong**

```java
payoutFile = null;
System.gc();
Thread.sleep(100);
System.out.println("cleaned: " + descriptorWasReleased);   // reads a plain boolean
```

Three separate holes. `System.gc()` is a hint — its javadoc says the JVM "makes a best effort", and
`-XX:+DisableExplicitGC` turns it into a no-op outright. Enqueueing a phantom reference and running
the action happen after the collection, on another thread, with no bound on when. And the flag is
read without synchronisation, so `main` may never observe the cleaner thread's write at all.

**Right**

```java
correct = null;
for (int attempt = 0; attempt < 5; attempt++) { System.gc(); Thread.sleep(50); }
boolean correctRan = PayoutFileHandle.CLEANED.await(5, TimeUnit.SECONDS);
System.out.println("  cleaning action ran within 5s: " + correctRan);
```

The latch supplies the happens-before edge and the timeout makes the negative case a bounded
observation rather than a hang. State the instrument when you report the result, and say when a run
was flaky.

**Why people believe it:** `System.gc()` usually does collect, so the pattern usually works on a
quiet machine, and a test that passes ninety-nine times reads as deterministic. It then fails in CI
under load, which is the worst place to learn that it was never a guarantee.

### Believing `AutoCloseable.close()` is required to be idempotent

**Wrong**

```java
// "close() is idempotent, that's the AutoCloseable contract"
FundsLedgerBatchWriter writer = openBatchWriter();
writer.close();
writer.close();   // assumed harmless for any AutoCloseable
```

For an arbitrary `AutoCloseable` the second call may double-decrement a count, emit a second commit
record, or throw. The JDK 21 `AutoCloseable.close()` javadoc: "this `close` method is *not* required
to be idempotent. In other words, calling this `close` method more than once may have some visible
side effect, unlike `Closeable.close` which is required to have no effect if called more than once."
The next sentence adds that implementers are "strongly encouraged" to make it idempotent —
encouragement, not contract.

**Right**

```java
@Override
public void close() {
    cleanable.clean();   // "invoked at most once regardless of the number of calls to clean"
}
```

```console
close() twice on a fresh correct holder:
  [cleaner] released payout-file descriptor for PR-4474
  survived two close() calls; open descriptors: 0
```

One `[cleaner]` line, one decrement, from two `close()` calls. Where there is no `Cleanable` to
delegate to, write the flag yourself and mark the resource closed *before* doing anything that can
throw — both javadocs advise exactly that.

**Why people believe it:** `Closeable` is the interface everyone met first, via `InputStream` and
`OutputStream`, and it *does* require idempotence. `AutoCloseable` was retrofitted underneath it in
Java 7 with a deliberately weaker contract so that resources whose close genuinely cannot be
repeated could still work with try-with-resources. The subtype is stricter than the supertype, which
is the reverse of the direction people expect to have to check.

---

## Cheat sheet

| Fact | Value in Java 21 |
|---|---|
| `Cleaner` trigger | the registered object becomes **phantom-reachable** |
| The one rule | the action must not reach the registered object |
| Action shape | `static` nested class implementing `Runnable`, holding only raw handles |
| Forbidden shapes | non-static inner class (`this$0`), lambda touching any instance field, anonymous class |
| `Cleanable.clean()` | "invoked at most once regardless of the number of calls" — free idempotence |
| Action thread | a `Cleaner`-owned daemon thread; actions may run concurrently with each other |
| Action exceptions | ignored; cleaner and other actions unaffected |
| `System.exit` | cleaner behaviour "implementation specific. No guarantees" |
| Cost per `Cleaner.create()` | one daemon thread — measured 1 to 9 threads over 8 `create()` calls |
| JDK's shared cleaner | `jdk.internal.ref.CleanerFactory.cleaner()`, thread `Common-Cleaner`, `MAX_PRIORITY - 2` |
| Verified JDK `Cleaner` users | `Inflater`, `Deflater`, `ZipFile`, `FileCleanable`, `FileChannelImpl`, `NioSocketImpl`, `Arena.ofAuto()`, `Timer`, `Perf` |
| `PhantomReference.get()` | `return null;` unconditionally — no resurrection |
| `AutoCloseable.close()` | throws `Exception`; idempotence **encouraged**, not required |
| `Closeable.close()` | throws `IOException`; "if already closed… has no effect" — **required** |
| Stackless throwable | `Throwable(msg, cause, false, false)` — no `fillInStackTrace`, `addSuppressed` becomes a validate-and-return |
| `Throwable.serialVersionUID` | `-3042686055658047285L` ("from JDK 1.0.2") |
| `UncheckedIOException.serialVersionUID` | `-8134305061645241065L`; both constructors `requireNonNull(cause)` |
| `finalize()` | `@Deprecated(since="9", forRemoval=true)`; JEP 421; `--finalization=disabled` works on 21.0.7 |
| `Optional` / `Stream` serializable | no, and no |
| Strategy vs net | try-with-resources is the strategy; `Cleaner` is the net |

---

## Self-test

**Q1.** Your `Cleaner` action never runs and no exception is logged. What is the first thing you look at, and how do you confirm it from the class file?

<details><summary>Answer</summary>

Whether the action can reach the object it is cleaning. That is the only failure mode that produces
total silence, because the trigger is unreachability and a reachable object never goes phantom.
Confirm it with `javap -p` on the action's class: a non-static nested class shows a field
`final <Enclosing> this$0;` that appears in no source line, and its constructor takes the enclosing
type as its first parameter. For a lambda, `javap -p` on the holder shows the desugared body as an
*instance* method (`private void lambda$new$0(java.lang.String)` rather than `private static`), and `javap -c -p`
on the constructor shows `aload_0` among the `invokedynamic` captured arguments with the holder's
type in the indy descriptor — `(LLambdaPayoutFileHandle;Ljava/lang/String;)Ljava/lang/Runnable;`.
</details>

**Q2.** Why is `close() { cleanable.clean(); }` idempotent when the `AutoCloseable` contract does not require idempotence?

<details><summary>Answer</summary>

Because the guarantee comes from `Cleaner.Cleanable`, not from `AutoCloseable`. The `Cleanable.clean`
javadoc says "Unregisters the cleanable and invokes the cleaning action. The cleanable's cleaning
action is invoked at most once regardless of the number of calls to `clean`." The implementation
removes the node from the cleaner's list under a lock before performing the action, so a second call
finds nothing to do. `AutoCloseable.close()` merely says implementers are "strongly encouraged" to be
idempotent; `java.io.Closeable.close()` is the one that *requires* it ("if the stream is already
closed then invoking this method has no effect"). Delegating to `clean()` is the rare case where you
get the stronger property without writing a flag.
</details>

**Q3.** What did the five `System.gc()` calls plus a `CountDownLatch.await(5, SECONDS)` actually establish, and what did they not?

<details><summary>Answer</summary>

A `true` from `await` establishes that the action ran and that `main` observed it with a proper
happens-before edge — the latch countdown in the action's `finally` synchronises with the successful
`await`. It does not establish that the action was *guaranteed* to run: `System.gc()` is only a hint
(and `-XX:+DisableExplicitGC` makes it a no-op), reference enqueueing is asynchronous, and the
cleaner thread's scheduling is not under the test's control, so a loaded machine could produce a
spurious `false`. A `false` for the two broken holders is the robust half of the result, because it
follows from reachability rather than from timing — no amount of extra waiting or extra collections
can make a strongly reachable object phantom-reachable.
</details>

**Q4.** The lambda version captured `this` for `channel` but captured `runId` as a separate `String`. Why the difference, and what does it tell you about reviewing this code?

<details><summary>Answer</summary>

`channel` inside the lambda resolves to the field `this.channel`, and reading a field requires the
receiver, so `this` joins the capture set. `runId` resolves to the *constructor parameter*, which
shadows the field of the same name, and an effectively-final local is captured by value — hence the
`Ljava/lang/String;` in the indy descriptor alongside the `LLambdaPayoutFileHandle;`. The review
lesson is that there is no source-level signal distinguishing the two: the same identifier spelling
produces a fatal capture in one case and a harmless one in the other, depending on whether a local
happens to shadow. That is why the rule is structural — the action must be a `static` nested class,
so the compiler cannot capture anything you did not pass as an argument.
</details>

**Q5.** Eight resource classes each declare `private static final Cleaner CLEANER = Cleaner.create();`. What does that cost, and what does the JDK do instead?

<details><summary>Answer</summary>

Eight always-live daemon threads. `Cleaner.create()` starts one thread per cleaner, which the
javadoc states and a thread count confirms: 1 thread matching `*Cleaner*` at startup, 9 after eight
`create()` calls. The JDK shares a single `Common-Cleaner`, created once by
`jdk.internal.ref.CleanerFactory` as an `InnocuousThread` at `Thread.MAX_PRIORITY - 2`, and uses it
from `Inflater`, `Deflater`, `ZipFile`, `FileCleanable`, `FileChannelImpl`, `NioSocketImpl`,
`Arena.ofAuto()` and others. The trade is stated in the `Cleaner` javadoc: sharing means "if the
cleaning action blocks, it may delay processing other cleaning actions registered to the same
cleaner", so all actions on a shared cleaner must be quick and non-blocking. One cleaner per library,
not one per class.
</details>

**Q6.** Which JDK class is the honest answer to "how does the JDK itself push a checked exception through a `Function`?", and why is it narrower than a generic `unchecked` adapter?

<details><summary>Answer</summary>

`java.io.UncheckedIOException`. Every functional interface in `java.base` declares no checked
exception, so `Files.lines` and friends wrap the `IOException` in an unchecked carrier — exactly the
wrap-and-rethrow workaround. It is narrower deliberately: it accepts only an `IOException`, both
constructors `Objects.requireNonNull(cause)`, `getCause()` is covariantly overridden to return
`IOException` so callers unwrap without a cast, and a custom `readObject` re-validates the cause's
type so a hostile stream cannot break that covariance. A generic `unchecked(CheckedFunction)` adapter
that wraps any `Exception` in a `RuntimeException` gives the caller no type to catch and no typed
unwrap — it moves the problem rather than solving it.
</details>

**Q7.** State the version facts about `finalize()` precisely, and say what would have to be true for it to be the right choice today.

<details><summary>Answer</summary>

`Object.finalize` carries `@Deprecated(since="9", forRemoval=true)` in the JDK 21 source, so it has
been deprecated since Java 9 and marked for removal by JEP 421, which its javadoc links to for
"discussion and alternatives" — naming `java.lang.ref.Cleaner`, `PhantomReference` and a `close()`
method with `AutoCloseable`. In JDK 21 finalization can be switched off entirely with
`--finalization=disabled` (listed by `java --help-extra`, enabled by default), which means code
relying on it can already be running on a JVM where it never fires. Nothing would make it the right
choice today: it costs an extra GC cycle per finalizable object, allows resurrection, swallows
exceptions, and offers no ordering or timing guarantee — every property `Cleaner` was designed to
fix.
</details>

**Q8.** `FilterOutputStream.close` throws if both `flush()` and `out.close()` fail. Which exception propagates, and why is there an identity check in the code?

<details><summary>Answer</summary>

The **close** exception propagates, with the flush exception attached to it via `addSuppressed` — the
opposite direction from try-with-resources, which propagates the body's exception and suppresses the
close's. The JDK's reasoning is that the flush failure is what caused the close attempt to matter,
but the resource release is the outcome the caller must know about. The identity check
`if (flushException != closeException)` exists because `flush()` and `out.close()` can throw the
*same* `Throwable` object — a `BufferedOutputStream` chain can propagate one instance out of both
calls — and `Throwable.addSuppressed` throws `IllegalArgumentException` with the message
"Self-suppression not permitted" if you hand it `this`. Without the guard, a real I/O failure would
be replaced by a confusing `IllegalArgumentException`.
</details>

---

## Open questions

- **JEP 421's target release.** The JEP number and its role are confirmed from the JDK 21
  `Object.finalize` javadoc, which links `https://openjdk.org/jeps/421`, and the
  `--finalization=<value>` option is confirmed from `java --help-extra` on 21.0.7. That the JEP
  *targeted JDK 18* specifically could not be confirmed — `openjdk.org/jeps/421` returned HTTP 403
  from this environment. Reading the JEP's own "Release" field, or the JDK 18 release notes, would
  settle it.

---

**Leaves covered:** 4.6.7, 4.6.9 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 857
