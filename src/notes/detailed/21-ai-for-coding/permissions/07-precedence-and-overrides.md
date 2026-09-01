# 21 AI for Coding — local files, precedence and per-run overrides — BASICS (§1.4.35–1.4.38)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 1 of 6** | [Index](../00-index.md)
Previous: [working directories and workspace trust](06-directories-and-trust.md) · Next: [the sandbox, and a real permission block](08-sandbox-and-a-real-block.md)

This file closes out §1.4 with two questions the earlier files in this folder left open. First:
your own `.claude/settings.local.json` applies without a trust prompt because it's *your* file — but
what makes a file "yours," precisely, and what strips that status away? Second: files 01–04 in this
folder built three rule lists (deny, ask, allow) and file 05 built six modes on top of them, but never
said what happens when two *different settings sources* — a managed policy, a project file, a
command-line flag — disagree about the same rule. The answer is not the five-layer "highest sheet
wins" stack from `settings/01-basics-files-and-precedence.md`. It is a different composition rule
entirely, and mixing the two up is the single most common shape of "why is my allow rule not working."

## Concept 1 — a tracked local file, or a symlinked `.claude`, stops being "your own file"

### Mental model

Don't picture `.claude/settings.local.json` as one file with one trust status. Picture the trust
engine asking a single question every time it reads that file: **could this exact content have
arrived on my disk because someone else put it there?** A file that fails that question — because git
is tracking it, so a `git pull` can rewrite it, or because `.claude` itself is a symlink, so the real
content lives somewhere else entirely — gets treated exactly like `.claude/settings.json`: held until
you trust the folder. A file that passes gets applied immediately, no dialog, no wait. The filename
never changes; only the provenance does.

### Why it exists

`.claude/settings.local.json` is designed to be your personal, usually-`.gitignore`d scratch file for
"yes, and don't ask again" approvals — file 06 showed Claude Code writes exactly that kind of rule
there. If nothing checked provenance, a repository could ship a *tracked*
`.claude/settings.local.json` full of `permissions.allow` entries, and every clone would treat those
rules as "the current user's own approvals" and apply them without ever showing the workspace-trust
dialog that a tracked `.claude/settings.json` would have to pass through. The check exists so that the
one file explicitly designed to skip the trust step can't be turned into a second, unguarded copy of
the file that doesn't skip it.

### How it works

`[DOC]` Re-verified against `https://code.claude.com/docs/en/permissions`, 2026-08-29, quoted exactly:

> `.claude/settings.local.json` is normally your own file, so Claude Code applies its allow rules and
> additional directories without the trust step. When the file is tracked in git, or `.claude` is a
> symlink, Claude Code treats it as repository-supplied instead and holds its rules until you trust
> the folder.

— *Configure permissions*, re-verified 2026-08-29.

Two independent triggers, either one is enough to flip the file from "yours" to "repository-supplied":

| Trigger | What it means concretely |
|---|---|
| The file is **tracked** by git | `git ls-files` would list it — someone ran `git add .claude/settings.local.json` at some point, even if it's since been `.gitignore`d going forward |
| `.claude` itself is a **symlink** | The directory Claude Code reads settings from doesn't physically hold the file; it resolves elsewhere, so "this file sits in my working tree" no longer implies "I wrote it" |

Telling tracked from untracked requires running `git`, and the documentation is explicit about when
that check itself is allowed to run:

> Claude Code runs git to tell the two apart, and it runs git only once you've trusted the folder: you
> accepted the trust dialog for it or for a parent directory whose trust extends to it, or you're in a
> `-p` or SDK session, which counts as accepted.

— *Configure permissions*, re-verified 2026-08-29.

That is the same "counts as accepted" phrase the previous file's §1.4.34 corrected once already — it
names this git check and nothing broader. Concretely, in a `-p`/SDK session the check always runs
(since a `-p`/SDK session always "counts as accepted" for it), and:

- **Untracked** local file → applied immediately, no dialog, regardless of whether this folder has
  ever been trusted.
- **Tracked** local file, or symlinked `.claude` → held, exactly like a tracked
  `.claude/settings.json`: not used until the folder is trusted, and in `-p`/SDK, never used at all
  (the folder is never trusted there) — a `this workspace has not been trusted` warning goes to
  stderr instead.

