# 02 Java Collections — `LinkedHashMap` — INTERNALS (§4.6.3 The LFU sketch, part 2 — LRU vs LFU vs aging vs W-TinyLFU)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [linked-hash-map/03-build-lfu-sketch.md](03-build-lfu-sketch.md) · Next: [tree-map/01-navigable-api.md](../tree-map/01-navigable-api.md)

---

The LFU cache is built and its bookkeeping is proven. What remains is the leaf's actual purpose: to say what each policy *evicts*, what each one costs, and — the interesting part — how each one fails. Both implementations from the previous files are on hand, so the comparison does not have to be argued. It can be run: one short access sequence on capacity 3, two caches, two different victims, printed.

**Code on this page.** One labelled `java` block, one file: `PolicyDemo.java`. It depends on `LruCache.java` from [02-build-lru-by-hand.md](02-build-lru-by-hand.md) and `LfuCache.java` from [03-build-lfu-sketch.md](03-build-lfu-sketch.md), and is compiled together with them under `javac -Xlint:all`, zero warnings. Every printed line below is real output of `java PolicyDemo`; the section numbers continue from `LfuDemo`, which is why the output starts at `== 3.`.

**No diagram on this page.** The subject is four policies' failure modes, which is a table, not a shape.

---

## §4.6.3c The four policies, and how each one fails

| Policy | What it evicts | Structures | `get` | `put` | Memory/entry | Scan-resistant | Failure mode |
|---|---|---|---|---|---|---|---|
| **LRU** | the entry untouched longest | hash index + one doubly-linked list | O(1), 6 pointer writes | O(1) | 40 B (`LinkedHashMap`) / 64 B (hand-rolled) | **No** | One pass over a large cold key set evicts the entire hot working set. |
| **LFU** | the entry with the fewest hits, oldest-in-bucket first | 3 maps + `minFrequency` | O(1), but 3 map writes | O(1) | ~120 B (Option B) | Yes | **Cache pollution by history**: a key that was hot last week can never be overtaken, so the cache never adapts. |
| **LFU with aging** | as LFU, on decayed counts | LFU's structures + a decay mechanism | O(1) | O(1) amortised | ~120 B | Yes | The periodic halving pass is O(n) and stops the world; the decay period is a new tuning knob with no good default. |
| **W-TinyLFU** | recency inside the main region; frequency decides *admission* | count-min sketch (4-bit counters) + LRU window + segmented main region | O(1) | O(1) | sketch ~a few bits/tracked key + entry cost | Yes | Complexity. Its own paper's answer to "just use it" is a library, not a code snippet. |

The memory figures for LFU are arithmetic from the per-object sizes verified in [02a-build-lru-b-proof-and-cost.md](02a-build-lru-b-proof-and-cost.md), 64-bit HotSpot with compressed oops: `values` costs one `HashMap.Node` (32 B), `counts` costs another (32 B) plus a boxed `Integer` count (12-byte header + 4-byte `int` = 16 B, though `Integer.valueOf` caches −128…127, so counts in that range allocate nothing), and each `LinkedHashSet` membership costs a `LinkedHashMap.Entry` (40 B). That is roughly **120 bytes per entry against LRU's 40**, before the per-bucket `LinkedHashSet` and `HashMap` objects themselves. **Unverified:** these totals are derived from the verified per-object figures rather than measured with JOL on this machine; the individual object sizes are sound, the sum assumes one live `Integer` box per entry and no shared boxes.

### LRU's failure: one scan destroys everything

LRU's assumption is that recent means valuable. A batch job, a nightly report, a full table export, or a crawler walks a key space larger than the cache once, touching each key a single time. Every one of those touches is "recent", so every one of them evicts a member of the genuinely hot set, and by the end of the scan the cache holds only keys that will never be requested again. Hit rate goes to zero and stays there until the working set is faulted back in one miss at a time. LFU is immune: a key seen once never outranks a key seen a thousand times, so the scan is admitted and then evicted without displacing anything durable. This is the single strongest argument for caring about frequency at all.

### LFU's failure: it never forgets

LFU's counts are cumulative and unbounded, so they encode *all* history with equal weight, and yesterday's popularity outranks today's. Work the arithmetic: a key at count 10,000 and a newly hot key at count 1 are 9,999 hits apart, so the newcomer must be requested 9,999 more times *while surviving in the cache* before it can outrank the veteran — and it usually cannot survive, because it starts in bucket 1, which is exactly where the eviction victim comes from. The stale key is not merely favoured; it is unevictable, and it holds a slot forever.

