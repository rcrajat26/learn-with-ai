#!/usr/bin/env python3
"""Builds one self-contained writer packet per note file."""
import json, os, re

ROOT = "/Users/rajat.chikkodikar/Desktop/My-files/rough"
PROMPT = f"{ROOT}/src/metadata/prompts/04-modern-java-prompt.md"
TOPIC = f"{ROOT}/src/notes/detailed/04-modern-java"
OUTDIR = f"{ROOT}/tmp/packets"
os.makedirs(OUTDIR, exist_ok=True)

lines = open(PROMPT).read().split('\n')
P = json.load(open('/tmp/plan2.json'))
plan, diag = P['plan'], P['diag']
secs = json.load(open('/tmp/secs.json'))
svgnames = json.load(open('/tmp/svgnames.json'))

writing = open(f"{ROOT}/tmp/spec-writing.md").read()
domain = open(f"{ROOT}/tmp/spec-domain.md").read()
verified = open(f"{ROOT}/tmp/spec-verified.md").read()
jdknote = open('/tmp/jdknote.md').read()

# ---- actual on-disk svg filenames, incl. frame splits ----
disk = sorted(os.listdir(f"{TOPIC}/diagrams"))
files_for = {}
for f in disk:
    m = re.match(r'(D-\d{3})([a-z]?)-', f)
    if m and f.endswith('.svg'):
        files_for.setdefault(m.group(1), []).append(f)
for k in files_for:
    files_for[k].sort()

# ---- verbatim leaf text, per section, keyed by leaf id ----
leaftext = {}
cur = None
buf = None
for l in lines[505:2760]:
    m = re.match(r'^## §(\d+\.\d+)', l)
    if m:
        cur = m.group(1)
    m2 = re.match(r'^(\d+\.\d+\.\d+) ', l)
    if m2:
        buf = m2.group(1)
        leaftext[buf] = [l]
        continue
    if buf is not None:
        if re.match(r'^\s+\S', l):
            leaftext[buf].append(l)
        else:
            buf = None
leaftext = {k: '\n'.join(v).rstrip() for k, v in leaftext.items()}

# ---- part-level requirements from the prompt, for the 9x files ----
PART_REQ = """**Every part ends with all three of these, and this file is where its part's three live:**

1. a **summary table** covering that part's concepts,
2. **10 interview Q&As** with full model answers — not hints, the answer a candidate would
   actually say out loud, at speaking length,
3. **5 "predict the output" puzzles** — a complete code snippet, the actual output, and an
   explanation of *why* the output is what it is.

They must cover the **whole part**, across every subject folder in it, not one subject."""

# ---- example-domain reading-order pointers per subject ----
def hdr_title(p):
    subj = {
        'platform-and-releases': 'The platform and the release model',
        'functional-interfaces': 'Functional interfaces',
        'lambdas': 'Lambdas',
        'method-references': 'Method references',
        'streams': 'Streams',
        'collectors': 'Collectors',
        'optional': '`Optional`',
        'var': '`var`',
        'records': 'Records',
        'sealed-types': 'Sealed types',
        'pattern-matching': 'Pattern matching',
        'switch': '`switch`',
        'text-blocks': 'Text blocks',
        'virtual-threads': 'Virtual threads',
        'structured-concurrency': 'Structured concurrency',
        'library-additions': 'The library additions, 9 to 21',
        'cost-model': 'The master tables',
        'which-construct': 'Which construct',
        'build-it': 'Build it',
    }
    if '/' in p['file']:
        return subj.get(p['file'].split('/')[0], p['subject'])
    return {
        '90-interview-basics.md': 'Part 1 wrap-up — basics',
        '91-interview-intermediate.md': 'Part 2 wrap-up — intermediate',
        '92-interview-internals.md': 'Part 3 wrap-up — internals',
        '93-interview-build-it.md': 'Part 4 wrap-up — build it',
        '94-interview-questions-a.md': 'The 95 questions, part A',
        '94-interview-questions-b.md': 'The 95 questions, part B',
        '94-interview-questions-c.md': 'The 95 questions, part C',
        '95-traps-drills-and-checklist.md': 'Traps, drills and the checklist',
    }[p['file']]

def theme(p):
    f = p['file'].split('/')[-1]
    t = re.sub(r'^\d+-', '', f).replace('.md', '').replace('-', ' ')
    return t

byfile = {p['file']: p for p in plan}
idx = {p['file']: i for i, p in enumerate(plan)}