**No SVG for this concept.** D-34, embedded in the previous file, already draws the tracked-versus-
untracked branch of this decision as one of its panels — see D-34 in the previous file.

### Code

The file that starts out on the "your own" side of the line — small, gitignored, exactly what
§1.2.4 said gets created on your first "don't ask again" approval:

```json
{
  "permissions": {
    "allow": ["Bash(./gradlew build:*)"]
  }
}
```

The same content, one `git add .claude/settings.local.json` away from crossing the line — nothing in
the JSON above changes; only git's index does. And the symlink route to the same outcome, with no git
operation at all:

```
rm -rf .claude
ln -s ../shared-claude-config .claude
```

After that `ln -s`, every settings file underneath — `.claude/settings.local.json` included — is read
through a symlink, so the local file is treated as repository-supplied even if it happens to be
untracked and even if `../shared-claude-config` is a private directory only you control. The gate
looks at the *shape* of the path (does `.claude` resolve somewhere your working tree doesn't
uniquely own), not at who currently has write access to the target.

### Gotcha

The symlink case is the one people trip on, because it produces the trust-gated behavior with **no
git operation to blame**. An engineer who centralizes their personal Claude Code configuration by
symlinking `.claude` at the root of every repository into one shared directory — a reasonable-looking
way to avoid repeating the same `settings.local.json` in ten checkouts — loses the "applies
immediately" fast path in every one of those ten repositories, because `.claude` being a symlink is
checked independently of whether the target's content is tracked anywhere. The fix is to symlink the
*contents* you want shared (a single file inside `.claude/`, or a settings key merged in some other
way) rather than the `.claude` directory itself, which is the one path component the trust engine
inspects directly.

**Pitfall:** the wrong belief is "trust is about the filename — `settings.local.json` always skips the
dialog because that's what the local file is for." The symptom is a session that inexplicably prints
`this workspace has not been trusted` in `-p` mode, or that queues an interactive trust prompt, even
though the file at that path looks exactly like a personal override. The fix: check `git ls-files
.claude/settings.local.json` and `ls -la .claude` (looking for `->` in the listing) before assuming
the file counts as yours — the filename never determines trust status, its provenance does.

> A local settings file is trusted as "your own" only while it is both untracked by git and reached
> through a real `.claude` directory; either condition failing makes it repository-supplied, held
> until the folder is trusted, exactly like `.claude/settings.json`.

## Concept 2 — deny is absolute: a different composition rule from settings precedence

### Mental model

`settings/01-basics-files-and-precedence.md` built the picture of five transparent sheets on a light
table, the highest sheet that draws on a key winning that key outright, every lower sheet's value for
that key invisible underneath. Permission `deny` does not sit on that table at all. Picture it
instead as a **union of blocklists**: every layer — managed, command line, project local, shared
project, user — contributes its own `deny` entries to one pooled set, and if *any* rule in that pooled
set matches the call, the call is blocked. There is no "sheet on top" for deny, because nothing ever
gets occluded — a deny written at the very bottom layer is exactly as final as one written at the
very top.

### Why it exists

The five-layer stack answers "whose configuration authority wins," which only needs one order because
exactly one layer's value can be "the" value for a scalar key like `model`. Permission rules are a
security control, and a security control that let a *lower*-authority layer silently reopen something
a *higher*-authority layer shut cannot be relied on by whoever set the block — an organization writing
`"deny": ["Bash(aws iam *)"]` into managed settings needs that block to survive every laptop's personal
settings, every project's committed file, and every command-line flag an individual engineer types,
without exception. A "highest wins" rule would let the command line, sitting only one layer below
managed, override it. Composing every layer's denies by union, rather than by rank, is what makes the
block unconditional instead of merely high-priority.

### How it works

`[DOC]` Re-verified against `https://code.claude.com/docs/en/permissions`, 2026-08-29, quoted in full:

> Permission rules follow the same settings precedence as all other Claude Code settings, with
> managed settings highest: no other level, including command line arguments, can override a managed
> permission rule.
>
> If a tool is denied at any level, no other level can allow it. For example, a managed settings deny
> can't be overridden by `--allowedTools`, and `--disallowedTools` can add restrictions beyond what
> managed settings define.
>
> The same holds across settings scopes: if user settings allow a permission and project settings
> deny it, the deny rule blocks it. The reverse is also true: a user-level deny blocks a project-level
> allow, because deny rules from any scope are evaluated before allow rules.