```text
== 4. LFU's disease: cache pollution by history, capacity 2 ==
  OLD frequency after last week's traffic: 10001
  round 1: HOT1 freq=101 keys=[HOT1, OLD] min=101
  round 2: HOT2 freq=101 keys=[HOT2, OLD] min=101
  round 3: HOT3 freq=101 keys=[HOT3, OLD] min=101
  OLD is never evicted. A newcomer needs 10000 more hits to overtake it, and each newcomer starts over at 1.
```

Three successive keys each get 100 hits — genuinely hot, by any reasonable definition — and each is evicted in turn by the *next* newcomer while `OLD`, which has not been requested since the first phase, keeps its slot in a cache of capacity 2. Half the cache is permanently dead. Note also `min=101`: `minFrequency` tracks the newcomer's count, so the veteran at 10,001 is never even considered.

### Aging: halve everything, occasionally

The fix is to make counts decay so that "frequent" means "frequent *recently*". Two mechanisms are used in practice. **Periodic halving**: every *N* operations, replace every count with `count / 2`. Ratios are preserved, absolute distances shrink, and after enough halvings a stale count decays to a value a newcomer can reach — 10,000 needs 13 halvings to fall below 2. **Windowed decay**: keep counts per time window and sum only the last *k* windows, which is exact but multiplies the memory by *k*.

Halving costs an O(n) pass over every count, which for the Option B design also means rebuilding every bucket, since keys at counts 4 and 5 both land in bucket 2 and the bucket map's key set changes shape entirely. That pass is amortised O(1) per operation if *N* scales with the cache size, but it is a stop-the-world hiccup in a data structure whose whole selling point was constant-time operations — and the decay period becomes a tuning knob with no defensible default. This is where hand-rolled LFU stops being a reasonable thing to ship.

### W-TinyLFU: frequency to get in, recency to stay in

The production answer inverts the question. Instead of ranking cached entries by frequency, W-TinyLFU uses frequency as an **admission filter** in front of an otherwise recency-managed cache. Frequency estimates live in a count-min sketch with 4-bit saturating counters — a few bits per tracked key rather than a map entry, so it can track far more keys than the cache holds — and the whole sketch is halved whenever the sample counter reaches a threshold, which is aging made cheap because it touches a fixed-size array of counters rather than the entries themselves. New arrivals land in a small LRU *window* (roughly 1% of capacity); when the window overflows, the candidate's estimated frequency is compared with that of the main region's eviction victim, and the candidate is admitted only if it is estimated to be more frequent. So frequency decides *who gets in*, recency decides *who leaves*, the sketch bounds the memory cost of remembering history, and the periodic halving bounds how long history counts for. Scans are rejected at the door without displacing anything; stale veterans decay out of the sketch. Mechanism and Caffeine's API are in [01c1-internals-c2-memory-set-and-caffeine.md](01c1-internals-c2-memory-set-and-caffeine.md); the caching architecture is guide 15's subject. Do not hand-roll this one.

**Insight:** every policy on the table is an answer to "which signal predicts the next request?" — recency, frequency, decayed frequency, or both signals used for different decisions. W-TinyLFU wins not by having a better signal but by using each signal for the decision it is actually good at.

---

## §4.6.3d The head-to-head, on one sequence

### Mental model

Policy arguments are unfalsifiable in prose and trivial in code: find a sequence where the two policies must disagree, run both, print the victims. The sequence has to make one key *old but hot* and another *recent but cold*, because that is the exact case where recency and frequency point in opposite directions.

`put A, B, C` fills a capacity-3 cache. Then `get A` three times makes `A` the most frequent key at count 4 — and then `get B`, `get C` make `A` the *least recently used*, since both others have been touched since. Now `put D` forces one eviction, and the two policies cannot agree: LRU must evict `A` (untouched longest), while LFU must keep `A` (count 4) and evict from the tied count-2 bucket, taking `B` because it entered that bucket first.

### The code

