## How a concept is written

### Which concepts get the full treatment

Not every concept carries eight beats. **Sort first.**

A **primary concept** is one that satisfies any of:

- it has a cost or performance claim;
- it has a diagram in the manifest;
- it has a sibling it must be chosen against;
- a reader could plausibly be asked about it for five minutes in an interview.

Primary concepts get **all eight beats, in order, with a `###` heading**.

A **supporting fact** is everything else — a convenience method, a constant, an
API shape with no tradeoff. Supporting facts get **three beats only**: mechanism,
gotcha if one exists, and the boxed definition. Three to ten lines. No diagram,
no separate heading, no manufactured analogy.

Forcing the full sequence onto a supporting fact produces exactly the filler the
house rules ban. `Collections.emptyList()` does not have a mental model and did
not solve a historical problem worth two paragraphs.

A note file carries **two to six primary concepts**. More than six means it should
have been split; zero means it should have been folded. Both are planning errors
— fix them in `00-index.md`, not by adjusting the prose. **You do not touch
`00-index.md`.** If you believe your row is wrong or under-scoped, return that as
a `blocked` instead of fixing it unilaterally.

**Concepts do not straddle splits.** Choose split points at concept boundaries, so
the boxed definition always closes its concept in the same file.

### The eight beats

These are for primary concepts. They need not be labelled, but they must be
present and in this sequence.

1. **Mental model first.** Open with the picture: what shape this thing is, what
   it is doing under the hood, the one analogy that makes the rest fall out. Not
   a definition. Never open with "X is a class in `java.util` that…".
2. **Why it exists** — the problem it solves, and what people did before it.
3. **When to reach for it, and when not.** Explicit. Name the sibling that wins
   in the cases where this one loses.
4. **How it works** — the mechanism, at the depth the tier demands. In an
   INTERNALS file this is a source walk with real named constants and their
   values.
5. **The diagram, embedded inline in the flow.** The `D-NNN` assigned to you,
   embedded with `![caption](../diagrams/D-NNN-slug.svg)` at the point in the
   explanation where the reader needs the picture — immediately after the
   mechanism it illustrates, before the code. Never collected into a gallery at
   the end of a file, never pushed to an appendix, never merely linked as "see
   diagram D-007". The caption states what to look at.
6. **A minimal concrete example** — real, complete, runnable code, **drawn from
   the QuizStakes domain**. Full method bodies, real generics, real edge cases.
   Strip only imports, package lines, and empty `main` scaffolding. No `...`, no
   "implementation omitted", no pseudo-code. Class and field names come from the
   domain — `LedgerEntry`, `ClientRestrictions`, `stakeReservation` — never
   `Foo`, `MyClass`, or `thread1`.
7. **The gotcha.**
8. **The definition, last** — one crisp sentence, boxed as a blockquote, now
   that the reader has earned it.

If a beat genuinely does not apply, say so in one line rather than dropping it
silently.

**The topic prompt states the chain as `Concept → Why it exists → How it works →
SVG → Code → Gotcha`, with all six links mandatory and any inapplicable link
noted in one line rather than dropped.** Those six are beats 1/2, 4, 5, 6 and 7.
The eight beats above are that chain plus the mental-model opener, the
when-to-reach-for-it beat, and the boxed closing definition. Satisfy the eight and
you have satisfied the six.

### Hierarchy before details

Every subtopic file that introduces a family opens with the hierarchy — as a
diagram where one is assigned to you, as a table otherwise. The reader sees the
map before the streets.

### Tradeoff, not fact

"`HashMap` is O(1) lookup" is documentation. Notes say: O(1) lookup, **but** no
ordering guarantee, **and** each bucket degrades to O(log n) after treeify since
Java 8 — which is precisely why `TreeMap` still earns its place when you need
sorted iteration. Every performance claim carries its cost and its escape hatch.

### Tables for siblings

Three or more things doing a similar job get a comparison table, always. Never
three paragraphs describing them one after another.