— *Configure permissions*, "Settings precedence", re-verified 2026-08-29.

Read that third paragraph slowly: **user settings — the bottom layer of the five-layer stack — can
deny something that project settings, three layers above it, tries to allow.** That sentence would be
nonsense under "highest sheet wins": a lower sheet cannot draw over a higher one. It is not nonsense
under "denies pool, then allows are checked" — a bottom-layer deny still lands in the pool, and the
pool is checked before any allow, from any layer, is consulted at all. This is the same
deny-then-ask-then-allow, first-match-wins evaluation order file 01 in this folder established for
rules *within* one merged rule set; §1.4.36 is the statement that the merge feeding that evaluation is
itself deny-first across every settings source, not rank-first.

**`[TRAP]`** The specific wrong belief §1.4.36 exists to correct is stated already in
`settings/01-basics-files-and-precedence.md`: *"Permission `deny` rules specifically follow an even
stricter rule than the five-layer stack above... that evaluation order is §1.4.36's material."* This
file is that material, made explicit: **a `deny` never loses a precedence contest, because it is never
in one.** Precedence contests exist for keys that have exactly one winning value, like `model`. A
`deny` list has no "winning value" to contest — it only ever adds entries, from every source, to one
pool that is consulted first.

`--allowedTools` is the flag most likely to make this feel like a bug: it sits at the command-line
layer, only one layer below managed, and reads like "the thing I typed for this run, closest to me, in
Manual mode." A managed `deny` still wins, because `--allowedTools` populates the allow list, and the
allow list is the one that gets checked last, not first.

### Code

A managed policy that blocks a whole class of AWS calls, complete and standalone:

```json
{
  "permissions": {
    "deny": ["Bash(aws iam *)"]
  }
}
```

An engineer's attempt to reopen exactly that command for one session, using the strongest per-run
override this topic covers (§1.4.38, below) rather than a settings file:

```
claude -p "Rotate the compromised access key for the deploy role" \
  --allowedTools "Bash(aws iam *)" "Read" \
  --output-format json
```

The `--allowedTools` flag is real, it is spelled correctly, and Claude Code accepts it without
complaint at startup. The session still refuses `aws iam` calls: the managed `deny` is in the pool
that's checked before any allow list — the command-line one included — is ever consulted. No error is
printed pointing at the flag; the tool call is simply denied at the point Claude would have made it,
the same as any other deny match.

### Gotcha

The place this bites hardest is exactly the "why is my allow rule not working" pattern named at the
top of this file: an engineer debugging a permission problem checks `/status` or `/permissions`
(§1.4.37, next), finds their own `--allowedTools` flag or their own project's `allow` entry, confirms
it's spelled correctly and reads it as "this should be granting the permission" — and stops looking,
because nothing in the five-layer settings-precedence mental model tells them to go check every
*other* layer's `deny` list too. The settings-precedence model they already know (highest wins)
predicts that checking their own layer's rule is sufficient. The deny-pool model this file establishes
says it is not: any layer, including one they don't control and may not even know exists, can hold a
matching deny.

**Insight:** the two composition rules coexist in the same product because they answer two different
questions. "Which value does this key have" (settings precedence, five-layer stack, highest wins) and
"is this specific action forbidden by anyone with the authority to forbid it" (permission deny,
union across every layer, first match in the pooled deny-then-ask-then-allow order) are not the same
kind of question, and a security control that behaved like the first would be a security control an
engineer could quietly route around one layer at a time.

**Interview:** *"If a managed settings file denies `Bash(aws iam *)`, can a developer re-enable it for
one session with `--allowedTools`?"* — No. Deny is not part of the five-layer "highest wins"
precedence stack; every layer's deny rules pool together and are checked before any layer's allow
rules, including `--allowedTools`, so a deny at any level — managed, project, or even a lower-ranked
user settings file — cannot be overridden by an allow rule anywhere else in the stack.

> A permission `deny` is not the winner of a five-layer precedence contest; it is one entry in a pool
> collected from every settings layer and evaluated before any `ask` or `allow` rule from any layer,
> which is why a deny written at the lowest layer still blocks an allow written at the highest one.

## Concept 3 — `/permissions`: read the rules and their source file; edits land mid-turn

