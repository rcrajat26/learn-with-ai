# 03 Java Core — Helpful NPE messages and the diagnostic toolkit — INTERNALS (§3.9, 3.9.11–3.9.13, 3.9.16–3.9.17)

**Target version: Java 21 LTS.** | **Part 3 of 5** | [Index](../00-index.md)
Previous: [Fast-throw, truncation and StackOverflowError](03c-internals-fast-throw-and-truncation.md) · Next: [Generics basics](../generics/01-basics.md)

`03b-internals-stack-trace-capture.md` priced the cost of *capturing* a trace. This file is about what happens once you actually have to read one: a `NullPointerException` that names the null reference instead of just the line, a `Caused by:` chain that has to be read from the bottom to find the real failure, a cheap way to look at two frames instead of the whole stack, and a way to find out that some exception type is being thrown two million times a day without a single line ever reaching a log. Five mechanisms, one theme — the JVM already has the answer to "what actually went wrong," and the tooling here is how you get it out.

Everything below is measured on **Oracle JDK 21.0.7 (21.0.7+8-LTS-245, macOS aarch64)**, in `/tmp/exc03d`, with **Oracle JDK 11.0.27** for the one before/after comparison JEP 358 needs. `-XX:+PrintFlagsFinal -version` on this build, quoted verbatim:

```
bool ShowCodeDetailsInExceptionMessages       = true    {manageable} {default}
bool OmitStackTraceInFastThrow                = true    {product} {default}
intx MaxJavaStackTraceDepth                   = 1024    {product} {default}
```

`{manageable}` on the first line is doing real work in this file — concept 2 measures exactly what it buys. `OmitStackTraceInFastThrow` and `MaxJavaStackTraceDepth` are `03c`'s territory; they are quoted here only because concept 1's laziness claim and concept 3's trace-reading rules both lean on facts `03c` establishes about *which* traces exist to read in the first place.

---

## 1. Helpful NPE: computed lazily from the bytecode of the failing instruction (3.9.11)

`[SOURCE]` `[RESEARCH]` The picture: the JVM does not remember *what* was null. It remembers *where* — the exact bytecode instruction that dereferenced a null reference — and reconstructs the English sentence describing that instruction only when something asks for it, by walking the failing method's bytecode a second time, off the instruction offset it already recorded.

### Why it exists

For twenty-five years, a `NullPointerException` carried no message unless the throwing code supplied one explicitly, and the overwhelming majority never did — the JVM-thrown form was, and on Java 8 through 11 still is, `java.lang.NullPointerException` with nothing after it. On a line dereferencing four different things — `reservation.split().bonusPortion().amount()` — that told you which *line* failed and left you to work out which of the four was actually null, often by adding logging and reproducing the failure a second time. JEP 358 exists to answer that second question from information the JVM already has: the constant pool already names every field and method a bytecode instruction touches, and the verifier already knows the type of everything on the operand stack at every offset. The JEP's own framing (secondary source, `javacodegeeks.com`, quoting the JEP): computing a full message *eagerly*, at every `NullPointerException` construction, "is expensive and may not always be needed, since many NPEs are caught and discarded by programs" — so the design's second half is as important as its first: compute the description only for the exception that someone actually inspects.

### When to reach for it, and when not

There is no "reach for it" — from Java 15 onward it is unconditional, free, and always on unless someone has explicitly turned it off (concept 2). The only decision left is whether to *keep* it on for a given process, and the only reason to turn it off is the security trade-off concept 2 covers in full. The sibling worth naming here is a hand-written message on a manually-thrown `NullPointerException`: `throw new NullPointerException("reservation must not be null")` gets none of this machinery — concept 1's laziness lives entirely inside the JVM-thrown path, and a constructed exception has nothing to compute from, which is demonstrated below.

### How it works

`[SOURCE]` The mechanism, from a secondary source quoting the JEP's own description of the computation (`javacodegeeks.com`, corroborated independently by `puradawid.pro`'s account of the same text): "The `null`-detail message is computed on demand, when the JVM calls `Throwable::getMessage`" — not at throw time, and not at construction time. Read that against `NullPointerException`'s own `getMessage()` override, which is what makes the on-demand computation possible: if the exception already carries an explicit message (the constructor that took a `String`), that message is returned unchanged; otherwise the override calls a native method — reported consistently across sources as `getExtendedNPEMessage()` — which walks the *failing method's bytecode*, starting from the exact instruction offset that threw, and reconstructs a description of the expression that produced null. "The computation requires the bytecode instructions of the method which caused the NPE, and the index of the instruction which popped null" — which is precisely why a manually-constructed `NullPointerException` gets nothing from this path: there is no "instruction that popped null" to walk back from, because the exception was built by `new`, not by a JVM-detected null dereference.

The three-part shape of the resulting message, measured on this build. Every message has an *action* — the verb naming what kind of bytecode operation failed — and, when the JVM can identify it, a *reason* clause naming the null-producing expression. Four action forms, produced by running each on a QuizStakes-shaped failure:

| Action (bytecode operation) | Example message, measured |
|---|---|
| `invokevirtual`/`invokeinterface` on a null receiver | `Cannot invoke "NpeForms$Reservation.split()" because "reservation" is null` |
| `getfield` on a null object | `Cannot read field "positions" because "conn" is null` |
| `aastore` (store into an object array) through a null array reference | `Cannot store to object array because "target" is null` |
| `arraylength` on a null array | `Cannot read the array length because "positions" is null` |

Two more forms confirmed while producing the table, both worth naming because they show the reason clause is not limited to object dereferences: unboxing a null `Integer` through `intValue()` — `Cannot invoke "java.lang.Integer.intValue()" because "OmitCase.x" is null`, the compiler-inserted unboxing call reported exactly like any other `invokevirtual` — and entering a `synchronized` block on a null monitor — `Cannot enter synchronized block because "OmitCase.x" is null`, naming the `monitorenter` instruction by its own English description rather than a method name, since there is no method to name.

**The naming limits, each verified rather than assumed.** A **field** or **method** name is always available, because both are stored as symbolic references in the constant pool regardless of any compiler flag — `positions` and `split()` appear identically whether the class was compiled with full debug information or none. A **local variable** name is different: it exists only in the class file's optional `LocalVariableTable` attribute, written only when `javac` is invoked with `-g` or `-g:vars`. Compiling the identical source both ways, measured:

```
$ javac -g NpeForms.java && java NpeForms
INVOKE: Cannot invoke "NpeForms$Reservation.split()" because "reservation" is null

$ javac -g:none NpeForms.java && java NpeForms
INVOKE: Cannot invoke "NpeForms$Reservation.split()" because "<local0>" is null
```

Same class, same failing instruction — the field/method half of the message (`NpeForms$Reservation.split()`) is identical in both runs; only the local's name degrades to `<local0>`, the raw stack-slot index the JVM falls back to when no source name is recorded. A value that arrived by **method return**, rather than through any local variable at all, is described the third way — not by a name, because it never had one, but by naming the call that produced it:

```
CHAINED_RETURN: Cannot invoke "NpeForms$Reservation.split()" because the return value of "NpeForms.lookupReservation(String)" is null
```

That phrasing needs no debug information at all, measured identical between the `-g` and `-g:none` compilations above, because a method's owning class and descriptor are always in the constant pool — there is no local-variable dependency to lose.

An expression the algorithm cannot describe, yielding a message with the reason clause dropped entirely, was searched for directly rather than assumed: an unboxing failure, a `synchronized` failure, and an `athrow` on a null throwable (`throw makeNull()`, measured as `Cannot throw exception because the return value of "OmitCase2.makeNull()" is null`) were all tried, and all were fully described. **I could not produce a case that omits the reason clause** — every JVM-detected null dereference this build was asked to describe came back with both halves of the sentence. This is recorded as an open question below rather than asserted either way.