### Callouts

Exactly three markers, bolded, inline where they belong. Do not invent others.

- `**Pitfall:**` — the wrong belief, the symptom it produces, the fix.
- `**Insight:**` — the non-obvious mechanism that makes the rest click.
- `**Interview:**` — how this is actually asked, and the one-line answer.

Every syllabus leaf tagged `[TRAP]` must carry a `**Pitfall:**`.

### Version behaviour

The file states its target version in the header. Any constant, default, API
shape, or behaviour that differs across versions is called out **inline at the
point of the claim**, naming which version does what. Where a widely-repeated
claim is version-stale, state what is true today, what used to be true, and flag
it as a version trap — interviewers still ask for the old form.

Because this topic *is* the version story, version deltas are not an afterthought.
Whenever a behaviour, a constant, a default or an API shape differs across
**Java 8 / 9+ / 11 / 17 / 21**, say which release does what, inline, at the point
of the claim — not in a footnote.

---

## Tag obligations — the syllabus tags are instructions, not decoration

Your pasted leaves carry these tags. Each one is a contract.

- `[PROVE]` — work the argument through on the page. Do not state the result.
- `[SOURCE]` — quote the real JDK source, JEP text or spec text (short excerpt)
  and explain **every quoted line**.
- `[BUILD]` — ship complete, compiling, generic code.
- `[TRAP]` — carry a `**Pitfall:**` marker: wrong belief, symptom, fix.
- `[RESEARCH]` — re-verify against the JDK 21 source at the jdk-21+35 tag, the
  javadoc, the JLS/JVMS or the named JEP **before writing**. If you cannot verify
  a claim, say so explicitly in the text rather than asserting it.
- `[VERSION-TRAP]` — state what is true in 21 **and** what used to be true.
- `[X-REF nn]` — one self-contained mechanism paragraph here, giving the reader
  enough to answer the interview question, **then** point to the sibling guide nn
  for the full treatment. Never send the reader away empty-handed, and never
  duplicate a sibling's full chapter. The sibling guides are: 01 DSA
  fundamentals, 02 Java collections, 03 Java core, 05 Multithreading and
  concurrency, 06 JVM internals, 07 Spring core, 08 Spring Data JPA, 09 SQL
  databases, 10 Networking, 12 API design, 13 Web security, 16 Testing, 17 Git
  craft, 20 Observability. Refer to them by number and subject in prose (for
  example, "the container internals are guide 02's territory"); do not invent
  file paths or links to them.
- `[NUM]` — state the number or byte arithmetic explicitly, **with the arithmetic
  shown**.
- `[BYTECODE]` — show the `javap -c` output and read it instruction by
  instruction.

---

## Every file ends the same way

1. `## Pitfalls` — **wrong-then-right**, one entry per pitfall:

   ```
   ### Assuming HashMap iteration order is insertion order

   **Wrong**
   <code showing the belief in action, and the output that surprises>

   **Right**
   <code that actually gets the guarantee, and why>

   **Why people believe it:** <the plausible-sounding reason>
   ```

2. `## Cheat sheet` — a one-screen table. Everything on it must be recallable
   at a glance the night before an interview. No prose.

3. `## Self-test` — **between 5 and 10 questions inclusive** (this is enforced by
   a verify script — fewer than 5 or more than 10 `<details>` blocks fails),
   answers folded below each:

   ```
   **Q3.** Why does ArrayList.remove(int) shift and ArrayList.remove(Object) scan?

   <details><summary>Answer</summary>

   <the full answer, not a hint>

   </details>
   ```

4. `## Deferred` — the leaves you could not cover, with the leaf number and a
   one-line reason each. **An empty `## Deferred` block containing the single
   line `None.` is the expected outcome.**

5. `## Open questions` — only if you have `**Unverified:**` claims in the body.
   One line each, naming what you could not confirm and what source would settle
   it. Omit the section entirely if you have none.

---