`[DOC]` `[VERSION]` `[BUILD]` Re-verified against `https://code.claude.com/docs/en/permissions`,
2026-08-29, quoted exactly:

> You can view and manage Claude Code's tool permissions with `/permissions`. The dialog lists all
> permission rules and the `settings.json` file each rule comes from. You can open the dialog while
> Claude is working: when you add or remove a rule, Claude Code applies the change starting with
> Claude's next tool call in the same turn. Before v2.1.234, Claude Code queued the command until the
> turn finished.

— *Configure permissions*, "Manage permissions", re-verified 2026-08-29.

**In v2.1.2xx** (the target of these notes), this states two separate, useful things. First,
`/permissions` doesn't just show you the merged rule list — it names, per rule, which physical
settings file contributed it, which is exactly the information Concept 2's "why is my allow rule not
working" debugging pattern needs. Second, since v2.1.234, an edit you make while Claude is mid-turn —
partway through a multi-step tool-calling response — is live for that turn's *next* tool call, not
queued until the turn ends. **Before v2.1.234**, the same edit was accepted by the dialog immediately
but held by the running turn until it finished, so a deny you added to stop a Bash call already
in flight would not, in fact, stop the next Bash call in that same turn — only the one after the turn
ended. An engineer who learned `/permissions` on an older point release and never re-tested it will
describe the older, queued behavior as current; in v2.1.2xx it isn't.

### The artefact — a rule-source lookup, the part of `/permissions` you can script

`/permissions` itself is an interactive-only dialog — there's no headless equivalent to invoke inside
a `-p` run. What *is* reproducible outside the dialog is the lookup its first sentence describes:
given a rule, which file defines it. Here is that lookup as a standalone script, walking the same
three on-disk settings files in the same order the dialog reads them (managed settings and a
`--settings` flag are session-scoped, not files on disk, so a static lookup script cannot inspect
them):

```bash
#!/usr/bin/env bash
# find-permission-rule-source.sh
# Reports which settings file a literal permission rule string is defined in,
# walking the same files /permissions reads, in the same precedence order
# (managed and --settings are session-only and are not disk files, so this
# script covers the three that are: project local, shared project, user).
set -euo pipefail

RULE="${1:?usage: find-permission-rule-source.sh 'Bash(mvn test:*)'}"

CANDIDATES=(
  ".claude/settings.local.json"
  ".claude/settings.json"
  "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/settings.json"
)

for FILE in "${CANDIDATES[@]}"; do
  if [[ -f "$FILE" ]]; then
    for LIST in allow ask deny; do
      MATCH=$(jq -r --arg r "$RULE" --arg l "$LIST" \
        '.permissions[$l]? // [] | index($r)' "$FILE" 2>/dev/null || echo null)
      if [[ "$MATCH" != "null" ]]; then
        echo "$RULE -> permissions.$LIST in $FILE"
        exit 0
      fi
    done
  fi
done

echo "$RULE -> not found in any local settings file (check managed settings or --settings)"
exit 1
```

### Prove

Run against a fixture with three files in play — a shared project file allowing `mvn test`, a
project-local file allowing a `gradlew` build, and a user file denying `git push` — this is the actual
output of running the script above, once per rule:

```
$ ./find-permission-rule-source.sh "Bash(mvn test:*)"
Bash(mvn test:*) -> permissions.allow in .claude/settings.json

$ ./find-permission-rule-source.sh "Bash(./gradlew build:*)"
Bash(./gradlew build:*) -> permissions.allow in .claude/settings.local.json

$ ./find-permission-rule-source.sh "Bash(git push:*)"
Bash(git push:*) -> permissions.deny in /Users/…/.claude/settings.json

$ ./find-permission-rule-source.sh "Bash(curl *)"
Bash(curl *) -> not found in any local settings file (check managed settings or --settings)
```

The first three lines are exactly the "rule, and the file it comes from" pairing `/permissions`
reports natively in its dialog, reproduced here from files on disk rather than from the UI. The
fourth line is the honest negative case — a rule this script can't find isn't necessarily absent, it
may be sitting in managed settings or a `--settings` flag, neither of which is a file this static
script can read; `/permissions` itself, running inside the live session, does see those and would
report them.

**Unverified:** the exact on-screen text and layout `/permissions` renders for a rule/source pairing
is not independently reproduced here — only the underlying rule-to-file mapping the documentation
describes it computing is. See `## Open questions`.