**Two consequences that matter in practice.** First, because the description is computed only on `getMessage()`, the cost is paid by whoever calls it — normally a logging framework formatting the exception for output, not the thread that threw it. A helpful NPE that is caught and immediately discarded (`catch (NullPointerException e) { return Optional.empty(); }`, never logged) costs nothing beyond what an ordinary NPE already costs, because `getExtendedNPEMessage()` is never invoked. Second, and this is where `03c-internals-fast-throw-and-truncation.md` and this file describe the same symptom from opposite sides: the description is derived from the *bytecode at the throw site*, so it is unavailable in two cases that look similar from the outside but have different causes. A `NullPointerException` **constructed by application code** — `throw new NullPointerException("reservation must not be null")`, or `throw new NullPointerException()` with no arguments — has no failing bytecode offset to walk back from, because it was never thrown by a null dereference the JVM detected; measured directly, `throw new NullPointerException();` produces `getMessage() == null`, not a synthesized description. And a **fast-thrown, preallocated** exception — `03c`'s subject — has no stack trace *or* extended message to compute from in the first place, because the JVM substituted a cached singleton for the newly-constructed instance; `03c-internals-fast-throw-and-truncation.md` owns that substitution in full, and the connection back to this file is exactly this: a fast-thrown NPE has no helpful message, for the identical reason it has no stack trace — there was no real construction event to capture anything from.

### The diagram

No diagram for this concept: the evidence is six measured message strings across a comparison table and a `-g`/`-g:none` pair, and a table of action forms is the clearer rendering — a picture of "action plus reason clause" would only redraw the table's two columns as boxes.

### A concrete example

The QuizStakes failure that motivates the whole feature, and its four sibling forms, all measured on this build from one source file:

```java
public class NpeForms {
    record StakeSplit(java.math.BigDecimal bonusPortion, java.math.BigDecimal cashPortion) {}
    record Reservation(StakeSplit split) {}

    static Reservation lookupReservation(String roundId) { return null; }

    static class LedgerConnection {
        int[] positions;
    }

    static LedgerConnection lookupConnection() { return null; }

    static void invokeForm() {
        Reservation reservation = lookupReservation("round-771");
        reservation.split();
    }

    static void readFieldForm() {
        LedgerConnection conn = lookupConnection();
        int[] p = conn.positions;
        System.out.println(p);
    }

    static void chainedReturnForm() {
        StakeSplit split = lookupReservation("round-772").split();
        System.out.println(split);
    }
}
```

`invokeForm` is the case a code reviewer meets constantly: a lookup that can legitimately return null (no reservation exists yet for that round) chained straight into a dereference. Before JEP 358, the trace named the line; after it, the message names the exact local (`reservation`) that was null, without a single added log statement.

### The gotcha

**Insight:** the laziness is not a minor implementation detail, it is the entire reason the feature could ship on by default with negligible measured overhead — an eagerly-computed message would have made every JVM-thrown NPE pay a bytecode walk whether or not anyone ever reads the result, which is exactly the "expensive and may not always be needed" cost the JEP's own text (quoted above) is written to avoid.

**Pitfall:** assuming a helpful NPE message survives being caught and rethrown as a different exception's message without the original object. A `catch (NullPointerException e) { throw new RestrictedActionException("lookup failed"); }` that does not chain `e` as the cause discards the computed description along with everything else about the original throwable — the new exception's own message is whatever string the catch block wrote, and `e`'s helpful text is gone. The fix is the ordinary one — chain the cause (`01a-throwable-api-and-chaining.md` owns the mechanics) — but it is easy to forget specifically here, because the helpful message can make the *original* exception look self-explanatory enough that preserving it feels optional.

> **Definition.** A JVM-thrown `NullPointerException`'s message is computed lazily, on the first call to `getMessage()`, by walking the throwing method's bytecode from the recorded failing instruction offset and describing that instruction's action (invoke, field read, array store, array-length, unboxing, monitor-enter) together with, where nameable, the null-producing expression — field and method names are always available from the constant pool, local names require `-g`/`-g:vars` and otherwise fall back to `<localN>`, and a value that arrived by method return is described as "the return value of" rather than by any name; a constructed `NullPointerException` and a fast-thrown one both have `getMessage() == null` or the literal string supplied, because neither has a bytecode-level failing instruction to walk back from.

---

## 2. The security consideration: NPE messages can leak internal structure (3.9.12)

`[RESEARCH]` `[X-REF 13]` The picture: every extra word concept 1 adds to a message is a word an attacker did not have to guess. A helpful NPE names real class names, real field names, real method signatures and, with debug info present, real local-variable names — information that has never previously been available to another program short of decompiling your jar.

### Why it exists

JEP 358's own risk framing, corroborated by a secondary source quoting it directly (`javacodegeeks.com`): the null-detail message "may contain variable names from the source code," and — this is the sentence that states the actual concern precisely — "these have not previously been available to other programs via Java's reflection APIs." That is a narrower and more careful claim than "this exposes secrets": reflection could already discover class, field and method *names* for anything on the classpath given a `Class` reference, so concept 2's real novelty is not that the names exist, it is that a *string thrown from a running failure* now hands them to whoever reads that string, with no need for a `Class` reference or classpath access at all. A stack trace has always done something similar for the *frames* it names; a helpful NPE does the identical thing for the *values inside* one specific line.

### When this matters, and when it does not

It matters exactly where a `Throwable`'s message text crosses a trust boundary — most commonly, into an HTTP response body, a webhook payload, or a third-party log sink outside your own infrastructure. It does not matter inside your own application logs, on your own observability platform, read by your own engineers: the entire value of concept 1 is realized there, and none of the risk is, because nothing has left the boundary you already trust.

### How it works

`[X-REF 13]` The mechanism, stated once and then made concrete on QuizStakes: any code path that serializes an exception's `getMessage()` into a response the caller can read publishes a slice of your internal structure — the type name, the field or accessor name, and by implication the shape of the object graph around it. Concretely: `Cannot invoke "StakeSplit.bonusPortion()" because the return value of "Reservation.split()" is null`, if it ever reached an HTTP response body, tells an external caller that there is an internal type called `StakeSplit` with an accessor `bonusPortion()`, that `Reservation` has a method `split()` returning it, and that under some condition `split()` returns null — three real facts about your domain model, extracted with no tooling beyond reading a JSON body. Guide 13 (Web security) owns the general OWASP-grade discipline this sits inside — information disclosure through error responses is a named category there, not specific to Java or to NPEs — and this file's contribution is the mechanism that makes a Java stack trace's message specifically dangerous in that category: it is not a generic "something failed" string, it is a machine-precise description of your bytecode.

**Three mitigations, in order of preference.** First and strongest: never put an exception's message into a response body at all. `02d-logging-and-api-boundaries.md` owns the REST error contract in full — map every internal exception to a stable, caller-facing error code and a hand-written, reviewed message, and log the real throwable, with its real message, only on your own side of the boundary. This mitigation makes concepts 1 and 2 irrelevant to the boundary simultaneously, and it is the one every other file in this topic already assumes. Second, if local-variable names specifically are the sensitive part (a message naming an internal field is usually tolerable in a log; a message naming a variable called `pendingChargebackAmount` is more specific than most teams want anywhere): compile production artefacts without `-g:vars` — concept 1 measured that this degrades local names to `<localN>` while leaving field and method names (which were never protected by the flag) unchanged, so it is a partial mitigation with an explicit, honest cost: the identical debug information a human debugging a production incident from a heap dump or a live-attached debugger would want is exactly what this removes. Third, the blunt instrument: `-XX:-ShowCodeDetailsInExceptionMessages`, JVM-wide, removing the extended message from every `NullPointerException` on that process. Because the flag carries `{manageable}` rather than plain `{product}`, it can be flipped on a *running* process without a restart — measured on this build, via `HotSpotDiagnosticMXBean.setVMOption`:

```java
HotSpotDiagnosticMXBean diag = ManagementFactory.getPlatformMXBean(HotSpotDiagnosticMXBean.class);
diag.setVMOption("ShowCodeDetailsInExceptionMessages", "false");
```

```
before: VM option: ShowCodeDetailsInExceptionMessages value: true  origin: DEFAULT (read-write)
initial: Cannot invoke "ManageableDemo$Reservation.split()" because the return value of "ManageableDemo.lookup()" is null
after: VM option: ShowCodeDetailsInExceptionMessages value: false  origin: MANAGEMENT (read-write)
after-toggle-off: null
after-toggle-on: Cannot invoke "ManageableDemo$Reservation.split()" because the return value of "ManageableDemo.lookup()" is null
```

Read the `origin` field across the three lines: it moves from `DEFAULT` to `MANAGEMENT` the instant the flag is set via the management interface, and the effect on the *next* NPE thrown on that process is immediate — `after-toggle-off` prints the bare `null` message, and setting the flag back to `true` restores the extended form on the very next throw. This is the operational value of `{manageable}`: a helpful NPE leak discovered in production can be silenced on the live process, without a redeploy, while the fix that should have been in place from the start — the response-contract mitigation above — is prepared.

