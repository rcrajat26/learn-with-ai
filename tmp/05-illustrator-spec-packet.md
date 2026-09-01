# ILLUSTRATOR SPEC PACKET — topic 05 Multithreading and Concurrency

Read this file in full before drawing. Your dispatch message carries your batch: the manifest row
for each `D-NNN` — id, title, syllabus leaf, type, and the `Must show` contents. This file carries
the drawing standard, which is the same for every illustrator on this topic.

You write **only** into
`/Users/rajat.chikkodikar/Desktop/My-files/rough/src/notes/detailed/05-multithreading-concurrency/diagrams/`.
You write no Markdown. You do not touch `00-index.md` or any note file.

For domain detail — entity names, status codes, figures — read the `## The example domain`
section of `/Users/rajat.chikkodikar/Desktop/My-files/rough/tmp/05-writer-style-packet.md`, and
`/Users/rajat.chikkodikar/Desktop/My-files/rough/src/scenario/scenario.md` if you need more. Both
are read-only.

---

## Manifest rules you must follow

- One idea per diagram. Prefer more, smaller diagrams over one dense one.
- Where the `Must show` column asks for *frames*, produce that many clearly separated,
  individually labelled panels inside the one SVG, each captioned with the frame number and what
  changed since the previous frame.
- **Every label, constant and value named in `Must show` must be visible as text in the SVG.** A
  diagram that omits a named value does not satisfy the manifest.
- Arrows must be directional, orthogonal, and labelled where the direction is not obvious.
- Every diagram is drawn on QuizStakes data. Where the `Must show` cell names domain values
  (`CLIENT_BONUS_AVAILABLE`, 1,200 reservations/sec, a 3.33 stake, the 240 ms PSP p50), use those
  exact values.
- Two-thread interleaving diagrams get a time axis running downwards with one lane per thread, and
  every step numbered so the reader can replay it.
- **Labels name the QuizStakes domain**, never `Foo`, `Object A`, or `thread1`. A node is
  `LedgerEntry`, `DEP-301 CAPTURED`, `PaymentRun`, `ClientRestrictions`. Threads in an
  interleaving are named for what they do — `settlement-ingest-3`, `payment-run-worker`,
  `operator-review`.

---

## Diagram spec

Every diagram is **one standalone `.svg` file** named `D-NNN-short-slug.svg`. Never ASCII art.

- The SVG must show everything its manifest row's **Must show** column names — every labelled
  constant, every value, every arrow.
- Where the manifest calls for a frame series that will not fit one canvas, author each frame as
  its own file (`D-007a-…`, `D-007b-…`) and report all ids in your envelope.
- The file is the single canonical home for that `D-NNN`. Never write a copy.

### Canvas

- `viewBox` always. **No `width` or `height` attributes on the `<svg>` element** — the diagram
  must scale to the reader's column.
- Size the canvas to the content, then stop. Working starting points: `0 0 1040 900` layered
  hierarchies, `0 0 1120 800` two-family side-by-side comparisons, `0 0 900 400` linear flows and
  timelines, `0 0 640 640` square structures such as trees and grids. Widen before you shrink
  text.
- Nothing may touch the `viewBox` edge; keep a **20-unit margin** on all sides.
- **First element is an opaque backdrop** covering the whole viewBox:
  `<rect x="0" y="0" width="W" height="H" fill="#ffffff"/>`. This is what makes the diagram
  legible in GitHub dark mode, in VS Code, and in a PDF export. **White is used for nothing else
  in the file** — no other `fill="#ffffff"`. Pure black fill is never used.

### Layout — this is what separates a clean diagram from a messy one

Fills and fonts are not the problem. Routing and alignment are. In order of importance:

1. **Layer it.** Every node of the same generation shares one y band. A child is never level with
   its parent, and never above it.
2. **Orthogonal routing only.** Every edge is horizontal and vertical segments with square
   elbows: `d="M 420 273 V 290 H 168 V 306"`. **No diagonals, no `C`/`Q`/`S`/`T`/`A` segments, no
   `<line>` between two arbitrary points.** Diagonal spaghetti is the single largest source of
   mess.
3. **Fan out on a bus.** One parent with three or more children draws one vertical stub down to a
   shared horizontal bus, then one vertical drop per child.
4. **Give each edge its own exit x.** Two edges leaving the same parent leave at different x
   offsets so their elbows never overlay.
5. **Route through corridors.** An edge that must pass a column reserves a clear x lane between
   boxes and turns only inside it.
6. **Target zero line crossings.** If one is genuinely unavoidable, keep it to one and say so in
   your envelope's `unverified` line.
7. **Put the relationship that matters on a straight centre spine**, and let the siblings go left
   and right.
8. **No per-edge text labels** beyond what the manifest demands. Encode the relation in the line
   style and explain it once in the legend.

### Required furniture

Every diagram has, in this order:

- **Title**, top-left, `.h1`, followed by a full-width hairline rule in `#d1d5db`. Not centred,
  not in a filled banner bar.