### What this costs

Nothing, in tokens or dollars. `/permissions` is a client-side dialog: opening it, reading the merged
rule list, and saving an added or removed rule are all local file operations Claude Code performs
itself — none of it is sent to the model as a turn, so it adds zero tokens to the running
conversation's context and bills nothing. That is worth stating explicitly because most of this
topic's other `[BUILD]` artefacts do cost something; this is the rare one that is genuinely free
because it never reaches the model at all.

**Gotcha:** free to *open* is not the same as free to *use well* — a rule you add mid-turn still only
takes effect starting with the next tool call in that turn, so a Bash command Claude is already
executing when you save the new deny is not retroactively cancelled; the guarantee is about the next
call, not the current one.

## Concept 4 — three per-run override flags, one table

`[DOC]` Re-verified against `https://code.claude.com/docs/en/cli-reference` and
`https://code.claude.com/docs/en/permissions`, 2026-08-29. Three flags do related but distinct jobs at
the command line, and conflating them is easy because all three take a list of tool/rule strings:

| Flag | What it does | Behaves like which of the three rule lists | Does a `deny` still beat it? | Reach for it when |
|---|---|---|---|---|
| `--allowedTools` (`--allowed-tools`) | Pre-approves the named tools/rules for this run so they execute without a permission prompt | **allow** — checked last, after deny and ask | Yes — a matching `deny` anywhere in the pool still blocks the call | You know exactly which commands a scripted or CI run needs to execute unattended, and want to skip prompts for only those |
| `--disallowedTools` (`--disallowed-tools`) | Adds deny rules for this run: a bare tool name removes that tool from Claude's context entirely, a scoped rule like `Bash(rm *)` leaves the tool available and blocks only matching calls | **deny** — joins the pool from Concept 2, evaluated before ask and allow | Yes, trivially — it *is* a deny, so it stacks with every other layer's deny rather than competing with it | You want to narrow a run below whatever the settings files already allow, without editing any settings file |
| `--tools` | Restricts the session to only the named built-in tools — anything not listed is not part of the tool inventory Claude is even offered, rather than being offered-then-denied | **none of the three** — it operates one level upstream, on which tools exist at all, before deny/ask/allow ever run | Yes, vacuously for tools it excludes (there's nothing to deny once a tool doesn't exist), and yes for tools it includes (an existing `deny` on an included tool still applies) | You want to hand a run a small, fixed toolbox — for example, enabling a task-tracking tool that's off by default on a given model, or building a minimal reviewer that should never see `Bash` at all |

`[DOC]` `--allowedTools`, quoted: "Tools that execute without prompting for permission. See
permission rule syntax for pattern matching. To restrict which tools are available, use `--tools`
instead." `[DOC]` `--disallowedTools`, quoted: "Deny rules. A bare tool name removes the matching
tools from Claude's context: `"Edit"` removes Edit, `"*"` removes every tool, and `"mcp__*"` removes
every MCP tool. A scoped rule such as `Bash(rm *)` leaves the tool available and denies only matching
calls." `[DOC]` `--tools`, quoted: "List the tools you want alongside the other built-in tools you
use" — restricting the session's built-in tools to exactly the ones named, which is the "restrict
which tools are available" case the `--allowedTools` entry points at.

A full command line using all three together, restricting a headless run of the sdlc-harness's own
kind of task — running a project's test suite and reporting failures, with `Bash` narrowed to the one
command it needs and network access removed — to exactly the tools and rules it should have:

```
claude -p "Run mvn-test-runner and summarize any failing test classes" \
  --tools Bash Read Grep Glob TodoWrite \
  --allowedTools "Bash(mvn test:*)" "Read" "Grep" "Glob" \
  --disallowedTools "WebFetch" "Bash(git push *)" \
  --output-format json
```

Read right to left through the mechanism: `--tools` first shrinks the entire tool inventory to five
names, so `WebFetch` is not even offered — the later `--disallowedTools "WebFetch"` is then redundant
for this exact tool set but harmless, and would matter again the moment `--tools` grew to include it.
`--allowedTools` then pre-approves the specific `Bash`, `Read`, `Grep`, and `Glob` patterns this run
needs so none of them prompt. `--disallowedTools "Bash(git push *)"` adds a deny on top of an allowed
tool, narrower than the tool itself, which is exactly Concept 2's pool: even though `Bash` is both in
`--tools` and pre-approved by `--allowedTools`, this one Bash pattern is still blocked, because the
deny list is checked before the allow list regardless of which flag populated either one.