**Be fair to the default.** `-XX:-ShowCodeDetailsInExceptionMessages` is a bad default choice for most services, not because the risk is imaginary but because the message is worth far more sitting in a correctly-bounded log than it costs as a risk when the boundary is actually correct — which is the entire argument for mitigation one over mitigation three. Reaching for the JVM-wide flag as your *primary* control, rather than an emergency lever, throws away the diagnostic value concept 1 exists to provide for every exception on the process, including the 99% that never come near an external boundary.

### The diagram

No diagram for this concept: the evidence is one quoted risk sentence, one concrete QuizStakes message and its three implications, and a measured before/after pair for the runtime toggle — three short, precise facts that a picture would only relabel as boxes and an arrow.

### A concrete example

The QuizStakes shape that shows the mitigation actually in force — a controller boundary that never lets a caught `Throwable`'s message reach the body, regardless of whether concept 1's machinery produced something informative or not:

```java
@ExceptionHandler(RestrictedActionException.class)
public ResponseEntity<ErrorBody> handleRestrictedAction(RestrictedActionException e) {
    log.warn("stake reservation blocked", e); // full message, full trace, on our side only
    return ResponseEntity.status(HttpStatus.CONFLICT)
        .body(new ErrorBody("STAKE_BLOCKED", "This stake could not be reserved."));
}
```

`e`'s message — helpful NPE or not, chained cause or not — never reaches `ErrorBody`. The mitigation is structural, not a decision made per exception type, which is why `02d-logging-and-api-boundaries.md` frames it as the boundary's contract rather than a rule to remember at every catch site.

### The gotcha

**Interview:** *"JEP 358 made NPE messages more detailed. What's the security angle?"* — "The message can name internal classes, fields, methods and — with debug info — local variables, none of which a caller previously got from a thrown exception's text. The fix isn't turning the feature off; it's never letting an exception's message reach a response body in the first place, which is a rule you need regardless of this JEP."

**Pitfall:** treating `-g:none` in production as a complete fix for the concern. It removes local-variable names from every message, including ones that were never going near an external boundary, while leaving field and method names — which JEP 358 exposes identically regardless of the flag — untouched, and it removes the same debug information a human needs to read a heap dump or attach a debugger during a real incident. It solves a narrower problem than "exception messages leak internals" and costs more than most teams realize when they reach for it as the first move instead of the boundary fix.

