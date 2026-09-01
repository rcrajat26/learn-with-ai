# VERBATIM style contract — from the notes-generator agent specification

Reproduced verbatim. This governs how a concept is written, the callout markers,
the research protocol and the house rules. Where the topic-21 prompt contract
(`writer-prompt-contract.md`) is more specific — the six-link concept chain, the
required header and footer, the required closing sections, the grounding repo —
**the prompt wins.** This file is the general style law underneath it.

---

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
house rules ban.

A note file carries **two to six primary concepts**. More than six means it should
have been split; zero means it should have been folded. Both are planning errors
— report them as `blocked` rather than adjusting the prose.

**Concepts do not straddle splits.** Choose split points at concept boundaries, so
the boxed definition always closes its concept in the same file.

### The eight beats

These are for primary concepts. They need not be labelled, but they must be
present and in this sequence. On topic 21 they are subsumed by the prompt's
mandatory six-link chain `Concept → Why it exists → How it works → SVG → Code →
Gotcha`; the beats below add the mental-model opening, the sibling comparison and
the boxed definition that the chain does not name.

1. **Mental model first.** Open with the picture: what shape this thing is, what
   it is doing under the hood, the one analogy that makes the rest fall out. Not
   a definition. Never open with "X is a class in `java.util` that…".
2. **Why it exists** — the problem it solves, and what people did before it.
3. **When to reach for it, and when not.** Explicit. Name the sibling that wins
   in the cases where this one loses.
4. **How it works** — the mechanism, at the depth the tier demands.
5. **The diagram, embedded inline in the flow.** The `D-NN` from the manifest,
   embedded with `![caption](../diagrams/D-NN-slug.svg)` at the point in the
   explanation where the reader needs the picture — immediately after the
   mechanism it illustrates, before the code. Never collected into a gallery at
   the end of a file, never pushed to an appendix, never merely linked as "see
   diagram D-07". The caption states what to look at.
6. **A minimal concrete example** — real, complete, runnable code. Full method
   bodies, real generics, real edge cases. Strip only imports, package lines, and
   empty `main` scaffolding. No `...`, no "implementation omitted", no
   pseudo-code.
7. **The gotcha.**
8. **The definition, last** — one crisp sentence, boxed as a blockquote, now
   that the reader has earned it.

If a beat genuinely does not apply, say so in one line rather than dropping it
silently.

### Hierarchy before details

Every file that introduces a family opens with the hierarchy — as a diagram where
one is in the manifest, as a table otherwise. The reader sees the map before the
streets.

### Tradeoff, not fact

A bare capability statement is documentation. Notes state the capability, **but**
its cost, **and** the condition under which it degrades — which is precisely why
the sibling mechanism still earns its place. Every performance or cost claim
carries its cost and its escape hatch.

### Tables for siblings

Three or more things doing a similar job get a comparison table, always. Never
three paragraphs describing them one after another.

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

## Research protocol

Search when it changes the answer:

- **Search:** version-sensitive behaviour, API changes and deprecations, current
  best practice, library and runtime versions, benchmark figures, anything where
  a specific number appears in the notes. Verify rather than recall.
- **Do not search:** stable fundamentals.

State the version the notes target near the top of every file, and flag
behaviour that differs across versions inline.

**When research is still insufficient after searching**, do not invent and do
not quietly soften the claim. Instead:

1. Mark the claim inline as `**Unverified:**` with what you could not confirm.
2. Record it in a `## Open questions` block at the foot of that file.
3. Surface every one of them in your return envelope.

If a missing fact blocks a whole file — the section cannot be written honestly
without it — **do not write that file**. Return it as `blocked` in the envelope,
naming what is missing and what would settle it.

---

## House rules

- No emojis. No filler — no "let's dive in", "great question", "in this section
  we will". Lead with content.
- **No line limit and no file-count limit.** Completeness beats brevity every
  time. Never truncate, never write "and so on", never defer a concept for
  space.
- Markdown (`.md`) for every file. SVG for every diagram.
- Java code is Java 21 idiomatic: records, pattern matching, `var` sparingly,
  modern Spring Boot 3.x.
- Every syllabus leaf in your packet appears in the file, or in a `## Deferred`
  block with a reason.

---

## Your return envelope

Return only this, nothing else:

```
path: <relative path written>
lines: <wc -l>
leaves: <ids covered>
diagrams: <D-NN embedded>
unverified: <none | one line per unverified claim>
blocked: <none | what is missing and what would settle it>
```
