# Illustrator packet ill-19 — topic 04 Modern Java

You are authoring **4 standalone SVG diagram files** for a study-note set on Modern Java
(Java 8 → 21). This packet is your complete brief. You need nothing else, with one exception:
`/Users/rajat.chikkodikar/Desktop/My-files/rough/src/scenario/scenario.md` is read-only shared domain reference you may open for detail
beyond what is pasted below.

## What to write, and where

Write each file into:

```
/Users/rajat.chikkodikar/Desktop/My-files/rough/src/notes/detailed/04-modern-java/diagrams/
```

Filenames are given per diagram below. Create nothing else. Do not touch any `.md` file. Do not
touch `00-index.md`.

## Your assignment

### D-101 — `parallelStream().forEach(list::add)` corrupts the list

- **Target filename:** `D-101-parallelstream-foreach-list-add.svg`
- **Type:** step-sequence, 3 frames
- **Syllabus leaf:** 2.4.11
- **Must show (this is the contract — every named label, constant and value must be visible as text in the SVG):** Two carrier threads adding to one `ArrayList` of ledger entries. Frame 1: both read `size` as 40. Frame 2: both write to index 40 — one entry lost. Frame 3: a grow racing with a write producing `ArrayIndexOutOfBoundsException` from inside `ArrayList.add`, plus the interspersed-null case. All three symptoms named

### D-102 — Where parallel starts paying

- **Target filename:** `D-102-parallel-starts-paying.svg`
- **Type:** cost-curve
- **Syllabus leaf:** 2.4.6, 2.4.7
- **Must show (this is the contract — every named label, constant and value must be visible as text in the SVG):** Sequential and parallel curves over N with the split/merge overhead as a constant band; the crossover marked near the N×Q ≈ 10,000 heuristic; three QuizStakes points plotted — 40 deposits/sec (never worth it), 95k deposits/day (marginal), 2.8M reservations/day with expensive per-element work (worth it)

### D-103 — `filtering(p, toList())` versus `filter(p)` before `groupingBy`

- **Target filename:** `D-103-filtering-p-tolist-versus.svg`
- **Type:** before-after
- **Syllabus leaf:** 2.5.3
- **Must show (this is the contract — every named label, constant and value must be visible as text in the SVG):** Grouping card deposits by rail where one rail has no deposit above 100. Left, `filter` before `groupingBy`: that rail's key is absent from the map entirely. Right, `filtering` as a downstream: the key is present with an empty list. Both result maps drawn key by key

### D-104 — A top-N collector's combiner

- **Target filename:** `D-104-top-n-collector-s.svg`
- **Type:** step-sequence, 3 frames
- **Syllabus leaf:** 2.5.8, 4.3.3
- **Must show (this is the contract — every named label, constant and value must be visible as text in the SVG):** Top-3 withdrawals by amount over two parallel leaves. Frame 1: each leaf maintains a bounded `PriorityQueue` of size 3, contents shown. Frame 2: the combiner merges the two heaps and re-bounds to 3 — the discarded elements marked. Frame 3: the finisher sorts descending. Actual withdrawal amounts (180, 260, 92) used


## Target version context

The notes target **Java 21 LTS**. Where a diagram carries a version banner or a version pill, it
is a Java release number. Three figures were re-verified from primary source and must be drawn as
stated here, not as older material states them:

- The virtual-thread scheduler's `maxPoolSize` default is `Integer.max(parallelism, 256)` — 256 is
  a **floor**, not a flat default. Parallelism defaults to `availableProcessors()`. `minRunnable`
  defaults to `max(parallelism / 2, 1)`. The scheduler is a `ForkJoinPool` created with
  `asyncMode = true`, which the JDK source comments `// FIFO`.
- `LEAF_TARGET = ForkJoinPool.getCommonPoolParallelism() << 2`, and
  `suggestTargetSize(sizeEstimate) = sizeEstimate / getLeafTarget()` as **floored integer
  division clamped to a minimum of 1** — *not* rounded up. `getLeafTarget()` uses the current
  pool's parallelism when the caller is a ForkJoin worker.
- `ForkJoinPool.commonPool()` parallelism is `availableProcessors() - 1`, **and** the submitting
  thread participates, so the effective width equals the core count. Where a diagram shows the
  common pool, label both halves.