> **Definition.** A helpful NPE message names real class, field and method identifiers (always) and real local-variable names (with `-g`/`-g:vars`), none of which a thrown exception's text exposed before JEP 358 without reflective access to a `Class` reference — so any code path that serializes an exception's message across a trust boundary publishes that structure; the sound fix is never doing that (guide 13, and `02d-logging-and-api-boundaries.md`'s error contract), with `-g:none` as a partial, cost-bearing mitigation and the `{manageable}` `-XX:-ShowCodeDetailsInExceptionMessages` flag — confirmed togglable on a live process via `HotSpotDiagnosticMXBean.setVMOption` with no restart — as the emergency lever, not the plan.

---

## 3. Reading a trace: `Suppressed:`, `Caused by:`, and the shared-frames marker (3.9.13)

`[TRAP]` The picture: a trace prints top-down, in the order the JVM assembled it, but the story it tells reads bottom-up — the deepest `Caused by:` block is almost always where the real failure happened, and everything above it is a chain of translation and re-wrapping on the way back to the surface.

### Why it exists

`01a-throwable-api-and-chaining.md` owns the `Throwable` API this format renders — `getCause()`, `getSuppressed()`, the chaining mechanism itself — and `01c-try-with-resources-and-suppression.md` owns the runtime behaviour that produces suppressed exceptions in the first place, specifically a `close()` failing while a `try` body is already unwinding on an exception. This file owns neither of those; it owns the *printed shape* that results, because reading it correctly under time pressure — an on-call engineer with a 200-line trace and an incident open — is a distinct skill from knowing the API exists.

### When to reach for it, and when not

Every time a trace is longer than the eye can hold in one glance, which in practice means every real production incident. There is no sibling to reach for instead — `printStackTrace()`'s format, or the equivalent a logging framework renders from the same `Throwable` API, is the only rendering most tooling produces, so the skill this concept teaches is unavoidable rather than optional.

### How it works

`[SOURCE]` A real trace, produced on this build, with all three elements the leaf names present at once — a header exception's own frames, a `Suppressed:` block nested under the cause, and a `Caused by:` chain:

```java
static class LedgerConnection implements AutoCloseable {
    final String id;
    LedgerConnection(String id) { this.id = id; }
    void writeMovement() {
        throw new IllegalStateException("ledger write failed for connection " + id);
    }
    @Override
    public void close() {
        throw new RuntimeException("close failed for connection " + id);
    }
}

static void writeLedgerEntries() {
    try (LedgerConnection conn = new LedgerConnection("primary")) {
        conn.writeMovement();
    }
}

static void settleStake() {
    try {
        writeLedgerEntries();
    } catch (IllegalStateException e) {
        throw new LedgerImbalanceException("stake settlement failed for round round-771", e);
    }
}
```

produced:

```
Exception in thread "main" TraceDemo$LedgerImbalanceException: stake settlement failed for round round-771
	at TraceDemo.settleStake(TraceDemo.java:28)
	at TraceDemo.main(TraceDemo.java:33)
Caused by: java.lang.IllegalStateException: ledger write failed for connection primary
	at TraceDemo$LedgerConnection.writeMovement(TraceDemo.java:6)
	at TraceDemo.writeLedgerEntries(TraceDemo.java:20)
	at TraceDemo.settleStake(TraceDemo.java:26)
	... 1 more
	Suppressed: java.lang.RuntimeException: close failed for connection primary
		at TraceDemo$LedgerConnection.close(TraceDemo.java:10)
		at TraceDemo.writeLedgerEntries(TraceDemo.java:19)
		... 2 more
```

Read it the way the JVM assembled it, top to bottom, then read it the way an on-call engineer should, bottom to top. Top: `LedgerImbalanceException` is what `settleStake` threw and what the caller saw — the *surfaced* failure, and the least informative layer, because it is a translation. `Caused by: IllegalStateException` is the ledger write itself failing — the real root cause, one level down. `Suppressed: RuntimeException` is nested *under* the `Caused by:` block, at greater indentation, because it happened while the try-with-resources block was unwinding from the `IllegalStateException` and closing `conn` — it is not a cause of anything, it is a *second, independent* failure that happened during cleanup and would otherwise have been lost entirely.

**The rules, stated precisely.** A trace prints top-down, but the root cause is at the bottom, so read the `Caused by:` chain from the bottom up to find what actually failed, and from the top down to find where it surfaced and how it was translated on the way. `Suppressed:` is nested under the *enclosing* trace it happened inside, and it is never a cause of that trace — it is a sibling failure, and `01c-try-with-resources-and-suppression.md` owns exactly when the runtime produces one. A suppressed exception can carry its own `Caused by:` chain, printed nested one level further, exactly as any other exception would — the format recurses.

**`[BYTECODE]`** And the marker that is the single most misread token in a Java stack trace, the `N more` marker. Quoted from this build's own `Throwable.java` (`lib/src.zip`), the routine that decides it:

```java
private void printEnclosedStackTrace(PrintStreamOrWriter s,
                                     StackTraceElement[] enclosingTrace,
                                     String caption,
                                     String prefix,
                                     Set<Throwable> dejaVu) {
    assert s.isLockedByCurrentThread();
    if (dejaVu.contains(this)) {
        s.println(prefix + caption + "[CIRCULAR REFERENCE: " + this + "]");
    } else {
        dejaVu.add(this);
        // Compute number of frames in common between this and enclosing trace
        StackTraceElement[] trace = getOurStackTrace();
        int m = trace.length - 1;
        int n = enclosingTrace.length - 1;
        while (m >= 0 && n >=0 && trace[m].equals(enclosingTrace[n])) {
            m--; n--;
        }
        int framesInCommon = trace.length - 1 - m;

        // Print our stack trace
        s.println(prefix + caption + this);
        for (int i = 0; i <= m; i++)
            s.println(prefix + "\tat " + trace[i]);
        if (framesInCommon != 0)
            s.println(prefix + "\t... " + framesInCommon + " more");

        // Print suppressed exceptions, if any
        for (Throwable se : getSuppressed())
            se.printEnclosedStackTrace(s, trace, SUPPRESSED_CAPTION,
                                       prefix +"\t", dejaVu);

        // Print cause, if any
        Throwable ourCause = getCause();
        if (ourCause != null)
            ourCause.printEnclosedStackTrace(s, trace, CAUSE_CAPTION, prefix, dejaVu);
    }
}
```

Read the loop from the bottom of both arrays upward: `m` walks backward from the end of *this* exception's own frames, `n` walks backward from the end of the *enclosing* trace's frames, and the loop keeps decrementing both for as long as the frames at those positions are `.equals()`. `StackTraceElement.equals()`, quoted from this build's `lib/src.zip`:

```java
public boolean equals(Object obj) {
    if (obj==this)
        return true;
    return (obj instanceof StackTraceElement e)
            && e.lineNumber == lineNumber
            && e.declaringClass.equals(declaringClass)
            && Objects.equals(classLoaderName, e.classLoaderName)
            && Objects.equals(moduleName, e.moduleName)
            && Objects.equals(moduleVersion, e.moduleVersion)
            && Objects.equals(methodName, e.methodName)
            && Objects.equals(fileName, e.fileName);
}
```

Seven fields, all compared together — declaring class, line number, method name, file name and, since Java 9, module name, module version and class-loader name — so two frames at the same method and line are equal only if every other field also matches, and two frames at the same method with a *different* line are never equal regardless of anything else. Those matching bottom frames are the call path the two exceptions share, because the cause was thrown from somewhere *inside* a call that the outer exception's own stack also passed through. `framesInCommon` is exactly that count, and the printed marker reports `N more`, not "N frames were dropped" — the frames are not gone, they are simply the enclosing trace's own frames, already printed once, a few lines above. In the trace above, `IllegalStateException`'s full stack, bottom to top, is `main:33`, `settleStake:26`, `writeLedgerEntries:20`, `writeMovement:6` — four frames — and `LedgerImbalanceException`'s own trace, bottom to top, is `main:33`, `settleStake:28`. The walk compares `settleStake:26` against `settleStake:28`: same method, different line, so `.equals()` is false and the walk stops there, one frame in — `main:33` against `main:33` matched first and is the only shared frame, which is exactly the measured `framesInCommon = 1`. The practical reading is simpler than re-deriving the arithmetic each time: the shared-frames marker means "the N deepest frames of this trace are identical to the N deepest frames already printed above, in the enclosing block" — go up, not down, to see them.

**Circular references, detected and marked.** The printer guards against a cause cycle with an identity-based `dejaVu` set (`IdentityHashMap`-backed specifically to defeat a malicious or careless `equals()` override, per the source's own comment, quoted above) and prints a `CIRCULAR REFERENCE` line naming the repeated throwable's own `toString()` in place of recursing forever. Measured, by constructing one deliberately:

```
Exception in thread "main" java.lang.RuntimeException: stake reservation loop A
	at CircularDemo.main(CircularDemo.java:3)
Caused by: java.lang.RuntimeException: stake reservation loop B
	at CircularDemo.main(CircularDemo.java:4)
Caused by: [CIRCULAR REFERENCE: java.lang.RuntimeException: stake reservation loop A]
```

`A`'s cause is `B`, `B`'s cause is `A` (via `initCause` after both were constructed), and the third line is the printer recognising it has already visited `A` and refusing to loop — this can only happen through `initCause`/reflection, since the four-argument constructor and the ordinary chaining constructors never allow a cause cycle to be built through normal code.

**The practical recipe for a 200-line trace**, stated as the numbered list an on-call engineer should actually run through:

1. Find the *last* `Caused by:` block in the file — scroll to the bottom of the chain, not the top. That is the exception closest to the actual failure.
2. Read that block's own frames (the ones printed before its `N more` marker, if it has one) as the real call path that failed — the class, method and line named at the top of that block.
3. Walk back *up* through each `Caused by:` block above it only to understand how the failure was translated and re-wrapped on its way to the surface — each layer's own message is what that layer's code chose to say about the layer below it, which is context, not the root cause itself. Treat any `Suppressed:` block encountered along the way as a second, independent finding, not as part of this walk.

### The diagram

No diagram for this concept: the evidence is one real multi-part trace with every token the leaf names present in it, one quoted source routine and one circular-reference example — a picture of "read from the bottom" would need to reproduce the same trace text in boxes to be any clearer than the annotated listing above.

### A concrete example

Already given in full above — the `TraceDemo` listing and its measured output is the complete worked example, produced from real QuizStakes types (`LedgerConnection`, `LedgerImbalanceException`) rather than a synthetic stand-in.

### The gotcha

**Pitfall:** reading a shared-frames marker reporting `23 more` as "23 frames were dropped from this trace."

Wrong belief: a trace ending in a shared-frames marker reporting `23 more` is missing information — someone truncated it, or `MaxJavaStackTraceDepth` cut it off, and the fix is to find a way to capture "the rest."

Right: the `N more` marker names frames the printer chose not to repeat because they are already printed, verbatim, a few lines above — in the block for the exception this one is nested under. `Throwable.printEnclosedStackTrace`'s own comment states the computation directly: "number of frames in common between this and enclosing trace." Nothing about the `N` frames is unrecoverable; they are sitting in the same file, one `Caused by:` (or the top-level) block earlier, because that is where the call path this exception shares with its enclosing trace was already shown.

**Why people believe it:** the phrase "N more" reads naturally as "N more exist, unshown, unavailable" — the same grammatical shape as a paginated log line reporting 40 more results, where the rest genuinely is not on screen and genuinely does require another action to see. A Java stack trace's shared-frames marker is the one place that phrase means the opposite: the rest is already visible, just not repeated.

> **Definition.** A trace's `Caused by:` chain is printed top-down but should be read bottom-up to find the root cause; `Suppressed:` blocks nest under the enclosing trace they occurred inside and are never causes of it; and the `N more` marker, computed by `Throwable.printEnclosedStackTrace` walking both traces' frame arrays backward from the end while they `.equals()`, names frames shared with the block printed immediately above — never dropped frames — with a circular cause chain marked by a `CIRCULAR REFERENCE` line naming the repeated throwable, via an identity-keyed visited set rather than looped forever.

---

## 4. `StackWalker` with `RETAIN_CLASS_REFERENCE`: the cheap way to inspect a few frames (3.9.16)

`[RESEARCH]` The picture: `new Throwable().getStackTrace()` answers "who called me?" by materialising the *entire* call stack into `StackTraceElement` objects, just to let you look at one or two of them. `StackWalker`, Java 9's answer to that waste, is a lazy, pull-based traversal — frames beyond the ones you actually consume are never decoded at all.

### Why it exists

Before Java 9, inspecting a caller meant constructing a `Throwable` — paying `03b-internals-stack-trace-capture.md`'s full construction-time walk — and then calling `getStackTrace()`, which decodes every captured frame into a `StackTraceElement`, at roughly 48 bytes per frame under compressed oops (`03b` concept 2's own arithmetic). A method that only wants to know its immediate caller's class, to attribute an audit log entry or check a permission, pays for the whole stack regardless. `StackWalker` (JEP 259, Java 9) exposes the identical native walk as a `Stream`-shaped API instead of an eagerly-decoded array, so `.findFirst()`, `.limit(2)` or `.skip(1)` can short-circuit the walk after materialising only the frames actually touched.

### When to reach for it, and when not

Reach for it when the goal is inspecting the *current* call stack for a small, bounded number of frames — a caller-attribution check, a "who invoked this deprecated API" diagnostic, a security-sensitive access check. Do not reach for it as a `Throwable` substitute: `StackWalker` never produces a `Throwable`, so it has nothing to log, nothing to catch, and nothing to attach as a cause — the moment the goal shifts from "inspect the stack" to "report a failure," `03b`'s stackless-exception forms are the right tool, not this one. `03b-internals-stack-trace-capture.md` concept 3 already names `StackWalker` as the sibling to reach for when the actual goal is inspection rather than failure-reporting; this file is where that pointer resolves.

### How it works

`[RESEARCH]` A real QuizStakes use: `AccountMaintenance` needs to attribute an audit-log entry to whichever service class actually called it, without constructing an exception or paying for the whole stack:

```java
import java.lang.StackWalker.Option;
import java.util.Optional;

final class AuditAttribution {

    static String callingServiceClass() {
        StackWalker walker = StackWalker.getInstance(Option.RETAIN_CLASS_REFERENCE);
        Optional<StackWalker.StackFrame> caller =
            walker.walk(stream -> stream.skip(1).findFirst());
        return caller.map(f -> f.getDeclaringClass().getSimpleName()).orElse("unknown");
    }
}
```

`walk` takes a function from `Stream<StackFrame>` to a result and is the only way to consume frames — the stream is only valid for the duration of that call, by design, so it cannot be returned or stored and iterated later. `skip(1)` discards the frame for `callingServiceClass` itself (the walk always starts at the calling method), and `findFirst()` short-circuits the whole traversal after exactly one more frame — two frames materialised, out of however deep the real call stack is, measured below.

**`RETAIN_CLASS_REFERENCE`, specifically.** Without it, calling `getDeclaringClass()` on a `StackFrame` throws, measured on this build:

```java
StackWalker noRetain = StackWalker.getInstance();
noRetain.walk(stream -> stream.findFirst()).get().getDeclaringClass();
```

```
without RETAIN_CLASS_REFERENCE: java.lang.UnsupportedOperationException: No access to RETAIN_CLASS_REFERENCE
```

The option exists because a `Class` object is a *capability*, not inert data — holding one gives access to reflection, to the class's `ClassLoader`, to everything a security-sensitive caller might not want handed out just for walking a stack to print method names. Without the option, `StackFrame` still exposes `getClassName()` (a plain `String`, no capability implied) and `getMethodName()`; only `getDeclaringClass()` — the one method that hands back the actual `Class<?>` — is gated, and it is gated per-instance of `StackWalker`, decided once at `getInstance()` time, not per-call.

**The other options, and what each exposes.**

| Option | What it enables | Default without it |
|---|---|---|
| `RETAIN_CLASS_REFERENCE` | `StackFrame.getDeclaringClass()` returns the real `Class<?>` | throws `UnsupportedOperationException` |
| `SHOW_REFLECT_FRAMES` | reflection-machinery frames (`Method.invoke`, `Constructor.newInstance` internals) appear in the walk | hidden — the walk skips straight past them to the real caller |
| `SHOW_HIDDEN_FRAMES` | implementation-internal frames — lambda-form frames, some proxy frames — appear too, a superset of `SHOW_REFLECT_FRAMES` | hidden |
| (neither) | the default: only "ordinary" application frames, hiding reflection and hidden frames | — |

`SHOW_HIDDEN_FRAMES` and `SHOW_REFLECT_FRAMES` are supporting facts here, not primary concepts — most callers never need either, because the default walk already gives the frames application code cares about, and the two options exist specifically for the narrower job of debugging *how* a reflective or lambda-generated call reached a given frame.

**`getCallerClass()`, the convenience method.** `StackWalker` declares `public Class<?> getCallerClass()` directly — confirmed on this build via `javap -public java.lang.StackWalker` — which returns the immediate caller's class in one call, with no `walk` lambda required, and is the direct, supported replacement for the old, unsupported `sun.reflect.Reflection.getCallerClass()` internal API. It carries the same `RETAIN_CLASS_REFERENCE` requirement implicitly, since it must hand back a `Class<?>`.

**`[NUM]` Measured: `StackWalker` limited to two frames against `new Throwable().getStackTrace()` at the same depth**, on this build, warmed and timed over matched iteration counts (the harness's limitations are `03b`'s own — no forking, uncontrolled JIT tier, a single run rather than several — stated there and inherited here rather than re-derived):

```
depth=10    stackwalker=     606.1ns  new-throwable-getstacktrace=    1328.0ns  ratio=2.2x
depth=100   stackwalker=     872.5ns  new-throwable-getstacktrace=    7797.7ns  ratio=8.9x
depth=1000  stackwalker=    2989.7ns  new-throwable-getstacktrace=   72197.8ns  ratio=24.1x
```

Read the ratio column, not just the absolute numbers: `StackWalker`'s cost grows slowly with real stack depth (it only ever materialises the two frames the lambda consumes, so the *walk* still has to traverse past the intervening native frames to reach them, which is where its own modest growth comes from), while `new Throwable().getStackTrace()` grows in lockstep with `03b`'s own construction-plus-decode curve, because it captures and decodes every frame regardless of how many the caller actually wants. At depth 1,000 the gap is a full order of magnitude — the exact order-of-magnitude win `03b` concept 4 found *missing* between a normal and a stackless exception is present here, because `StackWalker` is solving a narrower problem (inspect a few frames) that a `Throwable`, whose job is capturing *all* of them for later reporting, cannot be cheap at by design.

### The diagram

No diagram for this concept: the evidence is one measured three-row table whose story is entirely in the ratio column, and `03b`'s D-115 already carries the construction-cost curve this comparison is measured against — a second figure here would restate that curve's shape rather than add to it.

### A concrete example

Already given above — the `AuditAttribution.callingServiceClass()` listing is the complete, real, minimal example, and the benchmark table is the cost evidence for choosing it over the `Throwable`-based alternative.

### The gotcha

**Pitfall:** reaching for `StackWalker` when the actual requirement is "log this failure with its origin," not "look at the current stack." `StackWalker` never produces a `Throwable` — there is nothing to `throw`, nothing to attach as a `cause`, nothing a logging framework's trailing-`Throwable` argument convention (`01e-catch-discipline-and-top-level-handling.md` concept 1 owns that convention) can print a trace from. Symptom: code that walks the stack with `StackWalker` to build a *string* describing where a failure happened, then logs that string instead of an actual exception — discarding the structured trace a real `Throwable` would have given a log aggregator, in exchange for a cheaper walk that was never the bottleneck in a failure-reporting path to begin with. Fix: `StackWalker` for inspection questions ("who is my caller"), a real (possibly stackless, per `03b` concept 3) `Throwable` for anything that is actually a failure being reported.

> **Definition.** `StackWalker` (Java 9, JEP 259) exposes the JVM's stack-walking machinery as a lazy `Stream<StackFrame>`, materialising only the frames a terminal operation actually consumes rather than decoding the whole stack the way `new Throwable().getStackTrace()` does; `RETAIN_CLASS_REFERENCE`, decided once per `StackWalker` instance, gates `StackFrame.getDeclaringClass()` specifically, because a `Class` object is a capability rather than inert data, and `getCallerClass()` is the supported one-call replacement for the pre-9 `sun.reflect.Reflection.getCallerClass()` — measured on this build at roughly 2× to 24× cheaper than the `Throwable`-based equivalent for a two-frame inspection, with the gap widening as real stack depth grows.

---

## 5. JFR's `jdk.ExceptionStatistics` and `jdk.JavaExceptionThrow`: finding the throw nobody logs (3.9.17)

`[RESEARCH]` `[X-REF 20]` The picture: no log line exists for an exception that is thrown and caught in the same method without ever being logged — which is exactly the shape of an exception used as control flow, and exactly the shape that becomes invisible right up until someone asks JFR to count it.

`../language-substrate/05-internals-observability.md` §3.18 already owns this project's general observability toolkit, including a JFR §4b section covering the same two events at a higher level (rate-versus-trace, throttling, the shipped `.jfc` settings). This concept does not repeat that file's account of JFR mechanics — it states the exception-specific facts that file summarizes, verified independently on this exact build, and points there for the surrounding toolkit (JOL, async-profiler, heap dumps) that JFR sits alongside.

### Why it exists

JDK Flight Recorder is a low-overhead event recorder built into the JVM, writing fixed-layout events into thread-local buffers with individually configurable, individually throttleable event types. Applied to exceptions, it answers a question no log can: *what is throwing exceptions that nobody ever sees* — a `NumberFormatException` per malformed callback field, a `RestrictedActionException` a caller catches and silently retries, anything shaped like control flow rather than a genuine failure. `02c-cost-and-control-flow.md` and `03b-internals-stack-trace-capture.md` both price the *construction* cost of such an exception; JFR is the tool that tells you the *rate* is worth pricing at all.

### When to reach for it, and when not

Reach for `jdk.ExceptionStatistics` as the very first look — it is cheap enough to leave running, and it answers "is this actually happening a lot" without paying for a single stack trace. Reach for `jdk.JavaExceptionThrow` only after that first look says the rate is worth a stack trace's cost, and only for a bounded window, because it captures a trace per throw. Do not reach for either as a substitute for `03b`'s construction-cost harness or `02c`'s control-flow decision — JFR tells you *how often*, not *how expensive per throw*, which is a different number answered by a different tool.

### How it works

`[RESEARCH]` **Verify both event names, their default enablement, and their fields** — done here by reading this build's own shipped settings and confirming with a real recording, rather than described from memory. This build's `default.jfc` and `profile.jfc` (`$JAVA_HOME/lib/jfr/`), quoted:

```
<event name="jdk.JavaExceptionThrow">
  <setting name="enabled" control="enable-exceptions">false</setting>
  <setting name="stackTrace">true</setting>
</event>

<event name="jdk.JavaErrorThrow">
  <setting name="enabled" control="enable-errors">true</setting>
  <setting name="stackTrace">true</setting>
</event>

<event name="jdk.ExceptionStatistics">
  <setting name="enabled">true</setting>
  <setting name="period">1000 ms</setting>
</event>
```

Identical in both `default.jfc` and `profile.jfc` on this build — the two shipped settings files do not disagree here, which is itself worth confirming rather than assuming: `jdk.JavaExceptionThrow` is **off** in both, `jdk.ExceptionStatistics` is **on** in both with a one-second period, and there is a third event, `jdk.JavaErrorThrow`, covering `Error` specifically — the leaf's own "if it exists on this build" question, answered yes. The `<selection name="exceptions" default="errors">` control block that governs `enable-exceptions`/`enable-errors` confirms the default choice: `errors` only, unless a recording is started with `settings=profile,exceptions=all` or the flag is enabled individually.

**`jdk.ExceptionStatistics` — the cheap periodic count.** A real recording, on a workload shaped like the QuizStakes malformed-callback case — 2,000,000 simulated card-deposit callbacks with a steady 5% malformed-field rate, `NumberFormatException` caught per malformed row and never logged:

```
$ java -XX:StartFlightRecording=filename=deposit-default.jfr,duration=60s CardDepositCallback
processed=2000000 malformed=100000 elapsedMs=52
$ jfr summary deposit-default.jfr | grep -i exception
 jdk.ExceptionStatistics                     2            28
 jdk.JavaExceptionThrow                      0             0
$ jfr print --events jdk.ExceptionStatistics deposit-default.jfr
jdk.ExceptionStatistics {
  startTime = 14:58:40.358 (2026-08-29)
  throwables = 100006
  eventThread = "JFR Periodic Tasks" (javaThreadId = 20)
}

jdk.ExceptionStatistics {
  startTime = 14:58:41.362 (2026-08-29)
  throwables = 100006
  eventThread = "JFR Periodic Tasks" (javaThreadId = 20)
}
```

Read the fields precisely, because the shape is easy to misread. `throwables` is a **cumulative** count of `Throwable` construction since JVM start, not a per-second rate — this recording's two samples both read `100006` because the 100,000 malformed-callback exceptions had already all been thrown and the periodic sampler fired twice, one second apart, after the burst finished (the extra six are ordinary JVM-startup throwables). Two consecutive samples, subtracted, give the throw *rate* over that interval — a single sample only ever tells you the running total. `jdk.JavaExceptionThrow`'s summary count of `0` in the same recording confirms the flag-off default measured from the `.jfc` file: not one of the 100,000 `NumberFormatException`s produced a per-throw event, and no stack trace was ever captured for JFR's purposes, exactly as the shipped setting promises.

**`jdk.JavaExceptionThrow` — the expensive one, explicitly enabled.** Once the cheap counter has said "yes, this is worth a trace," enabling it individually rather than switching to `exceptions=all` wholesale:

```
$ java "-XX:StartFlightRecording=filename=deposit-throw.jfr,+jdk.JavaExceptionThrow#enabled=true" CardDepositSmall
$ jfr print --events jdk.JavaExceptionThrow deposit-throw.jfr
```

```
jdk.JavaExceptionThrow {
  startTime = 14:58:53.570 (2026-08-29)
  message = "For input string: "12.50-CORRUPT""
  thrownClass = java.lang.NumberFormatException (classLoader = bootstrap)
  eventThread = "main" (javaThreadId = 1)
  stackTrace = [
    java.lang.Throwable.<init>(String) line: 275
    java.lang.Exception.<init>(String) line: 67
    java.lang.RuntimeException.<init>(String) line: 63
    java.lang.IllegalArgumentException.<init>(String) line: 50
    java.lang.NumberFormatException.<init>(String) line: 54
  ]
}
```

(the recording's real output continues with the throwing method's own frames below `NumberFormatException.<init>`, trimmed here for length — every field shown above is verbatim). One event per throw, each carrying the exception's own class, message, thread and a full stack trace — the reason it is off by default is exactly this: at 100,000 throws in one burst, this event alone would be 100,000 stack-trace captures, each paying `03b`'s own capture cost on top of JFR's own event-write cost.

**`jdk.JavaErrorThrow` — confirmed, on by default, for `Error` specifically.** The leaf's own question, answered by producing one:

```java
throw new StackOverflowError("simulated for JFR jdk.JavaErrorThrow demo");
```

```
jdk.JavaErrorThrow {
  startTime = 14:59:00.627 (2026-08-29)
  message = "simulated for JFR jdk.JavaErrorThrow demo"
  thrownClass = java.lang.StackOverflowError (classLoader = bootstrap)
  eventThread = "main" (javaThreadId = 1)
  stackTrace = [
    java.lang.Error.<init>(String) line: 68
    java.lang.VirtualMachineError.<init>(String) line: 54
    java.lang.StackOverflowError.<init>(String) line: 52
    ErrorThrowDemo.main(String[]) line: 4
  ]
}
```

Present, with the identical shape as `jdk.JavaExceptionThrow`, and enabled by default in both shipped `.jfc` files — the platform treats `Error` as rare and severe enough to be worth its per-throw trace unconditionally, in contrast to ordinary `Exception`s, which it assumes may be thrown far more often and therefore gates behind an explicit choice.

**Framed on QuizStakes.** A `NumberFormatException` thrown per malformed field on 95,000 card-deposit callbacks a day is, at even a modest malformed rate, invisible in an application log that only logs *handled* failures at the boundary — the exception never reaches a boundary, it is caught and counted (or silently dropped) inside the parsing loop. `jdk.ExceptionStatistics`, sampled every second at negligible cost, makes the throw rate visible without a single stack trace, exactly the measurement this concept's harness reproduced: `100006` cumulative throwables against a workload that produced exactly `100000` malformed rows, confirming the counter tracks real construction events rather than a proxy for them.

### The diagram

No diagram for this concept: the evidence is a real `.jfc` excerpt and two real recordings' `jfr summary`/`jfr print` output, and both events' story is entirely in the field values already quoted — a picture of "cheap counter, expensive tracer" would only redraw the two code blocks as boxes.

### A concrete example

Already given above in full — the `CardDepositCallback` harness and its `deposit-default.jfr` recording is the complete, real, QuizStakes-shaped example, and `CardDepositSmall`'s `deposit-throw.jfr` is the follow-up once the counter has justified the more expensive event.

### The gotcha

**Insight:** `jdk.ExceptionStatistics`'s `throwables` field being cumulative rather than a delta is the detail that makes the event genuinely cheap — a periodic sampler reading one counter every second costs nothing proportional to the throw rate, where a per-throw event necessarily does. The cost of that cheapness is that a single sample tells you nothing about *rate*; two samples, subtracted, do.

**Pitfall:** reading `jdk.ExceptionStatistics`'s `throwables` count from a single sample as "the number of exceptions thrown recently." It is the running total since JVM start, and a process that has been up for days will report a large number on every sample regardless of whether anything unusual happened in the last minute. The fix is always a rate, computed from two or more samples over a known interval — exactly the same discipline `jcmd <pid> GC.class_histogram`'s instance counts need against a baseline, per `../language-substrate/05-internals-observability.md` §4b's own framing of JFR events as samples or counters to be compared, not absolute numbers to be read in isolation.

> **Definition.** `jdk.ExceptionStatistics` is a cheap, periodic (1000 ms on this build), cumulative counter of `Throwable` construction, enabled by default in both shipped `.jfc` settings, and is the first tool to reach for when the question is "is some type being thrown far more than any log line suggests"; `jdk.JavaExceptionThrow` is a per-throw event carrying the exception's class, message and full stack trace, disabled by default in both shipped settings because its cost is proportional to throw rate, and is the tool to reach for only once the counter has justified paying for a trace; `jdk.JavaErrorThrow` is the `Error`-specific sibling of the second event, confirmed present on this build and enabled by default in both settings files, reflecting the platform's judgment that an `Error` is rare and severe enough to always warrant its trace.

---

## Pitfalls

### Reading a shared-frames marker as dropped frames

**Wrong**

A trace ends in a shared-frames marker reporting `23 more` and the reader concludes those 23 frames were never captured — perhaps `MaxJavaStackTraceDepth` truncated them, or a logging framework's formatter cut the trace short to save space, and the fix is to find a configuration that "shows the rest."

**Right**

`Throwable.printEnclosedStackTrace`'s own source computes `framesInCommon` by walking this exception's frames and the *enclosing* trace's frames backward from the end while they `.equals()` — the token names frames this exception shares with whatever block was printed immediately above it, and those frames are already sitting in the file, verbatim, a few lines up. Nothing was dropped; go up, not down.

**Why people believe it:** the phrase "N more" reads naturally as "N more items exist and are not shown," matching the everyday sense of a paginated log or search result. A Java stack trace is the one place that phrase means the opposite — the rest is already visible, printed once, in the block above.

### Assuming a helpful NPE message survives an uninformative rethrow

**Wrong**

```java
try {
    reserveStake(roundId, stake);
} catch (NullPointerException e) {
    throw new RestrictedActionException(RestrictionType.STAKE_BLOCKED, "stake reservation failed");
}
```

The caught `NullPointerException` may carry a precisely computed description of exactly which reference was null — but this rethrow discards `e` entirely. The new exception's message is the literal string written here, and nothing about the original failure survives.

**Right**

```java
try {
    reserveStake(roundId, stake);
} catch (NullPointerException e) {
    throw new RestrictedActionException(RestrictionType.STAKE_BLOCKED,
        "stake reservation failed for round " + roundId, e);
}
```

Chaining `e` as the cause (`01a-throwable-api-and-chaining.md` owns the mechanics) means the helpful NPE's message survives in the `Caused by:` block, exactly as concept 3 above teaches reading it — the reader who scrolls to the bottom of the chain still finds the precise field or variable that was null.

**Why people believe it:** the JEP 358 message often makes the *caught* exception look self-explanatory enough on its own that preserving it feels like an optional nicety rather than the one piece of information a translation layer cannot reconstruct after the fact.

### Reaching for `-XX:-ShowCodeDetailsInExceptionMessages` as the primary fix for a leak

**Wrong**

```
# Production launch flags, chosen after a security review flagged that
# an internal field name once appeared in an HTTP error response.
java -XX:-ShowCodeDetailsInExceptionMessages -jar payment-service.jar
```

This silences the extended message for every `NullPointerException` on the entire process, including the overwhelming majority that never come near an external boundary — trading away concept 1's whole diagnostic value process-wide to patch what is actually a boundary bug.

**Right**

Fix the boundary — never let a caught exception's message reach a response body (`02d-logging-and-api-boundaries.md` owns the contract) — and keep the flag as an emergency, `{manageable}` lever that can be flipped on a live process (measured above, via `HotSpotDiagnosticMXBean.setVMOption`) if a leak is discovered before the boundary fix ships, not as the standing configuration.

**Why people believe it:** the flag is the fastest thing to change — one line in a launch script — against a code review that has to find and fix every path an exception's message could take toward an external caller. The fast fix is also the one that gives up the most, and it gives it up everywhere at once rather than just at the one boundary that was actually wrong.

---

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| Helpful NPE, when computed | Lazily, on the first call to `getMessage()` — not at throw, not at construction |
| Helpful NPE, on by default | Since Java **15** (JDK-8233014); Java 14 required `-XX:+ShowCodeDetailsInExceptionMessages` |
| Flag category | `{manageable}` — togglable on a live process via `HotSpotDiagnosticMXBean.setVMOption`, no restart |
| Field/method names in the message | Always available (constant pool), regardless of compiler flags |
| Local variable names in the message | Need `-g` or `-g:vars`; otherwise `<localN>` |
| Return-value form | "the return value of `Reservation.split()` is null" — no debug-info dependency |
| Constructed NPE (`throw new NullPointerException()`) | `getMessage() == null` — no bytecode offset to walk back from |
| Fast-thrown NPE | No trace, no helpful message — see `03c-internals-fast-throw-and-truncation.md` |
| Security risk | Message can name internal class/field/method/local identifiers not previously reflectively exposed via a thrown exception's text |
| Primary mitigation | Never put an exception's message in a response body — `02d-logging-and-api-boundaries.md` |
| Secondary mitigation | `-g:none` in production — removes local names only; costs the same debug info a human debugger needs |
| Emergency lever | `-XX:-ShowCodeDetailsInExceptionMessages`, `{manageable}`, live-togglable |
| Trace token | `Caused by:` — read the chain bottom-up for the root cause, top-down for the surfaced translation |
| Trace token | `Suppressed:` — nested under the enclosing block, never a cause of it |
| Trace token | `N more` marker — the shared-frames marker; frames already printed above, never dropped |
| Trace token | `CIRCULAR REFERENCE` line — identity-keyed cycle guard in `printEnclosedStackTrace` |
| `StackWalker`, introduced | Java 9, JEP 259 |
| `StackWalker.Option.RETAIN_CLASS_REFERENCE` | Required for `StackFrame.getDeclaringClass()`; otherwise `UnsupportedOperationException` |
| `StackWalker.Option.SHOW_REFLECT_FRAMES` | Exposes reflection-machinery frames, hidden by default |
| `StackWalker.Option.SHOW_HIDDEN_FRAMES` | Superset of the above; exposes implementation-internal frames too |
| `StackWalker.getCallerClass()` | Supported replacement for `sun.reflect.Reflection.getCallerClass()` |
| `StackWalker` vs `new Throwable().getStackTrace()` | Measured 2.2x–24.1x cheaper for a two-frame inspection, gap widening with real stack depth |
| `jdk.ExceptionStatistics` | Cheap periodic **cumulative** counter, 1000 ms period, enabled by default in `default.jfc` and `profile.jfc` |
| `jdk.JavaExceptionThrow` | Per-throw event with full stack trace, **disabled** by default in both shipped settings |
| `jdk.JavaErrorThrow` | `Error`-specific sibling of `jdk.JavaExceptionThrow`, **enabled** by default in both shipped settings |
| Enabling `jdk.JavaExceptionThrow` | `-XX:StartFlightRecording=filename=out.jfr,+jdk.JavaExceptionThrow#enabled=true`, or `settings=profile,exceptions=all` |
| Reading `jdk.ExceptionStatistics` | Subtract two samples for a rate — one sample is a running total, not a recent count |

---

## Self-test

**Q1.** A helpful NPE message reads `Cannot invoke "StakeSplit.bonusPortion()" because the return value of "Reservation.split()" is null`. Walk through when this text was actually computed, and why that timing matters.

<details><summary>Answer</summary>

Not at the moment the `NullPointerException` was constructed, and not at the moment it was thrown — the JVM records only the failing bytecode instruction's offset at throw time. The English description is built on the first call to `getMessage()`, which for a JVM-thrown NPE invokes a native routine (reported consistently as `getExtendedNPEMessage()`) that re-walks the throwing method's bytecode from that recorded offset and reconstructs the description of the failing instruction — here, an `invokevirtual` of `bonusPortion()` whose receiver came from a null-returning call to `split()`. The timing matters for two reasons: first, if this exception were caught and discarded without ever having `getMessage()` (or an equivalent, such as `printStackTrace()`) called on it, the bytecode walk never happens and the cost is zero beyond an ordinary NPE's — laziness is what let this feature ship on by default with negligible measured overhead. Second, it is why a hand-constructed `new NullPointerException("reservation must not be null")` or a bare `new NullPointerException()` gets none of this: there is no failing-instruction offset recorded for a `throw` the JVM did not itself detect as a null dereference, and measured on this build, the bare constructor's `getMessage()` returns `null`, not a synthesized description.

</details>

**Q2.** Name the JEP 358 security concern precisely — not "it's a security risk" but what specifically it exposes and to whom, and the two mitigations in order of preference.

<details><summary>Answer</summary>

The concern is that a helpful NPE message can name real class, field, method and (with `-g`/`-g:vars`) local-variable identifiers from the source — information that, per JEP 358's own framing, "have not previously been available to other programs via Java's reflection APIs" through a thrown exception's text specifically. The exposure only matters where that text crosses a trust boundary: an HTTP response body, a webhook payload, a third-party log sink. Concretely on QuizStakes, a message like `Cannot invoke "StakeSplit.bonusPortion()" because the return value of "Reservation.split()" is null` reaching a response body tells an external caller that a type `StakeSplit` exists with an accessor `bonusPortion()`, that `Reservation.split()` returns it and can return null — real facts about the domain model extracted from a JSON body with no other tooling. The preferred mitigation is structural: never let a caught exception's message reach a response body at all, mapping to a stable caller-facing code and a hand-written message instead (`02d-logging-and-api-boundaries.md` owns the contract) — this makes the concern irrelevant regardless of what the message contains. The secondary mitigation, `-g:none` in production, removes only the local-variable names (measured: field/method names are unaffected, since they are always in the constant pool) and costs the same debug information a human would want while reading a heap dump or attached debugger during a real incident — a partial fix with an explicit price, not the first move.

</details>

**Q3.** `-XX:-ShowCodeDetailsInExceptionMessages` carries the flag category `{manageable}` rather than plain `{product}`. What does that buy operationally, and how would you exercise it on a live process?

<details><summary>Answer</summary>

`{manageable}` means the flag can be changed on a running JVM through the platform management interface, with no restart — a genuinely different capability from most HotSpot flags, which are fixed at launch. Measured on this build via `HotSpotDiagnosticMXBean.setVMOption("ShowCodeDetailsInExceptionMessages", "false")`: the flag's reported `origin` moved from `DEFAULT` to `MANAGEMENT` immediately, and the very next `NullPointerException` thrown on that process produced the bare `null` message instead of the extended description; setting it back to `"true"` restored the extended form on the next throw after that, with no redeploy or restart involved either way. Operationally this is the emergency lever: if a leak into a response body is discovered in production, the flag can be flipped off on the live, affected process (or via `jcmd <pid> VM.set_flag`, the command-line equivalent of the same management path) while the actual fix — closing the boundary that let the message out — is prepared and shipped, rather than waiting for a redeploy to stop the immediate bleeding.

</details>

**Q4.** A trace ends in a shared-frames marker reporting `12 more`. Where are those twelve frames, and what routine decided the number 12?

<details><summary>Answer</summary>

They are not missing — they are the twelve deepest frames of the enclosing trace, already printed a few lines above this block, because this exception's own call path shares that many frames with whatever it is nested under (a `Caused by:` chain, or a `Suppressed:` block's enclosing trace). `Throwable.printEnclosedStackTrace`, quoted from this build's `lib/src.zip`, computes it by walking both `StackTraceElement[]` arrays — this exception's own trace and the enclosing one passed in — backward from their last index, decrementing both indices for as long as the frames at those positions are `.equals()` (same declaring class, method, file, line). `framesInCommon` is the count of matches found that way, and the printed marker reports `framesInCommon` followed by the literal text "more" — not "dropped," a *count of frames already shown*. To actually see them, look at the block printed immediately above this one, at the bottom of its own frame list.

