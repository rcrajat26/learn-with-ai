# 03 Java Core — `strictfp`, `StrictMath` and `Math.fma` — INTERNALS (§3.15, 3.15.9–3.15.11)

**Target version: Java 21 LTS.** | **Part 3 of 5** | [Index](../00-index.md)
Previous: [Math.ulp, round-to-nearest-even and Double.toString](04a-internals-ulp-rounding-and-tostring.md) · Next: [Compensated summation, narrowing, and where floating point fits](04c-internals-summation-narrowing-and-fit.md)

This file owns the three places Java lets floating-point *reproducibility*
and *accuracy* diverge from the language's own default guarantees: the now
dead `strictfp` keyword, the `Math`-versus-`StrictMath` split, and
`Math.fma`'s single-rounding contract. `04c` closes the row with compensated
summation and the widening/narrowing rules. The question this file answers:
**when, if ever, can two conforming JVMs legitimately disagree on the bits of
a `double` computation, and what tool exists if that disagreement is
unacceptable?**

Measured on Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64 (Apple
Silicon), plus `javac`/`javap` bytecode inspection under `--release 21` and
`--release 16`.

---

## 1. `strictfp` is a no-op since Java 17 (3.15.9)

`strictfp` still compiles. It still means nothing. This is the single most
commonly asked fact in this file, and the JDK 21 bytecode evidence proves it
directly rather than by assertion.

### Why it exists

On 32-bit x86, the only floating-point hardware available for years was the
x87 unit, whose internal registers are 80 bits wide regardless of whether the
program asked for `float` or `double`. A JVM computing `a * b * c` was free to
keep every intermediate result at that 80-bit extended precision and produce
a *different* — often more accurate, but different — final answer than a
strict binary64 evaluation at every step would give. The original JLS
permitted exactly that for ordinary (non-`strictfp`) code, which meant the
identical program could produce different floating-point results depending
on which JVM and which CPU ran it. `strictfp` was the opt-in escape hatch:
apply it to a class or method and the JVM was required to round every
intermediate to binary32/binary64 at every step, guaranteeing the same
result everywhere. `javac` recorded that choice by emitting the `ACC_STRICT`
flag (bit `0x0800`) on the affected method or class in the compiled bytecode.

### How it works

**JEP 306, "Restore Always-Strict Floating-Point Semantics," shipped in Java
17.** By then SSE2 (and its equivalents on every other production JVM
platform) made strict binary32/binary64 evaluation the *free* default rather
than a costly opt-in, so the JLS was changed to make strict evaluation the
**only** evaluation mode for every platform — the wider-intermediate
allowance was removed entirely. `strictfp` became a keyword with nothing left
to opt into.

The evidence, verbatim from §6.9. Compiling this source under JDK 21.0.7 with
the default `--release 21`:

```java
public class Sfp {
  strictfp double strictSplit(double stake) { return stake * 0.10; }
  double plainSplit(double stake) { return stake * 0.10; }
  strictfp static class Inner { double f(double d){ return d*2; } }
}
```

`javac` emits a warning rather than silently accepting the keyword:

```
Sfp.java:2: warning: [strictfp] as of release 17, all floating-point expressions are evaluated strictly and 'strictfp' is not required
  strictfp double strictSplit(double stake) { return stake * 0.10; }
                  ^
```

And `javap -p -v` on the resulting `--release 21` class file shows **no
`ACC_STRICT` bit on either method** — the `strictfp` one and the plain one
are byte-for-byte identical in this respect:

```
  double strictSplit(double);
    descriptor: (D)D
    flags: (0x0000)

  double plainSplit(double);
    descriptor: (D)D
    flags: (0x0000)
```

Recompiling the *identical source* with `--release 16` instead — one target
release earlier than JEP 306's Java 17 — flips the flag back on for the
`strictfp` method only:

```
  strictfp double strictSplit(double);
    flags: (0x0800) ACC_STRICT

  double plainSplit(double);
    flags: (0x0000)
```