## Header and footer on every note file

Header, exactly this shape (your packet gives you the filled-in values):

```
# 04 Modern Java — <subject> — <tier> (<syllabus sections covered>)

**Target version: Java 21 LTS.** | **Part <n> of 5** | [Index](<index link>)
Previous: [<title>](<relative path>) · Next: [<title>](<relative path>)
```

The first file in the whole set omits `Previous:` entirely; the last omits
`Next:`. Never emit a link to a file that does not exist and never write
`Previous: none`. Your packet hands you the finished nav line — use it verbatim.

Footer, exactly this shape:

```
---

**Leaves covered:** <explicit list or ranges> (<count> leaves)
**Leaves deferred:** <none | leaf number + one-line reason each>
**Diagrams included:** <D-NNN, D-NNN, …>
**Target version:** Java 21 LTS
**Lines:** <count>
```

Put a placeholder integer on the `**Lines:**` line; the orchestrator patches the
real count afterwards.

---

## Research protocol

Search when it changes the answer:

- **Search:** version-sensitive behaviour, API changes and deprecations, current
  best practice, library and runtime versions, benchmark figures, anything where
  a specific number appears in the notes. Verify rather than recall.
- **Do not search:** stable fundamentals. How a hash table works, what
  amortised O(1) means, why red-black trees rebalance.

`openjdk.org` may return HTTP 403 on direct fetch. JDK source at a release tag is
reliably reachable at
`https://raw.githubusercontent.com/openjdk/jdk/jdk-21%2B35/src/java.base/share/classes/<path>`,
and JEP text through a mirror (`javaalmanac.io`, `bugs.openjdk.org`,
`cr.openjdk.org`). Re-fetch a JEP through a mirror before quoting it verbatim.

**When research is still insufficient after searching**, do not invent and do
not quietly soften the claim. Instead:

1. Mark the claim inline as `**Unverified:**` with what you could not confirm.
2. Record it in the `## Open questions` block at the foot of the file.
3. Surface every one of them in your return envelope's `unverified` line.

If a missing fact blocks the whole file — it cannot be written honestly without
it — **do not write the file**. Return it as `blocked` in the envelope, naming
what is missing and what would settle it.

---

## House rules

- No emojis. No filler — no "let's dive in", "great question", "in this section
  we will", "as we all know", "it's worth noting". Lead with content.
- **No line limit on completeness.** Never truncate, never write "and so on",
  never write "similar to the above", never defer a concept for space. Your
  target size is a shape, not a budget: if you are overrunning it because the
  material genuinely needs the room, keep writing and say so in your envelope.
  What you must never do is thin the content to hit a number.
- Markdown (`.md`). One file — the one your packet names. Create nothing else.
  Never touch `00-index.md`, never touch another writer's file, never touch
  `src/scenario/scenario.md` or anything under `src/topics/`.
- Java code is Java 21 idiomatic: records, sealed interfaces, pattern-matching
  `switch`, text blocks, `var` sparingly, modern Spring Boot 3.x where Spring is
  in scope. Where a snippet needs `--enable-preview` on Java 21 (structured
  concurrency, scoped values, string templates), **say so on the snippet**.
- Every Java snippet is complete and compiles as written, minus only imports,
  package declarations and pointless `main` scaffolding. Quoted JDK source may be
  excerpted to the relevant lines, but every line quoted must then be explained.
- A table for any comparison of three or more things.
- **Every example uses the QuizStakes domain**, with entity names, status codes
  and numbers verbatim — never `Dog extends Animal`, `Foo`, `Bar`, `thread1`,
  `Person`, `Employee`, `MyClass`, `Shape`/`Circle`/`Square`, `doSomething()`.
- Do not write the string `...` inside a fenced code block; a verify script
  treats that as an elision failure and the file gets re-dispatched.
- Never inline `<svg>` in the Markdown, and never draw with ASCII characters.
  Diagrams are embedded image references to files that already exist.