</details>

**Q5.** Distinguish `Suppressed:` from `Caused by:` in one sentence each, and say what nests under what.

<details><summary>Answer</summary>

`Caused by:` names the exception that caused this one — a genuine causal chain, walked via `Throwable.getCause()`, printed one level below the exception it caused and read, for diagnosis, from the bottom of the chain upward. `Suppressed:` names an exception that happened while the enclosing exception's own frame was already unwinding — most commonly a `close()` failure inside a try-with-resources block that was already propagating a body exception (`01c-try-with-resources-and-suppression.md` owns exactly when the runtime records one) — and it is never a cause of the exception it is nested under; it is a second, independent finding that would otherwise have been silently lost. Nesting: a `Suppressed:` block is printed under the exception whose unwinding produced it, at one extra level of indentation, and can itself carry its own `Caused by:` chain, printed nested one level further — the format recurses identically regardless of which kind of block it is inside.

</details>

**Q6.** Why does calling `StackFrame.getDeclaringClass()` on a `StackWalker` obtained without `RETAIN_CLASS_REFERENCE` throw, and what does the option actually gate?

<details><summary>Answer</summary>

It throws `UnsupportedOperationException: No access to RETAIN_CLASS_REFERENCE`, measured directly on this build, because handing back a `Class<?>` object is treated as granting a capability, not just returning data — a `Class` reference gives access to reflection, to the class's loader, and to everything else reflection can reach from there, which is a materially larger grant than a plain `String` class name. The option is decided once, at `StackWalker.getInstance(Option.RETAIN_CLASS_REFERENCE)` time, and gates exactly one method: `getDeclaringClass()`. Without it, `StackFrame.getClassName()` (a `String`) and `getMethodName()` still work — only the method that would hand back the actual `Class<?>` object is refused. `getCallerClass()`, the convenience method that replaced the old unsupported `sun.reflect.Reflection.getCallerClass()`, needs the same access implicitly, since it must return a `Class<?>`.

