# Illustrator packet — topic 21 (AI for Coding / Claude Code)

You author SVG diagrams only. You write nothing else. You do not touch any `.md` file in the note
set.

## Your authoritative style contract — read this file first, in full

`/Users/rajat.chikkodikar/Desktop/My-files/rough/tmp/21-contract/diagram-spec.md`

That file is the verbatim `## Diagram spec` from the notes-generator agent specification. It is
binding in every particular: `viewBox` with no `width`/`height`, the opaque backdrop rect as the
first element, orthogonal-only edge routing (no diagonals, no Béziers, no arcs), the exact palette
values, the required title / band headers / legend furniture, the 10.5px text floor, no off-file
style dependency, and the render-and-look self-check. Do not improvise a colour.

## Your manifest rows

Your dispatch names one batch file under
`/Users/rajat.chikkodikar/Desktop/My-files/rough/tmp/21-contract/batches/`. Read it. It holds four
rows in the columns `# | Diagram | Syllabus leaf | Type | Must show`.

**Every label, constant, key name and value named in a row's `Must show` cell must be visibly
present as text in that SVG.** A diagram that omits a named value does not satisfy the manifest.
Where a row asks for arithmetic, the arithmetic is written on the canvas as a sum, not just its
result.

## Output

Write to:
`/Users/rajat.chikkodikar/Desktop/My-files/rough/src/notes/detailed/21-ai-for-coding/diagrams/`

Filenames: `D-NN-short-slug.svg`, lowercase kebab slug. Write only into that `diagrams/` directory.
Create nothing anywhere else, and leave no scratch file there.

## Labelling rule for this topic — this topic is NOT QuizStakes

Labels name the real subject matter of Claude Code and of the real sdlc-harness repository:
`permissions.deny`, `permissions.allow`, `PreToolUse`, `PostToolUse`, `SessionStart`, `Stop`,
`settings.json`, `settings.local.json`, `CLAUDE.md`, `.claude/rules/`, `SKILL.md`,
`allowed-tools`, `disallowed-tools`, `hooks.json`, `plugin.json`, `marketplace.json`,
`${CLAUDE_PLUGIN_ROOT}`, `check-init.sh`, `prod-guard-bash.sh`, `bootstrap-uv.sh`,
`progress-verifier.md`, `agent.py`, `claude -p`, `--output-format json`, `--max-turns`,
`--setting-sources`, `ClaudeRunner`, `ClaudeEnvelope`, `DEFAULT_MAX_TURNS = 160`,
`DEFAULT_TIMEOUT = 1800`, `claude-opus-5`, `claude-haiku-4-5-20251001`.

**Banned in every label, without exception:** `Foo`, `Bar`, `Baz`, `my-agent`, `my-skill`,
`thing1`, `thing2`, `MyClass`, `doSomething`, `test-agent`, `example-hook`, `hook1`, `Node A`,
`Dog extends Animal`. A throwaway name in a diagram label is a defect, not a style choice.

Escape `<`, `>` and `&` in SVG text as `&lt;` `&gt;` `&amp;` or the file will not parse. Beware
`--` inside an XML comment: it is invalid and will fail to parse.

## Frames

Where a row's `Type` says `step-sequence, N frames`, or the `Must show` cell asks for frames, author
each frame as its own file (`D-31a-…svg`, `D-31b-…svg`, …) **or** as that many clearly separated,
individually labelled panels inside one SVG. Either is acceptable. Report every id you produced.

## Mandatory self-check before you return

For every SVG you wrote, render into the scratch directory — **never into `diagrams/`**:

```bash
qlmanage -t -s 1400 -o /Users/rajat.chikkodikar/Desktop/My-files/rough/tmp/21-render /Users/rajat.chikkodikar/Desktop/My-files/rough/src/notes/detailed/21-ai-for-coding/diagrams/D-NN-slug.svg
```

Then open the resulting `.png` in `tmp/21-render/` with the Read tool and **look at it**. Check: no
text crosses or escapes its box; no box overlaps another box; no edge passes under a box and no two
edges overlay; zero line crossings (or exactly one, reported); every arrowhead lands on a box
border; every legend entry is used and every style used is in the legend; every `Must show` item is
visibly present. Fix and re-render until it passes.

Leave the PNGs in `tmp/21-render/`. **`rm` is denied in this session** — do not attempt to delete
them, and do not write them into `diagrams/`.

A diagram you did not render and look at is not done. If you genuinely could not render, say so in
your envelope's `unverified` line.

## Return only this envelope, nothing else

```
diagrams: <every D-NN id you produced, with its filename>
rendered: <yes | no, with the reason>
unverified: <none | one line per issue you could not fix>
blocked: <none | which D-NN is not renderable as a picture and why>
```
