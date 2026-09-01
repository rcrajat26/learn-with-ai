# 03 Java Core — Diagnostic harnesses: the pass-by-value harness — BUILD IT (§4.8.7)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [The inner-class retention harness](05h-inner-class-retention.md) · Next: [The overload-resolution harness](05j-overload-resolution-harness.md)

One harness, `[PROVE]`. The printed result *is* the argument: a predicted result would be a
defect, so every claim below is followed by real output from
**Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64 (Apple silicon)**.

The companion leaf 4.8.8, the overload-resolution harness, is in
[the next file](05j-overload-resolution-harness.md).

---

## 4.8.7 The pass-by-value harness `[PROVE]`

### The shape

Java passes **every** argument by value. For a reference type, the value passed is the
reference — a machine word naming an object, copied into a fresh local-variable slot in the
callee's frame. Two consequences fall straight out of that, and they are the whole leaf:

- The callee can change **the object the reference points at**, because both slots name the
  same object.
- The callee cannot change **which object the caller's variable points at**, because writing
  the parameter writes the callee's slot, not the caller's.

Mutate, reassign, swap-attempt, `String` and the boxed `Integer` are five spellings of that
one sentence. `../immutability-and-design/03-pass-by-value.md` owns pass-by-value as a topic
and **D-088** is its diagram; this file owns the executed harness.

### Why it exists as a question at all

The confusion is inherited from C++, where `PaymentRun& run` genuinely gives the callee
write access to the caller's variable, and from a widely-copied sentence that Java "passes
objects by reference". Java has no reference parameters and no out-parameters. Once you
accept that a parameter is a *local variable slot initialised from a copy*, there is nothing
left to remember.

### How it works