**The side-by-side is the proof.** Same source, same compiler, two `--release`
targets, and the emitted class file changes exactly at the JEP 306 boundary —
`0x0800` before Java 17's semantics apply, `0x0000` at and after. Nothing
about `strictfp`'s presence or absence in the source changes behavior once
targeting Java 17 or later; the bit simply stops being emitted.

Note that the flag value `0x0800` is not retired from the JVM specification —
it is simply that `javac` no longer emits it for this purpose in Java 17+
class files, since there is no longer strict-versus-non-strict semantics to
distinguish.

```java
public final class BonusMath {

    // strictfp buys nothing here on Java 17+ -- kept only because a reviewer
    // asked for it, which is exactly the cargo-cult scenario this concept warns about.
    strictfp static double legacyBonusPortion(double stake) {
        return stake * 0.10;
    }

    // Equivalent on Java 21: strict evaluation is now the only evaluation mode.
    static double bonusPortion(double stake) {
        return stake * 0.10;
    }
}
```

**Pitfall:** the wrong belief is that `strictfp` still buys reproducibility,
or conversely that *omitting* it on Java 21 risks platform-dependent
floating-point results. The symptom is code that carries the keyword as
cargo cult, a reviewer requesting it on a new method "to be safe," or a
`javac` build log full of the release-17 warning that nobody investigates.
The fix: delete it — on Java 17+ it changes nothing, and `javac` will now
actively warn about it.

**Interview:** the question is almost always phrased "what does `strictfp`
do" or "when would you use it," and the strong answer names JEP 306, Java 17,
the historical x87 80-bit intermediate problem, and the fact that `javac` no
longer emits `ACC_STRICT` for it on modern releases — with the honest caveat
that the keyword remains legal (for source compatibility with pre-17 code)
even though it has no effect.

Cross-reference:
[`../language-substrate/04-internals-version-history.md`](../language-substrate/04-internals-version-history.md)
for where JEP 306 sits in the version timeline, and
[`../language-substrate/03-internals-javac-and-class-file.md`](../language-substrate/03-internals-javac-and-class-file.md)
for the class-file flag format generally.

> `strictfp` forced binary32/binary64-only intermediates back when the JLS
> permitted wider x87 evaluation; since JEP 306 (Java 17) all floating-point
> evaluation is unconditionally strict, `javac` no longer emits `ACC_STRICT`
> for it, and the keyword is a legal no-op kept only for source compatibility.

## 2. `Math` versus `StrictMath` (3.15.10)

Two classes with nearly identical method signatures, one specified to be
*bit-for-bit reproducible everywhere* and one specified only to be *close
enough* — and the imprecise version of that distinction is the trap.

### Why it exists

Transcendental functions (`sin`, `pow`, `cbrt`, and friends) have no exact
closed-form binary64 result in general — computing them always involves an
approximation algorithm, and different algorithms (or the same algorithm run
on different hardware with different intrinsics) can legitimately produce
different last-bit results while both being "correct" within a documented
error bound. `StrictMath` and `Math` exist to let a caller choose which
guarantee they need: exact reproducibility, or speed with a bounded error.

### How it works