- `synchronized` pins a virtual thread on Java 21; JEP 491 removes that cause in Java 24; native
  and foreign frames still pin, so the `jdk.VirtualThreadPinned` JFR event survives.

---

## Diagram spec

Every diagram is **one standalone `.svg` file** in the topic-root `diagrams/` folder, named
`D-NNN-short-slug.svg`, embedded from the Markdown at the point of explanation:

```
![HashMap treeifying a bucket at 9 nodes](../diagrams/D-07-hashmap-treeify.svg)
```

- Do **not** paste inline `<svg>` into Markdown — GitHub strips it and VS Code's
  preview sanitizes it away, so the reader gets a blank gap where the picture
  should be. An embedded file renders in both and sits in the same place in the
  prose.
- **Never ASCII art**, under any circumstance. See *When a manifest diagram does
  not work* below for the one legitimate escape.
- The SVG must show everything its manifest row's **must-show** column names —
  every labelled constant, every value, every arrow. A diagram that omits a
  must-show element is not done.
- Prefer several small single-idea diagrams over one dense one. Where the
  manifest calls for a frame series, author each frame as its own file
  (`D-07a-…`, `D-07b-…`) and report all ids in your envelope.
- The file is the single canonical home for that `D-NN`. If two note files need
  the same picture, both embed the same path — never a copy.
- **Labels name the QuizStakes domain**, not throwaways. A node is
  `LedgerEntry`, `DEP-301 CAPTURED`, `PaymentRun`, or `ClientRestrictions` —
  never `Foo`, `Object A`, or `thread1`. Take the spelling from
  `src/scenario/scenario.md` and the figures from its Appendix A.

### Canvas

- `viewBox` always. **No `width` or `height` attributes** — the diagram must
  scale to the reader's column.
- Size the canvas to the content, then stop. Working starting points:
  `0 0 1040 900` layered hierarchies, `0 0 1120 800` two-family side-by-side
  comparisons, `0 0 900 400` linear flows and timelines, `0 0 640 640` square
  structures such as trees and grids. Widen before you shrink text.
- Nothing may touch the `viewBox` edge; keep a **20-unit margin** on all sides.
- **First element is an opaque backdrop** covering the whole viewBox:
  `<rect x="0" y="0" width="W" height="H" fill="#ffffff"/>`. This is what makes
  the diagram legible in GitHub dark mode, in `#1e1e1e` VS Code, and in a PDF
  export — the page background is never part of the contrast calculation, so
  labels no longer need an individual rect behind them.

### Layout — this is what separates a clean diagram from a messy one

Fills and fonts are not the problem. Routing and alignment are. In order of
importance:

1. **Layer it.** Every node of the same generation shares one y band. A child is
   never level with its parent, and never above it.
2. **Orthogonal routing only.** Every edge is horizontal and vertical segments
   with square elbows: `d="M 420 273 V 290 H 168 V 306"`. **No diagonals, no
   `C`/`Q` Béziers, no `<line>` between two arbitrary points.** Diagonal
   spaghetti is the single largest source of mess.
3. **Fan out on a bus.** One parent with three or more children draws one
   vertical stub down to a shared horizontal bus, then one vertical drop per
   child. Not three separate diagonals from the parent's edge.
4. **Give each edge its own exit x.** Two edges leaving the same parent leave at
   different x offsets so their elbows never overlay.
5. **Route through corridors.** An edge that must pass a column reserves a clear
   x lane between boxes (a "corridor") and turns only inside it.
6. **Target zero line crossings.** If one is genuinely unavoidable, keep it to
   one and say so in your envelope's `unverified` line.
7. **Put the relationship that matters on a straight centre spine.** If the
   reader's question is "is A really a subtype of Z", place `Z → … → A` on one
   unbroken vertical and let the siblings go left and right. Reinforce it with a
   short sub-label in the node (`is-a Collection ↑`) and, if it is the point of
   the whole diagram, an annotation panel.
8. **No per-edge text labels.** Never label thirty arrows `extends`. Encode the
   relation in the line style and explain it once in the legend. Edge text is
   reserved for the rare edge whose meaning the legend cannot carry (a method
   name on an adapter, a threshold on a transition).

### Required furniture

Every diagram has, in this order:

- **Title**, top-left, `.h1`, followed by a full-width hairline rule in
  `#d1d5db`. Not centred, not in a filled banner bar.
