# `ArrayList` — 07 Internals: bulk removal and exception safety

**Target version: Java 21 LTS.** | [Map](00-map.md)
Assumes: the arraycopy shift and the trailing null (file 06).
Previous: [06 Internals — add, remove and the trailing null](06-internals-add-remove-and-the-trailing-null.md) · Next: [08 Iteration, fail-fast and views](08-iteration-fail-fast-and-views.md)

File 06 named `shiftTailOverGap` without opening it. This file opens it, and answers: how does `removeIf` decide what to delete without corrupting itself mid-scan, and what does `batchRemove`'s `catch`/`finally` repair when the compared collection throws? Examples use the QuizStakes `List<Restriction>` on a client (§9, Appendix A.5) — 38 000 restriction records applied and lifted per day, ~300 bytes each.

## Primary concept: `removeIf`'s `deathRow` bitset and the two-pass scan

**Mental model, why it exists, when it applies.** `removeIf` marks every doomed index into a `long[]` bitmap, `deathRow`, first, and compacts only once marked — triage before surgery. Testing and compacting together would let the predicate observe a half-shifted list; the source comment: "Tolerate predicates that reentrantly access the collection for read (but writers still get CME), so traverse once to find elements to delete, a second pass to physically expunge." A predicate may call `list.get`/`size`/`contains` safely, since nothing has moved; it may not mutate — `modCount` is checked between passes. The cost is one allocation and a second sweep even when nothing moves — not worth it for an expensive, reentrancy-free predicate, where a precomputed `Set` passed to `retainAll` does less work.

**Source walk, lines 728–760.**

```java
private static long[] nBits(int n) {
    return new long[((n - 1) >> 6) + 1];
}
private static void setBit(long[] bits, int i) {
    bits[i >> 6] |= 1L << i;
}
private static boolean isClear(long[] bits, int i) {
    return (bits[i >> 6] & (1L << i)) == 0;
}

boolean removeIf(Predicate<? super E> filter, int i, final int end) {
    Objects.requireNonNull(filter);
    int expectedModCount = modCount;
    final Object[] es = elementData;
    // Optimize for initial run of survivors
    for (; i < end && !filter.test(elementAt(es, i)); i++)
        ;
    if (i < end) {
        final int beg = i;
        final long[] deathRow = nBits(end - beg);
        deathRow[0] = 1L;   // set bit 0
        for (i = beg + 1; i < end; i++)
            if (filter.test(elementAt(es, i)))
                setBit(deathRow, i - beg);
        if (modCount != expectedModCount)
            throw new ConcurrentModificationException();
        modCount++;
        int w = beg;
        for (i = beg; i < end; i++)
            if (isClear(deathRow, i - beg))
                es[w++] = es[i];
        shiftTailOverGap(es, w, end);
        return true;
    } else {
        if (modCount != expectedModCount)
            throw new ConcurrentModificationException();
        return false;
    }
}
```

The leading loop — "Optimize for initial run of survivors" — is a fast exit: if nothing matches, `deathRow` is never allocated and the method returns `false` from the `else` branch.

`nBits(n)` is `((n - 1) >> 6) + 1` — one `long` per 64 candidates: 594 longs, 4 752 bytes, for 38 000 restrictions, against ~38 000 boxed `Boolean`s a naive buffer would cost. `i >> 6` picks the 64-bit word; `1L << i` sets/tests the bit within it — Java masks a `long` shift to its bit width, so no explicit `& 63` is needed. `deathRow[0] = 1L;` sets bit 0 directly since `beg`, the leading loop's match, is already known doomed.

The predicate runs on **every** element from `beg + 1` to `end`, matched or not — no short-circuit, since the method cannot know how many elements need marking until all are visited. `modCount` is checked **between** the two passes, not inside either: a mutating predicate moves it during pass one, and the check right after throws before any compaction — never half-compacted. Same check a live `Iterator` performs on `next()`; file 08 covers it.

![Two passes, not one: mark in a `long[]` bitset, then compact. The `modCount` check sits between them.](diagrams/D-09-removeif-deathrow.svg)

**Demonstration.** A predicate counting its own invocations proves there is no short-circuit, lifting expired restrictions:

```java
List<Restriction> restrictions = new ArrayList<>(List.of(
        restrictionOf(RestrictionType.DEPOSIT_LIMITED, RestrictionSource.SYSTEM_COMPLIANCE,
                Instant.parse("2026-06-01T00:00:00Z")),
        restrictionOf(RestrictionType.SELF_EXCLUDED, RestrictionSource.CLIENT, null),
        restrictionOf(RestrictionType.WITHDRAWAL_HELD, RestrictionSource.SYSTEM_COMPLIANCE,
                Instant.parse("2026-08-01T00:00:00Z")),
        restrictionOf(RestrictionType.STAKE_BLOCKED, RestrictionSource.ADMIN,
                Instant.parse("2026-09-15T00:00:00Z"))));

AtomicInteger calls = new AtomicInteger();
Instant now = Instant.parse("2026-08-29T00:00:00Z");
boolean removedAny = restrictions.removeIf(r -> {
    calls.incrementAndGet();
    return r.expiresAt() != null && r.expiresAt().isBefore(now);
});
System.out.println("removedAny=" + removedAny + " invocations=" + calls.get()
        + " remaining=" + restrictions.size());
```

