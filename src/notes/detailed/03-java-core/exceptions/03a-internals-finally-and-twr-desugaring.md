# 03 Java Core — `finally` duplication and try-with-resources desugaring — INTERNALS (§3.9, 3.9.3–3.9.4)

**Target version: Java 21 LTS.** | **Part 3 of 5** | [Index](../00-index.md)
Previous: [Exception mechanics — the exception table](03-internals-exception-mechanics.md) · Next: [Stack-trace capture and its cost](03b-internals-stack-trace-capture.md)

The JVM has no instruction that means "run this code on the way out, however I leave." `javac` has to build that behaviour out of ordinary instructions and the exception table from [`03-internals-exception-mechanics.md`](03-internals-exception-mechanics.md), and the only tool it has for "run this no matter which way control leaves" is to **write the code once per way it can leave**. That single fact explains everything in this file: why a `return` in `finally` swallows an in-flight exception, why a large `finally` body is a code-size tax proportional to the number of exits from the `try`, and why try-with-resources — which is specified as sugar over exactly this same `try`/`finally` shape — duplicates its own close calls the same way.

All bytecode below was measured on **Oracle JDK 21.0.7 (21.0.7+8-LTS-245, macOS aarch64)**, `javac -g`, with cross-compiler checks against **Oracle JDK 17.0.15**, **11.0.27** and **1.8.0_202**. JDK 7 is not installed on this machine; every claim resting on it is marked `**Unverified:**` and recorded in [Open questions](#open-questions) rather than asserted.

The language-level rules for `finally` and try-with-resources are owned elsewhere and are not repeated here: [`01c-try-with-resources-and-suppression.md`](01c-try-with-resources-and-suppression.md) owns the construct and the observable suppression behaviour with measured runtime output; [`01d-finally-traps.md`](01d-finally-traps.md) owns `return`-in-`finally`, a throwing `finally`, and `System.exit` as pitfalls at the language level; [`02e-resources-interrupts-and-testing.md`](02e-resources-interrupts-and-testing.md) owns try-with-resources in practice and defers the null-check bytecode to this file. This file owns only the compiled shape those three build on. [`03-internals-exception-mechanics.md`](03-internals-exception-mechanics.md) (`Previous`) already established the exception table's four fields, `athrow`'s search, and previewed this file's three-row `any` table from `split` below — that structure is assumed known here, not re-derived.

---

## 1. `finally` is compiled by duplication (3.9.3)

`[BYTECODE]` `[SOURCE]` `[PROVE]` The mental model: `javac` cannot emit "run this code once, regardless of exit." It can only emit ordinary straight-line instructions at specific points in the method. So for every distinct point control can leave the `try`/`catch` region, `javac` writes a full copy of the `finally` body immediately before that exit, plus one extra copy behind a handler that catches everything, for the case where something goes wrong that none of the written exits anticipated. A `try` with a `catch` and a `finally` has (at minimum) three ways out — the `try` body finishing normally, the `catch` body finishing normally, and something escaping both — and `javac` writes the `finally` body three times.

### Why it exists

An older design existed and was abandoned, and the reason it was abandoned is one of the better stories in the class file format. Early `javac` (pre-Java 6) shared the `finally` body across every exit path using two instructions built for exactly this: `jsr` (jump to subroutine — push the return address, jump) and `ret` (return to the address in a local variable). One copy of the body, several `jsr`-to-it call sites, one `ret` at the end. That is real code sharing, and it is what a modern compiler backend would reach for by default.

It was dropped because of the **verifier**, not because of any runtime cost. The bytecode verifier proves — statically, before a method ever runs — that every instruction is reached with a stack and set of local-variable types consistent with every possible path to it. A `jsr` target is reachable from multiple call sites, each of which may have arrived with different types live in some local variable (a `finally` block reached from inside a `try` versus reached from inside its `catch` can see different locals initialized), and `ret` returns to a *computed* address held in a local, not a fixed target the verifier can enumerate. Type-checking that precisely, for all possible predecessors of a `jsr` target and all possible destinations of a `ret`, needs a polymorphic analysis the verifier's original single-pass, fixed-type-per-slot algorithm could not express. The practical fix was not "write a cleverer verifier" — it was "stop emitting `jsr`/`ret` and duplicate the body instead," which turns a hard verification problem into instructions the ordinary type-checking pass already handles, because a duplicated `finally` body is just more straight-line code with one predecessor shape at each copy.

**Unverified:** the exact JVMS clause banning `jsr`/`jsr_w`/`ret` in class files of version 50.0 (Java SE 6) or above could not be fetched and quoted verbatim in this session — the specification page is too large for this session's fetch tool to return in full, and repeated targeted fetches at §4.9 and §6.5 both came back truncated before reaching the relevant sentence. What is independently confirmed here, from JVMS Table 4.7-A: the `StackMapTable` attribute — the verifier's own replacement machinery for the polymorphic checking `jsr`/`ret` needed — was first defined at class file version **50.0**, the same version historically cited as the one after which `jsr`/`jsr_w` stopped being legal. The two facts are consistent with the standard account (`jsr`/`ret` retired, `StackMapTable`-based single-pass verification took over, at the same version boundary), but the retirement clause itself is not independently quoted here. See [Open questions](#open-questions).

The measurable, load-bearing consequence of the retirement is on this page regardless of that one unconfirmed clause: every `javap` listing below shows duplicated bodies and zero `jsr`/`ret` instructions, on a compiler more than a decade newer than the change.

### When this changes what you do

It reframes the `return`-in-`finally` trap as **inevitable given the duplication scheme**, not an arbitrary language wart. [`01d-finally-traps.md`](01d-finally-traps.md) owns the pitfall at the language level — this file explains why the compiler had no other choice once it commits to writing the `finally` body as ordinary straight-line code at each exit: if that copy ends in its own `return`, it is by construction the *last* instruction control executes at that exit, and whatever the `try` or `catch` was about to do — return a value, propagate a `Throwable` — never happens, because the duplicated copy's own exit instruction runs instead. Nothing decides to "swallow" anything; the copy at the `any`-handler's exit point simply ends differently than the other copies, and this is that decision made visible.

It also turns "avoid large `finally` blocks in methods with many exit paths" from a vague warning into an arithmetic one: the `finally` body's size multiplies by the number of exits, not by a small constant, and that multiplication is measured below.

### How it works

`[BYTECODE]` The method under test, from a payments audit path:

```java
static int split(int stakeMinor) {
    try {
        return stakeMinor / 10;
    } catch (ArithmeticException e) {
        return 0;
    } finally {
        audit(stakeMinor);
    }
}
```

`javap -c -p -v` output, verbatim, measured on JDK 21.0.7:

```
static int split(int);
  descriptor: (I)I
  flags: (0x0008) ACC_STATIC
  Code:
    stack=2, locals=4, args_size=1
       0: iload_0
       1: bipush        10
       3: idiv
       4: istore_1
       5: iload_0
       6: invokestatic  #19                 // Method audit:(I)V
       9: iload_1
      10: ireturn
      11: astore_1
      12: iconst_0
      13: istore_2
      14: iload_0
      15: invokestatic  #19                 // Method audit:(I)V
      18: iload_2
      19: ireturn
      20: astore_3
      21: iload_0
      22: invokestatic  #19                 // Method audit:(I)V
      25: aload_3
      26: athrow
    Exception table:
       from    to  target type
           0     5    11   Class java/lang/ArithmeticException
           0     5    20   any
          11    14    20   any
    LineNumberTable:
      line 25: 0
      line 29: 5
      line 25: 9
      line 26: 11
      line 27: 12
      line 29: 14
      line 27: 18
      line 29: 20
      line 30: 25
    LocalVariableTable:
      Start  Length  Slot  Name   Signature
         12       8     1     e   Ljava/lang/ArithmeticException;
          0      27     0 stakeMinor   I
    StackMapTable: number_of_entries = 2
      frame_type = 75 /* same_locals_1_stack_item */
        stack = [ class java/lang/ArithmeticException ]
      frame_type = 72 /* same_locals_1_stack_item */
        stack = [ class java/lang/Throwable ]
```

Read it instruction by instruction, in three blocks.

**Block 1, PC 0–10, the normal return path.** `0: iload_0` / `1: bipush 10` / `3: idiv` computes `stakeMinor / 10`. Then `4: istore_1` — the division's result is stashed in local slot 1 **before** the `finally` runs, not returned directly. `5: iload_0` / `6: invokestatic audit` is the first copy of the `finally` body. `9: iload_1` reloads the stashed result, `10: ireturn` returns it. The stash-then-reload is not incidental: it is why a `finally` cannot change the value the `try` already computed by assigning to a local variable — the value was copied out before the `finally` block's own instructions run at all, and the `finally` body has no way to reach back and overwrite slot 1 that the source doesn't already give it (assigning to `stakeMinor` inside `finally` would change slot 0, not slot 1).

**Block 2, PC 11–19, the catch path.** `11: astore_1` stores the caught `ArithmeticException` (the `LocalVariableTable` confirms slot 1 is reused here as `e`, its earlier life as the division result over). `12: iconst_0` / `13: istore_2` computes and stashes the catch's return value, `0`, into slot 2. `14: iload_0` / `15: invokestatic audit` is the **second** copy of the identical `finally` body. `18: iload_2` / `19: ireturn` reloads and returns.

**Block 3, PC 20–26, the synthetic `any` handler.** `20: astore_3` stores whatever `Throwable` arrived — either an exception escaping the `try` body that is not an `ArithmeticException`, or one thrown by the `catch` block itself. `21: iload_0` / `22: invokestatic audit` is the **third** copy of the `finally` body. `25: aload_3` / `26: athrow` reloads the saved `Throwable` and rethrows it. Three identical two-instruction bodies, at PC 5–6, 14–15 and 21–22, doing exactly `iload_0; invokestatic audit:(I)V` each time.

The exception table carries the shape:

| Row | Range guarded | Target | `catch_type` | What it protects |
|---|---|---|---|---|
| 1 | `[0, 5)` | 11 | `ArithmeticException` | The `try` body's division, routed to the user's `catch` |
| 2 | `[0, 5)` | 20 | `any` | The `try` body, routed to the `finally` copy for anything the `catch` doesn't handle |
| 3 | `[11, 14)` | 20 | `any` | The `catch` **block's own body** — if `audit` itself threw, or if the catch body could throw, this still reaches the `finally` |

Row 3's range is `[11, 14)`, which is the catch body up to but excluding its own `finally` copy at PC 14–15 — the `any` handler is not guarding its own copy of the `finally`, which is what stops the handler from catching an exception thrown by its own duplicate and recursing into itself. Two `any`-typed rows target the same handler at PC 20, matching this file's `Previous`'s general rule that any number of exception-table rows may share one `handler_pc` — the `any`-catch-type row is not a special case of that mechanism, it is an ordinary use of it.

The three copies against what guards each, together:

| Copy | PCs | Guarded/reached by | Exit taken after |
|---|---|---|---|
| 1 | 5–6 | Falls through from the `try` body finishing normally | `ireturn` at 10 (stashed value from slot 1) |
| 2 | 14–15 | Falls through from the `catch` body finishing normally | `ireturn` at 19 (stashed value from slot 2) |
| 3 | 21–22 | Reached only via the `any` handler at 20, rows 2 and 3 | `athrow` at 26 (rethrow of slot 3) |

The `LineNumberTable` shows the same duplication in debug metadata: line 29, the source line of `audit(stakeMinor);`, is listed three times — at PC 5, 14 and 20. That has two concrete practical effects. A breakpoint set on the `finally` line in a debugger resolves to three distinct bytecode offsets, so a single logical breakpoint can fire three separate times for three structurally different reasons on one call to `split`. And a sampling profiler attributing cost by line number will spread the `finally` body's true cost across three separate call sites in its own view, none of which by itself looks like "the whole `finally` cost" — a profile that undercounts a hot `finally` unless the reader already knows to sum across the duplicated PCs.

### The diagram

![D-114 — `finally` is duplicated into every exit path](../diagrams/D-114-finally-duplication.svg)

**D-114** — Two panels. The left panel places `split`'s source beside the measured listing above, with the three `finally` copies at PC 5–6, 14–15 and 21–22 each highlighted and the three-row exception table drawn underneath, its two `any` rows both arrowed to the shared handler at PC 20. The right panel is the try-with-resources shape from concept 2: the inlined close calls, the absence of any `ifnull` guard for a `new`-expression resource, the primary-exception local at slot 3, and the `addSuppressed` call at PC 46 — the same duplication principle, one level up, applied to a close instead of an arbitrary block.

### A concrete example — the swallow, and the cost of duplication measured

`[PROVE]` First, the trap this mechanism makes inevitable. Source, from a stake-reservation path:

```java
final class InsufficientFundsException extends RuntimeException {
    InsufficientFundsException(String message) { super(message); }
}

static int swallow(int stakeMinor) {
    try {
        throw new InsufficientFundsException("CLIENT_CASH_AVAILABLE too low");
    } finally {
        return -1;
    }
}
```

Measured `javap -c -p -v`, JDK 21.0.7:

```
static int swallow(int);
  descriptor: (I)I
  flags: (0x0008) ACC_STATIC
  Code:
    stack=3, locals=2, args_size=1
       0: new           #31                 // class InsufficientFundsException
       3: dup
       4: ldc           #33                 // String CLIENT_CASH_AVAILABLE too low
       6: invokespecial #35                 // Method InsufficientFundsException."<init>":(Ljava/lang/String;)V
       9: athrow
      10: astore_1
      11: iconst_m1
      12: ireturn
  Exception table:
     from    to  target type
         0    11    10   any
```

There is only one exit here — the `try` body never falls through, it always throws — so `javac` needs only the `any` copy: `10: astore_1` saves the in-flight `InsufficientFundsException` to slot 1, and the `finally` copy is `11: iconst_m1; 12: ireturn`. Nothing after PC 10 ever reads slot 1. The exception was captured, the `finally` copy's own `ireturn` ran instead of a rethrow, and `-1` is what `swallow` returns — silently, with no trace of the `InsufficientFundsException` anywhere in the return value or in any log unless something upstream explicitly inspects a suppressed or swallowed exception, which nothing here does. [`01d-finally-traps.md`](01d-finally-traps.md) is where the language-level shape of this pitfall, and how to avoid writing it, live in full; the point here is narrower: the compiler was never given a choice. Once the `finally` body is written as ordinary code ending in `return -1`, that `return` *is* the exit instruction for that copy, exactly as `return`, `ireturn` and `athrow` are the exit instructions for the other copies measured above. There is no fourth kind of instruction meaning "run this, then resume whatever was already in flight" for `javac` to have reached for instead.

Second, the code-size argument, measured rather than asserted. The same four-byte `finally` body (`iload_0; invokestatic audit:(I)V`) against a rising number of exit paths, all compiled with `javac -g` on JDK 21.0.7:

```java
static void oneExit(int stakeMinor) {          // try/finally, no catch — implicit fall-through only
    try {
        audit(stakeMinor);
    } finally {
        audit(stakeMinor);
    }
}

static int twoExit(int stakeMinor) {           // try/catch/finally — this file's split, one catch
    try {
        return stakeMinor / 10;
    } catch (ArithmeticException e) {
        return 0;
    } finally {
        audit(stakeMinor);
    }
}

static int threeExit(int stakeMinor) {         // try/catch/catch/finally — two catches
    try {
        return stakeMinor / 10;
    } catch (ArithmeticException e) {
        return 0;
    } catch (RuntimeException e) {
        return -1;
    } finally {
        audit(stakeMinor);
    }
}
```

| Method | Written exits (normal + catches) | `finally` copies emitted | `Code` array length (measured) |
|---|---|---|---|
| `oneExit` | 1 (fall-through only, no catch) | 2 | 19 bytes |
| `twoExit` (`split`, above) | 2 (normal return, one catch) | 3 | 27 bytes |
| `threeExit` | 3 (normal return, two catches) | 4 | 36 bytes |

Every written exit gets its own copy, plus exactly one more for the shared `any` handler — copies = written exits + 1, and each copy costs the `finally` body's own byte length. `oneExit`'s single copy count of 2 (not 1) is the detail worth pausing on: even a `try`/`finally` with **no** `catch` at all still needs the `any` copy, because the JVM has to run the `finally` on the way out whether the `try` body finishes normally or throws something nobody names — a bare `try`/`finally` is exactly two exits, not one, and `oneExit`'s exception table (`[0, 4) → 11, any`) confirms it: one row, guarding the whole body, feeding the second copy. The growth from 19 to 27 to 36 bytes, 8–9 bytes per additional catch clause here, is linear in the number of exits, not in anything about the `finally` body's own complexity — a `finally` doing real work (opening a `LedgerConnection`, calling `FundsLedger`, formatting a log line) multiplies that per-copy cost by however many bytes that body actually is. The mitigation this file's row calls for follows directly: keep the `finally` body itself a call to a small, separately compiled method — `audit(stakeMinor)` already is exactly that — so what gets duplicated at each exit is a three-to-five-byte `invokestatic`, and the JIT is free to inline the callee back in on whichever exit path turns out hot, rather than duplicating a large inline body four times over in the class file itself.

### The gotcha

**Pitfall:** believing the `finally` block appears once in the class file, because it appears once in the source. It does not — see the [Pitfalls](#pitfalls) section below for the full wrong/right pairing, including the measured evidence that a large `finally` in a method with several catch clauses is a code-size multiplier, not a fixed cost.

**Interview:** "Why does a `return` in `finally` swallow an exception?" — because `javac` writes the `finally` body as ordinary straight-line code at every exit point, including the synthetic `any` handler that reruns it before a pending `athrow`; if that copy's own last instruction is `return`/`ireturn`/`areturn` instead of `athrow`, that instruction is what actually executes, and the pending exception in the local slot the `any` handler stashed it in is simply never read again. Point to [`01d-finally-traps.md`](01d-finally-traps.md) for the language-level framing and the fix.

> **Definition.** `javac` compiles `finally` by emitting the block's body once per exit path from the guarded `try`/`catch` — one copy for the `try` body completing normally, one for each `catch` completing normally, and one behind a synthetic `catch_type = 0` ("any") handler for anything else — rather than sharing a single copy via `jsr`/`ret`, which class files of version 50.0 and later do not use because the polymorphic control flow a shared `jsr` target requires defeated the original verifier's single-pass type-checking algorithm; the resulting code size is `(written exits + 1) × body size`, and a `return`/`break`/`continue` inside any one copy replaces that copy's normal continuation, which is the entire mechanism behind the swallow.

---

## 2. Try-with-resources desugaring: the primary-exception local, the null check, and `addSuppressed` (3.9.4)

`[BYTECODE]` `[SOURCE]` `[PROVE]` The mental model: a `try (Resource r = …) { … }` is not a new JVM capability at all. It is specified as an ordinary `try`/`finally` — exactly the shape concept 1 just took apart — wrapped around a second, inner `try`/`catch` whose job is solely to close the resource and, if that close itself throws while another exception is already in flight, staple the second failure onto the first with `addSuppressed` instead of letting it replace it. `javac`'s actual output is a *leaner* rendering of that same specified shape, not a different mechanism.

### Why it exists

Before Java 7, closing a resource safely required a hand-written `finally` with its own null check and its own decision about what to do if the resource's own `close()` threw while the `try` body was already failing — and the almost-universal hand-written answer was to let the close exception silently replace the real one, because writing the correct behaviour (report the original failure, attach the close failure as auxiliary information) by hand is enough boilerplate that essentially nobody did it consistently. Java 7 moved that specific piece of boilerplate into the compiler, keyed off `AutoCloseable`, and specified its expansion precisely enough that every compliant `javac` produces the same *observable* behaviour even if the instructions differ in shape — which is exactly what the version comparison below demonstrates.

### When this changes what you do

It explains, mechanically, why the reserved word for the platform's answer is *suppression* rather than *replacement*: the specified expansion keeps a dedicated **primary-exception local**, so the original failure is never overwritten — a close failure is attached to it via `addSuppressed` and the primary is what actually propagates. It also explains a specific asymmetry a reader will eventually be asked about: a `null`-checked close appears only for a resource `javac` cannot prove non-null, never for a `new`-expression resource, because the compiler already has the proof it needs in the second case.

### How it works

`[BYTECODE]` Two resources declared with `new` expressions, from a payment-run flush:

```java
static void flush(String runId) {
    try (LedgerConnection ledger = new LedgerConnection();
         PaymentRunFileWriter file = new PaymentRunFileWriter()) {
        ledger.write(runId);
        file.append(runId);
    }
}
```

Measured `javap -c -p -v`, JDK 21.0.7:

```
static void flush(java.lang.String);
  Code:
     0: new           #37                 // class LedgerConnection
     3: dup
     4: invokespecial #39                 // Method LedgerConnection."<init>":()V
     7: astore_1
     8: new           #40                 // class PaymentRunFileWriter
    11: dup
    12: invokespecial #42                 // Method PaymentRunFileWriter."<init>":()V
    15: astore_2
    16: aload_1
    17: aload_0
    18: invokevirtual #43                 // Method LedgerConnection.write:(Ljava/lang/String;)V
    21: aload_2
    22: aload_0
    23: invokevirtual #46                 // Method PaymentRunFileWriter.append:(Ljava/lang/String;)V
    26: aload_2
    27: invokevirtual #49                 // Method PaymentRunFileWriter.close:()V
    30: goto          51
    33: astore_3
    34: aload_2
    35: invokevirtual #49                 // Method PaymentRunFileWriter.close:()V
    38: goto          49
    41: astore        4
    43: aload_3
    44: aload         4
    46: invokevirtual #54                 // Method java/lang/Throwable.addSuppressed:(Ljava/lang/Throwable;)V
    49: aload_3
    50: athrow
    51: aload_1
    52: invokevirtual #58                 // Method LedgerConnection.close:()V
    55: goto          74
    58: astore_2
    59: aload_1
    60: invokevirtual #58                 // Method LedgerConnection.close:()V
    63: goto          72
    66: astore_3
    67: aload_2
    68: aload_3
    69: invokevirtual #54                 // Method java/lang/Throwable.addSuppressed:(Ljava/lang/Throwable;)V
    72: aload_2
    73: athrow
    74: return
  Exception table:
     from    to  target type
        16    26    33   Class java/lang/Throwable
        34    38    41   Class java/lang/Throwable
         8    51    58   Class java/lang/Throwable
        59    63    66   Class java/lang/Throwable
  LocalVariableTable:
    Start  Length  Slot  Name   Signature
       16      35     2  file   LPaymentRunFileWriter;
        8      66     1 ledger   LLedgerConnection;
        0      75     0 runId   Ljava/lang/String;
```

Read it as two nested blocks, inner resource first, matching reverse-declaration-order closing.

**Construction, PC 0–15.** `0–7`: `new LedgerConnection(); astore_1` — slot 1 is `ledger`. `8–15`: `new PaymentRunFileWriter(); astore_2` — slot 2 is `file`. Both are plain `new`-expressions; `javac` has a static proof neither can be `null` at this point, which is why no guard appears anywhere in this listing.

**Body, PC 16–25.** `ledger.write(runId)` then `file.append(runId)`, unremarkable.

**Inner resource's close, PC 26–50 — `file`, closed first because it was opened last.** `26: aload_2; 27: invokevirtual close()` is the **normal-path close**: the body finished without throwing, so `file` is closed directly, then `30: goto 51` skips past the exceptional-path logic straight to the outer resource's close. `33: astore_3` is the **exceptional-path** entry — something thrown in `[16, 26)` lands here, and slot 3 is the **primary-exception local**: the failure that actually happened first. `34: aload_2; 35: invokevirtual close()` retries the same close, now inside its own guarded range `[34, 38)`. If that succeeds, `38: goto 49` skips the suppression logic and goes straight to rethrowing the primary. If the retried close **also** throws, `41: astore 4` captures the close failure into slot 4, and `43: aload_3; 44: aload 4; 46: invokevirtual addSuppressed` attaches the close failure to the primary — `primary.addSuppressed(closeFailure)` — before `49: aload_3; 50: athrow` rethrows the **primary**, now carrying the close failure as auxiliary data rather than having been replaced by it.

**Outer resource's close, PC 51–73 — `ledger`, the mirror of the block above at a wider range.** `51: aload_1; 52: invokevirtual close()` is the normal-path close, `55: goto 74` to `return`. `58: astore_2` — note slot 2 is reused here; `file`'s own slot is dead by this point, so the primary-exception local for the *outer* resource reuses it rather than allocating a fresh slot — captures whatever escaped everything above (either the original body failure that the inner block just finished rethrowing, or nothing if the inner block succeeded and control reached here via the exceptional path of something else). `59–63` retries `ledger.close()`; `66: astore_3` captures a second-level close failure into (again reused) slot 3, `67–69` calls `addSuppressed` on the outer primary, `72–73` rethrows it.

The exception table, read against which resource and which phase each row exists for:

| Row | Range | Target | Resource | Phase |
|---|---|---|---|---|
| `[16, 26)` | body | 33 | `file` (inner) | Body threw — enter `file`'s exceptional close |
| `[34, 38)` | `file`'s retried close | 41 | `file` (inner) | Close itself threw — capture as suppressed |
| `[8, 51)` | body + all of `file`'s handling | 58 | `ledger` (outer) | Anything above threw — enter `ledger`'s exceptional close |
| `[59, 63)` | `ledger`'s retried close | 66 | `ledger` (outer) | Close itself threw — capture as suppressed |

Two facts about the ranges are worth reading slowly rather than skimming past. First, row 3's range **starts at PC 8**, not PC 16 — it covers `file`'s own construction (`[8, 15]`) as well as the body and `file`'s handling. That is the guarantee that a failure while *constructing the second resource* still closes the *first*: if `new PaymentRunFileWriter()` itself threw, control would already be inside `[8, 51)`, `ledger` would still get closed via row 3's handler, and the never-fully-constructed `file` — whose `astore_2` never ran — is simply not something the close logic ever touches, because nothing in the surrounding code references slot 2 as `file` until after its constructor has returned. Second, there is **no `ifnull` anywhere** in this listing, for either resource, at either close site — four separate close call sites, zero null checks — because both resources are `new`-expressions and `javac` has already proven, at compile time, that neither variable can hold `null` by the time any of the four close sites runs.

And there is no `$closeResource` method anywhere in this class. `javap -p` on the compiled class, verbatim, JDK 21.0.7:

```
Compiled from "Split.java"
public class Split {
  public Split();
  static void audit(int);
  static int split(int);
  static int swallow(int);
  static void flush(java.lang.String);
  static LedgerConnection open();
  static void flushEffectivelyFinal(java.lang.String);
  public static void main(java.lang.String[]);
}
```

No synthetic member of any kind, on any class in the compilation unit. The entire close-and-suppress sequence for both resources is **inlined directly into `flush`**, the same way the `finally` bodies in concept 1 were inlined into `split` rather than factored into a helper. **Unverified:** a `$closeResource` static helper method is widely attributed to an earlier `javac` — plausibly the Java 7 compiler that introduced the feature, given how directly the *specified* translation in the next paragraph reads as something worth factoring into a shared helper — but JDK 7 is not installed on this machine and that attribution could not be measured here. What **is** measured, across every compiler this machine has: `javap -p` on classes compiled by javac 8u202, 11.0.27, 17.0.15 and 21.0.7 lists no `$closeResource` member for either a `new`-expression resource or the effectively-final resource below. Treat "`javac` emits a `$closeResource` helper" as **version-stale** folklore for any compiler measured here, and as unconfirmed rather than false for Java 7 specifically. See [Open questions](#open-questions).

`[SOURCE]` The specification gives the reason the shape above is legitimate even though it is not what the JLS's own translation literally writes down. JLS SE 21 §14.20.3.1, "Basic `try`-with-resources", specifies the translation of the single-resource form verbatim:

```
try {
    try (ResourceType resource = Expression) {
        Block
    }
}
```

is translated to:

```
{
    final ResourceType #resource = Expression;
    Throwable #primaryExc = null;
    try {
        Block
    } catch (Throwable #t) {
        #primaryExc = #t;
        throw #t;
    } finally {
        if (#resource != null) {
            if (#primaryExc != null) {
                try {
                    #resource.close();
                } catch (Throwable #suppressedExc) {
                    #primaryExc.addSuppressed(#suppressedExc);
                }
            } else {
                #resource.close();
            }
        }
    }
}
```

Read this against the measured bytecode above, because the relationship between the two is the sharpest thing in this file: the JLS specifies an **equivalent program**, written in the ordinary `try`/`catch`/`finally` and `if` constructs concept 1 already covers — it is not a specification of instructions, and it is not obligated to describe what `javac` literally emits. What `javap` shows for `flush` is a *lower-level optimisation* of that same equivalent program: the specified form catches `Throwable` unconditionally into `#primaryExc` even on the success path and then branches on `#primaryExc != null` and `#resource != null` inside the `finally`; the measured bytecode instead splits the **normal** completion of the body (PC 26–27, PC 51–52 — a bare, unguarded close, no exception object involved at all) from the **exceptional** completion (PC 33 onward, PC 58 onward — where the primary-exception local and the suppression logic actually appear) as two separate code paths reached by ordinary control flow rather than by testing a boolean-like `null` check on every call. Same observable behaviour, specified as one program shape, compiled as a leaner one — which is exactly the relationship a specification is supposed to have with an implementation, and precisely why quoting `javap` alone would have been the wrong `[SOURCE]` citation here: the spec text is what proves the *behaviour* is guaranteed across compilers, not what predicts the *instructions*.

### The diagram

D-114's second panel, embedded already in concept 1, carries this concept's picture: the inlined close calls for `flush`, the absence of an `ifnull` on the `new`-expression path, the primary-exception local at slot 3, and the `addSuppressed` call at PC 46 — the same PCs and slot numbers used in the walk above.

### A concrete example — the effectively-final form, and the version comparison

`[BYTECODE]` `[PROVE]` Second measurement: a resource that is not a `new`-expression, so `javac` cannot prove it non-null, using the Java 9 effectively-final try-with-resources form (a bare variable name in the resource specification rather than a declaration):

```java
static LedgerConnection open() { return new LedgerConnection(); }

static void flushEffectivelyFinal(String runId) {
    LedgerConnection ledger = open();
    try (ledger) {
        ledger.write(runId);
    }
}
```

Measured, JDK 21.0.7:

```
static void flushEffectivelyFinal(java.lang.String);
  Code:
     0: invokestatic  #59                 // Method open:()LLedgerConnection;
     3: astore_1
     4: aload_1
     5: astore_2
     6: aload_1
     7: aload_0
     8: invokevirtual #43                 // Method LedgerConnection.write:(Ljava/lang/String;)V
    11: aload_2
    12: ifnull        44
    15: aload_2
    16: invokevirtual #58                 // Method LedgerConnection.close:()V
    19: goto          44
    22: astore_3
    23: aload_2
    24: ifnull        42
    27: aload_2
    28: invokevirtual #58                 // Method LedgerConnection.close:()V
    31: goto          42
    34: astore        4
    36: aload_3
    37: aload         4
    39: invokevirtual #54                 // Method java/lang/Throwable.addSuppressed:(Ljava/lang/Throwable;)V
    42: aload_3
    43: athrow
    44: return
  Exception table:
     from    to  target type
         6    11    22   Class java/lang/Throwable
        27    31    34   Class java/lang/Throwable
```

Two differences from `flush`, both explained by the same cause: `ledger` came from a method call, `open()`, and `javac` cannot prove a method's return value is non-null. First, `ifnull` appears **twice** — once per close site, PC 12 on the normal path and PC 24 on the exceptional path — because a `null` resource is legally permitted here (the effectively-final form's whole point is to allow resources acquired earlier, including ones a caller might have passed in as `null`) and skipping `close()` on a `null` reference is required, not optional. Second, `ledger` (slot 1) is copied into a **second slot**, slot 2, at PC 4–5 (`aload_1; astore_2`), and every subsequent read of the resource for closing purposes reads slot 2, not slot 1. That copy is the mechanical reason the resource must be *effectively final*: the close logic reads a **snapshot** taken once, at the top of the `try`, so a hypothetical later reassignment of `ledger` (which effective-finality forbids at the source level) could not have silently changed which object gets closed — the snapshot in slot 2 is fixed the instant it is taken, independent of whatever slot 1 might do afterward.

The exception table again names resource and phase precisely: `[6, 11)` guards the body and routes to the exceptional close at 22; `[27, 31)` guards the retried close and routes to the suppression logic at 34 — the same two-row, body-then-retry shape as one resource's handling in `flush` above, minus the second resource.

Now the version comparison the row asks for, run rather than recalled: the identical single-resource, `new`-expression source,

```java
final class LedgerConnection implements AutoCloseable {
    void write(String runId) { System.out.println("write " + runId); }
    public void close() { System.out.println("close ledger"); }
}
public class SingleFlush {
    static void flush(String runId) {
        try (LedgerConnection ledger = new LedgerConnection()) {
            ledger.write(runId);
        }
    }
}
```

compiled with `javac -g` from all four installed JDKs and measured with `javap -c -p` and file size:

```
javac 1.8.0_202  → SingleFlush.class: 818 bytes
javac 11.0.27    → SingleFlush.class: 710 bytes
javac 17.0.15    → SingleFlush.class: 710 bytes
javac 21.0.7     → SingleFlush.class: 710 bytes
```

The javac 8 body (87 instruction bytes, by PC count 0–86) carries a **pre-nulled primary-exception local** — `8: aconst_null; 9: astore_2` before the body even runs — and **nested** null checks: `ifnull` on the resource *and* a separate `ifnull` on the still-`null` primary at both the normal-path close (PC 16, PC 19) and the exceptional-path close (PC 54, PC 57), plus a second `any`-type exception-table row (`from 10 to 15 target 51`) that the javac 11/17/21 form does not have. The javac 11 body (measured identical to 17 and to 21, byte for byte in the `flush` method's own instructions) drops the pre-nulled local entirely, checks the resource for `null` **once** on the close paths where it matters, and needs one fewer exception-table row. **The simplification happened between javac 8 and javac 11** — this machine cannot narrow it further because JDK 9 and 10 are not installed, but Java 9 is independently the release that introduced the effectively-final resource form this concept's second listing exercises, which makes a compiler-internals refresh of the desugaring in the same release window unsurprising, if unconfirmed as *the* cause. See [Open questions](#open-questions) for the precise boundary this machine cannot pin down further.

| javac | `SingleFlush.class` size | Null checks on resource | Primary-exception local | Extra `any` row |
|---|---|---|---|---|
| 8u202 | 818 bytes | Yes, nested with a second check on the primary | Pre-nulled before the body runs | Yes — two `any` rows |
| 11.0.27 | 710 bytes | Yes, once per close site | Only introduced where actually needed | No — one `any` row per close phase |
| 17.0.15 | 710 bytes | identical to 11.0.27 | identical to 11.0.27 | identical to 11.0.27 |
| 21.0.7 | 710 bytes | identical to 11.0.27 | identical to 11.0.27 | identical to 11.0.27 |

### The gotcha

**Pitfall:** believing try-with-resources needs a null check for a `new`-expression resource "just in case." It does not, and adding one is redundant work the compiler has already proven unnecessary — see [Pitfalls](#pitfalls) below for the full pairing, including where a null check *does* legitimately appear.

**Insight:** the reason suppression exists as its own mechanism, rather than the close failure simply propagating on its own, falls straight out of the primary-exception local: once `javac` commits to keeping the original failure in a dedicated slot so it can be the thing that actually propagates, attaching a second failure to it via `addSuppressed` is the only option left that does not throw information away — the close failure has nowhere else to go once the primary local already owns the return path.

> **Definition.** `javac` desugars `try (Resource r = Expression) { Block }` per JLS §14.20.3.1 into a `Block` guarded by an inner `try`/`catch(Throwable)` that captures the body's failure into a dedicated primary-exception local, followed by a close that is retried inside its own guard; a close failure while a primary is already recorded is attached via `Throwable.addSuppressed` rather than replacing it, and the specified `if (#resource != null)` guard is emitted as a real `ifnull` only when the resource's non-nullity is not already provable — never for a `new`-expression resource, and always exactly once per close site for an effectively-final resource obtained by any other means; no `javac` measured on this machine (8, 11, 17, 21) emits a separate `$closeResource` helper for either shape.

---

## Pitfalls

### Assuming the `finally` block appears once in the class file

**Wrong**

```java
static int split(int stakeMinor) {
    try {
        return stakeMinor / 10;
    } catch (ArithmeticException e) {
        return 0;
    } finally {
        audit(stakeMinor);      // "this runs from one place"
    }
}
```

Measured on JDK 21.0.7: `audit(stakeMinor)` — `iload_0; invokestatic audit:(I)V` — appears at three separate program counters in the compiled `split`: PC 5–6 (the `try` body's normal-return path), PC 14–15 (the `catch` body's normal-return path), and PC 21–22 (the synthetic `any`-handler path). The source has one `finally` block; the class file has three copies of its body, one per exit the method can take. A profiler attributing cost by source line, or a breakpoint set on the `finally`'s line, interacts with all three independently.

**Right**

Treat `finally`'s cost as `(number of ways the guarded region can be left) × (size of the finally body)`, not as a fixed per-`try` cost. Measured: a bare `try`/`finally` with no `catch` still costs two copies (one for normal completion, one for the `any` handler); adding a `catch` clause adds roughly one more copy each. Keep a nontrivial `finally` body factored into a small separately-compiled method — what gets duplicated at each exit is then a three-to-five-byte `invokestatic`, not the full body, and the JIT remains free to inline the callee back in on whichever path is actually hot.

**Why people believe it:** every other block construct in the language — an `if`, a `for` body, an ordinary method body — appears exactly once in the compiled output, because those constructs have exactly one way to be entered and, ignoring early exits reached by ordinary jumps, effectively one way to fall off the end that the compiler can express with a single instruction sequence and some branches. `finally` looks the same in source, so it is natural to assume it compiles the same way, and nothing about reading the source alone reveals that it does not.

### Believing `javac` emits a `$closeResource` helper method for try-with-resources

**Wrong**

```java
// "javac factors resource closing into a synthetic $closeResource helper method,
// which is why decompiled try-with-resources code looks unfamiliar."
```

Measured on JDK 21.0.7, 17.0.15 and 11.0.27, for both a `new`-expression resource (`flush`, two resources) and an effectively-final resource obtained from a method call (`flushEffectivelyFinal`): `javap -p` on the compiled class lists no member named `$closeResource`, and no synthetic member of any kind, on any class in the compilation unit. The close-and-suppress logic is inlined directly into the method that declares the `try`, the same way the duplicated `finally` bodies in concept 1 are inlined into `split` rather than factored out.

**Right**

Expect the close logic inlined at every close site — normal-path and exceptional-path, per resource — with the primary-exception local and the conditional `ifnull` guard (only where the resource's non-nullity is not already provable) appearing directly in the enclosing method's own bytecode. **Unverified:** whether javac 7, which introduced the feature, used a `$closeResource` helper is not settled here — JDK 7 is not installed on this machine, so the claim could not be measured either way and is recorded, not asserted, in [Open questions](#open-questions). What is confirmed: no compiler from 8 through 21 measured here uses one.

**Why people believe it:** `$closeResource` is a real, widely repeated attribution, and it is entirely plausible it was accurate for the compiler that first shipped the feature — early versions of a new desugaring are a natural place to reach for a shared helper before a later release inlines it for size or clarity. The claim simply outlived the compiler it may have described, and nothing about decompiled Java 8-or-later bytecode prompts a re-check, because the *observable behaviour* — suppression, close order, null tolerance — is identical either way and gives no visible sign of which shape produced it.

### Assuming try-with-resources needs an explicit null check for every resource "just in case"

**Wrong**

```java
static void flush(String runId) {
    try (LedgerConnection ledger = new LedgerConnection();
         PaymentRunFileWriter file = new PaymentRunFileWriter()) {
        if (ledger != null) {                 // redundant — ledger cannot be null here
            ledger.write(runId);
        }
        if (file != null) {
            file.append(runId);
        }
    }
}
```

Measured on JDK 21.0.7: the compiled `flush` for the un-guarded version above contains **zero** `ifnull` instructions across all four close sites for both resources, because both are `new`-expressions and `javac` has already proven neither can be `null`. The `if (ledger != null)` checks in the guarded version compile to real, executed `ifnull` bytecode inside the method body — extra instructions that can never take their `null` branch, guarding a condition the compiler had already eliminated one level up, in the resource-management code the source cannot see.

**Right**

Write the resource body without defensive null checks when the resource is a `new`-expression or otherwise statically known non-null; reserve the check for the one case where it is real — a resource obtained from something whose contract permits `null`, at the call site that produces it, not inside the `try` body. Measured, `flushEffectivelyFinal`: `javac` itself inserts exactly the guard that is needed, `ifnull` once per close site (PC 12 and PC 24), for a resource obtained from a method call it cannot prove non-null — and inserts none at all for the two `new`-expression resources in `flush`, in the same compilation.

**Why people believe it:** "always null-check external state" is sound general advice, and try-with-resources looks like ordinary external state from inside the `try` body. What is missed is that the resource-*closing* null check the JLS's specified translation describes is the compiler's own defensive measure for resources it cannot prove non-null, not a general contract the source is expected to duplicate — and duplicating it inside the body checks the wrong thing anyway, since the compiled close logic already has its own independent guard where one is actually needed.

---

## Cheat sheet

| Thing | Fact (Java 21 LTS, measured unless noted) |
|---|---|
| `finally`, no `catch` | Still 2 copies of the body: normal completion + the synthetic `any` handler |
| `finally`, 1 `catch` | 3 copies (measured `split`: PC 5–6, 14–15, 21–22); `Code` length 27 bytes for a 4-byte body |
| `finally`, 2 `catch`es | 4 copies; `Code` length 36 bytes for the same 4-byte body |
| Copy count formula | `(written exits: normal + each catch) + 1` for the shared `any` handler |
| Why not `jsr`/`ret` | Verifier could not type-check a `jsr` target's polymorphic predecessors under the original single-pass algorithm |
| `StackMapTable` origin | Class file version 50.0 (JVMS Table 4.7-A) — confirmed on this machine's fetch |
| `jsr`/`jsr_w`/`ret` ban at 50.0+ | Standard account, **not independently quoted** in this session — see Open questions |
| `return` in `finally` swallows | The `any`-handler's copy ends in `return`/`ireturn`/`areturn` instead of `athrow` — nothing decides to swallow, the copy just ends differently |
| `split`'s exception table | 3 rows: `[0,5)→11 ArithmeticException`, `[0,5)→20 any`, `[11,14)→20 any` |
| `LineNumberTable` duplication | The `finally`'s source line appears 3 times (PC 5, 14, 20) — one breakpoint hits 3 offsets |
| Mitigation for a large `finally` | Factor the body into a small method; duplicated cost becomes one `invokestatic` per exit, inlinable by the JIT |
| TWR `new`-expression resource | Zero `ifnull` instructions anywhere — non-nullity proven at compile time |
| TWR effectively-final resource | `ifnull` **twice**, once per close site (measured PC 12, PC 24) |
| Resource snapshot | Copied to a second local slot (measured slot 1→2) before first use — the mechanical reason for effective finality |
| Primary-exception local | Slot holding the body's `Throwable`; reused by a second resource's own handling once the first is dead |
| Suppression call | `primary.addSuppressed(closeFailure)` — measured PC 46 (two-resource form), PC 39 (single effectively-final form) |
| Close order | Reverse declaration order — inner resource's close block comes first in the bytecode |
| Resource-construction-failure boundary | Outer resource's guarded range starts **before** the inner resource's `new` (measured `[8, 51)`), so a failed construction still closes what already succeeded |
| `$closeResource` helper | **Not emitted** by javac 8, 11, 17 or 21 on this machine (confirmed via `javap -p`, no synthetic member) |
| `$closeResource` for javac 7 | **Unverified** — JDK 7 not installed on this machine |
| javac 8 → 11 shape change | `SingleFlush.class`: 818 bytes (8u202) → 710 bytes (11.0.27, 17.0.15, 21.0.7) — pre-nulled local and extra `any` row dropped |
| Exact release the shape simplified | **Unverified past "somewhere in 9 or 10"** — those JDKs are not installed on this machine |
| JLS source for TWR | §14.20.3.1, "Basic try-with-resources" — a specified equivalent *program*, not a specified instruction sequence |
| Relationship of spec to bytecode | The measured bytecode is a leaner optimisation of the JLS's specified program, splitting normal- and exceptional-completion into separate paths instead of one boolean-guarded `finally` |

---

## Self-test

**Q1.** Why does `javac` write the `finally` body three times for a `try`/`catch`/`finally` with one `catch` clause, instead of once?

<details><summary>Answer</summary>

Because the JVM has no instruction meaning "run this code regardless of how control leaves," so `javac` has to place ordinary straight-line copies of the body at every point control can actually leave. Measured on JDK 21.0.7 for `split` (one `try`, one `catch (ArithmeticException e)`, one `finally`): the two-instruction body `iload_0; invokestatic audit:(I)V` appears at PC 5–6 (the `try` body finishing normally, en route to its own `ireturn`), PC 14–15 (the `catch` body finishing normally, en route to its own `ireturn`), and PC 21–22 (a synthetic `catch_type = 0` handler that catches anything not already handled, en route to an `athrow` that rethrows it). Three exits, three copies. An older design existed that could have shared one copy — `jsr`/`ret`, jump-to-subroutine — but it was retired because the verifier could not type-check a `jsr` target reached from multiple call sites with a single-pass, fixed-type-per-local algorithm; duplication turns that hard verification problem into ordinary straight-line code the existing verifier already handles. The measured cost of duplication is linear: 19, 27 and 36 bytes of `Code` for the identical 4-byte body against 1, 2 and 3 written exits respectively (formula: copies = written exits + 1).

</details>

**Q2.** A `finally` block ends in `return -1;` while the `try` body is in the middle of throwing an exception. What actually happens at the instruction level, and why does the compiler have no way to prevent it?

<details><summary>Answer</summary>

The `any`-handler's copy of the `finally` body captures the in-flight `Throwable` into a local slot that then goes unread, and its own final instruction — `ireturn`, because the source says `return -1;` — executes instead of the `athrow` that would otherwise rethrow the captured exception. Measured on JDK 21.0.7 for a `try { throw new InsufficientFundsException("CLIENT_CASH_AVAILABLE too low"); } finally { return -1; }`: the exception table has one `any` row, `[0, 11) → 10`; PC 10 is `astore_1` (the exception saved, permanently unread); PC 11–12 is `iconst_m1; ireturn`. The compiler has no way to prevent this because it has already committed, by the same mechanism concept 1 establishes, to writing the `finally` block as ordinary code at this exit point — and ordinary code's own final instruction is, by definition, what runs last at that exit. There is no fourth kind of instruction available that means "run this, then resume whatever was already in flight," so a `return`/`break`/`continue` written inside a `finally` block necessarily replaces whatever that exit was originally going to do. [`01d-finally-traps.md`](01d-finally-traps.md) covers this as a language-level pitfall to avoid writing; this file explains why, mechanically, the compiler could not have stopped it.

</details>

**Q3.** Why is there no `ifnull` check anywhere in the compiled `flush`, which declares two resources with `new` expressions, but there are two `ifnull` checks in `flushEffectivelyFinal`, which uses a resource obtained from a method call?

<details><summary>Answer</summary>

Because the JLS's specified translation (§14.20.3.1) guards the close with `if (#resource != null)` only as part of the specified *equivalent program* — it does not obligate every compiled resource to carry a runtime check, and `javac` only emits the real `ifnull` instruction where it cannot already prove the resource non-null. A `new`-expression's result is never `null`, by construction, so the compiler has that proof at compile time and omits the check entirely — measured on JDK 21.0.7, `flush`'s two `LedgerConnection`/`PaymentRunFileWriter` resources produce four close call sites total and zero `ifnull` instructions among them. A resource obtained from `open()`, an ordinary method call whose return type does not rule out `null`, gives `javac` no such proof, so the compiler falls back to the specified guard literally: measured `ifnull` at PC 12 (the normal-path close) and PC 24 (the exceptional-path close), one per close site, matching the two `if (#resource != null)` occurrences the specified translation names (one inside each branch of the specified `if (#primaryExc != null)`, collapsed here into the two actual close sites the optimised bytecode uses instead of the specified single `finally`).

</details>

**Q4.** Walk the primary-exception local through `flush`'s bytecode: where is it stored, what happens if the close it guards also throws, and what ends up propagating?

<details><summary>Answer</summary>

For the inner resource, `file`: if `[16, 26)` — the try body — throws, control lands at PC 33, `astore_3`, which stores that thrown object into slot 3. This is the primary. PC 34–35 retries `file.close()` inside its own guarded range `[34, 38)`. If that succeeds, PC 38 jumps straight to PC 49, `aload_3; athrow` at PC 50 — the primary propagates, close having succeeded silently. If the retried close **also** throws, control lands at PC 41, `astore 4`, capturing the close failure into slot 4; PC 43–46 executes `aload_3; aload 4; invokevirtual addSuppressed`, which is `primary.addSuppressed(closeFailure)`; then PC 49–50 still rethrows slot 3, the primary — now carrying the close failure as an attached suppressed exception rather than having been replaced by it. The outer resource, `ledger`, repeats the identical shape at PC 58 onward, reusing slot 2 and slot 3 (dead from the inner resource's handling by that point) for its own primary and secondary captures. What ends up propagating out of `flush` in every failure combination is always the **original** failure — the suppression mechanism exists precisely so a close failure never gets to be the thing callers see instead of the real cause.

</details>

**Q5.** Someone tells you `javac` compiles try-with-resources by generating a synthetic `$closeResource` method. Is that true on Java 21?

<details><summary>Answer</summary>

No, measured. `javap -p` on a class compiled by JDK 21.0.7's `javac`, for both a two-`new`-expression-resource `try` (`flush`) and an effectively-final single resource obtained from a method call (`flushEffectivelyFinal`), lists exactly the source-declared methods and no synthetic members at all — no `$closeResource`, no holder class, nothing. The close-and-suppress sequence is inlined directly into the enclosing method's own bytecode at every close site. The same check against javac 17.0.15 and 11.0.27 gives the identical result: no `$closeResource` on any of the three. The one honest gap: JDK 7, the release that introduced the feature, is not installed on this machine, so whether *that* compiler used a `$closeResource` helper is genuinely unconfirmed here rather than measured false — it is recorded as **Unverified**, not asserted either way, because the claim is old enough and specific enough that it plausibly described an earlier compiler generation before being simplified away, the same way the pre-nulled primary-exception local and the extra `any` row measured in javac 8's `SingleFlush` output were themselves simplified away by javac 11.

</details>

**Q6.** What is the exact relationship between JLS §14.20.3.1's specified translation and the bytecode `javap` actually shows for `flush`? Are they the same program?

<details><summary>Answer</summary>

Not instruction-for-instruction, and the JLS never claims they should be. §14.20.3.1 specifies a **source-level equivalent program** — an ordinary `try`/`catch(Throwable)`/`finally` with `if (#resource != null)` and `if (#primaryExc != null)` guards, evaluated on every path including the success path — and that equivalent program is itself something concept 1's rules would compile in the ordinary way. What `javap` shows for `flush` is a lower-level optimisation of that same specified behaviour: instead of testing `#primaryExc != null` inside one shared `finally`, the measured bytecode splits into two structurally separate paths reached by ordinary control flow — a bare, unguarded close on normal completion (no exception object involved, no test performed) at PC 26–27 and PC 51–52, and the primary-exception-local-plus-suppression logic only on the exceptional path, PC 33 onward and PC 58 onward. Both renderings produce identical observable behaviour — same suppression semantics, same close order, same null tolerance — which is exactly the contract a specification is meant to guarantee: not a particular instruction sequence, but a particular program behaviour that any conforming compiler must reproduce, however it chooses to lower it.

</details>

**Q7.** Compare `split`'s three-copy `finally` duplication against `flush`'s close-and-suppress duplication. What is the same principle, and what is different?

<details><summary>Answer</summary>

The same principle: both are "no shared-subroutine instruction exists, so write the code at every place it needs to run." `split` duplicates a `finally` body across the `try`'s normal exit, the `catch`'s normal exit, and a synthetic `any` handler — three copies of `iload_0; invokestatic audit:(I)V`. `flush` duplicates a **close call** across the normal-completion path and the exceptional-completion path, per resource — `file.close()` appears at PC 27 and again at PC 35; `ledger.close()` appears at PC 52 and again at PC 60. What differs is what rides along with the exceptional copy: `split`'s exceptional copy is the *identical* body running for a different reason, with no additional bookkeeping. `flush`'s exceptional copy carries extra machinery the normal copy does not need at all — a primary-exception local to hold the original failure, a nested guard around the retried close, and an `addSuppressed` call if that retry also fails — because a resource close, unlike an arbitrary `finally` body, has a *second* failure to reconcile against the first rather than simply running unconditionally. Both are still fundamentally the same answer to the same missing-instruction problem; try-with-resources is just a `finally`-duplication problem with an extra failure-reconciliation problem layered on top of it.

</details>

---

## Open questions

- **Unverified:** the exact JVMS clause and wording banning `jsr`, `jsr_w` and `ret` instructions in class files of version 50.0 or above. Repeated targeted fetches of JVMS SE 21 §4.9 (Constraints on Java Virtual Machine Code) and §6.5 (the `jsr` instruction's own Notes) in this session returned truncated content that stopped before the relevant sentence, and a web search for the exact phrasing did not surface it either. What is independently confirmed: JVMS Table 4.7-A dates the `StackMapTable` attribute to class file version 50.0, which is consistent with — but does not by itself prove — the standard account that `jsr`/`ret` were retired at the same version boundary in favour of `StackMapTable`-based verification. What would settle it: a direct read of JVMS SE 21 §4.9.1 or §4.10, or the `jsr` instruction's Notes in §6.5, ideally via a tool that can page through the full chapter rather than a single large fetch.
- **Unverified:** whether javac 7 — the release that introduced try-with-resources — emitted a synthetic `$closeResource` helper method, as is widely attributed to it. JDK 7 is not installed on this machine, so this could not be measured either way. What is measured, and is not the same claim: javac 8u202, 11.0.27, 17.0.15 and 21.0.7 all inline the close-and-suppress logic directly into the enclosing method with no synthetic member of any kind, confirmed via `javap -p`. What would settle the javac 7 question: access to a JDK 7 `javac`, or the corresponding OpenJDK javac changeset/commit history for the try-with-resources lowering, showing whether an intermediate synthetic method was ever part of the shape before being inlined.
- **Unverified:** the precise JDK release at which the try-with-resources desugaring simplified from the javac 8 shape (pre-nulled primary-exception local, nested double null checks, an extra `any` exception-table row) to the javac 11 shape (no pre-nulled local, a single null check per close site, one fewer `any` row) — measured only as "somewhere between 8u202 and 11.0.27" because JDK 9 and JDK 10 are not installed on this machine. It is plausible, but not confirmed here, that this coincides with JDK 9's introduction of the effectively-final resource form, since both changes touch the same desugaring machinery in the same release window. What would settle it: compiling the identical `SingleFlush` source with a JDK 9 or JDK 10 `javac` and diffing against both the 8u202 and 11.0.27 output measured in this file.

---

**Leaves covered:** 3.9.3, 3.9.4 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** D-114
**Target version:** Java 21 LTS
**Lines:** 671
