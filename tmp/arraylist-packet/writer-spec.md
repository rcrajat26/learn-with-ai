## The teaching contract

The set is read front to back by someone who does not yet know the topic. That
imposes four rules the reference pipeline does not have:

1. **Nothing is used before it is taught.** If a file leans on a concept the set
   has not introduced, either teach it there or the file is in the wrong
   position. The map fixes the order; a writer that hits this returns `blocked`.
2. **Every file opens with its prerequisites**, one line naming the earlier files
   it depends on: `Assumes: <concept> (file 03).` The orchestrator computes this
   line and hands it over.
3. **Every file closes by naming what it set up.** One line: `Next: <the question
   the following file answers>.` A reader must always know why the next file
   exists.
4. **Depth increases monotonically.** A `01-` file that reaches for a named JVM
   constant or a bytecode listing, or an `07-` file that re-explains the topic's
   premise, is a defect. Early files earn the right to be simple; later files may
   assume everything before them.

The reader is a backend Java engineer with 3–4 years of experience. Assume
professional fluency in the language; assume nothing about this topic.

---

## How a concept is written

### Which concepts get the full treatment

**Sort first.** A **primary concept** satisfies any of: it carries a cost or
performance claim; it has a diagram in the manifest; it has an alternative it
must be chosen against; a reader could be asked about it for five minutes in an
interview. Primary concepts get **all eight beats, in order, under a `###`
heading**.

A **supporting fact** is everything else — a convenience method, a constant, a
flag nobody changes, a syntactic form with no tradeoff. Three beats only:
mechanism, gotcha if one exists, boxed definition. Three to ten lines, no
diagram, no separate heading, no manufactured analogy. Forcing eight beats onto a
one-line convenience produces exactly the filler the house rules ban.

Two to six primary concepts per file. More means it should have been split; zero
means it should have been folded. Both are map errors — fix them in `00-map.md`,
not in the prose.

### The eight beats

1. **Mental model first.** The picture: what shape this thing is, what it is
   doing underneath, the one analogy that makes the rest fall out. Never open
   with "X is a class in `java.util` that…" or "X is a specification that
   defines…".
2. **Why it exists** — the problem it solves, and what people did before it.
3. **When it applies, and when it does not.** Name the alternative that wins
   where this one loses: the sibling type, the other flag, the other model, the
   other technique.
4. **How it works** — the mechanism at this file's depth. In a deep file that is
   a source walk with real named fields and constants and their actual values; a
   bytecode listing; a phase sequence with its triggers; or the exact reordering
   the rule forbids. Never a restatement of the surface.
5. **The diagram, embedded inline in the flow** — `![caption](diagrams/D-NN-slug.svg)`,
   exactly the path handed to you, on **one line**,
   at the point the reader needs the picture: after the mechanism it illustrates,
   before the code. Never a gallery at the end, never "see diagram D-04". The
   caption says what to look at.
6. **A minimal concrete demonstration** — complete, runnable code from the
   QuizStakes domain. Full method bodies, real generics, real edge cases. Strip
   only imports, package lines, and empty `main` scaffolding. No `...`, no
   "implementation omitted", no pseudo-code. Where the concept is not expressible
   as a single snippet, the demonstration is the runnable command plus its real
   output — the `javap` listing, the GC log lines, the failing interleaving.
7. **The gotcha.**
8. **The definition, last** — one crisp sentence, boxed as a blockquote, now that
   the reader has earned it.

If a beat genuinely does not apply, say so in one line rather than dropping it
silently.

### The map before the streets

Any file that introduces a set of related things opens with the map — the type
hierarchy, the phase sequence, the layer diagram, the decision tree. A diagram
where the manifest has one, a table otherwise. Details never precede the shape
they sit in.

### Tradeoff, not fact

A bare capability claim is documentation. Notes state the claim, **its cost**, and
**the escape hatch**: the operation that is fast *but* is paid for elsewhere, the
guarantee that holds *but* only under a named condition, the flag that helps *but*
regresses something else, the technique that scales *but* turns over at a
threshold. If a claim has no stated cost, it is not finished.

### Tables for siblings

Three or more things doing a similar job get a comparison table, always. Never
three consecutive paragraphs describing them.

### Cost in place

