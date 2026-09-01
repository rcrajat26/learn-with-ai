#!/usr/bin/env python3
"""Builds self-contained illustrator packets, <=4 SVG diagrams each."""
import json, os, re

ROOT = "/Users/rajat.chikkodikar/Desktop/My-files/rough"
TOPIC = f"{ROOT}/src/notes/detailed/04-modern-java"
OUTDIR = f"{ROOT}/tmp/packets"
os.makedirs(OUTDIR, exist_ok=True)

d = json.load(open('/tmp/plan2.json'))
diag = d['diag']
spec = open(f"{ROOT}/tmp/spec-diagram.md").read()
domain = open(f"{ROOT}/tmp/spec-domain.md").read()

svgids = [k for k in sorted(diag) if diag[k]['type'] != 'table']
assert len(svgids) == 136

STOP = {'the','a','an','and','or','of','in','to','is','are','it','its','on','at',
        'for','with','not','do','does','where','what','how','why','which','that',
        'be','by','as','from','into','one','you','your','their','every','all'}
def slug(title):
    s = re.sub(r'`|\(|\)|,|\.|\'|"|—|:|/|\+|\?|<|>', ' ', title.lower())
    toks = [t for t in re.split(r'[^a-z0-9]+', s) if t and t not in STOP]
    return '-'.join(toks[:4]) or 'diagram'

batches = [svgids[i:i+4] for i in range(0, len(svgids), 4)]
manifest = []
for n, b in enumerate(batches, 1):
    name = f"ill-{n:02d}"
    rows = []
    for did in b:
        x = diag[did]
        rows.append(f"### {did} — {x['title']}\n\n"
                    f"- **Target filename:** `{did}-{slug(x['title'])}.svg`\n"
                    f"- **Type:** {x['type']}\n"
                    f"- **Syllabus leaf:** {x['leaf']}\n"
                    f"- **Must show (this is the contract — every named label, constant and value "
                    f"must be visible as text in the SVG):** {x['must']}\n")
    body = f"""# Illustrator packet {name} — topic 04 Modern Java

You are authoring **{len(b)} standalone SVG diagram files** for a study-note set on Modern Java
(Java 8 → 21). This packet is your complete brief. You need nothing else, with one exception:
`{ROOT}/src/scenario/scenario.md` is read-only shared domain reference you may open for detail
beyond what is pasted below.

## What to write, and where

Write each file into:

```
{TOPIC}/diagrams/
```

Filenames are given per diagram below. Create nothing else. Do not touch any `.md` file. Do not
touch `00-index.md`.

## Your assignment

{chr(10).join(rows)}

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

{spec}

---

{domain}

---

## Return only this envelope

```
path: <one line per file you wrote, relative to {TOPIC}/>
lines: <n/a for svg>
leaves: <the syllabus leaf ids from your rows>
diagrams: <the D-NNN ids you authored>
unverified: <none | one line per unverified claim, including any single unavoidable line crossing>
blocked: <none | what is missing and what would settle it>
```

Nothing else. No narration, no summary of what you drew.
"""
    open(f"{OUTDIR}/{name}.md", 'w').write(body)
    manifest.append((name, b))

json.dump({n: b for n, b in manifest}, open('/tmp/ill_batches.json', 'w'), indent=0)
print(f"wrote {len(batches)} illustrator packets to {OUTDIR}")
for n, b in manifest:
    print(n, ' '.join(b))