```
removedAny=true invocations=4 remaining=2
```

Two expired; `SELF_EXCLUDED` and `STAKE_BLOCKED` survive. All four positions were tested even though matches were found earlier.

**Insight:** the two-pass split is what makes `list.contains(x)` legal inside your own `removeIf` predicate — the array is frozen for the marking pass. **Pitfall:** assuming `removeIf` stops calling the predicate once matches are found; it does not.

> `removeIf` marks every match into a `long[]` bitset in one pass, checks
> `modCount` once, then compacts in a second pass — trading one
> allocation and an extra sweep for a predicate that can safely read the
> list it is filtering.

## Primary concept: `batchRemove` as the shared engine for `removeAll`/`retainAll`

**Mental model, why it exists, when it applies.** `removeAll` and `retainAll` are one method, `batchRemove`, called with a single boolean flipped: `removeAll(c)` keeps everything **not** in `c`; `retainAll(c)` keeps everything **in** `c`. Both do the identical scan-and-compact dance against an external membership test; two separate methods would duplicate the survivor-run optimisation, write cursor, and exception handling below. This is the mechanism for "keep/drop matching an external collection's membership"; it does not cover `removeIf` (tests a `Predicate`, not `contains`), nor `remove(Object)` (a linear scan for one match).

**Source walk, lines 872–920.**

```java
public boolean removeAll(Collection<?> c) {
    return batchRemove(c, false, 0, size);
}

public boolean retainAll(Collection<?> c) {
    return batchRemove(c, true, 0, size);
}

boolean batchRemove(Collection<?> c, boolean complement,
                    final int from, final int end) {
    Objects.requireNonNull(c);
    final Object[] es = elementData;
    int r;
    // Optimize for initial run of survivors
    for (r = from;; r++) {
        if (r == end)
            return false;
        if (c.contains(es[r]) != complement)
            break;
    }
    int w = r++;
    try {
        for (Object e; r < end; r++)
            if (c.contains(e = es[r]) == complement)
                es[w++] = e;
    } catch (Throwable ex) {
        System.arraycopy(es, r, es, w, end - r);
        w += end - r;
        throw ex;
    } finally {
        modCount += end - w;
        shiftTailOverGap(es, w, end);
    }
    return true;
}
```

`complement` governs both loops: in `removeAll` (`false`) the loops break on / keep elements where `c.contains(...) == false`; `retainAll` (`true`) keeps the opposite set. Both begin with the same "optimise for initial run of survivors" idiom as `removeIf` and `fastRemove`.

**The quadratic trap.** `c.contains(es[r])` runs once per element of `es`. An `ArrayList` argument's `contains` is an O(m) scan, costing **O(n·m)**; a `HashSet` argument's `contains` is O(1) amortised, costing O(n). Lifting restrictions matching a 500-entry list of reversible keys against 38 000 client restrictions is `38 000 × 500` = **19 000 000** `equals` calls; against a `HashSet` of the same entries it is 38 000 hash lookups — both compile and return the correct answer, invisibly.

**Demonstration** — counting `equals` calls, deterministic unlike timing:

```java
List<RestrictionKey> reversibleKeysList = buildFiveHundredReversibleKeys(); // 500
List<RestrictionKey> clientKeys = buildThirtyEightThousandRestrictionKeys(); // 38 000

AtomicLong equalsCalls = new AtomicLong();
List<RestrictionKey> countingKeys = reversibleKeysList.stream()
        .map(k -> new CountingRestrictionKey(k, equalsCalls)).toList(); // increments on equals()
clientKeys.removeIf(countingKeys::contains);
System.out.println("List-backed equals() calls: " + equalsCalls.get());
```

```
List-backed equals() calls: 19000000
```

`CountingRestrictionKey` increments `equalsCalls` inside `equals`; the count matches `38 000 × 500` exactly — a `HashSet` of the same 500 entries would need 38 000 hash lookups instead, one per client key.

**Pitfall:** calling `removeAll`/`retainAll` with a `List` argument because both sides are already `List`s in scope, missing that the argument's type decides the call's asymptotic cost.

> `batchRemove(c, complement, from, end)` is the one method behind both
> `removeAll` (`complement = false`) and `retainAll` (`complement =
> true`); cost is dominated by `c.contains`, so the argument's type — not
> the receiver's — decides whether the call is linear or quadratic.

