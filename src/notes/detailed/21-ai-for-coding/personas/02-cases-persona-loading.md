# 21 AI for Coding — how a real engine loads a persona — INTERMEDIATE (§2.2.5–2.2.7)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 2 of 6** | [Index](../00-index.md)
Previous: [four ways to set a persona](01-the-four-flags.md) · Next: [what a hook is](../hooks/01-basics-what-a-hook-is.md)

The previous file compared `--agent`, `--append-system-prompt`, `--system-prompt` /
`--system-prompt-file`, and `--append-subagent-system-prompt` against each other in the abstract, and
named the failure mode that makes picking the wrong one dangerous: a session that *behaves* almost
right while carrying no actual tool ceiling. This file does not re-run that comparison. It grounds it
in one real file from the sdlc-harness — `harness/src/harness/engine/agent.py`, the module that
spawns every `claude -p` subprocess the engine ever runs — and shows the engine choosing correctly
between the four, on purpose, in code a reader can point at.

Repository root for every path below:
`/Users/rajat.chikkodikar/Desktop/My-files/Codes/_non-clinet-tech/sdlc-harness`. The repository is
read-only for this note; nothing here was written to it.

## §2.2.5 [CASE] The engine's own choice: `--agent`, not `--append-system-prompt`

**Mental model.** `agent.py`'s job is to turn a Python function call into exactly one `claude -p`
subprocess invocation and one parsed result. Every keyword argument the caller passes — `persona`,
`system_prompt`, `model`, `effort` — becomes zero or more elements appended to a `List[str]` that
`subprocess.run` executes. Reading the function is reading the CLI invocation before it is built.

**Why it exists.** The engine dispatches many distinct roles across a pipeline run — a coder, a
reviewer, a progress-verifier, a calibrator — each needing its own fixed identity and its own tool
ceiling, run unattended with nobody at a keyboard to notice if a restriction silently failed to
apply. That is precisely the case the previous file named as `--agent`'s reason to exist: a fixed,
reusable, restricted persona that needs the same tool ceiling every time it runs inside a pipeline.

**How it works.** The module's own docstring states the design decision in one sentence, before any
code:

```python
Persona parity: `--agent <name>` loads a *registered* agent (from
~/.claude/agents/`) with its own system prompt, tools, and model — this is
the parity mechanism for an auto-spawned subagent, not `--append-system-prompt`
(which only appends to the default prompt). `--setting-sources` restores
file-based skills to an otherwise-isolated `-p` invocation.
```

"Parity" is the word doing the work: when the loop needs a manually-spawned `claude -p` process to
behave like the *same* role an auto-spawned subagent would have taken on inside an interactive
session, the only flag that reproduces that — system prompt, tools, and model all sourced from one
registered definition — is `--agent`. The docstring rules out `--append-system-prompt` by name,
for the exact reason file 01 gave it no tool allowlist: it "only appends to the default prompt."

`run_agent`'s own parameter docstring repeats the same distinction at the call site, one paragraph
each for the two flags it can emit:

```python
    `persona` (when given) loads a registered agent via `--agent` — the parity
    mechanism for an auto-spawned subagent's identity, tools, and model.
    `system_prompt` (when non-empty) is appended as EXTRA run context via
    `--append-system-prompt`, not a substitute for `persona`.
```

And the command assembly itself keeps the two on separate branches, never merged into one string:

```python
    cmd: List[str] = ["claude", "-p", task]
    if persona:
        cmd += ["--agent", persona]
    cmd += ["--output-format", "json"]
```

```python
    if system_prompt:
        cmd += ["--append-system-prompt", system_prompt]
