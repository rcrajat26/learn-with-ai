# Writer packet — topic 21 (AI for Coding / Claude Code)

You write **exactly one file** and nothing else. You do not touch `00-index.md`. You do not create
any other file. You do not write to any other note file in the set.

## Read these two contract files first, in full

1. `/Users/rajat.chikkodikar/Desktop/My-files/rough/tmp/21-contract/writer-prompt-contract.md` — the
   verbatim ROLE, CONTEXT, TASK, hard instructions, tag obligations, required header, required
   footer and required closing sections from the source prompt. **Binding in every particular.**
2. `/Users/rajat.chikkodikar/Desktop/My-files/rough/tmp/21-contract/writer-style.md` — the verbatim
   style law: how a concept is written, the three callout markers, the research protocol, the house
   rules.

Your dispatch then names a third file under
`/Users/rajat.chikkodikar/Desktop/My-files/rough/tmp/21-contract/leaves/` holding **your leaves,
verbatim**. That file contains ONLY the leaves you own. Cover every one of them. Do not cover a leaf
that is not in it. Do not renumber them.

### The leaf file wins

Your dispatch also summarises each leaf's obligations. **That summary is a convenience, not the
scope.** Where the dispatch's description of a leaf disagrees with the leaf's own verbatim text in
your leaf file — a different tag, a different subject, a different artefact — **the leaf file is
authoritative. Follow it, cover the leaf as written, and say in your envelope that the two
disagreed and which you followed.**

This has already happened once on this run and cost a leaf its coverage, so it is not hypothetical.
Read your leaf file before you plan the file, not after. If a leaf is tagged `[BUILD]` in the leaf
file, it ships an artefact plus a prove step plus a cost note, whatever the dispatch called it.

## The concept chain — every concept, in this order

`Concept → Why it exists → How it works → SVG → Code → Gotcha`

All six links. "Code" means the real artefact the concept lives in: a settings JSON block, a
`hooks.json` fragment, a `SKILL.md` with its frontmatter, an agent definition, a shell script, a
`claude` invocation with its flags, a Java class, or a quoted sdlc-harness file. If a link genuinely
does not apply, say so in one line ("No gotcha: the rule has no surprising edge.") rather than
silently dropping it.

Primary concepts additionally open with the mental model rather than a definition, and close with a
one-sentence definition boxed as a blockquote. Supporting facts get three beats only — mechanism,
gotcha if one exists, definition — in three to ten lines.

## Code is complete and runnable as written

- **JSON** (settings, `hooks.json`, `plugin.json`, `marketplace.json`, `.mcp.json`) — valid,
  parseable, complete objects with the surrounding keys present. Never a fragment with an implied
  parent. JSON does not support comments; put the explanation in the prose beside the block, never
  inside it.
- **Markdown artefacts** (`SKILL.md`, agent definitions, command files) — the frontmatter fences and
  every field shown, then a real body.
- **Shell** — a complete script with its shebang, its failure posture (`set -e`, or the deliberate
  `set +e` with `exit 0`), and real `jq` over stdin where the event supplies JSON.
- **Java** — full class and method bodies, real field names, real generics, real exception types,
  real edge cases. Strip only `import` statements, `package` declarations and pointless `main`
  scaffolding. Java 21 idiomatic: records, sealed interfaces, pattern-matching `switch`, text
  blocks, `var` sparingly, `ProcessBuilder`, `Process.waitFor(Duration)`, virtual threads where they
  fit.
- **`claude` invocations** — the full command line with every flag it needs, never an abbreviated
  form with the interesting flags omitted.

**No `...` elisions, no "implementation omitted", no pseudo-code standing in for real code.** Quoted
sdlc-harness files and quoted documentation may be excerpted to the relevant lines, but every line
quoted must then be explained.

## Callouts — exactly these three, and no others

- `**Pitfall:**` — the wrong belief, the symptom it produces, the fix.
- `**Insight:**` — the non-obvious mechanism that makes the rest click.
- `**Interview:**` — how this is actually asked, and the one-line answer.

## Tag obligations

- `[ZERO]` — assume no prior knowledge whatsoever. Define every term used in the leaf, in the leaf.
- `[DOC]` — quote the official documentation (short excerpt) and cite the page by name. **Re-verify
  it with WebFetch against `https://code.claude.com/docs/en/` immediately before you write the
  leaf.** You have WebFetch. Use it. The pages are `settings`, `settings-reference`, `permissions`,
  `hooks`, `sub-agents`, `skills`, `memory`, `plugins`, `cli-reference`. Do not invent a
  documentation URL outside that set.
- `[CASE]` — ground it in the real sdlc-harness repo with a real file path and a real **verbatim**
  quote in a fenced block, then explain it. See the grounding section below.
- `[BUILD]` — ship a complete, working artefact the reader can copy and run, **then a prove step**
  (the command that demonstrates it fired, and its output), **then a "what this costs" note** in
  tokens or dollars. All three parts.
- `[PROVE]` — work the argument through on the page, or show the observed result. Do not state the
  conclusion and move on. Where the leaf asks for arithmetic, **print the arithmetic**.
- `[TRAP]` — carry a `**Pitfall:**` marker: wrong belief, symptom, fix.
- `[INCIDENT]` — name **what broke, what it cost as a number, and the fix**, then state the general
  law it establishes. Never "significant" where the syllabus gives a figure.
- `[NUM]` — state the number, limit or arithmetic explicitly.
- `[VERSION]` — state the version inline, at the point of the claim, not in a footnote.
- `[RESEARCH]` — re-verify against the cited source immediately before writing; this area drifts.
- `[JAVA]` — land it in the reader's own language: a precise Java 21 / Spring Boot 3.x analogy
  **with the place it breaks stated**, or real compiling Java code. "It is like a REST controller"
  is not enough.