```java
// PolicyDemo.java
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public final class PolicyDemo {

    public static void main(String[] args) {
        headToHead();
        pollutionByHistory();
    }

    private static void headToHead() {
        System.out.println();
        System.out.println("== 3. head to head, capacity 3, same access sequence ==");
        System.out.println("  put A,B,C; get A; get A; get A; get B; get C; put D  ->  who dies?");
        LruCache<String, Integer> lru = new LruCache<>(3);
        LfuCache<String, Integer> lfu = new LfuCache<>(3);
        List<String> lruEvictions = new ArrayList<>();
        List<String> lfuEvictions = new ArrayList<>();

        put(lru, lfu, "A", 1, lruEvictions, lfuEvictions);
        put(lru, lfu, "B", 2, lruEvictions, lfuEvictions);
        put(lru, lfu, "C", 3, lruEvictions, lfuEvictions);
        for (int i = 0; i < 3; i++) {
            lru.get("A");
            lfu.get("A");
        }
        lru.get("B");
        lfu.get("B");
        lru.get("C");
        lfu.get("C");
        put(lru, lfu, "D", 4, lruEvictions, lfuEvictions);

        System.out.println("  LRU: recency order " + lru.keys() + " evicted " + lruEvictions);
        System.out.println("  LFU: " + lfu + " evicted " + lfuEvictions);
        System.out.println("  LRU evicted A, the hottest key in the trace, because it was touched longest ago.");
        System.out.println("  LFU evicted B, the coldest tied key, and kept A.");
    }

    private static void put(LruCache<String, Integer> lru, LfuCache<String, Integer> lfu,
                            String key, int value, List<String> lruEvictions, List<String> lfuEvictions) {
        Set<String> beforeLru = new HashSet<>(lru.keys());
        Set<String> beforeLfu = lfu.keys();
        lru.put(key, value);
        lfu.put(key, value);
        beforeLru.removeAll(new HashSet<>(lru.keys()));
        beforeLfu.removeAll(lfu.keys());
        lruEvictions.addAll(sorted(beforeLru));
        lfuEvictions.addAll(sorted(beforeLfu));
    }

    private static void pollutionByHistory() {
        System.out.println();
        System.out.println("== 4. LFU's disease: cache pollution by history, capacity 2 ==");
        LfuCache<String, Integer> lfu = new LfuCache<>(2);
        lfu.put("OLD", 0);
        for (int i = 0; i < 10_000; i++) {
            lfu.get("OLD");
        }
        System.out.println("  OLD frequency after last week's traffic: " + lfu.frequency("OLD"));
        for (int round = 1; round <= 3; round++) {
            lfu.put("HOT" + round, round);
            for (int i = 0; i < 100; i++) {
                lfu.get("HOT" + round);
            }
            System.out.println("  round " + round + ": HOT" + round + " freq=" + lfu.frequency("HOT" + round)
                    + " keys=" + sorted(lfu.keys()) + " min=" + lfu.minFrequency());
        }
        System.out.println("  OLD is never evicted. A newcomer needs " + (lfu.frequency("OLD") - 1)
                + " more hits to overtake it, and each newcomer starts over at 1.");
    }

    private static List<String> sorted(Set<String> keys) {
        List<String> out = new ArrayList<>(keys);
        out.sort(null);
        return out;
    }
}
```

Neither cache is asked what it evicted — neither exposes an eviction listener, which is one of the reasons you would hand-roll a cache in the first place. The `put` helper instead diffs the key set across the call, which is the honest way to observe a policy from outside it.

### The transcript

```text
== 3. head to head, capacity 3, same access sequence ==
  put A,B,C; get A; get A; get A; get B; get C; put D  ->  who dies?
  LRU: recency order [B, C, D] evicted [A]
  LFU: LfuCache{f1=[D], f2=[C], f4=[A]} min=1 evicted [B]
  LRU evicted A, the hottest key in the trace, because it was touched longest ago.
  LFU evicted B, the coldest tied key, and kept A.
```

Same sequence, same capacity, different survivors — and every element of the disagreement is visible. LRU's remaining order is `[B, C, D]`, LRU-first, so `A` is simply gone. LFU's buckets show `A` sitting at count 4 untouchable, `C` at 2, and the newcomer `D` at 1 with `min=1` correctly pointing at it; `B`, also at count 2, lost the tie because it entered bucket 2 before `C` did.

Which one was *right* depends entirely on what comes next. If the next request is for `A`, LFU wins and LRU takes a miss on the trace's hottest key. If the workload has moved on and `A` is finished, LRU wins and LFU is holding a dead entry with an unbeatable score. Neither policy knows which world it is in, and that — not the code — is why the production answer combines both signals.

**Interview:** "LRU or LFU?" is a trap unless you name the failure modes. The answer is: LRU is scan-vulnerable, LFU pollutes with history and needs aging to be usable at all, and the production choice is W-TinyLFU — frequency for admission, recency for eviction — which is what Caffeine implements and why you would not write either of these yourself.