- **Section band headers** in `.h2` where the diagram holds two families or
  lanes (`COLLECTION SIDE — root: Iterable`). Two unlabelled halves read as one
  confusing whole.
- **Legend**, bottom, under a second hairline rule: one swatch per box style used
  and one line sample per edge style used, each with a short gloss. Every style
  the diagram uses appears; no style appears that it does not use.

### Palette — use these values, do not improvise

Fill and stroke are a matched pair. Take both from the same row.

| Role | Fill | Stroke | Use for |
|---|---|---|---|
| Primary / interface | `#dbeafe` | `#2563eb` | the subject type, the main node |
| Highlight / new-in-version | `#fef3c7` | `#b45309` | the thing the diagram is about, version-new API |
| Resolved / concrete | `#dcfce7` | `#15803d` | concrete classes, success path, fast path |
| Legacy / deprecated | `#f5f5f4` | `#78716c` | retained-for-compatibility types |
| Weak / nested / inferred | `#f3f4f6` | `#9ca3af` | nested types, dashed boxes, secondary detail |
| Degraded / failure | `#fee2e2` | `#b91c1c` | collision, contention, thrown exception |
| Annotation panel | `#eff6ff` | `#2563eb` | callouts and note boxes |
| Version pill | `#fbbf24` | `#b45309` | small `rx`-rounded badge, e.g. `21` |

| Role | Value |
|---|---|
| Text | `#1f2937` |
| Secondary text | `#4b5563` |
| Structural edges (inheritance, flow) | `#475569` |
| Hairline rules and dividers | `#d1d5db` |
| Backdrop | `#ffffff` (backdrop rect only — never a text fill) |

No gradients, no opacity below 1 on fills, no drop shadows, no colour outside
these tables.

### Line semantics

One meaning per style, declared in the legend, consistent across every diagram in
the topic:

| Relation | Style | Stroke |
|---|---|---|
| extends / primary flow | solid, `stroke-width="2"`, filled arrowhead | `#475569` |
| implements / nested type of | dashed `6 4`, arrowhead | `#15803d` |
| adapter or bridge, **not** inheritance | dotted `3 3`, arrowhead | `#b45309` |
| weak, optional, or inferred link | dotted `4 3`, arrowhead | `#9ca3af` |
| class-to-class inheritance among legacy types | solid `1.8` | `#78716c` |

Arrowheads point **at the child / at the target**, and the legend spells the
direction out (`A → B : B extends A`) so it cannot be read backwards. One
`<marker>` per stroke colour in `<defs>`.

### Typography and the style block

- One `<style>` element at the top of the file holding class selectors, then
  class attributes on the shapes. This keeps the file short enough to review and
  makes the palette impossible to drift within one diagram. **Plain class
  selectors only** — no `@import`, no `@font-face`, no attribute selectors, no
  media queries, nothing that reaches off-file.
- Font stack: `-apple-system, "Segoe UI", Helvetica, Arial, sans-serif`.
- 15px node titles, 13px node body, 12.5px dense node body, 11px legend and
  annotation rows, **10.5px absolute floor** for sub-labels.
- `stroke-width="2"` minimum on any line that carries meaning; `1.3`–`1.6` is for
  box borders and hairlines only.

### Text must fit its box — do the arithmetic

An overflowing label is the most common defect and it is fully preventable.
Estimate rendered width as **characters × 0.55 × font-size** (× 0.6 for bold),
and keep **≥ 12 units of clearance** inside the box on each side. If it does not
fit: widen the box, or restructure — never shrink below the floor and never let
it spill.

**Leaf sets go in one grouped panel, not N tiny boxes.** Three sibling leaves
each carrying a method signature will not fit in three 130-wide boxes. Draw one
panel, one arrow into it, a bold header row, and one left-aligned row per leaf:

```
PrimitiveIterator nested specializations
OfInt · nextInt() · forEachRemaining(IntConsumer)
OfLong · nextLong() · forEachRemaining(LongConsumer)
```

**Annotation panels carry the prose.** Facts that are neither node nor edge — the
fail-fast rule, a characteristics bitmask, the reason the spine matters — go in an
`#eff6ff` panel with a bold header and 11px rows, placed in otherwise empty
canvas. They are not a dumping ground: two panels per diagram is the ceiling.

### Skeleton