```

**Code.** `run_agent`'s signature has both `persona: Optional[str] = None` and
`system_prompt: str = ""` as two distinct keyword parameters — not one `persona_text: str` that gets
routed to whichever flag looked convenient. A caller wanting a tool ceiling has to reach for
`persona`; there is no path through this function's argument list that lets a plain string bought
into `system_prompt` produce a `tools:` restriction, because `system_prompt` is wired to
`--append-system-prompt` and nothing else. The type signature enforces, at the Python level, the same
distinction file 01's table drew between the two flags: a `str` can only ever become decoration, a
persona name can only ever become a full identity swap with an enforced allowlist.

**Gotcha.** The parity the docstring names is real but partial: `--agent <name>` resolves the named
agent from `~/.claude/agents/` (or a project/plugin equivalent) via the `claude` binary's own
resolution, not via `agent.py`. If the name does not resolve to a registered definition on the
machine running the subprocess, the failure surfaces from the subprocess's stderr and stdout, not
from Python — `run_agent` has no pre-flight check that `persona` names something real before it
builds the command line and runs it. A typo in a persona name is discovered at `claude -p`'s own
resolution time, one subprocess launch later than a caller might expect.

> `--agent` is the parity mechanism for reproducing an auto-spawned subagent's own identity, tools,
> and model from a manually-launched `claude -p`; `--append-system-prompt` is kept as a separate,
> narrower parameter precisely because it cannot carry that parity — it only ever adds text.

## §2.2.6 [CASE] [SOURCE-EQUIV] `load_agent_prompt()` and the frontmatter-stripping regex

A note on where this leaf actually lands, before the quote: the leaf text asks for "the regex" behind
stripping a persona's `--- … ---` frontmatter, and names `load_agent_prompt()` as the function that
carries it — and that is exactly what the file has. `agent.py` does contain a second function whose
job description sounds adjacent — `extract_json_envelope`, which pulls the JSON result back out of
`claude -p --output-format json`'s stdout — but that function contains **no regex at all**; its
fallback path is `json.JSONDecoder().raw_decode` walked across each `{` in the text, not a pattern
match. That function, its retry loop, and the 500-character stdout snippet it preserves on an
unparseable envelope belong to §3.6.10–3.6.12, not here — this leaf's job is the one real regex in
the file, and it lives in `load_agent_prompt`.

**Concept.** `load_agent_prompt(persona, agents_dir)` reads a persona `.md` file off disk and returns
its body with the leading YAML frontmatter block removed, so that block never lands inside a system
prompt.

**Why it exists.** A persona file on disk looks like this, in outline:

```markdown
---
model: sonnet
tools: [Read, Grep, Glob]
---
You are a read-only code reviewer...
```

The `--- … ---` block is metadata for the harness — which model to use, which tools to grant — not
prose meant for the model to read and reason about. `run_agent` appends this file's body onto a
system prompt via `--append-system-prompt` in at least one call path that loads a persona this way
rather than through `--agent`'s own resolution; if the frontmatter rode along unstripped, the model
would be handed a literal `model: sonnet\ntools: [Read, Grep, Glob]` fragment inside its own system
prompt and, per the module docstring quoted above, treat it as "noise the model tries to interpret"
— text it did not need and might quote back, reason about, or mistake for an instruction about what
tools it currently has, which it does not, because YAML in a prompt is not a schema.

**How it works — quote first.**

```python
_FRONTMATTER = re.compile(r"^\s*---\r?\n.*?\r?\n---\r?\n", re.DOTALL)


def load_agent_prompt(persona: str, agents_dir: str) -> str:
    """Read `.claude/agents/<persona>.md` and strip leading YAML frontmatter.

    The frontmatter (`--- model: … ---`) would otherwise leak into the appended
    system prompt.
    """
    path = Path(agents_dir) / f"{persona}.md"
    body = path.read_text(encoding="utf-8")
    return _FRONTMATTER.sub("", body, count=1).lstrip()
```

**The regex, read character class by character class.**

- `^` — anchors the match to the very start of the string. Without `re.MULTILINE` set (it is not
  set here), `^` matches only position 0 of the whole file, never the start of an interior line. This
  is the load-bearing choice: it is what stops the pattern from matching a `---` horizontal rule that
  the persona's own Markdown body uses further down the file. A per-line anchor would happily match
  the *second* `---` pair it finds, wherever that is, and strip the wrong span.
- `\s*` — zero or more whitespace characters, including newlines, immediately after that anchored
  start. This tolerates a persona file that opens with a blank line or two before the frontmatter
  fence, without requiring the fence to be the literal first three bytes of the file.
- `---` — a literal three-hyphen opening fence, matched exactly.
- `\r?\n` — an optional carriage return followed by a mandatory line feed. This is what makes the
  regex line-ending-agnostic: a file saved with Unix `\n` endings and one saved with Windows `\r\n`
  endings both match, because the `\r` is optional and only the `\n` is required.
  **[JAVA]** This is the same problem `BufferedReader.readLine()` solves for you silently in Java —
  it strips either ending without you writing `\r?` anywhere; a hand-rolled Java regex reading a file
  byte-for-byte would need the identical `\r?\n` idiom.
- `.*?` — the frontmatter body itself, matched **non-greedily**. Combined with `re.DOTALL` (which
  makes `.` match newlines too, otherwise the multi-line YAML body would stop the match at the first
  line break), this is the second load-bearing choice: a non-greedy `.*?` stops at the *first*
  `\r?\n---\r?\n` it can find after the opening fence, rather than the *last* one in the file. If the
  frontmatter's own YAML body — or worse, the persona's prose below it — contains another line of
  three dashes later on, a greedy `.*` would swallow everything up to that final occurrence instead
  of stopping at the true closing fence, silently deleting part of the actual prompt along with the
  metadata.
- `\r?\n` — the same optional-CR-then-mandatory-LF, now terminating the line before the closing
  fence.
- `---` — the literal closing fence.
- `\r?\n` — the same line-ending pattern once more, consuming the newline that ends the closing
  fence's own line.
- No `$` or end anchor follows. The pattern is not anchored at its own end, only at its start; it
  matches exactly the frontmatter span and stops there, leaving everything after the closing fence's
  trailing newline — the actual prompt body — completely untouched by the match itself.
- `re.DOTALL` — the compile flag that makes `.` inside `.*?` match `\n` as well as every other
  character. Without it, `.*?` could never cross the multiple lines a real YAML frontmatter block
  spans, and the pattern would never match a real file at all.
- `.sub("", body, count=1)` — not the regex itself, but the call site's own safety margin:
  `count=1` limits the substitution to the first match only. Even in a pathological file where the
  anchored, non-greedy pattern still somehow matched more than once (it structurally cannot, because
  `^` only ever matches position 0 in a single string), `count=1` is a second, independent guarantee
  that only one block is ever removed.

**What defeats it.** The pattern requires the opening fence to be reachable from position 0 through
whitespace only. A file that opens with a byte-order-mark character (`﻿`), a shebang-style
comment line, or any non-whitespace character before the first `---` fails to match at `^` at all —
`_FRONTMATTER.sub` then removes nothing, and the frontmatter leaks straight through into the
appended system prompt, which is exactly the failure the function exists to prevent. A frontmatter
block closed with a YAML end-of-document marker (`...`) instead of a second `---` fence also fails to
match, for the same reason: the pattern's closing token is the literal string `---`, not "any
recognized YAML terminator."

**Design property named.** The anchor at `^` plus the non-greedy `.*?` plus `count=1` together commit
to a narrow, specific claim: *only the first mandatory-shaped fence pair, and nothing past it, is
metadata.* That specificity is what lets the function trust a persona body to contain its own literal
`---` dividers later on without fear of losing prose to an over-eager match. **What would break
without it:** a greedy version of the same pattern (`.*` instead of `.*?`, or `re.MULTILINE` added so
`^`/`$` matched every line) would risk stripping real instructional text out of the persona's own
prompt whenever that prompt used a Markdown horizontal rule, silently shrinking what the model was
told with no error raised anywhere in the pipeline — the kind of defect that only shows up as "the
reviewer persona stopped mentioning its own review checklist" days later, with no exception in any
log to point at.

**[JAVA]** Python's `re.sub(pattern, repl, string, count=1)` is `Pattern.compile(regex,
Pattern.DOTALL).matcher(body).replaceFirst("")` in Java — `replaceFirst` already caps the
replacement count at one, so Java's standard library does not need the equivalent of an explicit
`count=1` argument; the cap is baked into the method name instead of a parameter.

The reader will meet the rest of this file's envelope-handling machinery — the 500-character stdout
snippet and the "keep the last parsed envelope through a retry" behaviour — in full at
§3.6.10–3.6.12.

> `_FRONTMATTER` strips exactly the first `--- … ---` block anchored at the start of a persona file,
> using a non-greedy body match and CRLF-tolerant line endings, so that YAML metadata meant for the
> harness never reaches the model as prompt text.

## §2.2.7 [TRAP] Choosing `--append-system-prompt` when the caller meant `--agent`

**Pitfall:** a caller of `run_agent` reasons that a persona is "just some text describing a role,"
and passes a restrictive description — "act as a read-only reviewer, never write files" — into the
`system_prompt` parameter instead of registering it as an agent and passing its name through
`persona`. **Symptom:** the resulting subprocess runs `claude -p ... --append-system-prompt "act as a
read-only reviewer, never write files" ...` with no `--agent` flag anywhere on the command line. The
session this launches keeps every default tool, `Write` and `Edit` and `Bash` included, because
nothing in `run_agent`'s command-building code path from `system_prompt` ever reaches a `tools:`
field — there is no such field for a bare string to populate. The agent behaves almost right, exactly
as file 01 named it: a well-behaved model mostly does stick to reading and grepping because the text
is a real instruction it attends to, and the one time an ambiguous task nudges it toward a `Write`
call, nothing stops it, because the call was never withheld. **Fix:** the restriction has to be a
registered agent definition with an explicit `tools:` list, passed through `persona`, so it becomes
`cmd += ["--agent", persona]` rather than `cmd += ["--append-system-prompt", system_prompt]`.

This engine's own function signature makes the mistake harder to make by accident than a single
free-text parameter would: `persona` and `system_prompt` are two separate keyword arguments with two
separate docstring paragraphs, each naming which CLI flag it becomes. A caller who wants a tool
ceiling has to affirmatively choose to populate `persona` with a name that resolves to a real,
registered `.md` file with a `tools:` field — the mistake this trap describes is still possible (a
caller can always pass the restrictive text into `system_prompt` instead, and nothing in `run_agent`
stops them), but it requires deliberately reaching for the wrong parameter rather than there being
only one parameter to reach for in the first place. No gotcha beyond the one already named: the
function's separation of concerns lowers the odds of this trap, it does not eliminate them.

**Interview:** "You're building a wrapper around `claude -p` for a pipeline. How does your function
signature stop someone from thinking a plain string persona is enforced?" — give the two-parameter
model this engine uses: a `persona: Optional[str]` that resolves to a registered agent and becomes
`--agent`, and a separate `system_prompt: str` that only ever becomes `--append-system-prompt`,
documented in the code as "not a substitute for `persona`" — so the enforced path and the
decoration-only path are structurally different arguments, not two uses of the same string field.

**No SVG for this file.** D-48, the four-flags comparison table from the previous file, already
carries this area's picture; nothing here adds a fifth row to it, so no new diagram is embedded.

## Pitfalls

- **Belief:** "A persona is just text, so passing restrictive wording into `run_agent`'s
  `system_prompt` parameter is the same as registering it as an agent." **Symptom:** the subprocess
  runs with `--append-system-prompt` and every default tool remains callable; the model follows the
  wording most of the time and nothing stops it the one time it does not. **Fix:** register the
  persona as a `.md` file with a `tools:` field and pass its name through `persona`, so the command
  line carries `--agent` instead. **Why people believe it:** both parameters visibly change what the
  model is told about its own role, and the difference — one carries an enforced tool list, the other
  cannot — is invisible unless you read `run_agent`'s own docstrings or the resulting command line.
- **Belief:** "The frontmatter-stripping regex just deletes anything between two `---` lines,
  wherever they are." **Symptom:** assuming a greedy, unanchored version would work the same;
  it would instead risk deleting a persona's own Markdown horizontal rule and the prose after it, with
  no error raised. **Fix:** the actual pattern anchors at `^` (start of file only, no
  `re.MULTILINE`) and matches the body non-greedily, so only the first fence pair at the very top of
  the file is ever removed. **Why people believe it:** "strip everything between two markers" reads
  as the obvious implementation; the anchor and the non-greedy quantifier are exactly the two details
  that make it safe, and both are easy to skim past.

## Cheat sheet

| Function | What it does | Flag(s) it feeds | Regex? |
|---|---|---|---|
| `load_agent_prompt(persona, agents_dir)` | Reads `<agents_dir>/<persona>.md`, strips leading frontmatter | Feeds text some callers append via `--append-system-prompt` | Yes — `_FRONTMATTER`, anchored `^`, non-greedy `.*?`, `re.DOTALL`, `count=1` |
| `run_agent(..., persona=...)` | Builds and runs the `claude -p` command | `--agent <persona>` when `persona` is set | No |
| `run_agent(..., system_prompt=...)` | Appends extra run context | `--append-system-prompt <text>` when `system_prompt` is set | No |
| `extract_json_envelope(stdout)` | Recovers the JSON result from noisy stdout | N/A — parses output, does not build a command | No — `JSONDecoder.raw_decode`, not regex (§3.6.10–3.6.12) |

## Self-test

1. Why does the module docstring rule out `--append-system-prompt` by name as the persona-parity
   mechanism?
   <details><summary>Answer</summary>Because it only appends to the default system prompt — it
   carries no `tools:` field and no `model:` field, so it cannot reproduce an auto-spawned subagent's
   full identity (system prompt, tools, and model together) the way `--agent` does.</details>
2. What does `run_agent`'s own docstring say `system_prompt` is, in contrast to `persona`?
   <details><summary>Answer</summary>"Appended as EXTRA run context via `--append-system-prompt`,
   not a substitute for `persona`."</details>
3. Why is `^` in `_FRONTMATTER` significant given `re.MULTILINE` is not set?
   <details><summary>Answer</summary>Without `re.MULTILINE`, `^` matches only position 0 of the
   whole file, not the start of every line — so the pattern can only ever match a frontmatter block
   at the very top of the file, never a `---` divider appearing later in the persona's own
   body.</details>
4. Why is `.*?` non-greedy instead of `.*`?
   <details><summary>Answer</summary>So the match stops at the first closing `\r?\n---\r?\n` it
   finds after the opening fence, rather than the last one in the file — a greedy match could run
   past the true closing fence and delete real prompt text along with the metadata.</details>
5. What two things does `\r?\n` guard against, and where does Java give you the same guarantee for
   free?
   <details><summary>Answer</summary>It matches both Unix (`\n`) and Windows (`\r\n`) line endings.
   Java's `BufferedReader.readLine()` strips either ending automatically, without a regex.</details>
6. What input would make `_FRONTMATTER.sub` remove nothing at all, leaving frontmatter to leak into
   the prompt?
   <details><summary>Answer</summary>Any non-whitespace character before the opening `---` — such as
   a byte-order-mark character — since `\s*` only tolerates whitespace between the anchored start and
   the fence. A frontmatter block closed with a YAML `...` marker instead of `---` also fails to
   match.</details>
7. Does `extract_json_envelope` use a regex to pull the JSON object out of `claude -p`'s stdout?
   <details><summary>Answer</summary>No — it tries `json.loads` on the whole trimmed string first,
   then falls back to `json.JSONDecoder().raw_decode` starting from each `{` in turn. There is no
   regex anywhere in that function; the file's one regex is `_FRONTMATTER`, used by
   `load_agent_prompt`.</details>
8. What stops a caller of `run_agent` from getting an enforced tool ceiling by passing restrictive
   wording into `system_prompt` instead of registering a persona?
   <details><summary>Answer</summary>Nothing in `run_agent` itself prevents it — the two-parameter
   signature only makes the correct choice more discoverable (via the docstrings and the fact that
   only `persona` becomes `--agent`), it does not stop a caller from choosing the wrong
   parameter.</details>

## Open questions

None.

---

**Leaves covered:** 2.2.5–2.2.7 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none — D-48 in the previous file carries this area's comparison
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 335