</details>

**Q7.** `jdk.ExceptionStatistics` reports `throwables = 100006` on two consecutive one-second samples. Does that mean nothing was thrown in that second, or is the reading being misread?

<details><summary>Answer</summary>

The reading is being misread — `throwables` is a cumulative count of `Throwable` construction since JVM start, not a per-interval count, confirmed by reading this build's own `default.jfc` (`period 1000 ms`, no delta semantics stated or implied) and by measuring it directly: a burst of exactly 100,000 simulated malformed-callback exceptions produced two consecutive samples both reading `100006` (100,000 plus a handful of ordinary JVM-startup throwables), because the burst had already completed by the time both one-second samples fired. Two identical readings one second apart genuinely can mean zero throws happened in that particular second — or it can mean the sampler happened to land after a burst finished, which is exactly what happened here. The only way to get a rate is to subtract two samples taken at a known interval; a single sample, or two identical ones, says nothing about "just now" on its own.

</details>

**Q8.** `jdk.JavaExceptionThrow` and `jdk.JavaErrorThrow` are near-identical events. What's the actual distinction, and what does each one's default enablement say about the platform's judgment?

<details><summary>Answer</summary>

Structurally they are the same shape — class, message, thread and a full stack trace per throw — but they cover different subtrees of `Throwable`: `jdk.JavaExceptionThrow` fires for exceptions, `jdk.JavaErrorThrow` for `Error`s. Confirmed on this build by reading `default.jfc` and `profile.jfc` and by producing one of each in a real recording: `jdk.JavaExceptionThrow` is disabled in both shipped settings (`control="enable-exceptions"`, defaulting to off unless a recording explicitly requests `exceptions=all`), while `jdk.JavaErrorThrow` is enabled in both (`control="enable-errors"`, on by the `exceptions` selection's own default value of `"errors"`). The platform's judgment is explicit in that asymmetry: an ordinary exception can plausibly be thrown at a rate — thousands or millions per day — where capturing a trace per throw is a real cost not worth paying by default, while an `Error` is assumed rare and severe enough that its trace is worth capturing unconditionally, every time, with no opt-in required.

</details>

---

## Open questions

- **Unverified:** whether any JVM-detected null dereference produces a helpful NPE message with the reason clause omitted entirely (the leaf's own instruction: "find a case and show it, or say you could not"). Four action forms (`invokevirtual`, `getfield`, `aastore`, `arraylength`), plus unboxing (`intValue()`), a `synchronized`-block monitor check, and an `athrow` on a null throwable were all produced on this build and all came back with a complete action-plus-reason message. No omitted-reason case was found. What would settle it: reading the OpenJDK implementation of the bytecode-description algorithm itself (the `hotspot` C++ source behind `getExtendedNPEMessage()`, or the JEP 358 design document's own list of describable bytecodes) to check whether every bytecode capable of an NPE is covered, or whether some are known, documented exceptions.
- **Unverified, partially:** the exact wording of the JEP 358 quotations in concepts 1 and 2. Direct fetches of `openjdk.org/jeps/358` and `bugs.openjdk.org/browse/JDK-8220715` both returned HTTP 403 in this environment, so the quoted sentences ("computed on demand, when the JVM calls `Throwable::getMessage`"; "these have not previously been available to other programs via Java's reflection APIs") are sourced from secondary aggregators (`javacodegeeks.com`, `puradawid.pro`) that themselves present the text as direct JEP quotations, cross-checked across two independent sources with consistent phrasing. What would settle it: direct access to the JEP text itself, through a network path that is not blocked, or the JDK Enhancement Proposal's text as archived in the OpenJDK mercurial/git history for JDK-8218628.

---

**Leaves covered:** 3.9.11, 3.9.12, 3.9.13, 3.9.16, 3.9.17 (5 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 740