State the cost **where the mechanism is explained**, next to the reason it holds —
complexity, pause time, allocation, startup overhead, whatever the shape's cost
actually is. A summary table in the cheat sheet is a recall aid, not the
explanation. A number with no named cause is not an answer.

### Callouts

Exactly three markers, bolded, inline where they belong:

- `**Pitfall:**` — the wrong belief, the symptom it produces, the fix.
- `**Insight:**` — the non-obvious mechanism that makes the rest click.
- `**Interview:**` — how this is actually asked, and the one-line answer.

### Version behaviour

Every file states its target version in the header. Any constant, default, API
shape, or behaviour that differs across versions is called out **inline at the
point of the claim**, naming which version does what. Where a widely-repeated
claim is version-stale, state what is true today, what used to be true, and flag
it as a version trap — interviewers still ask for the old form.

---

## Every file ends the same way

1. `## Pitfalls` — wrong-then-right, one entry each:

   ```
   ### <The wrong belief, stated as the thing people do>

   **Wrong**
   <code or configuration showing the belief in action, and the output,
    exception, or log line that surprises>

   **Right**
   <what actually gets the guarantee, and why>

   **Why people believe it:** <the plausible-sounding reason>
   ```

2. `## Cheat sheet` — a one-screen table, recallable at a glance. No prose.

3. `## Self-test` — 5 to 10 questions, answers folded below each:

   ```
   **Q3.** <a question whose answer is the mechanism, not a definition>

   <details><summary>Answer</summary>

   <the full answer, not a hint>

   </details>
   ```

### Header and footer

Header:

```
# <Topic> — <NN> <File theme>

**Target version: <version>.** | [Map](00-map.md)
Assumes: <prerequisite line>
Previous: [<file>](<path>) · Next: [<file>](<path>)
```

The first file omits `Previous:` and its `Assumes:` line reads
`Assumes: no prior knowledge of <topic>.` The last file omits `Next:`. Never link
a file that does not exist and never write `Previous: none` — the orchestrator
computes both ends and hands over the finished lines.

Footer:

```
---

**Questions answered:** <explicit ids>
**Sets up:** <the closing line>
**Diagrams included:** <D-NN, …>
**Target version:** <version>
**Lines:** <count>
```

**`**Lines:**` is orchestrator-owned.** A writer cannot know its own final count,
so it writes `0` on a **new** file and the orchestrator patches the real number
afterwards. On a **re-dispatch**, whatever number is already in the footer is the
orchestrator's patched value: leave it, or write the count you actually produced.
**Never reset an existing count to `0`** — that silently un-patches the footer,
and a re-dispatch late in the run is exactly when nobody looks again.

---

## Research protocol

Search when it changes the answer. Version-sensitive behaviour, API changes,
deprecations, current best practice, benchmark figures, any specific number —
verify rather than recall. Do not search stable fundamentals.

When research is still insufficient after searching, do not invent and do not
quietly soften the claim:

1. Mark it inline as `**Unverified:**` with what you could not confirm.
2. Record it in a `## Open questions` block at the foot of that file.
3. Surface it in your envelope's `unverified` line.

If a missing fact blocks a whole file, return `blocked` naming what is missing
and what would settle it. Every unblocked file still gets written.

---

## House rules

- No emojis. No filler — no "let's dive in", "great question", "in this section
  we will". Lead with content.
- **No line limit and no file-count limit.** Completeness beats brevity. Never
  truncate, never write "and so on", never defer a concept for space.
- **The notes are self-contained.** A reader with only this folder has everything.
  No "see `src/notes/detailed/…`" as a substitute for explaining something, and
  **no provenance or "sourced from" lines in the note bodies** — provenance lives
  in `00-map.md`'s source ledger and nowhere else. Cross-links *within* the set
  are encouraged.
- Markdown for every file. SVG for every diagram — **never inline `<svg>`**
  (GitHub and VS Code strip it) and **never ASCII art**.
- Java code is Java 21 idiomatic: records, pattern matching, `var` sparingly,
  modern Spring Boot 3.x.
- **Examples come from the QuizStakes domain**, `src/scenario/scenario.md` —
  never `Dog extends Animal`, `Foo`, `thread1`, or any other throwaway.