```svg
<svg viewBox="0 0 900 320" xmlns="http://www.w3.org/2000/svg" role="img"
     aria-label="ArrayList growth: an eleventh add to a capacity-10 elementData
     calls grow(), which allocates a capacity-15 array as 10 + (10 >> 1) and
     copies the elements across.">
  <style>
    .lbl   { font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; fill: #1f2937; }
    .node  { font-size: 15px; font-weight: 600; }
    .body  { font-size: 13px; }
    .sub   { font-size: 10.5px; fill: #4b5563; }
    .tiny  { font-size: 11px; }
    .h1    { font-size: 15px; font-weight: 700; letter-spacing: .5px; }

    .boxP  { fill: #dbeafe; stroke: #2563eb; stroke-width: 1.6; }
    .boxR  { fill: #dcfce7; stroke: #15803d; stroke-width: 1.6; }

    .flow  { fill: none; stroke: #475569; stroke-width: 2; stroke-linejoin: round;
             marker-end: url(#tri); }
  </style>
  <defs>
    <marker id="tri" viewBox="0 0 10 10" refX="9" refY="5"
            markerWidth="6" markerHeight="6" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#475569"/>
    </marker>
  </defs>

  <rect x="0" y="0" width="900" height="320" fill="#ffffff"/>

  <text x="20" y="32" class="lbl h1">ARRAYLIST GROWTH ON THE ELEVENTH ADD</text>
  <line x1="20" y1="42" x2="880" y2="42" stroke="#d1d5db" stroke-width="1.5"/>

  <rect x="60" y="110" width="240" height="76" rx="6" class="boxP"/>
  <text x="180" y="140" text-anchor="middle" class="lbl node">elementData</text>
  <text x="180" y="162" text-anchor="middle" class="lbl body">capacity 10, size 10</text>
  <text x="180" y="178" text-anchor="middle" class="lbl sub">LedgerEntry[] backing array</text>

  <path class="flow" d="M 300 148 H 396"/>
  <text x="348" y="140" text-anchor="middle" class="lbl sub">grow()</text>

  <rect x="400" y="110" width="300" height="76" rx="6" class="boxR"/>
  <text x="550" y="140" text-anchor="middle" class="lbl node">new array</text>
  <text x="550" y="162" text-anchor="middle" class="lbl body">capacity 15 = 10 + (10 &gt;&gt; 1)</text>
  <text x="550" y="178" text-anchor="middle" class="lbl sub">Arrays.copyOf, O(n) once</text>

  <line x1="20" y1="266" x2="880" y2="266" stroke="#d1d5db" stroke-width="1.5"/>
  <rect x="20" y="278" width="22" height="16" rx="3" class="boxP"/>
  <text x="50" y="291" class="lbl tiny">state before</text>
  <rect x="150" y="278" width="22" height="16" rx="3" class="boxR"/>
  <text x="180" y="291" class="lbl tiny">state after</text>
  <path class="flow" d="M 290 286 H 330"/>
  <text x="338" y="291" class="lbl tiny">A → B : B is produced from A</text>
</svg>
```

Note `&gt;&gt;` — **escape `<`, `>`, and `&` in SVG text** or the file will not
parse.

Every SVG carries `role="img"` and an `aria-label` that reads as prose and states
what the picture shows, including the relationships a screen reader cannot infer
from geometry.

### Self-check: render it before you report it

Coordinates that look right in source are routinely wrong on screen. Before you
return, render and **look at** every SVG you wrote:

```bash
cd <topic>/diagrams && qlmanage -t -s 1400 -o . D-NN-slug.svg
```

Then open the resulting `.png` with the Read tool and check, per diagram:

- [ ] No text crosses or escapes its box.
- [ ] No box overlaps another box.
- [ ] No edge passes under a box, and no two edges overlay.
- [ ] Zero line crossings (or exactly one, reported).
- [ ] Every arrowhead lands on a box border, not in empty space or mid-label.
- [ ] Every legend entry is used, and every style used is in the legend.
- [ ] Every must-show item from the manifest row is visibly present.

Fix and re-render until it passes. Delete the `.png` files before returning —
they are scratch, not deliverables. A diagram you did not look at is not done.

### When a manifest diagram does not work

**Every id must land** still holds. If a `D-NN` in the manifest is genuinely not
renderable as a picture — it is a grid of values, or it is a list — render it as
a **Markdown table in the note file** at the point the diagram would have gone,
and record the substitution in the index's manifest block with a one-line reason.