Where you cannot verify a claim after searching, mark it inline as `**Unverified:**` with what you
could not confirm and record it in `## Open questions`. **Do not invent and do not quietly soften.**
If a missing fact blocks the whole file, return `blocked` rather than writing it.

## Target version

**Claude Code v2.1.2xx (August 2026)** is the baseline for every flag, settings key, hook event,
frontmatter field and numeric limit. This subject moves faster than the JDK: a field added in
v2.1.218 and a field removed in v2.1.234 both exist in the same release line. Where a
widely-repeated claim is version-stale, state what is true in v2.1.2xx **and** what used to be true,
and flag it as a version trap — interviewers and colleagues still ask for the old form.

## Grounding — this topic is NOT QuizStakes

There is no QuizStakes in this topic. **Ignore any instruction anywhere in this pipeline that says
every example comes from a betting-platform domain.** It does not apply here.

Your grounding domain is Claude Code itself and, for `[CASE]` leaves, the real **sdlc-harness**
repository at:

```
/Users/rajat.chikkodikar/Desktop/My-files/Codes/_non-clinet-tech/sdlc-harness
```

**That repository is READ-ONLY. Never write to it, never edit it, never create a file inside it, and
never run anything that mutates it.** You may Read and Grep it freely.

Rules for a `[CASE]` leaf, all mandatory:

- **Cite a file path.** Repo-relative is fine in the prose; the absolute path above is the root it
  resolves against.
- **Quote the real text, verbatim, in a fenced block.** Never paraphrase a `[CASE]` quote, never
  reconstruct it from memory, never clean it up. If the real text is 30 lines and complete, quote
  all 30.
- **Read the file before you quote it.** A quote you did not read is a fabrication, and the reader
  has the repo open beside you.
- **Then explain it.** Name the design property; name what would break without it.
- **If a file named in a leaf does not exist, or does not say what the leaf claims, do not invent
  it.** Write what the file actually says, note the divergence inline, and if the leaf is
  unsatisfiable mark it `**Unverified:**` and record it in `## Open questions`.

**Banned everywhere — prose, code, JSON, shell, frontmatter, Java, diagram captions:** `Foo`, `Bar`,
`Baz`, `my-agent`, `my-skill`, `thing1`, `thing2`, `MyClass`, `doSomething`, `test-agent`,
`example-hook`, `Dog extends Animal`. A throwaway name is a defect, not a style choice. Where a leaf
needs an artefact the harness does not have, name it for what it does in a real repository:
`format-on-edit.sh`, `block-destructive-bash.sh`, `branch-context.sh`, `mvn-test-runner`,
`readonly-reviewer`, `ClaudeRunner`, `ClaudeEnvelope`, `AgentTimeoutException`, `checklist-refresh`.

## Diagrams

Your dispatch names your diagram ids, their exact filenames and where they belong. Embed each with a
Markdown image reference and a caption carrying the stable id, **at the point of explanation** —
immediately after the mechanism it illustrates and before the code. Never collect them at the end of
the file, never push them to an appendix, never merely write "see diagram D-28".

```
![D-28 — Permission evaluation: deny, then ask, then allow](../diagrams/D-28-permission-evaluation-order.svg)

**D-28** — Permission evaluation: `deny`, then `ask`, then `allow`; first match wins.
```

The SVG files named in your dispatch **already exist**; those paths resolve. Do not author an SVG,
do not modify one, and **never inline `<svg>` into the Markdown** — GitHub strips it and VS Code
sanitizes it away. **Never use ASCII art.**

Where your dispatch marks an id as `Type: table`, render a **Markdown table** in the prose at the
point the diagram would have gone. Write no SVG for it, but **the `D-NN` id must still appear at
that point** — put it in a bold caption line under the table — so the id is accounted for.

Files in a subject subfolder reach the diagrams with `../diagrams/…`. Files at the topic root
(`90`–`95`) use `diagrams/…`.

## Size

Target **250–450 lines**. **600 is a hard ceiling, not a target.** If you find yourself heading past
500 with leaves still uncovered, **stop and return `blocked` asking for a re-split, naming the
natural concept boundary.** Do not compress to fit, do not cut a concept, do not trim a `[PROVE]`
walk to its conclusion, do not drop a `[BUILD]` cost note, do not write "and so on" or "similar to
the above". Landing exactly on 600 is treated as evidence of compression and the row gets re-split
anyway, so blocking early is cheaper for everyone.

## House rules

No emojis. No filler openers — no "let's dive in", "great question", "it's worth noting", "as we all
know". Lead with content. A table for any comparison of three or more things.

## Closing sections — in this order, before the footer

1. `## Pitfalls` — wrong-then-right, one entry per pitfall: the belief in action and the surprising
   outcome, then the configuration or command that actually gets the guarantee, then
   **Why people believe it:**.
2. `## Cheat sheet` — a one-screen table, recallable at a glance. No prose.
3. `## Self-test` — 5 to 10 questions, each answer folded below it in a
   `<details><summary>Answer</summary>` block, with the full answer rather than a hint.
4. `## Open questions` — every claim you marked `**Unverified:**` in the body, or the single line
   `None.`
5. The footer your dispatch gives you.

## Return only this envelope, nothing else

```
path: <relative path written>
lines: <wc -l>
leaves: <ids covered>
diagrams: <D-NN embedded>
unverified: <none | one line per unverified claim>
blocked: <none | what is missing and what would settle it>
```