**Pitfall:** the wrong belief is "`--disallowedTools` is the opposite of `--allowedTools`, so passing
both for the same tool is a contradiction Claude Code has to resolve somehow." The symptom is
surprise when a scoped `--disallowedTools "Bash(rm *)"` silently wins over a broader
`--allowedTools "Bash"` for that one pattern, with no warning or error about the "conflict." The fix:
they are not opposites competing for the same slot, they are two different lists (allow and deny)
being populated at the same command-line layer, and Concept 2's rule — deny is pooled and checked
first, from any source — applies to CLI-supplied rules exactly as it applies to settings-file rules.
**Why people believe it:** in ordinary CLI tools, two flags that both name the same argument usually
mean "last one wins" or "error: conflicting flags"; Claude Code's permission system instead always
resolves rule conflicts by rule *type* (deny before ask before allow), never by which flag or file
supplied the rule or in what order.

**Interview:** *"You pass `--allowedTools "Bash"` and `--disallowedTools "Bash(rm -rf *)"` in the same
invocation. What happens on `rm -rf tmp/`?"* — It's denied. `--disallowedTools` populates the deny
list, `--allowedTools` populates the allow list, and deny rules are evaluated before allow rules
regardless of which flag or settings source contributed either one — the broader allow on `Bash` never
gets a chance to apply to a call the narrower deny already matched.

**No gotcha beyond the pitfall above: the rule composition here is exactly Concept 2's, restated at
the command-line layer rather than across settings files.**

> `--allowedTools` and `--disallowedTools` add entries to the allow and deny lists for one run, exactly
> as a settings file would, and are subject to the same deny-first pooling; `--tools` is a different
> mechanism entirely, narrowing which tools exist in the session before any permission rule is
> consulted at all.

## Pitfalls

- **Belief:** "`.claude/settings.local.json` always applies immediately — that's the whole point of
  the local file." **Outcome:** a session prints `this workspace has not been trusted` or queues a
  trust prompt for a file that looks like an ordinary personal override. **Fix:** check whether the
  file is tracked by git (`git ls-files .claude/settings.local.json`) and whether `.claude` is a
  symlink (`ls -la .claude`) — either one flips the file to repository-supplied, held until the folder
  is trusted, regardless of the filename. **Why people believe it:** the file's entire purpose, as
  documented, is to be the trust-exempt personal file; nothing about its name signals that the
  exemption is conditional on provenance rather than guaranteed by location.
- **Belief:** "a managed or higher-layer `deny` can be reopened by something lower in the five-layer
  precedence stack, such as `--allowedTools` on the command line, because the command line is close to
  the top." **Outcome:** the flag is accepted with no error, and the call is still blocked with no
  message pointing at why. **Fix:** treat `deny` as a separate composition rule from settings
  precedence — a pool collected from every layer, checked before any `allow`, from any layer — rather
  than as just another key in the five-layer stack; use `/permissions` to see every rule and its
  source file before assuming a flag or a project setting is broken. **Why people believe it:** the
  settings precedence they already learned genuinely is "highest layer wins," and nothing in that
  model warns that one specific key type — `deny` — is composed by a completely different rule.
- **Belief:** "`--disallowedTools` and `--allowedTools` naming the same tool is a contradiction Claude
  Code must resolve by flag order or by picking the more specific one." **Outcome:** a scoped deny
  silently wins over a broader allow with no conflict warning printed. **Fix:** read both flags as
  populating the ordinary deny and allow lists respectively, then apply the same deny-before-allow rule
  used everywhere else in the permission system. **Why people believe it:** most CLI tools treat two
  flags that name the same target as a literal conflict to flag or resolve by order, not as two
  independent lists feeding one fixed evaluation order.

## Cheat sheet