The specified difference, precisely: `StrictMath` is specified to produce the
**same result on every platform and every conforming implementation**,
defined by reference to the published `fdlibm` ("freely distributable
libm") reference algorithms. `Math` is specified only within a **documented
per-method error bound** — typically 1 or 2 ulp, with an accompanying
monotonicity requirement (if `x1 <= x2` then `f(x1) <= f(x2)` for
monotonic `f`) — and is explicitly permitted by its own Javadoc to delegate
to a platform-specific intrinsic instruction or library when one is
available. `Math` may therefore be *faster* and may even be *more accurate*
than `StrictMath` on a given platform; neither direction is guaranteed.

Measured, §6.6, with the caveat spelled out because it is the point:

```
Math.sin(1e10)            == StrictMath.sin(1e10)             -> both -0.4875060250875107
Math.pow(1.0000001, 1e7)  == StrictMath.pow(1.0000001, 1e7)   -> both 2.7182816941320818
Math.cbrt(0.1)            == StrictMath.cbrt(0.1)              -> true
```

**Do not conclude from this that `Math` and `StrictMath` always agree.**
The measurement shows only that, on this one build and platform, every value
tried happened to match. `Math` is *allowed* to differ from `StrictMath`;
`StrictMath` is not allowed to differ from `fdlibm`. Agreement on one JDK
21.0.7 macOS aarch64 run is not a portability guarantee, and a genuine
divergence on JDK 21 has not been demonstrated here — see `## Open
questions` rather than asserting one.

```java
final class WinProbabilityModel {

    // Math: fine for a live probability estimate feeding a UI -- speed and
    // "close enough within documented ulp bound" matter more than exact
    // cross-machine reproducibility here.
    double liveWinProbability(double impliedOdds) {
        return Math.pow(impliedOdds, -1.0);
    }

    // StrictMath: needed only when the SAME numeric result must be
    // reproducible across machines/JVMs later -- e.g. a persisted risk-model
    // coefficient that a downstream audit recomputes and diffs bit-for-bit.
    double auditableRiskCoefficient(double impliedOdds) {
        return StrictMath.pow(impliedOdds, -1.0);
    }
}
```

The decision rule: reach for `Math` for everything by default, and reach for
`StrictMath` only when bit-for-bit reproducibility across machines is an
actual requirement — a persisted value that a different process must
recompute identically later, a consensus or replication protocol comparing
independently computed values, or a regression test pinning an exact
transcendental result. Several `Math` methods (`abs`, `max`, `min`, `sqrt`,
`round`, and the `*Exact` overflow-checked family) are exactly specified in
the first place and are therefore entirely unaffected by this distinction —
there is nothing for `StrictMath` to do differently for them, and indeed
`StrictMath` largely just delegates to `Math` for those.

QuizStakes framing: no money computation ever touches a transcendental
function — the ledger only ever adds, subtracts and compares exact decimal
amounts. This distinction matters for an affordability score or a
statistical risk model, never for `FundsLedger`.

**Pitfall:** the wrong belief is that `Math` and `StrictMath` "always give the
same answer anyway, so it doesn't matter which you pick." The symptom is code
that reaches for `StrictMath` reflexively for "safety" and pays whatever
speed cost that carries with no actual reproducibility requirement to justify
it, or the opposite — code that assumes `Math` values are portable and is
surprised when a value computed on one JVM/platform differs by an ulp from
the same computation on another. The fix: name the actual requirement
(speed vs. cross-platform reproducibility) and pick accordingly, rather than
assuming either class's current measured behavior generalizes.

**Interview:** "what's the difference between `Math` and `StrictMath`" — the
strong one-line answer is `StrictMath` is specified to be bit-for-bit
identical everywhere via `fdlibm`; `Math` is specified only to a documented
ulp error bound and may use a faster platform intrinsic that can legitimately
differ.

> `StrictMath` guarantees the identical `fdlibm`-derived result on every
> platform; `Math` guarantees only a documented per-method error bound
> (typically 1-2 ulp) and may use a faster platform intrinsic that can
> legitimately produce a different, still-correct, result.

## 3. `Math.fma` (3.15.11)

Two ways to write `a*b + c` in Java compute genuinely different numbers, and
`Math.fma` is the one that rounds only once.

### Why it exists

Written as ordinary Java, `a * b + c` computes and rounds the multiplication
to a `double` first, then adds `c` and rounds *again* — two roundings, two
chances to lose precision, and the two losses can compound badly when the
multiplication result and `c` are close in magnitude but opposite in sign
(catastrophic cancellation). A hardware fused multiply-add instruction
computes the product at full internal precision and only rounds once, after
the addition — `Math.fma` exposes that as a portable Java API.

### How it works

`Math.fma(a, b, c)` computes `a*b + c` with the product held at **infinite
precision** internally and exactly **one** rounding applied to the final sum,
where the equivalent Java expression `a * b + c` rounds twice — once after
the multiply, once after the add. That single-rounding property is what
makes `fma` a genuinely distinct operation, not merely a fused convenience
method, and it maps directly to a hardware FMA instruction on aarch64 and on
x86 with the FMA3 instruction set extension.

The measured divergences, §6.6, are the proof it is not the same operation:

```
Math.fma(0.1, 7.0, 1.0)  = 1.7                  (one rounding)
0.1 * 7.0 + 1.0          = 1.7000000000000002   (two roundings)

Math.fma(0.1, 0.1, -0.01) = 9.020562075079397E-19
0.1 * 0.1 - 0.01          = 1.734723475976807E-18
```

The second pair is where `fma` earns its keep: the naive form is off by
nearly a factor of two from the fused form, because `0.1 * 0.1` (0.01,
approximately) and `-0.01` nearly cancel — catastrophic cancellation amplifies
whatever rounding error was already present in the intermediate product.
Holding that product at infinite precision until the single final rounding
avoids compounding the two separate errors.

Honestly, though: they also **agree** in many ordinary cases —
`Math.fma(0.1, 0.2, 0.0)` matched the naive `0.1 * 0.2 + 0.0` form exactly on
this build (§6.6). `fma` is not a blanket accuracy upgrade; it specifically
helps the cancellation-prone case.

```java
final class ExposureModel {

    // Naive: two roundings, fine when the terms aren't close in magnitude
    // and don't nearly cancel.
    double naiveExposure(double stakeFactor, double riskWeight, double baseline) {
        return stakeFactor * riskWeight + baseline;
    }

    // fma: one rounding, worth reaching for specifically when baseline is
    // close in magnitude to -(stakeFactor * riskWeight), i.e. cancellation
    // is likely -- dot products and Horner-method polynomial evaluation are
    // the classic cases.
    double fusedExposure(double stakeFactor, double riskWeight, double baseline) {
        return Math.fma(stakeFactor, riskWeight, baseline);
    }
}
```

Reach for `fma` in dot products, polynomial evaluation by Horner's method,
and any accumulation where cancellation between the product and the
accumulator is likely. Compensated summation (`04c`) solves a related but
distinct problem — error accumulated across *many* additions rather than
within a single fused multiply-add — by a different route entirely.

The honest QuizStakes verdict: for money, `Math.fma` is the wrong tool,
because the problem with `double` money is not that it rounds *too many
times* — it's that binary floating point cannot represent decimal fractions
like `3.33` exactly in the first place, no matter how carefully the rounding
is minimized. `BigDecimal` is the actual answer for money; that decision is
owned by
[`02c-mathcontext-constants-and-minor-units.md`](02c-mathcontext-constants-and-minor-units.md).

**Pitfall:** the wrong belief is that `Math.fma(a, b, c)` is always more
accurate than `a * b + c` and should be used as a general substitute. The
symptom is `fma` sprinkled through code with no cancellation risk, adding a
non-obvious call for zero measured benefit (as the `Math.fma(0.1, 0.2, 0.0)`
agreement above shows) or, worse, being reached for on a money computation
where the real fix is `BigDecimal`, not fewer roundings. The fix: use `fma`
specifically where a product and an addend are expected to nearly cancel or
where many fused terms accumulate (dot products, Horner's method); leave
ordinary arithmetic alone everywhere else, and never use it for money.

**Interview:** "what does `Math.fma` do differently from `a*b+c`" — it
computes the product at full precision and applies exactly one rounding to
the final result instead of two, which specifically helps when the product
and the addend are close in magnitude and nearly cancel.

> `Math.fma(a, b, c)` computes `a*b + c` with the multiplication held at
> infinite internal precision and a single final rounding, against two
> roundings for the plain Java expression — a difference that matters
> specifically under catastrophic cancellation, not universally.

---

## Pitfalls

### "`strictfp` still guarantees reproducible floating point on Java 21"

**Wrong**

```java
public strictfp double bonusPortion(double stake) {
    return stake * 0.10; // reviewer insists this keyword is load-bearing
}
```

On Java 21 this compiles to `flags: (0x0000)` — identical bytecode to the
same method without `strictfp` — because JEP 306 made strict evaluation the
only mode since Java 17.

**Right**

```java
public double bonusPortion(double stake) {
    return stake * 0.10; // strict by default since JEP 306 / Java 17
}
```

Deleting the keyword changes nothing behaviorally and removes the `javac`
warning it now triggers.

**Why people believe it:** `strictfp` was genuinely load-bearing for many
years, and folklore, older interview prep, and habit outlive the JEP that
made it obsolete.

### "`Math` and `StrictMath` always produce identical results"

**Wrong**

```java
double a = Math.sin(1e10);
double b = StrictMath.sin(1e10);
// assumed always equal, so code compares them with == and asserts on any diff
assert a == b;
```

The assertion happens to hold on this build (measured in §6.6), but nothing
in either class's specification guarantees it — `Math` is only bound to a
documented ulp error and may use a platform intrinsic.

**Right**

```java
// If bit-for-bit reproducibility across platforms is actually required,
// use StrictMath everywhere that value is computed or recomputed -- don't
// mix Math and StrictMath and expect them to agree.
double reproducibleResult = StrictMath.sin(1e10);
```

Pick one class per reproducibility requirement rather than assuming the two
interchangeably agree.

**Why people believe it:** on any single build and platform they usually do
agree in casual testing (as measured here), which looks like proof of a
guarantee that the specification never actually makes.

### "`Math.fma` is a drop-in accuracy improvement for any multiply-add"

**Wrong**

```java
double result = Math.fma(0.1, 0.2, 0.0); // "fma is always more accurate, use it everywhere"
```

Measured in §6.6, this matches the naive `0.1 * 0.2 + 0.0` exactly on this
build — no benefit realized, because there is no cancellation between the
product and the addend here.

**Right**

```java
// Reach for fma specifically where the product and the addend are close in
// magnitude and nearly cancel -- that's where the single rounding matters.
double result = Math.fma(0.1, 0.1, -0.01); // diverges meaningfully from the naive form
```

Reserve `fma` for dot products, Horner's-method polynomial evaluation, and
cancellation-prone accumulations, not as a universal replacement.

**Why people believe it:** the single-rounding property sounds strictly
better in the abstract, and it's easy to skip checking whether the specific
computation actually exercises the case where that matters.

---

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| `strictfp` on Java 21 | no-op; `javac` warns, no `ACC_STRICT` emitted |
| JEP that killed `strictfp`'s effect | JEP 306, "Restore Always-Strict Floating-Point Semantics" |
| Java version JEP 306 shipped in | 17 |
| `ACC_STRICT` flag bit | `0x0800` |
| `--release 21` `javap` flags on `strictfp` method | `(0x0000)` — same as plain method |
| `--release 16` `javap` flags on `strictfp` method | `(0x0800) ACC_STRICT` |
| Historical reason for `strictfp` | x87 80-bit intermediates on some pre-SSE2 x86 platforms |
| `StrictMath` guarantee | bit-for-bit identical everywhere, via `fdlibm` |
| `Math` guarantee | documented per-method error bound, typically 1-2 ulp |
| `Math` may use | a platform-specific intrinsic instruction |
| Methods unaffected by the split | `abs`, `max`, `min`, `sqrt`, `round`, `*Exact` family |
| Measured `Math.sin`/`pow`/`cbrt` vs `StrictMath` | agreed on every tried value, this build only |
| `Math.fma(a,b,c)` | `a*b+c` with one rounding, product at infinite internal precision |
| `a*b+c` in plain Java | two roundings (after multiply, after add) |
| `Math.fma(0.1, 7.0, 1.0)` | 1.7 |
| `0.1 * 7.0 + 1.0` | 1.7000000000000002 |
| `Math.fma(0.1, 0.1, -0.01)` | 9.020562075079397E-19 |
| `0.1 * 0.1 - 0.01` | 1.734723475976807E-18 (nearly 2x off) |
| `fma` hardware mapping | FMA instruction on aarch64, FMA3 on x86 |
| Where `fma` earns its keep | dot products, Horner's method, cancellation-prone sums |
| `fma` for money | wrong tool — use `BigDecimal`, see `02c` |

---

## Self-test

**Q1.** What did `strictfp` used to guarantee, and why does it no longer
matter on Java 21?

<details><summary>Answer</summary>

It forced the JVM to round every floating-point intermediate to strict
binary32/binary64 precision at each step, preventing the wider 80-bit x87
intermediates that non-strict code was historically permitted to use on some
x86 platforms — which could otherwise make the same program produce
different results on different hardware. JEP 306, shipped in Java 17, made
strict evaluation the only evaluation mode for all floating-point code, so
the keyword now has nothing left to opt into; `javac` warns about it and
emits identical bytecode with or without it.

</details>

**Q2.** What concrete bytecode evidence proves `strictfp` is a no-op on Java
21?

<details><summary>Answer</summary>

Compiling the identical source with `--release 21` versus `--release 16` and
inspecting with `javap -p -v`: at `--release 16`, a `strictfp`-annotated
method carries `flags: (0x0800) ACC_STRICT` in the class file; at
`--release 21`, the same method carries `flags: (0x0000)`, identical to a
plain non-`strictfp` method. `javac` also emits an explicit warning under
`--release 21` saying the keyword is not required as of release 17.

</details>

**Q3.** What is the actual specified difference between `Math` and
`StrictMath`?

<details><summary>Answer</summary>

`StrictMath` is specified to produce the identical result on every platform,
defined by the `fdlibm` reference algorithms. `Math` is specified only within
a documented per-method error bound, typically 1 or 2 ulp, with a
monotonicity requirement, and is explicitly permitted to use a
platform-specific intrinsic. `Math` may be faster and sometimes more accurate,
but neither is guaranteed relative to `StrictMath`, and agreement between the
two on one build is not a portability guarantee.

</details>

**Q4.** When would you actually reach for `StrictMath` instead of `Math`?

<details><summary>Answer</summary>

Only when bit-for-bit reproducibility of a transcendental computation across
different machines or JVMs is an actual requirement — for example a
persisted risk coefficient that a different process must later recompute and
diff exactly, or a cross-platform regression test pinning an exact value.
For everything else, `Math` is the default because it may be faster and its
error bound is already tight enough for most purposes.

</details>

**Q5.** What is the difference between `Math.fma(a, b, c)` and the plain Java
expression `a * b + c`?

<details><summary>Answer</summary>

`a * b + c` written in ordinary Java rounds twice: once when the
multiplication result is stored as a `double`, and again when `c` is added.
`Math.fma` computes the product at full internal precision and applies only
one final rounding to the sum. The difference is negligible in most cases —
measured, `Math.fma(0.1, 0.2, 0.0)` matched the naive form exactly — but
becomes significant specifically when the product and `c` are close in
magnitude and nearly cancel, where the naive form's two separate roundings
compound.

</details>

**Q6.** Why is `Math.fma` not the right fix for `double` money-precision
problems?

<details><summary>Answer</summary>

`Math.fma` reduces the *number of roundings* in a single multiply-add, but
the fundamental problem with using `double` for money is that binary
floating point cannot represent most decimal fractions (like `3.33`) exactly
in the first place — no amount of rounding-count optimization fixes a value
that was never representable to begin with. The actual fix is `BigDecimal`
(or minor-units `long`), which represents decimal fractions exactly by
construction.

</details>

---

## Open questions

1. No case has been measured on Oracle JDK 21.0.7 (this batch's build) where
   `Math` and `StrictMath` produce genuinely different results for the same
   input — every method and input tried in §6.6 agreed. A run of the same
   comparison across multiple JDK 21 platforms (e.g. an x86-64 Linux build
   against this macOS aarch64 build) for a wider set of transcendental
   methods and inputs would be needed to demonstrate an actual divergence, if
   one exists on JDK 21 specifically.

---

**Leaves covered:** 3.15.9–3.15.11 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 582