The id is still accounted for. It is never silently dropped, and it never becomes
ASCII art.


---

## The example domain

**Every example comes from QuizStakes**, the shared fictional domain in
`src/scenario/scenario.md`. It is a regulated skill-based betting platform:
onboarding with status codes, compliance gates, restrictions, a bonus-and-cash
ledger, deposits and withdrawals, batched payment runs.

**Banned outright:** `Dog extends Animal`, `Foo` / `Bar` / `Baz`, `thread1` /
`thread2`, `MyClass`, `Employee`, `Shape` / `Circle` / `Square`, `Person`,
`test1`, `doSomething()`. A throwaway name in a code block is a defect, not a
style choice — re-dispatch the file.

**Where to take each thing from:**

| What you need | Where in `src/scenario/scenario.md` |
|---|---|
| A scenario for a concept | §15 Example Bank — 15.1 concurrency, 15.2 distributed/consistency, 15.3 data & storage, and the sections after |
| Vocabulary and status codes | §3 Glossary and §3.1 Status Code Index — `AA-610`, `DEP-301 CAPTURED`, `CLIENT_BONUS_RESERVED` |
| Services and their boundaries | §4 Service Catalog, §5 High-Level Architecture |
| Entities, fields, relationships | Appendix C — value types, aggregates, layering |
| Any number — volume, latency, size, lifetime | Appendix A. **Take the figure; never invent one.** |
| Money, buckets, ledger invariants | §11 Funds & Ledger Model |
| Flows worth walking end to end | §12 Client Payment Flows, §8 Onboarding Journey |
| Infrastructure or deployment naming | Appendix B |

**Rules that keep it honest:**

- Take names, status codes, and numbers **verbatim**. A reader who has met
  `CLIENT_BONUS_RESERVED` once must meet the same spelling every time.
- Reach for the Example Bank row that matches the concept before inventing a
  scenario. If §15 has no row for it, extend the domain in the same register —
  a new operation on an existing service, not a new universe.
- **Do not edit `src/scenario/scenario.md`.** It is read-only for this pipeline.
- The domain must not become the lesson. The concept stays the subject; QuizStakes
  is the material it is demonstrated on. If the example needs three paragraphs of
  domain setup before the concept appears, pick a smaller slice of the domain.
- **Where the concept is genuinely domain-free** — a language mechanic, a JVM
  constant, a bit trick — a minimal snippet with honestly-named locals is fine.
  Do not bolt a betting platform onto `Integer` caching. What is never fine is
  `Foo` and `thread1`.
- §1's reading-order table maps topic areas to the sections worth reading first.
  Use it when choosing a row's example assignment.

---

## The domain, reproduced in full (from the topic prompt's `# CONTEXT`)

**Every example in these notes comes from the QuizStakes domain, reproduced in full below.
Never write `Dog extends Animal`, `Foo`, `Bar`, `thread1`, `Person`, `Employee` or any other
throwaway example.** Use these entities, these status codes, these numbers, verbatim. A reader
who meets `CLIENT_BONUS_RESERVED` once must meet the same name every time. Where a concept is
genuinely domain-free (`peek` elision, text-block indentation, `Optional.empty()` identity),
still frame it in the domain: the stream is over stake reservations, the text block is the SQL
that reads the ledger, the `Optional` is a client lookup.

### What QuizStakes is

A regulated skill-based betting platform. A prospect registers, supplies personal details,
address, employment and income; is scored for affordability; accepts agreements; uploads
identity documents which an automated vendor verifies (inconclusive cases fall to human
review); and on approval the account is activated. The client deposits by card or bank
transfer. A first deposit with a valid coupon earns a bonus: **10% of the deposit, capped at
100**. Bonus money is stakeable but never directly withdrawable. Each stake draws
proportionally from bonus before cash. Winnings credit as cash. Withdrawals go out by card
(immediately, via the PSP) or by bank transfer (batched, with operator sign-off). The Quiz
Engine itself is a black box exposing exactly three operations: `ReserveStake`, `SettleStake`,
`VoidStake`.

### Vocabulary (use exactly these words)