- **Section band headers** in `.h2` where the diagram holds two families or lanes
  (`SINGLE CORE — concurrent, zero parallelism`). Two unlabelled halves read as one confusing
  whole.
- **Legend**, bottom, under a second hairline rule: one swatch per box style used and one line
  sample per edge style used, each with a short gloss. Every style the diagram uses appears; no
  style appears that it does not use.

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

No gradients, no opacity below 1 on fills, no drop shadows, no colour outside these tables.

### Line semantics

One meaning per style, declared in the legend, consistent across every diagram in the topic:

| Relation | Style | Stroke |
|---|---|---|
| extends / primary flow | solid, `stroke-width="2"`, filled arrowhead | `#475569` |
| implements / nested type of | dashed `6 4`, arrowhead | `#15803d` |
| adapter or bridge, **not** inheritance | dotted `3 3`, arrowhead | `#b45309` |
| weak, optional, or inferred link | dotted `4 3`, arrowhead | `#9ca3af` |
| class-to-class inheritance among legacy types | solid `1.8` | `#78716c` |

Arrowheads point **at the child / at the target**, and the legend spells the direction out
(`A → B : B extends A`) so it cannot be read backwards. One `<marker>` per stroke colour in
`<defs>`.

### Typography and the style block

- One `<style>` element at the top of the file holding class selectors, then class attributes on
  the shapes. **Plain class selectors only** — no `@import`, no `@font-face`, no attribute
  selectors, no media queries, no `xlink:href`, nothing that reaches off-file. No external URL
  anywhere in the file except the `w3.org` namespace.
- Font stack: `-apple-system, "Segoe UI", Helvetica, Arial, sans-serif`.
- 15px node titles, 13px node body, 12.5px dense node body, 11px legend and annotation rows,
  **10.5px absolute floor** for sub-labels. Nothing below 10.5px, in an attribute or in the style
  block.
- `stroke-width="2"` minimum on any line that carries meaning; `1.3`–`1.6` is for box borders and
  hairlines only.
- Explicit `fill` on every `<text>` (via its class is fine) and explicit `stroke` on every filled
  shape.

### Text must fit its box — do the arithmetic

An overflowing label is the most common defect and it is fully preventable. Estimate rendered
width as **characters × 0.55 × font-size** (× 0.6 for bold), and keep **≥ 12 units of clearance**
inside the box on each side. If it does not fit: widen the box, or restructure — never shrink
below the floor and never let it spill.

**Leaf sets go in one grouped panel, not N tiny boxes.** Draw one panel, one arrow into it, a bold
header row, and one left-aligned row per leaf.

**Annotation panels carry the prose.** Facts that are neither node nor edge go in an `#eff6ff`
panel with a bold header and 11px rows, placed in otherwise empty canvas. Two panels per diagram
is the ceiling.

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

  <text x="20" y="32" class="lbl h1">TITLE IN CAPS</text>
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

Note `&gt;&gt;` — **escape `<`, `>`, and `&` in SVG text** or the file will not parse.

Every SVG carries `role="img"` and an `aria-label` that reads as prose and states what the picture
shows, including the relationships a screen reader cannot infer from geometry.

---

## Self-check: render it before you report it

Coordinates that look right in source are routinely wrong on screen. Before you return, render and
**look at** every SVG you wrote:

**Render into a scratch directory outside `diagrams/`.** `rm` is denied in this session, so a PNG
written next to the SVGs cannot be cleaned up and becomes a stray deliverable. Use `/tmp`:

```bash
mkdir -p /tmp/05-render-check
cd /Users/rajat.chikkodikar/Desktop/My-files/rough/src/notes/detailed/05-multithreading-concurrency/diagrams && qlmanage -t -s 1400 -o /tmp/05-render-check D-NNN-slug.svg
```

The PNG then lands at `/tmp/05-render-check/D-NNN-slug.svg.png`. Open that path with the Read
tool. Never write a `.png` into `diagrams/`.

Then open the resulting `.png` with the Read tool and check, per diagram:

- [ ] No text crosses or escapes its box.
- [ ] No box overlaps another box.
- [ ] No edge passes under a box, and no two edges overlay.
- [ ] Zero line crossings (or exactly one, reported).
- [ ] Every arrowhead lands on a box border, not in empty space or mid-label.
- [ ] Every legend entry is used, and every style used is in the legend.
- [ ] Every `Must show` item from the manifest row is visibly present.

Fix and re-render until it passes. The `.png` files live in `/tmp/05-render-check` and need no
cleanup; do not attempt `rm`, it is denied. A diagram you did not look at is not done; if you
genuinely could not render, say `unverified: not rendered` in your envelope.

---

## Return envelope

Return only this, nothing else:

```
diagrams: <D-NNN files written, with filenames>
unverified: <none | one line per diagram you could not render or check>
blocked: <none | any D-NNN that is not renderable as a picture, with a one-line reason>
```

A `D-NNN` that is genuinely a grid of values or a list is **not** drawn as a picture and **not**
drawn as ASCII art — report it as `blocked` with the reason, and the orchestrator will have the
owning note file render it as a Markdown table instead.