### Definition

> An eviction policy is a bet on which signal predicts the next request; LRU bets on recency, LFU bets on cumulative frequency, and both bets have a workload that breaks them.

---

## One supporting fact

**The demo observes evictions by diffing key sets, and that is a real API gap.** Neither `LruCache` nor `LfuCache` can tell a caller what it dropped, so nothing downstream can log evictions, decrement a counter, close a resource held by the value, or write back a dirty entry. An eviction listener is exactly the kind of policy hook `removeEldestEntry` cannot express well — it fires *before* removal and returns a boolean — and it is one of the two legitimate reasons to hand-roll one of these classes at all ([02a-build-lru-b-proof-and-cost.md](02a-build-lru-b-proof-and-cost.md)). Caffeine has both `evictionListener` and `removalListener`, and the distinction between them is the reason its API is bigger than this whole file.

---

## Pitfalls

### Choosing LFU because "frequency is smarter than recency"

**Wrong**

```java
// "our workload has a stable hot set, so LFU it is"
LfuCache<String, Row> cache = new LfuCache<>(10_000);
```

Ships an unbounded-count LFU with no aging. Six weeks later a handful of keys hold five-figure counts, the working set has moved, and the cache's hit rate is a fraction of what a plain LRU would give — with no metric that points at the cause, because every count in the cache looks like evidence that the entry is popular.

**Right**

```java
// LinkedHashMap: correct, 40 B/entry, ten lines, and its failure mode is one sentence
Map<String, Row> cache = new LinkedHashMap<>(16, 0.75f, true) {
    @Override
    protected boolean removeEldestEntry(Map.Entry<String, Row> eldest) {
        return size() > 10_000;
    }
};
```

Or, if the workload genuinely has both a stable hot set and scans, use Caffeine and get W-TinyLFU, which handles both. Plain LFU without aging is a defensible teaching exercise and rarely a defensible production choice.

**Why people believe it:** LFU *is* strictly better than LRU on the scan workload, which is the example everyone is shown first. The failure mode runs on a timescale of weeks, so it never appears in a benchmark.

### Reading the head-to-head as "LFU wins"

**Wrong**

```java
// LFU kept A, the hottest key, so LFU is the better policy
```

**Right**

The transcript shows the two policies *disagreeing*, not one of them being correct. The sequence was constructed to force disagreement, and which survivor was the right one is determined by the requests that come after the trace ends — information neither policy has. Quote the disagreement; do not quote a winner.

**Why people believe it:** the demo's own commentary calls `A` "the hottest key in the trace", which is true of the past and says nothing about the future. Every eviction policy is a prediction, and traces only contain history.

---

## Cheat sheet

| Policy | Evicts | Fails when |
|---|---|---|
| LRU | untouched longest | a scan larger than the cache walks past once |
| LFU | fewest hits, oldest-in-bucket first | history accumulates and the working set moves |
| LFU + aging | fewest *decayed* hits | the O(n) halving pass and its untunable period |
| W-TinyLFU | recency in main, frequency at admission | never, materially — just use the library |

| Item | Value |
|---|---|
| LRU scan damage | whole hot set displaced by keys never requested again |
| LFU pollution arithmetic | count 10,000 vs count 1 → 9,999 hits needed, starting from the eviction bucket |
| Halvings to decay 10,000 below 2 | 13 |
| Aging cost (Option B) | O(n) over counts *and* a full rebuild of the bucket map |
| W-TinyLFU sketch | count-min, 4-bit saturating counters, halved on a sample threshold |
| W-TinyLFU split | frequency decides admission, recency decides eviction |
| Window size | ~1% of capacity, LRU |
| Memory: LRU / LFU (Option B) | 40 B (`LinkedHashMap`) / ~120 B per entry |
| Head-to-head sequence | `put A,B,C; get A ×3; get B; get C; put D` |
| Victims | LRU evicts `A`; LFU evicts `B` |
| Eviction listener | neither class has one — a real reason to hand-roll, and what Caffeine gives you |
| Production answer | Caffeine (W-TinyLFU) |

---

## Self-test

**Q1.** Describe the workload that breaks LRU, and why LFU is immune to it.

<details><summary>Answer</summary>