| Term | Meaning |
|---|---|
| **Prospect** | Has begun registration. Has an application and an account shell; every money action is restricted. |
| **Client** | Has an activated account. |
| **Application** | The onboarding case. Has a lifecycle, a status, an audit trail. |
| **Account** | Created at registration, not at activation. Activation is a status change. |
| **Account shell** | An account that exists but carries system restrictions on every money action. |
| **Wallet** | The client-facing view of their money. Four buckets, two derived totals. |
| **Ledger** | The double-entry record. Sole source of truth for money. |
| **Cash** | Money from a deposit or a win. Stakeable and withdrawable. |
| **Bonus** | Promotional money. Stakeable, never directly withdrawable. Converts to cash only by winning. |
| **Stakeable** | Cash available + bonus available. Derived, never stored. |
| **Withdrawable** | Cash available only. Derived, never stored. |
| **Reserved** | Funds committed to an open stake or a pending withdrawal. |
| **Rail** | A mechanism for moving money: card deposit, bank deposit, card withdrawal, bank withdrawal. |
| **Instrument** | A specific card or bank account belonging to a client. |
| **Closed loop** | Withdrawals return to the instrument the money came from, up to the deposited amount. |
| **Gate** | A compliance condition that must hold before a transition is permitted. |
| **Restriction** | A block on a specific client action. Additive, overlapping, sourced, individually lifted. |
| **Requirement** | An outstanding document obligation. |
| **Referral** | A case a machine could not decide, routed to a human. |
| **PaymentRun** | A batch of approved bank withdrawals with operator sign-off. |
| **Suspense** | A holding position for money received but not yet attributable to a client. |

### Services you may name

`ApplicationGateway`, `RouterInt`, `JwtService`, `AccountOpening`, `PersonalDetails`,
`ClientAgreements`, `AssessmentService`, `AccountActivation`, `DocumentVerification`,
`DocumentRequirements`, `ScreeningService`, `ApplicationHistory`, `AccountMaintenance`,
`ClientRestrictions`, `InternalPlatforms`, `PaymentService`, `FundsLedger`, `CardPayments`,
`BankDeposits`, `BankWithdrawal`, `BonusService`, `BalanceView`, `ProfileService`,
`PendingActions`, `NotificationService`.

### Status codes (verbatim — never invent one)

Application capture (`AO-`): `AO-099 UNIQUENESS_FAILED`, `AO-100 IDENTITY_CREATED`,
`AO-110 CONTACT_VERIFICATION_PENDING`, `AO-111 CONTACT_VERIFIED`, `AO-115 DOB_PHONE_PENDING`,
`AO-116 DOB_PHONE_CAPTURED`, `AO-119 AGE_INELIGIBLE`, `AO-120 ADDRESS_PENDING`,
`AO-121 ADDRESS_CAPTURED`, `AO-129 JURISDICTION_INELIGIBLE`, `AO-135 DUPLICATE_CHECK_PENDING`,
`AO-136 DUPLICATE_CHECK_CLEAR`, `AO-139 DUPLICATE_IDENTITY`, `AO-140 WEALTH_PENDING`,
`AO-141 WEALTH_ACCEPTABLE`, `AO-145 WEALTH_REFERRED`, `AO-149 WEALTH_REJECTED`,
`AO-200 AGREEMENTS_PENDING`, `AO-201 AGREEMENTS_ACCEPTED`, `AO-290 AGREEMENTS_SUPERSEDED`,
`AO-300 PROFILE_COMPLETE`, `AO-400 SUBMITTED`.

Activation (`AA-`): `AA-500 SCREENING_IN_PROGRESS`, `AA-501 SCREENING_CLEAR`,
`AA-550 SCREENING_POTENTIAL_MATCH`, `AA-599 SCREENING_PROHIBITED`, `AA-600 DOCUMENTS_REQUESTED`,
`AA-610 DOCUMENTS_UPLOADED`, `AA-611 DOCUMENTS_VERIFIED`, `AA-650 DOCUMENTS_REFERRED`,
`AA-690 DOCUMENTS_REJECTED`, `AA-699 DOCUMENTS_EXHAUSTED`, `AA-700 REVIEW_QUEUED`,
`AA-710 REVIEW_IN_PROGRESS`, `AA-711 REVIEW_APPROVED`, `AA-799 REVIEW_DECLINED`,
`AA-800 ACTIVATING`, `AA-801 ACTIVATED`, `AA-900 DECLINED`, `AA-910 ABANDONED`,
`AA-920 WITHDRAWN`.