written = []
for i, p in enumerate(plan):
    f = p['file']
    depth = '../' if '/' in f else ''
    # nav
    nav = []
    if p['prev']:
        nav.append(f"Previous: [{hdr_title(byfile[p['prev']])} — {theme(byfile[p['prev']])}]({p['prevlink']})")
    if p['next']:
        nav.append(f"Next: [{hdr_title(byfile[p['next']])} — {theme(byfile[p['next']])}]({p['nextlink']})")
    navline = ' · '.join(nav)
    secnames = ', '.join('§' + s for s in p['secs'])
    header = (f"# 04 Modern Java — {hdr_title(p)} — {p['tier']} ({secnames})\n\n"
              f"**Target version: Java 21 LTS.** | **Part {p['part']} of 5** | "
              f"[Index]({p['indexlink']})\n{navline}")

    # diagrams
    dblocks = []
    for did in p['diagrams']:
        x = diag[did]
        fl = files_for.get(did, [])
        if x['type'] == 'table':
            dblocks.append(
                f"- **{did} — {x['title']}** · type `table` · **render this as a Markdown table in "
                f"your prose, at the point of explanation. There is no SVG and you must not create "
                f"one.** Caption the table `**{did}** — {x['title']}` on the line beneath it. It "
                f"must contain every row, column and value named here: {x['must']}")
        else:
            embeds = '\n'.join(
                f"    ![{did} — {x['title']}]({depth}diagrams/{fn})" for fn in fl)
            frame = (f" · authored as **{len(fl)} frame files**, and you must embed **all of them, "
                     f"in order**, each with its own caption line naming the frame"
                     if len(fl) > 1 else "")
            dblocks.append(
                f"- **{did} — {x['title']}** · type `{x['type']}`{frame} · the file(s) already "
                f"exist; embed exactly:\n{embeds}\n"
                f"  Beneath each embed put the caption line `**{did}** — {x['title']}`. The diagram "
                f"shows: {x['must']}")
    dsection = '\n'.join(dblocks) if dblocks else ("- None. This file carries no diagram from the "
                                                   "manifest. Do not invent one, do not embed one "
                                                   "belonging to another file, and do not draw with "
                                                   "ASCII characters. Where you need a visual, a "
                                                   "Markdown table is the correct substitute.")

    # leaves
    if p['leafids']:
        lt = '\n\n'.join(leaftext[i2] for i2 in p['leafids'])
        leafsec = (f"These are the **{p['nleaves']} syllabus leaves you own**, verbatim, in order. "
                   f"Every one must appear in the file, or be listed in `## Deferred` with a "
                   f"one-line reason. No other file covers them; no other file's leaves are "
                   f"yours.\n\n```\n{lt}\n```")
    else:
        leafsec = ("This file owns **no syllabus leaves of its own**. It is a part wrap-up: it "
                   "summarises its whole part and adds that part's Q&As and puzzles. Its footer "
                   "reads `**Leaves covered:** none — part wrap-up (0 leaves)`.")

    extra = PART_REQ if (f[0] == '9' and f < '94') or f == '95-traps-drills-and-checklist.md' else ''
    if f == '95-traps-drills-and-checklist.md':
        extra += ("\n\n**This is the last file of the entire set.** It must end with a flat "
                  "`## Atomic concept checklist`: one bullet per distinct concept across all five "
                  "parts, in the format `- <concept name>` exactly — no nesting, no sub-bullets, no "
                  "trailing punctuation, no parentheticals, no headings inside it. Downstream "
                  "agents parse this list. Sort it by subject in the order the file plan runs, then "
                  "by the order the concept appears within that subject. Leaf 5.3.9 asks you to "
                  "preserve the 25 checklist lines of the previous guide in substance and add one "
                  "line per new concept in this syllabus; you do not have that previous guide, so "
                  "derive the checklist from this syllabus in full and note in your envelope that "
                  "the earlier 25 lines were reconstructed from the syllabus rather than copied.")
    if f == '92-interview-internals.md':
        extra += ("\n\nAdd, as the final line of this file, a single pointer sentence: the flat "
                  "`## Atomic concept checklist` for the whole set lives at the end of "
                  "`95-traps-drills-and-checklist.md`. Do **not** reproduce the checklist here.")
    if f.startswith('94-interview-questions'):
        extra += ("\n\nEach of your leaves is one interview question. Answer **every one** with the "
                  "answer shape a candidate would actually say out loud — the 60-to-90-second "
                  "spoken answer, not a hint and not a bullet list of API names. Structure each as: "
                  "`### <question, verbatim from the leaf>`, then the spoken answer, then a "
                  "`**Interview:**` line giving the one-sentence version for when time is short. "
                  "Where a question has a 30-second and a 5-minute answer, give both and label "
                  "them. This file's `## Self-test` section is still required and is separate from "
                  "the questions themselves — use it for the traps the questions did not cover.")
    if 'build-it' in f:
        extra += ("\n\nEvery item in Part 4 is `[BUILD]`: complete, compiling, generic Java 21. "
                  "**Each build ends with a \"Diff vs the real one\" table** covering at minimum "
                  "edge cases, intrinsics, serialization, null policy, thread safety, allocation "
                  "tricks, and why the JDK bothers.")
    if f == 'streams/09-internals-spliterator.md':
        extra += ("\n\nOne consistency note: your diagram **D-136**'s inset works the "
                  "`suggestTargetSize` arithmetic on an illustrative 5-core machine "
                  "(`LEAF_TARGET = 4 << 2 = 16`, target 5,937), and says so on its face. The rest "
                  "of this note set uses the 8-core convention in the verified-figures block "
                  "(parallelism 7, `LEAF_TARGET` 28). Say in prose that the diagram's inset is a "
                  "5-core illustration and give the 8-core figures as the set's default, so the two "
                  "never look like a contradiction.")

    body = f"""# Writer packet — `{f}`

You are writing **exactly one Markdown file** in a study-note set on Modern Java (Java 8 → 21),
for a backend Java engineer with 3–4 years' experience preparing for a senior/FAANG-level
interview loop. This packet is your complete brief. You need nothing else, with one exception:
`{ROOT}/src/scenario/scenario.md` is read-only shared domain reference you may open for detail
beyond what is pasted below.

## The file you write

```
{TOPIC}/{f}
```

Create that file and nothing else. Do not read, edit or create any other file in the notes tree.

## Your row from the file plan, verbatim

| Field | Value |
|---|---|
| File | `{f}` |
| Subject | {p['subject']} |
| Part / tier | Part {p['part']} — {p['tier']} |
| Syllabus sections | {secnames} — {', '.join(secs[s]['title'] for s in p['secs'] if s in secs)} |
| Leaves | {p['range']} ({p['nleaves']} leaves) |
| Primary concepts | {p['concepts']} |
| Diagrams | {', '.join(p['diagrams']) if p['diagrams'] else '—'} |
| Examples (QuizStakes slice) | {p['examples']} |
| Previous | {'`' + p['prev'] + '`' if p['prev'] else '— this is the first file of the set'} |
| Next | {'`' + p['next'] + '`' if p['next'] else '— this is the last file of the set'} |
| Target size | **{p['est2']} lines**, and anything from {int(p['est2']*0.7)} to {int(p['est2']*1.35)} is fine |

**Target size is a shape, not a budget, and completeness always wins.** Write what the leaves
need at the depth their tags demand. Do not compress, do not thin, do not drop a beat to hit a
number.

The mandatory per-file sections (`## Pitfalls` written wrong-then-right with real code, the cheat
sheet, 5–10 self-test questions with full answers) plus the eight-beat treatment of each primary
concept carry a large fixed cost, so a complete file in this set runs long by ordinary
note-writing standards — measured files in this set land between 770 and 1,600 lines. That is
expected and correct here, and the orchestrator has already accepted it.

**Do not return `blocked` because of length.** Length is not a defect in this set and a re-split
would only duplicate the per-file boilerplate. Write the file to completion at whatever length the
leaves need, and simply report the real `wc -l` in your envelope. Reserve `blocked` for what it is
actually for: a fact you cannot verify that makes the file impossible to write honestly.

## The header and nav line — use this verbatim as the first three lines of the file

```
{header}
```

## Your reader

Assume they already know, without re-teaching: how to write a lambda and a method reference; how
to call `stream().filter(...).map(...).collect(Collectors.toList())`; what `Optional.get()` does;
how to declare a record and a sealed interface; the arrow form of `switch`; that text blocks use
`\"\"\"`; that virtual threads exist and are "cheap"; generics syntax and the diamond;
`equals`/`hashCode`; big-O notation; the collections API surface.

Assume they do **not** have the mechanism-level model underneath any of it, and that they have
absorbed version-stale folklore from blogs written between 2019 and 2023. Closing that gap is the
entire reason these notes exist. Teach **mechanism, not usage**: "streams are lazy" is not an
explanation; "each intermediate operation allocates one `AbstractPipeline` stage linked to the
previous one and contributes an `opWrapSink`; nothing traverses until `evaluate(TerminalOp)` calls
`wrapSink` backwards from the terminal stage and then `copyInto`, which is why a pipeline with no
terminal operation does literally nothing" is.

Authority order for every claim: **JLS/JVMS > OpenJDK source at the release tag > JDK javadoc >
JEP text > the JDK bug database and OpenJDK mailing lists > engineer blog posts.** Never state a
blog claim as fact when the specification says otherwise.

## Your syllabus leaves

{leafsec}

## Your diagrams

Every id below is already authored and on disk. Embed each at the point of explanation — never in
a gallery at the end, never as "see diagram D-NNN".

{dsection}

{extra}

---

{writing}

---

{domain}

---

{verified}

{jdknote}

---

## Return only this envelope

```
path: {f}
lines: <wc -l of the file you wrote>
leaves: {p['range']}
diagrams: <the D-NNN ids you embedded>
unverified: <none | one line per **Unverified:** claim in the file>
blocked: <none | what is missing and what would settle it>
```

Nothing else. No narration, no summary of what you wrote.
"""
    name = 'wr-%02d' % (i + 1)
    open(f"{OUTDIR}/{name}.md", 'w').write(body)
    written.append((name, f, p['est'], len(p['diagrams'])))

json.dump({n: f for n, f, _, _ in written}, open('/tmp/wr_batches.json', 'w'), indent=0)
print(f"wrote {len(written)} writer packets")
for n, f, e, dd in written:
    print(f"{n}  {f:52s} est={e} D={dd}")