At the JVMS level a method invocation pushes arguments onto the operand stack; on entry the
new frame's local-variable array slots 0..n-1 are populated from those stack words
(JVMS §2.6.1, §4.7.3 — the `Code` attribute's `max_locals`). A `static` method's first
parameter is slot 0; an instance method's slot 0 is `this` and parameters start at 1.
Assigning to a parameter compiles to a store into that slot (`astore` for a reference,
`istore` for an `int`). There is no mechanism by which that store reaches the caller's frame.

### The complete harness

```java
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;

public class PassByValueHarness {

    // A mutable aggregate: a batch of approved bank withdrawals awaiting operator sign-off.
    static final class PaymentRun {
        private final String runId;
        private final List<BigDecimal> withdrawals = new ArrayList<>();
        private String status;

        PaymentRun(String runId, String status) {
            this.runId = runId;
            this.status = status;
        }

        void addWithdrawal(BigDecimal amount) { withdrawals.add(amount); }
        void setStatus(String status) { this.status = status; }

        BigDecimal total() {
            return withdrawals.stream().reduce(BigDecimal.ZERO, BigDecimal::add);
        }

        @Override
        public String toString() {
            return "PaymentRun[" + runId + ", status=" + status
                    + ", count=" + withdrawals.size() + ", total=" + total() + "]";
        }
    }

    record StakeSplit(BigDecimal bonusPortion, BigDecimal cashPortion) {}

    // Case 1 — MUTATE. Changes the state of the object the reference points at.
    static void mutate(PaymentRun run) {
        run.addWithdrawal(new BigDecimal("260.00"));
        run.setStatus("SUBMITTED");
        System.out.println("  inside mutate:   " + run);
    }

    // Case 2 — REASSIGN. Same parameter type, opposite outcome.
    static void reassign(PaymentRun run) {
        run = new PaymentRun("PR-9002", "PENDING_VERIFICATION");
        run.addWithdrawal(new BigDecimal("999.99"));
        System.out.println("  inside reassign: " + run);
    }

    // Case 3 — SWAP-ATTEMPT.
    static void swapAttempt(PaymentRun first, PaymentRun second) {
        PaymentRun scratch = first;
        first = second;
        second = scratch;
        System.out.println("  inside swapAttempt: first=" + first.runId + " second=" + second.runId);
    }

    // What actually works: return both.
    record RunPair(PaymentRun first, PaymentRun second) {}

    static RunPair swapped(PaymentRun first, PaymentRun second) {
        return new RunPair(second, first);
    }

    // What also works, and what it costs: an array of two as an out-parameter.
    static void swapInArray(PaymentRun[] slot) {
        PaymentRun scratch = slot[0];
        slot[0] = slot[1];
        slot[1] = scratch;
    }

    // Case 4 — String.
    static void renameStatus(String status) {
        status = status.concat(" / AA-801 ACTIVATED");
        System.out.println("  inside renameStatus: " + status);
    }

    // Case 5 — the boxed primitive, same trap in a different disguise.
    static void bumpAttempt(Integer reservationCount) {
        reservationCount++;
        System.out.println("  inside bumpAttempt:  " + reservationCount);
    }

    // The record-returning shape for the stake split, for contrast: no mutation at all.
    static StakeSplit split(BigDecimal stake) {
        BigDecimal bonus = stake.multiply(new BigDecimal("0.10"))
                                .setScale(2, java.math.RoundingMode.DOWN);
        return new StakeSplit(bonus, stake.subtract(bonus));
    }

    public static void main(String[] args) {
        System.out.println("=== 1. MUTATE ===");
        PaymentRun run = new PaymentRun("PR-9001", "PENDING_VERIFICATION");
        run.addWithdrawal(new BigDecimal("180.00"));
        System.out.println("  before:          " + run);
        mutate(run);
        System.out.println("  after:           " + run);

        System.out.println("=== 2. REASSIGN ===");
        PaymentRun run2 = new PaymentRun("PR-9001", "PENDING_VERIFICATION");
        run2.addWithdrawal(new BigDecimal("180.00"));
        System.out.println("  before:          " + run2);
        reassign(run2);
        System.out.println("  after:           " + run2);

        System.out.println("=== 3. SWAP-ATTEMPT ===");
        PaymentRun cardRun = new PaymentRun("PR-CARD", "ACTIVE");
        PaymentRun bankRun = new PaymentRun("PR-BANK", "ACTIVE");
        System.out.println("  before:          first=" + cardRun.runId + " second=" + bankRun.runId);
        swapAttempt(cardRun, bankRun);
        System.out.println("  after:           first=" + cardRun.runId + " second=" + bankRun.runId);
        RunPair pair = swapped(cardRun, bankRun);
        cardRun = pair.first();
        bankRun = pair.second();
        System.out.println("  after swapped(): first=" + cardRun.runId + " second=" + bankRun.runId);
        PaymentRun[] slot = { cardRun, bankRun };
        swapInArray(slot);
        System.out.println("  after array:     first=" + slot[0].runId + " second=" + slot[1].runId);

        System.out.println("=== 4. STRING ===");
        String status = "AA-800 ACTIVATING";
        System.out.println("  before:          " + status);
        renameStatus(status);
        System.out.println("  after:           " + status);

        System.out.println("=== 5. BOXED PRIMITIVE ===");
        Integer reservationCount = 1200;
        System.out.println("  before:          " + reservationCount);
        bumpAttempt(reservationCount);
        System.out.println("  after:           " + reservationCount);

        System.out.println("=== 6. THE SHAPE THAT SHIPS ===");
        System.out.println("  split(3.33) = " + split(new BigDecimal("3.33")));
    }
}
```

Real output, `javac -g PassByValueHarness.java && java PassByValueHarness` on 21.0.7:

```console
=== 1. MUTATE ===
  before:          PaymentRun[PR-9001, status=PENDING_VERIFICATION, count=1, total=180.00]
  inside mutate:   PaymentRun[PR-9001, status=SUBMITTED, count=2, total=440.00]
  after:           PaymentRun[PR-9001, status=SUBMITTED, count=2, total=440.00]
=== 2. REASSIGN ===
  before:          PaymentRun[PR-9001, status=PENDING_VERIFICATION, count=1, total=180.00]
  inside reassign: PaymentRun[PR-9002, status=PENDING_VERIFICATION, count=1, total=999.99]
  after:           PaymentRun[PR-9001, status=PENDING_VERIFICATION, count=1, total=180.00]
=== 3. SWAP-ATTEMPT ===
  before:          first=PR-CARD second=PR-BANK
  inside swapAttempt: first=PR-BANK second=PR-CARD
  after:           first=PR-CARD second=PR-BANK
  after swapped(): first=PR-BANK second=PR-CARD
  after array:     first=PR-CARD second=PR-BANK
=== 4. STRING ===
  before:          AA-800 ACTIVATING
  inside renameStatus: AA-800 ACTIVATING / AA-801 ACTIVATED
  after:           AA-800 ACTIVATING
=== 5. BOXED PRIMITIVE ===
  before:          1200
  inside bumpAttempt:  1201
  after:           1200
=== 6. THE SHAPE THAT SHIPS ===
  split(3.33) = StakeSplit[bonusPortion=0.33, cashPortion=3.00]
```

### Reading the five cases against the printed lines

**Mutate.** `total` went 180.00 → 440.00 and `status` went `PENDING_VERIFICATION` →
`SUBMITTED`, and the caller's `after:` line is identical to the `inside mutate:` line. Both
slots named the same `PaymentRun`, so the withdrawal is visible to both. This is the case
people mean when they say "objects are passed by reference" — the observation is right, the
explanation is wrong, and the next case is why.

**Reassign.** Same parameter type, same call shape, opposite outcome. `inside reassign:`
prints `PR-9002` with a total of 999.99; the caller's `after:` prints `PR-9001` with 180.00,
byte-identical to its `before:`. Put them side by side and the rule resolves itself: mutate
changed the object, reassign changed the slot, and only the object is shared.

**Insight:** the pairing is the proof. If Java passed objects by reference, `reassign` would
have to be visible too — there is no coherent model in which the mutate case succeeds and the
reassign case fails *except* the copied-reference one.

### The bytecode: the parameter is a slot

`javap -c -p -l PassByValueHarness.class`, the `reassign` method:

```text
  static void reassign(PassByValueHarness$PaymentRun);
    Code:
       0: new           #15                 // class PassByValueHarness$PaymentRun
       3: dup
       4: ldc           #46                 // String PR-9002
       6: ldc           #48                 // String PENDING_VERIFICATION
       8: invokespecial #50                 // Method PassByValueHarness$PaymentRun."<init>":(Ljava/lang/String;Ljava/lang/String;)V
      11: astore_0
      12: aload_0
      13: new           #7                  // class java/math/BigDecimal
      16: dup
      17: ldc           #53                 // String 999.99
      19: invokespecial #11                 // Method java/math/BigDecimal."<init>":(Ljava/lang/String;)V
      22: invokevirtual #14                 // Method PassByValueHarness$PaymentRun.addWithdrawal:(Ljava/math/BigDecimal;)V
      25: getstatic     #25                 // Field java/lang/System.out:Ljava/io/PrintStream;
      28: aload_0
      29: invokestatic  #31                 // Method java/lang/String.valueOf:(Ljava/lang/Object;)Ljava/lang/String;
      32: invokedynamic #55,  0             // InvokeDynamic #1:makeConcatWithConstants:(Ljava/lang/String;)Ljava/lang/String;
      37: invokevirtual #41                 // Method java/io/PrintStream.println:(Ljava/lang/String;)V
      40: return
    LocalVariableTable:
      Start  Length  Slot  Name   Signature
          0      41     0   run   LPassByValueHarness$PaymentRun;
```

Instruction by instruction, the two that matter:

- **`11: astore_0`** — the freshly constructed `PR-9002` is stored into **local slot 0**.
- **`LocalVariableTable`: slot 0 is `run`**, live for the whole 41-byte method body.

Slot 0 *is* the parameter. `astore_0` overwrites it. That is the entire explanation of the
reassign case, and the local variable table is the receipt: a parameter is a local variable
that happened to be initialised by the caller, and nothing about it is special afterwards.

### Swap-attempt, and what actually works

`swapAttempt` prints `first=PR-BANK second=PR-CARD` inside and the caller still sees
`first=PR-CARD second=PR-BANK`. Both parameter slots were overwritten; neither caller
variable was touched. **No `swap(a, b)` can be written in Java for any type**, primitive or
reference — not because of immutability, but because the callee has no name for the caller's
slots.

Three shapes do work, and they cost different things:

| Form | How it works | Cost | Ship it? |
|---|---|---|---|
| Return a record of both — `swapped(first, second)` above | callee returns a `RunPair`; caller reassigns its own two variables | one small allocation, usually scalar-replaced; caller must remember to assign the result | **Yes** |
| Array of two — `swapInArray(slot)` | callee writes `slot[0]`/`slot[1]`; the array object is shared, so the writes are visible | an array allocation, no bounds/arity checking, no names on the two positions, and it silently ignores the return value | No |
| Mutable holder object | a field per position, same mechanism as the array with names | a class per pair shape, mutable state, and the holder escapes | No |

Note that the array line prints `first=PR-CARD second=PR-BANK` — that looks unswapped only
because the preceding `swapped()` call had already put `PR-BANK` first in `cardRun`, so the
array swap put them back. The mechanism worked; the printed values are the round trip.

**Ship the record.** An out-parameter is the wrong shape in Java for three reasons: the
caller cannot tell from the signature whether the callee writes the slot, the mutation is
invisible at the call site, and a `void` method that communicates through its arguments
cannot be composed, streamed or made a method reference of a useful shape. The domain already
has the right idiom — `StakeSplit(Money bonusPortion, Money cashPortion)` returns two values
from one operation with the invariant stated in the type, and the harness's `split(3.33)`
printing `StakeSplit[bonusPortion=0.33, cashPortion=3.00]` is the canonical rounding case
arriving as a value rather than through a slot.

### `String`: the case people misread

`renameStatus` prints `AA-800 ACTIVATING / AA-801 ACTIVATED` inside, and the caller still
prints `AA-800 ACTIVATING`. The universal reading of this is "`String` is immutable, so it
could not be changed" — and that reading is **wrong about which mechanism produced the
output**.

Compare the two lines directly. `reassign(PaymentRun)` mutates nothing and reassigns the
slot; `renameStatus(String)` mutates nothing and reassigns the slot. Both print an unchanged
caller value. `PaymentRun` is emphatically mutable, so immutability cannot be what produced
the `String` result — **reassignment of any reference behaves identically**, and the harness
runs both to prove it in one execution.

What immutability *does* add is narrower and sharper. There are exactly two things a callee
can do to a reference parameter: mutate the object, or reassign the slot. With a mutable type
both are available and only one is visible, so the caller must reason about which one a method
does. With `String` the mutate case **cannot exist** — there is no mutator to call. So
immutability removes one of the two cases; it does not change the calling convention. The
calling convention is identical for `String`, `PaymentRun`, `int` and `Integer`.

> Immutability does not make a parameter safe from the caller's point of view; it makes the
> mutate case unavailable, leaving only the reassign case, which was never visible anyway.

`../immutability-and-design/02-immutability.md` owns the design consequences of that.

### The boxed primitive: the same trap in a different disguise

`bumpAttempt(Integer)` prints 1201 inside and the caller still prints 1200. `Integer` is
immutable, so `reservationCount++` cannot be an in-place increment; it must unbox, add, and
box a **new** object into the parameter slot. `javap -c -p -l` on that method:

```text
  static void bumpAttempt(java.lang.Integer);
    Code:
       0: aload_0
       1: astore_1
       2: aload_0
       3: invokevirtual #74                 // Method java/lang/Integer.intValue:()I
       6: iconst_1
       7: iadd
       8: invokestatic  #80                 // Method java/lang/Integer.valueOf:(I)Ljava/lang/Integer;
      11: astore_0
      12: aload_1
      13: pop
      14: getstatic     #25                 // Field java/lang/System.out:Ljava/io/PrintStream;
      17: aload_0
      18: invokedynamic #83,  0             // InvokeDynamic #4:makeConcatWithConstants:(Ljava/lang/Integer;)Ljava/lang/String;
      23: invokevirtual #41                 // Method java/io/PrintStream.println:(Ljava/lang/String;)V
      26: return
    LocalVariableTable:
      Start  Length  Slot  Name   Signature
          0      27     0 reservationCount   Ljava/lang/Integer;
```

Read it: `0-1` stash the old reference in a scratch slot (that is postfix `++` preserving the
old value); `3` unboxes via `intValue`; `6-7` add 1; `8` re-boxes via `Integer.valueOf`;
**`11: astore_0`** writes the *new* box into the parameter slot — the same `astore_0` as the
reassign case; `12-13` load and discard the stashed old value, because a statement-expression
`++` throws its result away. Five instructions where a `int` field increment would be one, and
the caller sees none of it.

Note that 1200 is outside `IntegerCache`'s default `-128..127`, so both `Integer.valueOf`
calls here allocate. `../wrappers-and-boxing/03a-internals-cache-mechanics.md` owns the cache
and its bounds; `../primitives-and-conversions/03a-promotion-boxing-and-inference.md` owns
boxing and promotion as rules.

**Pitfall:** a method taking `Integer`, `Long`, `Double` or `AtomicInteger`-shaped-but-not-
atomic accumulator parameters and incrementing them is a silent no-op for the caller. The
symptom is a counter that stays at its initial value across a whole `PaymentRun`. The fix is
to return the new value, or to pass a genuinely mutable accumulator (`LongAdder`, an
`AtomicLong`, or a field on an aggregate) whose *mutation* — not whose slot — carries the
result.

**Interview:** "Is Java pass-by-value or pass-by-reference?" — "Pass-by-value always; for
reference types the copied value is the reference, so callees can mutate the object and cannot
rebind the caller's variable." Then offer the mutate/reassign pair unprompted; that is what
distinguishes a memorised answer from an understood one.

### Diff vs the real one

The "real one" here is the JVM's actual argument-passing implementation and the JDK's own
multi-value return idioms; the harness is a probe of them, not a reimplementation.

| Axis | This harness | The real mechanism / the real JDK |
|---|---|---|
| Edge cases | five cases, single-threaded, no `long`/`double` parameters | `long` and `double` occupy **two** consecutive local slots (JVMS §2.6.1), so slot numbering is not parameter numbering; the harness never shows that |
| Intrinsics | none; `Integer.valueOf` and `BigDecimal.add` run as ordinary calls | `Integer.valueOf` is `@IntrinsicCandidate`-adjacent through C2's autobox elimination; under the default JIT the `bumpAttempt` box is typically scalar-replaced away entirely, so the *allocation* the bytecode shows may not happen at runtime while the *visibility* result is unchanged |
| Serialization | `PaymentRun` is not `Serializable`; `RunPair` and `StakeSplit` are plain records | the JDK's own pair-like carriers (`Map.Entry`, `AbstractMap.SimpleEntry`) are `Serializable` and specify `equals`/`hashCode`; records get `equals`/`hashCode`/`toString` but **not** `Serializable` unless declared |
| Null policy | no argument is null-checked; `swapInArray(null)` would throw `NullPointerException` at `slot[0]` | JDK library methods that take an out-array (`System.arraycopy`, `Arrays.fill`) null-check and bounds-check explicitly and document the exception; a shipped version needs `Objects.requireNonNull` |
| Thread safety | none. `mutate` writes `withdrawals` and `status` with no synchronization | argument passing itself is thread-confined and always safe — the frame is per-thread. The **object** reached through the reference is not; a `PaymentRun` shared across a `paymentRunWorker` and an `operatorThread` needs the safe-publication rules in `../immutability-and-design/02-immutability.md` |
| Allocation tricks | one `RunPair`, one `PaymentRun[2]`, two `Integer` boxes, `BigDecimal` per withdrawal | escape analysis removes non-escaping `RunPair` and array allocations under C2, which is exactly why the record shape costs nothing in practice and why the array shape buys no performance to justify its ergonomics |
| Why the JDK bothers | it does not "bother" — there is no alternative implementation to choose | the JVM has no reference parameters *by design*: a copied-word convention makes frames independent, lets the verifier type-check slots locally (JVMS §4.10), and keeps GC root scanning per-frame. Out-parameters would make every frame a potential writer of every caller slot |

---

## Pitfalls

### Believing Java passes objects by reference

**Wrong**

```java
static void reassign(PaymentRun run) {
    run = new PaymentRun("PR-9002", "PENDING_VERIFICATION");
    run.addWithdrawal(new BigDecimal("999.99"));
}
// caller
PaymentRun run2 = new PaymentRun("PR-9001", "PENDING_VERIFICATION");
run2.addWithdrawal(new BigDecimal("180.00"));
reassign(run2);
System.out.println(run2);
```

Real output — the caller's variable is untouched:

```console
PaymentRun[PR-9001, status=PENDING_VERIFICATION, count=1, total=180.00]
```

**Right**

```java
static PaymentRun replaced() {
    PaymentRun fresh = new PaymentRun("PR-9002", "PENDING_VERIFICATION");
    fresh.addWithdrawal(new BigDecimal("999.99"));
    return fresh;
}
// caller
run2 = replaced();
```

Return the new object and let the caller rebind its own variable. The callee has no name for
that variable and never will.

**Why people believe it:** the mutate case really does show the callee changing something the
caller sees, and "pass by reference" is a plausible-sounding explanation for it. It is the
right observation with the wrong mechanism — the reference is passed *by value*.

### Believing `String` behaves specially at a call boundary

**Wrong**

```java
static void renameStatus(String status) {
    status = status.concat(" / AA-801 ACTIVATED");
}
// "String is immutable, so of course this does not change the caller."
```

The output is indeed `AA-800 ACTIVATING` unchanged — but the explanation is wrong, and the
proof is that a mutable type does exactly the same thing:

```console
=== 2. REASSIGN ===
  after:           PaymentRun[PR-9001, status=PENDING_VERIFICATION, count=1, total=180.00]
=== 4. STRING ===
  after:           AA-800 ACTIVATING
```

**Right**

```java
static String renamedStatus(String status) {
    return status.concat(" / AA-801 ACTIVATED");
}
// caller
status = renamedStatus(status);
```

The reason nothing propagated is reassignment of a reference, not immutability. Immutability's
actual contribution is narrower: it removes the *mutate* case, so a `String` parameter has
only one thing a callee can do to it instead of two.

**Why people believe it:** the two facts co-occur in every example anyone shows — `String` is
immutable *and* the reassignment is invisible — so the causal link is assumed. Running the
mutable-type reassign case in the same program breaks the correlation.

### Believing a `swap` can be written

**Wrong**

```java
static void swapAttempt(PaymentRun first, PaymentRun second) {
    PaymentRun scratch = first;
    first = second;
    second = scratch;
}
```

```console
  inside swapAttempt: first=PR-BANK second=PR-CARD
  after:           first=PR-CARD second=PR-BANK
```

**Right**

```java
record RunPair(PaymentRun first, PaymentRun second) {}

static RunPair swapped(PaymentRun first, PaymentRun second) {
    return new RunPair(second, first);
}
// caller
RunPair pair = swapped(cardRun, bankRun);
cardRun = pair.first();
bankRun = pair.second();
```

Return both and let the caller assign. An array of two or a mutable holder also works
mechanically, but the record states the shape in the type and is the one to ship.

**Why people believe it:** every introductory C, C++ or C# course teaches `swap` as *the*
motivating example for pointers, references or `ref`/`out`, so the reader arrives expecting
the idiom to exist and concludes the Java version has a typo.

---

## Cheat sheet

| Fact | Value |
|---|---|
| Java's calling convention | pass-by-value, always, for every type |
| What is copied for a reference type | the reference |
| Callee can | mutate the object |
| Callee cannot | rebind the caller's variable |
| Bytecode for reassigning a parameter | `astore_<n>` into the parameter's own local slot |
| `long`/`double` parameters | occupy two consecutive local slots |
| `swap(a, b)` in Java | impossible for any type |
| Multi-value return, the shape to ship | a record (`StakeSplit`, `RunPair`) |
| `Integer param++` | unbox, add, `Integer.valueOf`, `astore` — caller sees nothing |
| What immutability changes at a call | removes the mutate case; the convention is unchanged |

---

## Self-test

**Q1.** The harness's `mutate` and `reassign` take the same parameter type and are called the
same way, yet one change is visible to the caller and the other is not. State the single rule
that produces both results.

<details><summary>Answer</summary>

Java copies the argument's value into a fresh local slot in the callee. For a reference type
the copied value is the reference, so both slots name the same object. `mutate` calls a
mutator on that shared object, so the caller's view of the object changes. `reassign` stores a
different reference into its own slot — bytecode `astore_0` — which the caller's frame cannot
observe, so the caller still names the original object. One rule, two outcomes, depending on
whether the callee touched the object or the slot.

</details>

**Q2.** Someone argues that the `String` case in the harness proves `String` gets special
treatment at a call boundary. Refute it using only the harness's own output.

<details><summary>Answer</summary>

The `PaymentRun` reassign case prints the same "no change" result, and `PaymentRun` is
mutable. Since a mutable type produces the identical outcome under identical treatment,
immutability cannot be the cause. Both cases are reassignment of a parameter slot. What
immutability adds is that with `String` the *other* case — in-place mutation — cannot exist at
all, so a `String` parameter offers a callee one option instead of two. The calling convention
is the same for both types.

</details>

**Q3.** A `PaymentRun` reconciliation job counts settled withdrawals by passing an `Integer`
counter to a helper that increments it. The counter is always the initial value at the end.
Diagnose it from the bytecode.

<details><summary>Answer</summary>

`Integer` is immutable, so `param++` cannot be an in-place increment. The bytecode is
`aload_0` / `invokevirtual Integer.intValue` / `iconst_1` / `iadd` /
`invokestatic Integer.valueOf` / `astore_0`: the incremented value is boxed into a **new**
`Integer` which is then stored into the parameter's own local slot. `astore_0` writes the
callee's frame, so the caller's variable is unaffected — this is the reassign case wearing a
boxing costume. Fix by returning the new count, or by passing something whose *mutation*
carries the result: a `LongAdder`, an `AtomicLong`, or a counter field on the `PaymentRun`
aggregate.

</details>

**Q4.** The array-swap line in the harness output prints `first=PR-CARD second=PR-BANK`,
which looks unswapped. Explain the printed values, and say why you would still ship the record
rather than the array.

<details><summary>Answer</summary>

The array swap worked; the printed values are a round trip. The preceding `swapped()` call had
already left `cardRun` holding `PR-BANK` and `bankRun` holding `PR-CARD`, and the array was
built from those two variables in that order — so swapping its two slots put `PR-CARD` back in
position 0. The mechanism is sound because the array object is shared between caller and
callee, so writes through it are writes to one object, which is the mutate case, not the
reassign case. It is still the wrong shape to ship: the signature does not tell a caller that
the callee writes the slots, the mutation is invisible at the call site, the two positions have
no names, and there is no arity checking. `RunPair` states all of that in the type, and under
C2 the allocation is typically scalar-replaced away, so the record costs nothing the array
saves.

</details>

**Q5.** A colleague reads the `LocalVariableTable` in the `reassign` excerpt and concludes that
parameter number equals slot number, so the third parameter of any method is slot 2. Where does
that break?

<details><summary>Answer</summary>

Two places. First, only a `static` method starts its parameters at slot 0; an instance method
puts `this` in slot 0, so its first declared parameter is slot 1. Second, and less obviously,
`long` and `double` occupy **two** consecutive slots each (JVMS §2.6.1), so a signature taking
`(long, int)` puts the `int` in slot 2, not slot 1. Slot numbering is a layout of the frame, not
an index over the parameter list. The `reassign` excerpt happens to show the simple case — one
`static` method, one reference parameter, slot 0 — which is exactly why it is a bad basis for
the general rule.

</details>

---

## Open questions

- The claim that C2's escape analysis usually removes the `RunPair` and `PaymentRun[2]`
  allocations in this harness is stated from the general behaviour of scalar replacement, not
  measured here. **Unverified:** a `getThreadAllocatedBytes` delta over a large loop with and
  without `-XX:-DoEscapeAnalysis` would settle it; `../cost-model/02-master-cost-table.md` owns
  that harness.

---

**Leaves covered:** 4.8.7 (1 leaf)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 634