Card deposit uses `DEP-nnn` (e.g. `DEP-301 CAPTURED`); bank deposit uses `BDP-nnn`. The
numbered-code structure is `XX-Nnn` where `N` is the phase and the middle digit is the
disposition: `0` in progress, `1` success, `5` referred to a human, `9` failed or blocked.

Bare-name machines: account lifecycle `PENDING_VERIFICATION`, `ACTIVE`, `DORMANT`, `CLOSING`,
`CLOSED`; restriction `ACTIVE`, `LIFTED`, `EXPIRED`; document requirement `REQUIRED`,
`SUBMITTED`, `SATISFIED`, `WAIVED`, `EXPIRED`; bonus `GRANTED`, `ACTIVE`, `CONSUMED`,
`EXPIRED`, `CLAWED_BACK`.

### Restrictions

`DEPOSIT_BLOCKED`, `STAKE_BLOCKED`, `WITHDRAWAL_BLOCKED`, `DEPOSIT_LIMITED`, `WITHDRAWAL_HELD`,
`SOURCE_OF_FUNDS_REQUIRED`, `ALL_BLOCKED`, `SELF_EXCLUDED`, `COOLING_OFF`, `DORMANT_FROZEN`.
Sources: `SYSTEM_ONBOARDING`, `SYSTEM_COMPLIANCE`, `SYSTEM_LIFECYCLE`, `ADMIN`, `CLIENT`.
**Restriction identity is the pair (type, source), not the type alone** — `STAKE_BLOCKED` from
`SYSTEM_ONBOARDING` lifts automatically at `AA-801`; the same type from `ADMIN` does not.
`SELF_EXCLUDED` carries `reversibleByOperator = false`.

### Ledger positions

`CLIENT_CASH_AVAILABLE`, `CLIENT_CASH_RESERVED`, `CLIENT_BONUS_AVAILABLE`,
`CLIENT_BONUS_RESERVED`, `SUSPENSE`, `PSP_RECEIVABLE`, `BANK_SETTLEMENT`, `HOUSE_REVENUE`,
`PROMOTIONAL_EXPENSE`, `FEES`, `CHARGEBACK_LOSS`.

Derived, never stored: **Stakeable** = `CASH_AVAILABLE + BONUS_AVAILABLE`; **Withdrawable** =
`CASH_AVAILABLE`; **Total** = all four client buckets.

The win/void asymmetry, which is the domain's sharpest edge: reserved bonus returns as **cash**
on a win, as **bonus** on a void, and goes to `HOUSE_REVENUE` on a loss.

### Bonus rules (use these exact numbers)

| Rule | Value |
|---|---|
| Grant | 10% of the first deposit, capped at 100 |
| Eligibility | First deposit only, one per identity, valid coupon |
| Coupon validity | 14 days from registration |
| Expiry | 30 days from grant; unspent reverses to `PROMOTIONAL_EXPENSE` |
| Wagering requirement | None |
| Stake consumption | `min(BONUS_AVAILABLE, 10% of stake)`; remainder from cash |
| Rounding | Bonus portion **rounds down** to the minor unit; cash covers the remainder |
| Clawback | Unspent bonus first; shortfall to `PROMOTIONAL_EXPENSE` |

The canonical rounding example: a stake of **3.33** splits as **0.33 bonus + 3.00 cash**.
Rounding the other way gives 0.34 + 3.00 = 3.34, which creates money. Use this example wherever
rounding, `BigDecimal` scale, `RoundingMode` or integer division is being taught.

### Types you may declare (from the domain's type sketch)

Value types: `Money(BigDecimal amount, Currency currency)`, `ClientId`, `ApplicationId`,
`AccountId`, `PersonId`, `RoundId` (each wrapping a `UUID`), `IdempotencyKey(String value)`,
`StatusCode(domain, phase, disposition, variant)`, `Jurisdiction(country, subdivision)`,
`AgreementRef(documentId, version)`, `LimitSet(dailyDeposit, maxStake, monthlyLoss)`,
`StakeSplit(Money bonusPortion, Money cashPortion)` — **invariant: the two sum exactly to the
stake** — `Verdict(outcome, reason, decidedAt, decidedBy)` as a sealed hierarchy
(`DocumentVerdict`, `ScreeningVerdict`, `ReviewVerdict`, `WealthVerdict`),
`RestrictionKey(RestrictionType type, RestrictionSource source)`.

