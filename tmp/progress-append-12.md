
### 12 api-design — syllabus, 2026-09-03 (prompt and notes NOT started)

| Artefact | State |
|---|---|
| `src/topics/12-api-design.md` | pre-existing |
| `src/syllabus/12-api-design.md` | written, 3,631 lines / **939 leaves** in 65 sections |
| `src/metadata/prompts/12-api-design-prompt.md` | not started |
| `src/notes/detailed/12-api-design/` | not started |

#### Syllabus pass — `topic-enhancer-agent` Mode A, 2026-09-03

PART 1 basics 478 (§1.1–1.28), PART 2 intermediate 146 (§2.1–2.15), PART 3 under
the hood 82 (§3.1–3.9), PART 4 build it 52 (§4.1–4.10), PART 5 interview/retention
181 (§5.1–5.3). Tags: 285 `[PROVE]`, 201 `[TRAP]`, 159 `[RESEARCH]`, 93 `[SOURCE]`,
52 `[BUILD]`, 50 `[VERSION-TRAP]`. PART 5 carries 118 questions and a 56-entry
trap index.

Scope frame: the **contract layer**. HTTP substrate (RFC 9110–9114), REST and the
maturity ladder, resource/URI modelling, the full method and status-code surface,
representation and PATCH formats, content negotiation, conditional requests and
ETags, HTTP caching (RFC 9111), collection semantics, the error contract (RFC 9457),
idempotency keys end to end, versioning/deprecation/sunset, rate limiting, async and
bulk shapes, hypermedia, OpenAPI + JSON Schema, gRPC and GraphQL as contracts, and
the Spring surface. Component internals are parked behind `[X-REF nn]` to siblings
09, 10, 13, 14, 15, 16, 22 with the "one paragraph, then point" contract.

**Four corrections the write pass must apply to the pre-existing guide** — each is
flagged in the syllabus's closing gap table:

1. `Deprecation: true` is invalid; RFC 9745 defines `Deprecation` as an IMF-fixdate.
2. RFC 7807 is obsoleted by **RFC 9457** — cite 9457 for problem details.
3. The `RateLimit-Limit` / `-Remaining` / `-Reset` triple is superseded by the
   ratelimit-headers draft-11 pair `RateLimit` + `RateLimit-Policy`.
4. A concurrent duplicate under an idempotency key answers **`409`**, not
   `425 Too Early`.

Five numeric claims are tagged **unverified** and must be confirmed against source
or dropped at write time.

#### Operational note — the 64k output cap kills a single-Write syllabus

The first dispatch died with `max_output_tokens` (64,000) mid-`Write` and left
**no file at all** — a whole research pass' worth of work was reachable only by
resuming the agent's transcript. Syllabus files run 1,900–5,700 lines; one Write
cannot carry that.

**Rule for every future syllabus pass:** instruct the agent to write the header
plus the first sections with `Write`, then append in **~400-line chunks** via
quoted-delimiter heredoc (`cat >> path <<'EOF'`) so backticks and `$` survive, and
never to shrink scope to fit the cap — chunk more, not less. Recovery path when it
does blow up: `SendMessage` to the same agent id, since the research context
survives the API error.