A single pass over a key space larger than the cache — a batch job, export, or crawler — touching each key once. Every touch is "recent", so each one evicts a member of the hot working set, and at the end the cache holds only keys that will never be requested again; the hit rate collapses until the working set faults back in one miss at a time. LFU is immune because a key seen once cannot outrank a key seen many times, so the scan's keys are admitted at count 1 and evicted at count 1 without displacing anything durable.

</details>

**Q2.** Work the arithmetic of LFU's pollution failure.

<details><summary>Answer</summary>

A veteran key at count 10,000 and a newly hot key at count 1 are 9,999 hits apart, so the newcomer must be requested 9,999 more times *while remaining cached* to overtake it — and it starts in bucket 1, which is exactly where the eviction victim is drawn from, so it is usually evicted first. The demo shows three successive keys receiving 100 hits each, all evicted in turn, while a key untouched since the first phase keeps half of a capacity-2 cache forever.

</details>

**Q3.** How does aging fix that, and what does it cost?

<details><summary>Answer</summary>

Periodic halving: every *N* operations, replace each count with `count / 2`. Ratios survive, absolute distances shrink, and a stale 10,000 falls below 2 after 13 halvings, so "frequent" comes to mean "frequent recently". The cost is an O(n) pass over every count — which in the bucket-map design also rebuilds the entire bucket map, since halved counts collide — plus a new tuning knob, the decay period, with no defensible default. Amortised O(1) per operation, but a stop-the-world hiccup in a structure sold on constant-time operations.

</details>

**Q4.** In one sentence, what is W-TinyLFU's structural insight?

<details><summary>Answer</summary>

Use each signal for the decision it is good at: frequency, estimated cheaply in a periodically-halved count-min sketch, decides *admission* through a small LRU window, and recency decides *eviction* inside the main region — so scans are rejected at the door and stale history decays out of the sketch rather than being stored per entry.

</details>

**Q5.** Construct the head-to-head sequence from first principles and give both victims.

<details><summary>Answer</summary>

You need one key that is old but hot and another that is recent but cold. `put A, B, C` at capacity 3; `get A` three times (A reaches count 4); `get B`, `get C` (A is now the least recently used, since both others were touched after it). `put D` then forces one eviction: LRU evicts `A`, the key untouched longest and the trace's hottest; LFU keeps `A` at count 4 and evicts from the tied count-2 bucket, taking `B` because it entered that bucket before `C`.

</details>

**Q6.** Why does the demo diff key sets instead of reading an eviction log?

<details><summary>Answer</summary>

Because neither class has one. Without an eviction listener nothing downstream can log a drop, decrement a metric, close a resource, or write back a dirty entry — and `removeEldestEntry` is a poor substitute since it fires before removal and returns a boolean. That API gap is one of the two legitimate reasons to hand-roll a cache instead of using `LinkedHashMap`, and it is why Caffeine exposes both `evictionListener` and `removalListener`.

</details>

**Q7.** Roughly what does an Option-B LFU entry cost against a `LinkedHashMap` LRU entry, and where does the difference go?

<details><summary>Answer</summary>

About 120 bytes against 40, on 64-bit HotSpot with compressed oops. The LFU entry pays a `HashMap.Node` in `values` (32 B), a second `HashMap.Node` in `counts` (32 B), a boxed `Integer` count (16 B, though `Integer.valueOf` caches −128…127 so low counts allocate nothing), and a `LinkedHashMap.Entry` for its `LinkedHashSet` bucket membership (40 B) — plus the per-bucket `LinkedHashSet` objects themselves. The list-of-lists design removes the boxed count and the per-bucket hash table, which is most of the gap.

</details>

---

## Open questions

- **The ~120 B/entry figure for the Option-B LFU** is arithmetic over verified per-object sizes (`HashMap.Node` 32 B, `LinkedHashMap.Entry` 40 B, `Integer` 16 B, compressed oops), not a JOL measurement on this machine. The individual sizes are sound; the sum assumes exactly one live `Integer` box per entry (false for counts in −128…127, which come from the autobox cache) and excludes the per-bucket `LinkedHashSet` and its table array. Treat it as an order-of-magnitude comparison against LRU's 40 B, not a number to quote. A JOL `GraphLayout` run on a populated `LfuCache` would settle it.

---

**Leaves covered:** 4.6.3 (part 2 of 2, continued from 03) (1 leaf)
**Leaves deferred:** none
**Diagrams included:** none new — the map-plus-linked-list structure (D-148) is embedded in [02-build-lru-by-hand.md](02-build-lru-by-hand.md)
**Target version:** Java 21 LTS
**Lines:** 325