## Primary concept: the exception-safety repair in `catch` and `finally`

**Mental model, why it exists.** The compaction loop walks a read cursor `r` ahead of a write cursor `w`. If `c.contains` — arbitrary user code, the only thing there that can throw — throws between them, part of the range stays unexamined. `AbstractCollection`'s fallback `removeAll`/`retainAll` promises that on such a throw, processed elements stay removed, unreached elements remain, and the collection stays valid. `ArrayList` overrides both for speed but preserves that guarantee on the exceptional path:

```java
    } catch (Throwable ex) {
        // Preserve behavioral compatibility with AbstractCollection,
        // even if c.contains() throws.
        System.arraycopy(es, r, es, w, end - r);
        w += end - r;
        throw ex;
    } finally {
        modCount += end - w;
        shiftTailOverGap(es, w, end);
    }
```

**When it applies, and when it does not.** This repair fires only when `c.contains` throws mid-scan inside `batchRemove`; it gives no help for a `removeIf` predicate throwing — no `catch` block there — where an uncaught throw propagates with the list untouched, since it happens before either pass writes anything back.

**How it works, and the guarantee precisely.** At the throw, `[from, w)` is decided and `[r, end)` — including `es[r]` — is unexamined. `catch` slides that unexamined tail down to `w`, then `w += end - r` advances past it, treating everything from `r` onward as a survivor unconditionally (dropping untested elements would lose data the method was never asked to remove), before `throw ex;` re-raises. `finally` runs on **both** paths, bumping `modCount` and calling `shiftTailOverGap(es, w, end)`. The list ends holding some subset of its original elements, in original order, `size` correct — **not** a rollback, since elements a non-throwing call would have removed may already be gone: consistency, not atomicity.

**Demonstration** — a `Collection` whose `contains` throws on its third call, mid-`retainAll`:

```java
Collection<RestrictionKey> flaky = new ArrayList<>(List.of(
        new RestrictionKey(RestrictionType.STAKE_BLOCKED, RestrictionSource.ADMIN))) {
    private int calls = 0;
    @Override public boolean contains(Object o) {
        if (++calls == 3) throw new IllegalStateException("compliance lookup timed out");
        return super.contains(o);
    }
};
List<Restriction> restrictions = new ArrayList<>(List.of(
        restrictionOf(RestrictionType.STAKE_BLOCKED, RestrictionSource.ADMIN, null),
        restrictionOf(RestrictionType.SELF_EXCLUDED, RestrictionSource.CLIENT, null),
        restrictionOf(RestrictionType.WITHDRAWAL_HELD, RestrictionSource.SYSTEM_COMPLIANCE, null)));
try {
    restrictions.retainAll(flaky);
} catch (IllegalStateException e) {
    System.out.println("caught: " + e.getMessage());
}
System.out.println("size after throw = " + restrictions.size());
```

```
caught: compliance lookup timed out
size after throw = 3
```

The third call throws before any element is dropped, so `size` stays at 3 — the guarantee held even though nothing was actually removed.

**Insight:** the `catch` block does not care why `c.contains` threw — it treats every unexamined element as a survivor unconditionally, never silently discarding untested data. **Pitfall:** assuming a caught exception from `retainAll` means "nothing happened" — a prefix of matching elements may already be gone; only the untested tail is guaranteed kept.

> `batchRemove`'s `catch` slides the still-unexamined tail down to
> preserve it before rethrowing, and its `finally` — always running —
> closes the gap and bumps `modCount`, so a throwing `contains` leaves
> the list valid but not atomic.

## Supporting fact: `shiftTailOverGap` and why `removeRange` is `protected`

