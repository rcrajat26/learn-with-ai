## Diagram spec

*Hand this section verbatim to every illustrator, with the manifest rows for its
batch.*

Every diagram is **one standalone `.svg` file** in the topic-root `diagrams/`
folder, named `D-NN-short-slug.svg`, embedded from the Markdown at the point of
explanation:

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

### Diagrams authored before this spec

Topics generated under the earlier spec have SVGs with no backdrop rect, inline
style attributes, `#737373` strokes, and diagonal or Bézier edges. They render
correctly; they are simply not this style, and the SVG block of the verify script
will flag every one of them.

**Do not restyle them as a side effect of another task.** Migrating a topic's
back catalogue is its own explicitly commissioned pass. When verify runs over a
topic that predates this spec, triage the SVG failures as known-legacy and report
the count in one line rather than as N separate failures. New and re-authored
diagrams meet this spec with no exceptions.

### When a manifest diagram does not work

**Every id must land** still holds. If a `D-NN` in the manifest is genuinely not
renderable as a picture — it is a grid of values, or it is a list — render it as
a **Markdown table in the note file** at the point the diagram would have gone,
and record the substitution in the index's manifest block with a one-line reason.

The id is still accounted for. It is never silently dropped, and it never becomes
ASCII art.

### Relationship to `src/topics/`

`src/topics/<NN>-<slug>.md` is a flat summary guide from a different pipeline.
**Read it for scope and register. Never edit it. Never write into it. Never
treat its coverage as sufficient.** You always build fresh in
`src/notes/detailed/`. Cross-reference it only if it genuinely holds something
your set does not.

---