| Fact | Value |
|---|---|
| Local file counts as "yours" when | Untracked by git **and** `.claude` is a real directory, not a symlink |
| Local file counts as repository-supplied when | Tracked by git **or** `.claude` is a symlink (either alone is enough) |
| Git check to tell tracked vs. untracked only runs | Once the folder is trusted, or in `-p`/SDK (which "counts as accepted" for this check specifically) |
| Deny composition rule | Every layer's `deny` entries pool together; checked before `ask`, before `allow`, from any source |
| Does `--allowedTools` beat a managed `deny`? | No |
| Does a lower-layer (user) `deny` beat a higher-layer (project) `allow`? | Yes |
| `/permissions` shows | Every merged rule **and** the settings file it came from |
| `/permissions` edit takes effect | Starting with Claude's next tool call, same turn (v2.1.234+); queued until turn end before that |
| `--allowedTools` | Adds `allow` entries for this run |
| `--disallowedTools` | Adds `deny` entries for this run (bare name removes the tool; scoped rule denies matching calls) |
| `--tools` | Restricts the session's entire tool inventory to the named tools — upstream of deny/ask/allow |
| Cost of using `/permissions` | $0 / 0 tokens — client-side dialog, never sent to the model |

## Self-test

<details><summary>1. A `.claude/settings.local.json` is untracked by git but `.claude` is a symlink to a shared directory. Is it treated as your own file?</summary>
No. Either condition alone is enough to make it repository-supplied — tracked in git, or `.claude`
being a symlink. Being untracked doesn't save it once the symlink condition is also true.
</details>

<details><summary>2. Why can a `deny` set in `~/.claude/settings.json` (the lowest of the five settings layers) block an `allow` set in a project's committed `.claude/settings.json` (three layers higher)?</summary>
Because `deny` doesn't participate in the five-layer "highest wins" precedence contest at all. Every
layer's `deny` rules pool into one set that's evaluated before any layer's `allow` rules, so a
bottom-layer deny is exactly as final as a top-layer one — there's no rank comparison between the
denying layer and the allowing layer to lose.
</details>

<details><summary>3. Does `--allowedTools "Bash(aws iam *)"` override a managed settings deny on the same pattern?</summary>
No. A managed deny can't be overridden by `--allowedTools`; deny rules from any level, including
managed settings, are evaluated before allow rules from any level, including the command line.
</details>

<details><summary>4. What two things does `/permissions` show for each rule?</summary>
The rule itself, and the settings file it comes from — the exact information needed to tell which
layer is responsible for a rule that's behaving unexpectedly.
</details>

<details><summary>5. On Claude Code v2.1.220, you add a deny rule via `/permissions` while Claude is mid-turn, hoping to stop the very next tool call in that turn. Does it work?</summary>
No — v2.1.220 is before v2.1.234, so the edit is accepted by the dialog but queued until the running
turn finishes; the next tool call in that same turn still uses the old rule set. On v2.1.234 or later,
the edit applies starting with the next tool call in the same turn.
</details>

<details><summary>6. `--tools Bash Read` and `--disallowedTools "WebFetch"` are passed together. Is the second flag doing anything?</summary>
No, redundantly — `--tools` already excludes `WebFetch` from the session's tool inventory entirely, so
there is no `WebFetch` tool call for the `--disallowedTools` deny rule to ever match. The deny rule
would matter only if `--tools` (or the absence of a `--tools` flag) left `WebFetch` available.
</details>

<details><summary>7. `--allowedTools "Bash"` and `--disallowedTools "Bash(rm -rf *)"` are both passed. What happens to `rm -rf tmp/`?</summary>
It's denied. The scoped deny rule is checked before the broad allow rule, regardless of which flag
supplied either one — this is the same deny-before-allow pooling that governs settings files, applied
at the command-line layer.
</details>

<details><summary>8. What does `/permissions` cost, in tokens, to open and use?</summary>
Nothing. It's a client-side dialog — reading the merged rule list and saving an edit are local file
operations that never get sent to the model as part of the conversation, so no tokens are spent and no
turn is billed.
</details>

## Open questions

**Unverified:** the exact on-screen text and visual layout `/permissions` renders when listing a
rule alongside its source file is not independently reproduced in this file — only the underlying
rule-to-file mapping the documentation describes it computing was reproduced, via the standalone
`find-permission-rule-source.sh` script and its real output. Confirming the literal dialog rendering
would need an interactive session capture against a v2.1.2xx binary.

---

**Leaves covered:** 1.4.35–1.4.38 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** none — D-34 in the previous file carries this row's tracked-versus-untracked panel
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 537