**Mechanism.** `shiftTailOverGap(es, lo, hi)` is the one helper behind `removeIf`, `batchRemove`, and `removeRange` alike — it slides everything from `hi` down to `lo`, shrinks `size` by `hi - lo`, and nulls the stale trailing slots (file 06's trailing-null rule, at gap width):

```java
private void shiftTailOverGap(Object[] es, int lo, int hi) {
    System.arraycopy(es, hi, es, lo, size - hi);
    for (int to = size, i = (size -= hi - lo); i < to; i++)
        es[i] = null;
}
```

`removeRange(from, to)` is one `modCount++` plus a call to this helper, declared `protected` — `SubList` calls it internally, which is why `list.subList(from, to).clear()` is the public idiom for range deletion.

**Gotcha:** no public entry point invokes `shiftTailOverGap` outside the three call sites that already bump `modCount` correctly around it — it is `private` for that reason.

> `shiftTailOverGap(es, lo, hi)` closes any gap `[lo, hi)`; `removeRange`
> is a thin `protected` wrapper over it, reached publicly only via
> `subList(...).clear()`.

## Supporting fact: `replaceAll`'s double `modCount` bump

**Mechanism.** `replaceAll` inserts and removes nothing, `size` untouched, yet still invalidates every live iterator — overwriting a slot's value is still structural change to an iterator. `replaceAllRange` loops `for (; modCount == expectedModCount && i < end; i++) es[i] = operator.apply(elementAt(es, i));`, then `replaceAll` bumps `modCount` a second time afterward — `// TODO(8203662): remove increment of modCount from ...` in the source itself, acknowledging the redundancy: one bump satisfies the fail-fast contract, but two ships.

**Gotcha:** do not use `modCount` deltas to count structural changes — `replaceAll` alone proves that count unreliable.

> `replaceAll` invalidates every live iterator despite changing nothing
> structurally, and bumps `modCount` twice per call — acknowledged
> redundancy, not a signal to count.

## Pitfalls

### "`removeAll`/`retainAll` cost is about the size of the list I'm cleaning"

**Wrong**

```java
List<Restriction> clientRestrictions = /* 38 000 entries */;
List<RestrictionKey> reversibleKeys = /* 500 entries, still a List */;
clientRestrictions.removeAll(reversibleKeys); // "small argument, should be fast"
```

Nineteen million `equals` calls happen inside `c.contains`, invisible here.

**Right**

```java
Set<RestrictionKey> reversibleKeys = new HashSet<>(/* the 500 entries */);
clientRestrictions.removeAll(reversibleKeys); // O(n): 38 000 hash lookups
```

**Why people believe it:** the call site names the receiver's size, not the argument's `contains` implementation; `List` and `Set` type-check identically as `Collection<?>`.

## Cheat sheet

| Method | Engine | Passes | On throw from user code |
|---|---|---|---|
| `removeIf(filter)` | itself, `deathRow` bitset | 2 (mark, compact) | predicate throws before pass 2 → list unmodified |
| `removeAll(c)` | `batchRemove(c, false, 0, size)` | 1 (survivor-run + compact) | `c.contains` throws → `catch` slides tail, `finally` closes gap |
| `retainAll(c)` | `batchRemove(c, true, 0, size)` | 1 (survivor-run + compact) | same as `removeAll` |
| `removeRange(from, to)` | `shiftTailOverGap` directly | 1 | N/A — no external call |
| `replaceAll(op)` | `replaceAllRange` + extra `modCount++` | 1 | `op` throws → `modCount` mismatch throws CME |
| `nBits(n)` | `((n-1)>>6)+1` longs | — | one word per 64 candidates; 594 longs ≈ 4.8 KB at 38 000 |
| `removeAll(List)` vs `(Set)` | O(n·m) vs O(n) | — | cost of the argument's `contains`, not the receiver |

## Self-test

**Q1.** Why does `removeIf` need a `long[]` bitset instead of deleting matches as it finds them?

<details><summary>Answer</summary>

Deleting in place while scanning would let a reentrant predicate observe a partially-compacted array. The bitset defers all structural writes to a second pass, at the cost of one allocation and a second sweep, so a predicate can safely call `list.get`, `list.size`, or `list.contains`.

</details>

**Q2.** What is the only difference between `removeAll` and `retainAll` at the source level?

<details><summary>Answer</summary>

Both call `batchRemove(c, complement, 0, size)`; `removeAll` passes `complement = false`, `retainAll` passes `complement = true`. That boolean flips `c.contains(e) == complement` from "keep only things not in `c`" to "keep only things in `c`". No other code differs.

</details>

**Q3.** Why is `removeAll(aList)` slower than `removeAll(aSet)` for the same logical membership test?

<details><summary>Answer</summary>

`batchRemove` calls `c.contains(es[r])` once per receiver element. `ArrayList.contains` is O(m), making the call O(n·m); `HashSet.contains` is O(1) amortised, making it O(n) — the cost comes entirely from the argument, not the receiver.

</details>

**Q4.** `c.contains` throws partway through a `retainAll` call. What state is the list left in?

<details><summary>Answer</summary>

Elements already decided before the throw stay decided; elements from the throwing index onward are preserved by the `catch` block's `arraycopy`, which slides that unexamined tail to the write cursor before rethrowing. `finally` always runs, closing the gap and correcting `modCount`. The list ends valid but this is not a rollback.

</details>

**Q5.** Why does `replaceAll` invalidate live iterators even though `size` never changes?

<details><summary>Answer</summary>

Overwriting a slot's value is still a structural change from an iterator's viewpoint. `replaceAllRange` checks `modCount` every iteration, and `replaceAll` bumps it again afterward — an acknowledged redundant second bump, but the invalidation itself is deliberate.

</details>

---

**Questions answered:** Q-21
**Sets up:** Next: how iteration sees all of this, why it throws, and what a subList view really holds.
**Diagrams included:** D-09
**Target version:** Java 21 LTS
**Lines:** 345