Aggregates: `Application`, `Account`, `Restriction`, `LedgerEntry`, `Movement`, `Position`,
`Reservation`, `Bonus`, `PaymentIntent`, `WithdrawalTransaction`, `PaymentRun`,
`InstrumentVerification`, `DocumentRequirement`, `GateSet`, `ReviewCase`.

Exceptions you may define: `InsufficientFundsException`, `RestrictedActionException`,
`IllegalTransitionException`, `LedgerImbalanceException`, `BonusIneligibleException`.

### Numbers you may quote (never invent new ones)

| Metric | Value |
|---|---|
| Registered clients | 2.4M |
| Monthly active clients | 380k |
| Concurrent sessions | 14k steady, 55k peak |
| Registrations started/day | 12k steady, 40k peak |
| Applications reaching `AO-400`/day | 7.2k steady, 24k peak |
| Manual review rate | 11% of submissions (19% on poor document quality) |
| Operators on shift | 40 steady, 90 peak; 22 cases per operator per hour |
| Card deposits | 95k/day, 40/sec peak, avg value 65 |
| Bank deposits | 6.5k/day, batch, avg value 480 |
| Bonus grants | 3.1k/day, 8/sec, avg value 42 |
| Card withdrawals | 11k/day, 12/sec, avg value 180 |
| Bank withdrawals | 7k/day, batch, avg value 260 |
| Stake reservations | 2.8M/day, 1,200/sec peak, avg value 4.20 |
| Stake settlements | 2.8M/day, 3,400/sec burst |
| Chargebacks raised | 140/day, avg value 92 |
| Ledger entries | ~19.8M/day, ~7.2B/year, ~180 bytes/row, ~1.3 TB/year |
| Ledger write rate | 230/sec sustained, 13,600/sec peak |
| Ledger hot window / retention | 90 days / 7 years |
| Identity vendor | p50 900ms, p99 38s, 600/min estate-wide cap |
| Watchlist provider | p50 1.4s, p99 25s, 30s timeout, 200/min |
| Card PSP authorise / capture / payout | p50 240ms / 180ms / 400ms; p99 11s / 6s / 9s |
| Banking partner payout file | p50 2s, p99 45s, 4 windows/day |

These are the numbers for every memory calculation, every allocation count, every throughput
argument. A parallel-stream benchmark runs over 2.8M stake reservations; a virtual-thread
sizing argument uses 55k peak concurrent sessions; a `groupingBy` example groups 95k card
deposits by rail; Little's law is worked with 1,200 reservations/sec and the PSP's 240ms p50.


---

## Return only this envelope

```
path: <one line per file you wrote, relative to /Users/rajat.chikkodikar/Desktop/My-files/rough/src/notes/detailed/04-modern-java/>
lines: <n/a for svg>
leaves: <the syllabus leaf ids from your rows>
diagrams: <the D-NNN ids you authored>
unverified: <none | one line per unverified claim, including any single unavoidable line crossing>
blocked: <none | what is missing and what would settle it>
```

Nothing else. No narration, no summary of what you drew.

---

## A real compiler is available — use it

`javac` and `java` **25.0.1** are on this machine at `/usr/bin/javac` and `/usr/bin/java`.
`jshell` and `javap` are alongside them.

**Any compiler diagnostic, exception message, `javap` listing or program output you put in a
diagram must be produced by actually running it, not recalled.** Work in a scratch directory
under `/tmp`, never inside the notes tree. Compile with `--release 21` so the class file and the
diagnostics match the notes' target:

```bash
mkdir -p /tmp/vfy && cd /tmp/vfy
javac --release 21 Example.java
javap -c -p -v Example.class
java --enable-preview --release 21 ...   # preview features need this on 21
```

Two cautions:

- You are on JDK 25, not 21. `--release 21` fixes the class-file version and the visible API, but
  a few *diagnostic wordings* and JIT/runtime behaviours can still differ. If a figure could
  differ between 21 and 25, say so on the diagram or in your envelope's `unverified` line rather
  than presenting the 25 output as 21's.
- Preview-only APIs of Java 21 (`StructuredTaskScope`, `ScopedValue`, string templates) are not
  compilable on 25 in their Java 21 shape, because the API changed. Do not try to reproduce their
  output; draw them from the API shape stated in your packet and mark the figure accordingly.
